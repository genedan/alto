---
title: alto.audio
parent: api
package: alto
order: 1
permalink: /api/alto.audio/
---
{% raw %}
Note playback: recorded instrument samples (University of Iowa), with pitch-shifting for missing notes.

`Sounds` plays notes through Qt's `QSoundEffect`, one effect per note, created the first time it is needed. A note with
no recording is made by shifting the nearest recording (or, for the piano outside its sampled range, by synthesis).
The module-level `sounds` is the one the interface uses.

**Examples**

```pycon
>>> [inst.label for inst in INSTRUMENTS][:2]
['Piano', 'Flute']
>>> Sounds().instrument
'piano'
```

## synth_piano

```python
def synth_piano(
    midi: int,
    *,
    duration: float = 1.6,
) -> np.ndarray
```

Synthesize a piano note, for notes outside the recorded range.

An additive model: stretched partials, a decay for each partial, a detuned string pair, and a hammer thump.

**Parameters**

- `midi` (*int*): The MIDI note number. The same number always gives the same sound.
- `duration` (*float, default 1.6*): How long the note lasts, in seconds. Keyword-only.

**Returns**

- *numpy.ndarray*: Mono samples at `SAMPLE_RATE`, scaled so the loudest is 0.8.

**Examples**

```pycon
>>> samples = synth_piano(60, duration=0.1)
>>> len(samples)
4410
>>> round(float(np.max(np.abs(samples))), 1)
0.8
```

## Instrument

```python
Instrument(
    key: str,
    *,
    label: str,
    folder: str,
    gain: float = 1.0,
    sustained: bool = False,
    family: str = '',
    variant: str = '',
)
```

An instrument that notes can be played on, and where its recordings are.

**Attributes**

- `key` (*str*): A short identifier used in settings and file names.
- `label` (*str*): The name shown in the interface. Keyword-only.
- `folder` (*str*): Under `assets/`: "piano" or "samples/<key>". File names are MIDI note numbers. Keyword-only.
- `gain` (*float, default 1.0*): The level relative to the piano. Keyword-only.
- `sustained` (*bool, default False*): True for bowed and blown instruments, whose notes end when the next one begins; struck and plucked ones ring on. Keyword-only.
- `family` (*str, default ""*): Instruments that are ways of playing the same instrument share a family (the viola: arco and pizzicato). Keyword-only.
- `variant` (*str, default ""*): Which way of playing it, within the family. Keyword-only.

**Examples**

```pycon
>>> Instrument("flute", label="Flute", folder="samples/flute", sustained=True).gain
1.0
```

## instrument_groups

```python
def instrument_groups() -> list[tuple[str, list[Instrument]]]
```

Return the instruments as they are listed for choosing.

Ways of playing one instrument share a single entry.

**Returns**

- *list of tuple of (str, list of Instrument)*: Each entry's name (the family, or the instrument's own label) and its instruments, in the order listed.

**Examples**

```pycon
>>> [name for name, _ in instrument_groups()]
['Piano', 'Flute', 'French Horn', 'Viola', 'Marimba', 'Vibraphone']
>>> [inst_.variant for inst_ in dict(instrument_groups())["Viola"]]
['Arco', 'Pizzicato']
```

## read_wav

```python
def read_wav(path: Path) -> tuple[np.ndarray, int]
```

Read a mono 16-bit WAV file.

**Parameters**

- `path` (*Path*): The file.

**Returns**

- *tuple of (numpy.ndarray, int)*: The samples as floats from -1 to 1, and the sample rate in hertz.

**Examples**

```pycon
>>> import tempfile
>>> path_ = Path(tempfile.mkdtemp()) / "silence.wav"
>>> _ = path_.write_bytes(to_wav_bytes(np.zeros(10)))
>>> samples, rate = read_wav(path_)
>>> len(samples), rate
(10, 44100)
```

## shift_pitch

```python
def shift_pitch(
    samples: np.ndarray,
    *,
    semitones: float,
) -> np.ndarray
```

Change the pitch of samples by resampling them.

It also changes the length, which is fine for a few semitones.

**Parameters**

- `samples` (*numpy.ndarray*): Mono samples.
- `semitones` (*float*): How far to shift; positive is higher. Keyword-only.

**Returns**

- *numpy.ndarray*: The resampled samples, shorter when shifted up and longer when shifted down.

**Examples**

```pycon
>>> len(shift_pitch(np.zeros(100), semitones=12))  # an octave up: half as long
50
```

## to_wav_bytes

```python
def to_wav_bytes(
    samples: np.ndarray,
    *,
    rate: int = SAMPLE_RATE,
) -> bytes
```

Encode samples as a mono 16-bit WAV file in memory.

