"""Rocks and stones for the countryside, on grass (build_scenery scatters them):
  * Rock002: a big grey boulder, mossy on top, in its own shadow (blocks, like Rock001)
  * Rock003: a cluster of three stones (a small obstacle)
  * Pebbles001-003: a scatter of pebbles in the grass (walk over them)
Drawn with numpy like the other tiles (house_tiles, interior_tiles); merged into cave_tiles.TILES."""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from farm_tiles import S, to_rows, smooth_noise  # noqa: E402

YS, XS = np.mgrid[0:S, 0:S]
GREYS = [(132, 128, 120), (118, 112, 104), (146, 138, 124)]
MOSS = [(78, 116, 52), (92, 132, 60)]


def grass():
    import house_tiles
    return np.array(house_tiles.tile_image("Grass001"), dtype=np.float32).copy()


def stone(img, rng, cx, cy, rx, ry, base, moss=0.0):
    """A rounded stone: shaded from the top left, speckled, outlined, a shadow on the ground below right, moss on
    its top if moss > 0."""
    sh = (((XS - cx - 1.5) / (rx + 0.5)) ** 2 + ((YS - cy - 2) / (ry * 0.7 + 0.5)) ** 2) <= 1
    img[sh] *= 0.62                                                  # its shadow on the grass
    d = ((XS - cx) / rx) ** 2 + ((YS - cy) / ry) ** 2
    body = d <= 1
    light = np.clip(1.25 - 0.35 * ((XS - cx) / rx + (YS - cy) / ry + 1), 0.6, 1.3)
    noise = 1 + 0.08 * np.array([[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)])
    col = np.array(base, dtype=np.float32)
    img[body] = (col * (light * noise)[..., None])[body]
    for _ in range(int(rx * ry / 6)):                                # cracks and pits
        x, y = int(cx + rng.uniform(-rx, rx) * 0.7), int(cy + rng.uniform(-ry, ry) * 0.7)
        if 0 <= x < S and 0 <= y < S and body[y, x]:
            img[y, x] *= 0.7
    if moss > 0:
        top = body & (YS < cy - ry * 0.25) & (np.array([[rng.random() for _ in range(S)] for _ in range(S)]) < moss)
        img[top] = np.array(rng.choice(MOSS), dtype=np.float32)
    edge = body & ~((((XS - cx) / (rx - 1)) ** 2 + ((YS - cy) / (ry - 1)) ** 2) <= 1)
    img[edge & (YS > cy)] *= 0.55                                    # the outline, darker underneath
    img[edge & (YS <= cy)] *= 0.8
    return img


def boulder():
    rng = random.Random(8101)
    img = grass()
    stone(img, rng, 16, 17, 11.5, 9.5, GREYS[0], moss=0.55)
    return to_rows(np.clip(img, 0, 255))


def cluster():
    rng = random.Random(8102)
    img = grass()
    for cx, cy, rx, ry, k in ((11, 19, 6.5, 5, 1), (21, 21, 5, 4, 2), (17, 13, 4.5, 3.6, 0)):
        stone(img, rng, cx, cy, rx, ry, GREYS[k], moss=0.25)
    return to_rows(np.clip(img, 0, 255))


def pebbles(n):
    rng = random.Random(8200 + n)
    img = grass()
    for _ in range(5 + n * 2):
        x, y = rng.randint(3, 28), rng.randint(3, 28)
        r = rng.choice((1.2, 1.6, 2.1))
        col = rng.choice(GREYS + [(150, 128, 100), (166, 158, 146)])
        stone(img, rng, x, y, r + 0.4, r, col)
    return to_rows(np.clip(img, 0, 255))


TILES = {"Rock002": boulder, "Rock003": cluster}
for _n in (1, 2, 3):
    TILES["Pebbles%03d" % _n] = (lambda n=_n: pebbles(n))
