"""Group parts that are the same shape (allowing rotation and mirroring).

The assembly PDF numbers each piece as it is fitted, so identical pieces get
several callouts. Knowing which parts are duplicates constrains the mapping.
"""
import collections, math
from parts import load_components, merge_nested, bbox_of
from labels import part_solid

doc, ents, comps = load_components()
allparts = merge_nested(ents, comps)

recs = []
for c in allparts:
    if len(c) == 1 and ents[c[0]].dxftype() == 'CIRCLE':
        continue
    x0, y0, x1, y1 = bbox_of(ents, c)
    recs.append(dict(idx=c, w=x1 - x0, h=y1 - y0, ox=x0, oy=y0))
recs.sort(key=lambda r: -(r['w'] * r['h']))

for pi, r in enumerate(recs):
    s = part_solid(ents, r['idx'], tag=pi)
    r['area'] = s.area if s is not None else 0.0
    r['perim'] = s.length if s is not None else 0.0
    r['nseg'] = len(r['idx'])

# signature invariant to rotation and mirroring
def sig(r):
    dims = tuple(sorted((round(r['w'], 1), round(r['h'], 1))))
    return (dims, round(r['area'], 0), round(r['perim'], 0))

groups = collections.defaultdict(list)
for pi, r in enumerate(recs):
    groups[sig(r)].append(pi)

print(f"{len(recs)} parts -> {len(groups)} distinct shapes\n")
print("DUPLICATE GROUPS (same shape, cut more than once):")
tot_dup = 0
for s, ids in sorted(groups.items(), key=lambda kv: kv[1][0]):
    if len(ids) > 1:
        r = recs[ids[0]]
        print(f"  {ids}  {r['w']:.1f} x {r['h']:.1f} mm, area {r['area']:.0f} mm2")
        tot_dup += len(ids)
print(f"\n{tot_dup} parts belong to a duplicate group; "
      f"{len(recs)-tot_dup} are unique.")

print("\nNEAR MATCHES (same bbox, different shape - check these are really distinct):")
bybox = collections.defaultdict(list)
for pi, r in enumerate(recs):
    bybox[tuple(sorted((round(r['w']), round(r['h']))))].append(pi)
for k, ids in sorted(bybox.items(), key=lambda kv: kv[1][0]):
    if len(ids) > 1 and len({sig(recs[i]) for i in ids}) > 1:
        print(f"  bbox {k[0]}x{k[1]}: " +
              ", ".join(f"{i}(a={recs[i]['area']:.0f})" for i in ids))
