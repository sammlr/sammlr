from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import json

from services.inventory import InventoryReadService


class TradeAcceptanceCode(str, Enum):
    ACCEPTED = "ACCEPTED"
    ALREADY_ACCEPTED = "ALREADY_ACCEPTED"
    INSUFFICIENT_AVAILABLE = "INSUFFICIENT_AVAILABLE"
    INVALID_TRADE_STATE = "INVALID_TRADE_STATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    TRANSACTION_ERROR = "TRANSACTION_ERROR"


@dataclass(frozen=True)
class TradeAcceptanceResultDTO:
    code: TradeAcceptanceCode
    trade_request_id: int
    lifecycle_trade_id: int | None
    explanation: str

    @property
    def accepted(self):
        return self.code is TradeAcceptanceCode.ACCEPTED

    @property
    def idempotent(self):
        return self.code is TradeAcceptanceCode.ALREADY_ACCEPTED


@dataclass(frozen=True)
class ReservationReleaseDTO:
    trade_request_id: int
    released_count: int
    reason: str


@dataclass(frozen=True)
class _Position:
    from_user_id: int
    to_user_id: int
    album_id: str
    sticker_code: str
    quantity: int


class _RejectedAcceptance(Exception):
    def __init__(self, code, explanation, lifecycle_trade_id=None):
        super().__init__(explanation)
        self.code = code
        self.explanation = explanation
        self.lifecycle_trade_id = lifecycle_trade_id


def reservation_schema_available(connection):
    required = {"trades", "trade_positions", "trade_reservations"}
    rows = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('trades', 'trade_positions', 'trade_reservations')
        """
    ).fetchall()
    return {row[0] for row in rows} == required


class ActiveReservationBindings:
    """Inventory Guard binding source backed by active S14 reservations."""

    def __init__(self, connection):
        self._connection = connection

    def minimum_quantity(self, user_id, album_id, sticker_code):
        if not reservation_schema_available(self._connection):
            return 0

        row = self._connection.execute(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM trade_reservations
            WHERE user_id=? AND album_id=? AND sticker_code=? AND state='active'
            """,
            (user_id, album_id, sticker_code),
        ).fetchone()
        reserved = int(row[0])
        if reserved == 0:
            return 0

        inventory_row = self._connection.execute(
            """
            SELECT quantity FROM stickers
            WHERE user_id=? AND album_id=? AND sticker_code=?
            """,
            (user_id, album_id, sticker_code),
        ).fetchone()
        physical = max(int(inventory_row[0]), 0) if inventory_row else 0
        assigned = min(physical, 1)
        return assigned + reserved


