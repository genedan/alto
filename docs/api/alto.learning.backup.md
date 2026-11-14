---
title: alto.learning.backup
parent: api
package: alto.learning
order: 6
permalink: /api/alto.learning.backup/
---
{% raw %}
Backup files: everything Alto keeps, in one file that can be read back into a clean install. Pure Python (no Qt).

A backup is a zip file holding three things: the whole database (profiles, every answer, what is known about each question),
the saved preferences (theme, fonts, instrument, every exercise's settings, the last profile used) and a manifest that says
which version of Alto made it and carries a checksum of each part. Reading a backup back checks the checksums and the database
before anything is changed, so a damaged or foreign file is refused instead of half applied.

**Examples**

```pycon
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
```

## BackupError

```python
class BackupError(Exception)
```

A backup file could not be written or read: it is damaged, is not a backup, or was made by a newer Alto.

**Examples**

```pycon
>>> str(BackupError("This is not an Alto backup."))
'This is not an Alto backup.'
```

## BackupInfo

```python
BackupInfo(
    created: float,
    app_version: str,
    schema_version: int,
    profiles: int,
    attempts: int,
)
```

What a backup says about itself.

**Attributes**

- `created` (*float*): When it was made, as a timestamp.
- `app_version` (*str*): The version of Alto that made it.
- `schema_version` (*int*): The version of the database layout it holds.
- `profiles` (*int*): How many profiles it holds.
- `attempts` (*int*): How many answers it holds.

**Examples**

```pycon
>>> BackupInfo(100.0, app_version="0.1.0", schema_version=1, profiles=2, attempts=30).profiles
2
```

## Backup

```python
Backup(
    info: BackupInfo,
    settings: dict[str, object],
    database: bytes,
)
```

A backup that has been read and checked, ready to be applied.

**Attributes**

- `info` (*BackupInfo*): What the backup says about itself.
- `settings` (*dict of str to object*): The saved preferences, by key.
- `database` (*bytes*): The database, as `Database.snapshot` returns it.

**Examples**

```pycon
>>> Backup(BackupInfo(1.0, app_version="0.1.0", schema_version=1, profiles=0, attempts=0), settings={}, database=b"").settings
{}
```

## app_version

```python
def app_version() -> str
```

Return the version of Alto that is running.

**Returns**

- *str*: The installed version, or "unknown" if Alto was not installed as a package.

**Examples**

```pycon
>>> app_version().count(".") >= 1
True
```

## encode_value

```python
def encode_value(value: object) -> object
```

Turn a saved preference into something JSON can hold.

Text, numbers, true and false and lists of them are kept as they are. Bytes, which Qt settings can hold, become a small
dictionary with the bytes in base64, so `decode_value` can bring them back.

**Parameters**

- `value` (*object*): The value of a preference.

**Returns**

- *object*: The same value, or its encoded form.

**Examples**

```pycon
>>> encode_value("dark"), encode_value(5), encode_value(["a", "b"])
('dark', 5, ['a', 'b'])
>>> encode_value(b"\x00\x01")
{'bytes': 'AAE='}
```

## decode_value

```python
def decode_value(value: object) -> object
```

Undo `encode_value`.

**Parameters**

- `value` (*object*): A value read from a backup.

**Returns**

- *object*: The preference's value, with bytes restored.

**Examples**

```pycon
>>> decode_value({"bytes": "AAE="})
b'\x00\x01'
>>> decode_value([1, 2])
[1, 2]
```

## write_backup

```python
def write_backup(
    db: Database,
    *,
    settings: Mapping[str, object],
    path: Path,
    now: float | None = None,
) -> BackupInfo
```

Write a backup of the database and the saved preferences to a file.

**Parameters**

- `db` (*Database*): The database to back up. It is not changed.
- `settings` (*mapping of str to object*): The saved preferences, by key. Keyword-only.
- `path` (*Path*): The file to write; it is replaced if it exists. Keyword-only.
- `now` (*float or None, default None*): The time to record, as a timestamp; the clock is used if None. Keyword-only.

**Returns**

- *BackupInfo*: What the backup says about itself.

**Raises**

- *BackupError*: If the file cannot be written. Nothing is left at `path` in that case.

**Examples**

```pycon
>>> import tempfile
>>> from alto.learning.database import Database
>>> folder = Path(tempfile.mkdtemp())
>>> write_backup(Database(), settings={}, path=folder / "empty.altobackup", now=5.0).created
5.0
```

## read_backup

```python
def read_backup(path: Path) -> Backup
```

Read a backup file and check it all the way through, without changing anything.

**Parameters**

- `path` (*Path*): The file.

**Returns**

- *Backup*: The backup, ready to be applied.

**Raises**

- *BackupError*: If the file cannot be read, is not an Alto backup, is damaged (a part does not match its checksum, or the database is not intact), or was made by a newer version of Alto.

**Examples**

```pycon
>>> import tempfile
>>> folder = Path(tempfile.mkdtemp())
>>> (folder / "x.altobackup").write_bytes(b"not a zip")
9
>>> read_backup(folder / "x.altobackup")
Traceback (most recent call last):
    ...
alto.learning.backup.BackupError: This is not an Alto backup.
```

## restore_database

```python
def restore_database(
    db: Database,
    *,
    backup: Backup,
) -> None
```

Replace everything in the database with what a backup holds.

**Parameters**

- `db` (*Database*): The database to replace the contents of.
- `backup` (*Backup*): A backup, as `read_backup` returns it. Keyword-only.

**Raises**

- *BackupError*: If the database in the backup cannot be loaded. The database is not changed.

**Examples**

```pycon
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
```
{% endraw %}
