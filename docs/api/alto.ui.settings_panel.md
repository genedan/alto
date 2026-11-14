---
title: alto.ui.settings_panel
parent: api
package: alto.ui
order: 31
permalink: /api/alto.ui.settings_panel/
---
{% raw %}
The settings panels that slide in beside an exercise, and the small widgets they are built from.

Each exercise with settings has a panel: a menu of rows (Clefs, Range, Key signatures ...) that each lead to a page. Edits
are live: they change the shared settings object, are saved, and a `changed` signal tells the exercise to ask a new
question. This module also loads and saves each exercise's settings.

**Examples**

```pycon
>>> _key_label(2)
'D  ·  2♯'
>>> row = _Row("Clefs")
>>> row.title.text()
'<b>Clefs</b>'
```

## load_note_names

```python
def load_note_names() -> None
```

Load the saved note identification settings into the shared settings object.

Settings saved by an older version, which had a switch between the grand staff and single clefs, are converted. Anything
in the saved data that is not valid is ignored.

**Examples**

```pycon
>>> cfg_ = settings.note_names
>>> cfg_.clefs = {"alto"}
>>> save_note_names()
>>> cfg_.clefs = {"treble"}
>>> load_note_names()
>>> cfg_.clefs
{'alto'}
>>> cfg_.clefs = {"treble", "bass"}
>>> save_note_names()
```

## save_note_names

```python
def save_note_names() -> None
```

Save the note identification settings.

**Examples**

```pycon
>>> cfg_ = settings.note_names
>>> cfg_.naming = "solfege"
>>> save_note_names()
>>> str(store().value("noteNames/naming"))
'solfege'
>>> cfg_.naming = "letters"
>>> save_note_names()
```

## RangeEditor

