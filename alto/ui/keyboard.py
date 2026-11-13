"""
The on-screen piano keyboard, drawn to real proportions, and a miniature of the whole piano for choosing a span of keys.

`KeyboardWidget` shows a range of keys and can highlight one. `KeyboardSpan` shows all 88 keys in miniature, shades the
range that will be asked, and can be dragged to change it. Colours and materials come from `keyboard_styles`.

Examples
--------
>>> keyboard = KeyboardWidget()
>>> keyboard.show_key(60)
>>> keyboard.highlight
60
"""

from __future__ import annotations

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QSizePolicy,
    QWidget,
)

from alto.settings import (
    KEYBOARD_DEFAULT,
    KEYBOARD_FULL,
)
from alto.ui import keyboard_styles
from alto.ui.keyboard_styles import (
    KeyboardStyle,
    on_redraw,
)

WHITE_PITCH_CLASSES = (
    0,
    2,
    4,
    5,
    7,
    9,
    11,
)
EDGE_REACH = 11.0  # px either side of a span's edge that grabs it
PAD = 10.0  # frame padding


# Real piano proportions, in units of one white key's width (23.5 mm): a white key is about 6.2 units long,
# a black key 0.58 wide and 0.63 as long as a white one. Black keys do not sit on the boundary between
# white keys: in each group they are spread a little, so these are their centres within an octave.
WHITE_INDEX = {
    0: 0,
    2: 1,
    4: 2,
    5: 3,
    7: 4,
    9: 5,
    11: 6,
}
BLACK_CENTER = {
    1: 0.93,
    3: 2.07,
    6: 3.86,
    8: 5.0,
    10: 6.14,
}
KEY_LENGTH, BLACK_WIDTH, BLACK_LENGTH = 6.2, 0.58, 0.63
MAX_KEY_WIDTH = 38.0  # px; keeps a short range from making a keyboard taller than the window


def _bottom_rounded(
    x: float,
    *,
    y: float,
    w: float,
    h: float,
    r: float,
) -> QPainterPath:
    """
    Return a rectangle with square top corners and rounded bottom corners, the shape of a piano key.

    Parameters
    ----------
    x : float
        The left edge, in pixels.
    y : float
        The top edge. Keyword-only.
    w : float
        The width. Keyword-only.
    h : float
        The height. Keyword-only.
    r : float
        The radius of the bottom corners. Keyword-only.

    Returns
    -------
    QPainterPath
        The outline.

    Examples
    --------
    >>> box = _bottom_rounded(0, y=0, w=10, h=20, r=3).boundingRect()
    >>> box.width(), box.height()
    (10.0, 20.0)
    """
    path = QPainterPath()
    path.moveTo(x, y)
    path.lineTo(x + w, y)
    path.lineTo(x + w, y + h - r)
    path.quadTo(
        x + w,
        y + h,
        x + w - r,
        y + h,
    )
    path.lineTo(x + r, y + h)
    path.quadTo(
        x,
        y + h,
        x,
        y + h - r,
    )
    path.closeSubpath()
    return path


