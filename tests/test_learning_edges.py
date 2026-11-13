"""Less common paths of the learner and of the statistics text."""

import json
import random

from alto.exercises.base import Exercise, Question
from alto.learning import Database, Learner, stats
from alto.learning.database import ItemRecord
from alto.theory.pitch import Note


class Fixed(Exercise):
    """Always the same question, so that the only other candidates are stored ones."""

    name, par_seconds = "Fixed", 4.0

    def generate(self, rng):
        return Question(
            "",
            choices=["A", "B"],
            answer="A",
            staff=[[Note(4, letter=0)]],
        )


def test_a_stored_question_that_cannot_be_read_is_skipped():
    db = Database()
    learner = Learner(db, profile=db.add_profile("Ada"))
    ex = Fixed()
    sig, pid = ex.settings_signature(), learner.profile.id
    db.save_item(
        pid,
        exercise="Fixed",
        item_key="broken",
        item=ItemRecord(
            5.0,
            seen=1,
            first_try_right=0,
            wrong_attempts=3,
            total_first_ms=0,
            last_seen=1.0,
            signature=sig,
            payload="{not json",
            item_key="broken",
        ),
    )
    wrong_shape = ItemRecord(
        5.0,
        seen=1,
        first_try_right=0,
        wrong_attempts=3,
        total_first_ms=0,
        last_seen=1.0,
        signature=sig,
        payload=json.dumps({"x": 1}),
        item_key="wrong-shape",
    )
    db.save_item(
        pid,
        exercise="Fixed",
        item_key="wrong-shape",
        item=wrong_shape,
    )
    assert learner.pick(ex, rng=random.Random(1)).answer == "A"  # the bad ones are ignored, a fresh question is asked


def test_when_the_only_question_is_the_one_to_avoid_a_new_one_is_made():
    db = Database()
    learner = Learner(db, profile=db.add_profile("Ada"))
    ex = Fixed()
    only = ex.generate(random.Random(0))
    assert learner.pick(ex, rng=random.Random(1), avoid=only.item_key()).item_key() == only.item_key()


def test_no_questions_means_no_accuracy_and_no_median():
    db = Database()
    ada = db.add_profile("Ada")
    s = stats.collect(db, profile_ids=[ada.id], now=1000.0)
    assert s.questions == 0 and s.accuracy is None and s.median_seconds is None


def test_a_question_is_described_whatever_it_shows():
    flats = Question(
        "",
        choices=["a"],
        answer="A",
        staff=[[Note(4, letter=2, accidental=-1)]],
        clef="bass",
        key=-3,
    )
    assert stats.describe(flats) == "Bass: E♭4 (3 flats) → A"
    sharps = Question(
        "",
        choices=["A"],
        answer="A",
        staff=[[Note(4, letter=0)], [Note(4, letter=4)]],
        key=2,
    )
    assert stats.describe(sharps).startswith("Treble: C4 – G4 (2 sharps)")
    keyboard = Question(
        "",
        choices=["A"],
        answer="A",
        keyboard=Note(4, letter=0),
        key=2,
    )
    assert stats.describe(keyboard) == "Key C4 in 2 sharps → A"
    assert (
        stats.describe(
            Question(
                "",
                choices=["A"],
                answer="A",
                keyboard=Note(4, letter=0),
                key=-1,
            ),
        )
        == "Key C4 in 1 flats → A"
    )
    assert stats.describe(Question("Which?", choices=["A", "B"], answer="B")) == "Which? → B"
    assert stats.describe(Question("", choices=["A"], answer="A")) == "A"  # nothing is drawn, so the answer is all there is


def test_the_hardest_questions_skip_stored_ones_that_cannot_be_read():
    db = Database()
    ada = db.add_profile("Ada")
    good = Question(
        "",
        choices=["A"],
        answer="A",
        staff=[[Note(4, letter=1)]],
    )
    stored = ItemRecord(
        4.0,
        seen=2,
        first_try_right=0,
        wrong_attempts=3,
        total_first_ms=0,
        last_seen=1.0,
        signature="",
        payload=json.dumps(good.to_dict()),
        item_key=good.item_key(),
    )
    db.save_item(
        ada.id,
        exercise="Fixed",
        item_key=good.item_key(),
        item=stored,
    )
    db.save_item(
        ada.id,
        exercise="Fixed",
        item_key="bad",
        item=ItemRecord(
            5.0,
            seen=2,
            first_try_right=0,
            wrong_attempts=3,
            total_first_ms=0,
            last_seen=1.0,
            signature="",
            payload="{nope",
            item_key="bad",
        ),
    )
    db.add_attempt(
        ada.id,
        exercise="Fixed",
        item_key=good.item_key(),
        attempt_no=1,
        answer="B",
        correct=False,
        duration_ms=1000,
        answered_at=5.0,
    )
    s = stats.collect(db, profile_ids=[ada.id], now=100.0)
    assert [h.text for h in s.hardest] == ["Treble: D4 → A"]
