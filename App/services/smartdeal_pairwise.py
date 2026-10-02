"""Isolated bilateral capacities from canonical planning inputs; no allocation."""
from dataclasses import dataclass

from services.smartdeal_planning import PairwisePlanningInputs, SmartDealPlanningService


@dataclass(frozen=True)
class PairwiseCandidate:
    album_id: str
    sticker_code: str
    quantity: int
    available_quantity: int
    giver_user_album_id: int
    receiver_user_album_id: int


@dataclass(frozen=True)
class PairwiseOpportunity:
    partner_id: int
    outgoing_candidates: tuple[PairwiseCandidate, ...]
    incoming_candidates: tuple[PairwiseCandidate, ...]
    max_equal_piece_count: int
    involved_albums: tuple[str, ...]


def _candidates(supply, needs, albums):
    demand = {(p.album_id, p.sticker_code): p for p in needs}
    result = []
    for piece in supply:
        key = (piece.album_id, piece.sticker_code)
        need = demand.get(key)
        if piece.album_id not in albums or need is None:
            continue
        if need.quantity != 1 or piece.quantity <= 0:
            raise ValueError("Pairwise inputs must obey canonical V1 supply/need contracts")
        result.append(PairwiseCandidate(
            piece.album_id, piece.sticker_code, min(piece.quantity, need.quantity),
            piece.quantity, piece.user_album_id, need.user_album_id,
        ))
    return tuple(sorted(result, key=lambda p: (p.album_id, p.sticker_code)))


class SmartDealPairwiseService:
    def __init__(self, planning_service: SmartDealPlanningService):
        self._planning = planning_service

    def build(self, user_id):
        return self.from_planning_inputs(self._planning.build_pairwise_inputs(user_id))

    @staticmethod
    def from_planning_inputs(inputs: PairwisePlanningInputs):
        """Pure calculation: complete candidates, never trim the longer side."""
        subject = inputs.subject
        inventories = {p.user_id:p for p in inputs.partners}
        if len(inventories) != len(inputs.partners):
            raise ValueError("Duplicate canonical partner inventory")
        result = []
        for partner in sorted(subject.eligible_partners, key=lambda p: p.user_id):
            if partner.user_id == subject.user_id:
                raise ValueError("Self is not an eligible pairwise partner")
            if partner.user_id not in inventories:
                raise ValueError("Missing canonical partner inventory")
            inventory = inventories[partner.user_id]
            outgoing = _candidates(subject.outgoing_supply, inventory.needs, partner.album_ids)
            incoming = _candidates(inventory.outgoing_supply, subject.needs, partner.album_ids)
            maximum = min(sum(p.quantity for p in outgoing), sum(p.quantity for p in incoming))
            if maximum:
                result.append(PairwiseOpportunity(
                    partner.user_id, outgoing, incoming, maximum,
                    tuple(sorted({p.album_id for p in outgoing + incoming})),
                ))
        return tuple(result)
