---
title: Styling beyond QtWidgets
parent: guide
order: 4
permalink: /guide/styling/
---
Out of the box, Qt widgets look like whatever platform they run on: grey rectangles on Windows, rounded and translucent on
macOS. Alto wants one consistent look with rounded corners, soft highlights and a light and a dark theme, and some pieces
(the staff, the keyboard, the switches, the charts) that no standard widget provides. This chapter explains the layers Qt gives
you for appearance, which one Alto uses for what, and the colour and design ideas behind the choices.

## Four layers of appearance

From the most automatic to the most hands-on:

1. **The style (`QStyle`).** The object that knows how to draw every standard widget: a button, a scroll bar, a check box. On
   each platform Qt picks the native one. *Fusion* is a built-in cross-platform style that looks the same everywhere.
2. **The palette (`QPalette`).** A table of named colours (*roles*) that the style draws with: `Window` (the background),
   `Base` (the background of lists and text boxes), `Text`, `Highlight` (the selection colour), `Mid`, `Midlight`, `Dark`, and
   so on. Each role has three states: active, inactive and disabled.
3. **Style sheets (QSS).** A subset of CSS that overrides how standard widgets are drawn: borders, radii, backgrounds, padding.
4. **Custom painting.** Overriding `paintEvent` and drawing the widget yourself with `QPainter`.

Alto uses all four, each where it fits:

| Need | Layer | Where |
|---|---|---|
| Light, dark or follow-the-system | Palette (through the colour scheme) | `alto/ui/theme.py` |
| Rounded buttons, check boxes, lists, menus, scroll bars | Style sheet | `alto/ui/style.py` |
| Switches, theme cards, charts, the staff, the keyboard | Custom painting | `settings_panel.py`, `app_settings.py`, `charts.py`, `staff.py`, `keyboard.py` |
| Monochrome icons that match the text colour | SVG, tinted and rendered | `alto/ui/icons.py` |

## Themes: the colour scheme and the palette

Since Qt 6.8 you can tell Qt which colour scheme to use: `QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)`.
Qt then switches the palette. `Qt.ColorScheme.Unknown` means "follow the operating system". `apply_theme` does exactly this,
then builds the style sheet from the new palette:

```python
def apply_theme(key: str) -> None:
    QGuiApplication.styleHints().setColorScheme(_SCHEMES.get(key, Qt.ColorScheme.Unknown))
    app = QApplication.instance()
    app.setStyleSheet(app_style(app.palette()))
```

The chosen theme is saved (`ui/theme`) and applied again at start-up, before any window exists.

The rule that makes theming work: **take colours from the palette, never from a constant.** A widget that paints with
`palette.color(QPalette.ColorRole.Text)` is correct in both themes; one that paints with `QColor("black")` is correct in one.
The staff is deliberately a white "paper" in both themes, because music reads best black on white; that is a design decision,
not an oversight.

## Style sheets, in practice

QSS looks like CSS and mostly behaves like it, with differences that matter.

```css
QPushButton {
    border: 1px solid <edge colour>;
    border-bottom-width: 2px;           /* a heavier lower edge lifts the button off the page */
    border-radius: 10px;
    padding: 6px 12px;
}
QPushButton:hover   { border-color: palette(highlight); }
QPushButton:pressed { border-bottom-width: 1px; padding-top: 7px; }
QPushButton:checked { border: 2px solid palette(highlight); }
```

- **Selectors.** `QPushButton` matches the class and its subclasses; `QListWidget#nav` matches the one with
  `setObjectName("nav")`; `QToolButton[arrowButton="true"]` matches a widget with that *dynamic property*
  (`widget.setProperty("arrowButton", True)`). If you set a property after the widget is shown, call
  `widget.style().unpolish(widget)` and `.polish(widget)` so the sheet is applied again.
- **Pseudo-states** (`:hover`, `:pressed`, `:checked`, `:disabled`) and **sub-controls** (`::indicator`, `::item`, `::handle`)
  name the parts of a widget you can style separately.
