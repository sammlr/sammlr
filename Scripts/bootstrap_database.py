"""Create a new user-free V20 database; never reuse an existing file."""

import argparse
import os
from pathlib import Path
import sqlite3

from App.Database.migration_runner import migrate


ROOT = Path(__file__).resolve().parents[1]


def bootstrap(database: Path) -> None:
    database = database.absolute()
    # Exclusive creation also rejects symlinks and existing empty files.
    descriptor = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(database) as connection:
            connection.executescript(
                (ROOT / "App/Database/base_schema.sql").read_text()
            )
            connection.executescript(
                (ROOT / "App/Database/catalog_seed.sql").read_text()
            )
            connection.execute("PRAGMA foreign_keys=ON")
            migrate(connection, target_version=20)
            if (connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 0
                    or connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
                    or connection.execute("PRAGMA foreign_key_check").fetchall()):
                raise RuntimeError("Bootstrap integrity validation failed")
    except Exception:
        # Only the new file exclusively created by this call is removed.
        database.unlink()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    bootstrap(parser.parse_args().database)
