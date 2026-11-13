---
title: Pitfalls and debugging
parent: guide
order: 12
permalink: /guide/pitfalls/
---
This is the chapter to open when something strange happens. Each entry below is a mistake that was actually made while building
Alto, with the symptom you will see, the cause, and the fix. After them come the tools for finding a problem you do not recognise.

## Qt objects and their lifetimes

**Symptom: a widget you created never appears, or a doctest that builds a widget in one line gives nothing.**
`QLabel("hi").show()` creates a widget with no parent and no Python variable. Python frees it immediately, and Qt deletes it.
*Fix:* keep it in a variable (`label = QLabel("hi")`), or give it a parent.

**Symptom: the program crashes (a segmentation fault, with no Python traceback) when painting onto an image.**
`QPainter(QImage(...))` paints on a temporary. Python frees the image while the painter still uses it. *Fix:* put the image in a
variable and keep it alive until after `p.end()`.

**Symptom: `RuntimeError: Internal C++ object (...) already deleted`.**
You kept a Python reference to a widget whose C++ side has been deleted, because its parent was deleted or `deleteLater()` ran.
*Fix:* do not use a widget after you closed it; clear your reference when you delete it; check `shiboken6.isValid(obj)` if you
must.

**Symptom: an animation or timer you started simply stops.**
It was garbage collected. *Fix:* give it a parent (`QVariantAnimation(self)`), or store it (`self._anim = ...`). See
[Animation]({{ '/guide/animation/' | relative_url }}).

**Symptom: a doctest prints `True` where you did not expect output.**
`QPainter.end()` returns `True`, and an interactive session prints return values. *Fix:* write the `True` in the expected output
or assign the result (`_ = p.end()`).

**Symptom: a widget's size is wrong in a test, or a resize handler never runs.**
Qt does not send resize events to a widget that has not been shown. *Fix:* call `widget.show()`; on the offscreen platform nothing
appears.

## A test run that passes but exits with an error

**Symptom:** every test reports "passed", and then the process dies with a signal: exit status 139 (segmentation fault), 135 (bus
error) or `-7`, and a message such as `pure virtual method called` or `terminate called without an active exception`. Because
the exit status is non-zero, the pre-push hook fails.

**Cause:** the doctests create hundreds of widgets they never close. When Python exits it destroys the last objects in whatever
order, and Qt's destruction of widgets after the `QApplication` has gone aborts.

**Fix:** the root `conftest.py` has a `pytest_sessionfinish` hook that closes and deletes every widget and runs the garbage collector
while Python and Qt are both still alive. If the symptom returns, a new kind of object is probably outliving the application;
look at what the last test created. Run `python -X faulthandler -m pytest` to see where it dies.

Always check the exit status, not just the summary line: `pytest -q; echo $?`.

## Sound in tests

**Symptom: a test makes noise, or fails on a machine with no audio.**
It submitted a right answer, which plays a sound. *Fix:* the test fixtures turn `sounds.enabled` off for every test. A *doctest* that
submits an answer must set `sounds.enabled = False` and restore it afterwards.

## Imports

**Symptom: `NameError` for a name that Pyright says is fine.**
The name is imported under `if TYPE_CHECKING:` but used at run time. Pyright sees the import and is satisfied; Python skips the
block. *Fix:* import it normally, above the guard.

**Symptom: `ImportError: cannot import name ... (most likely due to a circular import)`.**
Two modules import each other. *Fix:* do not move the import into a function (Ruff forbids it). Break the cycle: move the shared
piece to a third module, or have one module register a callback with the other, as `notation.on_redraw` does for the staff.

**Symptom: Ruff reports `E402` in a `conftest.py`.**
The settings folders must be redirected before anything from Alto is imported, so those imports come after code. Mark each with
`# noqa: E402`, on the first line of the statement.

## Tools that disagree

**Pyright is satisfied and PyCharm warns about `str(settings.value(...))`, or the reverse.** The two infer types differently.
Alto has helpers (`text_value`, `int_value`) so that neither complains. Where one tool is simply wrong, silence it narrowly and
say why: `# pyright: ignore[rule]`, `# noqa: CODE`, `# noinspection Name`.

**Pyright loses a type through `@cache`.** A cached function's signature can be hidden from the checker. *Fix:* give the wrapper
an explicit annotation, or add a `cast`.

**`ruff check` and `ruff format` undo each other.** Run them in order: `ruff format .` then `ruff check --fix .`. In the other order
the trailing-comma rule (`COM812`) and the formatter fight.

**Ruff says `PLR0917` on a call or a definition.** Only the first parameter may be positional. Add `*,` after the first parameter and
name the arguments at the call. In a fake that Qt calls positionally, add `# noqa: PLR0917` with the reason.

## PySide6 and Qt

**Symptom: a program that ran fine for a while aborts with no traceback after a lot of painting, on Python 3.11.**
PySide6 6.12.0 has a reference-counting bug on that Python. `pyproject.toml` excludes it. If you change the PySide6 requirement,
test a long session.

