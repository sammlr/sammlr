"""Create and validate a consistent private Sammlr SQLite backup."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from App.Database.sqlite_recovery import create_backup, prune_expired_backups
from App.services.observability import JsonErrorTracker


PRODUCTION_DATABASE = Path("/var/data/sammlr.db")
PRODUCTION_BACKUPS = Path("/var/data/backups")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", default=os.environ.get("DATABASE_PATH", str(PRODUCTION_DATABASE))
    )
    parser.add_argument("--backup-dir", default=str(PRODUCTION_BACKUPS))
    parser.add_argument("--retention-days", type=int, default=30)
    args = parser.parse_args()
    try:
        artifact = create_backup(args.database, args.backup_dir)
        removed = prune_expired_backups(
            args.backup_dir, retention_days=args.retention_days
        )
    except Exception as error:
        JsonErrorTracker().capture_exception(error, route="backup", method="OPERATOR")
        return 1
    print(json.dumps({
        "status": "ok",
        "backup_path": str(artifact.path),
        "sha256": artifact.sha256,
        "version": artifact.version,
        "expired_backups_removed": len(removed),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
