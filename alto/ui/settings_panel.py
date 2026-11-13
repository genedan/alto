from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import settings
from ..settings import (
    CLEFS,
    DEFAULT_RANGES,
    MAX_DIATONIC,
    MIN_DIATONIC,
    NAMINGS,
    NOTE_VALUES,
    RANGE_LIMITS,
    NoteNameSettings,
    diatonic_name,
    key_name,
)
from ..theory.pitch import MAJOR_KEYS, Note
from ..theory.scales import INVERSION_NAMES
from .colors import blend
from .keyboard import KeyboardSpan
from .pictures import CLEF_NAMES, VALUE_NAMES, ClefPictures, KeySignaturePicture, NamePicture, RangePictures, ValuePictures
from .staff import StaffWidget
from .store import int_value, store


def load_note_names() -> None:
    """Load saved note-name settings into the shared settings object."""
    s = store()
    cfg = settings.note_names
    saved = s.value("noteNames/clefs")
    if saved is not None:
        text = saved if isinstance(saved, str) else ",".join(saved)
        cfg.clefs = {c for c in text.split(",") if c in settings.RANGE_KEYS}
    if s.value("noteNames/mode") == "grand":  # an older version had a switch between the grand staff and single clefs
        cfg.clefs = {"grand"}
    s.remove("noteNames/mode")
    keys = str(s.value("noteNames/keys", "") or "")
    if keys:
        cfg.key_signatures = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or {0}
    values = str(s.value("noteNames/values", "") or "")
    if values:
        cfg.note_values = {v for v in values.split(",") if v in NOTE_VALUES} or {"whole"}
    naming = str(s.value("noteNames/naming", cfg.naming))
    cfg.naming = naming if naming in NAMINGS else "letters"
    cfg.accidentals = str(s.value("noteNames/accidentals", "false")).lower() == "true"
    cfg.ranges = {}
    for item in str(s.value("noteNames/ranges", "") or "").split(","):  # e.g. "treble:31-33,bass:14-28"
        try:
            key, span = item.split(":")
            lo, hi = (int(x) for x in span.split("-"))
        except ValueError:
            continue
        if key in DEFAULT_RANGES and MIN_DIATONIC <= lo <= hi <= MAX_DIATONIC:
            cfg.ranges[key] = (lo, hi)


def save_note_names() -> None:
    s = store()
    cfg = settings.note_names
    s.setValue("noteNames/clefs", ",".join(c for c in settings.RANGE_KEYS if c in cfg.clefs))
    s.setValue("noteNames/keys", ",".join(str(k) for k in cfg.active_keys()))
    s.setValue("noteNames/values", ",".join(cfg.active_values()))
    s.setValue("noteNames/naming", cfg.naming)
    s.setValue("noteNames/accidentals", "true" if cfg.accidentals else "false")
    s.setValue("noteNames/ranges", ",".join(f"{k}:{lo}-{hi}" for k, (lo, hi) in cfg.ranges.items()))


def _guard_last(boxes, enabled: bool = True) -> None:
    """Disable the only checked box so at least one choice always stays selected."""
    checked = [b for b in boxes if b.isChecked()]
    for box in boxes:
        box.setEnabled(enabled and not (len(checked) == 1 and box.isChecked()))


def _key_label(count: int) -> str:
    return f"{MAJOR_KEYS[count]}  ·  " + ("none" if count == 0 else f"{abs(count)}{'♯' if count > 0 else '♭'}")


def _arrow(kind: Qt.ArrowType, tip: str) -> QToolButton:
    btn = QToolButton()
    btn.setArrowType(kind)
    btn.setProperty("arrowButton", True)  # styled with a visible border (see style.py)
    btn.setToolTip(tip)
    btn.setAutoRepeat(True)
    btn.setAutoRepeatDelay(350)
    btn.setAutoRepeatInterval(90)
    return btn


class RangeEditor(QWidget):
    """A staff showing the lowest and highest note asked for a clef. Arrows on the left move the lower
    bound, arrows on the right move the upper bound."""

    edited = Signal(str, int, int)  # clef key, low, high (diatonic)

    def __init__(self, key: str, low: int, high: int, parent=None):
        super().__init__(parent)
        self.key, self.low, self.high = key, low, high
        self.limits = RANGE_LIMITS[key]
        self.caption_text = QLabel()
        self.caption_text.setStyleSheet("font-size: 12pt;")
        self.caption = QWidget()  # the clef as a picture, then the lowest and highest note
        caption_row = QHBoxLayout(self.caption)
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.addWidget(ClefPictures([key], 0.9))
        caption_row.addWidget(self.caption_text)
        caption_row.addStretch()
        self.staff = StaffWidget(gap=9.0, side=18.0, note_offset=62.0, margin=8.0, compact=True)
        self.staff.setFixedWidth(168)
        self.low_up = _arrow(Qt.ArrowType.UpArrow, "Raise the lowest note")
        self.low_down = _arrow(Qt.ArrowType.DownArrow, "Lower the lowest note")
        self.high_up = _arrow(Qt.ArrowType.UpArrow, "Raise the highest note")
        self.high_down = _arrow(Qt.ArrowType.DownArrow, "Lower the highest note")
        self.low_up.clicked.connect(lambda: self._move(low=1))
        self.low_down.clicked.connect(lambda: self._move(low=-1))
        self.high_up.clicked.connect(lambda: self._move(high=1))
        self.high_down.clicked.connect(lambda: self._move(high=-1))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch()  # keep the staff and its arrows together, centred in the pane
        for column, buttons in ((0, (self.low_up, self.low_down)), (2, (self.high_up, self.high_down))):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addStretch()  # centre the pair on the staff's midline
            col.addWidget(buttons[0])
            col.addWidget(buttons[1])
            col.addStretch()
            if column == 0:
                row.addLayout(col)
                row.addWidget(self.staff)
            else:
                row.addLayout(col)
        row.addStretch()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 16)  # space between one clef's block and the next
        lay.setSpacing(8)
        lay.addWidget(self.caption)
        lay.addLayout(row)
        self._refresh()

    def _move(self, low: int = 0, high: int = 0):
        self.low = min(max(self.low + low, self.limits[0]), self.high)  # the lower bound can't pass the upper
        self.high = max(min(self.high + high, self.limits[1]), self.low)
        self._refresh()
        self.edited.emit(self.key, self.low, self.high)

    def _refresh(self):
        self.caption_text.setText(f"<b>{diatonic_name(self.low)} – {diatonic_name(self.high)}</b>")
        self.staff.show_notes([[Note.from_diatonic(self.low)], [Note.from_diatonic(self.high)]], self.key)
        self.low_up.setEnabled(self.low < self.high)
        self.low_down.setEnabled(self.low > self.limits[0])
        self.high_up.setEnabled(self.high < self.limits[1])
        self.high_down.setEnabled(self.high > self.low)


