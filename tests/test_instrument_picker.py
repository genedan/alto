"""The instrument picker: the list, the summary of each instrument and choosing or hearing one."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import (
    QEvent,
    Qt,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from alto.audio import sounds
from alto.ui import instrument_picker
from alto.ui.instrument_picker import (
    InstrumentPicker,
    load_instrument,
    save_instrument,
)
from alto.ui.store import store

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def picker(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[InstrumentPicker]:
    """
    Provide a picker that never touches the saved settings, and puts the instrument back afterwards.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.

    Yields
    ------
    InstrumentPicker
        The picker; the instrument in use is put back afterwards.
    """
    monkeypatch.setattr(instrument_picker, "save_instrument", lambda: None)
    before = sounds.instrument
    sounds.instrument = "piano"
    yield InstrumentPicker()
    sounds.instrument = before


def rows(picker: InstrumentPicker) -> list[object]:
    """
    List the instruments in the picker's list.

    Parameters
    ----------
    picker : InstrumentPicker
        The picker.

    Returns
    -------
    list of object
        The name of each row, in order.
    """
    return [picker.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(picker.list.count())]


def texts(picker: InstrumentPicker) -> str:
    """
    Join the text of the summary's labels.

    Parameters
    ----------
    picker : InstrumentPicker
        The picker.

    Returns
    -------
    str
        The labels separated by spaces.
    """
    return " ".join(picker.facts.itemAt(i).widget().text() for i in range(picker.facts.count()))  # pyright: ignore[reportAttributeAccessIssue]


def row_labels(picker: InstrumentPicker) -> list[str]:
    """
    Return the text of each 'Use this instrument' button on the page, in order.

    Parameters
    ----------
    picker : InstrumentPicker
        The picker.

    Returns
    -------
    list of str
        The button texts, in order.
    """
    return [use.text() for use, _hear in picker.buttons.values()]


def test_every_instrument_is_listed_once_and_the_one_in_use_is_selected_and_ticked(picker: InstrumentPicker) -> None:
    """
    Check that every instrument is listed once and the one in use is selected and ticked.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    assert rows(picker) == [
        "Piano",
        "Flute",
        "French Horn",
        "Viola",
        "Marimba",
        "Vibraphone",
    ]
    assert picker.list.currentItem().data(Qt.ItemDataRole.UserRole) == "Piano"
    assert "✓" in picker.list.item(0).text()
    assert picker.title.text() == "Piano"
    assert row_labels(picker) == ["In use"]  # the piano has only one way of playing, so one row


def test_the_viola_is_one_entry_with_a_row_of_buttons_for_arco_and_for_pizzicato(picker: InstrumentPicker) -> None:
    """
    Check that the viola is one entry with a row of buttons for arco and for pizzicato.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    picker.select("viola_bowed")
    assert picker.title.text() == "Viola"
    assert list(picker.buttons) == ["viola_bowed", "viola_plucked"]
    assert row_labels(picker) == ["Use this instrument (Arco)", "Use this instrument (Pizzicato)"]
    assert "Bowed (arco)" in texts(picker) and "45 notes" in texts(picker)
    assert "Plucked (pizzicato)" in texts(picker) and "20 notes" in texts(picker)
    assert sounds.instrument == "piano"


def test_using_pizzicato_marks_the_viola_entry_with_the_way_of_playing(picker: InstrumentPicker) -> None:
    """
    Check that using pizzicato marks the viola entry with the way of playing.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    picker.select("viola_plucked")
    picker.buttons["viola_plucked"][0].click()
    assert sounds.instrument == "viola_plucked"
    assert row_labels(picker) == ["Use this instrument (Arco)", "In use (Pizzicato)"]
    entry = picker.list.item(rows(picker).index("Viola")).text()
    assert entry == "Viola (Pizzicato)  ✓"


