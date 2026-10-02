"""Controlled CB-004 legacy Trophy audit and backfill operation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.legacy_trophy_backfill import (  # noqa: E402
    ValidatedLegacyTrophyBackfillService,
)


def run(database_path, *, apply=False):
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("explicit database path does not exist")
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        service = ValidatedLegacyTrophyBackfillService(connection)
        result = service.apply() if apply else service.audit()
        return result.to_dict()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit legacy trophies; writes require explicit --apply"
    )
    parser.add_argument("--database", required=True, help="explicit SQLite database")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply only candidates announced by the same validated audit",
    )
    args = parser.parse_args(argv)
    try:
        document = run(args.database, apply=args.apply)
    except Exception as error:
        print(json.dumps({
            "status": "error",
            "error_type": type(error).__name__,
            "message": str(error),
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(
        {"status": "ok", **document},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
