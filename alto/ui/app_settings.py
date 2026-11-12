from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..theory.pitch import Note
from . import notation
from .instrument_picker import InstrumentPicker
from .staff import StaffWidget
from .theme import THEMES, apply_theme, save_theme, saved_theme


class StyleCard(QPushButton):
    """A selectable tile that previews a notation style: a short phrase on a staff, drawn in that style."""

    def __init__(self, style: notation.NotationStyle, parent=None):
        super().__init__(parent)
        self.style_key = style.key
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(232, 150)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)
        self.staff = StaffWidget(gap=6.5, side=8.0, note_offset=44.0, margin=3.2, compact=True)
        self.staff.style = style
        self.staff.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.staff.setFixedWidth(214)
        self.staff.show_notes([[Note(4, 2)], [Note(4, 4)], [Note(5, 0)], [Note(4, 6)]], "treble", key=1, value="quarter")
        name = QLabel(f"<b>{style.label}</b>")
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        blurb = QLabel(style.note)
        blurb.setStyleSheet("color: gray; font-size: 9pt;")
        blurb.setWordWrap(True)
        blurb.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.staff)
        lay.addWidget(name)
        lay.addWidget(blurb)


class AppSettingsDialog(QDialog):
    """Application-wide settings. Changes apply immediately."""


    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(1000, 640)
        self.theme_changed = False
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        # The categories sit in a list on the left; choosing one shows its settings on the right.
        self.categories = QListWidget()
        self.categories.setObjectName("categories")  # styled in style.py
        self.categories.setFixedWidth(170)
        self.pages = QStackedWidget()
        for name, page in (("Appearance", self._scrolling(self._appearance_page())), ("Sound", self._sound_page())):
            item = QListWidgetItem(name)
            item.setSizeHint(QSize(0, 36))
            self.categories.addItem(item)
            self.pages.addWidget(page)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.categories.setCurrentRow(0)
        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self.categories)
        body.addWidget(self.pages, 1)
        lay.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        lay.addWidget(buttons)

    @staticmethod
    def _page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        return page, lay

    @staticmethod
    def _heading(lay: QVBoxLayout, title: str, about: str) -> None:
        lay.addWidget(QLabel(f"<h3>{title}</h3>"))
        text = QLabel(about)
        text.setStyleSheet("color: gray;")
        text.setWordWrap(True)
        lay.addWidget(text)

    @staticmethod
    def _scrolling(page: QWidget) -> QScrollArea:
        """A page that scrolls when it is taller than the dialog."""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def _appearance_page(self) -> QWidget:
        page, lay = self._page()
        self._heading(lay, "Theme", "Follow the system's light or dark setting, or always use one of them.")
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        theme_group = QButtonGroup(self)
        theme_group.setExclusive(True)
        current = saved_theme()
        for key, label in THEMES:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(key == current)
            b.setFixedHeight(40)
            theme_group.addButton(b)
            b.clicked.connect(lambda _=False, k=key: self.choose_theme(k))
            theme_row.addWidget(b)
        theme_row.addStretch(1)
        lay.addLayout(theme_row)
        lay.addSpacing(6)
        self._heading(lay, "Notation style", "The music font used to draw clefs, notes and accidentals.")
        grid = QGridLayout()
        grid.setSpacing(10)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for i, st in enumerate(notation.STYLES):
            card = StyleCard(st)
            card.setChecked(st.key == notation.current().key)
            group.addButton(card)
            card.clicked.connect(lambda _=False, k=st.key: notation.set_style(k))
            grid.addWidget(card, i // 3, i % 3)
        grid.setColumnStretch(3, 1)  # keep the cards at the left edge
        lay.addLayout(grid)
        lay.addStretch(1)
        return page

    def _sound_page(self) -> QWidget:
        page, lay = self._page()
        self._heading(lay, "Instrument",
                      "The sound used for notes and for the correct-answer chime. Choose an instrument to see what it is "
                      "made from, and press Hear it to listen.")
        self.instruments = InstrumentPicker()
        lay.addWidget(self.instruments, 1)
        return page

    def choose_theme(self, key: str) -> None:
        save_theme(key)
        apply_theme(key)
        self.theme_changed = True
