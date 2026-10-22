"""Decor that comes in sets, and which piece of a set each tile is.

* Rugs are decor (see-through round their edges, so they lie on any floor): two styles, the red Rug and the blue
  Woven_Rug, each in 16 pieces <Style>001-009 (a 3 x 3 rug of any size: corners, edges, the middle) and 011-017 (a
  runner one tile wide, and a mat on its own). RUG_EDGES (interior_tiles.py) says which sides of each piece are edges.
  The old rugs drawn on stone tiles (Rug031-047) are the same rugs on Tile001 now (decor_map.json).
* Potted plants: five different plants, Potted_Plant001-005 (PLANTS). The builders put down Potted_Plant001; the maps
  get one of the five (common.DECOR_VARIANTS). The copies once drawn against each wall are gone: they're the one pot.
* Sets: Data\\TileSets.ini lists the tiles that fit together (a roof, a rug, a fence, the thin walls round a room) laid
  out as they go, and each tile's Tiles.ini Piece= says which piece it is ("corner: top left"). The editor's palette
  shows the set with the piece marked when you point at one. SETS / PIECES here make both (roofs, thin walls, rugs,
  fences, plants); a set or piece you change in the files is kept (GEN)."""
import os
import random

import numpy as np
from PIL import Image

import fence_tiles as F
from common import p, write_image, write_generated

