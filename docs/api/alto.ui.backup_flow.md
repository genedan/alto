---
title: alto.ui.backup_flow
parent: api
package: alto.ui
order: 14
permalink: /api/alto.ui.backup_flow/
---
{% raw %}
Exporting a backup and importing one: the file dialogs, the questions asked, and the safety copy made before anything is replaced.

Everything Alto keeps goes into a backup (the database and the saved preferences), and importing one replaces everything, so an
import into a clean install leaves it as if nothing had changed. Before an import replaces what is there, a backup of that is
saved next to the database, so a wrong choice can be undone.

**Examples**

```pycon
>>> default_name(now=0.0).endswith(".altobackup")
True
```

## default_name

```python
def default_name(
    *,
    now: float | None = None,
) -> str
```

Suggest a file name for a backup made now.

**Parameters**

- `now` (*float or None, default None*): The time as a timestamp; the clock is used if None. Keyword-only.

**Returns**

- *str*: For example `alto-backup-2026-11-13.altobackup`.

**Examples**

```pycon
>>> default_name(now=datetime(2026, 11, 13, 12).timestamp())
'alto-backup-2026-11-13.altobackup'
```

## counted

```python
def counted(
    number: int,
    *,
    noun: str,
) -> str
```

Write a count with its noun, in the plural unless there is one.

**Parameters**

- `number` (*int*): The count.
- `noun` (*str*): The singular noun. Keyword-only.

**Returns**

- *str*: For example "1 profile" or "12,345 answers".

**Examples**

```pycon
>>> counted(1, noun="profile"), counted(12345, noun="answer")
('1 profile', '12,345 answers')
```

## describe

```python
def describe(info: BackupInfo) -> str
```

Say what a backup holds and when it was made, for the question asked before importing it.

**Parameters**

- `info` (*BackupInfo*): What the backup says about itself.

**Returns**

- *str*: A sentence or two.

**Examples**

```pycon
>>> text = describe(BackupInfo(datetime(2026, 11, 13, 9, 30).timestamp(), app_version="0.1.0", schema_version=1,
...                            profiles=2, attempts=1500))
>>> text
'Made on 13 November 2026, 09:30 by Alto 0.1.0. It holds 2 profiles and 1,500 answers.'
```

## export_backup

```python
def export_backup(
    parent: QWidget,
    *,
    db: Database,
) -> Path | None
```

Ask where to save a backup, and write it.

**Parameters**

- `parent` (*QWidget*): The window the dialogs belong to.
- `db` (*Database*): The database to back up. Keyword-only.

**Returns**

- *Path or None*: The file that was written, or None if the user cancelled or the backup could not be written (which is explained).

**Examples**

```pycon
>>> export_backup(QWidget(), db=Database())  # doctest: +SKIP
PosixPath('/home/ada/alto-backup-2026-11-13.altobackup')
```

## safety_copy

```python
def safety_copy(db: Database) -> Path | None
```

Save a backup of what the database holds now, beside it, before it is replaced.

**Parameters**

- `db` (*Database*): The database about to be replaced.

**Returns**

- *Path or None*: The file written, or None for a throwaway in-memory database, which has no folder to keep a copy in.

**Raises**

- *BackupError*: If the copy cannot be written.

**Examples**

```pycon
>>> safety_copy(Database()) is None
True
```

## import_backup

```python
def import_backup(
    parent: QWidget,
    *,
    db: Database,
) -> bool
```

Ask for a backup file and, once the user has agreed, replace everything with what it holds.

The file is read and checked completely first, so a damaged or foreign file changes nothing. After the user agrees, a
backup of the current data is saved beside the database, then the database and the saved preferences are replaced. The
caller has to reload what is on screen afterwards.

**Parameters**

- `parent` (*QWidget*): The window the dialogs belong to.
- `db` (*Database*): The database to replace the contents of. Keyword-only.

**Returns**

- *bool*: True if the backup was applied; False if the user cancelled or the file was refused (which is explained).

**Examples**

```pycon
>>> import_backup(QWidget(), db=Database())  # doctest: +SKIP
True
```
{% endraw %}
