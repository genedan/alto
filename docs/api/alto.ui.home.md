---
title: alto.ui.home
parent: api
package: alto.ui
order: 20
permalink: /api/alto.ui.home/
---
{% raw %}
The start screen: a card for every exercise, in rows by category.

**Examples**

```pycon
>>> from alto.exercises import REGISTRY
>>> page = HomePage(REGISTRY)
>>> len(page.cards) == len(REGISTRY)
True
```

## ExerciseCard

```python
ExerciseCard(
    cls: type[Exercise],
    *,
    parent: QWidget | None = None,
)
```

Bases: `QPushButton`

A big button: the exercise's icon on top, then its category, name and a one-line description.

**Examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> card = ExerciseCard(NoteNames)
>>> card.toolTip() == NoteNames.description
True
>>> (card.width(), card.height()) == (CARD_W, CARD_H)
True
```

**Constructor**

Build the card for one exercise.

**Parameters**

- `cls` (*type of Exercise*): The exercise class; its name, category and description are shown, and its class name picks the icon.
- `parent` (*QWidget or None, default None*): The widget that owns the card. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.exercises.library import IntervalNames
>>> ExerciseCard(IntervalNames).toolTip()
'Name the interval between two notes (up to an octave).'
```

## HomePage

```python
HomePage(
    registry: Iterable[type[Exercise]],
    *,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

The start screen: a row of exercise buttons for each category.

**Attributes**

- `exercise_chosen` (*Signal*): Emitted with the `Exercise` class when a card is clicked.
- `cards` (*list of ExerciseCard*): One per exercise, in registry order.
- `scroll_area` (*QScrollArea*): Scrolls the rows when the window is shorter than all of them.

**Examples**

```pycon
>>> from alto.exercises import REGISTRY
>>> page = HomePage(REGISTRY)
>>> chosen = []
>>> _ = page.exercise_chosen.connect(chosen.append)
>>> page.cards[0].click()
>>> chosen == [REGISTRY[0]]
True
```

**Constructor**

Build the page.

**Parameters**

- `registry` (*iterable of type of Exercise*): The exercises to show, in the order to show them.
- `parent` (*QWidget or None, default None*): The widget that owns the page. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.exercises.library import NoteNames
>>> len(HomePage([NoteNames]).cards)
1
```

### HomePage.resizeEvent

```python
def resizeEvent(event: QResizeEvent) -> None
```

Lay the cards out again when the page changes size.

**Parameters**

- `event` (*QResizeEvent*): The resize that happened.

**Examples**

```pycon
>>> from alto.exercises import REGISTRY
>>> page = HomePage(REGISTRY)
>>> page.show()
>>> page.resize(1000, 600)
>>> page._columns >= 1
True
```
{% endraw %}
