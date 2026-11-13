---
title: Building an exercise
parent: guide
order: 9
permalink: /guide/exercises/
---
This chapter follows one new exercise from idea to published documentation, then covers the harder cases: exercises with
settings, with a staff, a keyboard, a second row of buttons, or a note to place. The short version of the steps is in
[For developers]({{ '/development/' | relative_url }}); here are the reasons.

## What an exercise is

An `Exercise` is a small class with four attributes and one method that matter. Everything else comes from the framework.

| | |
|---|---|
| `name`, `category`, `description` | What the home screen and the sidebar show. The category groups exercises. |
| `par_seconds` | How long a good *first* answer takes. The scheduler judges speed against it. |
| `generate(rng)` | Returns one `Question`. This is the whole of the exercise. |
| `settings_signature()` | Only for exercises with settings (see below). |

A `Question` says everything about one question. Its fields are the whole vocabulary of what the screen can show:

| Field | Meaning |
|---|---|
| `prompt` | The text above the question (may be empty). |
| `choices` | The answer buttons, in order. |
| `answer` | The right answer; it must be one of `choices`. |
| `staff` | Notes to draw: a list of chords, each a list of `Note`s. Empty for no staff. |
| `clef`, `key`, `value` | The clef, the key signature (sharps positive, flats negative) and the note value to draw. |
| `keyboard`, `key_staff`, `keyboard_range` | Highlight a piano key instead of drawing a staff; optionally with a small key signature above; and the range of keys to draw. |
| `octaves`, `second_label`, `joiner` | A two-part answer: a choice, then one of a second row of buttons ("C" then "4" gives "C4"). |
| `construct`, `accidentals` | A "place this note" question: the answer is a position on a clickable staff, not a button. |
| `grid` | Where to put each button, as `(row, column)`, instead of one row. |
| `explanation` | Text shown after the answer says why it is right. |

Because an exercise only fills in a `Question`, it never touches Qt.

## A complete example

We will add "Sharps and flats": it names a major key and asks how many sharps or flats it has. This code runs as written.

```python
import random

from alto.exercises.base import (
    Exercise,
    Question,
    register,
)
from alto.theory.scales import (
    MAJOR_KEYS,
    format_key_signature,
)


@register
class SharpsAndFlats(Exercise):
    name = "Sharps and flats"
    category = "Notation"
    description = "How many sharps or flats does a major key have?"
    par_seconds = 4.0

    def generate(self, rng: random.Random) -> Question:
        count = rng.randint(-7, 7)  # -7 flats ... +7 sharps
        return Question(
            f"How many sharps or flats are in {MAJOR_KEYS[count]} major?",
            choices=[format_key_signature(n) for n in range(-7, 8)],
            answer=format_key_signature(count),
            explanation=f"{MAJOR_KEYS[count]} major has {format_key_signature(count)}.",
        )
```

To try it without the program, in a Python session:

```pycon
>>> q = SharpsAndFlats().generate(random.Random(1))
>>> q.prompt, q.answer
('How many sharps or flats are in D♭ major?', '5 flats')
```

and to see it in a window:

```python
from PySide6.QtWidgets import QApplication
from alto.ui.exercise_view import ExerciseView

app = QApplication([])
view = ExerciseView(SharpsAndFlats(), rng=random.Random(1))
view.show()
app.exec()
```

Things to notice:

- **`rng` is an argument, not a global.** The exercise never calls `random.randint`. That is what makes the example above repeatable
  and the exercise testable with a seed.
- **`@register`** puts the class in `REGISTRY` next to the other exercises of its `category`, so the home screen and the sidebar
  list it with them, whatever order the file is written in. Pick an existing category or invent a new one.
- **Choices must be unique and the answer must be one of them.** A test, `test_every_exercise_generates_valid_questions`, draws 300
  questions from *every registered exercise* and checks both. A new exercise is covered the moment it is registered.
- **Distractors.** The wrong answers matter as much as the right one. `pick_distractors(correct, pool=..., n=..., rng=...)` in
  `base.py` returns the right answer shuffled in with `n` others drawn from a pool; use it, or write your own, with plausible
  wrong answers (for intervals: the neighbouring qualities, not random words). A question where only one answer is
  conceivable teaches nothing.
- **Where the logic lives.** Anything about music itself (spelling, intervals, scales) belongs in `alto/theory/`, with tests,
  and is *used* by the exercise. If your `generate` contains theory, move it.

## Calibrating `par_seconds`