class KeyDiagram(QWidget):
    """A small fork showing which key signatures are selected: C major on the left, then two rows of seven dots, 1 to
    7 sharps on the top row and 1 to 7 flats on the bottom. Selected keys are filled, the rest are hollow."""

    DOT, PITCH, ROW_GAP, PAD = 4.4, 12.6, 13.0, 1.5  # dot radius and spacing, in pixels

    def __init__(self, keys: set[int] | None = None, parent=None):
        super().__init__(parent)
        self.keys: set[int] = set(keys or ())
        self.first_column = self.PAD + 2 * self.DOT + 7 + self.DOT          # x of the 1-sharp / 1-flat dots
        self.setFixedSize(int(self.first_column + 6 * self.PITCH + self.DOT + self.PAD) + 1,
                          int(self.ROW_GAP + 2 * self.DOT + 2 * self.PAD) + 3)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row underneath is the click target
        self._update_tip()

    def set_keys(self, keys: set[int]) -> None:
        self.keys = set(keys)
        self._update_tip()
        self.update()

    def _update_tip(self) -> None:
        names = [MAJOR_KEYS[k] for k in sorted(self.keys, key=lambda k: (k < 0, abs(k)))]
        self.setToolTip(", ".join(names))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        text = pal.color(QPalette.ColorRole.Text)
        base = pal.color(QPalette.ColorRole.Base)  # the row is filled with the base colour

        def shade(t: float) -> QColor:  # t of the way from the row's background to the text colour
            return blend(base, text, t)

        filled, outline = shade(0.85), shade(0.5)  # both stand out from the background, in a light or a dark theme
        mid, top = self.height() / 2, self.height() / 2 - self.ROW_GAP / 2
        spots = [(0, self.PAD + self.DOT, mid)]  # C major, between the two rows
        for n in range(1, 8):
            x = self.first_column + (n - 1) * self.PITCH
            spots += [(n, x, top), (-n, x, top + self.ROW_GAP)]
        for count, x, y in spots:
            selected = count in self.keys
            p.setPen(QPen(filled if selected else outline, 1.2))
            p.setBrush(filled if selected else base)
            p.drawEllipse(QPointF(x, y), self.DOT, self.DOT)


ROW_PICTURE_WIDTH = 238  # room for a picture on its own line in a menu row (pane width less margins)


def _label_with_picture(button: QAbstractButton, picture, name: str) -> None:
    """Label a checkbox or radio button with a picture (a clef, a note value ...) instead of text. The name stays
    as the tooltip and the accessible name."""
    button.setIcon(picture.to_icon())
    button.setIconSize(picture.size())
    button.setToolTip(name)
    button.setAccessibleName(name)


def _label_with_clef(button: QAbstractButton, clef: str, scale: float = 1.4) -> None:
    """A clef's picture, with its name written to the right of it."""
    _label_with_picture(button, ClefPictures([clef], scale), CLEF_NAMES[clef])
    button.setText(CLEF_NAMES[clef])


def _clef_box(clef: str, scale: float = 1.4) -> QCheckBox:
    box = QCheckBox()
    _label_with_clef(box, clef, scale)
    return box


def _clef_list(boxes: dict[str, QCheckBox]) -> QWidget:
    """The clef checkboxes one under another, in three groups divided by a line: the grand staff, the treble, bass, alto and
    tenor clefs, and the soprano, mezzo-soprano and baritone clefs. A group none of the boxes belong to is left out. The
    list is indented under its heading."""
    widget = QWidget()
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(24, 0, 0, 0)
    lay.setSpacing(8)
    groups = [[boxes[c] for c in group if c in boxes] for group in settings.CLEF_GROUPS]
    for i, group in enumerate([g for g in groups if g]):
        if i:
            rule = QFrame()
            rule.setFrameShape(QFrame.Shape.HLine)
            rule.setFrameShadow(QFrame.Shadow.Plain)
            rule.setStyleSheet("color: palette(mid);")
            lay.addWidget(rule)
        for box in group:
            lay.addWidget(box, 0, Qt.AlignmentFlag.AlignLeft)
    return widget


def _show_keys(row: _Row, diagram: KeyDiagram, enabled: bool, keys: set[int]) -> None:
    """Show the selected keys as a circle of fifths in the row, or 'Off' when key signatures are switched off."""
    diagram.set_keys(keys)
    diagram.setVisible(enabled)
    row.value.setText("" if enabled else "Off")


