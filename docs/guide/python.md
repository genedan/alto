---
title: Python beyond the basics
parent: guide
order: 2
permalink: /guide/python/
---
Alto uses ordinary Python, but it leans on a handful of features that a first course does not reach. This chapter names each
one, shows where Alto uses it, and says what to read to learn it properly. If a line of code in Alto puzzles you, the cause
is probably here.

## Dataclasses

A **dataclass** is a class whose job is to hold fields. You list the fields with their types and Python writes `__init__`,
`__repr__` and `__eq__` for you.

```python
from dataclasses import dataclass


@dataclass
class Profile:
    id: int
    name: str
```

Alto uses them for `Question`, `Note`, `Instrument`, `NotationStyle`, `KeyboardStyle`, the settings objects and the rows read
from the database. Two options matter:

- `frozen=True` makes instances immutable, so they can be dictionary keys and cannot be changed by accident. `Note` and
  `Profile` are frozen.
- `KW_ONLY` is a marker field. Every field after it must be given by name. `Question("prompt", choices=[...], answer="C")`
  works because `prompt` comes first and `choices` and the rest come after `_: KW_ONLY`. This is how the "only the first
  parameter is positional" rule is applied to data.

*Read:* the `dataclasses` module documentation; PEP 557 (the proposal that introduced them); Luciano Ramalho, *Fluent Python*,
2nd ed. (O'Reilly, 2022), the chapter on data class builders.

## Type hints

A **type hint** says what a value should be: `def pick(self, exercise: Exercise, *, rng: random.Random) -> Question`. Python
ignores them at run time. **Pyright** reads them and reports contradictions before the program runs, and PyCharm uses them for
completion. Alto annotates everything.

Things you will meet:

- `int | None` means "an int or nothing". It replaced `Optional[int]` in Python 3.10. A value of this type must be checked
  before use (`if x is not None:`), and Pyright will insist.
- `list[str]`, `dict[str, int]`, `tuple[int, int]` are the built-in generic types (Python 3.9 and later).
- `from __future__ import annotations` is at the top of nearly every file. It makes annotations plain text that is never
  evaluated at import, so you can mention a class before it is defined and import a name only for typing.
- `if TYPE_CHECKING:` guards imports that exist only for annotations. The block is skipped when the program runs and read when
  Pyright runs. If you use such a name at run time (for example to call it), you get a `NameError`, so the import belongs above
  the guard. It is an easy trap, because Pyright is satisfied either way.
- `Callable[[int], str]` is a function taking an int and returning a str. `Callable[..., int]` is "any arguments".
- `# pyright: ignore[reportAttributeAccessIssue]` silences one specific message on one line. Always add the reason.

*Read:* PEP 484 (type hints), PEP 604 (the `X | Y` syntax), the Python documentation's `typing` module, and the Pyright
documentation (microsoft.github.io/pyright), whose "type concepts" pages are a good short course in the ideas. Ramalho's
*Fluent Python* has two chapters on type hints.

## Keyword-only arguments

```python
def record(self, exercise, *, question, answer, correct): ...
```

Everything after the bare `*` must be given by name. Alto requires this for every parameter after the first, and Ruff checks
it. When you write `Note(4, letter=0)` you can read the call without knowing the signature.

## Abstract base classes and decorators

`Exercise` is an **abstract base class**: it declares `generate` as `@abstractmethod`, so you cannot create an `Exercise`
without writing `generate`. `@register` is a **class decorator**: a function that receives the class you just defined,
records it (in `REGISTRY`), and returns it. The `@` line is shorthand for `MyExercise = register(MyExercise)`.

```python
@register
class NoteNames(Exercise): ...
```

Decorators are everywhere in Python: `@property` (a method read like an attribute), `@staticmethod`, `@cache`,
`@pytest.fixture`. A decorator is a function that takes a function or class and returns a replacement.

*Read:* Ramalho's *Fluent Python*, the chapters on decorators and closures, and on interfaces and abstract base classes.

## Closures

A **closure** is a function defined inside another function that remembers the outer function's variables. Alto uses them
constantly for Qt callbacks, because a callback has to remember something:

```python
def _flash(self, button, *, target):
    end, start = QColor(target), QColor("black")

    def step(t: float) -> None:  # remembers `button`, `start` and `end`
        button.setStyleSheet(self._style(blend(start, b=end, t=t)))

    anim.valueChanged.connect(step)
```

When a lambda is created in a loop, beware **late binding**: `lambda: self.show(i)` looks `i` up when called, not when
created, so every callback sees the last `i`. The fix, used throughout `alto/ui/`, is a default argument that captures the
value now: `lambda _=False, k=key: self.show_table(k)`.

## `functools.cache`

`@cache` memoizes a function: the first call with given arguments computes the result and later calls return the stored one.
`alto/ui/engraving.py` uses it so each glyph outline is built once. Two consequences: arguments must be hashable (immutable),
and Pyright cannot always see through the decorator, so type information is sometimes lost at the call site.

## Random numbers you can repeat

`random.Random(seed)` is a generator with its own state. Alto passes an `rng` argument into every exercise's `generate`, rather
than calling the module-level `random` functions, because a test can then pass `random.Random(1)` and get the same questions
every time. This is called **dependency injection**: the dependency (the random source) is passed in, not reached for.
`Learner.pick` takes an `rng` for the same reason. If you write code that makes random choices, take an `rng` argument.

## Dates and times

The database stores timestamps as seconds since 1970 (`time.time()`), which sort and subtract easily. Durations are measured
with `time.monotonic()`, a clock that never jumps backwards when the system time changes. Use `monotonic` for "how long did
that take" and `time` for "when did that happen".

## Paths

`pathlib.Path` represents file locations: `Path(__file__).parent / "assets" / "fonts"`. The `/` operator joins parts and works
on every operating system. `__file__` is the path of the current source file, which is how the program finds its fonts and
recordings wherever it is installed.

## Testing tools: doctest, fixtures, monkeypatch

- A **doctest** is an example inside a docstring. Lines starting `>>> ` are run, and the line below must match the output.
  pytest runs them with `--doctest-modules`. Two flags are on: `NORMALIZE_WHITESPACE` (ignore differences in spacing) and
  `ELLIPSIS` (`...` matches any text).
- A **fixture** is a function pytest runs to prepare something a test needs. A test asks for it by naming a parameter:
  `def test_x(app, tmp_path)`. `app` is Alto's fixture that provides the `QApplication`; `tmp_path` is pytest's own, a fresh
  empty folder.
- **`monkeypatch`** is a fixture that replaces something for one test and puts it back afterwards:
  `monkeypatch.setattr(sounds, "play_notes", lambda *a, **k: None)`. It is how tests keep the sound off and avoid real
  dialogs. The thing replaced is named by a string, which is why an IDE cannot always check it.
- A **fake** is a small class a test writes to stand in for something real (a `QSoundEffect`, a settings store). Because Qt calls
  fakes positionally, they sometimes need `# noqa: PLR0917`.

*Read:* Okken's *Python Testing with pytest*; the `doctest` and `unittest.mock` pages in the standard library documentation.

## Packaging in one paragraph

`pyproject.toml` is the single description of the project (PEP 621): its name, version, dependencies, the command `alto`,
which files ship with the package (the fonts and recordings), and the settings of every tool. `setuptools` builds it.
`pip install -e .` reads it. When you add a dependency, add it there.

## Words to search for

If you want to go further: *context managers* (`with` statements: used for database transactions and `QPainter` save/restore),
*generators* and `yield` (used by fixtures), *comprehensions*, *the descriptor protocol* (how `@property` works), *the data model*
and *dunder methods* (`__eq__`, `__lt__`: `Note` defines ordering), *structural subtyping* and `Protocol` (PEP 544).

## Further reading

- Luciano Ramalho, *Fluent Python*, 2nd ed. (O'Reilly, 2022): the best single book for the "beyond basics" material above.
- Brett Slatkin, *Effective Python*, 2nd ed. (Addison-Wesley, 2019): short, practical items on closures, decorators and
  typing.
- Python Software Foundation, *The Python Language Reference*, "Data model" chapter, and the `dataclasses`, `typing`,
  `functools`, `pathlib` and `doctest` library pages, at docs.python.org.
- PEP 8, PEP 257, PEP 484, PEP 557, PEP 604, PEP 621, at peps.python.org.
- The numpydoc docstring standard, numpydoc.readthedocs.io (the "format" page): the layout of Alto's docstrings.
