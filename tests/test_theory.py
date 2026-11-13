"""Music theory: notes, intervals, scales, chords and key signatures."""

import pytest

from alto.theory.pitch import (
    Interval,
    Note,
)
from alto.theory.scales import (
    CHORDS,
    SCALES,
    build,
    key_signature,
)


def test_parse_and_midi() -> None:
    """
    Test parse and midi.
    """
    assert Note.parse("C4").midi == 60
    assert Note.parse("A4").midi == 69
    assert Note.parse("Bb3").midi == 58
    assert str(Note.parse("F#5")) == "F♯5"


@pytest.mark.parametrize(
    "low,high,expected",
    [
        ("C4", "E4", "M3"),
        ("C4", "Eb4", "m3"),
        ("C4", "G4", "P5"),
        ("C4", "F#4", "A4"),
        ("C4", "Gb4", "d5"),
        ("C4", "C5", "P8"),
        ("E4", "C5", "m6"),
        ("B3", "F4", "d5"),
        ("C4", "B#4", "A7"),
    ],
)
def test_between(
    low: str,
    high: str,
    expected: str,
) -> None:
    """
    Test between.

    Parameters
    ----------
    low : str
        The lower note.
    high : str
        The upper note.
    expected : str
        The expected result.
    """
    assert str(Interval.between(Note.parse(low), high=Note.parse(high))) == expected


def test_transpose_roundtrip() -> None:
    """
    Test transpose roundtrip.
    """
    for tonic in (
        "C4",
        "F#4",
        "Eb4",
        "Bb3",
    ):
        for iv in (
            "m2",
            "M3",
            "P4",
            "A4",
            "d5",
            "m6",
            "M7",
            "P8",
        ):
            n = Note.parse(tonic)
            up = n.transpose(Interval.parse(iv))
            assert Interval.between(n, high=up) == Interval.parse(iv)


def test_scales() -> None:
    """
    Test scales.
    """
    notes = build(Note.parse("D4"), intervals=SCALES["Major (Ionian)"])
    assert [n.name for n in notes] == [
        "D",
        "E",
        "F♯",
        "G",
        "A",
        "B",
        "C♯",
    ]
    notes = build(Note.parse("A4"), intervals=SCALES["Harmonic minor"])
    assert [n.name for n in notes] == [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G♯",
    ]


def test_key_signatures() -> None:
    """
    Test key signatures.
    """
    assert key_signature("C") == 0
    assert key_signature("G") == 1
    assert key_signature("Eb") == -3
    assert key_signature("F#") == 6
    assert key_signature("A", scale="Natural minor (Aeolian)") == 0


def test_chords() -> None:
    """
    Test chords.
    """
    notes = build(Note.parse("C4"), intervals=CHORDS["dominant 7th"])
    assert [n.name for n in notes] == [
        "C",
        "E",
        "G",
        "B♭",
    ]
    notes = build(Note.parse("B3"), intervals=CHORDS["diminished 7th"])
    assert [n.name for n in notes] == [
        "B",
        "D",
        "F",
        "A♭",
    ]
