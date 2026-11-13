---
title: Glossary and further reading
parent: guide
order: 13
permalink: /guide/reading/
---
The first part of this page is a glossary of terms used in the guide and in the code, each with something to search for. The second
is a reading list by subject, favouring books, peer-reviewed papers, standards and official documentation over blog posts.
Web addresses change; the authors, titles and years are given so you can find a source even after a link has moved.

## A suggested order for learning

If you are new to some of this, this order builds on itself.

1. **The program as a user.** Run it, use every exercise, open every settings pane, look at the statistics and the database page.
2. **Python's less common features**: [Python beyond the basics]({{ '/guide/python/' | relative_url }}), with *Fluent Python* beside it.
3. **Qt's model**: [Qt and PySide6]({{ '/guide/qt/' | relative_url }}); build a ten-line window that draws a rectangle and responds to a click.
4. **One small change** in `alto/ui`: alter a colour, a radius, a duration. See [Styling]({{ '/guide/styling/' | relative_url }}) and
   [Animation]({{ '/guide/animation/' | relative_url }}).
5. **One new exercise**: [Building an exercise]({{ '/guide/exercises/' | relative_url }}). It touches the data model, the tests and the docs, in a small way.
6. **A change to the scheduler**, tested by simulation: [Spaced repetition]({{ '/guide/spaced-repetition/' | relative_url }}).
7. **Then whichever of notation and audio you need.** They are the deepest chapters and the most independent.

## Glossary

Terms are in alphabetical order. Italic words in an entry are terms to search for.

**Aliasing.** Frequencies above half the sample rate folding back as false lower ones. Search: *Nyquist frequency*, *anti-aliasing filter*.
See [Computer audio]({{ '/guide/audio/' | relative_url }}).

**Anchor (SMuFL).** A named point on a glyph, such as where a stem should attach to a notehead. Search: *SMuFL metadata*.

**Antialiasing (drawing).** Smoothing the jagged edges of shapes by blending edge pixels. Qt: `QPainter.RenderHint.Antialiasing`.

**Attempt.** One answer to a question, right or wrong. The log of attempts is the history; `attempt_no` is 1 for the first answer to a
showing. See [Data]({{ '/guide/data/' | relative_url }}).

**Bit depth.** How many bits store each audio sample. Alto uses 16. Search: *quantisation*, *dynamic range*.

**Bounding box (ink box).** The smallest rectangle around a glyph's shape; used to centre a notehead. Search: *glyph metrics*.

**Brace.** The curly bracket joining the two staves of a grand staff.

**Closure.** A function that remembers variables from the function that made it. Search: *lexical scope*, *late binding*.

**Clef.** The sign at the start of a staff saying which pitches its lines mean. Treble, bass, and the C clefs (alto, tenor, soprano,
mezzo-soprano, baritone).

**Cooldown (scheduler).** How long a question stays unlikely after being asked, long for easy questions and short for hard ones.

**Cold start.** What to do about a question or a user with no history.

**CWMN.** Common Western Music Notation, the notation Alto draws.

**Dataclass.** A class that holds fields, with its methods written for you. `@dataclass`; `frozen=True` makes it immutable.

**Decibel (dB).** A logarithmic unit for amplitude ratios: `20 × log10(ratio)`. Halving an amplitude is -6 dB.

**Desirable difficulties.** Robert Bjork's term for practice conditions that feel harder but make learning last. Search: *interleaving*.

**Device pixel ratio.** How many physical pixels make one of Qt's logical pixels on a high-resolution screen. Search: *HiDPI*.

**Diatonic index.** `octave * 7 + letter`: a note's position on the staff ladder, ignoring accidentals. `Note.diatonic`.

**Doctest.** An example in a docstring that is run as a test. Search: *doctest module*.

**Easing.** The shape of an animation's speed over time. `QEasingCurve`. Search: *Penner equations*.

**Engraving.** Preparing music for print; the craft that notation software imitates. Search: *music engraving rules*.

**Equal temperament.** Dividing the octave into 12 equal semitones, each a frequency ratio of 2^(1/12).

**Event loop.** The loop that waits for clicks, timers and repaint requests, and calls the code that handles them. `QApplication.exec()`.

