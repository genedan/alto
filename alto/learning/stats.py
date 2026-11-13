"""Numbers and series for the statistics screen, worked out from the answers in the database. Pure Python, no Qt.

A "question" here is one showing of a question, scored by its first answer: it is right if that answer was right.
Later attempts at the same showing show up as extra attempts per question, not as extra questions.
"""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from ..exercises.base import Question
from ..theory.pitch import Note
from ..theory.scales import format_key_signature
from . import scheduler
from .database import Database

IDLE_CAP_S = 120.0  # one answer counts for at most this long towards practice time, so leaving the app open does not inflate it


@dataclass
class Bucket:
    start: datetime
    label: str
    questions: int = 0
    first_right: int = 0
    times: list[float] = field(default_factory=list)  # seconds to the first answer

    @property
    def accuracy(self) -> float | None:
        return 100.0 * self.first_right / self.questions if self.questions else None

    @property
    def median_seconds(self) -> float | None:
        return statistics.median(self.times) if self.times else None


@dataclass
class ExerciseStats:
    exercise: str
    questions: int
    accuracy: float
    median_seconds: float


@dataclass
class HardQuestion:
    exercise: str
    text: str
    strain: float
    seen: int
    wrong: int


@dataclass
class Stats:
    questions: int = 0
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
        return 100.0 * self.first_right / self.questions if self.questions else None

    @property
    def attempts_per_question(self) -> float | None:
        return self.attempts / self.questions if self.questions else None


def _granularity(span_days: float) -> str:
    if span_days <= 1.5:
        return "hour"
    if span_days <= 45:
        return "day"
    if span_days <= 200:
        return "week"
    return "month"


def _floor(t: datetime, gran: str) -> datetime:
    if gran == "hour":
        return t.replace(minute=0, second=0, microsecond=0)
    day = t.replace(hour=0, minute=0, second=0, microsecond=0)
    if gran == "week":
        return day - timedelta(days=day.weekday())
    if gran == "month":
        return day.replace(day=1)
    return day


def _next(t: datetime, gran: str) -> datetime:
    if gran == "hour":
        return t + timedelta(hours=1)
    if gran == "week":
        return t + timedelta(days=7)
    if gran == "month":
        return (t.replace(day=28) + timedelta(days=4)).replace(day=1)
    return t + timedelta(days=1)


def _label(t: datetime, gran: str) -> str:
    if gran == "hour":
        return t.strftime("%H:%M")
    if gran == "month":
        return t.strftime("%b %Y")
    return f"{t.strftime('%b')} {t.day}"


def describe(question: Question) -> str:
    """A short line saying what a question was, for the list of questions that need practice."""
    def spelled(n: Note) -> str:
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


def daily_counts(db: Database, profile_ids: list[int] | None, exercise: str | None = None, weeks: int = 53,
                 now: float | None = None) -> dict[date, int]:
    """Questions answered on each day (local time) for the last `weeks` calendar weeks up to today, for the review
    heatmap. Days with no answers are left out. Counts questions, not attempts, like everything else here."""
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now).date()
    first = today - timedelta(days=today.weekday() + 7 * (weeks - 1))  # the Monday that starts the first week shown
    since = datetime.combine(first, datetime.min.time()).timestamp()
    counts: dict[date, int] = {}
    for r in db.attempts_in(profile_ids, exercise, since):
        if r["attempt_no"] == 1:
            day = datetime.fromtimestamp(r["answered_at"]).date()
            counts[day] = counts.get(day, 0) + 1
    return counts


def collect(db: Database, profile_ids: list[int] | None, exercise: str | None = None, since: float | None = None,
            now: float | None = None, hardest: int = 8) -> Stats:
    """Everything the statistics screen shows for these profiles (None = all of them), this exercise (None = all) and
    answers from `since` (a timestamp, None = from the start) up to now."""
    now = time.time() if now is None else now
    rows = db.attempts_in(profile_ids, exercise, since)
    out = Stats(attempts=len(rows))
    if rows:
        start = datetime.fromtimestamp(since if since is not None else rows[0]["answered_at"])
        out.granularity = gran = _granularity((now - start.timestamp()) / 86400)
        cursor, end = _floor(start, gran), datetime.fromtimestamp(now)
        buckets: dict[datetime, Bucket] = {}
        while cursor <= end:
            buckets[cursor] = Bucket(cursor, _label(cursor, gran))
            cursor = _next(cursor, gran)
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
            b = buckets.get(_floor(when, gran))
            if b:
                b.questions += 1
                b.first_right += ok
                b.times.append(seconds)
        out.buckets = list(buckets.values())
        out.days_practised = len(days)
        out.median_seconds = statistics.median(times) if times else None
        out.by_exercise = sorted(
            (ExerciseStats(name, len(v), 100.0 * sum(ok for ok, _ in v) / len(v), statistics.median(t for _, t in v))
             for name, v in per_exercise.items()), key=lambda e: e.exercise)
    for r in db.strained_items(profile_ids, exercise, since, min_strain=scheduler.NEW_STRAIN, limit=hardest):
        try:
            text = describe(Question.from_dict(json.loads(r["payload"])))
        except (ValueError, KeyError, TypeError):
            continue
        out.hardest.append(HardQuestion(r["exercise"], text, r["strain"], r["seen"], r["wrong"]))
    return out
