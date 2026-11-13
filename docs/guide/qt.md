---
title: Qt and PySide6
parent: guide
order: 3
permalink: /guide/qt/
---
Qt is a C++ toolkit for building desktop programs, and **PySide6** is the official Python binding to it (it is "Qt for
Python", maintained by The Qt Company). Alto's interface is entirely PySide6. This chapter covers the ideas you need to read
and change `alto/ui/`, and the traps that bite people who know Python but not Qt.

Qt's own documentation (doc.qt.io) is written for C++, but it is accurate for Python: every class and method has the same
name, and the Qt for Python site (doc.qt.io/qtforpython-6) has the Python signatures. When this chapter says "see QPainter",
look it up there.

## The event loop

A graphical program is not a script that runs top to bottom. It starts, builds its windows, and then calls `app.exec()`, which
runs the **event loop**: a loop that waits for something to happen (a click, a key press, a timer firing, a window needing to
be redrawn), then calls the code that handles it, then waits again. Everything in Alto happens inside handlers called by that
loop.

```python
app = QApplication(sys.argv)  # exactly one per program
window = MainWindow(learner)
window.show()
return app.exec()  # does not return until the last window closes
```

The most important rule follows directly: **never block the event loop.** While your handler runs, the window cannot repaint
or respond. A `time.sleep(2)` in a click handler freezes the whole program for two seconds. To do something later, use a
timer (`QTimer.singleShot(ms, callback)`); to do something over time, use an animation (see
[Animation]({{ '/guide/animation/' | relative_url }})). Alto does all its work in the one thread, and none of it is slow
enough to need more. (If you ever add something heavy, read about `QThread` and `QRunnable` first. Touching a widget from
another thread is not allowed.)

There is one `QApplication`, and `QApplication.instance()` returns it (or `None` if none exists). Tests create one through a
fixture, because widgets cannot exist without it.

## Widgets, layouts and size

A **widget** (`QWidget`) is a rectangle on screen that can draw itself and receive input. Buttons, labels and lists are
widgets, and so are Alto's `StaffWidget` and `KeyboardWidget`. Widgets nest: a widget made with a `parent` lives inside it.

You rarely set positions yourself. A **layout** (`QVBoxLayout`, `QHBoxLayout`, `QGridLayout`) arranges child widgets and
resizes them as the window changes. Each widget tells its layout how big it would like to be (`sizeHint()`) and how it may
stretch (its *size policy*). If a custom widget has the wrong size, the answer is usually its `sizeHint` or `setFixedSize`.

Custom positioning, as in `SlideStack`, sets `geometry` directly; that is the exception, and it is done with care.

## Signals and slots

A **signal** is an announcement that something happened; a **slot** is any callable that wants to hear about it. You connect
them:

```python
button.clicked.connect(self.next_question)  # call this method when clicked
self.settings_panel.changed.connect(self.next_question)
```

You can define your own signals on a class that inherits `QObject` (every widget does):

```python
class StaffInput(StaffWidget):
    placed = Signal(object)  # the note that was clicked
    accidental_cycled = Signal()
```

and `self.placed.emit(note)` sends it. This is how Alto keeps parts independent: the settings panel does not know about the
exercise screen, it only emits `changed`, and the screen decides what to do. The tests use `QSignalSpy` to watch a signal.

A trap with `lambda` slots: they capture variables late. See the closures section of
[Python beyond the basics]({{ '/guide/python/' | relative_url }}).

## Who owns an object, and when it is deleted

This is the most common source of mysterious crashes. A Qt object is really a C++ object with a Python wrapper. Two
different mechanisms decide its life.

- **Parent ownership.** A widget created with a parent (or placed in a layout that has one) is owned by it. When the parent is
  deleted, its children are deleted. The Python wrapper may stay around, but pointing at a dead object.
- **Python references.** A widget with **no parent** is owned by Python, and is destroyed when the last Python reference goes.

Consequences you will hit:

- `QLabel("hi").show()` in one expression shows nothing for long: the label has no other reference, so it is deleted at once.
  Keep it in a variable. This bit the doctests more than once.
- An **animation** or **timer** with no reference may be collected mid-run. Alto passes `self` as its parent (`QVariantAnimation(self)`)
  and often also keeps a list of live animations (`self._anims`).
- `widget.deleteLater()` schedules deletion for when control returns to the event loop. Deleting a widget while one of its own
  handlers is running can crash. In tests, `QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)` runs the pending
  deletions.
- Methods that return an object may return `None` (`layout()`, `widget()`, `QApplication.instance()`). Pyright makes you check.

## Painting

A widget draws itself in its **`paintEvent`** method, which Qt calls whenever the widget must be redrawn. You create a
`QPainter` on the widget and issue drawing commands.

```python
def paintEvent(self, _: QPaintEvent) -> None:
    p = QPainter(self)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)  # smooth edges
    p.setPen(QPen(color, 1.5))  # outlines
    p.setBrush(QBrush(fill))  # fills
    p.drawLine(QPointF(0, 10), QPointF(100, 10))
    p.drawPath(path)
```

Rules that explain most drawing bugs:

- **Never draw outside `paintEvent`.** To change the picture, change state and call `self.update()`, which asks Qt to schedule a
  repaint. `repaint()` draws immediately and is rarely right.
- A painter must finish before its device goes away. `p.end()` finishes it (it returns `True`, which a doctest then prints).
  Painting on a temporary object (`QPainter(QImage(...))`) crashes, because Python frees the image under the painter. Keep
  the image in a variable.
- **Coordinates**: the origin is the top left, `y` grows downward. The same drawing code can be moved or scaled with a
  `QTransform`. `p.save()` and `p.restore()` bracket changes to pen, brush and transform so one drawing step does not leak into
  the next.
- **Pixels are not pixels.** On a high-resolution screen Qt works in *logical* pixels and multiplies by the **device pixel
  ratio** (often 2 or 3) at the end, so a 10-pixel line is crisp at any density. To make an image look sharp, render it at
  twice the size and call `setDevicePixelRatio(2)`; `alto/ui/icons.py` does this.
- Floats matter. Use `QPointF` and `QRectF`, not `QPoint` and `QRect`, when positions are fractional; integers round and
  make lines wobble.
- `QPainterPath` describes a shape (lines and curves) that you can fill, stroke, transform, measure and hit-test. It is how
  Alto draws musical symbols. See [Rendering music notation]({{ '/guide/notation/' | relative_url }}).

The whole system is documented under "Paint System" in the Qt documentation.

## Models and views

A list or table in Qt separates the **model** (the data) from the **view** (the widget that shows it). The model answers
questions like "what is the text of row 3, column 1?" and the view asks. Alto's database browser (`alto/ui/database_page.py`)
defines `RowsModel`, a small `QAbstractTableModel`, and puts a `QSortFilterProxyModel` between the model and the table to give
sorting and searching for free. The idea, called **Model-View-Controller** in the wider world, is worth knowing even if you
never write another model.

## Saved settings

`QSettings` stores values by key in the operating system's usual place (an INI file on Linux, the registry on Windows, a
property list on macOS). Alto wraps it in `alto/ui/store.py`: `store()` returns the one `QSettings("alto", "alto")`, and
`int_value` and `text_value` read a value as the right type, because `QSettings` may hand back a string where you stored a
number. Exercise settings are saved by the `save_*` functions in `settings_panel.py`. Nothing saves the plain settings
objects in `alto/settings.py`.

