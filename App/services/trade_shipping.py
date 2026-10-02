from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.history_cutover import (
    HistoricalInventoryWriteService,
    cutover_schema_available,
)
from services.inventory_write import InventoryWriteService
from services.trade_reservations import reservation_schema_available


class TradeShippingCode(str, Enum):
    SHIPPED = "SHIPPED"
    ALREADY_SHIPPED = "ALREADY_SHIPPED"
    INVALID_TRADE_STATE = "INVALID_TRADE_STATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    MISSING_RESERVATIONS = "MISSING_RESERVATIONS"
    TRANSACTION_ERROR = "TRANSACTION_ERROR"


@dataclass(frozen=True)
class TradeShippingResultDTO:
    code: TradeShippingCode
    trade_request_id: int
    lifecycle_trade_id: int | None
    side: str | None
    shipped_at: str | None
    explanation: str

    @property
    def shipped(self):
        return self.code is TradeShippingCode.SHIPPED

    @property
    def idempotent(self):
        return self.code is TradeShippingCode.ALREADY_SHIPPED


@dataclass(frozen=True)
class TradeShippingStatusDTO:
    trade_request_id: int
    lifecycle_trade_id: int
    requester_user_id: int
    partner_user_id: int
    requester_shipped: bool
    requester_shipped_at: str | None
    partner_shipped: bool
    partner_shipped_at: str | None

    def side_for(self, user_id):
        if user_id == self.requester_user_id:
            return "requester"
        if user_id == self.partner_user_id:
            return "partner"
        return None

    def shipped_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.requester_shipped
        if side == "partner":
            return self.partner_shipped
        return False

    def shipped_at_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.requester_shipped_at
        if side == "partner":
            return self.partner_shipped_at
        return None

    def other_shipped_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.partner_shipped
        if side == "partner":
            return self.requester_shipped
        return False

    @property
    def any_shipped(self):
        return self.requester_shipped or self.partner_shipped

    @property
    def both_shipped(self):
        return self.requester_shipped and self.partner_shipped


class _RejectedShipping(Exception):
    def __init__(self, code, explanation, lifecycle_trade_id=None, side=None):
        super().__init__(explanation)
        self.code = code
        self.explanation = explanation
        self.lifecycle_trade_id = lifecycle_trade_id
        self.side = side


