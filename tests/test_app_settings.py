"""The settings dialog: its sections, the choices it saves and the pictures it shows."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QEvent
from PySide6.QtGui import (
    QColor,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QToolButton,
)

from alto.ui import (
    app_settings,
    keyboard_styles,
    theme,
)
from alto.ui.app_settings import AppSettingsDialog

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def dialog(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[AppSettingsDialog]:
    """
    Provide a settings dialog that never touches the saved settings.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.

    Yields
    ------
    AppSettingsDialog
        The dialog; it is closed afterwards.
    """
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(app_settings, "saved_theme", lambda: "dark")
    dlg = AppSettingsDialog()
    yield dlg
    dlg.deleteLater()  # gone before the application, or Qt crashes when Python exits
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_each_theme_has_a_preview_card_and_the_saved_one_is_chosen(dialog: AppSettingsDialog) -> None:
    """
    Check that each theme has a preview card and the saved one is chosen.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    assert list(dialog.theme_cards) == ["system", "light", "dark"]
    assert [k for k, c in dialog.theme_cards.items() if c.isChecked()] == ["dark"]


def test_the_theme_previews_draw_without_error(dialog: AppSettingsDialog) -> None:
    """
    Check that the theme previews draw without error.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    for card in dialog.theme_cards.values():
        pix = QPixmap(card.size())
        card.render(pix)
        assert not pix.isNull()


def test_the_segmented_control_switches_between_theme_and_notation_style(dialog: AppSettingsDialog) -> None:
    """
    Check that the segmented control switches between theme and notation style.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    assert dialog.appearance_pages.currentIndex() == 0
    dialog.segment_buttons[1].click()
    assert dialog.appearance_pages.currentIndex() == 1
    dialog.segment_buttons[0].click()
    assert dialog.appearance_pages.currentIndex() == 0


def test_a_palette_change_restyles_the_segmented_control(dialog: AppSettingsDialog) -> None:
    """
    Check that a palette change restyles the segmented control.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    before = dialog.segments.styleSheet()
    QApplication.sendEvent(dialog, QEvent(QEvent.Type.PaletteChange))
    assert dialog.segments.styleSheet() == before  # same palette, same style: redrawn without error


def test_choosing_a_theme_saves_and_applies_it(
    dialog: AppSettingsDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that choosing a theme saves and applies it.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    applied = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(app_settings, "apply_theme", applied.append)
    assert not dialog.theme_changed
    dialog.theme_cards["light"].click()
    assert theme.saved_theme() == "light" and applied == ["light"] and dialog.theme_changed


def test_each_keyboard_style_has_a_card_and_the_classic_one_is_chosen_by_default(dialog: AppSettingsDialog) -> None:
    """
    Check that each keyboard style has a card and the classic one is chosen by default.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    assert list(dialog.keyboard_cards) == [*(s.key for s in keyboard_styles.STYLES), "custom"]
    assert [k for k, c in dialog.keyboard_cards.items() if c.isChecked()] == ["classic"]
    dialog.segment_buttons[2].click()
    assert dialog.appearance_pages.currentIndex() == 2
    for card in dialog.keyboard_cards.values():
        pix = QPixmap(card.size())
        card.render(pix)
        assert not pix.isNull()


def test_clicking_a_keyboard_card_applies_the_style(dialog: AppSettingsDialog) -> None:
    """
    Check that clicking a keyboard card applies the style.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    dialog.keyboard_cards["harpsichord-french"].click()
    assert keyboard_styles.current().key == "harpsichord-french"


def test_the_builder_colours_each_part_and_selects_the_custom_style(dialog: AppSettingsDialog) -> None:
    """
    Check that the builder colours each part and selects the custom style.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    dialog.builder._set("naturals", colour="#ead9aa")  # boxwood
    assert keyboard_styles.current().key == "custom" and keyboard_styles.custom_colours()["naturals"] == "#ead9aa"
    assert dialog.keyboard_cards["custom"].isChecked()
    assert dialog.keyboard_cards["custom"].keys.style_override.white[0] == "#ead9aa"  # the card previews it
    dialog.builder._set("felt", colour="#7d1f27")
    dialog.builder._set("felt", colour=None)  # an optional part can be left out
    assert keyboard_styles.custom_colours()["felt"] is None and keyboard_styles.current().felt is None
    assert dialog.builder.swatches["felt"].text() == "none"


def test_the_builder_has_a_chip_for_every_material_and_none_for_optional_parts(dialog: AppSettingsDialog) -> None:
    """
    Check that the builder has a chip for every material and none for optional parts.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    """
    chips = dialog.builder.findChildren(QToolButton)
    required = sum(1 for _, _, optional in keyboard_styles.COMPONENTS if not optional)
    optional = len(keyboard_styles.COMPONENTS) - required
    assert len(chips) == len(keyboard_styles.COMPONENTS) * len(keyboard_styles.MATERIALS) + optional
    next(c for c in chips if c.toolTip().startswith("Ebony  ")).click()
    assert keyboard_styles.current().key == "custom"


def test_the_builder_opens_the_colour_picker_and_keeps_a_chosen_colour(
    dialog: AppSettingsDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that the builder opens the colour picker and keeps a chosen colour.

    Parameters
    ----------
    dialog : AppSettingsDialog
        The dialog under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    picked = iter([QColor("#336699"), QColor()])  # then the dialog is cancelled
    monkeypatch.setattr(app_settings.QColorDialog, "getColor", lambda *a, **k: next(picked))
    dialog.builder.swatches["case"].click()
    assert keyboard_styles.custom_colours()["case"] == "#336699"
    dialog.builder.swatches["case"].click()
    assert keyboard_styles.custom_colours()["case"] == "#336699"  # cancelled: unchanged
