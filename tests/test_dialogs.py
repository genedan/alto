"""The profile dialog and the question preview popup."""
import pytest
from alto import settings
from alto.exercises.base import Question
from alto.learning import Database
from alto.theory.pitch import Note
from alto.ui import profile_dialog
from alto.ui.profile_dialog import ProfileDialog, remember_profile, startup_profile
from alto.ui.question_preview import QuestionPreview
from alto.ui.store import store
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton

# -- choosing who is practising -------------------------------------------------------------------------------------


def test_the_first_time_it_asks_for_a_name_and_creates_the_profile(app):
    dialog = ProfileDialog(Database())
    assert dialog.windowTitle() == "Welcome" and not dialog.list.isVisibleTo(dialog)
    assert dialog.create_button.text() == "Create profile"
    dialog.create_button.click()  # nothing typed yet
    assert dialog.error.text() and dialog.chosen is None
    dialog.name.setText("Ada Lovelace")
    dialog.name.returnPressed.emit()
    assert dialog.chosen is not None and dialog.chosen.name == "Ada Lovelace" and dialog.result() == QDialog.DialogCode.Accepted


def test_a_name_that_is_taken_is_refused_with_a_reason(app):
    db = Database()
    db.add_profile("Ada")
    dialog = ProfileDialog(db)
    dialog.name.setText("ada")
    dialog.create_button.click()
    assert "already a profile" in dialog.error.text() and dialog.chosen is None


def test_with_profiles_it_lists_them_and_selects_the_current_one(app):
    db = Database()
    ada, ben = db.add_profile("Ada"), db.add_profile("Ben")
    dialog = ProfileDialog(db, current=ben)
    assert dialog.windowTitle() == "Profile" and dialog.create_button.text() == "Add"
    assert [dialog.list.item(i).text() for i in range(dialog.list.count())] == ["Ada", "Ben"]
    assert dialog.list.currentItem().data(Qt.ItemDataRole.UserRole) == ben
    assert ProfileDialog(db).list.currentRow() == 0  # nobody current: the first one is selected
    use = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Use selected profile")
    use.click()
    assert dialog.chosen == ben and ada is not None


def test_double_clicking_a_profile_uses_it_and_a_missing_selection_does_nothing(app):
    db = Database()
    ada = db.add_profile("Ada")
    dialog = ProfileDialog(db, current=ada)
    dialog.list.itemDoubleClicked.emit(dialog.list.item(0))
    assert dialog.chosen == ada
    other = ProfileDialog(db, current=ada)
    other.list.setCurrentRow(-1)
    other._use_selected()
    assert other.chosen is None
    cancel = next(b for b in other.findChildren(QPushButton) if b.text() == "Cancel")
    cancel.click()
    assert other.result() == QDialog.DialogCode.Rejected


def test_the_last_profile_is_remembered(app):
    db = Database()
    ada = db.add_profile("Ada")
    remember_profile(ada)
    assert int(store().value("profile/last")) == ada.id


class Decides:
    """Stands in for the dialog, so no window has to be answered."""

    def __init__(self, outcome):
        self.outcome, self.chosen = outcome, None

    def __call__(self, db):
        self.db = db
        return self

    def exec(self):
        if self.outcome is not None:
            self.chosen = self.db.add_profile(self.outcome)
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected


def test_it_opens_with_the_profile_used_last_time(app, monkeypatch):
    db = Database()
    db.add_profile("Ada")
    ben = db.add_profile("Ben")
    remember_profile(ben)
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides("never asked"))
    assert startup_profile(db) == ben


def test_a_single_profile_is_used_without_asking_but_several_are_asked_about(app, monkeypatch):
    db = Database()
    ada = db.add_profile("Ada")
    asked = Decides("Cleo")
    monkeypatch.setattr(profile_dialog, "ProfileDialog", asked)
    assert startup_profile(db) == ada  # only one, and nothing remembered
    db.add_profile("Ben")
    chosen = startup_profile(db)
    assert chosen is not None and chosen.name == "Cleo"  # two to choose from: the person is asked
    assert int(store().value("profile/last")) == chosen.id  # and the choice is remembered


def test_with_no_profile_a_new_one_is_made_or_the_start_is_cancelled(app, monkeypatch):
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides("Ada"))
    first = startup_profile(Database())
    assert first is not None and first.name == "Ada"
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides(None))
    assert startup_profile(Database()) is None


# -- the question preview popup -------------------------------------------------------------------------------------


def texts(dialog):
    return " ".join(label.text() for label in dialog.findChildren(QLabel))


def test_a_staff_question_shows_its_notes_answer_choices_and_explanation(app, monkeypatch):
    played = []
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    q = Question("Which?", ["major", "minor"], "minor", [[Note(4, 0)], [Note(4, 2)]], explanation="C minor",
                 octaves=["root position", "1st inversion"], second_label="Inversion")
    dialog = QuestionPreview("Chord", q, ["<b>You answered:</b> major"])
    shown = texts(dialog)
    assert "Which?" in shown and "<b>Answer:</b> minor" in shown and "Choices: major  ·  minor" in shown
    assert "Inversion: root position  ·  1st inversion" in shown and "You answered" in shown and "C minor" in shown
    play = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Play")
    play.click()
    assert played == [q.staff]
    close = next(b for b in dialog.findChildren(QPushButton) if b.text().replace("&", "") == "Close")
    close.click()
    assert dialog.result() == QDialog.DialogCode.Accepted


@pytest.mark.parametrize("key_staff", [False, True])
def test_a_keyboard_question_shows_the_key(app, key_staff, monkeypatch):
    played = []
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    q = Question("", ["C", "D"], "C", keyboard=Note(4, 0), key=2, key_staff=key_staff, keyboard_range=(48, 72))
    dialog = QuestionPreview("Keyboard", q)
    assert dialog.grab().width() > 0
    next(b for b in dialog.findChildren(QPushButton) if b.text() == "Play").click()
    assert played == [[[Note(4, 0)]]]


def test_a_note_construction_question_shows_the_note_that_was_asked_for(app, monkeypatch):
    played = []
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    settings.note_names.naming = "solfege"
    q = Question("Place Sol", [], "", clef="bass", construct=Note(3, 4))
    dialog = QuestionPreview("Construction", q)
    assert "<b>Answer:</b> Sol3" in texts(dialog)
    next(b for b in dialog.findChildren(QPushButton) if b.text() == "Play").click()
    assert played == [[[Note(3, 4)]]]


def test_a_question_with_nothing_to_play_has_no_play_button(app):
    dialog = QuestionPreview("Key signatures", Question("How many?", ["one", "two"], "two"))
    assert not [b for b in dialog.findChildren(QPushButton) if b.text() == "Play"]