**Parameters**

- `samples` (*numpy.ndarray*): Mono samples from -1 to 1.
- `rate` (*int, default SAMPLE_RATE*): The sample rate in hertz. Keyword-only.

**Returns**

- *bytes*: The contents of a WAV file.

**Examples**

```pycon
>>> to_wav_bytes(np.zeros(10))[:4]
b'RIFF'
```

## Sounds

```python
Sounds()
```

A lazy cache of notes played through `QSoundEffect`, in the chosen instrument.

**Attributes**

- `enabled` (*bool*): False while the app is muted.
- `instrument` (*str*): The key of the instrument in use, a key of `INSTRUMENT_BY_KEY`.
- `FADE_MS` (*int*): How quickly a sustained note dies away when the next one begins, in milliseconds.

**Examples**

```pycon
>>> s = Sounds()
>>> s.enabled, s.instrument
(True, 'piano')
>>> s.enabled = False  # muted: nothing below makes a sound
>>> s.play_midi(60)
```

**Constructor**

Create a player with the piano chosen and sound on.

**Constructor examples**

```pycon
>>> Sounds().instrument
'piano'
```

### Sounds.recordings

```python
def recordings(inst: Instrument) -> dict[int, Path]
```

Return the notes an instrument has a recording for on disk.

**Parameters**

- `inst` (*Instrument*): The instrument.

**Returns**

- *dict of int to Path*: MIDI note number to its sample file.

**Examples**

```pycon
>>> 60 in Sounds().recordings(INSTRUMENT_BY_KEY["piano"])
True
```

### Sounds.play_midi

```python
def play_midi(
    midi: int,
    *,
    volume: float = 1.0,
    instrument: str | None = None,
    force: bool = False,
    release_previous: bool = True,
) -> None
```

Play a note in the chosen instrument (or another one).

A sustained instrument (bowed or blown) ends the notes still sounding first, as a player would, unless
`release_previous` is False, which is for the notes of a chord that start together. Nothing plays while muted unless
`force` is set. A failure to play is reported but never raised, so audio can never break an exercise.

**Parameters**

- `midi` (*int*): The MIDI note number.
- `volume` (*float, default 1.0*): The level from 0 to 1, before the instrument's own gain. Keyword-only.
- `instrument` (*str or None, default None*): The key of the instrument to use instead of the chosen one. Keyword-only.
- `force` (*bool, default False*): Play even while muted, for previews. Keyword-only.
- `release_previous` (*bool, default True*): End the sustained notes still ringing first. Keyword-only.

**Examples**

```pycon
>>> s = Sounds()
>>> s.enabled = False
>>> s.play_midi(60)  # muted: returns at once
>>> Sounds().play_midi(60)  # doctest: +SKIP
```

### Sounds.stop_all

```python
def stop_all() -> None
```

Silence every note at once, and cancel any fade-outs under way.

**Examples**

```pycon
>>> Sounds().stop_all()
```

### Sounds.preview

```python
def preview(
    key: str,
    *,
    midis: Iterable[int],
    step_ms: int = 300,
) -> None
```

Play notes one after another in an instrument, even while muted, to hear what it sounds like.

Starting a preview silences the one before it.

**Parameters**

- `key` (*str*): The key of the instrument.
- `midis` (*iterable of int*): The MIDI notes to play, in order. Keyword-only.
- `step_ms` (*int, default 300*): The time between notes, in milliseconds. Keyword-only.

**Examples**

```pycon
>>> sounds.preview("flute", midis=[60, 64, 67])  # doctest: +SKIP
```

### Sounds.play_notes

```python
def play_notes(
    columns: Iterable[Sequence[Note]],
    *,
    gap_ms: int = 450,
) -> None
```

Play staff columns left to right, evenly spaced.

The notes within a column sound together, a little quieter the more there are.

**Parameters**

- `columns` (*iterable of sequence of Note*): The columns of notes, as drawn on a staff.
- `gap_ms` (*int, default 450*): The time between columns, in milliseconds. Keyword-only.

**Examples**

```pycon
>>> s = Sounds()
>>> s.enabled = False
>>> s.play_notes([[Note.parse("C4"), Note.parse("E4"), Note.parse("G4")]])  # muted: nothing sounds
```

### Sounds.play_correct

```python
def play_correct(streak: int) -> None
```

Play a note that climbs the C major scale (C5 to C6) as the streak grows, then wraps.

**Parameters**

- `streak` (*int*): How many right answers in a row; 1 plays C5.

**Examples**

```pycon
>>> s = Sounds()
>>> s.enabled = False
>>> s.play_correct(3)  # muted: nothing sounds
```
{% endraw %}
