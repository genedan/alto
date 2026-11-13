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
        return Question("", ["A", "B"], "A", [[Note(4, 0)]])


def test_a_stored_question_that_cannot_be_read_is_skipped():
    db = Database()
    learner = Learner(db, db.add_profile("Ada"))
    ex = Fixed()
    sig, pid = ex.settings_signature(), learner.profile.id
    db.save_item(pid, "Fixed", "broken", ItemRecord(5.0, 1, 0, 3, 0, 1.0, sig, "{not json", "broken"))
    wrong_shape = ItemRecord(5.0, 1, 0, 3, 0, 1.0, sig, json.dumps({"x": 1}), "wrong-shape")
    db.save_item(pid, "Fixed", "wrong-shape", wrong_shape)
    assert learner.pick(ex, random.Random(1)).answer == "A"  # the bad ones are ignored, a fresh question is asked


def test_when_the_only_question_is_the_one_to_avoid_a_new_one_is_made():
    db = Database()
    learner = Learner(db, db.add_profile("Ada"))
    ex = Fixed()
    only = ex.generate(random.Random(0))
    assert learner.pick(ex, random.Random(1), avoid=only.item_key()).item_key() == only.item_key()


def test_no_questions_means_no_accuracy_and_no_median():
    db = Database()
    ada = db.add_profile("Ada")
    s = stats.collect(db, [ada.id], now=1000.0)
    assert s.questions == 0 and s.accuracy is None and s.median_seconds is None


def test_a_question_is_described_whatever_it_shows():
    flats = Question("", ["a"], "A", [[Note(4, 2, -1)]], clef="bass", key=-3)
    assert stats.describe(flats) == "Bass: E♭4 (3 flats) → A"
    sharps = Question("", ["A"], "A", [[Note(4, 0)], [Note(4, 4)]], key=2)
    assert stats.describe(sharps).startswith("Treble: C4 – G4 (2 sharps)")
    keyboard = Question("", ["A"], "A", keyboard=Note(4, 0), key=2)
    assert stats.describe(keyboard) == "Key C4 in 2 sharps → A"
    assert stats.describe(Question("", ["A"], "A", keyboard=Note(4, 0), key=-1)) == "Key C4 in 1 flats → A"
    assert stats.describe(Question("Which?", ["A", "B"], "B")) == "Which? → B"
    assert stats.describe(Question("", ["A"], "A")) == "A"  # nothing is drawn, so the answer is all there is


def test_the_hardest_questions_skip_stored_ones_that_cannot_be_read():
    db = Database()
    ada = db.add_profile("Ada")
    good = Question("", ["A"], "A", [[Note(4, 1)]])
    stored = ItemRecord(4.0, 2, 0, 3, 0, 1.0, "", json.dumps(good.to_dict()), good.item_key())
    db.save_item(ada.id, "Fixed", good.item_key(), stored)
    db.save_item(ada.id, "Fixed", "bad", ItemRecord(5.0, 2, 0, 3, 0, 1.0, "", "{nope", "bad"))
    db.add_attempt(ada.id, "Fixed", good.item_key(), 1, "B", False, 1000, 5.0)
    s = stats.collect(db, [ada.id], now=100.0)
    assert [h.text for h in s.hardest] == ["Treble: D4 → A"]
