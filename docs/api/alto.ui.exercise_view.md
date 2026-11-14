---
title: alto.ui.exercise_view
parent: api
package: alto.ui
order: 19
permalink: /api/alto.ui.exercise_view/
---
{% raw %}
The exercise screen: a question, its answer buttons, the score, and a pane of settings that slides in from the right.

One `ExerciseView` works for every exercise. It asks the exercise (or, with a profile, the learner) for the next
`Question`, shows it as a staff, a keyboard or text, offers the answer buttons, and records each answer.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> view = ExerciseView(NoteNames(), rng=random.Random(1))
>>> # noinspection PyUnresolvedReferences
>>> view.question.answer in [button.text() for button in view.buttons]
True
```

## ExerciseView

```python
ExerciseView(
    exercise: Exercise,
    *,
    rng: random.Random | None = None,
    parent: QWidget | None = None,
    learner: Learner | None = None,
)
```

Bases: `QWidget`

The screen for practising one exercise.

**Attributes**

- `PANE_WIDTH` (*int*): The width of the settings pane when it is open, in pixels.
- `exercise` (*Exercise*): The exercise being practised.
- `learner` (*Learner or None*): Records every answer and chooses what to ask next; None asks at random.
- `rng` (*random.Random*): The random number generator for new questions.
- `correct` (*int*): Questions answered right first time.
- `total` (*int*): Questions answered.
- `streak` (*int*): Right answers in a row.
- `question` (*Question or None*): The question on screen.
- `answered` (*bool*): True once the question has been answered right.
- `missed` (*bool*): True once the question has been answered wrong, so it no longer counts towards the score.
- `buttons` (*list of QPushButton*): The answer buttons on screen.
- `settings_panel` (*QWidget or None*): The exercise's settings, or None for an exercise with none.
- `staff` (*StaffWidget*): Shows the notes of a question.
- `keyboard` (*KeyboardWidget*): Shows the key of a keyboard question.
- `input_staff` (*StaffInput*): The staff to click, for "place this note" questions.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> view = ExerciseView(NoteNames(), rng=random.Random(1))
>>> view.score.text()
'0/0 (–)   streak 0'
```

**Constructor**

Build the screen and show the first question.

**Parameters**

- `exercise` (*Exercise*): The exercise to practise.
- `rng` (*random.Random or None, default None*): The random number generator; a fresh one if None. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the screen. Keyword-only.
- `learner` (*Learner or None, default None*): Where to record answers and what to ask next; None asks at random and records nothing. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.exercises.library import KeySignatures
>>> view = ExerciseView(KeySignatures(), rng=random.Random(2))
>>> view.settings_panel is not None  # the exercise has settings behind the gear button
True
```

### ExerciseView.next_question

```python
def next_question() -> None
```

Show the next question: its staff, keyboard or text, and a fresh set of answer buttons.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> view = ExerciseView(NoteNames(), rng=random.Random(1))
>>> view.next_question()
>>> # noinspection PyUnresolvedReferences
>>> view.answered, len(view.buttons) == len(view.question.choices)
(False, True)
```

### ExerciseView.submit

```python
def submit(
    choice: str,
    *,
    button: QPushButton,
) -> None
```

Check an answer chosen with a button.

A right answer is scored, fades green, plays (unless the exercise is silent) and moves on after a moment; a wrong one
fades red and its button is switched off, so another can be tried.

**Parameters**

- `choice` (*str*): The text of the button that was pressed.
- `button` (*QPushButton*): The button. Nothing happens if it is switched off. Keyword-only.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> sounds.enabled = False
>>> view = ExerciseView(NoteNames(), rng=random.Random(1))
>>> question = view.question
>>> # noinspection PyUnresolvedReferences
>>> wrong = next(b for b in view.buttons if b.text() != question.answer)
>>> view.submit(wrong.text(), button=wrong)
>>> view.missed, wrong.isEnabled()
(True, False)
>>> # noinspection PyUnresolvedReferences
>>> right = next(b for b in view.buttons if b.text() == question.answer)
>>> # noinspection PyUnresolvedReferences
>>> view.submit(question.answer, button=right)
>>> view.answered
True
>>> view._advance.stop()
>>> sounds.enabled = True
```
{% endraw %}
