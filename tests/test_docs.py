"""The docs and their screenshots stay in step: every picture a page shows exists in both themes, and each one can be
regenerated with scripts/screenshots.py."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "assets" / "img"


def script():
    spec = importlib.util.spec_from_file_location("screenshots", ROOT / "scripts" / "screenshots.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # only defines things; the work happens under __main__
    return module


def shown() -> set[str]:
    """The picture names the docs pages include with shot.html, without the .png."""
    found = set()
    for page in (ROOT / "docs").glob("*.md"):
        found |= set(re.findall(r'shot\.html src="([^"]+)\.png"', page.read_text()))
    return found


def test_every_picture_a_page_shows_exists_in_both_themes():
    assert shown()
    for name in shown():
        assert (IMG / f"{name}.png").is_file(), f"{name}.png is missing"
        assert (IMG / f"{name}-dark.png").is_file(), f"{name}-dark.png is missing"


def test_every_picture_can_be_regenerated_by_the_script():
    made = set(script().SHOTS)
    assert shown() == made, "docs pictures and scripts/screenshots.py disagree"


def test_no_picture_of_the_exercise_level_settings_is_made_or_kept():
    # The pane behind the sliders button is described in text, never shown (see CLAUDE.md).
    assert not [p.name for p in IMG.glob("*exercise-settings*")]
    assert not [n for n in script().SHOTS if "exercise-settings" in n]
    assert ".gear" not in (ROOT / "scripts" / "screenshots.py").read_text()
