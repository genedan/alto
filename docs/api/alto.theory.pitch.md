---
title: alto.theory.pitch
parent: api
package: alto.theory
order: 10
permalink: /api/alto.theory.pitch/
---
{% raw %}
Pitches and intervals, spelled correctly (C# is not Db).

A `Note` is a pitch with its spelling (a letter, an accidental and an octave), so C♯4 and D♭4 are different notes even
though they sound the same. An `Interval` is a distance between two spelled notes, such as a major third or a perfect
fifth. Together they can transpose a note by an interval and work out the interval between two notes.

**Examples**

```pycon
>>> c4 = Note.parse("C4")
>>> str(c4.transpose(Interval.parse("M3")))
'E4'
>>> Interval.between(c4, high=Note.parse("G4"))
Interval(number=5, quality='P')
```

## Note

```python
Note(
    octave: int,
    *,
    letter: int,
    accidental: int = 0,
)
```

A spelled pitch: a letter name, an accidental and an octave.

The spelling matters. C♯4 and D♭4 sound the same (they share a MIDI number) but are different notes, because they sit on
different lines of the staff.

**Attributes**

- `octave` (*int*): The octave in scientific pitch notation, where middle C is C4.
- `letter` (*int*): An index into `LETTERS`: 0 is C, 1 is D, 2 is E, 3 is F, 4 is G, 5 is A and 6 is B. Keyword-only.
- `accidental` (*int, default 0*): -2 for a double flat, -1 for a flat, 0 for a natural, 1 for a sharp and 2 for a double sharp. Keyword-only.

**Examples**

```pycon
>>> middle_c = Note(4, letter=0)
>>> middle_c.midi
60
>>> str(Note(4, letter=3, accidental=1))
'F♯4'
>>> Note(4, letter=0) < Note(4, letter=1)
True
```

### Note.midi

```python
@property
def midi() -> int
```

Return the MIDI note number, where middle C (C4) is 60.

**Returns**

- *int*: The number of semitones above C-1.

**Examples**

```pycon
>>> Note(4, letter=0).midi
60
>>> Note(4, letter=1, accidental=-1).midi  # D♭4 sounds like C♯4
61
```

### Note.diatonic

```python
@property
def diatonic() -> int
```

Return the absolute staff-step index of the note, ignoring its accidental.

Counting from C0 as 0, D0 as 1 and so on, each line or space of the staff is one step. The distance between two notes in
staff steps is the difference of their indexes.

**Returns**

- *int*: `octave * 7 + letter`.

**Examples**

```pycon
>>> Note(4, letter=0).diatonic  # C4
28
>>> Note(4, letter=2, accidental=1).diatonic  # E♯4 is on the same step as E4
30
```

### Note.pitch_class

```python
@property
def pitch_class() -> int
```

Return the pitch class: the note's MIDI number modulo 12.

**Returns**

- *int*: A number from 0 (C) to 11 (B), the same for every octave and for enharmonic spellings.

**Examples**

```pycon
>>> Note(4, letter=0, accidental=1).pitch_class  # C♯4
1
>>> Note(3, letter=6, accidental=1).pitch_class  # B♯3 sounds like C
0
```

### Note.name

```python
@property
def name() -> str
```

Return the pitch-class name with Unicode accidentals, without the octave.

**Returns**

- *str*: The letter followed by ♭, ♯, 𝄫 or 𝄪 where the note has an accidental.

**Examples**

```pycon
>>> Note(4, letter=3, accidental=1).name
'F♯'
>>> Note(4, letter=3).name
'F'
```

### Note.from_diatonic

```python
@classmethod
def from_diatonic(
    diatonic: int,
    *,
    accidental: int = 0,
) -> Note
```

Build a note from an absolute staff-step index.

**Parameters**

- `diatonic` (*int*): The index, counting C0 as 0 (see `Note.diatonic`).
- `accidental` (*int, default 0*): The accidental to give the note. Keyword-only.

**Returns**

- *Note*: The note on that staff step with that accidental.

**Examples**

```pycon
>>> Note.from_diatonic(30)
Note(octave=4, letter=2, accidental=0)
>>> str(Note.from_diatonic(30, accidental=-1))
'E♭4'
```

### Note.parse

```python
@classmethod
def parse(text: str) -> Note
```

Parse a note written in plain text, such as 'F#4', 'Bb3' or 'Ebb2'.

**Parameters**

- `text` (*str*): A letter A-G (either case), then an accidental ('#' for a sharp, 'b' for a flat, 'bb' for a double flat, 'x' for a double sharp, or nothing for a natural), then the octave number.

**Returns**

- *Note*: The spelled note.

**Raises**

- *ValueError*: If the letter is not A-G, or the octave is missing.
- *KeyError*: If the accidental is not one of '', '#', 'b', 'bb' or 'x'.

**Examples**

```pycon
>>> Note.parse("F#4")
Note(octave=4, letter=3, accidental=1)
>>> Note.parse("Bb3")
Note(octave=3, letter=6, accidental=-1)
>>> Note.parse("H4")
Traceback (most recent call last):
    ...
ValueError: substring not found
```

### Note.transpose

```python
def transpose(
    interval: Interval,
    *,
    descending: bool = False,
) -> Note
```

Move the note up or down by an interval, keeping the spelling correct.

**Parameters**

- `interval` (*Interval*): How far to move. Its number decides the letter and its quality decides the accidental.
- `descending` (*bool, default False*): Move down instead of up. Keyword-only.

**Returns**

- *Note*: The new note. For example a major third above C is E, and a minor third above C is E♭, never D♯.

**Examples**

```pycon
>>> str(Note.parse("C4").transpose(Interval.parse("M3")))
'E4'
>>> str(Note.parse("C4").transpose(Interval.parse("m3")))
'E♭4'
>>> str(Note.parse("C4").transpose(Interval.parse("P5"), descending=True))
'F3'
```

## Interval

```python
Interval(
    number: int,
    *,
    quality: str,
)
```

A simple or compound interval between two spelled notes.

**Attributes**

- `number` (*int*): The size counting both end notes: 1 is a unison, 3 a third, 8 an octave, 9 a ninth and so on.
- `quality` (*str*): One of 'dd' (doubly diminished), 'd' (diminished), 'm' (minor), 'M' (major), 'P' (perfect), 'A' (augmented) and 'AA' (doubly augmented). Keyword-only. Unisons, fourths, fifths and octaves are perfect, the others major or minor.

**Examples**

```pycon
>>> Interval(3, quality="M").semitones
4
>>> str(Interval.parse("P5"))
'P5'
```

### Interval.is_perfect_type

```python
@property
def is_perfect_type() -> bool
```

Report whether this size of interval is "perfect type" (unison, fourth, fifth, octave) rather than major or minor type.

**Returns**

- *bool*: True for unisons, fourths, fifths and octaves (and their compounds), False for seconds, thirds, sixths and sevenths.

**Examples**

```pycon
>>> Interval.parse("P5").is_perfect_type
True
>>> Interval.parse("M3").is_perfect_type
False
```

### Interval.semitones

```python
@property
def semitones() -> int
```

Return the size of the interval in semitones.

**Returns**

- *int*: The distance in half steps, including whole octaves for compound intervals.

**Examples**

```pycon
>>> Interval.parse("M3").semitones
4
>>> Interval.parse("d5").semitones
6
>>> Interval.parse("m9").semitones  # a minor ninth is an octave plus a minor second
13
```

### Interval.short

```python
@property
def short() -> str
```

Return the interval in short form: its quality followed by its number.

**Returns**

- *str*: For example 'M3', 'P5' or 'd7'.

**Examples**

```pycon
>>> Interval(7, quality="m").short
'm7'
```

### Interval.between

```python
@classmethod
def between(
    low: Note,
    *,
    high: Note,
) -> Interval
```

Work out the interval from one note up to a higher one.

**Parameters**

- `low` (*Note*): The lower note.
- `high` (*Note*): The higher note. It must not be below `low`. Keyword-only.

**Returns**

- *Interval*: The spelled interval, such as a major third (C4 up to E4) or an augmented fourth (C4 up to F♯4).

**Examples**

```pycon
>>> Interval.between(Note.parse("C4"), high=Note.parse("E4"))
Interval(number=3, quality='M')
>>> Interval.between(Note.parse("C4"), high=Note.parse("F#4")).short
'A4'
```

### Interval.parse

```python
@classmethod
def parse(text: str) -> Interval
```

Parse an interval written in short form, such as 'M3', 'P5' or 'd7'.

**Parameters**

- `text` (*str*): The quality (one of dd, d, m, M, P, A, AA) followed by the number.

**Returns**

- *Interval*: The interval.

**Examples**

```pycon
>>> Interval.parse("m7")
Interval(number=7, quality='m')
>>> Interval.parse("P8").semitones
12
```

## key_accidental

```python
def key_accidental(
    letter: int,
    *,
    count: int,
) -> int
```

Return the accidental a key signature applies to a letter.

**Parameters**

- `letter` (*int*): An index into `LETTERS` (0 is C, 6 is B).
- `count` (*int*): The key signature: that many sharps if positive, that many flats if negative. Keyword-only.

**Returns**

- *int*: 1 if the signature sharpens the letter, -1 if it flattens it, 0 if it leaves it natural.

**Examples**

```pycon
>>> key_accidental(3, count=1)  # F in G major
1
>>> key_accidental(6, count=-1)  # B in F major
-1
>>> key_accidental(0, count=1)  # C in G major
0
```
{% endraw %}
