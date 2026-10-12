import hashlib
import tomllib
import zipfile
from pathlib import Path

from _project import discover_extension


def build(root: Path) -> Path:
    package = discover_extension(root)[0]
    manifest = tomllib.loads((package / "manifest.toml").read_text(encoding="utf-8"))

    output = root / "dist" / f"{package.name}-{manifest['extension']['version']}.zip"
    output.parent.mkdir(exist_ok=True)
    members = [
        (path, path.relative_to(package).as_posix())
        for path in package.rglob("*")
        if path.is_file()
        and (path.suffix in (".py", ".toml"))
        and "__pycache__" not in path.parts
    ]
    members.extend(
        (root / path, path)
        for path in ("README.md", "LICENSE", "config.example.toml", "docs/FORMAT.md")
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in sorted(members, key=lambda pair: pair[1]):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with output.open("rb") as package_file:
        digest = hashlib.file_digest(package_file, "sha256").hexdigest()
    output.with_suffix(".zip.sha256").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )
    print(f"{output}\nSHA-256: {digest}")
    return output


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
