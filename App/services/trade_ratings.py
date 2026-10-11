from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import sqlite3
import json
from datetime import datetime, timezone, timedelta

POSITIVE_RATING_TAGS = {
    "well_packed": "Gut verpackt",
    "quick_shipping": "Schnell verschickt",
    "friendly_trade": "Freundlicher Tausch",
    "as_described": "Sticker wie beschrieben",
    "reliable": "Zuverlässig",
}


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

    def _lifecycle_schema(self):
        return bool(self._connection.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_rating_eligibility'").fetchone())

    def create_lifecycle(self, trade, actor, stars, tags, now):
        """Shared rating persistence; caller owns the serialized V1 unit of work."""
        from services.trade_lifecycle_requests import instant
        if not self._connection.in_transaction or not self._lifecycle_schema():
            raise ValueError('V1 rating transaction required')
        target = self._counterpart(trade, actor)
        if target is None or target == actor or not self._valid_stars(stars):
            raise ValueError('Invalid rating owner or stars')
        if not isinstance(tags, list) or any(not isinstance(t, str) or t not in POSITIVE_RATING_TAGS for t in tags) or len(set(tags)) != len(tags):
            raise ValueError('Only distinct positive catalog tags allowed')
        serialized = json.dumps(sorted(tags), separators=(',', ':'))
        old = self._connection.execute('''SELECT r.*,d.tags_json FROM trade_ratings r
            LEFT JOIN lifecycle_rating_details d ON d.rating_id=r.id WHERE r.trade_id=? AND r.rater_user_id=?''',
            (trade['trade_id'], actor)).fetchone()
        if old:
            if old['stars'] != stars or old['tags_json'] != serialized or old['rated_user_id'] != target:
                raise ValueError('Rating is final')
            return dict(rating=old['id'], status='submitted'), False
        eligible = self._connection.execute('SELECT eligible_at FROM lifecycle_rating_eligibility WHERE trade_id=? AND user_id=?',
                                             (trade['trade_id'], actor)).fetchone()
        if not eligible or not instant(eligible[0]) <= now < instant(eligible[0]) + timedelta(days=14):
            raise ValueError('Rating window is not open')
        rating = self._connection.execute('INSERT INTO trade_ratings(trade_id,rater_user_id,rated_user_id,stars,created_at) VALUES (?,?,?,?,?)',
            (trade['trade_id'], actor, target, stars, now.isoformat())).lastrowid
        self._connection.execute('INSERT INTO lifecycle_rating_details VALUES (?,?)', (rating, serialized))
        return dict(rating=rating, status='submitted'), True

    def lifecycle_reveal_at(self, rating, now):
        from services.trade_lifecycle_requests import instant
        other = self._connection.execute('SELECT created_at FROM trade_ratings WHERE trade_id=? AND rater_user_id=?',
                                          (rating['trade_id'], rating['rated_user_id'])).fetchone()
        if other:
            stamp = max(instant(rating['created_at']), instant(other[0]))
            return stamp if now >= stamp else None
        eligible = self._connection.execute('SELECT eligible_at FROM lifecycle_rating_eligibility WHERE trade_id=? AND user_id=?',
                                             (rating['trade_id'], rating['rated_user_id'])).fetchone()
        if eligible:
            stamp = max(instant(rating['created_at']), instant(eligible[0]) + timedelta(days=14))
            if now >= stamp:
                return stamp
        return None

    def public_rows(self, rated_user_id, now=None):
        if not self._schema_available:
            return []
        now = now or datetime.now(timezone.utc)
        rows = self._connection.execute('SELECT * FROM trade_ratings WHERE rated_user_id=? ORDER BY created_at,id', (rated_user_id,)).fetchall()
        has_contracts = self._connection.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_contracts'").fetchone()
        result = []
        for r in rows:
            v1 = has_contracts and self._connection.execute('SELECT 1 FROM lifecycle_contracts WHERE trade_id=?', (r['trade_id'],)).fetchone()
            if not v1 or (self._lifecycle_schema() and self.lifecycle_reveal_at(r, now) is not None):
                result.append(dict(r))
        return result

    def lifecycle_view(self, trade, actor, now):
        from services.trade_lifecycle_requests import instant
        eligible = self._connection.execute('SELECT eligible_at FROM lifecycle_rating_eligibility WHERE trade_id=? AND user_id=?',
                                             (trade['trade_id'], actor)).fetchone()
        deadline = instant(eligible[0]) + timedelta(days=14) if eligible else None
        result = dict(eligible_at=eligible[0] if eligible else None, deadline=deadline.isoformat() if deadline else None,
                      can_rate=bool(eligible and instant(eligible[0]) <= now < deadline), own=None, visible=[], tags=POSITIVE_RATING_TAGS)
        for r in self._connection.execute('SELECT r.*,d.tags_json FROM trade_ratings r JOIN lifecycle_rating_details d ON d.rating_id=r.id WHERE r.trade_id=?', (trade['trade_id'],)):
            if r['rater_user_id'] == actor:
                result['own'] = dict(stars=r['stars'], tags=json.loads(r['tags_json']))
                result['can_rate'] = False
            if self.lifecycle_reveal_at(r, now) is not None:
                result['visible'].append(dict(rater=r['rater_user_id'], stars=r['stars'], tags=json.loads(r['tags_json'])))
        return result

    def summary_for_user(self, rated_user_id, now=None):
        rows = self.public_rows(rated_user_id, now)
        count = len(rows)
        average = None
        if count:
            average = (Decimal(sum(r['stars'] for r in rows)) / Decimal(count)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP)
        return TradeRatingSummaryDTO(rated_user_id, count, average)
