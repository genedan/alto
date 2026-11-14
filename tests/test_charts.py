"""The three charts: axes, bars and lines are drawn, empty data shows a message, and hovering explains a bar."""

from __future__ import annotations

from datetime import (
    date,
    timedelta,
)
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import (
    QEvent,
    QPoint,
    QPointF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
)
from PySide6.QtTest import QTest

from alto.ui import charts

if TYPE_CHECKING:
    from PySide6.QtWidgets import (
        QApplication,
        QWidget,
    )


def ink(
    widget: QWidget,
    *,
    size: tuple[int, int] = (560, 260),
) -> int:
    """
    Count the pixels a widget draws that are not blank.

    Parameters
    ----------
    widget : QWidget
        The widget to draw.
    size : tuple of int
        Its width and height.

    Returns
    -------
    int
        How many sampled pixels are not light.
    """
    widget.resize(*size)
    image = widget.grab().toImage()
    return sum(
        1 for y in range(0, image.height(), 3) for x in range(0, image.width(), 3) if image.pixelColor(x, y).lightness() < 140
    )


def test_ticks_are_round_numbers_up_to_just_above_the_top() -> None:
    """
    Check that ticks are round numbers up to just above the top.
    """
    assert charts.nice_ticks(13) == [
        0,
        5,
        10,
        15,
    ]
    assert charts.nice_ticks(0) == [0.0, 1.0] and charts.nice_ticks(-3) == [0.0, 1.0]
    assert charts.nice_ticks(100)[-1] >= 100 and charts.nice_ticks(0.07)[-1] >= 0.07
    ticks = charts.nice_ticks(8)
    assert ticks[0] == 0 and ticks == sorted(ticks) and ticks[-1] >= 8


def test_the_stacked_bar_chart_draws_bars_and_axes(app: QApplication) -> None:
    """
    Check that the stacked bar chart draws bars and axes.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.StackedBarChart("Questions")
    chart.set_data(
        [f"d{i}" for i in range(12)],
        right=[
            3,
            0,
            5,
            2,
            0,
            0,
            8,
            1,
            4,
            0,
            2,
            6,
        ],
        wrong=[
            1,
            2,
            0,
            0,
            0,
            4,
            1,
            0,
            0,
            0,
            3,
            0,
        ],
    )
    with_bars = ink(chart)
    chart.set_data(["a"], right=[0], wrong=[0])  # nothing answered: only a message
    assert ink(chart) < with_bars
    chart.set_data([], right=[], wrong=[])
    assert ink(chart) > 0  # the title and the message


def test_a_bar_names_itself_when_hovered(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a bar names itself when hovered.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    shown = []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    hidden = []
    monkeypatch.setattr(charts.QToolTip, "hideText", lambda: hidden.append(1))
    chart = charts.StackedBarChart("Questions")
    chart.resize(560, 260)
    chart.set_data(["Mon", "Tue"], right=[3, 1], wrong=[1, 0])
    plot = chart._plot()
    inside = QPoint(round(chart._centres()[0]), round(plot.center().y()))
    chart.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(inside),
            QPointF(inside),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )
    assert shown and shown[-1].startswith("Mon") and "4 questions" in shown[-1]
    outside = QPointF(5, 5)
    chart.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            outside,
            outside,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )
    assert hidden
    empty = charts.StackedBarChart("Empty")
    empty.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            outside,
            outside,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )  # no data: nothing to say
    one = charts.StackedBarChart("One")
    one.resize(560, 260)
    one.set_data(["x"], right=[1], wrong=[0])
    point = QPointF(one._centres()[0], one._plot().center().y())
    one.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            point,
            point,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )
    assert "1 question:" in shown[-1]  # one question is not "1 questions"


@pytest.mark.parametrize("fixed", [None, 100.0])
def test_the_line_chart_breaks_the_line_where_there_are_no_answers(
    app: QApplication,
    fixed: float | None,
) -> None:
    """
    Check that the line chart breaks the line where there are no answers.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    fixed : float | None
        The fixed top of the chart, or None to scale to the data.
    """
    chart = charts.LineChart("Accuracy", fmt=lambda v: f"{v:.0f}%", fixed_top=fixed)
    chart.set_data(["a", "b"], values=[None, None])
    message_only = ink(chart)  # nothing answered: only the title and a message
    chart.set_data(
        [f"d{i}" for i in range(8)],
        values=[
            50.0,
            60.0,
            None,
            80.0,
            None,
            None,
            90.0,
            95.0,
        ],
    )
    assert ink(chart) > message_only
    chart.set_data([f"d{i}" for i in range(60)], values=[float(i) for i in range(60)])  # many points: smaller dots
    assert ink(chart) > message_only


def test_a_line_chart_point_names_itself_when_hovered(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a line chart point names itself when hovered.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    shown = []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    chart = charts.LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
    chart.resize(560, 260)
    chart.set_data(["Mon", "Tue", "Wed"], values=[2.0, None, 4.5])
    plot = chart._plot()
    for i, expected in ((0, "Mon\n2.0 s"), (1, "Tue\nno answers"), (2, "Wed\n4.5 s")):
        # noinspection PyTypeChecker
        point = QPointF(chart._centres()[i], plot.center().y())
        chart.mouseMoveEvent(
            QMouseEvent(
                QMouseEvent.Type.MouseMove,
                point,
                point,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )
        assert shown[-1] == expected


def test_the_horizontal_bar_chart_lists_its_rows(app: QApplication) -> None:
    """
    Check that the horizontal bar chart lists its rows.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.HBarChart("By exercise")
    chart.set_data(
        [
            ("Note Identification", 92.0, "92%"),
            ("A very long exercise name that has to be shortened", 40.0, "40%"),
            ("Zero", 0.0, "0%"),
        ],
    )
    assert chart.minimumHeight() >= 190 and ink(chart) > 100
    chart.set_data([])
    assert ink(chart) > 0
    chart.set_data([("row", 50.0, "50%")] * 12)
    assert chart.minimumHeight() > 190


