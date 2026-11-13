"""Ties the profile, the database and the scheduler together for the exercise screen."""

from __future__ import annotations

import json
import random
import time

from ..exercises.base import Exercise, Question
from . import scheduler
from .database import Database, ItemRecord, Profile


class Learner:
    FRESH = 10  # new questions generated for each pick, alongside the ones asked before

    def __init__(
        self,
        db: Database,
        profile: Profile,
    ):
        self.db = db
        self.profile = profile

    def pick(
        self,
        exercise: Exercise,
        rng: random.Random,
        avoid: str | None = None,
        now: float | None = None,
    ) -> Question:
        """The next question: a mix of new ones and ones asked before under the same settings, drawn by weight.

        `avoid` is the key of the question just asked, so it does not come straight back."""
        now = time.time() if now is None else now
        name = type(exercise).__name__
        options: dict[str, tuple[Question, float]] = {}
        for _ in range(self.FRESH):
            q = exercise.generate(rng)
            key = q.item_key()
            if key in options or key == avoid:
                continue
            item = self.db.get_item(self.profile.id, name, key)
            options[key] = (q, scheduler.weight(item.strain if item else None, item.last_seen if item else None, now))
        for item in self.db.replay_candidates(self.profile.id, name, exercise.settings_signature()):
            if item.item_key in options or item.item_key == avoid:
                continue
            try:
                q = Question.from_dict(json.loads(item.payload))
            except (ValueError, KeyError, TypeError):
                continue
            options[item.item_key] = (q, scheduler.weight(item.strain, item.last_seen, now))
        if not options:  # every candidate was the question to avoid
            return exercise.generate(rng)
        questions, weights = zip(*options.values())
        return scheduler.choose(questions, weights, rng)

    def record(
        self,
        exercise: Exercise,
        question: Question,
        answer: str,
        correct: bool,
        attempt_no: int,
        seconds: float,
        now: float | None = None,
    ) -> None:
        """Log one answer and update what is known about the question."""
        now = time.time() if now is None else now
        name, key = type(exercise).__name__, question.item_key()
        self.db.add_attempt(
            self.profile.id,
            name,
            key,
            attempt_no,
            answer,
            correct,
            round(seconds * 1000),
            now,
        )
        old = self.db.get_item(self.profile.id, name, key)
        strain = old.strain if old else scheduler.NEW_STRAIN
        strain = scheduler.update_strain(
            strain,
            correct,
            attempt_no,
            seconds,
            exercise.par_seconds,
        )
        first = attempt_no == 1
        self.db.save_item(
            self.profile.id,
            name,
            key,
            ItemRecord(
                strain=strain,
                seen=(old.seen if old else 0) + (1 if first else 0),
                first_try_right=(old.first_try_right if old else 0) + (1 if first and correct else 0),
                wrong_attempts=(old.wrong_attempts if old else 0) + (0 if correct else 1),
                total_first_ms=(old.total_first_ms if old else 0) + (round(seconds * 1000) if first else 0),
                last_seen=now,
                signature=exercise.settings_signature(),
                payload=json.dumps(question.to_dict()),
            ),
        )
