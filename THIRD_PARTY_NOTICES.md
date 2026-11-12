# Third-party material

Alto bundles the following. Each item is used under the terms stated by its author. The source files and licence
texts are in the folders named below.

## Music fonts (`alto/assets/fonts/`)

All are under the SIL Open Font License 1.1 (OFL), whose texts are kept beside the fonts. The fonts are used unmodified.
`engraving.json` holds measurements read from each font's published SMuFL metadata; it is not a font.

| Font | Author | Source |
|---|---|---|
| Bravura | Steinberg Media Technologies GmbH | https://github.com/steinbergmedia/bravura |
| Petaluma | Steinberg Media Technologies GmbH | https://github.com/steinbergmedia/petaluma |
| Leland | MuseScore Limited | https://github.com/musescore/MuseScore/tree/main/fonts/leland |
| MuseJazz | Torsten Hämmerle and Abraham Lee | https://github.com/musescore/MuseScore/tree/main/fonts/musejazz |
| Eugene | Mikko Patama | https://github.com/mikkopatama/eugenefont |
| Leipzig | Etienne Darbellay, Jean-François Martin and Laurent Pugin | https://github.com/rism-digital/leipzig |
| Sebastian | Florian Kretlow and Ben Byram-Wigfield | https://github.com/fkretlow/sebastian |
| Golden Age | Don Rice | https://github.com/benwiggy/GoldenAge |
| Finale Maestro, Finale Broadway | MakeMusic, Inc. | https://github.com/musescore/MuseScore/tree/main/fonts |

The font names are the names their authors gave them. Alto is not affiliated with or endorsed by any of them, nor by
Dorico, Finale, MuseScore or Verovio, which are mentioned only to say where a font is used.

## Instrument recordings (`alto/assets/piano/`, `alto/assets/samples/marimba/`, `alto/assets/samples/vibraphone/`)

The piano, marimba and vibraphone recordings come from the Musical Instrument Samples of the University of Iowa
Electronic Music Studios (https://theremin.music.uiowa.edu/MIS.html). The site states that these recordings "have been
freely available on this website and may be downloaded and used for any projects, without restrictions." They were
converted to mono, trimmed and faded for use here. Details are in each folder's `SOURCE.txt`.

## App icons (`alto/assets/icon.svg`, `alto/assets/icon-treble.svg`)

The clef in each icon is an outline from the Noto Music font (Google, SIL Open Font License 1.1), set on a rounded
square: the alto clef in `icon.svg` and the treble clef in `icon-treble.svg`.

## Fonts used from the system, not bundled

- Noto Music (Google, SIL OFL 1.1) draws the "Noto Music" notation style, and DejaVu Sans (Bitstream Vera licence with
  DejaVu changes, free to redistribute) draws a few sharp and flat signs. Alto asks the operating system for them by name.

## Software dependencies

- PySide6 / Qt for Python (LGPL-3.0 or GPL-3.0 or commercial), numpy (BSD-3-Clause). pytest (MIT) is used for tests only.
