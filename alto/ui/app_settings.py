from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..theory.pitch import Note
from . import keyboard_styles, notation
from .colors import blend
from .instrument_picker import InstrumentPicker
from .keyboard import KeyboardWidget
from .pictures import ClefPictures
from .staff import StaffWidget
from .theme import THEMES, apply_theme, save_theme, saved_theme


class StyleCard(QPushButton):
    """A selectable tile that previews a notation style: a short phrase on a staff, drawn in that style."""

    def __init__(self, style: notation.NotationStyle, parent=None):
        super().__init__(parent)
        self.style_key = style.key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)
        self.staff = StaffWidget(gap=6.5, side=8.0, note_offset=44.0, margin=3.2, compact=True)
        self.staff.notation_style = style
        self.staff.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.staff.setFixedWidth(214)
        self.staff.show_notes([[Note(4, 2)], [Note(4, 4)], [Note(5, 0)], [Note(4, 6)]], "treble", key=1, value="quarter")
        name = QLabel(f"<b>{style.label}</b>")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        blurb = QLabel(style.note)
        blurb.setStyleSheet("color: gray; font-size: 9pt;")
        blurb.setWordWrap(True)
        blurb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(self.staff)
        lay.addWidget(name)
        lay.addWidget(blurb)


RIM = "rgba(136, 136, 136, 0.5)"  # the faint outline of the builder's swatches and chips


