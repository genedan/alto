import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from alto.audio import sounds
from alto.ui import instrument_picker
from alto.ui.instrument_picker import InstrumentPicker
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


@pytest.fixture
def picker(app, monkeypatch):
    """A picker that never touches the saved settings, and puts the instrument back afterwards."""
    monkeypatch.setattr(instrument_picker, "save_instrument", lambda: None)
    before = sounds.instrument
    sounds.instrument = "piano"
    yield InstrumentPicker()
    sounds.instrument = before


def rows(picker):
    return [picker.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(picker.list.count())]


def texts(picker):
    return " ".join(picker.facts.itemAt(i).widget().text() for i in range(picker.facts.count()))


def row_labels(picker):
    """The text of each 'Use this instrument' button on the page, in order."""
    return [use.text() for use, _hear in picker.buttons.values()]


def test_every_instrument_is_listed_once_and_the_one_in_use_is_selected_and_ticked(picker):
    assert rows(picker) == ["Piano", "Flute", "French Horn", "Viola", "Marimba", "Vibraphone"]
    assert picker.list.currentItem().data(Qt.ItemDataRole.UserRole) == "Piano"
    assert "✓" in picker.list.item(0).text()
    assert picker.title.text() == "Piano"
    assert row_labels(picker) == ["In use"]  # the piano has only one way of playing, so one row


def test_the_viola_is_one_entry_with_a_row_of_buttons_for_arco_and_for_pizzicato(picker):
    picker.select("viola_bowed")
    assert picker.title.text() == "Viola"
    assert list(picker.buttons) == ["viola_bowed", "viola_plucked"]
    assert row_labels(picker) == ["Use this instrument (Arco)", "Use this instrument (Pizzicato)"]
    assert "Bowed (arco)" in texts(picker) and "45 notes" in texts(picker)
    assert "Plucked (pizzicato)" in texts(picker) and "20 notes" in texts(picker)
    assert sounds.instrument == "piano"


def test_using_pizzicato_marks_the_viola_entry_with_the_way_of_playing(picker):
    picker.select("viola_plucked")
    picker.buttons["viola_plucked"][0].click()
    assert sounds.instrument == "viola_plucked"
    assert row_labels(picker) == ["Use this instrument (Arco)", "In use (Pizzicato)"]
    entry = picker.list.item(rows(picker).index("Viola")).text()
    assert entry == "Viola (Pizzicato)  ✓"


def test_choosing_a_row_shows_its_summary_without_switching_instrument(picker):
    picker.select("viola_bowed")
    assert picker.buttons["viola_bowed"][0].isEnabled()
    assert sounds.instrument == "piano"
    assert "Manuel Tabora" in texts(picker) and "45 notes" in texts(picker) and "C3 to A6" in texts(picker)


def test_using_an_instrument_switches_to_it_and_ticks_it(picker):
    picker.select("marimba")
    picker.buttons["marimba"][0].click()
    assert sounds.instrument == "marimba"
    use = picker.buttons["marimba"][0]
    assert use.text() == "In use" and not use.isEnabled()
    items = [picker.list.item(i) for i in range(picker.list.count())]
    ticked = [item.data(Qt.ItemDataRole.UserRole) for item in items if "✓" in item.text()]
    assert ticked == ["Marimba"]


def test_an_instrument_with_no_recordings_cannot_be_chosen(picker, monkeypatch):
    real = sounds.recordings
    monkeypatch.setattr(sounds, "recordings", lambda inst: {} if inst.key == "vibraphone" else real(inst))
    picker.select("vibraphone")
    assert not picker.banner.isHidden() and "No recordings" in picker.banner.text()
    use, hear = picker.buttons["vibraphone"]
    assert use.text() == "Not installed" and not use.isEnabled() and not hear.isEnabled()
    picker.use("vibraphone")
    assert sounds.instrument == "piano"


def test_hear_it_plays_a_short_arpeggio_in_that_instrument(picker, monkeypatch):
    played = []
    def record(midi, volume=1.0, instrument=None, force=False, **kwargs):
        played.append((midi, instrument, force))

    monkeypatch.setattr(sounds, "play_midi", record)
    picker.select("viola_bowed")
    picker.buttons["viola_bowed"][1].click()
    QTest.qWait(900)
    assert played == [(60, "viola_bowed", True), (64, "viola_bowed", True), (67, "viola_bowed", True)]
    assert sounds.instrument == "piano"  # hearing it does not choose it
