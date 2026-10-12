"""Validate extension project metadata."""

import tomllib
from pathlib import Path


def test_manifest_metadata() -> None:
    root = Path(__file__).resolve().parents[1]

    manifests = list((root / "src").glob("*/manifest.toml"))
    assert len(manifests) == 1

    manifest_path = manifests[0]
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    extension = manifest["extension"]

    assert extension["identifier"] == manifest_path.parent.name
    assert extension["version"] == pyproject["project"]["version"]
