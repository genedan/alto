"""Small charts drawn with QPainter, in the application's theme colours: stacked bars, a line, and horizontal bars."""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

GOOD, BAD = QColor("#2e7d32"), QColor("#c62828")  # the same greens and reds the exercise feedback uses


def nice_ticks(top: float, count: int = 4) -> list[float]:
    """Round tick values from 0 up to just above `top`, e.g. 0, 5, 10, 15 for a top of 13."""
    if top <= 0:
        return [0.0, 1.0]
    raw = top / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    n = math.ceil(top / step - 1e-9)
    return [i * step for i in range(n + 1)]


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(*(a.getRgbF()[k] + (b.getRgbF()[k] - a.getRgbF()[k]) * t for k in range(3)))


class _Chart(QWidget):
    """A titled plot area with a value axis on the left and labels along the bottom."""

    LEFT, RIGHT, TOP, BOTTOM = 40, 12, 34, 26

    def __init__(self, title: str, empty: str = "Nothing to show for this selection.", parent=None):
        super().__init__(parent)
        self.title, self.empty = title, empty
        self.labels: list[str] = []
        self.setMinimumSize(260, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    # -- colours -----------------------------------------------------------------------------------------------------

    def _ink(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.Text)

    def _soft(self) -> QColor:
        return _mix(self.palette().color(QPalette.ColorRole.Base), self._ink(), 0.55)

    def _grid(self) -> QColor:
        return _mix(self.palette().color(QPalette.ColorRole.Base), self._ink(), 0.16)

    def _plot(self) -> QRectF:
        return QRectF(self.LEFT, self.TOP, max(self.width() - self.LEFT - self.RIGHT, 10),
                      max(self.height() - self.TOP - self.BOTTOM, 10))

    # -- shared drawing ---------------------------------------------------------------------------------------------------

    def _frame(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self._ink())
        title_font = QFont(self.font())
        title_font.setBold(True)
        p.setFont(title_font)
        p.drawText(QRectF(0, 4, self.width(), 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)
        p.setFont(self.font())

    def _message(self, p: QPainter, text: str) -> None:
        p.setPen(self._soft())
        p.drawText(self._plot(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    def _value_axis(self, p: QPainter, ticks: Sequence[float], top: float, fmt: Callable[[float], str]) -> None:
        plot = self._plot()
        small = QFont(self.font())
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        p.setFont(small)
        for t in ticks:
            y = plot.bottom() - plot.height() * t / top
            p.setPen(QPen(self._grid(), 1))
            p.drawLine(QPointF(plot.left(), round(y) + 0.5), QPointF(plot.right(), round(y) + 0.5))
            p.setPen(self._soft())
            p.drawText(QRectF(0, y - 8, self.LEFT - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt(t))
        p.setFont(self.font())

    def _category_axis(self, p: QPainter, centres: Sequence[float], labels: Sequence[str]) -> None:
        """Label some of the positions along the bottom, skipping as many as needed so none overlap."""
        if not labels:
            return
        small = QFont(self.font())
        small.setPointSizeF(max(small.pointSizeF() - 1, 7))
        p.setFont(small)
        p.setPen(self._soft())
        widest = max(p.fontMetrics().horizontalAdvance(s) for s in labels) + 10
        every = max(1, math.ceil(widest / max(self._plot().width() / len(labels), 1)))
        for i in range(len(labels) - 1, -1, -every):  # count back from the latest, so the newest label is always there
            label_box = QRectF(centres[i] - widest / 2, self._plot().bottom() + 5, widest, 16)
            p.drawText(label_box, Qt.AlignmentFlag.AlignCenter, labels[i])
        p.setFont(self.font())

    def _hover(self, event, centres: Sequence[float], texts: Sequence[str]) -> None:
        if not centres:
            return
        x = event.position().x()
        i = min(range(len(centres)), key=lambda k: abs(centres[k] - x))
        if self._plot().adjusted(-4, -4, 4, 4).contains(event.position()):
            QToolTip.showText(event.globalPosition().toPoint(), texts[i], self)
        else:
            QToolTip.hideText()


class StackedBarChart(_Chart):
    """Questions per period, the first-try right ones in green with the missed ones stacked above in red."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent=parent)
        self.right: list[int] = []
        self.wrong: list[int] = []

    def set_data(self, labels: Sequence[str], right: Sequence[int], wrong: Sequence[int]) -> None:
        self.labels, self.right, self.wrong = list(labels), list(right), list(wrong)
        self.update()

    def _centres(self) -> list[float]:
        plot, n = self._plot(), max(len(self.labels), 1)
        return [plot.left() + plot.width() * (i + 0.5) / n for i in range(len(self.labels))]

    def paintEvent(self, _):
        p = QPainter(self)
        self._frame(p)
        totals = [r + w for r, w in zip(self.right, self.wrong)]
        if not any(totals):
            self._message(p, self.empty)
            return
        ticks = nice_ticks(max(totals))
        top = ticks[-1]
        self._value_axis(p, ticks, top, lambda v: f"{v:g}")
        plot, n = self._plot(), len(self.labels)
        slot = plot.width() / n
        bar = min(max(slot * 0.68, 2.0), 38.0)
        centres = self._centres()
        p.setPen(Qt.PenStyle.NoPen)
        for cx, r, w in zip(centres, self.right, self.wrong):
            h_right, h_wrong = plot.height() * r / top, plot.height() * w / top
            p.setBrush(GOOD)
            p.drawRoundedRect(QRectF(cx - bar / 2, plot.bottom() - h_right, bar, h_right), 2, 2) if r else None
            p.setBrush(BAD)
            p.drawRoundedRect(QRectF(cx - bar / 2, plot.bottom() - h_right - h_wrong, bar, h_wrong), 2, 2) if w else None
        self._category_axis(p, centres, self.labels)

    def mouseMoveEvent(self, event):
        self._hover(event, self._centres(), [
            f"{lab}\n{r + w} question{'s' if r + w != 1 else ''}: {r} right first time, {w} missed"
            for lab, r, w in zip(self.labels, self.right, self.wrong)])


class LineChart(_Chart):
    """A value per period joined by a line. Periods with no answers leave a gap rather than a zero."""

    def __init__(self, title: str, fmt: Callable[[float], str], fixed_top: float | None = None, parent=None):
        super().__init__(title, parent=parent)
        self.fmt, self.fixed_top = fmt, fixed_top
        self.values: list[float | None] = []

    def set_data(self, labels: Sequence[str], values: Sequence[float | None]) -> None:
        self.labels, self.values = list(labels), list(values)
        self.update()

    def _centres(self) -> list[float]:
        plot, n = self._plot(), len(self.labels)
        return [plot.left() + plot.width() * (i + 0.5) / n for i in range(n)]

    def _top_and_ticks(self) -> tuple[float, list[float]]:
        if self.fixed_top:
            step = self.fixed_top / 4
            return self.fixed_top, [step * i for i in range(5)]
        ticks = nice_ticks(max(v for v in self.values if v is not None))
        return ticks[-1], ticks

    def paintEvent(self, _):
        p = QPainter(self)
        self._frame(p)
        present = [v for v in self.values if v is not None]
        if not present:
            self._message(p, self.empty)
            return
        top, ticks = self._top_and_ticks()
        self._value_axis(p, ticks, top, self.fmt)
        plot, centres = self._plot(), self._centres()
        points = [QPointF(cx, plot.bottom() - plot.height() * min(v, top) / top) if v is not None else None
                  for cx, v in zip(centres, self.values)]
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        run: list[QPointF] = []
        for pt in [*points, None]:  # draw each unbroken run of points as one line
            if pt is not None:
                run.append(pt)
                continue
            if len(run) > 1:
                path = QPainterPath(run[0])
                for q in run[1:]:
                    path.lineTo(q)
                p.setPen(QPen(accent, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
            run = []
        p.setPen(QPen(self.palette().color(QPalette.ColorRole.Base), 1.5))
        p.setBrush(accent)
        radius = 3.6 if len(self.labels) <= 40 else 2.4
        for pt in points:
            if pt is not None:
                p.drawEllipse(pt, radius, radius)
        self._category_axis(p, centres, self.labels)

    def mouseMoveEvent(self, event):
        self._hover(event, self._centres(), [f"{lab}\n{self.fmt(v) if v is not None else 'no answers'}"
                                             for lab, v in zip(self.labels, self.values)])


class HBarChart(_Chart):
    """One bar per name, on a fixed 0-100 scale, each with its value at the end."""

    ROW = 26

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent=parent)
        self.rows: list[tuple[str, float, str]] = []

    def set_data(self, rows: Sequence[tuple[str, float, str]]) -> None:
        """`rows` are (name, value 0-100, text shown at the end of the bar)."""
        self.rows = list(rows)
        self.setMinimumHeight(max(190, self.TOP + 12 + self.ROW * len(self.rows)))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        self._frame(p)
        if not self.rows:
            self._message(p, self.empty)
            return
        label_w = min(max(p.fontMetrics().horizontalAdvance(n) for n, _, _ in self.rows) + 12, self.width() * 0.45)
        value_w = max(p.fontMetrics().horizontalAdvance(t) for _, _, t in self.rows) + 10
        x0, x1 = label_w, self.width() - value_w - 8
        for i, (name, value, text) in enumerate(self.rows):
            y = self.TOP + i * self.ROW
            p.setPen(self._ink())
            p.drawText(QRectF(0, y, label_w - 8, self.ROW - 6), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       p.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, int(label_w - 8)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._grid())
            p.drawRoundedRect(QRectF(x0, y + 4, x1 - x0, self.ROW - 14), 4, 4)
            p.setBrush(self.palette().color(QPalette.ColorRole.Highlight))
            p.drawRoundedRect(QRectF(x0, y + 4, max((x1 - x0) * value / 100, 3), self.ROW - 14), 4, 4)
            p.setPen(self._soft())
            p.drawText(QRectF(x1 + 6, y, value_w, self.ROW - 6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
