"""The exercise settings panes: the menus, the pages behind them, and the settings they save and load."""
import pytest
from alto import settings
from alto.ui import settings_panel as sp
from alto.ui.store import store
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QToolButton


def slide():
    QTest.qWait(300)  # a page slides in over about 220 ms


def back(panel):
    next(b for b in panel.findChildren(QToolButton) if b.text() == "‹ Back").click()
    slide()


# -- saving and loading ---------------------------------------------------------------------------------------------


def test_the_note_name_settings_are_saved_and_read_back():
    cfg = settings.note_names
    cfg.clefs, cfg.key_signatures = {"grand", "alto", "baritone"}, {-2, 0, 5}
    cfg.note_values, cfg.naming, cfg.accidentals = {"half", "eighth"}, "solfege", True
    cfg.ranges = {"treble": (30, 40), "bass": (15, 25)}
    sp.save_note_names()
    cfg.__init__()  # back to the defaults
    sp.load_note_names()
    assert (cfg.clefs, cfg.key_signatures) == ({"grand", "alto", "baritone"}, {-2, 0, 5})
    assert cfg.note_values == {"half", "eighth"} and cfg.naming == "solfege" and cfg.accidentals
    assert cfg.ranges == {"treble": (30, 40), "bass": (15, 25)}


def test_bad_saved_note_name_settings_fall_back_to_sensible_ones():
    s = store()
    s.setValue("noteNames/clefs", ["treble", "tenor", "sideways"])  # QSettings may give a list back
    s.setValue("noteNames/keys", "99,abc,-9")  # none of them is a real key
    s.setValue("noteNames/values", "zigzag")
    s.setValue("noteNames/naming", "klingon")
    s.setValue("noteNames/ranges", "treble:5-3,bass:oops,nonsense:20-30,alto:20-30,tenor:20,grand:1-2000000")
    settings.note_names.__init__()
    sp.load_note_names()
    cfg = settings.note_names
    assert cfg.clefs == {"treble", "tenor"}
    assert cfg.key_signatures == {0} and cfg.note_values == {"whole"} and cfg.naming == "letters"
    assert cfg.ranges == {"alto": (20, 30)}  # only the one well-formed range inside the limits is kept


def test_the_keyboard_settings_are_saved_and_read_back_and_bad_ones_ignored():
    cfg = settings.keyboard
    cfg.black_keys, cfg.require_octave, cfg.low, cfg.high = False, True, 40, 80
    cfg.key_signature, cfg.keys = True, {-1, 2}
    sp.save_keyboard()
    cfg.__init__()
    sp.load_keyboard()
    assert (cfg.black_keys, cfg.require_octave, cfg.low, cfg.high) == (False, True, 40, 80)
    assert cfg.key_signature and cfg.keys == {-1, 2}
    store().setValue("keyboard/low", 90)
    store().setValue("keyboard/high", 50)  # backwards: not used
    cfg.__init__()
    sp.load_keyboard()
    assert (cfg.low, cfg.high) == (settings.KEYBOARD_DEFAULT[0], settings.KEYBOARD_DEFAULT[1])
    store().setValue("keyboard/low", "not a number")
    cfg.__init__()
    sp.load_keyboard()  # unreadable: loading stops quietly and keeps the defaults
    assert cfg.low == settings.KEYBOARD_DEFAULT[0] and cfg.key_signature is False


def test_the_construction_settings_are_read_back_and_bad_ones_ignored():
    s = store()
    s.setValue("construction/clefs", "bass,grand,nonsense")
    s.setValue("construction/accidentals", "true")
    s.setValue("construction/keySignature", "true")
    s.setValue("construction/keys", "-3,0,40")
    settings.construction.__init__()
    sp.load_construction()
    cfg = settings.construction
    assert cfg.clefs == {"bass", "grand"} and cfg.accidentals and cfg.key_signature and cfg.keys == {-3, 0}
    s.setValue("construction/clefs", "nonsense")
    s.setValue("construction/keys", "99")
    cfg.__init__()
    sp.load_construction()
    assert cfg.clefs == {"treble", "bass"} and cfg.keys == {-3, -2, -1, 0, 1, 2, 3}


# -- the small parts --------------------------------------------------------------------------------------------------


