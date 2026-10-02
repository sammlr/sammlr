from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from services.inventory_availability import AvailabilityDTO, LegacyAvailabilityCalculator


AVAILABILITY_SNAPSHOT_VERSION = "S19-v1"


@dataclass(frozen=True)
class StickerAvailabilitySnapshotDTO:
    """Immutable S19 projection for one user/album/sticker identity."""

    sticker_code: str
    physical: int
    assigned: int
    reserved: int
    incoming_transit: int
    outgoing_transit: int
    available: int
    missing: bool
    duplicates: int
    effective_available: int
    reason_code: str
    explanation: str
    _availability: AvailabilityDTO

    @property
    def is_available(self):
        return self.effective_available > 0

    @property
    def reservable(self):
        return self.effective_available

    @property
    def availability(self):
        """Compatibility view for pre-S19 AvailabilityDTO consumers."""
        return self._availability

    @property
    def balance_is_valid(self):
        return self._availability.balance_is_valid


def _availability_snapshot_for(
    sticker_code,
    quantity=0,
    reserved=0,
    incoming_transit=0,
    outgoing_transit=0,
):
    availability = LegacyAvailabilityCalculator.from_quantity(
        quantity,
        reserved=reserved,
        incoming_transit=incoming_transit,
    )
    duplicates = max(availability.physical - availability.assigned, 0)
    return StickerAvailabilitySnapshotDTO(
        sticker_code=sticker_code,
        physical=availability.physical,
        assigned=availability.assigned,
        reserved=availability.reserved,
        incoming_transit=availability.incoming_transit,
        outgoing_transit=max(int(outgoing_transit), 0),
        available=availability.available,
        missing=availability.physical == 0,
        duplicates=duplicates,
        # In the current model outgoing positions have already left physical,
        # incoming positions are not physical yet, and active reservations are
        # already subtracted by AvailabilityDTO. No additional S19 rule exists.
        effective_available=availability.available,
        reason_code=availability.reason_code,
        explanation=availability.explanation,
        _availability=availability,
    )


@dataclass(frozen=True)
class AlbumAvailabilitySnapshotDTO:
    version: str
    captured_at: str
    user_id: int
    album_id: str
    stickers_by_code: Mapping[str, StickerAvailabilitySnapshotDTO]

    def sticker(self, sticker_code):
        snapshot = self.stickers_by_code.get(sticker_code)
        if snapshot is not None:
            return snapshot
        return _availability_snapshot_for(sticker_code)


@dataclass(frozen=True)
class StickerInventoryDTO:
    """Read-only projection of one row in the current stickers table."""

    id: int
    user_id: int
    album_id: str
    sticker_code: str
    status: str
    duplicates: int
    quantity: int
    reserved: int = 0
    incoming_transit: int = 0
    outgoing_transit: int = 0
    snapshot: StickerAvailabilitySnapshotDTO | None = None

    @property
    def physical(self):
        return self.snapshot.physical

    @property
    def assigned(self):
        return self.snapshot.assigned

    @property
    def duplicate_quantity(self):
        return self.snapshot.available

    @property
    def available(self):
        return self.snapshot.effective_available

    @property
    def availability(self):
        return self.snapshot.availability

    def __getitem__(self, key):
        """Compatibility adapter for existing row-style collection views."""
        if key in {
            "id",
            "user_id",
            "album_id",
            "sticker_code",
            "status",
            "duplicates",
            "quantity",
            "reserved",
            "incoming_transit",
            "outgoing_transit",
        }:
            return getattr(self, key)
        raise KeyError(key)


@dataclass(frozen=True)
class AlbumProgressDTO:
    collected: int
    duplicate_quantity: int
    total: int
    percent: int


@dataclass(frozen=True)
class MatchingInventoryStateDTO:
    """Minimal S19 state needed by read-only market projections."""

    missing_codes: frozenset[str]
    available_codes: frozenset[str]


@dataclass(frozen=True)
class AlbumMarketProjectionDTO:
    market_codes: frozenset[str]
    get_codes_by_user: Mapping[int, frozenset[str]]
    give_codes_by_user: Mapping[int, frozenset[str]]


@dataclass(frozen=True)
class CollectionInventorySummaryDTO:
    progress: AlbumProgressDTO
    matching_state: MatchingInventoryStateDTO
    physical_quantity: int


