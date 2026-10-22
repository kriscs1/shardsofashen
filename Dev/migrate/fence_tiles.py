"""Fences as decor tiles (see-through, Tiles.ini Layer=Decor): a wooden picket fence (Wood_Fence) and wrought-iron
railings (Iron_Fence), each in the twelve pieces that build any fence line: <Kind>_Fence001-012 (PIECES).

Every piece is drawn from the sides it joins (N, E, S, W): the fence runs along the middle of the tile, east-west on the
row the posts stand on (y 21) and north-south down the middle (x 16), so the pieces meet across tile edges. A post
stands where lines meet or end. Its walk grid blocks just the fence line (the posts' row east-west, the middle column
north-south), so the ground either side can be walked on. build_cinder.py registers them (Tiles.ini) and cinder_art.py
writes the pictures."""
import numpy as np
from PIL import Image

S = 32
YS, XS = np.mgrid[0:S, 0:S]
BASE = 21           # the row the posts stand on (an east-west fence's foot)
MID = 16            # the column a north-south fence runs down
PIECES = [          # number: (sides joined, what it is)
    (1, "EW", "east-west"), (2, "NS", "north-south"),
    (3, "ES", "corner: east and south (the top left of a pen)"), (4, "SW", "corner: west and south (the top right)"),
    (5, "NE", "corner: north and east (the bottom left)"), (6, "NW", "corner: north and west (the bottom right)"),
    (7, "ESW", "a T: east, south and west"), (8, "NEW", "a T: north, east and west"),
    (9, "NES", "a T: north, east and south"), (10, "NSW", "a T: north, south and west"),
    (11, "NESW", "a crossing"), (12, "", "a post on its own (or the end of a line)"),
]
KINDS = {"Wood": "A white-capped picket fence.", "Iron": "Wrought-iron railings, black, with gilt finials."}


def name(kind, n):
    return "%s_Fence%03d" % (kind, n)


def walk(sides):
    """7 x 7 walk grid: the fence line (row 4 east-west, column 3 north-south) blocked from the middle to each side."""
    g = [["1"] * 7 for _ in range(7)]
    r, c = BASE * 7 // S, MID * 7 // S
    g[r][c] = "0"
    for x in range(7):
        if ("W" in sides and x <= c) or ("E" in sides and x >= c):
            g[r][x] = "0"
    for y in range(7):
        if ("N" in sides and y <= r) or ("S" in sides and y >= r):
            g[y][c] = "0"
    return "".join("".join(row) for row in g)


def put(img, a, m, col):
    img[m] = col
    a[m] = 255


def shade(img, m, k):
    img[m] = img[m] * k


def shadow(img, a, m, k=0.4):
    free = m & (a == 0)
    img[free] = 0
    a[free] = int(255 * k)


def spans(sides, axis):
    """The x (or y) range a fence along this axis covers in the tile, or None."""
    if axis == "x":
        lo, hi = ("W" in sides), ("E" in sides)
        return (0 if lo else MID, S - 1 if hi else MID) if (lo or hi) else None
    lo, hi = ("N" in sides), ("S" in sides)
    return (0 if lo else BASE, S - 1 if hi else BASE) if (lo or hi) else None


def wood(sides):
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    wood_c, dark, cap = np.array((168, 124, 78)), np.array((112, 78, 46)), np.array((236, 230, 214))
    ew, ns = spans(sides, "x"), spans(sides, "y")
    if ew:
        x0, x1 = ew
        shadow(img, a, (XS >= x0) & (XS <= x1) & (YS >= BASE + 1) & (YS <= BASE + 3))
        for y in (BASE - 9, BASE - 3):                                  # the two rails
            put(img, a, (XS >= x0) & (XS <= x1) & (YS >= y) & (YS <= y + 1), wood_c)
            shade(img, (XS >= x0) & (XS <= x1) & (YS == y + 1), 0.72)
        for px in range(x0 + (2 - x0 % 4) % 4, x1 + 1, 4):              # pickets every 4 pixels, pointed
            m = (XS >= px) & (XS <= px + 1) & (YS >= BASE - 12) & (YS <= BASE)
            put(img, a, m & (XS <= x1), wood_c * 1.08)
            shade(img, m & (XS == px + 1), 0.78)
            put(img, a, (XS == px) & (YS == BASE - 13) & (XS <= x1), cap)
            put(img, a, (XS >= px) & (XS <= px + 1) & (YS == BASE - 12) & (XS <= x1), cap)
    if ns:
        y0, y1 = ns
        shadow(img, a, (XS >= MID + 2) & (XS <= MID + 4) & (YS >= y0) & (YS <= y1))
        put(img, a, (XS >= MID - 2) & (XS <= MID + 1) & (YS >= y0) & (YS <= y1), dark)    # the rails, from above
        put(img, a, (XS >= MID - 1) & (XS <= MID) & (YS >= y0) & (YS <= y1), wood_c)
        for py in range(y0 + (1 - y0 % 4) % 4, y1 + 1, 4):              # the picket tops
            put(img, a, (XS >= MID - 1) & (XS <= MID) & (YS >= py) & (YS <= py + 1) & (YS <= y1), cap)
    # a post where lines meet or end
    post = (XS >= MID - 2) & (XS <= MID + 1) & (YS >= BASE - 14) & (YS <= BASE)
    shadow(img, a, (XS >= MID - 1) & (XS <= MID + 4) & (YS >= BASE + 1) & (YS <= BASE + 3))
    put(img, a, post, dark * 1.15)
    shade(img, post & (XS == MID - 2), 1.3)
    shade(img, post & (XS == MID + 1), 0.7)
    put(img, a, (XS >= MID - 2) & (XS <= MID + 1) & (YS >= BASE - 15) & (YS <= BASE - 14), cap)
    return img, a


