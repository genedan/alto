---
title: alto.ui.main_window
parent: api
package: alto.ui
order: 23
permalink: /api/alto.ui.main_window/
---
{% raw %}
The main window: a menu, the exercise list on the left that can be collapsed, and the page on the right.

The page is the start screen, an exercise, or (while it is open) the statistics or the database browser.

**Examples**

```pycon
>>> window = MainWindow()
>>> window.title_label.text()
'Alto - Music Theory'
```

## MainWindow

```python
MainWindow(learner: Learner | None = None)
```

Bases: `QMainWindow`

The application window.

**Attributes**

- `SIDEBAR_MIN` (*int*): The narrowest the exercise list can be before it collapses, in pixels.
- `SIDEBAR_DEFAULT` (*int*): The list's width the first time.
- `APP_TITLE` (*str*): The title shown on the start screen.
- `learner` (*Learner or None*): Who is practising, and their history; None practises without recording.
- `nav` (*QListWidget*): The exercise list.
- `stack` (*QStackedWidget*): The pages: the start screen, then exercises and the statistics or database while they are open.
- `home` (*HomePage*): The start screen.
- `splitter` (*QSplitter*): Holds the list and the pages, so the list can be dragged narrower or wider.
- `title_label` (*QLabel*): The title in the top bar.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> window = MainWindow()
>>> window.open_exercise(NoteNames)
>>> window.title_label.text()
'Note Identification'
>>> window.show_home()
```

**Constructor**

Build the window and load every saved setting.

**Parameters**

- `learner` (*Learner or None, default None*): Who is practising. Without one, nothing is recorded and the statistics buttons are hidden.

**Constructor examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> window_ = MainWindow(Learner(db, profile=db.add_profile("Ada")))
>>> window_.stats_button.isVisibleTo(window_)
True
>>> MainWindow().stats_button.isVisibleTo(window_)  # no profile, no statistics
False
```

### MainWindow.sidebar_width

```python
def sidebar_width() -> int
```

Return how wide the exercise list is.

**Returns**

- *int*: The width in pixels; 0 when the list is collapsed, as it always is on the start screen.

**Examples**

```pycon
>>> MainWindow().sidebar_width()
0
```

### MainWindow.toggle_sidebar

```python
def toggle_sidebar() -> None
```

Slide the list closed, or back open, for the user's button. The choice is remembered for next time.

**Examples**

```pycon
>>> window = MainWindow()
>>> window.toggle_sidebar()
>>> window._sidebar_pref
True
```

### MainWindow.open_exercise

```python
def open_exercise(cls: type[Exercise] | None) -> None
```

Show an exercise.

**Parameters**

- `cls` (*type of Exercise or None*): The exercise class; None (a category heading in the list, which has no class) does nothing.

**Examples**

```pycon
>>> from alto.exercises.library import KeySignatures
>>> window = MainWindow()
>>> window.open_exercise(KeySignatures)
>>> window.title_label.text()
'Key signatures'
```

### MainWindow.open_settings

```python
def open_settings() -> None
```

Open the application settings, and rebuild the window if the theme was changed.

**Examples**

```pycon
>>> MainWindow().open_settings()  # doctest: +SKIP
```

### MainWindow.rebuild

```python
def rebuild() -> None
```

Open a fresh window in the same place, so every icon and colour is drawn in the new theme.

**Examples**

```pycon
>>> MainWindow().rebuild()  # doctest: +SKIP
```

### MainWindow.open_stats

```python
def open_stats() -> None
```

Show the statistics in place of the current page. Nothing happens without a profile.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
>>> window.open_stats()
>>> window.title_label.text()
'Statistics'
>>> window.close_overlay()
```

### MainWindow.open_database

```python
def open_database() -> None
```

Show the database browser in place of the current page. Nothing happens without a profile.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
>>> window.open_database()
>>> window.title_label.text()
'Database'
>>> window.close_overlay()
```

### MainWindow.close_overlay

```python
def close_overlay() -> None
```

Leave the statistics or database page and show the page that was open before it.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
>>> window.open_stats()
>>> window.close_overlay()
>>> window.title_label.text()
'Alto - Music Theory'
```

### MainWindow.switch_profile

```python
def switch_profile() -> None
```

Choose or add a profile.

Their history and questions are kept apart; the next question comes from theirs.

**Examples**

```pycon
>>> window = MainWindow()
>>> window.switch_profile()  # without a profile there is nothing to switch
```

### MainWindow.show_home

```python
def show_home() -> None
```

Go back to the start screen, closing the statistics or database and hiding the exercise list.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> window = MainWindow()
>>> window.open_exercise(NoteNames)
>>> window.show_home()
>>> window.title_label.text()
'Alto - Music Theory'
```

### MainWindow.restart_app

```python
def restart_app() -> None
```

Launch a fresh copy of the app, then close this one.

**Examples**

```pycon
>>> MainWindow().restart_app()  # doctest: +SKIP
```
{% endraw %}
