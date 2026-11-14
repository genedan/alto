"""
What is known about each instrument's recordings, for the summary shown in the instrument settings.

The facts here come from the sources' own pages (the University of Iowa Musical Instrument Samples, and the Salamander
Grand Piano). What is on disk
(how many notes, their range, their size) is worked out when the page is shown, not stored here. Pure Python, no Qt.

Examples
--------
>>> coverage(range(60, 73)).describe()
'13 notes, C4 to C5, every semitone'
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import (
    KW_ONLY,
    dataclass,
)

from alto.settings import key_name

IOWA = "University of Iowa Electronic Music Studios, Musical Instrument Samples"
IOWA_TERMS = "Freely available, and may be downloaded and used for any projects, without restrictions (the studio's statement)."
SALAMANDER = "Salamander Grand Piano V3, by Alexander Holm"
SALAMANDER_TERMS = "Creative Commons Attribution 3.0 (CC BY 3.0): free to use with credit to the author."
SYNTH = "Notes outside the recorded range are synthesized."


@dataclass(frozen=True)
class InstrumentInfo:
    """
    The facts about where an instrument's recordings came from.

    Attributes
    ----------
    summary : str
        One sentence on what the sound is.
    source : str
        Who made the recordings. Keyword-only.
    source_url : str
        Where the source describes them. Keyword-only.
    performer : str, default ""
        Who played. Keyword-only.
    recorded : str, default ""
        When and where it was recorded. Keyword-only.
    includes : str, default ""
        The articulation and dynamic that were used. Keyword-only.
    terms : str
        The terms the recordings may be used under. Keyword-only.
    note : str, default ""
        Anything a user should know about how Alto prepared the recordings. Keyword-only.

    Examples
    --------
    >>> info = InstrumentInfo("A flute.", source=IOWA, source_url="https://example.org/flute")
    >>> info.terms == IOWA_TERMS
    True
    """

    summary: str  # one sentence on what the sound is
    _: KW_ONLY
    source: str
    source_url: str
    performer: str = ""
    recorded: str = ""
    includes: str = ""  # the articulation and dynamic that were used
    terms: str = IOWA_TERMS
    note: str = ""  # anything a user should know about how Alto prepared it


INFO: dict[str, InstrumentInfo] = {
    "piano": InstrumentInfo(
        "A Yamaha C5 grand piano.",
        source=SALAMANDER,
        source_url="https://sfzinstruments.github.io/pianos/salamander",
        performer="Alexander Holm",
        recorded="Two AKG C414 microphones in an AB position, about 12 cm above the strings",
        includes="Medium dynamic (layer 8 of 16), a recording every minor third from A0 to C8",
        terms=SALAMANDER_TERMS,
        note="Each note is trimmed to 2.5 seconds with a fade-out. The notes between the recordings are shifted from a "
        "neighbour by at most a semitone. The highest notes are a little sharp, up to about 60 cents at C8, as in a "
        "real piano's stretch tuning. Notes outside A0 to C8 are synthesized.",
    ),
    "flute": InstrumentInfo(
        "A concert flute, played without vibrato.",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISFlute2012.html",
        performer="Sonja Feig",
        recorded="April 2000, anechoic chamber, Neumann KM 84 microphone",
        includes="Without vibrato, fortissimo",
        note="Every semitone from B3 to C♯7 is recorded, so Alto does not have to borrow a neighbouring note. "
        "The highest notes are played a little sharp, up to about 45 cents (nearly half a semitone), as recorded.",
    ),
    "horn": InstrumentInfo(
        "A French horn.",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISHorn2012.html",
        performer="Jessica Wiskus",
        recorded="27 July 1997, anechoic chamber, Neumann KM 84 microphone, 5 feet away",
        includes="Fortissimo",
        note="Every semitone from A♯1 to F5 is recorded, so Alto does not have to borrow a neighbouring note. "
        "The lowest notes are played a little flat, up to about 45 cents, as recorded.",
    ),
    "viola_bowed": InstrumentInfo(
        "A viola, bowed (arco).",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MISviola2012.html",
        performer="Manuel Tabora, on a viola by Anton Krutz (2001)",
        recorded="11 May 2012, anechoic chamber, Earthworks QTC40 microphones",
        includes="Bowed (arco), mezzo-forte, on the C, G, D and A strings",
        note="Nearly every semitone is recorded, so Alto rarely has to borrow a neighbouring note. "
        "The source files declare 44.1 kHz but hold 96 kHz audio, so Alto reads them at 96 kHz.",
    ),
    "viola_plucked": InstrumentInfo(
        "A viola, plucked (pizzicato).",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MISviola2012.html",
        performer="Manuel Tabora, on a viola by Anton Krutz (2001)",
        recorded="11 May 2012, anechoic chamber, Earthworks QTC40 microphones",
        includes="Plucked (pizzicato), fortissimo, on the C, D and A strings",
        note="The weakest and most ringing plucks were left out, so Alto shifts a neighbouring note for those. "
        "The source files declare 44.1 kHz but hold 96 kHz audio, so Alto reads them at 96 kHz.",
    ),
    "marimba": InstrumentInfo(
        "A marimba, struck with yarn mallets.",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISMarimba2012.html",
        performer="Andrew Thierauf",
        recorded="20 March 2013, anechoic chamber, Earthworks QTC40 microphones",
        includes="Normal strokes with yarn mallets, fortissimo",
    ),
    "vibraphone": InstrumentInfo(
        "A vibraphone, with its sustain.",
        source=IOWA,
        source_url="https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISVibraphone2012.html",
        performer="Andrew Thierauf",
        recorded="10 June 2013, anechoic chamber, Earthworks QTC40 microphones",
        includes="Sustain, fortissimo",
    ),
}


# What to say about an entry that groups several ways of playing the same instrument.
FAMILY_SUMMARY = {"Viola": "A viola, played bowed (arco) or plucked (pizzicato)."}


@dataclass(frozen=True)
class Coverage:
    """
    Which notes an instrument has recordings for.

    Attributes
    ----------
    count : int
        How many notes have a recording.
    lowest : int or None
        The lowest recorded note, as a MIDI number. Keyword-only.
    highest : int or None
        The highest recorded note, as a MIDI number. Keyword-only.
    gaps : int, default 0
        How many semitones inside the range have no recording. Keyword-only.

    Examples
    --------
    >>> Coverage(0).describe()
    'None installed'
    """

    count: int
    _: KW_ONLY
    lowest: int | None = None
    highest: int | None = None
    gaps: int = 0  # semitones inside the range with no recording

    @property
    def installed(self) -> bool:
        """
        Report whether any recordings are on disk.

        Returns
        -------
        bool
            True if at least one note has a recording.

        Examples
        --------
        >>> Coverage(0).installed, coverage([60]).installed
        (False, True)
        """
        return self.count > 0

    def describe(self) -> str:
        """
        Describe the coverage in a sentence for the instrument settings.

        Returns
        -------
        str
            The number of notes, the range, and how complete it is (the spacing, when the notes are well apart). Missing notes
            are shifted from a neighbour.

        Examples
        --------
        >>> coverage(range(60, 73)).describe()
        '13 notes, C4 to C5, every semitone'
        >>> coverage([60, 62, 64, 65]).describe()
        '4 notes, C4 to F4, almost every semitone. The few missing notes are shifted from a neighbour.'
        >>> coverage(range(48, 73, 2)).describe()
        '13 notes, C3 to C5, about every second semitone. The other notes are shifted from a neighbour.'
        >>> coverage(range(21, 109, 3)).describe()
        '30 notes, A0 to C8, about every third semitone. The other notes are shifted from a neighbour.'
        """
        if self.lowest is None or self.highest is None:  # no notes installed
            return "None installed"
        text = f"{self.count} notes, {key_name(self.lowest)} to {key_name(self.highest)}"
        if self.gaps == 0:
            return text + ", every semitone"
        if self.gaps <= max(2, (self.highest - self.lowest + 1) // 10):
            return f"{text}, almost every semitone. The few missing notes are shifted from a neighbour."
        step = round((self.highest - self.lowest) / (self.count - 1))
        spacing = {2: "second", 3: "third", 4: "fourth"}.get(step, f"{step}th")
        return f"{text}, about every {spacing} semitone. The other notes are shifted from a neighbour."


def coverage(midis: Iterable[int]) -> Coverage:
    """
    Summarise the notes that have a recording.

    Parameters
    ----------
    midis : iterable of int
        The MIDI numbers of the recorded notes, in any order and with repeats allowed.

    Returns
    -------
    Coverage
        The count, the range and the number of gaps.

    Examples
    --------
    >>> coverage([64, 60, 62])
    Coverage(count=3, lowest=60, highest=64, gaps=2)
    """
    have = sorted(set(midis))
    if not have:
        return Coverage(0)
    return Coverage(
        len(have),
        lowest=have[0],
        highest=have[-1],
        gaps=(have[-1] - have[0] + 1) - len(have),
    )
