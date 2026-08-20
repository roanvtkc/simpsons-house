# Laser-cut enclosure

Cut files for the physical Simpsons House model that the Raspberry Pi hardware
goes into.

## Available layouts

| Folder | Bed/stock size | Houses | Sheets | Average utilisation |
|---|---:|---:|---:|---:|
| `sheets-450x450-two-houses/` | 450 × 450 mm | 2 | 3 | 83.6% |
| `sheets-600x450/` | 600 × 450 mm | 10 | 11 | 85.5% |

The two-house layout uses the theoretical minimum of three 450 × 450 sheets:
the combined part bounding-box area will not fit on two sheets.

## What to send to the laser

For two houses on the 450 × 450 mm RedSail, send
`sheets-450x450-two-houses/sheet-01.dxf` … `sheet-03.dxf`. The files are in
millimetres.

For the original ten-house run, use `sheets-600x450/sheet-01.dxf` …
`sheet-11.dxf`.

Each file has three layers:

| Layer | What to do with it |
|---|---|
| `CUT` | Cut this. Part outlines only. |
| `ENGRAVE` | Part numbers, single-stroke. Run as a light score, or switch off. |
| `SHEET` | Reference rectangle matching the selected sheet size. **Not for cutting** — switch off or delete. |

**46 of 52 parts carry a number.** Each number sits on material only, at least
0.35 mm clear of every cut and score line, turned 90° where a narrow frame band
is the only place it fits. The six that are blank (31, 32, 40–43) are window
inserts whose bars are 2.5 mm wide — too narrow for a readable number. Each
belongs to a set of identical parts, so they are interchangeable; identify them
from `PART-CHART.pdf`.

## Reference

| File | Contents |
|---|---|
| `sheets-*/CUT-PLAN.txt` | Part library with sizes, and what sits on each sheet for that layout |
| `PART-CHART.pdf` | Every part drawn and numbered — use it to identify cut pieces |
| `ASSEMBLY-MAPPING.md` | Proposed mapping from engraved numbers to the assembly-instruction step numbers, graded by confidence |
| `sheets-*/nest-preview.png` | All sheets in that layout at a glance |
| `source/` | The original Shapr3D DXF export |

## Two-house 450 × 450 results

- 52 parts per house, 104 parts across 3 sheets
- 83.6% average sheet utilisation: 88.8%, 87.0%, and 75.0%
- 3 mm between part bounding boxes and a 5 mm border
- All 4,106 cut entities verified present; no part overlaps; every part inside the margin
- All 1,292 engrave strokes verified on material and at least 0.35 mm from a cut line

## Ten-house 600 × 450 results

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
python nest.py --copies 2 --sheet-w 450 --sheet-h 450 --outdir ../sheets-450x450-two-houses
python chart.py --out ../PART-CHART.svg
```

`nest.py` reads `../source/Simpsons House with precuts.dxf`; override with
`SIMPSONS_DXF=/path/to/other.dxf`.

Useful flags: `--copies N` (default 10), `--gap`, `--margin`, `--no-rotate`,
`--no-engrave`, `--keep-strays` (include the 6 stray circles).

| Script | Role |
|---|---|
| `parts.py` | Reads the DXF, groups loose lines into parts by endpoint connectivity, absorbs holes |
| `labels.py` | Builds each part's solid region and finds where a number fits |
| `strokefont.py` | Single-stroke digits |
| `verify_labels.py` | Independent check that a number is on material — ray casting against the raw cut segments |
| `nest.py` | Packs parts onto sheets, verifies, writes DXFs and the cut plan |
| `check_sheets.py` | End-to-end check of the written DXFs (`python check_sheets.py ../sheets-450x450-two-houses`) |
| `chart.py` | Renders the part identification chart |
| `shapes.py` | Reports which parts are duplicates |

The source DXF is 2,053 loose `LINE` entities rather than closed polylines, so
part identity is reconstructed from endpoint connectivity rather than read
directly. `nest.py` self-checks on every run: no part overlaps, everything
inside the margin, every engraved number lands on material, and the entity count
round-trips through the written files.

Engrave placement is checked **twice, by two independent routes**. `labels.py`
decides where a number goes from the part's solid region; `verify_labels.py`
then re-tests it by ray casting against the raw cut segments, never touching
that solid. This matters: an earlier version checked the text against the same
solid that positioned it, so when the solid was wrong the numbers landed in
window openings and the check still passed. `check_sheets.py` closes the loop by
re-deriving the material from the finished DXFs, which is the only check that
can catch a bad transform on a rotated copy.
