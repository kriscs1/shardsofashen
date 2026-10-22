"""Furnishings that give a house its trade (interiors.py lays them out): on the plank floor like interior_tiles.
  * Shelf_Goods001   shelves of jars, boxes and bolts of cloth (a shop's back wall)
  * Counter001       a shop or bank counter
  * Sacks001         sacks of grain and flour
  * Barrel002 / Crate002  a barrel and a crate indoors
  * Coin_Chest001    an iron-bound chest spilling gold (a bank)
  * Cauldron001      a black cauldron on the boil, green and bubbling (an herbalist)
  * Herb_Rack001     bundles of herbs drying on a rack
  * Potion_Shelf001  a shelf of coloured potions
  * Nets001          fishing nets and floats hung up to dry (a fisherman)
  * Fish_Barrel001   a barrel of fish
  * Candles001       a stand of candles
Merged into cave_tiles.TILES."""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from farm_tiles import S, to_rows  # noqa: E402
from interior_tiles import floor, box, ellipse, lit_box, C, WOOD, DARK_WOOD  # noqa: E402

YS, XS = np.mgrid[0:S, 0:S]


def shadow(img, x0, y0, x1, y1, k=0.6):
    img[box(x0, y0, x1, y1)] *= k


def shelf_goods():
    rng = random.Random(9101)
    img = floor()
    shadow(img, 2, 26, 30, 29)
    lit_box(img, box(2, 2, 29, 27), DARK_WOOD)
    for y0 in (4, 12, 20):                                           # three shelves
        img[box(3, y0 + 6, 28, y0 + 7)] = WOOD * 1.1
        x = 4
        while x < 26:
            w = rng.randint(2, 4)
            h = rng.randint(3, 5)
            col = C(rng.choice([(196, 80, 60), (70, 110, 170), (210, 190, 120), (120, 150, 80), (230, 220, 200),
                                (150, 100, 60)]))
            img[box(x, y0 + 6 - h, x + w - 1, y0 + 5)] = col
            img[box(x, y0 + 6 - h, x, y0 + 5)] *= 1.2
            x += w + 1
    return to_rows(np.clip(img, 0, 255))


def counter():
    img = floor()
    shadow(img, 1, 24, 31, 28)
    lit_box(img, box(0, 8, 31, 24), WOOD)                            # the front
    img[box(0, 6, 31, 10)] = WOOD * 1.3                              # the top
    img[box(0, 6, 31, 6)] *= 1.15
    for x in (4, 15, 26):                                            # panels
        img[box(x, 13, x + 4, 21)] *= 0.82
    return to_rows(np.clip(img, 0, 255))


