from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json

from services.inventory import InventoryReadService
from services.album_privacy import AlbumPrivacyService


SMART_REQUEST_MARKER = -22
SMART_REQUEST_LIMIT = 3
SMART_REQUEST_LIFETIME = timedelta(hours=48)
SMART_ACCEPTED_EVENT = "smart_request_accepted"


class SmartTradeRequestCode(str, Enum):
    READY = "ready"
    CREATED = "created"
    LIMIT_REACHED = "limit_reached"
    PACKAGE_CHANGED = "package_changed"
    OBSOLETE = "obsolete"
    EXPIRED = "expired"
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    NOT_SMART = "not_smart"


@dataclass(frozen=True)
class SmartPackageRecheckDTO:
    full_available: bool
    any_executable: bool
    unavailable_give: tuple[tuple[str, int], ...]
    unavailable_get: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class SmartTradeRequestStateDTO:
    code: SmartTradeRequestCode
    trade_request_id: int | None
    status: str | None
    expires_at: datetime | None
    recheck: SmartPackageRecheckDTO | None
    explanation: str


def is_smart_trade_request(trade):
    return bool(trade) and trade["from_confirmed"] == SMART_REQUEST_MARKER


class SmartTradeRequestService:
    """S22 orchestration over legacy TradeRequest and read-only inventory."""

    def __init__(self, connection, now_provider=None):
        self._connection = connection
        self._inventory = InventoryReadService(connection)
        self._trade_pool = AlbumPrivacyService(connection)
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _parse_created_at(value):
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _now(self):
        value = self._now_provider()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def expires_at(cls, trade):
        return cls._parse_created_at(trade["created_at"]) + SMART_REQUEST_LIFETIME

    def _is_expired(self, trade):
        return self._now() >= self.expires_at(trade)

    @staticmethod
    def _codes(trade, column):
        try:
            codes = json.loads(trade[column] or "[]")
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(codes, list) or not codes:
            return None
        return tuple(str(code) for code in codes)

    def recheck_codes(
        self,
        album_id,
        from_user_id,
        to_user_id,
        give_codes,
        get_codes,
    ):
        from services.community import CommunityService
        if not CommunityService(self._connection).can_start_interaction(
            from_user_id, to_user_id
        ):
            unavailable_give = tuple(sorted(Counter(give_codes).items(), key=lambda item: str(item[0])))
            unavailable_get = tuple(sorted(Counter(get_codes).items(), key=lambda item: str(item[0])))
            return SmartPackageRecheckDTO(False, False, unavailable_give, unavailable_get)
        give_counts = Counter(give_codes)
        get_counts = Counter(get_codes)
        if not (
            self._trade_pool.is_trade_pool_enabled(from_user_id, album_id)
            and self._trade_pool.is_trade_pool_enabled(to_user_id, album_id)
        ):
            return SmartPackageRecheckDTO(
                full_available=False,
                any_executable=False,
                unavailable_give=tuple(sorted(give_counts.items(), key=lambda item: str(item[0]))),
                unavailable_get=tuple(sorted(get_counts.items(), key=lambda item: str(item[0]))),
            )
        catalog = tuple(sorted(set(give_counts) | set(get_counts), key=str))
        sender = self._inventory.snapshot(from_user_id, album_id, catalog)
        receiver = self._inventory.snapshot(to_user_id, album_id, catalog)

        unavailable_give = tuple(
            (code, amount - sender.sticker(code).effective_available)
            for code, amount in sorted(give_counts.items(), key=lambda item: str(item[0]))
            if amount > sender.sticker(code).effective_available
        )
        unavailable_get = tuple(
            (code, amount - receiver.sticker(code).effective_available)
            for code, amount in sorted(get_counts.items(), key=lambda item: str(item[0]))
            if amount > receiver.sticker(code).effective_available
        )
        executable_give = sum(
            min(amount, sender.sticker(code).effective_available)
            for code, amount in give_counts.items()
        )
        executable_get = sum(
            min(amount, receiver.sticker(code).effective_available)
            for code, amount in get_counts.items()
        )
        return SmartPackageRecheckDTO(
            full_available=not unavailable_give and not unavailable_get,
            any_executable=executable_give > 0 and executable_get > 0,
            unavailable_give=unavailable_give,
            unavailable_get=unavailable_get,
        )

    def recheck(self, trade):
        give_codes = self._codes(trade, "give_codes")
        get_codes = self._codes(trade, "get_codes")
        if give_codes is None or get_codes is None:
            return SmartPackageRecheckDTO(False, False, (), ())
        return self.recheck_codes(
            trade["album_id"],
            trade["from_user_id"],
            trade["to_user_id"],
            give_codes,
            get_codes,
        )

    def _load(self, trade_request_id):
        return self._connection.execute(
            "SELECT * FROM trade_requests WHERE id=?",
            (trade_request_id,),
        ).fetchone()

    def inspect(self, trade_request_id, actor_user_id, *, recheck=True):
        trade = self._load(trade_request_id)
        if trade is None:
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.INVALID_REQUEST,
                trade_request_id,
                None,
                None,
                None,
                "Die Anfrage existiert nicht.",
            )
        if actor_user_id not in (trade["from_user_id"], trade["to_user_id"]):
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.UNAUTHORIZED,
                trade_request_id,
                trade["status"],
                None,
                None,
                "Die Anfrage gehört nicht zum angemeldeten Nutzer.",
            )
        if not is_smart_trade_request(trade):
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.NOT_SMART,
                trade_request_id,
                trade["status"],
                None,
                None,
                "Die Anfrage ist eine manuelle Anfrage.",
            )

        expiry = self.expires_at(trade)
        if trade["status"] == "open" and self._is_expired(trade):
            self._connection.execute(
                "UPDATE trade_requests SET status='expired' WHERE id=? AND status='open'",
                (trade_request_id,),
            )
            self._connection.commit()
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.EXPIRED,
                trade_request_id,
                "expired",
                expiry,
                None,
                "Die Smart-Anfrage ist nach 48 Stunden abgelaufen.",
            )
        if trade["status"] == "expired":
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.EXPIRED,
                trade_request_id,
                "expired",
                expiry,
                None,
                "Die Smart-Anfrage ist abgelaufen.",
            )
        if trade["status"] == "obsolete":
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.OBSOLETE,
                trade_request_id,
                "obsolete",
                expiry,
                None,
                "Das Smart-Paket ist nicht mehr ausführbar.",
            )
        if trade["status"] != "open" or not recheck:
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.READY,
                trade_request_id,
                trade["status"],
                expiry,
                None,
                "Keine S22-Änderung erforderlich.",
            )

        check = self.recheck(trade)
        if check.full_available:
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.READY,
                trade_request_id,
                "open",
                expiry,
                check,
                "Das unveränderte Smart-Paket ist vollständig verfügbar.",
            )
        if check.any_executable:
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.PACKAGE_CHANGED,
                trade_request_id,
                "open",
                expiry,
                check,
                "Das Smart-Paket ist nicht mehr vollständig verfügbar.",
            )

        self._connection.execute(
            "UPDATE trade_requests SET status='obsolete' WHERE id=? AND status='open'",
            (trade_request_id,),
        )
        from services.typed_notifications import (
            TypedNotificationService,
            typed_notification_schema_available,
        )
        try:
            if typed_notification_schema_available(self._connection):
                TypedNotificationService(
                    self._connection
                ).notify_request_unfulfillable(trade_request_id)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        return SmartTradeRequestStateDTO(
            SmartTradeRequestCode.OBSOLETE,
            trade_request_id,
            "obsolete",
            expiry,
            check,
            "Das Smart-Paket ist nicht mehr bilateral ausführbar.",
        )

    def open_count(self, from_user_id):
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM trade_requests
            WHERE from_user_id=? AND status='open' AND from_confirmed=?
            """,
            (from_user_id, SMART_REQUEST_MARKER),
        ).fetchone()
        return int(row["count"])

    def create(
        self,
        album_id,
        from_user_id,
        to_user_id,
        give_codes,
        get_codes,
        on_created=None,
    ):
        give_codes = tuple(give_codes)
        get_codes = tuple(get_codes)
        if (
            from_user_id == to_user_id
            or not give_codes
            or not get_codes
            or len(give_codes) < len(get_codes)
        ):
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.INVALID_REQUEST,
                None,
                None,
                None,
                None,
                "Das Smart-Paket ist ungültig.",
            )

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            if self.open_count(from_user_id) >= SMART_REQUEST_LIMIT:
                self._connection.rollback()
                return SmartTradeRequestStateDTO(
                    SmartTradeRequestCode.LIMIT_REACHED,
                    None,
                    None,
                    None,
                    None,
                    "Es sind bereits drei Smart-Anfragen gleichzeitig offen.",
                )

            check = self.recheck_codes(
                album_id,
                from_user_id,
                to_user_id,
                give_codes,
                get_codes,
            )
            if not check.full_available:
                self._connection.rollback()
                code = (
                    SmartTradeRequestCode.PACKAGE_CHANGED
                    if check.any_executable
                    else SmartTradeRequestCode.OBSOLETE
                )
                return SmartTradeRequestStateDTO(
                    code,
                    None,
                    None,
                    None,
                    check,
                    "Das Smart-Paket ist vor dem Absenden nicht mehr vollständig verfügbar.",
                )

            cursor = self._connection.execute(
                """
                INSERT INTO trade_requests
                    (album_id, from_user_id, to_user_id, give_codes, get_codes,
                     status, from_confirmed, to_confirmed)
                VALUES (?, ?, ?, ?, ?, 'open', ?, 0)
                """,
                (
                    album_id,
                    from_user_id,
                    to_user_id,
                    json.dumps(list(give_codes)),
                    json.dumps(list(get_codes)),
                    SMART_REQUEST_MARKER,
                ),
            )
            trade_request_id = cursor.lastrowid
            if on_created is not None:
                on_created(self._connection, trade_request_id)
            from services.community import UserActivityService
            UserActivityService(self._connection).touch(from_user_id)
            self._connection.commit()
            trade = self._load(trade_request_id)
            return SmartTradeRequestStateDTO(
                SmartTradeRequestCode.CREATED,
                trade_request_id,
                "open",
                self.expires_at(trade),
                check,
                "Die Smart-Anfrage wurde unverändert gespeichert.",
            )
        except Exception:
            self._connection.rollback()
            raise
