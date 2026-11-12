from __future__ import annotations

import sys

from PySide6.QtCore import QProcess, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette
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

from ..exercises import REGISTRY
from ..learning import Learner
from . import icons
from .app_settings import AppSettingsDialog
from .database_page import DatabasePage
from .exercise_view import ExerciseView
from .home import EXERCISE_ICONS, HomePage
from .icons import svg_icon
from .instrument_picker import load_instrument
from .notation import load_style as load_notation_style
from .profile_dialog import ProfileDialog, remember_profile
from .settings_panel import load_construction, load_keyboard, load_note_names
from .stats_dialog import StatsPage
from .store import store


class MainWindow(QMainWindow):
    SIDEBAR_MIN, SIDEBAR_DEFAULT = 170, 240
    APP_TITLE = "Alto - Music Theory"

    def __init__(self, learner: Learner | None = None):
        super().__init__()
        self._overlay: QWidget | None = None  # the statistics or database page, while one is showing
        self._overlay_return: tuple[QWidget, str] | None = None  # the page and title to go back to
        self.learner = learner  # who is practising, and their history; None practises without recording
        self.setWindowTitle(self.APP_TITLE)
        self.resize(1000, 640)
        self.nav = QListWidget()  # the exercise list: section labels and exercises, as a flat sidebar
        self.nav.setObjectName("nav")  # styled in style.py
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setMinimumWidth(self.SIDEBAR_MIN)
        self.nav.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.stack = QStackedWidget()
        self.home = HomePage(REGISTRY)  # start screen with a button for every exercise
        self.home.exercise_chosen.connect(self.open_exercise)
        self.stack.addWidget(self.home)

        self._items: dict[type, QListWidgetItem] = {}
        pal = self.palette()
        ink, window = pal.color(QPalette.Text), pal.color(QPalette.Window)
        section_colour = QColor.fromRgbF(*(ink.getRgbF()[k] * 0.5 + window.getRgbF()[k] * 0.5 for k in range(3)))
        section_font = QFont()
        section_font.setPixelSize(10)
        section_font.setBold(True)
        section_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.3)
        seen: set[str] = set()
        for cls in REGISTRY:
            if cls.category not in seen:
                seen.add(cls.category)
                label = QListWidgetItem(cls.category.upper())
                label.setFlags(Qt.NoItemFlags)  # a section label: not selectable, no hover highlight
                label.setFont(section_font)
                label.setForeground(section_colour)
                label.setTextAlignment(Qt.AlignLeft | Qt.AlignBottom)
                label.setSizeHint(QSize(0, 40))
                self.nav.addItem(label)
            item = QListWidgetItem(svg_icon(EXERCISE_ICONS.get(cls.__name__, icons.EXERCISE_NOTE_NAMES), ink, size=20), cls.name)
            item.setData(Qt.UserRole, cls)
            item.setToolTip(cls.description)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
            self._items[cls] = item
        self.nav.itemClicked.connect(lambda item: self.open_exercise(item.data(Qt.UserRole)))

        # Hamburger menu above the exercise list (replaces the menu bar).
        self.menu_button = QToolButton()
        self.menu_button.setText("☰")
        self.menu_button.setToolTip("Menu")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu_button.setStyleSheet("QToolButton { font-size: 16pt; } QToolButton::menu-indicator { image: none; }")
        menu = QMenu(self.menu_button)
        # A transparent, frameless popup lets the stylesheet's rounded corners show without a square backdrop.
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        glyph = self.menu_button.palette().color(QPalette.WindowText)  # menu icons share the text colour
        home = menu.addAction(svg_icon(icons.HOME, glyph, size=18), "Home")
        home.triggered.connect(self.show_home)
        menu.addSeparator()
        restart = menu.addAction(svg_icon(icons.RESTART, glyph, size=18), "Restart")
        restart.setShortcut(QKeySequence("Ctrl+R"))
        restart.triggered.connect(self.restart_app)
        stats_action = menu.addAction(svg_icon(icons.CHART, glyph, size=18), "Statistics")
        stats_action.triggered.connect(self.open_stats)
        database_action = menu.addAction(svg_icon(icons.DATABASE, glyph, size=18), "Browse database")
        database_action.triggered.connect(self.open_database)
        self.profile_action = menu.addAction(svg_icon(icons.PROFILE, glyph, size=18), "")
        self.profile_action.triggered.connect(self.switch_profile)
        self._show_profile()
        settings_action = menu.addAction(svg_icon(icons.GEAR, glyph, size=18), "Settings…")
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self.open_settings)
        menu.addSeparator()
        quit_action = menu.addAction(svg_icon(icons.QUIT, glyph, size=18), "Quit")
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(QApplication.quit)
        self.menu_button.setMenu(menu)
        self.addAction(settings_action)
        self.addAction(restart)  # keep the shortcuts working while the menu is closed
        self.addAction(quit_action)

        load_note_names()
        load_keyboard()
        load_construction()
        load_instrument()
        load_notation_style()

        # The list and the exercise sit in a splitter: drag the handle to resize, or drag the list
        # narrower than its minimum to collapse it.
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.nav)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self._sidebar_width = int(store().value("ui/sidebarWidth", self.SIDEBAR_DEFAULT))
        # Whether the user wants the list shown on exercise pages. The start screen never shows it.
        self._sidebar_pref = str(store().value("ui/sidebarCollapsed", "false")).lower() != "true"
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
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.menu_button)
        self.stats_button = QToolButton()  # a quick way to the statistics, beside the menu
        self.stats_button.setIcon(svg_icon(icons.CHART, self.palette().color(QPalette.WindowText)))
        self.stats_button.setIconSize(QSize(22, 22))
        self.stats_button.setAutoRaise(True)
        self.stats_button.setToolTip("Statistics")
        self.stats_button.setVisible(self.learner is not None)
        self.stats_button.clicked.connect(self.open_stats)
        buttons.addWidget(self.stats_button)
        self.database_button = QToolButton()
        self.database_button.setIcon(svg_icon(icons.DATABASE, self.palette().color(QPalette.WindowText)))
        self.database_button.setIconSize(QSize(22, 22))
        self.database_button.setAutoRaise(True)
        self.database_button.setToolTip("Browse the database")
        self.database_button.setVisible(self.learner is not None)
        self.database_button.clicked.connect(self.open_database)
        buttons.addWidget(self.database_button)
        bar = QGridLayout()
        bar.addLayout(buttons, 0, 0, Qt.AlignLeft)
        bar.addWidget(self.title_label, 0, 1, Qt.AlignCenter)
        bar.setColumnStretch(0, 1)
        bar.setColumnStretch(2, 1)
        lay.addLayout(bar)
        lay.addWidget(self.splitter, 1)
        self.setCentralWidget(root)

    # exercise list: collapse / resize
    def sidebar_width(self) -> int:
        return self.splitter.sizes()[0]

    def _sidebar_dragged(self, *_):
        width = self.sidebar_width()
        if width > 0:
            self._sidebar_width = width
        self._sidebar_pref = width > 0
        self._save_sidebar()
        self._update_sidebar_button()

    def _update_sidebar_button(self):
        """Keep every page's toggle button (they live in the exercise headers) in step with the list."""
        is_open = self.sidebar_width() > 0
        for i in range(self.stack.count()):
            button = getattr(self.stack.widget(i), "sidebar_button", None)
            if button:
                button.set_open(is_open)

    def _save_sidebar(self):
        s = store()
        s.setValue("ui/sidebarWidth", self._sidebar_width)
        s.setValue("ui/sidebarCollapsed", "false" if self._sidebar_pref else "true")

    def toggle_sidebar(self):
        """The user's button: slide the list closed, or back open. Remembered for next time."""
        self._set_sidebar(self.sidebar_width() == 0, user=True)

    def _set_sidebar(self, show: bool, user: bool = False):
        """Slide the exercise list open or closed. Only a user's choice changes the saved preference."""
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

        def done():
            self.nav.setMinimumWidth(self.SIDEBAR_MIN)
            self.splitter.setSizes([end, total - end])
            self._save_sidebar()
            self._update_sidebar_button()

        anim.finished.connect(done)
        anim.start()

    def open_exercise(self, cls):
        """Show an exercise (a no-op for category headings, which have no class)."""
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

    def open_settings(self):
        dialog = AppSettingsDialog(self)
        dialog.exec()
        if dialog.theme_changed:
            self.rebuild()

    def rebuild(self):
        """Open a fresh window in the same place, so every icon and colour is drawn in the new theme."""
        fresh = type(self)(self.learner)
        fresh.setGeometry(self.geometry())
        fresh.setWindowState(self.windowState())
        QApplication.instance().main_window = fresh
        fresh.show()
        self.close()

    def _show_profile(self):
        self.profile_action.setVisible(self.learner is not None)
        if self.learner:
            self.profile_action.setText(f"Profile: {self.learner.profile.name}…")

    def open_stats(self):
        if self.learner:
            self._open_overlay(StatsPage(self.learner), "Statistics")

    def open_database(self):
        if self.learner:
            self._open_overlay(DatabasePage(self.learner), "Database")

    def _open_overlay(self, page: QWidget, title: str):
        """Show `page` (which has a `back` signal) in place of the current page; Back returns to it."""
        self.close_overlay()
        self._overlay_return = (self.stack.currentWidget(), self.title_label.text())
        self._overlay = page
        page.back.connect(self.close_overlay)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.title_label.setText(title)

    def close_overlay(self):
        """Leave the statistics or database page and show the page that was open before it."""
        page, self._overlay = self._overlay, None
        if page is None:
            return
        previous, title = self._overlay_return
        self.stack.setCurrentWidget(previous)
        self.title_label.setText(title)
        self.stack.removeWidget(page)
        page.deleteLater()

    def switch_profile(self):
        """Choose or add a profile. Their history and questions are kept apart; the next question comes from theirs."""
        if not self.learner:
            return
        dialog = ProfileDialog(self.learner.db, self.learner.profile, self)
        if dialog.exec() == QDialog.Accepted and dialog.chosen and dialog.chosen != self.learner.profile:
            self.learner.profile = dialog.chosen
            remember_profile(dialog.chosen)
            self._show_profile()
            self.show_home()

    def show_home(self):
        self.close_overlay()
        old = self.stack.currentWidget()
        self.title_label.setText(self.APP_TITLE)
        self.nav.clearSelection()
        self.nav.setCurrentItem(None)
        self.stack.setCurrentWidget(self.home)
        self._update_sidebar_button()
        self._drop(old)
        self._set_sidebar(False)  # the start screen has no list
        self.splitter.handle(1).setEnabled(False)

    def _drop(self, old):
        if old is not self.home and old is not self.stack.currentWidget():
            self.stack.removeWidget(old)
            old.deleteLater()

    def restart_app(self):
        """Launch a fresh copy of the app, then close this one."""
        if QProcess.startDetached(sys.executable, ["-m", "alto"]):
            QApplication.quit()
