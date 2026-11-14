"""
Exporting a backup and importing one: the file dialogs, the questions asked, and the safety copy made before anything is replaced.

Everything Alto keeps goes into a backup (the database and the saved preferences), and importing one replaces everything, so an
import into a clean install leaves it as if nothing had changed. Before an import replaces what is there, a backup of that is
saved next to the database, so a wrong choice can be undone.

Examples
--------
>>> default_name(now=0.0).endswith(".altobackup")
True
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QWidget,
)

from alto.learning.backup import (
    BackupError,
    BackupInfo,
    read_backup,
    restore_database,
    write_backup,
)
from alto.learning.database import Database
from alto.ui.store import (
    export_settings,
    import_settings,
)

EXTENSION = ".altobackup"
FILTER = f"Alto backup (*{EXTENSION})"
EXPORT_TITLE, IMPORT_TITLE = "Export backup", "Import backup"


def default_name(*, now: float | None = None) -> str:
    """
    Suggest a file name for a backup made now.

    Parameters
    ----------
    now : float or None, default None
        The time as a timestamp; the clock is used if None. Keyword-only.

    Returns
    -------
    str
        For example `alto-backup-2026-11-13.altobackup`.

    Examples
    --------
    >>> default_name(now=datetime(2026, 11, 13, 12).timestamp())
    'alto-backup-2026-11-13.altobackup'
    """
    when = datetime.fromtimestamp(time.time() if now is None else now)
    return f"alto-backup-{when:%Y-%m-%d}{EXTENSION}"


def counted(
    number: int,
    *,
    noun: str,
) -> str:
    """
    Write a count with its noun, in the plural unless there is one.

    Parameters
    ----------
    number : int
        The count.
    noun : str
        The singular noun. Keyword-only.

    Returns
    -------
    str
        For example "1 profile" or "12,345 answers".

    Examples
    --------
    >>> counted(1, noun="profile"), counted(12345, noun="answer")
    ('1 profile', '12,345 answers')
    """
    return f"{number:,} {noun}" + ("" if number == 1 else "s")


def describe(info: BackupInfo) -> str:
    """
    Say what a backup holds and when it was made, for the question asked before importing it.

    Parameters
    ----------
    info : BackupInfo
        What the backup says about itself.

    Returns
    -------
    str
        A sentence or two.

    Examples
    --------
    >>> text = describe(BackupInfo(datetime(2026, 11, 13, 9, 30).timestamp(), app_version="0.1.0", schema_version=1,
    ...                            profiles=2, attempts=1500))
    >>> text
    'Made on 13 November 2026, 09:30 by Alto 0.1.0. It holds 2 profiles and 1,500 answers.'
    """
    when = datetime.fromtimestamp(info.created)
    return (
        f"Made on {when.day} {when:%B %Y, %H:%M} by Alto {info.app_version}. "
        f"It holds {counted(info.profiles, noun='profile')} and {counted(info.attempts, noun='answer')}."
    )


def export_backup(
    parent: QWidget,
    *,
    db: Database,
) -> Path | None:
    """
    Ask where to save a backup, and write it.

    Parameters
    ----------
    parent : QWidget
        The window the dialogs belong to.
    db : Database
        The database to back up. Keyword-only.

    Returns
    -------
    Path or None
        The file that was written, or None if the user cancelled or the backup could not be written (which is explained).

    Examples
    --------
    >>> export_backup(QWidget(), db=Database())  # doctest: +SKIP
    PosixPath('/home/ada/alto-backup-2026-11-13.altobackup')
    """
    name, _ = QFileDialog.getSaveFileName(
        parent,
        EXPORT_TITLE,
        str(Path.home() / default_name()),
        FILTER,
    )
    if not name:
        return None
    path = Path(name)
    if path.suffix != EXTENSION:
        path = path.with_name(path.name + EXTENSION)
    try:
        info = write_backup(db, settings=export_settings(), path=path)
    except BackupError as error:
        QMessageBox.warning(parent, EXPORT_TITLE, str(error))
        return None
    QMessageBox.information(
        parent,
        EXPORT_TITLE,
        f"Saved {counted(info.profiles, noun='profile')} and {counted(info.attempts, noun='answer')}, "
        f"with your settings, to:\n{path}",
    )
    return path


def safety_copy(db: Database) -> Path | None:
    """
    Save a backup of what the database holds now, beside it, before it is replaced.

    Parameters
    ----------
    db : Database
        The database about to be replaced.

    Returns
    -------
    Path or None
        The file written, or None for a throwaway in-memory database, which has no folder to keep a copy in.

    Raises
    ------
    BackupError
        If the copy cannot be written.

    Examples
    --------
    >>> safety_copy(Database()) is None
    True
    """
    if db.path == ":memory:":
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(db.path).parent / f"alto-before-import-{stamp}{EXTENSION}"
    write_backup(db, settings=export_settings(), path=path)
    return path


def import_backup(
    parent: QWidget,
    *,
    db: Database,
) -> bool:
    """
    Ask for a backup file and, once the user has agreed, replace everything with what it holds.

    The file is read and checked completely first, so a damaged or foreign file changes nothing. After the user agrees, a
    backup of the current data is saved beside the database, then the database and the saved preferences are replaced. The
    caller has to reload what is on screen afterwards.

    Parameters
    ----------
    parent : QWidget
        The window the dialogs belong to.
    db : Database
        The database to replace the contents of. Keyword-only.

    Returns
    -------
    bool
        True if the backup was applied; False if the user cancelled or the file was refused (which is explained).

    Examples
    --------
    >>> import_backup(QWidget(), db=Database())  # doctest: +SKIP
    True
    """
    name, _ = QFileDialog.getOpenFileName(
        parent,
        IMPORT_TITLE,
        str(Path.home()),
        f"{FILTER};;All files (*)",
    )
    if not name:
        return False
    try:
        backup = read_backup(Path(name))
    except BackupError as error:
        QMessageBox.warning(parent, IMPORT_TITLE, str(error))
        return False
    if backup.info.profiles == 0:
        QMessageBox.warning(parent, IMPORT_TITLE, "This backup has no profiles in it, so there is nothing to restore.")
        return False
    kept = "A copy of what is there now is saved first, so this can be undone." if db.path != ":memory:" else ""
    agreed = QMessageBox.question(
        parent,
        IMPORT_TITLE,
        f"Replace everything in Alto with this backup?\n\n{describe(backup.info)}\n\n"
        f"Your current profiles, history and settings will be replaced. {kept}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if agreed != QMessageBox.StandardButton.Yes:
        return False
    try:
        saved = safety_copy(db)
        restore_database(db, backup=backup)
    except BackupError as error:
        QMessageBox.warning(parent, IMPORT_TITLE, f"{error}\n\nNothing was changed.")
        return False
    import_settings(backup.settings)
    QMessageBox.information(
        parent,
        IMPORT_TITLE,
        "The backup has been imported." + (f"\n\nWhat was here before is kept in:\n{saved}" if saved else ""),
    )
    return True
