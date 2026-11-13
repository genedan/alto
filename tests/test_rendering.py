"""Drawing: every staff, clef, note value and picture is painted at least once, and shows something."""

import pytest
from alto.theory.pitch import Note
from alto.ui import keyboard_styles, notation
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def dark_pixels(
    widget,
    size=(520, 220),
    step=2,
) -> int:
    """How many pixels of the widget are dark: a blank drawing has none."""
    widget.resize(*size)
    image: QImage = widget.grab().toImage()
    return sum(
        1
        for y in range(0, image.height(), step)
        for x in range(0, image.width(), step)
        if image.pixelColor(x, y).lightness() < 100
    )


# -- the staff ------------------------------------------------------------------------------------------------------

# ledger lines above and below, accidentals, and a chord
COLUMNS = [
    [Note(4, 0)],
    [Note(5, 4, 1)],
    [Note(3, 2, -1)],
    [Note(6, 0), Note(5, 5)],
    [Note(2, 6)],
]


@pytest.mark.parametrize("style", notation.STYLES, ids=lambda s: s.key)
def test_a_staff_is_drawn_in_every_notation_style(
    app,
    style,
):
    from alto.ui.staff import StaffWidget

    staff = StaffWidget()
    staff.notation_style = style
    for clef in (
        "treble",
        "bass",
        "alto",
        "tenor",
        "grand",
    ):
        for key in (0, 3, -4):
            staff.show_notes(
                COLUMNS,
                clef,
                key,
                "quarter",
            )
            assert dark_pixels(staff) > 300, (style.key, clef, key)


@pytest.mark.parametrize(
    "value",
    [
        "breve",
        "whole",
        "half",
        "quarter",
        "eighth",
        "sixteenth",
        "thirty_second",
    ],
)
def test_every_note_value_is_drawn(
    app,
    value,
):
    from alto.ui.staff import StaffWidget

    staff = StaffWidget()
    for style in notation.STYLES:
        staff.notation_style = style
        staff.show_notes(
            [[Note(4, 2)], [Note(4, 6)]],
            "treble",
            0,
            value,
        )
        assert dark_pixels(staff) > 300


def test_a_staff_can_colour_its_notes_and_follows_the_chosen_style(app):
    from alto.ui.staff import StaffWidget

    staff = StaffWidget()
    staff.show_notes(COLUMNS[:2], "treble")
    plain = dark_pixels(staff)
    from PySide6.QtGui import QColor

    staff.set_note_color(QColor("red"))
    assert staff.note_color is not None and dark_pixels(staff) < plain  # red is lighter than black
    staff.set_note_color(None)
    assert staff.note_color is None
    # with no style of its own the staff follows the style chosen in the settings
    notation.set_style("bravura")
    assert notation.current().key == "bravura" and dark_pixels(staff) > 300
    notation.set_style("no-such-style")
    assert notation.current().key == notation.DEFAULT


def test_the_chosen_style_is_remembered(app):
    notation.set_style("leland")
    notation.load_style()
    assert notation.current().key == "leland"
    from alto.ui.store import store

    store().setValue("ui/notation", "gone")
    notation.load_style()
    assert notation.current().key == notation.DEFAULT


def test_a_staff_without_the_music_font_still_draws_with_the_built_in_shapes(app):
    from alto.ui.staff import StaffWidget

    staff = StaffWidget()
    staff.notation_style = notation.BY_KEY["noto"]  # read from the system, so it has no SMuFL font here
    for clef in (
        "treble",
        "bass",
        "alto",
        "tenor",
        "grand",
    ):
        staff.show_notes(COLUMNS, clef, 2)
        assert dark_pixels(staff) > 300


def test_a_compact_staff_sizes_itself(app):
    from alto.ui.staff import StaffWidget

    small = StaffWidget(
        gap=6.5,
        side=8.0,
        note_offset=44.0,
        margin=3.2,
        compact=True,
    )
    small.show_notes([[Note(4, 2)]], "treble")
    one = small.height()
    small.show_notes([[Note(4, 2)]], "grand")
    assert small.height() > one


