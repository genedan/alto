"""The statistics: counts, times and accuracy over days, exercises and profiles."""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import TYPE_CHECKING

from alto.exercises.base import Exercise, Question
from alto.learning import Database, Learner, stats
from alto.theory.pitch import Note

if TYPE_CHECKING:
    from collections.abc import Callable

    from alto.learning.database import Profile

DAY = 86400.0
NOW = datetime(
    2026,
    11,
    12,
    15,
    0,
).timestamp()


class A(Exercise):
    """
    An exercise with a fixed par time, whose questions are random notes.
    """

    name, par_seconds = "A", 4.0

    def generate(self, rng: random.Random) -> Question:
        """
        Make a question with a random note.

        Parameters
        ----------
        rng : random.Random
            The random source (not used: the question is fixed).

        Returns
        -------
        Question
            A question.
        """
        return Question(
            "",
            choices=["x", "y"],
            answer="x",
            staff=[[Note.from_diatonic(rng.randint(14, 60))]],
        )


class B(A):
    """
    A second exercise, the same as the first but with another name.
    """

    name = "B"


def fill() -> tuple[Database, Profile, Profile]:
    """
    Fill a database with two profiles' made-up answers.

    Returns
    -------
    tuple of Database, Profile and Profile
        The database, Ada and Ben.
    """
    db = Database()
    ada, ben = db.add_profile("Ada"), db.add_profile("Ben")
    rng = random.Random(1)
    a, b = A(), B()
    qa, qb = a.generate(rng), b.generate(rng)
    la, lb = Learner(db, profile=ada), Learner(db, profile=ben)
    # Ada, two days ago: A right first time (2 s), A wrong then right (4 s then 3 s)
    la.record(
        a,
        question=qa,
        answer="x",
        correct=True,
        attempt_no=1,
        seconds=2.0,
        now=NOW - 2 * DAY,
    )
    la.record(
        a,
        question=qb,
        answer="y",
        correct=False,
        attempt_no=1,
        seconds=4.0,
        now=NOW - 2 * DAY + 10,
    )
    la.record(
        a,
        question=qb,
        answer="x",
        correct=True,
        attempt_no=2,
        seconds=3.0,
        now=NOW - 2 * DAY + 20,
    )
    # Ada, today: exercise B wrong
    la.record(
        b,
        question=qb,
        answer="y",
        correct=False,
        attempt_no=1,
        seconds=6.0,
        now=NOW - 60,
    )
    # Ben, 20 days ago: A right
    lb.record(
        a,
        question=qa,
        answer="x",
        correct=True,
        attempt_no=1,
        seconds=8.0,
        now=NOW - 20 * DAY,
    )
    return db, ada, ben


def test_collects_first_attempt_accuracy_and_extra_attempts() -> None:
    """
    Check that collects first attempt accuracy and extra attempts.
    """
    db, ada, _ = fill()
    s = stats.collect(db, profile_ids=[ada.id], now=NOW)
    assert (s.questions, s.first_right, s.attempts) == (3, 1, 4)
    assert s.accuracy is not None and s.attempts_per_question is not None
    assert round(s.accuracy) == 33 and round(s.attempts_per_question, 2) == 1.33
    assert s.days_practised == 2
    assert s.median_seconds == 4.0  # first attempts took 2, 4 and 6 s


def test_filters_by_exercise_and_by_timeframe() -> None:
    """
    Check that filters by exercise and by timeframe.
    """
    db, ada, _ = fill()
    only_b = stats.collect(
        db,
        profile_ids=[ada.id],
        exercise="B",
        now=NOW,
    )
    assert (only_b.questions, only_b.first_right) == (1, 0)
    recent = stats.collect(
        db,
        profile_ids=[ada.id],
        since=NOW - DAY,
        now=NOW,
    )
    assert recent.questions == 1


def test_collection_wide_counts_every_profile() -> None:
    """
    Check that collection wide counts every profile.
    """
    db, ada, ben = fill()
    mine = stats.collect(db, profile_ids=[ada.id], now=NOW)
    everyone = stats.collect(db, profile_ids=None, now=NOW)
    assert everyone.questions == mine.questions + 1
    assert stats.collect(db, profile_ids=[ben.id], now=NOW).questions == 1


def test_buckets_run_without_gaps_from_first_answer_to_now() -> None:
    """
    Check that buckets run without gaps from first answer to now.
    """
    db, ada, _ = fill()
    s = stats.collect(
        db,
        profile_ids=[ada.id],
        since=NOW - 7 * DAY,
        now=NOW,
    )
    assert s.granularity == "day" and len(s.buckets) == 8
    assert sum(b.questions for b in s.buckets) == s.questions
    assert [b.questions for b in s.buckets][-3:] == [2, 0, 1]  # two days ago, yesterday (empty), today


def test_long_spans_use_coarser_buckets() -> None:
    """
    Check that long spans use coarser buckets.
    """
    db, ada, _ = fill()
    assert stats.collect(db, profile_ids=None, now=NOW).granularity == "day"  # 20 days
    assert (
        stats.collect(
            db,
            profile_ids=None,
            since=NOW - 120 * DAY,
            now=NOW,
        ).granularity
        == "week"
    )
    assert (
        stats.collect(
            db,
            profile_ids=None,
            since=NOW - 400 * DAY,
            now=NOW,
        ).granularity
        == "month"
    )
    assert (
        stats.collect(
            db,
            profile_ids=[ada.id],
            since=NOW - 3600 * 5,
            now=NOW,
        ).granularity
        == "hour"
    )


def test_by_exercise_and_hardest_questions() -> None:
    """
    Test by exercise and hardest questions.
    """
    db, ada, _ = fill()
    s = stats.collect(db, profile_ids=[ada.id], now=NOW)
    assert {e.exercise: e.questions for e in s.by_exercise} == {"A": 2, "B": 1}
    assert s.hardest and s.hardest[0].strain >= 1.5
    assert "→ x" in s.hardest[0].text


def test_nothing_recorded_gives_empty_stats() -> None:
    """
    Check that nothing recorded gives empty stats.
    """
    s = stats.collect(Database(), profile_ids=None, now=NOW)
    assert s.questions == 0 and s.accuracy is None and s.buckets == [] and s.hardest == []


def test_daily_counts_count_first_answers_per_local_day_and_follow_the_exercise(
    practised_learner: Callable[..., Learner],
) -> None:
    """
    Check that daily counts count first answers per local day and follow the exercise.

    Parameters
    ----------
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    from datetime import datetime

    from alto.learning import stats

    learner = practised_learner()
    now = time.time()
    everything = stats.daily_counts(learner.db, profile_ids=[learner.profile.id], now=now)
    assert everything and datetime.fromtimestamp(now).date() >= max(everything)
    total = sum(everything.values())
    assert (
        total
        == stats.collect(
            learner.db,
            profile_ids=[learner.profile.id],
            exercise=None,
            since=None,
            now=now,
        ).questions
    )
    assert (
        stats.daily_counts(
            learner.db,
            profile_ids=[learner.profile.id],
            exercise="NoSuchExercise",
            now=now,
        )
        == {}
    )
    assert (
        stats.daily_counts(
            learner.db,
            profile_ids=[learner.profile.id],
            weeks=1,
            now=now + 400 * 86400,
        )
        == {}
    )  # a year on: all too old
