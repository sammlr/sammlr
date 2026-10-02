"""Exact in-memory SD-T3a allocation engine; no IO or application state.

Proof and bounds: docs/SMARTDEAL_T3A_OPTIMIZATION_PROOF.md and T3B report.
Integer lower-bound circulation, exhaustive subsets and all size permutations.
"""
from collections import deque
from dataclasses import dataclass
from itertools import combinations, permutations


@dataclass(frozen=True)
class PartnerEdges:
    partner_id: int
    outgoing: tuple[tuple[str, str], ...]
    incoming: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Allocation:
    partner_id: int
    incoming: tuple[tuple[str, str], ...]
    outgoing: tuple[tuple[str, str], ...]


def _has_circulation(vertex_count, edges):
    """Integral lower-bound reduction with Dinic blocking flows."""
    source, sink = vertex_count, vertex_count + 1
    graph = [[] for _ in range(vertex_count + 2)]
    balance = [0] * vertex_count

    def add(u, v, capacity):
        graph[u].append([v, capacity, len(graph[v])])
        graph[v].append([u, 0, len(graph[u]) - 1])

    for u, v, low, high in edges:
        if low < 0 or high < low:
            return False
        add(u, v, high - low)
        balance[u] -= low
        balance[v] += low
    demand = 0
    for v, amount in enumerate(balance):
        if amount > 0:
            add(source, v, amount)
            demand += amount
        elif amount < 0:
            add(v, sink, -amount)
    sent = 0
    while sent < demand:
        level = [-1] * len(graph)
        level[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v, capacity, _ in graph[u]:
                if capacity > 0 and level[v] < 0:
                    level[v] = level[u] + 1
                    queue.append(v)
        if level[sink] < 0:
            return False
        cursor = [0] * len(graph)

        def augment(u, amount):
            if u == sink:
                return amount
            while cursor[u] < len(graph[u]):
                edge = graph[u][cursor[u]]
                v, capacity, reverse = edge
                if capacity > 0 and level[v] == level[u] + 1:
                    pushed = augment(v, min(amount, capacity))
                    if pushed:
                        edge[1] -= pushed
                        graph[v][reverse][1] += pushed
                        return pushed
                cursor[u] += 1
            return 0

        while sent < demand:
            pushed = augment(source, demand - sent)
            if not pushed:
                break
            sent += pushed
    return True


class _SubsetNetwork:
    """Immutable integer topology, fresh residual state per feasibility check."""
    def __init__(self, subset, supply, counters):
        self.subset = subset
        self.counters = counters
        self.cache = {}
        self.edges = []
        self.size_indices = {}
        self.piece_indices = {}
        outgoing = sorted({k for p in subset for k in p.outgoing})
        incoming = sorted({k for p in subset for k in p.incoming})
        out_nodes = {k: i + 2 for i, k in enumerate(outgoing)}
        in_nodes = {k: i + 2 + len(outgoing) for i, k in enumerate(incoming)}
        next_node = 2 + len(outgoing) + len(incoming)
        self.edges.extend((0, out_nodes[k], 0, supply[k]) for k in outgoing)
        self.edges.extend((in_nodes[k], 1, 0, 1) for k in incoming)
        for p in subset:
            left, right = next_node, next_node + 1
            next_node += 2
            self.size_indices[p.partner_id] = len(self.edges)
            self.edges.append((left, right, 5, min(len(p.outgoing), len(p.incoming))))
            for direction, keys in (('out', p.outgoing), ('in', p.incoming)):
                for k in keys:
                    self.piece_indices[(direction, p.partner_id, k)] = len(self.edges)
                    u, v = (out_nodes[k], left) if direction == 'out' else (right, in_nodes[k])
                    self.edges.append((u, v, 0, 1))
        self.return_index = len(self.edges)
        self.edges.append((1, 0, 0, 0))
        self.vertex_count = next_node

    def feasible(self, sizes, total_bounds, fixed=None):
        key = (tuple(sizes[p.partner_id] for p in self.subset), total_bounds)
        # No cache for C: each query has a different fixed edge prefix.
        if fixed is None and key in self.cache:
            self.counters['cache_hits'] += 1
            return self.cache[key]
        self.counters['flow_checks'] += 1
        edges = list(self.edges)
        for pid, index in self.size_indices.items():
            edges[index] = (*edges[index][:2], *sizes[pid])
        edges[self.return_index] = (1, 0, *total_bounds)
        if fixed is not None:
            for piece, bounds in fixed.items():
                index = self.piece_indices[piece]
                edges[index] = (*edges[index][:2], *bounds)
        result = _has_circulation(self.vertex_count, edges)
        if fixed is None:
            self.cache[key] = result
        return result


def _largest(low, high, predicate):
    """Predicate: feasible with AT LEAST this bound (monotone)."""
    if low < high:
        if predicate(high):
            return high
        high -= 1  # Already proved infeasible; do not test twice.
    while low < high:
        mid = (low + high + 1) // 2
        if predicate(mid):
            low = mid
        else:
            high = mid - 1
    return low


def _search_subsets(partners, supply, global_upper):
    """Try one algebraically ideal group, then exhaust the original search.

    The probe only changes traversal: it never excludes a subset. Memory stays
    O(partners + five partners' keys); no materialized combination frontier.
    """
    limit = min(5, len(partners), global_upper // 5)
    maxima = {p.partner_id: min(len(p.outgoing), len(p.incoming)) for p in partners}
    top = sorted(maxima.values(), reverse=True)
    bounds = [(min(global_upper, sum(top[:n])) - 2*n,
               min(global_upper, sum(top[:n])), n) for n in range(1, limit + 1)]
    if bounds:
        best = max((e, g) for e, g, _ in bounds)
        for e, target, count in bounds:
            if (e, target) != best:
                continue
            for subset in combinations(partners, count):
                if sum(maxima[p.partner_id] for p in subset) != target:
                    continue
                if len({k for p in subset for k in p.incoming}) < target:
                    continue
                if sum(supply[k] for k in {k for p in subset for k in p.outgoing}) < target:
                    continue
                yield count, subset
                break
            break
    for count in range(1, limit + 1):
        for subset in combinations(partners, count):
            yield count, subset


def allocate(supply, partners):
    """Return the proven optimum and deterministic diagnostics, or raise.

    All inputs have been validated by SmartDealOptimizer. No resource/time cutoff
    and no heuristic fallback; every returned result has completed the search.
    """
    partners = tuple(sorted((p for p in partners if min(len(p.outgoing), len(p.incoming)) >= 5),
                            key=lambda p: p.partner_id))
    counters = {'subsets': 0, 'pruned': 0, 'flow_checks': 0, 'cache_hits': 0, 'orders': 0}
    winner = None
    winner_key = (0, 0, (), ())
    global_upper = min(sum(supply.values()), len({k for p in partners for k in p.incoming}))
    for count, subset in _search_subsets(partners, supply, global_upper):
        counters['subsets'] += 1
        maxima = {p.partner_id: min(len(p.outgoing), len(p.incoming)) for p in subset}
        upper = min(sum(maxima.values()),
                    sum(supply[k] for k in {k for p in subset for k in p.outgoing}),
                    len({k for p in subset for k in p.incoming}))
        optimistic = (-(upper - 2 * count), -upper,
                      tuple(-v for v in sorted(maxima.values(), reverse=True)),
                      tuple(p.partner_id for p in subset))
        if upper < 5 * count or optimistic >= winner_key:
            counters['pruned'] += 1
            continue
        network = _SubsetNetwork(subset, supply, counters)
        sizes = {p: (5, maximum) for p, maximum in maxima.items()}
        if not network.feasible(sizes, (0, upper)):
            continue
        gain = _largest(5 * count, upper, lambda g: network.feasible(sizes, (g, upper)))
        if (-(gain - 2 * count), -gain) > winner_key[:2]:
            continue
        for order in permutations(subset):
            counters['orders'] += 1
            exact = dict(sizes)
            remaining_gain = gain
            for index, p in enumerate(order):
                pid = p.partner_id
                # Remaining active partners each need at least five; this
                # is an algebraic upper bound, not a size heuristic.
                high = min(maxima[pid], remaining_gain - 5 * (count - index - 1))
                low = max(5, remaining_gain - sum(maxima[q.partner_id] for q in order[index+1:]))
                size = _largest(low, high, lambda d: network.feasible(
                    {**exact, pid: (d, maxima[pid])}, (gain, gain)))
                exact[pid] = (size, size)
                remaining_gain -= size
            ordered = tuple(sorted(exact, key=lambda p: (-exact[p][0], p)))
            key = (-(gain - 2 * count), -gain, tuple(-exact[p][0] for p in ordered), ordered)
            if key < winner_key:
                winner_key = key
                winner = (network, exact, gain, ordered)
    if winner is None:
        return (), counters
    network, sizes, gain, ordered = winner
    by_id = {p.partner_id: p for p in network.subset}
    fixed = {}
    result = []
    for pid in ordered:
        selected = {}
        for direction, keys in (('in', by_id[pid].incoming), ('out', by_id[pid].outgoing)):
            selected[direction] = []
            for index, k in enumerate(keys):
                piece = (direction, pid, k)
                needed = sizes[pid][0] - len(selected[direction])
                if needed == 0:
                    fixed[piece] = (0, 0)
                    continue
                fixed[piece] = (1, 1)
                if needed == len(keys) - index or network.feasible(sizes, (gain, gain), fixed):
                    selected[direction].append(k)
                else:
                    fixed[piece] = (0, 0)
        result.append(Allocation(pid, tuple(selected['in']), tuple(selected['out'])))
    return tuple(result), counters
