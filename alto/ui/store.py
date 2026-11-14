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

from collections.abc import Mapping

from PySide6.QtCore import (
    QByteArray,
    QSettings,
)


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
    >>> settings_ = store()
    >>> settings_.setValue("demo/count", "42")
    >>> int_value(settings_, key="demo/count", default=0)
    42
    >>> int_value(settings_, key="demo/missing", default=7)
    7
    >>> settings_.setValue("demo/count", "many")
    >>> int_value(settings_, key="demo/count", default=0)
    Traceback (most recent call last):
        ...
    ValueError: invalid literal for int() with base 10: 'many'
    >>> settings_.remove("demo")
    """
    value = settings.value(key, default)
    return int(value) if isinstance(value, (int, float, str)) else default


def text_value(
    settings: QSettings,
    *,
    key: str,
    default: str,
) -> str:
    """
    Read a saved setting as text.

    Parameters
    ----------
    settings : QSettings
        The settings to read.
    key : str
        The setting's name. Keyword-only.
    default : str
        What to return if nothing is saved. Keyword-only.

    Returns
    -------
    str
        The saved text, or `default` if there is none (or it is not text).

    Examples
    --------
    >>> settings_ = store()
    >>> settings_.setValue("demo/name", "viola")
    >>> text_value(settings_, key="demo/name", default="piano")
    'viola'
    >>> text_value(settings_, key="demo/missing", default="piano")
    'piano'
    >>> settings_.remove("demo")
    """
    value = settings.value(key, default)
    return value if isinstance(value, str) else default


def export_settings() -> dict[str, object]:
    """
    Return every saved preference, by key, for a backup.

    Returns
    -------
    dict of str to object
        Each key Alto has saved and its value. Qt byte arrays come back as `bytes` and lists as lists.

    Examples
    --------
    >>> settings_ = store()
    >>> settings_.setValue("demo/name", "Ada")
    >>> export_settings()["demo/name"]
    'Ada'
    >>> settings_.remove("demo")
    """
    saved = store()
    return {key: _plain(saved.value(key)) for key in sorted(saved.allKeys())}


def _plain(value: object) -> object:
    """
    Turn a value read from `QSettings` into plain Python.

    Parameters
    ----------
    value : object
        What `QSettings.value` returned.

    Returns
    -------
    object
        The value, with Qt byte arrays as `bytes` and the items of lists made plain too.

    Examples
    --------
    >>> from PySide6.QtCore import QByteArray
    >>> _plain(QByteArray(b"ab")), _plain(["a", 1]), _plain("text")
    (b'ab', ['a', 1], 'text')
    """
    if isinstance(value, QByteArray):
        return bytes(value.data())
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def import_settings(values: Mapping[str, object]) -> None:
    """
    Replace every saved preference with the ones from a backup, so the preferences are exactly as they were.

    Preferences saved now that the backup does not have are removed. The marker that stops old "mtheory" preferences being
    brought across again is kept, so an old installation's leftovers cannot leak back in.

    Parameters
    ----------
    values : mapping of str to object
        The preferences, by key, as `export_settings` returned them.

    Examples
    --------
    >>> import_settings({"demo/name": "Ada", "demo/count": 3})
    >>> store().value("demo/name"), int_value(store(), key="demo/count", default=0)
    ('Ada', 3)
    >>> store().remove("demo")
    >>> store().remove("")
    """
    saved = store()  # first, so the one-time migration of old preferences has happened before everything is cleared
    saved.clear()
    for key, value in values.items():
        saved.setValue(key, value)
    if not saved.contains("migratedFromMtheory"):
        saved.setValue("migratedFromMtheory", True)
    saved.sync()
