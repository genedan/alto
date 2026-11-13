"""
Ties the profile, the database and the scheduler together for the exercise screen.

Examples
--------
>>> from alto.exercises.library import NoteNames
>>> db = Database()
>>> learner = Learner(db, profile=db.add_profile("Ada"))
>>> question = learner.pick(NoteNames(), rng=random.Random(1))
>>> question.answer in question.choices
True
"""

from __future__ import annotations

import json
import random
import time

from alto.exercises.base import (
    Exercise,
    Question,
)
from alto.learning import scheduler
from alto.learning.database import (
    Database,
    ItemRecord,
    Profile,
)


class Learner:
    """
    Chooses what a profile is asked next and records how it was answered.

    Attributes
    ----------
    FRESH : int
        How many new questions are generated for each pick, alongside the ones asked before.
    db : Database
        Where answers and what is known about each question are stored.
    profile : Profile
        Whose answers these are.

    Examples
    --------
    >>> from alto.exercises.library import NoteNames
    >>> db = Database()
    >>> learner = Learner(db, profile=db.add_profile("Ada"))
    >>> rng = random.Random(2)
    >>> question = learner.pick(NoteNames(), rng=rng)
    >>> learner.record(NoteNames(), question=question, answer=question.answer, correct=True, attempt_no=1, seconds=2.5)
    >>> db.count_attempts(learner.profile.id)
    1
    """

    FRESH = 10  # new questions generated for each pick, alongside the ones asked before

    def __init__(
        self,
        db: Database,
        *,
        profile: Profile,
    ) -> None:
        """
        Create a learner for one profile.

        Parameters
        ----------
        db : Database
            The database to read and write.
        profile : Profile
            The profile that is practising. Keyword-only.

        Examples
        --------
        >>> database = Database()
        >>> learner = Learner(database, profile=database.add_profile("Ada"))
        >>> learner.profile.name
        'Ada'
        """
        self.db = db
        self.profile = profile

    def pick(
        self,
        exercise: Exercise,
        *,
        rng: random.Random,
        avoid: str | None = None,
        now: float | None = None,
    ) -> Question:
        """
        Return the next question: a mix of new ones and ones asked before under the same settings, drawn by weight.

        Parameters
        ----------
        exercise : Exercise
            The exercise being practised.
        rng : random.Random
            The random number generator used to make new questions and to draw one. Keyword-only.
        avoid : str or None, default None
            The `item_key` of the question just asked, so it does not come straight back. Keyword-only.
        now : float or None, default None
            The current time as a timestamp; the clock is used if None. Keyword-only.

        Returns
        -------
        Question
            The question to ask.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> db = Database()
        >>> learner = Learner(db, profile=db.add_profile("Ada"))
        >>> first = learner.pick(NoteNames(), rng=random.Random(3))
        >>> second = learner.pick(NoteNames(), rng=random.Random(3), avoid=first.item_key())
        >>> second.item_key() != first.item_key()
        True
        """
        now = time.time() if now is None else now
        name = type(exercise).__name__
        options: dict[str, tuple[Question, float]] = {}
        for _ in range(self.FRESH):
            q = exercise.generate(rng)
            key = q.item_key()
            if key in options or key == avoid:
                continue
            item = self.db.get_item(self.profile.id, exercise=name, item_key=key)
            options[key] = (
                q,
                scheduler.weight(item.strain if item else None, last_seen=item.last_seen if item else None, now=now),
            )
        for item in self.db.replay_candidates(self.profile.id, exercise=name, signature=exercise.settings_signature()):
            if item.item_key in options or item.item_key == avoid:
                continue
            try:
                q = Question.from_dict(json.loads(item.payload))
            except (ValueError, KeyError, TypeError):
                continue
            options[item.item_key] = (q, scheduler.weight(item.strain, last_seen=item.last_seen, now=now))
        if not options:  # every candidate was the question to avoid
            return exercise.generate(rng)
        questions, weights = zip(*options.values())
        return scheduler.choose(questions, weights=weights, rng=rng)

    def record(
        self,
        exercise: Exercise,
        *,
        question: Question,
        answer: str,
        correct: bool,
        attempt_no: int,
        seconds: float,
        now: float | None = None,
    ) -> None:
        """
        Log one answer and update what is known about the question.

        Parameters
        ----------
        exercise : Exercise
            The exercise being practised.
        question : Question
            The question that was answered. Keyword-only.
        answer : str
            What was answered. Keyword-only.
        correct : bool
            Whether the answer was right. Keyword-only.
        attempt_no : int
            1 for the first answer to this showing of the question, 2 for the second and so on. Keyword-only.
        seconds : float
            How long the answer took. Keyword-only.
        now : float or None, default None
            When it was answered, as a timestamp; the clock is used if None. Keyword-only.

        Examples
        --------
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
        """
        now = time.time() if now is None else now
        name, key = type(exercise).__name__, question.item_key()
        self.db.add_attempt(
            self.profile.id,
            exercise=name,
            item_key=key,
            attempt_no=attempt_no,
            answer=answer,
            correct=correct,
            duration_ms=round(seconds * 1000),
            answered_at=now,
        )
        old = self.db.get_item(self.profile.id, exercise=name, item_key=key)
        strain = old.strain if old else scheduler.NEW_STRAIN
        strain = scheduler.update_strain(
            strain,
            correct=correct,
            attempt_no=attempt_no,
            seconds=seconds,
            par_seconds=exercise.par_seconds,
        )
        first = attempt_no == 1
        self.db.save_item(
            self.profile.id,
            exercise=name,
            item_key=key,
            item=ItemRecord(
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
