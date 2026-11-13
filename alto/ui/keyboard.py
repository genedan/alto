from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..settings import KEYBOARD_DEFAULT, KEYBOARD_FULL
from . import keyboard_styles
from .keyboard_styles import KeyboardStyle

WHITE_PITCH_CLASSES = (0, 2, 4, 5, 7, 9, 11)
EDGE_REACH = 11.0  # px either side of a span's edge that grabs it
PAD = 10.0  # frame padding


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
        self.style_override: KeyboardStyle | None = None  # a fixed style, for the preview cards in the settings
        self.pad = PAD
        self.max_key_width = MAX_KEY_WIDTH  # smaller when something else (the key signature) shares the page
        self.highlight_color = QColor(self.palette().color(QPalette.ColorRole.Highlight))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fit_height()

    # geometry
    @property
    def style(self) -> KeyboardStyle:
        return self.style_override or keyboard_styles.current()

    def refit(self) -> None:
        """Size and redraw after the style changes: some have a taller strip above the keys."""
        self._fit_height()
        self.update()

    def _whites(self) -> list[int]:
        return [m for m in range(self.lo, self.hi + 1) if m % 12 in WHITE_PITCH_CLASSES]

    def _key_width(self) -> float:
        if self.width() <= 0:
            return self.max_key_width
        return min((self.width() - 2 * self.pad) / max(len(self._whites()), 1), self.max_key_width)

    def _fit_height(self) -> None:
        height = int(2 * self.pad + self.style.rail + self._key_width() * KEY_LENGTH)
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
        style, pad = self.style, self.pad
        kw = self._key_width()
        n = len(whites)
        left = (self.width() - n * kw) / 2  # centre the keys
        top = pad + style.rail
        kh = kw * KEY_LENGTH
        first = 7 * (whites[0] // 12) + WHITE_INDEX[whites[0] % 12]  # absolute white-key number of the leftmost key

        # the body behind the keys, with its felt strip and stop knobs
        p.setPen(Qt.PenStyle.NoPen)
        if style.case:
            p.setBrush(QColor(style.case))
            p.drawRoundedRect(QRectF(left - pad, 0, n * kw + 2 * pad, top + kh + pad), 14, 14)
        if style.felt:
            p.setBrush(QColor(style.felt))
            p.drawRect(QRectF(left, top - 5, n * kw, 4))
        if style.knobs:
            count = max(3, int(n * kw / 56))
            for i in range(count):
                x = left + 14 + i * (n * kw - 28) / (count - 1)
                p.setPen(QPen(QColor("#3a2a18"), 1.2))
                p.setBrush(QColor("#e6d8b6"))
                p.drawEllipse(QPointF(x, pad + 13), 6.5, 6.5)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#6b4a2c"))
                p.drawEllipse(QPointF(x, pad + 13), 2.2, 2.2)

        # white keys: rounded at the bottom only
        radius = min(style.round, kw * 0.14)
        edge = 2.5 if style.thick else 1.0
        for i, midi in enumerate(whites):
            on = midi == self.highlight
            path = _bottom_rounded(left + i * kw + style.gap / 2, top, kw - style.gap, kh, radius)
            self._outline(p, path, style, midi, False, edge)
            p.setBrush(self.highlight_color if on else keyboard_styles.key_brush(style, midi, False, top, kh))
            p.drawPath(path)
            if style.dot and midi % 12 == 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(style.dot))
                p.drawEllipse(QPointF(left + (i + 0.5) * kw, top + kh - kw * 0.55), max(kw * 0.16, 2.5), max(kw * 0.16, 2.5))

        # black keys at their real positions
        bw, bh = kw * BLACK_WIDTH * style.narrow, kh * BLACK_LENGTH
        for midi in range(self.lo, self.hi + 1):
            if midi % 12 in WHITE_PITCH_CLASSES:
                continue
            centre = 7 * (midi // 12) + BLACK_CENTER[midi % 12]
            x = left + (centre - first) * kw - bw / 2
            on = midi == self.highlight
            path = _bottom_rounded(x, top - 1, bw, bh + 1, min(4.0, bw * 0.2))
            self._outline(p, path, style, midi, True, edge)
            p.setBrush(self.highlight_color if on else keyboard_styles.key_brush(style, midi, True, top, bh))
            p.drawPath(path)
            if style.cap:  # a bone cap over the darker wood
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(style.cap))
                p.drawRoundedRect(QRectF(x + 2, top, bw - 4, bh - 6), 1.5, 1.5)
            if style.ink:
                p.setPen(QPen(QColor(style.white[0]), 0.8))
                for step in range(3):
                    p.drawLine(QPointF(x + 2, top + 8 + step * 5), QPointF(x + bw - 2, top + 8 + step * 5))

    @staticmethod
    def _outline(p: QPainter, path: QPainterPath, style: KeyboardStyle, midi: int, black: bool, width: float) -> None:
        """Set the pen for a key's outline; a style with a glow first draws a wide faint halo of it."""
        colour = keyboard_styles.edge_color(style, midi, black)
        if style.glow:
            halo = QColor(colour)
            halo.setAlpha(60)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(halo, 5))
            p.drawPath(path)
        p.setPen(QPen(colour, width))


