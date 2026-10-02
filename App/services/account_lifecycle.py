"""S35 account lifecycle, privacy cleanup, and export-inventory foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import sqlite3

from services.auth_security import AuthSecurityService, canonical_password_hash


ACTIVE = "active"
DEACTIVATED = "deactivated"
ANONYMIZED = "anonymized"
ANONYMIZED_DISPLAY_NAME = "Gelöschter Nutzer"
TERMINAL_REQUEST_STATES = frozenset(
    {"completed", "closed_with_problem", "failed", "declined", "cancelled", "expired", "obsolete"}
)
RUNNING_REQUEST_STATES = frozenset({"open", "accepted"})


class AccountLifecycleCode(str, Enum):
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"
    ANONYMIZED = "anonymized"
    INVALID_PASSWORD = "invalid_password"
    INVALID_STATE = "invalid_state"
    CONFIRMATION_REQUIRED = "confirmation_required"
    RUNNING_TRADES = "running_trades"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class AccountLifecycleResultDTO:
    code: AccountLifecycleCode
    changed: bool
    auth_version: int | None = None


@dataclass(frozen=True)
class AccountDataCategoryDTO:
    key: str
    record_count: int
    anonymization_action: str
    retained_for_trade_history: bool = False


@dataclass(frozen=True)
class AccountDataInventoryDTO:
    user_id: int
    account_state: str
    categories: tuple[AccountDataCategoryDTO, ...]


def account_lifecycle_schema_available(connection: sqlite3.Connection) -> bool:
    return "account_state" in {
        row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }


def public_username(username: str | None, account_state: str | None) -> str:
    return ANONYMIZED_DISPLAY_NAME if account_state == ANONYMIZED else str(username or "")


class AccountLifecycleService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def state_for(self, user_id: int) -> str | None:
        if not account_lifecycle_schema_available(self.connection):
            return ACTIVE
        row = self.connection.execute(
            "SELECT account_state FROM users WHERE id=?", (int(user_id),)
        ).fetchone()
        return str(row[0]) if row else None

    def deactivate(self, user_id: int, current_password: str) -> AccountLifecycleResultDTO:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            state = self.state_for(user_id)
            if state is None:
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.NOT_FOUND, False)
            if state != ACTIVE:
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.INVALID_STATE, False)
            if not AuthSecurityService(self.connection).password_matches(user_id, current_password):
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.INVALID_PASSWORD, False)
            row = self.connection.execute(
                "SELECT auth_version FROM users WHERE id=?", (int(user_id),)
            ).fetchone()
            next_version = int(row[0]) + 1
            self.connection.execute(
                "UPDATE users SET account_state=?, auth_version=? WHERE id=?",
                (DEACTIVATED, next_version, int(user_id)),
            )
            self.connection.commit()
            return AccountLifecycleResultDTO(
                AccountLifecycleCode.DEACTIVATED, True, next_version
            )
        except Exception:
            self.connection.rollback()
            raise

    def reactivate(self, user_id: int, expected_auth_version: int) -> AccountLifecycleResultDTO:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT account_state, auth_version FROM users WHERE id=?", (int(user_id),)
            ).fetchone()
            if row is None:
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.NOT_FOUND, False)
            if row[0] != DEACTIVATED or int(row[1]) != int(expected_auth_version):
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.INVALID_STATE, False)
            next_version = int(row[1]) + 1
            self.connection.execute(
                "UPDATE users SET account_state=?, auth_version=? WHERE id=?",
                (ACTIVE, next_version, int(user_id)),
            )
            self.connection.commit()
            return AccountLifecycleResultDTO(
                AccountLifecycleCode.REACTIVATED, True, next_version
            )
        except Exception:
            self.connection.rollback()
            raise

    def has_running_trades(self, user_id: int) -> bool:
        running = self.connection.execute(
            """
            SELECT 1 FROM trade_requests
            WHERE (from_user_id=? OR to_user_id=?)
              AND status IN ('open', 'accepted')
            LIMIT 1
            """,
            (int(user_id), int(user_id)),
        ).fetchone()
        if running is not None:
            return True
        if not self._table_exists("trades"):
            return False
        orphan_running = self.connection.execute(
            """
            SELECT 1
            FROM trades lifecycle
            LEFT JOIN trade_requests request
              ON request.id=lifecycle.legacy_trade_request_id
            WHERE (lifecycle.requester_user_id=? OR lifecycle.partner_user_id=?)
              AND request.id IS NULL
              AND lifecycle.lifecycle_state NOT IN (
                  'completed', 'closed_with_problem', 'failed', 'declined',
                  'cancelled', 'expired', 'obsolete'
              )
            LIMIT 1
            """,
            (int(user_id), int(user_id)),
        ).fetchone()
        return orphan_running is not None

    def anonymize(
        self,
        user_id: int,
        current_password: str,
        confirmed: bool,
    ) -> AccountLifecycleResultDTO:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT username, account_state, auth_version FROM users WHERE id=?",
                (int(user_id),),
            ).fetchone()
            if row is None:
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.NOT_FOUND, False)
            if row[1] != ACTIVE:
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.INVALID_STATE, False)
            if not AuthSecurityService(self.connection).password_matches(user_id, current_password):
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.INVALID_PASSWORD, False)
            if not confirmed:
                self.connection.rollback()
                return AccountLifecycleResultDTO(
                    AccountLifecycleCode.CONFIRMATION_REQUIRED, False
                )
            if self.has_running_trades(user_id):
                self.connection.rollback()
                return AccountLifecycleResultDTO(AccountLifecycleCode.RUNNING_TRADES, False)

            old_username = str(row[0] or "")
            self.connection.execute("DELETE FROM stickers WHERE user_id=?", (int(user_id),))
            self.connection.execute("DELETE FROM user_albums WHERE user_id=?", (int(user_id),))
            self.connection.execute("DELETE FROM unlocked_trophies WHERE user_id=?", (int(user_id),))
            if self._table_exists("friendship_requests"):
                self.connection.execute(
                    "DELETE FROM friendship_requests WHERE requester_user_id=? OR recipient_user_id=?",
                    (int(user_id), int(user_id)),
                )
                self.connection.execute(
                    "DELETE FROM friendships WHERE user_low_id=? OR user_high_id=?",
                    (int(user_id), int(user_id)),
                )
                self.connection.execute(
                    "DELETE FROM blocks WHERE blocker_user_id=? OR blocked_user_id=?",
                    (int(user_id), int(user_id)),
                )
                self.connection.execute("DELETE FROM user_activity WHERE user_id=?", (int(user_id),))
            self.connection.execute("DELETE FROM notifications WHERE user_id=?", (int(user_id),))
            if self._table_exists("login_throttle"):
                self.connection.execute(
                    "DELETE FROM login_throttle WHERE normalized_username=?",
                    (old_username.strip().casefold(),),
                )

            next_version = int(row[2]) + 1
            tombstone = f"__sammlr_anonymized_{int(user_id)}__"
            self.connection.execute(
                """
                UPDATE users
                SET name=NULL, favorite_album_id=NULL, username=?, password=?,
                    password_scheme='werkzeug_scrypt', auth_version=?,
                    account_state='anonymized'
                WHERE id=?
                """,
                (
                    tombstone,
                    canonical_password_hash("account-anonymized-no-login"),
                    next_version,
                    int(user_id),
                ),
            )
            self.connection.commit()
            return AccountLifecycleResultDTO(
                AccountLifecycleCode.ANONYMIZED, True, next_version
            )
        except Exception:
            self.connection.rollback()
            raise

    def _table_exists(self, name: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None


class AccountDataInventoryService:
    """Read-only S35 inventory foundation; it exports no personal data."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def for_user(self, user_id: int) -> AccountDataInventoryDTO | None:
        row = self.connection.execute(
            "SELECT account_state FROM users WHERE id=?", (int(user_id),)
        ).fetchone()
        if row is None:
            return None
        specs = (
            ("stickers", "stickers", "user_id", "delete", False),
            ("album_memberships", "user_albums", "user_id", "delete", False),
            ("trophies", "unlocked_trophies", "user_id", "delete", False),
            ("notifications", "notifications", "user_id", "delete", False),
            ("trade_requests_sent", "trade_requests", "from_user_id", "retain_anonymized", True),
            ("trade_requests_received", "trade_requests", "to_user_id", "retain_anonymized", True),
            ("ratings_given", "trade_ratings", "rater_user_id", "retain_anonymized", True),
            ("ratings_received", "trade_ratings", "rated_user_id", "retain_without_profile", True),
        )
        categories = []
        for key, table, column, action, retained in specs:
            count = 0
            if self._table_exists(table):
                count = int(self.connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column}=?", (int(user_id),)
                ).fetchone()[0])
            categories.append(AccountDataCategoryDTO(key, count, action, retained))
        return AccountDataInventoryDTO(int(user_id), str(row[0]), tuple(categories))

    def _table_exists(self, name: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None
