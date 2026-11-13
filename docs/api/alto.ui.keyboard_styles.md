---
title: alto.ui.keyboard_styles
parent: api
package: alto.ui
order: 22
permalink: /api/alto.ui.keyboard_styles/
---
{% raw %}
Keyboard styles: the colours and materials the on-screen piano keys are drawn in.

There are ready-made styles (`STYLES`) and a custom one built from colours chosen part by part.

**Examples**

```pycon
>>> BY_KEY["classic"].label
'Classic'
>>> style_for("no such style").key == DEFAULT
True
```

## KeyboardStyle

```python
KeyboardStyle(
    key: str,
    *,
    label: str,
    note: str,
    white: tuple[str, str],
    white_edge: str,
    black: tuple[str, str],
    black_edge: str,
    case: str | None = DEFAULT_CASE,
    felt: str | None = None,
    cap: str | None = None,
    narrow: float = 1.0,
    gap: float = 1.0,
    rail: float = 8.0,
    thick: bool = False,
    hue: bool = False,
    glow: bool = False,
    ink: bool = False,
    knobs: bool = False,
    reverse_below: int | None = None,
    dot: str | None = None,
    round: float = 7.0,
)
```

How a keyboard looks: the colours of the keys and the case, and a few details of the drawing.

**Attributes**

