"""Furniture you can tell at a glance. At 32 px, on a plank floor, the shelves were a blur of one-pixel books and jars
in a frame the floor's own brown, and the wooden pieces melted into the boards. So:

  * The shelves are drawn again, simple and bold: a dark walnut frame with an outline, three shelves, a few chunky
    things on each in strong colours - Bookshelf001 (books), Shelf_Goods001 (jars, boxes, a sack), Potion_Shelf001
    (round bottles), Herb_Rack001 (bunches of herbs hung to dry).
  * The wooden pieces get a dark outline, as the newer pictures have (the cats, the trees, the fire): chairs, the
    table, the counter, benches, barrels, crates, sacks, the coin chest. From their originals, kept in
    Dev\\Archive\\Sprites\\Furniture, so running it again gives the same.

  python -I "Dev\\migrate\\clearer_furniture.py"
"""
import os
import random
import shutil

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TILES = os.path.join(ROOT, "Sprites", "Tiles")
ARCHIVE = os.path.join(ROOT, "Dev", "Archive", "Sprites", "Furniture")
OUTLINE = (34, 20, 12, 255)
FRAME, FRAME_LT, FRAME_DK, BACK = (92, 56, 30), (128, 84, 48), (62, 36, 18), (40, 24, 14)
OUTLINED = ["Table001", "Chair001", "Chair002", "Chair003", "Chair004", "Chair101", "Chair103", "Counter001",
            "Bench001", "Bench002", "Bench003", "Barrel001", "Barrel002", "Cellar_Barrel001", "Fish_Barrel001",
            "Suspicious_Barrel001", "Crate001", "Crate002", "Cellar_Crate001", "Cargo_Stack001", "Sacks001",
            "Coin_Chest001"]


# ----------------------------------------------------------------- the outline, round what's solid
def outline(img):
    """A 1 px dark line just outside the solid part of the picture (not round its see-through shadow)."""
    a = np.array(img.convert("RGBA"))
    solid = a[..., 3] >= 160
    near = np.zeros_like(solid)
    near[1:, :] |= solid[:-1, :]
    near[:-1, :] |= solid[1:, :]
    near[:, 1:] |= solid[:, :-1]
    near[:, :-1] |= solid[:, 1:]
    edge = near & ~solid
    a[edge] = OUTLINE
    return Image.fromarray(a, "RGBA")


# ----------------------------------------------------------------- the shelves
def shelf_frame():
    """The case: dark walnut, its edges lit and shaded, three shelves; returns (image, draw, the shelves' tops)."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 30, 28, 31], fill=(0, 0, 0, 90))                 # (its shadow on the floor)
    d.rectangle([4, 1, 27, 30], fill=FRAME)
    d.rectangle([6, 3, 25, 28], fill=BACK)                           # (the dark inside)
    d.line([(4, 1), (4, 30)], fill=FRAME_LT)
    d.line([(27, 1), (27, 30)], fill=FRAME_DK)
    d.line([(4, 1), (27, 1)], fill=FRAME_LT)
    tops = [11, 20, 29]                                              # (where each shelf's things stand)
    for y in tops[:-1]:
        d.rectangle([6, y, 25, y + 1], fill=FRAME)
        d.line([(6, y), (25, y)], fill=FRAME_LT)
    return img, d, tops


def bookshelf():
    img, d, tops = shelf_frame()
    rng = random.Random(41)
    colours = [(178, 40, 40), (46, 84, 168), (54, 128, 64), (204, 160, 52), (120, 52, 130)]
    for i, base in enumerate(tops):
        x = 7
        k = i
        while x < 24:
            w, h = rng.choice((2, 3, 3)), rng.randint(5, 7)
            if x + w > 25:
                break
            c = colours[k % len(colours)]
            d.rectangle([x, base - h, x + w - 1, base - 1], fill=c)
            d.line([(x, base - h), (x, base - 1)], fill=tuple(min(255, v + 50) for v in c))   # (lit spine edge)
            d.line([(x, base - 3), (x + w - 1, base - 3)], fill=(236, 214, 150))           # (a gilt band)
            x += w + (1 if rng.random() < 0.25 else 0)
            k += 1
    return outline(img)


def goods_shelf():
    img, d, tops = shelf_frame()
    jar, lid = (226, 214, 180), (150, 104, 60)
    for base in tops:
        d.rectangle([8, base - 6, 12, base - 1], fill=jar)                # a jar, its lid
        d.rectangle([8, base - 7, 12, base - 7], fill=lid)
        d.line([(8, base - 6), (8, base - 1)], fill=(250, 244, 222))
        d.rectangle([15, base - 5, 20, base - 1], fill=(170, 116, 64))    # a box
        d.line([(15, base - 3), (20, base - 3)], fill=(110, 70, 36))
        d.ellipse([21, base - 6, 25, base], fill=(204, 182, 130))         # a sack
    return outline(img)


def potion_shelf():
    img, d, tops = shelf_frame()
    colours = [(170, 60, 200), (220, 50, 60), (60, 120, 230), (70, 190, 90), (240, 180, 50)]
    k = 0
    for base in tops:
        for x in (8, 14, 20):
            c = colours[k % len(colours)]
            d.ellipse([x, base - 5, x + 4, base - 1], fill=c)             # the round bottle
            d.rectangle([x + 1, base - 7, x + 3, base - 5], fill=(200, 220, 230))   # its neck
            d.point((x + 1, base - 4), fill=(255, 255, 255))              # (a glint)
            k += 1
    return outline(img)


def herb_rack():
    img, d, tops = shelf_frame()
    greens = [(70, 150, 60), (120, 170, 70), (90, 130, 50), (150, 110, 170)]
    for i, base in enumerate(tops):
        top = base - 8
        for j, x in enumerate((8, 13, 18, 23)):                            # bunches hung upside down to dry
            c = greens[(i + j) % len(greens)]
            d.line([(x + 1, top), (x + 1, top + 1)], fill=(190, 160, 110))   # (the string)
            d.polygon([(x - 1, top + 2), (x + 3, top + 2), (x + 1, top + 7)], fill=c)
            d.point((x + 1, top + 3), fill=tuple(min(255, v + 50) for v in c))
    return outline(img)


SHELVES = {"Bookshelf001": bookshelf, "Shelf_Goods001": goods_shelf, "Potion_Shelf001": potion_shelf,
           "Herb_Rack001": herb_rack}


def main():
    os.makedirs(ARCHIVE, exist_ok=True)
    for name in list(SHELVES) + OUTLINED:                            # (the originals kept, to work from again)
        keep = os.path.join(ARCHIVE, name + ".png")
        if not os.path.exists(keep) and os.path.exists(os.path.join(TILES, name + ".png")):
            shutil.copy(os.path.join(TILES, name + ".png"), keep)
    for name, draw in SHELVES.items():
        draw().save(os.path.join(TILES, name + ".png"))
    n = 0
    for name in OUTLINED:
        keep = os.path.join(ARCHIVE, name + ".png")
        if os.path.exists(keep):
            outline(Image.open(keep)).save(os.path.join(TILES, name + ".png"))
            n += 1
    print("Shelves drawn again: %d; outlined: %d" % (len(SHELVES), n))


if __name__ == "__main__":
    main()
