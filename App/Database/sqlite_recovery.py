"""Consistent SQLite backup, validation, retention, and isolated restore."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3

from App.services.runtime_operations import (
    EXPECTED_SCHEMA_VERSION,
    RuntimeConfigurationError,
    schema_version,
)


BACKUP_NAME = re.compile(r"^sammlr-\d{8}-\d{6}-v\d{4}\.db$")


@dataclass(frozen=True)
class SqliteArtifact:
    path: Path
    sha256: str
    version: int


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exclusive_private_file(path: Path) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)


def _sqlite_backup(
    source: Path, destination: Path, *, secure_directory: bool = False
) -> None:
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination must be different")
    if not source.is_file():
        raise FileNotFoundError("source database is not available")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if secure_directory:
        os.chmod(destination.parent, 0o700)
    _exclusive_private_file(destination)
    try:
        source_uri = source.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source_connection:
            with sqlite3.connect(destination) as destination_connection:
                source_connection.backup(destination_connection)
        os.chmod(destination, 0o600)
    except Exception:
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise


def validate_artifact(
    path: str | Path,
    *,
    expected_version: int | None = EXPECTED_SCHEMA_VERSION,
) -> SqliteArtifact:
    artifact_path = Path(path).expanduser().resolve()
    if not artifact_path.is_file():
        raise RuntimeConfigurationError("SQLite artifact is not available")
    try:
        with sqlite3.connect(artifact_path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            version = schema_version(connection)
            if expected_version is not None and version != expected_version:
                raise RuntimeConfigurationError("SQLite artifact has invalid migration level")
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeConfigurationError("SQLite artifact integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeConfigurationError("SQLite artifact foreign key check failed")
    except RuntimeConfigurationError:
        raise
    except sqlite3.Error as error:
        raise RuntimeConfigurationError("SQLite artifact cannot be opened") from error
    return SqliteArtifact(artifact_path, sha256_file(artifact_path), version)


def create_backup(
    database_path: str | Path,
    backup_directory: str | Path,
    *,
    now: datetime | None = None,
) -> SqliteArtifact:
    source = Path(database_path).expanduser().resolve()
    timestamp = now or datetime.now(timezone.utc)
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        version = schema_version(connection)
    destination = Path(backup_directory).expanduser().resolve() / (
        f"sammlr-{timestamp:%Y%m%d-%H%M%S}-v{version:04d}.db"
    )
    _sqlite_backup(source, destination, secure_directory=True)
    return validate_artifact(destination, expected_version=version)


def restore_to_isolated_copy(
    backup_path: str | Path,
    recovery_path: str | Path,
    *,
    expected_version: int = EXPECTED_SCHEMA_VERSION,
) -> SqliteArtifact:
    backup = validate_artifact(backup_path, expected_version=expected_version)
    destination = Path(recovery_path).expanduser().resolve()
    _sqlite_backup(backup.path, destination)
    return validate_artifact(destination, expected_version=expected_version)


def prune_expired_backups(
    backup_directory: str | Path,
    *,
    retention_days: int = 30,
    now: datetime | None = None,
) -> tuple[Path, ...]:
    directory = Path(backup_directory).expanduser().resolve()
    if not directory.is_dir():
        return ()
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=retention_days)
    removed = []
    for candidate in directory.iterdir():
        if not candidate.is_file() or BACKUP_NAME.fullmatch(candidate.name) is None:
            continue
        modified = datetime.fromtimestamp(candidate.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            candidate.unlink()
            removed.append(candidate)
    return tuple(sorted(removed))
