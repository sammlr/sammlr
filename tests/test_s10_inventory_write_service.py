import atexit
from dataclasses import FrozenInstanceError
import hashlib
import inspect
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s10-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from services.inventory_write import (  # noqa: E402
    InventoryMutationDTO,
    InventoryWriteService,
)


class LegacyWriteAdapter:
    """Captured pre-S10 mechanics used only as the Golden Master."""

    def __init__(self, connection):
        self.connection = connection

    def row(self, user_id, album_id, code):
        return self.connection.execute(
            "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
            (user_id, album_id, code),
        ).fetchone()

    def change_quantity(self, user_id, album_id, code, delta):
        row = self.row(user_id, album_id, code)
        if row:
            quantity = max(row["quantity"] + delta, 0)
            duplicates = max(quantity - 1, 0)
            if quantity == 0:
                self.connection.execute(
                    "DELETE FROM stickers WHERE id=?", (row["id"],)
                )
            else:
                self.connection.execute(
                    "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                    (quantity, duplicates, row["id"]),
                )
        elif delta > 0:
            self.connection.execute(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, "owned", 0, ?)
                """,
                (user_id, album_id, code, delta),
            )

    def add(self, user_id, album_id, code, amount=1):
        self.change_quantity(user_id, album_id, code, max(amount, 0))

    def remove(self, user_id, album_id, code, amount=1):
        self.change_quantity(user_id, album_id, code, -max(amount, 0))

    def set_quantity(self, user_id, album_id, code, quantity):
        row = self.row(user_id, album_id, code)
        quantity = max(quantity, 0)
        duplicates = max(quantity - 1, 0)
        if quantity == 0:
            if row:
                self.connection.execute(
                    "DELETE FROM stickers WHERE id=?", (row["id"],)
                )
        elif row:
            self.connection.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (quantity, duplicates, row["id"]),
            )
        else:
            self.connection.execute(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, "owned", ?, ?)
                """,
                (user_id, album_id, code, duplicates, quantity),
            )


class InventoryWriteServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s10-test-")
        self.test_db = Path(self.test_dir.name) / "inventory.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))
        self.test_dir.cleanup()

    def connection(self, path=None):
        connection = sqlite3.connect(path or self.test_db, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def snapshot(self, connection):
        return [
            tuple(row)
            for row in connection.execute(
                """
                SELECT user_id, album_id, sticker_code, status,
                       duplicates, quantity
                FROM stickers
                ORDER BY user_id, album_id, sticker_code, id
                """
            ).fetchall()
        ]

    def quantity(self, code, user_id=1, album_id="vfl"):
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT quantity, duplicates FROM stickers
                WHERE user_id=? AND album_id=? AND sticker_code=?
                """,
                (user_id, album_id, code),
            ).fetchone()
        return tuple(row) if row else None

    def test_golden_master_matches_captured_legacy_command_sequence(self):
        legacy_db = Path(self.test_dir.name) / "legacy.db"
        service_db = Path(self.test_dir.name) / "service.db"
        shutil.copy2(REFERENCE_FIXTURE, legacy_db)
        shutil.copy2(REFERENCE_FIXTURE, service_db)

        with self.connection(legacy_db) as legacy_connection, self.connection(
            service_db
        ) as service_connection:
            legacy = LegacyWriteAdapter(legacy_connection)
            service = InventoryWriteService(service_connection)
            commands = (
                ("add", (1, "vfl", "1", 1)),
                ("add", (1, "vfl", "3", 3)),
                ("remove", (1, "vfl", "1", 2)),
                ("remove", (1, "vfl", "2", 5)),
                ("remove", (1, "vfl", "4", 1)),
                ("change_quantity", (2, "vfl", "3", -1)),
                ("change_quantity", (2, "vfl", "4", 2)),
                ("set_quantity", (1, "vfl", "1", 5)),
                ("set_quantity", (1, "vfl", "3", 0)),
                ("set_quantity", (1, "vfl", "4", 4)),
            )

            for method_name, arguments in commands:
                getattr(legacy, method_name)(*arguments)
                getattr(service, method_name)(*arguments)
                with self.subTest(method=method_name, arguments=arguments):
                    self.assertEqual(
                        self.snapshot(legacy_connection),
                        self.snapshot(service_connection),
                    )

    def test_mutation_dto_reports_existing_create_and_delete_results(self):
        with self.connection() as connection:
            service = InventoryWriteService(connection)
            updated = service.add(1, "vfl", "1")
            created = service.add(1, "vfl", "3")
            deleted = service.remove(1, "vfl", "2")

        self.assertIsInstance(updated, InventoryMutationDTO)
        self.assertEqual((3, 4, 3), (
            updated.previous_quantity, updated.quantity, updated.duplicates
        ))
        self.assertTrue(updated.changed)
        self.assertFalse(updated.created)
        self.assertFalse(updated.deleted)
        self.assertTrue(created.created)
        self.assertEqual((0, 1, 0), (
            created.previous_quantity, created.quantity, created.duplicates
        ))
        self.assertTrue(deleted.deleted)
        self.assertEqual(0, deleted.quantity)
        with self.assertRaises(FrozenInstanceError):
            updated.quantity = 99

    def test_invalid_legacy_amounts_remain_noops_without_new_guards(self):
        before = sha256(self.test_db)
        with self.connection() as connection:
            service = InventoryWriteService(connection)
            negative_add = service.add(1, "vfl", "1", -3)
            negative_remove = service.remove(1, "vfl", "1", -4)
            missing_remove = service.remove(1, "vfl", "249", 5)
            connection.commit()

        self.assertFalse(negative_add.changed)
        self.assertFalse(negative_remove.changed)
        self.assertFalse(missing_remove.changed)
        self.assertEqual(before, sha256(self.test_db))

    def test_service_leaves_commit_and_rollback_to_calling_workflow(self):
        with self.connection() as connection:
            service = InventoryWriteService(connection)
            service.add(1, "vfl", "1")
            self.assertEqual((4, 3), tuple(connection.execute(
                "SELECT quantity, duplicates FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'"
            ).fetchone()))
            connection.rollback()

        self.assertEqual((3, 2), self.quantity("1"))

    def test_concurrent_callers_are_serialized_by_existing_sqlite_transaction(self):
        errors = []
        barrier = threading.Barrier(3)

        def add_from_independent_connection():
            try:
                with self.connection() as connection:
                    barrier.wait()
                    connection.execute("BEGIN IMMEDIATE")
                    InventoryWriteService(connection).add(1, "vfl", "1")
                    connection.commit()
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [
            threading.Thread(target=add_from_independent_connection)
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertEqual((5, 4), self.quantity("1"))

    def test_batch_add_remove_and_undo_keep_legacy_session_behavior(self):
        add_response = self.client.post(
            "/bulk_add/vfl", data={"codes": ["1", "3"]}
        )
        self.assertEqual(302, add_response.status_code)
        self.assertEqual((4, 3), self.quantity("1"))
        self.assertEqual((1, 0), self.quantity("3"))
        self.client.post("/undo")
        self.assertEqual((3, 2), self.quantity("1"))
        self.assertIsNone(self.quantity("3"))

        remove_response = self.client.post(
            "/bulk_remove/vfl", data={"codes": ["1", "2", "3"]}
        )
        self.assertEqual(302, remove_response.status_code)
        self.assertEqual((2, 1), self.quantity("1"))
        self.assertIsNone(self.quantity("2"))
        self.assertIsNone(self.quantity("3"))
        self.client.post("/undo")
        self.assertEqual((3, 2), self.quantity("1"))
        self.assertEqual((1, 0), self.quantity("2"))
        # Legacy undo restores every selected code, including a missing code
        # for which bulk-remove itself performed no mutation.
        self.assertEqual((1, 0), self.quantity("3"))

    def test_detail_set_and_manual_swap_keep_exact_inventory_results(self):
        set_response = self.client.post(
            "/sticker/vfl/2", data={"quantity": "5"}
        )
        self.assertEqual(302, set_response.status_code)
        self.assertEqual((5, 4), self.quantity("2"))

        remove_response = self.client.post(
            "/sticker/vfl/2", data={"quantity": "0"}
        )
        self.assertEqual(302, remove_response.status_code)
        self.assertIsNone(self.quantity("2"))

        swap_response = self.client.post(
            "/album/vfl",
            data={
                "aktion": "trade",
                "filter": "all",
                "trade_out": "1",
                "trade_in": "3",
            },
        )
        self.assertEqual(302, swap_response.status_code)
        self.assertEqual((2, 1), self.quantity("1"))
        self.assertEqual((1, 0), self.quantity("3"))

    def test_paper_transfer_and_trade_completion_delegate_to_adapter(self):
        for function in (
            webapp.stickerliste_trade,
            webapp.complete_trade,
            webapp.change_sticker_quantity,
        ):
            source = inspect.getsource(function)
            with self.subTest(function=function.__name__):
                self.assertTrue(
                    "add_sticker_quantity" in source
                    or "remove_sticker_quantity" in source
                    or "InventoryWriteService" in source
                )

    def test_all_quantity_dml_is_centralized_with_documented_account_exception(self):
        source = inspect.getsource(webapp)
        webapp_statements = re.findall(
            r'(?:INSERT INTO|UPDATE|DELETE FROM) stickers[^\n]*', source
        )
        from services.account_lifecycle import AccountLifecycleService
        lifecycle_statements = re.findall(
            r'(?:INSERT INTO|UPDATE|DELETE FROM) stickers[^\n]*',
            inspect.getsource(AccountLifecycleService),
        )

        self.assertEqual([], webapp_statements)
        self.assertEqual(1, len(lifecycle_statements))
        self.assertTrue(
            lifecycle_statements[0].startswith("DELETE FROM stickers WHERE user_id=?")
        )
        self.assertIn("InventoryWriteService", inspect.getsource(webapp.add))
        self.assertIn("remove_sticker_quantity", inspect.getsource(webapp.remove))
        self.assertNotIn("create_notification", inspect.getsource(InventoryWriteService))
        self.assertNotIn("troph", inspect.getsource(InventoryWriteService).lower())

    def test_schema_and_canonical_databases_are_unchanged(self):
        with self.connection() as connection:
            columns = connection.execute("PRAGMA table_info(stickers)").fetchall()

        self.assertEqual(
            ["id", "album_id", "sticker_code", "status", "duplicates", "quantity", "user_id"],
            [column["name"] for column in columns],
        )
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
