"""
Note playback: recorded instrument samples (University of Iowa), with pitch-shifting for missing notes.

`Sounds` plays notes through Qt's `QSoundEffect`, one effect per note, created the first time it is needed. A note with
no recording is made by shifting the nearest recording (or, for the piano outside its sampled range, by synthesis).
The module-level `sounds` is the one the interface uses.

Examples
--------
>>> [inst.label for inst in INSTRUMENTS][:2]
['Piano', 'Flute']
>>> Sounds().instrument
'piano'
"""

from __future__ import annotations

import io
import tempfile
import time
import wave
from collections.abc import (
    Iterable,
    Sequence,
)
from dataclasses import (
    KW_ONLY,
    dataclass,
)
from pathlib import Path

import numpy as np
from PySide6.QtCore import (
    QPropertyAnimation,
    QTimer,
    QUrl,
)
from PySide6.QtMultimedia import QSoundEffect

from alto.theory.pitch import Note

SAMPLE_RATE = 44100


def synth_piano(
    midi: int,
    *,
    duration: float = 1.6,
) -> np.ndarray:
    """
    Synthesize a piano note, for notes outside the recorded range.

    An additive model: stretched partials, a decay for each partial, a detuned string pair, and a hammer thump.

    Parameters
    ----------
    midi : int
        The MIDI note number. The same number always gives the same sound.
    duration : float, default 1.6
        How long the note lasts, in seconds. Keyword-only.

    Returns
    -------
    numpy.ndarray
        Mono samples at `SAMPLE_RATE`, scaled so the loudest is 0.8.

    Examples
    --------
    >>> samples = synth_piano(60, duration=0.1)
    >>> len(samples)
    4410
    >>> round(float(np.max(np.abs(samples))), 1)
    0.8
    """
    rng = np.random.default_rng(midi)  # deterministic per note
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
    inharm = 0.00008 * (1 + max(0, 60 - midi) / 24) ** 2 if midi < 60 else 0.0002 * (midi - 55) / 10
    out = np.zeros_like(t)
    for n in range(1, 17):
        f = n * f0 * np.sqrt(1 + inharm * n * n)
        if f > 12000:
            break
        amp = 1.0 / n**1.15
        if n % 7 == 0:  # strike-point comb: hammer hits ~1/7 along the string
            amp *= 0.3
        decay = 2.2 + 1.1 * n + (midi - 60) * 0.03  # higher partials/notes die faster
        # two slightly detuned strings give the characteristic shimmer
        for detune in (-0.0008, 0.0008):
            out += amp * 0.5 * np.sin(2 * np.pi * f * (1 + detune) * t + rng.uniform(0, 2 * np.pi)) * np.exp(-decay * t)
    # soft attack, then a quick dip into the long sustain
    out *= 1 - np.exp(-t / 0.002)
    out *= 0.65 + 0.35 * np.exp(-t / 0.25)
    # hammer thump: very short band-limited noise burst
    n_th = int(0.02 * SAMPLE_RATE)
    thump = rng.standard_normal(n_th)
    # noinspection PyTypeChecker
    thump = np.convolve(thump, np.ones(24) / 24, mode="same") * np.exp(-np.arange(n_th) / (0.004 * SAMPLE_RATE))
    out[:n_th] += 0.25 * thump * (1.0 / (1 + (midi - 40) / 30))
    out *= np.minimum(1.0, (duration - t) / 0.05)  # fade out to avoid a click
    return out / np.max(np.abs(out)) * 0.8


@dataclass(frozen=True)
class Instrument:
    """
    An instrument that notes can be played on, and where its recordings are.

    Attributes
    ----------
    key : str
        A short identifier used in settings and file names.
    label : str
        The name shown in the interface. Keyword-only.
    folder : str
        Under `assets/`: "piano" or "samples/<key>". File names are MIDI note numbers. Keyword-only.
    gain : float, default 1.0
        The level relative to the piano. Keyword-only.
    sustained : bool, default False
        True for bowed and blown instruments, whose notes end when the next one begins; struck and plucked ones ring on.
        Keyword-only.
    family : str, default ""
        Instruments that are ways of playing the same instrument share a family (the viola: arco and pizzicato).
        Keyword-only.
    variant : str, default ""
        Which way of playing it, within the family. Keyword-only.

    Examples
    --------
    >>> Instrument("flute", label="Flute", folder="samples/flute", sustained=True).gain
    1.0
    """

    key: str
    _: KW_ONLY
    label: str
    folder: str  # under assets/: "piano" or "samples/<key>"; file names are MIDI note numbers
    gain: float = 1.0  # level relative to the piano
    sustained: bool = False  # bowed and blown notes end when the next one begins; struck and plucked ones ring on
    family: str = ""  # instruments that are ways of playing the same instrument share a family (the viola: arco, pizzicato)
    variant: str = ""  # which way of playing it, within the family