class KeyboardSpan(QWidget):
    """The whole 88-key piano in miniature, with the keys that will be asked shaded. The full-size one can be
    dragged across to choose the span: `dragged` is emitted with the lowest and highest key as it changes."""

    dragged = Signal(int, int)

    def __init__(self, parent=None, compact: bool = False, size: tuple[int, int] = (124, 26)):
        """`compact` makes a fixed-size version (`size` in pixels), for a summary in a menu row."""
        super().__init__(parent)
        self.lo, self.hi = KEYBOARD_DEFAULT
        self._compact = compact
        if compact:
            self.setFixedSize(*size)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # the row underneath is the click target
        else:
            self.setFixedHeight(64)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode: str | None = None  # while a button is held: new, pan, lo or hi
        self._anchor, self._offset = 0, 0
        self.setMouseTracking(True)

    def key_at(self, pos: QPointF) -> int:
        """The MIDI key under `pos`: a black key where one is drawn there, else the white key (clamped to the ends)."""
        first, last = KEYBOARD_FULL
        whites = [m for m in range(first, last + 1) if m % 12 in WHITE_PITCH_CLASSES]
        w, h = self.width(), self.height()
        kw = (w - 8) / len(whites)
        index = min(max(int((pos.x() - 4) // kw), 0), len(whites) - 1)
        if pos.y() < 4 + (h - 8) * 0.6:  # the black keys sit in the upper part, across a boundary between whites
            for i in (index, index + 1):
                midi = whites[i - 1] + 1 if 0 < i < len(whites) else None
                if midi is not None and midi % 12 not in WHITE_PITCH_CLASSES and abs(pos.x() - (4 + i * kw)) <= kw * 0.3:
                    return midi
        return whites[index]

    def _edges(self) -> tuple[float, float]:
        """The x of the left side of the lowest asked key and the right side of the highest."""
        first, last = KEYBOARD_FULL
        whites = [m for m in range(first, last + 1) if m % 12 in WHITE_PITCH_CLASSES]
        kw = (self.width() - 8) / len(whites)

        def sides(midi: int) -> tuple[float, float]:
            if midi % 12 in WHITE_PITCH_CLASSES:
                return 4 + whites.index(midi) * kw, 4 + (whites.index(midi) + 1) * kw
            centre = 4 + (whites.index(midi - 1) + 1) * kw
            return centre - kw * 0.3, centre + kw * 0.3

        return sides(self.lo)[0], sides(self.hi)[1]

    def _grab(self, x: float) -> str:
        """What a press at `x` would do: move the `lo` or `hi` edge, `pan` the span, or start a `new` one."""
        left, right = self._edges()
        reach = min(EDGE_REACH, (right - left) / 4)
        if abs(x - left) <= reach and abs(x - left) <= abs(x - right):
            return "lo"
        if abs(x - right) <= reach:
            return "hi"
        return "pan" if left < x < right else "new"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        key = self.key_at(event.position())
        self._mode = self._grab(event.position().x())
        self._anchor, self._offset = key, key - self.lo
        if self._mode == "new":
            self.dragged.emit(key, key)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._mode is None:
            cursor = {"lo": Qt.CursorShape.SizeHorCursor, "hi": Qt.CursorShape.SizeHorCursor,
                      "pan": Qt.CursorShape.OpenHandCursor, "new": Qt.CursorShape.PointingHandCursor}
            self.setCursor(cursor[self._grab(event.position().x())])
            return
        here = self.key_at(event.position())
        first, last = KEYBOARD_FULL
        if self._mode == "new":
            self.dragged.emit(min(self._anchor, here), max(self._anchor, here))
        elif self._mode == "lo":
            self.dragged.emit(min(here, self.hi), self.hi)
        elif self._mode == "hi":
            self.dragged.emit(self.lo, max(here, self.lo))
        else:  # pan: the span keeps its size and follows the pointer, stopping at the ends of the piano
            width = self.hi - self.lo
            low = min(max(here - self._offset, first), last - width)
            self.dragged.emit(low, low + width)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._mode = None
        self.mouseMoveEvent(event)  # refresh the cursor for where the pointer now is

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
        style = keyboard_styles.current()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(style.case or keyboard_styles.DEFAULT_CASE))  # the miniature always sits on a case
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)
        index_of = {}
        for i, midi in enumerate(whites):
            index_of[midi] = i
            on = self.lo <= midi <= self.hi
            p.setBrush(accent if on else keyboard_styles.key_brush(style, midi, False, 4, h - 8))
            p.drawRect(QRectF(4 + i * (w - 8) / len(whites), 4, (w - 8) / len(whites) - 0.6, h - 8))
        kw = (w - 8) / len(whites)
        for midi in range(first, last + 1):
            if midi % 12 in WHITE_PITCH_CLASSES or midi - 1 not in index_of:
                continue
            on = self.lo <= midi <= self.hi
            p.setBrush(accent.darker(150) if on else keyboard_styles.key_brush(style, midi, True, 4, (h - 8) * 0.6))
            p.drawRect(QRectF(4 + (index_of[midi - 1] + 1) * kw - kw * 0.3, 4, kw * 0.6, (h - 8) * 0.6))
        # the two edges of the span: a line, and (on the full-size one) a round knob with a chevron to grab
        left_edge, right_edge = self._edges()
        line = accent.lighter(150)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(line)
        for x in (left_edge, right_edge):
            p.drawRect(QRectF(x - 1, 4, 2, h - 8))
        if self._compact:
            return
        mid, radius = h / 2, 11.0
        for x, direction in ((left_edge, -1), (right_edge, 1)):
            p.setPen(QPen(accent.darker(180), 1.5))
            p.setBrush(QColor("white"))
            p.drawEllipse(QPointF(x, mid), radius, radius)
            chevron = QPainterPath()  # points outward, away from the span
            chevron.moveTo(x - direction * 2.5, mid - 5)
            chevron.lineTo(x + direction * 2.5, mid)
            chevron.lineTo(x - direction * 2.5, mid + 5)
            p.setPen(QPen(accent.darker(180), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(chevron)
