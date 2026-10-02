"""Exact SmartDeal V1 suggestion contents and read-only fresh revalidation.

VALID means this package is executable in the read snapshot, not reserved or
permission to create a request later. T5a must read and write in one transaction.
No optimizer call, client availability, payload repair or persistence here.
"""
from dataclasses import dataclass
from enum import Enum

from services.albums import all_codes
from services.smartdeal_identity import SmartDealIdentityService, SmartDealOpportunityIdentity
from services.smartdeal_optimizer import SmartDealCandidate, SmartDealPiece
from services.smartdeal_planning import SmartDealPlanningService
from services.trade_contracts import SMARTDEAL_V1_CONTRACT


@dataclass(frozen=True)
class SmartDealSuggestion:
    contract_type: str
    opportunity_identity: SmartDealOpportunityIdentity
    participant_a: int
    participant_b: int
    side_a_pieces: tuple[SmartDealPiece, ...]
    side_b_pieces: tuple[SmartDealPiece, ...]
    piece_count: int
    involved_albums: tuple[str, ...]

    @classmethod
    def from_deal(cls, user_id: int, deal: SmartDealCandidate):
        identity = SmartDealIdentityService.from_deal(user_id, deal)
        result = cls(SMARTDEAL_V1_CONTRACT, identity, identity.low_user_id, identity.high_user_id,
                     tuple(SmartDealPiece(*p) for p in identity.low_to_high),
                     tuple(SmartDealPiece(*p) for p in identity.high_to_low),
                     deal.piece_count, deal.involved_albums)
        if _payload_identity(result) is None:
            raise ValueError('Invalid final SmartDeal package')
        return result


class SuggestionStatus(str, Enum):
    VALID = 'VALID'
    STALE = 'STALE'
    INVALID_PAYLOAD = 'INVALID_PAYLOAD'


@dataclass(frozen=True)
class SuggestionValidation:
    status: SuggestionStatus
    reason: str


def _payload_identity(value):
    """Reconstruct all semantic content; never trust the submitted digest."""
    if type(value) is not SmartDealSuggestion or value.contract_type != SMARTDEAL_V1_CONTRACT:
        return None
    if (type(value.participant_a) is not int or type(value.participant_b) is not int
            or not 0 < value.participant_a < value.participant_b
            or type(value.piece_count) is not int or value.piece_count < 5
            or type(value.side_a_pieces) is not tuple or type(value.side_b_pieces) is not tuple
            or type(value.involved_albums) is not tuple
            or type(value.opportunity_identity) is not SmartDealOpportunityIdentity):
        return None
    pieces = value.side_a_pieces + value.side_b_pieces
    if any(type(p) is not SmartDealPiece for p in pieces):
        return None
    try:
        actual = SmartDealIdentityService.from_view(value.participant_a, value.participant_b,
                                                   value.side_a_pieces, value.side_b_pieces)
    except (ValueError, TypeError):
        return None
    if (len(actual.low_to_high) != value.piece_count or len(actual.high_to_low) != value.piece_count
            or value.involved_albums != tuple(sorted({a for a, _, _ in actual.low_to_high + actual.high_to_low}))):
        return None
    expected = value.opportunity_identity
    if (actual != expected or actual.canonical_payload != expected.canonical_payload
            or actual.digest != expected.digest):
        return None
    return actual


class SmartDealSuggestionValidator:
    def __init__(self, connection, catalog_provider=all_codes, now_provider=None):
        self._planning = SmartDealPlanningService(connection, catalog_provider, now_provider)

    def validate(self, suggestion: SmartDealSuggestion, actor_user_id: int) -> SuggestionValidation:
        """Load fresh server-owned T2a inputs on EVERY invocation.

        actor_user_id must come from the authenticated server context, not the
        submitted payload. Existing caller transactions are preserved by T2a;
        T5a must start its write transaction before this call, then reserve/write
        without releasing it. No read result here grants a request quota slot,
        locks resources, or implements acceptance of an already bound request.
        """
        identity = _payload_identity(suggestion)
        if identity is None:
            return SuggestionValidation(SuggestionStatus.INVALID_PAYLOAD, 'payload_contract')
        if type(actor_user_id) is not int or actor_user_id not in (identity.low_user_id, identity.high_user_id):
            return SuggestionValidation(SuggestionStatus.INVALID_PAYLOAD, 'actor_not_participant')
        partner_id = identity.high_user_id if actor_user_id == identity.low_user_id else identity.low_user_id
        try:
            inputs = self._planning.build_pairwise_inputs(actor_user_id)
        except ValueError:
            # Inactive/missing subject or inconsistent binding projection cannot
            # establish current executability. Infrastructure errors propagate.
            return SuggestionValidation(SuggestionStatus.STALE, 'canonical_state_unavailable')
        eligible = next((p for p in inputs.subject.eligible_partners if p.user_id == partner_id), None)
        partner = next((p for p in inputs.partners if p.user_id == partner_id), None)
        if eligible is None or partner is None:
            return SuggestionValidation(SuggestionStatus.STALE, 'partner_unavailable')
        outgoing, incoming = (identity.low_to_high, identity.high_to_low) if actor_user_id == identity.low_user_id else (identity.high_to_low, identity.low_to_high)
        for offered, giver, receiver in ((outgoing, inputs.subject, partner), (incoming, partner, inputs.subject)):
            supply = {(p.album_id, p.sticker_code): p.quantity for p in giver.outgoing_supply}
            needs = {(p.album_id, p.sticker_code): p.quantity for p in receiver.needs}
            for album, code, quantity in offered:
                if album not in eligible.album_ids:
                    return SuggestionValidation(SuggestionStatus.STALE, 'album_unavailable')
                if supply.get((album, code), 0) < quantity:
                    return SuggestionValidation(SuggestionStatus.STALE, 'supply_unavailable')
                if needs.get((album, code), 0) != quantity:
                    return SuggestionValidation(SuggestionStatus.STALE, 'need_unavailable')
        return SuggestionValidation(SuggestionStatus.VALID, 'exact_package_available')
