"""
Small monochrome icons drawn from SVG, tinted with the current theme's text color.

Each icon is the inside of a 24 by 24 SVG, written with the word COLOR where the theme color goes. `svg_icon` turns one
into a `QIcon`.

Examples
--------
>>> svg_icon(HELP, color=QColor("black")).isNull()
False
"""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import (
    QByteArray,
    QObject,
    QSignalBlocker,
    Qt,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
    QPixmapCache,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QAbstractItemView, QMenu

from alto.ui import zoom

ACTIVITY_ICON_SIZE = 20

CHECKED_BOX = (
    '<rect x="2" y="2" width="20" height="20" rx="4" fill="COLOR"/>'
    '<path d="m6 12 4 4 8-9" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
)

GLOSSARY = '<g fill="none" stroke="COLOR" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12 5 4l3 8M3.2 9h3.6M12 5h9M12 10h9M3 16h18M3 21h13"/></g>'

_BODY = '<path d="M3 9h4l5-4v14l-5-4H3z" fill="COLOR"/>'
_STROKE = 'fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round"'
_SPEAKER_ON = _BODY + f'<path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" {_STROKE}/>'
_SPEAKER_MUTED = _BODY + f'<path d="M16 9.5l5 5M21 9.5l-5 5" {_STROKE}/>'

SPEAKER_ON, SPEAKER_MUTED = _SPEAKER_ON, _SPEAKER_MUTED

# Settings: three thin vertical tracks with solid pill-shaped knobs.
SLIDERS = (
    '<path d="M6 3V21M12 3V21M18 3V21" fill="none" stroke="COLOR" stroke-width="1.6" stroke-linecap="round"/>'
    '<rect x="3" y="12.75" width="6" height="4.5" rx="2.25" fill="COLOR"/>'
    '<rect x="9" y="5.75" width="6" height="4.5" rx="2.25" fill="COLOR"/>'
    '<rect x="15" y="10.75" width="6" height="4.5" rx="2.25" fill="COLOR"/>'
)


class _PaletteBinding(QObject):
    """
    Refresh a control's artwork when Alto receives a new palette.

    Examples
    --------
    An open menu redraws its actions when the desktop changes theme.
    """

    def __init__(self, target: QObject) -> None:
        """
        Listen for theme changes while the target exists.

        Parameters
        ----------
        target : QObject
            Control, action, or item view that owns this binding.

        Examples
        --------
        Closing a menu disconnects its deleted actions automatically.
        """
        super().__init__(target)
        self.setObjectName("altoIconPalette")
        app = QGuiApplication.instance()
        assert isinstance(app, QGuiApplication)
        app.paletteChanged.connect(self.redraw)

    refresh: Callable[[QObject | None, QPalette], None]

    @Slot(QPalette)
    def redraw(self, palette: QPalette) -> None:
        """
        Apply the drawing to the live Qt control.

        Parameters
        ----------
        palette : QPalette
            Application colors after the theme change.

        Examples
        --------
        A toolbar button receives a fresh native icon when the desktop switches to light.
        """
        self.refresh(self.parent(), palette)


def _bind_palette(target: QObject, refresh: Callable[[QObject | None, QPalette], None]) -> None:  # noqa: PLR0917
    """
    Draw now and replace the drawing callback for subsequent palette changes.

    Parameters
    ----------
    target : QObject
        Lifetime owner of the binding.
    refresh : Callable
        Updates the supplied control using the current palette.

    Examples
    --------
    Changing a sound button from on to muted replaces its drawing.
    """
    binding = target.findChild(_PaletteBinding, "altoIconPalette", Qt.FindChildOption.FindDirectChildrenOnly)
    if binding is None:
        binding = _PaletteBinding(target)
    binding.refresh = refresh
    binding.redraw(QGuiApplication.palette())


def set_palette_icon(target: QAbstractButton | QAction | QMenu, render: Callable[[QPalette], QIcon]) -> None:  # noqa: PLR0917
    """
    Assign a native Qt icon and refresh it whenever the application palette changes.

    Parameters
    ----------
    target : QAbstractButton or QAction or QMenu
        Button, menu, or action to update.
    render : Callable
        Draws the icon in the supplied palette.

    Examples
    --------
    >>> from PySide6.QtWidgets import QPushButton
    >>> button = QPushButton()
    >>> set_palette_icon(button, lambda palette: svg_icon(HELP, color=palette.text().color()))
    >>> button.icon().isNull()
    False
    """

    def refresh(control: QObject | None, palette: QPalette) -> None:  # noqa: PLR0917 (palette callback)
        """
        Give the control a freshly rendered native icon.

        Parameters
        ----------
        control : QObject
            Live owner of the binding.
        palette : QPalette
            Current application palette.

        Examples
        --------
        A menu action repaints its icon with the new foreground.
        """
        assert isinstance(control, (QAbstractButton, QAction, QMenu))
        control.setIcon(render(palette))

    _bind_palette(target, refresh)


def set_svg_icon(  # noqa: PLR0917 (target and drawing)
    target: QAbstractButton | QAction | QMenu,
    inner: str,
    *,
    role: QPalette.ColorRole = QPalette.ColorRole.WindowText,
    size: int = 24,
) -> None:
    """
    Tint an SVG icon with the control's current foreground or accent color.

    Parameters
    ----------
    target : QAbstractButton or QAction or QMenu
        Control that displays the icon.
    inner : str
        SVG shapes using COLOR for the ink.
    role : QPalette.ColorRole, default WindowText
        Color to take from the application palette.
    size : int, default 24
        Logical size in pixels.

    Examples
    --------
    >>> from PySide6.QtWidgets import QPushButton
    >>> button = QPushButton()
    >>> set_svg_icon(button, HELP)
    >>> button.icon().isNull()
    False
    """
    set_palette_icon(target, lambda palette: svg_icon(inner, color=palette.color(role), size=size))


def set_item_icons(view: QAbstractItemView, items: list[tuple[str, Callable[[QIcon], None]]]) -> None:  # noqa: PLR0917
    """
    Recolor the current rows of a navigation list or tree without rebuilding it.

    Parameters
    ----------
    view : QAbstractItemView
        List or tree supplying the text color and icon size.
    items : list of tuple
        SVG drawing and icon setter for each row in the current model.

    Examples
    --------
    A category tree keeps its checked and expanded items when the theme changes.
    """

    def refresh(control: QObject | None, palette: QPalette) -> None:  # noqa: PLR0917 (palette callback)
        """
        Render the icons for the rows currently in the view.

        Parameters
        ----------
        control : QObject
            The list or tree containing the rows.
        palette : QPalette
            Current application palette.

        Examples
        --------
        Light navigation lists use the same ink as their text.
        """
        assert isinstance(control, QAbstractItemView)
        with QSignalBlocker(control):
            for glyph, assign in items:
                assign(svg_icon(glyph, color=palette.text().color(), size=control.iconSize().width()))

    _bind_palette(view, refresh)


def svg_icon(
    inner: str,
    *,
    color: QColor,
    size: int = 24,
    scale: float = 2.0,
) -> QIcon:
    """
    Render 24 by 24 SVG shapes into a crisp icon.

    Parameters
    ----------
    inner : str
        The SVG shapes, using COLOR wherever the color goes.
    color : QColor
        The color to draw in. Keyword-only.
    size : int, default 24
        The icon's size in logical pixels. Keyword-only.
    scale : float, default 2.0
        How many device pixels to render per logical pixel, so it stays sharp on high-resolution screens. Keyword-only.

    Returns
    -------
    QIcon
        The icon.

    Examples
    --------
    >>> icon = svg_icon(PLAY, color=QColor("#336699"), size=16)
    >>> icon.isNull()
    False
    """
    side = int(size * zoom.factor() * scale)
    key = f"alto.svg/{side}/{scale}/{color.name()}/{inner}"
    cached = QPixmap()
    if QPixmapCache.find(key, cached):
        return QIcon(cached)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{inner.replace("COLOR", color.name())}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(side, side)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    pixmap.setDevicePixelRatio(scale)
    QPixmapCache.insert(key, pixmap)
    return QIcon(pixmap)


# Sidebar toggle: an edge bar with a chevron pointing toward the edge while the list is shown
# (click to hide) and away from it while hidden (click to show).
_SIDEBAR_STROKE = 'fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
SIDEBAR_OPEN = f'<path d="M5 4v16M15 7l-5 5 5 5" {_SIDEBAR_STROKE}/>'
SIDEBAR_CLOSED = f'<path d="M5 4v16M10 7l5 5-5 5" {_SIDEBAR_STROKE}/>'

# Exercise icons for the home screen (24x24, drawn with outlines like the controls above).
_LINE = 'fill="none" stroke="COLOR" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'
_STAFF = '<path d="M2 6H22M2 9.5H22M2 13H22M2 16.5H22M2 20H22" fill="none" stroke="COLOR" stroke-width="1.1" opacity=".5"/>'


def _ring(
    x: float,
    *,
    y: float,
    rx: float = 3.3,
    ry: float = 2.3,
) -> str:
    """
    Return the SVG for an outlined oval, used as a note head.

    Parameters
    ----------
    x : float
        The center's x position in the 24 by 24 drawing.
    y : float
        The center's y position. Keyword-only.
    rx : float, default 3.3
        The horizontal radius. Keyword-only.
    ry : float, default 2.3
        The vertical radius. Keyword-only.

    Returns
    -------
    str
        An `<ellipse>` element.

    Examples
    --------
    >>> _ring(13, y=18.5).startswith('<ellipse cx="13" cy="18.5"')
    True
    """
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" {_LINE}/>'


# Note identification: a quarter note, in the Noto Music outline the app icon uses.
_NOTE_PATH = (
    "M14.55 3.50L14.55 17.74C14.55 18.23 14.39 18.68 14.06 19.10"
    "C13.74 19.52 13.32 19.86 12.81 20.12C12.30 20.37 11.76 20.50 11.19 20.50"
    "C10.67 20.50 10.25 20.37 9.93 20.10C9.61 19.83 9.45 19.47 9.45 19.02"
    "C9.45 18.67 9.56 18.33 9.76 18.00C9.97 17.67 10.24 17.37 10.57 17.10"
    "C10.90 16.83 11.27 16.62 11.67 16.47C12.07 16.32 12.46 16.24 12.84 16.24"
    "C13.33 16.24 13.75 16.38 14.10 16.67L14.10 3.50L14.55 3.50Z"
)
EXERCISE_NOTE_NAMES = f'<path d="{_NOTE_PATH}" fill="COLOR"/>'
# Noto Music quarter note, Noto Sans plus, and Noto Sans Symbols 2 square.
EXERCISE_RHYTHMIC_EQUATIONS = (
    '<path d="'
    "M350 1009 V173 Q350 130 321.5 93.0 Q293 56 248.0 33.5 Q203 11 153 11 Q107 11 79.0 34.5 Q51 58 51 98 "
    "Q51 129 69.0 158.0 Q87 187 116.5 210.5 Q146 234 181.0 247.5 Q216 261 250 261 Q293 261 324 236 V1009 "
    "Z "
    '" transform="translate(2.187375 19.15431) scale(0.01402806 -0.01402806)" fill="COLOR"/>'
    '<path d="'
    "M321 388 H520 V317 H321 V111 H249 V317 H50 V388 H249 V595 H321 Z "
    '" transform="translate(9.155785 15.64669) scale(0.01033058 -0.01033058)" fill="COLOR"/>'
    '<path d="'
    "M51 -4 V728 H783 V-4 Z M88 33 H746 V691 H88 Z "
    '" transform="translate(15.79713 15.21448) scale(0.008879781 -0.008879781)" fill="COLOR"/>'
)
EXERCISE_NOTATION_IDENTIFICATION = '<path d="M9.94 13.15 C8.15 12.27 6.78 11.29 5.85 10.24 C4.91 9.18 4.44 8.04 4.44 6.79 C4.44 5.98 4.64 5.22 5.05 4.49 C5.45 3.76 5.99 3.16 6.68 2.70 C7.36 2.23 8.11 2.00 8.94 2.00 C9.88 2.00 10.68 2.28 11.33 2.83 C11.99 3.38 12.31 4.09 12.31 4.96 C12.31 5.39 12.15 5.74 11.82 5.99 C11.50 6.25 11.14 6.38 10.74 6.38 C10.29 6.38 9.94 6.29 9.69 6.11 C9.45 5.93 9.27 5.70 9.17 5.40 L8.91 4.57 C8.81 4.26 8.68 4.00 8.52 3.80 C8.36 3.61 8.12 3.51 7.78 3.51 C7.35 3.51 6.98 3.72 6.69 4.14 C6.39 4.57 6.25 5.03 6.25 5.52 C6.25 6.35 6.61 7.12 7.34 7.83 C8.07 8.52 9.55 9.32 11.78 10.25 L17.16 2.18 L18.76 2.18 L13.05 10.85 C14.98 11.83 16.36 12.85 17.19 13.91 C18.02 14.96 18.44 16.08 18.44 17.27 C18.44 18.11 18.24 18.90 17.84 19.62 C17.45 20.34 16.90 20.91 16.21 21.35 C15.52 21.78 14.75 22.00 13.88 22.00 C12.87 22.00 12.08 21.72 11.50 21.16 C10.92 20.59 10.63 19.95 10.63 19.22 C10.63 18.76 10.76 18.40 11.04 18.12 C11.31 17.85 11.70 17.71 12.19 17.71 C12.77 17.71 13.16 17.85 13.39 18.14 C13.62 18.42 13.76 18.74 13.82 19.10 C13.88 19.45 13.99 19.78 14.14 20.06 C14.30 20.35 14.57 20.49 14.94 20.49 C15.48 20.49 15.90 20.30 16.21 19.93 C16.53 19.55 16.69 19.07 16.69 18.48 C16.69 17.23 15.88 16.19 14.26 15.34 C13.46 14.93 12.79 14.59 12.28 14.32 C11.77 14.06 11.40 13.86 11.18 13.74 L5.95 21.88 L4.38 21.88 L9.94 13.15 M18.17 8.01 C18.56 8.01 18.90 8.15 19.19 8.43 C19.47 8.72 19.62 9.06 19.62 9.46 C19.62 9.85 19.47 10.19 19.19 10.48 C18.90 10.76 18.56 10.91 18.17 10.91 C17.77 10.91 17.43 10.76 17.15 10.48 C16.86 10.19 16.72 9.85 16.72 9.46 C16.72 9.06 16.86 8.72 17.15 8.43 C17.43 8.15 17.77 8.01 18.17 8.01 M5.95 13.15 C6.34 13.15 6.68 13.30 6.97 13.58 C7.26 13.87 7.40 14.21 7.40 14.60 C7.40 15.00 7.26 15.34 6.97 15.62 C6.68 15.91 6.34 16.05 5.95 16.05 C5.55 16.05 5.21 15.91 4.93 15.62 C4.64 15.34 4.50 15.00 4.50 14.60 C4.50 14.21 4.64 13.87 4.93 13.58 C5.21 13.30 5.55 13.15 5.95 13.15" fill="COLOR" fill-rule="nonzero"/>'
# Interval identification: two whole notes one above the other, in the Noto Music outline the app icon uses, with a thin
# measuring bracket to their right. The upper note is the lower one moved up.
_INTERVAL_NOTE = (
    "M4.10 18.98C4.10 18.47 4.29 18.02 4.66 17.63C5.03 17.24 5.54 16.94 6.19 16.71"
    "C6.83 16.49 7.54 16.38 8.32 16.38C9.11 16.38 9.83 16.49 10.50 16.70"
    "C11.16 16.92 11.70 17.22 12.10 17.61C12.50 17.99 12.70 18.45 12.70 18.98"
    "C12.70 19.52 12.51 19.99 12.12 20.38C11.73 20.78 11.22 21.08 10.57 21.30"
    "C9.93 21.51 9.22 21.62 8.44 21.62C7.67 21.62 6.95 21.51 6.29 21.31"
    "C5.63 21.10 5.10 20.80 4.70 20.40C4.30 20.01 4.10 19.53 4.10 18.98M8.88 21.20"
    "C9.35 21.20 9.67 21.03 9.84 20.68C10.02 20.34 10.10 19.93 10.10 19.46"
    "C10.10 18.97 10.00 18.53 9.80 18.13C9.60 17.73 9.34 17.40 9.00 17.16"
    "C8.67 16.92 8.30 16.80 7.88 16.80C7.41 16.80 7.09 16.97 6.94 17.32"
    "C6.78 17.66 6.70 18.07 6.70 18.54C6.70 19.01 6.79 19.45 6.99 19.85"
    "C7.18 20.25 7.44 20.58 7.77 20.83C8.09 21.08 8.46 21.20 8.88 21.20Z"
)
EXERCISE_INTERVALS = (
    f'<path d="{_INTERVAL_NOTE}" fill="COLOR"/>'
    f'<path d="{_INTERVAL_NOTE}" fill="COLOR" transform="translate(0 -14)"/>'
    '<path d="M17.0 5H19.6V19H17.0" fill="none" stroke="COLOR" stroke-width=".95" stroke-linecap="round" stroke-linejoin="round"/>'
)

EXERCISE_INTERVAL_CONSTRUCTION = (
    f'<path d="{_INTERVAL_NOTE}" fill="COLOR"/>'
    f'<path d="{_INTERVAL_NOTE}" fill="COLOR" opacity=".55" transform="translate(0 -14)"/>'
    '<path d="M18 19V5m-3 3 3-3 3 3" fill="none" stroke="COLOR" stroke-width="1.4" stroke-linejoin="round"/>'
)

# Key signature identification: a sharp and a flat side by side, in the Noto Music outlines the app icon uses.
_SHARP_PATH = (
    "M12.12 14.58L9.92 15.54L9.92 19.45L8.87 19.45L8.87 15.97L5.25 17.72L5.25 21.65"
    "L4.20 21.65L4.20 18.15L2.00 19.20L2.00 17.45L4.20 16.42L4.20 10.92L2.00 11.98L2.00 10.23"
    "L4.20 9.17L4.20 5.61L5.25 5.61L5.25 8.75L8.87 7.00L8.87 3.18L9.92 3.18L9.92 6.57"
    "L12.12 5.54L12.12 7.27L9.92 8.32L9.92 13.82L12.12 12.83L12.12 14.58M8.87 14.24L8.87 8.75"
    "L5.25 10.50L5.25 15.99L8.87 14.24Z"
)
_FLAT_PATH = (
    "M16.51 2.35L17.34 2.35L17.34 10.09C17.77 9.48 18.22 9.00 18.68 8.65"
    "C19.15 8.29 19.60 8.12 20.05 8.12C20.66 8.12 21.14 8.31 21.48 8.68"
    "C21.83 9.05 22.00 9.57 22.00 10.23C22.00 11.09 21.75 11.86 21.26 12.54"
    "C20.93 12.99 20.52 13.37 20.03 13.68C19.53 14.00 19.01 14.24 18.47 14.41"
    "C17.92 14.58 17.40 14.67 16.91 14.67L16.51 14.67L16.51 2.35M17.34 10.95L17.34 14.04"
    "C17.74 14.04 18.23 13.88 18.79 13.55C19.38 13.22 19.84 12.79 20.19 12.25"
    "C20.55 11.71 20.72 11.12 20.72 10.47C20.72 10.04 20.66 9.71 20.53 9.48"
    "C20.41 9.24 20.17 9.13 19.83 9.13C19.41 9.13 18.97 9.31 18.51 9.67"
    "C18.06 10.03 17.66 10.45 17.34 10.95Z"
)
EXERCISE_KEY_SIGNATURES = f'<path d="{_SHARP_PATH}" fill="COLOR"/><path d="{_FLAT_PATH}" fill="COLOR"/>'
# The first three sharps of a treble signature, using the shared Noto Music outline.
EXERCISE_ORDER_OF_KEYS = "".join(
    f'<path transform="translate({x} {y}) scale(.66)" d="{_SHARP_PATH}" fill="COLOR"/>' for x, y in ((0, 3), (7, 8), (14, 1))
)
# Key signature construction: a fork on its side, a stem and two tines, with a sharp at the end of the upper tine and a flat at
# the end of the lower one, in the Noto Music outlines the app icon uses.
_FORK_SHARP = (
    "M22.30 7.66L21.13 8.17L21.13 10.25L20.56 10.25L20.56 8.40L18.64 9.33L18.64 11.43"
    "L18.07 11.43L18.07 9.56L16.90 10.12L16.90 9.19L18.07 8.64L18.07 5.70L16.90 6.27"
    "L16.90 5.33L18.07 4.77L18.07 2.87L18.64 2.87L18.64 4.54L20.56 3.61L20.56 1.57L21.13 1.57"
    "L21.13 3.38L22.30 2.83L22.30 3.75L21.13 4.32L21.13 7.25L22.30 6.72L22.30 7.66M20.56 7.48"
    "L20.56 4.54L18.64 5.48L18.64 8.41L20.56 7.48Z"
)
_FORK_FLAT = (
    "M18.13 14.21L18.58 14.21L18.58 18.34C18.81 18.02 19.05 17.76 19.30 17.57"
    "C19.54 17.38 19.79 17.29 20.03 17.29C20.35 17.29 20.61 17.39 20.79 17.59"
    "C20.97 17.79 21.07 18.06 21.07 18.41C21.07 18.88 20.93 19.29 20.67 19.65"
    "C20.50 19.89 20.28 20.09 20.01 20.26C19.75 20.43 19.47 20.56 19.18 20.65"
    "C18.89 20.74 18.61 20.79 18.35 20.79L18.13 20.79L18.13 14.21M18.58 18.80L18.58 20.45"
    "C18.79 20.45 19.05 20.36 19.35 20.19C19.67 20.01 19.92 19.78 20.10 19.49"
    "C20.29 19.21 20.38 18.89 20.38 18.55C20.38 18.32 20.35 18.14 20.28 18.01"
    "C20.22 17.89 20.09 17.83 19.91 17.83C19.68 17.83 19.45 17.92 19.21 18.12"
    "C18.96 18.31 18.75 18.54 18.58 18.80Z"
)
EXERCISE_KEY_CONSTRUCTION = (
    f'<path d="M2.5 12H7M7 6.5V17.5M7 6.5H15M7 17.5H15" {_LINE}/>'
    f'<path d="{_FORK_SHARP}" fill="COLOR"/>'
    f'<path d="{_FORK_FLAT}" fill="COLOR" stroke="COLOR" stroke-width=".25" stroke-linejoin="round"/>'
)
# Scale construction: four whole notes climbing, in the Noto Music outline the app icon uses, with a thin arrow running up beside
# them, for building a scale. Each note is the first moved.
_BUILD_NOTE = (
    "M4.50 20.54C4.50 20.15 4.64 19.82 4.92 19.53C5.19 19.24 5.57 19.02 6.05 18.85"
    "C6.53 18.69 7.06 18.60 7.64 18.60C8.23 18.60 8.77 18.68 9.26 18.84"
    "C9.76 19.00 10.15 19.23 10.45 19.52C10.75 19.80 10.90 20.14 10.90 20.54"
    "C10.90 20.94 10.76 21.29 10.47 21.58C10.18 21.87 9.80 22.10 9.32 22.26"
    "C8.84 22.42 8.31 22.50 7.73 22.50C7.15 22.50 6.62 22.42 6.13 22.27"
    "C5.64 22.11 5.25 21.89 4.95 21.60C4.65 21.30 4.50 20.95 4.50 20.54M8.06 22.19"
    "C8.41 22.19 8.65 22.06 8.77 21.80C8.90 21.55 8.97 21.24 8.97 20.89"
    "C8.97 20.53 8.89 20.20 8.74 19.90C8.59 19.60 8.40 19.36 8.15 19.18"
    "C7.90 19.00 7.62 18.91 7.31 18.91C6.96 18.91 6.73 19.04 6.61 19.30"
    "C6.49 19.56 6.43 19.86 6.43 20.21C6.43 20.56 6.50 20.89 6.65 21.19"
    "C6.79 21.48 6.99 21.73 7.23 21.91C7.47 22.10 7.75 22.19 8.06 22.19Z"
)
EXERCISE_SCALE_CONSTRUCTION = (
    '<g transform="translate(-3 0)">'
    f'<path d="{_BUILD_NOTE}" fill="COLOR"/>'
    f'<path d="{_BUILD_NOTE}" fill="COLOR" transform="translate(2.87 -5.7)"/>'
    f'<path d="{_BUILD_NOTE}" fill="COLOR" transform="translate(5.73 -11.4)"/>'
    f'<path d="{_BUILD_NOTE}" fill="COLOR" transform="translate(8.6 -17.1)"/>'
    "</g>"
    '<path d="M21 2.4L23.3 5.6H21.45V21.6H20.55V5.6H18.7Z" fill="COLOR" stroke="COLOR" stroke-width=".4" stroke-linejoin="round"/>'
)


def _cells(
    radius: float,
    *,
    gap: float,
) -> str:
    """
    Return the SVG for a ring cut into twelve cells, with the gap between cells centered at the top.

    Parameters
    ----------
    radius : float
        The ring's radius in the 24 by 24 drawing.
    gap : float
        The length of the gap between neighboring cells, along the ring. Keyword-only.

    Returns
    -------
    str
        A dashed `<circle>` element.

    Examples
    --------
    >>> _cells(9, gap=1).startswith('<circle cx="12" cy="12" r="9"')
    True
    """
    per_cell = 2 * math.pi * radius / 12
    start = -90 - math.degrees(gap / radius) / 2
    return (
        f'<circle cx="12" cy="12" r="{radius}" fill="none" stroke="COLOR" stroke-width="2.4" '
        f'stroke-dasharray="{per_cell - gap:.2f} {gap}" transform="rotate({start:.2f} 12 12)"/>'
    )


# Circle of fifths: two rings, each cut into twelve cells.
EXERCISE_CIRCLE = _cells(9, gap=1.0) + _cells(5, gap=0.8)
# Scale spelling: four whole notes climbing step by step, in the Noto Music outline the app icon uses. Each is the first moved.
_SCALE_NOTE = (
    "M1.00 20.85C1.00 20.43 1.15 20.07 1.46 19.75C1.76 19.44 2.17 19.19 2.70 19.01"
    "C3.22 18.83 3.80 18.74 4.43 18.74C5.08 18.74 5.67 18.83 6.21 19.00"
    "C6.75 19.18 7.18 19.42 7.51 19.74C7.84 20.05 8.00 20.42 8.00 20.85"
    "C8.00 21.29 7.84 21.67 7.53 21.99C7.21 22.31 6.79 22.56 6.27 22.74"
    "C5.74 22.91 5.17 23.00 4.53 23.00C3.90 23.00 3.32 22.92 2.78 22.75"
    "C2.25 22.58 1.82 22.33 1.49 22.01C1.16 21.69 1.00 21.30 1.00 20.85M4.89 22.66"
    "C5.27 22.66 5.53 22.52 5.68 22.24C5.82 21.96 5.89 21.62 5.89 21.24"
    "C5.89 20.85 5.80 20.49 5.64 20.16C5.48 19.83 5.26 19.57 4.99 19.37"
    "C4.72 19.17 4.42 19.08 4.08 19.08C3.69 19.08 3.44 19.22 3.31 19.50"
    "C3.18 19.78 3.11 20.11 3.11 20.50C3.11 20.88 3.19 21.24 3.35 21.56"
    "C3.51 21.89 3.72 22.15 3.98 22.36C4.25 22.56 4.55 22.66 4.89 22.66Z"
)
EXERCISE_SCALES = (
    f'<path d="{_SCALE_NOTE}" fill="COLOR"/>'
    f'<path d="{_SCALE_NOTE}" fill="COLOR" transform="translate(5 -5.91)"/>'
    f'<path d="{_SCALE_NOTE}" fill="COLOR" transform="translate(10 -11.83)"/>'
    f'<path d="{_SCALE_NOTE}" fill="COLOR" transform="translate(15 -17.74)"/>'
)
# Chord quality: three whole notes stacked in thirds, with room between them, in the Noto Music outline the app icon uses.
_CHORD_NOTE = (
    "M7.89 19.48C7.89 18.99 8.07 18.56 8.43 18.19C8.79 17.82 9.27 17.53 9.89 17.32"
    "C10.50 17.11 11.18 17.00 11.92 17.00C12.67 17.00 13.37 17.10 14.00 17.31"
    "C14.64 17.51 15.15 17.80 15.53 18.17C15.91 18.54 16.11 18.98 16.11 19.48"
    "C16.11 20.00 15.92 20.44 15.55 20.82C15.18 21.20 14.69 21.49 14.07 21.69"
    "C13.46 21.90 12.78 22.00 12.04 22.00C11.30 22.00 10.61 21.90 9.99 21.70"
    "C9.36 21.50 8.85 21.22 8.47 20.84C8.09 20.46 7.89 20.01 7.89 19.48M12.46 21.60"
    "C12.91 21.60 13.21 21.44 13.38 21.11C13.54 20.78 13.63 20.39 13.63 19.94"
    "C13.63 19.47 13.53 19.05 13.34 18.67C13.15 18.28 12.89 17.98 12.58 17.74"
    "C12.26 17.51 11.90 17.40 11.50 17.40C11.05 17.40 10.75 17.56 10.60 17.89"
    "C10.45 18.22 10.37 18.61 10.37 19.06C10.37 19.51 10.47 19.93 10.65 20.31"
    "C10.84 20.70 11.08 21.01 11.40 21.25C11.71 21.48 12.06 21.60 12.46 21.60Z"
)
EXERCISE_CHORDS = (
    f'<path d="{_CHORD_NOTE}" fill="COLOR"/>'
    f'<path d="{_CHORD_NOTE}" fill="COLOR" transform="translate(0 -7.5)"/>'
    f'<path d="{_CHORD_NOTE}" fill="COLOR" transform="translate(0 -15)"/>'
)
# Arpeggio identification: three eighth notes rising under one heavy beam. The notes are the Noto Music quarter note the app icon
# uses; the beam across their stems is a drawn bar, since the font has no three-note beam. Each note is the first moved.
_ARPEGGIO_NOTE = (
    "M6.43 9.28L6.43 19.94C6.43 20.30 6.31 20.64 6.07 20.95C5.83 21.27 5.51 21.52 5.13 21.71"
    "C4.75 21.90 4.35 22.00 3.92 22.00C3.53 22.00 3.22 21.90 2.98 21.70"
    "C2.74 21.50 2.62 21.23 2.62 20.89C2.62 20.63 2.70 20.37 2.85 20.13"
    "C3.00 19.88 3.21 19.66 3.46 19.46C3.71 19.26 3.98 19.10 4.28 18.99"
    "C4.58 18.87 4.87 18.81 5.16 18.81C5.52 18.81 5.84 18.92 6.10 19.13L6.10 9.28L6.43 9.28Z"
)
EXERCISE_ARPEGGIOS = (
    f'<path d="{_ARPEGGIO_NOTE}" fill="COLOR"/>'
    f'<path d="{_ARPEGGIO_NOTE}" fill="COLOR" transform="translate(7.47 -3.64)"/>'
    f'<path d="{_ARPEGGIO_NOTE}" fill="COLOR" transform="translate(14.95 -7.28)"/>'
    '<path d="M5.99 9.28L13.46 5.64L21.38 2.00L21.38 4.49L13.46 8.13L5.99 11.77L5.99 9.28Z" fill="COLOR"/>'
)

# A play triangle, for the "hear it" buttons.
PLAY = '<path d="M8 5.5v13l11-6.5z" fill="COLOR" stroke="COLOR" stroke-width="1.6" stroke-linejoin="round"/>'

# Keyboard: seven white keys (C through B) with the two-and-three black-key pattern. Retain the real key proportions:
# white keys are 6.2 times as long as they are wide; black keys are 0.58 as wide and 0.63 as long.
# Black-key centers match KeyboardWidget: slightly offset from the white-key boundaries within each group.
# Leave room above the shared keyboard artwork for the interval icon's bracket.
# Keep the key fills and dividers fixed so they read as piano keys in every theme.
_WHITE_KEY = 'y="5.56" width="2.7" height="16.74" rx="0.35" fill="#ffffff" stroke="#202020" stroke-width="0.65"'
EXERCISE_KEYBOARD = "".join(
    f'<rect x="{x:.2f}" {_WHITE_KEY}/>' for x in (2.55, 5.25, 7.95, 10.65, 13.35, 16.05, 18.75)
) + "".join(
    f'<rect x="{x:.3f}" y="5.56" width="1.566" height="10.5462" rx="0.2" fill="#202020"/>'
    for x in (4.278, 7.356, 12.189, 15.267, 18.345)
)

# Help: a question mark in a circle.
HELP = (
    '<circle cx="12" cy="12" r="9" fill="none" stroke="COLOR" stroke-width="2"/>'
    '<path d="M9.4 9.6a2.7 2.7 0 1 1 3.9 2.4c-.9.5-1.3 1.1-1.3 2" fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round"/>'
    '<circle cx="12" cy="16.9" r="1.15" fill="COLOR"/>'
)

# Reference: an open book.
BOOK = (
    '<path d="M12 6.5C10 5 7 4.6 3.5 5v13c3.5-.4 6.5 0 8.5 1.5M12 6.5c2-1.5 5-1.9 8.5-1.5v13c-3.5-.4-6.5 0-8.5 1.5M12 6.5v13" '
    'fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
)

# Search: a magnifying glass.
SEARCH = (
    '<circle cx="10.5" cy="10.5" r="6" fill="none" stroke="COLOR" stroke-width="2"/>'
    '<path d="M15 15l5.5 5.5" fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round"/>'
)

# Category filter: a funnel.
FILTER = '<path d="M3 4h18l-7 8v7l-4 2v-9z" fill="none" stroke="COLOR" stroke-width="2" stroke-linejoin="round"/>'
SHUFFLE = (
    '<g fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 6h2c5 0 8 12 13 12h3m-3-3 3 3-3 3M3 18h2c2 0 4-2 6-5m2-4c2-2 3-3 5-3h3m-3-3 3 3-3 3"/></g>'
)

# Tile catalog: a two-by-two grid.
TILES = (
    '<g fill="none" stroke="COLOR" stroke-width="2" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7" rx="1"/>'
    '<rect x="14" y="3" width="7" height="7" rx="1"/>'
    '<rect x="3" y="14" width="7" height="7" rx="1"/>'
    '<rect x="14" y="14" width="7" height="7" rx="1"/></g>'
)

# Navigation pane: a window with a left sidebar.
NAVIGATION_PANE = (
    '<rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="COLOR" stroke-width="2"/>'
    '<path d="M9 3v18" fill="none" stroke="COLOR" stroke-width="2"/>'
)

# Framed sidebar actions: the arrow points toward the destination of the pane.
NAVIGATION_OPEN = (
    NAVIGATION_PANE
    + '<path d="m14 9 3 3-3 3" fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
)
NAVIGATION_CLOSE = (
    NAVIGATION_PANE
    + '<path d="m17 9-3 3 3 3" fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
)

# Keyboard intervals: the shared keyboard with a span bracket above the keys.
EXERCISE_KEYBOARD_INTERVALS = (
    EXERCISE_KEYBOARD
    + '<path d="M3.9 3.6V1.5H20.1V3.6" fill="none" stroke="COLOR" stroke-width="0.7" stroke-linecap="round" stroke-linejoin="round"/>'
)

# Exercises: Iconoir music-double-note with filled note heads (MIT; see THIRD_PARTY_NOTICES.md).
EXERCISES = (
    '<g stroke="COLOR" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 14V3L9 5V16" fill="none"/>'
    '<path d="M17 19H18C19.1046 19 20 18.1046 20 17V14H17C15.8954 14 15 14.8954 15 16V17C15 18.1046 15.8954 19 17 19Z" fill="COLOR"/>'
    '<path d="M6 21H7C8.10457 21 9 20.1046 9 19V16H6C4.89543 16 4 16.8954 4 18V19C4 20.1046 4.89543 21 6 21Z" fill="COLOR"/>'
    "</g>"
)

# Lessons: a mortarboard.
LESSONS = (
    '<path d="M2 9.5l10-5 10 5-10 5zM6 12v4.5c0 1.4 2.7 2.8 6 2.8s6-1.4 6-2.8V12M22 9.5v5.5" '
    'fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
)

# Note construction: a quarter note, in the Noto Music outline the app icon uses, with a thin up arrow high and a thin
# down arrow low beside it, for moving a note up and down the staff.
_CONSTRUCTION_NOTE = (
    "M7.75 3.50L7.75 17.74C7.75 18.23 7.59 18.68 7.26 19.10C6.94 19.52 6.52 19.86 6.01 20.12"
    "C5.50 20.37 4.96 20.50 4.39 20.50C3.87 20.50 3.45 20.37 3.13 20.10"
    "C2.81 19.83 2.65 19.47 2.65 19.02C2.65 18.67 2.76 18.33 2.96 18.00"
    "C3.17 17.67 3.44 17.37 3.77 17.10C4.10 16.83 4.47 16.62 4.87 16.47"
    "C5.27 16.32 5.66 16.24 6.04 16.24C6.53 16.24 6.95 16.38 7.30 16.67L7.30 3.50L7.75 3.50Z"
)
_ARROW_STROKE = 'stroke="COLOR" stroke-width=".4" stroke-linejoin="round"'
EXERCISE_CONSTRUCTION = (
    f'<path d="{_CONSTRUCTION_NOTE}" fill="COLOR"/>'
    f'<path d="M15.2 20.8L17.5 17.6H15.65V9.4H14.75V17.6H12.9Z" fill="COLOR" {_ARROW_STROKE}/>'
    f'<path d="M20.5 3.2L22.8 6.4H20.95V14.6H20.05V6.4H18.2Z" fill="COLOR" {_ARROW_STROKE}/>'
)

# Clef basics: the alto clef, in the outline the app icon uses (Noto Music), scaled to fit 24 by 24.
_CLEF_PATH = (
    "M17.2 99.0L17.2 1.2L20.8 1.2L20.8 49.1C22.0 48.5 23.3 47.4 24.6 45.6"
    "C25.9 43.8 27.1 41.8 28.3 39.5C29.4 37.2 30.5 34.8 31.3 32.5"
    "C32.2 30.2 32.7 28.2 32.9 26.4C33.5 30.9 34.9 34.5 36.9 37.0"
    "C38.9 39.6 41.4 40.9 44.3 40.9C47.3 40.9 49.4 39.7 50.9 37.3"
    "C52.4 34.9 53.1 30.2 53.1 23.2C53.1 20.4 53.0 18.0 52.9 16.0"
    "C52.7 14.0 52.4 12.4 52.1 11.2C51.2 8.3 49.9 6.2 48.0 5.0C46.2 3.8 43.9 3.2 41.1 3.2"
    "C39.6 3.2 38.4 3.5 37.6 4.2C36.7 4.8 36.3 5.4 36.3 6.0C36.3 6.4 36.5 7.0 37.0 7.6"
    "C37.4 8.3 37.9 8.9 38.5 9.6C39.6 10.9 40.1 12.1 40.1 13.2C40.1 14.8 39.5 16.2 38.4 17.5"
    "C37.3 18.7 35.6 19.4 33.5 19.4C31.5 19.4 29.9 18.7 28.6 17.3"
    "C27.3 15.9 26.7 14.2 26.7 12.2C26.7 9.8 27.5 7.7 29.1 5.9C30.7 4.1 32.8 2.6 35.4 1.6"
    "C37.9 0.5 40.7 0.0 43.7 0.0C47.9 0.0 51.7 1.0 55.0 2.9C58.3 4.9 61.0 7.6 63.0 11.1"
    "C64.9 14.5 65.9 18.5 65.9 23.0C65.9 25.8 65.6 28.4 65.0 30.7"
    "C64.4 33.1 63.4 35.2 62.1 37.1C60.4 39.6 58.1 41.5 55.4 42.9"
    "C52.6 44.3 49.7 45.0 46.7 45.0C45.2 45.0 43.7 44.8 42.2 44.5"
    "C40.7 44.1 39.2 43.6 37.9 42.9L33.3 50.1L37.9 57.3C39.4 56.7 40.9 56.3 42.5 56.0"
    "C44.0 55.6 45.6 55.5 47.2 55.5C50.7 55.5 54.0 56.5 56.8 58.5"
    "C59.6 60.5 61.9 63.2 63.5 66.5C65.1 69.9 65.9 73.5 65.9 77.6"
    "C65.9 81.6 65.0 85.4 63.0 88.8C61.1 92.2 58.4 94.9 55.1 97.0"
    "C51.8 99.0 48.0 100.0 43.7 100.0C38.2 100.0 34.0 98.9 31.1 96.7"
    "C28.2 94.5 26.7 91.6 26.7 87.8C26.7 85.8 27.3 84.1 28.6 82.7"
    "C29.9 81.3 31.5 80.6 33.5 80.6C35.6 80.6 37.3 81.3 38.4 82.5"
    "C39.5 83.8 40.1 85.2 40.1 86.8C40.1 88.0 39.6 89.2 38.5 90.4"
    "C37.9 91.1 37.4 91.7 36.9 92.3C36.5 92.9 36.3 93.4 36.3 93.9"
    "C36.3 94.7 36.7 95.4 37.6 95.9C38.4 96.5 39.6 96.8 41.1 96.8"
    "C45.1 96.8 48.2 95.3 50.2 92.3C52.3 89.4 53.3 84.4 53.3 77.6"
    "C53.3 71.6 52.6 67.0 51.3 63.9C49.9 60.8 47.6 59.3 44.3 59.3"
    "C41.3 59.3 38.8 60.6 36.9 63.1C34.9 65.7 33.7 69.1 33.1 73.6"
    "C32.5 70.4 31.6 67.3 30.3 64.3C29.1 61.3 27.6 58.6 26.0 56.3"
    "C24.4 53.9 22.7 52.1 20.8 50.9L20.8 99.0L17.2 99.0M0.0 99.0L0.0 1.2L11.4 1.2L11.4 99.0"
    "L0.0 99.0"
)
EXERCISE_CLEFS = f'<path transform="translate(6.07 3.00) scale(0.18)" d="{_CLEF_PATH}" fill="COLOR"/>'

# Menu icons (24x24, outlined like the others): restart and the application's settings.
_MENU = 'fill="none" stroke="COLOR" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
TOOLS = (
    f'<path d="M20.5 3.8 17 7.3l-2.4-2.4 3.5-3.5a6 6 0 0 0-7.3 7.8l-8 8a2.5 2.5 0 0 0 3.5 3.5l8-8a6 6 0 0 0 6.2-8.9Z" {_MENU}/>'
)
CODE = f'<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 4l-4 16" {_MENU}/>'
# Two flashcards, with the back card visible above the front one.
FLASHCARDS = (
    f'<rect x="3" y="8" width="16" height="12" rx="2" {_MENU}/>'
    f'<path d="M6 5.5A2 2 0 0 1 8 4h11a2 2 0 0 1 2 2v9" {_MENU}/>'
)
# Iconoir GitHub icon; MIT license and attribution in THIRD_PARTY_NOTICES.md.
GITHUB = (
    '<g fill="none" stroke="COLOR" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 22.0268V19.1568C16.0375 18.68 15.9731 18.2006 15.811 17.7506C15.6489 17.3006 15.3929 16.8902 15.06 16.5468C18.2 16.1968 21.5 15.0068 21.5 9.54679C21.4997 8.15062 20.9627 6.80799 20 5.79679C20.4558 4.5753 20.4236 3.22514 19.91 2.02679C19.91 2.02679 18.73 1.67679 16 3.50679C13.708 2.88561 11.292 2.88561 8.99999 3.50679C6.26999 1.67679 5.08999 2.02679 5.08999 2.02679C4.57636 3.22514 4.54413 4.5753 4.99999 5.79679C4.03011 6.81549 3.49251 8.17026 3.49999 9.57679C3.49999 14.9968 6.79998 16.1868 9.93998 16.5768C9.61098 16.9168 9.35725 17.3222 9.19529 17.7667C9.03334 18.2112 8.96679 18.6849 8.99999 19.1568V22.0268"/>'
    '<path d="M9 20.0267C6 20.9999 3.5 20.0267 2 17.0267"/></g>'
)
ISSUE = f'<path d="M12 3 22 21H2ZM12 9v5" {_MENU}/><circle cx="12" cy="17.5" r="1.1" fill="COLOR"/>'
INFO = f'<circle cx="12" cy="12" r="9" {_MENU}/><path d="M12 11v6" {_MENU}/><circle cx="12" cy="7" r="1" fill="COLOR"/>'
RESTART = f'<path d="M19 12a7 7 0 1 1-2.05-4.95M17.6 3.6v4h-4" {_MENU}/>'
GEAR = (
    f'<circle cx="12" cy="12" r="3" {_MENU}/><circle cx="12" cy="12" r="6.4" {_MENU}/>'
    '<path d="M12 3.2v2.4M12 18.4v2.4M3.2 12h2.4M18.4 12h2.4M5.8 5.8l1.7 1.7M16.5 16.5l1.7 1.7M5.8 18.2l1.7-1.7M16.5 7.5l1.7-1.7" '
    'fill="none" stroke="COLOR" stroke-width="2.6" stroke-linecap="round"/>'
)
# Quit: a power symbol, a broken ring with a line through the gap.
QUIT = f'<path d="M12 3.5v8M7.2 6.6a7.2 7.2 0 1 0 9.6 0" {_MENU}/>'
# Export and import: a tray with an arrow going out of it, or into it.
_TRAY = f'<path d="M4.5 15v4.5h15V15" {_MENU}/>'
EXPORT = _TRAY + f'<path d="M12 15V4.2M7.8 8.2L12 4l4.2 4.2" {_MENU}/>'
IMPORT = _TRAY + f'<path d="M12 4v10.8M7.8 10.8L12 15l4.2-4.2" {_MENU}/>'
# Plugins: an electrical plug, two prongs over a rounded body with its cord.
PLUGIN = f'<path d="M9 3v4M15 3v4M6 7h12v3a6 6 0 0 1-12 0zM12 16v5" {_MENU}/>'
# Check for updates: an arrow going up inside a circle.
UPDATE = f'<circle cx="12" cy="12" r="8.2" {_MENU}/><path d="M12 16.2V8M8.6 11.4L12 8l3.4 3.4" {_MENU}/>'
# Profile: a head and shoulders.
PROFILE = f'<circle cx="12" cy="8.2" r="3.6" {_MENU}/><path d="M4.6 20c.7-4 3.7-6 7.4-6s6.7 2 7.4 6" {_MENU}/>'
# Statistics: a line graph, a rising line with its points over a pair of axes.
CHART = (
    f'<path d="M4 4v16h16" {_MENU}/><path d="M8 15l3.6-4.4 3 2.6 4.4-6" {_MENU}/>'
    '<circle cx="8" cy="15" r="1.2" fill="COLOR"/><circle cx="11.6" cy="10.6" r="1.2" fill="COLOR"/>'
    '<circle cx="14.6" cy="13.2" r="1.2" fill="COLOR"/><circle cx="19" cy="7.2" r="1.2" fill="COLOR"/>'
)
# Three columns on a baseline for an individual question's statistics.
BAR_CHART = (
    f'<path d="M3 20h18" {_MENU}/><g fill="COLOR">'
    '<rect x="5" y="11" width="3.5" height="8" rx="0.8"/><rect x="10.25" y="5" width="3.5" height="14" rx="0.8"/>'
    '<rect x="15.5" y="8" width="3.5" height="11" rx="0.8"/></g>'
)
# Database: a stack of discs, drawn as a cylinder.
DATABASE = (
    f'<ellipse cx="12" cy="6" rx="7" ry="2.6" {_MENU}/>'
    f'<path d="M5 6v12c0 1.45 3.1 2.6 7 2.6s7-1.15 7-2.6V6M5 12c0 1.45 3.1 2.6 7 2.6s7-1.15 7-2.6" {_MENU}/>'
)
