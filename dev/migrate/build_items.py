"""The everyday items, drawn again (sprites\\Entities): the tuna (Raw_Herring, Cooked_Herring), Burnt_Food, Bread, Logs, the
potion flask (Basic_Potion, Empty_Vial, Full_Vial), the Tinderbox, Bones (a heap), the poultry (Raw_, Cooked_Poultry)
and the buckets (Bucket, Bucket_of_Water). 32 x 32, lit from the top left, with the 1 px dark outline.

The items made from these are made again from them, by their own builders: the other potions (build_sprites.py,
build_herbs.py, build_status.py's Antidote, build_hob.py's Calming_Draught), the oak, willow and yew logs, the trout,
salmon and swordfish, the bucket of milk.

  python -I "dev\\migrate\\build_items.py" [--preview]       (--preview: dev\\Renders\\Items preview.png)
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K  # noqa: E402
from common import p  # noqa: E402

S = 32
OUTLINE = (34, 30, 30)
ITEMS = {}


def item(name):
    def deco(fn):
        ITEMS[name] = fn
        return fn
    return deco


def inside_poly(pts, x, y):
    hit = False
    j = len(pts) - 1
    for i in range(len(pts)):
        (xi, yi), (xj, yj) = pts[i], pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def poly(img, pts, colour):
    """Fills polygon pts (colour: a colour, or (x, y) -> a colour)."""
    for y in range(S):
        for x in range(S):
            if inside_poly(pts, x + 0.5, y + 0.5):
                img[y][x] = colour(x, y) if callable(colour) else colour


def band(t, stops):
    """The colour at t (0..1) along stops [(t, colour)...], stepped (pixel art: no blending between them)."""
    c = stops[0][1]
    for at, col in stops:
        if t >= at:
            c = col
    return c


def done(img):
    return K.outline_img(img, OUTLINE)


# ---------------------------------------------------------------- the tuna
def tuna(back, side, belly, sheen, fin, finlet, eye, marks=None, rng_seed=0):
    """A tuna, swimming left: a deep torpedo of a body, a dark back over a pale belly, sickle fins, the yellow
    finlets along its back and belly to a forked tail."""
    img = K.new()
    cy = 16

    def half(x):
        u = (x - 13.0) / 10.5
        if abs(u) >= 1:
            return 0
        return 6.4 * (1 - abs(u) ** 2.3) ** 0.55 * (1 - 0.12 * u)

    for x in range(3, 25):
        h = max(1.2, half(x + 0.5))
        for y in range(S):
            dy = y + 0.5 - cy
            if abs(dy) > h:
                continue
            t = (dy + h) / (2 * h)                                    # (0 at its back, 1 at its belly)
            c = band(t, [(0, back), (0.36, side), (0.5, belly), (0.6, sheen), (0.72, belly)])
            if t < 0.2 and x < 18:
                c = K.mul(back, 0.8)
            img[y][x] = c
    poly(img, [(22, 15), (28, 8), (30, 9), (26, 16), (30, 23), (28, 24), (22, 17)], fin)            # the tail
    top = lambda x: cy - half(x)                                                                    # noqa: E731
    poly(img, [(11, top(11) + 1), (14, top(14) - 4), (16, top(16) + 1)], fin)                         # first dorsal
    poly(img, [(18, top(18) + 1), (22, top(18) - 4), (20.5, top(20) + 1)], fin)                       # (sickle fins)
    poly(img, [(18, 2 * cy - top(18) - 1), (22, 2 * cy - top(18) + 4), (20.5, 2 * cy - top(20) - 1)], fin)
    poly(img, [(9, 16.5), (15, 18.5), (10, 18)], K.mul(back, 0.9))                                  # pectoral fin
    for x in (20, 22, 24):                                                                          # the finlets
        h = max(1.2, half(x + 0.5))
        K.put(img, x, int(cy - h) - 1, finlet)
        K.put(img, x, int(cy + h), finlet)
    for y in range(13, 19):                                                                         # the gill
        K.put(img, 9 if y in (13, 18) else 10, y, K.mul(side, 0.7))
    K.put(img, 6, 14, eye[0])
    K.put(img, 6, 15, eye[1])
    K.put(img, 5, 14, eye[1])
    K.put(img, 3, 17, K.mul(back, 0.7))                                                             # the mouth
    K.put(img, 4, 17, K.mul(back, 0.7))
    if marks:
        marks(img)
    return done(img)


@item("Raw_Herring")
def raw_tuna():
    return tuna(back=(30, 50, 98), side=(72, 100, 150), belly=(196, 204, 214), sheen=(232, 236, 242),
                fin=(40, 58, 96), finlet=(236, 198, 52), eye=((232, 232, 220), (16, 16, 22)))


@item("Cooked_Herring")
def cooked_tuna():
    def grill(img):
        for k in range(5):                                        # (the bars of the grill)
            for j in range(9):
                x, y = 6 + k * 4 + j // 3, 11 + j
                if img[y][x] is not None:
                    img[y][x] = (92, 50, 22)
    return tuna(back=(112, 64, 30), side=(160, 102, 52), belly=(212, 158, 94), sheen=(236, 196, 132),
                fin=(96, 54, 26), finlet=(196, 140, 60), eye=((236, 230, 210), (60, 34, 18)), marks=grill)


@item("Burnt_Food")
def burnt_food():
    """Whatever it was, it's charcoal now: a crumbling heap of black lumps, cracked, with crumbs, a smudge of grey ash
    and the last orange spark of an ember (every burnt dish is this, and they stack)."""
    img = K.new()
    rng = random.Random(11)
    char = ((40, 32, 28), (64, 52, 44), (18, 14, 12))
    for cx, cy, rx, ry in ((12, 22, 5.5, 4.2), (19.5, 21, 5.2, 4.6), (16, 17.5, 4.4, 3.6), (23, 24.5, 3.6, 2.8),
                           (9, 25.5, 3.2, 2.4)):
        K.shaded_ellipse(img, cx, cy, rx, ry, char[0], char[1], char[2])
    pts = [(x, y) for y in range(S) for x in range(S) if img[y][x] is not None]
    for _ in range(26):                                            # (cracks through the char)
        x, y = rng.choice(pts)
        img[y][x] = (10, 8, 8)
    for _ in range(10):                                            # (grey ash on the top)
        x, y = rng.choice([q for q in pts if q[1] < 21])
        img[y][x] = (120, 114, 108)
    for x, y in ((5, 27), (27, 26), (26, 28), (7, 29), (14, 28), (20, 28)):    # (crumbs round it)
        img[y][x] = char[2]
    for x, y in ((17, 18), (21, 22), (11, 23)):                    # (an ember still glowing)
        img[y][x] = (222, 104, 34)
    img[18][18] = (255, 170, 70)
    return done(img)


# ---------------------------------------------------------------- bread
@item("Bread")
def bread():
    """A round-topped loaf, golden crust, three slashes baked open, a dusting of flour."""
    img = K.new()
    K.shaded_ellipse(img, 16, 18, 12, 7.5, (192, 126, 56), (228, 168, 84), (140, 84, 34), hi=(246, 204, 124))
    for y in range(22, 27):                                       # (its flat underside, darker)
        for x in range(S):
            if img[y][x] is not None:
                img[y][x] = (122, 72, 30) if y >= 24 else img[y][x]
    for y in range(26, S):
        for x in range(S):
            img[y][x] = None
    for x0 in (8, 14, 20):                                        # the slashes: pale inside, a dark lip below
        for k in range(6):
            x, y = x0 + k, 18 - k // 2
            K.put(img, x, y, (240, 214, 160))
            K.put(img, x, y + 1, (150, 92, 38))
    rng = random.Random(3)
    for _ in range(10):
        x, y = rng.randrange(7, 25), rng.randrange(12, 19)
        if img[y][x] is not None:
            img[y][x] = (250, 236, 206)                           # (flour)
    return done(img)


# ---------------------------------------------------------------- logs
def log_end(img, cx, cy, r):
    """A log's sawn end: pale sapwood, the rings, the heart."""
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - cx, (y + 0.5 - cy) * 1.05)
            if d > r:
                continue
            if d > r - 0.9:
                c = (84, 52, 24)                                  # (the bark round it)
            elif d > r - 1.9:
                c = (214, 172, 112)
            elif abs(d - r * 0.5) < 0.55:
                c = (170, 124, 70)                                # (a ring)
            elif d < 1.0:
                c = (146, 100, 56)
            else:
                c = (198, 154, 96)
            img[y][x] = c


