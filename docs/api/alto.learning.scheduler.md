---
title: alto.learning.scheduler
parent: api
package: alto.learning
order: 9
permalink: /api/alto.learning.scheduler/
---
{% raw %}
How a question's history turns into how soon it comes back. Pure Python, no database and no Qt.

Every question carries a *strain*: how much practice it needs. A new question starts at NEW_STRAIN. Each answer moves
it, and the chance of being asked is exp(WEIGHT_SLOPE * strain), so strained questions come back sooner and more
often while well-known ones fade into the background.

* A wrong answer adds WRONG_PENALTY, so every extra attempt pushes the question further up.
* A right answer on the first try takes CORRECT_REWARD off. A right answer after misses earns only RETRY_REWARD.
* The first answer's speed, against the exercise's `par_seconds`, adds or removes strain on top: very quick
  answers take off up to FAST_BONUS, and slow ones add up to SLOW_PENALTY.

**Examples**

```pycon
>>> strain = update_strain(NEW_STRAIN, correct=False, attempt_no=1, seconds=4.0, par_seconds=4.0)
>>> strain  # a miss pushes the question up
3.0
>>> update_strain(strain, correct=True, attempt_no=2, seconds=2.0, par_seconds=4.0)  # a retry earns little
2.8
```

## speed_term

```python
def speed_term(
    seconds: float,
    *,
    par_seconds: float,
) -> float
```

Return the strain change for how long the first answer took.

**Parameters**

- `seconds` (*float*): How long the first answer took.
- `par_seconds` (*float*): How long a good first answer takes for this exercise. Keyword-only.

**Returns**

- *float*: Negative when the answer was quick (down to `-FAST_BONUS`), zero at par, and positive when it was slow (up to `SLOW_PENALTY`).

**Examples**

```pycon
>>> speed_term(1.0, par_seconds=10.0)  # at or under half of par: the full bonus
-0.6
>>> round(speed_term(7.5, par_seconds=10.0), 2)
-0.3
>>> round(speed_term(25.0, par_seconds=10.0), 2)
0.5
>>> speed_term(100.0, par_seconds=10.0)  # four times par or more: the full penalty
1.0
```

## update_strain

```python
def update_strain(
    strain: float,
    *,
    correct: bool,
    attempt_no: int,
    seconds: float,
    par_seconds: float,
) -> float
```

Return the question's strain after one more answer.

**Parameters**

- `strain` (*float*): The strain before this answer.
- `correct` (*bool*): Whether the answer was right. Keyword-only.
- `attempt_no` (*int*): 1 for the first answer to this showing of the question, 2 for the second and so on. Keyword-only.
- `seconds` (*float*): How long the answer took. Only the first attempt's speed matters. Keyword-only.
- `par_seconds` (*float*): How long a good first answer takes for this exercise. Keyword-only.

**Returns**

- *float*: The new strain, kept between 0 and `STRAIN_MAX`.

**Examples**

```pycon
>>> update_strain(1.5, correct=False, attempt_no=1, seconds=5.0, par_seconds=5.0)
3.0
>>> round(update_strain(1.5, correct=True, attempt_no=1, seconds=1.0, par_seconds=5.0), 2)  # right, and quick
0.4
>>> update_strain(5.9, correct=False, attempt_no=1, seconds=5.0, par_seconds=5.0)  # capped
6.0
```

## weight

```python
def weight(
    strain: float | None,
    *,
    last_seen: float | None,
    now: float,
) -> float
```

Return how likely a question is to be picked, relative to the others.

A question just seen is held back for a while, long for an easy one and short for a hard one, so what you have
learned is not repeated straight away but what you struggle with returns within the minute.

**Parameters**

- `strain` (*float or None*): The question's strain, or None for one never answered.
- `last_seen` (*float or None*): When it was last answered (a timestamp), or None if never. Keyword-only.
- `now` (*float*): The current time (a timestamp). Keyword-only.

**Returns**

- *float*: A positive number; a larger one means the question is more likely to come up.

**Examples**

```pycon
>>> round(weight(None, last_seen=None, now=0.0), 2)  # a new question
2.46
>>> round(weight(3.0, last_seen=0.0, now=1e9), 2)  # a hard question, long unseen
6.05
>>> round(weight(3.0, last_seen=100.0, now=100.0), 3)  # the same, just seen: held back
0.121
```

## choose

```python
def choose(
    options: Sequence[T],
    *,
    weights: Sequence[float],
    rng: random.Random,
) -> T
```

Pick one option at random, in proportion to its weight.

**Parameters**

- `options` (*sequence of T*): The things to choose from.
- `weights` (*sequence of float*): One weight per option; a larger weight makes it more likely. Keyword-only.
- `rng` (*random.Random*): The random number generator to draw with. Keyword-only.

**Returns**

- *T*: The chosen option.

**Examples**

```pycon
>>> choose(["a", "b"], weights=[1.0, 0.0], rng=random.Random(0))
'a'
```
{% endraw %}
