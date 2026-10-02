import atexit
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb005-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate, rollback  # noqa: E402
from services.inventory_write import InventoryWriteService  # noqa: E402
from services.history_cutover import HistoricalInventoryWriteService  # noqa: E402
from services.trophy_unlocks import (  # noqa: E402
    CanonicalTrophyUnlockService,
    TrophyUnlockError,
)
from trophy_definitions import canonical_album_trophy_definitions  # noqa: E402


class CanonicalTrophyTruthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb005-")
        self.db_path = Path(self.temp_dir.name) / "trophies.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 15)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self, path=None):
        connection = sqlite3.connect(path or self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id

    def scalar(self, statement, parameters=()):
        with self.connect() as connection:
            return connection.execute(statement, parameters).fetchone()[0]

    def user_album_id(self, user_id=1, album_id="vfl"):
        return self.scalar(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        )

    def seed_owned(self, user_id, codes, album_id="vfl", quantities=None):
        quantities = quantities or {}
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        user_id,
                        album_id,
                        str(code),
                        "duplicate" if quantities.get(str(code), 1) > 1 else "owned",
                        max(quantities.get(str(code), 1) - 1, 0),
                        quantities.get(str(code), 1),
                    )
                    for code in codes
                ],
            )

    def unlock_rows(self, user_id=1, album_id="vfl"):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM canonical_trophy_unlocks
                WHERE user_id=? AND album_id=?
                ORDER BY id
                """,
                (user_id, album_id),
            ).fetchall()

    def test_v0015_upgrade_repeat_down_constraints_and_no_backfill(self):
        isolated = Path(self.temp_dir.name) / "v14.db"
        shutil.copy2(REFERENCE_FIXTURE, isolated)
        with self.connect(isolated) as connection:
            migrate(connection, 14)
            legacy_before = connection.execute(
                "SELECT COUNT(*) FROM unlocked_trophies"
            ).fetchone()[0]
            self.assertEqual((15,), migrate(connection, 15))
            self.assertEqual((), migrate(connection, 15))
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks"
            ).fetchone()[0])
            self.assertEqual(legacy_before, connection.execute(
                "SELECT COUNT(*) FROM unlocked_trophies"
            ).fetchone()[0])
            user_album_id = connection.execute(
                "SELECT id FROM user_albums WHERE user_id=1 AND album_id='vfl'"
            ).fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO canonical_trophy_unlocks
                        (event_key, trophy_definition_id, user_album_id,
                         user_id, album_id, trophy_name, unlocked_at,
                         source_type, source_key)
                    VALUES ('bad-owner', 'vfl.chapter.intro.v1', ?, 2,
                            'vfl', 'Intro', '2026-08-16T12:00:00.000000Z',
                            'inventory_transition', 'mutation')
                    """,
                    (user_album_id,),
                )
            self.assertEqual([("ok",)], [
                tuple(row) for row in connection.execute(
                    "PRAGMA integrity_check"
                ).fetchall()
            ])
            self.assertEqual([], connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall())
            self.assertEqual((15,), rollback(connection, 14))
            self.assertEqual(14, current_version(connection))

    def test_catalog_is_explicit_stable_and_excludes_generic_and_em24(self):
        wm26 = canonical_album_trophy_definitions("wm26", 728)
        vfl = canonical_album_trophy_definitions("vfl", 250)
        self.assertEqual((20, 16), (len(wm26), len(vfl)))
        self.assertEqual((), canonical_album_trophy_definitions("em24", 728))
        for album_id, definitions in (("wm26", wm26), ("vfl", vfl)):
            self.assertTrue(all(
                definition["id"].startswith(f"{album_id}.")
                for definition in definitions
            ))
            self.assertEqual(len(definitions), len({
                definition["id"] for definition in definitions
            }))
            self.assertTrue({"Erster Sticker", "Halbzeit", "Endspurt"}.isdisjoint({
                definition["name"] for definition in definitions
            }))

    def test_real_chapter_trigger_persists_and_retry_is_exactly_once(self):
        self.seed_owned(1, (1,))
        timestamp = "2026-08-16T12:00:00.000000Z"
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            writer.add(
                1, "vfl", "2", event_key="chapter:intro:last",
                occurred_at=timestamp,
            )
            writer.add(
                1, "vfl", "2", event_key="chapter:intro:last",
                occurred_at=timestamp,
            )
            connection.commit()
        rows = self.unlock_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("vfl.chapter.intro.v1", rows[0]["trophy_definition_id"])
        self.assertEqual("Intro", rows[0]["trophy_name"])
        self.assertEqual(timestamp, rows[0]["unlocked_at"])
        self.assertEqual("chapter:intro:last", rows[0]["source_key"])
        self.assertEqual("2", rows[0]["trigger_sticker_code"])

    def test_reduction_and_reachievement_keep_original_unlock(self):
        self.seed_owned(1, (1,))
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            writer.add(
                1, "vfl", "2", event_key="intro:first",
                occurred_at="2026-08-16T12:00:00.000000Z",
            )
            writer.remove(1, "vfl", "2", event_key="intro:remove")
            writer.add(
                1, "vfl", "2", event_key="intro:again",
                occurred_at="2026-08-17T12:00:00.000000Z",
            )
            connection.commit()
        rows = self.unlock_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual("2026-08-16T12:00:00.000000Z", rows[0]["unlocked_at"])
        self.assertEqual("intro:first", rows[0]["source_key"])

    def test_completion_trophy_uses_cb003_fact_and_same_timestamp(self):
        self.seed_owned(1, range(1, 250))
        timestamp = "2026-08-16T13:00:00.000000Z"
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "250", event_key="completion:last",
                occurred_at=timestamp,
            )
            connection.commit()
        completion = self.scalar(
            "SELECT COUNT(*) FROM historical_album_records WHERE completed_at IS NOT NULL"
        )
        rows = self.unlock_rows()
        completion_unlock = next(
            row for row in rows
            if row["trophy_definition_id"] == "vfl.completion.v1"
        )
        self.assertEqual(1, completion)
        self.assertEqual(timestamp, completion_unlock["unlocked_at"])
        self.assertEqual("album_completion", completion_unlock["source_type"])
        self.assertEqual(
            f"album-completion:{self.user_album_id()}",
            completion_unlock["source_key"],
        )
        self.assertEqual("250", completion_unlock["trigger_sticker_code"])

    def test_pre_cutover_complete_album_and_legacy_unlock_are_not_backfilled(self):
        self.seed_owned(1, range(1, 251), quantities={"1": 2})
        legacy_before = self.scalar("SELECT COUNT(*) FROM unlocked_trophies")
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "1", event_key="precutover:duplicate"
            )
            connection.commit()
        self.assertEqual(0, len(self.unlock_rows()))
        self.assertEqual(legacy_before, self.scalar(
            "SELECT COUNT(*) FROM unlocked_trophies"
        ))

    def test_ambiguous_trigger_is_persisted_as_null(self):
        self.seed_owned(1, (1,))
        user_album_id = self.user_album_id()
        with self.connect() as connection:
            service = CanonicalTrophyUnlockService(connection)
            before = service.state(user_album_id)
            InventoryWriteService(connection).add(1, "vfl", "2")
            rows = service.evaluate_new_unlocks(
                user_album_id,
                before=before,
                mutation_event_key="ambiguous:batch",
                occurred_at="2026-08-16T14:00:00.000000Z",
                trigger_sticker_code=None,
            )
            connection.commit()
        intro = next(row for row in rows if row.trophy_name == "Intro")
        self.assertIsNone(intro.trigger_sticker_code)

    def test_gets_render_only_persisted_valid_unlocks_and_write_nothing(self):
        self.seed_owned(1, (1, 2))
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type, source_key)
                VALUES ('forged:unknown-definition', 'vfl.unknown.v1', ?, 1,
                        'vfl', 'Nicht im Katalog',
                        '2026-08-16T11:00:00.000000Z',
                        'inventory_transition', 'forged:source')
                """,
                (self.user_album_id(),),
            )
        before = self.scalar("SELECT COUNT(*) FROM canonical_trophy_unlocks")
        album_page = self.client.get("/album/vfl/trophaeen")
        cabinet = self.client.get("/trophaeen")
        forged = self.client.get("/album/vfl?trophy=Intro&trigger=2")
        self.assertEqual((200, 200, 200), (
            album_page.status_code, cabinet.status_code, forged.status_code
        ))
        self.assertNotIn("Intro", album_page.get_data(as_text=True))
        self.assertNotIn("Nicht im Katalog", album_page.get_data(as_text=True))
        self.assertIn("Auszeichnungen: 0", cabinet.get_data(as_text=True))
        self.assertNotIn("Tauschgeschäfte", cabinet.get_data(as_text=True))
        self.assertNotIn("Neue Trophäe freigeschaltet", forged.get_data(as_text=True))
        self.assertEqual(before, self.scalar(
            "SELECT COUNT(*) FROM canonical_trophy_unlocks"
        ))

    def test_persisted_unlock_remains_visible_after_inventory_reduction(self):
        self.seed_owned(1, (1,))
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            writer.add(1, "vfl", "2", event_key="visible:first")
            writer.remove(1, "vfl", "2", event_key="visible:remove")
            connection.commit()
        html = self.client.get("/album/vfl/trophaeen").get_data(as_text=True)
        self.assertIn("Intro", html)
        self.assertIn("Abgestaubt", html)

    def test_global_generic_and_em24_unlocks_are_never_canonical(self):
        self.seed_owned(1, ())
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "1", event_key="no-generic"
            )
            connection.commit()
        self.assertEqual(0, len(self.unlock_rows()))
        self.assertFalse(hasattr(webapp, "check_global_trophy_unlocks"))
        visible = webapp.record_trophy_unlocks(
            "vfl", ["Erster Sticker"], user_id=1,
            silent_reached=["Halbzeit"],
        )
        self.assertEqual([], visible)
        self.assertEqual(0, len(self.unlock_rows()))

    def test_legacy_silent_writer_is_disabled_without_deleting_legacy_data(self):
        legacy_before = self.scalar("SELECT COUNT(*) FROM unlocked_trophies")
        result = webapp.record_trophy_unlocks(
            "vfl", ["Legacy Visible"], user_id=1,
            silent_reached=["Legacy Silent"],
        )
        self.assertEqual([], result)
        self.assertEqual(legacy_before, self.scalar(
            "SELECT COUNT(*) FROM unlocked_trophies"
        ))
        self.assertEqual(0, len(self.unlock_rows()))

    def test_trophy_failure_rolls_back_inventory_history_and_completion(self):
        self.seed_owned(1, range(1, 250))
        with self.connect() as connection:
            writer = HistoricalInventoryWriteService(connection)
            with patch(
                "services.history_cutover.CanonicalTrophyUnlockService."
                "evaluate_new_unlocks",
                side_effect=RuntimeError("forced trophy failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced trophy failure"):
                    writer.add(1, "vfl", "250", event_key="atomic:trophy")
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM stickers
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='250'
                """
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM historical_album_records WHERE completed_at IS NOT NULL"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks"
            ).fetchone()[0])

    def test_state_ownership_and_concurrent_candidates_are_safe(self):
        self.seed_owned(1, (1,))
        user_album_id = self.user_album_id()
        with self.connect() as connection:
            service = CanonicalTrophyUnlockService(connection)
            before = service.state(user_album_id)
            InventoryWriteService(connection).add(1, "vfl", "2")
            connection.commit()
        wrong_before = before.__class__(
            self.user_album_id(2), before.user_id, before.album_id,
            before.achieved_definition_ids,
        )
        with self.connect() as connection:
            with self.assertRaises(TrophyUnlockError):
                CanonicalTrophyUnlockService(connection).evaluate_new_unlocks(
                    user_album_id,
                    before=wrong_before,
                    mutation_event_key="wrong-owner",
                    occurred_at="2026-08-16T15:00:00.000000Z",
                )

        def attempt(_):
            with self.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                result = CanonicalTrophyUnlockService(
                    connection
                ).evaluate_new_unlocks(
                    user_album_id,
                    before=before,
                    mutation_event_key="concurrent:intro",
                    occurred_at="2026-08-16T15:00:00.000000Z",
                    trigger_sticker_code="2",
                )
                connection.commit()
                return sum(unlock.created for unlock in result)

        with ThreadPoolExecutor(max_workers=2) as executor:
            created = list(executor.map(attempt, (1, 2)))
        self.assertEqual(1, sum(created))
        self.assertEqual(1, len(self.unlock_rows()))

    def test_unlock_writes_no_feed_notification_or_legacy_unlock(self):
        self.seed_owned(1, (1,))
        before = {
            table: self.scalar(f"SELECT COUNT(*) FROM {table}")
            for table in ("feed_events", "notifications", "unlocked_trophies")
        }
        with self.connect() as connection:
            HistoricalInventoryWriteService(connection).add(
                1, "vfl", "2", event_key="no-side-effects"
            )
            connection.commit()
        after = {
            table: self.scalar(f"SELECT COUNT(*) FROM {table}")
            for table in before
        }
        self.assertEqual(before, after)
        self.assertEqual(1, len(self.unlock_rows()))


if __name__ == "__main__":
    unittest.main()
