import atexit
import hashlib
import json
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
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s18-2-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_problems import (  # noqa: E402
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
    TradeProblemType,
    problem_reports_for_trade,
)
from services.trade_ratings import TradeRatingCode, TradeRatingService  # noqa: E402


class ProblemTradeFinalizationTestCase(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-s18-2-")
        self.database = Path(self.temp_dir.name) / "test.db"
        shutil.copy2(REFERENCE_FIXTURE, self.database)
        with self.connection() as connection:
            migrate(connection, target_version=8)
            self.assertEqual(8, current_version(connection))
        webapp.DB = str(self.database)
        self.client = webapp.app.test_client()

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def create_problem_trade(self, problem_type="missing", received=2, expected=3):
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE stickers SET quantity=?, duplicates=?
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'
                """,
                (expected + 1, expected),
            )
            connection.execute(
                """
                UPDATE stickers SET quantity=2, duplicates=1
                WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'
                """
            )
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, ?, '["3"]', 'open')
                """,
                (json.dumps(["1"] * expected),),
            )
            request_id = cursor.lastrowid
        self.login(2)
        self.client.post(f"/trade/{request_id}/accept")
        self.login(1)
        self.client.post(f"/trade/{request_id}/ship")
        with self.connection() as connection:
            position = connection.execute(
                """
                SELECT p.* FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=2
                """,
                (request_id,),
            ).fetchone()
            result = TradeProblemService(connection).report(
                request_id,
                2,
                (
                    PartialReceiptInputDTO(
                        position["id"], received, problem_type
                    ),
                ),
            )
        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        return request_id

    def close(self, request_id, user_id=2):
        with self.connection() as connection:
            return TradeProblemService(connection).close_with_problem(
                request_id, user_id
            )

    def resolve(self, request_id, user_id=2):
        with self.connection() as connection:
            return TradeProblemService(connection).resolve(request_id, user_id)

    def lifecycle(self, request_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT r.status, t.id AS lifecycle_trade_id,
                       t.lifecycle_state, t.completed_at
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                WHERE r.id=?
                """,
                (request_id,),
            ).fetchone()

    def inventory(self):
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT quantity, duplicates FROM stickers
                WHERE user_id=2 AND album_id='vfl' AND sticker_code='1'
                """
            ).fetchone()
        return tuple(row) if row else (0, 0)

    def transit(self):
        with self.connection() as connection:
            return InventoryReadService(connection).snapshot(
                2, "vfl", ("1",)
            ).sticker("1").incoming_transit

    def counts(self):
        with self.connection() as connection:
            return {
                "events": connection.execute(
                    "SELECT COUNT(*) FROM trade_events"
                ).fetchone()[0],
                "notifications": connection.execute(
                    "SELECT COUNT(*) FROM notifications"
                ).fetchone()[0],
                "trophies": connection.execute(
                    "SELECT COUNT(*) FROM unlocked_trophies"
                ).fetchone()[0],
            }

    def test_all_problem_types_close_without_booking_and_end_transit(self):
        cases = (
            (TradeProblemType.MISSING, 2, 3),
            (TradeProblemType.WRONG_STICKER, 0, 1),
            (TradeProblemType.DAMAGED, 0, 1),
            (TradeProblemType.SHIPMENT_LOST, 0, 1),
        )
        for problem_type, received, expected in cases:
            with self.subTest(problem_type=problem_type.value):
                request_id = self.create_problem_trade(
                    problem_type, received, expected
                )
                inventory_before = self.inventory()
                self.assertEqual(expected - received, self.transit())

                result = self.close(request_id)

                self.assertEqual(TradeProblemCode.CLOSED_WITH_PROBLEM, result.code)
                self.assertEqual(inventory_before, self.inventory())
                self.assertEqual(0, self.transit())
                state = self.lifecycle(request_id)
                self.assertEqual("completed", state["status"])
                self.assertEqual("closed_with_problem", state["lifecycle_state"])
                self.assertTrue(state["completed_at"])
                report = self.reports(request_id)[0]
                self.assertEqual("open", report.state)
                self.assertEqual(expected - received, report.open_quantity)
                self.assertTrue(report.closed_at)
                self.assertEqual(2, report.closed_by_user_id)

    def reports(self, request_id):
        with self.connection() as connection:
            return problem_reports_for_trade(connection, request_id)

    def test_close_and_late_resolution_are_idempotent_and_append_only(self):
        request_id = self.create_problem_trade(received=2, expected=3)
        initial_inventory = self.inventory()
        before = self.counts()
        first_close = self.close(request_id)
        after_close = self.counts()
        second_close = self.close(request_id)

        self.assertEqual(TradeProblemCode.CLOSED_WITH_PROBLEM, first_close.code)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, second_close.code)
        self.assertEqual(after_close, self.counts())
        self.assertEqual(initial_inventory, self.inventory())

        with self.connection() as connection:
            rating = TradeRatingService(connection).create(request_id, 2, 3)
        self.assertEqual(TradeRatingCode.CREATED, rating.code)

        resolved = self.resolve(request_id)
        after_resolve = self.counts()
        retry = self.resolve(request_id)

        self.assertEqual(
            TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE, resolved.code
        )
        self.assertEqual(1, resolved.booked_quantity)
        inventory_after = self.inventory()
        self.assertEqual(initial_inventory[0] + 1, inventory_after[0])
        self.assertEqual(inventory_after[0] - 1, inventory_after[1])
        self.assertEqual("problem_resolved_after_close", self.lifecycle(request_id)["lifecycle_state"])
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, retry.code)
        self.assertEqual(after_resolve, self.counts())
        self.assertEqual(0, self.transit())
        self.assertEqual(before["notifications"] + 2, after_resolve["notifications"])
        with self.connection() as connection:
            notification_types = tuple(
                row[0] for row in connection.execute(
                    "SELECT notification_type FROM notifications ORDER BY id DESC LIMIT 2"
                )
            )
        self.assertEqual(
            ("trade_rating_available", "trade_problem_terminal"),
            notification_types,
        )
        self.assertEqual(before["trophies"], after_resolve["trophies"])
        self.assertGreater(after_resolve["events"], before["events"])
        with self.connection() as connection:
            stored_rating = connection.execute(
                "SELECT stars FROM trade_ratings"
            ).fetchone()[0]
            event_types = tuple(
                row[0] for row in connection.execute(
                    """
                    SELECT event_type FROM trade_events
                    WHERE trade_id=? ORDER BY id
                    """,
                    (self.lifecycle(request_id)["lifecycle_trade_id"],),
                )
            )
        self.assertEqual(3, stored_rating)
        self.assertIn("problem_reported", event_types)
        self.assertIn("problem_trade_closed", event_types)
        self.assertIn("problem_resolved_after_close", event_types)
        self.login(2)
        timeline_html = self.client.get(
            f"/trades/{request_id}"
        ).get_data(as_text=True)
        self.assertIn("3 Sterne vergeben", timeline_html)

    def test_only_problem_receiver_can_close_and_later_resolve(self):
        request_id = self.create_problem_trade()
        before = self.inventory()
        self.assertEqual(TradeProblemCode.UNAUTHORIZED, self.close(request_id, 1).code)
        self.assertEqual(TradeProblemCode.UNAUTHORIZED, self.close(request_id, 3).code)
        self.assertEqual("problem_open", self.lifecycle(request_id)["lifecycle_state"])
        self.assertEqual(before, self.inventory())

        self.close(request_id, 2)
        self.assertNotEqual(
            TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE,
            self.resolve(request_id, 1).code,
        )
        self.assertEqual(before, self.inventory())

    def test_closed_trade_is_read_only_except_explicit_late_resolution(self):
        request_id = self.create_problem_trade()
        self.close(request_id)
        before = (self.inventory(), self.counts())
        self.login(1)
        self.client.post(f"/trade/{request_id}/ship")
        self.client.post(f"/trade/{request_id}/receive")
        self.client.post(f"/trade/{request_id}/confirm")
        self.client.post(f"/trade/{request_id}/fail")
        self.assertEqual(before, (self.inventory(), self.counts()))
        self.assertEqual("closed_with_problem", self.lifecycle(request_id)["lifecycle_state"])
        global_board = self.client.get(
            "/trades?tab=agreements"
        ).get_data(as_text=True)
        album_board = self.client.get(
            "/album/vfl/trades?tab=agreements"
        ).get_data(as_text=True)
        home = self.client.get("/").get_data(as_text=True)
        self.assertNotIn(
            f'href="/trades/{request_id}?origin=trades"', global_board
        )
        self.assertNotIn(
            f'href="/trades/{request_id}?origin=album_trades', album_board
        )
        self.assertNotIn(
            f'href="/trades/{request_id}?origin=home"', home
        )

    def test_ui_permissions_safety_copy_history_and_final_state(self):
        request_id = self.create_problem_trade()
        self.login(2)
        open_html = self.client.get(f"/trades/{request_id}").get_data(as_text=True)
        self.assertIn("Trade mit Problem beenden", open_html)
        self.assertIn("Nicht erhaltene Sticker werden nicht deiner Sammlung hinzugefügt.", open_html)
        self.assertIn("Abbrechen", open_html)

        self.login(1)
        other_html = self.client.get(f"/trades/{request_id}").get_data(as_text=True)
        self.assertNotIn("closeProblemTradeDialog", other_html)

        self.login(2)
        self.client.post(f"/trade/{request_id}/problem/close")
        closed_html = self.client.get(f"/trades/{request_id}").get_data(as_text=True)
        self.assertIn("Trade mit Problem beendet", closed_html)
        self.assertIn("Mindestens ein dokumentiertes Lieferproblem blieb offen.", closed_html)
        self.assertIn("Problem nachträglich gelöst", closed_html)
        self.assertIn("Bewerte deinen Tauschpartner", closed_html)

        self.client.post(
            f"/trade/{request_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        final_html = self.client.get(f"/trades/{request_id}").get_data(as_text=True)
        self.assertIn("Problem nachträglich gelöst", final_html)
        self.assertIn("Problemhistorie", final_html)
        self.assertIn("nur noch lesbar", final_html)
        self.assertNotIn("closeProblemTradeDialog", final_html)

    def test_ratings_allowed_but_successful_trade_metric_stays_unchanged(self):
        request_id = self.create_problem_trade()
        with self.connection() as connection:
            successful_before = CollectorProfileService(connection).by_user_id(
                1, 1
            ).successful_trade_count
        self.close(request_id)
        with self.connection() as connection:
            service = TradeRatingService(connection)
            self.assertEqual(
                TradeRatingCode.CREATED,
                service.create(request_id, 2, 4).code,
            )
            self.assertEqual(
                TradeRatingCode.ALREADY_RATED,
                service.create(request_id, 2, 1).code,
            )
            profile = CollectorProfileService(connection).by_user_id(1, 1)
        self.assertEqual(successful_before, profile.successful_trade_count)
        self.resolve(request_id)
        with self.connection() as connection:
            self.assertEqual(
                TradeRatingCode.ALREADY_RATED,
                TradeRatingService(connection).create(request_id, 2, 5).code,
            )
            profile = CollectorProfileService(connection).by_user_id(1, 1)
        self.assertEqual(successful_before, profile.successful_trade_count)

    def test_no_new_migration_and_final_state_cannot_reopen(self):
        migrations = sorted(
            path.name for path in (APP_DIR / "Database" / "migrations").glob("*.up.sql")
        )
        self.assertIn("0008_trade_ratings.up.sql", migrations)
        self.assertFalse(any("problem_trade_finalization" in name for name in migrations))
        request_id = self.create_problem_trade()
        self.close(request_id)
        self.resolve(request_id)
        report_before = self.reports(request_id)[0]
        result = self.close(request_id)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, result.code)
        self.assertEqual(report_before, self.reports(request_id)[0])
        self.assertEqual("problem_resolved_after_close", self.lifecycle(request_id)["lifecycle_state"])


if __name__ == "__main__":
    unittest.main()