def sacks():
    rng = random.Random(9103)
    img = floor()
    for cx, cy, r, col in ((10, 20, 7, (210, 190, 140)), (21, 19, 7, (196, 176, 128)), (15, 11, 6, (220, 204, 160))):
        shadow(img, cx - r + 2, cy + r - 2, cx + r + 2, cy + r + 1)
        m = ellipse(cx, cy, r, r + 1)
        img[m] = C(col) * (1 + 0.06 * np.array([[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)]))[m][:, None]
        img[m & (XS > cx + r // 3)] *= 0.85
        img[box(cx - 2, cy - r - 1, cx + 2, cy - r)] = C((150, 120, 70))       # the tied neck
    return to_rows(np.clip(img, 0, 255))


def barrel(fish=False):
    img = floor()
    shadow(img, 7, 26, 27, 29)
    body = box(7, 6, 24, 27)
    lit_box(img, body, C((150, 98, 52)))
    for y in (9, 17, 25):
        img[box(7, y, 24, y)] = C((70, 70, 76))                      # iron hoops
    img[box(8, 5, 23, 7)] = C((112, 72, 38))
    if fish:                                                         # silver fish packed in the top
        for x in range(9, 23, 3):
            img[box(x, 3, x + 2, 6)] = C((176, 190, 200))
            img[x + 1, 4] = C((40, 40, 50)) if x % 2 else img[x + 1, 4]
    return to_rows(np.clip(img, 0, 255))


def crate():
    img = floor()
    shadow(img, 5, 25, 29, 29)
    lit_box(img, box(5, 6, 26, 26), C((176, 132, 80)))
    for x in (5, 12, 19, 26):
        img[box(x, 6, x, 26)] *= 0.75
    img[(np.abs(XS - YS) <= 1) & box(5, 6, 26, 26)] = C((130, 92, 52))   # the brace
    return to_rows(np.clip(img, 0, 255))


def coin_chest():
    img = floor()
    shadow(img, 4, 25, 30, 29)
    lit_box(img, box(4, 10, 27, 26), C((120, 72, 40)))
    img[box(4, 8, 27, 12)] = C((140, 88, 50))                        # the lid, open
    for x in (4, 15, 27):
        img[box(x, 8, x, 26)] = C((80, 80, 86))
    rng = random.Random(9107)
    for _ in range(28):                                              # coins heaped in it and spilling out
        x, y = rng.randint(6, 25), rng.randint(9, 14)
        img[y, x] = C((240, 200, 70)) if rng.random() < 0.7 else C((200, 150, 40))
    for x, y in ((28, 26), (29, 27), (2, 27), (26, 28)):
        img[box(x - 1, y - 1, x, y)] = C((240, 200, 70))
    return to_rows(np.clip(img, 0, 255))


def cauldron():
    img = floor()
    shadow(img, 5, 26, 29, 29)
    for x in (8, 23):                                                # its legs
        img[box(x, 22, x + 1, 27)] = C((40, 40, 44))
    pot = ellipse(16, 18, 11, 8)
    img[pot] = C((44, 44, 48))
    img[pot & (XS < 12)] *= 1.4
    brew = ellipse(16, 12, 10, 3)
    img[brew] = C((80, 190, 70))
    img[ellipse(16, 12, 10, 3) & ~ellipse(16, 12, 9, 2)] = C((30, 30, 34))
    for x, y in ((12, 11), (19, 12), (15, 13)):                      # bubbles
        img[box(x, y, x + 1, y + 1)] = C((170, 240, 150))
    img[box(13, 27, 19, 29)] = C((255, 150, 50))                     # the fire under it
    img[box(15, 26, 17, 27)] = C((255, 220, 120))
    return to_rows(np.clip(img, 0, 255))


def herb_rack():
    rng = random.Random(9111)
    img = floor()
    shadow(img, 2, 26, 30, 29)
    img[box(3, 4, 4, 27)] = DARK_WOOD
    img[box(27, 4, 28, 27)] = DARK_WOOD
    for y in (5, 15):
        img[box(3, y, 28, y + 1)] = WOOD
        for x in range(6, 27, 4):                                    # bundles hanging upside down
            col = C(rng.choice([(70, 140, 60), (110, 150, 70), (150, 110, 160), (180, 160, 60)]))
            for k in range(rng.randint(5, 7)):
                img[box(x - (k // 3), y + 2 + k, x + 1 + (k // 3), y + 2 + k)] = col * (1.0 - 0.04 * k)
            img[box(x, y + 2, x + 1, y + 2)] = C((150, 110, 60))
    return to_rows(np.clip(img, 0, 255))


def potion_shelf():
    rng = random.Random(9113)
    img = floor()
    shadow(img, 3, 26, 29, 29)
    lit_box(img, box(3, 3, 28, 27), DARK_WOOD)
    for y0 in (4, 14):
        img[box(4, y0 + 8, 27, y0 + 9)] = WOOD * 1.1
        for x in range(5, 26, 4):
            col = C(rng.choice([(200, 50, 60), (70, 120, 220), (90, 190, 80), (220, 180, 60), (170, 80, 200)]))
            img[ellipse(x + 1, y0 + 6, 2, 2)] = col
            img[box(x + 1, y0 + 2, x + 1, y0 + 4)] = C((200, 210, 220))
            img[x, y0 + 5] = C((255, 255, 255))
    return to_rows(np.clip(img, 0, 255))


def nets():
    img = floor()
    shadow(img, 2, 26, 30, 29)
    img[box(2, 4, 29, 5)] = DARK_WOOD                               # the pole
    net = box(4, 6, 27, 25) & ((XS + YS) % 4 == 0) | box(4, 6, 27, 25) & ((XS - YS) % 4 == 0)
    img[net & (YS < 25 - (np.abs(XS - 16) // 4))] = C((200, 190, 160))
    for x, y in ((8, 14), (16, 18), (23, 12)):                       # cork floats
        img[ellipse(x, y, 2, 2)] = C((220, 120, 50))
    return to_rows(np.clip(img, 0, 255))


def candles():
    img = floor()
    shadow(img, 9, 25, 25, 29)
    img[box(15, 12, 16, 27)] = C((150, 120, 50))                     # the stand
    img[box(10, 26, 21, 27)] = C((150, 120, 50))
    img[box(9, 12, 22, 13)] = C((150, 120, 50))
    for x in (9, 15, 21):
        img[box(x, 6, x + 1, 11)] = C((240, 236, 220))
        img[box(x, 3, x + 1, 5)] = C((255, 200, 80))
        img[x, 2] = C((255, 240, 160))
    return to_rows(np.clip(img, 0, 255))


TILES = {"Shelf_Goods001": shelf_goods, "Counter001": counter, "Sacks001": sacks, "Barrel002": barrel,
         "Crate002": crate, "Coin_Chest001": coin_chest, "Cauldron001": cauldron, "Herb_Rack001": herb_rack,
         "Potion_Shelf001": potion_shelf, "Nets001": nets, "Fish_Barrel001": lambda: barrel(True),
         "Candles001": candles}
SOLID = "0" * 49
SMALL = "1111111" "1111111" "1100011" "1100011" "1100011" "1111111" "1111111"
TILE_DATA = {   # Walkable.Data, Show.Name, Use.Words, Examine.Info, Line.of.Sight, minimap colour
    "Shelf_Goods001": (SOLID, "1", "", "Shelves of jars, boxes and bolts of cloth.", "1", None),
    "Counter001": (SOLID, "1", "", "A worn wooden counter.", "1", None),
    "Sacks001": (SOLID, "1", "", "Sacks of grain and flour.", "1", None),
    "Barrel002": (SMALL, "1", "", "A barrel of ale. Or possibly pickles.", "1", None),
    "Crate002": (SMALL, "1", "", "A crate of goods, nailed shut.", "1", None),
    "Coin_Chest001": (SOLID, "1", "", "An iron-bound chest of coins. Don't even think about it.", "1", None),
    "Cauldron001": (SOLID, "1", "", "A cauldron, bubbling green. It smells of moss and pepper.", "1", None),
    "Herb_Rack001": (SOLID, "1", "", "Bundles of herbs hung up to dry.", "1", None),
    "Potion_Shelf001": (SOLID, "1", "", "A shelf of little bottles, every colour of the rainbow.", "1", None),
    "Nets001": (SOLID, "1", "", "Fishing nets hung up to dry, with cork floats.", "1", None),
    "Fish_Barrel001": (SMALL, "1", "", "A barrel of fresh fish. Very fresh. Very fishy.", "1", None),
    "Candles001": (SMALL, "1", "", "A stand of candles, burning low.", "1", None),
}
