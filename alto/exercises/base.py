"""
Exercise framework. To add an exercise: subclass Exercise, decorate with @register.

An `Exercise` makes `Question` objects. The `Question` says what to show (a staff, a keyboard or only text), which
buttons to offer and which answer is right. The exercise screen and the scheduler work with those two classes only, so
a new exercise needs no new interface code.

Examples
--------
>>> question = Question("Name this note.", choices=["C", "D", "E"], answer="D")
>>> question.check("D"), question.check("E")
(True, False)
"""

from __future__ import annotations

import hashlib
import json
import random
from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import (
    KW_ONLY,
    asdict,
    dataclass,
    field,
    is_dataclass,
)
from typing import Any

from alto.theory.pitch import Note


@dataclass
class Question:
    """
    One question, with what to show for it and which answer is right.

    Attributes
    ----------
    prompt : str
        The text shown above the question; may be empty.
    choices : list of str
        The answer buttons, in the order they should be offered. Keyword-only.
    answer : str
        The right answer, one of `choices` (or the note name for a "place this note" question). Keyword-only.
    staff : list of list of Note
        What to draw on the staff: each inner list is one chord or note. Keyword-only.
    clef : str, default "treble"
        The clef to draw on. Keyword-only.
    explanation : str, default ""
        Text shown after the answer to say why it is right. Keyword-only.
    key : int, default 0
        The key signature to draw: that many sharps if positive, flats if negative. Keyword-only.
    value : str, default "whole"
        The note value to draw (single notes only). Keyword-only.
    grid : dict of str to tuple of (int, int) or None
        Where to put each answer button, as (row, column). Without it the choices form one row. Keyword-only.
    keyboard : Note or None
        A piano key to highlight, instead of drawing a staff. Keyword-only.
    key_staff : bool, default False
        Draw `key` as a small key-signature staff above the keyboard. Keyword-only.
    keyboard_range : tuple of (int, int) or None
        The keys (MIDI numbers, inclusive) the keyboard picture should show. Keyword-only.
    octaves : list of str or None
        When set, the answer is a choice button plus one of these second-row buttons. Keyword-only.
    second_label : str, default "Octave"
        What the second row of buttons is called. Keyword-only.
    joiner : str, default ""
        Put between the two parts to make the answer ("" for a note and its octave: C + 4 gives C4). Keyword-only.
    construct : Note or None
        The note to place on the staff: the answer is a position, not a button. Keyword-only.
    accidentals : bool, default False
        Show the sharp, natural and flat buttons for a construct question. Keyword-only.
    accept : tuple of str
        Other answers that count as right, such as the enharmonic name of a black key. Keyword-only.
    show_staff : bool, default False
        Draw the staff even with no notes on it, to show only its clef and key signature. Keyword-only.
    caption : str, default ""
        Text written on the staff itself, under the music, in place of the prompt above it. Keyword-only.

    Examples
    --------
    >>> q = Question("Which note is this?", choices=["C", "D", "E"], answer="D", staff=[[Note.parse("D4")]])
    >>> q.check("D")
    True
    >>> Question.from_dict(q.to_dict()) == q  # a question can be stored and asked again
    True
    """

    prompt: str
    _: KW_ONLY
    choices: list[str]
    answer: str
    # What to draw on the staff: each inner list is one simultaneous chord/note.
    staff: list[list[Note]] = field(default_factory=list)
    clef: str = "treble"
    explanation: str = ""
    key: int = 0  # key signature to draw: sharps (+) / flats (-)
    value: str = "whole"  # note value to draw (single notes only)
    # Optional button placement: choice -> (row, column). Without it the choices form one row.
    grid: dict[str, tuple[int, int]] | None = None
    keyboard: Note | None = None  # a piano key to highlight, instead of drawing a staff
    key_staff: bool = False  # draw `key` as a small key-signature staff above the keyboard
    keyboard_range: tuple[int, int] | None = None  # the keys (MIDI, inclusive) the keyboard picture should show
    octaves: list[str] | None = None  # when set, the answer is a choice button plus one of these second-row buttons
    second_label: str = "Octave"  # what the second row of buttons is called
    joiner: str = ""  # put between the two parts to make the answer ("" for a note and its octave: C + 4 -> C4)
    construct: Note | None = None  # the note to place on the staff: the answer is a position, not a button
    accidentals: bool = False  # show the sharp / flat / natural buttons for a construct question
    accept: tuple[str, ...] = ()  # other answers that count as correct (e.g. the enharmonic name of a black key)
    show_staff: bool = False  # draw the staff even with no notes on it, to show only its clef and key signature
    caption: str = ""  # text written on the staff itself, under the music, in place of the prompt above it

    def check_placed(self, note: Note) -> bool:
        """
        Report whether a note placed on the staff is the one asked for.

        The spelling and octave must match exactly, so G♯4 is not A♭4.

        Parameters
        ----------
        note : Note
            The note the learner placed.

        Returns
        -------
        bool
            True if it equals the note in `construct`.

        Examples
        --------
        >>> q = Question("Place C4", choices=[], answer="C4", construct=Note.parse("C4"))
        >>> q.check_placed(Note.parse("C4"))
        True
        >>> q.check_placed(Note.parse("B#3"))  # sounds the same, but is spelled differently
        False
        """
        return note == self.construct

    def check(self, choice: str) -> bool:
        """
        Report whether a chosen answer is right.

        Parameters
        ----------
        choice : str
            The text of the button that was pressed.

        Returns
        -------
        bool
            True if it is the answer or one of the other accepted answers.

        Examples
        --------
        >>> q = Question("", choices=["F♯", "G♭"], answer="F♯", accept=("G♭",))
        >>> q.check("F♯"), q.check("G♭"), q.check("A")
        (True, True, False)
        """
        return choice == self.answer or choice in self.accept

    def item_key(self) -> str:
        """
        Return a stable identity for the question, so the same one can be recognised when it comes round again.

        It covers what is asked and where it is drawn, but not the note value or the order of the buttons.

        Returns
        -------
        str
            A 20-character hexadecimal string.

        Examples
        --------
        >>> a = Question("Name it.", choices=["C", "D"], answer="C")
        >>> b = Question("Name it.", choices=["D", "C"], answer="C")  # the same question, buttons in another order
        >>> a.item_key() == b.item_key()
        True
        >>> len(a.item_key())
        20
        """

        def spelled(n: Note | None) -> list[int] | None:
            """
            Describe a note in a form that can be written as JSON.

            Parameters
            ----------
            n : Note or None
                The note, or None for no note.

            Returns
            -------
            list of int or None
                `[octave, letter, accidental]`, or None if there was no note.

            Examples
            --------
            >>> on_keyboard = Question("Press it.", choices=["C"], answer="C", keyboard=Note.parse("C4"))
            >>> on_keyboard.item_key() == Question("Press it.", choices=["C"], answer="C").item_key()  # the key is part of it
            False
            """
            return None if n is None else [n.octave, n.letter, n.accidental]

        data = [
            self.prompt,
            self.answer,
            self.clef,
            [[spelled(n) for n in col] for col in self.staff],
            self.key,
            spelled(self.keyboard),
            spelled(self.construct),
        ]
        return hashlib.sha1(json.dumps(data).encode()).hexdigest()[:20]

    def to_dict(self) -> dict:
        """
        Return the question as plain data, so it can be stored and asked again.

        Returns
        -------
        dict
            The fields of the question, with notes as dictionaries and tuples as lists.

        Examples
        --------
        >>> data = Question("Name it.", choices=["C"], answer="C", staff=[[Note.parse("C4")]]).to_dict()
        >>> data["answer"], data["staff"]
        ('C', [[{'octave': 4, 'letter': 0, 'accidental': 0}]])
        """
        d = asdict(self)
        d["grid"] = None if self.grid is None else {k: list(v) for k, v in self.grid.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Question:
        """
        Rebuild a question from the data that `to_dict` made.

        Parameters
        ----------
        d : dict
            The stored data. Questions saved by older versions, which may carry a `play` field, are accepted.

        Returns
        -------
        Question
            The question.

        Examples
        --------
        >>> q = Question("Name it.", choices=["C", "D"], answer="C", key=2, accept=("D",))
        >>> Question.from_dict(q.to_dict()) == q
        True
        """
        d = dict(d)
        d["staff"] = [[Note(**n) for n in col] for col in d.get("staff", [])]
        d.pop("play", None)  # questions stored by an older version carried the notes of a scale to play
        d["keyboard"], d["construct"] = note_from(d.get("keyboard")), note_from(d.get("construct"))
        if d.get("grid") is not None:
            d["grid"] = {k: tuple(v) for k, v in d["grid"].items()}
        if d.get("keyboard_range") is not None:
            d["keyboard_range"] = tuple(d["keyboard_range"])
        d["accept"] = tuple(d.get("accept", ()))
        return cls(**d)


def note_from(v: dict | None) -> Note | None:
    """
    Rebuild a note from stored data.

    Parameters
    ----------
    v : dict or None
        A note as the dictionary `to_dict` stores, or None.

    Returns
    -------
    Note or None
        The note, or None if `v` was None.

    Examples
    --------
    >>> note_from({"octave": 4, "letter": 0, "accidental": 0})
    Note(octave=4, letter=0, accidental=0)
    >>> note_from(None) is None
    True
    """
    return None if v is None else Note(**v)


def signature(*parts: object) -> str:
    """
    Describe the exercise settings in force, so a stored question is only asked again under the settings it was made for.

    Parameters
    ----------
    *parts : object
        The settings to describe: dataclasses, dictionaries, lists, sets and plain values, nested as needed.

    Returns
    -------
    str
        A JSON string that is the same for equal settings, however their sets and dictionaries happen to be ordered.

    Examples
    --------
    >>> signature({"clefs": {"bass", "treble"}}, 3)
    '[{"clefs": ["bass", "treble"]}, 3]'
    >>> signature({"clefs": {"treble", "bass"}}, 3) == signature({"clefs": {"bass", "treble"}}, 3)
    True
    """

    def plain(o: Any) -> Any:  # noqa: ANN401  (settings are nested dicts, lists, sets and dataclasses of any content)
        """
        Turn settings into plain, ordered data that JSON can write.

        Parameters
        ----------
        o : Any
            A dataclass, dictionary, set, list, tuple or plain value.

        Returns
        -------
        Any
            Dataclasses become dictionaries, dictionary keys become strings, and sets become sorted lists.

        Examples
        --------
        >>> signature({3, 1, 2})  # a set is written as a sorted list
        '[[1, 2, 3]]'
        """
        if is_dataclass(o) and not isinstance(o, type):
            return plain(asdict(o))
        if isinstance(o, dict):
            return {str(k): plain(v) for k, v in o.items()}
        if isinstance(o, (set, frozenset)):
            return sorted(plain(x) for x in o)
        if isinstance(o, (list, tuple)):
            return [plain(x) for x in o]
        return o

    return json.dumps(plain(parts), sort_keys=True)


class Exercise(ABC):
    """
    What every exercise provides: its name, how it makes questions and how long a good answer takes.

    Attributes
    ----------
    name : str
        The title shown on the home screen and in the exercise list.
    category : str
        The heading it is listed under.
    description : str
        One line saying what the exercise is for.
    par_seconds : float, default 5.0
        How long a good first answer takes; much quicker earns credit and much slower counts against the question.
    has_sound : bool, default True
        False for an exercise that makes no sound at all, whatever the sound button says.

    Examples
    --------
    >>> class Demo(Exercise):
    ...     name = "Demo"
    ...     def generate(self, rng):
    ...         return Question("Pick A.", choices=["A", "B"], answer="A")
    >>> Demo().generate(random.Random(0)).answer
    'A'
    """

    name: str = ""
    category: str = ""
    description: str = ""
    par_seconds: float = 5.0  # how long a good first answer takes; much quicker earns credit, much slower counts against
    has_sound: bool = True  # False for an exercise that makes no sound at all, whatever the sound button says

    def settings_signature(self) -> str:
        """
        Return what identifies the settings that shape the questions.

        A stored question is only asked again while this is unchanged. Exercises with settings override it.

        Returns
        -------
        str
            An identifier; empty for an exercise with no settings.

        Examples
        --------
        >>> class Demo(Exercise):
        ...     def generate(self, rng):
        ...         return Question("?", choices=["A"], answer="A")
        >>> Demo().settings_signature()
        ''
        """
        return ""

    def instructions(self) -> str:
        """
        Return the help text shown from the exercise's help button.

        Exercises override it to describe themselves.

        Returns
        -------
        str
            Simple HTML; by default the one-line description.

        Examples
        --------
        >>> class Demo(Exercise):
        ...     description = "Spot the note."
        ...     def generate(self, rng):
        ...         return Question("?", choices=["A"], answer="A")
        >>> Demo().instructions()
        'Spot the note.'
        """
        return self.description

    @abstractmethod
    def generate(self, rng: random.Random) -> Question:
        """
        Make one new question.

        Parameters
        ----------
        rng : random.Random
            The random number generator to use, so tests can ask for a repeatable question.

        Returns
        -------
        Question
            The question.

        Examples
        --------
        >>> from alto.exercises.library import NoteNames
        >>> q = NoteNames().generate(random.Random(1))
        >>> q.answer in q.choices
        True
        """
        ...


REGISTRY: list[type[Exercise]] = []


def register(cls: type[Exercise]) -> type[Exercise]:
    """
    Add an exercise to `REGISTRY`, next to the others of its category.

    The categories come in the order they first appear, so the home screen and the exercise list can show each category
    once, with all its exercises under it. Used as a class decorator.

    Parameters
    ----------
    cls : type of Exercise
        The exercise class.

    Returns
    -------
    type of Exercise
        The same class, so the decorator can be applied to a class definition.

    Examples
    --------
    >>> @register
    ... class Demo(Exercise):
    ...     name = "Demo"
    ...     category = "A category no other exercise has"
    ...     def generate(self, rng):
    ...         return Question("?", choices=["A"], answer="A")
    >>> REGISTRY[-1] is Demo
    True
    >>> REGISTRY.remove(Demo)
    """
    last = max((i for i, other in enumerate(REGISTRY) if other.category == cls.category), default=None)
    if last is None:
        REGISTRY.append(cls)
    else:
        REGISTRY.insert(last + 1, cls)
    return cls


def pick_distractors(
    correct: str,
    *,
    pool: list[str],
    n: int,
    rng: random.Random,
) -> list[str]:
    """
    Choose wrong answers to offer alongside the right one, and shuffle them all.

    Parameters
    ----------
    correct : str
        The right answer. It is always in the result.
    pool : list of str
        Where the wrong answers come from; repeats and the right answer are ignored. Keyword-only.
    n : int
        How many wrong answers to include (fewer if the pool has fewer). Keyword-only.
    rng : random.Random
        The random number generator used to choose and shuffle. Keyword-only.

    Returns
    -------
    list of str
        The right answer and up to `n` others, in a random order.

    Examples
    --------
    >>> choices_ = pick_distractors("C", pool=["C", "D", "E", "F"], n=2, rng=random.Random(0))
    >>> len(choices_), "C" in choices_
    (3, True)
    """
    others = [p for p in dict.fromkeys(pool) if p != correct]
    rng.shuffle(others)
    choices = others[:n] + [correct]
    rng.shuffle(choices)
    return choices
