"""
A read-only look at what is stored: every answer, every question's record, and the profiles.

Examples
--------
>>> len(_when(0.0)[0])  # a timestamp as 'YYYY-MM-DD HH:MM:SS'
19
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import (
    Iterable,
    Sequence,
)
from datetime import datetime

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from alto.exercises import REGISTRY
from alto.exercises.base import Question
from alto.learning import (
    Learner,
    stats,
)
from alto.ui.question_preview import QuestionPreview

ROW_LIMIT = 10000
SORT_ROLE = Qt.ItemDataRole.UserRole
ROW_ROLE = Qt.ItemDataRole.UserRole + 1  # a row's hidden details


class RowsModel(QAbstractTableModel):
    """
    Rows of (text shown, value to sort by) cells, as a table model. Numbers are right-aligned.

    Attributes
    ----------
    headers : list of str
        The column headings.
    rows : list of list of tuple of (str, object)
        The cells: for each, the text to show and the value to sort by.
    numeric : set of int
        The columns to right-align.
    extras : list of dict
        Something about each row that is not shown, such as the stored question (see `ROW_ROLE`).

    Examples
    --------
    >>> model = RowsModel(["Name", "Count"], rows=[[("Ada", "Ada"), ("3", 3)]], numeric={1})
    >>> model.rowCount(), model.columnCount()
    (1, 2)
    >>> model.data(model.index(0, 1)), model.data(model.index(0, 1), SORT_ROLE)
    ('3', 3)
    """

    def __init__(
        self,
        headers: list[str],
        *,
        rows: list[list[tuple[str, object]]],
        numeric: Iterable[int] = (),
        extras: list[dict] | None = None,
        parent: QObject | None = None,
    ) -> None:
        """
        Create the model.

        Parameters
        ----------
        headers : list of str
            The column headings.
        rows : list of list of tuple of (str, object)
            The cells. Keyword-only.
        numeric : iterable of int, default ()
            The columns to right-align. Keyword-only.
        extras : list of dict or None, default None
            Something about each row that is not shown, such as the stored question; empty for each row if None. Keyword-only.
        parent : QObject or None, default None
            The owner. Keyword-only.

        Examples
        --------
        >>> RowsModel(["Name"], rows=[[("Ada", "Ada")]]).extras
        [{}]
        """
        super().__init__(parent)
        self.headers, self.rows, self.numeric = headers, rows, set(numeric)
        self.extras = extras or [{} for _ in rows]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """
        Return the number of rows.

        Parameters
        ----------
        parent : QModelIndex or QPersistentModelIndex
            Only the top level has rows: an index that is valid gives 0.

        Returns
        -------
        int
            The number of rows.

        Examples
        --------
        >>> RowsModel(["Name"], rows=[[("Ada", "Ada")], [("Ben", "Ben")]]).rowCount()
        2
        """
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        """
        Return the number of columns.

        Parameters
        ----------
        parent : QModelIndex or QPersistentModelIndex
            Only the top level has columns: an index that is valid gives 0.

        Returns
        -------
        int
            The number of columns.

        Examples
        --------
        >>> RowsModel(["Name", "Count"], rows=[]).columnCount()
        2
        """
        return 0 if parent.isValid() else len(self.headers)

    def data(  # noqa: PLR0917  (Qt calls this override with positional arguments)
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        """
        Return one piece of a cell for a role.

        Parameters
        ----------
        index : QModelIndex or QPersistentModelIndex
            The cell.
        role : int, default DisplayRole
            What is wanted: the text to show, the value to sort by (`SORT_ROLE`), the alignment, or the row's hidden details
            (`ROW_ROLE`).

        Returns
        -------
        object
            The requested data, or None for a role the model does not use.

        Examples
        --------
        >>> model = RowsModel(["Name", "Count"], rows=[[("Ada", "Ada"), ("3", 3)]], numeric={1})
        >>> model.data(model.index(0, 0))
        'Ada'
        >>> align = Qt.ItemDataRole.TextAlignmentRole
        >>> model.data(model.index(0, 1), align) != model.data(model.index(0, 0), align)  # numbers are right-aligned
        True
        """
        if role == ROW_ROLE:
            return self.extras[index.row()]
        text, value = self.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return text
        if role == SORT_ROLE:
            return value
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in self.numeric:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(  # noqa: PLR0917  (Qt calls this override with positional arguments)
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        """
        Return a column heading.

        Parameters
        ----------
        section : int
            The column.
        orientation : Qt.Orientation
            Only horizontal headings are used.
        role : int, default DisplayRole
            Only the display text is given.

        Returns
        -------
        object
            The heading, or None for anything else.

        Examples
        --------
        >>> model = RowsModel(["Name", "Count"], rows=[])
        >>> model.headerData(1, Qt.Orientation.Horizontal)
        'Count'
        """
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None


def _when(timestamp: float) -> tuple[str, float]:
    """
    Turn a timestamp into a cell: its text and its sort value.

    Parameters
    ----------
    timestamp : float
        Seconds since the epoch.

    Returns
    -------
    tuple of (str, float)
        The local time as 'YYYY-MM-DD HH:MM:SS', and the timestamp itself.

    Examples
    --------
    >>> text, value = _when(0.0)
    >>> len(text), value
    (19, 0.0)
    """
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"), timestamp


ANSWER_HEADERS = ["When", "Exercise", "Question", "Answer given", "Result", "Attempt", "Time"]


class QuestionTexts:
    """
    Describes stored questions in words, remembering each one so it is worked out only once.

    Examples
    --------
    >>> texts = QuestionTexts()
    >>> texts("NoteNames", key="k", payload=None)
    '(no longer stored)'
    """

    def __init__(self) -> None:
        """
        Create an empty memory.

        Examples
        --------
        >>> QuestionTexts()._described
        {}
        """
        self._described: dict[tuple[str, str], str] = {}

    def __call__(
        self,
        exercise: str,
        *,
        key: str,
        payload: str | None,
    ) -> str:
        """
        Describe a stored question: what was shown and what the answer was.

        Parameters
        ----------
        exercise : str
            The exercise's class name.
        key : str
            The question's `item_key`. Keyword-only.
        payload : str or None
            The stored question as JSON, or None if its record is gone. Keyword-only.

        Returns
        -------
        str
            The description, "(no longer stored)" if there is no payload, or "(unreadable)" if it cannot be read. A description
            is remembered, so asking again does not parse the payload again.

        Examples
        --------
        >>> QuestionTexts()("NoteNames", key="broken", payload="{not json")
        '(unreadable)'
        """
        if payload is None:
            return "(no longer stored)"
        cached = self._described.get((exercise, key))
        if cached is None:
            try:
                cached = stats.describe(Question.from_dict(json.loads(payload)))
            except (ValueError, KeyError, TypeError):
                cached = "(unreadable)"
            self._described[(exercise, key)] = cached
        return cached


def answer_cells(
    rows: Sequence[sqlite3.Row],
    *,
    names: dict[str, str],
    texts: QuestionTexts,
) -> tuple[list[list[tuple[str, object]]], list[dict]]:
    """
    Turn answers read from the database into the cells of a table, and the hidden details of each row.

    Parameters
    ----------
    rows : sequence of sqlite3.Row
        Answers, as `Database.attempt_rows` returns them.
    names : dict of str to str
        The title of each exercise, by class name. Keyword-only.
    texts : QuestionTexts
        Describes each question in words. Keyword-only.

    Returns
    -------
    tuple of (list, list of dict)
        The cells, in the order of `ANSWER_HEADERS`, and for each row the exercise, the stored question and the lines the
        question preview shows about the answer.

    Examples
    --------
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
    """
    cells, extras = [], []
    for r in rows:
        seconds = float(r["duration_ms"]) / 1000
        extras.append(
            {
                "exercise": r["exercise"],
                "payload": r["payload"],
                "details": [
                    (
                        f"<b>You answered:</b> {r['answer'] or '–'} ({'right' if r['correct'] else 'wrong'}, "
                        f"attempt {r['attempt_no']}, {seconds:.1f} s)"
                    ),
                    f"<span style='color: gray;'>{_when(r['answered_at'])[0]}</span>",
                ],
            },
        )
        cells.append(
            [
                _when(r["answered_at"]),
                (names.get(r["exercise"], r["exercise"]),) * 2,
                (texts(r["exercise"], key=r["item_key"], payload=r["payload"]),) * 2,
                (r["answer"],) * 2,
                ("Right", 1) if r["correct"] else ("Wrong", 0),
                (str(r["attempt_no"]), r["attempt_no"]),
                (f"{seconds:.1f} s", seconds),
            ],
        )
    return cells, extras


def open_preview(
    index: QModelIndex,
    *,
    names: dict[str, str],
    parent: QWidget,
) -> None:
    """
    Show the question behind a row of an answers table, if its record is still stored.

    Parameters
    ----------
    index : QModelIndex
        A cell of the row, in a model whose rows carry `ROW_ROLE` details.
    names : dict of str to str
        The title of each exercise, by class name. Keyword-only.
    parent : QWidget
        The widget the popup belongs to. Keyword-only.

    Examples
    --------
    >>> model = RowsModel(["Name"], rows=[[("Ada", "Ada")]])
    >>> open_preview(model.index(0, 0), names={}, parent=QWidget())  # a row with no stored question shows nothing
    """
    extra = index.data(ROW_ROLE) or {}
    if not extra.get("payload"):
        return  # profiles have no question; a question whose record is gone cannot be shown
    try:
        question = Question.from_dict(json.loads(extra["payload"]))
    except (ValueError, KeyError, TypeError):
        return
    name = str(names.get(extra["exercise"], extra["exercise"]))
    QuestionPreview(
        name,
        question=question,
        details=extra.get("details"),
        parent=parent,
    ).exec()


class AnswerList(QTableView):
    """
    A table of answers that sorts when a heading is clicked and opens the question behind a row on a double click.

    Attributes
    ----------
    proxy : QSortFilterProxyModel
        Sorts the rows by the values in `SORT_ROLE`.
    model_ : RowsModel or None
        The rows being shown; None until `show_answers` is called.

    Examples
    --------
    >>> table = AnswerList(names={})
    >>> table.show_answers([])
    >>> table.proxy.rowCount()
    0
    """

    def __init__(
        self,
        *,
        names: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty table.

        Parameters
        ----------
        names : dict of str to str
            The title of each exercise, by class name. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the table. Keyword-only.

        Examples
        --------
        >>> AnswerList(names={}).isSortingEnabled()
        True
        """
        super().__init__(parent)
        self.names = names
        self.texts = QuestionTexts()
        self.model_: RowsModel | None = None
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(28)
        self.horizontalHeader().setHighlightSections(False)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSortRole(SORT_ROLE)
        self.setModel(self.proxy)
        self.doubleClicked.connect(lambda index: open_preview(index, names=self.names, parent=self))

    def show_answers(self, rows: Sequence[sqlite3.Row]) -> None:
        """
        Show answers, newest first.

        Parameters
        ----------
        rows : sequence of sqlite3.Row
            Answers, as `Database.attempt_rows` returns them.

        Examples
        --------
        >>> table = AnswerList(names={})
        >>> table.show_answers([])
        >>> assert table.model_ is not None
        >>> table.model_.headers[:2]
        ['When', 'Exercise']
        """
        cells, extras = answer_cells(rows, names=self.names, texts=self.texts)
        model = RowsModel(
            ANSWER_HEADERS,
            rows=cells,
            numeric={5, 6},
            extras=extras,
            parent=self,
        )
        self.model_ = model
        self.proxy.setSourceModel(model)
        header = self.horizontalHeader()
        for column in range(len(ANSWER_HEADERS)):  # the question takes what room is left; the rest fit their contents
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.Stretch if column == 2 else QHeaderView.ResizeMode.ResizeToContents,
            )
        self.sortByColumn(0, Qt.SortOrder.DescendingOrder)  # newest first, and the heading says so


