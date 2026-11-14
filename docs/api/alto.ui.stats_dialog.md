---
title: alto.ui.stats_dialog
parent: api
package: alto.ui
order: 34
permalink: /api/alto.ui.stats_dialog/
---
{% raw %}
The statistics screen: a few numbers and charts about how practice is going.

It shows the active profile's own answers, filterable by exercise and by timeframe.

**Examples**

```pycon
>>> since_for(None, now=1000.0) is None  # all time: from the start
True
>>> format_duration(3600)
'1 h 00 min'
```

## since_for

```python
def since_for(
    span: str | int | None,
    *,
    now: float,
) -> float | None
```

Return the timestamp a timeframe starts from.

**Parameters**

- `span` (*str or int or None*): "today", a number of days back, or None for all time.
- `now` (*float*): The current time as a timestamp. Keyword-only.

**Returns**

- *float or None*: Midnight for "today", `now` less that many days for a number, and None for all time.

**Examples**

```pycon
>>> since_for(7, now=864000.0)
259200.0
>>> since_for(None, now=864000.0) is None
True
>>> 0 <= 864000.0 - since_for("today", now=864000.0) < 90000  # within a day of now
True
```

## format_duration

```python
def format_duration(seconds: float) -> str
```

Write a length of time the way the statistics show it.

**Parameters**

- `seconds` (*float*): The time in seconds.

**Returns**

- *str*: Seconds under half a minute, then minutes, then hours and minutes.

**Examples**

```pycon
>>> format_duration(5), format_duration(90), format_duration(3000)
('5 s', '2 min', '50 min')
>>> format_duration(3 * 3600 + 7 * 60)
'3 h 07 min'
```

## period_title

```python
def period_title(
    start: datetime,
    *,
    granularity: str,
) -> str
```

Name a chart period in words, for the heading of its list of answers.

**Parameters**

- `start` (*datetime*): The start of the period.
- `granularity` (*str*): "hour", "day", "week" or "month", as `Stats.granularity` says. Keyword-only.

**Returns**

- *str*: For example "Mon 5 Jan 2026", "Week of Mon 5 Jan 2026" or "January 2026".

**Examples**

```pycon
>>> period_title(datetime(2026, 1, 5, 14), granularity="hour")
'Mon 5 Jan 2026, 14:00'
>>> period_title(datetime(2026, 1, 5), granularity="day")
'Mon 5 Jan 2026'
>>> period_title(datetime(2026, 1, 5), granularity="week")
'Week of Mon 5 Jan 2026'
>>> period_title(datetime(2026, 1, 1), granularity="month")
'January 2026'
```

## Tile

```python
Tile(
    caption: str,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QFrame`

One headline number with its caption.

**Attributes**

- `value` (*QLabel*): The big number.
- `caption` (*QLabel*): What the number is.

**Examples**

```pycon
>>> tile = Tile("Questions answered")
>>> tile.value.text()
'–'
>>> tile.show_value("12")
>>> tile.value.text()
'12'
```

**Constructor**

Create a tile showing a dash until it is given a value.

**Parameters**

- `caption` (*str*): What the number is, shown under it.
- `parent` (*QWidget or None, default None*): The widget that owns the tile. Keyword-only.

**Constructor examples**

```pycon
>>> tile = Tile("Days practised")
>>> tile.caption.text()
'Days practised'
```

### Tile.show_value

```python
def show_value(text: str) -> None
```

Show a number (or any text) in the tile.

**Parameters**

- `text` (*str*): What to show.

**Examples**

```pycon
>>> tile = Tile("Typical first answer")
>>> tile.show_value("7.6 s")
>>> tile.value.text()
'7.6 s'
```

## StatsPage

```python
StatsPage(
    learner: Learner,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

The statistics, as a page of the main window.

**Attributes**

- `back` (*Signal*): Emitted by the Back button and by Escape.
- `learner` (*Learner*): Whose answers are shown; only the active profile's own.
- `exercise` (*QComboBox*): The exercise filter.
- `timeframe` (*QComboBox*): The timeframe filter.
- `tiles` (*dict of str to Tile*): The headline numbers, by name.
- `detail` (*QFrame*): The panel under the charts that lists the answers behind a clicked bar, point, row or day. Hidden until one is clicked.
- `answers` (*AnswerList*): The table in the detail panel.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
>>> page.note.text().startswith("No answers recorded for Ada")
True
```

**Constructor**

Build the page and fill it for the current filters.

**Parameters**

- `learner` (*Learner*): Whose statistics to show.
- `parent` (*QWidget or None, default None*): The widget that owns the page. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
>>> page.timeframe.currentText()  # the last 30 days, until another is chosen
'Last 30 days'
```

### StatsPage.refresh

```python
def refresh() -> None
```

Recalculate everything for the chosen exercise and timeframe and show it.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
>>> page.refresh()
>>> page.tiles["questions"].value.text()  # nothing answered yet
'0'
```
{% endraw %}
