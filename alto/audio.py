"""Note playback: recorded instrument samples (University of Iowa), with pitch-shifting for missing notes."""
from __future__ import annotations

import io
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100


def synth_piano(midi: int, duration: float = 1.6) -> np.ndarray:
    """Additive piano model: stretched partials, per-partial decay, detuned string pair, hammer thump."""
    rng = np.random.default_rng(midi)  # deterministic per note
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
    inharm = 0.00008 * (1 + max(0, 60 - midi) / 24) ** 2 if midi < 60 else 0.0002 * (midi - 55) / 10
    out = np.zeros_like(t)
    for n in range(1, 17):
        f = n * f0 * np.sqrt(1 + inharm * n * n)
        if f > 12000:
            break
        amp = 1.0 / n ** 1.15
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
    thump = np.convolve(thump, np.ones(24) / 24, mode="same") * np.exp(-np.arange(n_th) / (0.004 * SAMPLE_RATE))
    out[:n_th] += 0.25 * thump * (1.0 / (1 + (midi - 40) / 30))
    out *= np.minimum(1.0, (duration - t) / 0.05)  # fade out to avoid a click
    return out / np.max(np.abs(out)) * 0.8


@dataclass(frozen=True)
class Instrument:
    key: str
    label: str
    folder: str  # under assets/: "piano" or "samples/<key>"; file names are MIDI note numbers
    gain: float = 1.0  # level relative to the piano
    sustained: bool = False  # bowed and blown notes end when the next one begins; struck and plucked ones ring on
    family: str = ""  # instruments that are ways of playing the same instrument share a family (the viola: arco, pizzicato)
    variant: str = ""  # which way of playing it, within the family


INSTRUMENTS = (
    Instrument("piano", "Piano", "piano"),
    Instrument("flute", "Flute", "samples/flute", 0.85, sustained=True),
    Instrument("horn", "French Horn", "samples/horn", 0.85, sustained=True),
    Instrument("viola_bowed", "Viola (Arco)", "samples/viola_bowed", 0.85, sustained=True, family="Viola", variant="Arco"),
    Instrument("viola_plucked", "Viola (Pizzicato)", "samples/viola_plucked", 0.85, family="Viola", variant="Pizzicato"),
    Instrument("marimba", "Marimba", "samples/marimba", 0.85),
    Instrument("vibraphone", "Vibraphone", "samples/vibraphone", 0.85),
)
INSTRUMENT_BY_KEY = {i.key: i for i in INSTRUMENTS}


