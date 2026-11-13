"""
Scales, modes, key signatures and chords, built from spelled intervals.

`SCALES` and `CHORDS` map a name to the list of intervals above the tonic or root. `build` turns such a list into notes,
and the other functions work out key signatures, mode tonics and arpeggios from them.

Examples
--------
>>> [str(n) for n in build(Note.parse("D4"), intervals=SCALES["Dorian"])]
['D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']
>>> [str(n) for n in build(Note.parse("C4"), intervals=CHORDS["minor 7th"])]
['C4', 'E♭4', 'G4', 'B♭4']
"""

from __future__ import annotations

from .pitch import LETTERS, MAJOR_KEYS, Interval, Note

I = Interval.parse

SCALES: dict[str, list[Interval]] = {
    name: [I("P1")] + [I(x) for x in ivs.split()]
    for name, ivs in {
        "Major (Ionian)": "M2 M3 P4 P5 M6 M7",
        "Dorian": "M2 m3 P4 P5 M6 m7",
        "Phrygian": "m2 m3 P4 P5 m6 m7",
        "Lydian": "M2 M3 A4 P5 M6 M7",
        "Mixolydian": "M2 M3 P4 P5 M6 m7",
        "Natural minor (Aeolian)": "M2 m3 P4 P5 m6 m7",
        "Locrian": "m2 m3 P4 d5 m6 m7",
        "Harmonic minor": "M2 m3 P4 P5 m6 M7",
        "Melodic minor": "M2 m3 P4 P5 M6 M7",
    }.items()
}

CHORDS: dict[str, list[Interval]] = {
    name: [I("P1")] + [I(x) for x in ivs.split()]
    for name, ivs in {
        "major": "M3 P5",
        "minor": "m3 P5",
        "diminished": "m3 d5",
        "augmented": "M3 A5",
        "major 7th": "M3 P5 M7",
        "dominant 7th": "M3 P5 m7",
        "minor 7th": "m3 P5 m7",
        "half-diminished 7th": "m3 d5 m7",
        "diminished 7th": "m3 d5 d7",
    }.items()
}


# Which degree of the major scale a mode starts on: the Dorian mode on D uses the notes (and so the key signature) of C major.
MODE_DEGREE = {
    "Major (Ionian)": 0,
    "Dorian": 1,
    "Phrygian": 2,
    "Lydian": 3,
    "Mixolydian": 4,
    "Natural minor (Aeolian)": 5,
    "Locrian": 6,
}
# How a mode is named in a question: "major key", "minor key", "Dorian scale".
MODE_WORDS = {"Major (Ionian)": "major key", "Natural minor (Aeolian)": "minor key"}


def major_key_tonic(count: int) -> Note:
    """
    Return the tonic of the major key with a given number of sharps or flats.

    Parameters
    ----------
    count : int
        Sharps (positive) or flats (negative) in the key signature, from -7 to 7.

    Returns
    -------
    Note
        The tonic, in octave 4.

    Raises
    ------
    KeyError
        If `count` is outside -7..7.

    Examples
    --------
    >>> str(major_key_tonic(2))  # two sharps: D major
    'D4'
    >>> str(major_key_tonic(-3))  # three flats: E♭ major
    'E♭4'
    """
    name = MAJOR_KEYS[count]
    letter = LETTERS.index(name[0])
    return Note(4, letter=letter, accidental={"": 0, "♯": 1, "♭": -1}[name[1:]])


def mode_tonic(
    count: int,
    *,
    mode: str,
) -> Note:
    """
    Return the note a scale in a given mode starts on, for a given key signature.

    The notes of a mode are those of a major scale started from another degree. D Dorian, for example, has the key
    signature of C major, started from its second note.

    Parameters
    ----------
    count : int
        Sharps (positive) or flats (negative) in the key signature, from -7 to 7.
    mode : str
        A key of `MODE_DEGREE`, such as "Dorian" or "Natural minor (Aeolian)". Keyword-only.

    Returns
    -------
    Note
        The tonic of that mode, in octave 4 or 5.

    Examples
    --------
    >>> str(mode_tonic(0, mode="Dorian"))  # no sharps or flats: D Dorian
    'D4'
    >>> str(mode_tonic(2, mode="Natural minor (Aeolian)"))  # two sharps: B minor
    'B4'
    """
    return build(major_key_tonic(count), intervals=SCALES["Major (Ionian)"])[MODE_DEGREE[mode]]


INVERSION_NAMES = (
    "root position",
    "1st inversion",
    "2nd inversion",
    "3rd inversion",
)
OCTAVE = Interval(8, quality="P")


