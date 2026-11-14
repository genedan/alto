---
title: Your data
nav_order: 8
permalink: /data/
---
Everything Alto stores is on your own computer.

- Alto makes **no network connections**. It has no accounts, no sync and no analytics.
- Your name is only a label for a profile in a local file.

## Where it is

Your practice history, profiles included, is one [SQLite](https://www.sqlite.org/) file named `alto.db`:

| System | Location |
|---|---|
| Linux | `~/.local/share/Alto/alto.db` |
| macOS | `~/Library/Application Support/Alto/alto.db` |
| Windows | `C:\Users\<you>\AppData\Roaming\Alto\alto.db` |

Your settings (theme, notation style, keyboard style, instrument, exercise options and the last profile you used) are stored separately by Qt, in
your usual configuration location.

## What the file contains

| Table | Holds |
|---|---|
| `profiles` | Each profile's name and when it was created. |
| `attempts` | One row for every answer: the profile, exercise, question, your answer, whether it was right, the attempt number, how long it took and when. |
| `items` | What is known about each question: its strain, how often it was answered and missed, its typical time, when it was last seen, and the question itself so it can be asked again. |

Because it is a normal SQLite file, you can open it with any SQLite tool if you want to run your own queries. Close Alto
first. Alto's own [database browser]({{ '/statistics/' | relative_url }}) is read-only.

## Backing up and restoring

Open the menu (☰) and choose **Export backup…** to save everything Alto keeps to one file: all the profiles, every answer
and the record of each question, and every setting (the theme, the notation and keyboard styles, the instrument, each
exercise's options and the profile you used last). Choose **Import backup…** to read one back.

Importing **replaces everything** with the backup, so on a clean install, or on another computer, Alto comes up exactly as it
was when the backup was made: same profiles, same history, same settings, and the same profile open. Nothing is merged. What
is there before the import is gone from the app, so Alto saves a backup of it first, next to `alto.db` in a file named
`alto-before-import-<date and time>.altobackup`. If you imported the wrong file, import that one to put everything back.

- A backup file ends in `.altobackup`. It is a zip file holding the database, the settings and a note of which version of Alto
  made it, with a checksum of each part.
- Before anything is changed, Alto checks the file all the way through. A file that is damaged, is not an Alto backup, or was made
  by a **newer** version of Alto is refused with an explanation, and nothing changes. A backup from an older version is brought
  up to date as it is imported.
- A backup contains your whole practice history, so keep it as private as the history itself.

To move to another computer: install Alto there, start it once (it asks for a first profile), then import the backup.

## Copying the files by hand

- **Back up the history only:** close Alto and copy `alto.db` somewhere safe. Copy it back to restore it. This leaves out the settings; **Export backup…** includes them.
- **Move the history to another computer:** copy the file to the same location there.
- **Start over:** close Alto and delete `alto.db`. The next launch asks for a new profile and starts with an empty history.