def test_choosing_a_row_shows_its_summary_without_switching_instrument(picker: InstrumentPicker) -> None:
    """
    Check that choosing a row shows its summary without switching instrument.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    picker.select("viola_bowed")
    assert picker.buttons["viola_bowed"][0].isEnabled()
    assert sounds.instrument == "piano"
    assert "Manuel Tabora" in texts(picker) and "45 notes" in texts(picker) and "C3 to A6" in texts(picker)


def test_using_an_instrument_switches_to_it_and_ticks_it(picker: InstrumentPicker) -> None:
    """
    Check that using an instrument switches to it and ticks it.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    picker.select("marimba")
    picker.buttons["marimba"][0].click()
    assert sounds.instrument == "marimba"
    use = picker.buttons["marimba"][0]
    assert use.text() == "In use" and not use.isEnabled()
    items = [picker.list.item(i) for i in range(picker.list.count())]
    ticked = [item.data(Qt.ItemDataRole.UserRole) for item in items if "✓" in item.text()]
    assert ticked == ["Marimba"]


def test_an_instrument_with_no_recordings_cannot_be_chosen(
    picker: InstrumentPicker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that an instrument with no recordings cannot be chosen.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    real = sounds.recordings
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(sounds, "recordings", lambda inst: {} if inst.key == "vibraphone" else real(inst))
    picker.select("vibraphone")
    assert not picker.banner.isHidden() and "No recordings" in picker.banner.text()
    use, hear = picker.buttons["vibraphone"]
    assert use.text() == "Not installed" and not use.isEnabled() and not hear.isEnabled()
    picker.use("vibraphone")
    assert sounds.instrument == "piano"


def test_hear_it_plays_a_short_arpeggio_in_that_instrument(
    picker: InstrumentPicker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that hear it plays a short arpeggio in that instrument.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    played = []

    def record(
        midi: int,
        volume: float = 1.0,
        instrument: str | None = None,
        force: bool = False,
        **kwargs: object,
    ) -> None:
        """
        Record a note instead of playing it.

        Parameters
        ----------
        midi : int
            The note.
        volume : float
            Its volume.
        instrument : str or None
            The instrument.
        force : bool
            Whether it was forced.
        kwargs : object
            Ignored.
        """
        del volume, kwargs  # accepted to match what it stands in for, but not needed
        played.append((midi, instrument, force))

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(sounds, "play_midi", record)
    picker.select("viola_bowed")
    picker.buttons["viola_bowed"][1].click()
    QTest.qWait(900)
    assert played == [(60, "viola_bowed", True), (64, "viola_bowed", True), (67, "viola_bowed", True)]
    assert sounds.instrument == "piano"  # hearing it does not choose it


def test_double_clicking_an_entry_uses_the_way_of_playing_already_in_use_or_the_first(picker: InstrumentPicker) -> None:
    """
    Check that double clicking an entry uses the way of playing already in use or the first.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    viola = rows(picker).index("Viola")
    picker.list.itemDoubleClicked.emit(picker.list.item(viola))
    assert sounds.instrument == "viola_bowed"  # the first way of playing
    picker.use("viola_plucked")
    picker.list.itemDoubleClicked.emit(picker.list.item(viola))
    assert sounds.instrument == "viola_plucked"  # the one in use stays


def test_a_theme_change_redraws_the_summary_in_the_new_colours(picker: InstrumentPicker) -> None:
    """
    Check that a theme change redraws the summary in the new colours.

    Parameters
    ----------
    picker : InstrumentPicker
        The instrument picker under test.
    """
    picker.select("viola_bowed")
    before = picker.title.text()
    QApplication.sendEvent(picker, QEvent(QEvent.Type.PaletteChange))
    assert picker.title.text() == before and picker.shown == "Viola"


def test_the_chosen_instrument_is_saved_and_read_back(app: QApplication) -> None:
    """
    Check that the chosen instrument is saved and read back.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    sounds.instrument = "marimba"
    save_instrument()
    assert store().value("audio/instrument") == "marimba"
    sounds.instrument = "piano"
    load_instrument()
    assert sounds.instrument == "marimba"
    store().setValue("audio/instrument", "no-such-instrument")
    load_instrument()
    assert sounds.instrument == "piano"  # an unknown one falls back to the piano
    sounds.instrument = "piano"
