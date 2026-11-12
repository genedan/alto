import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from alto.theory.pitch import Note
from alto.ui.staff import BOTTOM_LINE
from alto.ui.staff_input import StaffInput


def y_of(staff: StaffInput, clef: str, diatonic: int) -> float:
    return staff.staff_bottoms()[clef] - (diatonic - BOTTOM_LINE[clef]) * staff.GAP / 2


def test_click_gives_the_note_the_key_signature_implies(app):
    staff = StaffInput()
    staff.resize(600, 300)
    f4 = Note(4, 3).diatonic

    staff.reset("treble", 2)  # D major: F and C are sharp
    assert staff.note_at(y_of(staff, "treble", f4)) == Note(4, 3, 1)          # F -> F sharp, no sign needed
    assert staff.note_at(y_of(staff, "treble", f4 + 1)) == Note(4, 4, 0)      # G is untouched
    staff.accidental = 0                                                      # an explicit natural cancels the key
    assert staff.note_at(y_of(staff, "treble", f4)) == Note(4, 3, 0)
    staff.accidental = -1
    assert staff.note_at(y_of(staff, "treble", f4)) == Note(4, 3, -1)

    staff.reset("treble", -3)  # E-flat major: B, E and A are flat
    assert staff.note_at(y_of(staff, "treble", Note(4, 2).diatonic)) == Note(4, 2, -1)
    staff.reset("treble", 0)
    assert staff.note_at(y_of(staff, "treble", f4)) == Note(4, 3, 0)          # no signature: a plain note


def test_reset_clears_the_sign_and_unlocks(app):
    staff = StaffInput()
    staff.accidental, staff.locked = 1, True
    staff.reset("bass", -1)
    assert staff.accidental is None and not staff.locked and staff.key == -1 and staff.clef == "bass"


def test_every_staff_draws_clefs_notes_and_key_signatures(app):
    """Painting touches clefs, key signatures and every note value, so a missing helper fails here."""
    from alto.settings import NOTE_VALUES
    from PySide6.QtGui import QPixmap

    for clef in ("treble", "bass", "alto", "tenor", "grand"):
        for value in NOTE_VALUES:
            staff = StaffInput()
            staff.resize(500, 360)
            staff.show_notes([[Note(4, 0)]], clef, 3, value)
            image = QPixmap(staff.size())
            staff.render(image)
            assert not image.isNull()
