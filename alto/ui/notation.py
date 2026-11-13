"""Notation styles: which music font the staff, clefs, notes and accidentals are engraved in."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from .store import store


@dataclass(frozen=True)
class NotationStyle:
    key: str
    label: str
    note: str  # a few words on where this look comes from
    font: str | None  # key in engraving.json, or None for the built-in Noto Music drawing
    line: float = 1.4  # staff line weight in pixels, for the built-in drawing (the SMuFL fonts state their own)


STYLES = (
    NotationStyle("finalemaestro", "Finale Maestro", "The look of Finale, the long-time publishing standard.", "finalemaestro"),
    NotationStyle("leland", "Leland", "MuseScore 4's font. Light and modern, modelled on SCORE.", "leland"),
    NotationStyle("bravura", "Bravura", "The reference font of the SMuFL standard. Dorico's default.", "bravura"),
    NotationStyle("noto", "Noto Music", "Google's engraved look.", None),
    NotationStyle("sebastian", "Sebastian", "A classic engraved face with generous proportions.", "sebastian"),
    NotationStyle("leipzig", "Leipzig", "The default of Verovio. Crisp and compact.", "leipzig"),
    NotationStyle("eugene", "Eugene", "Inspired by hand-engraved Parisian scores of the early 1900s.", "eugene"),
    NotationStyle("goldenage", "Golden Age", "A heavy, old-fashioned plate-engraved look.", "goldenage"),
    NotationStyle("petaluma", "Petaluma", "Handwritten look, as in jazz real books.", "petaluma"),
    NotationStyle("musejazz", "MuseJazz", "Brush-pen hand, like MuseScore's jazz template.", "musejazz"),
    NotationStyle("finalebroadway", "Finale Broadway", "Bold copyist's hand, as in Broadway scores.", "finalebroadway"),
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
