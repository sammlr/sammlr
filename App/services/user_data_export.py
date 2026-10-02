"""S36 synchronous, read-only export of one user's Sammlr data."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any


EXPORT_FORMAT_VERSION = "sammlr-user-export-v1"


@dataclass(frozen=True)
class UserDataExportDTO:
    subject_user_id: int
    profile: dict[str, Any]
    account: dict[str, Any]
    favorites: dict[str, Any]
    albums: tuple[dict[str, Any], ...]
    inventory: dict[str, Any]
    trades: dict[str, Any]
    ratings: dict[str, Any]
    notifications: tuple[dict[str, Any], ...]
    trophies: tuple[dict[str, Any], ...]
    feed_events: tuple[dict[str, Any], ...]
    community: dict[str, Any]
    login_security: tuple[dict[str, Any], ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "format_version": EXPORT_FORMAT_VERSION,
            "subject_user_id": self.subject_user_id,
            "profile": self.profile,
            "account": self.account,
            "favorites": self.favorites,
            "albums": list(self.albums),
            "inventory": self.inventory,
            "trades": self.trades,
            "ratings": self.ratings,
            "notifications": list(self.notifications),
            "trophies": list(self.trophies),
            "feed_events": list(self.feed_events),
            "community": self.community,
            "login_security": list(self.login_security),
        }

    def to_json_bytes(self) -> bytes:
        content = json.dumps(
            self.to_document(),
            ensure_ascii=False,
            indent=2,
            separators=(",", ": "),
        )
        return (content + "\n").encode("utf-8")


class UserDataExportService:
    """Build a deterministic export without mutating or committing anything."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def export_for_user(self, user_id: int) -> UserDataExportDTO | None:
        subject_id = int(user_id)
        user = self.connection.execute(
            """
            SELECT id, username, name, favorite_album_id, account_state,
                   profile_privacy
            FROM users
            WHERE id=?
            """,
            (subject_id,),
        ).fetchone()
        if user is None:
            return None

        profile = {
            "user_id": subject_id,
            "username": user["username"],
            "display_name": user["name"],
        }
        account = {
            "account_state": user["account_state"],
            "profile_privacy": user["profile_privacy"],
        }

        favorite_album_id = user["favorite_album_id"]
        favorite_album = None
        if favorite_album_id is not None:
            favorite_album = self._one(
                """
                SELECT id AS album_id, name, season, total, complete, cover
                FROM albums WHERE id=?
                """,
                (favorite_album_id,),
            )
        favorites = {
            "favorite_album_id": favorite_album_id,
            "favorite_album": favorite_album,
        }

        albums = self._rows(
            """
            SELECT
                membership.id AS membership_id,
                membership.album_id,
                album.name,
                album.season,
                album.total,
                album.complete,
                album.cover,
                membership.visibility,
                membership.trade_pool_enabled
            FROM user_albums membership
            JOIN albums album ON album.id=membership.album_id
            WHERE membership.user_id=?
            ORDER BY membership.album_id, membership.id
            """,
            (subject_id,),
            boolean_fields=("trade_pool_enabled",),
        )

        stickers = self._rows(
            """
            SELECT id, album_id, sticker_code, status, quantity, duplicates
            FROM stickers
            WHERE user_id=?
            ORDER BY album_id, sticker_code COLLATE NOCASE, sticker_code, id
            """,
            (subject_id,),
        )
        inventory = {
            "summary": {
                "sticker_positions": len(stickers),
                "physical_quantity": sum(int(row["quantity"] or 0) for row in stickers),
                "duplicates": sum(int(row["duplicates"] or 0) for row in stickers),
            },
            "stickers": list(stickers),
        }

        trade_requests = self._rows(
            """
            SELECT id, album_id, from_user_id, to_user_id, give_codes, get_codes,
                   status, created_at, from_confirmed, to_confirmed
            FROM trade_requests
            WHERE from_user_id=? OR to_user_id=?
            ORDER BY created_at, id
            """,
            (subject_id, subject_id),
            json_fields=("give_codes", "get_codes"),
            boolean_fields=("from_confirmed", "to_confirmed"),
        )
        lifecycle_rows = self._rows(
            """
            SELECT id, legacy_trade_request_id, requester_user_id,
                   partner_user_id, lifecycle_state, created_at, updated_at,
                   completed_at
            FROM trades
            WHERE requester_user_id=? OR partner_user_id=?
            ORDER BY created_at, id
            """,
            (subject_id, subject_id),
        ) if self._table_exists("trades") else ()
        lifecycle_trades = tuple(
            self._lifecycle_trade(row) for row in lifecycle_rows
        )
        trades = {
            "requests": list(trade_requests),
            "lifecycle": list(lifecycle_trades),
        }

        ratings = {
            "given": list(self._rows(
                """
                SELECT id, trade_id, rater_user_id, rated_user_id, stars, created_at
                FROM trade_ratings
                WHERE rater_user_id=?
                ORDER BY created_at, id
                """,
                (subject_id,),
            )) if self._table_exists("trade_ratings") else [],
            "received": list(self._rows(
                """
                SELECT id, trade_id, rater_user_id, rated_user_id, stars, created_at
                FROM trade_ratings
                WHERE rated_user_id=?
                ORDER BY created_at, id
                """,
                (subject_id,),
            )) if self._table_exists("trade_ratings") else [],
        }

        notifications = self._rows(
            """
            SELECT id, title, body, is_read, created_at, notification_type,
                   target_type, target_id, source_event_id, dedupe_key
            FROM notifications
            WHERE user_id=?
            ORDER BY created_at, id
            """,
            (subject_id,),
            boolean_fields=("is_read",),
        )
        trophies = self._rows(
            """
            SELECT id, album_id, trophy_name, unlocked_at
            FROM unlocked_trophies
            WHERE user_id=?
            ORDER BY unlocked_at, album_id, trophy_name, id
            """,
            (subject_id,),
        )
        feed_events = self._rows(
            """
            SELECT id, event_key, event_type, actor_user_id, user_album_id,
                   user_id, album_id, target_type, target_key, occurred_at
            FROM feed_events
            WHERE actor_user_id=?
            ORDER BY occurred_at, event_key, id
            """,
            (subject_id,),
        ) if self._table_exists("feed_events") else ()

        friendships = self._rows(
            """
            SELECT id, user_low_id, user_high_id, status, created_at
            FROM friendships
            WHERE user_low_id=? OR user_high_id=?
            ORDER BY created_at, id
            """,
            (subject_id, subject_id),
        ) if self._table_exists("friendships") else ()
        friendship_requests = self._rows(
            """
            SELECT id, requester_user_id, recipient_user_id, status,
                   created_at, updated_at
            FROM friendship_requests
            WHERE requester_user_id=? OR recipient_user_id=?
            ORDER BY created_at, id
            """,
            (subject_id, subject_id),
        ) if self._table_exists("friendship_requests") else ()
        blocks = self._rows(
            """
            SELECT id, blocker_user_id, blocked_user_id, created_at
            FROM blocks
            WHERE blocker_user_id=? OR blocked_user_id=?
            ORDER BY created_at, id
            """,
            (subject_id, subject_id),
        ) if self._table_exists("blocks") else ()
        activity = self._one(
            "SELECT user_id, last_active_at FROM user_activity WHERE user_id=?",
            (subject_id,),
        ) if self._table_exists("user_activity") else None
        community = {
            "friendships": list(friendships),
            "friendship_requests": list(friendship_requests),
            "blocks": list(blocks),
            "activity": activity,
        }

        login_security = ()
        if self._table_exists("login_throttle"):
            login_security = self._rows(
                """
                SELECT normalized_username, client_ip, failure_count,
                       window_started_at, locked_until, updated_at
                FROM login_throttle
                WHERE normalized_username=?
                ORDER BY client_ip
                """,
                (str(user["username"] or "").strip().casefold(),),
            )

        return UserDataExportDTO(
            subject_user_id=subject_id,
            profile=profile,
            account=account,
            favorites=favorites,
            albums=albums,
            inventory=inventory,
            trades=trades,
            ratings=ratings,
            notifications=notifications,
            trophies=trophies,
            feed_events=feed_events,
            community=community,
            login_security=login_security,
        )

    def _lifecycle_trade(self, trade: dict[str, Any]) -> dict[str, Any]:
        trade_id = int(trade["id"])
        result = dict(trade)
        result["positions"] = list(self._rows(
            """
            SELECT id, from_user_id, to_user_id, album_id, sticker_code,
                   quantity, created_at
            FROM trade_positions
            WHERE trade_id=?
            ORDER BY from_user_id, to_user_id, album_id,
                     sticker_code COLLATE NOCASE, sticker_code, id
            """,
            (trade_id,),
        ))
        result["events"] = list(self._rows(
            """
            SELECT id, event_type, actor_user_id, payload_json, occurred_at
            FROM trade_events
            WHERE trade_id=?
            ORDER BY occurred_at, id
            """,
            (trade_id,),
            json_fields=("payload_json",),
        ))
        result["reservations"] = list(self._rows(
            """
            SELECT id, trade_position_id, user_id, album_id, sticker_code,
                   quantity, state, created_at, released_at, release_reason
            FROM trade_reservations
            WHERE trade_id=?
            ORDER BY id
            """,
            (trade_id,),
        )) if self._table_exists("trade_reservations") else []
        result["shipping"] = self._one(
            """
            SELECT requester_shipped, requester_shipped_at, partner_shipped,
                   partner_shipped_at, updated_at
            FROM trade_shipping_status WHERE trade_id=?
            """,
            (trade_id,),
            boolean_fields=("requester_shipped", "partner_shipped"),
        ) if self._table_exists("trade_shipping_status") else None
        result["receipt"] = self._one(
            """
            SELECT requester_received, requester_received_at, partner_received,
                   partner_received_at, updated_at
            FROM trade_receipt_status WHERE trade_id=?
            """,
            (trade_id,),
            boolean_fields=("requester_received", "partner_received"),
        ) if self._table_exists("trade_receipt_status") else None
        reports = self._rows(
            """
            SELECT id, receiver_user_id, receiver_side, state, shipment_lost,
                   created_at, resolved_at
            FROM trade_receipt_reports
            WHERE trade_id=?
            ORDER BY created_at, id
            """,
            (trade_id,),
            boolean_fields=("shipment_lost",),
        ) if self._table_exists("trade_receipt_reports") else ()
        report_documents = []
        for report in reports:
            document = dict(report)
            document["positions"] = list(self._rows(
                """
                SELECT id, trade_position_id, expected_quantity,
                       initial_received_quantity, resolution_received_quantity,
                       problem_type, state, created_at, resolved_at
                FROM trade_receipt_report_positions
                WHERE report_id=?
                ORDER BY trade_position_id, id
                """,
                (report["id"],),
            ))
            report_documents.append(document)
        result["problem_history"] = report_documents
        return result

    def _table_exists(self, table: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is not None

    def _one(
        self,
        sql: str,
        parameters: tuple[Any, ...],
        *,
        json_fields: tuple[str, ...] = (),
        boolean_fields: tuple[str, ...] = (),
    ) -> dict[str, Any] | None:
        row = self.connection.execute(sql, parameters).fetchone()
        return self._document_row(row, json_fields, boolean_fields) if row else None

    def _rows(
        self,
        sql: str,
        parameters: tuple[Any, ...],
        *,
        json_fields: tuple[str, ...] = (),
        boolean_fields: tuple[str, ...] = (),
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._document_row(row, json_fields, boolean_fields)
            for row in self.connection.execute(sql, parameters).fetchall()
        )

    @staticmethod
    def _document_row(
        row: sqlite3.Row,
        json_fields: tuple[str, ...],
        boolean_fields: tuple[str, ...],
    ) -> dict[str, Any]:
        document = dict(row)
        for field in json_fields:
            value = document.get(field)
            if value is not None:
                try:
                    document[field] = json.loads(value)
                except (TypeError, ValueError):
                    document[field] = value
        for field in boolean_fields:
            value = document.get(field)
            document[field] = bool(value) if value is not None else None
        return document
