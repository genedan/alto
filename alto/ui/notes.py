"""Engraved notes built from the Noto Music font's glyphs, the way notation software draws them.

The font only has stem-up notes. A stem-down note is made from the same glyph turned half a turn (which puts the
stem on the left of the head and keeps the head's tilt), with the flags cut from the stem-up glyph and mirrored so
they sweep up from the stem's end, as an engraver would write them.

All numbers are in glyph units at a font size of 100, where one staff space is STAFF_SPACE units.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QTransform

STAFF_SPACE = 33.5  # a note head is one staff space tall
GLYPHS = {  # the breve is not here: its square form is drawn by _square_breve (the font only has the oval one)
    "whole": "\U0001d15d",
    "half": "\U0001d15e",
    "quarter": "\U0001d15f",
    "eighth": "\U0001d160",
    "sixteenth": "\U0001d161",
    "thirty_second": "\U0001d162",
}
HEAD_CENTRE = {  # centre of the note head, from the glyph's origin
    "breve": (0.0, 0.0),
    "whole": (34.2, -17.85),
    "half": (26.5, -17.9),
    "quarter": (26.6, -18.1),
    "eighth": (26.6, -18.1),
    "sixteenth": (26.6, -18.1),
    "thirty_second": (26.6, -18.1),
}
FLAGS = {"eighth": 1, "sixteenth": 2, "thirty_second": 3}
STEM_LEFT, STEM_RIGHT = 43.09, 46.55  # the stem of the stem-up quarter note
FLAG_CLIP = 46.9  # flags are the part of a glyph to the right of this
STEM_TOP = {"half": -134.2, "quarter": -134.2, "eighth": -134.2, "sixteenth": -134.2, "thirty_second": -153.5}

_glyphs: dict[str, QPainterPath] = {}
_shapes: dict[tuple[str, bool], QPainterPath] = {}


def _square_breve() -> QPainterPath:
    """The square form of the breve (double whole note), centred on (0, 0): two slender upright bars joined by a
    heavy bar above and below a hollow slot, with the uprights standing a little proud at the ends, so the sides
    read like the serifs of a capital I. 1.65 staff spaces wide and 1.45 tall."""
    s = STAFF_SPACE

    def rect(x0: float, y0: float, x1: float, y1: float, r: float = 0.0) -> QPainterPath:
        path = QPainterPath()
        if r:
            path.addRoundedRect(QRectF(x0 * s, y0 * s, (x1 - x0) * s, (y1 - y0) * s), r * s, r * s)
        else:
            path.addRect(QRectF(x0 * s, y0 * s, (x1 - x0) * s, (y1 - y0) * s))
        return path

    outer, inner = 0.825, 0.655  # the uprights run from `inner` to `outer`, either side of the middle
    shape = rect(-outer, -0.62, outer, 0.62)  # the heavy bars above and below the slot
    shape = shape.united(rect(-outer, -0.725, -inner, 0.725, 0.03))  # the uprights, a little taller than the bars
    shape = shape.united(rect(inner, -0.725, outer, 0.725, 0.03))
    return shape.subtracted(rect(-inner, -0.16, inner, 0.16, 0.10))  # the slot between the uprights


def _glyph(value: str) -> QPainterPath:
    path = _glyphs.get(value)
    if path is None:
        if value == "breve":
            path = _glyphs[value] = _square_breve()
        else:
            path = _glyphs[value] = QPainterPath()
            path.addText(0, 0, QFont("Noto Music", 100), GLYPHS[value])
    return path


def _stem_down_shape(value: str) -> QPainterPath:
    hx, hy = HEAD_CENTRE[value]
    turn = QTransform()
    turn.translate(hx, hy)
    turn.rotate(180)
    turn.translate(-hx, -hy)
    shape = turn.map(_glyph("half" if value == "half" else "quarter"))  # head and stem, stem now on the left
    left, right = 2 * hx - STEM_RIGHT, 2 * hx - STEM_LEFT  # where that stem is
    if value in FLAGS:
        extra = STEM_TOP["quarter"] - STEM_TOP[value]  # the 32nd note's stem is longer than the quarter's
        if extra:
            stem = QPainterPath()
            stem.addRect(QRectF(left, 2 * hy - STEM_TOP["quarter"] - 1, right - left, -extra + 1))
            shape = shape.united(stem)
        beside = QPainterPath()
        beside.addRect(QRectF(FLAG_CLIP, -300, 200, 400))
        flags = _glyph(value).intersected(beside)
        move = QTransform()
        move.translate(right - 0.3 - FLAG_CLIP, 0)  # the flag's root meets the new stem
        move.translate(0, 2 * hy)
        move.scale(1, -1)  # mirrored top to bottom: it now sweeps up from the stem's end
        shape = shape.united(move.map(flags))
    return shape


def note_shape(value: str, stem_down: bool = False) -> QPainterPath:
    """The outline of a note of this value (see the module docstring); stems only exist from the half note on."""
    stem_down = stem_down and value not in ("breve", "whole")
    key = (value, stem_down)
    if key not in _shapes:
        _shapes[key] = _stem_down_shape(value) if stem_down else _glyph(value)
    return _shapes[key]


def draw_note(p: QPainter, value: str, x: float, y: float, gap: float, colour: QColor, stem_down: bool = False) -> None:
    """Draw a note with its head centred on (x, y); `gap` is the distance between staff lines (the head's height)."""
    hx, hy = HEAD_CENTRE[value]
    k = gap / STAFF_SPACE
    t = QTransform()
    t.translate(x, y)
    t.scale(k, k)
    t.translate(-hx, -hy)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(colour)
    p.drawPath(t.map(note_shape(value, stem_down)))
    p.restore()
