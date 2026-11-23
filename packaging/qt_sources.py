#!/usr/bin/env python
"""Collect Qt's source archives and install notices for the Qt versions used in a desktop build."""

from __future__ import annotations

import hashlib
import lzma
import re
import shutil
import subprocess
import sys
import tarfile
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtCore import qVersion

# Native modules and plugin providers in the desktop bundles, including Qt's translations.
QT_MODULES = {"qtbase", "qtdeclarative", "qtimageformats", "qtmultimedia", "qtsvg", "qtwayland", "qttranslations"}


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _fetch_source(url: str, *, directory: Path) -> tuple[Path, str]:
    # Verify the checksum on cached and freshly downloaded archives.
    path = directory / url.rsplit("/", 1)[1]
    curl = ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3", "--connect-timeout", "30"]
    expected = subprocess.check_output([*curl, url + ".sha256"], text=True).split()[0].lower()
    if not re.fullmatch("[0-9a-f]{64}", expected):
        raise ValueError(f"Invalid upstream checksum for {path.name}")
    if not path.exists() or _sha256(path) != expected:
        partial = path.with_suffix(".part")
        subprocess.run([*curl, "--output", str(partial), url], check=True)
        if _sha256(partial) != expected:
            raise ValueError(f"Checksum mismatch for {path.name}")
        partial.replace(path)
    return path, expected


def _collect_notices(archive: Path, *, notices: ZipFile, destination: Path, bindings: bool) -> None:
    # Preserve upstream paths so each component retains its own credits.
    # Bound each decompressed read even when the source contains highly compressible assets.
    with lzma.open(archive, "rb") as source_stream, tarfile.open(fileobj=source_stream, mode="r|") as tar:
        for entry in tar:
            path = PurePosixPath(entry.name)
            if not entry.isfile() or len(path.parts) < 3:
                continue
            # The binding source contains the same LGPLv3 and GPLv3 texts referenced by Qt.
            if bindings and path.parts[1] == "LICENSES" and path.name in {"LGPL-3.0-only.txt", "GPL-3.0-only.txt"}:
                source = tar.extractfile(entry)
                assert source is not None
                with (destination / path.name).open("wb") as out:
                    shutil.copyfileobj(source, out)
                continue
            if not bindings and path.parts[1] not in QT_MODULES:
                continue
            name = path.name.lower()
            if name == "qt_attribution.json" or any(term in name for term in ("license", "copying", "copyright", "notice")):
                source = tar.extractfile(entry)
                assert source is not None
                notices.writestr(path.as_posix(), source.read())


def _install(frozen: Path, *, sources: Path) -> None:
    qt = qVersion()
    pyside = version("PySide6")
    shiboken = version("shiboken6")
    if pyside != shiboken:
        raise ValueError(f"Unexpected binding versions: PySide6 {pyside}, Shiboken {shiboken}")
    qt_minor = ".".join(qt.split(".")[:2])
    urls = [
        f"https://download.qt.io/archive/qt/{qt_minor}/{qt}/single/qt-everywhere-src-{qt}.tar.xz",
        (
            f"https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{pyside}-src/"
            f"pyside-setup-everywhere-src-{pyside}.tar.xz"
        ),
    ]
    destination = frozen / "licenses" / "Qt"
    destination.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    notice = f"""Alto uses Qt {qt}, PySide6 {pyside}, and Shiboken {shiboken} from The Qt Company and other contributors.
Alto distributes the Qt libraries and Python bindings under LGPL version 3. Their third-party components retain
their own licenses. See LGPL-3.0-only.txt, GPL-3.0-only.txt, and upstream-notices.zip in this directory.

You may modify these libraries, replace them with compatible builds, and reverse engineer Alto to debug those
modifications. Close Alto first. On Windows, the Qt libraries are under _internal/PySide6. On Linux they are
under _internal/PySide6/Qt/lib. Preserve the relative layout, filenames, and ABI when replacing the libraries.
The binding extensions are under _internal/PySide6 and _internal/shiboken6.

Download the corresponding sources alongside this installer on Alto's GitHub release page:
https://github.com/altosaurus/alto/releases/tag/v{version("alto")}

The original upstream source locations and SHA-256 checksums for this build follow.
"""
    with ZipFile(destination / "upstream-notices.zip", "w", compression=ZIP_DEFLATED) as notices:
        for url in urls:
            archive, digest = _fetch_source(url, directory=sources)
            _collect_notices(archive, notices=notices, destination=destination, bindings=archive.name.startswith("pyside-"))
            notice += f"\n{archive.name}\n{url}\nSHA-256 {digest}\n"
    for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt"):
        if not (destination / name).is_file():
            raise ValueError(f"Missing {name} in the upstream source")
    (destination / "README.txt").write_text(notice, encoding="utf-8")


if __name__ == "__main__":
    _install(Path(sys.argv[1]), sources=Path(sys.argv[2]))
