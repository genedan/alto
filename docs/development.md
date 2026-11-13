---
title: For developers
nav_order: 9
permalink: /development/
---
Alto is a Python application using PySide6. The source is at [github.com/genedan/alto](https://github.com/genedan/alto).

## Layout

| Folder | What is in it |
|---|---|
| `alto/theory/` | The music theory engine: spelled notes, intervals, scales and chords. Pure Python, no Qt. |
| `alto/exercises/` | The exercises and the `Question` and `Exercise` base classes. No Qt. |
| `alto/learning/` | Profiles, the SQLite database, the scheduler and the statistics calculations. No Qt. |
| `alto/ui/` | The Qt widgets: main window, staff drawing, exercise screen, charts, settings and the database page. |
| `alto/assets/` | Bundled music fonts and instrument recordings. |
| `tests/` | The test suite. |

Keeping the theory, exercises and learning code free of Qt means they can be tested without a display.

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

The tests that touch widgets run with Qt's offscreen platform, so no display is needed.

The tests never read or change your own settings, profile or history. `tests/conftest.py` points them at a throwaway
folder, closes every window and database a test leaves open, and turns the sound off. Every line of `alto/` is covered, so a
change that adds code should add a test for it; `pytest --cov --cov-report=term-missing` shows which lines are missed.

GitHub Actions runs the tests on every pull request (`.github/workflows/tests.yml`) and reports coverage to Codecov
(`.github/workflows/codecov.yml`). To measure coverage yourself:

```bash
pytest --cov --cov-report=term-missing
```

## Type checking

[Pyright](https://github.com/microsoft/pyright) checks the types of `alto`, `tests` and `scripts`, in basic mode, as if
for Python 3.11:

```bash
sh scripts/typecheck.sh
```

It must report no errors. It runs on every pull request (`.github/workflows/pyright.yml`) and before each push. Two things
to know when writing Qt code:

- **Write Qt enums in their full form**, such as `Qt.AlignmentFlag.AlignLeft`, not the short `Qt.AlignLeft`. The short form
  works when the program runs, but Pyright cannot see it.
- Qt functions that may return nothing (`layout()`, `widget()`, `QApplication.instance()`) have to be checked for `None`
  before use, with an `if` or an `assert`.

If Pyright is wrong about one line, silence just that line with `# pyright: ignore[ruleName]` and a short reason.

## Pre-commit

A [pre-commit](https://pre-commit.com/) configuration runs the checks automatically before each commit. Set it up once:

```bash
pip install -e ".[dev]"
pre-commit install
```

It then trims trailing whitespace, makes sure files end with a newline, checks YAML and TOML files, refuses very large
files (the bundled recordings and fonts are exempt) and runs Ruff, applying its safe fixes. If a hook changes a file,
the commit stops so you can review the change, then commit again.

The test suite and Pyright run when you **push**, not on every commit, so commits stay quick. A failing test or a type
error stops the push. Run the commit checks by hand with `pre-commit run --all-files`, the push checks with
`pre-commit run --all-files --hook-stage pre-push`, and update the pinned hook versions with `pre-commit autoupdate`.

## Linting

Alto uses [Ruff](https://docs.astral.sh/ruff/) for linting. It is installed with the `dev` extra and configured in
`pyproject.toml` (pycodestyle, pyflakes, import sorting, pyupgrade and bugbear rules, with a 130-character line limit).

```bash
ruff check alto tests          # report problems
ruff check --fix alto tests    # apply the safe fixes
```

## Adding an exercise

Subclass `Exercise` in `alto/exercises/library.py`, decorate it with `@register`, and implement `generate`, which returns a
`Question`:

```python
@register
class MyExercise(Exercise):
    name = "My exercise"
    category = "Intervals"
    description = "One line shown on the home screen."
    par_seconds = 5.0   # a good first-answer time; see How practice adapts

    def generate(self, rng):
        ...
        return Question("What is this?", choices, answer, staff=[[note]], clef="treble")
```

- `Question` describes everything the screen needs: a prompt, the answer buttons, the notes to draw, a key signature, a keyboard key to highlight, and so on.
- If your exercise reads user settings, override `settings_signature()` and return `signature(...)` of those settings. Stored questions are only replayed while the signature is unchanged.
- Give the exercise an icon in `alto/ui/home.py` so it appears properly on the home screen.

Everything else comes with it: the question is recorded in the database, scored for speed, drawn in the chosen
notation font and included in the statistics.

## Adding an instrument

1. Put its recordings in `alto/assets/samples/<key>/`, one mono WAV per note, named by MIDI note number (for example
   `60.wav` for middle C). Every semitone is best. Where a note has no recording, Alto shifts the nearest one.
2. Add an `Instrument` to `INSTRUMENTS` in `alto/audio.py`. Mark it `sustained=True` if it is bowed or blown, so each
   note ends as the next begins. If it is another way of playing an instrument already listed, give both the same
   `family` and each its own `variant` (the viola's "Arco" and "Pizzicato"), and they appear as one entry with a choice.
3. Add an entry for the same key to `INFO` in `alto/instrument_info.py`: what it is, the source, who played it, and
   the terms. This is what the summary in the Sound settings shows.
4. Credit the recordings in `THIRD_PARTY_NOTICES.md` and the folder's `SOURCE.txt`.

Only add recordings whose licence allows redistribution.

## Adding a notation font

Alto draws notes with fonts that follow the [SMuFL](https://www.smufl.org/) standard.

1. Put the font file and its licence in `alto/assets/fonts/`.
2. Add its stem anchors and engraving defaults to `engraving.json`, read from the font's SMuFL metadata file.
3. Register the file name in `_FILES` in `alto/ui/engraving.py`.
4. Add a `NotationStyle` to `STYLES` in `alto/ui/notation.py`.
5. Record the font in `THIRD_PARTY_NOTICES.md`.

Only add fonts whose licence allows redistribution, such as the SIL Open Font License.

## Adding a keyboard style

Add a `KeyboardStyle` to `STYLES` in `alto/ui/keyboard_styles.py`: the colours of the naturals and sharps, and any extras such as
a case, felt, bone caps or stop knobs. The settings page, the keyboard and the range picker all read from that list, so nothing
else needs changing. Add a row to the table in `docs/settings.md`. The colours named after materials in the builder are `MATERIALS` in the same file.

## Keeping the docs and screenshots current

Every picture in the docs comes as a light and a dark pair, and `scripts/screenshots.py` makes all of them:

```bash
.venv/bin/python scripts/screenshots.py                    # every picture, both themes
.venv/bin/python scripts/screenshots.py --only home stats  # just these
.venv/bin/python scripts/screenshots.py --out /tmp/shots   # somewhere else, to look before replacing
```

It runs against a made-up profile and a temporary settings folder, so it never touches your own history or settings. It
needs a display or `QT_QPA_PLATFORM=offscreen`. Fonts render slightly differently on each machine, so regenerate on the
machine you normally use and look at the pictures before committing them. To add a picture, include it in a docs page
with `shot.html`, and add its name to `SHOTS` in the script. `tests/test_docs.py` checks that both match and that both themes
exist.

The pre-push hook runs `scripts/check-docs.sh`, which warns when the interface (`alto/ui`) has changed since the pictures
were last updated. It only warns; set `ALTO_DOCS_STRICT=1` to make it fail.

## Reporting problems

Open an issue on [GitHub](https://github.com/genedan/alto/issues). Say which operating system and Python version you
use, and which exercise you were in.
