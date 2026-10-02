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
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s17-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import (  # noqa: E402
    current_version,
    migrate,
    rollback,
)
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_problems import (  # noqa: E402
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
    TradeProblemType,
    problem_reports_for_trade,
)


class TradeProblemsPartialReceiptTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.fixture_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.production_hash_before == sha256(PRODUCTION_DB)
        assert cls.fixture_hash_before == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s17-")
        self.test_db = Path(self.test_dir.name) / "problems.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual(
                (1, 2, 3, 4, 5), migrate(connection, target_version=5)
            )
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(2)

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def row(self, statement, parameters=()):
        with self.connection() as connection:
            return connection.execute(statement, parameters).fetchone()

    def count(self, table, where="1=1", parameters=()):
        return self.row(
            f"SELECT COUNT(*) AS count FROM {table} WHERE {where}", parameters
        )["count"]

    def create_accepted_trade(self, give_count=30, get_count=1):
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE stickers SET quantity=?, duplicates=?
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'
                """,
                (give_count + 1, give_count),
            )
            connection.execute(
                """
                UPDATE stickers SET quantity=?, duplicates=?
                WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'
                """,
                (get_count + 1, get_count),
            )
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, ?, ?, 'open')
                """,
                (
                    json.dumps(["1"] * give_count),
                    json.dumps(["3"] * get_count),
                ),
            )
            trade_id = cursor.lastrowid
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        return trade_id

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/ship")

    def receive_as(self, trade_id, user_id):
        self.login_as(user_id)
        return self.client.post(f"/trade/{trade_id}/receive")

    def incoming_position(self, trade_id, user_id):
        return self.row(
            """
            SELECT p.* FROM trade_positions p
            JOIN trades t ON t.id=p.trade_id
            WHERE t.legacy_trade_request_id=? AND p.to_user_id=?
            """,
            (trade_id, user_id),
        )

    def problem_input(self, trade_id, user_id, quantity, problem_type):
        position = self.incoming_position(trade_id, user_id)
        return (
            PartialReceiptInputDTO(position["id"], quantity, problem_type),
        )

    def report_as(self, trade_id, user_id, quantity, problem_type):
        with self.connection() as connection:
            return TradeProblemService(connection).report(
                trade_id,
                user_id,
                self.problem_input(trade_id, user_id, quantity, problem_type),
            )

    def resolve_as(self, trade_id, user_id):
        with self.connection() as connection:
            return TradeProblemService(connection).resolve(trade_id, user_id)

    def inventory(self, user_id, code):
        row = self.row(
            """
            SELECT quantity, duplicates FROM stickers
            WHERE user_id=? AND album_id='vfl' AND sticker_code=?
            """,
            (user_id, code),
        )
        return tuple(row) if row else (0, 0)

    def availability(self, user_id, code):
        with self.connection() as connection:
            return InventoryReadService(connection).album(
                user_id, "vfl"
            ).availability(code)

    def reports(self, trade_id):
        with self.connection() as connection:
            return problem_reports_for_trade(connection, trade_id)

    def lifecycle(self, trade_id):
        return self.row(
            "SELECT lifecycle_state FROM trades WHERE legacy_trade_request_id=?",
            (trade_id,),
        )["lifecycle_state"]

    def legacy_status(self, trade_id):
        return self.row(
            "SELECT status FROM trade_requests WHERE id=?", (trade_id,)
        )["status"]

    def test_normal_s16_full_receipt_remains_direct_and_unchanged(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.login_as(2)
        detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Empfang bestätigen", detail)
        self.assertIn("Alles vollständig erhalten", detail)
        self.assertIn("Problem melden / Lieferung unvollständig", detail)

        self.receive_as(trade_id, 2)

        self.assertEqual((30, 0), self.inventory(2, "1"))
        self.assertEqual(29, self.availability(2, "1").available)
        self.assertEqual((), self.reports(trade_id))

    def test_29_of_30_books_29_and_keeps_one_open(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)

        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        self.assertEqual((29, 0), self.inventory(2, "1"))
        self.assertEqual(28, self.availability(2, "1").available)
        self.assertEqual(1, result.open_quantity)
        self.assertEqual("accepted", self.legacy_status(trade_id))
        self.assertEqual("problem_open", self.lifecycle(trade_id))

    def test_partial_receipt_resolves_only_received_transit_share(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.assertEqual(30, self.availability(2, "1").incoming_transit)

        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)

        self.assertEqual(1, self.availability(2, "1").incoming_transit)

    def test_missing_remainder_is_persisted_with_expected_truth(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        report = self.reports(trade_id)[0]
        position = report.positions[0]

        self.assertEqual((30, 29, 0, 1), (
            position.expected_quantity,
            position.initial_received_quantity,
            position.resolution_received_quantity,
            position.open_quantity,
        ))
        self.assertEqual("missing", position.problem_type)
        self.assertEqual("open", report.state)

    def test_fully_lost_shipment_allows_zero_correct_quantity(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.report_as(
            trade_id, 2, 0, TradeProblemType.SHIPMENT_LOST
        )

        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertTrue(self.reports(trade_id)[0].shipment_lost)
        self.assertEqual(30, result.open_quantity)

    def test_quantity_above_expected_is_rejected(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.report_as(trade_id, 2, 31, TradeProblemType.MISSING)

        self.assertEqual(TradeProblemCode.INVALID_QUANTITY, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertEqual((), self.reports(trade_id))

    def test_negative_and_noninteger_quantities_are_rejected(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        for invalid in (-1, "29", True):
            with self.subTest(invalid=invalid):
                result = self.report_as(
                    trade_id, 2, invalid, TradeProblemType.MISSING
                )
                self.assertEqual(TradeProblemCode.INVALID_QUANTITY, result.code)
                self.assertEqual((), self.reports(trade_id))

    def test_wrong_sticker_does_not_book_expected_position(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.report_as(
            trade_id, 2, 0, TradeProblemType.WRONG_STICKER
        )

        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertEqual("wrong_sticker", self.reports(trade_id)[0].positions[0].problem_type)

    def test_damaged_sticker_is_not_automatically_booked(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.report_as(trade_id, 2, 0, TradeProblemType.DAMAGED)

        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertEqual("damaged", self.reports(trade_id)[0].positions[0].problem_type)

    def test_lost_shipment_never_completes_trade(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        self.report_as(trade_id, 2, 0, TradeProblemType.SHIPMENT_LOST)

        self.assertEqual("accepted", self.legacy_status(trade_id))
        self.assertEqual("problem_open", self.lifecycle(trade_id))

    def test_problem_is_visible_in_deal_view_and_history(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        self.login_as(1)
        detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)

        self.assertIn("Problemhistorie", detail)
        self.assertIn("Problem offen", detail)
        self.assertIn("erwartet 30", detail)
        self.assertIn("bei erster Meldung erhalten 29", detail)
        self.assertIn("später nachgeliefert 0", detail)
        self.assertIn("offen 1", detail)
        self.assertIn("keine Schuldfrage", detail)

    def test_later_arrival_resolves_problem_and_keeps_history(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        result = self.resolve_as(trade_id, 2)
        report = self.reports(trade_id)[0]

        self.assertEqual(
            TradeProblemCode.PROBLEM_RESOLVED,
            result.code,
            result.explanation,
        )
        self.assertEqual("resolved", report.state)
        self.assertTrue(report.resolved_at)
        self.assertEqual("resolved", report.positions[0].state)
        self.assertEqual(29, report.positions[0].initial_received_quantity)

    def test_resolution_books_only_open_remainder(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        before = self.inventory(2, "1")
        first = self.resolve_as(trade_id, 2)
        after = self.inventory(2, "1")
        second = self.resolve_as(trade_id, 2)

        self.assertEqual(1, first.booked_quantity)
        self.assertEqual((before[0] + 1, 29), after)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, second.code)
        self.assertEqual(after, self.inventory(2, "1"))
        self.assertEqual(0, self.availability(2, "1").incoming_transit)

    def test_trade_completes_only_after_both_sides_and_problem_resolution(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        self.assertEqual("accepted", self.legacy_status(trade_id))

        result = self.resolve_as(trade_id, 2)

        self.assertTrue(result.completed)
        self.assertEqual("completed", self.legacy_status(trade_id))
        self.assertEqual("completed", self.lifecycle(trade_id))

    def test_identical_report_retry_is_idempotent(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        first = self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        inventory_after = self.inventory(2, "1")
        report_before = self.reports(trade_id)[0]
        second = self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        report_after = self.reports(trade_id)[0]

        self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, first.code)
        self.assertEqual(TradeProblemCode.ALREADY_IDENTICAL, second.code)
        self.assertEqual(inventory_after, self.inventory(2, "1"))
        self.assertEqual(1, self.count("trade_receipt_reports"))
        self.assertEqual(report_before.created_at, report_after.created_at)

    def test_conflicting_retry_is_rejected_without_overwrite(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        before = self.reports(trade_id)[0]
        result = self.report_as(trade_id, 2, 28, TradeProblemType.DAMAGED)
        after = self.reports(trade_id)[0]

        self.assertEqual(TradeProblemCode.CONFLICTING_REPORT, result.code)
        self.assertEqual(before, after)
        self.assertEqual((29, 0), self.inventory(2, "1"))

    def test_unrelated_user_cannot_report_partial_receipt(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        position = self.incoming_position(trade_id, 2)
        with self.connection() as connection:
            result = TradeProblemService(connection).report(
                trade_id,
                3,
                (PartialReceiptInputDTO(position["id"], 29, "missing"),),
            )

        self.assertEqual(TradeProblemCode.UNAUTHORIZED, result.code)
        self.assertEqual((), self.reports(trade_id))

    def test_sender_cannot_submit_receiver_position_for_them(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        partner_position = self.incoming_position(trade_id, 2)
        with self.connection() as connection:
            result = TradeProblemService(connection).report(
                trade_id,
                1,
                (PartialReceiptInputDTO(partner_position["id"], 29, "missing"),),
            )

        self.assertEqual(TradeProblemCode.INVALID_QUANTITY, result.code)
        self.assertEqual((), self.reports(trade_id))

    def test_unshipped_positions_cannot_be_received(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 2)
        result = self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)

        self.assertEqual(TradeProblemCode.NOT_SHIPPED, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertEqual((), self.reports(trade_id))

    def test_technical_error_rolls_back_inventory_and_problem_together(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        inputs = self.problem_input(trade_id, 2, 29, TradeProblemType.MISSING)
        with patch(
            "services.trade_problems.InventoryWriteService.add",
            side_effect=RuntimeError("injected"),
        ):
            with self.connection() as connection:
                result = TradeProblemService(connection).report(
                    trade_id, 2, inputs
                )

        self.assertEqual(TradeProblemCode.TRANSACTION_ERROR, result.code)
        self.assertEqual((0, 0), self.inventory(2, "1"))
        self.assertEqual((), self.reports(trade_id))
        self.assertEqual("partially_shipped", self.lifecycle(trade_id))

    def test_v5_legacy_trophy_writer_stays_off_without_notification(self):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code<>'1'"
            )
            for code in range(4, 85):
                connection.execute(
                    """
                    INSERT INTO stickers
                        (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (1, 'vfl', ?, 'owned', 0, 1)
                    """,
                    (str(code),),
                )
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.ship_as(trade_id, 2)
        self.receive_as(trade_id, 2)
        position = self.incoming_position(trade_id, 1)
        self.login_as(1)
        self.client.post(
            f"/trade/{trade_id}/problem",
            data={
                f"received_{position['id']}": "0",
                f"problem_{position['id']}": "missing",
            },
        )
        notifications_before = self.count("notifications")

        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        notifications_after = self.count("notifications")
        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )

        self.assertEqual(notifications_before, notifications_after)
        self.assertEqual(notifications_after, self.count("notifications"))
        self.assertEqual(
            0,
            self.count(
                "unlocked_trophies",
                "user_id=1 AND album_id='vfl' AND trophy_name='Kader & Staff'",
            ),
        )

    def test_stable_result_codes_and_problem_types_are_exact(self):
        self.assertEqual(
            {
                "FULLY_RECEIVED", "PARTIAL_RECEIPT_RECORDED",
                "ALREADY_IDENTICAL", "PROBLEM_RESOLVED",
                "CLOSED_WITH_PROBLEM", "PROBLEM_RESOLVED_AFTER_CLOSE",
                "INVALID_QUANTITY", "CONFLICTING_REPORT", "NOT_SHIPPED",
                "INVALID_TRADE_STATE", "UNAUTHORIZED", "TRANSACTION_ERROR",
            },
            {code.value for code in TradeProblemCode},
        )
        self.assertEqual(
            {"missing", "wrong_sticker", "damaged", "shipment_lost"},
            {problem.value for problem in TradeProblemType},
        )

    def test_problem_form_is_simple_bounded_and_has_no_support_fields(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.login_as(2)
        html = self.client.get(f"/trades/{trade_id}/problem").get_data(as_text=True)

        self.assertIn("Erwartet: 30", html)
        self.assertIn('min="0" max="30"', html)
        self.assertIn("Falscher Sticker", html)
        self.assertIn("Beschädigt", html)
        self.assertIn("Gesamte Sendung verloren", html)
        self.assertIn("keine Schuldfrage", html)
        self.assertNotIn("Versicherung", html)
        self.assertNotIn("Bewertung", html)
        self.assertNotIn("Chat", html)

    def test_v0005_migrates_empty_and_fixture_copy_and_repeats_as_noop(self):
        empty_path = Path(self.test_dir.name) / "empty.db"
        with self.connection(empty_path) as connection:
            self.assertEqual(
                (1, 2, 3, 4, 5), migrate(connection, target_version=5)
            )
            self.assertEqual((), migrate(connection, target_version=5))
            self.assertEqual(5, current_version(connection))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertIn("trade_receipt_reports", tables)
        self.assertIn("trade_receipt_report_positions", tables)

    def test_v0005_empty_backout_and_fail_closed_used_backout(self):
        empty_path = Path(self.test_dir.name) / "backout.db"
        with self.connection(empty_path) as connection:
            migrate(connection, target_version=5)
            self.assertEqual((5,), rollback(connection, target_version=4))
            self.assertEqual(4, current_version(connection))

        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_as(trade_id, 2, 29, TradeProblemType.MISSING)
        with self.connection() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                rollback(connection, target_version=4)
            self.assertEqual(5, current_version(connection))

    def test_legacy_completed_trade_remains_unchanged_and_readable(self):
        trade = self.row("SELECT * FROM trade_requests WHERE id=1")
        self.assertEqual("completed", trade["status"])
        self.assertEqual('["2"]', trade["give_codes"])
        self.assertEqual('["4"]', trade["get_codes"])
        self.assertEqual(1, trade["from_confirmed"])
        self.assertEqual(1, trade["to_confirmed"])
        self.assertEqual((), self.reports(1))

    def test_canonical_databases_remain_unchanged(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.fixture_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