@dataclass(frozen=True)
class AlbumInventoryDTO:
    user_id: int
    album_id: str
    items_by_code: Mapping[str, StickerInventoryDTO]
    incoming_by_code: Mapping[str, int]
    outgoing_by_code: Mapping[str, int]
    availability_snapshot: AlbumAvailabilitySnapshotDTO

    def quantity(self, sticker_code):
        item = self.items_by_code.get(sticker_code)
        return item.quantity if item else 0

    def availability_snapshot_for(self, sticker_code):
        return self.availability_snapshot.sticker(sticker_code)

    def availability(self, sticker_code):
        """Compatibility adapter; new readers use availability_snapshot_for()."""
        return self.availability_snapshot_for(sticker_code).availability

    @property
    def snapshots(self):
        return self.availability_snapshot.stickers_by_code

    @property
    def availabilities(self):
        return MappingProxyType({
            code: snapshot.availability
            for code, snapshot in self.snapshots.items()
        })

    @property
    def quantities(self):
        return MappingProxyType({
            code: item.quantity
            for code, item in self.items_by_code.items()
        })

    def progress(self, catalog_codes: Iterable[str], total: int):
        codes = tuple(catalog_codes)
        collected = sum(not self.availability_snapshot_for(code).missing for code in codes)
        duplicate_quantity = sum(
            self.availability_snapshot_for(code).available
            for code in codes
        )
        percent = int((collected / total) * 100)
        return AlbumProgressDTO(
            collected=collected,
            duplicate_quantity=duplicate_quantity,
            total=total,
            percent=percent,
        )