class _Row(QPushButton):
    """A menu row: title on the left, current value and a chevron on the right. A `tall` row puts a picture on a
    second line of its own, using the full width, for summaries that need room to be readable."""

    def __init__(self, title: str, chevron: bool = True, tall: bool = False):
        super().__init__()
        self.tall = tall
        self._contents: QBoxLayout  # the layout inside the row
        self.title = QLabel(f"<b>{title}</b>")
        self.value = QLabel()
        self.value.setStyleSheet("color: gray;")
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for label in (self.title, self.value):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        arrow = QLabel("›")
        arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if tall:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(11, 8, 11, 8)
            outer.setSpacing(4)
            top = QHBoxLayout()
            top.addWidget(self.title)
            top.addWidget(self.value, 1)
            if chevron:
                top.addWidget(arrow)
            outer.addLayout(top)
            self._below = QHBoxLayout()
            outer.addLayout(self._below)
            self._contents = outer
            return
        self.setMinimumHeight(48)
        lay = QHBoxLayout(self)
        self._contents = lay
        lay.setContentsMargins(11, 4, 11, 4)  # leaves room for a small diagram in the row
        lay.addWidget(self.title)
        lay.addWidget(self.value, 1)
        if chevron:
            lay.addWidget(arrow)

    def attach(self, widget: QWidget) -> None:
        """Put a widget in the row: just after the value text, or (in a tall row) centred on its own line below."""
        if self.tall:
            self._below.addStretch()
            self._below.addWidget(widget)
            self._below.addStretch()
            self.fit()
        else:
            self._contents.insertWidget(2, widget)

    def fit(self) -> None:
        """Make a tall row as high as its contents need (a button does not size itself to a layout inside it)."""
        if self.tall:
            self.setMinimumHeight(self._contents.minimumSize().height())


class Switch(QAbstractButton):
    """A pill-shaped on/off switch whose knob slides across when toggled."""

    W, H = 42, 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pos = 0.0  # knob position, 0 (off) .. 1 (on)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._set_pos)
        self.toggled.connect(self._slide)

    def _set_pos(self, value):
        self._pos = float(value)
        self.update()

    def _slide(self, on: bool):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setChecked(self, on: bool):  # no animation when set programmatically
        super().setChecked(on)
        self._anim.stop()
        self._set_pos(1.0 if on else 0.0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        off, on = pal.color(QPalette.ColorRole.Mid), pal.color(QPalette.ColorRole.Highlight)
        track = blend(off, on, self._pos)
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(self.rect(), self.H / 2, self.H / 2)
        r, margin = self.H / 2 - 3, 3
        x = margin + r + self._pos * (self.W - 2 * (margin + r))
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(x, self.H / 2), r, r)

    def sizeHint(self):
        return QSize(self.W, self.H)


class _ToggleRow(_Row):
    """A menu row with a switch that changes a setting in place instead of opening a page."""

    switched = Signal(bool)

    def __init__(self, title: str):
        super().__init__(title, chevron=False)
        self.value.hide()
        self.switch = Switch()
        self.switch.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the whole row is the click target
        self._contents.addWidget(self.switch)
        self.clicked.connect(lambda: self._set(not self.switch.isChecked()))

    def _set(self, on: bool):
        self.switch.setChecked(on)
        self.switch.update()
        self.switched.emit(on)

    def isOn(self) -> bool:
        return self.switch.isChecked()

    def setOn(self, on: bool):
        self.switch.setChecked(on)


def _subpage(title: str, body: QWidget, back, fill: bool = False) -> QWidget:
    """A second-layer page: a Back button and title above `body`."""
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(0, 0, 0, 0)
    head = QHBoxLayout()
    btn = QToolButton()
    btn.setText("‹ Back")
    btn.setAutoRaise(True)
    btn.clicked.connect(back)
    head.addWidget(btn)
    head.addWidget(QLabel(f"<b>{title}</b>"))
    head.addStretch()
    lay.addLayout(head)
    lay.addWidget(body, 1 if fill else 0)
    if not fill:
        lay.addStretch()
    return page


class SlideStack(QStackedWidget):
    """A stacked widget whose pages slide in from the right (going deeper) or the left (going back)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slide: QParallelAnimationGroup | None = None

    @property
    def sliding(self) -> bool:
        return self._slide is not None

    def slide_to(self, index: int) -> None:
        if self.sliding or index == self.currentIndex():
            return  # ignore requests mid-transition
        old, new = self.currentWidget(), self.widget(index)
        assert old is not None and new is not None
        w = self.width()
        sign = 1 if index > self.currentIndex() else -1
        new.setGeometry(0, 0, w, self.height())
        new.move(sign * w, 0)
        new.show()
        new.raise_()
        group = QParallelAnimationGroup(self)
        for widget, start, end in ((old, 0, -sign * w), (new, sign * w, 0)):
            anim = QPropertyAnimation(widget, b"pos", group)
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(QPoint(start, 0))
            anim.setEndValue(QPoint(end, 0))
            group.addAnimation(anim)

        def done():
            self.setCurrentIndex(index)
            old.move(0, 0)
            new.move(0, 0)
            self._slide = None

        group.finished.connect(done)
        self._slide = group
        group.start()


class ExerciseSettingsPanel(QWidget):
    """What every exercise's settings pane has in common: it says when a setting has been edited."""

    changed = Signal()


