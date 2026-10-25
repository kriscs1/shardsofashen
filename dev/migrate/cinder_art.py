"""The pictures for the Cinderlands, the banks and Wardhaven's Dragonforge (build_cinder.py uses them).

Tiles (sprites\\Tiles), drawn here pixel by pixel like the other tile builders:
  * ground (opaque): Ash001 (grey ash with char and the odd ember), Cinder001 (cracked basalt), Lava001 (molten rock under
    a dark crust: Tiles.ini Flame=1 makes its bright pixels flicker, Light=40 lights the night)
  * decor (see-through, Layer=Decor): Dead_Tree001/002 (burnt trees), Basalt_Rock001, Ember_Vent001 (a glowing crack),
    Cult_Shrine001 (the Ashen Hand's obsidian altar), Bank_Column001 (a white column for a bank's front), Bank_Plaque001
    (a gilt plaque with a coin), Bank_Counter001 (a marble counter with stacked coins: a bank stall), Hero_Statue001 (a
    gilt statue of the dragon-slayer), Dragon_Skull001 (Ignaroth's skull, mounted)
Entities (sprites\\Entities, and their walking frames in sprites\\Walk), recoloured from ones that exist: the Warden
(the Captain in ember red), the Scout (the Ranger in ash grey), the Ashen Cultist and the Ashen Priest (the acolyte in
charcoal / crimson), the Ember Hound (a charcoal wolf with glowing eyes and mane), the Wyrmsmith (the Forgemaster in a
dragon-hide apron), the Dragonforge (the furnace in obsidian), Dragonscale armour (the mithril pieces in crimson and
gold), the Ashen Codex, a Scout's Tag and a Dragon Scale."""
import colorsys
import math
import os
import random

import numpy as np
from PIL import Image

from common import p, write_image

S = 32
YS, XS = np.mgrid[0:S, 0:S]


def noise(seed, amp, blur):
    rng = np.random.default_rng(seed)
    n = rng.uniform(-1, 1, (S, S))
    for _ in range(blur):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5
    return n / max(1e-6, np.abs(n).max()) * amp


def opaque(img):
    return Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8), "RGB")


def rgba(img, alpha):
    a = np.clip(np.round(alpha), 0, 255).astype(np.uint8)
    out = np.dstack([np.clip(np.round(img), 0, 255).astype(np.uint8), a])
    out[a == 0, :3] = 0
    return Image.fromarray(out, "RGBA")


def disc(cx, cy, rx, ry=None):
    ry = rx if ry is None else ry
    return ((XS + 0.5 - cx) / rx) ** 2 + ((YS + 0.5 - cy) / ry) ** 2 <= 1


def box(x0, y0, x1, y1):
    return (XS >= x0) & (XS <= x1) & (YS >= y0) & (YS <= y1)


def shade_box(img, a, m, col, top=1.15, bottom=0.7, left=1.08, right=0.8):
    img[m] = col
    a[m] = 255
    up = m & ~np.roll(m, 1, 0)
    dn = m & ~np.roll(m, -1, 0)
    lf = m & ~np.roll(m, 1, 1)
    rt = m & ~np.roll(m, -1, 1)
    img[up] *= top
    img[lf] *= left
    img[rt] *= right
    img[dn] *= bottom


def shadow(a, img, m, k=0.45):
    """A soft shadow on the ground (see-through black) where nothing is drawn yet."""
    free = m & (a == 0)
    img[free] = 0
    a[free] = int(255 * k)


# ================================================================================================= ground
def ash():
    img = np.zeros((S, S, 3))
    img[:] = (112, 106, 100)
    img += (noise(31, 12, 3) + noise(32, 5, 0))[:, :, None]
    rng = random.Random(33)
    for _ in range(26):                                  # flecks of char
        x, y = rng.randrange(S), rng.randrange(S)
        img[y, x] *= 0.55
    for _ in range(3):                                   # the odd ember
        x, y = rng.randrange(S), rng.randrange(S)
        img[y, x] = (214, 104, 40)
    return opaque(img)