def shipping_schema_available(connection):
    if not reservation_schema_available(connection):
        return False
    row = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='trade_shipping_status'
        """
    ).fetchone()
    return row is not None


def shipping_status_for_trade(connection, trade_request_id):
    if not shipping_schema_available(connection):
        return None
    row = connection.execute(
        """
        SELECT t.id AS lifecycle_trade_id, t.legacy_trade_request_id,
               t.requester_user_id, t.partner_user_id,
               s.requester_shipped, s.requester_shipped_at,
               s.partner_shipped, s.partner_shipped_at
        FROM trades t
        JOIN trade_shipping_status s ON s.trade_id=t.id
        WHERE t.legacy_trade_request_id=?
        """,
        (trade_request_id,),
    ).fetchone()
    if row is None:
        return None
    return TradeShippingStatusDTO(
        trade_request_id=row["legacy_trade_request_id"],
        lifecycle_trade_id=row["lifecycle_trade_id"],
        requester_user_id=row["requester_user_id"],
        partner_user_id=row["partner_user_id"],
        requester_shipped=bool(row["requester_shipped"]),
        requester_shipped_at=row["requester_shipped_at"],
        partner_shipped=bool(row["partner_shipped"]),
        partner_shipped_at=row["partner_shipped_at"],
    )


class TradeShippingService:
    """Moves one participant's reserved outgoing positions into transit."""

    def __init__(self, connection):
        self._connection = connection

    def _result(
        self,
        code,
        trade_request_id,
        lifecycle_trade_id=None,
        side=None,
        shipped_at=None,
        explanation="",
    ):
        return TradeShippingResultDTO(
            code=code,
            trade_request_id=trade_request_id,
            lifecycle_trade_id=lifecycle_trade_id,
            side=side,
            shipped_at=shipped_at,
            explanation=explanation,
        )

    def ship(self, trade_request_id, actor_user_id):
        if not shipping_schema_available(self._connection):
            return self._result(
                TradeShippingCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das versionierte Versandschema ist nicht installiert.",
            )

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._connection.execute(
                """
                SELECT r.*, t.id AS lifecycle_trade_id,
                       t.lifecycle_state, t.requester_user_id, t.partner_user_id
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                WHERE r.id=?
                """,
                (trade_request_id,),
            ).fetchone()
            if trade is None:
                raise _RejectedShipping(
                    TradeShippingCode.INVALID_TRADE_STATE,
                    "Der Trade besitzt keinen aktiven Lifecycle.",
                )
            lifecycle_trade_id = trade["lifecycle_trade_id"]
            if actor_user_id == trade["requester_user_id"]:
                side = "requester"
                shipped_column = "requester_shipped"
                timestamp_column = "requester_shipped_at"
            elif actor_user_id == trade["partner_user_id"]:
                side = "partner"
                shipped_column = "partner_shipped"
                timestamp_column = "partner_shipped_at"
            else:
                raise _RejectedShipping(
                    TradeShippingCode.UNAUTHORIZED,
                    "Nur beteiligte Nutzer dürfen den eigenen Versand bestätigen.",
                    lifecycle_trade_id,
                )

            if trade["status"] != "accepted" or trade["lifecycle_state"] not in {
                "accepted",
                "partially_shipped",
                "shipped",
                "partially_received",
                "problem_open",
            }:
                raise _RejectedShipping(
                    TradeShippingCode.INVALID_TRADE_STATE,
                    "Der Trade ist nicht in einem versandfähigen Zustand.",
                    lifecycle_trade_id,
                    side,
                )

            self._connection.execute(
                "INSERT OR IGNORE INTO trade_shipping_status (trade_id) VALUES (?)",
                (lifecycle_trade_id,),
            )
            status = self._connection.execute(
                "SELECT * FROM trade_shipping_status WHERE trade_id=?",
                (lifecycle_trade_id,),
            ).fetchone()
            if status[shipped_column] == 1:
                from services.typed_notifications import (
                    TypedNotificationService,
                    typed_notification_schema_available,
                )
                if typed_notification_schema_available(self._connection):
                    TypedNotificationService(self._connection).notify_shipped(
                        trade_request_id, actor_user_id
                    )
                self._connection.commit()
                return self._result(
                    TradeShippingCode.ALREADY_SHIPPED,
                    trade_request_id,
                    lifecycle_trade_id,
                    side,
                    status[timestamp_column],
                    "Der eigene Versand wurde bereits bestätigt.",
                )

            positions = self._connection.execute(
                """
                SELECT p.*, r.id AS reservation_id,
                       r.quantity AS reserved_quantity, r.state AS reservation_state
                FROM trade_positions p
                LEFT JOIN trade_reservations r
                  ON r.trade_position_id=p.id AND r.trade_id=p.trade_id
                WHERE p.trade_id=? AND p.from_user_id=?
                ORDER BY p.id
                """,
                (lifecycle_trade_id, actor_user_id),
            ).fetchall()
            if not positions:
                raise _RejectedShipping(
                    TradeShippingCode.MISSING_RESERVATIONS,
                    "Für die eigene Seite fehlen ausgehende Positionen.",
                    lifecycle_trade_id,
                    side,
                )
            for position in positions:
                if (
                    position["reservation_id"] is None
                    or position["reservation_state"] != "active"
                    or position["reserved_quantity"] != position["quantity"]
                ):
                    raise _RejectedShipping(
                        TradeShippingCode.MISSING_RESERVATIONS,
                        "Die eigenen Positionen sind nicht vollständig aktiv reserviert.",
                        lifecycle_trade_id,
                        side,
                    )

            for position in positions:
                released = self._connection.execute(
                    """
                    UPDATE trade_reservations
                    SET state='released', released_at=CURRENT_TIMESTAMP,
                        release_reason='shipped'
                    WHERE id=? AND state='active'
                    """,
                    (position["reservation_id"],),
                )
                if released.rowcount != 1:
                    raise _RejectedShipping(
                        TradeShippingCode.TRANSACTION_ERROR,
                        "Die Reservierung konnte nicht eindeutig überführt werden.",
                        lifecycle_trade_id,
                        side,
                    )

                if cutover_schema_available(self._connection):
                    mutation = HistoricalInventoryWriteService(
                        self._connection
                    ).remove(
                        actor_user_id,
                        position["album_id"],
                        position["sticker_code"],
                        position["quantity"],
                        event_key=(
                            f"trade-shipping:{lifecycle_trade_id}:"
                            f"{side}:{position['id']}"
                        ),
                        source_type="trade_shipping",
                    )
                else:
                    mutation = InventoryWriteService(self._connection).remove(
                        actor_user_id,
                        position["album_id"],
                        position["sticker_code"],
                        position["quantity"],
                    )
                expected = mutation.previous_quantity - position["quantity"]
                if not mutation.allowed or mutation.quantity != expected:
                    raise _RejectedShipping(
                        TradeShippingCode.TRANSACTION_ERROR,
                        "Der physische Versandbestand konnte nicht atomar überführt werden.",
                        lifecycle_trade_id,
                        side,
                    )

            updated = self._connection.execute(
                f"""
                UPDATE trade_shipping_status
                SET {shipped_column}=1, {timestamp_column}=CURRENT_TIMESTAMP,
                    updated_at=CURRENT_TIMESTAMP
                WHERE trade_id=? AND {shipped_column}=0
                """,
                (lifecycle_trade_id,),
            )
            if updated.rowcount != 1:
                raise _RejectedShipping(
                    TradeShippingCode.TRANSACTION_ERROR,
                    "Der Versandstatus konnte nicht eindeutig gespeichert werden.",
                    lifecycle_trade_id,
                    side,
                )

            status = self._connection.execute(
                "SELECT * FROM trade_shipping_status WHERE trade_id=?",
                (lifecycle_trade_id,),
            ).fetchone()
            receipt_table = self._connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table' AND name='trade_receipt_status'
                """
            ).fetchone()
            receipt_status = None
            if receipt_table:
                receipt_status = self._connection.execute(
                    """
                    SELECT requester_received, partner_received
                    FROM trade_receipt_status WHERE trade_id=?
                    """,
                    (lifecycle_trade_id,),
                ).fetchone()
            any_received = bool(
                receipt_status
                and (
                    receipt_status["requester_received"]
                    or receipt_status["partner_received"]
                )
            )
            problem_table = self._connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table' AND name='trade_receipt_reports'
                """
            ).fetchone()
            open_problem = False
            if problem_table:
                open_problem = self._connection.execute(
                    """
                    SELECT 1 FROM trade_receipt_reports
                    WHERE trade_id=? AND state='open'
                    LIMIT 1
                    """,
                    (lifecycle_trade_id,),
                ).fetchone() is not None
            if open_problem:
                lifecycle_state = "problem_open"
            elif any_received:
                lifecycle_state = "partially_received"
            elif status["requester_shipped"] and status["partner_shipped"]:
                lifecycle_state = "shipped"
            else:
                lifecycle_state = "partially_shipped"
            self._connection.execute(
                """
                UPDATE trades
                SET lifecycle_state=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (lifecycle_state, lifecycle_trade_id),
            )
            from services.typed_notifications import (
                TypedNotificationService,
                typed_notification_schema_available,
            )
            if typed_notification_schema_available(self._connection):
                TypedNotificationService(self._connection).notify_shipped(
                    trade_request_id, actor_user_id
                )
            self._connection.commit()
            return self._result(
                TradeShippingCode.SHIPPED,
                trade_request_id,
                lifecycle_trade_id,
                side,
                status[timestamp_column],
                "Der eigene Versand wurde bestätigt; die Positionen sind unterwegs.",
            )
        except _RejectedShipping as rejected:
            self._connection.rollback()
            return self._result(
                rejected.code,
                trade_request_id,
                rejected.lifecycle_trade_id,
                rejected.side,
                explanation=rejected.explanation,
            )
        except Exception:
            self._connection.rollback()
            return self._result(
                TradeShippingCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Die Versandbestätigung wurde vollständig zurückgerollt.",
            )
