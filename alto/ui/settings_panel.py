"""
The settings panels that slide in beside an exercise, and the small widgets they are built from.

Each exercise with settings has a panel: a menu of rows (Clefs, Range, Key signatures ...) that each lead to a page. Edits
are live: they change the shared settings object, are saved, and a `changed` signal tells the exercise to ask a new
question. This module also loads and saves each exercise's settings.

Examples
--------
>>> _key_label(2)
'D  ·  2♯'
>>> row = _Row("Clefs")
>>> row.title.text()
'<b>Clefs</b>'
"""

from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
)

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
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
)
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

from alto import settings
from alto.exercises.base import Exercise
from alto.exercises.library import (
    ArpeggioNames,
    KeyboardNotes,
    KeySignatures,
    NoteConstruction,
    NoteNames,
)
from alto.settings import (
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
from alto.theory.pitch import (
    MAJOR_KEYS,
    Note,
)
from alto.theory.scales import INVERSION_NAMES
from alto.ui.colors import blend
from alto.ui.keyboard import KeyboardSpan
from alto.ui.pictures import (
    CLEF_NAMES,
    VALUE_NAMES,
    ClefPictures,
    KeySignaturePicture,
    NamePicture,
    RangePictures,
    ValuePictures,
    _Picture,
)
from alto.ui.staff import StaffWidget
from alto.ui.store import (
    int_value,
    store,
    text_value,
)


def load_note_names() -> None:
    """
    Load the saved note identification settings into the shared settings object.

    Settings saved by an older version, which had a switch between the grand staff and single clefs, are converted. Anything
    in the saved data that is not valid is ignored.

    Examples
    --------
    >>> cfg_ = settings.note_names
    >>> cfg_.clefs = {"alto"}
    >>> save_note_names()
    >>> cfg_.clefs = {"treble"}
    >>> load_note_names()
    >>> cfg_.clefs
    {'alto'}
    >>> cfg_.clefs = {"treble", "bass"}
    >>> save_note_names()
    """
    s = store()
    cfg = settings.note_names
    saved = s.value("noteNames/clefs")
    if saved is not None:
        text = saved if isinstance(saved, str) else ",".join(saved)
        cfg.clefs = {c for c in text.split(",") if c in settings.RANGE_KEYS}
    if s.value("noteNames/mode") == "grand":  # an older version had a switch between the grand staff and single clefs
        cfg.clefs = {"grand"}
    s.remove("noteNames/mode")
    keys = text_value(s, key="noteNames/keys", default="")
    if keys:
        cfg.key_signatures = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or {0}
    values = text_value(s, key="noteNames/values", default="")
    if values:
        cfg.note_values = {v for v in values.split(",") if v in NOTE_VALUES} or {"whole"}
    naming = text_value(s, key="noteNames/naming", default=cfg.naming)
    cfg.naming = naming if naming in NAMINGS else "letters"
    cfg.accidentals = text_value(s, key="noteNames/accidentals", default="false").lower() == "true"
    cfg.ranges = {}
    for item in text_value(s, key="noteNames/ranges", default="").split(","):  # e.g. "treble:31-33,bass:14-28"
        try:
            key, span = item.split(":")
            lo, hi = (int(x) for x in span.split("-"))
        except ValueError:
            continue
        if key in DEFAULT_RANGES and MIN_DIATONIC <= lo <= hi <= MAX_DIATONIC:
            cfg.ranges[key] = (lo, hi)


def save_note_names() -> None:
    """
    Save the note identification settings.

    Examples
    --------
    >>> cfg_ = settings.note_names
    >>> cfg_.naming = "solfege"
    >>> save_note_names()
    >>> str(store().value("noteNames/naming"))
    'solfege'
    >>> cfg_.naming = "letters"
    >>> save_note_names()
    """
    s = store()
    cfg = settings.note_names
    s.setValue("noteNames/clefs", ",".join(c for c in settings.RANGE_KEYS if c in cfg.clefs))
    s.setValue("noteNames/keys", ",".join(str(k) for k in cfg.active_keys()))
    s.setValue("noteNames/values", ",".join(cfg.active_values()))
    s.setValue("noteNames/naming", cfg.naming)
    s.setValue("noteNames/accidentals", "true" if cfg.accidentals else "false")
    s.setValue("noteNames/ranges", ",".join(f"{k}:{lo}-{hi}" for k, (lo, hi) in cfg.ranges.items()))


def _guard_last(
    boxes: Iterable[QAbstractButton],
    *,
    enabled: bool = True,
) -> None:
    """
    Disable the only checked box, so that at least one choice always stays selected.

    Parameters
    ----------
    boxes : iterable of QAbstractButton
        The checkboxes of one choice.
    enabled : bool, default True
        False disables them all (for when the whole choice is switched off). Keyword-only.

    Examples
    --------
    >>> first, second = QCheckBox(), QCheckBox()
    >>> first.setChecked(True)
    >>> _guard_last([first, second])
    >>> first.isEnabled(), second.isEnabled()
    (False, True)
    >>> second.setChecked(True)
    >>> _guard_last([first, second])
    >>> first.isEnabled()
    True
    """
    checked = [b for b in boxes if b.isChecked()]
    for box in boxes:
        box.setEnabled(enabled and not (len(checked) == 1 and box.isChecked()))


def _key_label(count: int) -> str:
    """
    Label a key signature with its key and its accidentals.

    Parameters
    ----------
    count : int
        Sharps if positive, flats if negative.

    Returns
    -------
    str
        For example 'D  ·  2♯', 'E♭  ·  3♭' or 'C  ·  none'.

    Examples
    --------
    >>> _key_label(0), _key_label(2), _key_label(-3)
    ('C  ·  none', 'D  ·  2♯', 'E♭  ·  3♭')
    """
    return f"{MAJOR_KEYS[count]}  ·  " + ("none" if count == 0 else f"{abs(count)}{'♯' if count > 0 else '♭'}")


def _arrow(
    kind: Qt.ArrowType,
    *,
    tip: str,
) -> QToolButton:
    """
    Make a small arrow button that repeats while it is held.

    Parameters
    ----------
    kind : Qt.ArrowType
        Which way the arrow points.
    tip : str
        The tooltip. Keyword-only.

    Returns
    -------
    QToolButton
        The button.

    Examples
    --------
    >>> button = _arrow(Qt.ArrowType.UpArrow, tip="Raise the lowest note")
    >>> button.toolTip(), button.autoRepeat()
    ('Raise the lowest note', True)
    """
    btn = QToolButton()
    btn.setArrowType(kind)
    btn.setProperty("arrowButton", True)  # styled with a visible border (see style.py)
    btn.setToolTip(tip)
    btn.setAutoRepeat(True)
    btn.setAutoRepeatDelay(350)
    btn.setAutoRepeatInterval(90)
    return btn


class RangeEditor(QWidget):
    """
    A staff showing the lowest and highest note asked for a clef.

    Arrows on the left move the lower bound, arrows on the right move the upper bound.

    Attributes
    ----------
    edited : Signal
        Emitted with the clef key, the lowest note and the highest note (as staff steps) after a change.
    key : str
        The clef.
    low : int
        The lowest note asked, as a staff step (`Note.diatonic`).
    high : int
        The highest note asked.
    limits : tuple of (int, int)
        The furthest the bounds may go.
    staff : StaffWidget
        Shows the two notes.

    Examples
    --------
    >>> editor = RangeEditor("treble", low=28, high=34)
    >>> editor.caption_text.text()
    '<b>C4 – B4</b>'
    """

    edited = Signal(str, int, int)  # clef key, low, high (diatonic)

    def __init__(
        self,
        key: str,
        *,
        low: int,
        high: int,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the editor for a clef's range.

        Parameters
        ----------
        key : str
            The clef, a key of `RANGE_LIMITS`.
        low : int
            The lowest note asked, as a staff step. Keyword-only.
        high : int
            The highest note asked. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the editor. Keyword-only.

        Examples
        --------
        >>> RangeEditor("bass", low=14, high=28).limits == settings.RANGE_LIMITS["bass"]
        True
        """
        super().__init__(parent)
        self.key, self.low, self.high = key, low, high
        self.limits = RANGE_LIMITS[key]
        self.caption_text = QLabel()
        self.caption_text.setStyleSheet("font-size: 12pt;")
        self.caption = QWidget()  # the clef as a picture, then the lowest and highest note
        caption_row = QHBoxLayout(self.caption)
        caption_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        caption_row.addWidget(ClefPictures([key], scale=0.9))
        caption_row.addWidget(self.caption_text)
        caption_row.addStretch()
        self.staff = StaffWidget(
            gap=9.0,
            side=18.0,
            note_offset=62.0,
            margin=8.0,
            compact=True,
        )
        self.staff.setFixedWidth(168)
        self.low_up = _arrow(Qt.ArrowType.UpArrow, tip="Raise the lowest note")
        self.low_down = _arrow(Qt.ArrowType.DownArrow, tip="Lower the lowest note")
        self.high_up = _arrow(Qt.ArrowType.UpArrow, tip="Raise the highest note")
        self.high_down = _arrow(Qt.ArrowType.DownArrow, tip="Lower the highest note")
        self.low_up.clicked.connect(lambda: self._move(low=1))
        self.low_down.clicked.connect(lambda: self._move(low=-1))
        self.high_up.clicked.connect(lambda: self._move(high=1))
        self.high_down.clicked.connect(lambda: self._move(high=-1))

        row = QHBoxLayout()
        row.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        lay.setContentsMargins(
            0,
            8,
            0,
            16,
        )  # space between one clef's block and the next
        lay.setSpacing(8)
        lay.addWidget(self.caption)
        lay.addLayout(row)
        self._refresh()

    def _move(
        self,
        low: int = 0,
        *,
        high: int = 0,
    ) -> None:
        """
        Move the bounds by steps, keeping the lower below the upper and both within the limits.

        Parameters
        ----------
        low : int, default 0
            How many staff steps to move the lower bound; positive is higher.
        high : int, default 0
            How many steps to move the upper bound. Keyword-only.

        Examples
        --------
        >>> editor = RangeEditor("treble", low=28, high=34)
        >>> got = []
        >>> _ = editor.edited.connect(lambda key, lo, hi: got.append((key, lo, hi)))
        >>> editor._move(low=1)
        >>> got
        [('treble', 29, 34)]
        >>> editor._move(low=100)  # the lower bound cannot pass the upper
        >>> editor.low
        34
        """
        self.low = min(max(self.low + low, self.limits[0]), self.high)  # the lower bound can't pass the upper
        self.high = max(min(self.high + high, self.limits[1]), self.low)
        self._refresh()
        self.edited.emit(self.key, self.low, self.high)

    def _refresh(self) -> None:
        """
        Show the bounds on the staff and in the caption, and enable only the arrows that can still move.

        Examples
        --------
        >>> editor = RangeEditor("treble", low=22, high=30)  # 22 is the lowest the treble range goes
        >>> editor._refresh()
        >>> editor.low_down.isEnabled(), editor.low_up.isEnabled()
        (False, True)
        """
        self.caption_text.setText(f"<b>{diatonic_name(self.low)} – {diatonic_name(self.high)}</b>")
        self.staff.show_notes([[Note.from_diatonic(self.low)], [Note.from_diatonic(self.high)]], clef=self.key)
        self.low_up.setEnabled(self.low < self.high)
        self.low_down.setEnabled(self.low > self.limits[0])
        self.high_up.setEnabled(self.high < self.limits[1])
        self.high_down.setEnabled(self.high > self.low)


class KeyDiagram(QWidget):
    """
    A small fork showing which key signatures are selected.

    C major is on the left, then two rows of seven dots: 1 to 7 sharps on the top row and 1 to 7 flats on the bottom.
    Selected keys are filled, the rest are hollow.

    Attributes
    ----------
    DOT, PITCH, ROW_GAP, PAD : float
        The dot radius and the spacing, in pixels.
    keys : set of int
        The selected key signatures: sharps if positive, flats if negative.

    Examples
    --------
    >>> KeyDiagram({0, 2}).toolTip()
    'C, D'
    """

    DOT, PITCH, ROW_GAP, PAD = 4.4, 12.6, 13.0, 1.5  # dot radius and spacing, in pixels

    def __init__(
        self,
        keys: set[int] | None = None,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the diagram.

        Parameters
        ----------
        keys : set of int or None, default None
            The key signatures to show as selected.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> KeyDiagram().keys
        set()
        """
        super().__init__(parent)
        self.keys: set[int] = set(keys or ())
        self.first_column = self.PAD + 2 * self.DOT + 7 + self.DOT  # x of the 1-sharp / 1-flat dots
        self.setFixedSize(
            int(self.first_column + 6 * self.PITCH + self.DOT + self.PAD) + 1,
            int(self.ROW_GAP + 2 * self.DOT + 2 * self.PAD) + 3,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row underneath is the click target
        self._update_tip()

    def set_keys(self, keys: set[int]) -> None:
        """
        Choose which key signatures are shown as selected.

        Parameters
        ----------
        keys : set of int
            Sharps if positive, flats if negative.

        Examples
        --------
        >>> diagram = KeyDiagram()
        >>> diagram.set_keys({2, -1, 0})
        >>> diagram.toolTip()
        'C, D, F'
        """
        self.keys = set(keys)
        self._update_tip()
        self.update()

    def _update_tip(self) -> None:
        """
        Set the tooltip to the names of the selected keys, sharp keys first.

        Examples
        --------
        >>> diagram = KeyDiagram({3, 1})
        >>> diagram._update_tip()
        >>> diagram.toolTip()
        'G, A'
        """
        names = [MAJOR_KEYS[k] for k in sorted(self.keys, key=lambda k: (k < 0, abs(k)))]
        self.setToolTip(", ".join(names))

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw a dot for each key signature, filled when selected.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> KeyDiagram({0, 1, -1}).grab().isNull()
        False
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        text = pal.color(QPalette.ColorRole.Text)
        base = pal.color(QPalette.ColorRole.Base)  # the row is filled with the base colour

        def shade(t: float) -> QColor:  # t of the way from the row's background to the text colour
            """
            Return a colour a fraction of the way from the row's background to the text colour.

            Parameters
            ----------
            t : float
                0 for the background, 1 for the text colour.

            Returns
            -------
            QColor
                The blended colour.

            Examples
            --------
            >>> shade(0.5)  # doctest: +SKIP
            """
            return blend(base, b=text, t=t)

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


def _label_with_picture(
    button: QAbstractButton,
    *,
    picture: _Picture,
    name: str,
) -> None:
    """
    Label a checkbox or radio button with a picture instead of text.

    The name stays as the tooltip and the accessible name.

    Parameters
    ----------
    button : QAbstractButton
        The button to label.
    picture : _Picture
        The picture (a clef, a note value ...). Keyword-only.
    name : str
        What it is called. Keyword-only.

    Examples
    --------
    >>> box = QCheckBox()
    >>> _label_with_picture(box, picture=ClefPictures(["treble"]), name="Treble")
    >>> box.toolTip(), box.accessibleName()
    ('Treble', 'Treble')
    """
    button.setIcon(picture.to_icon())
    button.setIconSize(picture.size())
    button.setToolTip(name)
    button.setAccessibleName(name)


def _label_with_clef(
    button: QAbstractButton,
    *,
    clef: str,
    scale: float = 1.4,
) -> None:
    """
    Label a button with a clef's picture and its name beside it.

    Parameters
    ----------
    button : QAbstractButton
        The button to label.
    clef : str
        A key of `CLEF_NAMES`. Keyword-only.
    scale : float, default 1.4
        How much to enlarge the picture. Keyword-only.

    Examples
    --------
    >>> box = QCheckBox()
    >>> _label_with_clef(box, clef="mezzo")
    >>> box.text()
    'Mezzo-soprano'
    """
    _label_with_picture(button, picture=ClefPictures([clef], scale=scale), name=CLEF_NAMES[clef])
    button.setText(CLEF_NAMES[clef])


def _clef_box(
    clef: str,
    *,
    scale: float = 1.4,
) -> QCheckBox:
    """
    Make a checkbox for a clef, with its picture and name.

    Parameters
    ----------
    clef : str
        A key of `CLEF_NAMES`.
    scale : float, default 1.4
        How much to enlarge the picture. Keyword-only.

    Returns
    -------
    QCheckBox
        The checkbox.

    Examples
    --------
    >>> _clef_box("alto").text()
    'Alto'
    """
    box = QCheckBox()
    _label_with_clef(box, clef=clef, scale=scale)
    return box


def _clef_list(boxes: dict[str, QCheckBox]) -> QWidget:
    """
    Lay the clef checkboxes out one under another, in three groups divided by a line.

    The groups are the grand staff; the treble, bass, alto and tenor clefs; and the soprano, mezzo-soprano and baritone
    clefs. A group none of the boxes belong to is left out. The list is indented under its heading.

    Parameters
    ----------
    boxes : dict of str to QCheckBox
        The checkbox of each clef.

    Returns
    -------
    QWidget
        The list.

    Examples
    --------
    >>> boxes_ = {clef: _clef_box(clef) for clef in ("treble", "bass", "soprano")}
    >>> widget_ = _clef_list(boxes_)
    >>> # noinspection PyUnresolvedReferences
    >>> widget_.layout().count()  # two boxes_, a dividing line, and one box
    4
    """
    widget = QWidget()
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(
        24,
        0,
        0,
        0,
    )
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


def _show_keys(
    row: _Row,
    *,
    diagram: KeyDiagram,
    enabled: bool,
    keys: set[int],
) -> None:
    """
    Show the selected keys as a diagram in a menu row, or "Off" when key signatures are switched off.

    Parameters
    ----------
    row : _Row
        The menu row.
    diagram : KeyDiagram
        The diagram to update. Keyword-only.
    enabled : bool
        Whether key signatures are on. Keyword-only.
    keys : set of int
        The selected key signatures. Keyword-only.

    Examples
    --------
    >>> row_, diagram_ = _Row("Key signatures"), KeyDiagram()
    >>> _show_keys(row_, diagram=diagram_, enabled=False, keys={0})
    >>> row_.value.text(), diagram_.isHidden()
    ('Off', True)
    """
    diagram.set_keys(keys)
    diagram.setVisible(enabled)
    row.value.setText("" if enabled else "Off")


class _Row(QPushButton):
    """
    A menu row: title on the left, current value and a chevron on the right.

    A `tall` row puts a picture on a second line of its own, using the full width, for summaries that need room to be
    readable.

    Attributes
    ----------
    tall : bool
        Whether the row has a second line.
    title : QLabel
        The title.
    value : QLabel
        The current value, shown on the right.

    Examples
    --------
    >>> row = _Row("Range", tall=True)
    >>> row.tall, row.title.text()
    (True, '<b>Range</b>')
    """

    def __init__(
        self,
        title: str,
        *,
        chevron: bool = True,
        tall: bool = False,
    ) -> None:
        """
        Build the row.

        Parameters
        ----------
        title : str
            The row's title.
        chevron : bool, default True
            Show a chevron on the right, to say it opens a page. Keyword-only.
        tall : bool, default False
            Give the row a second line for a picture. Keyword-only.

        Examples
        --------
        >>> _Row("Clefs").minimumHeight()
        48
        """
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
            outer.setContentsMargins(
                11,
                8,
                11,
                8,
            )
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
        lay.setContentsMargins(
            11,
            4,
            11,
            4,
        )  # leaves room for a small diagram in the row
        lay.addWidget(self.title)
        lay.addWidget(self.value, 1)
        if chevron:
            lay.addWidget(arrow)

    def attach(self, widget: QWidget) -> None:
        """
        Put a widget in the row.

        Just after the value text, or (in a tall row) centred on its own line below.

        Parameters
        ----------
        widget : QWidget
            The widget, usually a small picture of the current choice.

        Examples
        --------
        >>> row = _Row("Clefs")
        >>> picture = ClefPictures(["treble"])
        >>> row.attach(picture)
        >>> # noinspection PyUnresolvedReferences
        >>> row.layout().indexOf(picture)
        2
        """
        if self.tall:
            self._below.addStretch()
            self._below.addWidget(widget)
            self._below.addStretch()
            self.fit()
        else:
            self._contents.insertWidget(2, widget)

    def fit(self) -> None:
        """
        Make a tall row as high as its contents need.

        A button does not size itself to a layout inside it.

        Examples
        --------
        >>> row = _Row("Range", tall=True)
        >>> row.attach(QLabel("a picture"))
        >>> row.minimumHeight() > 0
        True
        """
        if self.tall:
            self.setMinimumHeight(self._contents.minimumSize().height())


class Switch(QAbstractButton):
    """
    A pill-shaped on/off switch whose knob slides across when toggled.

    Attributes
    ----------
    W, H : int
        The switch's size, in pixels.

    Examples
    --------
    >>> switch = Switch()
    >>> switch.setChecked(True)
    >>> switch.isChecked()
    True
    """

    W, H = 42, 24

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create a switch that is off.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns it.

        Examples
        --------
        >>> Switch().isChecked()
        False
        """
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

    def _set_pos(self, value: float) -> None:
        """
        Move the knob.

        Parameters
        ----------
        value : float
            0 for off up to 1 for on, with values between while it slides.

        Examples
        --------
        >>> switch = Switch()
        >>> switch._set_pos(0.5)
        >>> switch._pos
        0.5
        """
        self._pos = float(value)
        self.update()

    def _slide(self, on: bool) -> None:
        """
        Slide the knob to on or off.

        Parameters
        ----------
        on : bool
            Where the knob is going.

        Examples
        --------
        >>> switch = Switch()
        >>> switch._slide(True)
        >>> switch._anim.endValue()
        1.0
        """
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setChecked(self, on: bool) -> None:  # no animation when set programmatically
        """
        Turn the switch on or off without animating, as when a setting is loaded.

        Parameters
        ----------
        on : bool
            The new state.

        Examples
        --------
        >>> switch = Switch()
        >>> switch.setChecked(True)
        >>> switch._pos
        1.0
        """
        super().setChecked(on)
        self._anim.stop()
        self._set_pos(1.0 if on else 0.0)

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the track, tinted between off and on, and the knob.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> Switch().grab().isNull()
        False
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        off, on = pal.color(QPalette.ColorRole.Mid), pal.color(QPalette.ColorRole.Highlight)
        track = blend(off, b=on, t=self._pos)
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(self.rect(), self.H / 2, self.H / 2)
        r, margin = self.H / 2 - 3, 3
        x = margin + r + self._pos * (self.W - 2 * (margin + r))
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(x, self.H / 2), r, r)

    def sizeHint(self) -> QSize:
        """
        Return the switch's fixed size.

        Returns
        -------
        QSize
            `W` by `H`.

        Examples
        --------
        >>> Switch().sizeHint()
        PySide6.QtCore.QSize(42, 24)
        """
        return QSize(self.W, self.H)


class _ToggleRow(_Row):
    """
    A menu row with a switch that changes a setting in place instead of opening a page.

    Attributes
    ----------
    switched : Signal
        Emitted with the new state when the row is clicked.
    switch : Switch
        The switch.

    Examples
    --------
    >>> row = _ToggleRow("Accidentals")
    >>> changes = []
    >>> _ = row.switched.connect(changes.append)
    >>> row.click()
    >>> changes, row.isOn()
    ([True], True)
    """

    switched = Signal(bool)

    def __init__(self, title: str) -> None:
        """
        Build the row with its switch off.

        Parameters
        ----------
        title : str
            The row's title.

        Examples
        --------
        >>> _ToggleRow("Accidentals").isOn()
        False
        """
        super().__init__(title, chevron=False)
        self.value.hide()
        self.switch = Switch()
        self.switch.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the whole row is the click target
        self._contents.addWidget(self.switch)
        self.clicked.connect(lambda: self._set(not self.switch.isChecked()))

    def _set(self, on: bool) -> None:
        """
        Set the switch and tell whoever is listening.

        Parameters
        ----------
        on : bool
            The new state.

        Examples
        --------
        >>> row = _ToggleRow("Accidentals")
        >>> changes = []
        >>> _ = row.switched.connect(changes.append)
        >>> row._set(True)
        >>> changes
        [True]
        """
        self.switch.setChecked(on)
        self.switch.update()
        self.switched.emit(on)

    # noinspection PyPep8Naming
    def isOn(self) -> bool:
        """
        Report whether the switch is on.

        Returns
        -------
        bool
            True if on.

        Examples
        --------
        >>> _ToggleRow("Accidentals").isOn()
        False
        """
        return self.switch.isChecked()

    # noinspection PyPep8Naming
    def setOn(self, on: bool) -> None:
        """
        Set the switch without announcing it, as when a setting is loaded.

        Parameters
        ----------
        on : bool
            The new state.

        Examples
        --------
        >>> row = _ToggleRow("Accidentals")
        >>> row.setOn(True)
        >>> row.isOn()
        True
        """
        self.switch.setChecked(on)


def _subpage(
    title: str,
    *,
    body: QWidget,
    back: Callable[[], object],
    fill: bool = False,
) -> QWidget:
    """
    Build a second-layer page: a Back button and title above a body.

    Parameters
    ----------
    title : str
        The page's title.
    body : QWidget
        What the page shows. Keyword-only.
    back : callable
        Called when Back is clicked. Keyword-only.
    fill : bool, default False
        Let the body take all the room (so a long page can scroll) instead of leaving space below it. Keyword-only.

    Returns
    -------
    QWidget
        The page.

    Examples
    --------
    >>> calls = []
    >>> page_ = _subpage("Clefs", body=QWidget(), back=lambda: calls.append("back"))
    >>> next(b for b in page_.findChildren(QToolButton) if b.text() == "‹ Back").click()
    >>> calls
    ['back']
    """
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(
        0,
        0,
        0,
        0,
    )
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
    """
    A stacked widget whose pages slide in from the right (going deeper) or the left (going back).

    Examples
    --------
    >>> stack = SlideStack()
    >>> _ = stack.addWidget(QWidget())
    >>> _ = stack.addWidget(QWidget())
    >>> stack.sliding
    False
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create an empty stack.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns it.

        Examples
        --------
        >>> SlideStack().count()
        0
        """
        super().__init__(parent)
        self._slide: QParallelAnimationGroup | None = None

    @property
    def sliding(self) -> bool:
        """
        Report whether a page is sliding in.

        Returns
        -------
        bool
            True from the start of a slide until it finishes.

        Examples
        --------
        >>> SlideStack().sliding
        False
        """
        return self._slide is not None

    def slide_to(self, index: int) -> None:
        """
        Slide to another page.

        Going to a later page slides it in from the right and going back slides it in from the left. A request made during a
        slide, or for the page already showing, is ignored.

        Parameters
        ----------
        index : int
            The page to go to.

        Examples
        --------
        >>> stack = SlideStack()
        >>> _ = stack.addWidget(QWidget())
        >>> _ = stack.addWidget(QWidget())
        >>> stack.slide_to(1)
        >>> stack.sliding
        True
        """
        if self.sliding or index == self.currentIndex():
            return  # ignore requests mid-transition
        old, new = self.currentWidget(), self.widget(index)
        assert old is not None and new is not None
        w = self.width()
        sign = 1 if index > self.currentIndex() else -1
        new.setGeometry(
            0,
            0,
            w,
            self.height(),
        )
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

        def done() -> None:
            """
            Finish the slide: show the new page and put both pages back in place.

            Examples
            --------
            >>> done()  # doctest: +SKIP
            """
            self.setCurrentIndex(index)
            # noinspection PyUnresolvedReferences
            old.move(0, 0)
            # noinspection PyUnresolvedReferences
            new.move(0, 0)
            self._slide = None

        group.finished.connect(done)
        self._slide = group
        group.start()


class ExerciseSettingsPanel(QWidget):
    """
    What every exercise's settings pane has in common: it says when a setting has been edited.

    Attributes
    ----------
    changed : Signal
        Emitted after any setting is edited.

    Examples
    --------
    >>> panel = ExerciseSettingsPanel()
    >>> got = []
    >>> _ = panel.changed.connect(lambda: got.append(1))
    >>> panel.changed.emit()
    True
    >>> got
    [1]
    """

    changed = Signal()


class NoteNameSettingsPanel(ExerciseSettingsPanel):
    """
    The settings of the note identification exercise: a menu leading to a page for each group of settings.

    Two layers: the menu (Clefs, Range, Key signatures, Note values, Note names and an Accidentals switch) and a page for each.
    Edits are live: each changes the settings, saves them and emits `changed`.

    Attributes
    ----------
    cfg : NoteNameSettings
        The settings being edited.
    stack : SlideStack
        The menu and its pages.
    boxes : dict of str to QCheckBox
        The clef checkboxes.
    key_boxes : dict of int to QCheckBox
        The key signature checkboxes.
    value_boxes : dict of str to QCheckBox
        The note value checkboxes.
    naming_radios : dict of str to QRadioButton
        The letters and solfège choices.
    range_editors : dict of str to RangeEditor
        The range editor of each clef in use, built when the Range page opens.

    Examples
    --------
    >>> panel = NoteNameSettingsPanel(NoteNameSettings())
    >>> panel.cfg.active_clefs()
    ['treble', 'bass']
    """

    def __init__(
        self,
        cfg: NoteNameSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the panel for a set of settings.

        Parameters
        ----------
        cfg : NoteNameSettings
            The settings to edit.
        parent : QWidget or None, default None
            The widget that owns the panel. Keyword-only.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel.stack.count()  # the menu and five pages
        6
        """
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        for index, row in enumerate(
            (
                self.clefs_row,
                self.range_row,
                self.keys_row,
                self.values_row,
                self.names_row,
            ),
            1,
        ):
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
        blay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        clefs_page = _subpage("Clefs", body=body, back=lambda: self._go(0))

        # layer 2: range
        self.range_body = QWidget()
        self.range_lay = QVBoxLayout(self.range_body)
        self.range_lay.setContentsMargins(
            6,
            4,
            10,
            8,
        )
        self.range_editors: dict[str, RangeEditor] = {}
        scroll = QScrollArea()
        scroll.setWidget(self.range_body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        range_page = _subpage(
            "Range",
            body=scroll,
            back=lambda: self._go(0),
            fill=True,
        )

        # layer 2: key signatures, each drawn as it would be written (flats on the left, sharps on the right)
        self.key_list = KeyChecklist(cfg.key_signatures)
        self.key_list.changed.connect(self._keys_edited)
        self.key_boxes = self.key_list.boxes
        keys_page = _subpage("Key signatures", body=self.key_list, back=lambda: self._go(0))

        # layer 2: note values, a vertical list: the engraved symbol, then its name
        self.value_boxes = {v: QCheckBox(VALUE_NAMES[v]) for v in NOTE_VALUES}
        values_body = QWidget()
        vlay = QVBoxLayout(values_body)
        vlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        vlay.setSpacing(2)
        values_hint = QLabel("One of the checked values is picked at random.")
        values_hint.setWordWrap(True)
        vlay.addWidget(values_hint)
        for v, box in self.value_boxes.items():
            picture = ValuePictures([v], scale=1.25, centre_stemless=True)
            box.setIcon(picture.to_icon())
            box.setIconSize(picture.size())
            box.setStyleSheet("QCheckBox { font-size: 11pt; }")
            box.setChecked(v in cfg.note_values)
            box.toggled.connect(self._values_edited)
            vlay.addWidget(box)
        vlay.addStretch()
        values_page = _subpage("Note values", body=values_body, back=lambda: self._go(0))

        # layer 2: note names
        self.naming_radios = {k: QRadioButton() for k in NAMINGS}
        for k, radio in self.naming_radios.items():
            _label_with_picture(radio, picture=NamePicture(k, scale=1.6), name=NAMINGS[k])
        names_body = QWidget()
        nlay = QVBoxLayout(names_body)
        nlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        naming_group = QButtonGroup(self)
        for k, radio in self.naming_radios.items():
            naming_group.addButton(radio)
            radio.setChecked(k == cfg.naming)
            radio.toggled.connect(self._names_edited)
            nlay.addWidget(radio)
        names_page = _subpage("Note names", body=names_body, back=lambda: self._go(0))

        for page in (
            menu,
            clefs_page,
            range_page,
            keys_page,
            values_page,
            names_page,
        ):
            self.stack.addWidget(page)
        _guard_last(list(self.key_boxes.values()))
        _guard_last(list(self.value_boxes.values()))
        self._refresh_summaries()

    # navigation
    def _go(self, index: int) -> None:
        """
        Slide to a page, refreshing it first.

        Going back to the menu refreshes its summaries; going to the Range page builds its rows. A request made during a slide is
        ignored.

        Parameters
        ----------
        index : int
            0 for the menu, 1 for Clefs, 2 for Range, then Key signatures, Note values and Note names.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel._go(2)
        >>> sorted(panel.range_editors), panel.stack.sliding
        (['bass', 'treble'], True)
        """
        if self.stack.sliding or index == self.stack.currentIndex():
            return  # ignore clicks mid-transition
        if index == 0:
            self._refresh_summaries()
        elif index == 2:
            self._build_range_rows()
        self.stack.slide_to(index)

    def _active_keys(self) -> list[str]:
        """
        Return the clefs in use.

        Returns
        -------
        list of str
            The chosen clefs, which the range editors and summaries are for.

        Examples
        --------
        >>> NoteNameSettingsPanel(NoteNameSettings(clefs={"alto"}))._active_keys()
        ['alto']
        """
        return self.cfg.active_clefs()

    def _refresh_summaries(self) -> None:
        """
        Update the menu's summaries (the clef, range, key, value and naming pictures) from the settings.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings(clefs={"bass", "tenor"}))
        >>> panel._refresh_summaries()
        >>> panel.clef_pictures.toolTip()
        'Bass, Tenor'
        """
        keys = self._active_keys()
        self.clef_pictures.set_clefs(keys)
        self.range_pictures.set_items([(k, *self.cfg.range_for(k)) for k in keys])
        self.range_row.fit()
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=True,
            keys=set(self.cfg.active_keys()),
        )
        self.value_pictures.set_values(self.cfg.active_values())
        self.name_picture.set_naming(self.cfg.naming)

    # clefs page
    def _clefs_edited(self) -> None:
        """
        Take the ticked clefs into the settings, save them and say so.

        The last ticked clef cannot be unticked.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> got = []
        >>> _ = panel.changed.connect(lambda: got.append(1))
        >>> panel.boxes["alto"].setChecked(True)
        >>> "alto" in panel.cfg.clefs, got
        (True, [1])
        """
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))  # the last checked clef can't be unchecked
        save_note_names()
        self.changed.emit()

    # key signatures / note values / note names pages
    def _keys_edited(self) -> None:
        """
        Take the ticked key signatures into the settings, save them and say so.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel.key_boxes[2].setChecked(True)
        >>> 2 in panel.cfg.key_signatures
        True
        """
        self.cfg.key_signatures = {k for k, b in self.key_boxes.items() if b.isChecked()}
        _guard_last(list(self.key_boxes.values()))
        self._save_and_emit()

    def _values_edited(self) -> None:
        """
        Take the ticked note values into the settings, save them and say so.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel.value_boxes["half"].setChecked(True)
        >>> "half" in panel.cfg.note_values
        True
        """
        self.cfg.note_values = {v for v, b in self.value_boxes.items() if b.isChecked()}
        _guard_last(list(self.value_boxes.values()))
        self._save_and_emit()

    def _names_edited(self) -> None:
        """
        Take the chosen naming (letters or solfège) into the settings, save it and say so.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel.naming_radios["solfege"].setChecked(True)
        >>> panel.cfg.naming
        'solfege'
        """
        self.cfg.naming = next(k for k, r in self.naming_radios.items() if r.isChecked())
        self._save_and_emit()

    def _accidentals_toggled(self, on: bool) -> None:
        """
        Take the Accidentals switch into the settings, save it and say so.

        Parameters
        ----------
        on : bool
            Whether sharps, flats and naturals are asked.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel._accidentals_toggled(True)
        >>> panel.cfg.accidentals
        True
        """
        self.cfg.accidentals = on
        self._save_and_emit()

    def _save_and_emit(self) -> None:
        """
        Save the note identification settings and emit `changed`.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> got = []
        >>> _ = panel.changed.connect(lambda: got.append(1))
        >>> panel._save_and_emit()
        >>> got
        [1]
        """
        save_note_names()
        self.changed.emit()

    # range page
    def _build_range_rows(self) -> None:
        """
        Build a range editor for each clef in use, and a button to reset them to the defaults.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings(clefs={"treble"}))
        >>> panel._build_range_rows()
        >>> list(panel.range_editors)
        ['treble']
        """
        while self.range_lay.count():
            item = self.range_lay.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self.range_editors = {}
        for key in self._active_keys():
            low, high = self.cfg.range_for(key)
            editor = RangeEditor(key, low=low, high=high)
            editor.edited.connect(self._range_edited)
            self.range_editors[key] = editor
            self.range_lay.addWidget(editor)
        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset_ranges)
        self.range_lay.addWidget(reset)
        self.range_lay.addStretch()

    def _range_edited(  # noqa: PLR0917  (a Qt slot: the signal passes positional arguments)
        self,
        key: str,
        low: int,
        high: int,
    ) -> None:
        """
        Take a changed range into the settings, save it and say so.

        Parameters
        ----------
        key : str
            The clef.
        low : int
            The lowest note, as a staff step.
        high : int
            The highest note.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings())
        >>> panel._range_edited("treble", 30, 40)
        >>> panel.cfg.ranges
        {'treble': (30, 40)}
        """
        self.cfg.ranges[key] = (low, high)
        self._save_and_emit()

    def _reset_ranges(self) -> None:
        """
        Go back to the default ranges and show them.

        Examples
        --------
        >>> panel = NoteNameSettingsPanel(NoteNameSettings(ranges={"treble": (30, 40)}))
        >>> panel._reset_ranges()
        >>> panel.cfg.ranges
        {}
        """
        self.cfg.ranges.clear()
        save_note_names()
        self._build_range_rows()
        self.changed.emit()


