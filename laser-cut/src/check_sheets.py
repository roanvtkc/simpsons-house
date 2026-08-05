"""End-to-end check on the written sheet DXFs.

Reads back what will actually be cut and confirms, in final sheet coordinates,
that every ENGRAVE stroke sits on material and clear of every CUT line. This is
the check that would catch a bad transform on the rotated copies, because it
never looks at the source drawing at all.
"""
import glob, math, sys, collections
import ezdxf
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
from shapely.prepared import prep

MIN_GAP = 0.35
SNAP = 1e-3


def snap(p):
    return (round(p[0] / SNAP) * SNAP, round(p[1] / SNAP) * SNAP)


total_strokes = 0
problems = []

for path in sorted(glob.glob(sys.argv[1] + "/sheet-*.dxf")):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    cut, eng = [], []
    for e in msp:
        if e.dxf.layer == 'CUT':
            if e.dxftype() == 'LINE':
                a, b = snap(e.dxf.start), snap(e.dxf.end)
                if a != b:
                    cut.append(LineString([a, b]))
            else:
                c, r = e.dxf.center, e.dxf.radius
                pts = [(c[0] + r * math.cos(t * math.tau / 64),
                        c[1] + r * math.sin(t * math.tau / 64)) for t in range(65)]
                cut.append(LineString(pts))
        elif e.dxf.layer == 'ENGRAVE' and e.dxftype() == 'LINE':
            eng.append(LineString([(e.dxf.start[0], e.dxf.start[1]),
                                   (e.dxf.end[0], e.dxf.end[1])]))

    # material on this sheet = even-odd fill of everything the cutter closes
    faces = list(polygonize(unary_union(cut)))
    rings, seen = [], set()
    from shapely.geometry import Polygon
    for f in faces:
        for coords in [f.exterior.coords] + [i.coords for i in f.interiors]:
            key = tuple(sorted((round(x, 3), round(y, 3)) for x, y in coords))
            if key in seen:
                continue
            seen.add(key)
            poly = Polygon(coords)
            if poly.is_valid and poly.area > 0:
                rings.append(poly)
    rings.sort(key=lambda g: -g.area)
    pre = [prep(g) for g in rings]
    solid, holes = [], []
    for i, g in enumerate(rings):
        pt = g.representative_point()
        depth = sum(1 for j in range(i) if pre[j].contains(pt))
        (holes if depth % 2 else solid).append(g)
    material = unary_union(solid)
    if holes:
        material = material.difference(unary_union(holes))
    pmat = prep(material)

    tree = STRtree(cut)
    off_material = near_cut = 0
    for ls in eng:
        total_strokes += 1
        if not pmat.contains(ls):
            off_material += 1
            continue
        for j in tree.query(ls.buffer(MIN_GAP)):
            if ls.distance(cut[j]) < MIN_GAP:
                near_cut += 1
                break
    name = path.split('/')[-1]
    if off_material or near_cut:
        problems.append(f"{name}: {off_material} strokes off material, "
                        f"{near_cut} closer than {MIN_GAP} mm to a cut")
    print(f"  {name}: {len(eng):5d} engrave strokes, {len(cut):5d} cut lines "
          f"-> {'OK' if not (off_material or near_cut) else 'PROBLEM'}")

print()
if problems:
    for p in problems:
        print("  !!", p)
    raise SystemExit("END-TO-END CHECK FAILED")
print(f"END-TO-END CHECK PASSED: {total_strokes} engrave strokes, all on "
      f"material and >= {MIN_GAP} mm from every cut line")
