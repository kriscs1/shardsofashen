"""Tiles for the Wildlands (build_regions.py): snow, ice, marsh, reeds, bog myrtle, snowy pines and rocks, cacti and
desert rocks. Used by build_tiles.py, which writes the sprites (sprites\\Tiles\\*.png).

Every function returns a 32x32 opaque image (rows of (r, g, b)). The ground tiles (snow, ice, marsh) are drawn
wrap-around so they tile seamlessly; the others are a ground tile with something on it.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K
from common import p, read_bmp

S = 32


def clamp(v):
    return max(0, min(255, int(round(v))))


def copy_tile(name):
    w, h, rows = read_bmp(p("sprites", "Tiles", name + ".png"))
    return [list(r) for r in rows[h // 2:]]


def ground(base, seed, amp=6, fine=3, blur=3):
    rng = random.Random(seed)
    big = K.noise_field(rng, S, S, amp, blur=blur)
    small = K.noise_field(rng, S, S, amp * 0.6, blur=1)
    return [[tuple(clamp(c + big[y][x] + small[y][x] + rng.uniform(-fine, fine)) for c in base)
             for x in range(S)] for y in range(S)], rng


def speck(img, rng, colours, count, size=1):
    for _ in range(count):
        x, y = rng.randrange(S), rng.randrange(S)
        c = rng.choice(colours)
        for dy in range(size):
            for dx in range(size):
                img[(y + dy) % S][(x + dx) % S] = c


def blob(img, rng, cx, cy, rx, ry, base, light, dark, outline=None, jitter=6):
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = dx * dx + dy * dy
            if d <= 1.0:
                k = -(dx + dy) * 0.7 + rng.uniform(-0.12, 0.12)
                if outline and d > 0.8:
                    c = outline
                elif k > 0.45:
                    c = light
                elif k < -0.5:
                    c = dark
                else:
                    c = base
                j = rng.uniform(-jitter, jitter)
                img[y][x] = tuple(clamp(v + j) for v in c)


# ---------------------------------------------------------------- ground
def snow():
    img, rng = ground((226, 232, 242), 1101, amp=5)
    speck(img, rng, [(246, 248, 252), (204, 214, 230), (214, 222, 236)], 60)
    return img


def ice():
    img, rng = ground((156, 196, 222), 1102, amp=5)
    for k in range(5):                                  # white cracks and streaks
        x, y = rng.randrange(S), rng.randrange(S)
        for t in range(rng.randrange(6, 14)):
            img[y % S][x % S] = (226, 238, 248)
            x += rng.choice((1, 1, 0, -1)); y += rng.choice((0, 1))
    speck(img, rng, [(196, 222, 240), (134, 176, 206)], 30)
    return img


def marsh():
    img, rng = ground((84, 96, 46), 1103, amp=8)
    for _ in range(4):                                  # dark wet patches
        cx, cy, r = rng.randrange(S), rng.randrange(S), rng.uniform(2, 4)
        for y in range(S):
            for x in range(S):
                dx = min(abs(x - cx), S - abs(x - cx)); dy = min(abs(y - cy), S - abs(y - cy))
                if dx * dx + dy * dy < r * r:
                    img[y][x] = tuple(clamp(v * 0.7) for v in img[y][x])
    speck(img, rng, [(110, 124, 60), (64, 76, 38), (96, 90, 50)], 50)
    return img


def reeds():
    img = marsh()
    rng = random.Random(1104)
    for k in range(14):                                 # reed stalks with brown cattail heads
        x = 2 + k * 2 + rng.randrange(-1, 2)
        top = rng.randrange(4, 12)
        for y in range(top, 30):
            img[y][x % S] = (70, 112, 40) if (x + y) % 3 else (96, 140, 54)
        if k % 2 == 0:
            for y in range(top - 1, top + 4):
                img[y][x % S] = (110, 70, 34)
    return img


def bog_myrtle():
    img = marsh()
    rng = random.Random(1105)
    blob(img, rng, 16, 18, 10, 8, (60, 104, 52), (90, 140, 70), (38, 70, 34), outline=(26, 46, 22))
    for _ in range(9):                                  # small purple-brown catkins
        x, y = rng.randrange(9, 24), rng.randrange(12, 24)
        img[y][x] = (150, 90, 130); img[y + 1][x] = (120, 70, 104)
    return img


# ---------------------------------------------------------------- things on snow and sand
def snow_pine():
    img = snow()
    rng = random.Random(1106)
    for x in range(14, 18):                             # trunk
        for y in range(25, 31):
            img[y][x] = (92, 60, 34) if x < 16 else (70, 44, 24)
    for tier, (top, half) in enumerate(((2, 5), (8, 8), (14, 11))):
        for y in range(top, top + 11):
            w = int(half * (y - top) / 10.0) + 1
            for x in range(16 - w, 16 + w):
                if 0 <= x < S and y < 27:
                    c = (34, 74, 46) if x < 16 else (22, 54, 34)
                    if y - top < 3 or rng.random() < 0.15:
                        c = (236, 240, 248)                 # snow on the branches
                    img[y][x] = c
    return img


def snow_rock():
    img = snow()
    rng = random.Random(1107)
    blob(img, rng, 16, 19, 11, 9, (112, 114, 122), (150, 152, 160), (74, 76, 84), outline=(52, 54, 60))
    for y in range(9, 16):                              # a snow cap
        for x in range(8, 25):
            dx, dy = (x + 0.5 - 16) / 9.0, (y + 0.5 - 13) / 4.0
            if dx * dx + dy * dy < 1:
                img[y][x] = (240, 244, 250) if rng.random() < 0.85 else (214, 222, 236)
    return img


def cactus():
    img = copy_tile("Sand001")
    def bar(x0, x1, y0, y1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = (70, 130, 60) if x < (x0 + x1) // 2 else (48, 98, 44)
                if x in (x0, x1 - 1):
                    c = (34, 70, 32)
                img[y][x] = c
    bar(13, 19, 4, 29)                                  # the trunk
    bar(6, 11, 10, 20); bar(6, 13, 18, 22)              # left arm
    bar(21, 26, 7, 16); bar(18, 26, 14, 18)             # right arm
    for y in range(6, 28, 3):                           # spines
        img[y][12] = (230, 224, 190); img[y + 1][19] = (230, 224, 190)
    return img


def desert_rock():
    img = copy_tile("Sand001")
    rng = random.Random(1108)
    blob(img, rng, 16, 18, 11, 9, (168, 100, 70), (206, 140, 98), (120, 68, 46), outline=(84, 46, 32))
    return img


# ---------------------------------------------------------------- shore corners on sand and snow
SHORE_SIDE = {2: "NE", 3: "NE", 4: "NW", 5: "NW", 6: "SW", 7: "SW", 8: "SE", 9: "SE"}   # the land corner of each piece
SHORE_REACH = float(S)  # the coast runs exactly corner to corner (see shore(); the browser's edge blending meets it)


def shore(n, land_tile):
    """The diagonal shore piece n (Water00n on grass, Sand_Water00n, Snow_Water00n): water with land_tile in one corner.
    The coast runs exactly from corner to corner of the tile (REACH), with the same wavy, dithered edge as the bands,
    the wave dying away at the corners. The browser meets it there (ground.js paintBlendEdges): no corner blob in the
    water beside it, and a straight band of land on the water next to it narrows to nothing at the corner it shares.
    The small pieces (3, 4, 7, 9) have the same line with another wave, so the coast doesn't repeat."""
    water, land = copy_tile("Water001"), copy_tile(land_tile)
    side, small = SHORE_SIDE[n], n in (3, 4, 7, 9)
    img = []
    for y in range(S):
        row = []
        for x in range(S):
            fx = x + 0.5 if "E" in side else S - x - 0.5        # turned so the land corner is at S,S
            fy = y + 0.5 if "S" in side else S - y - 0.5
            t = (fx - fy + S) / (2.0 * S)                       # 0 to 1 along the coast
            a = 2 * math.pi * t
            if small:
                wave = -1.2 * math.sin(a * 3) + 0.9 * math.sin(a * 2)
            else:
                wave = 1.3 * math.sin(a * 2) + 0.8 * math.sin(a * 3)
            d = (fx + fy - SHORE_REACH) / math.sqrt(2) + wave * math.sin(math.pi * t)   # px past the coast (+ = land)
            inside = d > 1.2 or (d > 0 and (x + y) % 2 == 0)
            row.append(land[y][x] if inside else water[y][x])
        img.append(row)
    return img