**Symptom: a setting you saved as a number comes back as a string.**
`QSettings` gives back whatever it finds. Read with `int_value` or `text_value`; store booleans as `"true"` and `"false"`.

**Symptom: `str.format` raises `KeyError` or `IndexError` when you edit the style sheet.**
`app_style` fills a template with `.format`, so every literal `{` and `}` of CSS is doubled in the template. A new rule needs doubled
braces.

**Symptom: a lambda connected in a loop always uses the last value.**
Late binding. *Fix:* capture the value as a default argument: `lambda _=False, k=key: self.show(k)`.

**Symptom: the first note of a sequence is missing.**
`QSoundEffect` loads in the background, and a note played before it is ready is silent. `Sounds._play_sequence` waits (for up
to a second) for loading. Anything new that plays a sound should do the same, or play something already loaded.

**Symptom: the screenshots differ after regenerating.**
Fonts render slightly differently on each machine and each version of the platform libraries. Regenerate on the machine you normally
use, look at the pictures, and commit only intended changes.

## The docs site

**Symptom: a page on the website is blank, or shows Liquid errors, after adding a code sample.**
Jekyll runs the Liquid template language over every page, and two opening curly braces in a row, or an opening brace followed by a percent sign, in a code block is taken
as template code. *Fix:* wrap the page or the block in `raw` and `endraw` tags, as the generated API pages do, or avoid the braces.

**Symptom: `tests/test_api_docs.py` fails.** The generated API pages are out of date. Run `python scripts/api_docs.py` and commit the
result.

## Finding a problem you do not recognise

### Reproduce it small

Almost every bug becomes obvious when reduced. Write a ten-line script that builds only the widget in question and draws it:

```python
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication

app = QApplication([])
w = SomeWidget()
w.resize(400, 300)
w.show()
w.grab().save("/tmp/w.png")  # then look at the image
```

If the bug appears, you have a test: put the script's assertions in `tests/`.

### Tools

| Need | Tool |
|---|---|
| A crash with no Python traceback | `python -X faulthandler`, which prints the Python stack on a fatal signal. For C-level detail, run under `gdb`. |
| Which tests fail, fast | `pytest -x -q` (stop at the first failure), `-k word` (only matching tests), `-s` (show prints), `--pdb` (debugger on failure). |
| What a widget looks like | `widget.grab().save("/tmp/x.png")`, then open the file. |
| What Qt is doing at start-up | `QT_DEBUG_PLUGINS=1 python -m alto` (platform plugin problems); `QT_LOGGING_RULES="*.debug=true"`. |
| Every widget alive | `QApplication.allWidgets()`; for one widget's children, `widget.findChildren(QPushButton)`. |
| Slow code | `python -m cProfile -s cumtime script.py`; for paint speed, `QElapsedTimer` around the drawing. |
| Memory growth | the standard library's `tracemalloc`. |
| A signal that never fires | `QSignalSpy(widget.someSignal)`, then `spy.count()`. |
| Why a test passed alone and fails with the others | a shared singleton changed state. Check `tests/conftest.py` resets it. |

A caution about debuggers: `pdb` and an IDE's breakpoints work in a Qt program, but stopping in the middle of a handler freezes the
event loop and the windows. That is expected. Do not stop inside a `paintEvent` while the window is repainting; use prints, or save
an image and stop afterwards.

### Questions to ask

1. Is it the *data* (the wrong `Question`), the *drawing* (the right data drawn wrongly), the *flow* (the right thing drawn at the
   wrong time) or the *environment* (a font, a platform, a library version)? Print the `Question` first.
2. What changed? `git bisect` finds the commit that broke it, using your test as the judge.
3. Does it happen with default settings and a fresh profile? Start with `XDG_CONFIG_HOME` and `XDG_DATA_HOME` pointing at an empty
   folder (as the tests do) to rule out stale saved state.

## Words to search for

*Segmentation fault, core dump, faulthandler.* *Garbage collection, reference counting, object lifetime, ownership.* *Late binding,
closure.* *Circular import.* *Flaky test, test isolation, global state.* *Bisecting.* *Race condition.* *Event loop starvation.*

## Further reading

- Andreas Zeller, *Why Programs Fail: A Guide to Systematic Debugging*, 2nd ed. (Morgan Kaufmann, 2009): the scientific method
  applied to bugs, including bisecting and reducing a failure.
- Andrew Hunt and David Thomas, *The Pragmatic Programmer*, 20th anniversary ed. (Addison-Wesley, 2019): the chapter on debugging.
- Python Software Foundation, the `faulthandler`, `pdb`, `cProfile` and `tracemalloc` pages in *The Python Standard Library*,
  docs.python.org.
- The Qt documentation, "Object Trees and Ownership", "Debugging Techniques" and "Environment Variables Recognized by Qt",
  doc.qt.io.
- The Qt for Python documentation, "Shiboken" and the pages on object ownership, doc.qt.io/qtforpython-6.
- Scott Chacon and Ben Straub, *Pro Git* (Apress, 2014; free at git-scm.com/book), the section on `git bisect`.
