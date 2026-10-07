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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb016-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.notification_history import NotificationHistoryService  # noqa: E402


class CB016LegacyCutoverTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb016-")
        self.db_path = Path(self.temp_dir.name) / "cutover.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
        webapp.DB = str(self.db_path)
        webapp.app.config.pop("FRIENDSHIP_CHECKER", None)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as login_session:
            login_session.clear()
            login_session["user_id"] = user_id

    def test_obsolete_operational_home_and_generic_notification_writer_are_removed(self):
        self.assertFalse((APP_DIR / "services" / "operational_home.py").exists())
        self.assertFalse((APP_DIR / "services" / "notifications.py").exists())
        source = (APP_DIR / "webapp.py").read_text(encoding="utf-8")
        self.assertNotIn("OperationalHomeService", source)
        self.assertNotIn("services.notifications", source)

    def test_each_migrated_projection_has_one_canonical_runtime_source(self):
        source = (APP_DIR / "webapp.py").read_text(encoding="utf-8")
        expected = (
            "FeedEventService", "CollectionProjectionService",
            "CollectorProfileService", "StatisticsProjectionService",
            "SuccessfulTradeProjectionService", "ExecutableTradeMatchService",
            "ProfilePrivacyService", "NotificationHistoryService",
        )
        for service_name in expected:
            self.assertIn(service_name, source)
        profile_source = (
            APP_DIR / "services" / "collector_profiles.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_legacy_current_albums", profile_source)
        self.assertNotIn("InventoryReadService", profile_source)

    def test_precanonical_trophy_schema_fails_closed_without_writes(self):
        old_db = Path(self.temp_dir.name) / "v7.db"
        shutil.copy2(FIXTURE, old_db)
        with self.connection(old_db) as connection:
            migrate(connection, 7)
            before = connection.execute(
                "SELECT COUNT(*) FROM unlocked_trophies"
            ).fetchone()[0]
        previous_db = webapp.DB
        webapp.DB = str(old_db)
        try:
            result = webapp.record_trophy_unlocks(
                "vfl", ["Legacy Visible"], user_id=1,
                silent_reached=["Legacy Silent"],
            )
            album_page = self.client.get("/album/vfl/trophaeen")
            cabinet = self.client.get("/trophaeen")
        finally:
            webapp.DB = previous_db
        with self.connection(old_db) as connection:
            after = connection.execute(
                "SELECT COUNT(*) FROM unlocked_trophies"
            ).fetchone()[0]
        self.assertEqual([], result)
        self.assertEqual(before, after)
        self.assertIn("Noch keine Auszeichnung", album_page.get_data(as_text=True))
        self.assertIn("Auszeichnungen: 0", cabinet.get_data(as_text=True))
        self.assertNotIn("Tauschgeschäfte", cabinet.get_data(as_text=True))

    def test_legacy_rows_are_retained_but_not_promoted_to_product_truth(self):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO unlocked_trophies "
                "(user_id, album_id, trophy_name) VALUES (1, 'vfl', 'Legacy Secret')"
            )
            connection.execute(
                "INSERT INTO notifications (user_id, title, body, is_read) "
                "VALUES (1, 'Legacy remains', 'Historical row', 0)"
            )
            connection.commit()
            before = tuple(connection.execute(
                "SELECT (SELECT COUNT(*) FROM unlocked_trophies), "
                "(SELECT COUNT(*) FROM notifications)"
            ).fetchone())
        trophy_html = self.client.get("/album/vfl/trophaeen").get_data(as_text=True)
        with self.connection() as connection:
            inbox = NotificationHistoryService(connection).page(1)
            after = tuple(connection.execute(
                "SELECT (SELECT COUNT(*) FROM unlocked_trophies), "
                "(SELECT COUNT(*) FROM notifications)"
            ).fetchone())
        self.assertEqual(before, after)
        self.assertNotIn("Legacy Secret", trophy_html)
        self.assertIn("Legacy remains", [item.title for item in inbox.items])

    def test_profile_uses_current_collection_without_reconstructing_history(self):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM historical_album_records WHERE user_id=1"
            )
            profile = CollectorProfileService(connection).by_user_id(1, 1)
        self.assertGreaterEqual(len(profile.current_albums), 1)
        self.assertEqual((), profile.historical_completions)

    def test_safe_legacy_deep_links_only_redirect_to_canonical_routes(self):
        expectations = {
            "/home": "/",
            "/zentrale": "/sammlung",
            "/sammlr-zentrale": "/sammlung",
        }
        for path, target in expectations.items():
            response = self.client.get(path, follow_redirects=False)
            self.assertEqual(302, response.status_code)
            self.assertEqual(target, response.headers["Location"])

    def test_cutover_adds_no_schema_migration(self):
        self.assertEqual(24, max(item.version for item in load_migrations()))


if __name__ == "__main__":
    unittest.main()