def portal():
    """The wizard's portal in the dragon's lair (build_dragon.py): a ring of violet fire on the cave floor."""
    img = copy_tile("Cave_Floor001")
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - 16, (y + 0.5 - 16) * 1.25)
            a = math.atan2(y + 0.5 - 16, x + 0.5 - 16)
            if 8 <= d <= 13:
                k = 0.5 + 0.5 * math.sin(a * 5 + d)
                img[y][x] = tuple(clamp(c1 + (c2 - c1) * k) for c1, c2 in zip((110, 30, 170), (230, 160, 255)))
            elif d < 8:
                img[y][x] = tuple(clamp(v * 0.5 + w * 0.5) for v, w in zip(img[y][x], (60, 20, 90)))
    return img


SHORE_PIECES = list(range(2, 10))     # Water002-009: 002/005/006/008 big corners, 003/004/007/009 small ones

TILES = {
    "Snow001": snow,
    "Ice001": ice,
    "Marsh001": marsh,
    "Reeds001": reeds,
    "Bog_Myrtle001": bog_myrtle,
    "Bog_Myrtle002": marsh,          # picked: the bush is gone for a while (it regrows into Bog_Myrtle001)
    "Snow_Pine001": snow_pine,
    "Snow_Rock001": snow_rock,
    "Cactus001": cactus,
    "Desert_Rock001": desert_rock,
    "Portal001": portal,
}
for _n in SHORE_PIECES:     # (the Isle's own grass pieces were redrawn the same way; originals in dev\Archive)
    TILES["Water%03d" % _n] = (lambda n=_n: shore(n, "Grass001"))
    TILES["Sand_Water%03d" % _n] = (lambda n=_n: shore(n, "Sand001"))
    TILES["Snow_Water%03d" % _n] = (lambda n=_n: shore(n, "Snow001"))
SEAMLESS = ["Snow001", "Ice001", "Marsh001"]
