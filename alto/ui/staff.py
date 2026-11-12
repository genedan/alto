from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..theory.pitch import ACCIDENTAL_SYMBOLS, Note, key_accidental
from . import engraving
from .notation import NotationStyle
from .notation import current as current_style
from .notes import draw_note

# Diatonic index of the bottom staff line.
BOTTOM_LINE = {
    "treble": Note(4, 2).diatonic,  # E4
    "bass": Note(2, 4).diatonic,    # G2
    "alto": Note(3, 3).diatonic,    # F3
    "tenor": Note(3, 1).diatonic,   # D3
}
CLEF_GLYPH = {"treble": "𝄞", "bass": "𝄢", "alto": "𝄡", "tenor": "𝄡"}
# (glyph top, glyph bottom) measured upward from the bottom staff line, in staff gaps
CLEF_EXTENT = {"treble": (6.6, -2.2), "bass": (4.0, 0.7), "alto": (4.0, 0.0), "tenor": (5.0, 1.0)}
MIDDLE_C = Note(4, 0).diatonic

# Where each key-signature accidental sits, in order of appearance (diatonic positions as note names).
_KEY_POSITIONS = {
    ("treble", 1): "F5 C5 G5 D5 A4 E5 B4", ("treble", -1): "B4 E5 A4 D5 G4 C5 F4",
    ("bass", 1): "F3 C3 G3 D3 A2 E3 B2", ("bass", -1): "B2 E3 A2 D3 G2 C3 F2",
    ("alto", 1): "F4 C4 G4 D4 A3 E4 B3", ("alto", -1): "B3 E4 A3 D4 G3 C4 F3",
    ("tenor", 1): "F3 C4 G3 D4 A3 E4 B3", ("tenor", -1): "B3 E4 A3 D4 G3 C4 F3",
}
KEY_STEP = 13.0  # horizontal spacing between key-signature accidentals

# Grand staff layout, in staff gaps: margin above/below the pair and the distance between them.
GRAND_BETWEEN = 3.5
CORNER_RADIUS = 14


def draw_key_signature(p: QPainter, clef: str, key: int, x: float, bottom: float, gap: float, color: QColor,
                       step: float = KEY_STEP, size: float = 2.0, font: str | None = None) -> None:
    """Draw the sharps or flats of a key signature (`key` sharps if positive, flats if negative) starting at x.
    `font` is a SMuFL font to engrave them in; None uses the built-in sharp and flat characters."""
    if not key:
        return
    if font:
        positions = _KEY_POSITIONS[(clef, 1 if key > 0 else -1)].split()
        for i, name in enumerate(positions[: abs(key)]):
            y = bottom - (Note.parse(name).diatonic - BOTTOM_LINE[clef]) * gap / 2
            engraving.draw_accidental(p, font, 1 if key > 0 else -1, x + i * step, y, gap, color, fit=step - 1)
        return
    sign = "♯" if key > 0 else "♭"
    positions = _KEY_POSITIONS[(clef, 1 if key > 0 else -1)].split()
    p.save()
    p.setPen(QPen(color, 1.4))
    font = QFont("DejaVu Sans")
    font.setPixelSize(max(int(gap * size * 1.33), 6))
    p.setFont(font)
    for i, name in enumerate(positions[: abs(key)]):
        y = bottom - (Note.parse(name).diatonic - BOTTOM_LINE[clef]) * gap / 2
        p.drawText(QPointF(x + i * step, y + gap * 0.5), sign)
    p.restore()


