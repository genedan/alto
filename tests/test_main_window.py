"""The home screen, the main window with its exercise list and menu, and starting the app."""

from typing import Any, cast

import pytest
from alto.exercises import REGISTRY
from alto.exercises.base import Exercise, Question
from alto.learning import Database, Learner
from alto.ui import main_window as mw
from alto.ui.exercise_view import ExerciseView
from alto.ui.home import CARD_W, EXERCISE_ICONS, ExerciseCard, HomePage
from alto.ui.main_window import MainWindow
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QListWidget

# -- the home screen ------------------------------------------------------------------------------------------------


def test_the_home_screen_has_a_card_for_each_exercise_and_reports_the_one_clicked(app):
    home = HomePage(REGISTRY)
    assert len(home.cards) == len(REGISTRY) and all(isinstance(c, ExerciseCard) for c in home.cards)
    chosen = []
    home.exercise_chosen.connect(chosen.append)
    home.cards[2].click()
    assert chosen == [REGISTRY[2]]
    assert home.cards[0].toolTip() == REGISTRY[0].description


def test_the_cards_are_laid_out_in_as_many_columns_as_fit(app):
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
        rows = [layout for item in items if item is not None and (layout := item.layout()) is not None]
        assert sum(r.count() - 2 for r in rows) == len(REGISTRY)  # every card is in a row (less the two stretches)
        assert home.grab().width() == width
    assert widths[300] == 1 and widths[300] <= widths[700] <= widths[1100] <= widths[2000]
    assert widths[2000] >= 7 and widths[1100] >= 4  # a wide window holds the whole row of cards
    home.resize(2000, 600)
    before = home._columns
    home._reflow()  # nothing changes when the width has not
    assert home._columns == before


def test_an_exercise_with_no_icon_of_its_own_gets_the_default(app):
    class Odd(Exercise):
        name, category, description = "Odd", "Notation", "Something new."

        def generate(self, rng):
            return Question("?", ["a"], "a")

    assert "Odd" not in EXERCISE_ICONS
    card = ExerciseCard(Odd)
    assert card.size() == QSize(CARD_W, card.height()) and card.grab().width() == CARD_W
    labels = [label.text() for label in card.findChildren(QLabel)]
    assert "<b>Odd</b>" in labels and "NOTATION" in labels


# -- the main window ------------------------------------------------------------------------------------------------


@pytest.fixture
def window(
    app,
    practised_learner,
):
    w = MainWindow(practised_learner(10))
    w.show()
    yield w
    w.close()
    w.deleteLater()
    QApplication.sendPostedEvents(None, 0)


def settle(ms=260):
    QTest.qWait(ms)


def test_the_window_starts_on_the_home_screen_with_a_list_of_exercises(window):
    assert window.windowTitle() == MainWindow.APP_TITLE and window.stack.currentWidget() is window.home
    assert window.sidebar_width() == 0  # the start screen has no list
    entries = [window.nav.item(i) for i in range(window.nav.count())]
    classes = [e.data(Qt.ItemDataRole.UserRole) for e in entries if e.data(Qt.ItemDataRole.UserRole)]
    assert classes == list(REGISTRY)
    headings = [e.text() for e in entries if not e.data(Qt.ItemDataRole.UserRole)]
    assert "NOTATION" in headings and all(not (e.flags() & Qt.ItemFlag.ItemIsSelectable) for e in entries if e.text() in headings)
    assert window.stats_button.isVisibleTo(window) and window.database_button.isVisibleTo(window)
    assert window.profile_action.text() == "Profile: Ada…"


def test_each_exercise_in_the_list_sits_under_its_own_category_heading(window):
    heading = None
    shown = []
    for i in range(window.nav.count()):
        entry = window.nav.item(i)
        cls = entry.data(Qt.ItemDataRole.UserRole)
        if cls is None:
            heading = entry.text()
            shown.append(heading)
        else:
            assert heading == cls.category.upper(), f"{cls.name} is under {heading}"
    assert len(shown) == len(set(shown))  # each heading appears once


def test_without_a_profile_nothing_is_recorded_and_the_history_buttons_are_hidden(app):
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


def test_choosing_an_exercise_shows_it_opens_the_list_and_titles_the_window(window):
    window.open_exercise(None)  # a section heading has no exercise: nothing happens
    assert window.stack.currentWidget() is window.home
    for cls in REGISTRY[:3]:
        window.open_exercise(cls)
        view = window.stack.currentWidget()
        assert isinstance(view, ExerciseView) and type(view.exercise) is cls
        assert window.title_label.text() == cls.name and window.nav.currentItem().data(Qt.ItemDataRole.UserRole) is cls
        settle()
        assert window.sidebar_width() > 0
    assert window.stack.count() == 2  # the home screen and the one exercise: each is dropped when the next opens


def test_the_exercise_list_can_be_collapsed_and_the_choice_is_remembered(window):
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
    from alto.ui.store import store

    assert str(store().value("ui/sidebarCollapsed")) == "false"
    window.splitter.setSizes([0, 800])  # dragging the handle shut counts as the user's choice too
    window._sidebar_dragged()
    assert not window._sidebar_pref
    window.splitter.setSizes([250, 550])
    window._sidebar_dragged()
    assert window._sidebar_pref and window._sidebar_width == window.sidebar_width()


def test_going_home_closes_the_list(window):
    window.open_exercise(REGISTRY[0])
    settle()
    window.show_home()
    settle()
    assert window.stack.currentWidget() is window.home and window.sidebar_width() == 0
    assert window.title_label.text() == MainWindow.APP_TITLE and window.nav.currentItem() is None
    assert window.stack.count() == 1