class KeyboardWidget(QWidget):
    """
    A piano keyboard drawn to real proportions that can highlight one key.

    Attributes
    ----------
    lo : int
        The lowest key shown, as a MIDI number.
    hi : int
        The highest key shown, as a MIDI number.
    highlight : int or None
        The key to highlight.
    style_override : KeyboardStyle or None
        A fixed style, for the preview cards in the settings; otherwise the style chosen in the settings is used.
    pad : float
        The frame padding, in pixels.
    max_key_width : float
        The widest a key may be, in pixels. Smaller when something else (the key signature) shares the page.
    highlight_color : QColor
        The colour of the highlighted key.

    Examples
    --------
    >>> keyboard = KeyboardWidget()
    >>> (keyboard.lo, keyboard.hi)  # C3 to C5, until another range is shown
    (48, 72)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create a keyboard showing the default range, with no key highlighted.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the keyboard.

        Examples
        --------
        >>> KeyboardWidget().highlight is None
        True
        """
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
    # noinspection PyMethodOverriding
    @property
    def style(self) -> KeyboardStyle:
        """
        Return the style the keyboard is drawn in.

        Returns
        -------
        KeyboardStyle
            The fixed style if one is set, otherwise the style chosen in the settings.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.style_override = keyboard_styles.BY_KEY["modern"]
        >>> keyboard.style.label
        'Modern piano'
        """
        return self.style_override or keyboard_styles.current()

    def refit(self) -> None:
        """
        Size and redraw the keyboard after the style changes.

        Some styles have a taller strip above the keys.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.refit()
        >>> keyboard.height() > 0
        True
        """
        self._fit_height()
        self.update()

    def _whites(self) -> list[int]:
        """
        Return the natural (white) keys in the shown range.

        Returns
        -------
        list of int
            Their MIDI numbers, lowest first.

        Examples
        --------
        >>> len(KeyboardWidget()._whites())  # C3 to C5: two octaves and the top C
        15
        """
        return [m for m in range(self.lo, self.hi + 1) if m % 12 in WHITE_PITCH_CLASSES]

    def _key_width(self) -> float:
        """
        Return how wide a white key is drawn.

        Returns
        -------
        float
            The width in pixels: what fits across the widget, but never more than `max_key_width`.

        Examples
        --------
        >>> KeyboardWidget()._key_width()
        38.0
        """
        if self.width() <= 0:
            return self.max_key_width
        return min((self.width() - 2 * self.pad) / max(len(self._whites()), 1), self.max_key_width)

    def _fit_height(self) -> None:
        """
        Set the height that the keys, the strip above them and the padding need.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard._fit_height()
        >>> keyboard.height()
        263
        """
        height = int(2 * self.pad + self.style.rail + self._key_width() * KEY_LENGTH)
        if height != self.height() or self.minimumHeight() != height:
            self.setFixedHeight(height)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Change the height to match the new width, since keys are drawn to real proportions.

        Parameters
        ----------
        event : QResizeEvent
            The resize that happened.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.show()
        >>> keyboard.resize(300, 300)
        >>> keyboard.height()  # narrower, so shorter
        143
        """
        super().resizeEvent(event)
        self._fit_height()

    def show_key(
        self,
        midi: int | None,
        *,
        span: tuple[int, int] | None = None,
    ) -> None:
        """
        Highlight a key, and optionally choose the range of keys to show.

        Parameters
        ----------
        midi : int or None
            The key to highlight, or None for no highlight.
        span : tuple of (int, int) or None, default None
            The lowest and highest key to show; it is widened to whole white keys. Keyword-only.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.show_key(60, span=(49, 71))  # C#3 is widened to C3
        >>> (keyboard.lo, keyboard.hi, keyboard.highlight)
        (48, 71, 60)
        """
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
        """
        Choose the colour of the highlighted key and redraw.

        Parameters
        ----------
        color : QColor
            The colour.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.set_highlight_color(QColor("#2e7d32"))
        >>> keyboard.highlight_color.name()
        '#2e7d32'
        """
        self.highlight_color = QColor(color)
        self.update()

    # drawing
    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the case, the keys, the highlighted key and the style's extras.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> keyboard = KeyboardWidget()
        >>> keyboard.show_key(60)
        >>> keyboard.grab().isNull()
        False
        """
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
            p.drawRoundedRect(
                QRectF(
                    left - pad,
                    0,
                    n * kw + 2 * pad,
                    top + kh + pad,
                ),
                14,
                14,
            )
        if style.felt:
            p.setBrush(QColor(style.felt))
            p.drawRect(
                QRectF(
                    left,
                    top - 5,
                    n * kw,
                    4,
                ),
            )
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
            path = _bottom_rounded(
                left + i * kw + style.gap / 2,
                y=top,
                w=kw - style.gap,
                h=kh,
                r=radius,
            )
            self._outline(
                p,
                path=path,
                style=style,
                midi=midi,
                black=False,
                width=edge,
            )
            p.setBrush(
                self.highlight_color
                if on
                else keyboard_styles.key_brush(
                    style,
                    midi=midi,
                    black=False,
                    y=top,
                    height=kh,
                ),
            )
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
            path = _bottom_rounded(
                x,
                y=top - 1,
                w=bw,
                h=bh + 1,
                r=min(4.0, bw * 0.2),
            )
            self._outline(
                p,
                path=path,
                style=style,
                midi=midi,
                black=True,
                width=edge,
            )
            p.setBrush(
                self.highlight_color
                if on
                else keyboard_styles.key_brush(
                    style,
                    midi=midi,
                    black=True,
                    y=top,
                    height=bh,
                ),
            )
            p.drawPath(path)
            if style.cap:  # a bone cap over the darker wood
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(style.cap))
                p.drawRoundedRect(
                    QRectF(
                        x + 2,
                        top,
                        bw - 4,
                        bh - 6,
                    ),
                    1.5,
                    1.5,
                )
            if style.ink:
                p.setPen(QPen(QColor(style.white[0]), 0.8))
                for step in range(3):
                    p.drawLine(QPointF(x + 2, top + 8 + step * 5), QPointF(x + bw - 2, top + 8 + step * 5))

    @staticmethod
    def _outline(
        p: QPainter,
        *,
        path: QPainterPath,
        style: KeyboardStyle,
        midi: int,
        black: bool,
        width: float,
    ) -> None:
        """
        Set the pen for a key's outline.

        A style with a glow first draws a wide faint halo of it.

        Parameters
        ----------
        p : QPainter
            The painter, whose pen is set.
        path : QPainterPath
            The key's outline, which the halo is drawn along. Keyword-only.
        style : KeyboardStyle
            The style, which gives the colour and whether there is a glow. Keyword-only.
        midi : int
            The key's MIDI number. Keyword-only.
        black : bool
            True for a sharp or flat. Keyword-only.
        width : float
            The pen width, in pixels. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(10, 10, QImage.Format.Format_ARGB32)  # kept, so it outlives the painter
        >>> painter = QPainter(image)
        >>> style_ = keyboard_styles.BY_KEY["classic"]
        >>> KeyboardWidget._outline(painter, path=QPainterPath(), style=style_, midi=60, black=False, width=1.0)
        >>> painter.pen().color().name()
        '#9a9a9f'
        >>> painter.end()
        True
        """
        colour = keyboard_styles.edge_color(style, midi=midi, black=black)
        if style.glow:
            halo = QColor(colour)
            halo.setAlpha(60)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(halo, 5))
            p.drawPath(path)
        p.setPen(QPen(colour, width))