class NoteNameSettingsPanel(ExerciseSettingsPanel):
    """Two-layer settings: a menu (Clefs, Range) leading to a page for each. Edits are live."""

    def __init__(self, cfg: NoteNameSettings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.clefs_row, self.range_row = _Row("Clefs"), _Row("Range", tall=True)
        self.keys_row, self.values_row, self.names_row = _Row("Key signatures"), _Row("Note values"), _Row("Note names")
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        self.clef_pictures = ClefPictures()
        self.clefs_row.attach(self.clef_pictures)
        self.range_pictures = RangePictures(max_width=ROW_PICTURE_WIDTH)
        self.range_row.attach(self.range_pictures)
        self.value_pictures = ValuePictures()
        self.values_row.attach(self.value_pictures)
        self.name_picture = NamePicture()
        self.names_row.attach(self.name_picture)
        for index, row in enumerate((self.clefs_row, self.range_row, self.keys_row, self.values_row, self.names_row), 1):
            row.clicked.connect(lambda _=False, i=index: self._go(i))
            mlay.addWidget(row)
        self.accidentals_row = _ToggleRow("Accidentals")
        self.accidentals_row.setToolTip("Also ask notes with sharps, flats and naturals")
        self.accidentals_row.setOn(cfg.accidentals)
        self.accidentals_row.switched.connect(self._accidentals_toggled)
        mlay.addWidget(self.accidentals_row)
        mlay.addStretch()

        # layer 2: clefs
        self.boxes = {c: _clef_box(c) for c in settings.RANGE_KEYS}
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("One of the checked clefs is picked at random.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        blay.addWidget(hint)
        for c, box in self.boxes.items():
            box.setChecked(c in cfg.clefs)
        blay.addWidget(_clef_list(self.boxes))
        _guard_last(list(self.boxes.values()))  # the last checked clef can't be unchecked
        for box in self.boxes.values():
            box.toggled.connect(self._clefs_edited)
        clefs_page = _subpage("Clefs", body, lambda: self._go(0))

        # layer 2: range
        self.range_body = QWidget()
        self.range_lay = QVBoxLayout(self.range_body)
        self.range_lay.setContentsMargins(6, 4, 10, 8)
        self.range_editors: dict[str, RangeEditor] = {}
        scroll = QScrollArea()
        scroll.setWidget(self.range_body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        range_page = _subpage("Range", scroll, lambda: self._go(0), fill=True)

        # layer 2: key signatures, each drawn as it would be written (flats on the left, sharps on the right)
        self.key_list = KeyChecklist(cfg.key_signatures)
        self.key_list.changed.connect(self._keys_edited)
        self.key_boxes = self.key_list.boxes
        keys_page = _subpage("Key signatures", self.key_list, lambda: self._go(0))

        # layer 2: note values, a vertical list: the engraved symbol, then its name
        self.value_boxes = {v: QCheckBox(VALUE_NAMES[v]) for v in NOTE_VALUES}
        values_body = QWidget()
        vlay = QVBoxLayout(values_body)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(2)
        values_hint = QLabel("One of the checked values is picked at random.")
        values_hint.setWordWrap(True)
        vlay.addWidget(values_hint)
        for v, box in self.value_boxes.items():
            picture = ValuePictures([v], 1.25, centre_stemless=True)
            box.setIcon(picture.to_icon())
            box.setIconSize(picture.size())
            box.setStyleSheet("QCheckBox { font-size: 11pt; }")
            box.setChecked(v in cfg.note_values)
            box.toggled.connect(self._values_edited)
            vlay.addWidget(box)
        vlay.addStretch()
        values_page = _subpage("Note values", values_body, lambda: self._go(0))

        # layer 2: note names
        self.naming_radios = {k: QRadioButton() for k in NAMINGS}
        for k, radio in self.naming_radios.items():
            _label_with_picture(radio, NamePicture(k, 1.6), NAMINGS[k])
        names_body = QWidget()
        nlay = QVBoxLayout(names_body)
        nlay.setContentsMargins(0, 0, 0, 0)
        naming_group = QButtonGroup(self)
        for k, radio in self.naming_radios.items():
            naming_group.addButton(radio)
            radio.setChecked(k == cfg.naming)
            radio.toggled.connect(self._names_edited)
            nlay.addWidget(radio)
        names_page = _subpage("Note names", names_body, lambda: self._go(0))

        for page in (menu, clefs_page, range_page, keys_page, values_page, names_page):
            self.stack.addWidget(page)
        _guard_last(list(self.key_boxes.values()))
        _guard_last(list(self.value_boxes.values()))
        self._refresh_summaries()

    # navigation
    def _go(self, index: int):
        if self.stack.sliding or index == self.stack.currentIndex():
            return  # ignore clicks mid-transition
        if index == 0:
            self._refresh_summaries()
        elif index == 2:
            self._build_range_rows()
        self.stack.slide_to(index)

    def _active_keys(self) -> list[str]:
        return self.cfg.active_clefs()

    def _refresh_summaries(self):
        keys = self._active_keys()
        self.clef_pictures.set_clefs(keys)
        self.range_pictures.set_items([(k, *self.cfg.range_for(k)) for k in keys])
        self.range_row.fit()
        _show_keys(self.keys_row, self.keys_diagram, True, set(self.cfg.active_keys()))
        self.value_pictures.set_values(self.cfg.active_values())
        self.name_picture.set_naming(self.cfg.naming)

    # clefs page
    def _clefs_edited(self):
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))  # the last checked clef can't be unchecked
        save_note_names()
        self.changed.emit()

    # key signatures / note values / note names pages
    def _keys_edited(self):
        self.cfg.key_signatures = {k for k, b in self.key_boxes.items() if b.isChecked()}
        _guard_last(list(self.key_boxes.values()))
        self._save_and_emit()

    def _values_edited(self):
        self.cfg.note_values = {v for v, b in self.value_boxes.items() if b.isChecked()}
        _guard_last(list(self.value_boxes.values()))
        self._save_and_emit()

    def _names_edited(self):
        self.cfg.naming = next(k for k, r in self.naming_radios.items() if r.isChecked())
        self._save_and_emit()

    def _accidentals_toggled(self, on: bool):
        self.cfg.accidentals = on
        self._save_and_emit()

    def _save_and_emit(self):
        save_note_names()
        self.changed.emit()

    # range page
    def _build_range_rows(self):
        while self.range_lay.count():
            item = self.range_lay.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self.range_editors = {}
        for key in self._active_keys():
            editor = RangeEditor(key, *self.cfg.range_for(key))
            editor.edited.connect(self._range_edited)
            self.range_editors[key] = editor
            self.range_lay.addWidget(editor)
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset_ranges)
        self.range_lay.addWidget(reset)
        self.range_lay.addStretch()

    def _range_edited(self, key: str, low: int, high: int):
        self.cfg.ranges[key] = (low, high)
        self._save_and_emit()

    def _reset_ranges(self):
        self.cfg.ranges.clear()
        save_note_names()
        self._build_range_rows()
        self.changed.emit()


