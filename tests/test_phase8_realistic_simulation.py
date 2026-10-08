from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import atexit
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-phase8-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402
from App.Database.migration_runner import current_version, migrate  # noqa: E402
from services.collector_profiles import CollectorProfileService  # noqa: E402
from services.community import CommunityMutationCode, CommunityService  # noqa: E402
from services.feed_events import FeedEventService  # noqa: E402
from services.history_cutover import (  # noqa: E402
    AlbumHistoryCutoverService,
    HistoricalInventoryWriteService,
)
from services.notification_history import NotificationHistoryService  # noqa: E402
from services.smart_trade_requests import (  # noqa: E402
    SmartTradeRequestCode,
    SmartTradeRequestService,
)
from services.statistics_projection import StatisticsProjectionService  # noqa: E402
from services.trade_problems import (  # noqa: E402
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
    TradeProblemType,
)
from services.trade_ratings import TradeRatingCode, TradeRatingService  # noqa: E402
from services.trade_receipt import TradeReceiptCode, TradeReceiptService  # noqa: E402
from services.trade_reservations import (  # noqa: E402
    TradeAcceptanceCode,
    TradeReservationService,
)
from services.trade_shipping import TradeShippingCode, TradeShippingService  # noqa: E402
from services.typed_notifications import (  # noqa: E402
    NOTIFICATION_TYPES,
    TypedNotificationService,
)


EXPECTED_NOTIFICATION_TYPES = {
    "trade_request_created",
    "smart_trade_request_created",
    "trade_request_declined",
    "trade_shipped",
    "trade_rating_available",
    "friend_request",
    "trade_request_unfulfillable",
    "trade_problem_action_required",
    "trade_problem_terminal",
}


