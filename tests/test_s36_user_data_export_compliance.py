import hashlib
import json
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
SPEC = (
    PROJECT_ROOT / "Dokumentation" / "Product Bible" / "roadmap"
    / "s36-data-export-compliance.md"
)

sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.user_data_export import (  # noqa: E402
    EXPORT_FORMAT_VERSION,
    UserDataExportService,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keys_recursive(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys_recursive(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys_recursive(child)


class UserDataExportComplianceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(
            TESTING=True,
            CSRF_ENABLED=True,
            TESTING_AUTH_VERSION_COMPAT=False,
        )

    @classmethod
    def tearDownClass(cls):
        webapp.app.config["TESTING_AUTH_VERSION_COMPAT"] = True
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s36-")
        self.db_path = Path(self.temp_dir.name) / "s36.db"
        shutil.copy2(FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 18)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def login_as(self, user_id=1):
        with self.connect() as connection:
            version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = version

    def seed_complete_export_data(self):
        with self.connect() as connection:
            connection.execute(
                "UPDATE users SET name='Välentin 🟣', favorite_album_id='vfl' WHERE id=1"
            )
            connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes,
                    status, from_confirmed, to_confirmed)
                   VALUES ('vfl', 1, 2, '[\"Ä1\"]', '[\"B2\"]',
                           'completed', 1, 1)"""
            )
            request_id = connection.execute(
                "SELECT MAX(id) FROM trade_requests"
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO trades
                   (legacy_trade_request_id, requester_user_id, partner_user_id,
                    lifecycle_state, completed_at)
                   VALUES (?, 1, 2, 'completed', CURRENT_TIMESTAMP)""",
                (request_id,),
            )
            trade_id = connection.execute("SELECT MAX(id) FROM trades").fetchone()[0]
            connection.execute(
                """INSERT INTO trade_positions
                   (trade_id, from_user_id, to_user_id, album_id, sticker_code, quantity)
                   VALUES (?, 2, 1, 'vfl', 'B2', 3)""",
                (trade_id,),
            )
            position_id = connection.execute(
                "SELECT MAX(id) FROM trade_positions"
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO trade_events
                   (trade_id, event_type, actor_user_id, payload_json)
                   VALUES (?, 'problem_reported', 1, '{\"note\":\"Größe beschädigt\"}')""",
                (trade_id,),
            )
            connection.execute(
                """INSERT INTO trade_reservations
                   (trade_id, trade_position_id, user_id, album_id, sticker_code,
                    quantity, state, released_at, release_reason)
                   VALUES (?, ?, 2, 'vfl', 'B2', 3, 'released',
                           CURRENT_TIMESTAMP, 'completed')""",
                (trade_id, position_id),
            )
            connection.execute(
                """INSERT INTO trade_shipping_status
                   (trade_id, requester_shipped, requester_shipped_at,
                    partner_shipped, partner_shipped_at)
                   VALUES (?, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)""",
                (trade_id,),
            )
            connection.execute(
                """INSERT INTO trade_receipt_status
                   (trade_id, requester_received, requester_received_at,
                    partner_received, partner_received_at)
                   VALUES (?, 1, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)""",
                (trade_id,),
            )
            connection.execute(
                """INSERT INTO trade_receipt_reports
                   (trade_id, receiver_user_id, receiver_side, state,
                    shipment_lost, resolved_at)
                   VALUES (?, 1, 'requester', 'resolved', 0, CURRENT_TIMESTAMP)""",
                (trade_id,),
            )
            report_id = connection.execute(
                "SELECT MAX(id) FROM trade_receipt_reports"
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO trade_receipt_report_positions
                   (report_id, trade_position_id, expected_quantity,
                    initial_received_quantity, resolution_received_quantity,
                    problem_type, state, resolved_at)
                   VALUES (?, ?, 3, 2, 1, 'missing', 'resolved', CURRENT_TIMESTAMP)""",
                (report_id, position_id),
            )
            connection.execute(
                """INSERT INTO trade_ratings
                   (trade_id, rater_user_id, rated_user_id, stars)
                   VALUES (?, 1, 2, 5)""",
                (trade_id,),
            )
            connection.execute(
                "INSERT INTO friendships (user_low_id, user_high_id) VALUES (1, 2)"
            )
            connection.execute(
                """INSERT INTO friendship_requests
                   (requester_user_id, recipient_user_id, status)
                   VALUES (1, 3, 'declined')"""
            )
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (1, 3)"
            )
            connection.execute(
                """INSERT INTO user_activity (user_id, last_active_at)
                   VALUES (1, '2026-08-09T12:00:00+00:00')
                   ON CONFLICT(user_id) DO UPDATE SET last_active_at=excluded.last_active_at"""
            )
            connection.execute(
                """INSERT INTO notifications
                   (user_id, title, body, is_read, notification_type)
                   VALUES (1, 'Grüße', 'Dein Tausch ist vollständig.', 0,
                           'trade_received')"""
            )
            connection.execute(
                """INSERT OR IGNORE INTO unlocked_trophies
                   (user_id, album_id, trophy_name)
                   VALUES (1, 'vfl', 'Überflieger')"""
            )
            connection.execute(
                """INSERT INTO login_throttle
                   (normalized_username, client_ip, failure_count,
                    window_started_at, locked_until, updated_at)
                   VALUES ('fixture_user_1', '127.0.0.1', 1,
                           '2026-08-09T12:00:00+00:00', NULL,
                           '2026-08-09T12:00:00+00:00')"""
            )
            connection.execute(
                """INSERT INTO stickers
                   (album_id, sticker_code, status, duplicates, quantity, user_id)
                   VALUES ('vfl', 'FOREIGN-SECRET', 'have', 8, 9, 2)"""
            )
            connection.commit()

    def test_complete_export_contains_owned_domains_and_trade_history(self):
        self.seed_complete_export_data()
        self.login_as(1)
        response = self.client.post(
            "/profil/datenexport", data={"current_password": "fixture-only"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response.mimetype)
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        document = json.loads(response.data.decode("utf-8"))

        self.assertEqual(EXPORT_FORMAT_VERSION, document["format_version"])
        self.assertEqual(1, document["subject_user_id"])
        self.assertEqual("Välentin 🟣", document["profile"]["display_name"])
        self.assertEqual("active", document["account"]["account_state"])
        self.assertEqual("public", document["account"]["profile_privacy"])
        self.assertEqual("vfl", document["favorites"]["favorite_album_id"])
        self.assertTrue(document["albums"])
        self.assertTrue(document["inventory"]["stickers"])
        self.assertTrue(document["trades"]["requests"])
        lifecycle = document["trades"]["lifecycle"][0]
        self.assertTrue(lifecycle["positions"])
        self.assertEqual("Größe beschädigt", lifecycle["events"][0]["payload_json"]["note"])
        self.assertEqual("missing", lifecycle["problem_history"][0]["positions"][0]["problem_type"])
        self.assertTrue(document["ratings"]["given"])
        self.assertTrue(document["community"]["friendships"])
        self.assertTrue(document["community"]["friendship_requests"])
        self.assertTrue(document["community"]["blocks"])
        self.assertIsNotNone(document["community"]["activity"])
        self.assertTrue(document["notifications"])
        self.assertTrue(document["trophies"])
        self.assertEqual([], document["feed_events"])
        self.assertTrue(document["login_security"])

        serialized = response.data.decode("utf-8")
        self.assertNotIn("FOREIGN-SECRET", serialized)
        self.assertNotIn("Fixture Person 2", serialized)
        self.assertNotIn("fixture_user_2", serialized)
        forbidden = {"password", "password_scheme", "auth_version", "csrf_token"}
        self.assertTrue(forbidden.isdisjoint(set(keys_recursive(document))))

    def test_empty_user_has_complete_empty_structure(self):
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO users
                   (id, username, password, password_scheme, auth_version, account_state)
                   VALUES (99, 'empty_export', 'unused', 'werkzeug_scrypt', 1, 'active')"""
            )
            connection.commit()
            document = UserDataExportService(connection).export_for_user(99).to_document()
        self.assertEqual([], document["albums"])
        self.assertEqual([], document["inventory"]["stickers"])
        self.assertEqual(0, document["inventory"]["summary"]["physical_quantity"])
        self.assertEqual([], document["trades"]["requests"])
        self.assertEqual([], document["trades"]["lifecycle"])
        self.assertEqual([], document["ratings"]["given"])
        self.assertEqual([], document["notifications"])
        self.assertEqual([], document["feed_events"])
        self.assertEqual([], document["community"]["friendships"])

    def test_large_collection_is_complete(self):
        rows = []
        for index in range(10_000):
            quantity = 1 + index % 4
            rows.append(
                ("vfl", f"LARGE-{index:05d}", "have", quantity - 1, quantity, 1)
            )
        with self.connect() as connection:
            connection.executemany(
                """INSERT INTO stickers
                   (album_id, sticker_code, status, duplicates, quantity, user_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows,
            )
            connection.commit()
            inserted_changes = connection.total_changes
            export = UserDataExportService(connection).export_for_user(1)
            self.assertEqual(inserted_changes, connection.total_changes)
        large = [
            row for row in export.inventory["stickers"]
            if row["sticker_code"].startswith("LARGE-")
        ]
        self.assertEqual(10_000, len(large))
        self.assertEqual("LARGE-00000", large[0]["sticker_code"])
        self.assertEqual("LARGE-09999", large[-1]["sticker_code"])

    def test_authentication_password_and_csrf_are_required(self):
        anonymous_get = self.client.get("/profil/datenexport")
        self.assertEqual("/login", anonymous_get.headers["Location"])
        anonymous_post = self.client.post(
            "/profil/datenexport",
            data={"current_password": "fixture-only"},
            csrf_protect=False,
        )
        self.assertEqual(403, anonymous_post.status_code)

        self.login_as(1)
        page = self.client.get("/profil/datenexport")
        self.assertEqual(200, page.status_code)
        self.assertIn("Aktuelles Passwort", page.get_data(as_text=True))
        wrong = self.client.post(
            "/profil/datenexport", data={"current_password": "wrong"}
        )
        self.assertEqual(403, wrong.status_code)
        missing_csrf = self.client.post(
            "/profil/datenexport",
            data={"current_password": "fixture-only"},
            csrf_protect=False,
        )
        self.assertEqual(403, missing_csrf.status_code)

    def test_json_is_utf8_human_readable_and_deterministic(self):
        self.seed_complete_export_data()
        self.login_as(1)
        first = self.client.post(
            "/profil/datenexport", data={"current_password": "fixture-only"}
        )
        second = self.client.post(
            "/profil/datenexport", data={"current_password": "fixture-only"}
        )
        self.assertEqual(first.data, second.data)
        self.assertIn("charset=utf-8", first.headers["Content-Type"].lower())
        decoded = first.data.decode("utf-8")
        self.assertIn("Välentin 🟣", decoded)
        self.assertIn("\n  \"profile\": {", decoded)
        self.assertNotIn("\\u00e4", decoded.lower())

    def test_public_compliance_pages_are_functional_without_export_link(self):
        for path, marker in (
            ("/datenschutz", "Datenschutzerklärung"),
            ("/impressum", "Impressum"),
            ("/datenexport-hinweise", "Exporthinweise"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code)
                html = response.get_data(as_text=True)
                self.assertIn(marker, html)
                self.assertNotIn('href="/profil/datenexport"', html)

        self.login_as(1)
        own_profile = self.client.get("/profil").get_data(as_text=True)
        self.assertIn('href="/account"', own_profile)
        account = self.client.get("/account").get_data(as_text=True)
        self.assertIn('href="/profil/datenexport"', account)

    def test_export_contract_documentation_and_no_schema_change(self):
        text = SPEC.read_text(encoding="utf-8")
        self.assertIn("UTF-8", text)
        self.assertIn("erneuter Passwortprüfung", text)
        self.assertIn("keine Migration", text)
        with self.connect() as connection:
            self.assertEqual(18, connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
