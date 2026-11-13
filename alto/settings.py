"""
User settings. Pure Python (no Qt); persistence lives in ui/settings_panel.py.

Each exercise with settings has a small dataclass here (`NoteNameSettings`, `KeyboardSettings` and so on) and one shared
instance of it (`note_names`, `keyboard` ...) that the exercise and its settings panel both read and write.

Examples
--------
>>> NoteNameSettings().active_clefs()
['treble', 'bass']
>>> spell(Note.parse("F#4"))
'F♯'
"""

from __future__ import annotations

from dataclasses import (
    KW_ONLY,
    dataclass,
    field,
)

from alto.theory.pitch import (
    ACCIDENTAL_SYMBOLS,
    LETTERS,
    Note,
)

# The clefs with a single staff. The C clefs differ only in the line the clef sits on: soprano on the bottom line, mezzo-soprano
# on the second, alto on the middle, tenor on the fourth and baritone on the top line.
CLEFS = (
    "treble",
    "bass",
    "alto",
    "tenor",
    "soprano",
    "mezzo",
    "baritone",
)
# How the clefs are grouped on the settings pages: the grand staff, the four in everyday use, and the three rarer ones.
CLEF_GROUPS = (
    ("grand",),
    (
        "treble",
        "bass",
        "alto",
        "tenor",
    ),
    ("soprano", "mezzo", "baritone"),
)
RANGE_KEYS = (*CLEFS, "grand")  # clefs that can have a note range
# Inclusive diatonic range of notes that may be asked, per clef (defaults sit comfortably on the staff).
DEFAULT_RANGES = {
    "treble": (Note(3, letter=1).diatonic, Note(7, letter=3).diatonic),  # D3..F7
    "bass": (Note(1, letter=3).diatonic, Note(5, letter=5).diatonic),  # F1..A5
    "alto": (Note(3, letter=0).diatonic, Note(5, letter=0).diatonic),  # C3..C5
    "tenor": (Note(2, letter=5).diatonic, Note(4, letter=5).diatonic),  # A2..A4
    "soprano": (Note(3, letter=4).diatonic, Note(5, letter=4).diatonic),  # G3..G5
    "mezzo": (Note(3, letter=2).diatonic, Note(5, letter=2).diatonic),  # E3..E5
    "baritone": (Note(2, letter=3).diatonic, Note(4, letter=3).diatonic),  # F2..F4
    "grand": (Note(2, letter=0).diatonic, Note(6, letter=0).diatonic),  # C2..C6
}
# Bounds for the range pickers: C1..C7.
MIN_DIATONIC, MAX_DIATONIC = Note(1, letter=0).diatonic, Note(7, letter=0).diatonic


NOTE_VALUES = (
    "breve",
    "whole",
    "half",
    "quarter",
    "eighth",
    "sixteenth",
    "thirty_second",
)
NAMINGS = {"letters": "Letters (C D E)", "solfege": "Solfège (Do Re Mi)"}
SOLFEGE = (
    "Do",
    "Re",
    "Mi",
    "Fa",
    "Sol",
    "La",
    "Si",
)


# How far the range arrows may go: up to 5 ledger lines (10 steps) beyond the staff.
_BOTTOM_LINES = {
    "treble": Note(4, letter=2),
    "bass": Note(2, letter=4),
    "alto": Note(3, letter=3),
    "tenor": Note(3, letter=1),  # E4 G2 F3 D3
    "soprano": Note(4, letter=0),
    "mezzo": Note(3, letter=5),
    "baritone": Note(2, letter=6),
}  # C4 A3 B2
RANGE_LIMITS = {
    **{c: (max(MIN_DIATONIC, n.diatonic - 10), min(MAX_DIATONIC, n.diatonic + 8 + 10)) for c, n in _BOTTOM_LINES.items()},
    "grand": (
        max(MIN_DIATONIC, _BOTTOM_LINES["bass"].diatonic - 10),
        min(MAX_DIATONIC, _BOTTOM_LINES["treble"].diatonic + 8 + 10),
    ),
    # The treble range runs from D3 to F7 and the bass range from F1 to A5. These are also the furthest the pickers go.
    "treble": DEFAULT_RANGES["treble"],
    "bass": DEFAULT_RANGES["bass"],
}


