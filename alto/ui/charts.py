"""
Small charts drawn with QPainter, in the application's theme colours.

Stacked bars, a line, horizontal bars and a calendar heatmap. Each has a title, draws a message when there is nothing to
show, and explains the bar or square under the pointer in a tooltip.

Examples
--------
>>> nice_ticks(13)
[0, 5, 10, 15]
>>> chart = StackedBarChart("Questions answered")
>>> chart.set_data(["Mon", "Tue"], right=[3, 1], wrong=[1, 0])
>>> chart.right, chart.wrong
([3, 1], [1, 0])
"""

from __future__ import annotations

import math
from collections.abc import (
    Callable,
    Sequence,
)
from datetime import (
    date,
    timedelta,
)

from PySide6.QtCore import (
    QEvent,
    QPointF,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QSizePolicy,
    QToolTip,
    QWidget,
)

from alto.ui.colors import blend

GOOD, BAD = QColor("#2e7d32"), QColor("#c62828")  # the same greens and reds the exercise feedback uses
FOCUS_LIGHTER = 125  # the element under the pointer is drawn this many percent as light (100 is unchanged)
DIM_OPACITY = 0.45  # the others are drawn this opaque while one is under the pointer


def nice_ticks(
    top: float,
    *,
    count: int = 4,
) -> list[float]:
    """
    Return round tick values from 0 up to just above a top value.

    Parameters
    ----------
    top : float
        The largest value to show.
    count : int, default 4
        Roughly how many ticks to aim for. Keyword-only.

    Returns
    -------
    list of float
        Ticks at round steps (1, 2, 2.5, 5 or 10 times a power of ten), starting at 0 and reaching at least `top`. Just
        0 and 1 when `top` is not positive.

    Examples
    --------
    >>> nice_ticks(13)
    [0, 5, 10, 15]
    >>> nice_ticks(8)[-1] >= 8
    True
    >>> nice_ticks(0)
    [0.0, 1.0]
    """
    if top <= 0:
        return [0.0, 1.0]
    raw = top / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(
        m * magnitude
        for m in (
            1,
            2,
            2.5,
            5,
            10,
        )
        if m * magnitude >= raw
    )
    n = math.ceil(top / step - 1e-9)
    return [i * step for i in range(n + 1)]


