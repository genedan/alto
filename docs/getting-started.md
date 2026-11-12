---
title: Getting started
nav_order: 2
permalink: /getting-started/
---
## What you need

- Python 3.10 or newer.
- A desktop operating system that runs Qt 6: Linux, macOS or Windows.
- Alto installs [PySide6](https://doc.qt.io/qtforpython-6/) (6.8 or newer) and numpy for you.

The default notation style is drawn with the Noto Music font, which Alto looks for on your system. Most Linux
distributions include it in their Noto font packages. If it is missing, choose another notation style in
[Settings]({{ '/settings/' | relative_url }}); the bundled fonts always work.

## Install and run

```bash
git clone https://github.com/genedan/alto.git
cd alto
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m alto
```

On Windows the virtual environment's programs are in `.venv\Scripts\` instead of `.venv/bin/`. After installing, the
command `alto` also starts the app from inside the environment.

## First launch

The first time you open Alto it asks you to create a profile.

{% include shot.html src="home.png" alt="The home screen after creating a profile" %}

Type a name and press **Create profile**. There is no password, and the name is only a label that keeps your history
separate from anyone else who uses the same computer. Next time Alto opens straight into the profile you used last.

To switch to someone else, or add another profile, open the menu (☰) and choose **Profile**.

## Your first session

1. Click an exercise on the home screen.
2. Answer by clicking a button, or by pressing the number key shown in its tooltip.
3. A correct answer turns green and plays the note. A wrong one turns red. Try again until you get it.
4. The counter at the top shows how many you have right and your current streak.

The sidebar on the left switches between exercises. The button at the top left of the exercise hides and shows it. The sliders button at the top right opens the
exercise's own settings, and the **?** button explains the exercise.

{% include shot.html src="note-identification.png" alt="Note Identification showing a note on a bass clef staff with buttons C to B" caption="An exercise screen. The row of buttons below the staff holds the possible answers." %}

## Running the tests

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```
