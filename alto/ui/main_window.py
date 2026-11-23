"""
The main window: tile browsing or a workspace with an independently selected exercise or lesson list.

Navigation stays on the left of the top bar, with data tools on the right. Browsing tiles retains the active activity.

Examples
--------
>>> window = MainWindow()
>>> window.title_label.text()
'Alto - Music Theory'
"""

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass, field
from html import escape
from importlib import metadata
from os.path import samestat
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QByteArray,
    QEasingCurve,
    QEvent,
    QFile,
    QLockFile,
    QObject,
    QPoint,
    QProcess,
    QPropertyAnimation,
    QSize,
    QStandardPaths,
    Qt,
    QTimer,
    QUrl,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QMoveEvent,
    QPainter,
    QPalette,
    QPixmap,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from alto import settings, updates
from alto.audio import sounds
from alto.exercises import REGISTRY
from alto.exercises.base import Exercise
from alto.exercises.packs import (
    InstalledPlugin,
    install_pack,
)
from alto.learning import Learner
from alto.learning.calendar import CALENDAR_SCHEDULERS, DEFAULT_SCHEDULER
from alto.location import database_path
from alto.ui import (
    backup_flow,
    icons,
    motion,
    update_flow,
    zoom,
)
from alto.ui.anki_exporter import ExporterSession
from alto.ui.app_settings import AppSettingsDialog
from alto.ui.database_page import DatabasePage
from alto.ui.exercise_settings import load_exercise_settings
from alto.ui.exercise_view import ExerciseView
from alto.ui.glossary import GlossaryPage
from alto.ui.home import (
    EXERCISE_ICONS,
    HomePage,
)
from alto.ui.icons import set_svg_icon, svg_icon
from alto.ui.instrument_picker import load_instrument
from alto.ui.keyboard_styles import load_style as load_keyboard_style
from alto.ui.lesson import LessonsPage
from alto.ui.lesson_nav import (
    STEP_ROLE,
    LessonNav,
    section_item,
)
from alto.ui.notation import load_style as load_notation_style
from alto.ui.plugins_dialog import PluginsDialog
from alto.ui.profile_dialog import (
    ProfileDialog,
    remember_profile,
)
from alto.ui.stats_dialog import StatsPage
from alto.ui.store import (
    import_settings,
    int_value,
    store,
    text_value,
)
from alto.ui.theme import (
    STUDIO,
    apply_theme,
    saved_theme,
)
from alto.ui.transitions import SIDEBAR_SLIDE_MS, saved_transition
from alto.ui.widgets import SidebarToggle
from alto.ui.zoom import css, px

DEFAULT_WIDTH, DEFAULT_HEIGHT = 1100, 820  # big enough for a lesson step with its circle, and an exercise with its pane
SCREEN_FRACTION = 0.92  # the most of the screen the window opens to, so that it never starts bigger than the screen


def default_size() -> tuple[int, int]:
    """
    Return the size a new window opens at.

    It is big enough for a lesson step, with its circle, to show without scrolling, but never more than most of the screen.

    Returns
    -------
    tuple of (int, int)
        The width and height in pixels.

    Examples
    --------
    >>> width, height = default_size()
    >>> 0 < width <= DEFAULT_WIDTH and 0 < height <= DEFAULT_HEIGHT
    True
    """
    available = QGuiApplication.primaryScreen().availableGeometry()
    return (
        min(DEFAULT_WIDTH, int(available.width() * SCREEN_FRACTION)),
        min(DEFAULT_HEIGHT, int(available.height() * SCREEN_FRACTION)),
    )


@dataclass(kw_only=True)
class _PageState:
    """
    Remember the activity, browsing section and layout across a theme rebuild.

    Attributes
    ----------
    exercise : type of Exercise or None
        The retained exercise's class.
    exercise_settings : tuple of (bool, int, int) or None
        Whether exercise settings are open, the selected settings page, and its scroll position.
    lesson : tuple of (str, int) or None
        The retained lesson's key and step.
    active : str
        "exercise", "lesson" or "empty" for the workspace behind the tiles.
    lesson_parent : str
        "exercise", "empty" or "home", the page to return to when leaving a lesson.
    overlay : str or None
        "stats" or "database" for a utility page on top.
    mode : str
        "exercises" or "lessons", independently of the active activity.
    pane : bool
        Whether the workspace rather than tiles is selected.
    sidebar : bool
        Whether the sidebar is expanded in the workspace.
    search : str
        The search text shared by the tiles and navigation lists.
    tile_filters : dict
        Checked tile titles for each filtered section.
    filters_open : bool
        Whether the tile grid's filter sidebar is open.
    shuffle : bool
        Whether to change exercise categories after each answer.

    Examples
    --------
    >>> _PageState().mode
    'exercises'
    """

    exercise: type[Exercise] | None = None
    exercise_settings: tuple[bool, int, int] | None = None
    lesson: tuple[str, int] | None = None
    active: str = "empty"
    lesson_parent: str = "home"
    overlay: str | None = None
    glossary: tuple[str, str, int, int, int] | None = None
    mode: str = "exercises"
    pane: bool = False
    sidebar: bool = True
    search: str = ""
    tile_filters: dict[str, frozenset[str]] = field(default_factory=dict)
    filters_open: bool = False
    shuffle: bool = False


class _AdjacentSubmenu(QMenu):
    """
    Place the popup flush with the parent menu's outer edge.

    Examples
    --------
    >>> parent = QMenu()
    >>> submenu = _AdjacentSubmenu("Help", parent)
    >>> submenu.title()
    'Help'
    """

    def showEvent(self, event: QShowEvent) -> None:
        """
        Align the popup after it opens and after deferred platform placement.

        Parameters
        ----------
        event : QShowEvent
            The popup's show event.

        Examples
        --------
        >>> submenu = _AdjacentSubmenu("Help")
        >>> submenu.showEvent(QShowEvent())
        """
        super().showEvent(event)
        self._align_edge()
        # Qt/platform popup placement can run after showEvent returns.
        QTimer.singleShot(0, self, self._align_edge)

    def moveEvent(self, event: QMoveEvent) -> None:
        """
        Restore edge alignment if Qt moves an open submenu.

        Parameters
        ----------
        event : QMoveEvent
            The popup's move event.

        Examples
        --------
        >>> from PySide6.QtCore import QPoint
        >>> submenu = _AdjacentSubmenu("Help")
        >>> submenu.moveEvent(QMoveEvent(QPoint(1, 1), QPoint()))
        """
        super().moveEvent(event)
        if self.isVisible():
            self._align_edge()

    def _align_edge(self) -> None:
        """
        Place a visible submenu beside its parent within the screen bounds.

        Examples
        --------
        >>> submenu = _AdjacentSubmenu("Help")
        >>> submenu._align_edge()  # hidden menus keep their position
        """
        if not self.isVisible():
            return
        parent = self.parentWidget()
        if not isinstance(parent, QMenu):
            return
        edge = parent.frameGeometry()
        x = edge.x() + edge.width()
        screen = parent.screen().availableGeometry()
        if x + self.width() > screen.x() + screen.width():
            x = edge.x() - self.width()
        offset = x - self.frameGeometry().x()
        if offset:
            self.move(self.x() + offset, self.y())


ZOOM_SETTLE_MS = 120
ZOOM_INDICATOR_MS = 1200


