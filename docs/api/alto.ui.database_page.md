---
title: alto.ui.database_page
parent: api
package: alto.ui
order: 17
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

## QuestionTexts

```python
QuestionTexts()
```

Describes stored questions in words, remembering each one so it is worked out only once.

**Examples**

```pycon
>>> texts = QuestionTexts()
>>> texts("NoteNames", key="k", payload=None)
'(no longer stored)'
```

**Constructor**

Create an empty memory.

**Constructor examples**

```pycon
>>> QuestionTexts()._described
{}
```

## answer_cells

```python
def answer_cells(
    rows: Sequence[sqlite3.Row],
    *,
    names: dict[str, str],
    texts: QuestionTexts,
) -> tuple[list[list[tuple[str, object]]], list[dict]]
```

Turn answers read from the database into the cells of a table, and the hidden details of each row.

**Parameters**

- `rows` (*sequence of sqlite3.Row*): Answers, as `Database.attempt_rows` returns them.
- `names` (*dict of str to str*): The title of each exercise, by class name. Keyword-only.
- `texts` (*QuestionTexts*): Describes each question in words. Keyword-only.

**Returns**

- *tuple of (list, list of dict)*: The cells, in the order of `ANSWER_HEADERS`, and for each row the exercise, the stored question and the lines the question preview shows about the answer.

**Examples**

```pycon
>>> from alto.learning import Database
>>> db = Database()
>>> ada = db.add_profile("Ada")
>>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
...                duration_ms=2500, answered_at=1000.0)
>>> table, hidden = answer_cells(
...     db.attempt_rows(ada.id), names={"NoteNames": "Note Identification"}, texts=QuestionTexts()
... )
>>> [text for text, _ in table[0]][1:]
['Note Identification', '(no longer stored)', 'C', 'Right', '1', '2.5 s']
>>> hidden[0]["exercise"]
'NoteNames'
```

## open_preview

```python
def open_preview(
    index: QModelIndex,
    *,
    names: dict[str, str],
    parent: QWidget,
) -> None
```

Show the question behind a row of an answers table, if its record is still stored.

**Parameters**

- `index` (*QModelIndex*): A cell of the row, in a model whose rows carry `ROW_ROLE` details.
- `names` (*dict of str to str*): The title of each exercise, by class name. Keyword-only.
- `parent` (*QWidget*): The widget the popup belongs to. Keyword-only.

**Examples**

```pycon
>>> model = RowsModel(["Name"], rows=[[("Ada", "Ada")]])
>>> open_preview(model.index(0, 0), names={}, parent=QWidget())  # a row with no stored question shows nothing
```

## AnswerList

```python
AnswerList(
    *,
    names: dict[str, str],
    parent: QWidget | None = None,
)
```

Bases: `QTableView`

A table of answers that sorts when a heading is clicked and opens the question behind a row on a double click.

**Attributes**

- `proxy` (*QSortFilterProxyModel*): Sorts the rows by the values in `SORT_ROLE`.
- `model_` (*RowsModel or None*): The rows being shown; None until `show_answers` is called.

**Examples**

```pycon
>>> table = AnswerList(names={})
>>> table.show_answers([])
>>> table.proxy.rowCount()
0
```

**Constructor**

Create an empty table.

**Parameters**

- `names` (*dict of str to str*): The title of each exercise, by class name. Keyword-only.
- `parent` (*QWidget or None, default None*): The widget that owns the table. Keyword-only.

**Constructor examples**

```pycon
>>> AnswerList(names={}).isSortingEnabled()
True
```

### AnswerList.show_answers

```python
def show_answers(rows: Sequence[sqlite3.Row]) -> None
```

Show answers, newest first.

**Parameters**

- `rows` (*sequence of sqlite3.Row*): Answers, as `Database.attempt_rows` returns them.

**Examples**

```pycon
>>> table = AnswerList(names={})
>>> table.show_answers([])
>>> assert table.model_ is not None
>>> table.model_.headers[:2]
['When', 'Exercise']
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