**Fake (test).** A small class that stands in for something real and records what is done to it. Search: *test double*.

**Fixture (pytest).** A function that prepares what a test needs; a test asks for it by parameter name.

**Forgetting curve.** The decay of memory over time without review. Search: *Ebbinghaus*.

**FSRS.** The Free Spaced Repetition Scheduler, a modern memory-model scheduler; its model is *DSR* (difficulty, stability, retrievability).

**Glyph.** The shape of one character or symbol in a font. In a music font, a notehead, a clef, a flag.

**Grand staff.** A treble and a bass staff joined by a brace, used for piano.

**Interleaving.** Mixing different kinds of problem in one practice session.

**Item key.** A 20-character hash that identifies a question, so the same question is recognised when it returns.
`Question.item_key()`.

**Keyword-only argument.** A parameter that must be given by name, written after a bare `*` in the definition.

**Ledger line.** A short extra line for a note above or below the staff.

**Leech.** A card or question that is failed again and again.

**MIDI note number.** A number for each pitch: middle C is 60, A4 is 69, each semitone adds 1.

**Model/view.** Separating the data (the model) from the widget that shows it (the view). Qt: `QAbstractTableModel`, `QTableView`.

**Monkeypatch (pytest).** A fixture that temporarily replaces an attribute or function for one test.

**Multisampling.** Recording an instrument at many pitches and playing the nearest. Search: *sampler*, *velocity layers*.

**Nyquist frequency.** Half the sample rate, the highest frequency that can be represented: 22,050 Hz at 44.1 kHz.

**Offscreen platform.** Qt's platform plugin that draws into memory instead of onto a screen, used by the tests.
`QT_QPA_PLATFORM=offscreen`.

**Overtone / partial.** A frequency above the fundamental in a note's sound; together they make the timbre.

**Painter (`QPainter`).** The object that draws shapes, text and images onto a widget or image.

**Palette (`QPalette`).** A widget's table of named colours (`Window`, `Base`, `Text`, `Highlight` ...).

**PCM.** Pulse-code modulation: audio stored as a list of sample values. WAV files carry PCM.

**Pitch shifting.** Changing the pitch of a recording. Alto does it by *resampling*, which also changes the duration.

**Property animation.** Animating a named property of a Qt object. `QPropertyAnimation`.

**Resampling.** Changing the sample rate or reading samples at a different speed, by interpolating between neighbours.

**Retrieval practice / testing effect.** Recalling an answer strengthens memory more than rereading it.

**Sample (audio).** One measurement of a sound signal. Do not confuse with a recorded *sample* in the music-production sense: a
recording of one note.

**Sample rate.** Measurements per second; 44,100 for CD quality.

**Signal and slot.** Qt's way for an object to announce an event and others to respond. `Signal`, `.connect`, `.emit`.

**SM-2.** The SuperMemo 2 algorithm: item intervals multiplied by an ease factor. Search: *Wozniak*.

**SMuFL.** Standard Music Font Layout: names, code points and metadata for music fonts. Search: *W3C Music Notation Community Group*.

**Softmax.** Choosing among options with probability proportional to `exp(β × value)`. Search: *Boltzmann distribution*,
*exploration-exploitation*.

**Spacing effect.** Spreading study over time produces better lasting memory than cramming.

**Staff space.** The distance between two staff lines; the unit of measurement in engraving. Alto's `gap`.

**Strain.** Alto's number, 0 to 6, for how much practice a question needs.

**Style sheet (QSS).** Qt's CSS-like language for appearance. Search: *Qt Style Sheets reference*.

**Timbre.** The quality that distinguishes two instruments playing the same note; set by the mix of partials.

**Token (cancellation).** A counter captured by a delayed callback so it can tell it has been superseded and do nothing.

**Type hint.** An annotation saying what type a value should be; checked by Pyright. Search: *PEP 484*.

**Voice (notation).** An independent line of music on a staff. Alto's staffs show single notes and simple chords and do not need
voices.

**WAV / RIFF.** A common audio file format: a small header followed by PCM samples.

## Reading list

### Python and software craft

