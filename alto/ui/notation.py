"""Notation styles: which music font the staff, clefs, notes and accidentals are engraved in."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from .store import store


@dataclass(frozen=True)
class NotationStyle:
    key: str
    label: str
    note: str            # a few words on where this look comes from
    font: str | None     # key in engraving.json, or None for the built-in Noto Music drawing
    line: float = 1.4    # staff line weight in pixels, for the built-in drawing (the SMuFL fonts state their own)


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


def current() -> NotationStyle:
    return _current


def load_style() -> None:
    """Apply the saved style (Finale Maestro if none is saved or it is unknown)."""
    global _current
    _current = BY_KEY.get(str(store().value("ui/notation", DEFAULT)), BY_KEY[DEFAULT])


def set_style(key: str) -> None:
    """Choose and save a style, and redraw every staff already on screen."""
    global _current
    _current = BY_KEY.get(key, BY_KEY[DEFAULT])
    store().setValue("ui/notation", _current.key)
    from .staff import StaffWidget  # imported here: staff.py imports this module
    for w in QApplication.allWidgets():
        if isinstance(w, StaffWidget):
            w.update()
