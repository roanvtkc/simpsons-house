"""Minimal single-stroke digit font for laser engraving.

Glyphs are polylines on a 0..6 (x) by 0..10 (y) grid. Single-stroke means the
laser traces each line once -- no fill, no outline doubling.
"""

GLYPHS = {
    '0': [[(1, 0), (5, 0), (6, 2), (6, 8), (5, 10), (1, 10), (0, 8), (0, 2), (1, 0)]],
    '1': [[(1, 8), (3, 10), (3, 0)], [(1, 0), (5, 0)]],
    '2': [[(0, 8), (1, 10), (5, 10), (6, 8), (6, 6.6), (0, 0), (6, 0)]],
    '3': [[(0, 9), (1, 10), (5, 10), (6, 9), (6, 6.6), (5, 5.6), (2, 5.6)],
          [(5, 5.6), (6, 4.6), (6, 1), (5, 0), (1, 0), (0, 1)]],
    '4': [[(4.5, 0), (4.5, 10), (0, 3.5), (6, 3.5)]],
    '5': [[(6, 10), (1, 10), (1, 6), (5, 6), (6, 5), (6, 1), (5, 0), (1, 0), (0, 1)]],
    '6': [[(5, 10), (2, 10), (0, 7), (0, 2), (1, 0), (5, 0), (6, 2), (6, 3.5),
           (5, 5), (1, 5), (0, 3.5)]],
    '7': [[(0, 10), (6, 10), (2, 0)]],
    '8': [[(2, 5), (1, 5.8), (1, 9), (2, 10), (4, 10), (5, 9), (5, 5.8), (4, 5),
           (2, 5), (0.7, 4), (0.7, 1), (2, 0), (4, 0), (5.3, 1), (5.3, 4), (4, 5)]],
    '9': [[(1, 0), (4, 0), (6, 3), (6, 8), (5, 10), (1, 10), (0, 8), (0, 6.5),
           (1, 5), (5, 5), (6, 6.5)]],
}

GW, GH, GAP = 6.0, 10.0, 2.0   # glyph width, height, inter-glyph gap


def text_width(s):
    return len(s) * GW + max(0, len(s) - 1) * GAP


def strokes(s, height, cx, cy):
    """Polylines for string `s`, cap height `height`, centred on (cx, cy)."""
    k = height / GH
    w = text_width(s) * k
    x0 = cx - w / 2
    y0 = cy - height / 2
    out = []
    for i, ch in enumerate(s):
        ox = x0 + i * (GW + GAP) * k
        for poly in GLYPHS[ch]:
            out.append([(ox + px * k, y0 + py * k) for px, py in poly])
    return out
