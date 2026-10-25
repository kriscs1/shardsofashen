"""Cave and gathering tiles for Dragon Sword v2 (used by build_tiles.py, which writes the sprites).

Every function returns a 32x32 opaque image (rows of (r, g, b)). Floors, walls, water, tracks and fields are
drawn wrap-around so they tile seamlessly. Run build_tiles.py with --preview to get dev\\Renders\\Tiles preview.png
and dev\\Renders\\Tiles 4x4.png (each tile repeated 4x4 to check the seams).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K
from common import p, read_bmp

S = 32
FLOOR = (78, 70, 62)


def clamp(v):
    return max(0, min(255, int(round(v))))


def copy_tile(name):
    w, h, rows = read_bmp(p("sprites", "Tiles", name + ".png"))
    return [list(r) for r in rows[h // 2:]]


# ---------------------------------------------------------------- floors
def _floor_base(seed, base=FLOOR, amp=7, fine=3):
    rng = random.Random(seed)
    big = K.noise_field(rng, S, S, 6, blur=4)
    small = K.noise_field(rng, S, S, amp, blur=1)
    img = [[tuple(clamp(c + big[y][x] + small[y][x] + rng.uniform(-fine, fine)) for c in base)
            for x in range(S)] for y in range(S)]
    return img, rng


def _crack(img, rng, x, y, n, col):
    for _ in range(n):
        K.put(img, x, y, col, wrap=True)
        if rng.random() < 0.3:
            K.put(img, x + 1, y, K.mul(col, 1.25), wrap=True)
        x += rng.choice((1, 1, 0, -1))
        y += rng.choice((1, 1, 0))


def _pebble(img, rng, x, y, r, base=(104, 96, 88)):
    K.put(img, int(x + r * 0.4), int(y + r * 0.9), K.add(FLOOR, -26), wrap=True)     # little shadow under it
    K.shaded_ellipse(img, x, y, r, r * 0.8, base, K.add(base, 26), K.add(base, -34), rng=rng, wrap=True)


def cave_floor(seed=303, pebbles=4, cracks=2):
    img, rng = _floor_base(seed)
    for _ in range(70):
        K.put(img, rng.randrange(S), rng.randrange(S), rng.choice([(62, 56, 50), (94, 86, 76), (70, 63, 56)]), wrap=True)
    for _ in range(cracks):
        _crack(img, rng, rng.randrange(S), rng.randrange(S), rng.randrange(5, 9), (58, 52, 46))
    for _ in range(pebbles):
        _pebble(img, rng, rng.randrange(S), rng.randrange(S), rng.choice((1.2, 1.5, 1.8)))
    return img


def cave_floor_gravel():
    img, rng = _floor_base(313, base=(84, 76, 67))
    for _ in range(90):
        K.put(img, rng.randrange(S), rng.randrange(S), rng.choice([(60, 54, 48), (104, 96, 86), (92, 84, 74)]), wrap=True)
    for _ in range(16):
        _pebble(img, rng, rng.randrange(S), rng.randrange(S), rng.choice((1.0, 1.3, 1.6, 2.0)),
                base=rng.choice([(104, 96, 88), (96, 90, 84), (112, 102, 90)]))
    return img


def cave_floor_damp():
    img, rng = _floor_base(323, base=(68, 63, 57))
    moss = K.noise_field(random.Random(324), S, S, 1.0, blur=3)
    for y in range(S):
        for x in range(S):
            if moss[y][x] > 0.35:
                img[y][x] = K.mix(img[y][x], (60, 80, 50), 0.45 + 0.3 * (moss[y][x] - 0.35))
            elif moss[y][x] < -0.55:
                img[y][x] = K.mix(img[y][x], (48, 56, 66), 0.5)      # wet, bluish
    for _ in range(14):
        x, y = rng.randrange(S), rng.randrange(S)
        if moss[y][x] < -0.4:
            K.put(img, x, y, (120, 132, 140), wrap=True)              # glints of water
    _crack(img, rng, 5, 20, 8, (44, 40, 36))
    for _ in range(2):
        _pebble(img, rng, rng.randrange(S), rng.randrange(S), 1.4, base=(90, 88, 80))
    return img


# ---------------------------------------------------------------- walls
ROCK = ((76, 69, 62), (106, 97, 88), (42, 38, 34), (30, 27, 24))     # base, light, dark, outline
WALL_ROCKS = [(6, 6, 8, 7), (21, 4, 9, 7), (14, 16, 9, 7), (30, 15, 7, 7), (4, 25, 8, 7), (20, 27, 9, 7),
              (29, 29, 6, 5), (10, 31, 5, 4)]


def cave_wall():
    rng = random.Random(404)
    img = [[K.jitter((40, 36, 32), rng, 3) for _ in range(S)] for _ in range(S)]
    for cx, cy, rx, ry in WALL_ROCKS:
        base, light, dark, outl = ROCK
        j = rng.uniform(-6, 6)
        K.shaded_ellipse(img, cx, cy, rx, ry, K.add(base, j), K.add(light, j), K.add(dark, j), rng=rng, noise=0.12,
                         outline=outl, wrap=True, hi=K.add(light, 18))
    return img


def _face(seed, torch=False):
    """A wall seen from the front: rock mass on top, a lit vertical rock face below, floor shadow at the base."""
    img = cave_wall()
    rng = random.Random(seed)
    edge = K.noise_field(random.Random(seed + 1), S, 1, 2.5, blur=2)[0]
    stri = K.noise_field(random.Random(seed + 2), S, 1, 8, blur=1)[0]
    for x in range(S):
        top = 11 + int(round(edge[x]))
        for y in range(top, S):
            t = (y - top) / float(S - top)
            base = K.mix((98, 89, 79), (54, 48, 43), t)
            c = K.add(base, stri[x] + rng.uniform(-3, 3))
            if y == top:
                c = (124, 114, 102)                     # lit lip
            elif y == top + 1:
                c = K.add(c, 14)
            if y >= S - 3:
                c = K.mix(c, (26, 23, 20), 0.55 if y == S - 1 else 0.3)
            img[y][x] = c
    for ly in (18, 24):                                   # ledges across the face
        x0 = rng.randrange(S)
        for i in range(rng.randrange(7, 14)):
            x = (x0 + i) % S
            img[ly][x] = K.add(img[ly][x], -22)
            img[ly - 1][x] = K.add(img[ly - 1][x], 12)
    for _ in range(3):                                    # cracks
        x, y = rng.randrange(S), rng.randrange(15, 26)
        for i in range(rng.randrange(3, 6)):
            K.put(img, x, y + i, K.add(img[(y + i) % S][x % S], -26), wrap=True)
            x += rng.choice((0, 0, 1, -1))
    if torch:
        cx, cy = 16, 11
        for y in range(S):                               # warm glow on the rock
            for x in range(S):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d < 14:
                    img[y][x] = K.mix(img[y][x], (255, 170, 70), 0.45 * (1 - d / 14.0) ** 1.3)
        K.rect(img, 14, 19, 18, 20, (52, 48, 46))        # iron bracket
        K.rect(img, 15, 21, 17, 21, (40, 36, 34))
        K.put(img, 16, 22, (40, 36, 34))
        K.rect(img, 15, 14, 17, 18, (110, 70, 34))       # wooden handle
        K.put(img, 15, 14, (140, 92, 48))
        K.put(img, 15, 15, (140, 92, 48))
        K.rect(img, 14, 12, 18, 13, (70, 50, 30))        # pitch-soaked head
        flame = ["  y  ",
                 " yoy ",
                 " oOo ",
                 "yoWOy",
                 "oOWOo",
                 " oOo "]
        pal = {"y": (230, 120, 30), "o": (250, 160, 40), "O": (255, 214, 90), "W": (255, 250, 210)}
        for fy, r in enumerate(flame):
            for fx, ch in enumerate(r):
                if ch != " ":
                    img[6 + fy][14 + fx] = pal[ch]
    return img


def cave_wall_face():
    return _face(414)


def cave_wall_torch():
    return _face(414, torch=True)


# ---------------------------------------------------------------- floor features
def rubble():
    img = cave_floor(seed=333, pebbles=2, cracks=1)
    rng = random.Random(334)
    for cx, cy, r in [(9, 10, 3.2), (13, 13, 2.2), (22, 8, 2.4), (20, 21, 3.6), (25, 24, 2.0), (8, 23, 2.6),
                      (15, 26, 1.6), (27, 14, 1.8), (5, 16, 1.4)]:
        b = rng.choice([(98, 90, 82), (90, 84, 78), (108, 98, 86)])
        for dy in range(1, 3):                                       # soft shadow, lower right
            for dx in range(int(r)):
                K.put(img, int(cx - r * 0.3) + dx + 1, int(cy + r * 0.7) + dy, K.add(FLOOR, -30), wrap=True)
        K.shaded_ellipse(img, cx, cy, r, r * 0.85, b, K.add(b, 28), K.add(b, -36), rng=rng, outline=(46, 41, 36),
                         wrap=True)
    for _ in range(25):
        K.put(img, rng.randrange(S), rng.randrange(S), rng.choice([(110, 102, 92), (60, 54, 48)]), wrap=True)
    return img


def stalagmite():
    img = cave_floor(seed=343, pebbles=2, cracks=1)
    for y in range(24, 31):                                       # shadow on the floor
        for x in range(6, 30):
            dx, dy = (x - 19) / 10.0, (y - 27.5) / 3.0
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.mix(img[y][x], (30, 26, 22), 0.5)
    top, bot = 3, 28
    for y in range(top, bot + 1):
        t = (y - top) / float(bot - top)
        half = 0.8 + 6.8 * t ** 0.85
        for x in range(32):
            dx = x + 0.5 - 16
            if abs(dx) <= half:
                k = dx / half
                base = (124, 114, 100) if k < -0.35 else (96, 87, 77) if k < 0.4 else (62, 56, 50)
                if abs(abs(dx) - half) < 0.9:
                    base = (44, 40, 35)
                if y % 6 == 0 and abs(k) < 0.9:
                    base = K.add(base, -12)                       # growth rings
                img[y][x] = base
    K.put(img, 15, top, (156, 146, 130))
    K.put(img, 15, top + 1, (150, 140, 126))
    for y in range(top + 4, bot - 2, 5):
        K.put(img, 14, y, (146, 136, 122))                         # wet highlights
    return img


def cave_pool():
    rng = random.Random(353)
    n = K.noise_field(rng, S, S, 8, blur=2)
    img = [[(clamp(20 + n[y][x]), clamp(42 + n[y][x] * 1.2), clamp(58 + n[y][x] * 1.4)) for x in range(S)]
           for y in range(S)]
    for cx, cy, ln in [(5, 6, 6), (20, 3, 5), (14, 13, 7), (27, 17, 5), (4, 22, 6), (18, 26, 6), (29, 29, 4)]:
        for i in range(ln):
            c = (64, 104, 122) if 0 < i < ln - 1 else (44, 76, 94)
            K.put(img, cx + i, cy, c, wrap=True)
            K.put(img, cx + i, cy + 1, (14, 30, 42), wrap=True)
    for _ in range(4):
        K.put(img, rng.randrange(S), rng.randrange(S), (150, 190, 205), wrap=True)
    return img


def cave_puddle():
    img = cave_floor(seed=363, pebbles=2, cracks=0)
    rng = random.Random(364)
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - 16) / 10.0, (y + 0.5 - 17) / 6.0
            d = dx * dx + dy * dy + 0.12 * math.sin(x * 0.9) * math.cos(y * 1.3)
            if d <= 1.0:
                c = (36, 54, 66) if d > 0.72 else (28, 46, 60)
                if -0.5 < dx < 0.1 and -0.6 < dy < -0.2:
                    c = (60, 86, 102)
                img[y][x] = K.jitter(c, rng, 3)
            elif d <= 1.3:
                img[y][x] = K.mix(img[y][x], (48, 46, 44), 0.5)    # damp rim
    K.put(img, 12, 14, (170, 200, 210))
    K.put(img, 13, 14, (130, 160, 175))
    K.put(img, 20, 19, (120, 150, 165))
    return img


def _mushroom(img, x, y, h, cw, cap, stem=(212, 202, 182)):
    """A glowing cave mushroom: stem from (x, y) up h pixels, a domed cap 2*cw+1 wide."""
    K.put(img, x + 1, y + 1, (30, 34, 30))
    K.put(img, x + 2, y + 1, (30, 34, 30))
    K.rect(img, x - 1, y - h, x + 1, y, stem)
    K.rect(img, x + 1, y - h, x + 1, y, K.add(stem, -46))
    K.rect(img, x - 1, y - h, x - 1, y, K.add(stem, 18))
    ch = max(3, cw - 1)
    for yy in range(ch):
        half = int(round(cw * math.sqrt(1 - ((ch - 1 - yy) / float(ch)) ** 2))) if yy < ch - 1 else cw
        for xx in range(-half, half + 1):
            k = xx / float(cw)
            c = K.mul(cap, 1.18) if k < -0.3 and yy < ch - 1 else cap if k < 0.35 else K.mul(cap, 0.7)
            K.put(img, x + xx, y - h - ch + yy, c)
    for xx in range(-cw + 1, cw):
        K.put(img, x + xx, y - h, K.mul(cap, 0.5))               # gills under the rim
    K.put(img, x - cw // 2, y - h - ch + 1, (235, 255, 252))     # glints and spots
    K.put(img, x + 1, y - h - ch + 2, (200, 240, 240))
    if cw >= 4:
        K.put(img, x - 2, y - h - 2, (200, 240, 240))


def mushroom_patch(picked=False):
    img = cave_floor_damp()
    spots = [(9, 23, 4, 4, (80, 196, 206)), (18, 27, 6, 5, (100, 210, 220)), (25, 22, 4, 4, (70, 176, 196)),
             (13, 15, 3, 3, (90, 200, 214)), (22, 13, 4, 3, (84, 190, 210)), (6, 13, 2, 3, (70, 176, 196))]
    if not picked:
        for y in range(S):                                           # faint glow
            for x in range(S):
                d = ((x - 16) ** 2 + (y - 19) ** 2) ** 0.5
                if d < 15:
                    img[y][x] = K.mix(img[y][x], (80, 170, 170), 0.34 * (1 - d / 15.0))
        for x, y, h, w, cap in sorted(spots, key=lambda s: s[1]):
            _mushroom(img, x, y, h, w, cap)
    else:
        for x, y, _, _, _ in spots:
            K.rect(img, x - 1, y - 1, x + 1, y, (176, 166, 150))
            K.rect(img, x - 1, y - 1, x + 1, y - 1, (214, 204, 186))
            K.put(img, x + 2, y, (40, 36, 32))
    return img


# ---------------------------------------------------------------- rocks to mine
def ore_rock(with_ore=True, flecks=None, seed=505, boulder_col=None):
    """flecks: (base, light, dark) colours of the ore; with_ore=False = mined out (no ore)."""
    img = cave_floor()
    rng = random.Random(seed if with_ore else 606)
    for y in range(25, 30):                                           # shadow
        for x in range(6, 31):
            dx, dy = (x - 19) / 12.0, (y - 27.0) / 2.4
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.mix(img[y][x], (30, 26, 22), 0.55)
    if boulder_col is None:
        boulder_col = ((112, 106, 100), (148, 142, 134), (70, 66, 62)) if with_ore else \
            ((92, 88, 84), (118, 112, 106), (58, 54, 50))
    b, l, d = boulder_col
    K.shaded_ellipse(img, 16, 17, 12, 10, b, l, d, rng=rng, noise=0.12, outline=(46, 42, 38))
    if with_ore:
        fb, fl, fd = flecks or ((178, 100, 52), (214, 140, 80), (128, 66, 34))
        n = 0
        while n < 9:
            x, y = 16 + rng.randrange(-8, 9), 17 + rng.randrange(-6, 7)
            if ((x - 16) / 9.5) ** 2 + ((y - 17) / 7.5) ** 2 > 1:
                continue
            r = rng.choice((1.2, 1.6, 2.0))
            K.shaded_ellipse(img, x, y, r, r * 0.9, fb, fl, fd, rng=rng)
            n += 1
    else:
        for x, y in ((12, 13), (13, 14), (14, 15), (15, 15), (16, 16), (19, 18), (20, 19), (21, 21)):
            img[y][x] = (44, 40, 36)
    return img


def gem_rock():
    img = ore_rock(True, flecks=((150, 110, 190), (200, 170, 240), (90, 60, 130)), seed=515,
                   boulder_col=((100, 98, 104), (136, 134, 142), (62, 60, 66)))
    crystals = [  # base x, base y, height, lean, colours (light, mid, dark)
        (11, 21, 11, -3, ((190, 245, 255), (90, 190, 230), (40, 110, 160))),
        (17, 19, 15, 1, ((236, 200, 255), (160, 110, 220), (90, 50, 150))),
        (22, 22, 10, 3, ((200, 255, 220), (80, 200, 130), (30, 120, 70))),
        (14, 25, 6, -2, ((236, 200, 255), (160, 110, 220), (90, 50, 150))),
    ]
    for bx, by, h, lean, (cl, cm, cd) in crystals:
        for i in range(h):
            t = i / float(h)
            w = max(1, int(round(2.4 * (1 - t) + 0.6)))
            cx = bx + lean * t
            for dx in range(-w, w + 1):
                c = cl if dx < 0 else cm if dx == 0 else cd
                if i >= h - 1:
                    c = (255, 255, 255)
                K.put(img, int(round(cx + dx)), by - i, c)
            K.put(img, int(round(cx - w - 1)), by - i, (40, 36, 50))
            K.put(img, int(round(cx + w + 1)), by - i, (30, 26, 40))
        K.put(img, bx - 1, by - h // 2, (255, 255, 255))
    return img


# ---------------------------------------------------------------- mine workings
def track(horizontal=False):
    img = cave_floor_gravel()
    wood, wl, wd = (112, 76, 42), (140, 100, 58), (70, 46, 24)
    for s in range(4):                                # sleepers every 8px: seamless along the track
        y0 = s * 8 + 2
        for y in range(y0, y0 + 4):
            for x in range(5, 27):
                c = wl if y == y0 else wd if y == y0 + 3 else wood
                if (x * 5 + y * 3) % 11 == 0:
                    c = K.add(c, -14)
                img[y][x] = c
        for x in range(6, 27):
            img[y0 + 4][x] = K.mix(img[y0 + 4][x], (30, 26, 22), 0.5)
    for rx in (9, 21):
        for y in range(S):
            img[y][rx - 1] = (60, 60, 66)
            img[y][rx] = (196, 196, 204)
            img[y][rx + 1] = (146, 146, 154)
            img[y][rx + 2] = (84, 84, 90)
    if horizontal:
        img = [[img[x][y] for x in range(S)] for y in range(S)]
    return img


def mine_support():
    img = cave_floor(seed=383, pebbles=3, cracks=1)
    wood, wl, wd, wo = (120, 82, 44), (152, 108, 62), (78, 52, 28), (46, 30, 16)
    for x0 in (1, 27):
        for y in range(0, S):
            K.put(img, x0 + 4, y, K.add(img[y][min(31, x0 + 4)], -28))  # shadow
            for x in range(x0, x0 + 4):
                c = wl if x == x0 else wd if x == x0 + 3 else wood
                if y % 9 == 4 and x == x0 + 1:
                    c = wd                                          # grain
                img[y][x] = c
            img[y][x0 - 1] = wo
    for i in range(7):                                               # braces
        for x0, d in ((5, 1), (26, -1)):
            K.put(img, x0 + d * i, 6 + i, wd)
            K.put(img, x0 + d * i, 7 + i, wood)
    for y in range(1, 6):                                            # cross beam
        for x in range(0, S):
            c = wl if y == 1 else wd if y == 5 else wood
            if x % 11 == 3 and y == 3:
                c = wd
            img[y][x] = c
    for x in range(S):
        img[6][x] = K.add(img[6][x], -30)
        img[0][x] = wo
    return img


# ---------------------------------------------------------------- ladders and holes
def _ladder(img, top, bottom, x0=9, x1=21, step=6, rung_from=None):
    wood, wl, wd = (130, 84, 40), (168, 116, 62), (78, 48, 20)
    for y in range(rung_from if rung_from is not None else top + 3, bottom, step):
        for x in range(x0 + 3, x1):
            img[y][x] = wood
            img[y + 1][x] = wd
    for rx in (x0, x1):
        for y in range(top, bottom + 1):
            img[y][rx] = wl
            img[y][rx + 1] = wood
            img[y][rx + 2] = wd


def ladder_up_cave():
    img = cave_floor(seed=393, pebbles=2, cracks=0)
    for y in range(0, 11):                                          # the shaft above, dark
        for x in range(5, 27):
            t = y / 11.0
            edge = min(x - 5, 26 - x) / 4.0
            img[y][x] = K.mix((8, 7, 6), img[y][x], min(1, t * t + max(0, 1 - edge) * 0.6))
    _ladder(img, 0, 28)
    for x in range(8, 25):
        img[29][x] = K.mix(img[29][x], (26, 22, 18), 0.6)
        img[30][x] = K.mix(img[30][x], (26, 22, 18), 0.3)
    return img


def _pit(img, x0, y0, x1, y1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            img[y][x] = (24, 20, 18)
    _ladder(img, y0, y1 - 2, x0 + 2, x1 - 4, step=5, rung_from=y0 + 1)
    for y in range(y0, y1 + 1):                                     # the ladder fades into the dark
        for x in range(x0, x1 + 1):
            t = (y - y0) / float(y1 - y0)
            img[y][x] = K.mix(img[y][x], (0, 0, 0), min(1, 0.15 + t * 1.2))
    wood, wl, wd = (120, 80, 40), (156, 108, 58), (70, 44, 20)
    for x in range(x0 - 2, x1 + 3):
        img[y0 - 2][x] = wl
        img[y0 - 1][x] = wood
        img[y1 + 1][x] = wood
        img[y1 + 2][x] = wd
    for y in range(y0 - 2, y1 + 3):
        img[y][x0 - 2] = wl
        img[y][x0 - 1] = wood
        img[y][x1 + 1] = wood
        img[y][x1 + 2] = wd
    for x, y in ((x0 - 2, y0 - 2), (x1 + 2, y0 - 2), (x0 - 2, y1 + 2), (x1 + 2, y1 + 2)):
        img[y][x] = (60, 58, 56)                                      # nails


def hatch_cave():
    img = cave_floor(seed=403, pebbles=2, cracks=0)
    _pit(img, 9, 8, 22, 22)
    return img


def _rim_hole(img, seed):
    rng = random.Random(seed)
    inside = lambda x, y: ((x + 0.5 - 16) / 10.5) ** 2 + ((y + 0.5 - 16) / 9.5) ** 2 <= 1.0
    for y in range(S):
        for x in range(S):
            if inside(x, y):
                img[y][x] = (24, 20, 18)
    _ladder(img, 7, 24, 11, 19, step=5, rung_from=8)
    for y in range(S):
        for x in range(S):
            if inside(x, y):
                t = (y - 6) / 20.0
                img[y][x] = K.mix(img[y][x], (0, 0, 0), min(1, max(0.1, t * 1.25)))
    for i in range(17):                                              # ring of stones
        a = i / 17.0 * 2 * math.pi
        cx, cy = 16 + 12.0 * math.cos(a), 16 + 11.0 * math.sin(a)
        r = rng.uniform(2.1, 2.9)
        b = rng.choice([(122, 116, 108), (108, 102, 96), (134, 126, 116)])
        K.shaded_ellipse(img, cx, cy, r, r * 0.85, b, K.add(b, 30), K.add(b, -40), rng=rng, outline=(54, 50, 46))
    return img


def hole_grass():
    return _rim_hole(copy_tile("Grass001"), 413)


def hole_dirt():
    return _rim_hole(copy_tile("Dirt001"), 423)


# ---------------------------------------------------------------- surface gathering
def _leafy(img, rng, cx, cy, rx, ry, dark=(28, 66, 18), mid=(52, 104, 30), light=(86, 146, 46), outline=(18, 40, 10)):
    for y in range(S):                                             # shadow
        for x in range(S):
            dx, dy = (x + 0.5 - cx - 2) / rx, (y + 0.5 - cy - 4) / (ry * 0.75)
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.mix(img[y][x], (20, 34, 10), 0.45)
    clumps = []
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0, 0.72)
        clumps.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr, rng.uniform(3.4, 4.8)))
    clumps.sort(key=lambda c: c[1])
    for x, y, r in clumps:
        K.shaded_ellipse(img, x, y, r, r * 0.9, mid, light, dark, rng=rng, noise=0.2, outline=outline)
    for _ in range(18):
        x, y = int(cx + rng.uniform(-rx * 0.7, rx * 0.7)), int(cy + rng.uniform(-ry * 0.7, ry * 0.5))
        K.put(img, x, y, K.add(light, 24))


def _trunk(img, x0, x1, top, bottom, light, mid, dark):
    for y in range(top, bottom + 1):
        for x in range(x0, x1 + 1):
            img[y][x] = light if x == x0 else dark if x == x1 else mid
    for x in (x0 - 1, x1 + 1):                                     # roots
        K.put(img, x, bottom, dark)


def oak_tree():
    """A broad oak: a thick trunk and a wide, olive-green crown (Woodcutting 10)."""
    img = copy_tile("Grass001")
    rng = random.Random(611)
    _trunk(img, 13, 18, 18, 29, (150, 104, 60), (112, 74, 40), (72, 46, 22))
    _leafy(img, rng, 16, 12, 14, 11, dark=(46, 70, 20), mid=(84, 112, 38), light=(128, 152, 62), outline=(26, 40, 10))
    for x, y in ((8, 9), (22, 7), (12, 15), (24, 14)):              # a few acorns
        K.put(img, x, y, (150, 100, 40))
    return img


def willow_tree():
    """A weeping willow: a pale yellow-green crown with long trailing strands (Woodcutting 20)."""
    img = copy_tile("Grass001")
    rng = random.Random(622)
    _trunk(img, 14, 17, 18, 29, (140, 120, 80), (104, 88, 58), (70, 58, 36))
    _leafy(img, rng, 16, 10, 12, 8, dark=(78, 110, 34), mid=(124, 160, 60), light=(176, 206, 104), outline=(44, 64, 18))
    for k in range(13):                                              # the strands hanging down
        x = 5 + k * 2 + rng.randint(-1, 1)
        top = 10 + abs(k - 6) // 2
        length = rng.randint(9, 15)
        for y in range(top, min(31, top + length)):
            col = (150, 186, 80) if (y + k) % 3 else (104, 140, 50)
            K.put(img, x + (1 if y > top + length // 2 and k % 2 else 0), y, col)
    return img


def yew_tree():
    """An ancient yew: a dark, dense blue-green crown with red berries (Woodcutting 35)."""
    img = copy_tile("Grass001")
    rng = random.Random(633)
    _trunk(img, 13, 18, 19, 29, (136, 70, 52), (102, 48, 34), (64, 28, 18))
    _leafy(img, rng, 16, 12, 13, 12, dark=(14, 40, 30), mid=(28, 70, 52), light=(54, 106, 80), outline=(8, 22, 16))
    for x, y in ((9, 8), (20, 6), (24, 13), (12, 17), (18, 14), (7, 14), (22, 19)):
        K.shaded_ellipse(img, x + 0.5, y + 0.5, 1.2, 1.2, (200, 30, 40), (250, 110, 110), (120, 10, 20))
    return img


def berry_bush(berries=True):
    img = copy_tile("Grass001")
    rng = random.Random(433)
    _leafy(img, rng, 16, 15, 11, 10)
    if berries:
        for x, y in [(9, 11), (14, 8), (20, 10), (23, 15), (11, 17), (17, 14), (21, 20), (13, 21), (7, 15), (18, 19),
                     (25, 11)]:
            K.shaded_ellipse(img, x + 0.5, y + 0.5, 1.7, 1.7, (190, 30, 60), (240, 90, 120), (110, 10, 40))
            K.put(img, x, y, (255, 200, 215))
    else:
        for x, y in [(12, 10), (20, 16), (10, 19)]:
            K.put(img, x, y, (150, 170, 80))
    return img


def herb_patch(picked=False):
    img = copy_tile("Grass001")
    rng = random.Random(443)
    if picked:
        for x, y in [(12, 18), (16, 20), (20, 17), (15, 15), (19, 22)]:
            K.rect(img, x, y - 1, x, y, (80, 130, 44))
            K.put(img, x, y + 1, (40, 70, 22))
        return img
    for y in range(S):
        for x in range(S):
            if ((x - 17) / 10.0) ** 2 + ((y - 21) / 4.5) ** 2 <= 1:
                img[y][x] = K.mix(img[y][x], (24, 44, 12), 0.4)
    leaf, ll, ld = (74, 156, 62), (126, 206, 96), (36, 92, 30)
    for i in range(18):
        a = -math.pi * (i + 0.5) / 18.0 + rng.uniform(-0.08, 0.08)       # fan of leaves, upwards
        ln = rng.uniform(9, 13) * (0.7 + 0.3 * abs(math.sin(a)))
        for t in range(int(ln)):
            x = 16 + math.cos(a) * t
            y = 20 + math.sin(a) * t * 0.9
            c = ll if t < ln * 0.35 else leaf if (i % 2) else K.add(leaf, -12)
            K.put(img, int(round(x)), int(round(y)), c)
            K.put(img, int(round(x + 1)), int(round(y)), ld if t > 1 else c)
            if 2 < t < ln - 2:
                K.put(img, int(round(x - 1)), int(round(y)), ll if i % 2 else leaf)
    for x, y in [(11, 9), (20, 10), (7, 15), (24, 15), (16, 7), (13, 13), (19, 14)]:
        K.put(img, x, y, (240, 240, 255))
        K.put(img, x + 1, y, (190, 170, 240))
        K.put(img, x, y + 1, (190, 170, 240))
        K.put(img, x + 1, y + 1, (250, 220, 90))
    return img


def wheat(cut=False):
    img = copy_tile("Dirt001")
    rng = random.Random(453 if not cut else 463)
    gold, gl, gd, stalk = (214, 178, 84), (246, 214, 120), (160, 120, 50), (176, 150, 70)
    for row in range(4):
        by = row * 8 + 7
        for col in range(8):
            x = col * 4 + (row % 2) * 2 + rng.choice((0, 1))
            if cut:
                for y in range(by - 2, by + 1):
                    K.put(img, x, y, (200, 176, 108) if y < by else (130, 104, 56), wrap=True)
                K.put(img, x + 1, by + 1, (96, 70, 42), wrap=True)
                continue
            h = rng.randrange(7, 10)
            for y in range(by - h, by + 1):
                K.put(img, x, y, stalk if y > by - h + 3 else gold, wrap=True)
            for y in range(by - h, by - h + 4):                      # the ear
                K.put(img, x - 1, y, gl if y % 2 == 0 else gold, wrap=True)
                K.put(img, x + 1, y, gd if y % 2 == 0 else gold, wrap=True)
            K.put(img, x, by - h - 1, gl, wrap=True)
            K.put(img, x + 1, by + 1, (90, 66, 40), wrap=True)       # shadow at the foot
    return img


def nest(eggs=True):
    img = copy_tile("Grass001")
    rng = random.Random(473)
    for y in range(S):                                               # shadow
        for x in range(S):
            dx, dy = (x + 0.5 - 17) / 12.5, (y + 0.5 - 19.5) / 7.0
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.mix(img[y][x], (30, 40, 12), 0.45)
    for i in range(320):                                            # straw strands round a hollow
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.55, 1.0)
        x, y = 16 + math.cos(a) * 11 * r, 17 + math.sin(a) * 6.5 * r
        ln = rng.randrange(2, 5)
        ang = a + math.pi / 2 + rng.uniform(-0.5, 0.5)
        c = rng.choice([(214, 184, 100), (190, 156, 76), (236, 210, 130), (160, 124, 58)])
        if math.sin(a) < -0.2:
            c = K.add(c, -30)                                       # far side in shade
        for t in range(ln):
            K.put(img, int(x + math.cos(ang) * t), int(y + math.sin(ang) * t * 0.6), c)
    for y in range(S):                                               # hollow
        for x in range(S):
            dx, dy = (x + 0.5 - 16) / 7.0, (y + 0.5 - 16.5) / 3.6
            if dx * dx + dy * dy <= 1:
                img[y][x] = K.jitter((120, 92, 44), rng, 8)
    if eggs:
        for x, y in [(13, 15), (19, 15.5), (16, 18)]:
            K.shaded_ellipse(img, x, y, 2.6, 3.2, (236, 226, 204), (255, 252, 240), (190, 176, 150),
                             outline=(140, 124, 96))
    return img


# ---------------------------------------------------------------- scenery (on grass): flowers, rocks, ruins, graves...
def _flowers(seed, colours, count=11):
    img = copy_tile("Grass001")
    rng = random.Random(seed)
    for _ in range(count):
        x, y = rng.randint(3, 28), rng.randint(4, 28)
        c = rng.choice(colours)
        K.put(img, x, y + 1, (40, 90, 30))                        # stalk
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1)):
            K.put(img, x + dx, y + dy, c)
        K.put(img, x, y, (250, 230, 120) if c != (250, 230, 120) else (230, 140, 40))
    return img


def tall_grass():
    img = copy_tile("Grass001")
    rng = random.Random(712)
    for _ in range(26):
        x, y = rng.randint(2, 29), rng.randint(8, 30)
        h = rng.randint(4, 8)
        lean = rng.choice((-1, 0, 1))
        for i in range(h):
            K.put(img, x + (lean if i > h // 2 else 0), y - i, (110, 150, 50) if i > h // 2 else (70, 110, 34))
    return img


def mushroom_ring():
    img = copy_tile("Grass001")
    for k in range(9):
        a = k * 2 * math.pi / 9
        x, y = 16 + math.cos(a) * 10, 17 + math.sin(a) * 7
        K.shaded_ellipse(img, x, y - 1, 2.2, 1.4, (200, 40, 40), (250, 120, 110), (130, 20, 20))
        K.put(img, int(x), int(y), (236, 230, 210))
        K.put(img, int(x) - 1, int(y) - 2, (255, 255, 255))
    return img


def _shadow(img, cx, cy, rx, ry):
    for y in range(32):
        for x in range(32):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                img[y][x] = K.mix(img[y][x], (20, 34, 10), 0.45)


def rock():
    img = copy_tile("Grass001")
    rng = random.Random(721)
    _shadow(img, 18, 24, 11, 4)
    K.shaded_ellipse(img, 16, 18, 10, 8, (128, 124, 116), (172, 168, 158), (80, 76, 70), rng=rng, noise=0.12, outline=(46, 44, 40))
    for x, y in ((11, 15), (12, 14), (20, 19), (21, 20), (13, 21)):          # moss
        K.put(img, x, y, (90, 130, 50))
    return img


def bush():
    img = copy_tile("Grass001")
    rng = random.Random(731)
    _leafy(img, rng, 16, 17, 10, 8, dark=(30, 74, 26), mid=(56, 112, 40), light=(96, 150, 60))
    return img


def fallen_log():
    img = copy_tile("Grass001")
    _shadow(img, 17, 22, 13, 4)
    for x in range(4, 27):
        for y in range(14, 21):
            t = (y - 14) / 6.0
            img[y][x] = (156, 108, 60) if t < 0.3 else (118, 78, 40) if t < 0.75 else (80, 50, 24)
    for y in range(14, 21):                                                    # the cut end
        for x in range(25, 29):
            if ((x - 26.5) / 2.2) ** 2 + ((y - 17) / 3.6) ** 2 <= 1:
                img[y][x] = (210, 170, 110) if ((x - 26.5) ** 2 + (y - 17) ** 2) > 2 else (170, 120, 70)
    for x in (8, 14, 19):
        K.put(img, x, 13, (70, 120, 40)); K.put(img, x + 1, 13, (70, 120, 40))   # moss
    return img


def standing_stone():
    img = copy_tile("Grass001")
    _shadow(img, 18, 27, 8, 3)
    for y in range(3, 28):
        w = 5 if y > 6 else 3 + (y - 3) // 2
        for x in range(16 - w, 16 + w):
            img[y][x] = (150, 148, 140) if x < 15 else (118, 116, 110) if x < 18 else (86, 84, 80)
    for x, y in ((14, 10), (15, 11), (16, 12), (17, 11), (16, 15), (15, 16), (14, 17), (15, 18), (16, 19)):   # spirals
        K.put(img, x, y, (70, 160, 180))
    return K.outline_img(img, (40, 40, 38)) if False else img


def ruined_wall(broken=False):
    img = copy_tile("Grass001")
    top = 8 if not broken else 16
    for y in range(top, 30):
        for x in range(0, 32):
            if broken and y < 20 and (x // 6) % 2:
                continue
            row, col = (y - top) // 5, (x + ((y - top) // 5) * 4) // 8
            edge = (y - top) % 5 == 0 or (x + ((y - top) // 5) * 4) % 8 == 0
            img[y][x] = (90, 86, 80) if edge else ((150, 144, 132) if (row + col) % 3 else (130, 124, 114))
    for x, y in ((3, top + 1), (12, top + 6), (24, top + 3), (18, top + 11)):
        K.put(img, x, y, (80, 120, 50))
    return img


def grave(kind):
    img = copy_tile("Grass001")
    _shadow(img, 17, 26, 8, 3)
    stone, light, dark = (150, 150, 156), (190, 190, 196), (96, 96, 104)
    if kind == 1:                                   # a round-topped headstone
        for y in range(8, 25):
            for x in range(10, 22):
                if y > 12 or ((x - 15.5) / 6) ** 2 + ((y - 13) / 5) ** 2 <= 1:
                    img[y][x] = light if x < 13 else dark if x > 19 else stone
        for x in range(13, 19):
            K.put(img, x, 15, dark); K.put(img, x, 18, dark)
    elif kind == 2:                                 # a cross
        for y in range(6, 25):
            for x in range(14, 18):
                img[y][x] = light if x == 14 else stone
        for y in range(10, 13):
            for x in range(9, 23):
                img[y][x] = light if y == 10 else stone
    else:                                           # an old, leaning slab with a mound of earth
        for y in range(20, 28):
            for x in range(8, 25):
                if ((x - 16) / 8) ** 2 + ((y - 24) / 3.5) ** 2 <= 1:
                    img[y][x] = (110, 84, 50) if y > 22 else (130, 100, 64)
        for y in range(9, 22):
            off = (21 - y) // 4
            for x in range(11 + off, 20 + off):
                img[y][x] = stone if x > 12 + off else light
    return img


def fence(vertical=False):
    img = copy_tile("Grass001")
    wood, dark, light = (150, 104, 56), (100, 66, 32), (186, 140, 86)
    if not vertical:
        for x in range(32):
            for y in (13, 19):
                img[y][x] = light; img[y + 1][x] = wood
        for x in (4, 20):
            for y in range(9, 26):
                img[y][x] = wood; img[y][x + 1] = dark
    else:
        for y in range(32):
            for x in (14,):
                img[y][x] = light; img[y][x + 1] = wood; img[y][x + 2] = dark
        for y in (6, 22):
            for x in range(12, 20):
                img[y][x] = wood; img[y + 1][x] = dark
    return img


def well():
    img = copy_tile("Grass001")
    _shadow(img, 17, 26, 12, 4)
    for y in range(14, 27):                         # the round stone wall
        for x in range(5, 27):
            if ((x - 16) / 11) ** 2 + ((y - 20) / 6.5) ** 2 <= 1:
                inner = ((x - 16) / 8) ** 2 + ((y - 18) / 3.5) ** 2 <= 1
                brick = (y // 3 + x // 5) % 2
                img[y][x] = (20, 30, 50) if inner else ((150, 146, 138) if brick else (122, 118, 110))
    for x in (6, 25):                               # posts and a little roof
        for y in range(5, 19):
            img[y][x] = (110, 74, 40); img[y][x + 1] = (80, 50, 24)
    for y in range(2, 7):
        for x in range(4 + (6 - y), 29 - (6 - y)):
            img[y][x] = (150, 60, 40) if (x + y) % 3 else (120, 44, 30)
    for x in range(8, 25):
        img[9][x] = (90, 60, 30)                    # the winch
    for y in range(10, 16):
        img[y][16] = (200, 190, 160)                # the rope
    return img


def pond():
    img = [[(40, 90, 150) if (x * 7 + y * 3) % 11 else (60, 120, 180) for x in range(32)] for y in range(32)]
    rng = random.Random(751)
    for _ in range(4):                              # lily pads
        x, y = rng.randint(6, 25), rng.randint(6, 25)
        K.shaded_ellipse(img, x, y, 3.4, 2.4, (60, 140, 50), (110, 190, 80), (30, 90, 30))
        if rng.random() < 0.5:
            K.put(img, x, y - 1, (250, 200, 230)); K.put(img, x + 1, y - 1, (250, 160, 200))
    return img


def haystack():
    img = copy_tile("Grass001")
    _shadow(img, 17, 27, 12, 3)
    for y in range(6, 28):
        w = min(12, 4 + (y - 6))
        for x in range(16 - w, 16 + w):
            img[y][x] = (230, 196, 90) if (x + y * 2) % 5 else (196, 160, 60)
    return img


def scarecrow():
    img = copy_tile("Grass001")
    for y in range(8, 30):
        img[y][15] = (110, 74, 40); img[y][16] = (80, 50, 24)          # the pole
    for x in range(6, 26):
        img[11][x] = (110, 74, 40)                                     # the arms
    for y in range(10, 22):                                            # a ragged coat
        for x in range(11, 21):
            img[y][x] = (110, 60, 40) if (x + y) % 4 else (80, 44, 30)
    for x, y in ((6, 12), (7, 13), (24, 12), (25, 13)):                # straw hands
        img[y][x] = (230, 196, 90)
    K.shaded_ellipse(img, 15.5, 6, 3.6, 3.6, (230, 200, 120), (250, 230, 160), (180, 150, 80))   # sack head
    for x in range(10, 22):
        img[3][x] = (90, 60, 30)                                       # hat brim
    for y in range(0, 3):
        for x in range(12, 20):
            img[y][x] = (110, 74, 40)
    K.put(img, 14, 6, (40, 30, 20)); K.put(img, 17, 6, (40, 30, 20))
    return img


def tent(colour=(170, 140, 90)):
    img = copy_tile("Grass001")
    _shadow(img, 17, 28, 14, 3)
    for y in range(4, 29):
        w = (y - 4) * 13 // 24
        for x in range(16 - w, 16 + w + 1):
            img[y][x] = K.mul(colour, 1.1) if x < 16 else K.mul(colour, 0.85)
    for y in range(16, 29):                                            # the dark doorway
        w = (y - 16) * 4 // 12
        for x in range(16 - w, 16 + w + 1):
            img[y][x] = (40, 30, 20)
    img[3][16] = (100, 70, 40); img[2][16] = (100, 70, 40)
    return img


def crate():
    img = copy_tile("Grass001")
    _shadow(img, 18, 26, 11, 3)
    for y in range(8, 26):
        for x in range(6, 26):
            edge = x in (6, 25) or y in (8, 25) or x == y + 2 - 4 or x == 31 - y
            img[y][x] = (110, 74, 36) if edge else ((176, 130, 76) if (y // 3) % 2 else (156, 112, 62))
    return img


def barrel():
    img = copy_tile("Grass001")
    _shadow(img, 18, 27, 9, 3)
    for y in range(6, 27):
        for x in range(8, 24):
            dx = (x - 15.5) / 8
            if abs(dx) <= 1:
                c = (150, 100, 52) if dx < -0.3 else (120, 80, 40) if dx < 0.4 else (90, 58, 28)
                if y in (9, 10, 21, 22):
                    c = (90, 90, 96)
                img[y][x] = c
    for x in range(9, 23):
        img[6][x] = (176, 128, 72)
    return img


DECOR = {
    "Flowers001": lambda: _flowers(701, [(250, 230, 120), (245, 245, 240)]),
    "Flowers002": lambda: _flowers(702, [(220, 40, 40), (170, 80, 190)]),
    "Flowers003": lambda: _flowers(703, [(90, 120, 230), (140, 170, 250)]),
    "Tall_Grass001": tall_grass,
    "Mushroom_Ring001": mushroom_ring,
    "Rock001": rock,
    "Bush001": bush,
    "Fallen_Log001": fallen_log,
    "Standing_Stone001": standing_stone,
    "Ruined_Wall001": ruined_wall,
    "Ruined_Wall002": lambda: ruined_wall(True),
    "Grave001": lambda: grave(1),
    "Grave002": lambda: grave(2),
    "Grave003": lambda: grave(3),
    "Fence001": fence,
    "Fence002": lambda: fence(True),
    "Well001": well,
    "Pond001": pond,
    "Haystack001": haystack,
    "Scarecrow001": scarecrow,
    "Tent001": tent,
    "Tent002": lambda: tent((120, 96, 60)),
    "Crate001": crate,
    "Barrel001": barrel,
}


# ---------------------------------------------------------------- table
TILES = {
    "Cave_Floor001": cave_floor,
    "Cave_Floor002": cave_floor_gravel,
    "Cave_Floor003": cave_floor_damp,
    "Cave_Wall001": cave_wall,
    "Cave_Wall002": cave_wall_face,
    "Cave_Wall003": cave_wall_torch,
    "Cave_Rubble001": rubble,
    "Stalagmite001": stalagmite,
    "Cave_Pool001": cave_pool,
    "Cave_Puddle001": cave_puddle,
    "Mushroom_Patch001": mushroom_patch,
    "Mushroom_Patch002": lambda: mushroom_patch(True),
    "Ore_Rock001": ore_rock,
    "Ore_Rock002": lambda: ore_rock(False),
    "Copper_Rock001": lambda: ore_rock(True, ((64, 168, 126), (130, 226, 176), (196, 112, 60)), seed=525),
    "Coal_Rock001": lambda: ore_rock(True, ((30, 30, 34), (100, 100, 112), (10, 10, 12)), seed=535),
    "Gold_Rock001": lambda: ore_rock(True, ((226, 184, 50), (255, 238, 136), (150, 110, 20)), seed=545),
    "Gem_Rock001": gem_rock,
    "Tin_Rock001": lambda: ore_rock(True, ((150, 156, 150), (206, 212, 204), (86, 92, 88)), seed=555,
                                    boulder_col=((104, 98, 92), (140, 134, 126), (64, 60, 56))),
    "Silver_Rock001": lambda: ore_rock(True, ((214, 220, 232), (255, 255, 255), (130, 138, 156)), seed=565,
                                       boulder_col=((86, 82, 80), (118, 112, 108), (52, 48, 46))),
    "Mithril_Rock001": lambda: ore_rock(True, ((56, 170, 176), (150, 240, 236), (26, 92, 120)), seed=575,
                                        boulder_col=((70, 70, 88), (100, 100, 122), (40, 40, 54))),
    "Mine_Track001": track,
    "Mine_Track002": lambda: track(True),
    "Mine_Support001": mine_support,
    "Ladder004": ladder_up_cave,
    "Ladder005": hatch_cave,
    "Ladder006": hole_grass,
    "Ladder007": hole_dirt,
    "Oak_Tree001": oak_tree,
    "Willow_Tree001": willow_tree,
    "Yew_Tree001": yew_tree,
    "Berry_Bush001": berry_bush,
    "Berry_Bush002": lambda: berry_bush(False),
    "Herb_Patch001": herb_patch,
    "Herb_Patch002": lambda: herb_patch(True),
    "Nest001": nest,
    "Nest002": lambda: nest(False),
}

TILES.update(DECOR)
# The wheat field, stubble, haystack and cliffs: redrawn in farm_tiles.py
from farm_tiles import TILES as FARM_TILES  # noqa: E402
TILES.update(FARM_TILES)
# The villages' walls, doors and roofs: house_tiles.py
from house_tiles import TILES as HOUSE_TILES  # noqa: E402
TILES.update(HOUSE_TILES)
# Furniture, stairs and the city walls: interior_tiles.py
from interior_tiles import TILES as INTERIOR_TILES  # noqa: E402
TILES.update(INTERIOR_TILES)
# King Tyron's palace on the Royal Isle: palace_tiles.py
from palace_tiles import TILES as PALACE_TILES  # noqa: E402
TILES.update(PALACE_TILES)
# The villages' character: ivy, window boxes, lanterns, shop signs, flower beds, benches: village_decor.py
from village_decor import TILES as DECOR_TILES  # noqa: E402
TILES.update(DECOR_TILES)
# Rocks and pebbles for the countryside: nature_tiles.py
from nature_tiles import TILES as NATURE_TILES  # noqa: E402
TILES.update(NATURE_TILES)
# Furnishings for a house's trade: interior_props.py
from interior_props import TILES as PROP_TILES  # noqa: E402
TILES.update(PROP_TILES)

# Tiles that repeat next to themselves (checked for seams in the 4x4 preview)
SEAMLESS = ["Cave_Floor001", "Cave_Floor002", "Cave_Floor003", "Cave_Wall001", "Cave_Wall002", "Cave_Pool001",
            "Mine_Track001", "Mine_Track002"]
