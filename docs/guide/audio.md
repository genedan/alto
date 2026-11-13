---
title: Computer audio
parent: guide
order: 6
permalink: /guide/audio/
---
Alto plays notes: when you answer correctly, when you press "hear it" on an instrument, when an arpeggio is sounded. That
needs very little code, but a few ideas about how computers represent and play sound, and a few about how instruments sound,
are what make the code readable and what let you change it safely. This chapter starts with those ideas, then walks through
`alto/audio.py`.

## Sound as numbers

Sound is air pressure varying over time. A microphone turns it into a voltage, and an **analogue-to-digital converter** measures
that voltage many times a second. The list of measurements is a **digital audio signal**. Playing it back reverses the process.

Three numbers describe a recording:

- **Sample rate**: how many measurements per second. Alto uses **44,100 Hz** (the Compact Disc rate; `SAMPLE_RATE` in `audio.py`).
- **Bit depth**: how precisely each measurement is stored. WAV files in Alto are **16-bit**: each sample is an integer from
  -32,768 to 32,767. Each bit adds about 6 dB of **dynamic range** (the gap between the quietest and loudest sound), so 16
  bits give about 96 dB.
- **Channels**: one (mono) or two (stereo). Alto's recordings and everything it makes are mono.

The encoding of plain samples like this is called **PCM**, *pulse-code modulation*. A **WAV** file is a PCM stream with a small
header (the **RIFF** container) saying the rate, depth and channels. Python's standard `wave` module reads and writes them,
which is all `audio.py` needs:

```python
with wave.open(str(path)) as w:
    samples = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
```

`"<i2"` means "little-endian signed 16-bit integer"; dividing by 32,768 turns the integers into floating-point numbers between
-1 and 1, which are easier to compute with. Writing does the reverse: multiply by 32,767 and store as `"<i2"`.

### The sampling theorem and aliasing

The **Nyquist-Shannon sampling theorem** says that a signal can be captured perfectly if it is sampled at more than twice its
highest frequency. At 44,100 Hz, nothing above **22,050 Hz** can be represented, which is just above what people hear. A
frequency that is *too* high is not lost but folded back down to a wrong, lower one. That is **aliasing**, and it is why
recording equipment filters before sampling. It matters in Alto only when you change a sample's speed (see below) or generate
a sound with many high partials, which is why `synth_piano` stops adding partials above 12,000 Hz.

### Loudness

- **Clipping**: a sample cannot go beyond -1 or 1. A calculation that goes past it is flattened ("clipped"), which sounds harsh.
  Anything you generate should be scaled down (**normalised**) so its peak is below 1. `synth_piano` scales its result so the
  loudest sample is 0.8.
- **Decibels** are a logarithmic scale for amplitude: `20 * log10(ratio)`. Halving the amplitude is -6 dB. Because hearing is
  roughly logarithmic too, a linear volume of 0.5 does not sound "half as loud"; it sounds only a little quieter. Qt's
  `QSoundEffect.setVolume` is linear. If you want a volume control that feels even, map it through a curve (Qt provides
  `QtAudio.convertVolume` for that).
- **Summing sounds adds amplitudes**, so a chord of four notes is louder, and can clip. Alto's `play_notes` plays each note of a
  chord at `1.4 / sqrt(count)` of full volume: that keeps the loudness of a chord about the same however many notes it has, because uncorrelated
  signals add in *power* (the square of amplitude), not in amplitude.

## Pitch, frequency and the numbers behind notes

A musical pitch is a **frequency** in hertz (cycles per second). Western music divides the octave into 12 equal ratios, **equal
temperament**, so each semitone multiplies the frequency by 2^(1/12). **MIDI** (the Musical Instrument Digital Interface
standard) numbers the notes: middle C is 60, A above it is 69, and each semitone adds one. The reference pitch A4 is 440 Hz (set
by an international standard, ISO 16). The formula in `synth_piano` is the whole story:

```python
f0 = 440.0 * 2 ** ((midi - 69) / 12)  # midi 60 gives 261.63 Hz
```

`Note.midi` in `alto/theory/pitch.py` computes the MIDI number from a spelled note. Note that C♯4 and D♭4 have the same MIDI
number and the same frequency (in equal temperament), which is why audio works with MIDI numbers while the rest of Alto works
with spelled notes.