def test_note_shapes(app):
    from alto.ui import notes

    for value in (
        "breve",
        "whole",
        "half",
        "quarter",
        "eighth",
        "sixteenth",
        "thirty_second",
    ):
        up, down = notes.note_shape(value), notes.note_shape(value, stem_down=True)
        assert not up.isEmpty() and not down.isEmpty()
        assert up.boundingRect() != down.boundingRect() or value in ("breve", "whole")


# -- placing a note by clicking the staff ---------------------------------------------------------------------------


def test_clicking_the_staff_places_the_nearest_note(app):
    from alto.ui.staff import BOTTOM_LINE
    from alto.ui.staff_input import StaffInput

    staff = StaffInput()
    staff.resize(520, 260)
    staff.show()
    staff.reset("treble", key=1)
    placed = []
    staff.placed.connect(placed.append)
    bottom = staff.staff_bottoms()["treble"]
    y = bottom - (Note(5, 3).diatonic - BOTTOM_LINE["treble"]) * staff.GAP / 2  # the F above the staff
    QTest.mouseClick(staff, Qt.MouseButton.LeftButton, pos=QPoint(300, round(y)))
    assert placed == [Note(5, 3, 1)]  # F♯, because the key signature has one sharp
    staff.accidental = 0
    assert staff.note_at(y).accidental == 0  # an explicit natural overrides the key
    staff.hide()


