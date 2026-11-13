---
title: alto.ui.notes
parent: api
package: alto.ui
order: 25
permalink: /api/alto.ui.notes/
---
{% raw %}
Engraved notes built from the Noto Music font's glyphs, the way notation software draws them.

The font only has stem-up notes. A stem-down note is made from the same glyph turned half a turn (which puts the stem on
the left of the head and keeps the head's tilt), with the flags cut from the stem-up glyph and mirrored so they sweep up
from the stem's end, as an engraver would write them.

All numbers are in glyph units at a font size of 100, where one staff space is `STAFF_SPACE` units.

**Examples**

```pycon
>>> note_shape("quarter").isEmpty()
False
>>> note_shape("whole", stem_down=True) is note_shape("whole")  # a whole note has no stem to turn
True
```

## note_shape

```python
def note_shape(
    value: str,
    *,
    stem_down: bool = False,
) -> QPainterPath
```

Return the outline of a note of a value, with the stem up or down.

Stems only exist from the half note on, so a breve or whole note is the same either way. Shapes are kept after the first
time.

**Parameters**

- `value` (*str*): "breve", "whole", "half", "quarter", "eighth", "sixteenth" or "thirty_second".
- `stem_down` (*bool, default False*): Turn the stem down. Keyword-only.

**Returns**

- *QPainterPath*: The outline, in glyph units.

**Examples**

```pycon
>>> up, down = note_shape("quarter"), note_shape("quarter", stem_down=True)
>>> up == down
False
```

## draw_note

```python
def draw_note(
    p: QPainter,
    *,
    value: str,
    x: float,
    y: float,
    gap: float,
    colour: QColor,
    stem_down: bool = False,
) -> None
```

Draw a note with its head centred on a point.

**Parameters**

- `p` (*QPainter*): The painter to draw with.
- `value` (*str*): The note value. Keyword-only.
- `x` (*float*): The head's centre, in pixels. Keyword-only.
- `y` (*float*): The head's centre, in pixels. Keyword-only.
- `gap` (*float*): The distance between staff lines, which is also the head's height. Keyword-only.
- `colour` (*QColor*): The colour to draw in. Keyword-only.
- `stem_down` (*bool, default False*): Draw the stem down. Keyword-only.

**Examples**

```pycon
>>> from PySide6.QtGui import QImage
>>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
>>> image.fill(QColor("white"))
>>> painter = QPainter(image)
>>> draw_note(painter, value="quarter", x=50, y=50, gap=16, colour=QColor("black"))
>>> painter.end()
True
>>> image.pixelColor(50, 50).lightness() < 128  # the head is drawn at the point
True
```
{% endraw %}
