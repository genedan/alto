---
title: alto.learning.stats
parent: api
package: alto.learning
order: 9
permalink: /api/alto.learning.stats/
---
{% raw %}
Numbers and series for the statistics screen, worked out from the answers in the database. Pure Python, no Qt.

A "question" here is one showing of a question, scored by its first answer: it is right if that answer was right.
Later attempts at the same showing show up as extra attempts per question, not as extra questions.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> for i, ok in enumerate((True, True, False)):
...     db.add_attempt(ada.id, exercise="NoteNames", item_key=str(i), attempt_no=1, answer="C", correct=ok,
...                    duration_ms=2000, answered_at=1000.0 + i)
>>> stats = collect(db, profile_ids=[ada.id], now=1010.0)
>>> stats.questions, stats.first_right
(3, 2)
>>> # noinspection PyTypeChecker
>>> round(stats.accuracy)
67
```

## Bucket

```python
Bucket(
    start: datetime,
    *,
    label: str,
    questions: int = 0,
    first_right: int = 0,
    times: list[float] = field(default_factory=list),
)
```

The answers given in one period (an hour, day, week or month), for the charts.

**Attributes**

- `start` (*datetime*): When the period begins.
- `label` (*str*): What to call the period on a chart axis. Keyword-only.
- `questions` (*int, default 0*): How many questions were answered in it. Keyword-only.
- `first_right` (*int, default 0*): How many of those were right on the first answer. Keyword-only.
- `times` (*list of float*): Seconds to the first answer, one per question. Keyword-only.

**Examples**

```pycon
>>> bucket = Bucket(datetime(2026, 1, 5), label="Jan 5", questions=2, first_right=1, times=[2.0, 4.0])
>>> bucket.accuracy, bucket.median_seconds
(50.0, 3.0)
```

### Bucket.accuracy

```python
@property
def accuracy() -> float | None
```

Return the percentage of questions in the period that were right first time.

**Returns**

- *float or None*: 0 to 100, or None if no questions were answered.

**Examples**

```pycon
>>> Bucket(datetime(2026, 1, 5), label="Jan 5", questions=4, first_right=3).accuracy
75.0
>>> Bucket(datetime(2026, 1, 5), label="Jan 5").accuracy is None
True
```

### Bucket.median_seconds

```python
@property
def median_seconds() -> float | None
```

Return the typical time to a first answer in the period.

**Returns**

- *float or None*: The median, in seconds, or None if no questions were answered.

**Examples**

```pycon
>>> Bucket(datetime(2026, 1, 5), label="Jan 5", times=[1.0, 2.0, 9.0]).median_seconds
2.0
```

## ExerciseStats

```python
ExerciseStats(
    exercise: str,
    *,
    questions: int,
    accuracy: float,
    median_seconds: float,
)
```

How practice is going on one exercise.

**Attributes**

- `exercise` (*str*): The exercise's class name.
- `questions` (*int*): How many questions were answered. Keyword-only.
- `accuracy` (*float*): The percentage right first time. Keyword-only.
- `median_seconds` (*float*): The typical time to a first answer, in seconds. Keyword-only.

**Examples**

```pycon
>>> ExerciseStats("NoteNames", questions=40, accuracy=87.5, median_seconds=3.2).accuracy
87.5
```

## HardQuestion

```python
HardQuestion(
    exercise: str,
    *,
    text: str,
    strain: float,
    seen: int,
    wrong: int,
)
```

A question that needs practice, for the list on the statistics screen.

**Attributes**

- `exercise` (*str*): The exercise's class name.
- `text` (*str*): A short line saying what the question was.  Keyword-only.
- `strain` (*float*): How much practice it needs; higher is more. Keyword-only.
- `seen` (*int*): How many times it was answered. Keyword-only.
- `wrong` (*int*): How many wrong answers it has had. Keyword-only.

**Examples**

```pycon
>>> HardQuestion("NoteNames", text="Treble: G4", strain=4.5, seen=6, wrong=5).wrong
5
```

## Stats

```python
Stats(
    questions: int = 0,
    *,
    first_right: int = 0,
    attempts: int = 0,
    median_seconds: float | None = None,
    practice_seconds: float = 0.0,
    days_practised: int = 0,
    granularity: str = 'day',
    buckets: list[Bucket] = field(default_factory=list),
    by_exercise: list[ExerciseStats] = field(default_factory=list),
    hardest: list[HardQuestion] = field(default_factory=list),
)
```

Everything the statistics screen shows.

**Attributes**

- `questions` (*int, default 0*): How many questions were answered, each counted once.
- `first_right` (*int, default 0*): How many were right on the first answer. Keyword-only.
- `attempts` (*int, default 0*): How many answers were given in all, including repeats. Keyword-only.
- `median_seconds` (*float or None*): The typical time to a first answer. Keyword-only.
- `practice_seconds` (*float, default 0.0*): Time spent practising, with a cap on each answer so leaving the app open does not inflate it. Keyword-only.
- `days_practised` (*int, default 0*): On how many different days there were answers. Keyword-only.
- `granularity` (*str, default "day"*): The size of the chart periods: "hour", "day", "week" or "month". Keyword-only.
- `buckets` (*list of Bucket*): One per period, oldest first. Keyword-only.
- `by_exercise` (*list of ExerciseStats*): One per exercise practised, sorted by name. Keyword-only.
- `hardest` (*list of HardQuestion*): The questions that need most practice. Keyword-only.

**Examples**

```pycon
>>> Stats().accuracy is None  # nothing answered yet
True
>>> Stats(4, first_right=3, attempts=6).attempts_per_question
1.5
```

### Stats.accuracy

```python
@property
def accuracy() -> float | None
```

Return the percentage of questions that were right first time.

**Returns**

- *float or None*: 0 to 100, or None if no questions were answered.

**Examples**

```pycon
>>> Stats(4, first_right=3).accuracy
75.0
```

### Stats.attempts_per_question

```python
@property
def attempts_per_question() -> float | None
```

Return the average number of answers it took per question.

**Returns**

- *float or None*: 1.0 if every question was answered right first time; None if no questions were answered.

**Examples**

```pycon
>>> Stats(4, attempts=5).attempts_per_question
1.25
```

## describe

```python
def describe(question: Question) -> str
```

Return a short line saying what a question was, for the list of questions that need practice.

**Parameters**

- `question` (*Question*): The question to describe.

**Returns**

- *str*: What was shown (notes, a key signature or a keyboard key) and, where that does not already say it, the answer.

**Examples**

```pycon
>>> from alto.exercises.base import Question
>>> describe(Question("What type of chord is this?", choices=["major", "minor"], answer="minor"))
'What type of chord is this? → minor'
```

## daily_counts

```python
def daily_counts(
    db: Database,
    *,
    profile_ids: list[int] | None,
    exercise: str | None = None,
    weeks: int = 53,
    now: float | None = None,
) -> dict[date, int]
```

Return how many questions were answered on each day, for the review heatmap.

Looks back over the last `weeks` calendar weeks up to today, in local time. Days with no answers are left out. It
counts questions (first attempts), not attempts, like everything else here.

**Parameters**

- `db` (*Database*): Where the answers are.
- `profile_ids` (*list of int or None*): The profiles to include; every profile if None. Keyword-only.
- `exercise` (*str or None, default None*): Only this exercise (its class name); every exercise if None. Keyword-only.
- `weeks` (*int, default 53*): How many calendar weeks to look back, counting this one. Keyword-only.
- `now` (*float or None, default None*): The current time as a timestamp; the clock is used if None. Keyword-only.

**Returns**

- *dict of date to int*: The number of questions answered on each day that had any.

**Examples**

```pycon
>>> database = Database()
>>> ada = database.add_profile("Ada")
>>> noon = datetime(2026, 11, 13, 12).timestamp()
>>> for i in range(3):
...     database.add_attempt(ada.id, exercise="NoteNames", item_key=str(i), attempt_no=1, answer="C", correct=True,
...                    duration_ms=1000, answered_at=noon + i)
>>> daily_counts(database, profile_ids=[ada.id], now=noon + 60)
{datetime.date(2026, 11, 13): 3}
```

## collect

```python
def collect(
    db: Database,
    *,
    profile_ids: list[int] | None,
    exercise: str | None = None,
    since: float | None = None,
    now: float | None = None,
    hardest: int = 8,
) -> Stats
```

Work out everything the statistics screen shows.

**Parameters**

- `db` (*Database*): Where the answers are.
- `profile_ids` (*list of int or None*): The profiles to include; every profile if None. Keyword-only.
- `exercise` (*str or None, default None*): Only this exercise (its class name); every exercise if None. Keyword-only.
- `since` (*float or None, default None*): Only answers from this timestamp on; the whole history if None. Keyword-only.
- `now` (*float or None, default None*): The current time as a timestamp; the clock is used if None. Keyword-only.
- `hardest` (*int, default 8*): How many questions to list as needing practice. Keyword-only.

**Returns**

- *Stats*: The totals, the per-period buckets, the per-exercise figures and the hardest questions.

**Examples**

```pycon
>>> database = Database()
>>> ada = database.add_profile("Ada")
>>> database.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                duration_ms=4000, answered_at=1000.0)
>>> stats = collect(database, profile_ids=[ada.id], now=1060.0)
>>> stats.questions, stats.median_seconds, stats.practice_seconds
(1, 4.0, 4.0)
>>> collect(database, profile_ids=[999], now=1060.0).questions  # nobody has answered anything
0
```
{% endraw %}
