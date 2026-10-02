from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from services.albums import all_codes
from services.historical_collection import historical_collection_schema_available
from services.inventory import InventoryReadService
from services.successful_trade_projection import (
    SuccessfulTradeAggregateDTO,
    SuccessfulTradeProjectionService,
)
from services.trophy_unlocks import (
    CanonicalTrophyUnlockService,
    canonical_trophy_schema_available,
)


@dataclass(frozen=True)
class CurrentAlbumStatisticsDTO:
    user_album_id: int
    album_id: str
    name: str
    season: str
    collected: int
    physical_quantity: int
    missing: int
    duplicate_quantity: int
    total: int
    percent: int


@dataclass(frozen=True)
class AlbumCareerStatisticsDTO:
    history_available: bool
    recorded_acquisition_quantity: int | None
    started_at: str | None
    completed_at: str | None
    first_completion_duration_days: int | None
    successful_trades: SuccessfulTradeAggregateDTO
    valid_trophy_count: int | None


@dataclass(frozen=True)
class CareerStatisticsDTO:
    history_available: bool
    recorded_acquisition_quantity: int | None
    recorded_album_start_count: int | None
    completed_album_count: int | None
    successful_trades: SuccessfulTradeAggregateDTO
    valid_trophy_count: int | None


@dataclass(frozen=True)
class StatisticsProjectionDTO:
    user_id: int
    current_albums: tuple[CurrentAlbumStatisticsDTO, ...]
    career: CareerStatisticsDTO


@dataclass(frozen=True)
class AlbumStatisticsProjectionDTO:
    user_id: int
    current: CurrentAlbumStatisticsDTO
    career: AlbumCareerStatisticsDTO