class _Chart(QWidget):
    """
    A titled plot area with a value axis on the left and labels along the bottom.

    The base of the other charts: it holds the title and labels, the plot area, the colours, and the shared drawing of the
    title, the axes and the hover tooltip.

    Attributes
    ----------
    LEFT, RIGHT, TOP, BOTTOM : int
        The space around the plot area, in pixels.
    title : str
        Drawn at the top left.
    empty : str
        The message drawn instead of the plot when there is nothing to show.
    labels : list of str
        The labels along the bottom.
    clicked : Signal
        Emitted with the item that was clicked: a period's index, a row's index, or a day. See `_item_at`.
    hovered : object
        The item under the pointer, or None. It is drawn brighter and the others fainter.
    selected : object
        The item the page is showing more about, or None. It stays emphasised. Set with `set_selected`.

    Examples
    --------
    >>> chart = _Chart("Accuracy", empty="No answers yet.")
    >>> chart.title, chart.empty
    ('Accuracy', 'No answers yet.')
    """

    LEFT, RIGHT, TOP, BOTTOM = 40, 12, 34, 26

    clicked = Signal(object)

    def __init__(
        self,
        title: str,
        *,
        empty: str = "Nothing to show for this selection.",
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty chart.

        Parameters
        ----------
        title : str
            Drawn at the top left.
        empty : str, default "Nothing to show for this selection."
            The message drawn when there is nothing to show. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the chart. Keyword-only.

        Examples
        --------
        >>> _Chart("Speed").minimumWidth()
        260
        """
        super().__init__(parent)
        self.title, self.empty = title, empty
        self.labels: list[str] = []
        self.hovered: object | None = None
        self.selected: object | None = None
        self._pressed: object | None = None
        self.setMinimumSize(260, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    # -- pointing and clicking -----------------------------------------------------------------------------------------

    def _item_at(self, pos: QPointF) -> object | None:
        """
        Return the item that can be clicked at a point.

        The base chart has none. Each chart says what its items are: a period (by index), a row (by index) or a day.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        object or None
            The item, or None if the point is not on one that has anything to show.

        Examples
        --------
        >>> _Chart("Speed")._item_at(QPointF(10, 10)) is None
        True
        """
        return None

    def _set_hovered(self, item: object | None) -> None:
        """
        Highlight an item as the one under the pointer, with a pointing hand over it, and repaint if that changed.

        Parameters
        ----------
        item : object or None
            The item, or None when the pointer is on nothing clickable.

        Examples
        --------
        >>> chart = _Chart("Speed")
        >>> chart._set_hovered(2)
        >>> chart.hovered, chart.cursor().shape() == Qt.CursorShape.PointingHandCursor
        (2, True)
        >>> chart._set_hovered(None)
        >>> chart.hovered, chart.cursor().shape() == Qt.CursorShape.ArrowCursor
        (None, True)
        """
        if item != self.hovered:
            self.hovered = item
            self.update()
        self.setCursor(Qt.CursorShape.ArrowCursor if item is None else Qt.CursorShape.PointingHandCursor)

    def set_selected(self, item: object | None) -> None:
        """
        Keep an item highlighted, as the one the page is showing more about.

        Parameters
        ----------
        item : object or None
            The item, or None to clear the selection.

        Examples
        --------
        >>> chart = _Chart("Speed")
        >>> chart.set_selected(3)
        >>> chart.selected
        3
        """
        if item != self.selected:
            self.selected = item
            self.update()

    def _tone(
        self,
        item: object,
        *,
        colour: QColor,
    ) -> QColor:
        """
        Return the colour to draw an element in: brighter if it is under the pointer or selected, fainter if another is.

        With nothing under the pointer and nothing selected, every element is drawn in its own colour.

        Parameters
        ----------
        item : object
            The element about to be drawn: a period or row by index, or a day.
        colour : QColor
            The colour it is drawn in when nothing is emphasised. Keyword-only.

        Returns
        -------
        QColor
            The colour to draw it in. The argument is not changed.

        Examples
        --------
        >>> chart = _Chart("Speed")
        >>> chart._tone(0, colour=QColor("#2e7d32")).name()  # nothing emphasised
        '#2e7d32'
        >>> chart.hovered = 1
        >>> chart._tone(1, colour=QColor("#2e7d32")).lightness() > QColor("#2e7d32").lightness()
        True
        >>> chart._tone(0, colour=QColor("#2e7d32")).alphaF() < 1.0
        True
        """
        if self.hovered is None and self.selected is None:
            return colour
        if item in (self.hovered, self.selected):
            return colour.lighter(FOCUS_LIGHTER)
        faint = QColor(colour)
        faint.setAlphaF(colour.alphaF() * DIM_OPACITY)
        return faint

    def _column_at(self, pos: QPointF) -> int | None:
        """
        Return the period whose column of the plot a point is in, for the charts that have a column for each label.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        int or None
            The index of the label, or None if there are none or the point is outside the plot.

        Examples
        --------
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> chart.labels = ["a", "b"]
        >>> area = chart._plot()
        >>> chart._column_at(QPointF(area.left() + 5, area.center().y())), chart._column_at(QPointF(5, 5))
        (0, None)
        """
        plot, n = self._plot(), len(self.labels)
        if not n or not plot.contains(pos):
            return None
        return min(int((pos.x() - plot.left()) // (plot.width() / n)), n - 1)

    def _track(self, event: QMouseEvent) -> None:
        """
        Follow the pointer: highlight the item under it.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> chart = _Chart("Speed")
        >>> point = QPointF(5, 5)
        >>> chart._track(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                          Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        >>> chart.hovered is None
        True
        """
        self._set_hovered(self._item_at(event.position()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Remember which item a left click went down on.

        Parameters
        ----------
        event : QMouseEvent
            The mouse press.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> chart = _Chart("Speed")
        >>> point = QPointF(5, 5)
        >>> chart.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
        ...                                   Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        >>> chart._pressed is None
        True
        """
        self._pressed = self._item_at(event.position()) if event.button() == Qt.MouseButton.LeftButton else None

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Announce the item that was clicked: the one the button went down on and came up on.

        Pressing on one item and releasing on another, or off the chart, is not a click.

        Parameters
        ----------
        event : QMouseEvent
            The mouse release.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> class Everywhere(_Chart):  # a chart with an item under every point
        ...     def _item_at(self, pos):
        ...         return 4
        >>> chart = Everywhere("Speed")
        >>> got = []
        >>> _ = chart.clicked.connect(got.append)
        >>> point = QPointF(5, 5)
        >>> press = QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
        ...                     Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        >>> release = QMouseEvent(QEvent.Type.MouseButtonRelease, point, point, Qt.MouseButton.LeftButton,
        ...                       Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        >>> chart.mousePressEvent(press)
        >>> chart.mouseReleaseEvent(release)
        >>> got
        [4]
        """
        item, pressed, self._pressed = self._item_at(event.position()), self._pressed, None
        if event.button() == Qt.MouseButton.LeftButton and item is not None and item == pressed:
            self.clicked.emit(item)

    def leaveEvent(self, event: QEvent) -> None:
        """
        Remove the highlight and the tooltip when the pointer leaves the chart.

        Parameters
        ----------
        event : QEvent
            The leave event.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> chart = _Chart("Speed")
        >>> chart._set_hovered(1)
        >>> chart.leaveEvent(QEvent(QEvent.Type.Leave))
        >>> chart.hovered is None
        True
        """
        self._set_hovered(None)
        QToolTip.hideText()
        super().leaveEvent(event)

    # -- colours -----------------------------------------------------------------------------------------------------

    def _ink(self) -> QColor:
        """
        Return the colour of text and lines in the current theme.

        Returns
        -------
        QColor
            The palette's text colour.

        Examples
        --------
        >>> _Chart("Speed")._ink().isValid()
        True
        """
        return self.palette().color(QPalette.ColorRole.Text)

    def _soft(self) -> QColor:
        """
        Return a muted colour for axis labels, between the background and the text colour.

        Returns
        -------
        QColor
            The blended colour.

        Examples
        --------
        >>> _Chart("Speed")._soft().isValid()
        True
        """
        return blend(self.palette().color(QPalette.ColorRole.Base), b=self._ink(), t=0.55)

    def _grid(self) -> QColor:
        """
        Return a faint colour for grid lines, close to the background.

        Returns
        -------
        QColor
            The blended colour.

        Examples
        --------
        >>> _Chart("Speed")._grid().isValid()
        True
        """
        return blend(self.palette().color(QPalette.ColorRole.Base), b=self._ink(), t=0.16)

    def _plot(self) -> QRectF:
        """
        Return the area the data is drawn in.

        Returns
        -------
        QRectF
            The widget less the margins for the title, the value axis and the labels, and never smaller than 10 by 10.

        Examples
        --------
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> area = chart._plot()
        >>> (area.x(), area.y(), area.width(), area.height())
        (40.0, 34.0, 348.0, 240.0)
        """
        return QRectF(
            self.LEFT,
            self.TOP,
            max(self.width() - self.LEFT - self.RIGHT, 10),
            max(self.height() - self.TOP - self.BOTTOM, 10),
        )

    # -- shared drawing ---------------------------------------------------------------------------------------------------

    def _frame(self, p: QPainter) -> None:
        """
        Prepare the painter and draw the title.

        Parameters
        ----------
        p : QPainter
            The painter, which is set to anti-alias and left with the normal font.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> image = QImage(400, 300, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> chart._frame(painter)
        >>> painter.end()
        True
        """
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self._ink())
        title_font = QFont(self.font())
        title_font.setBold(True)
        p.setFont(title_font)
        p.drawText(
            QRectF(
                0,
                4,
                self.width(),
                22,
            ),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )
        p.setFont(self.font())

    def _message(
        self,
        p: QPainter,
        *,
        text: str,
    ) -> None:
        """
        Draw a message in the middle of the plot area.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        text : str
            The message, which wraps to fit. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> image = QImage(400, 300, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> chart._message(painter, text="Nothing to show.")
        >>> painter.end()
        True
        """
        p.setPen(self._soft())
        p.drawText(self._plot(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    def _value_axis(
        self,
        p: QPainter,
        *,
        ticks: Sequence[float],
        top: float,
        fmt: Callable[[float], str],
    ) -> None:
        """
        Draw the horizontal grid lines and the value labels down the left.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        ticks : sequence of float
            The values to mark. Keyword-only.
        top : float
            The value at the top of the plot area. Keyword-only.
        fmt : callable
            Turns a value into its label. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> image = QImage(400, 300, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> chart._value_axis(painter, ticks=[0, 5, 10], top=10, fmt=lambda v: f"{v:g}")
        >>> painter.end()
        True
        """
        plot = self._plot()
        small = QFont(self.font())
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        p.setFont(small)
        for t in ticks:
            y = plot.bottom() - plot.height() * t / top
            p.setPen(QPen(self._grid(), 1))
            p.drawLine(QPointF(plot.left(), round(y) + 0.5), QPointF(plot.right(), round(y) + 0.5))
            p.setPen(self._soft())
            p.drawText(
                QRectF(
                    0,
                    y - 8,
                    self.LEFT - 6,
                    16,
                ),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                fmt(t),
            )
        p.setFont(self.font())

    def _category_axis(
        self,
        p: QPainter,
        *,
        centres: Sequence[float],
        labels: Sequence[str],
    ) -> None:
        """
        Label some of the positions along the bottom, skipping as many as needed so none overlap.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        centres : sequence of float
            The x position of each label's centre. Keyword-only.
        labels : sequence of str
            The labels. The newest (last) is always drawn. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> image = QImage(400, 300, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> chart._category_axis(painter, centres=[100.0, 200.0, 300.0], labels=["Mon", "Tue", "Wed"])
        >>> painter.end()
        True
        """
        if not labels:
            return
        small = QFont(self.font())
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        p.setFont(small)
        p.setPen(self._soft())
        widest = max(p.fontMetrics().horizontalAdvance(s) for s in labels) + 10
        every = max(1, math.ceil(widest / max(self._plot().width() / len(labels), 1)))
        for i in range(len(labels) - 1, -1, -every):  # count back from the latest, so the newest label is always there
            label_box = QRectF(
                centres[i] - widest / 2,
                self._plot().bottom() + 5,
                widest,
                16,
            )
            p.drawText(label_box, Qt.AlignmentFlag.AlignCenter, labels[i])
        p.setFont(self.font())

    def _hover(
        self,
        event: QMouseEvent,
        *,
        centres: Sequence[float],
        texts: Sequence[str],
    ) -> None:
        """
        Show a tooltip for the position nearest the pointer, or hide it when the pointer is outside the plot.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.
        centres : sequence of float
            The x position of each item. Keyword-only.
        texts : sequence of str
            The tooltip for each item. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> from PySide6.QtGui import QMouseEvent
        >>> chart = _Chart("Speed")
        >>> chart.resize(400, 300)
        >>> point = QPointF(100, 100)
        >>> event_ = QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                     Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        >>> chart._hover(event_, centres=[100.0, 200.0], texts=["First", "Second"])
        """
        if not centres:
            return
        x = event.position().x()
        i = min(range(len(centres)), key=lambda k: abs(centres[k] - x))
        if (
            self._plot()
            .adjusted(
                -4,
                -4,
                4,
                4,
            )
            .contains(event.position())
        ):
            QToolTip.showText(event.globalPosition().toPoint(), texts[i], self)
        else:
            QToolTip.hideText()


class StackedBarChart(_Chart):
    """
    Questions per period, the first-try right ones in green with the missed ones stacked above in red.

    Attributes
    ----------
    right : list of int
        Questions right first time, per period.
    wrong : list of int
        Questions missed, per period.

    Examples
    --------
    >>> chart = StackedBarChart("Questions answered per day")
    >>> chart.set_data(["Mon", "Tue", "Wed"], right=[3, 0, 5], wrong=[1, 2, 0])
    >>> chart.labels
    ['Mon', 'Tue', 'Wed']
    """

    def __init__(
        self,
        title: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty chart.

        Parameters
        ----------
        title : str
            Drawn at the top left.
        parent : QWidget or None, default None
            The widget that owns the chart. Keyword-only.

        Examples
        --------
        >>> StackedBarChart("Questions").right
        []
        """
        super().__init__(title, parent=parent)
        self.right: list[int] = []
        self.wrong: list[int] = []

    def set_data(
        self,
        labels: Sequence[str],
        *,
        right: Sequence[int],
        wrong: Sequence[int],
    ) -> None:
        """
        Show a count of right and missed questions for each period.

        Parameters
        ----------
        labels : sequence of str
            The label of each period.
        right : sequence of int
            Questions right first time in each period. Keyword-only.
        wrong : sequence of int
            Questions missed in each period. Keyword-only.

        Examples
        --------
        >>> chart = StackedBarChart("Questions")
        >>> chart.set_data(["a", "b"], right=[2, 0], wrong=[0, 4])
        >>> chart.right, chart.wrong
        ([2, 0], [0, 4])
        """
        self.labels, self.right, self.wrong = list(labels), list(right), list(wrong)
        self.update()

    def _centres(self) -> list[float]:
        """
        Return the x position of the middle of each period's bar.

        Returns
        -------
        list of float
            One per label, spread evenly across the plot area.

        Examples
        --------
        >>> chart = StackedBarChart("Questions")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], right=[1, 1], wrong=[0, 0])
        >>> [round(x) for x in chart._centres()]
        [127, 301]
        """
        plot, n = self._plot(), max(len(self.labels), 1)
        return [plot.left() + plot.width() * (i + 0.5) / n for i in range(len(self.labels))]

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the axes and a bar for each period, or a message when no questions were answered.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> chart = StackedBarChart("Questions")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], right=[3, 1], wrong=[1, 0])
        >>> chart.grab().isNull()
        False
        """
        p = QPainter(self)
        self._frame(p)
        totals = [r + w for r, w in zip(self.right, self.wrong)]
        if not any(totals):
            self._message(p, text=self.empty)
            return
        ticks = nice_ticks(max(totals))
        top = ticks[-1]
        self._value_axis(
            p,
            ticks=ticks,
            top=top,
            fmt=lambda v: f"{v:g}",
        )
        plot, n = self._plot(), len(self.labels)
        slot = plot.width() / n
        bar = min(max(slot * 0.68, 2.0), 38.0)
        centres = self._centres()
        p.setPen(Qt.PenStyle.NoPen)
        for i, (cx, r, w) in enumerate(zip(centres, self.right, self.wrong)):
            h_right, h_wrong = plot.height() * r / top, plot.height() * w / top
            if r:
                p.setBrush(self._tone(i, colour=GOOD))
                p.drawRoundedRect(
                    QRectF(
                        cx - bar / 2,
                        plot.bottom() - h_right,
                        bar,
                        h_right,
                    ),
                    2,
                    2,
                )
            if w:
                p.setBrush(self._tone(i, colour=BAD))
                p.drawRoundedRect(
                    QRectF(
                        cx - bar / 2,
                        plot.bottom() - h_right - h_wrong,
                        bar,
                        h_wrong,
                    ),
                    2,
                    2,
                )
        self._category_axis(p, centres=centres, labels=self.labels)

    def _item_at(self, pos: QPointF) -> int | None:
        """
        Return the period whose column the point is in, if anything was answered in it.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        int or None
            The period's index, or None if the point is outside the plot or the period is empty.

        Examples
        --------
        >>> chart = StackedBarChart("Questions")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], right=[3, 0], wrong=[1, 0])
        >>> area = chart._plot()
        >>> y = area.center().y()
        >>> chart._item_at(QPointF(area.left() + 5, y)), chart._item_at(QPointF(area.right() - 5, y))
        (0, None)
        >>> chart._item_at(QPointF(5, 5)) is None  # outside the plot
        True
        """
        i = self._column_at(pos)
        return i if i is not None and self.right[i] + self.wrong[i] else None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Explain the bar under the pointer in a tooltip.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> from PySide6.QtGui import QMouseEvent
        >>> chart = StackedBarChart("Questions")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["Mon", "Tue"], right=[3, 1], wrong=[1, 0])
        >>> point = QPointF(chart._centres()[0], chart._plot().center().y())
        >>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        """
        self._track(event)
        self._hover(
            event,
            centres=self._centres(),
            texts=[
                f"{lab}\n{r + w} question{'s' if r + w != 1 else ''}: {r} right first time, {w} missed"
                for lab, r, w in zip(self.labels, self.right, self.wrong)
            ],
        )


class LineChart(_Chart):
    """
    A value per period joined by a line.

    Periods with no answers leave a gap rather than a zero.

    Attributes
    ----------
    fmt : callable
        Turns a value into its label, for the axis and the tooltip.
    fixed_top : float or None
        The value at the top of the plot; the largest value, rounded up, if None.
    values : list of float or None
        The value of each period, or None for a gap.

    Examples
    --------
    >>> chart = LineChart("Right first time", fmt=lambda v: f"{v:.0f}%", fixed_top=100)
    >>> chart.set_data(["Mon", "Tue", "Wed"], values=[40.0, None, 80.0])
    >>> chart.values
    [40.0, None, 80.0]
    """

    def __init__(
        self,
        title: str,
        *,
        fmt: Callable[[float], str],
        fixed_top: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty chart.

        Parameters
        ----------
        title : str
            Drawn at the top left.
        fmt : callable
            Turns a value into its label. Keyword-only.
        fixed_top : float or None, default None
            The value at the top of the plot (such as 100 for a percentage); the largest value, rounded up, if None. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the chart. Keyword-only.

        Examples
        --------
        >>> LineChart("Speed", fmt=lambda v: f"{v:.1f} s").fixed_top is None
        True
        """
        super().__init__(title, parent=parent)
        self.fmt, self.fixed_top = fmt, fixed_top
        self.values: list[float | None] = []

    def set_data(
        self,
        labels: Sequence[str],
        *,
        values: Sequence[float | None],
    ) -> None:
        """
        Show a value for each period.

        Parameters
        ----------
        labels : sequence of str
            The label of each period.
        values : sequence of float or None
            The value of each period; None leaves a gap. Keyword-only.

        Examples
        --------
        >>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
        >>> chart.set_data(["a", "b"], values=[2.5, None])
        >>> chart.labels
        ['a', 'b']
        """
        self.labels, self.values = list(labels), list(values)
        self.update()

    def _centres(self) -> list[float]:
        """
        Return the x position of each period's point.

        Returns
        -------
        list of float
            One per label, spread evenly across the plot area.

        Examples
        --------
        >>> chart = LineChart("Speed", fmt=str)
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], values=[1.0, 2.0])
        >>> [round(x) for x in chart._centres()]
        [127, 301]
        """
        plot, n = self._plot(), len(self.labels)
        return [plot.left() + plot.width() * (i + 0.5) / n for i in range(n)]

    def _top_and_ticks(self) -> tuple[float, list[float]]:
        """
        Return the value at the top of the plot and the ticks to mark.

        Returns
        -------
        tuple of (float, list of float)
            The fixed top with a tick every quarter of it, or the round tick just above the largest value.

        Examples
        --------
        >>> chart = LineChart("Right first time", fmt=str, fixed_top=100)
        >>> chart._top_and_ticks()
        (100, [0.0, 25.0, 50.0, 75.0, 100.0])
        """
        if self.fixed_top:
            step = self.fixed_top / 4
            return self.fixed_top, [step * i for i in range(5)]
        ticks = nice_ticks(max(v for v in self.values if v is not None))
        return ticks[-1], ticks

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the axes, the line (one run at a time, so gaps show) and a dot for each value.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b", "c"], values=[2.0, None, 3.0])
        >>> chart.grab().isNull()
        False
        """
        p = QPainter(self)
        self._frame(p)
        present = [v for v in self.values if v is not None]
        if not present:
            self._message(p, text=self.empty)
            return
        top, ticks = self._top_and_ticks()
        self._value_axis(
            p,
            ticks=ticks,
            top=top,
            fmt=self.fmt,
        )
        plot, centres = self._plot(), self._centres()
        points = [
            QPointF(cx, plot.bottom() - plot.height() * min(v, top) / top) if v is not None else None
            for cx, v in zip(centres, self.values)
        ]
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        faint = QColor(accent)
        if self.hovered is not None or self.selected is not None:
            faint.setAlphaF(DIM_OPACITY)  # the line steps back so the point being pointed at stands out
        run: list[QPointF] = []
        for pt in [*points, None]:  # draw each unbroken run of points as one line
            if pt is not None:
                run.append(pt)
                continue
            if len(run) > 1:
                path = QPainterPath(run[0])
                for q in run[1:]:
                    path.lineTo(q)
                p.setPen(
                    QPen(
                        faint,
                        2.2,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    ),
                )
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
            run = []
        p.setPen(QPen(self.palette().color(QPalette.ColorRole.Base), 1.5))
        radius = 3.6 if len(self.labels) <= 40 else 2.4
        for i, pt in enumerate(points):
            if pt is not None:
                p.setBrush(self._tone(i, colour=accent))
                grown = radius * 1.4 if i in (self.hovered, self.selected) else radius  # the point being pointed at is larger
                p.drawEllipse(pt, grown, grown)
        self._category_axis(p, centres=centres, labels=self.labels)

    def _item_at(self, pos: QPointF) -> int | None:
        """
        Return the period whose column the point is in, if anything was answered in it.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        int or None
            The period's index, or None if the point is outside the plot or the period is empty.

        Examples
        --------
        >>> chart = LineChart("Speed", fmt=str)
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], values=[3.0, None])
        >>> area = chart._plot()
        >>> y = area.center().y()
        >>> chart._item_at(QPointF(area.left() + 5, y)), chart._item_at(QPointF(area.right() - 5, y))
        (0, None)
        >>> chart._item_at(QPointF(5, 5)) is None  # outside the plot
        True
        """
        i = self._column_at(pos)
        return i if i is not None and self.values[i] is not None else None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Say what the value under the pointer is in a tooltip.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> from PySide6.QtGui import QMouseEvent
        >>> chart = LineChart("Speed", fmt=lambda v: f"{v:.1f} s")
        >>> chart.resize(400, 300)
        >>> chart.set_data(["a", "b"], values=[2.0, 3.0])
        >>> point = QPointF(chart._centres()[0], chart._plot().center().y())
        >>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        """
        self._track(event)
        self._hover(
            event,
            centres=self._centres(),
            texts=[f"{lab}\n{self.fmt(v) if v is not None else 'no answers'}" for lab, v in zip(self.labels, self.values)],
        )


class HBarChart(_Chart):
    """
    One bar per name, on a fixed 0-100 scale, each with its value at the end.

    Attributes
    ----------
    ROW : int
        The height of each bar's row, in pixels.
    rows : list of tuple of (str, float, str)
        For each bar, its name, its value from 0 to 100 and the text shown at its end.

    Examples
    --------
    >>> chart = HBarChart("Right first time, by exercise")
    >>> chart.set_data([("Intervals", 77.0, "77%  ·  52 q"), ("Chords", 88.0, "88%  ·  48 q")])
    >>> len(chart.rows)
    2
    """

    ROW = 26

    def __init__(
        self,
        title: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty chart.

        Parameters
        ----------
        title : str
            Drawn at the top left.
        parent : QWidget or None, default None
            The widget that owns the chart. Keyword-only.

        Examples
        --------
        >>> HBarChart("By exercise").rows
        []
        """
        super().__init__(title, parent=parent)
        self.rows: list[tuple[str, float, str]] = []

    def set_data(self, rows: Sequence[tuple[str, float, str]]) -> None:
        """
        Show a bar for each name, and make the chart tall enough for them.

        Parameters
        ----------
        rows : sequence of tuple of (str, float, str)
            Each bar's name, its value from 0 to 100, and the text shown at the end of the bar.

        Examples
        --------
        >>> chart = HBarChart("By exercise")
        >>> chart.set_data([(f"Exercise {i}", 50.0, "50%") for i in range(10)])
        >>> chart.minimumHeight()
        306
        """
        self.rows = list(rows)
        self.setMinimumHeight(max(190, self.TOP + 12 + self.ROW * len(self.rows)))
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw a bar with its name and value for each row, or a message when there are none.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> chart = HBarChart("By exercise")
        >>> chart.resize(400, 300)
        >>> chart.set_data([("Intervals", 77.0, "77%")])
        >>> chart.grab().isNull()
        False
        """
        p = QPainter(self)
        self._frame(p)
        if not self.rows:
            self._message(p, text=self.empty)
            return
        label_w = min(max(p.fontMetrics().horizontalAdvance(n) for n, _, _ in self.rows) + 12, self.width() * 0.45)
        value_w = max(p.fontMetrics().horizontalAdvance(t) for _, _, t in self.rows) + 10
        x0, x1 = label_w, self.width() - value_w - 8
        for i, (name, value, text) in enumerate(self.rows):
            y = self.TOP + i * self.ROW
            p.setPen(self._tone(i, colour=self._ink()))
            p.drawText(
                QRectF(
                    0,
                    y,
                    label_w - 8,
                    self.ROW - 6,
                ),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                p.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, int(label_w - 8)),
            )
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._grid())
            p.drawRoundedRect(
                QRectF(
                    x0,
                    y + 4,
                    x1 - x0,
                    self.ROW - 14,
                ),
                4,
                4,
            )
            p.setBrush(self._tone(i, colour=self.palette().color(QPalette.ColorRole.Highlight)))
            p.drawRoundedRect(
                QRectF(
                    x0,
                    y + 4,
                    max((x1 - x0) * value / 100, 3),
                    self.ROW - 14,
                ),
                4,
                4,
            )
            p.setPen(self._tone(i, colour=self._soft()))
            p.drawText(
                QRectF(
                    x1 + 6,
                    y,
                    value_w,
                    self.ROW - 6,
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

    def _item_at(self, pos: QPointF) -> int | None:
        """
        Return the row the point is on.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        int or None
            The row's index, or None if the point is above the first row or below the last.

        Examples
        --------
        >>> chart = HBarChart("By exercise")
        >>> chart.set_data([("A", 50.0, "50%"), ("B", 80.0, "80%")])
        >>> chart._item_at(QPointF(10, chart.TOP + chart.ROW * 1.5)), chart._item_at(QPointF(10, chart.TOP - 5)) is None
        (1, True)
        """
        i = int((pos.y() - self.TOP) // self.ROW)
        return i if pos.y() >= self.TOP and 0 <= i < len(self.rows) else None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Highlight the row under the pointer.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> chart = HBarChart("By exercise")
        >>> chart.set_data([("A", 50.0, "50%")])
        >>> point = QPointF(10, chart.TOP + chart.ROW / 2)
        >>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        >>> chart.hovered
        0
        """
        self._track(event)


class HeatmapChart(_Chart):
    """
    A calendar of reviews: a column per week (Monday to Sunday), a square per day, darker the more questions.

    Attributes
    ----------
    LEVELS : int
        The number of shades above "none".
    counts : dict of date to int
        Questions answered on each day that had any.
    today : date
        The last day shown.
    weeks : int
        How many weeks are shown, counting this one.

    Examples
    --------
    >>> chart = HeatmapChart("Reviews")
    >>> chart.set_data({date(2026, 11, 13): 12}, today=date(2026, 11, 13))
    >>> chart.counts
    {datetime.date(2026, 11, 13): 12}
    """

    LEVELS = 4  # shades above "none"
    LEFT, TOP, BOTTOM = 34, 44, 30

    def __init__(
        self,
        title: str,
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create an empty calendar for the last 53 weeks.

        Parameters
        ----------
        title : str
            Drawn at the top left.
        parent : QWidget or None, default None
            The widget that owns the chart. Keyword-only.

        Examples
        --------
        >>> HeatmapChart("Reviews").weeks
        53
        """
        super().__init__(title, parent=parent)
        self.counts: dict[date, int] = {}
        self.today = date.today()
        self.weeks = 53
        self.setMinimumSize(260, 190)

    def set_data(
        self,
        counts: dict[date, int],
        *,
        today: date,
        weeks: int = 53,
    ) -> None:
        """
        Show how many questions were answered on each day.

        Parameters
        ----------
        counts : dict of date to int
            Questions answered on each day that had any.
        today : date
            The last day to show. Keyword-only.
        weeks : int, default 53
            How many weeks to show, counting this one. Keyword-only.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.set_data({}, today=date(2026, 11, 13), weeks=26)
        >>> chart.weeks
        26
        """
        self.counts, self.today, self.weeks = dict(counts), today, weeks
        self.update()

    def first_day(self) -> date:
        """
        Return the first day shown: the Monday that starts the first week.

        Returns
        -------
        date
            A Monday.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.set_data({}, today=date(2026, 11, 13))
        >>> chart.first_day(), chart.first_day().weekday()
        (datetime.date(2025, 11, 10), 0)
        """
        return self.today - timedelta(days=self.today.weekday() + 7 * (self.weeks - 1))

    def level(self, count: int) -> int:
        """
        Return how dark a day's square is.

        Parameters
        ----------
        count : int
            Questions answered that day.

        Returns
        -------
        int
            0 for no questions, otherwise 1 to `LEVELS` by how the day compares with the busiest. The scale is in quarters of the
            90th-percentile day, so one huge day does not flatten everything else.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.set_data({date(2026, 11, 13): 40, date(2026, 11, 12): 20, date(2026, 11, 11): 1}, today=date(2026, 11, 13))
        >>> chart.level(0), chart.level(1), chart.level(40)
        (0, 1, 4)
        """
        if count <= 0:
            return 0
        busy = sorted(self.counts.values())
        top = max(busy[int(0.9 * (len(busy) - 1))], 1)
        return min(self.LEVELS, max(1, math.ceil(self.LEVELS * count / top)))

    def _cell(self) -> float:
        """
        Return the size of one day's square.

        Returns
        -------
        float
            In pixels: what fits across the weeks, but between 4 and 18.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.resize(2000, 190)
        >>> chart._cell()
        18.0
        """
        return max(min((self.width() - self.LEFT - self.RIGHT) / self.weeks, 18.0), 4.0)

    def _origin(self) -> tuple[float, float]:
        """
        Return where the top left square is drawn.

        Returns
        -------
        tuple of (float, float)
            Its x and y position, in pixels.

        Examples
        --------
        >>> HeatmapChart("Reviews")._origin()
        (34.0, 44.0)
        """
        return float(self.LEFT), float(self.TOP)

    def _shade(self, level: int) -> QColor:
        """
        Return the colour of a square.

        Parameters
        ----------
        level : int
            0 for no questions, up to `LEVELS` for the busiest days.

        Returns
        -------
        QColor
            The grid colour for 0, otherwise a green that deepens with the level.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart._shade(0) == chart._grid()
        True
        >>> chart._shade(4).lightness() < chart._shade(1).lightness()
        True
        """
        base = self.palette().color(QPalette.ColorRole.Base)
        if level == 0:
            return self._grid()
        return blend(base, b=GOOD, t=0.25 + 0.75 * level / self.LEVELS)

    def day_at(self, pos: QPointF) -> date | None:
        """
        Return the day whose square is under a point.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        date or None
            The day, or None if the point is outside the calendar or on a day that has not happened yet.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.resize(760, 190)
        >>> chart.set_data({}, today=date(2026, 11, 13))
        >>> cell_, (x0_, y0_) = chart._cell(), chart._origin()
        >>> chart.day_at(QPointF(x0_ + 52.5 * cell_, y0_ + 4.5 * cell_))  # the last column, Friday
        datetime.date(2026, 11, 13)
        >>> chart.day_at(QPointF(x0_ + 52.5 * cell_, y0_ + 6.5 * cell_)) is None  # Sunday: not yet
        True
        """
        cell, (x0, y0) = self._cell(), self._origin()
        col, row = int((pos.x() - x0) // cell), int((pos.y() - y0) // cell)
        if pos.x() < x0 or pos.y() < y0 or not (0 <= col < self.weeks and 0 <= row < 7):
            return None
        day = self.first_day() + timedelta(days=7 * col + row)
        return day if day <= self.today else None

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the month and weekday labels, a square for each day, and the Less-More legend.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.resize(760, 190)
        >>> chart.set_data({date(2026, 11, 13): 5}, today=date(2026, 11, 13))
        >>> chart.grab().isNull()
        False
        """
        p = QPainter(self)
        self._frame(p)
        cell, (x0, y0) = self._cell(), self._origin()
        gap = 2.0 if cell >= 8 else 1.0
        small = QFont(self.font())
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        p.setFont(small)
        first = self.first_day()
        p.setPen(self._soft())
        for row, name in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
            label_box = QRectF(
                0,
                y0 + row * cell,
                self.LEFT - 6,
                cell,
            )
            p.drawText(label_box, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)
        last_month_label = -99.0
        p.setPen(Qt.PenStyle.NoPen)
        for col in range(self.weeks):
            monday = first + timedelta(days=7 * col)
            if monday > self.today:
                break
            x = x0 + col * cell
            if (monday.day <= 7 or col == 0) and x - last_month_label >= 30:  # label the week a month starts in
                p.setPen(self._soft())
                month_box = QRectF(
                    x,
                    y0 - 20,
                    40,
                    16,
                )
                p.drawText(month_box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, monday.strftime("%b"))
                p.setPen(Qt.PenStyle.NoPen)
                last_month_label = x
            for row in range(7):
                day = monday + timedelta(days=row)
                if day > self.today:
                    break
                square = QRectF(
                    x,
                    y0 + row * cell,
                    cell - gap,
                    cell - gap,
                )
                p.setBrush(self._tone(day, colour=self._shade(self.level(self.counts.get(day, 0)))))
                p.drawRoundedRect(square, 2, 2)
        # the legend, bottom right: Less [squares] More
        y = y0 + 7 * cell + 8
        box = 11.0
        right = self.width() - self.RIGHT
        p.setPen(self._soft())
        more_w = p.fontMetrics().horizontalAdvance("More")
        p.drawText(
            QRectF(
                right - more_w,
                y - 2,
                more_w,
                16,
            ),
            Qt.AlignmentFlag.AlignVCenter,
            "More",
        )
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(self.LEVELS, -1, -1):
            p.setBrush(self._shade(i))
            p.drawRoundedRect(
                QRectF(
                    right - more_w - 6 - (self.LEVELS + 1 - i) * (box + 3) + 3,
                    y,
                    box,
                    box,
                ),
                2,
                2,
            )
        p.setPen(self._soft())
        left_edge = right - more_w - 6 - (self.LEVELS + 1) * (box + 3)
        p.drawText(
            QRectF(
                left_edge - 40,
                y - 2,
                36,
                16,
            ),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "Less",
        )
        if not self.counts:
            p.setFont(self.font())
            p.drawText(
                QRectF(
                    x0,
                    y + 0,
                    left_edge - 50 - x0,
                    16,
                ),
                Qt.AlignmentFlag.AlignVCenter,
                self.empty,
            )

    def _item_at(self, pos: QPointF) -> date | None:
        """
        Return the day under a point, if any questions were answered on it.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        date or None
            The day, or None if the point is not on a day with answers.

        Examples
        --------
        >>> chart = HeatmapChart("Reviews")
        >>> chart.resize(760, 190)
        >>> chart.set_data({date(2026, 11, 13): 3}, today=date(2026, 11, 13))
        >>> cell, (x0, y0) = chart._cell(), chart._origin()
        >>> chart._item_at(QPointF(x0 + 52.5 * cell, y0 + 4.5 * cell))  # the 13th, a Friday, has answers
        datetime.date(2026, 11, 13)
        >>> chart._item_at(QPointF(x0 + 52.5 * cell, y0 + 3.5 * cell)) is None  # the 12th has none
        True
        """
        day = self.day_at(pos)
        return day if day is not None and self.counts.get(day, 0) > 0 else None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Say how many questions were answered on the day under the pointer, in a tooltip.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> from PySide6.QtGui import QMouseEvent
        >>> chart = HeatmapChart("Reviews")
        >>> chart.resize(760, 190)
        >>> chart.set_data({date(2026, 11, 13): 3}, today=date(2026, 11, 13))
        >>> cell, (x0, y0) = chart._cell(), chart._origin()
        >>> point = QPointF(x0 + 52.5 * cell, y0 + 4.5 * cell)
        >>> chart.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        """
        self._track(event)
        day = self.day_at(event.position())
        if day is None:
            QToolTip.hideText()
            return
        n = self.counts.get(day, 0)
        text = f"{day.strftime('%a')} {day.strftime('%b')} {day.day}, {day.year}\n" + (
            f"{n} question{'s' if n != 1 else ''}" if n else "no questions"
        )
        QToolTip.showText(event.globalPosition().toPoint(), text, self)
