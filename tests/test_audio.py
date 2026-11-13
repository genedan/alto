import io
import wave

import numpy as np
from alto.audio import SAMPLE_RATE, synth_piano, to_wav_bytes


def test_synth_is_normalized_and_finite():
    for midi in (36, 60, 72, 84):
        s = synth_piano(midi)
        assert np.isfinite(s).all()
        assert 0.5 < np.max(np.abs(s)) <= 0.8001


def test_dominant_frequency_matches_pitch():
    s = synth_piano(69)[: SAMPLE_RATE // 2]  # A4 = 440 Hz
    spectrum = np.abs(np.fft.rfft(s))
    assert abs(np.argmax(spectrum) * SAMPLE_RATE / len(s) - 440) < 3


def test_wav_roundtrip():
    with wave.open(io.BytesIO(to_wav_bytes(synth_piano(60)))) as w:
        assert w.getframerate() == SAMPLE_RATE and w.getnchannels() == 1


def test_bundled_samples_cover_staff_range():
    from alto.audio import ASSET_DIR

    for midi in range(36, 97):
        with wave.open(str(ASSET_DIR / f"{midi}.wav")) as w:
            assert w.getnchannels() == 1 and w.getframerate() == SAMPLE_RATE
            frames = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        assert frames.size > SAMPLE_RATE and np.abs(frames).max() > 1000, midi


def test_every_instrument_has_recordings_and_covers_the_notes():
    from alto.audio import INSTRUMENTS, Sounds, read_wav

    assert len(INSTRUMENTS) >= 7 and INSTRUMENTS[0].key == "piano"
    # instruments whose recordings ship with Alto; any other is still being sourced
    shipped = {"piano", "marimba", "vibraphone", "viola_bowed", "viola_plucked", "flute", "horn"}
    sounds = Sounds()
    for inst in INSTRUMENTS:
        files = sounds._samples(inst)
        if not files and inst.key not in shipped:
            continue  # no recordings yet: these notes play as the synthesized piano
        assert len(files) >= 15, inst.key
        for midi, path in list(files.items())[:3]:
            audio, rate = read_wav(path)
            assert np.isfinite(audio).all() and np.abs(audio).max() > 0.05 and len(audio) > rate // 2, (inst.key, midi)
        # any staff note gets a file: a recording or a pitch-shifted neighbour
        for midi in (40, 61, 73, 90):
            assert sounds._note_file(inst, midi).exists(), (inst.key, midi)


def test_pitch_shift_moves_the_frequency():
    from alto.audio import shift_pitch

    t = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    tone = np.sin(2 * np.pi * 440 * t)
    shifted = shift_pitch(tone, 2)  # up a whole tone: ~493.9 Hz
    peak = np.argmax(np.abs(np.fft.rfft(shifted))) * SAMPLE_RATE / len(shifted)
    assert abs(peak - 493.9) < 3


# -- sustained and ringing notes ------------------------------------------------------------------------------------


class FakeEffect:
    """Stands in for QSoundEffect, so these tests need no audio hardware."""

    def __init__(self, label, log):
        self.label, self.log, self._volume = label, log, 1.0

    def setVolume(self, v):
        self._volume = v

    def volume(self):
        return self._volume

    def play(self):
        self.log.append(("play", self.label))

    def stop(self):
        self.log.append(("stop", self.label))


def engine(monkeypatch, instrument):
    from alto.audio import Sounds

    log, effects = [], {}
    s = Sounds()
    s.instrument = instrument
    monkeypatch.setattr(s, "_effect", lambda inst, midi: effects.setdefault(midi, FakeEffect(midi, log)))
    monkeypatch.setattr(s, "_release", lambda fx: log.append(("release", fx.label)))
    return s, log


def test_only_bowed_and_blown_instruments_are_sustained():
    from alto.audio import INSTRUMENT_BY_KEY

    sustained = {k for k, i in INSTRUMENT_BY_KEY.items() if i.sustained}
    assert {"viola_bowed", "flute", "horn"} <= sustained
    assert not sustained & {"piano", "marimba", "vibraphone", "viola_plucked"}


def test_a_bowed_note_ends_when_the_next_one_begins(monkeypatch):
    s, log = engine(monkeypatch, "viola_bowed")
    s.play_midi(60)
    s.play_midi(62)
    assert log == [("play", 60), ("release", 60), ("play", 62)]


def test_struck_and_plucked_notes_ring_on(monkeypatch):
    for instrument in ("piano", "marimba", "vibraphone", "viola_plucked"):
        s, log = engine(monkeypatch, instrument)
        s.play_midi(60)
        s.play_midi(62)
        assert log == [("play", 60), ("play", 62)], instrument


def test_the_notes_of_a_chord_sound_together_and_end_together(monkeypatch):
    from alto.theory.pitch import Note

    s, log = engine(monkeypatch, "viola_bowed")
    s.play_notes([[Note(4, 0), Note(4, 2), Note(4, 4)]])  # C4 E4 G4 at once
    assert log == [("play", 60), ("play", 64), ("play", 67)]  # none of them cuts off another
    s.play_notes([[Note(4, 1)]])
    assert log[3:] == [("release", 60), ("release", 64), ("release", 67), ("play", 62)]


def test_a_melody_hands_over_from_note_to_note(monkeypatch):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from alto.theory.pitch import Note
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])  # kept alive for the timers
    s, log = engine(monkeypatch, "viola_bowed")
    s.play_notes([[Note(4, 0)], [Note(4, 1)], [Note(4, 2)]], gap_ms=30)
    QTest.qWait(250)
    assert log == [("play", 60), ("release", 60), ("play", 62), ("release", 62), ("play", 64)]