def arpeggio(
    root: Note,
    *,
    intervals: list[Interval],
    inversion: int = 0,
) -> list[Note]:
    """
    Return a chord broken and rising from its lowest note, then that note again an octave higher.

    Parameters
    ----------
    root : Note
        The root of the chord.
    intervals : list of Interval
        The intervals above the root that make the chord, such as `CHORDS["major"]`. Keyword-only.
    inversion : int, default 0
        How many of the lowest chord tones are moved up an octave first: 0 is root position, 1 puts the third at the
        bottom, 2 the fifth. Keyword-only.

    Returns
    -------
    list of Note
        The chord tones from the lowest up, ending on the lowest note an octave higher.

    Examples
    --------
    >>> [str(n) for n in arpeggio(Note.parse("C4"), intervals=CHORDS["major"])]
    ['C4', 'E4', 'G4', 'C5']
    >>> [str(n) for n in arpeggio(Note.parse("C4"), intervals=CHORDS["major"], inversion=1)]
    ['E4', 'G4', 'C5', 'E5']
    """
    tones = build(root, intervals=intervals)
    for _ in range(inversion):
        tones.append(tones.pop(0).transpose(OCTAVE))
    return tones + [tones[0].transpose(OCTAVE)]


def build(
    tonic: Note,
    *,
    intervals: list[Interval],
) -> list[Note]:
    """
    Build the notes of a scale or chord above a tonic.

    Parameters
    ----------
    tonic : Note
        The first note.
    intervals : list of Interval
        The intervals above the tonic, including the unison, such as a value of `SCALES` or `CHORDS`. Keyword-only.

    Returns
    -------
    list of Note
        The tonic transposed by each interval, in order.

    Examples
    --------
    >>> [str(n) for n in build(Note.parse("G4"), intervals=SCALES["Major (Ionian)"])]
    ['G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F♯5']
    """
    return [tonic.transpose(iv) for iv in intervals]


def key_signature(
    tonic_name: str,
    *,
    scale: str = "Major (Ionian)",
) -> int:
    """
    Return the key signature of a scale as a signed count of accidentals.

    Parameters
    ----------
    tonic_name : str
        The tonic in plain text without an octave, such as 'G', 'Eb' or 'F#'.
    scale : str, default "Major (Ionian)"
        A key of `SCALES`. Keyword-only.

    Returns
    -------
    int
        The sum of the accidentals of the scale's notes: positive for sharps, negative for flats.

    Examples
    --------
    >>> key_signature("G")  # G major has one sharp
    1
    >>> key_signature("Eb")  # E♭ major has three flats
    -3
    >>> key_signature("A", scale="Natural minor (Aeolian)")  # A minor has none
    0
    """
    tonic = Note.parse(tonic_name + "4")
    notes = build(tonic, intervals=SCALES[scale])
    return sum(n.accidental for n in notes)


def format_key_signature(count: int) -> str:
    """
    Describe a key signature in words.

    Parameters
    ----------
    count : int
        Sharps (positive) or flats (negative).

    Returns
    -------
    str
        For example '1 sharp', '3 flats' or 'no sharps or flats'.

    Examples
    --------
    >>> format_key_signature(0)
    'no sharps or flats'
    >>> format_key_signature(1)
    '1 sharp'
    >>> format_key_signature(-3)
    '3 flats'
    """
    if count == 0:
        return "no sharps or flats"
    return f"{abs(count)} {'sharp' if count > 0 else 'flat'}{'s' if abs(count) != 1 else ''}"


def all_tonics(max_accidentals: int = 1) -> list[Note]:
    """
    Return every spelled tonic in octave 4, within a limit on accidentals.

    Parameters
    ----------
    max_accidentals : int, default 1
        The most sharps or flats a tonic may have, so 1 allows C♭ through B♯ but not double sharps.

    Returns
    -------
    list of Note
        Each letter with each accidental from `-max_accidentals` to `max_accidentals`, letters in the order C to B.

    Examples
    --------
    >>> len(all_tonics())
    21
    >>> [str(n) for n in all_tonics(0)]
    ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4']
    """
    return [Note(4, letter=letter, accidental=acc) for letter in range(7) for acc in range(-max_accidentals, max_accidentals + 1)]


__all__ = [
    "SCALES",
    "CHORDS",
    "MODE_DEGREE",
    "MODE_WORDS",
    "major_key_tonic",
    "mode_tonic",
    "INVERSION_NAMES",
    "arpeggio",
    "build",
    "key_signature",
    "format_key_signature",
    "all_tonics",
    "LETTERS",
]
