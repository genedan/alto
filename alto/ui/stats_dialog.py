"""The statistics screen: a few numbers and charts about how practice is going for the active profile, filterable by
exercise and by timeframe."""

from __future__ import annotations

import time
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..exercises import REGISTRY
from ..learning import Learner, stats
from .charts import HBarChart, HeatmapChart, LineChart, StackedBarChart

DAY = 86400.0
TIMEFRAMES = (
    ("Today", "today"),
    ("Last 7 days", 7),
    ("Last 30 days", 30),
    ("Last 90 days", 90),
    ("Last year", 365),
    ("All time", None),
)


def since_for(span: str | int | None, now: float) -> float | None:
    """The timestamp a timeframe starts from: midnight for today, so many days back for the rest, None for all time."""
    if span == "today":
        return datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return None if span is None else now - int(span) * DAY


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 1:
        return f"{round(seconds)} s"
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60} h {minutes % 60:02d} min"


class Tile(QFrame):
    """One headline number with its caption."""

    def __init__(self, caption: str, parent=None):
        super().__init__(parent)
        self.setObjectName("keyGroup")  # the same bordered box used elsewhere in the settings
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        self.value = QLabel("–")
        self.value.setStyleSheet("font-size: 20pt; font-weight: bold;")
        self.caption = QLabel(caption)
        self.caption.setStyleSheet("color: gray;")
        lay.addWidget(self.value)
        lay.addWidget(self.caption)

    def show_value(self, text: str) -> None:
        self.value.setText(text)


class StatsPage(QWidget):
    """The statistics, as a page of the main window. `back` is emitted by the Back button and by Escape."""

    back = Signal()

    def __init__(self, learner: Learner, parent: QWidget | None = None):
        super().__init__(parent)
        self.learner = learner
        outer = QVBoxLayout(self)

        # Back to wherever you came from, then the filters: which profiles, which exercise, which period.
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.back_button = QPushButton("←  Back")
        self.back_button.setToolTip("Back to the previous page (Esc)")
        self.back_button.clicked.connect(self.back)
        bar.addWidget(self.back_button)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.back.emit)
        bar.addSpacing(12)
        who = QLabel(f"<b>{learner.profile.name}</b>")  # these are always the active profile's own numbers
        who.setToolTip("Statistics for the active profile")
        bar.addWidget(who)
        self.exercise = QComboBox()
        self.exercise.addItem("All exercises", None)
        for cls in REGISTRY:
            self.exercise.addItem(cls.name, cls.__name__)
        self.timeframe = QComboBox()
        for label, span in TIMEFRAMES:
            self.timeframe.addItem(label, span)
        self.timeframe.setCurrentIndex(2)  # last 30 days
        bar.addWidget(self.exercise)
        bar.addWidget(self.timeframe)
        bar.addStretch(1)
        outer.addLayout(bar)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 6, 8, 6)
        lay.setSpacing(14)
        self.note = QLabel()
        self.note.setStyleSheet("color: gray;")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)

        self.tiles = {
            key: Tile(caption)
            for key, caption in (
                ("questions", "Questions answered"),
                ("accuracy", "Right first time"),
                ("speed", "Typical first answer"),
                ("tries", "Attempts per question"),
                ("days", "Days practised"),
                ("time", "Time practising"),
            )
        }
        tiles = QGridLayout()
        tiles.setSpacing(10)
        for i, tile in enumerate(self.tiles.values()):
            tiles.addWidget(tile, i // 3, i % 3)
        lay.addLayout(tiles)

        self.volume = StackedBarChart("Questions answered")
        self.accuracy = LineChart("Right first time", lambda v: f"{v:.0f}%", fixed_top=100)
        self.speed = LineChart("Typical time to first answer", lambda v: f"{v:.1f} s")
        self.by_exercise = HBarChart("Right first time, by exercise")
        charts = QGridLayout()
        charts.setSpacing(14)
        for i, chart in enumerate((self.volume, self.accuracy, self.speed, self.by_exercise)):
            charts.addWidget(chart, i // 2, i % 2)
        lay.addLayout(charts)

        # The calendar always looks back about a year, whatever the timeframe, so it follows only the exercise filter.
        self.heatmap = HeatmapChart("Reviews, last 12 months")
        self.heatmap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.heatmap.setFixedHeight(190)
        lay.addWidget(self.heatmap)

        lay.addWidget(QLabel("<b>Questions that need practice</b>"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Exercise", "Question", "Missed", "Answered"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setShowGrid(False)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        for signal in (self.exercise.currentIndexChanged, self.timeframe.currentIndexChanged):
            signal.connect(lambda *_: self.refresh())
        self.refresh()

    def _names(self) -> dict[str, str]:
        return {cls.__name__: cls.name for cls in REGISTRY}

    def refresh(self) -> None:
        now = time.time()
        profiles = [self.learner.profile.id]  # only the active profile's answers
        s = stats.collect(
            self.learner.db,
            profiles,
            self.exercise.currentData(),
            since_for(self.timeframe.currentData(), now),
            now,
        )
        names = self._names()

        who = self.learner.profile.name
        self.note.setText(
            f"Showing {who}. A question counts as right only if the first answer was right."
            if s.questions
            else f"No answers recorded for {who} in this selection yet. Practise an exercise, then come back.",
        )
        self.tiles["questions"].show_value(str(s.questions))
        self.tiles["accuracy"].show_value("–" if s.accuracy is None else f"{s.accuracy:.0f}%")
        self.tiles["speed"].show_value("–" if s.median_seconds is None else f"{s.median_seconds:.1f} s")
        self.tiles["tries"].show_value("–" if s.attempts_per_question is None else f"{s.attempts_per_question:.2f}")
        self.tiles["days"].show_value(str(s.days_practised))
        self.tiles["time"].show_value(format_duration(s.practice_seconds))

        labels = [b.label for b in s.buckets]
        per = {"hour": "hour", "day": "day", "week": "week", "month": "month"}[s.granularity]
        self.volume.title = f"Questions answered per {per}"
        self.volume.set_data(labels, [b.first_right for b in s.buckets], [b.questions - b.first_right for b in s.buckets])
        self.accuracy.title = f"Right first time, per {per}"
        self.accuracy.set_data(labels, [b.accuracy for b in s.buckets])
        self.speed.title = f"Typical time to first answer, per {per}"
        self.speed.set_data(labels, [b.median_seconds for b in s.buckets])
        self.by_exercise.set_data(
            [
                (
                    names.get(e.exercise, e.exercise),
                    e.accuracy,
                    f"{e.accuracy:.0f}%  ·  {e.questions} q  ·  {e.median_seconds:.1f} s",
                )
                for e in s.by_exercise
            ],
        )

        counts = stats.daily_counts(self.learner.db, profiles, self.exercise.currentData(), now=now)
        self.heatmap.set_data(counts, datetime.fromtimestamp(now).date())

        self.table.setRowCount(len(s.hardest))
        for row, h in enumerate(s.hardest):
            for col, text in enumerate((names.get(h.exercise, h.exercise), h.text, str(h.wrong), str(h.seen))):
                item = QTableWidgetItem(text)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.setFixedHeight(self.table.horizontalHeader().height() + 30 * max(len(s.hardest), 1) + 6)
