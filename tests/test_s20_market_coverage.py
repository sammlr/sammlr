import atexit
from dataclasses import FrozenInstanceError
import hashlib
import inspect
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s20-coverage-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_coverage import (  # noqa: E402
    CommunityMarketCoverageDTO,
    PersonalTradeCoverageDTO,
    TradeCoverageService,
)


class MarketCoverageTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s20-coverage-")
        self.test_db = Path(self.test_dir.name) / "coverage.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5), migrate(connection, target_version=5))
            self.assertEqual(5, current_version(connection))
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        self.login_as(2)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def set_inventory(self, user_id, album_id, quantities):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            for code, quantity in quantities.items():
                connection.execute(
                    """
                    INSERT INTO stickers
                        (user_id, album_id, sticker_code, status,
                         duplicates, quantity)
                    VALUES (?, ?, ?, 'owned', ?, ?)
                    """,
                    (user_id, album_id, code, max(quantity - 1, 0), quantity),
                )

    def market(self, user_id, album_id, codes, community_user_ids):
        with self.connection() as connection:
            return TradeCoverageService(
                InventoryReadService(connection)
            ).community_market_coverage(
                user_id, album_id, codes, community_user_ids
            )

    def personal(self, user_id, counterpart_user_id, album_id, codes):
        with self.connection() as connection:
            return TradeCoverageService(
                InventoryReadService(connection)
            ).personal_trade_coverage(
                user_id, counterpart_user_id, album_id, codes
            )

    def inventory_rows(self):
        with self.connection() as connection:
            return tuple(
                tuple(row)
                for row in connection.execute(
                    """
                    SELECT user_id, album_id, sticker_code, quantity, duplicates
                    FROM stickers ORDER BY user_id, album_id, sticker_code
                    """
                ).fetchall()
            )

    def database_dump(self):
        with self.connection() as connection:
            return tuple(connection.iterdump())

    def create_accepted_trade(self, give_codes=("1",), get_codes=("3",)):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, ?, ?, 'open')
                """,
                (json.dumps(give_codes), json.dumps(get_codes)),
            )
            trade_id = cursor.lastrowid
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        return trade_id

    def prepare_trade_inventory(self, sender_quantity=2):
        self.set_inventory(1, "vfl", {"1": sender_quantity})
        self.set_inventory(2, "vfl", {"3": 2})

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/ship").status_code)

    def report_missing(self, trade_id):
        with self.connection() as connection:
            position = connection.execute(
                """
                SELECT p.id FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=2
                """,
                (trade_id,),
            ).fetchone()
        self.login_as(2)
        self.assertEqual(
            302,
            self.client.post(
                f"/trade/{trade_id}/problem",
                data={
                    f"received_{position['id']}": "0",
                    f"problem_{position['id']}": "missing",
                },
            ).status_code,
        )

    def test_zero_percent_market_coverage_without_partner_supply(self):
        self.set_inventory(1, "vfl", {})
        result = self.market(1, "vfl", ("1", "2", "3"), ())
        self.assertEqual((3, 0, 3, 0), (
            result.missing_count,
            result.available_in_community_count,
            result.unavailable_count,
            result.coverage_percent,
        ))
        self.assertEqual(0, result.community_user_count)

    def test_full_market_coverage_is_one_hundred_percent(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 2, "2": 3, "3": 2})
        result = self.market(1, "vfl", ("1", "2", "3"), (2,))
        self.assertEqual((3, 3, 0, 100), (
            result.missing_count,
            result.available_in_community_count,
            result.unavailable_count,
            result.coverage_percent,
        ))

    def test_partial_market_coverage_uses_distinct_codes(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 5})
        result = self.market(1, "vfl", ("1", "2", "3", "1"), (2,))
        self.assertEqual((3, 1, 2, 33), (
            result.missing_count,
            result.available_in_community_count,
            result.unavailable_count,
            result.coverage_percent,
        ))
        self.assertEqual(("1",), result.available_codes)

    def test_personal_coverage_separates_present_and_effective(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 1, "2": 2})
        result = self.personal(1, 2, "vfl", ("1", "2", "3"))
        self.assertIsInstance(result, PersonalTradeCoverageDTO)
        self.assertEqual((3, 2, 1, 33), (
            result.missing_count,
            result.present_at_counterpart_count,
            result.effectively_available_count,
            result.coverage_percent,
        ))
        self.assertEqual(("1", "2"), result.present_at_counterpart_codes)
        self.assertEqual(("2",), result.effectively_available_codes)

    def test_mutual_personal_coverage_can_be_asymmetric(self):
        self.set_inventory(1, "vfl", {"1": 2})
        self.set_inventory(2, "vfl", {"2": 2, "3": 2})
        one_from_two = self.personal(1, 2, "vfl", ("1", "2", "3"))
        two_from_one = self.personal(2, 1, "vfl", ("1", "2", "3"))
        self.assertEqual((2, 2, 100), (
            one_from_two.missing_count,
            one_from_two.effectively_available_count,
            one_from_two.coverage_percent,
        ))
        self.assertEqual((1, 1, 100), (
            two_from_one.missing_count,
            two_from_one.effectively_available_count,
            two_from_one.coverage_percent,
        ))
        self.assertNotEqual(
            one_from_two.effectively_available_count,
            two_from_one.effectively_available_count,
        )

    def test_active_reservation_reduces_personal_effective_coverage(self):
        self.prepare_trade_inventory(sender_quantity=2)
        trade_id = self.create_accepted_trade()
        result = self.personal(2, 1, "vfl", ("1",))
        self.assertGreater(trade_id, 0)
        self.assertEqual((1, 1, 0, 0), (
            result.missing_count,
            result.present_at_counterpart_count,
            result.effectively_available_count,
            result.coverage_percent,
        ))

    def test_incoming_transit_does_not_cover_missing_code(self):
        self.prepare_trade_inventory(sender_quantity=2)
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.personal(2, 1, "vfl", ("1",))
        with self.connection() as connection:
            incoming = InventoryReadService(connection).snapshot(
                2, "vfl", ("1",)
            ).sticker("1").incoming_transit
        self.assertEqual(1, incoming)
        self.assertEqual((1, 0), (
            result.missing_count, result.effectively_available_count,
        ))

    def test_outgoing_transit_is_not_counted_as_market_supply(self):
        self.prepare_trade_inventory(sender_quantity=2)
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        result = self.market(2, "vfl", ("1",), (1,))
        with self.connection() as connection:
            outgoing = InventoryReadService(connection).snapshot(
                1, "vfl", ("1",)
            ).sticker("1").outgoing_transit
        self.assertEqual(1, outgoing)
        self.assertEqual((0, 1, 0), (
            result.available_in_community_count,
            result.unavailable_count,
            result.coverage_percent,
        ))

    def test_preexisting_snapshot_object_remains_unchanged(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 2})
        with self.connection() as connection:
            inventory = InventoryReadService(connection)
            snapshot = inventory.snapshot(1, "vfl", ("1", "2"))
            before = tuple(snapshot.stickers_by_code.items())
            result = TradeCoverageService(inventory).community_market_coverage(
                1, "vfl", ("1", "2"), (2,)
            )
            after = tuple(snapshot.stickers_by_code.items())
        self.assertEqual(before, after)
        self.assertEqual(1, result.available_in_community_count)
        with self.assertRaises(TypeError):
            snapshot.stickers_by_code["new"] = snapshot.sticker("1")

    def test_coverage_reads_leave_inventory_unchanged(self):
        self.set_inventory(1, "vfl", {"3": 1})
        self.set_inventory(2, "vfl", {"1": 2, "2": 1})
        rows_before = self.inventory_rows()
        dump_before = self.database_dump()
        self.market(1, "vfl", ("1", "2", "3"), (2, 3))
        self.personal(1, 2, "vfl", ("1", "2", "3"))
        self.assertEqual(rows_before, self.inventory_rows())
        self.assertEqual(dump_before, self.database_dump())

    def test_multiple_users_form_union_without_double_counting(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 2, "2": 1})
        self.set_inventory(3, "vfl", {"1": 4, "2": 2})
        result = self.market(1, "vfl", ("1", "2", "3"), (1, 2, 2, 3))
        self.assertEqual((2, 1, 2), (
            result.available_in_community_count,
            result.unavailable_count,
            result.community_user_count,
        ))
        self.assertEqual(("1", "2"), result.available_codes)

    def test_multiple_albums_remain_strictly_separate(self):
        self.set_inventory(1, "vfl", {})
        self.set_inventory(2, "vfl", {"1": 2})
        self.set_inventory(1, "em24", {})
        self.set_inventory(2, "em24", {"A1": 1})
        vfl = self.market(1, "vfl", ("1",), (2,))
        em24 = self.market(1, "em24", ("A1",), (2,))
        self.assertEqual((100, 0), (vfl.coverage_percent, em24.coverage_percent))
        self.assertEqual(("A1",), em24.unavailable_codes)

    def test_open_problem_keeps_missing_code_uncovered(self):
        self.prepare_trade_inventory(sender_quantity=2)
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_missing(trade_id)
        result = self.personal(2, 1, "vfl", ("1",))
        self.assertEqual((1, 1, 0, 0), (
            result.missing_count,
            result.present_at_counterpart_count,
            result.effectively_available_count,
            result.coverage_percent,
        ))

    def test_problem_resolution_updates_later_snapshot_without_mutation(self):
        self.prepare_trade_inventory(sender_quantity=2)
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_missing(trade_id)
        before = self.personal(2, 1, "vfl", ("1",))
        self.login_as(2)
        self.assertEqual(
            302,
            self.client.post(
                f"/trade/{trade_id}/problem/resolve",
                data={"confirm_physical_arrival": "1"},
            ).status_code,
        )
        after = self.personal(2, 1, "vfl", ("1",))
        self.assertEqual((1, 0), (before.missing_count, after.missing_count))
        self.assertIsNone(after.coverage_percent)
        self.assertFalse(after.has_missing)

    def test_service_is_snapshot_only_read_only_and_dtos_are_immutable(self):
        source = inspect.getsource(TradeCoverageService)
        self.assertIn(".snapshot(", source)
        self.assertNotIn(".album(", source)
        for forbidden in (
            "INSERT ", "UPDATE ", "DELETE ", "COMMIT", "ROLLBACK",
            "RANK", "SORTED(",
        ):
            self.assertNotIn(forbidden, source.upper())

        self.set_inventory(1, "vfl", {})
        result = self.market(1, "vfl", ("1",), ())
        self.assertIsInstance(result, CommunityMarketCoverageDTO)
        self.assertTrue(result.scope)
        self.assertTrue(result.confidence)
        with self.assertRaises(FrozenInstanceError):
            result.coverage_percent = 99


if __name__ == "__main__":
    unittest.main()
