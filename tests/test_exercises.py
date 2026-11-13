"""The exercise library: every exercise makes valid questions, and the registry keeps them in order."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from alto.exercises import REGISTRY
from alto.exercises.base import Exercise, Question

if TYPE_CHECKING:
    from alto.theory.pitch import Note


def keyboard_of(q: Question) -> Note:
    """
    Return the highlighted key of a keyboard question.

    Parameters
    ----------
    q : Question
        A keyboard question.

    Returns
    -------
    Note
        The key to highlight.
    """
    assert q.keyboard is not None
    return q.keyboard


def construct_of(q: Question) -> Note:
    """
    Return the note to place, for a note construction question.

    Parameters
    ----------
    q : Question
        A note construction question.

    Returns
    -------
    Note
        The note to place.
    """
    assert q.construct is not None
    return q.construct


def test_the_exercises_of_a_category_are_listed_together() -> None:
    """
    Check that the exercises of a category are listed together.
    """
    categories = [cls.category for cls in REGISTRY]
    firsts = list(dict.fromkeys(categories))  # the categories in the order they first appear
    assert categories == sorted(categories, key=firsts.index)  # no category comes back after another one has started
    assert len(firsts) > 1


def test_registering_an_exercise_puts_it_beside_the_others_of_its_category() -> None:
    """
    Check that registering an exercise puts it beside the others of its category.
    """
    from alto.exercises.base import register

    class Extra(Exercise):
        """
        An exercise in a category that has others after it.
        """

        name, category = "Extra", "Intervals"  # a category with exercises after it, not the last one

        def generate(self, rng: random.Random) -> Question:
            """
            Make the one fixed question.

            Parameters
            ----------
            rng : random.Random
                The random source (not used: the question is fixed).

            Returns
            -------
            Question
                A question.
            """
            return Question("?", choices=["a"], answer="a")

    before = list(REGISTRY)
    try:
        register(Extra)
        last_of_category = max(i for i, c in enumerate(REGISTRY) if c.category == Extra.category and c is not Extra)
        assert REGISTRY.index(Extra) == last_of_category + 1
        assert [c for c in REGISTRY if c is not Extra] == before  # nothing else moved
        brand_new = type("New", (Extra,), {"category": "A category nobody has used"})
        # noinspection PyTypeChecker
        register(brand_new)
        assert REGISTRY[-1] is brand_new  # a new category goes at the end
    finally:
        REGISTRY[:] = before


def test_every_exercise_generates_valid_questions() -> None:
    """
    Check that every exercise generates valid questions.
    """
    rng = random.Random(1)
    for cls in REGISTRY:
        ex = cls()
        for _ in range(300):
            q = ex.generate(rng)
            if q.construct:  # answered by clicking the staff, so there are no buttons
                assert not q.choices and q.check_placed(q.construct), (cls.name, q)
                continue
            if q.octaves:  # a two-part answer: a choice, then one of the second row
                assert q.answer in [c + q.joiner + o for c in q.choices for o in q.octaves], (cls.name, q)
            else:
                assert q.answer in q.choices, (cls.name, q)
            assert len(set(q.choices)) == len(q.choices), (cls.name, q)


def test_note_names_respects_clef_settings() -> None:
    """
    Test note names respects clef settings.
    """
    from alto import settings
    from alto.exercises.library import NoteNames

    cfg = settings.note_names
    old = set(cfg.clefs)
    try:
        rng = random.Random(2)
        cfg.clefs = {"alto", "tenor"}
        assert {NoteNames().generate(rng).clef for _ in range(100)} == {"alto", "tenor"}
        cfg.clefs = {"grand"}
        qs = [NoteNames().generate(rng) for _ in range(100)]
        assert {q.clef for q in qs} == {"grand"}
        assert all(q.answer in q.choices for q in qs)
        cfg.clefs = {"grand", "baritone"}  # the grand staff is picked at random like any other clef
        assert {NoteNames().generate(rng).clef for _ in range(100)} == {"grand", "baritone"}
        cfg.clefs = set()
        assert NoteNames().generate(rng).clef == "treble"  # empty selection falls back
    finally:
        cfg.clefs = old


def test_note_names_respects_range_settings() -> None:
    """
    Test note names respects range settings.
    """
    from alto import settings
    from alto.exercises.library import NoteNames
    from alto.theory.pitch import Note

    cfg = settings.note_names
    old = (set(cfg.clefs), dict(cfg.ranges))
    try:
        cfg.clefs = {"treble"}
        cfg.ranges = {"treble": (Note(4, letter=0).diatonic, Note(4, letter=2).diatonic)}  # C4..E4
        rng = random.Random(3)
        got = {NoteNames().generate(rng).staff[0][0].name for _ in range(200)}
        assert got == {"C", "D", "E"}
    finally:
        cfg.clefs, cfg.ranges = old


def test_note_names_key_signature_values_and_naming() -> None:
    """
    Check that note names key signature values and naming.
    """
    from alto import settings
    from alto.exercises.library import NoteNames
    from alto.theory.pitch import key_accidental

    cfg = settings.note_names
    old = (
        set(cfg.clefs),
        dict(cfg.ranges),
        set(cfg.key_signatures),
        set(cfg.note_values),
        cfg.naming,
        cfg.accidentals,
    )
    try:
        cfg.clefs, cfg.ranges = {"treble"}, {}
        cfg.key_signatures, cfg.note_values = {2, -3}, {"half", "eighth"}
        rng = random.Random(4)
        for naming, accidentals in (("letters", False), ("solfege", True)):
            cfg.naming, cfg.accidentals = naming, accidentals
            qs = [NoteNames().generate(rng) for _ in range(300)]
            for q in qs:
                note = q.staff[0][0]
                assert q.key in (2, -3) and q.value in ("half", "eighth")
                assert q.answer in q.choices and len(set(q.choices)) == len(q.choices)
                assert q.answer == settings.spell(note, naming=naming)
                if not accidentals:  # with no explicit signs the key signature decides the accidental
                    assert note.accidental == key_accidental(note.letter, count=q.key)
            if naming == "solfege":
                assert all(
                    c[:2]
                    in (
                        "Do",
                        "Re",
                        "Mi",
                        "Fa",
                        "So",
                        "La",
                        "Si",
                    )
                    for q in qs
                    for c in q.choices
                )
        assert {q.key for q in qs} == {2, -3}
    finally:
        (
            cfg.clefs,
            cfg.ranges,
            cfg.key_signatures,
            cfg.note_values,
            cfg.naming,
            cfg.accidentals,
        ) = old


def test_keyboard_exercise() -> None:
    """
    Test keyboard exercise.
    """
    from alto import settings
    from alto.exercises.library import KeyboardNotes

    cfg = settings.keyboard
    old = cfg.black_keys
    try:
        rng = random.Random(5)
        lo, hi = cfg.low, cfg.high
        for black in (True, False):
            cfg.black_keys = black
            qs = [KeyboardNotes().generate(rng) for _ in range(300)]
            assert all(lo <= keyboard_of(q).midi <= hi and q.answer in q.choices for q in qs)
            assert len(qs[0].choices) == (17 if black else 7)
            blacks = [q for q in qs if keyboard_of(q).accidental]
            assert bool(blacks) == black
            for q in blacks:  # a black key accepts either name, and nothing else
                assert q.check(q.answer) and all(q.check(a) for a in q.accept) and len(q.accept) == 1
                wrong = [c for c in q.choices if c != q.answer and c not in q.accept]
                assert not any(q.check(c) for c in wrong)
    finally:
        cfg.black_keys = old


def test_keyboard_range_and_octave_answers() -> None:
    """
    Test keyboard range and octave answers.
    """
    from alto import settings
    from alto.exercises.library import KeyboardNotes

    cfg = settings.keyboard
    old = (
        cfg.black_keys,
        cfg.require_octave,
        cfg.low,
        cfg.high,
    )
    try:
        rng = random.Random(6)
        cfg.black_keys, cfg.require_octave, cfg.low, cfg.high = True, False, 48, 72
        assert {q.keyboard_range for q in (KeyboardNotes().generate(rng) for _ in range(20))} == {(48, 72)}
        qs = [KeyboardNotes().generate(rng) for _ in range(500)]
        assert min(keyboard_of(q).midi for q in qs) == 48 and max(keyboard_of(q).midi for q in qs) == 72  # default C3..C5
        assert all(q.octaves is None for q in qs)

        cfg.require_octave, cfg.low, cfg.high = True, 40, 66  # E2..F#4
        qs = [KeyboardNotes().generate(rng) for _ in range(500)]
        for q in qs:
            assert q.octaves == ["2", "3", "4"]
            octave = keyboard_of(q).octave
            assert q.answer.endswith(str(octave)) and q.answer[:-1] in q.choices
            assert q.check(q.answer) and not q.check(q.answer[:-1])  # the name alone is not enough
            wrong_octave = str(octave + 1 if octave < 4 else octave - 1)
            assert not q.check(q.answer[:-1] + wrong_octave)
            for alt in q.accept:  # a black key's other name counts, in the same octave
                assert q.check(alt) and alt.endswith(str(octave))

        cfg.low, cfg.high = settings.KEYBOARD_FULL  # the whole piano
        qs = [KeyboardNotes().generate(rng) for _ in range(2000)]
        assert min(keyboard_of(q).midi for q in qs) < 30 and max(keyboard_of(q).midi for q in qs) > 100
        assert qs[0].octaves == [str(o) for o in range(9)]
    finally:
        cfg.black_keys, cfg.require_octave, cfg.low, cfg.high = old


def test_keyboard_key_signature_requires_the_right_spelling() -> None:
    """
    Check that keyboard key signature requires the right spelling.
    """
    from alto import settings
    from alto.exercises.library import KeyboardNotes

    cfg = settings.keyboard
    old = (
        cfg.key_signature,
        cfg.keys,
        cfg.black_keys,
        cfg.require_octave,
        cfg.low,
        cfg.high,
    )
    try:
        cfg.key_signature, cfg.black_keys, cfg.require_octave, cfg.low, cfg.high = True, True, False, 60, 71
        rng = random.Random(8)

        cfg.keys = {2}  # D major: F#, C#; black keys outside the key are sharps too
        qs = [KeyboardNotes().generate(rng) for _ in range(400)]
        assert all(q.key == 2 and q.key_staff and len(q.choices) == 21 for q in qs)
        by_midi = {keyboard_of(q).midi: q for q in qs}
        assert by_midi[66].answer == "F♯" and not by_midi[66].check("G♭")  # no enharmonic
        assert by_midi[70].answer == "A♯" and not by_midi[70].check("B♭")
        assert all(q.accept == () for q in qs)

        cfg.keys = {-3}  # E-flat major: flats
        qs = {keyboard_of(q).midi: q for q in (KeyboardNotes().generate(rng) for _ in range(400))}
        assert qs[63].answer == "E♭" and not qs[63].check("D♯") and qs[66].answer == "G♭" and not qs[66].check("F♯")

        cfg.keys = {7}  # C-sharp major: the white key F is E-sharp, and C is B-sharp
        qs = {keyboard_of(q).midi: q for q in (KeyboardNotes().generate(rng) for _ in range(400))}
        assert qs[65].answer == "E♯" and not qs[65].check("F") and qs[60].answer == "B♯" and not qs[60].check("C")

        cfg.keys = {-7}  # C-flat major: the white key B is C-flat, which is written in the next octave up
        cfg.require_octave = True
        qs = {keyboard_of(q).midi: q for q in (KeyboardNotes().generate(rng) for _ in range(600))}
        assert qs[71].answer == "C♭5" and not qs[71].check("B4") and qs[65].answer == "F4"  # F is not altered
        assert qs[64].answer == "F♭4"

        cfg.keys, cfg.require_octave = {0}, False  # no signature: either name of a black key is accepted
        qs = [q for q in (KeyboardNotes().generate(rng) for _ in range(200)) if keyboard_of(q).accidental]
        assert qs and all(len(q.accept) == 1 and q.check(q.accept[0]) for q in qs)
    finally:
        cfg.key_signature, cfg.keys, cfg.black_keys, cfg.require_octave, cfg.low, cfg.high = old


def test_note_construction() -> None:
    """
    Test note construction.
    """
    from alto import settings
    from alto.exercises.library import NoteConstruction
    from alto.theory.pitch import Note

    cfg = settings.construction
    old = (set(cfg.clefs), cfg.accidentals)
    try:
        rng = random.Random(9)
        cfg.clefs, cfg.accidentals = {"treble", "alto"}, False
        qs = [NoteConstruction().generate(rng) for _ in range(300)]
        assert {q.clef for q in qs} == {"treble", "alto"} and not any(q.accidentals for q in qs)
        for q in qs:
            lo, hi = settings.DEFAULT_RANGES[q.clef]
            assert lo <= construct_of(q).diatonic <= hi and construct_of(q).accidental == 0
            assert q.answer in q.prompt  # the question shows the note's name and octave
        q = qs[0]
        assert q.check_placed(construct_of(q))
        assert not q.check_placed(Note(construct_of(q).octave, letter=construct_of(q).letter, accidental=1))  # wrong accidental
        assert not q.check_placed(Note.from_diatonic(construct_of(q).diatonic + 1))  # next line or space

        cfg.accidentals = True
        qs = [NoteConstruction().generate(rng) for _ in range(300)]
        assert any(construct_of(q).accidental for q in qs) and any(construct_of(q).accidental == 0 for q in qs)
        assert all(q.accidentals for q in qs)
        sharp = next(q for q in qs if construct_of(q).accidental == 1)  # G sharp is not A flat: same sound, wrong spelling
        enharmonic = Note.from_diatonic(construct_of(sharp).diatonic + 1, accidental=-1)
        assert enharmonic.midi == construct_of(sharp).midi and not sharp.check_placed(enharmonic)
    finally:
        cfg.clefs, cfg.accidentals = old


def test_note_construction_grand_staff() -> None:
    """
    Test note construction grand staff.
    """
    from alto import settings
    from alto.exercises.library import NoteConstruction

    cfg = settings.construction
    old = (set(cfg.clefs), cfg.accidentals)
    try:
        rng = random.Random(11)
        cfg.clefs, cfg.accidentals = {"grand"}, False
        qs = [NoteConstruction().generate(rng) for _ in range(300)]
        lo, hi = settings.DEFAULT_RANGES["grand"]
        assert {q.clef for q in qs} == {"grand"}
        assert all(lo <= construct_of(q).diatonic <= hi for q in qs)
        steps = [construct_of(q).diatonic for q in qs]
        assert min(steps) < 28 < max(steps)  # both below and above middle C
        cfg.clefs = {"treble", "grand", "tenor"}
        assert {NoteConstruction().generate(rng).clef for _ in range(200)} == {"treble", "grand", "tenor"}
        assert settings.ConstructionSettings(clefs={"grand", "bass"}).active_clefs() == ["bass", "grand"]
    finally:
        cfg.clefs, cfg.accidentals = old


def test_note_construction_key_signature() -> None:
    """
    Test note construction key signature.
    """
    from alto import settings
    from alto.exercises.library import NoteConstruction
    from alto.theory.pitch import key_accidental

    cfg = settings.construction
    old = (
        set(cfg.clefs),
        cfg.accidentals,
        cfg.key_signature,
        set(cfg.keys),
    )
    try:
        rng = random.Random(12)
        cfg.clefs, cfg.key_signature, cfg.keys, cfg.accidentals = {"treble"}, True, {2, -3}, False
        qs = [NoteConstruction().generate(rng) for _ in range(400)]
        assert {q.key for q in qs} == {2, -3}
        # no extra signs: the note is exactly what the key signature makes of its letter
        assert all(construct_of(q).accidental == key_accidental(construct_of(q).letter, count=q.key) for q in qs)
        f_in_d = next(q for q in qs if q.key == 2 and construct_of(q).letter == 3)
        assert construct_of(f_in_d).accidental == 1 and "F♯" in f_in_d.answer and "no sign" in f_in_d.explanation

        cfg.accidentals = True  # some notes now need their own sign (a natural cancels the key)
        qs = [NoteConstruction().generate(rng) for _ in range(600)]
        differing = [q for q in qs if construct_of(q).accidental != key_accidental(construct_of(q).letter, count=q.key)]
        assert differing and len(differing) < len(qs)
        assert any(construct_of(q).accidental == 0 for q in differing)  # an explicit natural
        assert all("needs its own" in q.explanation for q in differing)

        cfg.key_signature = False  # off: no signature, and the old behaviour
        assert {NoteConstruction().generate(rng).key for _ in range(100)} == {0}
    finally:
        cfg.clefs, cfg.accidentals, cfg.key_signature, cfg.keys = old
