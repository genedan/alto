---
title: alto.settings
parent: api
package: alto
order: 3
permalink: /api/alto.settings/
---
{% raw %}
User settings. Pure Python (no Qt); persistence lives in ui/settings_panel.py.

Each exercise with settings has a small dataclass here (`NoteNameSettings`, `KeyboardSettings` and so on) and one shared
instance of it (`note_names`, `keyboard` ...) that the exercise and its settings panel both read and write.

**Examples**

```pycon
>>> NoteNameSettings().active_clefs()
['treble', 'bass']
>>> spell(Note.parse("F#4"))
'F♯'
```

## spell

```python
def spell(
    note: Note,
    *,
    naming: str = 'letters',
) -> str
```

Return the pitch-class name of a note in the chosen naming system.

**Parameters**

- `note` (*Note*): The note.
- `naming` (*str, default "letters"*): "letters" for C D E, or "solfege" for Do Re Mi. Keyword-only.

**Returns**

- *str*: The name with its accidental, without the octave.

**Examples**

```pycon
>>> spell(Note.parse("F#4"))
'F♯'
>>> spell(Note.parse("F#4"), naming="solfege")
'Fa♯'
```

## diatonic_name

```python
def diatonic_name(d: int) -> str
```

Return the name and octave of the natural note on a staff step.

**Parameters**

- `d` (*int*): The staff-step index (see `Note.diatonic`).

**Returns**

- *str*: For example 'E4'.

**Examples**

```pycon
>>> diatonic_name(30)
'E4'
```

## NoteNameSettings

```python
NoteNameSettings(
    clefs: set[str] = field(default_factory=lambda: {'treble', 'bass'}),
    *,
    ranges: dict[str, tuple[int, int]] = field(default_factory=dict),
    key_signatures: set[int] = field(default_factory=lambda: {0}),
    note_values: set[str] = field(default_factory=lambda: {'whole'}),
    naming: str = 'letters',
    accidentals: bool = False,
)
```

The settings of the note identification exercise.

**Attributes**

- `clefs` (*set of str*): The clefs to ask on, any of `RANGE_KEYS`, so "grand" is allowed.
- `ranges` (*dict of str to tuple of (int, int)*): Overrides of `DEFAULT_RANGES`, as inclusive staff-step ranges. Keyword-only.
- `key_signatures` (*set of int*): The keys to use, as sharps (positive) or flats (negative). Keyword-only.
- `note_values` (*set of str*): The note values to draw, from `NOTE_VALUES`. Keyword-only.
- `naming` (*str, default "letters"*): A key of `NAMINGS`. Keyword-only.
- `accidentals` (*bool, default False*): Also ask notes with explicit sharps, flats and naturals. Keyword-only.

**Examples**

```pycon
>>> cfg = NoteNameSettings(clefs={"bass"}, key_signatures={2})
>>> cfg.active_clefs(), cfg.active_keys()
(['bass'], [2])
```

### NoteNameSettings.active_clefs

```python
def active_clefs() -> list[str]
```

Return the clefs to draw from, in canonical order.

**Returns**

- *list of str*: The chosen clefs, or the treble clef if none are chosen.

**Examples**

```pycon
>>> NoteNameSettings(clefs={"grand", "tenor"}).active_clefs()
['tenor', 'grand']
>>> NoteNameSettings(clefs=set()).active_clefs()
['treble']
```

### NoteNameSettings.active_keys

```python
def active_keys() -> list[int]
```

Return the key signatures to draw from, lowest first.

**Returns**

- *list of int*: Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

**Examples**

```pycon
>>> NoteNameSettings(key_signatures={2, -1}).active_keys()
[-1, 2]
```

### NoteNameSettings.active_values

```python
def active_values() -> list[str]
```

Return the note values to draw, from longest to shortest.

**Returns**

- *list of str*: The chosen values in the order of `NOTE_VALUES`, or whole notes if none are chosen.

**Examples**

```pycon
>>> NoteNameSettings(note_values={"half", "whole"}).active_values()
['whole', 'half']
```

### NoteNameSettings.range_for

```python
def range_for(clef: str) -> tuple[int, int]
```

Return the range of notes that may be asked on a clef.

**Parameters**

- `clef` (*str*): A key of `DEFAULT_RANGES`.

**Returns**

- *tuple of (int, int)*: The lowest and highest staff step, inclusive; the user's override if there is one, otherwise the default.

**Examples**

```pycon
>>> NoteNameSettings().range_for("treble")
(22, 52)
>>> NoteNameSettings(ranges={"treble": (40, 30)}).range_for("treble")  # given the wrong way round
(30, 40)
```

