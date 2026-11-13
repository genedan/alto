"""
The staff you click to place a note, for the note construction exercise.

Examples
--------
>>> staff = StaffInput()
>>> staff.accidental is None and not staff.locked
True
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEvent,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
)
from PySide6.QtWidgets import QWidget

from alto.settings import RANGE_LIMITS
from alto.theory.pitch import (
    Note,
    key_accidental,
)
from alto.ui.staff import (
    BOTTOM_LINE,
    MAX_STEP,
    MIDDLE_C,
    StaffWidget,
)

PREVIEW = QColor(
    53,
    132,
    228,
    170,
)  # the note that follows the pointer


class StaffInput(StaffWidget):
    """
    A single staff you click to place a note.

    The note snaps to the nearest line or space and follows the pointer until you click.

    Attributes
    ----------
    placed : Signal
        Emitted with the `Note` when you click, using the current `accidental`.
    accidental_cycled : Signal
        Emitted on a right click: the owner steps through natural, sharp and flat.
    accidental : int or None
        The sign you chose (-1 flat, 0 natural, 1 sharp); None follows the key signature.
    locked : bool
        Ignore the mouse (while feedback is showing).

    Examples
    --------
    >>> staff = StaffInput()
    >>> staff.reset("treble", key=0)
    >>> staff.resize(400, 300)
    >>> str(staff.note_at(staff.staff_bottoms()["treble"]))  # the bottom line of the treble staff
    'E4'
    """

    placed = Signal(object)
    accidental_cycled = Signal()  # right click: the owner steps through natural, sharp and flat

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create the staff.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the staff.

        Examples
        --------
        >>> StaffInput().hasMouseTracking()
        True
        """
        super().__init__(parent, max_step=MAX_STEP)
        self.accidental: int | None = None  # the sign you chose (-1 flat, 0 natural, +1 sharp); None follows the key signature
        self.locked = False  # ignore the mouse (while feedback is showing)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def reset(
        self,
        clef: str,
        *,
        key: int = 0,
    ) -> None:
        """
        Clear the staff for a new question, drawing a key signature.

        Parameters
        ----------
        clef : str
            The clef to draw.
        key : int, default 0
            The key signature: that many sharps if positive, flats if negative. Keyword-only.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.accidental, staff.locked = 1, True
        >>> staff.reset("bass", key=-2)
        >>> staff.accidental is None, staff.locked, staff.key
        (True, False, -2)
        """
        self.accidental, self.locked = None, False
        self.show_notes([], clef=clef, key=key)

    def note_at(self, y: float) -> Note:
        """
        Return the note on the line or space nearest to a height on the staff.

        The note is kept within five ledger lines of the staff. On a grand staff, a click in the upper half is on the treble
        staff and the lower half on the bass staff.

        Parameters
        ----------
        y : float
            The height in the widget, in pixels from the top.

        Returns
        -------
        Note
            The note, with the chosen accidental or, if none is chosen, the one the key signature gives it.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.reset("treble", key=1)  # G major: F is sharp
        >>> staff.resize(400, 300)
        >>> bottom = staff.staff_bottoms()["treble"]
        >>> str(staff.note_at(bottom - 3 * staff.GAP / 2))  # three steps above E4
        'A4'
        >>> str(staff.note_at(bottom - staff.GAP / 2))  # one step above E4: F, sharp in this key
        'F♯4'
        """
        gap, bottoms = self.GAP, self.staff_bottoms()
        low, high = RANGE_LIMITS[self.clef]
        if self.clef == "grand":
            # halfway between middle C as written on the treble staff and the B below it on the bass staff
            top_bottom, bass_bottom = bottoms["treble"], bottoms["bass"]
            c4 = top_bottom - (MIDDLE_C - BOTTOM_LINE["treble"]) * gap / 2
            b3 = bass_bottom - (MIDDLE_C - 1 - BOTTOM_LINE["bass"]) * gap / 2
            if y <= (c4 + b3) / 2:
                diatonic = max(BOTTOM_LINE["treble"] + round((top_bottom - y) / (gap / 2)), MIDDLE_C)
            else:
                diatonic = min(BOTTOM_LINE["bass"] + round((bass_bottom - y) / (gap / 2)), MIDDLE_C - 1)
        else:
            diatonic = BOTTOM_LINE[self.clef] + round((bottoms[self.clef] - y) / (gap / 2))
        diatonic = min(max(diatonic, low), high)
        accidental = self.accidental if self.accidental is not None else key_accidental(diatonic % 7, count=self.key)
        return Note.from_diatonic(diatonic, accidental=accidental)

    def show_note(
        self,
        note: Note | None,
        *,
        color: QColor | None = None,
    ) -> None:
        """
        Draw a single note on the staff, or clear it.

        Parameters
        ----------
        note : Note or None
            The note to draw; None clears the staff.
        color : QColor or None, default None
            The colour to draw it in; the notation's own ink if None. Keyword-only.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.show_note(Note.parse("C4"))
        >>> len(staff.columns)
        1
        >>> staff.show_note(None)
        >>> staff.columns
        []
        """
        self.columns = [[note]] if note else []
        self.note_color = QColor(color) if color else None
        self.update()

    def refresh_preview(self) -> None:
        """
        Redraw the pointer's note, for example after the accidental changes.

        Examples
        --------
        >>> StaffInput().refresh_preview()  # the pointer is not over the staff: nothing to redraw
        """
        if not self.locked and self.underMouse():
            self.show_note(self.note_at(self.mapFromGlobal(self.cursor().pos()).y()), color=PREVIEW)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Show the note under the pointer, in a lighter colour.

        Parameters
        ----------
        event : QMouseEvent
            The mouse move.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.reset("treble")
        >>> staff.resize(400, 300)
        >>> from PySide6.QtCore import QPointF
        >>> point = QPointF(50, staff.staff_bottoms()["treble"])
        >>> staff.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, point, point, Qt.MouseButton.NoButton,
        ...                                  Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        >>> str(staff.columns[0][0])
        'E4'
        """
        if not self.locked:
            self.show_note(self.note_at(event.position().y()), color=PREVIEW)

    def leaveEvent(self, event: QEvent) -> None:
        """
        Remove the pointer's note when the pointer leaves the staff.

        Parameters
        ----------
        event : QEvent
            The leave event.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.show_note(Note.parse("C4"))
        >>> staff.leaveEvent(QEvent(QEvent.Type.Leave))
        >>> staff.columns
        []
        """
        if not self.locked:
            self.show_note(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Place the note on a left click, or step through the accidentals on a right click.

        Parameters
        ----------
        event : QMouseEvent
            The mouse press. Nothing happens while the staff is locked.

        Examples
        --------
        >>> staff = StaffInput()
        >>> staff.reset("treble")
        >>> staff.resize(400, 300)
        >>> placed = []
        >>> _ = staff.placed.connect(placed.append)
        >>> from PySide6.QtCore import QPointF
        >>> point = QPointF(50, staff.staff_bottoms()["treble"])
        >>> staff.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, point, point, Qt.MouseButton.LeftButton,
        ...                                   Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        >>> [str(n) for n in placed]
        ['E4']
        """
        if event.button() == Qt.MouseButton.RightButton and not self.locked:
            self.accidental_cycled.emit()
        elif event.button() == Qt.MouseButton.LeftButton and not self.locked:
            note = self.note_at(event.position().y())
            self.show_note(note)  # solid black: the note you placed
            self.placed.emit(note)
