import atexit
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
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s19-snapshot-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402
from services.inventory import (  # noqa: E402
    AVAILABILITY_SNAPSHOT_VERSION,
    AlbumAvailabilitySnapshotDTO,
    AlbumInventoryDTO,
    InventoryReadService,
    StickerAvailabilitySnapshotDTO,
)


class SharedAvailabilitySnapshotTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s19-snapshot-")
        self.test_db = Path(self.test_dir.name) / "snapshot.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5), migrate(connection, target_version=5))
            self.assertEqual(5, current_version(connection))
            connection.execute(
                "DELETE FROM stickers WHERE user_id=2 AND album_id='vfl' "
                "AND sticker_code='1'"
            )
            connection.execute(
                """
                UPDATE stickers SET quantity=5, duplicates=4
                WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'
                """
            )
            connection.execute(
                """
                UPDATE stickers SET quantity=5, duplicates=4
                WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'
                """
            )
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

    def snapshot(self, user_id, code, catalog_codes=()):
        with self.connection() as connection:
            album_snapshot = InventoryReadService(connection).snapshot(
                user_id, "vfl", catalog_codes
            )
            return album_snapshot, album_snapshot.sticker(code)

    def inventory_rows(self):
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT user_id, album_id, sticker_code, quantity, duplicates
                FROM stickers ORDER BY user_id, album_id, sticker_code
                """
            ).fetchall()
            return tuple(tuple(row) for row in rows)

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

    def ship_as(self, trade_id, user_id):
        self.login_as(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/ship").status_code)

    def receive_as(self, trade_id, user_id):
        self.login_as(user_id)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/receive").status_code)

    def incoming_position(self, trade_id, user_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT p.id, p.quantity FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=?
                """,
                (trade_id, user_id),
            ).fetchone()

    def report_missing(self, trade_id, received=0):
        position = self.incoming_position(trade_id, 2)
        self.login_as(2)
        self.assertEqual(
            302,
            self.client.post(
                f"/trade/{trade_id}/problem",
                data={
                    f"received_{position['id']}": str(received),
                    f"problem_{position['id']}": "missing",
                },
            ).status_code,
        )

    def test_snapshot_matches_current_inventory_and_contract_type(self):
        album, item = self.snapshot(1, "1", ("1", "249"))
        self.assertIsInstance(album, AlbumAvailabilitySnapshotDTO)
        self.assertIsInstance(item, StickerAvailabilitySnapshotDTO)
        self.assertEqual(AVAILABILITY_SNAPSHOT_VERSION, album.version)
        self.assertTrue(album.captured_at)
        self.assertEqual(("1", 5, 1, 0, 4), (
            item.sticker_code, item.physical, item.assigned,
            item.reserved, item.available,
        ))

    def test_active_reservations_are_included_once(self):
        self.create_accepted_trade()
        _, item = self.snapshot(1, "1")
        self.assertEqual((5, 1, 1, 3), (
            item.physical, item.assigned, item.reserved, item.available,
        ))

    def test_incoming_transit_is_projected_for_receiver(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        _, item = self.snapshot(2, "1")
        self.assertEqual((0, 1), (item.physical, item.incoming_transit))

    def test_outgoing_transit_is_projected_for_sender(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        _, item = self.snapshot(1, "1")
        self.assertEqual((4, 1, 0), (
            item.physical, item.outgoing_transit, item.reserved,
        ))

    def test_missing_state_is_derived_from_physical_only(self):
        _, item = self.snapshot(2, "1", ("1",))
        self.assertTrue(item.missing)
        self.assertEqual(0, item.physical)

    def test_present_state_is_not_missing(self):
        _, item = self.snapshot(1, "1")
        self.assertFalse(item.missing)
        self.assertEqual(5, item.physical)

    def test_duplicates_are_physical_surplus(self):
        _, item = self.snapshot(1, "1")
        self.assertEqual(4, item.duplicates)

    def test_effective_available_matches_existing_availability(self):
        trade_id = self.create_accepted_trade()
        _, item = self.snapshot(1, "1")
        self.assertEqual(item.available, item.effective_available)
        self.assertEqual(3, item.effective_available)
        self.assertTrue(item.is_available)
        self.assertEqual(trade_id > 0, True)

    def test_snapshot_after_shipping_preserves_free_availability(self):
        trade_id = self.create_accepted_trade()
        _, before = self.snapshot(1, "1")
        self.ship_as(trade_id, 1)
        _, after = self.snapshot(1, "1")
        self.assertEqual(before.effective_available, after.effective_available)
        self.assertEqual((1, 0), (after.outgoing_transit, after.reserved))

    def test_snapshot_after_receipt_moves_transit_to_physical(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.receive_as(trade_id, 2)
        _, sender = self.snapshot(1, "1")
        _, receiver = self.snapshot(2, "1")
        self.assertEqual(0, sender.outgoing_transit)
        self.assertEqual((1, 0), (receiver.physical, receiver.incoming_transit))

    def test_open_problem_keeps_only_open_quantity_in_transit(self):
        trade_id = self.create_accepted_trade(give_codes=("1", "1", "1"))
        self.ship_as(trade_id, 1)
        self.report_missing(trade_id, received=2)
        _, sender = self.snapshot(1, "1")
        _, receiver = self.snapshot(2, "1")
        self.assertEqual(1, sender.outgoing_transit)
        self.assertEqual((2, 1), (receiver.physical, receiver.incoming_transit))

    def test_problem_resolution_clears_both_transit_views(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.report_missing(trade_id)
        self.login_as(2)
        self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        _, sender = self.snapshot(1, "1")
        _, receiver = self.snapshot(2, "1")
        self.assertEqual((0, 0, 1), (
            sender.outgoing_transit,
            receiver.incoming_transit,
            receiver.physical,
        ))

    def test_multiple_concurrent_trades_are_aggregated(self):
        first = self.create_accepted_trade()
        second = self.create_accepted_trade()
        _, reserved = self.snapshot(1, "1")
        self.assertEqual((2, 2), (reserved.reserved, reserved.effective_available))
        self.ship_as(first, 1)
        self.ship_as(second, 1)
        _, sender = self.snapshot(1, "1")
        _, receiver = self.snapshot(2, "1")
        self.assertEqual((2, 2), (sender.outgoing_transit, receiver.incoming_transit))

    def test_snapshot_read_does_not_mutate_any_database_state(self):
        before = self.database_dump()
        with self.connection() as connection:
            service = InventoryReadService(connection)
            service.snapshot(1, "vfl", webapp.all_codes("vfl"))
            service.snapshot(2, "vfl", webapp.all_codes("vfl"))
        self.assertEqual(before, self.database_dump())

    def test_snapshot_read_leaves_inventory_rows_unchanged(self):
        before = self.inventory_rows()
        self.snapshot(1, "1")
        self.snapshot(2, "1", ("1",))
        self.assertEqual(before, self.inventory_rows())

    def test_stickerwall_reads_incoming_from_shared_snapshot(self):
        trade_id = self.create_accepted_trade()
        self.ship_as(trade_id, 1)
        self.login_as(2)
        html = self.client.get("/album/vfl").get_data(as_text=True)
        self.assertIn('data-code="1"', html)
        self.assertIn('data-incoming-transit="1"', html)
        self.assertIn("Unterwegs", html)
        self.assertIn(
            "availability_snapshot_for",
            inspect.getsource(webapp.sticker_wall_slot_html),
        )

    def test_trade_views_and_candidates_read_shared_snapshot(self):
        with self.connection() as connection:
            service = InventoryReadService(connection)
            mine = service.album(1, "vfl")
            partner = service.album(2, "vfl")
            with patch.object(
                AlbumInventoryDTO,
                "availability",
                side_effect=AssertionError("legacy availability adapter used"),
            ):
                get_counts, give_counts = webapp.availability_trade_candidates(
                    "vfl", mine, partner
                )
        self.assertIn("3", get_counts)
        self.assertIn("1", give_counts)
        self.assertIn(
            "availability_snapshot_for",
            inspect.getsource(webapp.availability_trade_candidates),
        )

    def test_unbound_bilateral_matching_remains_golden_master_identical(self):
        with self.connection() as connection:
            service = InventoryReadService(connection)
            mine = service.album(1, "vfl")
            partner = service.album(2, "vfl")
            old = webapp.trade_candidates("vfl", mine.quantities, partner.quantities)
            new = webapp.availability_trade_candidates("vfl", mine, partner)
        self.assertEqual(old, new)


if __name__ == "__main__":
    unittest.main()