def load_keyboard() -> None:
    """
    Load the saved keyboard exercise settings into the shared settings object.

    A saved range that is not a valid span of keys, or a key list with nothing usable in it, is ignored.

    Examples
    --------
    >>> cfg_ = settings.keyboard
    >>> cfg_.require_octave = True
    >>> save_keyboard()
    >>> cfg_.require_octave = False
    >>> load_keyboard()
    >>> cfg_.require_octave
    True
    >>> cfg_.require_octave = False
    >>> save_keyboard()
    """
    saved_settings = store()
    cfg = settings.keyboard
    cfg.black_keys = text_value(saved_settings, key="keyboard/blackKeys", default="true").lower() != "false"
    cfg.require_octave = text_value(saved_settings, key="keyboard/requireOctave", default="false").lower() == "true"
    try:
        low = int_value(saved_settings, key="keyboard/low", default=cfg.low)
        high = int_value(saved_settings, key="keyboard/high", default=cfg.high)
    except (TypeError, ValueError):
        return
    first, last = settings.KEYBOARD_FULL
    if first <= low <= high <= last:
        cfg.low, cfg.high = low, high
    cfg.key_signature = text_value(saved_settings, key="keyboard/keySignature", default="false").lower() == "true"
    keys = text_value(saved_settings, key="keyboard/keys", default="")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


