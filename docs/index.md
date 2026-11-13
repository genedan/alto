---
title: Home
nav_order: 1
permalink: /
---
<div class="hero">
  <h1>Alto</h1>
  <p class="lead">Music theory drills for the desktop. Alto remembers what you get wrong and how long you take, and asks those questions again sooner.</p>
</div>

{% include shot.html src="home.png" alt="Alto's home screen with a card for each exercise" caption="The home screen. Pick an exercise to start." %}

## What you can practise

<ul class="cards">
  <li><strong>Note Identification</strong>Name notes on the treble, bass, alto and tenor clefs or the grand staff.</li>
  <li><strong>Keyboard Identification</strong>Name the highlighted key on a piano keyboard.</li>
  <li><strong>Note Construction</strong>Click the staff where a named note belongs.</li>
  <li><strong>Interval identification</strong>Name the interval between two notes.</li>
  <li><strong>Key signatures</strong>Read a key signature on a staff, or count the sharps and flats of a key, in major, minor and the modes.</li>
  <li><strong>Scale spelling</strong>Spell a degree of a scale or mode.</li>
  <li><strong>Chord quality</strong>Tell triads and seventh chords apart.</li>
  <li><strong>Arpeggio identification</strong>Name the type and the inversion of a broken chord.</li>
</ul>

## What makes it different

- **It learns from your answers.** Every answer is recorded under your profile. Questions you miss, or take a long time over, come back more often. Questions you answer quickly and correctly fade into the background. [How it works]({{ '/practice/' | relative_url }}).
- **Statistics and a database browser.** Charts of accuracy, speed and volume, filterable by exercise and timeframe, plus a table view of everything stored. [Statistics]({{ '/statistics/' | relative_url }}).
- **Notation and keyboards your way.** Eleven notation styles, including Finale Maestro, Leland, Bravura and two handwritten jazz styles, and eleven keyboard looks from a modern piano to a French harpsichord. [Settings]({{ '/settings/' | relative_url }}).
- **Local and private.** Your history is one file on your computer. Alto makes no network connections. [Your data]({{ '/data/' | relative_url }}).
- **Free and open source** under the MIT License.

{% include shot.html src="stats.png" alt="The statistics page with summary tiles and charts of accuracy, speed and volume" caption="Statistics for a demo profile: how often you are right, how fast, and how much you practise." %}

## Get started

```bash
git clone https://github.com/genedan/alto.git
cd alto
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m alto
```

The [getting started guide]({{ '/getting-started/' | relative_url }}) has the details, including what happens the first time you open the app.
