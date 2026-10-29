"""Terrain that doesn't look like tiles: mountains and streets painted from big seamless textures
(sprites\\Textures\\<Name>.png, plain pictures), so a range or a street runs on without repeating every 32 px (the
client paints each cell with its part of the texture, as the forest canopy does: build_forest.py).

  * Mountains: a range seen from above - ridges and gullies lit from the top left, scree low down, snow on the heights.
    Range_Rock (blue-grey: Peak..., Mountain...), Range_Snow (Snow_Peak...), Range_Cinder (black, lava glowing in
    the cracks: Cinder_Peak...). Their Blend is over grass and forest, so a range's edge breaks up raggedly.
  * Streets: uneven stones, never a grid - cobbles, setts, flags of all sizes, bricks in a wandering bond, gravel.

Each tile's own picture becomes one cell of its texture (for the editor and the minimap). Run it after
build_world_art.py (which draws the old tiles). Safe to run again.

  python -I "dev\\migrate\\build_terrain.py"
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprite_kit as K                       # noqa: E402
import story_kit as SK                       # noqa: E402
from common import write_sprite              # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.join(ROOT, "sprites", "Textures")


# ================================================================== noise on a torus (it tiles without a seam)
def value_noise(rng, size, cells):
    """Smooth noise, 0..1, size x size, from a cells x cells lattice that wraps."""
    lat = np.array([[rng.random() for _ in range(cells)] for _ in range(cells)], dtype=np.float64)
    t = np.arange(size) * cells / size
    i0 = np.floor(t).astype(int) % cells
    i1 = (i0 + 1) % cells
    f = t - np.floor(t)
    f = f * f * (3 - 2 * f)
    rows = lat[i0][:, i0] * (1 - f)[None, :] + lat[i0][:, i1] * f[None, :]
    rows1 = lat[i1][:, i0] * (1 - f)[None, :] + lat[i1][:, i1] * f[None, :]
    return rows * (1 - f)[:, None] + rows1 * f[:, None]


def fractal(rng, size, octaves, ridged=False, cells=4, gain=0.5):
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for _ in range(octaves):
        n = value_noise(rng, size, cells)
        if ridged:
            n = 1 - np.abs(2 * n - 1)
            n = n * n
        out += n * amp
        total += amp
        amp *= gain
        cells *= 2
    return out / total


def shade(h, contrast):
    """Hillshade, 0..1, lit from the top left: slopes facing the light bright, the far sides in shadow."""
    g = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) + (np.roll(h, -1, 0) - np.roll(h, 1, 0))
    return np.clip(0.55 - g / (3 * g.std() + 1e-9) * contrast, 0.0, 1.0)


def ramp(v, stops):
    """Colours along stops [(at, (r, g, b))...] for each value of v."""
    ats = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float64)
    out = np.zeros(v.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(v, ats, cols[:, c])
    return out


# ================================================================== mountains
RANGES = {   # texture: (tiles, (unused), (unused), seed)
    "Range_Rock": (("Peak", "Mountain"), [(0.0, (74, 76, 70)), (0.3, (92, 96, 100)), (0.65, (118, 122, 132)),
                                          (1.0, (150, 154, 164))], 0.86, 3),
    "Range_Snow": (("Snow_Peak",), [(0.0, (84, 90, 104)), (0.4, (116, 122, 136)), (1.0, (150, 156, 170))], 0.55, 5),
    "Range_Cinder": (("Cinder_Peak",), [(0.0, (34, 28, 28)), (0.5, (52, 46, 44)), (1.0, (78, 70, 66))], 9.0, 7),
}
RANGE_SIZE = 256


PEAKS = {   # texture: (lit face, shadowed face, the rock between, snow on how many in 10, lava)
    "Range_Rock": ((150, 156, 170), (84, 90, 108), (64, 68, 80), 4, False),
    "Range_Snow": ((168, 174, 190), (96, 104, 124), (78, 84, 100), 10, False),
    "Range_Cinder": ((84, 74, 70), (40, 34, 34), (28, 24, 24), 0, True),
}


def jagged(rng, a, b, n, amp):
    """Points from a to b, each nudged sideways a little: a rough mountainside."""
    (x0, y0), (x1, y1) = a, b
    out = [a]
    for i in range(1, n):
        t = i / n
        nx, ny = -(y1 - y0), x1 - x0
        ln = max(1e-6, (nx * nx + ny * ny) ** 0.5)
        o = rng.uniform(-amp, amp)
        out.append((x0 + (x1 - x0) * t + nx / ln * o, y0 + (y1 - y0) * t + ny / ln * o))
    out.append(b)
    return out


def range_texture(name):
    """Peaks of every size scattered over the texture (wrapping round), overlapping, the nearer in front: each lit
    on its left face, in shadow on its right, a ridge down the middle, gullies, and snow on the high ones."""
    import pygame
    lit, dark, between, snowy, lava = PEAKS[name]
    rng = random.Random(name)
    size = RANGE_SIZE
    s = pygame.Surface((size, size))
    s.fill(between)
    for _ in range(size * size // 30):                           # (scree between the peaks)
        c = tuple(max(0, min(255, v + rng.randint(-12, 12))) for v in between)
        s.set_at((rng.randrange(size), rng.randrange(size)), c)
    shapes = []                                                   # (each peak's shapes, worked out once)
    for _ in range(104):
        w = rng.choice((28, 32, 36, 40, 46, 52, 60, 70))
        h = w * rng.uniform(0.7, 0.95)
        cx, by = rng.uniform(0, size), rng.uniform(0, size)
        tone = rng.uniform(-10, 10)
        L = tuple(max(0, min(255, v + tone)) for v in lit)
        D = tuple(max(0, min(255, v + tone * 0.6)) for v in dark)
        apex = (cx + rng.uniform(-w * 0.1, w * 0.1), by - h)
        foot = (cx + rng.uniform(-w * 0.05, w * 0.12), by)
        left = jagged(rng, (cx - w / 2, by), apex, 6, w * 0.04)
        right = jagged(rng, apex, (cx + w / 2, by), 6, w * 0.04)
        ridge = jagged(rng, apex, foot, 5, w * 0.03)
        parts = [(L, left + ridge[1:]), (D, right + ridge[::-1][1:-1])]
        lines = []
        for k in range(3):                                         # (gullies down each face)
            t = rng.uniform(0.3, 0.8)
            for side, col in ((-1, tuple(v * 0.84 for v in L)), (1, tuple(v * 0.78 for v in D))):
                x0 = apex[0] + side * w * 0.5 * t * 0.6
                y0 = apex[1] + h * t * 0.6
                lines.append((col, jagged(rng, (x0, y0), (x0 + side * w * 0.07, by - 2), 3, 1.5)))
        if snowy and w >= 40 and rng.randrange(10) < snowy:       # (a snowcap on the high ones)
            cap = rng.uniform(0.28, 0.4)
            yl = apex[1] + h * cap
            lx = apex[0] + (cx - w / 2 - apex[0]) * cap
            rx = apex[0] + (cx + w / 2 - apex[0]) * cap
            mid = (apex[0] + (foot[0] - apex[0]) * cap, yl + 3)
            parts.append(((232, 236, 244), [apex] + jagged(rng, (lx, yl), mid, 3, 2)))
            parts.append(((172, 182, 204), [apex] + jagged(rng, mid, (rx, yl), 3, 2)))
        if lava and rng.random() < 0.6:                           # (lava glowing down a crack)
            lines.append(((240, 110, 30), jagged(rng, (apex[0] + 2, apex[1] + h * 0.25), (foot[0] + 3, by - 1), 6, 2)))
        lines.append((tuple(v * 0.6 for v in D), right))           # (the shadowed edge)
        shapes.append((by, parts, lines))
    shapes.sort(key=lambda p: p[0])
    for _, parts, lines in shapes:
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                for col, pts in parts:
                    pygame.draw.polygon(s, col, [(x + ox, y + oy) for x, y in pts])
                for col, pts in lines:
                    pygame.draw.lines(s, col, False, [(x + ox, y + oy) for x, y in pts], 1)
    return pygame.surfarray.array3d(s).transpose(1, 0, 2)


# ================================================================== streets: stones, packed (on a torus)
STREET_SIZE = 128


def stones_voronoi(rng, size, step, palette, gap, jitter=0.42):
    """Cobbles: rounded stones on a jittered grid, each its own shade, mortar between, lit from the top left."""
    n = size // step
    pts = []
    for j in range(n):
        for i in range(n):
            pts.append(((i + 0.5 + rng.uniform(-jitter, jitter)) * step, (j + 0.5 + rng.uniform(-jitter, jitter)) * step,
                        rng.choice(palette), rng.uniform(-10, 10)))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float64)
    d1 = np.full((size, size), 1e9)
    d2 = np.full((size, size), 1e9)
    own = np.zeros((size, size), dtype=int)
    for k, (px, py, _, _) in enumerate(pts):
        dx = (xs - px + size / 2) % size - size / 2
        dy = (ys - py + size / 2) % size - size / 2
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        own = np.where(closer, k, own)
        d1 = np.where(closer, d, d1)
    col = np.zeros((size, size, 3))
    for k, (px, py, c, v) in enumerate(pts):
        sel = own == k
        dx = (xs - px + size / 2) % size - size / 2
        dy = (ys - py + size / 2) % size - size / 2
        lit = np.clip(-(dx + dy) / (step * 0.9), -1, 1)
        col[sel] = (np.array(c) + v + lit[sel][:, None] * 22)
    edge = d2 - d1
    mortar = np.clip((1.6 - edge) / 1.0, 0, 1)
    col = col * (1 - mortar[..., None]) + np.array(gap) * mortar[..., None]
    col += np.array([[rng.uniform(-5, 5) for _ in range(size)] for _ in range(size)])[..., None]
    return np.clip(col, 0, 255).astype(np.uint8)


def laid_flags(rng, size, step, palette, gap, moss=None, jitter=0.34, stretch=1.25, pits=0.0, wear=14):
    """Flags laid by hand: irregular slabs (a jittered grid, a little longer than wide), each its own shade and
    surface, edges worn round, the joints between them uneven - dark and earthy, a little moss in some - lit from
    the top left. Wraps round (a seamless texture)."""
    nx, ny = int(size / (step * stretch)), size // step
    sx, sy = size / nx, size / ny
    pts = []
    for j in range(ny):
        off = rng.uniform(0, 0.5) if j % 2 else 0
        for i in range(nx):
            pts.append(((i + 0.5 + off + rng.uniform(-jitter, jitter)) * sx, (j + 0.5 + rng.uniform(-jitter, jitter)) * sy,
                        np.array(rng.choice(palette), dtype=np.float64) + rng.uniform(-9, 9), rng.random()))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float64)
    d1 = np.full((size, size), 1e9)
    d2 = np.full((size, size), 1e9)
    own = np.zeros((size, size), dtype=int)
    for k, (px, py, _, _) in enumerate(pts):
        dx = (xs - px + size / 2) % size - size / 2
        dy = ((ys - py + size / 2) % size - size / 2) * (stretch * 0.9)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        own = np.where(closer, k, own)
        d1 = np.where(closer, d, d1)
    grain = fractal(rng, size, 4) - 0.5                       # (the stone's own surface: a fine mottle)
    blotch = fractal(rng, size, 2, cells=3) - 0.5
    col = np.zeros((size, size, 3))
    edge = d2 - d1
    for k, (px, py, c, v) in enumerate(pts):
        sel = own == k
        dx = (xs - px + size / 2) % size - size / 2
        dy = (ys - py + size / 2) % size - size / 2
        tilt = (rng.uniform(-1, 1), rng.uniform(-1, 1))           # (each slab sits a little off level)
        lit = np.clip(-(dx * (0.7 + 0.3 * tilt[0]) + dy * (0.7 + 0.3 * tilt[1])) / (step * 1.2), -1, 1)
        col[sel] = c + lit[sel][:, None] * 12 + grain[sel][:, None] * 26 + blotch[sel][:, None] * 18
    rim = np.clip((4.0 - edge) / 4.0, 0, 1)                       # (worn round toward the joint: darker, then lit)
    col = col * (1 - rim[..., None] * 0.22)
    joint_w = 1.5 + (fractal(rng, size, 3) - 0.5) * 1.6        # (joints uneven, wider and narrower)
    mortar = np.clip((joint_w - edge) / 1.0, 0, 1)
    mcol = np.array(gap, dtype=np.float64)[None, None, :] + (grain[..., None] * 20)
    if moss is not None:
        m = np.clip((fractal(rng, size, 3, cells=5) - 0.55) * 4, 0, 1)
        mcol = mcol * (1 - m[..., None]) + np.array(moss)[None, None, :] * m[..., None]
    col = col * (1 - mortar[..., None]) + mcol * mortar[..., None]
    if pits:                                                     # (weathering: little pits in soft stone)
        for _ in range(int(size * size * pits)):
            x, y = rng.randrange(size), rng.randrange(size)
            if mortar[y, x] < 0.1:
                col[y, x] *= 0.86
                col[(y + 1) % size, x] = col[(y + 1) % size, x] * 0.94 + 10
    col += np.array([[rng.uniform(-3, 3) for _ in range(size)] for _ in range(size)])[..., None]
    return np.clip(col, 0, 255).astype(np.uint8)


def rows_of_stones(rng, size, heights, widths, palette, gap, bevel=18, crack=0.0):
    """Setts, flags and bricks: rows of random heights, each cut into stones of random widths (wrapping round)."""
    col = np.zeros((size, size, 3))
    y = 0
    rows = []
    while y < size:
        h = rng.choice(heights)
        if size - y < min(heights) + h:
            h = size - y
        rows.append((y, h))
        y += h
    for y0, h in rows:
        x = rng.randrange(0, size)
        start = x
        while True:
            w = rng.choice(widths)
            if x + w - start >= size:
                w = start + size - x
            c = np.array(rng.choice(palette), dtype=np.float64) + rng.uniform(-8, 8)
            for yy in range(y0, y0 + h):
                for xx in range(x, x + w):
                    px = xx % size
                    edge_l, edge_t = xx - x, yy - y0
                    edge_r, edge_b = x + w - 1 - xx, y0 + h - 1 - yy
                    if min(edge_l, edge_t, edge_r, edge_b) == 0:
                        col[yy, px] = gap
                    else:
                        lit = (bevel if (edge_t == 1 or edge_l == 1) else -bevel * 0.8 if (edge_b == 1 or edge_r == 1)
                               else 0)
                        col[yy, px] = c + lit + rng.uniform(-4, 4)
            if crack and rng.random() < crack and w > 6 and h > 6:   # (a hairline crack across it)
                cx, cy = x + rng.randrange(2, w - 2), y0 + 1
                while cy < y0 + h - 1:
                    col[cy, cx % size] = c * 0.7
                    cy += 1
                    cx += rng.choice((-1, 0, 0, 1))
            x += w
            if x - start >= size:
                break
    return np.clip(col, 0, 255).astype(np.uint8)


def gravel_texture(rng, size, base, palette):
    col = np.zeros((size, size, 3)) + np.array(base)
    col += (fractal(rng, size, 3)[..., None] - 0.5) * 30
    for _ in range(size * size // 5):
        x, y = rng.randrange(size), rng.randrange(size)
        c = np.array(rng.choice(palette))
        col[y, x] = c
        if rng.random() < 0.3:
            col[y, (x + 1) % size] = c * 0.85
            col[(y + 1) % size, x] = c * 0.7
    return np.clip(col, 0, 255).astype(np.uint8)


STREETS = {   # tile: (texture, how it's drawn)
    "Cobble001": ("Street_Cobble", lambda r: stones_voronoi(r, STREET_SIZE, 8, [(132, 130, 126), (118, 116, 112),
                                                                                  (146, 142, 136), (124, 120, 112)],
                                                            (66, 62, 58))),
    "Basalt_Paving001": ("Street_Basalt", lambda r: stones_voronoi(r, STREET_SIZE, 8, [(52, 50, 52), (62, 58, 58),
                                                                                       (44, 42, 46)], (26, 22, 22))),
    "Red_Sandstone001": ("Street_Red_Sandstone", lambda r: rows_of_stones(
        r, STREET_SIZE, (6, 7, 8), (8, 9, 10, 12, 14), [(176, 104, 78), (164, 94, 70), (186, 116, 88), (170, 100, 80)],
        (104, 62, 48))),
    "Brick_Paving001": ("Street_Brick", lambda r: rows_of_stones(
        r, STREET_SIZE, (4, 4, 5), (8, 9, 10), [(150, 62, 46), (166, 74, 54), (132, 54, 40), (156, 84, 60)],
        (98, 82, 72), bevel=12)),
    "Marble_Paving001": ("Street_Marble", lambda r: rows_of_stones(
        r, STREET_SIZE, (12, 14, 16, 18), (12, 16, 18, 22, 26), [(232, 230, 224), (222, 220, 214), (240, 238, 232)],
        (176, 172, 166), bevel=10, crack=0.15)),
    "Mage_Flag001": ("Street_Mage", lambda r: rows_of_stones(
        r, STREET_SIZE, (10, 12, 14, 16), (12, 14, 18, 22), [(112, 124, 146), (100, 112, 134), (124, 136, 158)],
        (62, 68, 84), crack=0.1)),
    "Slate_Flag001": ("Street_Slate", lambda r: rows_of_stones(
        r, STREET_SIZE, (10, 12, 14, 16), (12, 14, 18, 22), [(74, 76, 84), (66, 68, 76), (84, 86, 94)], (38, 40, 46),
        crack=0.2)),
    "Flagstone001": ("Street_Flagstone", lambda r: laid_flags(                 # (grey flags, a little moss between)
        r, STREET_SIZE, 15, [(146, 142, 134), (132, 129, 122), (156, 152, 144), (138, 136, 132), (124, 122, 118)],
        (70, 66, 58), moss=(86, 102, 58))),
    "Sandstone_Paving001": ("Street_Sandstone", lambda r: laid_flags(          # (warm slabs, weathered soft)
        r, STREET_SIZE, 19, [(220, 194, 146), (208, 182, 134), (228, 204, 158), (214, 188, 138), (202, 172, 124)],
        (150, 124, 84), pits=0.04, stretch=1.35)),
    "Gravel001": ("Street_Gravel", lambda r: gravel_texture(r, STREET_SIZE, (146, 132, 108),
                                                            [(120, 108, 88), (170, 160, 140), (132, 126, 116),
                                                             (100, 90, 74)])),
}


# ================================================================== writing
def save_texture(name, arr):
    write_sprite(os.path.join(TEX, name + ".png"), [[tuple(int(v) for v in c) for c in r] for r in arr], plain=True)


def cell_of(arr, i):
    """The i'th 32 x 32 cell along the texture's top rows (a tile's own picture)."""
    n = arr.shape[1] // 32
    i %= n * n
    x, y = (i % n) * 32, (i // n) * 32
    return [[tuple(int(v) for v in arr[y + yy, x + xx]) for xx in range(32)] for yy in range(32)]


def mountain_tiles(prefixes):
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, "sprites", "Tiles"))):
        n = f[:-4]
        if not f.endswith(".png") or not n[-3:].isdigit():
            continue
        base = n[:-3]
        for p in prefixes:
            if base in (p, p + "_Big", p + "_Huge"):
                out.append(n)
    return out


def main():
    os.makedirs(TEX, exist_ok=True)
    for name, (prefixes, _, _, _) in RANGES.items():
        arr = range_texture(name)
        save_texture(name, arr)
        tiles = mountain_tiles(prefixes)
        for i, t in enumerate(tiles):
            K.save("Tiles", t, cell_of(arr, i * 3))
            SK.section(SK.TILES, t, [("Texture", name), ("Blend", "8"), ("Blend.Texture", tiles[0])])
        print("%s: %d tiles" % (name, len(tiles)))
    for tile, (name, draw) in STREETS.items():
        arr = draw(random.Random(name))
        save_texture(name, arr)
        K.save("Tiles", tile, cell_of(arr, 0))
        SK.section(SK.TILES, tile, [("Texture", name), ("Blend.Texture", tile)])
    print("Streets: %d textures" % len(STREETS))


if __name__ == "__main__":
    main()
