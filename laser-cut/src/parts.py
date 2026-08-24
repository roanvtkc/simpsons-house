"""Group DXF geometry into top-level cuttable parts (outline + nested holes)."""
import ezdxf, collections, os

# The Shapr3D export. Override with SIMPSONS_DXF=/path/to/other.dxf
SRC = os.environ.get(
    "SIMPSONS_DXF",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "source", "Simpsons House with precuts.dxf"))
TOL = 1e-4


def load_components(src=SRC):
    doc = ezdxf.readfile(src)
    msp = doc.modelspace()
    ents = [e for e in msp if e.dxftype() in ('LINE', 'CIRCLE')]

    # DXF stores a CIRCLE centre in the entity's object coordinate system
    # (OCS), unlike LINE endpoints. The Shapr3D export uses a reversed normal,
    # so reading dxf.center directly makes the six panel cutouts appear at
    # negative X even though their world-coordinate positions are inside the
    # panels. Normalize them once here so every downstream geometry operation
    # sees the authored sheet coordinates.
    for e in ents:
        if e.dxftype() == 'CIRCLE':
            c = e.ocs().to_wcs(e.dxf.center)
            e.dxf.center = (c.x, c.y, 0.0)
            e.dxf.extrusion = (0.0, 0.0, 1.0)

    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def add(x):
        if x not in parent:
            parent[x] = x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def key(p):
        return (round(p[0] / TOL), round(p[1] / TOL))

    nodes = []
    for i, e in enumerate(ents):
        if e.dxftype() == 'LINE':
            a, b = key(e.dxf.start), key(e.dxf.end)
            add(a); add(b); union(a, b)
            nodes.append((i, a))
        else:
            c = e.dxf.center
            a = (round(c[0] / TOL), round(c[1] / TOL), 'c', i)
            add(a)
            nodes.append((i, a))

    groups = collections.defaultdict(list)
    for i, n in nodes:
        groups[find(n)].append(i)
    return doc, ents, list(groups.values())


def bbox_of(ents, idxs):
    xs, ys = [], []
    for i in idxs:
        e = ents[i]
        if e.dxftype() == 'LINE':
            xs += [e.dxf.start[0], e.dxf.end[0]]
            ys += [e.dxf.start[1], e.dxf.end[1]]
        else:
            c, r = e.dxf.center, e.dxf.radius
            xs += [c[0] - r, c[0] + r]
            ys += [c[1] - r, c[1] + r]
    return min(xs), min(ys), max(xs), max(ys)


def merge_nested(ents, comps):
    """Absorb components whose bbox lies inside another component's bbox."""
    boxes = [bbox_of(ents, c) for c in comps]
    order = sorted(range(len(comps)), key=lambda i: -((boxes[i][2] - boxes[i][0]) *
                                                      (boxes[i][3] - boxes[i][1])))
    owner = {}

    def contains(a, b, eps=1e-6):
        return (a[0] - eps <= b[0] and a[1] - eps <= b[1] and
                a[2] + eps >= b[2] and a[3] + eps >= b[3])

    for pos, i in enumerate(order):
        for j in order[:pos]:
            root = j
            while root in owner:
                root = owner[root]
            if contains(boxes[root], boxes[i]):
                owner[i] = root
                break

    merged = collections.defaultdict(list)
    for i in range(len(comps)):
        root = i
        while root in owner:
            root = owner[root]
        merged[root] += comps[i]
    return list(merged.values())


if __name__ == '__main__':
    doc, ents, comps = load_components()
    parts = merge_nested(ents, comps)
    rows = []
    for c in parts:
        x0, y0, x1, y1 = bbox_of(ents, c)
        rows.append((x1 - x0, y1 - y0, len(c), x0, y0))
    rows.sort(key=lambda r: -(r[0] * r[1]))
    print(f"top-level parts: {len(parts)}\n")
    tot = 0
    for i, (w, h, n, x0, y0) in enumerate(rows):
        tot += w * h
        print(f"{i:3d}  {w:8.2f} x {h:8.2f} mm   ents={n:5d}  at ({x0:9.2f},{y0:8.2f})")
    print(f"\nsum of part bbox area = {tot/100:.1f} cm^2 "
          f"({tot/(600*600):.2f} sheets of 600x600 at 100% packing)")
