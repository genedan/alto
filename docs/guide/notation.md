---
title: Rendering music notation
parent: guide
order: 5
permalink: /guide/notation/
---
Drawing music notation is a craft with a long history and a surprising amount of geometry. This chapter explains how Alto
puts a clef, a key signature and a note on a staff, from the musical rules to the pixels, and where in the code each step
happens. It assumes you can read music a little, and explains the engraving side from scratch.

## The vocabulary

Printing music is called **engraving**, from the days when plates were cut by hand. Software that does it is a *music
engraver* or *notation program* (Finale, Sibelius, Dorico, MuseScore, LilyPond). The notation most of us read is **Common
Western Music Notation**, abbreviated **CWMN**.

The pieces Alto draws:

- The **staff** (plural *staves*): five horizontal lines and the four spaces between them.
- A **clef** at the start says which pitch each line means. A treble clef curls around the second line from the bottom and says
  "this is G above middle C". A bass clef puts F below middle C on the second line from the top. A C clef says "middle C is
  here" and can sit on any line (alto, tenor, soprano, mezzo-soprano, and the baritone variants).
- The **key signature** is the group of sharps or flats after the clef.
- A **note** has a **notehead** (filled, open or breve), usually a **stem**, and for short notes **flags**. Accidentals (sharp,
  flat, natural) go in front of the head.
- **Ledger lines** are short extra lines for notes above or below the staff.
- The **grand staff** joins a treble and a bass staff with a **brace**.

## The unit of measure: the staff space

Everything in engraving is measured in **staff spaces**: the distance between two adjacent staff lines. A notehead is about one
space tall. A stem is about three and a half spaces long. A bass or alto clef is three to four spaces high, and a treble clef is almost nine, because it rises well above and below the
staff. Measure in spaces, and the
same drawing code works at any size by choosing what one space is in pixels.

In Alto this number is called `gap` (or `GAP` on `StaffWidget`): "the distance between staff lines in pixels". A `StaffWidget`
for the exercise uses 16, and the small key-signature staff uses 8. Every drawing function takes `gap` and multiplies.

## From a note to a position

A staff is a ladder: each line and each space is one **step**, so a note moves up one step when you go from a line to the space
above it. Alto numbers every note with a **diatonic index**, `octave * 7 + letter` (letters C=0 to B=6), so C0 is 0, D0 is 1, and
middle C (C4) is 28. `Note.diatonic` gives it, and it ignores sharps and flats, because an accidental changes the sound but not
the position on the staff. (C♯ and C are on the same line.) Interval size in steps is just a subtraction.

A clef fixes which index sits on the bottom line, `BOTTOM_LINE` in `alto/ui/staff.py`:

| Clef | Bottom line | Index |
|---|---|---|
| treble | E4 | 30 |
| bass | G2 | 18 |
| alto | F3 | 24 |
| tenor | D3 | 22 |
| soprano | C4 | 28 |
| mezzo-soprano | A3 | 26 |
| baritone (F clef) | B2 | 20 |

Given the bottom line's `y` on screen, the height of any note is

```python
steps = note.diatonic - BOTTOM_LINE[clef]  # 0 on the bottom line, 1 in the first space, 2 on the second line ...
y = bottom - steps * gap / 2  # screen y grows downward, and each step is half a gap
```

and that is the heart of it. The reverse, from a click to a note, is `StaffInput.note_at(y)`: `round((bottom - y) / (gap / 2))`
gives the step, and `Note.from_diatonic` gives the note, clamped to five ledger lines.

Ledger lines are needed when `steps` is below 0 or above 8 (the staff covers steps 0 to 8). They are drawn at every even step
outside the staff, as far as the note.

### Which way does the stem go?

The rule every musician learns: notes **on or above the middle line** get stems pointing down; notes below it get stems up.
The middle line is step 4, so `stem_down = steps >= 4`. Stems join the head on the right when up and the left when down.
Chords and beamed notes have more complex rules (the side of the stem with the most distant note wins), which Alto does not
need, because its questions are single notes or simple chords.

### Key signatures

A key signature is a row of sharps or flats in a fixed order (sharps F C G D A E B, flats B E A D G C F). The order is the same
in every clef, but the *positions* are not: engravers choose positions so the accidentals zigzag and stay inside the staff
(each one a fourth up or a fifth down from the last, with a few exceptions). `key_signature_positions(clef, sign=)` searches for
a placement that keeps all seven on or near the staff, and that reproduces the traditional signatures for treble, bass, alto and
tenor and works out the others. `tests/test_clefs.py` checks that no signature needs a ledger line.