INSTRUMENTS = (
    Instrument("piano", label="Piano", folder="piano"),
    Instrument(
        "flute",
        label="Flute",
        folder="samples/flute",
        gain=0.85,
        sustained=True,
    ),
    Instrument(
        "horn",
        label="French Horn",
        folder="samples/horn",
        gain=0.85,
        sustained=True,
    ),
    Instrument(
        "viola_bowed",
        label="Viola (Arco)",
        folder="samples/viola_bowed",
        gain=0.85,
        sustained=True,
        family="Viola",
        variant="Arco",
    ),
    Instrument(
        "viola_plucked",
        label="Viola (Pizzicato)",
        folder="samples/viola_plucked",
        gain=0.85,
        family="Viola",
        variant="Pizzicato",
    ),
    Instrument(
        "marimba",
        label="Marimba",
        folder="samples/marimba",
        gain=0.85,
    ),
    Instrument(
        "vibraphone",
        label="Vibraphone",
        folder="samples/vibraphone",
        gain=0.85,
    ),
)
INSTRUMENT_BY_KEY = {i.key: i for i in INSTRUMENTS}


def instrument_groups() -> list[tuple[str, list[Instrument]]]:
    """
    Return the instruments as they are listed for choosing.

    Ways of playing one instrument share a single entry.

    Returns
    -------
    list of tuple of (str, list of Instrument)
        Each entry's name (the family, or the instrument's own label) and its instruments, in the order listed.

    Examples
    --------
    >>> [name for name, _ in instrument_groups()]
    ['Piano', 'Flute', 'French Horn', 'Viola', 'Marimba', 'Vibraphone']
    >>> [inst_.variant for inst_ in dict(instrument_groups())["Viola"]]
    ['Arco', 'Pizzicato']
    """
    groups: dict[str, list[Instrument]] = {}
    for inst in INSTRUMENTS:
        groups.setdefault(inst.family or inst.label, []).append(inst)
    return list(groups.items())


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """
    Read a mono 16-bit WAV file.

    Parameters
    ----------
    path : Path
        The file.

    Returns
    -------
    tuple of (numpy.ndarray, int)
        The samples as floats from -1 to 1, and the sample rate in hertz.

    Examples
    --------
    >>> import tempfile
    >>> path_ = Path(tempfile.mkdtemp()) / "silence.wav"
    >>> _ = path_.write_bytes(to_wav_bytes(np.zeros(10)))
    >>> samples, rate = read_wav(path_)
    >>> len(samples), rate
    (10, 44100)
    """
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768, w.getframerate()


def shift_pitch(
    samples: np.ndarray,
    *,
    semitones: float,
) -> np.ndarray:
    """
    Change the pitch of samples by resampling them.

    It also changes the length, which is fine for a few semitones.

    Parameters
    ----------
    samples : numpy.ndarray
        Mono samples.
    semitones : float
        How far to shift; positive is higher. Keyword-only.

    Returns
    -------
    numpy.ndarray
        The resampled samples, shorter when shifted up and longer when shifted down.

    Examples
    --------
    >>> len(shift_pitch(np.zeros(100), semitones=12))  # an octave up: half as long
    50
    """
    ratio = 2 ** (semitones / 12)
    positions = np.arange(0, len(samples) - 1, ratio)
    return np.interp(positions, np.arange(len(samples)), samples)


