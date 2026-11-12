from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from . import icons

# Icon for each exercise, keyed by class name.
EXERCISE_ICONS = {
    "NoteNames": icons.EXERCISE_NOTE_NAMES,
    "KeyboardNotes": icons.EXERCISE_KEYBOARD,
    "NoteConstruction": icons.EXERCISE_CONSTRUCTION,
    "IntervalNames": icons.EXERCISE_INTERVALS,
    "KeySignatures": icons.EXERCISE_KEY_SIGNATURES,
    "ScaleDegrees": icons.EXERCISE_SCALES,
    "ChordQualities": icons.EXERCISE_CHORDS,
    "ArpeggioNames": icons.EXERCISE_ARPEGGIOS,
}


CARD_W, CARD_H, GAP = 190, 185, 14


class ExerciseCard(QPushButton):
    """A big button: icon on top, then the exercise name and a one-line description."""

    def __init__(self, cls, parent=None):
        super().__init__(parent)
        self.setFixedSize(CARD_W, CARD_H)
        self.setToolTip(cls.description)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(6)
        icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        color = self.palette().color(QPalette.ColorRole.WindowText)
        icon.setPixmap(icons.svg_icon(EXERCISE_ICONS.get(cls.__name__, icons.EXERCISE_NOTE_NAMES), color, size=56)
                       .pixmap(QSize(56, 56)))
        category = QLabel(cls.category.upper(), alignment=Qt.AlignmentFlag.AlignCenter)
        category.setStyleSheet("color: gray; font-size: 8pt; letter-spacing: 1px;")
        name = QLabel(f"<b>{cls.name}</b>", alignment=Qt.AlignmentFlag.AlignCenter)
        about = QLabel(cls.description, alignment=Qt.AlignmentFlag.AlignCenter)
        about.setWordWrap(True)
        about.setStyleSheet("color: gray; font-size: 9pt;")
        for label in (icon, category, name, about):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(icon)
        lay.addWidget(category)
        lay.addWidget(name)
        lay.addWidget(about, 1)


class HomePage(QWidget):
    """The start screen: a row of exercise buttons for each category."""

    exercise_chosen = Signal(object)  # the Exercise class

    def __init__(self, registry, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.cards = []
        for cls in registry:
            card = ExerciseCard(cls)
            card.clicked.connect(lambda _=False, c=cls: self.exercise_chosen.emit(c))
            self.cards.append(card)
        body = QWidget()  # scrolls when the window is shorter than all the rows
        self.rows = QVBoxLayout(body)  # one centred row of cards at a time
        self.rows.setContentsMargins(28, 12, 28, 12)
        self.rows.setSpacing(GAP)
        self._columns = 0
        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        body.setAutoFillBackground(False)
        self.scroll_area = scroll
        lay.addWidget(scroll, 1)
        self._reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self):
        """Rows of as many cards as fit across the page."""
        # Use the page's own width: the scroll area's viewport isn't resized yet when this runs.
        usable = self.width() - 56 - self.scroll_area.verticalScrollBar().sizeHint().width()
        columns = max(1, (usable + GAP) // (CARD_W + GAP))
        if columns == self._columns:
            return
        self._columns = columns
        while self.rows.count():  # take the old rows apart, keeping the cards
            item = self.rows.takeAt(0)
            old_row = item.layout() if item is not None else None
            if old_row is not None:
                while old_row.count():
                    old_row.takeAt(0)
                old_row.deleteLater()
        for start in range(0, len(self.cards), columns):
            row = QHBoxLayout()
            row.setSpacing(GAP)
            row.addStretch(1)
            for card in self.cards[start:start + columns]:
                row.addWidget(card)
            row.addStretch(1)
            self.rows.addLayout(row)
        self.rows.addStretch(1)
