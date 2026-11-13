"""
Small widgets shared by several screens: the sidebar toggle and the help button.

Examples
--------
>>> SidebarToggle().toolTip()
'Hide exercise list'
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QPoint,
    QSize,
    Qt,
)
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from alto.ui.icons import (
    HELP,
    SIDEBAR_CLOSED,
    SIDEBAR_OPEN,
    svg_icon,
)


class SidebarToggle(QToolButton):
    """
    A button that shows or hides the exercise list.

    Connect to `clicked`; the main window decides what to show and calls `set_open` to match.

    Examples
    --------
    >>> button = SidebarToggle()
    >>> button.toolTip()
    'Hide exercise list'
    >>> button.set_open(False)
    >>> button.toolTip()
    'Show exercise list'
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Create the toggle, showing the list as open.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the button.

        Examples
        --------
        >>> SidebarToggle().autoRaise()
        True
        """
        super().__init__(parent)
        self.setAutoRaise(True)
        self.setIconSize(QSize(24, 24))  # same size as the sound and settings buttons
        self.set_open(True)

    def set_open(self, is_open: bool) -> None:
        """
        Show the icon and tooltip for the list being open or closed.

        Parameters
        ----------
        is_open : bool
            True if the exercise list is showing.

        Examples
        --------
        >>> button = SidebarToggle()
        >>> button.set_open(False)
        >>> button.toolTip()
        'Show exercise list'
        """
        color = self.palette().color(QPalette.ColorRole.WindowText)  # same colour as the sound and settings icons
        self.setIcon(svg_icon(SIDEBAR_OPEN if is_open else SIDEBAR_CLOSED, color=color))
        self.setToolTip("Hide exercise list" if is_open else "Show exercise list")


class HelpButton(QToolButton):
    """
    A "?" button that opens a small popover with help text.

    Click anywhere else to close it.

    Examples
    --------
    >>> HelpButton(lambda: "<b>Press the right note.</b>").toolTip()
    'How this exercise works'
    """

    def __init__(
        self,
        text_provider: Callable[[], str],
        *,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create the button.

        Parameters
        ----------
        text_provider : callable
            Called with no arguments each time the help is shown, so the text can follow the current settings. It returns simple
            HTML.
        parent : QWidget or None, default None
            The widget that owns the button. Keyword-only.

        Examples
        --------
        >>> calls = []
        >>> button = HelpButton(lambda: calls.append(1) or "help")
        >>> calls  # the text is not asked for until the button is clicked
        []
        """
        super().__init__(parent)
        self._text = text_provider  # called each time, so the text can follow the current settings
        self.setAutoRaise(True)
        self.setIcon(svg_icon(HELP, color=self.palette().color(QPalette.ColorRole.WindowText)))
        self.setIconSize(QSize(24, 24))
        self.setToolTip("How this exercise works")
        self.clicked.connect(self.show_help)
        self._popup: QWidget | None = None

    def show_help(self) -> None:
        """
        Open the popover under the button, right-aligned with it.

        Examples
        --------
        >>> HelpButton(lambda: "<b>Help</b>").show_help()  # doctest: +SKIP
        """
        popup = QWidget(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # lets the card's rounded corners show
        card = QFrame(popup)
        card.setObjectName("helpCard")
        label = QLabel(self._text())
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setFixedWidth(340)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        inner.addWidget(label)
        outer = QVBoxLayout(popup)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.addWidget(card)
        popup.adjustSize()
        # right-aligned under the button
        below = self.mapToGlobal(QPoint(self.width() - popup.width(), self.height() + 4))
        popup.move(max(below.x(), 8), below.y())
        popup.show()
        self._popup = popup
