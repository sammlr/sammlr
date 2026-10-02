import atexit
import inspect
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

_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-phase7-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402


class Phase7EngineeringHardeningTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-phase7-")
        self.db_path = Path(self.temp_dir.name) / "phase7.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with sqlite3.connect(self.db_path) as connection:
            migrate(connection, 18)
        webapp.DB = str(self.db_path)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "fixture_user_1"
            session["auth_version"] = 1

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def test_stored_profile_values_are_attribute_escaped(self):
        payload = '\"><svg onload="alert(1)'
        with self.connect() as connection:
            connection.execute("UPDATE users SET name=?, username=? WHERE id=1", (payload, payload))
            connection.commit()

        name_page = self.client.get("/profil/name").get_data(as_text=True)
        username_page = self.client.get("/profil/username").get_data(as_text=True)
        for page in (name_page, username_page):
            self.assertNotIn('<svg onload="alert(1)', page)
            self.assertIn("&quot;&gt;&lt;svg", page)

    def test_oversized_stored_fields_are_rejected_server_side(self):
        with self.connect() as connection:
            before = connection.execute(
                "SELECT name, username FROM users WHERE id=1"
            ).fetchone()

        self.assertEqual(200, self.client.post(
            "/profil/name", data={"name": "n" * 121}
        ).status_code)
        self.assertEqual(200, self.client.post(
            "/profil/username", data={"username": "u" * 81}
        ).status_code)
        with self.connect() as connection:
            after = connection.execute(
                "SELECT name, username FROM users WHERE id=1"
            ).fetchone()
        self.assertEqual(tuple(before), tuple(after))

    def test_request_size_query_size_and_security_headers_are_enforced(self):
        self.assertEqual(1024 * 1024, webapp.app.config["MAX_CONTENT_LENGTH"])
        oversized = self.client.post(
            "/profil/name",
            data=b"x" * (1024 * 1024 + 1),
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(413, oversized.status_code)
        self.assertEqual(414, self.client.get("/?q=" + "x" * 8193).status_code)
        response = self.client.get("/")
        self.assertEqual("nosniff", response.headers["X-Content-Type-Options"])
        self.assertEqual("DENY", response.headers["X-Frame-Options"])
        self.assertEqual(
            "strict-origin-when-cross-origin", response.headers["Referrer-Policy"]
        )

    def test_runtime_connections_enforce_foreign_keys(self):
        connection = webapp.get_db()
        try:
            self.assertEqual(1, connection.execute("PRAGMA foreign_keys").fetchone()[0])
        finally:
            connection.close()

    def test_batch_market_projection_matches_full_s19_snapshots(self):
        with self.connect() as connection:
            service = InventoryReadService(connection)
            codes = tuple(str(value) for value in range(1, 251))
            others = (2, 3)
            projection = service.album_market_projection(1, others, "vfl", codes)
            mine = service.album(1, "vfl", codes)
            mine_missing = {
                code for code in codes
                if mine.availability_snapshot_for(code).missing
            }
            mine_available = {
                code for code in codes
                if mine.availability_snapshot_for(code).is_available
            }
            expected_market = set()
            for other_id in others:
                other = service.album(other_id, "vfl", codes)
                other_missing = {
                    code for code in codes
                    if other.availability_snapshot_for(code).missing
                }
                other_available = {
                    code for code in codes
                    if other.availability_snapshot_for(code).is_available
                }
                expected_get = mine_missing & other_available
                expected_give = (
                    mine_available & other_missing if expected_get else set()
                )
                expected_market.update(expected_get)
                self.assertEqual(expected_get, set(projection.get_codes_by_user[other_id]))
                self.assertEqual(expected_give, set(projection.give_codes_by_user[other_id]))
            self.assertEqual(expected_market, set(projection.market_codes))

    def test_no_request_values_are_printed_and_direct_runner_is_loopback_only(self):
        source = Path(webapp.__file__).read_text(encoding="utf-8")
        self.assertNotIn('print("TRIGGER ="', source)
        self.assertNotIn('print("FINAL URL:"', source)
        self.assertIn('app.run(debug=False, host="127.0.0.1"', source)
        self.assertNotIn('app.run(debug=True', source)
        self.assertIn("@serialized_sqlite_projection", inspect.getsource(webapp.trades_overview))


if __name__ == "__main__":
    unittest.main()
