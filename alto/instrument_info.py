"""What is known about each instrument's recordings, for the summary shown in the instrument settings.

The facts here come from the sources' own pages (the University of Iowa Musical Instrument Samples). What is on disk
(how many notes, their range, their size) is worked out when the page is shown, not stored here. Pure Python, no Qt.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .settings import key_name

IOWA = "University of Iowa Electronic Music Studios, Musical Instrument Samples"
IOWA_TERMS = "Freely available, and may be downloaded and used for any projects, without restrictions (the studio's statement)."
SYNTH = "Notes outside the recorded range are synthesized."


@dataclass(frozen=True)
class InstrumentInfo:
    summary: str  # one sentence on what the sound is
    source: str
    source_url: str
    performer: str = ""
    recorded: str = ""
    includes: str = ""  # the articulation and dynamic that were used
    terms: str = IOWA_TERMS
    note: str = ""  # anything a user should know about how Alto prepared it


INFO: dict[str, InstrumentInfo] = {
    "piano": InstrumentInfo(
        "A Steinway & Sons model B grand piano.",
        IOWA,
        "https://theremin.music.uiowa.edu/MISpiano.html",
        performer="Evan Mazunik",
        recorded="5 and 27 November 2001, Voxman Music Building, Neumann KM 84 microphones over the strings",
        includes="Mezzo-forte",
        note="Each note is trimmed to 2.5 seconds with a fade-out. " + SYNTH,
    ),
    "flute": InstrumentInfo(
        "A concert flute, played without vibrato.",
        IOWA,
        "https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISFlute2012.html",
        performer="Sonja Feig",
        recorded="April 2000, anechoic chamber, Neumann KM 84 microphone",
        includes="Without vibrato, fortissimo",
        note="Every semitone from B3 to C♯7 is recorded, so Alto does not have to borrow a neighbouring note. "
        "The highest notes are played a little sharp, up to about 45 cents (nearly half a semitone), as recorded.",
    ),
    "horn": InstrumentInfo(
        "A French horn.",
        IOWA,
        "https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISHorn2012.html",
        performer="Jessica Wiskus",
        recorded="27 July 1997, anechoic chamber, Neumann KM 84 microphone, 5 feet away",
        includes="Fortissimo",
        note="Every semitone from A♯1 to F5 is recorded, so Alto does not have to borrow a neighbouring note. "
        "The lowest notes are played a little flat, up to about 45 cents, as recorded.",
    ),
    "viola_bowed": InstrumentInfo(
        "A viola, bowed (arco).",
        IOWA,
        "https://theremin.music.uiowa.edu/MISviola2012.html",
        performer="Manuel Tabora, on a viola by Anton Krutz (2001)",
        recorded="11 May 2012, anechoic chamber, Earthworks QTC40 microphones",
        includes="Bowed (arco), mezzo-forte, on the C, G, D and A strings",
        note="Nearly every semitone is recorded, so Alto rarely has to borrow a neighbouring note. "
        "The source files declare 44.1 kHz but hold 96 kHz audio, so Alto reads them at 96 kHz.",
    ),
    "viola_plucked": InstrumentInfo(
        "A viola, plucked (pizzicato).",
        IOWA,
        "https://theremin.music.uiowa.edu/MISviola2012.html",
        performer="Manuel Tabora, on a viola by Anton Krutz (2001)",
        recorded="11 May 2012, anechoic chamber, Earthworks QTC40 microphones",
        includes="Plucked (pizzicato), fortissimo, on the C, D and A strings",
        note="The weakest and most ringing plucks were left out, so Alto shifts a neighbouring note for those. "
        "The source files declare 44.1 kHz but hold 96 kHz audio, so Alto reads them at 96 kHz.",
    ),
    "marimba": InstrumentInfo(
        "A marimba, struck with yarn mallets.",
        IOWA,
        "https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISMarimba2012.html",
        performer="Andrew Thierauf",
        recorded="20 March 2013, anechoic chamber, Earthworks QTC40 microphones",
        includes="Normal strokes with yarn mallets, fortissimo",
    ),
    "vibraphone": InstrumentInfo(
        "A vibraphone, with its sustain.",
        IOWA,
        "https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISVibraphone2012.html",
        performer="Andrew Thierauf",
        recorded="10 June 2013, anechoic chamber, Earthworks QTC40 microphones",
        includes="Sustain, fortissimo",
    ),
}


# What to say about an entry that groups several ways of playing the same instrument.
FAMILY_SUMMARY = {"Viola": "A viola, played bowed (arco) or plucked (pizzicato)."}


@dataclass(frozen=True)
class Coverage:
    """Which notes an instrument has recordings for."""

    count: int
    lowest: int | None = None
    highest: int | None = None
    gaps: int = 0  # semitones inside the range with no recording

    @property
    def installed(self) -> bool:
        return self.count > 0

    def describe(self) -> str:
        if self.lowest is None or self.highest is None:  # no notes installed
            return "None installed"
        text = f"{self.count} notes, {key_name(self.lowest)} to {key_name(self.highest)}"
        if self.gaps == 0:
            return text + ", every semitone"
        if self.gaps <= max(2, (self.highest - self.lowest + 1) // 10):
            return f"{text}, almost every semitone. The few missing notes are shifted from a neighbour."
        return f"{text}, about every second semitone. The other notes are shifted from a neighbour."


def coverage(midis: Iterable[int]) -> Coverage:
    """Summarise the notes that have a recording."""
    have = sorted(set(midis))
    if not have:
        return Coverage(0)
    return Coverage(len(have), have[0], have[-1], gaps=(have[-1] - have[0] + 1) - len(have))
