---
title: alto.exercises.library
parent: api
package: alto.exercises
order: 5
permalink: /api/alto.exercises.library/
---
{% raw %}
The exercises: note names, intervals, key signatures, scales, chords, arpeggios, keyboard keys and note construction.

Each class makes one kind of `Question` and registers itself with `@register`, so importing this module is what adds
the exercises to the home screen.

**Examples**

```pycon
>>> from alto.exercises import REGISTRY
>>> [cls.name for cls in REGISTRY][:3]
['Note Identification', 'Keyboard Identification', 'Note Construction']
```

## NoteNames

```python
NoteNames(accidentals: bool = False)
```

Bases: `Exercise`

Name the note shown on a staff.

**Examples**

```pycon
>>> q = NoteNames().generate(random.Random(1))
>>> len(q.staff), q.answer in q.choices
(1, True)
```

**Constructor**

Create the exercise.

**Parameters**

- `accidentals` (*bool, default False*): Ask notes with explicit sharps, flats and naturals, whatever the settings say.

**Constructor examples**

```pycon
>>> NoteNames(accidentals=True).accidentals
True
```

### NoteNames.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape these questions.

**Returns**

- *str*: The clefs, ranges, key signatures, note values and naming in force, and whether accidentals are asked.

**Examples**

```pycon
>>> NoteNames().settings_signature() != NoteNames(accidentals=True).settings_signature()
True
```

### NoteNames.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "Press the button with its name" in NoteNames().instructions()
True
```

### NoteNames.generate

```python
def generate(rng: random.Random) -> Question
```

Make a note to name, on one of the chosen clefs, in a chosen key.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: The note drawn on a staff, with one button for each name that could be the answer.

**Examples**

```pycon
>>> q = NoteNames().generate(random.Random(2))
>>> q.clef in ("treble", "bass", "alto", "tenor", "soprano", "mezzo", "baritone", "grand")
True
```

## IntervalNames

```python
class IntervalNames(Exercise)
```

Name the interval between two notes, up to an octave.

**Attributes**

- `QUALITIES` (*dict of int to str*): For each interval number, the qualities that can occur, separated by spaces.

**Examples**

```pycon
>>> q = IntervalNames().generate(random.Random(3))
>>> len(q.staff), q.answer in q.choices
(2, True)
```

### IntervalNames.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "quality followed by a number" in IntervalNames().instructions()
True
```

### IntervalNames.generate

```python
def generate(rng: random.Random) -> Question
```

Make two notes whose interval is to be named.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: The lower and higher note on a staff, and the interval (such as 'M3' or 'P5') as the answer.

**Examples**

```pycon
>>> q = IntervalNames().generate(random.Random(4))
>>> q.answer[0] in "PMmAd" and q.answer[1:].isdigit()
True
```

## KeySignatures

```python
class KeySignatures(Exercise)
```

Read a key signature, or count the sharps and flats of a named key.

**Examples**

```pycon
>>> q = KeySignatures().generate(random.Random(5))
>>> q.answer in q.choices
True
```

### KeySignatures.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape these questions.

**Returns**

- *str*: The kinds of question, clefs, scales and key signatures in force.

**Examples**

```pycon
>>> KeySignatures().settings_signature().startswith("[")
True
```

### KeySignatures.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "Key signatures" in KeySignatures().instructions()
True
```

### KeySignatures.generate

```python
def generate(rng: random.Random) -> Question
```

Make a key signature to read, or a key whose sharps and flats are to be counted.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: Either a signature on a staff (answer: the tonic) or a named key (answer: how many sharps or flats).

**Examples**

```pycon
>>> q = KeySignatures().generate(random.Random(6))
>>> q.show_staff or "How many sharps or flats" in q.prompt
True
```

## ScaleDegrees

```python
class ScaleDegrees(Exercise)
```

Spell a note of a scale or mode from its tonic.

**Examples**

```pycon
>>> q = ScaleDegrees().generate(random.Random(7))
>>> q.prompt.startswith("In ") and q.answer in q.choices
True
```

### ScaleDegrees.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "degree" in ScaleDegrees().instructions()
True
```

### ScaleDegrees.generate

```python
def generate(rng: random.Random) -> Question
```

Make a question asking for one degree of a scale.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: For example 'In E♭ Dorian, what is scale degree 6?', answered 'C'.

**Examples**

```pycon
>>> q = ScaleDegrees().generate(random.Random(8))
>>> "scale degree" in q.prompt
True
```

