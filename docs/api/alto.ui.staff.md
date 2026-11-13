---
title: alto.ui.staff
parent: api
package: alto.ui
order: 30
permalink: /api/alto.ui.staff/
---
{% raw %}
The staff: lines, clefs, key signatures and notes, drawn on a rounded white "paper".

`StaffWidget` draws one staff, or a grand staff with a brace, in any of the seven clefs. Notes and key signatures are
placed by their staff step (`Note.diatonic`) measured from the bottom line of the clef, and are engraved in the notation
font chosen in the settings.

**Examples**

```pycon
>>> key_signature_positions("treble", sign=1)
['F5', 'C5', 'G5', 'D5', 'A4', 'E5', 'B4']
>>> staff = StaffWidget()
>>> staff.show_notes([[Note.parse("C4")]], clef="treble", key=2)
>>> staff.clef, staff.key
('treble', 2)
```

## key_signature_positions

```python
def key_signature_positions(
    clef: str,
    *,
    sign: int,
) -> list[str]
```

Return the notes the sharps or flats of a key signature are written on, in a clef.

Each accidental is a fourth up or a fifth down from the one before (sharps: F C G D A E B, flats: B E A D G C F), and the
pattern is chosen so that all seven stay on the staff, or one step above or below it. This gives the usual signatures for
the treble, bass, alto and tenor clefs, and works out the rest.

**Parameters**

- `clef` (*str*): A key of `BOTTOM_LINE`.
- `sign` (*int*): 1 for sharps, -1 for flats. Keyword-only.

**Returns**

- *list of str*: Seven note names with octaves, in the order the accidentals appear.

**Raises**

- *ValueError*: If no placement keeps all seven accidentals on the staff.

**Examples**

```pycon
>>> key_signature_positions("treble", sign=1)
['F5', 'C5', 'G5', 'D5', 'A4', 'E5', 'B4']
>>> key_signature_positions("bass", sign=-1)
['B2', 'E3', 'A2', 'D3', 'G2', 'C3', 'F2']
```

## draw_key_signature

```python
def draw_key_signature(
    p: QPainter,
    *,
    clef: str,
    key: int,
    x: float,
    bottom: float,
    gap: float,
    color: QColor,
    step: float = KEY_STEP,
    size: float = 2.0,
    font: str | None = None,
) -> None
```

Draw the sharps or flats of a key signature, left to right.

**Parameters**

- `p` (*QPainter*): The painter to draw with.
- `clef` (*str*): The clef, which decides where on the staff each accidental goes. Keyword-only.
- `key` (*int*): The key signature: that many sharps if positive, flats if negative; nothing is drawn for 0. Keyword-only.
- `x` (*float*): The left edge of the first accidental, in pixels. Keyword-only.
- `bottom` (*float*): The y position of the staff's bottom line, in pixels. Keyword-only.
- `gap` (*float*): The distance between staff lines, in pixels. Keyword-only.
- `color` (*QColor*): The colour to draw in. Keyword-only.
- `step` (*float, default KEY_STEP*): The horizontal spacing between accidentals. Keyword-only.
- `size` (*float, default 2.0*): The size of the built-in characters, in staff gaps. Keyword-only.
- `font` (*str or None, default None*): A SMuFL font to engrave them in; None uses the built-in sharp and flat characters. Keyword-only.

**Examples**

```pycon
>>> from PySide6.QtGui import QImage
>>> image = QImage(200, 120, QImage.Format.Format_ARGB32)
>>> image.fill(QColor("white"))
>>> painter = QPainter(image)
>>> draw_key_signature(painter, clef="treble", key=3, x=10, bottom=80, gap=12, color=QColor("black"), font="bravura")
>>> painter.end()
True
>>> any(image.pixelColor(x_, y_).lightness() < 128 for x_ in range(10, 60) for y_ in range(20, 100))
True
```

## StaffWidget

```python
StaffWidget(
    parent: QWidget | None = None,
    *,
    gap: float = 16.0,
    side: float = 20.0,
    note_offset: float = 100.0,
    margin: float = 8.0,
    compact: bool = False,
    max_step: float | None = None,
)
```

Bases: `QWidget`

A staff with notes, a clef, a key signature and, optionally, a caption.

**Attributes**