def test_the_chart_colours_follow_the_palette(app: QApplication) -> None:
    """
    Check that the chart colours follow the palette.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.StackedBarChart("Colours")
    assert chart._ink() != chart._grid() and chart._soft() is not None
    QTest.qWait(1)


def test_an_axis_with_no_labels_draws_nothing(app: QApplication) -> None:
    """
    Check that an axis with no labels draws nothing.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.StackedBarChart("Nothing")
    image = QImage(200, 100, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    chart._category_axis(painter, centres=[], labels=[])
    painter.end()
    assert image.pixelColor(100, 90).alpha() == 0


def test_the_heatmap_shades_days_by_how_busy_they_were(app: QApplication) -> None:
    """
    Check that the heatmap shades days by how busy they were.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    today = date(2026, 11, 13)  # a Friday
    chart = charts.HeatmapChart("Reviews")
    chart.set_data({today: 40, today - timedelta(days=1): 20, today - timedelta(days=2): 1}, today=today)
    assert chart.level(0) == 0 and chart.level(1) >= 1
    assert chart.level(40) == chart.LEVELS and chart.level(1) < chart.level(40)
    assert chart.first_day().weekday() == 0 and (today - chart.first_day()).days // 7 == 52
    busy = ink(chart, size=(760, 190))
    chart.set_data({}, today=today)
    assert ink(chart, size=(760, 190)) > 0 and ink(chart, size=(760, 190)) != busy  # still drawn, with a message


def calendar(today: date) -> charts.HeatmapChart:
    """
    Make a calendar chart, sized, with three questions answered on one day.

    Parameters
    ----------
    today : date
        The last day of the calendar, and the day with answers.

    Returns
    -------
    charts.HeatmapChart
        The chart.
    """
    chart = charts.HeatmapChart("Reviews")
    chart.resize(760, 190)
    chart.set_data({today: 3}, today=today)
    return chart


def test_the_heatmap_names_the_day_under_the_pointer(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that the heatmap names the day under the pointer.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    shown, hidden = [], []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    monkeypatch.setattr(charts.QToolTip, "hideText", lambda: hidden.append(1))
    today = date(2026, 11, 13)
    chart = calendar(today)
    cell, (x0, y0) = chart._cell(), chart._origin()

    def move(
        x: float,
        *,
        y: float,
    ) -> None:
        """
        Move the pointer over the chart.

        Parameters
        ----------
        x : float
            Horizontal position.
        y : float
            Vertical position.
        """
        pt = QPointF(x, y)
        chart.mouseMoveEvent(
            QMouseEvent(
                QMouseEvent.Type.MouseMove,
                pt,
                pt,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )

    move(x0 + 52.5 * cell, y=y0 + 4.5 * cell)  # last column, Friday
    assert shown[-1].startswith("Fri Nov 13, 2026") and "3 questions" in shown[-1]
    move(x0 + 52.5 * cell, y=y0 + 6.5 * cell)  # Sunday, in the future
    move(2, y=2)
    assert len(hidden) == 2
    assert chart.day_at(QPointF(x0 + 0.5 * cell, y0 + 0.5 * cell)) == chart.first_day()


def mouse(
    chart: QWidget,
    kind: QMouseEvent.Type,
    *,
    at: QPointF,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> None:
    """
    Send a mouse event to a chart, as the window system would.

    Parameters
    ----------
    chart : QWidget
        The chart.
    kind : QMouseEvent.Type
        A move, press or release.
    at : QPointF
        Where the pointer is. Keyword-only.
    button : Qt.MouseButton
        The button that changed; it is held down for a move and a press. Keyword-only.
    """
    changed = Qt.MouseButton.NoButton if kind == QMouseEvent.Type.MouseMove else button
    held = button if kind == QMouseEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton
    event = QMouseEvent(kind, at, at, changed, held, Qt.KeyboardModifier.NoModifier)
    if kind == QMouseEvent.Type.MouseMove:
        chart.mouseMoveEvent(event)
    elif kind == QMouseEvent.Type.MouseButtonPress:
        chart.mousePressEvent(event)
    else:
        chart.mouseReleaseEvent(event)


def click(
    chart: QWidget,
    *,
    at: QPointF,
) -> None:
    """
    Move to a point on a chart and click there.

    Parameters
    ----------
    chart : QWidget
        The chart.
    at : QPointF
        Where to click. Keyword-only.
    """
    mouse(chart, QMouseEvent.Type.MouseMove, at=at)
    mouse(chart, QMouseEvent.Type.MouseButtonPress, at=at)
    mouse(chart, QMouseEvent.Type.MouseButtonRelease, at=at)


def test_a_bar_chart_highlights_the_period_under_the_pointer_and_announces_a_click_on_it(app: QApplication) -> None:
    """
    Check that pointing at a period highlights it, a click on it is announced, and an empty period cannot be clicked.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.StackedBarChart("Questions")
    chart.resize(400, 300)
    chart.set_data(["a", "b", "c"], right=[3, 0, 2], wrong=[1, 0, 2])
    got: list[object] = []
    chart.clicked.connect(got.append)
    plot = chart._plot()
    columns = [QPointF(c, plot.center().y()) for c in chart._centres()]
    mouse(chart, QMouseEvent.Type.MouseMove, at=columns[0])
    assert chart.hovered == 0 and chart.cursor().shape() == Qt.CursorShape.PointingHandCursor
    green = QColor("#2e7d32")
    assert chart._tone(0, colour=green).lightness() > green.lightness()  # the bar under the pointer is brighter
    assert chart._tone(2, colour=green).alphaF() < 1.0  # and the others are fainter
    mouse(chart, QMouseEvent.Type.MouseMove, at=columns[1])  # nothing was answered in the middle period
    assert chart.hovered is None and chart.cursor().shape() == Qt.CursorShape.ArrowCursor
    click(chart, at=columns[1])
    assert got == []
    click(chart, at=columns[2])
    assert got == [2]
    assert chart.grab().toImage() != ink_image_without_highlight(chart)


def ink_image_without_highlight(
    chart: charts.HeatmapChart | charts.LineChart | charts.HBarChart | charts.StackedBarChart,
) -> QImage:
    """
    Draw a chart with nothing highlighted, to compare with how it looks when something is.

    Parameters
    ----------
    chart : charts._Chart
        The chart. Its highlight is cleared.

    Returns
    -------
    QImage
        The picture.
    """
    chart.hovered = chart.selected = None
    return chart.grab().toImage()


def test_a_press_that_does_not_come_up_on_the_same_item_is_not_a_click(app: QApplication) -> None:
    """
    Check that pressing on one period and releasing on another is not a click, and that leaving the chart clears the highlight.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.StackedBarChart("Questions")
    chart.resize(400, 300)
    chart.set_data(["a", "b"], right=[3, 3], wrong=[0, 0])
    got: list[object] = []
    chart.clicked.connect(got.append)
    first, second = (QPointF(c, chart._plot().center().y()) for c in chart._centres())
    mouse(chart, QMouseEvent.Type.MouseButtonPress, at=first)
    mouse(chart, QMouseEvent.Type.MouseButtonRelease, at=second)
    mouse(chart, QMouseEvent.Type.MouseButtonPress, at=first, button=Qt.MouseButton.RightButton)
    mouse(chart, QMouseEvent.Type.MouseButtonRelease, at=first, button=Qt.MouseButton.RightButton)
    assert got == []
    chart.hovered = 0
    chart.leaveEvent(QEvent(QEvent.Type.Leave))
    assert chart.hovered is None


def test_a_line_chart_can_be_clicked_where_it_has_a_value(app: QApplication) -> None:
    """
    Check that a point of a line chart can be clicked, and a gap in the line cannot.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.LineChart("Speed", fmt=lambda v: f"{v:.1f}")
    chart.resize(400, 300)
    chart.set_data(["a", "b", "c"], values=[2.0, None, 5.0])
    got: list[object] = []
    chart.clicked.connect(got.append)
    for centre in chart._centres():
        click(chart, at=QPointF(centre, chart._plot().center().y()))
    assert got == [0, 2]
    chart.set_selected(0)
    assert chart.grab().toImage() != ink_image_without_highlight(chart)


def test_a_row_of_the_bar_list_highlights_and_announces_a_click(app: QApplication) -> None:
    """
    Check that a row of the horizontal bar chart is highlighted under the pointer and announced when it is clicked.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    chart = charts.HBarChart("By exercise")
    chart.resize(400, 200)
    chart.set_data([("A", 50.0, "50%"), ("B", 80.0, "80%")])
    got: list[object] = []
    chart.clicked.connect(got.append)
    second = QPointF(100, chart.TOP + chart.ROW * 1.5)
    mouse(chart, QMouseEvent.Type.MouseMove, at=second)
    assert chart.hovered == 1
    click(chart, at=second)
    assert got == [1]
    mouse(chart, QMouseEvent.Type.MouseMove, at=QPointF(100, chart.TOP + chart.ROW * 5))  # below the last row
    assert chart.hovered is None
    chart.set_selected(0)
    assert chart.grab().toImage() != ink_image_without_highlight(chart)


def test_the_calendar_emphasises_a_day_and_announces_a_click_only_on_days_with_answers(app: QApplication) -> None:
    """
    Check that a day of the calendar can be clicked only if questions were answered on it, and is emphasised when pointed at.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    today = date(2026, 11, 13)
    chart = calendar(today)
    cell, (x0, y0) = chart._cell(), chart._origin()
    got: list[object] = []
    chart.clicked.connect(got.append)
    friday, thursday = QPointF(x0 + 52.5 * cell, y0 + 4.5 * cell), QPointF(x0 + 52.5 * cell, y0 + 3.5 * cell)
    click(chart, at=thursday)  # the 12th had no answers
    assert got == [] and chart.hovered is None
    mouse(chart, QMouseEvent.Type.MouseMove, at=friday)
    assert chart.hovered == today
    click(chart, at=friday)
    assert got == [today]
    pointed_at = chart.grab().toImage()
    assert pointed_at != ink_image_without_highlight(chart)
    chart.set_selected(today)  # the page is still showing that day, so it stays emphasised when the pointer moves away
    mouse(chart, QMouseEvent.Type.MouseMove, at=thursday)
    assert chart.hovered is None and chart.grab().toImage() == pointed_at