## Fonts for music: SMuFL

A text font has letters. A **music font** has noteheads, clefs, accidentals and flags as characters. The modern standard is
**SMuFL**, the *Standard Music Font Layout*, maintained by the W3C Music Notation Community Group. It does three things:

1. It assigns every musical symbol a **name** (such as `noteheadBlack`, `gClef`, `accidentalSharp`, `flag8thUp`) and a **code
   point** in Unicode's Private Use Area (U+E000 to U+F8FF), so any SMuFL font puts the sharp at the same code.
2. It says how big things are: the font is drawn so that **four staff spaces equal one em**. The em is the font's nominal size,
   so a glyph at font size `S` has staff space `S / 4`.
3. It publishes **metadata** in a JSON file next to each font: *engraving defaults* (how thick a staff line, a stem and a
   ledger line should be) and **anchors** (exact points on a glyph, such as where a stem should attach to a notehead).

Bravura (the reference font), Leland (MuseScore's), Petaluma, Finale Maestro, Leipzig and others follow it, so Alto can offer
ten looks with the same code. `alto/assets/fonts/engraving.json` holds, per font, the numbers Alto needs, copied from each
font's metadata: line, stem and ledger thickness and the stem anchors.

### From glyph to pixels

`alto/ui/engraving.py` draws SMuFL fonts, and its method is worth understanding, because it is not "draw text".

1. A glyph's **outline** is read out of the font as a `QPainterPath`: `path.addText(0, 0, font, chr(codepoint))`. The outline is
   taken once at 100 pixels to the em (so one staff space is 25 units) and cached with `@cache`.
2. The code works out where the glyph's **origin** belongs and moves and scales the outline there: `_place` builds a
   `QTransform` that translates to the position and scales by `gap / 25`.
3. The outline is **filled** with the current colour.

Why not simply call `drawText`? Because text drawing positions glyphs by the font's advance widths and snaps to the pixel grid
("hinting"), which makes noteheads wobble by a pixel and defeats the anchors. Filling the outline gives exact positions in
fractions of a pixel, and the same code scales to any size.

A note is built from parts, the way an engraver would:

```python
# alto/ui/engraving.py: draw_note, simplified
left, _, right, _ = _ink(font, name="noteheadBlack")  # the head's ink box, in staff spaces
ox = x - (left + right) / 2 * gap  # centre the drawn head on x
_fill(p, path=_place(_outline(font, name="noteheadBlack"), x=ox, y=y, gap=gap), colour=colour)

ax, ay = _anchor(font, name="noteheadBlack", anchor="stemUpSE")  # where an up-stem attaches
thick = _metrics(font)["stem"] * gap  # stem width from the font
p.drawRect(QRectF(left_of_stem, stem_top, thick, stem_bottom - stem_top))  # the stem is just a rectangle
```

Notice that the **stem is a rectangle the code draws**, not a glyph. SMuFL leaves stems to the program, because their length
varies. The **flag** is a glyph, placed by lining up its stem anchor with the end of the rectangle. `STEM_LENGTH` gives the
lengths: three and a half spaces, longer for notes with more flags. The clef is a glyph placed so that its reference line (the G,
F or C it names) sits on the right staff line: `draw_clef` has a table of `(glyph name, line)`, for example treble is the `gClef`
on line 1 (the second line from the bottom).

Heights in font units go **upward**; on screen `y` goes downward. That sign flip is the source of many bugs when you first
work on this code. Keep both in your head: up in the font is minus in `y`.

### The built-in drawing

One style, "Noto Music", is not SMuFL. `alto/ui/notes.py` builds notes from Google's Noto Music font, which is read from the
system and not bundled. Because that font has only stem-up notes, a stem-down note is made by **rotating the glyph half a turn**
(which puts the stem on the left and keeps the head's tilt) and mirroring the flags. It exists for users who like that look; the SMuFL path in
`engraving.py` is the main one.

## Putting it together: `StaffWidget.paintEvent`

`alto/ui/staff.py` is the widget. Its `paintEvent` does these steps, in order, and each is a few lines you can find:

1. Choose the font from the current notation style (`current_style`, from `notation.py`). Compute the staff lines' bottoms with
   `staff_bottoms()` (one staff, or two for the grand staff with `GRAND_BETWEEN` spaces between).
2. Draw the five lines at `bottom - i * gap` for `i` in 0 to 4, with the font's line thickness.
3. Draw the clef, and the brace and the barline for a grand staff.
4. Draw the key signature (`_draw_key_signature`).
5. For each note: its `y` from the formula above, ledger lines if needed, accidental signs, then the note itself.
6. Draw the caption under the staff if there is one.

The same functions are reused for the small pictures in the settings panes (`alto/ui/pictures.py`), so a clef drawn in a
setting looks the same as in a question.

### A script you can run

This draws a treble clef and a stem-down quarter note on the fourth line (D5). It is the quickest way to try engraving code:

```python
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication
from alto.ui import engraving

app = QApplication([])
gap, bottom = 20, 150
image = QImage(300, 200, QImage.Format.Format_ARGB32)  # kept in a variable: the painter paints on it
image.fill(QColor("white"))
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
for i in range(5):
    p.drawLine(20, bottom - i * gap, 280, bottom - i * gap)
engraving.draw_clef(p, font="bravura", clef="treble", x=30, bottom=bottom, gap=gap, colour=QColor("black"))
engraving.draw_note(
    p, font="bravura", value="quarter", x=140, y=bottom - 6 * gap / 2, gap=gap, colour=QColor("black"), stem_down=True
)
p.end()
image.save("/tmp/notation-example.png")
```

Change `font="bravura"` to `"leland"` or `"petaluma"` and compare. Change `6` to `4` and the note moves to the middle line.

## Adding a notation font

The steps are in [For developers]({{ '/development/' | relative_url }}). In outline: put the `.otf` and its licence in
`alto/assets/fonts/`, add its numbers to `engraving.json` from the font's SMuFL metadata, register the file in `_FILES`, and add
a `NotationStyle`. Fonts without full SMuFL metadata may need the fallback numbers in `_anchor`. The test suite draws every style
and checks that something appears (`tests/test_rendering.py`). Look at the result by eye too: a wrong anchor still draws, just
slightly off.

## Where else notation appears

- **`StaffInput`** (`alto/ui/staff_input.py`) is a staff you click to place a note; `note_at` converts a mouse position to a note.
- **`KeyboardWidget`** (`alto/ui/keyboard.py`) draws a piano keyboard to real proportions and can highlight a key. Its geometry
  has the same flavour: white keys have equal width, and black keys are narrower and shorter and sit between them.
- **`QuestionPreview`**, which the database browser opens, redraws a stored question in the same widgets.

## Words to search for

*Engraving rules.* *Optical sizing* (staff lines thinner at small sizes). *Collision avoidance* and *spacing* (the hard parts
Alto avoids: moving objects apart, and spacing notes by duration). *Beaming.* *Cue notes.* *Proportional spacing.* *SMuFL
ranges.* *MusicXML* and *MNX* (formats for exchanging scores). *Font hinting.* *Bézier curves* (glyph outlines are made of
them, as `QPainterPath` lines and curves). *Ink box* or *bounding box* of a glyph.

## Further reading

- Elaine Gould, *Behind Bars: The Definitive Guide to Music Notation* (Faber Music, 2011). The modern authority on how notation
  should look. The chapters on noteheads, stems, accidentals and key signatures are what the code in this chapter encodes.
- Ted Ross, *The Art of Music Engraving and Processing* (Hansen Books, 1970). The classic engraver's manual, with the plate
  engraver's proportions and tricks.
- Gardner Read, *Music Notation: A Manual of Modern Practice*, 2nd ed. (Allyn and Bacon, 1969). Wide coverage of conventions.
- Standard Music Font Layout (SMuFL) specification, W3C Music Notation Community Group, w3c.github.io/smufl/latest. The glyph
  names, code points, metadata format and the rules about the four-spaces-per-em.
- Donald Byrd, *Music Notation by Computer* (PhD dissertation, Indiana University, 1984). An early and careful treatment of
  the problem of laying out notation by program; still the best account of why it is hard.
- The LilyPond documentation, lilypond.org/documentation: an open-source engraver, with an unusually thorough "Essay on
  automated music engraving" that explains its design decisions.
- Michael Scott Cuthbert and Christopher Ariza, "music21: A Toolkit for Computer-Aided Musicology and Symbolic Music Data",
  *Proceedings of the 11th International Society for Music Information Retrieval Conference* (2010): a model for representing
  notes, pitches and intervals in code.
- The W3C Music Notation Community Group's MusicXML 4.0 specification, w3.org, if you ever import or export scores.
