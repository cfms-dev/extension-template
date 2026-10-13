"""Exercise version synchronization and release packaging without CFMS."""

import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def release_project(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "scripts", tmp_path / "scripts")
    package = tmp_path / "src" / "ext_sample"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "ext-sample"\nversion = "1.2.3"\n', encoding="utf-8"
    )
    (package / "manifest.toml").write_text(
        'manifest_version = 3\n\n[extension]\nidentifier = "ext_sample"\n'
        "version = '0.1.0' # Initial version\nname = \"Sample\"\n"
        '\n[compatibility]\nminimum_server_version = "0.11.1"\n'
        '\n[dependencies.extensions.other]\nversion = "9.8.7"\n',
        encoding="utf-8",
    )
    for name in ("__init__.py", "_extension.py"):
        (package / name).write_text('"""Sample module."""\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    return tmp_path


def run_script(root: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / script), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_sync_preserves_metadata_and_is_idempotent(release_project: Path) -> None:
    manifest = release_project / "src" / "ext_sample" / "manifest.toml"
    original = manifest.read_text(encoding="utf-8")
    result = run_script(release_project, "sync_version.py")
    assert result.returncode == 0, result.stderr
    expected = original.replace("version = '0.1.0'", 'version = "1.2.3"')
    assert manifest.read_text(encoding="utf-8") == expected
    result = run_script(release_project, "sync_version.py")
    assert result.returncode == 0, result.stderr
    assert manifest.read_text(encoding="utf-8") == expected


def test_build_synchronizes_and_validates_archive(release_project: Path) -> None:
    result = run_script(release_project, "build_extension.py")
    assert result.returncode == 0, result.stderr
    archive_path = release_project / "dist" / "ext_sample-1.2.3.zip"
    first_archive = archive_path.read_bytes()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = tomllib.loads(archive.read("manifest.toml").decode("utf-8"))
        assert manifest["extension"]["version"] == "1.2.3"
        assert "README.md" in archive.namelist()
    result = run_script(release_project, "check_release.py", "v1.2.3", "--archive")
    assert result.returncode == 0, result.stderr
    result = run_script(release_project, "build_extension.py")
    assert result.returncode == 0, result.stderr
    assert archive_path.read_bytes() == first_archive
    archive_path.with_suffix(".zip.sha256").write_text("invalid\n", encoding="ascii")
    result = run_script(release_project, "check_release.py", "v1.2.3", "--archive")
    assert result.returncode != 0
    assert "Invalid SHA-256 checksum" in result.stderr


def test_release_rejects_wrong_tag_and_stale_manifest(release_project: Path) -> None:
    result = run_script(release_project, "check_release.py", "v1.2.3")
    assert result.returncode != 0
    assert "does not match manifest.toml" in result.stderr
    result = run_script(release_project, "sync_version.py")
    assert result.returncode == 0, result.stderr
    for tag in ("v1.2.4", "1.2.3", "v1.2.3-rc1"):
        result = run_script(release_project, "check_release.py", tag)
        assert result.returncode != 0
