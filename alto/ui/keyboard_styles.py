"""
Keyboard styles: the colours and materials the on-screen piano keys are drawn in.

There are ready-made styles (`STYLES`) and a custom one built from colours chosen part by part.

Examples
--------
>>> BY_KEY["classic"].label
'Classic'
>>> style_for("no such style").key == DEFAULT
True
"""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QLinearGradient
from PySide6.QtWidgets import QApplication

from .store import store

DEFAULT_CASE = "#2b2b30"


@dataclass(frozen=True)
class KeyboardStyle:
    """
    How a keyboard looks: the colours of the keys and the case, and a few details of the drawing.

    Attributes
    ----------
    key : str
        The identifier saved in the settings.
    label : str
        The name shown in the interface. Keyword-only.
    note : str
        A few words on what it is modelled on. Keyword-only.
    white : tuple of (str, str)
        The natural keys' colour at the top and at the bottom. Keyword-only.
    white_edge : str
        The outline colour of the natural keys. Keyword-only.
    black : tuple of (str, str)
        The sharps' colour at the top and at the bottom. Keyword-only.
    black_edge : str
        The outline colour of the sharps. Keyword-only.
    case : str or None
        The body around the keys; None draws no body. Keyword-only.
    felt : str or None
        A strip of felt under the fallboard. Keyword-only.
    cap : str or None
        A bone cap on top of each sharp. Keyword-only.
    narrow : float, default 1.0
        How wide the sharps are, compared with a piano's. Keyword-only.
    gap : float, default 1.0
        Pixels between neighbouring naturals. Keyword-only.
    rail : float, default 8.0
        The height of the strip above the keys. Keyword-only.
    thick : bool, default False
        Heavy outlines. Keyword-only.
    hue : bool, default False
        Colour each key by its note name. Keyword-only.
    glow : bool, default False
        A soft halo around the outlines. Keyword-only.
    ink : bool, default False
        Hatched sharps, like an engraving. Keyword-only.
    knobs : bool, default False
        A row of organ stop knobs in the strip above the keys. Keyword-only.
    reverse_below : int or None
        Keys under this MIDI number swap colours (an organ's preset keys). Keyword-only.
    dot : str or None
        The colour of a dot that marks every C. Keyword-only.
    round : float, default 7.0
        The most the lower corners of a natural are rounded, in pixels. Keyword-only.

    Examples
    --------
    >>> style = BY_KEY["modern"]
    >>> style.label, style.case
    ('Modern piano', '#0d0d0f')
    """

    key: str
    _: KW_ONLY
    label: str
    note: str  # a few words on what it is modelled on
    white: tuple[str, str]  # natural keys: colour at the top and at the bottom
    white_edge: str
    black: tuple[str, str]  # sharps and flats
    black_edge: str
    case: str | None = DEFAULT_CASE  # the body around the keys; None draws no body
    felt: str | None = None  # a strip of felt under the fallboard
    cap: str | None = None  # a bone cap on top of each sharp
    narrow: float = 1.0  # how wide the sharps are, compared with a piano's
    gap: float = 1.0  # pixels between neighbouring naturals
    rail: float = 8.0  # height of the strip above the keys
    thick: bool = False  # heavy outlines
    hue: bool = False  # colour each key by its note name
    glow: bool = False  # a soft halo around the outlines
    ink: bool = False  # hatched sharps, like an engraving
    knobs: bool = False  # a row of organ stop knobs in the strip above the keys
    reverse_below: int | None = None  # keys under this MIDI number swap colours (an organ's preset keys)
    dot: str | None = None  # colour of a dot that marks every C
    round: float = 7.0  # the most the lower corners of a natural are rounded, in pixels


