"""The exercise screen: the sound and settings buttons, placing notes on the staff, and what is ignored."""

import random

import pytest
from alto import settings
from alto.audio import sounds
from alto.exercises.library import (
    ArpeggioNames,
    IntervalNames,
    KeyboardNotes,
    KeySignatures,
    NoteConstruction,
    NoteNames,
)
from alto.theory.pitch import Note
from alto.ui.exercise_view import ExerciseView
from PySide6.QtTest import QTest


def view_of(
    exercise,
    *,
    seed=1,
    **kw,
):
    return ExerciseView(exercise, rng=random.Random(seed), **kw)


def asked(view):
    """The question on screen (there is always one)."""
    assert view.question is not None
    return view.question


def test_the_speaker_button_mutes_and_unmutes(app):
    view = view_of(KeySignatures())
    sounds.enabled = True
    view._show_sound_state()
    assert "mute)" in view.sound_btn.toolTip() and view.sound_btn.toolTip().startswith("Sound on")
    view.sound_btn.click()
    assert not sounds.enabled and view.sound_btn.toolTip().startswith("Muted")
    view.sound_btn.click()
    assert sounds.enabled


def test_an_exercise_with_fixed_rules_has_no_settings_button(app):
    view = view_of(IntervalNames())
    assert view.settings_panel is None and not hasattr(view, "gear") and not hasattr(view, "pane")


def test_the_settings_pane_slides_open_and_shut(app):
    view = view_of(NoteNames())
    view.show()
    assert not view.pane.isVisible() and view.pane.maximumWidth() == 0
    view.gear.setChecked(True)
    QTest.qWait(320)
    assert view.pane.isVisible() and view.pane.maximumWidth() == view.PANE_WIDTH
    view.gear.setChecked(False)
    QTest.qWait(320)
    assert view.pane.maximumWidth() == 0 and not view.pane.isVisible()


def test_a_change_in_the_settings_asks_a_new_question_straight_away(app):
    view = view_of(NoteNames())
    before = view.question
    assert view.settings_panel is not None
    view.settings_panel.changed.emit()
    assert view.question is not before


def test_the_choices_have_number_key_shortcuts_when_there_are_few_enough(app):
    view = view_of(KeySignatures())
    assert [b.toolTip() for b in view.buttons] == [f"Key {i + 1}" for i in range(len(view.buttons))]
    arpeggio = view_of(ArpeggioNames())
    assert all(b.toolTip() == "" for b in arpeggio.buttons)  # a two-part answer has no shortcuts


def test_the_score_starts_empty_and_counts_only_first_answers(app):
    view = view_of(KeySignatures())
    assert view.score.text() == "0/0 (–)   streak 0"
    q = asked(view)
    wrong = next(b for b in view.buttons if b.text() != q.answer)
    right = next(b for b in view.buttons if b.text() == q.answer)
    wrong.click()
    right.click()
    assert view.score.text() == "0/1 (0%)   streak 0"  # the miss counted, the later right answer did not
    right.click()  # answered already: ignored
    assert (view.correct, view.total) == (0, 1)
    view._advance.stop()


# -- placing a note on the staff ------------------------------------------------------------------------------------


@pytest.fixture
def construction(app):
    settings.construction.accidentals = True
    settings.construction.key_signature = False
    return view_of(NoteConstruction(), seed=4)


def test_a_construction_question_shows_the_staff_to_click_and_the_sign_buttons(construction):
    q = asked(construction)
    assert q.construct is not None and not construction.staff.isVisibleTo(construction)
    assert construction.input_staff.isVisibleTo(construction) and construction.accidental_row.isVisibleTo(construction)
    assert construction.accidental_buttons.keys() == {-1, 0, 1}


def test_the_sign_buttons_act_like_a_radio_group_that_can_be_cleared(construction):
    sharp, flat = construction.accidental_buttons[1], construction.accidental_buttons[-1]
    sharp.click()
    assert sharp.isChecked() and construction.input_staff.accidental == 1
    flat.click()
    assert flat.isChecked() and not sharp.isChecked() and construction.input_staff.accidental == -1
    flat.click()  # the lit one again: no sign
    assert not flat.isChecked() and construction.input_staff.accidental is None


def test_right_click_steps_through_the_signs(construction):
    seen = []
    for _ in range(4):
        construction.input_staff.accidental_cycled.emit()
        seen.append(construction.input_staff.accidental)
    assert seen == [
        1,
        -1,
        None,
        1,
    ]  # with no key signature, a natural is the same as no sign
    construction.question.key = 2
    construction.input_staff.accidental = -1
    construction.input_staff.accidental_cycled.emit()
    assert construction.input_staff.accidental == 0  # under a key signature there is a natural too
    construction.input_staff.accidental_cycled.emit()
    assert construction.input_staff.accidental is None
    construction.input_staff.accidental = 99  # something outside the cycle starts it again
    construction.input_staff.accidental_cycled.emit()
    assert construction.input_staff.accidental is None


def test_right_click_does_nothing_without_the_sign_buttons(app):
    settings.construction.accidentals = False
    view = view_of(NoteConstruction())
    view.input_staff.accidental_cycled.emit()
    assert view.input_staff.accidental is None
    other = view_of(KeySignatures())
    other._cycle_accidental()  # not a construction question at all


