"""The three charts: axes, bars and lines are drawn, empty data shows a message, and hovering explains a bar."""

import pytest
from alto.ui import charts
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest


def ink(
    widget,
    size=(560, 260),
) -> int:
    widget.resize(*size)
    image = widget.grab().toImage()
    return sum(
        1 for y in range(0, image.height(), 3) for x in range(0, image.width(), 3) if image.pixelColor(x, y).lightness() < 140
    )


def test_ticks_are_round_numbers_up_to_just_above_the_top():
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


def test_the_stacked_bar_chart_draws_bars_and_axes(app):
    chart = charts.StackedBarChart("Questions")
    chart.set_data(
        [f"d{i}" for i in range(12)],
        [
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
        [
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
    chart.set_data(["a"], [0], [0])  # nothing answered: only a message
    assert ink(chart) < with_bars
    chart.set_data([], [], [])
    assert ink(chart) > 0  # the title and the message


def test_a_bar_names_itself_when_hovered(
    app,
    monkeypatch,
):
    shown = []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    hidden = []
    monkeypatch.setattr(charts.QToolTip, "hideText", lambda: hidden.append(1))
    chart = charts.StackedBarChart("Questions")
    chart.resize(560, 260)
    chart.set_data(["Mon", "Tue"], [3, 1], [1, 0])
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
    one.set_data(["x"], [1], [0])
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
    app,
    fixed,
):
    chart = charts.LineChart("Accuracy", lambda v: f"{v:.0f}%", fixed_top=fixed)
    chart.set_data(["a", "b"], [None, None])
    message_only = ink(chart)  # nothing answered: only the title and a message
    chart.set_data(
        [f"d{i}" for i in range(8)],
        [
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
    chart.set_data([f"d{i}" for i in range(60)], [float(i) for i in range(60)])  # many points: smaller dots
    assert ink(chart) > message_only


def test_a_line_chart_point_names_itself_when_hovered(
    app,
    monkeypatch,
):
    shown = []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    chart = charts.LineChart("Speed", lambda v: f"{v:.1f} s")
    chart.resize(560, 260)
    chart.set_data(["Mon", "Tue", "Wed"], [2.0, None, 4.5])
    plot = chart._plot()
    for i, expected in ((0, "Mon\n2.0 s"), (1, "Tue\nno answers"), (2, "Wed\n4.5 s")):
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


def test_the_horizontal_bar_chart_lists_its_rows(app):
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


def test_the_chart_colours_follow_the_palette(app):
    chart = charts.StackedBarChart("Colours")
    assert chart._ink() != chart._grid() and chart._soft() is not None
    QTest.qWait(1)


def test_an_axis_with_no_labels_draws_nothing(app):
    from PySide6.QtGui import QImage, QPainter

    chart = charts.StackedBarChart("Nothing")
    image = QImage(200, 100, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    chart._category_axis(painter, [], [])
    painter.end()
    assert image.pixelColor(100, 90).alpha() == 0


def test_the_heatmap_shades_days_by_how_busy_they_were(app):
    from datetime import date, timedelta

    today = date(2026, 11, 13)  # a Friday
    chart = charts.HeatmapChart("Reviews")
    chart.set_data({today: 40, today - timedelta(days=1): 20, today - timedelta(days=2): 1}, today)
    assert chart.level(0) == 0 and chart.level(1) >= 1
    assert chart.level(40) == chart.LEVELS and chart.level(1) < chart.level(40)
    assert chart.first_day().weekday() == 0 and (today - chart.first_day()).days // 7 == 52
    busy = ink(chart, (760, 190))
    chart.set_data({}, today)
    assert ink(chart, (760, 190)) > 0 and ink(chart, (760, 190)) != busy  # still drawn, with a message


def test_the_heatmap_names_the_day_under_the_pointer(
    app,
    monkeypatch,
):
    from datetime import date

    shown, hidden = [], []
    monkeypatch.setattr(charts.QToolTip, "showText", lambda pos, text, widget=None: shown.append(text))
    monkeypatch.setattr(charts.QToolTip, "hideText", lambda: hidden.append(1))
    today = date(2026, 11, 13)
    chart = charts.HeatmapChart("Reviews")
    chart.resize(760, 190)
    chart.set_data({today: 3}, today)
    cell, (x0, y0) = chart._cell(), chart._origin()

    def move(
        x,
        y,
    ):
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

    move(x0 + 52.5 * cell, y0 + 4.5 * cell)  # last column, Friday
    assert shown[-1].startswith("Fri Nov 13, 2026") and "3 questions" in shown[-1]
    move(x0 + 52.5 * cell, y0 + 6.5 * cell)  # Sunday, in the future
    move(2, 2)
    assert len(hidden) == 2
    assert chart.day_at(QPointF(x0 + 0.5 * cell, y0 + 0.5 * cell)) == chart.first_day()
