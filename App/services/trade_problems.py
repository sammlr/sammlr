from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json

from services.inventory_write import InventoryWriteService
from services.history_cutover import (
    HistoricalInventoryWriteService,
    cutover_schema_available,
)
from services.trade_receipt import (
    finalize_received_side,
    receipt_schema_available,
)


class TradeProblemType(str, Enum):
    MISSING = "missing"
    WRONG_STICKER = "wrong_sticker"
    DAMAGED = "damaged"
    SHIPMENT_LOST = "shipment_lost"


class TradeProblemCode(str, Enum):
    FULLY_RECEIVED = "FULLY_RECEIVED"
    PARTIAL_RECEIPT_RECORDED = "PARTIAL_RECEIPT_RECORDED"
    ALREADY_IDENTICAL = "ALREADY_IDENTICAL"
    PROBLEM_RESOLVED = "PROBLEM_RESOLVED"
    CLOSED_WITH_PROBLEM = "CLOSED_WITH_PROBLEM"
    PROBLEM_RESOLVED_AFTER_CLOSE = "PROBLEM_RESOLVED_AFTER_CLOSE"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    CONFLICTING_REPORT = "CONFLICTING_REPORT"
    NOT_SHIPPED = "NOT_SHIPPED"
    INVALID_TRADE_STATE = "INVALID_TRADE_STATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    TRANSACTION_ERROR = "TRANSACTION_ERROR"


@dataclass(frozen=True)
class PartialReceiptInputDTO:
    trade_position_id: int
    correct_received_quantity: int
    problem_type: TradeProblemType | str | None = None


@dataclass(frozen=True)
class TradeProblemResultDTO:
    code: TradeProblemCode
    trade_request_id: int
    lifecycle_trade_id: int | None
    report_id: int | None
    side: str | None
    booked_quantity: int
    open_quantity: int
    trade_completed: bool
    explanation: str

    @property
    def changed(self):
        return self.code in {
            TradeProblemCode.FULLY_RECEIVED,
            TradeProblemCode.PARTIAL_RECEIPT_RECORDED,
            TradeProblemCode.PROBLEM_RESOLVED,
            TradeProblemCode.CLOSED_WITH_PROBLEM,
            TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE,
        }

    @property
    def idempotent(self):
        return self.code is TradeProblemCode.ALREADY_IDENTICAL

    @property
    def completed(self):
        return self.trade_completed


@dataclass(frozen=True)
class TradeProblemPositionDTO:
    trade_position_id: int
    album_id: str
    sticker_code: str
    expected_quantity: int
    initial_received_quantity: int
    resolution_received_quantity: int
    problem_type: str | None
    state: str
    created_at: str
    resolved_at: str | None

    @property
    def booked_quantity(self):
        return self.initial_received_quantity + self.resolution_received_quantity

    @property
    def open_quantity(self):
        return self.expected_quantity - self.booked_quantity


@dataclass(frozen=True)
class TradeProblemReportDTO:
    report_id: int
    trade_request_id: int
    lifecycle_trade_id: int
    receiver_user_id: int
    receiver_side: str
    state: str
    shipment_lost: bool
    created_at: str
    resolved_at: str | None
    positions: tuple[TradeProblemPositionDTO, ...]
    closed_at: str | None = None
    closed_by_user_id: int | None = None
    resolved_after_close_at: str | None = None

    @property
    def open_quantity(self):
        return sum(position.open_quantity for position in self.positions)

    @property
    def booked_quantity(self):
        return sum(position.booked_quantity for position in self.positions)


class _RejectedProblem(Exception):
    def __init__(self, code, explanation, lifecycle_trade_id=None, side=None):
        super().__init__(explanation)
        self.code = code
        self.explanation = explanation
        self.lifecycle_trade_id = lifecycle_trade_id
        self.side = side


