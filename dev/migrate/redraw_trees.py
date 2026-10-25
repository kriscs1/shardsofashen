"""The trees in one style: Tree001, Tree002 and the tall pine (Pine_Tree001, with its top Pine_Tree002 on the Over
layer in the tile above) drawn as the oak, willow and yew are (cave_tiles.py's trunk and leafy crown, a soft shadow on
the ground), and the pine as the snow pine is, without the snow. Drawn on grass, then cut off it as the editor's
"Split props off their floors" does (dsedit/decor.py split: see-through, the shadow see-through dark). Run it again
to draw them again.

  python -I "dev\\migrate\\redraw_trees.py"

  Tree001         the common tree: a round, leafy, mid-green crown on a short trunk (Woodcutting 1)
  Tree002         its taller cousin: a higher, darker, narrower crown on a longer trunk
  Pine_Tree001/2  a tall pine, two tiles high: its trunk and lower boughs, and its top (drawn over the player)
"""
import os
import random
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import sprite_kit as K  # noqa: E402
from cave_tiles import copy_tile, _leafy, _trunk  # noqa: E402
from dsedit.decor import split  # noqa: E402

TILES = os.path.join(ROOT, "sprites", "Tiles")
NEEDLES, NEEDLES_DK, NEEDLES_LT = (34, 74, 46), (22, 54, 34), (52, 98, 62)     # (the snow pine's greens)


def common_tree():
    img = copy_tile("Grass001")
    rng = random.Random(701)
    _trunk(img, 14, 18, 19, 29, (138, 96, 56), (104, 70, 38), (66, 42, 20))
    _leafy(img, rng, 16, 12, 12, 10)                       # (cave_tiles' own greens: the bushes' and trees' green)
    return img


def tall_tree():
    img = copy_tile("Grass001")
    rng = random.Random(712)
    _trunk(img, 14, 17, 17, 29, (128, 98, 70), (96, 72, 50), (60, 44, 30))
    _leafy(img, rng, 16, 10, 10, 10, dark=(20, 52, 22), mid=(40, 88, 38), light=(70, 128, 58), outline=(12, 32, 12))
    return img


def tall_pine():
    """A pine 64 px high: tiers of boughs, each wider than the one above, lit from the left; a trunk; a shadow."""
    img = copy_tile("Grass001") + copy_tile("Grass001")          # (two tiles of grass, one over the other)
    rng = random.Random(733)
    for y in range(56, 64):                                       # its shadow on the ground
        for x in range(32):
            dx, dy = (x + 0.5 - 18) / 11.0, (y + 0.5 - 60) / 3.6
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.mix(img[y][x], (20, 34, 10), 0.45)
    for x in range(14, 18):                                       # the trunk
        for y in range(50, 62):
            img[y][x] = (92, 60, 34) if x < 16 else (70, 44, 24)
    for top, half in ((3, 4), (11, 7), (20, 9), (30, 11), (40, 13)):
        for y in range(top, top + 13):
            w = int(half * (y - top) / 12.0) + 1
            for x in range(16 - w, 16 + w):
                if 0 <= x < 32 and y < 55:
                    c = NEEDLES if x < 16 else NEEDLES_DK
                    if x in (16 - w, 16 + w - 1) or y == top + 12:
                        c = (14, 38, 24)                          # (the boughs' edge)
                    elif x < 15 and rng.random() < 0.18:
                        c = NEEDLES_LT
                    img[y][x] = c
    return img


def cut(img, floor_rows):
    """The picture, cut off its grass: see-through, the shadow see-through dark."""
    t = np.array(img, dtype=np.int32)
    b = np.array(floor_rows, dtype=np.int32)
    rgba, _, _ = split(t, b)
    return Image.fromarray(rgba, "RGBA")


def main():
    grass = copy_tile("Grass001")
    cut(common_tree(), grass).save(os.path.join(TILES, "Tree001.png"))
    cut(tall_tree(), grass).save(os.path.join(TILES, "Tree002.png"))
    pine = tall_pine()
    cut(pine[32:], grass).save(os.path.join(TILES, "Pine_Tree001.png"))      # (the trunk and lower boughs)
    cut(pine[:32], grass).save(os.path.join(TILES, "Pine_Tree002.png"))      # (its top, on the Over layer above)
    print("Drew Tree001, Tree002 and the tall pine")


if __name__ == "__main__":
    main()