class InventoryReadService:
    """Central read-only access to inventory and S19 availability snapshots."""

    def __init__(self, connection):
        self._connection = connection

    def _table_exists(self, table_name):
        return self._connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table_name,),
        ).fetchone() is not None

    def _reserved_by_code(self, user_id, album_id):
        if not self._table_exists("trade_reservations"):
            return {}
        return {
            row["sticker_code"]: row["reserved"]
            for row in self._connection.execute(
                """
                SELECT sticker_code, SUM(quantity) AS reserved
                FROM trade_reservations
                WHERE user_id=? AND album_id=? AND state='active'
                GROUP BY sticker_code
                """,
                (user_id, album_id),
            ).fetchall()
        }

    def _transit_by_code(self, user_id, album_id, direction):
        if direction not in {"incoming", "outgoing"}:
            raise ValueError("direction must be incoming or outgoing")
        if not self._table_exists("trade_shipping_status"):
            return {}

        receipt_join = ""
        receipt_filter = ""
        if self._table_exists("trade_receipt_status"):
            receipt_join = (
                "LEFT JOIN trade_receipt_status receipt "
                "ON receipt.trade_id=t.id"
            )
            receipt_filter = """
                AND (
                  (p.to_user_id=t.requester_user_id
                   AND COALESCE(receipt.requester_received, 0)=0)
                  OR
                  (p.to_user_id=t.partner_user_id
                   AND COALESCE(receipt.partner_received, 0)=0)
                )
            """

        problem_join = ""
        transit_quantity = "p.quantity"
        problem_filter = ""
        if self._table_exists("trade_receipt_report_positions"):
            problem_join = (
                "LEFT JOIN trade_receipt_report_positions problem_position "
                "ON problem_position.trade_position_id=p.id"
            )
            transit_quantity = """
                p.quantity
                - COALESCE(problem_position.initial_received_quantity, 0)
                - COALESCE(problem_position.resolution_received_quantity, 0)
            """
            problem_filter = f"AND ({transit_quantity}) > 0"

        user_column = "p.to_user_id" if direction == "incoming" else "p.from_user_id"
        rows = self._connection.execute(
            f"""
            SELECT p.sticker_code,
                   SUM({transit_quantity}) AS transit_quantity
            FROM trade_positions p
            JOIN trades t ON t.id=p.trade_id
            JOIN trade_shipping_status s ON s.trade_id=t.id
            {receipt_join}
            {problem_join}
            WHERE {user_column}=? AND p.album_id=?
              AND t.lifecycle_state NOT IN (
                  'closed_with_problem',
                  'problem_resolved_after_close'
              )
              AND (
                (p.from_user_id=t.requester_user_id AND s.requester_shipped=1)
                OR
                (p.from_user_id=t.partner_user_id AND s.partner_shipped=1)
              )
              {receipt_filter}
              {problem_filter}
            GROUP BY p.sticker_code
            """,
            (user_id, album_id),
        ).fetchall()
        return {
            row["sticker_code"]: max(int(row["transit_quantity"] or 0), 0)
            for row in rows
        }

    def album(self, user_id, album_id, catalog_codes=()):
        reserved_by_code = self._reserved_by_code(user_id, album_id)
        incoming_by_code = self._transit_by_code(user_id, album_id, "incoming")
        outgoing_by_code = self._transit_by_code(user_id, album_id, "outgoing")
        rows = self._connection.execute(
            """
            SELECT id, user_id, album_id, sticker_code, status,
                   duplicates, quantity
            FROM stickers
            WHERE user_id=? AND album_id=?
            """,
            (user_id, album_id),
        ).fetchall()
        captured_at = self._connection.execute(
            "SELECT STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now') AS captured_at"
        ).fetchone()["captured_at"]

        rows_by_code = {row["sticker_code"]: row for row in rows}
        codes = set(catalog_codes)
        codes.update(rows_by_code)
        codes.update(reserved_by_code)
        codes.update(incoming_by_code)
        codes.update(outgoing_by_code)

        snapshots = {}
        for code in codes:
            row = rows_by_code.get(code)
            snapshots[code] = _availability_snapshot_for(
                code,
                quantity=row["quantity"] if row else 0,
                reserved=reserved_by_code.get(code, 0),
                incoming_transit=incoming_by_code.get(code, 0),
                outgoing_transit=outgoing_by_code.get(code, 0),
            )

        snapshot_dto = AlbumAvailabilitySnapshotDTO(
            version=AVAILABILITY_SNAPSHOT_VERSION,
            captured_at=captured_at,
            user_id=user_id,
            album_id=album_id,
            stickers_by_code=MappingProxyType(snapshots),
        )

        items = {}
        for code, row in rows_by_code.items():
            item = StickerInventoryDTO(
                id=row["id"],
                user_id=row["user_id"],
                album_id=row["album_id"],
                sticker_code=code,
                status=row["status"],
                duplicates=row["duplicates"],
                quantity=row["quantity"],
                reserved=reserved_by_code.get(code, 0),
                incoming_transit=incoming_by_code.get(code, 0),
                outgoing_transit=outgoing_by_code.get(code, 0),
                snapshot=snapshots[code],
            )
            items[code] = item

        return AlbumInventoryDTO(
            user_id=user_id,
            album_id=album_id,
            items_by_code=MappingProxyType(items),
            incoming_by_code=MappingProxyType(incoming_by_code),
            outgoing_by_code=MappingProxyType(outgoing_by_code),
            availability_snapshot=snapshot_dto,
        )

    def snapshot(self, user_id, album_id, catalog_codes=()):
        return self.album(
            user_id, album_id, catalog_codes
        ).availability_snapshot

    def matching_states(self, user_ids, album_id, catalog_codes):
        """Load matching-relevant inventory for many users in two queries.

        Matching only depends on the S19 ``missing`` and
        ``effective_available`` values. Incoming/outgoing transit never changes
        either value, so the full per-user album snapshot would add redundant
        lifecycle queries without changing the result.
        """

        users = tuple(dict.fromkeys(int(user_id) for user_id in user_ids))
        codes = frozenset(catalog_codes)
        if not users:
            return MappingProxyType({})

        placeholders = ", ".join("?" for _ in users)
        rows = self._connection.execute(
            f"""
            SELECT user_id, sticker_code, quantity
            FROM stickers
            WHERE album_id=? AND user_id IN ({placeholders})
            """,
            (album_id, *users),
        ).fetchall()
        quantities = {
            (int(row["user_id"]), row["sticker_code"]): max(
                int(row["quantity"] or 0), 0
            )
            for row in rows
            if row["sticker_code"] in codes
        }

        reserved = {}
        if self._table_exists("trade_reservations"):
            reserved = {
                (int(row["user_id"]), row["sticker_code"]): max(
                    int(row["reserved"] or 0), 0
                )
                for row in self._connection.execute(
                    f"""
                    SELECT user_id, sticker_code, SUM(quantity) AS reserved
                    FROM trade_reservations
                    WHERE album_id=? AND state='active'
                      AND user_id IN ({placeholders})
                    GROUP BY user_id, sticker_code
                    """,
                    (album_id, *users),
                ).fetchall()
                if row["sticker_code"] in codes
            }

        states = {}
        for user_id in users:
            physical_codes = {
                code for code in codes
                if quantities.get((user_id, code), 0) > 0
            }
            available_codes = {
                code for code in physical_codes
                if quantities[(user_id, code)]
                - 1
                - reserved.get((user_id, code), 0) > 0
            }
            states[user_id] = MatchingInventoryStateDTO(
                missing_codes=frozenset(codes - physical_codes),
                available_codes=frozenset(available_codes),
            )
        return MappingProxyType(states)

    def album_market_projection(
        self, subject_user_id, other_user_ids, album_id, catalog_codes,
        subject_state=None,
    ):
        """Project directed match sets without materializing every album wall."""

        subject = int(subject_user_id)
        others = tuple(sorted({
            int(user_id) for user_id in other_user_ids
            if int(user_id) != subject
        }))
        if subject_state is None:
            subject_state = self.matching_states(
                (subject,), album_id, catalog_codes
            )[subject]
        empty = MappingProxyType({user_id: frozenset() for user_id in others})
        if not others or not subject_state.missing_codes:
            return AlbumMarketProjectionDTO(frozenset(), empty, empty)

        user_placeholders = ", ".join("?" for _ in others)
        missing = tuple(sorted(subject_state.missing_codes))
        code_placeholders = ", ".join("?" for _ in missing)
        reserved = {}
        if self._table_exists("trade_reservations"):
            reserved = {
                (int(row["user_id"]), row["sticker_code"]): max(
                    int(row["reserved"] or 0), 0
                )
                for row in self._connection.execute(
                    f"""
                    SELECT user_id, sticker_code, SUM(quantity) AS reserved
                    FROM trade_reservations
                    WHERE album_id=? AND state='active'
                      AND user_id IN ({user_placeholders})
                      AND sticker_code IN ({code_placeholders})
                    GROUP BY user_id, sticker_code
                    """,
                    (album_id, *others, *missing),
                ).fetchall()
            }

        get_codes = {user_id: set() for user_id in others}
        for row in self._connection.execute(
            f"""
            SELECT user_id, sticker_code, quantity
            FROM stickers
            WHERE album_id=? AND user_id IN ({user_placeholders})
              AND sticker_code IN ({code_placeholders})
              AND quantity > 1
            """,
            (album_id, *others, *missing),
        ).fetchall():
            identity = (int(row["user_id"]), row["sticker_code"])
            if int(row["quantity"]) - 1 - reserved.get(identity, 0) > 0:
                get_codes[identity[0]].add(identity[1])

        matching_users = tuple(
            user_id for user_id in others if get_codes[user_id]
        )
        give_codes = {user_id: set() for user_id in others}
        if matching_users and subject_state.available_codes:
            match_user_placeholders = ", ".join("?" for _ in matching_users)
            available = tuple(sorted(subject_state.available_codes))
            available_placeholders = ", ".join("?" for _ in available)
            physical_by_user = {user_id: set() for user_id in matching_users}
            for row in self._connection.execute(
                f"""
                SELECT user_id, sticker_code
                FROM stickers
                WHERE album_id=? AND user_id IN ({match_user_placeholders})
                  AND sticker_code IN ({available_placeholders})
                  AND quantity > 0
                """,
                (album_id, *matching_users, *available),
            ).fetchall():
                physical_by_user[int(row["user_id"])].add(row["sticker_code"])
            for user_id in matching_users:
                give_codes[user_id].update(
                    subject_state.available_codes - physical_by_user[user_id]
                )

        return AlbumMarketProjectionDTO(
            market_codes=frozenset().union(*get_codes.values()),
            get_codes_by_user=MappingProxyType({
                user_id: frozenset(values)
                for user_id, values in get_codes.items()
            }),
            give_codes_by_user=MappingProxyType({
                user_id: frozenset(values)
                for user_id, values in give_codes.items()
            }),
        )

    def collection_summaries(self, user_id, album_catalogs, album_totals):
        """Load all current collection-card values from one inventory read."""

        user = int(user_id)
        catalogs = {
            album_id: frozenset(codes)
            for album_id, codes in album_catalogs.items()
        }
        quantities = {
            (row["album_id"], row["sticker_code"]): max(
                int(row["quantity"] or 0), 0
            )
            for row in self._connection.execute(
                """
                SELECT album_id, sticker_code, quantity
                FROM stickers
                WHERE user_id=?
                """,
                (user,),
            ).fetchall()
        }
        reserved = {}
        if self._table_exists("trade_reservations"):
            reserved = {
                (row["album_id"], row["sticker_code"]): max(
                    int(row["reserved"] or 0), 0
                )
                for row in self._connection.execute(
                    """
                    SELECT album_id, sticker_code, SUM(quantity) AS reserved
                    FROM trade_reservations
                    WHERE user_id=? AND state='active'
                    GROUP BY album_id, sticker_code
                    """,
                    (user,),
                ).fetchall()
            }

        summaries = {}
        for album_id, codes in catalogs.items():
            physical = {
                code for code in codes
                if quantities.get((album_id, code), 0) > 0
            }
            available = {
                code for code in physical
                if quantities[(album_id, code)]
                - 1
                - reserved.get((album_id, code), 0) > 0
            }
            duplicate_quantity = sum(
                max(
                    quantities[(album_id, code)]
                    - 1
                    - reserved.get((album_id, code), 0),
                    0,
                )
                for code in physical
            )
            total = int(album_totals[album_id])
            collected = len(physical)
            summaries[album_id] = CollectionInventorySummaryDTO(
                progress=AlbumProgressDTO(
                    collected=collected,
                    duplicate_quantity=duplicate_quantity,
                    total=total,
                    percent=int((collected / total) * 100),
                ),
                matching_state=MatchingInventoryStateDTO(
                    missing_codes=frozenset(codes - physical),
                    available_codes=frozenset(available),
                ),
                physical_quantity=sum(
                    quantities.get((album_id, code), 0) for code in codes
                ),
            )
        return MappingProxyType(summaries)
