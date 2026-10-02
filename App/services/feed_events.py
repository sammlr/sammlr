from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from services.album_privacy import AlbumPrivacyService
from services.collector_profiles import PublicCollectorIdentityService
from services.historical_collection import (
    HistoricalCollectionService,
    HistoricalWriteConflict,
    HistoricalWriteResult,
)
from services.profile_privacy import ProfilePrivacyService


FEED_EVENT_TYPES = frozenset({
    "album_started",
    "album_completed",
    "trophy_unlocked",
    "sammlr_news",
})

# Audit 11 has not approved any non-completion trophy for the feed. Tests may
# inject an explicit allowlist to verify the producer without changing product
# policy. Completion is represented only by album_completed.
FEED_WORTHY_TROPHY_DEFINITION_IDS = frozenset()
CANONICAL_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)


class FeedEventError(ValueError):
    """A CB-007 feed operation violates the frozen event contract."""


def validate_feed_timestamp(value):
    text = str(value or "").strip()
    if CANONICAL_UTC.fullmatch(text) is None:
        raise FeedEventError("feed timestamp must use canonical UTC")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise FeedEventError("feed timestamp is invalid") from error
    return text


@dataclass(frozen=True)
class FeedItemDTO:
    id: int
    event_key: str
    event_type: str
    actor_user_id: int | None
    user_album_id: int | None
    album_id: str | None
    target_type: str
    target_key: str
    occurred_at: str
    news_title: str | None = None
    news_body: str | None = None
    news_target_path: str | None = None
    actor_username: str | None = None
    actor_display_name: str | None = None
    album_name: str | None = None


def feed_event_schema_available(connection):
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    return {"feed_events", "sammlr_news"}.issubset(tables)


