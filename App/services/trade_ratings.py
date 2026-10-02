from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import sqlite3


class TradeRatingCode(str, Enum):
    READY = "ready"
    CREATED = "created"
    ALREADY_RATED = "already_rated"
    NOT_QUALIFIED = "not_qualified"
    UNAUTHORIZED = "unauthorized"
    INVALID_STARS = "invalid_stars"


@dataclass(frozen=True)
class TradeRatingStateDTO:
    code: TradeRatingCode
    legacy_trade_request_id: int
    trade_id: int | None
    rater_user_id: int
    rated_user_id: int | None
    stars: int | None
    created_at: str | None = None


@dataclass(frozen=True)
class TradeRatingSummaryDTO:
    rated_user_id: int
    rating_count: int
    average: Decimal | None

    @property
    def average_text(self):
        return f"{self.average:.1f}" if self.average is not None else None


def trade_rating_schema_available(connection):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='trade_ratings'"
    ).fetchone() is not None


class TradeRatingService:
    """S28 final post-lifecycle ratings and read-only profile aggregation."""

    def __init__(self, connection):
        self._connection = connection
        self._schema_available = trade_rating_schema_available(connection)

    @property
    def schema_available(self):
        return self._schema_available

    @staticmethod
    def _valid_stars(stars):
        return isinstance(stars, int) and not isinstance(stars, bool) and 1 <= stars <= 5

    def _lifecycle_trade(self, legacy_trade_request_id):
        return self._connection.execute(
            """
            SELECT id, legacy_trade_request_id, requester_user_id,
                   partner_user_id, lifecycle_state
            FROM trades
            WHERE legacy_trade_request_id=?
            """,
            (legacy_trade_request_id,),
        ).fetchone()

    @staticmethod
    def _counterpart(trade, actor_user_id):
        if actor_user_id == trade["requester_user_id"]:
            return trade["partner_user_id"]
        if actor_user_id == trade["partner_user_id"]:
            return trade["requester_user_id"]
        return None

    def state_for_request(self, legacy_trade_request_id, actor_user_id):
        if not self._schema_available:
            return TradeRatingStateDTO(
                TradeRatingCode.NOT_QUALIFIED,
                legacy_trade_request_id,
                None,
                actor_user_id,
                None,
                None,
            )
        trade = self._lifecycle_trade(legacy_trade_request_id)
        if trade is None:
            return TradeRatingStateDTO(
                TradeRatingCode.NOT_QUALIFIED,
                legacy_trade_request_id,
                None,
                actor_user_id,
                None,
                None,
            )
        rated_user_id = self._counterpart(trade, actor_user_id)
        if rated_user_id is None:
            return TradeRatingStateDTO(
                TradeRatingCode.UNAUTHORIZED,
                legacy_trade_request_id,
                trade["id"],
                actor_user_id,
                None,
                None,
            )
        if trade["lifecycle_state"] not in {
            "completed",
            "closed_with_problem",
            "problem_resolved_after_close",
        }:
            return TradeRatingStateDTO(
                TradeRatingCode.NOT_QUALIFIED,
                legacy_trade_request_id,
                trade["id"],
                actor_user_id,
                rated_user_id,
                None,
            )
        existing = self._connection.execute(
            """
            SELECT stars, created_at FROM trade_ratings
            WHERE trade_id=? AND rater_user_id=?
            """,
            (trade["id"], actor_user_id),
        ).fetchone()
        return TradeRatingStateDTO(
            (
                TradeRatingCode.ALREADY_RATED
                if existing is not None else TradeRatingCode.READY
            ),
            legacy_trade_request_id,
            trade["id"],
            actor_user_id,
            rated_user_id,
            existing["stars"] if existing is not None else None,
            existing["created_at"] if existing is not None else None,
        )

    def create(self, legacy_trade_request_id, actor_user_id, stars):
        if not self._valid_stars(stars):
            return TradeRatingStateDTO(
                TradeRatingCode.INVALID_STARS,
                legacy_trade_request_id,
                None,
                actor_user_id,
                None,
                None,
            )
        if not self._schema_available:
            return TradeRatingStateDTO(
                TradeRatingCode.NOT_QUALIFIED,
                legacy_trade_request_id,
                None,
                actor_user_id,
                None,
                None,
            )

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            state = self.state_for_request(
                legacy_trade_request_id, actor_user_id
            )
            if state.code != TradeRatingCode.READY:
                self._connection.rollback()
                return state
            self._connection.execute(
                """
                INSERT INTO trade_ratings
                    (trade_id, rater_user_id, rated_user_id, stars)
                VALUES (?, ?, ?, ?)
                """,
                (
                    state.trade_id,
                    actor_user_id,
                    state.rated_user_id,
                    stars,
                ),
            )
            from services.community import UserActivityService
            UserActivityService(self._connection).touch(actor_user_id)
            self._connection.commit()
            return TradeRatingStateDTO(
                TradeRatingCode.CREATED,
                legacy_trade_request_id,
                state.trade_id,
                actor_user_id,
                state.rated_user_id,
                stars,
            )
        except sqlite3.IntegrityError:
            self._connection.rollback()
            return self.state_for_request(
                legacy_trade_request_id, actor_user_id
            )
        except Exception:
            self._connection.rollback()
            raise

    def summary_for_user(self, rated_user_id):
        if not self._schema_available:
            return TradeRatingSummaryDTO(rated_user_id, 0, None)
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS rating_count, COALESCE(SUM(stars), 0) AS total
            FROM trade_ratings
            WHERE rated_user_id=?
            """,
            (rated_user_id,),
        ).fetchone()
        count = int(row["rating_count"])
        average = None
        if count:
            average = (Decimal(int(row["total"])) / Decimal(count)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        return TradeRatingSummaryDTO(rated_user_id, count, average)
