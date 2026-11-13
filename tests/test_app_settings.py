import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from alto.ui import app_settings
from alto.ui.app_settings import AppSettingsDialog
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture
def dialog(app, monkeypatch):
    """A settings dialog that never touches the saved settings."""
    monkeypatch.setattr(app_settings, "saved_theme", lambda: "dark")
    dlg = AppSettingsDialog()
    yield dlg
    dlg.deleteLater()  # gone before the application, or Qt crashes when Python exits
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_each_theme_has_a_preview_card_and_the_saved_one_is_chosen(dialog):
    assert list(dialog.theme_cards) == ["system", "light", "dark"]
    assert [k for k, c in dialog.theme_cards.items() if c.isChecked()] == ["dark"]


def test_the_theme_previews_draw_without_error(dialog):
    from PySide6.QtGui import QPixmap

    for card in dialog.theme_cards.values():
        pix = QPixmap(card.size())
        card.render(pix)
        assert not pix.isNull()


def test_the_segmented_control_switches_between_theme_and_notation_style(dialog):
    assert dialog.appearance_pages.currentIndex() == 0
    dialog.segment_buttons[1].click()
    assert dialog.appearance_pages.currentIndex() == 1
    dialog.segment_buttons[0].click()
    assert dialog.appearance_pages.currentIndex() == 0


def test_a_palette_change_restyles_the_segmented_control(dialog):
    from PySide6.QtCore import QEvent

    before = dialog.segments.styleSheet()
    QApplication.sendEvent(dialog, QEvent(QEvent.Type.PaletteChange))
    assert dialog.segments.styleSheet() == before  # same palette, same style: redrawn without error


def test_choosing_a_theme_saves_and_applies_it(dialog, monkeypatch):
    from alto.ui import theme

    applied = []
    monkeypatch.setattr(app_settings, "apply_theme", applied.append)
    assert not dialog.theme_changed
    dialog.theme_cards["light"].click()
    assert theme.saved_theme() == "light" and applied == ["light"] and dialog.theme_changed


def test_each_keyboard_style_has_a_card_and_the_classic_one_is_chosen_by_default(dialog):
    from alto.ui import keyboard_styles
    from PySide6.QtGui import QPixmap

    assert list(dialog.keyboard_cards) == [*(s.key for s in keyboard_styles.STYLES), "custom"]
    assert [k for k, c in dialog.keyboard_cards.items() if c.isChecked()] == ["classic"]
    dialog.segment_buttons[2].click()
    assert dialog.appearance_pages.currentIndex() == 2
    for card in dialog.keyboard_cards.values():
        pix = QPixmap(card.size())
        card.render(pix)
        assert not pix.isNull()


def test_clicking_a_keyboard_card_applies_the_style(dialog):
    from alto.ui import keyboard_styles

    dialog.keyboard_cards["harpsichord-french"].click()
    assert keyboard_styles.current().key == "harpsichord-french"


def test_the_builder_colours_each_part_and_selects_the_custom_style(dialog):
    from alto.ui import keyboard_styles

    dialog.builder._set("naturals", "#ead9aa")  # boxwood
    assert keyboard_styles.current().key == "custom" and keyboard_styles.custom_colours()["naturals"] == "#ead9aa"
    assert dialog.keyboard_cards["custom"].isChecked()
    assert dialog.keyboard_cards["custom"].keys.style_override.white[0] == "#ead9aa"  # the card previews it
    dialog.builder._set("felt", "#7d1f27")
    dialog.builder._set("felt", None)  # an optional part can be left out
    assert keyboard_styles.custom_colours()["felt"] is None and keyboard_styles.current().felt is None
    assert dialog.builder.swatches["felt"].text() == "none"


def test_the_builder_has_a_chip_for_every_material_and_none_for_optional_parts(dialog):
    from alto.ui import keyboard_styles
    from PySide6.QtWidgets import QToolButton

    chips = dialog.builder.findChildren(QToolButton)
    required = sum(1 for _, _, optional in keyboard_styles.COMPONENTS if not optional)
    optional = len(keyboard_styles.COMPONENTS) - required
    assert len(chips) == len(keyboard_styles.COMPONENTS) * len(keyboard_styles.MATERIALS) + optional
    next(c for c in chips if c.toolTip().startswith("Ebony  ")).click()
    assert keyboard_styles.current().key == "custom"


def test_the_builder_opens_the_colour_picker_and_keeps_a_chosen_colour(dialog, monkeypatch):
    from alto.ui import keyboard_styles
    from PySide6.QtGui import QColor

    picked = iter([QColor("#336699"), QColor()])  # then the dialog is cancelled
    monkeypatch.setattr(app_settings.QColorDialog, "getColor", lambda *a, **k: next(picked))
    dialog.builder.swatches["case"].click()
    assert keyboard_styles.custom_colours()["case"] == "#336699"
    dialog.builder.swatches["case"].click()
    assert keyboard_styles.custom_colours()["case"] == "#336699"  # cancelled: unchanged
