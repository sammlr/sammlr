from __future__ import annotations

from dataclasses import dataclass

from services.trade_coverage import TradeCoverageService


@dataclass(frozen=True)
class ExecutableTradeMatchDTO:
    user_id: int
    partner_user_id: int
    album_id: str
    executable_quantity: int
    personal_coverage_percent: int | None
    receive_codes: tuple[str, ...]
    give_codes: tuple[str, ...]


class ExecutableTradeMatchService:
    """CB-011 bilateral match priority over current S20 coverage snapshots."""

    def __init__(self, trade_coverage_service: TradeCoverageService):
        self._coverage = trade_coverage_service

    def matches(self, user_id, album_id, catalog_codes, partner_user_ids):
        matches = []
        subject = int(user_id)
        partners = tuple(sorted({
            int(partner_id) for partner_id in partner_user_ids
            if int(partner_id) != subject
        }))
        if not partners or not self._coverage._pool_enabled(subject, album_id):
            return ()
        interactable = self._coverage._community.interactable_user_ids(
            subject, partners
        )
        partners = tuple(
            partner_id for partner_id in partners
            if (
                partner_id in interactable
                and self._coverage._pool_enabled(partner_id, album_id)
            )
        )
        if not partners:
            return ()
        inventory = self._coverage._inventory
        subject_state = inventory.matching_states(
            (subject,), album_id, catalog_codes
        )[subject]
        projection = inventory.album_market_projection(
            subject, partners, album_id, catalog_codes,
            subject_state=subject_state,
        )
        for partner_id in partners:
            receive_codes = tuple(sorted(
                projection.get_codes_by_user[partner_id], key=str
            ))
            give_codes = tuple(sorted(
                projection.give_codes_by_user[partner_id], key=str
            ))
            executable_quantity = min(len(receive_codes), len(give_codes))
            if executable_quantity == 0:
                continue
            matches.append(ExecutableTradeMatchDTO(
                user_id=user_id,
                partner_user_id=partner_id,
                album_id=album_id,
                executable_quantity=executable_quantity,
                personal_coverage_percent=(
                    None if not subject_state.missing_codes else
                    int(len(receive_codes) / len(subject_state.missing_codes) * 100)
                ),
                receive_codes=receive_codes,
                give_codes=give_codes,
            ))
        return tuple(sorted(
            matches,
            key=lambda match: (
                -match.executable_quantity,
                match.partner_user_id,
                match.receive_codes,
                match.give_codes,
            ),
        ))
