from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..theory.pitch import ACCIDENTAL_SYMBOLS, Note, key_accidental
from . import engraving
from .notation import NotationStyle, clef_shape
from .notation import current as current_style
from .notes import draw_note

# Diatonic index of the bottom staff line.
BOTTOM_LINE = {
    "treble": Note(4, letter=2).diatonic,  # E4
    "bass": Note(2, letter=4).diatonic,  # G2
    "alto": Note(3, letter=3).diatonic,  # F3
    "tenor": Note(3, letter=1).diatonic,  # D3
    "soprano": Note(4, letter=0).diatonic,  # C4
    "mezzo": Note(3, letter=5).diatonic,  # A3
    "baritone": Note(2, letter=6).diatonic,  # B2
}
CLEF_GLYPH = {
    "treble": "𝄞",
    "bass": "𝄢",
    "alto": "𝄡",
    "tenor": "𝄡",
    "soprano": "𝄡",
    "mezzo": "𝄡",
    "baritone_c": "𝄡",
    "baritone_f": "𝄢",
}
# (glyph top, glyph bottom) measured upward from the bottom staff line, in staff gaps
CLEF_EXTENT = {
    "treble": (6.6, -2.2),
    "bass": (4.0, 0.7),
    "alto": (4.0, 0.0),
    "tenor": (5.0, 1.0),
    "soprano": (2.0, -2.0),
    "mezzo": (3.0, -1.0),
    "baritone_c": (6.0, 2.0),
    "baritone_f": (3.0, -0.3),
}
MIDDLE_C = Note(4, letter=0).diatonic

# Where each key-signature accidental sits, in order of appearance. Each is a fourth up or a fifth down from the one before
# (sharps: F C G D A E B, flats: B E A D G C F), and the pattern is chosen so that all seven stay on the staff, or one step
# above or below it. This gives the usual signatures for the treble, bass, alto and tenor clefs, and works out the rest.
_SHARP_PATTERNS = (
    (
        -3,
        4,
        -3,
        -3,
        4,
        -3,
    ),
    (
        4,
        -3,
        4,
        -3,
        4,
        -3,
    ),
)
_FLAT_PATTERNS = (
    (
        3,
        -4,
        3,
        -4,
        3,
        -4,
    ),
    (
        -4,
        3,
        -4,
        3,
        -4,
        3,
    ),
)


def key_signature_positions(
    clef: str,
    *,
    sign: int,
) -> list[str]:
    """The notes the sharps (sign 1) or flats (sign -1) of a key signature are written on in this clef."""
    bottom = BOTTOM_LINE[clef]
    first, patterns = ("F", _SHARP_PATTERNS) if sign > 0 else ("B", _FLAT_PATTERNS)
    for steps in patterns:
        for start in range(bottom - 1, bottom + 10):
            offsets = [0]
            for s in steps:
                offsets.append(offsets[-1] + s)
            places = [start + o for o in offsets]
            if Note.from_diatonic(start).name == first and all(bottom - 1 <= d <= bottom + 9 for d in places):
                return [f"{n.name}{n.octave}" for n in [Note.from_diatonic(d) for d in places]]
    raise ValueError(f"no key signature fits the {clef} clef")


_KEY_POSITIONS = {(clef, sign): " ".join(key_signature_positions(clef, sign=sign)) for clef in BOTTOM_LINE for sign in (1, -1)}
KEY_STEP = 13.0  # horizontal spacing between key-signature accidentals
# A staff with few notes should not stretch across a wide window: each column of notes gets at most this much width, and the
# staff is never made narrower than MIN_COLUMNS columns would need.
MAX_STEP = 120.0
MIN_COLUMNS = 3

# Grand staff layout, in staff gaps: margin above/below the pair and the distance between them.
GRAND_BETWEEN = 3.5
CORNER_RADIUS = 14


