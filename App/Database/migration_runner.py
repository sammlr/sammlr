"""Versioned SQLite migrations for controlled Sammlr schema changes.

The runner never selects a database implicitly. Callers must provide an open
connection or an explicit database path through the command line interface.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sqlite3
from typing import Iterable


MIGRATIONS_DIR = Path(__file__).with_name("migrations")
MIGRATION_NAME = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.up\.sql$")


class MigrationError(RuntimeError):
    """Base error for an invalid or failed migration plan."""


class MigrationDriftError(MigrationError):
    """An already applied migration no longer matches its source files."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up_sql: str
    down_sql: str
    checksum: str


@dataclass(frozen=True)
class AppliedMigration:
    version: int
    name: str
    checksum: str


def _checksum(up_sql: str, down_sql: str) -> str:
    content = f"{up_sql}\0{down_sql}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def load_migrations(directory: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    migrations = []
    for up_path in sorted(directory.glob("*.up.sql")):
        match = MIGRATION_NAME.fullmatch(up_path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {up_path.name}")

        version = int(match.group("version"))
        name = match.group("name")
        down_path = directory / f"{version:04d}_{name}.down.sql"
        if not down_path.is_file():
            raise MigrationError(f"Missing backout migration: {down_path.name}")

        up_sql = up_path.read_text(encoding="utf-8")
        down_sql = down_path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=version,
                name=name,
                up_sql=up_sql,
                down_sql=down_sql,
                checksum=_checksum(up_sql, down_sql),
            )
        )

    versions = [migration.version for migration in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Migration versions must be unique")
    if not migrations:
        raise MigrationError(f"No migrations found in {directory}")
    return tuple(migrations)


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _ensure_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def applied_migrations(connection: sqlite3.Connection) -> tuple[AppliedMigration, ...]:
    if not _table_exists(connection, "schema_migrations"):
        return ()
    rows = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    return tuple(AppliedMigration(int(row[0]), row[1], row[2]) for row in rows)


def current_version(connection: sqlite3.Connection) -> int:
    applied = applied_migrations(connection)
    return applied[-1].version if applied else 0


def _statements(script: str) -> Iterable[str]:
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        raise MigrationError("Migration contains an incomplete SQL statement")


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    for statement in _statements(script):
        connection.execute(statement)


@contextmanager
def _migration_transaction(connection: sqlite3.Connection):
    """Make DDL atomic without committing a caller-owned transaction."""

    if connection.in_transaction:
        savepoint = "sammlr_migration_runner"
        connection.execute(f"SAVEPOINT {savepoint}")
        try:
            yield
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        else:
            connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        return

    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()


def _validate_applied(
    available: tuple[Migration, ...], applied: tuple[AppliedMigration, ...]
) -> None:
    by_version = {migration.version: migration for migration in available}
    for record in applied:
        migration = by_version.get(record.version)
        if migration is None:
            raise MigrationDriftError(
                f"Applied migration {record.version:04d} has no source file"
            )
        if record.name != migration.name or record.checksum != migration.checksum:
            raise MigrationDriftError(
                f"Applied migration {record.version:04d} differs from its source"
            )


def migrate(
    connection: sqlite3.Connection,
    target_version: int | None = None,
    directory: Path = MIGRATIONS_DIR,
) -> tuple[int, ...]:
    """Apply pending migrations through ``target_version`` exactly once."""

    available = load_migrations(directory)
    latest = available[-1].version
    target = latest if target_version is None else target_version
    if target < 0 or target > latest:
        raise MigrationError(f"Target version {target} is outside 0..{latest}")

    applied = applied_migrations(connection)
    _validate_applied(available, applied)
    current = applied[-1].version if applied else 0
    if target < current:
        raise MigrationError("Use rollback() for a lower target version")

    pending = tuple(
        migration for migration in available if current < migration.version <= target
    )
    if not pending:
        return ()

    with _migration_transaction(connection):
        _ensure_ledger(connection)
        for migration in pending:
            _execute_script(connection, migration.up_sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, checksum) VALUES (?, ?, ?)",
                (migration.version, migration.name, migration.checksum),
            )
    return tuple(migration.version for migration in pending)


def rollback(
    connection: sqlite3.Connection,
    target_version: int = 0,
    directory: Path = MIGRATIONS_DIR,
) -> tuple[int, ...]:
    """Back out applied migrations down to ``target_version``."""

    if target_version < 0:
        raise MigrationError("Target version must not be negative")
    available = load_migrations(directory)
    applied = applied_migrations(connection)
    _validate_applied(available, applied)
    current = applied[-1].version if applied else 0
    if target_version > current:
        raise MigrationError("Use migrate() for a higher target version")

    by_version = {migration.version: migration for migration in available}
    selected = tuple(
        by_version[record.version]
        for record in reversed(applied)
        if record.version > target_version
    )
    if not selected:
        return ()

    with _migration_transaction(connection):
        for migration in selected:
            _execute_script(connection, migration.down_sql)
            connection.execute(
                "DELETE FROM schema_migrations WHERE version=?",
                (migration.version,),
            )
        if target_version == 0:
            connection.execute("DROP TABLE schema_migrations")
    return tuple(migration.version for migration in selected)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Sammlr schema migrations")
    parser.add_argument("direction", choices=("up", "down"))
    parser.add_argument("--database", required=True, help="Explicit SQLite database path")
    parser.add_argument("--target", type=int, help="Target migration version")
    args = parser.parse_args()

    database_path = Path(args.database).expanduser().resolve()
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        if args.direction == "up":
            changed = migrate(connection, target_version=args.target)
        else:
            changed = rollback(
                connection,
                target_version=0 if args.target is None else args.target,
            )
        version = current_version(connection)
    print(f"Applied change set: {changed}; current version: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
