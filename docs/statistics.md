---
title: Statistics and database
nav_order: 5
permalink: /statistics/
---
## Statistics

Open the statistics from the chart button next to the menu button, or from the menu. They always show the active
profile's own answers. Use **← Back** or <kbd>Esc</kbd> to return to the page you came from.

{% include shot.html src="stats.png" alt="The statistics page with summary tiles and four charts" caption="Statistics for a demo profile." %}

### Filters

- **Exercise:** all exercises, or any one of them.
- **Timeframe:** today, the last 7, 30 or 90 days, the last year, or all time.

### What you see

- **Summary tiles:** questions answered, how often the first answer was right, the typical time to a first answer,
  attempts per question, days practised, and time spent practising. A single answer counts for at most two minutes of
  practice time, so leaving the app open does not inflate it.
- **Questions answered:** a bar per day, with the questions you got right first time in green and the ones you missed in red.
  Short timeframes switch to hours, and long ones to weeks or months.
- **Right first time:** your first-try accuracy over time. Days with no answers leave a gap.
- **Typical time to first answer:** the median, over time, so a single slow answer does not distort it.
- **By exercise:** accuracy, number of questions and typical time for each exercise.
- **Questions that need practice:** the questions with the highest strain, how often you missed them, and how many times you have answered them.

A question counts as **right** only if your first answer was right. That is the same rule the
[practice scheduler]({{ '/practice/' | relative_url }}) uses, so the numbers match what Alto thinks about your progress.

## Browsing the database

The database button next to the statistics button opens a read-only view of what is stored. It never changes anything.

{% include shot.html src="database.png" alt="The database browser listing answers in a table" %}

Three tables are available:

- **Answers:** every answer the active profile has given, newest first, with the question, your answer, whether it was right, the attempt number and the time.
- **Questions:** the record kept for each question: its strain, how often it was answered, right first time, missed, typical time and when it was last seen.
- **Profiles:** everyone who has a profile, with how many answers and questions each has.

Click a column heading to sort, and use the search box to filter every column at once. Answers and questions are
limited to the newest 10,000 rows each; the line above the table says when that applies.

### Previewing a question

Double-click a row in Answers or Questions to see that question as the exercise showed it, with its answer.

{% include shot.html src="question-preview.png" alt="A popup showing a chord on a staff with its answer and what was answered" caption="The preview shows the notes, the correct answer, what you answered and how long it took. Play sounds the notes." %}