def iron(sides):
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    black, hi, gold = np.array((34, 34, 40)), np.array((92, 94, 106)), np.array((214, 172, 60))
    ew, ns = spans(sides, "x"), spans(sides, "y")
    if ew:
        x0, x1 = ew
        shadow(img, a, (XS >= x0) & (XS <= x1) & (YS >= BASE + 1) & (YS <= BASE + 2), 0.35)
        for y in (BASE - 12, BASE - 1):                                 # the top and bottom rails
            put(img, a, (XS >= x0) & (XS <= x1) & (YS == y), black)
        for px in range(x0 + (1 - x0 % 3) % 3, x1 + 1, 3):              # bars every 3 pixels, spear tips
            put(img, a, (XS == px) & (YS >= BASE - 15) & (YS <= BASE), black)
            put(img, a, (XS == px) & (YS == BASE - 16), hi)
            if px % 6 == 1:                                             # a scroll between the rails, now and then
                put(img, a, (XS == px + 1) & (YS == BASE - 7), hi)
        put(img, a, (XS >= x0) & (XS <= x1) & (YS == BASE - 13), hi * 0.9)    # the light along the top rail
    if ns:
        y0, y1 = ns
        shadow(img, a, (XS >= MID + 1) & (XS <= MID + 2) & (YS >= y0) & (YS <= y1), 0.35)
        put(img, a, (XS == MID - 1) & (YS >= y0) & (YS <= y1), black)
        put(img, a, (XS == MID) & (YS >= y0) & (YS <= y1), black * 1.4)
        for py in range(y0 + (1 - y0 % 3) % 3, y1 + 1, 3):              # the spear tips, from above
            put(img, a, (XS >= MID - 1) & (XS <= MID) & (YS == py) & (YS <= y1), hi)
    # a stone-footed post with a gilt finial
    shadow(img, a, (XS >= MID - 1) & (XS <= MID + 4) & (YS >= BASE + 1) & (YS <= BASE + 3), 0.4)
    put(img, a, (XS >= MID - 3) & (XS <= MID + 2) & (YS >= BASE - 2) & (YS <= BASE), np.array((150, 146, 140)))
    post = (XS >= MID - 2) & (XS <= MID + 1) & (YS >= BASE - 15) & (YS <= BASE - 3)
    put(img, a, post, black * 1.2)
    shade(img, post & (XS == MID - 2), 1.8)
    ball = ((XS + 0.5 - MID) ** 2 + (YS + 0.5 - (BASE - 17)) ** 2) <= 3.2
    put(img, a, ball, gold)
    put(img, a, (XS == MID - 1) & (YS == BASE - 18), gold * 1.2)
    return img, a


def picture(kind, sides):
    img, a = (wood if kind == "Wood" else iron)(sides)
    img = np.clip(np.round(img), 0, 255).astype(np.uint8)
    a = np.clip(np.round(a), 0, 255).astype(np.uint8)
    img[a == 0] = 0
    return Image.fromarray(np.dstack([img, a]), "RGBA")


TILE_ART = {name(k, n): (lambda k=k, s=sides: picture(k, s)) for k in KINDS for n, sides, _ in PIECES}
TILE_DATA = {name(k, n): (walk(sides), "1", "", KINDS[k], "1", "150 112 70" if k == "Wood" else "40 40 46")
             for k in KINDS for n, sides, _ in PIECES}
TILE_KEYS = {name(k, n): [("Layer", "Decor")] for k in KINDS for n, _, _ in PIECES}


def preview(path):
    """A pen of each kind on grass: every piece used."""
    grass = Image.open(__import__("common").p("Sprites", "Tiles", "Grass001.png")).convert("RGBA")
    layout = [[3, 7, 1, 4], [9, 11, 1, 10], [2, 2, 12, 2], [5, 8, 1, 6]]
    out = Image.new("RGBA", (S * 9, S * 4))
    for k, kind in enumerate(KINDS):
        for y, row in enumerate(layout):
            for x, n in enumerate(row):
                out.alpha_composite(grass, ((k * 5 + x) * S, y * S))
                out.alpha_composite(picture(kind, dict((p[0], p[1]) for p in PIECES)[n]), ((k * 5 + x) * S, y * S))
    out.resize((out.size[0] * 2, out.size[1] * 2), Image.NEAREST).save(path)


if __name__ == "__main__":
    import sys
    preview(sys.argv[1])
