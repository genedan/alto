"""A read-only look at what is stored: every answer, every question's record, and the profiles."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
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

from ..exercises import REGISTRY
from ..exercises.base import Question
from ..learning import Learner, stats
from .question_preview import QuestionPreview

ROW_LIMIT = 10000
SORT_ROLE = Qt.ItemDataRole.UserRole
ROW_ROLE = Qt.ItemDataRole.UserRole + 1  # a row's hidden details


class RowsModel(QAbstractTableModel):
    """Rows of (text shown, value to sort by) cells. Numbers are right-aligned."""

    def __init__(
        self,
        headers: list[str],
        rows: list[list[tuple[str, object]]],
        numeric: Iterable[int] = (),
        extras: list[dict] | None = None,
        parent=None,
    ):
        """`extras` holds something about each row that is not shown, such as the stored question (see ROW_ROLE)."""
        super().__init__(parent)
        self.headers, self.rows, self.numeric = headers, rows, set(numeric)
        self.extras = extras or [{} for _ in rows]

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.headers)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
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

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None


def _when(timestamp: float) -> tuple[str, float]:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"), timestamp


class DatabasePage(QWidget):
    """The tables behind the app. Answers and questions are the active profile's own; profiles lists everyone."""

    back = Signal()

    def __init__(
        self,
        learner: Learner,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.learner = learner
        self._names = {cls.__name__: cls.name for cls in REGISTRY}
        self._described: dict[tuple[str, str], str] = {}

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
        key: str,
        payload: str | None,
    ) -> str:
        """What the question was, for a row. Questions whose record is gone show their key."""
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

    def _answers(self) -> tuple[RowsModel, str]:
        db, pid = self.learner.db, self.learner.profile.id
        rows, extras = [], []
        for r in db.attempt_rows(pid, ROW_LIMIT):
            seconds = r["duration_ms"] / 1000
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
            rows.append(
                [
                    _when(r["answered_at"]),
                    (self._names.get(r["exercise"], r["exercise"]),) * 2,
                    (self._question_text(r["exercise"], r["item_key"], r["payload"]),) * 2,
                    (r["answer"],) * 2,
                    ("Right", 1) if r["correct"] else ("Wrong", 0),
                    (str(r["attempt_no"]), r["attempt_no"]),
                    (f"{seconds:.1f} s", seconds),
                ],
            )
        total = db.count_attempts(pid)
        who = self.learner.profile.name
        note = (
            f"{total:,} answers by {who}. Showing the newest {ROW_LIMIT:,}."
            if total > ROW_LIMIT
            else f"{total:,} answers by {who}."
        )
        model = RowsModel(
            [
                "When",
                "Exercise",
                "Question",
                "Answer given",
                "Result",
                "Attempt",
                "Time",
            ],
            rows,
            {5, 6},
            extras,
        )
        return model, note

    def _questions(self) -> tuple[RowsModel, str]:
        rows, extras = [], []
        for r in self.learner.db.item_rows(self.learner.profile.id, ROW_LIMIT):
            typical = r["total_first_ms"] / r["seen"] / 1000 if r["seen"] else 0.0
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
                    (self._question_text(r["exercise"], r["item_key"], r["payload"]),) * 2,
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
            rows,
            {
                2,
                3,
                4,
                5,
                6,
            },
            extras,
        )
        return model, (
            f"{len(rows):,} questions asked of {self.learner.profile.name}. "
            "Strain is how much practice a question needs: higher comes back sooner."
        )

    def _profiles(self) -> tuple[RowsModel, str]:
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
                rows,
                {2, 3},
            ),
            f"{len(rows)} profile{'s' if len(rows) != 1 else ''}.",
        )

    def show_table(self, key: str) -> None:
        model, note = {"answers": self._answers, "questions": self._questions, "profiles": self._profiles}[key]()
        self._base_note = note
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
        """Double-clicking a row pops up the question it is about, as the exercise showed it."""
        extra = index.data(ROW_ROLE) or {}
        if not extra.get("payload"):
            return  # profiles have no question; a question whose record is gone cannot be shown
        try:
            question = Question.from_dict(json.loads(extra["payload"]))
        except (ValueError, KeyError, TypeError):
            return
        name = str(self._names.get(extra["exercise"], extra["exercise"]))
        QuestionPreview(
            name,
            question,
            extra.get("details"),
            self,
        ).exec()

    def _show_count(self) -> None:
        shown, total = self.proxy.rowCount(), self.model.rowCount()
        self.note.setText(self._base_note + (f" {shown:,} match the search." if shown != total else ""))
