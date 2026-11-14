---
title: alto.ui.colors
parent: api
package: alto.ui
order: 16
permalink: /api/alto.ui.colors/
---
{% raw %}
Mixing colours. The interface blends palette colours to get its soft tints and highlights.

**Examples**

```pycon
>>> blend_name(QColor("#000000"), b=QColor("#ffffff"), t=0.5)
'#808080'
```

## blend

```python
def blend(
    a: QColor,
    *,
    b: QColor,
    t: float,
) -> QColor
```

Return the colour a given fraction of the way from one colour to another.

**Parameters**

- `a` (*QColor*): The colour at 0.
- `b` (*QColor*): The colour at 1. Keyword-only.
- `t` (*float*): How far from `a` to `b`: 0 is `a`, 1 is `b`, 0.5 is halfway. Keyword-only.

**Returns**

- *QColor*: The blended colour.

**Examples**

```pycon
>>> blend(QColor("#000000"), b=QColor("#ffffff"), t=0.0).name()
'#000000'
>>> blend(QColor("#ff0000"), b=QColor("#0000ff"), t=1.0).name()
'#0000ff'
```

## blend_name

```python
def blend_name(
    a: QColor,
    *,
    b: QColor,
    t: float,
) -> str
```

Return the hex name of a blended colour, for use in a stylesheet.

**Parameters**

- `a` (*QColor*): The colour at 0.
- `b` (*QColor*): The colour at 1. Keyword-only.
- `t` (*float*): How far from `a` to `b`. Keyword-only.

**Returns**

- *str*: The colour as '#rrggbb'.

**Examples**

```pycon
>>> blend_name(QColor("#000000"), b=QColor("#ffffff"), t=1.0)
'#ffffff'
```
{% endraw %}
