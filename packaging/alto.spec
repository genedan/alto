# PyInstaller recipe for Alto, used on Linux and Windows: `pyinstaller packaging/alto.spec`.
#
# It makes a folder, dist/alto, with the program `alto` (`alto.exe` on Windows) beside the Python, Qt and Alto files it needs. The
# folder can be copied anywhere. scripts/build-linux.sh builds it and wraps it in the Linux download.
#
# What goes in beyond what PyInstaller finds by itself:
#   - the files of the alto package that are not Python: the fonts, the recordings, the icons and the stylesheets in alto/assets;
#   - alto's package metadata, so that importlib.metadata (and so `alto --version`, a backup's version and the update check) works;
#   - PyNaCl, which checks the signature of an update: it loads a compiled helper (`_cffi_backend`) by a name that PyInstaller cannot
#     see from the imports, so without this the program does not start at all. `alto --self-test` and the build catch it if it breaks.
#
# ALTO_ICON, if set, names the icon of the program: a .ico on Windows. It is not set on Linux, where the menu entry names the icon.
import os
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

a = Analysis(
    ["launcher.py"],
    datas=collect_data_files("alto") + copy_metadata("alto") + copy_metadata("fsrs"),
    hiddenimports=["_cffi_backend", *collect_submodules("nacl")],
    excludes=["tkinter", "pytest"],
)
# Qt's hooks collect optional plugins and their native libraries. Alto draws its own keyboard
# and plays local PCM WAVs with QSoundEffect, which uses the platform audio output.
def unused_qt_component(destination):
    name = Path(destination).name.lower()
    return (
        "virtualkeyboard" in destination.lower()
        or "ffmpeg" in name
        or re.fullmatch(r"(?:lib)?(?:avcodec|avformat|avutil|swresample|swscale)(?:-\d+\.dll|\.so(?:\.\d+)*)", name)
    )


a.binaries = [entry for entry in a.binaries if not unused_qt_component(entry[0])]
a.datas = [entry for entry in a.datas if not unused_qt_component(entry[0])]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="alto",
    console=False,  # a window, not a terminal: there is no console to print to on Windows
    icon=os.environ.get("ALTO_ICON") or None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="alto",
)

# Check the finished bundle, including native libraries and symlinks created during collection.
for path in Path(coll.name).rglob("*"):
    if unused_qt_component(str(path.relative_to(coll.name))):
        raise SystemExit(f"Unexpected optional multimedia or keyboard component in the desktop package: {path}")