S = 32
YS, XS = np.mgrid[0:S, 0:S]
RUG_EDGES = {k: ("T" if k // 3 == 0 else "") + ("B" if k // 3 == 2 else "") + ("L" if k % 3 == 0 else "") +
             ("R" if k % 3 == 2 else "") for k in range(9)}
RUG_EDGES.update({10: "TBL", 11: "TB", 12: "TBR", 13: "LRT", 14: "LR", 15: "LRB", 16: "TBLR"})
RUG_PIECES = {**{k: "%s %s" % (("top", "middle", "bottom")[k // 3], ("left", "middle", "right")[k % 3])
                 for k in range(9)},
              10: "runner (east-west): left end", 11: "runner (east-west): middle", 12: "runner (east-west): right end",
              13: "runner (north-south): top end", 14: "runner (north-south): middle",
              15: "runner (north-south): bottom end", 16: "a mat on its own"}
RUG_PIECES[4] = "the middle"
RUG_STYLES = {"Rug": "A woven rug, warm underfoot.", "Woven_Rug": "A blue woven rug, striped in ochre and cream."}
RUG_LAYOUT = [[0, 1, 2, 13], [3, 4, 5, 14], [6, 7, 8, 15], [10, 11, 12, 16]]     # (the set as the editor shows it)


def rug_name(style, k):
    return "%s%03d" % (style, k + 1)


def C(c):
    return np.array(c, dtype=np.float32)


def box(x0, y0, x1, y1):
    return (XS >= x0) & (XS <= x1) & (YS >= y0) & (YS <= y1)


def ellipse(cx, cy, rx, ry):
    return ((XS + 0.5 - cx) / rx) ** 2 + ((YS + 0.5 - cy) / ry) ** 2 <= 1


class Canvas:
    """A see-through tile to draw on: colour (S, S, 3) and alpha (S, S)."""
    def __init__(self):
        self.img = np.zeros((S, S, 3), dtype=np.float32)
        self.a = np.zeros((S, S), dtype=np.float32)

    def put(self, m, col):
        self.img[m] = col
        self.a[m] = 255

    def shade(self, m, k):
        self.img[m] *= k

    def shadow(self, m, k=0.4):
        """A shadow on the floor (only where nothing is drawn): black, k of it."""
        free = m & (self.a == 0)
        self.img[free] = 0
        self.a[free] = 255 * k

    def image(self):
        img = np.clip(np.round(self.img), 0, 255).astype(np.uint8)
        a = np.clip(np.round(self.a), 0, 255).astype(np.uint8)
        img[a == 0] = 0
        return Image.fromarray(np.dstack([img, a]), "RGBA")


def smooth_noise(rng, blur):
    n = np.array([[rng.uniform(-1, 1) for _ in range(S)] for _ in range(S)], dtype=np.float32)
    for _ in range(blur):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5
    return n / max(1e-6, np.abs(n).max())


# ------------------------------------------------------------------ rugs
def rug(style, piece):
    c = Canvas()
    edges = RUG_EDGES[piece]
    top, bottom, left, right = "T" in edges, "B" in edges, "L" in edges, "R" in edges
    x0, x1 = (4 if left else 0), (27 if right else 31)
    y0, y1 = (4 if top else 0), (27 if bottom else 31)
    m = box(x0, y0, x1, y1)
    if right:
        c.shadow(box(28, y0 + 1, 29, min(31, y1 + 1)), 0.25)
    if bottom:
        c.shadow(box(x0 + 1, 28, min(31, x1 + 1), 29), 0.25)
    band, line = np.zeros((S, S), bool), np.zeros((S, S), bool)
    for on, b, l_ in ((top, box(x0, 4, x1, 7), box(x0, 6, x1, 6)), (bottom, box(x0, 24, x1, 27), box(x0, 25, x1, 25)),
                      (left, box(4, y0, 7, y1), box(6, y0, 6, y1)), (right, box(24, y0, 27, y1), box(25, y0, 25, y1))):
        if on:
            band |= b
            line |= l_
    if style == "Rug":                  # red, a lattice of cream diamonds with blue hearts; tassels at the sides
        c.put(m, C((138, 40, 36)))
        d = np.abs((XS % 16) - 7.5) + np.abs((YS % 16) - 7.5)
        c.put(m & (np.abs(d - 7.5) < 0.6), C((92, 26, 26)))
        c.put(m & (d <= 4.0), C((226, 208, 166)))
        c.put(m & (d <= 2.0), C((54, 78, 128)))
        c.put(band & m, C((92, 26, 26)))
        c.put(line & m, C((206, 160, 70)))
        for side, ex in ((left, 2), (right, 28)):
            if side:
                for y in range(y0 + 1, y1, 3):
                    c.put(box(ex, y, ex + 1, y), C((226, 208, 166)))
    else:                               # blue, ochre and cream stripes with rust chevrons; fringes at the ends
        navy, ochre, cream, rust = C((44, 62, 108)), C((200, 152, 66)), C((226, 214, 180)), C((150, 64, 42))
        c.put(m, navy)
        yy = YS % 16
        c.put(m & ((yy == 0) | (yy == 1)), cream)
        c.put(m & (yy == 3), ochre)
        c.put(m & (yy == 13), ochre)
        r, xx = yy - 6, XS % 8                                          # a band of zigzags between the stripes
        c.put(m & (r >= 0) & (r <= 3) & ((xx == r) | (xx == 7 - r)), rust)
        c.put(m & (r >= 0) & (r <= 3) & ((xx == r + 1) | (xx == 6 - r)) & (r < 3), C((120, 150, 190)))
        c.put(band & m, rust)
        c.put(line & m, cream)
        for side, ey in ((top, 2), (bottom, 28)):
            if side:
                for x in range(x0 + 1, x1, 3):
                    c.put(box(x, ey, x, ey + 1), cream)
    rng = random.Random((5100 if style == "Rug" else 5300) + piece)
    tex = 1 + 0.06 * smooth_noise(rng, 1)
    c.img[c.a == 255] *= tex[c.a == 255][:, None]
    return c.image()


# ------------------------------------------------------------------ potted plants
def pot(c, kind):
    """The pot, standing at the bottom of the tile, and its shadow."""
    c.shadow(ellipse(20, 26, 9, 4), 0.4)
    if kind == "tub":                               # a wooden tub: staves and two iron hoops
        body = box(9, 19, 22, 29)
        c.put(body, C((132, 88, 52)))
        for x in range(10, 23, 3):
            c.shade(body & (XS == x), 0.72)
        c.put(body & ((YS == 21) | (YS == 27)), C((70, 66, 64)))
        c.shade(body & (XS >= 20), 0.8)
        c.put(box(9, 18, 22, 18), C((150, 104, 62)))
        return
    shape = {"terracotta": 6, "stone": 6.5, "glazed": 5.5, "cream": 4.5}[kind]
    col = {"terracotta": (182, 94, 58), "stone": (140, 138, 132), "glazed": (60, 96, 150),
           "cream": (222, 210, 182)}[kind]
    top = 18 if kind != "cream" else 21
    body = (YS >= top) & (YS <= 29) & (np.abs(XS + 0.5 - 16) <= shape - (YS - top) * (0.18 if kind != "stone" else
                                                                                          -0.05))
    if kind == "stone":
        body &= (np.abs(XS + 0.5 - 16) <= shape - np.maximum(0, YS - 26) * 0.9)
    c.put(body, C(col))
    c.shade(body & (XS < 14), 1.12)
    c.shade(body & (XS > 18), 0.78)
    if kind == "glazed":
        c.put(body & ((YS == 23) | (YS == 24)), C((232, 226, 210)))
        c.shade(body & ((YS == 23) | (YS == 24)) & (XS > 18), 0.8)
    rim = box(16 - int(shape) - 1, top - 1, 16 + int(shape), top + 1)
    c.put(rim, C(col) * 1.08)
    c.shade(rim & (YS == top + 1), 0.7)
    c.put(box(16 - int(shape) + 1, top - 1, 16 + int(shape) - 2, top - 1), C((70, 50, 34)))     # the earth


def leaf(c, cx, cy, rx, ry, col):
    c.put(ellipse(cx, cy, rx, ry), C(col))


def leafy():
    c = Canvas()
    pot(c, "terracotta")
    rng = random.Random(4100)
    for _ in range(26):
        a = rng.uniform(-2.6, -0.5)
        r = rng.uniform(2, 11)
        cx, cy = 16 + np.cos(a) * r * 0.9, 15 + np.sin(a) * r
        k = (16 - cx + 15 - cy) / 20.0
        leaf(c, cx, cy, rng.uniform(1.8, 3), rng.uniform(1.2, 2.2), C((62, 124, 50)) * (1 + 0.35 * k) +
             rng.uniform(-8, 8))
    return c.image()


def fern():
    c = Canvas()
    pot(c, "stone")
    rng = random.Random(4300)
    for ang in (-2.9, -2.45, -2.0, -1.57, -1.15, -0.7, -0.25, -2.2, -0.95):
        length = rng.uniform(10, 14)
        for i in range(1, 15):
            t = i / 14.0
            x = 16 + np.cos(ang) * length * t
            y = 17 + np.sin(ang) * length * t + (t ** 2) * 6 * abs(np.cos(ang))     # the tips droop
            g = C((70, 140, 58)) * (1.15 - 0.3 * t) * (1.1 if np.cos(ang) < 0 else 0.92)
            c.put(ellipse(x, y, 0.9, 0.9), g * 0.8)                                  # the stem
            w = 2.6 * (1 - t) + 0.8
            for side in (-1, 1):
                lx = x + np.cos(ang + side * 1.3) * w
                ly = y + np.sin(ang + side * 1.3) * w
                c.put(ellipse(lx, ly, 1.0, 1.0), g)
    return c.image()


def flowering():
    c = Canvas()
    pot(c, "glazed")
    rng = random.Random(4400)
    bush = ellipse(16, 12, 9, 7)
    c.put(bush, C((54, 110, 52)))
    n = smooth_noise(rng, 1)
    c.img[bush] *= (1 + 0.25 * n[bush])[:, None]
    c.shade(bush & (XS + YS > 30), 0.82)
    for _ in range(11):
        fx, fy = rng.uniform(9, 23), rng.uniform(6, 17)
        if ((fx - 16) / 8) ** 2 + ((fy - 12) / 6) ** 2 > 1:
            continue
        col = rng.choice(((214, 70, 96), (236, 120, 150), (240, 200, 210)))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            c.put(box(int(fx) + dx, int(fy) + dy, int(fx) + dx, int(fy) + dy), C(col))
        c.put(box(int(fx), int(fy), int(fx), int(fy)), C((246, 214, 90)))
    return c.image()


def lemon_tree():
    c = Canvas()
    pot(c, "tub")
    rng = random.Random(4500)
    trunk = box(15, 11, 16, 18)
    c.put(trunk, C((104, 72, 44)))
    c.shade(trunk & (XS == 16), 0.75)
    crown = ellipse(16, 8, 8, 6.5)
    c.put(crown, C((60, 118, 48)))
    n = smooth_noise(rng, 1)
    c.img[crown] *= (1 + 0.3 * n[crown])[:, None]
    c.shade(crown & (XS + YS > 26), 0.8)
    c.shade(crown & (XS + YS < 16), 1.15)
    for fx, fy in ((11, 7), (19, 5), (14, 11), (21, 10), (17, 8)):
        c.put(ellipse(fx, fy, 1.4, 1.4), C((236, 206, 60)))
        c.put(box(fx - 1, fy - 1, fx - 1, fy - 1), C((252, 240, 150)))
    return c.image()


def aloe():
    c = Canvas()
    pot(c, "cream")
    rng = random.Random(4600)
    for ang, length in ((-2.7, 9), (-2.25, 12), (-1.85, 13), (-1.57, 14), (-1.3, 13), (-0.9, 12), (-0.45, 9),
                        (-2.0, 8), (-1.1, 8)):
        for i in range(0, 13):
            t = i / 12.0
            x = 16 + np.cos(ang) * length * t
            y = 20 + np.sin(ang) * length * t
            w = 1.7 * (1 - t) + 0.4
            col = C((96, 150, 120)) * (1.15 if np.cos(ang) < -0.2 else 0.9) * (1.05 - 0.15 * t) + rng.uniform(-6, 6)
            c.put(ellipse(x, y, w, w), col)
            if i % 4 == 2:                                                          # little teeth on the edges
                c.put(ellipse(x + np.cos(ang + 1.57) * w, y + np.sin(ang + 1.57) * w, 0.6, 0.6), C((200, 210, 170)))
    return c.image()


PLANTS = [  # name, picture, examine text
    ("Potted_Plant001", leafy, "A leafy plant in a clay pot."),
    ("Potted_Plant002", fern, "A fern in a stone pot, its fronds hanging over the edge."),
    ("Potted_Plant003", flowering, "A flowering bush in a blue glazed pot. It smells sweet."),
    ("Potted_Plant004", lemon_tree, "A little lemon tree in a wooden tub, heavy with fruit."),
    ("Potted_Plant005", aloe, "A spiky aloe in a cream pot. Good for burns, they say."),
]
POT_WALK = "1111111" "1111111" "1100011" "1100011" "1100011" "1111111" "1111111"


# ------------------------------------------------------------------ on a wall: ivy (signs and windows are the
# split's pictures: migrate_wall_decor.py)
IVY = {1: ([1, 4, 8], 30, 0.55, "from the left"), 2: ([2, 7, 12, 17, 22, 27, 30], 32, 0.7, "all over"),
       3: ([S - 2, S - 5, S - 9], 30, 0.55, "from the right")}


def ivy(kind):
    """Ivy climbing whatever wall it's on (village_decor.grow_ivy, on nothing)."""
    import village_decor as V
    starts, height, density, _ = IVY[kind]
    key = np.array((255, 0, 255), dtype=np.float32)
    img = np.tile(key, (S, S, 1))
    V.grow_ivy(img, random.Random(7100 + kind * 13 + 8), starts, height, 1.1, density)
    c = Canvas()
    m = np.abs(img - key).max(axis=-1) > 0.5
    c.put(m, 0)
    c.img[m] = img[m]
    return c.image()


SIGNS = ["bread (a baker)", "a gold coin (a bank)", "an anvil (a smithy)", "a sack (a trader)",
         "a potion (an apothecary)", "a fish (a fishmonger)", "a hammer (a workshop)", "a crown (an inn)"]
WINDOW_KINDS = ["a window", "a window with a loose shutter, open (a way in)",
                "a window upside down (a front wall facing north)", "a window with a box of flowers",
                "a window half hidden by ivy"]
LADDERS = {"Ladder001": "a ladder up", "Ladder002": "a hatch, a ladder down", "Ladder003": "a hatch, up or down",
           "Ladder006": "a hole in the ground, a ladder down", "Ladder008": "a ladder up to the loft",
           "Ladder009": "a trapdoor, a ladder down"}

# ------------------------------------------------------------------ what this module makes
TILE_ART = {}
TILE_DATA = {}  # name: (Walkable.Data, Show.Name, Use.Words, Examine.Info, Line.of.Sight, minimap colour)
TILE_KEYS = {}
for _style, _exa in RUG_STYLES.items():
    for _k in RUG_EDGES:
        _n = rug_name(_style, _k)
        TILE_ART[_n] = (lambda s=_style, k=_k: rug(s, k))
        TILE_DATA[_n] = ("1" * 49, "1", "", _exa, "1", "138 40 36" if _style == "Rug" else "44 62 108")
        TILE_KEYS[_n] = [("Layer", "Decor"), ("Piece", RUG_PIECES[_k])]
for _n, _fn, _exa in PLANTS:
    TILE_ART[_n] = _fn
    TILE_DATA[_n] = (POT_WALK, "1", "", _exa, "1", "62 124 50")
    TILE_KEYS[_n] = [("Layer", "Decor"), ("Piece", _exa.split(" in ")[0][2:] if " in " in _exa else "")]
for _k, (_s, _h, _d, _what) in IVY.items():
    TILE_ART["Ivy%03d" % _k] = (lambda k=_k: ivy(k))
    TILE_KEYS["Ivy%03d" % _k] = [("Piece", "ivy " + _what)]
for _i, _what in enumerate(SIGNS):
    TILE_KEYS["Sign%03d" % (_i + 1)] = [("Piece", "a hanging sign: " + _what)]
for _base in ("Brick", "Stone_Wall", "Timber", "Plaster", "Sandstone"):
    for _i, _what in enumerate(WINDOW_KINDS):
        TILE_KEYS["%s_Window%03d" % (_base, _i + 1)] = [("Piece", _what)]
for _n, _what in LADDERS.items():
    TILE_KEYS[_n] = [("Piece", _what)]
for _kind in F.KINDS:
    for _num, _sides, _what in F.PIECES:
        TILE_KEYS.setdefault(F.name(_kind, _num), []).append(("Piece", _what))
TILE_KEYS["Fence001"] = [("Piece", "east-west")]
TILE_KEYS["Fence002"] = [("Piece", "north-south")]


def roof_pieces():
    """Piece= for every roof piece (house_tiles: 15 pieces, rows T U R D B, columns W M E; 016-030 with a chimney)."""
    import house_tiles as H
    rows = ("top eave", "upper slope", "ridge", "lower slope", "bottom eave")
    cols = ("west end", "middle", "east end")
    out = {}
    for m in H.ROOF_MATERIALS:
        for k in range(15):
            out["%s_Roof%03d" % (m, k + 1)] = "%s, %s" % (rows[k // 3], cols[k % 3])
            out["%s_Roof%03d" % (m, k + 16)] = "%s, %s (with a chimney)" % (rows[k // 3], cols[k % 3])
        out["%s_Roof031" % m] = "a dormer window on the lower slope"
        out["%s_Roof032" % m] = "a dormer window on the bottom eave"
    return out


THIN_WHAT = ("the north wall", "the east wall", "the south wall", "the west wall", "the north-east corner",
             "the south-east corner", "the south-west corner", "the north-west corner")
THIN_ORDER = [8, 1, 5, 4, 0, 2, 7, 3, 6]               # round a room: NW N NE / W (the floor) E / SW S SE


def thin_walls():
    """{(wall, floor): its 8 pieces} (house_tiles: <Wall>_Thin_<Floor>001-008, a wall along the room's edge)."""
    import house_tiles as H
    walls = sorted(set(H.WALL_BASES.values()))
    return {(w, f): ["%s_Thin_%s%03d" % (w, f, n) for n in range(1, 9)] for w in walls for f in H.THIN_FLOORS.values()}


def sets():
    """[(set name, title, columns, [tile names row by row, "" = a gap])] for Data\\TileSets.ini."""
    import house_tiles as H
    out = []
    for m in H.ROOF_MATERIALS:
        out.append(("%s_Roof" % m, "%s roof" % m.lower(), 3, ["%s_Roof%03d" % (m, k) for k in range(1, 16)]))
        out.append(("%s_Roof_Chimney" % m, "%s roof with a chimney" % m.lower(), 3,
                    ["%s_Roof%03d" % (m, k) for k in range(16, 31)]))
        out.append(("%s_Roof_Dormer" % m, "%s roof: dormers" % m.lower(), 2, ["%s_Roof031" % m, "%s_Roof032" % m]))
    floors = {v: k for k, v in H.THIN_FLOORS.items()}
    for (w, f), names in thin_walls().items():
        out.append(("%s_Thin_%s" % (w, f), "thin %s walls round a %s floor" % (w.replace("_", " ").lower(), f.lower()),
                    3, [names[k - 1] if k else floors[f] for k in THIN_ORDER]))
    for style in RUG_STYLES:
        out.append((style, style.replace("_", " ").lower(), 4, [rug_name(style, k) for row in RUG_LAYOUT for k in row]))
    for kind in F.KINDS:
        out.append(("%s_Fence" % kind, "%s fence" % kind.lower(), 4,
                    [F.name(kind, n) for row in [[3, 7, 1, 4], [9, 11, 1, 10], [2, 2, 12, 2], [5, 8, 1, 6]]
                     for n in row]))
    out.append(("Fence", "old wooden fence", 2, ["Fence001", "Fence002"]))
    out.append(("Sign", "hanging signs", 4, ["Sign%03d" % i for i in range(1, 9)]))
    out.append(("Ivy", "ivy", 3, ["Ivy%03d" % k for k in IVY]))
    for base in ("Brick", "Stone_Wall", "Timber", "Plaster", "Sandstone"):
        out.append(("%s_Window" % base, "%s windows" % base.replace("_", " ").lower(), 5,
                    ["%s_Window%03d" % (base, i) for i in range(1, 6)]))
    out.append(("Ladder", "ladders and hatches", 3, list(LADDERS)))
    out.append(("Potted_Plant", "potted plants", 5, [n for n, _, _ in PLANTS]))
    return out


def all_pieces():
    out = roof_pieces()
    for (w, f), names in thin_walls().items():
        out.update({n: THIN_WHAT[i] for i, n in enumerate(names)})
    for n, keys in TILE_KEYS.items():
        out.update({n: v for k, v in keys if k == "Piece"})
    return out


# ------------------------------------------------------------------ build steps
def make_art():
    """The rugs, plants (written over the split's pictures: these are the decor now) and fences."""
    made = []
    for name, fn in TILE_ART.items():
        if write_image(p("Sprites", "Tiles", name + ".png"), fn(), decor=True):
            made.append("Sprites\\Tiles\\%s.png" % name)
    return made


def write_tile_sets():
    """Data\\TileSets.ini (only the sets whose tiles are there) and every piece's Tiles.ini Piece=."""
    from common import Ini
    have = lambda n: os.path.exists(p("Sprites", "Tiles", n + ".png"))
    lines = ["; Tiles that go together: a roof, a rug, a fence, the thin walls round a room. Made by",
             "; Dev\\migrate\\decor_sets.py (your changes are kept).",
             ";   Title    what the set is",
             ";   Columns  how many tiles across the set is laid out",
             ";   Tiles    its tiles row by row, as they fit together (a blank between commas is a gap). A tile can be in",
             ";            it more than once (a fence's middle).",
             "; Each tile's Data\\Tiles.ini Piece= says which piece it is (\"corner: top left\"). The editor shows the set,",
             "; with the piece marked, when you point at one in the Maps palette.", ""]
    for name, title, cols, names in sets():
        names = [n if n and have(n) else "" for n in names]
        if sum(1 for n in names if n) < 2:
            continue
        lines += ["[%s]" % name, "Title=%s" % title, "Columns=%d" % cols, "Tiles=%s" % ",".join(names), ""]
    changed = []
    if write_generated(p("Data", "TileSets.ini"), lines):
        changed.append("Data\\TileSets.ini")
    ini = Ini(p("Data", "Tiles.ini"))
    for n, what in all_pieces().items():
        if ini.section(n) is not None and what:
            ini.set(n, "Piece", what)
    if ini.save(p("Data", "Tiles.ini")):
        changed.append("Data\\Tiles.ini")
    return changed


def preview(path):
    """Every rug piece (laid out as a set) and the plants, on planks and on stone."""
    floors = [Image.open(p("Sprites", "Tiles", f + ".png")).convert("RGBA") for f in ("Plank001", "Tile001")]
    out = Image.new("RGBA", (S * 13, S * 5), (30, 24, 20, 255))
    for i, style in enumerate(RUG_STYLES):
        for y, row in enumerate(RUG_LAYOUT):
            for x, k in enumerate(row):
                at = ((i * 5 + x) * S, y * S)
                out.alpha_composite(floors[i], at)
                out.alpha_composite(rug(style, k), at)
    for j, (n, fn, _) in enumerate(PLANTS):
        for i in range(2):
            at = ((10 + i) * S if j < 4 else 12 * S, (j % 4) * S if j < 4 else (4 if i == 0 else 3) * S)
            out.alpha_composite(floors[i], at)
            out.alpha_composite(fn(), at)
    out.resize((out.size[0] * 2, out.size[1] * 2), Image.NEAREST).save(path)


if __name__ == "__main__":
    import sys
    preview(sys.argv[1])