@item("Logs")
def logs():
    """Three logs, piled two and one, their sawn ends towards you."""
    img = K.new()
    r = 4.6
    piled = ((15, 13), (10, 21), (19.5, 21))                      # (the top one first: the others in front)
    for cx, cy in piled:
        for k in range(14, 0, -1):
            t = k / 14.0
            bx, by = cx + 7 * t, cy - 6 * t
            for y in range(S):
                for x in range(S):
                    dx, dy = x + 0.5 - bx, y + 0.5 - by
                    d = math.hypot(dx, dy)
                    if d > r:
                        continue
                    side = (dx * -0.7 + dy * -0.7) / r
                    c = (132, 88, 48) if side > 0.35 else (64, 40, 20) if side < -0.35 else (98, 62, 32)
                    if (x * 3 + y * 5) % 7 == 0:
                        c = K.mul(c, 0.82)                        # (the bark's furrows)
                    img[y][x] = c
    for cx, cy in piled:                                          # (and all three ends, in the one plane)
        log_end(img, cx, cy, r)
    return done(img)


# ---------------------------------------------------------------- the potion flask
GLASS = (176, 192, 202)                     # (the glass, the cork: grey, so a potion's colour changes only its liquid)
GLASS_HI = (244, 248, 252)
GLASS_IN = (206, 220, 228)
CORK = ((176, 162, 144), (148, 134, 118), (118, 106, 92))


