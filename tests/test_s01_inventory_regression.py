import atexit
import hashlib
import os
from pathlib import Path
import re
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


# webapp initializes its configured database at import time. Point that import
# at a disposable S00 copy before loading any application module.
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s01-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


if os.environ.get("SAMMLR_S01_MUTATE_QUANTITY") == "1":
    _reference_change_sticker_quantity = webapp.change_sticker_quantity

    def _mutated_change_sticker_quantity(
        connection, user_id, album_id, code, delta
    ):
        # S01 mutation proof only: an in-memory replacement for this process.
        # It deliberately applies one extra item and never edits webapp.py.
        return _reference_change_sticker_quantity(
            connection, user_id, album_id, code, delta + 1
        )

    webapp.change_sticker_quantity = _mutated_change_sticker_quantity


class InventoryRegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s01-test-")
        self.test_db = Path(self.test_dir.name) / "inventory.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S01 test.",
        )
        self.test_dir.cleanup()

    def db_row(self, code, user_id=1, album_id="vfl"):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM stickers
                WHERE user_id=? AND album_id=? AND sticker_code=?
                """,
                (user_id, album_id, code),
            ).fetchone()

    def assert_sticker(self, code, quantity, duplicates):
        row = self.db_row(code)
        self.assertIsNotNone(row)
        self.assertEqual(quantity, row["quantity"])
        self.assertEqual(duplicates, row["duplicates"])
        self.assertEqual(max(quantity - 1, 0), row["duplicates"])

    def wall_classes(self, response_text, code):
        match = re.search(
            rf'<a class="([^"]*)" data-code="{re.escape(code)}"',
            response_text,
        )
        self.assertIsNotNone(match, f"Sticker {code} fehlt in der Stickerwall.")
        return set(match.group(1).split())

    def test_add_existing_sticker_updates_quantity_and_duplicates(self):
        response = self.client.get("/add/vfl/1")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=4, duplicates=3)

    def test_add_missing_sticker_creates_first_copy(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.get("/add/vfl/3")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("3", quantity=1, duplicates=0)

    def test_remove_existing_sticker_updates_quantity_and_duplicates(self):
        response = self.client.get("/remove/vfl/1")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=2, duplicates=1)

    def test_remove_last_copy_reaches_zero_by_deleting_row(self):
        self.assert_sticker("2", quantity=1, duplicates=0)

        response = self.client.get("/remove/vfl/2")

        self.assertEqual(302, response.status_code)
        self.assertIsNone(self.db_row("2"))

    def test_remove_missing_sticker_does_not_create_negative_stock(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.get("/remove/vfl/3")

        self.assertEqual(302, response.status_code)
        self.assertIsNone(self.db_row("3"))

    def test_inline_plus_updates_db_and_response_contract(self):
        response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(4, payload["quantity"])
        self.assertEqual(3, payload["duplicates"])
        self.assertEqual("duplicate", payload["statusClass"])
        self.assert_sticker("1", quantity=4, duplicates=3)

    def test_inline_plus_creates_missing_sticker(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.post(
            "/album/vfl/sticker/3/quantity",
            data={"delta": "1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(1, payload["quantity"])
        self.assertEqual(0, payload["duplicates"])
        self.assertEqual("owned", payload["statusClass"])
        self.assert_sticker("3", quantity=1, duplicates=0)

    def test_inline_minus_updates_db_and_response_contract(self):
        response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "-1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(2, payload["quantity"])
        self.assertEqual(1, payload["duplicates"])
        self.assert_sticker("1", quantity=2, duplicates=1)

    def test_inline_minus_never_goes_below_zero(self):
        first_response = self.client.post(
            "/album/vfl/sticker/2/quantity",
            data={"delta": "-1"},
        )
        second_response = self.client.post(
            "/album/vfl/sticker/2/quantity",
            data={"delta": "-99"},
        )

        self.assertEqual(200, first_response.status_code)
        self.assertEqual(0, first_response.get_json()["quantity"])
        self.assertEqual(200, second_response.status_code)
        self.assertEqual(0, second_response.get_json()["quantity"])
        self.assertEqual(0, second_response.get_json()["duplicates"])
        self.assertIsNone(self.db_row("2"))

    def test_inline_rejects_zero_and_non_numeric_delta_without_db_change(self):
        zero_response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "0"},
        )
        text_response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "not-a-number"},
        )

        self.assertEqual(400, zero_response.status_code)
        self.assertEqual(400, text_response.status_code)
        self.assert_sticker("1", quantity=3, duplicates=2)

    def test_stickerwall_filter_predicate_covers_all_states(self):
        _, by_code, _, _, _, _ = webapp.lade_album_for_user("vfl", 1)

        self.assertTrue(webapp.filter_ok("missing", "3", by_code))
        self.assertFalse(webapp.filter_ok("missing", "2", by_code))
        self.assertTrue(webapp.filter_ok("owned", "2", by_code))
        self.assertFalse(webapp.filter_ok("owned", "3", by_code))
        self.assertTrue(webapp.filter_ok("duplicate", "1", by_code))
        self.assertFalse(webapp.filter_ok("duplicate", "2", by_code))
        self.assertTrue(webapp.filter_ok("all", "1", by_code))
        self.assertTrue(webapp.filter_ok("all", "3", by_code))

    def test_stickerwall_routes_hide_nonmatching_cards(self):
        missing_html = self.client.get(
            "/album/vfl?filter=missing"
        ).get_data(as_text=True)
        owned_html = self.client.get(
            "/album/vfl?filter=owned"
        ).get_data(as_text=True)
        duplicate_html = self.client.get(
            "/album/vfl?filter=duplicate"
        ).get_data(as_text=True)

        self.assertNotIn("filter-hidden", self.wall_classes(missing_html, "3"))
        self.assertIn("filter-hidden", self.wall_classes(missing_html, "1"))
        self.assertNotIn("filter-hidden", self.wall_classes(owned_html, "2"))
        self.assertIn("filter-hidden", self.wall_classes(owned_html, "3"))
        self.assertNotIn("filter-hidden", self.wall_classes(duplicate_html, "1"))
        self.assertIn("filter-hidden", self.wall_classes(duplicate_html, "2"))

    def test_album_progress_counts_unique_owned_codes_not_quantity(self):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(
                "UPDATE albums SET total=4 WHERE id='vfl'"
            )
            connection.commit()

        _, by_code, collected, duplicates, percent, total = (
            webapp.lade_album_for_user("vfl", 1)
        )
        self.assertEqual(3, collected)
        self.assertEqual(2, duplicates)
        self.assertEqual(75, percent)
        self.assertEqual(4, total)
        self.assertEqual(75, webapp.sticker_progress_percent(
            ["1", "2", "3", "4"], by_code
        ))

        response = self.client.post(
            "/album/vfl/sticker/3/quantity",
            data={"delta": "1"},
        )
        payload = response.get_json()
        self.assertEqual(4, payload["album"]["collected"])
        self.assertEqual(100, payload["album"]["percent"])

    def test_undo_restores_add_inventory_change(self):
        self.client.get("/add/vfl/1")
        self.assert_sticker("1", quantity=4, duplicates=3)

        response = self.client.get("/undo")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=3, duplicates=2)
        with self.client.session_transaction() as session:
            self.assertNotIn("last_action", session)

    def test_undo_restores_remove_inventory_change(self):
        self.client.get("/remove/vfl/2")
        self.assertIsNone(self.db_row("2"))

        response = self.client.get("/undo")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("2", quantity=1, duplicates=0)
        with self.client.session_transaction() as session:
            self.assertNotIn("last_action", session)

    def test_existing_sticker_code_resolution_is_unchanged(self):
        self.assertEqual("1", webapp.resolve_code("vfl", "1"))
        self.assertEqual("250", webapp.resolve_code("vfl", "250"))
        self.assertIsNone(webapp.resolve_code("vfl", "0"))
        self.assertIsNone(webapp.resolve_code("vfl", "251"))
        self.assertIsNone(webapp.resolve_code("vfl", "not-a-code"))


if __name__ == "__main__":
    unittest.main()
