from __future__ import annotations

from datetime import datetime, timezone
import re

from services.album_completion import FirstAlbumCompletionService
from services.historical_collection import (
    HistoricalCollectionError,
    HistoricalCollectionService,
    HistoricalWriteConflict,
)
from services.feed_events import FeedEventService, feed_event_schema_available
from services.inventory_guard import InventoryGuardCode, InventoryGuardDecisionDTO
from services.inventory_write import InventoryMutationDTO, InventoryWriteService
from services.trophy_unlocks import (
    CanonicalTrophyUnlockService,
    canonical_trophy_schema_available,
)


CANONICAL_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6})?Z$"
)
HISTORY_SOURCE_TYPES = frozenset({
    "inventory",
    "paper_trade",
    "trade_receipt",
    "trade_shipping",
})
ACQUISITION_SOURCE_BY_MUTATION = {
    "inventory": "inventory",
    "paper_trade": "paper_trade",
    "trade_receipt": "trade_receipt",
}


def canonical_utc_timestamp(moment=None):
    """Return one canonical UTC timestamp shared by all CB-002 producers."""

    value = moment or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("historical timestamps require a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def validate_canonical_utc(value):
    text = str(value or "").strip()
    if CANONICAL_UTC.fullmatch(text) is None:
        raise HistoricalCollectionError(
            "historical timestamp must use canonical UTC ISO-8601"
        )
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise HistoricalCollectionError(
            "historical timestamp is not a valid UTC instant"
        ) from error
    return text


def cutover_schema_available(connection):
    return connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='historical_inventory_mutations'
        """
    ).fetchone() is not None


class AlbumHistoryCutoverService:
    """Creates new album membership and its start fact in one transaction."""

    def __init__(self, connection):
        self._connection = connection

    def add(self, user_id, album_id, *, occurred_at=None):
        occurred_at = validate_canonical_utc(
            occurred_at or canonical_utc_timestamp()
        )
        savepoint = "cb002_album_start"
        started_transaction = not self._connection.in_transaction
        if started_transaction:
            self._connection.execute("BEGIN IMMEDIATE")
        self._connection.execute(f"SAVEPOINT {savepoint}")
        try:
            inserted = self._connection.execute(
                """
                INSERT OR IGNORE INTO user_albums (user_id, album_id)
                VALUES (?, ?)
                """,
                (user_id, album_id),
            )
            membership = self._connection.execute(
                """
                SELECT id FROM user_albums WHERE user_id=? AND album_id=?
                """,
                (user_id, album_id),
            ).fetchone()
            if membership is None:
                raise HistoricalCollectionError("user album could not be created")
            if inserted.rowcount == 1:
                HistoricalCollectionService(self._connection).record_album_start(
                    int(membership[0]),
                    started_at=occurred_at,
                    event_key=f"album-start:{int(membership[0])}",
                )
                if feed_event_schema_available(self._connection):
                    FeedEventService(self._connection).record_album_started(
                        int(membership[0])
                    )
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            return inserted.rowcount == 1
        except Exception:
            self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self._connection.rollback()
            raise


class HistoricalInventoryWriteService:
    """Atomically joins current inventory writes with CB-002 history facts."""

    def __init__(self, connection, guard=None):
        self._connection = connection
        self._inventory = InventoryWriteService(connection, guard=guard)
        if not cutover_schema_available(connection):
            raise RuntimeError("V0014 collection history cutover schema is not installed")

    @staticmethod
    def _required_text(value, field_name):
        text = str(value or "").strip()
        if not text:
            raise HistoricalCollectionError(f"{field_name} must not be empty")
        return text

    def _membership(self, user_id, album_id):
        row = self._connection.execute(
            """
            SELECT id, user_id, album_id FROM user_albums
            WHERE user_id=? AND album_id=?
            """,
            (user_id, album_id),
        ).fetchone()
        if row is None:
            raise HistoricalCollectionError("user album does not exist")
        return int(row[0]), int(row[1]), row[2]

    def _replay(self, row):
        guard = InventoryGuardDecisionDTO(
            code=InventoryGuardCode.OK,
            current_quantity=int(row["previous_quantity"]),
            requested_quantity=int(row["result_quantity"]),
            bound_quantity=0,
            explanation="Idempotent wiederholte Bestandsmutation.",
        )
        return InventoryMutationDTO(
            user_id=int(row["user_id"]),
            album_id=row["album_id"],
            sticker_code=row["sticker_code"],
            previous_quantity=int(row["previous_quantity"]),
            quantity=int(row["result_quantity"]),
            duplicates=max(int(row["result_quantity"]) - 1, 0),
            created=(
                int(row["previous_quantity"]) == 0
                and int(row["result_quantity"]) > 0
            ),
            deleted=(
                int(row["previous_quantity"]) > 0
                and int(row["result_quantity"]) == 0
            ),
            guard_decision=guard,
        )

    def _mutate(
        self,
        user_id,
        album_id,
        sticker_code,
        *,
        operation_type,
        requested_value,
        event_key,
        source_type,
        occurred_at=None,
    ):
        event_key = self._required_text(event_key, "event_key")
        sticker_code = self._required_text(sticker_code, "sticker_code")
        source_type = self._required_text(source_type, "source_type")
        if source_type not in HISTORY_SOURCE_TYPES:
            raise HistoricalCollectionError("unsupported mutation source_type")
        if operation_type not in {"delta", "set"}:
            raise HistoricalCollectionError("unsupported inventory operation")
        if isinstance(requested_value, bool) or not isinstance(requested_value, int):
            raise HistoricalCollectionError("requested_value must be an integer")
        if operation_type == "set" and requested_value < 0:
            raise HistoricalCollectionError("set quantity must not be negative")
        occurred_at = validate_canonical_utc(
            occurred_at or canonical_utc_timestamp()
        )
        savepoint = "cb002_inventory_history"
        started_transaction = not self._connection.in_transaction
        if started_transaction:
            self._connection.execute("BEGIN IMMEDIATE")
        self._connection.execute(f"SAVEPOINT {savepoint}")
        try:
            membership = self._membership(user_id, album_id)
            expected_identity = (
                membership[0], membership[1], membership[2], sticker_code,
                source_type, operation_type, requested_value,
            )
            existing = self._connection.execute(
                "SELECT * FROM historical_inventory_mutations WHERE event_key=?",
                (event_key,),
            ).fetchone()
            if existing is not None:
                actual_identity = (
                    int(existing["user_album_id"]), int(existing["user_id"]),
                    existing["album_id"], existing["sticker_code"],
                    existing["source_type"], existing["operation_type"],
                    int(existing["requested_value"]),
                )
                if actual_identity != expected_identity:
                    raise HistoricalWriteConflict(
                        "inventory event key already records another mutation"
                    )
                replay = self._replay(existing)
                self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                return replay

            completion = FirstAlbumCompletionService(self._connection)
            before_completion = None
            trophies = None
            before_trophies = None
            if requested_value > 0:
                before_completion = completion.state(membership[0])
                if canonical_trophy_schema_available(self._connection):
                    trophies = CanonicalTrophyUnlockService(self._connection)
                    before_trophies = trophies.state(membership[0])

            if operation_type == "set":
                mutation = self._inventory.set_quantity(
                    user_id, album_id, sticker_code, requested_value
                )
            else:
                mutation = self._inventory.change_quantity(
                    user_id, album_id, sticker_code, requested_value
                )
            if not mutation.allowed:
                self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                return mutation

            self._connection.execute(
                """
                INSERT INTO historical_inventory_mutations
                    (event_key, user_album_id, user_id, album_id, sticker_code,
                     source_type, operation_type, requested_value,
                     previous_quantity, result_quantity, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_key, *membership, sticker_code, source_type,
                    operation_type, requested_value, mutation.previous_quantity,
                    mutation.quantity, occurred_at,
                ),
            )

            history = HistoricalCollectionService(self._connection)
            positive_quantity = mutation.quantity - mutation.previous_quantity
            if positive_quantity > 0:
                acquisition_source = ACQUISITION_SOURCE_BY_MUTATION.get(source_type)
                if acquisition_source is None:
                    raise HistoricalCollectionError(
                        "positive mutation requires an acquisition source"
                    )
                history.record_positive_acquisition(
                    membership[0],
                    sticker_code=sticker_code,
                    quantity=positive_quantity,
                    source_type=acquisition_source,
                    source_key=event_key,
                    occurred_at=occurred_at,
                )

            ownership_changed = (
                (mutation.previous_quantity > 0) != (mutation.quantity > 0)
            )
            if ownership_changed:
                owned_count = int(self._connection.execute(
                    """
                    SELECT COUNT(*) FROM stickers
                    WHERE user_id=? AND album_id=? AND quantity > 0
                    """,
                    (user_id, album_id),
                ).fetchone()[0])
                album = self._connection.execute(
                    "SELECT total FROM albums WHERE id=?", (album_id,)
                ).fetchone()
                if album is None or int(album[0]) <= 0:
                    raise HistoricalCollectionError("album total is not available")
                history.record_progress_point(
                    membership[0],
                    event_key=f"inventory-progress:{event_key}",
                    captured_at=occurred_at,
                    owned_count=owned_count,
                    total_count=int(album[0]),
                )
            if (
                before_completion is not None
                and mutation.previous_quantity == 0
                and mutation.quantity > 0
            ):
                completion_result = completion.evaluate_first_album_completion(
                    membership[0],
                    before=before_completion,
                    mutation_event_key=event_key,
                    completed_at=occurred_at,
                )
                feed = (
                    FeedEventService(self._connection)
                    if feed_event_schema_available(self._connection) else None
                )
                if (
                    feed is not None
                    and completion_result is not None
                    and completion_result.created
                ):
                    feed.record_album_completed(membership[0])
                if trophies is not None:
                    new_unlocks = trophies.evaluate_new_unlocks(
                        membership[0],
                        before=before_trophies,
                        mutation_event_key=event_key,
                        occurred_at=occurred_at,
                        trigger_sticker_code=sticker_code,
                    )
                    if feed is not None:
                        for unlock in new_unlocks:
                            if unlock.created:
                                feed.record_trophy_unlocked(unlock.id)
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            return mutation
        except Exception:
            self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self._connection.rollback()
            raise

    def set_quantity(
        self, user_id, album_id, sticker_code, quantity, *,
        event_key, source_type="inventory", occurred_at=None,
    ):
        return self._mutate(
            user_id, album_id, sticker_code,
            operation_type="set", requested_value=quantity,
            event_key=event_key, source_type=source_type,
            occurred_at=occurred_at,
        )

    def change_quantity(
        self, user_id, album_id, sticker_code, delta, *,
        event_key, source_type="inventory", occurred_at=None,
    ):
        return self._mutate(
            user_id, album_id, sticker_code,
            operation_type="delta", requested_value=delta,
            event_key=event_key, source_type=source_type,
            occurred_at=occurred_at,
        )

    def add(
        self, user_id, album_id, sticker_code, amount=1, *,
        event_key, source_type="inventory", occurred_at=None,
    ):
        return self.change_quantity(
            user_id, album_id, sticker_code, max(amount, 0),
            event_key=event_key, source_type=source_type,
            occurred_at=occurred_at,
        )

    def remove(
        self, user_id, album_id, sticker_code, amount=1, *,
        event_key, source_type="inventory", occurred_at=None,
    ):
        return self.change_quantity(
            user_id, album_id, sticker_code, -max(amount, 0),
            event_key=event_key, source_type=source_type,
            occurred_at=occurred_at,
        )
