"""
The colour theme: follow the system, or force light or dark.

Examples
--------
>>> [key for key, label in THEMES]
['system', 'light', 'dark']
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from .store import store
from .style import app_style

THEMES = (("system", "System"), ("light", "Light"), ("dark", "Dark"))
_SCHEMES = {"system": Qt.ColorScheme.Unknown, "light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}


def saved_theme() -> str:
    """
    Return the theme the user chose.

    Returns
    -------
    str
        "system", "light" or "dark"; "system" if nothing valid is saved.

    Examples
    --------
    >>> save_theme("dark")
    >>> saved_theme()
    'dark'
    >>> save_theme("system")
    """
    key = str(store().value("ui/theme", "system"))
    return key if key in _SCHEMES else "system"


def save_theme(key: str) -> None:
    """
    Remember the theme the user chose.

    Parameters
    ----------
    key : str
        "system", "light" or "dark".

    Examples
    --------
    >>> save_theme("light")
    >>> saved_theme()
    'light'
    >>> save_theme("system")
    """
    store().setValue("ui/theme", key)


def apply_theme(key: str) -> None:
    """
    Switch the application's colour scheme and rebuild the stylesheet from the new palette.

    Parameters
    ----------
    key : str
        "system" to follow the desktop, "light" or "dark". Anything else follows the system.

    Examples
    --------
    >>> apply_theme("system")
    >>> app.styleSheet() != ""
    True
    """
    QGuiApplication.styleHints().setColorScheme(_SCHEMES.get(key, Qt.ColorScheme.Unknown))
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    app.setStyleSheet(app_style(app.palette()))
