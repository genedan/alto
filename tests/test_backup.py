"""Backups: everything Alto keeps goes into one file, and importing it into a clean install leaves nothing different."""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QByteArray

from alto.learning.backup import (
    DATABASE_FILE,
    FORMAT,
    MANIFEST_FILE,
    SETTINGS_FILE,
    BackupError,
    decode_value,
    encode_value,
    read_backup,
    restore_database,
    write_backup,
)
from alto.learning.database import (
    SCHEMA_VERSION,
    Database,
    check_snapshot,
)
from alto.ui.store import (
    export_settings,
    import_settings,
    store,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from alto.learning import Learner

TABLES = ("profiles", "attempts", "items")


def everything(db: Database) -> dict[str, list[tuple]]:
    """
    Read every row of every table, in a fixed order, so two databases can be compared.

    Parameters
    ----------
    db : Database
        The database.

    Returns
    -------
    dict of str to list of tuple
        The rows of each table.
    """
    return {t: [tuple(r) for r in db.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3")] for t in TABLES}


def forge(
    path: Path,
    *,
    database: bytes | None = None,
    settings: bytes = b"{}",
    manifest: dict | None = None,
) -> Path:
    """
    Write a backup file by hand, with correct checksums unless told otherwise, to try the checks on damaged ones.

    Parameters
    ----------
    path : Path
        The file to write.
    database : bytes or None
        The database inside; an empty Alto database if None. Keyword-only.
    settings : bytes
        The settings file inside. Keyword-only.
    manifest : dict or None
        Entries that replace or add to the manifest. Keyword-only.

    Returns
    -------
    Path
        The file.
    """
    data = database if database is not None else Database().snapshot()
    entries = {
        "format": FORMAT,
        "app": "alto",
        "app_version": "0.0.0",
        "created": 1.0,
        "checksums": {
            DATABASE_FILE: hashlib.sha256(data).hexdigest(),
            SETTINGS_FILE: hashlib.sha256(settings).hexdigest(),
        },
        **(manifest or {}),
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(MANIFEST_FILE, json.dumps(entries))
        z.writestr(SETTINGS_FILE, settings)
        z.writestr(DATABASE_FILE, data)
    return path


def test_importing_a_backup_into_a_clean_install_restores_every_row_exactly(
    practised_learner: Callable[..., Learner],
    tmp_path: Path,
) -> None:
    """
    Check that every profile, answer and question record comes back exactly, with the same ids, in a clean database.

    Parameters
    ----------
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    source = practised_learner(60).db
    practised_learner(30, name="Ben", db=source)
    path = tmp_path / "all.altobackup"
    info = write_backup(source, settings={}, path=path)
    clean = Database()
    restore_database(clean, backup=read_backup(path))
    assert everything(clean) == everything(source) and len(everything(source)["attempts"]) > 20
    assert info.profiles == 2 and info.attempts == len(everything(source)["attempts"])
    assert clean.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_a_restored_database_works_as_before(
    practised_learner: Callable[..., Learner],
    tmp_path: Path,
) -> None:
    """
    Check that after a restore the database enforces its rules and takes new answers, as the original did.

    Parameters
    ----------
    practised_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    source = practised_learner(30).db
    ada = source.profiles()[0]
    write_backup(source, settings={}, path=tmp_path / "a.altobackup")
    target = Database(tmp_path / "target.db")
    restore_database(target, backup=read_backup(tmp_path / "a.altobackup"))
    before = target.count_attempts(ada.id)
    target.add_attempt(
        ada.id,
        exercise="NoteNames",
        item_key="k",
        attempt_no=1,
        answer="C",
        correct=True,
        duration_ms=1,
        answered_at=1.0,
    )
    assert target.count_attempts(ada.id) == before + 1
    with pytest.raises(sqlite3.IntegrityError):  # foreign keys are still enforced
        target.add_attempt(
            999,
            exercise="x",
            item_key="k",
            attempt_no=1,
            answer="C",
            correct=True,
            duration_ms=1,
            answered_at=1.0,
        )
    target.close()
    reopened = Database(tmp_path / "target.db")  # and what was restored is on disk, not only in memory
    assert reopened.count_attempts(ada.id) == before + 1


def test_a_restore_replaces_what_was_there_instead_of_merging(tmp_path: Path) -> None:
    """
    Check that profiles and answers in the database before a restore are gone afterwards.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    source = Database()
    source.add_profile("Ada")
    write_backup(source, settings={}, path=tmp_path / "a.altobackup")
    target = Database()
    ben = target.add_profile("Ben")
    target.add_attempt(
        ben.id,
        exercise="NoteNames",
        item_key="k",
        attempt_no=1,
        answer="C",
        correct=True,
        duration_ms=1,
        answered_at=1.0,
    )
    restore_database(target, backup=read_backup(tmp_path / "a.altobackup"))
    assert [p.name for p in target.profiles()] == ["Ada"] and everything(target)["attempts"] == []


@pytest.mark.parametrize(
    ("what", "message"),
    [
        ("not a zip", "not an Alto backup"),
        ("no manifest", "not an Alto backup"),
        ("another app", "not an Alto backup"),
        ("newer format", "newer version of Alto"),
        ("changed database", "damaged"),
        ("changed settings", "damaged"),
        ("garbage database", "not an Alto database"),
        ("empty sqlite database", "not an Alto database"),
        ("newer schema", "newer version of Alto"),
        ("settings that are not a table", "not an Alto backup"),
    ],
)
def test_a_file_that_is_not_a_sound_backup_is_refused_with_a_reason(
    what: str,
    message: str,
    tmp_path: Path,
) -> None:
    """
    Check that damaged, foreign and newer files are refused, and say why, before anything could be changed.

    Parameters
    ----------
    what : str
        What is wrong with the file, supplied by the parametrisation.
    message : str
        Part of the explanation expected, supplied by the parametrisation.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    path = tmp_path / "bad.altobackup"
    good = tmp_path / "good.altobackup"
    write_backup(Database(), settings={"a": "b"}, path=good)
    newer = sqlite3.connect(":memory:")
    newer.executescript(
        "CREATE TABLE profiles (id); CREATE TABLE attempts (id); CREATE TABLE items (id); PRAGMA user_version = 99",
    )
    plain = sqlite3.connect(":memory:")
    plain.execute("CREATE TABLE t (x)")
    if what == "not a zip":
        path.write_bytes(b"this is not a zip file")
    elif what == "no manifest":
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("something.txt", "x")
    elif what == "another app":
        forge(path, manifest={"app": "other"})
    elif what == "newer format":
        forge(path, manifest={"format": FORMAT + 1})
    elif what in ("changed database", "changed settings"):
        changed = DATABASE_FILE if what == "changed database" else SETTINGS_FILE
        with zipfile.ZipFile(good) as z, zipfile.ZipFile(path, "w") as out:
            for name in z.namelist():
                data = z.read(name)
                out.writestr(name, data + b"x" if name == changed else data)
    elif what == "garbage database":
        forge(path, database=b"garbage" * 100)
    elif what == "empty sqlite database":
        forge(path, database=plain.serialize())
    elif what == "newer schema":
        forge(path, database=newer.serialize())
    else:
        forge(path, settings=b"[1, 2]")
    with pytest.raises(BackupError, match=message):
        read_backup(path)


def test_a_backup_that_cannot_be_written_leaves_nothing_behind(tmp_path: Path) -> None:
    """
    Check that a backup that cannot be written is reported, and leaves neither the file nor a half-written one.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    target = tmp_path / "missing folder" / "x.altobackup"
    with pytest.raises(BackupError, match="could not be written"):
        write_backup(Database(), settings={}, path=target)
    assert not target.exists() and not target.with_name(target.name + ".part").exists()


def test_a_backup_that_is_replaced_is_replaced_whole(tmp_path: Path) -> None:
    """
    Check that writing a backup over an older one leaves a complete, readable file, never a mixture.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    path = tmp_path / "x.altobackup"
    db = Database()
    db.add_profile("Ada")
    write_backup(db, settings={"n": 1}, path=path)
    db.add_profile("Ben")
    write_backup(db, settings={"n": 2}, path=path)
    backup = read_backup(path)
    assert backup.info.profiles == 2 and backup.settings == {"n": 2}


def test_the_manifest_says_what_the_backup_holds(tmp_path: Path) -> None:
    """
    Check that the backup says when and by which version it was made, and what is in it.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    db = Database()
    db.add_profile("Ada")
    write_backup(db, settings={}, path=tmp_path / "x.altobackup", now=1234.0)
    info = read_backup(tmp_path / "x.altobackup").info
    assert (info.created, info.profiles, info.attempts, info.schema_version) == (1234.0, 1, 0, SCHEMA_VERSION)
    assert info.app_version
    with zipfile.ZipFile(tmp_path / "x.altobackup") as z:
        assert set(z.namelist()) == {MANIFEST_FILE, SETTINGS_FILE, DATABASE_FILE}


def test_a_snapshot_is_checked_before_it_is_used() -> None:
    """
    Check that a database that is not an intact Alto database, or is from a newer version, is refused and nothing is changed.
    """
    db = Database()
    db.add_profile("Ada")
    with pytest.raises(ValueError, match="not an Alto database"):
        db.restore(b"nope")
    assert [p.name for p in db.profiles()] == ["Ada"]
    damaged = bytearray(Database().snapshot())
    damaged[len(damaged) // 2 :] = b"\xff" * (len(damaged) - len(damaged) // 2)
    with pytest.raises(ValueError, match="database|Alto"):
        check_snapshot(bytes(damaged))


def test_preferences_survive_the_trip_in_every_form_qt_can_hold() -> None:
    """
    Check that text, numbers, true and false, lists and bytes come back from a backup as they went in.
    """
    values = {"a": "text", "b": 3, "c": 2.5, "d": True, "e": ["x", "y"], "f": b"\x00\xff", "g": ["a", b"b"]}
    packed = json.loads(json.dumps({k: encode_value(v) for k, v in values.items()}))
    assert {k: decode_value(v) for k, v in packed.items()} == values


def test_importing_preferences_makes_them_exactly_what_the_backup_had() -> None:
    """
    Check that the saved preferences are replaced, not merged: ones the backup has are set and the others are gone.
    """
    saved = store()
    saved.setValue("ui/theme", "dark")
    saved.setValue("noteNames/clefs", "treble,bass")
    saved.setValue("keyboard/low", 36)
    saved.setValue("blob", QByteArray(b"\x01\x02"))
    exported = export_settings()
    assert exported["blob"] == b"\x01\x02" and exported["ui/theme"] == "dark"
    saved.setValue("ui/theme", "light")  # what a different install has: another value, and a key the backup lacks
    saved.setValue("only/here", "x")
    import_settings(exported)
    assert export_settings() == exported and "only/here" not in export_settings()
    assert "migratedFromMtheory" in export_settings()  # the marker stays, so old preferences are not brought back


def test_settings_that_a_backup_lacks_cannot_bring_back_old_preferences() -> None:
    """
    Check that importing a backup made without the migration marker still records that migration is done.
    """
    import_settings({"ui/theme": "dark"})
    assert store().contains("migratedFromMtheory") and store().value("ui/theme") == "dark"


def test_a_zip_of_the_wrong_kind_is_not_mistaken_for_a_backup(tmp_path: Path) -> None:
    """
    Check that an ordinary zip file with other things in it is refused.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("photo.jpg", "x")
    (tmp_path / "x.zip").write_bytes(buffer.getvalue())
    with pytest.raises(BackupError, match="not an Alto backup"):
        read_backup(tmp_path / "x.zip")
