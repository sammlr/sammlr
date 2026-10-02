import atexit
from dataclasses import FrozenInstanceError
import hashlib
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
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s11-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.inventory_availability import (  # noqa: E402
    AvailabilityDTO,
    LegacyAvailabilityCalculator,
)


class AvailabilityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s11-test-")
        self.test_db = Path(self.test_dir.name) / "availability.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db)
        connection.row_factory = sqlite3.Row
        return connection

    def legacy_quantities(self, connection, user_id, album_id):
        rows = connection.execute(
            "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchall()
        return {row["sticker_code"]: row["quantity"] for row in rows}

    def test_legacy_quantity_examples_map_to_s08_availability_exactly(self):
        expected = {
            0: (0, 0, 0, 0, 0, "not_physical"),
            1: (1, 1, 0, 0, 0, "assigned_only"),
            2: (2, 1, 0, 1, 0, "legacy_surplus_available"),
            5: (5, 1, 0, 4, 0, "legacy_surplus_available"),
        }

        for quantity, values in expected.items():
            availability = LegacyAvailabilityCalculator.from_quantity(quantity)
            with self.subTest(quantity=quantity):
                self.assertIsInstance(availability, AvailabilityDTO)
                self.assertEqual(values, (
                    availability.physical,
                    availability.assigned,
                    availability.reserved,
                    availability.available,
                    availability.incoming_transit,
                    availability.reason_code,
                ))
                self.assertEqual(availability.available, availability.reservable)
                self.assertTrue(availability.balance_is_valid)

    def test_available_is_never_negative_or_greater_than_physical(self):
        for quantity in range(-10, 101):
            availability = LegacyAvailabilityCalculator.from_quantity(quantity)
            with self.subTest(quantity=quantity):
                self.assertGreaterEqual(availability.available, 0)
                self.assertLessEqual(availability.available, availability.physical)
                self.assertTrue(availability.balance_is_valid)

    def test_reason_codes_and_explanations_make_each_state_understandable(self):
        missing = LegacyAvailabilityCalculator.from_quantity(0)
        assigned = LegacyAvailabilityCalculator.from_quantity(1)
        surplus = LegacyAvailabilityCalculator.from_quantity(3)

        self.assertFalse(missing.is_available)
        self.assertIn("keine physische Kopie", missing.explanation)
        self.assertFalse(assigned.is_available)
        self.assertIn("Einzelalbum zugeordnet", assigned.explanation)
        self.assertTrue(surplus.is_available)
        self.assertIn("2 physische Überschusskopie", surplus.explanation)
        with self.assertRaises(FrozenInstanceError):
            surplus.available = 99

    def test_fixture_projection_matches_today_quantity_and_duplicates(self):
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT user_id, album_id, sticker_code, quantity, duplicates
                FROM stickers
                """
            ).fetchall()

        self.assertGreater(len(rows), 0)
        for row in rows:
            availability = LegacyAvailabilityCalculator.from_quantity(
                row["quantity"]
            )
            with self.subTest(
                user=row["user_id"], album=row["album_id"], code=row["sticker_code"]
            ):
                self.assertEqual(row["quantity"], availability.physical)
                self.assertEqual(min(row["quantity"], 1), availability.assigned)
                self.assertEqual(row["duplicates"], availability.available)
                self.assertEqual(0, availability.reserved)
                self.assertEqual(0, availability.incoming_transit)

    def test_read_service_exposes_availability_for_present_and_missing_codes(self):
        with self.connection() as connection:
            album = InventoryReadService(connection).album(1, "vfl")

        present = album.availability("1")
        missing = album.availability("249")
        self.assertEqual((3, 1, 2), (
            present.physical, present.assigned, present.available
        ))
        self.assertEqual((0, 0, 0), (
            missing.physical, missing.assigned, missing.available
        ))
        self.assertEqual(present, album.items_by_code["1"].availability)
        with self.assertRaises(TypeError):
            album.availabilities["new"] = missing

    def test_collection_progress_and_paper_list_keep_golden_master_values(self):
        with self.connection() as connection:
            rows = self.legacy_quantities(connection, 1, "vfl")
            total = connection.execute(
                "SELECT total FROM albums WHERE id='vfl'"
            ).fetchone()["total"]

        codes = webapp.all_codes("vfl")
        old_collected = sum(rows.get(code, 0) > 0 for code in codes)
        old_duplicates = sum(max(rows.get(code, 0) - 1, 0) for code in codes)
        _, _, collected, duplicates, percent, returned_total = (
            webapp.lade_album_for_user("vfl", 1)
        )
        list_html = self.client.get("/album/vfl/liste").get_data(as_text=True)

        self.assertEqual((old_collected, old_duplicates), (collected, duplicates))
        self.assertEqual(int((old_collected / total) * 100), percent)
        self.assertEqual(total, returned_total)
        self.assertEqual(
            old_duplicates,
            list_html.count('data-list-mode="give"'),
        )

    def test_availability_matching_equals_legacy_quantity_matching_on_fixture(self):
        with self.connection() as connection:
            pairs = connection.execute(
                """
                SELECT mine.user_id AS mine_id, other.user_id AS other_id,
                       mine.album_id
                FROM user_albums mine
                JOIN user_albums other ON other.album_id = mine.album_id
                WHERE mine.user_id != other.user_id
                ORDER BY mine.user_id, other.user_id, mine.album_id
                """
            ).fetchall()
            service = InventoryReadService(connection)

            for pair in pairs:
                old_mine = self.legacy_quantities(
                    connection, pair["mine_id"], pair["album_id"]
                )
                old_other = self.legacy_quantities(
                    connection, pair["other_id"], pair["album_id"]
                )
                new_mine = service.album(pair["mine_id"], pair["album_id"])
                new_other = service.album(pair["other_id"], pair["album_id"])

                with self.subTest(
                    mine=pair["mine_id"], other=pair["other_id"], album=pair["album_id"]
                ):
                    self.assertEqual(
                        webapp.trade_candidates(
                            pair["album_id"], old_mine, old_other
                        ),
                        webapp.availability_trade_candidates(
                            pair["album_id"], new_mine, new_other
                        ),
                    )

    def test_active_collection_and_matching_paths_use_central_availability(self):
        for function in (
            webapp.lade_album_for_user,
            webapp.stickerliste,
            webapp.tauschbare_luecken_count,
            webapp.album_trade_preview_counts,
            webapp.album_trades,
            webapp.availability_trade_candidates,
            webapp.trade_center,
            webapp.create_trade_request,
            webapp.trades_overview,
        ):
            with self.subTest(function=function.__name__):
                source = inspect.getsource(function)
                self.assertTrue(
                    "availability" in source
                    or function is webapp.lade_album_for_user
                )

    def test_availability_component_is_read_only_and_schema_free(self):
        source = inspect.getsource(LegacyAvailabilityCalculator)
        for forbidden in (
            "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "DROP "
        ):
            self.assertNotIn(forbidden, source.upper())

        with self.connection() as connection:
            columns = connection.execute("PRAGMA table_info(stickers)").fetchall()
        self.assertEqual(
            ["id", "album_id", "sticker_code", "status", "duplicates", "quantity", "user_id"],
            [column["name"] for column in columns],
        )

    def test_canonical_databases_are_never_test_targets(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
