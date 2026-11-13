"""
Choosing the instrument that plays notes, with a summary of what each one is made from.

Examples
--------
>>> format_size(2_500_000)
'2.5 MB'
>>> sorted(PREVIEW)
[60, 64, 67]
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..audio import INSTRUMENT_BY_KEY, Instrument, instrument_groups, sounds
from ..instrument_info import FAMILY_SUMMARY, INFO, coverage
from .colors import blend_name
from .store import store

PREVIEW = (60, 64, 67)  # a C major arpeggio, to hear an instrument


def load_instrument() -> None:
    """
    Apply the saved instrument.

    The piano is used if nothing is saved or the saved key is not an instrument.

    Examples
    --------
    >>> store().setValue("audio/instrument", "flute")
    >>> load_instrument()
    >>> sounds.instrument
    'flute'
    >>> store().setValue("audio/instrument", "not an instrument")
    >>> load_instrument()
    >>> sounds.instrument
    'piano'
    """
    key = str(store().value("audio/instrument", "piano"))
    sounds.instrument = key if key in INSTRUMENT_BY_KEY else "piano"


def save_instrument() -> None:
    """
    Remember the instrument in use.

    Examples
    --------
    >>> sounds.instrument = "marimba"
    >>> save_instrument()
    >>> str(store().value("audio/instrument"))
    'marimba'
    >>> sounds.instrument = "piano"
    >>> save_instrument()
    """
    store().setValue("audio/instrument", sounds.instrument)


def tokens(widget: QWidget) -> dict[str, str]:
    """
    Return the summary page's colours.

    All are mixed from the system palette so they follow its light or dark theme.

    Parameters
    ----------
    widget : QWidget
        The widget whose palette to use.

    Returns
    -------
    dict of str to str
        Colour name to '#rrggbb': accent, accent_soft, muted, line, panel and well, and for each of good, warn and bad a
        text colour and a soft background (such as good and good_soft).

    Examples
    --------
    >>> colours = tokens(QWidget())
    >>> sorted(colours)[:3]
    ['accent', 'accent_soft', 'bad']
    >>> colours["panel"].startswith("#")
    True
    """
    pal = widget.palette()
    base, text = pal.color(QPalette.ColorRole.Base), pal.color(QPalette.ColorRole.Text)
    accent = pal.color(QPalette.ColorRole.Highlight)
    window = pal.color(QPalette.ColorRole.Window)
    out = dict(
        accent=blend_name(accent, b=text, t=0.35),  # as text, a little towards the text colour so it reads on either theme
        accent_soft=blend_name(base, b=accent, t=0.18),
        muted=blend_name(text, b=base, t=0.42),
        line=pal.color(QPalette.ColorRole.Mid).name(),
        panel=base.name(),
        well=blend_name(window, b=text, t=0.05),
    )
    for kind, hue in (("good", QColor("#2e9e50")), ("warn", QColor("#d08a00")), ("bad", QColor("#d64a37"))):
        out[kind] = blend_name(text, b=hue, t=0.65)  # the text colour leaning towards the hue, so it stays readable
        out[kind + "_soft"] = blend_name(base, b=hue, t=0.16)
    return out


def format_size(nbytes: int) -> str:
    """
    Write a file size the way the instrument page shows it.

    Parameters
    ----------
    nbytes : int
        The size in bytes.

    Returns
    -------
    str
        Megabytes with one decimal from a million bytes, otherwise whole kilobytes (at least 1).

    Examples
    --------
    >>> format_size(2_500_000), format_size(500_000), format_size(10)
    ('2.5 MB', '500 KB', '1 KB')
    """
    return f"{nbytes / 1e6:.1f} MB" if nbytes >= 1e6 else f"{max(nbytes // 1000, 1)} KB"


class InstrumentPicker(QWidget):
    """
    The instruments in a box on the left; on the right, what the selected one is made from.

    An instrument that can be played in more than one way (the viola, arco or pizzicato) is one entry, and its page has a
    'Use this instrument' and a 'Hear it' for each way. 'Hear it' plays a short arpeggio even while sound is muted.

    Attributes
    ----------
    chosen : Signal
        Emitted with the key of the instrument that is now in use.
    groups : dict of str to list of Instrument
        The entries in the list, each with the instruments (ways of playing) it holds.
    list : QListWidget
        The box of entries.
    shown : str or None
        The entry whose page is showing.

    Examples
    --------
    >>> picker = InstrumentPicker()
    >>> picker.select("viola_plucked")
    >>> picker.shown
    'Viola'
    """

    chosen = Signal(str)  # the key of the instrument now in use

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Build the picker, showing the page of the instrument in use.

        Parameters
        ----------
        parent : QWidget or None, default None
            The widget that owns the picker.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> picker.list.count() == len(picker.groups)
        True
        """
        super().__init__(parent)
        self.list = QListWidget()
        self.list.setObjectName("categories")  # the rounded list used for the settings categories
        self.list.setFixedWidth(220)
        self.list.setStyleSheet("")  # set when shown, from the palette
        self.groups = dict(instrument_groups())  # list entry -> the ways of playing it
        for name in self.groups:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setSizeHint(QSize(0, 34))
            self.list.addItem(item)
        self.list.currentItemChanged.connect(lambda cur, _prev: cur and self.show_group(cur.data(Qt.ItemDataRole.UserRole)))
        self.list.itemDoubleClicked.connect(lambda item: self.use(self._default_key(item.data(Qt.ItemDataRole.UserRole))))

        # The summary page.
        self.title = QLabel()
        title_font = QFont(self.font())
        title_font.setPointSizeF(title_font.pointSizeF() * 1.5)
        title_font.setBold(True)
        self.title.setFont(title_font)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setObjectName("banner")
        self.facts = QGridLayout()
        self.facts.setHorizontalSpacing(16)
        self.facts.setVerticalSpacing(8)
        self.facts.setColumnStretch(1, 1)
        self.action_rows = QVBoxLayout()  # one row of buttons for each way of playing the instrument
        self.action_rows.setSpacing(8)
        self.buttons: dict[str, tuple[QPushButton, QPushButton]] = {}  # instrument key -> (use, hear)

        page = QWidget()
        page.setObjectName("instrumentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(
            18,
            16,
            12,
            10,
        )
        lay.setSpacing(10)
        lay.addWidget(self.title)
        lay.addLayout(self.chips)
        lay.addWidget(self.summary)
        lay.addWidget(self.banner)
        lay.addLayout(self.facts)
        lay.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        scroll.setStyleSheet("QScrollArea, QWidget#instrumentPage { background: transparent; }")
        self.divider = QFrame()
        self.divider.setFixedHeight(1)

        self.card = card = QFrame()  # the summary sits in a card; the buttons stay in view below the scrolling details
        card.setObjectName("helpCard")
        right = QVBoxLayout(card)
        right.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        right.setSpacing(0)
        right.addWidget(scroll, 1)
        right.addWidget(self.divider)
        bar = QWidget()
        bar.setLayout(self.action_rows)
        self.action_rows.setContentsMargins(
            18,
            12,
            18,
            14,
        )
        right.addWidget(bar)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.setSpacing(14)
        outer.addWidget(self.list)
        outer.addWidget(card, 1)

        self.shown = ""  # the list entry whose page is showing
        self._mark_in_use()
        self.select(sounds.instrument)

    # -- the list --------------------------------------------------------------------------------------------------

    @staticmethod
    def _group_of(key: str) -> str:
        """
        Return the list entry an instrument belongs to.

        Parameters
        ----------
        key : str
            An instrument's key.

        Returns
        -------
        str
            Its family (for the viola, 'Viola') or its own name.

        Examples
        --------
        >>> InstrumentPicker._group_of("viola_bowed"), InstrumentPicker._group_of("flute")
        ('Viola', 'Flute')
        """
        inst = INSTRUMENT_BY_KEY[key]
        return inst.family or inst.label

    def _default_key(self, group: str) -> str:
        """
        Return which way of playing a double-click on an entry uses.

        Parameters
        ----------
        group : str
            An entry in the list.

        Returns
        -------
        str
            The instrument in use if it is one of the entry's, otherwise the entry's first.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> sounds.instrument = "piano"
        >>> picker._default_key("Viola")
        'viola_bowed'
        """
        members = self.groups[group]
        return next((i.key for i in members if i.key == sounds.instrument), members[0].key)

    def select(self, key: str) -> None:
        """
        Show the page of the entry an instrument belongs to.

        Parameters
        ----------
        key : str
            An instrument's key.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> picker.select("marimba")
        >>> picker.shown
        'Marimba'
        """
        group = self._group_of(key)
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole) == group:
                self.list.setCurrentRow(row)
                break
        self.show_group(group)

    def _mark_in_use(self) -> None:
        """
        Mark the entry in use in the list.

        It is shown bold and ticked (saying which way of playing, if there are several), and the entries with no recordings
        installed are put in italics.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> sounds.instrument = "piano"
        >>> picker._mark_in_use()
        >>> picker.list.item(0).data(Qt.ItemDataRole.UserRole), picker.list.item(0).font().bold()
        ('Piano', True)
        """
        for row in range(self.list.count()):
            item = self.list.item(row)
            group = item.data(Qt.ItemDataRole.UserRole)
            members = self.groups[group]
            active = next((i for i in members if i.key == sounds.instrument), None)
            if active is None:
                text = group
            else:
                text = f"{group} ({active.variant})  ✓" if active.variant else f"{group}  ✓"
            item.setText(text)
            installed = any(coverage(sounds.recordings(i)).installed for i in members)
            font = item.font()
            font.setBold(active is not None)
            font.setItalic(not installed)  # the list's stylesheet fixes the colour, so italics mark what is missing
            item.setFont(font)
            item.setToolTip("" if installed else "No recordings are installed for this instrument")

    # -- the summary page ------------------------------------------------------------------------------------------

    @staticmethod
    def _clear(layout: QLayout) -> None:
        """
        Remove everything from a layout at once.

        None of it is left drawn under what replaces it.

        Parameters
        ----------
        layout : QLayout
            The layout to empty, including the layouts inside it.

        Examples
        --------
        >>> layout = QVBoxLayout()
        >>> layout.addWidget(QLabel("one"))
        >>> InstrumentPicker._clear(layout)
        >>> layout.count()
        0
        """
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                break
            widget, inner = item.widget(), item.layout()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif inner is not None:
                InstrumentPicker._clear(inner)

    def _chip(
        self,
        text: str,
        *,
        kind: str = "",
    ) -> QLabel:
        """
        Make a small rounded tag.

        Parameters
        ----------
        text : str
            What the tag says.
        kind : str, default ""
            "accent", "good", "warn" or "bad" for a coloured one, or empty for a plain outlined one. Keyword-only.

        Returns
        -------
        QLabel
            The tag.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> chip = picker._chip("In use", kind="good")
        >>> chip.text()
        'In use'
        """
        t = tokens(self)
        chip = QLabel(text)
        if kind:
            colours = f"color: {t[kind]}; background: {t[kind + '_soft']}; border: 1px solid transparent; font-weight: 600;"
        else:
            colours = f"color: {t['muted']}; background: transparent; border: 1px solid {t['line']};"
        chip.setStyleSheet(colours + " border-radius: 10px; padding: 2px 10px;")
        return chip

    def _link(
        self,
        url: str,
        *,
        text: str,
    ) -> str:
        """
        Return a link as HTML, in the accent colour.

        Parameters
        ----------
        url : str
            Where it goes.
        text : str
            What it says. Keyword-only.

        Returns
        -------
        str
            An `<a>` element.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> picker._link("https://example.org", text="Source").startswith('<a href="https://example.org">')
        True
        """
        return f'<a href="{url}"><span style="color: {tokens(self)["accent"]};">{text}</span></a>'

    def _fact(
        self,
        row: int,
        *,
        label: str,
        value: str,
        link: bool = False,
    ) -> None:
        """
        Add a labelled line to the facts grid on the summary page.

        Parameters
        ----------
        row : int
            The grid row.
        label : str
            The name of the fact, such as "Performer". Keyword-only.
        value : str
            Its value. Keyword-only.
        link : bool, default False
            Treat the value as HTML, so links in it can be clicked. Keyword-only.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> before = picker.facts.count()
        >>> picker._fact(99, label="Performer", value="Someone")
        >>> picker.facts.count() - before  # a label and its value
        2
        """
        name = QLabel(label)
        name.setStyleSheet(f"color: {tokens(self)['muted']};")
        name.setFixedWidth(84)
        name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text = QLabel(value)
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.RichText if link else Qt.TextFormat.PlainText)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        text.setOpenExternalLinks(True)
        self.facts.addWidget(
            name,
            row,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        self.facts.addWidget(text, row, 1)

    @staticmethod
    def _per_way(
        members: list[Instrument],
        *,
        values: list[str],
    ) -> str:
        r"""
        Say a fact about each way of playing, or once if they agree.

        Parameters
        ----------
        members : list of Instrument
            The ways of playing an instrument.
        values : list of str
            The fact for each, in the same order; an empty string for none. Keyword-only.

        Returns
        -------
        str
            One value if the ways agree, otherwise a line for each, led by its name.

        Examples
        --------
        >>> viola = dict(instrument_groups())["Viola"]
        >>> InstrumentPicker._per_way(viola, values=["Bowed", "Bowed"])
        'Bowed'
        >>> InstrumentPicker._per_way(viola, values=["Bowed", "Plucked"])
        'Arco: Bowed\nPizzicato: Plucked'
        """
        shown = [(m, v) for m, v in zip(members, values) if v]
        if not shown:
            return ""
        if len({v for _, v in shown}) == 1 and len(shown) == len(members):
            return shown[0][1]
        return "\n".join(f"{m.variant}: {v}" for m, v in shown)

    def show_group(self, group: str) -> None:
        """
        Fill the summary page for an entry from what is known about it and what is on disk.

        Parameters
        ----------
        group : str
            An entry in the list, such as "Flute" or "Viola".

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> picker.show_group("Flute")
        >>> picker.shown
        'Flute'
        """
        self.shown = group
        members = self.groups[group]
        many = len(members) > 1
        infos = [INFO[m.key] for m in members]
        have = [coverage(sounds.recordings(m)) for m in members]
        files = [sounds.recordings(m) for m in members]
        t = tokens(self)
        self.title.setText(group)
        self.card.setStyleSheet(f"QFrame#helpCard {{ background: {t['panel']}; border: 1px solid {t['line']}; }}")
        self.list.setStyleSheet(f"QListWidget#categories {{ background: {t['well']}; }}")  # a shade apart from the card
        self.divider.setStyleSheet(f"background: {t['line']};")
        self.summary.setStyleSheet(f"color: {t['muted']};")
        self.banner.setStyleSheet(f"color: {t['bad']}; background: {t['bad_soft']}; border-radius: 8px; padding: 8px 12px;")
        self.summary.setText(FAMILY_SUMMARY.get(group, infos[0].summary) if many else infos[0].summary)

        # The chips: what is in use, what is installed, how notes behave.
        self._clear(self.chips)
        active = next((m for m in members if m.key == sounds.instrument), None)
        if active is not None:
            self.chips.addWidget(self._chip(f"In use: {active.variant}" if many else "In use", kind="accent"))
        installed = [h.installed for h in have]
        state = "Installed" if all(installed) else "Not installed" if not any(installed) else "Partly installed"
        self.chips.addWidget(
            self._chip(state, kind="good" if state == "Installed" else "bad" if state == "Not installed" else "warn"),
        )
        if len({m.sustained for m in members}) == 1:
            self.chips.addWidget(self._chip("Each note ends as the next begins" if members[0].sustained else "Notes ring on"))
        self.chips.addStretch(1)

        missing = [m for m, h in zip(members, have) if not h.installed]
        if missing:
            which = group if len(missing) == len(members) else " and ".join(m.variant for m in missing)
            self.banner.setText(
                f"No recordings are installed for {which} in this copy of Alto, so it would play as the "
                "synthesized piano. It is listed so you can see what it is made from.",
            )
        self.banner.setVisible(bool(missing))

        # The facts. What all the ways of playing share is shown once; what differs is shown for each.
        self._clear(self.facts)
        urls = {i.source_url for i in infos}
        source = (
            self._link(infos[0].source_url, text=infos[0].source)
            if len(urls) == 1
            else "<br>".join(f"{m.variant}: {self._link(i.source_url, text=i.source)}" for m, i in zip(members, infos))
        )
        rows = [
            ("Source", source, True),
            ("Performer", self._per_way(members, values=[i.performer for i in infos]), False),
            ("Recorded", self._per_way(members, values=[i.recorded for i in infos]), False),
            ("Includes", self._per_way(members, values=[i.includes for i in infos]), False),
            ("Notes", self._per_way(members, values=[h.describe() for h in have]), False),
            (
                "Size",
                self._per_way(
                    members,
                    values=[
                        format_size(sum(p.stat().st_size for p in f.values())) if h.installed else "" for f, h in zip(files, have)
                    ],
                ),
                False,
            ),
            ("Terms", self._per_way(members, values=[i.terms for i in infos]), False),
            ("About", self._per_way(members, values=[i.note for i in infos]), False),
        ]
        for row, (label, value, link) in enumerate(r for r in rows if r[1]):
            self._fact(
                row,
                label=label,
                value=value,
                link=link,
            )

        # One row of buttons for each way of playing the instrument.
        self._clear(self.action_rows)
        self.buttons = {}
        for m, h in zip(members, have):
            suffix = f" ({m.variant})" if many else ""
            in_use = m.key == sounds.instrument
            use = QPushButton(
                f"In use{suffix}" if in_use else f"Use this instrument{suffix}" if h.installed else f"Not installed{suffix}",
            )
            use.setEnabled(h.installed and not in_use)
            if in_use:
                use.setStyleSheet(
                    f"QPushButton:disabled {{ background: {t['accent_soft']}; color: {t['accent']}; "
                    f"border-color: {t['accent_soft']}; }}",
                )
            use.clicked.connect(lambda _=False, k=m.key: self.use(k))
            hear = QPushButton("▶  Hear it")
            hear.setEnabled(h.installed)
            hear.clicked.connect(lambda _=False, k=m.key: self.preview(k))
            row = QHBoxLayout()
            row.addWidget(use)
            row.addWidget(hear)
            row.addStretch(1)
            self.action_rows.addLayout(row)
            self.buttons[m.key] = (use, hear)

    def changeEvent(self, event: QEvent) -> None:
        """
        Redraw the summary page when the palette changes, so its colours follow the theme.

        Parameters
        ----------
        event : QEvent
            The change.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> picker.show_group("Flute")
        >>> picker.changeEvent(QEvent(QEvent.Type.PaletteChange))
        >>> picker.shown
        'Flute'
        """
        if event.type() == QEvent.Type.PaletteChange and self.shown:
            self.show_group(self.shown)
        super().changeEvent(event)

    # -- actions ---------------------------------------------------------------------------------------------------

    def use(self, key: str) -> None:
        """
        Make an instrument the one for notes and the correct-answer chime.

        Nothing happens if it has no recordings installed.

        Parameters
        ----------
        key : str
            The instrument's key.

        Examples
        --------
        >>> picker = InstrumentPicker()
        >>> chosen = []
        >>> _ = picker.chosen.connect(chosen.append)
        >>> picker.use("marimba")
        >>> sounds.instrument, chosen
        ('marimba', ['marimba'])
        >>> picker.use("piano")
        """
        if not coverage(sounds.recordings(INSTRUMENT_BY_KEY[key])).installed:
            return
        sounds.instrument = key
        save_instrument()
        self._mark_in_use()
        self.show_group(self._group_of(key))
        self.chosen.emit(key)

    def preview(self, key: str) -> None:
        """
        Play a short C major arpeggio in an instrument, even if sound is muted.

        Parameters
        ----------
        key : str
            The instrument's key.

        Examples
        --------
        >>> InstrumentPicker().preview("flute")  # doctest: +SKIP
        """
        sounds.preview(key, midis=PREVIEW)
