---
title: alto.exercises.base
parent: api
package: alto.exercises
order: 4
permalink: /api/alto.exercises.base/
---
{% raw %}
Exercise framework. To add an exercise: subclass Exercise, decorate with @register.

An `Exercise` makes `Question` objects. The `Question` says what to show (a staff, a keyboard or only text), which
buttons to offer and which answer is right. The exercise screen and the scheduler work with those two classes only, so
a new exercise needs no new interface code.

**Examples**

```pycon
>>> question = Question("Name this note.", choices=["C", "D", "E"], answer="D")
>>> question.check("D"), question.check("E")
(True, False)
```

## Question

```python
Question(
    prompt: str,
    *,
    choices: list[str],
    answer: str,
    staff: list[list[Note]] = field(default_factory=list),
    clef: str = 'treble',
    explanation: str = '',
    key: int = 0,
    value: str = 'whole',
    grid: dict[str, tuple[int, int]] | None = None,
    keyboard: Note | None = None,
    key_staff: bool = False,
    keyboard_range: tuple[int, int] | None = None,
    octaves: list[str] | None = None,
    second_label: str = 'Octave',
    joiner: str = '',
    construct: Note | None = None,
    accidentals: bool = False,
    accept: tuple[str, ...] = (),
    show_staff: bool = False,
    caption: str = '',
)
```

One question, with what to show for it and which answer is right.

**Attributes**

- `prompt` (*str*): The text shown above the question; may be empty.
- `choices` (*list of str*): The answer buttons, in the order they should be offered. Keyword-only.
- `answer` (*str*): The right answer, one of `choices` (or the note name for a "place this note" question). Keyword-only.
- `staff` (*list of list of Note*): What to draw on the staff: each inner list is one chord or note. Keyword-only.
- `clef` (*str, default "treble"*): The clef to draw on. Keyword-only.
- `explanation` (*str, default ""*): Text shown after the answer to say why it is right. Keyword-only.
- `key` (*int, default 0*): The key signature to draw: that many sharps if positive, flats if negative. Keyword-only.
- `value` (*str, default "whole"*): The note value to draw (single notes only). Keyword-only.
- `grid` (*dict of str to tuple of (int, int) or None*): Where to put each answer button, as (row, column). Without it the choices form one row. Keyword-only.
- `keyboard` (*Note or None*): A piano key to highlight, instead of drawing a staff. Keyword-only.
- `key_staff` (*bool, default False*): Draw `key` as a small key-signature staff above the keyboard. Keyword-only.
- `keyboard_range` (*tuple of (int, int) or None*): The keys (MIDI numbers, inclusive) the keyboard picture should show. Keyword-only.
- `octaves` (*list of str or None*): When set, the answer is a choice button plus one of these second-row buttons. Keyword-only.
- `second_label` (*str, default "Octave"*): What the second row of buttons is called. Keyword-only.
- `joiner` (*str, default ""*): Put between the two parts to make the answer ("" for a note and its octave: C + 4 gives C4). Keyword-only.
- `construct` (*Note or None*): The note to place on the staff: the answer is a position, not a button. Keyword-only.
- `accidentals` (*bool, default False*): Show the sharp, natural and flat buttons for a construct question. Keyword-only.
- `accept` (*tuple of str*): Other answers that count as right, such as the enharmonic name of a black key. Keyword-only.
- `show_staff` (*bool, default False*): Draw the staff even with no notes on it, to show only its clef and key signature. Keyword-only.
- `caption` (*str, default ""*): Text written on the staff itself, under the music, in place of the prompt above it. Keyword-only.

**Examples**

```pycon
>>> q = Question("Which note is this?", choices=["C", "D", "E"], answer="D", staff=[[Note.parse("D4")]])
>>> q.check("D")
True
>>> Question.from_dict(q.to_dict()) == q  # a question can be stored and asked again
True
```

### Question.check_placed

```python
def check_placed(note: Note) -> bool
```

Report whether a note placed on the staff is the one asked for.

The spelling and octave must match exactly, so G♯4 is not A♭4.

**Parameters**

- `note` (*Note*): The note the learner placed.

**Returns**

- *bool*: True if it equals the note in `construct`.

**Examples**

```pycon
>>> q = Question("Place C4", choices=[], answer="C4", construct=Note.parse("C4"))
>>> q.check_placed(Note.parse("C4"))
True
>>> q.check_placed(Note.parse("B#3"))  # sounds the same, but is spelled differently
False
```

### Question.check

```python
def check(choice: str) -> bool
```

Report whether a chosen answer is right.

**Parameters**

- `choice` (*str*): The text of the button that was pressed.

**Returns**

- *bool*: True if it is the answer or one of the other accepted answers.

**Examples**

```pycon
>>> q = Question("", choices=["F♯", "G♭"], answer="F♯", accept=("G♭",))
>>> q.check("F♯"), q.check("G♭"), q.check("A")
(True, True, False)
```

### Question.item_key

```python
def item_key() -> str
```

Return a stable identity for the question, so the same one can be recognised when it comes round again.

It covers what is asked and where it is drawn, but not the note value or the order of the buttons.

**Returns**

- *str*: A 20-character hexadecimal string.

**Examples**

```pycon
>>> a = Question("Name it.", choices=["C", "D"], answer="C")
>>> b = Question("Name it.", choices=["D", "C"], answer="C")  # the same question, buttons in another order
>>> a.item_key() == b.item_key()
True
>>> len(a.item_key())
20
```

### Question.to_dict

```python
def to_dict() -> dict
```

Return the question as plain data, so it can be stored and asked again.

**Returns**

