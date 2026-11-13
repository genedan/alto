---
title: Testing, quality and release
parent: guide
order: 11
permalink: /guide/quality/
---
This chapter is about how Alto stays correct as it changes: what the tests are, how the automated checks fit together, how
the documentation is kept honest, and how to release a version. The commands are collected in
[Getting oriented]({{ '/guide/orientation/' | relative_url }}) and [For developers]({{ '/development/' | relative_url }}); here
is the reasoning.

## The safety net, in layers

| Layer | Catches | Where | When it runs |
|---|---|---|---|
| **Doctests** | a docstring example that no longer matches the code | every `>>>` line under `alto/` | with `pytest` |
| **Unit and widget tests** | wrong behaviour | `tests/` | with `pytest` |
| **Docstring check** | missing or incomplete documentation | `tests/test_docstrings.py` | with `pytest` |
| **Docs checks** | a screenshot or API page out of date | `tests/test_docs.py`, `tests/test_api_docs.py`, `scripts/check-docs.sh` | with `pytest`, and on push |
| **Ruff** | style, unused code, import order, many bugs | `ruff format`, `ruff check` | on commit, in CI |
| **Pyright** | type errors | `scripts/typecheck.sh` | on push, in CI |
| **PyCharm inspections** | more type and style warnings | the IDE | while you edit |
| **CI** | all of the above on a clean machine and on every supported Python | `.github/workflows/` | on every pull request |

A change is done when every layer is green. None of them needs a person to remember anything.

## The tests

`pytest` is configured in `pyproject.toml`: it looks in `tests/` and `alto/`, and runs docstring examples as tests
(`--doctest-modules`), ignoring differences in whitespace and allowing `...` as a wildcard in expected output. A run takes about
a minute and covers every line of `alto/`.

### Layout

One file per area: `test_theory.py`, `test_exercises.py`, `test_learning.py`, `test_database.py`, `test_exercise_view.py`,
`test_main_window.py`, `test_settings_panels.py`, `test_rendering.py` (every widget draws something) and so on. A test function
is named as a sentence for what should be true (`test_a_wrong_note_is_shown_then_cleared_for_another_try`), so a failing name
tells you what broke. Each test has a docstring that begins "Check that ...".

### Fixtures

Two `conftest.py` files set the stage.

- **The root `conftest.py`** serves the doctests: it points the settings and data folders at a temporary directory (so an example
  that saves a setting cannot touch yours), gives every doctest a `QApplication` as `app`, and, when the run ends, deletes
  leftover widgets so Python's exit does not crash (see [Pitfalls]({{ '/guide/pitfalls/' | relative_url }})).
- **`tests/conftest.py`** serves the tests: the same isolation, a session-wide `app` fixture, and an automatic fixture that, around
  every test, resets the exercise settings to their defaults, resets the keyboard and notation styles, clears the saved settings,
  turns sound off, closes every window and closes every database a test left open. That is why tests do not affect each other:
  each starts from the same state. `practised_learner` builds a learner with months of made-up answers for tests that need
  history.

### What to test

- **Pure logic** (theory, scheduler, statistics): plain functions with plain asserts; use a seeded `random.Random`.
- **Exercises:** the generation tests in `tests/test_exercises.py`, which loop over the whole registry.
- **Widgets:** build it, `show()` it, act on it with `QTest`, assert on state and on signals. Widgets are drawn into memory on the
  offscreen platform, so you can also check a drawing: `widget.grab().toImage()` and look at pixels (`tests/test_rendering.py`
  counts dark pixels to prove something was drawn).
- **Things with side effects** (audio, dialogs, saved settings): replace them with a recorder, using `monkeypatch`. Tests never
  play a sound or open a real dialog.

### Writing a test well

