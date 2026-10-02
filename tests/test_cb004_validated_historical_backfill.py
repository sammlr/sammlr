import atexit
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
SCRIPT = PROJECT_ROOT / "Scripts" / "cb004_validated_trophy_backfill.py"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path):
    with sqlite3.connect(path) as connection:
        return "\n".join(connection.iterdump())


sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

from App.Database.migration_runner import current_version, migrate, rollback  # noqa: E402
from services.historical_collection import HistoricalCollectionService  # noqa: E402
from services.legacy_trophy_backfill import (  # noqa: E402
    AMBIGUOUS,
    BOTH,
    CANONICAL_TROPHY,
    HISTORICAL_COMPLETION,
    INVALID,
    LEGACY_GENERIC,
    LEGACY_GLOBAL,
    NONE,
    NO_CANONICAL_CATALOG,
    VALID_BOTH,
    VALID_CANONICAL_TROPHY,
    LegacyTrophyAuditRow,
    ValidatedLegacyTrophyBackfillService,
    normalize_legacy_unlock_timestamp,
)


class ValidatedHistoricalBackfillTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb004-")
        self.db_path = Path(self.temp_dir.name) / "backfill.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 16)
            connection.execute("DELETE FROM unlocked_trophies")
            connection.execute("DELETE FROM canonical_trophy_unlocks")
            connection.execute("DELETE FROM historical_album_records")

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self, path=None):
        connection = sqlite3.connect(path or self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def membership(self, user_id=1, album_id="vfl"):
        with self.connect() as connection:
            return connection.execute(
                "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            ).fetchone()[0]

    def legacy(self, user_id, album_id, name, timestamp="2026-07-01 12:00:00"):
        with self.connect() as connection:
            inserted = connection.execute(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, album_id, name, timestamp),
            )
            return inserted.lastrowid

    def audit(self, *, now=None):
        with self.connect() as connection:
            return ValidatedLegacyTrophyBackfillService(connection).audit(
                now=now or datetime(2026, 8, 18, tzinfo=timezone.utc)
            )

    def test_v0016_upgrade_repeat_down_and_preserves_v0015_rows(self):
        isolated = Path(self.temp_dir.name) / "v15.db"
        shutil.copy2(REFERENCE_FIXTURE, isolated)
        with self.connect(isolated) as connection:
            migrate(connection, 15)
            user_album_id = connection.execute(
                "SELECT id FROM user_albums WHERE user_id=1 AND album_id='vfl'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type, source_key)
                VALUES ('existing-live', 'vfl.chapter.intro.v1', ?, 1,
                        'vfl', 'Intro', '2026-08-01T10:00:00.000000Z',
                        'inventory_transition', 'live-source')
                """,
                (user_album_id,),
            )
            self.assertEqual((16,), migrate(connection, 16))
            self.assertEqual((), migrate(connection, 16))
            self.assertEqual("existing-live", connection.execute(
                "SELECT event_key FROM canonical_trophy_unlocks"
            ).fetchone()[0])
            connection.execute(
                """
                INSERT INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type, source_key)
                VALUES ('backfill-source-check', 'vfl.special.dj_matze.v1', ?, 1,
                        'vfl', 'DJ Matze', '2026-07-01T10:00:00.000000Z',
                        'legacy_trophy_backfill', 'legacy-trophy:77')
                """,
                (user_album_id,),
            )
            connection.execute(
                "DELETE FROM canonical_trophy_unlocks WHERE event_key='backfill-source-check'"
            )
            self.assertEqual([("ok",)], [
                tuple(row) for row in connection.execute("PRAGMA integrity_check")
            ])
            self.assertEqual([], connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall())
            self.assertEqual((16,), rollback(connection, 15))
            self.assertEqual(15, current_version(connection))
            self.assertEqual("existing-live", connection.execute(
                "SELECT event_key FROM canonical_trophy_unlocks"
            ).fetchone()[0])

    def test_exact_wm26_and_vfl_names_are_deterministic_candidates(self):
        wm_id = self.legacy(1, "wm26", "Wappenexperte")
        vfl_id = self.legacy(1, "vfl", "Intro", "2026-07-01T14:00:00+02:00")
        rows = {row.legacy_row_id: row for row in self.audit().rows}
        self.assertEqual(VALID_CANONICAL_TROPHY, rows[wm_id].category)
        self.assertEqual("wm26.series.crests.v1", rows[wm_id].canonical_trophy_definition_id)
        self.assertEqual(CANONICAL_TROPHY, rows[wm_id].allowed_backfill)
        self.assertEqual("vfl.chapter.intro.v1", rows[vfl_id].canonical_trophy_definition_id)
        self.assertEqual("2026-07-01T12:00:00.000000Z", rows[vfl_id].normalized_unlocked_at)

    def test_global_generic_unknown_and_catalogless_rows_are_rejected(self):
        ids = {
            "global": self.legacy(1, "__global__", "Stickerjäger 50"),
            "generic": self.legacy(1, "vfl", "Halbzeit"),
            "unknown": self.legacy(1, "vfl", "Fast wie Intro"),
            "em24": self.legacy(1, "em24", "Album vollendet"),
        }
        rows = {row.legacy_row_id: row for row in self.audit().rows}
        self.assertEqual(LEGACY_GLOBAL, rows[ids["global"]].category)
        self.assertEqual(LEGACY_GENERIC, rows[ids["generic"]].category)
        self.assertEqual(AMBIGUOUS, rows[ids["unknown"]].category)
        self.assertEqual(NO_CANONICAL_CATALOG, rows[ids["em24"]].category)
        self.assertTrue(all(rows[row_id].allowed_backfill == NONE for row_id in ids.values()))
        self.assertIsNone(rows[ids["em24"]].canonical_trophy_definition_id)

    def test_completion_evidence_is_valid_both_and_current_state_is_never_used(self):
        completion_id = self.legacy(1, "vfl", "Album vollendet")
        with self.connect() as connection:
            connection.execute("DELETE FROM stickers WHERE user_id=2 AND album_id='vfl'")
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (2, 'vfl', ?, 'owned', 0, 1)
                """,
                [(str(number),) for number in range(1, 251)],
            )
        audit = self.audit()
        row = next(row for row in audit.rows if row.legacy_row_id == completion_id)
        self.assertEqual(VALID_BOTH, row.category)
        self.assertEqual(BOTH, row.allowed_backfill)
        self.assertEqual(1, len(audit.completion_candidates))
        self.assertFalse(any(row.user_id == 2 for row in audit.completion_candidates))

    def test_missing_ambiguous_and_future_timestamps_are_invalid(self):
        missing_id = self.legacy(1, "vfl", "Intro", None)
        ambiguous_id = self.legacy(1, "vfl", "DJ Matze", "2026-07-01T12:00:00")
        future_id = self.legacy(1, "wm26", "Intro", "2027-01-01T00:00:00Z")
        rows = {row.legacy_row_id: row for row in self.audit().rows}
        for row_id in (missing_id, ambiguous_id, future_id):
            self.assertEqual(INVALID, rows[row_id].category)
            self.assertEqual(NONE, rows[row_id].allowed_backfill)
        normalized, error = normalize_legacy_unlock_timestamp(
            "2026-07-01 12:00:00",
            now=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )
        self.assertEqual("2026-07-01T12:00:00.000000Z", normalized)
        self.assertIsNone(error)

    def test_missing_user_album_fails_ownership_validation(self):
        inserted = self.legacy(3, "vfl", "Intro")
        row = next(row for row in self.audit().rows if row.legacy_row_id == inserted)
        self.assertEqual(INVALID, row.category)
        self.assertIsNone(row.user_album_id)
        self.assertEqual(NONE, row.allowed_backfill)

    def test_dry_run_is_read_only_and_reports_each_row_once(self):
        self.legacy(1, "vfl", "Intro")
        self.legacy(1, "wm26", "Gruppe A")
        self.legacy(1, "__global__", "Stickerjäger 50")
        before = dump(self.db_path)
        first = self.audit()
        second = self.audit()
        self.assertEqual(before, dump(self.db_path))
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(3, first.legacy_total)
        self.assertEqual(3, len({row.legacy_row_id for row in first.rows}))
        self.assertEqual(2, first.summary()["canonical_trophy_candidates"])

    def test_apply_creates_only_announced_rows_and_repeat_creates_zero(self):
        intro_id = self.legacy(1, "vfl", "Intro")
        completion_id = self.legacy(
            1, "vfl", "Album vollendet", "2026-07-02 13:14:15"
        )
        self.legacy(1, "vfl", "Erster Sticker")
        self.legacy(1, "__global__", "Stickerjäger 50")
        with self.connect() as connection:
            service = ValidatedLegacyTrophyBackfillService(connection)
            announced = service.audit(now=datetime(2026, 8, 18, tzinfo=timezone.utc))
            first = service.apply(now=datetime(2026, 8, 18, tzinfo=timezone.utc))
            second = service.apply(now=datetime(2026, 8, 18, tzinfo=timezone.utc))
            trophies = connection.execute(
                "SELECT * FROM canonical_trophy_unlocks ORDER BY trophy_definition_id"
            ).fetchall()
            completion = connection.execute(
                "SELECT * FROM historical_album_records WHERE user_album_id=?",
                (self.membership(),),
            ).fetchone()
        self.assertEqual(2, len(announced.trophy_candidates))
        self.assertEqual(1, len(announced.completion_candidates))
        self.assertEqual((2, 1), (
            first.created_canonical_trophies,
            first.created_historical_completions,
        ))
        self.assertEqual((0, 0), (
            second.created_canonical_trophies,
            second.created_historical_completions,
        ))
        self.assertEqual(2, len(trophies))
        self.assertTrue(all(row["source_type"] == "legacy_trophy_backfill" for row in trophies))
        self.assertTrue(all(row["trigger_sticker_code"] is None for row in trophies))
        self.assertEqual(
            {f"legacy-trophy:{intro_id}", f"legacy-trophy:{completion_id}"},
            {row["source_key"] for row in trophies},
        )
        self.assertEqual("2026-07-02T13:14:15.000000Z", completion["completed_at"])
        self.assertEqual("validated_trophy", completion["completion_source_type"])
        self.assertEqual(f"legacy-trophy:{completion_id}", completion["completion_source_key"])

    def test_matching_existing_facts_win_and_are_not_overwritten(self):
        intro_id = self.legacy(1, "vfl", "Intro")
        completion_id = self.legacy(1, "vfl", "Album vollendet")
        user_album_id = self.membership()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type, source_key,
                     trigger_sticker_code)
                VALUES ('live:intro', 'vfl.chapter.intro.v1', ?, 1, 'vfl',
                        'Intro', '2026-07-01T12:00:00.000000Z',
                        'inventory_transition', 'live:source', '2')
                """,
                (user_album_id,),
            )
            HistoricalCollectionService(connection).record_first_album_completion(
                user_album_id,
                completed_at="2026-07-01T12:00:00.000000Z",
                event_key="album-completion:live",
                source_type="inventory_transition",
                source_key="live:completion",
            )
            audit = ValidatedLegacyTrophyBackfillService(connection).audit(
                now=datetime(2026, 8, 18, tzinfo=timezone.utc)
            )
            result = ValidatedLegacyTrophyBackfillService(connection).apply(
                now=datetime(2026, 8, 18, tzinfo=timezone.utc)
            )
        rows = {row.legacy_row_id: row for row in audit.rows}
        self.assertEqual("ALREADY_PRESENT", rows[intro_id].validation_status)
        self.assertEqual("ELIGIBLE", rows[completion_id].validation_status)
        self.assertEqual(NONE, rows[intro_id].allowed_backfill)
        self.assertEqual(CANONICAL_TROPHY, rows[completion_id].allowed_backfill)
        self.assertEqual((1, 0), (
            result.created_canonical_trophies,
            result.created_historical_completions,
        ))
        with self.connect() as connection:
            persisted = connection.execute(
                """
                SELECT completed_at, completion_event_key,
                       completion_source_type, completion_source_key
                FROM historical_album_records WHERE user_album_id=?
                """,
                (user_album_id,),
            ).fetchone()
        self.assertEqual(
            (
                "2026-07-01T12:00:00.000000Z",
                "album-completion:live",
                "inventory_transition",
                "live:completion",
            ),
            tuple(persisted),
        )

    def test_conflicting_canonical_trophy_or_completion_blocks_row(self):
        intro_id = self.legacy(1, "vfl", "Intro")
        completion_id = self.legacy(1, "vfl", "Album vollendet")
        user_album_id = self.membership()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type, source_key)
                VALUES ('live:intro', 'vfl.chapter.intro.v1', ?, 1, 'vfl',
                        'Intro', '2026-08-01T12:00:00.000000Z',
                        'inventory_transition', 'live:source')
                """,
                (user_album_id,),
            )
            HistoricalCollectionService(connection).record_first_album_completion(
                user_album_id,
                completed_at="2026-08-01T12:00:00.000000Z",
                event_key="album-completion:live",
                source_type="inventory_transition",
                source_key="live:completion",
            )
        rows = {row.legacy_row_id: row for row in self.audit().rows}
        self.assertEqual("CONFLICT", rows[intro_id].validation_status)
        self.assertEqual("CONFLICT", rows[completion_id].validation_status)
        self.assertEqual(NONE, rows[intro_id].allowed_backfill)
        self.assertEqual(NONE, rows[completion_id].allowed_backfill)

    def test_conflicting_legacy_evidence_blocks_every_automatic_write(self):
        rows = ValidatedLegacyTrophyBackfillService._reconcile_duplicate_evidence((
            self.audit_row(1, "2026-07-01T12:00:00.000000Z"),
            self.audit_row(2, "2026-07-02T12:00:00.000000Z"),
        ))
        self.assertTrue(all(row.validation_status == "CONFLICT" for row in rows))
        self.assertTrue(all(row.allowed_backfill == NONE for row in rows))

    def test_identical_duplicate_evidence_has_one_deterministic_candidate(self):
        rows = ValidatedLegacyTrophyBackfillService._reconcile_duplicate_evidence((
            self.audit_row(1, "2026-07-01T12:00:00.000000Z"),
            self.audit_row(2, "2026-07-01T12:00:00.000000Z"),
        ))
        self.assertEqual(CANONICAL_TROPHY, rows[0].allowed_backfill)
        self.assertEqual("REDUNDANT_EVIDENCE", rows[1].validation_status)
        self.assertEqual(NONE, rows[1].allowed_backfill)

    @staticmethod
    def audit_row(row_id, timestamp):
        return LegacyTrophyAuditRow(
            legacy_row_id=row_id,
            user_id=1,
            album_id="vfl",
            user_album_id=1,
            legacy_trophy_name="Intro",
            legacy_unlocked_at=timestamp,
            normalized_unlocked_at=timestamp,
            canonical_trophy_definition_id="vfl.chapter.intro.v1",
            trophy_type="normal_album",
            category=VALID_CANONICAL_TROPHY,
            validation_status="ELIGIBLE",
            reason="test candidate",
            allowed_backfill=CANONICAL_TROPHY,
        )

    def test_apply_changes_only_canonical_trophy_and_completion_tables(self):
        self.legacy(1, "vfl", "Intro")
        self.legacy(1, "vfl", "Album vollendet")
        protected = (
            "users", "user_albums", "stickers", "trade_requests", "trades",
            "trade_positions", "unlocked_trophies", "notifications", "feed_events",
        )
        with self.connect() as connection:
            before = {
                table: [tuple(row) for row in connection.execute(
                    f"SELECT * FROM {table} ORDER BY rowid"
                ).fetchall()]
                for table in protected
            }
            result = ValidatedLegacyTrophyBackfillService(connection).apply(
                now=datetime(2026, 8, 18, tzinfo=timezone.utc)
            )
            after = {
                table: [tuple(row) for row in connection.execute(
                    f"SELECT * FROM {table} ORDER BY rowid"
                ).fetchall()]
                for table in protected
            }
            self.assertEqual([("ok",)], [
                tuple(row) for row in connection.execute("PRAGMA integrity_check")
            ])
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())
        self.assertEqual(before, after)
        self.assertEqual((2, 1), (
            result.created_canonical_trophies,
            result.created_historical_completions,
        ))

    def test_forced_failure_rolls_back_the_entire_apply(self):
        self.legacy(1, "vfl", "Intro")
        self.legacy(1, "wm26", "Gruppe A")
        before = dump(self.db_path)
        with self.connect() as connection:
            service = ValidatedLegacyTrophyBackfillService(connection)
            with patch.object(
                service, "_record_trophy",
                wraps=service._record_trophy,
            ) as writer:
                def fail_second(row):
                    if writer.call_count == 2:
                        raise RuntimeError("forced CB-004 failure")
                    return writer._mock_wraps(row)

                writer.side_effect = fail_second
                with self.assertRaisesRegex(RuntimeError, "forced CB-004 failure"):
                    service.apply(now=datetime(2026, 8, 18, tzinfo=timezone.utc))
        self.assertEqual(before, dump(self.db_path))

    def test_cli_defaults_to_dry_run_and_requires_explicit_apply(self):
        self.legacy(1, "vfl", "Intro")
        environment = os.environ.copy()
        dry = subprocess.run(
            [sys.executable, str(SCRIPT), "--database", str(self.db_path)],
            cwd=PROJECT_ROOT, env=environment, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(0, dry.returncode, dry.stderr)
        dry_document = json.loads(dry.stdout)
        self.assertEqual("dry-run", dry_document["mode"])
        with self.connect() as connection:
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks"
            ).fetchone()[0])
        applied = subprocess.run(
            [sys.executable, str(SCRIPT), "--database", str(self.db_path), "--apply"],
            cwd=PROJECT_ROOT, env=environment, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(0, applied.returncode, applied.stderr)
        document = json.loads(applied.stdout)
        self.assertEqual("apply", document["mode"])
        self.assertEqual(1, document["created_canonical_trophies"])


if __name__ == "__main__":
    unittest.main()
