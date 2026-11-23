"""Copy or verify upstream notices for the genanki and PyNaCl wheels in a desktop build."""

from argparse import ArgumentParser
from importlib.metadata import distribution
from pathlib import Path

# libsodium is included in the PyNaCl wheel and carries a separate notice.
LICENSE_FILES = (
    ("genanki", "LICENSE.txt", "genanki/LICENSE.txt"),
    ("PyNaCl", "LICENSE", "PyNaCl/LICENSE"),
    ("PyNaCl", "LICENSE.libsodium.txt", "libsodium/LICENSE.libsodium.txt"),
)


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("copy", "verify"))
    parser.add_argument("app_directory", type=Path)
    args = parser.parse_args()

    for package, filename, relative_path in LICENSE_FILES:
        wheel = distribution(package)
        matches = [entry for entry in wheel.files or () if entry.name == filename and entry.parts[0].endswith(".dist-info")]
        if len(matches) != 1:
            raise SystemExit(f"Expected one {filename} in {package} {wheel.version} metadata, found {len(matches)}")
        contents = matches[0].read_binary()
        if not contents.strip():
            raise SystemExit(f"Empty upstream notice in {package} {wheel.version}: {filename}")
        target = args.app_directory / "licenses" / relative_path
        if args.action == "copy":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
        elif not target.is_file() or target.read_bytes() != contents:
            raise SystemExit(f"Missing or altered installed notice: {target}")


if __name__ == "__main__":
    main()
