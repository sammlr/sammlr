from __future__ import annotations

from dataclasses import dataclass
import json


NOTIFICATION_TYPES = frozenset({
    "trade_request_created",
    "smart_trade_request_created",
    "trade_request_declined",
    "trade_shipped",
    "trade_rating_available",
    "friend_request",
    "trade_request_unfulfillable",
    "trade_problem_action_required",
    "trade_problem_terminal",
})
REQUEST_NOTIFICATION_TYPES = frozenset({
    "trade_request_created",
    "smart_trade_request_created",
    "trade_request_declined",
    "trade_request_unfulfillable",
})
FRIEND_NOTIFICATION_TYPES = frozenset({"friend_request"})
TARGET_TYPES = frozenset({"trade_request", "trade", "friendship"})


@dataclass(frozen=True)
class NotificationTargetDTO:
    target_type: str
    target_id: int


@dataclass(frozen=True)
class TypedNotificationDTO:
    id: int
    user_id: int
    title: str
    body: str
    is_read: bool
    created_at: str
    notification_type: str
    target: NotificationTargetDTO | None
    source_event_id: int | None
    dedupe_key: str | None


@dataclass(frozen=True)
class NotificationCreateResultDTO:
    notification: TypedNotificationDTO
    created: bool


def typed_notification_schema_available(connection):
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(notifications)").fetchall()
    }
    return {
        "notification_type",
        "target_type",
        "target_id",
        "source_event_id",
        "dedupe_key",
    }.issubset(columns)


