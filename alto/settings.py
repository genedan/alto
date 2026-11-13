"""User settings. Pure Python (no Qt); persistence lives in ui/settings_panel.py."""
from __future__ import annotations

from dataclasses import dataclass, field

from .theory.pitch import ACCIDENTAL_SYMBOLS, LETTERS, Note

# The clefs with a single staff. The C clefs differ only in the line the clef sits on: soprano on the bottom line, mezzo-soprano
# on the second, alto on the middle, tenor on the fourth and baritone on the top line.
CLEFS = ("treble", "bass", "alto", "tenor", "soprano", "mezzo", "baritone")
# How the clefs are grouped on the settings pages: the grand staff, the four in everyday use, and the three rarer ones.
CLEF_GROUPS = (("grand",), ("treble", "bass", "alto", "tenor"), ("soprano", "mezzo", "baritone"))
RANGE_KEYS = (*CLEFS, "grand")  # clefs that can have a note range
# Inclusive diatonic range of notes that may be asked, per clef (defaults sit comfortably on the staff).
DEFAULT_RANGES = {
    "treble": (Note(3, 1).diatonic, Note(7, 3).diatonic),  # D3..F7
    "bass": (Note(1, 3).diatonic, Note(5, 5).diatonic),    # F1..A5
    "alto": (Note(3, 0).diatonic, Note(5, 0).diatonic),    # C3..C5
    "tenor": (Note(2, 5).diatonic, Note(4, 5).diatonic),   # A2..A4
    "soprano": (Note(3, 4).diatonic, Note(5, 4).diatonic),   # G3..G5
    "mezzo": (Note(3, 2).diatonic, Note(5, 2).diatonic),     # E3..E5
    "baritone": (Note(2, 3).diatonic, Note(4, 3).diatonic),  # F2..F4
    "grand": (Note(2, 0).diatonic, Note(6, 0).diatonic),   # C2..C6
}
# Bounds for the range pickers: C1..C7.
MIN_DIATONIC, MAX_DIATONIC = Note(1, 0).diatonic, Note(7, 0).diatonic


NOTE_VALUES = ("breve", "whole", "half", "quarter", "eighth", "sixteenth", "thirty_second")
NAMINGS = {"letters": "Letters (C D E)", "solfege": "Solfège (Do Re Mi)"}
SOLFEGE = ("Do", "Re", "Mi", "Fa", "Sol", "La", "Si")


# How far the range arrows may go: up to 5 ledger lines (10 steps) beyond the staff.
_BOTTOM_LINES = {"treble": Note(4, 2), "bass": Note(2, 4), "alto": Note(3, 3), "tenor": Note(3, 1),  # E4 G2 F3 D3
                 "soprano": Note(4, 0), "mezzo": Note(3, 5), "baritone": Note(2, 6)}  # C4 A3 B2
RANGE_LIMITS = {
    **{c: (max(MIN_DIATONIC, n.diatonic - 10), min(MAX_DIATONIC, n.diatonic + 8 + 10)) for c, n in _BOTTOM_LINES.items()},
    "grand": (max(MIN_DIATONIC, _BOTTOM_LINES["bass"].diatonic - 10),
              min(MAX_DIATONIC, _BOTTOM_LINES["treble"].diatonic + 8 + 10)),
}
# The treble range runs from D3 to F7 and the bass range from F1 to A5. These are also the furthest the pickers go.
RANGE_LIMITS["treble"] = DEFAULT_RANGES["treble"]
RANGE_LIMITS["bass"] = DEFAULT_RANGES["bass"]


def spell(note: Note, naming: str = "letters") -> str:
    """Pitch-class name of `note` in the chosen naming system, e.g. 'F♯' or 'Fa♯'."""
    base = SOLFEGE[note.letter] if naming == "solfege" else LETTERS[note.letter]
    return base + ACCIDENTAL_SYMBOLS[note.accidental]


def diatonic_name(d: int) -> str:
    n = Note.from_diatonic(d)
    return f"{n.name}{n.octave}"


@dataclass
class NoteNameSettings:
    mode: str = "single"  # "grand" = grand staff; "single" = random pick among `clefs`
    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})
    ranges: dict[str, tuple[int, int]] = field(default_factory=dict)  # overrides of DEFAULT_RANGES
    key_signatures: set[int] = field(default_factory=lambda: {0})  # sharps (+) / flats (-) of the keys to use
    note_values: set[str] = field(default_factory=lambda: {"whole"})
    naming: str = "letters"  # key of NAMINGS
    accidentals: bool = False  # also ask notes with explicit sharps/flats/naturals

    def active_clefs(self) -> list[str]:
        """Clefs to draw from, in canonical order; falls back to treble if none are checked."""
        return [c for c in CLEFS if c in self.clefs] or ["treble"]

    def active_keys(self) -> list[int]:
        return sorted(self.key_signatures) or [0]

    def active_values(self) -> list[str]:
        return [v for v in NOTE_VALUES if v in self.note_values] or ["whole"]

    def range_for(self, clef: str) -> tuple[int, int]:
        lo, hi = self.ranges.get(clef, DEFAULT_RANGES[clef])
        return (lo, hi) if lo <= hi else (hi, lo)


