---
title: alto.ui.pictures
parent: api
package: alto.ui
order: 28
permalink: /api/alto.ui.pictures/
---
{% raw %}
Small pictures of musical things (clefs, note values, key signatures, note ranges ...) for the settings panes.

Each picture is drawn in fixed units and then scaled, so the same picture serves as a summary in a menu row and, larger,
as the label of a choice. Colours come from the palette, so they work in light and dark themes.

**Examples**

```pycon
>>> CLEF_NAMES["treble"], VALUE_NAMES["sixteenth"]
('Treble', '16th')
>>> ClefPictures(["treble", "bass"]).toolTip()
'Treble, Bass'
```

## ClefPictures

```python
ClefPictures(
    clefs: list[str] | None = None,
    *,
    scale: float = 1.0,
    parent: QWidget | None = None,
)
```

Bases: `_Picture`

The selected clefs, each on its own five-line staff, and a two-stave picture with a brace for the grand staff.

Showing each clef on its own staff lets alto and tenor, which share a symbol, look different.

**Attributes**

- `H, W, GAP, SPACING` (*float*): The picture's height, the width of one clef, the distance between staff lines and the space between clefs.
- `NAMES` (*dict of str to str*): The name of each clef.
- `clefs` (*list of str*): The clefs shown.

**Examples**

```pycon
>>> ClefPictures(["alto", "tenor"]).toolTip()
'Alto, Tenor'
```

**Constructor**

Create the picture.

**Parameters**

- `clefs` (*list of str or None, default None*): The clefs to show, any of `CLEF_NAMES`.
- `scale` (*float, default 1.0*): How much to enlarge it. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> ClefPictures(["treble"], scale=2.0).width()
60
```

### ClefPictures.set_clefs

```python
def set_clefs(clefs: list[str]) -> None
```

Show different clefs and size the picture for them.

**Parameters**

- `clefs` (*list of str*): The clefs to show, any of `CLEF_NAMES`.

**Examples**

```pycon
>>> pictures = ClefPictures()
>>> pictures.set_clefs(["treble", "bass", "alto"])
>>> pictures.width()  # three clefs and the space between them
106
>>> pictures.toolTip()
'Treble, Bass, Alto'
```

### ClefPictures.icon

```python
@classmethod
def icon(
    clef: str,
    *,
    scale: float = 1.8,
) -> QIcon
```

Return one clef as an icon.

**Parameters**

- `clef` (*str*): A key of `CLEF_NAMES`.
- `scale` (*float, default 1.8*): How much to enlarge it. Keyword-only.

**Returns**

- *QIcon*: The icon.

**Examples**

```pycon
>>> ClefPictures.icon("grand").isNull()
False
```

### ClefPictures.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw each clef on its staff, or the grand staff with its brace.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> ClefPictures(["treble", "grand"]).grab().isNull()
False
```

## ValuePictures

```python
ValuePictures(
    values: list[str] | None = None,
    *,
    scale: float = 1.0,
    centre_stemless: bool = False,
    parent: QWidget | None = None,
)
```

Bases: `_Picture`

Note values as engraved symbols (no staff), each with its head on the same baseline so they line up.

**Attributes**

- `values` (*list of str*): The note values shown, keys of `VALUE_NAMES`.
- `centre_stemless` (*bool*): Whether the breve and whole note sit at the picture's vertical centre.

**Examples**

```pycon
>>> pictures = ValuePictures(["whole", "quarter", "eighth"])
>>> pictures.values
['whole', 'quarter', 'eighth']
```

**Constructor**

Create the picture.

**Parameters**

- `values` (*list of str or None, default None*): The note values to show.
- `scale` (*float, default 1.0*): How much to enlarge it. Keyword-only.
- `centre_stemless` (*bool, default False*): Put the breve and whole note at the picture's vertical centre, so beside a line of text they line up with the middle of the text; the others keep their heads low so their stems fit above. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> ValuePictures(["half"], centre_stemless=True).centre_stemless
True
```

### ValuePictures.set_values

```python
def set_values(values: list[str]) -> None
```

Show different note values and size the picture for them.

**Parameters**

- `values` (*list of str*): The note values to show.

**Examples**

```pycon
>>> pictures = ValuePictures()
>>> pictures.set_values(["breve", "whole"])
>>> pictures.values
['breve', 'whole']
```

### ValuePictures.icon

```python
@classmethod
def icon(
    value: str,
    *,
    scale: float = 1.7,
) -> QIcon
```

Return one note value as an icon.

**Parameters**

- `value` (*str*): A key of `VALUE_NAMES`.
- `scale` (*float, default 1.7*): How much to enlarge it. Keyword-only.

**Returns**

- *QIcon*: The icon.

**Examples**

```pycon
>>> ValuePictures.icon("quarter").isNull()
False
```

### ValuePictures.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw each note value.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> ValuePictures(["whole", "half", "quarter"]).grab().isNull()
False
```

## KeySignaturePicture

```python
KeySignaturePicture(
    key: int = 0,
    *,
    scale: float = 1.0,
    parent: QWidget | None = None,
)
```

Bases: `_Picture`

A key signature as a plain row of its sharps or flats, with no staff or clef.

Each sign sits at the height it has after a treble clef, and C major, which has none, shows a natural sign.

**Attributes**