def save_keyboard() -> None:
    """
    Save the keyboard exercise settings.

    Examples
    --------
    >>> cfg_ = settings.keyboard
    >>> save_keyboard()
    >>> int(store().value("keyboard/low")) == cfg_.low
    True
    """
    saved_settings = store()
    cfg = settings.keyboard
    saved_settings.setValue("keyboard/blackKeys", "true" if cfg.black_keys else "false")
    saved_settings.setValue("keyboard/requireOctave", "true" if cfg.require_octave else "false")
    saved_settings.setValue("keyboard/low", cfg.low)
    saved_settings.setValue("keyboard/high", cfg.high)
    saved_settings.setValue("keyboard/keySignature", "true" if cfg.key_signature else "false")
    saved_settings.setValue("keyboard/keys", ",".join(str(k) for k in cfg.active_keys()))


class KeyChecklist(QWidget):
    """
    Checkboxes for the 15 major keys, flats on the left and sharps on the right.

    At least one stays checked. Each is labelled with a picture of its signature.

    Attributes
    ----------
    changed : Signal
        Emitted after a box is ticked or unticked.
    boxes : dict of int to QCheckBox
        The checkbox of each key signature, from -7 (seven flats) to 7 (seven sharps).

    Examples
    --------
    >>> KeyChecklist({0, 2}).selected() == {0, 2}
    True
    """

    changed = Signal()

    def __init__(
        self,
        selected: set[int],
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the checklist.

        Parameters
        ----------
        selected : set of int
            The key signatures to tick at first.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> len(KeyChecklist({0}).boxes)
        15
        """
        super().__init__(parent)
        self.boxes = {k: QCheckBox() for k in range(-7, 8)}
        for k, box in self.boxes.items():  # each key is labelled with its signature, as written after a treble clef
            description = f"{MAJOR_KEYS[k]} major, {_key_label(k).split('·')[1].strip()}"
            _label_with_picture(box, picture=KeySignaturePicture(k, scale=1.15), name=description)
        # Two framed groups: C major on its own, and the keys with sharps or flats (flats left, sharps right).
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        """
        Return the ticked key signatures.

        Returns
        -------
        set of int
            Sharps if positive, flats if negative.

        Examples
        --------
        >>> KeyChecklist({-3, 1}).selected() == {-3, 1}
        True
        """
        return {k for k, box in self.boxes.items() if box.isChecked()}

    def _toggled(self) -> None:
        """
        Keep one box ticked, and say that something changed.

        Examples
        --------
        >>> checklist = KeyChecklist({0})
        >>> got = []
        >>> _ = checklist.changed.connect(lambda: got.append(1))
        >>> checklist.boxes[3].setChecked(True)
        >>> got
        [1]
        """
        _guard_last(list(self.boxes.values()))
        self.changed.emit()


class KeySignaturePage(QWidget):
    """
    The key signature sub-page: a switch for using key signatures at all, and the keys to draw from.

    Attributes
    ----------
    changed : Signal
        Emitted after the switch or a key is changed.
    switch_row : _ToggleRow
        The "Use key signatures" switch.
    checklist : KeyChecklist
        The keys; only enabled while the switch is on.

    Examples
    --------
    >>> page = KeySignaturePage(True, selected={0, 1})
    >>> page.enabled(), page.selected() == {0, 1}
    (True, True)
    """

    changed = Signal()

    def __init__(
        self,
        enabled: bool,
        *,
        selected: set[int],
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the page.

        Parameters
        ----------
        enabled : bool
            Whether key signatures are on.
        selected : set of int
            The key signatures to tick at first. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> page = KeySignaturePage(False, selected={0})
        >>> page.checklist.isEnabled()
        False
        """
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        """
        Report whether key signatures are switched on.

        Returns
        -------
        bool
            True if the switch is on.

        Examples
        --------
        >>> KeySignaturePage(True, selected={0}).enabled()
        True
        """
        return self.switch_row.isOn()

    def selected(self) -> set[int]:
        """
        Return the ticked key signatures.

        Returns
        -------
        set of int
            Sharps if positive, flats if negative.

        Examples
        --------
        >>> KeySignaturePage(True, selected={-2, 0}).selected() == {-2, 0}
        True
        """
        return self.checklist.selected()

    def _switched(self, on: bool) -> None:
        """
        Enable the keys only while key signatures are on, and say that something changed.

        Parameters
        ----------
        on : bool
            The switch's new state.

        Examples
        --------
        >>> page = KeySignaturePage(True, selected={0})
        >>> got = []
        >>> _ = page.changed.connect(lambda: got.append(1))
        >>> page._switched(False)
        >>> page.checklist.isEnabled(), got
        (False, [1])
        """
        self.checklist.setEnabled(on)
        self.changed.emit()


class KeyboardSettingsPanel(ExerciseSettingsPanel):
    """
    The settings of the keyboard exercise: a menu with a page for the range of keys.

    The menu has Range, Black keys, Octave number and Key signatures. Edits are live: each changes the settings, saves them
    and emits `changed`.

    Attributes
    ----------
    cfg : KeyboardSettings
        The settings being edited.
    stack : SlideStack
        The menu and its pages.
    span : KeyboardSpan
        The miniature piano on the Range page, which can be dragged to choose the keys.
    low_label, high_label : QLabel
        The names of the lowest and highest key asked.
    key_page : KeySignaturePage
        The key signature sub-page.

    Examples
    --------
    >>> panel = KeyboardSettingsPanel(settings.KeyboardSettings())
    >>> panel.low_label.text(), panel.high_label.text()
    ('C3', 'C5')
    """

    def __init__(
        self,
        cfg: settings.KeyboardSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the panel for a set of settings.

        Parameters
        ----------
        cfg : KeyboardSettings
            The settings to edit.
        parent : QWidget or None, default None
            The widget that owns the panel. Keyword-only.

        Examples
        --------
        >>> KeyboardSettingsPanel(settings.KeyboardSettings()).stack.count()  # the menu, the range and the keys
        3
        """
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        for row in (
            self.range_row,
            self.black_keys_row,
            self.octave_row,
            self.keys_row,
        ):
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: range
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
            down = _arrow(Qt.ArrowType.LeftArrow, tip=f"{title}: one key down")
            up = _arrow(Qt.ArrowType.RightArrow, tip=f"{title}: one key up")
            down.clicked.connect(lambda _=False, w=which: self._step(w, delta=-1))
            up.clicked.connect(lambda _=False, w=which: self._step(w, delta=1))
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
        range_page = _subpage("Range", body=body, back=lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, selected=cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", body=self.key_page, back=lambda: self._go(0))

        self.stack.addWidget(menu)
        self.stack.addWidget(range_page)
        self.stack.addWidget(keys_page)
        self._refresh_range()
        self._show_keys()

    def _go(self, index: int) -> None:
        """
        Slide to a page, refreshing the menu's summaries when going back to it.

        Parameters
        ----------
        index : int
            0 for the menu, 1 for the Range page, 2 for the key signatures.

        Examples
        --------
        >>> panel = KeyboardSettingsPanel(settings.KeyboardSettings())
        >>> panel._go(1)
        >>> panel.stack.sliding
        True
        """
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        self.stack.slide_to(index)

    def _refresh_range(self) -> None:
        """
        Show the range everywhere it appears and enable only the arrows that can still move.

        Examples
        --------
        >>> cfg_ = settings.KeyboardSettings()
        >>> panel = KeyboardSettingsPanel(cfg_)
        >>> cfg_.low = 50
        >>> panel._refresh_range()
        >>> panel.low_label.text()
        'D3'
        """
        cfg = self.cfg
        self.low_label.setText(key_name(cfg.low))
        self.high_label.setText(key_name(cfg.high))
        self.span.set_span(cfg.low, hi=cfg.high)
        first, last = settings.KEYBOARD_FULL
        self.arrows["low"][0].setEnabled(cfg.low > first)
        self.arrows["low"][1].setEnabled(cfg.low < cfg.high)  # the lowest key can't pass the highest
        self.arrows["high"][0].setEnabled(cfg.high > cfg.low)
        self.arrows["high"][1].setEnabled(cfg.high < last)
        self.range_keyboard.set_span(cfg.low, hi=cfg.high)
        self.range_keyboard.setToolTip(f"{key_name(cfg.low)} to {key_name(cfg.high)}")

    def _step(
        self,
        which: str,
        *,
        delta: int,
    ) -> None:
        """
        Move one end of the range by some keys, keeping the lowest below the highest and both on the piano.

        Parameters
        ----------
        which : str
            "low" or "high".
        delta : int
            How many keys to move; positive is higher. Keyword-only.

        Examples
        --------
        >>> cfg = settings.KeyboardSettings()
        >>> panel = KeyboardSettingsPanel(cfg)
        >>> panel._step("low", delta=2)
        >>> cfg.low
        50
        >>> panel._step("high", delta=-100)  # the highest key cannot pass the lowest
        >>> cfg.high
        50
        """
        low, high = self.cfg.low, self.cfg.high
        first, last = settings.KEYBOARD_FULL
        if which == "low":
            low = min(max(low + delta, first), high)
        else:
            high = max(min(high + delta, last), low)
        self._set_range(low, high)

    def _set_range(  # noqa: PLR0917  (a Qt slot: the signal passes positional arguments)
        self,
        low: int,
        high: int,
    ) -> None:
        """
        Take a new range into the settings, show it, save it and say so.

        Nothing happens if the range has not changed.

        Parameters
        ----------
        low : int
            The lowest key asked, as a MIDI number.
        high : int
            The highest key asked.

        Examples
        --------
        >>> cfg = settings.KeyboardSettings()
        >>> panel = KeyboardSettingsPanel(cfg)
        >>> panel._set_range(60, 72)
        >>> (cfg.low, cfg.high), panel.low_label.text()
        ((60, 72), 'C4')
        """
        if (low, high) == (self.cfg.low, self.cfg.high):
            return
        self.cfg.low, self.cfg.high = low, high
        self._refresh_range()
        self._save_and_emit()

    def _black_keys_toggled(self, on: bool) -> None:
        """
        Take the Black keys switch into the settings, save it and say so.

        Parameters
        ----------
        on : bool
            Whether the black keys are asked.

        Examples
        --------
        >>> cfg = settings.KeyboardSettings()
        >>> KeyboardSettingsPanel(cfg)._black_keys_toggled(False)
        >>> cfg.black_keys
        False
        """
        self.cfg.black_keys = on
        self._save_and_emit()

    def _octave_toggled(self, on: bool) -> None:
        """
        Take the Octave number switch into the settings, save it and say so.

        Parameters
        ----------
        on : bool
            Whether the answer must include the octave.

        Examples
        --------
        >>> cfg = settings.KeyboardSettings()
        >>> KeyboardSettingsPanel(cfg)._octave_toggled(True)
        >>> cfg.require_octave
        True
        """
        self.cfg.require_octave = on
        self._save_and_emit()

    def _show_keys(self) -> None:
        """
        Update the menu's key signature summary.

        Examples
        --------
        >>> panel = KeyboardSettingsPanel(settings.KeyboardSettings())
        >>> panel._show_keys()
        >>> panel.keys_row.value.text()  # key signatures are off
        'Off'
        """
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=self.cfg.key_signature,
            keys=set(self.cfg.active_keys()),
        )

    def _keys_edited(self) -> None:
        """
        Take the key signature page into the settings, save it and say so.

        Examples
        --------
        >>> cfg = settings.KeyboardSettings()
        >>> panel = KeyboardSettingsPanel(cfg)
        >>> panel.key_page.switch_row.setOn(True)
        >>> panel._keys_edited()
        >>> cfg.key_signature
        True
        """
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        self._show_keys()
        self._save_and_emit()

    def _save_and_emit(self) -> None:
        """
        Save the keyboard settings and emit `changed`.

        Examples
        --------
        >>> panel = KeyboardSettingsPanel(settings.KeyboardSettings())
        >>> got = []
        >>> _ = panel.changed.connect(lambda: got.append(1))
        >>> panel._save_and_emit()
        >>> got
        [1]
        """
        save_keyboard()
        self.changed.emit()


def load_construction() -> None:
    """
    Load the saved note construction settings into the shared settings object.

    Examples
    --------
    >>> store().setValue("construction/accidentals", "true")
    >>> load_construction()
    >>> settings.construction.accidentals
    True
    >>> store().setValue("construction/accidentals", "false")
    >>> load_construction()
    """
    saved_settings = store()
    cfg = settings.construction
    saved = saved_settings.value("construction/clefs")
    if saved is not None:
        text = saved if isinstance(saved, str) else ",".join(saved)
        cfg.clefs = {c for c in text.split(",") if c in settings.RANGE_KEYS} or cfg.clefs
    cfg.accidentals = text_value(saved_settings, key="construction/accidentals", default="false").lower() == "true"
    cfg.key_signature = text_value(saved_settings, key="construction/keySignature", default="false").lower() == "true"
    keys = text_value(saved_settings, key="construction/keys", default="")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class NoteConstructionSettingsPanel(ExerciseSettingsPanel):
    """
    The settings of the note construction exercise: a menu with a page for the staff and one for the keys.

    The menu has Staff, Accidentals, Key signatures and Keys. Edits are live: each changes the settings, saves them and
    emits `changed`.

    Attributes
    ----------
    cfg : ConstructionSettings
        The settings being edited.
    stack : SlideStack
        The menu and its pages.
    boxes : dict of str to QCheckBox
        The clef checkboxes, including the grand staff.
    key_page : KeySignaturePage
        The key signature sub-page.

    Examples
    --------
    >>> panel = NoteConstructionSettingsPanel(settings.ConstructionSettings())
    >>> sorted(panel.boxes)[:3]
    ['alto', 'baritone', 'bass']
    """

    def __init__(
        self,
        cfg: settings.ConstructionSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the panel for a set of settings.

        Parameters
        ----------
        cfg : ConstructionSettings
            The settings to edit.
        parent : QWidget or None, default None
            The widget that owns the panel. Keyword-only.

        Examples
        --------
        >>> NoteConstructionSettingsPanel(settings.ConstructionSettings()).stack.count()
        3
        """
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        blay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        staff_page = _subpage("Staff", body=body, back=lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, selected=cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", body=self.key_page, back=lambda: self._go(0))

        for page in (menu, staff_page, keys_page):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int) -> None:
        """
        Slide to a page, refreshing the menu's summaries when going back to it.

        Parameters
        ----------
        index : int
            0 for the menu, 1 for the Staff page, 2 for the key signatures.

        Examples
        --------
        >>> panel = NoteConstructionSettingsPanel(settings.ConstructionSettings())
        >>> panel._go(1)
        >>> panel.stack.sliding
        True
        """
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self) -> None:
        """
        Update the menu's clef and key signature summaries from the settings.

        Examples
        --------
        >>> panel = NoteConstructionSettingsPanel(settings.ConstructionSettings(clefs={"bass"}))
        >>> panel._refresh_summaries()
        >>> panel.clef_pictures.toolTip()
        'Bass'
        """
        self.clef_pictures.set_clefs(self.cfg.active_clefs())
        self._show_keys()

    def _save_and_emit(self) -> None:
        """
        Save the note construction settings and emit `changed`.

        Examples
        --------
        >>> cfg_ = settings.ConstructionSettings(accidentals=True)
        >>> panel = NoteConstructionSettingsPanel(cfg_)
        >>> panel._save_and_emit()
        >>> str(store().value("construction/accidentals"))
        'true'
        >>> cfg_.accidentals = False
        >>> panel._save_and_emit()
        """
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("construction/clefs", ",".join(c for c in settings.RANGE_KEYS if c in cfg.clefs))
        saved_settings.setValue("construction/accidentals", "true" if cfg.accidentals else "false")
        saved_settings.setValue("construction/keySignature", "true" if cfg.key_signature else "false")
        saved_settings.setValue("construction/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _clefs_edited(self) -> None:
        """
        Take the ticked clefs into the settings, save them and say so.

        The last ticked clef cannot be unticked.

        Examples
        --------
        >>> cfg = settings.ConstructionSettings()
        >>> panel = NoteConstructionSettingsPanel(cfg)
        >>> panel.boxes["grand"].setChecked(True)
        >>> "grand" in cfg.clefs
        True
        """
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))  # the last checked choice can't be unchecked
        self._save_and_emit()

    def _accidentals_toggled(self, on: bool) -> None:
        """
        Take the Accidentals switch into the settings, save it and say so.

        Parameters
        ----------
        on : bool
            Whether sharps and flats are asked.

        Examples
        --------
        >>> cfg = settings.ConstructionSettings()
        >>> NoteConstructionSettingsPanel(cfg)._accidentals_toggled(True)
        >>> cfg.accidentals
        True
        """
        self.cfg.accidentals = on
        self._save_and_emit()

    def _show_keys(self) -> None:
        """
        Update the menu's key signature summary.

        Examples
        --------
        >>> panel = NoteConstructionSettingsPanel(settings.ConstructionSettings())
        >>> panel._show_keys()
        >>> panel.keys_row.value.text()
        'Off'
        """
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=self.cfg.key_signature,
            keys=set(self.cfg.active_keys()),
        )

    def _keys_edited(self) -> None:
        """
        Take the key signature page into the settings, save it and say so.

        Examples
        --------
        >>> cfg = settings.ConstructionSettings()
        >>> panel = NoteConstructionSettingsPanel(cfg)
        >>> panel.key_page.switch_row.setOn(True)
        >>> panel._keys_edited()
        >>> cfg.key_signature
        True
        """
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        self._show_keys()
        self._save_and_emit()