## ChordQualities

```python
class ChordQualities(Exercise)
```

Identify the quality of a triad or seventh chord in root position.

**Examples**

```pycon
>>> q = ChordQualities().generate(random.Random(9))
>>> len(q.staff[0]) in (3, 4) and q.answer in q.choices
True
```

### ChordQualities.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "root position" in ChordQualities().instructions()
True
```

### ChordQualities.generate

```python
def generate(rng: random.Random) -> Question
```

Make a chord in root position whose quality is to be named.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: The chord drawn as one stack of notes, with its type (such as 'minor 7th') as the answer.

**Examples**

```pycon
>>> q = ChordQualities().generate(random.Random(10))
>>> q.answer in CHORDS
True
```

## ArpeggioNames

```python
class ArpeggioNames(Exercise)
```

Name the type and the inversion of a broken chord.

**Examples**

```pycon
>>> q = ArpeggioNames().generate(random.Random(11))
>>> q.octaves is not None and len(q.staff) >= 4
True
```

### ArpeggioNames.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape these questions.

**Returns**

- *str*: The clefs, chord types, inversions and key signatures in force.

**Examples**

```pycon
>>> ArpeggioNames().settings_signature().startswith("[")
True
```

### ArpeggioNames.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML.

**Examples**

```pycon
>>> "inversion" in ArpeggioNames().instructions()
True
```

### ArpeggioNames.generate

```python
def generate(rng: random.Random) -> Question
```

Make an arpeggio on one of the chosen clefs, in a chosen position.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: The arpeggio's notes one after another on a staff; the answer is the chord type and inversion, such as 'major · 1st inversion'.

**Raises**

- *RuntimeError*: If no arpeggio fits the chosen clefs, chord types and inversions.

**Examples**

```pycon
>>> q = ArpeggioNames().generate(random.Random(12))
>>> " · " in q.answer
True
```

## KeyboardNotes

```python
class KeyboardNotes(Exercise)
```

Name the highlighted key on a piano keyboard.

**Examples**

```pycon
>>> q = KeyboardNotes().generate(random.Random(13))
>>> q.keyboard is not None and q.answer in q.choices
True
```

### KeyboardNotes.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape these questions.

**Returns**

- *str*: The keyboard range, black keys, octave and key signature settings, and the naming in force.

**Examples**

```pycon
>>> KeyboardNotes().settings_signature().startswith("[")
True
```

### KeyboardNotes.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML, with paragraphs added for the octave and key signature settings that are on.

**Examples**

```pycon
>>> "highlighted" in KeyboardNotes().instructions()
True
```

### KeyboardNotes.generate

```python
def generate(rng: random.Random) -> Question
```

Make a keyboard with one key highlighted.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: The keyboard, a grid of name buttons (and a row of octave buttons if octaves are asked), and the key's name as the answer, with the other spelling of a black key accepted.

**Examples**

```pycon
>>> q = KeyboardNotes().generate(random.Random(14))
>>> # noinspection PyUnresolvedReferences
>>> q.keyboard_range[0] <= q.keyboard.midi <= q.keyboard_range[1]
True
```

## NoteConstruction

```python
class NoteConstruction(Exercise)
```

Place a named note on the staff.

**Examples**

```pycon
>>> q = NoteConstruction().generate(random.Random(15))
>>> q.construct is not None and q.prompt.startswith("Place ")
True
```

### NoteConstruction.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape these questions.

**Returns**

- *str*: The clefs, accidentals and key signature settings, and the naming in force.

**Examples**

```pycon
>>> NoteConstruction().settings_signature().startswith("[")
True
```

### NoteConstruction.instructions

```python
def instructions() -> str
```

Return the help text for the exercise.

**Returns**

- *str*: Simple HTML, with paragraphs added for the key signature and accidental settings that are on.

**Examples**

```pycon
>>> "Click the staff" in NoteConstruction().instructions()
True
```

### NoteConstruction.generate

```python
def generate(rng: random.Random) -> Question
```

Make a note name to be placed on the staff.

**Parameters**

- `rng` (*random.Random*): The random number generator.

**Returns**

- *Question*: A prompt such as 'Place F♯4 on the staff.'; the answer is the note's name, and `construct` is the note to place.

**Examples**

```pycon
>>> q = NoteConstruction().generate(random.Random(16))
>>> q.answer in q.prompt
True
```
{% endraw %}
