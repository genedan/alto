from __future__ import annotations

import random

from .. import settings
from ..settings import spell
from ..theory.pitch import MAJOR_KEYS, NATURAL_SEMITONES, QUALITY_NAMES, Interval, Note, key_accidental
from ..theory.scales import (
    CHORDS,
    INVERSION_NAMES,
    MODE_WORDS,
    SCALES,
    arpeggio,
    build,
    format_key_signature,
    mode_tonic,
)
from .base import Exercise, Question, pick_distractors, register, signature

CLEF_RANGES = {  # inclusive diatonic range that sits comfortably on the staff
    "treble": (Note(3, 5), Note(5, 5)),  # A3..A5
    "bass": (Note(2, 0), Note(4, 0)),    # C2..C4
}


def _random_note(rng: random.Random, clef: str, accidentals: bool, span: tuple[int, int] | None = None) -> Note:
    """Random note; `span` is an inclusive diatonic range (default: the clef's comfortable range)."""
    lo, hi = span or (CLEF_RANGES[clef][0].diatonic, CLEF_RANGES[clef][1].diatonic)
    d = rng.randint(lo, hi)
    return Note.from_diatonic(d, rng.choice((-1, 0, 1)) if accidentals else 0)


@register
class NoteNames(Exercise):
    name = "Note Identification"
    category = "Notation"
    description = "Identify notes on the grand staff or on any of seven clefs, from treble to baritone."
    par_seconds = 3.0

    def settings_signature(self) -> str:
        return signature(settings.note_names, self.accidentals)

    def instructions(self) -> str:
        return ("<b>Note Identification</b><br>A note is shown on the staff. Press the button with its name.<br><br>"
                "Use the sliders button to choose the clefs, the range of notes, key signatures (the name then has to "
                "match the signature), note values, letter or solfège names, and whether sharps, flats and naturals appear.")

    def __init__(self, accidentals: bool = False):
        self.accidentals = accidentals

    def generate(self, rng):
        cfg = settings.note_names
        clef = rng.choice(cfg.active_clefs())
        key = rng.choice(cfg.active_keys())
        value = rng.choice(cfg.active_values())
        with_accidentals = self.accidentals or cfg.accidentals

        letter_pos = rng.randint(*cfg.range_for(clef))
        in_key = key_accidental(letter_pos % 7, key)
        acc = in_key
        if with_accidentals and rng.random() < 0.5:  # an explicit sign that differs from the key signature
            acc = rng.choice([a for a in (-1, 0, 1) if a != in_key])
        note = Note.from_diatonic(letter_pos, acc)

        name = spell(note, cfg.naming)
        # One button for every name that can be the answer under the current settings.
        if with_accidentals:
            pool = {(l, a) for l in range(7) for a in (-1, 0, 1)}
        else:
            pool = {(l, key_accidental(l, k)) for l in range(7) for k in cfg.active_keys()}
        ordered = sorted(pool)
        choices = [spell(Note(4, l, a), cfg.naming) for l, a in ordered]
        if len(pool) == 7:  # one name per letter: a single row, one column per letter
            grid = {c: (0, l) for c, (l, _) in zip(choices, ordered)}
        else:  # columns are letters; sharps on the top row, then naturals, then flats
            rows = {a: r for r, a in enumerate(sorted({a for _, a in pool}, reverse=True))}
            grid = {c: (rows[a], l) for c, (l, a) in zip(choices, ordered)}

        expl = []
        if key:
            expl.append(f"{MAJOR_KEYS[key]} major has {format_key_signature(key)}.")
        if acc != in_key:
            expl.append("The accidental on the note overrides the key signature.")
        return Question("", choices, name, [[note]], clef, " ".join(expl), key, value, grid)


@register
class IntervalNames(Exercise):
    name = "Interval identification"
    category = "Intervals"
    description = "Name the interval between two notes (up to an octave)."
    par_seconds = 6.0

    def instructions(self) -> str:
        return ("<b>Interval identification</b><br>Two notes are shown. Name the interval from the lower note to the "
                "higher one.<br><br>An interval has a quality followed by a number. The number counts the letter names it "
                "spans, including both notes. The quality is P (perfect), M (major), m (minor), A (augmented) or "
                "d (diminished).")

    QUALITIES = {1: "P A d", 2: "M m A d", 3: "M m A d", 4: "P A d", 5: "P A d", 6: "M m A d", 7: "M m A d", 8: "P"}

    def generate(self, rng):
        clef = rng.choice(("treble", "bass"))
        low = _random_note(rng, clef, True)
        number = rng.randint(2, 8)
        quality = rng.choice(self.QUALITIES[number].split())
        iv = Interval(number, quality)
        high = low.transpose(iv)
        if abs(high.accidental) > 1 or abs(low.accidental) > 1:
            return self.generate(rng)
        pool = [f"{q}{n}" for n, qs in self.QUALITIES.items() if n > 1 for q in qs.split()]
        near = [f"{q}{number}" for q in self.QUALITIES[number].split()]
        choices = pick_distractors(iv.short, near + pool, 5, rng)
        expl = f"{low} to {high}: {QUALITY_NAMES[quality]} {number}, {iv.semitones} semitones."
        return Question("", choices, iv.short, [[low], [high]], clef, expl)


