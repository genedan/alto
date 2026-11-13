---
title: How practice adapts
nav_order: 4
permalink: /practice/
---
Alto is not a flash-card list that shows every question equally often. It keeps track of how you do on each question
and decides what to ask next from that.

## What is recorded

Every answer is stored under your profile, including wrong ones: which exercise, which question, what you answered,
whether it was right, which attempt it was, and how long it took. A question that took three tries leaves three rows.

A **question** here is one specific problem, such as "treble clef, F♯4, in D major" or "place B♭2 on the staff". The note
value and the order of the answer buttons do not make it a different question.

## Strain

Each question has a score called **strain**, which says how much practice it needs. It starts at 1.5 for a question
you have not seen, stays between 0 and 6, and changes with each answer.

| What happened | Effect on strain |
|---|---|
| A wrong answer | **+1.5** each time, so every extra attempt pushes the question higher |
| Right first time | **−0.5** |
| Right, but only after misses | **−0.2** |
| First answer very quick | up to **−0.6** more |
| First answer very slow | up to **+1.0** more |

Because of the last two rows, a slow correct answer still counts against a question, and a very quick correct one
counts strongly in its favour.

### How speed is judged

Speed is measured on your **first** answer only, from the moment the question appears. It is compared with a "par" time
for the exercise, since reading a note takes less time than spelling a scale:

| Exercise | Par time |
|---|---|
| Note Identification, Keyboard Identification | 3 s |
| Key signatures | 5 s |
| Interval identification, Chord quality, Note Construction | 6 s |
| Scale spelling | 8 s |
| Arpeggio identification | 9 s |

At half the par time or quicker you get the full speed bonus. At par there is no effect. At four times par or slower
you get the full slow penalty. In between it changes smoothly.

## What gets asked next

Alto builds a small pool of candidates for each question: a handful of newly generated ones, plus questions you have
been asked before under the same exercise settings (the ones with the highest strain, and a few at random). It then
picks one at random, but weighted:

- The higher a question's strain, the more likely it is. Weight grows steeply with strain, so a question you keep
  missing is far more likely than one you know.
- A question you answered just now is held back for a while. For an easy question this lasts many minutes. For a hard
  one it is short, so what you struggle with returns within about a minute.
- A question you have never seen is more likely than one you have mastered, so new material keeps arriving.
- The question you just answered is never asked twice in a row.

Questions from earlier sessions are only replayed when the exercise settings match the ones they were asked under.
If you change the clefs or key signatures, you will not be given old questions that no longer fit.

## Your profile

Each profile has its own history, so two people sharing a computer do not affect each other's questions. The profile
name is shown in the menu (☰), where you can switch or add profiles. See [Statistics]({{ '/statistics/' | relative_url }}) to check how a profile is going.
