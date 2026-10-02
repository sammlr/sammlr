from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from services.albums import all_codes
from services.historical_collection import HistoricalCollectionError
from services.inventory import InventoryReadService
from trophy_definitions import canonical_album_trophy_definitions


CANONICAL_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)


class TrophyUnlockError(ValueError):
    """A canonical trophy unlock request violates the CB-005 contract."""


@dataclass(frozen=True)
class TrophyEvaluationState:
    user_album_id: int
    user_id: int
    album_id: str
    achieved_definition_ids: frozenset[str]


@dataclass(frozen=True)
class TrophyUnlockDTO:
    id: int
    event_key: str
    trophy_definition_id: str
    user_album_id: int
    user_id: int
    album_id: str
    trophy_name: str
    unlocked_at: str
    source_type: str
    source_key: str
    trigger_sticker_code: str | None
    created: bool = False


def canonical_trophy_schema_available(connection):
    return connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='canonical_trophy_unlocks'
        """
    ).fetchone() is not None


class CanonicalTrophyUnlockService:
    """Persistent, mutation-bound truth for curated album trophies."""

    def __init__(self, connection):
        self._connection = connection
        if not canonical_trophy_schema_available(connection):
            raise RuntimeError("V0015 canonical trophy schema is not installed")

    @staticmethod
    def _canonical_timestamp(value):
        text = str(value or "").strip()
        if CANONICAL_UTC.fullmatch(text) is None:
            raise TrophyUnlockError("unlock timestamp must use canonical UTC")
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as error:
            raise TrophyUnlockError("unlock timestamp is invalid") from error
        return text

    def _membership(self, user_album_id):
        row = self._connection.execute(
            """
            SELECT ua.id, ua.user_id, ua.album_id, a.total
            FROM user_albums ua
            JOIN albums a ON a.id=ua.album_id
            WHERE ua.id=?
            """,
            (user_album_id,),
        ).fetchone()
        if row is None:
            raise TrophyUnlockError("user album does not exist")
        return int(row[0]), int(row[1]), row[2], int(row[3])

    @staticmethod
    def _catalog_total(album_id, stored_total, codes):
        return len(codes) if album_id in {"em24", "wm26"} else stored_total

    def _definitions(self, membership):
        codes = tuple(all_codes(membership[2]))
        total = self._catalog_total(membership[2], membership[3], codes)
        return canonical_album_trophy_definitions(membership[2], total), codes

    def _completion(self, user_album_id):
        return self._connection.execute(
            """
            SELECT completed_at, completion_event_key
            FROM historical_album_records
            WHERE user_album_id=? AND completed_at IS NOT NULL
            """,
            (user_album_id,),
        ).fetchone()

    def state(self, user_album_id):
        membership = self._membership(user_album_id)
        definitions, catalog_codes = self._definitions(membership)
        inventory = InventoryReadService(self._connection).album(
            membership[1], membership[2], catalog_codes
        )
        completion = self._completion(membership[0])
        achieved = set()
        for definition in definitions:
            if definition["trigger_type"] == "album_complete":
                if completion is not None:
                    achieved.add(definition["id"])
                continue
            if definition["trigger_type"] != "codes":
                raise TrophyUnlockError("unsupported canonical trophy trigger")
            if all(
                not inventory.availability_snapshot_for(code).missing
                for code in definition["sticker_codes"]
            ):
                achieved.add(definition["id"])
        return TrophyEvaluationState(
            membership[0], membership[1], membership[2], frozenset(achieved)
        )

    def _row_to_dto(self, row, *, created=False):
        return TrophyUnlockDTO(*tuple(row), created=created)

    def unlocks_for_album(self, user_album_id):
        membership = self._membership(user_album_id)
        valid_ids = {
            definition["id"]
            for definition in self._definitions(membership)[0]
        }
        rows = self._connection.execute(
            """
            SELECT id, event_key, trophy_definition_id, user_album_id,
                   user_id, album_id, trophy_name, unlocked_at, source_type,
                   source_key, trigger_sticker_code
            FROM canonical_trophy_unlocks
            WHERE user_album_id=?
            ORDER BY unlocked_at, id
            """,
            (membership[0],),
        ).fetchall()
        return tuple(
            self._row_to_dto(row)
            for row in rows
            if row[2] in valid_ids
        )

    def unlocks_for_albums(self, user_album_ids):
        """Load valid canonical unlocks for a privacy-filtered membership set."""

        membership_ids = tuple(sorted({int(value) for value in user_album_ids}))
        if not membership_ids:
            return ()
        placeholders = ", ".join("?" for _ in membership_ids)
        memberships = self._connection.execute(
            f"""
            SELECT ua.id, ua.album_id, albums.total
            FROM user_albums ua
            JOIN albums ON albums.id=ua.album_id
            WHERE ua.id IN ({placeholders})
            """,
            membership_ids,
        ).fetchall()
        valid_by_membership = {}
        for membership in memberships:
            codes = tuple(all_codes(membership[1]))
            total = self._catalog_total(membership[1], membership[2], codes)
            valid_by_membership[int(membership[0])] = {
                definition["id"]
                for definition in canonical_album_trophy_definitions(
                    membership[1], total
                )
            }
        rows = self._connection.execute(
            f"""
            SELECT id, event_key, trophy_definition_id, user_album_id,
                   user_id, album_id, trophy_name, unlocked_at, source_type,
                   source_key, trigger_sticker_code
            FROM canonical_trophy_unlocks
            WHERE user_album_id IN ({placeholders})
            ORDER BY unlocked_at DESC, event_key DESC
            """,
            membership_ids,
        ).fetchall()
        return tuple(
            self._row_to_dto(row)
            for row in rows
            if row[2] in valid_by_membership.get(int(row[3]), set())
        )

    def unlocks_for_user_album(self, user_id, album_id):
        row = self._connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? AND album_id=?",
            (user_id, album_id),
        ).fetchone()
        if row is None:
            return ()
        return self.unlocks_for_album(int(row[0]))

    def unlocks_for_user(self, user_id):
        memberships = self._connection.execute(
            "SELECT id FROM user_albums WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
        unlocks = []
        for membership in memberships:
            unlocks.extend(self.unlocks_for_album(int(membership[0])))
        return tuple(sorted(unlocks, key=lambda unlock: (unlock.unlocked_at, unlock.id)))

    def evaluate_new_unlocks(
        self,
        user_album_id,
        *,
        before,
        mutation_event_key,
        occurred_at,
        trigger_sticker_code=None,
    ):
        if not isinstance(before, TrophyEvaluationState):
            raise TrophyUnlockError("before trophy state is required")
        if before.user_album_id != user_album_id:
            raise TrophyUnlockError("trophy state belongs to another album")
        mutation_event_key = str(mutation_event_key or "").strip()
        if not mutation_event_key:
            raise TrophyUnlockError("mutation_event_key must not be empty")
        occurred_at = self._canonical_timestamp(occurred_at)

        membership = self._membership(user_album_id)
        definitions, catalog_codes = self._definitions(membership)
        by_id = {definition["id"]: definition for definition in definitions}
        after = self.state(user_album_id)
        new_ids = after.achieved_definition_ids - before.achieved_definition_ids
        if not new_ids:
            return ()

        trigger = None
        if trigger_sticker_code is not None:
            candidate = str(trigger_sticker_code).strip()
            if candidate in set(catalog_codes):
                trigger = candidate

        completion = self._completion(user_album_id)
        results = []
        for definition_id in sorted(new_ids):
            definition = by_id[definition_id]
            if definition["trigger_type"] == "album_complete":
                if completion is None:
                    raise HistoricalCollectionError(
                        "completion trophy requires historical completion"
                    )
                unlocked_at = self._canonical_timestamp(completion[0])
                source_type = "album_completion"
                source_key = completion[1]
                definition_trigger = trigger
            else:
                unlocked_at = occurred_at
                source_type = "inventory_transition"
                source_key = mutation_event_key
                definition_trigger = (
                    trigger
                    if trigger in set(definition["sticker_codes"])
                    else None
                )
            event_key = f"trophy-unlock:{user_album_id}:{definition_id}"
            inserted = self._connection.execute(
                """
                INSERT OR IGNORE INTO canonical_trophy_unlocks
                    (event_key, trophy_definition_id, user_album_id, user_id,
                     album_id, trophy_name, unlocked_at, source_type,
                     source_key, trigger_sticker_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_key, definition_id, membership[0], membership[1],
                    membership[2], definition["name"], unlocked_at,
                    source_type, source_key, definition_trigger,
                ),
            )
            row = self._connection.execute(
                """
                SELECT id, event_key, trophy_definition_id, user_album_id,
                       user_id, album_id, trophy_name, unlocked_at, source_type,
                       source_key, trigger_sticker_code
                FROM canonical_trophy_unlocks
                WHERE user_album_id=? AND trophy_definition_id=?
                """,
                (membership[0], definition_id),
            ).fetchone()
            if row is None:
                raise TrophyUnlockError("canonical trophy unlock was not persisted")
            results.append(self._row_to_dto(row, created=inserted.rowcount == 1))
        return tuple(results)
