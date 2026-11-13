"""The clickable staff: where the notes go and how a click turns into a note."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QPixmap

from alto.settings import NOTE_VALUES
from alto.theory.pitch import Note
from alto.ui.staff import BOTTOM_LINE
from alto.ui.staff_input import StaffInput

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def y_of(
    staff: StaffInput,
    *,
    clef: str,
    diatonic: int,
) -> float:
    """
    Find the height of a note on the clickable staff.

    Parameters
    ----------
    staff : StaffInput
        The staff.
    clef : str
        The clef.
    diatonic : int
        The note's diatonic number.

    Returns
    -------
    float
        The y position of the note.
    """
    return staff.staff_bottoms()[clef] - (diatonic - BOTTOM_LINE[clef]) * staff.GAP / 2


def test_click_gives_the_note_the_key_signature_implies(app: QApplication) -> None:
    """
    Check that click gives the note the key signature implies.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    staff = StaffInput()
    staff.resize(600, 300)
    f4 = Note(4, letter=3).diatonic

    staff.reset("treble", key=2)  # D major: F and C are sharp
    assert staff.note_at(y_of(staff, clef="treble", diatonic=f4)) == Note(
        4,
        letter=3,
        accidental=1,
    )  # F -> F sharp, no sign needed
    assert staff.note_at(y_of(staff, clef="treble", diatonic=f4 + 1)) == Note(4, letter=4, accidental=0)  # G is untouched
    staff.accidental = 0  # an explicit natural cancels the key
    assert staff.note_at(y_of(staff, clef="treble", diatonic=f4)) == Note(4, letter=3, accidental=0)
    staff.accidental = -1
    assert staff.note_at(y_of(staff, clef="treble", diatonic=f4)) == Note(4, letter=3, accidental=-1)

    staff.reset("treble", key=-3)  # E-flat major: B, E and A are flat
    assert staff.note_at(y_of(staff, clef="treble", diatonic=Note(4, letter=2).diatonic)) == Note(4, letter=2, accidental=-1)
    staff.reset("treble", key=0)
    assert staff.note_at(y_of(staff, clef="treble", diatonic=f4)) == Note(4, letter=3, accidental=0)  # no signature: a plain note


def test_reset_clears_the_sign_and_unlocks(app: QApplication) -> None:
    """
    Check that reset clears the sign and unlocks.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    staff = StaffInput()
    staff.accidental, staff.locked = 1, True
    staff.reset("bass", key=-1)
    assert staff.accidental is None and not staff.locked and staff.key == -1 and staff.clef == "bass"


def test_every_staff_draws_clefs_notes_and_key_signatures(app: QApplication) -> None:
    """
    Painting touches clefs, key signatures and every note value, so a missing helper fails here.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    for clef in (
        "treble",
        "bass",
        "alto",
        "tenor",
        "grand",
    ):
        for value in NOTE_VALUES:
            staff = StaffInput()
            staff.resize(500, 360)
            staff.show_notes(
                [[Note(4, letter=0)]],
                clef=clef,
                key=3,
                value=value,
            )
            image = QPixmap(staff.size())
            staff.render(image)
            assert not image.isNull()
