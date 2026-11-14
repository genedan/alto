"""Exporting and importing a backup from the menu: the questions asked, what is refused, and that nothing ends up different."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
)

from alto import settings
from alto.audio import sounds
from alto.learning import (
    Database,
    Learner,
)
from alto.learning.backup import (
    read_backup,
    write_backup,
)
from alto.ui import (
    backup_flow,
)
from alto.ui import (
    main_window as mw,
)
from alto.ui.instrument_picker import save_instrument
from alto.ui.main_window import MainWindow
from alto.ui.profile_dialog import remember_profile
from alto.ui.settings_panel import save_note_names
from alto.ui.store import (
    export_settings,
    store,
)
from alto.ui.theme import save_theme

if TYPE_CHECKING:
    from collections.abc import Callable

YES, NO = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No


class Dialogs:
    """
    Stands in for the file dialogs and message boxes, answering as the test says and recording what was shown.

    Attributes
    ----------
    save_to : str
        The file the save dialog returns; empty means the user cancelled.
    open_from : str
        The file the open dialog returns; empty means the user cancelled.
    answer : QMessageBox.StandardButton
        What the user answers when asked whether to replace everything.
    shown : list of tuple
        Each message box that appeared, as (kind, text).
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Put the stand-ins in place for the length of the test.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Replaces the dialogs.
        """
        self.save_to, self.open_from, self.answer = "", "", NO
        self.shown: list[tuple[str, str]] = []
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (self.save_to, ""))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (self.open_from, ""))
        monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: self.shown.append(("warning", text)))
        monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text: self.shown.append(("information", text)))
        monkeypatch.setattr(QMessageBox, "question", lambda parent, title, text, buttons, default: self._ask(text))

    def _ask(self, text: str) -> QMessageBox.StandardButton:
        """
        Record a question and give the answer the test chose.

        Parameters
        ----------
        text : str
            The question.

        Returns
        -------
        QMessageBox.StandardButton
            The chosen answer.
        """
        self.shown.append(("question", text))
        return self.answer


def rows(db: Database) -> dict[str, list[tuple]]:
    """
    Read every row of every table, in a fixed order.

    Parameters
    ----------
    db : Database
        The database.

    Returns
    -------
    dict of str to list of tuple
        The rows of each table.
    """
    return {
        t: [tuple(r) for r in db.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3")] for t in ("profiles", "attempts", "items")
    }


@pytest.fixture
def dialogs(monkeypatch: pytest.MonkeyPatch) -> Dialogs:
    """
    Provide stand-ins for the dialogs.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Replaces the dialogs.

    Returns
    -------
    Dialogs
        The stand-ins, to be told what to answer.
    """
    return Dialogs(monkeypatch)


def test_the_suggested_name_carries_the_date_and_the_extension() -> None:
    """
    Check that the suggested file name has the date and the backup extension, and counts read naturally.
    """
    assert backup_flow.default_name(now=0.0).startswith("alto-backup-19") and backup_flow.default_name().endswith(".altobackup")
    assert backup_flow.counted(1, noun="answer") == "1 answer" and backup_flow.counted(0, noun="profile") == "0 profiles"


def test_exporting_writes_one_file_with_the_extension_and_says_what_it_holds(
    app: QApplication,
    practised_learner: Callable[..., Learner],
    dialogs: Dialogs,
    tmp_path: Path,
) -> None:
    """
    Check that exporting writes a readable backup even if the name lacks the extension, and reports what went in it.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    dialogs : Dialogs
        Stands in for the dialogs.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    learner = practised_learner(30)
    dialogs.save_to = str(tmp_path / "mine")
    written = backup_flow.export_backup(QApplication.activeWindow() or MainWindow(), db=learner.db)
    assert written is not None
    # noinspection PyUnresolvedReferences
    assert written == tmp_path / "mine.altobackup" and written.exists()
    # noinspection PyTypeChecker
    assert read_backup(written).info.attempts == learner.db.count_attempts(learner.profile.id)
    assert dialogs.shown[-1][0] == "information" and str(written) in dialogs.shown[-1][1]


def test_cancelling_the_export_or_failing_to_write_changes_nothing_and_says_so(
    app: QApplication,
    dialogs: Dialogs,
    tmp_path: Path,
) -> None:
    """
    Check that cancelling writes nothing and shows nothing, and that a file that cannot be written is explained.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    dialogs : Dialogs
        Stands in for the dialogs.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    db = Database()
    db.add_profile("Ada")
    window = MainWindow()
    assert backup_flow.export_backup(window, db=db) is None and dialogs.shown == []
    dialogs.save_to = str(tmp_path / "no such folder" / "x.altobackup")
    assert backup_flow.export_backup(window, db=db) is None
    assert dialogs.shown[-1][0] == "warning" and "could not be written" in dialogs.shown[-1][1]


def test_an_import_that_is_refused_or_declined_leaves_everything_as_it_was(
    app: QApplication,
    dialogs: Dialogs,
    tmp_path: Path,
) -> None:
    """
    Check that cancelling, a file that is not a backup, a backup with nobody in it and answering No each change nothing.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    dialogs : Dialogs
        Stands in for the dialogs.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    db = Database()
    db.add_profile("Ada")
    store().setValue("ui/theme", "light")
    before, saved = rows(db), export_settings()
    window = MainWindow()
    assert backup_flow.import_backup(window, db=db) is False  # cancelled at the file dialog
    junk = tmp_path / "junk.altobackup"
    junk.write_bytes(b"not a backup")
    dialogs.open_from = str(junk)
    assert backup_flow.import_backup(window, db=db) is False and dialogs.shown[-1][0] == "warning"
    nobody = tmp_path / "nobody.altobackup"
    write_backup(Database(), settings={"ui/theme": "dark"}, path=nobody)
    dialogs.open_from = str(nobody)
    assert backup_flow.import_backup(window, db=db) is False and "no profiles" in dialogs.shown[-1][1]
    other = Database()
    other.add_profile("Ben")
    good = tmp_path / "good.altobackup"
    write_backup(other, settings={"ui/theme": "dark"}, path=good)
    dialogs.open_from, dialogs.answer = str(good), NO
    assert backup_flow.import_backup(window, db=db) is False and dialogs.shown[-1][0] == "question"
    assert rows(db) == before and export_settings() == saved


