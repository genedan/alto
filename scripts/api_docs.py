#!/usr/bin/env python
"""
Write the API reference pages in docs/api from the docstrings in alto/.

    python scripts/api_docs.py            # rewrite docs/api
    python scripts/api_docs.py --check    # fail if docs/api is out of date, changing nothing

Every public module gets a page with its public classes, methods and functions: the signature, then the NumPy-style
docstring turned into Markdown. The source is read as text and never imported, so the script needs neither Qt nor a
display. GitHub Pages cannot run this script, so the pages are committed, and `tests/test_api_docs.py` fails when they are
out of date.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "alto"
OUT = ROOT / "docs" / "api"
SECTION = re.compile(r"^(?P<title>[A-Z][A-Za-z ]+)\n-{3,}$", re.MULTILINE)
LIST_SECTIONS = ("Parameters", "Attributes", "Returns", "Yields", "Raises")


def module_files() -> list[Path]:
    """
    List the modules that get a page: every file of the package except the `__init__` and `__main__` files.

    Returns
    -------
    list of Path
        The source files, ordered by package and then by name.

    Examples
    --------
    >>> [dotted(p) for p in module_files()][:2]
    ['alto.audio', 'alto.instrument_info']
    """
    files = [p for p in SOURCE.rglob("*.py") if p.name not in ("__init__.py", "__main__.py")]
    return sorted(files, key=lambda p: (package_of(p) != "alto", package_of(p), p.name))


def dotted(path: Path) -> str:
    """
    Return the dotted module name of a source file.

    Parameters
    ----------
    path : Path
        A file under `alto/`.

    Returns
    -------
    str
        The name, such as `alto.theory.pitch`.

    Examples
    --------
    >>> dotted(SOURCE / "theory" / "pitch.py")
    'alto.theory.pitch'
    >>> dotted(SOURCE / "theory" / "__init__.py")
    'alto.theory'
    """
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def package_of(path: Path) -> str:
    """
    Return the package a module belongs to.

    Parameters
    ----------
    path : Path
        A file under `alto/`.

    Returns
    -------
    str
        The dotted name of the folder it is in, such as `alto.theory`, or `alto` for a module at the top.

    Examples
    --------
    >>> package_of(SOURCE / "theory" / "pitch.py")
    'alto.theory'
    >>> package_of(SOURCE / "audio.py")
    'alto'
    """
    return dotted(path).rsplit(".", 1)[0]


def split_sections(doc: str) -> dict[str, str]:
    r"""
    Split a cleaned NumPy-style docstring into its sections.

    Parameters
    ----------
    doc : str
        The docstring, already dedented.

    Returns
    -------
    dict of str to str
        Section title to its text. The text before the first section is under the key "".

    Examples
    --------
    >>> split_sections("Summary.\n\nReturns\n-------\nint\n    A number.")
    {'': 'Summary.', 'Returns': 'int\n    A number.'}
    """
    found = list(SECTION.finditer(doc))
    out = {"": doc[: found[0].start()].strip() if found else doc.strip()}
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(doc)
        out[m["title"]] = doc[m.end() : end].strip("\n").rstrip()
    return out


def entries(text: str) -> list[tuple[str, str, str]]:
    r"""
    Read the entries of a Parameters, Attributes, Returns or Raises section.

    Parameters
    ----------
    text : str
        The section's text.

    Returns
    -------
    list of tuple of str
        One `(name, type, description)` per entry. The name is empty for a Returns or Raises entry, which has only a type.

    Examples
    --------
    >>> entries("n : int\n    How many.\nflag : bool, default False\n    Whether.")
    [('n', 'int', 'How many.'), ('flag', 'bool, default False', 'Whether.')]
    >>> entries("int\n    A number.")
    [('', 'int', 'A number.')]
    """
    out: list[tuple[str, str, str]] = []
    for line in text.split("\n"):
        if line and not line.startswith(" "):
            name, sep, kind = line.partition(" : ")
            out.append((name, kind, "") if sep else ("", line, ""))
        elif line.strip() and out:
            name, kind, desc = out[-1]
            out[-1] = (name, kind, f"{desc} {line.strip()}".strip())
    return out


def render_doc(doc: str | None) -> str:
    r"""
    Turn a docstring into Markdown.

    Parameters
    ----------
    doc : str or None
        The raw docstring, or None if there is none.

    Returns
    -------
    str
        The Markdown: the text, then each section. The examples go in a fenced block.

    Examples
    --------
    >>> print(render_doc("Do it.\n\nParameters\n----------\nn : int\n    How many."))
    Do it.
    <BLANKLINE>
    **Parameters**
    <BLANKLINE>
    - `n` (*int*): How many.
    """
    if not doc:
        return ""
    parts = split_sections(inspect.cleandoc(doc))
    out = [parts[""]] if parts[""] else []
    for title, text in parts.items():
        if not title:
            continue
        if title == "Examples":
            out.append(f"**Examples**\n\n```pycon\n{text}\n```")
        elif title in LIST_SECTIONS:
            lines = []
            for name, kind, desc in entries(text):
                label = f"`{name}` (*{kind}*)" if name and kind else f"`{name}`" if name else f"*{kind}*"
                lines.append(f"- {label}: {desc}" if desc else f"- {label}")
            out.append(f"**{title}**\n\n" + "\n".join(lines))
        else:
            out.append(f"**{title}**\n\n{text}")
    return "\n\n".join(out)


def parameters(args: ast.arguments) -> list[str]:
    """
    List the parameters of a function as they are written in its signature, without `self` or `cls`.

    Parameters
    ----------
    args : ast.arguments
        The function's arguments.

    Returns
    -------
    list of str
        One string per parameter, such as `n: int = 3`, with `*` and `**` entries where they belong.

    Examples
    --------
    >>> parameters(ast.parse("def f(self, a: int, *, b: str = 'x', **rest: int): ...").body[0].args)
    ['a: int', '*', "b: str = 'x'", '**rest: int']
    """
    positional = [*args.posonlyargs, *args.args]
    if positional and positional[0].arg in ("self", "cls"):
        positional = positional[1:]
    defaults: list[ast.expr | None] = [None] * (len(args.posonlyargs) + len(args.args) - len(args.defaults)) + list(args.defaults)
    defaults = defaults[len(defaults) - len(positional) :]

    def one(arg: ast.arg, *, default: ast.expr | None) -> str:
        """
        Write one parameter.

        Parameters
        ----------
        arg : ast.arg
            The parameter.
        default : ast.expr or None
            Its default value, if it has one. Keyword-only.

        Returns
        -------
        str
            The parameter as written in a signature.

        Examples
        --------
        >>> one(ast.arg(arg="n", annotation=ast.Name(id="int")), default=ast.Constant(value=3))
        'n: int = 3'
        """
        text = arg.arg + (f": {ast.unparse(arg.annotation)}" if arg.annotation else "")
        return text + (f" = {ast.unparse(default)}" if default is not None else "")

    out = [one(a, default=d) for a, d in zip(positional, defaults, strict=True)]
    if args.vararg:
        out.append("*" + one(args.vararg, default=None))
    elif args.kwonlyargs:
        out.append("*")
    out += [one(a, default=d) for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True)]
    if args.kwarg:
        out.append("**" + one(args.kwarg, default=None))
    return out


def fence(
    head: str,
    *,
    params: list[str] | None,
    returns: str = "",
) -> str:
    """
    Write a signature as a Python code block, one parameter to a line when there are two or more.

    Parameters
    ----------
    head : str
        What comes before the parentheses, such as `def area` or `Note`.
    params : list of str or None
        The parameters, or None for a name with no parentheses at all. Keyword-only.
    returns : str, default ""
        The return annotation, written after `->`. Keyword-only.

    Returns
    -------
    str
        The fenced code block.

    Examples
    --------
    >>> print(fence("def f", params=["a: int"], returns="int"))
    ```python
    def f(a: int) -> int
    ```
    >>> print(fence("def f", params=["a", "b"]))
    ```python
    def f(
        a,
        b,
    )
    ```
    """
    tail = f" -> {returns}" if returns else ""
    if params is None:
        body = head + tail
    elif len(params) < 2:
        body = f"{head}({', '.join(params)}){tail}"
    else:
        body = f"{head}(\n" + "".join(f"    {p},\n" for p in params) + f"){tail}"
    return f"```python\n{body}\n```"


def decorator_names(node: ast.FunctionDef | ast.ClassDef) -> list[str]:
    r"""
    List the decorators of a function or class, written as in the source.

    Parameters
    ----------
    node : ast.FunctionDef or ast.ClassDef
        The definition.

    Returns
    -------
    list of str
        The decorators, without the `@`.

    Examples
    --------
    >>> decorator_names(ast.parse("@property\ndef f(self): ...").body[0])
    ['property']
    """
    return [ast.unparse(d) for d in node.decorator_list]


def render_function(
    node: ast.FunctionDef,
    *,
    level: int,
    prefix: str = "",
) -> str:
    r"""
    Write the section for one function or method.

    Parameters
    ----------
    node : ast.FunctionDef
        The function.
    level : int
        The heading level, 2 for a function and 3 for a method. Keyword-only.
    prefix : str, default ""
        The class name and a dot, for a method. Keyword-only.

    Returns
    -------
    str
        The Markdown: a heading, the signature and the docstring.

    Examples
    --------
    >>> tree = ast.parse("def f(n: int) -> int:\n    '''Double it.'''\n    return n * 2")
    >>> print(render_function(tree.body[0], level=2))
    ## f
    <BLANKLINE>
    ```python
    def f(n: int) -> int
    ```
    <BLANKLINE>
    Double it.
    """
    head = "\n".join(f"@{d}" for d in decorator_names(node))
    sig = fence(
        f"def {node.name}",
        params=parameters(node.args),
        returns=ast.unparse(node.returns) if node.returns else "",
    )
    if head:
        sig = sig.replace("```python\n", f"```python\n{head}\n", 1)
    parts = [f"{'#' * level} {prefix}{node.name}", sig, render_doc(ast.get_docstring(node, clean=False))]
    return "\n\n".join(p for p in parts if p)


def class_fields(node: ast.ClassDef) -> list[str]:
    r"""
    List the fields of a dataclass as constructor parameters.

    Parameters
    ----------
    node : ast.ClassDef
        The class.

    Returns
    -------
    list of str
        One string per field, with `*` where the keyword-only fields start (a `KW_ONLY` marker).

    Examples
    --------
    >>> tree = ast.parse("class C:\n    a: int\n    _: KW_ONLY\n    b: str = 'x'")
    >>> class_fields(tree.body[0])
    ['a: int', '*', "b: str = 'x'"]
    """
    out = []
    for stmt in node.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        annotation = ast.unparse(stmt.annotation)
        if annotation == "KW_ONLY":
            out.append("*")
        elif not annotation.startswith("ClassVar"):
            out.append(f"{stmt.target.id}: {annotation}" + (f" = {ast.unparse(stmt.value)}" if stmt.value is not None else ""))
    return out


def render_class(node: ast.ClassDef) -> str:
    r"""
    Write the section for one class: its constructor, its docstring and its public methods.

    Parameters
    ----------
    node : ast.ClassDef
        The class.

    Returns
    -------
    str
        The Markdown.

    Examples
    --------
    >>> tree = ast.parse("class C(Base):\n    '''A thing.'''\n    def go(self) -> None:\n        '''Go.'''")
    >>> print(render_class(tree.body[0]).splitlines()[0])
    ## C
    """
    init: ast.FunctionDef | None = None
    methods: list[ast.FunctionDef] = []
    for stmt in node.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            init = stmt
        elif isinstance(stmt, ast.FunctionDef) and not stmt.name.startswith("_"):
            methods.append(stmt)
    if init is not None:
        params: list[str] | None = parameters(init.args)
    elif any(d.startswith("dataclass") or d.endswith(".dataclass") for d in decorator_names(node)):
        params = class_fields(node)
    else:
        params = None
    bases = ", ".join(ast.unparse(b) for b in node.bases)
    parts = [f"## {node.name}", fence(f"class {node.name}" + (f"({bases})" if bases else ""), params=None)]
    if params is not None:
        parts[1] = fence(node.name, params=params)
        if bases:
            parts.append(f"Bases: `{bases}`")
    parts.append(render_doc(ast.get_docstring(node, clean=False)))
    if init is not None and ast.get_docstring(init):
        built = render_doc(ast.get_docstring(init, clean=False)).replace("**Examples**", "**Constructor examples**")
        parts.append(f"**Constructor**\n\n{built}")
    parts.extend(render_function(method, level=3, prefix=f"{node.name}.") for method in methods)
    return "\n\n".join(p for p in parts if p)


def summary(doc: str | None) -> str:
    r"""
    Return the first paragraph of a docstring on one line.

    Parameters
    ----------
    doc : str or None
        The docstring.

    Returns
    -------
    str
        The first paragraph, joined into a single line. Empty if there is no docstring.

    Examples
    --------
    >>> summary("First line\ncontinues here.\n\nSecond paragraph.")
    'First line continues here.'
    """
    return " ".join(inspect.cleandoc(doc).split("\n\n")[0].split()) if doc else ""


def render_module(
    path: Path,
    *,
    order: int,
) -> str:
    r"""
    Write the page for one module.

    Parameters
    ----------
    path : Path
        The source file.
    order : int
        Where the page goes in the contents list. Keyword-only.

    Returns
    -------
    str
        The whole page: front matter and body. The body is wrapped in Liquid's `raw` tags so that braces in a docstring
        cannot be taken for template code.

    Examples
    --------
    >>> page = render_module(SOURCE / "theory" / "pitch.py", order=7)
    >>> page.startswith("---\ntitle: alto.theory.pitch\n")
    True
    >>> "## Note" in page
    True
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = dotted(path)
    front = f"---\ntitle: {name}\nparent: api\npackage: {package_of(path)}\norder: {order}\npermalink: /api/{name}/\n---\n"
    parts = [render_doc(ast.get_docstring(tree, clean=False))]
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            parts.append(render_class(node))
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            parts.append(render_function(node, level=2))
    body = "\n\n".join(p for p in parts if p)
    return f"{front}{{% raw %}}\n{body}\n{{% endraw %}}\n"


