"""The API reference in docs/api stays in step with the docstrings it is written from."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def api_docs() -> ModuleType:
    """
    Load scripts/api_docs.py as a module, without running it.

    Returns
    -------
    ModuleType
        The loaded module.
    """
    spec = importlib.util.spec_from_file_location("api_docs", ROOT / "scripts" / "api_docs.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # only defines things; the work happens under __main__
    return module


def test_the_committed_pages_match_the_docstrings(api_docs: ModuleType) -> None:
    """
    Check that the committed pages match the docstrings; if not, run `python scripts/api_docs.py`.

    Parameters
    ----------
    api_docs : ModuleType
        The script that writes the pages.
    """
    assert api_docs.problems() == [], "docs/api is out of date: run `python scripts/api_docs.py`"


def test_every_module_has_a_page_with_its_public_names(api_docs: ModuleType) -> None:
    """
    Check that every module has a page, listed on the index, that names its public classes and leaves out private ones.

    Parameters
    ----------
    api_docs : ModuleType
        The script that writes the pages.
    """
    pages = api_docs.build()
    for path in api_docs.module_files():
        assert f"{api_docs.dotted(path)}.md" in pages
        assert f"[{api_docs.dotted(path)}]" in pages["index.md"]
    assert "## Learner" in pages["alto.learning.learner.md"]
    assert "## _Chart" not in pages["alto.ui.charts.md"]
    assert "## StackedBarChart" in pages["alto.ui.charts.md"]


def test_a_page_has_the_front_matter_the_site_needs(api_docs: ModuleType) -> None:
    """
    Check that a page carries the front matter the docs layout reads, and wraps its text in Liquid's raw tags.

    Parameters
    ----------
    api_docs : ModuleType
        The script that writes the pages.
    """
    page = api_docs.build()["alto.theory.pitch.md"]
    head, _, body = page.removeprefix("---\n").partition("---\n")
    assert "title: alto.theory.pitch" in head and "parent: api" in head and "permalink: /api/alto.theory.pitch/" in head
    assert body.startswith("{% raw %}") and body.rstrip().endswith("{% endraw %}")
    assert "{%" not in body.replace("{% raw %}", "").replace("{% endraw %}", "")


def test_the_check_reports_what_is_missing_or_stale(
    api_docs: ModuleType,
    tmp_path: Path,
) -> None:
    """
    Check that a folder with a missing, a stale and an unwanted page is reported, and a freshly written one is clean.

    Parameters
    ----------
    api_docs : ModuleType
        The script that writes the pages.
    tmp_path : Path
        A scratch folder unique to this test.
    """
    assert api_docs.write(out=tmp_path) == len(api_docs.build())
    assert api_docs.problems(out=tmp_path) == []
    (tmp_path / "alto.audio.md").write_text("old")
    (tmp_path / "alto.settings.md").unlink()
    (tmp_path / "gone.md").write_text("x")
    assert sorted(api_docs.problems(out=tmp_path)) == [
        "missing: alto.settings.md",
        "no longer wanted: gone.md",
        "out of date: alto.audio.md",
    ]
