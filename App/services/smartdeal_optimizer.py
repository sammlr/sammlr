"""Read-only SmartDeal V1 global optimization over a canonical T2a/T2b snapshot.

Internal domain API, not an HTTP payload validator. Caller supplies the COMPLETE
T2b opportunities from the SAME snapshot as PlanningState; this API never reads
inventory, checks live privacy, loads a database, or manufactures missing edges.
"""
from collections import Counter
from dataclasses import dataclass

from services._smartdeal_flow import PartnerEdges, allocate
from services.smartdeal_pairwise import PairwiseOpportunity
from services.smartdeal_planning import PlanningState
from services.trade_v2_rules import maximum_equal, valid_balance


class SmartDealOptimizationError(ValueError):
    """Invalid planning inputs or an incomplete/invalid optimization result."""


@dataclass(frozen=True)
class SmartDealPiece:
    album_id: str
    sticker_code: str
    quantity: int = 1


@dataclass(frozen=True)
class SmartDealCandidate:
    partner_id: int
    outgoing_pieces: tuple[SmartDealPiece, ...]
    incoming_pieces: tuple[SmartDealPiece, ...]
    piece_count: int
    involved_albums: tuple[str, ...]


@dataclass(frozen=True)
class SmartDealObjective:
    efficiency: int
    total_gain: int
    trade_count: int
    deal_sizes: tuple[int, ...]
    partner_ids: tuple[int, ...]
    positions: tuple[tuple[str, str], ...]

    @property
    def comparison_key(self):
        """Smaller wins, exactly AC12: E/G/D descending, J/C ascending."""
        return (-self.efficiency, -self.total_gain, tuple(-n for n in self.deal_sizes),
                self.partner_ids, self.positions)


@dataclass(frozen=True)
class SmartDealDiagnostics:
    subsets: int
    pruned: int
    flow_checks: int
    cache_hits: int
    orders: int


@dataclass(frozen=True)
class SmartDealPlan:
    deals: tuple[SmartDealCandidate, ...]
    objective: SmartDealObjective
    diagnostics: SmartDealDiagnostics


def _key(piece):
    if type(piece.album_id) is not str or type(piece.sticker_code) is not str:
        raise SmartDealOptimizationError('Canonical album/code strings required')
    return piece.album_id, piece.sticker_code


def _positive(value):
    return type(value) is int and value > 0


def _inputs(state, opportunities, quantities=False):
    if not isinstance(state, PlanningState) or not _positive(state.user_id):
        raise SmartDealOptimizationError('Canonical PlanningState required')
    albums = {a.album_id: a for a in state.album_context}
    if len(albums) != len(state.album_context):
        raise SmartDealOptimizationError('Duplicate album context')
    catalogs = {a: set(context.catalog_codes) for a, context in albums.items()}

    def pieces(values, binary=False):
        result = {}
        for piece in values:
            k = _key(piece)
            if k in result or not _positive(piece.quantity) or (binary and piece.quantity != 1):
                raise SmartDealOptimizationError('Duplicate or invalid canonical quantity')
            if (piece.album_id not in albums or piece.sticker_code not in catalogs[piece.album_id]
                    or not _positive(piece.user_album_id)
                    or piece.user_album_id != albums[piece.album_id].user_album_id):
                raise SmartDealOptimizationError('Piece does not belong to canonical album context')
            result[k] = piece
        return result

    supply = pieces(state.outgoing_supply)
    needs = pieces(state.needs, binary=not quantities)
    missing = pieces(state.missing, binary=True)
    committed = pieces(state.incoming_committed_needs, binary=True)
    if not quantities and (supply.keys() & missing.keys() or needs.keys() & committed.keys()
            or missing.keys() != needs.keys() | committed.keys()):
        raise SmartDealOptimizationError('Inconsistent physical/free/committed planning resources')
    eligible = {}
    for partner in state.eligible_partners:
        if (not _positive(partner.user_id) or partner.user_id == state.user_id
                or partner.user_id in eligible or not set(partner.album_ids) <= albums.keys()):
            raise SmartDealOptimizationError('Inconsistent canonical eligible roster')
        eligible[partner.user_id] = set(partner.album_ids)
    result = []
    seen = set()
    for opportunity in opportunities:
        if not isinstance(opportunity, PairwiseOpportunity):
            raise SmartDealOptimizationError('Canonical PairwiseOpportunity required')
        pid = opportunity.partner_id
        if not _positive(pid) or pid in seen or pid not in eligible:
            raise SmartDealOptimizationError('Duplicate or noneligible pairwise partner')
        seen.add(pid)
        sides = []
        memberships = {}
        capacities = {}
        for outgoing, candidates in ((True, opportunity.outgoing_candidates),
                                     (False, opportunity.incoming_candidates)):
            keys = []
            for candidate in candidates:
                k = _key(candidate)
                own = (supply if outgoing else needs).get(k)
                own_membership = candidate.giver_user_album_id if outgoing else candidate.receiver_user_album_id
                other_membership = candidate.receiver_user_album_id if outgoing else candidate.giver_user_album_id
                if (not _positive(candidate.quantity) or (not quantities and candidate.quantity != 1)
                        or not _positive(candidate.available_quantity) or own is None
                        or candidate.quantity > candidate.available_quantity
                        or (own is not None and candidate.quantity > own.quantity)
                        or candidate.album_id not in eligible[pid]
                        or own_membership != own.user_album_id or not _positive(own_membership)
                        or not _positive(other_membership) or other_membership == own_membership
                        or (outgoing and candidate.available_quantity != own.quantity)):
                    raise SmartDealOptimizationError('Pairwise candidate conflicts with canonical snapshot')
                old = memberships.setdefault(candidate.album_id, other_membership)
                if old != other_membership:
                    raise SmartDealOptimizationError('Inconsistent partner membership identity')
                keys.append(k)
                capacities[("out" if outgoing else "in",k)] = candidate.quantity
            if len(set(keys)) != len(keys):
                raise SmartDealOptimizationError('Duplicate binary candidate need')
            sides.append(tuple(sorted(keys)))
        out, inc = sides
        expected_albums = {k[0] for k in out + inc}
        groups = opportunity.balance_groups
        if groups is not None:
            if {a for group in groups for a in group} - eligible[pid]:
                raise SmartDealOptimizationError('Balance group outside permitted albums')
            expected_maximum = maximum_equal((k[0] for k in out for _ in range(capacities[("out",k)])), (k[0] for k in inc for _ in range(capacities[("in",k)])), groups)
        else:
            expected_maximum = min(sum(capacities[("out",k)] for k in out), sum(capacities[("in",k)] for k in inc))
        if (not out or not inc or type(opportunity.max_equal_piece_count) is not int
                or opportunity.max_equal_piece_count != expected_maximum
                or len(set(opportunity.involved_albums)) != len(opportunity.involved_albums)
                or set(opportunity.involved_albums) != expected_albums):
            raise SmartDealOptimizationError('Pairwise maximum or album projection is inconsistent')
        result.append(PartnerEdges(pid, out, inc, groups, capacities))
    return {k: p.quantity for k, p in supply.items()}, tuple(result), {k:p.quantity for k,p in needs.items()}


