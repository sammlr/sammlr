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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s26-bootstrap-")
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
)
from services.albums import all_codes  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402


class CollectorProfilesTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s26-")
        self.test_db = Path(self.test_dir.name) / "profiles.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5, 6), migrate(connection, 6))
            self.clear_profile_domain(connection)
            connection.execute(
                "UPDATE users SET username='owner', name='Owner Name' WHERE id=1"
            )
            connection.execute(
                """
                UPDATE users
                SET username='partner', name='Partner <script>alert(1)</script>'
                WHERE id=2
                """
            )
            connection.execute(
                "UPDATE users SET username='nameless', name='' WHERE id=3"
            )
            connection.executemany(
                "INSERT INTO user_albums (user_id, album_id) VALUES (?, ?)",
                ((1, "vfl"), (2, "vfl"), (2, "em24")),
            )
            connection.execute(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (2, 'vfl', '1', 'owned', 2, 3)
                """
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (2, 'em24', ?, 'owned', 0, 1)
                """,
                ((code,) for code in all_codes("em24")),
            )
            connection.executemany(
                """
                INSERT INTO unlocked_trophies
                    (user_id, album_id, trophy_name, unlocked_at)
                VALUES (2, ?, ?, '2026-08-08 10:00:00')
                """,
                (("vfl", "Trophy detail secret"), ("em24", "Second secret")),
            )
            self.legacy_trade_id = self.add_request(
                connection, "completed", 1, 2
            )
            lifecycle_request_id = self.add_request(
                connection, "completed", 2, 1
            )
            lifecycle = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id, partner_user_id,
                     lifecycle_state, completed_at)
                VALUES (?, 2, 1, 'completed', '2026-08-08 11:00:00')
                """,
                (lifecycle_request_id,),
            )
            connection.execute(
                """
                INSERT INTO trade_receipt_status
                    (trade_id, requester_received, requester_received_at,
                     partner_received, partner_received_at)
                VALUES (?, 1, '2026-08-08 10:59:00',
                        1, '2026-08-08 11:00:00')
                """,
                (lifecycle.lastrowid,),
            )
            connection.executemany(
                """
                INSERT INTO trade_positions
                    (trade_id, from_user_id, to_user_id, album_id,
                     sticker_code, quantity)
                VALUES (?, ?, ?, 'vfl', ?, 1)
                """,
                (
                    (lifecycle.lastrowid, 2, 1, "1"),
                    (lifecycle.lastrowid, 1, 2, "2"),
                ),
            )
            for status in (
                "open", "accepted", "failed", "declined", "rejected",
                "expired", "obsolete",
            ):
                self.add_request(connection, status, 2, 1)
            inconsistent_id = self.add_request(
                connection, "completed", 2, 1
            )
            connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id, partner_user_id,
                     lifecycle_state)
                VALUES (?, 2, 1, 'failed')
                """,
                (inconsistent_id,),
            )

        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def clear_profile_domain(connection):
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

    @staticmethod
    def add_request(connection, status, from_user, to_user):
        cursor = connection.execute(
            """
            INSERT INTO trade_requests
                (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
            VALUES ('vfl', ?, ?, '["1"]', '["2"]', ?)
            """,
            (from_user, to_user, status),
        )
        return cursor.lastrowid

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def profile_model(self, username="partner"):
        with self.connection() as connection:
            return CollectorProfileService(connection).by_username(username)

    def test_own_profile_remains_reachable_and_editable(self):
        response = self.client.get("/profil")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('aria-label="Sammlervitrine"', html)
        self.assertIn("@owner", html)
        self.assertIn('class="app-header-action app-header-settings" href="/account"', html)
        self.assertNotIn('class="app-header-action app-header-profile"', html)
        self.assertNotIn('class="collector-showcase-settings"', html)
        self.assertIn('href="/album/vfl"', html)
        for path in ("/profil/trade-archiv", "/statistik", "/trophaeen"):
            self.assertNotIn(f'href="{path}"', html)
        account_html = self.client.get("/account").get_data(as_text=True)
        for path in ("/profil/name", "/profil/username", "/profil/password"):
            self.assertIn(f'href="{path}"', account_html)
        for edit_path in ("/profil/name", "/profil/username", "/profil/password"):
            self.assertEqual(200, self.client.get(edit_path).status_code)

    def test_foreign_profile_by_username_is_readonly_and_conservative(self):
        response = self.client.get("/profil/partner")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn("@partner", html)
        self.assertNotIn("Partner &lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("Partner <script>", html)
        self.assertIn("VfL Osnabrück", html)
        self.assertIn("EURO 2024", html)
        for forbidden in (
            "/profil/name", "/profil/username", "/profil/password",
            "/statistik", "/trophaeen", "Trophy detail secret",
            "Second secret", "sticker_code", "Profil &amp; Konto",
        ):
            self.assertNotIn(forbidden, html)
        self.assertNotIn('href="/album/', html)
        self.assertEqual(1, html.count('method="POST"'))
        self.assertIn('method="POST" action="/notifications"', html)
        self.assertNotIn("Sticker erstellen", html)
        self.assertNotIn("Sticker bearbeiten", html)
        self.assertNotIn('class="collector-showcase-settings"', html)
        self.assertNotIn('class="app-header-action app-header-settings"', html)
        self.assertIn('class="app-header-action app-header-profile"', html)

    def test_profile_v1_album_cards_are_reduced_and_keep_dom_order(self):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO user_albums (user_id, album_id) VALUES (2, 'wm26')"
            )
        html = self.client.get("/profil/partner").get_data(as_text=True)
        ordered_names = ("EURO 2024", "FIFA World Cup 2026", "VfL Osnabrück")
        positions = [html.index(name) for name in ordered_names]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(3, html.count("data-profile-album-order="))
        for expected in ("EURO", "🌍", "VFL", "707 / 707", "100&nbsp;%"):
            self.assertIn(expected, html)
        for forbidden in (
            "Doppelte", "fehlende verfügbar", "fehlenden erhältlich",
            "Album hinzufügen", "Favoritenalbum",
        ):
            self.assertNotIn(forbidden, html)

    def test_profile_v1_css_has_hard_mobile_two_column_grid(self):
        css = (APP_DIR / "static" / "profile_v1.css").read_text()
        self.assertIn(
            "grid-template-columns:repeat(2,minmax(0,1fr))", css
        )
        self.assertNotIn("overflow-x:auto", css)

    def test_unknown_username_is_404_and_missing_optional_name_works(self):
        self.assertEqual(404, self.client.get("/profil/does-not-exist").status_code)
        response = self.client.get("/profil/nameless")
        self.assertEqual(200, response.status_code)
        self.assertIn("@nameless", response.get_data(as_text=True))

    def test_legacy_fixture_keeps_current_albums_without_public_progress(self):
        profile = self.profile_model()
        self.assertEqual(("em24", "vfl"), tuple(
            a.album_id for a in profile.current_albums
        ))
        self.assertEqual((), profile.showcase_albums)

    def test_cb014_metrics_remove_duplicates_and_legacy_trophies(self):
        profile = self.profile_model()
        self.assertEqual(2, profile.album_count)
        self.assertEqual(0, profile.duplicate_count)
        self.assertEqual(2, profile.successful_trade_count)
        self.assertEqual(0, profile.trophy_count)
        html = self.client.get("/profil/partner").get_data(as_text=True)
        self.assertIn("2 Tausche", html)
        for label in ("Sammler-Kennzahlen", "Gültige Trophäen"):
            self.assertNotIn(label, html)
        self.assertNotIn("Doppelte", html)

    def test_lifecycle_and_legacy_completed_count_once_other_states_do_not(self):
        self.assertEqual(2, self.profile_model().successful_trade_count)
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT request.id, request.status, lifecycle.lifecycle_state
                FROM trade_requests request
                LEFT JOIN trades lifecycle
                  ON lifecycle.legacy_trade_request_id=request.id
                WHERE request.from_user_id=2 OR request.to_user_id=2
                ORDER BY request.id
                """
            ).fetchall()
        self.assertGreaterEqual(len(rows), 10)

    def test_profile_statistics_and_archive_share_canonical_trade_count(self):
        profile_html = self.client.get("/profil").get_data(as_text=True)
        statistics_html = self.client.get("/statistik").get_data(as_text=True)
        archive_html = self.client.get(
            "/profil/trade-archiv"
        ).get_data(as_text=True)
        self.assertIn("2 Tausche", profile_html)
        self.assertIn("2 Tausche abgeschlossen", statistics_html)
        self.assertIn("2 Trades", archive_html)
        self.assertIn("Zeitpunkt nicht verfügbar", archive_html)

    def test_foreign_profile_has_required_mobile_content_order(self):
        html = self.client.get("/profil/partner").get_data(as_text=True)
        positions = [
            html.index('aria-label="Sammlerprofil"'),
            html.index('id="active-albums-title"'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Abgeschlossene Alben", html)
        for removed in (
            "Dein Sammlr-Ausweis.", "Sammler-Kennzahlen", "Meine Alben",
            "Meine Statistik", "Meine Trophäen", "Trade-Archiv", "Freunde",
            "Account &amp; Einstellungen", "Noch keine abgeschlossenen Alben.",
            "Noch keine gültigen Trophäen freigeschaltet.",
        ):
            self.assertNotIn(removed, html)

    def test_partner_name_in_trade_detail_links_to_username_profile(self):
        response = self.client.get(f"/trades/{self.legacy_trade_id}")
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn(
            '<a class="trade-partner-profile-link" href="/profil/partner">partner</a>',
            html,
        )

    def test_foreign_profile_get_has_no_database_mutation(self):
        before_hash = sha256(self.test_db)
        with self.connection() as connection:
            before_changes = connection.total_changes
        response = self.client.get("/profil/partner")
        self.assertEqual(200, response.status_code)
        self.assertEqual(before_hash, sha256(self.test_db))
        with self.connection() as connection:
            self.assertEqual(before_changes, connection.total_changes)

    def test_dtos_are_immutable(self):
        profile = self.profile_model()
        with self.assertRaises(FrozenInstanceError):
            profile.trophy_count = 99
        with self.assertRaises(FrozenInstanceError):
            profile.active_albums[0].name = "Changed"

    def test_s26_adds_no_migration(self):
        # S26 remains on V0006; later S27/S28 added V0007/V0008.
        self.assertEqual(26, load_migrations()[-1].version)
        with self.connection() as connection:
            self.assertEqual(6, current_version(connection))


if __name__ == "__main__":
    unittest.main()