def test_the_question_before_replacing_says_what_the_backup_holds(
    app: QApplication,
    dialogs: Dialogs,
    tmp_path: Path,
) -> None:
    """
    Check that the question names the backup's version, date and contents and warns that everything is replaced.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    dialogs : Dialogs
        Stands in for the dialogs.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    other = Database()
    other.add_profile("Ben")
    write_backup(other, settings={}, path=tmp_path / "b.altobackup")
    dialogs.open_from = str(tmp_path / "b.altobackup")
    backup_flow.import_backup(MainWindow(), db=Database(tmp_path / "here.db"))
    kind, text = dialogs.shown[-1]
    assert kind == "question" and "1 profile and 0 answers" in text and "replaced" in text and "undone" in text


def test_an_import_saves_a_copy_of_what_it_replaces_so_it_can_be_undone(
    app: QApplication,
    practised_learner: Callable[..., Learner],
    dialogs: Dialogs,
    tmp_path: Path,
) -> None:
    """
    Check that importing into a database file first saves a backup beside it, and that restoring that backup undoes the import.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    dialogs : Dialogs
        Stands in for the dialogs.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    here = practised_learner(30, db=Database(tmp_path / "data" / "alto.db")).db
    original = rows(here)
    other = Database()
    other.add_profile("Ben")
    write_backup(other, settings={}, path=tmp_path / "ben.altobackup")
    dialogs.open_from, dialogs.answer = str(tmp_path / "ben.altobackup"), YES
    assert backup_flow.import_backup(MainWindow(), db=here) is True
    assert [p.name for p in here.profiles()] == ["Ben"]
    copies = list((tmp_path / "data").glob("alto-before-import-*.altobackup"))
    assert len(copies) == 1 and str(copies[0]) in dialogs.shown[-1][1]
    here.restore(read_backup(copies[0]).database)  # the undo
    assert rows(here) == original


def test_importing_a_backup_into_a_clean_install_leaves_it_as_if_nothing_had_changed(
    app: QApplication,
    practised_learner: Callable[..., Learner],
    dialogs: Dialogs,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Check the whole promise: the profiles, answers, saved preferences, profile in use and loaded settings all match.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    dialogs : Dialogs
        Stands in for the dialogs.
    monkeypatch : pytest.MonkeyPatch
        Replaces the theme change, which would alter the whole test run's palette.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    applied: list[str] = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw, "apply_theme", applied.append)
    learner = practised_learner(90, db=Database(tmp_path / "old" / "alto.db"))
    practised_learner(40, name="Ben", db=learner.db)
    remember_profile(learner.profile)
    settings.note_names.clefs = {"alto"}
    save_note_names()
    sounds.instrument = "flute"
    save_instrument()
    save_theme("dark")
    dialogs.save_to = str(tmp_path / "backup.altobackup")
    MainWindow(learner).export_backup()
    original_rows, original_settings = rows(learner.db), export_settings()

    store().clear()  # a clean install on a new computer: an empty database but for the profile it asked for, and default settings
    settings.note_names.__dict__.update(type(settings.note_names)().__dict__)
    sounds.instrument = "piano"
    clean = Database(tmp_path / "new" / "alto.db")
    fresh_start = Learner(clean, profile=clean.add_profile("Someone"))
    window = MainWindow(fresh_start)
    assert export_settings() != original_settings and rows(clean) != original_rows

    dialogs.open_from, dialogs.answer = dialogs.save_to, YES
    window.import_backup()

    assert rows(clean) == original_rows
    assert export_settings() == original_settings
    reopened = getattr(QApplication.instance(), "main_window", None)
    assert isinstance(reopened, MainWindow)
    assert reopened is not window
    # noinspection PyUnresolvedReferences
    now_learner = reopened.learner
    assert now_learner is not None
    assert now_learner.profile.name == "Ada" and now_learner.profile.id == learner.profile.id
    assert settings.note_names.active_clefs() == ["alto"] and sounds.instrument == "flute"
    assert applied == ["dark"]
    assert now_learner.db.count_attempts(learner.profile.id) == learner.db.count_attempts(learner.profile.id)


def test_the_backup_actions_are_offered_only_when_there_is_a_profile(app: QApplication) -> None:
    """
    Check that export and import appear in the menu with a profile and are hidden without one.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    bare = MainWindow()
    assert not bare.export_action.isVisible() and not bare.import_action.isVisible()
    bare.export_backup()
    bare.import_backup()  # nothing to back up or to restore into, so nothing happens
    db = Database()
    with_profile = MainWindow(Learner(db, profile=db.add_profile("Ada")))
    assert with_profile.export_action.text().startswith("Export") and with_profile.import_action.text().startswith("Import")
    assert with_profile.export_action.isVisible() and with_profile.import_action.isVisible()
