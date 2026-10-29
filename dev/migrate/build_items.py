"""The everyday items, drawn again (sprites\\Entities): the tuna (Raw_Herring, Cooked_Herring, Burnt_Herring), Bread, Logs, the
potion flask (Basic_Potion, Empty_Vial, Full_Vial), the Tinderbox, Bones, the poultry (Raw_, Cooked_, Burnt_Poultry)
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


@item("Burnt_Herring")
def burnt_tuna():
    def char(img):
        rng = random.Random(5)
        pts = [(x, y) for y in range(S) for x in range(S) if img[y][x] is not None]
        for _ in range(24):
            x, y = rng.choice(pts)
            img[y][x] = (20, 14, 12)                               # (cracks in the char)
        for _ in range(4):
            x, y = rng.choice(pts)
            img[y][x] = (196, 86, 30)                              # (a last ember)
    return tuna(back=(32, 24, 20), side=(52, 40, 34), belly=(82, 64, 52), sheen=(104, 84, 70),
                fin=(28, 20, 18), finlet=(70, 54, 40), eye=((120, 110, 96), (10, 8, 8)), marks=char)


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
    """A small tin box, its lid up on its hinge, tinder inside; the steel and the flint beside it."""
    img = K.new()
    poly(img, [(6, 15), (24, 15), (24, 25), (6, 25)], lambda x, y: (126, 120, 112) if y < 17 else (98, 92, 86))
    poly(img, [(6, 15), (24, 15), (23, 5), (7, 5)], (176, 170, 160))                               # the lid, up
    poly(img, [(8, 14), (22, 14), (21.5, 7), (8.5, 7)], (84, 78, 72))                              # (inside it)
    for x in range(7, 24):
        img[15][x] = (178, 172, 164)                                                               # (the rim)
        if x % 3:
            img[16][x] = (150, 120, 60) if x % 2 else (196, 164, 90)                                # the tinder
    for x in range(6, 25):
        img[25][x] = (70, 66, 60)
    for k in range(-10, 11):                                                                       # the steel
        a = math.radians(k * 13)
        x, y = 24 + 4.5 * math.sin(a), 24 - 4.5 * math.cos(a) * 0.55
        K.put(img, int(round(x)), int(round(y)), (196, 200, 208) if k < 4 else (140, 144, 152))
    K.shaded_ellipse(img, 5.5, 25, 3.2, 2.4, (78, 80, 90), (120, 122, 132), (50, 50, 58))            # the flint
    return done(img)


# ---------------------------------------------------------------- bones
def bone(img, x0, y0, x1, y1):
    import build_sprites as B
    ivory = ((246, 240, 218), (222, 212, 184), (176, 164, 134))
    B.seg(img, x0, y0, x1, y1, 3.4, *ivory)
    vx, vy = x1 - x0, y1 - y0
    ln = math.hypot(vx, vy)
    nx, ny = -vy / ln * 1.7, vx / ln * 1.7
    for ex, ey in ((x0, y0), (x1, y1)):                            # (the knuckled ends)
        for s in (-1, 1):
            K.shaded_ellipse(img, ex + nx * s, ey + ny * s, 2.3, 2.3, *ivory)


@item("Bones")
def bones():
    img = K.new()
    bone(img, 8, 9, 24, 23)
    bone(img, 24, 9, 8, 23)
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


@item("Burnt_Poultry")
def burnt_poultry():
    return poultry((70, 46, 32), (102, 70, 48), (40, 26, 18), (132, 92, 62), speck=(22, 14, 10))


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