1. Write it so that it fails first. A test that has never failed has not been shown to test anything.
2. One reason to fail. If it asserts five unrelated things, you cannot tell which broke.
3. Seed every random source. A flaky test teaches people to ignore red.
4. Do not test private details if a public behaviour says the same thing. The exceptions are private helpers that are hard to
   reach through the public interface (the animations' final states, for example).
5. Keep durations short: `QTest.qWait` costs real time.

### Coverage

`pytest --cov --cov-report=term-missing` prints the lines the tests never ran. Alto aims for every line, so a pull request that adds
code should add its tests. Coverage measures what was *executed*, not whether the assertions are good, so treat the number as
a floor, not a goal. Codecov displays it on pull requests but, by design, does not block them (`codecov.yml`).

## The automated checks

### Ruff

Ruff is a linter (it finds problems) and a formatter (it lays code out). It replaces several older tools (pycodestyle, pyflakes,
isort, pyupgrade, flake8 plugins). The rules enabled in `pyproject.toml` are named in groups by their letter prefixes, and each
has a comment saying why: `E`/`W` style, `F` unused names and similar, `I` import order, `UP` outdated syntax, `B` likely bugs,
`D` docstrings, `ANN` annotations, `TID252` no relative imports, `PLC0415` no imports inside functions, `PLR0917` only the first
argument positional, and several more. To see what a rule means, look up its code in the Ruff documentation, or run
`ruff rule <CODE>`.

### Pyright

Pyright reads the type hints and reports contradictions. It is run through `scripts/typecheck.sh` so it uses the project's
virtual environment and can read PySide6's type information. Basic mode, as if for Python 3.11. Tests have two optional-access
checks relaxed (in `pyproject.toml`), because tests deliberately assert on widgets that the application keeps optional.

### pre-commit

`.pre-commit-config.yaml` installs hooks into Git. On **commit**: trailing whitespace, final newline, YAML and TOML validity,
large files, `ruff format`, `ruff check --fix`. On **push**: the whole test suite, the docs freshness check (a warning only) and
Pyright. If a hook changes a file the commit stops so you can look; commit again.

### Continuous integration

GitHub Actions workflows in `.github/workflows/` run on every pull request and every push to `main`:

- **`tests.yml`** runs the suite on every Python version that has not reached end of life (a matrix, currently 3.11 to 3.15). When a
  version stops being supported, drop it here and in `pyproject.toml`.
- **`pyright.yml`** runs Pyright.
- **`codecov.yml`** runs the tests with coverage and uploads the report. It needs a repository secret, `CODECOV_TOKEN`.

The workflows install a few system libraries (`libegl1`, `libxkbcommon0` and others) because Qt's offscreen platform needs them
even though nothing appears on screen. If CI fails on a missing library with a message about `libGL` or `xcb`, that list is where
to look.

## Keeping the documentation true

Two things generate documentation, and tests insist they are current.

- **Screenshots** (`docs/assets/img/`) come from `scripts/screenshots.py`, which runs the real program against a made-up profile and
  a temporary settings folder, in both themes. `tests/test_docs.py` checks every picture a page shows exists in both. The pre-push
  hook runs `scripts/check-docs.sh`, which only *warns* when `alto/ui` has changed since the pictures were made. Look at the pictures
  after regenerating: fonts render slightly differently on each machine, so regenerate on the one you normally use.
- **The API reference** (`docs/api/`) is generated by `scripts/api_docs.py` from the docstrings, and `tests/test_api_docs.py` fails if
  it is stale.

The docs site itself is Jekyll, served by GitHub Pages from the `docs/` folder. To preview it locally you need Ruby and the
`github-pages` gem, which is outside the Python toolchain; most changes can be checked by reading the Markdown and the layout in
`docs/_layouts/`.

## Releasing a version

Alto is installed from source today. When you want to cut a release:

1. **Decide the version** (`version` in `pyproject.toml`). Use *semantic versioning*: `MAJOR.MINOR.PATCH`. Bump PATCH for fixes, MINOR for
   new features, MAJOR for changes that break users. For a program with a database, a change that needs a schema migration is at least
   MINOR.
2. **Make sure the checks pass on a clean checkout**, in CI, on all Python versions.
3. **Migrations.** If the database changed, confirm the migration works on a copy of a real older database, and say in the notes to
   copy `alto.db` first.
4. **Regenerate** screenshots and the API pages, and check [Your data]({{ '/data/' | relative_url }}) is still true.
5. **Update the licence notices** in `THIRD_PARTY_NOTICES.md` if you added fonts or recordings, and check their licences allow
   redistribution.
6. **Build** the package: `python -m pip install build` then `python -m build` produces a source distribution and a wheel in `dist/`.
   Open the wheel (it is a zip) and check that the fonts and recordings are inside; `pyproject.toml` lists them under
   `package-data`.
7. **Tag** the commit (`git tag v0.2.0`, `git push --tags`) and write release notes: what changed for users, in plain words.
8. **Publish** if you want to: PyPI via `twine upload dist/*`, or attach the files to a GitHub release. A GUI program is also often
   distributed as a standalone application (see "Packaging" in the reading list); that is a separate project.

## Words to search for

*Unit test, integration test, end-to-end test.* *Test double: fake, stub, mock, spy.* *Fixture.* *Flaky test.* *Property-based
testing* (the `hypothesis` library, which would suit the theory code). *Mutation testing.* *Continuous integration.* *Semantic
versioning.* *Linter, formatter, static analysis, type checker.* *Wheel and sdist.* *Reproducible build.* *Changelog.*

## Further reading

- Brian Okken, *Python Testing with pytest*, 2nd ed. (Pragmatic Bookshelf, 2022).
- Kent Beck, *Test-Driven Development: By Example* (Addison-Wesley, 2002): the method of writing the failing test first.
- Michael C. Feathers, *Working Effectively with Legacy Code* (Prentice Hall, 2004): how to put tests around code that has none.
- Gerard Meszaros, *xUnit Test Patterns* (Addison-Wesley, 2007): the vocabulary of test doubles (fake, stub, mock, spy).
- Jez Humble and David Farley, *Continuous Delivery* (Addison-Wesley, 2010): why every change goes through the same automated checks.
- Tom Preston-Werner (and the community), *Semantic Versioning 2.0.0*, semver.org: the specification.
- The pytest documentation, docs.pytest.org: fixtures, `monkeypatch` and parametrisation.
- Python Packaging Authority, *Python Packaging User Guide*, packaging.python.org: building and publishing wheels and `pyproject.toml`.
- The Ruff documentation, docs.astral.sh/ruff, and the Pyright documentation, microsoft.github.io/pyright.
- The Qt documentation, "Qt Test Overview", doc.qt.io: the tools behind `QTest` and `QSignalSpy`.
