from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.account_lifecycle import account_lifecycle_schema_available
from services.album_privacy import AlbumPrivacyService
from services.collection_projection import (
    CollectionProjectionService,
    CurrentCollectionAlbumDTO,
    HistoricalAlbumCompletionDTO,
)
from services.profile_privacy import ProfilePrivacyService
from services.statistics_projection import StatisticsProjectionService
from services.trade_ratings import TradeRatingService
from services.trophy_unlocks import (
    CanonicalTrophyUnlockService,
    TrophyUnlockDTO,
    canonical_trophy_schema_available,
)


@dataclass(frozen=True)
class CollectorProfileDTO:
    """CB-014 public profile contract; account data is deliberately absent."""

    user_id: int
    username: str
    display_name: str | None
    current_albums: tuple[CurrentCollectionAlbumDTO, ...]
    historical_completions: tuple[HistoricalAlbumCompletionDTO, ...]
    valid_trophies: tuple[TrophyUnlockDTO, ...]
    successful_trade_count: int
    rating_average: Decimal | None
    rating_count: int
    collector_world_visible: bool = True

    @property
    def completed_album_count(self):
        return len(self.historical_completions)

    @property
    def trophy_count(self):
        return len(self.valid_trophies)

    @property
    def albums(self):
        return self.current_albums

    @property
    def active_albums(self):
        return self.current_albums

    @property
    def showcase_albums(self):
        return self.historical_completions

    @property
    def album_count(self):
        return len(self.current_albums)

    @property
    def duplicate_count(self):
        return 0


@dataclass(frozen=True)
class AccountSettingsDTO:
    """Owner-only account/settings projection, separate from public profile."""

    user_id: int
    username: str
    display_name: str | None
    profile_privacy: str | None
    account_state: str | None


@dataclass(frozen=True)
class PublicCollectorIdentityDTO:
    """Minimal public identity after the CB-006 outer privacy gate."""

    user_id: int
    username: str
    display_name: str | None


class PublicCollectorIdentityService:
    """Bulk identity projection for privacy-filtered consumers such as Feed."""

    def __init__(self, connection):
        self._connection = connection
        self._privacy = ProfilePrivacyService(connection)

    def visible_for_users(self, viewer_user_id, owner_user_ids):
        try:
            viewer = int(viewer_user_id)
            owners = tuple(sorted({int(value) for value in owner_user_ids}))
        except (TypeError, ValueError):
            return ()
        visible = self._privacy.visible_collector_world_owner_ids(viewer, owners)
        if not visible:
            return ()
        placeholders = ", ".join("?" for _ in visible)
        active_filter = (
            " AND account_state='active'"
            if account_lifecycle_schema_available(self._connection) else ""
        )
        rows = self._connection.execute(
            f"SELECT id, username, name FROM users "
            f"WHERE id IN ({placeholders}){active_filter} ORDER BY id",
            tuple(sorted(visible)),
        ).fetchall()
        return tuple(PublicCollectorIdentityDTO(
            user_id=int(row[0]),
            username=row[1],
            display_name=(row[2] or "").strip() or None,
        ) for row in rows)


class AccountSettingsService:
    def __init__(self, connection):
        self._connection = connection

    def for_owner(self, user_id):
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        privacy_column = "profile_privacy" if "profile_privacy" in columns else "NULL"
        state_column = "account_state" if "account_state" in columns else "NULL"
        row = self._connection.execute(
            f"SELECT id, username, name, {privacy_column}, {state_column} "
            "FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return AccountSettingsDTO(
            user_id=int(row[0]),
            username=row[1],
            display_name=(row[2] or "").strip() or None,
            profile_privacy=row[3],
            account_state=row[4],
        )


class CollectorProfileService:
    """Privacy-gated CB-014 projection for own and foreign profiles."""

    def __init__(self, connection, friendship_checker=None):
        self._connection = connection
        self._privacy = AlbumPrivacyService(connection, friendship_checker)
        self._profile_privacy = ProfilePrivacyService(
            connection, friendship_checker=friendship_checker
        )

    def by_username(self, username, viewer_user_id=None):
        active_filter = (
            " AND account_state='active'"
            if account_lifecycle_schema_available(self._connection) else ""
        )
        user = self._connection.execute(
            f"SELECT id, username, name FROM users WHERE username=?{active_filter}",
            (username,),
        ).fetchone()
        return self._build(user, viewer_user_id) if user is not None else None

    def by_user_id(self, user_id, viewer_user_id=None):
        active_filter = (
            " AND account_state='active'"
            if account_lifecycle_schema_available(self._connection) else ""
        )
        user = self._connection.execute(
            f"SELECT id, username, name FROM users WHERE id=?{active_filter}",
            (user_id,),
        ).fetchone()
        return self._build(user, viewer_user_id) if user is not None else None

    def _empty(self, user):
        return CollectorProfileDTO(
            user_id=int(user["id"]),
            username=user["username"],
            display_name=None,
            current_albums=(),
            historical_completions=(),
            valid_trophies=(),
            successful_trade_count=0,
            rating_average=None,
            rating_count=0,
            collector_world_visible=False,
        )

    def _build(self, user, viewer_user_id):
        viewer_user_id = user["id"] if viewer_user_id is None else viewer_user_id
        visible = (
            self._profile_privacy.can_view_collector_world(
                viewer_user_id, user["id"]
            )
            if self._profile_privacy.schema_available else True
        )
        # CB-006 outer gate: no album, trophy, trade or rating reads before it.
        if not visible:
            return self._empty(user)

        current, completions = self._canonical_collection(
            int(user["id"]), int(viewer_user_id)
        )
        trophies = self._canonical_trophies(current)

        rating = TradeRatingService(self._connection).summary_for_user(user["id"])
        return CollectorProfileDTO(
            user_id=int(user["id"]),
            username=user["username"],
            display_name=(user["name"] or "").strip() or None,
            current_albums=current,
            historical_completions=completions,
            valid_trophies=trophies,
            successful_trade_count=StatisticsProjectionService(
                self._connection
            ).successful_trades_for_user(
                user["id"]
            ).successful_trade_count,
            rating_average=rating.average,
            rating_count=rating.rating_count,
            collector_world_visible=True,
        )

    def _canonical_collection(self, owner_user_id, viewer_user_id):
        projection = CollectionProjectionService(
            self._connection, self._privacy
        ).for_user(owner_user_id, viewer_user_id)
        return projection.current_albums, projection.historical_completions

    def _canonical_trophies(self, current_albums):
        if not canonical_trophy_schema_available(self._connection):
            return ()
        service = CanonicalTrophyUnlockService(self._connection)
        return service.unlocks_for_albums(
            album.user_album_id for album in current_albums
        )