A real note is not a pure tone. It is a **fundamental** at `f0` plus **overtones**, or **partials**, at higher frequencies. In
a string or a pipe the partials are close to whole-number multiples (the **harmonic series**: 2×, 3×, 4× ...), and the mix of
their strengths is what we hear as **timbre**, the difference between a flute and a viola playing the same note.

## How Alto plays a note

Everything is in the class `Sounds` and a single shared instance, `sounds`, in `alto/audio.py`.

### Instruments and recordings

An `Instrument` (a frozen dataclass) has a `key`, a `label`, a `folder` under `alto/assets/` and a few flags: `gain` (its level
relative to the piano), `sustained` and, for instruments with several ways of playing (the viola's arco and pizzicato), a
`family` and a `variant`. Recordings are **one mono WAV file per note**, named by MIDI number: `alto/assets/samples/flute/72.wav`
is the flute's C5. Most come from the University of Iowa Electronic Music Studios' Musical Instrument Samples, recorded in a
studio, in most cases at every semitone.

An instrument that plays one recording for each pitch is a **sampler**, and the technique is **multisampling**. Professional
samplers add more: several recordings per note at different loudnesses (**velocity layers**), alternating takes to avoid a
machine-gun repetition (**round robin**), and repeating a section of a long note to sustain it (**looping**). Alto needs none
of these, since each note is played once at one level.

### Creating the sound

```
play_midi(midi)
   -> _effect(inst, midi)          get or make a QSoundEffect for (instrument, note)
        -> _note_file(inst, midi)  find the WAV; make one if the note has no recording
   -> setVolume(...), play()
```

1. **`_note_file`** returns the recording's path if that note has one. If it does not, it picks the *nearest* recorded note and
   makes a new WAV by shifting its pitch (below), saved in `alto_sounds` in the system temporary folder. The piano is special:
   beyond two semitones from a recording it is synthesised instead (below).
2. **`_effect`** wraps the file in a `QSoundEffect` the first time and keeps it, so a note is loaded once.
   **`QSoundEffect`** is Qt Multimedia's class for short, uncompressed sounds that must start with low delay: it loads the whole
   file into memory, so `play()` is quick. Qt has two others: `QMediaPlayer` streams longer, compressed audio and starts slower,
   and `QAudioSink` is a lower-level output that you feed raw samples yourself. Short WAV notes are what `QSoundEffect` is for.
3. **`play_midi`** sets the volume (the requested volume times the instrument's gain, capped at 1) and plays. It is wrapped in
   `try/except` and prints rather than raises: **audio must never break an exercise**, and machines with no sound card exist.
   `sounds.enabled` is the master switch the sound button controls; `force=True` plays anyway, for the instrument preview.

### Pitch shifting by resampling

```python
def shift_pitch(samples, *, semitones):
    ratio = 2 ** (semitones / 12)
    positions = np.arange(0, len(samples) - 1, ratio)
    return np.interp(positions, np.arange(len(samples)), samples)
```

To raise a recording by two semitones, read it 12% faster: take the samples at positions 0, 1.122, 2.245, ... and interpolate
between neighbours. This is **resampling**, and it is the simplest pitch shifter. It has two well-known side effects: the
sound gets **shorter** (a note shifted up two semitones lasts 1/1.122 of the time, which the arithmetic above confirms: 70,560
samples become 62,861), and the **timbre** changes, because everything speeds up together (the "chipmunk effect"). For one or
two semitones on a flute or a viola neither is noticeable, which is why Alto shifts only to fill the odd missing note.

If you ever need large shifts, there are better algorithms, each a topic of its own:

- **Phase vocoder**: works in the frequency domain, so it can change pitch without changing duration, at some cost in clarity.
- **PSOLA** (*pitch-synchronous overlap-add*): cuts the sound into one-period grains and overlaps them at new spacing; good for
  speech and single voices.
- **Better interpolation**: `np.interp` is **linear interpolation**, which smooths the high frequencies slightly. Sinc or
  polynomial interpolation is more accurate (a polyphase resampler such as `scipy.signal.resample_poly`).

### Making a piano with arithmetic

`synth_piano(midi)` makes a piano note without any recording. It is **additive synthesis**: build the sound by adding sine
waves, one per partial. The code has several pieces of real physics, each one line:

```python
f0 = 440.0 * 2 ** ((midi - 69) / 12)
for n in range(1, 17):  # the first 16 partials
    f = n * f0 * np.sqrt(1 + inharm * n * n)  # stiff strings: partials sit slightly sharp
    amp = 1.0 / n**1.15  # higher partials are quieter
    if n % 7 == 0:
        amp *= 0.3  # the hammer strikes ~1/7 along the string, which suppresses these
    decay = 2.2 + 1.1 * n + (midi - 60) * 0.03  # higher partials, and higher notes, die faster
    for detune in (-0.0008, 0.0008):  # two strings per note, slightly apart: the shimmer
        out += amp * 0.5 * np.sin(2 * np.pi * f * (1 + detune) * t + phase) * np.exp(-decay * t)
```

- **Inharmonicity.** A stiff string's partials are not exact multiples of the fundamental; they are slightly *sharper*, by a factor
  of `sqrt(1 + B n^2)` for a constant `B` of the string. This is why a piano's octaves are tuned wide, and why a pure harmonic
  sound would not sound like a piano.
- **Decay** is an exponential, `exp(-decay * t)`; higher partials fade quicker, so the sound mellows as it rings.
- **Strike point.** Where the hammer hits a string, the partials that have a node there are not excited.
- **Envelope.** After the partials come an attack of a couple of milliseconds (`1 - exp(-t / 0.002)`), a dip into the sustain, a
  short burst of **filtered noise** for the hammer's thump (white noise smoothed by a moving average, a crude low-pass filter),
  and a 50 ms fade-out so the file does not end with a click.

You can check the result in a few lines. A Fourier transform shows the spectrum, and the loudest peak of a synthesised middle C
is at 261.9 Hz (the frequency resolution of a 1.6 second clip is about 0.6 Hz, so this is the fundamental, 261.63 Hz):

```python
import numpy as np
from alto.audio import synth_piano, SAMPLE_RATE

x = synth_piano(60)
spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))  # a window function reduces leakage
freqs = np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)
print(freqs[spectrum.argmax()])
```

To listen, write it with `to_wav_bytes` and open the file:

```python
from alto.audio import to_wav_bytes

open("/tmp/c4.wav", "wb").write(to_wav_bytes(synth_piano(60)))
```

### Sustained and plucked sounds

A piano key, once struck, rings and fades whatever you do. A flute or a bowed string ends when the player stops. `Instrument.sustained`
captures that: when a **sustained** instrument plays a note, any note still sounding is **released** by `_release`: a 70 ms
fade of the effect's `volume` property with a `QPropertyAnimation`, then `stop()`. Without that, melodies on a flute would
pile up. `stop_all` cancels all fades and silences everything.

An abrupt stop is audible as a click, and a fade avoids it. The same idea (**an envelope**) shapes every synthesised note.
The classical envelope is **ADSR**: *attack* (how fast the sound begins), *decay*, *sustain* level, *release* (how it ends).

### Timing a sequence

To play a melody or an arpeggio, `_play_sequence` schedules each step with `QTimer.singleShot` and has three safeguards.

1. **Wait for loading.** `QSoundEffect` loads in the background, and a note started before it is ready is silent. The sequence
   polls `status()` every 10 ms for up to a second before starting.
2. **Anchor the schedule to the start.** Step *i* schedules step *i + 1* a full gap after step *i* *starts*, not after it
   finishes. If starting one note takes a while, the others are not pushed later and the rhythm stays even. The test
   `test_a_note_that_is_slow_to_start_does_not_upset_the_rhythm` checks this.
3. **A newer sequence cancels an older one.** Each sequence has a run number, and a step that finds a newer number does nothing.
   This pattern, a *token*, appears in the animations too: callbacks scheduled for later cannot be cancelled easily, so they
   check whether they are still wanted.

## Latency and the limits of this design

**Latency** is the delay between asking for a sound and hearing it. `QSoundEffect` is good enough here: a few tens of
milliseconds. Real-time musical instruments need under about 10 ms, and for that you would use an audio library with a
callback, such as **PortAudio**, and fill small buffers on a high-priority thread. If your program fills a buffer too late you
get an **underrun** (a glitch). None of that applies to Alto, and it is the reason the playback code is short.

## Adding an instrument

The steps are in [For developers]({{ '/development/' | relative_url }}): the WAV files named by MIDI number in
`alto/assets/samples/<key>/`, an `Instrument` in `INSTRUMENTS`, an entry in `instrument_info.INFO`, and the credit in
`THIRD_PARTY_NOTICES.md`. Check that the licence permits redistribution. A few practical points:

- **Trim silence at the start**, or the note feels late. Normalise levels so that notes of one instrument are similar, then set
  `gain` to balance instruments against each other.
- **Mono, 16-bit** files at any common rate (44.1 or 48 kHz) work; `QSoundEffect` resamples at playback.
- Mark `sustained=True` for bowed and blown instruments; leave it off for struck and plucked ones.
- Gaps are fine: a missing note is made from its nearest neighbour.

## Testing audio without speakers

Tests never play sound. `tests/conftest.py` turns `sounds.enabled` off for every test, and `tests/test_audio.py` replaces
`QSoundEffect` with a `FakeEffect` that records `play`, `stop` and `setVolume` calls in a list, so assertions are about *what
would have been played*, in what order and how loudly. This is the general approach to testing anything with a side effect on
the world: replace the world with a recorder.

## Words to search for

*PCM, WAV, RIFF.* *Nyquist frequency, aliasing, anti-aliasing filter.* *Quantisation, dither.* *Dynamic range, decibel,
loudness, psychoacoustics, equal-loudness contours.* *Overtone, partial, harmonic series, timbre, inharmonicity.* *Additive,
subtractive, FM, wavetable and physical-modelling synthesis.* *Karplus-Strong algorithm* (a famous few-line plucked-string
model). *Convolution* and *impulse response* (how reverb is done). *Fourier transform, FFT, spectrogram, window function.*
*Resampling, interpolation, sinc interpolation, polyphase filter.* *Time-stretching, phase vocoder, PSOLA.* *Sampler,
multisampling, velocity layer, round robin, loop point.* *SoundFont and SFZ* (sample instrument formats). *Latency, buffer,
underrun, callback.* *MIDI* (the standard also defines messages, channels and file formats).

## Further reading

- Julius O. Smith III, *Mathematics of the Discrete Fourier Transform*, *Introduction to Digital Filters*, *Physical Audio Signal
  Processing* and *Spectral Audio Signal Processing* (W3K Publishing, 2007; free at ccrma.stanford.edu/~jos, the author's
  Stanford page, which is the primary source). The best free route from the sampling theorem to physical modelling of
  instruments.
- Ken C. Pohlmann, *Principles of Digital Audio*, 6th ed. (McGraw-Hill, 2010): sampling, quantisation, converters, file formats.
- Alan V. Oppenheim and Ronald W. Schafer, *Discrete-Time Signal Processing*, 3rd ed. (Pearson, 2010): the standard textbook
  on the mathematics behind everything above.
- Claude E. Shannon, "Communication in the Presence of Noise", *Proceedings of the IRE* 37(1), 1949: the sampling theorem.
- Miller Puckette, *The Theory and Technique of Electronic Music* (World Scientific, 2007): a gentle book on building sound from
  oscillators and envelopes, and a good second read after this chapter.
- Curtis Roads, *The Computer Music Tutorial* (MIT Press, 1996): the broad survey of the field.
- Udo Zölzer (ed.), *DAFX: Digital Audio Effects*, 2nd ed. (Wiley, 2011): resampling, pitch shifting and time stretching, with the
  phase vocoder in detail.
- Mark Dolson, "The Phase Vocoder: A Tutorial", *Computer Music Journal* 10(4), 1986; and Jean Laroche and Mark Dolson, "Improved
  Phase Vocoder Time-Scale Modification of Audio", *IEEE Transactions on Speech and Audio Processing* 7(3), 1999.
- Kevin Karplus and Alex Strong, "Digital Synthesis of Plucked-String and Drum Timbres", *Computer Music Journal* 7(2), 1983.
- Harvey Fletcher, "Normal Vibration Frequencies of a Stiff Piano String", *Journal of the Acoustical Society of America* 36(1),
  1964: the inharmonicity formula used in `synth_piano`.
- Neville H. Fletcher and Thomas D. Rossing, *The Physics of Musical Instruments*, 2nd ed. (Springer, 1998): why instruments
  sound as they do.
- *MIDI 1.0 Detailed Specification*, MIDI Manufacturers Association, midi.org.
- The University of Iowa Electronic Music Studios, *Musical Instrument Samples*, theremin.music.uiowa.edu/MIS.html: the source
  of the recordings Alto ships.
- The Qt documentation for `QSoundEffect`, `QMediaPlayer`, `QAudioSink` and "Qt Multimedia", doc.qt.io.