def spell(
    note: Note,
    *,
    naming: str = "letters",
) -> str:
    """
    Return the pitch-class name of a note in the chosen naming system.

    Parameters
    ----------
    note : Note
        The note.
    naming : str, default "letters"
        "letters" for C D E, or "solfege" for Do Re Mi. Keyword-only.

    Returns
    -------
    str
        The name with its accidental, without the octave.

    Examples
    --------
    >>> spell(Note.parse("F#4"))
    'F♯'
    >>> spell(Note.parse("F#4"), naming="solfege")
    'Fa♯'
    """
    base = SOLFEGE[note.letter] if naming == "solfege" else LETTERS[note.letter]
    return base + ACCIDENTAL_SYMBOLS[note.accidental]


def diatonic_name(d: int) -> str:
    """
    Return the name and octave of the natural note on a staff step.

    Parameters
    ----------
    d : int
        The staff-step index (see `Note.diatonic`).

    Returns
    -------
    str
        For example 'E4'.

    Examples
    --------
    >>> diatonic_name(30)
    'E4'
    """
    n = Note.from_diatonic(d)
    return f"{n.name}{n.octave}"


@dataclass
class NoteNameSettings:
    """
    The settings of the note identification exercise.

    Attributes
    ----------
    clefs : set of str
        The clefs to ask on, any of `RANGE_KEYS`, so "grand" is allowed.
    ranges : dict of str to tuple of (int, int)
        Overrides of `DEFAULT_RANGES`, as inclusive staff-step ranges. Keyword-only.
    key_signatures : set of int
        The keys to use, as sharps (positive) or flats (negative). Keyword-only.
    note_values : set of str
        The note values to draw, from `NOTE_VALUES`. Keyword-only.
    naming : str, default "letters"
        A key of `NAMINGS`. Keyword-only.
    accidentals : bool, default False
        Also ask notes with explicit sharps, flats and naturals. Keyword-only.

    Examples
    --------
    >>> cfg = NoteNameSettings(clefs={"bass"}, key_signatures={2})
    >>> cfg.active_clefs(), cfg.active_keys()
    (['bass'], [2])
    """

    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of RANGE_KEYS, so "grand" is allowed
    _: KW_ONLY
    ranges: dict[str, tuple[int, int]] = field(default_factory=dict)  # overrides of DEFAULT_RANGES
    key_signatures: set[int] = field(default_factory=lambda: {0})  # sharps (+) / flats (-) of the keys to use
    note_values: set[str] = field(default_factory=lambda: {"whole"})
    naming: str = "letters"  # key of NAMINGS
    accidentals: bool = False  # also ask notes with explicit sharps/flats/naturals

    def active_clefs(self) -> list[str]:
        """
        Return the clefs to draw from, in canonical order.

        Returns
        -------
        list of str
            The chosen clefs, or the treble clef if none are chosen.

        Examples
        --------
        >>> NoteNameSettings(clefs={"grand", "tenor"}).active_clefs()
        ['tenor', 'grand']
        >>> NoteNameSettings(clefs=set()).active_clefs()
        ['treble']
        """
        return [c for c in RANGE_KEYS if c in self.clefs] or ["treble"]

    def active_keys(self) -> list[int]:
        """
        Return the key signatures to draw from, lowest first.

        Returns
        -------
        list of int
            Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

        Examples
        --------
        >>> NoteNameSettings(key_signatures={2, -1}).active_keys()
        [-1, 2]
        """
        return sorted(self.key_signatures) or [0]

    def active_values(self) -> list[str]:
        """
        Return the note values to draw, from longest to shortest.

        Returns
        -------
        list of str
            The chosen values in the order of `NOTE_VALUES`, or whole notes if none are chosen.

        Examples
        --------
        >>> NoteNameSettings(note_values={"half", "whole"}).active_values()
        ['whole', 'half']
        """
        return [v for v in NOTE_VALUES if v in self.note_values] or ["whole"]

    def range_for(self, clef: str) -> tuple[int, int]:
        """
        Return the range of notes that may be asked on a clef.

        Parameters
        ----------
        clef : str
            A key of `DEFAULT_RANGES`.

        Returns
        -------
        tuple of (int, int)
            The lowest and highest staff step, inclusive; the user's override if there is one, otherwise the default.

        Examples
        --------
        >>> NoteNameSettings().range_for("treble")
        (22, 52)
        >>> NoteNameSettings(ranges={"treble": (40, 30)}).range_for("treble")  # given the wrong way round
        (30, 40)
        """
        lo, hi = self.ranges.get(clef, DEFAULT_RANGES[clef])
        return (lo, hi) if lo <= hi else (hi, lo)