class DatabasePage(QWidget):
    """
    The tables behind the app.

    Answers and questions are the active profile's own; profiles lists everyone.

    Attributes
    ----------
    back : Signal
        Emitted by the Back button and by Escape.
    learner : Learner
        Whose answers and questions are shown.
    tabs : dict of str to QPushButton
        The buttons that choose the table: "answers", "questions" and "profiles".
    search : QLineEdit
        Filters every column at once.
    view : QTableView
        The table.
    proxy : QSortFilterProxyModel
        Sorts and filters the rows.

    Examples
    --------
    >>> from alto.learning import Database
    >>> db = Database()
    >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
    >>> page.note.text()
    '0 answers by Ada.'
    """

    back = Signal()

    def __init__(
        self,
        learner: Learner,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the page, showing the answers table.

        Parameters
        ----------
        learner : Learner
            Whose data to show.
        parent : QWidget or None, default None
            The widget that owns the page. Keyword-only.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.tabs["answers"].isChecked()
        True
        """
        super().__init__(parent)
        self.learner = learner
        self._names = {cls.__name__: cls.name for cls in REGISTRY}
        self._texts = QuestionTexts()

        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.setSpacing(10)
        back = QPushButton("←  Back")
        back.setToolTip("Back to the previous page (Esc)")
        back.clicked.connect(self.back)
        bar.addWidget(back)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.back.emit)
        bar.addSpacing(12)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.tabs: dict[str, QPushButton] = {}
        for key, label, tip in (
            ("answers", "Answers", "Every answer given, newest first"),
            ("questions", "Questions", "What is known about each question asked"),
            ("profiles", "Profiles", "Everyone who has a profile"),
        ):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=key: self.show_table(k))
            self.group.addButton(b)
            self.tabs[key] = b
            bar.addWidget(b)
        bar.addSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        bar.addWidget(self.search, 1)
        lay.addLayout(bar)

        self.note = QLabel()
        self.note.setStyleSheet("color: gray;")
        lay.addWidget(self.note)
        self.view = QTableView()
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(28)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.horizontalHeader().setStretchLastSection(False)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSortRole(SORT_ROLE)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)  # search every column
        self.view.setModel(self.proxy)
        self.view.doubleClicked.connect(self._preview)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.proxy.layoutChanged.connect(self._show_count)
        self.proxy.rowsInserted.connect(self._show_count)
        self.proxy.rowsRemoved.connect(self._show_count)  # narrowing the search removes rows
        self.proxy.modelReset.connect(self._show_count)
        lay.addWidget(self.view, 1)

        self.tabs["answers"].setChecked(True)
        self.show_table("answers")

    # -- tables ---------------------------------------------------------------------------------------------------------

    def _question_text(
        self,
        exercise: str,
        *,
        key: str,
        payload: str | None,
    ) -> str:
        """
        Return what a question was, for a row.

        Questions whose record is gone say so, and descriptions are kept so each question is only worked out once.

        Parameters
        ----------
        exercise : str
            The exercise's class name.
        key : str
            The question's identity. Keyword-only.
        payload : str or None
            The stored question as JSON, or None if it is no longer stored. Keyword-only.

        Returns
        -------
        str
            A short description such as 'Treble: G4 → G', '(no longer stored)' or '(unreadable)'.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> page._question_text("NoteNames", key="k", payload=None)
        '(no longer stored)'
        >>> page._question_text("NoteNames", key="k", payload="not json")
        '(unreadable)'
        """
        return self._texts(exercise, key=key, payload=payload)

    def _answers(self) -> tuple[RowsModel, str]:
        """
        Build the table of every answer the profile has given, newest first.

        Returns
        -------
        tuple of (RowsModel, str)
            The model and the line of text shown above the table.

        Examples
        --------
        >>> from alto.learning import Database
        >>> database = Database()
        >>> page = DatabasePage(Learner(database, profile=database.add_profile("Ada")))
        >>> model_, note_ = page._answers()
        >>> model_.rowCount(), note_
        (0, '0 answers by Ada.')
        """
        db, pid = self.learner.db, self.learner.profile.id
        rows, extras = answer_cells(db.attempt_rows(pid, limit=ROW_LIMIT), names=self._names, texts=self._texts)
        total = db.count_attempts(pid)
        who = self.learner.profile.name
        note = (
            f"{total:,} answers by {who}. Showing the newest {ROW_LIMIT:,}."
            if total > ROW_LIMIT
            else f"{total:,} answers by {who}."
        )
        model = RowsModel(
            ANSWER_HEADERS,
            rows=rows,
            numeric={5, 6},
            extras=extras,
        )
        return model, note

    def _questions(self) -> tuple[RowsModel, str]:
        """
        Build the table of what is known about each question the profile has been asked.

        Returns
        -------
        tuple of (RowsModel, str)
            The model and the line of text shown above the table.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> model_, note = page._questions()
        >>> model_.rowCount(), note.startswith("0 questions asked of Ada.")
        (0, True)
        """
        rows, extras = [], []
        for r in self.learner.db.item_rows(self.learner.profile.id, limit=ROW_LIMIT):
            typical: float = float(r["total_first_ms"]) / r["seen"] / 1000 if r["seen"] else 0.0
            extras.append(
                {
                    "exercise": r["exercise"],
                    "payload": r["payload"],
                    "details": [
                        (
                            f"<b>History:</b> answered {r['seen']} time{'s' if r['seen'] != 1 else ''}, right first time "
                            f"{r['first_try_right']}, {r['wrong_attempts']} "
                            f"missed attempt{'s' if r['wrong_attempts'] != 1 else ''}, "
                            f"typically {typical:.1f} s"
                        ),
                        f"<b>Strain:</b> {r['strain']:.1f} (higher comes back sooner)",
                    ],
                },
            )
            rows.append(
                [
                    (self._names.get(r["exercise"], r["exercise"]),) * 2,
                    (self._question_text(r["exercise"], key=r["item_key"], payload=r["payload"]),) * 2,
                    (f"{r['strain']:.1f}", r["strain"]),
                    (str(r["seen"]), r["seen"]),
                    (str(r["first_try_right"]), r["first_try_right"]),
                    (str(r["wrong_attempts"]), r["wrong_attempts"]),
                    (f"{typical:.1f} s", typical),
                    _when(r["last_seen"]),
                ],
            )
        model = RowsModel(
            [
                "Exercise",
                "Question",
                "Strain",
                "Answered",
                "Right first time",
                "Missed",
                "Typical time",
                "Last seen",
            ],
            rows=rows,
            numeric={
                2,
                3,
                4,
                5,
                6,
            },
            extras=extras,
        )
        return model, (
            f"{len(rows):,} questions asked of {self.learner.profile.name}. "
            "Strain is how much practice a question needs: higher comes back sooner."
        )

    def _profiles(self) -> tuple[RowsModel, str]:
        """
        Build the table of everyone who has a profile.

        Returns
        -------
        tuple of (RowsModel, str)
            The model and the line of text shown above the table.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> model, note = page._profiles()
        >>> model.rowCount(), note
        (1, '1 profile.')
        """
        rows = [
            [
                (r["name"],) * 2,
                _when(r["created_at"]),
                (f"{r['attempts']:,}", r["attempts"]),
                (f"{r['questions']:,}", r["questions"]),
            ]
            for r in self.learner.db.profile_rows()
        ]
        return (
            RowsModel(
                [
                    "Name",
                    "Created",
                    "Answers",
                    "Questions",
                ],
                rows=rows,
                numeric={2, 3},
            ),
            f"{len(rows)} profile{'s' if len(rows) != 1 else ''}.",
        )

    def show_table(self, key: str) -> None:
        """
        Show one of the tables.

        Parameters
        ----------
        key : str
            "answers", "questions" or "profiles".

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.show_table("profiles")
        >>> page.note.text()
        '1 profile.'
        """
        model, note = {"answers": self._answers, "questions": self._questions, "profiles": self._profiles}[key]()
        # noinspection PyAttributeOutsideInit
        self._base_note = note
        # noinspection PyAttributeOutsideInit
        self.model = model  # keeps the model alive while the proxy uses it
        self.proxy.setSourceModel(model)
        head = self.view.horizontalHeader()
        for col in range(model.columnCount()):
            stretch = model.headers[col] == "Question"
            head.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch if stretch else QHeaderView.ResizeMode.ResizeToContents)
        if key == "answers":
            self.view.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        elif key == "questions":
            self.view.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        else:
            self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._show_count()

    def _preview(self, index: QModelIndex) -> None:
        """
        Pop up the question a double-clicked row is about, as the exercise showed it.

        Rows with no stored question (the profiles table, or a question whose record is gone) do nothing.

        Parameters
        ----------
        index : QModelIndex
            The row that was double-clicked.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.show_table("profiles")
        >>> page._preview(page.proxy.index(0, 0))  # a profile has no question to show
        """
        open_preview(index, names=self._names, parent=self)

    def _show_count(self) -> None:
        """
        Show how many rows match the search, below the table's description.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = DatabasePage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.show_table("profiles")
        >>> page.search.setText("zzz")  # matches no profile
        >>> page.note.text()
        '1 profile. 0 match the search.'
        """
        shown, total = self.proxy.rowCount(), self.model.rowCount()
        self.note.setText(self._base_note + (f" {shown:,} match the search." if shown != total else ""))
