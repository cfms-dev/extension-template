"""Shared utilities for extension project scripts."""

import tomllib
from pathlib import Path


def discover_extension(root: Path) -> tuple[Path, str]:
    manifests = sorted((root / "src").glob("*/manifest.toml"))

    if len(manifests) != 1:
        raise ValueError(
            f"Expected exactly one extension manifest, found {len(manifests)}"
        )

    package = manifests[0].parent
    manifest = tomllib.loads(manifests[0].read_text(encoding="utf-8"))
    identifier = manifest["extension"]["identifier"]

    if identifier != package.name:
        raise ValueError(
            f"Extension identifier {identifier!r} "
            f"does not match package name {package.name!r}"
        )

    return package, identifier
