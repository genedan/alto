---
title: Animation
parent: guide
order: 8
permalink: /guide/animation/
---
Alto moves a few things on purpose: the exercise list slides shut, the settings pane slides open and its pages slide in and out,
switches slide, and an answer button fades to green or red. None of it is decoration. Motion tells the eye *what changed and
where it went*. This chapter explains Qt's animation tools, how each of Alto's animations is built, the patterns that keep them
from going wrong, and the design rules that decide how long and in what manner to move something.

## What an animation is

An animation changes a value over time. Everything else follows from that sentence.

- Pick a **value** that describes the look: a number from 0 to 1, a position, a width, a colour.
- Pick a **start** and an **end** and a **duration**.
- At each tick Qt computes where the value is on its way (a number between the start and the end, shaped by an **easing
  curve**) and hands it to you.
- You apply it: move something, resize it, set a colour, call `update()` and repaint with it.

A screen refreshes about 60 times a second, so a 200 ms animation is roughly twelve frames. Qt drives the ticks from its
event loop, which means they stop if you block the loop. That is why the first rule of
[Qt and PySide6]({{ '/guide/qt/' | relative_url }}) (never block) is also the first rule of animation.

## The tools Qt provides

| Class | What it does |
|---|---|
| `QVariantAnimation` | Animates *any* value (a float, a colour, a point) and calls a function with each value: `valueChanged`. The general tool. |
| `QPropertyAnimation` | Animates a named **property** of an object (`b"pos"`, `b"maximumWidth"`, `b"volume"`) directly, so you do not write the callback. |
| `QParallelAnimationGroup` | Runs several animations at once. |
| `QSequentialAnimationGroup` | Runs them one after another. |
| `QEasingCurve` | Shapes the progress: `OutCubic`, `InOutQuad`, `Linear`, `OutBack` and about forty more. |
| `QTimer` | Not an animation, but the tool for "do this once, later". |

Two of these cover nearly everything. Use `QPropertyAnimation` when the thing you are animating is already a Qt property, and
`QVariantAnimation` when it is not (or you need to draw from the value).

### Easing

A linear animation moves at constant speed, which looks mechanical, because real things accelerate and slow. An **easing
curve** changes the speed over the animation. The names say where the speed changes: *In* starts slowly, *Out* ends slowly,
*InOut* does both. Alto uses `OutCubic` almost everywhere: it starts fast and settles gently, which feels responsive,
because the first thing the user sees is immediate movement. The curves go back to the **easing equations** of Robert Penner,
which Qt's set is based on.

Rules of thumb that most design systems agree on: use ease-**out** for things *entering* or responding to the user (they arrive
and settle); ease-**in** for things *leaving* (they accelerate away); ease-**in-out** for things that move from one place to
another on screen; and **linear** only for colour fades, rotations and progress bars, where no physical object is implied.

## Alto's animations, one at a time

### The settings page slide: `SlideStack`

`SlideStack` in `settings_panel.py` is a `QStackedWidget` whose pages slide instead of switching. It is a good model of how
to build a transition by hand:

```python
def slide_to(self, index):
    if self.sliding or index == self.currentIndex():
        return  # ignore requests mid-transition
    old, new = self.currentWidget(), self.widget(index)
    w, sign = self.width(), 1 if index > self.currentIndex() else -1
    new.setGeometry(0, 0, w, self.height())
    new.move(sign * w, 0)  # park the new page just outside, on the side it enters from
    new.show()
    new.raise_()
    group = QParallelAnimationGroup(self)
    for widget, start, end in ((old, 0, -sign * w), (new, sign * w, 0)):
        anim = QPropertyAnimation(widget, b"pos", group)  # animate the widget's own position property
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(QPoint(start, 0))
        anim.setEndValue(QPoint(end, 0))
        group.addAnimation(anim)
    group.finished.connect(done)  # setCurrentIndex(index) and put both pages at (0, 0)
    group.start()
```

Points to copy: the new page is positioned off-screen *before* it is shown (otherwise it flashes in place for one frame); the two
pages move in parallel; a request that arrives mid-slide is ignored rather than queued (so a double click does not slide twice);
and the final state is set in `finished`, not assumed, so the widgets always end in a clean position.

### Opening and closing a pane: animate a limit

