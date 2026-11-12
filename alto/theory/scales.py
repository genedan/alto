"""Scales, modes, key signatures and chords, built from spelled intervals."""
from __future__ import annotations

from .pitch import LETTERS, Interval, Note

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


INVERSION_NAMES = ("root position", "1st inversion", "2nd inversion", "3rd inversion")
OCTAVE = Interval(8, "P")


def arpeggio(root: Note, intervals: list[Interval], inversion: int = 0) -> list[Note]:
    """A chord broken and rising from its lowest note, then that note again an octave higher. `inversion` is how many of
    the lowest chord tones are moved up an octave first (0 = root position, 1 = the third at the bottom ...)."""
    tones = build(root, intervals)
    for _ in range(inversion):
        tones.append(tones.pop(0).transpose(OCTAVE))
    return tones + [tones[0].transpose(OCTAVE)]


def build(tonic: Note, intervals: list[Interval]) -> list[Note]:
    return [tonic.transpose(iv) for iv in intervals]


def key_signature(tonic_name: str, scale: str = "Major (Ionian)") -> int:
    """Signed accidental count: +n sharps, -n flats, for the given tonic + scale."""
    tonic = Note.parse(tonic_name + "4")
    notes = build(tonic, SCALES[scale])
    return sum(n.accidental for n in notes)


def format_key_signature(count: int) -> str:
    if count == 0:
        return "no sharps or flats"
    return f"{abs(count)} {'sharp' if count > 0 else 'flat'}{'s' if abs(count) != 1 else ''}"


def all_tonics(max_accidentals: int = 1) -> list[Note]:
    """Every spelled tonic (octave 4) with |accidental| <= max_accidentals."""
    return [
        Note(4, letter, acc)
        for letter in range(7)
        for acc in range(-max_accidentals, max_accidentals + 1)
    ]


__all__ = ["SCALES", "CHORDS", "INVERSION_NAMES", "arpeggio", "build", "key_signature", "format_key_signature", "all_tonics",
           "LETTERS"]
