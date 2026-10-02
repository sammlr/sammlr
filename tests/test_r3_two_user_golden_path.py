import atexit
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-r3-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402


class R3TwoUserGoldenPathTestCase(unittest.TestCase):
    """Current-schema HTTP gate for the Closed-Beta two-user core."""

    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-r3-")
        self.db_path = Path(self.temp_dir.name) / "golden-path.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 20)
        webapp.DB = str(self.db_path)
        self.alex = webapp.app.test_client()
        self.bela = webapp.app.test_client()
        self.outsider = webapp.app.test_client()

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def register_and_login(self, client, *, name, username):
        response = client.post("/register", data={
            "name": name,
            "username": username,
            "password": "r3-closed-beta",
            "password_repeat": "r3-closed-beta",
        })
        self.assertEqual(302, response.status_code)
        self.assertEqual("/login", response.headers["Location"])
        response = client.post("/login", data={
            "username": username,
            "password": "r3-closed-beta",
        })
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            return connection.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            ).fetchone()["id"]

    def quantity(self, user_id, code):
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT quantity, duplicates FROM stickers
                WHERE user_id=? AND album_id='vfl' AND sticker_code=?
                """,
                (user_id, code),
            ).fetchone()
        return None if row is None else (row["quantity"], row["duplicates"])

    def trade_row(self, alex_id, bela_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT * FROM trade_requests
                WHERE from_user_id=? AND to_user_id=?
                ORDER BY id DESC LIMIT 1
                """,
                (alex_id, bela_id),
            ).fetchone()

    def assert_database_health(self):
        with self.connection() as connection:
            self.assertEqual(20, current_version(connection))
            self.assertEqual(
                "ok", connection.execute("PRAGMA integrity_check").fetchone()[0]
            )
            self.assertEqual(
                [], connection.execute("PRAGMA foreign_key_check").fetchall()
            )

    def test_two_user_golden_path_and_required_countercases(self):
        # Two independent accounts start the same album through the real routes.
        alex_id = self.register_and_login(
            self.alex, name="Alex R3", username="r3_alex"
        )
        bela_id = self.register_and_login(
            self.bela, name="Bela R3", username="r3_bela"
        )
        self.assertNotEqual(alex_id, bela_id)
        for client in (self.alex, self.bela):
            self.assertEqual(302, client.post("/alben/hinzufuegen/vfl").status_code)
            self.assertEqual(302, client.post(
                "/album/vfl/privacy",
                data={"visibility": "public", "trade_pool_enabled": "1"},
            ).status_code)

        # Alex owns a duplicate of 1 and misses 2; Bela has the inverse state.
        for _ in range(2):
            self.assertEqual(200, self.alex.post(
                "/album/vfl/sticker/1/quantity", data={"delta": "1"}
            ).status_code)
            self.assertEqual(200, self.bela.post(
                "/album/vfl/sticker/2/quantity", data={"delta": "1"}
            ).status_code)
        self.assertEqual((2, 1), self.quantity(alex_id, "1"))
        self.assertEqual((2, 1), self.quantity(bela_id, "2"))
        self.assertIn('data-stack-quantity="2"', self.alex.get(
            "/album/vfl?filter=duplicate"
        ).get_data(as_text=True))
        self.assertIn('data-stack-quantity="0"', self.alex.get(
            "/album/vfl?filter=missing"
        ).get_data(as_text=True))

        # Public is read-only, while the owner wall keeps its inventory controls.
        public_wall = self.alex.get("/profil/r3_bela/album/vfl")
        self.assertEqual(200, public_wall.status_code)
        public_html = public_wall.get_data(as_text=True)
        self.assertNotIn("data-quantity-delta", public_html)
        self.assertNotIn("albumSettingsDialog", public_html)
        owner_html = self.bela.get("/album/vfl").get_data(as_text=True)
        self.assertIn("data-quantity-delta", owner_html)
        self.assertIn("albumSettingsDialog", owner_html)

        # Privacy hides direct reads but does not silently disable an enabled pool.
        self.assertEqual(302, self.bela.post(
            "/album/vfl/privacy",
            data={"visibility": "private", "trade_pool_enabled": "1"},
        ).status_code)
        self.assertEqual(404, self.alex.get("/profil/r3_bela/album/vfl").status_code)
        self.assertIn("r3_bela", self.alex.get(
            "/album/vfl/trades?tab=partners"
        ).get_data(as_text=True))
        self.assertEqual(302, self.bela.post(
            "/album/vfl/privacy",
            data={"visibility": "public", "trade_pool_enabled": "1"},
        ).status_code)

        # A bidirectional block removes discovery and prevents direct mutation.
        self.assertEqual(302, self.alex.post("/profil/r3_bela/block").status_code)
        self.assertNotIn("r3_bela", self.alex.get(
            "/album/vfl/trades?tab=partners"
        ).get_data(as_text=True))
        self.alex.post(
            f"/album/vfl/trade/{bela_id}/request",
            data={"give_codes": ["1"], "get_codes": ["2"]},
        )
        self.assertIsNone(self.trade_row(alex_id, bela_id))
        self.assertEqual(302, self.alex.post("/profil/r3_bela/unblock").status_code)

        # Partner discovery, manual request and recipient notification.
        partners = self.alex.get("/album/vfl/trades?tab=partners")
        self.assertEqual(200, partners.status_code)
        self.assertIn("r3_bela", partners.get_data(as_text=True))
        request_response = self.alex.post(
            f"/album/vfl/trade/{bela_id}/request",
            data={"give_codes": ["1"], "get_codes": ["2"]},
        )
        self.assertEqual(302, request_response.status_code)
        trade = self.trade_row(alex_id, bela_id)
        self.assertIsNotNone(trade)
        trade_id = trade["id"]
        self.assertEqual("open", trade["status"])
        with self.connection() as connection:
            self.assertEqual(1, connection.execute(
                """
                SELECT COUNT(*) FROM notifications
                WHERE user_id=? AND notification_type='trade_request_created'
                  AND target_id=?
                """,
                (bela_id, trade_id),
            ).fetchone()[0])

        # Direct URL and reload work for both participants, never for an outsider.
        for client in (self.alex, self.bela):
            first = client.get(f"/trades/{trade_id}")
            refreshed = client.get(f"/trades/{trade_id}")
            self.assertEqual((200, 200), (first.status_code, refreshed.status_code))
        with self.outsider.session_transaction() as session:
            session["user_id"] = 3
        self.assertEqual(302, self.outsider.get(f"/trades/{trade_id}").status_code)
        self.outsider.post(f"/trade/{trade_id}/accept")
        self.assertEqual("open", self.trade_row(alex_id, bela_id)["status"])

        # Acceptance reserves both physical duplicates and protects availability.
        self.assertEqual(302, self.bela.post(f"/trade/{trade_id}/accept").status_code)
        with self.connection() as connection:
            reservations = connection.execute(
                """
                SELECT r.user_id, r.sticker_code, r.quantity, r.state
                FROM trade_reservations r
                JOIN trades t ON t.id=r.trade_id
                WHERE t.legacy_trade_request_id=?
                ORDER BY r.user_id, r.sticker_code
                """,
                (trade_id,),
            ).fetchall()
        self.assertEqual(
            [(alex_id, "1", 1, "active"), (bela_id, "2", 1, "active")],
            [tuple(row) for row in reservations],
        )
        denied = self.alex.post(
            "/album/vfl/sticker/1/quantity", data={"delta": "-1"}
        )
        self.assertEqual(200, denied.status_code)
        self.assertEqual(2, denied.get_json()["quantity"])
        self.assertEqual((2, 1), self.quantity(alex_id, "1"))
        self.outsider.post(f"/trade/{trade_id}/ship")
        self.outsider.post(f"/trade/{trade_id}/receive")

        # Both sides ship and receive; only the final receipt books inventory.
        self.assertEqual(302, self.alex.post(f"/trade/{trade_id}/ship").status_code)
        self.assertEqual(302, self.bela.post(f"/trade/{trade_id}/ship").status_code)
        before_receipt = (
            self.quantity(alex_id, "1"), self.quantity(bela_id, "2")
        )
        self.assertEqual(302, self.alex.post(f"/trade/{trade_id}/receive").status_code)
        self.assertEqual(before_receipt, (
            self.quantity(alex_id, "1"), self.quantity(bela_id, "2")
        ))
        self.assertEqual(302, self.bela.post(f"/trade/{trade_id}/receive").status_code)
        self.assertEqual("completed", self.trade_row(alex_id, bela_id)["status"])
        self.assertEqual((1, 0), self.quantity(alex_id, "1"))
        self.assertEqual((1, 0), self.quantity(alex_id, "2"))
        self.assertEqual((1, 0), self.quantity(bela_id, "1"))
        self.assertEqual((1, 0), self.quantity(bela_id, "2"))
        with self.connection() as connection:
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM trade_reservations r
                JOIN trades t ON t.id=r.trade_id
                WHERE t.legacy_trade_request_id=? AND r.state='active'
                """,
                (trade_id,),
            ).fetchone()[0])
            notification_types = {
                row[0] for row in connection.execute(
                    """
                    SELECT DISTINCT notification_type FROM notifications
                    WHERE user_id IN (?, ?)
                    """,
                    (alex_id, bela_id),
                )
            }
        self.assertTrue(
            {"trade_request_created", "trade_shipped", "trade_rating_available"}
            <= notification_types
        )

        # Completed state, inbox, public profile and wall survive refreshes.
        completed = self.alex.get(f"/trades/{trade_id}")
        self.assertEqual(200, completed.status_code)
        self.assertIn("Abgeschlossen", completed.get_data(as_text=True))
        inbox = self.bela.post("/notifications")
        self.assertEqual(200, inbox.status_code)
        self.assertIn("Tauschanfrage", inbox.get_data(as_text=True))
        self.assertEqual(200, self.alex.get("/profil/r3_bela").status_code)
        self.assertEqual(200, self.alex.get("/profil/r3_bela/album/vfl").status_code)

        # Anonymous direct URLs are login-gated and cannot mutate the completed trade.
        anonymous = webapp.app.test_client()
        self.assertEqual("/login", anonymous.get(
            f"/trades/{trade_id}"
        ).headers["Location"])
        anonymous.post(f"/trade/{trade_id}/receive", csrf_protect=False)
        self.assertEqual("completed", self.trade_row(alex_id, bela_id)["status"])
        self.assert_database_health()


if __name__ == "__main__":
    unittest.main()
