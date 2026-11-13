"""The database: profiles, the stored questions and answers, and the read-only views the browser uses."""

import json

import pytest
from alto.exercises.base import Exercise, Question
from alto.learning import Database, Learner
from alto.learning.database import ItemRecord
from alto.theory.pitch import Note


def question(letter=0):
    return Question("", ["A", "B"], "A", [[Note(4, letter)]])


def test_a_profile_can_be_found_by_id_and_removed_with_its_history():
    db = Database()
    ada, ben = db.add_profile("Ada"), db.add_profile("Ben")
    assert db.profile(ada.id) == ada and db.profile(9999) is None
    q = question()
    learner = Learner(db, ada)

    class Stub(Exercise):
        par_seconds = 4.0

        def generate(self, rng):
            return q

    learner.record(Stub(), q, "A", True, 1, 2.0)
    assert db.count_attempts(ada.id) == 1
    db.delete_profile(ada.id)
    assert db.profile(ada.id) is None and db.count_attempts(ada.id) == 0  # the answers go with the profile
    assert [p.name for p in db.profiles()] == ["Ben"] and db.profile(ben.id) == ben


def test_the_browser_rows_come_newest_first_with_the_stored_question():
    db = Database()
    ada = db.add_profile("Ada")
    q = question()
    payload = json.dumps(q.to_dict())
    db.save_item(ada.id, "Stub", q.item_key(), ItemRecord(1.5, 1, 0, 1, 2000, 10.0, "sig", payload))
    db.add_attempt(ada.id, "Stub", q.item_key(), 1, "B", False, 1500, 10.0)
    db.add_attempt(ada.id, "Stub", q.item_key(), 2, "A", True, 900, 11.0)
    rows = db.attempt_rows(ada.id)
    assert [r["attempt_no"] for r in rows] == [2, 1]
    assert rows[0]["payload"] == payload and rows[0]["answer"] == "A"
    assert [r["item_key"] for r in db.item_rows(ada.id)] == [q.item_key()]
    profiles = db.profile_rows()
    assert [(r["name"], r["attempts"], r["questions"]) for r in profiles] == [("Ada", 2, 1)]


def test_the_item_rows_list_the_hardest_questions_first():
    db = Database()
    ada = db.add_profile("Ada")
    for i, strain in enumerate((1.0, 5.0, 3.0)):
        q = question(i)
        db.save_item(ada.id, "Stub", q.item_key(), ItemRecord(strain, 1, 0, 0, 0, float(i), "", json.dumps(q.to_dict())))
    assert [r["strain"] for r in db.item_rows(ada.id)] == [5.0, 3.0, 1.0]
    assert len(db.item_rows(ada.id, limit=2)) == 2


def test_a_closed_database_refuses_further_work():
    import sqlite3

    db = Database()
    db.close()
    with pytest.raises(sqlite3.ProgrammingError):
        db.profiles()
