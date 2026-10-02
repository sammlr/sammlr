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


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s12-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from services.inventory_guard import (  # noqa: E402
    InventoryGuard,
    InventoryGuardCode,
    InventoryGuardDecisionDTO,
    NoInventoryBindings,
)
from services.inventory_write import InventoryWriteService  # noqa: E402


class SimulatedBindings:
    """S12 test double only; no application reservation source exists."""

    def __init__(self, bindings=None):
        self.bindings = bindings or {}

    def minimum_quantity(self, user_id, album_id, sticker_code):
        return self.bindings.get((user_id, album_id, sticker_code), 0)


class InvalidBindingSource:
    def minimum_quantity(self, user_id, album_id, sticker_code):
        return "invalid"


class InventoryGuardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s12-test-")
        self.test_db = Path(self.test_dir.name) / "guard.db"
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

    def quantity(self, connection, code="1"):
        row = connection.execute(
            """
            SELECT quantity, duplicates FROM stickers
            WHERE user_id=1 AND album_id='vfl' AND sticker_code=?
            """,
            (code,),
        ).fetchone()
        return tuple(row) if row else None

    def bound_guard(self, amount, code="1"):
        source = SimulatedBindings({(1, "vfl", code): amount})
        return InventoryGuard(source)

    def test_change_without_binding_remains_allowed_and_unchanged(self):
        with self.connection() as connection:
            result = InventoryWriteService(connection).remove(
                1, "vfl", "1", 2
            )
            connection.commit()
            stored = self.quantity(connection)

        self.assertTrue(result.allowed)
        self.assertEqual("OK", result.error_code)
        self.assertEqual(InventoryGuardCode.OK, result.guard_decision.code)
        self.assertEqual((1, 0), stored)

    def test_simulated_binding_prevents_below_bound_stock(self):
        guard = self.bound_guard(2)
        with self.connection() as connection:
            changes_before = connection.total_changes
            result = InventoryWriteService(connection, guard).remove(
                1, "vfl", "1", 2
            )
            changes_after = connection.total_changes
            stored = self.quantity(connection)

        self.assertFalse(result.allowed)
        self.assertFalse(result.changed)
        self.assertEqual("BELOW_BOUND_STOCK", result.error_code)
        self.assertEqual(InventoryGuardCode.BELOW_BOUND_STOCK, result.guard_decision.code)
        self.assertEqual(2, result.guard_decision.bound_quantity)
        self.assertIn("Mindestens 2", result.guard_decision.explanation)
        self.assertEqual((3, 2), stored)
        self.assertEqual(changes_before, changes_after)

    def test_change_to_exact_bound_is_allowed(self):
        guard = self.bound_guard(2)
        with self.connection() as connection:
            result = InventoryWriteService(connection, guard).remove(
                1, "vfl", "1", 1
            )
            connection.commit()
            stored = self.quantity(connection)

        self.assertTrue(result.allowed)
        self.assertEqual((2, 1), stored)
        self.assertEqual(2, result.guard_decision.requested_quantity)

    def test_idempotent_change_is_allowed_even_for_simulated_inconsistent_bound(self):
        guard = self.bound_guard(4)
        with self.connection() as connection:
            result = InventoryWriteService(connection, guard).set_quantity(
                1, "vfl", "1", 3
            )
            connection.commit()
            stored = self.quantity(connection)

        self.assertTrue(result.allowed)
        self.assertFalse(result.changed)
        self.assertEqual("OK", result.error_code)
        self.assertEqual((3, 2), stored)

    def test_increase_is_allowed_and_does_not_enforce_existing_invalid_bound(self):
        guard = self.bound_guard(5)
        with self.connection() as connection:
            result = InventoryWriteService(connection, guard).add(
                1, "vfl", "1", 1
            )
            connection.commit()
            stored = self.quantity(connection)

        self.assertTrue(result.allowed)
        self.assertEqual((4, 3), stored)

    def test_all_defined_guard_codes_are_ui_neutral_strings(self):
        self.assertEqual(
            {"OK", "BELOW_BOUND_STOCK", "INVALID_OPERATION"},
            {code.value for code in InventoryGuardCode},
        )
        self.assertTrue(issubclass(InventoryGuardCode, str))

    def test_invalid_operations_return_defined_code(self):
        guard = InventoryGuard()
        invalid_values = (
            (-1, 0),
            (1, -1),
            (True, 1),
            (1, 1.5),
            ("1", 1),
        )

        for current, requested in invalid_values:
            decision = guard.evaluate(
                1, "vfl", "1", current, requested
            )
            with self.subTest(current=current, requested=requested):
                self.assertIsInstance(decision, InventoryGuardDecisionDTO)
                self.assertFalse(decision.allowed)
                self.assertEqual(
                    InventoryGuardCode.INVALID_OPERATION, decision.code
                )

    def test_invalid_binding_test_double_returns_invalid_operation(self):
        decision = InventoryGuard(InvalidBindingSource()).evaluate(
            1, "vfl", "1", 3, 2
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(InventoryGuardCode.INVALID_OPERATION, decision.code)
        self.assertIn("Ungültige Bindungsquelle", decision.explanation)

    def test_decision_dto_is_explainable_and_immutable(self):
        decision = self.bound_guard(2).evaluate(
            1, "vfl", "1", 3, 1
        )

        self.assertEqual((3, 1, 2), (
            decision.current_quantity,
            decision.requested_quantity,
            decision.bound_quantity,
        ))
        self.assertTrue(decision.explanation)
        with self.assertRaises(FrozenInstanceError):
            decision.code = InventoryGuardCode.OK

    def test_default_application_wiring_has_no_simulated_binding(self):
        self.assertEqual(
            0,
            NoInventoryBindings().minimum_quantity(1, "vfl", "1"),
        )
        for function in (
            webapp.add,
            webapp.remove,
            webapp.update_sticker_quantity_inline,
            webapp.stickerliste_trade,
            webapp.complete_trade,
        ):
            with self.subTest(function=function.__name__):
                source = inspect.getsource(function)
                self.assertNotIn("SimulatedBindings", source)
                self.assertNotIn("binding_source", source)

    def test_guard_is_service_centered_and_has_no_persistence_or_ui(self):
        write_source = inspect.getsource(InventoryWriteService)
        guard_source = inspect.getsource(InventoryGuard)

        self.assertIn("self._guard.evaluate", write_source)
        for forbidden in (
            "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "DROP ",
            "HTML", "CSS", "FLASK", "SESSION",
        ):
            self.assertNotIn(forbidden, guard_source.upper())

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