def draw_key_signature(
    p: QPainter,
    *,
    clef: str,
    key: int,
    x: float,
    bottom: float,
    gap: float,
    color: QColor,
    step: float = KEY_STEP,
    size: float = 2.0,
    font: str | None = None,
) -> None:
    """Draw the sharps or flats of a key signature (`key` sharps if positive, flats if negative) starting at x.
    `font` is a SMuFL font to engrave them in; None uses the built-in sharp and flat characters."""
    if not key:
        return
    if font:
        positions = _KEY_POSITIONS[(clef, 1 if key > 0 else -1)].split()
        for i, name in enumerate(positions[: abs(key)]):
            y = bottom - (Note.parse(name).diatonic - BOTTOM_LINE[clef]) * gap / 2
            engraving.draw_accidental(
                p,
                font=font,
                sign=1 if key > 0 else -1,
                x=x + i * step,
                y=y,
                gap=gap,
                colour=color,
                fit=step - 1,
            )
        return
    sign = "♯" if key > 0 else "♭"
    positions = _KEY_POSITIONS[(clef, 1 if key > 0 else -1)].split()
    p.save()
    p.setPen(QPen(color, 1.4))
    sign_font = QFont("DejaVu Sans")
    sign_font.setPixelSize(max(int(gap * size * 1.33), 6))
    p.setFont(sign_font)
    for i, name in enumerate(positions[: abs(key)]):
        y = bottom - (Note.parse(name).diatonic - BOTTOM_LINE[clef]) * gap / 2
        p.drawText(QPointF(x + i * step, y + gap * 0.5), sign)
    p.restore()


