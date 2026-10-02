from __future__ import annotations

from dataclasses import dataclass

from services.albums import all_codes
from services.historical_collection import (
    HistoricalCollectionError,
    HistoricalCollectionService,
    HistoricalWriteResult,
)
from services.inventory import InventoryReadService


@dataclass(frozen=True)
class AlbumCompletionState:
    user_album_id: int
    user_id: int
    album_id: str
    collected: int
    total: int

    @property
    def complete(self):
        return self.collected >= self.total


class FirstAlbumCompletionService:
    """Orchestrates only mutation-caused first album completion facts."""

    def __init__(self, connection):
        self._connection = connection
        self._history = HistoricalCollectionService(connection)

    def _membership(self, user_album_id):
        row = self._connection.execute(
            """
            SELECT id, user_id, album_id
            FROM user_albums
            WHERE id=?
            """,
            (user_album_id,),
        ).fetchone()
        if row is None:
            raise HistoricalCollectionError("user album does not exist")
        return int(row[0]), int(row[1]), row[2]

    def state(self, user_album_id):
        membership = self._membership(user_album_id)
        album = self._connection.execute(
            "SELECT total FROM albums WHERE id=?", (membership[2],)
        ).fetchone()
        if album is None or int(album[0]) <= 0:
            raise HistoricalCollectionError("album total is not available")

        catalog_codes = tuple(all_codes(membership[2]))
        # This mirrors the existing lade_album_for_user contract: the data-file
        # catalogs are canonical for EM24/WM26; other supported albums use the
        # persisted album total.
        total = (
            len(catalog_codes)
            if membership[2] in {"em24", "wm26"}
            else int(album[0])
        )
        if not catalog_codes or total <= 0:
            raise HistoricalCollectionError("album catalog is not available")
        progress = InventoryReadService(self._connection).album(
            membership[1], membership[2], catalog_codes
        ).progress(catalog_codes, total)
        return AlbumCompletionState(
            user_album_id=membership[0],
            user_id=membership[1],
            album_id=membership[2],
            collected=progress.collected,
            total=progress.total,
        )

    def evaluate_first_album_completion(
        self,
        user_album_id,
        *,
        before,
        mutation_event_key,
        completed_at,
    ):
        """Record only a real incomplete-to-complete mutation transition."""

        if not isinstance(before, AlbumCompletionState):
            raise HistoricalCollectionError("before completion state is required")
        if before.user_album_id != user_album_id:
            raise HistoricalCollectionError("completion state belongs to another album")
        if before.complete:
            return None

        existing = self._history.album_history(user_album_id)
        if existing is not None and existing.completed_at is not None:
            return HistoricalWriteResult(user_album_id, False)

        after = self.state(user_album_id)
        if not after.complete:
            return None

        return self._history.record_first_album_completion(
            user_album_id,
            completed_at=completed_at,
            event_key=f"album-completion:{user_album_id}",
            source_type="inventory_transition",
            source_key=mutation_event_key,
        )
