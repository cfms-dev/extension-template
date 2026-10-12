"""Resolve the minimum compatible CFMS server Git ref."""

import os
import re
import tomllib
from pathlib import Path

from _project import discover_extension


def resolve(root: Path) -> tuple[str, str]:
    package, _ = discover_extension(root)

    manifest = tomllib.loads(
        (package / "manifest.toml").read_text(encoding="utf-8")
    )

    version = manifest["compatibility"]["minimum_server_version"]

    if not isinstance(version, str):
        raise TypeError("Minimum server version must be a string")

    version = version.removeprefix("v")

    if re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version) is None:
        raise ValueError(f"Invalid minimum server version: {version!r}")

    return version, f"v{version}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    version, ref = resolve(root)

    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as file:
            file.write(f"version={version}\n")
            file.write(f"ref={ref}\n")

    print(f"Resolved CFMS server: {ref}")


if __name__ == "__main__":
    main()