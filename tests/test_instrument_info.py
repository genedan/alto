from alto.audio import INSTRUMENTS
from alto.instrument_info import INFO, coverage


def test_every_instrument_has_a_summary_with_a_source_and_terms():
    assert {i.key for i in INSTRUMENTS} == set(INFO)
    for key, info in INFO.items():
        assert info.summary and info.source and info.terms, key
        assert info.source_url.startswith("https://"), key


def test_the_recordings_that_ship_say_who_played_them():
    for key in (
        "piano",
        "viola_bowed",
        "viola_plucked",
        "marimba",
        "vibraphone",
    ):
        assert INFO[key].performer and INFO[key].recorded, key


def test_nothing_installed():
    c = coverage([])
    assert not c.installed and c.describe() == "None installed"


def test_every_semitone_is_described_as_such():
    c = coverage(range(36, 97))
    assert (
        c.count,
        c.lowest,
        c.highest,
        c.gaps,
    ) == (
        61,
        36,
        96,
        0,
    )
    assert c.describe() == "61 notes, C2 to C7, every semitone"


def test_a_single_missing_note_is_almost_every_semitone():
    c = coverage([m for m in range(48, 94) if m != 51])
    assert c.gaps == 1
    assert "almost every semitone" in c.describe() and "C3 to A6" in c.describe()


def test_every_second_semitone_is_described_as_such():
    c = coverage(range(48, 92, 2))
    assert "about every second semitone" in c.describe()
