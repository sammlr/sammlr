from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json

from services.inventory_write import InventoryWriteService
from services.history_cutover import (
    HistoricalInventoryWriteService,
    cutover_schema_available,
)
from services.trade_shipping import shipping_schema_available


class TradeReceiptCode(str, Enum):
    RECEIVED = "RECEIVED"
    ALREADY_RECEIVED = "ALREADY_RECEIVED"
    NOT_SHIPPED = "NOT_SHIPPED"
    INVALID_TRADE_STATE = "INVALID_TRADE_STATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    TRANSACTION_ERROR = "TRANSACTION_ERROR"


@dataclass(frozen=True)
class TradeReceiptResultDTO:
    code: TradeReceiptCode
    trade_request_id: int
    lifecycle_trade_id: int | None
    side: str | None
    received_at: str | None
    trade_completed: bool
    explanation: str

    @property
    def received(self):
        return self.code is TradeReceiptCode.RECEIVED

    @property
    def idempotent(self):
        return self.code is TradeReceiptCode.ALREADY_RECEIVED

    @property
    def completed(self):
        return self.trade_completed


@dataclass(frozen=True)
class TradeReceiptStatusDTO:
    trade_request_id: int
    lifecycle_trade_id: int
    requester_user_id: int
    partner_user_id: int
    requester_received: bool
    requester_received_at: str | None
    partner_received: bool
    partner_received_at: str | None

    def side_for(self, user_id):
        if user_id == self.requester_user_id:
            return "requester"
        if user_id == self.partner_user_id:
            return "partner"
        return None

    def received_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.requester_received
        if side == "partner":
            return self.partner_received
        return False

    def received_at_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.requester_received_at
        if side == "partner":
            return self.partner_received_at
        return None

    def other_received_for(self, user_id):
        side = self.side_for(user_id)
        if side == "requester":
            return self.partner_received
        if side == "partner":
            return self.requester_received
        return False

    @property
    def any_received(self):
        return self.requester_received or self.partner_received

    @property
    def both_received(self):
        return self.requester_received and self.partner_received


class _RejectedReceipt(Exception):
    def __init__(self, code, explanation, lifecycle_trade_id=None, side=None):
        super().__init__(explanation)
        self.code = code
        self.explanation = explanation
        self.lifecycle_trade_id = lifecycle_trade_id
        self.side = side


def receipt_schema_available(connection):
    if not shipping_schema_available(connection):
        return False
    row = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='trade_receipt_status'
        """
    ).fetchone()
    return row is not None


def receipt_status_for_trade(connection, trade_request_id):
    if not receipt_schema_available(connection):
        return None
    row = connection.execute(
        """
        SELECT t.id AS lifecycle_trade_id, t.legacy_trade_request_id,
               t.requester_user_id, t.partner_user_id,
               COALESCE(r.requester_received, 0) AS requester_received,
               r.requester_received_at,
               COALESCE(r.partner_received, 0) AS partner_received,
               r.partner_received_at
        FROM trades t
        LEFT JOIN trade_receipt_status r ON r.trade_id=t.id
        WHERE t.legacy_trade_request_id=?
        """,
        (trade_request_id,),
    ).fetchone()
    if row is None:
        return None
    return TradeReceiptStatusDTO(
        trade_request_id=row["legacy_trade_request_id"],
        lifecycle_trade_id=row["lifecycle_trade_id"],
        requester_user_id=row["requester_user_id"],
        partner_user_id=row["partner_user_id"],
        requester_received=bool(row["requester_received"]),
        requester_received_at=row["requester_received_at"],
        partner_received=bool(row["partner_received"]),
        partner_received_at=row["partner_received_at"],
    )


def _open_problem_exists(connection, lifecycle_trade_id):
    table = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='trade_receipt_reports'
        """
    ).fetchone()
    if table is None:
        return False
    row = connection.execute(
        """
        SELECT 1 FROM trade_receipt_reports
        WHERE trade_id=? AND state='open'
        LIMIT 1
        """,
        (lifecycle_trade_id,),
    ).fetchone()
    return row is not None