class StaffWidget(QWidget):
    def __init__(self, parent=None, gap: float = 14.0, side: float = 20.0, note_offset: float = 100.0,
                 margin: float = 8.0, compact: bool = False):
        """`gap` is the distance between staff lines in pixels; `margin` is the space (in gaps) kept above
        and below the staff for ledger lines; `compact` sizes the widget to fit instead of the 220 px default."""
        super().__init__(parent)
        self.GAP, self.side, self.note_offset, self.margin, self.compact = gap, side, note_offset, margin, compact
        self.clef = "treble"
        self.columns: list[list[Note]] = []
        self.note_color: QColor | None = None  # None draws notes in the style's ink
        self.style: NotationStyle | None = None  # None follows the style chosen in settings
        self.key = 0
        self.value = "whole"
        self._fit_height("treble")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def show_notes(self, columns: list[list[Note]], clef: str = "treble", key: int = 0, value: str = "whole") -> None:
        self.columns, self.clef, self.key, self.value = columns, clef, key, value
        self.note_color = None
        self._fit_height(clef)
        self.update()

    def _fit_height(self, clef: str) -> None:
        grand_height = 2 * self.margin + 8 + GRAND_BETWEEN  # in gaps
        if self.compact:
            self.setFixedHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP))
        else:
            self.setMinimumHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP) + 10)

    def set_note_color(self, color: QColor | None) -> None:
        self.note_color = QColor(color) if color is not None else None
        self.update()

    def staff_bottoms(self) -> dict[str, float]:
        """Where each staff is drawn: clef name -> y of its bottom line (a grand staff has a treble and a bass)."""
        gap, h = self.GAP, self.height()
        if self.clef == "grand":
            top = (h - (2 * self.margin + 8 + GRAND_BETWEEN) * gap) / 2 + self.margin * gap
            return {"treble": top + 4 * gap, "bass": top + (8 + GRAND_BETWEEN) * gap}
        return {self.clef: h / 2 + 2 * gap}

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        look = self.style or current_style()
        font = look.font
        fg = QColor("black")
        line = engraving.staff_line_width(font, self.GAP) if font else look.line
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        p.drawRoundedRect(self.rect(), CORNER_RADIUS, CORNER_RADIUS)  # the rounded "paper" behind the music
        p.setPen(QPen(fg, line))
        gap = self.GAP
        w = self.width()
        grand = self.clef == "grand"
        left, right = self.side + (18.0 if grand else 0.0), w - self.side

        staves = self.staff_bottoms()

        def staff_for(note: Note) -> str:
            if not grand:
                return self.clef
            return "treble" if note.diatonic >= MIDDLE_C else "bass"

        for clef, bottom in staves.items():
            for i in range(5):
                p.drawLine(QPointF(left, bottom - i * gap), QPointF(right, bottom - i * gap))
            self._draw_clef(p, clef, left + 8, bottom, gap, fg, font)
            self._draw_key_signature(p, clef, left + 56, bottom, gap, fg, font)
        if grand:
            ys = list(staves.values())
            p.drawLine(QPointF(left, ys[0] - 4 * gap), QPointF(left, ys[1]))
            self._brace(p, left - 3, ys[0] - 4 * gap, ys[1], fg, font=font)

        n = max(len(self.columns), 1)
        x0 = left + self.note_offset + KEY_STEP * abs(self.key)
        step = (right - x0) / n
        nfg = self.note_color or fg
        p.setBrush(nfg)
        for ci, col in enumerate(self.columns):
            x = x0 + step * (ci + 0.5)
            acc_slot = 0
            for note in sorted(col):
                clef = staff_for(note)
                bottom = staves[clef]
                y = bottom - (note.diatonic - BOTTOM_LINE[clef]) * gap / 2
                steps = round((bottom - y) / (gap / 2))
                p.setPen(QPen(fg, engraving.ledger_width(font, gap) if font else line))
                if steps < 0:
                    for s in range(-2, steps - 1, -2):
                        self._ledger(p, x, bottom - s * gap / 2, gap)
                elif steps > 8:
                    for s in range(10, steps + 1, 2):
                        self._ledger(p, x, bottom - s * gap / 2, gap)
                p.setPen(Qt.PenStyle.NoPen)
                value = self.value if len(col) == 1 else "whole"  # stems are only drawn for single notes
                self._note(p, x, y, gap, nfg, value, stem_down=steps >= 4, font=font)
                p.setPen(QPen(nfg, 1.4))
                # A sign is written only where the note differs from what the key signature already says.
                if note.accidental != key_accidental(note.letter, self.key):
                    ax = x - gap * (2.3 + 1.2 * (acc_slot % 3))
                    if font:
                        engraving.draw_accidental(p, font, note.accidental, ax, y, gap, fg)
                    else:
                        sign = ACCIDENTAL_SYMBOLS[note.accidental] or "♮"
                        p.setFont(QFont("DejaVu Sans", int(gap * 2.0)))
                        p.drawText(QPointF(ax, y + gap * 0.5), sign)
                    acc_slot += 1

    def _draw_key_signature(self, p: QPainter, clef: str, x: float, bottom: float, gap: float, color: QColor,
                            font: str | None = None) -> None:
        draw_key_signature(p, clef, self.key, x, bottom, gap, color, font=font)

    @staticmethod
    def _note(p: QPainter, x: float, y: float, gap: float, color: QColor, value: str, stem_down: bool,
              font: str | None = None) -> None:
        """Draw a note of the given value; the head is centred on (x, y)."""
        if font and value != "breve":  # the breve is always the square form, whatever the music font
            engraving.draw_note(p, font, value, x, y, gap, color, stem_down)
        elif value == "whole":
            StaffWidget._whole_note(p, x, y, gap, color)
        else:
            draw_note(p, value, x, y, gap, color, stem_down)

    @staticmethod
    def _draw_clef(p: QPainter, clef: str, x: float, bottom: float, gap: float, color: QColor = QColor("black"),
                   font: str | None = None) -> None:
        """Draw the clef: from a SMuFL font if given, else as a Noto Music path scaled to its extent in gaps."""
        if font:
            engraving.draw_clef(p, font, clef, x, bottom, gap, color)
            return
        top, bot = CLEF_EXTENT[clef]
        path = QPainterPath()
        path.addText(0, 0, QFont("Noto Music", 100), CLEF_GLYPH[clef])
        r = path.boundingRect()
        scale = (top - bot) * gap / r.height()
        t = QTransform()
        t.translate(x, bottom - top * gap)
        t.scale(scale, scale)
        t.translate(-r.x(), -r.y())
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(t.map(path))
        p.restore()

    @staticmethod
    def _brace(p: QPainter, x: float, y0: float, y1: float, color: QColor, wd: float = 11.0, font: str | None = None) -> None:
        """A curly brace whose point faces left, spanning y0..y1 with its right edge at x: the music font's brace if
        it has one, else a drawn one."""
        if font and engraving.draw_brace(p, font, x, y0, y1, color, wd * 1.25):
            return
        mid = (y0 + y1) / 2
        path = QPainterPath()
        path.moveTo(x, y0)
        path.cubicTo(x - wd, y0 + (mid - y0) * 0.25, x, mid - (mid - y0) * 0.35, x - wd, mid)
        path.cubicTo(x, mid + (y1 - mid) * 0.35, x - wd, y1 - (y1 - mid) * 0.25, x, y1)
        path.cubicTo(x - wd * 0.4, y1 - (y1 - mid) * 0.25, x - wd * 1.4, mid + (y1 - mid) * 0.3, x - wd * 1.4, mid)
        path.cubicTo(x - wd * 1.4, mid - (mid - y0) * 0.3, x - wd * 0.4, y0 + (mid - y0) * 0.25, x, y0)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)
        p.restore()

    @staticmethod
    def _whole_note(p: QPainter, x: float, y: float, gap: float, color: QColor = QColor("black")) -> None:
        """Whole note: black oval with a tilted white hole."""
        outer = QPainterPath()
        outer.addEllipse(QPointF(0, 0), gap * 0.74, gap * 0.5)
        hole = QPainterPath()
        hole.addEllipse(QPointF(0, 0), gap * 0.38, gap * 0.42)
        t = QTransform()
        t.rotate(-35)
        shape = outer.subtracted(t.map(hole))  # transparent hole: staff line shows through
        p.save()
        p.translate(x, y)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(shape)
        p.restore()

    @staticmethod
    def _ledger(p: QPainter, x: float, y: float, gap: float) -> None:
        """Ledger line, a little wider than the note head (which is about 0.74 gap either side of centre)."""
        p.drawLine(QPointF(x - gap, y), QPointF(x + gap, y))
