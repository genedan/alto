#!/usr/bin/env python3
"""Copy dependency licenses and verify the notices shipped in a desktop installation."""

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
    """
    Write the wheel notices or compare them with the installed copies.

    Raises
    ------
    SystemExit
        If a required notice is ambiguous, missing, empty, or differs after installation.

    """
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

    if args.action == "verify":
        root = Path(__file__).resolve().parents[1]
        sample_credits = Path("alto/assets/samples/SOURCE.txt")
        notices = Path("THIRD_PARTY_NOTICES.md")
        wheel_metadata = Path(f"alto-{distribution('alto').version}.dist-info")
        for source, installed in (
            (notices, notices),
            (notices, Path("_internal") / wheel_metadata / "licenses" / notices),
            (sample_credits, Path("_internal") / sample_credits),
        ):
            expected = (root / source).read_text(encoding="utf-8")
            if (args.app_directory / installed).read_text(encoding="utf-8") != expected:
                raise SystemExit(f"Installed credits differ from {source}: {installed}")


if __name__ == "__main__":
    main()
