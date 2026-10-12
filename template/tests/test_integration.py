"""Reusable, isolated CFMS server smoke test.

Set CFMS_SOURCE to the CFMS checkout or its src directory. The test starts
and stops an isolated server without exercising extension business behavior.
"""

import hashlib
import ipaddress
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def fingerprint(path: Path) -> str | None:
    """Record the original server's config/database state."""
    if not path.is_file():
        return None
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def write_test_certificates(runtime: Path) -> Path:
    """Create a short-lived local CA and server certificate for the sandbox."""
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Isolated CFMS test CA")
    ])
    ca = (
        x509
        .CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, True, True, None, None),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf = (
        x509
        .CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, False, False, None, None),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("::1")),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ssl_dir = runtime / "content" / "ssl"
    ca_path = ssl_dir / "integration-ca.pem"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (ssl_dir / "cert.pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    (ssl_dir / "key.pem").write_bytes(
        leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return ca_path


def prepare_runtime(source: Path, destination: Path) -> None:
    """Copy only the server runtime into pytest's temporary directory."""
    destination.mkdir(parents=True)
    for filename in ("main.py", "alembic.ini", "config.toml.sample"):
        shutil.copy2(source / filename, destination / filename)
    for directory in ("include", "maintenance", "alembic"):
        shutil.copytree(
            source / directory,
            destination / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
        )
    (destination / "content" / "logs").mkdir(parents=True)
    (destination / "content" / "ssl").mkdir()
    shutil.copy2(source / "content" / "hello", destination / "content" / "hello")
    shutil.copytree(
        source / "content" / "ssl" / "client",
        destination / "content" / "ssl" / "client",
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )


@dataclass
class IsolatedCfms:
    """Manage a temporary server; future tests can reuse settings and CA."""

    settings: Any
    ca_path: Path
    start_server: Any
    stop_server: Any
    process: Any = None
    logs: Any = None

    def start(self) -> None:
        if self.process is not None:
            raise RuntimeError("CFMS server has already started")
        self.process, self.logs = self.start_server(self.settings)

    def stop(self) -> None:
        if self.process is not None:
            process, logs = self.process, self.logs
            self.process = self.logs = None
            self.stop_server(process, logs)


@pytest.fixture
def isolated_cfms(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Provision CFMS without importing its potentially destructive fixtures."""
    requested = os.environ.get("CFMS_SOURCE")
    if not requested:
        pytest.skip("Set CFMS_SOURCE to enable the CFMS smoke test")

    checkout = Path(requested).resolve()
    source = checkout / "src" if (checkout / "src" / "main.py").is_file() else checkout
    if not (source / "main.py").is_file():
        pytest.fail("CFMS_SOURCE must identify the CFMS checkout or src directory")

    monkeypatch.syspath_prepend(str(source.parent))
    monkeypatch.syspath_prepend(str(source))
    # Import targeted helpers, never the server's conftest.py or whole test suite.
    from tests.support.config import managed_test_config
    from tests.support.server import start_server, stop_server

    original_files = (source / "config.toml", source / "app.db")
    originals = {path: fingerprint(path) for path in original_files}
    runtime = tmp_path / "cfms-runtime" / "src"
    prepare_runtime(source, runtime)

    with managed_test_config(runtime) as settings:
        harness = IsolatedCfms(
            settings=settings,
            ca_path=write_test_certificates(settings.src_dir),
            start_server=start_server,
            stop_server=stop_server,
        )
        try:
            yield harness
        finally:
            try:
                harness.stop()
            finally:
                assert {
                    path: fingerprint(path) for path in original_files
                } == originals, "Original CFMS config/database changed"


def test_cfms_server_smoke(isolated_cfms: IsolatedCfms) -> None:
    """Check only that the isolated server can start and be cleaned up."""
    isolated_cfms.start()
