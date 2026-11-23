#!/bin/sh
# Build the Linux download: dist/alto-<version>-linux-<architecture>.tar.gz, and a .sha256 file beside it.
#
#   sh scripts/build-linux.sh
#   PYTHON=/path/to/python3.13 sh scripts/build-linux.sh
#
# It makes a clean virtual environment, installs Alto and PyInstaller in it, freezes Alto with packaging/alto.spec, checks that the
# result starts, and packs it with install.sh. Nothing is installed on this computer.
#
# The frozen program carries the Python it was built with, so build with the Python to ship (the release workflow uses 3.13). It
# also needs at least the C library of the system it was built on, so the release workflow builds on an older Linux than most
# computers have.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
WORK="${ALTO_BUILD_DIR:-$ROOT/.package-build}"
VERSION="$("$PYTHON" -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' "$ROOT/pyproject.toml")"
NAME="alto-$VERSION-linux-$(uname -m)"

echo "Building $NAME with $("$PYTHON" --version)"
rm -rf "$WORK"
mkdir -p "$WORK" "$ROOT/dist"
# Alto is installed from a copy of the source, because installing from the folder itself would leave build files in it.
mkdir -p "$WORK/source"
tar -C "$ROOT" --exclude=.git --exclude=.venv --exclude=.package-build --exclude=dist --exclude=build --exclude=__pycache__ \
    --exclude=alto.egg-info -cf - . | tar -C "$WORK/source" -xf -
"$PYTHON" -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install --quiet "$WORK/source[package]"
(cd "$WORK" && "$WORK/venv/bin/pyinstaller" --noconfirm --clean --log-level WARN --distpath "$WORK/dist" --workpath "$WORK/work" "$ROOT/packaging/alto.spec")
FROZEN="$WORK/dist/alto"
"$WORK/venv/bin/python" "$ROOT/packaging/qt_sources.py" "$FROZEN" "$ROOT/dist/qt-sources"
cp "$ROOT/THIRD_PARTY_NOTICES.md" "$FROZEN/"

# The frozen program must say what version it is, and must open its window. Nothing is drawn on a screen, and it uses its own folder
# for its data, so a real profile is never touched.
SAID="$("$FROZEN/alto" --version)"
[ "$SAID" = "Alto $VERSION" ] || {
    echo "The frozen program says '$SAID', not 'Alto $VERSION'." >&2
    exit 1
}
# What an update needs (the certificate list and the signature check) must be inside the folder.
[ "$("$FROZEN/alto" --self-test)" = "ok" ] || {
    echo "The frozen program's self-test failed: $("$FROZEN/alto" --self-test)" >&2
    exit 1
}
STATUS=0
QT_QPA_PLATFORM=offscreen ALTO_HOME="$WORK/home" timeout 10 "$FROZEN/alto" >/dev/null 2>&1 || STATUS=$?
[ "$STATUS" -eq 124 ] || {
    echo "The frozen program did not stay open (exit code $STATUS)." >&2
    exit 1
}
echo "The frozen program starts and says: $SAID"

# The libraries Qt's X11 plugin needs are copied into the folder from the system this runs on, so a build machine that lacks them makes
# a download that starts on Wayland and not on X11, and the check above (which uses the offscreen platform) cannot tell.
XCB="$FROZEN/_internal/PySide6/Qt/plugins/platforms/libqxcb.so"
MISSING="$(LD_LIBRARY_PATH="$FROZEN/_internal:$FROZEN/_internal/PySide6/Qt/lib" ldd "$XCB" | grep 'not found' || true)"
if [ -n "$MISSING" ]; then
    echo "Qt's X11 plugin is missing libraries, so Alto would not start on an X11 session:" >&2
    echo "$MISSING" >&2
    echo "Install them on this machine (the list is in .github/workflows/build-packages.yml) and build again." >&2
    exit 1
fi

PACKAGE="$WORK/$NAME"
mkdir -p "$PACKAGE/icons"
cp -R "$FROZEN" "$PACKAGE/alto"
cp "$ROOT/packaging/linux/install.sh" "$ROOT/packaging/linux/README.txt" "$PACKAGE/"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$PACKAGE/"
cp "$ROOT/alto/assets/icon-256.png" "$ROOT/alto/assets/icon.png" "$PACKAGE/icons/"
tar -C "$WORK" -czf "$ROOT/dist/$NAME.tar.gz" "$NAME"
(cd "$ROOT/dist" && sha256sum "$NAME.tar.gz" >"$NAME.tar.gz.sha256")
echo "Wrote dist/$NAME.tar.gz ($(du -h "$ROOT/dist/$NAME.tar.gz" | cut -f1)) and its .sha256"
