"""Nest the Simpsons house parts onto fixed-size laser sheets.

Writes one DXF per sheet plus an SVG/PNG preview of the whole run.
"""
import argparse, math, os, collections
import ezdxf
from rectpack import newPacker, MaxRectsBssf, SORT_AREA, PackingBin
from parts import load_components, merge_nested, bbox_of, SRC
import labels as labelmod
from labels import part_solid, part_lines, label_spot
from verify_labels import check_part, MIN_GAP
import strokefont

AP = argparse.ArgumentParser()
AP.add_argument('--copies', type=int, default=10)
AP.add_argument('--sheet-w', type=float, default=600.0, help='sheet width (X) in mm')
AP.add_argument('--sheet-h', type=float, default=450.0, help='sheet height (Y) in mm')
AP.add_argument('--margin', type=float, default=5.0, help='clear border inside sheet edge')
AP.add_argument('--gap', type=float, default=3.0, help='clear space between parts')
AP.add_argument('--no-rotate', action='store_true')
AP.add_argument('--keep-strays', action='store_true',
                help='include the 6 isolated circles at negative X')
AP.add_argument('--outdir', default='nested')
AP.add_argument('--no-engrave', action='store_true',
                help='omit the ENGRAVE layer with part numbers')
args = AP.parse_args()

SW, SH = args.sheet_w, args.sheet_h
UW, UH = SW - 2 * args.margin, SH - 2 * args.margin
SHEET_AREA = SW * SH

doc, ents, comps = load_components()
parts = merge_nested(ents, comps)

# ---------------------------------------------------------------- part records
records = []
strays = []
for c in parts:
    x0, y0, x1, y1 = bbox_of(ents, c)
    rec = dict(idx=c, w=x1 - x0, h=y1 - y0, ox=x0, oy=y0)
    is_stray = len(c) == 1 and ents[c[0]].dxftype() == 'CIRCLE'
    (strays if is_stray else records).append(rec)

if args.keep_strays:
    records += strays
    strays = []

records.sort(key=lambda r: -(r['w'] * r['h']))
print(f"parts/house: {len(records)}   excluded strays: {len(strays)}")
# -------------------------------------------------- engrave label per part
# The number goes at the roomiest spot on the part's material, turned along the
# grain of a narrow band if that is the only way it fits. Holes, scrap and open
# score lines are all treated as obstacles.
if not args.no_engrave:
    unlabelled = []
    for pi, r in enumerate(records):
        solid = part_solid(ents, r['idx'], tag=pi)
        spot = label_spot(solid, lines=part_lines(ents, r['idx']))
        if spot is None:
            r['label'] = None
            unlabelled.append(pi)
        else:
            lx, ly, lh, la = spot
            r['label'] = (lx - r['ox'], ly - r['oy'], lh, la)   # part-local

    # Independent check -- deliberately does NOT reuse part_solid(). An earlier
    # version validated the text against the same solid that positioned it, so a
    # wrong solid passed its own check and numbers landed in window openings.
    # check_part() works from the raw cut segments instead.
    bad = []
    for pi, r in enumerate(records):
        if not r['label']:
            continue
        lx, ly, lh, la = r['label']
        problems = check_part(ents, r['idx'], f"{pi:02d}",
                              (lx + r['ox'], ly + r['oy'], lh, la))
        if problems:
            bad.append((pi, problems[0]))
    if bad:
        for pi, p in bad:
            print(f"  !! part {pi}: {p}")
        raise SystemExit(f"ENGRAVE CHECK FAILED on {len(bad)} parts")
    print(f"engrave check: {sum(1 for r in records if r['label'])} numbers verified "
          f"on material and >= {MIN_GAP} mm from every cut  [OK]")
    n_lab = sum(1 for r in records if r['label'])
    n_rot = sum(1 for r in records if r['label'] and r['label'][3])
    print(f"engrave: {n_lab}/{len(records)} parts numbered ({n_rot} turned 90 deg)"
          + (f"; no room on {unlabelled}" if unlabelled else ""))
    if labelmod.GAPS:
        worst = max(d for _, d in labelmod.GAPS)
        print(f"note: bridged {len(labelmod.GAPS)} open-contour gaps in the source "
              f"(largest {worst:.3f} mm) for analysis only")
else:
    for r in records:
        r['label'] = None

print(f"sheet {SW:.0f} x {SH:.0f} mm -> usable {UW:.0f} x {UH:.0f} mm")
for pi, r in enumerate(records):
    fits = (r['w'] + args.gap <= UW and r['h'] + args.gap <= UH)
    fits_rot = (not args.no_rotate and
                r['h'] + args.gap <= UW and r['w'] + args.gap <= UH)
    if not (fits or fits_rot):
        raise SystemExit(f"part {pi} is {r['w']:.1f}x{r['h']:.1f} mm and will not "
                         f"fit the usable area {UW:.0f}x{UH:.0f} in either orientation")

