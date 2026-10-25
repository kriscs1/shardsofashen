"""King Tyron's palace on the Royal Isle (build_palace.py): its floors, furniture and garden pieces. Used by
build_tiles.py through cave_tiles.TILES; each function returns a 32x32 opaque image (rows of (r, g, b)), lit from the
top left like the other tiles.

  * Paving001: pale dressed flagstones (the causeway, the royal road and the courtyard). Seamless.
  * Marble001: polished marble in cream and grey squares (the throne hall). Seamless.
  * Carpet001: the royal red runner with gold edges, on marble, running north-south (seamless that way).
  * Carpet002: the throne dais, red carpet edged in gold all round.
  * Throne001: the gilded throne with its red cushion, on the dais.
  * Pillar001: a marble column (base, fluted shaft, capital) on the marble floor.
  * Banner001: a royal blue banner with a gold crown, hanging on the stone wall (Stone_Wall001).
  * Wall_Torch001: an iron sconce with a burning torch on the stone wall, the stones lit round it.
  * Statue001 / Statue002: a knight of stone with sword and shield on a plinth, on grass / on the paving.
  * Fountain001: a round stone basin of clear water with a spout, on the paving.
  * Hedge001: a clipped box hedge on grass.
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402
from farm_tiles import S, to_rows, smooth_noise, tile_array  # noqa: E402
from interior_tiles import C, box, ellipse, lit_box, shadow, YS, XS  # noqa: E402

GOLD = (222, 176, 64)
GOLD_DK = (150, 108, 32)
RED = (150, 28, 34)
RED_LT = (186, 46, 48)
BLUE = (40, 64, 150)


def sprite(name):
    return tile_array(p("sprites", "Tiles", name + ".png")).copy()


def stone_wall():
    return sprite("Stone_Wall001")


def grass():
    return sprite("Grass001")


# ---------------------------------------------------------------- floors
def paving():
    rng = random.Random(7101)
    img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = (184, 176, 160)
    img += smooth_noise(rng, 8, 1)[:, :, None]
    # flags in running bond: 16 x 8, every other course shifted by 8 (wraps, so it is seamless)
    course = YS // 8
    xs = (XS + (course % 2) * 8) % 16
    joint = (YS % 8 == 7) | (xs == 15)
    for c in range(4):                                  # each course's flags a little lighter or darker
        for k in range(2):
            m = (course == c) & (((XS + (c % 2) * 8) % 32) // 16 == k)
            img[m] *= 0.94 + 0.12 * rng.random()
    img[joint] = img[joint] * 0.62
    img[(YS % 8 == 0) & ~joint] *= 1.07                 # the lit top edge of each flag
    return to_rows(img)


def marble_floor():
    rng = random.Random(7102)
    img = np.empty((S, S, 3), dtype=np.float32)
    check = ((XS // 16) + (YS // 16)) % 2 == 0
    img[check] = (232, 226, 212)
    img[~check] = (176, 172, 168)
    vein = smooth_noise(rng, 1, 3)
    img[:, :] *= (1 + 0.05 * vein)[:, :, None]
    for _ in range(5):                                  # a few fine veins
        x, y = rng.randrange(S), rng.randrange(S)
        for t in range(10):
            img[(y + t // 2) % S, (x + t) % S] *= 0.9
    img[(XS % 16 == 15) | (YS % 16 == 15)] *= 0.8
    img[(XS % 16 == 0) | (YS % 16 == 0)] *= 1.05
    return img


def marble():
    return to_rows(marble_floor())


def carpet_runner():
    img = marble_floor()
    shadow(img, box(27, 0, 27, 31), 0.75)
    rng = random.Random(7103)
    m = box(5, 0, 26, 31)
    img[m] = C(RED)
    img[m] *= (1 + 0.06 * smooth_noise(rng, 1, 1))[m][:, None]
    img[box(5, 0, 6, 31) | box(25, 0, 26, 31)] = C(GOLD)            # gold edges
    img[box(8, 0, 8, 31) | box(23, 0, 23, 31)] = C(GOLD_DK)
    diamond = (np.abs(XS - 15.5) + np.abs((YS % 16) - 7.5)) <= 4     # a gold lozenge every half tile
    img[diamond & box(9, 0, 22, 31)] = C(RED_LT)
    img[((np.abs(XS - 15.5) + np.abs((YS % 16) - 7.5)) <= 1.5)] = C(GOLD)
    return to_rows(img)


def dais(img=None):
    rng = random.Random(7104)
    if img is None:
        img = np.empty((S, S, 3), dtype=np.float32)
    img[:, :] = C(RED)
    img *= (1 + 0.06 * smooth_noise(rng, 1, 1))[:, :, None]
    edge = ~box(2, 2, 29, 29)
    img[edge] = C(GOLD)
    img[box(2, 2, 29, 2) | box(2, 2, 2, 29)] = C(RED_LT)
    img[box(3, 29, 29, 29) | box(29, 3, 29, 29)] = C((96, 16, 20))
    return img


def carpet_dais():
    return to_rows(dais())


# ---------------------------------------------------------------- the throne
def throne():
    img = dais()
    shadow(img, box(8, 6, 27, 30), 0.55)                              # its shadow on the dais
    back = box(7, 2, 24, 18) & ~(((XS + 0.5 - 15.5) / 9.5) ** 2 + ((YS + 0.5 - 2) / 5.0) ** 2 > 1) | box(7, 6, 24, 18)
    lit_box(img, back, GOLD, top=1.25, bottom=0.6)
    img[box(10, 7, 21, 17)] = C(RED)                                  # the padded back
    img[box(10, 7, 21, 7) | box(10, 7, 10, 17)] = C(RED_LT)
    for x, y in ((12, 10), (15, 10), (18, 10), (13, 14), (16, 14)):
        img[y, x] = C(GOLD)                                           # buttons
    crown = box(12, 0, 19, 3)                                         # a crown on the top rail
    img[crown & ((XS - 12) % 3 != 1) | box(12, 2, 19, 3)] = C((255, 214, 90))
    img[1, 15] = C((60, 140, 220))
    seat = box(6, 18, 25, 23)
    lit_box(img, seat, GOLD, top=1.3, bottom=0.6)
    img[box(9, 18, 22, 21)] = C(RED_LT)                               # the cushion
    lit_box(img, box(5, 12, 7, 26), GOLD_DK, top=1.2, bottom=0.6)    # arms and legs
    lit_box(img, box(24, 12, 26, 26), GOLD_DK, top=1.2, bottom=0.6)
    lit_box(img, box(8, 24, 10, 28), GOLD_DK)
    lit_box(img, box(21, 24, 23, 28), GOLD_DK)
    return to_rows(img)


def pillar():
    img = marble_floor()
    shadow(img, ellipse(20, 28, 10, 4), 0.6)
    lit_box(img, box(7, 25, 24, 30), (214, 208, 196), top=1.2, bottom=0.6)        # the base
    shaft = box(10, 6, 21, 25)
    img[shaft] = C((236, 232, 222))
    shade = np.clip((XS - 10) / 11.0, 0, 1)                                          # lit from the left
    img[shaft] *= (1.08 - 0.42 * shade)[shaft][:, None]
    img[shaft & ((XS - 10) % 3 == 2)] *= 0.86                                        # flutes
    lit_box(img, box(7, 1, 24, 6), (220, 214, 202), top=1.2, bottom=0.62)          # the capital
    img[box(8, 4, 23, 4)] = C(GOLD)
    return to_rows(img)


# ---------------------------------------------------------------- on the walls
def banner():
    img = stone_wall()
    shadow(img, box(10, 3, 25, 29), 0.6)
    lit_box(img, box(6, 1, 25, 3), (110, 74, 40))                    # the pole
    img[box(5, 1, 6, 3) | box(25, 1, 26, 3)] = C(GOLD)
    cloth = box(8, 3, 23, 24) | (box(8, 24, 23, 30) & (np.abs(XS - 15.5) >= (YS - 24) * 1.3))
    img[cloth] = C(BLUE)
    img[cloth] *= (1.0 + 0.12 * np.sin((XS + 0.5) / 2.5))[cloth][:, None]           # folds
    img[cloth & (box(8, 3, 9, 30) | box(22, 3, 23, 30))] = C(GOLD)
    crown = box(11, 12, 20, 16) | (box(11, 8, 20, 11) & ((XS - 11) % 4 < 2))
    img[crown] = C(GOLD)
    img[box(11, 16, 20, 16)] = C(GOLD_DK)
    img[10, 15] = img[10, 16] = C((220, 40, 40))
    return to_rows(img)


def wall_torch():
    img = stone_wall()
    glow = ellipse(16, 10, 15, 13)
    d = np.sqrt((XS + 0.5 - 16) ** 2 + (YS + 0.5 - 10) ** 2)
    img[glow] = img[glow] + (C((255, 160, 70)) - img[glow]) * np.clip(0.45 - d / 30, 0, 1)[glow][:, None]
    lit_box(img, box(13, 18, 18, 21), (70, 66, 64))                  # the bracket
    lit_box(img, box(15, 21, 16, 27), (62, 58, 56))
    lit_box(img, box(14, 12, 17, 18), (120, 80, 44))                 # the torch
    for x, top, col in ((14, 7, (255, 120, 40)), (15, 4, (255, 180, 60)), (16, 5, (255, 200, 80)), (17, 8, (240, 110, 30))):
        for y in range(top, 12):
            img[y, x] = C(col)
    img[box(15, 8, 16, 11)] = C((255, 240, 170))
    return to_rows(img)


# ---------------------------------------------------------------- the gardens and courtyard
def statue(on_paving=False):
    img = np.array(paving(), dtype=np.float32) if on_paving else grass()
    shadow(img, ellipse(21, 28, 11, 4), 0.55)
    lit_box(img, box(6, 22, 25, 30), (168, 162, 152), top=1.2, bottom=0.6)          # the plinth
    img[box(6, 25, 25, 25)] *= 0.85
    stone = (196, 192, 184)
    lit_box(img, box(12, 10, 19, 21), stone)                                          # body and legs
    img[box(15, 16, 16, 21)] *= 0.75
    lit_box(img, ellipse(15.5, 6.5, 3.6, 3.8), stone)                                # helmeted head
    img[box(13, 6, 18, 6)] *= 0.6                                                     # visor slit
    img[box(15, 1, 16, 3)] = C((176, 172, 164))                                       # crest
    lit_box(img, ellipse(9.5, 15, 4.2, 5.5), (180, 176, 168))                        # the shield
    img[box(9, 11, 10, 19) | box(6, 14, 13, 15)] *= 0.78
    lit_box(img, box(21, 3, 22, 18), (210, 210, 214))                                 # the sword, point up
    lit_box(img, box(19, 17, 24, 18), (176, 172, 164))
    img[box(20, 10, 21, 13)] = C(stone)                                               # the hand on the hilt
    return to_rows(img)


def fountain():
    img = np.array(paving(), dtype=np.float32)
    shadow(img, ellipse(17.5, 18, 15.5, 13), 0.6)
    rim = ellipse(15.5, 16, 14.5, 13)
    lit_box(img, rim, (190, 184, 172), top=1.2, bottom=0.65)
    water = ellipse(15.5, 16.5, 11.5, 10)
    rng = random.Random(7105)
    img[water] = C((70, 130, 190))
    img[water] *= (1 + 0.1 * smooth_noise(rng, 1, 1))[water][:, None]
    ring = water & ~ellipse(15.5, 16.5, 8, 7) & ellipse(15.5, 16.5, 9, 8)
    img[ring] = C((150, 200, 236))                                    # ripples
    lit_box(img, ellipse(15.5, 15, 3.5, 3.5), (200, 194, 182))        # the spout's column
    for (x, y) in ((15, 7), (16, 7), (14, 8), (17, 8), (13, 10), (18, 10), (12, 12), (19, 12), (15, 9), (16, 9),
                   (15, 10), (16, 10), (15, 11), (16, 11)):
        img[y, x] = C((210, 236, 255))                               # the jet, falling both ways
    img[box(15, 5, 16, 6)] = C((240, 250, 255))
    return to_rows(img)


def hedge():
    img = grass()
    rng = random.Random(7106)
    shadow(img, box(4, 6, 31, 31) & ellipse(18, 19, 15, 14), 0.55)
    body = box(2, 4, 29, 27)
    leaf = (52, 108, 50)
    img[body] = C(leaf)
    img[body] *= (1 + 0.22 * smooth_noise(rng, 1, 0))[body][:, None]
    top = box(2, 4, 29, 15)                                           # the clipped top catches the light
    img[top] *= 1.18
    img[box(2, 4, 29, 4) | box(2, 4, 2, 27)] *= 1.15
    img[box(2, 27, 29, 27) | box(29, 4, 29, 27)] *= 0.6
    img[box(2, 16, 29, 16)] *= 0.8
    return to_rows(img)


TILES = {
    "Paving001": paving,
    "Marble001": marble,
    "Carpet001": carpet_runner,
    "Carpet002": carpet_dais,
    "Throne001": throne,
    "Pillar001": pillar,
    "Banner001": banner,
    "Wall_Torch001": wall_torch,
    "Statue001": statue,
    "Statue002": lambda: statue(True),
    "Fountain001": fountain,
    "Hedge001": hedge,
}
