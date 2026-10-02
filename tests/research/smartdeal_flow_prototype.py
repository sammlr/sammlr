"""SD-T3a research prototype: subset search + integral bounded circulation.

Standard library only. No application import, runtime entry point or persistence.
This executable proof is intentionally separate from the exhaustive oracle.
"""
from collections import deque
from itertools import combinations, permutations
from tests.research.smartdeal_oracle import Deal, canonical, plan_key, validate_problem, validate_plan


def circulation(edges):
    """Feasibility of integer lower/upper bounds via super-source max flow."""
    graph = {}
    balance = {}

    def add(u, v, capacity):
        graph.setdefault(u, [])
        graph.setdefault(v, [])
        forward = [v, capacity, len(graph[v])]
        backward = [u, 0, len(graph[u])]
        graph[u].append(forward)
        graph[v].append(backward)

    for u, v, low, high in edges:
        if low < 0 or high < low:
            return False
        add(u, v, high - low)
        balance[u] = balance.get(u, 0) - low
        balance[v] = balance.get(v, 0) + low
    source, sink = ('super-source',), ('super-sink',)
    demand = 0
    for node, amount in balance.items():
        if amount > 0:
            add(source, node, amount)
            demand += amount
        elif amount < 0:
            add(node, sink, -amount)
    total = 0
    while total < demand:
        parents = {source: None}
        queue = deque([source])
        while queue and sink not in parents:
            u = queue.popleft()
            for index, (v, capacity, _) in enumerate(graph.get(u, ())):
                if capacity and v not in parents:
                    parents[v] = (u, index)
                    queue.append(v)
        if sink not in parents:
            return False
        amount = demand - total
        v = sink
        while v != source:
            u, index = parents[v]
            amount = min(amount, graph[u][index][1])
            v = u
        v = sink
        while v != source:
            u, index = parents[v]
            edge = graph[u][index]
            edge[1] -= amount
            graph[v][edge[2]][1] += amount
            v = u
        total += amount
    return True


def solve(problem, stats=None):
    validate_problem(problem)
    supply = dict(problem.supply)
    partners = tuple(sorted((p for p in problem.partners
                             if min(len(p.outgoing), len(p.incoming)) >= 5),
                            key=lambda p: p.partner_id))
    counters = {'subsets': 0, 'pruned': 0, 'flow_checks': 0, 'orders': 0}
    winner = None
    winner_key = plan_key(())[:4]

    def feasible(subset, sizes, total_bounds, fixed=None):
        counters['flow_checks'] += 1
        fixed = fixed or {}
        source, sink = ('source',), ('sink',)
        outs = sorted({k for p in subset for k in p.outgoing})
        ins = sorted({k for p in subset for k in p.incoming})
        edges = [(source, ('out', k), 0, supply[k]) for k in outs]
        edges += [(('in', k), sink, 0, 1) for k in ins]
        for p in subset:
            left, right = ('left', p.partner_id), ('right', p.partner_id)
            edges.append((left, right, *sizes[p.partner_id]))
            for direction, keys in (('out', p.outgoing), ('in', p.incoming)):
                for k in sorted(keys):
                    bounds = fixed.get((direction, p.partner_id, k), (0, 1))
                    u, v = (('out', k), left) if direction == 'out' else (right, ('in', k))
                    edges.append((u, v, *bounds))
        edges.append((sink, source, *total_bounds))
        return circulation(edges)

    def largest(low, high, predicate):
        # Predicate means feasible with an AT LEAST bound, hence monotone.
        if low < high and predicate(high):
            return high
        while low < high:
            mid = (low + high + 1) // 2
            if predicate(mid):
                low = mid
            else:
                high = mid - 1
        return low

    global_upper = min(sum(supply.values()), len({k for p in partners for k in p.incoming}))
    for count in range(1, min(5, len(partners), global_upper // 5) + 1):
        for subset in combinations(partners, count):
            counters['subsets'] += 1
            maxima = {p.partner_id: min(len(p.outgoing), len(p.incoming)) for p in subset}
            out_union = {k for p in subset for k in p.outgoing}
            in_union = {k for p in subset for k in p.incoming}
            upper = min(sum(maxima.values()), sum(supply[k] for k in out_union), len(in_union))
            # Componentwise deal upper bounds give a safe sorted-D upper bound.
            # Sorted IDs are a J lower bound over every possible output order.
            optimistic = (-(upper - 2 * count), -upper,
                          tuple(-v for v in sorted(maxima.values(), reverse=True)),
                          tuple(p.partner_id for p in subset))
            if upper < 5 * count or optimistic >= winner_key:
                counters['pruned'] += 1
                continue
            sizes = {p: (5, size) for p, size in maxima.items()}
            if not feasible(subset, sizes, (0, upper)):
                continue
            gain = largest(0, upper, lambda g: feasible(subset, sizes, (g, upper)))
            if (-(gain - 2 * count), -gain) > winner_key[:2]:
                continue
            # All output orders considered; no early ID/rank selection.
            for order in permutations(subset):
                counters['orders'] += 1
                exact = dict(sizes)
                for p in order:
                    pid = p.partner_id
                    size = largest(5, maxima[pid], lambda d: feasible(
                        subset, {**exact, pid: (d, maxima[pid])}, (gain, gain)))
                    exact[pid] = (size, size)
                ordered = sorted(exact, key=lambda p: (-exact[p][0], p))
                key = (-(gain - 2 * count), -gain, tuple(-exact[p][0] for p in ordered), tuple(ordered))
                if key < winner_key:
                    winner_key = key
                    winner = (subset, exact, gain, ordered)
    if winner is None:
        if stats is not None:
            stats.update(counters)
        return ()
    subset, sizes, gain, ordered = winner
    by_id = {p.partner_id: p for p in subset}
    fixed = {}
    deals = []
    # Unique E/G/D/J fixes sizes and people. Lex smallest fixed-size piece
    # sequence includes the earliest identity iff an optimal completion exists.
    for pid in ordered:
        selected = {}
        for direction, keys in (('in', by_id[pid].incoming), ('out', by_id[pid].outgoing)):
            selected[direction] = []
            ordered_keys = sorted(keys)
            for index, k in enumerate(ordered_keys):
                edge = (direction, pid, k)
                needed = sizes[pid][0] - len(selected[direction])
                if needed == 0:
                    fixed[edge] = (0, 0)
                    continue
                fixed[edge] = (1, 1)
                # If every remaining edge is needed, feasibility of the current
                # prefix already proves these edges forced. No solve necessary.
                if needed == len(ordered_keys) - index or feasible(subset, sizes, (gain, gain), fixed):
                    selected[direction].append(k)
                else:
                    fixed[edge] = (0, 0)
        deals.append(Deal(pid, tuple(selected['in']), tuple(selected['out'])))
    result = canonical(deals)
    validate_plan(problem, result)
    if stats is not None:
        stats.update(counters)
    return result
