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
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb006-bootstrap-")
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    migrate,
    rollback,
)
from services.album_privacy import AlbumPrivacyService  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.profile_privacy import (  # noqa: E402
    DEFAULT_PROFILE_PRIVACY,
    PROFILE_PRIVACIES,
    ProfilePrivacyService,
    ProfilePrivacyUpdateCode,
)


class ProfilePrivacyGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)
        _bootstrap_dir.cleanup()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb006-")
        self.db_path = Path(self.temp_dir.name) / "privacy.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 17)
            connection.execute("DELETE FROM blocks")
            connection.execute("DELETE FROM friendships")
            connection.execute("DELETE FROM friendship_requests")
            connection.execute(
                "UPDATE users SET username='viewer', name='Viewer', "
                "account_state='active', profile_privacy='public' WHERE id=1"
            )
            connection.execute(
                "UPDATE users SET username='owner', name='Owner Secret', "
                "account_state='active', profile_privacy='public' WHERE id=2"
            )
            connection.execute(
                "UPDATE users SET username='other', name='Other', "
                "account_state='active', profile_privacy='public' WHERE id=3"
            )
            for album_id, visibility, pool in (
                ("vfl", "public", 1),
                ("wm26", "friends", 0),
                ("em24", "private", 1),
            ):
                connection.execute(
                    """
                    INSERT INTO user_albums
                        (user_id, album_id, visibility, trade_pool_enabled)
                    VALUES (2, ?, ?, ?)
                    ON CONFLICT(user_id, album_id) DO UPDATE SET
                        visibility=excluded.visibility,
                        trade_pool_enabled=excluded.trade_pool_enabled
                    """,
                    (album_id, visibility, pool),
                )
            connection.execute(
                """
                INSERT INTO user_albums
                    (user_id, album_id, visibility, trade_pool_enabled)
                VALUES (1, 'vfl', 'private', 1)
                ON CONFLICT(user_id, album_id) DO UPDATE SET
                    visibility='private', trade_pool_enabled=1
                """
            )
            connection.execute("DELETE FROM stickers WHERE user_id=2")
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (2, ?, ?, 'owned', ?, ?)
                """,
                (
                    ("vfl", "1", 1, 2),
                    ("wm26", "ARG1", 0, 1),
                    ("em24", "FWC 1", 0, 1),
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (2, 'vfl', 'CB006 secret trophy', CURRENT_TIMESTAMP)
                """
            )
        webapp.DB = str(self.db_path)
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connect(self, path=None):
        connection = sqlite3.connect(path or self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id

    def set_profile_privacy(self, value, user_id=2):
        with self.connect() as connection:
            connection.execute(
                "UPDATE users SET profile_privacy=? WHERE id=?",
                (value, user_id),
            )

    def make_friends(self, first=1, second=2):
        low, high = sorted((first, second))
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
                (low, high),
            )

    def profile_html(self):
        response = self.client.get("/profil/owner")
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def assert_collector_world_hidden(self, html):
        self.assertIn("@owner", html)
        self.assertIn("Dieses Profil ist privat.", html)
        for secret in (
            "Owner Secret", "Sammelt gerade", "VfL Osnabrück",
            "FIFA World Cup 2026", "EURO 2024", "Doppelte",
            "Erfolgreiche Trades", "Trophäen", "Bewertung",
            "Wie gut kann dieser Nutzer mir helfen?", "CB006 secret trophy",
        ):
            self.assertNotIn(secret, html)

    def test_v0017_defaults_constraints_repeat_and_safe_backout(self):
        isolated = Path(self.temp_dir.name) / "migration.db"
        shutil.copy2(FIXTURE, isolated)
        with self.connect(isolated) as connection:
            migrate(connection, 16)
            before_albums = [tuple(row) for row in connection.execute(
                "SELECT user_id, album_id, visibility, trade_pool_enabled "
                "FROM user_albums ORDER BY user_id, album_id"
            )]
            user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            self.assertEqual((17,), migrate(connection, 17))
            self.assertEqual((), migrate(connection, 17))
            self.assertEqual(17, current_version(connection))
            self.assertEqual({"public"}, {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT profile_privacy FROM users"
                )
            })
            connection.execute(
                """
                INSERT INTO users
                    (username, password, name, password_scheme,
                     auth_version, account_state)
                VALUES ('cb006_new', 'unused', 'New',
                        'werkzeug_scrypt', 1, 'active')
                """
            )
            self.assertEqual(DEFAULT_PROFILE_PRIVACY, connection.execute(
                "SELECT profile_privacy FROM users WHERE username='cb006_new'"
            ).fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE users SET profile_privacy='friends' WHERE id=1"
                )
            self.assertEqual(before_albums, [tuple(row) for row in connection.execute(
                "SELECT user_id, album_id, visibility, trade_pool_enabled "
                "FROM user_albums ORDER BY user_id, album_id"
            )])
            self.assertEqual(user_count + 1, connection.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0])
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=1"
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 16)
            self.assertEqual(17, current_version(connection))
            connection.execute("UPDATE users SET profile_privacy='public'")
            connection.commit()
            self.assertEqual((17,), rollback(connection, 16))
            self.assertNotIn("profile_privacy", {
                row[1] for row in connection.execute("PRAGMA table_info(users)")
            })
            self.assertEqual((17,), migrate(connection, 17))

    def test_a_b_owner_always_sees_public_and_private_profile(self):
        for value in ("public", "private"):
            with self.subTest(case="A" if value == "public" else "B"):
                self.set_profile_privacy(value)
                self.login_as(2)
                html = self.client.get("/profil").get_data(as_text=True)
                self.assertIn("Sammelt gerade", html)
                self.assertNotIn("Owner Secret", html)
                with self.connect() as connection:
                    self.assertTrue(ProfilePrivacyService(
                        connection
                    ).can_view_collector_world(2, 2))
                self.login_as(1)

    def test_c_d_e_f_g_profile_gate_uses_only_mutual_friendship(self):
        with self.connect() as connection:
            policy = ProfilePrivacyService(connection)
            self.assertTrue(policy.can_view_collector_world(1, 2))  # C
        self.set_profile_privacy("private")
        self.assert_collector_world_hidden(self.profile_html())  # D
        self.make_friends()
        self.assertIn("Sammelt gerade", self.profile_html())  # E

        with self.connect() as connection:
            connection.execute("DELETE FROM friendships")
            connection.execute(
                """
                INSERT INTO friendship_requests
                    (requester_user_id, recipient_user_id, status)
                VALUES (1, 2, 'pending')
                """
            )
        self.assert_collector_world_hidden(self.profile_html())  # F
        with self.connect() as connection:
            connection.execute(
                "UPDATE friendship_requests SET status='accepted'"
            )
        self.assert_collector_world_hidden(self.profile_html())  # G

    def test_h_i_block_is_prior_to_public_or_private_gate(self):
        for value in ("public", "private"):
            with self.subTest(case="H" if value == "public" else "I"):
                self.set_profile_privacy(value)
                with self.connect() as connection:
                    connection.execute("DELETE FROM blocks")
                    connection.execute("DELETE FROM friendships")
                    connection.execute(
                        "INSERT INTO friendships (user_low_id, user_high_id) VALUES (1, 2)"
                    )
                    connection.execute(
                        "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
                    )
                html = self.profile_html()
                self.assertIn("Dieses Profil ist privat.", html)
                self.assertNotIn("Sammelt gerade", html)
                self.assertEqual(404, self.client.get(
                    "/profil/owner/album/vfl"
                ).status_code)

    def test_j_to_r_profile_then_album_matrix(self):
        cases = (
            ("J", "public", False, "vfl", 200),
            ("K", "public", False, "wm26", 404),
            ("L", "public", True, "wm26", 200),
            ("M", "public", True, "em24", 404),
            ("N", "private", False, "vfl", 404),
            ("O", "private", False, "wm26", 404),
            ("P", "private", True, "vfl", 200),
            ("Q", "private", True, "wm26", 200),
            ("R", "private", True, "em24", 404),
        )
        for case, privacy, friends, album_id, expected in cases:
            with self.subTest(case=case):
                with self.connect() as connection:
                    connection.execute("DELETE FROM friendships")
                    connection.execute("DELETE FROM blocks")
                    connection.execute(
                        "UPDATE users SET profile_privacy=? WHERE id=2",
                        (privacy,),
                    )
                    if friends:
                        connection.execute(
                            "INSERT INTO friendships (user_low_id, user_high_id) VALUES (1, 2)"
                        )
                self.assertEqual(expected, self.client.get(
                    f"/profil/owner/album/{album_id}"
                ).status_code)

    def test_s_t_deep_links_and_private_profile_do_not_leak_collector_data(self):
        self.set_profile_privacy("private")
        for path in (
            "/profil/owner/album/vfl",
            "/profil/owner/album/vfl/sticker/1",
            "/profil/owner/album/wm26",
            "/profil/owner/album/em24/sticker/FWC%201",
        ):
            response = self.client.get(path)
            self.assertEqual(404, response.status_code, path)
            body = response.get_data(as_text=True)
            self.assertNotIn("data-quantity", body)
            self.assertNotIn("Doppelte", body)
        self.assert_collector_world_hidden(self.profile_html())
        with self.connect() as connection:
            model = CollectorProfileService(connection).by_user_id(2, 1)
        self.assertFalse(model.collector_world_visible)
        self.assertEqual((), model.albums)
        self.assertEqual((0, 0, 0), (
            model.duplicate_count,
            model.successful_trade_count,
            model.trophy_count,
        ))

    def test_denied_profile_stops_before_sensitive_projection_queries(self):
        self.set_profile_privacy("private")
        with self.connect() as connection:
            statements = []
            before = connection.total_changes
            connection.set_trace_callback(statements.append)
            model = CollectorProfileService(connection).by_user_id(2, 1)
            connection.set_trace_callback(None)
            self.assertEqual(before, connection.total_changes)
        self.assertFalse(model.collector_world_visible)
        normalized = "\n".join(statements).lower()
        for sensitive_table in (
            " from user_albums", " from stickers", " from trade_requests",
            " from trades", " from trade_ratings", " from unlocked_trophies",
            " from canonical_trophy_unlocks", " from historical_album_records",
        ):
            self.assertNotIn(sensitive_table, normalized)

    def test_u_v_w_setting_changes_only_profile_privacy(self):
        with self.connect() as connection:
            before = [tuple(row) for row in connection.execute(
                "SELECT album_id, visibility, trade_pool_enabled "
                "FROM user_albums WHERE user_id=2 ORDER BY album_id"
            )]
            pool_before = AlbumPrivacyService(
                connection
            ).trade_pool_user_ids("vfl")
        self.login_as(2)
        page = self.client.get("/profil/privacy")
        self.assertEqual(200, page.status_code)
        self.assertIn("Album-Sichtbarkeit und Tradepool bleiben separat", page.get_data(as_text=True))
        for value in ("private", "public"):
            response = self.client.post(
                "/profil/privacy", data={"profile_privacy": value}
            )
            self.assertEqual(302, response.status_code)
            with self.connect() as connection:
                self.assertEqual(value, connection.execute(
                    "SELECT profile_privacy FROM users WHERE id=2"
                ).fetchone()[0])
                self.assertEqual(before, [tuple(row) for row in connection.execute(
                    "SELECT album_id, visibility, trade_pool_enabled "
                    "FROM user_albums WHERE user_id=2 ORDER BY album_id"
                )])
                self.assertEqual(pool_before, AlbumPrivacyService(
                    connection
                ).trade_pool_user_ids("vfl"))
        self.assertEqual(400, self.client.post(
            "/profil/privacy", data={"profile_privacy": "friends"}
        ).status_code)

    def test_x_y_existing_and_new_users_default_public(self):
        with self.connect() as connection:
            self.assertEqual({"public"}, {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT profile_privacy FROM users WHERE id IN (1, 2, 3, 7)"
                )
            })
        response = self.client.post("/register", data={
            "name": "New User",
            "username": "cb006_registered",
            "password": "secret",
            "password_repeat": "secret",
        })
        self.assertEqual(302, response.status_code)
        with self.connect() as connection:
            self.assertEqual("public", connection.execute(
                "SELECT profile_privacy FROM users WHERE username='cb006_registered'"
            ).fetchone()[0])
        self.assertEqual({"public", "private"}, set(PROFILE_PRIVACIES))

    def test_z_unknown_privacy_and_invalid_ids_fail_closed(self):
        with self.connect() as connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute(
                "UPDATE users SET profile_privacy='broken' WHERE id=2"
            )
            connection.execute("PRAGMA ignore_check_constraints=OFF")
            policy = ProfilePrivacyService(connection)
            self.assertFalse(policy.can_view_collector_world(1, 2))
            self.assertFalse(policy.can_view_collector_world("bad", 2))
            self.assertFalse(policy.can_view_collector_world(1, "bad"))
            self.assertEqual(
                ProfilePrivacyUpdateCode.UNAUTHORIZED,
                policy.update(1, 2, "public").code,
            )
        self.assert_collector_world_hidden(self.profile_html())
        self.assertEqual(404, self.client.get(
            "/profil/owner/album/vfl"
        ).status_code)


if __name__ == "__main__":
    unittest.main()
