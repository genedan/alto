"""Shared test setup: one Qt application for the whole run, and settings and data kept away from the real ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from alto.learning import Learner
    from PySide6.QtCore import QCoreApplication

import atexit
import copy
import os
import shutil
import tempfile

# Alto saves its settings (QSettings) and its database under the XDG folders. Point them at a throwaway folder before
# anything reads them, so no test can read or change the real ones.
_HOME = tempfile.mkdtemp(prefix="alto-tests-")
os.environ["XDG_CONFIG_HOME"] = f"{_HOME}/config"
os.environ["XDG_DATA_HOME"] = f"{_HOME}/data"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
atexit.register(lambda: shutil.rmtree(_HOME, ignore_errors=True))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def app() -> QCoreApplication:
    """
    Provide the one Qt application for the whole run.

    Returns
    -------
    QCoreApplication
        The shared application, created on first use.
    """
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _close_every_window() -> None:
    """Close and delete every window a test left open, so none is torn down by Qt after the application is gone."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def _isolated_state() -> Iterator[None]:
    """
    Every test starts with the default exercise settings and no saved settings, and sound off.

    Yields
    ------
    None
        Control, while the test runs with fresh settings.
    """
    from alto import settings
    from alto.audio import sounds

    names = (
        "note_names",
        "keyboard",
        "construction",
        "arpeggio",
        "key_signatures",
    )
    before = {n: copy.deepcopy(getattr(settings, n).__dict__) for n in names}
    muted = sounds.enabled
    sounds.enabled = False
    yield
    _close_every_window()
    sounds.enabled = muted
    from alto.ui import keyboard_styles

    keyboard_styles._current = keyboard_styles.BY_KEY[keyboard_styles.DEFAULT]
    # noinspection PyProtectedMember
    keyboard_styles._custom.clear()
    # noinspection PyProtectedMember
    keyboard_styles._custom.update(keyboard_styles.DEFAULT_CUSTOM)
    for n in names:
        getattr(settings, n).__dict__.clear()
        getattr(settings, n).__dict__.update(before[n])
    try:
        from PySide6.QtCore import QSettings

        saved = QSettings("alto", "alto")
        saved.clear()
        saved.sync()
    except ImportError:  # pragma: no cover  (PySide6 is a requirement; this only guards a broken install)
        pass


@pytest.fixture
def practised_learner() -> Callable[..., Learner]:
    """
    Provide a function that makes a profile with answers spread over the last `days` days, some wrong first and some slow.

    Returns
    -------
    Callable[..., Learner]
        A function that builds a learner with a history of answers.
    """
    import random
    import time

    from alto.exercises import REGISTRY
    from alto.learning import Database, Learner

    def make(
        days: int = 120,
        *,
        name: str = "Ada",
        db: Database | None = None,
    ) -> Learner:
        """
        Build a learner with a history of answers spread over the past days.

        Parameters
        ----------
        days : int
            How many days back the history starts.
        name : str
            The profile's name.
        db : Database or None
            The database to use; a new in-memory one if None.

        Returns
        -------
        Learner
            The learner, with answers recorded every third day.
        """
        db = db or Database()
        learner = Learner(db, profile=db.add_profile(name))
        rng, now = random.Random(3), time.time()
        for day in range(days, -1, -3):
            for _ in range(rng.randint(2, 6)):
                ex = rng.choice(REGISTRY)()
                q = ex.generate(rng)
                at = now - day * 86400.0 - rng.randint(0, 3000)
                if rng.random() < 0.4:
                    learner.record(
                        ex,
                        question=q,
                        answer="wrong",
                        correct=False,
                        attempt_no=1,
                        seconds=rng.uniform(1, 9),
                        now=at,
                    )
                    learner.record(
                        ex,
                        question=q,
                        answer=q.answer,
                        correct=True,
                        attempt_no=2,
                        seconds=2.0,
                        now=at + 5,
                    )
                else:
                    learner.record(
                        ex,
                        question=q,
                        answer=q.answer,
                        correct=True,
                        attempt_no=1,
                        seconds=rng.uniform(0.5, 12),
                        now=at,
                    )
        return learner

    return make


@pytest.fixture(autouse=True)
def _close_databases(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """
    Close every database a test opened, so none is left for the garbage collector to report as unclosed.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.

    Yields
    ------
    None
        Control, while the test runs; every database opened meanwhile is closed afterwards.
    """
    from alto.learning import Database

    opened = []
    original = Database.__init__

    def tracking(
        self: Database,
        *args: str | Path,
        **kwargs: str | Path,
    ) -> None:
        """
        Open a database as usual, and remember it so it can be closed after the test.

        Parameters
        ----------
        self : Database
            The database being opened.
        args : str or Path
            The positional arguments of `Database`.
        kwargs : str or Path
            The keyword arguments of `Database`.
        """
        # noinspection PyTypeChecker
        original(self, *args, **kwargs)
        opened.append(self)

    monkeypatch.setattr(Database, "__init__", tracking)
    yield
    for db in opened:
        db.close()  # closing twice is harmless
