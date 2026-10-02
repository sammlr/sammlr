"""SD-T3a exhaustive package oracle. Synthetic/small snapshots only; no SQL.

Independent allocation enumeration, shared explicit contract comparator. A work
limit raises instead of returning a partial plan. Not a production optimizer.
"""
from collections import Counter
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Partner:
    partner_id: int
    outgoing: tuple[tuple[str, str], ...]
    incoming: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Problem:
    supply: tuple[tuple[tuple[str, str], int], ...]
    partners: tuple[Partner, ...]


@dataclass(frozen=True)
class Deal:
    partner_id: int
    incoming: tuple[tuple[str, str], ...]
    outgoing: tuple[tuple[str, str], ...]

    @property
    def size(self):
        return len(self.incoming)


def canonical(deals):
    return tuple(sorted((Deal(d.partner_id, tuple(sorted(d.incoming)),
                             tuple(sorted(d.outgoing))) for d in deals),
                        key=lambda d: (-d.size, d.partner_id)))


def plan_key(deals):
    """Smaller is better: AC12 E DESC, G DESC, D DESC, J ASC, C ASC."""
    plan = canonical(deals)
    gain = sum(d.size for d in plan)
    return (-(gain - 2 * len(plan)), -gain, tuple(-d.size for d in plan),
            tuple(d.partner_id for d in plan),
            tuple(k for d in plan for side in (d.incoming, d.outgoing) for k in side))


def validate_problem(problem):
    supply = dict(problem.supply)
    if len(supply) != len(problem.supply) or any(type(n) is not int or n <= 0 for n in supply.values()):
        raise ValueError('Supply must be unique positive integer free capacities')
    ids = [p.partner_id for p in problem.partners]
    if len(set(ids)) != len(ids) or any(type(p) is not int or p <= 0 for p in ids):
        raise ValueError('Unique numeric canonical partner IDs required')
    for p in problem.partners:
        for side in (p.incoming, p.outgoing):
            if len(set(side)) != len(side):
                raise ValueError('Binary need: no duplicate candidate identity')
            if any(len(k) != 2 or any(type(s) is not str for s in k) for k in side):
                raise ValueError('Canonical album/code strings required')
        if not set(p.outgoing) <= supply.keys():
            raise ValueError('Candidate is not free supply')
    # Canonical physical missing and free supply cannot overlap for the subject.
    if set(supply) & {k for p in problem.partners for k in p.incoming}:
        raise ValueError('An incoming need cannot simultaneously be own supply')


def from_snapshot(inputs, opportunities):
    """Verify the complete T2b projection against the same frozen T2a snapshot."""
    from services.smartdeal_pairwise import SmartDealPairwiseService
    expected = SmartDealPairwiseService.from_planning_inputs(inputs)
    if tuple(opportunities) != expected:
        raise ValueError('Incomplete, stale or inconsistent pairwise snapshot')
    problem = Problem(tuple(((p.album_id, p.sticker_code), p.quantity)
                            for p in inputs.subject.outgoing_supply),
                      tuple(Partner(p.partner_id,
                                    tuple((k.album_id, k.sticker_code) for k in p.outgoing_candidates),
                                    tuple((k.album_id, k.sticker_code) for k in p.incoming_candidates))
                            for p in expected))
    validate_problem(problem)
    return problem


def validate_plan(problem, plan):
    validate_problem(problem)
    roster = {p.partner_id: p for p in problem.partners}
    if len(plan) > 5 or len({d.partner_id for d in plan}) != len(plan):
        raise ValueError('Max five unique partners')
    used_out, used_in = Counter(), Counter()
    for d in plan:
        if d.partner_id not in roster or d.size < 5 or d.size != len(d.outgoing):
            raise ValueError('Eligibility, minimum or balance violation')
        p = roster[d.partner_id]
        for selected, candidates in ((d.incoming, p.incoming), (d.outgoing, p.outgoing)):
            if len(set(selected)) != len(selected) or not set(selected) <= set(candidates):
                raise ValueError('Noncandidate or repeated need')
        used_out.update(d.outgoing)
        used_in.update(d.incoming)
    if any(n > dict(problem.supply).get(k, 0) for k, n in used_out.items()) or any(n > 1 for n in used_in.values()):
        raise ValueError('Global supply/need collision')
    return True


class OracleLimit(RuntimeError):
    pass


def solve(problem, max_states=2_000_000, stats=None):
    validate_problem(problem)
    partners = sorted(problem.partners, key=lambda p: p.partner_id)
    remaining = dict(problem.supply)
    best = ()
    visited = 0

    def visit(index, plan, received):
        nonlocal best, visited
        visited += 1
        if max_states is not None and visited > max_states:
            raise OracleLimit('Exhaustive proof unfinished; no optimal result')
        if index == len(partners) or len(plan) == 5:
            if plan_key(plan) < plan_key(best):
                best = canonical(plan)
            return
        p = partners[index]
        visit(index + 1, plan, received)  # Not activating this partner is a real branch.
        outgoing = sorted(k for k in p.outgoing if remaining[k] > 0)
        incoming = sorted(set(p.incoming) - received)
        for size in range(5, min(len(outgoing), len(incoming)) + 1):
            for give in combinations(outgoing, size):
                for get in combinations(incoming, size):
                    for k in give:
                        remaining[k] -= 1
                    visit(index + 1, plan + (Deal(p.partner_id, get, give),), received | set(get))
                    for k in give:
                        remaining[k] += 1
    visit(0, (), set())
    if stats is not None:
        stats['states'] = visited
    validate_plan(problem, best)
    return best


def differential(problem, candidate):
    """Reusable exact acceptance harness for a future T3b callable."""
    expected = solve(problem)
    actual = candidate(problem)
    validate_plan(problem, actual)
    if canonical(actual) != expected:
        raise AssertionError((expected, actual))
    return expected
