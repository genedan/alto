"""
Pitches and intervals, spelled correctly (C# is not Db).

A `Note` is a pitch with its spelling (a letter, an accidental and an octave), so C♯4 and D♭4 are different notes even
though they sound the same. An `Interval` is a distance between two spelled notes, such as a major third or a perfect
fifth. Together they can transpose a note by an interval and work out the interval between two notes.

Examples
--------
>>> c4 = Note.parse("C4")
>>> str(c4.transpose(Interval.parse("M3")))
'E4'
>>> Interval.between(c4, high=Note.parse("G4"))
Interval(number=5, quality='P')
"""

from __future__ import annotations

from dataclasses import (
    KW_ONLY,
    dataclass,
)

LETTERS = "CDEFGAB"
NATURAL_SEMITONES = (
    0,
    2,
    4,
    5,
    7,
    9,
    11,
)
ACCIDENTAL_SYMBOLS = {
    -2: "𝄫",
    -1: "♭",
    0: "",
    1: "♯",
    2: "𝄪",
}
_ASCII = {
    -2: "bb",
    -1: "b",
    0: "",
    1: "#",
    2: "x",
}

_MAJOR_BASE = (
    0,
    2,
    4,
    5,
    7,
    9,
    11,
)  # semitones above tonic for degrees 1-7
_PERFECT_DEGREES = (0, 3, 4)  # 1st, 4th, 5th