def test_the_key_diagram_shows_which_keys_are_chosen(app):
    diagram = sp.KeyDiagram({0, 2, -3})
    assert diagram.toolTip() == "C, D, E♭" or set(diagram.toolTip().split(", ")) == {"C", "D", "E♭"}
    diagram.set_keys({7, -7})
    assert set(diagram.toolTip().split(", ")) == {"C♯", "C♭"}
    assert diagram.grab().width() == diagram.width()


def test_the_switch_slides_when_clicked_and_jumps_when_set(app):
    switch = sp.Switch()
    switch.setChecked(True)
    assert switch._pos == 1.0 and switch.isChecked()
    switch.setChecked(False)
    assert switch._pos == 0.0
    switch.click()  # the user's click animates the knob
    QTest.qWait(250)
    assert switch.isChecked() and switch._pos == pytest.approx(1.0)
    assert switch.sizeHint() == switch.size()
    assert switch.grab().width() == switch.width()
    switch.setEnabled(False)
    assert switch.grab().width() == switch.width()  # a disabled switch is drawn fainter


def test_a_menu_row_can_hold_a_picture_inline_or_on_its_own_line(app):
    from PySide6.QtWidgets import QLabel

    plain = sp._Row("Plain")
    plain.attach(QLabel("inline"))
    plain.fit()  # only a tall row needs fitting
    tall = sp._Row("Tall", tall=True)
    tall.attach(QLabel("below"))
    assert tall.minimumHeight() > 0 and plain._contents.count() >= 3
    plain.show()
    assert plain.grab().width() > 0


def test_a_page_slides_in_and_ignores_requests_while_sliding(app):
    from PySide6.QtWidgets import QLabel

    stack = sp.SlideStack()
    stack.resize(200, 100)
    for text in ("one", "two", "three"):
        stack.addWidget(QLabel(text))
    stack.show()
    stack.slide_to(0)  # already there
    assert not stack.sliding
    stack.slide_to(1)
    assert stack.sliding
    stack.slide_to(2)  # ignored mid-transition
    slide()
    assert stack.currentIndex() == 1 and not stack.sliding
    stack.slide_to(0)  # going back slides the other way
    slide()
    assert stack.currentIndex() == 0


def test_the_range_editor_moves_either_end_within_its_limits(app):
    low_limit, high_limit = settings.RANGE_LIMITS["treble"]
    editor = sp.RangeEditor("treble", low_limit + 2, low_limit + 4)
    seen = []
    editor.edited.connect(lambda *args: seen.append(args))
    editor.low_up.click()
    assert editor.low == low_limit + 3 and seen[-1] == ("treble", low_limit + 3, low_limit + 4)
    editor.low_up.click()
    assert editor.low == low_limit + 4 and not editor.low_up.isEnabled()  # the lowest cannot pass the highest
    editor.high_up.click()
    editor.high_down.click()
    editor.low_down.click()
    assert editor.low == low_limit + 3 and editor.high == low_limit + 4
    for _ in range(10):
        editor.low_down.click()
    assert editor.low == low_limit and not editor.low_down.isEnabled()
    editor.high = high_limit - 1
    editor.high_up.click()
    assert editor.high == high_limit and not editor.high_up.isEnabled()
    assert "–" in editor.caption_text.text()


def test_the_choice_checklist_always_keeps_one_choice(app):
    checklist = sp.ChoiceChecklist([("Heading", [("a", "A"), ("b", "B")]), ("", [("c", "C")])], {"a"})
    changed = []
    checklist.changed.connect(lambda: changed.append(1))
    assert checklist.selected() == {"a"} and not checklist.boxes["a"].isEnabled()  # the only one cannot be unchecked
    checklist.boxes["b"].setChecked(True)
    assert checklist.selected() == {"a", "b"} and checklist.boxes["a"].isEnabled() and changed == [1]


def test_the_key_signature_page_greys_out_the_keys_until_it_is_switched_on(app):
    page = sp.KeySignaturePage(False, {0, 1})
    changed = []
    page.changed.connect(lambda: changed.append(1))
    assert not page.enabled() and not page.checklist.isEnabled() and page.selected() == {0, 1}
    page.switch_row.click()
    assert page.enabled() and page.checklist.isEnabled() and changed == [1]
    page.checklist.boxes[3].setChecked(True)
    assert page.selected() == {0, 1, 3} and changed == [1, 1]
    page.checklist.boxes[0].setChecked(False)
    page.checklist.boxes[1].setChecked(False)
    assert page.selected() == {3} and not page.checklist.boxes[3].isEnabled()  # the last key stays