def flask(liquid=None):
    """A round-bellied glass flask, stoppered, filled (or not) with liquid: (dark, base, light, shine)."""
    img = K.new()
    cx, cy, r = 16, 21, 7.6
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d > r:
                continue
            if d > r - 1.0:
                c = GLASS
            elif liquid and y >= 18:
                k = ((x + 0.5 - cx) * -0.7 + (y + 0.5 - cy) * -0.7) / r
                c = liquid[2] if k > 0.3 else liquid[0] if k < -0.35 else liquid[1]
                if y == 18:
                    c = liquid[2]                                 # (the top of it)
            else:
                c = GLASS_IN
            img[y][x] = c
    for y in range(8, 15):                                         # the neck
        for x in range(14, 19):
            img[y][x] = GLASS if x in (14, 18) else GLASS_IN
    for x in range(13, 20):
        img[8][x] = GLASS                                         # (its lip)
    for y in range(4, 8):                                          # the cork
        for x in range(14, 19):
            img[y][x] = CORK[0] if x == 14 else CORK[2] if x == 18 else CORK[1]
    for x, y in ((12, 18), (11, 19), (11, 20), (15, 10)):           # (the glass's shine)
        img[y][x] = GLASS_HI
    if liquid:
        for x, y in ((18, 22), (20, 24), (17, 25)):
            img[y][x] = liquid[3]                                 # (bubbles)
    return done(img)


@item("Basic_Potion")
def basic_potion():
    return flask(((70, 120, 22), (118, 178, 36), (166, 218, 66), (214, 246, 140)))


@item("Empty_Vial")
def empty_vial():
    return flask()


@item("Full_Vial")
def full_vial():
    return flask(((84, 132, 190), (124, 172, 220), (166, 206, 238), (226, 242, 252)))      # (water)


# ---------------------------------------------------------------- the tinderbox
@item("Tinderbox")
def tinderbox():
    """Small, and plainly what it is: a little round-cornered tin shut on its tinder, a C of fire steel and a nub of
    flint before it, a spark struck between them (it was a big open box, read as a chest)."""
    img = K.new()
    tin = lambda x, y: (150, 144, 134) if y < 16 else (118, 112, 104) if y < 21 else (92, 86, 80)   # noqa: E731
    poly(img, [(11, 14), (22, 14), (23, 15), (23, 21), (22, 22), (11, 22), (10, 21), (10, 15)], tin)  # the tin
    for x in range(11, 23):
        img[16][x] = (78, 72, 66)                                                                  # (its lid's seam)
        img[14][x] = (190, 184, 174)                                                               # (lit from above)
    img[18][16], img[18][17] = (200, 170, 96), (164, 132, 66)                                      # (the clasp)
    for deg in range(0, 360, 3):                                                                   # the steel, a C
        if 55 < deg < 125:
            continue                                                                               # (open at the top)
        a = math.radians(deg)
        for rx, ry in ((6, 2.8), (5.2, 2.1)):
            x, y = 17.5 + rx * math.cos(a), 25 - ry * math.sin(a)
            K.put(img, int(round(x)), int(round(y)), (214, 218, 226) if math.sin(a) > -0.3 else (146, 150, 160))
    for x in (12, 13, 22, 23):
        img[25][x] = (120, 84, 50)                                                                 # (its wrapped grips)
    K.shaded_ellipse(img, 8, 25, 2.4, 1.8, (78, 80, 90), (132, 134, 146), (46, 46, 54))              # the flint
    for x, y, c in ((9, 21, (255, 214, 120)), (10, 20, (255, 170, 60)), (8, 20, (255, 236, 170))):
        img[y][x] = c                                                                              # a spark
    return done(img)


