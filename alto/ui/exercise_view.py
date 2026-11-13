"""
The exercise screen: a question, its answer buttons, the score, and a pane of settings that slides in from the right.

One `ExerciseView` works for every exercise. It asks the exercise (or, with a profile, the learner) for the next
`Question`, shows it as a staff, a keyboard or text, offers the answer buttons, and records each answer.

Examples
--------
>>> from alto.exercises.library import NoteNames
>>> view = ExerciseView(NoteNames(), rng=random.Random(1))
>>> view.question.answer in [button.text() for button in view.buttons]
True
"""

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
from ..theory.pitch import Note
from .colors import blend
from .icons import SLIDERS, SPEAKER_MUTED, SPEAKER_ON, svg_icon
from .keyboard import KeyboardWidget
from .settings_panel import settings_panel_for
from .staff import MAX_STEP, StaffWidget
from .staff_input import StaffInput
from .widgets import HelpButton, SidebarToggle


class ExerciseView(QWidget):
    """
    The screen for practising one exercise.

    Attributes
    ----------
    PANE_WIDTH : int
        The width of the settings pane when it is open, in pixels.
    exercise : Exercise
        The exercise being practised.
    learner : Learner or None
        Records every answer and chooses what to ask next; None asks at random.
    rng : random.Random
        The random number generator for new questions.
    correct : int
        Questions answered right first time.
    total : int
        Questions answered.
    streak : int
        Right answers in a row.
    question : Question or None
        The question on screen.
    answered : bool
        True once the question has been answered right.
    missed : bool
        True once the question has been answered wrong, so it no longer counts towards the score.
    buttons : list of QPushButton
        The answer buttons on screen.
    settings_panel : QWidget or None
        The exercise's settings, or None for an exercise with none.
    staff : StaffWidget
        Shows the notes of a question.
    keyboard : KeyboardWidget
        Shows the key of a keyboard question.
    input_staff : StaffInput
        The staff to click, for "place this note" questions.

    Examples
    --------
    >>> from alto.exercises.library import NoteNames
    >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
    >>> view.score.text()
    '0/0 (–)   streak 0'
    """

    PANE_WIDTH = 290

    def __init__(
        self,
        exercise: Exercise,
        *,
        rng: random.Random | None = None,
        parent: QWidget | None = None,
        learner: Learner | None = None,
    ) -> None:
        """
        Build the screen and show the first question.

        Parameters
        ----------
        exercise : Exercise
            The exercise to practise.
        rng : random.Random or None, default None
            The random number generator; a fresh one if None. Keyword-only.
        parent : QWidget or None, default None
            The widget that owns the screen. Keyword-only.
        learner : Learner or None, default None
            Where to record answers and what to ask next; None asks at random and records nothing. Keyword-only.

        Examples
        --------
        >>> from alto.exercises.library import KeySignatures
        >>> view = ExerciseView(KeySignatures(), rng=random.Random(2))
        >>> view.settings_panel is not None  # the exercise has settings behind the gear button
        True
        """
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
        self.staff = StaffWidget(max_step=MAX_STEP)
        self.keyboard = KeyboardWidget()
        self.input_staff = StaffInput()  # for 'place this note' questions
        self.input_staff.placed.connect(self._place)
        self.input_staff.accidental_cycled.connect(self._cycle_accidental)
        self.accidental_row = QWidget()  # sharp / natural / flat, for questions that need an accidental
        arow = QHBoxLayout(self.accidental_row)
        arow.setContentsMargins(
            0,
            4,
            0,
            0,
        )
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
        self.key_staff = StaffWidget(
            gap=8.0,
            side=12.0,
            note_offset=70.0,
            margin=3.6,
            compact=True,
        )  # key signature only
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
            self.gear.setIcon(svg_icon(SLIDERS, color=self.palette().color(QPalette.ColorRole.WindowText)))
            self.gear.setIconSize(QSize(24, 24))
            self.gear.setCheckable(True)
            self.gear.setAutoRaise(True)
            self.gear.setToolTip("Exercise settings")
            top.addWidget(self.gear)
        main = QWidget()
        lay = QVBoxLayout(main)
        lay.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        lay.addLayout(top)
        lay.addWidget(self.prompt)
        lay.addWidget(self.staff, alignment=Qt.AlignmentFlag.AlignHCenter)  # a capped staff sits in the middle
        lay.addWidget(self.input_staff, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.accidental_row)
        lay.addWidget(self.key_staff, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.keyboard)
        lay.addLayout(self.choice_box)
        self.octave_row = QWidget()  # shown only when the answer needs an octave as well as a name
        self.octave_box = QHBoxLayout(self.octave_row)
        self.octave_box.setContentsMargins(
            0,
            4,
            0,
            0,
        )
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

    def _toggle_sound(self) -> None:
        """
        Switch the app's sound on or off and show the button to match.

        The sound button is a mute for the whole app, so this changes `sounds.enabled`, not just this exercise.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> before = sounds.enabled
        >>> view._toggle_sound()
        >>> sounds.enabled == (not before)
        True
        >>> view._toggle_sound()
        """
        sounds.enabled = not sounds.enabled
        self._show_sound_state()

    def _show_sound_state(self) -> None:
        """
        Show the sound button's icon and tooltip for whether sound is on.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._show_sound_state()
        >>> view.sound_btn.toolTip().startswith(("Sound on", "Muted"))
        True
        """
        color = self.palette().color(QPalette.ColorRole.WindowText)
        self.sound_btn.setIcon(svg_icon(SPEAKER_ON if sounds.enabled else SPEAKER_MUTED, color=color))
        self.sound_btn.setToolTip("Sound on (click to mute)" if sounds.enabled else "Muted (click to unmute)")

    def _toggle_pane(self, open_: bool) -> None:
        """
        Slide the settings pane open or closed.

        Parameters
        ----------
        open_ : bool
            True to open it, False to close it.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._toggle_pane(True)
        >>> view._pane_anim.endValue()
        290
        """
        self._pane_anim.stop()
        self.pane.show()
        self._pane_anim.setStartValue(self.pane.maximumWidth())
        self._pane_anim.setEndValue(self.PANE_WIDTH if open_ else 0)
        self._pane_anim.start()

    def _pane_settled(self) -> None:
        """
        Hide the pane once it has finished sliding shut.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._pane_settled()  # the pane starts closed
        >>> view.pane.isVisible()
        False
        """
        if self.pane.maximumWidth() == 0:
            self.pane.hide()

    def _pick_question(self) -> Question:
        """
        Choose the next question.

        Returns
        -------
        Question
            One drawn by what the learner needs, or at random without a profile. The one just asked is avoided.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> isinstance(view._pick_question(), Question)
        True
        """
        if self.learner is None:
            return self.exercise.generate(self.rng)
        return self.learner.pick(self.exercise, rng=self.rng, avoid=self.question.item_key() if self.question else None)

    def next_question(self) -> None:
        """
        Show the next question: its staff, keyboard or text, and a fresh set of answer buttons.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view.next_question()
        >>> view.answered, len(view.buttons) == len(view.question.choices)
        (False, True)
        """
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
        self.prompt.setVisible(bool(q.prompt) and not q.caption)  # some need none; a caption goes on the staff
        construct = q.construct is not None
        self.staff.setVisible((bool(q.staff) or q.show_staff) and not construct)
        self.input_staff.setVisible(construct)
        self.accidental_row.setVisible(construct and q.accidentals)
        if construct:
            self.input_staff.reset(q.clef, key=q.key)
            for b in self.accidental_buttons.values():
                b.setChecked(False)
        self.keyboard.setVisible(q.keyboard is not None)
        self.key_staff.setVisible(q.key_staff)
        self.key_staff.show_notes([], clef="treble", key=q.key)
        self.keyboard.max_key_width = 30.0 if q.key_staff else 38.0  # leave room for the staff above
        self.keyboard.show_key(q.keyboard.midi if q.keyboard else None, span=q.keyboard_range)
        self.staff.show_notes(
            q.staff,
            clef=q.clef,
            key=q.key,
            value=q.value,
            caption=q.caption,
        )
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
                b.clicked.connect(lambda _=False, choice=c, btn=b: self._pick("name", text=choice, button=btn))
            else:
                b.clicked.connect(lambda _=False, choice=c, btn=b: self.submit(choice, button=btn))
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
                b.clicked.connect(lambda _=False, text=octave, btn=b: self._pick("octave", text=text, button=btn))
                self.octave_box.addWidget(b, 1)
                self.buttons.append(b)
        self._update_score()

    @staticmethod
    def _style(color: QColor) -> str:
        """
        Return the style sheet that colours an answer button.

        Parameters
        ----------
        color : QColor
            The background colour, with white text on it.

        Returns
        -------
        str
            Qt style sheet text.

        Examples
        --------
        >>> ExerciseView._style(QColor("#2e7d32"))
        'QPushButton, QPushButton:disabled { background: #2e7d32; color: white; }'
        """
        return f"QPushButton, QPushButton:disabled {{ background: {color.name()}; color: white; }}"

    def _flash(
        self,
        button: QPushButton,
        *,
        target: str,
        staff: bool = False,
    ) -> None:
        """
        Fade a button (and optionally the notes) from the staff's ink to a colour over a short time.

        Parameters
        ----------
        button : QPushButton
            The button to colour.
        target : str
            The colour to fade to, such as '#2e7d32'. Keyword-only.
        staff : bool, default False
            Also colour the notes on the staff, or the highlighted key. Keyword-only.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._flash(view.buttons[0], target="#2e7d32")
        >>> len(view._anims)
        1
        """
        end, start = QColor(target), QColor("black")
        anim = QVariantAnimation(self)
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def step(t: float) -> None:
            """
            Set the colours for one moment of the fade.

            Parameters
            ----------
            t : float
                How far through the fade: 0 at the start, 1 at the end.

            Examples
            --------
            >>> step(0.5)  # doctest: +SKIP
            """
            c = blend(start, b=end, t=t)
            button.setStyleSheet(self._style(c))
            if staff:
                self.staff.set_note_color(c if t > 0 else None)
                if self.question and self.question.keyboard:
                    self.keyboard.set_highlight_color(c if t > 0 else self.palette().color(QPalette.ColorRole.Highlight))

        anim.valueChanged.connect(step)
        self._anims.append(anim)
        anim.start()

    def _set_accidental(self, accidental: int | None) -> None:
        """
        Use a sign for the next note, light its button and update the preview.

        Parameters
        ----------
        accidental : int or None
            -1 for a flat, 0 for a natural, 1 for a sharp, or None to follow the key signature.

        Examples
        --------
        >>> from alto.exercises.library import NoteConstruction
        >>> view = ExerciseView(NoteConstruction(), rng=random.Random(2))
        >>> view._set_accidental(1)
        >>> view.input_staff.accidental, view.accidental_buttons[1].isChecked()
        (1, True)
        >>> view._set_accidental(None)
        >>> view.input_staff.accidental is None
        True
        """
        for a, b in self.accidental_buttons.items():
            b.setChecked(accidental is not None and a == accidental)
        self.input_staff.accidental = accidental
        self.input_staff.refresh_preview()

    def _pick_accidental(self, accidental: int) -> None:
        """
        Handle a click on a sign button.

        The buttons act like a radio group, and clicking the lit one again clears it.

        Parameters
        ----------
        accidental : int
            The sign of the button that was clicked: -1, 0 or 1.

        Examples
        --------
        >>> from alto.exercises.library import NoteConstruction
        >>> view = ExerciseView(NoteConstruction(), rng=random.Random(2))
        >>> view.accidental_buttons[-1].click()
        >>> view.input_staff.accidental
        -1
        >>> view.accidental_buttons[-1].click()  # clicking the lit one again clears it
        >>> view.input_staff.accidental is None
        True
        """
        lit = self.accidental_buttons[accidental].isChecked()  # the click has already toggled it
        self._set_accidental(accidental if lit else None)

    def _cycle_accidental(self) -> None:
        """
        Step to the next sign after a right click on the staff.

        The order is no sign, sharp, flat and (under a key signature) natural, then round again. It does nothing unless the
        question asks for signs.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._cycle_accidental()  # not a "place this note" question: nothing happens
        >>> view.input_staff.accidental is None
        True
        """
        q = self.question
        if q and q.construct is not None and q.accidentals:
            order = (
                [
                    None,
                    1,
                    -1,
                    0,
                ]
                if q.key
                else [None, 1, -1]
            )  # without a key a natural is the same as no sign
            current = self.input_staff.accidental
            self._set_accidental(order[(order.index(current) + 1) % len(order)] if current in order else None)

    def _flash_note(self, target: str) -> None:
        """
        Fade the placed note from the staff's ink to a colour.

        Parameters
        ----------
        target : str
            The colour to fade to, such as '#c62828'.

        Examples
        --------
        >>> from alto.exercises.library import NoteConstruction
        >>> view = ExerciseView(NoteConstruction(), rng=random.Random(2))
        >>> view._flash_note("#c62828")
        >>> len(view._anims)
        1
        """
        end, start = QColor(target), QColor("black")
        anim = QVariantAnimation(self)
        anim.setDuration(350)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(lambda t: self.input_staff.set_note_color(blend(start, b=end, t=t)))
        self._anims.append(anim)
        anim.start()

    def _place(self, note: Note) -> None:
        """
        Check a note that was clicked onto the staff against the one asked for.

        A right note is scored, fades green, plays and moves on; a wrong one fades red and the staff clears so another can be
        tried.

        Parameters
        ----------
        note : Note
            The note that was placed.

        Examples
        --------
        >>> from alto.exercises.library import NoteConstruction
        >>> sounds.enabled = False
        >>> view = ExerciseView(NoteConstruction(), rng=random.Random(2))
        >>> view._place(view.question.construct)
        >>> view.answered, view.correct
        (True, 1)
        >>> view._advance.stop()
        >>> sounds.enabled = True
        """
        q = self.question
        if not q or q.construct is None or self.answered or self._busy:
            return
        ok = q.check_placed(note)
        self._record(ok, choice=f"{spell(note, naming=app_settings.note_names.naming)}{note.octave}")
        self.input_staff.locked = True
        if ok:
            self.answered = True
            self._flash_note("#2e7d32")
            if self.exercise.has_sound:
                sounds.play_notes([[q.construct]])
            self._advance.start(1200)
        else:
            self.missed = True
            self._busy = True
            self._flash_note("#c62828")
            token = self._pair_token

            def retry() -> None:
                """
                Clear the staff so a wrong placement can be tried again, unless a new question has replaced it.

                Examples
                --------
                >>> retry()  # doctest: +SKIP
                """
                if token != self._pair_token:  # a new question replaced this one
                    return
                self.input_staff.locked = False
                self.input_staff.show_note(None)
                self._busy = False

            QTimer.singleShot(900, retry)
        self._update_score()

    def _record(
        self,
        ok: bool,
        *,
        choice: str = "",
    ) -> None:
        """
        Count an answer and log it.

        Only the first attempt at a question counts towards the score and the streak. Each attempt is recorded with its time,
        measured from the question appearing (first attempt) or the previous attempt.

        Parameters
        ----------
        ok : bool
            Whether the answer was right.
        choice : str, default ""
            What was answered. Keyword-only.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view._record(True, choice="C")
        >>> view.total, view.correct, view.streak
        (1, 1, 1)
        """
        self._attempts += 1
        now = time.monotonic()
        seconds, self._clock = now - self._clock, now  # the first answer is timed from the question appearing
        if self.learner and self.question:
            self.learner.record(
                self.exercise,
                question=self.question,
                answer=choice,
                correct=ok,
                attempt_no=self._attempts,
                seconds=seconds,
            )
        if not self.missed:  # only the first attempt counts toward the score
            self.total += 1
            self.correct += ok
            self.streak = self.streak + 1 if ok else 0

    def _pick(
        self,
        part: str,
        *,
        text: str,
        button: QPushButton,
    ) -> None:
        """
        Choose one part of a two-part answer.

        A name and then an octave (or a chord type and an inversion), in either order; the answer is checked once both are set.

        Parameters
        ----------
        part : str
            "name" or "octave".
        text : str
            The text of the button. Keyword-only.
        button : QPushButton
            The button, which is lit while it is the chosen one. Keyword-only.

        Examples
        --------
        >>> from alto.exercises.library import ArpeggioNames
        >>> sounds.enabled = False
        >>> view = ExerciseView(ArpeggioNames(), rng=random.Random(11))
        >>> kind, inversion = view.question.answer.split(view.question.joiner)
        >>> by_text = {button.text(): button for button in view.buttons}
        >>> view._pick("name", text=kind, button=by_text[kind])
        >>> view._pick("octave", text=inversion, button=by_text[inversion])
        >>> view.answered
        True
        >>> view._advance.stop()
        >>> sounds.enabled = True
        """
        if self.answered or self._busy:
            return
        previous = self._pending.get(part)
        if previous and previous[1] is not button:
            previous[1].setChecked(False)
        button.setChecked(True)
        self._pending[part] = (text, button)
        if len(self._pending) == 2:
            self._submit_pair()

    def _submit_pair(self) -> None:
        """
        Check a two-part answer once both parts are chosen.

        A right answer is scored through `submit`; a wrong one fades both buttons red and clears them so it can be tried again.

        Examples
        --------
        >>> from alto.exercises.library import ArpeggioNames
        >>> sounds.enabled = False
        >>> view = ExerciseView(ArpeggioNames(), rng=random.Random(11))
        >>> by_text = {button.text(): button for button in view.buttons}
        >>> wrong_kind = next(c for c in view.question.choices if c != view.question.answer.split(view.question.joiner)[0])
        >>> view._pending = {"name": (wrong_kind, by_text[wrong_kind]), "octave": ("root position", by_text["root position"])}
        >>> view._submit_pair()
        >>> view.missed
        True
        >>> sounds.enabled = True
        """
        q = self.question
        assert q is not None
        (name, name_btn), (octave, octave_btn) = self._pending["name"], self._pending["octave"]
        choice = name + q.joiner + octave
        if q.check(choice):
            self._flash(octave_btn, target="#2e7d32")
            self.submit(choice, button=name_btn)  # scores it, flashes the name button, plays the note, moves on
            return
        self._record(False, choice=choice)
        self.missed = True
        self._busy = True
        for b in (name_btn, octave_btn):
            self._flash(b, target="#c62828")
        self._update_score()
        token = self._pair_token

        def reset() -> None:
            """
            Clear the two buttons after a wrong two-part answer, unless a new question has replaced them.

            Examples
            --------
            >>> reset()  # doctest: +SKIP
            """
            if token != self._pair_token:  # a new question replaced these buttons
                return
            for b in (name_btn, octave_btn):
                b.setStyleSheet("")
                b.setChecked(False)
            self._pending = {}
            self._busy = False

        QTimer.singleShot(700, reset)

    def submit(
        self,
        choice: str,
        *,
        button: QPushButton,
    ) -> None:
        """
        Check an answer chosen with a button.

        A right answer is scored, fades green, plays (unless the exercise is silent) and moves on after a moment; a wrong one
        fades red and its button is switched off, so another can be tried.

        Parameters
        ----------
        choice : str
            The text of the button that was pressed.
        button : QPushButton
            The button. Nothing happens if it is switched off. Keyword-only.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> sounds.enabled = False
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> question = view.question
        >>> wrong = next(b for b in view.buttons if b.text() != question.answer)
        >>> view.submit(wrong.text(), button=wrong)
        >>> view.missed, wrong.isEnabled()
        (True, False)
        >>> right = next(b for b in view.buttons if b.text() == question.answer)
        >>> view.submit(question.answer, button=right)
        >>> view.answered
        True
        >>> view._advance.stop()
        >>> sounds.enabled = True
        """
        if self.answered or not self.question or not button.isEnabled():
            return
        q = self.question
        ok = q.check(choice)
        self._record(ok, choice=choice)
        if ok:
            self.answered = True  # the other buttons stay as they are; only the one pressed animates
            self._flash(button, target="#2e7d32", staff=True)
            notes = q.staff or ([[q.keyboard]] if q.keyboard else [])
            if not self.exercise.has_sound:
                pass  # no tone for this exercise
            elif notes:
                sounds.play_notes(notes)
            else:
                sounds.play_correct(self.streak)
            self._advance.start(1200)
        else:
            self.missed = True
            button.setEnabled(False)
            self._flash(button, target="#c62828")
        self._update_score()

    def _update_score(self) -> None:
        """
        Show the score, the percentage right first time, and the streak.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> view = ExerciseView(NoteNames(), rng=random.Random(1))
        >>> view.total, view.correct = 4, 3
        >>> view._update_score()
        >>> view.score.text()
        '3/4 (75%)   streak 0'
        """
        pct = f"{100 * self.correct / self.total:.0f}%" if self.total else "–"
        self.score.setText(f"{self.correct}/{self.total} ({pct})   streak {self.streak}")
