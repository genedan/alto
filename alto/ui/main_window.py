"""
The main window: a menu, the exercise list on the left that can be collapsed, and the page on the right.

The page is the start screen, an exercise, or (while it is open) the statistics or the database browser.

Examples
--------
>>> window = MainWindow()
>>> window.title_label.text()
'Alto - Music Theory'
"""

from __future__ import annotations

import sys

from PySide6.QtCore import (
    QProcess,
    QSize,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QFont,
    QKeySequence,
    QPalette,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from alto.exercises import REGISTRY
from alto.exercises.base import Exercise
from alto.learning import Learner
from alto.ui import (
    backup_flow,
    icons,
)
from alto.ui.app_settings import AppSettingsDialog
from alto.ui.colors import blend
from alto.ui.database_page import DatabasePage
from alto.ui.exercise_view import ExerciseView
from alto.ui.home import (
    EXERCISE_ICONS,
    HomePage,
)
from alto.ui.icons import svg_icon
from alto.ui.instrument_picker import load_instrument
from alto.ui.keyboard_styles import load_style as load_keyboard_style
from alto.ui.notation import load_style as load_notation_style
from alto.ui.profile_dialog import (
    ProfileDialog,
    remember_profile,
)
from alto.ui.settings_panel import (
    load_arpeggio,
    load_construction,
    load_key_signatures,
    load_keyboard,
    load_note_names,
)
from alto.ui.stats_dialog import StatsPage
from alto.ui.store import (
    int_value,
    store,
    text_value,
)
from alto.ui.theme import (
    apply_theme,
    saved_theme,
)


class MainWindow(QMainWindow):
    """
    The application window.

    Attributes
    ----------
    SIDEBAR_MIN : int
        The narrowest the exercise list can be before it collapses, in pixels.
    SIDEBAR_DEFAULT : int
        The list's width the first time.
    APP_TITLE : str
        The title shown on the start screen.
    learner : Learner or None
        Who is practising, and their history; None practises without recording.
    nav : QListWidget
        The exercise list.
    stack : QStackedWidget
        The pages: the start screen, then exercises and the statistics or database while they are open.
    home : HomePage
        The start screen.
    splitter : QSplitter
        Holds the list and the pages, so the list can be dragged narrower or wider.
    title_label : QLabel
        The title in the top bar.

    Examples
    --------
    >>> from alto.exercises.library import NoteNames
    >>> window = MainWindow()
    >>> window.open_exercise(NoteNames)
    >>> window.title_label.text()
    'Note Identification'
    >>> window.show_home()
    """

    SIDEBAR_MIN, SIDEBAR_DEFAULT = 170, 240
    APP_TITLE = "Alto - Music Theory"

    def __init__(self, learner: Learner | None = None) -> None:
        """
        Build the window and load every saved setting.

        Parameters
        ----------
        learner : Learner or None, default None
            Who is practising. Without one, nothing is recorded and the statistics buttons are hidden.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> window_ = MainWindow(Learner(db, profile=db.add_profile("Ada")))
        >>> window_.stats_button.isVisibleTo(window_)
        True
        >>> MainWindow().stats_button.isVisibleTo(window_)  # no profile, no statistics
        False
        """
        super().__init__()
        self._overlay: StatsPage | DatabasePage | None = None  # the statistics or database page, while one is showing
        self._overlay_return: tuple[QWidget | None, str] | None = None  # the page and title to go back to
        self.learner = learner  # who is practising, and their history; None practises without recording
        self.setWindowTitle(self.APP_TITLE)
        self.resize(1000, 640)
        self.nav = QListWidget()  # the exercise list: section labels and exercises, as a flat sidebar
        self.nav.setObjectName("nav")  # styled in style.py
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setMinimumWidth(self.SIDEBAR_MIN)
        self.nav.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.stack = QStackedWidget()
        self.home = HomePage(REGISTRY)  # start screen with a button for every exercise
        self.home.exercise_chosen.connect(self.open_exercise)
        self.stack.addWidget(self.home)

        self._items: dict[type, QListWidgetItem] = {}
        pal = self.palette()
        ink, window = pal.color(QPalette.ColorRole.Text), pal.color(QPalette.ColorRole.Window)
        section_colour = blend(ink, b=window, t=0.5)
        section_font = QFont()
        section_font.setPixelSize(10)
        section_font.setBold(True)
        section_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.3)
        seen: set[str] = set()
        for cls in REGISTRY:
            if cls.category not in seen:
                seen.add(cls.category)
                label = QListWidgetItem(cls.category.upper())
                label.setFlags(Qt.ItemFlag.NoItemFlags)  # a section label: not selectable, no hover highlight
                label.setFont(section_font)
                label.setForeground(section_colour)
                label.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
                label.setSizeHint(QSize(0, 40))
                self.nav.addItem(label)
            item = QListWidgetItem(
                svg_icon(EXERCISE_ICONS.get(cls.__name__, icons.EXERCISE_NOTE_NAMES), color=ink, size=20),
                cls.name,
            )
            item.setData(Qt.ItemDataRole.UserRole, cls)
            item.setToolTip(cls.description)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
            self._items[cls] = item
        # noinspection PyShadowingNames
        self.nav.itemClicked.connect(lambda item: self.open_exercise(item.data(Qt.ItemDataRole.UserRole)))

        # Hamburger menu above the exercise list (replaces the menu bar).
        self.menu_button = QToolButton()
        self.menu_button.setText("☰")
        self.menu_button.setToolTip("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.setStyleSheet("QToolButton { font-size: 16pt; } QToolButton::menu-indicator { image: none; }")
        menu = QMenu(self.menu_button)
        # A transparent, frameless popup lets the stylesheet's rounded corners show without a square backdrop.
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        glyph = self.menu_button.palette().color(QPalette.ColorRole.WindowText)  # menu icons share the text colour
        home = menu.addAction(svg_icon(icons.HOME, color=glyph, size=18), "Home")
        home.triggered.connect(self.show_home)
        menu.addSeparator()
        restart = menu.addAction(svg_icon(icons.RESTART, color=glyph, size=18), "Restart")
        restart.setShortcut(QKeySequence("Ctrl+R"))
        restart.triggered.connect(self.restart_app)
        stats_action = menu.addAction(svg_icon(icons.CHART, color=glyph, size=18), "Statistics")
        stats_action.triggered.connect(self.open_stats)
        database_action = menu.addAction(svg_icon(icons.DATABASE, color=glyph, size=18), "Browse database")
        database_action.triggered.connect(self.open_database)
        self.profile_action = menu.addAction(svg_icon(icons.PROFILE, color=glyph, size=18), "")
        self.profile_action.triggered.connect(self.switch_profile)
        settings_action = menu.addAction(svg_icon(icons.GEAR, color=glyph, size=18), "Settings…")
        settings_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        settings_action.triggered.connect(self.open_settings)
        menu.addSeparator()
        self.export_action = menu.addAction(svg_icon(icons.EXPORT, color=glyph, size=18), "Export backup…")
        self.export_action.setToolTip("Save everything Alto keeps (profiles, history and settings) to one file")
        self.export_action.triggered.connect(self.export_backup)
        self.import_action = menu.addAction(svg_icon(icons.IMPORT, color=glyph, size=18), "Import backup…")
        self.import_action.setToolTip("Replace everything with a backup made earlier")
        self.import_action.triggered.connect(self.import_backup)
        self._show_profile()  # shows or hides the three actions that need a profile
        menu.addSeparator()
        quit_action = menu.addAction(svg_icon(icons.QUIT, color=glyph, size=18), "Quit")
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.quit)
        self.menu_button.setMenu(menu)
        self.addAction(settings_action)
        self.addAction(restart)  # keep the shortcuts working while the menu is closed
        self.addAction(quit_action)

        load_note_names()
        load_keyboard()
        load_construction()
        load_arpeggio()
        load_key_signatures()
        load_instrument()
        load_notation_style()
        load_keyboard_style()

        # The list and the exercise sit in a splitter: drag the handle to resize, or drag the list
        # narrower than its minimum to collapse it.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.nav)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self._sidebar_width = int_value(store(), key="ui/sidebarWidth", default=self.SIDEBAR_DEFAULT)
        # Whether the user wants the list shown on exercise pages. The start screen never shows it.
        self._sidebar_pref = text_value(store(), key="ui/sidebarCollapsed", default="false").lower() != "true"
        self._sidebar_anim: QVariantAnimation | None = None
        self.splitter.splitterMoved.connect(self._sidebar_dragged)
        self.splitter.setSizes([0, 10_000])  # start on the home screen, with no list
        self.splitter.handle(1).setEnabled(False)
        self._update_sidebar_button()

        root = QWidget()
        lay = QVBoxLayout(root)
        # Top bar: menu buttons on the left, the exercise title centred. Equal-stretch outer columns
        # keep the title centred however wide the buttons are.
        self.title_label = QLabel(self.APP_TITLE)
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        buttons = QHBoxLayout()
        buttons.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        buttons.addWidget(self.menu_button)
        self.stats_button = QToolButton()  # a quick way to the statistics, beside the menu
        self.stats_button.setIcon(svg_icon(icons.CHART, color=self.palette().color(QPalette.ColorRole.WindowText)))
        self.stats_button.setIconSize(QSize(22, 22))
        self.stats_button.setAutoRaise(True)
        self.stats_button.setToolTip("Statistics")
        self.stats_button.setVisible(self.learner is not None)
        self.stats_button.clicked.connect(self.open_stats)
        buttons.addWidget(self.stats_button)
        self.database_button = QToolButton()
        self.database_button.setIcon(svg_icon(icons.DATABASE, color=self.palette().color(QPalette.ColorRole.WindowText)))
        self.database_button.setIconSize(QSize(22, 22))
        self.database_button.setAutoRaise(True)
        self.database_button.setToolTip("Browse the database")
        self.database_button.setVisible(self.learner is not None)
        self.database_button.clicked.connect(self.open_database)
        buttons.addWidget(self.database_button)
        bar = QGridLayout()
        bar.addLayout(
            buttons,
            0,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        bar.addWidget(
            self.title_label,
            0,
            1,
            Qt.AlignmentFlag.AlignCenter,
        )
        bar.setColumnStretch(0, 1)
        bar.setColumnStretch(2, 1)
        lay.addLayout(bar)
        lay.addWidget(self.splitter, 1)
        self.setCentralWidget(root)

    # exercise list: collapse / resize
    def sidebar_width(self) -> int:
        """
        Return how wide the exercise list is.

        Returns
        -------
        int
            The width in pixels; 0 when the list is collapsed, as it always is on the start screen.

        Examples
        --------
        >>> MainWindow().sidebar_width()
        0
        """
        return self.splitter.sizes()[0]

    def _sidebar_dragged(self, *_: object) -> None:
        """
        Remember the list's new width after the splitter handle is dragged.

        Parameters
        ----------
        *_ : object
            What the splitter's signal passes (the handle's position and index); not used.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._sidebar_dragged(0, 1)  # the list is collapsed, so it is remembered as hidden
        >>> window._sidebar_pref
        False
        """
        width = self.sidebar_width()
        if width > 0:
            self._sidebar_width = width
        self._sidebar_pref = width > 0
        self._save_sidebar()
        self._update_sidebar_button()

    def _update_sidebar_button(self) -> None:
        """
        Keep every page's toggle button in step with the list.

        The buttons live in the exercise headers.

        Examples
        --------
        >>> MainWindow()._update_sidebar_button()
        """
        is_open = self.sidebar_width() > 0
        for i in range(self.stack.count()):
            button = getattr(self.stack.widget(i), "sidebar_button", None)
            if button is not None:
                # noinspection PyUnresolvedReferences
                button.set_open(is_open)

    def _save_sidebar(self) -> None:
        """
        Save the list's width and whether the user wants it shown.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._sidebar_pref = False
        >>> window._save_sidebar()
        >>> str(store().value("ui/sidebarCollapsed"))
        'true'
        """
        s = store()
        s.setValue("ui/sidebarWidth", self._sidebar_width)
        s.setValue("ui/sidebarCollapsed", "false" if self._sidebar_pref else "true")

    def toggle_sidebar(self) -> None:
        """
        Slide the list closed, or back open, for the user's button. The choice is remembered for next time.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.toggle_sidebar()
        >>> window._sidebar_pref
        True
        """
        self._set_sidebar(self.sidebar_width() == 0, user=True)

    def _set_sidebar(
        self,
        show: bool,
        *,
        user: bool = False,
    ) -> None:
        """
        Slide the exercise list open or closed.

        Only a user's choice changes the saved preference.

        Parameters
        ----------
        show : bool
            True to open the list, False to close it.
        user : bool, default False
            True if the user asked for this (with the button), so it is remembered. Keyword-only.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._set_sidebar(True, user=True)
        >>> window._sidebar_pref
        True
        >>> window._set_sidebar(False)  # the start screen hides it without changing the preference
        >>> window._sidebar_pref
        True
        """
        if self._sidebar_anim:
            self._sidebar_anim.stop()
        start = self.sidebar_width()
        if start > 0:
            self._sidebar_width = start
        end = self._sidebar_width if show else 0
        if user:
            self._sidebar_pref = show
        if start == end:
            return
        total = sum(self.splitter.sizes())
        self.nav.setMinimumWidth(0)  # let the width pass through values below the minimum while animating
        anim = self._sidebar_anim = QVariantAnimation(self)
        anim.setDuration(180)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.valueChanged.connect(lambda w: self.splitter.setSizes([int(w), total - int(w)]))

        def done() -> None:
            """
            Finish the slide: restore the list's minimum width, set its final size and save it.

            Examples
            --------
            >>> done()  # doctest: +SKIP
            """
            self.nav.setMinimumWidth(self.SIDEBAR_MIN)
            self.splitter.setSizes([end, total - end])
            self._save_sidebar()
            self._update_sidebar_button()

        anim.finished.connect(done)
        anim.start()

    def open_exercise(self, cls: type[Exercise] | None) -> None:
        """
        Show an exercise.

        Parameters
        ----------
        cls : type of Exercise or None
            The exercise class; None (a category heading in the list, which has no class) does nothing.

        Examples
        --------
        >>> from alto.exercises.library import KeySignatures
        >>> window = MainWindow()
        >>> window.open_exercise(KeySignatures)
        >>> window.title_label.text()
        'Key signatures'
        """
        if cls is None:
            return
        self.close_overlay()
        old = self.stack.currentWidget()
        view = ExerciseView(cls(), learner=self.learner)
        view.sidebar_button.clicked.connect(self.toggle_sidebar)
        self.title_label.setText(cls.name)
        self.nav.setCurrentItem(self._items[cls])
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self._update_sidebar_button()
        self._drop(old)
        self.splitter.handle(1).setEnabled(True)
        if self._sidebar_pref:
            self._set_sidebar(True)  # the list appears once an exercise is chosen

    def open_settings(self) -> None:
        """
        Open the application settings, and rebuild the window if the theme was changed.

        Examples
        --------
        >>> MainWindow().open_settings()  # doctest: +SKIP
        """
        dialog = AppSettingsDialog(self)
        dialog.exec()
        if dialog.theme_changed:
            self.rebuild()

    def rebuild(self) -> None:
        """
        Open a fresh window in the same place, so every icon and colour is drawn in the new theme.

        Examples
        --------
        >>> MainWindow().rebuild()  # doctest: +SKIP
        """
        fresh = type(self)(self.learner)
        fresh.setGeometry(self.geometry())
        fresh.setWindowState(self.windowState())
        app = QApplication.instance()
        if app is not None:
            # noinspection PyUnresolvedReferences
            app.main_window = fresh  # pyright: ignore[reportAttributeAccessIssue]  (see alto/__main__.py)
        fresh.show()
        self.close()

    def _show_profile(self) -> None:
        """
        Show the profile's name in the menu, or hide that entry when there is no profile.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
        >>> window.profile_action.text()
        'Profile: Ada…'
        """
        for action in (self.profile_action, self.export_action, self.import_action):
            action.setVisible(self.learner is not None)  # there is nothing to back up or to restore into without a profile
        if self.learner:
            self.profile_action.setText(f"Profile: {self.learner.profile.name}…")

    def open_stats(self) -> None:
        """
        Show the statistics in place of the current page. Nothing happens without a profile.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
        >>> window.open_stats()
        >>> window.title_label.text()
        'Statistics'
        >>> window.close_overlay()
        """
        if self.learner:
            self._open_overlay(StatsPage(self.learner), title="Statistics")

    def open_database(self) -> None:
        """
        Show the database browser in place of the current page. Nothing happens without a profile.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
        >>> window.open_database()
        >>> window.title_label.text()
        'Database'
        >>> window.close_overlay()
        """
        if self.learner:
            self._open_overlay(DatabasePage(self.learner), title="Database")

    def _open_overlay(
        self,
        page: StatsPage | DatabasePage,
        *,
        title: str,
    ) -> None:
        """
        Show a page that has a `back` signal in place of the current page.

        Parameters
        ----------
        page : StatsPage or DatabasePage
            The page to show; its Back button returns to the page it replaced.
        title : str
            The title to show in the top bar while it is open. Keyword-only.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> learner = Learner(db, profile=db.add_profile("Ada"))
        >>> window = MainWindow(learner)
        >>> window._open_overlay(StatsPage(learner), title="Statistics")
        >>> window.stack.currentWidget() is window._overlay
        True
        >>> window.close_overlay()
        """
        self.close_overlay()
        self._overlay_return = (self.stack.currentWidget(), self.title_label.text())
        self._overlay = page
        page.back.connect(self.close_overlay)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.title_label.setText(title)

    def close_overlay(self) -> None:
        """
        Leave the statistics or database page and show the page that was open before it.

        Examples
        --------
        >>> from alto.learning import Database
        >>> db = Database()
        >>> window = MainWindow(Learner(db, profile=db.add_profile("Ada")))
        >>> window.open_stats()
        >>> window.close_overlay()
        >>> window.title_label.text()
        'Alto - Music Theory'
        """
        page, self._overlay = self._overlay, None
        if page is None or self._overlay_return is None:
            return
        previous, title = self._overlay_return
        if previous is not None:
            self.stack.setCurrentWidget(previous)
        self.title_label.setText(title)
        self.stack.removeWidget(page)
        page.deleteLater()

    def switch_profile(self) -> None:
        """
        Choose or add a profile.

        Their history and questions are kept apart; the next question comes from theirs.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.switch_profile()  # without a profile there is nothing to switch
        """
        if not self.learner:
            return
        dialog = ProfileDialog(self.learner.db, current=self.learner.profile, parent=self)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        chosen = dialog.chosen
        if accepted and chosen is not None and chosen != self.learner.profile:
            self.learner.profile = chosen
            # noinspection PyTypeChecker
            remember_profile(chosen)
            self._show_profile()
            self.show_home()

    def export_backup(self) -> None:
        """
        Save a backup of everything: ask where, then write profiles, history and settings to one file.

        Examples
        --------
        >>> MainWindow().export_backup()  # does nothing without a profile
        """
        if self.learner:
            backup_flow.export_backup(self, db=self.learner.db)

    def import_backup(self) -> None:
        """
        Replace everything with a backup: ask for the file, check it, ask again, and reload the whole window from it.

        Examples
        --------
        >>> MainWindow().import_backup()  # does nothing without a profile
        """
        if self.learner and backup_flow.import_backup(self, db=self.learner.db):
            self._restored()

    def _restored(self) -> None:
        """
        Pick up an imported backup: the profile that was in use, the theme and every setting, then open a fresh window.

        Examples
        --------
        >>> MainWindow()._restored()  # doctest: +SKIP
        """
        if not self.learner:
            return
        db = self.learner.db
        profiles = db.profiles()
        self.learner.profile = db.profile(int_value(store(), key="profile/last", default=-1)) or profiles[0]
        apply_theme(saved_theme())
        self.rebuild()  # a new window loads every setting, and draws every icon and colour in the theme again

    def show_home(self) -> None:
        """
        Go back to the start screen, closing the statistics or database and hiding the exercise list.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> window = MainWindow()
        >>> window.open_exercise(NoteNames)
        >>> window.show_home()
        >>> window.title_label.text()
        'Alto - Music Theory'
        """
        self.close_overlay()
        old = self.stack.currentWidget()
        self.title_label.setText(self.APP_TITLE)
        self.nav.clearSelection()
        self.nav.setCurrentRow(-1)
        self.stack.setCurrentWidget(self.home)
        self._update_sidebar_button()
        self._drop(old)
        self._set_sidebar(False)  # the start screen has no list
        self.splitter.handle(1).setEnabled(False)

    def _drop(self, old: QWidget | None) -> None:
        """
        Remove a page that is no longer showing, unless it is the start screen.

        Parameters
        ----------
        old : QWidget or None
            The page that was showing before; None does nothing.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._drop(None)
        >>> window._drop(window.home)  # the start screen is kept
        >>> window.stack.indexOf(window.home)
        0
        """
        if old is None:
            return
        if old is self.home or old is self.stack.currentWidget():
            return
        # noinspection PyTypeChecker
        self.stack.removeWidget(old)
        # noinspection PyUnresolvedReferences
        old.deleteLater()

    # noinspection PyMethodMayBeStatic
    def restart_app(self) -> None:
        """
        Launch a fresh copy of the app, then close this one.

        Examples
        --------
        >>> MainWindow().restart_app()  # doctest: +SKIP
        """
        if QProcess.startDetached(sys.executable, ["-m", "alto"]):
            QApplication.quit()
