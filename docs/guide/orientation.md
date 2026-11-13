---
title: Getting oriented
parent: guide
order: 1
permalink: /guide/orientation/
---
This chapter gets you from a fresh clone to a working change: setting up, finding your way around the code, and the rules the
project follows. Those rules are collected here on purpose. They are the same ones enforced by Ruff, Pyright and the tests,
and writing them down means you can follow them without remembering them.

## Set up

You need Python 3.11 or newer. Alto supports every Python version that has not reached end of life (see the matrix in
`.github/workflows/tests.yml`), so do not use syntax newer than 3.11.

```bash
git clone https://github.com/genedan/alto.git
cd alto
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pre-commit install
.venv/bin/python -m alto            # run the app
.venv/bin/pytest                    # run every test and every docstring example
```

On Windows the programs are in `.venv\Scripts\` instead of `.venv/bin/`.

Three things in that list deserve a sentence each.

- **`-e` (editable install).** Python installs the project as a link to the folder you are working in, not a copy, so edits
  take effect without reinstalling. It also makes `import alto` work from anywhere, which the tests and scripts rely on.
  `pip install -e` reads `pyproject.toml`, which is where the dependencies, the entry point (`alto = "alto.__main__:main"`)
  and the tool settings live.
- **`[dev]`** is an optional dependency group in `pyproject.toml`: pytest, coverage, Ruff, Pyright and pre-commit.
- **`pre-commit install`** installs two Git hooks: quick checks on every commit, and the full test suite and type check on every
  push. Nothing reaches the remote with a failing test.

If the program starts but the notation looks odd, see [Rendering music notation]({{ '/guide/notation/' | relative_url }}). The
default style, Finale Maestro, and the other SMuFL styles use fonts bundled with the program. Only the "Noto Music" style needs
a font from your system.

### Running without a screen

All the tests, and the screenshot script, run on Qt's *offscreen platform*, which draws into memory. Set
`QT_QPA_PLATFORM=offscreen` and nothing opens on screen. The test configuration sets it for you. It is how continuous
integration runs the tests on a machine with no display, and it is how you can draw a widget to a PNG in a script.

## A tour of the repository

```
alto/                  the program
    __main__.py        starts the app: python -m alto
    audio.py           samples, pitch shifting, the piano synthesiser, playback
    instrument_info.py facts about each instrument's recordings
    settings.py        the user's choices as plain objects (no saving)
    theory/            notes, intervals, scales, chords
    exercises/         Exercise and Question, and the eight exercises
    learning/          profiles, SQLite, the scheduler, the statistics
    ui/                everything that needs Qt
    assets/            fonts, instrument recordings, icons (ship with the package)
tests/                 the tests, one file per area
docs/                  this website (Jekyll, published to GitHub Pages)
    api/               generated API reference (do not edit by hand)
    guide/             this guide
scripts/               screenshots.py, api_docs.py, typecheck.sh, check-docs.sh, run-tests.sh
ARCHITECTURE.md        a one-page map of how the pieces fit
pyproject.toml         dependencies, entry point, pytest, Ruff, Pyright and coverage settings
.pre-commit-config.yaml   the checks run on commit and on push
.github/workflows/     continuous integration: tests, Pyright, coverage
```

`alto/ui/` is large because drawing is verbose. The biggest files are `settings_panel.py` (the sliding settings panes for
every exercise), `charts.py`, `pictures.py` (the small illustrations in the settings), `staff.py`, `keyboard.py` and
`exercise_view.py`. You will rarely need to read any of them from top to bottom. Read one class, and use its docstring.

### The files to read first

If you read only five files, read these, in this order.

1. `alto/exercises/base.py`: `Question`, `Exercise` and `register`. Everything revolves around them.
2. `alto/exercises/library.py`: one real exercise, `NoteNames`, to see how a `Question` is made.
3. `alto/learning/scheduler.py`: forty lines of arithmetic that decide what is asked next.
4. `alto/learning/learner.py`: how a question is chosen and an answer recorded.
5. `alto/ui/exercise_view.py`: `next_question`, `submit` and `_record`, the loop the user lives in.

## Learn the code by running it

Every docstring has an `Examples` section, and `pytest` runs it. That makes the docstrings a guided tour you can execute:

```bash
.venv/bin/python
>>> from alto.theory.pitch import Note, Interval
>>> Note.parse("C4").transpose(Interval.parse("M3"))
```

The examples in `alto/ui/` create real widgets, because the root `conftest.py` gives every example a `QApplication` called
`app`. Copy one into a script, add `widget.show()` and `app.exec()` and you have a window. To draw a widget to a file:

```python
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from alto.ui.staff import StaffWidget

