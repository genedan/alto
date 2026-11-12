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

## Pre-commit

A [pre-commit](https://pre-commit.com/) configuration runs the checks automatically before each commit. Set it up once:

```bash
pip install -e ".[dev]"
pre-commit install
```

It then trims trailing whitespace, makes sure files end with a newline, checks YAML and TOML files, refuses very large
files (the bundled recordings and fonts are exempt) and runs Ruff, applying its safe fixes. If a hook changes a file,
the commit stops so you can review the change, then commit again.

The test suite runs when you **push**, not on every commit, so commits stay quick. A failing test stops the push.
Run the commit checks by hand with `pre-commit run --all-files`, the push check with
`pre-commit run pytest --hook-stage pre-push`, and update the pinned hook versions with `pre-commit autoupdate`.

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

## Adding a notation font

Alto draws notes with fonts that follow the [SMuFL](https://www.smufl.org/) standard.

1. Put the font file and its licence in `alto/assets/fonts/`.
2. Add its stem anchors and engraving defaults to `engraving.json`, read from the font's SMuFL metadata file.
3. Register the file name in `_FILES` in `alto/ui/engraving.py`.
4. Add a `NotationStyle` to `STYLES` in `alto/ui/notation.py`.
5. Record the font in `THIRD_PARTY_NOTICES.md`.

Only add fonts whose licence allows redistribution, such as the SIL Open Font License.

## Reporting problems

Open an issue on [GitHub](https://github.com/genedan/alto/issues). Say which operating system and Python version you
use, and which exercise you were in.
