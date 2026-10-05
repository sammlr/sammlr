"""Fail-closed runtime and SQLite validation contracts for S34."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
from typing import Mapping


EXPECTED_SCHEMA_VERSION = 20
TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS = (20, 21, 22)
PRODUCTION_DATABASE_PATH = Path("/var/data/sammlr.db")


class RuntimeConfigurationError(RuntimeError):
    """Raised when the production runtime contract is incomplete or unsafe."""


@dataclass(frozen=True)
class DatabaseValidation:
    path: Path
    version: int
    sha256: str | None = None


def schema_version(connection: sqlite3.Connection) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if exists is None:
        return 0
    row = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()
    return int(row[0])


def open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def validate_database(
    path: str | Path,
    *,
    expected_version: int = EXPECTED_SCHEMA_VERSION,
    full_integrity: bool = False,
    compatible_versions: tuple[int, ...] | None = None,
) -> DatabaseValidation:
    database_path = Path(path).expanduser().resolve()
    if not database_path.is_file():
        raise RuntimeConfigurationError("configured database is not available")
    try:
        with open_read_only(database_path) as connection:
            connection.execute("SELECT 1").fetchone()
            version = schema_version(connection)
            if version not in (compatible_versions or (expected_version,)):
                raise RuntimeConfigurationError("database migration level is invalid")
            if full_integrity:
                integrity = connection.execute("PRAGMA integrity_check").fetchall()
                if integrity != [("ok",)]:
                    raise RuntimeConfigurationError("database integrity check failed")
                if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise RuntimeConfigurationError("database foreign key check failed")
    except RuntimeConfigurationError:
        raise
    except sqlite3.Error as error:
        raise RuntimeConfigurationError("configured database cannot be opened") from error
    return DatabaseValidation(database_path, version)


def validate_production_environment(
    environment: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    if values.get("SAMMLR_ENV") != "production":
        raise RuntimeConfigurationError("SAMMLR_ENV must be production")
    if not values.get("SAMMLR_SECRET_KEY"):
        raise RuntimeConfigurationError("SAMMLR_SECRET_KEY is required")
    raw_database_path = values.get("DATABASE_PATH", "")
    database_path = Path(raw_database_path) if raw_database_path else Path(".")
    if not database_path.is_absolute() or database_path != PRODUCTION_DATABASE_PATH:
        raise RuntimeConfigurationError("DATABASE_PATH must use the production volume")
    if not values.get("PORT"):
        raise RuntimeConfigurationError("PORT is required")
    return database_path