def cinder():
    img = np.zeros((S, S, 3))
    img[:] = (64, 58, 60)
    img += (noise(41, 9, 2) + noise(42, 4, 0))[:, :, None]
    rng = random.Random(43)
    cracks = np.zeros((S, S), bool)
    for _ in range(5):                                   # plates of cooled rock, cracked apart
        x, y = rng.uniform(0, S), rng.uniform(0, S)
        ang = rng.uniform(0, math.pi)
        for t in range(rng.randrange(8, 18)):
            ang += rng.uniform(-0.6, 0.6)
            x, y = (x + math.cos(ang)) % S, (y + math.sin(ang)) % S
            cracks[int(y), int(x)] = True
    img[cracks] = img[cracks] * 0.45 + np.array((120, 40, 20)) * 0.35
    img[np.roll(cracks, 1, 0) & ~cracks] *= 1.12
    return opaque(img)


def lava():
    img = np.zeros((S, S, 3))
    heat = (noise(51, 1, 3) + 1) / 2                    # 0 crust .. 1 molten
    hot = np.clip((heat - 0.35) / 0.65, 0, 1)
    img[..., 0] = 120 + 135 * hot
    img[..., 1] = 30 + 170 * hot ** 1.6
    img[..., 2] = 10 + 60 * hot ** 3
    crust = heat < 0.38
    img[crust] = np.array((52, 40, 38)) + noise(52, 8, 1)[crust][:, None]
    rim = crust & ~np.roll(crust, 1, 0)
    img[rim] = (150, 60, 26)
    return opaque(img)


# ================================================================================================= decor
def dead_tree(variant):
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, disc(17, 29, 10, 3))
    bark = np.array((48, 40, 36))
    trunk = box(14, 12, 18, 29)
    shade_box(img, a, trunk, bark, top=1.0, bottom=0.8, left=1.3, right=0.6)
    rng = random.Random(60 + variant)
    branches = [(16, 14, -1, -1.2, 9), (17, 12, 1, -1.1, 9), (15, 18, -1, -0.5, 7), (18, 17, 1, -0.6, 7)]
    if variant == 2:
        branches = [(16, 13, -1, -0.9, 10), (17, 15, 1, -1.3, 8), (16, 19, 1, -0.4, 6)]
    for x, y, dx, dy, n in branches:
        for i in range(n):
            x += dx * rng.uniform(0.7, 1.2)
            y += dy * rng.uniform(0.6, 1.1)
            xi, yi = int(round(x)), int(round(y))
            for w in (0, 1) if i < n // 2 else (0,):
                if 0 <= xi + w < S and 0 <= yi < S:
                    img[yi, xi + w] = bark * (1.25 if w == 0 else 0.8)
                    a[yi, xi + w] = 255
            if i == n - 3 and rng.random() < 0.7:        # a twig off it
                tx, ty = xi, yi
                for _ in range(3):
                    tx += -dx
                    ty -= 1
                    if 0 <= tx < S and 0 <= ty < S:
                        img[ty, tx] = bark
                        a[ty, tx] = 255
    img[box(15, 22, 16, 23)] = (190, 80, 30)             # a last ember in the bark
    return rgba(img, a)


def basalt_rock():
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, disc(18, 26, 12, 4))
    body = disc(16, 18, 11, 9) & ~(box(0, 0, 9, 11) & disc(5, 5, 9))
    shade_box(img, a, body, np.array((70, 64, 70)))
    facets = body & (XS + YS > 34)
    img[facets] *= 0.78
    img[body & (np.abs(XS - YS + 2) < 1)] *= 1.3
    return rgba(img, a)


def ember_vent():
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    glow = disc(16, 17, 12, 8)
    d = np.sqrt(((XS + 0.5 - 16) / 12) ** 2 + ((YS + 0.5 - 17) / 8) ** 2)
    a[glow] = (np.clip(1 - d, 0, 1) * 150)[glow]
    img[glow] = (255, 150, 60)
    crack = (np.abs(YS - 17 - 3 * np.sin(XS / 3.0)) <= 1) & box(5, 10, 27, 24)
    img[crack] = (255, 214, 120)
    a[crack] = 255
    lips = (np.roll(crack, 1, 0) | np.roll(crack, -1, 0)) & ~crack & box(4, 8, 28, 26)
    img[lips] = (40, 32, 30)
    a[lips] = 255
    return rgba(img, a)