class TradeReservationService:
    """Atomically accepts one legacy request and reserves every position."""

    def __init__(self, connection):
        self._connection = connection

    @staticmethod
    def _positions(trade):
        try:
            give_codes = json.loads(trade["give_codes"])
            get_codes = json.loads(trade["get_codes"])
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise _RejectedAcceptance(
                TradeAcceptanceCode.INVALID_TRADE_STATE,
                "Das bestehende Tradepaket ist ungültig.",
            ) from error

        if not isinstance(give_codes, list) or not isinstance(get_codes, list):
            raise _RejectedAcceptance(
                TradeAcceptanceCode.INVALID_TRADE_STATE,
                "Das bestehende Tradepaket ist ungültig.",
            )

        positions = []
        directions = (
            (trade["from_user_id"], trade["to_user_id"], give_codes),
            (trade["to_user_id"], trade["from_user_id"], get_codes),
        )
        for from_user_id, to_user_id, codes in directions:
            normalized = []
            for code in codes:
                if not isinstance(code, str) or not code:
                    raise _RejectedAcceptance(
                        TradeAcceptanceCode.INVALID_TRADE_STATE,
                        "Das bestehende Tradepaket enthält einen ungültigen Stickercode.",
                    )
                normalized.append(code)
            for sticker_code, quantity in Counter(normalized).items():
                positions.append(
                    _Position(
                        from_user_id=from_user_id,
                        to_user_id=to_user_id,
                        album_id=trade["album_id"],
                        sticker_code=sticker_code,
                        quantity=quantity,
                    )
                )

        if not positions or not give_codes or not get_codes:
            raise _RejectedAcceptance(
                TradeAcceptanceCode.INVALID_TRADE_STATE,
                "Der Trade besitzt keine vollständigen ausgehenden Positionen.",
            )
        return tuple(positions)

    def _lifecycle_trade(self, trade):
        existing = self._connection.execute(
            "SELECT * FROM trades WHERE legacy_trade_request_id=?",
            (trade["id"],),
        ).fetchone()
        if existing:
            if (
                existing["requester_user_id"] != trade["from_user_id"]
                or existing["partner_user_id"] != trade["to_user_id"]
            ):
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.TRANSACTION_ERROR,
                    "Die bestehende Lifecycle-Zuordnung ist widersprüchlich.",
                    existing["id"],
                )
            return existing["id"]

        cursor = self._connection.execute(
            """
            INSERT INTO trades
                (legacy_trade_request_id, requester_user_id, partner_user_id,
                 lifecycle_state, created_at, updated_at)
            VALUES (?, ?, ?, 'accepted', ?, CURRENT_TIMESTAMP)
            """,
            (
                trade["id"],
                trade["from_user_id"],
                trade["to_user_id"],
                trade["created_at"],
            ),
        )
        return cursor.lastrowid

    def _store_positions(self, lifecycle_trade_id, positions):
        stored = []
        for position in positions:
            existing = self._connection.execute(
                """
                SELECT id, quantity FROM trade_positions
                WHERE trade_id=? AND from_user_id=? AND to_user_id=?
                  AND album_id=? AND sticker_code=?
                """,
                (
                    lifecycle_trade_id,
                    position.from_user_id,
                    position.to_user_id,
                    position.album_id,
                    position.sticker_code,
                ),
            ).fetchone()
            if existing:
                if existing["quantity"] != position.quantity:
                    raise _RejectedAcceptance(
                        TradeAcceptanceCode.TRANSACTION_ERROR,
                        "Die bestehende Lifecycle-Position ist widersprüchlich.",
                        lifecycle_trade_id,
                    )
                position_id = existing["id"]
            else:
                cursor = self._connection.execute(
                    """
                    INSERT INTO trade_positions
                        (trade_id, from_user_id, to_user_id, album_id,
                         sticker_code, quantity)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lifecycle_trade_id,
                        position.from_user_id,
                        position.to_user_id,
                        position.album_id,
                        position.sticker_code,
                        position.quantity,
                    ),
                )
                position_id = cursor.lastrowid
            stored.append((position_id, position))
        return tuple(stored)

    def _ensure_shipping_status(self, lifecycle_trade_id):
        table = self._connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='trade_shipping_status'
            """
        ).fetchone()
        if table:
            self._connection.execute(
                "INSERT OR IGNORE INTO trade_shipping_status (trade_id) VALUES (?)",
                (lifecycle_trade_id,),
            )

    def _assert_available(self, positions, lifecycle_trade_id):
        inventories = {}
        for position in positions:
            key = (position.from_user_id, position.album_id)
            if key not in inventories:
                inventories[key] = InventoryReadService(self._connection).album(*key)
            reservable = inventories[key].availability(
                position.sticker_code
            ).reservable
            if position.quantity > reservable:
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.INSUFFICIENT_AVAILABLE,
                    (
                        "Nicht mehr genügend verfügbar: "
                        f"{position.album_id}/{position.sticker_code}."
                    ),
                    lifecycle_trade_id,
                )

    def accept(self, trade_request_id, actor_user_id, on_accepted=None):
        if not reservation_schema_available(self._connection):
            return TradeAcceptanceResultDTO(
                TradeAcceptanceCode.TRANSACTION_ERROR,
                trade_request_id,
                None,
                "Das versionierte Reservierungsschema ist nicht installiert.",
            )

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._connection.execute(
                "SELECT * FROM trade_requests WHERE id=?",
                (trade_request_id,),
            ).fetchone()
            if trade is None:
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.INVALID_TRADE_STATE,
                    "Die Tradeanfrage existiert nicht.",
                )
            if trade["to_user_id"] != actor_user_id:
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.UNAUTHORIZED,
                    "Nur der Empfänger darf die Tradeanfrage annehmen.",
                )
            if trade["status"] == "accepted":
                existing = self._connection.execute(
                    "SELECT id FROM trades WHERE legacy_trade_request_id=?",
                    (trade_request_id,),
                ).fetchone()
                self._connection.commit()
                return TradeAcceptanceResultDTO(
                    TradeAcceptanceCode.ALREADY_ACCEPTED,
                    trade_request_id,
                    existing["id"] if existing else None,
                    "Die Tradeanfrage ist bereits angenommen.",
                )
            if trade["status"] != "open":
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.INVALID_TRADE_STATE,
                    "Die Tradeanfrage ist nicht mehr offen.",
                )

            positions = self._positions(trade)
            lifecycle_trade_id = self._lifecycle_trade(trade)
            self._ensure_shipping_status(lifecycle_trade_id)
            self._assert_available(positions, lifecycle_trade_id)
            stored_positions = self._store_positions(lifecycle_trade_id, positions)

            for position_id, position in stored_positions:
                self._connection.execute(
                    """
                    INSERT INTO trade_reservations
                        (trade_id, trade_position_id, user_id, album_id,
                         sticker_code, quantity, state)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                    """,
                    (
                        lifecycle_trade_id,
                        position_id,
                        position.from_user_id,
                        position.album_id,
                        position.sticker_code,
                        position.quantity,
                    ),
                )

            updated = self._connection.execute(
                """
                UPDATE trade_requests
                SET status='accepted', from_confirmed=0, to_confirmed=0
                WHERE id=? AND to_user_id=? AND status='open'
                """,
                (trade_request_id, actor_user_id),
            )
            if updated.rowcount != 1:
                raise _RejectedAcceptance(
                    TradeAcceptanceCode.INVALID_TRADE_STATE,
                    "Die Tradeanfrage wurde parallel verändert.",
                    lifecycle_trade_id,
                )

            if on_accepted is not None:
                on_accepted(self._connection, trade)
            from services.community import UserActivityService
            UserActivityService(self._connection).touch(actor_user_id)
            self._connection.commit()
            return TradeAcceptanceResultDTO(
                TradeAcceptanceCode.ACCEPTED,
                trade_request_id,
                lifecycle_trade_id,
                "Die Tradeanfrage wurde vollständig angenommen und reserviert.",
            )
        except _RejectedAcceptance as rejected:
            self._connection.rollback()
            return TradeAcceptanceResultDTO(
                rejected.code,
                trade_request_id,
                rejected.lifecycle_trade_id,
                rejected.explanation,
            )
        except Exception:
            self._connection.rollback()
            return TradeAcceptanceResultDTO(
                TradeAcceptanceCode.TRANSACTION_ERROR,
                trade_request_id,
                None,
                "Die Annahme wurde vollständig zurückgerollt.",
            )

    def release(self, trade_request_id, reason, lifecycle_state, *, released_at=None):
        if not reservation_schema_available(self._connection):
            return ReservationReleaseDTO(trade_request_id, 0, reason)

        trade = self._connection.execute(
            "SELECT id FROM trades WHERE legacy_trade_request_id=?",
            (trade_request_id,),
        ).fetchone()
        if trade is None:
            return ReservationReleaseDTO(trade_request_id, 0, reason)

        released = self._connection.execute(
            """
            UPDATE trade_reservations
            SET state='released', released_at=COALESCE(?, CURRENT_TIMESTAMP), release_reason=?
            WHERE trade_id=? AND state='active'
            """,
            (released_at, reason, trade["id"]),
        )
        self._connection.execute(
            """
            UPDATE trades
            SET lifecycle_state=?, updated_at=COALESCE(?, CURRENT_TIMESTAMP),
                completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
            WHERE id=?
            """,
            (lifecycle_state, released_at, lifecycle_state, trade["id"]),
        )
        return ReservationReleaseDTO(trade_request_id, released.rowcount, reason)
