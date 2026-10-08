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
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s27-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    load_migrations,
    migrate,
    rollback,
)
from services.album_privacy import (  # noqa: E402
    ALBUM_VISIBILITIES,
    AlbumPrivacyService,
    AlbumPrivacyUpdateCode,
)
from services.inventory import InventoryReadService  # noqa: E402
from services.smart_trade_requests import (  # noqa: E402
    SmartTradeRequestCode,
    SmartTradeRequestService,
)
from services.top_match_optimization import TopMatchOptimizationService  # noqa: E402
from services.trade_coverage import TradeCoverageService  # noqa: E402


class AlbumPrivacyTradePoolTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s27-")
        self.test_db = Path(self.test_dir.name) / "privacy.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5, 6, 7), migrate(connection, 7))
            self._clear_domain(connection)
            connection.execute(
                "UPDATE users SET username='owner', name='Owner' WHERE id=1"
            )
            connection.execute(
                "UPDATE users SET username='public_partner', name='Public' WHERE id=2"
            )
            connection.execute(
                "UPDATE users SET username='friend_partner', name='Friend' WHERE id=3"
            )
            connection.execute(
                "UPDATE users SET username='visible_no_pool', name='Visible' WHERE id=4"
            )
            connection.executemany(
                """
                INSERT INTO user_albums
                    (user_id, album_id, visibility, trade_pool_enabled)
                VALUES (?, 'vfl', ?, ?)
                """,
                (
                    (1, "private", 1),
                    (2, "public", 1),
                    (3, "friends", 1),
                    (4, "public", 0),
                ),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, 'vfl', ?, 'owned', ?, ?)
                """,
                (
                    (1, "1", 1, 2),
                    (2, "2", 1, 2),
                    (3, "3", 1, 2),
                    (4, "4", 1, 2),
                ),
            )
            connection.execute(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (2, 'vfl', 'Visible independent count', CURRENT_TIMESTAMP)
                """
            )

        webapp.DB = str(self.test_db)
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _clear_domain(connection):
        for table in (
            "trade_receipt_report_positions",
            "trade_receipt_reports",
            "trade_receipt_status",
            "trade_shipping_status",
            "trade_reservations",
            "trade_events",
            "trade_positions",
            "trades",
            "trade_requests",
            "notifications",
            "unlocked_trophies",
            "stickers",
            "user_albums",
        ):
            connection.execute(f"DELETE FROM {table}")

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def set_membership(self, user_id, *, visibility=None, pool=None):
        assignments = []
        values = []
        if visibility is not None:
            assignments.append("visibility=?")
            values.append(visibility)
        if pool is not None:
            assignments.append("trade_pool_enabled=?")
            values.append(1 if pool else 0)
        values.extend((user_id, "vfl"))
        with self.connection() as connection:
            connection.execute(
                f"UPDATE user_albums SET {', '.join(assignments)} "
                "WHERE user_id=? AND album_id=?",
                values,
            )

    def test_v0007_backfill_defaults_constraints_repeat_and_backout(self):
        migration_db = Path(self.test_dir.name) / "migration.db"
        shutil.copy2(REFERENCE_FIXTURE, migration_db)
        with self.connection(migration_db) as connection:
            self.assertEqual((1, 2, 3, 4, 5, 6), migrate(connection, 6))
            connection.execute("DELETE FROM user_albums")
            connection.execute(
                "INSERT INTO user_albums (user_id, album_id) VALUES (1, 'vfl')"
            )
            self.assertEqual((7,), migrate(connection, 7))
            self.assertEqual(7, current_version(connection))
            row = connection.execute(
                "SELECT visibility, trade_pool_enabled FROM user_albums"
            ).fetchone()
            self.assertEqual(("private", 1), tuple(row))
            connection.execute(
                "INSERT INTO user_albums (user_id, album_id) VALUES (2, 'vfl')"
            )
            new_row = connection.execute(
                "SELECT visibility, trade_pool_enabled FROM user_albums WHERE user_id=2"
            ).fetchone()
            self.assertEqual(("private", 1), tuple(new_row))
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE user_albums SET visibility='unknown' WHERE user_id=1"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE user_albums SET trade_pool_enabled=2 WHERE user_id=1"
                )
            self.assertEqual((), migrate(connection, 7))
            self.assertEqual((7,), rollback(connection, 6))
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(user_albums)")
            }
            self.assertNotIn("visibility", columns)
            self.assertNotIn("trade_pool_enabled", columns)
            self.assertEqual(2, connection.execute(
                "SELECT COUNT(*) FROM user_albums"
            ).fetchone()[0])
            self.assertEqual((7,), migrate(connection, 7))
        # S27 remains on V0007; S28 subsequently added V0008.
        self.assertEqual(28, load_migrations()[-1].version)

    def test_service_visibility_matrix_friend_double_and_immutable_dto(self):
        with self.connection() as connection:
            service = AlbumPrivacyService(connection)
            self.assertTrue(service.can_view(1, 1, "vfl"))
            self.assertTrue(service.can_view(1, 2, "vfl"))
            self.assertFalse(service.can_view(1, 3, "vfl"))
            self.assertFalse(service.can_view(2, 1, "vfl"))
            friend_service = AlbumPrivacyService(
                connection,
                lambda viewer, owner: (viewer, owner) == (1, 3),
            )
            self.assertTrue(friend_service.can_view(1, 3, "vfl"))
            self.assertEqual(
                {"public", "friends", "private"}, set(ALBUM_VISIBILITIES)
            )
            access = service.access(1, "vfl")
            with self.assertRaises(FrozenInstanceError):
                access.visibility = "public"

    def test_owner_controls_update_invalid_input_and_other_owner_is_untouched(self):
        response = self.client.get("/album/vfl")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn("Sichtbarkeit &amp; Tradepool", html)
        self.assertIn('<dialog id="albumSettingsDialog"', html)
        self.assertIn('data-album-settings-open', html)
        self.assertIn('aria-controls="albumSettingsDialog"', html)
        self.assertIn('data-album-settings-close', html)
        self.assertIn('method="POST" action="/album/vfl/privacy"', html)
        self.assertIn('name="visibility"', html)
        self.assertIn('name="trade_pool_enabled" value="1"', html)
        self.assertIn("dialog.showModal()", html)
        self.assertNotIn("Album übertragen", html)
        self.assertEqual(403, self.client.post(
            "/album/vfl/privacy",
            data={"visibility": "public"},
            csrf_protect=False,
        ).status_code)
        response = self.client.post(
            "/album/vfl/privacy",
            data={"visibility": "public"},
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            owner = connection.execute(
                "SELECT visibility, trade_pool_enabled FROM user_albums "
                "WHERE user_id=1 AND album_id='vfl'"
            ).fetchone()
            other = connection.execute(
                "SELECT visibility, trade_pool_enabled FROM user_albums "
                "WHERE user_id=2 AND album_id='vfl'"
            ).fetchone()
        self.assertEqual(("public", 0), tuple(owner))
        self.assertEqual(("public", 1), tuple(other))

        response = self.client.post(
            "/album/vfl/privacy",
            data={"visibility": "friends", "trade_pool_enabled": "1"},
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            owner = connection.execute(
                "SELECT visibility, trade_pool_enabled FROM user_albums "
                "WHERE user_id=1 AND album_id='vfl'"
            ).fetchone()
        self.assertEqual(("friends", 1), tuple(owner))
        self.assertEqual(400, self.client.post(
            "/album/vfl/privacy", data={"visibility": "admin"}
        ).status_code)
        self.login_as(5)
        self.assertEqual(404, self.client.post(
            "/album/vfl/privacy", data={"visibility": "public"}
        ).status_code)

    def test_public_foreign_wall_and_detail_are_exact_read_only(self):
        before = sha256(self.test_db)
        response = self.client.get("/profil/public_partner/album/vfl")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn("VfL Osnabrück", html)
        self.assertIn('data-code="2"', html)
        self.assertIn('data-quantity="2"', html)
        self.assertNotIn("Menge erhöhen", html)
        self.assertEqual(1, html.count('method="POST"'))
        self.assertIn('method="POST" action="/notifications"', html)
        detail = self.client.get(
            "/profil/public_partner/album/vfl/sticker/2"
        )
        self.assertEqual(200, detail.status_code)
        detail_html = detail.get_data(as_text=True)
        self.assertIn("Anzahl: <strong>2</strong>", detail_html)
        self.assertIn("Doppelte: <strong>1</strong>", detail_html)
        self.assertEqual(before, sha256(self.test_db))

    def test_private_and_friends_hide_profile_aggregates_wall_and_detail(self):
        self.set_membership(2, visibility="private")
        profile = self.client.get("/profil/public_partner")
        self.assertEqual(200, profile.status_code)
        html = profile.get_data(as_text=True)
        self.assertNotIn("VfL Osnabrück", html)
        self.assertNotIn("Gültige Trophäen", html)
        self.assertIn("Sammelt gerade", html)
        for path in (
            "/profil/public_partner/album/vfl",
            "/profil/public_partner/album/vfl/sticker/2",
            "/profil/public_partner/album/unknown",
        ):
            response = self.client.get(path)
            self.assertEqual(404, response.status_code)
            self.assertNotIn("data-code", response.get_data(as_text=True))

        webapp.app.config["FRIENDSHIP_CHECKER"] = (
            lambda viewer, owner: (viewer, owner) == (1, 3)
        )
        response = self.client.get("/profil/friend_partner/album/vfl")
        self.assertEqual(200, response.status_code)
        self.assertIn('data-code="3"', response.get_data(as_text=True))

    def test_private_pool_enabled_is_matchable_without_general_inspection(self):
        self.set_membership(2, visibility="private", pool=True)
        self.assertEqual(
            404,
            self.client.get("/profil/public_partner/album/vfl").status_code,
        )
        global_html = self.client.get("/trades?tab=partners").get_data(as_text=True)
        album_html = self.client.get("/album/vfl/trades?tab=partners").get_data(as_text=True)
        self.assertIn("public_partner", global_html)
        self.assertIn("public_partner", album_html)
        self.assertNotIn('data-code="2"', global_html)

    def test_public_pool_disabled_is_visible_but_absent_from_trade_paths(self):
        self.set_membership(2, visibility="public", pool=False)
        self.assertEqual(
            200,
            self.client.get("/profil/public_partner/album/vfl").status_code,
        )
        self.assertNotIn(
            "public_partner",
            self.client.get("/trades?tab=partners").get_data(as_text=True),
        )
        self.assertNotIn(
            "public_partner",
            self.client.get("/album/vfl/trades?tab=partners").get_data(as_text=True),
        )
        self.assertEqual(404, self.client.get("/album/vfl/trade/2").status_code)
        self.assertEqual(404, self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": "1", "get_codes": "2"},
        ).status_code)

    def test_coverage_top_match_and_smart_request_share_trade_pool(self):
        with self.connection() as connection:
            privacy = AlbumPrivacyService(connection)
            inventory = InventoryReadService(connection)
            coverage = TradeCoverageService(inventory, privacy)
            personal = coverage.personal_trade_coverage(1, 2, "vfl", ("1", "2"))
            self.assertEqual(("2",), personal.effectively_available_codes)
            market = coverage.community_market_coverage(
                1, "vfl", ("1", "2"), (2, 3, 4)
            )
            self.assertEqual(("2",), market.available_codes)
            optimized = TopMatchOptimizationService(inventory).optimize(
                1, "vfl", ("1", "2"), (2,)
            )
            self.assertEqual((2,), tuple(
                package.partner_user_id for package in optimized.packages
            ))

            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=0 "
                "WHERE user_id=2 AND album_id='vfl'"
            )
            connection.commit()
            personal_disabled = coverage.personal_trade_coverage(
                1, 2, "vfl", ("1", "2")
            )
            self.assertEqual((), personal_disabled.effectively_available_codes)
            self.assertEqual((), coverage.community_market_coverage(
                1, "vfl", ("1", "2"), (2,)
            ).available_codes)
            self.assertEqual((), TopMatchOptimizationService(inventory).optimize(
                1, "vfl", ("1", "2"), (2,)
            ).packages)

            before_requests = connection.execute(
                "SELECT COUNT(*) FROM trade_requests"
            ).fetchone()[0]
            result = SmartTradeRequestService(connection).create(
                "vfl", 1, 2, ("1",), ("2",)
            )
            self.assertEqual(SmartTradeRequestCode.OBSOLETE, result.code)
            self.assertEqual(before_requests, connection.execute(
                "SELECT COUNT(*) FROM trade_requests"
            ).fetchone()[0])

    def test_existing_trade_remains_visible_after_pool_opt_out(self):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status)
                VALUES ('vfl', 1, 2, '["1"]', '["2"]', 'accepted')
                """
            )
            trade_id = cursor.lastrowid
            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=0 "
                "WHERE user_id=2 AND album_id='vfl'"
            )
        response = self.client.get(f"/trades/{trade_id}")
        self.assertEqual(200, response.status_code)
        self.assertIn("public_partner", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