STYLES = (
    KeyboardStyle(
        "classic",
        label="Classic",
        note="The standard Alto look: white keys in a dark case.",
        white=("#fbfbfc", "#fbfbfc"),
        white_edge="#9a9a9f",
        black=("#1c1c20", "#1c1c20"),
        black_edge="#111114",
    ),
    KeyboardStyle(
        "modern",
        label="Modern piano",
        note="A current upright or grand, with the red felt under the fallboard.",
        white=("#fbfaf7", "#e9e6df"),
        white_edge="#b9b6ae",
        black=("#34343a", "#0e0e10"),
        black_edge="#000000",
        case="#0d0d0f",
        felt="#7d1f27",
    ),
    KeyboardStyle(
        "ivory",
        label="Antique ivory",
        note="Naturals aged to a warm yellow, in a rosewood case.",
        white=("#f1e5c6", "#dccb9e"),
        white_edge="#a8946a",
        black=("#2d2420", "#120d0b"),
        black_edge="#080605",
        case="#4a2a1c",
        felt="#5f2a24",
    ),
    KeyboardStyle(
        "harpsichord-italian",
        label="Harpsichord, Italian",
        note="Boxwood naturals and dark sharps in a cypress case.",
        white=("#ead9aa", "#d6c088"),
        white_edge="#9b8451",
        black=("#3a2b21", "#1b1410"),
        black_edge="#0d0907",
        case="#b98a55",
        narrow=0.87,
        gap=1.5,
        round=2,
    ),
    KeyboardStyle(
        "harpsichord-french",
        label="Harpsichord, French",
        note="Reversed colours: ebony naturals, bone-topped sharps.",
        white=("#2a211c", "#120d0a"),
        white_edge="#000000",
        black=("#4b3b30", "#2a2019"),
        black_edge="#000000",
        case="#1b3a2a",
        cap="#eee3c8",
        narrow=0.87,
        gap=1.5,
        round=2,
    ),
    KeyboardStyle(
        "organ",
        label="Baroque pipe organ",
        note="Bone and ebony keys in an oak case, under a row of stop knobs.",
        white=("#f0e8d2", "#dccfae"),
        white_edge="#a39470",
        black=("#2a211c", "#0e0a08"),
        black_edge="#000000",
        case="#6b4a2c",
        narrow=0.92,
        gap=1.5,
        rail=30.0,
        knobs=True,
        round=2,
    ),
    KeyboardStyle(
        "tonewheel",
        label="Tonewheel organ",
        note="Plastic keys in a walnut case, with the lowest octave reversed.",
        white=("#f6f4ee", "#e4e1d8"),
        white_edge="#aaa79e",
        black=("#2c2c30", "#0c0c0e"),
        black_edge="#000000",
        case="#5a3320",
        reverse_below=60,
        round=2,
    ),
    KeyboardStyle(
        "flat",
        label="Flat and minimal",
        note="No case and no gradients. Reads well at small sizes.",
        white=("#fafafa", "#fafafa"),
        white_edge="#d3d6db",
        black=("#25272c", "#25272c"),
        black_edge="#25272c",
        case=None,
        gap=2,
        rail=4,
    ),
    KeyboardStyle(
        "engraving",
        label="Engraving",
        note="Ink on paper, like a plate in an old method book.",
        white=("#f5efdf", "#f5efdf"),
        white_edge="#2a2620",
        black=("#2a2620", "#2a2620"),
        black_edge="#2a2620",
        case="#efe7d1",
        gap=0,
        rail=4,
        ink=True,
        round=0,
    ),
    KeyboardStyle(
        "colour",
        label="Colour by note",
        note="One hue per semitone, so every C has the same colour.",
        white=("#ffffff", "#ffffff"),
        white_edge="#44000000",
        black=("#222222", "#222222"),
        black_edge="#66000000",
        case=None,
        gap=1.5,
        rail=4,
        hue=True,
    ),
    KeyboardStyle(
        "neon",
        label="Midnight neon",
        note="Dark keys with a cyan glow and magenta sharps.",
        white=("#1d2230", "#141824"),
        white_edge="#35d6e8",
        black=("#241230", "#150a1e"),
        black_edge="#ff4fd0",
        case="#0a0c12",
        gap=2,
        glow=True,
    ),
    KeyboardStyle(
        "contrast",
        label="High contrast",
        note="Pure black and white with heavy outlines and a yellow dot on every C.",
        white=("#ffffff", "#ffffff"),
        white_edge="#000000",
        black=("#000000", "#000000"),
        black_edge="#000000",
        case="#000000",
        gap=2,
        rail=4,
        thick=True,
        dot="#ffd400",
        round=1,
    ),
)
DEFAULT = "classic"
BY_KEY = {s.key: s for s in STYLES}
CUSTOM = "custom"
_current = BY_KEY[DEFAULT]

# The parts of a keyboard you can colour yourself: (key, label, whether it can be left out).
COMPONENTS = (
    ("naturals", "Naturals", False),
    ("sharps", "Sharps", False),
    ("case", "Case", True),
    ("felt", "Felt strip", True),
    ("caps", "Sharp caps", True),
)
DEFAULT_CUSTOM: dict[str, str | None] = {
    "naturals": "#fbfbfc",
    "sharps": "#1c1c20",
    "case": "#2b2b30",
    "felt": None,
    "caps": None,
}
_custom: dict[str, str | None] = dict(DEFAULT_CUSTOM)

