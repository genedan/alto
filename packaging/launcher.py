#!/usr/bin/env python
"""
The entry point that PyInstaller builds into the `alto` program of a packaged copy.

PyInstaller needs a script to start from, and `alto = alto.__main__:main` in pyproject.toml is only a name for one. This file
runs the same function, so a packaged build and `python -m alto` start the same way.
"""

from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()  # dispatch a spawned exporter before starting the main application
    from alto.__main__ import main

    raise SystemExit(main())