note_names = NoteNameSettings()

# Keyboard exercise: the whole piano is A0..C8 (MIDI 21..108); by default it asks C3..C5.
KEYBOARD_FULL = (21, 108)
KEYBOARD_DEFAULT = (48, 72)
_SHARP_NAMES = ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")


def key_name(midi: int) -> str:
    """Name with octave, black keys as sharps: 60 -> 'C4'."""
    return f"{_SHARP_NAMES[midi % 12]}{midi // 12 - 1}"


@dataclass
class KeyboardSettings:
    black_keys: bool = True  # also ask the black keys, answered by either enharmonic name
    require_octave: bool = False  # the answer must include the octave number as well
    low: int = KEYBOARD_DEFAULT[0]  # lowest and highest key asked (MIDI numbers, inclusive)
    high: int = KEYBOARD_DEFAULT[1]
    key_signature: bool = False  # show a key signature, and require the name that fits it (no enharmonic spelling)
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3})  # sharps (+) / flats (-) to draw from

    def active_keys(self) -> list[int]:
        return sorted(self.keys) or [0]


keyboard = KeyboardSettings()


@dataclass
class ConstructionSettings:
    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of RANGE_KEYS, so "grand" is allowed
    accidentals: bool = False  # also ask for sharps and flats, which the answer then has to include
    key_signature: bool = False  # draw a key signature; it applies to the note unless you give the note its own sign
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3})  # sharps (+) / flats (-) to draw from

    def active_clefs(self) -> list[str]:
        return [c for c in RANGE_KEYS if c in self.clefs] or ["treble"]

    def active_keys(self) -> list[int]:
        return sorted(self.keys) or [0]


construction = ConstructionSettings()


# Arpeggio exercise. The chord types are the names in theory.scales.CHORDS, triads first and then seventh chords.
ARPEGGIO_TRIADS = ("major", "minor", "diminished", "augmented")
ARPEGGIO_SEVENTHS = ("dominant 7th", "major 7th", "minor 7th", "half-diminished 7th", "diminished 7th")
ARPEGGIO_TYPES = ARPEGGIO_TRIADS + ARPEGGIO_SEVENTHS
INVERSIONS = (0, 1, 2, 3)  # root position, 1st, 2nd and 3rd inversion (the 3rd only exists for seventh chords)


@dataclass
class ArpeggioSettings:
    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of CLEFS
    types: set[str] = field(default_factory=lambda: {"major", "minor", "dominant 7th", "diminished 7th"})
    inversions: set[int] = field(default_factory=lambda: set(INVERSIONS))
    key_signature: bool = False  # draw a key signature, so the arpeggio only gets signs where it differs from it
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3})  # sharps (+) / flats (-) to draw from

    def active_clefs(self) -> list[str]:
        return [c for c in CLEFS if c in self.clefs] or ["treble"]

    def active_types(self) -> list[str]:
        return [t for t in ARPEGGIO_TYPES if t in self.types] or ["major"]

    def active_inversions(self) -> list[int]:
        return [i for i in INVERSIONS if i in self.inversions] or [0]

    def inversions_for(self, chord_type: str) -> list[int]:
        """The inversions that can be asked for this type: a triad has no 3rd inversion. If none of the chosen
        inversions applies (only the 3rd, for a triad), root position is used."""
        allowed = [i for i in self.active_inversions() if i < (3 if chord_type in ARPEGGIO_TRIADS else 4)]
        return allowed or [0]

    def active_keys(self) -> list[int]:
        return sorted(self.keys) or [0]


arpeggio = ArpeggioSettings()


# Key signature exercise: read the signature on a staff and name the key, or count its sharps and flats.
KEY_QUESTIONS = {"read": "Name the key from its signature", "count": "Count the sharps or flats"}
KEY_MODES = ("Major (Ionian)", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Natural minor (Aeolian)", "Locrian")
MODE_LABELS = {"Major (Ionian)": "Major (Ionian)", "Dorian": "Dorian", "Phrygian": "Phrygian", "Lydian": "Lydian",
               "Mixolydian": "Mixolydian", "Natural minor (Aeolian)": "Minor (Aeolian)", "Locrian": "Locrian"}


@dataclass
class KeySignatureSettings:
    questions: set[str] = field(default_factory=lambda: {"read", "count"})  # keys of KEY_QUESTIONS
    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of CLEFS: the clef the signature is drawn on
    modes: set[str] = field(default_factory=lambda: {"Major (Ionian)", "Natural minor (Aeolian)"})  # of KEY_MODES
    keys: set[int] = field(default_factory=lambda: set(range(-7, 8)))  # the key signatures asked: sharps (+) / flats (-)

    def active_questions(self) -> list[str]:
        return [q for q in KEY_QUESTIONS if q in self.questions] or ["read"]

    def active_clefs(self) -> list[str]:
        return [c for c in CLEFS if c in self.clefs] or ["treble"]

    def active_modes(self) -> list[str]:
        return [m for m in KEY_MODES if m in self.modes] or ["Major (Ionian)"]

    def active_keys(self) -> list[int]:
        return sorted(self.keys) or [0]


key_signatures = KeySignatureSettings()
