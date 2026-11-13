"""
Every module, class, function and method has a NumPy-style docstring that describes its parameters and what it returns.

Ruff checks the public ones. This test also covers the private, dunder and nested ones, which Ruff skips, and checks that
each docstring has the sections the signature calls for. The packages listed in `DOCUMENTED` are checked; the list grows as each
package is documented.
"""

import ast
import inspect
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCUMENTED = [
    "alto/theory",
    "alto/learning",
    "alto/exercises",
    "alto/__init__.py",
    "alto/__main__.py",
    "alto/audio.py",
    "alto/instrument_info.py",
    "alto/settings.py",
    "alto/ui/__init__.py",
    "alto/ui/colors.py",
    "alto/ui/app_settings.py",
    "alto/ui/charts.py",
    "alto/ui/database_page.py",
    "alto/ui/pictures.py",
    "alto/ui/exercise_view.py",
    "alto/ui/instrument_picker.py",
    "alto/ui/keyboard.py",
    "alto/ui/main_window.py",
    "alto/ui/staff.py",
    "alto/ui/settings_panel.py",
    "alto/ui/engraving.py",
    "alto/ui/keyboard_styles.py",
    "alto/ui/notes.py",
    "alto/ui/stats_dialog.py",
    "alto/ui/home.py",
    "alto/ui/icons.py",
    "alto/ui/profile_dialog.py",
    "alto/ui/question_preview.py",
    "alto/ui/staff_input.py",
    "alto/ui/style.py",
    "alto/ui/notation.py",
    "alto/ui/store.py",
    "alto/ui/theme.py",
    "alto/ui/widgets.py",
    "tests",
    "scripts",
    "conftest.py",
]

SECTION = re.compile(r"^(?P<title>[A-Z][A-Za-z ]+)\n-{3,}$", re.MULTILINE)


def sections(doc: str) -> dict[str, str]:
    r"""
    Split a NumPy-style docstring into its sections.

    Parameters
    ----------
    doc : str
        The docstring text.

    Returns
    -------
    dict of str to str
        Section title to the text under it. The text before the first section is under the key "".

    Examples
    --------
    >>> sections("Summary.\n\nParameters\n----------\nx : int\n    An x.\n")["Parameters"]
    'x : int\n    An x.\n'
    """
    found = list(SECTION.finditer(doc))
    out = {"": doc[: found[0].start()] if found else doc}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(doc)
        out[m.group("title")] = doc[m.end() + 1 : end]
    return out


def documented_names(parameters: str) -> set[str]:
    r"""
    Return the parameter names listed in a Parameters section.

    Parameters
    ----------
    parameters : str
        The text under the "Parameters" heading.

    Returns
    -------
    set of str
        Each name that starts an entry, such as `x` in `x : int` or both names in `x, y : int`.

    Examples
    --------
    >>> sorted(documented_names("x, y : int\n    Two numbers.\n*args : float\n    More.\n"))
    ['args', 'x', 'y']
    """
    names: set[str] = set()
    for line in parameters.splitlines():
        m = re.match(r"^(\*{0,2}\w+(?:\s*,\s*\*{0,2}\w+)*)\s*:\s*\S", line)
        if m:
            names.update(n.strip().lstrip("*") for n in m.group(1).split(","))
    return names


def python_files() -> list[Path]:
    """
    Return the source files in the documented packages.

    Returns
    -------
    list of Path
        Every .py file under each directory in `DOCUMENTED`, and each file listed there, sorted.

    Examples
    --------
    >>> all(p.suffix == ".py" for p in python_files())
    True
    """
    return sorted(p for d in DOCUMENTED for p in ([ROOT / d] if (ROOT / d).is_file() else (ROOT / d).rglob("*.py")))


def problems(path: Path) -> list[str]:
    """
    Return everything wrong with the docstrings of one file.

    Parameters
    ----------
    path : Path
        The source file.

    Returns
    -------
    list of str
        One line per problem, each starting with `file:line`. Empty when the file is fine.

    Examples
    --------
    >>> problems(ROOT / "alto" / "theory" / "pitch.py")
    []
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    where = path.relative_to(ROOT)
    out: list[str] = []
    if not ast.get_docstring(tree):
        out.append(f"{where}:1 module has no docstring")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        label = f"{where}:{node.lineno} {node.name}"
        raw = ast.get_docstring(node, clean=False)
        if raw is None:
            out.append(f"{label} has no docstring")
            continue
        parts = sections(inspect.cleandoc(raw))
        is_test = node.name.startswith("test_") or where.parts[0] == "tests" or where.name == "conftest.py"
        if not parts[""].strip():
            out.append(f"{label} has no summary line")
        if isinstance(node, ast.ClassDef):
            if not is_test and "Examples" not in parts:
                out.append(f"{label} has no Examples section")
            continue
        if any(isinstance(d, ast.Attribute) and d.attr in ("setter", "deleter") for d in node.decorator_list):
            continue
        a = node.args
        extras = [x for x in (a.vararg, a.kwarg) if x is not None]
        params = [*a.posonlyargs, *a.args, *a.kwonlyargs, *extras]
        names = [p.arg for p in params]
        if names and names[0] in ("self", "cls"):
            names = names[1:]
        if names:
            listed = documented_names(parts.get("Parameters", ""))
            out.extend(f"{label} does not describe the parameter `{name}`" for name in names if name not in listed)
        returns_nothing = node.returns is None or ast.unparse(node.returns) in ("None", "NoReturn", "Never")
        yields = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))
        if yields and "Yields" not in parts:
            out.append(f"{label} has no Yields section")
        elif not yields and not returns_nothing and "Returns" not in parts:
            out.append(f"{label} has no Returns section")
        if not is_test and "Examples" not in parts:
            out.append(f"{label} has no Examples section")
    return out


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_every_definition_has_a_complete_docstring(path: Path) -> None:
    """
    Check the docstrings of one source file.

    Parameters
    ----------
    path : Path
        The file, supplied by the parametrisation.
    """
    assert problems(path) == []


def test_the_checker_catches_what_it_should(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Check that a file with missing and incomplete docstrings is reported.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder.
    monkeypatch : pytest.MonkeyPatch
        Used to point the checker's root at the scratch folder.
    """
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    bad = tmp_path / "bad.py"
    bad.write_text(
        '"""Module."""\n'
        "\n"
        "\n"
        "def f(a: int, b: int) -> int:\n"
        '    """Do it.\n'
        "\n"
        "    Parameters\n"
        "    ----------\n"
        "    a : int\n"
        "        An a.\n"
        '    """\n'
        "    return a\n"
        "\n"
        "\n"
        "def g():\n"
        "    pass\n",
    )
    found = problems(bad)
    assert any("does not describe the parameter `b`" in line for line in found)
    assert any("f has no Returns section" in line for line in found)
    assert any("f has no Examples section" in line for line in found)
    assert any("g has no docstring" in line for line in found)


def test_there_are_documented_packages_to_check() -> None:
    """
    Check that the list of documented packages is not empty and points at real code.

    Notes
    -----
    A vacuous pass would be worse than a failure, so each package must contain source files.
    """
    assert DOCUMENTED and all((ROOT / d).is_file() or list((ROOT / d).rglob("*.py")) for d in DOCUMENTED)
