"""
The statistics screen: a few numbers and charts about how practice is going.

It shows the active profile's own answers, filterable by exercise and by timeframe.

Examples
--------
>>> since_for(None, now=1000.0) is None  # all time: from the start
True
>>> format_duration(3600)
'1 h 00 min'
"""

from __future__ import annotations

import time
from datetime import (
    date,
    datetime,
    timedelta,
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
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

from alto.exercises import REGISTRY
from alto.learning import (
    Learner,
    stats,
)
from alto.ui.charts import (
    HBarChart,
    HeatmapChart,
    LineChart,
    StackedBarChart,
)
from alto.ui.database_page import AnswerList

DAY = 86400.0
DETAIL_LIMIT = 500  # the most answers the drilldown lists; the note above it says when there are more
TIMEFRAMES = (
    ("Today", "today"),
    ("Last 7 days", 7),
    ("Last 30 days", 30),
    ("Last 90 days", 90),
    ("Last year", 365),
    ("All time", None),
)


def since_for(
    span: str | int | None,
    *,
    now: float,
) -> float | None:
    """
    Return the timestamp a timeframe starts from.

    Parameters
    ----------
    span : str or int or None
        "today", a number of days back, or None for all time.
    now : float
        The current time as a timestamp. Keyword-only.

    Returns
    -------
    float or None
        Midnight for "today", `now` less that many days for a number, and None for all time.

    Examples
    --------
    >>> since_for(7, now=864000.0)
    259200.0
    >>> since_for(None, now=864000.0) is None
    True
    >>> 0 <= 864000.0 - since_for("today", now=864000.0) < 90000  # within a day of now
    True
    """
    if span == "today":
        return (
            datetime.fromtimestamp(now)
            .replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            .timestamp()
        )
    return None if span is None else now - int(span) * DAY


def format_duration(seconds: float) -> str:
    """
    Write a length of time the way the statistics show it.

    Parameters
    ----------
    seconds : float
        The time in seconds.

    Returns
    -------
    str
        Seconds under half a minute, then minutes, then hours and minutes.

    Examples
    --------
    >>> format_duration(5), format_duration(90), format_duration(3000)
    ('5 s', '2 min', '50 min')
    >>> format_duration(3 * 3600 + 7 * 60)
    '3 h 07 min'
    """
    minutes = round(seconds / 60)
    if minutes < 1:
        return f"{round(seconds)} s"
    return f"{minutes} min" if minutes < 60 else f"{minutes // 60} h {minutes % 60:02d} min"


def period_title(
    start: datetime,
    *,
    granularity: str,
) -> str:
    """
    Name a chart period in words, for the heading of its list of answers.

    Parameters
    ----------
    start : datetime
        The start of the period.
    granularity : str
        "hour", "day", "week" or "month", as `Stats.granularity` says. Keyword-only.

    Returns
    -------
    str
        For example "Mon 5 Jan 2026", "Week of Mon 5 Jan 2026" or "January 2026".

    Examples
    --------
    >>> period_title(datetime(2026, 1, 5, 14), granularity="hour")
    'Mon 5 Jan 2026, 14:00'
    >>> period_title(datetime(2026, 1, 5), granularity="day")
    'Mon 5 Jan 2026'
    >>> period_title(datetime(2026, 1, 5), granularity="week")
    'Week of Mon 5 Jan 2026'
    >>> period_title(datetime(2026, 1, 1), granularity="month")
    'January 2026'
    """
    day = f"{start.strftime('%a')} {start.day} {start.strftime('%b')} {start.year}"
    return {
        "hour": f"{day}, {start.strftime('%H')}:00",
        "day": day,
        "week": f"Week of {day}",
        "month": start.strftime("%B %Y"),
    }[granularity]


class Tile(QFrame):
    """
    One headline number with its caption.

    Attributes
    ----------
    value : QLabel
        The big number.
    caption : QLabel
        What the number is.

    Examples
    --------
    >>> tile = Tile("Questions answered")
    >>> tile.value.text()
    '–'
    >>> tile.show_value("12")
    >>> tile.value.text()
    '12'
    """

    def __init__(
        self,
        caption: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a tile showing a dash until it is given a value.

        Parameters
        ----------
        caption : str
            What the number is, shown under it.
        parent : QWidget or None, default None
            The widget that owns the tile. Keyword-only.

        Examples
        --------
        >>> tile = Tile("Days practised")
        >>> tile.caption.text()
        'Days practised'
        """
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
        """
        Show a number (or any text) in the tile.

        Parameters
        ----------
        text : str
            What to show.

        Examples
        --------
        >>> tile = Tile("Typical first answer")
        >>> tile.show_value("7.6 s")
        >>> tile.value.text()
        '7.6 s'
        """
        self.value.setText(text)


class StatsPage(QWidget):
    """
    The statistics, as a page of the main window.

    Attributes
    ----------
    back : Signal
        Emitted by the Back button and by Escape.
    learner : Learner
        Whose answers are shown; only the active profile's own.
    exercise : QComboBox
        The exercise filter.
    timeframe : QComboBox
        The timeframe filter.
    tiles : dict of str to Tile
        The headline numbers, by name.
    detail : QFrame
        The panel under the charts that lists the answers behind a clicked bar, point, row or day. Hidden until one is clicked.
    answers : AnswerList
        The table in the detail panel.

    Examples
    --------
    >>> from alto.learning import Database
    >>> db = Database()
    >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
    >>> page.note.text().startswith("No answers recorded for Ada")
    True
    """

    back = Signal()

    def __init__(
        self,
        learner: Learner,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Build the page and fill it for the current filters.

        Parameters
        ----------
        learner : Learner
            Whose statistics to show.
        parent : QWidget or None, default None
            The widget that owns the page. Keyword-only.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.timeframe.currentText()  # the last 30 days, until another is chosen
        'Last 30 days'
        """
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
        lay.setContentsMargins(
            0,
            6,
            8,
            6,
        )
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
        self.accuracy = LineChart("Right first time", fmt=lambda v: f"{v:.0f}%", fixed_top=100)
        self.speed = LineChart("Typical time to first answer", fmt=lambda v: f"{v:.1f} s")
        self.by_exercise = HBarChart("Right first time, by exercise")
        charts = QGridLayout()
        charts.setSpacing(14)
        for i, chart in enumerate(
            (
                self.volume,
                self.accuracy,
                self.speed,
                self.by_exercise,
            ),
        ):
            charts.addWidget(chart, i // 2, i % 2)
        lay.addLayout(charts)

        # The calendar always looks back about a year, whatever the timeframe, so it follows only the exercise filter.
        self.heatmap = HeatmapChart("Reviews, last 12 months")
        self.heatmap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.heatmap.setFixedHeight(190)
        lay.addWidget(self.heatmap)

        # Clicking a bar, a point, a row or a day lists the answers behind it here.
        self.detail = QFrame()
        self.detail.setObjectName("detailPane")
        detail_lay = QVBoxLayout(self.detail)
        head = QHBoxLayout()
        self.detail_title = QLabel()
        head.addWidget(self.detail_title, 1)
        self.detail_close = QPushButton("Close")
        self.detail_close.setToolTip("Close the list of answers")
        self.detail_close.clicked.connect(self._close_detail)
        head.addWidget(self.detail_close)
        detail_lay.addLayout(head)
        self.detail_note = QLabel()
        self.detail_note.setStyleSheet("color: gray;")
        self.detail_note.setWordWrap(True)
        detail_lay.addWidget(self.detail_note)
        self.answers = AnswerList(names=self._names())
        self.answers.setMinimumHeight(240)
        self.answers.setMaximumHeight(380)
        detail_lay.addWidget(self.answers)
        self.detail.hide()
        lay.addWidget(self.detail)

        lay.addWidget(QLabel("<b>Questions that need practice</b>"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                "Exercise",
                "Question",
                "Missed",
                "Answered",
            ],
        )
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

        self.scroller = QScrollArea()
        self.scroller.setWidgetResizable(True)
        self.scroller.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroller.setWidget(body)
        outer.addWidget(self.scroller, 1)
        self._reveal = QTimer(self)  # owned by the page, so it cannot fire after the page has gone
        self._reveal.setSingleShot(True)
        self._reveal.timeout.connect(lambda: self.scroller.ensureWidgetVisible(self.detail))
        self._stats: stats.Stats | None = None  # what the charts show now, so a click can be turned into a period
        self._since: float | None = None
        for chart in (self.volume, self.accuracy, self.speed):
            chart.clicked.connect(self._drill_period)
        self.by_exercise.clicked.connect(self._drill_exercise)
        self.heatmap.clicked.connect(self._drill_day)

        for signal in (self.exercise.currentIndexChanged, self.timeframe.currentIndexChanged):
            signal.connect(lambda *_: self.refresh())
        self.refresh()

    # noinspection PyMethodMayBeStatic
    def _names(self) -> dict[str, str]:
        """
        Return the title of each exercise, by class name.

        Returns
        -------
        dict of str to str
            For example `{"NoteNames": "Note Identification", ...}`.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
        >>> page._names()["NoteNames"]
        'Note Identification'
        """
        return {cls.__name__: cls.name for cls in REGISTRY}

    def refresh(self) -> None:
        """
        Recalculate everything for the chosen exercise and timeframe and show it.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.refresh()
        >>> page.tiles["questions"].value.text()  # nothing answered yet
        '0'
        """
        now = time.time()
        profiles = [self.learner.profile.id]  # only the active profile's answers
        since = since_for(self.timeframe.currentData(), now=now)
        s = stats.collect(
            self.learner.db,
            profile_ids=profiles,
            exercise=self.exercise.currentData(),
            since=since,
            now=now,
        )
        self._stats, self._since = s, since
        self._close_detail()  # the numbers have changed, so a list of answers from the old ones would no longer match
        names = self._names()

        who = self.learner.profile.name
        self.note.setText(
            f"Showing {who}. A question counts as right only if the first answer was right."
            if s.questions
            else f"No answers recorded for {who} in this selection yet. Practise an exercise, then come back.",
        )
        self.tiles["questions"].show_value(str(s.questions))
        accuracy, tries = s.accuracy, s.attempts_per_question
        self.tiles["accuracy"].show_value("–" if accuracy is None else f"{accuracy:.0f}%")
        self.tiles["speed"].show_value("–" if s.median_seconds is None else f"{s.median_seconds:.1f} s")
        self.tiles["tries"].show_value("–" if tries is None else f"{tries:.2f}")
        self.tiles["days"].show_value(str(s.days_practised))
        self.tiles["time"].show_value(format_duration(s.practice_seconds))

        labels = [b.label for b in s.buckets]
        per = {
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month",
        }[s.granularity]
        self.volume.title = f"Questions answered per {per}"
        self.volume.set_data(
            labels,
            right=[b.first_right for b in s.buckets],
            wrong=[b.questions - b.first_right for b in s.buckets],
        )
        self.accuracy.title = f"Right first time, per {per}"
        self.accuracy.set_data(labels, values=[b.accuracy for b in s.buckets])
        self.speed.title = f"Typical time to first answer, per {per}"
        self.speed.set_data(labels, values=[b.median_seconds for b in s.buckets])
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

        counts = stats.daily_counts(
            self.learner.db,
            profile_ids=profiles,
            exercise=self.exercise.currentData(),
            now=now,
        )
        self.heatmap.set_data(counts, today=datetime.fromtimestamp(now).date())

        self.table.setRowCount(len(s.hardest))
        for row, h in enumerate(s.hardest):
            for col, text in enumerate(
                (
                    names.get(h.exercise, h.exercise),
                    h.text,
                    str(h.wrong),
                    str(h.seen),
                ),
            ):
                item = QTableWidgetItem(text)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.setFixedHeight(self.table.horizontalHeader().height() + 30 * max(len(s.hardest), 1) + 6)

    def _clear_selection(self) -> None:
        """
        Remove the highlight that marks the clicked element in every chart.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
        >>> page.volume.set_selected(2)
        >>> page._clear_selection()
        >>> page.volume.selected is None
        True
        """
        for chart in (self.volume, self.accuracy, self.speed, self.by_exercise, self.heatmap):
            chart.set_selected(None)

    def _close_detail(self) -> None:
        """
        Hide the list of answers and the highlight of the element it was opened from.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> page = StatsPage(Learner(db, profile=db.add_profile("Ada")))
        >>> page._close_detail()
        >>> page.detail.isHidden()
        True
        """
        self.detail.hide()
        self._clear_selection()

    def _open_detail(
        self,
        title: str,
        *,
        exercise: str | None,
        since: float | None,
        until: float | None,
    ) -> None:
        """
        List the answers within a scope under the charts, and scroll to them.

        Parameters
        ----------
        title : str
            The heading of the list.
        exercise : str or None
            The exercise to list (a class name), or None for all of them. Keyword-only.
        since : float or None
            The earliest answer to list (a timestamp), or None for no limit. Keyword-only.
        until : float or None
            The time before which answers are listed, or None for no limit. Keyword-only.

        Examples
        --------
        >>> from alto.learning import Database
        >>> store = Database()
        >>> ada = store.add_profile("Ada")
        >>> store.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                   duration_ms=2000, answered_at=1000.0)
        >>> page = StatsPage(Learner(store, profile=ada))
        >>> page._open_detail("A day", exercise=None, since=0.0, until=2000.0)
        >>> page.detail.isHidden(), page.answers.proxy.rowCount()
        (False, 1)
        >>> page.detail_note.text()
        '1 answer, to 1 question, 1 right first time.'
        """
        db, pid = self.learner.db, self.learner.profile.id
        rows = db.attempt_rows(
            pid,
            limit=DETAIL_LIMIT,
            exercise=exercise,
            since=since,
            until=until,
        )
        total = db.count_attempts(
            pid,
            exercise=exercise,
            since=since,
            until=until,
        )
        plural = "s" if total != 1 else ""
        if total > len(rows):
            note = f"{total:,} answers. Showing the newest {len(rows):,}."
        else:
            firsts = [r for r in rows if r["attempt_no"] == 1]
            right = sum(1 for r in firsts if r["correct"])
            asked = f"{len(firsts)} question{'s' if len(firsts) != 1 else ''}"
            note = f"{total:,} answer{plural}, to {asked}, {right} right first time."
        self.detail_title.setText(f"<b>{title}</b>")
        self.detail_note.setText(note)
        self.answers.show_answers(rows)
        self.detail.show()
        self._reveal.start(0)  # scroll to it once the layout has made room for it

    def _drill_period(self, index: object) -> None:
        """
        List the answers given in the period of a clicked bar or point, or close the list if that period is already open.

        Parameters
        ----------
        index : object
            The index of the period, as the chart that was clicked emits it.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                duration_ms=2000, answered_at=time.time())
        >>> page = StatsPage(Learner(db, profile=ada))
        >>> page._drill_period(len(page.volume.labels) - 1)  # the last period is today
        >>> page.answers.proxy.rowCount(), page.volume.selected == page.accuracy.selected
        (1, True)
        >>> page._drill_period(len(page.volume.labels) - 1)  # clicking it again closes the list
        >>> page.detail.isHidden()
        True
        """
        s = self._stats
        if s is None or not isinstance(index, int) or not 0 <= index < len(s.buckets):
            return
        if self.volume.selected == index:
            self._close_detail()
            return
        bucket = s.buckets[index]
        begin = bucket.start.timestamp()
        if self._since is not None:
            begin = max(begin, self._since)  # the first period may begin before the timeframe does
        self._clear_selection()
        self._open_detail(
            period_title(bucket.start, granularity=s.granularity),
            exercise=self.exercise.currentData(),
            since=begin,
            until=stats.period_end(bucket.start, granularity=s.granularity).timestamp(),
        )
        for chart in (self.volume, self.accuracy, self.speed):
            chart.set_selected(index)

    def _drill_exercise(self, index: object) -> None:
        """
        List the answers to a clicked exercise within the timeframe, or close the list if it is already open.

        Parameters
        ----------
        index : object
            The index of the row, as the chart that was clicked emits it.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                duration_ms=2000, answered_at=time.time())
        >>> page = StatsPage(Learner(db, profile=ada))
        >>> page._drill_exercise(0)
        >>> page.detail_title.text()
        '<b>Answers to Note Identification</b>'
        """
        s = self._stats
        if s is None or not isinstance(index, int) or not 0 <= index < len(s.by_exercise):
            return
        if self.by_exercise.selected == index:
            self._close_detail()
            return
        name = s.by_exercise[index].exercise
        self._clear_selection()
        self._open_detail(
            f"Answers to {self._names().get(name, name)}",
            exercise=name,
            since=self._since,
            until=None,
        )
        self.by_exercise.set_selected(index)

    def _drill_day(self, day: object) -> None:
        """
        List the answers given on a clicked day of the calendar, or close the list if that day is already open.

        The calendar always looks back about a year, so this ignores the timeframe and follows only the exercise filter.

        Parameters
        ----------
        day : object
            The day, as the calendar emits it.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> ada = db.add_profile("Ada")
        >>> db.add_attempt(ada.id, exercise="NoteNames", item_key="k", attempt_no=1, answer="C", correct=True,
        ...                duration_ms=2000, answered_at=time.time())
        >>> page = StatsPage(Learner(db, profile=ada))
        >>> page._drill_day(date.today())
        >>> page.answers.proxy.rowCount()
        1
        """
        if not isinstance(day, date):
            return
        if self.heatmap.selected == day:
            self._close_detail()
            return
        midnight = datetime(day.year, day.month, day.day)
        self._clear_selection()
        self._open_detail(
            f"Answers on {period_title(midnight, granularity='day')}",
            exercise=self.exercise.currentData(),
            since=midnight.timestamp(),
            until=(midnight + timedelta(days=1)).timestamp(),
        )
        self.heatmap.set_selected(day)