def load_keyboard() -> None:
    saved_settings = store()
    cfg = settings.keyboard
    cfg.black_keys = str(saved_settings.value("keyboard/blackKeys", "true")).lower() != "false"
    cfg.require_octave = str(saved_settings.value("keyboard/requireOctave", "false")).lower() == "true"
    try:
        low = int_value(saved_settings, "keyboard/low", cfg.low)
        high = int_value(saved_settings, "keyboard/high", cfg.high)
    except (TypeError, ValueError):
        return
    first, last = settings.KEYBOARD_FULL
    if first <= low <= high <= last:
        cfg.low, cfg.high = low, high
    cfg.key_signature = str(saved_settings.value("keyboard/keySignature", "false")).lower() == "true"
    keys = str(saved_settings.value("keyboard/keys", "") or "")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


def save_keyboard() -> None:
    saved_settings = store()
    cfg = settings.keyboard
    saved_settings.setValue("keyboard/blackKeys", "true" if cfg.black_keys else "false")
    saved_settings.setValue("keyboard/requireOctave", "true" if cfg.require_octave else "false")
    saved_settings.setValue("keyboard/low", cfg.low)
    saved_settings.setValue("keyboard/high", cfg.high)
    saved_settings.setValue("keyboard/keySignature", "true" if cfg.key_signature else "false")
    saved_settings.setValue("keyboard/keys", ",".join(str(k) for k in cfg.active_keys()))


class KeyChecklist(QWidget):
    """Checkboxes for the 15 major keys, flats on the left and sharps on the right. At least one stays checked."""

    changed = Signal()

    def __init__(self, selected: set[int], parent=None):
        super().__init__(parent)
        self.boxes = {k: QCheckBox() for k in range(-7, 8)}
        for k, box in self.boxes.items():  # each key is labelled with its signature, as written after a treble clef
            description = f"{MAJOR_KEYS[k]} major, {_key_label(k).split('·')[1].strip()}"
            _label_with_picture(box, KeySignaturePicture(k, 1.15), description)
        # Two framed groups: C major on its own, and the keys with sharps or flats (flats left, sharps right).
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        natural = QFrame()
        natural.setObjectName("keyGroup")  # styled in style.py
        natural_lay = QVBoxLayout(natural)
        natural_lay.addWidget(self.boxes[0])
        outer.addWidget(natural)
        marked = QFrame()
        marked.setObjectName("keyGroup")
        grid = QGridLayout(marked)
        for n in range(1, 8):
            grid.addWidget(self.boxes[-n], n - 1, 0)
            grid.addWidget(self.boxes[n], n - 1, 1)
        outer.addWidget(marked)
        for k, box in self.boxes.items():
            box.setChecked(k in selected)
            box.toggled.connect(self._toggled)
        _guard_last(list(self.boxes.values()))

    def selected(self) -> set[int]:
        return {k for k, box in self.boxes.items() if box.isChecked()}

    def _toggled(self):
        _guard_last(list(self.boxes.values()))
        self.changed.emit()


