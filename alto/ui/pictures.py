"""Small pictures of musical things (clefs, note values, key signatures, note ranges ...) for the settings panes.

Each picture is drawn in fixed units and then scaled, so the same picture serves as a summary in a menu row and,
larger, as the label of a choice. Colours come from the palette, so they work in light and dark themes.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPen, QPixmap, QRegion
from PySide6.QtWidgets import QWidget

from ..settings import SOLFEGE
from ..theory.pitch import MAJOR_KEYS, Note
from . import engraving
from .colors import blend
from .notation import current as current_style
from .staff import BOTTOM_LINE, MIDDLE_C, StaffWidget

CLEF_NAMES = {"treble": "Treble", "bass": "Bass", "alto": "Alto", "tenor": "Tenor", "soprano": "Soprano",
              "mezzo": "Mezzo-soprano", "baritone": "Baritone", "grand": "Grand staff",
              "baritone_f": "Baritone (F clef)", "baritone_c": "Baritone (C clef)"}  # the two ways of writing the baritone clef
VALUE_NAMES = {"breve": "Breve", "whole": "Whole", "half": "Half", "quarter": "Quarter", "eighth": "Eighth",
               "sixteenth": "16th", "thirty_second": "32nd"}


class _Picture(QWidget):
    """Base class: a widget drawn in its own units, enlarged by `scale`, that ignores the mouse."""

    def __init__(self, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.scale = scale
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row or checkbox underneath is the click target

    def _fit(self, width: float, height: float) -> None:
        self.setFixedSize(round(width * self.scale), round(height * self.scale))

    def _colours(self) -> tuple[QColor, QColor]:
        """(ink, softer ink for staff lines), both readable against the background in light and dark themes."""
        pal = self.palette()
        text, base = pal.color(QPalette.ColorRole.Text), pal.color(QPalette.ColorRole.Base)
        line = blend(base, text, 0.62)
        return text, line

    def _painter(self) -> QPainter:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(self.scale, self.scale)
        self._dev = abs(p.deviceTransform().m11()) or 1.0  # device pixels per picture unit
        return p

    def _hline(self, p: QPainter, x0: float, x1: float, y: float, colour: QColor, width: float = 1.0) -> None:
        """A horizontal line a whole number of device pixels thick and placed on the pixel grid, so staff lines come
        out crisp and equally strong at any scale."""
        d = self._dev
        n = max(round(width * d), 1)
        y = (int(y * d) + 0.5) / d if n % 2 else round(y * d) / d
        p.setPen(QPen(colour, n / d, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(x0, y), QPointF(x1, y))

    def _vline(self, p: QPainter, x: float, y0: float, y1: float, colour: QColor, width: float = 1.0) -> None:
        d = self._dev
        n = max(round(width * d), 1)
        x = (int(x * d) + 0.5) / d if n % 2 else round(x * d) / d
        p.setPen(QPen(colour, n / d, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawLine(QPointF(x, y0), QPointF(x, y1))

    def to_icon(self) -> QIcon:
        """This picture as an icon (e.g. for a checkbox), drawn crisply at twice the screen resolution."""
        ratio = 2.0
        pixmap = QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        self.render(pixmap, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)  # just the picture, not the widget background
        return QIcon(pixmap)

    def _staff(self, p: QPainter, x0: float, x1: float, bottom: float, gap: float, colour: QColor) -> None:
        for n in range(5):
            self._hline(p, x0, x1, bottom - n * gap, colour, 0.65)


class ClefPictures(_Picture):
    """The selected clefs, each on its own five-line staff (so alto and tenor, which share a symbol, look different),
    and a two-stave picture with a brace for the grand staff."""

    H, W, GAP, SPACING = 34, 30, 3.4, 8
    NAMES = CLEF_NAMES

    def __init__(self, clefs: list[str] | None = None, scale: float = 1.0, parent=None):
        super().__init__(scale, parent)
        self.clefs: list[str] = []
        self.set_clefs(clefs or [])

    def set_clefs(self, clefs: list[str]) -> None:
        self.clefs = list(clefs)
        count = max(len(self.clefs), 1)
        self._fit(count * self.W + (count - 1) * self.SPACING, self.H)
        self.setToolTip(", ".join(CLEF_NAMES[c] for c in self.clefs))
        self.update()

    @classmethod
    def icon(cls, clef: str, scale: float = 1.8) -> QIcon:
        return cls([clef], scale).to_icon()

    def paintEvent(self, _):
        p = self._painter()
        text, line = self._colours()
        for i, clef in enumerate(self.clefs):
            x = i * (self.W + self.SPACING)
            if clef == "grand":
                self._grand(p, x, text, line)
                continue
            self._staff(p, x + 1, x + self.W - 1, 24.0, self.GAP, line)
            StaffWidget._draw_clef(p, clef, x + 3, 24.0, self.GAP, text, current_style().font)

    def _grand(self, p: QPainter, x: float, text: QColor, line: QColor) -> None:
        gap, tops = 2.1, (6.0, 22.6)  # y of the top line of each stave
        for top, clef in zip(tops, ("treble", "bass")):
            bottom = top + 4 * gap
            self._staff(p, x + 5, x + self.W - 1, bottom, gap, line)
            StaffWidget._draw_clef(p, clef, x + 8, bottom, gap, text, current_style().font)
        self._vline(p, x + 5, tops[0], tops[1] + 4 * gap, line, 0.65)
        StaffWidget._brace(p, x + 4, tops[0], tops[1] + 4 * gap, text, wd=3.5, font=current_style().font)


class ValuePictures(_Picture):
    """Note values as engraved symbols (no staff), each with its head on the same baseline so they line up."""

    H, W, GAP, SPACING = 40, 18, 4.5, 4
    HEAD_X, HEAD_Y = 6.5, 25.0  # where each symbol's head sits in its box (about level with the text beside it)

    def __init__(self, values: list[str] | None = None, scale: float = 1.0, centre_stemless: bool = False, parent=None):
        """With `centre_stemless` the breve and whole note sit at the picture's vertical centre, so beside a line of
        text they line up with the middle of the text; the others keep their heads low so their stems fit above."""
        super().__init__(scale, parent)
        self.centre_stemless = centre_stemless
        self.values: list[str] = []
        self.set_values(values or [])

    def set_values(self, values: list[str]) -> None:
        self.values = list(values)
        count = max(len(self.values), 1)
        self._fit(count * self.W + (count - 1) * self.SPACING, self.H)
        self.setToolTip(", ".join(VALUE_NAMES[v] for v in self.values))
        self.update()

    @classmethod
    def icon(cls, value: str, scale: float = 1.7) -> QIcon:
        return cls([value], scale).to_icon()

    def paintEvent(self, _):
        p = self._painter()
        text, _line = self._colours()
        for i, value in enumerate(self.values):
            x = i * (self.W + self.SPACING)
            wide = value in ("breve", "whole")  # the heads without stems are wider, so centre them in the box
            y = self.H / 2 if wide and self.centre_stemless else self.HEAD_Y
            # drawn by the same routine as the staff, so the symbol matches the one in the exercise
            StaffWidget._note(p, x + (self.W / 2 if wide else self.HEAD_X), y, self.GAP, text, value, False,
                              current_style().font)


class KeySignaturePicture(_Picture):
    """A key signature as a plain row of its sharps or flats, with no staff or clef. Each sign sits at the height it
    has after a treble clef, and C major, which has none, shows a natural sign."""

    H, GAP, STEP = 40, 6.0, 8.0
    ORDER = {1: "F5 C5 G5 D5 A4 E5 B4", -1: "B4 E5 A4 D5 G4 C5 F4"}  # where each sign is written, in order
    CENTRE = {1: 6, -1: 4}  # the height (half-gaps above the bottom line) drawn in the middle of the picture

    def __init__(self, key: int = 0, scale: float = 1.0, parent=None):
        super().__init__(scale, parent)
        self.key = key
        self._fit(4 + max(abs(key), 1) * self.STEP, self.H)
        names = "no sharps or flats" if key == 0 else f"{abs(key)} {'sharp' if key > 0 else 'flat'}{'s' if abs(key) > 1 else ''}"
        self.setToolTip(f"{MAJOR_KEYS[key]} major: {names}")

    @classmethod
    def icon(cls, key: int, scale: float = 1.2) -> QIcon:
        return cls(key, scale).to_icon()

    def _sign(self, p: QPainter, sign: int, x: float, y: float, colour: QColor) -> None:
        """One sharp (1), flat (-1) or natural (0) with its left edge at x and its reference line at y."""
        font = current_style().font
        if font:
            engraving.draw_accidental(p, font, sign, x, y + 0.2 * self.GAP, self.GAP, colour, fit=self.STEP - 0.8)
            return
        p.setPen(QPen(colour, 1.0))
        f = QFont("DejaVu Sans")
        f.setPixelSize(int(self.GAP * 2.6))
        p.setFont(f)
        p.drawText(QPointF(x, y + self.GAP * 0.9), {1: "♯", -1: "♭", 0: "♮"}[sign])

    def paintEvent(self, _):
        p = self._painter()
        text, _line = self._colours()
        mid = self.H / 2
        if not self.key:
            self._sign(p, 0, 2, mid, text)
            return
        kind = 1 if self.key > 0 else -1
        for i, name in enumerate(self.ORDER[kind].split()[: abs(self.key)]):
            steps = Note.parse(name).diatonic - BOTTOM_LINE["treble"]
            self._sign(p, kind, 2 + i * self.STEP, mid - (steps - self.CENTRE[kind]) * self.GAP / 2, text)


class RangePictures(_Picture):
    """For each clef, a staff with its lowest and highest note, so the range can be read off at a glance."""

    H, W, SPACING = 38, 46, 6
    MAX_SCALE = 1.9

    def __init__(self, items: list[tuple[str, int, int]] | None = None, scale: float = 1.0, max_width: float | None = None,
                 parent=None):
        """With `max_width` the picture is enlarged to use that width (up to MAX_SCALE) however many clefs there are."""
        super().__init__(scale, parent)
        self.max_width = max_width
        self.items: list[tuple[str, int, int]] = []
        self.set_items(items or [])

    def set_items(self, items: list[tuple[str, int, int]]) -> None:
        """`items` are (clef, lowest, highest) with notes as diatonic numbers."""
        self.items = list(items)
        count = max(len(self.items), 1)
        natural = count * self.W + (count - 1) * self.SPACING
        if self.max_width:
            self.scale = min(self.MAX_SCALE, self.max_width / natural)
        self._fit(natural, self.H)
        tip = [f"{CLEF_NAMES[c]}: {Note.from_diatonic(lo).name}{Note.from_diatonic(lo).octave} to "
               f"{Note.from_diatonic(hi).name}{Note.from_diatonic(hi).octave}" for c, lo, hi in self.items]
        self.setToolTip("\n".join(tip))
        self.update()

    def _note_head(self, p: QPainter, x: float, y: float, bottom: float, gap: float, colour: QColor, steps: int) -> None:
        """A whole note at (x, y) with ledger lines if it lies outside the staff (`steps` half-gaps above the bottom line)."""
        if steps < 0:
            ledgers = range(-2, steps - 1, -2)
        elif steps > 8:
            ledgers = range(10, steps + 1, 2)
        else:
            ledgers = ()
        for s_ in ledgers:
            self._hline(p, x - 4.2, x + 4.2, bottom - s_ * gap / 2, colour, 0.65)
        # a whole note, a little larger than the staff gap so it reads
        StaffWidget._note(p, x, y, gap * 1.45, colour, "whole", False, current_style().font)

    def paintEvent(self, _):
        p = self._painter()
        text, line = self._colours()
        for i, (clef, lo, hi) in enumerate(self.items):
            x = i * (self.W + self.SPACING)
            p.save()
            p.setClipRect(QRectF(x, 0, self.W, self.H))
            if clef == "grand":
                gap = 2.0
                bottoms = {"treble": 15.0, "bass": 29.0}
                for name, b in bottoms.items():
                    self._staff(p, x + 6, x + self.W - 1, b, gap, line)
                    StaffWidget._draw_clef(p, name, x + 8, b, gap, text, current_style().font)
                self._vline(p, x + 6, 7, 29, line, 0.65)
                StaffWidget._brace(p, x + 5, 7, 29, text, wd=3.0, font=current_style().font)
            else:
                gap = 2.6
                bottoms = {clef: 25.0}
                self._staff(p, x + 1, x + self.W - 1, 25.0, gap, line)
                StaffWidget._draw_clef(p, clef, x + 3, 25.0, gap, text, current_style().font)
            for note_x, d in ((x + 30, lo), (x + 40, hi)):
                staff = "treble" if clef == "grand" and d >= MIDDLE_C else "bass" if clef == "grand" else clef
                steps = d - BOTTOM_LINE[staff]
                y = bottoms[staff] - steps * gap / 2
                self._note_head(p, note_x, y, bottoms[staff], gap, text, steps)
            p.restore()


class NamePicture(_Picture):
    """How notes are named: C, D and E on a staff, labelled with letters or with solfège syllables."""

    H, W = 38, 62
    LETTERS, SYLLABLES = ("C", "D", "E"), SOLFEGE[:3]

    def __init__(self, naming: str = "letters", scale: float = 1.0, parent=None):
        super().__init__(scale, parent)
        self._fit(self.W, self.H)
        self.set_naming(naming)

    def set_naming(self, naming: str) -> None:
        self.naming = naming
        self.setToolTip("Solfège (Do Re Mi)" if naming == "solfege" else "Letters (C D E)")
        self.update()

    @classmethod
    def icon(cls, naming: str, scale: float = 1.6) -> QIcon:
        return cls(naming, scale).to_icon()

    def paintEvent(self, _):
        p = self._painter()
        text, line = self._colours()
        gap, bottom = 2.4, 17.0
        self._staff(p, 1, self.W - 1, bottom, gap, line)
        StaffWidget._draw_clef(p, "treble", 2.5, bottom, gap, text, current_style().font)
        names = self.SYLLABLES if self.naming == "solfege" else self.LETTERS
        font = QFont()
        font.setPixelSize(8)
        font.setBold(True)
        p.setFont(font)
        for i, (name, steps) in enumerate(zip(names, (-2, -1, 0))):  # C4 sits on a ledger line below the staff
            x = 24 + i * 12.5
            y = bottom - steps * gap / 2
            if steps == -2:
                self._hline(p, x - 3.4, x + 3.4, y, text, 0.65)
            StaffWidget._note(p, x, y, gap * 1.45, text, "whole", False, current_style().font)
            p.setPen(QPen(text, 1.0))
            p.drawText(QRectF(x - 6.5, 29.5, 13, 9), Qt.AlignmentFlag.AlignCenter, name)
