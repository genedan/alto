"""The statistics page: its numbers follow the answers recorded and the filters chosen."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import pytest
from alto.exercises import REGISTRY
from alto.learning import Database, Learner
from alto.ui import stats_dialog
from alto.ui.stats_dialog import StatsPage, format_duration, since_for
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtTest import QSignalSpy

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QApplication

DAY = 86400.0


def test_a_timeframe_starts_where_it_says() -> None:
    """
    Check that a timeframe starts where it says.
    """
    now = time.time()
    assert since_for(None, now=now) is None
    assert since_for(7, now=now) == pytest.approx(now - 7 * DAY)
    today = since_for("today", now=now)
    assert today is not None and now - DAY < today <= now


def test_durations_read_naturally() -> None:
    """
    Check that durations read naturally.
    """
    assert format_duration(5) == "5 s" and format_duration(29) == "29 s"
    assert format_duration(90) == "2 min" and format_duration(3000) == "50 min"
    assert format_duration(3600) == "1 h 00 min" and format_duration(3 * 3600 + 7 * 60) == "3 h 07 min"


def test_a_profile_with_no_answers_gets_an_invitation_not_numbers(app: QApplication) -> None:
    """
    Check that a profile with no answers gets an invitation not numbers.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    db = Database()
    page = StatsPage(Learner(db, profile=db.add_profile("Ben")))
    assert "No answers recorded for Ben" in page.note.text()
    assert page.tiles["questions"].value.text() == "0" and page.tiles["accuracy"].value.text() == "–"
    assert page.tiles["speed"].value.text() == "–" and page.tiles["tries"].value.text() == "–"
    assert page.table.rowCount() == 0
    assert page.grab().width() > 0


def test_the_numbers_come_from_the_active_profiles_answers(
    app: QApplication,
    practised_learner: Callable[..., Learner],
) -> None:
    """
    Check that the numbers come from the active profiles answers.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    learner = practised_learner()
    other = learner.db.add_profile("Someone else")
    other_learner = Learner(learner.db, profile=other)
    ex = REGISTRY[0]()
    other_learner.record(
        ex,
        question=ex.generate(random.Random(1)),
        answer="x",
        correct=False,
        attempt_no=1,
        seconds=3.0,
    )
    page = StatsPage(learner)
    page.timeframe.setCurrentIndex(page.timeframe.findText("All time"))
    total = int(page.tiles["questions"].value.text())
    assert total > 20 and "Showing Ada" in page.note.text()
    assert page.tiles["accuracy"].value.text().endswith("%")
    assert page.tiles["speed"].value.text().endswith(" s") and float(page.tiles["tries"].value.text()) >= 1.0
    assert page.tiles["time"].value.text().endswith(("s", "min"))
    first_question = page.table.item(0, 1)
    assert page.table.rowCount() > 0 and first_question is not None and first_question.text()
    assert page.table.horizontalHeader().height() > 0
    assert page.grab().width() > 0


def test_every_timeframe_and_exercise_can_be_chosen(
    app: QApplication,
    practised_learner: Callable[..., Learner],
) -> None:
    """
    Check that every timeframe and exercise can be chosen.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    page = StatsPage(practised_learner())
    counts = {}
    for i in range(page.timeframe.count()):
        page.timeframe.setCurrentIndex(i)
        counts[page.timeframe.currentText()] = int(page.tiles["questions"].value.text())
        assert page.volume.title.startswith("Questions answered per ")
    assert counts["Last 7 days"] <= counts["Last 30 days"] <= counts["Last 90 days"] <= counts["All time"]
    assert counts["Last year"] <= counts["All time"]
    page.timeframe.setCurrentIndex(page.timeframe.findText("All time"))
    for i in range(1, page.exercise.count()):
        page.exercise.setCurrentIndex(i)
        shown = int(page.tiles["questions"].value.text())
        assert shown <= counts["All time"]
    page.exercise.setCurrentIndex(0)
    assert int(page.tiles["questions"].value.text()) == counts["All time"]
    page.timeframe.setCurrentIndex(page.timeframe.findText("Today"))
    assert page.volume.title.endswith(("hour", "day"))


def test_back_is_offered_by_a_button_and_by_escape(
    app: QApplication,
    practised_learner: Callable[..., Learner],
) -> None:
    """
    Check that back is offered by a button and by escape.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    page = StatsPage(practised_learner(30))
    spy = QSignalSpy(page.back)
    page.back_button.click()
    escape = [s for s in page.findChildren(QShortcut) if s.key() == QKeySequence(Qt.Key.Key_Escape)]
    assert len(escape) == 1
    escape[0].activated.emit()  # what pressing Esc does (a headless window is never the active one)
    assert spy.count() == 2


def test_a_name_is_kept_for_exercises_the_page_no_longer_knows(
    app: QApplication,
    practised_learner: Callable[..., Learner],
) -> None:
    """
    Check that a name is kept for exercises the page no longer knows.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    page = StatsPage(practised_learner(30))
    assert page._names()[REGISTRY[0].__name__] == REGISTRY[0].name
    assert stats_dialog.Tile("caption").caption.text() == "caption"
