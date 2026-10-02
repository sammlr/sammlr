from __future__ import annotations

from dataclasses import dataclass

from services.album_privacy import AlbumPrivacyService
from services.historical_collection import historical_collection_schema_available


@dataclass(frozen=True)
class CurrentCollectionAlbumDTO:
    user_album_id: int
    album_id: str
    name: str
    season: str
    cover: str


@dataclass(frozen=True)
class HistoricalAlbumCompletionDTO:
    user_album_id: int
    album_id: str
    name: str
    season: str
    completed_at: str
    completion_source_type: str


@dataclass(frozen=True)
class CollectionProjectionDTO:
    owner_user_id: int
    viewer_user_id: int
    current_albums: tuple[CurrentCollectionAlbumDTO, ...]
    historical_completions: tuple[HistoricalAlbumCompletionDTO, ...]


class CollectionProjectionService:
    """Read-only CB-013 projection of current albums and completion history."""

    def __init__(self, connection, album_privacy_service=None):
        self._connection = connection
        self._privacy = album_privacy_service or AlbumPrivacyService(connection)

    def _visible_membership_ids(self, owner_user_id, viewer_user_id, rows):
        membership_ids = tuple(int(row["user_album_id"]) for row in rows)
        if int(owner_user_id) == int(viewer_user_id):
            return frozenset(membership_ids)
        if not membership_ids:
            return frozenset()
        privacy_tables = {
            row[0] for row in self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('blocks', 'friendships')"
            ).fetchall()
        }
        if self._privacy.schema_available and privacy_tables == {
            "blocks", "friendships"
        }:
            return self._privacy.visible_user_album_ids(
                viewer_user_id, membership_ids
            )
        # Older migration fixtures can still use their persisted album policy
        # (and an explicitly supplied friendship checker). This is only a
        # policy compatibility branch; collection data still comes from this
        # single canonical projection and never becomes completion history.
        visible_album_ids = set(self._privacy.visible_album_ids(
            viewer_user_id, owner_user_id
        ))
        return frozenset(
            int(row["user_album_id"])
            for row in rows
            if row["album_id"] in visible_album_ids
        )

    def for_user(self, owner_user_id, viewer_user_id=None):
        owner = int(owner_user_id)
        viewer = owner if viewer_user_id is None else int(viewer_user_id)
        rows = self._connection.execute(
            """
            SELECT user_albums.id AS user_album_id,
                   albums.id AS album_id,
                   albums.name,
                   albums.season,
                   albums.cover
            FROM user_albums
            JOIN albums ON albums.id=user_albums.album_id
            WHERE user_albums.user_id=?
            ORDER BY albums.season DESC, albums.name COLLATE NOCASE,
                     albums.id, user_albums.id
            """,
            (owner,),
        ).fetchall()
        visible_ids = self._visible_membership_ids(owner, viewer, rows)
        current = tuple(
            CurrentCollectionAlbumDTO(
                user_album_id=int(row["user_album_id"]),
                album_id=row["album_id"],
                name=row["name"],
                season=row["season"],
                cover=row["cover"],
            )
            for row in rows
            if int(row["user_album_id"]) in visible_ids
        )

        completions = ()
        if visible_ids and historical_collection_schema_available(
            self._connection
        ):
            placeholders = ", ".join("?" for _ in visible_ids)
            completed_rows = self._connection.execute(
                f"""
                SELECT history.user_album_id, history.album_id,
                       albums.name, albums.season, history.completed_at,
                       history.completion_source_type
                FROM historical_album_records history
                JOIN albums ON albums.id=history.album_id
                WHERE history.user_id=?
                  AND history.completed_at IS NOT NULL
                  AND history.user_album_id IN ({placeholders})
                ORDER BY history.completed_at DESC, history.user_album_id DESC
                """,
                (owner, *sorted(visible_ids)),
            ).fetchall()
            completions = tuple(
                HistoricalAlbumCompletionDTO(
                    user_album_id=int(row["user_album_id"]),
                    album_id=row["album_id"],
                    name=row["name"],
                    season=row["season"],
                    completed_at=row["completed_at"],
                    completion_source_type=row["completion_source_type"],
                )
                for row in completed_rows
            )
        return CollectionProjectionDTO(owner, viewer, current, completions)
