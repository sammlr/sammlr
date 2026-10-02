import hashlib
from dataclasses import dataclass, fields
from pathlib import Path
import sqlite3
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


@dataclass(frozen=True)
class InventoryContractState:
    physical: int
    assigned: int
    available: int
    reserved: int
    outgoing_transit: int = 0
    incoming_transit: int = 0

    def violations(self):
        violations = []
        values = {field.name: getattr(self, field.name) for field in fields(self)}
        if any(type(value) is not int for value in values.values()):
            violations.append("all quantities must be integers")
            return violations
        if any(value < 0 for value in values.values()):
            violations.append("all quantities must be nonnegative")
        if self.physical != self.assigned + self.available + self.reserved:
            violations.append("physical balance must be exact")
        if self.available > self.physical:
            violations.append("available must not exceed physical")
        return violations


def legacy_quantity_projection(quantity):
    if type(quantity) is not int or quantity < 0:
        raise ValueError("legacy quantity must be a nonnegative integer")
    return InventoryContractState(
        physical=quantity,
        assigned=min(quantity, 1),
        available=max(quantity - 1, 0),
        reserved=0,
    )


def apply_reservation(state, amount):
    if type(amount) is not int or amount < 0 or amount > state.available:
        raise ValueError("reservation exceeds available quantity")
    return InventoryContractState(
        physical=state.physical,
        assigned=state.assigned,
        available=state.available - amount,
        reserved=state.reserved + amount,
        outgoing_transit=state.outgoing_transit,
        incoming_transit=state.incoming_transit,
    )


def ship_reserved(state, amount):
    if type(amount) is not int or amount < 0 or amount > state.reserved:
        raise ValueError("shipment exceeds reserved quantity")
    return InventoryContractState(
        physical=state.physical - amount,
        assigned=state.assigned,
        available=state.available,
        reserved=state.reserved - amount,
        outgoing_transit=state.outgoing_transit + amount,
        incoming_transit=state.incoming_transit,
    )


def receive_incoming(state, amount, assign=False):
    if type(amount) is not int or amount < 0 or amount > state.incoming_transit:
        raise ValueError("receipt exceeds incoming transit")
    return InventoryContractState(
        physical=state.physical + amount,
        assigned=state.assigned + (amount if assign else 0),
        available=state.available + (0 if assign else amount),
        reserved=state.reserved,
        outgoing_transit=state.outgoing_transit,
        incoming_transit=state.incoming_transit - amount,
    )


def transit_pair_is_valid(outgoing_transit, incoming_transit):
    return (
        type(outgoing_transit) is int
        and type(incoming_transit) is int
        and outgoing_transit >= 0
        and incoming_transit >= 0
        and outgoing_transit == incoming_transit
    )