The exercise's settings pane opens by animating `maximumWidth` of the pane from 0 to `PANE_WIDTH` (`QPropertyAnimation(self.pane,
b"maximumWidth", self)`, 220 ms, `OutCubic`). The layout does the rest: as the pane's allowed width grows, the layout gives it
the room and shrinks its neighbour. This is a common Qt trick: **animate a constraint, not a position**, and let the layout
move everything. The pane is hidden when it finishes at zero (`_pane_settled`) so it takes no space and cannot be tabbed into.

### The sidebar: animate the splitter

The sidebar collapse in `MainWindow._set_sidebar` uses a `QVariantAnimation` from the current width to the target and, on each
tick, calls `splitter.setSizes`. The animation is a number; the callback decides what the number means. Two details:

- It temporarily lowers the list's minimum width so the width can pass through values below the usual minimum, and restores it
  in `done`.
- It stops the previous animation first (`self._sidebar_anim.stop()`) and starts from wherever the sidebar currently is, so
  clicking the toggle in the middle of a slide reverses smoothly instead of jumping.

### The switch knob: animate a number, paint from it

`Switch` (also in `settings_panel.py`) holds a float `_pos` between 0 and 1. A `QVariantAnimation` of 140 ms moves `_pos`, and
each tick calls `update()`. `paintEvent` draws the track colour as `blend(off, b=on, t=self._pos)` and the knob at
`margin + r + _pos * travel`. One number drives both the colour and the position, so they cannot disagree. The class
`setChecked` skips the animation (**"no animation when set programmatically"**) so that loading a setting at start-up does not
make every switch slide.

### The right/wrong flash: animate a colour

`ExerciseView._flash` fades an answer button from black to green or red in 350 ms with a **linear** curve, because it is a colour
fade. It uses `QVariantAnimation` with a start of 0.0 and an end of 1.0 and in its callback computes `blend(start, b=end, t=t)`
and sets the button's style sheet from the result. The animations are kept in a list (`self._anims`) that is cleared when the next
question appears, so nothing animates a button that no longer exists.

### The fade of a sound

Not visual, but the same idea: `Sounds._release` fades a `QSoundEffect`'s `volume` property to 0 in 70 ms with a
`QPropertyAnimation`, then stops it. See [Computer audio]({{ '/guide/audio/' | relative_url }}).

## Patterns that keep animations correct

1. **Keep a reference.** A `QVariantAnimation` created in a function with no parent and no stored reference can be garbage
   collected while running, and simply stops. Give it a parent (`QVariantAnimation(self)`) or store it (`self._anim = ...`).
2. **Stop the old one first.** If an animation of the same property may already be running, call `.stop()` before starting a new
   one, and start from the *current* value, not from a remembered end. Otherwise two animations fight.
3. **Set the end state in `finished`.** Do not rely on the last tick landing exactly on the end value.
4. **Guard against re-entry.** Ignore a request while a transition is running (`SlideStack`), or cancel and restart (the sidebar).
   Decide deliberately which; the one you did not decide on is the one with the bug.
5. **Cancel late callbacks with a token.** A `QTimer.singleShot` cannot be cancelled once scheduled. If the callback might fire
   after the state has moved on (a new question has appeared), have it compare a counter it captured against the current one and
   do nothing if they differ. `ExerciseView._pair_token` and `Sounds._sequence_run` do this.
6. **Do not animate loading.** Setting a value from saved settings should jump, not animate (see `Switch.setChecked`).
7. **Animate cheap things.** Each tick repaints. Moving a widget or changing a width is cheap; repainting a large, complex
   widget sixty times a second is not. If a widget is expensive to draw, draw it once into a `QPixmap` and animate the pixmap.

## Testing animations

Tests run the event loop long enough for an animation to finish: `QTest.qWait(300)` after triggering a 220 ms slide, then
assert the end state. A shorter wait asserts the middle. `tests/test_settings_panels.py` has a `slide()` helper that waits
300 ms for a page to finish sliding, and `SlideStack.sliding` reports whether a slide is under way. To test that your code ignores a request
during a slide, call it twice in a row and assert one slide happened.

Because tests wait in real time, keep durations short. There is no virtual clock in Qt's animation framework.

## Deciding how it should move

A few principles, from animation and interface design.

- **Duration.** Interface animations feel good between about 150 and 300 ms. Under 100 ms the eye barely registers movement; over
  500 ms it feels slow, and a user doing something repeatedly is made to wait. Larger moves can take longer than small ones.
  Alto's are 70 to 350 ms.
- **Purpose.** Each animation should answer a question: where did that come from, what changed, did my action work? An animation
  that only decorates is noise the second time you see it.
- **Direction means something.** A page that slides in from the right says "forward"; sliding back from the left says "back".
  Alto's settings pages use this, and so should anything new.
- **Continuity.** Moving the object from where it was to where it is, instead of cutting, preserves the user's sense of what it is.
- **Follow-through and easing.** Real objects do not stop dead. Easing out gives a soft landing.
- **Respect the user's settings.** Many people turn on a "reduce motion" option in their operating system. Alto does not read it
  yet, which is a good first improvement: if it is set, use durations of 0.
- **Stay consistent.** Same durations and curves for the same kinds of motion, so the program feels like one thing.

The 12 principles of animation from the Disney studios (squash and stretch, anticipation, staging, slow in and slow out, and so on)
were written for cartoon characters, and the subset that applies to interfaces is the last three paragraphs above.

## Words to search for

*Tweening* (calculating the frames between two states). *Easing, ease-in, ease-out, Bézier easing, cubic-bezier.* *Spring
animation* (physically based, overshoots; not in Qt's standard set). *Frame rate, vsync, jank.* *Dirty rectangle* (repaint only
what changed). *Compositing.* *Reduced motion* (an accessibility setting). *Skeleton screens* and *loading states*.

## Further reading

- The Qt documentation: "The Animation Framework", and the class pages for `QVariantAnimation`, `QPropertyAnimation`,
  `QAbstractAnimation`, `QParallelAnimationGroup` and `QEasingCurve` (which has a picture of every curve), at doc.qt.io.
- Robert Penner, *Programming Macromedia Flash MX* (McGraw-Hill/Osborne, 2002), chapter 7: the easing equations that nearly every
  animation library, Qt included, implements.
- Val Head, *Designing Interface Animation: Improving the User Experience Through Animation* (Rosenfeld Media, 2016): the book on
  motion in interfaces, with guidance on duration, easing and purpose.
- Frank Thomas and Ollie Johnston, *The Illusion of Life: Disney Animation* (Abbeville Press, 1981): the twelve principles.
- Richard Williams, *The Animator's Survival Kit* (Faber and Faber, 2001): timing and spacing in depth.
- Page Laubheimer, "Executing UX Animations: Duration and Motion Characteristics", Nielsen Norman Group, nngroup.com (2014):
  research-backed guidance on how long interface animations should last.
- World Wide Web Consortium, *Web Content Accessibility Guidelines 2.1*, success criterion 2.3.3 "Animation from Interactions",
  w3.org/TR/WCAG21: on motion and people who are sensitive to it.