# -- the note names pane --------------------------------------------------------------------------------------------


def watch(panel) -> list[int]:
    """A list that gets an entry each time the pane announces a change."""
    changes: list[int] = []
    panel.changed.connect(lambda: changes.append(1))
    return changes


@pytest.fixture
def names(app):
    panel = sp.NoteNameSettingsPanel(settings.note_names)
    panel.resize(290, 600)
    panel.show()
    return panel


def test_the_menu_opens_each_page_and_back_returns_to_the_menu(names):
    for row, index in ((names.clefs_row, 1), (names.range_row, 2), (names.keys_row, 3), (names.values_row, 4),
                       (names.names_row, 5)):
        row.click()
        slide()
        assert names.stack.currentIndex() == index
        back(names)
        assert names.stack.currentIndex() == 0
    names.clefs_row.click()
    names.clefs_row.click()  # a second click mid-slide is ignored
    slide()
    assert names.stack.currentIndex() == 1
    names._go(1)  # already there
    back(names)


def test_choosing_the_clefs_including_the_grand_staff(names):
    changes = watch(names)
    cfg = settings.note_names
    assert not hasattr(names, "single") and set(names.boxes) == set(settings.RANGE_KEYS)  # no switch: just the clefs
    names.boxes["grand"].setChecked(True)
    assert cfg.clefs == {"treble", "bass", "grand"} and store().value("noteNames/clefs") == "treble,bass,grand"
    names.boxes["soprano"].setChecked(True)
    for clef in ("treble", "bass", "grand"):
        names.boxes[clef].setChecked(False)
    assert cfg.clefs == {"soprano"} and not names.boxes["soprano"].isEnabled()  # the last clef stays
    assert changes and store().value("noteNames/clefs") == "soprano"
    back(names)
    assert names.range_pictures.items  # the menu's summary follows the settings


def test_a_grand_staff_saved_by_an_older_version_becomes_the_grand_staff_clef():
    s = store()
    s.setValue("noteNames/mode", "grand")
    s.setValue("noteNames/clefs", "treble,bass")  # the clefs an older version kept for when "single clef" was chosen
    settings.note_names.__init__()
    sp.load_note_names()
    assert settings.note_names.clefs == {"grand"} and s.value("noteNames/mode") is None
    sp.save_note_names()  # saved the new way, the old key is not written again
    settings.note_names.__init__()
    sp.load_note_names()
    assert settings.note_names.clefs == {"grand"} and s.value("noteNames/mode") is None


def test_the_summaries_follow_the_grand_staff(names):
    names.boxes["grand"].setChecked(True)
    names.boxes["treble"].setChecked(False)
    names.boxes["bass"].setChecked(False)
    names._refresh_summaries()
    assert [clef for clef, _, _ in names.range_pictures.items] == ["grand"]
    names.range_row.click()
    slide()
    assert list(names.range_editors) == ["grand"]
    back(names)


# -- the keyboard pane ------------------------------------------------------------------------------------------------


@pytest.fixture
def keyboard(app):
    panel = sp.KeyboardSettingsPanel(settings.keyboard)
    panel.resize(290, 600)
    panel.show()
    return panel


def test_the_keyboard_menu_opens_its_pages(keyboard):
    keyboard.range_row.click()
    slide()
    assert keyboard.stack.currentIndex() == 1
    back(keyboard)
    keyboard.keys_row.click()
    slide()
    assert keyboard.stack.currentIndex() == 2
    back(keyboard)
    keyboard.range_row.click()
    keyboard.range_row.click()  # ignored mid-slide
    slide()
    keyboard._go(1)  # already there
    assert keyboard.stack.currentIndex() == 1