`par_seconds` is the time a fluent person takes to answer correctly the *first* time. The scheduler rewards answers at half par
or faster and penalises answers over four times par. Too small and everything looks slow, so strain rises for everyone; too large
and nothing is ever rewarded. A good method: answer fifty questions yourself in a row, at the speed you would call "fluent", and
take the median of your answer times (the statistics page shows the median per exercise). The existing exercises run from 3 seconds
(naming a note) to 9 (naming an arpeggio's type and inversion); scale spelling is 8. See [Spaced repetition]({{ '/guide/spaced-repetition/' | relative_url }}).

## Adding settings to an exercise

If users should be able to change what is asked, there are four more places to touch. The `NoteNames` exercise is the model.

1. **A settings object** in `alto/settings.py`: a dataclass with the fields and the rules about them, and a module-level instance
   (`note_names = NoteNameSettings()`). Keep it free of Qt and of saving.
2. **The exercise reads it** when it generates a question: `settings.note_names.active_clefs()`. Because the instance is shared,
   a change takes effect on the next question.
3. **A signature.** Override `settings_signature()` to return `signature(settings.note_names, ...)`. This is what stops a
   stored question from coming back under settings it was not made for. It is the step people forget, and nothing fails visibly:
   old questions simply reappear when they should not.
4. **A panel and persistence** in `alto/ui/settings_panel.py`: a panel class (a subclass of `ExerciseSettingsPanel` that emits
   `changed` when something is edited), `load_*` and `save_*` functions that read and write `QSettings` through
   `store()` with `text_value` and `int_value`, a branch in `settings_panel_for`, and a call to your `load_*` in
   `MainWindow.__init__` so settings are restored at start. The screen connects `changed` to `next_question`, so edits apply
   at once.

The panel is the largest piece of code in the program, and that is mostly widgets: copy a panel with a similar shape (for
a menu of pages, `ArpeggioSettingsPanel`) and change it.

## Showing a staff, a keyboard or a clickable staff

Fill in the fields and the screen does the rest.

- **A note on a staff:** `staff=[[note]]`, `clef="treble"`. Several notes at once (a chord) go in one inner list; several columns
  in sequence (an arpeggio) are several inner lists.
- **A key signature:** `key=3` for three sharps. The staff draws it after the clef.
- **A piano key:** `keyboard=note`, and `keyboard_range=(low_midi, high_midi)` to show only a span. `key_staff=True` adds a small
  key-signature staff above the keyboard.
- **Place a note:** `construct=note` and `choices=[]`. The user clicks the staff, `StaffInput.note_at` turns the click into a
  `Note`, and `Question.check_placed` compares it, spelling and octave included (G♯4 is not A♭4). Set `accidentals=True` to show
  the sharp, flat and natural buttons.
- **A two-part answer:** `choices=["C", "D", ...]`, `octaves=["3", "4", "5"]`, `joiner=""`, so the right answer is the choice
  joined to the octave. The screen shows two rows and submits when both are chosen.

If your question needs something the fields cannot say, the right move is to add a field to `Question` (with a default, so old
stored questions still load), teach `ExerciseView` to draw it, and add it to `to_dict`/`from_dict`. Decide whether it belongs in
`item_key()`: if two questions that differ in the new field are different questions, it does.

## The icon

The home screen shows an icon per exercise. `alto/ui/home.py` has `EXERCISE_ICONS`, a dictionary from the exercise's *class name* to
an SVG snippet in `alto/ui/icons.py` (a 24-by-24 drawing whose fill is the word `COLOR`). An exercise with no entry gets a default,
which `tests/test_main_window.py` checks. Make a simple monochrome icon in an SVG editor such as Inkscape, copy the path data into
a new constant, and add the dictionary entry.

## Documenting it

1. **A section in `docs/exercises.md`** that says what is shown, what to press, and what the settings do. Write it for a user.
2. **A screenshot** if you want one: add a name to `SHOTS` in `scripts/screenshots.py`, write the few lines that open your
   exercise and call `save(window, name="your-name")`, include it in the page the way the other pages do (copy a line that uses the `shot.html` include),
   and run `python scripts/screenshots.py --only your-name`. `tests/test_docs.py` checks that every picture a page shows exists in
   both themes.
3. **The instructions** shown behind the "?" button: override `instructions()` to return a little HTML.
4. **The API reference:** run `python scripts/api_docs.py`.
5. **A line in `ARCHITECTURE.md`** only if the exercise changes the picture of how the program fits together.

## Testing it

Write the tests that the existing exercises have:

- **A generation test:** seed an `rng`, draw some questions, and assert on what you can predict (the answer is in the choices; a
  question for G major shows one sharp).
- **A settings test:** change a setting in the test (tests start from the defaults and restore them afterwards) and check the
  questions follow it.
- **A screen test:** build an `ExerciseView(YourExercise(), rng=random.Random(1))`, click an answer, and check the score. The
  `tests/test_exercise_view.py` helpers `view_of` and `asked` do the work; set `sounds.enabled = False` in any test that submits
  an answer, or it will try to play.
- **A docstring** with an example for every function, which `tests/test_docstrings.py` demands and `pytest` then runs.

## Further reading

- *Fluent Python* (see [Python beyond the basics]({{ '/guide/python/' | relative_url }})) on abstract base classes and decorators
  for the framework side.
- Music theory references for exercise content: Stefan Kostka and Dorothy Payne, *Tonal Harmony*, 7th ed. (McGraw-Hill, 2013), and
  Edward Aldwell, Carl Schachter and Allen Cadwallader, *Harmony and Voice Leading*, 4th ed. (Schirmer, 2011). They agree on terms,
  and when they disagree, that is a sign the exercise needs a setting.
- Thomas M. Haladyna, *Developing and Validating Multiple-Choice Test Items*, 3rd ed. (Lawrence Erlbaum, 2004): the standard
  book on writing good questions and, above all, good distractors.
