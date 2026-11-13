---
title: alto.ui.keyboard
parent: api
package: alto.ui
order: 21
permalink: /api/alto.ui.keyboard/
---
{% raw %}
The on-screen piano keyboard, drawn to real proportions, and a miniature of the whole piano for choosing a span of keys.

`KeyboardWidget` shows a range of keys and can highlight one. `KeyboardSpan` shows all 88 keys in miniature, shades the
range that will be asked, and can be dragged to change it. Colours and materials come from `keyboard_styles`.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.show_key(60)
>>> keyboard.highlight
60
```

## KeyboardWidget

```python
KeyboardWidget(parent: QWidget | None = None)
```

Bases: `QWidget`

A piano keyboard drawn to real proportions that can highlight one key.

**Attributes**

- `lo` (*int*): The lowest key shown, as a MIDI number.
- `hi` (*int*): The highest key shown, as a MIDI number.
- `highlight` (*int or None*): The key to highlight.
- `style_override` (*KeyboardStyle or None*): A fixed style, for the preview cards in the settings; otherwise the style chosen in the settings is used.
- `pad` (*float*): The frame padding, in pixels.
- `max_key_width` (*float*): The widest a key may be, in pixels. Smaller when something else (the key signature) shares the page.
- `highlight_color` (*QColor*): The colour of the highlighted key.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> (keyboard.lo, keyboard.hi)  # C3 to C5, until another range is shown
(48, 72)
```

**Constructor**

Create a keyboard showing the default range, with no key highlighted.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the keyboard.

**Constructor examples**

```pycon
>>> KeyboardWidget().highlight is None
True
```

### KeyboardWidget.style

```python
@property
def style() -> KeyboardStyle
```

Return the style the keyboard is drawn in.

**Returns**

- *KeyboardStyle*: The fixed style if one is set, otherwise the style chosen in the settings.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.style_override = keyboard_styles.BY_KEY["modern"]
>>> keyboard.style.label
'Modern piano'
```

### KeyboardWidget.refit

```python
def refit() -> None
```

Size and redraw the keyboard after the style changes.

Some styles have a taller strip above the keys.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.refit()
>>> keyboard.height() > 0
True
```

### KeyboardWidget.resizeEvent

```python
def resizeEvent(event: QResizeEvent) -> None
```

Change the height to match the new width, since keys are drawn to real proportions.

**Parameters**

- `event` (*QResizeEvent*): The resize that happened.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.show()
>>> keyboard.resize(300, 300)
>>> keyboard.height()  # narrower, so shorter
143
```

### KeyboardWidget.show_key

```python
def show_key(
    midi: int | None,
    *,
    span: tuple[int, int] | None = None,
) -> None
```

Highlight a key, and optionally choose the range of keys to show.

**Parameters**

- `midi` (*int or None*): The key to highlight, or None for no highlight.
- `span` (*tuple of (int, int) or None, default None*): The lowest and highest key to show; it is widened to whole white keys. Keyword-only.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.show_key(60, span=(49, 71))  # C#3 is widened to C3
>>> (keyboard.lo, keyboard.hi, keyboard.highlight)
(48, 71, 60)
```

### KeyboardWidget.set_highlight_color

```python
def set_highlight_color(color: QColor) -> None
```

Choose the colour of the highlighted key and redraw.

**Parameters**

- `color` (*QColor*): The colour.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.set_highlight_color(QColor("#2e7d32"))
>>> keyboard.highlight_color.name()
'#2e7d32'
```

### KeyboardWidget.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the case, the keys, the highlighted key and the style's extras.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> keyboard = KeyboardWidget()
>>> keyboard.show_key(60)
>>> keyboard.grab().isNull()
False
```

## KeyboardSpan

```python
KeyboardSpan(
    parent: QWidget | None = None,
    *,
    compact: bool = False,
    size: tuple[int, int] = (124, 26),
)
```

Bases: `QWidget`