def _validated_plan(supply, partners, allocations, counters, needs=None, minimum=5):
    """Independent postcondition check before publishing any domain result."""
    roster = {p.partner_id: p for p in partners}
    used_out, used_in = Counter(), Counter()
    seen = set()
    deals = []
    if len(allocations) > 5:
        raise SmartDealOptimizationError('Optimizer exceeded the partner limit')
    for allocation in allocations:
        pid = allocation.partner_id
        size = len(allocation.incoming)
        if pid in seen or pid not in roster or size < minimum or size != len(allocation.outgoing):
            raise SmartDealOptimizationError('Optimizer violated eligibility or 1:1/minimum')
        seen.add(pid)
        partner = roster[pid]
        for direction, selected, candidates in (("in", allocation.incoming, partner.incoming), ("out", allocation.outgoing, partner.outgoing)):
            if not set(selected) <= set(candidates) or any(n > partner.capacity(direction,k) for k,n in Counter(selected).items()):
                raise SmartDealOptimizationError('Optimizer used an invalid candidate')
        if partner.balance_groups is not None and not valid_balance(
                (k[0] for k in allocation.outgoing), (k[0] for k in allocation.incoming),
                partner.balance_groups, equal=True):
            raise SmartDealOptimizationError('Optimizer crossed a restricted balance group')
        used_out.update(allocation.outgoing)
        used_in.update(allocation.incoming)
        deals.append(SmartDealCandidate(
            pid, tuple(SmartDealPiece(*k,n) for k,n in sorted(Counter(allocation.outgoing).items())),
            tuple(SmartDealPiece(*k,n) for k,n in sorted(Counter(allocation.incoming).items())), size,
            tuple(sorted({k[0] for k in allocation.outgoing + allocation.incoming})),
        ))
    if any(n > supply.get(k, 0) for k, n in used_out.items()) or any(n > (needs or {}).get(k,1) for k,n in used_in.items()):
        raise SmartDealOptimizationError('Optimizer double-allocated a resource or need')
    deals = tuple(sorted(deals, key=lambda d: (-d.piece_count, d.partner_id)))
    gain = sum(d.piece_count for d in deals)
    objective = SmartDealObjective(
        gain - 2 * len(deals), gain, len(deals), tuple(d.piece_count for d in deals),
        tuple(d.partner_id for d in deals),
        tuple((p.album_id, p.sticker_code) for d in deals for side in (d.incoming_pieces, d.outgoing_pieces) for p in side for _ in range(p.quantity)),
    )
    return SmartDealPlan(deals, objective, SmartDealDiagnostics(**counters))


class SmartDealOptimizer:
    @staticmethod
    def optimize(state: PlanningState, opportunities: tuple[PairwiseOpportunity, ...], *, quantities=False, minimum=5) -> SmartDealPlan:
        """Consume one trusted complete T2a/T2b snapshot, with zero SQL/writes.

        Returns only after exact proof completion. No top-partner preselection,
        time-dependent diagnostics, persistent identity, timeout or fallback.
        Exceptions leave caller inputs and database state untouched.
        """
        if type(minimum) is not int or minimum not in (1,5):
            raise ValueError('Unsupported offer minimum')
        supply, partners, needs = _inputs(state, opportunities, quantities)
        allocations, counters = allocate(supply, partners, needs, minimum=minimum)
        return _validated_plan(supply, partners, allocations, counters, needs, minimum)
