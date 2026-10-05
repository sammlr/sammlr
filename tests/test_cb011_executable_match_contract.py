import atexit
import hashlib
import json
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
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb011-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import load_migrations, migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.executable_trade_matches import ExecutableTradeMatchService  # noqa: E402
from services.smart_trade_requests import (  # noqa: E402
    SMART_REQUEST_MARKER,
    SmartTradeRequestCode,
    SmartTradeRequestService,
)
from services.top_match_optimization import (  # noqa: E402
    OPTIMIZATION_VERSION,
    TopMatchOptimizationService,
)
from services.trade_coverage import TradeCoverageService  # noqa: E402


class CB011ExecutableMatchContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-cb011-")
        self.db_path = Path(self.temp_dir.name) / "matches.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            for table in (
                "trade_receipt_report_positions", "trade_receipt_reports",
                "trade_receipt_status", "trade_shipping_status",
                "trade_reservations", "trade_events", "trade_positions",
                "trades", "trade_requests", "notifications", "blocks",
                "stickers",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.executemany(
                "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, 'vfl')",
                ((1,), (2,), (3,)),
            )
            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=1 "
                "WHERE user_id IN (1,2,3) AND album_id='vfl'"
            )
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        self.login_as(1)

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def login_as(self, user_id):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id

    def set_inventory(self, user_id, quantities):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM stickers WHERE user_id=? AND album_id='vfl'",
                (user_id,),
            )
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, 'vfl', ?, 'owned', ?, ?)
                """,
                (
                    (user_id, code, max(quantity - 1, 0), quantity)
                    for code, quantity in quantities.items()
                ),
            )

    def matches(self, partner_ids=(2, 3)):
        with self.connection() as connection:
            inventory = InventoryReadService(connection)
            return ExecutableTradeMatchService(
                TradeCoverageService(inventory)
            ).matches(
                1, "vfl", tuple(str(code) for code in range(1, 21)), partner_ids
            )

    def optimize(self, partner_ids=(2, 3)):
        with self.connection() as connection:
            return TopMatchOptimizationService(
                InventoryReadService(connection)
            ).optimize(
                1, "vfl", tuple(str(code) for code in range(1, 21)), partner_ids
            )

    def seed_ranked_matches(self):
        self.set_inventory(1, {"1": 2, "2": 2, "3": 2})
        self.set_inventory(2, {"10": 2, "11": 2})
        self.set_inventory(3, {"12": 2})

    def reserve(self, user_id, code):
        with self.connection() as connection:
            request_id = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', ?, 3, ?, '["12"]', 'accepted')
                """,
                (user_id, json.dumps([code])),
            ).lastrowid
            trade_id = connection.execute(
                """
                INSERT INTO trades
                    (legacy_trade_request_id, requester_user_id, partner_user_id,
                     lifecycle_state)
                VALUES (?, ?, 3, 'accepted')
                """,
                (request_id, user_id),
            ).lastrowid
            position_id = connection.execute(
                """
                INSERT INTO trade_positions
                    (trade_id, from_user_id, to_user_id, album_id,
                     sticker_code, quantity)
                VALUES (?, ?, 3, 'vfl', ?, 1)
                """,
                (trade_id, user_id, code),
            ).lastrowid
            connection.execute(
                """
                INSERT INTO trade_reservations
                    (trade_id, trade_position_id, user_id, album_id,
                     sticker_code, quantity, state)
                VALUES (?, ?, ?, 'vfl', ?, 1, 'active')
                """,
                (trade_id, position_id, user_id, code),
            )

    def test_larger_bilateral_quantity_is_first_and_one_sided_is_excluded(self):
        self.seed_ranked_matches()
        self.set_inventory(3, {"12": 2, "13": 2})

        matches = self.matches()

        self.assertEqual((2, 3), tuple(match.partner_user_id for match in matches))
        self.assertEqual((2, 2), tuple(match.executable_quantity for match in matches))
        self.set_inventory(3, {"12": 2, "13": 2, "1": 1, "2": 1, "3": 1})
        self.assertEqual((2,), tuple(match.partner_user_id for match in self.matches()))

    def test_better_match_precedes_weaker_and_tie_uses_partner_id(self):
        self.seed_ranked_matches()
        matches = self.matches((3, 2, 3))
        self.assertEqual((2, 3), tuple(match.partner_user_id for match in matches))
        self.assertEqual((2, 1), tuple(match.executable_quantity for match in matches))

        self.set_inventory(2, {"10": 2})
        tied = self.matches((3, 2))
        self.assertEqual((2, 3), tuple(match.partner_user_id for match in tied))

    def test_reservations_and_conflicts_use_effective_availability(self):
        self.seed_ranked_matches()
        self.reserve(1, "1")
        self.reserve(1, "2")

        matches = self.matches()
        result = self.optimize()

        self.assertEqual(1, matches[0].executable_quantity)
        used = [
            position.sticker_code
            for package in result.packages
            for position in package.give_positions
        ]
        self.assertNotIn("1", used)
        self.assertNotIn("2", used)
        self.assertEqual(["3"], used)

    def test_block_wins_but_private_profile_does_not_disable_trade_pool(self):
        self.seed_ranked_matches()
        with self.connection() as connection:
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=2"
            )
        self.assertEqual(2, self.matches()[0].partner_user_id)

        with self.connection() as connection:
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (1, 2)"
            )
        self.assertEqual((3,), tuple(match.partner_user_id for match in self.matches()))

    def test_trade_pool_opt_out_excludes_match_without_profile_coupling(self):
        self.seed_ranked_matches()
        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=0 "
                "WHERE user_id=2 AND album_id='vfl'"
            )
        self.assertEqual((3,), tuple(match.partner_user_id for match in self.matches()))

    def test_optimizer_and_album_page_use_the_same_stable_priority(self):
        self.seed_ranked_matches()
        result = self.optimize((3, 2, 3))
        self.assertEqual("CB011-v1", OPTIMIZATION_VERSION)
        self.assertEqual((2, 3), tuple(
            package.partner_user_id for package in result.packages
        ))
        self.assertEqual(result.result_id, self.optimize((2, 3)).result_id)

        html = self.client.get("/album/vfl/trades?tab=partners").get_data(as_text=True)
        self.assertLess(html.index("fixture_user_2"), html.index("fixture_user_3"))
        self.assertIn("Direkter Tausch möglich · 2", html)

    def test_generous_unequal_manual_request_remains_allowed_and_exact(self):
        self.set_inventory(1, {"1": 2, "2": 2})
        self.set_inventory(2, {"10": 2})

        response = self.client.post(
            "/album/vfl/trade/2/request",
            data={"give_codes": ["1", "2"], "get_codes": ["10"]},
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM trade_requests ORDER BY id DESC LIMIT 1"
            ).fetchone()
        self.assertEqual(["1", "2"], json.loads(row["give_codes"]))
        self.assertEqual(["10"], json.loads(row["get_codes"]))
        self.assertEqual(0, row["from_confirmed"])

    def test_smart_request_is_immutable_and_acceptance_race_fails_closed(self):
        self.seed_ranked_matches()
        page = self.client.get("/album/vfl/smart-trades").get_data(as_text=True)
        result_id = re.search(
            r'name="result_id" value="([0-9a-f]+)"', page
        ).group(1)
        response = self.client.post(
            "/album/vfl/smart-trades/2/request", data={"result_id": result_id}
        )
        self.assertEqual(302, response.status_code)
        with self.connection() as connection:
            original = connection.execute(
                "SELECT * FROM trade_requests ORDER BY id DESC LIMIT 1"
            ).fetchone()
            original_give = original["give_codes"]
            original_get = original["get_codes"]
            trade_id = original["id"]
        self.assertEqual(SMART_REQUEST_MARKER, original["from_confirmed"])

        self.set_inventory(2, {"10": 2})
        self.login_as(2)
        self.client.post(f"/trade/{trade_id}/accept")
        with self.connection() as connection:
            after = connection.execute(
                "SELECT * FROM trade_requests WHERE id=?", (trade_id,)
            ).fetchone()
            reservations = connection.execute(
                "SELECT COUNT(*) FROM trade_reservations"
            ).fetchone()[0]
        self.assertEqual(original_give, after["give_codes"])
        self.assertEqual(original_get, after["get_codes"])
        self.assertEqual("open", after["status"])
        self.assertEqual(0, reservations)

    def test_smart_request_retry_keeps_the_confirmed_payload_exact(self):
        self.seed_ranked_matches()
        page = self.client.get("/album/vfl/smart-trades").get_data(as_text=True)
        result_id = re.search(
            r'name="result_id" value="([0-9a-f]+)"', page
        ).group(1)
        path = "/album/vfl/smart-trades/2/request"

        first = self.client.post(path, data={"result_id": result_id})
        second = self.client.post(path, data={"result_id": result_id})

        self.assertEqual((302, 302), (first.status_code, second.status_code))
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT give_codes, get_codes, from_confirmed
                FROM trade_requests
                WHERE from_user_id=1 AND to_user_id=2
                ORDER BY id
                """
            ).fetchall()
        self.assertEqual(2, len(rows))
        self.assertEqual(rows[0]["give_codes"], rows[1]["give_codes"])
        self.assertEqual(rows[0]["get_codes"], rows[1]["get_codes"])
        self.assertEqual(
            (SMART_REQUEST_MARKER, SMART_REQUEST_MARKER),
            tuple(row["from_confirmed"] for row in rows),
        )

    def test_no_migration_and_cb008_to_cb010_sources_untouched(self):
        self.assertEqual(22, max(item.version for item in load_migrations()))
        with self.connection() as connection:
            versions = tuple(row[0] for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ))
        self.assertEqual(tuple(range(1, 19)), versions)


if __name__ == "__main__":
    unittest.main()
