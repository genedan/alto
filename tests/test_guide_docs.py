"""The developer guide in docs/guide hangs together: every chapter is listed, every link works, and Jekyll can render it."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
GUIDE = DOCS / "guide"
LINK = re.compile(r"\{\{\s*'([^']+)'\s*\|\s*relative_url\s*}}")


def front_matter(page: Path) -> dict[str, str]:
    """
    Read the front matter of a docs page.

    Parameters
    ----------
    page : Path
        A Markdown file that starts with a `---` block.

    Returns
    -------
    dict of str to str
        Each `key: value` line of the block.
    """
    head = page.read_text(encoding="utf-8").split("---\n", 2)[1]
    return dict(line.split(": ", 1) for line in head.strip().split("\n"))


def permalinks() -> set[str]:
    """
    List the permalink of every page of the site.

    Returns
    -------
    set of str
        The permalinks of the pages in `docs/` and `docs/guide/` and `docs/api/`, such as `/guide/qt/`.
    """
    pages = [*DOCS.glob("*.md"), *GUIDE.glob("*.md"), *(DOCS / "api").glob("*.md")]
    return {front_matter(p)["permalink"] for p in pages}


def chapters() -> list[Path]:
    """
    List the chapters of the guide, without its index.

    Returns
    -------
    list of Path
        The chapter files, in the order the guide gives them.
    """
    return sorted((p for p in GUIDE.glob("*.md") if p.name != "index.md"), key=lambda p: int(front_matter(p)["order"]))


def test_every_chapter_is_listed_on_the_index_and_numbered_once() -> None:
    """
    Check that every chapter has a distinct order number and is linked from the guide's index.
    """
    index = (GUIDE / "index.md").read_text(encoding="utf-8")
    orders = [int(front_matter(p)["order"]) for p in chapters()]
    assert orders == sorted(set(orders)), "chapter order numbers must be distinct"
    for chapter in chapters():
        meta = front_matter(chapter)
        assert meta["parent"] == "guide" and meta["permalink"] == f"/guide/{chapter.stem}/", chapter.name
        assert f"'{meta['permalink']}'" in index, f"{chapter.name} is not linked from the index"


@pytest.mark.parametrize("page", [GUIDE / "index.md", *chapters()], ids=lambda p: p.name)
def test_every_link_in_a_guide_page_goes_to_a_page_that_exists(page: Path) -> None:
    """
    Check that every site link in a guide page points at the permalink of a real page.

    Parameters
    ----------
    page : Path
        The guide page, supplied by the parametrisation.
    """
    known = permalinks()
    for target in LINK.findall(page.read_text(encoding="utf-8")):
        assert target in known, f"{page.name} links to {target}, which is no page"


@pytest.mark.parametrize("page", [GUIDE / "index.md", *chapters()], ids=lambda p: p.name)
def test_a_guide_page_has_no_stray_liquid_for_jekyll_to_trip_over(page: Path) -> None:
    """
    Check that the only template code in a guide page is a `relative_url` link, since Jekyll runs Liquid over every page.

    Parameters
    ----------
    page : Path
        The guide page, supplied by the parametrisation.
    """
    text = LINK.sub("", page.read_text(encoding="utf-8"))
    assert "{{" not in text and "{%" not in text, f"{page.name} has braces that Jekyll would read as template code"


def test_the_guide_has_a_glossary_and_reading_list() -> None:
    """
    Check that the last chapter has the glossary and the reading list the other chapters point to.
    """
    text = (GUIDE / "reading.md").read_text(encoding="utf-8")
    assert "## Glossary" in text and "## Reading list" in text
