"""The home screen, the main window with its exercise list and menu, and starting the app."""

from __future__ import annotations

import random
import sys
from typing import (
    TYPE_CHECKING,
)

import pytest
from PySide6.QtCore import (
    QEvent,
    QObject,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QHelpEvent, QKeySequence, QPalette
from PySide6.QtTest import (
    QSignalSpy,
    QTest,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QListWidget,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolTip,
    QWidget,
)

from alto import __main__ as entry
from alto import settings, updates
from alto.exercises import REGISTRY
from alto.exercises.base import (
    Exercise,
    Question,
)
from alto.exercises.library import KeyboardIntervals
from alto.learning import (
    Database,
    Learner,
)
from alto.learning.backup import app_version
from alto.ui import icons, motion
from alto.ui import main_window as mw
from alto.ui.colors import blend_name
from alto.ui.exercise_settings import save_keyboard_intervals
from alto.ui.exercise_view import ExerciseView
from alto.ui.home import (
    CARD_W,
    EXERCISE_ICONS,
    ExerciseCard,
    HomePage,
)
from alto.ui.lesson import LessonsPage
from alto.ui.main_window import MainWindow
from alto.ui.pictures import ClefPictures
from alto.ui.settings_panel import KeyboardIntervalSettingsPanel
from alto.ui.store import store
from alto.ui.theme import apply_theme, custom_theme, theme_palette

if TYPE_CHECKING:
    from collections.abc import (
        Callable,
        Iterator,
    )
    from pathlib import Path

# -- the home screen ------------------------------------------------------------------------------------------------


def test_every_card_shows_its_whole_name_and_description(app: QApplication) -> None:
    """
    Check that every card shows its whole name and description, with nothing cut off or running past the card.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    for cls in REGISTRY:
        card = ExerciseCard(cls)
        card.show()
        app.processEvents()
        for label in card.findChildren(QLabel):
            if label.wordWrap():
                assert label.heightForWidth(label.width()) <= label.height(), (cls.name, label.text())
            else:
                assert label.sizeHint().width() <= label.width(), (cls.name, label.text())
        card.close()


def test_tile_count_hover_explains_the_colors_and_clicks_the_tile(app: QApplication) -> None:
    """
    Give the count strip its own hover target while keeping the whole exercise tile clickable.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    card = ExerciseCard(KeyboardIntervals)
    card.set_counts((2, 4, 1))
    card.show()
    app.processEvents()
    target = card.counts
    assert card.childAt(target.geometry().center()) is target
    point = target.rect().center()
    app.sendEvent(target, QHelpEvent(QEvent.Type.ToolTip, point, target.mapToGlobal(point)))
    assert QToolTip.text().splitlines() == [
        "Blue — 4 new cards available",
        "Red — 1 incorrect card awaiting a correct answer",
        "Green — 2 reviews due",
    ]
    clicked = QSignalSpy(card.clicked)
    QTest.mouseClick(target, Qt.MouseButton.LeftButton, pos=point)
    assert clicked.count() == 1
    point = card.rect().center()
    app.sendEvent(card, QHelpEvent(QEvent.Type.ToolTip, point, card.mapToGlobal(point)))
    assert QToolTip.text() == KeyboardIntervals.description
    QToolTip.hideText()
    card.close()


def test_home_tile_and_button_borders_follow_theme_changes(app: QApplication, request: pytest.FixtureRequest) -> None:
    """
    Check the resting outlines on exercise tiles, lesson tiles, and ordinary buttons across theme changes.

    Parameters
    ----------
    app : QApplication
        Shared Qt application.
    request : pytest.FixtureRequest
        Restores the system theme after the comparison.
    """
    request.addfinalizer(lambda: apply_theme("system"))
    home = HomePage(REGISTRY)
    controls = (home.cards[0], home.lesson_cards[0], QPushButton("Next"))
    for theme, expected in (
        ("studio_dark", ["#181818", "#505050", "#505050"]),
        ("studio", ["#b3b6bb"] * 3),
    ):
        apply_theme(theme)
        app.processEvents()
        assert [widget.grab().toImage().pixelColor(20, 0).name() for widget in controls] == expected


def test_lesson_tiles_follow_the_desktop_while_visible(app: QApplication) -> None:
    """
    Check rendered borders and icons when Qt announces the scheme before installing its new palette.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    apply_theme("system")
    original = app.palette()
    home = HomePage(REGISTRY)
    home.set_mode("lessons", animate=False)
    home.show()
    app.processEvents()
    cards = tuple(home.lesson_cards)
    try:
        for key, scheme, border in (
            ("studio_dark", Qt.ColorScheme.Dark, "#505050"),
            ("studio", Qt.ColorScheme.Light, "#b0b0b0"),
            ("studio_dark", Qt.ColorScheme.Dark, "#505050"),
        ):
            colors = custom_theme(key)
            assert colors is not None
            palette = theme_palette(colors)
            app.styleHints().colorSchemeChanged.emit(scheme)
            app.setPalette(palette)
            app.processEvents()
            background = "#ffffff" if scheme == Qt.ColorScheme.Light else colors.panel
            for card in cards:
                assert card.isVisible()
                tile = card.grab().toImage()
                assert tile.pixelColor(20, 0).name() == border
                assert tile.pixelColor(5, tile.height() // 2).name() == background
                picture = next(label for label in card.findChildren(QLabel) if not label.pixmap().isNull())
                size = QSize(56, 56)
                expected = icons.svg_icon(card.icon_svg, color=palette.windowText().color(), size=56)
                assert picture.pixmap().toImage() == expected.pixmap(size).toImage()
    finally:
        app.setPalette(original)
        apply_theme("system")


@pytest.mark.parametrize("key", ["light", "system"])
def test_default_light_grid_matches_the_release_screenshot(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
) -> None:
    """
    Check the rendered grid, tile and search colors on a desktop with near-white window and base colors.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Provides a desktop scheme independently of the headless platform plugin.
    key : str
        The Light or System setting.
    """
    original = app.palette()
    desktop = QPalette(QColor("#fcfcfc"))
    desktop.setColor(QPalette.ColorRole.Base, QColor("#fcfcfc"))
    desktop.setColor(QPalette.ColorRole.Highlight, QColor("#ae510a"))
    try:
        app.setPalette(desktop)
        scheme = Qt.ColorScheme.Light if key == "system" else Qt.ColorScheme.Dark
        with monkeypatch.context() as patch:
            patch.setattr(type(app.styleHints()), "colorScheme", lambda self: scheme)
            apply_theme(key)
            window = MainWindow()
            window.show()
            app.processEvents()
            grid = window.home.grab().toImage()
            assert grid.pixelColor(2, grid.height() - 15).name() == "#efefef"
            tile = window.home.cards[0].grab().toImage()
            assert tile.pixelColor(5, tile.height() // 2).name() == "#ffffff"
            search = window.search_row.grab().toImage()
            assert search.pixelColor(search.width() - 18, 8).name() == "#e5e5e5"
            assert app.palette().highlight().color() == desktop.highlight().color()
    finally:
        app.setPalette(original)
        apply_theme("system")


def test_tiles_and_search_follow_the_scheme_when_the_platform_keeps_its_palette(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reproduce a GNOME scheme change that only updates the Qt style's standard palette.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Supplies the scheme and standard palette that a desktop platform plugin reports.
    """
    apply_theme("system")
    light = app.palette()
    colors = custom_theme("studio_dark")
    assert colors is not None
    dark = theme_palette(colors)
    window = MainWindow()
    window.home.mode_control.buttons[1].click()
    window.show()
    window.search_field.setText("clef")
    window.search_field.setFocus()
    app.processEvents()
    tile = window.home.lesson_cards[1]
    category_changes = QSignalSpy(window.home.category_tree.itemChanged)
    search_action = next(action for action in window.search_field.actions() if action.text() == "Search")
    try:
        with monkeypatch.context() as patch:
            scheme = Qt.ColorScheme.Light
            patch.setattr(type(app.styleHints()), "colorScheme", lambda self: scheme)
            patch.setattr(type(app.style()), "standardPalette", lambda self: dark if scheme == Qt.ColorScheme.Dark else light)
            for scheme, expected in ((Qt.ColorScheme.Dark, dark), (Qt.ColorScheme.Light, light)):
                app.styleHints().colorSchemeChanged.emit(scheme)
                app.processEvents()
                image = tile.grab().toImage()
                assert image.pixelColor(5, image.height() // 2) == expected.base().color()
                ink = expected.text().color()
                fill = blend_name(expected.window().color(), b=ink, t=0.04)
                edge = blend_name(expected.window().color(), b=ink, t=0.22)
                search = window.search_row.grab().toImage()
                assert search.pixelColor(search.width() // 2, search.height() // 2).name() == fill
                assert search.pixelColor(20, 0) == expected.highlight().color()
                assert window.search_field.text() == "clef" and window.search_field.hasFocus()
                assert (
                    search_action.icon().pixmap(16, 16).toImage()
                    == icons.svg_icon(icons.SEARCH, color=ink).pixmap(16, 16).toImage()
                )
                for actual, glyph, role, size in (
                    (window.glossary_button.icon(), icons.GLOSSARY, QPalette.ColorRole.WindowText, 24),
                    (window.home.mode_control.buttons[1].icon(), icons.LESSONS, QPalette.ColorRole.Highlight, 18),
                    (window.profile_action.icon(), icons.PROFILE, QPalette.ColorRole.WindowText, 18),
                    (window.home.category_filter.icon(), icons.FILTER, QPalette.ColorRole.WindowText, 24),
                ):
                    reference = icons.svg_icon(glyph, color=app.palette().color(role), size=size)
                    assert actual.pixmap(size, size).toImage() == reference.pixmap(size, size).toImage(), glyph
                leaf = window.home._filter_leaves[tile.title]
                size = window.home.category_tree.iconSize()
                expected_icon = icons.svg_icon(tile.icon_svg, color=app.palette().text().color(), size=size.width())
                assert leaf.icon(0).pixmap(size).toImage() == expected_icon.pixmap(size).toImage()
                assert category_changes.count() == 0
                window.view_button.setFocus()
                assert window.search_row.grab().toImage().pixelColor(20, 0).name() == edge
                window.search_field.setFocus()
    finally:
        apply_theme("system")


def test_musical_icons_follow_the_theme_at_double_density(app: QApplication, request: pytest.FixtureRequest) -> None:
    """
    Check that a clef checkbox redraws in the current theme at double density.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    request : pytest.FixtureRequest
        Restores the system theme.
    """
    request.addfinalizer(lambda: apply_theme("system"))
    picture = ClefPictures(["bass"])
    checkbox = QPushButton()
    picture.label_button(checkbox)
    for theme in ("studio_dark", "light"):
        apply_theme(theme)
        app.processEvents()
        actual = checkbox.icon().pixmap(picture.size(), 2.0).toImage()
        assert actual.devicePixelRatio() == 2
        assert actual == ClefPictures(["bass"]).to_icon().pixmap(picture.size(), 2.0).toImage()
        assert app.palette().text().color().name() in {
            actual.pixelColor(x, y).name()
            for x in range(actual.width())
            for y in range(actual.height())
            if actual.pixelColor(x, y).alpha() == 255
        }


def test_the_home_screen_has_a_card_for_each_exercise_and_reports_the_one_clicked(app: QApplication) -> None:
    """
    Check that the home screen has a card for each exercise and reports the one clicked.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    home = HomePage(REGISTRY)
    assert len(home.cards) == len(REGISTRY) and all(isinstance(c, ExerciseCard) for c in home.cards)
    chosen = []
    home.exercise_chosen.connect(chosen.append)
    home.cards[2].click()
    assert chosen == [REGISTRY[2]]
    assert home.cards[0].toolTip() == REGISTRY[0].description


def test_the_cards_are_laid_out_in_as_many_columns_as_fit(app: QApplication) -> None:
    """
    Check that the cards are laid out in as many columns as fit.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    home = HomePage(REGISTRY)
    widths = {}
    for width in (
        300,
        700,
        1100,
        2000,
    ):
        home.resize(width, 600)
        home.show()
        QTest.qWait(10)
        widths[width] = home._columns
        items = [home.rows.itemAt(i) for i in range(home.rows.count())]
        # noinspection PyUnboundLocalVariable
        rows = [layout for item in items if item is not None and (layout := item.layout()) is not None]
        # noinspection PyUnresolvedReferences
        assert sum(r.count() - 2 for r in rows) == len(REGISTRY)  # every card is in a row (less the two stretches)
        assert home.grab().width() == width
    assert widths[300] == 1 and widths[300] <= widths[700] <= widths[1100] <= widths[2000]
    assert widths[2000] >= 7 and widths[1100] >= 4  # a wide window holds the whole row of cards
    home.resize(2000, 600)
    before = home._columns
    home._reflow()  # nothing changes when the width has not
    assert home._columns == before
    home.category_filter.click()
    home._filter_slide.setCurrentTime(home._filter_slide.duration())
    assert home.filter_sidebar.isVisible() and home._columns < before
    home.category_filter.click()
    home._filter_slide.setCurrentTime(0)
    assert home.filter_sidebar.isHidden() and home._columns == before


def test_an_exercise_with_no_icon_of_its_own_gets_the_default(app: QApplication) -> None:
    """
    Check that an exercise with no icon of its own gets the default.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """

    class Odd(Exercise):
        """
        An exercise with no icon of its own.
        """

        name, category, description = "Odd", "Notation", "Something new."

        def generate(self, rng: random.Random) -> Question:
            """
            Make the one fixed question.

            Parameters
            ----------
            rng : random.Random
                The random source (not used: the question is fixed).

            Returns
            -------
            Question
                A question.
            """
            return Question("?", choices=["a"], answer="a")

    assert "Odd" not in EXERCISE_ICONS
    card = ExerciseCard(Odd)
    assert card.size() == QSize(CARD_W, card.height()) and card.grab().width() == CARD_W
    labels = [label.text() for label in card.findChildren(QLabel)]
    assert "<b>Odd</b>" in labels and "NOTATION" in labels


# -- the main window ------------------------------------------------------------------------------------------------


@pytest.fixture
def window(
    app: QApplication,
    practiced_learner: Callable[..., Learner],
) -> Iterator[MainWindow]:
    """
    Provide a shown main window with some history.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practiced_learner : Callable
        Builds a learner with a history.

    Yields
    ------
    MainWindow
        The window; it is closed afterwards.
    """
    w = MainWindow(practiced_learner(10))
    w.show()
    yield w
    w.close()
    w.deleteLater()
    QApplication.sendPostedEvents(None, 0)


def settle() -> None:
    """
    Let the window's animations finish: the list sliding open or shut, and the page sliding in.
    """
    motion.settle()


def test_the_window_starts_on_the_home_screen_with_a_list_of_exercises(window: MainWindow) -> None:
    """
    Check that the window starts on the home screen with a list of exercises.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    assert window.windowTitle() == MainWindow.APP_TITLE and window.stack.currentWidget() is window.home
    assert window.sidebar_width() == 0  # the start screen has no list
    entries = [window.nav.item(i) for i in range(window.nav.count())]
    classes = [e.data(Qt.ItemDataRole.UserRole) for e in entries if e.data(Qt.ItemDataRole.UserRole)]
    assert classes == list(REGISTRY)
    headings = [e.text() for e in entries if not e.data(Qt.ItemDataRole.UserRole)]
    # noinspection PyTypeChecker
    assert "NOTATION" in headings and all(not (e.flags() & Qt.ItemFlag.ItemIsSelectable) for e in entries if e.text() in headings)
    assert window.stats_button.isVisibleTo(window) and window.database_button.isVisibleTo(window)
    assert window.profile_action.text() == "Profile: Ada…"


def test_each_exercise_in_the_list_sits_under_its_own_category_heading(window: MainWindow) -> None:
    """
    Check that each exercise in the list sits under its own category heading.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    heading = None
    shown = []
    for i in range(window.nav.count()):
        row = window.nav.item(i)
        cls = row.data(Qt.ItemDataRole.UserRole)
        if cls is None:
            heading = row.text()
            shown.append(heading)
        else:
            assert heading == cls.category.upper(), f"{cls.name} is under {heading}"
    assert len(shown) == len(set(shown))  # each heading appears once


def test_building_the_window_opens_no_other_window(
    app: QApplication,
    practiced_learner: Callable[..., Learner],
) -> None:
    """
    Check that building the main window opens no window of its own besides itself.

    A widget with no parent that is shown opens as a window. The desktop gives the first window an app opens the startup token
    of the launch, and the dock waits for it, so a button that flashed up as a window first made the icon wait for 15 seconds.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practiced_learner : Callable
        Builds a learner with a history. Only the first parameter may be positional.
    """
    opened: list[str] = []

    class Spy(QObject):
        """Note every top-level widget that is shown."""

        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            """
            Note a top-level widget that is shown.

            Parameters
            ----------
            watched : QObject
                The object the event is for.
            event : QEvent
                The event.

            Returns
            -------
            bool
                False, so the event is not stopped.
            """
            if event.type() == QEvent.Type.Show and isinstance(watched, QWidget) and watched.isWindow():
                opened.append(type(watched).__name__)
            return False

    spy = Spy()
    app.installEventFilter(spy)
    try:
        for learner in (practiced_learner(3), None):
            w = MainWindow(learner)
            w.close()
            w.deleteLater()
    finally:
        app.removeEventFilter(spy)
    assert opened == []


def test_without_a_profile_nothing_is_recorded_and_the_history_buttons_are_hidden(app: QApplication) -> None:
    """
    Check that without a profile nothing is recorded and the history buttons are hidden.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    w = MainWindow(None)
    w.show()
    assert not w.stats_button.isVisibleTo(w) and not w.database_button.isVisibleTo(w)
    assert not w.profile_action.isVisible()
    w.open_stats()
    w.open_database()
    w.switch_profile()
    assert w._overlay is None  # all three need a profile
    w.open_exercise(REGISTRY[0])
    current = w.stack.currentWidget()
    assert isinstance(current, ExerciseView) and current.learner is None
    w.close()


def test_choosing_an_exercise_shows_it_opens_the_list_and_titles_the_window(window: MainWindow) -> None:
    """
    Check that choosing an exercise shows it opens the list and titles the window.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    # noinspection PyTypeChecker
    window.open_exercise(None)  # pyright: ignore[reportArgumentType]  (a section heading has no exercise: nothing happens)
    assert window.stack.currentWidget() is window.home
    for cls in REGISTRY[:3]:
        window.open_exercise(cls)
        view = window.stack.currentWidget()
        assert isinstance(view, ExerciseView) and type(view.exercise) is cls
        assert window.title_label.text() == cls.name and window.nav.currentItem().data(Qt.ItemDataRole.UserRole) is cls
        settle()
        assert window.sidebar_width() > 0
    assert window.stack.count() == 3  # tiles, the empty workspace and one retained exercise


def test_the_exercise_list_can_be_collapsed_and_the_choice_is_remembered(window: MainWindow) -> None:
    """
    Check that the exercise list can be collapsed and the choice is remembered.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    window.open_exercise(REGISTRY[0])
    settle()
    open_width = window.sidebar_width()
    window.toggle_sidebar()
    settle()
    assert window.sidebar_width() == 0 and not window._sidebar_pref
    window.open_exercise(REGISTRY[1])  # the choice sticks while moving between exercises
    settle()
    assert window.sidebar_width() == 0
    window.toggle_sidebar()
    settle()
    assert window.sidebar_width() > 0 and window._sidebar_pref
    assert abs(window.sidebar_width() - open_width) < 60

    assert str(store().value("ui/sidebarCollapsed")) == "false"
    window.splitter.setSizes([0, 800])  # dragging the handle shut counts as the user's choice too
    window._sidebar_dragged()
    assert not window._sidebar_pref
    window.splitter.setSizes([250, 550])
    window._sidebar_dragged()
    assert window._sidebar_pref and window._sidebar_width == window.sidebar_width()


def test_going_home_closes_the_list(window: MainWindow) -> None:
    """
    Check that going home closes the list.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    window.open_exercise(REGISTRY[0])
    settle()
    window.show_home()
    settle()
    assert window.stack.currentWidget() is window.home and window.sidebar_width() == 0
    assert window.title_label.text() == MainWindow.APP_TITLE
    assert window.nav.currentItem() is not None  # retain the active exercise's selection
    assert window.stack.count() == 3


def test_the_statistics_and_database_pages_replace_the_current_page_and_back_returns(window: MainWindow) -> None:
    """
    Check that the statistics and database pages replace the current page and back returns.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    window.open_exercise(REGISTRY[0])
    exercise = window.stack.currentWidget()
    window.stats_button.click()
    assert window.title_label.text() == "Statistics" and window.stack.currentWidget() is window._overlay
    # noinspection PyUnresolvedReferences
    window._overlay.back.emit()
    assert window.stack.currentWidget() is exercise and window.title_label.text() == REGISTRY[0].name
    window.database_button.click()
    first = window._overlay
    assert window.title_label.text() == "Database"
    window.open_stats()  # opening another replaces the first
    assert window._overlay is not first and window.title_label.text() == "Statistics"
    window.close_overlay()
    window.close_overlay()  # closing with nothing open is harmless
    assert window._overlay is None and window.stack.currentWidget() is exercise


def test_switching_profile_changes_who_is_practicing_and_goes_home(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that switching profile changes who is practicing and goes home.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    # noinspection PyUnresolvedReferences
    db = window.learner.db
    ben = db.add_profile("Ben")

    class Chooses:
        """
        A stand-in for the profile dialog that picks another profile.
        """

        # noinspection PyShadowingNames
        def __init__(
            self,
            db: Database,
            *,
            current: object,
            parent: QWidget | None,
        ) -> None:
            """
            Build the stand-in.

            Parameters
            ----------
            db : Database
                The database.
            current : object
                The profile in use.
            parent : QWidget or None
                The owning widget.
            """
            del db, current, parent  # accepted to match what it stands in for, but not needed
            self.chosen = ben

        # noinspection PyMethodMayBeStatic
        def exec(self) -> QDialog.DialogCode:
            """
            Accept without showing anything.

            Returns
            -------
            QDialog.DialogCode
                Always Accepted.
            """
            return QDialog.DialogCode.Accepted

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw, "ProfileDialog", Chooses)
    window.open_exercise(REGISTRY[0])
    window.open_settings()
    window.switch_profile()
    assert window._settings is None
    # noinspection PyUnresolvedReferences
    assert window.learner.profile == ben and window.profile_action.text() == "Profile: Ben…"
    assert window.stack.currentWidget() is window.home

    assert int(store().value("profile/last")) == ben.id

    class Cancels(Chooses):
        """
        A stand-in for the profile dialog that is canceled.
        """

        def exec(self) -> QDialog.DialogCode:
            """
            Reject without showing anything.

            Returns
            -------
            QDialog.DialogCode
                Always Rejected.
            """
            return QDialog.DialogCode.Rejected

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw, "ProfileDialog", Cancels)
    window.switch_profile()
    # noinspection PyUnresolvedReferences
    assert window.learner.profile == ben  # nothing changed

    class SameAgain(Chooses):
        """
        A stand-in for the profile dialog that picks the profile already in use.
        """

        # noinspection PyMissingConstructor,PyShadowingNames
        def __init__(
            self,
            db: Database,
            *,
            current: object,
            parent: QWidget | None,
        ) -> None:
            """
            Build the stand-in.

            Parameters
            ----------
            db : Database
                The database.
            current : object
                The profile in use.
            parent : QWidget or None
                The owning widget.
            """
            del db, current, parent  # accepted to match what it stands in for, but not needed
            self.chosen = ben

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw, "ProfileDialog", SameAgain)
    window.open_exercise(REGISTRY[1])
    window.switch_profile()
    assert isinstance(window.stack.currentWidget(), ExerciseView)  # the same profile again: stay where you are


def test_changing_the_theme_in_settings_opens_a_fresh_window(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that changing the theme in settings rebuilds the window, once the settings are closed.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    rebuilt = []
    monkeypatch.setattr(window, "rebuild", lambda: rebuilt.append(1))
    window.open_settings()
    first = window._settings
    assert first is not None
    first.close()
    assert rebuilt == [] and not settings_are_open(window)  # nothing changed
    window.open_settings()
    second = window._settings
    assert second is not None
    second.theme_changed = True
    assert rebuilt == []  # the window is not rebuilt while the settings are still open
    second.close()
    assert rebuilt == [1] and not settings_are_open(window)


def settings_are_open(window: MainWindow) -> bool:
    """
    Say whether the window has its settings open.

    Parameters
    ----------
    window : MainWindow
        The window.

    Returns
    -------
    bool
        True if they are.
    """
    # noinspection PyProtectedMember
    return window._settings is not None


def test_the_settings_do_not_block_the_window(
    window: MainWindow,
    app: QApplication,
) -> None:
    """
    Check that the settings dialog is modeless, that opening it again brings the same one forward, and that the window works.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    app : QApplication
        The shared Qt application.
    """
    window.show()
    window.open_settings()
    dialog = window._settings
    assert dialog is not None and not dialog.isModal() and dialog.isVisible()
    window.open_settings()
    assert window._settings is dialog  # the same one, not a second
    window.open_exercise(REGISTRY[0])  # the window can be used while the settings are open
    assert window.title_label.text() == REGISTRY[0].name
    dialog.close()


def test_a_rebuilt_window_stays_where_it_was(
    app: QApplication,
    practiced_learner: Callable[..., Learner],
) -> None:
    """
    Check that a rebuilt window stays where it was, as the same window.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practiced_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    old = MainWindow(practiced_learner(5))
    old.setGeometry(
        120,
        80,
        900,
        600,
    )
    old.show()
    old.rebuild()
    assert old.isVisible() and old.geometry() == QRect(120, 80, 900, 600)  # the same window, in the same place
    old.close()


def test_a_rebuilt_window_shows_the_page_that_was_open(
    app: QApplication,
    practiced_learner: Callable[..., Learner],
) -> None:
    """
    Check that a rebuilt window shows the exercise, the lesson at its step, or the statistics that were open.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    practiced_learner : Callable[..., Learner]
        Builds a learner with a history of answers.
    """
    learner = practiced_learner(5)
    old = MainWindow(learner)
    old.open_exercise(REGISTRY[0])
    old.open_stats()
    old.rebuild()
    fresh = old
    assert fresh.title_label.text() == "Statistics"
    assert fresh.sidebar_width() > 0  # the list is in place at once, not sliding open
    fresh.close_overlay()
    assert fresh.title_label.text() == REGISTRY[0].name
    fresh.open_lessons("circle-of-fifths")
    page = fresh._overlay
    assert isinstance(page, LessonsPage)
    page.view.go(to=2)
    fresh.rebuild()
    page = fresh._overlay
    assert isinstance(page, LessonsPage) and page.view.current == 2
    fresh.close()


def test_restarting_starts_a_new_copy_then_quits(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that restarting starts a new copy then quits.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    started, quit_calls = [], []
    monkeypatch.setattr(mw.QProcess, "startDetached", lambda program, args: started.append((program, args)) or (True, 42))
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw.QApplication, "quit", lambda: quit_calls.append(1))
    window.restart_app()
    assert started and started[0][1] == ["-m", "alto"] and quit_calls == [1]
    monkeypatch.setattr(mw.QProcess, "startDetached", lambda program, args: (False, -1))
    monkeypatch.setattr(mw.QMessageBox, "warning", lambda *args: None)
    window.restart_app()
    assert quit_calls == [1]  # if the new copy could not start, this one stays open
    window.restart_app(quit_on_failure=True)
    assert quit_calls == [1, 1]


def test_a_packaged_build_restarts_by_starting_itself_with_no_arguments(
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that a packaged build, whose executable is Alto itself, is not given `-m alto` as arguments when it restarts.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    started: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(mw.QProcess, "startDetached", lambda program, args: started.append((program, args)) or (True, 42))
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(mw.QApplication, "quit", lambda: None)
    monkeypatch.setattr(mw.updates, "is_frozen", lambda: True)
    window.restart_app()
    assert started == [(sys.executable, [])]


def test_the_menu_has_no_home_entry_and_ends_with_restart_above_quit(window: MainWindow) -> None:
    """
    Check that the menu does not offer Home, does not start with a separator, and has Restart directly above Quit.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    entries = window.menu_button.menu().actions()
    names = [a.text() for a in entries if not a.isSeparator()]
    assert "Home" not in names and not entries[0].isSeparator()
    assert names[-4:] == ["Tools", "Help", "Restart", "Quit"]
    tools = next(action for action in entries if action.text() == "Tools")
    submenu = tools.menu()
    assert isinstance(submenu, QMenu) and not tools.icon().isNull()
    assert [a.text() for a in submenu.actions()] == [
        "Import backup…",
        "Export backup…",
        "Plugins…",
        "Anki Exporter",
        "Check for updates…",
    ]
    assert all(action not in entries for action in submenu.actions())
    plugins = next(action for action in submenu.actions() if action.text() == "Plugins…")
    assert not plugins.icon().isNull()
    assert entries[-2].text() == "Restart" and entries[-1].text() == "Quit"  # no separator between them
    assert entries[-3].isSeparator()  # separate Restart and Quit from Help


def test_exporter_flashcards_are_outlined_in_both_themes(window: MainWindow, request: pytest.FixtureRequest) -> None:
    """
    Check the icon at menu size after switching between light and dark palettes.

    Parameters
    ----------
    window : MainWindow
        Window containing the Tools menu.
    request : pytest.FixtureRequest
        Restores the system theme after the comparison.
    """
    request.addfinalizer(lambda: apply_theme("system"))
    menu = next(action.menu() for action in window.menu_button.menu().actions() if action.text() == "Tools")
    assert isinstance(menu, QMenu)
    action = next(action for action in menu.actions() if action.text() == "Anki Exporter")
    for theme, ink in (("studio_dark", "#ffffff"), ("studio", "#000000")):
        apply_theme(theme)
        menu.popup(window.pos())
        image = action.icon().pixmap(18, 18).toImage()
        assert image.pixelColor(image.width() // 2, image.height() // 2).alpha() == 0
        colors = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
        assert {color.name() for color in colors if color.alpha() > 127} == {ink}
        menu.hide()


def test_help_report_an_issue_opens_the_github_issue_tracker(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Trigger the Help menu action and check the URL sent to the default browser.

    Parameters
    ----------
    window : MainWindow
        The window containing the Help menu.
    monkeypatch : pytest.MonkeyPatch
        Captures the URL passed to the desktop.
    """
    opened: list[str] = []
    monkeypatch.setattr(mw.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    help_menu = next(action.menu() for action in window.menu_button.menu().actions() if action.text() == "Help")
    assert isinstance(help_menu, QMenu)
    actions = help_menu.actions()
    index = [action.text() for action in actions].index("Report an issue")
    assert actions[index + 1].text() == "GitHub"
    actions[index].trigger()
    assert opened == ["https://github.com/altosaurus/alto/issues"]


@pytest.mark.parametrize("installed", [True, False])
def test_help_about_shows_the_development_status(window: MainWindow, monkeypatch: pytest.MonkeyPatch, installed: bool) -> None:
    """
    Open About through Help and check the status even when running without package metadata.

    Parameters
    ----------
    window : MainWindow
        The window containing the Help menu.
    monkeypatch : pytest.MonkeyPatch
        Captures the dialog text and simulates unavailable package metadata.
    installed : bool
        Whether the dialog can read Alto's package metadata.
    """
    if not installed:

        def missing_metadata(name: str) -> None:
            """
            Simulate a lookup for an uninstalled package.

            Parameters
            ----------
            name : str
                The requested distribution name.

            Raises
            ------
            PackageNotFoundError
                The distribution has no installed metadata.
            """
            raise mw.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(mw.metadata, "metadata", missing_metadata)
    messages: list[str] = []
    monkeypatch.setattr(mw.QMessageBox, "about", lambda parent, title, text: messages.append(text))
    help_menu = next(action.menu() for action in window.menu_button.menu().actions() if action.text() == "Help")
    assert isinstance(help_menu, QMenu)
    next(action for action in help_menu.actions() if action.text() == "About").trigger()
    assert len(messages) == 1
    assert f"Development status: {'Alpha' if installed else 'Unknown'}" in messages[0]


def test_the_menu_has_the_shortcuts(window: MainWindow) -> None:
    """
    Check that the menu has the shortcuts.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    actions = {a.text(): a for a in window.menu_button.menu().actions() if a.text()}
    assert actions["Settings…"].shortcut() == QKeySequence("Ctrl+Alt+S")
    assert actions["Restart"].shortcut() == QKeySequence("Ctrl+R")
    assert {
        "Quit",
    } <= set(actions)
    window.stats_button.click()
    assert window._overlay is not None
    window.close_overlay()
    window.database_button.click()
    assert window._overlay is not None
    window.close_overlay()


def test_the_exercise_list_item_is_a_list_widget_entry(window: MainWindow) -> None:
    """
    Check that the exercise list item is a list widget entry.

    Parameters
    ----------
    window : MainWindow
        The main window under test.
    """
    assert isinstance(window.nav, QListWidget) and QSignalSpy(window.nav.itemClicked).isValid()
    row = next(window.nav.item(i) for i in range(window.nav.count()) if window.nav.item(i).data(Qt.ItemDataRole.UserRole))
    window.nav.itemClicked.emit(row)
    assert isinstance(window.stack.currentWidget(), ExerciseView)


# -- starting the app -----------------------------------------------------------------------------------------------


class FakeApp:
    """Stands in for the QApplication that main() would create: the test run already has one."""

    def __init__(self, argv: list[str]) -> None:
        """
        Build the stand-in for the application.

        Parameters
        ----------
        argv : list of str
            The command line, ignored.
        """
        del argv  # accepted to match what it stands in for, but not needed
        self.calls = []

    def __getattr__(self, name: str) -> Callable[..., int | None]:
        """
        Make any method of the application do nothing but note that it was called.

        Parameters
        ----------
        name : str
            The method asked for.

        Returns
        -------
        Callable
            `exec` returns 0; every other method records its name.
        """
        if name == "exec":
            return lambda: 0
        return lambda *a: self.calls.append(name)


def test_the_app_opens_a_window_for_the_chosen_profile(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Check that the app opens a window for the chosen profile.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    broken = tmp_path / "plugins" / "mistyped"
    broken.mkdir(parents=True)
    (broken / "pack.json").write_text("{")
    warnings = []
    monkeypatch.setattr(entry.QMessageBox, "warning", lambda parent, title, message: warnings.append(message))
    path = tmp_path / "alto.db"
    db = Database(path)
    db_profile = db.add_profile("Ada")
    db.close()
    monkeypatch.setattr(entry, "database_path", lambda: path)
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "QApplication", FakeApp)
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "startup_profile", lambda db: db.profile(db_profile.id))
    shown = []
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry.MainWindow, "show", lambda self: shown.append(self))
    assert entry.main() == 0
    assert len(warnings) == 1 and "mistyped/pack.json" in warnings[0]
    assert len(shown) == 1 and isinstance(shown[0].learner, Learner) and shown[0].learner.profile == db_profile
    shown[0].close()


def test_asking_for_the_version_prints_it_and_opens_nothing(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Check that `alto --version` prints the version and exits with 0 without making an application or a window.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces the command line and the application.
    capsys : pytest.CaptureFixture
        Captures what is printed.
    """

    def refuse(*_args: object) -> None:
        """
        Fail the test: nothing should be built.

        Parameters
        ----------
        *_args : object
            Whatever was asked for.

        Raises
        ------
        AssertionError
            Always.
        """
        raise AssertionError("--version must not open anything")

    monkeypatch.setattr(sys, "argv", ["alto", "--version"])
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "QApplication", refuse)
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "startup_profile", refuse)
    assert entry.main() == 0
    assert capsys.readouterr().out == f"Alto {app_version()}\n"
    monkeypatch.setattr(sys, "stdout", None)  # a program with no console, as the Windows build is
    assert entry.main() == 0


def test_the_self_test_says_ok_and_exits_with_0_or_names_the_problem_and_exits_with_1(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Check what the build runs on a packaged copy: `alto --self-test` opens nothing, prints `ok`, and fails if something is wrong.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces the command line, the application and the keys in the code.
    capsys : pytest.CaptureFixture
        Captures what is printed.
    """
    monkeypatch.setattr(sys, "argv", ["alto", "--self-test"])
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "QApplication", lambda *_args: pytest.fail("--self-test must not open anything"))
    assert entry.main() == 0
    assert capsys.readouterr().out == "ok\n"
    monkeypatch.setattr(updates, "UPDATE_PUBLIC_KEYS", ("not a key",))
    assert entry.main() == 1
    assert "not a valid Ed25519 key" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdout", None)  # a program with no console, as the Windows build is
    assert entry.main() == 1


def test_the_app_quits_quietly_if_no_profile_is_chosen(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Check that the app quits quietly if no profile is chosen.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    """
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "QApplication", FakeApp)
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(entry, "startup_profile", lambda db: None)
    assert entry.main() == 0


def retained_exercise_page(window: MainWindow) -> ExerciseView:
    """
    Return the retained exercise view for a window under test.

    Parameters
    ----------
    window : MainWindow
        The window with an open exercise.

    Returns
    -------
    ExerciseView
        The retained exercise view.
    """
    # noinspection PyProtectedMember
    page = window._exercise_page
    assert isinstance(page, ExerciseView)
    return page


@pytest.mark.parametrize("opened,page_index", [(False, 0), (True, 0), (True, 2)])
def test_theme_changes_preserve_the_exercise_settings_pane(app: QApplication, opened: bool, page_index: int) -> None:
    """
    Keep exercise settings open or closed and retain their page and scroll position after closing theme settings.

    Parameters
    ----------
    app : QApplication
        The shared application.
    opened : bool
        Whether the exercise settings pane starts open.
    page_index : int
        The settings menu or interval page to preserve.
    """
    window = MainWindow()
    window.resize(1100, 750)
    window.show()
    cfg = settings.keyboard_intervals
    cfg.low, cfg.high = settings.KEYBOARD_FULL
    save_keyboard_intervals(cfg)
    window.open_exercise(KeyboardIntervals)
    view = retained_exercise_page(window)
    assert isinstance(view, ExerciseView) and view.gear is not None
    panel = view.settings_panel
    assert isinstance(panel, KeyboardIntervalSettingsPanel)
    panel.stack.setCurrentIndex(page_index)
    view.gear.setChecked(opened)
    if opened:
        view._pane_anim.setCurrentTime(view._pane_anim.duration())
    app.processEvents()
    scroll = panel.stack.currentWidget().findChild(QScrollArea)
    if scroll is not None:
        scroll.verticalScrollBar().setValue(180)
    before = view.settings_state()
    assert before is not None
    if page_index == 2:
        assert before[2] > 0
    try:
        for theme in ("dark", "light"):
            window.open_settings()
            dialog = window._settings
            assert dialog is not None
            dialog.choose_theme(theme)
            dialog.close()
            app.processEvents()
            fresh = retained_exercise_page(window)
            assert fresh is not view
            assert fresh.settings_state() == before
            assert fresh.gear is not None and fresh.gear.isChecked() == opened
            assert fresh.pane.isVisible() == opened
            assert fresh.pane.maximumWidth() == (fresh.PANE_WIDTH if opened else 0)
            view = fresh
    finally:
        window.close()
        apply_theme("system")
