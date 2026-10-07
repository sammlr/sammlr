import atexit
from dataclasses import FrozenInstanceError
from decimal import Decimal
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s28-bootstrap-")
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
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.trade_ratings import (  # noqa: E402
    TradeRatingCode,
    TradeRatingService,
)


class TradeRatingsTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s28-")
        self.test_db = Path(self.test_dir.name) / "ratings.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual(tuple(range(1, 9)), migrate(connection, 8))
            self._clear_domain(connection)
            connection.execute(
                "UPDATE users SET username='owner', name='Owner' WHERE id=1"
            )
            connection.execute(
                "UPDATE users SET username='partner', name='Partner' WHERE id=2"
            )
            connection.execute(
                "UPDATE users SET username='third', name='Third' WHERE id=3"
            )
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _clear_domain(connection):
        for table in (
            "trade_ratings",
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

    def create_trade(
        self,
        lifecycle_state="completed",
        legacy_status="completed",
        requester=1,
        partner=2,
    ):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes,
                     get_codes, status, from_confirmed, to_confirmed)
                VALUES ('vfl', ?, ?, '["1"]', '["2"]', ?, 1, 1)
                """,
                (requester, partner, legacy_status),
            )
            legacy_id = cursor.lastrowid
            lifecycle = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id,
                     partner_user_id, lifecycle_state, completed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    legacy_id,
                    requester,
                    partner,
                    lifecycle_state,
                    (
                        "2026-08-08 10:00:00"
                        if lifecycle_state == "completed" else None
                    ),
                ),
            )
            if lifecycle_state == "completed":
                connection.execute(
                    """
                    INSERT INTO trade_receipt_status
                        (trade_id, requester_received, requester_received_at,
                         partner_received, partner_received_at)
                    VALUES (?, 1, '2026-08-08 09:59:00',
                            1, '2026-08-08 10:00:00')
                    """,
                    (lifecycle.lastrowid,),
                )
            return legacy_id, lifecycle.lastrowid

    def rate(self, legacy_id, actor, stars):
        with self.connection() as connection:
            return TradeRatingService(connection).create(
                legacy_id, actor, stars
            )

    def test_v0008_migration_existing_completed_trade_repeat_down_and_fail_closed(self):
        migration_db = Path(self.test_dir.name) / "migration.db"
        shutil.copy2(REFERENCE_FIXTURE, migration_db)
        with self.connection(migration_db) as connection:
            self.assertEqual(tuple(range(1, 8)), migrate(connection, 7))
            request = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes,
                     get_codes, status)
                VALUES ('vfl', 1, 2, '[]', '[]', 'completed')
                """
            )
            lifecycle = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id,
                     partner_user_id, lifecycle_state, completed_at)
                VALUES (?, 1, 2, 'completed', CURRENT_TIMESTAMP)
                """,
                (request.lastrowid,),
            )
            self.assertEqual((8,), migrate(connection, 8))
            self.assertEqual(8, current_version(connection))
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(trade_ratings)"
                )
            }
            self.assertEqual(
                {"id", "trade_id", "rater_user_id", "rated_user_id", "stars", "created_at"},
                columns,
            )
            self.assertEqual((), migrate(connection, 8))
            self.assertEqual((8,), rollback(connection, 7))
            self.assertEqual((8,), migrate(connection, 8))
            connection.execute(
                """
                INSERT INTO trade_ratings
                    (trade_id, rater_user_id, rated_user_id, stars)
                VALUES (?, 1, 2, 5)
                """,
                (lifecycle.lastrowid,),
            )
            connection.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, 7)
            self.assertEqual(8, current_version(connection))
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM trade_ratings"
            ).fetchone()[0])
        self.assertEqual(25, load_migrations()[-1].version)

    def test_completed_is_rateable_open_and_legacy_without_lifecycle_are_not(self):
        completed, _ = self.create_trade()
        open_trade, _ = self.create_trade("accepted", "accepted")
        with self.connection() as connection:
            legacy = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes,
                     get_codes, status)
                VALUES ('vfl', 1, 2, '[]', '[]', 'completed')
                """
            ).lastrowid

        self.assertEqual(TradeRatingCode.CREATED, self.rate(completed, 1, 5).code)
        self.assertEqual(
            TradeRatingCode.NOT_QUALIFIED,
            self.rate(open_trade, 1, 5).code,
        )
        self.assertEqual(
            TradeRatingCode.NOT_QUALIFIED,
            self.rate(legacy, 1, 5).code,
        )

    def test_resolved_problem_does_not_change_completed_qualification(self):
        legacy_id, lifecycle_id = self.create_trade()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO trade_receipt_reports
                    (trade_id, receiver_user_id, receiver_side, state,
                     resolved_at)
                VALUES (?, 2, 'partner', 'resolved', CURRENT_TIMESTAMP)
                """,
                (lifecycle_id,),
            )
        self.assertEqual(
            TradeRatingCode.CREATED, self.rate(legacy_id, 1, 4).code
        )

    def test_one_final_rating_per_direction_independent_and_no_delete_route(self):
        legacy_id, _ = self.create_trade()
        first = self.rate(legacy_id, 1, 4)
        retry = self.rate(legacy_id, 1, 2)
        other_side = self.rate(legacy_id, 2, 5)
        foreign = self.rate(legacy_id, 3, 5)
        self.assertEqual(TradeRatingCode.CREATED, first.code)
        self.assertEqual(TradeRatingCode.ALREADY_RATED, retry.code)
        self.assertEqual(4, retry.stars)
        self.assertEqual(TradeRatingCode.CREATED, other_side.code)
        self.assertEqual(TradeRatingCode.UNAUTHORIZED, foreign.code)
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT rater_user_id, rated_user_id, stars
                FROM trade_ratings ORDER BY rater_user_id
                """
            ).fetchall()
        self.assertEqual(((1, 2, 4), (2, 1, 5)), tuple(map(tuple, rows)))
        self.assertEqual(
            405, self.client.delete(f"/trades/{legacy_id}/rating").status_code
        )
        with self.connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE trade_ratings SET stars=1 WHERE trade_id=?",
                    (first.trade_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM trade_ratings WHERE trade_id=?",
                    (first.trade_id,),
                )

    def test_star_bounds_and_database_constraints(self):
        legacy_id, lifecycle_id = self.create_trade()
        for value in (-1, 0, 6, 99, True, "5"):
            self.assertEqual(
                TradeRatingCode.INVALID_STARS,
                self.rate(legacy_id, 1, value).code,
            )
        with self.connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO trade_ratings
                        (trade_id, rater_user_id, rated_user_id, stars)
                    VALUES (?, 1, 2, 6)
                    """,
                    (lifecycle_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO trade_ratings
                        (trade_id, rater_user_id, rated_user_id, stars)
                    VALUES (?, 1, 1, 5)
                    """,
                    (lifecycle_id,),
                )

    def test_average_rounding_count_and_immediate_profile_aggregation(self):
        trades = (
            self.create_trade(requester=1, partner=2)[0],
            self.create_trade(requester=3, partner=2)[0],
            self.create_trade(requester=1, partner=2)[0],
        )
        self.assertEqual(TradeRatingCode.CREATED, self.rate(trades[0], 1, 4).code)
        self.assertEqual(TradeRatingCode.CREATED, self.rate(trades[1], 3, 5).code)
        self.assertEqual(TradeRatingCode.CREATED, self.rate(trades[2], 1, 5).code)
        with self.connection() as connection:
            summary = TradeRatingService(connection).summary_for_user(2)
            profile = CollectorProfileService(connection).by_user_id(2, 2)
        self.assertEqual(3, summary.rating_count)
        self.assertEqual(Decimal("4.7"), summary.average)
        self.assertEqual("4.7", summary.average_text)
        self.assertEqual((Decimal("4.7"), 3), (
            profile.rating_average, profile.rating_count
        ))
        self.assertEqual(3, profile.successful_trade_count)
        with self.assertRaises(FrozenInstanceError):
            summary.rating_count = 99

    def test_completed_deal_route_is_only_rating_ui_and_retry_creates_no_notification(self):
        completed, _ = self.create_trade()
        open_trade, _ = self.create_trade("accepted", "accepted")
        with self.connection() as connection:
            notifications_before = connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0]

        completed_html = self.client.get(
            f"/trades/{completed}"
        ).get_data(as_text=True)
        self.assertIn("Bewerte deinen Tauschpartner", completed_html)
        self.assertIn("Bewertung speichern", completed_html)
        self.assertNotIn("Bewerte deinen Tauschpartner", self.client.get(
            f"/trades/{open_trade}"
        ).get_data(as_text=True))
        self.assertIn(
            "Dieser Trade kann noch nicht bewertet werden.",
            self.client.get(f"/trades/{open_trade}").get_data(as_text=True),
        )
        self.assertNotIn("Bewertung speichern", self.client.get(
            "/profil/trade-archiv"
        ).get_data(as_text=True))

        response = self.client.post(
            f"/trades/{completed}/rating",
            data={"stars": "5"},
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn("Du hast diesen Trade bereits bewertet.", html)
        self.assertNotIn("Bewertung speichern", html)
        retry = self.client.post(
            f"/trades/{completed}/rating", data={"stars": "1"}
        )
        self.assertEqual(302, retry.status_code)
        with self.connection() as connection:
            self.assertEqual(5, connection.execute(
                "SELECT stars FROM trade_ratings"
            ).fetchone()[0])
            self.assertEqual(notifications_before, connection.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0])

        not_qualified = self.client.post(
            f"/trades/{open_trade}/rating",
            data={"stars": "5"},
            follow_redirects=True,
        )
        self.assertIn(
            "Dieser Trade kann noch nicht bewertet werden.",
            not_qualified.get_data(as_text=True),
        )
        self.assertEqual(400, self.client.post(
            f"/trades/{completed}/rating", data={"stars": "5.0"}
        ).status_code)

    def test_own_and_foreign_profiles_show_only_aggregate_and_empty_text(self):
        empty_own = self.client.get("/profil").get_data(as_text=True)
        self.assertIn("Noch keine Bewertung", empty_own)

        trades = (
            self.create_trade(requester=1, partner=2)[0],
            self.create_trade(requester=3, partner=2)[0],
        )
        self.rate(trades[0], 1, 4)
        self.rate(trades[1], 3, 5)

        self.login_as(2)
        own = self.client.get("/profil").get_data(as_text=True)
        self.login_as(1)
        foreign = self.client.get("/profil/partner").get_data(as_text=True)
        for html in (own, foreign):
            self.assertIn("★ 4,5", html)
            self.assertIn("2 Bewertungen", html)
            self.assertNotIn("rater_user_id", html)
            self.assertNotIn("rated_user_id", html)
            self.assertNotIn("trade_ratings", html)
            self.assertNotIn("Bewertung speichern", html)

    def test_schema_has_no_reason_storage_and_reads_do_not_mutate(self):
        legacy_id, _ = self.create_trade()
        self.rate(legacy_id, 1, 5)
        before = sha256(self.test_db)
        with self.connection() as connection:
            columns = {
                row[1] for row in connection.execute(
                    "PRAGMA table_info(trade_ratings)"
                )
            }
            TradeRatingService(connection).summary_for_user(2)
            CollectorProfileService(connection).by_user_id(2, 1)
        self.assertFalse(any("reason" in column for column in columns))
        self.assertEqual(before, sha256(self.test_db))


if __name__ == "__main__":
    unittest.main()
