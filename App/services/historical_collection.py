from __future__ import annotations

from dataclasses import dataclass
import sqlite3


ACQUISITION_SOURCE_TYPES = frozenset({
    "inventory",
    "paper_trade",
    "trade_receipt",
})
FEED_EVENT_TYPES = frozenset({
    "album_started",
    "album_completed",
    "trophy_unlocked",
    "sammlr_news",
})
FEED_TARGET_TYPES = frozenset({"album", "trophy", "profile", "trade", "news"})


class HistoricalCollectionError(ValueError):
    """Base error for a rejected CB-001 historical write."""


class HistoricalWriteConflict(HistoricalCollectionError):
    """A stable idempotency key was reused for different historical facts."""


@dataclass(frozen=True)
class HistoricalWriteResult:
    record_id: int
    created: bool


@dataclass(frozen=True)
class AlbumHistoryDTO:
    user_album_id: int
    user_id: int
    album_id: str
    started_at: str | None
    start_event_key: str | None
    completed_at: str | None
    completion_event_key: str | None
    completion_source_type: str | None
    completion_source_key: str | None


@dataclass(frozen=True)
class StickerAcquisitionDTO:
    id: int
    user_album_id: int
    user_id: int
    album_id: str
    sticker_code: str
    quantity: int
    source_type: str
    source_key: str
    occurred_at: str


@dataclass(frozen=True)
class AlbumProgressPointDTO:
    id: int
    user_album_id: int
    user_id: int
    album_id: str
    event_key: str
    captured_at: str
    owned_count: int
    total_count: int


@dataclass(frozen=True)
class FeedEventDTO:
    id: int
    event_key: str
    event_type: str
    actor_user_id: int | None
    user_album_id: int | None
    user_id: int | None
    album_id: str | None
    target_type: str
    target_key: str
    occurred_at: str


def historical_collection_schema_available(connection) -> bool:
    required = {
        "historical_album_records",
        "historical_sticker_acquisitions",
        "historical_album_progress_points",
        "feed_events",
        "trophy_unlock_history_context",
    }
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return required.issubset({row[0] for row in rows})