- `GAP` (*float*): The distance between staff lines, in pixels.
- `side` (*float*): The space at the left and right edges.
- `note_offset` (*float*): Where the notes start, from the left edge.
- `margin` (*float*): The space kept above and below the staff for ledger lines, in gaps.
- `compact` (*bool*): Size the widget to fit instead of the 220 px default.
- `max_step` (*float or None*): The most width each column of notes may take.
- `clef` (*str*): The clef being drawn ("treble", "bass", "alto", "tenor", "soprano", "mezzo", "baritone" or "grand").
- `columns` (*list of list of Note*): The notes drawn; each inner list is one chord or note.
- `note_color` (*QColor or None*): The colour of the notes; None draws them in the notation style's ink.
- `notation_style` (*NotationStyle or None*): A style to use instead of the one chosen in the settings.
- `key` (*int*): The key signature drawn: sharps if positive, flats if negative.
- `value` (*str*): The note value drawn.
- `caption` (*str*): Text written under the staff, inside the paper.

**Examples**

```pycon
>>> staff = StaffWidget()
>>> staff.show_notes([[Note.parse("E4")], [Note.parse("G4")]], clef="treble")
>>> len(staff.columns)
2
```

**Constructor**

Create an empty treble staff.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the staff.
- `gap` (*float, default 16.0*): The distance between staff lines, in pixels. Keyword-only.
- `side` (*float, default 20.0*): The space at the left and right edges. Keyword-only.
- `note_offset` (*float, default 100.0*): Where the notes start, from the left edge. Keyword-only.
- `margin` (*float, default 8.0*): The space kept above and below the staff for ledger lines, in gaps. Keyword-only.
- `compact` (*bool, default False*): Size the widget to fit instead of the 220 px default. Keyword-only.
- `max_step` (*float or None, default None*): The most width each column of notes may take: the staff then stops growing once its notes would be spread wider than that, so a few notes stay easy to read in a wide window. Keyword-only.

**Constructor examples**

```pycon
>>> StaffWidget(gap=8.0, compact=True).GAP
8.0
```

### StaffWidget.show_notes

```python
def show_notes(
    columns: list[list[Note]],
    *,
    clef: str = 'treble',
    key: int = 0,
    value: str = 'whole',
    caption: str = '',
) -> None
```

Show some notes, with a clef and a key signature.

**Parameters**

- `columns` (*list of list of Note*): The notes: each inner list is one note or chord, drawn left to right.
- `clef` (*str, default "treble"*): The clef, or "grand" for a grand staff. Keyword-only.
- `key` (*int, default 0*): The key signature: that many sharps if positive, flats if negative. Keyword-only.
- `value` (*str, default "whole"*): The note value to draw (stems are only drawn for single notes). Keyword-only.
- `caption` (*str, default ""*): Text to write under the staff. Keyword-only.

**Examples**

```pycon
>>> staff = StaffWidget()
>>> staff.show_notes([[Note.parse("C4")]], clef="bass", key=-1, value="quarter", caption="_ Major")
>>> staff.clef, staff.key, staff.value, staff.caption
('bass', -1, 'quarter', '_ Major')
```

### StaffWidget.sizeHint

```python
def sizeHint() -> QSize
```

Return the size the staff would like.

A capped staff asks for its full capped width, so a layout that centres it gives it that much.

**Returns**

- *QSize*: The capped width and the minimum height for a staff with a `max_step`; otherwise Qt's default.

**Examples**

```pycon
>>> staff = StaffWidget(max_step=120.0)
>>> staff.show_notes([[Note.parse("C4")]])
>>> staff.sizeHint().width()
500
```

### StaffWidget.set_note_color

```python
def set_note_color(color: QColor | None) -> None
```

Draw the notes in a colour, for feedback, or back in the style's ink.

**Parameters**

- `color` (*QColor or None*): The colour; None to use the notation style's ink.

**Examples**

```pycon
>>> staff = StaffWidget()
>>> staff.set_note_color(QColor("#2e7d32"))
>>> # noinspection PyUnresolvedReferences
>>> staff.note_color.name()
'#2e7d32'
>>> staff.set_note_color(None)
>>> staff.note_color is None
True
```

### StaffWidget.staff_bottoms

```python
def staff_bottoms() -> dict[str, float]
```

Return where each staff is drawn.

**Returns**

- *dict of str to float*: Clef name to the y position of that staff's bottom line, in pixels. A grand staff has a "treble" and a "bass".

**Examples**

```pycon
>>> staff = StaffWidget()
>>> staff.resize(400, 400)
>>> staff.staff_bottoms()
{'treble': 232.0}
```

### StaffWidget.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the paper, the staff lines, the clef, the key signature, the notes and the caption.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> staff = StaffWidget()
>>> staff.resize(400, 400)
>>> staff.show_notes([[Note.parse("C4")]], clef="treble")
>>> staff.grab().toImage().pixelColor(200, 5).name()  # the white paper
'#ffffff'
```
{% endraw %}
