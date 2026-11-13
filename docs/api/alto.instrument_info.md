---
title: alto.instrument_info
parent: api
package: alto
order: 2
permalink: /api/alto.instrument_info/
---
{% raw %}
What is known about each instrument's recordings, for the summary shown in the instrument settings.

The facts here come from the sources' own pages (the University of Iowa Musical Instrument Samples). What is on disk
(how many notes, their range, their size) is worked out when the page is shown, not stored here. Pure Python, no Qt.

**Examples**

```pycon
>>> coverage(range(60, 73)).describe()
'13 notes, C4 to C5, every semitone'
```

## InstrumentInfo

```python
InstrumentInfo(
    summary: str,
    *,
    source: str,
    source_url: str,
    performer: str = '',
    recorded: str = '',
    includes: str = '',
    terms: str = IOWA_TERMS,
    note: str = '',
)
```

The facts about where an instrument's recordings came from.

**Attributes**

- `summary` (*str*): One sentence on what the sound is.
- `source` (*str*): Who made the recordings. Keyword-only.
- `source_url` (*str*): Where the source describes them. Keyword-only.
- `performer` (*str, default ""*): Who played. Keyword-only.
- `recorded` (*str, default ""*): When and where it was recorded. Keyword-only.
- `includes` (*str, default ""*): The articulation and dynamic that were used. Keyword-only.
- `terms` (*str*): The terms the recordings may be used under. Keyword-only.
- `note` (*str, default ""*): Anything a user should know about how Alto prepared the recordings. Keyword-only.

**Examples**

```pycon
>>> info = InstrumentInfo("A flute.", source=IOWA, source_url="https://example.org/flute")
>>> info.terms == IOWA_TERMS
True
```

## Coverage

```python
Coverage(
    count: int,
    *,
    lowest: int | None = None,
    highest: int | None = None,
    gaps: int = 0,
)
```

Which notes an instrument has recordings for.

**Attributes**

- `count` (*int*): How many notes have a recording.
- `lowest` (*int or None*): The lowest recorded note, as a MIDI number. Keyword-only.
- `highest` (*int or None*): The highest recorded note, as a MIDI number. Keyword-only.
- `gaps` (*int, default 0*): How many semitones inside the range have no recording. Keyword-only.

**Examples**

```pycon
>>> Coverage(0).describe()
'None installed'
```

### Coverage.installed

```python
@property
def installed() -> bool
```

Report whether any recordings are on disk.

**Returns**

- *bool*: True if at least one note has a recording.

**Examples**

```pycon
>>> Coverage(0).installed, coverage([60]).installed
(False, True)
```

### Coverage.describe

```python
def describe() -> str
```

Describe the coverage in a sentence for the instrument settings.

**Returns**

- *str*: The number of notes, the range, and how complete it is. Missing notes are shifted from a neighbour.

**Examples**

```pycon
>>> coverage(range(60, 73)).describe()
'13 notes, C4 to C5, every semitone'
>>> coverage([60, 62, 64, 65]).describe()
'4 notes, C4 to F4, almost every semitone. The few missing notes are shifted from a neighbour.'
>>> coverage(range(48, 73, 2)).describe()
'13 notes, C3 to C5, about every second semitone. The other notes are shifted from a neighbour.'
```

## coverage

```python
def coverage(midis: Iterable[int]) -> Coverage
```

Summarise the notes that have a recording.

**Parameters**

- `midis` (*iterable of int*): The MIDI numbers of the recorded notes, in any order and with repeats allowed.

**Returns**

- *Coverage*: The count, the range and the number of gaps.

**Examples**

```pycon
>>> coverage([64, 60, 62])
Coverage(count=3, lowest=60, highest=64, gaps=2)
```
{% endraw %}
