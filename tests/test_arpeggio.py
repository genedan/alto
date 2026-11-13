import copy
import os
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from alto import settings
from alto.exercises.library import ARPEGGIO_WINDOWS, ArpeggioNames
from alto.theory.pitch import Note
from alto.theory.scales import CHORDS, INVERSION_NAMES, arpeggio


@pytest.fixture
def cfg():
    """The arpeggio settings, put back as they were after the test."""
    saved = copy.deepcopy(settings.arpeggio)
    yield settings.arpeggio
    settings.arpeggio.__dict__.update(saved.__dict__)


def names(notes):
    return " ".join(n.name for n in notes)


def test_an_arpeggio_rises_from_the_bass_note_to_its_octave():
    c = Note(4, 0)
    assert names(arpeggio(c, CHORDS["major"], 0)) == "C E G C"
    assert names(arpeggio(c, CHORDS["major"], 1)) == "E G C E"
    assert names(arpeggio(c, CHORDS["major"], 2)) == "G C E G"
    assert names(arpeggio(c, CHORDS["dominant 7th"], 3)) == "B♭ C E G B♭"
    notes = arpeggio(c, CHORDS["diminished 7th"], 2)
    assert [n.midi for n in notes] == sorted(n.midi for n in notes)  # always rising
    assert notes[-1].midi - notes[0].midi == 12


def test_the_question_names_the_type_and_the_inversion(cfg):
    cfg.types, cfg.inversions = {"minor"}, {1}
    q = ArpeggioNames().generate(random.Random(1))
    assert q.answer == "minor · 1st inversion"
    assert q.choices == ["minor"] and q.octaves == ["1st inversion"]
    assert q.second_label == "Inversion" and q.joiner == " · "
    assert q.check("minor · 1st inversion") and not q.check("minor · root position")
    first = q.staff[0][0]
    assert first.letter in range(7) and len(q.staff) == 4 and all(len(col) == 1 for col in q.staff)
    # The lowest note of a minor chord in first inversion is its third: a minor third above the root.
    root_name = q.explanation.split()[0]
    assert q.explanation.startswith(f"{root_name} minor, 1st inversion")


def test_every_answer_the_exercise_can_give_is_one_of_its_buttons(cfg):
    cfg.types = set(settings.ARPEGGIO_TYPES)
    cfg.clefs = {
        "treble",
        "bass",
        "alto",
        "tenor",
    }
    rng = random.Random(5)
    for _ in range(400):
        q = ArpeggioNames().generate(rng)
        kind, inversion = q.answer.split(q.joiner)
        assert q.octaves is not None
        assert kind in q.choices and inversion in q.octaves
        assert len(set(q.choices)) == len(q.choices)
        assert [n.midi for n in (c[0] for c in q.staff)] == sorted(c[0].midi for c in q.staff)


def test_a_triad_is_never_in_third_inversion(cfg):
    cfg.types, cfg.inversions = {"major", "minor"}, {3}  # the 3rd inversion does not exist for these
    answers = {ArpeggioNames().generate(random.Random(i)).answer for i in range(60)}
    assert {a.split(" · ")[1] for a in answers} == {"root position"}  # so root position is used instead
    cfg.types = {"dominant 7th"}
    assert {ArpeggioNames().generate(random.Random(i)).answer for i in range(30)} == {"dominant 7th · 3rd inversion"}


def test_the_inversion_buttons_are_only_those_that_can_be_asked(cfg):
    cfg.types, cfg.inversions = {"major", "dominant 7th"}, {0, 2}
    q = ArpeggioNames().generate(random.Random(2))
    assert q.octaves == ["root position", "2nd inversion"]
    cfg.inversions = {
        0,
        1,
        2,
        3,
    }
    cfg.types = {"major"}
    assert ArpeggioNames().generate(random.Random(2)).octaves == list(INVERSION_NAMES[:3])  # a triad stops at the 2nd


def test_the_notes_sit_on_the_chosen_staff(cfg):
    cfg.types = set(settings.ARPEGGIO_TYPES)
    rng = random.Random(7)
    for clef in (
        "treble",
        "bass",
        "alto",
        "tenor",
    ):
        cfg.clefs = {clef}
        low, high = (n.diatonic for n in ARPEGGIO_WINDOWS[clef])
        for _ in range(150):
            q = ArpeggioNames().generate(rng)
            assert q.clef == clef
            assert low <= q.staff[0][0].diatonic and q.staff[-1][0].diatonic <= high
            assert all(abs(c[0].accidental) <= 1 for c in q.staff)  # no double sharps or flats


def test_key_signatures_are_only_drawn_when_switched_on(cfg):
    rng = random.Random(3)
    assert {ArpeggioNames().generate(rng).key for _ in range(60)} == {0}
    cfg.key_signature, cfg.keys = True, {-2, 3}
    assert {ArpeggioNames().generate(rng).key for _ in range(80)} == {-2, 3}


