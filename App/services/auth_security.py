"""S32 authentication, password migration, and persistent login throttling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import hmac
import sqlite3
from typing import Callable

from werkzeug.security import check_password_hash, generate_password_hash


CANONICAL_PASSWORD_METHOD = "scrypt:32768:8:1"
LEGACY_PASSWORD_SCHEME = "legacy_plaintext"
WERKZEUG_PASSWORD_SCHEME = "werkzeug_scrypt"
LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCK_DURATION = timedelta(minutes=15)


class AuthenticationCode(str, Enum):
    AUTHENTICATED = "authenticated"
    REACTIVATION_REQUIRED = "reactivation_required"
    INVALID_CREDENTIALS = "invalid_credentials"
    THROTTLED = "throttled"


@dataclass(frozen=True)
class AuthenticationResult:
    code: AuthenticationCode
    user_id: int | None = None
    username: str | None = None
    auth_version: int | None = None
    account_state: str | None = None
    password_upgraded: bool = False


def auth_schema_available(connection: sqlite3.Connection) -> bool:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    return {"password_scheme", "auth_version"}.issubset(columns)


def throttle_schema_available(connection: sqlite3.Connection) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='login_throttle'"
    ).fetchone() is not None


def canonical_password_hash(password: str) -> str:
    return generate_password_hash(password, method=CANONICAL_PASSWORD_METHOD)


def is_canonical_password_hash(value: str) -> bool:
    return str(value or "").split("$", 1)[0] == CANONICAL_PASSWORD_METHOD


def verify_password(password_value: str, password_scheme: str, candidate: str) -> bool:
    if password_scheme == LEGACY_PASSWORD_SCHEME:
        return hmac.compare_digest(str(password_value or ""), str(candidate or ""))
    if password_scheme == WERKZEUG_PASSWORD_SCHEME:
        try:
            return check_password_hash(str(password_value or ""), str(candidate or ""))
        except (TypeError, ValueError):
            return False
    return False


def _utc_now(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _db_timestamp(value: datetime) -> str:
    return _utc_now(value).strftime("%Y-%m-%d %H:%M:%S")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError):
        return None


class LoginThrottleService:
    def __init__(
        self,
        connection: sqlite3.Connection,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self.connection = connection
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def normalized_username(username: str) -> str:
        return str(username or "").strip().casefold()

    def _key(self, username: str, client_ip: str) -> tuple[str, str]:
        return self.normalized_username(username), str(client_ip or "unknown")

    def is_blocked(self, username: str, client_ip: str) -> bool:
        if not throttle_schema_available(self.connection):
            return False
        key = self._key(username, client_ip)
        row = self.connection.execute(
            """
            SELECT locked_until
            FROM login_throttle
            WHERE normalized_username=? AND client_ip=?
            """,
            key,
        ).fetchone()
        locked_until = _parse_timestamp(row[0]) if row else None
        return bool(locked_until and locked_until > _utc_now(self.now_provider()))

    def record_failure(self, username: str, client_ip: str) -> None:
        if not throttle_schema_available(self.connection):
            return
        key = self._key(username, client_ip)
        now = _utc_now(self.now_provider())
        row = self.connection.execute(
            """
            SELECT failure_count, window_started_at, locked_until
            FROM login_throttle
            WHERE normalized_username=? AND client_ip=?
            """,
            key,
        ).fetchone()

        window_started = _parse_timestamp(row[1]) if row else None
        if row is None or window_started is None or now - window_started >= LOGIN_WINDOW:
            failure_count = 1
            window_started = now
        else:
            failure_count = int(row[0]) + 1

        locked_until = now + LOGIN_LOCK_DURATION if failure_count >= LOGIN_FAILURE_LIMIT else None
        self.connection.execute(
            """
            INSERT INTO login_throttle
                (normalized_username, client_ip, failure_count,
                 window_started_at, locked_until, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(normalized_username, client_ip) DO UPDATE SET
                failure_count=excluded.failure_count,
                window_started_at=excluded.window_started_at,
                locked_until=excluded.locked_until,
                updated_at=excluded.updated_at
            """,
            (
                key[0], key[1], failure_count, _db_timestamp(window_started),
                _db_timestamp(locked_until) if locked_until else None,
                _db_timestamp(now),
            ),
        )

    def reset(self, username: str, client_ip: str) -> None:
        if not throttle_schema_available(self.connection):
            return
        self.connection.execute(
            "DELETE FROM login_throttle WHERE normalized_username=? AND client_ip=?",
            self._key(username, client_ip),
        )


class AuthSecurityService:
    def __init__(
        self,
        connection: sqlite3.Connection,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self.connection = connection
        self.throttle = LoginThrottleService(connection, now_provider=now_provider)

    def authenticate(
        self, username: str, password: str, client_ip: str
    ) -> AuthenticationResult:
        username = str(username or "").strip()
        password = str(password or "")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if self.throttle.is_blocked(username, client_ip):
                self.connection.rollback()
                return AuthenticationResult(AuthenticationCode.THROTTLED)

            schema_available = auth_schema_available(self.connection)
            lifecycle_available = "account_state" in {
                row[1] for row in self.connection.execute("PRAGMA table_info(users)")
            }
            select_fields = (
                "id, username, password, password_scheme, auth_version"
                + (", account_state" if lifecycle_available else "")
                if schema_available else
                "id, username, password"
            )
            user = self.connection.execute(
                f"SELECT {select_fields} FROM users WHERE username=?",
                (username,),
            ).fetchone()
            scheme = (
                user["password_scheme"] if user and schema_available
                else LEGACY_PASSWORD_SCHEME
            )
            valid = bool(user) and verify_password(user["password"], scheme, password)
            if not valid:
                self.throttle.record_failure(username, client_ip)
                self.connection.commit()
                return AuthenticationResult(AuthenticationCode.INVALID_CREDENTIALS)

            upgraded = False
            auth_version = int(user["auth_version"]) if schema_available else 1
            account_state = user["account_state"] if lifecycle_available else "active"
            if schema_available and (
                scheme == LEGACY_PASSWORD_SCHEME
                or not is_canonical_password_hash(user["password"])
            ):
                self.connection.execute(
                    """
                    UPDATE users
                    SET password=?, password_scheme=?
                    WHERE id=?
                    """,
                    (canonical_password_hash(password), WERKZEUG_PASSWORD_SCHEME, user["id"]),
                )
                upgraded = True

            self.throttle.reset(username, client_ip)
            self.connection.commit()
            authentication_code = (
                AuthenticationCode.AUTHENTICATED
                if account_state == "active"
                else AuthenticationCode.REACTIVATION_REQUIRED
                if account_state == "deactivated"
                else AuthenticationCode.INVALID_CREDENTIALS
            )
            return AuthenticationResult(
                authentication_code,
                user_id=int(user["id"]) if authentication_code != AuthenticationCode.INVALID_CREDENTIALS else None,
                username=user["username"] if authentication_code != AuthenticationCode.INVALID_CREDENTIALS else None,
                auth_version=auth_version if authentication_code != AuthenticationCode.INVALID_CREDENTIALS else None,
                account_state=account_state,
                password_upgraded=upgraded,
            )
        except Exception:
            self.connection.rollback()
            raise

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> int | None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            if not auth_schema_available(self.connection):
                self.connection.rollback()
                return None
            user = self.connection.execute(
                """
                SELECT password, password_scheme, auth_version
                FROM users WHERE id=?
                """,
                (user_id,),
            ).fetchone()
            if not user or not verify_password(
                user["password"], user["password_scheme"], current_password
            ):
                self.connection.rollback()
                return None
            next_version = int(user["auth_version"]) + 1
            self.connection.execute(
                """
                UPDATE users
                SET password=?, password_scheme=?, auth_version=?
                WHERE id=?
                """,
                (
                    canonical_password_hash(new_password),
                    WERKZEUG_PASSWORD_SCHEME,
                    next_version,
                    user_id,
                ),
            )
            self.connection.commit()
            return next_version
        except Exception:
            self.connection.rollback()
            raise

    def password_matches(self, user_id: int, candidate: str) -> bool:
        schema_available = auth_schema_available(self.connection)
        fields = "password, password_scheme" if schema_available else "password"
        user = self.connection.execute(
            f"SELECT {fields} FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not user:
            return False
        scheme = user["password_scheme"] if schema_available else LEGACY_PASSWORD_SCHEME
        return verify_password(user["password"], scheme, candidate)
