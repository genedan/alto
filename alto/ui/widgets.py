from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout, QWidget

from .icons import HELP, SIDEBAR_CLOSED, SIDEBAR_OPEN, svg_icon


class SidebarToggle(QToolButton):
    """A button that shows or hides the exercise list. Connect to `clicked`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoRaise(True)
        self.setIconSize(QSize(24, 24))  # same size as the sound and settings buttons
        self.set_open(True)

    def set_open(self, is_open: bool) -> None:
        color = self.palette().color(QPalette.WindowText)  # same colour as the sound and settings icons
        self.setIcon(svg_icon(SIDEBAR_OPEN if is_open else SIDEBAR_CLOSED, color))
        self.setToolTip("Hide exercise list" if is_open else "Show exercise list")


class HelpButton(QToolButton):
    """A "?" button that opens a small popover with help text. Click anywhere else to close it."""

    def __init__(self, text_provider, parent=None):
        super().__init__(parent)
        self._text = text_provider  # called each time, so the text can follow the current settings
        self.setAutoRaise(True)
        self.setIcon(svg_icon(HELP, self.palette().color(QPalette.WindowText)))
        self.setIconSize(QSize(24, 24))
        self.setToolTip("How this exercise works")
        self.clicked.connect(self.show_help)
        self._popup: QWidget | None = None

    def show_help(self) -> None:
        popup = QWidget(self, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground)  # lets the card's rounded corners show
        card = QFrame(popup)
        card.setObjectName("helpCard")
        label = QLabel(self._text())
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setFixedWidth(340)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 14, 16, 14)
        inner.addWidget(label)
        outer = QVBoxLayout(popup)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        popup.adjustSize()
        # right-aligned under the button
        below = self.mapToGlobal(QPoint(self.width() - popup.width(), self.height() + 4))
        popup.move(max(below.x(), 8), below.y())
        popup.show()
        self._popup = popup