app = QApplication([])
staff = StaffWidget()
staff.resize(400, 200)
staff.grab().save("/tmp/staff.png")  # grab() renders the widget into a pixmap
```

This is the quickest feedback loop for drawing work: change a number, save the picture, look at it.

## The rules

These are enforced by tools wherever a tool can do it. Where none can, they are marked.

### Layout

- Lines are at most 130 characters. Strings use double quotes.
- Anything with several elements that does not fit on a line (a list, dictionary, tuple, call or signature) goes **one element
  per line with a trailing comma**. A trailing comma you write yourself keeps even a short list exploded; that is how you ask
  for one-per-line. Function definitions with two or more parameters, and calls, collections and tuples with four or more
  elements, are written one per line. Short calls stay on one line.
- Run the formatter and then the linter, in this order: `ruff format .` then `ruff check --fix .`. The formatter splits long
  lines, and the linter adds the trailing commas it leaves out. In the other order they fight each other.

### Arguments

- **Only the first parameter of a function may be positional.** The rest are keyword-only (written after a bare `*`), and every
  call names them: `Note(3, letter=1)`, not `Note(3, 1)`. Ruff enforces it (`PLR0917`). Calls then read as sentences, and
  adding a parameter later cannot silently change what an existing call means.
- Tests that stand in for Qt functions, which Qt calls positionally, may need `# noqa: PLR0917` with a reason. Test functions
  receive pytest fixtures as plain parameters, which is allowed.

### Imports

- **Absolute only.** `from alto.ui.store import store`, never `from .store import store` (`TID252`).
- **All at the top of the file.** None inside a function (`PLC0415`). The `>>>` lines of a docstring example are the one
  exception, because an example has to import what it uses. When two modules need each other, do not import one lazily: move
  the shared thing, or have one register a callback with the other. `alto/ui/notation.py` and `alto/ui/staff.py` do this with
  `on_redraw`.
- **Sorted like isort**, with `alto` as its own section after the third-party packages (`I`).
- **Two or more names from one module: one per line, in parentheses, with a trailing comma.** Ruff cannot enforce this; it only
  keeps an import that is already written this way:

  ```python
  from alto.learning.database import (
      Database,
      ItemRecord,
      Profile,
  )
  ```
- In the two `conftest.py` files the imports that come after the environment setup carry `# noqa: E402`, on the first line of
  the statement. The setup must run before anything from Alto is imported.

### Docstrings and types

- Every module, class, function, method, nested function and test has a **NumPy-style docstring**. The text starts on the line
  after the opening `"""`.
- Describe every parameter with its type, every return and yield, and, with `Raises`, every error the function raises. Add an
  `Examples` section that runs as a doctest. Tests are exempt from `Examples`. `tests/test_docstrings.py` checks all of this
  for every file, including private and nested functions that Ruff skips.
- Every signature is fully annotated, and `Any` is not used: write the real type. Pyright runs in basic mode as if on Python
  3.11 (`sh scripts/typecheck.sh`).
- Use a raw docstring (`r"""`) if it contains a backslash.

### No warnings

There must be no warnings from Ruff, Pyright or PyCharm. Where a tool is wrong, silence it narrowly and say why: `# pyright:
ignore[ruleName]`, `# noqa: CODE`, or `# noinspection InspectionName` for PyCharm (in a doctest, a line `>>> # noinspection
InspectionName` covers the next statement). [For developers]({{ '/development/' | relative_url }}) lists the PyCharm settings a
fresh clone needs.

### Before you commit

```bash
.venv/bin/ruff format .
.venv/bin/ruff check --fix .
sh scripts/typecheck.sh
.venv/bin/pytest
```

If you changed a docstring or a public signature: `python scripts/api_docs.py`. If you changed anything visible:
`python scripts/screenshots.py` and look at the pictures before committing them (fonts render slightly differently on every
machine, so regenerate on the machine you normally use).

### Git

- Work on a branch. Open a pull request into `main`; CI runs the tests on every supported Python version, Pyright, and coverage.
- Commits are yours. Write the message as a short summary line, a blank line, and a paragraph on *why*.
- `pre-commit` may change files and stop the commit. Look at the change, `git add` the files, and commit again.

## What to read next

If you are going to add an exercise, read [Building an exercise]({{ '/guide/exercises/' | relative_url }}). If you are about
to touch the user interface, read [Qt and PySide6]({{ '/guide/qt/' | relative_url }}) first. It will save you from the traps
that are hard to see.

## Further reading

- *Python Packaging User Guide*, packaging.python.org (the Python Packaging Authority): `pyproject.toml`, editable installs and
  virtual environments, from the people who maintain the tools.
- Python Software Foundation, *The Python Tutorial* and *The Python Standard Library*, docs.python.org.
- Pro Git, Scott Chacon and Ben Straub (Apress, 2014; free at git-scm.com/book): the standard book on Git.
- Brian Okken, *Python Testing with pytest*, 2nd ed. (Pragmatic Bookshelf, 2022).
- The Ruff documentation, docs.astral.sh/ruff, for what each rule code means. A rule code such as `PLR0917` is looked up there.
- PEP 8, *Style Guide for Python Code*, and PEP 257, *Docstring Conventions*, at peps.python.org.
