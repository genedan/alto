from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..settings import KEYBOARD_DEFAULT, KEYBOARD_FULL

WHITE_PITCH_CLASSES = (0, 2, 4, 5, 7, 9, 11)
PAD, RAIL = 10.0, 8.0  # frame padding, and the dark strip above the keys


# Real piano proportions, in units of one white key's width (23.5 mm): a white key is about 6.2 units long,
# a black key 0.58 wide and 0.63 as long as a white one. Black keys do not sit on the boundary between
# white keys: in each group they are spread a little, so these are their centres within an octave.
WHITE_INDEX = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
BLACK_CENTER = {1: 0.93, 3: 2.07, 6: 3.86, 8: 5.0, 10: 6.14}
KEY_LENGTH, BLACK_WIDTH, BLACK_LENGTH = 6.2, 0.58, 0.63
MAX_KEY_WIDTH = 38.0  # px; keeps a short range from making a keyboard taller than the window


def _bottom_rounded(x: float, y: float, w: float, h: float, r: float) -> QPainterPath:
    """A rectangle with square top corners and rounded bottom corners."""
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + w, y)
    path.lineTo(x + w, y + h - r)
    path.quadTo(x + w, y + h, x + w - r, y + h)
    path.lineTo(x + r, y + h)
    path.quadTo(x, y + h, x, y + h - r)
    path.closeSubpath()
    return path


class KeyboardWidget(QWidget):
    """A piano keyboard drawn to real proportions that can highlight one key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lo, self.hi = KEYBOARD_DEFAULT
        self.highlight: int | None = None
        self.max_key_width = MAX_KEY_WIDTH  # smaller when something else (the key signature) shares the page
        self.highlight_color = QColor(self.palette().color(QPalette.ColorRole.Highlight))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fit_height()

    # geometry
    def _whites(self) -> list[int]:
        return [m for m in range(self.lo, self.hi + 1) if m % 12 in WHITE_PITCH_CLASSES]

    def _key_width(self) -> float:
        if self.width() <= 0:
            return self.max_key_width
        return min((self.width() - 2 * PAD) / max(len(self._whites()), 1), self.max_key_width)

    def _fit_height(self) -> None:
        height = int(2 * PAD + RAIL + self._key_width() * KEY_LENGTH)
        if height != self.height() or self.minimumHeight() != height:
            self.setFixedHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_height()

    def show_key(self, midi: int | None, span: tuple[int, int] | None = None) -> None:
        """Highlight a key. `span` is the range of keys to show; it is widened to whole white keys."""
        if span:
            self.lo, self.hi = span
            if self.lo % 12 not in WHITE_PITCH_CLASSES:
                self.lo -= 1
            if self.hi % 12 not in WHITE_PITCH_CLASSES:
                self.hi += 1
        self.highlight = midi
        self.highlight_color = QColor(self.palette().color(QPalette.ColorRole.Highlight))
        self._fit_height()
        self.update()

    def set_highlight_color(self, color: QColor) -> None:
        self.highlight_color = QColor(color)
        self.update()

    # drawing
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        whites = self._whites()
        if not whites:
            return
        kw = self._key_width()
        n = len(whites)
        left = (self.width() - n * kw) / 2  # centre the keys
        top = PAD + RAIL
        kh = kw * KEY_LENGTH
        first = 7 * (whites[0] // 12) + WHITE_INDEX[whites[0] % 12]  # absolute white-key number of the leftmost key

        # dark case behind the keys
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2b2b30"))
        p.drawRoundedRect(QRectF(left - PAD, 0, n * kw + 2 * PAD, top + kh + PAD), 14, 14)

        # white keys: rounded at the bottom only
        radius = min(7.0, kw * 0.14)
        for i, midi in enumerate(whites):
            on = midi == self.highlight
            p.setPen(QPen(QColor("#9a9a9f"), 1))
            p.setBrush(self.highlight_color if on else QColor("#fbfbfc"))
            p.drawPath(_bottom_rounded(left + i * kw + 0.5, top, kw - 1, kh, radius))

        # black keys at their real positions
        bw, bh = kw * BLACK_WIDTH, kh * BLACK_LENGTH
        for midi in range(self.lo, self.hi + 1):
            if midi % 12 in WHITE_PITCH_CLASSES:
                continue
            centre = 7 * (midi // 12) + BLACK_CENTER[midi % 12]
            x = left + (centre - first) * kw - bw / 2
            on = midi == self.highlight
            p.setPen(QPen(QColor("#111114"), 1))
            p.setBrush(self.highlight_color if on else QColor("#1c1c20"))
            p.drawPath(_bottom_rounded(x, top - 1, bw, bh + 1, min(4.0, bw * 0.2)))


class KeyboardSpan(QWidget):
    """The whole 88-key piano in miniature, with the keys that will be asked shaded."""

    def __init__(self, parent=None, compact: bool = False, size: tuple[int, int] = (124, 26)):
        """`compact` makes a fixed-size version (`size` in pixels), for a summary in a menu row."""
        super().__init__(parent)
        self.lo, self.hi = KEYBOARD_DEFAULT
        if compact:
            self.setFixedSize(*size)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row underneath is the click target
        else:
            self.setFixedHeight(64)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_span(self, lo: int, hi: int) -> None:
        self.lo, self.hi = lo, hi
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        first, last = KEYBOARD_FULL
        whites = [m for m in range(first, last + 1) if m % 12 in WHITE_PITCH_CLASSES]
        w, h = self.width(), self.height()
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2b2b30"))
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)
        index_of = {}
        for i, midi in enumerate(whites):
            index_of[midi] = i
            on = self.lo <= midi <= self.hi
            p.setBrush(accent if on else QColor("#e9e9ec"))
            p.drawRect(QRectF(4 + i * (w - 8) / len(whites), 4, (w - 8) / len(whites) - 0.6, h - 8))
        kw = (w - 8) / len(whites)
        for midi in range(first, last + 1):
            if midi % 12 in WHITE_PITCH_CLASSES or midi - 1 not in index_of:
                continue
            on = self.lo <= midi <= self.hi
            p.setBrush(accent.darker(150) if on else QColor("#1c1c20"))
            p.drawRect(QRectF(4 + (index_of[midi - 1] + 1) * kw - kw * 0.3, 4, kw * 0.6, (h - 8) * 0.6))
