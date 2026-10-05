import atexit
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb013-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.collection_projection import CollectionProjectionService  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.historical_collection import HistoricalCollectionService  # noqa: E402


class CB013CollectionCompletionProjectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb013-")
        self.db_path = Path(self.temp_dir.name) / "collection.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            connection.execute("DELETE FROM historical_album_records")
            connection.execute("DELETE FROM canonical_trophy_unlocks")
            connection.execute("DELETE FROM feed_events")
            connection.execute("DELETE FROM blocks")
            connection.execute("DELETE FROM friendships")
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def membership(self, user_id, album_id):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            ).fetchone()
            return int(row[0])

    def ensure_membership(self, user_id, album_id):
        with self.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, ?)",
                (user_id, album_id),
            )
        return self.membership(user_id, album_id)

    def complete_history(
        self,
        user_id,
        album_id,
        completed_at,
        source_type="inventory_transition",
    ):
        user_album_id = self.ensure_membership(user_id, album_id)
        with self.connection() as connection:
            HistoricalCollectionService(connection).record_first_album_completion(
                user_album_id,
                completed_at=completed_at,
                event_key=f"album-completion:{user_album_id}",
                source_type=source_type,
                source_key=f"cb013:{source_type}:{user_album_id}",
            )
        return user_album_id

    def set_inventory(self, user_id, album_id, quantities):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, 'owned', ?, ?)
                """,
                (
                    (user_id, album_id, code, max(quantity - 1, 0), quantity)
                    for code, quantity in quantities.items()
                ),
            )

    def projection(self, owner=1, viewer=1):
        with self.connection() as connection:
            return CollectionProjectionService(connection).for_user(owner, viewer)

    def test_current_albums_all_remain_operational_and_history_is_additional(self):
        self.set_inventory(1, "vfl", {"1": 1})
        self.complete_history(1, "vfl", "2026-08-18T12:00:00.000000Z")

        html = self.client.get("/sammlung").get_data(as_text=True)

        self.assertEqual(2, html.count("VfL Osnabrück"))
        self.assertLess(
            html.index("VfL Osnabrück"), html.index("Abgeschlossene Alben")
        )
        self.assertIn('href="/album/vfl"', html)
        self.assertIn("Vervollständigt", html)
        self.assertIn("Abgeschlossen am 18.08.2026", html)
        history_html = html[html.index("Abgeschlossene Alben"):]
        for operational_detail in (
            "Doppelte", "fehlende erhältlich", "home-album-progress", "250/250"
        ):
            self.assertNotIn(operational_detail, history_html)

    def test_current_one_hundred_percent_never_reconstructs_history(self):
        self.set_inventory(1, "vfl", {
            str(code): 1 for code in range(1, 251)
        })

        projection = self.projection()
        html = self.client.get("/sammlung").get_data(as_text=True)

        self.assertEqual((), projection.historical_completions)
        self.assertIn("250 von 250 Stickern", html)
        self.assertNotIn("Abgeschlossene Alben", html)
        self.assertNotIn("Vervollständigt", html)

    def test_historical_completion_survives_later_current_state_reduction(self):
        user_album_id = self.complete_history(
            1, "vfl", "2026-08-17T12:00:00.000000Z"
        )
        self.set_inventory(1, "vfl", {"1": 1})

        first = self.projection().historical_completions[0]
        self.set_inventory(1, "vfl", {})
        second = self.projection().historical_completions[0]

        self.assertEqual(user_album_id, first.user_album_id)
        self.assertEqual(first, second)
        self.assertEqual("2026-08-17T12:00:00.000000Z", second.completed_at)

    def test_multiple_completions_sort_by_time_then_stable_membership_id(self):
        vfl_id = self.complete_history(
            1, "vfl", "2026-08-19T10:00:00.000000Z"
        )
        wm_id = self.complete_history(
            1, "wm26", "2026-08-19T10:00:00.000000Z"
        )
        self.complete_history(1, "em24", "2026-08-18T10:00:00.000000Z")

        first = self.projection().historical_completions
        second = self.projection().historical_completions

        self.assertEqual((max(vfl_id, wm_id), min(vfl_id, wm_id)), tuple(
            item.user_album_id for item in first[:2]
        ))
        self.assertEqual("em24", first[-1].album_id)
        self.assertEqual(first, second)

    def test_album_and_profile_privacy_and_blocks_prevent_foreign_leaks(self):
        self.complete_history(2, "vfl", "2026-08-18T12:00:00.000000Z")
        with self.connection() as connection:
            connection.execute(
                "UPDATE users SET profile_privacy='public' WHERE id=2"
            )
            connection.execute(
                "UPDATE user_albums SET visibility='public' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
        self.assertEqual(("vfl",), tuple(
            item.album_id for item in self.projection(2, 1).historical_completions
        ))

        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET visibility='private' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
        self.assertEqual((), self.projection(2, 1).historical_completions)

        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET visibility='public' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=2"
            )
        self.assertEqual((), self.projection(2, 1).historical_completions)

        with self.connection() as connection:
            connection.execute(
                "INSERT INTO friendships (user_low_id, user_high_id) VALUES (1, 2)"
            )
        self.assertEqual(1, len(self.projection(2, 1).historical_completions))

        with self.connection() as connection:
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
            )
        blocked = self.projection(2, 1)
        self.assertEqual((), blocked.current_albums)
        self.assertEqual((), blocked.historical_completions)

    def test_legacy_trophy_and_current_state_are_not_completion_evidence(self):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (1, 'vfl', 'Album vollendet', '2025-01-01 12:00:00')
                """
            )
        self.assertEqual((), self.projection().historical_completions)

    def test_cb003_and_validated_cb004_sources_are_both_canonical(self):
        self.complete_history(
            1, "vfl", "2026-08-19T12:00:00.000000Z",
            "inventory_transition",
        )
        self.complete_history(
            1, "wm26", "2026-08-18T12:00:00.000000Z",
            "validated_trophy",
        )

        completions = self.projection().historical_completions

        self.assertEqual(
            ("inventory_transition", "validated_trophy"),
            tuple(item.completion_source_type for item in completions),
        )

    def test_collection_read_does_not_touch_trophy_feed_or_notifications(self):
        self.complete_history(1, "vfl", "2026-08-19T12:00:00.000000Z")
        with self.connection() as connection:
            before = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in (
                    "canonical_trophy_unlocks", "feed_events", "notifications"
                )
            }
        self.assertEqual(200, self.client.get("/sammlung").status_code)
        with self.connection() as connection:
            after = {
                table: connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in before
            }
        self.assertEqual(before, after)

    def test_cb014_profile_now_consumes_cb013_history_without_changing_statistics(self):
        self.complete_history(2, "vfl", "2026-08-19T12:00:00.000000Z")
        self.set_inventory(2, "vfl", {"1": 1})
        with self.connection() as connection:
            profile = CollectorProfileService(connection).by_user_id(2, 2)

        self.assertEqual(("vfl",), tuple(
            album.album_id for album in profile.current_albums
        ))
        self.assertEqual(("vfl",), tuple(
            album.album_id for album in profile.historical_completions
        ))

    def test_projection_is_read_only_immutable_and_adds_no_migration(self):
        self.complete_history(1, "vfl", "2026-08-19T12:00:00.000000Z")
        before = sha256(self.db_path)

        projection = self.projection()

        self.assertEqual(before, sha256(self.db_path))
        with self.assertRaises(FrozenInstanceError):
            projection.historical_completions[0].name = "Changed"
        self.assertEqual(22, max(item.version for item in load_migrations()))


if __name__ == "__main__":
    unittest.main()
