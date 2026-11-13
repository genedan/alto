"""The profile dialog and the question preview popup."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QWidget

# -- choosing who is practising -------------------------------------------------------------------------------------


def test_the_first_time_it_asks_for_a_name_and_creates_the_profile(app: QApplication) -> None:
    """
    Check that the first time it asks for a name and creates the profile.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    dialog = ProfileDialog(Database())
    assert dialog.windowTitle() == "Welcome" and not dialog.list.isVisibleTo(dialog)
    assert dialog.create_button.text() == "Create profile"
    dialog.create_button.click()  # nothing typed yet
    assert dialog.error.text() and dialog.chosen is None
    dialog.name.setText("Ada Lovelace")
    dialog.name.returnPressed.emit()
    # noinspection PyUnresolvedReferences
    assert dialog.chosen is not None and dialog.chosen.name == "Ada Lovelace" and dialog.result() == QDialog.DialogCode.Accepted


def test_a_name_that_is_taken_is_refused_with_a_reason(app: QApplication) -> None:
    """
    Check that a name that is taken is refused with a reason.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    db = Database()
    db.add_profile("Ada")
    dialog = ProfileDialog(db)
    dialog.name.setText("ada")
    dialog.create_button.click()
    assert "already a profile" in dialog.error.text() and dialog.chosen is None


def test_with_profiles_it_lists_them_and_selects_the_current_one(app: QApplication) -> None:
    """
    Check that with profiles it lists them and selects the current one.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
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


def test_double_clicking_a_profile_uses_it_and_a_missing_selection_does_nothing(app: QApplication) -> None:
    """
    Check that double clicking a profile uses it and a missing selection does nothing.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
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


def test_the_last_profile_is_remembered(app: QApplication) -> None:
    """
    Check that the last profile is remembered.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    db = Database()
    ada = db.add_profile("Ada")
    remember_profile(ada)
    assert int(store().value("profile/last")) == ada.id


class Decides:
    """Stands in for the dialog, so no window has to be answered."""

    def __init__(self, outcome: str | None) -> None:
        """
        Build the stand-in.

        Parameters
        ----------
        outcome : str or None
            The name of the profile to add, or None to cancel.
        """
        self.outcome, self.chosen = outcome, None

    def __call__(self, db: Database) -> Decides:
        """
        Take the place of the dialog class: remember the database and return itself.

        Parameters
        ----------
        db : Database
            The database.

        Returns
        -------
        Decides
            This object, standing in for the dialog.
        """
        self.db = db
        return self

    def exec(self) -> QDialog.DialogCode:
        """
        Answer the dialog without showing it.

        Returns
        -------
        QDialog.DialogCode
            Accepted after adding the profile, or Rejected if there is none.
        """
        if self.outcome is not None:
            self.chosen = self.db.add_profile(self.outcome)
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected


def test_it_opens_with_the_profile_used_last_time(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that it opens with the profile used last time.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    db = Database()
    db.add_profile("Ada")
    ben = db.add_profile("Ben")
    remember_profile(ben)
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides("never asked"))
    assert startup_profile(db) == ben


def test_a_single_profile_is_used_without_asking_but_several_are_asked_about(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a single profile is used without asking but several are asked about.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    db = Database()
    ada = db.add_profile("Ada")
    asked = Decides("Cleo")
    monkeypatch.setattr(profile_dialog, "ProfileDialog", asked)
    assert startup_profile(db) == ada  # only one, and nothing remembered
    db.add_profile("Ben")
    chosen = startup_profile(db)
    assert chosen is not None and chosen.name == "Cleo"  # two to choose from: the person is asked
    assert int(store().value("profile/last")) == chosen.id  # and the choice is remembered


def test_with_no_profile_a_new_one_is_made_or_the_start_is_cancelled(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that with no profile a new one is made or the start is cancelled.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides("Ada"))
    first = startup_profile(Database())
    assert first is not None and first.name == "Ada"
    monkeypatch.setattr(profile_dialog, "ProfileDialog", Decides(None))
    assert startup_profile(Database()) is None


# -- the question preview popup -------------------------------------------------------------------------------------


def texts(dialog: QWidget) -> str:
    """
    Join the text of every label in a dialog.

    Parameters
    ----------
    dialog : QWidget
        The dialog.

    Returns
    -------
    str
        All the label texts separated by spaces.
    """
    return " ".join(label.text() for label in dialog.findChildren(QLabel))


def test_a_staff_question_shows_its_notes_answer_choices_and_explanation(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a staff question shows its notes answer choices and explanation.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    played = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    q = Question(
        "Which?",
        choices=["major", "minor"],
        answer="minor",
        staff=[[Note(4, letter=0)], [Note(4, letter=2)]],
        explanation="C minor",
        octaves=["root position", "1st inversion"],
        second_label="Inversion",
    )
    dialog = QuestionPreview("Chord", question=q, details=["<b>You answered:</b> major"])
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
def test_a_keyboard_question_shows_the_key(
    app: QApplication,
    key_staff: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a keyboard question shows the key.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    key_staff : bool
        Whether the question is drawn on a key staff.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    played = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    q = Question(
        "",
        choices=["C", "D"],
        answer="C",
        keyboard=Note(4, letter=0),
        key=2,
        key_staff=key_staff,
        keyboard_range=(48, 72),
    )
    dialog = QuestionPreview("Keyboard", question=q)
    assert dialog.grab().width() > 0
    next(b for b in dialog.findChildren(QPushButton) if b.text() == "Play").click()
    assert played == [[[Note(4, letter=0)]]]


def test_a_note_construction_question_shows_the_note_that_was_asked_for(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a note construction question shows the note that was asked for.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    played = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr("alto.ui.question_preview.sounds.play_notes", lambda notes: played.append(notes))
    settings.note_names.naming = "solfege"
    q = Question(
        "Place Sol",
        choices=[],
        answer="",
        clef="bass",
        construct=Note(3, letter=4),
    )
    dialog = QuestionPreview("Construction", question=q)
    assert "<b>Answer:</b> Sol3" in texts(dialog)
    next(b for b in dialog.findChildren(QPushButton) if b.text() == "Play").click()
    assert played == [[[Note(3, letter=4)]]]


def test_a_question_with_nothing_to_play_has_no_play_button(app: QApplication) -> None:
    """
    Check that a question with nothing to play has no play button.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    dialog = QuestionPreview("Key signatures", question=Question("How many?", choices=["one", "two"], answer="two"))
    assert not [b for b in dialog.findChildren(QPushButton) if b.text() == "Play"]


def test_the_staff_in_the_preview_is_capped_like_the_one_in_the_exercise(app: QApplication) -> None:
    """
    Check that the staff in the preview is capped like the one in the exercise.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    from alto.ui.staff import StaffWidget

    dialog = QuestionPreview(
        "Note",
        question=Question(
            "",
            choices=["C"],
            answer="C",
            staff=[[Note(4, letter=0)]],
        ),
    )
    staff = dialog.findChildren(StaffWidget)[0]
    assert staff.max_step is not None and staff.maximumWidth() < 1000