def load_arpeggio() -> None:
    """
    Load the saved arpeggio settings into the shared settings object.

    Anything in the saved data that is not valid is ignored, and a list with nothing valid in it leaves the setting as it was.

    Examples
    --------
    >>> store().setValue("arpeggio/types", "major")
    >>> load_arpeggio()
    >>> settings.arpeggio.types
    {'major'}
    >>> settings.arpeggio.types = {"major", "minor", "dominant 7th", "diminished 7th"}
    >>> store().setValue("arpeggio/types", ",".join(settings.arpeggio.active_types()))
    """
    saved_settings = store()
    cfg = settings.arpeggio
    clefs = text_value(saved_settings, key="arpeggio/clefs", default="")
    if clefs:
        cfg.clefs = {c for c in clefs.split(",") if c in CLEFS} or cfg.clefs
    types = text_value(saved_settings, key="arpeggio/types", default="")
    if types:
        cfg.types = {t for t in types.split(",") if t in settings.ARPEGGIO_TYPES} or cfg.types
    inversions = text_value(saved_settings, key="arpeggio/inversions", default="")
    if inversions:
        found = {int(i) for i in inversions.split(",") if i.isdigit() and int(i) in settings.INVERSIONS}
        cfg.inversions = found or cfg.inversions
    cfg.key_signature = text_value(saved_settings, key="arpeggio/keySignature", default="false").lower() == "true"
    keys = text_value(saved_settings, key="arpeggio/keys", default="")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class ChoiceChecklist(QWidget):
    """
    Checkboxes for a list of choices, optionally under small headings. At least one stays checked.

    Attributes
    ----------
    changed : Signal
        Emitted after a box is ticked or unticked.
    boxes : dict
        The checkbox of each choice, by its key.

    Examples
    --------
    >>> groups = [("Triads", [("major", "Major"), ("minor", "Minor")]), ("", [("x", "Other")])]
    >>> checklist = ChoiceChecklist(groups, selected={"major"})
    >>> checklist.selected()
    {'major'}
    """

    changed = Signal()

    def __init__(
        self,
        groups: list[tuple[str, list[tuple[object, str]]]],
        *,
        selected: set,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the checklist.

        Parameters
        ----------
        groups : list of tuple of (str, list of tuple of (object, str))
            The headings and, under each, the choices as (key, label); an empty heading shows none.
        selected : set
            The keys to tick at first. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> checklist = ChoiceChecklist([("", [(0, "Root"), (1, "1st")])], selected={0})
        >>> # noinspection PyTypeChecker
        >>> sorted(checklist.boxes)
        [0, 1]
        """
        super().__init__(parent)
        self.boxes: dict[object, QCheckBox] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        """
        Return the ticked choices.

        Returns
        -------
        set
            The keys of the ticked boxes.

        Examples
        --------
        >>> ChoiceChecklist([("", [(0, "Root"), (1, "1st")])], selected={0, 1}).selected()
        {0, 1}
        """
        return {k for k, box in self.boxes.items() if box.isChecked()}

    def _toggled(self) -> None:
        """
        Keep one box ticked, and say that something changed.

        Examples
        --------
        >>> checklist = ChoiceChecklist([("", [(0, "Root"), (1, "1st")])], selected={0})
        >>> got = []
        >>> _ = checklist.changed.connect(lambda: got.append(1))
        >>> checklist.boxes[1].setChecked(True)
        >>> got
        [1]
        """
        _guard_last(list(self.boxes.values()))
        self.changed.emit()


_INVERSION_SHORT = (
    "Root",
    "1st",
    "2nd",
    "3rd",
)


class ArpeggioSettingsPanel(ExerciseSettingsPanel):
    """
    The settings of the arpeggio exercise: a menu with a page for each group of settings.

    The menu has Staff, Arpeggio types, Inversions and Key signatures. Edits are live: each changes the settings, saves them
    and emits `changed`.

    Attributes
    ----------
    cfg : ArpeggioSettings
        The settings being edited.
    stack : SlideStack
        The menu and its pages.
    boxes : dict of str to QCheckBox
        The clef checkboxes.
    types : ChoiceChecklist
        The chord types.
    inversions : ChoiceChecklist
        The inversions.
    key_page : KeySignaturePage
        The key signature sub-page.

    Examples
    --------
    >>> panel = ArpeggioSettingsPanel(settings.ArpeggioSettings())
    >>> panel.types_row.value.text()
    '4 of 9'
    """

    def __init__(
        self,
        cfg: settings.ArpeggioSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the panel for a set of settings.

        Parameters
        ----------
        cfg : ArpeggioSettings
            The settings to edit.
        parent : QWidget or None, default None
            The widget that owns the panel. Keyword-only.

        Examples
        --------
        >>> ArpeggioSettingsPanel(settings.ArpeggioSettings()).stack.count()  # the menu and four pages
        5
        """
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        for row in (
            self.staff_row,
            self.types_row,
            self.inversions_row,
            self.keys_row,
        ):
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: the staff (the four clefs that have a single staff)
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        staff_page = _subpage("Staff", body=body, back=lambda: self._go(0))

        # layer 2: arpeggio types, and inversions
        self.types = ChoiceChecklist(
            [
                ("Triads", [(t, t.capitalize()) for t in settings.ARPEGGIO_TRIADS]),
                ("Seventh chords", [(t, t.capitalize()) for t in settings.ARPEGGIO_SEVENTHS]),
            ],
            selected=cfg.types,
        )
        self.types.changed.connect(self._types_edited)
        types_page = _subpage("Arpeggio types", body=self.types, back=lambda: self._go(0))
        names = settings_inversion_names()
        self.inversions = ChoiceChecklist([("", [(i, names[i]) for i in settings.INVERSIONS])], selected=cfg.inversions)
        self.inversions.changed.connect(self._inversions_edited)
        note = QLabel("A triad has no 3rd inversion, so that choice only applies to seventh chords.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        inv_body = QWidget()
        inv_lay = QVBoxLayout(inv_body)
        inv_lay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        inv_lay.addWidget(self.inversions)
        inv_lay.addWidget(note)
        inversions_page = _subpage("Inversions", body=inv_body, back=lambda: self._go(0))

        # layer 2: key signatures
        self.key_page = KeySignaturePage(cfg.key_signature, selected=cfg.keys)
        self.key_page.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", body=self.key_page, back=lambda: self._go(0))

        for page in (
            menu,
            staff_page,
            types_page,
            inversions_page,
            keys_page,
        ):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int) -> None:
        """
        Slide to a page, refreshing the menu's summaries when going back to it.

        Parameters
        ----------
        index : int
            0 for the menu, then the pages in the order of the menu.

        Examples
        --------
        >>> panel = ArpeggioSettingsPanel(settings.ArpeggioSettings())
        >>> panel._go(2)
        >>> panel.stack.sliding
        True
        """
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self) -> None:
        """
        Update the menu's summaries: the clefs, how many types, which inversions and the keys.

        Examples
        --------
        >>> panel = ArpeggioSettingsPanel(settings.ArpeggioSettings(inversions={0, 2}))
        >>> panel._refresh_summaries()
        >>> panel.inversions_row.value.text()
        'Root, 2nd'
        """
        cfg = self.cfg
        self.clef_pictures.set_clefs(cfg.active_clefs())
        types = cfg.active_types()
        self.types_row.value.setText(f"{len(types)} of {len(settings.ARPEGGIO_TYPES)}")
        inversions = cfg.active_inversions()
        self.inversions_row.value.setText(
            "All" if len(inversions) == len(settings.INVERSIONS) else ", ".join(_INVERSION_SHORT[i] for i in inversions),
        )
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=cfg.key_signature,
            keys=set(cfg.active_keys()),
        )

    def _save_and_emit(self) -> None:
        """
        Save the arpeggio settings and emit `changed`.

        Examples
        --------
        >>> cfg_ = settings.ArpeggioSettings(clefs={"tenor"})
        >>> panel = ArpeggioSettingsPanel(cfg_)
        >>> panel._save_and_emit()
        >>> str(store().value("arpeggio/clefs"))
        'tenor'
        >>> store().setValue("arpeggio/clefs", "treble,bass")
        """
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("arpeggio/clefs", ",".join(cfg.active_clefs()))
        saved_settings.setValue("arpeggio/types", ",".join(cfg.active_types()))
        saved_settings.setValue("arpeggio/inversions", ",".join(str(i) for i in cfg.active_inversions()))
        saved_settings.setValue("arpeggio/keySignature", "true" if cfg.key_signature else "false")
        saved_settings.setValue("arpeggio/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _clefs_edited(self) -> None:
        """
        Take the ticked clefs into the settings, save them and say so.

        The last ticked clef cannot be unticked.

        Examples
        --------
        >>> cfg = settings.ArpeggioSettings()
        >>> panel = ArpeggioSettingsPanel(cfg)
        >>> panel.boxes["alto"].setChecked(True)
        >>> "alto" in cfg.clefs
        True
        """
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))
        self._save_and_emit()

    def _types_edited(self) -> None:
        """
        Take the ticked chord types into the settings, save them and say so.

        Examples
        --------
        >>> cfg = settings.ArpeggioSettings()
        >>> panel = ArpeggioSettingsPanel(cfg)
        >>> panel.types.boxes["minor 7th"].setChecked(True)
        >>> "minor 7th" in cfg.types
        True
        """
        self.cfg.types = self.types.selected()
        self._save_and_emit()

    def _inversions_edited(self) -> None:
        """
        Take the ticked inversions into the settings, save them and say so.

        Examples
        --------
        >>> cfg = settings.ArpeggioSettings()
        >>> panel = ArpeggioSettingsPanel(cfg)
        >>> panel.inversions.boxes[3].setChecked(False)
        >>> 3 in cfg.inversions
        False
        """
        self.cfg.inversions = self.inversions.selected()
        self._save_and_emit()

    def _keys_edited(self) -> None:
        """
        Take the key signature page into the settings, update the menu, save and say so.

        Examples
        --------
        >>> cfg = settings.ArpeggioSettings()
        >>> panel = ArpeggioSettingsPanel(cfg)
        >>> panel.key_page.switch_row.setOn(True)
        >>> panel._keys_edited()
        >>> cfg.key_signature
        True
        """
        self.cfg.key_signature = self.key_page.enabled()
        self.cfg.keys = self.key_page.selected()
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=self.cfg.key_signature,
            keys=set(self.cfg.active_keys()),
        )
        self._save_and_emit()