def test_many_types_are_laid_out_in_two_rows(cfg):
    cfg.types = set(settings.ARPEGGIO_TYPES)
    q = ArpeggioNames().generate(random.Random(4))
    assert q.grid and {row for row, _ in q.grid.values()} == {0, 1}
    cfg.types = {"major", "minor"}
    assert ArpeggioNames().generate(random.Random(4)).grid is None


def test_the_question_survives_being_stored_and_asked_again(cfg):
    from alto.exercises.base import Question

    q = ArpeggioNames().generate(random.Random(8))
    again = Question.from_dict(q.to_dict())
    assert again == q and again.item_key() == q.item_key()
    assert again.second_label == "Inversion" and again.joiner == " · "


def test_changing_the_settings_changes_the_settings_signature(cfg):
    before = ArpeggioNames().settings_signature()
    cfg.types = {"minor"}
    assert ArpeggioNames().settings_signature() != before


# -- the exercise screen and its settings panel ---------------------------------------------------------------------


class FakeStore:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def setValue(
        self,
        key,
        value,
    ):
        self.values[key] = value

    def value(
        self,
        key,
        default=None,
    ):
        return self.values.get(key, default)


@pytest.fixture
def view(
    app,
    cfg,
    monkeypatch,
):
    from alto.audio import sounds
    from alto.ui import settings_panel
    from alto.ui.exercise_view import ExerciseView
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    monkeypatch.setattr(settings_panel, "store", lambda: FakeStore())
    cfg.types, cfg.inversions, cfg.clefs = {"major", "minor"}, {0, 1}, {"treble"}
    # Nothing is played: a note scheduled for later would sound (and load the audio system) during some other test.
    monkeypatch.setattr(sounds, "play_notes", lambda *args, **kwargs: None)
    monkeypatch.setattr(sounds, "play_correct", lambda *args, **kwargs: None)
    v = ExerciseView(ArpeggioNames(), random.Random(1))
    yield v
    v.deleteLater()  # gone before the application, or Qt crashes when Python exits
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def press(
    view,
    text,
):
    next(b for b in view.buttons if b.text() == text).click()


def test_choosing_the_type_and_the_inversion_answers_the_question(view):
    q = view.question
    kind, inversion = q.answer.split(q.joiner)
    press(view, kind)
    assert not view.answered  # one part is not an answer yet
    press(view, inversion)
    assert view.answered and (view.correct, view.total) == (1, 1)


def test_a_wrong_pair_is_a_miss_and_the_buttons_reset(view):
    from PySide6.QtTest import QTest

    q = view.question
    kind, inversion = q.answer.split(q.joiner)
    wrong = next(t for t in q.choices if t != kind)
    press(view, inversion)
    press(view, wrong)
    assert view.missed and not view.answered and view.total == 1 and view.correct == 0
    QTest.qWait(900)
    assert view._pending == {} and not view._busy
    press(view, kind)
    press(view, inversion)  # trying again works, but it still counts as missed
    assert view.answered and view.correct == 0


def test_the_inversion_row_is_labelled_inversion(view):
    from PySide6.QtWidgets import QLabel

    labels = [view.octave_box.itemAt(i).widget() for i in range(view.octave_box.count())]
    assert [w.text() for w in labels if isinstance(w, QLabel)] == ["Inversion"]


def test_the_settings_panel_edits_and_saves_the_settings(
    view,
    cfg,
    monkeypatch,
):
    from alto.ui import settings_panel

    saved = FakeStore()
    monkeypatch.setattr(settings_panel, "store", lambda: saved)
    panel = view.settings_panel
    seen = []
    panel.changed.connect(lambda: seen.append(1))
    panel.types.boxes["augmented"].setChecked(True)
    assert "augmented" in cfg.types and seen
    assert "augmented" in saved.values["arpeggio/types"].split(",")
    panel.inversions.boxes[1].setChecked(False)
    assert cfg.inversions == {0}
    assert saved.values["arpeggio/inversions"] == "0"
    assert not panel.inversions.boxes[0].isEnabled()  # the last inversion cannot be unchecked
    panel._refresh_summaries()  # done when going back to the menu
    assert panel.types_row.value.text() == "3 of 9"
    assert panel.inversions_row.value.text() == "Root"


def test_the_saved_settings_are_read_back(
    cfg,
    monkeypatch,
):
    from alto.ui import settings_panel

    monkeypatch.setattr(
        settings_panel,
        "store",
        lambda: FakeStore(
            {
                "arpeggio/clefs": "alto,tenor",
                "arpeggio/types": "minor 7th,half-diminished 7th,nonsense",
                "arpeggio/inversions": "2,3",
                "arpeggio/keySignature": "true",
                "arpeggio/keys": "-1,2",
            },
        ),
    )
    settings_panel.load_arpeggio()
    assert cfg.clefs == {"alto", "tenor"} and cfg.types == {"minor 7th", "half-diminished 7th"}
    assert cfg.inversions == {2, 3} and cfg.key_signature and cfg.keys == {-1, 2}