def test_placing_the_right_note_scores_locks_the_staff_and_moves_on(construction):
    q = asked(construction)
    first = q
    construction._place(q.construct)
    assert construction.answered and (construction.correct, construction.total) == (1, 1)
    assert construction.input_staff.locked and construction._advance.isActive()
    construction._place(q.construct)  # a second click on the same question is ignored
    assert construction.total == 1
    construction._advance.stop()
    construction.next_question()
    assert construction.question is not first and not construction.input_staff.locked


def test_a_wrong_note_is_shown_then_cleared_for_another_try(construction):
    q = asked(construction)
    wrong = Note(q.construct.octave, letter=(q.construct.letter + 1) % 7)
    construction._place(wrong)
    assert construction.missed and not construction.answered and construction._busy and construction.total == 1
    construction._place(q.construct)  # while the miss is showing, clicks are ignored
    assert not construction.answered
    QTest.qWait(1000)
    assert not construction._busy and not construction.input_staff.locked and construction.input_staff.columns == []
    construction._place(q.construct)
    assert construction.answered and (construction.correct, construction.total) == (0, 1)  # still a miss overall
    construction._advance.stop()


def test_a_new_question_cancels_the_clearing_of_the_old_one(construction):
    q = asked(construction)
    construction._place(Note(q.construct.octave, letter=(q.construct.letter + 2) % 7))
    construction.next_question()  # before the 900 ms are up
    assert not construction._busy
    QTest.qWait(1000)  # the old timer fires and must leave the new question alone
    assert not construction.input_staff.locked and not construction._busy


def test_clicks_on_a_question_that_is_not_construction_are_ignored(app):
    view = view_of(KeySignatures())
    view._place(Note(4, letter=0))
    assert view.total == 0


# -- two-part answers: what is ignored ------------------------------------------------------------------------------


def test_choices_are_ignored_once_the_question_is_answered_or_while_a_miss_shows(app):
    view = view_of(ArpeggioNames(), seed=3)
    q = asked(view)
    kind, inversion = q.answer.split(q.joiner)
    names = {b.text(): b for b in view.buttons}
    wrong = next(t for t in q.choices if t != kind)
    names[wrong].click()
    names[inversion].click()  # a wrong pair: a miss is showing
    assert view._busy
    names[kind].click()
    assert view._pending.get("name") is not None and view._pending["name"][0] == wrong  # ignored while busy
    QTest.qWait(800)
    names[kind].click()
    names[inversion].click()
    assert view.answered
    other = next(t for t in q.choices if t != kind)
    names[other].click()
    assert view._pending["name"][0] == kind  # ignored once answered
    view._advance.stop()


def test_choosing_a_different_type_unlights_the_one_before(app):
    view = view_of(ArpeggioNames(), seed=5)
    names = {b.text(): b for b in view.buttons}
    first, second = asked(view).choices[:2]
    names[first].click()
    names[second].click()
    assert names[second].isChecked() and not names[first].isChecked()
    view._advance.stop()


# -- feedback and the less common orderings -------------------------------------------------------------------------


def test_a_right_answer_fades_the_staff_notes_to_green(app):
    view = view_of(NoteNames(), seed=2)
    q = asked(view)
    next(b for b in view.buttons if b.text() == q.answer).click()
    QTest.qWait(450)  # the colour fades in over about 350 ms
    assert view.staff.note_color is not None and view.staff.note_color.green() > view.staff.note_color.red()
    view._advance.stop()


def test_a_right_answer_fades_the_highlighted_key_to_green(app):
    view = view_of(KeyboardNotes(), seed=2)
    assert view.settings_panel is not None and view.keyboard.isVisibleTo(view)
    q = asked(view)
    assert q.keyboard is not None
    next(b for b in view.buttons if b.text() == q.answer).click()
    QTest.qWait(450)
    view._advance.stop()


def test_a_second_submit_after_the_question_is_answered_is_ignored(app):
    view = view_of(KeySignatures(), seed=2)
    q = asked(view)
    right = next(b for b in view.buttons if b.text() == q.answer)
    right.click()
    view.submit(q.answer, button=right)  # the button is disabled and the question answered
    assert (view.correct, view.total) == (1, 1)
    view._advance.stop()


def test_a_wrong_pair_clears_itself_unless_a_new_question_has_come(app):
    view = view_of(ArpeggioNames(), seed=3)
    q = asked(view)
    kind, inversion = q.answer.split(q.joiner)
    wrong = next(t for t in q.choices if t != kind)
    names = {b.text(): b for b in view.buttons}
    names[wrong].click()
    names[inversion].click()
    assert view._busy
    view.next_question()  # before the 700 ms are up
    QTest.qWait(800)  # the old timer fires and finds its question gone
    assert not view._busy and view._pending == {}
    view._advance.stop()


# -- the music stays a readable size in a wide window -----------------------------------------------------------------


def test_in_a_wide_window_the_staff_is_capped_and_centred(app):
    view = view_of(NoteNames(), seed=2)
    view.resize(2400, 700)
    view.show()
    QTest.qWait(50)
    staff = view.staff
    assert staff.width() == staff.maximumWidth() < 1000  # a single note is not spread over the whole window
    parent = staff.parentWidget()
    assert parent is not None
    left, right = staff.x(), parent.width() - staff.x() - staff.width()
    assert left > 200 and abs(left - right) <= 2  # centred
    view.hide()


def test_the_staff_for_placing_a_note_is_capped_too(app):
    settings.construction.accidentals = False
    view = view_of(NoteConstruction(), seed=4)
    view.resize(2400, 700)
    view.show()
    QTest.qWait(50)
    assert view.input_staff.width() == view.input_staff.maximumWidth() < 1000
    view.hide()
