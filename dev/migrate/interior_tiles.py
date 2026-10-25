"""Furniture, stairs and city walls (used by build_tiles.py through cave_tiles.TILES). Each function returns a 32x32
opaque image (rows of (r, g, b)); light comes from the top left, so things cast their shadow down and to the right.

  * Furniture, drawn on the plank floor (Plank001) that every house has (villages.furnish() puts it in):
    Bed001 / Bed002 (the head and the foot of a bed, one above the other), Table001, Chair001-004 (facing south, north,
    east, west), Potted_Plant001, Bookshelf001, and Fireplace001 (a hearth set into a wall: the back wall of a room,
    under the chimney on the roof).
  * Stairs001 (up) / Stairs002 (down): the same as a ladder (Climb Up / Climb Down to the same X,Y on the level above or
    below), for houses with an upper floor. Ladder008 (a ladder up) / Ladder009 (a hatch down) are Ladder001 / Ladder002
    on planks, for the houses that make do with a ladder.
  * City walls, two tiles tall where they run east-west (the top row: wall-walk and battlements; the row below: the
    face): City_Wall001 over City_Wall004; City_Wall002 (a wall running north-south, seen from above, one tile);
    City_Wall003 over City_Wall005 (a tower: the corners, half way along, either side of the gate); the gateway,
    City_Gate003 (the arch) over City_Gate001 (the gates), shut, and City_Gate004 over City_Gate002, open. Tiles.ini:
    City_Gate001 and 003 have Unlocked.Tile=City_Gate002 and 004, so a gate with Lock lines on it is drawn open once
    the locks' condition is met.
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402
from farm_tiles import S, to_rows, smooth_noise, tile_array  # noqa: E402

YS, XS = np.mgrid[0:S, 0:S]
WOOD = np.array((132, 88, 52), dtype=np.float32)
DARK_WOOD = np.array((88, 56, 32), dtype=np.float32)


def C(c):
    return np.array(c, dtype=np.float32)


FLOOR = ["Plank001"]     # the floor the furniture is drawn on (on_floor() draws it on another)


def floor():
    return tile_array(p("sprites", "Tiles", FLOOR[0] + ".png")).copy()


# The furniture again on the other floors, so a table in a tiled room stands on tiles: <Name>1NN on Tile001, 2NN on
# Marble001 (Table101, Chair203...: the same name less its number, so its scripts are the same).
FURNITURE = ["Bed001", "Bed002", "Table001", "Chair001", "Chair002", "Chair003", "Chair004", "Potted_Plant001",
             "Bookshelf001"]
FURNITURE_FLOORS = {"Tile001": 100, "Marble001": 200}


def furniture_on(name, floor_tile):
    n = int(name[-3:]) + FURNITURE_FLOORS[floor_tile]
    return "%s%03d" % (name[:-3], n)


def on_floor(floor_tile, make):
    FLOOR[0] = floor_tile
    try:
        return make()
    finally:
        FLOOR[0] = "Plank001"


def box(x0, y0, x1, y1):
    return (XS >= x0) & (XS <= x1) & (YS >= y0) & (YS <= y1)


def ellipse(cx, cy, rx, ry):
    return ((XS + 0.5 - cx) / rx) ** 2 + ((YS + 0.5 - cy) / ry) ** 2 <= 1


def shadow(img, m, f=0.6):
    img[m] *= f


def lit_box(img, m, col, top=1.18, bottom=0.68, left=1.1, right=0.78):
    """Fill m with col, lighter along its top and left edges, darker along the bottom and right."""
    img[m] = C(col)
    up = m & ~np.roll(m, 1, 0)
    dn = m & ~np.roll(m, -1, 0)
    lf = m & ~np.roll(m, 1, 1)
    rt = m & ~np.roll(m, -1, 1)
    img[up] *= top
    img[lf] *= left
    img[rt] *= right
    img[dn] *= bottom


# ---------------------------------------------------------------- beds
QUILT, QUILT_LIGHT = (156, 48, 44), (184, 76, 62)


def quilt(img, m):
    img[m] = C(QUILT)
    check = m & (((XS // 5) + (YS // 5)) % 2 == 0)
    img[check] = C(QUILT_LIGHT)
    img[m & (XS % 5 == 0)] *= 0.86


def bed_head():
    img = floor()
    shadow(img, box(28, 3, 30, 31))
    rails = box(4, 8, 5, 31) | box(26, 8, 27, 31)
    lit_box(img, rails, WOOD)
    sheet = box(6, 8, 25, 31)
    img[sheet] = C((228, 224, 212))
    pillow = ellipse(16, 12.5, 8.5, 4)
    img[pillow] = C((244, 242, 236))
    img[pillow & (YS >= 14)] = C((206, 202, 192))
    img[pillow & (XS == 16)] *= 0.93
    cover = box(6, 19, 25, 31)
    quilt(img, cover)
    img[box(6, 18, 25, 19)] = C((236, 232, 220))                     # the sheet turned down over it
    img[box(6, 20, 25, 20)] *= 0.7
    head = box(3, 1, 28, 7)
    lit_box(img, head, DARK_WOOD, top=1.35)
    for x0 in (3, 26):                                               # the bed posts, a little taller
        lit_box(img, box(x0, 0, x0 + 2, 7), (104, 68, 40), top=1.4)
    img[box(7, 3, 24, 4)] *= 0.8                                     # a carved panel
    return to_rows(img)


def bed_foot():
    img = floor()
    shadow(img, box(28, 0, 30, 31))
    shadow(img, box(5, 30, 30, 31), 0.65)
    rails = box(4, 0, 5, 27) | box(26, 0, 27, 27)
    lit_box(img, rails, WOOD)
    cover = box(6, 0, 25, 24)
    quilt(img, cover)
    img[box(6, 22, 25, 24)] *= 0.82                                  # the quilt falls over the end
    foot = box(3, 25, 28, 29)
    lit_box(img, foot, DARK_WOOD, top=1.3)
    for x0 in (3, 26):
        lit_box(img, box(x0, 24, x0 + 2, 30), (104, 68, 40), top=1.4)
    return to_rows(img)


# ---------------------------------------------------------------- table and chairs
def table():
    img = floor()
    shadow(img, ellipse(19, 24, 13, 6), 0.62)
    for x0 in (6, 23):
        lit_box(img, box(x0, 21, x0 + 2, 28), DARK_WOOD)
    top = ellipse(15.5, 13, 13, 9.5)
    img[top] = WOOD
    img[top & (YS % 5 == 0)] *= 0.86                                 # the boards
    img[top & ~ellipse(15.5, 13, 12, 8.5) & (YS < 13)] *= 1.2        # the lit near edge
    edge = ellipse(15.5, 15, 13, 9.5) & ~top
    img[edge] = DARK_WOOD                                            # the table top's thickness
    plate = ellipse(21, 12, 4, 2.6)
    img[plate] = C((222, 220, 212))
    img[ellipse(21, 12, 2.4, 1.4)] = C((196, 150, 92))               # a loaf on it
    img[box(10, 7, 11, 12)] = C((236, 230, 210))                     # a candle
    img[box(11, 7, 11, 12)] *= 0.8
    img[box(10, 5, 11, 6)] = C((255, 214, 90))
    img[box(10, 4, 10, 4)] = C((255, 246, 200))
    img[box(9, 13, 12, 13)] = C((150, 150, 156))
    return to_rows(img)


def chair(facing):
    img = floor()
    seat_col = (146, 98, 58)
    if facing in ("S", "N"):
        shadow(img, box(13, 13, 25, 27), 0.62)
        for x0 in (10, 20):
            lit_box(img, box(x0, 20, x0 + 1, 26), DARK_WOOD)
        lit_box(img, box(9, 11, 22, 20), seat_col)
        if facing == "S":                                            # the back behind the seat (north)
            lit_box(img, box(9, 3, 22, 6), DARK_WOOD, top=1.35)
            for x0 in (10, 14, 18, 21):
                lit_box(img, box(x0, 6, x0 + 1, 11), DARK_WOOD)
        else:                                                        # the back nearest us (south)
            lit_box(img, box(9, 17, 22, 23), DARK_WOOD, top=1.35)
            for x0 in (10, 21):
                lit_box(img, box(x0, 23, x0 + 1, 27), DARK_WOOD)
    else:
        shadow(img, box(12, 14, 26, 27), 0.62)
        for x0 in (10, 20):
            lit_box(img, box(x0, 21, x0 + 1, 27), DARK_WOOD)
        lit_box(img, box(9, 13, 22, 21), seat_col)
        bx = 8 if facing == "E" else 21                              # the back on the side it faces away from
        lit_box(img, box(bx, 3, bx + 2, 22), DARK_WOOD, top=1.35)
        for y0 in (7, 12):
            img[box(bx, y0, bx + 2, y0)] *= 0.7
    return to_rows(img)


# ---------------------------------------------------------------- plant, bookshelf, fireplace
def potted_plant():
    img = floor()
    rng = random.Random(4100)
    shadow(img, ellipse(20, 26, 9, 4), 0.6)
    pot = (YS >= 18) & (YS <= 29) & (np.abs(XS + 0.5 - 16) <= 6 - (YS - 18) * 0.18)
    img[pot] = C((182, 94, 58))
    img[pot & (XS < 14)] *= 1.12
    img[pot & (XS > 18)] *= 0.78
    img[box(9, 17, 22, 19)] = C((200, 110, 70))
    img[box(9, 19, 22, 19)] *= 0.7
    img[box(11, 17, 20, 17)] = C((70, 50, 34))                       # earth
    for _ in range(26):                                              # leaves
        a = rng.uniform(-2.6, -0.5)
        r = rng.uniform(2, 11)
        cx, cy = 16 + np.cos(a) * r * 0.9, 15 + np.sin(a) * r
        leaf = ellipse(cx, cy, rng.uniform(1.8, 3), rng.uniform(1.2, 2.2))
        k = (16 - cx + 15 - cy) / 20.0
        img[leaf] = C((62, 124, 50)) * (1 + 0.35 * k) + rng.uniform(-8, 8)
    return to_rows(img)


def bookshelf():
    img = floor()
    rng = random.Random(4200)
    shadow(img, box(29, 2, 31, 31))
    shadow(img, box(4, 29, 31, 31), 0.65)
    case = box(2, 0, 28, 28)
    lit_box(img, case, DARK_WOOD)
    for y0, y1 in ((2, 8), (11, 17), (20, 26)):
        img[box(4, y0, 26, y1)] = C((40, 28, 18))                    # the back of the shelf
        x = 4
        while x <= 25:
            w = rng.choice((2, 2, 3))
            h = rng.randrange(4, y1 - y0 + 2)
            col = C(rng.choice([(140, 40, 40), (44, 70, 120), (60, 104, 58), (150, 120, 60), (96, 54, 96),
                                (170, 150, 120), (110, 70, 40)]))
            if rng.random() < 0.85:
                spine = box(x, y1 - h + 1, min(26, x + w - 1), y1)
                img[spine] = col
                img[spine & (XS == x)] *= 1.2
                img[spine & (YS == y1 - h + 3)] = C((214, 190, 110))  # a gilt band
            x += w
        img[box(3, y1 + 1, 27, y1 + 2)] = WOOD * 1.1                 # the shelf
    return to_rows(img)


def fireplace(south=False, brick=False):
    """south: Fireplace002, the hearth in a room's bottom wall (a house facing north): the stonework upside down,
    the mantel below and the opening above, with the fire still burning upright in it. brick: Fireplace003, the same
    hearth built of red brick in pale mortar (for the brick houses)."""
    rng = random.Random(4300)
    img = np.empty((S, S, 3), dtype=np.float32)
    if brick:
        course = YS // 4                                             # small red bricks, four pixels a course
        img[:, :] = (150, 62, 44)
        img += smooth_noise(rng, 6, 1)[:, :, None]
        shade = np.array([[rng.uniform(0.86, 1.12) for _ in range(4)] for _ in range(9)], dtype=np.float32)
        img *= shade[course.clip(0, 8), ((XS + (course % 2) * 4) // 8).clip(0, 3)][:, :, None]
        joint = (YS % 4 == 3) | (((XS + (course % 2) * 4) % 8) == 7)
        img[joint] = C((198, 178, 156))
        img[(YS % 4 == 0) & ~joint] *= 1.1
    else:
        img[:, :] = (150, 144, 136)
        img += smooth_noise(rng, 6, 1)[:, :, None]
        course = YS // 6
        joint = (YS % 6 == 5) | (((XS + (course % 2) * 5) % 10) == 9)
        img[joint] *= 0.7
        img[(YS % 6 == 0)] *= 1.08
    opening = (XS >= 7) & (XS <= 24) & (YS >= 13) & (((XS + 0.5 - 16) / 9.0) ** 2 + ((YS + 0.5 - 21) / 9.0) ** 2 <= 1.2)
    opening |= box(7, 20, 24, 28)
    glow = ellipse(16, 24, 15, 11) & ~opening
    img[glow] = img[glow] * 0.8 + C((255, 140, 60)) * 0.2           # firelight on the stones
    t = np.clip((YS - 13) / 15.0, 0, 1)
    soot = np.stack([22 + 30 * t, 16 + 14 * t, 14 + 6 * t], axis=-1).astype(np.float32)
    img[opening] = soot[opening]
    if south:
        return to_rows(fireplace_south(img))
    img[box(9, 25, 22, 27)] = C((92, 58, 34))                        # logs
    img[box(9, 25, 22, 25)] *= 1.3
    img[box(12, 24, 19, 24)] = C((120, 76, 42))
    for x, top, col in ((11, 19, (255, 120, 40)), (13, 16, (255, 160, 50)), (15, 15, (255, 196, 70)),
                        (17, 16, (255, 172, 60)), (19, 18, (255, 130, 40)), (21, 21, (240, 100, 30))):
        for y in range(top, 25):
            w = 1 + (y - top) // 3
            for dx in range(-w, w + 1):
                if 7 < x + dx < 25:
                    k = (y - top) / max(1.0, 25.0 - top)
                    img[y, x + dx] = C(col) * (1.05 - 0.25 * abs(dx) / (w + 1)) * (0.85 + 0.15 * k)
    img[box(13, 21, 18, 23)] = C((255, 236, 150))                    # the hottest heart of it
    mantel = box(1, 7, 30, 10)
    lit_box(img, mantel, WOOD, top=1.35, bottom=0.55)
    img[box(1, 11, 30, 11)] *= 0.6
    img[box(4, 4, 6, 6)] = C((210, 200, 180))                        # a jug and a candlestick on the mantel
    img[box(24, 3, 25, 6)] = C((200, 180, 90))
    img[box(24, 1, 25, 2)] = C((255, 214, 90))
    hearth = box(4, 29, 27, 31)
    img[hearth] = C((176, 168, 156))
    img[box(4, 29, 27, 29)] *= 1.15
    return to_rows(img)


def fireplace_south(img):
    """The stones, soot and mantel of fireplace() turned upside down, then the logs and flames drawn upright in the
    opening (now at the top of the tile)."""
    mantel = box(1, 7, 30, 10)
    lit_box(img, mantel, WOOD, top=1.35, bottom=0.55)
    img[box(1, 11, 30, 11)] *= 0.6
    img[box(4, 29, 27, 31)] = C((176, 168, 156))                     # the hearth slab (the top, once turned)
    img = img[::-1].copy()
    d = -10                                                           # the fire sits 10 pixels higher
    img[box(9, 25 + d, 22, 27 + d)] = C((92, 58, 34))
    img[box(9, 25 + d, 22, 25 + d)] *= 1.3
    img[box(12, 24 + d, 19, 24 + d)] = C((120, 76, 42))
    for x, top, col in ((11, 19, (255, 120, 40)), (13, 16, (255, 160, 50)), (15, 15, (255, 196, 70)),
                        (17, 16, (255, 172, 60)), (19, 18, (255, 130, 40)), (21, 21, (240, 100, 30))):
        for y in range(top, 25):
            w = 1 + (y - top) // 3
            for dx in range(-w, w + 1):
                if 7 < x + dx < 25:
                    k = (y - top) / max(1.0, 25.0 - top)
                    img[y + d, x + dx] = C(col) * (1.05 - 0.25 * abs(dx) / (w + 1)) * (0.85 + 0.15 * k)
    img[box(13, 21 + d, 18, 23 + d)] = C((255, 236, 150))
    return img


# ---------------------------------------------------------------- stairs and ladders
def stairs_up():
    """Steps rising to the north (the top of the tile), between two stringers, a banister on the east side."""
    img = floor()
    shadow(img, box(28, 0, 31, 31), 0.58)
    tread, riser = C((168, 120, 74)), C((104, 70, 42))
    steps = [(28, 31), (23, 27), (18, 22), (13, 17), (8, 12), (3, 7)]
    for i, (a, b) in enumerate(steps):
        lift = 1 + 0.07 * i                                          # higher steps are nearer the light
        img[box(6, a, 25, b)] = tread * lift
        img[box(6, b - 1, 25, b)] = riser * lift                     # the riser of the next step up faces us
        img[box(6, a, 25, a)] *= 1.15
        img[box(6, a, 7, b)] *= 0.85
    img[box(6, 0, 25, 2)] = C((30, 22, 16))                          # the floor above
    for x0 in (4, 26):
        lit_box(img, box(x0, 0, x0 + 1, 31), DARK_WOOD)
    for y0 in (3, 13, 23):                                           # the banister posts
        lit_box(img, box(26, y0, 28, y0 + 3), (112, 74, 44), top=1.4)
    img[box(27, 0, 27, 31)] = C((150, 104, 62))                      # the handrail
    return to_rows(img)


def stairs_down():
    """A stairwell in the floor: steps going down to the south into the dark, a railing round three sides."""
    img = floor()
    tread, riser = C((150, 106, 66)), C((84, 56, 34))
    img[box(5, 3, 26, 30)] = C((16, 12, 10))
    steps = [(4, 8), (9, 13), (14, 18), (19, 23), (24, 28)]
    for i, (a, b) in enumerate(steps):
        k = 1 - 0.17 * i                                             # deeper = darker
        img[box(6, a, 25, b - 2)] = tread * k
        img[box(6, b - 1, 25, b)] = riser * k * 0.8
    img[box(6, 3, 25, 3)] = C((20, 14, 10))
    img[box(5, 3, 6, 30)] *= 0.55                                    # the well's own shadow
    lit_box(img, box(3, 1, 28, 2), WOOD, top=1.35)                    # the railing
    lit_box(img, box(3, 1, 4, 30), WOOD, top=1.35)
    lit_box(img, box(27, 1, 28, 30), WOOD, top=1.35)
    for (x0, y0) in ((3, 0), (27, 0), (3, 28), (27, 28)):
        lit_box(img, box(x0, y0, x0 + 1, y0 + 3), DARK_WOOD, top=1.5)
    shadow(img, box(29, 2, 31, 31), 0.6)
    return to_rows(img)


def on_planks(name):
    """Ladder001 / Ladder002 (drawn on Tile001) moved onto the plank floor: the pixels that differ from Tile001."""
    src = tile_array(p("sprites", "Tiles", name + ".png"))
    ground = tile_array(p("sprites", "Tiles", "Tile001.png"))
    img = floor()
    m = np.abs(src - ground).sum(2) > 40
    img[m] = src[m]
    edge = ~m & np.roll(m, 1, 0) & np.roll(m, 1, 1)                 # a soft shadow under the ladder
    img[edge] *= 0.7
    return to_rows(img)


# ---------------------------------------------------------------- city walls
STONE = (166, 160, 148)


def stone(seed, rows=6, w=12):
    """Big dressed blocks, a fresh tone each, in courses of `rows` pixels (seamless across and down)."""
    rng = random.Random(seed)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = STONE
    course = YS // rows
    off = (course % 2) * (w // 2)
    block = ((XS + off) // w) % (S // w + 1) + course * 4
    tones = np.array([rng.uniform(-14, 14) for _ in range(64)], dtype=np.float32)
    img += tones[block % 64][:, :, None] + smooth_noise(rng, 4, 0)[:, :, None]
    joint = (YS % rows == rows - 1) | ((XS + off) % w == w - 1)
    img[joint] = C((108, 102, 94))
    img[(YS % rows == 0) & ~joint] *= 1.1                            # the top of each block catches the light
    return img


def flagstones(seed):
    rng = random.Random(seed)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (150, 146, 138)
    img += smooth_noise(rng, 5, 1)[:, :, None]
    joint = (YS % 8 == 7) | (((XS + (YS // 8 % 2) * 6) % 13) == 12)
    img[joint] *= 0.78
    return img


def wall_top(img, y_walk_end=9):
    """The wall-walk and parapet across the top of an east-west wall: merlons every 16 pixels."""
    walk = flagstones(5001)
    img[YS <= y_walk_end] = walk[YS <= y_walk_end] * 0.82            # behind the parapet: in its shadow
    para = box(0, 9, 31, 13)
    img[para] = stone(5002, rows=5, w=10)[para]
    img[YS == 9] = C(STONE) * 1.25
    merlon = ((XS % 16) >= 2) & ((XS % 16) <= 11)
    m_top = merlon & (YS >= 3) & (YS <= 5)
    m_face = merlon & (YS >= 6) & (YS <= 9)
    img[m_top] = C(STONE) * 1.28
    img[m_face] = stone(5003, rows=4, w=10)[m_face]
    img[merlon & (YS == 3)] *= 1.08
    img[merlon & ((XS % 16) == 11) & (YS >= 3) & (YS <= 9)] *= 0.72
    img[((XS % 16) >= 12) & ((XS % 16) <= 14) & (YS >= 6) & (YS <= 8)] *= 0.7   # each merlon's shadow on the walk
    img[YS == 14] *= 0.55                                            # under the parapet's lip
    return img


# The east-west walls, the towers and the gate are two tiles tall: drawn 64 pixels high here and cut in two. The top
# tile is the wall-walk and battlements, the bottom one the stone face down to the ground.
Y2, X2 = np.mgrid[0:2 * S, 0:S]


def box2(x0, y0, x1, y1):
    return (X2 >= x0) & (X2 <= x1) & (Y2 >= y0) & (Y2 <= y1)


def tall(fn, seed, rows=6, w=12):
    """A 64-high image: fn(top) for the top tile, over two stacked stone faces."""
    img = np.concatenate([stone(seed, rows, w), stone(seed + 7, rows, w)], axis=0)
    img[:S] = fn(img[:S].copy())
    return img


def halves(img):
    return to_rows(img[:S]), to_rows(img[S:])


def slit(img, x, y0, y1):
    img[box2(x, y0, x + 1, y1)] = C((30, 26, 24))
    img[box2(x - 1, y0, x - 1, y1)] *= 0.8
    img[box2(x - 1, y0 - 1, x + 2, y0 - 1)] *= 1.15


def wall_pair():
    img = tall(wall_top, 5000)
    slit(img, 22, 30, 44)
    img[Y2 >= 60] *= 0.72                                            # the foot of the wall, in the grass
    img[Y2 >= 62] *= 0.85
    return halves(img)


def tower_pair():
    """A square tower standing out from the wall: its battlemented top, then its face, lit on the left."""
    img = np.concatenate([stone(5200, 6, 11), stone(5207, 6, 11)], axis=0)
    top = box2(0, 0, 31, 25)
    img[top] = np.concatenate([flagstones(5201), flagstones(5202)], axis=0)[top] * 0.78
    rim = top & ~box2(5, 5, 26, 20)
    img[rim] = C(STONE) * 1.22
    merl = rim & ((((X2 // 6) + (Y2 // 6)) % 2) == 0)
    img[merl] *= 1.12
    img[rim & ((Y2 == 0) | (X2 == 0))] *= 1.1
    img[rim & ((Y2 == 25) | (X2 == 31))] *= 0.7
    img[box2(5, 5, 26, 7)] *= 0.6                                    # the rim's shadow on the tower's roof
    img[box2(5, 5, 7, 20)] *= 0.7
    img[box2(13, 11, 18, 15)] = C((96, 64, 40))                      # a trapdoor
    img[box2(13, 11, 18, 11)] *= 1.3
    img[box2(0, 26, 31, 28)] = C(STONE) * 0.5                        # the parapet overhangs the face
    for x0 in range(1, 31, 5):
        img[box2(x0, 26, x0 + 2, 29)] = C(STONE) * 1.05              # corbels
    img[box2(0, 29, 1, 63)] *= 1.18                                  # the face: a lit edge and a shaded one
    img[box2(29, 29, 31, 63)] *= 0.66
    slit(img, 15, 36, 50)
    img[Y2 >= 60] *= 0.72
    return halves(img)


def gate_pair(open_):
    img = tall(wall_top, 5300)
    cx, spring = 15.5, 41
    opening = (X2 >= 7) & (X2 <= 24) & ((Y2 >= spring) | (((X2 + 0.5 - cx) / 9.0) ** 2 + ((Y2 + 0.5 - spring) / 13.0) ** 2 <= 1))
    ring = ~opening & (X2 >= 4) & (X2 <= 27) & ((Y2 >= spring) | (((X2 + 0.5 - cx) / 12.0) ** 2 + ((Y2 + 0.5 - spring) / 16.0) ** 2 <= 1))
    ring &= Y2 >= 18
    img[ring] = C(STONE) * 1.16
    img[ring & (((X2 * 3 + Y2 * 2) // 5) % 3 == 0)] *= 0.82          # the voussoirs
    img[ring & (X2 >= 25)] *= 0.8
    shield = (Y2 >= 18) & (Y2 <= 25) & (np.abs(X2 + 0.5 - cx) <= 4 - np.maximum(0, Y2 - 22) * 0.9)
    img[shield] = C((150, 36, 36))                                   # Wardhaven's arms over the gate
    img[shield & (np.abs(X2 + 0.5 - cx) <= 1)] = C((220, 184, 70))
    if open_:
        dirt = np.concatenate([tile_array(p("sprites", "Tiles", "Dirt001.png"))] * 2, axis=0)
        t = np.clip((Y2 - 28) / 34.0, 0, 1)
        img[opening] = dirt[opening] * (0.18 + 0.82 * t[opening] ** 1.5)[:, None]   # the road through, dark in the arch
        for x0, x1 in ((7, 9), (22, 24)):                            # the gates, swung back against the walls
            leaf = opening & (X2 >= x0) & (X2 <= x1) & (Y2 >= 34)
            img[leaf] = C((98, 62, 36)) * (1.15 if x0 == 7 else 0.8)
            img[leaf & ((Y2 == 42) | (Y2 == 54))] = C((70, 70, 74))
        portc = opening & (Y2 <= 31) & (Y2 >= 28)
        img[portc & (X2 % 3 == 0)] = C((60, 60, 64))                 # the portcullis, drawn up
    else:
        img[opening] = C((112, 72, 42))
        img[opening & (X2 % 4 == 0)] *= 0.72                         # the boards
        img[opening & ((X2 == 15) | (X2 == 16))] = C((54, 34, 20))   # where the two gates meet
        for yb in (38, 50, 58):
            bands = opening & ((Y2 == yb) | (Y2 == yb + 1))
            img[bands] = C((70, 70, 74))
            img[bands & (Y2 == yb)] *= 1.25
            img[opening & (Y2 == yb) & (X2 % 4 == 2)] = C((176, 176, 184))   # the rivets
        img[opening & (Y2 <= 33)] *= 0.65                            # the arch's shadow
        img[box2(12, 45, 13, 47) | box2(18, 45, 19, 47)] = C((48, 48, 52))   # the ring handles
        img[box2(12, 47, 13, 47) | box2(18, 47, 19, 47)] = C((150, 150, 158))
    img[~opening & (Y2 >= 60)] *= 0.72
    return halves(img)


def city_wall_v():
    img = flagstones(5100)
    img[box(9, 0, 22, 31)] *= 0.9
    for side, (a, b) in (("W", (0, 8)), ("E", (23, 31))):
        para = (XS >= a) & (XS <= b)
        light = 1.18 if side == "W" else 0.95
        img[para] = stone(5101 if side == "W" else 5102, rows=8, w=9)[para] * light
        merlon = para & ((YS % 16) <= 8)
        img[merlon] *= 1.14
        img[merlon & ((YS % 16) == 0)] *= 1.12
        img[para & ((YS % 16) == 9)] *= 0.62                         # the gap below each merlon
        img[para & (XS == a)] *= 1.12 if side == "W" else 0.8
        img[para & (XS == b)] *= 0.62
    sh = (XS >= 9) & (XS <= 11) & ((YS % 16) <= 9)
    img[sh] *= 0.68                                                  # the west merlons' shadows on the walk
    return to_rows(img)


# ---------------------------------------------------------------- rugs
# A rug is any rectangle of pieces, each with the border along the sides that are the rug's outside edge, so the
# border goes round the outside and the pattern runs on across the middle. Per floor (base 1 on the planks, 31 on a
# stone tile floor, Tile001): base + 0-8, the nine pieces of a rug at least 2 x 2 (row * 3 + column: rows top /
# middle / bottom, columns left / middle / right); base + 10-12, a runner one tile high (left, middle, right);
# base + 13-15, one tile wide (top, middle, bottom); base + 16, a mat one tile square. villages.lay_rug lays them.
RUG_FLOORS = {"Plank001": 1, "Tile001": 31}
RUG_EDGES = {k: ("T" if k // 3 == 0 else "") + ("B" if k // 3 == 2 else "") + ("L" if k % 3 == 0 else "") +
             ("R" if k % 3 == 2 else "") for k in range(9)}
RUG_EDGES.update({10: "TBL", 11: "TB", 12: "TBR", 13: "LRT", 14: "LR", 15: "LRB", 16: "TBLR"})
RUG_RED, RUG_DARK, RUG_GOLD, RUG_CREAM, RUG_BLUE = (138, 40, 36), (92, 26, 26), (206, 160, 70), (226, 208, 166), (54, 78, 128)


def rug(piece, floor_tile):
    img = tile_array(p("sprites", "Tiles", floor_tile + ".png")).copy()
    edges = RUG_EDGES[piece]
    top, bottom, left, right = "T" in edges, "B" in edges, "L" in edges, "R" in edges
    x0, x1 = (4 if left else 0), (27 if right else 31)
    y0, y1 = (4 if top else 0), (27 if bottom else 31)
    m = box(x0, y0, x1, y1)
    if right:
        shadow(img, box(28, y0 + 1, 29, min(31, y1 + 1)), 0.75)
    if bottom:
        shadow(img, box(x0 + 1, 28, min(31, x1 + 1), 29), 0.75)
    img[m] = C(RUG_RED)
    # a lattice of cream diamonds with a blue heart, every 16 pixels, running on from one piece to the next
    dx, dy = (XS % 16) - 7.5, (YS % 16) - 7.5
    d = np.abs(dx) + np.abs(dy)
    img[m & (np.abs(d - 7.5) < 0.6)] = C(RUG_DARK)
    img[m & (d <= 4.0)] = C(RUG_CREAM)
    img[m & (d <= 2.0)] = C(RUG_BLUE)
    # the border: a dark band and a gold line inside it, along the outside edges only
    band = np.zeros((S, S), dtype=bool)
    gold = np.zeros((S, S), dtype=bool)
    if top:
        band |= box(x0, 4, x1, 7)
        gold |= box(x0, 6, x1, 6)
    if bottom:
        band |= box(x0, 24, x1, 27)
        gold |= box(x0, 25, x1, 25)
    if left:
        band |= box(4, y0, 7, y1)
        gold |= box(6, y0, 6, y1)
    if right:
        band |= box(24, y0, 27, y1)
        gold |= box(25, y0, 25, y1)
    img[band & m] = C(RUG_DARK)
    img[gold & m] = C(RUG_GOLD)
    # tassels on the left and right ends
    for side, ex in ((left, 2), (right, 28)):
        if side:
            for y in range(y0 + 1, y1, 3):
                img[y, ex:ex + 2] = C(RUG_CREAM)
    rng = random.Random(5100 + piece)
    img[m] *= (1 + 0.06 * smooth_noise(rng, 1, 0))[m][:, None]
    return to_rows(img)


TILES = {
    "Bed001": bed_head,
    "Bed002": bed_foot,
    "Table001": table,
    "Chair001": lambda: chair("S"),
    "Chair002": lambda: chair("N"),
    "Chair003": lambda: chair("E"),
    "Chair004": lambda: chair("W"),
    "Potted_Plant001": potted_plant,
    "Bookshelf001": bookshelf,
    "Fireplace001": fireplace,
    "Fireplace002": lambda: fireplace(south=True),
    "Fireplace003": lambda: fireplace(brick=True),
    "Stairs001": stairs_up,
    "Stairs002": stairs_down,
    "Ladder008": lambda: on_planks("Ladder001"),
    "Ladder009": lambda: on_planks("Ladder002"),
    "City_Wall001": lambda: wall_pair()[0],         # an east-west wall: its top ...
    "City_Wall004": lambda: wall_pair()[1],         # ... and its face, the row below
    "City_Wall002": city_wall_v,                    # a north-south wall, from above
    "City_Wall003": lambda: tower_pair()[0],        # a tower: its top ...
    "City_Wall005": lambda: tower_pair()[1],        # ... and its face
    "City_Gate003": lambda: gate_pair(False)[0],    # the gateway, shut: the arch ...
    "City_Gate001": lambda: gate_pair(False)[1],    # ... and the gates
    "City_Gate004": lambda: gate_pair(True)[0],     # the same, open
    "City_Gate002": lambda: gate_pair(True)[1],
}
for _f in FURNITURE_FLOORS:
    for _n in FURNITURE:
        TILES[furniture_on(_n, _f)] = (lambda f=_f, m=TILES[_n]: on_floor(f, m))
for _floor, _base in RUG_FLOORS.items():
    for _k in RUG_EDGES:
        TILES["Rug%03d" % (_base + _k)] = (lambda k=_k, f=_floor: rug(k, f))
