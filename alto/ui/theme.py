"""The colour theme: follow the system, or force light or dark."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from .store import store
from .style import app_style

THEMES = (("system", "System"), ("light", "Light"), ("dark", "Dark"))
_SCHEMES = {"system": Qt.ColorScheme.Unknown, "light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}


def saved_theme() -> str:
    key = str(store().value("ui/theme", "system"))
    return key if key in _SCHEMES else "system"


def save_theme(key: str) -> None:
    store().setValue("ui/theme", key)


def apply_theme(key: str) -> None:
    """Switch the application's colour scheme and rebuild the stylesheet from the new palette."""
    QGuiApplication.styleHints().setColorScheme(_SCHEMES.get(key, Qt.ColorScheme.Unknown))
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    app.setStyleSheet(app_style(app.palette()))
