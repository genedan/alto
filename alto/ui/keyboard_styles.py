"""Keyboard styles: the colours and materials the on-screen piano keys are drawn in."""

from __future__ import annotations

from dataclasses import KW_ONLY, dataclass

from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QLinearGradient
from PySide6.QtWidgets import QApplication

from .store import store

DEFAULT_CASE = "#2b2b30"


@dataclass(frozen=True)
class KeyboardStyle:
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
    """The colour of each part of the custom keyboard (None where a part is left out)."""
    return dict(_custom)


def custom_style() -> KeyboardStyle:
    """The style built from the custom colours: gradients and outlines are worked out from each part's colour."""
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
    if key == CUSTOM:
        return custom_style()
    return BY_KEY.get(key, BY_KEY[DEFAULT])


def current() -> KeyboardStyle:
    return _current


def load_style() -> None:
    """Apply the saved style (Classic if none is saved or it is unknown), and the saved custom colours."""
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
    """Choose and save a style, and redraw every keyboard already on screen."""
    global _current
    _current = style_for(key)
    store().setValue("ui/keyboard", _current.key)
    _redraw()


def set_custom_colour(
    part: str,
    *,
    colour: str | None,
) -> None:
    """Colour one part of the custom keyboard (None leaves an optional part out) and use the custom style."""
    _custom[part] = colour
    store().setValue(f"ui/keyboardCustom/{part}", colour or "none")
    set_style(CUSTOM)


def _redraw() -> None:
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
    return style.reverse_below is not None and midi < style.reverse_below


def key_brush(
    style: KeyboardStyle,
    *,
    midi: int,
    black: bool,
    y: float,
    height: float,
) -> QBrush:
    """The fill of a key whose top edge is at `y` and which is `height` tall."""
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
    return QColor(style.black_edge if black != reversed_key(style, midi=midi) else style.white_edge)