class HistoricalCollectionService:
    """Service boundary for explicit historical collection facts.

    All supplied event timestamps use canonical UTC ISO-8601 text (``...Z``).
    CB-002 owns central serialization at mutation integrations; this contract
    deliberately does not infer or rewrite historical timestamps. CB-003 uses
    the completion write only through its mutation-bound orchestrator.
    """

    def __init__(self, connection):
        self._connection = connection
        if not historical_collection_schema_available(connection):
            raise RuntimeError("V0013 historical collection schema is not installed")

    @staticmethod
    def _required_text(value, field_name):
        text = str(value or "").strip()
        if not text:
            raise HistoricalCollectionError(f"{field_name} must not be empty")
        return text

    @staticmethod
    def _positive_integer(value, field_name):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise HistoricalCollectionError(f"{field_name} must be positive")
        return value

    @staticmethod
    def _non_negative_integer(value, field_name):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise HistoricalCollectionError(
                f"{field_name} must be a non-negative integer"
            )
        return value

    def _album_context(self, user_album_id):
        self._positive_integer(user_album_id, "user_album_id")
        row = self._connection.execute(
            "SELECT id, user_id, album_id FROM user_albums WHERE id=?",
            (user_album_id,),
        ).fetchone()
        if row is None:
            raise HistoricalCollectionError("user album does not exist")
        return int(row[0]), int(row[1]), row[2]

    def record_album_start(self, user_album_id, *, started_at, event_key):
        context = self._album_context(user_album_id)
        started_at = self._required_text(started_at, "started_at")
        event_key = self._required_text(event_key, "event_key")
        existing = self._connection.execute(
            "SELECT * FROM historical_album_records WHERE user_album_id=?",
            (context[0],),
        ).fetchone()
        if existing is None:
            try:
                inserted = self._connection.execute(
                    """
                    INSERT INTO historical_album_records
                        (user_album_id, user_id, album_id, started_at,
                         start_event_key)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (*context, started_at, event_key),
                )
            except sqlite3.IntegrityError:
                same_key = self._connection.execute(
                    """
                    SELECT * FROM historical_album_records
                    WHERE start_event_key=?
                    """,
                    (event_key,),
                ).fetchone()
                if same_key is None:
                    raise
                existing = same_key
            else:
                return HistoricalWriteResult(int(inserted.lastrowid), True)
        if (
            int(existing[0]) == context[0]
            and int(existing[1]) == context[1]
            and existing[2] == context[2]
            and existing[3] == started_at
            and existing[4] == event_key
        ):
            return HistoricalWriteResult(context[0], False)
        if existing[3] is None and existing[4] is None:
            updated = self._connection.execute(
                """
                UPDATE historical_album_records
                SET started_at=?, start_event_key=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_album_id=? AND started_at IS NULL
                  AND start_event_key IS NULL
                """,
                (started_at, event_key, context[0]),
            )
            if updated.rowcount == 1:
                return HistoricalWriteResult(context[0], True)
        raise HistoricalWriteConflict("album start already records another fact")

    def album_history(self, user_album_id):
        context = self._album_context(user_album_id)
        row = self._connection.execute(
            """
            SELECT user_album_id, user_id, album_id, started_at,
                   start_event_key, completed_at, completion_event_key,
                   completion_source_type, completion_source_key
            FROM historical_album_records
            WHERE user_album_id=?
            """,
            (context[0],),
        ).fetchone()
        return AlbumHistoryDTO(*row) if row is not None else None

    def record_first_album_completion(
        self,
        user_album_id,
        *,
        completed_at,
        event_key,
        source_type,
        source_key,
    ):
        """Persist the first completion of one concrete user-album identity.

        A different later completion candidate is an idempotent no-op: the
        first persisted fact wins. Reusing the same event key for different
        facts remains a write conflict.
        """

        context = self._album_context(user_album_id)
        completed_at = self._required_text(completed_at, "completed_at")
        event_key = self._required_text(event_key, "event_key")
        source_type = self._required_text(source_type, "source_type")
        if source_type not in {"inventory_transition", "validated_trophy"}:
            raise HistoricalCollectionError("unsupported completion source_type")
        source_key = self._required_text(source_key, "source_key")

        existing = self._connection.execute(
            "SELECT * FROM historical_album_records WHERE user_album_id=?",
            (context[0],),
        ).fetchone()
        if existing is not None and existing[5] is not None:
            expected = (completed_at, event_key, source_type, source_key)
            recorded = tuple(existing[index] for index in (5, 6, 7, 8))
            if existing[6] == event_key and recorded != expected:
                raise HistoricalWriteConflict(
                    "completion event key already records different facts"
                )
            return HistoricalWriteResult(context[0], False)

        key_owner = self._connection.execute(
            """
            SELECT user_album_id, completed_at, completion_source_type,
                   completion_source_key
            FROM historical_album_records
            WHERE completion_event_key=?
            """,
            (event_key,),
        ).fetchone()
        if key_owner is not None:
            expected_owner = (context[0], completed_at, source_type, source_key)
            if tuple(key_owner) != expected_owner:
                raise HistoricalWriteConflict(
                    "completion event key already records another album"
                )
            return HistoricalWriteResult(context[0], False)

        if existing is None:
            inserted = self._connection.execute(
                """
                INSERT INTO historical_album_records
                    (user_album_id, user_id, album_id, completed_at,
                     completion_event_key, completion_source_type,
                     completion_source_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (*context, completed_at, event_key, source_type, source_key),
            )
            return HistoricalWriteResult(int(inserted.lastrowid), True)

        updated = self._connection.execute(
            """
            UPDATE historical_album_records
            SET completed_at=?, completion_event_key=?,
                completion_source_type=?, completion_source_key=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_album_id=? AND completed_at IS NULL
              AND completion_event_key IS NULL
              AND completion_source_type IS NULL
              AND completion_source_key IS NULL
            """,
            (completed_at, event_key, source_type, source_key, context[0]),
        )
        if updated.rowcount == 1:
            return HistoricalWriteResult(context[0], True)

        concurrent = self._connection.execute(
            "SELECT completed_at FROM historical_album_records WHERE user_album_id=?",
            (context[0],),
        ).fetchone()
        if concurrent is not None and concurrent[0] is not None:
            return HistoricalWriteResult(context[0], False)
        raise HistoricalWriteConflict("album completion could not be persisted")

    def record_positive_acquisition(
        self,
        user_album_id,
        *,
        sticker_code,
        quantity,
        source_type,
        source_key,
        occurred_at,
    ):
        context = self._album_context(user_album_id)
        sticker_code = self._required_text(sticker_code, "sticker_code")
        quantity = self._positive_integer(quantity, "quantity")
        source_type = self._required_text(source_type, "source_type")
        if source_type not in ACQUISITION_SOURCE_TYPES:
            raise HistoricalCollectionError("unsupported acquisition source_type")
        source_key = self._required_text(source_key, "source_key")
        occurred_at = self._required_text(occurred_at, "occurred_at")
        inserted = self._connection.execute(
            """
            INSERT OR IGNORE INTO historical_sticker_acquisitions
                (user_album_id, user_id, album_id, sticker_code, quantity,
                 source_type, source_key, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*context, sticker_code, quantity, source_type, source_key, occurred_at),
        )
        row = self._connection.execute(
            """
            SELECT id, user_album_id, user_id, album_id, sticker_code, quantity,
                   source_type, source_key, occurred_at
            FROM historical_sticker_acquisitions
            WHERE source_type=? AND source_key=? AND user_album_id=?
              AND sticker_code=?
            """,
            (source_type, source_key, context[0], sticker_code),
        ).fetchone()
        expected = (
            context[0], context[1], context[2], sticker_code, quantity,
            source_type, source_key, occurred_at,
        )
        if row is None or tuple(row[1:]) != expected:
            raise HistoricalWriteConflict(
                "acquisition idempotency key already records another fact"
            )
        return HistoricalWriteResult(int(row[0]), inserted.rowcount == 1)

    def acquisitions_for_album(self, user_album_id):
        context = self._album_context(user_album_id)
        rows = self._connection.execute(
            """
            SELECT id, user_album_id, user_id, album_id, sticker_code, quantity,
                   source_type, source_key, occurred_at
            FROM historical_sticker_acquisitions
            WHERE user_album_id=?
            ORDER BY occurred_at, id
            """,
            (context[0],),
        ).fetchall()
        return tuple(StickerAcquisitionDTO(*row) for row in rows)

    def record_progress_point(
        self,
        user_album_id,
        *,
        event_key,
        captured_at,
        owned_count,
        total_count,
    ):
        context = self._album_context(user_album_id)
        event_key = self._required_text(event_key, "event_key")
        captured_at = self._required_text(captured_at, "captured_at")
        owned_count = self._non_negative_integer(owned_count, "owned_count")
        total_count = self._positive_integer(total_count, "total_count")
        if owned_count > total_count:
            raise HistoricalCollectionError("owned_count must not exceed total_count")
        inserted = self._connection.execute(
            """
            INSERT OR IGNORE INTO historical_album_progress_points
                (user_album_id, user_id, album_id, event_key, captured_at,
                 owned_count, total_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (*context, event_key, captured_at, owned_count, total_count),
        )
        row = self._connection.execute(
            """
            SELECT id, user_album_id, user_id, album_id, event_key, captured_at,
                   owned_count, total_count
            FROM historical_album_progress_points
            WHERE user_album_id=? AND event_key=?
            """,
            (context[0], event_key),
        ).fetchone()
        expected = (*context, event_key, captured_at, owned_count, total_count)
        if row is None or tuple(row[1:]) != expected:
            raise HistoricalWriteConflict(
                "progress idempotency key already records another fact"
            )
        return HistoricalWriteResult(int(row[0]), inserted.rowcount == 1)

    def progress_for_album(self, user_album_id):
        context = self._album_context(user_album_id)
        rows = self._connection.execute(
            """
            SELECT id, user_album_id, user_id, album_id, event_key, captured_at,
                   owned_count, total_count
            FROM historical_album_progress_points
            WHERE user_album_id=?
            ORDER BY captured_at, id
            """,
            (context[0],),
        ).fetchall()
        return tuple(AlbumProgressPointDTO(*row) for row in rows)

    def record_feed_event(
        self,
        *,
        event_key,
        event_type,
        target_type,
        target_key,
        occurred_at,
        actor_user_id=None,
        user_album_id=None,
    ):
        event_key = self._required_text(event_key, "event_key")
        event_type = self._required_text(event_type, "event_type")
        if event_type not in FEED_EVENT_TYPES:
            raise HistoricalCollectionError("unsupported feed event_type")
        target_type = self._required_text(target_type, "target_type")
        if target_type not in FEED_TARGET_TYPES:
            raise HistoricalCollectionError("unsupported feed target_type")
        target_key = self._required_text(target_key, "target_key")
        occurred_at = self._required_text(occurred_at, "occurred_at")
        if event_type == "sammlr_news":
            if actor_user_id is not None:
                raise HistoricalCollectionError("sammlr_news must not have an actor")
        else:
            actor_user_id = self._positive_integer(actor_user_id, "actor_user_id")
            if self._connection.execute(
                "SELECT 1 FROM users WHERE id=?", (actor_user_id,)
            ).fetchone() is None:
                raise HistoricalCollectionError("actor user does not exist")
        context = (None, None, None)
        if user_album_id is not None:
            context = self._album_context(user_album_id)
            if actor_user_id is not None and actor_user_id != context[1]:
                raise HistoricalCollectionError(
                    "feed actor must own the referenced user album"
                )
        inserted = self._connection.execute(
            """
            INSERT OR IGNORE INTO feed_events
                (event_key, event_type, actor_user_id, user_album_id, user_id,
                 album_id, target_type, target_key, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_key, event_type, actor_user_id, context[0], context[1],
                context[2], target_type, target_key, occurred_at,
            ),
        )
        row = self._connection.execute(
            """
            SELECT id, event_key, event_type, actor_user_id, user_album_id,
                   user_id, album_id, target_type, target_key, occurred_at
            FROM feed_events WHERE event_key=?
            """,
            (event_key,),
        ).fetchone()
        expected = (
            event_key, event_type, actor_user_id, context[0], context[1],
            context[2], target_type, target_key, occurred_at,
        )
        if row is None or tuple(row[1:]) != expected:
            raise HistoricalWriteConflict(
                "feed idempotency key already records another fact"
            )
        return HistoricalWriteResult(int(row[0]), inserted.rowcount == 1)

    def feed_event(self, event_key):
        event_key = self._required_text(event_key, "event_key")
        row = self._connection.execute(
            """
            SELECT id, event_key, event_type, actor_user_id, user_album_id,
                   user_id, album_id, target_type, target_key, occurred_at
            FROM feed_events WHERE event_key=?
            """,
            (event_key,),
        ).fetchone()
        return FeedEventDTO(*row) if row is not None else None
