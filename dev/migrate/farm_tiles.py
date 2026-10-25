"""Wheat, stubble, the haystack and the cliffs (used by build_tiles.py through cave_tiles.TILES).

Each function returns a 32x32 opaque image (rows of (r, g, b)), like the other tile makers.
  * Wheat001 / Wheat002: a field of ripe wheat / stubble after harvesting, drawn wrap-around so fields tile seamlessly.
  * Haystack001: a round, layered stack of straw on grass.
  * Door002 / Door003: the house door (Door001, on red brick) set in the grey castle stone / in cave rock.
  * Cliff001-005: rock faces. Their shapes come from the original sprites (kept in dev\\Archive\\Sprites), so the pieces
    still join up and match their Walkable.Data: a grassy lip along the top, cracked stone lit from the top left,
    and a shadow at the foot.
"""
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p, read_bmp

S = 32


def tile_array(path):
    w, h, rows = read_bmp(path)
    return np.array(rows[h // 2:], dtype=np.float32)


def grass():
    return tile_array(p("sprites", "Tiles", "Grass001.png"))


def to_rows(a):
    a = np.clip(np.round(a), 0, 255).astype(np.uint8)
    return [[tuple(int(v) for v in a[y, x]) for x in range(S)] for y in range(S)]


def smooth_noise(rng, amp, blur, wrap=True):
    """Value noise, blurred (wrapping round the tile)."""
    n = np.array([[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)], dtype=np.float32)
    for _ in range(blur):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5
    n /= max(1e-6, np.abs(n).max())
    return n * amp


def blend(img, x, y, col, a):
    """Mix col into pixel x,y (wrapping) by a (0..1)."""
    x, y = int(x) % S, int(y) % S
    img[y, x] = img[y, x] * (1 - a) + np.array(col, dtype=np.float32) * a


# ---------------------------------------------------------------- wheat
def wheat(cut=False):
    rng = random.Random(911 if not cut else 921)
    soil = np.array((92, 70, 40), dtype=np.float32)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = soil
    img += smooth_noise(rng, 10, 2)[:, :, None]
    if cut:
        return to_rows(stubble(img, rng))
    # Dense stalks, back to front, each leaning a little the same way (the wind), with a heavy ear on top
    stalks = []
    for row in range(8):                                   # staggered rows so it never looks like a grid
        for k in range(9):
            x = k * 32 / 9 + rng.uniform(-1.6, 1.6) + (row % 2) * 1.8
            y = row * 4 + rng.uniform(-1.2, 1.2)
            stalks.append((y, x))
    stalks.sort()
    for by, bx in stalks:
        h = rng.uniform(7, 10)
        lean = 0.22 + rng.uniform(-0.12, 0.12)
        tone = rng.uniform(-18, 18)
        stalk = (172 + tone, 142 + tone, 66 + tone * 0.5)
        for i in range(int(h)):
            t = i / h
            x, y = bx + lean * i, by - i
            blend(img, x, y + 6, (60, 44, 22), 0.25)                   # shade between the stalks
            blend(img, x, y, stalk, 0.95)
        tx, ty = bx + lean * h, by - h                                  # the ear: plump grains, lit on the left
        for j in range(5):
            gx, gy = tx + lean * j * 0.6, ty - j * 0.9
            light = (250, 222, 128) if j % 2 == 0 else (236, 198, 98)
            blend(img, gx - 0.6, gy, light, 0.95)
            blend(img, gx + 0.8, gy, (198, 150, 58), 0.9)
        blend(img, tx + lean * 3.6 + 0.3, ty - 4.6, (252, 232, 150), 0.8)   # the tip
        for a in (-1, 1):                                               # whiskers (awns)
            blend(img, tx + a * 1.6 + lean * 4, ty - 4.2, (226, 196, 120), 0.45)
    img += smooth_noise(rng, 6, 3)[:, :, None]                          # gentle patches of light and shade
    return to_rows(img)


def stubble(img, rng):
    """After harvesting: rows of short cut stalks on the earth, with loose straw lying about."""
    img = img * 0.95 + np.array((10, 6, 0), dtype=np.float32)
    for row in range(8):
        for k in range(10):
            x = k * 3.2 + rng.uniform(-0.8, 0.8) + (row % 2) * 1.6
            y = row * 4 + 2 + rng.uniform(-0.5, 0.5)
            blend(img, x + 1, y + 1, (58, 42, 22), 0.5)                 # its shadow
            blend(img, x, y, (188, 160, 92), 0.95)
            blend(img, x, y - 1, (224, 198, 130), 0.9)                  # the cut end catches the light
    for _ in range(26):                                                 # loose straw
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        a = rng.uniform(0, math.pi)
        c = rng.choice([(214, 184, 104), (190, 158, 80), (236, 210, 140)])
        for i in range(rng.randrange(3, 6)):
            blend(img, x + math.cos(a) * i, y + math.sin(a) * i * 0.5, c, 0.75)
    return img


# ---------------------------------------------------------------- haystack
def haystack():
    rng = random.Random(931)
    img = grass()
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32) + 0.5
    # shadow on the grass, to the lower right
    d = ((xs - 18.5) / 14.0) ** 2 + ((ys - 28.0) / 4.2) ** 2
    img *= np.where(d < 1, 0.55 + 0.45 * np.clip(d, 0, 1) ** 2, 1.0)[:, :, None]
    # the stack: a dome, flat at the bottom, a little narrower at the top
    cx, base, top = 16.0, 28.5, 4.5
    t = np.clip((ys - top) / (base - top), 0, 1)
    half = 13.0 * np.sqrt(np.clip(1 - (1 - t) ** 2.2, 0, 1)) * (0.92 + 0.08 * t)
    inside = (ys >= top) & (ys <= base) & (np.abs(xs - cx) <= half)
    nx = (xs - cx) / np.maximum(half, 1)
    ny = 1 - t
    light = np.clip(0.62 - 0.38 * nx + 0.42 * ny, 0.2, 1.15)              # lit from the upper left
    straw = np.array((222, 184, 86), dtype=np.float32)
    body = straw[None, None, :] * light[:, :, None]
    # straw: short strokes running down and out from the top, in layers
    streaks = np.zeros((S, S), dtype=np.float32)
    for _ in range(170):
        sx = rng.uniform(cx - 13, cx + 13)
        sy = rng.uniform(top, base)
        ang = math.atan2(1.0, (sx - cx) / 9.0)
        dv = rng.choice((-1, 1)) * rng.uniform(0.25, 0.55)
        for i in range(rng.randrange(3, 7)):
            x, y = int(sx + math.cos(ang) * i), int(sy + math.sin(ang) * i * 0.8)
            if 0 <= x < S and 0 <= y < S:
                streaks[y, x] = dv
    layers = 0.08 * np.sin((ys - top) * 1.15 + np.sin(xs * 0.5))           # the bands where it was piled
    shade = 1 + streaks + layers
    body *= shade[:, :, None]
    rim = inside & ~(np.roll(inside, 1, 0) & np.roll(inside, -1, 0) & np.roll(inside, 1, 1) & np.roll(inside, -1, 1))
    body[rim] *= 0.72                                                       # a soft dark edge
    img = np.where(inside[:, :, None], body, img)
    # loose straw on the grass round the foot
    for _ in range(18):
        a = rng.uniform(0, 2 * math.pi)
        x, y = cx + math.cos(a) * rng.uniform(12, 15), base - 0.5 + math.sin(a) * rng.uniform(1, 3)
        b = rng.uniform(0, math.pi)
        for i in range(rng.randrange(2, 4)):
            blend(img, x + math.cos(b) * i, y + math.sin(b) * i * 0.5, (226, 192, 100), 0.85)
    return to_rows(img)


# ---------------------------------------------------------------- cliffs
# All five pieces are cut from the same two bands, so they meet exactly: the upright band (Cliff001 its top end,
# Cliff002 straight, Cliff003 turning east) and the lying band (Cliff003, Cliff004 straight, Cliff005 its east end).
# The bands' ragged edges repeat every 32 pixels, so pieces in a row join without a step.
def _wave(t, parts):
    return sum(a * np.sin(2 * np.pi * k * t / S + ph) for a, k, ph in parts)


def band_edges():
    t = np.arange(S, dtype=np.float32) + 0.5
    left = 9.5 + _wave(t, ((1.1, 1, 0.6), (0.5, 2, 1.9)))           # the upright band, x at each y
    right = 22.5 + _wave(t, ((0.9, 1, 2.4), (0.45, 3, 0.3)))
    top = 16.5 + _wave(t, ((1.1, 1, 1.1), (0.55, 2, 0.2)))          # the lying band, y at each x
    bottom = 29.5 + _wave(t, ((0.7, 1, 2.0), (0.35, 3, 1.4)))
    return left, right, top, bottom


def cliff_shape(name):
    """The piece's cliff as a 0/1 mask (rows y, columns x)."""
    left, right, top, bottom = band_edges()
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32) + 0.5
    upright = (xs >= left[ys.astype(int)]) & (xs <= right[ys.astype(int)])
    lying = (ys >= top[xs.astype(int)]) & (ys <= bottom[xs.astype(int)])
    mid, half = (left + right) / 2, (right - left) / 2
    if name == "Cliff001":                      # the top end of an upright run: rounded off
        end = 7.0 + 6.0 * ((xs - mid[ys.astype(int)]) / half[ys.astype(int)]) ** 2
        m = upright & (ys >= end)
    elif name == "Cliff002":
        m = upright
    elif name == "Cliff003":                    # coming down, then turning east along the foot
        m = (upright & (ys <= bottom[xs.astype(int)])) | (lying & (xs >= left[ys.astype(int)]))
        # round the outside of the bend
        r = 4.0
        cx, cy = left[S - 4] + r, bottom[int(left[S - 4])] - r
        m &= ~((xs < cx) & (ys > cy) & ((xs - cx) ** 2 + (ys - cy) ** 2 > r * r))
    elif name == "Cliff004":
        m = lying
    else:                                       # Cliff005: the east end of a lying run
        tmid, thalf = (top + bottom) / 2, (bottom - top) / 2
        end = 26.0 - 5.0 * ((ys - tmid[xs.astype(int)]) / thalf[xs.astype(int)]) ** 2
        m = lying & (xs <= end)
    return m.astype(np.float32)