class Phase8RealisticSimulationTestCase(unittest.TestCase):
    """One connected Closed-Beta journey over a realistic disposable population."""

    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.fixture_hash = sha256(FIXTURE)
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)
        assert cls.fixture_hash == sha256(FIXTURE)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="sammlr-phase8-")
        self.db_path = Path(self.temp_dir.name) / "simulation.db"
        shutil.copy2(FIXTURE, self.db_path)
        with self.connection() as connection:
            migrate(connection, 18)
            self._reset_domain(connection)
            self._seed_population(connection)
        webapp.DB = str(self.db_path)
        self.client = webapp.app.test_client()
        with self.connection() as connection:
            self.initial_legacy_notifications = connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE notification_type='legacy'"
            ).fetchone()[0]
            self.operational_notification_floor = connection.execute(
                "SELECT COALESCE(MAX(id), 0) FROM notifications"
            ).fetchone()[0]

    def tearDown(self):
        self.assertEqual(self.local_hash, sha256(LOCAL_DB))
        self.assertEqual(self.fixture_hash, sha256(FIXTURE))
        self.temp_dir.cleanup()

    def connection(self):
        connection = sqlite3.connect(self.db_path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _reset_domain(connection):
        for table in (
            "sammlr_news", "feed_events", "trophy_unlock_history_context",
            "canonical_trophy_unlocks", "historical_album_progress_points",
            "historical_sticker_acquisitions", "historical_inventory_mutations",
            "historical_album_records", "trade_ratings",
            "trade_receipt_report_positions", "trade_receipt_reports",
            "trade_receipt_status", "trade_shipping_status",
            "trade_reservations", "trade_events", "trade_positions", "trades",
            "trade_requests", "notifications", "blocks", "friendships",
            "friendship_requests", "user_activity", "unlocked_trophies",
            "stickers", "user_albums",
        ):
            connection.execute(f"DELETE FROM {table}")
        connection.execute("DELETE FROM users WHERE id > 3")
        connection.execute(
            "UPDATE users SET account_state='active', profile_privacy='public'"
        )
        connection.commit()

    def _seed_population(self, connection):
        connection.executemany(
            """
            INSERT INTO users
                (username, password, name, favorite_album_id, profile_privacy)
            VALUES (?, 'phase8-only', ?, 'vfl', ?)
            """,
            (
                (
                    f"phase8_user_{user_id:02d}",
                    f"Simulation {user_id:02d}",
                    "private" if user_id % 5 == 0 else "public",
                )
                for user_id in range(4, 31)
            ),
        )
        connection.commit()

        history = AlbumHistoryCutoverService(connection)
        for user_id in range(1, 31):
            history.add(
                user_id,
                "vfl",
                occurred_at=f"2026-07-{(user_id % 28) + 1:02d}T08:00:00.000000Z",
            )
            if user_id % 2 == 0:
                history.add(
                    user_id,
                    "wm26",
                    occurred_at=f"2026-07-{(user_id % 28) + 1:02d}T09:00:00.000000Z",
                )
            if user_id % 3 == 0:
                history.add(
                    user_id,
                    "em24",
                    occurred_at=f"2026-07-{(user_id % 28) + 1:02d}T10:00:00.000000Z",
                )

        for user_id in range(1, 31):
            collected = 12 + ((user_id * 7) % 70)
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, 'vfl', ?, 'owned', ?, ?)
                """,
                (
                    (
                        user_id,
                        str(code),
                        2 if code % 17 == user_id % 17 else (
                            1 if code % 11 == user_id % 11 else 0
                        ),
                        3 if code % 17 == user_id % 17 else (
                            2 if code % 11 == user_id % 11 else 1
                        ),
                    )
                    for code in range(1, collected + 1)
                ),
            )
        connection.execute(
            "UPDATE user_albums SET visibility='friends' WHERE user_id % 3 = 0"
        )
        connection.execute(
            "UPDATE user_albums SET visibility='public' WHERE user_id % 3 = 1"
        )
        connection.execute(
            "UPDATE user_albums SET visibility='private' WHERE user_id % 3 = 2"
        )
        connection.execute(
            "UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id % 7 = 0"
        )
        connection.executemany(
            "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
            ((1, 2), (3, 4), (7, 8), (12, 13), (20, 21)),
        )
        connection.executemany(
            """
            INSERT INTO friendship_requests
                (requester_user_id, recipient_user_id, status)
            VALUES (?, ?, 'pending')
            """,
            ((5, 6), (9, 10), (14, 15)),
        )
        connection.executemany(
            "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (?, ?)",
            ((16, 17), (18, 19)),
        )

        # Pre-existing inbox history: multiple pages, typed and legacy, old read
        # rows eligible for retention and old unread rows that must survive.
        for index in range(32):
            connection.execute(
                """
                INSERT INTO notifications
                    (user_id, title, body, is_read, created_at,
                     notification_type, target_type, target_id, dedupe_key)
                VALUES (15, ?, 'Population', 0, ?, ?, 'friendship', ?, ?)
                """,
                (
                    f"Population {index}",
                    f"2026-08-{(index % 18) + 1:02d} 10:00:00",
                    "friend_request" if index % 2 == 0 else "legacy",
                    10000 + index,
                    f"phase8:population:{index}",
                ),
            )
        connection.execute(
            """
            INSERT INTO notifications
                (user_id, title, body, is_read, created_at, notification_type)
            VALUES (15, 'Alt gelesen', 'Retention', 1,
                    '2026-06-01 10:00:00', 'legacy')
            """
        )
        connection.execute(
            """
            INSERT INTO notifications
                (user_id, title, body, is_read, created_at, notification_type,
                 target_type, target_id, dedupe_key)
            VALUES (15, 'Alt ungelesen', 'Bleibt', 0,
                    '2026-06-01 10:00:00', 'friend_request',
                    'friendship', 20000, 'phase8:old-unread')
            """
        )
        connection.commit()

    def set_inventory(self, user_id, quantities, album_id="vfl"):
        with self.connection() as connection:
            connection.execute(
                "UPDATE user_albums SET trade_pool_enabled=1 "
                "WHERE user_id=? AND album_id=?",
                (user_id, album_id),
            )
            for code, quantity in quantities.items():
                if quantity <= 0:
                    connection.execute(
                        "DELETE FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                        (user_id, album_id, code),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO stickers
                            (user_id, album_id, sticker_code, status, duplicates, quantity)
                        VALUES (?, ?, ?, 'owned', ?, ?)
                        ON CONFLICT(user_id, album_id, sticker_code) DO UPDATE SET
                            status='owned', duplicates=excluded.duplicates,
                            quantity=excluded.quantity
                        """,
                        (user_id, album_id, code, quantity - 1, quantity),
                    )

    def checkpoint(self, label):
        with self.connection() as connection:
            self.assertEqual(18, current_version(connection), label)
            self.assertEqual("ok", connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0], label)
            self.assertEqual([], connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(), label)
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM stickers WHERE quantity < 1 OR duplicates <> quantity - 1"
            ).fetchone()[0], label)
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM trade_requests WHERE from_user_id=to_user_id"
            ).fetchone()[0], label)
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT user_album_id FROM historical_album_records
                    WHERE completed_at IS NOT NULL GROUP BY user_album_id HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0], label)
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT user_album_id, trophy_definition_id
                    FROM canonical_trophy_unlocks
                    GROUP BY user_album_id, trophy_definition_id HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0], label)
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT dedupe_key FROM notifications WHERE dedupe_key IS NOT NULL
                    GROUP BY dedupe_key HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0], label)
            self.assertEqual(0, connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT r.user_id, r.album_id, r.sticker_code,
                           SUM(r.quantity) AS reserved,
                           COALESCE(MAX(s.quantity), 0) AS physical
                    FROM trade_reservations r
                    LEFT JOIN stickers s ON s.user_id=r.user_id
                       AND s.album_id=r.album_id AND s.sticker_code=r.sticker_code
                    WHERE r.state='active'
                    GROUP BY r.user_id, r.album_id, r.sticker_code
                    HAVING reserved > MAX(physical - 1, 0)
                )
                """
            ).fetchone()[0], label)
            placeholders = ",".join("?" for _ in EXPECTED_NOTIFICATION_TYPES)
            self.assertEqual(0, connection.execute(
                f"""
                SELECT COUNT(*) FROM notifications
                WHERE id > ? AND notification_type NOT IN ({placeholders})
                """,
                (self.operational_notification_floor, *sorted(EXPECTED_NOTIFICATION_TYPES)),
            ).fetchone()[0], label)
            self.assertLessEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM notifications WHERE notification_type='legacy'"
                ).fetchone()[0],
                self.initial_legacy_notifications,
                label,
            )

    def create_smart_request(self, from_user_id, to_user_id, give, get):
        with self.connection() as connection:
            notifications = TypedNotificationService(connection)
            return SmartTradeRequestService(connection).create(
                "vfl", from_user_id, to_user_id, give, get,
                on_created=lambda con, request_id: notifications.notify_request_created(
                    request_id, from_user_id, to_user_id, smart=True
                ),
            )

    def accept(self, request_id, actor_id):
        with self.connection() as connection:
            return TradeReservationService(connection).accept(request_id, actor_id)

    def ship(self, request_id, actor_id):
        with self.connection() as connection:
            return TradeShippingService(connection).ship(request_id, actor_id)

    def receive(self, request_id, actor_id):
        with self.connection() as connection:
            return TradeReceiptService(connection).receive(request_id, actor_id)

    def test_connected_multiuser_closed_beta_simulation(self):
        # Account/onboarding uses the real HTTP/session/CSRF path.
        registered = self.client.post("/register", data={
            "name": "Neue Simulation",
            "username": "phase8_new_user",
            "password": "phase8-password",
            "password_repeat": "phase8-password",
        })
        self.assertEqual(302, registered.status_code)
        self.assertEqual(302, self.client.post("/login", data={
            "username": "phase8_new_user", "password": "phase8-password",
        }).status_code)
        self.assertEqual(200, self.client.get("/account").status_code)
        self.assertEqual(302, self.client.post(
            "/profil/privacy", data={"profile_privacy": "private"}
        ).status_code)
        self.assertEqual(302, self.client.post("/alben/hinzufuegen/vfl").status_code)
        quantity = self.client.post(
            "/album/vfl/sticker/1/quantity", data={"delta": "1"}
        )
        self.assertEqual(200, quantity.status_code)
        self.assertEqual(1, quantity.get_json()["quantity"])
        self.assertEqual(200, self.client.get("/album/vfl?filter=missing").status_code)
        self.assertEqual(200, self.client.get("/album/vfl?filter=duplicate").status_code)
        self.assertEqual(302, self.client.post("/logout").status_code)

        self.checkpoint("after account and collection onboarding")

        # Social flow, privacy and blocks.
        with self.connection() as connection:
            community = CommunityService(connection)
            created = community.send_request(22, 23)
            self.assertEqual(CommunityMutationCode.CREATED, created.code)
            accepted = community.accept_request(created.friendship_request_id, 23)
            self.assertEqual(CommunityMutationCode.ACCEPTED, accepted.code)
            self.assertTrue(community.are_friends(22, 23))
            pending = community.send_request(24, 25)
            self.assertEqual(CommunityMutationCode.CREATED, pending.code)
            blocked = community.block(26, 27)
            self.assertEqual(CommunityMutationCode.BLOCKED, blocked.code)
            self.assertFalse(community.can_start_interaction(26, 27))

        # Exactly-once completion, trophy and feed from one final sticker.
        with self.connection() as connection:
            connection.execute("DELETE FROM stickers WHERE user_id=12 AND album_id='vfl'")
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (12, 'vfl', ?, 'owned', 0, 1)
                """,
                ((str(code),) for code in range(1, 250)),
            )
            connection.commit()

        def finish_album(event_number):
            with self.connection() as connection:
                return HistoricalInventoryWriteService(connection).set_quantity(
                    12, "vfl", "250", 1,
                    event_key=f"phase8:parallel-completion:{event_number}",
                    occurred_at="2026-08-21T10:00:00.000000Z",
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            completion_results = tuple(executor.map(finish_album, (1, 2)))
        self.assertTrue(all(result.allowed for result in completion_results))
        with self.connection() as connection:
            membership = connection.execute(
                "SELECT id FROM user_albums WHERE user_id=12 AND album_id='vfl'"
            ).fetchone()[0]
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM historical_album_records WHERE user_album_id=? AND completed_at IS NOT NULL",
                (membership,),
            ).fetchone()[0])
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM canonical_trophy_unlocks WHERE user_album_id=? AND source_type='album_completion'",
                (membership,),
            ).fetchone()[0])
            self.assertEqual(1, connection.execute(
                "SELECT COUNT(*) FROM feed_events WHERE event_key=?",
                (f"feed:album-completion:{membership}",),
            ).fetchone()[0])
            HistoricalInventoryWriteService(connection).remove(
                12, "vfl", "250", event_key="phase8:post-completion-remove"
            )
            connection.commit()
            self.assertIsNotNone(connection.execute(
                "SELECT completed_at FROM historical_album_records WHERE user_album_id=?",
                (membership,),
            ).fetchone()[0])

            connection.execute("DELETE FROM stickers WHERE user_id=13 AND album_id='vfl'")
            connection.executemany(
                """
                INSERT INTO stickers
                    (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (13, 'vfl', ?, 'owned', 0, 1)
                """,
                ((str(code),) for code in range(1, 250)),
            )
            connection.commit()
            HistoricalInventoryWriteService(connection).set_quantity(
                13, "vfl", "250", 1,
                event_key="phase8:second-completion",
                occurred_at="2026-08-21T10:05:00.000000Z",
            )
            connection.commit()
            self.assertEqual(2, connection.execute(
                "SELECT COUNT(*) FROM historical_album_records WHERE completed_at IS NOT NULL"
            ).fetchone()[0])

        self.checkpoint("after parallel album completion")

        # Full unequal SmartTrade including retries, inventory direction and rating.
        self.set_inventory(1, {"1": 3, "2": 2})
        self.set_inventory(2, {"10": 3})
        smart = self.create_smart_request(1, 2, ("1", "2"), ("10",))
        self.assertEqual(SmartTradeRequestCode.CREATED, smart.code)
        accepted = self.accept(smart.trade_request_id, 2)
        self.assertEqual(TradeAcceptanceCode.ACCEPTED, accepted.code)
        self.assertEqual(
            TradeAcceptanceCode.ALREADY_ACCEPTED,
            self.accept(smart.trade_request_id, 2).code,
        )
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(smart.trade_request_id, 1).code)
        self.assertEqual(
            TradeShippingCode.ALREADY_SHIPPED,
            self.ship(smart.trade_request_id, 1).code,
        )
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(smart.trade_request_id, 2).code)
        self.assertEqual(TradeReceiptCode.RECEIVED, self.receive(smart.trade_request_id, 1).code)
        self.assertEqual(TradeReceiptCode.RECEIVED, self.receive(smart.trade_request_id, 2).code)
        self.assertEqual(
            TradeReceiptCode.ALREADY_RECEIVED,
            self.receive(smart.trade_request_id, 2).code,
        )
        with self.connection() as connection:
            rating = TradeRatingService(connection).create(smart.trade_request_id, 1, 5)
            self.assertEqual(TradeRatingCode.CREATED, rating.code)
            self.assertNotEqual(
                TradeRatingCode.CREATED,
                TradeRatingService(connection).create(smart.trade_request_id, 1, 5).code,
            )
            statistics = StatisticsProjectionService(connection).for_user(1, 1)
            profile = CollectorProfileService(connection).by_user_id(1, 1)
            self.assertEqual(1, statistics.career.successful_trades.successful_trade_count)
            self.assertEqual(1, profile.successful_trade_count)
            self.assertEqual((2, 1), (
                statistics.career.successful_trades.given_quantity_total,
                statistics.career.successful_trades.received_quantity_total,
            ))

        # A second independent end-to-end trade keeps multiple completed and
        # overlapping lifecycle histories in the same simulation database.
        self.set_inventory(13, {"80": 2})
        self.set_inventory(14, {"90": 2})
        second_trade = self.create_smart_request(13, 14, ("80",), ("90",))
        self.assertEqual(SmartTradeRequestCode.CREATED, second_trade.code)
        self.assertEqual(
            TradeAcceptanceCode.ACCEPTED,
            self.accept(second_trade.trade_request_id, 14).code,
        )
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(second_trade.trade_request_id, 13).code)
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(second_trade.trade_request_id, 14).code)
        self.assertEqual(TradeReceiptCode.RECEIVED, self.receive(second_trade.trade_request_id, 13).code)
        self.assertTrue(self.receive(second_trade.trade_request_id, 14).completed)

        # Bestandsänderung after SmartMatch makes the immutable request obsolete.
        self.set_inventory(3, {"20": 2})
        self.set_inventory(4, {"30": 2})
        obsolete = self.create_smart_request(3, 4, ("20",), ("30",))
        self.assertEqual(SmartTradeRequestCode.CREATED, obsolete.code)
        self.set_inventory(4, {"30": 1})
        with self.connection() as connection:
            state = SmartTradeRequestService(connection).inspect(
                obsolete.trade_request_id, 3
            )
        self.assertEqual(SmartTradeRequestCode.OBSOLETE, state.code)

        # Manual decline creates only the contracted notifications.
        with self.connection() as connection:
            request_id = connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', 5, 6, '[\"31\"]', '[\"32\"]', 'open')
                """
            ).lastrowid
            notifications = TypedNotificationService(connection)
            notifications.notify_request_created(request_id, 5, 6)
            connection.execute(
                "UPDATE trade_requests SET status='declined' WHERE id=?", (request_id,)
            )
            notifications.notify_request_declined(request_id, 6)
            connection.commit()

        self.checkpoint("after successful and obsolete trade journeys")

        # Problem journey: report, retry and terminal close without overbooking.
        self.set_inventory(7, {"40": 2})
        self.set_inventory(8, {"50": 2})
        problem_trade = self.create_smart_request(7, 8, ("40",), ("50",))
        self.assertEqual(SmartTradeRequestCode.CREATED, problem_trade.code)
        self.assertEqual(
            TradeAcceptanceCode.ACCEPTED,
            self.accept(problem_trade.trade_request_id, 8).code,
        )
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(problem_trade.trade_request_id, 7).code)
        self.assertEqual(TradeShippingCode.SHIPPED, self.ship(problem_trade.trade_request_id, 8).code)
        with self.connection() as connection:
            incoming = connection.execute(
                """
                SELECT p.id FROM trade_positions p
                JOIN trades t ON t.id=p.trade_id
                WHERE t.legacy_trade_request_id=? AND p.to_user_id=7
                """,
                (problem_trade.trade_request_id,),
            ).fetchone()[0]
            service = TradeProblemService(connection)
            inputs = (PartialReceiptInputDTO(
                incoming, 0, TradeProblemType.MISSING
            ),)
            reported = service.report(problem_trade.trade_request_id, 7, inputs)
            self.assertEqual(TradeProblemCode.PARTIAL_RECEIPT_RECORDED, reported.code)
            self.assertEqual(
                TradeProblemCode.ALREADY_IDENTICAL,
                service.report(problem_trade.trade_request_id, 7, inputs).code,
            )
            terminal = service.close_with_problem(problem_trade.trade_request_id, 7)
            self.assertEqual(TradeProblemCode.CLOSED_WITH_PROBLEM, terminal.code)
            self.assertEqual(
                TradeProblemCode.ALREADY_IDENTICAL,
                service.close_with_problem(problem_trade.trade_request_id, 7).code,
            )

        # Two requesters race for the same last duplicate: one reservation only.
        self.set_inventory(9, {"60": 2})
        self.set_inventory(10, {"70": 2})
        self.set_inventory(11, {"71": 2})
        with self.connection() as connection:
            race_ids = tuple(connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
                VALUES ('vfl', ?, 9, ?, '[\"60\"]', 'open')
                """,
                (requester, f'["{code}"]'),
            ).lastrowid for requester, code in ((10, "70"), (11, "71")))
            connection.commit()

        def race_accept(request_id):
            with self.connection() as connection:
                return TradeReservationService(connection).accept(request_id, 9).code

        with ThreadPoolExecutor(max_workers=2) as executor:
            race_results = tuple(executor.map(race_accept, race_ids))
        self.assertEqual(1, race_results.count(TradeAcceptanceCode.ACCEPTED))
        with self.connection() as connection:
            self.assertEqual(1, connection.execute(
                """
                SELECT COALESCE(SUM(quantity), 0) FROM trade_reservations
                WHERE user_id=9 AND album_id='vfl' AND sticker_code='60'
                  AND state='active'
                """
            ).fetchone()[0])

        self.checkpoint("after problem and competing reservation chaos")

        # Feed is chronological, contains at most one news item, and rechecks
        # current profile/album privacy and blocks for already stored events.
        with self.connection() as connection:
            connection.execute("UPDATE users SET profile_privacy='public' WHERE id IN (1,2)")
            connection.execute(
                "UPDATE user_albums SET visibility='public' WHERE user_id=2 AND album_id='vfl'"
            )
            feed = FeedEventService(connection)
            feed.publish_news(
                "phase8-one", title="News 1", body="Simulation",
                published_at="2026-08-20T10:00:00.000000Z",
            )
            feed.publish_news(
                "phase8-two", title="News 2", body="Simulation",
                published_at="2026-08-21T10:00:00.000000Z",
            )
            visible = feed.feed_for_user(1, limit=100)
            self.assertLessEqual(sum(item.event_type == "sammlr_news" for item in visible), 1)
            self.assertTrue(any(item.actor_user_id == 2 for item in visible))
            connection.execute(
                "UPDATE user_albums SET visibility='private' WHERE user_id=2 AND album_id='vfl'"
            )
            self.assertFalse(any(
                item.actor_user_id == 2 for item in feed.feed_for_user(1, limit=100)
            ))
            connection.execute(
                "UPDATE user_albums SET visibility='public' WHERE user_id=2 AND album_id='vfl'"
            )
            connection.execute(
                "INSERT INTO blocks (blocker_user_id, blocked_user_id) VALUES (2, 1)"
            )
            self.assertFalse(any(
                item.actor_user_id == 2 for item in feed.feed_for_user(1, limit=100)
            ))
            connection.rollback()

        # Inbox pagination/read-state/retention on one real populated inbox.
        clock = lambda: datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        with self.connection() as connection:
            inbox = NotificationHistoryService(connection, now_provider=clock)
            first = inbox.open_page(15, 1)
            self.assertEqual(25, len(first.items))
            self.assertGreaterEqual(first.total_pages, 2)
            self.assertEqual(1, first.retention_deleted)
            self.assertGreater(first.unread_count, 0)
            self.assertIsNotNone(connection.execute(
                "SELECT id FROM notifications WHERE dedupe_key='phase8:old-unread'"
            ).fetchone())
            second_page_before = inbox.page(15, 2)
            self.assertTrue(any(not item.is_read for item in second_page_before.items))

        with self.connection() as connection:
            produced_types = {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT notification_type FROM notifications WHERE id > ?",
                    (self.operational_notification_floor,),
                ).fetchall()
            }
            self.assertEqual(EXPECTED_NOTIFICATION_TYPES | {"lifecycle_addresses_released"}, NOTIFICATION_TYPES)
            self.assertEqual(EXPECTED_NOTIFICATION_TYPES, produced_types)
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM feed_events WHERE event_type NOT IN ('album_started','album_completed','trophy_unlocked','sammlr_news')"
            ).fetchone()[0])
            self.assertEqual(0, connection.execute(
                "SELECT COUNT(*) FROM user_activity WHERE user_id IS NULL"
            ).fetchone()[0])
            self.assertGreaterEqual(connection.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0], 31)
            self.assertGreaterEqual(connection.execute(
                "SELECT COUNT(*) FROM user_albums"
            ).fetchone()[0], 55)
            self.assertGreaterEqual(connection.execute(
                "SELECT COUNT(*) FROM stickers"
            ).fetchone()[0], 1000)

        self.checkpoint("final realistic simulation checkpoint")


if __name__ == "__main__":
    unittest.main()
