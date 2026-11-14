---
title: alto.ui.charts
parent: api
package: alto.ui
order: 15
permalink: /api/alto.ui.charts/
---
{% raw %}
Small charts drawn with QPainter, in the application's theme colours.

Stacked bars, a line, horizontal bars and a calendar heatmap. Each has a title, draws a message when there is nothing to
show, and explains the bar or square under the pointer in a tooltip.

**Examples**

```pycon
>>> nice_ticks(13)
[0, 5, 10, 15]
>>> chart = StackedBarChart("Questions answered")
>>> chart.set_data(["Mon", "Tue"], right=[3, 1], wrong=[1, 0])
>>> chart.right, chart.wrong
([3, 1], [1, 0])
```

## nice_ticks

```python
def nice_ticks(
    top: float,
    *,
    count: int = 4,
) -> list[float]
```

Return round tick values from 0 up to just above a top value.

**Parameters**

- `top` (*float*): The largest value to show.
- `count` (*int, default 4*): Roughly how many ticks to aim for. Keyword-only.

**Returns**

- *list of float*: Ticks at round steps (1, 2, 2.5, 5 or 10 times a power of ten), starting at 0 and reaching at least `top`. Just 0 and 1 when `top` is not positive.

**Examples**

```pycon
>>> nice_ticks(13)
[0, 5, 10, 15]
>>> nice_ticks(8)[-1] >= 8
True
>>> nice_ticks(0)
[0.0, 1.0]
```

## StackedBarChart

```python
StackedBarChart(
    title: str,
    *,
    parent: QWidget | None = None,
)
```

Bases: `_Chart`

Questions per period, the first-try right ones in green with the missed ones stacked above in red.

**Attributes**

- `right` (*list of int*): Questions right first time, per period.
- `wrong` (*list of int*): Questions missed, per period.

**Examples**

```pycon
>>> chart = StackedBarChart("Questions answered per day")
>>> chart.set_data(["Mon", "Tue", "Wed"], right=[3, 0, 5], wrong=[1, 2, 0])
>>> chart.labels
['Mon', 'Tue', 'Wed']
```

**Constructor**

Create an empty chart.

**Parameters**

- `title` (*str*): Drawn at the top left.
- `parent` (*QWidget or None, default None*): The widget that owns the chart. Keyword-only.

**Constructor examples**

```pycon
>>> StackedBarChart("Questions").right
[]
```

### StackedBarChart.set_data

```python
def set_data(
    labels: Sequence[str],
    *,
    right: Sequence[int],
    wrong: Sequence[int],
) -> None
```

Show a count of right and missed questions for each period.

**Parameters**

- `labels` (*sequence of str*): The label of each period.
- `right` (*sequence of int*): Questions right first time in each period. Keyword-only.
- `wrong` (*sequence of int*): Questions missed in each period. Keyword-only.

**Examples**

```pycon
>>> chart = StackedBarChart("Questions")
>>> chart.set_data(["a", "b"], right=[2, 0], wrong=[0, 4])
>>> chart.right, chart.wrong
([2, 0], [0, 4])
```

### StackedBarChart.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the axes and a bar for each period, or a message when no questions were answered.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> chart = StackedBarChart("Questions")
>>> chart.resize(400, 300)
>>> chart.set_data(["a", "b"], right=[3, 1], wrong=[1, 0])
>>> chart.grab().isNull()
False
```

### StackedBarChart.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Explain the bar under the pointer in a tooltip.

**Parameters**

- `event` (*QMouseEvent*): The mouse move.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> from PySide6.QtGui import QMouseEvent
>>> chart = StackedBarChart("Questions")
>>> chart.resize(400, 300)
>>> chart.set_data(["Mon", "Tue"], right=[3, 1], wrong=[1, 0])
>>> point = QPointF(chart._centres()[0], chart._plot().center().y())
>>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
```

## LineChart

```python
LineChart(
    title: str,
    *,
    fmt: Callable[[float], str],
    fixed_top: float | None = None,
    parent: QWidget | None = None,
)
```

Bases: `_Chart`

A value per period joined by a line.

Periods with no answers leave a gap rather than a zero.

**Attributes**