- **`palette(highlight)`** reads a palette role, so a sheet can follow the theme without Python.
- **The box model** is the same as CSS: content, padding, border, margin.
- **A widget that gets a style sheet is drawn by a different code path.** Once you style a part of a widget, Qt stops using the
  platform style for it and you must style the rest, or it looks half done. Styling `QCheckBox::indicator` means styling its
  checked, hover and disabled states too, as `style.py` does.
- **What QSS cannot do.** It cannot animate (a `:hover` change is instant), cannot draw arbitrary shapes, and gradients are
  limited to `qlineargradient` and `qradialgradient`. For those, paint it yourself.

Alto's sheet is one Python string template in `alto/ui/style.py`, filled with `str.format` using colours computed from the
current palette:

```python
return _TEMPLATE.format(RADIUS=RADIUS, edge=dark, accent=accent_c.name(), nav_hover=blend_name(window_c, b=text_c, t=0.07), ...)
```

Because `.format` treats `{` and `}` as fields, every brace that is really CSS is doubled in the template. If you add a rule
and get a `KeyError` or `IndexError`, you forgot to double a brace. The sheet is rebuilt on every theme change, since the
colours come from the palette.

## Painting your own widgets

When no sheet can do it, draw it. The `Switch` in `settings_panel.py` is a good small example: about thirty lines of
`paintEvent` give a pill-shaped track whose colour is a blend between the "off" and "on" palette colours, and a white knob
that slides.

```python
track = blend(off, b=on, t=self._pos)  # _pos goes 0 -> 1 while the knob slides
p.setBrush(track)
p.drawRoundedRect(self.rect(), self.H / 2, self.H / 2)
x = margin + r + self._pos * (self.W - 2 * (margin + r))
p.drawEllipse(QPointF(x, self.H / 2), r, r)
```

Patterns to copy:

- **State in numbers, drawing from numbers.** The widget holds `_pos`, a float. Animation changes the number and calls
  `update()`. Painting reads the number. There is no separate "off look" and "on look".
- **`blend(a, b=, t=)`** in `alto/ui/colors.py` mixes two colours linearly. It is the workhorse: hover tints, disabled states,
  the fade on a right or wrong answer.
- **Read the palette inside `paintEvent`,** not in `__init__`, so a theme change shows up on the next repaint.
- **`sizeHint()`** must be right, or layouts will squash the widget.
- **Keep drawing code free of side effects.** `paintEvent` can be called at any time and as often as Qt likes.

## Colour: the ideas worth knowing

- **sRGB and gamma.** Screen colours are stored in sRGB, which is not linear in light. Mixing two sRGB colours with plain
  arithmetic, as `blend` does, gives a result a little darker in the middle than a physically correct mix. For UI tints that is
  fine and common. For anything that must be perceptually even (a heat map), use a designed palette. See Poynton in the reading
  list.
- **Contrast.** Text must be readable against its background. The WCAG guidelines define a contrast ratio from the relative
  luminance of two colours and ask for at least 4.5:1 for body text. When you add a colour, check it in both themes.
- **Do not rely on colour alone.** About one man in twelve cannot distinguish red from green. Alto marks right and wrong answers
  with green and red flashes, and shows the explanation as text as well. If you add a chart
  that needs red against green to be read, add a second cue (position, a label, a pattern) or pick a colour-blind-safe pair
  such as blue and orange.
- **Sequential palettes.** The review heatmap uses one hue in steps of lightness, which reads as "more". That is the right choice
  for ordered data. Cynthia Brewer's ColorBrewer scheme names (sequential, diverging, qualitative) are the vocabulary.
- **Alpha.** A colour with transparency (`setAlpha(110)`) is the cheapest way to dim something, as `Switch` does when disabled.

## Icons

