from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import sqlite3

from services.historical_collection import HistoricalCollectionService
from trophy_definitions import (
    GLOBAL_SCOPE,
    canonical_album_trophy_definitions,
)


VALID_CANONICAL_TROPHY = "VALID_CANONICAL_TROPHY"
VALID_COMPLETION_EVIDENCE = "VALID_COMPLETION_EVIDENCE"
VALID_BOTH = "VALID_BOTH"
LEGACY_GLOBAL = "LEGACY_GLOBAL"
LEGACY_GENERIC = "LEGACY_GENERIC"
NO_CANONICAL_CATALOG = "NO_CANONICAL_CATALOG"
AMBIGUOUS = "AMBIGUOUS"
INVALID = "INVALID"

CANONICAL_TROPHY = "CANONICAL_TROPHY"
HISTORICAL_COMPLETION = "HISTORICAL_COMPLETION"
BOTH = "BOTH"
NONE = "NONE"

GENERIC_NAMES = frozenset({"Erster Sticker", "Halbzeit", "Endspurt"})
COMPLETION_NAME = "Album vollendet"


class LegacyTrophyBackfillError(RuntimeError):
    """The controlled CB-004 operation cannot be performed safely."""


@dataclass(frozen=True)
class LegacyTrophyAuditRow:
    legacy_row_id: int
    user_id: int | None
    album_id: str | None
    user_album_id: int | None
    legacy_trophy_name: str | None
    legacy_unlocked_at: str | None
    normalized_unlocked_at: str | None
    canonical_trophy_definition_id: str | None
    trophy_type: str
    category: str
    validation_status: str
    reason: str
    allowed_backfill: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class LegacyTrophyAudit:
    rows: tuple[LegacyTrophyAuditRow, ...]

    @property
    def legacy_total(self):
        return len(self.rows)

    @property
    def trophy_candidates(self):
        return tuple(
            row for row in self.rows
            if row.allowed_backfill in {CANONICAL_TROPHY, BOTH}
        )

    @property
    def completion_candidates(self):
        return tuple(
            row for row in self.rows
            if row.allowed_backfill in {HISTORICAL_COMPLETION, BOTH}
        )

    @property
    def rejected(self):
        return tuple(row for row in self.rows if row.allowed_backfill == NONE)

    def summary(self):
        categories = {}
        statuses = {}
        allowed = {}
        for row in self.rows:
            categories[row.category] = categories.get(row.category, 0) + 1
            statuses[row.validation_status] = statuses.get(
                row.validation_status, 0
            ) + 1
            allowed[row.allowed_backfill] = allowed.get(row.allowed_backfill, 0) + 1
        return {
            "legacy_rows_total": self.legacy_total,
            "legacy_rows_checked": self.legacy_total,
            "categories": dict(sorted(categories.items())),
            "validation_statuses": dict(sorted(statuses.items())),
            "allowed_backfills": dict(sorted(allowed.items())),
            "canonical_trophy_candidates": len(self.trophy_candidates),
            "historical_completion_candidates": len(self.completion_candidates),
            "rejected_or_already_present": len(self.rejected),
        }

    def to_dict(self):
        return {
            "mode": "dry-run",
            "summary": self.summary(),
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class LegacyTrophyApplyResult:
    audit: LegacyTrophyAudit
    created_canonical_trophies: int
    created_historical_completions: int

    def to_dict(self):
        return {
            "mode": "apply",
            "summary": self.audit.summary(),
            "created_canonical_trophies": self.created_canonical_trophies,
            "created_historical_completions": self.created_historical_completions,
            "rows": [row.to_dict() for row in self.audit.rows],
        }


def normalize_legacy_unlock_timestamp(value, *, now=None):
    """Normalize only timestamps whose UTC semantics are explicit or structural.

    Legacy `unlocked_trophies.unlocked_at` was written by SQLite
    `CURRENT_TIMESTAMP`, whose documented value is UTC in the exact
    ``YYYY-MM-DD HH:MM:SS`` shape. ISO-8601 values additionally require an
    explicit offset or ``Z``. Other naive values are ambiguous and rejected.
    """

    text = str(value or "").strip()
    if not text:
        return None, "Legacy-Unlockzeitpunkt fehlt."
    parsed = None
    try:
        if len(text) == 19 and text[4] == "-" and text[10] == " ":
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        else:
            candidate = text.replace("Z", "+00:00") if text.endswith("Z") else text
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None, "Zeitzonensemantik des Legacy-Zeitpunkts ist unklar."
    except (TypeError, ValueError):
        return None, "Legacy-Unlockzeitpunkt ist nicht parsebar."
    parsed = parsed.astimezone(timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if parsed > reference.astimezone(timezone.utc):
        return None, "Legacy-Unlockzeitpunkt liegt offensichtlich in der Zukunft."
    return parsed.isoformat(timespec="microseconds").replace("+00:00", "Z"), None


class ValidatedLegacyTrophyBackfillService:
    """Deterministic dry-run and explicit apply for CB-004 legacy evidence."""

    def __init__(self, connection):
        self.connection = connection
        self._require_schema()

    def _require_schema(self):
        required = {"unlocked_trophies", "canonical_trophy_unlocks", "historical_album_records"}
        tables = {
            row[0] for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if not required.issubset(tables):
            raise LegacyTrophyBackfillError("CB-004 requires schema V0016")
        version = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]
        if int(version) < 16:
            raise LegacyTrophyBackfillError("CB-004 requires schema V0016")

    def _catalog(self, album_id):
        album = self.connection.execute(
            "SELECT total FROM albums WHERE id=?", (album_id,)
        ).fetchone()
        if album is None:
            return ()
        return canonical_album_trophy_definitions(album_id, int(album[0]))

    def _memberships(self, user_id, album_id):
        return self.connection.execute(
            """
            SELECT id FROM user_albums
            WHERE user_id=? AND album_id=?
            ORDER BY id
            """,
            (user_id, album_id),
        ).fetchall()

    def _existing_trophy(self, user_album_id, definition_id):
        return self.connection.execute(
            """
            SELECT trophy_name, unlocked_at, source_type, source_key,
                   trigger_sticker_code, event_key
            FROM canonical_trophy_unlocks
            WHERE user_album_id=? AND trophy_definition_id=?
            """,
            (user_album_id, definition_id),
        ).fetchone()

    def _existing_completion(self, user_album_id):
        return self.connection.execute(
            """
            SELECT completed_at, completion_event_key,
                   completion_source_type, completion_source_key
            FROM historical_album_records
            WHERE user_album_id=? AND completed_at IS NOT NULL
            """,
            (user_album_id,),
        ).fetchone()

    @staticmethod
    def _row(
        legacy,
        *,
        user_album_id=None,
        normalized=None,
        definition_id=None,
        trophy_type="unknown",
        category=INVALID,
        status="REJECTED",
        reason,
        allowed=NONE,
    ):
        return LegacyTrophyAuditRow(
            legacy_row_id=int(legacy[0]),
            user_id=int(legacy[1]) if legacy[1] is not None else None,
            album_id=legacy[2],
            user_album_id=user_album_id,
            legacy_trophy_name=legacy[3],
            legacy_unlocked_at=legacy[4],
            normalized_unlocked_at=normalized,
            canonical_trophy_definition_id=definition_id,
            trophy_type=trophy_type,
            category=category,
            validation_status=status,
            reason=reason,
            allowed_backfill=allowed,
        )

    def _audit_legacy_row(self, legacy, *, now):
        user_id, album_id, name = legacy[1], legacy[2], legacy[3]
        if album_id == GLOBAL_SCOPE:
            return self._row(
                legacy, trophy_type="global", category=LEGACY_GLOBAL,
                reason="Globale Legacy-Trophäen sind nicht Teil des kanonischen Katalogs.",
            )
        if user_id is None or not str(album_id or "").strip() or not str(name or "").strip():
            return self._row(
                legacy, reason="Nutzer-, Album- oder Trophy-Identität fehlt."
            )

        definitions = self._catalog(album_id)
        if not definitions:
            memberships = self._memberships(user_id, album_id)
            return self._row(
                legacy,
                user_album_id=int(memberships[0][0]) if len(memberships) == 1 else None,
                trophy_type="completion" if name == COMPLETION_NAME else "unknown",
                category=NO_CANONICAL_CATALOG,
                reason="Für dieses Album ist kein kanonischer Trophy-Katalog freigegeben.",
            )
        if name in GENERIC_NAMES:
            memberships = self._memberships(user_id, album_id)
            return self._row(
                legacy,
                user_album_id=int(memberships[0][0]) if len(memberships) == 1 else None,
                trophy_type="generic",
                category=LEGACY_GENERIC,
                reason="Generische Fortschritts-Trophäen sind Legacy und nicht backfillfähig.",
            )

        matching_definitions = tuple(
            definition for definition in definitions if definition["name"] == name
        )
        if len(matching_definitions) != 1:
            memberships = self._memberships(user_id, album_id)
            return self._row(
                legacy,
                user_album_id=int(memberships[0][0]) if len(memberships) == 1 else None,
                category=AMBIGUOUS,
                reason=(
                    "Legacy-Name besitzt kein exaktes kanonisches Mapping."
                    if not matching_definitions else
                    "Legacy-Name ist im kanonischen Katalog nicht eindeutig."
                ),
            )
        definition = matching_definitions[0]

        memberships = self._memberships(user_id, album_id)
        if len(memberships) == 0:
            return self._row(
                legacy,
                definition_id=definition["id"],
                trophy_type=("completion" if name == COMPLETION_NAME else "normal_album"),
                reason="Kein passendes Nutzeralbum für die Legacy-Evidenz vorhanden.",
            )
        if len(memberships) != 1:
            return self._row(
                legacy,
                definition_id=definition["id"],
                trophy_type=("completion" if name == COMPLETION_NAME else "normal_album"),
                category=AMBIGUOUS,
                reason="Mehrere Nutzeralben passen zur Legacy-Evidenz.",
            )
        user_album_id = int(memberships[0][0])
        normalized, timestamp_error = normalize_legacy_unlock_timestamp(
            legacy[4], now=now
        )
        if timestamp_error:
            return self._row(
                legacy,
                user_album_id=user_album_id,
                definition_id=definition["id"],
                trophy_type=("completion" if name == COMPLETION_NAME else "normal_album"),
                reason=timestamp_error,
            )

        completion = name == COMPLETION_NAME
        category = VALID_BOTH if completion else VALID_CANONICAL_TROPHY
        existing_trophy = self._existing_trophy(user_album_id, definition["id"])
        trophy_missing = existing_trophy is None
        if existing_trophy is not None and (
            existing_trophy[0] != name or existing_trophy[1] != normalized
        ):
            return self._row(
                legacy,
                user_album_id=user_album_id,
                normalized=normalized,
                definition_id=definition["id"],
                trophy_type=("completion" if completion else "normal_album"),
                category=category,
                status="CONFLICT",
                reason="Bestehender kanonischer Trophy-Unlock besitzt andere historische Fakten.",
            )

        completion_missing = False
        if completion:
            existing_completion = self._existing_completion(user_album_id)
            completion_missing = existing_completion is None
            if existing_completion is not None and existing_completion[0] != normalized:
                return self._row(
                    legacy,
                    user_album_id=user_album_id,
                    normalized=normalized,
                    definition_id=definition["id"],
                    trophy_type="completion",
                    category=category,
                    status="CONFLICT",
                    reason="Bestehender historischer Abschluss besitzt einen anderen Zeitpunkt.",
                )

        if trophy_missing and completion_missing:
            allowed = BOTH
        elif trophy_missing:
            allowed = CANONICAL_TROPHY
        elif completion_missing:
            allowed = HISTORICAL_COMPLETION
        else:
            allowed = NONE
        return self._row(
            legacy,
            user_album_id=user_album_id,
            normalized=normalized,
            definition_id=definition["id"],
            trophy_type=("completion" if completion else "normal_album"),
            category=category,
            status="ELIGIBLE" if allowed != NONE else "ALREADY_PRESENT",
            reason=(
                "Eindeutiges exaktes Mapping mit belastbarem UTC-Zeitpunkt."
                if allowed != NONE else
                "Bestehende kanonische Fakten stimmen zeitlich mit der Legacy-Evidenz überein."
            ),
            allowed=allowed,
        )

    def audit(self, *, now=None):
        reference = now or datetime.now(timezone.utc)
        legacy_rows = self.connection.execute(
            """
            SELECT id, user_id, album_id, trophy_name, unlocked_at
            FROM unlocked_trophies
            ORDER BY id
            """
        ).fetchall()
        rows = [self._audit_legacy_row(row, now=reference) for row in legacy_rows]
        return LegacyTrophyAudit(self._reconcile_duplicate_evidence(rows))

    @staticmethod
    def _reconcile_duplicate_evidence(rows):
        rows = list(rows)
        candidate_groups = {}
        for index, row in enumerate(rows):
            if row.allowed_backfill == NONE:
                continue
            key = (row.user_album_id, row.canonical_trophy_definition_id)
            candidate_groups.setdefault(key, []).append(index)
        for indexes in candidate_groups.values():
            if len(indexes) < 2:
                continue
            timestamps = {rows[index].normalized_unlocked_at for index in indexes}
            if len(timestamps) > 1:
                for index in indexes:
                    rows[index] = replace(
                        rows[index],
                        validation_status="CONFLICT",
                        reason=(
                            "Mehrere Legacy-Evidenzen für dieselbe kanonische "
                            "Trophäe besitzen widersprüchliche Zeitpunkte."
                        ),
                        allowed_backfill=NONE,
                    )
                continue
            for index in indexes[1:]:
                rows[index] = replace(
                    rows[index],
                    validation_status="REDUNDANT_EVIDENCE",
                    reason=(
                        "Identische Legacy-Evidenz ist bereits durch die "
                        "kleinste Legacy-Row-ID repräsentiert."
                    ),
                    allowed_backfill=NONE,
                )
        return tuple(rows)

    @staticmethod
    def _source_key(row):
        return f"legacy-trophy:{row.legacy_row_id}"

    def _record_trophy(self, row):
        source_key = self._source_key(row)
        inserted = self.connection.execute(
            """
            INSERT INTO canonical_trophy_unlocks
                (event_key, trophy_definition_id, user_album_id, user_id,
                 album_id, trophy_name, unlocked_at, source_type,
                 source_key, trigger_sticker_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'legacy_trophy_backfill', ?, NULL)
            """,
            (
                f"trophy-backfill:{source_key}",
                row.canonical_trophy_definition_id,
                row.user_album_id,
                row.user_id,
                row.album_id,
                row.legacy_trophy_name,
                row.normalized_unlocked_at,
                source_key,
            ),
        )
        return inserted.rowcount == 1

    def _record_completion(self, row):
        source_key = self._source_key(row)
        return HistoricalCollectionService(
            self.connection
        ).record_first_album_completion(
            row.user_album_id,
            completed_at=row.normalized_unlocked_at,
            event_key=f"album-completion-backfill:{source_key}",
            source_type="validated_trophy",
            source_key=source_key,
        ).created

    def apply(self, *, now=None):
        savepoint = "cb004_validated_backfill"
        started_transaction = not self.connection.in_transaction
        if started_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        self.connection.execute(f"SAVEPOINT {savepoint}")
        try:
            audit = self.audit(now=now)
            created_trophies = 0
            created_completions = 0
            for row in audit.rows:
                if row.allowed_backfill in {CANONICAL_TROPHY, BOTH}:
                    created_trophies += int(self._record_trophy(row))
                if row.allowed_backfill in {HISTORICAL_COMPLETION, BOTH}:
                    created_completions += int(self._record_completion(row))
            self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self.connection.commit()
            return LegacyTrophyApplyResult(
                audit, created_trophies, created_completions
            )
        except Exception:
            self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            if started_transaction:
                self.connection.rollback()
            raise