class KeySignaturePage(QWidget):
    """The key-signature sub-page: a switch for using key signatures at all, and the keys to draw from."""

    changed = Signal()

    def __init__(self, enabled: bool, selected: set[int], parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.switch_row = _ToggleRow("Use key signatures")
        self.switch_row.setOn(enabled)
        self.switch_row.switched.connect(self._switched)
        self.checklist = KeyChecklist(selected)
        self.checklist.changed.connect(self.changed)
        self.checklist.setEnabled(enabled)  # the keys only matter while key signatures are on
        lay.addWidget(self.switch_row)
        lay.addWidget(QLabel("Draw from these keys:"))
        lay.addWidget(self.checklist)

    def enabled(self) -> bool:
        return self.switch_row.isOn()

    def selected(self) -> set[int]:
        return self.checklist.selected()

    def _switched(self, on: bool):
        self.checklist.setEnabled(on)
        self.changed.emit()


class KeyboardSettingsPanel(ExerciseSettingsPanel):
    """Settings for the keyboard exercise: a menu (Range, Black keys, Octave number) with a page for the range.
    Edits are live; emits `changed` after each one."""

    def __init__(self, cfg: settings.KeyboardSettings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.range_row = _Row("Range", tall=True)
        self.range_row.clicked.connect(lambda: self._go(1))
        self.range_keyboard = KeyboardSpan(compact=True, size=(ROW_PICTURE_WIDTH, 36))  # the asked span, lit on a miniature piano
        self.range_row.attach(self.range_keyboard)
        self.black_keys_row = _ToggleRow("Black keys")
        self.black_keys_row.setToolTip("Also ask the black keys, answered by either of their names")
        self.black_keys_row.setOn(cfg.black_keys)
        self.black_keys_row.switched.connect(self._black_keys_toggled)
        self.octave_row = _ToggleRow("Octave number")
        self.octave_row.setToolTip("Answer with the octave as well, for example C4")
        self.octave_row.setOn(cfg.require_octave)
        self.octave_row.switched.connect(self._octave_toggled)
        self.keys_row = _Row("Key signatures")  # opens a page: use them or not, and which keys
        self.keys_row.setToolTip("Show a key signature above the keyboard and require the name that fits it")
        self.keys_row.clicked.connect(lambda: self._go(2))
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        for row in (self.range_row, self.black_keys_row, self.octave_row, self.keys_row):
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: range
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(10)
        blay.addWidget(QLabel("Keys that will be asked: click and drag on the keyboard to choose them."))
        self.span = KeyboardSpan()
        self.span.dragged.connect(self._set_range)
        blay.addWidget(self.span)
        self.low_label, self.high_label = QLabel(), QLabel()
        self.arrows = {}
        for title, label, which in (("Lowest key", self.low_label, "low"), ("Highest key", self.high_label, "high")):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{title}</b>"), 1)
            down = _arrow(Qt.ArrowType.LeftArrow, f"{title}: one key down")
            up = _arrow(Qt.ArrowType.RightArrow, f"{title}: one key up")
            down.clicked.connect(lambda _=False, w=which: self._step(w, -1))
            up.clicked.connect(lambda _=False, w=which: self._step(w, 1))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumWidth(48)
            row.addWidget(down)
            row.addWidget(label)
            row.addWidget(up)
            blay.addLayout(row)
            self.arrows[which] = (down, up)
        self.entire = QPushButton("Entire keyboard")
        self.entire.clicked.connect(lambda: self._set_range(*settings.KEYBOARD_FULL))
        self.default = QPushButton("Reset to default")
        self.default.clicked.connect(lambda: self._set_range(*settings.KEYBOARD_DEFAULT))
        blay.addWidget(self.entire)
        blay.addWidget(self.default)
        range_page = _subpage("Range", body, lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", self.key_page, lambda: self._go(0))

        self.stack.addWidget(menu)
        self.stack.addWidget(range_page)
        self.stack.addWidget(keys_page)
        self._refresh_range()
        self._show_keys()

    def _go(self, index: int):
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        self.stack.slide_to(index)

    def _refresh_range(self):
        cfg = self.cfg
        self.low_label.setText(key_name(cfg.low))
        self.high_label.setText(key_name(cfg.high))
        self.span.set_span(cfg.low, cfg.high)
        first, last = settings.KEYBOARD_FULL
        self.arrows["low"][0].setEnabled(cfg.low > first)
        self.arrows["low"][1].setEnabled(cfg.low < cfg.high)  # the lowest key can't pass the highest
        self.arrows["high"][0].setEnabled(cfg.high > cfg.low)
        self.arrows["high"][1].setEnabled(cfg.high < last)
        self.range_keyboard.set_span(cfg.low, cfg.high)
        self.range_keyboard.setToolTip(f"{key_name(cfg.low)} to {key_name(cfg.high)}")

    def _step(self, which: str, delta: int):
        low, high = self.cfg.low, self.cfg.high
        first, last = settings.KEYBOARD_FULL
        if which == "low":
            low = min(max(low + delta, first), high)
        else:
            high = max(min(high + delta, last), low)
        self._set_range(low, high)

    def _set_range(self, low: int, high: int):
        if (low, high) == (self.cfg.low, self.cfg.high):
            return
        self.cfg.low, self.cfg.high = low, high
        self._refresh_range()
        self._save_and_emit()

    def _black_keys_toggled(self, on: bool):
        self.cfg.black_keys = on
        self._save_and_emit()

    def _octave_toggled(self, on: bool):
        self.cfg.require_octave = on
        self._save_and_emit()

    def _show_keys(self):
        _show_keys(self.keys_row, self.keys_diagram, self.cfg.key_signature, set(self.cfg.active_keys()))

    def _keys_edited(self):
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        self._show_keys()
        self._save_and_emit()

    def _save_and_emit(self):
        save_keyboard()
        self.changed.emit()


def load_construction() -> None:
    saved_settings = store()
    cfg = settings.construction
    saved = saved_settings.value("construction/clefs")
    if saved is not None:
        text = saved if isinstance(saved, str) else ",".join(saved)
        cfg.clefs = {c for c in text.split(",") if c in settings.RANGE_KEYS} or cfg.clefs
    cfg.accidentals = str(saved_settings.value("construction/accidentals", "false")).lower() == "true"
    cfg.key_signature = str(saved_settings.value("construction/keySignature", "false")).lower() == "true"
    keys = str(saved_settings.value("construction/keys", "") or "")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class NoteConstructionSettingsPanel(ExerciseSettingsPanel):
    """Settings for the note-construction exercise: a menu (Staff, Accidentals, Key signature, Keys) with a page for
    the staff choices and one for the keys. Edits are live; emits `changed` after each one."""

    def __init__(self, cfg: settings.ConstructionSettings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.staff_row = _Row("Staff")
        self.staff_row.clicked.connect(lambda: self._go(1))
        self.clef_pictures = ClefPictures()
        self.staff_row.attach(self.clef_pictures)
        self.accidentals_row = _ToggleRow("Accidentals")
        self.accidentals_row.setToolTip("Also ask for sharps and flats")
        self.accidentals_row.setOn(cfg.accidentals)
        self.accidentals_row.switched.connect(self._accidentals_toggled)
        self.keys_row = _Row("Key signatures")  # opens a page: use them or not, and which keys
        self.keys_row.setToolTip("Draw a key signature that applies to the note")
        self.keys_row.clicked.connect(lambda: self._go(2))
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        for row in (self.staff_row, self.accidentals_row, self.keys_row):
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: staff choices
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("One of the checked choices is picked at random.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        blay.addWidget(hint)
        self.boxes = {c: _clef_box(c) for c in settings.RANGE_KEYS}
        for c, box in self.boxes.items():
            box.setChecked(c in cfg.clefs)
            box.toggled.connect(self._clefs_edited)
        blay.addWidget(_clef_list(self.boxes))
        _guard_last(list(self.boxes.values()))
        staff_page = _subpage("Staff", body, lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", self.key_page, lambda: self._go(0))

        for page in (menu, staff_page, keys_page):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int):
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self):
        self.clef_pictures.set_clefs(self.cfg.active_clefs())
        self._show_keys()

    def _save_and_emit(self):
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("construction/clefs", ",".join(c for c in settings.RANGE_KEYS if c in cfg.clefs))
        saved_settings.setValue("construction/accidentals", "true" if cfg.accidentals else "false")
        saved_settings.setValue("construction/keySignature", "true" if cfg.key_signature else "false")
        saved_settings.setValue("construction/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _clefs_edited(self):
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))  # the last checked choice can't be unchecked
        self._save_and_emit()

    def _accidentals_toggled(self, on: bool):
        self.cfg.accidentals = on
        self._save_and_emit()

    def _show_keys(self):
        _show_keys(self.keys_row, self.keys_diagram, self.cfg.key_signature, set(self.cfg.active_keys()))

    def _keys_edited(self):
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        self._show_keys()
        self._save_and_emit()


def load_arpeggio() -> None:
    saved_settings = store()
    cfg = settings.arpeggio
    clefs = str(saved_settings.value("arpeggio/clefs", "") or "")
    if clefs:
        cfg.clefs = {c for c in clefs.split(",") if c in CLEFS} or cfg.clefs
    types = str(saved_settings.value("arpeggio/types", "") or "")
    if types:
        cfg.types = {t for t in types.split(",") if t in settings.ARPEGGIO_TYPES} or cfg.types
    inversions = str(saved_settings.value("arpeggio/inversions", "") or "")
    if inversions:
        found = {int(i) for i in inversions.split(",") if i.isdigit() and int(i) in settings.INVERSIONS}
        cfg.inversions = found or cfg.inversions
    cfg.key_signature = str(saved_settings.value("arpeggio/keySignature", "false")).lower() == "true"
    keys = str(saved_settings.value("arpeggio/keys", "") or "")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class ChoiceChecklist(QWidget):
    """Checkboxes for a list of choices, optionally under small headings. At least one stays checked."""

    changed = Signal()

    def __init__(self, groups: list[tuple[str, list[tuple[object, str]]]], selected: set, parent=None):
        super().__init__(parent)
        self.boxes: dict[object, QCheckBox] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        for title, items in groups:
            if title:
                heading = QLabel(title)
                heading.setStyleSheet("color: gray;")
                lay.addWidget(heading)
            for key, label in items:
                box = QCheckBox(label)
                box.setChecked(key in selected)
                box.toggled.connect(self._toggled)
                self.boxes[key] = box
                lay.addWidget(box)
        _guard_last(list(self.boxes.values()))

    def selected(self) -> set:
        return {k for k, box in self.boxes.items() if box.isChecked()}

    def _toggled(self):
        _guard_last(list(self.boxes.values()))
        self.changed.emit()


_INVERSION_SHORT = ("Root", "1st", "2nd", "3rd")


class ArpeggioSettingsPanel(ExerciseSettingsPanel):
    """Settings for the arpeggio exercise: a menu (Staff, Arpeggio types, Inversions, Key signatures) with a page for
    each. Edits are live; emits `changed` after each one."""

    def __init__(self, cfg: settings.ArpeggioSettings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.staff_row = _Row("Staff")
        self.staff_row.clicked.connect(lambda: self._go(1))
        self.clef_pictures = ClefPictures()
        self.staff_row.attach(self.clef_pictures)
        self.types_row = _Row("Arpeggio types")
        self.types_row.clicked.connect(lambda: self._go(2))
        self.inversions_row = _Row("Inversions")
        self.inversions_row.clicked.connect(lambda: self._go(3))
        self.keys_row = _Row("Key signatures")
        self.keys_row.setToolTip("Draw a key signature; the arpeggio then only gets signs where it differs from it")
        self.keys_row.clicked.connect(lambda: self._go(4))
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        for row in (self.staff_row, self.types_row, self.inversions_row, self.keys_row):
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: the staff (the four clefs that have a single staff)
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("One of the checked choices is picked at random.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        blay.addWidget(hint)
        self.boxes = {c: _clef_box(c) for c in CLEFS}
        for c, box in self.boxes.items():
            box.setChecked(c in cfg.clefs)
            box.toggled.connect(self._clefs_edited)
        blay.addWidget(_clef_list(self.boxes))
        _guard_last(list(self.boxes.values()))
        staff_page = _subpage("Staff", body, lambda: self._go(0))

        # layer 2: arpeggio types, and inversions
        self.types = ChoiceChecklist([("Triads", [(t, t.capitalize()) for t in settings.ARPEGGIO_TRIADS]),
                                      ("Seventh chords", [(t, t.capitalize()) for t in settings.ARPEGGIO_SEVENTHS])],
                                     cfg.types)
        self.types.changed.connect(self._types_edited)
        types_page = _subpage("Arpeggio types", self.types, lambda: self._go(0))
        names = settings_inversion_names()
        self.inversions = ChoiceChecklist([("", [(i, names[i]) for i in settings.INVERSIONS])], cfg.inversions)
        self.inversions.changed.connect(self._inversions_edited)
        note = QLabel("A triad has no 3rd inversion, so that choice only applies to seventh chords.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        inv_body = QWidget()
        inv_lay = QVBoxLayout(inv_body)
        inv_lay.setContentsMargins(0, 0, 0, 0)
        inv_lay.addWidget(self.inversions)
        inv_lay.addWidget(note)
        inversions_page = _subpage("Inversions", inv_body, lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", self.key_page, lambda: self._go(0))

        for page in (menu, staff_page, types_page, inversions_page, keys_page):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int):
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self):
        cfg = self.cfg
        self.clef_pictures.set_clefs(cfg.active_clefs())
        types = cfg.active_types()
        self.types_row.value.setText(f"{len(types)} of {len(settings.ARPEGGIO_TYPES)}")
        inversions = cfg.active_inversions()
        self.inversions_row.value.setText("All" if len(inversions) == len(settings.INVERSIONS)
                                          else ", ".join(_INVERSION_SHORT[i] for i in inversions))
        _show_keys(self.keys_row, self.keys_diagram, cfg.key_signature, set(cfg.active_keys()))

    def _save_and_emit(self):
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("arpeggio/clefs", ",".join(cfg.active_clefs()))
        saved_settings.setValue("arpeggio/types", ",".join(cfg.active_types()))
        saved_settings.setValue("arpeggio/inversions", ",".join(str(i) for i in cfg.active_inversions()))
        saved_settings.setValue("arpeggio/keySignature", "true" if cfg.key_signature else "false")
        saved_settings.setValue("arpeggio/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _clefs_edited(self):
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))
        self._save_and_emit()

    def _types_edited(self):
        self.cfg.types = self.types.selected()
        self._save_and_emit()

    def _inversions_edited(self):
        self.cfg.inversions = self.inversions.selected()
        self._save_and_emit()

    def _keys_edited(self):
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        _show_keys(self.keys_row, self.keys_diagram, self.cfg.key_signature, set(self.cfg.active_keys()))
        self._save_and_emit()


def load_key_signatures() -> None:
    saved_settings = store()
    cfg = settings.key_signatures
    questions = str(saved_settings.value("keySignatures/questions", "") or "")
    if questions:
        cfg.questions = {q for q in questions.split(",") if q in settings.KEY_QUESTIONS} or cfg.questions
    clefs = str(saved_settings.value("keySignatures/clefs", "") or "")
    if clefs:
        cfg.clefs = {c for c in clefs.split(",") if c in CLEFS} or cfg.clefs
    modes = str(saved_settings.value("keySignatures/modes", "") or "")
    if modes:
        cfg.modes = {m for m in modes.split("|") if m in settings.KEY_MODES} or cfg.modes
    keys = str(saved_settings.value("keySignatures/keys", "") or "")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class KeySignatureSettingsPanel(ExerciseSettingsPanel):
    """Settings for the key signature exercise: a menu (Questions, Staff, Scales, Key signatures) with a page for each.
    Edits are live; emits `changed` after each one."""

    def __init__(self, cfg: settings.KeySignatureSettings, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.questions_row = _Row("Questions")
        self.staff_row = _Row("Staff")
        self.modes_row = _Row("Scales")
        self.keys_row = _Row("Key signatures")
        self.clef_pictures = ClefPictures()
        self.staff_row.attach(self.clef_pictures)
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        for index, row in enumerate((self.questions_row, self.staff_row, self.modes_row, self.keys_row), 1):
            row.clicked.connect(lambda _=False, i=index: self._go(i))
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: the kinds of question
        self.questions = ChoiceChecklist([("", [(k, v) for k, v in settings.KEY_QUESTIONS.items()])], cfg.questions)
        self.questions.changed.connect(self._questions_edited)
        questions_note = QLabel("A key signature is drawn on a staff and you name its key, or a key is named and you count "
                                "its sharps and flats. One of the checked kinds is picked at random.")
        questions_note.setWordWrap(True)
        questions_note.setStyleSheet("color: gray;")
        questions_body = QWidget()
        qlay = QVBoxLayout(questions_body)
        qlay.setContentsMargins(0, 0, 0, 0)
        qlay.addWidget(self.questions)
        qlay.addWidget(questions_note)
        questions_page = _subpage("Questions", questions_body, lambda: self._go(0))

        # layer 2: the clefs the signature is drawn on
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("One of the checked choices is picked at random.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        blay.addWidget(hint)
        self.boxes = {c: _clef_box(c) for c in CLEFS}
        for c, box in self.boxes.items():
            box.setChecked(c in cfg.clefs)
            box.toggled.connect(self._clefs_edited)
        blay.addWidget(_clef_list(self.boxes))
        _guard_last(list(self.boxes.values()))
        staff_page = _subpage("Staff", body, lambda: self._go(0))

        # layer 2: the scales, so the key can be a major or minor key or a mode
        self.modes = ChoiceChecklist([("", [(m, settings.MODE_LABELS[m]) for m in settings.KEY_MODES])], cfg.modes)
        self.modes.changed.connect(self._modes_edited)
        modes_note = QLabel("A mode has the key signature of a major key and starts from another note of it: D Dorian has "
                            "the signature of C major.")
        modes_note.setWordWrap(True)
        modes_note.setStyleSheet("color: gray;")
        modes_body = QWidget()
        mlay2 = QVBoxLayout(modes_body)
        mlay2.setContentsMargins(0, 0, 0, 0)
        mlay2.addWidget(self.modes)
        mlay2.addWidget(modes_note)
        modes_page = _subpage("Scales", modes_body, lambda: self._go(0))

        # layer 2: the key signatures asked
        self.key_list = KeyChecklist(cfg.keys)
        self.key_list.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", self.key_list, lambda: self._go(0))

        for page in (menu, questions_page, staff_page, modes_page, keys_page):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int):
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self):
        cfg = self.cfg
        questions = cfg.active_questions()
        self.questions_row.value.setText("Both" if len(questions) == len(settings.KEY_QUESTIONS)
                                         else "Read" if questions == ["read"] else "Count")
        self.clef_pictures.set_clefs(cfg.active_clefs())
        modes = cfg.active_modes()
        self.modes_row.value.setText(f"{len(modes)} of {len(settings.KEY_MODES)}")
        _show_keys(self.keys_row, self.keys_diagram, True, set(cfg.active_keys()))

    def _save_and_emit(self):
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("keySignatures/questions", ",".join(cfg.active_questions()))
        saved_settings.setValue("keySignatures/clefs", ",".join(cfg.active_clefs()))
        saved_settings.setValue("keySignatures/modes", "|".join(cfg.active_modes()))
        saved_settings.setValue("keySignatures/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _questions_edited(self):
        self.cfg.questions = self.questions.selected()
        self._save_and_emit()

    def _clefs_edited(self):
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))
        self._save_and_emit()

    def _modes_edited(self):
        self.cfg.modes = self.modes.selected()
        self._save_and_emit()

    def _keys_edited(self):
        self.cfg.keys = self.key_list.selected()
        self._save_and_emit()


def settings_inversion_names() -> tuple[str, ...]:
    """The inversions as written in the settings: 'Root position', '1st inversion' ..."""
    return tuple(n.capitalize() for n in INVERSION_NAMES)


def settings_panel_for(exercise) -> ExerciseSettingsPanel | None:
    """The settings panel for an exercise (has a `changed` signal), or None if it has none."""
    from ..exercises.library import ArpeggioNames, KeyboardNotes, KeySignatures, NoteConstruction, NoteNames

    if isinstance(exercise, NoteNames):
        return NoteNameSettingsPanel(settings.note_names)
    if isinstance(exercise, KeyboardNotes):
        return KeyboardSettingsPanel(settings.keyboard)
    if isinstance(exercise, NoteConstruction):
        return NoteConstructionSettingsPanel(settings.construction)
    if isinstance(exercise, ArpeggioNames):
        return ArpeggioSettingsPanel(settings.arpeggio)
    if isinstance(exercise, KeySignatures):
        return KeySignatureSettingsPanel(settings.key_signatures)
    return None