def _scale_name(mode: str) -> str:
    """The mode as it follows a tonic: 'major', 'minor', 'Dorian'."""
    return {"Major (Ionian)": "major", "Natural minor (Aeolian)": "minor"}.get(mode, mode)


@register
class KeySignatures(Exercise):
    name = "Key signatures"
    category = "Scales & keys"
    description = "Read a key signature, or count the sharps and flats of a key."
    par_seconds = 5.0

    def settings_signature(self) -> str:
        return signature(settings.key_signatures)

    def instructions(self) -> str:
        return ("<b>Key signatures</b><br>Two kinds of question. In one a key signature is drawn on a staff: press the "
                "tonic of the scale it belongs to (the question says whether it is a major key, a minor key or a mode such "
                "as Dorian). In the other a key is named: press how many sharps or flats it has.<br><br>"
                "Sharp keys add sharps (G, D, A ...) and flat keys add flats (F, B♭, E♭ ...). A mode uses the signature of a "
                "major key, started from another degree: D Dorian has the signature of C major, started from its second note."
                "<br><br>Use the sliders button to choose the kinds of question, the clefs, the scales and the key signatures.")

    def generate(self, rng):
        cfg = settings.key_signatures
        kind = rng.choice(cfg.active_questions())
        mode = rng.choice(cfg.active_modes())
        count = rng.choice(cfg.active_keys())
        tonic = mode_tonic(count, mode)
        if kind == "count":
            return self._count_question(tonic, mode, count, rng)
        return self._read_question(tonic, mode, count, rng.choice(cfg.active_clefs()), rng)

    @staticmethod
    def _count_question(tonic: Note, mode: str, count: int, rng: random.Random) -> Question:
        """'How many sharps or flats are in D Dorian?': the key is named, the signature is the answer."""
        correct = format_key_signature(count)
        near = [format_key_signature(c) for c in range(count - 2, count + 3) if abs(c) <= 7]
        choices = pick_distractors(correct, near, 3, rng)
        return Question(f"How many sharps or flats are in {tonic.name} {_scale_name(mode)}?", choices, correct)

    @staticmethod
    def _read_question(tonic: Note, mode: str, count: int, clef: str, rng: random.Random) -> Question:
        """A key signature on a staff: press the tonic of the scale of the kind asked, which has that signature."""
        correct = tonic.name
        near = [mode_tonic(c, mode).name for c in range(count - 2, count + 3) if abs(c) <= 7]
        everyone = [mode_tonic(c, mode).name for c in range(-7, 8)]
        choices = pick_distractors(correct, near + everyone, 5, rng)
        word = MODE_WORDS.get(mode, f"{mode} scale")
        notes = [*build(tonic, SCALES[mode]), tonic.transpose(Interval(8, "P"))]  # the scale, up to its octave
        scale = _scale_name(mode)
        blank = f"_ {scale if scale == 'minor' else scale[0].upper() + scale[1:]}"  # "_ Major", "_ minor", "_ Dorian"
        return Question(f"Which {word} has this key signature?", choices, correct, clef=clef, key=count, show_staff=True,
                        caption=blank,
                        explanation=f"{format_key_signature(count)}: {tonic.name} {_scale_name(mode)}: "
                        + " ".join(n.name for n in notes))


