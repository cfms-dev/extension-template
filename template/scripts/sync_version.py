"""Overwrite the extension manifest version from pyproject.toml."""

import json
import re
import tomllib
from pathlib import Path

from _project import discover_extension


def sync_version(root: Path) -> str:
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("project.version must be a non-empty string")

    package, _ = discover_extension(root)
    path = package / "manifest.toml"
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    in_extension = False
    replacements = 0
    for index, line in enumerate(lines):
        if line.lstrip().startswith("["):
            in_extension = (
                re.fullmatch(r"\s*\[extension\]\s*(?:#.*)?", line) is not None
            )
        if in_extension and (
            match := re.fullmatch(
                r"([ \t]*version[ \t]*=[ \t]*)(?:\"[^\"\r\n]*\"|'[^'\r\n]*')"
                r"([ \t]*(?:#[^\r\n]*)?)(\r?\n)?",
                line,
            )
        ):
            lines[index] = match[1] + json.dumps(version) + match[2] + (match[3] or "")
            replacements += 1

    if replacements != 1:
        raise ValueError("Expected one single-line version string in [extension]")

    updated = "".join(lines)
    original = tomllib.loads(source)
    original["extension"]["version"] = version
    if tomllib.loads(updated) != original:
        raise ValueError("Version synchronization would change other manifest metadata")
    if updated != source:
        path.write_text(updated, encoding="utf-8")
    return version


if __name__ == "__main__":
    print(
        f"Synchronized manifest version to {sync_version(Path(__file__).resolve().parents[1])}"
    )
