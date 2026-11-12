"""Pitches and intervals, spelled correctly (C# is not Db)."""
from __future__ import annotations

from dataclasses import dataclass

LETTERS = "CDEFGAB"
NATURAL_SEMITONES = (0, 2, 4, 5, 7, 9, 11)
ACCIDENTAL_SYMBOLS = {-2: "𝄫", -1: "♭", 0: "", 1: "♯", 2: "𝄪"}
_ASCII = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "x"}

_MAJOR_BASE = (0, 2, 4, 5, 7, 9, 11)  # semitones above tonic for degrees 1-7
_PERFECT_DEGREES = (0, 3, 4)  # 1st, 4th, 5th


@dataclass(frozen=True, order=True)
class Note:
    """A spelled pitch. `letter` is an index into LETTERS."""

    octave: int
    letter: int
    accidental: int = 0

    @property
    def midi(self) -> int:
        return 12 * (self.octave + 1) + NATURAL_SEMITONES[self.letter] + self.accidental

    @property
    def diatonic(self) -> int:
        """Absolute staff-step index (C0 = 0, D0 = 1, ...)."""
        return self.octave * 7 + self.letter

    @property
    def pitch_class(self) -> int:
        return self.midi % 12

    @property
    def name(self) -> str:
        """Pitch-class name with unicode accidentals, e.g. 'F♯'."""
        return LETTERS[self.letter] + ACCIDENTAL_SYMBOLS[self.accidental]

    def __str__(self) -> str:
        return f"{self.name}{self.octave}"

    @classmethod
    def from_diatonic(cls, diatonic: int, accidental: int = 0) -> Note:
        return cls(diatonic // 7, diatonic % 7, accidental)

    @classmethod
    def parse(cls, text: str) -> Note:
        """Parse e.g. 'F#4', 'Bb3', 'Ebb2'."""
        letter = LETTERS.index(text[0].upper())
        rest = text[1:]
        octave = int(rest.lstrip("#bx"))
        acc_text = rest[: len(rest) - len(str(octave))]
        acc = {v: k for k, v in _ASCII.items()}[acc_text]
        return cls(octave, letter, acc)

    def transpose(self, interval: Interval, descending: bool = False) -> Note:
        steps = interval.number - 1
        d = self.diatonic + (-steps if descending else steps)
        semis = interval.semitones
        target_midi = self.midi + (-semis if descending else semis)
        letter = d % 7
        natural = 12 * (d // 7 + 1) + NATURAL_SEMITONES[letter]
        return Note(d // 7, letter, target_midi - natural)


@dataclass(frozen=True)
class Interval:
    """A simple or compound interval. number: 1=unison, 8=octave, 9=ninth..."""

    number: int
    quality: str  # one of "dd d m M P A AA"

    @property
    def _degree(self) -> int:
        return (self.number - 1) % 7

    @property
    def is_perfect_type(self) -> bool:
        return self._degree in _PERFECT_DEGREES

    @property
    def semitones(self) -> int:
        base = _MAJOR_BASE[self._degree] + 12 * ((self.number - 1) // 7)
        offsets = (
            {"dd": -2, "d": -1, "P": 0, "A": 1, "AA": 2}
            if self.is_perfect_type
            else {"dd": -3, "d": -2, "m": -1, "M": 0, "A": 1, "AA": 2}
        )
        return base + offsets[self.quality]

    @property
    def short(self) -> str:
        return f"{self.quality}{self.number}"

    def __str__(self) -> str:
        return self.short

    @classmethod
    def between(cls, low: Note, high: Note) -> Interval:
        """Interval from `low` up to `high` (low must not be above high)."""
        number = high.diatonic - low.diatonic + 1
        semis = high.midi - low.midi
        base = _MAJOR_BASE[(number - 1) % 7] + 12 * ((number - 1) // 7)
        diff = semis - base
        if (number - 1) % 7 in _PERFECT_DEGREES:
            table = {-2: "dd", -1: "d", 0: "P", 1: "A", 2: "AA"}
        else:
            table = {-3: "dd", -2: "d", -1: "m", 0: "M", 1: "A", 2: "AA"}
        return cls(number, table[diff])

    @classmethod
    def parse(cls, text: str) -> Interval:
        quality = text.rstrip("0123456789")
        return cls(int(text[len(quality):]), quality)


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
SHARP_ORDER = (3, 0, 4, 1, 5, 2, 6)  # letter indexes: F C G D A E B
FLAT_ORDER = (6, 2, 5, 1, 4, 0, 3)   # B E A D G C F
MAJOR_KEYS = {0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F♯", 7: "C♯",
              -1: "F", -2: "B♭", -3: "E♭", -4: "A♭", -5: "D♭", -6: "G♭", -7: "C♭"}


def key_accidental(letter: int, count: int) -> int:
    """Accidental the key signature `count` applies to `letter` (index into LETTERS)."""
    if count > 0 and letter in SHARP_ORDER[:count]:
        return 1
    if count < 0 and letter in FLAT_ORDER[:-count]:
        return -1
    return 0
