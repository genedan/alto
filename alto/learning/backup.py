"""
Backup files: everything Alto keeps, in one file that can be read back into a clean install. Pure Python (no Qt).

A backup is a zip file holding three things: the whole database (profiles, every answer, what is known about each question),
the saved preferences (theme, fonts, instrument, every exercise's settings, the last profile used) and a manifest that says
which version of Alto made it and carries a checksum of each part. Reading a backup back checks the checksums and the database
before anything is changed, so a damaged or foreign file is refused instead of half applied.

Examples
--------
>>> import tempfile
>>> from alto.learning.database import Database
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> folder = Path(tempfile.mkdtemp())
>>> info = write_backup(db, settings={"ui/theme": "dark"}, path=folder / "ada.altobackup")
>>> info.profiles, info.attempts
(1, 0)
>>> backup = read_backup(folder / "ada.altobackup")
>>> backup.settings
{'ui/theme': 'dark'}
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import zipfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from alto.learning.database import check_snapshot

if TYPE_CHECKING:
    from collections.abc import Mapping

    from alto.learning.database import Database

FORMAT = 1
DATABASE_FILE, SETTINGS_FILE, MANIFEST_FILE = "alto.db", "settings.json", "manifest.json"


class BackupError(Exception):
    """
    A backup file could not be written or read: it is damaged, is not a backup, or was made by a newer Alto.

    Examples
    --------
    >>> str(BackupError("This is not an Alto backup."))
    'This is not an Alto backup.'
    """


@dataclass(frozen=True)
class BackupInfo:
    """
    What a backup says about itself.

    Attributes
    ----------
    created : float
        When it was made, as a timestamp.
    app_version : str
        The version of Alto that made it.
    schema_version : int
        The version of the database layout it holds.
    profiles : int
        How many profiles it holds.
    attempts : int
        How many answers it holds.

    Examples
    --------
    >>> BackupInfo(100.0, app_version="0.1.0", schema_version=1, profiles=2, attempts=30).profiles
    2
    """

    created: float
    app_version: str
    schema_version: int
    profiles: int
    attempts: int


@dataclass(frozen=True)
class Backup:
    """
    A backup that has been read and checked, ready to be applied.

    Attributes
    ----------
    info : BackupInfo
        What the backup says about itself.
    settings : dict of str to object
        The saved preferences, by key.
    database : bytes
        The database, as `Database.snapshot` returns it.

    Examples
    --------
    >>> Backup(BackupInfo(1.0, app_version="0.1.0", schema_version=1, profiles=0, attempts=0), settings={}, database=b"").settings
    {}
    """

    info: BackupInfo
    settings: dict[str, object]
    database: bytes


def app_version() -> str:
    """
    Return the version of Alto that is running.

    Returns
    -------
    str
        The installed version, or "unknown" if Alto was not installed as a package.

    Examples
    --------
    >>> app_version().count(".") >= 1
    True
    """
    try:
        return metadata.version("alto")
    except metadata.PackageNotFoundError:  # pragma: no cover  (running from a source tree that was never installed)
        return "unknown"


def encode_value(value: object) -> object:
    r"""
    Turn a saved preference into something JSON can hold.

    Text, numbers, true and false and lists of them are kept as they are. Bytes, which Qt settings can hold, become a small
    dictionary with the bytes in base64, so `decode_value` can bring them back.

    Parameters
    ----------
    value : object
        The value of a preference.

    Returns
    -------
    object
        The same value, or its encoded form.

    Examples
    --------
    >>> encode_value("dark"), encode_value(5), encode_value(["a", "b"])
    ('dark', 5, ['a', 'b'])
    >>> encode_value(b"\x00\x01")
    {'bytes': 'AAE='}
    """
    if isinstance(value, bytes):
        return {"bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, list):
        return [encode_value(v) for v in value]
    return value


def decode_value(value: object) -> object:
    r"""
    Undo `encode_value`.

    Parameters
    ----------
    value : object
        A value read from a backup.

    Returns
    -------
    object
        The preference's value, with bytes restored.

    Examples
    --------
    >>> decode_value({"bytes": "AAE="})
    b'\x00\x01'
    >>> decode_value([1, 2])
    [1, 2]
    """
    if isinstance(value, dict) and set(value) == {"bytes"}:
        return base64.b64decode(str(value["bytes"]))
    if isinstance(value, list):
        return [decode_value(v) for v in value]
    return value


def _digest(data: bytes) -> str:
    """
    Return the checksum of some bytes.

    Parameters
    ----------
    data : bytes
        What to summarise.

    Returns
    -------
    str
        The SHA-256 of the data, in hexadecimal.

    Examples
    --------
    >>> _digest(b"")[:16]
    'e3b0c44298fc1c14'
    """
    return hashlib.sha256(data).hexdigest()


def write_backup(
    db: Database,
    *,
    settings: Mapping[str, object],
    path: Path,
    now: float | None = None,
) -> BackupInfo:
    """
    Write a backup of the database and the saved preferences to a file.

    Parameters
    ----------
    db : Database
        The database to back up. It is not changed.
    settings : mapping of str to object
        The saved preferences, by key. Keyword-only.
    path : Path
        The file to write; it is replaced if it exists. Keyword-only.
    now : float or None, default None
        The time to record, as a timestamp; the clock is used if None. Keyword-only.

    Returns
    -------
    BackupInfo
        What the backup says about itself.

    Raises
    ------
    BackupError
        If the file cannot be written. Nothing is left at `path` in that case.

    Examples
    --------
    >>> import tempfile
    >>> from alto.learning.database import Database
    >>> folder = Path(tempfile.mkdtemp())
    >>> write_backup(Database(), settings={}, path=folder / "empty.altobackup", now=5.0).created
    5.0
    """
    data = db.snapshot()
    schema_version, profiles, attempts = check_snapshot(data)
    plain = json.dumps({k: encode_value(v) for k, v in sorted(settings.items())}, indent=2).encode("utf-8")
    info = BackupInfo(
        created=time.time() if now is None else now,
        app_version=app_version(),
        schema_version=schema_version,
        profiles=profiles,
        attempts=attempts,
    )
    manifest = {
        "format": FORMAT,
        "app": "alto",
        "app_version": info.app_version,
        "created": info.created,
        "schema_version": info.schema_version,
        "profiles": info.profiles,
        "attempts": info.attempts,
        "checksums": {DATABASE_FILE: _digest(data), SETTINGS_FILE: _digest(plain)},
    }
    partial = path.with_name(
        path.name + ".part",
    )  # written beside the target and moved into place, so a failure leaves no half file
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(MANIFEST_FILE, json.dumps(manifest, indent=2))
            z.writestr(SETTINGS_FILE, plain)
            z.writestr(DATABASE_FILE, data)
        partial.replace(path)
    except OSError as error:
        partial.unlink(missing_ok=True)
        raise BackupError(f"The backup could not be written: {error.strerror or error}.") from error
    return info


def read_backup(path: Path) -> Backup:
    """
    Read a backup file and check it all the way through, without changing anything.

    Parameters
    ----------
    path : Path
        The file.

    Returns
    -------
    Backup
        The backup, ready to be applied.

    Raises
    ------
    BackupError
        If the file cannot be read, is not an Alto backup, is damaged (a part does not match its checksum, or the database is
        not intact), or was made by a newer version of Alto.

    Examples
    --------
    >>> import tempfile
    >>> folder = Path(tempfile.mkdtemp())
    >>> (folder / "x.altobackup").write_bytes(b"not a zip")
    9
    >>> read_backup(folder / "x.altobackup")
    Traceback (most recent call last):
        ...
    alto.learning.backup.BackupError: This is not an Alto backup.
    """
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if not {MANIFEST_FILE, SETTINGS_FILE, DATABASE_FILE} <= names:
                raise BackupError("This is not an Alto backup.")
            manifest = json.loads(z.read(MANIFEST_FILE))
            plain, data = z.read(SETTINGS_FILE), z.read(DATABASE_FILE)
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError, UnicodeDecodeError):
        raise BackupError("This is not an Alto backup.") from None
    except OSError as error:
        raise BackupError(f"The file could not be read: {error.strerror or error}.") from error
    if not isinstance(manifest, dict) or manifest.get("app") != "alto":
        raise BackupError("This is not an Alto backup.")
    if not isinstance(manifest.get("format"), int) or manifest["format"] > FORMAT:
        raise BackupError("This backup was made by a newer version of Alto. Update Alto to read it.")
    checksums = manifest.get("checksums", {})
    if checksums.get(DATABASE_FILE) != _digest(data) or checksums.get(SETTINGS_FILE) != _digest(plain):
        raise BackupError("This backup is damaged: its contents do not match their checksums.")
    try:
        schema_version, profiles, attempts = check_snapshot(data)
        settings = json.loads(plain)
    except (ValueError, UnicodeDecodeError) as error:
        raise BackupError(str(error)) from error
    if not isinstance(settings, dict):
        raise BackupError("This is not an Alto backup.")
    return Backup(
        info=BackupInfo(
            created=float(manifest.get("created", 0.0)),
            app_version=str(manifest.get("app_version", "unknown")),
            schema_version=schema_version,
            profiles=profiles,
            attempts=attempts,
        ),
        settings={str(k): decode_value(v) for k, v in settings.items()},
        database=data,
    )


def restore_database(
    db: Database,
    *,
    backup: Backup,
) -> None:
    """
    Replace everything in the database with what a backup holds.

    Parameters
    ----------
    db : Database
        The database to replace the contents of.
    backup : Backup
        A backup, as `read_backup` returns it. Keyword-only.

    Raises
    ------
    BackupError
        If the database in the backup cannot be loaded. The database is not changed.

    Examples
    --------
    >>> import tempfile
    >>> from alto.learning.database import Database
    >>> source = Database()
    >>> _ = source.add_profile("Ada")
    >>> folder = Path(tempfile.mkdtemp())
    >>> _ = write_backup(source, settings={}, path=folder / "a.altobackup")
    >>> clean = Database()
    >>> restore_database(clean, backup=read_backup(folder / "a.altobackup"))
    >>> [p.name for p in clean.profiles()]
    ['Ada']
    """
    try:
        db.restore(backup.database)
    except ValueError as error:
        raise BackupError(str(error)) from error
