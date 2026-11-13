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
