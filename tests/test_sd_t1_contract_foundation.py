"""SD-T1 storage only; synthetic fixtures, no new user-facing trade flow."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from App.Database.migration_runner import current_version, migrate, rollback
from App.services.trade_contracts import (
    LEGACY_CONTRACT, SMARTDEAL_V1_CONTRACT,
    is_smartdeal_v1_request, request_contract_type,
)
from Scripts.bootstrap_database import bootstrap

ROOT = Path(__file__).resolve().parents[1]


class ContractFoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="sdt1-")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "fixture.db"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((ROOT / "App/Database/sammlr_reference_s00.sql").read_text())
        migrate(self.db, 20)
        self.db.execute("PRAGMA foreign_keys=ON")

    def insert_request(self, marker=0, status="open", contract=None):
        columns = "album_id,from_user_id,to_user_id,give_codes,get_codes,status,from_confirmed"
        values = ["vfl", 1, 2, '["001"]', '["002"]', status, marker]
        if contract is not None:
            columns += ",contract_type"
            values.append(contract)
        return self.db.execute(
            f"INSERT INTO trade_requests ({columns}) VALUES ({','.join('?' for _ in values)})",
            values,
        ).lastrowid

    def row(self, identity):
        return self.db.execute("SELECT * FROM trade_requests WHERE id=?", (identity,)).fetchone()

    def check_integrity(self):
        self.assertEqual([("ok",)], [tuple(r) for r in self.db.execute("PRAGMA integrity_check")])
        self.assertEqual([], self.db.execute("PRAGMA foreign_key_check").fetchall())

    def test_existing_manual_request_stays_legacy(self):
        identity = self.insert_request()
        before = dict(self.row(identity))
        migrate(self.db, 21)
        row = self.row(identity)
        self.assertEqual(LEGACY_CONTRACT, request_contract_type(row))
        self.assertEqual(before, {k: row[k] for k in before})
        self.assertIsNone(row["binding_created_at"])
        self.assertIsNone(row["accepted_at"])

    def test_historical_smart_marker_does_not_become_v1(self):
        identity = self.insert_request(marker=-22)
        migrate(self.db, 21)
        self.assertFalse(is_smartdeal_v1_request(self.row(identity)))
        self.assertEqual(-22, self.row(identity)["from_confirmed"])

    def test_accepted_and_completed_legacy_rows_keep_their_contract(self):
        ids = [self.insert_request(status=s) for s in ("accepted", "completed")]
        migrate(self.db, 21)
        self.assertEqual(["accepted", "completed"], [self.row(i)["status"] for i in ids])
        self.assertTrue(all(request_contract_type(self.row(i)) == LEGACY_CONTRACT for i in ids))

    def test_explicit_v1_survives_database_close_and_reopen(self):
        migrate(self.db, 21)
        identity = self.insert_request(contract=SMARTDEAL_V1_CONTRACT)
        self.db.commit()
        with sqlite3.connect(self.path) as reopened:
            reopened.row_factory = sqlite3.Row
            row = reopened.execute("SELECT * FROM trade_requests WHERE id=?", (identity,)).fetchone()
            self.assertTrue(is_smartdeal_v1_request(row))
            self.assertEqual("open", row["status"])

    def test_old_row_without_column_has_safe_fallback(self):
        self.assertEqual(LEGACY_CONTRACT, request_contract_type(self.row(self.insert_request(-22))))
        self.assertFalse(is_smartdeal_v1_request({"from_confirmed": -22, "status": "accepted"}))
        self.assertFalse(is_smartdeal_v1_request(None))

    def test_explicit_unknown_or_null_contract_is_not_guessed(self):
        for value in (None, "", "smart", "manual", "smartdeal_v2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                request_contract_type({"contract_type": value})

    def test_database_rejects_unknown_and_null_contract(self):
        migrate(self.db, 21)
        for value in (None, "smart", "smartdeal_v2"):
            with self.subTest(value=value), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute("INSERT INTO trade_requests(contract_type) VALUES (?)", (value,))

    def test_omitted_contract_on_new_legacy_write_defaults_to_legacy(self):
        migrate(self.db, 21)
        self.assertFalse(is_smartdeal_v1_request(self.row(self.insert_request(-22))))

    def test_existing_contract_cannot_be_reclassified(self):
        migrate(self.db, 21)
        for original, replacement in ((LEGACY_CONTRACT, SMARTDEAL_V1_CONTRACT),
                                      (SMARTDEAL_V1_CONTRACT, LEGACY_CONTRACT)):
            identity = self.insert_request(contract=original)
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute("UPDATE trade_requests SET contract_type=? WHERE id=?", (replacement, identity))
            self.assertEqual(original, request_contract_type(self.row(identity)))

    def test_time_storage_is_distinct_persistent_and_write_once(self):
        migrate(self.db, 21)
        identity = self.insert_request(contract=SMARTDEAL_V1_CONTRACT)
        for column, instant in (("binding_created_at", "2026-09-10 10:00:00"),
                                ("accepted_at", "2026-09-10 11:00:00")):
            self.db.execute(f"UPDATE trade_requests SET {column}=? WHERE id=?", (instant, identity))
            self.db.execute(f"UPDATE trade_requests SET {column}=? WHERE id=?", (instant, identity))
            for replacement in (None, "2026-09-10 12:00:00"):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.db.execute(f"UPDATE trade_requests SET {column}=? WHERE id=?", (replacement, identity))
        self.db.commit()
        with sqlite3.connect(self.path) as reopened:
            self.assertEqual(("2026-09-10 10:00:00", "2026-09-10 11:00:00", "open"),
                reopened.execute("SELECT binding_created_at,accepted_at,status FROM trade_requests WHERE id=?", (identity,)).fetchone())
        self.assertEqual(0, self.db.execute("SELECT COUNT(*) FROM trade_reservations").fetchone()[0])

    def test_upgrade_preserves_all_existing_table_data(self):
        self.insert_request(-22)
        tables = [r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'schema_migrations'")]
        before = {t: [tuple(r) for r in self.db.execute(f'SELECT * FROM "{t}" ORDER BY rowid')] for t in tables}
        columns = {t: [r[1] for r in self.db.execute(f'PRAGMA table_info("{t}")')] for t in tables}
        migrate(self.db, 21)
        for table in tables:
            names = ','.join('"'+c+'"' for c in columns[table])
            self.assertEqual(before[table], [tuple(r) for r in self.db.execute(f'SELECT {names} FROM "{table}" ORDER BY rowid')], table)
        self.assertEqual(21, current_version(self.db))
        self.check_integrity()

    def test_migration_is_idempotent(self):
        migrate(self.db, 21)
        self.assertEqual((), migrate(self.db, 21))
        self.check_integrity()

    def test_release_bootstrap_then_explicit_v21_upgrade(self):
        path = Path(self.directory.name) / "fresh.db"
        bootstrap(path)
        with sqlite3.connect(path) as connection:
            self.assertEqual(20, current_version(connection))
            migrate(connection, 21)
            self.assertEqual(21, current_version(connection))
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])
            self.assertEqual([("ok",)], connection.execute("PRAGMA integrity_check").fetchall())
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())

    def test_backout_without_v1_restores_legacy_schema_and_rows(self):
        identity = self.insert_request(-22)
        before = dict(self.row(identity))
        migrate(self.db, 21)
        rollback(self.db, 20)
        self.assertEqual(before, dict(self.row(identity)))
        self.check_integrity()

    def test_backout_with_v1_refuses_data_loss(self):
        migrate(self.db, 21)
        identity = self.insert_request(contract=SMARTDEAL_V1_CONTRACT)
        with self.assertRaises(sqlite3.IntegrityError):
            rollback(self.db, 20)
        self.assertEqual(21, current_version(self.db))
        self.assertTrue(is_smartdeal_v1_request(self.row(identity)))
        self.check_integrity()

    def test_fresh_schema_can_migrate_directly_to_v21(self):
        with sqlite3.connect(":memory:") as connection:
            connection.executescript((ROOT / "App/Database/base_schema.sql").read_text())
            connection.executescript((ROOT / "App/Database/catalog_seed.sql").read_text())
            connection.execute("PRAGMA foreign_keys=ON")
            self.assertEqual(tuple(range(1, 22)), migrate(connection, 21))
            self.assertEqual([("ok",)], connection.execute("PRAGMA integrity_check").fetchall())
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())

    def test_legacy_lifecycle_on_v21_still_books_only_at_ship_and_receipt(self):
        import sys
        sys.path.insert(0, str(ROOT / "App"))
        from services.trade_reservations import TradeReservationService
        from services.trade_shipping import TradeShippingService
        from services.trade_receipt import TradeReceiptService
        migrate(self.db, 21)
        identity = self.insert_request()
        self.db.execute("UPDATE trade_requests SET give_codes=?,get_codes=? WHERE id=?", ('["1"]', '["3"]', identity))
        self.db.commit()
        def inventory():
            return [tuple(r) for r in self.db.execute("SELECT user_id,album_id,sticker_code,quantity FROM stickers ORDER BY user_id,album_id,sticker_code")]
        before = inventory()
        self.assertEqual(0, self.db.execute("SELECT COUNT(*) FROM trade_reservations").fetchone()[0])
        result = TradeReservationService(self.db).accept(identity, 2)
        self.assertTrue(result.accepted, result)
        self.assertEqual(before, inventory())
        self.assertEqual(2, self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        for actor in (1, 2):
            result = TradeShippingService(self.db).ship(identity, actor)
            self.assertTrue(result.shipped, result)
            after_ship = inventory()
            self.assertTrue(TradeShippingService(self.db).ship(identity, actor).idempotent)
            self.assertEqual(after_ship, inventory())
        self.assertNotEqual(before, inventory())
        for actor in (1, 2):
            result = TradeReceiptService(self.db).receive(identity, actor)
            self.assertTrue(result.received, result)
            after_receipt = inventory()
            self.assertTrue(TradeReceiptService(self.db).receive(identity, actor).idempotent)
            self.assertEqual(after_receipt, inventory())
        row = self.row(identity)
        self.assertEqual("completed", row["status"])
        self.assertFalse(is_smartdeal_v1_request(row))
        self.assertIsNone(row["binding_created_at"])
        self.assertIsNone(row["accepted_at"])
        self.check_integrity()

    def test_legacy_smart_expiry_remains_48_hours_on_v21(self):
        import sys
        from datetime import timedelta
        sys.path.insert(0, str(ROOT / "App"))
        from services.smart_trade_requests import SmartTradeRequestService
        migrate(self.db, 21)
        row = self.row(self.insert_request(-22))
        self.assertEqual(timedelta(hours=48), SmartTradeRequestService.expires_at(row)
                         - SmartTradeRequestService._parse_created_at(row["created_at"]))
        self.assertFalse(is_smartdeal_v1_request(row))