class KeyboardSpan(QWidget):
    """
    The whole 88-key piano in miniature, with the keys that will be asked shaded.

    The full-size one can be dragged across to choose the span: `dragged` is emitted with the lowest and highest key as it
    changes.

    Attributes
    ----------
    dragged : Signal
        Emitted with the lowest and highest key (MIDI numbers) as the span is dragged.
    lo : int
        The lowest key shaded.
    hi : int
        The highest key shaded.

    Examples
    --------
    >>> span = KeyboardSpan()
    >>> span.set_span(60, hi=72)
    >>> (span.lo, span.hi)
    (60, 72)
    """

    dragged = Signal(int, int)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        compact: bool = False,
        size: tuple[int, int] = (124, 26),
    ) -> None:
        """
        Create the miniature, shading the default range.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns it.
        compact : bool, default False
            Make a fixed-size version that ignores the mouse, for a summary in a menu row. Keyword-only.
        size : tuple of (int, int), default (124, 26)
            The width and height of the compact version, in pixels. Keyword-only.

        Examples
        --------
        >>> KeyboardSpan(compact=True, size=(100, 20)).size().width()
        100
        """
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
        """
        Return the key under a point.

        Parameters
        ----------
        pos : QPointF
            The position in the widget.

        Returns
        -------
        int
            The MIDI number: a black key where one is drawn there, else the white key (clamped to the ends of the piano).

        Examples
        --------
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> span.key_at(QPointF(0, 50)), span.key_at(QPointF(499, 50))  # the lowest and highest keys
        (21, 108)
        >>> span.key_at(QPointF(250, 50))
        64
        """
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
        """
        Return where the shaded span starts and ends.

        Returns
        -------
        tuple of (float, float)
            The x position of the left side of the lowest asked key and the right side of the highest.

        Examples
        --------
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> tuple(round(x) for x in span._edges())
        (155, 297)
        """
        first, last = KEYBOARD_FULL
        whites = [m for m in range(first, last + 1) if m % 12 in WHITE_PITCH_CLASSES]
        kw = (self.width() - 8) / len(whites)

        def sides(midi: int) -> tuple[float, float]:
            """
            Return the left and right sides of one key.

            Parameters
            ----------
            midi : int
                The key's MIDI number.

            Returns
            -------
            tuple of (float, float)
                The x positions of its sides; a black key is narrower than a white one.

            Examples
            --------
            >>> sides(60)  # doctest: +SKIP
            (155.4, 164.8)
            """
            if midi % 12 in WHITE_PITCH_CLASSES:
                return 4 + whites.index(midi) * kw, 4 + (whites.index(midi) + 1) * kw
            centre = 4 + (whites.index(midi - 1) + 1) * kw
            return centre - kw * 0.3, centre + kw * 0.3

        return sides(self.lo)[0], sides(self.hi)[1]

    def _grab(self, x: float) -> str:
        """
        Say what a press at a position would do.

        Parameters
        ----------
        x : float
            The horizontal position of the press.

        Returns
        -------
        str
            "lo" or "hi" near an edge of the span (to move that edge), "pan" inside it (to move the whole span), or "new" outside
            it (to start a new one).

        Examples
        --------
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> left_, right_ = span._edges()
        >>> span._grab(left_), span._grab((left_ + right_) / 2), span._grab(5)
        ('lo', 'pan', 'new')
        """
        left, right = self._edges()
        reach = min(EDGE_REACH, (right - left) / 4)
        if abs(x - left) <= reach and abs(x - left) <= abs(x - right):
            return "lo"
        if abs(x - right) <= reach:
            return "hi"
        return "pan" if left < x < right else "new"

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Start choosing a span: grab an edge, pick the span up, or start a new one.

        Parameters
        ----------
        event : QMouseEvent
            The press. Only the left button does anything.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> got = []
        >>> _ = span.dragged.connect(lambda lo, hi: got.append((lo, hi)))
        >>> point = QPointF(5, 50)
        >>> span.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
        ...                                  Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        >>> got  # a press outside the span starts a new one on that key
        [(21, 21)]
        """
        if event.button() != Qt.MouseButton.LeftButton:
            return
        key = self.key_at(event.position())
        self._mode = self._grab(event.position().x())
        self._anchor, self._offset = key, key - self.lo
        if self._mode == "new":
            self.dragged.emit(key, key)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Drag the span, or (with no button held) show the cursor for what a press here would do.

        Parameters
        ----------
        event : QMouseEvent
            The move.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> middle = QPointF(sum(span._edges()) / 2, 50)
        >>> span.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, middle, middle, Qt.MouseButton.NoButton,
        ...                                 Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        >>> span.cursor().shape() == Qt.CursorShape.OpenHandCursor  # inside the span: it can be picked up
        True
        """
        if self._mode is None:
            cursor = {
                "lo": Qt.CursorShape.SizeHorCursor,
                "hi": Qt.CursorShape.SizeHorCursor,
                "pan": Qt.CursorShape.OpenHandCursor,
                "new": Qt.CursorShape.PointingHandCursor,
            }
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
        """
        Finish a drag and refresh the cursor for where the pointer now is.

        Parameters
        ----------
        event : QMouseEvent
            The release.

        Examples
        --------
        >>> from PySide6.QtCore import QEvent
        >>> span = KeyboardSpan()
        >>> span.resize(500, 64)
        >>> point = QPointF(5, 50)
        >>> span.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, point, point, Qt.MouseButton.LeftButton,
        ...                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        >>> span._mode is None
        True
        """
        self._mode = None
        self.mouseMoveEvent(event)  # refresh the cursor for where the pointer now is

    def set_span(
        self,
        lo: int,
        *,
        hi: int,
    ) -> None:
        """
        Choose which keys are shaded and redraw.

        Parameters
        ----------
        lo : int
            The lowest key asked, as a MIDI number.
        hi : int
            The highest key asked. Keyword-only.

        Examples
        --------
        >>> span = KeyboardSpan()
        >>> span.set_span(48, hi=72)
        >>> (span.lo, span.hi)
        (48, 72)
        """
        self.lo, self.hi = lo, hi
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the whole piano in miniature with the asked keys shaded and the span's edges marked.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> span = KeyboardSpan()
        >>> span.grab().isNull()
        False
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        first, last = KEYBOARD_FULL
        whites = [m for m in range(first, last + 1) if m % 12 in WHITE_PITCH_CLASSES]
        w, h = self.width(), self.height()
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        style = keyboard_styles.current()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(style.case or keyboard_styles.DEFAULT_CASE))  # the miniature always sits on a case
        p.drawRoundedRect(
            QRectF(
                0,
                0,
                w,
                h,
            ),
            8,
            8,
        )
        index_of = {}
        for i, midi in enumerate(whites):
            index_of[midi] = i
            on = self.lo <= midi <= self.hi
            p.setBrush(
                accent
                if on
                else keyboard_styles.key_brush(
                    style,
                    midi=midi,
                    black=False,
                    y=4,
                    height=h - 8,
                ),
            )
            p.drawRect(
                QRectF(
                    4 + i * (w - 8) / len(whites),
                    4,
                    (w - 8) / len(whites) - 0.6,
                    h - 8,
                ),
            )
        kw = (w - 8) / len(whites)
        for midi in range(first, last + 1):
            if midi % 12 in WHITE_PITCH_CLASSES or midi - 1 not in index_of:
                continue
            on = self.lo <= midi <= self.hi
            p.setBrush(
                accent.darker(150)
                if on
                else keyboard_styles.key_brush(
                    style,
                    midi=midi,
                    black=True,
                    y=4,
                    height=(h - 8) * 0.6,
                ),
            )
            p.drawRect(
                QRectF(
                    4 + (index_of[midi - 1] + 1) * kw - kw * 0.3,
                    4,
                    kw * 0.6,
                    (h - 8) * 0.6,
                ),
            )
        # the two edges of the span: a line, and (on the full-size one) a round knob with a chevron to grab
        left_edge, right_edge = self._edges()
        line = accent.lighter(150)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(line)
        for x in (left_edge, right_edge):
            p.drawRect(
                QRectF(
                    x - 1,
                    4,
                    2,
                    h - 8,
                ),
            )
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
            p.setPen(
                QPen(
                    accent.darker(180),
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                ),
            )
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(chevron)


def _refit_keyboards() -> None:
    """
    Lay out and paint every keyboard on screen again, after the keyboard style changed.

    Examples
    --------
    >>> _refit_keyboards()  # with no keyboards open, nothing happens
    """
    for w in QApplication.allWidgets():
        if isinstance(w, KeyboardWidget):
            w.refit()
        elif isinstance(w, KeyboardSpan):
            w.update()


on_redraw(_refit_keyboards)
