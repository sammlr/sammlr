from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import ceil

from services.typed_notifications import (
    TypedNotificationService,
    typed_notification_schema_available,
)


NOTIFICATION_PAGE_SIZE = 25
READ_NOTIFICATION_RETENTION_DAYS = 30


class NotificationOpenCode(str, Enum):
    OPENED = "opened"
    TARGET_UNAVAILABLE = "target_unavailable"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class NotificationHistoryItemDTO:
    id: int
    title: str
    body: str
    created_at: str
    is_read: bool
    notification_type: str
    target_path: str | None
    target_available: bool
    is_legacy: bool


@dataclass(frozen=True)
class NotificationHistoryPageDTO:
    items: tuple[NotificationHistoryItemDTO, ...]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool
    unread_count: int = 0
    read_state_changed: int = 0
    retention_deleted: int = 0


@dataclass(frozen=True)
class NotificationOpenResultDTO:
    code: NotificationOpenCode
    target_path: str | None
    read_state_changed: bool


class NotificationHistoryService:
    """Small-inbox read-state and retention over the existing notification table."""

    def __init__(self, connection, now_provider=None):
        self._connection = connection
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def unread_count(self, user_id):
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id=? AND is_read=0
            """,
            (user_id,),
        ).fetchone()
        return int(row["count"] if row else 0)

    def page(self, user_id, requested_page=1):
        total_items = int(self._connection.execute(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id=?",
            (user_id,),
        ).fetchone()["count"])
        total_pages = max(1, ceil(total_items / NOTIFICATION_PAGE_SIZE))
        page = min(max(int(requested_page), 1), total_pages)
        rows = self._connection.execute(
            """
            SELECT * FROM notifications
            WHERE user_id=?
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (
                user_id,
                NOTIFICATION_PAGE_SIZE,
                (page - 1) * NOTIFICATION_PAGE_SIZE,
            ),
        ).fetchall()
        return NotificationHistoryPageDTO(
            items=tuple(self._history_item(row, user_id) for row in rows),
            page=page,
            page_size=NOTIFICATION_PAGE_SIZE,
            total_items=total_items,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
            unread_count=self.unread_count(user_id),
        )

    def open_page(self, user_id, requested_page=1):
        """Clean and open one concrete inbox page in one user-scoped transaction."""
        cutoff = self._retention_cutoff()
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            deleted = self._connection.execute(
                """
                DELETE FROM notifications
                WHERE user_id=? AND is_read=1 AND created_at < ?
                """,
                (user_id, cutoff),
            ).rowcount
            total_items = int(self._connection.execute(
                "SELECT COUNT(*) AS count FROM notifications WHERE user_id=?",
                (user_id,),
            ).fetchone()["count"])
            total_pages = max(1, ceil(total_items / NOTIFICATION_PAGE_SIZE))
            try:
                requested_page = int(requested_page)
            except (TypeError, ValueError):
                requested_page = 1
            page = min(max(requested_page, 1), total_pages)
            rows = self._connection.execute(
                """
                SELECT * FROM notifications
                WHERE user_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    user_id,
                    NOTIFICATION_PAGE_SIZE,
                    (page - 1) * NOTIFICATION_PAGE_SIZE,
                ),
            ).fetchall()
            delivered_ids = tuple(int(row["id"]) for row in rows)
            changed = 0
            if delivered_ids:
                placeholders = ",".join("?" for _ in delivered_ids)
                changed = self._connection.execute(
                    f"""
                    UPDATE notifications
                    SET is_read=1
                    WHERE user_id=? AND is_read=0 AND id IN ({placeholders})
                    """,
                    (user_id, *delivered_ids),
                ).rowcount
                rows = self._connection.execute(
                    f"""
                    SELECT * FROM notifications
                    WHERE user_id=? AND id IN ({placeholders})
                    ORDER BY created_at DESC, id DESC
                    """,
                    (user_id, *delivered_ids),
                ).fetchall()
            unread_count = self.unread_count(user_id)
            result = NotificationHistoryPageDTO(
                items=tuple(self._history_item(row, user_id) for row in rows),
                page=page,
                page_size=NOTIFICATION_PAGE_SIZE,
                total_items=total_items,
                total_pages=total_pages,
                has_previous=page > 1,
                has_next=page < total_pages,
                unread_count=unread_count,
                read_state_changed=changed,
                retention_deleted=deleted,
            )
            self._connection.commit()
            return result
        except Exception:
            self._connection.rollback()
            raise

    def _retention_cutoff(self):
        now = self._now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        cutoff = now.astimezone(timezone.utc) - timedelta(
            days=READ_NOTIFICATION_RETENTION_DAYS
        )
        return cutoff.strftime("%Y-%m-%d %H:%M:%S")

    def mark_read(self, notification_id, user_id):
        cursor = self._connection.execute(
            """
            UPDATE notifications
            SET is_read=1
            WHERE id=? AND user_id=? AND is_read=0
            """,
            (notification_id, user_id),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def open_target(self, notification_id, user_id):
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                "SELECT * FROM notifications WHERE id=? AND user_id=?",
                (notification_id, user_id),
            ).fetchone()
            if row is None:
                self._connection.rollback()
                return NotificationOpenResultDTO(
                    NotificationOpenCode.NOT_FOUND, None, False
                )
            target_path = self._target_path(row, user_id)
            if target_path is None:
                self._connection.rollback()
                return NotificationOpenResultDTO(
                    NotificationOpenCode.TARGET_UNAVAILABLE, None, False
                )
            cursor = self._connection.execute(
                """
                UPDATE notifications
                SET is_read=1
                WHERE id=? AND user_id=? AND is_read=0
                """,
                (notification_id, user_id),
            )
            self._connection.commit()
            return NotificationOpenResultDTO(
                NotificationOpenCode.OPENED,
                target_path,
                cursor.rowcount == 1,
            )
        except Exception:
            self._connection.rollback()
            raise

    def _history_item(self, row, user_id):
        schema_available = typed_notification_schema_available(self._connection)
        notification_type = (
            row["notification_type"] if schema_available else "legacy"
        )
        is_legacy = notification_type == "legacy"
        target_path = self._target_path(row, user_id) if not is_legacy else None
        return NotificationHistoryItemDTO(
            id=row["id"],
            title=row["title"] or "Benachrichtigung",
            body=row["body"] or "",
            created_at=row["created_at"] or "",
            is_read=bool(row["is_read"]),
            notification_type=notification_type,
            target_path=target_path,
            target_available=target_path is not None,
            is_legacy=is_legacy,
        )

    def _target_path(self, row, user_id):
        if not typed_notification_schema_available(self._connection):
            return None
        notification = TypedNotificationService.from_row(row)
        if notification.notification_type == "legacy":
            return None
        return TypedNotificationService(self._connection).target_path_for(
            notification, user_id
        )
