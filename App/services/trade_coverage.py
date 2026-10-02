from __future__ import annotations

from dataclasses import dataclass

from services.album_privacy import AlbumPrivacyService
from services.inventory import InventoryReadService


COVERAGE_SCOPE = "distinct_codes/current_album/current_snapshot"
COVERAGE_CONFIDENCE = "exact_for_supplied_users_and_snapshot_state"


def _distinct_codes(catalog_codes):
    return tuple(dict.fromkeys(catalog_codes))


def _coverage_percent(covered, missing):
    if missing == 0:
        return None
    return int((covered / missing) * 100)


@dataclass(frozen=True)
class CommunityMarketCoverageDTO:
    user_id: int
    album_id: str
    missing_count: int
    available_in_community_count: int
    unavailable_count: int
    coverage_percent: int | None
    missing_codes: tuple[str, ...]
    available_codes: tuple[str, ...]
    unavailable_codes: tuple[str, ...]
    community_user_count: int
    scope: str = COVERAGE_SCOPE
    confidence: str = COVERAGE_CONFIDENCE

    @property
    def has_missing(self):
        return self.missing_count > 0


@dataclass(frozen=True)
class PersonalTradeCoverageDTO:
    user_id: int
    counterpart_user_id: int
    album_id: str
    missing_count: int
    present_at_counterpart_count: int
    effectively_available_count: int
    coverage_percent: int | None
    missing_codes: tuple[str, ...]
    present_at_counterpart_codes: tuple[str, ...]
    effectively_available_codes: tuple[str, ...]
    scope: str = COVERAGE_SCOPE
    confidence: str = COVERAGE_CONFIDENCE

    @property
    def has_missing(self):
        return self.missing_count > 0


class TradeCoverageService:
    """Read-only S20 metrics derived exclusively from S19 snapshots."""

    def __init__(self, inventory_read_service: InventoryReadService, trade_pool=None):
        self._inventory = inventory_read_service
        self._trade_pool = trade_pool or AlbumPrivacyService(
            inventory_read_service._connection
        )
        from services.community import CommunityService
        self._community = CommunityService(inventory_read_service._connection)

    def _pool_enabled(self, user_id, album_id):
        return (
            self._trade_pool.is_trade_pool_enabled(user_id, album_id)
        )

    def community_market_coverage(
        self,
        user_id,
        album_id,
        catalog_codes,
        community_user_ids,
    ):
        codes = _distinct_codes(catalog_codes)
        subject = self._inventory.snapshot(user_id, album_id, codes)
        missing_codes = tuple(
            code for code in codes if subject.sticker(code).missing
        )

        subject_pool_enabled = self._pool_enabled(user_id, album_id)
        other_user_ids = tuple(
            candidate_id
            for candidate_id in dict.fromkeys(community_user_ids)
            if (
                candidate_id != user_id
                and self._community.can_start_interaction(user_id, candidate_id)
                and subject_pool_enabled
                and self._pool_enabled(candidate_id, album_id)
            )
        )
        community = tuple(
            self._inventory.snapshot(candidate_id, album_id, codes)
            for candidate_id in other_user_ids
        )
        available_codes = tuple(
            code
            for code in missing_codes
            if any(
                snapshot.sticker(code).effective_available > 0
                for snapshot in community
            )
        )
        available = set(available_codes)
        unavailable_codes = tuple(
            code for code in missing_codes if code not in available
        )

        return CommunityMarketCoverageDTO(
            user_id=user_id,
            album_id=album_id,
            missing_count=len(missing_codes),
            available_in_community_count=len(available_codes),
            unavailable_count=len(unavailable_codes),
            coverage_percent=_coverage_percent(
                len(available_codes), len(missing_codes)
            ),
            missing_codes=missing_codes,
            available_codes=available_codes,
            unavailable_codes=unavailable_codes,
            community_user_count=len(other_user_ids),
        )

    def personal_trade_coverage(
        self,
        user_id,
        counterpart_user_id,
        album_id,
        catalog_codes,
    ):
        codes = _distinct_codes(catalog_codes)
        subject = self._inventory.snapshot(user_id, album_id, codes)
        counterpart = self._inventory.snapshot(
            counterpart_user_id, album_id, codes
        )
        missing_codes = tuple(
            code for code in codes if subject.sticker(code).missing
        )
        pair_pool_enabled = (
            self._pool_enabled(user_id, album_id)
            and self._pool_enabled(counterpart_user_id, album_id)
            and self._community.can_start_interaction(user_id, counterpart_user_id)
        )
        present_codes = tuple(
            code
            for code in missing_codes
            if pair_pool_enabled and counterpart.sticker(code).physical > 0
        )
        effective_codes = tuple(
            code
            for code in missing_codes
            if (
                pair_pool_enabled
                and counterpart.sticker(code).effective_available > 0
            )
        )

        return PersonalTradeCoverageDTO(
            user_id=user_id,
            counterpart_user_id=counterpart_user_id,
            album_id=album_id,
            missing_count=len(missing_codes),
            present_at_counterpart_count=len(present_codes),
            effectively_available_count=len(effective_codes),
            coverage_percent=_coverage_percent(
                len(effective_codes), len(missing_codes)
            ),
            missing_codes=missing_codes,
            present_at_counterpart_codes=present_codes,
            effectively_available_codes=effective_codes,
        )