# Colours named after what keyboards are made of. They are typical shades, not measurements of one instrument.
MATERIALS = (
    ("Acrylic white", "#fbfaf7"),
    ("Mother-of-pearl", "#f2eee6"),
    ("Ivory", "#f1e5c6"),
    ("Bone", "#eee3c8"),
    ("Boxwood", "#ead9aa"),
    ("Maple", "#e3c08d"),
    ("Cypress", "#b98a55"),
    ("Oak", "#6b4a2c"),
    ("Walnut", "#5a3320"),
    ("Rosewood", "#4a2a1c"),
    ("Ebonised pearwood", "#2a211c"),
    ("Ebony", "#120d0a"),
    ("Black acrylic", "#1c1c20"),
    ("Aluminium", "#b8bcc2"),
    ("Brass", "#b5933a"),
    ("Red felt", "#7d1f27"),
    ("Green baize", "#1b3a2a"),
    ("Blue felt", "#22345a"),
)


def custom_colours() -> dict[str, str | None]:
    """
    Return the colour of each part of the custom keyboard.

    Returns
    -------
    dict of str to str or None
        Part name ("naturals", "sharps", "case", "felt" or "caps") to its colour, or None where an optional part is left out.

    Examples
    --------
    >>> sorted(custom_colours())
    ['caps', 'case', 'felt', 'naturals', 'sharps']
    """
    return dict(_custom)


def custom_style() -> KeyboardStyle:
    """
    Build the style from the custom colours.

    Gradients and outlines are worked out from each part's colour.

    Returns
    -------
    KeyboardStyle
        The custom style, with the key "custom".

    Examples
    --------
    >>> custom_style().key, custom_style().label
    ('custom', 'Custom')
    """
    naturals, sharps = QColor(_custom["naturals"]), QColor(_custom["sharps"])
    case, felt, cap = _custom["case"], _custom["felt"], _custom["caps"]
    return KeyboardStyle(
        CUSTOM,
        label="Custom",
        note="Your own colours, part by part.",
        white=(naturals.name(), naturals.darker(106).name()),
        white_edge=naturals.darker(140).name(),
        black=(sharps.lighter(130).name(), sharps.name()),
        black_edge=sharps.darker(200).name(),
        case=case,
        felt=felt,
        cap=cap,
        rail=8.0 if case or felt else 4.0,
    )


def style_for(key: str) -> KeyboardStyle:
    """
    Return the style with a given key.

    Parameters
    ----------
    key : str
        A key of `BY_KEY`, or "custom".

    Returns
    -------
    KeyboardStyle
        That style; the default (Classic) if the key is not known.

    Examples
    --------
    >>> style_for("modern").label
    'Modern piano'
    >>> style_for("nonsense").label
    'Classic'
    """
    if key == CUSTOM:
        return custom_style()
    return BY_KEY.get(key, BY_KEY[DEFAULT])


def current() -> KeyboardStyle:
    """
    Return the keyboard style in use.

    Returns
    -------
    KeyboardStyle
        The style chosen in the settings (Classic until another is chosen).

    Examples
    --------
    >>> current().key in BY_KEY or current().key == CUSTOM
    True
    """
    return _current


def load_style() -> None:
    """
    Apply the saved style (Classic if none is saved or it is unknown), and the saved custom colours.

    Examples
    --------
    >>> store().setValue("ui/keyboard", "modern")
    >>> load_style()
    >>> current().key
    'modern'
    >>> set_style(DEFAULT)
    """
    global _current
    saved = store()
    for part, default in DEFAULT_CUSTOM.items():
        value = str(saved.value(f"ui/keyboardCustom/{part}", default or "none"))
        if value == "none" and part in ("case", "felt", "caps"):
            _custom[part] = None
        else:
            _custom[part] = value if QColor(value).isValid() else default
    _current = style_for(str(saved.value("ui/keyboard", DEFAULT)))


def set_style(key: str) -> None:
    """
    Choose and save a style, and redraw every keyboard already on screen.

    Parameters
    ----------
    key : str
        A key of `BY_KEY`, or "custom".

    Examples
    --------
    >>> set_style("modern")
    >>> current().label
    'Modern piano'
    >>> set_style(DEFAULT)
    """
    global _current
    _current = style_for(key)
    store().setValue("ui/keyboard", _current.key)
    _redraw()