def finalize_received_side(
    connection,
    trade,
    actor_user_id,
    side,
    on_completed=None,
    event_payload=None,
):
    """Persist one fully settled receiver side within the caller transaction."""

    lifecycle_trade_id = trade["lifecycle_trade_id"]
    trade_request_id = trade["id"]
    received_column = f"{side}_received"
    timestamp_column = f"{side}_received_at"
    updated = connection.execute(
        f"""
        UPDATE trade_receipt_status
        SET {received_column}=1, {timestamp_column}=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        WHERE trade_id=? AND {received_column}=0
        """,
        (lifecycle_trade_id,),
    )
    if updated.rowcount != 1:
        raise RuntimeError("receipt side was not updated exactly once")

    status = connection.execute(
        "SELECT * FROM trade_receipt_status WHERE trade_id=?",
        (lifecycle_trade_id,),
    ).fetchone()
    payload = {"side": side}
    payload.update(event_payload or {})
    connection.execute(
        """
        INSERT INTO trade_events
            (trade_id, event_type, actor_user_id, payload_json)
        VALUES (?, 'receipt_confirmed', ?, ?)
        """,
        (lifecycle_trade_id, actor_user_id, json.dumps(payload)),
    )

    completed = bool(
        status["requester_received"]
        and status["partner_received"]
        and not _open_problem_exists(connection, lifecycle_trade_id)
    )
    if completed:
        connection.execute(
            """
            UPDATE trades
            SET lifecycle_state='completed',
                completed_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (lifecycle_trade_id,),
        )
        completed_update = connection.execute(
            """
            UPDATE trade_requests
            SET status='completed', from_confirmed=1, to_confirmed=1
            WHERE id=? AND status='accepted'
            """,
            (trade_request_id,),
        )
        if completed_update.rowcount != 1:
            raise RuntimeError("trade completion was not updated exactly once")
        connection.execute(
            """
            INSERT INTO trade_events
                (trade_id, event_type, actor_user_id, payload_json)
            VALUES (?, 'completed', ?, ?)
            """,
            (
                lifecycle_trade_id,
                actor_user_id,
                json.dumps({"completion": "both_received"}),
            ),
        )
        from services.typed_notifications import (
            TypedNotificationService,
            typed_notification_schema_available,
        )
        if typed_notification_schema_available(connection):
            TypedNotificationService(connection).notify_rating_available(
                trade_request_id, actor_user_id
            )
        if on_completed is not None:
            on_completed(connection, trade)
    else:
        lifecycle_state = (
            "problem_open"
            if _open_problem_exists(connection, lifecycle_trade_id)
            else "partially_received"
        )
        connection.execute(
            """
            UPDATE trades
            SET lifecycle_state=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (lifecycle_state, lifecycle_trade_id),
        )
    return status, completed


