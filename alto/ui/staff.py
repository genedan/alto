"""
The staff: lines, clefs, key signatures and notes, drawn on a rounded white "paper".

`StaffWidget` draws one staff, or a grand staff with a brace, in any of the seven clefs. Notes and key signatures are
placed by their staff step (`Note.diatonic`) measured from the bottom line of the clef, and are engraved in the notation
font chosen in the settings.

Examples
--------
>>> key_signature_positions("treble", sign=1)
['F5', 'C5', 'G5', 'D5', 'A4', 'E5', 'B4']
>>> staff = StaffWidget()
>>> staff.show_notes([[Note.parse("C4")]], clef="treble", key=2)
>>> staff.clef, staff.key
('treble', 2)
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPaintEvent, QPen, QTransform
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
    """
    Return the notes the sharps or flats of a key signature are written on, in a clef.

    Each accidental is a fourth up or a fifth down from the one before (sharps: F C G D A E B, flats: B E A D G C F), and the
    pattern is chosen so that all seven stay on the staff, or one step above or below it. This gives the usual signatures for
    the treble, bass, alto and tenor clefs, and works out the rest.

    Parameters
    ----------
    clef : str
        A key of `BOTTOM_LINE`.
    sign : int
        1 for sharps, -1 for flats. Keyword-only.

    Returns
    -------
    list of str
        Seven note names with octaves, in the order the accidentals appear.

    Raises
    ------
    ValueError
        If no placement keeps all seven accidentals on the staff.

    Examples
    --------
    >>> key_signature_positions("treble", sign=1)
    ['F5', 'C5', 'G5', 'D5', 'A4', 'E5', 'B4']
    >>> key_signature_positions("bass", sign=-1)
    ['B2', 'E3', 'A2', 'D3', 'G2', 'C3', 'F2']
    """
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
    """
    Draw the sharps or flats of a key signature, left to right.

    Parameters
    ----------
    p : QPainter
        The painter to draw with.
    clef : str
        The clef, which decides where on the staff each accidental goes. Keyword-only.
    key : int
        The key signature: that many sharps if positive, flats if negative; nothing is drawn for 0. Keyword-only.
    x : float
        The left edge of the first accidental, in pixels. Keyword-only.
    bottom : float
        The y position of the staff's bottom line, in pixels. Keyword-only.
    gap : float
        The distance between staff lines, in pixels. Keyword-only.
    color : QColor
        The colour to draw in. Keyword-only.
    step : float, default KEY_STEP
        The horizontal spacing between accidentals. Keyword-only.
    size : float, default 2.0
        The size of the built-in characters, in staff gaps. Keyword-only.
    font : str or None, default None
        A SMuFL font to engrave them in; None uses the built-in sharp and flat characters. Keyword-only.

    Examples
    --------
    >>> from PySide6.QtGui import QImage
    >>> image = QImage(200, 120, QImage.Format.Format_ARGB32)
    >>> image.fill(QColor("white"))
    >>> painter = QPainter(image)
    >>> draw_key_signature(painter, clef="treble", key=3, x=10, bottom=80, gap=12, color=QColor("black"), font="bravura")
    >>> painter.end()
    True
    >>> any(image.pixelColor(x, y).lightness() < 128 for x in range(10, 60) for y in range(20, 100))
    True
    """
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
    """
    A staff with notes, a clef, a key signature and, optionally, a caption.

    Attributes
    ----------
    GAP : float
        The distance between staff lines, in pixels.
    side : float
        The space at the left and right edges.
    note_offset : float
        Where the notes start, from the left edge.
    margin : float
        The space kept above and below the staff for ledger lines, in gaps.
    compact : bool
        Size the widget to fit instead of the 220 px default.
    max_step : float or None
        The most width each column of notes may take.
    clef : str
        The clef being drawn ("treble", "bass", "alto", "tenor", "soprano", "mezzo", "baritone" or "grand").
    columns : list of list of Note
        The notes drawn; each inner list is one chord or note.
    note_color : QColor or None
        The colour of the notes; None draws them in the notation style's ink.
    notation_style : NotationStyle or None
        A style to use instead of the one chosen in the settings.
    key : int
        The key signature drawn: sharps if positive, flats if negative.
    value : str
        The note value drawn.
    caption : str
        Text written under the staff, inside the paper.

    Examples
    --------
    >>> staff = StaffWidget()
    >>> staff.show_notes([[Note.parse("E4")], [Note.parse("G4")]], clef="treble")
    >>> len(staff.columns)
    2
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        gap: float = 16.0,
        side: float = 20.0,
        note_offset: float = 100.0,
        margin: float = 8.0,
        compact: bool = False,
        max_step: float | None = None,
    ) -> None:
        """
        Create an empty treble staff.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the staff.
        gap : float, default 16.0
            The distance between staff lines, in pixels. Keyword-only.
        side : float, default 20.0
            The space at the left and right edges. Keyword-only.
        note_offset : float, default 100.0
            Where the notes start, from the left edge. Keyword-only.
        margin : float, default 8.0
            The space kept above and below the staff for ledger lines, in gaps. Keyword-only.
        compact : bool, default False
            Size the widget to fit instead of the 220 px default. Keyword-only.
        max_step : float or None, default None
            The most width each column of notes may take: the staff then stops growing once its notes would be spread wider than
            that, so a few notes stay easy to read in a wide window. Keyword-only.

        Examples
        --------
        >>> StaffWidget(gap=8.0, compact=True).GAP
        8.0
        """
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
        """
        Show some notes, with a clef and a key signature.

        Parameters
        ----------
        columns : list of list of Note
            The notes: each inner list is one note or chord, drawn left to right.
        clef : str, default "treble"
            The clef, or "grand" for a grand staff. Keyword-only.
        key : int, default 0
            The key signature: that many sharps if positive, flats if negative. Keyword-only.
        value : str, default "whole"
            The note value to draw (stems are only drawn for single notes). Keyword-only.
        caption : str, default ""
            Text to write under the staff. Keyword-only.

        Examples
        --------
        >>> staff = StaffWidget()
        >>> staff.show_notes([[Note.parse("C4")]], clef="bass", key=-1, value="quarter", caption="_ Major")
        >>> staff.clef, staff.key, staff.value, staff.caption
        ('bass', -1, 'quarter', '_ Major')
        """
        self.columns, self.clef, self.key, self.value, self.caption = columns, clef, key, value, caption
        self.note_color = None
        self._fit_height(clef)
        self._fit_width()
        self.update()

    def _fit_width(self) -> None:
        """
        Cap the width so that no column of notes is spread wider than `max_step`.

        Examples
        --------
        >>> staff = StaffWidget(max_step=120.0)
        >>> staff.show_notes([[Note.parse("C4")]])
        >>> staff.maximumWidth()  # room for the clef and at least three columns of notes
        500
        """
        if self.max_step is None:
            return
        left = self.side + (18.0 if self.clef == "grand" else 0.0)  # the same left edge the drawing uses
        columns = max(len(self.columns), MIN_COLUMNS)
        self.setMaximumWidth(round(left + self.note_offset + KEY_STEP * abs(self.key) + columns * self.max_step + self.side))

    def sizeHint(self) -> QSize:
        """
        Return the size the staff would like.

        A capped staff asks for its full capped width, so a layout that centres it gives it that much.

        Returns
        -------
        QSize
            The capped width and the minimum height for a staff with a `max_step`; otherwise Qt's default.

        Examples
        --------
        >>> staff = StaffWidget(max_step=120.0)
        >>> staff.show_notes([[Note.parse("C4")]])
        >>> staff.sizeHint().width()
        500
        """
        if self.max_step is None:
            return super().sizeHint()
        return QSize(self.maximumWidth(), self.minimumHeight())

    def _fit_height(self, clef: str) -> None:
        """
        Set the height the staff needs for its clef.

        Parameters
        ----------
        clef : str
            "grand" needs room for two staves; any other clef for one.

        Examples
        --------
        >>> staff = StaffWidget()
        >>> staff.minimumHeight()
        330
        >>> staff._fit_height("grand")
        >>> staff.minimumHeight()
        450
        """
        grand_height = 2 * self.margin + 8 + GRAND_BETWEEN  # in gaps
        if self.compact:
            self.setFixedHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP))
        else:
            self.setMinimumHeight(int((grand_height if clef == "grand" else 4 + 2 * self.margin) * self.GAP) + 10)

    def set_note_color(self, color: QColor | None) -> None:
        """
        Draw the notes in a colour, for feedback, or back in the style's ink.

        Parameters
        ----------
        color : QColor or None
            The colour; None to use the notation style's ink.

        Examples
        --------
        >>> staff = StaffWidget()
        >>> staff.set_note_color(QColor("#2e7d32"))
        >>> staff.note_color.name()
        '#2e7d32'
        >>> staff.set_note_color(None)
        >>> staff.note_color is None
        True
        """
        self.note_color = QColor(color) if color is not None else None
        self.update()

    def staff_bottoms(self) -> dict[str, float]:
        """
        Return where each staff is drawn.

        Returns
        -------
        dict of str to float
            Clef name to the y position of that staff's bottom line, in pixels. A grand staff has a "treble" and a "bass".

        Examples
        --------
        >>> staff = StaffWidget()
        >>> staff.resize(400, 400)
        >>> staff.staff_bottoms()
        {'treble': 232.0}
        """
        gap, h = self.GAP, self.height()
        if self.clef == "grand":
            top = (h - (2 * self.margin + 8 + GRAND_BETWEEN) * gap) / 2 + self.margin * gap
            return {"treble": top + 4 * gap, "bass": top + (8 + GRAND_BETWEEN) * gap}
        return {self.clef: h / 2 + 2 * gap}

    def paintEvent(self, _: QPaintEvent) -> None:
        """
        Draw the paper, the staff lines, the clef, the key signature, the notes and the caption.

        Parameters
        ----------
        _ : QPaintEvent
            The paint request; the whole widget is always redrawn.

        Examples
        --------
        >>> staff = StaffWidget()
        >>> staff.resize(400, 400)
        >>> staff.show_notes([[Note.parse("C4")]], clef="treble")
        >>> staff.grab().toImage().pixelColor(200, 5).name()  # the white paper
        '#ffffff'
        """
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
            """
            Return which staff a note is on.

            Parameters
            ----------
            note : Note
                The note to place.

            Returns
            -------
            str
                The staff's clef name. On a grand staff, middle C and above are on the treble staff, the rest on the bass staff.

            Examples
            --------
            >>> staff_for(Note.parse("C4"))  # doctest: +SKIP
            'treble'
            """
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
        """
        Draw this staff's key signature.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        clef : str
            The clef of the staff. Keyword-only.
        x : float
            The left edge of the first accidental, in pixels. Keyword-only.
        bottom : float
            The y position of the staff's bottom line. Keyword-only.
        gap : float
            The distance between staff lines. Keyword-only.
        color : QColor
            The colour to draw in. Keyword-only.
        font : str or None, default None
            A SMuFL font to engrave with. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> staff = StaffWidget()
        >>> staff.show_notes([], key=2)
        >>> image = QImage(200, 120, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> staff._draw_key_signature(painter, clef="treble", x=10, bottom=80, gap=12, color=QColor("black"))
        >>> painter.end()
        True
        """
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
        """
        Draw a note of a value with its head centred on a point.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The head's centre, in pixels. Keyword-only.
        y : float
            The head's centre, in pixels. Keyword-only.
        gap : float
            The distance between staff lines, in pixels. Keyword-only.
        color : QColor
            The colour to draw in. Keyword-only.
        value : str
            The note value. Keyword-only.
        stem_down : bool
            Draw the stem down. Keyword-only.
        font : str or None, default None
            A SMuFL font to engrave with; None uses the built-in Noto Music drawing. The breve is always the square form.
            Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> StaffWidget._note(painter, x=50, y=50, gap=16, color=QColor("black"), value="quarter", stem_down=False)
        >>> painter.end()
        True
        >>> image.pixelColor(50, 50).lightness() < 128
        True
        """
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
        """
        Draw a clef.

        From a SMuFL font if one is given, else as a Noto Music path scaled to its extent in gaps. The baritone clef is drawn as
        an F clef or a C clef, whichever is chosen in the settings.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        clef : str
            The clef's name. Keyword-only.
        x : float
            The clef's left edge, in pixels. Keyword-only.
        bottom : float
            The y position of the staff's bottom line, in pixels. Keyword-only.
        gap : float
            The distance between staff lines, in pixels. Keyword-only.
        color : QColor, default black
            The colour to draw in. Keyword-only.
        font : str or None, default None
            A SMuFL font to engrave with. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> StaffWidget._draw_clef(painter, clef="treble", x=10, bottom=70, gap=10)
        >>> painter.end()
        True
        >>> any(image.pixelColor(x, y).lightness() < 128 for x in range(10, 40) for y in range(20, 90))
        True
        """
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
        """
        Draw a curly brace whose point faces left, for a grand staff.

        The music font's brace if it has one, else a drawn one.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The brace's right edge, in pixels. Keyword-only.
        y0 : float
            The top, in pixels. Keyword-only.
        y1 : float
            The bottom, in pixels. Keyword-only.
        color : QColor
            The colour to draw in. Keyword-only.
        wd : float, default 11.0
            How wide to draw it, in pixels. Keyword-only.
        font : str or None, default None
            A SMuFL font to take the brace from. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> StaffWidget._brace(painter, x=40, y0=10, y1=90, color=QColor("black"))
        >>> painter.end()
        True
        >>> any(image.pixelColor(x, 50).lightness() < 128 for x in range(20, 41))
        True
        """
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
        """
        Draw a whole note: a black oval with a tilted hole that the staff line shows through.

        Parameters
        ----------
        p : QPainter
            The painter to draw with.
        x : float
            The head's centre, in pixels. Keyword-only.
        y : float
            The head's centre, in pixels. Keyword-only.
        gap : float
            The distance between staff lines, which sets the size. Keyword-only.
        color : QColor, default black
            The colour to draw in. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(100, 100, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> StaffWidget._whole_note(painter, x=50, y=50, gap=20)
        >>> painter.end()
        True
        >>> image.pixelColor(62, 50).lightness() < 128  # the ring is dark ...
        True
        >>> image.pixelColor(50, 50).lightness() > 200  # ... and the hole is clear
        True
        """
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
        """
        Draw a ledger line, a little wider than the note head (which is about 0.74 gap either side of centre).

        Parameters
        ----------
        p : QPainter
            The painter to draw with, with its pen already set.
        x : float
            The centre of the line, in pixels. Keyword-only.
        y : float
            The line's height, in pixels. Keyword-only.
        gap : float
            The distance between staff lines; the line reaches one gap either side of `x`. Keyword-only.

        Examples
        --------
        >>> from PySide6.QtGui import QImage
        >>> image = QImage(100, 40, QImage.Format.Format_ARGB32)
        >>> image.fill(QColor("white"))
        >>> painter = QPainter(image)
        >>> painter.setPen(QColor("black"))
        >>> StaffWidget._ledger(painter, x=50, y=20, gap=16)
        >>> painter.end()
        True
        >>> image.pixelColor(40, 20).lightness() < 128
        True
        """
        p.drawLine(QPointF(x - gap, y), QPointF(x + gap, y))
