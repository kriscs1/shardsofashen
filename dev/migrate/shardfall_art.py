"""The Shardfall Deep's pictures and sounds (build_shardfall.py draws them all through draw_all): its grounds, painted from
big seamless textures (fused glass, crystal-veined stone, fungal loam, chalk, wet shingle, the brine and the glowing Shard
pools, which move), its walls' faces (crystal, wet, fungal, chalk, and the Wardens' dressed stone), what stands about in it
(crystals, lantern caps, the leviathan's bones, the Wardens' statues, braziers and tombs), the Fallen Shard and the Singing
Geode, its creatures (the base kinds' pictures recoloured, crystals grown out of the shard-touched ones), and its gear.

Nothing here runs on its own.
"""
import glob
import math
import os
import random
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import p, write_image                                    # noqa: E402
from build_ground_textures import soft, stretch, steps, specks      # noqa: E402
from build_terrain import ramp, save_texture, cell_of               # noqa: E402

SIZE = 256
POOL_FRAMES = 6
POOL_SPEED = 300
OUTLINE = (26, 18, 30, 255)

VIOLET = [(0.0, (34, 20, 54)), (0.35, (70, 44, 120)), (0.6, (128, 92, 214)), (0.82, (176, 150, 250)), (1.0, (232, 222, 255))]


# ================================================================== helpers
def rgba(w=32, h=32):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def outlined(im, col=OUTLINE):
    """A 1 px dark outline round what's drawn (the mask-silhouette method)."""
    a = np.array(im.getchannel("A")) > 0
    ring = np.zeros_like(a)
    ring[1:, :] |= a[:-1, :]
    ring[:-1, :] |= a[1:, :]
    ring[:, 1:] |= a[:, :-1]
    ring[:, :-1] |= a[:, 1:]
    ring &= ~a
    out = np.array(im)
    out[ring] = col
    return Image.fromarray(out, "RGBA")