def test_the_statistics_and_database_pages_replace_the_current_page_and_back_returns(window):
    window.open_exercise(REGISTRY[0])
    exercise = window.stack.currentWidget()
    window.stats_button.click()
    assert window.title_label.text() == "Statistics" and window.stack.currentWidget() is window._overlay
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


def test_switching_profile_changes_who_is_practising_and_goes_home(
    window,
    monkeypatch,
):
    db = window.learner.db
    ben = db.add_profile("Ben")

    class Chooses:
        def __init__(
            self,
            db,
            current,
            parent,
        ):
            self.chosen = ben

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(mw, "ProfileDialog", Chooses)
    window.open_exercise(REGISTRY[0])
    window.switch_profile()
    assert window.learner.profile == ben and window.profile_action.text() == "Profile: Ben…"
    assert window.stack.currentWidget() is window.home
    from alto.ui.store import store

    assert int(store().value("profile/last")) == ben.id

    class Cancels(Chooses):
        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(mw, "ProfileDialog", Cancels)
    window.switch_profile()
    assert window.learner.profile == ben  # nothing changed

    class SameAgain(Chooses):
        def __init__(
            self,
            db,
            current,
            parent,
        ):
            self.chosen = ben

    monkeypatch.setattr(mw, "ProfileDialog", SameAgain)
    window.open_exercise(REGISTRY[1])
    window.switch_profile()
    assert isinstance(window.stack.currentWidget(), ExerciseView)  # the same profile again: stay where you are


def test_changing_the_theme_in_settings_opens_a_fresh_window(
    window,
    monkeypatch,
):
    rebuilt = []
    monkeypatch.setattr(window, "rebuild", lambda: rebuilt.append(1))

    class Dialog:
        theme_changed = False

        def __init__(self, parent):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr(mw, "AppSettingsDialog", Dialog)
    window.open_settings()
    assert rebuilt == []
    Dialog.theme_changed = True
    window.open_settings()
    assert rebuilt == [1]


def test_a_rebuilt_window_takes_the_old_ones_place(
    app,
    practised_learner,
):
    old = MainWindow(practised_learner(5))
    old.setGeometry(
        120,
        80,
        900,
        600,
    )
    old.show()
    old.rebuild()
    fresh = cast(Any, QApplication.instance()).main_window  # set by rebuild()
    assert fresh is not old and fresh.learner is old.learner and fresh.geometry().size() == old.geometry().size()
    assert fresh.isVisible() and not old.isVisible()
    fresh.close()


def test_restarting_starts_a_new_copy_then_quits(
    window,
    monkeypatch,
):
    started, quit_calls = [], []
    monkeypatch.setattr(mw.QProcess, "startDetached", lambda program, args: started.append((program, args)) or True)
    monkeypatch.setattr(mw.QApplication, "quit", lambda: quit_calls.append(1))
    window.restart_app()
    assert started and started[0][1] == ["-m", "alto"] and quit_calls == [1]
    monkeypatch.setattr(mw.QProcess, "startDetached", lambda program, args: False)
    window.restart_app()
    assert quit_calls == [1]  # if the new copy could not start, this one stays open


def test_the_menu_has_the_shortcuts(window):
    actions = {a.text(): a for a in window.menu_button.menu().actions() if a.text()}
    assert actions["Settings…"].shortcut() == QKeySequence("Ctrl+Alt+S")
    assert actions["Restart"].shortcut() == QKeySequence("Ctrl+R")
    assert {
        "Home",
        "Statistics",
        "Browse database",
        "Quit",
    } <= set(actions)
    actions["Home"].trigger()
    assert window.stack.currentWidget() is window.home
    actions["Statistics"].trigger()
    assert window._overlay is not None
    window.close_overlay()
    actions["Browse database"].trigger()
    assert window._overlay is not None
    window.close_overlay()


def test_the_exercise_list_item_is_a_list_widget_entry(window):
    assert isinstance(window.nav, QListWidget) and QSignalSpy(window.nav.itemClicked).isValid()
    entry = next(window.nav.item(i) for i in range(window.nav.count()) if window.nav.item(i).data(Qt.ItemDataRole.UserRole))
    window.nav.itemClicked.emit(entry)
    assert isinstance(window.stack.currentWidget(), ExerciseView)


# -- starting the app -----------------------------------------------------------------------------------------------


class FakeApp:
    """Stands in for the QApplication that main() would create: the test run already has one."""

    def __init__(self, argv):
        self.calls = []

    def __getattr__(self, name):
        if name == "exec":
            return lambda: 0
        return lambda *a: self.calls.append(name)


def test_the_app_opens_a_window_for_the_chosen_profile(
    app,
    monkeypatch,
    tmp_path,
):
    from alto import __main__ as entry

    db_profile = Database().add_profile("Ada")
    monkeypatch.setattr(entry, "QApplication", FakeApp)
    monkeypatch.setattr(entry, "startup_profile", lambda db: db_profile)
    shown = []
    monkeypatch.setattr(entry.MainWindow, "show", lambda self: shown.append(self))
    assert entry.main() == 0
    assert len(shown) == 1 and isinstance(shown[0].learner, Learner) and shown[0].learner.profile == db_profile
    shown[0].close()


def test_the_app_quits_quietly_if_no_profile_is_chosen(
    app,
    monkeypatch,
):
    from alto import __main__ as entry

    monkeypatch.setattr(entry, "QApplication", FakeApp)
    monkeypatch.setattr(entry, "startup_profile", lambda db: None)
    assert entry.main() == 0