## key_name

```python
def key_name(midi: int) -> str
```

Return the name of a MIDI note with its octave, black keys as sharps.

**Parameters**

- `midi` (*int*): The MIDI note number.

**Returns**

- *str*: For example 'C4' for 60 and 'C♯4' for 61.

**Examples**

```pycon
>>> key_name(60), key_name(61)
('C4', 'C♯4')
```

## KeyboardSettings

```python
KeyboardSettings(
    black_keys: bool = True,
    *,
    require_octave: bool = False,
    low: int = KEYBOARD_DEFAULT[0],
    high: int = KEYBOARD_DEFAULT[1],
    key_signature: bool = False,
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3}),
)
```

The settings of the keyboard identification exercise.

**Attributes**

- `black_keys` (*bool, default True*): Also ask the black keys, answered by either enharmonic name.
- `require_octave` (*bool, default False*): The answer must include the octave number as well. Keyword-only.
- `low` (*int*): The lowest key asked, as a MIDI number. Keyword-only.
- `high` (*int*): The highest key asked, as a MIDI number, inclusive. Keyword-only.
- `key_signature` (*bool, default False*): Show a key signature, and require the name that fits it (no enharmonic spelling). Keyword-only.
- `keys` (*set of int*): The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

**Examples**

```pycon
>>> cfg = KeyboardSettings()
>>> key_name(cfg.low), key_name(cfg.high)
('C3', 'C5')
```

### KeyboardSettings.active_keys

```python
def active_keys() -> list[int]
```

Return the key signatures to draw from, lowest first.

**Returns**

- *list of int*: Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

**Examples**

```pycon
>>> KeyboardSettings().active_keys()
[-3, -2, -1, 0, 1, 2, 3]
```

## ConstructionSettings

```python
ConstructionSettings(
    clefs: set[str] = field(default_factory=lambda: {'treble', 'bass'}),
    *,
    accidentals: bool = False,
    key_signature: bool = False,
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3}),
)
```

The settings of the note construction exercise.

**Attributes**

- `clefs` (*set of str*): The clefs to ask on, any of `RANGE_KEYS`, so "grand" is allowed.
- `accidentals` (*bool, default False*): Also ask for sharps and flats, which the answer then has to include. Keyword-only.
- `key_signature` (*bool, default False*): Draw a key signature; it applies to the note unless the note is given its own sign. Keyword-only.
- `keys` (*set of int*): The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

**Examples**

```pycon
>>> ConstructionSettings(clefs={"grand"}).active_clefs()
['grand']
```

### ConstructionSettings.active_clefs

```python
def active_clefs() -> list[str]
```

Return the clefs to draw from, in canonical order.

**Returns**

- *list of str*: The chosen clefs, or the treble clef if none are chosen.

**Examples**

```pycon
>>> ConstructionSettings().active_clefs()
['treble', 'bass']
```

### ConstructionSettings.active_keys

```python
def active_keys() -> list[int]
```

Return the key signatures to draw from, lowest first.

**Returns**

- *list of int*: Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

**Examples**

```pycon
>>> ConstructionSettings(keys={3, -2}).active_keys()
[-2, 3]
```

## ArpeggioSettings

```python
ArpeggioSettings(
    clefs: set[str] = field(default_factory=lambda: {'treble', 'bass'}),
    *,
    types: set[str] = field(default_factory=lambda: {'major', 'minor', 'dominant 7th', 'diminished 7th'}),
    inversions: set[int] = field(default_factory=lambda: set(INVERSIONS)),
    key_signature: bool = False,
    keys: set[int] = field(default_factory=lambda: {-3, -2, -1, 0, 1, 2, 3}),
)
```

The settings of the arpeggio identification exercise.

**Attributes**

- `clefs` (*set of str*): The clefs to draw on, any of `CLEFS`.
- `types` (*set of str*): The chord types to ask, from `ARPEGGIO_TYPES`. Keyword-only.
- `inversions` (*set of int*): The inversions to ask: 0 for root position up to 3 for the third inversion. Keyword-only.
- `key_signature` (*bool, default False*): Draw a key signature, so the arpeggio only gets signs where it differs from it. Keyword-only.
- `keys` (*set of int*): The key signatures to draw from, as sharps (positive) or flats (negative). Keyword-only.

**Examples**

```pycon
>>> ArpeggioSettings().active_types()
['major', 'minor', 'dominant 7th', 'diminished 7th']
```

### ArpeggioSettings.active_clefs

```python
def active_clefs() -> list[str]
```

Return the clefs to draw from, in canonical order.

