---
title: alto.ui.app_settings
parent: api
package: alto.ui
order: 13
permalink: /api/alto.ui.app_settings/
---
{% raw %}
The application-wide settings dialog: the colour theme, the notation font, the keyboard style and the instrument.

Changes apply as soon as they are made. Each style is a card that previews it.

**Examples**

```pycon
>>> dialog = AppSettingsDialog()
>>> dialog.windowTitle()
'Settings'
>>> dialog.pages.count()  # Appearance and Sound
2
```

## StyleCard

```python
StyleCard(
    style: notation.NotationStyle,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QPushButton`

A selectable tile that previews a notation style: a short phrase on a staff, drawn in that style.

**Attributes**

- `style_key` (*str*): The key of the style the card stands for.
- `staff` (*StaffWidget*): The preview.

**Examples**

```pycon
>>> card = StyleCard(notation.BY_KEY["leland"])
>>> card.style_key, card.isCheckable()
('leland', True)
```

**Constructor**

Build the card for a notation style.

**Parameters**

- `style` (*NotationStyle*): The style to preview; its label and a few words about it are shown under the staff.
- `parent` (*QWidget or None, default None*): The widget that owns the card. Keyword-only.

**Constructor examples**

```pycon
>>> StyleCard(notation.BY_KEY["bravura"]).width()
232
```

## KeyboardCard

```python
KeyboardCard(
    style: keyboard_styles.KeyboardStyle,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QPushButton`

A selectable tile that previews a keyboard style: a short stretch of keys drawn in that style.

**Attributes**

- `style_key` (*str*): The key of the style the card stands for.
- `keys` (*KeyboardWidget*): The preview.

**Examples**

```pycon
>>> card = KeyboardCard(keyboard_styles.BY_KEY["modern"])
>>> card.style_key
'modern'
```

**Constructor**

Build the card for a keyboard style.

**Parameters**

- `style` (*KeyboardStyle*): The style to preview; its label and a few words about it are shown under the keys.
- `parent` (*QWidget or None, default None*): The widget that owns the card. Keyword-only.

**Constructor examples**

```pycon
>>> # noinspection PyUnresolvedReferences
>>> KeyboardCard(keyboard_styles.BY_KEY["classic"]).keys.style_override.key
'classic'
```

### KeyboardCard.show_style

```python
def show_style(style: keyboard_styles.KeyboardStyle) -> None
```

Redraw the preview in a style.

The custom card follows the colours being edited.

**Parameters**

- `style` (*KeyboardStyle*): The style to preview.

**Examples**

```pycon
>>> card = KeyboardCard(keyboard_styles.BY_KEY["classic"])
>>> card.show_style(keyboard_styles.BY_KEY["modern"])
>>> # noinspection PyUnresolvedReferences
>>> card.keys.style_override.key
'modern'
```

## KeyboardBuilder

```python
KeyboardBuilder(parent: QWidget | None = None)
```

Bases: `QFrame`

Rows for colouring each part of a keyboard.

Each has a swatch that opens the colour picker, and chips for colours named after materials. Changing anything selects
the Custom style.

**Attributes**

- `changed` (*Signal*): Emitted after a part is recoloured.
- `swatches` (*dict of str to QPushButton*): The swatch of each part ("naturals", "sharps", "case", "felt" and "caps").

**Examples**

```pycon
>>> builder = KeyboardBuilder()
>>> sorted(builder.swatches)
['caps', 'case', 'felt', 'naturals', 'sharps']
```

**Constructor**

Build the rows and show each part's current colour.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the builder.

**Constructor examples**

```pycon
>>> KeyboardBuilder().swatches["naturals"].width()
46
```

### KeyboardBuilder.refresh

```python
def refresh() -> None
```

Show each part's current colour on its swatch.

**Examples**

```pycon
>>> builder = KeyboardBuilder()
>>> builder.refresh()
>>> builder.swatches["naturals"].text()  # a colour is set, so the swatch shows it, not "none"
''
```

## ThemeCard

```python
ThemeCard(
    key: str,
    *,
    label: str,
    note: str,
    parent: QWidget | None = None,
)
```

Bases: `QPushButton`

A selectable tile that previews a theme: a miniature of the app window in light, in dark, or split for System.

**Attributes**

- `LIGHT, DARK` (*dict of str to str*): The colours of the miniature in each theme.
- `theme_key` (*str*): "system", "light" or "dark".
- `preview` (*QWidget*): The miniature.

**Examples**

```pycon
>>> ThemeCard("dark", label="Dark", note="Always dark.").theme_key
'dark'
```

**Constructor**

Build the card for a theme.

**Parameters**

- `key` (*str*): "system", "light" or "dark".
- `label` (*str*): The name shown under the preview. Keyword-only.
- `note` (*str*): A short explanation shown under the name. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the card. Keyword-only.

**Constructor examples**

```pycon
>>> ThemeCard("system", label="System", note="Follows your desktop.").height()
168
```

## AppSettingsDialog

```python
AppSettingsDialog(parent: QWidget | None = None)
```

Bases: `QDialog`

Application-wide settings. Changes apply immediately.

**Attributes**

- `theme_changed` (*bool*): True once the theme has been changed, so the window can be rebuilt in it.
- `categories` (*QListWidget*): The list of pages on the left: Appearance and Sound.
- `pages` (*QStackedWidget*): The page for the chosen category.
- `instruments` (*InstrumentPicker*): The instrument chooser on the Sound page.

**Examples**

```pycon
>>> dialog = AppSettingsDialog()
>>> dialog.theme_changed
False
```

**Constructor**

Build the dialog with the Appearance page showing.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the dialog.

**Constructor examples**

```pycon
>>> dialog = AppSettingsDialog()
>>> dialog.categories.currentRow()
0
```

### AppSettingsDialog.changeEvent

```python
def changeEvent(event: QEvent) -> None
```

Restyle the segmented control when the palette changes, so it follows the theme.

**Parameters**

- `event` (*QEvent*): The change.

**Examples**

```pycon
>>> dialog = AppSettingsDialog()
>>> dialog.changeEvent(QEvent(QEvent.Type.PaletteChange))
```

### AppSettingsDialog.choose_theme

```python
def choose_theme(key: str) -> None
```

Switch the colour theme, remember it, and note that the window should be rebuilt in it.

**Parameters**

- `key` (*str*): "system", "light" or "dark".

**Examples**

```pycon
>>> dialog = AppSettingsDialog()
>>> dialog.choose_theme("light")
>>> dialog.theme_changed, saved_theme()
(True, 'light')
>>> dialog.choose_theme("system")
```
{% endraw %}