# ------------------------------------------------------------------- packing
# MaxRects best-short-side-fit is materially better for mixed-size panels than
# the earlier bottom-left skyline heuristic. In particular it reaches the
# three-sheet theoretical minimum for two houses on 450 x 450 mm stock.
packer = newPacker(pack_algo=MaxRectsBssf, sort_algo=SORT_AREA,
                   bin_algo=PackingBin.BBF, rotation=not args.no_rotate)
# Reserve w+gap x h+gap per part inside a bin of exactly USABLE, then draw the
# part inset by gap/2 -- that guarantees >= gap clearance to every neighbour and
# >= margin to the sheet edge.
for copy in range(args.copies):
    for pi, r in enumerate(records):
        packer.add_rect(r['w'] + args.gap, r['h'] + args.gap, rid=(pi, copy))
for _ in range(400):
    packer.add_bin(UW, UH)
packer.pack()

placed = collections.defaultdict(list)
count = 0
for b, x, y, w, h, rid in packer.rect_list():
    pi, copy = rid
    r = records[pi]
    rotated = abs(w - (r['w'] + args.gap)) > 1e-6  # width no longer matches -> 90 deg
    placed[b].append((pi, copy, x, y, rotated))
    count += 1
assert count == len(records) * args.copies, (count, len(records) * args.copies)
sheets = sorted(placed)
print(f"placed {count} parts on {len(sheets)} sheets of {SW:.0f}x{SH:.0f} mm")

# ------------------------------------------------------------------- emit DXF
os.makedirs(args.outdir, exist_ok=True)


def emit(e, tx, ty, rot, out, layer):
    """Copy entity e into `out` msp, rotated 0/90 about part origin then offset."""
    def xf(p):
        x, y = p[0] - e_ox, p[1] - e_oy
        if rot:
            x, y = -y + e_h, x          # +90 deg, keep in positive quadrant
        return x + tx, y + ty
    if e.dxftype() == 'LINE':
        s, t = xf(e.dxf.start), xf(e.dxf.end)
        out.add_line(s, t, dxfattribs={'layer': layer})
    else:
        c = xf(e.dxf.center)
        out.add_circle(c, e.dxf.radius, dxfattribs={'layer': layer})


# --------------------------------------------------------------- verification
# Each part is drawn strictly inside its reserved rect, so proving the reserved
# rects are disjoint and inside the sheet proves the geometry is too.
problems = []
for b in sheets:
    boxes = []
    for pi, copy, x, y, rot in placed[b]:
        r = records[pi]
        w, h = (r['h'], r['w']) if rot else (r['w'], r['h'])
        bx = x + args.margin + args.gap / 2
        by = y + args.margin + args.gap / 2
        boxes.append((bx, by, bx + w, by + h, pi, copy))
        if bx < args.margin - 1e-6 or by < args.margin - 1e-6 or \
           bx + w > SW - args.margin + 1e-6 or by + h > SH - args.margin + 1e-6:
            problems.append(f"sheet {b}: part {pi} copy {copy} outside margin")
    boxes.sort()
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, c = boxes[i], boxes[j]
            if c[0] >= a[2]:
                break
            ox = min(a[2], c[2]) - max(a[0], c[0])
            oy = min(a[3], c[3]) - max(a[1], c[1])
            if ox > 1e-6 and oy > 1e-6:
                problems.append(f"sheet {b}: parts {a[4]}/{a[5]} and {c[4]}/{c[5]} "
                                f"overlap by {ox:.2f}x{oy:.2f} mm")
if problems:
    for p in problems[:20]:
        print("  !!", p)
    raise SystemExit(f"VERIFICATION FAILED: {len(problems)} problems")
print("verification: no overlaps, all parts inside margins  [OK]")

# also confirm every part kept all of its source entities
src_counts = collections.Counter()
for pi, r in enumerate(records):
    src_counts[pi] = len(r['idx'])
expected_ents = sum(src_counts[pi] for b in sheets for pi, _, _, _, _ in placed[b])
print(f"entities to emit: {expected_ents} "
      f"(= {sum(src_counts.values())}/house x {args.copies})")

