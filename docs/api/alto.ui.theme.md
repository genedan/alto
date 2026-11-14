---
title: alto.ui.theme
parent: api
package: alto.ui
order: 37
permalink: /api/alto.ui.theme/
---
{% raw %}
The colour theme: follow the system, or force light or dark.

**Examples**

```pycon
>>> [key for key, label in THEMES]
['system', 'light', 'dark']
```

## saved_theme

```python
def saved_theme() -> str
```

Return the theme the user chose.

**Returns**

- *str*: "system", "light" or "dark"; "system" if nothing valid is saved.

**Examples**

```pycon
>>> save_theme("dark")
>>> saved_theme()
'dark'
>>> save_theme("system")
```

## save_theme

```python
def save_theme(key: str) -> None
```

Remember the theme the user chose.

**Parameters**

- `key` (*str*): "system", "light" or "dark".

**Examples**

```pycon
>>> save_theme("light")
>>> saved_theme()
'light'
>>> save_theme("system")
```

## apply_theme

```python
def apply_theme(key: str) -> None
```

Switch the application's colour scheme and rebuild the stylesheet from the new palette.

**Parameters**

- `key` (*str*): "system" to follow the desktop, "light" or "dark". Anything else follows the system.

**Examples**

```pycon
>>> apply_theme("system")
>>> # noinspection PyUnresolvedReferences
>>> app.styleSheet() != ""
True
```
{% endraw %}