def walk_data(name):
    """Tiles.ini Walkable.Data for a piece: 7 x 7 cells, 0 where the rock covers 40% of the cell or more."""
    m = cliff_shape(name)
    out = ""
    for cy in range(7):
        for cx in range(7):
            y0, y1 = int(cy * S / 7), int((cy + 1) * S / 7)
            x0, x1 = int(cx * S / 7), int((cx + 1) * S / 7)
            out += "0" if m[y0:y1, x0:x1].mean() >= 0.4 else "1"
    return out


def soften(m, n=2):
    """A blurred copy that doesn't wrap (the edges of the tile carry on outward)."""
    a = m.copy()
    for _ in range(n):
        pad = np.pad(a, 1, mode="edge")
        a = (pad[1:-1, 1:-1] * 4 + pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]) / 8
    return a


def cliff(name, seed):
    rng = random.Random(seed)
    img = grass()
    m = cliff_shape(name)
    soft = soften(m, 3)
    gy, gx = np.gradient(soft)                                  # which way each bit of rock faces
    ys, xs = np.mgrid[0:S, 0:S].astype(np.float32)
    # how far down the face each pixel is (0 at the top edge, 1 at the foot): lit at the top, shaded below
    depth = np.zeros((S, S), dtype=np.float32)
    for x in range(S):
        run = 0
        col = m[:, x]
        for y in range(S):
            run = run + 1 if col[y] > 0 else 0
            depth[y, x] = run
    height = np.maximum(depth, 1)
    for x in range(S):                                          # each run's own length, so depth is 0..1
        y = S - 1
        while y >= 0:
            if m[y, x] > 0:
                top = y
                while top > 0 and m[top - 1, x] > 0:
                    top -= 1
                # a run that goes off the top or bottom of the tile carries on into the next one: shade it as the
                # middle of a longer face, so the pieces join without a bright band at each tile's edge
                above_more = 8 if top == 0 else 0
                below_more = 8 if y == S - 1 else 0
                depth[top:y + 1, x] += above_more
                height[top:y + 1, x] = y - top + 1 + above_more + below_more
                if above_more and below_more:               # the whole height of the tile: shade it evenly
                    depth[top:y + 1, x] = (height[top, x] + 1) / 2
                y = top - 1
            else:
                y -= 1
    down = np.clip((depth - 1) / np.maximum(height - 1, 1), 0, 1)
    side = np.clip(0.9 - 2.2 * gx, 0.55, 1.2)                   # the upright pieces: lit on the left, dark on the right
    lit = side * (1.12 - 0.5 * down)
    # stone: grey-brown with vertical fluting and grain
    rock = np.empty((S, S, 3), dtype=np.float32)
    rock[:, :] = (126, 112, 96)
    flutes = np.array([rng.uniform(-1, 1) for _ in range(S)], dtype=np.float32)
    flutes = (flutes + np.roll(flutes, 1) * 0.6 + np.roll(flutes, -1) * 0.3) / 1.9
    rock += (14 * flutes)[None, :, None]
    rock += smooth_noise(rng, 8, 0)[:, :, None]
    rock += smooth_noise(rng, 10, 2)[:, :, None]
    rock *= lit[:, :, None]
    # cracks: dark lines running down the face, lit on their left
    for _ in range(7):
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        for i in range(rng.randrange(4, 9)):
            xi, yi = int(x), int(y + i)
            if 0 <= xi < S and 0 <= yi < S and m[yi, xi] > 0:
                rock[yi, xi] *= 0.5
                if xi > 0 and m[yi, xi - 1] > 0:
                    rock[yi, xi - 1] *= 1.18
            x += rng.uniform(-0.6, 0.6)
    # the top edge: a sunlit rim of rock, and grass hanging over it in tufts
    above = (m > 0) & (np.pad(m, ((1, 0), (0, 0)), mode="edge")[:-1] == 0)
    rim = (m > 0) & np.roll(above, 1, 0) & ~above
    rock[rim] = np.minimum(255, rock[rim] * 1.35)
    rock[above] = rock[above] * 0.2 + np.array((96, 132, 48)) * 0.8
    for x in range(S):
        for y in range(S - 2):
            if above[y, x] and rng.random() < 0.4 and m[y + 1, x] > 0:
                rock[y + 1, x] = rock[y + 1, x] * 0.3 + np.array((76, 112, 38)) * 0.7
    # the foot: dark where it meets the ground, and a shadow cast onto the grass below and to the right
    below = (m > 0) & (np.pad(m, ((0, 1), (0, 0)), mode="edge")[1:] == 0)
    rock[below] *= 0.55
    shadow = np.pad(m, ((2, 0), (2, 0)), mode="edge")[:-2, :-2]
    shadow = soften(np.clip(shadow - m, 0, 1), 1)
    img *= (1 - 0.55 * shadow)[:, :, None]
    a = np.clip((soften(m, 1) - 0.25) * 2.0, 0, 1)              # rock over grass, a crisp edge
    img = img * (1 - a[:, :, None]) + rock * a[:, :, None]
    return to_rows(img)