def instrument_groups() -> list[tuple[str, list[Instrument]]]:
    """The instruments as they are listed for choosing: ways of playing one instrument share a single entry."""
    groups: dict[str, list[Instrument]] = {}
    for inst in INSTRUMENTS:
        groups.setdefault(inst.family or inst.label, []).append(inst)
    return list(groups.items())


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Mono 16-bit WAV -> (float samples in -1..1, sample rate)."""
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768, w.getframerate()


def shift_pitch(samples: np.ndarray, semitones: float) -> np.ndarray:
    """Change pitch by resampling (it also changes the length, which is fine for a few semitones)."""
    ratio = 2 ** (semitones / 12)
    positions = np.arange(0, len(samples) - 1, ratio)
    return np.interp(positions, np.arange(len(samples)), samples)


def to_wav_bytes(samples: np.ndarray, rate: int = SAMPLE_RATE) -> bytes:
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
    """Lazy cache of notes played through QSoundEffect, in the chosen instrument."""

    def __init__(self):
        self.enabled = True
        self.instrument = "piano"  # key into INSTRUMENT_BY_KEY
        self._effects = {}
        self._sounding: list = []  # sustained notes that may still be sounding, to release when the next note begins
        self._fades: dict = {}  # running fade-outs, by effect
        self._preview_run = 0  # which preview is current, so that an older one stops when a new one starts
        self._sample_files: dict[str, dict[int, Path]] = {}
        self._dir = Path(tempfile.gettempdir()) / "alto_sounds"

    def _samples(self, inst: Instrument) -> dict[int, Path]:
        """MIDI note -> recorded sample file, for the notes this instrument has on disk."""
        found = self._sample_files.get(inst.key)
        if found is None:
            folder = ASSETS / inst.folder
            found = {int(p.stem): p for p in folder.glob("*.wav") if p.stem.isdigit()}
            self._sample_files[inst.key] = found
        return found

    def recordings(self, inst: Instrument) -> dict[int, Path]:
        """The notes this instrument has a recording for on disk, as MIDI note -> file."""
        return self._samples(inst)

    def _note_file(self, inst: Instrument, midi: int) -> Path:
        """A WAV for this note: the recording if there is one, else the nearest recording pitch-shifted."""
        samples = self._samples(inst)
        if midi in samples:
            return samples[midi]
        self._dir.mkdir(exist_ok=True)
        path = self._dir / f"{inst.key}_{midi}.wav"
        if samples and (inst.key != "piano" or abs(min(samples, key=lambda m: abs(m - midi)) - midi) <= 2):
            nearest = min(samples, key=lambda m: abs(m - midi))
            audio, rate = read_wav(samples[nearest])
            path.write_bytes(to_wav_bytes(shift_pitch(audio, midi - nearest), rate))
        else:  # the piano outside its sampled range
            path.write_bytes(to_wav_bytes(synth_piano(midi)))
        return path

    FADE_MS = 70  # how quickly a sustained note dies away when the next one begins

    def _effect(self, inst: Instrument, midi: int):
        """The sound effect for this note, created the first time it is needed."""
        key = (inst.key, midi)
        fx = self._effects.get(key)
        if fx is None:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect

            fx = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(str(self._note_file(inst, midi))))
            self._effects[key] = fx
        return fx

    def _release(self, fx) -> None:
        """Let a sustained note die away quickly instead of cutting it off."""
        from PySide6.QtCore import QPropertyAnimation

        fade = QPropertyAnimation(fx, b"volume")
        fade.setDuration(self.FADE_MS)
        fade.setStartValue(fx.volume())
        fade.setEndValue(0.0)
        fade.finished.connect(fx.stop)
        self._fades[id(fx)] = fade
        fade.start()

    def _release_sounding(self) -> None:
        """End the sustained notes that are still ringing."""
        sounding, self._sounding = self._sounding, []
        for fx in sounding:
            self._release(fx)

    def play_midi(self, midi: int, volume: float = 1.0, instrument: str | None = None, force: bool = False,
                  release_previous: bool = True) -> None:
        """Play a note in the chosen instrument (or `instrument`). `force` plays even while muted, for previews.

        A sustained instrument (bowed or blown) ends the notes still sounding first, as a player would, unless
        `release_previous` is False, which is for the notes of a chord that start together."""
        if not (self.enabled or force):
            return
        try:
            inst = INSTRUMENT_BY_KEY.get(instrument or self.instrument, INSTRUMENTS[0])
            if inst.sustained and release_previous:
                self._release_sounding()
            fx = self._effect(inst, midi)
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
        """Silence every note at once, and cancel any fade-outs under way."""
        for fade in self._fades.values():
            fade.stop()
        self._fades.clear()
        self._sounding = []
        for fx in self._effects.values():
            if fx.isPlaying():
                fx.setVolume(0.0)
                fx.stop()

    def preview(self, key: str, midis, step_ms: int = 300) -> None:
        """Play these notes one after another in an instrument, even while muted, to hear what it sounds like.

        The notes are loaded first, and each one is scheduled when the one before it has played, so a pause while the
        sound system starts up delays the rest instead of making them all sound at once. Starting a preview ends the
        one before it."""
        import time

        from PySide6.QtCore import QTimer

        self._preview_run += 1
        run = self._preview_run
        self.stop_all()
        notes = list(midis)
        try:
            inst = INSTRUMENT_BY_KEY[key]
            effects = [self._effect(inst, m) for m in notes]
        except Exception as exc:  # audio must never break the settings
            print(f"audio unavailable: {exc}")
            return
        deadline = time.monotonic() + 1.0

        def loading() -> bool:
            from PySide6.QtMultimedia import QSoundEffect

            return any(getattr(fx, "status", lambda: None)() == QSoundEffect.Status.Loading for fx in effects)

        def step(i: int) -> None:
            if run != self._preview_run:
                return
            self.play_midi(notes[i], 0.9, instrument=key, force=True)
            if i + 1 < len(notes):
                QTimer.singleShot(step_ms, lambda: step(i + 1))

        def wait() -> None:
            if run != self._preview_run:
                return
            if loading() and time.monotonic() < deadline:
                QTimer.singleShot(10, wait)
            else:
                step(0)

        wait()

    def _play_column(self, notes, volume: float) -> None:
        """Start the notes of one column together, first ending any sustained notes still ringing."""
        inst = INSTRUMENT_BY_KEY.get(self.instrument, INSTRUMENTS[0])
        if inst.sustained and (self.enabled):
            self._release_sounding()
        for note in notes:
            self.play_midi(note.midi, volume, release_previous=False)

    def play_notes(self, columns, gap_ms: int = 450) -> None:
        """Play staff columns left to right; notes within a column sound together."""
        from PySide6.QtCore import QTimer

        for i, col in enumerate(columns):
            vol = min(1.0, 1.4 / len(col) ** 0.5)
            if i == 0:
                self._play_column(col, vol)
            else:
                QTimer.singleShot(i * gap_ms, lambda c=col, v=vol: self._play_column(c, v))

    def play_correct(self, streak: int) -> None:
        """Climb the C major scale (C5..C6) as the streak grows, then wrap."""
        scale = (72, 74, 76, 77, 79, 81, 83, 84)
        self.play_midi(scale[(max(streak, 1) - 1) % len(scale)])


sounds = Sounds()