**Returns**

- *list of str*: The chosen clefs, or the treble clef if none are chosen.

**Examples**

```pycon
>>> ArpeggioSettings(clefs={"tenor", "alto"}).active_clefs()
['alto', 'tenor']
```

### ArpeggioSettings.active_types

```python
def active_types() -> list[str]
```

Return the chord types to ask, triads first and then seventh chords.

**Returns**

- *list of str*: The chosen types in the order of `ARPEGGIO_TYPES`, or "major" if none are chosen.

**Examples**

```pycon
>>> ArpeggioSettings(types={"minor 7th", "major"}).active_types()
['major', 'minor 7th']
```

### ArpeggioSettings.active_inversions

```python
def active_inversions() -> list[int]
```

Return the inversions to ask, root position first.

**Returns**

- *list of int*: The chosen inversions, or root position (0) if none are chosen.

**Examples**

```pycon
>>> ArpeggioSettings(inversions={2, 0}).active_inversions()
[0, 2]
```

### ArpeggioSettings.inversions_for

```python
def inversions_for(chord_type: str) -> list[int]
```

Return the inversions that can be asked for a chord type.

A triad has no third inversion. If none of the chosen inversions applies (only the third, for a triad), root position is
used.

**Parameters**

- `chord_type` (*str*): A key of `CHORDS`, such as "major" or "dominant 7th".

**Returns**

- *list of int*: The inversions to choose from.

**Examples**

```pycon
>>> cfg = ArpeggioSettings()
>>> cfg.inversions_for("major"), cfg.inversions_for("dominant 7th")
([0, 1, 2], [0, 1, 2, 3])
>>> ArpeggioSettings(inversions={3}).inversions_for("major")
[0]
```

### ArpeggioSettings.active_keys

```python
def active_keys() -> list[int]
```

Return the key signatures to draw from, lowest first.

**Returns**

- *list of int*: Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

**Examples**

```pycon
>>> ArpeggioSettings(keys={1}).active_keys()
[1]
```

## KeySignatureSettings

```python
KeySignatureSettings(
    questions: set[str] = field(default_factory=lambda: {'read', 'count'}),
    *,
    clefs: set[str] = field(default_factory=lambda: {'treble', 'bass'}),
    modes: set[str] = field(default_factory=lambda: {'Major (Ionian)', 'Natural minor (Aeolian)'}),
    keys: set[int] = field(default_factory=lambda: set(range(-7, 8))),
)
```

The settings of the key signatures exercise.

**Attributes**

- `questions` (*set of str*): The kinds of question, keys of `KEY_QUESTIONS`: "read" a signature or "count" its sharps and flats.
- `clefs` (*set of str*): The clefs a signature is drawn on, any of `CLEFS`. Keyword-only.
- `modes` (*set of str*): The scales to ask about, from `KEY_MODES`. Keyword-only.
- `keys` (*set of int*): The key signatures asked, as sharps (positive) or flats (negative). Keyword-only.

**Examples**

```pycon
>>> cfg = KeySignatureSettings()
>>> cfg.active_questions(), len(cfg.active_keys())
(['read', 'count'], 15)
```

### KeySignatureSettings.active_questions

```python
def active_questions() -> list[str]
```

Return the kinds of question to ask.

**Returns**

- *list of str*: The chosen kinds in the order of `KEY_QUESTIONS`, or "read" if none are chosen.

**Examples**

```pycon
>>> KeySignatureSettings(questions={"count"}).active_questions()
['count']
```

### KeySignatureSettings.active_clefs

```python
def active_clefs() -> list[str]
```

Return the clefs to draw signatures on, in canonical order.

**Returns**

- *list of str*: The chosen clefs, or the treble clef if none are chosen.

**Examples**

```pycon
>>> KeySignatureSettings().active_clefs()
['treble', 'bass']
```

### KeySignatureSettings.active_modes

```python
def active_modes() -> list[str]
```

Return the scales to ask about, in the order of `KEY_MODES`.

**Returns**

- *list of str*: The chosen modes, or major if none are chosen.

**Examples**

```pycon
>>> KeySignatureSettings().active_modes()
['Major (Ionian)', 'Natural minor (Aeolian)']
```

### KeySignatureSettings.active_keys

```python
def active_keys() -> list[int]
```

Return the key signatures to ask about, lowest first.

**Returns**

- *list of int*: Sharps (positive) or flats (negative); no sharps or flats if none are chosen.

**Examples**

```pycon
>>> KeySignatureSettings(keys={3, -4}).active_keys()
[-4, 3]
```
{% endraw %}
