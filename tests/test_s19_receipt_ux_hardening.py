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
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s19-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from services.inventory import InventoryReadService  # noqa: E402
from services.trade_problems import problem_reports_for_trade  # noqa: E402


class ReceiptUxHardeningRouteRegressionTestCase(unittest.TestCase):
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
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s19-")
        self.test_db = Path(self.test_dir.name) / "receipt-ux.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        with self.connection() as connection:
            self.assertEqual((1, 2, 3, 4, 5), migrate(connection, target_version=5))
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

    def create_accepted_trade(self, give_codes):
        with self.connection() as connection:
            for code in set(give_codes):
                updated = connection.execute(
                    """
                    UPDATE stickers SET quantity=10, duplicates=9
                    WHERE user_id=1 AND album_id='vfl' AND sticker_code=?
                    """,
                    (code,),
                )
                if updated.rowcount == 0:
                    connection.execute(
                        """
                        INSERT INTO stickers
                            (user_id, album_id, sticker_code, status,
                             duplicates, quantity)
                        VALUES (1, 'vfl', ?, 'owned', 9, 10)
                        """,
                        (code,),
                    )
            connection.execute(
                "UPDATE stickers SET quantity=10, duplicates=9 "
                "WHERE user_id=2 AND album_id='vfl' AND sticker_code='3'"
            )
            cursor = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id,
                     give_codes, get_codes, status)
                VALUES ('vfl', 1, 2, ?, '["3"]', 'open')
                """,
                (json.dumps(give_codes),),
            )
            trade_id = cursor.lastrowid
        self.login_as(2)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/accept").status_code)
        self.login_as(1)
        self.assertEqual(302, self.client.post(f"/trade/{trade_id}/ship").status_code)
        self.login_as(2)
        return trade_id

    def positions(self, trade_id):
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT p.id, p.sticker_code, p.quantity
                FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=2
                ORDER BY p.id
                """,
                (trade_id,),
            ).fetchall()

    def snapshot(self, trade_id):
        positions = self.positions(trade_id)
        with self.connection() as connection:
            inventory = InventoryReadService(connection).album(2, "vfl")
            values = {}
            for position in positions:
                row = connection.execute(
                    """
                    SELECT quantity, duplicates FROM stickers
                    WHERE user_id=2 AND album_id='vfl' AND sticker_code=?
                    """,
                    (position["sticker_code"],),
                ).fetchone()
                availability = inventory.availability(position["sticker_code"])
                values[position["sticker_code"]] = {
                    "quantity": row["quantity"] if row else 0,
                    "duplicates": row["duplicates"] if row else 0,
                    "physical": availability.physical,
                    "assigned": availability.assigned,
                    "available": availability.available,
                    "incoming_transit": availability.incoming_transit,
                }
            status = connection.execute(
                """
                SELECT r.status AS legacy_status, t.lifecycle_state
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                WHERE r.id=?
                """,
                (trade_id,),
            ).fetchone()
        return {
            "inventory": values,
            "legacy_status": status["legacy_status"],
            "lifecycle_state": status["lifecycle_state"],
        }

    def reports(self, trade_id):
        with self.connection() as connection:
            return problem_reports_for_trade(connection, trade_id)

    def wall_slot(self, html, code):
        match = re.search(
            rf'<a class="slot ([^"]*)"[^>]* data-code="{re.escape(code)}" '
            rf'([^>]*)>(.*?)</a>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match, f"Stickerkarte {code} fehlt")
        return match.group(1), match.group(2), match.group(3)

    def assert_route_case(
        self,
        give_codes,
        correct_quantities,
        problem_types,
        shipment_lost=False,
    ):
        trade_id = self.create_accepted_trade(give_codes)
        positions = self.positions(trade_id)
        self.assertEqual(len(correct_quantities), len(positions))
        before = self.snapshot(trade_id)
        form = {}
        for position, quantity, problem_type in zip(
            positions, correct_quantities, problem_types
        ):
            form[f"received_{position['id']}"] = str(quantity)
            form[f"problem_{position['id']}"] = problem_type or ""
        if shipment_lost:
            form["shipment_lost"] = "1"

        first = self.client.post(f"/trade/{trade_id}/problem", data=form)
        self.assertIn("Problem%20und%20erhaltene%20Mengen%20gespeichert", first.location)
        after = self.snapshot(trade_id)
        reports = self.reports(trade_id)
        self.assertEqual(1, len(reports))
        self.assertEqual("open", reports[0].state)
        self.assertEqual("accepted", after["legacy_status"])
        self.assertEqual("problem_open", after["lifecycle_state"])

        for position, correct, problem_type, report_position in zip(
            positions, correct_quantities, problem_types, reports[0].positions
        ):
            code = position["sticker_code"]
            expected = position["quantity"]
            effective_type = "shipment_lost" if shipment_lost else problem_type
            effective_correct = 0 if shipment_lost else correct
            self.assertEqual(
                before["inventory"][code]["quantity"] + effective_correct,
                after["inventory"][code]["quantity"],
            )
            self.assertEqual(
                before["inventory"][code]["physical"] + effective_correct,
                after["inventory"][code]["physical"],
            )
            self.assertEqual(
                expected - effective_correct,
                after["inventory"][code]["incoming_transit"],
            )
            self.assertEqual(after["inventory"][code]["quantity"], after["inventory"][code]["physical"])
            self.assertEqual(min(after["inventory"][code]["physical"], 1), after["inventory"][code]["assigned"])
            self.assertEqual(max(after["inventory"][code]["physical"] - 1, 0), after["inventory"][code]["available"])
            self.assertEqual(expected, report_position.expected_quantity)
            self.assertEqual(effective_correct, report_position.initial_received_quantity)
            self.assertEqual(expected - effective_correct, report_position.open_quantity)
            self.assertEqual(effective_type, report_position.problem_type)

        retry = self.client.post(f"/trade/{trade_id}/problem", data=form)
        self.assertIn("Identische%20Meldung%20bereits%20verarbeitet", retry.location)
        self.assertEqual(after, self.snapshot(trade_id))
        self.assertEqual(reports, self.reports(trade_id))

        detail = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Die fehlende Restmenge ist jetzt physisch angekommen", detail)
        self.assertIn('name="confirm_physical_arrival" value="1"', detail)
        self.assertIn("Nachlieferung als angekommen bestätigen", detail)

        unconfirmed = self.client.post(f"/trade/{trade_id}/problem/resolve")
        self.assertIn("ausdr%C3%BCcklich%20best%C3%A4tigen", unconfirmed.location)
        self.assertEqual(after, self.snapshot(trade_id))
        self.assertEqual("open", self.reports(trade_id)[0].state)

        resolved = self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        self.assertIn("Problem%20aufgel%C3%B6st", resolved.location)
        after_resolution = self.snapshot(trade_id)
        resolved_report = self.reports(trade_id)[0]
        self.assertEqual("resolved", resolved_report.state)
        self.assertEqual("accepted", after_resolution["legacy_status"])
        self.assertEqual("partially_received", after_resolution["lifecycle_state"])

        for position, correct, report_position in zip(
            positions, correct_quantities, resolved_report.positions
        ):
            code = position["sticker_code"]
            expected = position["quantity"]
            effective_correct = 0 if shipment_lost else correct
            self.assertEqual(
                before["inventory"][code]["quantity"] + expected,
                after_resolution["inventory"][code]["quantity"],
            )
            self.assertEqual(0, after_resolution["inventory"][code]["incoming_transit"])
            self.assertEqual(effective_correct, report_position.initial_received_quantity)
            self.assertEqual(expected - effective_correct, report_position.resolution_received_quantity)
            self.assertEqual(0, report_position.open_quantity)

        resolution_retry = self.client.post(
            f"/trade/{trade_id}/problem/resolve",
            data={"confirm_physical_arrival": "1"},
        )
        self.assertIn("Problem%20bereits%20aufgel%C3%B6st", resolution_retry.location)
        self.assertEqual(after_resolution, self.snapshot(trade_id))
        self.assertEqual(resolved_report, self.reports(trade_id)[0])
        return trade_id

    def test_missing_route_inventory_transit_report_retry_and_resolution(self):
        self.assert_route_case(["1"], [0], ["missing"])

    def test_wrong_sticker_route_inventory_transit_report_retry_and_resolution(self):
        self.assert_route_case(["1"], [0], ["wrong_sticker"])

    def test_damaged_route_inventory_transit_report_retry_and_resolution(self):
        self.assert_route_case(["1"], [0], ["damaged"])

    def test_shipment_lost_route_covers_every_expected_position(self):
        self.assert_route_case(
            ["1", "2"], [1, 1], [None, None], shipment_lost=True
        )

    def test_mixed_delivery_books_only_full_position_then_resolves_remainder(self):
        self.assert_route_case(["1", "2"], [1, 0], [None, "missing"])

    def test_deal_view_labels_contract_as_expected_not_received_inventory(self):
        trade_id = self.create_accepted_trade(["1"])
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("Erwartete Lieferung: 1 Sticker", html)
        self.assertIn("Vereinbart abzugeben: 1 Sticker", html)
        self.assertNotIn("<h2>Du bekommst", html)
        self.assertNotIn("Du bekommst: <strong>", html)

    def test_problem_history_separates_initial_receipt_and_later_delivery(self):
        trade_id = self.assert_route_case(["1"], [0], ["missing"])
        html = self.client.get(f"/trades/{trade_id}").get_data(as_text=True)
        self.assertIn("bei erster Meldung erhalten 0", html)
        self.assertIn("später nachgeliefert 1", html)
        self.assertIn("offen 0", html)

    def test_wall_keeps_missing_without_transit_unchanged(self):
        html = self.client.get("/album/vfl").get_data(as_text=True)
        classes, attributes, inner = self.wall_slot(html, "1")

        self.assertIn("missing", classes.split())
        self.assertIn('data-quantity="0"', attributes)
        self.assertIn('data-incoming-transit="0"', attributes)
        self.assertNotIn("sticker-transit-badge", inner)

    def test_wall_marks_missing_transit_and_keeps_progress_and_filters_physical(self):
        self.create_accepted_trade(["1"])
        html = self.client.get("/album/vfl").get_data(as_text=True)
        classes, attributes, inner = self.wall_slot(html, "1")
        missing_html = self.client.get(
            "/album/vfl?filter=missing"
        ).get_data(as_text=True)
        owned_html = self.client.get(
            "/album/vfl?filter=owned"
        ).get_data(as_text=True)

        with self.connection() as connection:
            inventory = InventoryReadService(connection).album(2, "vfl")
            progress = inventory.progress(webapp.all_codes("vfl"), 250)

        self.assertIn("missing", classes.split())
        self.assertIn('data-quantity="0"', attributes)
        self.assertIn('data-incoming-transit="1"', attributes)
        self.assertIn(">Unterwegs</span>", inner)
        self.assertEqual(0, inventory.availability("1").physical)
        self.assertEqual(1, inventory.availability("1").incoming_transit)
        self.assertEqual(3, progress.collected)
        self.assertNotIn("filter-hidden", self.wall_slot(missing_html, "1")[0])
        self.assertIn("filter-hidden", self.wall_slot(owned_html, "1")[0])

    def test_wall_displays_transit_quantity_greater_than_one(self):
        self.create_accepted_trade(["1", "1", "1"])
        html = self.client.get("/album/vfl").get_data(as_text=True)
        classes, attributes, inner = self.wall_slot(html, "1")

        self.assertIn("missing", classes.split())
        self.assertIn('data-incoming-transit="3"', attributes)
        self.assertIn(">3 unterwegs</span>", inner)

    def test_owned_wall_status_and_inventory_stay_separate_from_transit(self):
        self.create_accepted_trade(["2"])
        html = self.client.get("/album/vfl").get_data(as_text=True)
        classes, attributes, inner = self.wall_slot(html, "2")
        missing_html = self.client.get(
            "/album/vfl?filter=missing"
        ).get_data(as_text=True)
        owned_html = self.client.get(
            "/album/vfl?filter=owned"
        ).get_data(as_text=True)

        self.assertIn("owned", classes.split())
        self.assertIn('data-quantity="1"', attributes)
        self.assertIn('data-incoming-transit="1"', attributes)
        self.assertIn(">+1 unterwegs</span>", inner)
        self.assertIn("filter-hidden", self.wall_slot(missing_html, "2")[0])
        self.assertNotIn("filter-hidden", self.wall_slot(owned_html, "2")[0])

    def test_transit_marker_disappears_after_receipt_and_detail_uses_same_value(self):
        trade_id = self.create_accepted_trade(["1"])
        before_html = self.client.get("/album/vfl").get_data(as_text=True)
        detail_html = self.client.get("/sticker/vfl/1").get_data(as_text=True)

        self.assertIn(">Unterwegs</span>", self.wall_slot(before_html, "1")[2])
        self.assertIn("1 unterwegs", detail_html)
        self.assertIn('id="stickerDetailTransit" hidden', before_html)

        receipt = self.client.post(f"/trade/{trade_id}/receive")
        self.assertEqual(302, receipt.status_code)
        after_html = self.client.get("/album/vfl").get_data(as_text=True)
        classes, attributes, inner = self.wall_slot(after_html, "1")

        self.assertIn("owned", classes.split())
        self.assertIn('data-quantity="1"', attributes)
        self.assertIn('data-incoming-transit="0"', attributes)
        self.assertNotIn("sticker-transit-badge", inner)

    def test_local_and_fixture_databases_remain_unchanged(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(REFERENCE_FIXTURE))


if __name__ == "__main__":
    unittest.main()
