"""Notation styles: which music font the staff, clefs, notes and accidentals are engraved in."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

from PySide6.QtWidgets import QApplication

from .store import store


@dataclass(frozen=True)
class NotationStyle:
    key: str
    _: KW_ONLY
    label: str
    note: str  # a few words on where this look comes from
    font: str | None  # key in engraving.json, or None for the built-in Noto Music drawing
    line: float = 1.4  # staff line weight in pixels, for the built-in drawing (the SMuFL fonts state their own)


STYLES = (
    NotationStyle(
        "finalemaestro",
        label="Finale Maestro",
        note="The look of Finale, the long-time publishing standard.",
        font="finalemaestro",
    ),
    NotationStyle(
        "leland",
        label="Leland",
        note="MuseScore 4's font. Light and modern, modelled on SCORE.",
        font="leland",
    ),
    NotationStyle(
        "bravura",
        label="Bravura",
        note="The reference font of the SMuFL standard. Dorico's default.",
        font="bravura",
    ),
    NotationStyle(
        "noto",
        label="Noto Music",
        note="Google's engraved look.",
        font=None,
    ),
    NotationStyle(
        "sebastian",
        label="Sebastian",
        note="A classic engraved face with generous proportions.",
        font="sebastian",
    ),
    NotationStyle(
        "leipzig",
        label="Leipzig",
        note="The default of Verovio. Crisp and compact.",
        font="leipzig",
    ),
    NotationStyle(
        "eugene",
        label="Eugene",
        note="Inspired by hand-engraved Parisian scores of the early 1900s.",
        font="eugene",
    ),
    NotationStyle(
        "goldenage",
        label="Golden Age",
        note="A heavy, old-fashioned plate-engraved look.",
        font="goldenage",
    ),
    NotationStyle(
        "petaluma",
        label="Petaluma",
        note="Handwritten look, as in jazz real books.",
        font="petaluma",
    ),
    NotationStyle(
        "musejazz",
        label="MuseJazz",
        note="Brush-pen hand, like MuseScore's jazz template.",
        font="musejazz",
    ),
    NotationStyle(
        "finalebroadway",
        label="Finale Broadway",
        note="Bold copyist's hand, as in Broadway scores.",
        font="finalebroadway",
    ),
)
DEFAULT = "finalemaestro"
BY_KEY = {s.key: s for s in STYLES}
_current = BY_KEY[DEFAULT]

# The baritone clef is written two ways, on the same staff (the bottom line is B2 and the top line is C4): as an F clef on
# the middle line, like a bass clef moved up, or as a C clef on the top line, like an alto clef moved up.
BARITONE_CLEFS = {"f": "F clef, on the middle line", "c": "C clef, on the top line"}
DEFAULT_BARITONE = "f"
_baritone = DEFAULT_BARITONE


def baritone_clef() -> str:
    """Which way the baritone clef is written: 'f' or 'c'."""
    return _baritone


def clef_shape(clef: str) -> str:
    """The clef as it is drawn: 'baritone' becomes 'baritone_f' or 'baritone_c' by the chosen way of writing it."""
    return f"baritone_{_baritone}" if clef == "baritone" else clef


def set_baritone_clef(kind: str) -> None:
    """Choose and save how the baritone clef is written, and redraw every staff already on screen."""
    global _baritone
    _baritone = kind if kind in BARITONE_CLEFS else DEFAULT_BARITONE
    store().setValue("ui/baritoneClef", _baritone)
    _redraw()


def current() -> NotationStyle:
    return _current


def load_style() -> None:
    """Apply the saved style (Finale Maestro if none is saved or it is unknown)."""
    global _current
    global _baritone
    _current = BY_KEY.get(str(store().value("ui/notation", DEFAULT)), BY_KEY[DEFAULT])
    saved = str(store().value("ui/baritoneClef", DEFAULT_BARITONE))
    _baritone = saved if saved in BARITONE_CLEFS else DEFAULT_BARITONE


def set_style(key: str) -> None:
    """Choose and save a style, and redraw every staff already on screen."""
    global _current
    _current = BY_KEY.get(key, BY_KEY[DEFAULT])
    store().setValue("ui/notation", _current.key)
    _redraw()


def _redraw() -> None:
    from .staff import StaffWidget  # imported here: staff.py imports this module

    for w in QApplication.allWidgets():
        if isinstance(w, StaffWidget):
            w.update()