note_names = NoteNameSettings()

# Keyboard exercise: the whole piano is A0..C8 (MIDI 21..108); by default it asks C3..C5.
KEYBOARD_FULL = (21, 108)
KEYBOARD_DEFAULT = (48, 72)
_SHARP_NAMES = (
    "C",
    "C♯",
    "D",
    "D♯",
    "E",
    "F",
    "F♯",
    "G",
    "G♯",
    "A",
    "A♯",
    "B",
)


def key_name(midi: int) -> str:
    """
    Return the name of a MIDI note with its octave, black keys as sharps.

    Parameters
    ----------
    midi : int
        The MIDI note number.

    Returns
    -------
    str
        For example 'C4' for 60 and 'C♯4' for 61.

    Examples
    --------
    >>> key_name(60), key_name(61)
    ('C4', 'C♯4')
    """
    return f"{_SHARP_NAMES[midi % 12]}{midi // 12 - 1}"


@dataclass
class KeyboardSettings:
    """
    The settings of the keyboard identification exercise.

    Attributes
    ----------
    black_keys : bool, default True
        Also ask the black keys, answered by either enharmonic name.
    require_octave : bool, default False
        The answer must include the octave number as well. Keyword-only.
    low : int
        The lowest key asked, as a MIDI number. Keyword-only.
    high : int
        The highest key asked, as a MIDI number, inclusive. Keyword-only.
    key_signature : bool, default False
        Show a key signature, and require the name that fits it (no enharmonic spelling). Keyword-only.
    keys : set of int
        The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

    Examples
    --------
    >>> cfg = KeyboardSettings()
    >>> key_name(cfg.low), key_name(cfg.high)
    ('C3', 'C5')
    """

    black_keys: bool = True  # also ask the black keys, answered by either enharmonic name
    _: KW_ONLY
    require_octave: bool = False  # the answer must include the octave number as well
    low: int = KEYBOARD_DEFAULT[0]  # lowest and highest key asked (MIDI numbers, inclusive)
    high: int = KEYBOARD_DEFAULT[1]
    key_signature: bool = False  # show a key signature, and require the name that fits it (no enharmonic spelling)
    keys: set[int] = field(
        default_factory=lambda: {
            -3,
            -2,
            -1,
            0,
            1,
            2,
            3,
        },
    )  # sharps (+) / flats (-) to draw from

    def active_keys(self) -> list[int]:
        """
        Return the key signatures to draw from, lowest first.

        Returns
        -------
        list of int
            Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

        Examples
        --------
        >>> KeyboardSettings().active_keys()
        [-3, -2, -1, 0, 1, 2, 3]
        """
        return sorted(self.keys) or [0]


keyboard = KeyboardSettings()


@dataclass
class ConstructionSettings:
    """
    The settings of the note construction exercise.

    Attributes
    ----------
    clefs : set of str
        The clefs to ask on, any of `RANGE_KEYS`, so "grand" is allowed.
    accidentals : bool, default False
        Also ask for sharps and flats, which the answer then has to include. Keyword-only.
    key_signature : bool, default False
        Draw a key signature; it applies to the note unless the note is given its own sign. Keyword-only.
    keys : set of int
        The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

    Examples
    --------
    >>> ConstructionSettings(clefs={"grand"}).active_clefs()
    ['grand']
    """

    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of RANGE_KEYS, so "grand" is allowed
    _: KW_ONLY
    accidentals: bool = False  # also ask for sharps and flats, which the answer then has to include
    key_signature: bool = False  # draw a key signature; it applies to the note unless you give the note its own sign
    keys: set[int] = field(
        default_factory=lambda: {
            -3,
            -2,
            -1,
            0,
            1,
            2,
            3,
        },
    )  # sharps (+) / flats (-) to draw from

    def active_clefs(self) -> list[str]:
        """
        Return the clefs to draw from, in canonical order.

        Returns
        -------
        list of str
            The chosen clefs, or the treble clef if none are chosen.

        Examples
        --------
        >>> ConstructionSettings().active_clefs()
        ['treble', 'bass']
        """
        return [c for c in RANGE_KEYS if c in self.clefs] or ["treble"]

    def active_keys(self) -> list[int]:
        """
        Return the key signatures to draw from, lowest first.

        Returns
        -------
        list of int
            Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

        Examples
        --------
        >>> ConstructionSettings(keys={3, -2}).active_keys()
        [-2, 3]
        """
        return sorted(self.keys) or [0]


