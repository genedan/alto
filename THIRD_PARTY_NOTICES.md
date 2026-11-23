# Third-party material

Alto bundles the following. Each item is used under the terms stated by its author. The source files and license
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

## Notation Identification excerpts

Alto includes eight piano passages from free CC0 transcriptions in the [OpenScore Lieder catalogue](https://fourscoreandmore.org/openscore/lieder/).
OpenScore distributes the transcriptions under its [CC0 1.0 public-domain dedication](https://github.com/OpenScore/Lieder/blob/main/LICENSE.txt).
The historical editions used for these transcriptions are listed below.

| Work | Source edition | Piano measures |
| --- | --- | --- |
| Franz Schubert, *Erlkönig*, D. 328, fourth version | Eusebius Mandyczewski, ed., Breitkopf & Härtel, 1895. [IMSLP 15041](https://imslp.org/wiki/Special:ReverseLookup/15041) | 1–2 and 3–4 |
| Robert Schumann, *Schöne Fremde*, Op. 39 No. 6 | Clara Schumann, ed., Breitkopf & Härtel, 1885. [IMSLP 270920](https://imslp.org/wiki/Special:ReverseLookup/270920) | 2–3, 5, 19, and 29–30 |
| Robert Schumann, *Die Lotosblume*, Op. 25 No. 7 | Clara Schumann, ed., Breitkopf & Härtel, plate R.S. 120. [IMSLP 270905](https://imslp.org/wiki/Special:ReverseLookup/270905) | 1–2 and 4–5 |

Each passage in `alto/assets/excerpts/` includes its MusicXML, the source URL and SHA-256 digest of the downloaded MusicXML archive.
The exercise engraving was made with Verovio 6.4.1 and Bravura. The excerpt begins with its clefs, key and meter.
Ties, slurs, and hairpins with an endpoint outside the passage are omitted.

## Piano recordings (`alto/assets/piano/`)

The piano is the Salamander Grand Piano V3 by Alexander Holm: a Yamaha C5 grand recorded with two AKG C414 microphones
(https://sfzinstruments.github.io/pianos/salamander, https://github.com/sfzinstruments/SalamanderGrandPiano). It is used under the
Creative Commons Attribution 3.0 Unported license (CC BY 3.0, https://creativecommons.org/licenses/by/3.0/), whose text is in
`alto/assets/piano/LICENSE-CC-BY-3.0.txt`. Alto uses 30 recordings from one dynamic layer, converted to mono 44.1 kHz, trimmed
and faded to 2.5 s, and levelled. Details are in `alto/assets/piano/SOURCE.txt`. Alexander Holm does not endorse Alto.

## Other instrument recordings (`alto/assets/samples/`: marimba, vibraphone, flute, horn, viola_bowed, viola_plucked)

The marimba, vibraphone, flute, French horn and viola recordings come from the Musical Instrument Samples of the University of Iowa
Electronic Music Studios (https://theremin.music.uiowa.edu/MIS.html). The site states that these recordings "have been
freely available on this website and may be downloaded and used for any projects, without restrictions." They were
converted to mono, trimmed and faded for use here. The viola is the 2012 recording by Manuel Tabora, the flute the 2000 recording by Sonja Feig and the horn the 1997 recording by Jessica Wiskus. Details are in
`alto/assets/samples/SOURCE.txt`.

## App icons (`alto/assets/icon.svg`, `alto/assets/icon-treble.svg`)

The clef in each icon is an outline from the Noto Music font (Google, SIL Open Font License 1.1), set on a rounded
square: the alto clef in `icon.svg` and the treble clef in `icon-treble.svg`.

## Anki logo in the README

Alto is developed independently of Anki. Its README uses Anki Software, LLC’s desktop launcher icon to indicate compatibility with Anki.
The badge scales the icon proportionally. [Anki](https://apps.ankiweb.net/) · [Original artwork](https://github.com/ankitects/anki/blob/a78c31d2954f4e6d620e74e992ed994b0febe9d4/qt/installer/app/resources/anki.png) · [Logo use terms](https://github.com/ankitects/anki/blob/main/LICENSE)

## Fonts used from the system, not bundled

- Noto Music (Google, SIL OFL 1.1) draws the "Noto Music" notation style, and DejaVu Sans (Bitstream Vera license with
  DejaVu changes, free to redistribute) draws a few sharp and flat signs. Alto asks the operating system for them by name.

## SuperMemo SM-2

Alto’s SM-2 review scheduler is based on the spaced repetition algorithm Piotr Woźniak developed for SuperMemo in 1987.
[Original SM-2 specification](https://super-memory.com/english/ol/sm2.htm)

## Software dependencies

- The desktop installers use Qt, PySide6, and Shiboken under LGPL-3.0. The installed `licenses/Qt/` directory
  contains the license texts, upstream credits, source archive names and checksums, and instructions for replacing
  the libraries. The matching source archives accompany the installers on the [Alto releases page](https://github.com/altosaurus/alto/releases).
- NumPy uses the BSD-3-Clause license. pytest (MIT) is used for tests only.

## Iconoir icons (`alto/ui/icons.py`)

The GitHub and music-double-note (Exercises) icons are from [Iconoir](https://github.com/iconoir-icons/iconoir), under the
[MIT license](alto/assets/licenses/LICENSE-iconoir.txt).
Their paths are unchanged; their colors follow the application theme. The music-double-note icon's note heads are filled.

Copyright (c) 2021 Luca Burgio. The full license is bundled at the path linked above.
