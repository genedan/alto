---
title: Exercises
nav_order: 3
permalink: /exercises/
---
Alto has eight exercises. Each one has a **?** button with a short explanation, and five of them have their own
settings (the sliders button). The others use fixed rules, described below.

## Note Identification

A note is drawn on a staff. Press the button with its name.

In the exercise settings you can choose:

- **Clefs:** the grand staff, or any of the seven single-staff clefs, listed in three groups: treble, bass, alto and
  tenor; then soprano, mezzo-soprano and baritone. Each clef is shown with its name beside it. The same list is used by every
  exercise that has a clef setting, apart from the grand staff, which only Note Identification and Note Construction use.
- **Range:** the lowest and highest note that can appear, per clef.
- **Key signatures:** which keys appear. When a key is on, the note's name has to agree with the signature.
- **Note values:** whole notes up to thirty-second notes, and the breve.
- **Note names:** letters (C D E) or solfège (Do Re Mi).
- **Accidentals:** whether notes with their own sharp, flat or natural sign appear.

The settings open in a pane on the right of the exercise. Each row names an option, and clicking it opens a page for
that option. Changes apply to the next question straight away.

## Keyboard Identification

One key on a piano keyboard is highlighted. Press the button with its name.

- **Black keys:** include them. A black key has two names, such as C♯ and D♭, and either one is accepted.
- **Octave number:** also choose the octave from a second row. Octaves count up from C, so middle C is C4.
- **Range:** which part of the keyboard is asked.
- **Key signatures:** show a key signature above the keyboard. The name then has to follow that signature. F♯ and G♭ are no longer interchangeable.

{% include shot.html src="keyboard.png" alt="Keyboard Identification with one highlighted key and the note name buttons" %}

## Note Construction

The reverse of note identification. A note name is shown, and you click the staff where that note belongs.

- The octave counts: middle C is C4. On a grand staff, click the upper staff for notes from middle C up and the lower staff for the notes below.
- With **Accidentals** on, pick ♭, ♮ or ♯ first, or right-click the staff to step through them.
- With **Key signatures** on, a signature is drawn at the start of the staff. It already applies to every note of that letter, so in G major you place F♯ on the F line with no extra sign.
- A wrong click shows the note you placed so you can adjust and try again. Only the exact spelling counts, so G♯ is not A♭.

{% include shot.html src="note-construction.png" alt="Note Construction asking to place a note on a staff" %}

## Interval identification

Two notes are shown. Name the interval from the lower note to the higher one, up to an octave.

An interval has a quality and a number. The number counts the letter names it spans, including both notes. The quality
is **P** (perfect), **M** (major), **m** (minor), **A** (augmented) or **d** (diminished). So C to E is M3, and C to E♭
is m3.

{% include shot.html src="intervals.png" alt="Interval identification showing two notes and the interval buttons" %}

## Key signatures

Two kinds of question, asked at random:

- **Read the signature.** A key signature is drawn on a staff and you press the tonic of the scale it belongs to. The
  kind of scale is written under the staff with a blank for the tonic: "_ Major", "_ minor" or, for a mode, "_ Dorian".
- **Count the sharps or flats.** A key is named, such as "How many sharps or flats are in D major?" or "... in E Dorian?",
  and you press how many it has.

A mode uses the key signature of a major key and starts from another note of it, so D Dorian has the signature of C major
(no sharps or flats), started from D. By default Alto asks major and natural minor keys, on the treble and bass staves.
In the exercise settings you can choose:

- **Questions:** read the signature, count the sharps and flats, or both.
- **Staff:** any of the seven clefs (treble, bass, alto, tenor, soprano, mezzo-soprano and baritone), for the signature that is drawn.
- **Scales:** major (Ionian), Dorian, Phrygian, Lydian, Mixolydian, minor (Aeolian) and Locrian.
- **Key signatures:** which of the fifteen signatures, from seven flats to seven sharps, can appear.

{% include shot.html src="key-signatures.png" alt="Key signatures showing three flats on an alto clef staff, with the caption _ Major under the staff" %}

## Scale spelling

A question such as "In B♭ Dorian, what is scale degree 3?" Press the note's name. Each scale uses every letter name
once, so use a sharp or flat where the pattern needs one. Alto asks about:

Major (Ionian), Dorian, Phrygian, Lydian, Mixolydian, natural minor (Aeolian), Locrian, harmonic minor and melodic minor.

## Chord quality

A chord is drawn in root position on a treble or bass staff. Press its type:

major, minor, diminished, augmented, major 7th, dominant 7th, minor 7th, half-diminished 7th and diminished 7th.

Check the size of the intervals stacked above the lowest note to tell the types apart.

## Arpeggio identification

A chord is drawn one note at a time, rising from its lowest note to the same note an octave higher. Press its type, then
press its inversion. The answer counts once you have chosen both, in either order, and a wrong pair is cleared so you can
try again.

The inversion is which chord tone is lowest:

| Inversion | Lowest note |
|---|---|
| Root position | the root |
| 1st inversion | the third |
| 2nd inversion | the fifth |
| 3rd inversion | the seventh (seventh chords only) |

By default Alto asks major, minor, dominant 7th and diminished 7th arpeggios on the treble and bass staves, in every
inversion. In the exercise settings you can choose:

- **Staff:** any of the seven clefs, from treble to baritone.
- **Arpeggio types:** any of major, minor, diminished and augmented triads, and dominant 7th, major 7th, minor 7th,
  half-diminished 7th and diminished 7th chords. The type buttons below the staff follow your choice.
- **Inversions:** root position and the first three inversions. A triad has no 3rd inversion, so that choice only applies to seventh chords.
- **Key signatures:** draw a key signature from the keys you pick. The arpeggio then only gets a sign where it differs
  from the signature, so a natural sign appears where the chord needs one.

{% include shot.html src="arpeggios.png" alt="Arpeggio identification showing four notes rising on a staff, with a row of type buttons and a row of inversion buttons" %}