def tint(im, col, keep_dark=42, gain=150.0):
    """A picture in another colour, as light and dark as it was; its dark outline stays (build_zones.tint)."""
    a = np.array(im.convert("RGBA"), dtype=np.float32)
    lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
    k = np.clip(lum / gain, 0, 1.45)[..., None]
    out = np.array(col, dtype=np.float32)[None, None, :] * k
    rgb = np.where((lum < keep_dark)[..., None], a[..., :3], out)
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def crystal(d, x, y, h, w, col, lean=0):
    """A crystal standing at x, y (its foot), h tall: a light face, a dark face and a pale heart."""
    light = tuple(min(255, int(c * 1.25 + 30)) for c in col)
    dark = tuple(int(c * 0.6) for c in col)
    tip = (x + lean, y - h)
    d.polygon([(x - w, y), (x, y), tip], fill=light + (255,))
    d.polygon([(x, y), (x + w, y), tip], fill=dark + (255,))
    d.line([(x - max(1, w // 2), y - 1), tip], fill=(236, 230, 255, 255))


def spikes(im, col, seed, n=3):
    """Crystals grown out of a creature's back and shoulders (the shard-touched ones)."""
    a = np.array(im.getchannel("A")) > 0
    h, w = a.shape
    tops = [(x, int(np.argmax(a[:, x]))) for x in range(w) if a[:, x].any()]
    if not tops:
        return im
    rng = random.Random(seed)
    tops.sort(key=lambda t: t[1])
    picks = sorted(rng.sample(tops[:max(n, len(tops) // 2)], min(n, len(tops))))
    out = im.copy()
    d = ImageDraw.Draw(out)
    for x, y in picks:
        crystal(d, x, y + 2, rng.randint(3, 5), 1 + rng.randint(0, 1), col, rng.choice((-1, 0, 1)))
    return outlined(out)


def scaled(im, k):
    """As big again by k, on the same ground line (a boss over its kind)."""
    w, h = im.size
    big = im.resize((int(w * k), int(h * k)), Image.NEAREST)
    return big


def save(kind, name, im):
    return write_image(p("sprites", kind, name + ".png"), im)


def save_tile(name, arr):
    return write_image(p("sprites", "Tiles", name + ".png"), Image.fromarray(np.array(cell_of(arr, 0), dtype=np.uint8), "RGB"))


# ================================================================== the grounds (textures)
def ridges(rng, size, beta):
    return 1 - np.abs(2 * soft(rng, size, beta) - 1)


def shardglass(seed=401):
    """The Shardfall's floor: fused violet glass in plates, cracks of light between them."""
    rng = random.Random(seed)
    plates = stretch(0.7 * soft(rng, SIZE, 1.9) + 0.3 * soft(rng, SIZE, 0.8, low=0.06))
    cracks = stretch(ridges(rng, SIZE, 2.2)) ** 40
    v = np.clip(0.1 + 0.42 * plates + 0.38 * cracks + 0.06 * specks(rng, (SIZE, SIZE), SIZE * SIZE // 120, 1), 0, 1)
    return ramp(steps(v, 9), [(0.0, (30, 20, 48)), (0.3, (52, 34, 86)), (0.55, (78, 54, 128)), (0.8, (120, 92, 190)),
                              (1.0, (170, 146, 240))])


def gallery_stone(seed=402):
    """The Galleries' floor: blue-grey cave stone, a thin violet vein now and then, glints."""
    rng = random.Random(seed)
    base = stretch(0.6 * soft(rng, SIZE, 1.7) + 0.4 * soft(rng, SIZE, 0.7, low=0.08))
    v = ramp(steps(base, 6), [(0.0, (54, 52, 66)), (0.5, (72, 70, 86)), (1.0, (94, 92, 108))])
    vein = stretch(ridges(rng, SIZE, 2.2)) ** 14
    glow = ramp(vein, [(0.0, (0, 0, 0)), (0.5, (110, 70, 190)), (1.0, (196, 170, 255))])
    v = np.where((vein > 0.35)[..., None], glow, v)
    g = specks(rng, (SIZE, SIZE), SIZE * SIZE // 260, 1) > 0
    v[g] = (170, 196, 240)
    return v


def spore_loam(seed=403):
    """The Lantern Wood's floor: dark loam, pale threads of mycelium through it, a glowing speck here and there."""
    rng = random.Random(seed)
    base = stretch(0.7 * soft(rng, SIZE, 1.6) + 0.3 * soft(rng, SIZE, 0.6, low=0.1))
    v = ramp(steps(base, 6), [(0.0, (38, 30, 36)), (0.5, (52, 40, 46)), (1.0, (68, 54, 58))])
    threads = stretch(ridges(rng, SIZE, 1.8)) ** 30
    v = v * (1 - 0.3 * threads[..., None]) + np.array((150, 142, 128)) * 0.3 * threads[..., None]
    g = specks(rng, (SIZE, SIZE), SIZE * SIZE // 320, 1) > 0
    v[g] = (110, 230, 200)
    return v


def chalk(seed=404):
    """Leviathan's Rest: pale chalk, a darker drift through it, little shells pressed in it."""
    rng = random.Random(seed)
    base = stretch(0.6 * soft(rng, SIZE, 1.8) + 0.4 * soft(rng, SIZE, 0.6, low=0.08))
    v = ramp(steps(base, 6), [(0.0, (142, 136, 122)), (0.5, (164, 158, 142)), (1.0, (184, 178, 162))])
    s = specks(rng, (SIZE, SIZE), SIZE * SIZE // 140, 2)
    v[s > 0] = (204, 198, 184)
    v[s < 0] = (120, 112, 100)
    return v


def shingle(seed=405):
    """The Brinewater's shore: wet dark shingle."""
    rng = random.Random(seed)
    base = stretch(0.5 * soft(rng, SIZE, 1.5) + 0.5 * soft(rng, SIZE, 0.4, low=0.15))
    v = ramp(steps(base, 7), [(0.0, (44, 50, 54)), (0.5, (64, 70, 72)), (1.0, (92, 98, 98))])
    s = specks(rng, (SIZE, SIZE), SIZE * SIZE // 30, 1)
    v[s > 0] = (110, 116, 112)
    return v


def brine(seed=406):
    """The underground sea: deep teal, slow swells, motes of light in it."""
    rng = random.Random(seed)
    deep = stretch(soft(rng, SIZE, 1.8))
    warp = soft(rng, SIZE, 1.9)
    ys = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    swell = np.sin((ys * 8 / SIZE + warp * 3.0) * 2 * math.pi) * 0.5 + 0.5
    v = stretch(0.6 * deep + 0.4 * swell)
    out = ramp(steps(v, 6), [(0.0, (8, 30, 40)), (0.5, (14, 46, 58)), (1.0, (24, 66, 78))])
    g = specks(rng, (SIZE, SIZE), SIZE * SIZE // 400, 1) > 0
    out[g] = (90, 200, 190)
    return out


def shard_pool_frames(seed=407):
    """A pool of liquid Shard light: swirls of violet fading into each other and back, so the frames loop."""
    rng = random.Random(seed)
    n = 128
    fields = [ridges(rng, n, 2.0) for _ in range(3)]
    out = []
    for f in range(POOL_FRAMES):
        t = f / POOL_FRAMES * 2 * math.pi
        w = [0.5 + 0.5 * math.cos(t + k * 2 * math.pi / 3) for k in range(3)]
        mix = sum(a * b for a, b in zip(w, fields)) / sum(w)
        v = np.clip(0.3 + 0.7 * stretch(mix) ** 1.6, 0, 1)
        out.append(ramp(steps(v, 10), [(0.0, (110, 70, 200)), (0.4, (160, 120, 250)), (0.75, (206, 186, 255)),
                                       (1.0, (250, 246, 255))]))
    return out


def warden_flags(seed=408):
    """The Wardens' floor: pale blue-grey flagstones of different sizes, laid in courses, mortar between."""
    rng = random.Random(seed)
    v = np.zeros((SIZE, SIZE, 3))
    grain = stretch(soft(rng, SIZE, 0.9, low=0.05))
    y = 0
    while y < SIZE:
        h = 16 if SIZE - y < 40 else rng.choice((16, 20, 24))
        h = min(h, SIZE - y)
        x = rng.randrange(0, 24)
        first = x
        while x < first + SIZE:
            w = rng.choice((20, 24, 28, 32, 40))
            w = min(w, first + SIZE - x)
            shade = rng.uniform(-10, 10)
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    edge = yy == y or xx == x
                    c = (66, 68, 78) if edge else tuple(b + shade + 14 * (grain[yy, xx % SIZE] - 0.5) for b in (118, 124, 136))
                    v[yy, xx % SIZE] = c
            x += w
        y += h
    return np.clip(v, 0, 255)


GROUNDS = {   # tile: (texture, its picture's maker, Examine.Info)
    "Shardglass001": ("Shardglass", shardglass, "Glass, fused out of the rock by something that fell burning. It hums."),
    "Gallery_Floor001": ("Gallery_Stone", gallery_stone, "Cave stone, veined with violet. The veins are warm."),
    "Spore_Loam001": ("Spore_Loam", spore_loam, "Soft dark loam, threaded through with something pale and living."),
    "Chalk_Floor001": ("Chalk", chalk, "Chalk, full of little shells. This was a sea floor once, long before the sea."),
    "Deep_Shingle001": ("Deep_Shingle", shingle, "Wet black shingle. The lake laps at it, very quietly."),
    "Brine001": ("Brine", brine, "Black water, salt and very cold. Lights drift in it, a long way down."),
    "Warden_Flag001": ("Warden_Flags", warden_flags, "Flagstones, laid by careful hands, worn by careful feet."),
}


def grounds():
    made = 0
    for tile, (tex, maker, _) in GROUNDS.items():
        arr = maker().astype(np.uint8)
        save_texture(tex, arr)
        made += save_tile(tile, arr)
    frames = shard_pool_frames()
    for f, arr in enumerate(frames):
        save_texture("Shard_Pool_%d" % f, arr.astype(np.uint8))
    save_texture("Shard_Pool", frames[0].astype(np.uint8))
    made += save_tile("Shard_Pool001", frames[0].astype(np.uint8))
    return made


# ================================================================== walls
def base_wall():
    return Image.open(p("sprites", "Tiles", "Cave_Wall002.png")).convert("RGBA")


def recolour(im, stops):
    a = np.array(im, dtype=np.float32)
    lum = (a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11) / 255
    out = ramp(np.clip(lum * 1.4, 0, 1), stops)
    a[..., :3] = out
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def crystal_face(seed):
    im = recolour(base_wall(), [(0.0, (22, 18, 30)), (0.5, (62, 58, 78)), (1.0, (120, 116, 140))])
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(rng.randint(2, 3)):
        x, y = rng.randint(5, 26), rng.randint(16, 30)
        col = rng.choice(((150, 100, 240), (110, 190, 240), (190, 140, 250)))
        for k in range(rng.randint(2, 3)):
            crystal(d, x + k * 3 - 3, y, rng.randint(5, 10), 2, col, rng.choice((-2, -1, 1, 2)))
    return im


def wet_face(seed):
    im = recolour(base_wall(), [(0.0, (12, 20, 22)), (0.5, (42, 56, 58)), (1.0, (90, 110, 108))])
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(5):                                       # (drips running down it)
        x, y = rng.randint(2, 29), rng.randint(0, 12)
        d.line([(x, y), (x, y + rng.randint(6, 16))], fill=(70, 120, 120, 255))
    for x in range(0, 32, 2):                                # (weed along its foot)
        h = rng.randint(2, 6)
        d.line([(x, 31), (x + rng.choice((-1, 0, 1)), 31 - h)], fill=(40, 90, 60, 255))
    return im


def fungal_face(seed):
    im = recolour(base_wall(), [(0.0, (24, 18, 22)), (0.5, (58, 46, 52)), (1.0, (110, 96, 100))])
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(rng.randint(2, 4)):                       # (shelf fungi, their rims glowing)
        x, y, w = rng.randint(3, 22), rng.randint(8, 26), rng.randint(5, 8)
        d.chord([x, y - 3, x + w, y + 3], 180, 360, fill=(150, 120, 90, 255))
        d.line([(x + 1, y), (x + w - 1, y)], fill=(120, 240, 210, 255))
    return im


def chalk_face(seed):
    im = recolour(base_wall(), [(0.0, (70, 66, 58)), (0.5, (140, 134, 120)), (1.0, (200, 194, 178))])
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    x, y = rng.randint(8, 22), rng.randint(10, 22)           # (an ammonite in the chalk)
    for t in range(0, 40):
        a = t * 0.45
        r = 0.18 * t
        d.point((x + r * math.cos(a), y + r * math.sin(a)), fill=(96, 88, 76, 255))
    return im


def warden_wall_top():
    """The Wardens' wall seen from above: dressed capstones, dark."""
    im = Image.new("RGBA", (32, 32), (40, 42, 52, 255))
    d = ImageDraw.Draw(im)
    for y in (0, 16):
        d.line([(0, y), (31, y)], fill=(28, 28, 36, 255))
        off = 0 if y == 0 else 8
        for x in range(off, 32, 16):
            d.line([(x, y), (x, y + 15)], fill=(28, 28, 36, 255))
    for x in range(1, 31, 3):
        d.point((x, 1 + (x * 7) % 13), fill=(52, 54, 66, 255))
    return im


def warden_wall_face(rune=False):
    """The Wardens' wall's face: courses of pale ashlar, a carved band, a glass rune glowing in one."""
    im = Image.new("RGBA", (32, 32), (96, 102, 116, 255))
    d = ImageDraw.Draw(im)
    rng = random.Random(77 if not rune else 78)
    for y0 in range(0, 32, 8):
        d.line([(0, y0), (31, y0)], fill=(54, 56, 66, 255))
        off = 0 if (y0 // 8) % 2 == 0 else 8
        for x in range(off, 33, 16):
            d.line([(x, y0), (x, y0 + 7)], fill=(54, 56, 66, 255))
        for _ in range(6):
            d.point((rng.randint(0, 31), y0 + rng.randint(1, 6)), fill=(112, 118, 132, 255))
    d.rectangle([0, 0, 31, 2], fill=(70, 74, 86, 255))       # (the top course in shadow)
    d.rectangle([0, 29, 31, 31], fill=(62, 64, 74, 255))     # (its foot)
    if rune:
        d.rectangle([11, 10, 20, 21], fill=(60, 62, 74, 255))
        for a, b in (((15, 11), (15, 20)), ((12, 14), (19, 14)), ((13, 18), (18, 12))):
            d.line([a, b], fill=(170, 150, 250, 255))
    return im


def seal_door(open_=False):
    """The Wardens' Seal: a slab of black glass in a stone frame, runes round it, a hollow for a signet in its middle;
    open, a dark way through."""
    im = warden_wall_face()
    d = ImageDraw.Draw(im)
    d.rectangle([5, 3, 26, 31], fill=(70, 74, 88, 255))
    if open_:
        d.rectangle([8, 6, 23, 31], fill=(14, 12, 20, 255))
        d.line([(8, 6), (23, 6)], fill=(40, 36, 54, 255))
        return im
    d.rectangle([8, 6, 23, 31], fill=(20, 14, 34, 255))
    for y in range(8, 30, 3):
        d.point((9, y), fill=(140, 110, 230, 255))
        d.point((22, y + 1), fill=(140, 110, 230, 255))
    d.line([(10, 7), (21, 7)], fill=(60, 40, 100, 255))
    d.ellipse([13, 15, 18, 20], outline=(190, 170, 255, 255))
    d.point((15, 13), fill=(220, 210, 255, 255))
    return im


def iron_door(open_=False):
    im = warden_wall_face()
    d = ImageDraw.Draw(im)
    d.rectangle([6, 4, 25, 31], fill=(70, 74, 88, 255))
    if open_:
        d.rectangle([9, 7, 22, 31], fill=(16, 14, 20, 255))
        d.rectangle([20, 7, 22, 31], fill=(52, 50, 56, 255))
        return im
    d.rectangle([9, 7, 22, 31], fill=(58, 56, 62, 255))
    for y in (11, 20, 28):
        d.line([(9, y), (22, y)], fill=(34, 32, 38, 255))
    for x, y in ((11, 11), (20, 11), (11, 20), (20, 20)):
        d.point((x, y), fill=(120, 116, 120, 255))
    d.ellipse([17, 15, 20, 18], fill=(150, 130, 230, 255))  # (the Wardens' seal on its lock)
    return im


def sea_cave():
    """Gull Point's sea cave: the mountain's cave mouth, wrack and foam at its foot."""
    im = Image.open(p("sprites", "Tiles", "Mire_Tunnel_Mouth001.png")).convert("RGBA")
    d = ImageDraw.Draw(im)
    rng = random.Random(9)
    for x in range(2, 30):
        if rng.random() < 0.6:
            d.point((x, 30 + rng.randint(0, 1)), fill=(220, 230, 230, 255))
        if rng.random() < 0.4:
            d.line([(x, 31), (x, 29 - rng.randint(0, 2))], fill=(54, 84, 52, 255))
    return im


def walls():
    made = 0
    for n, seed in ((1, 11), (2, 12), (3, 13)):
        made += save("Tiles", "Crystal_Face%03d" % n, crystal_face(seed))
    for n, seed in ((1, 21), (2, 22)):
        made += save("Tiles", "Wet_Face%03d" % n, wet_face(seed))
    for n, seed in ((1, 31), (2, 32)):
        made += save("Tiles", "Fungal_Face%03d" % n, fungal_face(seed))
    for n, seed in ((1, 41), (2, 42)):
        made += save("Tiles", "Chalk_Face%03d" % n, chalk_face(seed))
    top = Image.open(p("sprites", "Tiles", "Cave_Wall001.png")).convert("RGBA")   # (the rock behind each kind of face)
    made += save("Tiles", "Crystal_Rock001", recolour(top, [(0.0, (20, 16, 28)), (0.5, (54, 50, 68)), (1.0, (100, 96, 120))]))
    made += save("Tiles", "Wet_Rock001", recolour(top, [(0.0, (12, 18, 20)), (0.5, (40, 52, 54)), (1.0, (82, 100, 98))]))
    made += save("Tiles", "Fungal_Rock001", recolour(top, [(0.0, (22, 16, 20)), (0.5, (52, 42, 48)), (1.0, (100, 88, 92))]))
    made += save("Tiles", "Chalk_Rock001", recolour(top, [(0.0, (66, 62, 54)), (0.5, (126, 120, 106)), (1.0, (180, 174, 158))]))
    made += save("Tiles", "Warden_Wall001", warden_wall_top())
    made += save("Tiles", "Warden_Wall002", warden_wall_face())
    made += save("Tiles", "Warden_Wall003", warden_wall_face(rune=True))
    made += save("Tiles", "Warden_Seal001", seal_door())
    made += save("Tiles", "Warden_Seal002", seal_door(open_=True))
    made += save("Tiles", "Warden_Door001", iron_door())
    made += save("Tiles", "Warden_Door002", iron_door(open_=True))
    made += save("Tiles", "Gull_Cave001", sea_cave())
    return made


# ================================================================== what stands about
def crystals_decor(seed, cols, n, hmin, hmax, spread):
    im = rgba()
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    spots = sorted(((16 + rng.randint(-spread, spread), 26 + rng.randint(-2, 3)) for _ in range(n)), key=lambda s: s[1])
    for x, y in spots:
        crystal(d, x, y, rng.randint(hmin, hmax), rng.randint(2, 3), rng.choice(cols), rng.choice((-3, -1, 0, 1, 3)))
    for x in range(8, 25):                                   # (its light pooled at its foot)
        if x % 3 != 1:
            d.point((x, 29), fill=tuple(int(c * 0.55) for c in cols[0]) + (255,))
    return outlined(im)


def lantern_cap(seed, cap, gill):
    """A mushroom as tall as a person: a pale stalk, a wide cap, its gills glowing."""
    im = rgba()
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    sx = 16 + rng.randint(-2, 2)
    d.rectangle([sx - 2, 14, sx + 2, 30], fill=(206, 200, 184, 255))
    d.line([(sx - 2, 14), (sx - 2, 30)], fill=(232, 228, 214, 255))
    d.line([(sx + 2, 14), (sx + 2, 30)], fill=(160, 152, 138, 255))
    w = rng.randint(11, 14)
    d.pieslice([sx - w, 2, sx + w, 24], 180, 360, fill=cap + (255,))
    d.line([(sx - w + 1, 13), (sx + w - 1, 13)], fill=gill + (255,))
    d.line([(sx - w + 3, 14), (sx + w - 3, 14)], fill=tuple(int(c * 0.7) for c in gill) + (255,))
    for _ in range(5):                                       # (spots on the cap)
        a = rng.uniform(math.pi * 1.1, math.pi * 1.9)
        r = rng.uniform(0.4, 0.85) * w
        d.point((sx + r * math.cos(a), 13 + r * 0.9 * math.sin(a)), fill=(240, 236, 220, 255))
    return outlined(im)


def glow_moss():
    im = rgba()
    d = ImageDraw.Draw(im)
    rng = random.Random(55)
    for _ in range(26):
        x, y = rng.randint(6, 26), rng.randint(14, 28)
        d.point((x, y), fill=rng.choice(((80, 200, 170, 255), (120, 240, 210, 255), (50, 140, 110, 255))))
    return im


def kelp(seed):
    im = rgba()
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    for _ in range(4):
        x = rng.randint(8, 24)
        pts = [(x, 30)]
        for k in range(1, 5):
            pts.append((x + rng.choice((-1, 0, 1)) * k % 3 - 1, 30 - k * rng.randint(3, 4)))
        d.line(pts, fill=(44, 96, 66, 255), width=2)
        d.line(pts, fill=(70, 130, 84, 255), width=1)
    return outlined(im)


BONE, BONE_D, BONE_L = (214, 206, 186, 255), (150, 142, 124, 255), (236, 230, 214, 255)


def rib(part):
    """The leviathan's ribs, a ribcage five tiles tall round its spine: 1, an upper rib's tip curling over; 2, its foot
    rising from the spine; 3, a lower rib's foot; 4, its tip."""
    im = rgba()
    d = ImageDraw.Draw(im)
    if part == 1:
        pts = [(18, 31), (13, 22), (11, 13), (13, 6), (19, 3)]
    elif part == 2:
        pts = [(15, 31), (16, 22), (19, 12), (18, 0)]
    elif part == 3:
        pts = [(18, 31), (19, 20), (16, 10), (15, 0)]
    else:
        pts = [(19, 0), (13, 9), (11, 18), (13, 25), (19, 28)]
    d.line(pts, fill=BONE_D, width=4)
    d.line(pts, fill=BONE, width=3)
    d.line([(x - 1, y) for x, y in pts], fill=BONE_L, width=1)
    return outlined(im)


def spine():
    im = rgba()
    d = ImageDraw.Draw(im)
    for x in range(0, 32, 8):
        d.rounded_rectangle([x + 1, 11, x + 7, 21], 2, fill=BONE)
        d.line([(x + 2, 12), (x + 6, 12)], fill=BONE_L)
        d.line([(x + 4, 6), (x + 4, 11)], fill=BONE_D, width=2)
    return outlined(im)


def skull_parts():
    """The leviathan's skull, 96 x 96: cut into nine tiles (a Whole set), left to right, top row first."""
    im = rgba(96, 96)
    d = ImageDraw.Draw(im)
    d.polygon([(2, 50), (16, 22), (52, 10), (84, 20), (95, 46), (88, 70), (54, 86), (16, 76)], fill=BONE)
    d.polygon([(6, 50), (20, 28), (52, 16), (80, 24), (90, 44)], fill=BONE_L)
    d.ellipse([56, 28, 76, 46], fill=(40, 34, 30, 255))       # (the eye)
    d.ellipse([61, 33, 69, 41], fill=(70, 160, 160, 255))     # (something glows in it)
    d.line([(4, 58), (70, 64)], fill=(70, 60, 50, 255), width=3)   # (the jaw's line)
    for x in range(8, 66, 6):                                  # (teeth, both jaws)
        d.polygon([(x, 57), (x + 3, 57), (x + 1, 66)], fill=BONE_L)
        d.polygon([(x + 2, 66), (x + 5, 66), (x + 3, 59)], fill=BONE_L)
    im = outlined(im)
    return [im.crop((x, y, x + 32, y + 32)) for y in (0, 32, 64) for x in (0, 32, 64)]


def warden_statue():
    """A Glass Warden in stone, cloaked, a shard held up that still glows."""
    im = rgba()
    d = ImageDraw.Draw(im)
    stone, dark, light = (150, 152, 160, 255), (104, 106, 116, 255), (190, 192, 200, 255)
    d.rectangle([9, 26, 23, 30], fill=dark)                    # (the plinth)
    d.polygon([(12, 26), (11, 12), (16, 9), (21, 12), (20, 26)], fill=stone)
    d.line([(12, 26), (11, 12)], fill=light)
    d.ellipse([13, 4, 19, 10], fill=stone)
    d.line([(20, 13), (24, 6)], fill=stone, width=2)          # (the arm raised)
    crystal(d, 24, 6, 5, 1, (150, 120, 250))
    return outlined(im)


def brazier():
    im = rgba()
    d = ImageDraw.Draw(im)
    d.rectangle([14, 20, 18, 29], fill=(90, 92, 102, 255))
    d.rectangle([11, 28, 21, 30], fill=(70, 72, 82, 255))
    d.chord([7, 12, 25, 24], 0, 180, fill=(110, 112, 124, 255))
    for x, h, c in ((12, 8, (120, 90, 230)), (16, 12, (180, 150, 255)), (20, 7, (120, 90, 230)), (14, 5, (230, 220, 255))):
        d.polygon([(x - 2, 18), (x + 2, 18), (x, 18 - h)], fill=c + (255,))
    return outlined(im)


def tomb():
    im = rgba()
    d = ImageDraw.Draw(im)
    d.rectangle([5, 8, 26, 29], fill=(120, 124, 134, 255))
    d.rectangle([5, 8, 26, 11], fill=(150, 154, 164, 255))
    d.ellipse([12, 11, 19, 17], fill=(140, 144, 154, 255))    # (a Warden carved on the lid)
    d.rectangle([13, 17, 18, 26], fill=(140, 144, 154, 255))
    d.line([(15, 18), (15, 25)], fill=(160, 140, 240, 255))   # (a glass sword laid on them)
    return outlined(im)


def cell_bars():
    im = rgba()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 3, 31, 5], fill=(70, 68, 74, 255))
    d.rectangle([0, 27, 31, 29], fill=(70, 68, 74, 255))
    for x in range(2, 32, 5):
        d.line([(x, 3), (x, 29)], fill=(96, 94, 100, 255), width=2)
    return outlined(im)


def shardglass_rock(spent):
    """A boulder glassed through with Shard: dig it for Shard Remnants (spent: its glass dug out, dull)."""
    im = rgba()
    d = ImageDraw.Draw(im)
    d.ellipse([4, 10, 28, 30], fill=(70, 66, 80, 255))
    d.ellipse([6, 11, 24, 24], fill=(92, 88, 104, 255))
    if not spent:
        for x, y, h in ((11, 22, 8), (16, 20, 11), (21, 23, 7)):
            crystal(d, x, y, h, 2, (160, 120, 250))
    else:
        for x, y in ((11, 20), (16, 18), (21, 21)):
            d.point((x, y), fill=(50, 40, 70, 255))
    return outlined(im)


def decor():
    made = 0
    sets = {"Shard_Crystal001": (61, [(150, 100, 240)], 3, 5, 9, 6), "Shard_Crystal002": (62, [(110, 190, 240)], 2, 10, 16, 3),
            "Shard_Crystal003": (63, [(150, 100, 240), (190, 140, 250)], 5, 7, 15, 8),
            "Shard_Crystal004": (64, [(230, 200, 240), (200, 170, 250)], 3, 6, 11, 6)}
    for name, args in sets.items():
        made += save("Tiles", name, crystals_decor(*args))
    for n, (seed, cap, gill) in enumerate(((71, (120, 70, 140), (120, 240, 210)), (72, (180, 110, 60), (250, 210, 120)),
                                           (73, (70, 110, 150), (160, 220, 255))), 1):
        made += save("Tiles", "Lantern_Cap%03d" % n, lantern_cap(seed, cap, gill))
    made += save("Tiles", "Glow_Moss001", glow_moss())
    made += save("Tiles", "Deep_Kelp001", kelp(81))
    made += save("Tiles", "Deep_Kelp002", kelp(82))
    for part in (1, 2, 3, 4):
        made += save("Tiles", "Leviathan_Rib%03d" % part, rib(part))
    made += save("Tiles", "Leviathan_Spine001", spine())
    for i, part in enumerate(skull_parts(), 1):
        made += save("Tiles", "Leviathan_Skull%03d" % i, part)
    made += save("Tiles", "Warden_Statue001", warden_statue())
    made += save("Tiles", "Warden_Brazier001", brazier())
    made += save("Tiles", "Warden_Tomb001", tomb())
    made += save("Tiles", "Cell_Bars001", cell_bars())
    made += save("Tiles", "Shardglass_Rock001", shardglass_rock(False))
    made += save("Tiles", "Shardglass_Rock002", shardglass_rock(True))
    return made


# ================================================================== the Fallen Shard, the Singing Geode, the glowfin
def fallen_shard(frame):
    """The piece of the Heart that fell into the sea: a great crystal standing in fused glass, light breathing in it."""
    im = rgba(96, 96)
    d = ImageDraw.Draw(im)
    glow = 0.5 + 0.5 * math.sin(frame / 4 * 2 * math.pi)
    d.ellipse([10, 78, 86, 94], fill=(90, 60, 150, 255))      # (its light pooled about it)
    d.ellipse([22, 81, 74, 91], fill=(140, 110, 220, 255))
    heart = int(200 + 55 * glow)
    crystal(d, 48, 88, 82, 13, (150, 110, 240), 2)
    crystal(d, 32, 88, 44, 8, (120, 90, 220), -6)
    crystal(d, 63, 88, 38, 8, (170, 140, 250), 5)
    crystal(d, 22, 90, 20, 5, (110, 180, 240), -3)
    crystal(d, 74, 90, 16, 4, (110, 180, 240), 3)
    d.line([(48, 82), (49, 14)], fill=(heart, heart, 255, 255), width=3)
    for k in range(6):                                        # (motes drifting up from it)
        y = int(70 - (frame * 9 + k * 13) % 64)
        x = 48 + int(20 * math.sin(k * 2.1 + frame * 0.8))
        d.point((x, y), fill=(230, 220, 255, 255))
        d.point((x + 1, y), fill=(200, 180, 255, 255))
    return outlined(im)


def lantern_tree(seed, cap, gill):
    """A lantern cap as tall as a house: a pale twisting stalk, a wide cap, its gills glowing."""
    im = rgba(48, 72)
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    lean = rng.choice((-3, -2, 2, 3))
    for y in range(24, 70):                                   # (the stalk)
        t = (y - 24) / 46
        x = 24 + int(lean * (1 - t) * math.sin(t * 3))
        w = 3 + int(2 * t)
        d.line([(x - w, y), (x + w, y)], fill=(206, 200, 184, 255))
        d.point((x - w, y), fill=(232, 228, 214, 255))
        d.point((x + w, y), fill=(150, 142, 128, 255))
    d.ellipse([16, 64, 34, 71], fill=(120, 110, 100, 255))   # (its foot)
    d.pieslice([2, 2, 46, 42], 180, 360, fill=cap + (255,))
    d.chord([4, 18, 44, 30], 0, 180, fill=tuple(int(c * 0.55) for c in cap) + (255,))
    for x in range(7, 42, 3):                                 # (the gills, glowing)
        d.line([(x, 22), (24 + (x - 24) // 3, 27)], fill=gill + (255,))
    for _ in range(8):                                        # (spots on the cap)
        a = rng.uniform(math.pi * 1.1, math.pi * 1.9)
        r = rng.uniform(0.35, 0.85) * 20
        cx, cy = 24 + r * math.cos(a), 21 + r * 0.9 * math.sin(a)
        d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=(240, 236, 220, 255))
    return outlined(im)


def stalk_foot():
    """Where a tall thing's foot meets the ground (the tile under it: it can't be walked through)."""
    im = rgba()
    d = ImageDraw.Draw(im)
    d.ellipse([7, 22, 25, 31], fill=(20, 14, 24, 110))
    return im


def shard_spire(seed):
    """A crystal as tall as two people, growing out of the floor, others round its foot."""
    im = rgba(32, 72)
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    col = rng.choice(((150, 100, 240), (110, 190, 240), (190, 140, 250)))
    crystal(d, 16, 70, rng.randint(52, 64), 6, col, rng.choice((-3, -1, 1, 3)))
    crystal(d, 9, 70, rng.randint(18, 26), 4, col, -3)
    crystal(d, 24, 70, rng.randint(14, 22), 4, col, 3)
    return outlined(im)


def geode():
    im = rgba()
    d = ImageDraw.Draw(im)
    d.ellipse([3, 8, 29, 30], fill=(96, 90, 86, 255))
    d.ellipse([7, 12, 25, 27], fill=(60, 40, 90, 255))
    for a in range(0, 360, 30):
        x, y = 16 + 7 * math.cos(math.radians(a)), 19 + 6 * math.sin(math.radians(a))
        crystal(d, int(x), int(y) + 2, 4, 1, (200, 170, 255))
    d.point((16, 19), fill=(255, 250, 255, 255))
    return outlined(im)


def entities():
    made = 0
    frames = [fallen_shard(f) for f in range(4)]
    made += save("Entities", "Fallen_Shard", frames[0])
    for f, im in enumerate(frames, 1):
        made += save("Entities", "Fallen_Shard%d" % f, im)
    made += save("Entities", "Singing_Geode", geode())
    for n, (seed, cap, gill) in enumerate(((171, (120, 70, 140), (120, 240, 210)), (172, (180, 110, 60), (250, 210, 120)),
                                           (173, (70, 110, 150), (160, 220, 255))), 1):
        made += save("Entities", "Lantern_Tree%03d" % n, lantern_tree(seed, cap, gill))
    for n, seed in enumerate((181, 182, 183), 1):
        made += save("Entities", "Shard_Spire%03d" % n, shard_spire(seed))
    made += save("Tiles", "Stalk_Foot001", stalk_foot())
    for n in ("", "1", "2", "3", "4"):
        src = p("sprites", "Entities", "Swordfish_Spot%s.png" % n)
        if os.path.exists(src):
            made += save("Entities", "Glowfin_Spot%s" % n, tint(Image.open(src), (110, 230, 210), keep_dark=0, gain=180))
    lec = Image.open(p("sprites", "Entities", "Grimoire_Lectern.png")).convert("RGBA")
    made += save("Entities", "Wardens_Journal", tint(lec, (150, 160, 200)))
    return made


# ================================================================== gear and things carried
def ring_icon(gem, band=(150, 154, 170)):
    im = rgba()
    d = ImageDraw.Draw(im)
    d.ellipse([8, 12, 24, 26], outline=band + (255,), width=3)
    d.ellipse([9, 13, 23, 25], outline=tuple(min(255, c + 60) for c in band) + (255,), width=1)
    d.ellipse([12, 7, 20, 15], fill=gem + (255,))
    d.point((15, 9), fill=(255, 255, 255, 255))
    return outlined(im)


def marshal_seal():
    im = rgba()
    d = ImageDraw.Draw(im)
    d.ellipse([6, 6, 26, 26], fill=(60, 62, 76, 255))
    d.ellipse([8, 8, 24, 24], fill=(110, 114, 130, 255))
    crystal(d, 16, 22, 13, 3, (160, 130, 250))
    return outlined(im)


def gear():
    made = 0
    made += save("Entities", "Wardens_Signet", ring_icon((150, 120, 240)))
    made += save("Entities", "Brine_Pearl_Ring", ring_icon((236, 240, 232), band=(120, 170, 170)))
    made += save("Entities", "Marshals_Seal", marshal_seal())
    for src, dst, col in (("Raw_Swordfish", "Raw_Glowfin", (100, 200, 190)), ("Cooked_Swordfish", "Cooked_Glowfin", (200, 170, 120))):
        made += save("Entities", dst, tint(Image.open(p("sprites", "Entities", src + ".png")), col))
    for src, dst, col in (("Mithril_Sword", "Shardglass_Blade", (176, 140, 255)), ("Mithril_Shield", "Wardens_Aegis", (170, 200, 220))):
        made += save("Entities", dst, tint(Image.open(p("sprites", "Entities", src + ".png")), col))
        for path in glob.glob(p("sprites", "Worn", "Worn_%s*.png" % src)):        # (drawn on whoever wears it)
            rest = os.path.basename(path)[len("Worn_" + src):-len(".png")]
            made += save("Worn", "Worn_%s%s" % (dst, rest), tint(Image.open(path), col))
    return made


# ================================================================== creatures
def creatures(mobs):
    """mobs: {name: (base, colour, level, kind, words, opts)}: each drawn from its base, recoloured; opts' Spikes grows
    crystals on it, Scale makes it bigger (a boss), Ghost makes it see-through."""
    made = 0
    for name, (base, col, _, _, _, opts) in mobs.items():
        pics = [(p("sprites", "Entities", base + ".png"), p("sprites", "Entities", name + ".png"))]
        for path in glob.glob(p("sprites", "Walk", base + "[1248][abc].png")):
            pics.append((path, p("sprites", "Walk", name + os.path.basename(path)[len(base):])))
        for k, (src, dst) in enumerate(pics):
            if not os.path.exists(src):
                continue
            im = tint(Image.open(src), col)
            if opts.get("Spikes"):
                im = spikes(im, opts["Spikes"], zlib.crc32(name.encode()) % 1000)
            if opts.get("Scale"):
                im = scaled(im, opts["Scale"])
            if opts.get("Ghost"):
                a = np.array(im)
                a[..., 3] = (a[..., 3] * 0.72).astype(np.uint8)
                im = Image.fromarray(a, "RGBA")
            made += write_image(dst, im)
    return made


# ================================================================== sounds (the old world's: bells, breath, plucked strings)
def sounds():
    import story_kit as SK
    rate = SK.RATE
    made = 0
    # (the seal breaking: a low bell, and a long breath let out)
    bell = SK.tone(110, 2.2, harmonics=(1.0, 0.5, 0.28, 0.12), attack=0.005, release=1.6)
    rng = random.Random(5)
    breath = [0.0] * len(bell)
    v = 0.0
    for i in range(len(breath)):
        v = 0.96 * v + 0.04 * rng.uniform(-1, 1)
        t = i / rate
        breath[i] = v * 2.2 * math.sin(math.pi * min(1.0, t / 2.2))
    made += SK.wav("Seal_Break", [a * math.exp(-i / rate * 1.4) + b * 0.5 for i, (a, b) in enumerate(zip(bell, breath))])
    # (the geode's song: a slow chord of low harp strings, each let ring)
    out = [0.0] * int(rate * 3.2)
    for k, f in enumerate((130.8, 164.8, 196.0, 261.6)):
        start = int(k * 0.32 * rate)
        note = SK.tone(f, 2.4, harmonics=(1.0, 0.4, 0.2, 0.1), attack=0.004, release=1.8)
        for i, s in enumerate(note):
            if start + i < len(out):
                out[start + i] += s * math.exp(-i / rate * 1.1) * 0.5
    made += SK.wav("Geode_Song", out)
    return made


def draw_all(mobs):
    made = grounds() + walls() + decor() + entities() + gear() + creatures(mobs) + sounds()
    print("The Shardfall Deep's pictures and sounds: %d written" % made)
