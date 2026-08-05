# Laser-cut enclosure

Cut files for the physical Simpsons House model that the Raspberry Pi hardware
goes into. Nested for a **600 × 450 mm** bed, **10 houses per run**.

## What to send to the laser

`sheets-600x450/sheet-01.dxf` … `sheet-11.dxf` — eleven sheets, in millimetres.

Each file has three layers:

| Layer | What to do with it |
|---|---|
| `CUT` | Cut this. Part outlines only. |
| `ENGRAVE` | Part numbers, single-stroke. Run as a light score, or switch off. |
| `SHEET` | 600 × 450 reference rectangle. **Not for cutting** — switch off or delete. |

## Reference

| File | Contents |
|---|---|
| `CUT-PLAN.txt` | Part library with sizes, and what sits on each sheet |
| `PART-CHART.pdf` | Every part drawn and numbered — use it to identify cut pieces |
| `ASSEMBLY-MAPPING.md` | Proposed mapping from engraved numbers to the assembly-instruction step numbers, graded by confidence |
| `nest-preview.png` | All eleven sheets at a glance |
| `source/` | The original Shapr3D DXF export |

## Results

- 52 parts per house (40 distinct shapes), 520 parts over 11 sheets
- 85.5% average sheet utilisation; worst sheet 79.8%
- 3 mm between parts, 5 mm border
- All 20,530 cut entities verified present; no part overlaps; every part inside the margin

## Known issues with the source export

Both are recorded in `CUT-PLAN.txt` and neither is corrected in the cut files —
the geometry is passed through untouched.

1. **The 6 circles are not on any part.** They sit at negative X, between 90 mm
   and 629 mm clear of the nearest part, so they cannot function as the cable
   holes they were intended to be. They are excluded from the nest. Fix by
   re-exporting with them positioned on the panels.
2. **54 open-contour gaps**, largest 0.090 mm. Most laser software cuts open
   paths fine; if yours needs closed contours, weld on import with a 0.1 mm
   tolerance.

Note also that the 3 mm spacing is *between parts*, not kerf compensation — cut
paths are the original geometry, so parts finish about one kerf undersize. Check
a test joint before committing a full run of material.

## Regenerating

```bash
cd laser-cut/src
pip install -r requirements.txt
python nest.py --sheet-w 600 --sheet-h 450 --outdir ../sheets-600x450
python chart.py --out ../PART-CHART.svg
```

`nest.py` reads `../source/Simpsons House with precuts.dxf`; override with
`SIMPSONS_DXF=/path/to/other.dxf`.

Useful flags: `--copies N` (default 10), `--gap`, `--margin`, `--no-rotate`,
`--no-engrave`, `--keep-strays` (include the 6 stray circles).

| Script | Role |
|---|---|
| `parts.py` | Reads the DXF, groups loose lines into parts by endpoint connectivity, absorbs holes |
| `labels.py` | Builds each part's solid region, finds the point furthest from any edge for the number |
| `strokefont.py` | Single-stroke digits |
| `nest.py` | Packs parts onto sheets, verifies, writes DXFs and the cut plan |
| `chart.py` | Renders the part identification chart |
| `shapes.py` | Reports which parts are duplicates |

The source DXF is 2,053 loose `LINE` entities rather than closed polylines, so
part identity is reconstructed from endpoint connectivity rather than read
directly. `nest.py` self-checks on every run: no part overlaps, everything
inside the margin, every engraved number lands on material, and the entity count
round-trips through the written files.
