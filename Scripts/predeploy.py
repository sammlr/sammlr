"""Fail-closed Sammlr production backup, migration, and integrity gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

from App.Database.migration_runner import migrate
from App.Database.sqlite_recovery import create_backup, validate_artifact
from App.services.observability import JsonErrorTracker
from App.services.runtime_operations import (
    EXPECTED_SCHEMA_VERSION,
    PRODUCTION_DATABASE_PATH,
    RuntimeConfigurationError,
    validate_production_environment,
)


PRODUCTION_BACKUP_DIRECTORY = Path("/var/data/backups")


def run_predeploy(
    database_path: str | Path,
    backup_directory: str | Path,
    *,
    target_version: int = EXPECTED_SCHEMA_VERSION,
) -> dict:
    database = Path(database_path).expanduser().resolve()
    backup = create_backup(database, backup_directory)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        changed = migrate(connection, target_version=target_version)
    validated = validate_artifact(database, expected_version=target_version)
    return {
        "status": "ok",
        "backup_path": str(backup.path),
        "backup_sha256": backup.sha256,
        "backup_version": backup.version,
        "database_version": validated.version,
        "applied_migrations": list(changed),
    }


def main() -> int:
    try:
        database = validate_production_environment(os.environ)
        if database != PRODUCTION_DATABASE_PATH:
            raise RuntimeConfigurationError("production database path is invalid")
        result = run_predeploy(database, PRODUCTION_BACKUP_DIRECTORY)
    except Exception as error:
        JsonErrorTracker().capture_exception(
            error, route="predeploy", method="OPERATOR"
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