# ---------------------------------------------------------------- bones
IVORY = ((246, 240, 218), (222, 212, 184), (176, 164, 134))


def bone(img, x0, y0, x1, y1, width=3.4, knob=2.3, ivory=IVORY):
    import build_sprites as B
    B.seg(img, x0, y0, x1, y1, width, *ivory)
    vx, vy = x1 - x0, y1 - y0
    ln = math.hypot(vx, vy)
    nx, ny = -vy / ln * width / 2, vx / ln * width / 2
    for ex, ey in ((x0, y0), (x1, y1)):                            # (the knuckled ends)
        for s in (-1, 1):
            K.shaded_ellipse(img, ex + nx * s, ey + ny * s, knob, knob, *ivory)


@item("Bones")
def bones():
    """A little heap of bones: long bones lying every which way, a curl of ribs, and a skull on top."""
    import build_sprites as B
    img = K.new()
    old = (K.mul(IVORY[0], 0.9), K.mul(IVORY[1], 0.88), K.mul(IVORY[2], 0.85))     # (the ones underneath: duller)
    bone(img, 5, 25, 19, 27, 2.6, 1.7, old)                        # the long bones at the bottom of the heap
    bone(img, 13, 28, 27, 23, 2.6, 1.7, old)
    bone(img, 7, 19, 15, 26, 2.4, 1.6, old)
    for k in range(4):                                             # ribs: short curves, side by side
        x = 6 + k * 2.6
        B.seg(img, x, 15 + k * 0.6, x + 2.2, 19.5 + k * 0.4, 1.6, *IVORY)
        B.seg(img, x + 2.2, 19.5 + k * 0.4, x + 1.2, 23 + k * 0.3, 1.6, *IVORY)
    bone(img, 15, 22, 26, 17, 2.8, 1.9)                            # one across the top
    # the skull: a round dome, a jaw under it, dark sockets and a nose
    K.shaded_ellipse(img, 20.5, 12.5, 6.2, 5.6, IVORY[1], IVORY[0], IVORY[2])
    K.shaded_ellipse(img, 21, 18, 3.8, 2.2, IVORY[1], IVORY[0], IVORY[2])
    dark = (58, 44, 34)
    for x, y in ((18, 13), (19, 13), (18, 14), (19, 14), (22, 13), (23, 13), (22, 14), (23, 14), (21, 16)):
        img[y][x] = dark
    for x in (19, 21, 23):                                         # (its teeth)
        img[18][x] = IVORY[2]
    return done(img)


# ---------------------------------------------------------------- poultry
def poultry(base, light, dark, hi, speck=None):
    """A plucked bird on its back: the plump body, its wing tucked in, both drumsticks up, their bone ends."""
    img = K.new()
    import build_sprites as B
    for x0, y0, x1, y1 in ((12, 16, 8, 9), (20, 16, 24, 9)):       # the drumsticks
        B.seg(img, x0, y0, x1, y1, 5.2, light, base, dark)
        K.shaded_ellipse(img, x1, y1, 1.8, 1.8, (242, 236, 220), (252, 250, 240), (206, 196, 176))
    K.shaded_ellipse(img, 16, 19.5, 10, 7.2, base, light, dark, hi=hi)
    K.shaded_ellipse(img, 20, 21, 3.6, 2.4, K.mul(base, 0.92), base, dark)                          # (the wing)
    if speck:
        rng = random.Random(7)
        for _ in range(9):
            x, y = rng.randrange(9, 24), rng.randrange(15, 25)
            if img[y][x] is not None:
                img[y][x] = speck
    return done(img)