class TradeReceiptService:
    """Books one participant's fully received incoming trade positions."""

    def __init__(self, connection):
        self._connection = connection

    def _result(
        self,
        code,
        trade_request_id,
        lifecycle_trade_id=None,
        side=None,
        received_at=None,
        trade_completed=False,
        explanation="",
    ):
        return TradeReceiptResultDTO(
            code=code,
            trade_request_id=trade_request_id,
            lifecycle_trade_id=lifecycle_trade_id,
            side=side,
            received_at=received_at,
            trade_completed=trade_completed,
            explanation=explanation,
        )

    def receive(self, trade_request_id, actor_user_id, on_completed=None):
        if not receipt_schema_available(self._connection):
            return self._result(
                TradeReceiptCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das versionierte Empfangsschema ist nicht installiert.",
            )

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._connection.execute(
                """
                SELECT r.*, t.id AS lifecycle_trade_id,
                       t.lifecycle_state, t.requester_user_id, t.partner_user_id,
                       s.requester_shipped, s.partner_shipped
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                JOIN trade_shipping_status s ON s.trade_id=t.id
                WHERE r.id=?
                """,
                (trade_request_id,),
            ).fetchone()
            if trade is None:
                raise _RejectedReceipt(
                    TradeReceiptCode.INVALID_TRADE_STATE,
                    "Der Trade besitzt keinen gültigen Versand-Lifecycle.",
                )

            lifecycle_trade_id = trade["lifecycle_trade_id"]
            if actor_user_id == trade["requester_user_id"]:
                side = "requester"
                received_column = "requester_received"
                timestamp_column = "requester_received_at"
                other_shipped_column = "partner_shipped"
            elif actor_user_id == trade["partner_user_id"]:
                side = "partner"
                received_column = "partner_received"
                timestamp_column = "partner_received_at"
                other_shipped_column = "requester_shipped"
            else:
                raise _RejectedReceipt(
                    TradeReceiptCode.UNAUTHORIZED,
                    "Nur der jeweilige Empfänger darf den eigenen Empfang bestätigen.",
                    lifecycle_trade_id,
                )

            self._connection.execute(
                "INSERT OR IGNORE INTO trade_receipt_status (trade_id) VALUES (?)",
                (lifecycle_trade_id,),
            )
            status = self._connection.execute(
                "SELECT * FROM trade_receipt_status WHERE trade_id=?",
                (lifecycle_trade_id,),
            ).fetchone()
            if status[received_column] == 1:
                self._connection.commit()
                return self._result(
                    TradeReceiptCode.ALREADY_RECEIVED,
                    trade_request_id,
                    lifecycle_trade_id,
                    side,
                    status[timestamp_column],
                    trade["status"] == "completed",
                    "Der eigene Empfang wurde bereits bestätigt.",
                )

            problem_table = self._connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table' AND name='trade_receipt_reports'
                """
            ).fetchone()
            if problem_table:
                existing_problem = self._connection.execute(
                    """
                    SELECT 1 FROM trade_receipt_reports
                    WHERE trade_id=? AND receiver_user_id=?
                    """,
                    (lifecycle_trade_id, actor_user_id),
                ).fetchone()
                if existing_problem:
                    raise _RejectedReceipt(
                        TradeReceiptCode.INVALID_TRADE_STATE,
                        "Für diese Empfangsseite besteht bereits ein Problembericht.",
                        lifecycle_trade_id,
                        side,
                    )

            if trade["status"] != "accepted" or trade["lifecycle_state"] not in {
                "partially_shipped",
                "shipped",
                "partially_received",
                "problem_open",
            }:
                raise _RejectedReceipt(
                    TradeReceiptCode.INVALID_TRADE_STATE,
                    "Der Trade ist nicht in einem empfangsfähigen Zustand.",
                    lifecycle_trade_id,
                    side,
                )
            if trade[other_shipped_column] != 1:
                raise _RejectedReceipt(
                    TradeReceiptCode.NOT_SHIPPED,
                    "Die Gegenseite hat ihren Versand noch nicht bestätigt.",
                    lifecycle_trade_id,
                    side,
                )

            positions = self._connection.execute(
                """
                SELECT * FROM trade_positions
                WHERE trade_id=? AND to_user_id=?
                ORDER BY id
                """,
                (lifecycle_trade_id, actor_user_id),
            ).fetchall()
            if not positions:
                raise _RejectedReceipt(
                    TradeReceiptCode.INVALID_TRADE_STATE,
                    "Für den Empfänger fehlen eingehende Positionen.",
                    lifecycle_trade_id,
                    side,
                )

            inventory = (
                HistoricalInventoryWriteService(self._connection)
                if cutover_schema_available(self._connection)
                else InventoryWriteService(self._connection)
            )
            for position in positions:
                arguments = {}
                if isinstance(inventory, HistoricalInventoryWriteService):
                    arguments = {
                        "event_key": (
                            f"trade-receipt:{lifecycle_trade_id}:"
                            f"{side}:{position['id']}"
                        ),
                        "source_type": "trade_receipt",
                    }
                mutation = inventory.add(
                    actor_user_id,
                    position["album_id"],
                    position["sticker_code"],
                    position["quantity"],
                    **arguments,
                )
                expected = mutation.previous_quantity + position["quantity"]
                if not mutation.allowed or mutation.quantity != expected:
                    raise _RejectedReceipt(
                        TradeReceiptCode.TRANSACTION_ERROR,
                        "Der Empfangsbestand konnte nicht atomar eingebucht werden.",
                        lifecycle_trade_id,
                        side,
                    )

            status, completed = finalize_received_side(
                self._connection,
                trade,
                actor_user_id,
                side,
                on_completed=on_completed,
            )

            self._connection.commit()
            return self._result(
                TradeReceiptCode.RECEIVED,
                trade_request_id,
                lifecycle_trade_id,
                side,
                status[timestamp_column],
                completed,
                (
                    "Beide Sendungen wurden empfangen; der Trade ist abgeschlossen."
                    if completed
                    else "Der eigene Empfang wurde bestätigt und eingebucht."
                ),
            )
        except _RejectedReceipt as rejected:
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
                TradeReceiptCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Die Empfangsbestätigung wurde vollständig zurückgerollt.",
            )
