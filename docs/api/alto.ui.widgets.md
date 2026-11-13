---
title: alto.ui.widgets
parent: api
package: alto.ui
order: 36
permalink: /api/alto.ui.widgets/
---
{% raw %}
Small widgets shared by several screens: the sidebar toggle and the help button.

**Examples**

```pycon
>>> SidebarToggle().toolTip()
'Hide exercise list'
```

## SidebarToggle

```python
SidebarToggle(parent: QWidget | None = None)
```

Bases: `QToolButton`

A button that shows or hides the exercise list.

Connect to `clicked`; the main window decides what to show and calls `set_open` to match.

**Examples**

```pycon
>>> button = SidebarToggle()
>>> button.toolTip()
'Hide exercise list'
>>> button.set_open(False)
>>> button.toolTip()
'Show exercise list'
```

**Constructor**

Create the toggle, showing the list as open.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the button.

**Constructor examples**

```pycon
>>> SidebarToggle().autoRaise()
True
```

### SidebarToggle.set_open

```python
def set_open(is_open: bool) -> None
```

Show the icon and tooltip for the list being open or closed.

**Parameters**

- `is_open` (*bool*): True if the exercise list is showing.

**Examples**

```pycon
>>> button = SidebarToggle()
>>> button.set_open(False)
>>> button.toolTip()
'Show exercise list'
```

## HelpButton

```python
HelpButton(
    text_provider: Callable[[], str],
    *,
    parent: QWidget | None = None,
)
```

Bases: `QToolButton`

A "?" button that opens a small popover with help text.

Click anywhere else to close it.

**Examples**

```pycon
>>> HelpButton(lambda: "<b>Press the right note.</b>").toolTip()
'How this exercise works'
```

**Constructor**

Create the button.

**Parameters**

- `text_provider` (*callable*): Called with no arguments each time the help is shown, so the text can follow the current settings. It returns simple HTML.
- `parent` (*QWidget or None, default None*): The widget that owns the button. Keyword-only.

**Constructor examples**

```pycon
>>> calls = []
>>> button = HelpButton(lambda: calls.append(1) or "help")
>>> calls  # the text is not asked for until the button is clicked
[]
```

### HelpButton.show_help

```python
def show_help() -> None
```

Open the popover under the button, right-aligned with it.

**Examples**

```pycon
>>> HelpButton(lambda: "<b>Help</b>").show_help()  # doctest: +SKIP
```
{% endraw %}
