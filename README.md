# Alto

Desktop music theory drills (PySide6). Run: `python -m alto`

- `alto/theory/` – pure-Python theory engine (spelled notes, intervals, scales, chords); no Qt.
- `alto/exercises/` – exercises. Add one by subclassing `Exercise` and decorating with `@register`.
- `alto/ui/` – Qt widgets (staff renderer, exercise view, main window).

Setup: `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`; run: `alto` or `python -m alto`; tests: `pytest`; lint: `ruff check alto tests`; checks on commit and tests on push: `pre-commit install`.

## Documentation

User and developer guides are in [`docs/`](docs/), published at https://genedan.github.io/alto/.

## License

Alto's own code is released under the [MIT License](LICENSE). The bundled music fonts and instrument recordings are
not covered by it: each keeps its author's terms, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), with the
licence texts beside the files in `alto/assets/`.