def cult_shrine():
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, disc(17, 28, 13, 4))
    shade_box(img, a, box(6, 14, 25, 28), np.array((34, 28, 34)), top=1.5)            # the altar block
    shade_box(img, a, box(4, 11, 27, 14), np.array((48, 40, 48)), top=1.4)            # its top slab
    hand = (disc(15.5, 21, 3.2, 3.2) | box(12, 16, 13, 19) | box(14, 15, 15, 18) | box(16, 15, 17, 18) |
            box(18, 16, 19, 19))
    img[hand & box(6, 15, 25, 27)] = (150, 26, 22)                                    # the burnt red hand
    for cx in (8, 23):                                                                 # black candles, lit
        shade_box(img, a, box(cx - 1, 5, cx + 1, 11), np.array((30, 26, 30)))
        img[box(cx, 2, cx, 4)] = (255, 190, 80)
        a[box(cx, 2, cx, 4)] = 255
        img[box(cx, 3, cx, 3)] = (255, 240, 180)
    return rgba(img, a)


MARBLE = np.array((232, 228, 220))
GILT = np.array((214, 172, 60))


def bank_column():
    """A white column for a bank's front: drawn over the wall, the wall showing either side."""
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shade_box(img, a, box(9, 4, 22, 27), MARBLE * 0.98, top=1.0, bottom=0.9, left=1.05, right=0.8)
    for x in (12, 16, 20):                                  # the fluting
        img[box(x, 6, x, 25)] *= 0.82
    shade_box(img, a, box(7, 0, 24, 3), MARBLE, bottom=0.75)  # the capital
    img[box(7, 0, 24, 0)] = GILT
    shade_box(img, a, box(7, 28, 24, 31), MARBLE * 0.95, top=1.1, bottom=0.6)   # the base
    return rgba(img, a)


def bank_plaque():
    """A gilt plaque with a gold coin: over a bank's sign (or its wall)."""
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shade_box(img, a, box(3, 6, 28, 25), GILT, top=1.25, bottom=0.6, left=1.15, right=0.7)
    shade_box(img, a, box(5, 8, 26, 23), np.array((40, 52, 64)), top=0.7, bottom=1.2, left=0.8, right=1.1)
    coin = disc(16, 15.5, 6)
    img[coin] = GILT * 1.12
    img[coin & ~disc(16, 15.5, 4.6)] = GILT * 0.75
    img[box(15, 12, 16, 19) & coin] = GILT * 0.6                    # the coin's mark
    img[box(13, 12, 18, 12) & coin] = GILT * 0.6
    img[box(13, 19, 18, 19) & coin] = GILT * 0.6
    for x in (5, 26):                                              # the bolts
        img[box(x, 8, x, 8)] = (250, 230, 150)
        img[box(x, 23, x, 23)] = (250, 230, 150)
    return rgba(img, a)


def bank_counter():
    """A bank's stall: a marble counter with a stack of coins and a ledger."""
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, box(3, 27, 31, 31))
    shade_box(img, a, box(2, 15, 29, 28), MARBLE * 0.92, top=1.05, bottom=0.65)        # the front
    for x in (8, 16, 24):
        img[box(x, 17, x + 1, 26)] *= 0.85                                            # panels
    shade_box(img, a, box(0, 11, 31, 15), MARBLE, top=1.1, bottom=0.7)                 # the top
    img[box(0, 15, 31, 15)] = GILT * 0.8
    for k, (cx, h) in enumerate(((7, 4), (10, 6), (13, 3))):                           # coins, stacked
        for i in range(h):
            img[box(cx - 2, 10 - i, cx + 1, 10 - i)] = GILT * (1.15 if i == h - 1 else 0.85 + 0.05 * (i % 2))
            a[box(cx - 2, 10 - i, cx + 1, 10 - i)] = 255
    shade_box(img, a, box(19, 7, 27, 11), np.array((120, 36, 30)))                   # the ledger
    img[box(20, 8, 26, 10)] = (232, 222, 196)
    img[box(23, 8, 23, 10)] = (150, 130, 100)
    return rgba(img, a)


def hero_statue():
    """A gilt statue of the dragon-slayer on a plinth, sword raised."""
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, disc(17, 29, 12, 3))
    shade_box(img, a, box(6, 23, 25, 30), np.array((176, 170, 160)), top=1.2, bottom=0.6)       # plinth
    img[box(6, 26, 25, 26)] *= 0.82
    gold = GILT
    shade_box(img, a, box(13, 13, 18, 22), gold)                     # body and legs
    img[box(15, 18, 16, 22)] *= 0.7
    shade_box(img, a, disc(15.5, 10, 2.6, 2.8), gold * 1.1)           # head
    shade_box(img, a, box(10, 13, 12, 16), gold * 0.9)                # shield arm
    shade_box(img, a, disc(9.5, 16, 3.2, 3.8), gold * 0.95)           # the shield
    img[box(9, 14, 10, 18)] *= 0.75
    shade_box(img, a, box(19, 9, 20, 14), gold)                       # sword arm, raised
    shade_box(img, a, box(20, 1, 21, 9), np.array((236, 232, 220)))   # the blade
    img[box(18, 9, 23, 9)] = gold * 0.8                               # the crossguard
    a[box(18, 9, 23, 9)] = 255
    return rgba(img, a)