class KeyboardCard(QPushButton):
    """A selectable tile that previews a keyboard style: a short stretch of keys drawn in that style."""

    def __init__(self, style: keyboard_styles.KeyboardStyle, parent=None):
        super().__init__(parent)
        self.style_key = style.key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 222)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)
        self.keys = KeyboardWidget()
        self.keys.style_override = style
        self.keys.pad = 6.0
        self.keys.max_key_width = 16.0
        self.keys.setFixedWidth(2 * 6 + 10 * 16)  # ten white keys, C4 to E5
        self.keys.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.keys.show_key(None, (60, 76))
        holder = QWidget()
        holder.setFixedHeight(int(2 * 6 + 30 + 16 * 6.2))  # room for the tallest strip above the keys
        holder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        holder_lay = QVBoxLayout(holder)
        holder_lay.setContentsMargins(0, 0, 0, 0)
        holder_lay.addWidget(self.keys, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        name = QLabel(f"<b>{style.label}</b>")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        blurb = QLabel(style.note)
        blurb.setStyleSheet("color: gray; font-size: 9pt;")
        blurb.setWordWrap(True)
        blurb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(holder)
        lay.addWidget(name)
        lay.addWidget(blurb)
        lay.addStretch(1)

    def show_style(self, style: keyboard_styles.KeyboardStyle) -> None:
        """Redraw the preview in `style` (the custom card follows the colours being edited)."""
        self.keys.style_override = style
        self.keys.refit()


class KeyboardBuilder(QFrame):
    """Rows for colouring each part of a keyboard: a swatch that opens the colour picker, and chips for colours named after
    materials. Changing anything selects the Custom style."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(QLabel("<b>Build your own</b>"))
        about = QLabel("Choose a colour for each part, from a material or with the colour picker. "
                       "Changing any part switches to the Custom style.")
        about.setWordWrap(True)
        about.setStyleSheet("color: gray;")
        lay.addWidget(about)
        self.swatches: dict[str, QPushButton] = {}
        for part, label, optional in keyboard_styles.COMPONENTS:
            row = QHBoxLayout()
            row.setSpacing(4)
            name = QLabel(label)
            name.setFixedWidth(84)
            row.addWidget(name)
            swatch = QPushButton()
            swatch.setFixedSize(46, 24)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            swatch.setToolTip(f"Pick a colour for the {label.lower()}")
            swatch.clicked.connect(lambda _=False, p=part, t=label: self._pick(p, t))
            row.addWidget(swatch)
            row.addSpacing(6)
            self.swatches[part] = swatch
            if optional:
                none = self._chip("None", None)
                none.setText("✕")
                none.clicked.connect(lambda _=False, p=part: self._set(p, None))
                row.addWidget(none)
            else:
                row.addSpacing(24)  # line the chips up with the rows that have a None chip
            for material, colour in keyboard_styles.MATERIALS:
                chip = self._chip(f"{material}  {colour}", colour)
                chip.clicked.connect(lambda _=False, p=part, c=colour: self._set(p, c))
                row.addWidget(chip)
            row.addStretch(1)
            lay.addLayout(row)
        self.refresh()

    @staticmethod
    def _chip(tip: str, colour: str | None) -> QToolButton:
        chip = QToolButton()
        chip.setFixedSize(20, 20)
        chip.setToolTip(tip)
        chip.setCursor(Qt.CursorShape.PointingHandCursor)
        if colour:
            chip.setStyleSheet(f"QToolButton {{ background: {colour}; border: 1px solid {RIM}; border-radius: 10px; }}")
        else:
            chip.setStyleSheet(f"QToolButton {{ border: 1px solid {RIM}; border-radius: 10px; color: gray; }}")
        return chip

    def refresh(self) -> None:
        """Show each part's current colour on its swatch."""
        for part, colour in keyboard_styles.custom_colours().items():
            swatch = self.swatches[part]
            swatch.setText("" if colour else "none")
            swatch.setStyleSheet(f"QPushButton {{ background: {colour}; border: 1px solid {RIM}; border-radius: 6px; }}"
                                 if colour else f"QPushButton {{ border: 1px dashed {RIM}; border-radius: 6px; color: gray; }}")

    def _set(self, part: str, colour: str | None) -> None:
        keyboard_styles.set_custom_colour(part, colour)
        self.refresh()
        self.changed.emit()

    def _pick(self, part: str, title: str) -> None:
        current = keyboard_styles.custom_colours()[part] or "#ffffff"
        colour = QColorDialog.getColor(QColor(current), self, f"Colour for the {title.lower()}")
        if colour.isValid():
            self._set(part, colour.name())


class ThemeCard(QPushButton):
    """A selectable tile that previews a theme: a miniature of the app window in light, in dark, or split for System."""

    LIGHT = dict(window="#efefef", panel="#ffffff", line="#c9c9c9", ink="#2a2a2a", faint="#b9b9b9",
                 accent="#3b8ed0", tint="#c9dce8")
    DARK = dict(window="#2b2b2b", panel="#232323", line="#454545", ink="#ececec", faint="#5a5a5a",
                accent="#2f7fe0", tint="#22364f")

    def __init__(self, key: str, label: str, note: str, parent=None):
        super().__init__(parent)
        self.theme_key = key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 168)
        self.preview = QWidget()
        self.preview.setFixedHeight(92)
        self.preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.preview.paintEvent = self._paint_preview
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)
        name = QLabel(f"<b>{label}</b>")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        blurb = QLabel(note)
        blurb.setStyleSheet("color: gray; font-size: 9pt;")
        blurb.setWordWrap(True)
        blurb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(self.preview)
        lay.addWidget(name)
        lay.addWidget(blurb)
        lay.addStretch(1)

    def _paint_preview(self, _event) -> None:
        p = QPainter(self.preview)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.preview.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.setClipPath(clip)
        if self.theme_key == "system":  # light on the left, dark on the right, split on a slant
            self._mock(p, r, self.LIGHT)
            right = QPainterPath()
            right.addPolygon(QPolygonF([QPointF(r.center().x() + 14, r.top()), r.topRight(), r.bottomRight(),
                                        QPointF(r.center().x() - 14, r.bottom())]))
            p.setClipPath(right.intersected(clip))
            self._mock(p, r, self.DARK)
        else:
            self._mock(p, r, self.LIGHT if self.theme_key == "light" else self.DARK)
        p.setClipping(False)  # an outline, so the dark preview shows against a dark window
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(128, 128, 128, 150), 1))
        p.drawRoundedRect(r, 8, 8)

    @staticmethod
    def _mock(p: QPainter, r: QRectF, c: dict) -> None:
        """A small drawing of the settings window: a list on the left, a staff with notes and a button on the right."""
        p.fillRect(r, QColor(c["window"]))
        side = QRectF(r.left() + 6, r.top() + 6, 40, r.height() - 12)
        p.setPen(QPen(QColor(c["line"]), 1))
        p.setBrush(QColor(c["panel"]))
        p.drawRoundedRect(side, 5, 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["tint"]))
        p.drawRoundedRect(QRectF(side.left() + 4, side.top() + 5, side.width() - 8, 9), 3, 3)
        p.setBrush(QColor(c["faint"]))
        for i in range(2):
            p.drawRoundedRect(QRectF(side.left() + 6, side.top() + 22 + i * 12, side.width() - 20 - i * 6, 4), 2, 2)
        card = QRectF(side.right() + 8, r.top() + 6, r.right() - side.right() - 14, r.height() - 12)
        p.setPen(QPen(QColor(c["line"]), 1))
        p.setBrush(QColor(c["panel"]))
        p.drawRoundedRect(card, 5, 5)
        p.setPen(QPen(QColor(c["ink"]), 0.8))
        top = card.top() + 12
        for i in range(5):
            p.drawLine(QPointF(card.left() + 6, top + i * 5), QPointF(card.right() - 6, top + i * 5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["ink"]))
        for x, row in ((20, 4), (38, 3), (56, 1), (74, 2)):
            p.drawEllipse(QPointF(card.left() + x, top + row * 2.5), 3.2, 2.5)
        p.setBrush(QColor(c["accent"]))
        p.drawRoundedRect(QRectF(card.left() + 6, card.bottom() - 17, 30, 10), 4, 4)


