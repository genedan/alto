from __future__ import annotations

import random
import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import settings as app_settings
from ..audio import sounds
from ..exercises.base import Exercise, Question
from ..learning import Learner
from ..settings import spell
from .colors import blend
from .icons import SLIDERS, SPEAKER_MUTED, SPEAKER_ON, svg_icon
from .keyboard import KeyboardWidget
from .settings_panel import settings_panel_for
from .staff import StaffWidget
from .staff_input import StaffInput
from .widgets import HelpButton, SidebarToggle


class ExerciseView(QWidget):
    PANE_WIDTH = 290

    def __init__(self, exercise: Exercise, rng: random.Random | None = None, parent=None, learner: Learner | None = None):
        super().__init__(parent)
        self.exercise = exercise
        self.learner = learner  # records every answer and chooses what to ask next; None asks at random
        self.rng = rng or random.Random()
        self.correct = self.total = self.streak = 0
        self.question: Question | None = None
        self.answered = False
        self.missed = False
        self._attempts = 0  # answers given to the question on screen
        self._clock = time.monotonic()  # when the last answer was given, or the question appeared

        self.score = QLabel()
        self.prompt = QLabel()
        self.prompt.setStyleSheet("font-size: 16pt;")
        self.staff = StaffWidget()
        self.keyboard = KeyboardWidget()
        self.input_staff = StaffInput()  # for 'place this note' questions
        self.input_staff.placed.connect(self._place)
        self.input_staff.accidental_cycled.connect(self._cycle_accidental)
        self.accidental_row = QWidget()  # sharp / natural / flat, for questions that need an accidental
        arow = QHBoxLayout(self.accidental_row)
        arow.setContentsMargins(0, 4, 0, 0)
        arow.addWidget(QLabel("Accidental"))
        self.accidental_group = QButtonGroup(self)
        self.accidental_group.setExclusive(False)
        self.accidental_buttons = {}
        for acc, symbol in ((-1, "♭"), (0, "♮"), (1, "♯")):
            b = QPushButton(symbol)
            b.setCheckable(True)
            b.setMinimumHeight(40)
            b.setStyleSheet("font-size: 15pt;")
            b.clicked.connect(lambda _=False, a=acc: self._pick_accidental(a))
            self.accidental_buttons[acc] = b
            arow.addWidget(b, 1)
        self.key_staff = StaffWidget(gap=8.0, side=12.0, note_offset=70.0, margin=3.6, compact=True)  # key signature only
        self.key_staff.setFixedWidth(210)
        self.choice_box = QGridLayout()
        self._advance = QTimer(self)
        self._advance.setSingleShot(True)
        self._advance.timeout.connect(self.next_question)
        self._anims: list[QVariantAnimation] = []

        top = QHBoxLayout()
        self.sidebar_button = SidebarToggle()  # wired up by the main window
        top.addWidget(self.sidebar_button)
        top.addStretch()
        top.addWidget(self.score)
        self.help_btn = HelpButton(exercise.instructions)
        top.addWidget(self.help_btn)
        self.sound_btn = QToolButton()
        self.sound_btn.setAutoRaise(True)
        self.sound_btn.setIconSize(QSize(24, 24))
        self.sound_btn.clicked.connect(self._toggle_sound)
        self._show_sound_state()
        top.addWidget(self.sound_btn)
        self.settings_panel = settings_panel_for(exercise)
        if self.settings_panel:
            self.gear = QToolButton()
            self.gear.setIcon(svg_icon(SLIDERS, self.palette().color(QPalette.ColorRole.WindowText)))
            self.gear.setIconSize(QSize(24, 24))
            self.gear.setCheckable(True)
            self.gear.setAutoRaise(True)
            self.gear.setToolTip("Exercise settings")
            top.addWidget(self.gear)
        main = QWidget()
        lay = QVBoxLayout(main)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(top)
        lay.addWidget(self.prompt)
        lay.addWidget(self.staff)
        lay.addWidget(self.input_staff)
        lay.addWidget(self.accidental_row)
        lay.addWidget(self.key_staff, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.keyboard)
        lay.addLayout(self.choice_box)
        self.octave_row = QWidget()  # shown only when the answer needs an octave as well as a name
        self.octave_box = QHBoxLayout(self.octave_row)
        self.octave_box.setContentsMargins(0, 4, 0, 0)
        lay.addWidget(self.octave_row)
        lay.addStretch()
        outer = QHBoxLayout(self)
        outer.addWidget(main, 1)
        if self.settings_panel:
            # Collapsible pane on the right, toggled by the gear.
            self.pane = QFrame()
            self.pane.setObjectName("settingsPane")
            self.pane.setFrameShape(QFrame.Shape.StyledPanel)
            self.pane.setMinimumWidth(0)
            self.pane.setMaximumWidth(0)
            pane_lay = QVBoxLayout(self.pane)
            pane_lay.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)  # let the pane shrink to zero while animating
            self.settings_panel.setFixedWidth(self.PANE_WIDTH - 2 * 9)
            pane_lay.addWidget(self.settings_panel, 1)  # fill the pane so long pages (Range) can scroll
            self.pane.hide()
            outer.addWidget(self.pane)
            self._pane_anim = QPropertyAnimation(self.pane, b"maximumWidth", self)
            self._pane_anim.setDuration(220)
            self._pane_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._pane_anim.finished.connect(self._pane_settled)
            self.gear.toggled.connect(self._toggle_pane)
            self.settings_panel.changed.connect(self.next_question)  # apply new settings right away
        self.buttons: list[QPushButton] = []
        self.next_question()

    def _toggle_sound(self):
        sounds.enabled = not sounds.enabled
        self._show_sound_state()

    def _show_sound_state(self):
        color = self.palette().color(QPalette.ColorRole.WindowText)
        self.sound_btn.setIcon(svg_icon(SPEAKER_ON if sounds.enabled else SPEAKER_MUTED, color))
        self.sound_btn.setToolTip("Sound on (click to mute)" if sounds.enabled else "Muted (click to unmute)")

    def _toggle_pane(self, open_: bool):
        """Slide the settings pane open or closed."""
        self._pane_anim.stop()
        self.pane.show()
        self._pane_anim.setStartValue(self.pane.maximumWidth())
        self._pane_anim.setEndValue(self.PANE_WIDTH if open_ else 0)
        self._pane_anim.start()

    def _pane_settled(self):
        if self.pane.maximumWidth() == 0:
            self.pane.hide()

    def _pick_question(self) -> Question:
        """A question drawn by what the learner needs, or at random without a profile."""
        if self.learner is None:
            return self.exercise.generate(self.rng)
        return self.learner.pick(self.exercise, self.rng, avoid=self.question.item_key() if self.question else None)

    def next_question(self):
        self._advance.stop()
        self._anims.clear()
        q = self.question = self._pick_question()
        self.answered = False
        self.missed = False
        self._attempts = 0
        self._clock = time.monotonic()
        self._pair_token = getattr(self, "_pair_token", 0) + 1  # cancels a pending 'try again' reset
        self._pending = {}  # 'name' / 'octave' -> (text, button), for two-part answers
        self._busy = False
        self.prompt.setText(q.prompt)
        self.prompt.setVisible(bool(q.prompt))  # some exercises need no prompt
        construct = q.construct is not None
        self.staff.setVisible((bool(q.staff) or q.show_staff) and not construct)
        self.input_staff.setVisible(construct)
        self.accidental_row.setVisible(construct and q.accidentals)
        if construct:
            self.input_staff.reset(q.clef, q.key)
            for b in self.accidental_buttons.values():
                b.setChecked(False)
        self.keyboard.setVisible(q.keyboard is not None)
        self.key_staff.setVisible(q.key_staff)
        self.key_staff.show_notes([], "treble", q.key)
        self.keyboard.max_key_width = 30.0 if q.key_staff else 38.0  # leave room for the staff above
        self.keyboard.show_key(q.keyboard.midi if q.keyboard else None, q.keyboard_range)
        self.staff.show_notes(q.staff, q.clef, q.key, q.value)
        for b in self.buttons:
            b.deleteLater()
        self.buttons = []
        for col in range(self.choice_box.columnCount()):
            self.choice_box.setColumnStretch(col, 0)
        for i, c in enumerate(q.choices):
            b = QPushButton(c)
            b.setMinimumHeight(40)
            if len(q.choices) <= 9 and not q.octaves:  # number-key shortcuts only when every choice can have one
                b.setShortcut(str(i + 1))
                b.setToolTip(f"Key {i + 1}")
            if q.octaves:
                b.setCheckable(True)
                b.clicked.connect(lambda _=False, choice=c, btn=b: self._pick("name", choice, btn))
            else:
                b.clicked.connect(lambda _=False, choice=c, btn=b: self.submit(choice, btn))
            row, col = q.grid[c] if q.grid else (0, i)
            self.choice_box.addWidget(b, row, col)
            self.buttons.append(b)
        for col in {(q.grid[c][1] if q.grid else i) for i, c in enumerate(q.choices)}:
            self.choice_box.setColumnStretch(col, 1)  # equal-width columns
        while self.octave_box.count():
            item = self.octave_box.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self.octave_row.setVisible(bool(q.octaves))
        if q.octaves:
            self.octave_box.addWidget(QLabel(q.second_label))
            for octave in q.octaves:
                b = QPushButton(octave)
                b.setMinimumHeight(40)
                b.setCheckable(True)
                b.clicked.connect(lambda _=False, text=octave, btn=b: self._pick("octave", text, btn))
                self.octave_box.addWidget(b, 1)
                self.buttons.append(b)
        self._update_score()

    @staticmethod
    def _style(color: QColor) -> str:
        return f"QPushButton, QPushButton:disabled {{ background: {color.name()}; color: white; }}"

    def _flash(self, button: QPushButton, target: str, staff: bool = False):
        """Animate from the staff ink to `target` over a short time."""
        end, start = QColor(target), QColor("black")
        anim = QVariantAnimation(self)
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def step(t: float):
            c = blend(start, end, t)
            button.setStyleSheet(self._style(c))
            if staff:
                self.staff.set_note_color(c if t > 0 else None)
                if self.question and self.question.keyboard:
                    self.keyboard.set_highlight_color(c if t > 0 else self.palette().color(QPalette.ColorRole.Highlight))

        anim.valueChanged.connect(step)
        self._anims.append(anim)
        anim.start()

    def _set_accidental(self, accidental: int | None):
        """Use this sign for the next note (None follows the key signature): light its button and update the preview."""
        for a, b in self.accidental_buttons.items():
            b.setChecked(accidental is not None and a == accidental)
        self.input_staff.accidental = accidental
        self.input_staff.refresh_preview()

    def _pick_accidental(self, accidental: int):
        """The buttons act like a radio group, and clicking the lit one again clears it."""
        lit = self.accidental_buttons[accidental].isChecked()  # the click has already toggled it
        self._set_accidental(accidental if lit else None)

    def _cycle_accidental(self):
        """Right click on the staff: no sign, sharp, flat, and (under a key signature) natural, then round again."""
        q = self.question
        if q and q.construct is not None and q.accidentals:
            order = [None, 1, -1, 0] if q.key else [None, 1, -1]  # without a key a natural is the same as no sign
            current = self.input_staff.accidental
            self._set_accidental(order[(order.index(current) + 1) % len(order)] if current in order else None)

    def _flash_note(self, target: str):
        """Fade the placed note from the staff ink to `target`."""
        end, start = QColor(target), QColor("black")
        anim = QVariantAnimation(self)
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(lambda t: self.input_staff.set_note_color(blend(start, end, t)))
        self._anims.append(anim)
        anim.start()

    def _place(self, note):
        """A note was clicked onto the staff: check it against the one we asked for."""
        q = self.question
        if not q or q.construct is None or self.answered or self._busy:
            return
        ok = q.check_placed(note)
        self._record(ok, f"{spell(note, app_settings.note_names.naming)}{note.octave}")
        self.input_staff.locked = True
        if ok:
            self.answered = True
            self._flash_note("#2e7d32")
            sounds.play_notes([[q.construct]])
            self._advance.start(1200)
        else:
            self.missed = True
            self._busy = True
            self._flash_note("#c62828")
            token = self._pair_token

            def retry():
                if token != self._pair_token:  # a new question replaced this one
                    return
                self.input_staff.locked = False
                self.input_staff.show_note(None)
                self._busy = False

            QTimer.singleShot(900, retry)
        self._update_score()

    def _record(self, ok: bool, choice: str = ""):
        self._attempts += 1
        now = time.monotonic()
        seconds, self._clock = now - self._clock, now  # the first answer is timed from the question appearing
        if self.learner and self.question:
            self.learner.record(self.exercise, self.question, choice, ok, self._attempts, seconds)
        if not self.missed:  # only the first attempt counts toward the score
            self.total += 1
            self.correct += ok
            self.streak = self.streak + 1 if ok else 0

    def _pick(self, part: str, text: str, button: QPushButton):
        """Two-part answer: choose a name and then an octave (or a chord type and an inversion), in either order; the
        answer is checked once both are set."""
        if self.answered or self._busy:
            return
        previous = self._pending.get(part)
        if previous and previous[1] is not button:
            previous[1].setChecked(False)
        button.setChecked(True)
        self._pending[part] = (text, button)
        if len(self._pending) == 2:
            self._submit_pair()

    def _submit_pair(self):
        q = self.question
        assert q is not None
        (name, name_btn), (octave, octave_btn) = self._pending["name"], self._pending["octave"]
        choice = name + q.joiner + octave
        if q.check(choice):
            self._flash(octave_btn, "#2e7d32")
            self.submit(choice, name_btn)  # scores it, flashes the name button, plays the note, moves on
            return
        self._record(False, choice)
        self.missed = True
        self._busy = True
        for b in (name_btn, octave_btn):
            self._flash(b, "#c62828")
        self._update_score()
        token = self._pair_token

        def reset():
            if token != self._pair_token:  # a new question replaced these buttons
                return
            for b in (name_btn, octave_btn):
                b.setStyleSheet("")
                b.setChecked(False)
            self._pending = {}
            self._busy = False

        QTimer.singleShot(700, reset)

    def submit(self, choice: str, button: QPushButton):
        if self.answered or not self.question or not button.isEnabled():
            return
        q = self.question
        ok = q.check(choice)
        self._record(ok, choice)
        if ok:
            self.answered = True
            for b in self.buttons:
                b.setEnabled(False)
            self._flash(button, "#2e7d32", staff=True)
            notes = q.staff or q.play or ([[q.keyboard]] if q.keyboard else [])
            if notes:
                sounds.play_notes(notes)
            else:
                sounds.play_correct(self.streak)
            self._advance.start(1200)
        else:
            self.missed = True
            button.setEnabled(False)
            self._flash(button, "#c62828")
        self._update_score()

    def _update_score(self):
        pct = f"{100 * self.correct / self.total:.0f}%" if self.total else "–"
        self.score.setText(f"{self.correct}/{self.total} ({pct})   streak {self.streak}")
