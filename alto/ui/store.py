"""
The application's saved settings (a thin layer over `QSettings`).

Examples
--------
>>> settings = store()
>>> settings.setValue("demo/count", 3)
>>> int_value(settings, key="demo/count", default=0)
3
>>> settings.remove("demo")
"""

from __future__ import annotations

from PySide6.QtCore import QSettings


def store() -> QSettings:
    """
    Return the app's saved settings.

    The first time it is opened under the name "alto" it brings across anything saved under the old name ("mtheory"), so a
    rename does not reset anyone's preferences.

    Returns
    -------
    QSettings
        The settings, kept in the user's configuration folder.

    Examples
    --------
    >>> settings = store()
    >>> settings.setValue("demo/name", "Ada")
    >>> str(store().value("demo/name"))
    'Ada'
    >>> settings.remove("demo")
    """
    s = QSettings("alto", "alto")
    if not s.contains("migratedFromMtheory"):
        old = QSettings("mtheory", "mtheory")
        for key in old.allKeys():
            if not s.contains(key):
                s.setValue(key, old.value(key))
        s.setValue("migratedFromMtheory", True)
    return s


def int_value(
    settings: QSettings,
    *,
    key: str,
    default: int,
) -> int:
    """
    Read an integer setting.

    `QSettings` hands back whatever was saved, which may be a number or its text.

    Parameters
    ----------
    settings : QSettings
        The settings to read.
    key : str
        The setting's name. Keyword-only.
    default : int
        What to return if nothing is saved. Keyword-only.

    Returns
    -------
    int
        The saved value, or `default` if there is none (or it is not a number, text or similar).

    Raises
    ------
    ValueError
        If the saved text is not a whole number.

    Examples
    --------
    >>> settings = store()
    >>> settings.setValue("demo/count", "42")
    >>> int_value(settings, key="demo/count", default=0)
    42
    >>> int_value(settings, key="demo/missing", default=7)
    7
    >>> settings.setValue("demo/count", "many")
    >>> int_value(settings, key="demo/count", default=0)
    Traceback (most recent call last):
        ...
    ValueError: invalid literal for int() with base 10: 'many'
    >>> settings.remove("demo")
    """
    value = settings.value(key, default)
    return int(value) if isinstance(value, (int, float, str)) else default
