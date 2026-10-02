import atexit
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s34-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402
from App.Database.sqlite_recovery import (  # noqa: E402
    create_backup,
    prune_expired_backups,
    restore_to_isolated_copy,
    sha256_file,
    validate_artifact,
)
from App.services.observability import JsonErrorTracker  # noqa: E402
from App.services.runtime_operations import (  # noqa: E402
    RuntimeConfigurationError,
    validate_production_environment,
)
from Scripts.predeploy import run_predeploy  # noqa: E402


def exploding_s34_test_route():
    raise RuntimeError("password=must-not-appear token=must-not-appear")


def explicit_s34_test_500_route():
    return "internal-only-detail-must-not-be-tracked", 500


if "s34_test_error" not in webapp.app.view_functions:
    webapp.app.add_url_rule(
        "/_s34-test-error", "s34_test_error", exploding_s34_test_route
    )
if "s34_test_500" not in webapp.app.view_functions:
    webapp.app.add_url_rule(
        "/_s34-test-500", "s34_test_500", explicit_s34_test_500_route
    )


class DeploymentRecoveryObservabilityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256_file(LOCAL_DB)
        cls.fixture_hash = sha256_file(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256_file(LOCAL_DB)
        assert cls.fixture_hash == sha256_file(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s34-")
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "s34.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 20)
        webapp.DB = str(self.db_path)
        webapp.app.config.update(
            TESTING=True,
            PROPAGATE_EXCEPTIONS=False,
            CSRF_ENABLED=True,
            TESTING_AUTH_VERSION_COMPAT=True,
        )
        self.request_log = io.StringIO()
        self.error_log = io.StringIO()
        webapp.app.config["REQUEST_LOG_STREAM"] = self.request_log
        webapp.app.config["ERROR_TRACKER"] = JsonErrorTracker(self.error_log)
        self.client = webapp.app.test_client()

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256_file(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256_file(REFERENCE_FIXTURE))
        webapp.app.config.pop("REQUEST_LOG_STREAM", None)
        webapp.app.config["ERROR_TRACKER"] = JsonErrorTracker()
        self.temp_dir.cleanup()

    def login_as(self, user_id=1):
        with sqlite3.connect(self.db_path) as connection:
            auth_version = connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (user_id,)
            ).fetchone()[0]
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id
            login_session["auth_version"] = auth_version

    def request_events(self):
        return [json.loads(line) for line in self.request_log.getvalue().splitlines()]

    def test_production_configuration_is_fail_closed_and_path_is_exact(self):
        valid = {
            "SAMMLR_ENV": "production",
            "SAMMLR_SECRET_KEY": "external-test-secret",
            "DATABASE_PATH": "/var/data/sammlr.db",
            "PORT": "8000",
        }
        self.assertEqual(Path("/var/data/sammlr.db"), validate_production_environment(valid))
        for key in ("SAMMLR_SECRET_KEY", "DATABASE_PATH", "PORT"):
            invalid = dict(valid)
            invalid.pop(key)
            with self.subTest(missing=key), self.assertRaises(RuntimeConfigurationError):
                validate_production_environment(invalid)
        invalid = dict(valid, DATABASE_PATH="relative.db")
        with self.assertRaises(RuntimeConfigurationError):
            validate_production_environment(invalid)
        invalid = dict(valid, SAMMLR_ENV="development")
        with self.assertRaises(RuntimeConfigurationError):
            validate_production_environment(invalid)

    def test_gunicorn_import_contract_and_proxyfix_are_production_only(self):
        probe = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'App')