def load_key_signatures() -> None:
    """
    Load the saved key signature exercise settings into the shared settings object.

    Anything in the saved data that is not valid is ignored, and a list with nothing valid in it leaves the setting as it was.

    Examples
    --------
    >>> store().setValue("keySignatures/questions", "count")
    >>> load_key_signatures()
    >>> settings.key_signatures.questions
    {'count'}
    >>> settings.key_signatures.questions = {"read", "count"}
    >>> store().setValue("keySignatures/questions", "read,count")
    """
    saved_settings = store()
    cfg = settings.key_signatures
    questions = text_value(saved_settings, key="keySignatures/questions", default="")
    if questions:
        cfg.questions = {q for q in questions.split(",") if q in settings.KEY_QUESTIONS} or cfg.questions
    clefs = text_value(saved_settings, key="keySignatures/clefs", default="")
    if clefs:
        cfg.clefs = {c for c in clefs.split(",") if c in CLEFS} or cfg.clefs
    modes = text_value(saved_settings, key="keySignatures/modes", default="")
    if modes:
        cfg.modes = {m for m in modes.split("|") if m in settings.KEY_MODES} or cfg.modes
    keys = text_value(saved_settings, key="keySignatures/keys", default="")
    if keys:
        cfg.keys = {int(k) for k in keys.split(",") if k.lstrip("-").isdigit() and abs(int(k)) <= 7} or cfg.keys