def dragon_skull():
    """Ignaroth's skull, mounted on a black plinth: horns, a long snout, empty sockets."""
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    shadow(a, img, disc(16, 29, 14, 3))
    shade_box(img, a, box(7, 25, 24, 30), np.array((40, 34, 38)), top=1.4, bottom=0.6)
    bone = np.array((222, 212, 188))
    skull = disc(16, 15, 9, 7.5) | box(11, 16, 21, 24)
    shade_box(img, a, skull, bone, top=1.05, bottom=0.75)
    img[disc(12.5, 14, 2.2, 1.8)] = (30, 20, 20)                      # sockets, a faint red glow in one
    img[disc(19.5, 14, 2.2, 1.8)] = (30, 20, 20)
    img[box(19, 14, 20, 14)] = (180, 40, 30)
    img[box(14, 19, 14, 20)] = (60, 50, 44)                           # nostrils
    img[box(18, 19, 18, 20)] = (60, 50, 44)
    for x in range(12, 21, 2):                                        # teeth
        img[box(x, 23, x, 24)] = (250, 246, 230)
    for side in (-1, 1):                                              # the horns, sweeping back and up
        x, y = 16 + side * 7, 9
        for i in range(9):
            xi, yi = int(round(x)), int(round(y))
            for w in (0, side):
                if 0 <= xi + w < S and 0 <= yi < S:
                    img[yi, xi + w] = bone * (0.95 - 0.04 * i)
                    a[yi, xi + w] = 255
            x += side * 0.8
            y -= 0.95
    return rgba(img, a)


TILE_ART = {"Ash001": ash, "Cinder001": cinder, "Lava001": lava,
            "Dead_Tree001": lambda: dead_tree(1), "Dead_Tree002": lambda: dead_tree(2),
            "Basalt_Rock001": basalt_rock, "Ember_Vent001": ember_vent, "Cult_Shrine001": cult_shrine,
            "Bank_Column001": bank_column, "Bank_Plaque001": bank_plaque, "Bank_Counter001": bank_counter,
            "Hero_Statue001": hero_statue, "Dragon_Skull001": dragon_skull}
TILE_ART.update(__import__("fence_tiles").TILE_ART)     # the wooden and iron fences


# ================================================================================================= recolours
def hsv_map(fn):
    def apply(c):
        r, g, b = (v / 255 for v in c[:3])
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        out = fn(h, s, v)
        if out is None:
            return c
        r, g, b = colorsys.hsv_to_rgb(*out)
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255))) + tuple(c[3:])
    return apply


def warden(h, s, v):
    if 0.55 < h < 0.75 and s > 0.25:                     # the blue cape and trim: ember red
        return 0.01, min(1, s * 1.1), v * 0.95
    return None


def scout(h, s, v):
    if 0.18 < h < 0.48 and s > 0.15:                     # the green cloak: ash grey, a little warm
        return 0.07, s * 0.25, v * 0.85
    return None


def cultist(h, s, v):
    if s < 0.2 and 0.18 < v < 0.85:                      # the grey robe: charcoal
        return 0.95, 0.12, v * 0.48
    return None


def priest(h, s, v):
    if s < 0.2 and 0.18 < v < 0.85:                      # the grey robe: crimson
        return 0.985, 0.72, min(1, v * 0.85)
    return None


def hound(h, s, v):
    if s < 0.25 and v > 0.78:                            # the light fur: embers
        return 0.06, 0.85, 1.0
    if s < 0.25:                                         # the rest: charcoal
        return h, s, v * 0.45
    if 0.1 < h < 0.2:                                    # the yellow eyes: red
        return 0.0, 1.0, 1.0
    return None


def wyrmsmith(h, s, v):
    if 0.03 < h < 0.12 and s > 0.3 and v < 0.6:          # the leather apron: dark red dragon-hide
        return 0.99, min(1, s * 1.2), v * 0.85
    return None