- `fmt` (*callable*): Turns a value into its label, for the axis and the tooltip.
- `fixed_top` (*float or None*): The value at the top of the plot; the largest value, rounded up, if None.
- `values` (*list of float or None*): The value of each period, or None for a gap.

**Examples**

```pycon
>>> chart = LineChart("Right first time", fmt=lambda v: f"{v:.0f}%", fixed_top=100)
>>> chart.set_data(["Mon", "Tue", "Wed"], values=[40.0, None, 80.0])
>>> chart.values
[40.0, None, 80.0]
```

**Constructor**

Create an empty chart.

**Parameters**

- `title` (*str*): Drawn at the top left.
- `fmt` (*callable*): Turns a value into its label. Keyword-only.
- `fixed_top` (*float or None, default None*): The value at the top of the plot (such as 100 for a percentage); the largest value, rounded up, if None. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the chart. Keyword-only.

**Constructor examples**

```pycon
>>> LineChart("Speed", fmt=lambda v: f"{v:.1f} s").fixed_top is None
True
```

### LineChart.set_data

```python
def set_data(
    labels: Sequence[str],
    *,
    values: Sequence[float | None],
) -> None
```

Show a value for each period.

**Parameters**

- `labels` (*sequence of str*): The label of each period.
- `values` (*sequence of float or None*): The value of each period; None leaves a gap. Keyword-only.

**Examples**

```pycon
>>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
>>> chart.set_data(["a", "b"], values=[2.5, None])
>>> chart.labels
['a', 'b']
```

### LineChart.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the axes, the line (one run at a time, so gaps show) and a dot for each value.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
>>> chart.resize(400, 300)
>>> chart.set_data(["a", "b", "c"], values=[2.0, None, 3.0])
>>> chart.grab().isNull()
False
```

### LineChart.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Say what the value under the pointer is in a tooltip.

**Parameters**

- `event` (*QMouseEvent*): The mouse move.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> from PySide6.QtGui import QMouseEvent
>>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
>>> chart.resize(400, 300)
>>> chart.set_data(["a", "b"], values=[2.0, 3.0])
>>> point = QPointF(chart._centres()[0], chart._plot().center().y())
>>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
```

## HBarChart

```python
HBarChart(
    title: str,
    *,
    parent: QWidget | None = None,
)
```

Bases: `_Chart`

One bar per name, on a fixed 0-100 scale, each with its value at the end.

**Attributes**

- `ROW` (*int*): The height of each bar's row, in pixels.
- `rows` (*list of tuple of (str, float, str)*): For each bar, its name, its value from 0 to 100 and the text shown at its end.

**Examples**

```pycon
>>> chart = HBarChart("Right first time, by exercise")
>>> chart.set_data([("Intervals", 77.0, "77%  ·  52 q"), ("Chords", 88.0, "88%  ·  48 q")])
>>> len(chart.rows)
2
```

**Constructor**

Create an empty chart.

**Parameters**

- `title` (*str*): Drawn at the top left.
- `parent` (*QWidget or None, default None*): The widget that owns the chart. Keyword-only.

**Constructor examples**

```pycon
>>> HBarChart("By exercise").rows
[]
```

### HBarChart.set_data

```python
def set_data(rows: Sequence[tuple[str, float, str]]) -> None
```

Show a bar for each name, and make the chart tall enough for them.

**Parameters**

- `rows` (*sequence of tuple of (str, float, str)*): Each bar's name, its value from 0 to 100, and the text shown at the end of the bar.

**Examples**

```pycon
>>> chart = HBarChart("By exercise")
>>> chart.set_data([(f"Exercise {i}", 50.0, "50%") for i in range(10)])
>>> chart.minimumHeight()
306
```

### HBarChart.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw a bar with its name and value for each row, or a message when there are none.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> chart = HBarChart("By exercise")
>>> chart.resize(400, 300)
>>> chart.set_data([("Intervals", 77.0, "77%")])
>>> chart.grab().isNull()
False
```

### HBarChart.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Highlight the row under the pointer.

**Parameters**

- `event` (*QMouseEvent*): The mouse move.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> chart = HBarChart("By exercise")
>>> chart.set_data([("A", 50.0, "50%")])
>>> point = QPointF(10, chart.TOP + chart.ROW / 2)
>>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
>>> chart.hovered
0
```