construction = ConstructionSettings()


# Arpeggio exercise. The chord types are the names in theory.scales.CHORDS, triads first and then seventh chords.
ARPEGGIO_TRIADS = (
    "major",
    "minor",
    "diminished",
    "augmented",
)
ARPEGGIO_SEVENTHS = (
    "dominant 7th",
    "major 7th",
    "minor 7th",
    "half-diminished 7th",
    "diminished 7th",
)
ARPEGGIO_TYPES = ARPEGGIO_TRIADS + ARPEGGIO_SEVENTHS
INVERSIONS = (
    0,
    1,
    2,
    3,
)  # root position, 1st, 2nd and 3rd inversion (the 3rd only exists for seventh chords)


@dataclass
class ArpeggioSettings:
    """
    The settings of the arpeggio identification exercise.

    Attributes
    ----------
    clefs : set of str
        The clefs to draw on, any of `CLEFS`.
    types : set of str
        The chord types to ask, from `ARPEGGIO_TYPES`. Keyword-only.
    inversions : set of int
        The inversions to ask: 0 for root position up to 3 for the third inversion. Keyword-only.
    key_signature : bool, default False
        Draw a key signature, so the arpeggio only gets signs where it differs from it. Keyword-only.
    keys : set of int
        The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

    Examples
    --------
    >>> ArpeggioSettings().active_types()
    ['major', 'minor', 'dominant 7th', 'diminished 7th']
    """

    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of CLEFS
    _: KW_ONLY
    types: set[str] = field(
        default_factory=lambda: {
            "major",
            "minor",
            "dominant 7th",
            "diminished 7th",
        },
    )
    inversions: set[int] = field(default_factory=lambda: set(INVERSIONS))
    key_signature: bool = False  # draw a key signature, so the arpeggio only gets signs where it differs from it
    keys: set[int] = field(
        default_factory=lambda: {
            -3,
            -2,
            -1,
            0,
            1,
            2,
            3,
        },
    )  # sharps (+) / flats (-) to draw from

    def active_clefs(self) -> list[str]:
        """
        Return the clefs to draw from, in canonical order.

        Returns
        -------
        list of str
            The chosen clefs, or the treble clef if none are chosen.

        Examples
        --------
        >>> ArpeggioSettings(clefs={"tenor", "alto"}).active_clefs()
        ['alto', 'tenor']
        """
        return [c for c in CLEFS if c in self.clefs] or ["treble"]

    def active_types(self) -> list[str]:
        """
        Return the chord types to ask, triads first and then seventh chords.

        Returns
        -------
        list of str
            The chosen types in the order of `ARPEGGIO_TYPES`, or "major" if none are chosen.

        Examples
        --------
        >>> ArpeggioSettings(types={"minor 7th", "major"}).active_types()
        ['major', 'minor 7th']
        """
        return [t for t in ARPEGGIO_TYPES if t in self.types] or ["major"]

    def active_inversions(self) -> list[int]:
        """
        Return the inversions to ask, root position first.

        Returns
        -------
        list of int
            The chosen inversions, or root position (0) if none are chosen.

        Examples
        --------
        >>> ArpeggioSettings(inversions={2, 0}).active_inversions()
        [0, 2]
        """
        return [i for i in INVERSIONS if i in self.inversions] or [0]

    def inversions_for(self, chord_type: str) -> list[int]:
        """
        Return the inversions that can be asked for a chord type.

        A triad has no third inversion. If none of the chosen inversions applies (only the third, for a triad), root position is
        used.

        Parameters
        ----------
        chord_type : str
            A key of `CHORDS`, such as "major" or "dominant 7th".

        Returns
        -------
        list of int
            The inversions to choose from.

        Examples
        --------
        >>> cfg = ArpeggioSettings()
        >>> cfg.inversions_for("major"), cfg.inversions_for("dominant 7th")
        ([0, 1, 2], [0, 1, 2, 3])
        >>> ArpeggioSettings(inversions={3}).inversions_for("major")
        [0]
        """
        allowed = [i for i in self.active_inversions() if i < (3 if chord_type in ARPEGGIO_TRIADS else 4)]
        return allowed or [0]

    def active_keys(self) -> list[int]:
        """
        Return the key signatures to draw from, lowest first.

        Returns
        -------
        list of int
            Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

        Examples
        --------
        >>> ArpeggioSettings(keys={1}).active_keys()
        [1]
        """
        return sorted(self.keys) or [0]


