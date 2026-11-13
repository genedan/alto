---
title: Settings
nav_order: 6
permalink: /settings/
---
There are two kinds of settings. **App settings** apply everywhere. **Exercise settings** belong to one exercise.

## App settings

Open them from the menu (☰) with **Settings…** or <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>S</kbd>. Categories are listed on the left, and
the selected one's settings appear on the right.

{% include shot.html src="settings.png" alt="The settings dialog showing theme and notation style options" %}

### Appearance

The Appearance page has three sections, **Theme**, **Notation style** and **Keyboard style**, which you switch between with the pill-shaped control at the top.

**Theme.** Choose System to follow your operating system's light or dark setting, or Light or Dark to always use one.
Each choice is a card with a small picture of the window in that theme (System shows both halves). It applies
immediately.

**Notation style.** The music font used to draw clefs, notes and accidentals. Each choice shows a preview. Your choice
applies to every staff in the app, including the small pictures in the settings panels. The default is Finale Maestro.

| Style | Character |
|---|---|
| Finale Maestro | The look of Finale. |
| Leland | MuseScore 4's font. Light and modern, modelled on SCORE. |
| Bravura | The reference font of the SMuFL standard, which Dorico uses by default. |
| Noto Music | Google's engraved look. |
| Sebastian | A classic engraved face with generous proportions. |
| Leipzig | The default of Verovio. Crisp and compact. |
| Eugene | Inspired by hand-engraved Parisian scores of the early 1900s. |
| Golden Age | A heavy, old-fashioned plate-engraved look. |
| Petaluma | A handwritten look, as in jazz real books. |
| MuseJazz | A brush-pen hand, like MuseScore's jazz template. |
| Finale Broadway | A bold copyist's hand, as in Broadway scores. |

**Keyboard style.** How the piano keyboard looks in the keyboard exercise and in the range picker. Each choice is a card with a
small picture of the keys. Your choice applies to every keyboard in the app. The default is Classic, the standard Alto look.

| Style | Character |
|---|---|
| Classic | White keys in a dark case. |
| Modern piano | A current upright or grand, with red felt under the fallboard. |
| Antique ivory | Naturals aged to a warm yellow, in a rosewood case. |
| Harpsichord, Italian | Boxwood naturals and dark sharps in a cypress case. |
| Harpsichord, French | Reversed colours: ebony naturals with bone-topped sharps. |
| Baroque pipe organ | Bone and ebony keys in an oak case, under a row of stop knobs. |
| Tonewheel organ | Plastic keys in a walnut case, with the lowest octave reversed. |
| Flat and minimal | No case and no gradients. Reads well at small sizes. |
| Engraving | Ink on paper, like a plate in an old method book. |
| Colour by note | One hue per semitone, so every C has the same colour. |
| Midnight neon | Dark keys with a cyan glow and magenta sharps. |
| High contrast | Pure black and white with heavy outlines and a yellow dot on every C. |

The colours are typical of the materials, not measurements of one instrument.

**Build your own.** Below the cards, each part of the keyboard has a row: **Naturals**, **Sharps**, **Case**, **Felt strip** and
**Sharp caps**. Click a part's swatch to open the colour picker, or click one of the round chips for a colour named after a
material: Acrylic white, Mother-of-pearl, Ivory, Bone, Boxwood, Maple, Cypress, Oak, Walnut, Rosewood, Ebonised pearwood, Ebony,
Black acrylic, Aluminium, Brass, Red felt, Green baize and Blue felt. Hover a chip to see its name. The case, felt and caps can be
left out with the ✕ chip. Changing any part switches to the **Custom** style, and your colours are remembered.

The breve is always drawn in its square form, whichever font you choose. All the fonts are bundled with Alto except Noto Music, which is read from your system.

### Sound

**Instrument.** The sound used for notes and for the correct-answer chime. The instruments are listed in a box on the
left: piano, flute, French horn, viola, marimba and vibraphone. The one in use is in bold and
ticked. Choose any of them to see a summary on the right of what its sound is made from:

- where the recordings come from, who played them, and when and how they were recorded;
- which articulation and dynamic were used, such as blown without vibrato at fortissimo or struck with yarn mallets;
- how many notes are recorded, their range, and whether every semitone is covered (notes in between are shifted from
  a neighbour);
- how much space they take, and the terms they are available under.

The viola can be played two ways, so it has one entry. Its page describes the **Arco** (bowed) and **Pizzicato**
(plucked) recordings together, and has a row of buttons for each, such as **Use this instrument (Arco)**. The list says
which one is in use, such as "Viola (Pizzicato)".

Press **Use this instrument**, or double-click the entry in the list, to switch to it. Press **Hear it** beside it to listen
to a short arpeggio first without choosing it, even while sound is muted. Sound can also be muted with the speaker
button in any exercise.

The flute, French horn and arco viola, which are blown or bowed, end each note as the next one begins, as a player would. Struck and plucked instruments, such as the piano, marimba and pizzicato viola, ring on. An instrument
whose recordings are not installed in your copy of Alto is shown in italics and cannot be chosen, because it would
only play as the synthesized piano.

{% include shot.html src="settings-sound.png" alt="The Sound page of the settings dialog with a list of instruments and a summary of the selected one" %}

## Exercise settings

Note Identification, Keyboard Identification and Note Construction have a sliders button at the top right of the
exercise. It opens a pane on the right. Each row summarises its setting with a small picture, and clicking a row opens
that setting's page. See [Exercises]({{ '/exercises/' | relative_url }}) for what each option does.

Changing a setting starts a new question straight away, and the settings are remembered the next time you open Alto.

## Where settings are stored

Settings are kept by Qt in your user configuration (for example `~/.config/alto/alto.conf` on Linux), separate from your
practice history. See [Your data]({{ '/data/' | relative_url }}).