@item("Raw_Poultry")
def raw_poultry():
    return poultry((232, 182, 160), (248, 212, 194), (204, 146, 126), (255, 234, 222), speck=(212, 160, 140))


@item("Cooked_Poultry")
def cooked_poultry():
    return poultry((194, 120, 50), (230, 164, 82), (146, 82, 30), (250, 206, 132))


# ---------------------------------------------------------------- buckets
def bucket(inside):
    """A wooden bucket of staves, two iron bands, an iron handle; inside: [(dark, mid, light, shine)] or bare wood."""
    img = K.new()
    top, bottom = 11, 27
    for y in range(top, bottom + 1):                                # the staves, wider at the top
        half = 9 - (y - top) * 2.0 / (bottom - top)
        for x in range(S):
            dx = x + 0.5 - 16
            if abs(dx) > half:
                continue
            k = dx / half
            c = (188, 132, 76) if k < -0.45 else (106, 66, 34) if k > 0.5 else (152, 100, 54)
            if int(dx + 16) % 4 == 0:
                c = K.mul(c, 0.78)                                    # (between the staves)
            if y in (14, 15, 23, 24):
                c = (150, 150, 160) if k < -0.3 else (96, 96, 106)    # the bands
            img[y][x] = c
    for y in range(top - 3, top + 4):                                # the open top
        for x in range(S):
            d = ((x + 0.5 - 16) / 9.0) ** 2 + ((y + 0.5 - top) / 3.0) ** 2
            if d > 1:
                continue
            if d > 0.62:
                img[y][x] = (196, 142, 84)                            # (the rim)
            elif inside:
                k = (x + 0.5 - 16) / 9.0
                img[y][x] = inside[2] if k < -0.3 else inside[0] if k > 0.35 else inside[1]
            else:
                img[y][x] = (70, 44, 24) if y < top + 1 else (92, 58, 30)
    if inside:
        img[top - 1][12] = img[top - 1][13] = inside[3]               # (light on the water)
    for k in range(0, 21):                                            # the handle
        a = math.pi * k / 20
        K.put(img, int(round(16 - 9.5 * math.cos(a))), int(round(top - 1 - 8 * math.sin(a))), (112, 112, 122))
    return done(img)


@item("Bucket")
def empty_bucket():
    return bucket(None)


@item("Bucket_of_Water")
def water_bucket():
    return bucket(((40, 80, 150), (58, 104, 180), (96, 146, 214), (196, 226, 248)))


# ---------------------------------------------------------------- the items made from these
def derived():
    """The other potions, logs and fish, and the bucket of milk: made again by their own builders, from these."""
    import build_sprites as B
    import build_herbs
    import build_status
    import build_hob
    made = []
    for name in ("Super_Potion", "Strength_Potion", "Defence_Potion", "Combat_Potion", "Magic_Potion", "Mega_Potion",
                 "Owl_Potion", "Witch_Brew", "Alchemy_Table", "Oak_Logs", "Willow_Logs", "Yew_Logs", "Raw_Trout",
                 "Cooked_Trout", "Raw_Salmon", "Cooked_Salmon", "Raw_Swordfish", "Cooked_Swordfish", "Bucket_of_Milk"):
        if K.save("Entities", name, B.SPRITES[name]()):
            made.append(name)
    for name, (hue, _, _, _) in build_herbs.POTIONS.items():
        if K.save("Entities", name, build_herbs.potion_img(hue)):
            made.append(name)
    build_status.make_sprites()                                     # (the Antidote, and the gravestone the same)
    build_hob.make_art()                                            # (the Calming_Draught, and Hob the same)
    return made


def main():
    made = [name for name, fn in ITEMS.items() if K.save("Entities", name, fn())]
    made += derived()
    print("Drew " + (", ".join(made) if made else "nothing new"))
    if "--preview" in sys.argv:
        names = list(ITEMS) + ["Super_Potion", "Strength_Potion", "Magic_Potion", "Antidote", "Calming_Draught",
                               "Oak_Logs", "Yew_Logs", "Raw_Trout", "Raw_Salmon", "Raw_Swordfish", "Bucket_of_Milk"]
        K.sheet(p("dev", "Renders", "Items preview.png"), [K.load("Entities", n) for n in names], scale=4, cols=9)
        print("preview: dev\\Renders\\Items preview.png")


if __name__ == "__main__":
    main()