class KeySignatureSettingsPanel(ExerciseSettingsPanel):
    """
    The settings of the key signatures exercise: a menu with a page for each group of settings.

    The menu has Questions, Staff, Scales and Key signatures. Edits are live: each changes the settings, saves them and
    emits `changed`.

    Attributes
    ----------
    cfg : KeySignatureSettings
        The settings being edited.
    stack : SlideStack
        The menu and its pages.
    questions : ChoiceChecklist
        Reading a signature, counting its accidentals, or both.
    boxes : dict of str to QCheckBox
        The clef checkboxes.
    modes : ChoiceChecklist
        The scales (major, minor and the modes).
    key_list : KeyChecklist
        The key signatures.

    Examples
    --------
    >>> panel = KeySignatureSettingsPanel(settings.KeySignatureSettings())
    >>> panel.questions_row.value.text()
    'Both'
    """

    def __init__(
        self,
        cfg: settings.KeySignatureSettings,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the panel for a set of settings.

        Parameters
        ----------
        cfg : KeySignatureSettings
            The settings to edit.
        parent : QWidget or None, default None
            The widget that owns the panel. Keyword-only.

        Examples
        --------
        >>> KeySignatureSettingsPanel(settings.KeySignatureSettings()).stack.count()  # the menu and four pages
        5
        """
        super().__init__(parent)
        self.cfg = cfg
        self.stack = SlideStack()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(self.stack)

        # layer 1: menu
        menu = QWidget()
        mlay = QVBoxLayout(menu)
        mlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        mlay.addWidget(QLabel("<h3>Settings</h3>"))
        self.questions_row = _Row("Questions")
        self.staff_row = _Row("Staff")
        self.modes_row = _Row("Scales")
        self.keys_row = _Row("Key signatures")
        self.clef_pictures = ClefPictures()
        self.staff_row.attach(self.clef_pictures)
        self.keys_diagram = KeyDiagram()
        self.keys_row.attach(self.keys_diagram)
        for index, row in enumerate(
            (
                self.questions_row,
                self.staff_row,
                self.modes_row,
                self.keys_row,
            ),
            1,
        ):
            row.clicked.connect(lambda _=False, i=index: self._go(i))
            mlay.addWidget(row)
        mlay.addStretch()

        # layer 2: the kinds of question
        self.questions = ChoiceChecklist([("", [(k, v) for k, v in settings.KEY_QUESTIONS.items()])], selected=cfg.questions)
        self.questions.changed.connect(self._questions_edited)
        questions_note = QLabel(
            "A key signature is drawn on a staff and you name its key, or a key is named and you count "
            "its sharps and flats. One of the checked kinds is picked at random.",
        )
        questions_note.setWordWrap(True)
        questions_note.setStyleSheet("color: gray;")
        questions_body = QWidget()
        qlay = QVBoxLayout(questions_body)
        qlay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        qlay.addWidget(self.questions)
        qlay.addWidget(questions_note)
        questions_page = _subpage("Questions", body=questions_body, back=lambda: self._go(0))

        # layer 2: the clefs the signature is drawn on
        body = QWidget()
        blay = QVBoxLayout(body)
        blay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        staff_page = _subpage("Staff", body=body, back=lambda: self._go(0))

        # layer 2: the scales, so the key can be a major or minor key or a mode
        self.modes = ChoiceChecklist([("", [(m, settings.MODE_LABELS[m]) for m in settings.KEY_MODES])], selected=cfg.modes)
        self.modes.changed.connect(self._modes_edited)
        modes_note = QLabel(
            "A mode has the key signature of a major key and starts from another note of it: D Dorian has "
            "the signature of C major.",
        )
        modes_note.setWordWrap(True)
        modes_note.setStyleSheet("color: gray;")
        modes_body = QWidget()
        mlay2 = QVBoxLayout(modes_body)
        mlay2.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        mlay2.addWidget(self.modes)
        mlay2.addWidget(modes_note)
        modes_page = _subpage("Scales", body=modes_body, back=lambda: self._go(0))

        # layer 2: the key signatures asked
        self.key_list = KeyChecklist(cfg.keys)
        self.key_list.changed.connect(self._keys_edited)
        keys_page = _subpage("Key signatures", body=self.key_list, back=lambda: self._go(0))

        for page in (
            menu,
            questions_page,
            staff_page,
            modes_page,
            keys_page,
        ):
            self.stack.addWidget(page)
        self._refresh_summaries()

    def _go(self, index: int) -> None:
        """
        Slide to a page, refreshing the menu's summaries when going back to it.

        Parameters
        ----------
        index : int
            0 for the menu, then the pages in the order of the menu.

        Examples
        --------
        >>> panel = KeySignatureSettingsPanel(settings.KeySignatureSettings())
        >>> panel._go(1)
        >>> panel.stack.sliding
        True
        """
        if self.stack.sliding or index == self.stack.currentIndex():
            return
        if index == 0:
            self._refresh_summaries()
        self.stack.slide_to(index)

    def _refresh_summaries(self) -> None:
        """
        Update the menu's summaries: the kinds of question, the clefs, how many scales and the keys.

        Examples
        --------
        >>> panel = KeySignatureSettingsPanel(settings.KeySignatureSettings(questions={"read"}))
        >>> panel._refresh_summaries()
        >>> panel.questions_row.value.text(), panel.modes_row.value.text()
        ('Read', '2 of 7')
        """
        cfg = self.cfg
        questions = cfg.active_questions()
        self.questions_row.value.setText(
            "Both" if len(questions) == len(settings.KEY_QUESTIONS) else "Read" if questions == ["read"] else "Count",
        )
        self.clef_pictures.set_clefs(cfg.active_clefs())
        modes = cfg.active_modes()
        self.modes_row.value.setText(f"{len(modes)} of {len(settings.KEY_MODES)}")
        _show_keys(
            self.keys_row,
            diagram=self.keys_diagram,
            enabled=True,
            keys=set(cfg.active_keys()),
        )

    def _save_and_emit(self) -> None:
        """
        Save the key signature settings and emit `changed`.

        Examples
        --------
        >>> panel = KeySignatureSettingsPanel(settings.KeySignatureSettings(clefs={"alto"}))
        >>> panel._save_and_emit()
        >>> str(store().value("keySignatures/clefs"))
        'alto'
        >>> store().setValue("keySignatures/clefs", "treble,bass")
        """
        saved_settings = store()
        cfg = self.cfg
        saved_settings.setValue("keySignatures/questions", ",".join(cfg.active_questions()))
        saved_settings.setValue("keySignatures/clefs", ",".join(cfg.active_clefs()))
        saved_settings.setValue("keySignatures/modes", "|".join(cfg.active_modes()))
        saved_settings.setValue("keySignatures/keys", ",".join(str(k) for k in cfg.active_keys()))
        self.changed.emit()

    def _questions_edited(self) -> None:
        """
        Take the ticked kinds of question into the settings, save them and say so.

        Examples
        --------
        >>> cfg = settings.KeySignatureSettings()
        >>> panel = KeySignatureSettingsPanel(cfg)
        >>> panel.questions.boxes["count"].setChecked(False)
        >>> cfg.questions
        {'read'}
        """
        self.cfg.questions = self.questions.selected()
        self._save_and_emit()

    def _clefs_edited(self) -> None:
        """
        Take the ticked clefs into the settings, save them and say so.

        The last ticked clef cannot be unticked.

        Examples
        --------
        >>> cfg = settings.KeySignatureSettings()
        >>> panel = KeySignatureSettingsPanel(cfg)
        >>> panel.boxes["alto"].setChecked(True)
        >>> "alto" in cfg.clefs
        True
        """
        self.cfg.clefs = {c for c, b in self.boxes.items() if b.isChecked()}
        _guard_last(list(self.boxes.values()))
        self._save_and_emit()

    def _modes_edited(self) -> None:
        """
        Take the ticked scales into the settings, save them and say so.

        Examples
        --------
        >>> cfg = settings.KeySignatureSettings()
        >>> panel = KeySignatureSettingsPanel(cfg)
        >>> panel.modes.boxes["Dorian"].setChecked(True)
        >>> "Dorian" in cfg.modes
        True
        """
        self.cfg.modes = self.modes.selected()
        self._save_and_emit()

    def _keys_edited(self) -> None:
        """
        Take the ticked key signatures into the settings, save them and say so.

        Examples
        --------
        >>> cfg = settings.KeySignatureSettings()
        >>> panel = KeySignatureSettingsPanel(cfg)
        >>> panel.key_list.boxes[2].setChecked(False)
        >>> 2 in cfg.keys
        False
        """
        self.cfg.keys = self.key_list.selected()
        self._save_and_emit()


def settings_inversion_names() -> tuple[str, ...]:
    """
    Return the inversions as they are written in the settings.

    Returns
    -------
    tuple of str
        'Root position', '1st inversion', '2nd inversion' and '3rd inversion'.

    Examples
    --------
    >>> settings_inversion_names()
    ('Root position', '1st inversion', '2nd inversion', '3rd inversion')
    """
    return tuple(n.capitalize() for n in INVERSION_NAMES)


def settings_panel_for(exercise: Exercise) -> ExerciseSettingsPanel | None:
    """
    Return the settings panel for an exercise.

    Parameters
    ----------
    exercise : Exercise
        The exercise.

    Returns
    -------
    ExerciseSettingsPanel or None
        A panel with a `changed` signal, or None for an exercise with no settings.

    Examples
    --------
    >>> from alto.exercises.library import IntervalNames, NoteNames
    >>> type(settings_panel_for(NoteNames())).__name__
    'NoteNameSettingsPanel'
    >>> settings_panel_for(IntervalNames()) is None
    True
    """
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
