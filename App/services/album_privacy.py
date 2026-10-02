from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.profile_privacy import ProfilePrivacyService


ALBUM_VISIBILITIES = frozenset({"public", "friends", "private"})
DEFAULT_ALBUM_VISIBILITY = "private"


def album_privacy_schema_available(connection):
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(user_albums)").fetchall()
    }
    return {"visibility", "trade_pool_enabled"}.issubset(columns)


@dataclass(frozen=True)
class AlbumAccessDTO:
    owner_user_id: int
    album_id: str
    visibility: str
    trade_pool_enabled: bool


class AlbumPrivacyUpdateCode(str, Enum):
    UPDATED = "updated"
    NOT_FOUND = "not_found"
    INVALID_VISIBILITY = "invalid_visibility"
    UNAUTHORIZED = "unauthorized"


@dataclass(frozen=True)
class AlbumPrivacyUpdateResultDTO:
    code: AlbumPrivacyUpdateCode
    access: AlbumAccessDTO | None


class AlbumPrivacyService:
    """S27 visibility and independent trade-pool policy for user albums."""

    def __init__(self, connection, friendship_checker=None):
        self._connection = connection
        if friendship_checker is None:
            from services.community import CommunityService
            friendship_checker = CommunityService(connection).are_friends
        self._friendship_checker = friendship_checker
        self._schema_available = album_privacy_schema_available(connection)
        self._profile_privacy = ProfilePrivacyService(
            connection, friendship_checker=friendship_checker
        )

    @property
    def schema_available(self):
        return self._schema_available

    def access(self, owner_user_id, album_id):
        columns = (
            "user_id, album_id, visibility, trade_pool_enabled"
            if self._schema_available else
            "user_id, album_id, 'public' AS visibility, 1 AS trade_pool_enabled"
        )
        row = self._connection.execute(
            f"""
            SELECT {columns}
            FROM user_albums
            WHERE user_id=? AND album_id=?
            """,
            (owner_user_id, album_id),
        ).fetchone()
        if row is None:
            return None
        return AlbumAccessDTO(
            owner_user_id=int(row["user_id"]),
            album_id=row["album_id"],
            visibility=row["visibility"],
            trade_pool_enabled=bool(row["trade_pool_enabled"]),
        )

    def can_view(self, viewer_user_id, owner_user_id, album_id):
        try:
            viewer_user_id = int(viewer_user_id)
            owner_user_id = int(owner_user_id)
        except (TypeError, ValueError):
            return False
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        if "account_state" in columns:
            owner = self._connection.execute(
                "SELECT account_state FROM users WHERE id=?", (owner_user_id,)
            ).fetchone()
            if owner is None or owner[0] != "active":
                return False
        is_owner = viewer_user_id == owner_user_id
        # Historical schemas before CB-006 retain their S27 behavior for
        # migration-specific tests. The V0017 runtime always applies this gate.
        if (
            not is_owner
            and self._profile_privacy.schema_available
            and not self._profile_privacy.can_view_collector_world(
                viewer_user_id, owner_user_id
            )
        ):
            return False
        access = self.access(owner_user_id, album_id)
        if access is None:
            return False
        if is_owner:
            return True
        if access.visibility == "public":
            return True
        if access.visibility == "friends":
            return bool(self._friendship_checker(
                viewer_user_id, owner_user_id
            ))
        return False

    def visible_album_ids(self, viewer_user_id, owner_user_id):
        try:
            viewer_user_id = int(viewer_user_id)
            owner_user_id = int(owner_user_id)
        except (TypeError, ValueError):
            return ()
        user_columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        if "account_state" in user_columns:
            owner = self._connection.execute(
                "SELECT account_state FROM users WHERE id=?", (owner_user_id,)
            ).fetchone()
            if owner is None or owner[0] != "active":
                return ()
        if (
            viewer_user_id != owner_user_id
            and self._profile_privacy.schema_available
            and not self._profile_privacy.can_view_collector_world(
                viewer_user_id, owner_user_id
            )
        ):
            return ()
        visibility_select = (
            "visibility" if self._schema_available
            else "'public' AS visibility"
        )
        rows = self._connection.execute(
            f"SELECT album_id, {visibility_select} FROM user_albums "
            "WHERE user_id=? ORDER BY album_id",
            (owner_user_id,),
        ).fetchall()
        if viewer_user_id == owner_user_id:
            return tuple(row["album_id"] for row in rows)
        mutual_friend = None
        if any(row["visibility"] == "friends" for row in rows):
            mutual_friend = bool(self._friendship_checker(
                viewer_user_id, owner_user_id
            ))
        return tuple(
            row["album_id"]
            for row in rows
            if row["visibility"] == "public"
            or (row["visibility"] == "friends" and mutual_friend)
        )

    def visible_user_album_ids(
        self, viewer_user_id, user_album_ids, *, require_mutual_friend=False
    ):
        """Batch variant for privacy-sensitive projections such as the feed."""

        if not self._schema_available:
            return frozenset()
        try:
            viewer = int(viewer_user_id)
            membership_ids = frozenset(int(value) for value in user_album_ids)
        except (TypeError, ValueError):
            return frozenset()
        if not membership_ids:
            return frozenset()

        placeholders = ", ".join("?" for _ in membership_ids)
        rows = self._connection.execute(
            f"""
            SELECT id, user_id, visibility
            FROM user_albums
            WHERE id IN ({placeholders})
            """,
            tuple(sorted(membership_ids)),
        ).fetchall()
        owner_ids = {int(row[1]) for row in rows}
        outer_visible = self._profile_privacy.visible_collector_world_owner_ids(
            viewer, owner_ids
        )
        foreign = sorted(owner_ids - {viewer})
        mutual = set()
        if foreign:
            foreign_placeholders = ", ".join("?" for _ in foreign)
            mutual = {
                int(row[0])
                for row in self._connection.execute(
                    f"""
                    SELECT CASE
                        WHEN user_low_id=? THEN user_high_id ELSE user_low_id
                    END AS other_user_id
                    FROM friendships
                    WHERE (user_low_id=? AND user_high_id IN ({foreign_placeholders}))
                       OR (user_high_id=? AND user_low_id IN ({foreign_placeholders}))
                    """,
                    (viewer, viewer, *foreign, viewer, *foreign),
                ).fetchall()
            }

        return frozenset(
            int(row[0])
            for row in rows
            if int(row[1]) in outer_visible
            and (
                int(row[1]) == viewer
                or (
                    (not require_mutual_friend or int(row[1]) in mutual)
                    and (
                        row[2] == "public"
                        or (row[2] == "friends" and int(row[1]) in mutual)
                    )
                )
            )
        )

    def is_trade_pool_enabled(self, user_id, album_id):
        # Compatibility for V0000–V0006: before S27, callers could evaluate
        # explicitly supplied users without a persisted album membership.
        if not self._schema_available:
            return True
        access = self.access(user_id, album_id)
        return bool(access and access.trade_pool_enabled)

    def trade_pool_user_ids(self, album_id, excluded_user_id=None):
        condition = (
            "AND trade_pool_enabled=1" if self._schema_available else ""
        )
        account_columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_join = (
            "JOIN users ON users.id=user_albums.user_id AND users.account_state='active'"
            if "account_state" in account_columns else ""
        )
        rows = self._connection.execute(
            f"""
            SELECT user_albums.user_id
            FROM user_albums
            {active_join}
            WHERE user_albums.album_id=? {condition}
            ORDER BY user_albums.user_id
            """,
            (album_id,),
        ).fetchall()
        return tuple(
            int(row["user_id"])
            for row in rows
            if excluded_user_id is None or int(row["user_id"]) != int(excluded_user_id)
        )

    def trade_pool_user_ids_by_album(self, album_ids, excluded_user_id=None):
        albums = tuple(dict.fromkeys(str(album_id) for album_id in album_ids))
        if not albums:
            return {}
        condition = "AND user_albums.trade_pool_enabled=1" if self._schema_available else ""
        account_columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_join = (
            "JOIN users ON users.id=user_albums.user_id AND users.account_state='active'"
            if "account_state" in account_columns else ""
        )
        placeholders = ", ".join("?" for _ in albums)
        rows = self._connection.execute(
            f"""
            SELECT user_albums.album_id, user_albums.user_id
            FROM user_albums
            {active_join}
            WHERE user_albums.album_id IN ({placeholders}) {condition}
            ORDER BY user_albums.album_id, user_albums.user_id
            """,
            albums,
        ).fetchall()
        result = {album_id: [] for album_id in albums}
        for row in rows:
            user_id = int(row["user_id"])
            if excluded_user_id is None or user_id != int(excluded_user_id):
                result[row["album_id"]].append(user_id)
        return {
            album_id: tuple(user_ids)
            for album_id, user_ids in result.items()
        }

    def update(
        self,
        actor_user_id,
        owner_user_id,
        album_id,
        visibility,
        trade_pool_enabled,
    ):
        if visibility not in ALBUM_VISIBILITIES:
            return AlbumPrivacyUpdateResultDTO(
                AlbumPrivacyUpdateCode.INVALID_VISIBILITY, None
            )
        if int(actor_user_id) != int(owner_user_id):
            return AlbumPrivacyUpdateResultDTO(
                AlbumPrivacyUpdateCode.UNAUTHORIZED, None
            )
        current = self.access(owner_user_id, album_id)
        if current is None or not self._schema_available:
            return AlbumPrivacyUpdateResultDTO(
                AlbumPrivacyUpdateCode.NOT_FOUND, None
            )
        self._connection.execute(
            """
            UPDATE user_albums
            SET visibility=?, trade_pool_enabled=?
            WHERE user_id=? AND album_id=?
            """,
            (
                visibility,
                1 if trade_pool_enabled else 0,
                owner_user_id,
                album_id,
            ),
        )
        if (
            current.visibility != visibility
            or current.trade_pool_enabled != bool(trade_pool_enabled)
        ):
            from services.community import UserActivityService
            UserActivityService(self._connection).touch(actor_user_id)
        return AlbumPrivacyUpdateResultDTO(
            AlbumPrivacyUpdateCode.UPDATED,
            AlbumAccessDTO(
                int(owner_user_id),
                album_id,
                visibility,
                bool(trade_pool_enabled),
            ),
        )
