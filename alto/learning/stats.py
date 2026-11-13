"""
Numbers and series for the statistics screen, worked out from the answers in the database. Pure Python, no Qt.

A "question" here is one showing of a question, scored by its first answer: it is right if that answer was right.
Later attempts at the same showing show up as extra attempts per question, not as extra questions.

Examples
--------
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
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import (
    KW_ONLY,
    dataclass,
    field,
)
from datetime import (
    date,
    datetime,
    timedelta,
)

from alto.exercises.base import Question
from alto.learning import scheduler
from alto.learning.database import Database
from alto.theory.pitch import Note
from alto.theory.scales import format_key_signature

IDLE_CAP_S = 120.0  # one answer counts for at most this long towards practice time, so leaving the app open does not inflate it


@dataclass
class Bucket:
    """
    The answers given in one period (an hour, day, week or month), for the charts.

    Attributes
    ----------
    start : datetime
        When the period begins.
    label : str
        What to call the period on a chart axis. Keyword-only.
    questions : int, default 0
        How many questions were answered in it. Keyword-only.
    first_right : int, default 0
        How many of those were right on the first answer. Keyword-only.
    times : list of float
        Seconds to the first answer, one per question. Keyword-only.

    Examples
    --------
    >>> bucket = Bucket(datetime(2026, 1, 5), label="Jan 5", questions=2, first_right=1, times=[2.0, 4.0])
    >>> bucket.accuracy, bucket.median_seconds
    (50.0, 3.0)
    """

    start: datetime
    _: KW_ONLY
    label: str
    questions: int = 0
    first_right: int = 0
    times: list[float] = field(default_factory=list)  # seconds to the first answer

    @property
    def accuracy(self) -> float | None:
        """
        Return the percentage of questions in the period that were right first time.

        Returns
        -------
        float or None
            0 to 100, or None if no questions were answered.

        Examples
        --------
        >>> Bucket(datetime(2026, 1, 5), label="Jan 5", questions=4, first_right=3).accuracy
        75.0
        >>> Bucket(datetime(2026, 1, 5), label="Jan 5").accuracy is None
        True
        """
        return 100.0 * self.first_right / self.questions if self.questions else None

    @property
    def median_seconds(self) -> float | None:
        """
        Return the typical time to a first answer in the period.

        Returns
        -------
        float or None
            The median, in seconds, or None if no questions were answered.

        Examples
        --------
        >>> Bucket(datetime(2026, 1, 5), label="Jan 5", times=[1.0, 2.0, 9.0]).median_seconds
        2.0
        """
        return statistics.median(self.times) if self.times else None


@dataclass
class ExerciseStats:
    """
    How practice is going on one exercise.

    Attributes
    ----------
    exercise : str
        The exercise's class name.
    questions : int
        How many questions were answered. Keyword-only.
    accuracy : float
        The percentage right first time. Keyword-only.
    median_seconds : float
        The typical time to a first answer, in seconds. Keyword-only.

    Examples
    --------
    >>> ExerciseStats("NoteNames", questions=40, accuracy=87.5, median_seconds=3.2).accuracy
    87.5
    """

    exercise: str
    _: KW_ONLY
    questions: int
    accuracy: float
    median_seconds: float


@dataclass
class HardQuestion:
    """
    A question that needs practice, for the list on the statistics screen.

    Attributes
    ----------
    exercise : str
        The exercise's class name.
    text : str
        A short line saying what the question was.  Keyword-only.
    strain : float
        How much practice it needs; higher is more. Keyword-only.
    seen : int
        How many times it was answered. Keyword-only.
    wrong : int
        How many wrong answers it has had. Keyword-only.

    Examples
    --------
    >>> HardQuestion("NoteNames", text="Treble: G4", strain=4.5, seen=6, wrong=5).wrong
    5
    """

    exercise: str
    _: KW_ONLY
    text: str
    strain: float
    seen: int
    wrong: int


@dataclass
class Stats:
    """
    Everything the statistics screen shows.

    Attributes
    ----------
    questions : int, default 0
        How many questions were answered, each counted once.
    first_right : int, default 0
        How many were right on the first answer. Keyword-only.
    attempts : int, default 0
        How many answers were given in all, including repeats. Keyword-only.
    median_seconds : float or None
        The typical time to a first answer. Keyword-only.
    practice_seconds : float, default 0.0
        Time spent practising, with a cap on each answer so leaving the app open does not inflate it. Keyword-only.
    days_practised : int, default 0
        On how many different days there were answers. Keyword-only.
    granularity : str, default "day"
        The size of the chart periods: "hour", "day", "week" or "month". Keyword-only.
    buckets : list of Bucket
        One per period, oldest first. Keyword-only.
    by_exercise : list of ExerciseStats
        One per exercise practised, sorted by name. Keyword-only.
    hardest : list of HardQuestion
        The questions that need most practice. Keyword-only.

    Examples
    --------
    >>> Stats().accuracy is None  # nothing answered yet
    True
    >>> Stats(4, first_right=3, attempts=6).attempts_per_question
    1.5
    """

    questions: int = 0
    _: KW_ONLY
    first_right: int = 0
    attempts: int = 0
    median_seconds: float | None = None
    practice_seconds: float = 0.0
    days_practised: int = 0
    granularity: str = "day"
    buckets: list[Bucket] = field(default_factory=list)
    by_exercise: list[ExerciseStats] = field(default_factory=list)
    hardest: list[HardQuestion] = field(default_factory=list)

    @property
    def accuracy(self) -> float | None:
        """
        Return the percentage of questions that were right first time.

        Returns
        -------
        float or None
            0 to 100, or None if no questions were answered.

        Examples
        --------
        >>> Stats(4, first_right=3).accuracy
        75.0
        """
        return 100.0 * self.first_right / self.questions if self.questions else None

    @property
    def attempts_per_question(self) -> float | None:
        """
        Return the average number of answers it took per question.

        Returns
        -------
        float or None
            1.0 if every question was answered right first time; None if no questions were answered.

        Examples
        --------
        >>> Stats(4, attempts=5).attempts_per_question
        1.25
        """
        return self.attempts / self.questions if self.questions else None


def _granularity(span_days: float) -> str:
    """
    Choose the size of the chart periods for a span of time.

    Parameters
    ----------
    span_days : float
        How many days the statistics cover.

    Returns
    -------
    str
        "hour" up to a day and a half, "day" up to 45 days, "week" up to 200 days, otherwise "month".

    Examples
    --------
    >>> [_granularity(d) for d in (1, 30, 90, 365)]
    ['hour', 'day', 'week', 'month']
    """
    if span_days <= 1.5:
        return "hour"
    if span_days <= 45:
        return "day"
    if span_days <= 200:
        return "week"
    return "month"


def _floor(
    t: datetime,
    *,
    gran: str,
) -> datetime:
    """
    Round a time down to the start of its period.

    Parameters
    ----------
    t : datetime
        The time.
    gran : str
        "hour", "day", "week" (starting on Monday) or "month". Keyword-only.

    Returns
    -------
    datetime
        The start of the hour, day, week or month containing `t`.

    Examples
    --------
    >>> _floor(datetime(2026, 11, 13, 15, 42), gran="day")
    datetime.datetime(2026, 11, 13, 0, 0)
    >>> _floor(datetime(2026, 11, 13, 15, 42), gran="week")  # a Friday: back to Monday
    datetime.datetime(2026, 11, 9, 0, 0)
    >>> _floor(datetime(2026, 11, 13, 15, 42), gran="month")
    datetime.datetime(2026, 11, 1, 0, 0)
    """
    if gran == "hour":
        return t.replace(minute=0, second=0, microsecond=0)
    day = t.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    if gran == "week":
        return day - timedelta(days=day.weekday())
    if gran == "month":
        return day.replace(day=1)
    return day


def _next(
    t: datetime,
    *,
    gran: str,
) -> datetime:
    """
    Return the start of the period after the one starting at a given time.

    Parameters
    ----------
    t : datetime
        The start of a period.
    gran : str
        "hour", "day", "week" or "month". Keyword-only.

    Returns
    -------
    datetime
        The start of the next period.

    Examples
    --------
    >>> _next(datetime(2026, 11, 1), gran="month")
    datetime.datetime(2026, 12, 1, 0, 0)
    >>> _next(datetime(2026, 11, 9), gran="week")
    datetime.datetime(2026, 11, 16, 0, 0)
    """
    if gran == "hour":
        return t + timedelta(hours=1)
    if gran == "week":
        return t + timedelta(days=7)
    if gran == "month":
        return (t.replace(day=28) + timedelta(days=4)).replace(day=1)
    return t + timedelta(days=1)


def _label(
    t: datetime,
    *,
    gran: str,
) -> str:
    """
    Return the text that labels a period on a chart axis.

    Parameters
    ----------
    t : datetime
        The start of the period.
    gran : str
        "hour", "day", "week" or "month". Keyword-only.

    Returns
    -------
    str
        The time for an hour, the month and year for a month, otherwise the month and day.

    Examples
    --------
    >>> _label(datetime(2026, 11, 13, 15), gran="hour")
    '15:00'
    >>> _label(datetime(2026, 11, 13), gran="day")
    'Nov 13'
    >>> _label(datetime(2026, 11, 1), gran="month")
    'Nov 2026'
    """
    if gran == "hour":
        return t.strftime("%H:%M")
    if gran == "month":
        return t.strftime("%b %Y")
    return f"{t.strftime('%b')} {t.day}"


def describe(question: Question) -> str:
    """
    Return a short line saying what a question was, for the list of questions that need practice.

    Parameters
    ----------
    question : Question
        The question to describe.

    Returns
    -------
    str
        What was shown (notes, a key signature or a keyboard key) and, where that does not already say it, the answer.

    Examples
    --------
    >>> from alto.exercises.base import Question
    >>> describe(Question("What type of chord is this?", choices=["major", "minor"], answer="minor"))
    'What type of chord is this? → minor'
    """

    def spelled(n: Note) -> str:
        """
        Return a note's name with its octave.

        Parameters
        ----------
        n : Note
            The note.

        Returns
        -------
        str
            For example 'F♯4'.

        Examples
        --------
        >>> from alto.exercises.base import Question
        >>> from alto.theory.pitch import Note
        >>> describe(Question("", choices=["F♯", "G♭"], answer="F♯", keyboard=Note.parse("F#4")))  # names the key with `spelled`
        'Key F♯4'
        """
        return f"{n.name}{n.octave}"

    clef = question.clef.capitalize()
    if question.show_staff:
        what = f"{clef}: {format_key_signature(question.key)}. {question.prompt}"
    elif question.prompt:
        what = question.prompt
    elif question.keyboard:
        what = f"Key {spelled(question.keyboard)}"
        if question.key:
            what += f" in {abs(question.key)} {'sharps' if question.key > 0 else 'flats'}"
    elif question.staff:
        notes = " – ".join(" ".join(spelled(n) for n in col) for col in question.staff)
        what = f"{clef}: {notes}"
        if question.key:
            what += f" ({abs(question.key)} {'sharps' if question.key > 0 else 'flats'})"
    else:
        what = question.answer
    return what if question.construct is not None or question.answer in what else f"{what} → {question.answer}"


def daily_counts(
    db: Database,
    *,
    profile_ids: list[int] | None,
    exercise: str | None = None,
    weeks: int = 53,
    now: float | None = None,
) -> dict[date, int]:
    """
    Return how many questions were answered on each day, for the review heatmap.

    Looks back over the last `weeks` calendar weeks up to today, in local time. Days with no answers are left out. It
    counts questions (first attempts), not attempts, like everything else here.

    Parameters
    ----------
    db : Database
        Where the answers are.
    profile_ids : list of int or None
        The profiles to include; every profile if None. Keyword-only.
    exercise : str or None, default None
        Only this exercise (its class name); every exercise if None. Keyword-only.
    weeks : int, default 53
        How many calendar weeks to look back, counting this one. Keyword-only.
    now : float or None, default None
        The current time as a timestamp; the clock is used if None. Keyword-only.

    Returns
    -------
    dict of date to int
        The number of questions answered on each day that had any.

    Examples
    --------
    >>> database = Database()
    >>> ada = database.add_profile("Ada")
    >>> noon = datetime(2026, 11, 13, 12).timestamp()
    >>> for i in range(3):
    ...     database.add_attempt(ada.id, exercise="NoteNames", item_key=str(i), attempt_no=1, answer="C", correct=True,
    ...                    duration_ms=1000, answered_at=noon + i)
    >>> daily_counts(database, profile_ids=[ada.id], now=noon + 60)
    {datetime.date(2026, 11, 13): 3}
    """
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now).date()
    first = today - timedelta(days=today.weekday() + 7 * (weeks - 1))  # the Monday that starts the first week shown
    since = datetime.combine(first, datetime.min.time()).timestamp()
    counts: dict[date, int] = {}
    for r in db.attempts_in(profile_ids, exercise=exercise, since=since):
        if r["attempt_no"] == 1:
            day = datetime.fromtimestamp(r["answered_at"]).date()
            counts[day] = counts.get(day, 0) + 1
    return counts


def collect(
    db: Database,
    *,
    profile_ids: list[int] | None,
    exercise: str | None = None,
    since: float | None = None,
    now: float | None = None,
    hardest: int = 8,
) -> Stats:
    """
    Work out everything the statistics screen shows.

    Parameters
    ----------
    db : Database
        Where the answers are.
    profile_ids : list of int or None
        The profiles to include; every profile if None. Keyword-only.
    exercise : str or None, default None
        Only this exercise (its class name); every exercise if None. Keyword-only.
    since : float or None, default None
        Only answers from this timestamp on; the whole history if None. Keyword-only.
    now : float or None, default None
        The current time as a timestamp; the clock is used if None. Keyword-only.
    hardest : int, default 8
        How many questions to list as needing practice. Keyword-only.

    Returns
    -------
    Stats
        The totals, the per-period buckets, the per-exercise figures and the hardest questions.

    Examples
    --------
    >>> database = Database()
    >>> ada = database.add_profile("Ada")
    >>> database.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
    ...                duration_ms=4000, answered_at=1000.0)
    >>> stats = collect(database, profile_ids=[ada.id], now=1060.0)
    >>> stats.questions, stats.median_seconds, stats.practice_seconds
    (1, 4.0, 4.0)
    >>> collect(database, profile_ids=[999], now=1060.0).questions  # nobody has answered anything
    0
    """
    now = time.time() if now is None else now
    rows = db.attempts_in(profile_ids, exercise=exercise, since=since)
    out = Stats(attempts=len(rows))
    if rows:
        start = datetime.fromtimestamp(since if since is not None else rows[0]["answered_at"])
        out.granularity = gran = _granularity((now - start.timestamp()) / 86400)
        cursor, end = _floor(start, gran=gran), datetime.fromtimestamp(now)
        buckets: dict[datetime, Bucket] = {}
        while cursor <= end:
            buckets[cursor] = Bucket(cursor, label=_label(cursor, gran=gran))
            cursor = _next(cursor, gran=gran)
        per_exercise: dict[str, list[tuple[bool, float]]] = {}
        times: list[float] = []
        days = set()
        for r in rows:
            when = datetime.fromtimestamp(r["answered_at"])
            days.add(when.date())
            out.practice_seconds += min(r["duration_ms"] / 1000, IDLE_CAP_S)
            if r["attempt_no"] != 1:
                continue
            ok, seconds = bool(r["correct"]), r["duration_ms"] / 1000
            out.questions += 1
            out.first_right += ok
            times.append(seconds)
            per_exercise.setdefault(r["exercise"], []).append((ok, seconds))
            b = buckets.get(_floor(when, gran=gran))
            if b:
                b.questions += 1
                b.first_right += ok
                b.times.append(seconds)
        out.buckets = list(buckets.values())
        out.days_practised = len(days)
        out.median_seconds = statistics.median(times) if times else None
        out.by_exercise = sorted(
            (
                ExerciseStats(
                    name,
                    questions=len(v),
                    accuracy=100.0 * sum(ok for ok, _ in v) / len(v),
                    median_seconds=statistics.median(t for _, t in v),
                )
                for name, v in per_exercise.items()
            ),
            key=lambda e: e.exercise,
        )
    for r in db.strained_items(
        profile_ids,
        exercise=exercise,
        since=since,
        min_strain=scheduler.NEW_STRAIN,
        limit=hardest,
    ):
        try:
            text = describe(Question.from_dict(json.loads(r["payload"])))
        except (ValueError, KeyError, TypeError):
            continue
        out.hardest.append(
            HardQuestion(
                r["exercise"],
                text=text,
                strain=r["strain"],
                seen=r["seen"],
                wrong=r["wrong"],
            ),
        )
    return out