def test_the_keyboard_range_moves_one_key_at_a_time_within_the_whole_piano(keyboard):
    changes = watch(keyboard)
    cfg, first, last = settings.keyboard, *settings.KEYBOARD_FULL
    low, high = cfg.low, cfg.high
    keyboard.arrows["low"][1].click()
    keyboard.arrows["high"][0].click()
    assert (cfg.low, cfg.high) == (low + 1, high - 1)
    assert keyboard.low_label.text() == sp.key_name(low + 1) and store().value("keyboard/low") == low + 1
    keyboard.entire.click()
    assert (cfg.low, cfg.high) == (first, last) and not keyboard.arrows["low"][0].isEnabled()
    assert not keyboard.arrows["high"][1].isEnabled()
    keyboard.entire.click()  # nothing changes, so nothing is saved or announced again
    count = len(changes)
    keyboard.entire.click()
    assert len(changes) == count
    keyboard.default.click()
    assert (cfg.low, cfg.high) == settings.KEYBOARD_DEFAULT
    cfg.low = cfg.high
    keyboard._refresh_range()
    assert not keyboard.arrows["low"][1].isEnabled() and not keyboard.arrows["high"][0].isEnabled()
    keyboard._step("low", +5)  # the lowest key cannot pass the highest
    keyboard._step("high", -5)
    assert cfg.low <= cfg.high


def test_the_keyboard_switches_and_key_signatures_change_the_settings(keyboard):
    changes = watch(keyboard)
    cfg = settings.keyboard
    keyboard.black_keys_row.click()
    assert not cfg.black_keys
    keyboard.octave_row.click()
    assert cfg.require_octave and store().value("keyboard/requireOctave") == "true"
    keyboard.key_page.switch_row.click()
    keyboard.key_page.checklist.boxes[4].setChecked(True)
    assert cfg.key_signature and 4 in cfg.keys and store().value("keyboard/keySignature") == "true"
    assert len(changes) == 4


# -- the note construction pane -------------------------------------------------------------------------------------


@pytest.fixture
def construction(app):
    panel = sp.NoteConstructionSettingsPanel(settings.construction)
    panel.resize(290, 600)
    panel.show()
    return panel


def test_the_construction_pane_opens_its_pages_and_edits_the_settings(construction):
    cfg = settings.construction
    construction.staff_row.click()
    slide()
    assert construction.stack.currentIndex() == 1
    construction.boxes["grand"].setChecked(True)
    construction.boxes["bass"].setChecked(False)
    assert cfg.clefs == {"treble", "grand"} and store().value("construction/clefs") == "treble,grand"
    construction.boxes["treble"].setChecked(False)
    assert cfg.clefs == {"grand"} and not construction.boxes["grand"].isEnabled()
    construction.staff_row.click()  # ignored: already open
    back(construction)
    assert construction.clef_pictures is not None
    construction.accidentals_row.click()
    assert cfg.accidentals and store().value("construction/accidentals") == "true"
    construction.keys_row.click()
    slide()
    assert construction.stack.currentIndex() == 2
    construction.key_page.switch_row.click()
    construction.key_page.checklist.boxes[-2].setChecked(True)
    assert cfg.key_signature and -2 in cfg.keys
    back(construction)
    assert construction.keys_row.value.text() == ""  # with key signatures on, the diagram shows instead of "Off"


# -- the arpeggio pane's pages ----------------------------------------------------------------------------------------


def test_the_arpeggio_pane_opens_each_page_and_back_returns(app):
    panel = sp.ArpeggioSettingsPanel(settings.arpeggio)
    panel.resize(290, 600)
    panel.show()
    for row, index in ((panel.staff_row, 1), (panel.types_row, 2), (panel.inversions_row, 3), (panel.keys_row, 4)):
        row.click()
        slide()
        assert panel.stack.currentIndex() == index
        back(panel)
    panel.staff_row.click()
    panel.staff_row.click()  # ignored mid-slide
    slide()
    panel._go(1)
    panel.boxes["alto"].setChecked(True)
    panel.boxes["treble"].setChecked(False)
    assert settings.arpeggio.clefs == {"bass", "alto"}
    back(panel)
    panel.key_page.switch_row.click()
    assert settings.arpeggio.key_signature
    assert panel.keys_row.value.text() == ""


def test_dragging_the_keyboard_sets_the_range(app):
    panel = sp.KeyboardSettingsPanel(settings.keyboard)
    panel.span.dragged.emit(48, 60)
    assert (settings.keyboard.low, settings.keyboard.high) == (48, 60)
    assert panel.low_label.text() == sp.key_name(48)