```python
RangeEditor(
    key: str,
    *,
    low: int,
    high: int,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

A staff showing the lowest and highest note asked for a clef.

Arrows on the left move the lower bound, arrows on the right move the upper bound.

**Attributes**

- `edited` (*Signal*): Emitted with the clef key, the lowest note and the highest note (as staff steps) after a change.
- `key` (*str*): The clef.
- `low` (*int*): The lowest note asked, as a staff step (`Note.diatonic`).
- `high` (*int*): The highest note asked.
- `limits` (*tuple of (int, int)*): The furthest the bounds may go.
- `staff` (*StaffWidget*): Shows the two notes.

**Examples**

```pycon
>>> editor = RangeEditor("treble", low=28, high=34)
>>> editor.caption_text.text()
'<b>C4 – B4</b>'
```

**Constructor**

Build the editor for a clef's range.

**Parameters**

- `key` (*str*): The clef, a key of `RANGE_LIMITS`.
- `low` (*int*): The lowest note asked, as a staff step. Keyword-only.
- `high` (*int*): The highest note asked. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the editor. Keyword-only.

**Constructor examples**

```pycon
>>> RangeEditor("bass", low=14, high=28).limits == settings.RANGE_LIMITS["bass"]
True
```

## KeyDiagram

```python
KeyDiagram(
    keys: set[int] | None = None,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

A small fork showing which key signatures are selected.

C major is on the left, then two rows of seven dots: 1 to 7 sharps on the top row and 1 to 7 flats on the bottom.
Selected keys are filled, the rest are hollow.

**Attributes**

- `DOT, PITCH, ROW_GAP, PAD` (*float*): The dot radius and the spacing, in pixels.
- `keys` (*set of int*): The selected key signatures: sharps if positive, flats if negative.

**Examples**

```pycon
>>> KeyDiagram({0, 2}).toolTip()
'C, D'
```

**Constructor**

Create the diagram.

**Parameters**

- `keys` (*set of int or None, default None*): The key signatures to show as selected.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> KeyDiagram().keys
set()
```

### KeyDiagram.set_keys

```python
def set_keys(keys: set[int]) -> None
```

Choose which key signatures are shown as selected.

**Parameters**

- `keys` (*set of int*): Sharps if positive, flats if negative.

**Examples**

```pycon
>>> diagram = KeyDiagram()
>>> diagram.set_keys({2, -1, 0})
>>> diagram.toolTip()
'C, D, F'
```

### KeyDiagram.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw a dot for each key signature, filled when selected.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> KeyDiagram({0, 1, -1}).grab().isNull()
False
```

## Switch

```python
Switch(parent: QWidget | None = None)
```

Bases: `QAbstractButton`

A pill-shaped on/off switch whose knob slides across when toggled.

**Attributes**

- `W, H` (*int*): The switch's size, in pixels.

**Examples**

```pycon
>>> switch = Switch()
>>> switch.setChecked(True)
>>> switch.isChecked()
True
```

**Constructor**

Create a switch that is off.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns it.

**Constructor examples**

```pycon
>>> Switch().isChecked()
False
```

### Switch.setChecked

```python
def setChecked(on: bool) -> None
```

Turn the switch on or off without animating, as when a setting is loaded.

**Parameters**

- `on` (*bool*): The new state.

**Examples**

```pycon
>>> switch = Switch()
>>> switch.setChecked(True)
>>> switch._pos
1.0
```

### Switch.paintEvent

```python
def paintEvent(_: QPaintEvent) -> None
```

Draw the track, tinted between off and on, and the knob.

**Parameters**

- `_` (*QPaintEvent*): The paint request; the whole widget is always redrawn.

**Examples**

```pycon
>>> Switch().grab().isNull()
False
```

### Switch.sizeHint

```python
def sizeHint() -> QSize
```

Return the switch's fixed size.

**Returns**

- *QSize*: `W` by `H`.

**Examples**

```pycon
>>> Switch().sizeHint()
PySide6.QtCore.QSize(42, 24)
```

## SlideStack

```python
SlideStack(parent: QWidget | None = None)
```

Bases: `QStackedWidget`

A stacked widget whose pages slide in from the right (going deeper) or the left (going back).

**Examples**

```pycon
>>> stack = SlideStack()
>>> _ = stack.addWidget(QWidget())
>>> _ = stack.addWidget(QWidget())
>>> stack.sliding
False
```

**Constructor**

Create an empty stack.

**Parameters**

- `parent` (*QWidget or None, default None*): The widget that owns it.

**Constructor examples**

```pycon
>>> SlideStack().count()
0
```

### SlideStack.sliding

```python
@property
def sliding() -> bool
```

Report whether a page is sliding in.

**Returns**

- *bool*: True from the start of a slide until it finishes.

**Examples**

```pycon
>>> SlideStack().sliding
False
```

### SlideStack.slide_to

```python
def slide_to(index: int) -> None
```

Slide to another page.

Going to a later page slides it in from the right and going back slides it in from the left. A request made during a
slide, or for the page already showing, is ignored.

**Parameters**

- `index` (*int*): The page to go to.

**Examples**

```pycon
>>> stack = SlideStack()
>>> _ = stack.addWidget(QWidget())
>>> _ = stack.addWidget(QWidget())
>>> stack.slide_to(1)
>>> stack.sliding
True
```

## ExerciseSettingsPanel

```python
class ExerciseSettingsPanel(QWidget)
```

What every exercise's settings pane has in common: it says when a setting has been edited.

**Attributes**

- `changed` (*Signal*): Emitted after any setting is edited.

**Examples**

```pycon
>>> panel = ExerciseSettingsPanel()
>>> got = []
>>> _ = panel.changed.connect(lambda: got.append(1))
>>> panel.changed.emit()
True
>>> got
[1]
```

## NoteNameSettingsPanel

```python
NoteNameSettingsPanel(
    cfg: NoteNameSettings,
    *,
    parent: QWidget | None = None,
)
```

Bases: `ExerciseSettingsPanel`

The settings of the note identification exercise: a menu leading to a page for each group of settings.

Two layers: the menu (Clefs, Range, Key signatures, Note values, Note names and an Accidentals switch) and a page for each.
Edits are live: each changes the settings, saves them and emits `changed`.

**Attributes**

- `cfg` (*NoteNameSettings*): The settings being edited.
- `stack` (*SlideStack*): The menu and its pages.
- `boxes` (*dict of str to QCheckBox*): The clef checkboxes.
- `key_boxes` (*dict of int to QCheckBox*): The key signature checkboxes.
- `value_boxes` (*dict of str to QCheckBox*): The note value checkboxes.
- `naming_radios` (*dict of str to QRadioButton*): The letters and solfège choices.
- `range_editors` (*dict of str to RangeEditor*): The range editor of each clef in use, built when the Range page opens.

**Examples**

```pycon
>>> panel = NoteNameSettingsPanel(NoteNameSettings())
>>> panel.cfg.active_clefs()
['treble', 'bass']
```

**Constructor**

Build the panel for a set of settings.

**Parameters**

- `cfg` (*NoteNameSettings*): The settings to edit.
- `parent` (*QWidget or None, default None*): The widget that owns the panel. Keyword-only.

**Constructor examples**

```pycon
>>> panel = NoteNameSettingsPanel(NoteNameSettings())
>>> panel.stack.count()  # the menu and five pages
6
```

## load_keyboard

```python
def load_keyboard() -> None
```

Load the saved keyboard exercise settings into the shared settings object.

A saved range that is not a valid span of keys, or a key list with nothing usable in it, is ignored.

**Examples**

```pycon
>>> cfg_ = settings.keyboard
>>> cfg_.require_octave = True
>>> save_keyboard()
>>> cfg_.require_octave = False
>>> load_keyboard()
>>> cfg_.require_octave
True
>>> cfg_.require_octave = False
>>> save_keyboard()
```

## save_keyboard

```python
def save_keyboard() -> None
```

Save the keyboard exercise settings.

**Examples**

```pycon
>>> cfg_ = settings.keyboard
>>> save_keyboard()
>>> int(store().value("keyboard/low")) == cfg_.low
True
```

## KeyChecklist

```python
KeyChecklist(
    selected: set[int],
    *,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

Checkboxes for the 15 major keys, flats on the left and sharps on the right.

At least one stays checked. Each is labelled with a picture of its signature.

**Attributes**

- `changed` (*Signal*): Emitted after a box is ticked or unticked.
- `boxes` (*dict of int to QCheckBox*): The checkbox of each key signature, from -7 (seven flats) to 7 (seven sharps).

**Examples**

```pycon
>>> KeyChecklist({0, 2}).selected() == {0, 2}
True
```

**Constructor**

Build the checklist.

**Parameters**

- `selected` (*set of int*): The key signatures to tick at first.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> len(KeyChecklist({0}).boxes)
15
```

### KeyChecklist.selected

```python
def selected() -> set[int]
```

Return the ticked key signatures.

**Returns**

- *set of int*: Sharps if positive, flats if negative.

**Examples**

```pycon
>>> KeyChecklist({-3, 1}).selected() == {-3, 1}
True
```

## KeySignaturePage

```python
KeySignaturePage(
    enabled: bool,
    *,
    selected: set[int],
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

The key signature sub-page: a switch for using key signatures at all, and the keys to draw from.

**Attributes**

- `changed` (*Signal*): Emitted after the switch or a key is changed.
- `switch_row` (*_ToggleRow*): The "Use key signatures" switch.
- `checklist` (*KeyChecklist*): The keys; only enabled while the switch is on.

**Examples**

```pycon
>>> page = KeySignaturePage(True, selected={0, 1})
>>> page.enabled(), page.selected() == {0, 1}
(True, True)
```

**Constructor**

Build the page.

**Parameters**

- `enabled` (*bool*): Whether key signatures are on.
- `selected` (*set of int*): The key signatures to tick at first. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> page = KeySignaturePage(False, selected={0})
>>> page.checklist.isEnabled()
False
```

### KeySignaturePage.enabled

```python
def enabled() -> bool
```

Report whether key signatures are switched on.

**Returns**

- *bool*: True if the switch is on.

**Examples**

```pycon
>>> KeySignaturePage(True, selected={0}).enabled()
True
```

### KeySignaturePage.selected

```python
def selected() -> set[int]
```

Return the ticked key signatures.

**Returns**

- *set of int*: Sharps if positive, flats if negative.

**Examples**

```pycon
>>> KeySignaturePage(True, selected={-2, 0}).selected() == {-2, 0}
True
```

## KeyboardSettingsPanel

```python
KeyboardSettingsPanel(
    cfg: settings.KeyboardSettings,
    *,
    parent: QWidget | None = None,
)
```

Bases: `ExerciseSettingsPanel`

The settings of the keyboard exercise: a menu with a page for the range of keys.

The menu has Range, Black keys, Octave number and Key signatures. Edits are live: each changes the settings, saves them
and emits `changed`.

**Attributes**

- `cfg` (*KeyboardSettings*): The settings being edited.
- `stack` (*SlideStack*): The menu and its pages.
- `span` (*KeyboardSpan*): The miniature piano on the Range page, which can be dragged to choose the keys.
- `low_label, high_label` (*QLabel*): The names of the lowest and highest key asked.
- `key_page` (*KeySignaturePage*): The key signature sub-page.

**Examples**

```pycon
>>> panel = KeyboardSettingsPanel(settings.KeyboardSettings())
>>> panel.low_label.text(), panel.high_label.text()
('C3', 'C5')
```

**Constructor**

Build the panel for a set of settings.

**Parameters**

- `cfg` (*KeyboardSettings*): The settings to edit.
- `parent` (*QWidget or None, default None*): The widget that owns the panel. Keyword-only.

**Constructor examples**

```pycon
>>> KeyboardSettingsPanel(settings.KeyboardSettings()).stack.count()  # the menu, the range and the keys
3
```

## load_construction

```python
def load_construction() -> None
```

Load the saved note construction settings into the shared settings object.

**Examples**

```pycon
>>> store().setValue("construction/accidentals", "true")
>>> load_construction()
>>> settings.construction.accidentals
True
>>> store().setValue("construction/accidentals", "false")
>>> load_construction()
```

## NoteConstructionSettingsPanel

```python
NoteConstructionSettingsPanel(
    cfg: settings.ConstructionSettings,
    *,
    parent: QWidget | None = None,
)
```

Bases: `ExerciseSettingsPanel`

The settings of the note construction exercise: a menu with a page for the staff and one for the keys.

The menu has Staff, Accidentals, Key signatures and Keys. Edits are live: each changes the settings, saves them and
emits `changed`.

**Attributes**

- `cfg` (*ConstructionSettings*): The settings being edited.
- `stack` (*SlideStack*): The menu and its pages.
- `boxes` (*dict of str to QCheckBox*): The clef checkboxes, including the grand staff.
- `key_page` (*KeySignaturePage*): The key signature sub-page.

**Examples**

```pycon
>>> panel = NoteConstructionSettingsPanel(settings.ConstructionSettings())
>>> sorted(panel.boxes)[:3]
['alto', 'baritone', 'bass']
```

**Constructor**

Build the panel for a set of settings.

**Parameters**

- `cfg` (*ConstructionSettings*): The settings to edit.
- `parent` (*QWidget or None, default None*): The widget that owns the panel. Keyword-only.

**Constructor examples**

```pycon
>>> NoteConstructionSettingsPanel(settings.ConstructionSettings()).stack.count()
3
```

## load_arpeggio

```python
def load_arpeggio() -> None
```

Load the saved arpeggio settings into the shared settings object.

Anything in the saved data that is not valid is ignored, and a list with nothing valid in it leaves the setting as it was.

**Examples**

```pycon
>>> store().setValue("arpeggio/types", "major")
>>> load_arpeggio()
>>> settings.arpeggio.types
{'major'}
>>> settings.arpeggio.types = {"major", "minor", "dominant 7th", "diminished 7th"}
>>> store().setValue("arpeggio/types", ",".join(settings.arpeggio.active_types()))
```

## ChoiceChecklist

```python
ChoiceChecklist(
    groups: list[tuple[str, list[tuple[object, str]]]],
    *,
    selected: set,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

Checkboxes for a list of choices, optionally under small headings. At least one stays checked.

**Attributes**

- `changed` (*Signal*): Emitted after a box is ticked or unticked.
- `boxes` (*dict*): The checkbox of each choice, by its key.

**Examples**

```pycon
>>> groups = [("Triads", [("major", "Major"), ("minor", "Minor")]), ("", [("x", "Other")])]
>>> checklist = ChoiceChecklist(groups, selected={"major"})
>>> checklist.selected()
{'major'}
```

**Constructor**

Build the checklist.

**Parameters**

- `groups` (*list of tuple of (str, list of tuple of (object, str))*): The headings and, under each, the choices as (key, label); an empty heading shows none.
- `selected` (*set*): The keys to tick at first. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns it. Keyword-only.

**Constructor examples**

```pycon
>>> checklist = ChoiceChecklist([("", [(0, "Root"), (1, "1st")])], selected={0})
>>> # noinspection PyTypeChecker
>>> sorted(checklist.boxes)
[0, 1]
```

### ChoiceChecklist.selected

```python
def selected() -> set
```

Return the ticked choices.

**Returns**

- *set*: The keys of the ticked boxes.

**Examples**

```pycon
>>> ChoiceChecklist([("", [(0, "Root"), (1, "1st")])], selected={0, 1}).selected()
{0, 1}
```

## ArpeggioSettingsPanel

```python
ArpeggioSettingsPanel(
    cfg: settings.ArpeggioSettings,
    *,
    parent: QWidget | None = None,
)
```

Bases: `ExerciseSettingsPanel`

The settings of the arpeggio exercise: a menu with a page for each group of settings.

The menu has Staff, Arpeggio types, Inversions and Key signatures. Edits are live: each changes the settings, saves them
and emits `changed`.

**Attributes**

- `cfg` (*ArpeggioSettings*): The settings being edited.
- `stack` (*SlideStack*): The menu and its pages.
- `boxes` (*dict of str to QCheckBox*): The clef checkboxes.
- `types` (*ChoiceChecklist*): The chord types.
- `inversions` (*ChoiceChecklist*): The inversions.
- `key_page` (*KeySignaturePage*): The key signature sub-page.

**Examples**

```pycon
>>> panel = ArpeggioSettingsPanel(settings.ArpeggioSettings())
>>> panel.types_row.value.text()
'4 of 9'
```

**Constructor**

Build the panel for a set of settings.

**Parameters**

- `cfg` (*ArpeggioSettings*): The settings to edit.
- `parent` (*QWidget or None, default None*): The widget that owns the panel. Keyword-only.

**Constructor examples**

```pycon
>>> ArpeggioSettingsPanel(settings.ArpeggioSettings()).stack.count()  # the menu and four pages
5
```

## load_key_signatures

```python
def load_key_signatures() -> None
```

Load the saved key signature exercise settings into the shared settings object.

Anything in the saved data that is not valid is ignored, and a list with nothing valid in it leaves the setting as it was.

**Examples**

```pycon
>>> store().setValue("keySignatures/questions", "count")
>>> load_key_signatures()
>>> settings.key_signatures.questions
{'count'}
>>> settings.key_signatures.questions = {"read", "count"}
>>> store().setValue("keySignatures/questions", "read,count")
```

## KeySignatureSettingsPanel

```python
KeySignatureSettingsPanel(
    cfg: settings.KeySignatureSettings,
    *,
    parent: QWidget | None = None,
)
```

Bases: `ExerciseSettingsPanel`

The settings of the key signatures exercise: a menu with a page for each group of settings.

The menu has Questions, Staff, Scales and Key signatures. Edits are live: each changes the settings, saves them and
emits `changed`.

**Attributes**

- `cfg` (*KeySignatureSettings*): The settings being edited.
- `stack` (*SlideStack*): The menu and its pages.
- `questions` (*ChoiceChecklist*): Reading a signature, counting its accidentals, or both.
- `boxes` (*dict of str to QCheckBox*): The clef checkboxes.
- `modes` (*ChoiceChecklist*): The scales (major, minor and the modes).
- `key_list` (*KeyChecklist*): The key signatures.

**Examples**

```pycon
>>> panel = KeySignatureSettingsPanel(settings.KeySignatureSettings())
>>> panel.questions_row.value.text()
'Both'
```

**Constructor**

Build the panel for a set of settings.

**Parameters**

- `cfg` (*KeySignatureSettings*): The settings to edit.
- `parent` (*QWidget or None, default None*): The widget that owns the panel. Keyword-only.

**Constructor examples**

```pycon
>>> KeySignatureSettingsPanel(settings.KeySignatureSettings()).stack.count()  # the menu and four pages
5
```

## settings_inversion_names

```python
def settings_inversion_names() -> tuple[str, ...]
```

Return the inversions as they are written in the settings.

**Returns**

- *tuple of str*: 'Root position', '1st inversion', '2nd inversion' and '3rd inversion'.

**Examples**

```pycon
>>> settings_inversion_names()
('Root position', '1st inversion', '2nd inversion', '3rd inversion')
```

## settings_panel_for

```python
def settings_panel_for(exercise: Exercise) -> ExerciseSettingsPanel | None
```

Return the settings panel for an exercise.

**Parameters**

- `exercise` (*Exercise*): The exercise.

**Returns**

- *ExerciseSettingsPanel or None*: A panel with a `changed` signal, or None for an exercise with no settings.

**Examples**

```pycon
>>> from alto.exercises.library import IntervalNames, NoteNames
>>> type(settings_panel_for(NoteNames())).__name__
'NoteNameSettingsPanel'
>>> settings_panel_for(IntervalNames()) is None
True
```
{% endraw %}