@register
class ScaleDegrees(Exercise):
    name = "Scale spelling"
    category = "Scales & keys"
    description = "Spell a note of a scale or mode from its tonic."
    par_seconds = 8.0

    def instructions(self) -> str:
        return ("<b>Scale spelling</b><br>Work out the note at the given degree of the scale or mode and press its name. "
                "Each scale uses every letter name once, so use a sharp or flat where the pattern needs one.")

    def generate(self, rng):
        scale = rng.choice(list(SCALES))
        tonic = rng.choice([Note(4, l, a) for l in range(7) for a in (-1, 0, 1)])
        degree = rng.randint(2, 7)
        notes = build(tonic, SCALES[scale])
        if any(abs(n.accidental) > 1 for n in notes):
            return self.generate(rng)
        target = notes[degree - 1]
        pool = [Note(4, l, a).name for l in range(7) for a in (-1, 0, 1)]
        near = [Note.from_diatonic(target.diatonic, a).name for a in (-1, 0, 1)]
        choices = pick_distractors(target.name, near + pool, 5, rng)
        spelled = " ".join(n.name for n in notes)
        return Question(f"In {tonic.name} {scale}, what is scale degree {degree}?", choices, target.name,
                        explanation=f"{tonic.name} {scale}: {spelled}")


@register
class ChordQualities(Exercise):
    name = "Chord quality"
    category = "Chords"
    description = "Identify triads and seventh chords in root position."
    par_seconds = 6.0

    def instructions(self) -> str:
        return ("<b>Chord quality</b><br>A chord is shown in root position. Press its type. Check the size of the "
                "intervals stacked above the lowest note to tell the types apart.")

    def generate(self, rng):
        clef = rng.choice(("treble", "bass"))
        quality = rng.choice(list(CHORDS))
        root = _random_note(rng, clef, True)
        lo, hi = CLEF_RANGES[clef]
        chord = build(root, CHORDS[quality])
        if any(abs(n.accidental) > 1 for n in chord) or chord[-1].diatonic > hi.diatonic + 3:
            return self.generate(rng)
        choices = pick_distractors(quality, list(CHORDS), 4, rng)
        expl = f"{root.name} {quality}: " + " ".join(n.name for n in chord)
        return Question("", choices, quality, [chord], clef, expl)


# Where the lowest and highest note of an arpeggio may sit on each clef (up to two ledger lines either side of the staff).
ARPEGGIO_WINDOWS = {
    "treble": (Note(3, 6), Note(6, 0)),  # B3..C6
    "bass": (Note(2, 0), Note(4, 2)),    # C2..E4
    "alto": (Note(2, 6), Note(5, 1)),    # B2..D5
    "tenor": (Note(2, 4), Note(4, 6)),   # G2..B4
    "soprano": (Note(3, 3), Note(5, 5)),    # F3..A5
    "mezzo": (Note(3, 1), Note(5, 3)),      # D3..F5
    "baritone": (Note(2, 2), Note(4, 4)),   # E2..G4
}


@register
class ArpeggioNames(Exercise):
    name = "Arpeggio identification"
    category = "Chords"
    description = "Name the type and the inversion of a broken chord."
    par_seconds = 9.0

    def settings_signature(self) -> str:
        return signature(settings.arpeggio)

    def instructions(self) -> str:
        return ("<b>Arpeggio identification</b><br>A chord is played one note at a time, rising from its lowest note to "
                "the same note an octave higher. Press its type, then its inversion.<br><br>"
                "Find the chord's root by looking for the notes a third apart. The inversion is which chord tone is "
                "lowest: the root (root position), the third (1st inversion), the fifth (2nd inversion) or the seventh "
                "(3rd inversion, seventh chords only).<br><br>"
                "Use the sliders button to choose the clefs, the types of arpeggio, the inversions and key signatures.")

    def generate(self, rng):
        cfg = settings.arpeggio
        for _ in range(500):
            chord_type = rng.choice(cfg.active_types())
            inversion = rng.choice(cfg.inversions_for(chord_type))
            clef = rng.choice(cfg.active_clefs())
            key = rng.choice(cfg.active_keys()) if cfg.key_signature else 0
            root = Note(4, rng.randrange(7), rng.choice((-1, 0, 1)))
            if (root.letter, root.accidental) in ((2, 1), (6, 1), (0, -1), (3, -1)):  # E♯ B♯ C♭ F♭ are not worth asking
                continue
            notes = arpeggio(root, CHORDS[chord_type], inversion)
            if any(abs(n.accidental) > 1 for n in notes):  # no double sharps or flats
                continue
            low, high = (n.diatonic for n in ARPEGGIO_WINDOWS[clef])
            fits = [s for s in range(-28, 29, 7) if notes[0].diatonic + s >= low and notes[-1].diatonic + s <= high]
            if not fits:
                continue
            shift = rng.choice(fits) // 7
            notes = [Note(n.octave + shift, n.letter, n.accidental) for n in notes]
            return self._question(chord_type, inversion, root, notes, clef, key, cfg)
        raise RuntimeError("no arpeggio fits the chosen settings")

    @staticmethod
    def _question(chord_type, inversion, root, notes, clef, key, cfg) -> Question:
        joiner = " \u00b7 "
        types = cfg.active_types()
        inversions = sorted({i for t in types for i in cfg.inversions_for(t)})
        answer = f"{chord_type}{joiner}{INVERSION_NAMES[inversion]}"
        grid = {t: divmod(i, 5) for i, t in enumerate(types)} if len(types) > 5 else None  # two rows once there are many
        expl = f"{root.name} {chord_type}, {INVERSION_NAMES[inversion]}: " + " ".join(n.name for n in notes)
        return Question("What type of arpeggio is this, and which inversion?", types, answer, [[n] for n in notes], clef,
                        expl, key=key, value="quarter", grid=grid, octaves=[INVERSION_NAMES[i] for i in inversions],
                        second_label="Inversion", joiner=joiner)


