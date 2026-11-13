import random

import pytest
from alto.exercises.base import Exercise, Question
from alto.learning import Database, Learner, scheduler
from alto.theory.pitch import Note

# -- the scheduler --------------------------------------------------------------------------------------------------


def test_speed_term_runs_from_bonus_to_penalty():
    par = 4.0
    assert scheduler.speed_term(0.5, par_seconds=par) == -scheduler.FAST_BONUS  # very quick
    assert scheduler.speed_term(par, par_seconds=par) == 0.0  # right on par
    assert scheduler.speed_term(par * 10, par_seconds=par) == scheduler.SLOW_PENALTY  # as slow as it counts
    samples = [scheduler.speed_term(par * r / 10, par_seconds=par) for r in range(1, 60)]
    assert samples == sorted(samples)  # never rewards slowness


def test_quick_correct_answer_ends_up_easier_than_slow_one():
    quick = scheduler.update_strain(
        2.0,
        correct=True,
        attempt_no=1,
        seconds=0.5,
        par_seconds=4.0,
    )
    steady = scheduler.update_strain(
        2.0,
        correct=True,
        attempt_no=1,
        seconds=4.0,
        par_seconds=4.0,
    )
    slow = scheduler.update_strain(
        2.0,
        correct=True,
        attempt_no=1,
        seconds=40.0,
        par_seconds=4.0,
    )
    assert quick < steady < 2.0 < slow  # even a correct answer is held against you if it took too long


def test_every_extra_attempt_adds_strain():
    s = 1.5
    for _ in range(3):
        before = s
        s = scheduler.update_strain(
            s,
            correct=False,
            attempt_no=1,
            seconds=2.0,
            par_seconds=4.0,
        )
        assert s > before
    assert s == scheduler.STRAIN_MAX or s > 1.5 + 2 * scheduler.WRONG_PENALTY


def test_strain_stays_in_bounds():
    assert (
        scheduler.update_strain(
            0.1,
            correct=True,
            attempt_no=1,
            seconds=0.1,
            par_seconds=4.0,
        )
        == 0.0
    )
    assert (
        scheduler.update_strain(
            5.9,
            correct=False,
            attempt_no=1,
            seconds=1.0,
            par_seconds=4.0,
        )
        == scheduler.STRAIN_MAX
    )


def test_weight_grows_with_strain_and_new_questions_beat_mastered_ones():
    later = 10_000.0
    weights = [
        scheduler.weight(s, last_seen=0.0, now=later)
        for s in (
            0.0,
            1.0,
            2.0,
            4.0,
            6.0,
        )
    ]
    assert weights == sorted(weights)
    assert scheduler.weight(None, last_seen=None, now=later) > scheduler.weight(0.0, last_seen=0.0, now=later)


def test_a_question_just_seen_is_held_back_and_hard_ones_return_sooner():
    assert scheduler.weight(1.0, last_seen=100.0, now=101.0) < scheduler.weight(1.0, last_seen=0.0, now=101.0)
    # after the same short wait, the hard question has recovered more of its chance than the easy one
    easy = scheduler.weight(0.5, last_seen=0.0, now=60.0) / scheduler.weight(0.5, last_seen=0.0, now=1e6)
    hard = scheduler.weight(5.0, last_seen=0.0, now=60.0) / scheduler.weight(5.0, last_seen=0.0, now=1e6)
    assert hard > easy


# -- the database ---------------------------------------------------------------------------------------------------


def test_profiles_are_unique_ignoring_case_and_need_a_name():
    db = Database()
    first = db.add_profile("  Ada   Lovelace ")
    assert first.name == "Ada Lovelace"
    with pytest.raises(ValueError):
        db.add_profile("ada lovelace")
    with pytest.raises(ValueError):
        db.add_profile("   ")
    assert [p.name for p in db.profiles()] == ["Ada Lovelace"]


def test_database_is_created_on_disk_and_reopened(tmp_path):
    path = tmp_path / "nested" / "alto.db"
    Database(path).add_profile("Ben")
    assert [p.name for p in Database(path).profiles()] == ["Ben"]


# -- the learner ----------------------------------------------------------------------------------------------------


class Stub(Exercise):
    """A question per note A0..: one correct button, with a pool big enough that fresh ones rarely repeat."""

    name, par_seconds = "Stub", 4.0

    def generate(self, rng):
        n = Note.from_diatonic(rng.randint(14, 60))
        return Question(
            "",
            choices=["A", "B"],
            answer="A",
            staff=[[n]],
        )


def distinct(
    ex,
    *,
    count,
    rng,
):
    """`count` questions that are all different from each other."""
    found = {}
    while len(found) < count:
        q = ex.generate(rng)
        found.setdefault(q.item_key(), q)
    return list(found.values())


def make_learner():
    db = Database()
    return Learner(db, profile=db.add_profile("Tester")), Stub()


def test_every_answer_is_recorded_including_the_wrong_ones():
    learner, ex = make_learner()
    q = ex.generate(random.Random(1))
    learner.record(
        ex,
        question=q,
        answer="B",
        correct=False,
        attempt_no=1,
        seconds=2.0,
        now=100.0,
    )
    learner.record(
        ex,
        question=q,
        answer="B",
        correct=False,
        attempt_no=2,
        seconds=1.0,
        now=102.0,
    )
    learner.record(
        ex,
        question=q,
        answer="A",
        correct=True,
        attempt_no=3,
        seconds=1.5,
        now=104.0,
    )
    rows = learner.db.attempts(learner.profile.id)
    assert [(r["attempt_no"], r["answer"], r["correct"]) for r in rows] == [(1, "B", 0), (2, "B", 0), (3, "A", 1)]
    item = learner.db.get_item(learner.profile.id, exercise="Stub", item_key=q.item_key())
    assert item is not None
    assert (item.seen, item.first_try_right, item.wrong_attempts) == (1, 0, 2)