@dataclass(frozen=True, order=True)
class Note:
    """
    A spelled pitch: a letter name, an accidental and an octave.

    The spelling matters. C♯4 and D♭4 sound the same (they share a MIDI number) but are different notes, because they sit on
    different lines of the staff.

    Attributes
    ----------
    octave : int
        The octave in scientific pitch notation, where middle C is C4.
    letter : int
        An index into `LETTERS`: 0 is C, 1 is D, 2 is E, 3 is F, 4 is G, 5 is A and 6 is B. Keyword-only.
    accidental : int, default 0
        -2 for a double flat, -1 for a flat, 0 for a natural, 1 for a sharp and 2 for a double sharp. Keyword-only.

    Examples
    --------
    >>> middle_c = Note(4, letter=0)
    >>> middle_c.midi
    60
    >>> str(Note(4, letter=3, accidental=1))
    'F♯4'
    >>> Note(4, letter=0) < Note(4, letter=1)
    True
    """

    octave: int
    _: KW_ONLY
    letter: int
    accidental: int = 0

    @property
    def midi(self) -> int:
        """
        Return the MIDI note number, where middle C (C4) is 60.

        Returns
        -------
        int
            The number of semitones above C-1.

        Examples
        --------
        >>> Note(4, letter=0).midi
        60
        >>> Note(4, letter=1, accidental=-1).midi  # D♭4 sounds like C♯4
        61
        """
        return 12 * (self.octave + 1) + NATURAL_SEMITONES[self.letter] + self.accidental

    @property
    def diatonic(self) -> int:
        """
        Return the absolute staff-step index of the note, ignoring its accidental.

        Counting from C0 as 0, D0 as 1 and so on, each line or space of the staff is one step. The distance between two notes in
        staff steps is the difference of their indexes.

        Returns
        -------
        int
            `octave * 7 + letter`.

        Examples
        --------
        >>> Note(4, letter=0).diatonic  # C4
        28
        >>> Note(4, letter=2, accidental=1).diatonic  # E♯4 is on the same step as E4
        30
        """
        return self.octave * 7 + self.letter

    @property
    def pitch_class(self) -> int:
        """
        Return the pitch class: the note's MIDI number modulo 12.

        Returns
        -------
        int
            A number from 0 (C) to 11 (B), the same for every octave and for enharmonic spellings.

        Examples
        --------
        >>> Note(4, letter=0, accidental=1).pitch_class  # C♯4
        1
        >>> Note(3, letter=6, accidental=1).pitch_class  # B♯3 sounds like C
        0
        """
        return self.midi % 12

    @property
    def name(self) -> str:
        """
        Return the pitch-class name with Unicode accidentals, without the octave.

        Returns
        -------
        str
            The letter followed by ♭, ♯, 𝄫 or 𝄪 where the note has an accidental.

        Examples
        --------
        >>> Note(4, letter=3, accidental=1).name
        'F♯'
        >>> Note(4, letter=3).name
        'F'
        """
        return LETTERS[self.letter] + ACCIDENTAL_SYMBOLS[self.accidental]

    def __str__(self) -> str:
        """
        Return the name with its octave, for display.

        Returns
        -------
        str
            For example 'F♯4'.

        Examples
        --------
        >>> str(Note(2, letter=6, accidental=-1))
        'B♭2'
        """
        return f"{self.name}{self.octave}"

    @classmethod
    def from_diatonic(
        cls,
        diatonic: int,
        *,
        accidental: int = 0,
    ) -> Note:
        """
        Build a note from an absolute staff-step index.

        Parameters
        ----------
        diatonic : int
            The index, counting C0 as 0 (see `Note.diatonic`).
        accidental : int, default 0
            The accidental to give the note. Keyword-only.

        Returns
        -------
        Note
            The note on that staff step with that accidental.

        Examples
        --------
        >>> Note.from_diatonic(30)
        Note(octave=4, letter=2, accidental=0)
        >>> str(Note.from_diatonic(30, accidental=-1))
        'E♭4'
        """
        return cls(diatonic // 7, letter=diatonic % 7, accidental=accidental)

    @classmethod
    def parse(cls, text: str) -> Note:
        """
        Parse a note written in plain text, such as 'F#4', 'Bb3' or 'Ebb2'.

        Parameters
        ----------
        text : str
            A letter A-G (either case), then an accidental ('#' for a sharp, 'b' for a flat, 'bb' for a double flat, 'x' for a
            double sharp, or nothing for a natural), then the octave number.

        Returns
        -------
        Note
            The spelled note.

        Raises
        ------
        ValueError
            If the letter is not A-G, or the octave is missing.
        KeyError
            If the accidental is not one of '', '#', 'b', 'bb' or 'x'.

        Examples
        --------
        >>> Note.parse("F#4")
        Note(octave=4, letter=3, accidental=1)
        >>> Note.parse("Bb3")
        Note(octave=3, letter=6, accidental=-1)
        >>> Note.parse("H4")
        Traceback (most recent call last):
            ...
        ValueError: substring not found
        """
        letter = LETTERS.index(text[0].upper())
        rest = text[1:]
        octave = int(rest.lstrip("#bx"))
        acc_text = rest[: len(rest) - len(str(octave))]
        acc = {v: k for k, v in _ASCII.items()}[acc_text]
        return cls(octave, letter=letter, accidental=acc)

    def transpose(
        self,
        interval: Interval,
        *,
        descending: bool = False,
    ) -> Note:
        """
        Move the note up or down by an interval, keeping the spelling correct.

        Parameters
        ----------
        interval : Interval
            How far to move. Its number decides the letter and its quality decides the accidental.
        descending : bool, default False
            Move down instead of up. Keyword-only.

        Returns
        -------
        Note
            The new note. For example a major third above C is E, and a minor third above C is E♭, never D♯.

        Examples
        --------
        >>> str(Note.parse("C4").transpose(Interval.parse("M3")))
        'E4'
        >>> str(Note.parse("C4").transpose(Interval.parse("m3")))
        'E♭4'
        >>> str(Note.parse("C4").transpose(Interval.parse("P5"), descending=True))
        'F3'
        """
        steps = interval.number - 1
        d = self.diatonic + (-steps if descending else steps)
        semis = interval.semitones
        target_midi = self.midi + (-semis if descending else semis)
        letter = d % 7
        natural = 12 * (d // 7 + 1) + NATURAL_SEMITONES[letter]
        return Note(d // 7, letter=letter, accidental=target_midi - natural)


@dataclass(frozen=True)
class Interval:
    """
    A simple or compound interval between two spelled notes.

    Attributes
    ----------
    number : int
        The size counting both end notes: 1 is a unison, 3 a third, 8 an octave, 9 a ninth and so on.
    quality : str
        One of 'dd' (doubly diminished), 'd' (diminished), 'm' (minor), 'M' (major), 'P' (perfect), 'A' (augmented) and
        'AA' (doubly augmented). Keyword-only. Unisons, fourths, fifths and octaves are perfect, the others major or minor.

    Examples
    --------
    >>> Interval(3, quality="M").semitones
    4
    >>> str(Interval.parse("P5"))
    'P5'
    """

    number: int
    _: KW_ONLY
    quality: str  # one of "dd d m M P A AA"

    @property
    def _degree(self) -> int:
        """
        Return the scale degree the interval spans within one octave, counting from 0.

        Returns
        -------
        int
            `(number - 1) % 7`: 0 for a unison or octave, 1 for a second or ninth, up to 6 for a seventh.

        Examples
        --------
        >>> Interval.parse("M9")._degree
        1
        """
        return (self.number - 1) % 7

    @property
    def is_perfect_type(self) -> bool:
        """
        Report whether this size of interval is "perfect type" (unison, fourth, fifth, octave) rather than major or minor type.

        Returns
        -------
        bool
            True for unisons, fourths, fifths and octaves (and their compounds), False for seconds, thirds, sixths and sevenths.

        Examples
        --------
        >>> Interval.parse("P5").is_perfect_type
        True
        >>> Interval.parse("M3").is_perfect_type
        False
        """
        return self._degree in _PERFECT_DEGREES

    @property
    def semitones(self) -> int:
        """
        Return the size of the interval in semitones.

        Returns
        -------
        int
            The distance in half steps, including whole octaves for compound intervals.

        Examples
        --------
        >>> Interval.parse("M3").semitones
        4
        >>> Interval.parse("d5").semitones
        6
        >>> Interval.parse("m9").semitones  # a minor ninth is an octave plus a minor second
        13
        """
        base = _MAJOR_BASE[self._degree] + 12 * ((self.number - 1) // 7)
        offsets = (
            {
                "dd": -2,
                "d": -1,
                "P": 0,
                "A": 1,
                "AA": 2,
            }
            if self.is_perfect_type
            else {
                "dd": -3,
                "d": -2,
                "m": -1,
                "M": 0,
                "A": 1,
                "AA": 2,
            }
        )
        return base + offsets[self.quality]

    @property
    def short(self) -> str:
        """
        Return the interval in short form: its quality followed by its number.

        Returns
        -------
        str
            For example 'M3', 'P5' or 'd7'.

        Examples
        --------
        >>> Interval(7, quality="m").short
        'm7'
        """
        return f"{self.quality}{self.number}"

    def __str__(self) -> str:
        """
        Return the interval in short form, for display.

        Returns
        -------
        str
            The same as `Interval.short`.

        Examples
        --------
        >>> str(Interval(5, quality="P"))
        'P5'
        """
        return self.short

    @classmethod
    def between(
        cls,
        low: Note,
        *,
        high: Note,
    ) -> Interval:
        """
        Work out the interval from one note up to a higher one.

        Parameters
        ----------
        low : Note
            The lower note.
        high : Note
            The higher note. It must not be below `low`. Keyword-only.

        Returns
        -------
        Interval
            The spelled interval, such as a major third (C4 up to E4) or an augmented fourth (C4 up to F♯4).

        Examples
        --------
        >>> Interval.between(Note.parse("C4"), high=Note.parse("E4"))
        Interval(number=3, quality='M')
        >>> Interval.between(Note.parse("C4"), high=Note.parse("F#4")).short
        'A4'
        """
        number = high.diatonic - low.diatonic + 1
        semis = high.midi - low.midi
        base = _MAJOR_BASE[(number - 1) % 7] + 12 * ((number - 1) // 7)
        diff = semis - base
        if (number - 1) % 7 in _PERFECT_DEGREES:
            table = {
                -2: "dd",
                -1: "d",
                0: "P",
                1: "A",
                2: "AA",
            }
        else:
            table = {
                -3: "dd",
                -2: "d",
                -1: "m",
                0: "M",
                1: "A",
                2: "AA",
            }
        return cls(number, quality=table[diff])

    @classmethod
    def parse(cls, text: str) -> Interval:
        """
        Parse an interval written in short form, such as 'M3', 'P5' or 'd7'.

        Parameters
        ----------
        text : str
            The quality (one of dd, d, m, M, P, A, AA) followed by the number.

        Returns
        -------
        Interval
            The interval.

        Examples
        --------
        >>> Interval.parse("m7")
        Interval(number=7, quality='m')
        >>> Interval.parse("P8").semitones
        12
        """
        quality = text.rstrip("0123456789")
        return cls(int(text[len(quality) :]), quality=quality)


QUALITY_NAMES = {
    "dd": "doubly diminished",
    "d": "diminished",
    "m": "minor",
    "M": "major",
    "P": "perfect",
    "A": "augmented",
    "AA": "doubly augmented",
}


# Key signatures: count > 0 is that many sharps, count < 0 that many flats.
SHARP_ORDER = (
    3,
    0,
    4,
    1,
    5,
    2,
    6,
)  # letter indexes: F C G D A E B
FLAT_ORDER = (
    6,
    2,
    5,
    1,
    4,
    0,
    3,
)  # B E A D G C F
MAJOR_KEYS = {
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F♯",
    7: "C♯",
    -1: "F",
    -2: "B♭",
    -3: "E♭",
    -4: "A♭",
    -5: "D♭",
    -6: "G♭",
    -7: "C♭",
}


def key_accidental(
    letter: int,
    *,
    count: int,
) -> int:
    """
    Return the accidental a key signature applies to a letter.

    Parameters
    ----------
    letter : int
        An index into `LETTERS` (0 is C, 6 is B).
    count : int
        The key signature: that many sharps if positive, that many flats if negative. Keyword-only.

    Returns
    -------
    int
        1 if the signature sharpens the letter, -1 if it flattens it, 0 if it leaves it natural.

    Examples
    --------
    >>> key_accidental(3, count=1)  # F in G major
    1
    >>> key_accidental(6, count=-1)  # B in F major
    -1
    >>> key_accidental(0, count=1)  # C in G major
    0
    """
    if count > 0 and letter in SHARP_ORDER[:count]:
        return 1
    if count < 0 and letter in FLAT_ORDER[:-count]:
        return -1
    return 0