# Black keys: pitch class -> (letter, accidental) for the sharp name and for the flat name.
_BLACK_KEY_NAMES = {1: ((0, 1), (1, -1)), 3: ((1, 1), (2, -1)), 6: ((3, 1), (4, -1)), 8: ((4, 1), (5, -1)), 10: ((5, 1), (6, -1))}
_WHITE_KEY_LETTER = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}


def _key_tonic(count: int) -> Note:
    """The major key with `count` sharps (+) or flats (-), as a Note."""
    name = MAJOR_KEYS[count]
    return Note(4, "CDEFGAB".index(name[0]), 1 if "♯" in name else -1 if "♭" in name else 0)


def _key_spellings(pc: int, count: int | None) -> list[tuple[int, int]]:
    """The (letter, accidental) names that are correct for a key of pitch class `pc` in a key signature.

    Notes of the key keep the spelling the key gives them (the F key is E♯ in C♯ major). Other white keys use
    their natural name. Other black keys are spelled with sharps in a sharp key and flats in a flat key; with
    no signature (or none given) either name is right.
    """
    diatonic = {}
    if count is not None:
        diatonic = {n.pitch_class: (n.letter, n.accidental) for n in build(_key_tonic(count), SCALES["Major (Ionian)"])}
    if pc in diatonic:
        return [diatonic[pc]]
    if pc in _WHITE_KEY_LETTER:
        return [(_WHITE_KEY_LETTER[pc], 0)]
    sharp, flat = _BLACK_KEY_NAMES[pc]
    if count and count > 0:
        return [sharp]
    if count and count < 0:
        return [flat]
    return [sharp, flat]


