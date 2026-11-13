---
title: alto.learning.database
parent: api
package: alto.learning
order: 6
permalink: /api/alto.learning.database/
---
{% raw %}
The SQLite store: profiles, every answer given, and what is known about each question. Pure Python (no Qt).

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                duration_ms=2000, answered_at=100.0)
>>> db.count_attempts(ada.id)
1
```

## Profile

```python
Profile(
    id: int,
    *,
    name: str,
)
```

A person who practises: their answers are kept apart from everyone else's.

**Attributes**

- `id` (*int*): The profile's row number in the database.
- `name` (*str*): The name shown in the interface. Keyword-only.

**Examples**

```pycon
>>> Profile(1, name="Ada")
Profile(id=1, name='Ada')
```

## ItemRecord

```python
ItemRecord(
    strain: float,
    *,
    seen: int,
    first_try_right: int,
    wrong_attempts: int,
    total_first_ms: int,
    last_seen: float,
    signature: str,
    payload: str,
    item_key: str = '',
)
```

What a profile's history says about one question.

**Attributes**

- `strain` (*float*): How much practice the question needs; higher means it comes back sooner.
- `seen` (*int*): How many times the question was shown and answered. Keyword-only.
- `first_try_right` (*int*): How many of those showings were answered right first time. Keyword-only.
- `wrong_attempts` (*int*): How many wrong answers there have been in all. Keyword-only.
- `total_first_ms` (*int*): Time to the first answer, summed over the showings, in milliseconds. Keyword-only.
- `last_seen` (*float*): When the question was last answered, as a timestamp. Keyword-only.
- `signature` (*str*): The exercise settings it was asked under; it is only asked again while these are unchanged. Keyword-only.
- `payload` (*str*): The question itself as JSON, so it can be asked again. Keyword-only.
- `item_key` (*str, default ""*): The question's identity. Empty when the record is built to be saved, filled in when it is read back. Keyword-only.

**Examples**

```pycon
>>> record = ItemRecord(2.0, seen=3, first_try_right=1, wrong_attempts=2, total_first_ms=9000,
...                     last_seen=100.0, signature="s", payload="{}")
>>> record.seen
3
```

## Database

```python
Database(path: str | Path = ':memory:')
```

The SQLite database behind profiles, answers and per-question history.

**Attributes**

- `conn` (*sqlite3.Connection*): The open connection, with rows returned as `sqlite3.Row` so columns can be read by name.

**Examples**

```pycon
>>> db = Database()  # in memory; give a path to keep it on disk
>>> db.profiles()
[]
>>> db.add_profile("Ada")
Profile(id=1, name='Ada')
```

**Constructor**

Open the database, creating it and its tables if they do not exist.

**Parameters**

- `path` (*str or Path, default ":memory:"*): The file to use, whose folder is created if needed, or ":memory:" for a throwaway database.

**Constructor examples**

```pycon
>>> db = Database()
>>> db.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
True
```

### Database.close

```python
def close() -> None
```

Close the connection.

**Examples**

```pycon
>>> db = Database()
>>> db.close()
```

### Database.profiles

```python
def profiles() -> list[Profile]
```

Return every profile, sorted by name without regard to case.

**Returns**

- *list of Profile*: The profiles.

**Examples**

```pycon
>>> db = Database()
>>> _ = db.add_profile("ben")
>>> _ = db.add_profile("Ada")
>>> [p.name for p in db.profiles()]
['Ada', 'ben']
```

### Database.profile

```python
def profile(profile_id: int) -> Profile | None
```

Return one profile by its id.

**Parameters**

- `profile_id` (*int*): The profile's id.

**Returns**

- *Profile or None*: The profile, or None if there is none with that id.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> # noinspection PyUnresolvedReferences
>>> db.profile(ada.id).name
'Ada'
>>> db.profile(999) is None
True
```

### Database.add_profile

```python
def add_profile(name: str) -> Profile
```

Create a profile.

**Parameters**

- `name` (*str*): The name. Runs of spaces are collapsed to one, and case does not matter when checking for a duplicate.

**Returns**

- *Profile*: The new profile.

**Raises**

- *ValueError*: If the name is empty, or is already taken.

**Examples**

```pycon
>>> db = Database()
>>> db.add_profile("  Ada   Lovelace ")
Profile(id=1, name='Ada Lovelace')
>>> db.add_profile("ada lovelace")
Traceback (most recent call last):
    ...
ValueError: There is already a profile called ada lovelace.
```

