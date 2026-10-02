import hashlib
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from dataclasses import FrozenInstanceError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

from App.Database.migration_runner import migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.top_match_optimization import (  # noqa: E402
    MAX_SELECTED_PACKAGES,
    TopMatchOptimizationResultDTO,
    TopMatchOptimizationService,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TopMatchOptimizationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(REFERENCE_FIXTURE)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(REFERENCE_FIXTURE)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s21-")
        self.test_db = Path(self.test_dir.name) / "s21.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            migrate(connection, target_version=5)
            connection.execute("DELETE FROM stickers")

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def add_users(self, count):
        ids = []
        with self.connection() as connection:
            for index in range(count):
                cursor = connection.execute(
                    "INSERT INTO users (name, username, password) VALUES (?, ?, 'x')",
                    (f"S21 {index}", f"s21-{index}-{len(ids)}"),
                )
                ids.append(cursor.lastrowid)
        return tuple(ids)

    def set_inventory(self, user_id, album_id, quantities):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, 'owned', ?, ?)
                """,
                (
                    (
                        user_id,
                        album_id,
                        code,
                        max(quantity - 1, 0),
                        quantity,
                    )
                    for code, quantity in quantities.items()
                ),
            )

    def optimize(self, user_id, album_id, codes, partner_ids):
        with self.connection() as connection:
            return TopMatchOptimizationService(
                InventoryReadService(connection)
            ).optimize(user_id, album_id, codes, partner_ids)

    @staticmethod
    def package_ids(result):
        return tuple(package.partner_user_id for package in result.packages)

    @staticmethod
    def received_codes(result):
        return tuple(
            position.sticker_code
            for package in result.packages
            for position in package.receive_positions
        )

    @staticmethod
    def given_codes(result):
        return tuple(
            position.sticker_code
            for package in result.packages
            for position in package.give_positions
        )

    def create_binding(self, from_user, to_user, code, state="active", shipped=False):
        with self.connection() as connection:
            legacy = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', ?, ?, '[]', '[]', 'accepted')
                """,
                (from_user, to_user),
            ).lastrowid
            trade = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id, partner_user_id,
                     lifecycle_state)
                VALUES (?, ?, ?, ?)
                """,
                (
                    legacy,
                    from_user,
                    to_user,
                    "partially_shipped" if shipped else "accepted",
                ),
            ).lastrowid
            position = connection.execute(
                """
                INSERT INTO trade_positions
                    (trade_id, from_user_id, to_user_id, album_id,
                     sticker_code, quantity)
                VALUES (?, ?, ?, 'vfl', ?, 1)
                """,
                (trade, from_user, to_user, code),
            ).lastrowid
            if state == "active":
                connection.execute(
                    """
                    INSERT INTO trade_reservations
                        (trade_id, trade_position_id, user_id, album_id,
                         sticker_code, quantity, state)
                    VALUES (?, ?, ?, 'vfl', ?, 1, 'active')
                    """,
                    (trade, position, from_user, code),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO trade_reservations
                        (trade_id, trade_position_id, user_id, album_id,
                         sticker_code, quantity, state, released_at, release_reason)
                    VALUES (?, ?, ?, 'vfl', ?, 1, 'released', CURRENT_TIMESTAMP,
                            'shipped')
                    """,
                    (trade, position, from_user, code),
                )
            connection.execute(
                """
                INSERT INTO trade_shipping_status
                    (trade_id, requester_shipped, requester_shipped_at)
                VALUES (?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)
                """,
                (trade, int(shipped), int(shipped)),
            )
            connection.execute(
                "INSERT INTO trade_receipt_status (trade_id) VALUES (?)",
                (trade,),
            )

    def test_no_partner_returns_explained_empty_immutable_result(self):
        self.set_inventory(1, "vfl", {"G": 2})
        result = self.optimize(1, "vfl", ("G", "R"), ())
        self.assertIsInstance(result, TopMatchOptimizationResultDTO)
        self.assertEqual(((), 0, 0), (
            result.packages,
            result.total_covered_missing_count,
            result.selected_partner_count,
        ))
        self.assertIn("No executable", result.explanation)
        with self.assertRaises(FrozenInstanceError):
            result.total_covered_missing_count = 1

    def test_one_partner_produces_balanced_read_only_package(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        result = self.optimize(1, "vfl", ("G", "R"), (2,))
        self.assertEqual((2,), self.package_ids(result))
        self.assertEqual(("R",), self.received_codes(result))
        self.assertEqual(("G",), self.given_codes(result))
        self.assertEqual((1, 1, 1, 0), (
            result.total_covered_missing_count,
            result.selected_partner_count,
            result.total_given_quantity,
            result.redundant_received_positions,
        ))

    def test_more_than_three_partners_selects_at_most_three(self):
        partners = (2, 3) + self.add_users(2)
        codes = []
        subject = {}
        for index, partner in enumerate(partners, start=1):
            give = f"G{index}"
            receive = f"R{index}"
            codes.extend((give, receive))
            subject[give] = 2
            self.set_inventory(partner, "vfl", {receive: 2})
        self.set_inventory(1, "vfl", subject)
        result = self.optimize(1, "vfl", codes, partners)
        self.assertEqual(MAX_SELECTED_PACKAGES, result.selected_partner_count)
        self.assertEqual(3, result.total_covered_missing_count)

    def test_joint_optimization_beats_isolated_top_partner_order(self):
        partner_four, partner_five = self.add_users(2)
        own_codes = ("S1", "S2", "S3", "A1", "A2", "A3", "A4")
        self.set_inventory(1, "vfl", {code: 2 for code in own_codes})
        self.set_inventory(
            2,
            "vfl",
            {**{f"R{i}": 2 for i in range(1, 4)}, **{f"A{i}": 1 for i in range(1, 5)}},
        )
        self.set_inventory(
            3,
            "vfl",
            {**{f"R{i}": 2 for i in range(4, 7)}, **{f"A{i}": 1 for i in range(1, 5)}},
        )
        self.set_inventory(
            partner_four,
            "vfl",
            {
                "R7": 2,
                "R8": 2,
                "S1": 1,
                "S2": 1,
                "S3": 1,
                "A3": 1,
                "A4": 1,
            },
        )
        self.set_inventory(
            partner_five,
            "vfl",
            {
                "R9": 2,
                "R10": 2,
                "S1": 1,
                "S2": 1,
                "S3": 1,
                "A1": 1,
                "A2": 1,
            },
        )
        codes = own_codes + tuple(f"R{i}" for i in range(1, 11))
        result = self.optimize(
            1, "vfl", codes, (2, 3, partner_four, partner_five)
        )
        self.assertEqual(7, result.total_covered_missing_count)
        self.assertEqual((2, partner_four, partner_five), self.package_ids(result))
        self.assertNotIn(3, self.package_ids(result))

    def test_ger17_is_never_allocated_twice_and_larger_contribution_wins(self):
        self.set_inventory(1, "vfl", {"ALT": 2, "GER17": 2})
        self.set_inventory(2, "vfl", {"R1": 2, "R2": 2})
        self.set_inventory(3, "vfl", {"R3": 2})
        result = self.optimize(
            1, "vfl", ("ALT", "GER17", "R1", "R2", "R3"), (2, 3)
        )
        self.assertEqual((2,), self.package_ids(result))
        self.assertEqual(1, self.given_codes(result).count("GER17"))
        self.assertEqual(2, result.total_covered_missing_count)
        self.assertEqual((3,), tuple(
            conflict.partner_user_id for conflict in result.not_selected_conflicts
        ))

    def test_greater_progress_wins_before_fewer_partner_packages(self):
        partner_four = self.add_users(1)[0]
        self.set_inventory(
            1, "vfl", {"G1": 2, "G2": 2, "G3": 2, "G4": 2}
        )
        self.set_inventory(2, "vfl", {"R1": 2, "R2": 2})
        self.set_inventory(3, "vfl", {"R3": 2, "R4": 2})
        self.set_inventory(partner_four, "vfl", {"R5": 2})
        result = self.optimize(
            1,
            "vfl",
            ("G1", "G2", "G3", "G4", "R1", "R2", "R3", "R4", "R5"),
            (2, 3, partner_four),
        )
        self.assertEqual(4, result.total_covered_missing_count)
        self.assertEqual(2, result.selected_partner_count)

    def test_fewer_partners_wins_at_identical_coverage(self):
        self.set_inventory(1, "vfl", {"G1": 2, "G2": 2})
        self.set_inventory(2, "vfl", {"R1": 2, "R2": 2})
        self.set_inventory(3, "vfl", {"R1": 2})
        extra = self.add_users(1)[0]
        self.set_inventory(extra, "vfl", {"R2": 2})
        result = self.optimize(
            1, "vfl", ("G1", "G2", "R1", "R2"), (2, 3, extra)
        )
        self.assertEqual((2,), self.package_ids(result))
        self.assertEqual(2, result.total_covered_missing_count)

    def test_minimum_give_quantity_and_no_redundant_receipt(self):
        self.set_inventory(1, "vfl", {"G1": 2, "G2": 2, "G3": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        self.set_inventory(3, "vfl", {"R": 2})
        result = self.optimize(
            1, "vfl", ("G1", "G2", "G3", "R"), (2, 3)
        )
        self.assertEqual(1, result.total_covered_missing_count)
        self.assertEqual(1, result.total_given_quantity)
        self.assertEqual(0, result.redundant_received_positions)
        self.assertEqual(1, len(self.received_codes(result)))

    def test_smaller_partner_id_breaks_equal_bilateral_quantity(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R1": 2})
        self.set_inventory(3, "vfl", {"R1": 2, "R2": 2})
        result = self.optimize(1, "vfl", ("G", "R1", "R2"), (2, 3))
        self.assertEqual((2,), self.package_ids(result))
        self.assertEqual(50, result.personal_coverage_sum)

    def test_smaller_partner_id_breaks_equal_score(self):
        self.set_inventory(1, "vfl", {"GER17": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        self.set_inventory(3, "vfl", {"R": 2})
        result = self.optimize(1, "vfl", ("GER17", "R"), (3, 2))
        self.assertEqual((2,), self.package_ids(result))

    def test_lexicographically_smaller_codes_break_final_tie(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R1": 2, "R2": 2})
        receive_tie = self.optimize(1, "vfl", ("R2", "G", "R1"), (2,))
        self.assertEqual(("R1",), self.received_codes(receive_tie))

        self.set_inventory(1, "vfl", {"G1": 2, "G2": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        give_tie = self.optimize(1, "vfl", ("R", "G2", "G1"), (2,))
        self.assertEqual(("G1",), self.given_codes(give_tie))

    def test_input_order_and_repetition_are_deterministic(self):
        self.set_inventory(1, "vfl", {"G1": 2, "G2": 2})
        self.set_inventory(2, "vfl", {"R1": 2})
        self.set_inventory(3, "vfl", {"R2": 2})
        first = self.optimize(1, "vfl", ("G1", "G2", "R1", "R2"), (2, 3))
        second = self.optimize(1, "vfl", ("R2", "R1", "G2", "G1"), (3, 2, 3))
        third = self.optimize(1, "vfl", ("G1", "G2", "R1", "R2"), (2, 3))
        self.assertEqual(first, second)
        self.assertEqual(first.result_id, third.result_id)

    def test_quantity_greater_than_one_can_supply_two_partners_once_each(self):
        self.set_inventory(1, "vfl", {"GER17": 3})
        self.set_inventory(2, "vfl", {"R1": 2})
        self.set_inventory(3, "vfl", {"R2": 2})
        result = self.optimize(1, "vfl", ("GER17", "R1", "R2"), (2, 3))
        self.assertEqual((2, 3), self.package_ids(result))
        self.assertEqual(("GER17", "GER17"), self.given_codes(result))
        self.assertEqual(2, result.total_covered_missing_count)

    def test_active_reservation_excludes_subject_supply(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        self.create_binding(1, 3, "G", state="active", shipped=False)
        result = self.optimize(1, "vfl", ("G", "R"), (2,))
        self.assertEqual((), result.packages)

    def test_outgoing_transit_is_not_subject_supply(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"R": 2})
        self.create_binding(1, 3, "G", state="released", shipped=True)
        result = self.optimize(1, "vfl", ("G", "R"), (2,))
        self.assertEqual((), result.packages)

    def test_incoming_transit_is_not_subject_supply(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"R": 2})
        self.set_inventory(3, "vfl", {})
        self.create_binding(3, 1, "G", state="released", shipped=True)
        result = self.optimize(1, "vfl", ("G", "R"), (2,))
        self.assertEqual((), result.packages)

    def test_albums_remain_strictly_separate(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        self.set_inventory(1, "wm26", {})
        self.set_inventory(2, "wm26", {"R": 2})
        self.assertEqual(1, self.optimize(1, "vfl", ("G", "R"), (2,)).total_covered_missing_count)
        self.assertEqual(0, self.optimize(1, "wm26", ("G", "R"), (2,)).total_covered_missing_count)

    def test_snapshot_inventory_and_database_remain_unchanged(self):
        self.set_inventory(1, "vfl", {"G": 2})
        self.set_inventory(2, "vfl", {"R": 2})
        with self.connection() as connection:
            before = tuple(connection.iterdump())
            snapshot = InventoryReadService(connection).snapshot(
                1, "vfl", ("G", "R")
            )
            before_values = snapshot.stickers_by_code
        self.optimize(1, "vfl", ("G", "R"), (2,))
        with self.connection() as connection:
            after = tuple(connection.iterdump())
        self.assertEqual(before, after)
        self.assertEqual(before_values["G"].effective_available, 1)

    def test_reference_performance_budget_with_100_partners(self):
        fixture_started = time.perf_counter()
        partners = self.add_users(98)
        partner_ids = (2, 3) + partners
        codes = tuple(f"C{index:04d}" for index in range(1000))
        subject_inventory = {code: 2 for code in codes[:100]}
        self.set_inventory(1, "vfl", subject_inventory)
        partner_inventory = {code: 2 for code in codes[100:200]}
        with self.connection() as connection:
            rows = []
            for partner_id in partner_ids:
                for code, quantity in partner_inventory.items():
                    rows.append(
                        (
                            partner_id,
                            "vfl",
                            code,
                            "owned",
                            quantity - 1,
                            quantity,
                        )
                    )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        fixture_elapsed = time.perf_counter() - fixture_started

        with self.connection() as connection:
            service = TopMatchOptimizationService(InventoryReadService(connection))
            optimization_started = time.perf_counter()
            result = service.optimize(
                1, "vfl", codes, partner_ids
            )
            optimization_elapsed = time.perf_counter() - optimization_started
        complete_elapsed = time.perf_counter() - fixture_started

        self.assertEqual((2,), self.package_ids(result))
        self.assertEqual(100, result.total_covered_missing_count)
        self.assertLess(optimization_elapsed, 2.0)
        self.assertLess(complete_elapsed, 2.0)
        self.assertLess(fixture_elapsed, 2.0)


if __name__ == "__main__":
    unittest.main()