class AppSettingsDialog(QDialog):
    """Application-wide settings. Changes apply immediately."""


    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(1000, 640)
        self.theme_changed = False
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        # The categories sit in a list on the left; choosing one shows its settings on the right.
        self.categories = QListWidget()
        self.categories.setObjectName("categories")  # styled in style.py
        self.categories.setFixedWidth(170)
        self.pages = QStackedWidget()
        for name, page in (("Appearance", self._appearance_page()), ("Sound", self._sound_page())):
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(0, 36))
            self.categories.addItem(item)
            self.pages.addWidget(page)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.categories.setCurrentRow(0)
        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self.categories)
        body.addWidget(self.pages, 1)
        lay.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        lay.addWidget(buttons)

    @staticmethod
    def _page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        return page, lay

    @staticmethod
    def _heading(lay: QVBoxLayout, title: str, about: str) -> None:
        lay.addWidget(QLabel(f"<h3>{title}</h3>"))
        text = QLabel(about)
        text.setStyleSheet("color: gray;")
        text.setWordWrap(True)
        lay.addWidget(text)

    @staticmethod
    def _about(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: gray;")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _scrolling(page: QWidget) -> QScrollArea:
        """A page that scrolls when it is taller than the dialog."""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def _appearance_page(self) -> QWidget:
        """Three sections, switched with a segmented control: the colour theme, the notation style and the keyboard style."""
        page, lay = self._page()
        self.appearance_pages = QStackedWidget()
        self.appearance_pages.addWidget(self._theme_tab())
        self.appearance_pages.addWidget(self._scrolling(self._notation_tab()))
        self.appearance_pages.addWidget(self._scrolling(self._keyboard_tab()))
        self.segments = QFrame()
        self.segments.setObjectName("segments")
        row = QHBoxLayout(self.segments)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.segment_buttons = []
        for i, label in enumerate(("Theme", "Notation style", "Keyboard style")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setChecked(i == 0)
            group.addButton(b, i)
            b.clicked.connect(lambda _=False, k=i: self.appearance_pages.setCurrentIndex(k))
            row.addWidget(b)
            self.segment_buttons.append(b)
        self._style_segments()
        top = QHBoxLayout()
        top.addWidget(self.segments)
        top.addStretch(1)
        lay.addLayout(top)
        lay.addWidget(self.appearance_pages, 1)
        return page

    def _style_segments(self) -> None:
        """A rounded track with the chosen segment raised and tinted, from the current palette."""
        pal = self.palette()
        roles = (QPalette.ColorRole.Window, QPalette.ColorRole.Text, QPalette.ColorRole.Base, QPalette.ColorRole.Highlight)
        window, text, base, accent = (pal.color(r) for r in roles)
        track = blend(window, text, 0.07)
        self.segments.setStyleSheet(
            f"QFrame#segments {{ background: {track.name()}; border-radius: 12px; }}"
            "QFrame#segments QPushButton { border: 0; border-radius: 9px; padding: 6px 18px; background: transparent; }"
            f"QFrame#segments QPushButton:checked {{ background: {base.name()}; color: {accent.name()}; "
            f"border: 1px solid {pal.color(QPalette.ColorRole.Mid).name()}; }}")

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "segments"):
            self._style_segments()
        super().changeEvent(event)

    THEME_NOTES = {"system": "Follows your desktop's light or dark setting.", "light": "Always light.", "dark": "Always dark."}

    def _theme_tab(self) -> QWidget:
        page, lay = self._page()
        lay.addWidget(self._about("Follow the system's light or dark setting, or always use one of them."))
        row = QHBoxLayout()
        row.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.theme_cards = {}
        current = saved_theme()
        for key, label in THEMES:
            card = ThemeCard(key, label, self.THEME_NOTES.get(key, ""))
            card.setChecked(key == current)
            group.addButton(card)
            card.clicked.connect(lambda _=False, k=key: self.choose_theme(k))
            row.addWidget(card)
            self.theme_cards[key] = card
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(1)
        return page

    def _notation_tab(self) -> QWidget:
        page, lay = self._page()
        lay.addWidget(self._about("The music font used to draw clefs, notes and accidentals."))
        grid = QGridLayout()
        grid.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for i, st in enumerate(notation.STYLES):
            card = StyleCard(st)
            card.setChecked(st.key == notation.current().key)
            group.addButton(card)
            card.clicked.connect(lambda _=False, k=st.key: self._choose_notation(k))
            grid.addWidget(card, i // 3, i % 3)
        grid.setColumnStretch(3, 1)  # keep the cards at the left edge
        lay.addLayout(grid)

        lay.addSpacing(8)
        lay.addWidget(QLabel("<h3>Baritone clef</h3>"))
        lay.addWidget(self._about("The baritone clef can be written two ways. The staff and the notes on it are the same."))
        self.baritone_buttons = {}
        baritone_group = QButtonGroup(self)
        for kind, label in notation.BARITONE_CLEFS.items():
            radio = QRadioButton(label)
            radio.setChecked(kind == notation.baritone_clef())
            baritone_group.addButton(radio)
            radio.clicked.connect(lambda _=False, k=kind: notation.set_baritone_clef(k))
            self.baritone_buttons[kind] = radio
            lay.addWidget(radio)
        self._draw_baritone_icons()
        lay.addStretch(1)
        return page

    def _choose_notation(self, key: str) -> None:
        notation.set_style(key)
        self._draw_baritone_icons()  # the two baritone clefs are pictured in the font just chosen

    def _draw_baritone_icons(self) -> None:
        for kind, radio in self.baritone_buttons.items():
            picture = ClefPictures([f"baritone_{kind}"], 1.4)
            radio.setIcon(picture.to_icon())
            radio.setIconSize(picture.size())

    def _keyboard_tab(self) -> QWidget:
        page, lay = self._page()
        lay.addWidget(self._about("How the piano keyboard looks: the colours and materials of its keys."))
        grid = QGridLayout()
        grid.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.keyboard_cards = {}
        styles = (*keyboard_styles.STYLES, keyboard_styles.custom_style())
        for i, st in enumerate(styles):
            card = KeyboardCard(st)
            card.setChecked(st.key == keyboard_styles.current().key)
            group.addButton(card)
            card.clicked.connect(lambda _=False, k=st.key: keyboard_styles.set_style(k))
            grid.addWidget(card, i // 3, i % 3)
            self.keyboard_cards[st.key] = card
        grid.setColumnStretch(3, 1)  # keep the cards at the left edge
        lay.addLayout(grid)
        self.builder = KeyboardBuilder()
        self.builder.changed.connect(self._custom_edited)
        lay.addWidget(self.builder)
        lay.addStretch(1)
        return page

    def _custom_edited(self) -> None:
        """A part was recoloured: the Custom card shows the result and becomes the chosen one."""
        card = self.keyboard_cards[keyboard_styles.CUSTOM]
        card.show_style(keyboard_styles.custom_style())
        card.setChecked(True)

    def _sound_page(self) -> QWidget:
        page, lay = self._page()
        self._heading(lay, "Instrument",
                      "The sound used for notes and for the correct-answer chime. Choose an instrument to see what it is "
                      "made from, and press Hear it to listen.")
        self.instruments = InstrumentPicker()
        lay.addWidget(self.instruments, 1)
        return page

    def choose_theme(self, key: str) -> None:
        save_theme(key)
        apply_theme(key)
        self.theme_changed = True
