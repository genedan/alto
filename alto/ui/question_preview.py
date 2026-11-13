"""A popup showing a stored question the way the exercise showed it, with its answer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import settings as app_settings
from ..audio import sounds
from ..exercises.base import Question
from ..settings import spell
from .keyboard import KeyboardWidget
from .staff import MAX_STEP, StaffWidget


class QuestionPreview(QDialog):
    """`question` as it appeared (the notes on the staff, or the highlighted key), then what the answer is.
    `details` are extra lines, such as what was answered and how long it took."""

    def __init__(self, exercise_name: str, question: Question, details: list[str] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.question = question
        self.setWindowTitle(exercise_name)
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        title = QLabel(f"<h3>{exercise_name}</h3>")
        lay.addWidget(title)
        if question.prompt and not question.caption:
            prompt = QLabel(question.prompt)
            prompt.setWordWrap(True)
            prompt.setStyleSheet("font-size: 14pt;")
            lay.addWidget(prompt)

        q = question
        if q.staff or q.show_staff or q.construct is not None:
            staff = StaffWidget(max_step=MAX_STEP)
            # a "place this note" question shows the note that was the answer
            notes = q.staff or ([[q.construct]] if q.construct is not None else [])
            staff.show_notes(notes, q.clef, q.key, q.value, q.caption)
            lay.addWidget(staff, alignment=Qt.AlignmentFlag.AlignHCenter)
        if q.keyboard is not None:
            if q.key_staff:
                key_staff = StaffWidget(gap=8.0, side=12.0, note_offset=70.0, margin=3.6, compact=True)
                key_staff.setFixedWidth(210)
                key_staff.show_notes([], "treble", q.key)
                lay.addWidget(key_staff, alignment=Qt.AlignmentFlag.AlignHCenter)
            keyboard = KeyboardWidget()
            keyboard.max_key_width = 30.0 if q.key_staff else 38.0
            keyboard.show_key(q.keyboard.midi, q.keyboard_range)
            lay.addWidget(keyboard)

        lines = [f"<b>Answer:</b> {self._answer_text()}"]
        if q.choices:
            lines.append("<span style='color: gray;'>Choices: " + "  ·  ".join(q.choices) + "</span>")
        if q.octaves:
            lines.append(f"<span style='color: gray;'>{q.second_label}: " + "  ·  ".join(q.octaves) + "</span>")
        lines += details or []
        if q.explanation:
            lines.append(q.explanation)
        info = QLabel("<br>".join(lines))
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(info)

        buttons = QDialogButtonBox()
        notes = q.staff or ([[q.keyboard]] if q.keyboard else [[q.construct]] if q.construct is not None else [])
        if notes:
            play = QPushButton("Play")
            play.clicked.connect(lambda: sounds.play_notes(notes))
            buttons.addButton(play, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        lay.addWidget(buttons)

    def _answer_text(self) -> str:
        q = self.question
        if q.construct is not None:
            return f"{spell(q.construct, app_settings.note_names.naming)}{q.construct.octave}"
        return q.answer
