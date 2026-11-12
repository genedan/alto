#!/bin/sh
# Run the test suite for the pre-push hook, using the project's virtual environment if there is one.
# The widget tests use Qt's offscreen platform, so no display is needed.
cd "$(dirname "$0")/.." || exit 1
py=.venv/bin/python
[ -x "$py" ] || py=.venv/Scripts/python.exe
[ -x "$py" ] || py=python
QT_QPA_PLATFORM=offscreen exec "$py" -m pytest -q
