"""Exercise framework. To add an exercise: subclass Exercise, decorate with @register."""
from __future__ import annotations

import hashlib
import json
import random
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass

from ..theory.pitch import Note


@dataclass
class Question:
    prompt: str
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
        """Is this the note we asked for? The spelling and octave must match exactly, so G♯4 is not A♭4."""
        return note == self.construct

    def check(self, choice: str) -> bool:
        return choice == self.answer or choice in self.accept

    def item_key(self) -> str:
        """A stable identity for this question, so the same one can be recognised when it comes round again.
        It covers what is asked and where it is drawn, but not the note value or the order of the buttons."""
        def spelled(n: Note | None):
            return None if n is None else [n.octave, n.letter, n.accidental]
        data = [self.prompt, self.answer, self.clef, [[spelled(n) for n in col] for col in self.staff], self.key,
                spelled(self.keyboard), spelled(self.construct)]
        return hashlib.sha1(json.dumps(data).encode()).hexdigest()[:20]

    def to_dict(self) -> dict:
        """This question as plain data, so it can be stored and asked again."""
        d = asdict(self)
        d["grid"] = None if self.grid is None else {k: list(v) for k, v in self.grid.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Question:
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
    return None if v is None else Note(**v)


def signature(*parts) -> str:
    """A short description of the exercise settings in force, so a stored question is only asked again under the
    settings it was made for."""
    def plain(o):
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
    name: str = ""
    category: str = ""
    description: str = ""
    par_seconds: float = 5.0  # how long a good first answer takes; much quicker earns credit, much slower counts against
    has_sound: bool = True  # False for an exercise that makes no sound at all, whatever the sound button says

    def settings_signature(self) -> str:
        """Identifies the settings that shape the questions. A stored question is only asked again while this is unchanged."""
        return ""

    def instructions(self) -> str:
        """Help text shown from the exercise's help button (simple HTML). Override to describe the exercise."""
        return self.description

    @abstractmethod
    def generate(self, rng: random.Random) -> Question: ...


REGISTRY: list[type[Exercise]] = []


def register(cls: type[Exercise]) -> type[Exercise]:
    """Add an exercise to REGISTRY, next to the others of its category. The categories come in the order they first
    appear, so the home screen and the exercise list can show each category once, with all its exercises under it."""
    last = max((i for i, other in enumerate(REGISTRY) if other.category == cls.category), default=None)
    if last is None:
        REGISTRY.append(cls)
    else:
        REGISTRY.insert(last + 1, cls)
    return cls


def pick_distractors(correct: str, pool: list[str], n: int, rng: random.Random) -> list[str]:
    others = [p for p in dict.fromkeys(pool) if p != correct]
    rng.shuffle(others)
    choices = others[:n] + [correct]
    rng.shuffle(choices)
    return choices
