from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.community import CommunityService


PROFILE_PRIVACIES = frozenset({"public", "private"})
DEFAULT_PROFILE_PRIVACY = "public"


def profile_privacy_schema_available(connection):
    return "profile_privacy" in {
        row[1] for row in connection.execute("PRAGMA table_info(users)")
    }


@dataclass(frozen=True)
class ProfilePrivacyDecisionDTO:
    viewer_user_id: int
    owner_user_id: int
    profile_privacy: str | None
    owner: bool
    mutual_friend: bool
    blocked: bool
    can_view_collector_world: bool


class ProfilePrivacyUpdateCode(str, Enum):
    UPDATED = "updated"
    INVALID_PRIVACY = "invalid_privacy"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    SCHEMA_UNAVAILABLE = "schema_unavailable"


@dataclass(frozen=True)
class ProfilePrivacyUpdateResultDTO:
    code: ProfilePrivacyUpdateCode
    profile_privacy: str | None


class ProfilePrivacyService:
    """CB-006 outer profile gate; album privacy remains the inner policy."""

    def __init__(
        self, connection, friendship_checker=None, block_checker=None
    ):
        self._connection = connection
        community = CommunityService(connection)
        self._friendship_checker = (
            friendship_checker or community.are_friends
        )
        self._block_checker = (
            block_checker or community.is_blocked_between
        )
        self._schema_available = profile_privacy_schema_available(connection)

    @property
    def schema_available(self):
        return self._schema_available

    def privacy_for_user(self, user_id):
        if not self._schema_available:
            return None
        try:
            owner_user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_filter = (
            " AND account_state='active'" if "account_state" in columns else ""
        )
        row = self._connection.execute(
            f"SELECT profile_privacy FROM users WHERE id=?{active_filter}",
            (owner_user_id,),
        ).fetchone()
        if row is None or row[0] not in PROFILE_PRIVACIES:
            return None
        return row[0]

    def decision(self, viewer_user_id, owner_user_id):
        try:
            viewer = int(viewer_user_id)
            owner = int(owner_user_id)
        except (TypeError, ValueError):
            return ProfilePrivacyDecisionDTO(
                0, 0, None, False, False, False, False
            )
        privacy = self.privacy_for_user(owner)
        is_owner = viewer == owner and privacy in PROFILE_PRIVACIES
        if is_owner:
            return ProfilePrivacyDecisionDTO(
                viewer, owner, privacy, True, False, False, True
            )
        blocked = bool(
            privacy in PROFILE_PRIVACIES
            and self._block_checker(viewer, owner)
        )
        mutual_friend = bool(
            privacy in PROFILE_PRIVACIES
            and not blocked
            and self._friendship_checker(viewer, owner)
        )
        allowed = bool(
            privacy == "public" or (
                privacy == "private" and mutual_friend
            )
        ) and not blocked
        return ProfilePrivacyDecisionDTO(
            viewer,
            owner,
            privacy,
            False,
            mutual_friend,
            blocked,
            allowed,
        )

    def can_view_collector_world(self, viewer_user_id, owner_user_id):
        return self.decision(
            viewer_user_id, owner_user_id
        ).can_view_collector_world

    def visible_collector_world_owner_ids(self, viewer_user_id, owner_user_ids):
        """Return current outer-gate grants in a bounded number of queries."""

        if not self._schema_available:
            return frozenset()
        try:
            viewer = int(viewer_user_id)
            owners = frozenset(int(value) for value in owner_user_ids)
        except (TypeError, ValueError):
            return frozenset()
        if not owners:
            return frozenset()

        placeholders = ", ".join("?" for _ in owners)
        columns = {
            row[1] for row in self._connection.execute("PRAGMA table_info(users)")
        }
        active_filter = (
            " AND account_state='active'" if "account_state" in columns else ""
        )
        rows = self._connection.execute(
            f"SELECT id, profile_privacy FROM users "
            f"WHERE id IN ({placeholders}){active_filter}",
            tuple(sorted(owners)),
        ).fetchall()
        privacy_by_owner = {
            int(row[0]): row[1]
            for row in rows
            if row[1] in PROFILE_PRIVACIES
        }
        if not privacy_by_owner:
            return frozenset()

        foreign = set(privacy_by_owner) - {viewer}
        blocked = set()
        mutual = set()
        if foreign:
            foreign_placeholders = ", ".join("?" for _ in foreign)
            blocked = {
                int(row[0])
                for row in self._connection.execute(
                    f"""
                    SELECT CASE
                        WHEN blocker_user_id=? THEN blocked_user_id
                        ELSE blocker_user_id
                    END AS other_user_id
                    FROM blocks
                    WHERE (blocker_user_id=? AND blocked_user_id IN ({foreign_placeholders}))
                       OR (blocked_user_id=? AND blocker_user_id IN ({foreign_placeholders}))
                    """,
                    (viewer, viewer, *sorted(foreign), viewer, *sorted(foreign)),
                ).fetchall()
            }
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
                    (viewer, viewer, *sorted(foreign), viewer, *sorted(foreign)),
                ).fetchall()
            }

        return frozenset(
            owner
            for owner, privacy in privacy_by_owner.items()
            if owner == viewer or (
                owner not in blocked
                and (privacy == "public" or owner in mutual)
            )
        )

    def update(self, actor_user_id, owner_user_id, profile_privacy):
        if profile_privacy not in PROFILE_PRIVACIES:
            return ProfilePrivacyUpdateResultDTO(
                ProfilePrivacyUpdateCode.INVALID_PRIVACY, None
            )
        try:
            actor = int(actor_user_id)
            owner = int(owner_user_id)
        except (TypeError, ValueError):
            return ProfilePrivacyUpdateResultDTO(
                ProfilePrivacyUpdateCode.UNAUTHORIZED, None
            )
        if actor != owner:
            return ProfilePrivacyUpdateResultDTO(
                ProfilePrivacyUpdateCode.UNAUTHORIZED, None
            )
        if not self._schema_available:
            return ProfilePrivacyUpdateResultDTO(
                ProfilePrivacyUpdateCode.SCHEMA_UNAVAILABLE, None
            )
        cursor = self._connection.execute(
            "UPDATE users SET profile_privacy=? WHERE id=?",
            (profile_privacy, owner),
        )
        if cursor.rowcount != 1:
            return ProfilePrivacyUpdateResultDTO(
                ProfilePrivacyUpdateCode.NOT_FOUND, None
            )
        return ProfilePrivacyUpdateResultDTO(
            ProfilePrivacyUpdateCode.UPDATED, profile_privacy
        )
