"""How a lesson scores from the nodes that match a query (graph.py). rows = [(similarity, lesson id, path key)] of the searched
nodes. Variants (tried against each other by eval_variants.py): best = its best node; top3 = mean of its 3 best nodes;
path = its best occurrence, an occurrence scoring as the mean of its 2 best nodes; normN = best node minus N/100 * ln(its
node count), so a lesson with many examples does not win by having many chances. Returns [(score, lesson id, path key)] best first."""
import math
from collections import defaultdict


def agg(rows, variant="best"):
    by = defaultdict(list)
    for s, lid, p in rows:
        by[lid].append((s, p))
    out = []
    for lid, ns in by.items():
        ns.sort(key=lambda x: -x[0])
        if variant == "top3":
            out.append((sum(s for s, _ in ns[:3]) / len(ns[:3]), lid, ns[0][1]))
        elif variant == "path":
            ps = defaultdict(list)
            for s, p in ns:
                ps[p].append(s)
            out.append(max((sum(v[:2]) / len(v[:2]), lid, p) for p, v in ps.items()))
        elif variant.startswith("norm"):
            out.append((ns[0][0] - int(variant[4:]) / 100 * math.log(len(ns)), lid, ns[0][1]))
        else:
            out.append((ns[0][0], lid, ns[0][1]))
    return sorted(out, key=lambda x: -x[0])