def test_a_muted_engine_neither_plays_nor_releases(monkeypatch):
    s, log = engine(monkeypatch, "viola_bowed")
    s.enabled = False
    s.play_midi(60)
    s.play_midi(62)
    assert log == []


def test_the_two_ways_of_playing_the_viola_are_listed_together():
    from alto.audio import instrument_groups

    groups = dict(instrument_groups())
    assert [i.key for i in groups["Viola"]] == ["viola_bowed", "viola_plucked"]
    assert [i.variant for i in groups["Viola"]] == ["Arco", "Pizzicato"]
    assert all(len(v) == 1 for k, v in groups.items() if k != "Viola")  # everything else is on its own
    assert len(groups) == 6


# -- hearing an instrument (the preview in the settings) ------------------------------------------------------------


def preview_engine(monkeypatch, instrument="viola_bowed"):
    """An engine whose notes are recorded with the time they were started."""
    import os
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from alto.audio import Sounds
    from PySide6.QtWidgets import QApplication

    global _preview_app
    _preview_app = QApplication.instance() or QApplication([])  # kept alive for the timers
    s, started = Sounds(), []

    class Quiet(FakeEffect):
        def isPlaying(self):
            return False

    monkeypatch.setattr(s, "_effect", lambda inst, midi: Quiet(midi, []))
    monkeypatch.setattr(s, "play_midi", lambda midi, *a, **k: started.append((midi, time.monotonic())))
    return s, started


def test_a_preview_plays_its_notes_in_order_one_step_apart(monkeypatch):
    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.preview("viola_bowed", (60, 64, 67), step_ms=60)
    QTest.qWait(400)
    assert [m for m, _ in started] == [60, 64, 67]
    times = [t for _, t in started]
    assert all(b - a >= 0.05 for a, b in zip(times, times[1:]))


def test_a_pause_in_the_program_delays_the_notes_instead_of_making_them_sound_together(monkeypatch):
    import time

    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.preview("viola_bowed", (60, 64, 67), step_ms=80)
    time.sleep(0.5)  # the sound system starting up, say, which blocks the timers
    QTest.qWait(500)
    assert [m for m, _ in started] == [60, 64, 67]
    times = [t for _, t in started]
    assert all(b - a >= 0.07 for a, b in zip(times, times[1:]))


def test_starting_a_second_preview_ends_the_first(monkeypatch):
    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.preview("viola_bowed", (60, 64, 67), step_ms=80)
    QTest.qWait(100)  # the first note, and maybe the second, have started
    s.preview("viola_bowed", (62, 65, 69), step_ms=80)
    QTest.qWait(400)
    played = [m for m, _ in started]
    assert played[-3:] == [62, 65, 69]
    assert 67 not in played  # the old one never reached its last note


# -- the rhythm of a melody (the arpeggio that plays on a right answer) ----------------------------------------------


def melody(n):
    from alto.theory.pitch import Note

    return [[Note(4, i % 7)] for i in range(n)]


def test_the_notes_of_a_melody_are_evenly_spaced(monkeypatch):
    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.play_notes(melody(5), gap_ms=70)
    QTest.qWait(600)
    assert len(started) == 5
    gaps = [b - a for (_, a), (_, b) in zip(started, started[1:])]
    assert all(0.06 <= g <= 0.14 for g in gaps), gaps


def test_a_note_that_is_slow_to_start_does_not_upset_the_rhythm(monkeypatch):
    import time

    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)

    def slow_start(midi, *args, **kwargs):  # the first note takes 60 ms to get going, as the first one can
        if not started:
            time.sleep(0.06)
        started.append((midi, time.monotonic()))

    monkeypatch.setattr(s, "play_midi", slow_start)
    s.play_notes(melody(4), gap_ms=100)
    QTest.qWait(700)
    gaps = [b - a for (_, a), (_, b) in zip(started, started[1:])]
    assert len(started) == 4 and all(0.09 <= g <= 0.16 for g in gaps), gaps


def test_a_stall_delays_the_notes_instead_of_bunching_them(monkeypatch):
    import time

    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.play_notes(melody(4), gap_ms=80)
    time.sleep(0.4)  # the program is busy, so the timers are late
    QTest.qWait(600)
    gaps = [b - a for (_, a), (_, b) in zip(started, started[1:])]
    assert len(started) == 4 and all(g >= 0.07 for g in gaps), gaps


def test_a_new_melody_cancels_the_notes_still_waiting_from_the_last(monkeypatch):
    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.play_notes(melody(5), gap_ms=80)
    QTest.qWait(100)
    s.play_notes([[n] for n in melody(1)[0]] * 3, gap_ms=80)
    QTest.qWait(500)
    first = [m for m, _ in started]
    assert first.count(first[0]) >= 3 and len(started) < 5 + 3  # the old melody never reached its end
    assert len([m for m in first]) <= 2 + 3


def test_a_muted_melody_plays_nothing(monkeypatch):
    from PySide6.QtTest import QTest

    s, started = preview_engine(monkeypatch)
    s.enabled = False
    s.play_notes(melody(3), gap_ms=30)
    QTest.qWait(150)
    assert started == []
