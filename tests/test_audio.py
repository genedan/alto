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
    shipped = {"piano", "marimba", "vibraphone", "flute", "horn", "viola_bowed", "viola_plucked"}
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
