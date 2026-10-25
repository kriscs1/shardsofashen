"""Generate the extra tile sprites the expanded world needs (sprites\\Tiles\\*.png).

Run:  python -I "dev\\migrate\\build_tiles.py" [--preview]   (--preview also writes dev\\Renders\\Tiles preview.png and Tiles 4x4.png)
Deterministic (fixed seeds) and re-runnable; it only (re)writes the tiles listed in NEW_TILES.
Format, as for every LB sprite here: 24-bit BMP, 32 wide x 64 high, top half = mask
(black = drawn, white = transparent), bottom half = image. All of these tiles are opaque.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p, read_bmp, write_sprite

S = 32


def clamp(v):
    return max(0, min(255, int(round(v))))


def noise_field(rng, amp, blur=1):
    """Tileable smooth noise in -amp..amp (box blur on a torus)."""
    f = [[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)]
    for _ in range(blur):
        g = [[0.0] * S for _ in range(S)]
        for y in range(S):
            for x in range(S):
                t = 0.0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        t += f[(y + dy) % S][(x + dx) % S]
                g[y][x] = t / 9.0
        f = g
    m = max(abs(v) for r in f for v in r) or 1
    return [[v / m * amp for v in r] for r in f]


def textured(base, amp, seed, blur=1, fine=3):
    rng = random.Random(seed)
    n = noise_field(rng, amp, blur)
    img = []
    for y in range(S):
        row = []
        for x in range(S):
            d = n[y][x] + rng.uniform(-fine, fine)
            row.append(tuple(clamp(c + d) for c in base))
        img.append(row)
    return img, rng


def speck(img, rng, colours, count, size=1):
    for _ in range(count):
        x, y = rng.randrange(S), rng.randrange(S)
        c = rng.choice(colours)
        for dy in range(size):
            for dx in range(size):
                img[(y + dy) % S][(x + dx) % S] = c


def pebble(img, x0, y0, r, base, light, dark):
    for y in range(S):
        for x in range(S):
            dx, dy = x - x0, y - y0
            if dx * dx + dy * dy * 1.3 <= r * r:
                k = (-dx - dy) / (2.0 * r)          # light from the top-left
                c = light if k > 0.35 else dark if k < -0.45 else base
                img[y][x] = c


def boulder(img, rng, cx, cy, rx, ry, base, light, dark, outline=None):
    for y in range(S):
        for x in range(S):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            d = dx * dx + dy * dy
            if d <= 1.0:
                k = -(dx + dy) * 0.7 + rng.uniform(-0.12, 0.12)
                if outline and d > 0.82:
                    c = outline
                elif k > 0.45:
                    c = light
                elif k < -0.5:
                    c = dark
                else:
                    c = base
                j = rng.uniform(-6, 6)
                img[y][x] = tuple(clamp(v + j) for v in c)


def sand():
    img, rng = textured((208, 186, 132), 9, 101, blur=2, fine=4)
    speck(img, rng, [(176, 152, 104), (186, 162, 112), (230, 214, 168)], 40)
    speck(img, rng, [(160, 140, 110)], 3, 2)
    return img


def dirt():
    img, rng = textured((126, 92, 56), 10, 202, blur=2, fine=5)
    speck(img, rng, [(104, 74, 44), (146, 110, 70), (112, 82, 50)], 70)
    for x, y in ((9, 22), (24, 8)):
        pebble(img, x, y, 1.3, (118, 102, 82), (140, 124, 102), (92, 70, 48))
    return img


# (cave tiles: see the CAVE AND GATHERING TILES section below)


def forest():
    """Dense forest canopy: overlapping leafy clumps, tileable (clumps wrap round the edges)."""
    img, rng = textured((30, 54, 14), 6, 707, blur=1, fine=3)
    clumps = [(4, 5, 7), (17, 3, 8), (28, 9, 7), (9, 16, 8), (22, 18, 8), (3, 27, 7), (15, 28, 7), (29, 27, 6), (16, 11, 5)]
    for cx, cy, r in clumps:
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                d = (x * x + y * y) ** 0.5
                if d > r + rng.uniform(-0.8, 0.3):
                    continue
                k = (-x - y) / (2.0 * r)                  # light from the top-left
                if d > r - 1.2:
                    c = (22, 40, 10)
                elif k > 0.3:
                    c = (78, 116, 34)
                elif k < -0.35:
                    c = (34, 62, 15)
                else:
                    c = (52, 88, 22)
                j = rng.uniform(-6, 6)
                img[(cy + y) % S][(cx + x) % S] = tuple(clamp(v + j) for v in c)
    speck(img, rng, [(92, 132, 44), (60, 100, 28)], 30)
    return img


def copy_tile(name):
    w, h, rows = read_bmp(p("sprites", "Tiles", name + ".png"))
    return rows[h // 2:]


def sea_rock(variant):
    """Rocks sticking out of the open sea, with a ring of white foam (on the Water001 picture)."""
    img = [list(r) for r in copy_tile("Water001")]
    rng = random.Random(900 + variant)
    rocks = [(16, 17, 9, 7.5)] if variant == 1 else [(11, 19, 6.5, 5.5), (22, 12, 5, 4.2)]
    for cx, cy, rx, ry in rocks:                    # the foam first, a little bigger than the rock
        for y in range(S):
            for x in range(S):
                dx, dy = (x + 0.5 - cx) / (rx + 2.2), (y + 0.5 - cy) / (ry + 2.0)
                d = dx * dx + dy * dy
                if d <= 1.0 and (d > 0.62 or (x + y) % 2 == 0):
                    img[y][x] = (222, 236, 246) if (x * 3 + y) % 5 else (180, 206, 228)
    for cx, cy, rx, ry in rocks:
        boulder(img, rng, cx, cy, rx, ry, (112, 112, 108), (156, 156, 150), (70, 70, 68), outline=(46, 46, 48))
        for _ in range(int(rx)):                    # wet moss and barnacles
            x, y = int(cx + rng.uniform(-rx, rx) * 0.6), int(cy + rng.uniform(0.1, 0.8) * ry)
            if 0 <= x < S and 0 <= y < S:
                img[y][x] = rng.choice([(70, 96, 52), (84, 112, 60), (190, 186, 170)])
    return img


# ----- Edge blending masks (sprites\Interface\Blend_<side><variant>.png), used by the game's Paint.Window.Cell: where a tile
# meets a neighbour with a higher Tiles.ini Blend (grass 3 > sand, dirt 2 > water 1), the neighbour's Blend.Texture is
# drawn over this tile's edge through the mask. Top half = mask (black where the neighbour shows), bottom half = the
# same area in white (the game ANDs the texture with it). Side edges are wavy bands about 6 px deep that start and end
# at the same depth, so neighbouring tiles' bands join up; the last pixel or so is dithered. Corners are wavy blobs.
def _band_depth(t, variant):
    import math
    a = 2 * math.pi * t / S
    if variant == 1:
        return 6.0 + 1.9 * math.sin(a * 2) + 1.1 * math.sin(a * 3 + 0.0) * math.sin(a)
    return 6.0 - 1.6 * math.sin(a * 3) + 1.2 * math.sin(a) * math.sin(a * 2)


def blend_mask(side, variant):
    import math
    m = [[False] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            if side in ("N", "S", "E", "W"):
                t, d = {"N": (x, y), "S": (x, S - 1 - y), "W": (y, x), "E": (y, S - 1 - x)}[side]
                depth = _band_depth(t + 0.5, variant)
                inside = d + 0.5 < depth - 1.2 or (d + 0.5 < depth and (x + y) % 2 == 0)
            else:
                cx = 0 if "W" in side else S
                cy = 0 if "N" in side else S
                r = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                ang = math.atan2(y + 0.5 - cy, x + 0.5 - cx)
                radius = 7.5 + (1.2 if variant == 1 else -0.8) * math.sin(ang * 6)
                inside = r < radius - 1.2 or (r < radius and (x + y) % 2 == 0)
            m[y][x] = inside
    return m


BLEND_MASKS = {"Blend_%s%d" % (side, v): (side, v) for side in ("N", "E", "S", "W", "NE", "SE", "SW", "NW") for v in (1, 2)}


NEW_TILES = {
    "Sand001": sand,
    "Dirt001": dirt,
    # Forest001 (impassable dense woodland) is drawn by build_forest.py now, from its canopy texture
    # The castle walls: the existing Stone_Wall sprite has no variant number (and Tiles.ini already has
    # a [Stone_Wall001] section with no sprite), so this is the same image under the proper name.
    "Stone_Wall001": lambda: copy_tile("Stone_Wall"),
    "Sea_Rock001": lambda: sea_rock(1),   # rocks in the open sea (scattered by build_scenery.py)
    "Sea_Rock002": lambda: sea_rock(2),
}
# The cave tileset and the gathering tiles (mushrooms, ore, berries, wheat, nests, ladders...): see cave_tiles.py
from cave_tiles import TILES as CAVE_TILES, SEAMLESS
NEW_TILES.update(CAVE_TILES)
# The Wildlands (build_regions.py): snow, ice, marsh, reeds, bog myrtle, snowy pines and rocks, cacti: see region_tiles.py
from region_tiles import TILES as REGION_TILES
NEW_TILES.update(REGION_TILES)


def write_sprite_bmp(path, image, mask=None):
    """image: S rows of S (r,g,b), top to bottom. mask: same shape of bools (True = drawn); default all drawn.
    Written as a PNG (path's .png becomes .png)."""
    rows = [[(0, 0, 0) if (mask is None or mask[y][x]) else (255, 255, 255) for x in range(S)] for y in range(S)]
    return write_sprite(path, rows + image)         # (top half mask, bottom half image)


def main():
    made = {}
    for name, make in NEW_TILES.items():
        made[name] = make()
        changed = write_sprite_bmp(p("sprites", "Tiles", name + ".png"), made[name])
        print(("wrote " if changed else "unchanged ") + name)
    for name, (side, v) in BLEND_MASKS.items():
        m = blend_mask(side, v)
        white = [[(255, 255, 255) if m[y][x] else (0, 0, 0) for x in range(S)] for y in range(S)]
        changed = write_sprite_bmp(p("sprites", "Interface", name + ".png"), white, m)
        print(("wrote " if changed else "unchanged ") + name)
    import farm_tiles                                # the wheat plants and stubble (entities)
    for name in farm_tiles.write_entities():
        print("wrote " + name)
    if "--preview" in sys.argv:
        import sprite_kit as K
        names = list(CAVE_TILES)
        K.sheet(p("dev", "Renders", "Tiles preview.png"), [made[n] for n in names], scale=3, cols=8)
        K.sheet(p("dev", "Renders", "Tiles 4x4.png"), [made[n] for n in SEAMLESS], scale=2, cols=5, tile_repeat=4)
        print("previews: dev\\Renders\\Tiles preview.png, dev\\Renders\\Tiles 4x4.png")
        print("  order: " + ", ".join(names))


if __name__ == "__main__":
    main()