def test_more_attempts_and_slower_answers_leave_a_question_more_strained():
    learner, ex = make_learner()
    rng = random.Random(2)
    clean, fumbled, slow, quick = distinct(ex, count=4, rng=rng)
    learner.record(
        ex,
        question=clean,
        answer="A",
        correct=True,
        attempt_no=1,
        seconds=4.0,
        now=1.0,
    )
    learner.record(
        ex,
        question=fumbled,
        answer="B",
        correct=False,
        attempt_no=1,
        seconds=4.0,
        now=1.0,
    )
    learner.record(
        ex,
        question=fumbled,
        answer="B",
        correct=False,
        attempt_no=2,
        seconds=4.0,
        now=2.0,
    )
    learner.record(
        ex,
        question=fumbled,
        answer="A",
        correct=True,
        attempt_no=3,
        seconds=4.0,
        now=3.0,
    )
    learner.record(
        ex,
        question=slow,
        answer="A",
        correct=True,
        attempt_no=1,
        seconds=30.0,
        now=1.0,
    )
    learner.record(
        ex,
        question=quick,
        answer="A",
        correct=True,
        attempt_no=1,
        seconds=0.5,
        now=1.0,
    )

    def strain_of(q):
        item = learner.db.get_item(learner.profile.id, exercise="Stub", item_key=q.item_key())
        assert item is not None
        return item.strain

    strain = {
        n: strain_of(q)
        for n, q in (
            ("clean", clean),
            ("fumbled", fumbled),
            ("slow", slow),
            ("quick", quick),
        )
    }
    assert strain["fumbled"] > strain["slow"] > strain["clean"] > strain["quick"]


def test_a_hard_question_comes_back_far_more_often_than_a_mastered_one():
    learner, ex = make_learner()
    rng = random.Random(3)
    hard, easy = distinct(ex, count=2, rng=rng)
    for attempt in (1, 2, 3):
        learner.record(
            ex,
            question=hard,
            answer="B",
            correct=False,
            attempt_no=attempt,
            seconds=8.0,
            now=0.0,
        )
    for _ in range(3):
        learner.record(
            ex,
            question=easy,
            answer="A",
            correct=True,
            attempt_no=1,
            seconds=0.5,
            now=0.0,
        )
    later = 3600.0  # an hour on, so neither is being held back
    counts = {"hard": 0, "easy": 0}
    for _ in range(400):
        q = learner.pick(ex, rng=rng, now=later)
        if q.item_key() == hard.item_key():
            counts["hard"] += 1
        elif q.item_key() == easy.item_key():
            counts["easy"] += 1
    assert counts["hard"] > 40 and counts["hard"] > 8 * max(counts["easy"], 1)


def test_pick_never_repeats_the_question_just_asked():
    learner, ex = make_learner()
    rng = random.Random(4)
    last = ex.generate(rng)
    learner.record(
        ex,
        question=last,
        answer="B",
        correct=False,
        attempt_no=1,
        seconds=9.0,
        now=0.0,
    )
    for _ in range(100):
        assert (
            learner.pick(
                ex,
                rng=rng,
                avoid=last.item_key(),
                now=1e6,
            ).item_key()
            != last.item_key()
        )


def test_stored_questions_are_only_asked_again_under_the_same_settings():
    learner, ex = make_learner()
    rng = random.Random(5)
    q = ex.generate(rng)
    for attempt in (1, 2, 3):
        learner.record(
            ex,
            question=q,
            answer="B",
            correct=False,
            attempt_no=attempt,
            seconds=8.0,
            now=0.0,
        )
    assert any(
        i.item_key == q.item_key() for i in learner.db.replay_candidates(learner.profile.id, exercise="Stub", signature="")
    )
    assert learner.db.replay_candidates(learner.profile.id, exercise="Stub", signature="other settings") == []


def test_each_profile_has_its_own_history():
    db = Database()
    ada, ben = db.add_profile("Ada"), db.add_profile("Ben")
    ex = Stub()
    q = ex.generate(random.Random(6))
    Learner(db, profile=ada).record(
        ex,
        question=q,
        answer="B",
        correct=False,
        attempt_no=1,
        seconds=5.0,
        now=0.0,
    )
    assert db.get_item(ben.id, exercise="Stub", item_key=q.item_key()) is None
    assert len(db.attempts(ben.id)) == 0 and len(db.attempts(ada.id)) == 1


# -- the exercise screen --------------------------------------------------------------------------------------------


def test_exercise_view_records_each_answer_with_its_timing():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from alto.exercises.library import KeySignatures
    from alto.ui.exercise_view import ExerciseView
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])  # kept alive for the widgets below
    learner, _ = make_learner()
    view = ExerciseView(KeySignatures(), rng=random.Random(7), learner=learner)
    q = view.question
    assert q is not None
    wrong = next(b for b in view.buttons if b.text() != q.answer)
    right = next(b for b in view.buttons if b.text() == q.answer)
    wrong.click()
    right.click()
    rows = learner.db.attempts(learner.profile.id, exercise="KeySignatures")
    assert [(r["attempt_no"], r["correct"]) for r in rows] == [(1, 0), (2, 1)]
    assert all(r["item_key"] == q.item_key() for r in rows)
    item = learner.db.get_item(learner.profile.id, exercise="KeySignatures", item_key=q.item_key())
    assert item is not None and item.wrong_attempts == 1
    view._advance.stop()
    view.next_question()
    assert view.question is not None and view.question.item_key() != q.item_key()  # the next one is a different question
