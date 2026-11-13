---
title: alto.theory.scales
parent: api
package: alto.theory
order: 11
permalink: /api/alto.theory.scales/
---
{% raw %}
Scales, modes, key signatures and chords, built from spelled intervals.

`SCALES` and `CHORDS` map a name to the list of intervals above the tonic or root. `build` turns such a list into notes,
and the other functions work out key signatures, mode tonics and arpeggios from them.

**Examples**

```pycon
>>> [str(n) for n in build(Note.parse("D4"), intervals=SCALES["Dorian"])]
['D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']
>>> [str(n) for n in build(Note.parse("C4"), intervals=CHORDS["minor 7th"])]
['C4', 'E♭4', 'G4', 'B♭4']
```

## major_key_tonic

```python
def major_key_tonic(count: int) -> Note
```

Return the tonic of the major key with a given number of sharps or flats.

**Parameters**

- `count` (*int*): Sharps (positive) or flats (negative) in the key signature, from -7 to 7.

**Returns**

- *Note*: The tonic, in octave 4.

**Raises**

- *KeyError*: If `count` is outside -7..7.

**Examples**

```pycon
>>> str(major_key_tonic(2))  # two sharps: D major
'D4'
>>> str(major_key_tonic(-3))  # three flats: E♭ major
'E♭4'
```

## mode_tonic

```python
def mode_tonic(
    count: int,
    *,
    mode: str,
) -> Note
```

Return the note a scale in a given mode starts on, for a given key signature.

The notes of a mode are those of a major scale started from another degree. D Dorian, for example, has the key
signature of C major, started from its second note.

**Parameters**

- `count` (*int*): Sharps (positive) or flats (negative) in the key signature, from -7 to 7.
- `mode` (*str*): A key of `MODE_DEGREE`, such as "Dorian" or "Natural minor (Aeolian)". Keyword-only.

**Returns**

- *Note*: The tonic of that mode, in octave 4 or 5.

**Examples**

```pycon
>>> str(mode_tonic(0, mode="Dorian"))  # no sharps or flats: D Dorian
'D4'
>>> str(mode_tonic(2, mode="Natural minor (Aeolian)"))  # two sharps: B minor
'B4'
```

## arpeggio

```python
def arpeggio(
    root: Note,
    *,
    intervals: list[Interval],
    inversion: int = 0,
) -> list[Note]
```

Return a chord broken and rising from its lowest note, then that note again an octave higher.

**Parameters**

- `root` (*Note*): The root of the chord.
- `intervals` (*list of Interval*): The intervals above the root that make the chord, such as `CHORDS["major"]`. Keyword-only.
- `inversion` (*int, default 0*): How many of the lowest chord tones are moved up an octave first: 0 is root position, 1 puts the third at the bottom, 2 the fifth. Keyword-only.

**Returns**

- *list of Note*: The chord tones from the lowest up, ending on the lowest note an octave higher.

**Examples**

```pycon
>>> [str(n) for n in arpeggio(Note.parse("C4"), intervals=CHORDS["major"])]
['C4', 'E4', 'G4', 'C5']
>>> [str(n) for n in arpeggio(Note.parse("C4"), intervals=CHORDS["major"], inversion=1)]
['E4', 'G4', 'C5', 'E5']
```

## build

```python
def build(
    tonic: Note,
    *,
    intervals: list[Interval],
) -> list[Note]
```

Build the notes of a scale or chord above a tonic.

**Parameters**

- `tonic` (*Note*): The first note.
- `intervals` (*list of Interval*): The intervals above the tonic, including the unison, such as a value of `SCALES` or `CHORDS`. Keyword-only.

**Returns**

- *list of Note*: The tonic transposed by each interval, in order.

**Examples**

```pycon
>>> [str(n) for n in build(Note.parse("G4"), intervals=SCALES["Major (Ionian)"])]
['G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F♯5']
```

## key_signature

```python
def key_signature(
    tonic_name: str,
    *,
    scale: str = 'Major (Ionian)',
) -> int
```

Return the key signature of a scale as a signed count of accidentals.

**Parameters**

- `tonic_name` (*str*): The tonic in plain text without an octave, such as 'G', 'Eb' or 'F#'.
- `scale` (*str, default "Major (Ionian)"*): A key of `SCALES`. Keyword-only.

**Returns**

- *int*: The sum of the accidentals of the scale's notes: positive for sharps, negative for flats.

**Examples**

```pycon
>>> key_signature("G")  # G major has one sharp
1
>>> key_signature("Eb")  # E♭ major has three flats
-3
>>> key_signature("A", scale="Natural minor (Aeolian)")  # A minor has none
0
```

## format_key_signature

```python
def format_key_signature(count: int) -> str
```

Describe a key signature in words.

**Parameters**

- `count` (*int*): Sharps (positive) or flats (negative).

**Returns**

- *str*: For example '1 sharp', '3 flats' or 'no sharps or flats'.

**Examples**

```pycon
>>> format_key_signature(0)
'no sharps or flats'
>>> format_key_signature(1)
'1 sharp'
>>> format_key_signature(-3)
'3 flats'
```

## all_tonics

```python
def all_tonics(max_accidentals: int = 1) -> list[Note]
```

Return every spelled tonic in octave 4, within a limit on accidentals.

**Parameters**

- `max_accidentals` (*int, default 1*): The most sharps or flats a tonic may have, so 1 allows C♭ through B♯ but not double sharps.

**Returns**

- *list of Note*: Each letter with each accidental from `-max_accidentals` to `max_accidentals`, letters in the order C to B.

**Examples**

```pycon
>>> len(all_tonics())
21
>>> [str(n) for n in all_tonics(0)]
['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4']
```
{% endraw %}
