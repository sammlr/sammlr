from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import sqlite3

from services.typed_notifications import TypedNotificationService


FRIENDSHIP_REQUEST_STATUSES = frozenset({
    "pending", "accepted", "declined", "cancelled"
})


def community_schema_available(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {row[0] for row in rows}
    return {
        "friendship_requests", "friendships", "blocks", "user_activity"
    }.issubset(names)


def canonical_pair(first_user_id, second_user_id):
    first = int(first_user_id)
    second = int(second_user_id)
    return (first, second) if first < second else (second, first)


class CommunityMutationCode(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    REMOVED = "removed"
    BLOCKED = "blocked"
    UNBLOCKED = "unblocked"
    ALREADY_EXISTS = "already_exists"
    ALREADY_BLOCKED = "already_blocked"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    BLOCKED_INTERACTION = "blocked_interaction"
    INVALID_OPERATION = "invalid_operation"


@dataclass(frozen=True)
class CommunityMutationResultDTO:
    code: CommunityMutationCode
    changed: bool
    friendship_request_id: int | None = None
    friendship_id: int | None = None


@dataclass(frozen=True)
class CommunityUserDTO:
    user_id: int
    username: str
    display_name: str | None
    already_friends: bool
    activity_label: str | None = None


class UserActivityService:
    """Coarse S29 activity projection, written only after domain mutations."""

    def __init__(self, connection, now_provider=None):
        self._connection = connection
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    @property
    def schema_available(self):
        return self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_activity'"
        ).fetchone() is not None

    def _now(self):
        value = self._now_provider()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def touch(self, user_id):
        if not self.schema_available:
            return False
        timestamp = self._now().replace(microsecond=0).isoformat()
        self._connection.execute(
            """
            INSERT INTO user_activity (user_id, last_active_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_active_at=excluded.last_active_at
            """,
            (int(user_id), timestamp),
        )
        return True

    def label_for(self, user_id, viewer_user_id):
        if not community_schema_available(self._connection):
            return None
        if not CommunityService(self._connection).are_friends(
            user_id, viewer_user_id
        ):
            return None
        row = self._connection.execute(
            "SELECT last_active_at FROM user_activity WHERE user_id=?",
            (int(user_id),),
        ).fetchone()
        return self.label_from_timestamp(
            row["last_active_at"] if row is not None else None
        )

    def label_from_timestamp(self, timestamp):
        if not timestamp:
            return "Länger nicht aktiv"
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = (self._now() - parsed.astimezone(timezone.utc)).total_seconds() / 86400
        if age_days < 1:
            return "Heute aktiv"
        if age_days <= 7:
            return "Diese Woche aktiv"
        if age_days <= 30:
            return "Kürzlich aktiv"
        return "Länger nicht aktiv"


class CommunityService:
    """Transactional S29 friendship/block policy and read projection."""

    def __init__(self, connection, now_provider=None):
        self._connection = connection
        self._activity = UserActivityService(connection, now_provider)

    @property
    def schema_available(self):
        return community_schema_available(self._connection)

    def are_friends(self, first_user_id, second_user_id):
        if not self.schema_available or int(first_user_id) == int(second_user_id):
            return False
        low, high = canonical_pair(first_user_id, second_user_id)
        return self._connection.execute(
            "SELECT 1 FROM friendships WHERE user_low_id=? AND user_high_id=?",
            (low, high),
        ).fetchone() is not None

    def is_blocked_between(self, first_user_id, second_user_id):
        if not self.schema_available or int(first_user_id) == int(second_user_id):
            return False
        return self._connection.execute(
            """
            SELECT 1 FROM blocks
            WHERE (blocker_user_id=? AND blocked_user_id=?)
               OR (blocker_user_id=? AND blocked_user_id=?)
            """,
            (first_user_id, second_user_id, second_user_id, first_user_id),
        ).fetchone() is not None

    def can_start_interaction(self, first_user_id, second_user_id):
        return (
            int(first_user_id) != int(second_user_id)
            and self._user_exists(first_user_id)
            and self._user_exists(second_user_id)
            and not self.is_blocked_between(first_user_id, second_user_id)
        )

    def interactable_user_ids(self, first_user_id, candidate_user_ids):
        """Batch equivalent of ``can_start_interaction`` for read projections."""

        try:
            first = int(first_user_id)
            candidates = tuple(sorted({
                int(user_id) for user_id in candidate_user_ids
                if int(user_id) != first
            }))
        except (TypeError, ValueError):
            return frozenset()
        if not candidates or not self._user_exists(first):
            return frozenset()

        placeholders = ", ".join("?" for _ in candidates)
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        state_filter = " AND account_state='active'" if "account_state" in columns else ""
        existing = {
            int(row[0])
            for row in self._connection.execute(
                f"SELECT id FROM users WHERE id IN ({placeholders}){state_filter}",
                candidates,
            ).fetchall()
        }
        if not self.schema_available or not existing:
            return frozenset(existing)

        existing_placeholders = ", ".join("?" for _ in existing)
        blocked = {
            int(row[0])
            for row in self._connection.execute(
                f"""
                SELECT CASE
                    WHEN blocker_user_id=? THEN blocked_user_id
                    ELSE blocker_user_id
                END AS other_user_id
                FROM blocks
                WHERE (blocker_user_id=? AND blocked_user_id IN ({existing_placeholders}))
                   OR (blocked_user_id=? AND blocker_user_id IN ({existing_placeholders}))
                """,
                (first, first, *sorted(existing), first, *sorted(existing)),
            ).fetchall()
        }
        return frozenset(existing - blocked)

    def _user_exists(self, user_id):
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        state_filter = " AND account_state='active'" if "account_state" in columns else ""
        return self._connection.execute(
            f"SELECT 1 FROM users WHERE id=?{state_filter}", (int(user_id),)
        ).fetchone() is not None

    def _friendship(self, first_user_id, second_user_id):
        low, high = canonical_pair(first_user_id, second_user_id)
        return self._connection.execute(
            "SELECT * FROM friendships WHERE user_low_id=? AND user_high_id=?",
            (low, high),
        ).fetchone()

    def _notify_request(self, request_id, requester_id, recipient_id):
        TypedNotificationService(self._connection).create(
            recipient_id,
            "friend_request",
            "Neue Freundschaftsanfrage",
            "Jemand möchte sich mit dir vernetzen.",
            "friendship",
            request_id,
            request_id,
        )

    def send_request(self, requester_id, recipient_id):
        requester_id, recipient_id = int(requester_id), int(recipient_id)
        if (
            not self.schema_available or requester_id == recipient_id
            or not self._user_exists(requester_id)
            or not self._user_exists(recipient_id)
        ):
            return CommunityMutationResultDTO(CommunityMutationCode.INVALID_OPERATION, False)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            if self.is_blocked_between(requester_id, recipient_id):
                self._connection.rollback()
                return CommunityMutationResultDTO(CommunityMutationCode.BLOCKED_INTERACTION, False)
            existing_friendship = self._friendship(requester_id, recipient_id)
            if existing_friendship is not None:
                self._connection.rollback()
                return CommunityMutationResultDTO(
                    CommunityMutationCode.ALREADY_EXISTS, False,
                    friendship_id=existing_friendship["id"],
                )
            same = self._connection.execute(
                """SELECT id FROM friendship_requests
                   WHERE requester_user_id=? AND recipient_user_id=? AND status='pending'""",
                (requester_id, recipient_id),
            ).fetchone()
            if same is not None:
                self._connection.rollback()
                return CommunityMutationResultDTO(
                    CommunityMutationCode.ALREADY_EXISTS, False,
                    friendship_request_id=same["id"],
                )
            reciprocal = self._connection.execute(
                """SELECT id FROM friendship_requests
                   WHERE requester_user_id=? AND recipient_user_id=? AND status='pending'""",
                (recipient_id, requester_id),
            ).fetchone()
            cursor = self._connection.execute(
                """INSERT INTO friendship_requests
                   (requester_user_id, recipient_user_id, status)
                   VALUES (?, ?, 'pending')""",
                (requester_id, recipient_id),
            )
            request_id = cursor.lastrowid
            if reciprocal is None:
                self._notify_request(request_id, requester_id, recipient_id)
                self._activity.touch(requester_id)
                self._connection.commit()
                return CommunityMutationResultDTO(
                    CommunityMutationCode.CREATED, True, request_id
                )
            low, high = canonical_pair(requester_id, recipient_id)
            friendship_cursor = self._connection.execute(
                "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
                (low, high),
            )
            friendship_id = friendship_cursor.lastrowid
            self._connection.execute(
                """UPDATE friendship_requests
                   SET status='accepted', updated_at=CURRENT_TIMESTAMP
                   WHERE id IN (?, ?)""",
                (reciprocal["id"], request_id),
            )
            self._connection.execute(
                """DELETE FROM notifications
                   WHERE notification_type='friend_request'
                     AND target_type='friendship' AND target_id=?""",
                (reciprocal["id"],),
            )
            self._activity.touch(requester_id)
            self._connection.commit()
            return CommunityMutationResultDTO(
                CommunityMutationCode.ACCEPTED, True, request_id, friendship_id
            )
        except sqlite3.IntegrityError:
            self._connection.rollback()
            return CommunityMutationResultDTO(CommunityMutationCode.ALREADY_EXISTS, False)
        except Exception:
            self._connection.rollback()
            raise

    def _transition_request(self, request_id, actor_id, role, new_status):
        column = "recipient_user_id" if role == "recipient" else "requester_user_id"
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            row = self._connection.execute(
                f"SELECT * FROM friendship_requests WHERE id=? AND {column}=? AND status='pending'",
                (int(request_id), int(actor_id)),
            ).fetchone()
            if row is None:
                self._connection.rollback()
                return CommunityMutationResultDTO(CommunityMutationCode.UNAUTHORIZED, False)
            friendship_id = None
            if new_status == "accepted":
                if self.is_blocked_between(row["requester_user_id"], row["recipient_user_id"]):
                    self._connection.rollback()
                    return CommunityMutationResultDTO(CommunityMutationCode.BLOCKED_INTERACTION, False)
                low, high = canonical_pair(row["requester_user_id"], row["recipient_user_id"])
                cursor = self._connection.execute(
                    "INSERT INTO friendships (user_low_id, user_high_id) VALUES (?, ?)",
                    (low, high),
                )
                friendship_id = cursor.lastrowid
            self._connection.execute(
                "UPDATE friendship_requests SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (new_status, int(request_id)),
            )
            self._activity.touch(actor_id)
            self._connection.commit()
            code = CommunityMutationCode(new_status)
            return CommunityMutationResultDTO(code, True, int(request_id), friendship_id)
        except sqlite3.IntegrityError:
            self._connection.rollback()
            return CommunityMutationResultDTO(CommunityMutationCode.ALREADY_EXISTS, False)
        except Exception:
            self._connection.rollback()
            raise

    def accept_request(self, request_id, actor_id):
        return self._transition_request(request_id, actor_id, "recipient", "accepted")

    def decline_request(self, request_id, actor_id):
        return self._transition_request(request_id, actor_id, "recipient", "declined")

    def cancel_request(self, request_id, actor_id):
        return self._transition_request(request_id, actor_id, "requester", "cancelled")

    def remove_friendship(self, other_user_id, actor_id):
        if not self.schema_available or int(other_user_id) == int(actor_id):
            return CommunityMutationResultDTO(CommunityMutationCode.INVALID_OPERATION, False)
        low, high = canonical_pair(other_user_id, actor_id)
        self._connection.execute("BEGIN IMMEDIATE")
        cursor = self._connection.execute(
            "DELETE FROM friendships WHERE user_low_id=? AND user_high_id=?",
            (low, high),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            return CommunityMutationResultDTO(CommunityMutationCode.NOT_FOUND, False)
        self._activity.touch(actor_id)
        self._connection.commit()
        return CommunityMutationResultDTO(CommunityMutationCode.REMOVED, True)

    def block(self, actor_id, other_user_id):
        actor_id, other_user_id = int(actor_id), int(other_user_id)
        if (
            not self.schema_available or actor_id == other_user_id
            or not self._user_exists(other_user_id)
        ):
            return CommunityMutationResultDTO(CommunityMutationCode.INVALID_OPERATION, False)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            inserted = self._connection.execute(
                "INSERT OR IGNORE INTO blocks (blocker_user_id, blocked_user_id) VALUES (?, ?)",
                (actor_id, other_user_id),
            )
            if inserted.rowcount != 1:
                self._connection.rollback()
                return CommunityMutationResultDTO(CommunityMutationCode.ALREADY_BLOCKED, False)
            low, high = canonical_pair(actor_id, other_user_id)
            self._connection.execute(
                "DELETE FROM friendships WHERE user_low_id=? AND user_high_id=?",
                (low, high),
            )
            self._connection.execute(
                """UPDATE friendship_requests
                   SET status='cancelled', updated_at=CURRENT_TIMESTAMP
                   WHERE status='pending' AND
                     ((requester_user_id=? AND recipient_user_id=?) OR
                      (requester_user_id=? AND recipient_user_id=?))""",
                (actor_id, other_user_id, other_user_id, actor_id),
            )
            # V21 pending bindings need the same atomic bilateral release as
            # decline/withdraw. Older schemas retain their original cancel path.
            v1_schema = any(r[1] == 'contract_type' for r in
                            self._connection.execute('PRAGMA table_info(trade_requests)'))
            if v1_schema:
                from services.smartdeal_release import SmartDealReleaseService
                from services.smartdeal_expiry import utc_instant
                from datetime import datetime, timezone
                release = SmartDealReleaseService(self._connection)
                now = utc_instant(datetime.now(timezone.utc))
                pending = self._connection.execute("""SELECT id FROM trade_requests
                    WHERE contract_type='smartdeal_v1' AND status='open' AND accepted_at IS NULL
                    AND ((from_user_id=? AND to_user_id=?) OR (from_user_id=? AND to_user_id=?))""",
                    (actor_id, other_user_id, other_user_id, actor_id)).fetchall()
                for row in pending:
                    release._release_locked(row['id'], 'blocked', actor_id, now)
            self._connection.execute(
                """UPDATE trade_requests SET status='cancelled'
                   WHERE status='open' AND
                     ((from_user_id=? AND to_user_id=?) OR
                      (from_user_id=? AND to_user_id=?))"""
                + (" AND contract_type='legacy'" if v1_schema else ""),
                (actor_id, other_user_id, other_user_id, actor_id),
            )
            self._activity.touch(actor_id)
            self._connection.commit()
            return CommunityMutationResultDTO(CommunityMutationCode.BLOCKED, True)
        except Exception:
            self._connection.rollback()
            raise

    def unblock(self, actor_id, other_user_id):
        if not self.schema_available:
            return CommunityMutationResultDTO(CommunityMutationCode.NOT_FOUND, False)
        self._connection.execute("BEGIN IMMEDIATE")
        cursor = self._connection.execute(
            "DELETE FROM blocks WHERE blocker_user_id=? AND blocked_user_id=?",
            (int(actor_id), int(other_user_id)),
        )
        if cursor.rowcount != 1:
            self._connection.rollback()
            return CommunityMutationResultDTO(CommunityMutationCode.NOT_FOUND, False)
        self._activity.touch(actor_id)
        self._connection.commit()
        return CommunityMutationResultDTO(CommunityMutationCode.UNBLOCKED, True)

    def search(self, actor_id, prefix, limit=20):
        if not self.schema_available:
            return ()
        prefix = str(prefix or "").strip()
        if not prefix:
            return ()
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_filter = " AND account_state='active'" if "account_state" in columns else ""
        rows = self._connection.execute(
            f"""
            SELECT id, username, name,
                   EXISTS (
                     SELECT 1 FROM friendships f
                     WHERE (f.user_low_id=? AND f.user_high_id=users.id)
                        OR (f.user_high_id=? AND f.user_low_id=users.id)
                   ) AS already_friends
            FROM users
            WHERE id<>?
              AND substr(username, 1, length(?))=? COLLATE NOCASE
              {active_filter}
              AND NOT EXISTS (
                SELECT 1 FROM blocks b
                WHERE (b.blocker_user_id=? AND b.blocked_user_id=users.id)
                   OR (b.blocker_user_id=users.id AND b.blocked_user_id=?)
              )
            ORDER BY username COLLATE NOCASE, id
            LIMIT ?
            """,
            (
                int(actor_id), int(actor_id), int(actor_id), prefix, prefix,
                int(actor_id), int(actor_id),
                max(0, min(int(limit), 20)),
            ),
        ).fetchall()
        return tuple(
            CommunityUserDTO(
                row["id"], row["username"], (row["name"] or "").strip() or None,
                bool(row["already_friends"]),
            )
            for row in rows
        )

    def friends(self, actor_id):
        if not self.schema_available:
            return ()
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_filter = " AND users.account_state='active'" if "account_state" in columns else ""
        rows = self._connection.execute(
            f"""
            SELECT users.id, users.username, users.name,
                   activity.last_active_at
            FROM friendships f
            JOIN users ON users.id=CASE
                WHEN f.user_low_id=? THEN f.user_high_id ELSE f.user_low_id END
            LEFT JOIN user_activity activity ON activity.user_id=users.id
            WHERE (f.user_low_id=? OR f.user_high_id=?) {active_filter}
            ORDER BY users.username COLLATE NOCASE, users.id
            """,
            (int(actor_id), int(actor_id), int(actor_id)),
        ).fetchall()
        return tuple(
            CommunityUserDTO(
                row["id"], row["username"], (row["name"] or "").strip() or None,
                True, self._activity.label_from_timestamp(row["last_active_at"]),
            ) for row in rows
        )

    def pending_requests(self, actor_id):
        if not self.schema_available:
            return (), ()
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_filter = " AND u.account_state='active'" if "account_state" in columns else ""
        incoming = self._connection.execute(
            f"""SELECT r.*, u.username FROM friendship_requests r
               JOIN users u ON u.id=r.requester_user_id
               WHERE r.recipient_user_id=? AND r.status='pending' {active_filter}
               ORDER BY r.created_at, r.id""",
            (int(actor_id),),
        ).fetchall()
        outgoing = self._connection.execute(
            f"""SELECT r.*, u.username FROM friendship_requests r
               JOIN users u ON u.id=r.recipient_user_id
               WHERE r.requester_user_id=? AND r.status='pending' {active_filter}
               ORDER BY r.created_at, r.id""",
            (int(actor_id),),
        ).fetchall()
        return tuple(incoming), tuple(outgoing)
