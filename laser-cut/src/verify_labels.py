"""Independent check that engraved numbers land on material.

Deliberately does NOT reuse part_solid(). The earlier bug survived because the
check validated the text against the same (wrong) solid that positioned it. This
tests the text directly against the raw cut segments instead:

  1. even-odd ray casting -- a point is on material if a ray to infinity crosses
     the cut lines an odd number of times;
  2. minimum distance from every stroke to every cut segment.
"""
import math
from shapely.geometry import LineString, MultiLineString
from shapely.strtree import STRtree
import strokefont

MIN_GAP = 0.35   # hard floor: no engrave stroke closer than this to a cut, mm


def _segments(ents, idxs):
    segs = []
    for i in idxs:
        e = ents[i]
        if e.dxftype() == 'LINE':
            a = (e.dxf.start[0], e.dxf.start[1])
            b = (e.dxf.end[0], e.dxf.end[1])
            if a != b:
                segs.append((a, b))
        else:
            c, r = e.dxf.center, e.dxf.radius
            pts = [(c[0] + r * math.cos(t * math.tau / 64),
                    c[1] + r * math.sin(t * math.tau / 64)) for t in range(65)]
            segs += list(zip(pts, pts[1:]))
    return segs


def _crossings(segs, px, py):
    """How many cut segments a ray heading +x from (px,py) crosses."""
    n = 0
    for (x1, y1), (x2, y2) in segs:
        if (y1 > py) == (y2 > py):
            continue
        t = (py - y1) / (y2 - y1)
        if x1 + t * (x2 - x1) > px:
            n += 1
    return n


def check_part(ents, idxs, text, spot, samples=7):
    """Return a list of problems for one labelled part (empty means fine)."""
    if spot is None:
        return []
    x, y, h, angle = spot
    segs = _segments(ents, idxs)
    problems = []

    polys = strokefont.strokes(text, h, x, y, angle)

    # 1. every sampled point along every stroke must be on material
    for poly in polys:
        for (ax, ay), (bx, by) in zip(poly, poly[1:]):
            for k in range(samples + 1):
                t = k / samples
                px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                # nudge off exact vertical alignment with any vertex
                if _crossings(segs, px, py + 1e-7) % 2 == 0:
                    problems.append(f"stroke point ({px:.2f},{py:.2f}) is not on material")
                    return problems

    # 2. clearance from every cut segment
    tree = STRtree([LineString(s) for s in segs])
    for poly in polys:
        ls = LineString(poly)
        for j in tree.query(ls.buffer(MIN_GAP)):
            d = ls.distance(LineString(segs[j]))
            if d < MIN_GAP:
                problems.append(f"stroke passes {d:.3f} mm from a cut line "
                                f"(minimum {MIN_GAP})")
                return problems
    return problems
