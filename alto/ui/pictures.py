"""
Small pictures of musical things (clefs, note values, key signatures, note ranges ...) for the settings panes.

Each picture is drawn in fixed units and then scaled, so the same picture serves as a summary in a menu row and, larger,
as the label of a choice. Colours come from the palette, so they work in light and dark themes.

Examples
--------
>>> CLEF_NAMES["treble"], VALUE_NAMES["sixteenth"]
('Treble', '16th')
>>> ClefPictures(["treble", "bass"]).toolTip()
'Treble, Bass'
"""

from __future__ import annotations

from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QPixmap,
    QRegion,
)
from PySide6.QtWidgets import QWidget

from alto.settings import SOLFEGE
from alto.theory.pitch import (
    MAJOR_KEYS,
    Note,
)
from alto.ui import engraving
from alto.ui.colors import blend
from alto.ui.notation import current as current_style
from alto.ui.staff import (
    BOTTOM_LINE,
    MIDDLE_C,
    StaffWidget,
)

CLEF_NAMES = {
    "treble": "Treble",
    "bass": "Bass",
    "alto": "Alto",
    "tenor": "Tenor",
    "soprano": "Soprano",
    "mezzo": "Mezzo-soprano",
    "baritone": "Baritone",
    "grand": "Grand staff",
    "baritone_f": "Baritone (F clef)",
    "baritone_c": "Baritone (C clef)",
}  # the two ways of writing the baritone clef
VALUE_NAMES = {
    "breve": "Breve",
    "whole": "Whole",
    "half": "Half",
    "quarter": "Quarter",
    "eighth": "Eighth",
    "sixteenth": "16th",
    "thirty_second": "32nd",
}