### Database.delete_profile

```python
def delete_profile(profile_id: int) -> None
```

Delete a profile together with all of its answers and question history.

**Parameters**

- `profile_id` (*int*): The profile's id.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.delete_profile(ada.id)
>>> db.profiles()
[]
```

### Database.get_item

```python
def get_item(
    profile_id: int,
    *,
    exercise: str,
    item_key: str,
) -> ItemRecord | None
```

Return what is known about one question for a profile.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `exercise` (*str*): The exercise's class name. Keyword-only.
- `item_key` (*str*): The question's identity. Keyword-only.

**Returns**

- *ItemRecord or None*: The record, or None if the question has never been answered.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.get_item(ada.id, exercise="NoteNames", item_key="k") is None
True
```

### Database.save_item

```python
def save_item(
    profile_id: int,
    *,
    exercise: str,
    item_key: str,
    item: ItemRecord,
) -> None
```

Store what is known about a question, replacing any earlier record of it.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `exercise` (*str*): The exercise's class name. Keyword-only.
- `item_key` (*str*): The question's identity. Keyword-only.
- `item` (*ItemRecord*): What to store. Keyword-only.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> record = ItemRecord(2.0, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=3000,
...                     last_seen=100.0, signature="s", payload="{}")
>>> db.save_item(ada.id, exercise="NoteNames", item_key="k", item=record)
>>> # noinspection PyUnresolvedReferences
>>> db.get_item(ada.id, exercise="NoteNames", item_key="k").strain
2.0
```

### Database.add_attempt

```python
def add_attempt(
    profile_id: int,
    *,
    exercise: str,
    item_key: str,
    attempt_no: int,
    answer: str,
    correct: bool,
    duration_ms: int,
    answered_at: float,
) -> None
```

Log one answer, right or wrong.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `exercise` (*str*): The exercise's class name. Keyword-only.
- `item_key` (*str*): The question's identity. Keyword-only.
- `attempt_no` (*int*): 1 for the first answer to this showing of the question, 2 for the second and so on. Keyword-only.
- `answer` (*str*): What was answered. Keyword-only.
- `correct` (*bool*): Whether it was right. Keyword-only.
- `duration_ms` (*int*): How long it took, in milliseconds. Keyword-only.
- `answered_at` (*float*): When it was answered, as a timestamp. Keyword-only.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=False,
...                duration_ms=1500, answered_at=50.0)
>>> [(r["answer"], r["correct"]) for r in db.attempts(ada.id)]
[('C', 0)]
```

### Database.attempts

```python
def attempts(
    profile_id: int,
    *,
    exercise: str | None = None,
) -> list[sqlite3.Row]
```

Return all of a profile's answers in the order they were given.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `exercise` (*str or None, default None*): Only answers to this exercise (its class name); every exercise if None. Keyword-only.

**Returns**

- *list of sqlite3.Row*: Every column of each answer.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> for i, name in enumerate(["NoteNames", "IntervalNames"]):
...     db.add_attempt(ada.id, exercise=name, item_key="k", attempt_no=1, answer="x", correct=True,
...                    duration_ms=1000, answered_at=float(i))
>>> [r["exercise"] for r in db.attempts(ada.id)]
['NoteNames', 'IntervalNames']
>>> [r["exercise"] for r in db.attempts(ada.id, exercise="IntervalNames")]
['IntervalNames']
```

### Database.attempts_in

```python
def attempts_in(
    profile_ids: list[int] | None = None,
    *,
    exercise: str | None = None,
    since: float | None = None,
) -> list[sqlite3.Row]
```

Return answers given, oldest first, for some profiles, an exercise and a period.

**Parameters**

- `profile_ids` (*list of int or None, default None*): The profiles to include; every profile if None.
- `exercise` (*str or None, default None*): Only this exercise (its class name); every exercise if None. Keyword-only.
- `since` (*float or None, default None*): Only answers from this timestamp on; the whole history if None. Keyword-only.

**Returns**

- *list of sqlite3.Row*: Each answer's exercise, attempt number, correctness, duration in milliseconds and time.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> for t in (10.0, 20.0, 30.0):
...     db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                    duration_ms=1000, answered_at=t)
>>> [r["answered_at"] for r in db.attempts_in([ada.id], since=15.0)]
[20.0, 30.0]
```

### Database.strained_items

