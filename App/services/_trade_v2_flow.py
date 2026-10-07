"""Balance-group feasibility inside the existing exact SmartDeal subset search.

Bucket edges conserve each bilateral album pool. Partner size constraints are
sums of those edges; branch-and-bound proves integral feasibility without
changing E/G/D/J/C objectives, ranking, subset search or resource capacities.
"""
from services._smartdeal_flow import _has_circulation


class ScopedSubsetNetwork:
    def __init__(self, subset, supply, counters, needs=None):
        self.subset, self.counters, self.cache = subset, counters, {}
        self.edges, self.size_indices, self.piece_indices = [], {}, {}
        outgoing = sorted({k for p in subset for k in p.outgoing})
        incoming = sorted({k for p in subset for k in p.incoming})
        out_nodes = {k:i+2 for i,k in enumerate(outgoing)}
        in_nodes = {k:i+2+len(outgoing) for i,k in enumerate(incoming)}
        node = 2+len(outgoing)+len(incoming)
        self.edges.extend((0,out_nodes[k],0,supply[k]) for k in outgoing)
        self.edges.extend((in_nodes[k],1,0,(needs or {}).get(k,1)) for k in incoming)
        for p in subset:
            groups = p.balance_groups or (tuple(sorted({k[0] for k in p.outgoing+p.incoming})),)
            indices = []
            for group in groups:
                out = tuple(k for k in p.outgoing if k[0] in group)
                inc = tuple(k for k in p.incoming if k[0] in group)
                left,right = node,node+1
                node += 2
                indices.append(len(self.edges))
                self.edges.append((left,right,0,min(sum(p.capacity("out",k) for k in out),sum(p.capacity("in",k) for k in inc))))
                for direction,keys in (('out',out),('in',inc)):
                    for k in keys:
                        self.piece_indices[(direction,p.partner_id,k)] = len(self.edges)
                        u,v = (out_nodes[k],left) if direction=='out' else (right,in_nodes[k])
                        self.edges.append((u,v,0,p.capacity(direction,k)))
            self.size_indices[p.partner_id] = tuple(indices)
        self.return_index = len(self.edges)
        self.edges.append((1,0,0,0))
        self.vertex_count = node

    def feasible(self, sizes, total_bounds, fixed=None):
        key = (tuple(sizes[p.partner_id] for p in self.subset),total_bounds)
        if fixed is None and key in self.cache:
            self.counters['cache_hits'] += 1
            return self.cache[key]
        edges = list(self.edges)
        edges[self.return_index] = (1,0,*total_bounds)
        for piece,bounds in (fixed or {}).items():
            index = self.piece_indices[piece]
            edges[index] = (*edges[index][:2],*bounds)

        def search(current):
            # Exact propagation of each partner's sum-of-buckets bounds.
            changed = True
            while changed:
                changed = False
                for pid,indices in self.size_indices.items():
                    low,high = sizes[pid]
                    lows = sum(current[i][2] for i in indices)
                    highs = sum(current[i][3] for i in indices)
                    if lows > high or highs < low:
                        return False
                    for i in indices:
                        u,v,a,b = current[i]
                        lo,hi = max(a,low-(highs-b)),min(b,high-(lows-a))
                        if lo > hi:
                            return False
                        if (lo,hi)!=(a,b):
                            current[i]=(u,v,lo,hi)
                            changed=True
            self.counters['flow_checks'] += 1
            flows = _has_circulation(self.vertex_count,current,return_flows=True)
            if flows is None:
                return False
            for pid,indices in self.size_indices.items():
                low,high = sizes[pid]
                if low <= sum(flows[i] for i in indices) <= high:
                    continue
                # Both integer halves partition all possibilities; no heuristic loss.
                candidates = [i for i in indices if current[i][2]<current[i][3]]
                if not candidates:
                    return False
                i = max(candidates,key=lambda j:current[j][3]-current[j][2])
                u,v,a,b = current[i]; mid=(a+b)//2
                first=list(current);first[i]=(u,v,a,mid)
                second=list(current);second[i]=(u,v,mid+1,b)
                return search(first) or search(second)
            return True
        result = search(edges)
        if fixed is None:
            self.cache[key]=result
        return result
