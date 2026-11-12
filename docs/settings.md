---
title: Settings
nav_order: 6
permalink: /settings/
---
There are two kinds of settings. **App settings** apply everywhere. **Exercise settings** belong to one exercise.

## App settings

Open them from the menu (☰) with **Settings…** or <kbd>Ctrl</kbd>+<kbd>,</kbd>. Categories are listed on the left, and
the selected one's settings appear on the right.

{% include shot.html src="settings.png" alt="The settings dialog showing theme and notation style options" %}

### Appearance

**Theme.** Choose System to follow your operating system's light or dark setting, or Light or Dark to always use one.
It applies immediately.

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

The breve is always drawn in its square form, whichever font you choose. All the fonts are bundled with Alto except Noto Music, which is read from your system.

### Sound

**Instrument.** The sound used for notes and for the correct-answer chime: piano, flute, clarinet, oboe, trumpet,
violin, cello, marimba or vibraphone. Press ▶ on a card to hear it without choosing it. Sound can also be muted with
the speaker button in any exercise.

{% include shot.html src="settings-sound.png" alt="The Sound page of the settings dialog with the instrument choices" %}

## Exercise settings

Note Identification, Keyboard Identification and Note Construction have a sliders button at the top right of the
exercise. It opens a pane on the right. Each row summarises its setting with a small picture, and clicking a row opens
that setting's page. See [Exercises]({{ '/exercises/' | relative_url }}) for what each option does.

Changing a setting starts a new question straight away, and the settings are remembered the next time you open Alto.

## Where settings are stored

Settings are kept by Qt in your user configuration (for example `~/.config/alto/alto.conf` on Linux), separate from your
practice history. See [Your data]({{ '/data/' | relative_url }}).
