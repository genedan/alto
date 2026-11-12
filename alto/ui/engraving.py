"""Drawing notation with SMuFL music fonts (Bravura, Leland, Petaluma, MuseJazz).

A SMuFL font has the parts of a note rather than whole notes: the head, the flag, and the clef and accidental
glyphs, all measured in staff spaces (four to the em). The stem is a plain rectangle that the code draws, placed
using the stem anchors the font publishes for each head. Heights are measured upward, so they are flipped on screen.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QTransform

_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FILES = {
    "bravura": "Bravura.otf", "leland": "Leland.otf", "petaluma": "Petaluma.otf", "musejazz": "MuseJazz.otf",
    "eugene": "Eugene.otf", "leipzig": "Leipzig.otf", "sebastian": "Sebastian.otf", "goldenage": "GoldenAge.otf",
    "finalemaestro": "FinaleMaestro.otf", "finalebroadway": "FinaleBroadway.otf",
}
_PX = 100.0  # glyph outlines are taken at 100 px to the em, so one staff space is 25 units
_SPACE = _PX / 4

CODEPOINTS = {
    "brace": 0xE000,
    "gClef": 0xE050, "fClef": 0xE062, "cClef": 0xE05C,
    "noteheadDoubleWhole": 0xE0A0, "noteheadWhole": 0xE0A2, "noteheadHalf": 0xE0A3, "noteheadBlack": 0xE0A4,
    "flag8thUp": 0xE240, "flag8thDown": 0xE241, "flag16thUp": 0xE242, "flag16thDown": 0xE243,
    "flag32ndUp": 0xE244, "flag32ndDown": 0xE245,
    "accidentalFlat": 0xE260, "accidentalNatural": 0xE261, "accidentalSharp": 0xE262,
    "accidentalDoubleSharp": 0xE263, "accidentalDoubleFlat": 0xE264,
}
HEADS = {"breve": "noteheadDoubleWhole", "whole": "noteheadWhole", "half": "noteheadHalf"}
FLAGS = {"eighth": "8th", "sixteenth": "16th", "thirty_second": "32nd"}
ACCIDENTALS = {-2: "accidentalDoubleFlat", -1: "accidentalFlat", 0: "accidentalNatural",
               1: "accidentalSharp", 2: "accidentalDoubleSharp"}
STEM_LENGTH = {"half": 3.5, "quarter": 3.5, "eighth": 3.5, "sixteenth": 4.0, "thirty_second": 4.5}  # staff spaces

_data: dict | None = None
_family: dict[str, str] = {}


def _metrics(font: str) -> dict:
    global _data
    if _data is None:
        _data = json.loads((_DIR / "engraving.json").read_text())
    return _data[font]


def _family_of(font: str) -> str:
    """The font's family name, registering the file with Qt the first time."""
    if font not in _family:
        fid = QFontDatabase.addApplicationFont(str(_DIR / _FILES[font]))
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        _family[font] = families[0] if families else _metrics(font)["family"]
    return _family[font]


@cache
def _outline(font: str, name: str) -> QPainterPath:
    """The glyph as a path in font units (100 per em), with its origin at (0, 0) and y pointing down."""
    f = QFont(_family_of(font))
    f.setPixelSize(int(_PX))
    path = QPainterPath()
    path.addText(0, 0, f, chr(CODEPOINTS[name]))
    return path


def _ink(font: str, name: str) -> tuple[float, float, float, float]:
    """The glyph's drawn extent as (left, bottom, right, top) in staff spaces, measured up from its origin."""
    r = _outline(font, name).boundingRect()
    return r.left() / _SPACE, -r.bottom() / _SPACE, r.right() / _SPACE, -r.top() / _SPACE


def _anchor(font: str, name: str, anchor: str) -> tuple[float, float]:
    """A stem anchor from the font's metadata, or where one would normally sit if the font does not give it."""
    given = _metrics(font)["anchors"].get(name, {}).get(anchor)
    if given:
        return given[0], given[1]
    left, _, right, _ = _ink(font, name)
    return {"stemUpSE": (right, 0.17), "stemDownNW": (left, -0.17)}.get(anchor, (0.0, 0.0))