# ---------------------------------------------------------------- doors in other walls
def door(wall, frame, frame_dark):
    """Door001's wooden door on another wall: its pixels are the ones that differ from plain brick, with a frame
    (an arch of dressed stone, or timber) round them."""
    d = tile_array(p("sprites", "Tiles", "Door001.png"))
    b = tile_array(p("sprites", "Tiles", "Brick001.png"))
    img = tile_array(p("sprites", "Tiles", wall + ".png"))
    m = np.abs(d - b).sum(2) > 40
    grow = m.copy()
    grow[:, 1:] |= m[:, :-1]
    grow[:, :-1] |= m[:, 1:]
    grow[1:, :] |= m[:-1, :]
    ring = grow & ~m
    ys = np.mgrid[0:S, 0:S][0]
    img[ring] = np.array(frame, dtype=np.float32)
    img[ring & (ys % 4 == 0)] = np.array(frame_dark, dtype=np.float32)     # joints in the frame
    img[m] = d[m]
    return to_rows(img)


# ---------------------------------------------------------------- the wheat field: soil, plants and stubble
def field():
    """Field001: ploughed earth in furrows, seamless (the wheat plants stand on it as entities)."""
    rng = random.Random(951)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (104, 78, 46)
    img += smooth_noise(rng, 9, 2)[:, :, None]
    ys = np.mgrid[0:S, 0:S][0]
    ridge = np.cos(2 * np.pi * (ys + 0.5) / 8.0)                    # a furrow every 8 pixels
    img *= (1 + 0.16 * ridge)[:, :, None]
    img += smooth_noise(rng, 6, 0)[:, :, None]
    for _ in range(14):                                             # clods and stones
        x, y = rng.randrange(S), rng.randrange(S)
        blend(img, x, y, (70, 52, 32), 0.6)
        blend(img, x + 1, y - 1, (140, 112, 78), 0.4)
    return to_rows(img)