class TypedNotificationService:
    """Closed-Beta notification projection over canonical domain facts."""

    def __init__(self, connection):
        self._connection = connection

    @staticmethod
    def _positive_id(value, field_name):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field_name} must be a positive integer")
        return value

    @staticmethod
    def from_row(row):
        target = None
        if row["target_type"] is not None and row["target_id"] is not None:
            target = NotificationTargetDTO(row["target_type"], row["target_id"])
        return TypedNotificationDTO(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"] or "",
            body=row["body"] or "",
            is_read=bool(row["is_read"]),
            created_at=row["created_at"],
            notification_type=row["notification_type"],
            target=target,
            source_event_id=row["source_event_id"],
            dedupe_key=row["dedupe_key"],
        )

    @staticmethod
    def dedupe_key(
        recipient_id,
        notification_type,
        target_type,
        target_id,
        source_event_id=None,
    ):
        if source_event_id is not None:
            return f"{recipient_id}:{notification_type}:{source_event_id}"
        return f"{recipient_id}:{notification_type}:{target_type}:{target_id}"

    def create(
        self,
        recipient_id,
        notification_type,
        title,
        body,
        target_type,
        target_id,
        source_event_id=None,
    ):
        if not typed_notification_schema_available(self._connection):
            raise RuntimeError("V0006 typed notification schema is not installed")
        self._positive_id(recipient_id, "recipient_id")
        self._positive_id(target_id, "target_id")
        if notification_type not in NOTIFICATION_TYPES:
            raise ValueError("unsupported S23 notification type")
        if target_type not in TARGET_TYPES:
            raise ValueError("unsupported S23 target type")
        expected_target = (
            "friendship"
            if notification_type in FRIEND_NOTIFICATION_TYPES
            else (
                "trade_request"
                if notification_type in REQUEST_NOTIFICATION_TYPES
                else "trade"
            )
        )
        if target_type != expected_target:
            raise ValueError("notification type and target type do not match")
        if source_event_id is None:
            raise ValueError("CB-008 notifications require a stable source id")
        self._positive_id(source_event_id, "source_event_id")

        key = self.dedupe_key(
            recipient_id,
            notification_type,
            target_type,
            target_id,
            source_event_id,
        )
        inserted = self._connection.execute(
            """
            INSERT OR IGNORE INTO notifications
                (user_id, title, body, is_read, notification_type,
                 target_type, target_id, source_event_id, dedupe_key)
            VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                recipient_id,
                title,
                body,
                notification_type,
                target_type,
                target_id,
                source_event_id,
                key,
            ),
        )
        row = self._connection.execute(
            "SELECT * FROM notifications WHERE dedupe_key=?",
            (key,),
        ).fetchone()
        if row is None:
            raise RuntimeError("typed notification could not be read after insert")
        return NotificationCreateResultDTO(
            notification=self.from_row(row),
            created=inserted.rowcount == 1,
        )

    def target_path_for(self, notification, actor_user_id):
        if notification.user_id != actor_user_id or notification.target is None:
            return None
        target = notification.target
        if target.target_type == "trade_request":
            row = self._connection.execute(
                """
                SELECT id FROM trade_requests
                WHERE id=? AND (from_user_id=? OR to_user_id=?)
                """,
                (target.target_id, actor_user_id, actor_user_id),
            ).fetchone()
            return f"/trades/{row['id']}" if row else None
        if target.target_type == "trade":
            row = self._connection.execute(
                """
                SELECT legacy_trade_request_id
                FROM trades
                WHERE id=? AND (requester_user_id=? OR partner_user_id=?)
                """,
                (target.target_id, actor_user_id, actor_user_id),
            ).fetchone()
            if row and row["legacy_trade_request_id"] is not None:
                return f"/trades/{row['legacy_trade_request_id']}"
        if target.target_type == "friendship":
            row = self._connection.execute(
                """
                SELECT id FROM friendship_requests request
                WHERE request.id=? AND request.recipient_user_id=?
                  AND request.status='pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM blocks block
                      WHERE (block.blocker_user_id=request.requester_user_id
                             AND block.blocked_user_id=request.recipient_user_id)
                         OR (block.blocker_user_id=request.recipient_user_id
                             AND block.blocked_user_id=request.requester_user_id)
                  )
                """,
                (target.target_id, actor_user_id),
            ).fetchone()
            return (
                f"/profil/freunde#friend-request-{row['id']}" if row else None
            )
        return None

    def _matching_event(self, trade_id, event_type, actor_user_id, side):
        rows = self._connection.execute(
            """
            SELECT * FROM trade_events
            WHERE trade_id=? AND event_type=? AND actor_user_id=?
            ORDER BY id
            """,
            (trade_id, event_type, actor_user_id),
        ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("side") == side:
                return row
        return None

    def _ensure_event(self, trade_id, event_type, actor_user_id, side):
        event = self._matching_event(
            trade_id, event_type, actor_user_id, side
        )
        if event is not None:
            return event
        cursor = self._connection.execute(
            """
            INSERT INTO trade_events
                (trade_id, event_type, actor_user_id, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                trade_id,
                event_type,
                actor_user_id,
                json.dumps({"side": side}, sort_keys=True),
            ),
        )
        return self._connection.execute(
            "SELECT * FROM trade_events WHERE id=?",
            (cursor.lastrowid,),
        ).fetchone()

    def notify_request_created(
        self, trade_request_id, sender_user_id, recipient_user_id, *, smart=False
    ):
        sender = self._connection.execute(
            "SELECT username FROM users WHERE id=?", (sender_user_id,)
        ).fetchone()
        notification_type = (
            "smart_trade_request_created" if smart else "trade_request_created"
        )
        title = "Neue Smart-Tauschanfrage" if smart else "Neue Tauschanfrage"
        body = (
            f"{sender['username']} möchte ein Smart-Paket mit dir tauschen."
            if smart
            else f"{sender['username']} möchte mit dir tauschen."
        )
        return self.create(
            recipient_user_id,
            notification_type,
            title,
            body,
            "trade_request",
            trade_request_id,
            source_event_id=trade_request_id,
        )

    def notify_request_declined(self, trade_request_id, actor_user_id):
        trade = self._connection.execute(
            """
            SELECT * FROM trade_requests
            WHERE id=? AND to_user_id=? AND status='declined'
            """,
            (trade_request_id, actor_user_id),
        ).fetchone()
        if trade is None or trade["from_user_id"] == actor_user_id:
            return None
        actor = self._connection.execute(
            "SELECT username FROM users WHERE id=?", (actor_user_id,)
        ).fetchone()
        return self.create(
            trade["from_user_id"],
            "trade_request_declined",
            "Tauschanfrage abgelehnt",
            f"{actor['username']} hat deine Tauschanfrage abgelehnt.",
            "trade_request",
            trade_request_id,
            source_event_id=trade_request_id,
        )

    def notify_request_unfulfillable(self, trade_request_id):
        trade = self._connection.execute(
            """
            SELECT * FROM trade_requests
            WHERE id=? AND status='obsolete'
            """,
            (trade_request_id,),
        ).fetchone()
        if trade is None:
            return None
        return self.create(
            trade["from_user_id"],
            "trade_request_unfulfillable",
            "Tauschanfrage nicht mehr erfüllbar",
            "Deine versendete Smart-Tauschanfrage ist nicht mehr ausführbar.",
            "trade_request",
            trade_request_id,
            source_event_id=trade_request_id,
        )

    def notify_rating_available(self, trade_request_id, actor_user_id):
        lifecycle = self._connection.execute(
            """
            SELECT id, requester_user_id, partner_user_id
            FROM trades WHERE legacy_trade_request_id=?
            """,
            (trade_request_id,),
        ).fetchone()
        if lifecycle is None:
            return None
        if actor_user_id == lifecycle["requester_user_id"]:
            recipient_id = lifecycle["partner_user_id"]
        elif actor_user_id == lifecycle["partner_user_id"]:
            recipient_id = lifecycle["requester_user_id"]
        else:
            return None
        if recipient_id == actor_user_id:
            return None
        from services.trade_ratings import TradeRatingCode, TradeRatingService
        rating_state = TradeRatingService(self._connection).state_for_request(
            trade_request_id, recipient_id
        )
        if rating_state.code != TradeRatingCode.READY:
            return None
        return self.create(
            recipient_id,
            "trade_rating_available",
            "Bewertung möglich",
            "Du kannst deinen Tauschpartner jetzt bewerten.",
            "trade",
            lifecycle["id"],
            source_event_id=lifecycle["id"],
        )

    def _problem_context(self, trade_request_id, report_id, actor_user_id):
        return self._connection.execute(
            """
            SELECT report.id AS report_id, report.state AS report_state,
                   report.receiver_user_id, request.status AS request_status,
                   trade.id AS lifecycle_trade_id, trade.lifecycle_state,
                   trade.requester_user_id, trade.partner_user_id
            FROM trade_receipt_reports report
            JOIN trades trade ON trade.id=report.trade_id
            JOIN trade_requests request ON request.id=trade.legacy_trade_request_id
            WHERE request.id=? AND report.id=? AND report.receiver_user_id=?
            """,
            (trade_request_id, report_id, actor_user_id),
        ).fetchone()

    @staticmethod
    def _problem_recipient(context, actor_user_id):
        if actor_user_id == context["requester_user_id"]:
            return context["partner_user_id"]
        if actor_user_id == context["partner_user_id"]:
            return context["requester_user_id"]
        return None

    def notify_problem_action_required(
        self, trade_request_id, report_id, actor_user_id
    ):
        context = self._problem_context(
            trade_request_id, report_id, actor_user_id
        )
        if context is None or context["report_state"] != "open":
            return None
        recipient_id = self._problem_recipient(context, actor_user_id)
        if recipient_id is None or recipient_id == actor_user_id:
            return None
        return self.create(
            recipient_id,
            "trade_problem_action_required",
            "Problem beim Trade gemeldet",
            "Dein Tauschpartner hat ein Problem mit der Lieferung gemeldet.",
            "trade",
            context["lifecycle_trade_id"],
            source_event_id=report_id,
        )

    def notify_problem_terminal(self, trade_request_id, report_id, actor_user_id):
        context = self._problem_context(
            trade_request_id, report_id, actor_user_id
        )
        if (
            context is None
            or context["lifecycle_state"] != "closed_with_problem"
            or context["request_status"] != "completed"
        ):
            return None
        recipient_id = self._problem_recipient(context, actor_user_id)
        if recipient_id is None or recipient_id == actor_user_id:
            return None
        return self.create(
            recipient_id,
            "trade_problem_terminal",
            "Trade mit Problem beendet",
            "Dein Tauschpartner hat den Trade mit dokumentiertem Problem beendet.",
            "trade",
            context["lifecycle_trade_id"],
            source_event_id=report_id,
        )

    def notify_shipped(self, trade_request_id, actor_user_id):
        started_transaction = not self._connection.in_transaction
        if started_transaction:
            self._connection.execute("BEGIN IMMEDIATE")
        try:
            trade = self._connection.execute(
                """
                SELECT r.*, t.id AS lifecycle_trade_id,
                       t.requester_user_id, t.partner_user_id,
                       shipping.requester_shipped, shipping.partner_shipped
                FROM trade_requests r
                JOIN trades t ON t.legacy_trade_request_id=r.id
                JOIN trade_shipping_status shipping ON shipping.trade_id=t.id
                WHERE r.id=?
                """,
                (trade_request_id,),
            ).fetchone()
            if trade is None:
                if started_transaction:
                    self._connection.rollback()
                return None
            if actor_user_id == trade["requester_user_id"]:
                side = "requester"
                recipient_id = trade["partner_user_id"]
                shipped = trade["requester_shipped"]
            elif actor_user_id == trade["partner_user_id"]:
                side = "partner"
                recipient_id = trade["requester_user_id"]
                shipped = trade["partner_shipped"]
            else:
                if started_transaction:
                    self._connection.rollback()
                return None
            if not shipped:
                if started_transaction:
                    self._connection.rollback()
                return None
            event = self._ensure_event(
                trade["lifecycle_trade_id"],
                "shipment_confirmed",
                actor_user_id,
                side,
            )
            actor = self._connection.execute(
                "SELECT username FROM users WHERE id=?", (actor_user_id,)
            ).fetchone()
            result = self.create(
                recipient_id,
                "trade_shipped",
                "Tauschpartner hat versendet",
                f"{actor['username']} hat den Versand bestätigt.",
                "trade",
                trade["lifecycle_trade_id"],
                source_event_id=event["id"],
            )
            if started_transaction:
                self._connection.commit()
            return result
        except Exception:
            if started_transaction:
                self._connection.rollback()
            raise