def set_custom_colour(
    part: str,
    *,
    colour: str | None,
) -> None:
    """
    Colour one part of the custom keyboard and switch to the custom style.

    Parameters
    ----------
    part : str
        One of "naturals", "sharps", "case", "felt" or "caps".
    colour : str or None
        A colour such as '#336699', or None to leave an optional part (case, felt or caps) out. Keyword-only.

    Examples
    --------
    >>> set_custom_colour("naturals", colour="#ffffff")
    >>> current().key, custom_colours()["naturals"]
    ('custom', '#ffffff')
    >>> set_custom_colour("naturals", colour=DEFAULT_CUSTOM["naturals"])
    >>> set_style(DEFAULT)
    """
    _custom[part] = colour
    store().setValue(f"ui/keyboardCustom/{part}", colour or "none")
    set_style(CUSTOM)


def _redraw() -> None:
    """
    Ask every keyboard on screen to lay itself out and paint again.

    Examples
    --------
    >>> _redraw()  # with no keyboards open, nothing happens
    """
    from .keyboard import KeyboardSpan, KeyboardWidget  # imported here: keyboard.py imports this module

    for w in QApplication.allWidgets():
        if isinstance(w, KeyboardWidget):
            w.refit()
        elif isinstance(w, KeyboardSpan):
            w.update()


# -- colours --------------------------------------------------------------------------------------------------------


def reversed_key(
    style: KeyboardStyle,
    *,
    midi: int,
) -> bool:
    """
    Report whether a key has swapped colours, as the low preset keys of an organ do.

    Parameters
    ----------
    style : KeyboardStyle
        The style.
    midi : int
        The key's MIDI number. Keyword-only.

    Returns
    -------
    bool
        True if the style swaps colours below some key and this key is below it.

    Examples
    --------
    >>> from dataclasses import replace
    >>> reversed_key(BY_KEY["classic"], midi=40)
    False
    >>> reversed_key(replace(BY_KEY["classic"], reverse_below=50), midi=40)
    True
    """
    return style.reverse_below is not None and midi < style.reverse_below


def key_brush(
    style: KeyboardStyle,
    *,
    midi: int,
    black: bool,
    y: float,
    height: float,
) -> QBrush:
    """
    Return the fill for a key.

    Parameters
    ----------
    style : KeyboardStyle
        The style.
    midi : int
        The key's MIDI number. Keyword-only.
    black : bool
        True for a sharp or flat, False for a natural. Keyword-only.
    y : float
        The key's top edge, in pixels. Keyword-only.
    height : float
        The key's height, in pixels. Keyword-only.

    Returns
    -------
    QBrush
        A solid colour, a top-to-bottom gradient, or (for styles that colour keys by note) a colour that depends on the note.

    Examples
    --------
    >>> key_brush(BY_KEY["classic"], midi=60, black=False, y=0, height=100).color().name()
    '#fbfbfc'
    >>> key_brush(BY_KEY["modern"], midi=60, black=False, y=0, height=100).gradient() is not None
    True
    """
    pitch = midi % 12
    if style.hue:
        return QBrush(QColor.fromHslF(pitch / 12, 0.55 if black else 0.72, 0.34 if black else 0.76))
    top, bottom = style.black if black != reversed_key(style, midi=midi) else style.white
    if top == bottom:
        return QBrush(QColor(top))
    gradient = QLinearGradient(QPointF(0, y), QPointF(0, y + height))
    gradient.setColorAt(0, QColor(top))
    gradient.setColorAt(1, QColor(bottom))
    return QBrush(gradient)


def edge_color(
    style: KeyboardStyle,
    *,
    midi: int,
    black: bool,
) -> QColor:
    """
    Return the outline colour for a key.

    Parameters
    ----------
    style : KeyboardStyle
        The style.
    midi : int
        The key's MIDI number. Keyword-only.
    black : bool
        True for a sharp or flat, False for a natural. Keyword-only.

    Returns
    -------
    QColor
        The outline colour.

    Examples
    --------
    >>> edge_color(BY_KEY["classic"], midi=60, black=False).name()
    '#9a9a9f'
    >>> edge_color(BY_KEY["classic"], midi=61, black=True).name()
    '#111114'
    """
    return QColor(style.black_edge if black != reversed_key(style, midi=midi) else style.white_edge)
