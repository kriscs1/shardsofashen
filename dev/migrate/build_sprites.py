"""Generate the new entity sprites (sprites\\Entities\\*.png): items, crafting stations, NPCs and monsters.

Run:  python -I "dev\\migrate\\build_sprites.py" [--preview]
Deterministic and re-runnable: only the sprites in SPRITES are (re)written, and only when they change.
--preview writes dev\\Renders\\Entities preview.png (all of them on a checkerboard, 3x).

Format (as every LB sprite here): 24-bit BMP 32 x 64; top half = mask (black = drawn, white = see-through),
bottom half = image (black where see-through). Items are small shaded objects; NPCs are little standing figures
in the style of the existing ones (Miner, Farmer, Baker...). Some items are recolours of existing sprites
(Iron_Ore, Iron_Bar, Ruby, Raw_Fish, Cooked_Fish, Basic_Potion, Bucket_of_Water) so they match exactly.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K
from common import p

S = 32
SPRITES = {}          # name -> function returning a 32x32 image (None = transparent)
INTERFACE = {"Heart", "Mana"}  # made here but saved in sprites\Interface (pictures that aren't entities, e.g. skill icons)


def sprite(name):
    def deco(fn):
        SPRITES[name] = fn
        return fn
    return deco


def art(rows, pal, ox=None, oy=0):
    return K.from_ascii(rows, pal, ox=ox, oy=oy)


def seg(img, x0, y0, x1, y1, width, light, mid, dark, cap=True):
    """A shaded stroke from (x0,y0) to (x1,y1): pixels within width/2 of the segment, lit on the upper-left side."""
    vx, vy = x1 - x0, y1 - y0
    ln = math.hypot(vx, vy) or 1
    nx, ny = -vy / ln, vx / ln            # normal
    if nx + ny > 0:                       # make the normal point up-left
        nx, ny = -nx, -ny
    for y in range(S):
        for x in range(S):
            px, py = x + 0.5 - x0, y + 0.5 - y0
            t = (px * vx + py * vy) / (ln * ln)
            if not cap and (t < 0 or t > 1):
                continue
            t = max(0, min(1, t))
            dx, dy = px - vx * t, py - vy * t
            d = math.hypot(dx, dy)
            if d <= width / 2.0:
                side = (dx * nx + dy * ny) / max(0.5, width / 2.0)
                img[y][x] = light if side > 0.3 else dark if side < -0.3 else mid


# ================================================================== recoloured items
def gm(name, stops):
    return K.gradient_map(K.load("Entities", name), stops)


@sprite("Copper_Ore")
def copper_ore():
    return gm("Iron_Ore", [(0.0, (40, 22, 12)), (0.3, (120, 64, 30)), (0.55, (196, 112, 58)), (0.8, (236, 170, 110)),
                           (1.0, (255, 220, 180))])


@sprite("Coal")
def coal():
    return gm("Iron_Ore", [(0.0, (6, 6, 8)), (0.35, (26, 26, 30)), (0.6, (52, 52, 60)), (0.85, (110, 110, 124)),
                           (1.0, (170, 170, 186))])


@sprite("Gold_Ore")
def gold_ore():
    img = gm("Iron_Ore", [(0.0, (44, 34, 20)), (0.3, (110, 92, 60)), (0.55, (156, 136, 96)), (1.0, (214, 200, 160))])
    rng = random.Random(7)
    pts = [(x, y) for y, r in enumerate(img) for x, c in enumerate(r) if c is not None]
    for _ in range(26):                                   # gold specks in the rock
        x, y = rng.choice(pts)
        img[y][x] = rng.choice([(250, 210, 60), (255, 240, 140), (210, 160, 30)])
    return img


@sprite("Copper_Bar")
def copper_bar():
    return gm("Iron_Bar", [(0.0, (30, 14, 6)), (0.25, (110, 52, 24)), (0.45, (176, 96, 50)), (0.7, (222, 144, 90)),
                           (1.0, (255, 214, 170))])


@sprite("Steel_Bar")
def steel_bar():
    return gm("Iron_Bar", [(0.0, (14, 18, 26)), (0.25, (70, 84, 100)), (0.45, (128, 146, 166)), (0.7, (186, 202, 220)),
                           (1.0, (245, 250, 255))])


@sprite("Gold_Bar")
def gold_bar():
    return gm("Iron_Bar", [(0.0, (40, 26, 4)), (0.25, (150, 104, 20)), (0.45, (214, 166, 40)), (0.7, (250, 214, 90)),
                           (1.0, (255, 250, 200))])


@sprite("Sapphire")
def sapphire():
    return K.hue_shift(K.load("Entities", "Ruby"), target_hue=0.62, sat_mul=1.0, val_mul=1.15)


@sprite("Emerald")
def emerald():
    return K.hue_shift(K.load("Entities", "Ruby"), target_hue=0.38, sat_mul=0.95, val_mul=1.15)


@sprite("Super_Potion")
def super_potion():
    return K.hue_shift(K.load("Entities", "Basic_Potion"), target_hue=0.58, pred=lambda c: max(c) - min(c) > 40)


@sprite("Strength_Potion")
def strength_potion():
    return K.hue_shift(K.load("Entities", "Basic_Potion"), target_hue=0.0, sat_mul=1.1, pred=lambda c: max(c) - min(c) > 40)


def fish_map(src, stops):
    img = K.load("Entities", src)
    out = K.gradient_map(img, stops)
    for y, r in enumerate(img):
        for x, c in enumerate(r):
            if c is not None and c[1] > c[0] + 30:                # keep the green eye
                out[y][x] = c
    return out


@sprite("Raw_Trout")
def raw_trout():
    img = fish_map("Raw_Fish", [(0.0, (30, 34, 20)), (0.35, (96, 110, 70)), (0.6, (170, 170, 130)),
                                (0.8, (236, 196, 186)), (1.0, (255, 236, 230))])
    rng = random.Random(11)
    pts = [(x, y) for y, r in enumerate(img) for x, c in enumerate(r) if c is not None and K.lum(c) < 0.62]
    for _ in range(16):
        x, y = rng.choice(pts)
        img[y][x] = (50, 44, 34)                              # trout spots
    return img


@sprite("Cooked_Trout")
def cooked_trout():
    return fish_map("Cooked_Fish", [(0.0, (40, 22, 10)), (0.35, (120, 70, 30)), (0.6, (190, 130, 70)),
                                    (0.85, (236, 190, 130)), (1.0, (255, 230, 190))])


@sprite("Raw_Cave_Eel")
def raw_eel():
    return eel((70, 60, 110), (150, 170, 200), (40, 34, 70))


@sprite("Cooked_Cave_Eel")
def cooked_eel():
    return eel((130, 80, 40), (220, 170, 110), (80, 46, 20))


def eel(back, belly, dark):
    img = K.new()
    pts = []
    for i in range(60):                                       # an S-shaped body
        t = i / 59.0
        x = 4 + t * 24
        y = 16 + math.sin(t * math.pi * 1.6 + 0.3) * 6
        pts.append((x, y, 2.6 - 1.6 * max(0, t - 0.6) / 0.4 if t > 0.6 else 2.6))
    for x, y, r in pts:
        K.shaded_ellipse(img, x, y, r, r, K.mix(back, belly, 0.4), belly, back)
    for x, y, r in pts[::3]:
        K.put(img, int(x), int(y - r + 1), K.mix(back, (255, 255, 255), 0.2))
    K.put(img, 5, 14, (240, 240, 120))                         # eye
    K.put(img, 5, 15, (20, 20, 20))
    for x, y, r in pts[8:50:4]:                                # fin along the back
        K.put(img, int(x), int(y - r - 0.5), dark)
    return K.outline_img(img, K.mul(dark, 0.6))


@sprite("Bucket_of_Milk")
def bucket_of_milk():
    img = K.load("Entities", "Bucket_of_Water")
    out = K.copy(img)
    for y, r in enumerate(img):
        for x, c in enumerate(r):
            if c is not None and c[2] > c[0] + 25 and c[2] > c[1]:     # the bluish water
                l = K.lum(c)
                out[y][x] = K.mix((214, 214, 206), (255, 255, 250), min(1, l * 1.3))
    return out


# ================================================================== drawn items
@sprite("Berries")
def berries():
    img = K.new()
    seg(img, 15, 7, 13, 13, 1.5, (110, 170, 60), (80, 130, 40), (50, 90, 20))
    for (x, y) in [(11, 16), (16, 15), (13, 20), (19, 19), (9, 21), (16, 23), (21, 14)]:
        K.shaded_ellipse(img, x, y, 3.0, 3.0, (186, 30, 60), (236, 90, 120), (110, 10, 40), outline=(70, 6, 24))
        K.put(img, x - 2, y - 2, (255, 210, 225))
    for x in range(14, 20):                                   # leaves at the stalk
        K.put(img, x, 8 + (x - 14) // 2, (70, 140, 50))
        K.put(img, x, 9 + (x - 14) // 2, (40, 90, 30))
    return img


@sprite("Cave_Mushroom")
def cave_mushroom():
    img = K.new()
    stem, cap = (220, 210, 190), (90, 200, 214)
    K.rect(img, 14, 14, 18, 27, stem)
    K.rect(img, 17, 14, 18, 27, K.add(stem, -46))
    K.rect(img, 14, 14, 14, 27, K.add(stem, 18))
    K.rect(img, 13, 26, 19, 28, K.add(stem, -20))
    for y in range(6, 15):                                    # domed cap
        t = (y - 5) / 9.0
        half = int(round(11 * math.sqrt(max(0, 1 - (1 - t) ** 2))))
        for x in range(16 - half, 17 + half):
            k = (x - 16) / 11.0
            c = K.mul(cap, 1.2) if k < -0.35 and y < 12 else cap if k < 0.35 else K.mul(cap, 0.68)
            img[y][x] = c
    for x in range(6, 27):
        if img[14][x]:
            img[14][x] = K.mul(cap, 0.45)
    for x, y in [(11, 9), (19, 8), (15, 11), (22, 11)]:
        K.put(img, x, y, (230, 255, 252))
        K.put(img, x + 1, y, (190, 240, 240))
    return K.outline_img(img, (24, 60, 66))


@sprite("Wheat")
def wheat_bundle():
    img = K.new()
    gold, gl, gd = (214, 178, 84), (246, 214, 120), (150, 112, 44)
    for lean in (-5, -3, -1, 1, 3, 5, -2, 2, 0):          # stalks gathered at the twine, fanning out at both ends
        top = (16 + lean * 1.4, 8 + abs(lean) * 0.6)
        bot = (16 + lean * 0.6, 29)
        seg(img, top[0], top[1] + 4, 16 + lean * 0.15, 19, 1.3, gl, gold, gd)
        seg(img, 16 + lean * 0.15, 19, bot[0], bot[1], 1.3, gold, (180, 150, 70), gd)
        tx, ty = int(round(top[0])), int(round(top[1]))
        for k in range(6):                                # the ear
            K.put(img, tx - 1, ty + k, gl if k % 2 == 0 else gold)
            K.put(img, tx + 1, ty + k, gd if k % 2 == 0 else gold)
            K.put(img, tx, ty + k, gold)
        K.put(img, tx, ty - 1, gl)
    K.rect(img, 13, 18, 19, 20, (150, 60, 40))            # twine
    K.rect(img, 13, 18, 19, 18, (190, 90, 60))
    return K.outline_img(img, (90, 66, 20))


@sprite("Flour")
def flour():
    rows = [
        "      t  t      ",
        "     tTttTt     ",
        "      TttT      ",
        "     wwwwww     ",
        "    wwwwwwwWW   ",
        "   wwwwwwwwwWW  ",
        "  wwwwwwwwwwwWW ",
        "  wwwwFFFwwwwWW ",
        " wwwwwFwwwwwwwWW",
        " wwwwwFFwwwwwwWW",
        " wwwwwFwwwwwwwWW",
        " wwwwwFwwwwwwwWW",
        " wwwwwwwwwwwwwWW",
        " wwwwwwwwwwwwwWW",
        "  wwwwwwwwwwwWW ",
        "  wwwwwwwwwwwWW ",
        "   WWWWWWWWWWW  ",
    ]
    img = art(rows, {"w": (232, 222, 196), "W": (186, 172, 140), "t": (150, 110, 60), "T": (110, 76, 40),
                     "F": (150, 120, 80)}, oy=8)
    for x in range(10, 23):                                   # flour dusting on top
        if img[11][x]:
            img[11][x] = (250, 248, 240)
    return K.outline_img(img, (110, 96, 70))


def pie(filling, filling_dark, lattice=True):
    img = K.new()
    crust, cl, cd = (214, 160, 80), (242, 196, 120), (150, 100, 44)
    for y in range(20, 26):                                   # dish side
        for x in range(4, 29):
            if ((x - 16) / 12.5) ** 2 <= 1:
                img[y][x] = (150, 150, 160) if y > 22 else (190, 190, 200)
    K.shaded_ellipse(img, 16, 18, 12.5, 7.5, crust, cl, cd)
    K.shaded_ellipse(img, 16, 18, 10, 5.5, filling, K.add(filling, 40), filling_dark)
    if lattice:
        for i in range(-3, 4):
            for t in range(-12, 13):
                x, y = 16 + t, 18 + i * 2.2 + t * 0.25
                if ((x - 16) / 10.0) ** 2 + ((y - 18) / 5.5) ** 2 <= 1 and i % 2 == 0:
                    K.put(img, int(x), int(y), cl)
            for t in range(-6, 7):
                x, y = 16 + i * 3 + t * 0.4, 18 + t
                if ((x - 16) / 10.0) ** 2 + ((y - 18) / 5.5) ** 2 <= 1 and i % 2 == 0:
                    K.put(img, int(x), int(y), crust)
    else:
        K.shaded_ellipse(img, 16, 18, 10, 5.5, crust, cl, cd)
        for x, y in [(12, 17), (16, 16), (20, 17), (14, 20), (18, 20)]:
            K.put(img, x, y, cd)                              # vents
            K.put(img, x + 1, y, filling_dark)
    for a in range(0, 360, 20):                               # crimped rim
        x, y = 16 + 11.8 * math.cos(math.radians(a)), 18 + 7.0 * math.sin(math.radians(a))
        K.put(img, int(x), int(y), cl if math.sin(math.radians(a)) < 0 else cd)
    return K.outline_img(img, (80, 54, 24))


@sprite("Berry_Pie")
def berry_pie():
    return pie((150, 30, 70), (90, 10, 40))


@sprite("Fish_Pie")
def fish_pie():
    return pie((220, 200, 160), (150, 120, 90), lattice=False)


@sprite("Wool")
def wool():
    img = K.new()
    rng = random.Random(5)
    for x, y, r in [(10, 18, 5), (16, 15, 6), (22, 18, 5), (13, 22, 5), (19, 22, 5), (16, 19, 5), (8, 22, 3.5),
                    (24, 22, 3.5)]:
        K.shaded_ellipse(img, x, y, r, r * 0.9, (230, 228, 220), (255, 255, 250), (180, 176, 166), rng=rng, noise=0.25)
    for _ in range(30):
        x, y = rng.randrange(6, 27), rng.randrange(10, 27)
        if img[y][x]:
            img[y][x] = K.add(img[y][x], -24)
    return K.outline_img(img, (120, 116, 106))


@sprite("Ball_of_Wool")
def ball_of_wool():
    img = K.new()
    K.shaded_ellipse(img, 16, 18, 9, 9, (226, 222, 210), (255, 255, 250), (170, 164, 150))
    for k in range(-3, 4):                                    # strands wound round it
        for t in range(-9, 10):
            x, y = 16 + t, 18 + k * 2.5 + t * 0.45
            if (x - 16) ** 2 + (y - 18) ** 2 < 70:
                K.put(img, int(x), int(y), (160, 154, 140))
    for t in range(0, 10):                                    # loose end
        K.put(img, 24 + t // 2, 24 + t, (210, 204, 190))
    K.put(img, 12, 13, (255, 255, 255))
    return K.outline_img(img, (110, 104, 94))


@sprite("Cowhide")
def cowhide():
    rows = [
        "   bb          bb   ",
        "  bbbb  bbbbb bbbb  ",
        "   bwwwwwwbbbwwwbb  ",
        "    wwwwBBBwwwwwbb  ",
        "   wwwwBBBBBwwwwww  ",
        "  wwwwwwBBBwwwwwwww ",
        "  wwwwwwwwwwwBBwwww ",
        " bbwwwwwwwwwBBBBwwww",
        " bbwwwBBwwwwwBBwwwww",
        "  wwwBBBBwwwwwwwwww ",
        "  wwwwBBwwwwwwwwwBb ",
        "   wwwwwwwwwBBwwwbb ",
        "  bbwwwwwwwBBBBwww  ",
        "  bbbwwwwwwwBBwwwb  ",
        "   bb  wwwwwww bbb  ",
        "        bbbb    b   ",
    ]
    return K.outline_img(art(rows, {"w": (226, 214, 196), "B": (60, 40, 30), "b": (120, 80, 50)}, oy=8), (70, 50, 34))


@sprite("Leather")
def leather():
    rows = [
        "    LLLLLLLLLLLLLL  ",
        "   LllllllllllllLDD ",
        "  LlllllllllllllLDD ",
        "  LlllllllllllllLDD ",
        "  LlllllllllllllLDD ",
        " LLLLLLLLLLLLLLLLDD ",
        " LllllllllllllllLDDD",
        " LllllllllllllllLDDD",
        " LlllllllllllllllDDD",
        " LllllllllllllllLDD ",
        " LLLLLLLLLLLLLLLLD  ",
        "  DDDDDDDDDDDDDDD   ",
    ]
    img = art(rows, {"L": (150, 100, 56), "l": (190, 136, 80), "D": (100, 64, 32)}, oy=11)
    for x in range(7, 24, 3):                                 # stitching
        K.put(img, x, 12, (232, 210, 170))
        K.put(img, x, 21, (232, 210, 170))
    return K.outline_img(img, (70, 44, 20))


@sprite("Leather_Boots")
def leather_boots():
    boot = [
        " LLLL  ",
        " LllL  ",
        " LllL  ",
        " LllL  ",
        " LllL  ",
        " LllLL ",
        " LlllLL",
        " LllllL",
        "DDDDDDD",
    ]
    pal = {"L": (120, 76, 40), "l": (170, 116, 66), "D": (60, 38, 18)}
    img = K.new()
    K.paste(img, art(boot, pal, ox=8, oy=12))
    K.paste(img, art(boot, pal, ox=15, oy=14))
    for y in (13, 15):
        K.put(img, 10, y, (220, 190, 140))
    for y in (15, 17):
        K.put(img, 17, y, (220, 190, 140))
    return K.outline_img(img, (50, 30, 14))


@sprite("Spider_Silk")
def spider_silk():
    img = K.new()
    rng = random.Random(9)
    for k in range(9):
        a0 = rng.uniform(0, math.pi)
        for t in range(140):
            a = a0 + t / 140.0 * 2 * math.pi
            r = 7 + 2.5 * math.sin(a * 3 + k)
            x, y = 16 + r * math.cos(a), 17 + r * 0.75 * math.sin(a)
            K.put(img, int(x), int(y), rng.choice([(236, 236, 240), (210, 210, 220), (255, 255, 255)]))
    for t in range(9):
        K.put(img, 23 + t // 3, 22 + t, (230, 230, 236))
    return K.outline_img(img, (120, 120, 132))


@sprite("Shears")
def shears():
    img = K.new()
    seg(img, 8, 6, 19, 19, 3, (230, 232, 240), (180, 184, 196), (110, 114, 126))
    seg(img, 24, 6, 13, 19, 3, (230, 232, 240), (180, 184, 196), (110, 114, 126))
    for cx in (11, 21):                                       # handles (rings)
        for a in range(0, 360, 10):
            x, y = cx + 4 * math.cos(math.radians(a)), 24 + 3.4 * math.sin(math.radians(a))
            K.put(img, int(round(x)), int(round(y)), (150, 60, 40) if math.sin(math.radians(a)) > -0.3 else (200, 90, 60))
            K.put(img, int(round(x * 0.9 + cx * 0.1)), int(round(y * 0.9 + 2.4)), (120, 44, 30))
    seg(img, 16, 18, 13, 22, 2, (200, 90, 60), (150, 60, 40), (110, 40, 26))
    seg(img, 16, 18, 19, 22, 2, (200, 90, 60), (150, 60, 40), (110, 40, 26))
    K.put(img, 16, 17, (60, 60, 70))
    return K.outline_img(img, (40, 40, 48))


def sword(blade_l, blade_m, blade_d, guard, grip):
    img = K.new()
    seg(img, 26, 4, 12, 18, 4, blade_l, blade_m, blade_d)
    K.put(img, 27, 3, blade_l)
    seg(img, 25, 5, 13, 17, 1, K.add(blade_l, 10), K.add(blade_l, 10), K.add(blade_l, 10))   # fuller shine
    seg(img, 8, 15, 15, 22, 2.6, *guard)
    seg(img, 11, 19, 6, 24, 2.4, *grip)
    K.shaded_ellipse(img, 5, 25.5, 2.2, 2.2, *guard)
    return K.outline_img(img, (30, 30, 36))


@sprite("Iron_Sword")
def iron_sword():
    return sword((214, 214, 220), (160, 160, 168), (100, 100, 108),
                 ((150, 150, 156), (110, 110, 116), (70, 70, 76)), ((130, 84, 44), (96, 60, 30), (64, 40, 18)))


@sprite("Steel_Sword")
def steel_sword():
    return sword((240, 248, 255), (176, 196, 220), (104, 122, 150),
                 ((250, 214, 90), (214, 166, 40), (150, 104, 20)), ((60, 60, 120), (40, 40, 90), (24, 24, 60)))


@sprite("Iron_Shield")
def iron_shield():
    img = K.new()
    K.shaded_ellipse(img, 16, 16, 12, 12, (140, 140, 148), (196, 196, 204), (80, 80, 88))
    K.shaded_ellipse(img, 16, 16, 9.5, 9.5, (150, 46, 40), (196, 76, 64), (100, 26, 22))
    for y in range(7, 26):                                    # a pale cross
        for x in range(14, 19):
            if img[y][x] and (x - 16) ** 2 + (y - 16) ** 2 < 90:
                img[y][x] = (230, 210, 150) if x < 17 else (190, 170, 110)
    for x in range(7, 26):
        for y in range(14, 19):
            if img[y][x] and (x - 16) ** 2 + (y - 16) ** 2 < 90:
                img[y][x] = (230, 210, 150) if y < 17 else (190, 170, 110)
    K.shaded_ellipse(img, 16, 16, 3, 3, (170, 170, 178), (230, 230, 236), (90, 90, 98))
    for a in range(0, 360, 45):                               # rivets
        K.put(img, int(16 + 10.8 * math.cos(math.radians(a))), int(16 + 10.8 * math.sin(math.radians(a))), (236, 236, 240))
    return K.outline_img(img, (40, 40, 46))


def ring(gem=None):
    img = K.new()
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - 16) / 9.0, (y + 0.5 - 19) / 6.5
            d = dx * dx + dy * dy
            if 0.45 <= d <= 1.0:
                k = -(dx + dy)
                img[y][x] = (255, 240, 150) if k > 0.6 else (230, 186, 60) if k > -0.4 else (160, 110, 20)
    K.put(img, 10, 14, (255, 255, 230))
    K.put(img, 11, 14, (255, 255, 230))
    if gem:
        K.shaded_ellipse(img, 16, 12.5, 3.6, 3.6, gem[0], gem[1], gem[2], outline=(150, 110, 20))
        K.put(img, 15, 11, (255, 255, 255))
    return K.outline_img(img, (90, 60, 10))


@sprite("Gold_Ring")
def gold_ring():
    return ring()


@sprite("Sapphire_Ring")
def sapphire_ring():
    return ring(((50, 80, 210), (130, 170, 255), (20, 30, 120)))


@sprite("Emerald_Ring")
def emerald_ring():
    return ring(((30, 170, 80), (120, 240, 150), (10, 90, 40)))


@sprite("Ruby_Ring")
def ruby_ring():
    return ring(((200, 30, 50), (255, 120, 130), (110, 10, 24)))


# ================================================================== armour and weapons (equipment)
# Materials: h highlight, l light, m mid, d dark, k shadow/inside, t trim light, T trim dark, s stitching.
IRON = {"h": (236, 236, 242), "l": (190, 190, 198), "m": (148, 148, 156), "d": (98, 98, 106), "k": (46, 46, 52),
        "t": (122, 122, 130), "T": (80, 80, 88), "s": (210, 210, 216), "o": (30, 30, 36)}
STEEL = {"h": (250, 252, 255), "l": (206, 220, 236), "m": (160, 180, 204), "d": (100, 118, 146), "k": (40, 50, 70),
         "t": (250, 214, 90), "T": (190, 140, 30), "s": (255, 240, 160), "o": (26, 30, 44)}
LEATHER = {"h": (222, 168, 106), "l": (190, 136, 80), "m": (154, 102, 56), "d": (108, 68, 34), "k": (64, 40, 18),
           "t": (120, 76, 40), "T": (84, 52, 24), "s": (236, 214, 172), "o": (50, 30, 14)}


def mat_art(rows, mat, ox=None, oy=0):
    pal = {k: v for k, v in mat.items() if k != "o"}
    return K.outline_img(art(rows, pal, ox=ox, oy=oy), mat["o"])


HELM = [
    "       llmmmd       ",
    "     hllmmmmmdd     ",
    "    hllmmmmmmmdd    ",
    "   hllmmmmmmmmmdd   ",
    "   hlmmmmmmmmmmmd   ",
    "  hllmmmmmmmmmmmdd  ",
    "  hlmmmmmmmmmmmmmd  ",
    "  tttttttttttttttT  ",
    "  lmmmmmmhmmmmmmmd  ",
    "  lmmkkkkhmkkkkmmd  ",
    "  lmmkkkkhmkkkkmmd  ",
    "  lmmmmmmhmmmmmmmd  ",
    "  lmmm   hm   mmmd  ",
    "  lmm    hm    mmd  ",
    "  lmm    lm    mmd  ",
    "   lm          md   ",
]


@sprite("Iron_Helm")
def iron_helm():
    img = mat_art(HELM, IRON, oy=8)
    for x in (5, 26):                                         # rivets on the band
        K.put(img, x + (1 if x < 16 else -1), 15, IRON["h"])
    return img


@sprite("Steel_Helm")
def steel_helm():
    img = mat_art(HELM, STEEL, oy=8)
    for y in range(3, 8):                                     # a gilded crest
        K.put(img, 15, y + 2, STEEL["t"])
        K.put(img, 16, y + 2, STEEL["T"])
    K.put(img, 15, 4, STEEL["s"])
    return img


@sprite("Leather_Cap")
def leather_cap():
    rows = [
        "       llmmmd       ",
        "     hllmmmmmdd     ",
        "    hlllmmmmmmdd    ",
        "   hllmmmsmmmmmdd   ",
        "   hlmmmmsmmmmmmd   ",
        "  hllmmmmsmmmmmmdd  ",
        "  hlmmmmmsmmmmmmmd  ",
        "  lmmmmmmsmmmmmmmd  ",
        " ttttttttttttttttTT ",
        " TTTTTTTTTTTTTTTTTT ",
        "  kkk          kkk  ",
    ]
    return mat_art(rows, LEATHER, oy=11)


PLATEBODY = [
    "   hhll          mmdd   ",
    "  hllllm        mmmddd  ",
    " hlllllmmkkkkkkmmmmdddd ",
    " hlllmmmmmkkkkmmmmmmddd ",
    " hllmmmmmmmhhmmmmmmmmdd ",
    " llll lmmmmmhhmmmmmmd dd",
    "  ll  lmmmmmhhmmmmmmd d ",
    "      lmmmmmhhmmmmmmd   ",
    "      tTTTTTTTTTTTTTT   ",
    "      lmmmmmhhmmmmmmd   ",
    "      lmmmmmhhmmmmmmd   ",
    "      tTTTTTTTTTTTTTT   ",
    "      lmmmmmhhmmmmmmd   ",
    "       lmmmmhhmmmmmd    ",
    "       ttttttttttttT    ",
    "       lmmmmmmmmmmmd    ",
    "        lmmmmmmmmmd     ",
]


@sprite("Iron_Platebody")
def iron_platebody():
    return mat_art(PLATEBODY, IRON, oy=8)


@sprite("Steel_Platebody")
def steel_platebody():
    img = mat_art(PLATEBODY, STEEL, oy=8)
    for x, y in [(4, 9), (5, 10), (26, 9), (25, 10)]:        # gilded shoulder edges
        K.put(img, x, y, STEEL["t"])
    return img


@sprite("Leather_Body")
def leather_body():
    rows = [
        "   hhll          mmdd   ",
        "  hllllm        mmmddd  ",
        " hlllllmmkkkkkkmmmmdddd ",
        " hlllmmmmmkkkkmmmmmmddd ",
        " hllmmmmmmmsmmmmmmmmmdd ",
        " llll lmmmmmsmmmmmmmd dd",
        "  ll  lmmmmmsmmmmmmmd d ",
        "      lmmmmmsmmmmmmmd   ",
        "      lmmmmmsmmmmmmmd   ",
        "      lmmmmmsmmmmmmmd   ",
        "      lmmmmmsmmmmmmmd   ",
        "      lmmmmmsmmmmmmmd   ",
        "      ttttttttttttttT   ",
        "      TTTTTTsTTTTTTTT   ",
        "      lmmmmmmmmmmmmmd   ",
        "       lmmmmmmmmmmmd    ",
    ]
    img = mat_art(rows, LEATHER, oy=8)
    for y in (13, 15, 17, 19):                                 # laces across the front seam
        K.put(img, 13, y, LEATHER["s"])
    return img


PLATELEGS = [
    "   tttttttttttttttT   ",
    "   TTTTTTTTTTTTTTTT   ",
    "   hlmmmmmmmmmmmmmd   ",
    "   hlmmmmmkkmmmmmmd   ",
    "   hlmmmmdkkhlmmmmd   ",
    "   hlmmmmd  hlmmmmd   ",
    "  hlmmmmd    hlmmmmd  ",
    "  hlmmmmd    hlmmmmd  ",
    "  thhhhhT    thhhhhT  ",
    "  hlmmmmd    hlmmmmd  ",
    "  hlmmmmd    hlmmmmd  ",
    " hlmmmmd      hlmmmmd ",
    " hlmmmmd      hlmmmmd ",
    " lmmmmdd      lmmmmdd ",
]


@sprite("Iron_Platelegs")
def iron_platelegs():
    return mat_art(PLATELEGS, IRON, oy=9)


@sprite("Steel_Platelegs")
def steel_platelegs():
    return mat_art(PLATELEGS, STEEL, oy=9)


@sprite("Leather_Legs")
def leather_legs():
    rows = [
        "   tttttttttttttttT   ",
        "   TTTTTTTTsTTTTTTT   ",
        "   hlmmmmmmsmmmmmmd   ",
        "   hlmmmmmkkmmmmmmd   ",
        "   hlmmmsdkkhlsmmmd   ",
        "   hlmmmsd  hlsmmmd   ",
        "  hlmmmsd    hlsmmmd  ",
        "  hlmmmsd    hlsmmmd  ",
        "  hlmmmsd    hlsmmmd  ",
        "  hlmmmsd    hlsmmmd  ",
        "  hlmmmsd    hlsmmmd  ",
        " hlmmmsd      hlsmmmd ",
        " hlmmmsd      hlsmmmd ",
        " lmmmmdd      lmmmmdd ",
    ]
    return mat_art(rows, LEATHER, oy=9)


@sprite("Leather_Gloves")
def leather_gloves():
    glove = [
        " l m d  ",
        " lm m d ",
        "llmmmmd ",
        "lmmmmmd ",
        "lmmmmmdd",
        "lmmmmmdd",
        " lmmmmd ",
        " tttttT ",
        " TTTTTT ",
    ]
    pal = {k: v for k, v in LEATHER.items() if k != "o"}
    img = K.new()
    K.paste(img, art(glove, pal, ox=6, oy=11))
    K.paste(img, K.flip_h(art(glove, pal, ox=6, oy=13)))
    for x, y in [(9, 18), (22, 20)]:
        K.put(img, x, y, LEATHER["s"])
    return K.outline_img(img, LEATHER["o"])


@sprite("Steel_Shield")
def steel_shield():
    """A kite shield: steel rim, a blue field and a gold chevron."""
    img = K.new()
    rim_l, rim_m, rim_d = STEEL["l"], STEEL["m"], STEEL["d"]
    field, field_l, field_d = (44, 70, 160), (80, 110, 200), (24, 40, 100)

    def inside(x, y, shrink):
        top, bot = 4 + shrink, 29 - shrink * 1.6
        if y < top or y > bot:
            return False
        half = 11 - shrink if y < 13 else (11 - shrink) * max(0.0, (bot - y)) / max(1.0, (bot - 13))
        return abs(x + 0.5 - 16) <= half
    for y in range(S):
        for x in range(S):
            if inside(x, y, 0):
                k = (16 - (x + 0.5)) / 11.0 - (y - 12) / 30.0
                img[y][x] = rim_l if k > 0.35 else rim_d if k < -0.4 else rim_m
            if inside(x, y, 2):
                k = (16 - (x + 0.5)) / 9.0
                img[y][x] = field_l if k > 0.45 else field_d if k < -0.45 else field
    for x in range(S):                                        # gold chevron
        for y in range(S):
            if img[y][x] in (field, field_l, field_d):
                d = y - (9 + abs(x + 0.5 - 16) * 0.75)
                if 0 <= d < 3:
                    img[y][x] = STEEL["t"] if x < 16 else STEEL["T"]
    K.shaded_ellipse(img, 16, 18, 2, 2, STEEL["m"], STEEL["h"], STEEL["d"])
    for x, y in [(7, 6), (24, 6), (16, 26)]:
        K.put(img, x, y, STEEL["h"])
    return K.outline_img(img, STEEL["o"])


@sprite("Copper_Dagger")
def copper_dagger():
    img = K.new()
    seg(img, 23, 7, 14, 16, 3.2, (255, 214, 170), (222, 144, 90), (150, 76, 36))
    K.put(img, 24, 6, (255, 214, 170))
    seg(img, 11, 13, 17, 19, 2.4, (150, 104, 60), (110, 76, 40), (70, 46, 20))
    seg(img, 13, 17, 8, 22, 2.4, (130, 84, 44), (96, 60, 30), (64, 40, 18))
    K.shaded_ellipse(img, 7, 23.5, 1.8, 1.8, (222, 144, 90), (255, 214, 170), (150, 76, 36))
    return K.outline_img(img, (40, 24, 14))


@sprite("Chest")
def chest():
    rows = [
        "   wwwwwwwwwwwwwwwwww   ",
        "  wWwwwwwwwwwwwwwwwwwD  ",
        "  wwwwwwwwwwwwwwwwwwwD  ",
        "  iiiiiiiiiiiiiiiiiiiI  ",
        "  wwwwwwwwggggwwwwwwwD  ",
        "  bbbbbbbbgkkgbbbbbbbD  ",
        "  wwwwwwwwggggwwwwwwwD  ",
        "  wwwwwwwwwwwwwwwwwwwD  ",
        "  iiiiiiiiiiiiiiiiiiiI  ",
        "  wwwwwwwwwwwwwwwwwwwD  ",
        "  wwwwwwwwwwwwwwwwwwwD  ",
        "  wwwwwwwwwwwwwwwwwwwD  ",
        "  iiiiiiiiiiiiiiiiiiiI  ",
        "  DDDDDDDDDDDDDDDDDDDD  ",
    ]
    img = art(rows, {"w": (150, 96, 50), "W": (196, 140, 80), "D": (96, 58, 26), "b": (70, 42, 18),
                     "i": (130, 130, 140), "I": (80, 80, 90), "g": (240, 200, 70), "k": (40, 30, 10)}, oy=15)
    for x in range(4, 23, 4):                                 # planks
        for y in (19, 20, 21, 22, 24, 25, 26):
            if img[y][x] == (150, 96, 50):
                img[y][x] = (124, 78, 38)
    return K.outline_img(img, (40, 24, 10))


# ================================================================== crafting stations (StaticObjects)
@sprite("Furnace")
def furnace():
    rows = [
        "      ssssssssssss      ",
        "     sSssssssssssSs     ",
        "    ssssbbbbbbbssssS    ",
        "    sssbb      bbssS    ",
        "   sssbb        bbssS   ",
        "   ssbb          bbsS   ",
        "   ssb   ffffff   bsS   ",
        "   ssb  fFFFFFFf  bsS   ",
        "   ssb fFFWWWWFFf bsS   ",
        "   ssbbfFWWWWWWFfbbsS   ",
        "   ssssssssssssssssssS  ",
        "   sSsssSsssSsssSsssS   ",
        "   ssssssssssssssssssS  ",
        "   sssSsssSsssSsssSsS   ",
        "   ssssssssssssssssssS  ",
        "   SSSSSSSSSSSSSSSSSSS  ",
    ]
    img = art(rows, {"s": (120, 112, 104), "S": (76, 70, 64), "b": (40, 30, 26), "f": (220, 90, 30),
                     "F": (250, 160, 40), "W": (255, 240, 170)}, oy=13)
    for y in range(4, 13):                                     # chimney with a little smoke
        for x in range(13, 19):
            img[y][x] = (110, 102, 96) if x < 17 else (76, 70, 64)
    for x, y in [(15, 1), (16, 2), (14, 0), (17, 3)]:
        K.put(img, x, y, (170, 170, 176))
    return K.outline_img(img, (40, 36, 32))


@sprite("Anvil")
def anvil():
    rows = [
        " AAAAAAAAAAAAAAAAAAAA   ",
        "AaaaaaaaaaaaaaaaaaaaAAA ",
        " aaaaaaaaaaaaaaaaaaaaAAA",
        "   DDDaaaaaaaaaaaDDD    ",
        "       aaaaaaaaa        ",
        "       DaaaaaaaD        ",
        "      DDaaaaaaaDD       ",
        "    DDDDDDDDDDDDDDD     ",
        "    wwwwwwwwwwwwwwwW    ",
        "   wWwwwwwwwwwwwwwwwW   ",
        "   wwwwwwwwwwwwwwwwwW   ",
        "   wwwwwwwwwwwwwwwwwW   ",
        "   wwwwwwwwwwwwwwwwwW   ",
        "    WWWWWWWWWWWWWWWW    ",
    ]
    img = art(rows, {"A": (190, 194, 204), "a": (96, 98, 108), "D": (54, 56, 64), "w": (130, 88, 48),
                     "W": (86, 56, 28)}, oy=14)
    for x in range(6, 26, 4):                                  # tree rings on the stump
        K.put(img, x, 24, (106, 70, 36))
    return K.outline_img(img, (30, 30, 34))


@sprite("Range")
def cooking_range():
    rows = [
        "      PPPPPPP           ",
        "     PppppppPP          ",
        "     PppppppPP          ",
        "    rrrrrrrrrrrrrrrrrr  ",
        "   rRrrrrrrrrrrrrrrrrrR ",
        "   rrrrrrrrrrrrrrrrrrrR ",
        "   rkkkkkkkkkkkkkkkkkrR ",
        "   rkbbbbbbbbbbbbbbbkrR ",
        "   rkb  ffff  ffff bkrR ",
        "   rkb ffFFffffFFffbkrR ",
        "   rkbfFFWWFFFFWWFFbkrR ",
        "   rkkkkkkkkkkkkkkkkkrR ",
        "   rrrrrrrrrrrrrrrrrrrR ",
        "   rrRrrrrRrrrrRrrrrRrR ",
        "   rrrrrrrrrrrrrrrrrrrR ",
        "   RRRRRRRRRRRRRRRRRRRR ",
    ]
    img = art(rows, {"P": (60, 60, 66), "p": (110, 110, 118), "r": (170, 92, 64), "R": (110, 56, 38),
                     "k": (60, 52, 48), "b": (30, 22, 20), "f": (220, 90, 30), "F": (250, 160, 40),
                     "W": (255, 240, 170)}, oy=13)
    for x, y in [(9, 10), (10, 9), (8, 8)]:                    # steam from the pot
        K.put(img, x, y, (220, 220, 226))
    return K.outline_img(img, (50, 30, 22))


@sprite("Alchemy_Table")
def alchemy_table():
    img = K.new()
    rows = [
        "WWWWWWWWWWWWWWWWWWWWWWWW",
        "wwwwwwwwwwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDDDDDDDDDD",
        " DD                  DD ",
        " DD                  DD ",
        " DD                  DD ",
        " DD                  DD ",
        " DD                  DD ",
        " DD                  DD ",
        " DD                  DD ",
    ]
    K.paste(img, art(rows, {"W": (176, 126, 76), "w": (140, 96, 54), "D": (90, 58, 30)}, oy=20))
    for cx, liquid in ((7, ((70, 120, 22), (118, 178, 36), (166, 218, 66))),          # (three little flasks, in
                       (14, ((30, 70, 150), (52, 110, 200), (110, 160, 230))),         # the potions' own colours)
                       (21, ((120, 18, 18), (186, 34, 30), (226, 90, 80)))):
        K.shaded_ellipse(img, cx, 16.5, 3.6, 3.6, liquid[1], liquid[2], liquid[0], outline=(176, 192, 202))
        for y in range(9, 13):
            K.put(img, cx - 1, y, (176, 192, 202))
            K.put(img, cx, y, (206, 220, 228))
        K.put(img, cx - 1, 8, (148, 134, 118))
        K.put(img, cx, 8, (148, 134, 118))
        K.put(img, cx - 2, 15, (244, 248, 252))
    K.shaded_ellipse(img, 25, 18.5, 3, 2, (180, 180, 186), (220, 220, 226), (120, 120, 126))
    K.put(img, 26, 15, (150, 110, 70))
    K.put(img, 27, 14, (150, 110, 70))
    return K.outline_img(img, (50, 34, 20))


@sprite("Workbench")
def workbench():
    img = K.new()
    rows = [
        "WWWWWWWWWWWWWWWWWWWWWWWWWW",
        "wwwwwwwwwwwwwwwwwwwwwwwwww",
        "wwwwwwwwwwwwwwwwwwwwwwwwww",
        "DDDDDDDDDDDDDDDDDDDDDDDDDD",
        " DD    DDDDDDDDDDDD    DD ",
        " DD                    DD ",
        " DD                    DD ",
        " DD                    DD ",
        " DD                    DD ",
    ]
    K.paste(img, art(rows, {"W": (190, 140, 84), "w": (156, 108, 62), "D": (96, 62, 32)}, oy=20))
    for x in range(4, 28, 6):
        K.put(img, x, 21, (130, 88, 48))
    K.paste(img, K.shift(leather(), -7, -4))                    # leather and a ball of wool on top
    seg(img, 20, 19, 27, 15, 1.6, (200, 200, 210), (160, 160, 170), (100, 100, 110))  # a knife
    seg(img, 18, 20, 21, 18, 2, (150, 100, 60), (120, 80, 44), (80, 50, 24))
    return K.outline_img(img, (50, 34, 18))


@sprite("Mine_Cart")
def mine_cart():
    rows = [
        "  ooOoooOOoooOooo      ",
        " oOooOooooOoooOOoo     ",
        "  MMMMMMMMMMMMMMMMMMM  ",
        "  MmmmmmmmmmmmmmmmmmMD ",
        "  MmmmmmmmmmmmmmmmmmMD ",
        "  MmmRmmmmmmmmmmRmmmMD ",
        "   MmmmmmmmmmmmmmmmMD  ",
        "   MmmmmmmmmmmmmmmmMD  ",
        "   MMMMMMMMMMMMMMMMMD  ",
        "    WWW         WWW    ",
        "   WwwwW       WwwwW   ",
        "    WWW         WWW    ",
    ]
    img = art(rows, {"o": (176, 100, 52), "O": (214, 140, 80), "M": (70, 72, 80), "m": (120, 100, 70),
                     "R": (160, 160, 170), "D": (40, 40, 46), "W": (40, 40, 46), "w": (110, 110, 120)}, oy=15)
    return K.outline_img(img, (24, 24, 28))


# ================================================================== people
# A 16-wide figure, placed at x=8, feet on row 30 (like the Miner/Farmer). Codes:
# H/h hair (light/shade), s/S skin, w eye white, e pupil, m mouth, n neck, t/T torso, a/A sleeves, x belt,
# p/P trousers, b/B boots, d/D dress, o/O apron, M/m metal, R/r tabard/trim, k/K hat, g held item, G held item shade
HUMAN = [
    "                ",
    "                ",
    "     HHHHHH     ",
    "    HHHHHHHH    ",
    "    HswsswsH    ",
    "    ssessess    ",
    "    sssmmsss    ",
    "     ssssss     ",
    "      ssss      ",
    "      nnnn      ",
    "    tttttttT    ",
    "   atttttttTA   ",
    "  aatttttttTAA  ",
    "  aatttttttTAA  ",
    "  aatttttttTAA  ",
    "  aatttttttTAA  ",
    "  aatttttttTAA  ",
    "  aaxxxxxxxxAA  ",
    "  sspppppppPSS  ",
    "  sspppppppPSS  ",
    "    pppppppP    ",
    "    pppppppP    ",
    "    ppp  ppP    ",
    "    ppp  ppP    ",
    "    ppp  ppP    ",
    "    ppp  ppP    ",
    "    ppP  ppP    ",
    "    bbb  bbb    ",
    "    bbb  bbb    ",
    "   bbbB  bbbB   ",
    "   bbbB  bbbB   ",
    "                ",
]

DRESS = {
    17: "  aadddddddDAA  ",
    18: "  ssdddddddDSS  ",
    19: "  ssdddddddDSS  ",
    20: "    dddddddD    ",
    21: "   ddddddddDD   ",
    22: "   ddddddddDD   ",
    23: "   ddddddddDD   ",
    24: "  dddddddddDDD  ",
    25: "  dddddddddDDD  ",
    26: "  dddddddddDDD  ",
    27: "  dddddddddDDD  ",
    28: "    bb    bb    ",
    29: "   bbb    bbb   ",
    30: "________________",
}

LONG_HAIR = {
    3: "   HHHHHHHHHH   ",
    4: "   HHswsswsHH   ",
    5: "   HssessessH   ",
    6: "   HsssmmsssH   ",
    7: "   HHssssssHH   ",
    8: "    HH ss HH    ",
    9: "    HH nn HH    ",
}


def person(pal, *overlays, held=None):
    rows = [list(r) for r in HUMAN]
    for ov in overlays:
        for y, r in ov.items():
            for x, ch in enumerate(r):
                if ch == "_":
                    rows[y][x] = " "
                elif ch != " ":
                    rows[y][x] = ch
    base = {"w": (255, 255, 255), "e": (0, 0, 0), "m": (162, 32, 6), "s": (244, 184, 160), "S": (206, 146, 124),
            "n": (206, 146, 124)}
    base.update(pal)
    img = art(["".join(r) for r in rows], base, ox=8)
    if held:
        held(img)
    return img


SKIN_DARK = {"s": (150, 100, 70), "S": (118, 76, 52), "n": (118, 76, 52)}


@sprite("Guard")
def guard():
    helmet = {
        1: "     MMMMMM     ",
        2: "    MMMMMMMm    ",
        3: "   MMMMMMMMMm   ",
        4: "   mswsMswsmm   ",
        5: "    ssesMess    ",
        6: "    sssmmsss    ",
    }
    tabard = {
        10: "    MMRRRRMm    ",
        11: "   MMMRRRRMmm   ",
        12: "  MMMMRYYRMmmm  ",
        13: "  MMMMRYYRMmmm  ",
        14: "  MMMMRRRRMmmm  ",
        15: "  MMMMRRRRMmmm  ",
        16: "  MMMMRRRRMmmm  ",
        17: "  MMxxRRRRxxmm  ",
    }

    def spear(img):
        for y in range(0, 31):
            K.put(img, 23, y, (120, 80, 40))
            K.put(img, 24, y, (84, 54, 26))
        for y, half in [(0, 0), (1, 1), (2, 1), (3, 1), (4, 0)]:
            for x in range(23 - half, 25 + half):
                K.put(img, x, y, (220, 220, 230) if x <= 23 else (150, 150, 160))
        K.rect(img, 21, 18, 22, 19, (244, 184, 160))           # hand on the spear
    return person({"M": (150, 150, 160), "m": (100, 100, 110), "R": (170, 30, 30), "Y": (240, 200, 60),
                   "x": (70, 40, 20), "p": (80, 80, 96), "P": (56, 56, 70), "b": (60, 40, 24), "B": (40, 26, 14),
                   "a": (150, 150, 160), "A": (100, 100, 110), "t": (150, 150, 160), "T": (100, 100, 110),
                   "H": (60, 40, 20)}, helmet, tabard, held=spear)


@sprite("Quartermaster")
def quartermaster():
    hat = {
        1: "     kkkkkk     ",
        2: "    kkkkkkkK    ",
        3: "   kkkkkkkkkK   ",
        6: "    smmmmmms    ",
    }
    coat = {
        10: "    RtttttRT    ",
        11: "   aRtttttRTA   ",
        12: "  aaRtYtttRTAA  ",
        17: "  aaxxxYxxxxAA  ",
    }

    def ledger(img):
        K.rect(img, 6, 15, 10, 21, (120, 40, 30))
        K.rect(img, 7, 16, 10, 20, (230, 220, 190))
        K.rect(img, 6, 15, 6, 21, (80, 24, 18))
    return person({"H": (90, 60, 30), "k": (40, 50, 90), "K": (26, 32, 60), "t": (50, 66, 120), "T": (34, 44, 84),
                   "a": (50, 66, 120), "A": (34, 44, 84), "R": (220, 190, 80), "Y": (240, 210, 90),
                   "x": (60, 36, 18), "p": (200, 190, 160), "P": (160, 150, 120), "b": (40, 30, 24),
                   "B": (24, 18, 14)}, hat, coat, held=ledger)


@sprite("Villager")
def villager():
    hair = {2: "     HHHHHH     ", 3: "    HHhHHhHH    "}
    return person({"H": (120, 80, 40), "h": (90, 58, 28), "t": (70, 130, 60), "T": (44, 92, 38),
                   "a": (70, 130, 60), "A": (44, 92, 38), "x": (90, 60, 30), "p": (110, 84, 56),
                   "P": (80, 60, 38), "b": (70, 46, 26), "B": (46, 30, 16)}, hair)


@sprite("Milkmaid")
def milkmaid():
    scarf = {
        1: "     kkkkkk     ",
        2: "    kkkkkkkk    ",
        3: "   kkkkkkkkkk   ",
        4: "   kHswsswsHk   ",
        5: "   kHsessesHk   ",
        6: "    HsssmssH    ",
        7: "    HHssssHH    ",
    }
    apron = {
        12: "  aatoooootTAA  ",
        13: "  aatoooootTAA  ",
        17: "  aaoooooooOAA  ",
        18: "  ssoooooooOSS  ",
        19: "  ssoooooooOSS  ",
        20: "    oooooooO    ",
        21: "   doooooooOD   ",
        22: "   doooooooOD   ",
        23: "   doooooooOD   ",
        24: "  ddoooooooODD  ",
        25: "  ddoooooooODD  ",
    }

    def pail(img):
        for y in range(19, 26):
            for x in range(2, 9):
                K.put(img, x, y, (160, 120, 70) if x < 6 else (120, 86, 46))
        for x in range(2, 9):
            K.put(img, x, 19, (240, 240, 236))
            K.put(img, x, 22, (90, 90, 96))
        for x, y in [(3, 17), (4, 16), (5, 16), (6, 16), (7, 17)]:
            K.put(img, x, y, (90, 90, 96))
    return person({"H": (200, 150, 70), "k": (200, 70, 70), "t": (90, 120, 200), "T": (60, 84, 150),
                   "a": (90, 120, 200), "A": (60, 84, 150), "d": (90, 120, 200), "D": (60, 84, 150),
                   "o": (244, 240, 230), "O": (200, 196, 186), "b": (70, 46, 26), "B": (46, 30, 16)},
                  DRESS, apron, scarf, held=pail)


@sprite("Fisherman")
def fisherman():
    hat = {
        1: "     kkkkkk     ",
        2: "    kkkkkkkK    ",
        3: "  kkkkkkkkkkKK  ",
        4: "    HswsswsH    ",
        6: "    shhhhhhs    ",
        7: "     hhhhhh     ",
        8: "      hhhh      ",
    }

    def rod(img):
        for i in range(0, 22):
            K.put(img, 22 + i // 3, 20 - i, (120, 80, 40) if i < 12 else (150, 110, 60))
        for y in range(0, 14):
            K.put(img, 29, y + 1, (220, 220, 230))
        K.put(img, 29, 15, (200, 40, 40))
        K.rect(img, 21, 18, 22, 19, (244, 184, 160))
    return person({"H": (170, 170, 170), "h": (200, 200, 200), "k": (230, 190, 40), "K": (180, 140, 20),
                   "t": (230, 190, 40), "T": (180, 140, 20), "a": (230, 190, 40), "A": (180, 140, 20),
                   "x": (180, 140, 20), "p": (60, 70, 110), "P": (40, 48, 80), "b": (40, 40, 44),
                   "B": (24, 24, 28)}, hat, held=rod)


@sprite("Dwarf")
def dwarf():
    rows = [
        "                ",
        "                ",
        "                ",
        "                ",
        "                ",
        "                ",
        "      MMMM      ",
        "    MMMMMMMm    ",
        "   MMMMMMMMMm   ",
        "   mMMMMMMMMmm  ",
        "    swsswss     ",
        "    sessess     ",
        "   rrrsSsrrr    ",
        "  rrrrrrrrrrr   ",
        "  rrrrRrrrrrr   ",
        " aarrrrRrrrrrAA ",
        " aarrrrrRrrrrAA ",
        " aatrrrrrrrrtAA ",
        " aattrrrrrrttAA ",
        " aatttrrrrtttAA ",
        " ssxxxxrrxxxxSS ",
        " ss tttrrtttTSS ",
        "   ppppppppP    ",
        "   pppp  ppP    ",
        "   pppp  ppP    ",
        "   pppp  ppP    ",
        "   bbbb  bbbb   ",
        "  bbbbB  bbbbB  ",
        "  bbbbB  bbbbB  ",
        "  bbbbB  bbbbB  ",
        "                ",
        "                ",
    ]
    img = art(rows, {"M": (140, 140, 150), "m": (96, 96, 106), "s": (236, 170, 140), "S": (200, 130, 104),
                     "w": (255, 255, 255), "e": (0, 0, 0), "r": (200, 110, 40), "R": (160, 80, 26),
                     "a": (120, 50, 40), "A": (86, 34, 26), "t": (120, 50, 40), "T": (86, 34, 26),
                     "x": (60, 40, 20), "p": (90, 70, 50), "P": (64, 48, 32), "b": (60, 40, 24),
                     "B": (40, 26, 14)}, ox=8)
    K.put(img, 11, 6, (220, 190, 80))                            # helmet horns
    K.put(img, 10, 5, (220, 190, 80))
    K.put(img, 20, 6, (220, 190, 80))
    K.put(img, 21, 5, (220, 190, 80))
    for y in range(4, 22):                                       # an axe over his shoulder
        K.put(img, 22 + (21 - y) // 6, y, (120, 80, 40))
    for y in range(3, 9):
        for x in range(23, 28 - abs(y - 6) // 2):
            K.put(img, x, y, (200, 200, 210) if y < 6 else (140, 140, 150))
    return img


@sprite("Dog")
def dog():
    rows = [
        "                        ",
        "  bb                    ",
        " bBBb                   ",
        " bBBBbbb                ",
        "bBwBBBBbn               ",
        "bBBBBBBBBk           bb ",
        " bBBBBBb            bBb ",
        "   bBBBBBBBBBBBBBBBBBb  ",
        "   bBBBBBBBBBBBBBBBBBb  ",
        "   bBBBBBBBBBBBBBBBBb   ",
        "    bBBBBBBBBBBBBBBb    ",
        "    bBb bBb  bBb bBb    ",
        "    bBb bBb  bBb bBb    ",
        "    bBb bBb  bBb bBb    ",
        "    ddd ddd  ddd ddd    ",
    ]
    img = art(rows, {"b": (110, 70, 34), "B": (160, 108, 60), "w": (20, 20, 20), "n": (30, 20, 20),
                     "k": (30, 20, 20), "d": (80, 50, 24)}, oy=15)
    K.rect(img, 6, 21, 8, 21, (200, 40, 40))                     # collar
    return img


# ================================================================== animals and monsters
@sprite("Cow")
def cow():
    rows = [
        "  hh  hh                      ",
        "  hwwwwh                      ",
        "  wwwwwwbbbbwwwwwwwwwwwwwww   ",
        "  wewwewbbbbbwwwwwwbbbwwwwwww ",
        "  wwwwwwwbbbwwwwwwbbbbbwwwwwwt",
        "  ppppppwwwwwwwwwwwbbbwwwwwwwt",
        "  pnppnpwwwwbbwwwwwwwwwwwwwww ",
        "   ppppwwwwbbbbwwwwwwwwwwbbww ",
        "       wwwwwbbwwwwwwwwwwbbbbw ",
        "        wwwwwwwwwpPPwwwwwbbw  ",
        "        ww  ww   pPP  ww  ww  ",
        "        ww  ww        ww  ww  ",
        "        ww  ww        ww  ww  ",
        "        kk  kk        kk  kk  ",
    ]
    img = art(rows, {"h": (220, 210, 190), "w": (240, 236, 228), "b": (40, 30, 26), "e": (10, 10, 10),
                     "p": (230, 160, 160), "n": (150, 70, 70), "P": (220, 140, 150), "t": (60, 50, 40),
                     "k": (60, 50, 40)}, oy=14)
    for y in range(14, 28):                                    # shading on the belly side
        for x in range(S):
            c = img[y][x]
            if c is not None and c[0] > 200 and y > 22:
                img[y][x] = K.mul(c, 0.86)
    return K.outline_img(img, (70, 64, 60))


@sprite("Sheep")
def sheep():
    img = K.new()
    rng = random.Random(3)
    for x, y, r in [(12, 18, 5), (17, 16, 6), (22, 18, 5), (14, 22, 5), (20, 22, 5), (25, 20, 3.5), (9, 21, 3.5)]:
        K.shaded_ellipse(img, x, y, r, r * 0.9, (236, 234, 226), (255, 255, 250), (190, 186, 176), rng=rng, noise=0.25)
    for x in (12, 15, 20, 23):                                   # legs
        K.rect(img, x, 26, x + 1, 30, (50, 44, 40))
    rows = [
        " kk  ",
        "kkkkk",
        "kwkkk",
        "kkkkk",
        " kkk ",
    ]
    K.paste(img, art(rows, {"k": (50, 44, 40), "w": (240, 240, 240)}, ox=0)[0:5], 3, 14)
    K.put(img, 4, 16, (10, 10, 10))
    return K.outline_img(img, (110, 106, 98))


@sprite("Rat")
def rat():
    rows = [
        "      gg               ",
        "     gpgg              ",
        "  ggggggggg            ",
        " gwgggggggggGG         ",
        "nggggggggggggGGt       ",
        " gggggggggggGGGG t     ",
        "   GG  GGGG GG    tt   ",
        "   kk  kk  kk      ttt ",
    ]
    img = art(rows, {"g": (130, 124, 120), "G": (96, 90, 86), "p": (230, 160, 170), "w": (20, 20, 20),
                     "n": (230, 150, 160), "t": (220, 160, 170), "k": (230, 160, 170)}, oy=22)
    return K.outline_img(img, (50, 46, 44))


@sprite("Bat")
def bat():
    rows = [
        "  k                       k  ",
        " kkk                     kkk ",
        " kkkk       e  e        kkkk ",
        "kkkkkk      eeee       kkkkkk",
        "kkKkkkk    ewreerw    kkkKkkk",
        "kKkKkkkkk  eeeeee  kkkkKkKkkk",
        "kK kKkkkkkkkeeeekkkkkkkKk Kkk",
        "k  kK kKkkkkkeeeekkkkKk Kk  k",
        "   k  kK  kKkkeekkkK  Kk  k  ",
        "      k   k    ee    k   k   ",
    ]
    img = art(rows, {"k": (60, 46, 70), "K": (100, 80, 110), "e": (80, 60, 70), "w": (255, 255, 255),
                     "r": (220, 30, 30)}, oy=10)
    return K.outline_img(img, (20, 14, 24))


@sprite("Giant_Spider")
def giant_spider():
    img = K.new()
    leg = (40, 34, 30)
    for side in (-1, 1):                                         # eight legs
        for i, (ang, ln) in enumerate([(-50, 12), (-15, 13), (20, 13), (55, 11)]):
            a = math.radians(ang)
            x0, y0 = 16 + side * 3, 18 + i * 1.2
            kx, ky = x0 + side * math.cos(a) * ln * 0.6, y0 - 5 + math.sin(a) * 4
            ex, ey = x0 + side * math.cos(a) * ln, y0 + 6 + math.sin(a) * 5
            seg(img, x0, y0, kx, ky, 1.6, (90, 80, 70), leg, (20, 16, 14))
            seg(img, kx, ky, ex, ey, 1.4, (90, 80, 70), leg, (20, 16, 14))
    K.shaded_ellipse(img, 16, 22, 7.5, 6.5, (60, 50, 44), (110, 96, 84), (30, 24, 20))   # abdomen
    for y in range(18, 27):                                      # red hourglass mark
        w = abs(y - 22) // 2
        for x in range(16 - w, 17 + w):
            if y != 22:
                K.put(img, x, y, (190, 30, 30))
    K.shaded_ellipse(img, 16, 14, 4.5, 4, (70, 60, 52), (120, 104, 90), (34, 28, 24))   # head
    for x, y in [(14, 13), (18, 13), (15, 12), (17, 12)]:
        K.put(img, x, y, (230, 40, 40))
    K.put(img, 15, 17, (220, 220, 200))
    K.put(img, 17, 17, (220, 220, 200))
    return K.outline_img(img, (16, 12, 10))


@sprite("Wolf")
def wolf():
    rows = [
        "   gg                          ",
        "  gGg                          ",
        "  gGGg                         ",
        " gGGGGgg                       ",
        "gGwGGGGGg          gggg        ",
        "GGGGGGGGGg  ggggggGGGGGgg     g",
        "nGGGGGGGGGggGGGGGGGGGGGGGg  ggG",
        " lllGGGGGGGGGGGGGGGGGGGGGGGgGGg",
        "  llGGGGGGGGGGGGGGGGGGGGGGGGGg ",
        "    lGGGGGGGGGGGGGGGGGGGGGGg   ",
        "     llGGGGGGGGGGGGGGGGGGGg    ",
        "      llllllllllllGGGGGGg      ",
        "      GGg GGg     GGg GGg      ",
        "      GGg GGg     GGg GGg      ",
        "      GGg GGg     GGg GGg      ",
        "      kk  kk      kk  kk       ",
    ]
    img = art(rows, {"g": (96, 96, 104), "G": (140, 140, 150), "w": (230, 200, 40), "n": (20, 20, 20),
                     "l": (204, 204, 210), "k": (60, 60, 66)}, oy=14)
    for y in range(14, 30):                                   # darker back
        for x in range(S):
            if img[y][x] == (140, 140, 150) and y <= 19 and x > 10:
                img[y][x] = (118, 118, 128)
    return K.outline_img(img, (40, 40, 46))


@sprite("Skeleton")
def skeleton():
    rows = [
        "                ",
        "                ",
        "     bbbbbb     ",
        "    bbbbbbbB    ",
        "    bkkbbkkB    ",
        "    bkkbbkkB    ",
        "    bbbkbbbB    ",
        "     btttB      ",
        "      bbB       ",
        "       b        ",
        "    bbbbbbbB    ",
        "   b  bbB  B    ",
        "  b  bbbbbB  B  ",
        "  b   bbB    B  ",
        "  b  bbbbbB  B  ",
        "  b   bbB    B  ",
        "  b  bbbbbB  B  ",
        "  b    bB    B  ",
        "  bb   bB   BB  ",
        "      bbbB      ",
        "     bbbbbB     ",
        "     b    B     ",
        "     b    B     ",
        "     b    B     ",
        "     b    B     ",
        "     b    B     ",
        "     b    B     ",
        "     bb   BB    ",
        "    bbb   BBB   ",
        "                ",
        "                ",
        "                ",
    ]
    img = art(rows, {"b": (226, 222, 204), "B": (170, 164, 146), "k": (20, 16, 16), "t": (200, 196, 180)}, ox=8)
    for y in range(9, 29):                                       # a rusty sword
        K.put(img, 22, y - 6, (150, 120, 100) if y > 14 else (120, 90, 70))
    K.rect(img, 20, 15, 24, 15, (90, 70, 50))
    K.put(img, 13, 5, (255, 60, 40))                              # glowing eyes
    K.put(img, 17, 5, (255, 60, 40))
    return K.outline_img(img, (60, 56, 50))


@sprite("Cave_Troll")
def cave_troll():
    rows = [
        "          gggggggg          ",
        "        ggGGGGGGGGgg        ",
        "       gGGGGGGGGGGGGg       ",
        "       gGGyyGGGGyyGGg       ",
        "       gGGrkGGGGkrGGg       ",
        "       gGGGGGnnGGGGGg       ",
        "        gGtGGGGGGtGg        ",
        "        gGGwwwwwwGGg        ",
        "    gggggGGGGGGGGGGggggg    ",
        "  ggGGGGGGGGGGGGGGGGGGGGgg  ",
        " gGGGGGGGGGGGGGGGGGGGGGGGGg ",
        "gGGGGgGGGGGGGGGGGGGGGGgGGGGg",
        "gGGGg gGGGGGGGGGGGGGGGg gGGg",
        "gGGg  gGGGGGlllllGGGGGg  gGg",
        "gGGg  gGGGGllllllGGGGGg  gGg",
        "gGGg  gGGGGGlllllGGGGGg  gGg",
        "gGGg  gbbbbbbbbbbbbbbbg  gGg",
        "ggGgg  bbbbbbbbbbbbbbb  ggGgg",
        "gGGGg  gGGGGGg  gGGGGg  gGGGg",
        " ggg   gGGGGGg  gGGGGg   ggg ",
        "       gGGGGGg  gGGGGg      ",
        "       gGGGGg    gGGGg      ",
        "      gGGGGGg    gGGGGGg    ",
        "      ggggggg    ggggggg    ",
    ]
    img = art(rows, {"g": (70, 90, 70), "G": (110, 134, 104), "y": (230, 220, 90), "r": (200, 40, 30),
                     "k": (20, 20, 20), "n": (80, 100, 76), "t": (240, 236, 210), "w": (60, 30, 30),
                     "l": (140, 160, 128), "b": (110, 80, 50)}, oy=7)
    for y in range(4, 31):                                     # a big club in the right hand
        x = 29 - (30 - y) // 9
        K.put(img, x, y - 6, (120, 84, 46))
        K.put(img, x + 1, y - 6, (90, 60, 30))
    K.shaded_ellipse(img, 27, 2.5, 2.5, 3, (140, 100, 60), (180, 136, 84), (90, 60, 30))
    return K.outline_img(img, (30, 40, 30))


# ================================================================== ores, bars and the bronze/mithril tiers
# Metals as luminance ramps (dark -> light). metal() recolours only the grey (metal) pixels of a sprite, so wooden
# grips, leather straps and painted crosses keep their colours.
BRONZE_RAMP = [(0.0, (34, 18, 6)), (0.25, (104, 60, 22)), (0.45, (166, 108, 44)), (0.7, (214, 160, 84)),
               (1.0, (255, 228, 164))]
MITHRIL_RAMP = [(0.0, (6, 24, 34)), (0.25, (24, 84, 102)), (0.45, (46, 144, 156)), (0.7, (112, 212, 210)),
                (1.0, (228, 255, 250))]
SILVER_RAMP = [(0.0, (26, 28, 36)), (0.25, (104, 108, 122)), (0.45, (166, 172, 186)), (0.7, (214, 220, 232)),
               (1.0, (255, 255, 255))]
IRON_RAMP = [(0.0, (20, 20, 24)), (0.25, (70, 70, 78)), (0.45, (130, 130, 138)), (0.7, (186, 186, 194)),
             (1.0, (240, 240, 246))]
STEEL_RAMP = [(0.0, (14, 18, 26)), (0.25, (70, 84, 100)), (0.45, (128, 146, 166)), (0.7, (186, 202, 220)),
              (1.0, (245, 250, 255))]
TIN_RAMP = [(0.0, (28, 30, 28)), (0.3, (92, 96, 92)), (0.55, (146, 152, 146)), (0.8, (198, 204, 198)),
            (1.0, (240, 244, 240))]
WOOD = ((176, 120, 64), (130, 84, 40), (84, 52, 22))           # light, mid, dark


def metal(name, ramp, sat=36):
    img = K.load("Entities", name)
    out = K.gradient_map(img, ramp)
    for y, r in enumerate(img):
        for x, c in enumerate(r):
            if c is not None and max(c) - min(c) > sat:
                out[y][x] = c
    return out


def specked_ore(specks, seed):
    img = gm("Iron_Ore", [(0.0, (30, 28, 26)), (0.3, (86, 82, 78)), (0.55, (128, 122, 116)), (1.0, (196, 190, 182))])
    rng = random.Random(seed)
    pts = [(x, y) for y, r in enumerate(img) for x, c in enumerate(r) if c is not None]
    for _ in range(30):
        x, y = rng.choice(pts)
        img[y][x] = rng.choice(specks)
    return img


@sprite("Tin_Ore")
def tin_ore():
    return gm("Iron_Ore", TIN_RAMP)


@sprite("Silver_Ore")
def silver_ore():
    return specked_ore([(255, 255, 255), (214, 222, 236), (170, 180, 200)], 11)


@sprite("Mithril_Ore")
def mithril_ore():
    return specked_ore([(150, 240, 236), (70, 190, 196), (220, 255, 250)], 13)


@sprite("Bronze_Bar")
def bronze_bar():
    return gm("Iron_Bar", BRONZE_RAMP)


@sprite("Silver_Bar")
def silver_bar():
    return gm("Iron_Bar", SILVER_RAMP)


@sprite("Mithril_Bar")
def mithril_bar():
    return gm("Iron_Bar", MITHRIL_RAMP)


for _tier, _ramp in (("Bronze", BRONZE_RAMP), ("Mithril", MITHRIL_RAMP)):
    for _part in ("Sword", "Helm", "Shield", "Platebody", "Platelegs"):
        SPRITES["%s_%s" % (_tier, _part)] = (lambda part=_part, ramp=_ramp: metal("Iron_" + part, ramp))
for _tier, _ramp in (("Iron", IRON_RAMP), ("Steel", STEEL_RAMP), ("Mithril", MITHRIL_RAMP)):
    SPRITES[_tier + "_Boots"] = (lambda ramp=_ramp: gm("Leather_Boots", ramp))
    SPRITES[_tier + "_Gauntlets"] = (lambda ramp=_ramp: gm("Leather_Gloves", ramp))


def handle(img, x0, y0, x1, y1):
    seg(img, x0, y0, x1, y1, 2.6, *WOOD)
    K.put(img, int(x0), int(y0), WOOD[2])


def pickaxe(ramp):
    img = K.new()
    handle(img, 7, 28, 20, 9)
    l, m, d = ramp[4][1], ramp[2][1], ramp[1][1]
    # the head: a shallow arc across the top of the handle, thick in the middle, pointed at both ends
    pts = [(9, 9), (13, 6), (18, 6.5), (22, 8.5), (26, 12), (29, 17)]
    widths = [1.6, 2.6, 3.4, 3.4, 2.6, 1.6]
    for (ax, ay), (bx, by), w in zip(pts, pts[1:], widths):
        seg(img, ax, ay, bx, by, w, l, m, d)
    return K.outline_img(img, (24, 18, 12))


def axe(ramp):
    img = K.new()
    handle(img, 9, 29, 20, 5)
    l, m, d = ramp[4][1], ramp[2][1], ramp[1][1]
    # the blade: a wedge on the right of the handle's top, widening to a curved edge
    for y in range(S):
        for x in range(S):
            u, v = (x + 0.5 - 19.5) / 9.0, (y + 0.5 - 9.5) / 7.5
            if 0.05 <= u <= 1 and abs(v) <= 0.35 + 0.65 * u and (u - 0.15) ** 2 + v * v * 0.55 <= 0.75:
                edge = (u - 0.15) ** 2 + v * v * 0.55 > 0.52
                img[y][x] = l if edge else (m if v < 0.1 else d)
    return K.outline_img(img, (24, 18, 12))


# the iron tools keep their old names (Pickaxe, Axe): redrawn so the four tiers match
SPRITES["Pickaxe"] = lambda: pickaxe(IRON_RAMP)
SPRITES["Axe"] = lambda: axe(IRON_RAMP)
for _tier, _ramp in (("Bronze", BRONZE_RAMP), ("Steel", STEEL_RAMP), ("Mithril", MITHRIL_RAMP)):
    SPRITES[_tier + "_Pickaxe"] = (lambda ramp=_ramp: pickaxe(ramp))
    SPRITES[_tier + "_Axe"] = (lambda ramp=_ramp: axe(ramp))


@sprite("Silver_Ring")
def silver_ring():
    return gm("Gold_Ring", SILVER_RAMP)


@sprite("Silver_Tiara")
def silver_tiara():
    img = K.new()
    l, m, d = (255, 255, 255), (196, 202, 216), (120, 126, 142)
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - 16) / 12.0, (y + 0.5 - 18) / 6.0
            dd = dx * dx + dy * dy
            if 0.62 <= dd <= 1.0:
                img[y][x] = l if dy < -0.4 else m if dy < 0.5 else d
    for cx, h in ((10, 4), (16, 7), (22, 4)):                    # three points on the front of the band
        for i in range(h):
            for dx in range(-(h - i) // 2, (h - i) // 2 + 1):
                K.put(img, cx + dx, 21 - i, l if dx < 0 else m)
    K.shaded_ellipse(img, 16, 19, 2.2, 2.2, (70, 110, 220), (170, 200, 255), (30, 50, 140), outline=(120, 126, 142))
    return K.outline_img(img, (50, 52, 64))


# ================================================================== spell scrolls
PARCHMENT = ((246, 230, 190), (224, 200, 150), (176, 146, 98))     # light, mid, dark


def scroll(seal=None, rune=None):
    """A sheet of parchment, rolled at both ends; spell scrolls have a coloured rune and a wax seal."""
    img = K.new()
    l, m, d = PARCHMENT
    for y in range(9, 24):                       # the flat sheet between the rolls
        for x in range(9, 24):
            img[y][x] = l if (x + y) % 7 else m
    for x in range(9, 24):
        img[23][x] = d
    for yy, (cy) in enumerate((8, 24)):          # the rolls, top and bottom
        for x in range(6, 27):
            for dy in (-2, -1, 0, 1, 2):
                c = l if dy < 0 else m if dy == 0 else d
                if abs(dy) == 2 and (x in (6, 26)):
                    continue
                img[cy + dy][x] = c
        img[cy][5] = d
        img[cy][27] = d
    for y in (11, 14, 17, 20):                   # lines of writing
        for x in range(11, 22):
            if (x * 3 + y) % 5:
                img[y][x] = (120, 96, 70) if not rune else rune[1]
    if rune:
        K.shaded_ellipse(img, 16, 15.5, 4.2, 4.2, rune[0], K.mix(rune[0], (255, 255, 255), 0.5), rune[1])
    if seal:
        K.shaded_ellipse(img, 22, 22, 3.2, 3.2, seal, K.mix(seal, (255, 255, 255), 0.4), K.mul(seal, 0.6))
        for k in range(3):                       # the ribbon under the seal
            K.put(img, 21 + k, 26 + k // 2, K.mul(seal, 0.8))
    return K.outline_img(img, (70, 52, 30))


SCROLLS = {   # name: (seal colour, (rune colour, rune shade))
    "Fire_Bolt_Scroll": ((200, 40, 30), ((255, 150, 40), (180, 60, 10))),
    "Ice_Bolt_Scroll": ((40, 90, 200), ((140, 210, 255), (40, 110, 200))),
    "Lightning_Scroll": ((150, 120, 20), ((255, 240, 100), (190, 150, 20))),
    "Fire_Storm_Scroll": ((120, 20, 20), ((255, 90, 30), (150, 20, 10))),
    "Healing_Scroll": ((30, 140, 60), ((120, 240, 130), (30, 130, 60))),
    "Stone_Skin_Scroll": ((110, 90, 60), ((200, 180, 140), (110, 90, 60))),
    "Teleport_Scroll": ((110, 50, 170), ((210, 150, 255), (110, 50, 170))),
    "Farsight_Scroll": ((30, 120, 130), ((150, 235, 240), (30, 120, 140))),
    "Frost_Nova_Scroll": ((90, 160, 220), ((225, 246, 255), (90, 160, 220))),
    "Thunderclap_Scroll": ((70, 80, 110), ((245, 240, 150), (90, 100, 140))),
    "Blizzard_Scroll": ((190, 214, 240), ((255, 255, 255), (110, 150, 200))),
}
SPRITES["Blank_Scroll"] = lambda: scroll()
for _name, (_seal, _rune) in SCROLLS.items():
    SPRITES[_name] = (lambda seal=_seal, rune=_rune: scroll(seal, rune))


def upgrade_scroll(seal, rune, rank):
    """An upgrade's scroll (build_shards.py: Rank=2...): the spell's scroll with its rank in gold strokes, II or III,
    down its left side, and a gold seal."""
    img = scroll((214, 170, 60), rune)
    for k in range(rank):
        for y in range(11, 21):
            K.put(img, 4 + k * 3, y, (240, 200, 80) if y % 9 else (255, 236, 150))
            K.put(img, 5 + k * 3, y, (150, 110, 30))
    return K.outline_img(img, (70, 52, 30))


for _name, _rank in (("Fire_Bolt", 2), ("Fire_Bolt", 3), ("Healing", 2), ("Ice_Bolt", 2), ("Lightning", 2),
                     ("Frost_Nova", 2), ("Fire_Storm", 2)):
    _seal, _rune = SCROLLS[_name + "_Scroll"]
    SPRITES["%s_Scroll_%s" % (_name, "I" * _rank)] = (lambda seal=_seal, rune=_rune, r=_rank: upgrade_scroll(seal, rune, r))


# ================================================================== skill tiers: logs, fish, food, potions, wooden gear
@sprite("Oak_Logs")
def oak_logs():
    return gm("Logs", [(0.0, (36, 20, 8)), (0.3, (96, 60, 28)), (0.6, (146, 100, 52)), (1.0, (214, 176, 120))])


@sprite("Willow_Logs")
def willow_logs():
    return gm("Logs", [(0.0, (50, 44, 26)), (0.3, (118, 106, 68)), (0.6, (176, 164, 110)), (1.0, (236, 228, 186))])


@sprite("Yew_Logs")
def yew_logs():
    return gm("Logs", [(0.0, (40, 10, 6)), (0.3, (108, 38, 24)), (0.6, (162, 72, 48)), (1.0, (226, 154, 114))])


@sprite("Raw_Salmon")
def raw_salmon():
    return fish_map("Raw_Fish", [(0.0, (60, 30, 30)), (0.3, (150, 80, 76)), (0.6, (226, 130, 116)), (1.0, (255, 214, 200))])


@sprite("Cooked_Salmon")
def cooked_salmon():
    return fish_map("Cooked_Fish", [(0.0, (60, 26, 14)), (0.3, (160, 80, 40)), (0.6, (226, 140, 84)), (1.0, (255, 220, 170))])


@sprite("Raw_Swordfish")
def raw_swordfish():
    img = fish_map("Raw_Fish", [(0.0, (14, 24, 50)), (0.3, (50, 80, 130)), (0.6, (110, 150, 200)), (1.0, (220, 236, 255))])
    pts = [(x, y) for y, r in enumerate(img) for x, c in enumerate(r) if c is not None]
    if pts:                                               # the sword: a long bill out of the front of its head
        x0 = min(x for x, y in pts)
        ys = sorted(y for x, y in pts if x <= x0 + 1)
        y0 = ys[len(ys) // 2]
        for k in range(1, 6):
            K.put(img, x0 - k, y0, (200, 210, 230))
    return img


@sprite("Cooked_Swordfish")
def cooked_swordfish():
    return fish_map("Cooked_Fish", [(0.0, (40, 30, 20)), (0.3, (120, 96, 70)), (0.6, (196, 168, 130)), (1.0, (250, 236, 210))])


@sprite("Meat_Pie")
def meat_pie():
    return pie((140, 70, 40), (90, 40, 20), lattice=False)


@sprite("Stew")
def stew():
    img = K.new()
    K.shaded_ellipse(img, 16, 19, 11, 7, (120, 80, 50), (170, 120, 80), (70, 44, 24), outline=(40, 24, 10))   # the bowl
    K.shaded_ellipse(img, 16, 16, 9, 3.4, (150, 80, 40), (200, 130, 80), (110, 56, 26))                       # the stew
    for x, y, c in ((12, 16, (230, 140, 50)), (18, 15, (90, 150, 50)), (15, 17, (200, 120, 70)), (20, 17, (230, 140, 50))):
        K.put(img, x, y, c)
        K.put(img, x + 1, y, c)
    for k, x in enumerate((11, 16, 21)):                                                                      # steam
        for y in range(5, 11):
            if (y + k) % 3:
                K.put(img, x + (1 if (y // 2 + k) % 2 else 0), y, (230, 230, 240))
    return img


def potion(hue):
    return K.hue_shift(K.load("Entities", "Basic_Potion"), target_hue=hue, sat_mul=1.05, pred=lambda c: max(c) - min(c) > 40)


SPRITES["Defence_Potion"] = lambda: potion(0.11)
SPRITES["Combat_Potion"] = lambda: potion(0.83)
SPRITES["Magic_Potion"] = lambda: potion(0.72)
SPRITES["Mega_Potion"] = lambda: potion(0.30)
SPRITES["Owl_Potion"] = lambda: potion(0.58)

# ----- the Wildlands (build_regions.py): monsters recoloured from the wolf, spider and troll (their walking frames come
# from build_walk.py), and the quest items
SPRITES["Bear"] = lambda: gm("Wolf", [(0.0, (20, 12, 6)), (0.3, (70, 42, 22)), (0.6, (120, 78, 42)), (1.0, (180, 140, 100))])
SPRITES["Snow_Wolf"] = lambda: gm("Wolf", [(0.0, (40, 46, 60)), (0.3, (150, 160, 176)), (0.6, (214, 220, 232)), (1.0, (250, 252, 255))])
SPRITES["Alpha_Wolf"] = lambda: gm("Wolf", [(0.0, (10, 8, 8)), (0.3, (46, 40, 42)), (0.6, (84, 74, 76)), (0.85, (160, 40, 30)), (1.0, (230, 60, 40))])
SPRITES["Scorpion"] = lambda: gm("Giant_Spider", [(0.0, (40, 20, 6)), (0.3, (140, 80, 30)), (0.6, (210, 140, 60)), (1.0, (250, 220, 140))])
SPRITES["Bog_Troll"] = lambda: gm("Cave_Troll", [(0.0, (14, 22, 10)), (0.3, (50, 80, 40)), (0.6, (96, 130, 70)), (1.0, (180, 200, 140))])
SPRITES["Frost_Troll"] = lambda: gm("Cave_Troll", [(0.0, (16, 24, 40)), (0.3, (80, 110, 150)), (0.6, (150, 190, 220)), (1.0, (240, 250, 255))])
# (Bog_Myrtle, once the herb recoloured, is drawn by build_herbs.py now, with the other herbs)
SPRITES["Witch_Brew"] = lambda: potion(0.45)
@sprite("Ferry_Ticket")
def ferry_ticket():
    """The ferry ticket (the Isle's starter quest): a slanted cream card with a red band, print and a punched hole."""
    img = K.new()
    for y in range(9, 24):
        for x in range(4, 28):
            c = (238, 226, 190) if (x + y) % 5 else (226, 212, 172)
            if 4 <= x <= 8:
                c = (176, 40, 36) if (x + y) % 4 else (150, 30, 28)
            K.put(img, x + (y - 16) // 4, y, c)
    for y, x0, x1 in ((12, 11, 24), (15, 11, 22), (18, 11, 25), (21, 11, 19)):     # the printing
        for x in range(x0, x1):
            if x % 3:
                K.put(img, x + (y - 16) // 4, y, (90, 70, 50))
    for x, y in ((6, 15), (7, 15), (6, 16), (7, 16)):                              # the punched hole
        img[y][x + (y - 16) // 4] = None
    return K.outline_img(img, (70, 50, 30))


SPRITES["Stolen_Goods"] = lambda: gm("Wool", [(0.0, (40, 26, 12)), (0.4, (120, 86, 50)), (0.7, (176, 140, 96)), (1.0, (230, 210, 170))])
SPRITES["Caravan_Ledger"] = lambda: gm("Blank_Scroll", [(0.0, (30, 14, 8)), (0.4, (110, 50, 30)), (0.7, (190, 150, 100)), (1.0, (240, 226, 190))])
SPRITES["Strongbox"] = lambda: gm("Chest", [(0.0, (14, 14, 18)), (0.35, (70, 72, 80)), (0.65, (130, 132, 140)), (1.0, (220, 200, 120))])


@sprite("Heart")
def heart():
    """The Hitpoints skill's icon (Config.ini [Skills] Icon.Hitpoints): a shaded red heart."""
    img = K.new()
    base, light, dark = (200, 30, 40), (255, 120, 120), (120, 10, 20)
    for y in range(S):
        for x in range(S):
            u, v = (x + 0.5 - 16) / 11.5, (15 - (y + 0.5)) / 11.5   # the heart curve spans u -1.14..1.14, v -1..1.2
            if (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0:
                shade = (u + v) * 0.5                 # lit from the top left
                img[y][x] = K.mix(base, light, min(1, -shade * 1.6 + 0.2)) if shade < 0 else K.mix(base, dark, min(1, shade * 1.2))
    for (x, y) in ((9, 7), (10, 7), (8, 8), (9, 8), (8, 9)):   # a little shine
        K.put(img, x, y, (255, 210, 210))
    return K.outline_img(img, (70, 10, 15))


@sprite("Mana")
def mana():
    """The Mana tile's icon (the Stats tab): a glowing blue droplet with a white spark."""
    img = K.new()
    base, light, dark = (50, 110, 230), (140, 200, 255), (20, 40, 130)
    for y in range(S):
        for x in range(S):
            u, v = (x + 0.5 - 16) / 10.0, (y + 0.5 - 19) / 10.0
            if (v > 0 and u * u + v * v <= 1) or (v <= 0 and v >= -1.35 and abs(u) <= 1 + v / 1.35):
                shade = (u + v) * 0.5
                img[y][x] = K.mix(base, light, min(1, -shade * 1.6 + 0.2)) if shade < 0 else K.mix(base, dark, min(1, shade * 1.2))
    for (x, y) in ((12, 16), (12, 17), (13, 15), (11, 18)):
        K.put(img, x, y, (230, 245, 255))
    return K.outline_img(img, (10, 20, 70))


def wood_shield(light, mid, dark, rim):
    img = K.new()
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - 16) / 12.0, (y + 0.5 - 16) / 12.0
            d = dx * dx + dy * dy
            if d <= 1:
                plank = int((x - 4) / 5)
                c = (light, mid, dark)[plank % 3] if d < 0.78 else rim[1]
                if d >= 0.78 and -dx - dy > 0.4:
                    c = rim[0]
                if d < 0.78 and (x - 4) % 5 == 0:
                    c = K.mul(dark, 0.8)                                  # the gaps between the planks
                img[y][x] = c
    K.shaded_ellipse(img, 16, 16, 3, 3, rim[1], rim[0], rim[2])          # the boss
    return K.outline_img(img, (30, 20, 10))


SPRITES["Wooden_Shield"] = lambda: wood_shield((176, 120, 64), (150, 100, 52), (124, 82, 40),
                                               ((200, 200, 206), (140, 140, 148), (80, 80, 88)))
SPRITES["Oak_Shield"] = lambda: wood_shield((150, 104, 56), (124, 82, 40), (100, 64, 30),
                                            ((250, 214, 90), (200, 150, 40), (120, 84, 10)))


def staff(wood, orb=None, knot=False):
    img = K.new()
    seg(img, 8, 29, 22, 6, 2.6, *wood)
    if orb:
        K.shaded_ellipse(img, 23, 5.5, 3.6, 3.6, orb[0], orb[1], orb[2], outline=(30, 20, 10))
        K.put(img, 22, 4, (255, 255, 255))
        for x, y in ((19, 2), (27, 3), (26, 9)):                          # a little sparkle round the gem
            K.put(img, x, y, orb[1])
    if knot:
        K.shaded_ellipse(img, 22.5, 6, 3.4, 2.6, wood[1], wood[0], wood[2], outline=(30, 20, 10))
    return K.outline_img(img, (30, 20, 10))


SPRITES["Oak_Staff"] = lambda: staff(((176, 128, 72), (130, 88, 44), (84, 54, 24)), knot=True)
SPRITES["Willow_Staff"] = lambda: staff(((226, 214, 160), (176, 162, 110), (120, 108, 68)),
                                        orb=((60, 110, 220), (170, 200, 255), (20, 40, 140)))
SPRITES["Yew_Staff"] = lambda: staff(((196, 110, 80), (150, 70, 46), (96, 36, 22)),
                                     orb=((200, 30, 40), (255, 140, 140), (110, 10, 20)))


# ================================================================== wildlife (side-on ones face west, like the others)
@sprite("Rabbit")
def rabbit():
    img = K.new()
    fur, light, dark = (150, 110, 70), (196, 156, 110), (100, 70, 40)
    K.shaded_ellipse(img, 18, 23, 7, 5, fur, light, dark, outline=(60, 40, 20))           # body
    K.shaded_ellipse(img, 11, 19, 4, 3.6, fur, light, dark, outline=(60, 40, 20))         # head
    for y in range(10, 17):                                                                 # ears
        K.put(img, 11, y, dark); K.put(img, 12, y, light)
        K.put(img, 14, y + 1, dark); K.put(img, 15, y + 1, fur)
    K.shaded_ellipse(img, 25, 21, 2, 2, (240, 240, 236), (255, 255, 255), (200, 200, 196))  # tail
    K.put(img, 9, 19, (20, 20, 20))                                                        # eye
    K.put(img, 7, 20, (220, 140, 150))                                                     # nose
    for x in (13, 21):                                                                     # feet
        K.put(img, x, 28, dark); K.put(img, x + 1, 28, dark)
    return img


@sprite("Duck")
def duck():
    img = K.new()
    body, light, dark = (180, 150, 110), (220, 196, 160), (120, 96, 66)
    K.shaded_ellipse(img, 18, 22, 8, 5, body, light, dark, outline=(70, 50, 30))
    for x in range(14, 23):                                                                # wing
        K.put(img, x, 21, dark)
    K.shaded_ellipse(img, 11, 15, 3.6, 3.4, (40, 120, 60), (80, 170, 90), (20, 70, 30), outline=(20, 40, 20))  # green head
    for x in range(10, 13):
        K.put(img, x, 18, (240, 240, 240))                                                # white collar
    for x in range(5, 8):
        K.put(img, x, 15, (240, 170, 40)); K.put(img, x, 16, (210, 130, 20))              # beak
    K.put(img, 10, 14, (10, 10, 10))
    for x in (15, 20):
        K.put(img, x, 27, (240, 150, 30)); K.put(img, x + 1, 27, (240, 150, 30)); K.put(img, x, 26, (240, 150, 30))
    return img


@sprite("Butterfly")
def butterfly():
    img = K.new()
    for (cx, cy, rx, ry) in ((12, 14, 4.5, 4), (20, 14, 4.5, 4), (13, 20, 3, 3), (19, 20, 3, 3)):
        K.shaded_ellipse(img, cx, cy, rx, ry, (240, 140, 40), (255, 200, 100), (190, 90, 20), outline=(40, 20, 10))
    for x, y in ((11, 13), (21, 13), (13, 20), (19, 20)):
        K.put(img, x, y, (40, 20, 10))
    for y in range(11, 23):
        K.put(img, 16, y, (40, 30, 30))
    K.put(img, 15, 10, (40, 30, 30)); K.put(img, 17, 10, (40, 30, 30))
    K.put(img, 14, 9, (40, 30, 30)); K.put(img, 18, 9, (40, 30, 30))
    return img


# ================================================================== main
# ================================================================== the dragon (build_dragon.py): 64 x 64, front on, wings spread
BIG = {"Dragon": 64}          # sprites bigger than 32 x 32 (the game sizes entities from their sprite)


@sprite("Dragon")
def dragon():
    D = 64
    img = K.new(D, D)
    red, light, dark, deep = (196, 34, 26), (240, 96, 60), (128, 18, 14), (70, 8, 8)
    belly, belly_d = (236, 186, 96), (196, 140, 60)

    def blob(cx, cy, rx, ry, base, hi, lo):
        for y in range(D):
            for x in range(D):
                dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if dx * dx + dy * dy <= 1:
                    k = -(dx + dy) * 0.7
                    img[y][x] = hi if k > 0.45 else lo if k < -0.45 else base

    def wing(sign):
        # a bat wing: from the shoulder out to the tip, three fingers, the membrane scalloped between them
        sx, sy = 32 + sign * 7, 27
        tips = [(32 + sign * 30, 4), (32 + sign * 31, 22), (32 + sign * 26, 36), (32 + sign * 15, 40)]
        for y in range(D):
            for x in range(D):
                for (ax, ay), (bx, by) in zip(tips, tips[1:]):
                    # inside the triangle shoulder - finger tip - next finger tip, less a scallop
                    d1 = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
                    d2 = (sx - bx) * (y - by) - (sy - by) * (x - bx)
                    d3 = (ax - sx) * (y - sy) - (ay - sy) * (x - sx)
                    if (d1 >= 0 and d2 >= 0 and d3 >= 0) or (d1 <= 0 and d2 <= 0 and d3 <= 0):
                        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
                        if math.hypot(x - mx, y - my) > 5.5 or math.hypot(x - sx, y - sy) < math.hypot(mx - sx, my - sy) - 3:
                            img[y][x] = dark if (x + y) % 7 else deep
        for tx, ty in tips:                          # the wing bones
            n = int(math.hypot(tx - sx, ty - sy))
            for i in range(n + 1):
                x, y = int(sx + (tx - sx) * i / n), int(sy + (ty - sy) * i / n)
                if 0 <= x < D and 0 <= y < D:
                    img[y][x] = light if i < n - 2 else (240, 230, 200)

    wing(-1)
    wing(1)
    for i, (cx, cy, r) in enumerate([(40, 54, 5), (46, 57, 4), (51, 59, 3.5), (55, 58, 3), (58, 55, 2.5)]):   # tail
        blob(cx, cy, r, r, red, light, dark)
    for x, y in ((60, 52), (61, 53), (60, 53), (59, 51), (61, 51)):                                       # its spade tip
        img[y][x] = dark
    blob(32, 42, 12, 15, red, light, dark)                                                              # body
    blob(32, 45, 6, 10, belly, (250, 214, 140), belly_d)                                                # belly
    for y in range(37, 55, 3):
        for x in range(27, 38):
            if img[y][x] in (belly, belly_d, (250, 214, 140)):
                img[y][x] = belly_d
    for lx in (23, 41):                                                                                 # legs and claws
        blob(lx, 54, 4.5, 6.5, red, light, dark)
        for cx in (lx - 3, lx, lx + 3):
            img[60][cx] = (240, 230, 200)
            img[61][cx] = (200, 190, 160)
    for y in range(18, 30):                                                                             # neck
        for x in range(28, 37):
            img[y][x] = red if x < 33 else dark
    blob(32, 15, 8, 7, red, light, dark)                                                                # head
    blob(32, 22, 5, 4, red, light, dark)                                                                # snout
    for (x0, y0), (x1, y1) in (((26, 11), (21, 2)), ((38, 11), (43, 2))):                               # horns
        for i in range(11):
            x, y = int(x0 + (x1 - x0) * i / 10.0), int(y0 + (y1 - y0) * i / 10.0)
            img[y][x] = (236, 226, 196)
            img[y][x + 1] = (190, 178, 150)
    for ex in (28, 36):                                                                                 # burning eyes
        img[14][ex] = (255, 230, 60)
        img[14][ex + 1] = (255, 160, 20)
        img[15][ex] = (255, 160, 20)
    img[23][30] = deep                                                                                  # nostrils
    img[23][34] = deep
    for x in range(29, 36):                                                                             # teeth
        if x % 2:
            img[25][x] = (240, 236, 220)
    return K.outline_img(img, (40, 6, 6))


def bow(light, mid, dark):
    """A bow drawn diagonally, curving up-left, with its string."""
    img = K.new()
    for i in range(41):
        t = i / 40.0
        x = 6 + 20 * t - 7 * math.sin(math.pi * t)          # bottom-left to top-right, bowed out towards the top-left
        y = 26 - 20 * t - 7 * math.sin(math.pi * t)
        for dx, dy, c in ((0, 0, mid), (1, 0, light), (0, 1, dark)):
            K.put(img, int(x) + dx, int(y) + dy, c)
    for i in range(21):                                   # the string, straight from tip to tip
        K.put(img, int(7 + 19 * i / 20.0), int(26 - 20 * i / 20.0), (232, 228, 214))
    for x, y in ((14, 17), (15, 16), (16, 15)):           # the grip
        K.put(img, x - 3, y - 3, (90, 50, 30))
    return K.outline_img(img, (40, 26, 14))


SPRITES["Oak_Bow"] = lambda: bow((190, 140, 80), (150, 100, 52), (100, 64, 30))
SPRITES["Yew_Bow"] = lambda: bow((220, 120, 90), (160, 70, 46), (100, 36, 22))


@sprite("Arrows")
def arrows():
    """A bundle of three arrows."""
    img = K.new()
    for k, (ox, oy) in enumerate(((0, 0), (3, 2), (6, 4))):
        for i in range(18):
            K.put(img, 6 + ox + i, 24 + oy - i, (156, 108, 62))
        for dx, dy in ((0, 0), (1, 0), (0, 1), (2, -1), (1, -1)):
            K.put(img, 24 + ox + dx, 6 + oy + dy, (200, 204, 214))
        for dx, dy in ((0, 0), (1, 1), (-1, 1), (0, 2), (2, 2), (-1, 0)):
            K.put(img, 6 + ox + dx, 24 + oy + dy - 2, (240, 240, 240))
    return K.outline_img(img, (40, 30, 20))


@sprite("Shardstone")
def shardstone():
    """Fast travel (build_travel.py): a tall grey standing stone with a glowing blue rune."""
    img = K.new()
    for y in range(3, 31):
        half = 6 if y > 8 else 3 + (y - 3) // 2        # a rounded top
        for x in range(16 - half, 16 + half):
            shade = (150, 150, 158) if x < 14 else (118, 118, 128) if x < 19 else (88, 88, 98)
            if (x * 7 + y * 3) % 11 == 0:
                shade = tuple(v - 18 for v in shade)    # pits in the stone
            img[y][x] = shade
    for y in range(29, 32):                              # the base, a little wider
        for x in range(8, 24):
            img[y][x] = (96, 90, 82)
    rune = [(16, 11), (16, 12), (16, 13), (16, 14), (16, 15), (16, 16), (16, 17), (14, 12), (15, 13), (17, 13), (18, 12),
            (14, 17), (15, 16), (17, 16), (18, 17), (16, 19), (15, 20), (17, 20), (16, 21)]
    for x, y in rune:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):      # a soft glow round it
            if img[y + dy][x + dx] is not None and (x + dx, y + dy) not in rune:
                img[y + dy][x + dx] = K.mix(img[y + dy][x + dx], (110, 190, 255), 0.45)
    for x, y in rune:
        img[y][x] = (200, 240, 255)
    return K.outline_img(img, (40, 40, 48))


def shardstone_sparkle(frame):
    """The shardstone with a star twinkling at its tip (Shardstone1..4, Anim.Frames): it swells and fades, a mote or two
    drifting up beside it."""
    img = shardstone()
    arm = (2, 3, 4, 3)[frame]
    core = ((200, 235, 255), (235, 250, 255), (255, 255, 255), (225, 245, 255))[frame]
    cx, cy = 16, 4
    for d in range(1, arm + 1):                           # the star's four arms, fading out to their tips
        c = K.mix(core, (110, 190, 255), d / (arm + 1.0))
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            K.put(img, cx + dx, cy + dy, c)
    if arm >= 2:
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            K.put(img, cx + dx, cy + dy, K.mix(core, (110, 190, 255), 0.6))
    K.put(img, cx, cy, core)
    for mx, my in (((11, 7), (21, 9)), ((12, 5), (20, 7)), ((11, 3), (21, 5)), ((12, 1), (20, 3)))[frame]:
        K.put(img, mx, my, (170, 220, 255))               # (motes rising)
    return img


for _f in range(4):
    SPRITES["Shardstone%d" % (_f + 1)] = (lambda f=_f: shardstone_sparkle(f))


@sprite("Shard")
def shard():
    """A Shard of the world's magic: a tall splinter of glowing crystal, violet at its edges and pale blue at its
    heart, leaning, with a chip beside it and a glint (nothing like the round gems)."""
    img = K.new()
    edge, mid, heart, glint = (110, 60, 190), (130, 150, 245), (190, 235, 255), (255, 255, 255)
    for y in range(4, 28):                                # the splinter: widest a third of the way down
        t = (y - 4) / 23.0
        half = 1 + int(5 * (1 - abs(t - 0.38) / 0.62))
        cx = 18 - (y - 4) * 5 // 23                       # (leaning to the right at its tip)
        for x in range(cx - half, cx + half + 1):
            d = abs(x - cx) / max(1, half)
            img[y][x] = heart if d < 0.3 else mid if d < 0.75 else edge
            if x == cx - half:
                img[y][x] = K.mul(edge, 0.75)             # (the shaded face)
    for y in range(20, 27):                               # a small chip beside it
        for x in range(21, 21 + (27 - y) // 2):
            img[y][x] = mid if x < 22 else edge
    for dx, dy in ((0, 0), (1, 1), (0, 1), (-1, 1)):
        K.put(img, 16 + dx, 9 + dy, glint)
    return K.outline_img(img, (40, 24, 70))


@sprite("Feather")
def feather():
    """A grey goose feather (arrows are fletched with them): a pale quill, the vane shaded, a white tip."""
    img = K.new()
    for i in range(20):                                   # the shaft, from the quill (bottom left) up and right
        x, y = 8 + i * 16 // 20, 26 - i
        K.put(img, x, y, (236, 230, 214) if i < 5 else (214, 208, 196))
        if i >= 5:
            w = 3 if 7 < i < 17 else 2
            for k in range(1, w + 1):
                K.put(img, x - k, y - k // 2, (150, 152, 160) if k < w else (118, 120, 130))   # the vane, each side
                K.put(img, x + k, y + k // 2, (176, 178, 186) if k < w else (140, 142, 150))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 1)):
        K.put(img, 24 + dx, 6 + dy, (246, 246, 250))      # (a white tip)
    return K.outline_img(img, (50, 50, 58))


SPRITES["Dragon_Sword"] = lambda: gm("Mithril_Sword", [(0.0, (60, 8, 6)), (0.35, (150, 24, 18)), (0.65, (226, 70, 40)), (0.85, (255, 190, 90)), (1.0, (255, 240, 200))])


def main():
    made = {}
    import build_people                         # people and goblins are drawn there (on the player's body) now
    for name in build_people.PEOPLE:
        SPRITES.pop(name, None)
    for name, fn in SPRITES.items():
        img = fn()
        assert K.size(img)[0] <= BIG.get(name, S) and K.size(img)[1] <= BIG.get(name, S), name
        made[name] = img
        changed = K.save("Interface" if name in INTERFACE else "Entities", name, img)
        print(("wrote " if changed else "unchanged ") + name)
    if "--preview" in sys.argv:
        names = list(SPRITES)
        K.sheet(p("dev", "Renders", "Entities preview.png"), [made[n] for n in names], scale=3, cols=10)
        print("preview: dev\\Renders\\Entities preview.png")
        print("  order: " + ", ".join(names))


if __name__ == "__main__":
    main()
