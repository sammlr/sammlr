from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from services.executable_trade_matches import ExecutableTradeMatchService
from services.inventory import InventoryReadService
from services.trade_coverage import TradeCoverageService


MAX_SELECTED_PACKAGES = 3
OPTIMIZATION_VERSION = "CB011-v1"


@dataclass(frozen=True)
class StickerQuantityDTO:
    sticker_code: str
    quantity: int


@dataclass(frozen=True)
class TopMatchPackageDTO:
    partner_user_id: int
    receive_positions: tuple[StickerQuantityDTO, ...]
    give_positions: tuple[StickerQuantityDTO, ...]
    covered_missing_count: int
    personal_coverage_percent: int | None
    selection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class TopMatchConflictDTO:
    partner_user_id: int
    conflicting_give_codes: tuple[str, ...]
    reason_code: str = "own_effective_supply_already_allocated"


@dataclass(frozen=True)
class TopMatchOptimizationResultDTO:
    version: str
    user_id: int
    album_id: str
    packages: tuple[TopMatchPackageDTO, ...]
    not_selected_conflicts: tuple[TopMatchConflictDTO, ...]
    total_missing_count: int
    total_covered_missing_count: int
    selected_partner_count: int
    total_given_quantity: int
    redundant_received_positions: int
    personal_coverage_sum: int
    result_id: str
    explanation: str


@dataclass(frozen=True)
class _PartnerCandidate:
    partner_user_id: int
    personal_coverage_percent: int | None
    receive_codes: tuple[str, ...]
    give_codes: tuple[str, ...]
    executable_quantity: int


class TopMatchOptimizationService:
    """Read-only, album-bound S21 optimizer over S19/S20 projections."""

    def __init__(
        self,
        inventory_read_service: InventoryReadService,
        trade_coverage_service: TradeCoverageService | None = None,
    ):
        self._inventory = inventory_read_service
        self._coverage = trade_coverage_service or TradeCoverageService(
            inventory_read_service
        )

    @staticmethod
    def _distinct_sorted(values):
        return tuple(sorted(set(values), key=str))

    def _candidates(self, user_id, album_id, codes, partner_user_ids):
        return tuple(
            _PartnerCandidate(
                partner_user_id=match.partner_user_id,
                personal_coverage_percent=match.personal_coverage_percent,
                receive_codes=match.receive_codes,
                give_codes=match.give_codes,
                executable_quantity=match.executable_quantity,
            )
            for match in ExecutableTradeMatchService(self._coverage).matches(
                user_id, album_id, codes, partner_user_ids
            )
        )

    @staticmethod
    def _prioritized_allocations(candidates, subject_snapshot):
        remaining_by_code = {
            code: subject_snapshot.sticker(code).effective_available
            for candidate in candidates
            for code in candidate.give_codes
        }
        covered_receive_codes = set()
        selected_order = []
        allocations = {}
        for candidate in candidates:
            receive_codes = tuple(
                code for code in candidate.receive_codes
                if code not in covered_receive_codes
            )
            give_codes = tuple(
                code for code in candidate.give_codes
                if remaining_by_code.get(code, 0) > 0
            )
            executable_quantity = min(len(receive_codes), len(give_codes))
            if executable_quantity == 0:
                continue
            selected_receive = receive_codes[:executable_quantity]
            selected_give = give_codes[:executable_quantity]
            allocations[candidate.partner_user_id] = (
                selected_receive, selected_give
            )
            selected_order.append(candidate.partner_user_id)
            covered_receive_codes.update(selected_receive)
            for code in selected_give:
                remaining_by_code[code] -= 1
            if len(selected_order) == MAX_SELECTED_PACKAGES:
                break
        return tuple(selected_order), allocations

    @staticmethod
    def _result_id(user_id, album_id, packages):
        payload = {
            "version": OPTIMIZATION_VERSION,
            "user_id": user_id,
            "album_id": album_id,
            "packages": [
                {
                    "partner_user_id": package.partner_user_id,
                    "receive": [
                        (position.sticker_code, position.quantity)
                        for position in package.receive_positions
                    ],
                    "give": [
                        (position.sticker_code, position.quantity)
                        for position in package.give_positions
                    ],
                }
                for package in packages
            ],
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def optimize(self, user_id, album_id, catalog_codes, partner_user_ids):
        codes = self._distinct_sorted(catalog_codes)
        partner_ids = tuple(
            partner_id
            for partner_id in sorted(set(partner_user_ids))
            if partner_id != user_id
        )
        subject_snapshot = self._inventory.snapshot(user_id, album_id, codes)
        market = self._coverage.community_market_coverage(
            user_id, album_id, codes, partner_ids
        )
        candidates = self._candidates(
            user_id, album_id, codes, partner_ids
        )

        selected_order, best_allocations = self._prioritized_allocations(
            candidates, subject_snapshot
        )

        candidate_by_id = {
            candidate.partner_user_id: candidate for candidate in candidates
        }
        packages = tuple(
            TopMatchPackageDTO(
                partner_user_id=partner_id,
                receive_positions=tuple(
                    StickerQuantityDTO(code, 1)
                    for code in best_allocations[partner_id][0]
                ),
                give_positions=tuple(
                    StickerQuantityDTO(code, 1)
                    for code in best_allocations[partner_id][1]
                ),
                covered_missing_count=len(best_allocations[partner_id][0]),
                personal_coverage_percent=(
                    candidate_by_id[partner_id].personal_coverage_percent
                ),
                selection_reasons=(
                    "largest_bilateral_executable_quantity_first",
                    "uses_conflict_free_effective_supply",
                    "stable_partner_and_code_tie_breakers",
                ),
            )
            for partner_id in selected_order
        )

        used_by_code = {}
        for package in packages:
            for position in package.give_positions:
                used_by_code[position.sticker_code] = (
                    used_by_code.get(position.sticker_code, 0) + position.quantity
                )
        exhausted_codes = {
            code
            for code, quantity in used_by_code.items()
            if quantity >= subject_snapshot.sticker(code).effective_available
        }
        selected_ids = set(selected_order)
        conflicts = tuple(
            TopMatchConflictDTO(
                partner_user_id=candidate.partner_user_id,
                conflicting_give_codes=tuple(
                    code for code in candidate.give_codes if code in exhausted_codes
                ),
            )
            for candidate in candidates
            if candidate.partner_user_id not in selected_ids
            and any(code in exhausted_codes for code in candidate.give_codes)
        )

        total_covered = sum(
            package.covered_missing_count for package in packages
        )
        total_given = sum(
            position.quantity
            for package in packages
            for position in package.give_positions
        )
        personal_sum = sum(
            package.personal_coverage_percent or 0 for package in packages
        )
        result_id = self._result_id(user_id, album_id, packages)
        explanation = (
            "No executable bilateral package exists."
            if not packages
            else (
                f"Selected {len(packages)} prioritized conflict-free package(s) covering "
                f"{total_covered} of {market.missing_count} distinct missing "
                "codes under the CB-011 bilateral quantity contract."
            )
        )
        return TopMatchOptimizationResultDTO(
            version=OPTIMIZATION_VERSION,
            user_id=user_id,
            album_id=album_id,
            packages=packages,
            not_selected_conflicts=conflicts,
            total_missing_count=market.missing_count,
            total_covered_missing_count=total_covered,
            selected_partner_count=len(packages),
            total_given_quantity=total_given,
            redundant_received_positions=0,
            personal_coverage_sum=personal_sum,
            result_id=result_id,
            explanation=explanation,
        )
