"""
Notation styles: which music font the staff, clefs, notes and accidentals are engraved in.

Also holds the choice of how the baritone clef is written (an F clef or a C clef).

Examples
--------
>>> BY_KEY["leland"].label
'Leland'
>>> clef_shape("treble")
'treble'
"""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

from PySide6.QtWidgets import QApplication

from .store import store


@dataclass(frozen=True)
class NotationStyle:
    """
    One look for the music: a font and how heavy the staff lines are.

    Attributes
    ----------
    key : str
        The identifier saved in the settings.
    label : str
        The name shown in the interface. Keyword-only.
    note : str
        A few words on where this look comes from. Keyword-only.
    font : str or None
        A key in engraving.json, or None for the built-in Noto Music drawing. Keyword-only.
    line : float, default 1.4
        The staff line weight in pixels, for the built-in drawing (the SMuFL fonts state their own). Keyword-only.

    Examples
    --------
    >>> style = BY_KEY["noto"]
    >>> style.label, style.font
    ('Noto Music', None)
    """

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
    """
    Return which way the baritone clef is written.

    Returns
    -------
    str
        "f" for an F clef on the middle line, or "c" for a C clef on the top line.

    Examples
    --------
    >>> baritone_clef() in BARITONE_CLEFS
    True
    """
    return _baritone


def clef_shape(clef: str) -> str:
    """
    Return the clef as it is drawn.

    Parameters
    ----------
    clef : str
        A clef name such as "treble" or "baritone".

    Returns
    -------
    str
        The same name, except that "baritone" becomes "baritone_f" or "baritone_c" by the chosen way of writing it.

    Examples
    --------
    >>> clef_shape("alto")
    'alto'
    >>> set_baritone_clef("c")
    >>> clef_shape("baritone")
    'baritone_c'
    >>> set_baritone_clef("f")  # back to the default
    >>> clef_shape("baritone")
    'baritone_f'
    """
    return f"baritone_{_baritone}" if clef == "baritone" else clef


def set_baritone_clef(kind: str) -> None:
    """
    Choose and save how the baritone clef is written, and redraw every staff already on screen.

    Parameters
    ----------
    kind : str
        "f" or "c"; anything else gives the default (F).

    Examples
    --------
    >>> set_baritone_clef("c")
    >>> baritone_clef()
    'c'
    >>> set_baritone_clef("sideways")  # not a choice: the default
    >>> baritone_clef()
    'f'
    """
    global _baritone
    _baritone = kind if kind in BARITONE_CLEFS else DEFAULT_BARITONE
    store().setValue("ui/baritoneClef", _baritone)
    _redraw()


def current() -> NotationStyle:
    """
    Return the notation style in use.

    Returns
    -------
    NotationStyle
        The style chosen in the settings (Finale Maestro until another is chosen).

    Examples
    --------
    >>> current().key in BY_KEY
    True
    """
    return _current


def load_style() -> None:
    """
    Apply the saved choices: the style (Finale Maestro if none is saved or it is unknown) and the baritone clef.

    Examples
    --------
    >>> store().setValue("ui/notation", "bravura")
    >>> load_style()
    >>> current().key
    'bravura'
    >>> set_style(DEFAULT)  # back to the default
    """
    global _current
    global _baritone
    _current = BY_KEY.get(str(store().value("ui/notation", DEFAULT)), BY_KEY[DEFAULT])
    saved = str(store().value("ui/baritoneClef", DEFAULT_BARITONE))
    _baritone = saved if saved in BARITONE_CLEFS else DEFAULT_BARITONE


def set_style(key: str) -> None:
    """
    Choose and save a style, and redraw every staff already on screen.

    Parameters
    ----------
    key : str
        A key of `BY_KEY`; an unknown key gives the default.

    Examples
    --------
    >>> set_style("leland")
    >>> current().label
    'Leland'
    >>> set_style(DEFAULT)
    """
    global _current
    _current = BY_KEY.get(key, BY_KEY[DEFAULT])
    store().setValue("ui/notation", _current.key)
    _redraw()


def _redraw() -> None:
    """
    Ask every staff on screen to paint itself again.

    Examples
    --------
    >>> _redraw()  # with no staffs open, nothing happens
    """
    from .staff import StaffWidget  # imported here: staff.py imports this module

    for w in QApplication.allWidgets():
        if isinstance(w, StaffWidget):
            w.update()