import services.runtime_operations as runtime
runtime.PRODUCTION_DATABASE_PATH = Path(os.environ['DATABASE_PATH'])
from gunicorn.util import import_app
application = import_app('webapp:app')
middleware = application.wsgi_app
print(json.dumps({
    'app': application.name,
    'middleware': type(middleware).__name__,
    'x_for': middleware.x_for,
    'x_proto': middleware.x_proto,
    'x_host': middleware.x_host,
    'x_port': middleware.x_port,
    'x_prefix': middleware.x_prefix,
}))
"""
        environment = os.environ.copy()
        environment.update({
            "SAMMLR_ENV": "production",
            "SAMMLR_SECRET_KEY": "external-test-secret",
            "DATABASE_PATH": str(self.db_path),
            "PORT": "8000",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=PROJECT_ROOT, env=environment,
            text=True, capture_output=True, timeout=15, check=True,
        )
        contract = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual("webapp", contract["app"])
        self.assertEqual("ProxyFix", contract["middleware"])
        self.assertEqual((1, 1, 1, 0, 0), tuple(
            contract[key] for key in ("x_for", "x_proto", "x_host", "x_port", "x_prefix")
        ))
        self.assertNotEqual("ProxyFix", type(webapp.app.wsgi_app).__name__)

    def test_health_is_public_and_requires_database_v0011(self):
        healthy = self.client.get("/healthz")
        self.assertEqual(200, healthy.status_code)
        self.assertEqual({"status": "ok"}, healthy.get_json())

        wrong_version = self.root / "wrong-version.db"
        shutil.copy2(REFERENCE_FIXTURE, wrong_version)
        with sqlite3.connect(wrong_version) as connection:
            migrate(connection, 10)
        webapp.DB = str(wrong_version)
        self.assertEqual(503, self.client.get("/healthz").status_code)
        webapp.DB = str(self.root / "missing.db")
        failed = self.client.get("/healthz")
        self.assertEqual(503, failed.status_code)
        self.assertNotIn(str(self.root), failed.get_data(as_text=True))

    def test_request_id_is_generated_accepted_or_replaced_and_returned(self):
        generated = self.client.get("/healthz").headers["X-Request-ID"]
        self.assertRegex(generated, r"^[a-f0-9]{32}$")
        accepted = self.client.get(
            "/healthz", headers={"X-Request-ID": "beta.safe-Request_42"}
        )
        self.assertEqual("beta.safe-Request_42", accepted.headers["X-Request-ID"])
        rejected = self.client.get(
            "/healthz", headers={"X-Request-ID": "unsafe value/" + "x" * 80}
        )
        self.assertNotEqual(
            "unsafe value/" + "x" * 80, rejected.headers["X-Request-ID"]
        )

    def test_json_request_log_has_contract_and_redacts_sensitive_input(self):
        self.client.post("/login", data={
            "username": "private-username",
            "password": "private-password",
            "current_password": "private-current",
            "new_password": "private-new",
            "confirm_password": "private-confirm",
            "_csrf_token": "private-csrf",
        }, csrf_protect=False)
        event = self.request_events()[-1]
        self.assertEqual(
            {"timestamp", "level", "request_id", "method", "path", "status", "duration_ms"},
            set(event),
        )
        self.assertEqual("/login", event["path"])
        serialized = self.request_log.getvalue()
        for sensitive in (
            "private-username", "private-password", "private-current",
            "private-new", "private-confirm", "private-csrf",
        ):
            self.assertNotIn(sensitive, serialized)

    def test_unexpected_500_is_sanitized_but_expected_4xx_is_not_error_event(self):
        self.login_as(1)
        response = self.client.get("/_s34-test-error")
        self.assertEqual(500, response.status_code)
        event = json.loads(self.error_log.getvalue().splitlines()[-1])
        self.assertEqual("unhandled_exception", event["event"])
        self.assertEqual("RuntimeError", event["error_class"])
        self.assertEqual("/_s34-test-error", event["route"])
        self.assertNotIn("must-not-appear", self.error_log.getvalue())
        count = len(self.error_log.getvalue().splitlines())
        self.client.get("/definitely-not-found")
        self.assertEqual(count, len(self.error_log.getvalue().splitlines()))
        explicit = self.client.get("/_s34-test-500")
        self.assertEqual(500, explicit.status_code)
        explicit_event = json.loads(self.error_log.getvalue().splitlines()[-1])
        self.assertEqual("Http500Response", explicit_event["error_class"])
        self.assertNotIn("internal-only-detail", self.error_log.getvalue())

    def test_backup_is_consistent_private_versioned_and_hashed(self):
        backup = create_backup(
            self.db_path, self.root / "backups",
            now=datetime(2026, 8, 9, 12, 34, 56, tzinfo=timezone.utc),
        )
        self.assertEqual("sammlr-20260809-123456-v0020.db", backup.path.name)
        self.assertEqual(20, backup.version)
        self.assertEqual(sha256_file(backup.path), backup.sha256)
        self.assertEqual(0o600, stat.S_IMODE(backup.path.stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE(backup.path.parent.stat().st_mode))
        with sqlite3.connect(self.db_path) as source, sqlite3.connect(backup.path) as copied:
            self.assertEqual(
                source.execute("SELECT COUNT(*) FROM stickers").fetchone(),
                copied.execute("SELECT COUNT(*) FROM stickers").fetchone(),
            )

    def test_restore_is_isolated_validated_and_never_overwrites(self):
        backup = create_backup(self.db_path, self.root / "backups")
        source_hash = sha256_file(backup.path)
        recovery_path = self.root / "recovery" / "sammlr-recovered.db"
        recovered = restore_to_isolated_copy(backup.path, recovery_path)
        self.assertEqual(20, recovered.version)
        self.assertEqual(source_hash, sha256_file(backup.path))
        with self.assertRaises(FileExistsError):
            restore_to_isolated_copy(backup.path, recovery_path)
        self.assertEqual(source_hash, sha256_file(backup.path))

    def test_predeploy_backs_up_before_migrating_and_aborts_invalid_artifact(self):
        database = self.root / "predeploy.db"
        shutil.copy2(REFERENCE_FIXTURE, database)
        with sqlite3.connect(database) as connection:
            migrate(connection, 10)
        result = run_predeploy(database, self.root / "predeploy-backups")
        self.assertEqual(10, result["backup_version"])
        self.assertEqual(
            [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            result["applied_migrations"],
        )
        self.assertEqual(20, result["database_version"])
        with sqlite3.connect(database) as connection:
            self.assertEqual(20, current_version(connection))
        validate_artifact(database, expected_version=20)

    def test_wrong_version_blocks_restore(self):
        database = self.root / "v10.db"
        shutil.copy2(REFERENCE_FIXTURE, database)
        with sqlite3.connect(database) as connection:
            migrate(connection, 10)
        backup = create_backup(database, self.root / "backups")
        with self.assertRaises(RuntimeConfigurationError):
            restore_to_isolated_copy(backup.path, self.root / "recovery.db")

    def test_retention_removes_only_expired_owned_backup_names(self):
        backup_dir = self.root / "backups"
        backup_dir.mkdir()
        old = backup_dir / "sammlr-20260601-000000-v0011.db"
        recent = backup_dir / "sammlr-20260808-000000-v0011.db"
        foreign = backup_dir / "important.db"
        for path in (old, recent, foreign):
            path.write_bytes(b"not-a-database")
        old_time = datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
        recent_time = datetime(2026, 8, 8, tzinfo=timezone.utc).timestamp()
        os.utime(old, (old_time, old_time))
        os.utime(recent, (recent_time, recent_time))
        removed = prune_expired_backups(
            backup_dir, now=datetime(2026, 8, 9, tzinfo=timezone.utc)
        )
        self.assertEqual((old.resolve(),), removed)
        self.assertTrue(recent.exists())
        self.assertTrue(foreign.exists())

    def test_recovery_copy_passes_read_only_application_smoke(self):
        backup = create_backup(self.db_path, self.root / "backups")
        recovered = restore_to_isolated_copy(
            backup.path, self.root / "recovered.db"
        )
        webapp.DB = str(recovered.path)
        self.assertEqual(200, self.client.get("/healthz").status_code)
        self.assertEqual(200, self.client.get("/login").status_code)
        self.assertEqual(302, self.client.get("/").status_code)
        self.assertEqual(200, self.client.get("/static/style.css").status_code)
        self.login_as(1)
        for path in ("/", "/sammlung", "/trades", "/profil", "/notifications"):
            with self.subTest(path=path):
                self.assertEqual(200, self.client.get(path).status_code)

    def test_app_import_performs_no_schema_creation(self):
        missing_database = self.root / "not-created.db"
        probe = "import sys; sys.path.insert(0, 'App'); import webapp"
        environment = os.environ.copy()
        environment.update({
            "SAMMLR_ENV": "development",
            "DATABASE_PATH": str(missing_database),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        environment.pop("SAMMLR_SECRET_KEY", None)
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=PROJECT_ROOT, env=environment,
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(missing_database.exists())


if __name__ == "__main__":
    unittest.main()
