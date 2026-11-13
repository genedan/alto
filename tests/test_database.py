"""The database: profiles, the stored questions and answers, and the read-only views the browser uses."""

import json
import random
import sqlite3

import pytest

from alto.exercises.base import (
    Exercise,
    Question,
)
from alto.learning import (
    Database,
    Learner,
)
from alto.learning.database import ItemRecord
from alto.theory.pitch import Note


def question(letter: int = 0) -> Question:
    """
    Make a two-choice question on a staff.

    Parameters
    ----------
    letter : int
        The letter of the note shown (0 is C).

    Returns
    -------
    Question
        The question.
    """
    return Question(
        "",
        choices=["A", "B"],
        answer="A",
        staff=[[Note(4, letter=letter)]],
    )


def test_a_profile_can_be_found_by_id_and_removed_with_its_history() -> None:
    """
    Check that a profile can be found by id and removed with its history.
    """
    db = Database()
    ada, ben = db.add_profile("Ada"), db.add_profile("Ben")
    assert db.profile(ada.id) == ada and db.profile(9999) is None
    q = question()
    learner = Learner(db, profile=ada)

    class Stub(Exercise):
        """
        An exercise that always asks the same question.
        """

        par_seconds = 4.0

        def generate(self, rng: random.Random) -> Question:
            """
            Make the same question every time.

            Parameters
            ----------
            rng : random.Random
                The random source (not used: the question is fixed).

            Returns
            -------
            Question
                A question.
            """
            return q

    learner.record(
        Stub(),
        question=q,
        answer="A",
        correct=True,
        attempt_no=1,
        seconds=2.0,
    )
    assert db.count_attempts(ada.id) == 1
    db.delete_profile(ada.id)
    assert db.profile(ada.id) is None and db.count_attempts(ada.id) == 0  # the answers go with the profile
    assert [p.name for p in db.profiles()] == ["Ben"] and db.profile(ben.id) == ben


def test_the_browser_rows_come_newest_first_with_the_stored_question() -> None:
    """
    Check that the browser rows come newest first with the stored question.
    """
    db = Database()
    ada = db.add_profile("Ada")
    q = question()
    payload = json.dumps(q.to_dict())
    db.save_item(
        ada.id,
        exercise="Stub",
        item_key=q.item_key(),
        item=ItemRecord(
            1.5,
            seen=1,
            first_try_right=0,
            wrong_attempts=1,
            total_first_ms=2000,
            last_seen=10.0,
            signature="sig",
            payload=payload,
        ),
    )
    db.add_attempt(
        ada.id,
        exercise="Stub",
        item_key=q.item_key(),
        attempt_no=1,
        answer="B",
        correct=False,
        duration_ms=1500,
        answered_at=10.0,
    )
    db.add_attempt(
        ada.id,
        exercise="Stub",
        item_key=q.item_key(),
        attempt_no=2,
        answer="A",
        correct=True,
        duration_ms=900,
        answered_at=11.0,
    )
    rows = db.attempt_rows(ada.id)
    assert [r["attempt_no"] for r in rows] == [2, 1]
    assert rows[0]["payload"] == payload and rows[0]["answer"] == "A"
    assert [r["item_key"] for r in db.item_rows(ada.id)] == [q.item_key()]
    profiles = db.profile_rows()
    assert [(r["name"], r["attempts"], r["questions"]) for r in profiles] == [("Ada", 2, 1)]


def test_the_item_rows_list_the_hardest_questions_first() -> None:
    """
    Check that the item rows list the hardest questions first.
    """
    db = Database()
    ada = db.add_profile("Ada")
    for i, strain in enumerate((1.0, 5.0, 3.0)):
        q = question(i)
        db.save_item(
            ada.id,
            exercise="Stub",
            item_key=q.item_key(),
            item=ItemRecord(
                strain,
                seen=1,
                first_try_right=0,
                wrong_attempts=0,
                total_first_ms=0,
                last_seen=float(i),
                signature="",
                payload=json.dumps(q.to_dict()),
            ),
        )
    assert [r["strain"] for r in db.item_rows(ada.id)] == [5.0, 3.0, 1.0]
    assert len(db.item_rows(ada.id, limit=2)) == 2


def test_a_closed_database_refuses_further_work() -> None:
    """
    Check that a closed database refuses further work.
    """
    db = Database()
    db.close()
    with pytest.raises(sqlite3.ProgrammingError):
        db.profiles()