def _spelled(midi: int, letter: int, accidental: int) -> Note:
    """The Note that sounds as `midi` when written with this letter name (B3 written as C♭ is C♭4)."""
    return Note((midi - accidental - NATURAL_SEMITONES[letter]) // 12 - 1, letter, accidental)


@register
class KeyboardNotes(Exercise):
    name = "Keyboard Identification"
    category = "Notation"
    description = "Name the highlighted key on a piano keyboard."
    par_seconds = 3.0

    def settings_signature(self) -> str:
        return signature(settings.keyboard, settings.note_names.naming)

    def instructions(self) -> str:
        cfg = settings.keyboard
        text = ["<b>Keyboard Identification</b><br>One key on the keyboard is highlighted. Press the button with its name."]
        if cfg.require_octave:
            text.append("Choose its octave too, from the row below. Octaves count up from C, so middle C is the C in "
                        "octave 4.")
        if cfg.key_signature:
            text.append("A key signature is shown above the keyboard. Name the key the way that signature spells it. Only "
                        "that spelling counts, so F♯ and G♭ are not interchangeable. A black key that is not in the key "
                        "is spelled with sharps in a sharp key and with flats in a flat key.")
        else:
            text.append("Black keys have two names, such as C♯ and D♭. Either one is accepted.")
        return "<br><br>".join(text)

    def generate(self, rng):
        cfg = settings.keyboard
        naming = settings.note_names.naming
        lo, hi = min(cfg.low, cfg.high), max(cfg.low, cfg.high)
        candidates = [m for m in range(lo, hi + 1) if cfg.black_keys or m % 12 in _WHITE_KEY_LETTER] or [lo]
        count = rng.choice(cfg.active_keys()) if cfg.key_signature else None
        midi = rng.choice(candidates)

        spelled = [_spelled(midi, letter, acc) for letter, acc in _key_spellings(midi % 12, count)]
        key = spelled[0]  # the key as the signature spells it (also what plays when you answer correctly)
        names = [spell(n, naming) for n in spelled]
        answer, accept = names[0], tuple(names[1:])
        octaves = None
        if cfg.require_octave:
            octaves = [str(o) for o in sorted({_spelled(m, *_key_spellings(m % 12, count)[0]).octave for m in candidates})]
            answer, accept = f"{names[0]}{spelled[0].octave}", tuple(f"{n}{sp.octave}" for n, sp in zip(names[1:], spelled[1:]))

        if len(spelled) > 1:
            explanation = f"{names[0]} and {names[1]} are the same black key."
        elif count is not None:
            in_key = midi % 12 in {n.pitch_class for n in build(_key_tonic(count), SCALES["Major (Ionian)"])}
            explanation = f"In {MAJOR_KEYS[count]} major ({format_key_signature(count)}) this key is called {names[0]}."
            if not in_key and midi % 12 not in _WHITE_KEY_LETTER:
                explanation += f" It is not in the key, so it is spelled with {'sharps' if count > 0 else 'flats'}."
        else:
            explanation = ""

        # One button per name: sharps on the top row, naturals in the middle, flats below, a column per letter.
        # A key signature can need any spelling (E♯, C♭ ...), so it gets the full set.
        grid, choices = {}, []
        for letter in range(7):
            n = spell(Note(4, letter), naming)
            choices.append(n)
            grid[n] = (1, letter)
        if cfg.key_signature:
            extra = [(letter, acc, 0 if acc > 0 else 2) for letter in range(7) for acc in (1, -1)]
        elif cfg.black_keys:
            extra = [(letter, acc, row) for (sharp, flat) in _BLACK_KEY_NAMES.values()
                     for (letter, acc), row in ((sharp, 0), (flat, 2))]
        else:
            extra = []
        for letter, acc, row in extra:
            n = spell(Note(4, letter, acc), naming)
            choices.append(n)
            grid[n] = (row, letter)

        return Question("", choices, answer, keyboard=key, accept=accept, explanation=explanation, grid=grid,
                        keyboard_range=(lo, hi), octaves=octaves, key=count or 0, key_staff=cfg.key_signature)


@register
class NoteConstruction(Exercise):
    name = "Note Construction"
    category = "Notation"
    description = "Place the named note on the staff."
    par_seconds = 6.0

    def settings_signature(self) -> str:
        return signature(settings.construction, settings.note_names.naming)

    def instructions(self) -> str:
        cfg = settings.construction
        text = ["<b>Note Construction</b><br>A note name is shown. Click the staff where that note belongs. The octave "
                "counts: the number says which C-to-B you mean, and middle C is C4. On a grand staff, click the upper "
                "staff for notes from middle C up and the lower staff for the notes below it."]
        if cfg.key_signature:
            text.append("A key signature is drawn at the start of the staff. It already applies to every note of that "
                        "letter, so in G major you place F♯ on the F line with no sign. A note that the key does not "
                        "give you needs its own sign.")
        if cfg.accidentals:
            text.append("To give a note its own sign, choose ♯, ♮ or ♭ first, then click the staff. You can also right "
                        "click the staff to step through them. ♮ cancels a sharp or flat from the key signature. Only the "
                        "exact spelling counts, so G♯ is not A♭.")
        text.append("A wrong click shows the note you placed so you can adjust and try again.")
        return "<br><br>".join(text)

    def generate(self, rng):
        cfg = settings.construction
        clef = rng.choice(cfg.active_clefs())
        lo, hi = settings.DEFAULT_RANGES[clef]
        count = rng.choice(cfg.active_keys()) if cfg.key_signature else 0
        diatonic = rng.randint(lo, hi)
        implied = key_accidental(diatonic % 7, count)  # what the key signature already does to this letter
        accidental = implied
        if cfg.accidentals and rng.random() < (0.4 if cfg.key_signature else 0.5):
            accidental = rng.choice([a for a in (-1, 0, 1) if a != implied])  # a sign that differs from the key
        note = Note.from_diatonic(diatonic, accidental)
        name = f"{spell(note, settings.note_names.naming)}{note.octave}"
        explanation = ""
        if cfg.key_signature and count:
            key_name = f"{MAJOR_KEYS[count]} major ({format_key_signature(count)})"
            word = {1: "sharp", -1: "flat", 0: "natural"}
            if accidental == implied and implied:
                explanation = f"In {key_name} the key signature already makes this a {word[implied]}, so it needs no sign."
            elif accidental != implied:
                explanation = f"In {key_name} this note needs its own {word[accidental]} sign."
        return Question(f"Place {name} on the staff.", [], name, clef=clef, construct=note, accidentals=cfg.accidentals,
                        key=count, explanation=explanation)