def wheat_plant(seed):
    """A clump of ripe wheat standing on its own (an entity: transparent round it), its foot at the bottom."""
    rng = random.Random(seed)
    img = [[None] * S for _ in range(S)]

    def put(x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < S and 0 <= y < S:
            img[y][x] = tuple(int(max(0, min(255, v))) for v in c)

    stalks = []
    for _ in range(rng.randrange(13, 17)):
        stalks.append((rng.uniform(5, 27), rng.uniform(27, 31)))
    stalks.sort(key=lambda s_: s_[1])                               # the ones further back first
    for bx, by in stalks:
        h = rng.uniform(14, 22)
        lean = (bx - 16) / 16 * 0.25 + rng.uniform(-0.1, 0.1)       # fanning out a little from the middle
        tone = rng.uniform(-20, 16)
        for i in range(int(h)):
            t = i / h
            c = (150 + tone - 30 * (1 - t), 132 + tone - 30 * (1 - t), 60 + tone * 0.5)
            put(bx + lean * i, by - i, c)
        tx, ty = bx + lean * h, by - h
        for j in range(6):                                          # the ear, lit on its left
            gx, gy = tx + lean * j * 0.5, ty - j * 0.8
            put(gx - 0.6, gy, (250, 222, 128) if j % 2 == 0 else (232, 194, 96))
            put(gx + 0.6, gy, (196, 150, 58))
        put(tx + lean * 5, ty - 5.4, (252, 234, 156))
        if rng.random() < 0.6:                                      # whiskers
            put(tx + lean * 6 - 1, ty - 6, (226, 200, 126))
    for x in range(6, 27):                                          # a little shade where they stand
        if img[30][x] is not None:
            img[30][x] = tuple(int(v * 0.6) for v in img[30][x])
    return img


def stubble_plant():
    """What's left when it's cut: short stalks and loose straw (an entity)."""
    rng = random.Random(961)
    img = [[None] * S for _ in range(S)]
    for _ in range(14):
        x, y = rng.randrange(6, 27), rng.randrange(25, 31)
        for i in range(rng.randrange(2, 4)):
            if 0 <= y - i < S:
                img[y - i][x] = (196, 168, 96) if i else (130, 104, 56)
        if y - 3 >= 0:
            img[y - 3][x] = (226, 200, 132)
    for _ in range(8):
        x, y = rng.uniform(5, 26), rng.uniform(26, 31)
        for i in range(3):
            xi, yi = int(x + i), int(y + i * 0.3)
            if 0 <= xi < S and 0 <= yi < S:
                img[yi][xi] = (214, 186, 106)
    return img


ENTITIES = {
    "Ripe_Wheat001": lambda: wheat_plant(971),
    "Ripe_Wheat002": lambda: wheat_plant(972),
    "Ripe_Wheat003": lambda: wheat_plant(973),
    "Stubble": stubble_plant,
}


def write_entities():
    """Writes the entity sprites above (sprites\\Entities). Returns the names written."""
    import sprite_kit as K
    return [name for name, make in ENTITIES.items() if K.save("Entities", name, make())]


TILES = {
    "Field001": field,
    "Haystack001": haystack,
    "Door002": lambda: door("Stone_Wall001", (176, 172, 164), (112, 108, 102)),
    "Door003": lambda: door("Cave_Wall002", (104, 76, 46), (66, 46, 28)),
    "Cliff001": lambda: cliff("Cliff001", 941),
    "Cliff002": lambda: cliff("Cliff002", 942),
    "Cliff003": lambda: cliff("Cliff003", 943),
    "Cliff004": lambda: cliff("Cliff004", 944),
    "Cliff005": lambda: cliff("Cliff005", 945),
}