sheet_report = []
emitted_total = 0
for si, b in enumerate(sheets, 1):
    out = ezdxf.new('R2010', setup=False)
    out.header['$INSUNITS'] = 4  # millimetres
    out.layers.add('CUT', color=1)
    out.layers.add('SHEET', color=8)
    out.layers.add('ENGRAVE', color=5)
    msp = out.modelspace()
    # sheet outline for reference
    for p, q in [((0, 0), (SW, 0)), ((SW, 0), (SW, SH)),
                 ((SW, SH), (0, SH)), ((0, SH), (0, 0))]:
        msp.add_line(p, q, dxfattribs={'layer': 'SHEET'})

    used = 0.0
    for pi, copy, x, y, rot in placed[b]:
        r = records[pi]
        e_ox, e_oy, e_h = r['ox'], r['oy'], r['h']
        tx = x + args.margin + args.gap / 2
        ty = y + args.margin + args.gap / 2
        for i in r['idx']:
            emit(ents[i], tx, ty, rot, msp, 'CUT')
        # Part number. When the nester turns a part 90 deg the number turns with
        # it -- a number sized to run along a narrow band stops fitting the
        # moment it is held upright against a rotated part.
        if r['label']:
            lx, ly, lh, la = r['label']
            LX, LY = (-ly + e_h, lx) if rot else (lx, ly)
            # mod 180: a half turn maps the text box onto itself, so this
            # never changes whether it fits, but keeps digits off upside-down
            ang = (la + (90 if rot else 0)) % 180
            for poly in strokefont.strokes(f"{pi:02d}", lh, LX + tx, LY + ty, ang):
                for p, q in zip(poly, poly[1:]):
                    msp.add_line(p, q, dxfattribs={'layer': 'ENGRAVE'})
        used += r['w'] * r['h']

    path = os.path.join(args.outdir, f"sheet-{si:02d}.dxf")
    out.saveas(path)
    back = ezdxf.readfile(path)
    n_cut = sum(1 for e in back.modelspace() if e.dxf.layer == 'CUT')
    emitted_total += n_cut
    sheet_report.append((si, len(placed[b]), used / SHEET_AREA * 100, path))
    print(f"  sheet {si:2d}: {len(placed[b]):3d} parts, {used/SHEET_AREA*100:5.1f}% area used -> {path}")

# ------------------------------------------------------------------ preview
PAL = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#0f9ba8",
       "#c026d3", "#84cc16", "#469990", "#9A6324", "#800000", "#000075"]
cols = min(len(sheets), 4)
rows = math.ceil(len(sheets) / cols)
PAD = 30
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" '
       f'viewBox="0 0 {cols*(SW+PAD)+PAD} {rows*(SH+PAD+22)+PAD}" width="1900">',
       f'<rect width="100%" height="100%" fill="#fafafa"/>']