def dragonforge(h, s, v):
    if s < 0.2:                                          # the grey stone: black obsidian with a purple sheen
        return 0.8, 0.18, v * 0.42
    return None


def dragonscale(h, s, v):
    if 0.38 < h < 0.62 and s > 0.15:                     # mithril blue-green: crimson
        return 0.995, min(1, s * 1.25 + 0.1), v * 0.88
    if s < 0.12 and v > 0.85:                            # the white trim: gold
        return 0.12, 0.7, v * 0.9
    return None


def codex(h, s, v):
    if 0.2 < h < 0.45 and s > 0.1:                       # the green cover: black, red trim where it was light
        return (0.0, 0.8, 0.6) if v > 0.7 else (0.9, 0.1, v * 0.25)
    return None


def tag(h, s, v):
    return 0.6, 0.06, min(1, v * 2.4 + 0.15)              # the dark disc: dented steel


def scale(h, s, v):
    return 0.02, min(1, s * 1.1), min(1, v * 1.25)        # a ruby: a red-gold dragon scale


ENTITY_ART = [   # (source, new, recolour, walking frames too)
    ("Captain", "Warden", warden, True),
    ("Ranger", "Scout", scout, True),
    ("Ashen_Acolyte", "Ashen_Cultist", cultist, True),
    ("Ashen_Acolyte", "Ashen_Priest", priest, True),
    ("Wolf", "Ember_Hound", hound, True),
    ("Forgemaster", "Wyrmsmith", wyrmsmith, True),
    ("Furnace", "Dragonforge", dragonforge, False),
    ("Mithril_Helm", "Dragonscale_Helm", dragonscale, False),
    ("Mithril_Platebody", "Dragonscale_Platebody", dragonscale, False),
    ("Mithril_Platelegs", "Dragonscale_Platelegs", dragonscale, False),
    ("Mithril_Shield", "Dragonscale_Shield", dragonscale, False),
    ("Mithril_Boots", "Dragonscale_Boots", dragonscale, False),
    ("Hobs_Diary", "Ashen_Codex", codex, False),
    ("Ashen_Sigil", "Scout_Tag", tag, False),
    ("Ruby", "Dragon_Scale", scale, False),
]


def recolour_file(src, dst, fn):
    im = Image.open(src).convert("RGBA")
    m = hsv_map(fn)
    px = [c if c[3] == 0 else m(c) for c in im.getdata()]
    out = Image.new("RGBA", im.size)
    out.putdata(px)
    return write_image(dst, out)


def make_art():
    """Writes the tiles and the recoloured entities (only what changed). Returns what it wrote."""
    made = []
    for name, fn in TILE_ART.items():
        if write_image(p("sprites", "Tiles", name + ".png"), fn()):
            made.append("sprites\\Tiles\\%s.png" % name)
    for src, dst, fn, walking in ENTITY_ART:
        jobs = [("Entities", src, dst)]
        if walking:
            for d in "1248":
                for f in "abc":
                    if os.path.exists(p("sprites", "Walk", src + d + f + ".png")):
                        jobs.append(("Walk", src + d + f, dst + d + f))
        for kind, a, b in jobs:
            if recolour_file(p("sprites", kind, a + ".png"), p("sprites", kind, b + ".png"), fn):
                made.append("sprites\\%s\\%s.png" % (kind, b))
    return made


def preview(path):
    tiles = [TILE_ART[n]().convert("RGBA") for n in TILE_ART]
    ents = []
    for src, dst, fn, _ in ENTITY_ART:
        im = Image.open(p("sprites", "Entities", src + ".png")).convert("RGBA")
        m = hsv_map(fn)
        out = Image.new("RGBA", im.size)
        out.putdata([c if c[3] == 0 else m(c) for c in im.getdata()])
        ents.append(out)
    w = max(len(tiles), len(ents)) * 36
    sheet = Image.new("RGBA", (w, 76), (90, 110, 70, 255))
    for i, t in enumerate(tiles):
        sheet.alpha_composite(t, (i * 36, 2))
    for i, e in enumerate(ents):
        sheet.alpha_composite(e, (i * 36, 40))
    sheet.resize((w * 3, 76 * 3), Image.NEAREST).save(path)


if __name__ == "__main__":
    import sys
    preview(sys.argv[1])