class FeedEventService:
    """CB-007 event producers and current-state privacy-safe feed reads."""

    def __init__(self, connection, *, trophy_allowlist=None):
        self._connection = connection
        if not feed_event_schema_available(connection):
            raise RuntimeError("V0018 feed eventstore schema is not installed")
        self._history = HistoricalCollectionService(connection)
        self._trophy_allowlist = frozenset(
            FEED_WORTHY_TROPHY_DEFINITION_IDS
            if trophy_allowlist is None else trophy_allowlist
        )

    @staticmethod
    def _positive_integer(value, field_name):
        try:
            value = int(value)
        except (TypeError, ValueError) as error:
            raise FeedEventError(f"{field_name} must be a positive integer") from error
        if value <= 0:
            raise FeedEventError(f"{field_name} must be a positive integer")
        return value

    @staticmethod
    def _required_text(value, field_name):
        text = str(value or "").strip()
        if not text:
            raise FeedEventError(f"{field_name} must not be empty")
        return text

    def record_album_started(self, user_album_id):
        user_album_id = self._positive_integer(user_album_id, "user_album_id")
        row = self._connection.execute(
            """
            SELECT user_id, album_id, started_at, start_event_key
            FROM historical_album_records
            WHERE user_album_id=? AND started_at IS NOT NULL
            """,
            (user_album_id,),
        ).fetchone()
        if row is None or row[3] != f"album-start:{user_album_id}":
            raise FeedEventError("canonical album start is not available")
        occurred_at = validate_feed_timestamp(row[2])
        return self._history.record_feed_event(
            event_key=f"feed:album-start:{user_album_id}",
            event_type="album_started",
            actor_user_id=int(row[0]),
            user_album_id=user_album_id,
            target_type="album",
            target_key=row[1],
            occurred_at=occurred_at,
        )

    def record_album_completed(self, user_album_id):
        user_album_id = self._positive_integer(user_album_id, "user_album_id")
        row = self._connection.execute(
            """
            SELECT user_id, album_id, completed_at, completion_event_key
            FROM historical_album_records
            WHERE user_album_id=? AND completed_at IS NOT NULL
            """,
            (user_album_id,),
        ).fetchone()
        if row is None or row[3] != f"album-completion:{user_album_id}":
            raise FeedEventError("canonical album completion is not available")
        occurred_at = validate_feed_timestamp(row[2])
        return self._history.record_feed_event(
            event_key=f"feed:album-completion:{user_album_id}",
            event_type="album_completed",
            actor_user_id=int(row[0]),
            user_album_id=user_album_id,
            target_type="album",
            target_key=row[1],
            occurred_at=occurred_at,
        )

    def record_trophy_unlocked(self, canonical_trophy_unlock_id):
        unlock_id = self._positive_integer(
            canonical_trophy_unlock_id, "canonical_trophy_unlock_id"
        )
        row = self._connection.execute(
            """
            SELECT trophy_definition_id, user_album_id, user_id, album_id,
                   unlocked_at, source_type
            FROM canonical_trophy_unlocks
            WHERE id=?
            """,
            (unlock_id,),
        ).fetchone()
        if row is None:
            raise FeedEventError("canonical trophy unlock is not available")
        definition_id = row[0]
        if row[5] == "album_completion" or definition_id not in self._trophy_allowlist:
            return None
        occurred_at = validate_feed_timestamp(row[4])
        user_album_id = int(row[1])
        return self._history.record_feed_event(
            event_key=f"feed:trophy-unlock:{user_album_id}:{definition_id}",
            event_type="trophy_unlocked",
            actor_user_id=int(row[2]),
            user_album_id=user_album_id,
            target_type="trophy",
            target_key=definition_id,
            occurred_at=occurred_at,
        )

    def publish_news(
        self, news_key, *, title, body, target_path=None, published_at
    ):
        news_key = self._required_text(news_key, "news_key")
        title = self._required_text(title, "title")
        body = self._required_text(body, "body")
        published_at = validate_feed_timestamp(published_at)
        if target_path is not None:
            target_path = self._required_text(target_path, "target_path")
            if not target_path.startswith("/") or target_path.startswith("//"):
                raise FeedEventError("target_path must be an internal absolute path")

        savepoint = "cb007_publish_news"
        started_transaction = not self._connection.in_transaction
        if started_transaction:
            self._connection.execute("BEGIN IMMEDIATE")
        self._connection.execute(f"SAVEPOINT {savepoint}")
        try:
            event_key = f"feed:sammlr-news:{news_key}"
            result = self._history.record_feed_event(
                event_key=event_key,
                event_type="sammlr_news",
                target_type="news",
                target_key=news_key,
                occurred_at=published_at,
            )
            inserted = self._connection.execute(
                """
                INSERT OR IGNORE INTO sammlr_news
                    (news_key, event_key, title, body, target_path, published_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (news_key, event_key, title, body, target_path, published_at),
            )
            row = self._connection.execute(
                """
                SELECT event_key, title, body, target_path, published_at
                FROM sammlr_news WHERE news_key=?
                """,
                (news_key,),
            ).fetchone()
            expected = (event_key, title, body, target_path, published_at)
            if row is None or tuple(row) != expected:
                raise HistoricalWriteConflict(
                    "news idempotency key already records another fact"
                )
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self._connection.commit()
            return HistoricalWriteResult(result.record_id, inserted.rowcount == 1)
        except Exception:
            self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self._connection.rollback()
            raise

    def _visible_personal_events(self, viewer_user_id):
        rows = self._connection.execute(
            """
            SELECT id, event_key, event_type, actor_user_id, user_album_id,
                   album_id, target_type, target_key, occurred_at
            FROM feed_events
            WHERE event_type IN ('album_started', 'album_completed', 'trophy_unlocked')
            ORDER BY occurred_at DESC, event_key DESC
            """
        ).fetchall()
        if not rows:
            return []
        album_ids = sorted({
            int(row[4]) for row in rows if row[4] is not None
        })
        visible_album_ids = AlbumPrivacyService(
            self._connection
        ).visible_user_album_ids(
            viewer_user_id, album_ids, require_mutual_friend=True
        )

        candidate_rows = [
            row for row in rows
            if row[4] is not None and int(row[4]) in visible_album_ids
        ]
        identities = {
            identity.user_id: identity
            for identity in PublicCollectorIdentityService(
                self._connection
            ).visible_for_users(
                viewer_user_id,
                (row[3] for row in candidate_rows if row[3] is not None),
            )
        }
        album_ids_for_names = sorted({
            str(row[5]) for row in candidate_rows if row[5] is not None
        })
        album_names = {}
        if album_ids_for_names:
            placeholders = ", ".join("?" for _ in album_ids_for_names)
            album_names = {
                row[0]: row[1]
                for row in self._connection.execute(
                    f"SELECT id, name FROM albums WHERE id IN ({placeholders})",
                    album_ids_for_names,
                ).fetchall()
            }

        visible = []
        for row in candidate_rows:
            try:
                occurred_at = validate_feed_timestamp(row[8])
                actor_id = int(row[3])
                user_album_id = int(row[4])
            except (FeedEventError, TypeError, ValueError):
                continue
            if user_album_id not in visible_album_ids:
                continue
            identity = identities.get(actor_id)
            album_name = album_names.get(row[5])
            if identity is None or album_name is None:
                continue
            visible.append(FeedItemDTO(
                int(row[0]), row[1], row[2], actor_id, user_album_id,
                row[5], row[6], row[7], occurred_at,
                actor_username=identity.username,
                actor_display_name=identity.display_name,
                album_name=album_name,
            ))
        return visible

    def _latest_news(self):
        row = self._connection.execute(
            """
            SELECT e.id, e.event_key, e.event_type, e.target_type,
                   e.target_key, e.occurred_at, n.title, n.body, n.target_path,
                   n.published_at
            FROM feed_events e
            JOIN sammlr_news n ON n.event_key=e.event_key
            WHERE e.event_type='sammlr_news'
            ORDER BY e.occurred_at DESC, e.event_key DESC
            LIMIT 1
            """
        ).fetchone()
        if row is None or row[5] != row[9]:
            return None
        try:
            occurred_at = validate_feed_timestamp(row[5])
        except FeedEventError:
            return None
        target_path = row[8]
        if target_path is not None and (
            not str(target_path).startswith("/")
            or str(target_path).startswith("//")
        ):
            target_path = None
        return FeedItemDTO(
            int(row[0]), row[1], row[2], None, None, None,
            row[3], row[4], occurred_at, row[6], row[7], target_path,
        )

    def feed_for_user(self, viewer_user_id, *, limit=20):
        viewer = self._positive_integer(viewer_user_id, "viewer_user_id")
        if ProfilePrivacyService(self._connection).privacy_for_user(viewer) is None:
            return ()
        try:
            limit = int(limit)
        except (TypeError, ValueError) as error:
            raise FeedEventError("limit must be an integer") from error
        if limit <= 0:
            return ()
        limit = min(limit, 100)
        personal = self._visible_personal_events(viewer)
        items = personal[:limit]
        if len(items) < limit:
            news = self._latest_news()
            if news is not None:
                items.append(news)
        items.sort(key=lambda item: (item.occurred_at, item.event_key), reverse=True)
        return tuple(items[:limit])
