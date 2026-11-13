"""
The clefs.

The seven clefs with one staff (treble, bass, and the C clefs from soprano to baritone), how they are grouped on the
settings pages, and that every exercise with a clef setting works on each of them.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Any

import pytest
from alto import settings
from alto.exercises.library import ARPEGGIO_WINDOWS, ArpeggioNames, KeySignatures, NoteConstruction, NoteNames
from alto.theory.pitch import Note
from alto.ui import settings_panel as sp
from alto.ui.pictures import CLEF_NAMES

# noinspection PyProtectedMember
from alto.ui.staff import _KEY_POSITIONS, BOTTOM_LINE, MIDDLE_C, StaffWidget
from PySide6.QtWidgets import QApplication, QCheckBox

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

    from PySide6.QtWidgets import QWidget

NEW = ("soprano", "mezzo", "baritone")


def test_each_c_clef_puts_middle_c_on_its_own_line() -> None:
    """
    Check that each c clef puts middle c on its own line.
    """
    lines_up = {
        "soprano": 0,
        "mezzo": 1,
        "alto": 2,
        "tenor": 3,
        "baritone": 4,
    }  # lines above the bottom one
    for clef, lines in lines_up.items():
        assert MIDDLE_C - BOTTOM_LINE[clef] == 2 * lines, clef


def test_the_clefs_are_grouped_into_the_grand_staff_the_everyday_clefs_and_the_rest() -> None:
    """
    Check that the clefs are grouped into the grand staff the everyday clefs and the rest.
    """
    assert settings.CLEF_GROUPS == (
        ("grand",),
        (
            "treble",
            "bass",
            "alto",
            "tenor",
        ),
        ("soprano", "mezzo", "baritone"),
    )
    assert sorted(c for g in settings.CLEF_GROUPS for c in g) == sorted(settings.RANGE_KEYS)  # each clef in one group
    for clef in settings.RANGE_KEYS:
        assert clef in CLEF_NAMES and clef in settings.DEFAULT_RANGES and clef in settings.RANGE_LIMITS


def test_the_default_ranges_sit_inside_the_limits_and_span_two_octaves() -> None:
    """
    Check that the default ranges sit inside the limits and span two octaves.
    """
    for clef in NEW:
        lo, hi = settings.DEFAULT_RANGES[clef]
        limit_lo, limit_hi = settings.RANGE_LIMITS[clef]
        assert limit_lo <= lo < hi <= limit_hi and hi - lo == 14
        assert lo == BOTTOM_LINE[clef] - 3  # the same place relative to the staff as the alto and tenor ranges
    assert settings.DEFAULT_RANGES["alto"][0] == BOTTOM_LINE["alto"] - 3


def test_key_signatures_keep_their_usual_places_on_the_four_older_clefs() -> None:
    """
    Check that key signatures keep their usual places on the four older clefs.
    """
    assert _KEY_POSITIONS[("treble", 1)] == "F5 C5 G5 D5 A4 E5 B4" and _KEY_POSITIONS[("treble", -1)] == "B4 E5 A4 D5 G4 C5 F4"
    assert _KEY_POSITIONS[("bass", 1)] == "F3 C3 G3 D3 A2 E3 B2" and _KEY_POSITIONS[("bass", -1)] == "B2 E3 A2 D3 G2 C3 F2"
    assert _KEY_POSITIONS[("alto", 1)] == "F4 C4 G4 D4 A3 E4 B3" and _KEY_POSITIONS[("alto", -1)] == "B3 E4 A3 D4 G3 C4 F3"
    assert _KEY_POSITIONS[("tenor", 1)] == "F3 C4 G3 D4 A3 E4 B3" and _KEY_POSITIONS[("tenor", -1)] == "B3 E4 A3 D4 G3 C4 F3"


@pytest.mark.parametrize("clef", settings.CLEFS)
def test_every_signature_sits_on_the_staff_in_every_clef(clef: str) -> None:
    """
    Check that every signature sits on the staff in every clef.

    Parameters
    ----------
    clef : str
        The clef under test.
    """
    for sign, order in ((1, "FCGDAEB"), (-1, "BEADGCF")):
        notes = [Note.parse(n) for n in _KEY_POSITIONS[(clef, sign)].split()]
        assert "".join(n.name for n in notes) == order  # the usual order of sharps and of flats
        assert all(BOTTOM_LINE[clef] - 1 <= n.diatonic <= BOTTOM_LINE[clef] + 9 for n in notes)  # no ledger lines
        assert len({n.diatonic for n in notes}) == 7


@pytest.mark.parametrize("clef", settings.CLEFS)
def test_a_staff_with_notes_and_a_key_signature_draws_in_every_clef(
    app: QApplication,
    clef: str,
) -> None:
    """
    Check that a staff with notes and a key signature draws in every clef.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    clef : str
        The clef under test.
    """
    staff = StaffWidget()
    staff.resize(500, 300)
    low = Note.from_diatonic(BOTTOM_LINE[clef])
    staff.show_notes([[low], [Note.from_diatonic(BOTTOM_LINE[clef] + 8)]], clef=clef, key=-3)
    assert staff.grab().width() == 500
    assert staff.staff_bottoms().keys() == {clef}


@pytest.mark.parametrize("clef", NEW)
def test_the_exercises_ask_on_the_new_clefs(clef: str) -> None:
    """
    Check that the exercises ask on the new clefs.

    Parameters
    ----------
    clef : str
        The clef under test.
    """
    rng = random.Random(4)
    cfg = settings.note_names
    cfg.clefs = {clef}
    lo, hi = cfg.range_for(clef)
    for _ in range(60):
        q = NoteNames().generate(rng)
        assert q.clef == clef and lo <= q.staff[0][0].diatonic <= hi
    settings.construction.clefs = {clef}
    assert all(NoteConstruction().generate(rng).clef == clef for _ in range(40))
    settings.arpeggio.clefs = {clef}
    low, high = (n.diatonic for n in ARPEGGIO_WINDOWS[clef])
    for _ in range(80):
        q = ArpeggioNames().generate(rng)
        assert q.clef == clef and low <= q.staff[0][0].diatonic and q.staff[-1][0].diatonic <= high
    settings.key_signatures.clefs, settings.key_signatures.questions = {clef}, {"read"}
    assert all(KeySignatures().generate(rng).clef == clef for _ in range(40))


def test_the_arpeggio_windows_sit_the_same_way_on_every_clef_but_the_treble() -> None:
    """
    Check that the arpeggio windows sit the same way on every clef but the treble.
    """
    for clef in (
        *NEW,
        "bass",
        "alto",
        "tenor",
    ):
        lo, hi = ARPEGGIO_WINDOWS[clef]
        assert (lo.diatonic - BOTTOM_LINE[clef], hi.diatonic - BOTTOM_LINE[clef]) == (-4, 12), clef


@pytest.mark.parametrize(
    "panel_class, config, expect_grand",
    [
        (sp.NoteNameSettingsPanel, settings.note_names, True),
        (sp.NoteConstructionSettingsPanel, settings.construction, True),
        (sp.ArpeggioSettingsPanel, settings.arpeggio, False),
        (sp.KeySignatureSettingsPanel, settings.key_signatures, False),
    ],
)
def test_the_clef_pages_list_the_clefs_one_under_another_with_their_names(
    app: QApplication,
    panel_class: Callable[[Any], Any],
    config: object,
    expect_grand: bool,
) -> None:
    """
    Check that the clef pages list the clefs one under another with their names.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    panel_class : Callable[[Any], Any]
        The settings panel class.
    config : object
        The settings the panel edits.
    expect_grand : bool
        Whether a grand staff is expected.
    """
    panel = panel_class(config)
    panel.resize(272, 800)
    panel.show()
    page = next(iter(panel.boxes.values()))
    while page.parentWidget() is not panel.stack:  # the page of the settings that the clefs are on
        page = page.parentWidget()
    panel._go(panel.stack.indexOf(page))
    deadline = time.monotonic() + 1.0
    while panel.stack.sliding and time.monotonic() < deadline:
        QApplication.processEvents()
    QApplication.processEvents()
    boxes = panel.boxes
    assert set(boxes) == set(settings.RANGE_KEYS if expect_grand else settings.CLEFS)
    assert all(isinstance(b, QCheckBox) and b.text() == CLEF_NAMES[c] for c, b in boxes.items())
    order = [c for g in settings.CLEF_GROUPS for c in g if c in boxes]
    ys = [boxes[c].mapTo(panel, boxes[c].rect().topLeft()).y() for c in order]
    xs = {boxes[c].mapTo(panel, boxes[c].rect().topLeft()).x() for c in order}
    assert ys == sorted(ys) and len(set(ys)) == len(ys) and len(xs) == 1  # a single column, in group order
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    assert max(gaps) > min(gaps)  # a larger gap where one group ends and the next begins
    assert ("grand" in boxes) == expect_grand and not hasattr(panel, "single")  # no "Single clef" switch


@pytest.fixture
def baritone() -> Iterator[ModuleType]:
    """
    Put the baritone clef's style back to the default after the test.

    Yields
    ------
    ModuleType
        The notation module; the default baritone clef is put back afterwards.
    """
    from alto.ui import notation

    yield notation
    notation.set_baritone_clef(notation.DEFAULT_BARITONE)


def _ink(widget: QWidget) -> bytes:
    """
    Return the raw pixels a widget draws.

    Parameters
    ----------
    widget : QWidget
        The widget.

    Returns
    -------
    bytes
        The image data.
    """
    image = widget.grab().toImage()
    return bytes(image.constBits())


def test_the_baritone_clef_is_an_f_clef_unless_the_c_clef_is_chosen(
    app: QApplication,
    baritone: ModuleType,
) -> None:
    """
    Check that the baritone clef is an f clef unless the c clef is chosen.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    baritone : ModuleType
        The notation module, with the baritone clef style restored afterwards.
    """
    assert baritone.DEFAULT_BARITONE == "f" and baritone.baritone_clef() == "f"
    assert baritone.clef_shape("baritone") == "baritone_f" and baritone.clef_shape("alto") == "alto"
    staff = StaffWidget()
    staff.resize(400, 300)
    staff.show_notes([[Note(3, letter=3)]], clef="baritone", key=0)
    as_f = _ink(staff)
    baritone.set_baritone_clef("c")
    assert baritone.clef_shape("baritone") == "baritone_c"
    assert _ink(staff) != as_f  # a staff already on screen is redrawn with the other clef
    baritone.set_baritone_clef("f")
    assert _ink(staff) == as_f
    baritone.set_baritone_clef("sideways")  # not a choice: back to the default
    assert baritone.baritone_clef() == "f"


def test_the_baritone_clef_choice_is_saved_and_read_back(baritone: ModuleType) -> None:
    """
    Check that the baritone clef choice is saved and read back.

    Parameters
    ----------
    baritone : ModuleType
        The notation module, with the baritone clef style restored afterwards.
    """
    from alto.ui.store import store

    baritone.set_baritone_clef("c")
    assert store().value("ui/baritoneClef") == "c"
    baritone.set_baritone_clef("f")
    baritone.load_style()
    assert baritone.baritone_clef() == "f"
    store().setValue("ui/baritoneClef", "c")
    baritone.load_style()
    assert baritone.baritone_clef() == "c"
    store().setValue("ui/baritoneClef", "nonsense")
    baritone.load_style()
    assert baritone.baritone_clef() == "f"


@pytest.mark.parametrize("font", ["finalemaestro", "noto"])
def test_both_baritone_clefs_draw_in_a_music_font_and_in_the_built_in_one(
    app: QApplication,
    baritone: ModuleType,
    font: object,
) -> None:
    """
    Check that both baritone clefs draw in a music font and in the built in one.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    baritone : ModuleType
        The notation module, with the baritone clef style restored afterwards.
    font : object
        A value supplied by the parametrisation.
    """
    baritone.set_style(font)
    try:
        for kind in ("f", "c"):
            baritone.set_baritone_clef(kind)
            staff = StaffWidget()
            staff.resize(400, 300)
            staff.show_notes([[Note(3, letter=3)]], clef="baritone", key=-2)
            assert staff.grab().width() == 400
    finally:
        baritone.set_style("finalemaestro")


def test_the_settings_dialog_offers_both_ways_of_writing_the_baritone_clef(
    app: QApplication,
    baritone: ModuleType,
) -> None:
    """
    Check that the settings dialog offers both ways of writing the baritone clef.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    baritone : ModuleType
        The notation module, with the baritone clef style restored afterwards.
    """
    from alto.ui.app_settings import AppSettingsDialog

    dialog = AppSettingsDialog()
    buttons = dialog.baritone_buttons
    assert set(buttons) == {"f", "c"} and buttons["f"].isChecked() and not buttons["c"].isChecked()
    buttons["c"].click()
    assert baritone.baritone_clef() == "c"
    buttons["f"].click()
    assert baritone.baritone_clef() == "f"
    dialog.choose_theme("light")  # unrelated pages still work