for si, b in enumerate(sheets):
    gx = PAD + (si % cols) * (SW + PAD)
    gy = PAD + (si // cols) * (SH + PAD + 22)
    svg.append(f'<g transform="translate({gx},{gy})">')
    svg.append(f'<rect width="{SW}" height="{SH}" fill="#fff" stroke="#111" stroke-width="2"/>')
    svg.append(f'<text x="0" y="{SH+16}" font-size="18" font-family="sans-serif">'
               f'Sheet {si+1} — {len(placed[b])} parts</text>')
    for pi, copy, x, y, rot in placed[b]:
        r = records[pi]
        e_ox, e_oy, e_h = r['ox'], r['oy'], r['h']
        tx = x + args.margin + args.gap / 2
        ty = y + args.margin + args.gap / 2

        def xf(p):
            X, Y = p[0] - e_ox, p[1] - e_oy
            if rot:
                X, Y = -Y + e_h, X
            return X + tx, SH - (Y + ty)
        col = PAL[pi % len(PAL)]
        svg.append(f'<g stroke="{col}" fill="none" stroke-width="0.7">')
        for i in r['idx']:
            e = ents[i]
            if e.dxftype() == 'LINE':
                s, t = xf(e.dxf.start), xf(e.dxf.end)
                svg.append(f'<line x1="{s[0]:.2f}" y1="{s[1]:.2f}" x2="{t[0]:.2f}" y2="{t[1]:.2f}"/>')
            else:
                c = xf(e.dxf.center)
                svg.append(f'<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="{e.dxf.radius:.2f}"/>')
        svg.append('</g>')
        if r['label']:
            lx, ly, lh, la = r['label']
            LX, LY = (-ly + e_h, lx) if rot else (lx, ly)
            svg.append('<g stroke="#111" fill="none" stroke-width="0.5">')
            ang = (la + (90 if rot else 0)) % 180
            for poly in strokefont.strokes(f"{pi:02d}", lh, LX + tx, LY + ty, ang):
                d = " ".join(f"{'M' if k == 0 else 'L'}{px:.2f},{SH-py:.2f}"
                             for k, (px, py) in enumerate(poly))
                svg.append(f'<path d="{d}"/>')
            svg.append('</g>')
    svg.append('</g>')
svg.append('</svg>')
open(os.path.join(args.outdir, 'nest-preview.svg'), 'w').write('\n'.join(svg))
print(f"\npreview -> {args.outdir}/nest-preview.svg")

tot = sum(r[2] for r in sheet_report) / len(sheet_report)
print(f"average sheet utilisation (bbox): {tot:.1f}%")
assert emitted_total == expected_ents, (emitted_total, expected_ents)
print(f"round-trip check: {emitted_total} CUT entities read back from DXFs  [OK]")

# ------------------------------------------------------------------ manifest
lines = ["SIMPSONS HOUSE - NESTED CUT PLAN",
         "=" * 70,
         f"Source      : {os.path.basename(SRC)}",
         f"Houses      : {args.copies}",
         f"Sheet       : {SW:.0f} (X) x {SH:.0f} (Y) mm, {args.margin:.1f} mm border, "
         f"{args.gap:.1f} mm between parts",
         f"Parts/house : {len(records)}   Total parts: {len(records)*args.copies}",
         f"Sheets      : {len(sheets)}",
         f"Units       : millimetres (DXF $INSUNITS = 4)",
         "",
         "LAYERS IN EACH SHEET DXF",
         "-" * 70,
         "  CUT      the part outlines. This is the only layer that must be cut.",
         "  ENGRAVE  part numbers, single-stroke. Run as a light score/engrave,",
         "           or switch the layer off if you do not want visible marks.",
         f"  SHEET    {SW:.0f}x{SH:.0f} reference rectangle. Not for cutting - delete or",
         "           switch off before sending to the laser.",
         "",
         "Part numbers match PART-CHART.pdf and the PART LIBRARY below. They are",
         "geometry IDs assigned by size, NOT the 01-55 step callouts used in",
         "Simpsons_House_Assemble.pdf.",
         "",
         "Numbers sit on material only, clear of every cut and score line, and",
         "are turned 90 degrees where that is the only way they fit. Parts marked",
         "'no room' are too narrow to take a number at a readable size; each of",
         "them belongs to a set of identical parts, so they are interchangeable",
         "and can be told apart from PART-CHART.pdf.",
         "",
         "PART LIBRARY (one house)",
         "-" * 70,
         f"{'ID':>4}  {'width':>8}  {'height':>8}  {'entities':>8}  {'engraved':>8}",
         ]
for pi, r in enumerate(records):
    tag = (f"{r['label'][2]:.1f} mm" + (" rot" if r['label'][3] else "")) \
        if r['label'] else "no room"
    lines.append(f"{pi:4d}  {r['w']:8.2f}  {r['h']:8.2f}  {len(r['idx']):8d}  {tag:>9}")

lines += ["", "SHEET CONTENTS", "-" * 70]
for si, b in enumerate(sheets, 1):
    ids = collections.Counter(pi for pi, _, _, _, _ in placed[b])
    rot = sum(1 for *_, r in placed[b] if r)
    lines.append(f"\nSheet {si:02d}  ({len(placed[b])} parts, {rot} rotated 90 deg, "
                 f"{sheet_report[si-1][2]:.1f}% of sheet area)")
    for pi in sorted(ids):
        r = records[pi]
        lines.append(f"    part {pi:3d} x{ids[pi]:3d}   {r['w']:7.2f} x {r['h']:7.2f} mm")

if strays:
    hull = (min(r['ox'] for r in records), min(r['oy'] for r in records),
            max(r['ox'] + r['w'] for r in records),
            max(r['oy'] + r['h'] for r in records))
    lines += ["", "EXCLUDED CIRCLES - NOT PLACED ON ANY PART IN THE SOURCE DXF",
              "-" * 70,
              f"All real parts occupy X {hull[0]:.0f}..{hull[2]:.0f}, "
              f"Y {hull[1]:.0f}..{hull[3]:.0f} mm.",
              "These 6 circles sit at negative X, well outside every part, so they",
              "cannot be cable holes as exported. Re-export with them positioned on",
              "the panels, or say which part and where, and they can be added.",
              ""]
    for r in strays:
        dx = hull[0] - (r['ox'] + r['w'] / 2)
        lines.append(f"    dia {r['w']:6.2f} mm at ({r['ox'] + r['w']/2:9.2f},"
                     f"{r['oy'] + r['h']/2:8.2f})   {dx:.0f} mm left of all parts")

if labelmod.GAPS:
    worst = max(d for _, d in labelmod.GAPS)
    lines += ["", "OPEN CONTOURS IN THE SOURCE", "-" * 70,
              f"{len(labelmod.GAPS)} outline gaps found, largest {worst:.3f} mm.",
              "Bridged for analysis only - the cut geometry is passed through",
              "untouched. Most laser software cuts open paths fine, but if yours",
              "needs closed contours, weld with a 0.1 mm tolerance on import."]

open(os.path.join(args.outdir, 'CUT-PLAN.txt'), 'w').write("\n".join(lines) + "\n")
print(f"manifest -> {args.outdir}/CUT-PLAN.txt")
