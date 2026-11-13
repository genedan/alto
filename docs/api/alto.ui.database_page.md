---
title: alto.ui.database_page
parent: api
package: alto.ui
order: 15
permalink: /api/alto.ui.database_page/
---
{% raw %}
A read-only look at what is stored: every answer, every question's record, and the profiles.

**Examples**

```pycon
>>> len(_when(0.0)[0])  # a timestamp as 'YYYY-MM-DD HH:MM:SS'
19
```

## RowsModel

```python
RowsModel(
    headers: list[str],
    *,
    rows: list[list[tuple[str, object]]],
    numeric: Iterable[int] = (),
    extras: list[dict] | None = None,
    parent: QObject | None = None,
)
```

Bases: `QAbstractTableModel`

Rows of (text shown, value to sort by) cells, as a table model. Numbers are right-aligned.

**Attributes**

- `headers` (*list of str*): The column headings.
- `rows` (*list of list of tuple of (str, object)*): The cells: for each, the text to show and the value to sort by.
- `numeric` (*set of int*): The columns to right-align.
- `extras` (*list of dict*): Something about each row that is not shown, such as the stored question (see `ROW_ROLE`).

**Examples**

```pycon
>>> model = RowsModel(["Name", "Count"], rows=[[("Ada", "Ada"), ("3", 3)]], numeric={1})
>>> model.rowCount(), model.columnCount()
(1, 2)
>>> model.data(model.index(0, 1)), model.data(model.index(0, 1), SORT_ROLE)
('3', 3)
```

**Constructor**

Create the model.

**Parameters**

- `headers` (*list of str*): The column headings.
- `rows` (*list of list of tuple of (str, object)*): The cells. Keyword-only.
- `numeric` (*iterable of int, default ()*): The columns to right-align. Keyword-only.
- `extras` (*list of dict or None, default None*): Something about each row that is not shown, such as the stored question; empty for each row if None. Keyword-only.
- `parent` (*QObject or None, default None*): The owner. Keyword-only.

**Constructor examples**

```pycon
>>> RowsModel(["Name"], rows=[[("Ada", "Ada")]]).extras
[{}]
```

### RowsModel.rowCount

```python
def rowCount(parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int
```

Return the number of rows.

**Parameters**

- `parent` (*QModelIndex or QPersistentModelIndex*): Only the top level has rows: an index that is valid gives 0.

**Returns**

- *int*: The number of rows.

**Examples**

```pycon
>>> RowsModel(["Name"], rows=[[("Ada", "Ada")], [("Ben", "Ben")]]).rowCount()
2
```

### RowsModel.columnCount

```python
def columnCount(parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int
```

Return the number of columns.

**Parameters**

- `parent` (*QModelIndex or QPersistentModelIndex*): Only the top level has columns: an index that is valid gives 0.

**Returns**

- *int*: The number of columns.

**Examples**

```pycon
>>> RowsModel(["Name", "Count"], rows=[]).columnCount()
2
```

### RowsModel.data

```python
def data(
    index: QModelIndex | QPersistentModelIndex,
    role: int = Qt.ItemDataRole.DisplayRole,
) -> object
```

Return one piece of a cell for a role.

**Parameters**

- `index` (*QModelIndex or QPersistentModelIndex*): The cell.
- `role` (*int, default DisplayRole*): What is wanted: the text to show, the value to sort by (`SORT_ROLE`), the alignment, or the row's hidden details (`ROW_ROLE`).

**Returns**

- *object*: The requested data, or None for a role the model does not use.

**Examples**

```pycon
>>> model = RowsModel(["Name", "Count"], rows=[[("Ada", "Ada"), ("3", 3)]], numeric={1})
>>> model.data(model.index(0, 0))
'Ada'
>>> align = Qt.ItemDataRole.TextAlignmentRole
>>> model.data(model.index(0, 1), align) != model.data(model.index(0, 0), align)  # numbers are right-aligned
True
```

### RowsModel.headerData

```python
def headerData(
    section: int,
    orientation: Qt.Orientation,
    role: int = Qt.ItemDataRole.DisplayRole,
) -> object
```

Return a column heading.

**Parameters**

- `section` (*int*): The column.
- `orientation` (*Qt.Orientation*): Only horizontal headings are used.
- `role` (*int, default DisplayRole*): Only the display text is given.

**Returns**

- *object*: The heading, or None for anything else.

**Examples**

```pycon
>>> model = RowsModel(["Name", "Count"], rows=[])
>>> model.headerData(1, Qt.Orientation.Horizontal)
'Count'
```

## DatabasePage

```python
DatabasePage(
    learner: Learner,
    *,
    parent: QWidget | None = None,
)
```

Bases: `QWidget`

The tables behind the app.

Answers and questions are the active profile's own; profiles lists everyone.

**Attributes**

- `back` (*Signal*): Emitted by the Back button and by Escape.
- `learner` (*Learner*): Whose answers and questions are shown.
- `tabs` (*dict of str to QPushButton*): The buttons that choose the table: "answers", "questions" and "profiles".
- `search` (*QLineEdit*): Filters every column at once.
- `view` (*QTableView*): The table.
- `proxy` (*QSortFilterProxyModel*): Sorts and filters the rows.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
>>> page.note.text()
'0 answers by Ada.'
```

**Constructor**

Build the page, showing the answers table.

**Parameters**

- `learner` (*Learner*): Whose data to show.
- `parent` (*QWidget or None, default None*): The widget that owns the page. Keyword-only.

**Constructor examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
>>> page.tabs["answers"].isChecked()
True
```

### DatabasePage.show_table

```python
def show_table(key: str) -> None
```

Show one of the tables.

**Parameters**

- `key` (*str*): "answers", "questions" or "profiles".

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
>>> page.show_table("profiles")
>>> page.note.text()
'1 profile.'
```
{% endraw %}
