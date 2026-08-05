"""Work out where a part number can be engraved on each part.

Builds the true solid region of every part (outline minus its holes) via
even-odd combination of its closed rings, then picks the point furthest from
any edge (pole of inaccessibility) and the largest text that clears it.
"""
import math
from shapely.geometry import LineString, Polygon, Point, box
from shapely.affinity import rotate
from shapely.ops import polygonize, unary_union
from shapely.prepared import prep
from strokefont import text_width, GH

MAX_H = 7.0      # preferred cap height, mm
MIN_H = 1.8      # below this the engraving is not readable -- skip the part
CLEAR = 1.0      # preferred gap between text and any cut edge, mm
# Narrow frame parts have no room at the preferred clearance. Rather than leave
# them blank, step the clearance down. 0.5 mm is still several times the kerf.
CLEARANCES = (1.0, 0.7, 0.5)
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
    # unary_union nodes every crossing and T-junction, which polygonize needs.
    noded = unary_union([LineString(s) for s in segs])
    faces = list(polygonize(noded))
    if not faces:
        return None

    # polygonize returns MINIMAL faces, not simple rings: an outline with a
    # window comes back as an annulus plus the window, and the annulus does not
    # contain the window's interior points. Classifying those faces by nesting
    # depth marks the window as material. Work from the rings instead -- every
    # face exterior and every face interior -- and apply the even-odd rule to
    # those, which is what a cut path actually means.
    rings, seen = [], set()
    for f in faces:
        for coords in [f.exterior.coords] + [i.coords for i in f.interiors]:
            poly = Polygon(coords)
            if not poly.is_valid or poly.area <= 0:
                continue
            key = tuple(sorted((round(x, 4), round(y, 4)) for x, y in coords))
            if key in seen:
                continue
            seen.add(key)
            rings.append(poly)
    if not rings:
        return None

    # A ring nested inside an odd number of other rings bounds a hole.
    rings.sort(key=lambda g: -g.area)
    prepped = [prep(g) for g in rings]
    solid, holes = [], []
    for i, g in enumerate(rings):
        pt = g.representative_point()
        depth = sum(1 for j in range(i) if prepped[j].contains(pt))
        (holes if depth % 2 else solid).append(g)
    if not solid:
        return None
    out = unary_union(solid)
    if holes:
        out = out.difference(unary_union(holes))
    return out if not out.is_empty else None


def _largest_fit(psafe, cx, cy, aspect, angle):
    """Biggest cap height whose text box fits inside `safe` at this spot/angle."""
    lo, hi = 0.0, MAX_H
    for _ in range(16):
        mid = (lo + hi) / 2
        w, h = aspect * mid, mid
        rect = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if angle:
            rect = rotate(rect, angle, origin=(cx, cy))
        if psafe.contains(rect):
            lo = mid
        else:
            hi = mid
    return lo


def part_lines(ents, idxs):
    """Every cut or score line of a part, as one geometry.

    Includes open linework -- the garage door's slats are free-standing score
    lines that form no ring, so they never appear in the solid, but a number
    must not run across them either.
    """
    out = []
    for i in idxs:
        e = ents[i]
        if e.dxftype() == 'LINE':
            a, b = _snap(e.dxf.start), _snap(e.dxf.end)
            if a != b:
                out.append(LineString([a, b]))
        else:
            c, r = e.dxf.center, e.dxf.radius
            pts = [(c[0] + r * math.cos(t * math.tau / 64),
                    c[1] + r * math.sin(t * math.tau / 64)) for t in range(65)]
            out.append(LineString(pts))
    return unary_union(out) if out else None


def _spot_at(solid, aspect, clear, lines=None):
    """Best (x, y, h, angle) achievable at this clearance, or None."""
    safe = solid.buffer(-clear)
    if lines is not None and not safe.is_empty:
        safe = safe.difference(lines.buffer(clear))
    if safe.is_empty:
        return None
    psafe = prep(safe)
    boundary = safe.boundary
    minx, miny, maxx, maxy = safe.bounds
    step = max(maxx - minx, maxy - miny) / 70 or 1.0

    cands = []
    y = miny
    while y <= maxy:
        x = minx
        while x <= maxx:
            p = Point(x, y)
            if psafe.contains(p):
                cands.append((p.distance(boundary), x, y))
            x += step
        y += step
    if not cands:
        return None
    cands.sort(reverse=True)

    best = None
    for _, x, y in cands[:25]:
        for angle in (0, 90):
            h = _largest_fit(psafe, x, y, aspect, angle)
            if best is None or h > best[2]:
                best = (x, y, h, angle)
    return best


def label_spot(solid, digits=2, lines=None):
    """Return (x, y, cap_height, angle) for the number, or None if it won't fit.

    Tries the number both upright and turned 90 degrees -- a thin frame part has
    no room for a horizontal number but plenty along the band. Falls back to a
    tighter clearance before giving up.
    """
    if solid is None or solid.is_empty:
        return None
    aspect = text_width('0' * digits) / GH
    for clear in CLEARANCES:
        best = _spot_at(solid, aspect, clear, lines)
        if best and best[2] >= MIN_H:
            return (best[0], best[1], min(best[2], MAX_H), best[3])
    return None
