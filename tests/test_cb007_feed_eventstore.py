import hashlib
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"

sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

from App.Database.migration_runner import current_version, migrate, rollback  # noqa: E402
from services.albums import all_codes  # noqa: E402
from services.feed_events import (  # noqa: E402
    FEED_WORTHY_TROPHY_DEFINITION_IDS,
    FeedEventError,
    FeedEventService,
)
from services.historical_collection import (  # noqa: E402
    HistoricalCollectionError,
    HistoricalCollectionService,
    HistoricalWriteConflict,
)
from services.history_cutover import (  # noqa: E402
    AlbumHistoryCutoverService,
    HistoricalInventoryWriteService,
)
from services.user_data_export import UserDataExportService  # noqa: E402


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FeedEventstoreTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb007-")
        self.db_path = Path(self.temp_dir.name) / "feed.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 18)
            connection.execute("DELETE FROM sammlr_news")
            connection.execute("DELETE FROM feed_events")
            connection.execute("DELETE FROM canonical_trophy_unlocks")
            connection.execute("DELETE FROM historical_album_progress_points")
            connection.execute("DELETE FROM historical_sticker_acquisitions")
            connection.execute("DELETE FROM historical_inventory_mutations")
            connection.execute("DELETE FROM historical_album_records")
            connection.execute("DELETE FROM blocks")
            connection.execute("DELETE FROM friendships")
            connection.execute("DELETE FROM friendship_requests")
            connection.execute(
                "UPDATE users SET account_state='active', profile_privacy='public' "
                "WHERE id IN (1, 2, 3)"
            )
            for user_id in (1, 2, 3):
                connection.execute(
                    """
                    INSERT INTO user_albums
                        (user_id, album_id, visibility, trade_pool_enabled)
                    VALUES (?, 'vfl', 'public', 1)
                    ON CONFLICT(user_id, album_id) DO UPDATE SET
                        visibility='public', trade_pool_enabled=1
                    """,
                    (user_id,),
                )

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connect(self, path=None):
        connection = sqlite3.connect(path or self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def membership(self, connection, user_id=1, album_id="vfl"):
        return int(connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchone()[0])

    def add_event(
        self, connection, user_id, suffix, occurred_at, *, event_type="album_started"
    ):
        user_album_id = self.membership(connection, user_id)
        return HistoricalCollectionService(connection).record_feed_event(
            event_key=f"feed:test:{suffix}",
            event_type=event_type,
            actor_user_id=user_id,
            user_album_id=user_album_id,
            target_type="trophy" if event_type == "trophy_unlocked" else "album",
            target_key="test.definition" if event_type == "trophy_unlocked" else "vfl",
            occurred_at=occurred_at,
        )

    def make_friends(self, connection, first=1, second=2):
        low, high = sorted((first, second))
        connection.execute(
            "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
            (low, high),
        )

    def test_v0018_is_additive_repeatable_and_has_safe_news_backout(self):
        isolated = Path(self.temp_dir.name) / "migration.db"
        shutil.copy2(FIXTURE, isolated)
        with self.connect(isolated) as connection:
            migrate(connection, 17)
            before = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("users", "user_albums", "feed_events", "notifications")
            }
            self.assertEqual((18,), migrate(connection, 18))
            self.assertEqual((), migrate(connection, 18))
            self.assertEqual(18, current_version(connection))
            self.assertEqual(before, {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in before
            })
            indexes = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            self.assertIn("idx_cb007_feed_events_canonical_time", indexes)
            self.assertIn("idx_cb007_news_time", indexes)
            FeedEventService(connection).publish_news(
                "migration-news", title="News", body="Body",
                target_path="/sammlung",
                published_at="2026-08-18T10:00:00.000000Z",
            )
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 17)
            self.assertEqual(18, current_version(connection))
            connection.execute("DELETE FROM sammlr_news")
            connection.execute(
                "DELETE FROM feed_events WHERE event_key='feed:sammlr-news:migration-news'"
            )
            connection.commit()
            self.assertEqual((18,), rollback(connection, 17))
            self.assertEqual(17, current_version(connection))

    def test_persistent_events_deduplicate_and_sort_by_stable_event_key(self):
        with self.connect() as connection:
            first = self.add_event(
                connection, 1, "a", "2026-08-18T10:00:00.000000Z"
            )
            retry = self.add_event(
                connection, 1, "a", "2026-08-18T10:00:00.000000Z"
            )
            self.add_event(connection, 1, "b", "2026-08-18T10:00:00.000000Z")
            self.add_event(connection, 1, "older", "2026-08-18T09:00:00.000000Z")
            self.assertTrue(first.created)
            self.assertFalse(retry.created)
            items = FeedEventService(connection).feed_for_user(1)
            self.assertEqual(
                ["feed:test:b", "feed:test:a", "feed:test:older"],
                [item.event_key for item in items],
            )
            with self.assertRaises(HistoricalWriteConflict):
                self.add_event(connection, 1, "a", "2026-08-18T11:00:00.000000Z")

    def test_friend_profile_album_and_block_policy_is_fail_closed(self):
        with self.connect() as connection:
            self.add_event(connection, 2, "friend", "2026-08-18T10:00:00.000000Z")
            service = FeedEventService(connection)
            self.assertEqual((), service.feed_for_user(1))
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=2"
            )
            self.assertEqual((), service.feed_for_user(1))
            connection.execute(
                "UPDATE users SET profile_privacy='public' WHERE id=2"
            )
            connection.execute(
                """
                INSERT INTO friendship_requests
                    (requester_user_id, recipient_user_id, status)
                VALUES (1, 2, 'pending')
                """
            )
            self.assertEqual((), service.feed_for_user(1))
            connection.execute(
                "UPDATE friendship_requests SET status='accepted'"
            )
            self.assertEqual((), service.feed_for_user(1))
            self.make_friends(connection)
            self.assertEqual(1, len(service.feed_for_user(1)))
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=2"
            )
            self.assertEqual(1, len(service.feed_for_user(1)))
            connection.execute(
                "UPDATE user_albums SET visibility='private' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            self.assertEqual((), service.feed_for_user(1))
            connection.execute(
                "UPDATE user_albums SET visibility='friends' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            self.assertEqual(1, len(service.feed_for_user(1)))
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
            )
            self.assertEqual((), service.feed_for_user(1))
            connection.execute("DELETE FROM blocks")
            connection.execute("DELETE FROM friendships")
            connection.execute(
                "UPDATE users SET profile_privacy='public' WHERE id=2"
            )
            connection.execute(
                "UPDATE user_albums SET visibility='public' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            self.assertEqual((), service.feed_for_user(1))

    def test_owner_private_album_is_visible_and_invalid_viewer_is_closed(self):
        with self.connect() as connection:
            self.add_event(connection, 1, "own", "2026-08-18T10:00:00.000000Z")
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=1"
            )
            connection.execute(
                "UPDATE user_albums SET visibility='private' "
                "WHERE user_id=1 AND album_id='vfl'"
            )
            service = FeedEventService(connection)
            self.assertEqual(1, len(service.feed_for_user(1)))
            self.assertEqual((), service.feed_for_user(999999))
            with self.assertRaises(FeedEventError):
                service.feed_for_user("invalid")

    def test_album_start_producer_is_atomic_and_retry_safe(self):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO albums (id, name, total) VALUES ('cb007', 'CB007', 1)"
            )
            service = AlbumHistoryCutoverService(connection)
            self.assertTrue(service.add(
                1, "cb007", occurred_at="2026-08-18T10:00:00.000000Z"
            ))
            self.assertFalse(service.add(
                1, "cb007", occurred_at="2026-08-18T11:00:00.000000Z"
            ))
            membership = self.membership(connection, 1, "cb007")
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM feed_events WHERE event_key=?",
                (f"feed:album-start:{membership}",),
            ).fetchone()[0])

            connection.execute(
                "INSERT INTO albums (id, name, total) VALUES ('cb007-fail', 'Fail', 1)"
            )
            with mock.patch(
                "services.history_cutover.FeedEventService.record_album_started",
                side_effect=RuntimeError("forced feed failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced feed failure"):
                    service.add(
                        1, "cb007-fail",
                        occurred_at="2026-08-18T12:00:00.000000Z",
                    )
            self.assertIsNone(connection.execute(
                "SELECT id FROM user_albums WHERE user_id=1 AND album_id='cb007-fail'"
            ).fetchone())

    def _prepare_almost_complete_vfl(self, connection, user_id):
        codes = tuple(all_codes("vfl"))
        connection.execute(
            "DELETE FROM stickers WHERE user_id=? AND album_id='vfl'", (user_id,)
        )
        connection.executemany(
            """
            INSERT INTO stickers
                (user_id, album_id, sticker_code, status, duplicates, quantity)
            VALUES (?, 'vfl', ?, 'owned', 0, 1)
            """,
            ((user_id, code) for code in codes[:-1]),
        )
        return codes[-1]

    def test_completion_produces_one_event_and_completion_trophy_no_second_event(self):
        with self.connect() as connection:
            last = self._prepare_almost_complete_vfl(connection, 1)
            mutation = HistoricalInventoryWriteService(connection).set_quantity(
                1, "vfl", last, 1, event_key="cb007:complete",
                occurred_at="2026-08-18T10:00:00.000000Z",
            )
            self.assertTrue(mutation.allowed)
            connection.commit()
            membership = self.membership(connection)
            rows = connection.execute(
                "SELECT event_type, event_key FROM feed_events ORDER BY event_key"
            ).fetchall()
            self.assertEqual([
                ("album_completed", f"feed:album-completion:{membership}")
            ], [tuple(row) for row in rows])
            completion_trophies = connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks "
                "WHERE source_type='album_completion'"
            ).fetchone()[0]
            self.assertGreaterEqual(completion_trophies, 1)
            HistoricalInventoryWriteService(connection).set_quantity(
                1, "vfl", last, 1, event_key="cb007:complete",
                occurred_at="2026-08-18T10:00:00.000000Z",
            )
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM feed_events"
            ).fetchone()[0])

    def test_completion_feed_failure_rolls_back_inventory_completion_and_unlocks(self):
        with self.connect() as connection:
            last = self._prepare_almost_complete_vfl(connection, 2)
            with mock.patch(
                "services.history_cutover.FeedEventService.record_album_completed",
                side_effect=RuntimeError("forced completion feed failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced completion feed failure"):
                    HistoricalInventoryWriteService(connection).set_quantity(
                        2, "vfl", last, 1, event_key="cb007:rollback",
                        occurred_at="2026-08-18T10:00:00.000000Z",
                    )
            membership = self.membership(connection, 2)
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM stickers WHERE user_id=2 AND album_id='vfl' "
                "AND sticker_code=? AND quantity > 0", (last,)
            ).fetchone())
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM historical_album_records WHERE user_album_id=? "
                "AND completed_at IS NOT NULL", (membership,)
            ).fetchone())
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks WHERE user_album_id=?",
                (membership,),
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM feed_events WHERE user_album_id=?", (membership,)
            ).fetchone()[0])

    def _insert_trophy(self, connection, definition_id, *, source_type="inventory_transition"):
        membership = self.membership(connection)
        cursor = connection.execute(
            """
            INSERT INTO canonical_trophy_unlocks
                (event_key, trophy_definition_id, user_album_id, user_id,
                 album_id, trophy_name, unlocked_at, source_type, source_key)
            VALUES (?, ?, ?, 1, 'vfl', ?, '2026-08-18T10:00:00.000000Z', ?, ?)
            """,
            (
                f"trophy-unlock:{membership}:{definition_id}", definition_id,
                membership, definition_id, source_type, f"source:{definition_id}",
            ),
        )
        return int(cursor.lastrowid), membership

    def test_trophy_producer_uses_explicit_empty_by_default_allowlist(self):
        self.assertEqual(frozenset(), FEED_WORTHY_TROPHY_DEFINITION_IDS)
        with self.connect() as connection:
            allowed_id, membership = self._insert_trophy(connection, "test.feedworthy")
            hidden_id, _ = self._insert_trophy(connection, "test.hidden")
            completion_id, _ = self._insert_trophy(
                connection, "test.completion", source_type="album_completion"
            )
            default = FeedEventService(connection)
            self.assertIsNone(default.record_trophy_unlocked(allowed_id))
            self.assertIsNone(default.record_trophy_unlocked(hidden_id))
            controlled = FeedEventService(
                connection, trophy_allowlist={"test.feedworthy", "test.completion"}
            )
            first = controlled.record_trophy_unlocked(allowed_id)
            retry = controlled.record_trophy_unlocked(allowed_id)
            self.assertTrue(first.created)
            self.assertFalse(retry.created)
            self.assertIsNone(controlled.record_trophy_unlocked(hidden_id))
            self.assertIsNone(controlled.record_trophy_unlocked(completion_id))
            self.assertEqual(
                [f"feed:trophy-unlock:{membership}:test.feedworthy"],
                [row[0] for row in connection.execute(
                    "SELECT event_key FROM feed_events ORDER BY event_key"
                )],
            )
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
            rolled_back_id, _ = self._insert_trophy(connection, "test.rollback")
            FeedEventService(
                connection, trophy_allowlist={"test.rollback"}
            ).record_trophy_unlocked(rolled_back_id)
            connection.rollback()
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM feed_events WHERE event_key LIKE '%test.rollback'"
            ).fetchone())
            with self.assertRaises(FeedEventError):
                controlled.record_trophy_unlocked(999999)

    def test_news_is_controlled_deduplicated_and_never_dominates(self):
        with self.connect() as connection:
            service = FeedEventService(connection)
            for index in range(3):
                result = service.publish_news(
                    f"news-{index}", title=f"News {index}", body="Body",
                    target_path="/sammlung",
                    published_at=f"2026-08-18T1{index}:00:00.000000Z",
                )
                self.assertTrue(result.created)
            retry = service.publish_news(
                "news-2", title="News 2", body="Body", target_path="/sammlung",
                published_at="2026-08-18T12:00:00.000000Z",
            )
            self.assertFalse(retry.created)
            with self.assertRaises(HistoricalWriteConflict):
                service.publish_news(
                    "news-2", title="Changed", body="Body",
                    published_at="2026-08-18T12:00:00.000000Z",
                )
            with self.assertRaises(FeedEventError):
                service.publish_news(
                    "external", title="Unsafe", body="Body",
                    target_path="https://example.com",
                    published_at="2026-08-18T13:00:00.000000Z",
                )
            self.add_event(connection, 1, "personal-a", "2026-08-18T09:00:00.000000Z")
            self.add_event(connection, 1, "personal-b", "2026-08-18T08:00:00.000000Z")
            self.assertNotIn("sammlr_news", {
                item.event_type for item in service.feed_for_user(1, limit=2)
            })
            items = service.feed_for_user(1, limit=3)
            self.assertEqual(1, sum(
                item.event_type == "sammlr_news" for item in items
            ))
            self.assertEqual(
                sorted(
                    ((item.occurred_at, item.event_key) for item in items),
                    reverse=True,
                ),
                [(item.occurred_at, item.event_key) for item in items],
            )

    def test_no_notification_activity_smartmatch_or_tradepool_feed_source(self):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO user_activity (user_id, last_active_at) VALUES (1, CURRENT_TIMESTAMP) "
                "ON CONFLICT(user_id) DO UPDATE SET last_active_at=CURRENT_TIMESTAMP"
            )
            connection.execute(
                "INSERT INTO notifications (user_id, title, body, is_read) "
                "VALUES (1, 'Not feed', 'Not feed', 0)"
            )
            membership = self.membership(connection)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO feed_events
                        (event_key, event_type, actor_user_id, user_album_id,
                         user_id, album_id, target_type, target_key, occurred_at)
                    VALUES ('feed:smartmatch:forbidden', 'trade_milestone', 1, ?,
                            1, 'vfl', 'trade', 'smartmatch',
                            '2026-08-18T10:00:00.000000Z')
                    """,
                    (membership,),
                )
            statements = []
            connection.set_trace_callback(statements.append)
            self.assertEqual((), FeedEventService(connection).feed_for_user(1))
            connection.set_trace_callback(None)
            trace = "\n".join(statements).lower()
            self.assertNotIn(" from notifications", trace)
            self.assertNotIn(" from user_activity", trace)
            self.assertNotIn("trade_pool_enabled", trace)
            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=0 "
                "WHERE user_id=1 AND album_id='vfl'"
            )
            self.add_event(connection, 1, "tradepool-independent", "2026-08-18T11:00:00.000000Z")
            self.assertEqual(1, len(FeedEventService(connection).feed_for_user(1)))
            with self.assertRaises(HistoricalCollectionError):
                HistoricalCollectionService(connection).record_feed_event(
                    event_key="feed:smartmatch:blocked-by-service",
                    event_type="trade_milestone", actor_user_id=1,
                    user_album_id=membership, target_type="trade",
                    target_key="smartmatch",
                    occurred_at="2026-08-18T12:00:00.000000Z",
                )

    def test_export_contains_only_the_subjects_own_feed_events(self):
        with self.connect() as connection:
            self.add_event(connection, 1, "export-own", "2026-08-18T10:00:00.000000Z")
            self.add_event(connection, 2, "export-foreign", "2026-08-18T11:00:00.000000Z")
            document = UserDataExportService(connection).export_for_user(1).to_document()
            self.assertEqual(
                ["feed:test:export-own"],
                [event["event_key"] for event in document["feed_events"]],
            )


if __name__ == "__main__":
    unittest.main()
