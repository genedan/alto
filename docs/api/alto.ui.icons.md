---
title: alto.ui.icons
parent: api
package: alto.ui
order: 19
permalink: /api/alto.ui.icons/
---
{% raw %}
Small monochrome icons drawn from SVG, tinted with the current theme's text colour.

Each icon is the inside of a 24 by 24 SVG, written with the word COLOR where the theme colour goes. `svg_icon` turns one
into a `QIcon`.

**Examples**

```pycon
>>> svg_icon(HELP, color=QColor("black")).isNull()
False
```

## svg_icon

```python
def svg_icon(
    inner: str,
    *,
    color: QColor,
    size: int = 24,
    scale: float = 2.0,
) -> QIcon
```

Render 24 by 24 SVG shapes into a crisp icon.

**Parameters**

- `inner` (*str*): The SVG shapes, using COLOR wherever the colour goes.
- `color` (*QColor*): The colour to draw in. Keyword-only.
- `size` (*int, default 24*): The icon's size in logical pixels. Keyword-only.
- `scale` (*float, default 2.0*): How many device pixels to render per logical pixel, so it stays sharp on high-resolution screens. Keyword-only.

**Returns**

- *QIcon*: The icon.

**Examples**

```pycon
>>> icon = svg_icon(PLAY, color=QColor("#336699"), size=16)
>>> icon.isNull()
False
```
{% endraw %}
