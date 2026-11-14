---
title: alto.ui.notation
parent: api
package: alto.ui
order: 26
permalink: /api/alto.ui.notation/
---
{% raw %}
Notation styles: which music font the staff, clefs, notes and accidentals are engraved in.

Also holds the choice of how the baritone clef is written (an F clef or a C clef).

**Examples**

```pycon
>>> BY_KEY["leland"].label
'Leland'
>>> clef_shape("treble")
'treble'
```

## NotationStyle

```python
NotationStyle(
    key: str,
    *,
    label: str,
    note: str,
    font: str | None,
    line: float = 1.4,
)
```

One look for the music: a font and how heavy the staff lines are.

**Attributes**

- `key` (*str*): The identifier saved in the settings.
- `label` (*str*): The name shown in the interface. Keyword-only.
- `note` (*str*): A few words on where this look comes from. Keyword-only.
- `font` (*str or None*): A key in engraving.json, or None for the built-in Noto Music drawing. Keyword-only.
- `line` (*float, default 1.4*): The staff line weight in pixels, for the built-in drawing (the SMuFL fonts state their own). Keyword-only.

**Examples**

```pycon
>>> style = BY_KEY["noto"]
>>> style.label, style.font
('Noto Music', None)
```

## baritone_clef

```python
def baritone_clef() -> str
```

Return which way the baritone clef is written.

**Returns**

- *str*: "f" for an F clef on the middle line, or "c" for a C clef on the top line.

**Examples**

```pycon
>>> baritone_clef() in BARITONE_CLEFS
True
```

## clef_shape

```python
def clef_shape(clef: str) -> str
```

Return the clef as it is drawn.

**Parameters**

- `clef` (*str*): A clef name such as "treble" or "baritone".

**Returns**

- *str*: The same name, except that "baritone" becomes "baritone_f" or "baritone_c" by the chosen way of writing it.

**Examples**

```pycon
>>> clef_shape("alto")
'alto'
>>> set_baritone_clef("c")
>>> clef_shape("baritone")
'baritone_c'
>>> set_baritone_clef("f")  # back to the default
>>> clef_shape("baritone")
'baritone_f'
```

## set_baritone_clef

```python
def set_baritone_clef(kind: str) -> None
```

Choose and save how the baritone clef is written, and redraw every staff already on screen.

**Parameters**

- `kind` (*str*): "f" or "c"; anything else gives the default (F).

**Examples**

```pycon
>>> set_baritone_clef("c")
>>> baritone_clef()
'c'
>>> set_baritone_clef("sideways")  # not a choice: the default
>>> baritone_clef()
'f'
```

## current

```python
def current() -> NotationStyle
```

Return the notation style in use.

**Returns**

- *NotationStyle*: The style chosen in the settings (Finale Maestro until another is chosen).

**Examples**

```pycon
>>> current().key in BY_KEY
True
```

## load_style

```python
def load_style() -> None
```

Apply the saved choices: the style (Finale Maestro if none is saved or it is unknown) and the baritone clef.

**Examples**

```pycon
>>> store().setValue("ui/notation", "bravura")
>>> load_style()
>>> current().key
'bravura'
>>> set_style(DEFAULT)  # back to the default
```

## set_style

```python
def set_style(key: str) -> None
```

Choose and save a style, and redraw every staff already on screen.

**Parameters**

- `key` (*str*): A key of `BY_KEY`; an unknown key gives the default.

**Examples**

```pycon
>>> set_style("leland")
>>> current().label
'Leland'
>>> set_style(DEFAULT)
```

## on_redraw

```python
def on_redraw(hook: Callable[[], None]) -> None
```

Register a function to call whenever the notation style changes.

The staff widgets live in a module that imports this one, so they register themselves here instead of being found by
this module.

**Parameters**

- `hook` (*Callable*): A function with no arguments that repaints what depends on the style.

**Examples**

```pycon
>>> calls = []
>>> def repaint() -> None:
...     calls.append(1)
>>> on_redraw(repaint)
>>> _redraw()
>>> calls
[1]
>>> _redraw_hooks.remove(repaint)
```
{% endraw %}