def to_wav_bytes(
    samples: np.ndarray,
    *,
    rate: int = SAMPLE_RATE,
) -> bytes:
    """
    Encode samples as a mono 16-bit WAV file in memory.

    Parameters
    ----------
    samples : numpy.ndarray
        Mono samples from -1 to 1.
    rate : int, default SAMPLE_RATE
        The sample rate in hertz. Keyword-only.

    Returns
    -------
    bytes
        The contents of a WAV file.

    Examples
    --------
    >>> to_wav_bytes(np.zeros(10))[:4]
    b'RIFF'
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((samples * 32767).astype("<i2").tobytes())
    return buf.getvalue()


ASSETS = Path(__file__).parent / "assets"
ASSET_DIR = ASSETS / "piano"


class Sounds:
    """
    A lazy cache of notes played through `QSoundEffect`, in the chosen instrument.

    Attributes
    ----------
    enabled : bool
        False while the app is muted.
    instrument : str
        The key of the instrument in use, a key of `INSTRUMENT_BY_KEY`.
    FADE_MS : int
        How quickly a sustained note dies away when the next one begins, in milliseconds.

    Examples
    --------
    >>> s = Sounds()
    >>> s.enabled, s.instrument
    (True, 'piano')
    >>> s.enabled = False  # muted: nothing below makes a sound
    >>> s.play_midi(60)
    """

    def __init__(self) -> None:
        """
        Create a player with the piano chosen and sound on.

        Examples
        --------
        >>> Sounds().instrument
        'piano'
        """
        self.enabled = True
        self.instrument = "piano"  # key into INSTRUMENT_BY_KEY
        self._effects = {}
        self._sounding: list = []  # sustained notes that may still be sounding, to release when the next note begins
        self._fades: dict = {}  # running fade-outs, by effect
        self._sequence_run = 0  # which sequence of notes is current, so that an older one stops when a new one starts
        self._sample_files: dict[str, dict[int, Path]] = {}
        self._dir = Path(tempfile.gettempdir()) / "alto_sounds"

    def _samples(self, inst: Instrument) -> dict[int, Path]:
        """
        Find the recorded notes an instrument has on disk.

        Parameters
        ----------
        inst : Instrument
            The instrument.

        Returns
        -------
        dict of int to Path
            MIDI note number to its sample file. The folder is read once and the result is remembered.

        Examples
        --------
        >>> piano = Sounds()._samples(INSTRUMENT_BY_KEY["piano"])
        >>> 60 in piano and piano[60].suffix
        '.wav'
        """
        found = self._sample_files.get(inst.key)
        if found is None:
            folder = ASSETS / inst.folder
            found = {int(p.stem): p for p in folder.glob("*.wav") if p.stem.isdigit()}
            self._sample_files[inst.key] = found
        return found

    def recordings(self, inst: Instrument) -> dict[int, Path]:
        """
        Return the notes an instrument has a recording for on disk.

        Parameters
        ----------
        inst : Instrument
            The instrument.

        Returns
        -------
        dict of int to Path
            MIDI note number to its sample file.

        Examples
        --------
        >>> 60 in Sounds().recordings(INSTRUMENT_BY_KEY["piano"])
        True
        """
        return self._samples(inst)

    def _note_file(
        self,
        inst: Instrument,
        *,
        midi: int,
    ) -> Path:
        """
        Return a WAV file for a note.

        The recording if there is one, otherwise the nearest recording pitch-shifted (or a synthesized piano note outside the
        piano's sampled range). Made files are kept in a temporary folder.

        Parameters
        ----------
        inst : Instrument
            The instrument.
        midi : int
            The MIDI note number. Keyword-only.

        Returns
        -------
        Path
            The file to play.

        Examples
        --------
        >>> Sounds()._note_file(INSTRUMENT_BY_KEY["piano"], midi=60).suffix
        '.wav'
        """
        samples = self._samples(inst)
        if midi in samples:
            return samples[midi]
        self._dir.mkdir(exist_ok=True)
        path = self._dir / f"{inst.key}_{midi}.wav"
        if samples and (inst.key != "piano" or abs(min(samples, key=lambda m: abs(m - midi)) - midi) <= 2):
            nearest = min(samples, key=lambda m: abs(m - midi))
            audio, rate = read_wav(samples[nearest])
            path.write_bytes(to_wav_bytes(shift_pitch(audio, semitones=midi - nearest), rate=rate))
        else:  # the piano outside its sampled range
            path.write_bytes(to_wav_bytes(synth_piano(midi)))
        return path

    FADE_MS = 70  # how quickly a sustained note dies away when the next one begins

    def _effect(
        self,
        inst: Instrument,
        *,
        midi: int,
    ) -> QSoundEffect:
        """
        Return the sound effect for a note, creating it the first time it is needed.

        Parameters
        ----------
        inst : Instrument
            The instrument.
        midi : int
            The MIDI note number. Keyword-only.

        Returns
        -------
        QSoundEffect
            The loaded effect, which can be played again and again.

        Examples
        --------
        >>> effect = Sounds()._effect(INSTRUMENT_BY_KEY["piano"], midi=60)  # doctest: +SKIP
        """
        key = (inst.key, midi)
        fx = self._effects.get(key)
        if fx is None:
            fx = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(str(self._note_file(inst, midi=midi))))
            self._effects[key] = fx
        return fx

    def _release(self, fx: QSoundEffect) -> None:
        """
        Let a sustained note die away quickly instead of cutting it off.

        Parameters
        ----------
        fx : QSoundEffect
            The effect that is sounding.

        Examples
        --------
        >>> from PySide6.QtMultimedia import QSoundEffect
        >>> effect = QSoundEffect()
        >>> # noinspection PyProtectedMember
        >>> sounds._release(effect)  # doctest: +SKIP
        """
        fade = QPropertyAnimation(fx, b"volume")
        fade.setDuration(self.FADE_MS)
        fade.setStartValue(fx.volume())
        fade.setEndValue(0.0)
        fade.finished.connect(fx.stop)
        self._fades[id(fx)] = fade
        fade.start()

    def _release_sounding(self) -> None:
        """
        End the sustained notes that are still ringing.

        Examples
        --------
        >>> Sounds()._release_sounding()  # nothing is ringing: nothing happens
        """
        sounding, self._sounding = self._sounding, []
        for fx in sounding:
            self._release(fx)

    def play_midi(
        self,
        midi: int,
        *,
        volume: float = 1.0,
        instrument: str | None = None,
        force: bool = False,
        release_previous: bool = True,
    ) -> None:
        """
        Play a note in the chosen instrument (or another one).

        A sustained instrument (bowed or blown) ends the notes still sounding first, as a player would, unless
        `release_previous` is False, which is for the notes of a chord that start together. Nothing plays while muted unless
        `force` is set. A failure to play is reported but never raised, so audio can never break an exercise.

        Parameters
        ----------
        midi : int
            The MIDI note number.
        volume : float, default 1.0
            The level from 0 to 1, before the instrument's own gain. Keyword-only.
        instrument : str or None, default None
            The key of the instrument to use instead of the chosen one. Keyword-only.
        force : bool, default False
            Play even while muted, for previews. Keyword-only.
        release_previous : bool, default True
            End the sustained notes still ringing first. Keyword-only.

        Examples
        --------
        >>> s = Sounds()
        >>> s.enabled = False
        >>> s.play_midi(60)  # muted: returns at once
        >>> Sounds().play_midi(60)  # doctest: +SKIP
        """
        if not (self.enabled or force):
            return
        try:
            inst = INSTRUMENT_BY_KEY.get(instrument or self.instrument, INSTRUMENTS[0])
            if inst.sustained and release_previous:
                self._release_sounding()
            fx = self._effect(inst, midi=midi)
            fade = self._fades.pop(id(fx), None)  # this note may have been released a moment ago
            if fade is not None:
                fade.stop()
            fx.setVolume(min(1.0, volume * inst.gain))
            fx.play()
            if inst.sustained:
                self._sounding.append(fx)
        except Exception as exc:  # audio must never break an exercise
            print(f"audio unavailable: {exc}")

    def stop_all(self) -> None:
        """
        Silence every note at once, and cancel any fade-outs under way.

        Examples
        --------
        >>> Sounds().stop_all()
        """
        for fade in self._fades.values():
            fade.stop()
        self._fades.clear()
        self._sounding = []
        for fx in self._effects.values():
            if fx.isPlaying():
                fx.setVolume(0.0)
                fx.stop()

    def preview(
        self,
        key: str,
        *,
        midis: Iterable[int],
        step_ms: int = 300,
    ) -> None:
        """
        Play notes one after another in an instrument, even while muted, to hear what it sounds like.

        Starting a preview silences the one before it.

        Parameters
        ----------
        key : str
            The key of the instrument.
        midis : iterable of int
            The MIDI notes to play, in order. Keyword-only.
        step_ms : int, default 300
            The time between notes, in milliseconds. Keyword-only.

        Examples
        --------
        >>> sounds.preview("flute", midis=[60, 64, 67])  # doctest: +SKIP
        """
        self.stop_all()
        self._play_sequence(
            key,
            steps=[([m], 0.9) for m in midis],
            gap_ms=step_ms,
            force=True,
        )

    def _play_column(
        self,
        midis: Iterable[int],
        *,
        volume: float,
        key: str | None = None,
        force: bool = False,
    ) -> None:
        """
        Start the notes of one column together, first ending any sustained notes still ringing.

        Parameters
        ----------
        midis : iterable of int
            The MIDI notes to sound together.
        volume : float
            The level for each, from 0 to 1. Keyword-only.
        key : str or None, default None
            The instrument's key; the chosen instrument if None. Keyword-only.
        force : bool, default False
            Play even while muted. Keyword-only.

        Examples
        --------
        >>> s = Sounds()
        >>> s.enabled = False
        >>> s._play_column([60, 64, 67], volume=1.0)  # muted: nothing sounds
        """
        inst = INSTRUMENT_BY_KEY.get(key or self.instrument, INSTRUMENTS[0])
        if inst.sustained and (self.enabled or force):
            self._release_sounding()
        for midi in midis:
            self.play_midi(
                midi,
                volume=volume,
                instrument=key,
                force=force,
                release_previous=False,
            )

    def _play_sequence(
        self,
        key: str,
        *,
        steps: list[tuple[list[int], float]],
        gap_ms: int,
        force: bool = False,
    ) -> None:
        """
        Play steps one after another, a fixed time apart.

        The rhythm has to be even, so the notes are loaded first (making a sound effect the first time it is needed takes long
        enough to hold up the next note), and each step is scheduled only once the one before it has been started. A pause
        while the sound system starts therefore delays the rest instead of making them sound together. Starting a sequence
        cancels the steps still waiting from an earlier one.

        Parameters
        ----------
        key : str
            The instrument's key.
        steps : list of tuple of (list of int, float)
            For each step, the MIDI notes of its column and their volume. Keyword-only.
        gap_ms : int
            The time from the start of one step to the start of the next, in milliseconds. Keyword-only.
        force : bool, default False
            Play even while muted. Keyword-only.

        Examples
        --------
        >>> s = Sounds()
        >>> s.enabled = False
        >>> s._play_sequence("piano", steps=[([60], 1.0)], gap_ms=300)  # muted: only cancels any earlier sequence
        >>> s._sequence_run
        1
        """
        self._sequence_run += 1
        run = self._sequence_run
        if not (self.enabled or force) or not steps:
            return
        try:
            inst = INSTRUMENT_BY_KEY[key]
            effects = [self._effect(inst, midi=m) for midis, _ in steps for m in midis]
        except Exception as exc:  # audio must never break an exercise
            print(f"audio unavailable: {exc}")
            return
        deadline = time.monotonic() + 1.0

        def loading() -> bool:
            """
            Report whether any of the sequence's sound effects is still loading.

            Returns
            -------
            bool
                True while at least one effect has not finished loading.

            Examples
            --------
            >>> loading()  # doctest: +SKIP
            False
            """
            # noinspection PyNoneFunctionAssignment
            return any(getattr(fx, "status", lambda: None)() == QSoundEffect.Status.Loading for fx in effects)

        def step(i: int) -> None:
            """
            Play one step of the sequence and schedule the next.

            Parameters
            ----------
            i : int
                The index of the step. Nothing happens if a newer sequence has started since this one was scheduled.

            Examples
            --------
            >>> step(0)  # doctest: +SKIP
            """
            if run != self._sequence_run:
                return
            midis, volume = steps[i]
            self._play_column(
                midis,
                volume=volume,
                key=key,
                force=force,
            )
            if i + 1 < len(steps):  # the next one is due a full gap after this one has started, however long that took
                QTimer.singleShot(gap_ms, lambda: step(i + 1))

        def wait() -> None:
            """
            Wait for the effects to load, for at most a second, then start the first step.

            Examples
            --------
            >>> wait()  # doctest: +SKIP
            """
            if run != self._sequence_run:
                return
            if loading() and time.monotonic() < deadline:
                QTimer.singleShot(10, wait)
            else:
                step(0)

        wait()

    def play_notes(
        self,
        columns: Iterable[Sequence[Note]],
        *,
        gap_ms: int = 450,
    ) -> None:
        """
        Play staff columns left to right, evenly spaced.

        The notes within a column sound together, a little quieter the more there are.

        Parameters
        ----------
        columns : iterable of sequence of Note
            The columns of notes, as drawn on a staff.
        gap_ms : int, default 450
            The time between columns, in milliseconds. Keyword-only.

        Examples
        --------
        >>> s = Sounds()
        >>> s.enabled = False
        >>> s.play_notes([[Note.parse("C4"), Note.parse("E4"), Note.parse("G4")]])  # muted: nothing sounds
        """
        self._play_sequence(
            self.instrument,
            steps=[([n.midi for n in col], min(1.0, 1.4 / len(col) ** 0.5)) for col in columns],
            gap_ms=gap_ms,
        )

    def play_correct(self, streak: int) -> None:
        """
        Play a note that climbs the C major scale (C5 to C6) as the streak grows, then wraps.

        Parameters
        ----------
        streak : int
            How many right answers in a row; 1 plays C5.

        Examples
        --------
        >>> s = Sounds()
        >>> s.enabled = False
        >>> s.play_correct(3)  # muted: nothing sounds
        """
        scale = (
            72,
            74,
            76,
            77,
            79,
            81,
            83,
            84,
        )
        self.play_midi(scale[(max(streak, 1) - 1) % len(scale)])


sounds = Sounds()
