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

## Backing up and starting over

- **Back up:** close Alto and copy `alto.db` somewhere safe. Copy it back to restore it.
- **Move to another computer:** copy the file to the same location there.
- **Start over:** close Alto and delete `alto.db`. The next launch asks for a new profile and starts with an empty history.
