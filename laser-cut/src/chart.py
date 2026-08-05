"""Part identification chart: every part drawn to a common scale with its ID.

Use it to map the engraved numbers onto the numbered steps in the assembly PDF.
"""
import argparse, math, os
from parts import load_components, merge_nested, bbox_of

AP = argparse.ArgumentParser()
AP.add_argument('--out', default='PART-CHART.svg')
AP.add_argument('--cols', type=int, default=6)
args = AP.parse_args()

doc, ents, comps = load_components()
parts = merge_nested(ents, comps)

recs = []
for c in parts:
    if len(c) == 1 and ents[c[0]].dxftype() == 'CIRCLE':
        continue
    x0, y0, x1, y1 = bbox_of(ents, c)
    recs.append(dict(idx=c, w=x1 - x0, h=y1 - y0, ox=x0, oy=y0))
recs.sort(key=lambda r: -(r['w'] * r['h']))

COLS = args.cols
ROWS = math.ceil(len(recs) / COLS)
CELL_W, CELL_H = 190, 175      # drawing area per cell
HEAD = 26                      # header strip inside each cell
PAD = 14

# each part is zoomed to fill its own cell -- shapes stay legible for the tiny
# parts. Sizes are printed because the drawings are NOT to a common scale.
def scale_for(r):
    return min((CELL_W - PAD - 2 * PAD) / r['w'],
               (CELL_H - PAD - HEAD - PAD) / r['h'])

W = COLS * CELL_W + PAD
H = ROWS * CELL_H + PAD + 54

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
       f'width="{W*2}" height="{H*2}" font-family="Helvetica,Arial,sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       f'<text x="{PAD}" y="26" font-size="20" font-weight="bold">'
       f'Simpsons House &#8212; part identification chart</text>',
       f'<text x="{PAD}" y="44" font-size="11" fill="#555">'
       f'{len(recs)} parts. The number shown is engraved on the part. '
       f'Sizes are the bounding box in mm &#8212; each part is zoomed to fill its '
       f'box, so the drawings are not to a common scale.</text>']

for i, r in enumerate(recs):
    cx = PAD + (i % COLS) * CELL_W
    cy = 54 + (i // COLS) * CELL_H
    out.append(f'<g transform="translate({cx},{cy})">')
    out.append(f'<rect width="{CELL_W-PAD}" height="{CELL_H-PAD}" fill="#fcfcfc" '
               f'stroke="#ddd" rx="4"/>')
    out.append(f'<text x="8" y="18" font-size="17" font-weight="bold">{i:02d}</text>')
    out.append(f'<text x="{CELL_W-PAD-8}" y="18" font-size="10" fill="#666" '
               f'text-anchor="end">{r["w"]:.0f} &#215; {r["h"]:.0f} mm</text>')
    # centre the part in the drawing area below the header
    SCALE = scale_for(r)
    dw, dh = r['w'] * SCALE, r['h'] * SCALE
    ox = (CELL_W - PAD - dw) / 2
    oy = HEAD + (CELL_H - PAD - HEAD - dh) / 2

    def xf(p):
        return (ox + (p[0] - r['ox']) * SCALE, oy + dh - (p[1] - r['oy']) * SCALE)

    out.append('<g stroke="#1a1a1a" fill="none" stroke-width="0.6">')
    for j in r['idx']:
        e = ents[j]
        if e.dxftype() == 'LINE':
            a, b = xf(e.dxf.start), xf(e.dxf.end)
            out.append(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" '
                       f'x2="{b[0]:.2f}" y2="{b[1]:.2f}"/>')
        else:
            c = xf(e.dxf.center)
            out.append(f'<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" '
                       f'r="{e.dxf.radius*SCALE:.2f}"/>')
    out.append('</g></g>')

out.append('</svg>')
open(args.out, 'w').write("\n".join(out))
print(f"wrote {args.out}  ({len(recs)} parts, {COLS}x{ROWS} grid)")
