# Proposed mapping: engraved part number → assembly-step callout

Engraved numbers are geometry IDs (`00`–`51`, assigned largest-first) shown in
`PART-CHART.pdf`. Callouts `01`–`55` are the step numbers in
`Simpsons_House_Assemble.pdf`.

The two sets do **not** line up one-to-one:

| | count |
|---|---|
| Distinct parts cut per house | 52 |
| Distinct *shapes* (after removing duplicates) | 40 |
| Assembly callouts | 55 |

The gap is because the instructions number each piece **as it is fitted**, so an
identical piece that goes in four times gets four callouts, and a few callouts
point at a sub-assembly rather than a new part.

Confidence is graded. Read the "why" column before trusting a row.

---

## Tier A — confident

Matched on a distinctive feature or on an exact dimension pair.

| Callout | Part | Why |
|---|---|---|
| 01 | **06** (173.1 × 90.1) | Feature-for-feature match in the p2 drawing: two rectangular window slots, two arched bay recesses, central arch notch. |
| 04, 05, 06, 07 | **22, 23, 24, 25** (23.3 × 42.0) | Four bay-window fins, two per bay. Exactly four callouts and exactly four geometrically identical parts — interchangeable, so any order works. |
| 13 | **51** (13.2 × 15.1) | The cross/plus-shaped key that slots into the gable wall. Only cruciform part in the set. |
| 22, 23 | **26, 27** (39.0 × 20.9) | The two upper-storey window frames. Identical pair, and the only 39 × 21 rectangular frames. |
| 44 | **00** (313.2 × 197.7) | The base plate — the driveway/path notch in the drawing matches part 00's outline exactly. Largest part in the set. |
| 53, 55 | **05** (86.8 × 183.4) and **07** (183.4 × 83.0) | The two main roof slopes. Both share the 183.36 mm ridge edge; nothing else in the set does. Which is which depends on ridge overlap — check the tab positions. |

## Tier B — probable

Shape and size fit, but I could not confirm every feature through the 3D views.

| Callout | Part | Why |
|---|---|---|
| 08 | **29** (22.1 × 35.7) | The arched interior door. Size and proportion fit; the drawing shows a knob hole I could not resolve on the flat part. |
| 09 | **34** (13.5 × 38.3) | The door linkage arm — has a pivot hole at one end and a hook at the other, matching the arm in p3. |
| 15, 16 | **17, 18** (24.4 × 87.1) | The two tall corner posts. Only near-identical tall strips in the set (areas 1105 / 1097 mm², so they are mirrored, not identical). |
| 24, 25, 27, 28 | **40, 41, 42, 43** (22.9 × 13.3) | Bay-window panes, two per bay. Four identical parts, four callouts. |
| 32 | **36** (24.4 × 20.1) | Chimney cap — a small rectangular ring, matching the chimney top in p5. |
| 12, 20 | **02** (124.4 × 157.7) and **04** (101.9 × 157.7) | The two gable end walls. Both share the 157.72 mm height; nothing else does. |

## Tier C — unresolved

I could not distinguish these reliably from the drawings. Sizes and likely roles
are given so you can settle them against physical parts in a minute or two.

| Parts | Likely role | Note |
|---|---|---|
| **37, 38** (15.0 × 25.9) | Bay-window side walls | Identical pair — order does not matter. |
| **47, 48, 49, 50** (14.7 × 14.6) | Bay-window roof triangles | Four identical parts. |
| **31, 32** (23.3 × 22.9) | Window inserts, 3 horizontal bars | Identical pair. |
| **09** (107.0 × 69.2), **10** (107.0 × 57.3) | Roof or garage panels | Share the 107.01 mm edge — a matched pair. |
| **12** (63.5 × 60.9), **13** (63.5 × 57.6) | Garage roof slopes | Share the 63.47 mm edge — a matched pair. |
| **15** (32.6 × 103.1) | Garage door | Slatted panel — distinctive, but its callout is not shown in the views I could read. |
| **01** (273.2 × 91.1), **03** (136.5 × 124.4) | Long front wall / internal partition | Both large and distinctive; I could not pin which callout. |
| **11** (103.1 × 57.0) | Bay floor + linkage mount | Carries a pivot hole; part of the door mechanism. |
| Remainder | Trim, brackets, steps | Small pieces, several near-identical. |

---

## The reliable way to finish this

Roughly half the set above is solid and half is not, and guessing the rest from
3D line drawings is not going to get more accurate.

Since the numbers are already engraved and `PART-CHART.pdf` shows every part:

1. Cut **one** house (sheets 1–11 produce 10, but one of each is enough to start).
2. Lay the parts on the chart to confirm the engraved IDs.
3. Walk the assembly PDF and write the callout beside each part.

That produces a verified table in about ten minutes. Send it back and the
engraving can be regenerated to carry the assembly numbers instead of the
geometry IDs — it is a one-line change to the label text in `nest.py`.