def render_index(files: list[Path]) -> str:
    """
    Write the front page of the reference: what it covers and a list of every module.

    Parameters
    ----------
    files : list of Path
        The modules, in the order they are listed.

    Returns
    -------
    str
        The page.

    Examples
    --------
    >>> page = render_index(module_files())
    >>> "[alto.audio](alto.audio/)" in page
    True
    """
    out = [
        "---\ntitle: API reference\nnav_order: 11\nchildren: api\npermalink: /api/\n---\n",
        (
            "Every public module, class and function in Alto, with its signature and docstring. Names that begin with an "
            "underscore are internal and are left out. The pages are written from the docstrings by `scripts/api_docs.py`, so "
            "they match the code.\n"
        ),
    ]
    last = ""
    for path in files:
        pkg = package_of(path)
        if pkg != last:
            init = path.parent / "__init__.py"
            blurb = summary(ast.get_docstring(ast.parse(init.read_text(encoding="utf-8")))) if init.exists() else ""
            out.append(f"\n## {pkg}\n" + (f"\n{blurb}\n" if blurb else "") + "\n| Module | What it is |\n|---|---|")
            last = pkg
        about = summary(ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))))
        out.append(f"| [{dotted(path)}]({dotted(path)}/) | {about.replace('|', chr(92) + '|')} |")
    return "\n".join(out) + "\n"