def _place(path: QPainterPath, x: float, y: float, gap: float, scale: float = 1.0) -> QPainterPath:
    t = QTransform()
    t.translate(x, y)
    t.scale(gap / _SPACE * scale, gap / _SPACE * scale)
    return t.map(path)


def staff_line_width(font: str, gap: float) -> float:
    return max(_metrics(font)["staffLine"] * gap, 1.0)


def ledger_width(font: str, gap: float) -> float:
    return max(_metrics(font)["ledger"] * gap, 1.2)


def _fill(p: QPainter, path: QPainterPath, colour: QColor) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(colour)
    p.drawPath(path)
    p.restore()


def draw_note(p: QPainter, font: str, value: str, x: float, y: float, gap: float, colour: QColor,
              stem_down: bool = False) -> None:
    """A note of this value with its head centred on (x, y); `gap` is the distance between staff lines."""
    head_name = HEADS.get(value, "noteheadBlack")
    left, _, right, _ = _ink(font, head_name)
    ox, oy = x - (left + right) / 2 * gap, y  # the head's origin, with the drawn head centred on the line or space
    _fill(p, _place(_outline(font, head_name), ox, oy, gap), colour)
    if value in ("breve", "whole"):
        return
    stem_down = bool(stem_down)
    ax, ay = _anchor(font, head_name, "stemDownNW" if stem_down else "stemUpSE")
    thick = _metrics(font)["stem"] * gap
    sx = ox + ax * gap                       # the stem's edge that touches the head
    sy = oy - ay * gap
    end = y + (1 if stem_down else -1) * STEM_LENGTH[value] * gap  # the far end of the stem, on screen
    left = sx if stem_down else sx - thick
    top, bottom = (sy, end) if stem_down else (end, sy)
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(colour)
    p.drawRect(QRectF(left, top, thick, bottom - top))
    p.restore()
    if value in FLAGS:
        name = f"flag{FLAGS[value]}{'Down' if stem_down else 'Up'}"
        fx, fy = _anchor(font, name, "stemDownSW" if stem_down else "stemUpNW")
        # put the flag's anchor on the stem's far end, on the side the stem's outer edge is on
        _fill(p, _place(_outline(font, name), left - fx * gap, end + fy * gap, gap), colour)


def draw_clef(p: QPainter, font: str, clef: str, x: float, bottom: float, gap: float, colour: QColor) -> None:
    """The clef with its left edge at x; `bottom` is the y of the staff's bottom line."""
    name, line = {"treble": ("gClef", 1), "bass": ("fClef", 3), "alto": ("cClef", 2), "tenor": ("cClef", 3)}[clef]
    _fill(p, _place(_outline(font, name), x, bottom - line * gap, gap), colour)


def draw_accidental(p: QPainter, font: str, sign: int, x: float, y: float, gap: float, colour: QColor,
                    fit: float | None = None) -> float:
    """An accidental with its left edge at x and its reference line at y. If `fit` is given, the glyph is
    shrunk to be no wider than that many pixels. Returns the width drawn."""
    name = ACCIDENTALS[sign]
    left, _, right, _ = _ink(font, name)
    width = (right - left) * gap
    k = min(1.0, fit / width) if fit else 1.0
    _fill(p, _place(_outline(font, name), x - left * gap * k, y, gap, k), colour)
    return width * k


def draw_brace(p: QPainter, font: str, x: float, y0: float, y1: float, colour: QColor, width: float) -> bool:
    """The font's brace stretched to span y0..y1, `width` wide, with its right edge at x. Returns False (and draws
    nothing) if the font has no brace."""
    outline = _outline(font, "brace")
    box = outline.boundingRect()
    if outline.isEmpty() or box.width() <= 0 or box.height() < 4 * box.width():  # not a tall, narrow brace
        return False
    t = QTransform()
    t.translate(x - width, y0)
    t.scale(width / box.width(), (y1 - y0) / box.height())
    t.translate(-box.left(), -box.top())
    _fill(p, t.map(outline), colour)
    return True