```python
def strained_items(
    profile_ids: list[int] | None = None,
    *,
    exercise: str | None = None,
    since: float | None = None,
    min_strain: float = 0.0,
    limit: int = 10,
) -> list[sqlite3.Row]
```

Return the questions that need most practice, the same question from different profiles counted together.

**Parameters**

- `profile_ids` (*list of int or None, default None*): The profiles to include; every profile if None.
- `exercise` (*str or None, default None*): Only this exercise (its class name); every exercise if None. Keyword-only.
- `since` (*float or None, default None*): Only questions last seen from this timestamp on; the whole history if None. Keyword-only.
- `min_strain` (*float, default 0.0*): Leave out questions with less strain than this. Keyword-only.
- `limit` (*int, default 10*): The most questions to return. Keyword-only.

**Returns**

- *list of sqlite3.Row*: Each question's exercise, key, average strain, times seen, wrong attempts and stored payload, most strained first.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> for key, strain in (("easy", 0.5), ("hard", 4.0)):
...     item = ItemRecord(strain, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=1000,
...                       last_seen=1.0, signature="s", payload="{}")
...     db.save_item(ada.id, exercise="NoteNames", item_key=key, item=item)
>>> [r["item_key"] for r in db.strained_items([ada.id], min_strain=1.0)]
['hard']
```

### Database.count_attempts

```python
def count_attempts(profile_id: int) -> int
```

Return how many answers a profile has given.

**Parameters**

- `profile_id` (*int*): The profile's id.

**Returns**

- *int*: The number of answers, wrong ones included.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.count_attempts(ada.id)
0
```

### Database.attempt_rows

```python
def attempt_rows(
    profile_id: int,
    *,
    limit: int = 10000,
) -> list[sqlite3.Row]
```

Return the newest answers first, each with the stored question it was an answer to (if that is still known).

**Parameters**

- `profile_id` (*int*): The profile's id.
- `limit` (*int, default 10000*): The most rows to return. Keyword-only.

**Returns**

- *list of sqlite3.Row*: Each answer's time, exercise, question key, answer, correctness, attempt number, duration and question payload.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> for t in (1.0, 2.0):
...     db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                    duration_ms=1000, answered_at=t)
>>> [r["answered_at"] for r in db.attempt_rows(ada.id)]
[2.0, 1.0]
```

### Database.item_rows

```python
def item_rows(
    profile_id: int,
    *,
    limit: int = 10000,
) -> list[sqlite3.Row]
```

Return what is known about each of a profile's questions, the most strained first.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `limit` (*int, default 10000*): The most rows to return. Keyword-only.

**Returns**

- *list of sqlite3.Row*: Every column of each question's record.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.item_rows(ada.id)
[]
```

### Database.profile_rows

```python
def profile_rows() -> list[sqlite3.Row]
```

Return every profile with how many answers and questions it has.

**Returns**

- *list of sqlite3.Row*: Each profile's id, name, creation time, number of answers and number of questions, sorted by name.

**Examples**

```pycon
>>> db = Database()
>>> _ = db.add_profile("Ada")
>>> [(r["name"], r["attempts"], r["questions"]) for r in db.profile_rows()]
[('Ada', 0, 0)]
```

### Database.replay_candidates

```python
def replay_candidates(
    profile_id: int,
    *,
    exercise: str,
    signature: str,
    hardest: int = 25,
    random_extra: int = 10,
) -> list[ItemRecord]
```

Return questions asked before under these same settings: the ones that need most practice, plus a few at random.

**Parameters**

- `profile_id` (*int*): The profile's id.
- `exercise` (*str*): The exercise's class name. Keyword-only.
- `signature` (*str*): The exercise's current settings signature; only questions asked under it qualify. Keyword-only.
- `hardest` (*int, default 25*): How many of the most strained questions to include. Keyword-only.
- `random_extra` (*int, default 10*): How many more to pick at random. Keyword-only.

**Returns**

- *list of ItemRecord*: The questions, each at most once.

**Examples**

```pycon
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> item = ItemRecord(3.0, seen=1, first_try_right=0, wrong_attempts=1, total_first_ms=1000,
...                   last_seen=1.0, signature="s1", payload="{}")
>>> db.save_item(ada.id, exercise="NoteNames", item_key="k", item=item)
>>> [row_.item_key for row_ in db.replay_candidates(ada.id, exercise="NoteNames", signature="s1")]
['k']
>>> db.replay_candidates(ada.id, exercise="NoteNames", signature="other settings")
[]
```
{% endraw %}