## HeatmapChart

```python
HeatmapChart(
    title: str,
    *,
    parent: QWidget | None = None,
)
```

Bases: `_Chart`

A calendar of reviews: a column per week (Monday to Sunday), a square per day, darker the more questions.

**Attributes**

- `LEVELS` (*int*): The number of shades above "none".
- `counts` (*dict of date to int*): Questions answered on each day that had any.
- `today` (*date*): The last day shown.
- `weeks` (*int*): How many weeks are shown, counting this one.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.set_data({date(2026, 11, 13): 12}, today=date(2026, 11, 13))
>>> chart.counts
{datetime.date(2026, 11, 13): 12}
```

**Constructor**

Create an empty calendar for the last 53 weeks.

**Parameters**

- `title` (*str*): Drawn at the top left.
- `parent` (*QWidget or None, default None*): The widget that owns the chart. Keyword-only.

**Constructor examples**

```pycon
>>> HeatmapChart("Reviews").weeks
53
```

### HeatmapChart.set_data

```python
def set_data(
    counts: dict[date, int],
    *,
    today: date,
    weeks: int = 53,
) -> None
```

Show how many questions were answered on each day.

**Parameters**

- `counts` (*dict of date to int*): Questions answered on each day that had any.
- `today` (*date*): The last day to show. Keyword-only.
- `weeks` (*int, default 53*): How many weeks to show, counting this one. Keyword-only.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.set_data({}, today=date(2026, 11, 13), weeks=26)
>>> chart.weeks
26
```

### HeatmapChart.first_day

```python
def first_day() -> date
```

Return the first day shown: the Monday that starts the first week.

**Returns**

- *date*: A Monday.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.set_data({}, today=date(2026, 11, 13))
>>> chart.first_day(), chart.first_day().weekday()
(datetime.date(2025, 11, 10), 0)
```

### HeatmapChart.level

```python
def level(count: int) -> int
```

Return how dark a day's square is.

**Parameters**

- `count` (*int*): Questions answered that day.

**Returns**

- *int*: 0 for no questions, otherwise 1 to `LEVELS` by how the day compares with the busiest. The scale is in quarters of the 90th-percentile day, so one huge day does not flatten everything else.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.set_data({date(2026, 11, 13): 40, date(2026, 11, 12): 20, date(2026, 11, 11): 1}, today=date(2026, 11, 13))
>>> chart.level(0), chart.level(1), chart.level(40)
(0, 1, 4)
```

### HeatmapChart.day_at

```python
def day_at(pos: QPointF) -> date | None
```

Return the day whose square is under a point.

**Parameters**

- `pos` (*QPointF*): The position in the widget.

**Returns**

- *date or None*: The day, or None if the point is outside the calendar or on a day that has not happened yet.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.resize(760, 190)
>>> chart.set_data({}, today=date(2026, 11, 13))
>>> cell_, (x0_, y0_) = chart._cell(), chart._origin()
>>> chart.day_at(QPointF(x0_ + 52.5 * cell_, y0_ + 4.5 * cell_))  # the last column, Friday
datetime.date(2026, 11, 13)
>>> chart.day_at(QPointF(x0_ + 52.5 * cell_, y0_ + 6.5 * cell_)) is None  # Sunday: not yet
True
```

### HeatmapChart.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the month and weekday labels, a square for each day, and the Less-More legend.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> chart = HeatmapChart("Reviews")
>>> chart.resize(760, 190)
>>> chart.set_data({date(2026, 11, 13): 5}, today=date(2026, 11, 13))
>>> chart.grab().isNull()
False
```

### HeatmapChart.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Say how many questions were answered on the day under the pointer, in a tooltip.

**Parameters**

- `event` (*QMouseEvent*): The mouse move.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> from PySide6.QtGui import QMouseEvent
>>> chart = HeatmapChart("Reviews")
>>> chart.resize(760, 190)
>>> chart.set_data({date(2026, 11, 13): 3}, today=date(2026, 11, 13))
>>> cell, (x0, y0) = chart._cell(), chart._origin()
>>> point = QPointF(x0 + 52.5 * cell, y0 + 4.5 * cell)
>>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
```
{% endraw %}