class InventoryContractV1TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        cls.reference_hash_before = sha256(REFERENCE_FIXTURE)

    def tearDown(self):
        self.assertEqual(self.production_hash_before, sha256(PRODUCTION_DB))
        self.assertEqual(self.reference_hash_before, sha256(REFERENCE_FIXTURE))

    def assert_contract(self, state):
        self.assertEqual([], state.violations())

    def test_documented_state_table_satisfies_contract(self):
        states = (
            InventoryContractState(0, 0, 0, 0, 0, 0),
            InventoryContractState(1, 1, 0, 0, 0, 0),
            InventoryContractState(2, 1, 1, 0, 0, 0),
            InventoryContractState(3, 1, 1, 1, 0, 0),
            InventoryContractState(2, 1, 1, 0, 1, 0),
            InventoryContractState(0, 0, 0, 0, 0, 1),
            InventoryContractState(3, 2, 1, 0, 0, 0),
        )

        for state in states:
            with self.subTest(state=state):
                self.assert_contract(state)

    def test_negative_quantities_are_contract_violations(self):
        names = [field.name for field in fields(InventoryContractState)]
        for name in names:
            values = {
                "physical": 0,
                "assigned": 0,
                "available": 0,
                "reserved": 0,
                "outgoing_transit": 0,
                "incoming_transit": 0,
            }
            values[name] = -1
            with self.subTest(name=name):
                self.assertIn(
                    "all quantities must be nonnegative",
                    InventoryContractState(**values).violations(),
                )

    def test_noninteger_and_boolean_quantities_are_contract_violations(self):
        for value in (1.5, "1", True, None):
            with self.subTest(value=value):
                state = InventoryContractState(value, 0, 0, 0)
                self.assertIn(
                    "all quantities must be integers",
                    state.violations(),
                )

    def test_physical_balance_excludes_double_counted_buckets(self):
        undercounted = InventoryContractState(3, 1, 1, 0)
        overcounted = InventoryContractState(2, 1, 1, 1)

        self.assertIn("physical balance must be exact", undercounted.violations())
        self.assertIn("physical balance must be exact", overcounted.violations())

    def test_available_never_exceeds_physical(self):
        state = InventoryContractState(1, 0, 2, 0)

        self.assertIn("available must not exceed physical", state.violations())

    def test_reservation_moves_only_available_quantity(self):
        initial = InventoryContractState(3, 1, 2, 0)
        reserved = apply_reservation(initial, 1)

        self.assertEqual(InventoryContractState(3, 1, 1, 1), reserved)
        self.assert_contract(reserved)
        with self.assertRaises(ValueError):
            apply_reservation(reserved, 2)

    def test_shipping_moves_reserved_out_of_physical_stock(self):
        reserved = InventoryContractState(3, 1, 1, 1)
        shipped = ship_reserved(reserved, 1)

        self.assertEqual(InventoryContractState(2, 1, 1, 0, 1, 0), shipped)
        self.assert_contract(shipped)
        with self.assertRaises(ValueError):
            ship_reserved(shipped, 1)

    def test_incoming_transit_is_not_physical_until_receipt(self):
        incoming = InventoryContractState(0, 0, 0, 0, 0, 1)

        self.assert_contract(incoming)
        received = receive_incoming(incoming, 1, assign=True)
        self.assertEqual(InventoryContractState(1, 1, 0, 0, 0, 0), received)
        self.assert_contract(received)

    def test_transit_mirror_is_equal_and_counted_once(self):
        sender_outgoing = 2
        receiver_incoming = 2
        physical_across_users = 7

        self.assertTrue(transit_pair_is_valid(sender_outgoing, receiver_incoming))
        self.assertFalse(transit_pair_is_valid(2, 1))
        self.assertFalse(transit_pair_is_valid(-1, -1))
        self.assertFalse(transit_pair_is_valid(1.0, 1))
        self.assertEqual(
            physical_across_users + sender_outgoing,
            physical_across_users + receiver_incoming,
        )
        self.assertNotEqual(
            physical_across_users + sender_outgoing,
            physical_across_users + sender_outgoing + receiver_incoming,
        )

    def test_legacy_quantity_projection_is_exact_for_tabular_examples(self):
        expected = {
            0: InventoryContractState(0, 0, 0, 0),
            1: InventoryContractState(1, 1, 0, 0),
            2: InventoryContractState(2, 1, 1, 0),
            5: InventoryContractState(5, 1, 4, 0),
        }

        for quantity, state in expected.items():
            with self.subTest(quantity=quantity):
                self.assertEqual(state, legacy_quantity_projection(quantity))
                self.assert_contract(state)

    def test_legacy_duplicates_equal_available_without_bindings(self):
        for quantity in range(0, 11):
            state = legacy_quantity_projection(quantity)
            duplicates = max(quantity - 1, 0)

            self.assertEqual(duplicates, state.available)
            self.assertEqual(duplicates, state.physical - state.assigned)

    def test_invalid_legacy_quantities_are_rejected_by_contract_projection(self):
        for quantity in (-1, 1.5, "1", True, None):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    legacy_quantity_projection(quantity)

    def test_s00_fixture_rows_match_legacy_compatibility_projection(self):
        with sqlite3.connect(REFERENCE_FIXTURE) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT user_id, album_id, sticker_code, quantity, duplicates
                FROM stickers
                """
            ).fetchall()

        self.assertGreater(len(rows), 0)
        for row in rows:
            with self.subTest(
                user_id=row["user_id"],
                album_id=row["album_id"],
                code=row["sticker_code"],
            ):
                self.assertGreaterEqual(row["quantity"], 1)
                state = legacy_quantity_projection(row["quantity"])
                self.assert_contract(state)
                self.assertEqual(state.available, row["duplicates"])

    def test_s00_fixture_contains_no_zero_or_negative_inventory_rows(self):
        with sqlite3.connect(REFERENCE_FIXTURE) as connection:
            invalid_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM stickers
                WHERE quantity <= 0 OR duplicates < 0
                """
            ).fetchone()[0]

        self.assertEqual(0, invalid_count)

    def test_legacy_schema_has_no_target_model_columns_or_migration(self):
        with sqlite3.connect(REFERENCE_FIXTURE) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(stickers)").fetchall()
            }

        self.assertEqual(
            {"id", "album_id", "sticker_code", "status", "duplicates", "quantity", "user_id"},
            columns,
        )
        self.assertTrue(
            {"physical", "assigned", "available", "reserved", "outgoing_transit", "incoming_transit"}.isdisjoint(columns)
        )


if __name__ == "__main__":
    unittest.main()
