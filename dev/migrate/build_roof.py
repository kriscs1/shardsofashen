"""Draws sprites\\Tiles\\Roof001.png: wooden shingles that tile seamlessly (rows of 8 px, staggered by half a shingle).
Usage: python -I build_roof.py [output.png]   (default: the game's Roof001.png)
The tile is 32 x 64: the top half is the mask (all black = fully drawn), the bottom half is the image."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import write_sprite

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'sprites', 'Tiles', 'Roof001.png')

T = 32                 # tile size
ROW = 8                # shingle row height (4 rows per tile)
SW = 16                # shingle width (2 per row, every other row shifted by half a shingle)
HANG = 3               # how far each shingle's rounded bottom hangs over the row below
TOP = (124, 82, 56)    # shingle colour at its top ...
BOTTOM = (84, 52, 34)  # ... darkening towards its rounded bottom edge
EDGE = (44, 27, 18)    # outline of the rounded bottom and the gaps between shingles
SHADOW = 26            # how much darker a shingle is just under the row above it

rnd = random.Random(11)
# one tint per shingle position; the tile repeats, so this small table keeps it seamless
tint = [[rnd.randint(-10, 10) for _ in range(T // SW)] for _ in range(T // ROW)]


def clamp(v):
    return max(0, min(255, int(v)))


def mix(a, b, t):
    return tuple(clamp(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, d):
    return tuple(clamp(v + d) for v in c)


img = [[EDGE] * T for _ in range(T)]
# Each row overlaps the top of the row below it (like a real roof seen from above), and the tile wraps, so the
# bottom row's overhang must lie on top of row 0 of the next tile. Paint order: row 0, then rows 3, 2, 1 (each over the
# one below), then just the overhang of row 0 (over row 1).
ROWS = T // ROW


def paint(row, overhang_only):
    shift = (SW // 2) if row % 2 else 0
    for col in range(T // SW):
        left = col * SW - shift
        for rx in range(SW):
            u = (rx + 0.5 - SW / 2) / (SW / 2)          # -1 .. 1 across the shingle
            bottom = (ROW - 1) + HANG * (1 - u * u)      # rounded bottom: lowest in the middle
            for ry in range(int(bottom) + 1):
                if overhang_only and ry < ROW:
                    continue
                y = (row * ROW + ry) % T
                x = (left + rx) % T
                c = mix(TOP, BOTTOM, ry / bottom)
                c = shade(c, tint[row][col])
                if ry <= 2:
                    c = shade(c, -SHADOW + ry * 8)       # shadow cast by the row above
                if ry >= bottom - 1:
                    c = EDGE                             # outline of the rounded bottom
                elif rx == 0 or rx == SW - 1:
                    c = EDGE if ry < ROW - 2 else shade(c, -18)   # gaps between shingles
                elif rx == 1:
                    c = shade(c, 12)                     # left side catches the light
                elif rx == SW - 2:
                    c = shade(c, -10)
                img[y][x] = c


paint(0, False)
for row in range(ROWS - 1, 0, -1):
    paint(row, False)
paint(0, True)

px = [[(0, 0, 0)] * T for _ in range(T)] + img
write_sprite(os.path.normpath(OUT), px)
print('wrote', os.path.normpath(OUT))
