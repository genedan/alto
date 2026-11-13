"""Small monochrome icons drawn from SVG, tinted with the current theme's text colour."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

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


def svg_icon(
    inner: str,
    color: QColor,
    size: int = 24,
    scale: float = 2.0,
) -> QIcon:
    """Render 24x24 SVG shapes (using COLOR as the colour) to a crisp icon of `size` logical pixels."""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{inner.replace("COLOR", color.name())}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    px = QPixmap(int(size * scale), int(size * scale))
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    px.setDevicePixelRatio(scale)
    return QIcon(px)


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
    y: float,
    rx: float = 3.3,
    ry: float = 2.3,
) -> str:
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" {_LINE}/>'


EXERCISE_NOTE_NAMES = _STAFF + _ring(
    12,
    11.25,
    3.4,
    2.1,
)
# Two stacked notes with a bracket spanning the distance between them.
EXERCISE_INTERVALS = (
    _ring(
        7,
        6,
        3.2,
        2.2,
    )
    + _ring(
        7,
        18,
        3.2,
        2.2,
    )
    + f'<path d="M15.5 6h4v12h-4" {_LINE}/>'
)
EXERCISE_KEY_SIGNATURES = f'<path d="M9 4v16M15 3.5v16M5 9.5l14-3M5 16.5l14-3" {_LINE}/>'
EXERCISE_SCALES = "".join(
    _ring(
        x,
        y,
        2.4,
        1.7,
    )
    for x, y in (
        (4.5, 18.5),
        (9.5, 14.8),
        (14.5, 11.1),
        (19.5, 7.4),
    )
)
EXERCISE_CHORDS = (
    _ring(
        12,
        18.5,
        3.6,
        2.4,
    )
    + _ring(
        12,
        12,
        3.6,
        2.4,
    )
    + _ring(
        12,
        5.5,
        3.6,
        2.4,
    )
)
# Three eighth notes rising under one beam.
_NOTE = 'fill="COLOR" stroke="COLOR" stroke-width="1" stroke-linejoin="round"'


def _beamed_notes() -> str:
    heads = ((4.6, 19.0), (11.8, 15.0), (19.0, 11.0))  # note heads rise to the right
    beam_start, beam_end = (7.0, 6.2), (21.6, 2.2)  # the beam follows them
    out = []
    for x, y in heads:
        stem = x + 2.4  # the stem rises from the right edge of the head to the beam
        top = beam_start[1] + (stem - beam_start[0]) * (beam_end[1] - beam_start[1]) / (beam_end[0] - beam_start[0])
        out.append(f'<ellipse cx="{x}" cy="{y}" rx="2.7" ry="1.9" transform="rotate(-20 {x} {y})" {_NOTE}/>')
        out.append(f'<path d="M{stem} {y - 0.3}V{top:.2f}" {_LINE}/>')
    out.append(
        f'<path d="M{beam_start[0]} {beam_start[1]}L{beam_end[0]} {beam_end[1]}" stroke="COLOR" stroke-width="2.6" '
        'stroke-linecap="butt" fill="none"/>',
    )
    return "".join(out)


EXERCISE_ARPEGGIOS = _beamed_notes()

# A play triangle, for the "hear it" buttons.
PLAY = '<path d="M8 5.5v13l11-6.5z" fill="COLOR" stroke="COLOR" stroke-width="1.6" stroke-linejoin="round"/>'

# Keyboard: four white keys with black keys on top, in real proportions (a white key is 6.2 times as long as it is
# wide; a black key is 0.58 as wide and 0.63 as long) and in their real colours, not tinted to the theme.
EXERCISE_KEYBOARD = (
    '<path d="M5.20 1.46H8.60V21.94Q8.60 22.54 8.00 22.54H5.80Q5.20 22.54 5.20 21.94Z" fill="#ffffff" stroke="#5c5c64" stroke-width="0.7" stroke-linejoin="miter"/>'
    '<path d="M8.60 1.46H12.00V21.94Q12.00 22.54 11.40 22.54H9.20Q8.60 22.54 8.60 21.94Z" fill="#ffffff" stroke="#5c5c64" stroke-width="0.7" stroke-linejoin="miter"/>'
    '<path d="M12.00 1.46H15.40V21.94Q15.40 22.54 14.80 22.54H12.60Q12.00 22.54 12.00 21.94Z" fill="#ffffff" stroke="#5c5c64" stroke-width="0.7" stroke-linejoin="miter"/>'
    '<path d="M15.40 1.46H18.80V21.94Q18.80 22.54 18.20 22.54H16.00Q15.40 22.54 15.40 21.94Z" fill="#ffffff" stroke="#5c5c64" stroke-width="0.7" stroke-linejoin="miter"/>'
    '<rect x="7.38" y="1.46" width="1.97" height="13.28" rx="0.25" fill="#1a1a1a"/>'
    '<rect x="11.25" y="1.46" width="1.97" height="13.28" rx="0.25" fill="#1a1a1a"/>'
    '<rect x="14.41" y="1.46" width="1.97" height="13.28" rx="0.25" fill="#1a1a1a"/>'
)

# Help: a question mark in a circle.
HELP = (
    '<circle cx="12" cy="12" r="9" fill="none" stroke="COLOR" stroke-width="2"/>'
    '<path d="M9.4 9.6a2.7 2.7 0 1 1 3.9 2.4c-.9.5-1.3 1.1-1.3 2" fill="none" stroke="COLOR" stroke-width="2" stroke-linecap="round"/>'
    '<circle cx="12" cy="16.9" r="1.15" fill="COLOR"/>'
)

# Note construction: a staff with a note being dropped onto it.
EXERCISE_CONSTRUCTION = (
    '<path d="M2 11.5H22M2 14.3H22M2 17.1H22M2 19.9H22M2 22.7H22" fill="none" stroke="COLOR" stroke-width="1.1" opacity=".5"/>'
    + _ring(
        13,
        18.5,
        3.3,
        1.9,
    )
    + f'<path d="M13 1.6V8M10.2 5.2L13 8L15.8 5.2" {_LINE}/>'
)

# Menu icons (24x24, outlined like the others): home, restart and the application's settings.
_MENU = 'fill="none" stroke="COLOR" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
HOME = f'<path d="M3.5 11.2L12 4l8.5 7.2M6 9.6V20h4.4v-5.2h3.2V20H18V9.6" {_MENU}/>'
RESTART = f'<path d="M19 12a7 7 0 1 1-2.05-4.95M17.6 3.6v4h-4" {_MENU}/>'
GEAR = (
    f'<circle cx="12" cy="12" r="3" {_MENU}/><circle cx="12" cy="12" r="6.4" {_MENU}/>'
    '<path d="M12 3.2v2.4M12 18.4v2.4M3.2 12h2.4M18.4 12h2.4M5.8 5.8l1.7 1.7M16.5 16.5l1.7 1.7M5.8 18.2l1.7-1.7M16.5 7.5l1.7-1.7" '
    'fill="none" stroke="COLOR" stroke-width="2.6" stroke-linecap="round"/>'
)
# Quit: a power symbol, a broken ring with a line through the gap.
QUIT = f'<path d="M12 3.5v8M7.2 6.6a7.2 7.2 0 1 0 9.6 0" {_MENU}/>'
# Profile: a head and shoulders.
PROFILE = f'<circle cx="12" cy="8.2" r="3.6" {_MENU}/><path d="M4.6 20c.7-4 3.7-6 7.4-6s6.7 2 7.4 6" {_MENU}/>'
# Statistics: a line graph, a rising line with its points over a pair of axes.
CHART = (
    f'<path d="M4 4v16h16" {_MENU}/><path d="M8 15l3.6-4.4 3 2.6 4.4-6" {_MENU}/>'
    '<circle cx="8" cy="15" r="1.2" fill="COLOR"/><circle cx="11.6" cy="10.6" r="1.2" fill="COLOR"/>'
    '<circle cx="14.6" cy="13.2" r="1.2" fill="COLOR"/><circle cx="19" cy="7.2" r="1.2" fill="COLOR"/>'
)
# Database: a stack of discs, drawn as a cylinder.
DATABASE = (
    f'<ellipse cx="12" cy="6" rx="7" ry="2.6" {_MENU}/>'
    f'<path d="M5 6v12c0 1.45 3.1 2.6 7 2.6s7-1.15 7-2.6V6M5 12c0 1.45 3.1 2.6 7 2.6s7-1.15 7-2.6" {_MENU}/>'
)
