---
title: alto.learning.learner
parent: api
package: alto.learning
order: 7
permalink: /api/alto.learning.learner/
---
{% raw %}
Ties the profile, the database and the scheduler together for the exercise screen.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> question = learner.pick(NoteNames(), rng=random.Random(1))
>>> question.answer in question.choices
True
```

## Learner

```python
Learner(
    db: Database,
    *,
    profile: Profile,
)
```

Chooses what a profile is asked next and records how it was answered.

**Attributes**

- `FRESH` (*int*): How many new questions are generated for each pick, alongside the ones asked before.
- `db` (*Database*): Where answers and what is known about each question are stored.
- `profile` (*Profile*): Whose answers these are.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> rng = random.Random(2)
>>> question = learner.pick(NoteNames(), rng=rng)
>>> learner.record(NoteNames(), question=question, answer=question.answer, correct=True, attempt_no=1, seconds=2.5)
>>> db.count_attempts(learner.profile.id)
1
```

**Constructor**

Create a learner for one profile.

**Parameters**

- `db` (*Database*): The database to read and write.
- `profile` (*Profile*): The profile that is practising. Keyword-only.

**Constructor examples**

```pycon
>>> database = Database()
>>> learner = Learner(database, profile=database.add_profile("Ada"))
>>> learner.profile.name
'Ada'
```

### Learner.pick

```python
def pick(
    exercise: Exercise,
    *,
    rng: random.Random,
    avoid: str | None = None,
    now: float | None = None,
) -> Question
```

Return the next question: a mix of new ones and ones asked before under the same settings, drawn by weight.

**Parameters**

- `exercise` (*Exercise*): The exercise being practised.
- `rng` (*random.Random*): The random number generator used to make new questions and to draw one. Keyword-only.
- `avoid` (*str or None, default None*): The `item_key` of the question just asked, so it does not come straight back. Keyword-only.
- `now` (*float or None, default None*): The current time as a timestamp; the clock is used if None. Keyword-only.

**Returns**

- *Question*: The question to ask.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> first = learner.pick(NoteNames(), rng=random.Random(3))
>>> second = learner.pick(NoteNames(), rng=random.Random(3), avoid=first.item_key())
>>> second.item_key() != first.item_key()
True
```

### Learner.record

```python
def record(
    exercise: Exercise,
    *,
    question: Question,
    answer: str,
    correct: bool,
    attempt_no: int,
    seconds: float,
    now: float | None = None,
) -> None
```

Log one answer and update what is known about the question.

**Parameters**

- `exercise` (*Exercise*): The exercise being practised.
- `question` (*Question*): The question that was answered. Keyword-only.
- `answer` (*str*): What was answered. Keyword-only.
- `correct` (*bool*): Whether the answer was right. Keyword-only.
- `attempt_no` (*int*): 1 for the first answer to this showing of the question, 2 for the second and so on. Keyword-only.
- `seconds` (*float*): How long the answer took. Keyword-only.
- `now` (*float or None, default None*): When it was answered, as a timestamp; the clock is used if None. Keyword-only.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> q = learner.pick(NoteNames(), rng=random.Random(4))
>>> learner.record(NoteNames(), question=q, answer="?", correct=False, attempt_no=1, seconds=3.0)
>>> learner.record(NoteNames(), question=q, answer=q.answer, correct=True, attempt_no=2, seconds=1.0)
>>> [row["correct"] for row in db.attempts(learner.profile.id)]
[0, 1]
>>> # noinspection PyUnresolvedReferences
>>> db.get_item(learner.profile.id, exercise="NoteNames", item_key=q.item_key()).wrong_attempts
1
```
{% endraw %}