Tests point the settings at a throwaway folder (the `XDG_CONFIG_HOME` variable on Linux), so no test can change your real
settings.

## Timers and the passage of time

`QTimer.singleShot(150, callback)` calls `callback` after 150 ms. A `QTimer(self)` object with `setSingleShot(True)` can be
started, stopped and restarted, which is how the exercise screen cancels the delay before the next question when the user
moves on. Timers run in the event loop, so they are as accurate as the loop is free; do not expect better than a few
milliseconds.

## Testing widgets

Use `QTest` (in `PySide6.QtTest`) to act like a user: `QTest.mouseClick(widget, Qt.MouseButton.LeftButton)`, `button.click()`,
`QTest.keyClick(widget, Qt.Key.Key_1)`. `QTest.qWait(300)` runs the event loop for 300 ms, which lets animations and timers
progress. A widget that has not been shown gets no resize or paint events, so `show()` it (the offscreen platform makes this
safe) before testing anything about its size.

## Enums, the full form

PySide6 lets you write `Qt.AlignLeft` as well as `Qt.AlignmentFlag.AlignLeft`, but Pyright can only see the second. Alto
writes the full form everywhere.

## Known problems with the library

`pyproject.toml` excludes PySide6 6.12.0 on Python 3.11: that release drops a reference to `None` on every call that returns
nothing, and enough painting aborts the interpreter. If you ever upgrade PySide6 and the program crashes after a while with no
traceback, suspect the library, and run with `python -X faulthandler`.

## Words to search for

*QObject* (the root of Qt's object tree), *the meta-object system* (how signals work), *Graphics View* (a framework for many
movable items; Alto draws by hand instead, which is simpler for a fixed diagram), *QML* and *Qt Quick* (the other way to build
Qt programs, declarative and GPU-based; not used here), *HiDPI*, *platform plugin* (`xcb`, `wayland`, `cocoa`, `windows`,
`offscreen`), *accessibility* (Qt supports screen readers; Alto does not yet do much).

## Further reading

- The Qt documentation, doc.qt.io/qt-6 and doc.qt.io/qtforpython-6: start with "Signals & Slots", "The Event System",
  "Layout Management", "Paint System", "High DPI" and "Model/View Programming".
- Jasmin Blanchette and Mark Summerfield, *C++ GUI Programming with Qt 4*, 2nd ed. (Prentice Hall, 2008). Written for an older
  Qt and for C++, but its explanation of layouts, painting and the event system is still the clearest book-length account.
- Mark Summerfield, *Rapid GUI Programming with Python and Qt* (Prentice Hall, 2007): the same ideas in Python, for PyQt4.
- Guillaume Lazar and Robin Penea, *Mastering Qt 5*, 2nd ed. (Packt, 2018): architecture of a larger application.
- Erich Gamma, Richard Helm, Ralph Johnson and John Vlissides, *Design Patterns* (Addison-Wesley, 1994): the observer pattern
  is what signals and slots are, and MVC's origins are described there.