- `H, GAP, STEP` (*float*): The picture's height, the distance between staff lines and the space between signs.
- `ORDER` (*dict of int to str*): Where each sign is written, in order, for sharps (1) and flats (-1).
- `key` (*int*): The key signature: sharps if positive, flats if negative.

**Examples**

```pycon
>>> KeySignaturePicture(2).toolTip()
'D major: 2 sharps'
```

**Constructor**

Create the picture.

**Parameters**

- `key` (*int, default 0*): The key signature: that many sharps if positive, flats if negative.
- `scale` (*float, default 1.0*): How much to enlarge it. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> KeySignaturePicture(0).toolTip()
'C major: no sharps or flats'
>>> KeySignaturePicture(-1).toolTip()
'F major: 1 flat'
```

### KeySignaturePicture.icon

```python
@classmethod
def icon(
    key: int,
    *,
    scale: float = 1.2,
) -> QIcon
```

Return a key signature as an icon.

**Parameters**

- `key` (*int*): Sharps if positive, flats if negative.
- `scale` (*float, default 1.2*): How much to enlarge it. Keyword-only.

**Returns**

- *QIcon*: The icon.

**Examples**

```pycon
>>> KeySignaturePicture.icon(3).isNull()
False
```

### KeySignaturePicture.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the row of sharps or flats, or a natural sign for C major.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> KeySignaturePicture(-3).grab().isNull()
False
```

## RangePictures

```python
RangePictures(
    items: list[tuple[str, int, int]] | None = None,
    *,
    scale: float = 1.0,
    max_width: float | None = None,
    parent: QWidget | None = None,
)
```

Bases: `_Picture`

For each clef, a staff with its lowest and highest note, so the range can be read off at a glance.

**Attributes**

- `H, W, SPACING` (*float*): The picture's height, the width of one staff and the space between staves.
- `MAX_SCALE` (*float*): The most the picture is enlarged to fit `max_width`.
- `max_width` (*float or None*): The width to enlarge the picture to, if any.
- `items` (*list of tuple of (str, int, int)*): Each clef with its lowest and highest note, as staff steps (`Note.diatonic`).

**Examples**

```pycon
>>> pictures = RangePictures([("treble", 22, 52)])
>>> pictures.toolTip()
'Treble: D3 to F7'
```

**Constructor**

Create the picture.

**Parameters**

- `items` (*list of tuple of (str, int, int) or None, default None*): Each clef with its lowest and highest note.
- `scale` (*float, default 1.0*): How much to enlarge it. Keyword-only.
- `max_width` (*float or None, default None*): Enlarge the picture to use this width (up to `MAX_SCALE`) however many clefs there are. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> RangePictures([("treble", 22, 52)], max_width=238).scale
1.9
```

### RangePictures.set_items

```python
def set_items(items: list[tuple[str, int, int]]) -> None
```

Show the ranges of some clefs and size the picture for them.

**Parameters**

- `items` (*list of tuple of (str, int, int)*): Each clef with its lowest and highest note, as staff steps (`Note.diatonic`).

**Examples**

```pycon
>>> pictures = RangePictures()
>>> pictures.set_items([("bass", 10, 40), ("alto", 21, 35)])
>>> pictures.toolTip().splitlines()
['Bass: F1 to A5', 'Alto: C3 to C5']
```

### RangePictures.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw a staff for each clef with its lowest and highest note.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> RangePictures([("treble", 22, 52), ("bass", 10, 40)]).grab().isNull()
False
```

## NamePicture

```python
NamePicture(
    naming: str = 'letters',
    *,
    scale: float = 1.0,
    parent: QWidget | None = None,
)
```

Bases: `_Picture`

How notes are named: C, D and E on a staff, labelled with letters or with solfège syllables.

**Attributes**

- `H, W` (*float*): The picture's height and width.
- `LETTERS, SYLLABLES` (*tuple of str*): The two sets of labels.
- `naming` (*str*): "letters" or "solfege".

**Examples**

```pycon
>>> NamePicture("solfege").toolTip()
'Solfège (Do Re Mi)'
```

**Constructor**

Create the picture.

**Parameters**

- `naming` (*str, default "letters"*): "letters" or "solfege".
- `scale` (*float, default 1.0*): How much to enlarge it. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> NamePicture().naming
'letters'
```

### NamePicture.set_naming

```python
def set_naming(naming: str) -> None
```

Choose which labels are drawn.

**Parameters**

- `naming` (*str*): "letters" for C D E, or "solfege" for Do Re Mi.

**Examples**

```pycon
>>> picture = NamePicture()
>>> picture.set_naming("solfege")
>>> picture.toolTip()
'Solfège (Do Re Mi)'
```

### NamePicture.icon

```python
@classmethod
def icon(
    naming: str,
    *,
    scale: float = 1.6,
) -> QIcon
```

Return the picture as an icon.

**Parameters**

- `naming` (*str*): "letters" or "solfege".
- `scale` (*float, default 1.6*): How much to enlarge it. Keyword-only.

**Returns**

- *QIcon*: The icon.

**Examples**

```pycon
>>> NamePicture.icon("letters").isNull()
False
```

### NamePicture.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the staff, the clef, the three notes and their labels.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> NamePicture("letters").grab().isNull()
False
```
{% endraw %}
