"""
Drawing notation with SMuFL music fonts (Bravura, Leland, Petaluma, MuseJazz and others).

A SMuFL font has the parts of a note rather than whole notes: the head, the flag, and the clef and accidental glyphs,
all measured in staff spaces (four to the em). The stem is a plain rectangle that the code draws, placed using the stem
anchors the font publishes for each head. Heights are measured upward, so they are flipped on screen.

Examples
--------
>>> sorted(HEADS)
['breve', 'half', 'whole']
>>> ACCIDENTALS[1]
'accidentalSharp'
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from PySide6.QtCore import (
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QPainterPath,
    QTransform,
)

_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FILES = {
    "bravura": "Bravura.otf",
    "leland": "Leland.otf",
    "petaluma": "Petaluma.otf",
    "musejazz": "MuseJazz.otf",
    "eugene": "Eugene.otf",
    "leipzig": "Leipzig.otf",
    "sebastian": "Sebastian.otf",
    "goldenage": "GoldenAge.otf",
    "finalemaestro": "FinaleMaestro.otf",
    "finalebroadway": "FinaleBroadway.otf",
}
_PX = 100.0  # glyph outlines are taken at 100 px to the em, so one staff space is 25 units
_SPACE = _PX / 4

CODEPOINTS = {
    "brace": 0xE000,
    "gClef": 0xE050,
    "fClef": 0xE062,
    "cClef": 0xE05C,
    "noteheadDoubleWhole": 0xE0A0,
    "noteheadWhole": 0xE0A2,
    "noteheadHalf": 0xE0A3,
    "noteheadBlack": 0xE0A4,
    "flag8thUp": 0xE240,
    "flag8thDown": 0xE241,
    "flag16thUp": 0xE242,
    "flag16thDown": 0xE243,
    "flag32ndUp": 0xE244,
    "flag32ndDown": 0xE245,
    "accidentalFlat": 0xE260,
    "accidentalNatural": 0xE261,
    "accidentalSharp": 0xE262,
    "accidentalDoubleSharp": 0xE263,
    "accidentalDoubleFlat": 0xE264,
}
HEADS = {"breve": "noteheadDoubleWhole", "whole": "noteheadWhole", "half": "noteheadHalf"}
FLAGS = {"eighth": "8th", "sixteenth": "16th", "thirty_second": "32nd"}
ACCIDENTALS = {
    -2: "accidentalDoubleFlat",
    -1: "accidentalFlat",
    0: "accidentalNatural",
    1: "accidentalSharp",
    2: "accidentalDoubleSharp",
}
STEM_LENGTH = {
    "half": 3.5,
    "quarter": 3.5,
    "eighth": 3.5,
    "sixteenth": 4.0,
    "thirty_second": 4.5,
}  # staff spaces

_family: dict[str, str] = {}


@cache
def _all_metrics() -> dict:
    """
    Return the measurements of every font, read once from engraving.json.

    Returns
    -------
    dict
        Font key to its measurements (stem and line thickness, glyph anchors, family name).

    Examples
    --------
    >>> "bravura" in _all_metrics()
    True
    """
    return json.loads((_DIR / "engraving.json").read_text())


def _metrics(font: str) -> dict:
    """
    Return the measurements of one font.

    Parameters
    ----------
    font : str
        A key of `_FILES`, such as "bravura".

    Returns
    -------
    dict
        The font's stem and line thickness, glyph anchors and family name.

    Examples
    --------
    >>> _metrics("bravura")["stem"] > 0
    True
    """
    return _all_metrics()[font]


def _family_of(font: str) -> str:
    """
    Return the font's family name, registering the file with Qt the first time.

    Parameters
    ----------
    font : str
        A key of `_FILES`.

    Returns
    -------
    str
        The family name Qt knows the font by.

    Examples
    --------
    >>> isinstance(_family_of("bravura"), str)
    True
    """
    if font not in _family:
        fid = QFontDatabase.addApplicationFont(str(_DIR / _FILES[font]))
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        _family[font] = families[0] if families else _metrics(font)["family"]
    return _family[font]


@cache
def _outline(
    font: str,
    *,
    name: str,
) -> QPainterPath:
    """
    Return a glyph as a path in font units (100 per em), with its origin at (0, 0) and y pointing down.

    Parameters
    ----------
    font : str
        A key of `_FILES`.
    name : str
        A key of `CODEPOINTS`, such as "gClef" or "noteheadBlack". Keyword-only.

    Returns
    -------
    QPainterPath
        The glyph's outline. The result is remembered.

    Examples
    --------
    >>> _outline("bravura", name="gClef").isEmpty()
    False
    """
    f = QFont(_family_of(font))
    f.setPixelSize(int(_PX))
    path = QPainterPath()
    path.addText(
        0,
        0,
        f,
        chr(CODEPOINTS[name]),
    )
    return path


def _ink(
    font: str,
    *,
    name: str,
) -> tuple[float, float, float, float]:
    """
    Return the extent a glyph actually draws.

    Parameters
    ----------
    font : str
        A key of `_FILES`.
    name : str
        A key of `CODEPOINTS`. Keyword-only.

    Returns
    -------
    tuple of (float, float, float, float)
        Left, bottom, right and top, in staff spaces measured up from the glyph's origin.

    Examples
    --------
    >>> left, bottom, right, top = _ink("bravura", name="noteheadBlack")
    >>> right > left and top > bottom
    True
    """
    r = _outline(font, name=name).boundingRect()
    return r.left() / _SPACE, -r.bottom() / _SPACE, r.right() / _SPACE, -r.top() / _SPACE


def _anchor(
    font: str,
    *,
    name: str,
    anchor: str,
) -> tuple[float, float]:
    """
    Return a stem anchor from the font's metadata.

    If the font does not give one, the place it would normally sit is used.

    Parameters
    ----------
    font : str
        A key of `_FILES`.
    name : str
        The glyph, a key of `CODEPOINTS`. Keyword-only.
    anchor : str
        The anchor's name, such as "stemUpSE" or "stemDownNW". Keyword-only.

    Returns
    -------
    tuple of (float, float)
        The anchor's position in staff spaces from the glyph's origin.

    Examples
    --------
    >>> len(_anchor("bravura", name="noteheadBlack", anchor="stemUpSE"))
    2
    """
    given = _metrics(font)["anchors"].get(name, {}).get(anchor)
    if given:
        return given[0], given[1]
    left, _, right, _ = _ink(font, name=name)
    return {"stemUpSE": (right, 0.17), "stemDownNW": (left, -0.17)}.get(anchor, (0.0, 0.0))


def _place(
    path: QPainterPath,
    *,
    x: float,
    y: float,
    gap: float,
    scale: float = 1.0,
) -> QPainterPath:
    """
    Move and scale a glyph outline to a place on screen.

    Parameters
    ----------
    path : QPainterPath
        The outline, in font units.
    x : float
        Where the glyph's origin goes, in pixels. Keyword-only.
    y : float
        Where the glyph's origin goes, in pixels. Keyword-only.
    gap : float
        The distance between staff lines in pixels, which sets the size. Keyword-only.
    scale : float, default 1.0
        A further scale factor. Keyword-only.

    Returns
    -------
    QPainterPath
        The outline in screen coordinates.

    Examples
    --------
    >>> head = _outline("bravura", name="noteheadBlack")
    >>> round(_place(head, x=50, y=50, gap=10).boundingRect().height())  # a head is about one staff space tall
    10
    """
    t = QTransform()
    t.translate(x, y)
    t.scale(gap / _SPACE * scale, gap / _SPACE * scale)
    return t.map(path)


def staff_line_width(
    font: str,
    *,
    gap: float,
) -> float:
    """
    Return the thickness of a staff line, as the font specifies.

    Parameters
    ----------
    font : str
        A key of `_FILES`.
    gap : float
        The distance between staff lines in pixels. Keyword-only.

    Returns
    -------
    float
        The thickness in pixels, at least 1.

    Examples
    --------
    >>> staff_line_width("bravura", gap=16) >= 1.0
    True
    """
    return max(_metrics(font)["staffLine"] * gap, 1.0)


def ledger_width(
    font: str,
    *,
    gap: float,
) -> float:
    """
    Return the thickness of a ledger line, as the font specifies.

    Parameters
    ----------
    font : str
        A key of `_FILES`.
    gap : float
        The distance between staff lines in pixels. Keyword-only.

    Returns
    -------
    float
        The thickness in pixels, at least 1.2.

    Examples
    --------
    >>> ledger_width("bravura", gap=16) >= 1.2
    True
    """
    return max(_metrics(font)["ledger"] * gap, 1.2)


def _fill(
    p: QPainter,
    *,
    path: QPainterPath,
    colour: QColor,
) -> None:
    """
    Fill a path with a colour and no outline.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    path : QPainterPath
        What to fill. Keyword-only.
    colour : QColor
        The colour. Keyword-only.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(20, 20, QImage.Format.Format_ARGB32)
    >>> image.fill(QColor("white"))
    >>> painter = QPainter(image)
    >>> square = QPainterPath()
    >>> square.addRect(QRectF(5, 5, 10, 10))
    >>> _fill(painter, path=square, colour=QColor("black"))
    >>> painter.end()
    True
    >>> image.pixelColor(10, 10).lightness() < 128
    True
    """
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(colour)
    p.drawPath(path)
    p.restore()


def draw_note(
    p: QPainter,
    *,
    font: str,
    value: str,
    x: float,
    y: float,
    gap: float,
    colour: QColor,
    stem_down: bool = False,
) -> None:
    """
    Draw a note with its head centred on a point.

    The head, then a stem and (for the short values) a flag, placed on the font's anchors.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    font : str
        A key of `_FILES`. Keyword-only.
    value : str
        "breve", "whole", "half", "quarter", "eighth", "sixteenth" or "thirty_second". Keyword-only.
    x : float
        The head's centre, in pixels. Keyword-only.
    y : float
        The head's centre, in pixels. Keyword-only.
    gap : float
        The distance between staff lines in pixels. Keyword-only.
    colour : QColor
        The colour. Keyword-only.
    stem_down : bool, default False
        Draw the stem down. Keyword-only.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
    >>> image.fill(QColor("white"))
    >>> painter = QPainter(image)
    >>> draw_note(painter, font="bravura", value="eighth", x=50, y=60, gap=16, colour=QColor("black"))
    >>> painter.end()
    True
    >>> image.pixelColor(50, 60).lightness() < 128
    True
    """
    head_name = HEADS.get(value, "noteheadBlack")
    left, _, right, _ = _ink(font, name=head_name)
    ox, oy = x - (left + right) / 2 * gap, y  # the head's origin, with the drawn head centred on the line or space
    _fill(
        p,
        path=_place(
            _outline(font, name=head_name),
            x=ox,
            y=oy,
            gap=gap,
        ),
        colour=colour,
    )
    if value in ("breve", "whole"):
        return
    stem_down = bool(stem_down)
    ax, ay = _anchor(font, name=head_name, anchor="stemDownNW" if stem_down else "stemUpSE")
    thick = _metrics(font)["stem"] * gap
    sx = ox + ax * gap  # the stem's edge that touches the head
    sy = oy - ay * gap
    end = y + (1 if stem_down else -1) * STEM_LENGTH[value] * gap  # the far end of the stem, on screen
    left = sx if stem_down else sx - thick
    top, bottom = (sy, end) if stem_down else (end, sy)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(colour)
    p.drawRect(
        QRectF(
            left,
            top,
            thick,
            bottom - top,
        ),
    )
    p.restore()
    if value in FLAGS:
        name = f"flag{FLAGS[value]}{'Down' if stem_down else 'Up'}"
        fx, fy = _anchor(font, name=name, anchor="stemDownSW" if stem_down else "stemUpNW")
        # put the flag's anchor on the stem's far end, on the side the stem's outer edge is on
        _fill(
            p,
            path=_place(
                _outline(font, name=name),
                x=left - fx * gap,
                y=end + fy * gap,
                gap=gap,
            ),
            colour=colour,
        )


def draw_clef(
    p: QPainter,
    *,
    font: str,
    clef: str,
    x: float,
    bottom: float,
    gap: float,
    colour: QColor,
) -> None:
    """
    Draw a clef with its left edge at a point.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    font : str
        A key of `_FILES`. Keyword-only.
    clef : str
        "treble", "bass", "alto", "tenor", "soprano", "mezzo", "baritone_c" or "baritone_f". Keyword-only.
    x : float
        The clef's left edge, in pixels. Keyword-only.
    bottom : float
        The y position of the staff's bottom line, in pixels. Keyword-only.
    gap : float
        The distance between staff lines in pixels. Keyword-only.
    colour : QColor
        The colour. Keyword-only.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
    >>> image.fill(QColor("white"))
    >>> painter = QPainter(image)
    >>> draw_clef(painter, font="bravura", clef="treble", x=10, bottom=70, gap=10, colour=QColor("black"))
    >>> painter.end()
    True
    >>> any(image.pixelColor(x_, y).lightness() < 128 for x_ in range(10, 40) for y in range(20, 90))
    True
    """
    # `line` is how many gaps above the bottom staff line the clef's reference line (the G, F or middle C) is
    name, line = {
        "treble": ("gClef", 1),
        "bass": ("fClef", 3),
        "alto": ("cClef", 2),
        "tenor": ("cClef", 3),
        "soprano": ("cClef", 0),
        "mezzo": ("cClef", 1),
        "baritone_c": ("cClef", 4),
        "baritone_f": ("fClef", 2),
    }[clef]
    _fill(
        p,
        path=_place(
            _outline(font, name=name),
            x=x,
            y=bottom - line * gap,
            gap=gap,
        ),
        colour=colour,
    )


def draw_accidental(
    p: QPainter,
    *,
    font: str,
    sign: int,
    x: float,
    y: float,
    gap: float,
    colour: QColor,
    fit: float | None = None,
) -> float:
    """
    Draw a sharp, flat or natural with its left edge at a point.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    font : str
        A key of `_FILES`. Keyword-only.
    sign : int
        -2 for a double flat, -1 flat, 0 natural, 1 sharp or 2 double sharp. Keyword-only.
    x : float
        The glyph's left edge, in pixels. Keyword-only.
    y : float
        The glyph's reference line, in pixels. Keyword-only.
    gap : float
        The distance between staff lines in pixels. Keyword-only.
    colour : QColor
        The colour. Keyword-only.
    fit : float or None, default None
        If given, shrink the glyph to be no wider than this many pixels. Keyword-only.

    Returns
    -------
    float
        The width drawn, in pixels.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
    >>> painter = QPainter(image)
    >>> normal = draw_accidental(painter, font="bravura", sign=1, x=10, y=50, gap=16, colour=QColor("black"))
    >>> squeezed = draw_accidental(painter, font="bravura", sign=1, x=10, y=50, gap=16, colour=QColor("black"), fit=5.0)
    >>> painter.end()
    True
    >>> squeezed <= 5.0 < normal
    True
    """
    name = ACCIDENTALS[sign]
    left, _, right, _ = _ink(font, name=name)
    width = (right - left) * gap
    k = min(1.0, fit / width) if fit else 1.0
    _fill(
        p,
        path=_place(
            _outline(font, name=name),
            x=x - left * gap * k,
            y=y,
            gap=gap,
            scale=k,
        ),
        colour=colour,
    )
    return width * k


def draw_brace(
    p: QPainter,
    *,
    font: str,
    x: float,
    y0: float,
    y1: float,
    colour: QColor,
    width: float,
) -> bool:
    """
    Draw the font's brace stretched between two heights, for a grand staff.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    font : str
        A key of `_FILES`. Keyword-only.
    x : float
        The brace's right edge, in pixels. Keyword-only.
    y0 : float
        The top, in pixels. Keyword-only.
    y1 : float
        The bottom, in pixels. Keyword-only.
    colour : QColor
        The colour. Keyword-only.
    width : float
        How wide to draw it, in pixels. Keyword-only.

    Returns
    -------
    bool
        True if it was drawn; False (and nothing is drawn) if the font has no usable brace.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
    >>> painter = QPainter(image)
    >>> draw_brace(painter, font="bravura", x=30, y0=10, y1=90, colour=QColor("black"), width=12)
    True
    >>> painter.end()
    True
    """
    outline = _outline(font, name="brace")
    box = outline.boundingRect()
    if outline.isEmpty() or box.width() <= 0 or box.height() < 4 * box.width():  # not a tall, narrow brace
        return False
    t = QTransform()
    t.translate(x - width, y0)
    t.scale(width / box.width(), (y1 - y0) / box.height())
    t.translate(-box.left(), -box.top())
    _fill(p, path=t.map(outline), colour=colour)
    return True
