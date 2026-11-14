---
title: alto.ui.instrument_picker
parent: api
package: alto.ui
order: 22
permalink: /api/alto.ui.instrument_picker/
---
{% raw %}
Choosing the instrument that plays notes, with a summary of what each one is made from.

**Examples**

```pycon
>>> format_size(2_500_000)
'2.5 MB'
>>> sorted(PREVIEW)
[60, 64, 67]
```

## load_instrument

```python
def load_instrument() -> None
```

Apply the saved instrument.

The piano is used if nothing is saved or the saved key is not an instrument.

**Examples**

```pycon
>>> store().setValue("audio/instrument", "flute")
>>> load_instrument()
>>> sounds.instrument
'flute'
>>> store().setValue("audio/instrument", "not an instrument")
>>> load_instrument()
>>> sounds.instrument
'piano'
```

## save_instrument

```python
def save_instrument() -> None
```

Remember the instrument in use.

**Examples**

```pycon
>>> sounds.instrument = "marimba"
>>> save_instrument()
>>> str(store().value("audio/instrument"))
'marimba'
>>> sounds.instrument = "piano"
>>> save_instrument()
```

## tokens

```python
def tokens(widget: QWidget) -> dict[str, str]
```

Return the summary page's colours.

All are mixed from the system palette so they follow its light or dark theme.

**Parameters**

- `widget` (*QWidget*): The widget whose palette to use.

**Returns**

- *dict of str to str*: Colour name to '#rrggbb': accent, accent_soft, muted, line, panel and well, and for each of good, warn and bad a text colour and a soft background (such as good and good_soft).

**Examples**

```pycon
>>> colours = tokens(QWidget())
>>> sorted(colours)[:3]
['accent', 'accent_soft', 'bad']
>>> colours["panel"].startswith("#")
True
```

## format_size

```python
def format_size(nbytes: int) -> str
```

Write a file size the way the instrument page shows it.

**Parameters**

- `nbytes` (*int*): The size in bytes.

**Returns**

- *str*: Megabytes with one decimal from a million bytes, otherwise whole kilobytes (at least 1).

**Examples**

```pycon
>>> format_size(2_500_000), format_size(500_000), format_size(10)
('2.5 MB', '500 KB', '1 KB')
```

## InstrumentPicker

```python
InstrumentPicker(parent: QWidget | None = None)
```

Bases: `QWidget`

The instruments in a box on the left; on the right, what the selected one is made from.

An instrument that can be played in more than one way (the viola, arco or pizzicato) is one entry, and its page has a
'Use this instrument' and a 'Hear it' for each way. 'Hear it' plays a short arpeggio even while sound is muted.

**Attributes**

- `chosen` (*Signal*): Emitted with the key of the instrument that is now in use.
- `groups` (*dict of str to list of Instrument*): The entries in the list, each with the instruments (ways of playing) it holds.
- `list` (*QListWidget*): The box of entries.
- `shown` (*str or None*): The entry whose page is showing.

**Examples**

```pycon
>>> picker = InstrumentPicker()
>>> picker.select("viola_plucked")
>>> picker.shown
'Viola'
```

**Constructor**

Build the picker, showing the page of the instrument in use.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns the picker.

**Constructor examples**

```pycon
>>> picker = InstrumentPicker()
>>> picker.list.count() == len(picker.groups)
True
```

### InstrumentPicker.select

```python
def select(key: str) -> None
```

Show the page of the entry an instrument belongs to.

**Parameters**

- `key` (*str*): An instrument's key.

**Examples**

```pycon
>>> picker = InstrumentPicker()
>>> picker.select("marimba")
>>> picker.shown
'Marimba'
```

### InstrumentPicker.show_group

```python
def show_group(group: str) -> None
```

Fill the summary page for an entry from what is known about it and what is on disk.

**Parameters**

- `group` (*str*): An entry in the list, such as "Flute" or "Viola".

**Examples**

```pycon
>>> picker = InstrumentPicker()
>>> picker.show_group("Flute")
>>> picker.shown
'Flute'
```

### InstrumentPicker.changeEvent

```python
def changeEvent(event: QEvent) -> None
```

Redraw the summary page when the palette changes, so its colours follow the theme.

**Parameters**

- `event` (*QEvent*): The change.

**Examples**

```pycon
>>> picker = InstrumentPicker()
>>> picker.show_group("Flute")
>>> picker.changeEvent(QEvent(QEvent.Type.PaletteChange))
>>> picker.shown
'Flute'
```

### InstrumentPicker.use

```python
def use(key: str) -> None
```

Make an instrument the one for notes and the correct-answer chime.

Nothing happens if it has no recordings installed.

**Parameters**

- `key` (*str*): The instrument's key.

**Examples**

```pycon
>>> picker = InstrumentPicker()
>>> chosen = []
>>> _ = picker.chosen.connect(chosen.append)
>>> picker.use("marimba")
>>> sounds.instrument, chosen
('marimba', ['marimba'])
>>> picker.use("piano")
```

### InstrumentPicker.preview

```python
def preview(key: str) -> None
```

Play a short C major arpeggio in an instrument, even if sound is muted.

**Parameters**

- `key` (*str*): The instrument's key.

**Examples**

```pycon
>>> InstrumentPicker().preview("flute")  # doctest: +SKIP
```
{% endraw %}
