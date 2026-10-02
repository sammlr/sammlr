import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from Scripts.bootstrap_database import bootstrap


class ReleaseBootstrapTests(unittest.TestCase):
    def test_empty_database_reaches_v20_without_users_and_rejects_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "new.db"
            bootstrap(database)
            with sqlite3.connect(database) as connection:
                self.assertEqual(20, connection.execute(
                    "SELECT MAX(version) FROM schema_migrations").fetchone()[0])
                for table in ("users", "user_albums", "stickers", "trade_requests"):
                    self.assertEqual(0, connection.execute(
                        f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                self.assertEqual(3, connection.execute(
                    "SELECT COUNT(*) FROM albums").fetchone()[0])
                self.assertEqual([("ok",)], connection.execute("PRAGMA integrity_check").fetchall())
                self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())
            digest = hashlib.sha256(database.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):
                bootstrap(database)
            self.assertEqual(digest, hashlib.sha256(database.read_bytes()).hexdigest())

    def test_existing_empty_file_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "existing.db"
            database.touch()
            with self.assertRaises(FileExistsError):
                bootstrap(database)
            self.assertEqual(b"", database.read_bytes())

    def test_symlink_target_is_never_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private.db"
            target.write_bytes(b"private-existing-data")
            link = Path(directory) / "alias.db"
            link.symlink_to(target)
            with self.assertRaises(FileExistsError):
                bootstrap(link)
            self.assertEqual(b"private-existing-data", target.read_bytes())

    def test_base_schema_matches_synthetic_legacy_fixture(self):
        root = Path(__file__).resolve().parents[1] / "App/Database"
        with sqlite3.connect(":memory:") as expected, sqlite3.connect(":memory:") as actual:
            expected.executescript((root / "sammlr_reference_s00.sql").read_text())
            actual.executescript((root / "base_schema.sql").read_text())
            query = "SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
            self.assertEqual(expected.execute(query).fetchall(), actual.execute(query).fetchall())