class _Picture(QWidget):
    """
    Base class: a widget drawn in its own units, enlarged by `scale`, that ignores the mouse.

    Attributes
    ----------
    scale : float
        How much the picture is enlarged.

    Examples
    --------
    >>> picture = _Picture(2.0)
    >>> picture._fit(10, height=20)
    >>> (picture.width(), picture.height())
    (20, 40)
    """

    def __init__(
        self,
        scale: float = 1.0,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a picture that lets mouse clicks through to what is underneath.

        Parameters
        ----------
        scale : float, default 1.0
            How much to enlarge the picture.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> _Picture(1.5).scale
        1.5
        """
        super().__init__(parent)
        self.scale = scale
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row or checkbox underneath is the click target

    def _fit(
        self,
        width: float,
        *,
        height: float,
    ) -> None:
        """
        Make the widget the size of the picture at the current scale.

        Parameters
        ----------
        width : float
            The picture's width in its own units.
        height : float
            The picture's height in its own units. Keyword-only.

        Examples
        --------
        >>> picture = _Picture(2.0)
        >>> picture._fit(30, height=34)
        >>> picture.size().width(), picture.size().height()
        (60, 68)
        """
        self.setFixedSize(round(width * self.scale), round(height * self.scale))

    def _colours(self) -> tuple[QColor, QColor]:
        """
        Return the colours to draw with.

        Returns
        -------
        tuple of (QColor, QColor)
            The ink, and a softer ink for staff lines. Both are readable against the background in light and dark themes.

        Examples
        --------
        >>> ink, line_ = _Picture()._colours()
        >>> ink.isValid() and line_.isValid()
        True
        """
        pal = self.palette()
        text, base = pal.color(QPalette.ColorRole.Text), pal.color(QPalette.ColorRole.Base)
        line = blend(base, b=text, t=0.62)
        return text, line

    def _painter(self) -> QPainter:
        """
        Start painting the picture: anti-aliased, scaled, and with the device scale noted.

        Must be called while the widget is being painted (from `paintEvent`).

        Returns
        -------
        QPainter
            The painter, which the caller must end.

        Examples
        --------
        >>> # noinspection PyProtectedMember
        >>> p_ = NamePicture()._painter()  # doctest: +SKIP
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(self.scale, self.scale)
        self._dev = abs(p.deviceTransform().m11()) or 1.0  # device pixels per picture unit
        return p

    # noinspection DuplicatedCode
    def _hline(
        self,
        p: QPainter,
        *,
        x0: float,
        x1: float,
        y: float,
        colour: QColor,
        width: float = 1.0,
    ) -> None:
        """
        Draw a horizontal line a whole number of device pixels thick, placed on the pixel grid.

        Staff lines then come out crisp and equally strong at any scale.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x0 : float
            The left end, in picture units. Keyword-only.
        x1 : float
            The right end. Keyword-only.
        y : float
            The height of the line. Keyword-only.
        colour : QColor
            The colour. Keyword-only.
        width : float, default 1.0
            The thickness in picture units. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(20, 20, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> picture = _Picture()
        >>> picture._dev = 1.0  # one device pixel per picture unit
        >>> picture._hline(painter, x0=0, x1=20, y=10, colour=QColor("black"))
        >>> painter.end()
        True
        >>> image.pixelColor(10, 10).lightness() < 128
        True
        """
        d = self._dev
        n = max(round(width * d), 1)
        y = (int(y * d) + 0.5) / d if n % 2 else round(y * d) / d
        p.setPen(
            QPen(
                colour,
                n / d,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
            ),
        )
        p.drawLine(QPointF(x0, y), QPointF(x1, y))

    # noinspection DuplicatedCode
    def _vline(
        self,
        p: QPainter,
        *,
        x: float,
        y0: float,
        y1: float,
        colour: QColor,
        width: float = 1.0,
    ) -> None:
        """
        Draw a vertical line a whole number of device pixels thick, placed on the pixel grid.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The line's x position, in picture units. Keyword-only.
        y0 : float
            The top end. Keyword-only.
        y1 : float
            The bottom end. Keyword-only.
        colour : QColor
            The colour. Keyword-only.
        width : float, default 1.0
            The thickness in picture units. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(20, 20, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> picture = _Picture()
        >>> picture._dev = 1.0
        >>> picture._vline(painter, x=10, y0=0, y1=20, colour=QColor("black"))
        >>> painter.end()
        True
        >>> image.pixelColor(10, 10).lightness() < 128
        True
        """
        d = self._dev
        n = max(round(width * d), 1)
        x = (int(x * d) + 0.5) / d if n % 2 else round(x * d) / d
        p.setPen(
            QPen(
                colour,
                n / d,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
            ),
        )
        p.drawLine(QPointF(x, y0), QPointF(x, y1))

    def to_icon(self) -> QIcon:
        """
        Return the picture as an icon, for example to label a checkbox.

        Drawn crisply at twice the screen resolution.

        Returns
        -------
        QIcon
            The icon.

        Examples
        --------
        >>> ClefPictures(["treble"]).to_icon().isNull()
        False
        """
        ratio = 2.0
        pixmap = QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(
            pixmap,
            QPoint(),
            QRegion(),
            QWidget.RenderFlag.DrawChildren,
        )  # just the picture, not the widget background
        return QIcon(pixmap)

    def _staff(
        self,
        p: QPainter,
        *,
        x0: float,
        x1: float,
        bottom: float,
        gap: float,
        colour: QColor,
    ) -> None:
        """
        Draw five staff lines.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x0 : float
            The left end, in picture units. Keyword-only.
        x1 : float
            The right end. Keyword-only.
        bottom : float
            The height of the bottom line. Keyword-only.
        gap : float
            The distance between lines. Keyword-only.
        colour : QColor
            The colour. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(40, 40, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> picture = _Picture()
        >>> picture._dev = 1.0
        >>> picture._staff(painter, x0=0, x1=40, bottom=30, gap=5, colour=QColor("black"))
        >>> painter.end()
        True
        """
        for n in range(5):
            self._hline(
                p,
                x0=x0,
                x1=x1,
                y=bottom - n * gap,
                colour=colour,
                width=0.65,
            )


class ClefPictures(_Picture):
    """
    The selected clefs, each on its own five-line staff, and a two-stave picture with a brace for the grand staff.

    Showing each clef on its own staff lets alto and tenor, which share a symbol, look different.

    Attributes
    ----------
    H, W, GAP, SPACING : float
        The picture's height, the width of one clef, the distance between staff lines and the space between clefs.
    NAMES : dict of str to str
        The name of each clef.
    clefs : list of str
        The clefs shown.

    Examples
    --------
    >>> ClefPictures(["alto", "tenor"]).toolTip()
    'Alto, Tenor'
    """

    H, W, GAP, SPACING = 34, 30, 3.4, 8
    NAMES = CLEF_NAMES

    def __init__(
        self,
        clefs: list[str] | None = None,
        *,
        scale: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the picture.

        Parameters
        ----------
        clefs : list of str or None, default None
            The clefs to show, any of `CLEF_NAMES`.
        scale : float, default 1.0
            How much to enlarge it. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> ClefPictures(["treble"], scale=2.0).width()
        60
        """
        super().__init__(scale, parent=parent)
        self.clefs: list[str] = []
        self.set_clefs(clefs or [])

    # noinspection DuplicatedCode
    def set_clefs(self, clefs: list[str]) -> None:
        """
        Show different clefs and size the picture for them.

        Parameters
        ----------
        clefs : list of str
            The clefs to show, any of `CLEF_NAMES`.

        Examples
        --------
        >>> pictures = ClefPictures()
        >>> pictures.set_clefs(["treble", "bass", "alto"])
        >>> pictures.width()  # three clefs and the space between them
        106
        >>> pictures.toolTip()
        'Treble, Bass, Alto'
        """
        self.clefs = list(clefs)
        count = max(len(self.clefs), 1)
        self._fit(count * self.W + (count - 1) * self.SPACING, height=self.H)
        self.setToolTip(", ".join(CLEF_NAMES[c] for c in self.clefs))
        self.update()

    @classmethod
    def icon(
        cls,
        clef: str,
        *,
        scale: float = 1.8,
    ) -> QIcon:
        """
        Return one clef as an icon.

        Parameters
        ----------
        clef : str
            A key of `CLEF_NAMES`.
        scale : float, default 1.8
            How much to enlarge it. Keyword-only.

        Returns
        -------
        QIcon
            The icon.

        Examples
        --------
        >>> ClefPictures.icon("grand").isNull()
        False
        """
        return cls([clef], scale=scale).to_icon()

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw each clef on its staff, or the grand staff with its brace.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> ClefPictures(["treble", "grand"]).grab().isNull()
        False
        """
        p = self._painter()
        text, line = self._colours()
        for i, clef in enumerate(self.clefs):
            x = i * (self.W + self.SPACING)
            if clef == "grand":
                self._grand(
                    p,
                    x=x,
                    text=text,
                    line=line,
                )
                continue
            self._staff(
                p,
                x0=x + 1,
                x1=x + self.W - 1,
                bottom=24.0,
                gap=self.GAP,
                colour=line,
            )
            # noinspection PyProtectedMember
            StaffWidget._draw_clef(
                p,
                clef=clef,
                x=x + 3,
                bottom=24.0,
                gap=self.GAP,
                color=text,
                font=current_style().font,
            )

    def _grand(
        self,
        p: QPainter,
        *,
        x: float,
        text: QColor,
        line: QColor,
    ) -> None:
        """
        Draw the grand staff: two staves joined by a line and a brace.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The left edge, in picture units. Keyword-only.
        text : QColor
            The colour of the clefs and brace. Keyword-only.
        line : QColor
            The colour of the staff lines. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(40, 40, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> pictures = ClefPictures()
        >>> pictures._dev = 1.0
        >>> pictures._grand(painter, x=0, text=QColor("black"), line=QColor("gray"))
        >>> painter.end()
        True
        """
        gap, tops = 2.1, (6.0, 22.6)  # y of the top line of each stave
        for top, clef in zip(tops, ("treble", "bass")):
            bottom = top + 4 * gap
            self._staff(
                p,
                x0=x + 5,
                x1=x + self.W - 1,
                bottom=bottom,
                gap=gap,
                colour=line,
            )
            # noinspection PyProtectedMember
            StaffWidget._draw_clef(
                p,
                clef=clef,
                x=x + 8,
                bottom=bottom,
                gap=gap,
                color=text,
                font=current_style().font,
            )
        self._vline(
            p,
            x=x + 5,
            y0=tops[0],
            y1=tops[1] + 4 * gap,
            colour=line,
            width=0.65,
        )
        # noinspection PyProtectedMember
        StaffWidget._brace(
            p,
            x=x + 4,
            y0=tops[0],
            y1=tops[1] + 4 * gap,
            color=text,
            wd=3.5,
            font=current_style().font,
        )


class ValuePictures(_Picture):
    """
    Note values as engraved symbols (no staff), each with its head on the same baseline so they line up.

    Attributes
    ----------
    values : list of str
        The note values shown, keys of `VALUE_NAMES`.
    centre_stemless : bool
        Whether the breve and whole note sit at the picture's vertical centre.

    Examples
    --------
    >>> pictures = ValuePictures(["whole", "quarter", "eighth"])
    >>> pictures.values
    ['whole', 'quarter', 'eighth']
    """

    H, W, GAP, SPACING = 40, 18, 4.5, 4
    HEAD_X, HEAD_Y = 6.5, 25.0  # where each symbol's head sits in its box (about level with the text beside it)

    def __init__(
        self,
        values: list[str] | None = None,
        *,
        scale: float = 1.0,
        centre_stemless: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the picture.

        Parameters
        ----------
        values : list of str or None, default None
            The note values to show.
        scale : float, default 1.0
            How much to enlarge it. Keyword-only.
        centre_stemless : bool, default False
            Put the breve and whole note at the picture's vertical centre, so beside a line of text they line up with the middle
            of the text; the others keep their heads low so their stems fit above. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> ValuePictures(["half"], centre_stemless=True).centre_stemless
        True
        """
        super().__init__(scale, parent=parent)
        self.centre_stemless = centre_stemless
        self.values: list[str] = []
        self.set_values(values or [])

    # noinspection DuplicatedCode
    def set_values(self, values: list[str]) -> None:
        """
        Show different note values and size the picture for them.

        Parameters
        ----------
        values : list of str
            The note values to show.

        Examples
        --------
        >>> pictures = ValuePictures()
        >>> pictures.set_values(["breve", "whole"])
        >>> pictures.values
        ['breve', 'whole']
        """
        self.values = list(values)
        count = max(len(self.values), 1)
        self._fit(count * self.W + (count - 1) * self.SPACING, height=self.H)
        self.setToolTip(", ".join(VALUE_NAMES[v] for v in self.values))
        self.update()

    @classmethod
    def icon(
        cls,
        value: str,
        *,
        scale: float = 1.7,
    ) -> QIcon:
        """
        Return one note value as an icon.

        Parameters
        ----------
        value : str
            A key of `VALUE_NAMES`.
        scale : float, default 1.7
            How much to enlarge it. Keyword-only.

        Returns
        -------
        QIcon
            The icon.

        Examples
        --------
        >>> ValuePictures.icon("quarter").isNull()
        False
        """
        return cls([value], scale=scale).to_icon()

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw each note value.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> ValuePictures(["whole", "half", "quarter"]).grab().isNull()
        False
        """
        p = self._painter()
        text, _line = self._colours()
        for i, value in enumerate(self.values):
            x = i * (self.W + self.SPACING)
            wide = value in ("breve", "whole")  # the heads without stems are wider, so centre them in the box
            y = self.H / 2 if wide and self.centre_stemless else self.HEAD_Y
            # drawn by the same routine as the staff, so the symbol matches the one in the exercise
            # noinspection PyProtectedMember
            StaffWidget._note(
                p,
                x=x + (self.W / 2 if wide else self.HEAD_X),
                y=y,
                gap=self.GAP,
                color=text,
                value=value,
                stem_down=False,
                font=current_style().font,
            )


class KeySignaturePicture(_Picture):
    """
    A key signature as a plain row of its sharps or flats, with no staff or clef.

    Each sign sits at the height it has after a treble clef, and C major, which has none, shows a natural sign.

    Attributes
    ----------
    H, GAP, STEP : float
        The picture's height, the distance between staff lines and the space between signs.
    ORDER : dict of int to str
        Where each sign is written, in order, for sharps (1) and flats (-1).
    key : int
        The key signature: sharps if positive, flats if negative.

    Examples
    --------
    >>> KeySignaturePicture(2).toolTip()
    'D major: 2 sharps'
    """

    H, GAP, STEP = 40, 6.0, 8.0
    ORDER = {1: "F5 C5 G5 D5 A4 E5 B4", -1: "B4 E5 A4 D5 G4 C5 F4"}  # where each sign is written, in order
    CENTRE = {1: 6, -1: 4}  # the height (half-gaps above the bottom line) drawn in the middle of the picture

    def __init__(
        self,
        key: int = 0,
        *,
        scale: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the picture.

        Parameters
        ----------
        key : int, default 0
            The key signature: that many sharps if positive, flats if negative.
        scale : float, default 1.0
            How much to enlarge it. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> KeySignaturePicture(0).toolTip()
        'C major: no sharps or flats'
        >>> KeySignaturePicture(-1).toolTip()
        'F major: 1 flat'
        """
        super().__init__(scale, parent=parent)
        self.key = key
        self._fit(4 + max(abs(key), 1) * self.STEP, height=self.H)
        names = "no sharps or flats" if key == 0 else f"{abs(key)} {'sharp' if key > 0 else 'flat'}{'s' if abs(key) > 1 else ''}"
        self.setToolTip(f"{MAJOR_KEYS[key]} major: {names}")

    @classmethod
    def icon(
        cls,
        key: int,
        *,
        scale: float = 1.2,
    ) -> QIcon:
        """
        Return a key signature as an icon.

        Parameters
        ----------
        key : int
            Sharps if positive, flats if negative.
        scale : float, default 1.2
            How much to enlarge it. Keyword-only.

        Returns
        -------
        QIcon
            The icon.

        Examples
        --------
        >>> KeySignaturePicture.icon(3).isNull()
        False
        """
        return cls(key, scale=scale).to_icon()

    def _sign(
        self,
        p: QPainter,
        *,
        sign: int,
        x: float,
        y: float,
        colour: QColor,
    ) -> None:
        """
        Draw one sharp, flat or natural sign.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        sign : int
            1 for a sharp, -1 for a flat, 0 for a natural. Keyword-only.
        x : float
            The sign's left edge, in picture units. Keyword-only.
        y : float
            The sign's reference line. Keyword-only.
        colour : QColor
            The colour. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(40, 40, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> picture = KeySignaturePicture(1)
        >>> picture._sign(painter, sign=1, x=5, y=20, colour=QColor("black"))
        >>> painter.end()
        True
        """
        font = current_style().font
        if font:
            engraving.draw_accidental(
                p,
                font=font,
                sign=sign,
                x=x,
                y=y + 0.2 * self.GAP,
                gap=self.GAP,
                colour=colour,
                fit=self.STEP - 0.8,
            )
            return
        p.setPen(QPen(colour, 1.0))
        f = QFont("DejaVu Sans")
        f.setPixelSize(int(self.GAP * 2.6))
        p.setFont(f)
        p.drawText(QPointF(x, y + self.GAP * 0.9), {1: "♯", -1: "♭", 0: "♮"}[sign])

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the row of sharps or flats, or a natural sign for C major.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> KeySignaturePicture(-3).grab().isNull()
        False
        """
        p = self._painter()
        text, _line = self._colours()
        mid = self.H / 2
        if not self.key:
            self._sign(
                p,
                sign=0,
                x=2,
                y=mid,
                colour=text,
            )
            return
        kind = 1 if self.key > 0 else -1
        for i, name in enumerate(self.ORDER[kind].split()[: abs(self.key)]):
            steps = Note.parse(name).diatonic - BOTTOM_LINE["treble"]
            self._sign(
                p,
                sign=kind,
                x=2 + i * self.STEP,
                y=mid - (steps - self.CENTRE[kind]) * self.GAP / 2,
                colour=text,
            )


class RangePictures(_Picture):
    """
    For each clef, a staff with its lowest and highest note, so the range can be read off at a glance.

    Attributes
    ----------
    H, W, SPACING : float
        The picture's height, the width of one staff and the space between staves.
    MAX_SCALE : float
        The most the picture is enlarged to fit `max_width`.
    max_width : float or None
        The width to enlarge the picture to, if any.
    items : list of tuple of (str, int, int)
        Each clef with its lowest and highest note, as staff steps (`Note.diatonic`).

    Examples
    --------
    >>> pictures = RangePictures([("treble", 22, 52)])
    >>> pictures.toolTip()
    'Treble: D3 to F7'
    """

    H, W, SPACING = 38, 46, 6
    MAX_SCALE = 1.9

    def __init__(
        self,
        items: list[tuple[str, int, int]] | None = None,
        *,
        scale: float = 1.0,
        max_width: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the picture.

        Parameters
        ----------
        items : list of tuple of (str, int, int) or None, default None
            Each clef with its lowest and highest note.
        scale : float, default 1.0
            How much to enlarge it. Keyword-only.
        max_width : float or None, default None
            Enlarge the picture to use this width (up to `MAX_SCALE`) however many clefs there are. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> RangePictures([("treble", 22, 52)], max_width=238).scale
        1.9
        """
        super().__init__(scale, parent=parent)
        self.max_width = max_width
        self.items: list[tuple[str, int, int]] = []
        self.set_items(items or [])

    def set_items(self, items: list[tuple[str, int, int]]) -> None:
        """
        Show the ranges of some clefs and size the picture for them.

        Parameters
        ----------
        items : list of tuple of (str, int, int)
            Each clef with its lowest and highest note, as staff steps (`Note.diatonic`).

        Examples
        --------
        >>> pictures = RangePictures()
        >>> pictures.set_items([("bass", 10, 40), ("alto", 21, 35)])
        >>> pictures.toolTip().splitlines()
        ['Bass: F1 to A5', 'Alto: C3 to C5']
        """
        self.items = list(items)
        count = max(len(self.items), 1)
        natural = count * self.W + (count - 1) * self.SPACING
        if self.max_width:
            self.scale = min(self.MAX_SCALE, self.max_width / natural)
        self._fit(natural, height=self.H)
        tip = [
            f"{CLEF_NAMES[c]}: {Note.from_diatonic(lo).name}{Note.from_diatonic(lo).octave} to "
            f"{Note.from_diatonic(hi).name}{Note.from_diatonic(hi).octave}"
            for c, lo, hi in self.items
        ]
        self.setToolTip("\n".join(tip))
        self.update()

    def _note_head(
        self,
        p: QPainter,
        *,
        x: float,
        y: float,
        bottom: float,
        gap: float,
        colour: QColor,
        steps: int,
    ) -> None:
        """
        Draw a whole note, with ledger lines if it lies outside the staff.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The head's centre, in picture units. Keyword-only.
        y : float
            The head's height. Keyword-only.
        bottom : float
            The height of the staff's bottom line. Keyword-only.
        gap : float
            The distance between staff lines. Keyword-only.
        colour : QColor
            The colour. Keyword-only.
        steps : int
            How many half-gaps the note is above the bottom line; negative below it. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(40, 40, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> pictures = RangePictures()
        >>> pictures._dev = 1.0
        >>> pictures._note_head(painter, x=20, y=34, bottom=30, gap=4, colour=QColor("black"), steps=-4)
        >>> painter.end()
        True
        """
        if steps < 0:
            ledgers = range(-2, steps - 1, -2)
        elif steps > 8:
            ledgers = range(10, steps + 1, 2)
        else:
            ledgers = ()
        for s_ in ledgers:
            self._hline(
                p,
                x0=x - 4.2,
                x1=x + 4.2,
                y=bottom - s_ * gap / 2,
                colour=colour,
                width=0.65,
            )
        # a whole note, a little larger than the staff gap so it reads
        # noinspection PyProtectedMember
        StaffWidget._note(
            p,
            x=x,
            y=y,
            gap=gap * 1.45,
            color=colour,
            value="whole",
            stem_down=False,
            font=current_style().font,
        )

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw a staff for each clef with its lowest and highest note.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> RangePictures([("treble", 22, 52), ("bass", 10, 40)]).grab().isNull()
        False
        """
        p = self._painter()
        text, line = self._colours()
        for i, (clef, lo, hi) in enumerate(self.items):
            x = i * (self.W + self.SPACING)
            p.save()
            p.setClipRect(
                QRectF(
                    x,
                    0,
                    self.W,
                    self.H,
                ),
            )
            if clef == "grand":
                gap = 2.0
                bottoms = {"treble": 15.0, "bass": 29.0}
                for name, b in bottoms.items():
                    self._staff(
                        p,
                        x0=x + 6,
                        x1=x + self.W - 1,
                        bottom=b,
                        gap=gap,
                        colour=line,
                    )
                    # noinspection PyProtectedMember
                    StaffWidget._draw_clef(
                        p,
                        clef=name,
                        x=x + 8,
                        bottom=b,
                        gap=gap,
                        color=text,
                        font=current_style().font,
                    )
                self._vline(
                    p,
                    x=x + 6,
                    y0=7,
                    y1=29,
                    colour=line,
                    width=0.65,
                )
                # noinspection PyProtectedMember
                StaffWidget._brace(
                    p,
                    x=x + 5,
                    y0=7,
                    y1=29,
                    color=text,
                    wd=3.0,
                    font=current_style().font,
                )
            else:
                gap = 2.6
                bottoms = {clef: 25.0}
                self._staff(
                    p,
                    x0=x + 1,
                    x1=x + self.W - 1,
                    bottom=25.0,
                    gap=gap,
                    colour=line,
                )
                # noinspection PyProtectedMember
                StaffWidget._draw_clef(
                    p,
                    clef=clef,
                    x=x + 3,
                    bottom=25.0,
                    gap=gap,
                    color=text,
                    font=current_style().font,
                )
            for note_x, d in ((x + 30, lo), (x + 40, hi)):
                staff = "treble" if clef == "grand" and d >= MIDDLE_C else "bass" if clef == "grand" else clef
                steps = d - BOTTOM_LINE[staff]
                y = bottoms[staff] - steps * gap / 2
                self._note_head(
                    p,
                    x=note_x,
                    y=y,
                    bottom=bottoms[staff],
                    gap=gap,
                    colour=text,
                    steps=steps,
                )
            p.restore()


class NamePicture(_Picture):
    """
    How notes are named: C, D and E on a staff, labelled with letters or with solfège syllables.

    Attributes
    ----------
    H, W : float
        The picture's height and width.
    LETTERS, SYLLABLES : tuple of str
        The two sets of labels.
    naming : str
        "letters" or "solfege".

    Examples
    --------
    >>> NamePicture("solfege").toolTip()
    'Solfège (Do Re Mi)'
    """

    H, W = 38, 62
    LETTERS, SYLLABLES = ("C", "D", "E"), SOLFEGE[:3]

    def __init__(
        self,
        naming: str = "letters",
        *,
        scale: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the picture.

        Parameters
        ----------
        naming : str, default "letters"
            "letters" or "solfege".
        scale : float, default 1.0
            How much to enlarge it. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns it. Keyword-only.

        Examples
        --------
        >>> NamePicture().naming
        'letters'
        """
        super().__init__(scale, parent=parent)
        self.naming = naming
        self._fit(self.W, height=self.H)
        self.set_naming(naming)

    def set_naming(self, naming: str) -> None:
        """
        Choose which labels are drawn.

        Parameters
        ----------
        naming : str
            "letters" for C D E, or "solfege" for Do Re Mi.

        Examples
        --------
        >>> picture = NamePicture()
        >>> picture.set_naming("solfege")
        >>> picture.toolTip()
        'Solfège (Do Re Mi)'
        """
        self.naming = naming
        self.setToolTip("Solfège (Do Re Mi)" if naming == "solfege" else "Letters (C D E)")
        self.update()

    @classmethod
    def icon(
        cls,
        naming: str,
        *,
        scale: float = 1.6,
    ) -> QIcon:
        """
        Return the picture as an icon.

        Parameters
        ----------
        naming : str
            "letters" or "solfege".
        scale : float, default 1.6
            How much to enlarge it. Keyword-only.

        Returns
        -------
        QIcon
            The icon.

        Examples
        --------
        >>> NamePicture.icon("letters").isNull()
        False
        """
        return cls(naming, scale=scale).to_icon()

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the staff, the clef, the three notes and their labels.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> NamePicture("letters").grab().isNull()
        False
        """
        p = self._painter()
        text, line = self._colours()
        gap, bottom = 2.4, 17.0
        self._staff(
            p,
            x0=1,
            x1=self.W - 1,
            bottom=bottom,
            gap=gap,
            colour=line,
        )
        # noinspection PyProtectedMember
        StaffWidget._draw_clef(
            p,
            clef="treble",
            x=2.5,
            bottom=bottom,
            gap=gap,
            color=text,
            font=current_style().font,
        )
        names = self.SYLLABLES if self.naming == "solfege" else self.LETTERS
        font = QFont()
        font.setPixelSize(8)
        font.setBold(True)
        p.setFont(font)
        for i, (name, steps) in enumerate(zip(names, (-2, -1, 0))):  # C4 sits on a ledger line below the staff
            x = 24 + i * 12.5
            y = bottom - steps * gap / 2
            if steps == -2:
                self._hline(
                    p,
                    x0=x - 3.4,
                    x1=x + 3.4,
                    y=y,
                    colour=text,
                    width=0.65,
                )
            # noinspection PyProtectedMember
            StaffWidget._note(
                p,
                x=x,
                y=y,
                gap=gap * 1.45,
                color=text,
                value="whole",
                stem_down=False,
                font=current_style().font,
            )
            p.setPen(QPen(text, 1.0))
            p.drawText(
                QRectF(
                    x - 6.5,
                    29.5,
                    13,
                    9,
                ),
                Qt.AlignmentFlag.AlignCenter,
                name,
            )
