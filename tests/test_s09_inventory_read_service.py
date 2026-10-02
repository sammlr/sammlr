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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s09-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from services.inventory import (  # noqa: E402
    AlbumInventoryDTO,
    AlbumProgressDTO,
    InventoryReadService,
    StickerInventoryDTO,
)


class InventoryReadServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s09-test-")
        self.test_db = Path(self.test_dir.name) / "inventory.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.test_db)
        connection.row_factory = sqlite3.Row
        return connection

    def legacy_rows_by_code(self, connection, user_id, album_id):
        rows = connection.execute(
            "SELECT * FROM stickers WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchall()
        return {row["sticker_code"]: row for row in rows}

    def legacy_quantities(self, connection, user_id, album_id):
        rows = connection.execute(
            "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchall()
        return {row["sticker_code"]: row["quantity"] for row in rows}

    def legacy_progress(self, by_code, codes, total):
        collected = 0
        duplicate_quantity = 0
        for code in codes:
            quantity = by_code[code]["quantity"] if code in by_code else 0
            if quantity > 0:
                collected += 1
            if quantity > 1:
                duplicate_quantity += quantity - 1
        return collected, duplicate_quantity, int((collected / total) * 100)

    def legacy_matching_counts(self, connection, user_id, album_id):
        codes = webapp.all_codes(album_id)
        mine = self.legacy_quantities(connection, user_id, album_id)
        my_missing = {code for code in codes if mine.get(code, 0) == 0}
        my_duplicates = {code for code in codes if mine.get(code, 0) >= 2}
        other_users = connection.execute(
            """
            SELECT users.id
            FROM users
            JOIN user_albums ON user_albums.user_id = users.id
            WHERE users.id != ? AND user_albums.album_id = ?
            """,
            (user_id, album_id),
        ).fetchall()

        market_codes = set()
        direct_partner_count = 0
        for user in other_users:
            other = self.legacy_quantities(connection, user["id"], album_id)
            other_missing = {code for code in codes if other.get(code, 0) == 0}
            other_duplicates = {code for code in codes if other.get(code, 0) >= 2}
            receive = my_missing.intersection(other_duplicates)
            give = my_duplicates.intersection(other_missing)
            market_codes.update(receive)
            if receive and give:
                direct_partner_count += 1

        return len(market_codes), direct_partner_count

    def test_fixture_rows_match_old_read_path_exactly(self):
        with self.connection() as connection:
            pairs = connection.execute(
                "SELECT DISTINCT user_id, album_id FROM stickers ORDER BY user_id, album_id"
            ).fetchall()
            service = InventoryReadService(connection)

            for pair in pairs:
                user_id = pair["user_id"]
                album_id = pair["album_id"]
                old = self.legacy_rows_by_code(connection, user_id, album_id)
                new = service.album(user_id, album_id)

                with self.subTest(user_id=user_id, album_id=album_id):
                    self.assertIsInstance(new, AlbumInventoryDTO)
                    self.assertEqual(set(old), set(new.items_by_code))
                    for code, row in old.items():
                        item = new.items_by_code[code]
                        self.assertIsInstance(item, StickerInventoryDTO)
                        self.assertEqual(row["id"], item.id)
                        self.assertEqual(row["status"], item.status)
                        self.assertEqual(row["duplicates"], item.duplicates)
                        self.assertEqual(row["quantity"], item.quantity)

    def test_quantity_dto_projects_current_physical_duplicate_and_available_values(self):
        expected = {
            0: (0, 0, 0),
            1: (1, 0, 0),
            2: (2, 1, 1),
            5: (5, 4, 4),
        }
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=1 AND album_id='vfl'"
            )
            for index, quantity in enumerate(expected, start=1):
                connection.execute(
                    """
                    INSERT INTO stickers
                        (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (1, 'vfl', ?, 'owned', ?, ?)
                    """,
                    (str(index), max(quantity - 1, 0), quantity),
                )
            connection.commit()

            inventory = InventoryReadService(connection).album(1, "vfl")
            for index, values in enumerate(expected.values(), start=1):
                item = inventory.items_by_code[str(index)]
                with self.subTest(quantity=item.quantity):
                    self.assertEqual(values, (
                        item.physical,
                        item.duplicate_quantity,
                        item.available,
                    ))

    def test_album_progress_matches_captured_old_calculation_for_edge_quantities(self):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=1 AND album_id='vfl'"
            )
            for code, quantity in (("1", 0), ("2", 1), ("3", 2), ("4", 5)):
                connection.execute(
                    """
                    INSERT INTO stickers
                        (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (1, 'vfl', ?, 'owned', ?, ?)
                    """,
                    (code, max(quantity - 1, 0), quantity),
                )
            connection.commit()

            codes = ("1", "2", "3", "4", "5")
            old = self.legacy_progress(
                self.legacy_rows_by_code(connection, 1, "vfl"), codes, 5
            )
            progress = InventoryReadService(connection).album(1, "vfl").progress(
                codes, 5
            )

        self.assertIsInstance(progress, AlbumProgressDTO)
        self.assertEqual(old, (
            progress.collected,
            progress.duplicate_quantity,
            progress.percent,
        ))
        self.assertEqual(5, progress.total)

    def test_collection_adapter_matches_old_fixture_progress_and_row_access(self):
        with self.connection() as connection:
            album = connection.execute(
                "SELECT * FROM albums WHERE id='vfl'"
            ).fetchone()
            old_by_code = self.legacy_rows_by_code(connection, 1, "vfl")
            old_progress = self.legacy_progress(
                old_by_code, webapp.all_codes("vfl"), album["total"]
            )

        _, by_code, collected, duplicates, percent, total = (
            webapp.lade_album_for_user("vfl", 1)
        )

        self.assertEqual(old_progress, (collected, duplicates, percent))
        self.assertEqual(album["total"], total)
        self.assertEqual(old_by_code["1"]["quantity"], by_code["1"]["quantity"])

    def test_matching_candidates_are_identical_for_old_and_new_quantities(self):
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
                new_mine = service.album(
                    pair["mine_id"], pair["album_id"]
                ).quantities
                new_other = service.album(
                    pair["other_id"], pair["album_id"]
                ).quantities

                with self.subTest(
                    mine=pair["mine_id"],
                    other=pair["other_id"],
                    album=pair["album_id"],
                ):
                    self.assertEqual(old_mine, dict(new_mine))
                    self.assertEqual(old_other, dict(new_other))
                    self.assertEqual(
                        webapp.trade_candidates(pair["album_id"], old_mine, old_other),
                        webapp.trade_candidates(pair["album_id"], new_mine, new_other),
                    )

    def test_matching_preview_counts_match_captured_old_queries(self):
        with self.connection() as connection:
            album_ids = [
                row["album_id"]
                for row in connection.execute(
                    "SELECT album_id FROM user_albums WHERE user_id=1 ORDER BY album_id"
                ).fetchall()
            ]
            expected = {
                album_id: self.legacy_matching_counts(connection, 1, album_id)
                for album_id in album_ids
            }

        with webapp.app.test_request_context("/"):
            webapp.session["user_id"] = 1
            for album_id in album_ids:
                with self.subTest(album_id=album_id):
                    self.assertEqual(
                        expected[album_id][0],
                        webapp.tauschbare_luecken_count(album_id),
                    )
                    self.assertEqual(
                        expected[album_id],
                        webapp.album_trade_preview_counts(album_id),
                    )

    def test_missing_inventory_is_an_empty_typed_result(self):
        with self.connection() as connection:
            inventory = InventoryReadService(connection).album(9999, "unknown")

        self.assertIsInstance(inventory, AlbumInventoryDTO)
        self.assertEqual({}, dict(inventory.items_by_code))
        self.assertEqual({}, dict(inventory.quantities))
        self.assertEqual(0, inventory.quantity("missing"))

    def test_dtos_and_mappings_are_read_only(self):
        with self.connection() as connection:
            inventory = InventoryReadService(connection).album(1, "vfl")
        item = next(iter(inventory.items_by_code.values()))

        with self.assertRaises(FrozenInstanceError):
            item.quantity = 99
        with self.assertRaises(TypeError):
            inventory.items_by_code["new"] = item
        with self.assertRaises(TypeError):
            inventory.quantities["new"] = 1

    def test_service_performs_no_database_write(self):
        before_hash = sha256(self.test_db)
        with self.connection() as connection:
            changes_before = connection.total_changes
            service = InventoryReadService(connection)
            service.album(1, "vfl")
            service.album(2, "em24")
            changes_after = connection.total_changes

        self.assertEqual(changes_before, changes_after)
        self.assertEqual(before_hash, sha256(self.test_db))

    def test_migrated_collection_and_matching_paths_use_central_service(self):
        for function in (
            webapp.lade_album_for_user,
            webapp.tauschbare_luecken_count,
            webapp.album_trade_preview_counts,
            webapp.album_trades,
            webapp.user_album_quantities,
            webapp.trades_overview,
        ):
            with self.subTest(function=function.__name__):
                self.assertIn("InventoryReadService", inspect.getsource(function))

    def test_current_schema_is_unchanged(self):
        with self.connection() as connection:
            columns = connection.execute("PRAGMA table_info(stickers)").fetchall()

        self.assertEqual(
            ["id", "album_id", "sticker_code", "status", "duplicates", "quantity", "user_id"],
            [column["name"] for column in columns],
        )


if __name__ == "__main__":
    unittest.main()