class StatisticsProjectionService:
    """CB-015 read-only split between current inventory and career facts."""

    def __init__(self, connection):
        self._connection = connection
        self._inventory = InventoryReadService(connection)
        self._trades = SuccessfulTradeProjectionService(connection)

    @staticmethod
    def _catalog_total(album_id, stored_total, codes):
        return len(codes) if album_id in {"em24", "wm26"} else int(stored_total)

    def _memberships(self, user_id, album_id=None):
        filter_sql = " AND albums.id=?" if album_id is not None else ""
        parameters = (int(user_id), str(album_id)) if album_id is not None else (int(user_id),)
        return self._connection.execute(
            f"""
            SELECT user_albums.id AS user_album_id, albums.id AS album_id,
                   albums.name, albums.season, albums.total
            FROM user_albums
            JOIN albums ON albums.id=user_albums.album_id
            WHERE user_albums.user_id=?{filter_sql}
            ORDER BY albums.season DESC, albums.name COLLATE NOCASE,
                     albums.id, user_albums.id
            """,
            parameters,
        ).fetchall()

    def _current_album(self, user_id, row):
        codes = tuple(all_codes(row["album_id"]))
        total = self._catalog_total(row["album_id"], row["total"], codes)
        inventory = self._inventory.album(user_id, row["album_id"], codes)
        progress = inventory.progress(codes, total)
        return CurrentAlbumStatisticsDTO(
            user_album_id=int(row["user_album_id"]),
            album_id=row["album_id"],
            name=row["name"],
            season=row["season"],
            collected=progress.collected,
            physical_quantity=sum(
                inventory.availability_snapshot_for(code).physical
                for code in codes
            ),
            missing=max(total - progress.collected, 0),
            duplicate_quantity=progress.duplicate_quantity,
            total=progress.total,
            percent=progress.percent,
        )

    def _history_totals(self, user_id, membership_ids):
        if not historical_collection_schema_available(self._connection):
            return None, None, None
        ids = tuple(sorted({int(value) for value in membership_ids}))
        if not ids:
            return 0, 0, 0
        placeholders = ", ".join("?" for _ in ids)
        row = self._connection.execute(
            f"""
            SELECT COALESCE(SUM(acquisitions.quantity), 0)
            FROM historical_sticker_acquisitions acquisitions
            WHERE acquisitions.user_id=?
              AND acquisitions.user_album_id IN ({placeholders})
            """,
            (int(user_id), *ids),
        ).fetchone()
        albums = self._connection.execute(
            f"""
            SELECT SUM(CASE WHEN started_at IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END)
            FROM historical_album_records
            WHERE user_id=? AND user_album_id IN ({placeholders})
            """,
            (int(user_id), *ids),
        ).fetchone()
        return int(row[0] or 0), int(albums[0] or 0), int(albums[1] or 0)

    def _valid_trophy_count(self, membership_ids):
        if not canonical_trophy_schema_available(self._connection):
            return None
        return len(CanonicalTrophyUnlockService(
            self._connection
        ).unlocks_for_albums(membership_ids))

    def career_for_user(self, user_id, membership_ids=None):
        user_id = int(user_id)
        if membership_ids is None:
            membership_ids = tuple(
                int(row["user_album_id"]) for row in self._memberships(user_id)
            )
        else:
            membership_ids = tuple(sorted({int(value) for value in membership_ids}))
        acquisitions, starts, completions = self._history_totals(
            user_id, membership_ids
        )
        return CareerStatisticsDTO(
            history_available=acquisitions is not None,
            recorded_acquisition_quantity=acquisitions,
            recorded_album_start_count=starts,
            completed_album_count=completions,
            successful_trades=self._trades.aggregates_for_user(user_id),
            valid_trophy_count=self._valid_trophy_count(membership_ids),
        )

    def successful_trades_for_user(self, user_id):
        """Shared CB-010 career definition used by statistics and profile."""
        return self._trades.aggregates_for_user(int(user_id))

    def current_albums_for_memberships(self, user_id, membership_ids):
        """Canonical current progress for an already privacy-filtered membership set."""
        user_id = int(user_id)
        ordered_ids = tuple(dict.fromkeys(int(value) for value in membership_ids))
        if not ordered_ids:
            return ()
        placeholders = ", ".join("?" for _ in ordered_ids)
        rows = self._connection.execute(
            f"""
            SELECT user_albums.id AS user_album_id, albums.id AS album_id,
                   albums.name, albums.season, albums.total
            FROM user_albums
            JOIN albums ON albums.id=user_albums.album_id
            WHERE user_albums.user_id=?
              AND user_albums.id IN ({placeholders})
            """,
            (user_id, *ordered_ids),
        ).fetchall()
        catalogs = {
            row["album_id"]: tuple(all_codes(row["album_id"])) for row in rows
        }
        totals = {
            row["album_id"]: self._catalog_total(
                row["album_id"], row["total"], catalogs[row["album_id"]]
            ) for row in rows
        }
        summaries = self._inventory.collection_summaries(
            user_id, catalogs, totals
        )
        by_membership = {}
        for row in rows:
            summary = summaries[row["album_id"]]
            progress = summary.progress
            by_membership[int(row["user_album_id"])] = CurrentAlbumStatisticsDTO(
                user_album_id=int(row["user_album_id"]),
                album_id=row["album_id"],
                name=row["name"],
                season=row["season"],
                collected=progress.collected,
                physical_quantity=summary.physical_quantity,
                missing=max(progress.total - progress.collected, 0),
                duplicate_quantity=progress.duplicate_quantity,
                total=progress.total,
                percent=progress.percent,
            )
        return tuple(
            by_membership[membership_id]
            for membership_id in ordered_ids
            if membership_id in by_membership
        )

    def for_user(self, user_id, viewer_user_id=None):
        user_id = int(user_id)
        viewer = user_id if viewer_user_id is None else int(viewer_user_id)
        if viewer != user_id:
            return None
        rows = self._memberships(user_id)
        current = tuple(self._current_album(user_id, row) for row in rows)
        return StatisticsProjectionDTO(
            user_id=user_id,
            current_albums=current,
            career=self.career_for_user(
                user_id, (album.user_album_id for album in current)
            ),
        )

    def for_album(self, user_id, album_id, viewer_user_id=None):
        user_id = int(user_id)
        viewer = user_id if viewer_user_id is None else int(viewer_user_id)
        if viewer != user_id:
            return None
        rows = self._memberships(user_id, album_id)
        if not rows:
            return None
        current = self._current_album(user_id, rows[0])
        history_available = historical_collection_schema_available(
            self._connection
        )
        acquisition_quantity = None
        started_at = None
        completed_at = None
        duration = None
        if history_available:
            acquisition_quantity = int(self._connection.execute(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM historical_sticker_acquisitions
                WHERE user_album_id=?
                """,
                (current.user_album_id,),
            ).fetchone()[0] or 0)
            history = self._connection.execute(
                """
                SELECT started_at, completed_at
                FROM historical_album_records WHERE user_album_id=?
                """,
                (current.user_album_id,),
            ).fetchone()
            if history is not None:
                started_at, completed_at = history[0], history[1]
                duration = self._duration_days(started_at, completed_at)
        trophy_count = self._valid_trophy_count((current.user_album_id,))
        return AlbumStatisticsProjectionDTO(
            user_id=user_id,
            current=current,
            career=AlbumCareerStatisticsDTO(
                history_available=history_available,
                recorded_acquisition_quantity=acquisition_quantity,
                started_at=started_at,
                completed_at=completed_at,
                first_completion_duration_days=duration,
                successful_trades=self._trades.aggregates_for_user(
                    user_id, current.album_id
                ),
                valid_trophy_count=trophy_count,
            ),
        )

    @staticmethod
    def _duration_days(started_at, completed_at):
        if not started_at or not completed_at:
            return None
        try:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            completed = datetime.fromisoformat(
                str(completed_at).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        seconds = (completed.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds()
        return int(seconds // 86400) if seconds >= 0 else None
