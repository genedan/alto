"""Setup for the doctests in alto/: a Qt application for examples that make widgets, and settings kept away from the real ones."""

import atexit
import os
import shutil
import tempfile

# Examples that save a setting must not touch the real ones, even if only `pytest alto` runs and tests/conftest.py is not loaded.
_HOME = tempfile.mkdtemp(prefix="alto-doctests-")
os.environ["XDG_CONFIG_HOME"] = f"{_HOME}/config"
os.environ["XDG_DATA_HOME"] = f"{_HOME}/data"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
atexit.register(shutil.rmtree, _HOME, ignore_errors=True)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _qt_application_for_doctests(
    request: pytest.FixtureRequest,
    *,
    doctest_namespace: dict,
) -> None:
    """
    Give every doctest a Qt application, available as `app`.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The running test, used to tell doctests from ordinary tests.
    doctest_namespace : dict
        The names every doctest can use without importing them. Keyword-only.

    Examples
    --------
    >>> app.applicationName() == app.applicationName()  # `app` is a QApplication in every doctest
    True
    """
    if type(request.node).__name__ != "DoctestItem":
        return
    from PySide6.QtWidgets import QApplication

    doctest_namespace["app"] = QApplication.instance() or QApplication([])


def pytest_sessionfinish(session: pytest.Session) -> None:
    """
    Delete every widget the run left behind, while Python and Qt are both still running.

    Examples make widgets they never close. Left to the interpreter's exit, PySide destroys them in an order that aborts the
    process after every test has passed, which fails the pre-push hook.

    Parameters
    ----------
    session : pytest.Session
        The finished run. Not used.

    Examples
    --------
    >>> callable(pytest_sessionfinish)
    True
    """
    import gc

    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
