#!/bin/sh
# Run Pyright over the code, using the project's virtual environment if there is one, so it can read PySide6's type hints.
cd "$(dirname "$0")/.." || exit 1
py=.venv/bin/python
[ -x "$py" ] || py=.venv/Scripts/python.exe
[ -x "$py" ] || py=$(command -v python)  # Pyright needs the interpreter's full path
exec "$py" -m pyright --pythonpath "$py"
