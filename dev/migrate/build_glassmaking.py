"""Glassmaking sprites: Spade (dig sand), Sand and Glass, in sprites\\Entities (the LB sprite format, via sprite_kit).

The chain: Dig a sand tile with a Spade -> Sand; smelt Sand at a Furnace (CRAFT-Smelting) -> Glass; make Glass into an
Empty_Vial at a Workbench (CRAFT-Crafting). The data (Entities.ini, Tiles.ini Sand001 Use.Words, ItemRacks.ini,
Gathering.ini, data\\Scripts\\Dig Sand.txt) was added by hand. Run: python dev\\migrate\\build_glassmaking.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K  # noqa: E402

OUTLINE = (40, 30, 22)


def inside(poly, x, y):
    """Point in polygon (even-odd), for pixel centres."""
    n = len(poly)
    c = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def spade():
    img = K.new()
    wood, light, dark = (150, 104, 58), (190, 142, 88), (98, 66, 34)
    # Handle (top-left to the blade) with a T grip
    K.line(img, 7, 5, 18, 16, light)
    K.line(img, 8, 5, 19, 16, wood)
    K.line(img, 8, 6, 19, 17, dark)
    K.line(img, 4, 7, 10, 1, dark)
    K.line(img, 5, 7, 11, 1, wood)
    # Blade: a rounded scoop pointing down and right, lit from the top left
    blade = [(17, 17), (22, 14), (28, 21), (27, 27), (21, 28), (15, 22)]
    for y in range(32):
        for x in range(32):
            if inside(blade, x + 0.5, y + 0.5):
                k = (x - 22) + (y - 21)
                c = (205, 208, 214) if k < -4 else ((112, 114, 122) if k > 6 else (165, 168, 176))
                K.put(img, x, y, c)
    K.line(img, 18, 18, 23, 15, (232, 234, 238))  # The blade's bright top edge
    return K.outline_img(img, OUTLINE)


def sand():
    img = K.new()
    rng = random.Random(7)
    K.shaded_ellipse(img, 16, 23, 12, 6.5, (214, 186, 120), (240, 218, 160), (172, 142, 88), rng=rng, noise=0.15)
    K.shaded_ellipse(img, 15, 19, 7.5, 5, (220, 192, 128), (244, 224, 168), (180, 150, 94), rng=rng, noise=0.15)
    for _ in range(14):  # Grains
        x, y = rng.randint(6, 26), rng.randint(15, 28)
        if K.get(img, x, y) is not None:
            K.put(img, x, y, (150, 120, 72) if rng.random() < 0.6 else (250, 236, 190))
    return K.centre_bottom(K.outline_img(img, (112, 88, 50)), 29)


def glass():
    """A slab of glass in perspective: pale top, blue-green front, darker side and a glint."""
    img = K.new()
    top, front, side = (214, 240, 246), (160, 208, 226), (108, 160, 186)
    ox, oy = 7, 12
    for y in range(11):
        for x in range(18):
            c = None
            if y <= 4 and 4 - y <= x <= 17 - y:
                c = top
            elif y >= 5 and x <= 13:
                c = front
            elif y >= 5 and 14 <= x <= 17 - max(0, y - 6):
                c = side
            elif 1 <= y <= 4 and 18 - y <= x <= 17:
                c = side
            if c is not None:
                K.put(img, ox + x, oy + y, c)
    for x, y in ((8, 1), (9, 1), (10, 1), (7, 2), (8, 2), (3, 7), (3, 8), (4, 9)):  # Glints
        K.put(img, ox + x, oy + y, (255, 255, 255))
    for x in range(1, 13):  # Where the top meets the front
        K.put(img, ox + x, oy + 5, (196, 230, 240))
    return K.centre_bottom(K.outline_img(img, (62, 104, 126)), 28)


def main():
    made = []
    for name, img in (("Spade", spade()), ("Sand", sand()), ("Glass", glass())):
        if K.save("Entities", name, img):
            made.append(name)
    print("Glassmaking sprites written:", ", ".join(made) if made else "none (unchanged)")


if __name__ == "__main__":
    main()