- Luciano Ramalho, *Fluent Python*, 2nd ed. (O'Reilly, 2022).
- Brett Slatkin, *Effective Python*, 2nd ed. (Addison-Wesley, 2019).
- Brian Okken, *Python Testing with pytest*, 2nd ed. (Pragmatic Bookshelf, 2022).
- John Ousterhout, *A Philosophy of Software Design* (Yaknyam Press, 2018): on keeping modules deep and interfaces small, which is
  what `Question` and `Exercise` are.
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd ed. (Addison-Wesley, 2018).
- Andrew Hunt and David Thomas, *The Pragmatic Programmer*, 20th anniversary ed. (Addison-Wesley, 2019).
- Erich Gamma, Richard Helm, Ralph Johnson and John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*
  (Addison-Wesley, 1994): observer, strategy, and the other names for what the code does.
- Python Software Foundation, *The Python Language Reference* and *The Python Standard Library*, docs.python.org; PEPs 8, 257, 484,
  557, 604 and 621 at peps.python.org.
- Python Packaging Authority, *Python Packaging User Guide*, packaging.python.org.
- Scott Chacon and Ben Straub, *Pro Git* (Apress, 2014; free at git-scm.com/book).

### Qt, drawing and interface design

- The Qt documentation, doc.qt.io/qt-6 and doc.qt.io/qtforpython-6.
- Jasmin Blanchette and Mark Summerfield, *C++ GUI Programming with Qt 4*, 2nd ed. (Prentice Hall, 2008).
- Mark Summerfield, *Rapid GUI Programming with Python and Qt* (Prentice Hall, 2007).
- Donald A. Norman, *The Design of Everyday Things*, revised ed. (Basic Books, 2013).
- Steve Krug, *Don't Make Me Think, Revisited* (New Riders, 2014).
- Edward R. Tufte, *The Visual Display of Quantitative Information*, 2nd ed. (Graphics Press, 2001).
- Cynthia A. Brewer, *Designing Better Maps* (Esri Press, 2005): colour schemes for ordered and categorical data.
- Charles Poynton, *Digital Video and HD*, 2nd ed. (Morgan Kaufmann, 2012).
- Ellen Lupton, *Thinking with Type*, 2nd ed. (Princeton Architectural Press, 2010).
- *Web Content Accessibility Guidelines 2.1*, W3C, w3.org/TR/WCAG21.

### Animation and motion

- Val Head, *Designing Interface Animation* (Rosenfeld Media, 2016).
- Robert Penner, *Programming Macromedia Flash MX* (McGraw-Hill/Osborne, 2002), chapter 7: the easing equations.
- Frank Thomas and Ollie Johnston, *The Illusion of Life: Disney Animation* (Abbeville Press, 1981).
- Richard Williams, *The Animator's Survival Kit* (Faber and Faber, 2001).
- Page Laubheimer, "Executing UX Animations: Duration and Motion Characteristics", Nielsen Norman Group, nngroup.com (2014).

### Music notation and music theory in code

- Elaine Gould, *Behind Bars: The Definitive Guide to Music Notation* (Faber Music, 2011).
- Ted Ross, *The Art of Music Engraving and Processing* (Hansen Books, 1970).
- Gardner Read, *Music Notation: A Manual of Modern Practice*, 2nd ed. (Allyn and Bacon, 1969).
- *Standard Music Font Layout (SMuFL)*, W3C Music Notation Community Group, w3c.github.io/smufl/latest.
- *MusicXML 4.0*, W3C Music Notation Community Group, w3.org.
- Donald Byrd, *Music Notation by Computer* (PhD dissertation, Indiana University, 1984).
- The LilyPond documentation, lilypond.org/documentation, including the "Essay on automated music engraving".
- Michael Scott Cuthbert and Christopher Ariza, "music21: A Toolkit for Computer-Aided Musicology and Symbolic Music Data",
  *Proceedings of the 11th International Society for Music Information Retrieval Conference* (2010), and the music21 documentation
  at music21.org (MIT).
- Stefan Kostka and Dorothy Payne, *Tonal Harmony*, 7th ed. (McGraw-Hill, 2013).
- Edward Aldwell, Carl Schachter and Allen Cadwallader, *Harmony and Voice Leading*, 4th ed. (Schirmer, 2011).
- Walter B. Hewlett, "A base-40 number-line representation of musical pitch notation", *Musikometrika* 4, 1992: one way to number
  spelled pitches, an alternative to Alto's letter, accidental and octave.

### Audio and signal processing

- Julius O. Smith III, the four online books at ccrma.stanford.edu/~jos (Stanford CCRMA): *Mathematics of the DFT*, *Introduction to Digital
  Filters*, *Physical Audio Signal Processing*, *Spectral Audio Signal Processing*.
- Ken C. Pohlmann, *Principles of Digital Audio*, 6th ed. (McGraw-Hill, 2010).
- Alan V. Oppenheim and Ronald W. Schafer, *Discrete-Time Signal Processing*, 3rd ed. (Pearson, 2010).
- Miller Puckette, *The Theory and Technique of Electronic Music* (World Scientific, 2007).
- Curtis Roads, *The Computer Music Tutorial* (MIT Press, 1996).
- Udo Zölzer (ed.), *DAFX: Digital Audio Effects*, 2nd ed. (Wiley, 2011).
- Neville H. Fletcher and Thomas D. Rossing, *The Physics of Musical Instruments*, 2nd ed. (Springer, 1998).
- Claude E. Shannon, "Communication in the Presence of Noise", *Proceedings of the IRE* 37(1), 1949.
- Mark Dolson, "The Phase Vocoder: A Tutorial", *Computer Music Journal* 10(4), 1986.
- Kevin Karplus and Alex Strong, "Digital Synthesis of Plucked-String and Drum Timbres", *Computer Music Journal* 7(2), 1983.
- *MIDI 1.0 Detailed Specification*, MIDI Manufacturers Association, midi.org.
- The University of Iowa Electronic Music Studios, *Musical Instrument Samples*, theremin.music.uiowa.edu/MIS.html.

### Learning science and adaptive practice

- Peter C. Brown, Henry L. Roediger III and Mark A. McDaniel, *Make It Stick* (Belknap Press, 2014): the best place to start.
- Nicholas J. Cepeda and colleagues, "Distributed practice in verbal recall tasks", *Psychological Bulletin* 132(3), 2006.
- Henry L. Roediger III and Jeffrey D. Karpicke, "Test-enhanced learning", *Psychological Science* 17(3), 2006.
- Burr Settles and Brendan Meeder, "A Trainable Spaced Repetition Model for Language Learning", *ACL 2016*.
- Piotr A. Wozniak and Edward J. Gorzelańczyk, "Optimization of repetition spacing in the practice of learning", *Acta Neurobiologiae
  Experimentalis* 54, 1994.
- Radek Pelánek, "Applications of the Elo rating system in adaptive educational systems", *Computers & Education* 98, 2016.
- Albert T. Corbett and John R. Anderson, "Knowledge tracing", *User Modeling and User-Adapted Interaction* 4, 1995.
- Richard S. Sutton and Andrew G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed. (MIT Press, 2018).
- Thomas M. Haladyna, *Developing and Validating Multiple-Choice Test Items*, 3rd ed. (Lawrence Erlbaum, 2004).

### Data

- The SQLite documentation, sqlite.org/docs.html.
- Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2017).
- C. J. Date, *An Introduction to Database Systems*, 8th ed. (Pearson, 2003).

### Testing, debugging and delivery

- Kent Beck, *Test-Driven Development: By Example* (Addison-Wesley, 2002).
- Michael C. Feathers, *Working Effectively with Legacy Code* (Prentice Hall, 2004).
- Gerard Meszaros, *xUnit Test Patterns* (Addison-Wesley, 2007).
- Jez Humble and David Farley, *Continuous Delivery* (Addison-Wesley, 2010).
- Andreas Zeller, *Why Programs Fail*, 2nd ed. (Morgan Kaufmann, 2009).
- *Semantic Versioning 2.0.0*, semver.org.
- For shipping a standalone application (not needed to develop Alto): the Qt for Python documentation page "Deployment", and the
  manuals for the PyInstaller (pyinstaller.org) and BeeWare Briefcase (briefcase.readthedocs.io) packagers.
