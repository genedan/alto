"""Help texts, stored questions, and the small helpers around the exercises."""

import random

import pytest
from alto import settings
from alto.exercises import REGISTRY
from alto.exercises.base import Exercise, Question
from alto.exercises.library import ARPEGGIO_WINDOWS, ArpeggioNames, KeyboardNotes, NoteConstruction
from alto.settings import diatonic_name
from alto.theory.pitch import Note
from alto.theory.scales import all_tonics


def test_every_exercise_explains_itself():
    for cls in REGISTRY:
        text = cls().instructions()
        assert isinstance(text, str) and len(text) > 40, cls.name


def test_an_exercise_without_its_own_help_uses_its_description():
    class Plain(Exercise):
        name, description = "Plain", "Just a description."

        def generate(self, rng):
            return Question("?", choices=["a"], answer="a")

    assert Plain().instructions() == "Just a description."
    assert Plain().settings_signature() == ""


def test_the_keyboard_help_follows_the_settings():
    cfg = settings.keyboard
    cfg.require_octave, cfg.key_signature = False, False
    plain = KeyboardNotes().instructions()
    assert "C♯ and D♭" in plain and "octave" not in plain.lower().replace("octaves", "")
    cfg.require_octave, cfg.key_signature = True, True
    full = KeyboardNotes().instructions()
    assert "middle C" in full and "key signature is shown" in full and "C♯ and D♭" not in full


def test_the_note_construction_help_follows_the_settings():
    cfg = settings.construction
    cfg.key_signature, cfg.accidentals = False, False
    plain = NoteConstruction().instructions()
    assert "key signature" not in plain and "right" not in plain
    cfg.key_signature, cfg.accidentals = True, True
    full = NoteConstruction().instructions()
    assert "key signature is drawn" in full and "right click" in full


def test_a_stored_question_comes_back_exactly():
    q = Question(
        "Which?",
        choices=["a", "b", "c"],
        answer="b",
        staff=[[Note(4, letter=0), Note(4, letter=2)]],
        clef="bass",
        key=-2,
        value="half",
        grid={"a": (0, 0), "b": (1, 0), "c": (1, 1)},
        keyboard=Note(3, letter=4, accidental=1),
        keyboard_range=(48, 72),
        octaves=["3", "4"],
        construct=Note(2, letter=1),
        accidentals=True,
        accept=("B", "b"),
    )
    again = Question.from_dict(q.to_dict())
    assert again == q
    assert again.grid == {"a": (0, 0), "b": (1, 0), "c": (1, 1)} and again.keyboard_range == (48, 72)
    assert again.accept == ("B", "b") and again.check("B") and again.check("b") and not again.check("c")


def test_an_arpeggio_that_fits_nowhere_is_reported(monkeypatch):
    tiny = {
        clef: (Note(4, letter=0), Note(4, letter=1)) for clef in ARPEGGIO_WINDOWS
    }  # two staff steps: too small for any arpeggio
    monkeypatch.setattr("alto.exercises.library.ARPEGGIO_WINDOWS", tiny)
    with pytest.raises(RuntimeError, match="no arpeggio fits"):
        ArpeggioNames().generate(random.Random(1))


def test_diatonic_names_and_tonics():
    assert diatonic_name(Note(4, letter=0).diatonic) == "C4" and diatonic_name(Note(2, letter=6).diatonic) == "B2"
    tonics = all_tonics()
    assert len(tonics) == 21 and Note(4, letter=3, accidental=1) in tonics and Note(4, letter=0, accidental=2) not in tonics
    assert len(all_tonics(0)) == 7 and len(all_tonics(2)) == 35


def test_a_stored_question_is_only_asked_again_under_the_settings_it_was_made_for():
    from alto.exercises.library import NoteNames

    for exercise, change in (
        (NoteNames(), lambda: setattr(settings.note_names, "naming", "solfege")),
        (KeyboardNotes(), lambda: setattr(settings.keyboard, "black_keys", False)),
        (NoteConstruction(), lambda: setattr(settings.construction, "accidentals", True)),
    ):
        before = exercise.settings_signature()
        change()
        assert exercise.settings_signature() != before, type(exercise).__name__
