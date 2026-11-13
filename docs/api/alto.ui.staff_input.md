---
title: alto.ui.staff_input
parent: api
package: alto.ui
order: 31
permalink: /api/alto.ui.staff_input/
---
{% raw %}
The staff you click to place a note, for the note construction exercise.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.accidental is None and not staff.locked
True
```

## StaffInput

```python
StaffInput(parent: QWidget | None = None)
```

Bases: `StaffWidget`

A single staff you click to place a note.

The note snaps to the nearest line or space and follows the pointer until you click.

**Attributes**

- `placed` (*Signal*): Emitted with the `Note` when you click, using the current `accidental`.
- `accidental_cycled` (*Signal*): Emitted on a right click: the owner steps through natural, sharp and flat.
- `accidental` (*int or None*): The sign you chose (-1 flat, 0 natural, 1 sharp); None follows the key signature.
- `locked` (*bool*): Ignore the mouse (while feedback is showing).

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.reset("treble", key=0)
>>> staff.resize(400, 300)
>>> str(staff.note_at(staff.staff_bottoms()["treble"]))  # the bottom line of the treble staff
'E4'
```

**Constructor**

Create the staff.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the staff.

**Constructor examples**

```pycon
>>> StaffInput().hasMouseTracking()
True
```

### StaffInput.reset

```python
def reset(
    clef: str,
    *,
    key: int = 0,
) -> None
```

Clear the staff for a new question, drawing a key signature.

**Parameters**

- `clef` (*str*): The clef to draw.
- `key` (*int, default 0*): The key signature: that many sharps if positive, flats if negative. Keyword-only.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.accidental, staff.locked = 1, True
>>> staff.reset("bass", key=-2)
>>> staff.accidental is None, staff.locked, staff.key
(True, False, -2)
```

### StaffInput.note_at

```python
def note_at(y: float) -> Note
```

Return the note on the line or space nearest to a height on the staff.

The note is kept within five ledger lines of the staff. On a grand staff, a click in the upper half is on the treble
staff and the lower half on the bass staff.

**Parameters**

- `y` (*float*): The height in the widget, in pixels from the top.

**Returns**

- *Note*: The note, with the chosen accidental or, if none is chosen, the one the key signature gives it.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.reset("treble", key=1)  # G major: F is sharp
>>> staff.resize(400, 300)
>>> bottom = staff.staff_bottoms()["treble"]
>>> str(staff.note_at(bottom - 3 * staff.GAP / 2))  # three steps above E4
'A4'
>>> str(staff.note_at(bottom - staff.GAP / 2))  # one step above E4: F, sharp in this key
'F♯4'
```

### StaffInput.show_note

```python
def show_note(
    note: Note | None,
    *,
    color: QColor | None = None,
) -> None
```

Draw a single note on the staff, or clear it.

**Parameters**

- `note` (*Note or None*): The note to draw; None clears the staff.
- `color` (*QColor or None, default None*): The colour to draw it in; the notation's own ink if None. Keyword-only.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.show_note(Note.parse("C4"))
>>> len(staff.columns)
1
>>> staff.show_note(None)
>>> staff.columns
[]
```

### StaffInput.refresh_preview

```python
def refresh_preview() -> None
```

Redraw the pointer's note, for example after the accidental changes.

**Examples**

```pycon
>>> StaffInput().refresh_preview()  # the pointer is not over the staff: nothing to redraw
```

### StaffInput.mouseMoveEvent

```python
def mouseMoveEvent(event: QMouseEvent) -> None
```

Show the note under the pointer, in a lighter colour.

**Parameters**

- `event` (*QMouseEvent*): The mouse move.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.reset("treble")
>>> staff.resize(400, 300)
>>> from PySide6.QtCore import QPointF
>>> point = QPointF(50, staff.staff_bottoms()["treble"])
>>> staff.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
>>> str(staff.columns[0][0])
'E4'
```

### StaffInput.leaveEvent

```python
def leaveEvent(event: QEvent) -> None
```

Remove the pointer's note when the pointer leaves the staff.

**Parameters**

- `event` (*QEvent*): The leave event.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.show_note(Note.parse("C4"))
>>> staff.leaveEvent(QEvent(QEvent.Type.Leave))
>>> staff.columns
[]
```

### StaffInput.mousePressEvent

```python
def mousePressEvent(event: QMouseEvent) -> None
```

Place the note on a left click, or step through the accidentals on a right click.

**Parameters**

- `event` (*QMouseEvent*): The mouse press. Nothing happens while the staff is locked.

**Examples**

```pycon
>>> staff = StaffInput()
>>> staff.reset("treble")
>>> staff.resize(400, 300)
>>> placed = []
>>> _ = staff.placed.connect(placed.append)
>>> from PySide6.QtCore import QPointF
>>> point = QPointF(50, staff.staff_bottoms()["treble"])
>>> staff.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
...                                   Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
>>> [str(n) for n in placed]
['E4']
```
{% endraw %}
