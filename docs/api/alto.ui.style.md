---
title: alto.ui.style
parent: api
package: alto.ui
order: 34
permalink: /api/alto.ui.style/
---
{% raw %}
Application-wide stylesheet: rounded corners on buttons, panes, lists and scroll bars.

Colours come from the palette so it follows the system light/dark theme.

**Examples**

```pycon
>>> RADIUS
10
```

## app_style

```python
def app_style(palette: QPalette) -> str
```

Build the stylesheet for a palette.

White-filled buttons with a dark border and a heavier lower edge, rounded check boxes and lists, and so on, with colours
taken from the palette.

**Parameters**

- `palette` (*QPalette*): The palette to take colours from, so the style follows the light or dark theme.

**Returns**

- *str*: Qt style sheet text.

**Examples**

```pycon
>>> from PySide6.QtWidgets import QApplication
>>> sheet = app_style(QApplication.palette())
>>> "QPushButton" in sheet and "border-radius" in sheet
True
```
{% endraw %}
