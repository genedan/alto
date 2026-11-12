from __future__ import annotations

from PySide6.QtCore import QSettings


def store() -> QSettings:
    """The app's saved settings. The first time it is opened under the name "alto" it brings across anything saved
    under the old name ("mtheory"), so a rename does not reset anyone's preferences."""
    s = QSettings("alto", "alto")
    if not s.contains("migratedFromMtheory"):
        old = QSettings("mtheory", "mtheory")
        for key in old.allKeys():
            if not s.contains(key):
                s.setValue(key, old.value(key))
        s.setValue("migratedFromMtheory", True)
    return s


def int_value(settings: QSettings, key: str, default: int) -> int:
    """An integer setting. QSettings hands back whatever was saved (a number or its text); text that is not a number
    raises ValueError."""
    value = settings.value(key, default)
    return int(value) if isinstance(value, (int, float, str)) else default