The whole 88-key piano in miniature, with the keys that will be asked shaded.

The full-size one can be dragged across to choose the span: `dragged` is emitted with the lowest and highest key as it
changes.

**Attributes**

- `dragged` (*Signal*): Emitted with the lowest and highest key (MIDI numbers) as the span is dragged.
- `lo` (*int*): The lowest key shaded.
- `hi` (*int*): The highest key shaded.

**Examples**

```pycon
>>> span = KeyboardSpan()
>>> span.set_span(60, hi=72)
>>> (span.lo, span.hi)
(60, 72)
```

**Constructor**

Create the miniature, shading the default range.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns it.
- `compact` (*bool, default False*): Make a fixed-size version that ignores the mouse, for a summary in a menu row. Keyword-only.
- `size` (*tuple of (int, int), default (124, 26)*): The width and height of the compact version, in pixels. Keyword-only.

**Constructor examples**

```pycon
>>> KeyboardSpan(compact=True, size=(100, 20)).size().width()
100
```

### KeyboardSpan.key_at

```python
def key_at(pos: QPointF) -> int
```

Return the key under a point.

**Parameters**

- `pos` (*QPointF*): The position in the widget.

**Returns**

- *int*: The MIDI number: a black key where one is drawn there, else the white key (clamped to the ends of the piano).

**Examples**

```pycon
>>> span = KeyboardSpan()
>>> span.resize(500, 64)
>>> span.key_at(QPointF(0, 50)), span.key_at(QPointF(499, 50))  # the lowest and highest keys
(21, 108)
>>> span.key_at(QPointF(250, 50))
64
```

### KeyboardSpan.mousePressEvent

```python
def mousePressEvent(event: QMouseEvent) -> None
```

Start choosing a span: grab an edge, pick the span up, or start a new one.

**Parameters**

- `event` (*QMouseEvent*): The press. Only the left button does anything.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> span = KeyboardSpan()
>>> span.resize(500, 64)
>>> got = []
>>> _ = span.dragged.connect(lambda lo, hi: got.append((lo, hi)))
>>> point = QPointF(5, 50)
>>> span.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
...                                  Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
>>> got  # a press outside the span starts a new one on that key
[(21, 21)]
```

### KeyboardSpan.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Drag the span, or (with no button held) show the cursor for what a press here would do.

**Parameters**

- `event` (*QMouseEvent*): The move.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> span = KeyboardSpan()
>>> span.resize(500, 64)
>>> middle = QPointF(sum(span._edges()) / 2, 50)
>>> span.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, middle, middle, Qt.MouseButton.NoButton,
...                                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
>>> span.cursor().shape() == Qt.CursorShape.OpenHandCursor  # inside the span: it can be picked up
True
```

### KeyboardSpan.mouseReleaseEvent

```python
def mouseReleaseEvent(event: QMouseEvent) -> None
```

Finish a drag and refresh the cursor for where the pointer now is.

**Parameters**

- `event` (*QMouseEvent*): The release.

**Examples**

```pycon
>>> from PySide6.QtCore import QEvent
>>> span = KeyboardSpan()
>>> span.resize(500, 64)
>>> point = QPointF(5, 50)
>>> span.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, point, point, Qt.MouseButton.LeftButton,
...                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
>>> span._mode is None
True
```

### KeyboardSpan.set_span

```python
def set_span(
    lo: int,
    *,
    hi: int,
) -> None
```

Choose which keys are shaded and redraw.

**Parameters**

- `lo` (*int*): The lowest key asked, as a MIDI number.
- `hi` (*int*): The highest key asked. Keyword-only.

**Examples**

```pycon
>>> span = KeyboardSpan()
>>> span.set_span(48, hi=72)
>>> (span.lo, span.hi)
(48, 72)
```

### KeyboardSpan.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the whole piano in miniature with the asked keys shaded and the span's edges marked.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> span = KeyboardSpan()
>>> span.grab().isNull()
False
```
{% endraw %}
