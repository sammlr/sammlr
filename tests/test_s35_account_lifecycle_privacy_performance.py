import hashlib
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
    / "s35-account-lifecycle-privacy-performance.md"
)

sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, load_migrations, migrate, rollback  # noqa: E402
from services.account_lifecycle import (  # noqa: E402
    ACTIVE,
    ANONYMIZED,
    DEACTIVATED,
    AccountDataInventoryService,
    AccountLifecycleCode,
    AccountLifecycleService,
)
from services.album_privacy import AlbumPrivacyService  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.community import CommunityService  # noqa: E402


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AccountLifecyclePrivacyPerformanceTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s35-")
        self.db_path = Path(self.temp_dir.name) / "s35.db"
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

    def terminalize_user_trades(self, connection, user_id=1, state="completed"):
        connection.execute(
            "UPDATE trade_requests SET status=? WHERE from_user_id=? OR to_user_id=?",
            (state, user_id, user_id),
        )
        connection.execute(
            """
            UPDATE trades SET lifecycle_state=?
            WHERE requester_user_id=? OR partner_user_id=?
            """,
            (state, user_id, user_id),
        )
        connection.commit()

    def test_v0012_forward_repeat_and_fail_closed_backout(self):
        self.assertEqual(21, load_migrations()[-1].version)
        with self.connect() as connection:
            self.assertEqual(18, current_version(connection))
            self.assertEqual((), migrate(connection, 18))
            self.assertEqual({ACTIVE}, {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT account_state FROM users"
                )
            })
            connection.execute(
                "UPDATE users SET account_state='deactivated' WHERE id=1"
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 11)
            self.assertEqual(18, current_version(connection))
            connection.execute("UPDATE users SET account_state='active' WHERE id=1")
            connection.commit()
            self.assertEqual((18, 17, 16, 15, 14, 13, 12), rollback(connection, 11))
            self.assertNotIn("account_state", {
                row[1] for row in connection.execute("PRAGMA table_info(users)")
            })
            self.assertEqual((12, 13, 14, 15, 16, 17, 18), migrate(connection, 18))

    def test_deactivate_invalidates_session_and_explicit_reactivation_creates_it(self):
        self.login_as(1)
        denied = self.client.post(
            "/profil/deactivate", data={"current_password": "wrong"}
        )
        self.assertEqual(403, denied.status_code)
        with self.connect() as connection:
            self.assertEqual(ACTIVE, connection.execute(
                "SELECT account_state FROM users WHERE id=1"
            ).fetchone()[0])

        response = self.client.post(
            "/profil/deactivate", data={"current_password": "fixture-only"}
        )
        self.assertEqual(302, response.status_code)
        with self.connect() as connection:
            self.assertEqual(DEACTIVATED, connection.execute(
                "SELECT account_state FROM users WHERE id=1"
            ).fetchone()[0])
        self.assertEqual(302, self.client.get("/").status_code)

        login = self.client.post("/login", data={
            "username": "fixture_user_1", "password": "fixture-only",
        })
        self.assertEqual("/konto/reaktivieren", login.headers["Location"])
        with self.client.session_transaction() as pending:
            self.assertNotIn("user_id", pending)
            self.assertEqual(1, pending["reactivation_user_id"])
        page = self.client.get("/konto/reaktivieren")
        self.assertIn("Konto reaktivieren", page.get_data(as_text=True))
        activated = self.client.post("/konto/reaktivieren")
        self.assertEqual("/", activated.headers["Location"])
        with self.client.session_transaction() as active_session:
            self.assertEqual(1, active_session["user_id"])
        with self.connect() as connection:
            self.assertEqual(ACTIVE, connection.execute(
                "SELECT account_state FROM users WHERE id=1"
            ).fetchone()[0])

    def test_anonymization_requires_both_confirmations_and_blocks_running_trade(self):
        self.login_as(1)
        missing_checkbox = self.client.post("/profil/delete", data={
            "current_password": "fixture-only",
        })
        self.assertEqual(400, missing_checkbox.status_code)
        wrong_password = self.client.post("/profil/delete", data={
            "current_password": "wrong", "confirm_anonymization": "yes",
        })
        self.assertEqual(403, wrong_password.status_code)

        with self.connect() as connection:
            connection.execute(
                """INSERT INTO trade_requests
                   (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                   VALUES ('vfl', 1, 2, '[]', '[]', 'open')"""
            )
            connection.commit()
        blocked = self.client.post("/profil/delete", data={
            "current_password": "fixture-only", "confirm_anonymization": "yes",
        })
        self.assertEqual(409, blocked.status_code)
        self.assertIn(
            "Dein Konto besitzt noch laufende Tauschaktionen",
            blocked.get_data(as_text=True),
        )

    def test_terminal_states_allow_anonymization_and_preserve_trade_history(self):
        for state in ("completed", "failed", "declined", "cancelled", "expired", "obsolete"):
            with self.subTest(state=state):
                database = Path(self.temp_dir.name) / f"terminal-{state}.db"
                shutil.copy2(FIXTURE, database)
                with sqlite3.connect(database) as connection:
                    connection.row_factory = sqlite3.Row
                    migrate(connection, 18)
                    connection.execute(
                        """INSERT INTO trade_requests
                           (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                           VALUES ('vfl', 1, 2, '[\"1\"]', '[\"2\"]', ?)""",
                        (state,),
                    )
                    connection.commit()
                    request_id = connection.execute(
                        "SELECT MAX(id) FROM trade_requests"
                    ).fetchone()[0]
                    result = AccountLifecycleService(connection).anonymize(
                        1, "fixture-only", True
                    )
                    self.assertEqual(AccountLifecycleCode.ANONYMIZED, result.code)
                    user = connection.execute(
                        "SELECT * FROM users WHERE id=1"
                    ).fetchone()
                    self.assertEqual(ANONYMIZED, user["account_state"])
                    self.assertIsNone(user["name"])
                    self.assertNotEqual("fixture_user_1", user["username"])
                    self.assertIsNotNone(connection.execute(
                        "SELECT 1 FROM trade_requests WHERE id=?", (request_id,)
                    ).fetchone())

    def test_anonymization_removes_personal_data_but_keeps_ratings_and_deleted_label(self):
        with self.connect() as connection:
            self.terminalize_user_trades(connection, 1)
            trade = connection.execute(
                "SELECT id FROM trades WHERE requester_user_id=1 OR partner_user_id=1 LIMIT 1"
            ).fetchone()
            if trade:
                connection.execute(
                    """INSERT OR IGNORE INTO trade_ratings
                       (trade_id, rater_user_id, rated_user_id, stars)
                       VALUES (?, 1, 2, 5)""",
                    (trade[0],),
                )
            rating_count = connection.execute(
                "SELECT COUNT(*) FROM trade_ratings WHERE rater_user_id=1 OR rated_user_id=1"
            ).fetchone()[0]
            result = AccountLifecycleService(connection).anonymize(
                1, "fixture-only", True
            )
            self.assertEqual(AccountLifecycleCode.ANONYMIZED, result.code)
            for table, condition in (
                ("stickers", "user_id=1"),
                ("user_albums", "user_id=1"),
                ("unlocked_trophies", "user_id=1"),
                ("notifications", "user_id=1"),
                ("friendship_requests", "requester_user_id=1 OR recipient_user_id=1"),
                ("friendships", "user_low_id=1 OR user_high_id=1"),
                ("blocks", "blocker_user_id=1 OR blocked_user_id=1"),
                ("user_activity", "user_id=1"),
            ):
                self.assertEqual(0, connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {condition}"
                ).fetchone()[0], table)
            self.assertEqual(rating_count, connection.execute(
                "SELECT COUNT(*) FROM trade_ratings WHERE rater_user_id=1 OR rated_user_id=1"
            ).fetchone()[0])

        self.login_as(2)
        with self.connect() as connection:
            historical = connection.execute(
                "SELECT id FROM trade_requests WHERE from_user_id=1 OR to_user_id=1 LIMIT 1"
            ).fetchone()
        if historical:
            detail = self.client.get(f"/trades/{historical[0]}")
            self.assertIn("Gelöschter Nutzer", detail.get_data(as_text=True))
            self.assertNotIn("__sammlr_anonymized_1__", detail.get_data(as_text=True))

    def test_inactive_accounts_are_absent_from_profile_search_matching_and_login(self):
        with self.connect() as connection:
            connection.execute(
                "UPDATE users SET account_state='deactivated' WHERE id=2"
            )
            connection.commit()
            self.assertIsNone(CollectorProfileService(connection).by_user_id(2, 1))
            self.assertEqual((), CommunityService(connection).search(1, "fixture_user_2"))
            self.assertNotIn(2, AlbumPrivacyService(connection).trade_pool_user_ids("vfl"))
            self.assertFalse(CommunityService(connection).can_start_interaction(1, 2))

        response = self.client.post("/login", data={
            "username": "fixture_user_2", "password": "fixture-only",
        })
        self.assertEqual("/konto/reaktivieren", response.headers["Location"])
        with self.client.session_transaction() as login_session:
            self.assertNotIn("user_id", login_session)

    def test_data_inventory_is_read_only_and_documents_export_foundation(self):
        with self.connect() as connection:
            before = connection.total_changes
            inventory = AccountDataInventoryService(connection).for_user(1)
            self.assertEqual(ACTIVE, inventory.account_state)
            self.assertIn("stickers", {category.key for category in inventory.categories})
            self.assertIn("trade_requests_sent", {
                category.key for category in inventory.categories
            })
            self.assertEqual(before, connection.total_changes)
        text = SPEC.read_text(encoding="utf-8")
        self.assertIn("100.000 Stickerpositionen", text)
        self.assertIn("20 gleichzeitige Requests", text)
        self.assertIn("über 1000 ms Release-Blocker", text)


if __name__ == "__main__":
    unittest.main()