def problem_schema_available(connection):
    if not receipt_schema_available(connection):
        return False
    rows = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table'
          AND name IN (
              'trade_receipt_reports',
              'trade_receipt_report_positions'
          )
        """
    ).fetchall()
    return {row[0] for row in rows} == {
        "trade_receipt_reports",
        "trade_receipt_report_positions",
    }


def problem_reports_for_trade(connection, trade_request_id):
    if not problem_schema_available(connection):
        return ()
    report_rows = connection.execute(
        """
        SELECT r.*, t.legacy_trade_request_id
        FROM trade_receipt_reports r
        JOIN trades t ON t.id=r.trade_id
        WHERE t.legacy_trade_request_id=?
        ORDER BY r.id
        """,
        (trade_request_id,),
    ).fetchall()
    reports = []
    for report in report_rows:
        history_rows = connection.execute(
            """
            SELECT event_type, actor_user_id, payload_json, occurred_at
            FROM trade_events
            WHERE trade_id=?
              AND event_type IN (
                  'problem_trade_closed',
                  'problem_resolved_after_close'
              )
            ORDER BY id
            """,
            (report["trade_id"],),
        ).fetchall()
        closed_at = None
        closed_by_user_id = None
        resolved_after_close_at = None
        for event in history_rows:
            try:
                payload = json.loads(event["payload_json"] or "{}")
            except (TypeError, ValueError):
                payload = {}
            if payload.get("report_id") != report["id"]:
                continue
            if event["event_type"] == "problem_trade_closed":
                closed_at = event["occurred_at"]
                closed_by_user_id = event["actor_user_id"]
            elif event["event_type"] == "problem_resolved_after_close":
                resolved_after_close_at = event["occurred_at"]
        position_rows = connection.execute(
            """
            SELECT rp.*, p.album_id, p.sticker_code
            FROM trade_receipt_report_positions rp
            JOIN trade_positions p ON p.id=rp.trade_position_id
            WHERE rp.report_id=?
            ORDER BY p.id
            """,
            (report["id"],),
        ).fetchall()
        positions = tuple(
            TradeProblemPositionDTO(
                trade_position_id=row["trade_position_id"],
                album_id=row["album_id"],
                sticker_code=row["sticker_code"],
                expected_quantity=row["expected_quantity"],
                initial_received_quantity=row["initial_received_quantity"],
                resolution_received_quantity=row["resolution_received_quantity"],
                problem_type=row["problem_type"],
                state=row["state"],
                created_at=row["created_at"],
                resolved_at=row["resolved_at"],
            )
            for row in position_rows
        )
        reports.append(
            TradeProblemReportDTO(
                report_id=report["id"],
                trade_request_id=report["legacy_trade_request_id"],
                lifecycle_trade_id=report["trade_id"],
                receiver_user_id=report["receiver_user_id"],
                receiver_side=report["receiver_side"],
                state=report["state"],
                shipment_lost=bool(report["shipment_lost"]),
                created_at=report["created_at"],
                resolved_at=report["resolved_at"],
                positions=positions,
                closed_at=closed_at,
                closed_by_user_id=closed_by_user_id,
                resolved_after_close_at=resolved_after_close_at,
            )
        )
    return tuple(reports)


class TradeProblemService:
    """Records exact partial receipt truth and resolves only expected remainders."""

    def __init__(self, connection):
        self._connection = connection

    def _result(
        self,
        code,
        trade_request_id,
        lifecycle_trade_id=None,
        report_id=None,
        side=None,
        booked_quantity=0,
        open_quantity=0,
        trade_completed=False,
        explanation="",
    ):
        return TradeProblemResultDTO(
            code=code,
            trade_request_id=trade_request_id,
            lifecycle_trade_id=lifecycle_trade_id,
            report_id=report_id,
            side=side,
            booked_quantity=booked_quantity,
            open_quantity=open_quantity,
            trade_completed=trade_completed,
            explanation=explanation,
        )

    def _trade(self, trade_request_id):
        return self._connection.execute(
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

    @staticmethod
    def _side(trade, actor_user_id):
        if actor_user_id == trade["requester_user_id"]:
            return "requester", "partner_shipped", "requester_received"
        if actor_user_id == trade["partner_user_id"]:
            return "partner", "requester_shipped", "partner_received"
        raise _RejectedProblem(
            TradeProblemCode.UNAUTHORIZED,
            "Nur der tatsächliche Empfänger darf diese Lieferung dokumentieren.",
            trade["lifecycle_trade_id"],
        )

    def _positions(self, trade, actor_user_id):
        positions = self._connection.execute(
            """
            SELECT * FROM trade_positions
            WHERE trade_id=? AND to_user_id=?
            ORDER BY id
            """,
            (trade["lifecycle_trade_id"], actor_user_id),
        ).fetchall()
        if not positions:
            raise _RejectedProblem(
                TradeProblemCode.INVALID_TRADE_STATE,
                "Für den Empfänger fehlen erwartete Tradepositionen.",
                trade["lifecycle_trade_id"],
            )
        return positions

    def _normalize(self, positions, inputs):
        expected_by_id = {position["id"]: position for position in positions}
        normalized = {}
        try:
            candidates = tuple(inputs)
        except TypeError as error:
            raise _RejectedProblem(
                TradeProblemCode.INVALID_QUANTITY,
                "Die Empfangsmengen sind ungültig.",
            ) from error

        for item in candidates:
            if not isinstance(item, PartialReceiptInputDTO):
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_QUANTITY,
                    "Die Empfangsmengen sind ungültig.",
                )
            if item.trade_position_id in normalized:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_QUANTITY,
                    "Eine erwartete Position wurde mehrfach übergeben.",
                )
            position = expected_by_id.get(item.trade_position_id)
            quantity = item.correct_received_quantity
            if position is None or isinstance(quantity, bool) or not isinstance(quantity, int):
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_QUANTITY,
                    "Eine Position oder Menge ist ungültig.",
                )
            if quantity < 0 or quantity > position["quantity"]:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_QUANTITY,
                    "Korrekt erhalten muss zwischen 0 und erwartet liegen.",
                )
            try:
                problem_type = (
                    None
                    if item.problem_type in (None, "")
                    else TradeProblemType(item.problem_type).value
                )
            except ValueError as error:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Problemtyp ist nicht zulässig.",
                ) from error
            if quantity == position["quantity"] and problem_type is not None:
                raise _RejectedProblem(
                    TradeProblemCode.CONFLICTING_REPORT,
                    "Eine vollständig erhaltene Position darf kein Problem tragen.",
                )
            if quantity < position["quantity"] and problem_type is None:
                raise _RejectedProblem(
                    TradeProblemCode.CONFLICTING_REPORT,
                    "Für eine offene Restmenge fehlt der Problemtyp.",
                )
            normalized[item.trade_position_id] = (position, quantity, problem_type)

        if set(normalized) != set(expected_by_id):
            raise _RejectedProblem(
                TradeProblemCode.INVALID_QUANTITY,
                "Alle erwarteten Positionen müssen genau einmal dokumentiert werden.",
            )
        lost = any(
            problem_type == TradeProblemType.SHIPMENT_LOST.value
            for _, _, problem_type in normalized.values()
        )
        if lost and any(
            quantity != 0 or problem_type != TradeProblemType.SHIPMENT_LOST.value
            for _, quantity, problem_type in normalized.values()
        ):
            raise _RejectedProblem(
                TradeProblemCode.CONFLICTING_REPORT,
                "Eine verlorene Sendung muss vollständig mit Menge 0 dokumentiert werden.",
            )
        return normalized, lost

    def _existing_report(self, lifecycle_trade_id, actor_user_id):
        return self._connection.execute(
            """
            SELECT * FROM trade_receipt_reports
            WHERE trade_id=? AND receiver_user_id=?
            """,
            (lifecycle_trade_id, actor_user_id),
        ).fetchone()

    def _closed_event(self, lifecycle_trade_id, report_id):
        rows = self._connection.execute(
            """
            SELECT actor_user_id, payload_json, occurred_at
            FROM trade_events
            WHERE trade_id=? AND event_type='problem_trade_closed'
            ORDER BY id
            """,
            (lifecycle_trade_id,),
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except (TypeError, ValueError):
                payload = {}
            if payload.get("report_id") == report_id:
                return row
        return None

    def close_with_problem(self, trade_request_id, actor_user_id):
        """End an open problem trade without booking its unresolved remainder."""
        if not problem_schema_available(self._connection):
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das versionierte S17-Problemschema ist nicht installiert.",
            )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._trade(trade_request_id)
            if trade is None:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Trade besitzt keinen gültigen Problem-Lifecycle.",
                )
            lifecycle_trade_id = trade["lifecycle_trade_id"]
            side, _, _ = self._side(trade, actor_user_id)
            report = self._existing_report(lifecycle_trade_id, actor_user_id)
            if report is None:
                other_report = self._connection.execute(
                    """
                    SELECT 1 FROM trade_receipt_reports
                    WHERE trade_id=? AND state='open' LIMIT 1
                    """,
                    (lifecycle_trade_id,),
                ).fetchone()
                raise _RejectedProblem(
                    (
                        TradeProblemCode.UNAUTHORIZED
                        if other_report else TradeProblemCode.INVALID_TRADE_STATE
                    ),
                    "Nur der Empfänger mit offenem Problem darf den Trade beenden.",
                    lifecycle_trade_id,
                    side,
                )
            closed_event = self._closed_event(lifecycle_trade_id, report["id"])
            if trade["lifecycle_state"] in {
                "closed_with_problem",
                "problem_resolved_after_close",
            } and closed_event is not None:
                self._connection.commit()
                return self._result(
                    TradeProblemCode.ALREADY_IDENTICAL,
                    trade_request_id,
                    lifecycle_trade_id,
                    report["id"],
                    side,
                    open_quantity=self._report_open_quantity(report["id"]),
                    explanation="Der Trade wurde bereits mit Problem beendet.",
                )
            if (
                trade["status"] != "accepted"
                or trade["lifecycle_state"] != "problem_open"
                or report["state"] != "open"
            ):
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Nur ein aktiver eigener Problemfall kann beendet werden.",
                    lifecycle_trade_id,
                    side,
                )
            open_quantity = self._report_open_quantity(report["id"])
            if open_quantity <= 0:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Problembericht besitzt keine offene Restmenge.",
                    lifecycle_trade_id,
                    side,
                )

            self._connection.execute(
                """
                UPDATE trade_reservations
                SET state='released', released_at=CURRENT_TIMESTAMP,
                    release_reason='closed_with_problem'
                WHERE trade_id=? AND state='active'
                """,
                (lifecycle_trade_id,),
            )
            request_update = self._connection.execute(
                """
                UPDATE trade_requests SET status='completed'
                WHERE id=? AND status='accepted'
                """,
                (trade_request_id,),
            )
            if request_update.rowcount != 1:
                raise RuntimeError("problem trade request was not closed exactly once")
            lifecycle_update = self._connection.execute(
                """
                UPDATE trades
                SET lifecycle_state='closed_with_problem',
                    completed_at=COALESCE(completed_at, CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND lifecycle_state='problem_open'
                """,
                (lifecycle_trade_id,),
            )
            if lifecycle_update.rowcount != 1:
                raise RuntimeError("problem lifecycle was not closed exactly once")
            self._connection.execute(
                """
                INSERT INTO trade_events
                    (trade_id, event_type, actor_user_id, payload_json)
                VALUES (?, 'problem_trade_closed', ?, ?)
                """,
                (
                    lifecycle_trade_id,
                    actor_user_id,
                    json.dumps(
                        {
                            "report_id": report["id"],
                            "side": side,
                            "open_quantity": open_quantity,
                        }
                    ),
                ),
            )
            from services.typed_notifications import (
                TypedNotificationService,
                typed_notification_schema_available,
            )
            if typed_notification_schema_available(self._connection):
                notifications = TypedNotificationService(self._connection)
                notifications.notify_problem_terminal(
                    trade_request_id, report["id"], actor_user_id
                )
                notifications.notify_rating_available(
                    trade_request_id, actor_user_id
                )
            self._connection.commit()
            return self._result(
                TradeProblemCode.CLOSED_WITH_PROBLEM,
                trade_request_id,
                lifecycle_trade_id,
                report["id"],
                side,
                open_quantity=open_quantity,
                explanation=(
                    "Der Trade wurde mit dokumentiertem Problem beendet; "
                    "die offene Restmenge wurde nicht eingebucht."
                ),
            )
        except _RejectedProblem as rejected:
            self._connection.rollback()
            return self._result(
                rejected.code,
                trade_request_id,
                rejected.lifecycle_trade_id,
                side=rejected.side,
                explanation=rejected.explanation,
            )
        except Exception:
            self._connection.rollback()
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das Beenden des Problemtrades wurde zurückgerollt.",
            )

    def _report_open_quantity(self, report_id):
        return int(self._connection.execute(
            """
            SELECT COALESCE(SUM(
                expected_quantity
                - initial_received_quantity
                - resolution_received_quantity
            ), 0)
            FROM trade_receipt_report_positions
            WHERE report_id=?
            """,
            (report_id,),
        ).fetchone()[0])

    def _matches_existing(self, report, normalized, shipment_lost):
        if bool(report["shipment_lost"]) != shipment_lost:
            return False
        rows = self._connection.execute(
            """
            SELECT * FROM trade_receipt_report_positions
            WHERE report_id=?
            """,
            (report["id"],),
        ).fetchall()
        if {row["trade_position_id"] for row in rows} != set(normalized):
            return False
        for row in rows:
            position, quantity, problem_type = normalized[row["trade_position_id"]]
            if (
                row["expected_quantity"] != position["quantity"]
                or row["initial_received_quantity"] != quantity
                or row["problem_type"] != problem_type
            ):
                return False
        return True

    def _book(
        self, actor_user_id, normalized, quantities, *, event_key_prefix
    ):
        historical = cutover_schema_available(self._connection)
        inventory = (
            HistoricalInventoryWriteService(self._connection)
            if historical else InventoryWriteService(self._connection)
        )
        booked = 0
        for position_id, amount in quantities.items():
            if amount <= 0:
                continue
            position = normalized[position_id][0]
            arguments = {}
            if historical:
                arguments = {
                    "event_key": f"{event_key_prefix}:{position_id}",
                    "source_type": "trade_receipt",
                }
            mutation = inventory.add(
                actor_user_id,
                position["album_id"],
                position["sticker_code"],
                amount,
                **arguments,
            )
            expected = mutation.previous_quantity + amount
            if not mutation.allowed or mutation.quantity != expected:
                raise RuntimeError("partial receipt inventory booking failed")
            booked += amount
        return booked

    def report(self, trade_request_id, actor_user_id, inputs, on_completed=None):
        if not problem_schema_available(self._connection):
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das versionierte S17-Problemschema ist nicht installiert.",
            )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._trade(trade_request_id)
            if trade is None:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Trade besitzt keinen gültigen Empfangs-Lifecycle.",
                )
            lifecycle_trade_id = trade["lifecycle_trade_id"]
            side, other_shipped_column, received_column = self._side(
                trade, actor_user_id
            )
            positions = self._positions(trade, actor_user_id)
            normalized, shipment_lost = self._normalize(positions, inputs)
            self._connection.execute(
                "INSERT OR IGNORE INTO trade_receipt_status (trade_id) VALUES (?)",
                (lifecycle_trade_id,),
            )
            existing = self._existing_report(lifecycle_trade_id, actor_user_id)
            if existing is not None:
                if self._matches_existing(existing, normalized, shipment_lost):
                    open_quantity = self._connection.execute(
                        """
                        SELECT COALESCE(SUM(
                            expected_quantity
                            - initial_received_quantity
                            - resolution_received_quantity
                        ), 0)
                        FROM trade_receipt_report_positions
                        WHERE report_id=?
                        """,
                        (existing["id"],),
                    ).fetchone()[0]
                    self._connection.commit()
                    return self._result(
                        TradeProblemCode.ALREADY_IDENTICAL,
                        trade_request_id,
                        lifecycle_trade_id,
                        existing["id"],
                        side,
                        open_quantity=open_quantity,
                        trade_completed=trade["status"] == "completed",
                        explanation="Die identische Meldung wurde bereits verarbeitet.",
                    )
                raise _RejectedProblem(
                    TradeProblemCode.CONFLICTING_REPORT,
                    "Eine widersprüchliche Wiederholung überschreibt den bestehenden Bericht nicht.",
                    lifecycle_trade_id,
                    side,
                )

            receipt_status = self._connection.execute(
                "SELECT * FROM trade_receipt_status WHERE trade_id=?",
                (lifecycle_trade_id,),
            ).fetchone()
            all_full = all(
                quantity == position["quantity"] and problem_type is None
                for position, quantity, problem_type in normalized.values()
            )
            if receipt_status and receipt_status[received_column] == 1:
                if all_full:
                    self._connection.commit()
                    return self._result(
                        TradeProblemCode.ALREADY_IDENTICAL,
                        trade_request_id,
                        lifecycle_trade_id,
                        side=side,
                        trade_completed=trade["status"] == "completed",
                        explanation="Diese Empfangsseite ist bereits vollständig verarbeitet.",
                    )
                raise _RejectedProblem(
                    TradeProblemCode.CONFLICTING_REPORT,
                    "Eine abgeschlossene Empfangsseite kann nicht widersprüchlich geändert werden.",
                    lifecycle_trade_id,
                    side,
                )

            if trade["status"] != "accepted" or trade["lifecycle_state"] not in {
                "partially_shipped",
                "shipped",
                "partially_received",
                "problem_open",
            }:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Trade ist nicht in einem dokumentierbaren Empfangszustand.",
                    lifecycle_trade_id,
                    side,
                )
            if trade[other_shipped_column] != 1:
                raise _RejectedProblem(
                    TradeProblemCode.NOT_SHIPPED,
                    "Die Gegenseite hat ihren Versand noch nicht bestätigt.",
                    lifecycle_trade_id,
                    side,
                )

            quantities = {
                position_id: quantity
                for position_id, (_, quantity, _) in normalized.items()
            }
            booked = self._book(
                actor_user_id,
                normalized,
                quantities,
                event_key_prefix=(
                    f"trade-problem-initial:{lifecycle_trade_id}:{side}"
                ),
            )
            if all_full:
                _, completed = finalize_received_side(
                    self._connection,
                    trade,
                    actor_user_id,
                    side,
                    on_completed=on_completed,
                    event_payload={"source": "problem_form_full_receipt"},
                )
                self._connection.commit()
                return self._result(
                    TradeProblemCode.FULLY_RECEIVED,
                    trade_request_id,
                    lifecycle_trade_id,
                    side=side,
                    booked_quantity=booked,
                    trade_completed=completed,
                    explanation="Die Lieferung wurde vollständig eingebucht.",
                )

            report_cursor = self._connection.execute(
                """
                INSERT INTO trade_receipt_reports
                    (trade_id, receiver_user_id, receiver_side,
                     state, shipment_lost)
                VALUES (?, ?, ?, 'open', ?)
                """,
                (lifecycle_trade_id, actor_user_id, side, int(shipment_lost)),
            )
            report_id = report_cursor.lastrowid
            open_quantity = 0
            for position, quantity, problem_type in normalized.values():
                is_full = quantity == position["quantity"]
                state = "fulfilled" if is_full else "open"
                open_quantity += position["quantity"] - quantity
                self._connection.execute(
                    """
                    INSERT INTO trade_receipt_report_positions
                        (report_id, trade_position_id, expected_quantity,
                         initial_received_quantity, problem_type, state)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        position["id"],
                        position["quantity"],
                        quantity,
                        problem_type,
                        state,
                    ),
                )
            self._connection.execute(
                """
                INSERT INTO trade_events
                    (trade_id, event_type, actor_user_id, payload_json)
                VALUES (?, 'problem_reported', ?, ?)
                """,
                (
                    lifecycle_trade_id,
                    actor_user_id,
                    json.dumps(
                        {
                            "report_id": report_id,
                            "side": side,
                            "open_quantity": open_quantity,
                            "shipment_lost": shipment_lost,
                        }
                    ),
                ),
            )
            self._connection.execute(
                """
                UPDATE trades
                SET lifecycle_state='problem_open', updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (lifecycle_trade_id,),
            )
            from services.typed_notifications import (
                TypedNotificationService,
                typed_notification_schema_available,
            )
            if typed_notification_schema_available(self._connection):
                TypedNotificationService(
                    self._connection
                ).notify_problem_action_required(
                    trade_request_id, report_id, actor_user_id
                )
            self._connection.commit()
            return self._result(
                TradeProblemCode.PARTIAL_RECEIPT_RECORDED,
                trade_request_id,
                lifecycle_trade_id,
                report_id,
                side,
                booked,
                open_quantity,
                explanation="Korrekte Mengen wurden gebucht; das Problem bleibt offen.",
            )
        except _RejectedProblem as rejected:
            self._connection.rollback()
            return self._result(
                rejected.code,
                trade_request_id,
                rejected.lifecycle_trade_id,
                side=rejected.side,
                explanation=rejected.explanation,
            )
        except Exception:
            self._connection.rollback()
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Buchung und Problembericht wurden vollständig zurückgerollt.",
            )

    def resolve(self, trade_request_id, actor_user_id, on_completed=None):
        if not problem_schema_available(self._connection):
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Das versionierte S17-Problemschema ist nicht installiert.",
            )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            trade = self._trade(trade_request_id)
            if trade is None:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Trade besitzt keinen gültigen Empfangs-Lifecycle.",
                )
            lifecycle_trade_id = trade["lifecycle_trade_id"]
            side, other_shipped_column, _ = self._side(trade, actor_user_id)
            report = self._existing_report(lifecycle_trade_id, actor_user_id)
            if report is None:
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Für diese Empfangsseite existiert kein Problembericht.",
                    lifecycle_trade_id,
                    side,
                )
            if report["state"] == "resolved":
                self._connection.commit()
                return self._result(
                    TradeProblemCode.ALREADY_IDENTICAL,
                    trade_request_id,
                    lifecycle_trade_id,
                    report["id"],
                    side,
                    trade_completed=trade["status"] == "completed",
                    explanation="Der Problembericht wurde bereits vollständig aufgelöst.",
                )
            closed_event = self._closed_event(lifecycle_trade_id, report["id"])
            resolve_after_close = trade["lifecycle_state"] == "closed_with_problem"
            if resolve_after_close and (
                closed_event is None
                or closed_event["actor_user_id"] != actor_user_id
            ):
                raise _RejectedProblem(
                    TradeProblemCode.UNAUTHORIZED,
                    "Nur der Nutzer, der den Problemtrade beendet hat, darf ihn nachträglich lösen.",
                    lifecycle_trade_id,
                    side,
                )
            if trade["status"] != "accepted" or trade["lifecycle_state"] not in {
                "problem_open",
                "partially_received",
            }:
                if not (
                    resolve_after_close
                    and trade["status"] == "completed"
                    and report["state"] == "open"
                ):
                    raise _RejectedProblem(
                        TradeProblemCode.INVALID_TRADE_STATE,
                        "Der Problembericht kann in diesem Tradezustand nicht aufgelöst werden.",
                        lifecycle_trade_id,
                        side,
                    )
            if (
                not resolve_after_close
                and trade["status"] != "accepted"
            ):
                raise _RejectedProblem(
                    TradeProblemCode.INVALID_TRADE_STATE,
                    "Der Problembericht kann in diesem Tradezustand nicht aufgelöst werden.",
                    lifecycle_trade_id,
                    side,
                )
            if trade[other_shipped_column] != 1:
                raise _RejectedProblem(
                    TradeProblemCode.NOT_SHIPPED,
                    "Die Gegenseite hat ihren Versand noch nicht bestätigt.",
                    lifecycle_trade_id,
                    side,
                )

            rows = self._connection.execute(
                """
                SELECT rp.*, p.album_id, p.sticker_code, p.quantity
                FROM trade_receipt_report_positions rp
                JOIN trade_positions p ON p.id=rp.trade_position_id
                WHERE rp.report_id=? AND rp.state='open'
                ORDER BY rp.id
                """,
                (report["id"],),
            ).fetchall()
            if not rows:
                raise RuntimeError("open report has no open position")

            historical = cutover_schema_available(self._connection)
            inventory = (
                HistoricalInventoryWriteService(self._connection)
                if historical else InventoryWriteService(self._connection)
            )
            booked = 0
            for row in rows:
                remaining = row["expected_quantity"] - row["initial_received_quantity"]
                arguments = {}
                if historical:
                    arguments = {
                        "event_key": (
                            f"trade-problem-resolution:{report['id']}:"
                            f"{row['trade_position_id']}"
                        ),
                        "source_type": "trade_receipt",
                    }
                mutation = inventory.add(
                    actor_user_id,
                    row["album_id"],
                    row["sticker_code"],
                    remaining,
                    **arguments,
                )
                expected = mutation.previous_quantity + remaining
                if not mutation.allowed or mutation.quantity != expected:
                    raise RuntimeError("problem resolution inventory booking failed")
                booked += remaining
                updated = self._connection.execute(
                    """
                    UPDATE trade_receipt_report_positions
                    SET resolution_received_quantity=?, state='resolved',
                        resolved_at=CURRENT_TIMESTAMP
                    WHERE id=? AND state='open'
                    """,
                    (remaining, row["id"]),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("problem position was not resolved exactly once")

            report_update = self._connection.execute(
                """
                UPDATE trade_receipt_reports
                SET state='resolved', resolved_at=CURRENT_TIMESTAMP
                WHERE id=? AND state='open'
                """,
                (report["id"],),
            )
            if report_update.rowcount != 1:
                raise RuntimeError("problem report was not resolved exactly once")
            event_type = (
                "problem_resolved_after_close"
                if resolve_after_close else "problem_resolved"
            )
            self._connection.execute(
                """
                INSERT INTO trade_events
                    (trade_id, event_type, actor_user_id, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    lifecycle_trade_id,
                    event_type,
                    actor_user_id,
                    json.dumps(
                        {"report_id": report["id"], "booked_quantity": booked}
                    ),
                ),
            )
            if resolve_after_close:
                lifecycle_update = self._connection.execute(
                    """
                    UPDATE trades
                    SET lifecycle_state='problem_resolved_after_close',
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=? AND lifecycle_state='closed_with_problem'
                    """,
                    (lifecycle_trade_id,),
                )
                if lifecycle_update.rowcount != 1:
                    raise RuntimeError(
                        "closed problem lifecycle was not resolved exactly once"
                    )
                self._connection.commit()
                return self._result(
                    TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE,
                    trade_request_id,
                    lifecycle_trade_id,
                    report["id"],
                    side,
                    booked,
                    0,
                    False,
                    "Die offene Restmenge wurde nach Tradeende genau einmal eingebucht.",
                )
            _, completed = finalize_received_side(
                self._connection,
                trade,
                actor_user_id,
                side,
                on_completed=on_completed,
                event_payload={"source": "problem_resolved"},
            )
            self._connection.commit()
            return self._result(
                TradeProblemCode.PROBLEM_RESOLVED,
                trade_request_id,
                lifecycle_trade_id,
                report["id"],
                side,
                booked,
                0,
                completed,
                "Die offene erwartete Restmenge wurde eingebucht und aufgelöst.",
            )
        except _RejectedProblem as rejected:
            self._connection.rollback()
            return self._result(
                rejected.code,
                trade_request_id,
                rejected.lifecycle_trade_id,
                side=rejected.side,
                explanation=rejected.explanation,
            )
        except Exception:
            self._connection.rollback()
            return self._result(
                TradeProblemCode.TRANSACTION_ERROR,
                trade_request_id,
                explanation="Problemauflösung und Buchung wurden vollständig zurückgerollt.",
            )
