import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
STYLE = APP_DIR / "static" / "style.css"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb012-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.feed_events import (  # noqa: E402
    FEED_WORTHY_TROPHY_DEFINITION_IDS,
    FeedEventService,
)
from services.historical_collection import HistoricalCollectionService  # noqa: E402


class CB012FeedHomeCutoverTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        cls.css = STYLE.read_text(encoding="utf-8")
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb012-")
        self.db_path = Path(self.temp_dir.name) / "feed-home.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            for table in (
                "sammlr_news", "feed_events", "canonical_trophy_unlocks",
                "historical_sticker_acquisitions",
                "historical_album_progress_points", "historical_album_records",
                "blocks", "friendships", "friendship_requests",
                "notifications", "user_activity",
                "trade_receipt_report_positions", "trade_receipt_reports",
                "trade_receipt_status", "trade_shipping_status",
                "trade_reservations", "trade_events", "trade_positions",
                "trades", "trade_requests",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute(
                "UPDATE users SET account_state='active', profile_privacy='public' "
                "WHERE id IN (1, 2, 3)"
            )
            connection.execute(
                "UPDATE users SET username='owner', name='Owner' WHERE id=1"
            )
            connection.execute(
                "UPDATE users SET username='freund', name='Langer Freundesname' WHERE id=2"
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

    @staticmethod
    def membership(connection, user_id=1):
        return int(connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id='vfl'",
            (user_id,),
        ).fetchone()[0])

    def add_event(
        self, connection, user_id, key, occurred_at, event_type="album_started"
    ):
        membership = self.membership(connection, user_id)
        return HistoricalCollectionService(connection).record_feed_event(
            event_key=f"feed:test:{key}",
            event_type=event_type,
            actor_user_id=user_id,
            user_album_id=membership,
            target_type="trophy" if event_type == "trophy_unlocked" else "album",
            target_key="test.feedworthy" if event_type == "trophy_unlocked" else "vfl",
            occurred_at=occurred_at,
        )

    def make_friends(self, connection, first=1, second=2):
        low, high = sorted((first, second))
        connection.execute(
            "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
            (low, high),
        )

    def home(self):
        response = self.client.get("/")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def test_own_start_and_completion_render_in_canonical_order_and_deep_link(self):
        with self.connection() as connection:
            self.add_event(
                connection, 1, "start", "2026-08-20T10:00:00.000000Z"
            )
            self.add_event(
                connection, 1, "completion-a", "2026-08-20T11:00:00.000000Z",
                "album_completed",
            )
            self.add_event(
                connection, 1, "completion-b", "2026-08-20T11:00:00.000000Z",
                "album_completed",
            )
        html = self.home()
        self.assertIn("Du hast ein Album begonnen", html)
        self.assertIn("Du hast ein Album vervollständigt", html)
        self.assertEqual(
            3,
            len(re.findall(r'class="feed-card"[^>]*href="/album/vfl"', html)),
        )
        self.assertLess(html.index("feed:test:completion-b") if "feed:test:completion-b" in html else html.index("Du hast ein Album vervollständigt"), html.index("Du hast ein Album begonnen"))
        with self.connection() as connection:
            keys = [item.event_key for item in FeedEventService(
                connection
            ).feed_for_user(1)]
        self.assertEqual(
            ["feed:test:completion-b", "feed:test:completion-a", "feed:test:start"],
            keys,
        )
        self.assertEqual(200, self.client.get("/album/vfl").status_code)

    def test_completion_trophy_is_not_duplicated_and_allowed_trophy_renders(self):
        self.assertEqual(frozenset(), FEED_WORTHY_TROPHY_DEFINITION_IDS)
        with self.connection() as connection:
            membership = self.membership(connection)
            self.add_event(
                connection, 1, "completed", "2026-08-20T10:00:00.000000Z",
                "album_completed",
            )
            rows = []
            for definition, source in (
                ("test.feedworthy", "inventory_transition"),
                ("test.hidden", "inventory_transition"),
                ("test.completion", "album_completion"),
            ):
                cursor = connection.execute(
                    """
                    INSERT INTO canonical_trophy_unlocks
                        (event_key, trophy_definition_id, user_album_id, user_id,
                         album_id, trophy_name, unlocked_at, source_type, source_key)
                    VALUES (?, ?, ?, 1, 'vfl', ?,
                            '2026-08-20T11:00:00.000000Z', ?, ?)
                    """,
                    (f"unlock:{definition}", definition, membership, definition,
                     source, f"source:{definition}"),
                )
                rows.append(int(cursor.lastrowid))
            default = FeedEventService(connection)
            self.assertIsNone(default.record_trophy_unlocked(rows[1]))
            controlled = FeedEventService(
                connection, trophy_allowlist={"test.feedworthy", "test.completion"}
            )
            controlled.record_trophy_unlocked(rows[0])
            self.assertIsNone(controlled.record_trophy_unlocked(rows[2]))
        html = self.home()
        self.assertEqual(1, html.count("ein Album vervollständigt"))
        self.assertEqual(1, html.count("eine besondere Trophäe freigeschaltet"))
        self.assertIn('href="/album/vfl/trophaeen"', html)
        self.assertNotIn("test.hidden", html)

    def test_only_mutual_friend_is_visible_and_profile_album_link_is_authorized(self):
        with self.connection() as connection:
            self.add_event(
                connection, 2, "friend", "2026-08-20T10:00:00.000000Z"
            )
            connection.execute(
                "INSERT INTO friendship_requests "
                "(requester_user_id, recipient_user_id, status) "
                "VALUES (1, 2, 'pending')"
            )
        self.assertNotIn("Langer Freundesname", self.home())
        with self.connection() as connection:
            connection.execute("UPDATE friendship_requests SET status='accepted'")
        self.assertNotIn("Langer Freundesname", self.home())
        with self.connection() as connection:
            self.make_friends(connection)
        html = self.home()
        target = '/profil/freund/album/vfl'
        self.assertIn("Langer Freundesname hat ein Album begonnen", html)
        self.assertIn(f'href="{target}"', html)
        self.assertEqual(200, self.client.get(target).status_code)

    def test_current_block_profile_and_album_privacy_hide_persisted_friend_event(self):
        with self.connection() as connection:
            self.add_event(
                connection, 2, "friend-private", "2026-08-20T10:00:00.000000Z"
            )
            self.make_friends(connection)
        self.assertIn("Langer Freundesname", self.home())

        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET visibility='private' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
        self.assertNotIn("Langer Freundesname", self.home())
        self.assertEqual(404, self.client.get("/profil/freund/album/vfl").status_code)

        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET visibility='friends' "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=2"
            )
        self.assertIn("Langer Freundesname", self.home())
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
            )
        self.assertNotIn("Langer Freundesname", self.home())

    def test_news_is_limited_to_one_and_personal_events_take_capacity_first(self):
        with self.connection() as connection:
            service = FeedEventService(connection)
            for index in range(2):
                service.publish_news(
                    f"news-{index}", title=f"News {index}", body="Neuigkeit",
                    target_path="/sammlung",
                    published_at=f"2026-08-20T1{index}:00:00.000000Z",
                )
            for index in range(20):
                self.add_event(
                    connection, 1, f"personal-{index}",
                    f"2026-08-19T{index:02d}:00:00.000000Z",
                )
            items = service.feed_for_user(1, limit=20)
        self.assertEqual(20, len(items))
        self.assertNotIn("sammlr_news", [item.event_type for item in items])

        with self.connection() as connection:
            connection.execute(
                "DELETE FROM feed_events WHERE event_key='feed:test:personal-0'"
            )
            items = FeedEventService(connection).feed_for_user(1, limit=20)
        self.assertEqual(1, sum(item.event_type == "sammlr_news" for item in items))
        html = self.home()
        self.assertEqual(1, html.count('data-event-type="sammlr_news"'))
        self.assertIn('href="/sammlung"', html)

    def test_no_events_uses_approved_action_plane_without_artificial_feed_empty(self):
        html = self.home()
        self.assertNotIn("Deine Sammlerreise beginnt hier.", html)
        self.assertNotIn('class="feed-empty"', html)
        self.assertIn("Tauschchance", html)
        self.assertIn("Favoritenalbum", html)
        self.assertIn('href="/trades"', html)
        self.assertNotIn("Fake", html)
        with self.connection() as connection:
            self.add_event(
                connection, 2, "invisible", "2026-08-20T10:00:00.000000Z"
            )
        filtered = self.home()
        self.assertIn("Tauschchance", filtered)
        self.assertNotIn('class="feed-card"', filtered)
        self.assertNotIn("freund", filtered)

    def test_notifications_activity_smartmatches_and_trades_are_not_feed_sources(self):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO notifications
                    (user_id, title, body, is_read, notification_type,
                     target_type, target_id, dedupe_key)
                VALUES (1, 'Trade-Aktion', 'Versenden', 0,
                        'trade_shipped', 'trade', 999, 'cb012:notification')
                """
            )
            connection.execute(
                "INSERT INTO user_activity (user_id, last_active_at) "
                "VALUES (1, CURRENT_TIMESTAMP)"
            )
            connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, from_confirmed)
                VALUES ('vfl', 1, 2, '["1"]', '["2"]', 'open', -22)
                """
            )
        html = self.home()
        self.assertIn("Tauschchance", html)
        self.assertNotIn('class="feed-card"', html)
        for forbidden in (
            "Trade-Aktion", "Versenden", "SmartMatch", "Das braucht dich",
            "Laufende Trades / Sendungen", "Priorität",
        ):
            self.assertNotIn(forbidden, html)

    def test_operational_home_legacy_service_is_removed(self):
        source = (APP_DIR / "webapp.py").read_text(encoding="utf-8")
        self.assertNotIn("OperationalHomeService", source)
        self.assertFalse((APP_DIR / "services" / "operational_home.py").exists())
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 2, 1, '["1"]', '["2"]', 'open')
                """
            )
        html = self.home()
        self.assertNotIn("Neue Tauschanfrage", html)
        self.assertIn('action="/notifications"', html)
        self.assertIn('href="/trades"', html)

    def test_tradepool_is_unchanged_and_home_read_is_side_effect_free(self):
        before_hash = sha256(self.db_path)
        with self.connection() as connection:
            before = connection.execute(
                "SELECT user_id, album_id, trade_pool_enabled FROM user_albums "
                "ORDER BY user_id, album_id"
            ).fetchall()
        self.home()
        with self.connection() as connection:
            after = connection.execute(
                "SELECT user_id, album_id, trade_pool_enabled FROM user_albums "
                "ORDER BY user_id, album_id"
            ).fetchall()
        self.assertEqual(before, after)
        self.assertEqual(before_hash, sha256(self.db_path))

    def test_navigation_and_390px_mobile_contract_remain_reachable(self):
        html = self.home()
        for target in ('href="/sammlung"', 'href="/"', 'href="/trades"'):
            self.assertIn(target, html)
        self.assertIn('action="/notifications"', html)
        self.assertIn('href="/profil"', html)
        mobile = self.css.split("@media (max-width:390px)", 1)[1]
        self.assertIn(".feed-card", mobile)
        self.assertIn("width:100%", mobile)
        self.assertIn("overflow-wrap:anywhere", self.css)
        feed_box = self.css.split(".feed-card,\n.feed-empty{", 1)[1].split("}", 1)[0]
        self.assertIn("box-sizing:border-box", feed_box)
        nav_box = self.css.split(
            ".s31-product-page .bottom-nav:not(.album-bottom-nav){", 1
        )[1].split("}", 1)[0]
        self.assertIn("box-sizing:border-box", nav_box)
        self.assertNotIn('class="card', html)

    def test_no_migration_or_parallel_reconstruction_is_added(self):
        self.assertEqual(22, max(item.version for item in load_migrations()))
        source = (APP_DIR / "webapp.py").read_text(encoding="utf-8")
        home_source = source[source.index("def startseite():"):source.index(
            '@app.route("/home")'
        )]
        self.assertIn("FeedEventService", home_source)
        for forbidden in (
            "notifications", "user_activity", "SmartTrade", "trade_requests",
            "OperationalHomeService",
        ):
            self.assertNotIn(forbidden, home_source)


if __name__ == "__main__":
    unittest.main()
