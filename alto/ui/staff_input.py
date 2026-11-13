from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent

from ..settings import RANGE_LIMITS
from ..theory.pitch import Note, key_accidental
from .staff import BOTTOM_LINE, MAX_STEP, MIDDLE_C, StaffWidget

PREVIEW = QColor(53, 132, 228, 170)  # the note that follows the pointer


class StaffInput(StaffWidget):
    """A single staff you click to place a note. The note snaps to the nearest line or space and follows the
    pointer until you click; `placed` is emitted with the Note, using the current `accidental`."""

    placed = Signal(object)
    accidental_cycled = Signal()  # right click: the owner steps through natural, sharp and flat

    def __init__(self, parent=None):
        super().__init__(parent, max_step=MAX_STEP)
        self.accidental: int | None = None  # the sign you chose (-1 flat, 0 natural, +1 sharp); None follows the key signature
        self.locked = False  # ignore the mouse (while feedback is showing)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def reset(self, clef: str, key: int = 0) -> None:
        """Clear the staff for a new question, drawing the key signature `key` (sharps +, flats -)."""
        self.accidental, self.locked = None, False
        self.show_notes([], clef, key)

    def note_at(self, y: float) -> Note:
        """The note on the line or space nearest to height `y`, within five ledger lines of the staff.
        On a grand staff, a click in the upper half is on the treble staff and the lower half on the bass staff."""
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
        accidental = self.accidental if self.accidental is not None else key_accidental(diatonic % 7, self.key)
        return Note.from_diatonic(diatonic, accidental)

    def show_note(self, note: Note | None, color: QColor | None = None) -> None:
        self.columns = [[note]] if note else []
        self.note_color = QColor(color) if color else None
        self.update()

    def refresh_preview(self) -> None:
        """Redraw the pointer's note, e.g. after the accidental changes."""
        if not self.locked and self.underMouse():
            self.show_note(self.note_at(self.mapFromGlobal(self.cursor().pos()).y()), PREVIEW)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.locked:
            self.show_note(self.note_at(event.position().y()), PREVIEW)

    def leaveEvent(self, event) -> None:
        if not self.locked:
            self.show_note(None)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton and not self.locked:
            self.accidental_cycled.emit()
        elif event.button() == Qt.MouseButton.LeftButton and not self.locked:
            note = self.note_at(event.position().y())
            self.show_note(note)  # solid black: the note you placed
            self.placed.emit(note)