class StaffWidget(QWidget):
    def __init__(
        self,
        parent=None,
        *,
        gap: float = 16.0,
        side: float = 20.0,
        note_offset: float = 100.0,
        margin: float = 8.0,
        compact: bool = False,
        max_step: float | None = None,
    ):
        """`gap` is the distance between staff lines in pixels; `margin` is the space (in gaps) kept above
        and below the staff for ledger lines; `compact` sizes the widget to fit instead of the 220 px default.
        `max_step`, if given, is the most width each column of notes may take: the staff then stops growing once
        its notes would be spread wider than that, so a few notes stay easy to read in a wide window."""
        super().__init__(parent)
        self.GAP, self.side, self.note_offset, self.margin, self.compact = gap, side, note_offset, margin, compact
        self.max_step = max_step
        self.clef = "treble"
        self.columns: list[list[Note]] = []
        self.note_color: QColor | None = None  # None draws notes in the style's ink
        self.notation_style: NotationStyle | None = None  # None follows the style chosen in settings
        self.key = 0
        self.value = "whole"
        self.caption = ""  # text written under the staff, inside the paper
        self._fit_height("treble")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def show_notes(
        self,
        columns: list[list[Note]],
        *,
        clef: str = "treble",
        key: int = 0,
        value: str = "whole",
        caption: str = "",
    ) -> None:
        self.columns, self.clef, self.key, self.value, self.caption = columns, clef, key, value, caption
        self.note_color = None
        self._fit_height(clef)
        self._fit_width()
        self.update()

    def _fit_width(self) -> None:
        """Cap the width so that no column of notes is spread wider than `max_step` (see __init__)."""
        if self.max_step is None:
            return
        left = self.side + (18.0 if self.clef == "grand" else 0.0)  # the same left edge the drawing uses
        columns = max(len(self.columns), MIN_COLUMNS)
        self.setMaximumWidth(round(left + self.note_offset + KEY_STEP * abs(self.key) + columns * self.max_step + self.side))

    def sizeHint(self) -> QSize:
        """A capped staff asks for its full capped width, so a layout that centres it gives it that much."""
        if self.max_step is None:
            return super().sizeHint()
        return QSize(self.maximumWidth(), self.minimumHeight())

    def _fit_height(self, clef: str) -> None:
        grand_height = 2 * self.margin + 8 + GRAND_BETWEEN  # in gaps
        if self.compact:
            self.setFixedHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP))
        else:
            self.setMinimumHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP) + 10)

    def set_note_color(self, color: QColor | None) -> None:
        self.note_color = QColor(color) if color is not None else None
        self.update()

    def staff_bottoms(self) -> dict[str, float]:
        """Where each staff is drawn: clef name -> y of its bottom line (a grand staff has a treble and a bass)."""
        gap, h = self.GAP, self.height()
        if self.clef == "grand":
            top = (h - (2 * self.margin + 8 + GRAND_BETWEEN) * gap) / 2 + self.margin * gap
            return {"treble": top + 4 * gap, "bass": top + (8 + GRAND_BETWEEN) * gap}
        return {self.clef: h / 2 + 2 * gap}

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        look = self.notation_style or current_style()
        font = look.font
        fg = QColor("black")
        line = engraving.staff_line_width(font, gap=self.GAP) if font else look.line
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        p.drawRoundedRect(self.rect(), CORNER_RADIUS, CORNER_RADIUS)  # the rounded "paper" behind the music
        p.setPen(QPen(fg, line))
        gap = self.GAP
        w = self.width()
        grand = self.clef == "grand"
        left, right = self.side + (18.0 if grand else 0.0), w - self.side

        staves = self.staff_bottoms()

        def staff_for(note: Note) -> str:
            if not grand:
                return self.clef
            return "treble" if note.diatonic >= MIDDLE_C else "bass"

        for clef, bottom in staves.items():
            for i in range(5):
                p.drawLine(QPointF(left, bottom - i * gap), QPointF(right, bottom - i * gap))
            self._draw_clef(
                p,
                clef=clef,
                x=left + 8,
                bottom=bottom,
                gap=gap,
                color=fg,
                font=font,
            )
            self._draw_key_signature(
                p,
                clef=clef,
                x=left + 56,
                bottom=bottom,
                gap=gap,
                color=fg,
                font=font,
            )
        if grand:
            ys = list(staves.values())
            p.drawLine(QPointF(left, ys[0] - 4 * gap), QPointF(left, ys[1]))
            self._brace(
                p,
                x=left - 3,
                y0=ys[0] - 4 * gap,
                y1=ys[1],
                color=fg,
                font=font,
            )

        if self.caption:
            caption_font = QFont(self.font())
            caption_font.setPixelSize(max(int(gap * 1.6), 12))
            p.setFont(caption_font)
            p.setPen(fg)
            top = max(staves.values()) + 2.5 * gap  # below the lowest staff, clear of its ledger lines
            p.drawText(
                QRectF(
                    left,
                    top,
                    right - left,
                    max(self.height() - top - gap, gap * 2),
                ),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.caption,
            )

        n = max(len(self.columns), 1)
        x0 = left + self.note_offset + KEY_STEP * abs(self.key)
        step = (right - x0) / n
        nfg = self.note_color or fg
        p.setBrush(nfg)
        for ci, col in enumerate(self.columns):
            x = x0 + step * (ci + 0.5)
            acc_slot = 0
            for note in sorted(col):
                clef = staff_for(note)
                bottom = staves[clef]
                y = bottom - (note.diatonic - BOTTOM_LINE[clef]) * gap / 2
                steps = round((bottom - y) / (gap / 2))
                p.setPen(QPen(fg, engraving.ledger_width(font, gap=gap) if font else line))
                if steps < 0:
                    for s in range(-2, steps - 1, -2):
                        self._ledger(
                            p,
                            x=x,
                            y=bottom - s * gap / 2,
                            gap=gap,
                        )
                elif steps > 8:
                    for s in range(10, steps + 1, 2):
                        self._ledger(
                            p,
                            x=x,
                            y=bottom - s * gap / 2,
                            gap=gap,
                        )
                p.setPen(Qt.PenStyle.NoPen)
                value = self.value if len(col) == 1 else "whole"  # stems are only drawn for single notes
                self._note(
                    p,
                    x=x,
                    y=y,
                    gap=gap,
                    color=nfg,
                    value=value,
                    stem_down=steps >= 4,
                    font=font,
                )
                p.setPen(QPen(nfg, 1.4))
                # A sign is written only where the note differs from what the key signature already says.
                if note.accidental != key_accidental(note.letter, count=self.key):
                    ax = x - gap * (2.3 + 1.2 * (acc_slot % 3))
                    if font:
                        engraving.draw_accidental(
                            p,
                            font=font,
                            sign=note.accidental,
                            x=ax,
                            y=y,
                            gap=gap,
                            colour=nfg,
                        )
                    else:
                        sign = ACCIDENTAL_SYMBOLS[note.accidental] or "♮"
                        p.setFont(QFont("DejaVu Sans", int(gap * 2.0)))
                        p.drawText(QPointF(ax, y + gap * 0.5), sign)
                    acc_slot += 1

    def _draw_key_signature(
        self,
        p: QPainter,
        *,
        clef: str,
        x: float,
        bottom: float,
        gap: float,
        color: QColor,
        font: str | None = None,
    ) -> None:
        draw_key_signature(
            p,
            clef=clef,
            key=self.key,
            x=x,
            bottom=bottom,
            gap=gap,
            color=color,
            font=font,
        )

    @staticmethod
    def _note(
        p: QPainter,
        *,
        x: float,
        y: float,
        gap: float,
        color: QColor,
        value: str,
        stem_down: bool,
        font: str | None = None,
    ) -> None:
        """Draw a note of the given value; the head is centred on (x, y)."""
        if font and value != "breve":  # the breve is always the square form, whatever the music font
            engraving.draw_note(
                p,
                font=font,
                value=value,
                x=x,
                y=y,
                gap=gap,
                colour=color,
                stem_down=stem_down,
            )
        elif value == "whole":
            StaffWidget._whole_note(
                p,
                x=x,
                y=y,
                gap=gap,
                color=color,
            )
        else:
            draw_note(
                p,
                value=value,
                x=x,
                y=y,
                gap=gap,
                colour=color,
                stem_down=stem_down,
            )

    @staticmethod
    def _draw_clef(
        p: QPainter,
        *,
        clef: str,
        x: float,
        bottom: float,
        gap: float,
        color: QColor = QColor("black"),
        font: str | None = None,
    ) -> None:
        """Draw the clef: from a SMuFL font if given, else as a Noto Music path scaled to its extent in gaps."""
        clef = clef_shape(clef)  # the baritone clef is an F clef or a C clef, as chosen in the settings
        if font:
            engraving.draw_clef(
                p,
                font=font,
                clef=clef,
                x=x,
                bottom=bottom,
                gap=gap,
                colour=color,
            )
            return
        top, bot = CLEF_EXTENT[clef]
        path = QPainterPath()
        path.addText(
            0,
            0,
            QFont("Noto Music", 100),
            CLEF_GLYPH[clef],
        )
        r = path.boundingRect()
        scale = (top - bot) * gap / r.height()
        t = QTransform()
        t.translate(x, bottom - top * gap)
        t.scale(scale, scale)
        t.translate(-r.x(), -r.y())
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(t.map(path))
        p.restore()

    @staticmethod
    def _brace(
        p: QPainter,
        *,
        x: float,
        y0: float,
        y1: float,
        color: QColor,
        wd: float = 11.0,
        font: str | None = None,
    ) -> None:
        """A curly brace whose point faces left, spanning y0..y1 with its right edge at x: the music font's brace if
        it has one, else a drawn one."""
        if font and engraving.draw_brace(
            p,
            font=font,
            x=x,
            y0=y0,
            y1=y1,
            colour=color,
            width=wd * 1.25,
        ):
            return
        mid = (y0 + y1) / 2
        path = QPainterPath()
        path.moveTo(x, y0)
        path.cubicTo(
            x - wd,
            y0 + (mid - y0) * 0.25,
            x,
            mid - (mid - y0) * 0.35,
            x - wd,
            mid,
        )
        path.cubicTo(
            x,
            mid + (y1 - mid) * 0.35,
            x - wd,
            y1 - (y1 - mid) * 0.25,
            x,
            y1,
        )
        path.cubicTo(
            x - wd * 0.4,
            y1 - (y1 - mid) * 0.25,
            x - wd * 1.4,
            mid + (y1 - mid) * 0.3,
            x - wd * 1.4,
            mid,
        )
        path.cubicTo(
            x - wd * 1.4,
            mid - (mid - y0) * 0.3,
            x - wd * 0.4,
            y0 + (mid - y0) * 0.25,
            x,
            y0,
        )
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(path)
        p.restore()

    @staticmethod
    def _whole_note(
        p: QPainter,
        *,
        x: float,
        y: float,
        gap: float,
        color: QColor = QColor("black"),
    ) -> None:
        """Whole note: black oval with a tilted white hole."""
        outer = QPainterPath()
        outer.addEllipse(QPointF(0, 0), gap * 0.74, gap * 0.5)
        hole = QPainterPath()
        hole.addEllipse(QPointF(0, 0), gap * 0.38, gap * 0.42)
        t = QTransform()
        t.rotate(-35)
        shape = outer.subtracted(t.map(hole))  # transparent hole: staff line shows through
        p.save()
        p.translate(x, y)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(shape)
        p.restore()

    @staticmethod
    def _ledger(
        p: QPainter,
        *,
        x: float,
        y: float,
        gap: float,
    ) -> None:
        """Ledger line, a little wider than the note head (which is about 0.74 gap either side of centre)."""
        p.drawLine(QPointF(x - gap, y), QPointF(x + gap, y))
