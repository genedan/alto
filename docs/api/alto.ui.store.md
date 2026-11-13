---
title: alto.ui.store
parent: api
package: alto.ui
order: 33
permalink: /api/alto.ui.store/
---
{% raw %}
The application's saved settings (a thin layer over `QSettings`).

**Examples**

```pycon
>>> settings = store()
>>> settings.setValue("demo/count", 3)
>>> int_value(settings, key="demo/count", default=0)
3
>>> settings.remove("demo")
```

## store

```python
def store() -> QSettings
```

Return the app's saved settings.

The first time it is opened under the name "alto" it brings across anything saved under the old name ("mtheory"), so a
rename does not reset anyone's preferences.

**Returns**

- *QSettings*: The settings, kept in the user's configuration folder.

**Examples**

```pycon
>>> settings = store()
>>> settings.setValue("demo/name", "Ada")
>>> str(store().value("demo/name"))
'Ada'
>>> settings.remove("demo")
```

## int_value

```python
def int_value(
    settings: QSettings,
    *,
    key: str,
    default: int,
) -> int
```

Read an integer setting.

`QSettings` hands back whatever was saved, which may be a number or its text.

**Parameters**

- `settings` (*QSettings*): The settings to read.
- `key` (*str*): The setting's name. Keyword-only.
- `default` (*int*): What to return if nothing is saved. Keyword-only.

**Returns**

- *int*: The saved value, or `default` if there is none (or it is not a number, text or similar).

**Raises**

- *ValueError*: If the saved text is not a whole number.

**Examples**

```pycon
>>> settings_ = store()
>>> settings_.setValue("demo/count", "42")
>>> int_value(settings_, key="demo/count", default=0)
42
>>> int_value(settings_, key="demo/missing", default=7)
7
>>> settings_.setValue("demo/count", "many")
>>> int_value(settings_, key="demo/count", default=0)
Traceback (most recent call last):
    ...
ValueError: invalid literal for int() with base 10: 'many'
>>> settings_.remove("demo")
```

## text_value

```python
def text_value(
    settings: QSettings,
    *,
    key: str,
    default: str,
) -> str
```

Read a saved setting as text.

**Parameters**

- `settings` (*QSettings*): The settings to read.
- `key` (*str*): The setting's name. Keyword-only.
- `default` (*str*): What to return if nothing is saved. Keyword-only.

**Returns**

- *str*: The saved text, or `default` if there is none (or it is not text).

**Examples**

```pycon
>>> settings_ = store()
>>> settings_.setValue("demo/name", "viola")
>>> text_value(settings_, key="demo/name", default="piano")
'viola'
>>> text_value(settings_, key="demo/missing", default="piano")
'piano'
>>> settings_.remove("demo")
```
{% endraw %}
