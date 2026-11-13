---
title: Developer guide
nav_order: 10
children: guide
permalink: /guide/
---
This guide is written so that one person, with basic Python and no help beyond the internet and a library card, can pick up
Alto and keep developing it. It explains how the program works, and also the ideas underneath it that a Python programmer
may never have met: how computers make sound, how music notation is drawn, how a flash-card program decides what to ask you
next, how to make a Qt program look and move the way you want.

It does not replace the shorter pages. [For developers]({{ '/development/' | relative_url }}) is the quick reference for
commands and tooling, [ARCHITECTURE.md](https://github.com/genedan/alto/blob/main/ARCHITECTURE.md) is a one-page map of the
code, and the [API reference]({{ '/api/' | relative_url }}) lists every public class and function. This guide is the
explanation that ties them together.

## How to use this guide

Read [Getting oriented]({{ '/guide/orientation/' | relative_url }}) first, whatever else you do. Then read what you need:

| If you want to ... | Read |
|---|---|
| Get the program running, find your way around, and follow the project's rules | [Getting oriented]({{ '/guide/orientation/' | relative_url }}) |
| Understand the Python features the code leans on (dataclasses, type hints, keyword-only arguments, closures) | [Python beyond the basics]({{ '/guide/python/' | relative_url }}) |
| Understand Qt: the event loop, signals, painting, ownership, and the traps in each | [Qt and PySide6]({{ '/guide/qt/' | relative_url }}) |
| Change how the program looks (colours, themes, stylesheets, icons, custom widgets) | [Styling beyond QtWidgets]({{ '/guide/styling/' | relative_url }}) |
| Change how music is drawn (clefs, noteheads, key signatures, fonts) | [Rendering music notation]({{ '/guide/notation/' | relative_url }}) |
| Change or add sounds (instruments, pitch shifting, timing) | [Computer audio]({{ '/guide/audio/' | relative_url }}) |
| Change what gets asked and when | [Spaced repetition and adaptive practice]({{ '/guide/spaced-repetition/' | relative_url }}) |
| Add or change movement on screen | [Animation]({{ '/guide/animation/' | relative_url }}) |
| Add an exercise, from idea to published docs | [Building an exercise]({{ '/guide/exercises/' | relative_url }}) |
| Change what is stored, or add a column | [Data and persistence]({{ '/guide/data/' | relative_url }}) |
| Run the checks, understand CI, and release | [Testing, quality and release]({{ '/guide/quality/' | relative_url }}) |
| Work out why something strange is happening | [Pitfalls and debugging]({{ '/guide/pitfalls/' | relative_url }}) |
| Look up a term, or find a book to read | [Glossary and further reading]({{ '/guide/reading/' | relative_url }}) |

## The mental model in one page

Alto is four layers. Only the top one knows that Qt exists.

```
 alto/ui          windows, drawing, animation, saved settings            (Qt)
    |
 alto/audio.py    sample playback, pitch shifting, synthesis             (Qt Multimedia)
    |
 alto/learning    profiles, SQLite, the scheduler, statistics            (no Qt)
    |
 alto/exercises   Exercise and Question, the eight exercises             (no Qt)
    |
 alto/settings    the user's choices as plain objects                    (no Qt)
    |
 alto/theory      spelled notes, intervals, scales, chords               (no Qt)
```

Three ideas carry the whole design. If you remember nothing else, remember these.

1. **A `Question` is plain data.** An exercise's only job is to turn a random number generator and the current settings into
   a `Question`: a prompt, some buttons, what to draw, which answer is right. The screen, the scheduler and the database
   know nothing about any particular exercise. They only handle `Question`s. That is why adding an exercise needs no new
   interface code.
2. **Each question has a strain.** The database keeps one number for every question a person has met: how much practice it
   still needs. Wrong answers and slow answers raise it, quick right answers lower it. The chance of a question being asked
   is an exponential function of that number. There are no due dates and no schedules.
3. **Everything is drawn, not assembled.** Staffs, keyboards, charts, switches, even the pictures in the settings panes are
   painted with `QPainter` from numbers. That is why they follow the theme, scale cleanly and animate, and also why a drawing
   bug is a geometry bug, not a layout bug.

## If you can no longer use an LLM

The code base was written with an assistant's help, and was shaped so that you do not need one to maintain it. These habits
are what make that true, and the guide assumes you keep them.

- **Every function explains itself.** Each module, class and function has a NumPy-style docstring with every parameter, the
  return value and a runnable example. Read the docstring before the code. `pytest` runs the examples, so they are never
  out of date.
- **Types are complete.** Every signature is annotated and Pyright checks them. When you are unsure what a value is, the
  signature tells you.
- **The tests are the safety net.** More than a thousand tests and doctests run in a minute. Make a change, run
  `pytest`, and fix what turns red. The tests drive widgets with Qt's offscreen platform, so no screen is needed.
- **The rules are mechanical.** Ruff, Pyright, the pre-commit hooks and the tests check the style for you. You do not have
  to remember the rules, only to run the checks. [Getting oriented]({{ '/guide/orientation/' | relative_url }}) lists them.
- **Hard parts have a chapter.** Audio, notation, spaced repetition, styling and animation each have a chapter that starts
  from first principles and ends with a reading list.

A workflow that works without an assistant:

1. Find the code. Search the [API reference]({{ '/api/' | relative_url }}) or run `grep -rn "name" alto/`.
2. Read the docstring and its example. Open a Python shell and run the example with small changes until the behaviour is clear.
3. Write a failing test for the change first, in `tests/`. It tells you when you are done.
4. Make the change. Run `pytest -x -q` often, since most mistakes show up in seconds.
5. Run the full checks listed in [Getting oriented]({{ '/guide/orientation/' | relative_url }}) before you commit.
6. If you change a docstring or a public signature, run `python scripts/api_docs.py`. If you change anything the user can
   see, regenerate the screenshots with `python scripts/screenshots.py`.

## Words that come up again and again

You will meet these terms in the chapters. Each has a short entry in the [glossary]({{ '/guide/reading/' | relative_url }}).

*Event loop. Signal and slot. Painter. Palette. Style sheet. Staff space. SMuFL. Glyph. Engraving. Sample. Sample rate.
PCM. MIDI note number. Equal temperament. Resampling. Strain. Spacing effect. Retrieval practice. Softmax. Easing.
Property animation. Offscreen platform. Doctest. Fixture. Monkeypatch.*

## A word on the reading lists

Each chapter ends with further reading. They favour books, peer-reviewed papers, standards and official documentation over
blog posts. Where a source is on the author's own site (as the Stanford audio books are), it is there because it is the
primary source. Web addresses change, so the lists give authors, titles, publishers and years, which are enough to find a
book or paper even when a link has gone. Treat the addresses as hints.