class _ZoomPreview(QGraphicsEffect):
    """
    Animate the workspace from a single frame captured by Qt during painting.

    Examples
    --------
    >>> preview = _ZoomPreview(window.splitter)  # doctest: +SKIP
    >>> preview.move_to(1.25)  # doctest: +SKIP
    """

    frame_ready = Signal()

    def __init__(self, workspace: QWidget) -> None:
        """
        Prepare to capture the workspace on its first paint.

        Parameters
        ----------
        workspace : QWidget
            The live workspace below the toolbar.

        Examples
        --------
        >>> preview = _ZoomPreview(window.splitter)  # doctest: +SKIP
        """
        super().__init__(workspace)
        self.frame = QPixmap()
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(90)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(1.0)
        self.animation.valueChanged.connect(lambda _value: self.update())
        self.setEnabled(False)
        workspace.setGraphicsEffect(self)

    def move_to(self, scale: float) -> None:
        """
        Retarget the animation from the scale currently on screen.

        Parameters
        ----------
        scale : float
            Requested zoom divided by the zoom of the captured workspace.

        Examples
        --------
        >>> preview.move_to(1.25)  # doctest: +SKIP
        """
        current = self.animation.currentValue() if self.isEnabled() else 1.0
        self.setEnabled(True)
        self.animation.stop()
        self.animation.setStartValue(current)
        self.animation.setEndValue(scale)
        if self.frame.isNull():
            self.update()
        else:
            self.animation.start()

    def draw(self, painter: QPainter) -> None:
        """
        Paint the workspace at the current animation scale.

        Parameters
        ----------
        painter : QPainter
            The workspace painter supplied by Qt.

        Examples
        --------
        >>> preview.update()  # doctest: +SKIP
        """
        if self.frame.isNull():
            self.frame = self.sourcePixmap(mode=QGraphicsEffect.PixmapPadMode.NoPad)
            self.animation.start()
            self.frame_ready.emit()
        scale = self.animation.currentValue()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(self.frame.deviceIndependentSize().width() * (1 - scale) / 2, 0)
        painter.scale(scale, scale)
        painter.drawPixmap(0, 0, self.frame)
        painter.restore()


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
        Who is practicing, and their history; None practices without recording.
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
    view_button : QToolButton
        Returns to the tiles without discarding the current activity.
    pane_button : SidebarToggle
        Opens or closes the navigation pane beside the current activity.
    empty_page : QLabel
        The selected section's prompt before an activity starts.
    search_field : QLineEdit
        Filters tiles and navigation lists without leaving the current activity.

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
            Who is practicing. Without one, nothing is recorded and the statistics buttons are hidden.

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
        self._overlay: StatsPage | DatabasePage | GlossaryPage | LessonsPage | None = (
            None  # the statistics, database or lesson page, while one is showing
        )
        self._overlay_return: tuple[QWidget | None, str] | None = None  # the page and title to go back to
        self._pane_view = False
        self._grid_return_available = False
        self._exercise_page: ExerciseView | None = None
        self._lesson_page: LessonsPage | None = None
        self._workspace_page: ExerciseView | LessonsPage | None = None
        self._lesson_return: tuple[QWidget | None, str] | None = None
        self._settings: AppSettingsDialog | None = None  # the settings, while they are open
        self._exporter = ExporterSession()
        self.learner = learner  # who is practicing, and their history; None practices without recording
        zoom.load()
        self._zoom_timer = QTimer(self)  # a turn of the wheel makes several steps; the window is made again once they stop
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(ZOOM_SETTLE_MS)
        self._zoom_timer.timeout.connect(self._apply_zoom)
        self._layout_zoom = zoom.percent()
        self._zoom_notice_timer = QTimer(self)
        self._zoom_notice_timer.setSingleShot(True)
        self._zoom_notice_timer.setInterval(ZOOM_INDICATOR_MS)
        zoom.signals.changed.connect(self._zoom_changed)
        self._wheel_zoom = zoom.WheelZoom(self)
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        self._wheel_zoom.follow(app)  # on each window in turn: a filter on the whole application slows every widget
        self.setWindowTitle(self.APP_TITLE)
        self.resize(*default_size())
        saved_geometry = store().value("ui/windowGeometry", QByteArray())
        if isinstance(saved_geometry, QByteArray):
            self.restoreGeometry(saved_geometry)
        self._build()

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Remember the window's size and position when the app closes.

        Parameters
        ----------
        event : QCloseEvent
            The window close event.


        Examples
        --------
        >>> closeEvent()  # doctest: +SKIP
        """
        self._exporter.close()
        store().setValue("ui/windowGeometry", self.saveGeometry())
        super().closeEvent(event)

    def _build(self) -> None:
        """
        Make the window's contents: the lists, the pages, the menu and the top bar, drawn in the current theme.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.title_label.text()
        'Alto - Music Theory'
        """
        self._layout_zoom = zoom.percent()
        self._pane_view = False
        self._exercise_page = None
        self._lesson_page = None
        self._workspace_page = None
        self._lesson_return = None
        self.nav = QListWidget()  # the exercise list: section labels and exercises, as a flat sidebar
        self.nav.setObjectName("nav")  # styled in style.py
        self.nav.setIconSize(QSize(px(icons.ACTIVITY_ICON_SIZE), px(icons.ACTIVITY_ICON_SIZE)))
        self.nav.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lesson_nav = LessonNav()  # the lesson list, which takes the exercise list's place in lesson mode
        self.nav_stack = QStackedWidget()  # holds the two lists; the page decides which shows
        self.nav_stack.addWidget(self.nav)
        self.nav_stack.addWidget(self.lesson_nav)
        self.nav_stack.setMinimumWidth(px(self.SIDEBAR_MIN))
        self.lesson_nav.lesson_chosen.connect(self._lesson_picked)
        self.lesson_nav.step_chosen.connect(self._step_picked)
        self.stack = QStackedWidget()
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        activity_scroll = QScrollArea()
        activity_scroll.setFrameShape(QFrame.Shape.NoFrame)
        activity_scroll.setWidgetResizable(True)
        activity_scroll.setWidget(self.stack)
        self.stack.setAutoFillBackground(False)
        activity_scroll.viewport().setAutoFillBackground(False)
        workspace_layout.addWidget(activity_scroll, 1)
        self.home = HomePage(REGISTRY, learner=self.learner, filter_layout=workspace_layout)
        self.home.exercise_chosen.connect(self.open_exercise)
        self.home.lesson_chosen.connect(self.open_lessons)
        self.home.resume_button.clicked.connect(self._back_from_topbar)
        self.stack.addWidget(self.home)
        self.empty_page = QLabel()
        self.empty_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_page.setWordWrap(True)
        self.empty_page.setAccessibleName("Select an activity")
        self.stack.addWidget(self.empty_page)
        self._update_empty_page()

        self._items: dict[type[Exercise], QListWidgetItem] = {}
        seen: set[str] = set()
        for cls in REGISTRY:
            if cls.category not in seen:
                seen.add(cls.category)
                self.nav.addItem(section_item(cls.category, palette=self.palette()))
            item = QListWidgetItem(cls.name)
            item.setData(Qt.ItemDataRole.UserRole, cls)
            item.setToolTip(cls.description)
            item.setSizeHint(QSize(0, px(38)))
            self.nav.addItem(item)
            self._items[cls] = item
        icons.set_item_icons(
            self.nav,
            [(EXERCISE_ICONS.get(cls.__name__, icons.EXERCISE_NOTE_NAMES), item.setIcon) for cls, item in self._items.items()],
        )
        widest_navigation = max(self.nav.sizeHintForColumn(0), self.lesson_nav.sizeHintForColumn(0))
        self.SIDEBAR_DEFAULT = max(px(self.SIDEBAR_MIN), widest_navigation + 28)
        # noinspection PyShadowingNames
        self.nav.itemClicked.connect(lambda item: self.open_exercise(item.data(Qt.ItemDataRole.UserRole)))

        # Hamburger menu above the exercise list (replaces the menu bar).
        self.menu_button = QToolButton()
        self.menu_button.setText("☰")
        self.menu_button.setToolTip("Menu")
        self.menu_button.setAccessibleName("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.setStyleSheet(css("QToolButton { font-size: 16pt; } QToolButton::menu-indicator { image: none; }"))
        menu = QMenu(self.menu_button)
        tools_menu = _AdjacentSubmenu("Tools", menu)
        help_menu = _AdjacentSubmenu("Help", menu)
        # Transparent, frameless popups let the stylesheet's rounded corners show.
        for popup in (menu, tools_menu, help_menu):
            popup.setObjectName("appMenu")
            popup.setWindowFlags(popup.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.profile_action = menu.addAction("")
        set_svg_icon(self.profile_action, icons.PROFILE, size=18)
        self.profile_action.triggered.connect(self.switch_profile)
        settings_action = menu.addAction("Settings…")
        set_svg_icon(settings_action, icons.GEAR, size=18)
        settings_action.setShortcut(QKeySequence("Ctrl+Alt+S"))
        settings_action.triggered.connect(self.open_settings)
        menu.addSeparator()
        set_svg_icon(tools_menu, icons.TOOLS, size=18)
        menu.addMenu(tools_menu)
        self.import_action = tools_menu.addAction("Import backup…")
        set_svg_icon(self.import_action, icons.IMPORT, size=18)
        self.import_action.setToolTip("Replace everything with a backup made earlier")
        self.import_action.triggered.connect(self.import_backup)
        self.export_action = tools_menu.addAction("Export backup…")
        set_svg_icon(self.export_action, icons.EXPORT, size=18)
        self.export_action.setToolTip("Save everything Alto keeps (profiles, history and settings) to one file")
        self.export_action.triggered.connect(self.export_backup)
        plugins_action = tools_menu.addAction("Plugins…")
        set_svg_icon(plugins_action, icons.PLUGIN, size=18)
        plugins_action.setToolTip("Install, update, or uninstall instrument plugins")
        plugins_action.triggered.connect(self.open_plugins)
        exporter_action = tools_menu.addAction("Anki Exporter")

        icons.set_palette_icon(
            exporter_action,
            lambda palette: svg_icon(
                icons.FLASHCARDS,
                color=QColor("white" if palette.window().color().lightness() < 128 else "black"),
                size=18,
            ),
        )
        exporter_action.triggered.connect(self.open_anki_exporter)
        self._show_profile()  # shows or hides the three actions that need a profile
        self.update_action = tools_menu.addAction("Check for updates…")
        set_svg_icon(self.update_action, icons.UPDATE, size=18)
        self.update_action.setToolTip("See whether a newer Alto is available, and install it")
        self.update_action.triggered.connect(self.check_for_updates)  # needs no profile, so it is always there
        set_svg_icon(help_menu, icons.HELP, size=18)
        menu.addMenu(help_menu)
        documentation = help_menu.addAction("Documentation")
        set_svg_icon(documentation, icons.BOOK, size=18)
        documentation.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://altosaurus.github.io/alto/getting-started/")),
        )
        report_issue = help_menu.addAction("Report an issue")
        set_svg_icon(report_issue, icons.ISSUE, size=18)
        report_issue.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/altosaurus/alto/issues")))
        github = help_menu.addAction("GitHub")
        set_svg_icon(github, icons.GITHUB, size=18)
        github.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/altosaurus/alto")))
        about = help_menu.addAction("About")
        set_svg_icon(about, icons.INFO, size=18)
        about.triggered.connect(self.show_about)
        menu.addSeparator()
        restart = menu.addAction("Restart")
        set_svg_icon(restart, icons.RESTART, size=18)
        restart.setShortcut(QKeySequence("Ctrl+R"))
        restart.triggered.connect(self.restart_app)
        quit_action = menu.addAction("Quit")
        set_svg_icon(quit_action, icons.QUIT, size=18)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.quit)
        self.menu_button.setMenu(menu)
        self.addAction(settings_action)
        self.addAction(restart)  # keep the shortcuts working while the menu is closed
        self.addAction(quit_action)
        self._add_zoom_actions()

        load_exercise_settings()
        load_instrument()
        load_notation_style()
        load_keyboard_style()

        # The list and the exercise sit in a splitter: drag the handle to resize, or drag the list
        # narrower than its minimum to collapse it.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self._zoom_preview = _ZoomPreview(self.splitter)
        self._zoom_preview.frame_ready.connect(self._zoom_timer.start)
        self.splitter.setHandleWidth(10)
        self.splitter.addWidget(self.nav_stack)
        self.splitter.addWidget(workspace)
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

        root = QWidget()
        lay = QVBoxLayout(root)
        # Navigation on the left, data tools on the right, with the activity title centered.
        self.title_label = QLabel(self.APP_TITLE)
        self.title_label.setObjectName("activityTitle")
        buttons = QHBoxLayout()
        buttons.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        # noinspection DuplicatedCode
        buttons.addWidget(self.menu_button)
        self.view_button = QToolButton()
        self.view_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.view_button.setIconSize(QSize(px(18), px(18)))
        self.view_button.setAutoRaise(True)
        self.view_button.clicked.connect(self._toggle_tiles_workspace)
        self.pane_button = SidebarToggle(noun="navigation pane")
        self.pane_button.setObjectName("navigationPane")
        self.pane_button.setCheckable(True)
        self.pane_button.setIconSize(QSize(px(18), px(18)))
        self.pane_button.set_open(False)
        set_svg_icon(self.pane_button, icons.NAVIGATION_OPEN)
        self.pane_button.clicked.connect(self.toggle_navigation)
        self.search_field = QLineEdit()
        self.search_field.setObjectName("navigationSearch")
        self.search_field.setClearButtonEnabled(True)
        self.search_field.setMinimumWidth(0)
        self.search_field.setMinimumHeight(px(32))
        self.search_field.textChanged.connect(self.home.set_search)
        self.search_action = self.search_field.addAction(
            QIcon(),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        set_svg_icon(self.search_action, icons.SEARCH, role=QPalette.ColorRole.Text)
        self.search_action.setText("Search")
        self.search_action.triggered.connect(lambda: self.search_field.setFocus())
        self.view_button.setObjectName("navigationView")
        self.view_button.setMinimumHeight(px(32))
        self.search_row = QFrame()
        self.search_row.setObjectName("navigationSearchGroup")
        self.search_row.setProperty("focusWithin", False)
        self.search_row.setFixedWidth(max(px(self.SIDEBAR_MIN), self._sidebar_width))
        self.navigation_group = QFrame()
        self.navigation_group.setObjectName("navigationGroup")
        self.home.mode_control.setStyleSheet("""
            QFrame#segments { background: transparent; border: none; }
            QFrame#segments QPushButton,
            QFrame#segments QPushButton:hover,
            QFrame#segments QPushButton:pressed,
            QFrame#segments QPushButton:checked,
            QFrame#segments QPushButton:focus {
                background: transparent; border: none; outline: none;
            }
            QFrame#segments QPushButton:checked { color: palette(highlight); }
        """)
        for name, button in zip(("navigationExercises", "navigationLessons"), self.home.mode_control.buttons, strict=True):
            button.setObjectName(name)
            button.setMinimumHeight(px(32))
        section_layout = self.home.mode_control.layout()
        assert section_layout is not None
        section_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        section_layout.setSpacing(2)
        navigation_row = QHBoxLayout(self.navigation_group)
        navigation_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        navigation_row.setSpacing(10)
        navigation_row.addWidget(self.home.mode_control)
        navigation_row.addWidget(self.pane_button)
        self.navigation_divider = QFrame()
        self.navigation_divider.setObjectName("navigationDivider")
        self.navigation_divider.setFixedSize(px(1), px(22))
        navigation_row.addWidget(self.navigation_divider, alignment=Qt.AlignmentFlag.AlignVCenter)
        navigation_row.addWidget(self.view_button)
        buttons.addWidget(self.navigation_group)
        self.search_field.installEventFilter(self)
        search_row = QHBoxLayout(self.search_row)
        search_row.setContentsMargins(
            1,
            1,
            1,
            1,
        )
        search_row.setSpacing(0)
        search_row.addWidget(self.search_field, 1)
        tools = QHBoxLayout()
        tools.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.zoom_indicator = QLabel(f"{zoom.percent()}%")
        self.zoom_indicator.setAccessibleName("Zoom level")
        self._zoom_notice_timer.timeout.connect(self.zoom_indicator.hide)
        tools.addWidget(self.zoom_indicator)
        self.glossary_button = QToolButton()
        self.glossary_button.setIconSize(QSize(px(22), px(22)))
        self.glossary_button.setAutoRaise(True)
        self.glossary_button.setCheckable(True)
        self.glossary_button.setStyleSheet("QToolButton:checked { background: transparent; }")
        self.glossary_button.setToolTip("Glossary")
        self.glossary_button.setAccessibleName("Glossary")
        self.glossary_button.clicked.connect(self.open_glossary)
        tools.addWidget(self.glossary_button)
        self.stats_button = QToolButton()  # data tools stay separate from navigation
        set_svg_icon(self.stats_button, icons.CHART)
        self.stats_button.setIconSize(QSize(px(22), px(22)))
        self.stats_button.setAutoRaise(True)
        self.stats_button.setCheckable(True)
        self.stats_button.setStyleSheet(
            "QToolButton:checked { background: transparent; }",
        )
        self.stats_button.setToolTip("Statistics")
        self.stats_button.setAccessibleName("Statistics")
        if self.learner is None:  # hidden, never shown here: a button with no parent that is shown opens as a window of its own
            self.stats_button.hide()
        self.stats_button.clicked.connect(self.open_stats)
        tools.addWidget(self.stats_button)
        self.database_button = QToolButton()
        set_svg_icon(self.database_button, icons.DATABASE)
        self.database_button.setIconSize(QSize(px(22), px(22)))
        self.database_button.setAutoRaise(True)
        self.database_button.setCheckable(True)
        self.database_button.setStyleSheet(
            "QToolButton:checked { background: transparent; }",
        )
        self.database_button.setToolTip("Browse the database")
        self.database_button.setAccessibleName("Browse the database")
        if self.learner is None:
            self.database_button.hide()
        self.database_button.clicked.connect(self.open_database)
        tools.addWidget(self.database_button)
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
        bar.addLayout(
            tools,
            0,
            2,
            Qt.AlignmentFlag.AlignRight,
        )
        browser_row = QHBoxLayout()
        browser_row.addWidget(self.search_row)
        browser_row.addWidget(self.home.resume_button)
        browser_row.addStretch(1)
        self.shuffle_button = QToolButton(root)
        self.shuffle_button.setAutoRaise(True)
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.setIconSize(self.home.category_filter.iconSize())
        self.shuffle_button.setMinimumSize(self.home.category_filter.minimumSize())
        self.shuffle_button.setAccessibleName("Shuffle exercises")
        self.shuffle_button.toggled.connect(self._update_shuffle_button)
        self.shuffle_button.clicked.connect(
            lambda checked: self._shuffle_exercise() if checked and self.stack.currentWidget() is self.home else None,
        )
        self.home.filters_changed.connect(self._filter_navigation)
        self.home.filters_changed.connect(self._update_shuffle_button)
        browser_row.addWidget(self.shuffle_button)
        browser_row.addWidget(self.home.category_filter)
        bar.addLayout(
            browser_row,
            1,
            0,
            1,
            3,
        )
        self.stack.currentChanged.connect(self._show_mode_control)
        self.stack.currentChanged.connect(self._show_nav)
        self.stack.currentChanged.connect(self.home.page_changed)
        self.home.mode_control.chosen.connect(self._mode_chosen)
        self._show_mode_control()
        bar.setColumnStretch(0, 1)
        bar.setColumnStretch(2, 1)
        lay.addLayout(bar)
        lay.addWidget(self.splitter, 1)
        self.setCentralWidget(root)
        if self.isVisible():
            root.show()
        self.zoom_indicator.setVisible(self._zoom_notice_timer.isActive())
        self._update_sidebar_button()

    def eventFilter(  # noqa: PLR0917 (Qt calls this override with both positional arguments)
        self,
        watched: QObject,
        event: QEvent,
    ) -> bool:
        """
        Highlight the search field's outline while it has keyboard focus.

        Parameters
        ----------
        watched : QObject
            The search field.
        event : QEvent
            The event being delivered.

        Returns
        -------
        bool
            Whether the base window consumes the event; focus changes are allowed through.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.eventFilter(window.search_field, QEvent(QEvent.Type.FocusIn))
        False
        >>> window.search_row.property("focusWithin")
        True
        """
        if watched is self.search_field and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.search_row.setProperty("focusWithin", event.type() == QEvent.Type.FocusIn)
            self.search_row.style().unpolish(self.search_row)
            self.search_row.style().polish(self.search_row)
            self.search_row.update()
        return super().eventFilter(watched, event)

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
        Keep the header and lesson toggle buttons in step with the list.

        Examples
        --------
        >>> MainWindow()._update_sidebar_button()
        """
        is_open = self.sidebar_width() > 0
        if hasattr(self, "pane_button"):
            self.pane_button.setChecked(is_open)
            self.pane_button.set_open(is_open)
            icon_color = QPalette.ColorRole.Highlight if is_open else QPalette.ColorRole.WindowText
            set_svg_icon(self.pane_button, icons.NAVIGATION_CLOSE if is_open else icons.NAVIGATION_OPEN, role=icon_color)
        if hasattr(self, "search_row"):
            self.search_row.setFixedWidth(max(px(self.SIDEBAR_MIN), self._sidebar_width))
        for i in range(self.stack.count()):
            button = getattr(self.stack.widget(i), "sidebar_button", None)
            if isinstance(button, SidebarToggle):
                button.noun = "lesson list" if self.home.mode == "lessons" else "exercise list"
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
        animate: bool = True,
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
        animate : bool, default True
            Slide to the new width. Disable this to lay out the tile grid at its final width immediately.

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
        self.nav_stack.setMinimumWidth(0)  # let the width pass through values below the minimum while animating
        anim = self._sidebar_anim = QVariantAnimation(self)
        anim.setDuration(SIDEBAR_SLIDE_MS if animate else 0)
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
            self.nav_stack.setMinimumWidth(px(self.SIDEBAR_MIN))
            self.splitter.setSizes([end, total - end])
            self._save_sidebar()
            self._update_sidebar_button()

        anim.finished.connect(done)
        motion.play(anim)

    def _shuffle_choices(self) -> list[type[Exercise]]:
        """
        Find all exercises included in the filtered navigation list.

        Returns
        -------
        list of type of Exercise
            Exercises eligible for the next shuffle.

        Examples
        --------
        >>> bool(MainWindow()._shuffle_choices())
        True
        """
        return [cls for cls, item in self._items.items() if not item.isHidden()]

    def _update_shuffle_button(self) -> None:
        """
        Show shuffle during exercise practice and explain when the filters leave no choices.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._update_shuffle_button()
        """
        current = self.stack.currentWidget()
        on_exercise_grid = current is self.home and self.home.mode == "exercises"
        self.shuffle_button.setVisible(on_exercise_grid or isinstance(current, ExerciseView))
        active = self.shuffle_button.isChecked()
        if active:
            icons.set_palette_icon(
                self.shuffle_button,
                lambda palette: svg_icon(
                    icons.SHUFFLE,
                    color=QColor(STUDIO[1].accent if palette.button().color().lightness() < 128 else STUDIO[0].accent),
                ),
            )
        else:
            set_svg_icon(self.shuffle_button, icons.SHUFFLE)
        choices = self._shuffle_choices()
        self.shuffle_button.setEnabled(active or bool(choices))
        if self._exercise_page is not None:
            self._exercise_page.shuffle_answers = active and choices != [type(self._exercise_page.exercise)]
        if active:
            tip = "Turn off exercise shuffle"
        elif choices:
            tip = "Shuffle selected exercises after each answer"
        else:
            tip = "No exercises match your filters"
        self.shuffle_button.setToolTip(tip)

    def _shuffle_exercise(self) -> None:
        """
        Open a random eligible exercise through the same navigation as its tile.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._shuffle_exercise()
        >>> isinstance(window.stack.currentWidget(), ExerciseView)
        True
        """
        choices = self._shuffle_choices()
        view = self._exercise_page
        current = type(view.exercise) if view is not None else None
        groups: dict[str, list[type[Exercise]]] = {}
        for cls in choices:
            if cls is not current:
                groups.setdefault(cls.category, []).append(cls)
        categories = list(groups)
        random.shuffle(categories)
        if current is not None and current.category in groups:
            categories.remove(current.category)
            categories.append(current.category)
        learner = self.learner
        mode = learner.mode if learner else DEFAULT_SCHEDULER
        now = time.time()
        for category in categories:
            exercises = groups[category]
            random.shuffle(exercises)
            for exercise in exercises:
                if (
                    learner
                    and mode in CALENDAR_SCHEDULERS
                    and not any(
                        learner.calendar.counts(exercise(), profile=learner.profile.id, mode=mode, now=now),
                    )
                ):
                    continue
                self.open_exercise(exercise)
                return
        if view is not None and current in choices:
            if self.stack.currentWidget() is view:
                view.next_question()
            else:
                self.open_exercise(current)
        elif categories:
            self.open_exercise(groups[categories[0]][0])  # Show the scheduler's caught-up message.
        else:
            self.show_home()

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
        'Key Signature Identification'
        """
        if cls is None:
            return
        self.close_overlay()
        old = self._exercise_page
        view = old if old is not None and type(old.exercise) is cls else ExerciseView(cls(), learner=self.learner)
        if view is not old:
            view.shuffle_requested.connect(self._shuffle_exercise)
            view.lesson_requested.connect(lambda key: self.open_lessons(key))
            view.lesson_back_button.clicked.connect(self._back_to_practice_lesson)
            self.stack.addWidget(view)
        if self._lesson_return is not None and self._lesson_return[0] is old:
            self._lesson_return = (view, cls.name)
        view.lesson_back_button.hide()
        self._exercise_page = view
        self._workspace_page = view
        self.home.set_mode("exercises", animate=False)
        self.nav.setCurrentItem(self._items[cls])
        self._show_workspace()
        self._drop(old)
        view.setFocus()

    def show_about(self) -> None:
        """
        Show the installed version, development status, and purpose of Alto.

        Examples
        --------
        >>> window.show_about()  # doctest: +SKIP
        """
        try:
            classifiers = metadata.metadata("alto").get_all("Classifier") or []
        except metadata.PackageNotFoundError:
            classifiers = []
        status = next((item.rsplit(" - ", 1)[-1] for item in classifiers if item.startswith("Development Status :: ")), "Unknown")
        QMessageBox.about(
            self,
            "About Alto",
            f"<h3>Alto {updates.installed_version()}</h3>"
            f"<p>Development status: {status}</p>"
            "<p>Learn and practice music theory with interactive exercises and lessons.</p>",
        )

    def open_anki_exporter(self) -> None:
        """
        Open the modeless exporter with a private copy of the current exercise settings.

        Examples
        --------
        Choose Anki Exporter from Tools to prepare a deck while keeping the exercise open.
        """
        selected = type(self._exercise_page.exercise).__name__ if self._exercise_page is not None else ""
        try:
            self._exporter.open(self.learner, selected=selected)
        except OSError as error:
            QMessageBox.warning(self, "Anki Exporter", f"Could not open the exporter. {error}")

    def open_settings(self) -> None:
        """
        Open the application settings without blocking the window, or bring them forward if they are already open.

        If the theme was changed, the window is rebuilt in it once the settings are closed.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.open_settings()
        >>> # noinspection PyUnresolvedReferences
        >>> window._settings is not None and not window._settings.isModal()
        True
        >>> # noinspection PyUnresolvedReferences
        >>> window._settings.close()
        True
        """
        if self._settings is not None:
            self._settings.raise_()
            self._settings.activateWindow()
            return
        dialog = AppSettingsDialog(self, learner=self.learner)
        dialog.theme_selected.connect(self._exporter.sync_theme)
        dialog.scheduler_changed.connect(self.home.refresh_counts)
        dialog.scheduler_changed.connect(self._scheduler_changed)
        dialog.defaults_requested.connect(self._restore_defaults)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.finished.connect(self._settings_closed)
        self._settings = dialog
        dialog.show()

    def _scheduler_changed(self) -> None:
        """
        Apply the scheduler to an open exercise and refresh due dates in the database browser.

        Examples
        --------
        >>> MainWindow()._scheduler_changed()
        """
        if self._exercise_page is not None:
            self._exercise_page.scheduling_changed()
        if isinstance(self._overlay, DatabasePage):
            for tab in ("answers", "questions"):
                if self._overlay.tabs[tab].isChecked():
                    self._overlay.show_table(tab, keep_sort=True)
                    break

    def _restore_defaults(self) -> None:
        """
        Restore all preferences while retaining profiles and recorded practice.

        Examples
        --------
        >>> _restore_defaults()  # doctest: +SKIP
        """
        if self.learner:
            self.learner.set_mode(DEFAULT_SCHEDULER)
            self.learner.set_self_grading(False)
            self.learner.set_speed_thresholds(easy=15, hard=15)
            self.learner.calendar.reset_limits(self.learner.profile.id)
        saved = store()
        retained = {key: saved.value(key) for key in saved.allKeys() if key.startswith(("profile/", "lessons/"))}
        import_settings(retained)
        for name in (
            "note_names",
            "intervals",
            "interval_construction",
            "keyboard",
            "keyboard_intervals",
            "construction",
            "arpeggio",
            "key_signatures",
            "key_construction",
            "order_of_keys",
            "scale_identification",
            "scale_construction",
            "clef_basics",
            "notation",
            "circle",
        ):
            cfg = getattr(settings, name)
            cfg.__dict__.clear()
            cfg.__dict__.update(type(cfg)().__dict__)
        sounds.stop_all()
        sounds.enabled = True
        apply_theme("system")
        self._exporter.sync_theme("system")
        if self._sidebar_anim is not None:
            self._sidebar_anim.stop()
        self._overlay = None
        self._overlay_return = None
        for action in self.actions():
            self.removeAction(action)
        old = self.takeCentralWidget()
        self._build()
        self.resize(*default_size())
        if old is not None:
            old.deleteLater()

    def _add_zoom_actions(self) -> None:
        """
        Add the keyboard shortcuts that zoom in and out and go back to 100%, which work in every window of the app.

        Examples
        --------
        >>> window = MainWindow()
        >>> sorted(action.text() for action in window.actions() if action.objectName().startswith("zoom"))
        ['Actual Size', 'Zoom In', 'Zoom Out']
        """
        for name, text, shortcuts, change in (
            (
                "zoomIn",
                "Zoom In",
                [*QKeySequence.keyBindings(QKeySequence.StandardKey.ZoomIn), QKeySequence("Ctrl+=")],
                lambda: zoom.step(1),
            ),
            ("zoomOut", "Zoom Out", QKeySequence.keyBindings(QKeySequence.StandardKey.ZoomOut), lambda: zoom.step(-1)),
            ("zoomReset", "Actual Size", [QKeySequence("Ctrl+0")], self._reset_zoom),
        ):
            action = QAction(text, self.menu_button)
            action.setObjectName(name)
            action.setShortcuts(shortcuts)
            action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            action.triggered.connect(change)
            self.addAction(action)

    def _reset_zoom(self) -> None:
        """
        Reset the workspace and confirm actual size even when it is already at 100%.

        Examples
        --------
        >>> window._reset_zoom()  # doctest: +SKIP
        """
        if not zoom.reset():
            self.zoom_indicator.show()
            self._zoom_notice_timer.start()

    def _zoom_changed(self, percent: int) -> None:
        """
        Show the requested percentage and animate the workspace until input settles.

        Parameters
        ----------
        percent : int
            The newly requested zoom level.

        Examples
        --------
        >>> zoom.step(1)  # doctest: +SKIP
        """
        self.zoom_indicator.setText(f"{percent}%")
        self.zoom_indicator.show()
        self._zoom_notice_timer.start()
        if self.isVisible():
            self._zoom_preview.move_to(percent / self._layout_zoom)
        self._zoom_timer.start()

    def _apply_zoom(self) -> None:
        """
        Draw everything again at the new zoom: the stylesheet, and the window with the sizes it fixes in pixels.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._apply_zoom()
        """
        self._zoom_preview.animation.stop()
        self._zoom_preview.setEnabled(False)
        self._zoom_preview.frame = QPixmap()
        if self._layout_zoom != zoom.percent():
            self.rebuild()
            self._layout_zoom = zoom.percent()
            self.zoom_indicator.show()
            self._zoom_notice_timer.start()

    def _settings_closed(self) -> None:
        """
        Pick up what the settings changed once they are closed: a new theme needs the window to be rebuilt.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._settings_closed()  # nothing was open
        """
        dialog, self._settings = self._settings, None
        if dialog is not None and dialog.theme_changed:
            self.rebuild()

    def rebuild(self) -> None:
        """
        Make the window's contents again in the same window, so every icon and color is drawn in the new theme.

        The window itself stays, so it does not vanish and reappear. The page that was open is shown again, with the list
        already open or closed as it was, not sliding.

        Examples
        --------
        >>> window = MainWindow()
        >>> old_root = window.centralWidget()
        >>> window.rebuild()
        >>> window.centralWidget() is old_root
        False
        """
        state = self._page_state()
        if self._sidebar_anim is not None:
            self._sidebar_anim.stop()
        self._overlay = None
        self._overlay_return = None
        for action in self.actions():
            self.removeAction(action)
        if self._layout_zoom != zoom.percent():
            old = self.centralWidget()
            if old is not None:
                old.deleteLater()
                QApplication.sendPostedEvents(old, QEvent.Type.DeferredDelete)
                old = None
            apply_theme(saved_theme())
        else:
            old = self.takeCentralWidget()
        self._build()
        self._restore_page(state)
        animation = self._sidebar_anim
        if animation is not None and animation.state() != QAbstractAnimation.State.Stopped:
            animation.setCurrentTime(animation.duration())  # the list is already open, not sliding open again
        if old is not None:
            old.deleteLater()

    def _page_state(self) -> _PageState:
        """
        Remember retained activities and the independently selected navigation section.

        Returns
        -------
        _PageState
            Activities, selected section, tile or pane view, and any utility page.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._page_state().pane
        False
        """
        parent = self._lesson_return[0] if self._lesson_return else self.home
        return _PageState(
            exercise=type(self._exercise_page.exercise) if self._exercise_page is not None else None,
            exercise_settings=self._exercise_page.settings_state() if self._exercise_page is not None else None,
            lesson=(self._lesson_page.view.lesson.key, self._lesson_page.view.current) if self._lesson_page is not None else None,
            active="lesson" if isinstance(self._workspace_page, LessonsPage) else "exercise" if self._workspace_page else "empty",
            lesson_parent="exercise" if isinstance(parent, ExerciseView) else "empty" if parent is self.empty_page else "home",
            overlay="stats"
            if isinstance(self._overlay, StatsPage)
            else "database"
            if isinstance(self._overlay, DatabasePage)
            else "glossary"
            if isinstance(self._overlay, GlossaryPage)
            else None,
            glossary=(
                self._overlay.search.text(),
                self._overlay.terms.currentItem().text() if self._overlay.terms.currentItem() else "",
                self._overlay.activity_switch.current(),
                getattr(self._overlay, "_example_index", 0),
                self._overlay.definition.verticalScrollBar().value(),
            )
            if isinstance(self._overlay, GlossaryPage)
            else None,
            mode=self.home.mode,
            pane=self._pane_view,
            sidebar=self._sidebar_pref,
            search=self.search_field.text(),
            tile_filters=self.home.tile_filters.copy(),
            filters_open=self.home.category_filter.isChecked(),
            shuffle=self.shuffle_button.isChecked(),
        )

    def _restore_page(self, state: _PageState) -> None:
        """
        Restore retained activity types and the navigation layout after rebuilding.

        Parameters
        ----------
        state : _PageState
            The activities and navigation state to restore.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> window = MainWindow()
        >>> window._restore_page(_PageState(exercise=NoteNames, active="exercise", pane=True))
        >>> window.title_label.text()
        'Note Identification'
        """
        if state.exercise is not None:
            self.open_exercise(state.exercise)
            if self._exercise_page is not None and state.exercise_settings is not None:
                self._exercise_page.restore_settings_state(state.exercise_settings)
        if state.lesson is not None:
            self.open_lessons(state.lesson[0])
            if self._lesson_page is not None:
                self._lesson_page.view.go(to=state.lesson[1])
            if state.lesson_parent != "exercise":
                parent = self.empty_page if state.lesson_parent == "empty" else self.home
                self._lesson_return = (parent, self.APP_TITLE)
        self._workspace_page = (
            self._lesson_page if state.active == "lesson" else self._exercise_page if state.active == "exercise" else None
        )
        if self.home.mode != state.mode:
            self.home.set_mode(state.mode, animate=False)
        self.search_field.setText(state.search)
        self.home.restore_tile_filters(state.tile_filters, expanded=state.filters_open)
        self.shuffle_button.setChecked(state.shuffle)
        self._sidebar_pref = state.sidebar
        if state.pane:
            self._show_workspace()
        else:
            self.show_home()
        if state.overlay == "stats":
            self.open_stats()
        elif state.overlay == "database":
            self.open_database()
        elif state.overlay == "glossary":
            self.open_glossary()
            if isinstance(self._overlay, GlossaryPage) and state.glossary is not None:
                page = self._overlay
                search, term, mode, example, scroll = state.glossary
                page.search.setText(search)
                for row in range(page.terms.count()):
                    if page.terms.item(row).text() == term:
                        page.terms.setCurrentRow(row)
                        break
                page.activity_switch.set_current(mode)
                page._show_activities(mode)
                page._example_index = example
                if term:
                    page._update_example()
                QTimer.singleShot(0, page, lambda: page.definition.verticalScrollBar().setValue(scroll))

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

    def open_glossary(self) -> None:
        """
        Toggle the glossary from its toolbar button.

        Examples
        --------
        >>> open_glossary()  # doctest: +SKIP
        """
        if isinstance(self._overlay, GlossaryPage):
            self.close_overlay()
            return
        page = GlossaryPage()
        page.lesson_requested.connect(self.open_lessons)
        page.exercise_requested.connect(self._practice)
        self._open_overlay(page, title="Glossary")

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
            if isinstance(self._overlay, StatsPage):
                self.close_overlay()
                return
            self._open_overlay(StatsPage(self.learner), title="Statistics")

    def _update_empty_page(self) -> None:
        """
        Match the empty workspace prompt to the selected exercise or lesson list.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.home.set_mode("exercises", animate=False)
        >>> window._update_empty_page()
        >>> window.empty_page.text()
        'Select an exercise to begin.'
        """
        noun = "a lesson" if self.home.mode == "lessons" else "an exercise"
        self.empty_page.setText(f"Select {noun} to begin.")

    def _show_mode_control(self) -> None:
        """
        Keep navigation icon-only in both views and name the view button for its destination.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.view_button.accessibleName()
        'Tiles'
        """
        self.home.mode_control.set_compact(True)
        self.home.mode_control.set_current(1 if self.home.mode == "lessons" else 0)
        for index, (button, icon) in enumerate(
            zip(
                self.home.mode_control.buttons,
                (icons.EXERCISES, icons.LESSONS),
                strict=True,
            ),
        ):
            color = QPalette.ColorRole.Highlight if index == self.home.mode_control.current() else QPalette.ColorRole.WindowText
            set_svg_icon(button, icon, role=color, size=18)
        section = "lessons" if self.home.mode == "lessons" else "exercises"
        self.search_field.setPlaceholderText(f"Search {section}…")
        self.search_field.setAccessibleName(f"Search {section}")
        self.view_button.setText("")
        self.view_button.setAccessibleName("Tiles")
        self.view_button.setToolTip("Return to tiles")
        set_svg_icon(
            self.view_button,
            icons.TILES,
            role=QPalette.ColorRole.Highlight if not self._pane_view else QPalette.ColorRole.WindowText,
        )
        stats_active = isinstance(self._overlay, StatsPage)
        glossary_active = isinstance(self._overlay, GlossaryPage)
        self.glossary_button.setChecked(glossary_active)
        set_svg_icon(
            self.glossary_button,
            icons.GLOSSARY,
            role=QPalette.ColorRole.Highlight if glossary_active else QPalette.ColorRole.WindowText,
        )
        database_active = isinstance(self._overlay, DatabasePage)
        self.stats_button.setChecked(stats_active)
        self.database_button.setChecked(database_active)
        set_svg_icon(
            self.stats_button,
            icons.CHART,
            role=QPalette.ColorRole.Highlight if stats_active else QPalette.ColorRole.WindowText,
        )
        set_svg_icon(
            self.database_button,
            icons.DATABASE,
            role=QPalette.ColorRole.Highlight if database_active else QPalette.ColorRole.WindowText,
        )
        activity = self._workspace_page
        activity_section = "exercises" if isinstance(activity, ExerciseView) else "lessons" if activity else None
        current = self.stack.currentWidget()
        self.home.set_filter_available(current in (self.home, self.empty_page) or isinstance(current, ExerciseView))
        self._update_shuffle_button()
        show_back = (current is self.home and activity_section is not None) or isinstance(
            self._overlay,
            (StatsPage, DatabasePage, GlossaryPage),
        )
        self.home.resume_button.setVisible(show_back)
        if show_back:
            self.home.resume_button.setText("←  Back")
            self.home.resume_button.setAccessibleName("Back")
            self.home.resume_button.setToolTip("Back to the previous page")

    def _back_from_topbar(self) -> None:
        """
        Return from a data page or resume the current activity from the tiles.

        Examples
        --------
        >>> _back_from_topbar()  # doctest: +SKIP
        """
        if isinstance(self._overlay, (StatsPage, DatabasePage, GlossaryPage)):
            self.close_overlay()
        else:
            self._show_workspace()

    def _mode_chosen(self) -> None:
        """
        Switch the browser's section without replacing the current activity.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> window = MainWindow()
        >>> window.open_exercise(NoteNames)
        >>> view = window.stack.currentWidget()
        >>> window.home.mode_control.buttons[1].click()
        >>> window.stack.currentWidget() is view and window.nav_stack.currentWidget() is window.lesson_nav
        True
        """
        self._show_nav()
        self._show_mode_control()
        self._update_empty_page()
        self._update_sidebar_button()
        if self._pane_view:
            self._set_sidebar(True, user=True)

    def toggle_navigation(self) -> None:
        """
        Open the workspace from tiles, or toggle its navigation pane without leaving the activity.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.toggle_navigation()
        >>> window.stack.currentWidget() is window.empty_page, window.view_button.accessibleName()
        (True, 'Tiles')
        """
        if self._pane_view:
            self.toggle_sidebar()
        else:
            self._show_workspace()
            self._set_sidebar(True, user=True)

    def _show_workspace(self) -> None:
        """
        Show the retained activity, or the empty prompt before an activity begins.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._show_workspace()
        >>> window.stack.currentWidget() is window.empty_page
        True
        """
        if isinstance(self._overlay, (StatsPage, DatabasePage, GlossaryPage)):
            self.close_overlay()
        self._pane_view = True
        page = self._workspace_page
        self._overlay = page if isinstance(page, LessonsPage) else None
        self._overlay_return = self._lesson_return if self._overlay is not None else None
        self._update_empty_page()
        self.title_label.setText(
            page.exercise.name
            if isinstance(page, ExerciseView)
            else page.view.lesson.title
            if isinstance(page, LessonsPage)
            else self.APP_TITLE,
        )
        self.stack.setCurrentWidget(page if page is not None else self.empty_page)
        self.splitter.handle(1).setEnabled(True)
        self._set_sidebar(self._sidebar_pref)
        self._show_nav()
        self._show_mode_control()
        self._update_sidebar_button()

    def _toggle_tiles_workspace(self) -> None:
        """
        Switch between the tile catalog and the workspace while keeping the activity in place.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._toggle_tiles_workspace()
        >>> window.stack.currentWidget() is window.empty_page
        True
        >>> window._toggle_tiles_workspace()
        >>> window.stack.currentWidget() is window.home
        True
        """
        if self.stack.currentWidget() is not self.home:
            if self._pane_view:
                self._grid_return_available = True
                self._grid_return_sidebar = self.sidebar_width() > 0 or self._sidebar_pref
            self.show_home()
        elif self._grid_return_available:
            self._grid_return_available = False
            self._sidebar_pref = self._grid_return_sidebar
            self._show_workspace()
        else:
            self._show_workspace()

    def show_lessons(self) -> None:
        """
        Go to the start screen showing the lessons.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.show_lessons()
        >>> window.home.mode
        'lessons'
        >>> window.home.set_mode("exercises")
        """
        self.home.set_mode("lessons")
        self.show_home()

    def open_lessons(self, lesson: str) -> None:
        """
        Open a lesson in place of the current page, at the step it was left at, with the lesson list on the left.

        Parameters
        ----------
        lesson : str
            The key of the lesson.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.open_lessons("circle-of-fifths")
        >>> window.title_label.text(), window.nav_stack.currentWidget() is window.lesson_nav
        ('The Circle of Fifths', True)
        >>> window.close_overlay()
        """
        self.close_overlay()
        if isinstance(self._overlay, LessonsPage):
            self.close_overlay()
        old = self._lesson_page
        page = old if old is not None and old.view.lesson.key == lesson else LessonsPage(lesson)
        if page is not old:
            page.practice_requested.connect(self._practice)
            page.back.connect(self._leave_lesson)
            page.view.stepped.connect(self.lesson_nav.select_step)
            self.stack.addWidget(page)
        self._lesson_return = (self.stack.currentWidget(), self.title_label.text())
        if self._exercise_page is not None:
            self._exercise_page.lesson_back_button.hide()
        self._lesson_page = page
        self._workspace_page = page
        self.home.set_mode("lessons", animate=False)
        self.lesson_nav.show_lesson(lesson)
        self.lesson_nav.select_step(page.view.current)
        self._show_workspace()
        self._drop(old)

    def _leave_lesson(self) -> None:
        """
        Close the open lesson and show what was open before it, with the exercise list or without the list, as that page has.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.open_lessons("circle-of-fifths")
        >>> window._leave_lesson()
        >>> window.stack.currentWidget() is window.home
        True
        """
        self.close_overlay()
        page = self.stack.currentWidget()
        self._workspace_page = page if isinstance(page, ExerciseView) else None
        if page is self.home:
            self.show_home()
        elif isinstance(page, ExerciseView):
            self.home.set_mode("exercises", animate=False)
            self._show_workspace()
        else:
            self._show_workspace()

    def _lesson_picked(self, key: str) -> None:
        """
        Open the lesson whose row was clicked in the list, unless it is the one that is open.

        Parameters
        ----------
        key : str
            The lesson's key.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.open_lessons("circle-of-fifths")
        >>> window._lesson_picked("circle-of-fifths")  # already open: nothing changes
        >>> window.close_overlay()
        """
        page = self._overlay
        if isinstance(page, LessonsPage) and page.view.lesson.key == key:
            return
        self.open_lessons(key)

    def _step_picked(self, number: int) -> None:
        """
        Go to the step whose row was clicked in the list.

        Parameters
        ----------
        number : int
            The step, from 0.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.open_lessons("circle-of-fifths")
        >>> window._step_picked(2)
        >>> window.lesson_nav.currentItem() is window.lesson_nav.step_items[2]
        True
        >>> window.close_overlay()
        """
        page = self._lesson_page
        if page is not None:
            self._workspace_page = page
            self._show_workspace()
            page.view.go(to=number)

    def _show_nav(self) -> None:
        """
        Show the selected browser section independently of the active activity.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._show_nav()
        >>> window.nav_stack.currentWidget() is window.nav
        True
        """
        lesson = self.home.mode == "lessons"
        nav = self.lesson_nav if lesson else self.nav
        self.nav_stack.setCurrentWidget(nav)
        self._filter_navigation()

    def _filter_navigation(self) -> None:
        """
        Hide unmatched rows and empty category headings, retaining matching lessons' steps.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.search_field.setText("nothing matches this")
        >>> all(window.nav.item(i).isHidden() for i in range(window.nav.count()))
        True
        """
        for nav, cards, section in (
            (self.nav, self.home.cards, "exercises"),
            (self.lesson_nav, self.home.lesson_cards, "lessons"),
        ):
            matching = [card for card in cards if self.home.matches_filter(card, section=section)]
            titles = {card.title for card in matching}
            headings = {card.category.upper() for card in matching}
            visible = False
            for index in range(nav.count()):
                item = nav.item(index)
                if not item.flags() & Qt.ItemFlag.ItemIsSelectable:
                    visible = item.text() in headings
                elif item.data(STEP_ROLE) is None:
                    visible = item.text() in titles
                item.setHidden(not visible)

    def _practice(self, name: str) -> None:
        """
        Leave the lessons and open the exercise that a lesson ends with.

        Parameters
        ----------
        name : str
            The exercise's class name.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._practice("CircleOfFifths")
        >>> window.title_label.text()
        'Circle of Fifths'
        """
        from_lesson = isinstance(self.stack.currentWidget(), LessonsPage)
        cls = next((candidate for candidate in REGISTRY if candidate.__name__ == name), None)
        if cls is not None:
            self.open_exercise(cls)
            if self._exercise_page is not None:
                self._exercise_page.lesson_back_button.setVisible(from_lesson)

    def _back_to_practice_lesson(self) -> None:
        """
        Return from practice to the retained lesson and its current step.

        Examples
        --------
        >>> window = MainWindow()
        >>> window._back_to_practice_lesson()
        >>> window.open_lessons("circle-of-fifths")
        >>> window._practice("CircleOfFifths")
        >>> window._back_to_practice_lesson()
        >>> window.title_label.text()
        'The Circle of Fifths'
        """
        page = self._lesson_page
        if page is None:
            return
        if self._exercise_page is not None:
            self._exercise_page.lesson_back_button.hide()
        self._workspace_page = page
        self.home.set_mode("lessons", animate=False)
        self._show_workspace()

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
            if isinstance(self._overlay, DatabasePage):
                self.close_overlay()
                return
            self._open_overlay(DatabasePage(self.learner), title="Database")

    def _open_overlay(
        self,
        page: StatsPage | DatabasePage | GlossaryPage,
        *,
        title: str,
    ) -> None:
        """
        Slide a utility page in from the right and remember the page to return to.

        Parameters
        ----------
        page : StatsPage or DatabasePage or GlossaryPage
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
        backdrop = self.stack.grab() if self.stack.isVisible() and saved_transition() != "none" else None
        previous = self._overlay
        if previous is None or isinstance(previous, LessonsPage):
            current = self.stack.currentWidget()
            self._pane_view = current is not self.home
            self._overlay_return = (current, self.title_label.text())
        self._overlay = page
        page.back.connect(self.close_overlay)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.title_label.setText(title)
        self._drop(previous)
        if backdrop is not None:
            self._slide_overlay(backdrop)

    def _slide_overlay(self, backdrop: QPixmap) -> None:
        """
        Reveal the incoming page over a still image of the page the user was viewing.

        Parameters
        ----------
        backdrop : QPixmap
            The stack as it appeared immediately before navigation.

        Examples
        --------
        >>> window = MainWindow()
        >>> window.show()
        >>> window.open_glossary()
        >>> isinstance(window.stack.currentWidget(), GlossaryPage)
        True
        """
        incoming = self.stack.grab()
        background = QLabel(self.stack)
        background.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        background.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        background.setPixmap(backdrop)
        background.setGeometry(self.stack.contentsRect())
        foreground = QLabel(background)
        foreground.setPixmap(incoming)
        foreground.setGeometry(background.rect())

        slide = QPropertyAnimation(foreground, b"pos", background)
        slide.setDuration(220)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide.setStartValue(QPoint(self.stack.width(), 0))
        slide.setEndValue(QPoint())
        self.stack.currentChanged.connect(slide.stop)
        self.stack.currentChanged.connect(background.close)
        slide.finished.connect(background.close)
        motion.play(slide)
        background.show()
        background.raise_()

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
        self._overlay_return = None
        if previous is not None:
            self.stack.setCurrentWidget(previous)
        self.title_label.setText(title)
        if isinstance(previous, LessonsPage):
            self._overlay = previous
            self._overlay_return = self._lesson_return
        self._drop(page)

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
            if self._settings is not None:
                self._settings.close()
            self._exporter.close()
            self.learner.set_profile(chosen)
            self.home.refresh_counts()
            # noinspection PyTypeChecker
            remember_profile(chosen)
            self._show_profile()
            self.show_home()
            exercise, lesson = self._exercise_page, self._lesson_page
            self._workspace_page = self._exercise_page = self._lesson_page = None
            self._lesson_return = None
            self._drop(exercise)
            self._drop(lesson)
            self._show_mode_control()

    def export_backup(self) -> None:
        """
        Save a backup of everything: ask where, then write profiles, history and settings to one file.

        Examples
        --------
        >>> MainWindow().export_backup()  # does nothing without a profile
        """
        if self.learner:
            backup_flow.export_backup(self, db=self.learner.db)

    def check_for_updates(self) -> None:
        """
        Ask whether a newer Alto is available; if so and the person agrees, install it and restart.

        Examples
        --------
        >>> MainWindow().check_for_updates()  # doctest: +SKIP
        """
        update_flow.check_for_updates(self, restart=self.restart_app)

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
        self._exporter.close()
        db = self.learner.db
        profiles = db.profiles()
        self.learner.set_profile(db.profile(int_value(store(), key="profile/last", default=-1)) or profiles[0])
        apply_theme(saved_theme())
        self.rebuild()  # a new window loads every setting, and draws every icon and color in the theme again

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
        if not isinstance(self._overlay, LessonsPage):
            self.close_overlay()
        current = self.stack.currentWidget()
        if isinstance(current, (ExerciseView, LessonsPage)):
            self._workspace_page = current
        self._overlay = None
        self._overlay_return = None
        self._pane_view = False
        self.title_label.setText(self.APP_TITLE)
        self._set_sidebar(False, animate=False)
        self.stack.setCurrentWidget(self.home)
        self._show_mode_control()
        self.splitter.handle(1).setEnabled(False)
        self._update_sidebar_button()

    def _drop(self, old: QWidget | None) -> None:
        """
        Remove an unused page, keeping the tiles, empty workspace and retained activities.

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
        if old in (self.home, self.empty_page, self._exercise_page, self._lesson_page, self.stack.currentWidget()):
            return
        # noinspection PyTypeChecker
        self.stack.removeWidget(old)
        # noinspection PyUnresolvedReferences
        old.deleteLater()

    def open_plugins(self) -> None:
        """
        Manage installed plugins, install by code or ZIP, and update from registered releases.

        Examples
        --------
        Choose Plugins in Tools to see the installed viola pack.
        """
        dialog = PluginsDialog(database_path().parent / "plugins", parent=self)
        dialog.restart_requested.connect(self.restart_app)
        dialog.install_requested.connect(lambda: self.install_plugin(parent=dialog))
        dialog.uninstall_requested.connect(lambda plugin: self.uninstall_plugin(plugin, parent=dialog))
        dialog.finished.connect(dialog.deleteLater)
        dialog.exec()

    def install_plugin(self, *, parent: QWidget | None = None) -> None:
        """
        Install a downloaded instrument pack and offer to restart Alto.

        Parameters
        ----------
        parent : QWidget or None, default None
            The window that owns the file chooser and messages. Defaults to this window. Keyword-only.

        Examples
        --------
        Press Install plugin from file in the Plugins dialog and open viola.zip.
        """
        parent = parent or self
        title = "Install plugin from file"
        name, _ = QFileDialog.getOpenFileName(
            parent,
            title,
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),
            "Alto instrument packs (*.zip *.ZIP)",
        )
        if not name:
            return
        source = Path(name)
        try:
            pack_name = install_pack(source, folder=database_path().parent / "plugins")
        except (ValueError, OSError) as error:
            QMessageBox.warning(parent, title, str(error))
            return
        message = f"<p>Installed {escape(pack_name)}. Restart Alto now to use its exercises?</p>"
        if QMessageBox.question(parent, "Plugin installed", message) == QMessageBox.StandardButton.Yes:
            self.restart_app()

    def uninstall_plugin(self, plugin: InstalledPlugin, *, parent: QWidget | None = None) -> None:
        """
        Move a plugin to the system trash after confirming, then restart Alto.

        Parameters
        ----------
        plugin : InstalledPlugin
            The plugin selected in the Plugins dialog.
        parent : QWidget or None, default None
            The window that owns the confirmation and messages. Defaults to this window. Keyword-only.

        Examples
        --------
        Select Viola Instrument Pack in the Plugins dialog and press Uninstall plugin.
        """
        parent = parent or self
        title = "Uninstall plugin"
        message = (
            f"<p>Move <b>{escape(plugin.title)}</b> ({escape(plugin.path.name)}) to the system trash?</p>"
            "<p>Selecting a folder moves all its contents. Alto will restart. Your practice history is kept.</p>"
        )
        if QMessageBox.question(parent, title, message) != QMessageBox.StandardButton.Yes:
            return
        lock = QLockFile(str(plugin.path.parent / ".install.lock"))
        if not lock.tryLock(0):
            QMessageBox.warning(parent, title, "Another plugin change is in progress. Try again.")
            return
        try:
            if not plugin.manifest.is_file() or not samestat(plugin.snapshot, plugin.path.lstat()):
                QMessageBox.warning(
                    parent,
                    title,
                    "The installation changed. The list has been refreshed; choose the plugin again.",
                )
                return
            pack = QFile(str(plugin.path))
            if not pack.moveToTrash():
                QMessageBox.warning(
                    parent,
                    title,
                    f"Could not move {plugin.path.name} to the system trash.\n\n{pack.errorString()}",
                )
                return
        except OSError as error:
            QMessageBox.warning(parent, title, str(error))
            return
        finally:
            lock.unlock()
        self.restart_app(quit_on_failure=True)

    def restart_app(self, *, quit_on_failure: bool = False) -> None:
        """
        Launch a fresh copy of the app, then close this one.

        Parameters
        ----------
        quit_on_failure : bool
            Close after a failed relaunch if an uninstalled pack's assets are already gone.

        Examples
        --------
        >>> MainWindow().restart_app()  # doctest: +SKIP
        """
        arguments = [] if updates.is_frozen() else ["-m", "alto"]  # a packaged build is Alto itself, not Python
        started, _ = QProcess.startDetached(sys.executable, arguments)
        if not started:
            message = "Open Alto again to finish uninstalling the plugin." if quit_on_failure else "Please restart Alto manually."
            QMessageBox.warning(self, "Could not restart Alto", message)
        if started or quit_on_failure:
            QApplication.quit()
