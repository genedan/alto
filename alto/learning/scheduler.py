"""How a question's history turns into how soon it comes back. Pure Python, no database and no Qt.

Every question carries a *strain*: how much practice it needs. A new question starts at NEW_STRAIN. Each answer moves
it, and the chance of being asked is exp(WEIGHT_SLOPE * strain), so strained questions come back sooner and more
often while well-known ones fade into the background.

* A wrong answer adds WRONG_PENALTY, so every extra attempt pushes the question further up.
* A right answer on the first try takes CORRECT_REWARD off. A right answer after misses earns only RETRY_REWARD.
* The first answer's speed, against the exercise's `par_seconds`, adds or removes strain on top: very quick
  answers take off up to FAST_BONUS, and slow ones add up to SLOW_PENALTY.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import TypeVar

STRAIN_MAX = 6.0
NEW_STRAIN = 1.5
WRONG_PENALTY = 1.5
CORRECT_REWARD = 0.5
RETRY_REWARD = 0.2
FAST_BONUS = 0.6
SLOW_PENALTY = 1.0
VERY_FAST = 0.5  # at or below this fraction of par counts as very quick
VERY_SLOW = 4.0  # at or above this many times par counts as as slow as it gets
WEIGHT_SLOPE = 0.6
BASE_COOLDOWN = 120.0  # seconds a question of strain 3 stays out of the running before it can recur freely
MIN_RECENCY = 0.02

T = TypeVar("T")


def speed_term(
    seconds: float,
    *,
    par_seconds: float,
) -> float:
    """The strain change for how long the first answer took: negative when quick, positive when slow."""
    ratio = seconds / par_seconds
    if ratio <= VERY_FAST:
        return -FAST_BONUS
    if ratio <= 1.0:
        return -FAST_BONUS * (1.0 - ratio) / (1.0 - VERY_FAST)
    return min(SLOW_PENALTY, SLOW_PENALTY * (ratio - 1.0) / (VERY_SLOW - 1.0))


def update_strain(
    strain: float,
    *,
    correct: bool,
    attempt_no: int,
    seconds: float,
    par_seconds: float,
) -> float:
    """The question's strain after one more answer. `seconds` only matters for the first attempt."""
    if not correct:
        strain += WRONG_PENALTY
    elif attempt_no == 1:
        strain += -CORRECT_REWARD + speed_term(seconds, par_seconds=par_seconds)
    else:
        strain -= RETRY_REWARD
    return min(max(strain, 0.0), STRAIN_MAX)


def weight(
    strain: float | None,
    *,
    last_seen: float | None,
    now: float,
) -> float:
    """How likely a question is to be picked, relative to the others. `strain` is None for one never answered.

    A question just seen is held back for a while, long for an easy one and short for a hard one, so what you have
    learned is not repeated straight away but what you struggle with returns within the minute.
    """
    if strain is None:
        return math.exp(WEIGHT_SLOPE * NEW_STRAIN)
    cooldown = BASE_COOLDOWN * 2 ** (3.0 - strain)
    recency = 1.0 - math.exp(-max(now - (last_seen or 0.0), 0.0) / cooldown)
    return math.exp(WEIGHT_SLOPE * strain) * max(recency, MIN_RECENCY)


def choose(
    options: Sequence[T],
    *,
    weights: Sequence[float],
    rng: random.Random,
) -> T:
    return rng.choices(options, weights=weights, k=1)[0]
