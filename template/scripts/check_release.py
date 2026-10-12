"""Validate release metadata and ZIP without importing the extension runtime."""

import argparse
import ast
import hashlib
import re
import tomllib
import zipfile
from pathlib import Path

from _project import discover_extension


def module_version(source: str) -> str:
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in statement.targets
        ):
            value = ast.literal_eval(statement.value)
            if isinstance(value, str):
                return value

    raise ValueError("Missing literal __version__ assignment")


def check_version(root: Path, tag: str) -> tuple[str, str]:
    if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) is None:
        raise ValueError(f"Release tag must use vX.Y.Z format: {tag}")

    version = tag[1:]
    package, identifier = discover_extension(root)

    versions = {
        "pyproject.toml": tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"],
        "manifest.toml": tomllib.loads(
            (package / "manifest.toml").read_text(encoding="utf-8")
        )["extension"]["version"],
        **{
            name: module_version((package / name).read_text(encoding="utf-8"))
            for name in ("__init__.py", "_extension.py")
        },
    }

    for name, declared in versions.items():
        if declared != version:
            raise ValueError(
                f"Tag version {version} does not match {name} version {declared}"
            )

    return version, identifier


def check_archive(root: Path, version: str, identifier: str) -> Path:
    path = root / "dist" / f"{identifier}-{version}.zip"

    with path.open("rb") as package_file:
        digest = hashlib.file_digest(package_file, "sha256").hexdigest()

    checksum = path.with_suffix(".zip.sha256").read_text(encoding="ascii")

    if checksum != f"{digest}  {path.name}\n":
        raise ValueError(f"Invalid SHA-256 checksum: {path.name}")

    with zipfile.ZipFile(path) as archive:
        if bad_member := archive.testzip():
            raise ValueError(f"Corrupt ZIP member: {bad_member}")

        manifest = tomllib.loads(archive.read("manifest.toml").decode("utf-8"))

        if manifest["extension"]["identifier"] != identifier:
            raise ValueError("Invalid archive extension identifier")

        if manifest["extension"]["version"] != version:
            raise ValueError("Archive manifest version does not match release")

        for name in ("__init__.py", "_extension.py"):
            if module_version(archive.read(name).decode("utf-8")) != version:
                raise ValueError(f"Archive {name} version does not match release")

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Version tag in vX.Y.Z format")
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Also verify dist ZIP",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]

    try:
        version, identifier = check_version(root, args.tag)
        if args.archive:
            check_archive(root, version, identifier)
    except (
        ValueError,
        OSError,
        KeyError,
        SyntaxError,
        zipfile.BadZipFile,
    ) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")

    print(f"Validated release {args.tag}" + (" and archive" if args.archive else ""))


if __name__ == "__main__":
    main()