arpeggio = ArpeggioSettings()


# Key signature exercise: read the signature on a staff and name the key, or count its sharps and flats.
KEY_QUESTIONS = {"read": "Name the key from its signature", "count": "Count the sharps or flats"}
KEY_MODES = (
    "Major (Ionian)",
    "Dorian",
    "Phrygian",
    "Lydian",
    "Mixolydian",
    "Natural minor (Aeolian)",
    "Locrian",
)
MODE_LABELS = {
    "Major (Ionian)": "Major (Ionian)",
    "Dorian": "Dorian",
    "Phrygian": "Phrygian",
    "Lydian": "Lydian",
    "Mixolydian": "Mixolydian",
    "Natural minor (Aeolian)": "Minor (Aeolian)",
    "Locrian": "Locrian",
}


@dataclass
class KeySignatureSettings:
    """
    The settings of the key signatures exercise.

    Attributes
    ----------
    questions : set of str
        The kinds of question, keys of `KEY_QUESTIONS`: "read" a signature or "count" its sharps and flats.
    clefs : set of str
        The clefs a signature is drawn on, any of `CLEFS`. Keyword-only.
    modes : set of str
        The scales to ask about, from `KEY_MODES`. Keyword-only.
    keys : set of int
        The key signatures asked, as sharps (positive) or flats (negative). Keyword-only.

    Examples
    --------
    >>> cfg = KeySignatureSettings()
    >>> cfg.active_questions(), len(cfg.active_keys())
    (['read', 'count'], 15)
    """

    questions: set[str] = field(default_factory=lambda: {"read", "count"})  # keys of KEY_QUESTIONS
    _: KW_ONLY
    clefs: set[str] = field(default_factory=lambda: {"treble", "bass"})  # any of CLEFS: the clef the signature is drawn on
    modes: set[str] = field(default_factory=lambda: {"Major (Ionian)", "Natural minor (Aeolian)"})  # of KEY_MODES
    keys: set[int] = field(default_factory=lambda: set(range(-7, 8)))  # the key signatures asked: sharps (+) / flats (-)

    def active_questions(self) -> list[str]:
        """
        Return the kinds of question to ask.

        Returns
        -------
        list of str
            The chosen kinds in the order of `KEY_QUESTIONS`, or "read" if none are chosen.

        Examples
        --------
        >>> KeySignatureSettings(questions={"count"}).active_questions()
        ['count']
        """
        return [q for q in KEY_QUESTIONS if q in self.questions] or ["read"]

    def active_clefs(self) -> list[str]:
        """
        Return the clefs to draw signatures on, in canonical order.

        Returns
        -------
        list of str
            The chosen clefs, or the treble clef if none are chosen.

        Examples
        --------
        >>> KeySignatureSettings().active_clefs()
        ['treble', 'bass']
        """
        return [c for c in CLEFS if c in self.clefs] or ["treble"]

    def active_modes(self) -> list[str]:
        """
        Return the scales to ask about, in the order of `KEY_MODES`.

        Returns
        -------
        list of str
            The chosen modes, or major if none are chosen.

        Examples
        --------
        >>> KeySignatureSettings().active_modes()
        ['Major (Ionian)', 'Natural minor (Aeolian)']
        """
        return [m for m in KEY_MODES if m in self.modes] or ["Major (Ionian)"]

    def active_keys(self) -> list[int]:
        """
        Return the key signatures to ask about, lowest first.

        Returns
        -------
        list of int
            Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

        Examples
        --------
        >>> KeySignatureSettings(keys={3, -4}).active_keys()
        [-4, 3]
        """
        return sorted(self.keys) or [0]


key_signatures = KeySignatureSettings()