`alto/ui/icons.py` holds icons as snippets of SVG with the word `COLOR` where the fill goes. `svg_icon(inner, color=...)`
replaces it, renders the SVG with `QSvgRenderer` into a pixmap twice the size, sets the **device pixel ratio** to 2 so it is
sharp on a high-resolution screen, and returns a `QIcon`. Pass the text colour from the palette and the icon matches the theme.

Because the colour is baked into the pixmap when the icon is made, an icon does not change by itself when the theme changes.
That is why changing the theme builds a fresh `MainWindow` (`rebuild()`): it is simpler than finding and refreshing every
icon, and a theme change is rare.

## Fonts

A `QFont` names a family and a size. Prefer **pixel size** (`setPixelSize`) for drawing that must line up with other geometry,
as the staff does, and point size for ordinary text. Fonts that ship with the program are loaded with
`QFontDatabase.addApplicationFont(path)`, which returns an id you can turn into the family name; this is how the music fonts in
`alto/assets/fonts` are used (see [Rendering music notation]({{ '/guide/notation/' | relative_url }})). Always give a fallback:
if a font is missing on the machine, Qt substitutes one silently.

## Visual design vocabulary

A few terms, so you can search for the right thing:

- **Elevation** is the impression that a surface sits above another; Alto fakes it with the heavier lower border on buttons.
  `QGraphicsDropShadowEffect` makes real shadows but costs performance on every repaint.
- **Affordance** is what a control's appearance says about what you can do with it. A raised button invites pressing.
- **Design tokens** are named values (a radius, a spacing, an accent colour) used everywhere instead of literals. `RADIUS` in
  `style.py` is one; changing it changes every corner.
- **Skeuomorphism and flat design** are the two ends of a style spectrum. Alto sits in the middle: flat, with small cues.
- **A spacing scale** (multiples of 4 or 8 pixels) keeps layouts feeling regular.

## The docs site

The website in `docs/` has its own theme in `docs/assets/css/site.css`, written with CSS **custom properties** (variables such
as `--fg` and `--accent`) that are redefined for dark mode, both from the operating system (`prefers-color-scheme`) and from a
toggle that sets `data-theme` on the page. The screenshots come in a light and a dark pair for the same reason. See
[For developers]({{ '/development/' | relative_url }}).

## A checklist for a new themed widget

1. Take every colour from the palette or from `blend` of palette colours.
2. Paint in `paintEvent`; change state, then call `update()`.
3. Set a correct `sizeHint`.
4. Look at it in both themes, with the screenshot script or by running the app and switching.
5. Add a test that grabs it (`widget.grab()`) and checks it is not blank, as `tests/test_rendering.py` does.

## Further reading

- The Qt documentation: "Qt Style Sheets" (including the Reference and the Examples, which show every widget), "QPalette",
  "QStyle", and "Styles and Style Aware Widgets", at doc.qt.io.
- *Web Content Accessibility Guidelines (WCAG) 2.1*, World Wide Web Consortium Recommendation, w3.org/TR/WCAG21: the
  "Contrast (Minimum)" criterion, 1.4.3, and "Use of Color", 1.4.1.
- Charles Poynton, *Digital Video and HD: Algorithms and Interfaces*, 2nd ed. (Morgan Kaufmann, 2012): gamma, luminance and
  colour spaces from the source.
- Cynthia A. Brewer, *Designing Better Maps: A Guide for GIS Users* (Esri Press, 2005): the thinking behind ColorBrewer.
- Edward R. Tufte, *The Visual Display of Quantitative Information*, 2nd ed. (Graphics Press, 2001): charts, ink and clutter.
- Donald A. Norman, *The Design of Everyday Things*, revised ed. (Basic Books, 2013): affordances and feedback.
- Ellen Lupton, *Thinking with Type*, 2nd ed. (Princeton Architectural Press, 2010): type for people who are not designers.
- Steve Krug, *Don't Make Me Think, Revisited* (New Riders, 2014): usability in short chapters.
- Apple, *Human Interface Guidelines*, and Google, *Material Design* guidelines: two worked-out design systems to learn from.
