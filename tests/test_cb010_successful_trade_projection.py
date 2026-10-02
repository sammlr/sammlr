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
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

from App.Database.migration_runner import migrate  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.successful_trade_projection import (  # noqa: E402
    SuccessfulTradeProjectionService,
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SuccessfulTradeProjectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb010-")
        self.db_path = Path(self.temp_dir.name) / "projection.db"
        shutil.copy2(REFERENCE_FIXTURE, self.db_path)
        with self.connect() as connection:
            migrate(connection, 16)
            for table in (
                "trade_ratings", "trade_receipt_report_positions",
                "trade_receipt_reports", "trade_receipt_status",
                "trade_shipping_status", "trade_reservations", "trade_events",
                "trade_positions", "trades", "trade_requests",
            ):
                connection.execute(f"DELETE FROM {table}")

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def legacy(
        self, connection, *, status="completed", requester=1, partner=2,
        album="vfl", give=("1",), receive=("2",), raw_give=None,
    ):
        give_json = raw_give if raw_give is not None else json.dumps(give)
        cursor = connection.execute(
            """
            INSERT INTO trade_requests
                (album_id, from_user_id, to_user_id, give_codes, get_codes,
                 status, from_confirmed, to_confirmed)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1)
            """,
            (album, requester, partner, give_json, json.dumps(receive), status),
        )
        return cursor.lastrowid

    def lifecycle(
        self, connection, *, state="completed", request_status="completed",
        requester=1, partner=2, completed_at="2026-08-18 12:00:00",
        receipt=(1, 1), positions=None,
    ):
        request_id = self.legacy(
            connection, status=request_status, requester=requester,
            partner=partner,
        )
        cursor = connection.execute(
            """
            INSERT INTO trades
                (legacy_trade_request_id, requester_user_id, partner_user_id,
                 lifecycle_state, completed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (request_id, requester, partner, state, completed_at),
        )
        trade_id = cursor.lastrowid
        requester_received, partner_received = receipt
        connection.execute(
            """
            INSERT INTO trade_receipt_status
                (trade_id, requester_received, requester_received_at,
                 partner_received, partner_received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                requester_received,
                completed_at if requester_received else None,
                partner_received,
                completed_at if partner_received else None,
            ),
        )
        for giver, receiver, album, code, quantity in positions or (
            (requester, partner, "vfl", "1", 1),
            (partner, requester, "vfl", "2", 1),
        ):
            connection.execute(
                """
                INSERT INTO trade_positions
                    (trade_id, from_user_id, to_user_id, album_id,
                     sticker_code, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (trade_id, giver, receiver, album, code, quantity),
            )
        return request_id, trade_id

    def lifecycle_quantities(
        self, connection, given, received, **kwargs
    ):
        requester = kwargs.get("requester", 1)
        partner = kwargs.get("partner", 2)
        return self.lifecycle(
            connection,
            positions=(
                (requester, partner, "vfl", "GIVEN", given),
                (partner, requester, "vfl", "RECEIVED", received),
            ),
            **kwargs,
        )

    def test_lifecycle_counts_once_and_both_perspectives_mirror_quantities(self):
        with self.connect() as connection:
            self.lifecycle(connection, positions=(
                (1, 2, "vfl", "A", 3),
                (1, 2, "wm26", "B", 2),
                (2, 1, "vfl", "C", 4),
            ))
            first = SuccessfulTradeProjectionService(connection).trades_for_user(1)
            second = SuccessfulTradeProjectionService(connection).trades_for_user(2)
        self.assertEqual((1, 1), (len(first), len(second)))
        self.assertEqual((5, 4), (
            first[0].given_quantity_total, first[0].received_quantity_total
        ))
        self.assertEqual((4, 5), (
            second[0].given_quantity_total, second[0].received_quantity_total
        ))
        self.assertEqual(first[0].canonical_trade_id, second[0].canonical_trade_id)
        self.assertEqual((2, 1), (
            first[0].partner_user_id, second[0].partner_user_id
        ))

    def test_active_shipped_partial_and_problem_terminal_states_do_not_count(self):
        with self.connect() as connection:
            for state, status in (
                ("accepted", "accepted"),
                ("partially_shipped", "accepted"),
                ("shipped", "accepted"),
                ("partially_received", "accepted"),
                ("closed_with_problem", "completed"),
                ("problem_resolved_after_close", "completed"),
            ):
                self.lifecycle(
                    connection, state=state, request_status=status,
                    completed_at=None, receipt=(0, 0),
                )
            self.assertEqual(
                (), SuccessfulTradeProjectionService(connection).trades_for_user(1)
            )

    def test_completed_lifecycle_requires_both_receipts_and_no_open_remainder(self):
        with self.connect() as connection:
            self.lifecycle(connection, receipt=(1, 0))
            _, trade_id = self.lifecycle(connection)
            position_id = connection.execute(
                "SELECT id FROM trade_positions WHERE trade_id=? LIMIT 1",
                (trade_id,),
            ).fetchone()[0]
            report_id = connection.execute(
                """
                INSERT INTO trade_receipt_reports
                    (trade_id, receiver_user_id, receiver_side, state)
                VALUES (?, 1, 'requester', 'open')
                """,
                (trade_id,),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trade_receipt_report_positions
                    (report_id, trade_position_id, expected_quantity,
                     initial_received_quantity, problem_type, state)
                VALUES (?, ?, 1, 0, 'missing', 'open')
                """,
                (report_id, position_id),
            )
            self.assertEqual(
                0, SuccessfulTradeProjectionService(connection).count_for_user(1)
            )

    def test_resolved_problem_can_count_but_open_quantity_fails_closed(self):
        with self.connect() as connection:
            _, trade_id = self.lifecycle(connection)
            position_id = connection.execute(
                "SELECT id FROM trade_positions WHERE trade_id=? LIMIT 1",
                (trade_id,),
            ).fetchone()[0]
            report_id = connection.execute(
                """
                INSERT INTO trade_receipt_reports
                    (trade_id, receiver_user_id, receiver_side, state, resolved_at)
                VALUES (?, 1, 'requester', 'resolved', CURRENT_TIMESTAMP)
                """,
                (trade_id,),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trade_receipt_report_positions
                    (report_id, trade_position_id, expected_quantity,
                     initial_received_quantity, resolution_received_quantity,
                     problem_type, state, resolved_at)
                VALUES (?, ?, 1, 0, 1, 'missing', 'resolved', CURRENT_TIMESTAMP)
                """,
                (report_id, position_id),
            )
            self.assertEqual(
                1, SuccessfulTradeProjectionService(connection).count_for_user(1)
            )

    def test_legacy_completed_counts_with_null_time_and_invalid_or_active_fails(self):
        with self.connect() as connection:
            valid = self.legacy(
                connection, give=("11", "11", "12"), receive=("7",)
            )
            self.legacy(connection, status="accepted")
            self.legacy(connection, raw_give="not-json")
            trades = SuccessfulTradeProjectionService(connection).trades_for_user(1)
        self.assertEqual(1, len(trades))
        self.assertEqual(valid, trades[0].source_id)
        self.assertEqual("legacy", trades[0].source_type)
        self.assertIsNone(trades[0].completed_at)
        self.assertEqual((3, 1), (
            trades[0].given_quantity_total, trades[0].received_quantity_total
        ))

    def test_lifecycle_representation_deduplicates_legacy_request(self):
        with self.connect() as connection:
            request_id, lifecycle_id = self.lifecycle(connection)
            trades = SuccessfulTradeProjectionService(connection).trades_for_user(1)
        self.assertEqual(1, len(trades))
        self.assertEqual(("lifecycle", lifecycle_id, request_id), (
            trades[0].source_type, trades[0].source_id,
            trades[0].trade_request_id,
        ))

    def test_album_projection_filters_positions_and_global_trade_stays_once(self):
        with self.connect() as connection:
            self.lifecycle(connection, positions=(
                (1, 2, "vfl", "A", 3),
                (2, 1, "vfl", "B", 1),
                (1, 2, "wm26", "C", 2),
                (2, 1, "wm26", "D", 4),
            ))
            service = SuccessfulTradeProjectionService(connection)
            global_values = service.aggregates_for_user(1)
            vfl = service.aggregates_for_user(1, "vfl")
            wm26 = service.aggregates_for_user(1, "wm26")
            absent = service.aggregates_for_user(1, "em24")
        self.assertEqual((1, 1, 1, 0), (
            global_values.successful_trade_count, vfl.successful_trade_count,
            wm26.successful_trade_count, absent.successful_trade_count,
        ))
        self.assertEqual((3, 1), (vfl.given_quantity_total, vfl.received_quantity_total))
        self.assertEqual((2, 4), (wm26.given_quantity_total, wm26.received_quantity_total))

    def test_largest_a_18_received_21_given_scores_21(self):
        with self.connect() as connection:
            self.lifecycle_quantities(connection, 21, 18)
            trade = SuccessfulTradeProjectionService(
                connection
            ).trades_for_user(1)[0]
        self.assertEqual((21, 18, 21), (
            trade.given_quantity_total,
            trade.received_quantity_total,
            trade.largest_trade_score,
        ))

    def test_largest_b_20_received_5_given_scores_20(self):
        with self.connect() as connection:
            self.lifecycle_quantities(connection, 5, 20)
            trade = SuccessfulTradeProjectionService(
                connection
            ).trades_for_user(1)[0]
        self.assertEqual(20, trade.largest_trade_score)

    def test_largest_c_balanced_7_and_7_scores_7(self):
        with self.connect() as connection:
            self.lifecycle_quantities(connection, 7, 7)
            trade = SuccessfulTradeProjectionService(
                connection
            ).trades_for_user(1)[0]
        self.assertEqual(7, trade.largest_trade_score)

    def test_largest_d_higher_score_wins(self):
        with self.connect() as connection:
            _, expected = self.lifecycle_quantities(
                connection, 5, 20, completed_at="2026-08-18 10:00:00"
            )
            self.lifecycle_quantities(
                connection, 18, 2, completed_at="2026-08-18 11:00:00"
            )
            largest = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1).largest_trade
        self.assertEqual(expected, largest.source_id)

    def test_largest_e_equal_score_later_completed_at_wins(self):
        with self.connect() as connection:
            self.lifecycle_quantities(
                connection, 20, 1, completed_at="2026-08-18 10:00:00"
            )
            _, expected = self.lifecycle_quantities(
                connection, 2, 20, completed_at="2026-08-18 11:00:00"
            )
            largest = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1).largest_trade
        self.assertEqual(expected, largest.source_id)

    def test_largest_f_known_timestamp_wins_over_missing_timestamp(self):
        with self.connect() as connection:
            self.legacy(
                connection,
                give=tuple(str(value) for value in range(20)),
                receive=("R",),
            )
            _, expected = self.lifecycle_quantities(
                connection, 1, 20, completed_at="2026-08-18 10:00:00"
            )
            largest = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1).largest_trade
        self.assertEqual(("lifecycle", expected), (
            largest.source_type, largest.source_id
        ))

    def test_largest_g_equal_score_and_time_uses_stable_canonical_id(self):
        with self.connect() as connection:
            _, expected = self.lifecycle_quantities(
                connection, 20, 1, completed_at="2026-08-18 10:00:00"
            )
            self.lifecycle_quantities(
                connection, 1, 20, completed_at="2026-08-18 10:00:00"
            )
            aggregate = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1)
        self.assertEqual(expected, aggregate.largest_trade.source_id)

    def test_largest_unparseable_timestamp_is_not_belastbar(self):
        with self.connect() as connection:
            self.lifecycle_quantities(
                connection, 20, 1, completed_at="kein-zeitpunkt"
            )
            _, expected = self.lifecycle_quantities(
                connection, 1, 20, completed_at="2026-08-18 10:00:00"
            )
            largest = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1).largest_trade
        self.assertEqual(expected, largest.source_id)

    def test_largest_h_score_is_not_given_plus_received(self):
        with self.connect() as connection:
            self.lifecycle_quantities(connection, 21, 18)
            trade = SuccessfulTradeProjectionService(
                connection
            ).trades_for_user(1)[0]
        self.assertEqual(21, trade.largest_trade_score)
        self.assertNotEqual(
            trade.given_quantity_total + trade.received_quantity_total,
            trade.largest_trade_score,
        )

    def test_largest_i_score_is_not_minimum_direction(self):
        with self.connect() as connection:
            self.lifecycle_quantities(connection, 21, 18)
            trade = SuccessfulTradeProjectionService(
                connection
            ).trades_for_user(1)[0]
        self.assertEqual(21, trade.largest_trade_score)
        self.assertNotEqual(
            min(trade.given_quantity_total, trade.received_quantity_total),
            trade.largest_trade_score,
        )

    def test_distinct_partners_and_largest_trade_use_po_score_and_ties(self):
        with self.connect() as connection:
            _, older = self.lifecycle(
                connection, partner=2, completed_at="2026-08-18 10:00:00",
                positions=((1, 2, "vfl", "A", 21), (2, 1, "vfl", "B", 18)),
            )
            _, newer = self.lifecycle(
                connection, partner=2, completed_at="2026-08-18 11:00:00",
                positions=((1, 2, "vfl", "C", 7), (2, 1, "vfl", "D", 21)),
            )
            _, same_time_larger_id = self.lifecycle(
                connection, partner=3, completed_at="2026-08-18 11:00:00",
                positions=((1, 3, "vfl", "E", 21), (3, 1, "vfl", "F", 1)),
            )
            aggregate = SuccessfulTradeProjectionService(
                connection
            ).aggregates_for_user(1)
        self.assertEqual((3, 2), (
            aggregate.successful_trade_count, aggregate.distinct_partner_count
        ))
        self.assertEqual(21, aggregate.largest_trade.largest_trade_score)
        self.assertEqual(newer, aggregate.largest_trade.source_id)
        self.assertNotEqual(older, aggregate.largest_trade.source_id)
        self.assertNotEqual(same_time_larger_id, aggregate.largest_trade.source_id)

    def test_rating_is_neither_success_source_nor_required(self):
        with self.connect() as connection:
            _, active_id = self.lifecycle(
                connection, state="accepted", request_status="accepted",
                completed_at=None, receipt=(0, 0),
            )
            connection.execute(
                """
                INSERT INTO trade_ratings
                    (trade_id, rater_user_id, rated_user_id, stars)
                VALUES (?, 1, 2, 5)
                """,
                (active_id,),
            )
            self.lifecycle(connection)
            self.assertEqual(
                1, SuccessfulTradeProjectionService(connection).count_for_user(1)
            )

    def test_foreign_user_and_mismatched_positions_fail_closed(self):
        with self.connect() as connection:
            self.lifecycle(connection, positions=((1, 3, "vfl", "A", 1),))
            service = SuccessfulTradeProjectionService(connection)
            self.assertEqual((), service.trades_for_user(1))
            self.assertEqual((), service.trades_for_user(3))

    def test_stable_sorting_null_last_and_reads_have_no_side_effects_or_n_plus_one(self):
        with self.connect() as connection:
            self.legacy(connection)
            self.lifecycle(connection, completed_at="2026-08-18 09:00:00")
            self.lifecycle(connection, completed_at="2026-08-18 10:00:00")
            before = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "notifications", "trade_events", "unlocked_trophies",
                    "historical_inventory_mutations",
                )
            }
            statements = []
            connection.set_trace_callback(statements.append)
            first = SuccessfulTradeProjectionService(connection).trades_for_user(1)
            connection.set_trace_callback(None)
            second = SuccessfulTradeProjectionService(connection).trades_for_user(1)
            after = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in before
            }
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual(
            ["2026-08-18 10:00:00", "2026-08-18 09:00:00", None],
            [trade.completed_at for trade in first],
        )
        selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")]
        self.assertLessEqual(len(selects), 9)

    def test_collector_profile_uses_canonical_count(self):
        with self.connect() as connection:
            self.legacy(connection)
            self.lifecycle(connection, receipt=(1, 0))
            profile = CollectorProfileService(connection).by_user_id(1, 1)
        self.assertEqual(1, profile.successful_trade_count)


if __name__ == "__main__":
    unittest.main()