def build() -> dict[str, str]:
    """
    Write every page, in memory.

    Returns
    -------
    dict of str to str
        File name (relative to `docs/api`) to its content.

    Examples
    --------
    >>> built = build()
    >>> "index.md" in built and "alto.audio.md" in built
    True
    """
    files = module_files()
    pages = {"index.md": render_index(files)}
    for i, path in enumerate(files, start=1):
        pages[f"{dotted(path)}.md"] = render_module(path, order=i)
    return pages


def problems(*, out: Path = OUT) -> list[str]:
    """
    Compare the pages on disk with the ones the docstrings give.

    Parameters
    ----------
    out : Path, default docs/api
        The folder the pages are in. Keyword-only.

    Returns
    -------
    list of str
        One line for each page that is missing, out of date or no longer wanted. Empty when everything is current.

    Examples
    --------
    >>> problems(out=Path("/nonexistent"))[0]
    'missing: index.md'
    """
    wanted = build()
    found = {p.name for p in out.glob("*.md")} if out.is_dir() else set()
    out_of_date = [
        f"out of date: {n}" for n, text in wanted.items() if n in found and (out / n).read_text(encoding="utf-8") != text
    ]
    return (
        [f"missing: {n}" for n in wanted if n not in found]
        + out_of_date
        + [f"no longer wanted: {n}" for n in sorted(found - set(wanted))]
    )


def write(*, out: Path = OUT) -> int:
    """
    Write the pages to disk and remove the ones that are no longer wanted.

    Parameters
    ----------
    out : Path, default docs/api
        The folder to write to. Keyword-only.

    Returns
    -------
    int
        How many pages were written.

    Examples
    --------
    >>> write(out=Path("/tmp/api-docs-example")) > 10  # doctest: +SKIP
    True
    """
    pages = build()
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.md"):
        if stale.name not in pages:
            stale.unlink()
    for name, text in pages.items():
        (out / name).write_text(text, encoding="utf-8")
    return len(pages)


def main() -> int:
    """
    Run the script: rewrite docs/api, or with `--check` only report what is out of date.

    Returns
    -------
    int
        0 on success, 1 if `--check` found pages that are out of date.

    Examples
    --------
    >>> main()  # doctest: +SKIP
    wrote 43 pages to docs/api
    0
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[1].strip())
    parser.add_argument("--check", action="store_true", help="report out-of-date pages instead of writing them")
    args = parser.parse_args()
    if args.check:
        found = problems()
        for line in found:
            print(line)
        if found:
            print("docs/api is out of date: run `python scripts/api_docs.py`")
        return 1 if found else 0
    count = write()
    print(f"wrote {count} pages to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
