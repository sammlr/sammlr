"""Restore a Sammlr backup into a new isolated recovery file."""

from __future__ import annotations

import argparse
import json

from App.Database.sqlite_recovery import restore_to_isolated_copy
from App.services.observability import JsonErrorTracker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--recovery", required=True)
    parser.add_argument("--target", type=int, default=12)
    args = parser.parse_args()
    try:
        artifact = restore_to_isolated_copy(
            args.backup, args.recovery, expected_version=args.target
        )
    except Exception as error:
        JsonErrorTracker().capture_exception(error, route="restore", method="OPERATOR")
        return 1
    print(json.dumps({
        "status": "ok",
        "recovery_path": str(artifact.path),
        "sha256": artifact.sha256,
        "version": artifact.version,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
