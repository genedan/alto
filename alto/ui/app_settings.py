"""
The application-wide settings dialog: the colour theme, the notation font, the keyboard style and the instrument.

Changes apply as soon as they are made. Each style is a card that previews it.

Examples
--------
>>> dialog = AppSettingsDialog()
>>> dialog.windowTitle()
'Settings'
>>> dialog.pages.count()  # Appearance and Sound
2
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPalette, QPen, QPolygonF
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
    """
    A selectable tile that previews a notation style: a short phrase on a staff, drawn in that style.

    Attributes
    ----------
    style_key : str
        The key of the style the card stands for.
    staff : StaffWidget
        The preview.

    Examples
    --------
    >>> card = StyleCard(notation.BY_KEY["leland"])
    >>> card.style_key, card.isCheckable()
    ('leland', True)
    """

    def __init__(
        self,
        style: notation.NotationStyle,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the card for a notation style.

        Parameters
        ----------
        style : NotationStyle
            The style to preview; its label and a few words about it are shown under the staff.
        parent : QWidget or None, default None
            The widget that owns the card. Keyword-only.

        Examples
        --------
        >>> StyleCard(notation.BY_KEY["bravura"]).width()
        232
        """
        super().__init__(parent)
        self.style_key = style.key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            8,
            8,
            8,
            6,
        )
        lay.setSpacing(4)
        self.staff = StaffWidget(
            gap=6.5,
            side=8.0,
            note_offset=44.0,
            margin=3.2,
            compact=True,
        )
        self.staff.notation_style = style
        self.staff.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.staff.setFixedWidth(214)
        self.staff.show_notes(
            [
                [Note(4, letter=2)],
                [Note(4, letter=4)],
                [Note(5, letter=0)],
                [Note(4, letter=6)],
            ],
            clef="treble",
            key=1,
            value="quarter",
        )
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
    """
    A selectable tile that previews a keyboard style: a short stretch of keys drawn in that style.

    Attributes
    ----------
    style_key : str
        The key of the style the card stands for.
    keys : KeyboardWidget
        The preview.

    Examples
    --------
    >>> card = KeyboardCard(keyboard_styles.BY_KEY["modern"])
    >>> card.style_key
    'modern'
    """

    def __init__(
        self,
        style: keyboard_styles.KeyboardStyle,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the card for a keyboard style.

        Parameters
        ----------
        style : KeyboardStyle
            The style to preview; its label and a few words about it are shown under the keys.
        parent : QWidget or None, default None
            The widget that owns the card. Keyword-only.

        Examples
        --------
        >>> KeyboardCard(keyboard_styles.BY_KEY["classic"]).keys.style_override.key
        'classic'
        """
        super().__init__(parent)
        self.style_key = style.key
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 222)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            8,
            8,
            8,
            6,
        )
        lay.setSpacing(4)
        self.keys = KeyboardWidget()
        self.keys.style_override = style
        self.keys.pad = 6.0
        self.keys.max_key_width = 16.0
        self.keys.setFixedWidth(2 * 6 + 10 * 16)  # ten white keys, C4 to E5
        self.keys.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.keys.show_key(None, span=(60, 76))
        holder = QWidget()
        holder.setFixedHeight(int(2 * 6 + 30 + 16 * 6.2))  # room for the tallest strip above the keys
        holder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        holder_lay = QVBoxLayout(holder)
        holder_lay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
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
        """
        Redraw the preview in a style.

        The custom card follows the colours being edited.

        Parameters
        ----------
        style : KeyboardStyle
            The style to preview.

        Examples
        --------
        >>> card = KeyboardCard(keyboard_styles.BY_KEY["classic"])
        >>> card.show_style(keyboard_styles.BY_KEY["modern"])
        >>> card.keys.style_override.key
        'modern'
        """
        self.keys.style_override = style
        self.keys.refit()


class KeyboardBuilder(QFrame):
    """
    Rows for colouring each part of a keyboard.

    Each has a swatch that opens the colour picker, and chips for colours named after materials. Changing anything selects
    the Custom style.

    Attributes
    ----------
    changed : Signal
        Emitted after a part is recoloured.
    swatches : dict of str to QPushButton
        The swatch of each part ("naturals", "sharps", "case", "felt" and "caps").

    Examples
    --------
    >>> builder = KeyboardBuilder()
    >>> sorted(builder.swatches)
    ['caps', 'case', 'felt', 'naturals', 'sharps']
    """

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Build the rows and show each part's current colour.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the builder.

        Examples
        --------
        >>> KeyboardBuilder().swatches["naturals"].width()
        46
        """
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(
            0,
            8,
            0,
            0,
        )
        lay.setSpacing(6)
        lay.addWidget(QLabel("<b>Build your own</b>"))
        about = QLabel(
            "Choose a colour for each part, from a material or with the colour picker. "
            "Changing any part switches to the Custom style.",
        )
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
            swatch.clicked.connect(lambda _=False, p=part, t=label: self._pick(p, title=t))
            row.addWidget(swatch)
            row.addSpacing(6)
            self.swatches[part] = swatch
            if optional:
                none = self._chip("None", colour=None)
                none.setText("✕")
                none.clicked.connect(lambda _=False, p=part: self._set(p, colour=None))
                row.addWidget(none)
            else:
                row.addSpacing(24)  # line the chips up with the rows that have a None chip
            for material, colour in keyboard_styles.MATERIALS:
                chip = self._chip(f"{material}  {colour}", colour=colour)
                chip.clicked.connect(lambda _=False, p=part, c=colour: self._set(p, colour=c))
                row.addWidget(chip)
            row.addStretch(1)
            lay.addLayout(row)
        self.refresh()

    @staticmethod
    def _chip(
        tip: str,
        *,
        colour: str | None,
    ) -> QToolButton:
        """
        Make a small round colour chip.

        Parameters
        ----------
        tip : str
            The tooltip, such as the material's name and colour.
        colour : str or None
            The chip's colour, or None for the "leave this part out" chip.

        Returns
        -------
        QToolButton
            The chip.

        Examples
        --------
        >>> chip = KeyboardBuilder._chip("Ivory  #f1e5c6", colour="#f1e5c6")
        >>> chip.toolTip()
        'Ivory  #f1e5c6'
        """
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
        """
        Show each part's current colour on its swatch.

        Examples
        --------
        >>> builder = KeyboardBuilder()
        >>> builder.refresh()
        >>> builder.swatches["naturals"].text()  # a colour is set, so the swatch shows it, not "none"
        ''
        """
        for part, colour in keyboard_styles.custom_colours().items():
            swatch = self.swatches[part]
            swatch.setText("" if colour else "none")
            swatch.setStyleSheet(
                f"QPushButton {{ background: {colour}; border: 1px solid {RIM}; border-radius: 6px; }}"
                if colour
                else f"QPushButton {{ border: 1px dashed {RIM}; border-radius: 6px; color: gray; }}",
            )

    def _set(
        self,
        part: str,
        *,
        colour: str | None,
    ) -> None:
        """
        Recolour a part (or leave it out) and switch to the custom style.

        Parameters
        ----------
        part : str
            "naturals", "sharps", "case", "felt" or "caps".
        colour : str or None
            The new colour, or None to leave an optional part out. Keyword-only.

        Examples
        --------
        >>> builder = KeyboardBuilder()
        >>> changes = []
        >>> _ = builder.changed.connect(lambda: changes.append(1))
        >>> builder._set("naturals", colour="#ffffff")
        >>> keyboard_styles.custom_colours()["naturals"], changes
        ('#ffffff', [1])
        >>> builder._set("naturals", colour=keyboard_styles.DEFAULT_CUSTOM["naturals"])
        >>> keyboard_styles.set_style(keyboard_styles.DEFAULT)
        """
        keyboard_styles.set_custom_colour(part, colour=colour)
        self.refresh()
        self.changed.emit()

    def _pick(
        self,
        part: str,
        *,
        title: str,
    ) -> None:
        """
        Open the colour picker for a part and apply the colour chosen.

        Parameters
        ----------
        part : str
            "naturals", "sharps", "case", "felt" or "caps".
        title : str
            The part's label, used in the picker's title. Keyword-only.

        Examples
        --------
        >>> KeyboardBuilder()._pick("case", title="Case")  # doctest: +SKIP
        """
        current = keyboard_styles.custom_colours()[part] or "#ffffff"
        colour = QColorDialog.getColor(QColor(current), self, f"Colour for the {title.lower()}")
        if colour.isValid():
            self._set(part, colour=colour.name())


class ThemeCard(QPushButton):
    """
    A selectable tile that previews a theme: a miniature of the app window in light, in dark, or split for System.

    Attributes
    ----------
    LIGHT, DARK : dict of str to str
        The colours of the miniature in each theme.
    theme_key : str
        "system", "light" or "dark".
    preview : QWidget
        The miniature.

    Examples
    --------
    >>> ThemeCard("dark", label="Dark", note="Always dark.").theme_key
    'dark'
    """

    LIGHT = dict(
        window="#efefef",
        panel="#ffffff",
        line="#c9c9c9",
        ink="#2a2a2a",
        faint="#b9b9b9",
        accent="#3b8ed0",
        tint="#c9dce8",
    )
    DARK = dict(
        window="#2b2b2b",
        panel="#232323",
        line="#454545",
        ink="#ececec",
        faint="#5a5a5a",
        accent="#2f7fe0",
        tint="#22364f",
    )

    def __init__(
        self,
        key: str,
        *,
        label: str,
        note: str,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the card for a theme.

        Parameters
        ----------
        key : str
            "system", "light" or "dark".
        label : str
            The name shown under the preview. Keyword-only.
        note : str
            A short explanation shown under the name. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the card. Keyword-only.

        Examples
        --------
        >>> ThemeCard("system", label="System", note="Follows your desktop.").height()
        168
        """
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
        lay.setContentsMargins(
            8,
            8,
            8,
            6,
        )
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

    def _paint_preview(self, _event: QPaintEvent) -> None:
        """
        Draw the miniature: light, dark, or the two side by side for System.

        Parameters
        ----------
        _event : QPaintEvent
            The paint request.

        Examples
        --------
        >>> card = ThemeCard("system", label="System", note="Follows your desktop.")
        >>> card.preview.grab().isNull()
        False
        """
        p = QPainter(self.preview)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.preview.rect()).adjusted(
            0.5,
            0.5,
            -0.5,
            -0.5,
        )
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.setClipPath(clip)
        if self.theme_key == "system":  # light on the left, dark on the right, split on a slant
            self._mock(p, r=r, c=self.LIGHT)
            right = QPainterPath()
            right.addPolygon(
                QPolygonF(
                    [
                        QPointF(r.center().x() + 14, r.top()),
                        r.topRight(),
                        r.bottomRight(),
                        QPointF(r.center().x() - 14, r.bottom()),
                    ],
                ),
            )
            p.setClipPath(right.intersected(clip))
            self._mock(p, r=r, c=self.DARK)
        else:
            self._mock(p, r=r, c=self.LIGHT if self.theme_key == "light" else self.DARK)
        p.setClipping(False)  # an outline, so the dark preview shows against a dark window
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(
            QPen(
                QColor(
                    128,
                    128,
                    128,
                    150,
                ),
                1,
            ),
        )
        p.drawRoundedRect(r, 8, 8)

    @staticmethod
    def _mock(
        p: QPainter,
        *,
        r: QRectF,
        c: dict,
    ) -> None:
        """
        Draw a small picture of the settings window: a list on the left, a staff with notes and a button on the right.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        r : QRectF
            Where to draw it. Keyword-only.
        c : dict of str to str
            The colours to use, `ThemeCard.LIGHT` or `ThemeCard.DARK`. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(120, 80, QImage.Format.Format_ARGB32)
        >>> painter = QPainter(image)
        >>> ThemeCard._mock(painter, r=QRectF(0, 0, 120, 80), c=ThemeCard.LIGHT)
        >>> painter.end()
        True
        >>> image.pixelColor(2, 2).name()  # the window colour fills the margin
        '#efefef'
        """
        p.fillRect(r, QColor(c["window"]))
        side = QRectF(
            r.left() + 6,
            r.top() + 6,
            40,
            r.height() - 12,
        )
        p.setPen(QPen(QColor(c["line"]), 1))
        p.setBrush(QColor(c["panel"]))
        p.drawRoundedRect(side, 5, 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["tint"]))
        p.drawRoundedRect(
            QRectF(
                side.left() + 4,
                side.top() + 5,
                side.width() - 8,
                9,
            ),
            3,
            3,
        )
        p.setBrush(QColor(c["faint"]))
        for i in range(2):
            p.drawRoundedRect(
                QRectF(
                    side.left() + 6,
                    side.top() + 22 + i * 12,
                    side.width() - 20 - i * 6,
                    4,
                ),
                2,
                2,
            )
        card = QRectF(
            side.right() + 8,
            r.top() + 6,
            r.right() - side.right() - 14,
            r.height() - 12,
        )
        p.setPen(QPen(QColor(c["line"]), 1))
        p.setBrush(QColor(c["panel"]))
        p.drawRoundedRect(card, 5, 5)
        p.setPen(QPen(QColor(c["ink"]), 0.8))
        top = card.top() + 12
        for i in range(5):
            p.drawLine(QPointF(card.left() + 6, top + i * 5), QPointF(card.right() - 6, top + i * 5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["ink"]))
        for x, row in (
            (20, 4),
            (38, 3),
            (56, 1),
            (74, 2),
        ):
            p.drawEllipse(QPointF(card.left() + x, top + row * 2.5), 3.2, 2.5)
        p.setBrush(QColor(c["accent"]))
        p.drawRoundedRect(
            QRectF(
                card.left() + 6,
                card.bottom() - 17,
                30,
                10,
            ),
            4,
            4,
        )


class AppSettingsDialog(QDialog):
    """
    Application-wide settings. Changes apply immediately.

    Attributes
    ----------
    theme_changed : bool
        True once the theme has been changed, so the window can be rebuilt in it.
    categories : QListWidget
        The list of pages on the left: Appearance and Sound.
    pages : QStackedWidget
        The page for the chosen category.
    instruments : InstrumentPicker
        The instrument chooser on the Sound page.

    Examples
    --------
    >>> dialog = AppSettingsDialog()
    >>> dialog.theme_changed
    False
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Build the dialog with the Appearance page showing.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the dialog.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog.categories.currentRow()
        0
        """
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
        """
        Make an empty page with a vertical layout.

        Returns
        -------
        tuple of (QWidget, QVBoxLayout)
            The page and its layout.

        Examples
        --------
        >>> page, layout = AppSettingsDialog._page()
        >>> layout.count()
        0
        """
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(
            4,
            4,
            4,
            4,
        )
        lay.setSpacing(10)
        return page, lay

    @staticmethod
    def _heading(
        lay: QVBoxLayout,
        *,
        title: str,
        about: str,
    ) -> None:
        """
        Add a heading and a line of grey explanation to a layout.

        Parameters
        ----------
        lay : QVBoxLayout
            The layout to add to.
        title : str
            The heading. Keyword-only.
        about : str
            The explanation under it. Keyword-only.

        Examples
        --------
        >>> layout = QVBoxLayout()
        >>> AppSettingsDialog._heading(layout, title="Instrument", about="The sound used for notes.")
        >>> layout.count()
        2
        """
        lay.addWidget(QLabel(f"<h3>{title}</h3>"))
        text = QLabel(about)
        text.setStyleSheet("color: gray;")
        text.setWordWrap(True)
        lay.addWidget(text)

    @staticmethod
    def _about(text: str) -> QLabel:
        """
        Make a line of grey explanatory text.

        Parameters
        ----------
        text : str
            What to say.

        Returns
        -------
        QLabel
            The label, which wraps to fit.

        Examples
        --------
        >>> AppSettingsDialog._about("The music font.").text()
        'The music font.'
        """
        label = QLabel(text)
        label.setStyleSheet("color: gray;")
        label.setWordWrap(True)
        return label

    @staticmethod
    def _scrolling(page: QWidget) -> QScrollArea:
        """
        Wrap a page so that it scrolls when it is taller than the dialog.

        Parameters
        ----------
        page : QWidget
            The page.

        Returns
        -------
        QScrollArea
            A scroll area holding the page, with no horizontal scroll bar.

        Examples
        --------
        >>> page = QWidget()
        >>> AppSettingsDialog._scrolling(page).widget() is page
        True
        """
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def _appearance_page(self) -> QWidget:
        """
        Build the Appearance page.

        It has three sections, switched with a segmented control: the colour theme, the notation style and the keyboard style.

        Returns
        -------
        QWidget
            The page.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog.appearance_pages.count()
        3
        """
        page, lay = self._page()
        self.appearance_pages = QStackedWidget()
        self.appearance_pages.addWidget(self._theme_tab())
        self.appearance_pages.addWidget(self._scrolling(self._notation_tab()))
        self.appearance_pages.addWidget(self._scrolling(self._keyboard_tab()))
        self.segments = QFrame()
        self.segments.setObjectName("segments")
        row = QHBoxLayout(self.segments)
        row.setContentsMargins(
            3,
            3,
            3,
            3,
        )
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
        """
        Style the segmented control: a rounded track with the chosen segment raised and tinted, from the current palette.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog._style_segments()
        >>> "segments" in dialog.segments.styleSheet()
        True
        """
        pal = self.palette()
        roles = (
            QPalette.ColorRole.Window,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.Base,
            QPalette.ColorRole.Highlight,
        )
        window, text, base, accent = (pal.color(r) for r in roles)
        track = blend(window, b=text, t=0.07)
        self.segments.setStyleSheet(
            f"QFrame#segments {{ background: {track.name()}; border-radius: 12px; }}"
            "QFrame#segments QPushButton { border: 0; border-radius: 9px; padding: 6px 18px; background: transparent; }"
            f"QFrame#segments QPushButton:checked {{ background: {base.name()}; color: {accent.name()}; "
            f"border: 1px solid {pal.color(QPalette.ColorRole.Mid).name()}; }}",
        )

    def changeEvent(self, event: QEvent) -> None:
        """
        Restyle the segmented control when the palette changes, so it follows the theme.

        Parameters
        ----------
        event : QEvent
            The change.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog.changeEvent(QEvent(QEvent.Type.PaletteChange))
        """
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "segments"):
            self._style_segments()
        super().changeEvent(event)

    THEME_NOTES = {"system": "Follows your desktop's light or dark setting.", "light": "Always light.", "dark": "Always dark."}

    def _theme_tab(self) -> QWidget:
        """
        Build the theme section: a card for System, Light and Dark.

        Returns
        -------
        QWidget
            The page.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> sorted(dialog.theme_cards)
        ['dark', 'light', 'system']
        """
        page, lay = self._page()
        lay.addWidget(self._about("Follow the system's light or dark setting, or always use one of them."))
        row = QHBoxLayout()
        row.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.theme_cards = {}
        current = saved_theme()
        for key, label in THEMES:
            card = ThemeCard(key, label=label, note=self.THEME_NOTES.get(key, ""))
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
        """
        Build the notation section: a card for each music font, and the choice of how the baritone clef is written.

        Returns
        -------
        QWidget
            The page.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> sorted(dialog.baritone_buttons)
        ['c', 'f']
        """
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
        """
        Choose a notation font and redraw the baritone pictures in it.

        Parameters
        ----------
        key : str
            A key of `notation.BY_KEY`.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog._choose_notation("leland")
        >>> notation.current().key
        'leland'
        >>> dialog._choose_notation(notation.DEFAULT)
        """
        notation.set_style(key)
        self._draw_baritone_icons()  # the two baritone clefs are pictured in the font just chosen

    def _draw_baritone_icons(self) -> None:
        """
        Draw the two ways of writing the baritone clef on their buttons, in the notation font in use.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog._draw_baritone_icons()
        >>> dialog.baritone_buttons["f"].icon().isNull()
        False
        """
        for kind, radio in self.baritone_buttons.items():
            picture = ClefPictures([f"baritone_{kind}"], scale=1.4)
            radio.setIcon(picture.to_icon())
            radio.setIconSize(picture.size())

    def _keyboard_tab(self) -> QWidget:
        """
        Build the keyboard section: a card for each style, and the builder for your own.

        Returns
        -------
        QWidget
            The page.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> keyboard_styles.CUSTOM in dialog.keyboard_cards
        True
        """
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
        """
        Show the result of recolouring a part on the Custom card and make it the chosen one.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog._custom_edited()
        >>> dialog.keyboard_cards[keyboard_styles.CUSTOM].isChecked()
        True
        """
        card = self.keyboard_cards[keyboard_styles.CUSTOM]
        card.show_style(keyboard_styles.custom_style())
        card.setChecked(True)

    def _sound_page(self) -> QWidget:
        """
        Build the Sound page: the instrument chooser.

        Returns
        -------
        QWidget
            The page.

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog.instruments.list.count() > 0
        True
        """
        page, lay = self._page()
        self._heading(
            lay,
            title="Instrument",
            about="The sound used for notes and for the correct-answer chime. Choose an instrument to see what it is "
            "made from, and press Hear it to listen.",
        )
        self.instruments = InstrumentPicker()
        lay.addWidget(self.instruments, 1)
        return page

    def choose_theme(self, key: str) -> None:
        """
        Switch the colour theme, remember it, and note that the window should be rebuilt in it.

        Parameters
        ----------
        key : str
            "system", "light" or "dark".

        Examples
        --------
        >>> dialog = AppSettingsDialog()
        >>> dialog.choose_theme("light")
        >>> dialog.theme_changed, saved_theme()
        (True, 'light')
        >>> dialog.choose_theme("system")
        """
        save_theme(key)
        apply_theme(key)
        self.theme_changed = True