- `key` (*str*): The identifier saved in the settings.
- `label` (*str*): The name shown in the interface. Keyword-only.
- `note` (*str*): A few words on what it is modelled on. Keyword-only.
- `white` (*tuple of (str, str)*): The natural keys' colour at the top and at the bottom. Keyword-only.
- `white_edge` (*str*): The outline colour of the natural keys. Keyword-only.
- `black` (*tuple of (str, str)*): The sharps' colour at the top and at the bottom. Keyword-only.
- `black_edge` (*str*): The outline colour of the sharps. Keyword-only.
- `case` (*str or None*): The body around the keys; None draws no body. Keyword-only.
- `felt` (*str or None*): A strip of felt under the fallboard. Keyword-only.
- `cap` (*str or None*): A bone cap on top of each sharp. Keyword-only.
- `narrow` (*float, default 1.0*): How wide the sharps are, compared with a piano's. Keyword-only.
- `gap` (*float, default 1.0*): Pixels between neighbouring naturals. Keyword-only.
- `rail` (*float, default 8.0*): The height of the strip above the keys. Keyword-only.
- `thick` (*bool, default False*): Heavy outlines. Keyword-only.
- `hue` (*bool, default False*): Colour each key by its note name. Keyword-only.
- `glow` (*bool, default False*): A soft halo around the outlines. Keyword-only.
- `ink` (*bool, default False*): Hatched sharps, like an engraving. Keyword-only.
- `knobs` (*bool, default False*): A row of organ stop knobs in the strip above the keys. Keyword-only.
- `reverse_below` (*int or None*): Keys under this MIDI number swap colours (an organ's preset keys). Keyword-only.
- `dot` (*str or None*): The colour of a dot that marks every C. Keyword-only.
- `round` (*float, default 7.0*): The most the lower corners of a natural are rounded, in pixels. Keyword-only.

**Examples**

```pycon
>>> style = BY_KEY["modern"]
>>> style.label, style.case
('Modern piano', '#0d0d0f')
```

## custom_colours

```python
def custom_colours() -> dict[str, str | None]
```

Return the colour of each part of the custom keyboard.

**Returns**

- *dict of str to str or None*: Part name ("naturals", "sharps", "case", "felt" or "caps") to its colour, or None where an optional part is left out.

**Examples**

```pycon
>>> sorted(custom_colours())
['caps', 'case', 'felt', 'naturals', 'sharps']
```

## custom_style

```python
def custom_style() -> KeyboardStyle
```

Build the style from the custom colours.

Gradients and outlines are worked out from each part's colour.

**Returns**

- *KeyboardStyle*: The custom style, with the key "custom".

**Examples**

```pycon
>>> custom_style().key, custom_style().label
('custom', 'Custom')
```

## style_for

```python
def style_for(key: str) -> KeyboardStyle
```

Return the style with a given key.

**Parameters**

- `key` (*str*): A key of `BY_KEY`, or "custom".

**Returns**

- *KeyboardStyle*: That style; the default (Classic) if the key is not known.

**Examples**

```pycon
>>> style_for("modern").label
'Modern piano'
>>> style_for("nonsense").label
'Classic'
```

## current

```python
def current() -> KeyboardStyle
```

Return the keyboard style in use.

**Returns**

- *KeyboardStyle*: The style chosen in the settings (Classic until another is chosen).

**Examples**

```pycon
>>> current().key in BY_KEY or current().key == CUSTOM
True
```

## load_style

```python
def load_style() -> None
```

Apply the saved style (Classic if none is saved or it is unknown), and the saved custom colours.

**Examples**

```pycon
>>> store().setValue("ui/keyboard", "modern")
>>> load_style()
>>> current().key
'modern'
>>> set_style(DEFAULT)
```

## set_style

```python
def set_style(key: str) -> None
```

Choose and save a style, and redraw every keyboard already on screen.

**Parameters**

- `key` (*str*): A key of `BY_KEY`, or "custom".

**Examples**

```pycon
>>> set_style("modern")
>>> current().label
'Modern piano'
>>> set_style(DEFAULT)
```

## set_custom_colour

```python
def set_custom_colour(
    part: str,
    *,
    colour: str | None,
) -> None
```

Colour one part of the custom keyboard and switch to the custom style.

**Parameters**

- `part` (*str*): One of "naturals", "sharps", "case", "felt" or "caps".
- `colour` (*str or None*): A colour such as '#336699', or None to leave an optional part (case, felt or caps) out. Keyword-only.

**Examples**

```pycon
>>> set_custom_colour("naturals", colour="#ffffff")
>>> current().key, custom_colours()["naturals"]
('custom', '#ffffff')
>>> set_custom_colour("naturals", colour=DEFAULT_CUSTOM["naturals"])
>>> set_style(DEFAULT)
```

## on_redraw

```python
def on_redraw(hook: Callable[[], None]) -> None
```

Register a function to call whenever the keyboard style changes.

The keyboard widgets live in a module that imports this one, so they register themselves here instead of being found by
this module.

**Parameters**

- `hook` (*Callable*): A function with no arguments that lays out and repaints what depends on the style.

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

## reversed_key

```python
def reversed_key(
    style: KeyboardStyle,
    *,
    midi: int,
) -> bool
```

Report whether a key has swapped colours, as the low preset keys of an organ do.

**Parameters**

- `style` (*KeyboardStyle*): The style.
- `midi` (*int*): The key's MIDI number. Keyword-only.

**Returns**

- *bool*: True if the style swaps colours below some key and this key is below it.

**Examples**

```pycon
>>> from dataclasses import replace
>>> reversed_key(BY_KEY["classic"], midi=40)
False
>>> reversed_key(replace(BY_KEY["classic"], reverse_below=50), midi=40)
True
```

## key_brush

```python
def key_brush(
    style: KeyboardStyle,
    *,
    midi: int,
    black: bool,
    y: float,
    height: float,
) -> QBrush
```

Return the fill for a key.

**Parameters**

- `style` (*KeyboardStyle*): The style.
- `midi` (*int*): The key's MIDI number. Keyword-only.
- `black` (*bool*): True for a sharp or flat, False for a natural. Keyword-only.
- `y` (*float*): The key's top edge, in pixels. Keyword-only.
- `height` (*float*): The key's height, in pixels. Keyword-only.

**Returns**

- *QBrush*: A solid colour, a top-to-bottom gradient, or (for styles that colour keys by note) a colour that depends on the note.

**Examples**

```pycon
>>> key_brush(BY_KEY["classic"], midi=60, black=False, y=0, height=100).color().name()
'#fbfbfc'
>>> key_brush(BY_KEY["modern"], midi=60, black=False, y=0, height=100).gradient() is not None
True
```

## edge_color

```python
def edge_color(
    style: KeyboardStyle,
    *,
    midi: int,
    black: bool,
) -> QColor
```

Return the outline colour for a key.

**Parameters**

- `style` (*KeyboardStyle*): The style.
- `midi` (*int*): The key's MIDI number. Keyword-only.
- `black` (*bool*): True for a sharp or flat, False for a natural. Keyword-only.

**Returns**

- *QColor*: The outline colour.

**Examples**

```pycon
>>> edge_color(BY_KEY["classic"], midi=60, black=False).name()
'#9a9a9f'
>>> edge_color(BY_KEY["classic"], midi=61, black=True).name()
'#111114'
```
{% endraw %}
