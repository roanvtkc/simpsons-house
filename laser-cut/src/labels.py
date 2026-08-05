"""Work out where a part number can be engraved on each part.

Builds the true solid region of every part (outline minus its holes) via
even-odd combination of its closed rings, then picks the point furthest from
any edge (pole of inaccessibility) and the largest text that clears it.
"""
import math
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, polylabel, unary_union
from shapely.prepared import prep
from strokefont import text_width, GH

MAX_H = 7.0      # preferred cap height, mm
MIN_H = 2.2      # below this the engraving is not readable -- skip the part
CLEAR = 1.2      # keep the text at least this far from any cut edge, mm
SNAP = 1e-3      # weld endpoints within 0.001 mm so rings actually close
BRIDGE = 0.25    # close outline gaps up to this size (analysis only -- the cut
                 # geometry emitted to the DXF is never modified)
GAPS = []        # (part_index, gap_mm) recorded for the report


def _snap(p):
    return (round(p[0] / SNAP) * SNAP, round(p[1] / SNAP) * SNAP)


def _bridge_gaps(segs, tag):
    """Join dangling endpoints that are within BRIDGE of each other.

    The source export leaves sub-0.1 mm gaps in a few outlines, which stops the
    ring from closing. Welding them lets us compute the solid region; it has no
    effect on what gets cut.
    """
    import collections
    deg = collections.Counter()
    for a, b in segs:
        deg[a] += 1
        deg[b] += 1
    loose = [p for p, d in deg.items() if d == 1]
    used = set()
    for i, p in enumerate(loose):
        if p in used:
            continue
        for q in loose[i + 1:]:
            if q in used:
                continue
            d = math.dist(p, q)
            if 0 < d <= BRIDGE:
                segs.add((p, q) if p < q else (q, p))
                used.add(p)
                used.add(q)
                GAPS.append((tag, d))
                break


def part_solid(ents, idxs, tag=None):
    """Shapely geometry of the material of one part, holes removed."""
    segs = set()
    for i in idxs:
        e = ents[i]
        if e.dxftype() == 'LINE':
            a, b = _snap(e.dxf.start), _snap(e.dxf.end)
            if a != b:
                segs.add((a, b) if a < b else (b, a))   # dedupe, ignore direction
        else:  # CIRCLE -> a closed ring (a hole through the material)
            c, r = e.dxf.center, e.dxf.radius
            pts = [(c[0] + r * math.cos(t * math.tau / 64),
                    c[1] + r * math.sin(t * math.tau / 64)) for t in range(64)]
            pts.append(pts[0])
            for u, v in zip(pts, pts[1:]):
                segs.add((_snap(u), _snap(v)))
    _bridge_gaps(segs, tag)
    # unary_union nodes every crossing and T-junction, which polygonize needs
    noded = unary_union([LineString(s) for s in segs])
    rings = list(polygonize(noded))
    if not rings:
        return None
    # nesting depth decides material vs hole: depth 0 = solid, 1 = hole, 2 = island
    rings.sort(key=lambda g: -g.area)
    prepped = [(prep(g), g) for g in rings]
    solid, holes = [], []
    for i, g in enumerate(rings):
        pt = g.representative_point()
        depth = sum(1 for j, (pg, og) in enumerate(prepped)
                    if j != i and og.area > g.area and pg.contains(pt))
        (holes if depth % 2 else solid).append(g)
    if not solid:
        return None
    out = unary_union(solid)
    if holes:
        out = out.difference(unary_union(holes))
    return out


def label_spot(solid, digits=2):
    """Return (x, y, cap_height) for the number, or None if it will not fit."""
    if solid is None or solid.is_empty:
        return None
    # work on the largest single piece of material
    geoms = getattr(solid, 'geoms', [solid])
    best = max((g for g in geoms if g.geom_type == 'Polygon'),
               key=lambda g: g.area, default=None)
    if best is None or best.area <= 0:
        return None
    try:
        p = polylabel(best, tolerance=0.25)
    except Exception:
        p = best.representative_point()
    r = p.distance(best.exterior)
    for interior in best.interiors:
        r = min(r, p.distance(interior))
    r -= CLEAR
    if r <= 0:
        return None
    # text box is text_width x GH in glyph units; half-diagonal must clear r
    aspect = text_width('0' * digits) / GH          # width / height
    half_diag = ((aspect / 2) ** 2 + 0.25) ** 0.5   # in units of cap height
    h = min(MAX_H, r / half_diag)
    if h < MIN_H:
        return None
    return (p.x, p.y, h)