def move(
    widget,
    x,
    y,
):
    """Move the pointer over the widget (sent as an event, so it does not depend on the real pointer)."""
    point = QPointF(x, y)
    QApplication.sendEvent(
        widget,
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            point,
            point,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


def test_the_staff_input_previews_and_locks(
    app,
    monkeypatch,
):
    from alto.ui.staff_input import StaffInput

    staff = StaffInput()
    staff.resize(520, 260)
    staff.reset("bass")
    move(staff, 250, 100)
    assert staff.columns and staff.note_color is not None  # the preview follows the pointer
    monkeypatch.setattr(staff, "underMouse", lambda: True)
    staff.accidental = 1
    staff.refresh_preview()  # e.g. after the accidental changes
    assert staff.columns[0][0].accidental == 1
    staff.leaveEvent(None)
    assert staff.columns == []
    staff.locked = True
    move(staff, 250, 110)
    QTest.mouseClick(staff, Qt.MouseButton.RightButton, pos=QPoint(250, 110))
    staff.refresh_preview()
    assert staff.columns == []  # a locked staff ignores the mouse
    staff.show_note(Note(3, 0))
    staff.leaveEvent(None)
    assert staff.columns != []  # and stays as it is when the pointer leaves
    staff.locked = False
    cycled = []
    staff.accidental_cycled.connect(lambda: cycled.append(1))
    QTest.mouseClick(staff, Qt.MouseButton.RightButton, pos=QPoint(250, 110))
    assert cycled == [1]


def test_the_grand_staff_input_splits_at_middle_c(app):
    from alto.ui.staff_input import StaffInput

    staff = StaffInput()
    staff.resize(520, 360)
    staff.reset("grand")
    bottoms = staff.staff_bottoms()
    assert staff.note_at(bottoms["treble"] - 4 * staff.GAP).diatonic >= Note(4, 0).diatonic
    assert staff.note_at(bottoms["bass"]).diatonic < Note(4, 0).diatonic
    assert staff.note_at(-5000).diatonic >= Note(4, 0).diatonic and staff.note_at(5000).diatonic < Note(4, 0).diatonic
    staff.show_note(Note(4, 0), None)
    assert dark_pixels(staff, (520, 360)) > 300


# -- the keyboard ---------------------------------------------------------------------------------------------------


def test_the_keyboard_highlights_a_key_and_changes_its_range(app):
    from alto.ui.keyboard import KeyboardWidget
    from PySide6.QtGui import QColor

    keyboard = KeyboardWidget()
    keyboard.resize(700, 140)
    for midi, span in (
        (60, (48, 72)),
        (61, (48, 72)),
        (21, None),
        (108, None),
        (None, (60, 72)),
    ):
        keyboard.show_key(midi, span)
        assert dark_pixels(keyboard, (700, 140)) > 200
    keyboard.max_key_width = 30.0
    keyboard.set_highlight_color(QColor("green"))
    keyboard.show_key(64, (55, 70))
    keyboard.resize(500, 140)
    assert dark_pixels(keyboard, (500, 140)) > 100


@pytest.mark.parametrize("style", [*keyboard_styles.STYLES, keyboard_styles.custom_style()], ids=lambda s: s.key)
def test_a_keyboard_is_drawn_in_every_style(
    app,
    style,
):
    from alto.ui.keyboard import KeyboardSpan, KeyboardWidget

    keyboard = KeyboardWidget()
    keyboard.style_override = style
    keyboard.show_key(64, (48, 77))  # a span that reaches below the organ's reversed octave, with sharps at both ends
    keyboard.resize(700, 200)
    assert dark_pixels(keyboard, (700, 200)) > 100
    assert keyboard.height() >= 2 * keyboard.pad + style.rail  # the strip above the keys is allowed for
    keyboard_styles.set_style(style.key)
    span = KeyboardSpan()
    span.set_span(48, 72)
    assert dark_pixels(span, (500, 64)) > 20


def test_choosing_a_keyboard_style_is_saved_and_redraws_open_keyboards(app):
    from alto.ui.keyboard import KeyboardSpan, KeyboardWidget
    from alto.ui.store import store

    span = KeyboardSpan()  # redrawn too, though its size does not change
    keyboard = KeyboardWidget()
    keyboard.resize(600, 300)
    flat = keyboard.height()
    keyboard_styles.set_style("organ")  # a taller strip above the keys
    assert keyboard_styles.current().key == "organ" and store().value("ui/keyboard") == "organ"
    assert keyboard.height() > flat
    assert span.lo <= span.hi  # the miniature is still there, redrawn in the new style
    keyboard_styles.set_style("no-such-style")
    assert keyboard_styles.current().key == keyboard_styles.DEFAULT
    keyboard_styles.set_style("neon")
    keyboard_styles._current = keyboard_styles.BY_KEY["classic"]
    keyboard_styles.load_style()
    assert keyboard_styles.current().key == "neon"
    store().setValue("ui/keyboard", "gone")
    keyboard_styles.load_style()
    assert keyboard_styles.current().key == keyboard_styles.DEFAULT


def test_custom_keyboard_colours_are_saved_loaded_and_checked(app):
    from alto.ui.store import store

    keyboard_styles.set_custom_colour("naturals", "#ead9aa")
    keyboard_styles.set_custom_colour("case", None)
    keyboard_styles.set_custom_colour("caps", "#eee3c8")
    style = keyboard_styles.current()
    assert style.key == "custom" and style.white[0] == "#ead9aa" and style.case is None and style.cap == "#eee3c8"
    assert style.rail == 4.0  # no case and no felt: a thin strip
    assert keyboard_styles.custom_style().rail == 4.0
    keyboard_styles.set_custom_colour("felt", "#7d1f27")
    assert keyboard_styles.custom_style().rail == 8.0
    keyboard_styles._custom.update(keyboard_styles.DEFAULT_CUSTOM)
    keyboard_styles.load_style()  # what was saved comes back
    assert keyboard_styles.custom_colours()["naturals"] == "#ead9aa" and keyboard_styles.custom_colours()["case"] is None
    assert keyboard_styles.current().key == "custom"
    store().setValue("ui/keyboardCustom/naturals", "not a colour")
    keyboard_styles.load_style()  # a bad value falls back to the default
    assert keyboard_styles.custom_colours()["naturals"] == keyboard_styles.DEFAULT_CUSTOM["naturals"]


def test_a_keyboard_span_shows_the_range_in_miniature(app):
    from alto.ui.keyboard import KeyboardSpan

    for compact in (False, True):
        span = KeyboardSpan(compact=compact)
        span.set_span(48, 72)
        assert dark_pixels(span, span.size().toTuple()) > 20
        span.set_span(21, 108)
        span.update()


def test_a_keyboard_span_is_chosen_by_dragging_its_edges_or_the_whole(app):
    from alto.ui.keyboard import KeyboardSpan
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    span = KeyboardSpan()
    span.resize(880, 64)
    span.set_span(48, 72)
    heard: list[tuple[int, int]] = []
    span.dragged.connect(lambda lo, hi: (heard.append((lo, hi)), span.set_span(lo, hi)))

    def send(
        kind,
        x,
        y=50.0,
        button=Qt.MouseButton.LeftButton,
    ):
        pos = QPointF(x, y)
        event = QMouseEvent(
            kind,
            pos,
            span.mapToGlobal(pos),
            button,
            button,
            Qt.KeyboardModifier.NoModifier,
        )
        {
            QEvent.Type.MouseButtonPress: span.mousePressEvent,
            QEvent.Type.MouseMove: span.mouseMoveEvent,
            QEvent.Type.MouseButtonRelease: span.mouseReleaseEvent,
        }[kind](event)

    def x_of(midi):  # the middle of a white key
        whites = [
            m
            for m in range(21, 109)
            if m % 12
            in (
                0,
                2,
                4,
                5,
                7,
                9,
                11,
            )
        ]
        return 4 + (whites.index(midi) + 0.5) * (880 - 8) / len(whites)

    left, right = span._edges()
    cursors = {}
    for name, x in (
        ("lo", left),
        ("hi", right),
        ("pan", (left + right) / 2),
        ("new", 20.0),
    ):
        send(QEvent.Type.MouseMove, x)  # hovering shows what a press would do
        cursors[name] = span.cursor().shape()
    assert cursors["lo"] == cursors["hi"] == Qt.CursorShape.SizeHorCursor
    assert cursors["pan"] == Qt.CursorShape.OpenHandCursor and cursors["new"] == Qt.CursorShape.PointingHandCursor
    assert heard == []

    send(QEvent.Type.MouseButtonPress, 4, button=Qt.MouseButton.RightButton)
    assert heard == []

    send(QEvent.Type.MouseButtonPress, left + 1)  # the low edge moves alone, and cannot pass the high one
    send(QEvent.Type.MouseMove, x_of(43))
    assert heard[-1] == (43, 72)
    send(QEvent.Type.MouseMove, x_of(91))
    assert heard[-1] == (72, 72)
    send(QEvent.Type.MouseButtonRelease, x_of(91))
    span.set_span(48, 72)
    left, right = span._edges()

    send(QEvent.Type.MouseButtonPress, right - 1)  # the high edge likewise
    send(QEvent.Type.MouseMove, x_of(79))
    assert heard[-1] == (48, 79)
    send(QEvent.Type.MouseMove, x_of(31))
    assert heard[-1] == (48, 48)
    send(QEvent.Type.MouseButtonRelease, 0)
    span.set_span(48, 72)

    send(QEvent.Type.MouseButtonPress, x_of(60))  # the middle pans: same size, following the pointer
    send(QEvent.Type.MouseMove, x_of(64))
    assert heard[-1] == (52, 76)
    send(QEvent.Type.MouseMove, x_of(101))
    assert heard[-1] == (108 - 24, 108)  # stops at the top of the piano
    send(QEvent.Type.MouseMove, -50)
    assert heard[-1] == (21, 45)
    send(QEvent.Type.MouseButtonRelease, 0)
    count = len(heard)
    send(QEvent.Type.MouseMove, 400)  # released: moving only changes the cursor
    assert len(heard) == count

    span.set_span(48, 72)
    send(QEvent.Type.MouseButtonPress, x_of(31))  # pressing outside starts a new span
    assert heard[-1] == (31, 31)
    send(QEvent.Type.MouseMove, x_of(36))
    assert heard[-1] == (31, 36)
    send(QEvent.Type.MouseMove, x_of(24))
    assert heard[-1] == (24, 31)
    send(QEvent.Type.MouseButtonRelease, 0)

    # a black key is found in the upper part where it is drawn, and the white key beneath it lower down
    black = span.key_at(QPointF(4 + 1 * (880 - 8) / 52, 5))
    assert black == 22  # the key between the first two whites, A0 and B0, is A sharp 0
    assert span.key_at(QPointF(4 + 1 * (880 - 8) / 52, 60)) in (21, 23)
    span.set_span(22, 70)  # a span that starts and ends on black keys still has handles
    assert span._edges()[0] < span._edges()[1]


# -- the little pictures in the settings ----------------------------------------------------------------------------


def test_the_settings_pictures_draw_and_make_icons(app):
    from alto.ui import pictures

    clefs = pictures.ClefPictures(
        [
            "treble",
            "bass",
            "alto",
            "tenor",
            "grand",
        ],
    )
    clefs.set_clefs(["grand"])
    values = pictures.ValuePictures(
        [
            "whole",
            "quarter",
            "eighth",
            "breve",
        ],
        centre_stemless=True,
    )
    values.set_values(["half", "sixteenth", "thirty_second"])
    keys = [
        pictures.KeySignaturePicture(k)
        for k in (
            0,
            1,
            7,
            -1,
            -7,
        )
    ]
    ranges = pictures.RangePictures(
        [
            ("treble", 28, 41),
            ("bass", 16, 29),
            ("grand", 14, 42),
            ("alto", 21, 35),
            ("tenor", 19, 33),
        ],
    )
    assert dark_pixels(ranges, ranges.sizeHint().toTuple(), step=1) > 0
    ranges.set_items([("treble", 20, 45), ("bass", 10, 16), ("alto", 31, 35)])  # below, above and inside the staff
    names = pictures.NamePicture("letters")
    names.set_naming("solfege")
    for widget in (
        clefs,
        values,
        *keys,
        ranges,
        names,
    ):
        widget.resize(widget.sizeHint())
        assert dark_pixels(widget, widget.size().toTuple(), step=1) > 0, type(widget).__name__
    for icon in (
        pictures.ClefPictures.icon("treble"),
        pictures.ValuePictures.icon("quarter"),
        pictures.KeySignaturePicture.icon(3),
        pictures.NamePicture.icon("letters"),
    ):
        assert not icon.isNull()
    assert not pictures.ClefPictures(["alto"]).to_icon().isNull()


# -- theme, settings storage and the small widgets ------------------------------------------------------------------


def test_the_range_picture_shrinks_to_fit_and_the_key_signature_picture_draws_without_a_font(app):
    from alto.ui import pictures

    ranges = pictures.RangePictures([("treble", 28, 41)] * 5, max_width=120)
    assert ranges.scale < 1.0 and "Treble: C4 to " in ranges.toolTip()
    notation.set_style("noto")  # a style with no SMuFL font: the signs are the built-in characters
    for key in (0, 2, -2):
        picture = pictures.KeySignaturePicture(key)
        assert dark_pixels(picture, picture.sizeHint().toTuple(), step=1) > 0


def test_a_keyboard_with_no_width_or_no_white_keys_draws_nothing_and_does_not_fail(app):
    from alto.ui.keyboard import KeyboardWidget

    keyboard = KeyboardWidget()
    keyboard.resize(0, 0)
    assert keyboard._key_width() == keyboard.max_key_width
    keyboard.show_key(None, (49, 73))  # both ends are black keys, so the range is widened to the white keys beside them
    assert (keyboard.lo, keyboard.hi) == (48, 74)
    keyboard.lo = keyboard.hi = 61  # a black key on its own: no white keys to draw
    keyboard.resize(300, 100)
    assert dark_pixels(keyboard, (300, 100)) == 0


def test_the_theme_is_saved_and_applied(app):
    from alto.ui import theme
    from alto.ui.style import app_style

    assert theme.saved_theme() == "system"
    theme.save_theme("dark")
    assert theme.saved_theme() == "dark"
    theme.save_theme("nonsense")
    assert theme.saved_theme() == "system"  # an unknown choice falls back
    for key, _label in theme.THEMES:
        theme.apply_theme(key)
        assert app.styleSheet() == app_style(app.palette())
    theme.apply_theme("system")


def test_the_settings_store_brings_over_the_old_names_once(app):
    from alto.ui.store import int_value, store
    from PySide6.QtCore import QSettings

    old = QSettings("mtheory", "mtheory")
    old.setValue("ui/theme", "light")
    old.sync()
    saved = store()
    assert saved.value("ui/theme") == "light" and saved.value("migratedFromMtheory") in (True, "true")
    old.clear()
    old.sync()
    saved.setValue("number", "42")
    assert int_value(saved, "number", 7) == 42 and int_value(saved, "missing", 7) == 7
    saved.setValue("text", "abc")
    with pytest.raises(ValueError):
        int_value(saved, "text", 7)
    saved.setValue("list", ["a"])
    assert int_value(saved, "list", 5) == 5  # not a number at all: the default


def test_the_sidebar_button_and_help_button(app):
    from alto.ui.widgets import HelpButton, SidebarToggle

    toggle = SidebarToggle()
    assert toggle.toolTip() == "Hide exercise list"
    toggle.set_open(False)
    assert toggle.toolTip() == "Show exercise list"

    texts = iter(["<b>First</b>", "<b>Second</b>"])
    button = HelpButton(lambda: next(texts))
    button.show()
    button.click()
    popup = button._popup
    assert popup is not None and popup.isVisible()
    popup.close()
    button.click()  # the text is asked for again each time, so it can follow the settings
    second = button._popup
    assert second is not None and second is not popup
    second.close()
    button.hide()


# -- a staff with few notes does not stretch across a wide window ----------------------------------------------------


def test_a_capped_staff_gets_a_share_of_width_for_each_column_of_notes(app):
    from alto.ui.staff import KEY_STEP, MAX_STEP, MIN_COLUMNS, StaffWidget

    staff = StaffWidget(max_step=MAX_STEP)
    staff.show_notes([[Note(4, 0)]], "treble")
    one = staff.maximumWidth()
    assert one == round(2 * staff.side + staff.note_offset + MIN_COLUMNS * MAX_STEP) and staff.sizeHint().width() == one
    staff.show_notes([[Note(4, i)] for i in range(7)], "treble")
    assert staff.maximumWidth() == one + round((7 - MIN_COLUMNS) * MAX_STEP)  # more notes, more room
    staff.show_notes([[Note(4, 0)]], "treble", key=7)
    assert staff.maximumWidth() == one + round(7 * KEY_STEP)  # the key signature needs room too
    staff.show_notes([[Note(4, 0)]], "grand")
    assert staff.maximumWidth() == one + 18  # and so does the brace of a grand staff
    staff.show_notes([], "treble")
    assert staff.maximumWidth() == one  # an empty staff (just a clef and a key signature) is the narrowest it gets


def test_a_staff_without_a_cap_is_left_as_it_was(app):
    from alto.ui.staff import StaffWidget

    staff = StaffWidget()
    staff.show_notes([[Note(4, 0)]], "treble")
    assert staff.maximumWidth() == 16777215 and staff.max_step is None
    small = StaffWidget(
        gap=6.5,
        side=8.0,
        note_offset=44.0,
        margin=3.2,
        compact=True,
    )
    small.setFixedWidth(214)
    small.show_notes([[Note(4, 0)]], "treble")
    assert small.maximumWidth() == 214  # the small previews in the settings keep their fixed width


def test_a_capped_staff_in_a_narrow_space_shrinks_to_fit_and_in_a_wide_one_is_centred(app):
    from alto.ui.staff import MAX_STEP, StaffWidget
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    holder = QWidget()
    lay = QVBoxLayout(holder)
    lay.setContentsMargins(
        0,
        0,
        0,
        0,
    )
    staff = StaffWidget(max_step=MAX_STEP)
    lay.addWidget(staff, alignment=Qt.AlignmentFlag.AlignHCenter)
    staff.show_notes([[Note(4, 0)]], "treble")
    holder.show()
    holder.resize(300, 300)
    QTest.qWait(30)
    assert staff.width() == 300 < staff.maximumWidth()  # not wide enough for the cap: the staff takes all there is
    holder.resize(1600, 300)
    QTest.qWait(30)
    assert staff.width() == staff.maximumWidth() and abs(staff.x() - (1600 - staff.width()) // 2) <= 1
    holder.hide()