- *dict*: The fields of the question, with notes as dictionaries and tuples as lists.

**Examples**

```pycon
>>> data = Question("Name it.", choices=["C"], answer="C", staff=[[Note.parse("C4")]]).to_dict()
>>> data["answer"], data["staff"]
('C', [[{'octave': 4, 'letter': 0, 'accidental': 0}]])
```

### Question.from_dict

```python
@classmethod
def from_dict(d: dict) -> Question
```

Rebuild a question from the data that `to_dict` made.

**Parameters**

- `d` (*dict*): The stored data. Questions saved by older versions, which may carry a `play` field, are accepted.

**Returns**

- *Question*: The question.

**Examples**

```pycon
>>> q = Question("Name it.", choices=["C", "D"], answer="C", key=2, accept=("D",))
>>> Question.from_dict(q.to_dict()) == q
True
```

## note_from

```python
def note_from(v: dict | None) -> Note | None
```

Rebuild a note from stored data.

**Parameters**

- `v` (*dict or None*): A note as the dictionary `to_dict` stores, or None.

**Returns**

- *Note or None*: The note, or None if `v` was None.

**Examples**

```pycon
>>> note_from({"octave": 4, "letter": 0, "accidental": 0})
Note(octave=4, letter=0, accidental=0)
>>> note_from(None) is None
True
```

## signature

```python
def signature(*parts: object) -> str
```

Describe the exercise settings in force, so a stored question is only asked again under the settings it was made for.

**Parameters**

- `*parts` (*object*): The settings to describe: dataclasses, dictionaries, lists, sets and plain values, nested as needed.

**Returns**

- *str*: A JSON string that is the same for equal settings, however their sets and dictionaries happen to be ordered.

**Examples**

```pycon
>>> signature({"clefs": {"bass", "treble"}}, 3)
'[{"clefs": ["bass", "treble"]}, 3]'
>>> signature({"clefs": {"treble", "bass"}}, 3) == signature({"clefs": {"bass", "treble"}}, 3)
True
```

## Exercise

```python
class Exercise(ABC)
```

What every exercise provides: its name, how it makes questions and how long a good answer takes.

**Attributes**

- `name` (*str*): The title shown on the home screen and in the exercise list.
- `category` (*str*): The heading it is listed under.
- `description` (*str*): One line saying what the exercise is for.
- `par_seconds` (*float, default 5.0*): How long a good first answer takes; much quicker earns credit and much slower counts against the question.
- `has_sound` (*bool, default True*): False for an exercise that makes no sound at all, whatever the sound button says.

**Examples**

```pycon
>>> class Demo(Exercise):
...     name = "Demo"
...     def generate(self, rng):
...         return Question("Pick A.", choices=["A", "B"], answer="A")
>>> Demo().generate(random.Random(0)).answer
'A'
```

### Exercise.settings_signature

```python
def settings_signature() -> str
```

Return what identifies the settings that shape the questions.

A stored question is only asked again while this is unchanged. Exercises with settings override it.

**Returns**

- *str*: An identifier; empty for an exercise with no settings.

**Examples**

```pycon
>>> class Demo(Exercise):
...     def generate(self, rng):
...         return Question("?", choices=["A"], answer="A")
>>> Demo().settings_signature()
''
```

### Exercise.instructions

```python
def instructions() -> str
```

Return the help text shown from the exercise's help button.

Exercises override it to describe themselves.

**Returns**

- *str*: Simple HTML; by default the one-line description.

**Examples**

```pycon
>>> class Demo(Exercise):
...     description = "Spot the note."
...     def generate(self, rng):
...         return Question("?", choices=["A"], answer="A")
>>> Demo().instructions()
'Spot the note.'
```

### Exercise.generate

```python
@abstractmethod
def generate(rng: random.Random) -> Question
```

Make one new question.

**Parameters**

- `rng` (*random.Random*): The random number generator to use, so tests can ask for a repeatable question.

**Returns**

- *Question*: The question.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> q = NoteNames().generate(random.Random(1))
>>> q.answer in q.choices
True
```

## register

```python
def register() -> type[Exercise]
```

Add an exercise to `REGISTRY`, next to the others of its category.

The categories come in the order they first appear, so the home screen and the exercise list can show each category
once, with all its exercises under it. Used as a class decorator.

**Parameters**

- `cls` (*type of Exercise*): The exercise class.

**Returns**

- *type of Exercise*: The same class, so the decorator can be applied to a class definition.

**Examples**

```pycon
>>> @register
... class Demo(Exercise):
...     name = "Demo"
...     category = "A category no other exercise has"
...     def generate(self, rng):
...         return Question("?", choices=["A"], answer="A")
>>> REGISTRY[-1] is Demo
True
>>> REGISTRY.remove(Demo)
```

## pick_distractors

```python
def pick_distractors(
    correct: str,
    *,
    pool: list[str],
    n: int,
    rng: random.Random,
) -> list[str]
```

Choose wrong answers to offer alongside the right one, and shuffle them all.

**Parameters**

- `correct` (*str*): The right answer. It is always in the result.
- `pool` (*list of str*): Where the wrong answers come from; repeats and the right answer are ignored. Keyword-only.
- `n` (*int*): How many wrong answers to include (fewer if the pool has fewer). Keyword-only.
- `rng` (*random.Random*): The random number generator used to choose and shuffle. Keyword-only.

**Returns**

- *list of str*: The right answer and up to `n` others, in a random order.

**Examples**

```pycon
>>> choices_ = pick_distractors("C", pool=["C", "D", "E", "F"], n=2, rng=random.Random(0))
>>> len(choices_), "C" in choices_
(3, True)
```
{% endraw %}
