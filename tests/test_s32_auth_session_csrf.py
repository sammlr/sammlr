import atexit
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from werkzeug.security import check_password_hash, generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
SECURITY_DOC = (
    PROJECT_ROOT / "Dokumentation" / "Product Bible" / "security"
    / "s32-auth-session-csrf.md"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s32-bootstrap-")
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
from services.auth_security import (  # noqa: E402
    AuthSecurityService,
    AuthenticationCode,
    CANONICAL_PASSWORD_METHOD,
    LoginThrottleService,
)


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class AuthSessionCsrfTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(
            TESTING=True,
            TESTING_AUTH_VERSION_COMPAT=False,
            CSRF_ENABLED=True,
        )

    @classmethod
    def tearDownClass(cls):
        webapp.app.config["TESTING_AUTH_VERSION_COMPAT"] = True
        webapp.app.config.pop("AUTH_CLOCK", None)
        webapp.app.config.pop("CLIENT_IP_PROVIDER", None)
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s32-")
        self.db_path = Path(self.temp_dir.name) / "s32.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(tuple(range(1, 11)), migrate(connection, 10))
        webapp.DB = str(self.db_path)
        self.clock = MutableClock()
        webapp.app.config["AUTH_CLOCK"] = self.clock
        webapp.app.config["CLIENT_IP_PROVIDER"] = lambda: "203.0.113.10"
        self.client = webapp.app.test_client()

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        webapp.app.config.pop("AUTH_CLOCK", None)
        webapp.app.config.pop("CLIENT_IP_PROVIDER", None)
        self.temp_dir.cleanup()

    def login_as(self, user_id=1):
        with sqlite3.connect(self.db_path) as connection:
            version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = version

    def user(self, username="fixture_user_1"):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return dict(connection.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone())

    def test_v0010_forward_repeat_and_fail_closed_backout(self):
        self.assertEqual(29, load_migrations()[-1].version)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(10, current_version(connection))
            self.assertEqual((), migrate(connection, 10))
            schemes = {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT password_scheme FROM users"
                )
            }
            self.assertEqual({"legacy_plaintext"}, schemes)
            self.assertEqual({1}, {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT auth_version FROM users"
                )
            })
            self.assertIsNotNone(connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='login_throttle'"
            ).fetchone())
            self.assertEqual((10,), rollback(connection, 9))
            self.assertEqual(9, current_version(connection))
            self.assertEqual((10,), migrate(connection, 10))
            connection.execute(
                """
                UPDATE users SET password=?, password_scheme='werkzeug_scrypt'
                WHERE id=1
                """,
                (generate_password_hash("fixture-only", method=CANONICAL_PASSWORD_METHOD),),
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 9)
            self.assertEqual(10, current_version(connection))
            self.assertEqual("werkzeug_scrypt", connection.execute(
                "SELECT password_scheme FROM users WHERE id=1"
            ).fetchone()[0])

    def test_registration_stores_only_canonical_scrypt_and_hides_details(self):
        response = self.client.post("/register", data={
            "name": "Secure User",
            "username": "secure_user",
            "password": "correct horse battery staple",
            "password_repeat": "correct horse battery staple",
        })
        self.assertEqual(302, response.status_code)
        row = self.user("secure_user")
        self.assertEqual("werkzeug_scrypt", row["password_scheme"])
        self.assertEqual(1, row["auth_version"])
        self.assertNotEqual("correct horse battery staple", row["password"])
        self.assertTrue(row["password"].startswith(CANONICAL_PASSWORD_METHOD + "$"))
        self.assertTrue(check_password_hash(row["password"], "correct horse battery staple"))

        duplicate = self.client.post("/register", data={
            "username": "secure_user", "password": "another password",
            "password_repeat": "another password",
        })
        mismatch = self.client.post("/register", data={
            "username": "other", "password": "one", "password_repeat": "two",
        })
        expected = "Registrierung nicht möglich. Bitte prüfe deine Angaben."
        self.assertIn(expected, duplicate.get_data(as_text=True))
        self.assertIn(expected, mismatch.get_data(as_text=True))
        self.assertNotIn("bereits vergeben", duplicate.get_data(as_text=True))

    def test_legacy_login_migrates_only_after_success_and_rotates_session(self):
        before = self.user()
        self.assertEqual("legacy_plaintext", before["password_scheme"])
        wrong = self.client.post("/login", data={
            "username": "fixture_user_1", "password": "wrong",
        })
        self.assertEqual(200, wrong.status_code)
        self.assertIn("Benutzername oder Passwort ist falsch.", wrong.get_data(as_text=True))
        self.assertEqual(before["password"], self.user()["password"])
        self.assertEqual("legacy_plaintext", self.user()["password_scheme"])

        with self.client.session_transaction() as anonymous_session:
            anonymous_session["discard_me"] = "old"
            old_token = anonymous_session["csrf_token"]
        success = self.client.post("/login", data={
            "username": "fixture_user_1", "password": "fixture-only",
        })
        self.assertEqual(302, success.status_code)
        after = self.user()
        self.assertEqual("werkzeug_scrypt", after["password_scheme"])
        self.assertNotEqual("fixture-only", after["password"])
        self.assertTrue(check_password_hash(after["password"], "fixture-only"))
        with self.client.session_transaction() as authenticated_session:
            self.assertNotIn("discard_me", authenticated_session)
            self.assertFalse(authenticated_session.permanent)
            self.assertEqual(1, authenticated_session["user_id"])
            self.assertEqual(after["auth_version"], authenticated_session["auth_version"])
            self.assertNotEqual(old_token, authenticated_session["csrf_token"])

    def test_valid_noncanonical_hash_is_rehashed_after_success(self):
        old_hash = generate_password_hash(
            "fixture-only", method="scrypt:16384:8:1"
        )
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                UPDATE users SET password=?, password_scheme='werkzeug_scrypt'
                WHERE id=1
                """,
                (old_hash,),
            )
            connection.commit()
        response = self.client.post("/login", data={
            "username": "fixture_user_1", "password": "fixture-only",
        })
        self.assertEqual(302, response.status_code)
        current = self.user()["password"]
        self.assertNotEqual(old_hash, current)
        self.assertTrue(current.startswith(CANONICAL_PASSWORD_METHOD + "$"))

    def test_secret_and_cookie_contract(self):
        with patch.dict(os.environ, {"SAMMLR_ENV": "production"}, clear=True):
            with self.assertRaises(RuntimeError):
                webapp.configure_flask_security(Flask("missing-production-secret"))

        production = Flask("production")
        with patch.dict(os.environ, {
            "SAMMLR_ENV": "production", "SAMMLR_SECRET_KEY": "production-secret"
        }, clear=True):
            webapp.configure_flask_security(production)
        self.assertTrue(production.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual("Lax", production.config["SESSION_COOKIE_SAMESITE"])
        self.assertTrue(production.config["SESSION_COOKIE_SECURE"])
        self.assertIsNone(production.config["SESSION_COOKIE_DOMAIN"])

        development = Flask("development")
        output = io.StringIO()
        with patch.dict(os.environ, {"SAMMLR_ENV": "development"}, clear=True):
            with redirect_stdout(output):
                webapp.configure_flask_security(development)
        self.assertIn(
            "Temporary development secret active – sessions reset on restart.",
            output.getvalue(),
        )
        self.assertFalse(development.config["SESSION_COOKIE_SECURE"])

        direct_development = Flask("direct-development")
        direct_output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(direct_output):
                webapp.configure_flask_security(
                    direct_development, direct_development=True
                )
        self.assertEqual("development", direct_development.config["SAMMLR_ENV"])
        self.assertFalse(direct_development.config["SESSION_COOKIE_SECURE"])
        self.assertIn(
            "Temporary development secret active – sessions reset on restart.",
            direct_output.getvalue(),
        )
        self.assertEqual(
            "sammlr-explicit-testing-secret", webapp.app.config["SECRET_KEY"]
        )

        environment = os.environ.copy()
        environment.pop("SAMMLR_SECRET_KEY", None)
        environment["SAMMLR_ENV"] = "production"
        environment["PYTHONPATH"] = str(APP_DIR)
        probe = subprocess.run(
            [sys.executable, "-c", "import webapp"], cwd=APP_DIR,
            env=environment, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(0, probe.returncode)
        self.assertIn("SAMMLR_SECRET_KEY is required", probe.stderr)

    def test_csrf_blocks_missing_and_invalid_tokens_before_mutation(self):
        login_get = self.client.get("/login")
        html = login_get.get_data(as_text=True)
        self.assertIn('name="_csrf_token"', html)
        self.assertIn('name="csrf-token"', html)

        missing = self.client.post(
            "/login", data={"username": "fixture_user_1", "password": "fixture-only"},
            csrf_protect=False,
        )
        wrong = self.client.post(
            "/login", data={"username": "fixture_user_1", "password": "fixture-only"},
            headers={"X-CSRF-Token": "wrong"}, csrf_protect=False,
        )
        self.assertEqual(403, missing.status_code)
        self.assertEqual(403, wrong.status_code)
        self.assertEqual("legacy_plaintext", self.user()["password_scheme"])

        self.login_as()
        with sqlite3.connect(self.db_path) as connection:
            before = connection.execute(
                "SELECT COUNT(*) FROM stickers WHERE user_id=1"
            ).fetchone()[0]
        for path in (
            "/bulk_add/vfl", "/trade/999/accept", "/album/vfl/privacy",
            "/album/vfl/liste/trade", "/profil/fixture_user_2/block",
            "/trades/999/rating",
        ):
            with self.subTest(path=path):
                response = self.client.post(path, csrf_protect=False)
                self.assertEqual(403, response.status_code)
        with sqlite3.connect(self.db_path) as connection:
            self.assertEqual(before, connection.execute(
                "SELECT COUNT(*) FROM stickers WHERE user_id=1"
            ).fetchone()[0])

    def test_all_rendered_post_forms_receive_session_token(self):
        for path in ("/login", "/register"):
            html = self.client.get(path).get_data(as_text=True)
            self.assertEqual(html.count('<form method="POST"'), html.count('name="_csrf_token"'))
        self.login_as()
        for path in ("/profil", "/profil/password", "/album/vfl"):
            html = self.client.get(path).get_data(as_text=True)
            post_forms = html.count('method="POST"')
            self.assertGreater(post_forms, 0, path)
            self.assertEqual(post_forms, html.count('name="_csrf_token"'), path)

    def test_auth_version_mismatch_invalidates_session(self):
        self.login_as()
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("UPDATE users SET auth_version=2 WHERE id=1")
            connection.commit()
        response = self.client.get("/")
        self.assertEqual(302, response.status_code)
        self.assertEqual("/login", response.headers["Location"])
        with self.client.session_transaction() as invalidated_session:
            self.assertNotIn("user_id", invalidated_session)
            self.assertNotIn("auth_version", invalidated_session)

    def test_password_change_requires_current_password_and_invalidates_session(self):
        self.login_as()
        wrong = self.client.post("/profil/password", data={
            "current_password": "wrong", "new_password": "new-secure-password",
            "repeat_password": "new-secure-password",
        })
        self.assertEqual(200, wrong.status_code)
        self.assertIn("Passwort konnte nicht bestätigt werden.", wrong.get_data(as_text=True))
        self.assertEqual(1, self.user()["auth_version"])

        changed = self.client.post("/profil/password", data={
            "current_password": "fixture-only", "new_password": "new-secure-password",
            "repeat_password": "new-secure-password",
        })
        self.assertEqual(302, changed.status_code)
        self.assertEqual("/login", changed.headers["Location"])
        row = self.user()
        self.assertEqual(2, row["auth_version"])
        self.assertEqual("werkzeug_scrypt", row["password_scheme"])
        self.assertTrue(check_password_hash(row["password"], "new-secure-password"))
        with self.client.session_transaction() as changed_session:
            self.assertNotIn("user_id", changed_session)

    def test_account_delete_requires_current_password(self):
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 18)
        self.login_as(3)
        wrong = self.client.post("/profil/delete", data={
            "current_password": "wrong", "confirm_anonymization": "yes",
        })
        self.assertEqual(403, wrong.status_code)
        self.assertEqual(
            "Passwort konnte nicht bestätigt werden.", wrong.get_data(as_text=True)
        )
        self.assertIsNotNone(self.user("fixture_user_3"))

        unconfirmed = self.client.post(
            "/profil/delete", data={"current_password": "fixture-only"}
        )
        self.assertEqual(400, unconfirmed.status_code)
        deleted = self.client.post("/profil/delete", data={
            "current_password": "fixture-only", "confirm_anonymization": "yes",
        })
        self.assertEqual(302, deleted.status_code)
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT account_state FROM users WHERE id=3"
            ).fetchone()
            self.assertEqual("anonymized", row[0])
        with self.client.session_transaction() as deleted_session:
            self.assertNotIn("user_id", deleted_session)

    def test_throttling_limit_window_reset_and_key_isolation(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            service = AuthSecurityService(connection, now_provider=self.clock)
            for _ in range(5):
                result = service.authenticate(
                    "fixture_user_1", "wrong", "198.51.100.1"
                )
                self.assertEqual(AuthenticationCode.INVALID_CREDENTIALS, result.code)
            blocked = service.authenticate(
                "fixture_user_1", "fixture-only", "198.51.100.1"
            )
            self.assertEqual(AuthenticationCode.THROTTLED, blocked.code)
            other_ip = service.authenticate(
                "fixture_user_1", "fixture-only", "198.51.100.2"
            )
            self.assertEqual(AuthenticationCode.AUTHENTICATED, other_ip.code)

            self.clock.advance(minutes=15, seconds=1)
            success = service.authenticate(
                "fixture_user_1", "fixture-only", "198.51.100.1"
            )
            self.assertEqual(AuthenticationCode.AUTHENTICATED, success.code)
            self.assertIsNone(connection.execute(
                """
                SELECT 1 FROM login_throttle
                WHERE normalized_username='fixture_user_1'
                  AND client_ip='198.51.100.1'
                """
            ).fetchone())

            for _ in range(2):
                service.authenticate("fixture_user_2", "wrong", "198.51.100.3")
            reset = service.authenticate(
                "fixture_user_2", "fixture-only", "198.51.100.3"
            )
            self.assertEqual(AuthenticationCode.AUTHENTICATED, reset.code)
            self.assertIsNone(connection.execute(
                "SELECT 1 FROM login_throttle WHERE normalized_username='fixture_user_2'"
            ).fetchone())

    def test_throttle_route_returns_429_without_enumeration(self):
        for username in ("fixture_user_1", "unknown_user"):
            client = webapp.app.test_client()
            webapp.app.config["CLIENT_IP_PROVIDER"] = lambda username=username: (
                "192.0.2.11" if username == "fixture_user_1" else "192.0.2.12"
            )
            for _ in range(5):
                response = client.post("/login", data={
                    "username": username, "password": "wrong"
                })
                self.assertEqual(200, response.status_code)
                self.assertIn(
                    "Benutzername oder Passwort ist falsch.",
                    response.get_data(as_text=True),
                )
            blocked = client.post("/login", data={
                "username": username, "password": "wrong"
            })
            self.assertEqual(429, blocked.status_code)
            body = blocked.get_data(as_text=True)
            self.assertIn(
                "Anmeldung momentan nicht möglich. Bitte versuche es später erneut.",
                body,
            )
            self.assertNotIn("existiert", body)
            self.assertNotIn("gesperrt", body)

    def test_s33_hardened_route_methods_preserve_s32_csrf_contract(self):
        document = SECURITY_DOC.read_text(encoding="utf-8")
        for path in (
            "/debug-seed-now", "/logout", "/favorit/toggle/<album_id>",
            "/alben/hinzufuegen/<album_id>", "/add/<album_id>/<code>",
            "/undo", "/notifications/<id>/read",
        ):
            self.assertIn(path, document)
        self.assertIn("S33", document)
        logout_rule = next(rule for rule in webapp.app.url_map.iter_rules() if rule.rule == "/logout")
        self.assertEqual({"POST", "OPTIONS"}, logout_rule.methods)
        for path in (
            "/favorit/toggle/<album_id>",
            "/alben/hinzufuegen/<album_id>",
            "/add/<album_id>/<path:code>",
            "/remove/<album_id>/<path:code>",
            "/undo",
            "/notifications/<int:notification_id>/read",
        ):
            rule = next(rule for rule in webapp.app.url_map.iter_rules() if rule.rule == path)
            self.assertEqual({"POST", "OPTIONS"}, rule.methods)


if __name__ == "__main__":
    unittest.main()
