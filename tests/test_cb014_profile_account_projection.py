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


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb014-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.collector_profiles import (  # noqa: E402
    AccountSettingsService,
    CollectorProfileService,
)
from services.historical_collection import HistoricalCollectionService  # noqa: E402


class CB014ProfileAccountProjectionTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb014-")
        self.db_path = Path(self.temp_dir.name) / "profile.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            for table in (
                "trade_ratings", "trade_receipt_report_positions",
                "trade_receipt_reports", "trade_receipt_status",
                "trade_shipping_status", "trade_reservations", "trade_events",
                "trade_positions", "trades", "trade_requests",
                "canonical_trophy_unlocks", "historical_album_records",
                "feed_events", "blocks", "friendships",
                "friendship_requests", "unlocked_trophies", "stickers",
                "user_albums",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute(
                "UPDATE users SET username='viewer', name='Viewer', "
                "profile_privacy='public', account_state='active' WHERE id=1"
            )
            connection.execute(
                "UPDATE users SET username='collector', name='Collector Name', "
                "password='account-secret-hash', profile_privacy='public', "
                "account_state='active' WHERE id=2"
            )
            connection.executemany(
                """
                INSERT INTO user_albums
                    (user_id, album_id, visibility, trade_pool_enabled)
                VALUES (2, ?, ?, 1)
                """,
                (("vfl", "public"), ("wm26", "friends"), ("em24", "private")),
            )
            connection.execute(
                "INSERT INTO user_albums "
                "(user_id, album_id, visibility, trade_pool_enabled) "
                "VALUES (1, 'vfl', 'private', 1)"
            )
            self.vfl_membership = self.membership(connection, 2, "vfl")
            self.wm_membership = self.membership(connection, 2, "wm26")
            self.em_membership = self.membership(connection, 2, "em24")
            self.complete(
                connection, self.vfl_membership,
                "2026-08-18T12:00:00.000000Z",
            )
            self.complete(
                connection, self.wm_membership,
                "2026-08-19T12:00:00.000000Z",
            )
            self.add_trophy(
                connection, self.vfl_membership, "vfl",
                "vfl.chapter.intro.v1", "Intro",
                "2026-08-18T13:00:00.000000Z",
            )
            self.add_trophy(
                connection, self.wm_membership, "wm26",
                "wm26.chapter.intro.v1", "Intro WM",
                "2026-08-19T13:00:00.000000Z",
            )
            self.add_trophy(
                connection, self.vfl_membership, "vfl",
                "not-approved.v1", "Nicht gültig",
                "2026-08-20T13:00:00.000000Z",
            )
            connection.execute(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (2, 'vfl', 'Legacy Trophy Secret', CURRENT_TIMESTAMP)
                """
            )
            self.add_successful_rated_trade(connection)

        webapp.DB = str(self.db_path)
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
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

    @staticmethod
    def membership(connection, user_id, album_id):
        return int(connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchone()[0])

    @staticmethod
    def complete(connection, membership_id, completed_at):
        HistoricalCollectionService(connection).record_first_album_completion(
            membership_id,
            completed_at=completed_at,
            event_key=f"album-completion:{membership_id}",
            source_type="inventory_transition",
            source_key=f"cb014:completion:{membership_id}",
        )

    @staticmethod
    def add_trophy(
        connection, membership_id, album_id, definition_id, name, unlocked_at
    ):
        connection.execute(
            """
            INSERT INTO canonical_trophy_unlocks
                (event_key, trophy_definition_id, user_album_id, user_id,
                 album_id, trophy_name, unlocked_at, source_type, source_key)
            VALUES (?, ?, ?, 2, ?, ?, ?, 'inventory_transition', ?)
            """,
            (
                f"trophy-unlock:{membership_id}:{definition_id}",
                definition_id, membership_id, album_id, name, unlocked_at,
                f"cb014:trophy:{membership_id}:{definition_id}",
            ),
        )

    @staticmethod
    def add_successful_rated_trade(connection):
        request = connection.execute(
            """
            INSERT INTO trade_requests
                (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
            VALUES ('vfl', 1, 2, '["1"]', '["2"]', 'completed')
            """
        )
        trade = connection.execute(
            """
            INSERT INTO trades
                (legacy_trade_request_id, requester_user_id, partner_user_id,
                 lifecycle_state, completed_at)
            VALUES (?, 1, 2, 'completed', '2026-08-19T15:00:00.000000Z')
            """,
            (request.lastrowid,),
        )
        connection.execute(
            """
            INSERT INTO trade_receipt_status
                (trade_id, requester_received, requester_received_at,
                 partner_received, partner_received_at)
            VALUES (?, 1, '2026-08-19T14:59:00.000000Z',
                    1, '2026-08-19T15:00:00.000000Z')
            """,
            (trade.lastrowid,),
        )
        connection.executemany(
            """
            INSERT INTO trade_positions
                (trade_id, from_user_id, to_user_id, album_id,
                 sticker_code, quantity)
            VALUES (?, ?, ?, 'vfl', ?, 1)
            """,
            (
                (trade.lastrowid, 1, 2, "1"),
                (trade.lastrowid, 2, 1, "2"),
            ),
        )
        connection.execute(
            """
            INSERT INTO trade_ratings
                (trade_id, rater_user_id, rated_user_id, stars)
            VALUES (?, 1, 2, 5)
            """,
            (trade.lastrowid,),
        )

    def login_as(self, user_id):
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id

    def model(self, viewer=1):
        with self.connection() as connection:
            return CollectorProfileService(connection).by_user_id(2, viewer)

    def profile_html(self):
        response = self.client.get("/profil/collector")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def make_friends(self):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO friendships (user_low_id, user_high_id) VALUES (1, 2)"
            )

    def test_public_profile_uses_compact_trust_contract(self):
        model = self.model()
        html = self.profile_html()
        self.assertEqual(("vfl",), tuple(a.album_id for a in model.current_albums))
        self.assertEqual(1, model.completed_album_count)
        self.assertEqual(1, model.trophy_count)
        self.assertEqual((1, 5), (model.rating_count, model.rating_average))
        self.assertEqual(1, model.successful_trade_count)
        header = html[
            html.index('aria-label="Sammlerprofil"'):
            html.index("</section>", html.index('aria-label="Sammlerprofil"'))
        ]
        self.assertIn("★ 5,0", header)
        self.assertIn("1 Bewertung · 1 Tausch", header)
        for forbidden in (
            "Sammler-Kennzahlen", "Gültige Trophäen", "Doppelte",
            "Fehlende", "Partnerzahl",
        ):
            self.assertNotIn(forbidden, html)

    def test_valid_canonical_trophies_only_and_no_duplicates(self):
        html = self.profile_html()
        self.assertNotIn("<strong>Intro</strong>", html)
        self.assertNotIn("Nicht gültig", html)
        self.assertNotIn("Legacy Trophy Secret", html)
        self.assertEqual(1, self.model().trophy_count)

    def test_historical_completions_are_canonical_and_current_state_is_not_history(self):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (2, 'em24', 'FWC 1', 'owned', 50, 51)
                """
            )
        model = self.model()
        self.assertEqual(("vfl",), tuple(
            completion.album_id for completion in model.historical_completions
        ))
        html = self.profile_html()
        self.assertIn("Abgeschlossene Alben", html)
        self.assertIn("Vervollständigt", html)
        self.assertIn("18.08.2026", html)
        self.assertNotIn("Doppelte", html)

    def test_album_privacy_filters_albums_history_and_trophies_together(self):
        self.make_friends()
        model = self.model()
        self.assertEqual(("wm26", "vfl"), tuple(
            album.album_id for album in model.current_albums
        ))
        self.assertEqual(("wm26", "vfl"), tuple(
            completion.album_id for completion in model.historical_completions
        ))
        self.assertEqual(("wm26", "vfl"), tuple(
            trophy.album_id for trophy in model.valid_trophies
        ))
        self.assertNotIn("EURO 2024", self.profile_html())

    def test_private_profile_requires_mutual_friendship_pending_is_not_enough(self):
        with self.connection() as connection:
            connection.execute("UPDATE users SET profile_privacy='private' WHERE id=2")
            connection.execute(
                """
                INSERT INTO friendship_requests
                    (requester_user_id, recipient_user_id, status)
                VALUES (1, 2, 'pending')
                """
            )
        hidden = self.model()
        self.assertFalse(hidden.collector_world_visible)
        self.assertEqual(((), (), ()), (
            hidden.current_albums, hidden.historical_completions,
            hidden.valid_trophies,
        ))
        self.assertIn("Dieses Profil ist privat.", self.profile_html())
        self.make_friends()
        self.assertTrue(self.model().collector_world_visible)

    def test_block_wins_over_public_and_friendship(self):
        self.make_friends()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
            )
        html = self.profile_html()
        self.assertIn("Dieses Profil ist privat.", html)
        self.assertNotIn("Collector Name", html)
        self.assertEqual(404, self.client.get(
            "/profil/collector/album/vfl"
        ).status_code)

    def test_owner_profile_sees_private_album_but_account_actions_are_separate(self):
        self.login_as(2)
        profile_html = self.client.get("/profil").get_data(as_text=True)
        self.assertIn("EURO 2024", profile_html)
        self.assertIn('href="/account"', profile_html)
        for internal_path in (
            "/profil/name", "/profil/username", "/profil/password",
            "/profil/privacy", "/profil/datenexport",
        ):
            self.assertNotIn(f'href="{internal_path}"', profile_html)
        account_html = self.client.get("/account").get_data(as_text=True)
        for internal_path in (
            "/profil/name", "/profil/username", "/profil/password",
            "/profil/privacy", "/profil/datenexport",
        ):
            self.assertIn(f'href="{internal_path}"', account_html)

    def test_foreign_profile_leaks_no_account_or_detail_statistics(self):
        html = self.profile_html()
        for forbidden in (
            "account-secret-hash", "account_state",
            "/profil/password", "/profil/privacy", "/profil/datenexport",
            "Doppelte", "sticker_code", "data-quantity",
            "Wie gut kann dieser Nutzer mir helfen?",
        ):
            self.assertNotIn(forbidden, html)

    def test_tradepool_is_unchanged_and_not_rendered_as_profile_inventory(self):
        with self.connection() as connection:
            before = tuple(connection.execute(
                "SELECT album_id, trade_pool_enabled FROM user_albums "
                "WHERE user_id=2 ORDER BY album_id"
            ))
        self.profile_html()
        with self.connection() as connection:
            after = tuple(connection.execute(
                "SELECT album_id, trade_pool_enabled FROM user_albums "
                "WHERE user_id=2 ORDER BY album_id"
            ))
        self.assertEqual(before, after)

    def test_public_projection_is_bounded_and_reads_no_inventory_or_legacy_trophies(self):
        with self.connection() as connection:
            statements = []
            connection.set_trace_callback(statements.append)
            model = CollectorProfileService(connection).by_user_id(2, 1)
            connection.set_trace_callback(None)
        self.assertTrue(model.collector_world_visible)
        reads = [
            statement.lower() for statement in statements
            if statement.lstrip().lower().startswith("select")
        ]
        self.assertLessEqual(len(reads), 30, "\n".join(reads))
        joined = "\n".join(reads)
        self.assertNotIn(" from stickers", joined)
        self.assertNotIn(" from unlocked_trophies", joined)

    def test_profile_and_account_reads_are_read_only_and_models_immutable(self):
        before = sha256(self.db_path)
        model = self.model()
        self.client.get("/profil/collector")
        self.login_as(2)
        self.client.get("/account")
        self.assertEqual(before, sha256(self.db_path))
        with self.assertRaises(FrozenInstanceError):
            model.username = "changed"
        with self.connection() as connection:
            account = AccountSettingsService(connection).for_owner(2)
        with self.assertRaises(FrozenInstanceError):
            account.username = "changed"

    def test_no_migration_and_no_notification_or_feed_side_effect(self):
        with self.connection() as connection:
            before = tuple(connection.execute(
                "SELECT (SELECT COUNT(*) FROM notifications), "
                "(SELECT COUNT(*) FROM feed_events)"
            ).fetchone())
        self.profile_html()
        with self.connection() as connection:
            after = tuple(connection.execute(
                "SELECT (SELECT COUNT(*) FROM notifications), "
                "(SELECT COUNT(*) FROM feed_events)"
            ).fetchone())
        self.assertEqual(before, after)
        self.assertEqual(22, max(item.version for item in load_migrations()))


if __name__ == "__main__":
    unittest.main()
