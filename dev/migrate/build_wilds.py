"""Something to find in the empty corners of the mainland (the owner's wish: the wide places with nothing in them and
the dead ends, each its own thing). On the world map unless it's a secret; none of it is needed by the story.

  * The Ringing Rocks (map 1,7): five veined stones in a mountain hollow, and Tamsin, who rings them. Ring her tunes
    back (the CHIMES minigame, dsengine/minigames.py), longer each time.
  * Abel's Pasture (5,9): Abel's three lambs got over the river. Catch them (side quest LambQuest).
  * The Collier's Clearing (6,14): Hode and his smoking clamp. Logs for coal (CollierQuest, then a trade).
  * The Old Tollhouse (2,14): where the road stops in the woods, a bar across it and the toll-keeper who never left.
    Three riddles (TollRiddles).
  * Merrin's Meadow (-9,10): bee skeps in the high meadow. Smoke them first (BeeQuest).
  * The Fen Horn (-7,8): an old horn on a post by a black pool. Blow it, and what the pool keeps comes up for a minute.
  * Natter's Corner (-11,4): Mother Natter, the Frog King, and the heron that robbed him (FrogQuest: you'll be a frog).
  * Pell (-5,8): a miner's ghost in the Stoneways, and the wraith that has his pick (DelverQuest).
  * Salt Agnes's Cove (0,22) and three bottles on the shore (0,22 and 1,23): a castaway's letters, and where he left
    it all (CastawayQuest).
  * The Smugglers' Signal (27,12): a pyre on the point. Light it, and somebody rows in (Marro sells; shared, a while).
  * The Ward-Circle (21,9): eight stones in the gravel bowl of the Cinder Peaks. Wake them, and hold (a wave, Waves.ini
    Ward_Circle_Trial).
  * The Ice-Fishers' Camp (18,23): Ulla, her hole in the ice, and the man frozen in it further out.
  * Three fairy rings (19,10, 10,1 and -11,19), not on the world map: step in one, and out of the next.

Run after the owner's maps are in (it changes them in place, a thing at a time). Shards: Shards.ini [Shards] (Wilds.*)
and each quest's Reward.Shards. Safe to run again.

  python -I "dev\\migrate\\build_wilds.py"   (then build_minimaps.py, export_web_assets.py)
"""
import collections
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import Ini, p, write_image           # noqa: E402
import story_kit as SK                           # noqa: E402
import world_edit as W                           # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

MAKER = "build_wilds.py"
S = 32
OPEN = "1" * 49
SOLID = "1111111111111111000111100011110001111111111111111"   # (the foot of it, in its cell's middle)
OUTLINE = (24, 20, 14, 255)
FAR = (("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",))
SHARDS = [("Wilds.Rocks", "8"), ("Wilds.Coffer", "5"), ("Wilds.Ward", "8"), ("Wilds.Ice", "6"), ("Wilds.Fairy", "10")]
ROCK_HUES = [(138, 106, 208), (79, 143, 216), (63, 176, 160), (208, 176, 64), (224, 120, 88)]   # (as games.js draws them)


def cell(mx, my, tx, ty):
    """A map's tile (counted from 1) as a world cell."""
    return mx * W.XT + tx - 1, my * W.YT + ty - 1


def px(tx, ty):
    """A map tile's top left in pixels, as a script's coordinates are."""
    return "%d,%d" % ((tx - 1) * S, (ty - 1) * S)


# ------------------------------------------------------------------ pictures
def new(w=S, h=S):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def outlined(im):
    out = im.copy()
    a, pix = im.load(), out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if a[x, y][3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + dx < w and 0 <= y + dy < h and a[x + dx, y + dy][3]:
                    pix[x, y] = OUTLINE
                    break
    return out


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


def shadow(w=S, h=S, box=(7, 26, 25, 31), alpha=80):
    sh = new(w, h)
    ImageDraw.Draw(sh).ellipse(box, fill=(16, 14, 10, alpha))
    return sh


def lit(pic, box=(7, 26, 25, 31), alpha=80):
    return Image.alpha_composite(shadow(box=box, alpha=alpha), pic)


def speckle(im, rng, k=0.12, lo=0.86, hi=1.08):
    pix = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            c = pix[x, y]
            if c[3] == 255 and c[:3] != OUTLINE[:3] and rng.random() < k:
                pix[x, y] = shade(c, rng.uniform(lo, hi))
    return im


def ringing_rock(n):
    """A grey stone, taller as its note's higher, a coloured vein running up it where it sings; lit on the west."""
    rng = random.Random("ringing_rock%d" % n)
    im = new()
    d = ImageDraw.Draw(im)
    top = 15 - n * 2
    w = 7 - n // 3
    d.polygon([(16 - w - 2, 30), (16 + w + 2, 30), (16 + w, top + 4), (17, top), (14, top + 1), (16 - w, top + 5)],
              fill=(118, 116, 112, 255))
    pix = im.load()
    for y in range(S):
        for x in range(S):
            if pix[x, y][3]:
                c = (138, 136, 130) if x < 16 else (98, 96, 92)
                if y > 27:
                    c = shade(c, 0.78)[:3]
                pix[x, y] = c + (255,)
    hue = ROCK_HUES[n - 1]
    x = 15
    for y in range(29, top + 2, -1):                                  # (the vein, wandering up it)
        if rng.random() < 0.35:
            x += rng.choice((-1, 1))
        x = max(16 - w, min(16 + w - 1, x))
        if pix[x, y][3]:
            pix[x, y] = hue + (255,)
            if y % 3 == 0 and pix[x + 1, y][3]:
                pix[x + 1, y] = shade(hue, 0.7)
    speckle(im, rng)
    return lit(outlined(im), (16 - w - 4, 26, 16 + w + 5, 32))


def recolour(src, parts, new_cols):
    """A person's picture with some of its Look.Parts in other colours (each shade kept as light as it was)."""
    im = src.convert("RGBA").copy()
    swap = {}
    for part in parts.split(";"):
        name, _, cols = part.partition(":")
        if name not in new_cols:
            continue
        cs = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in cols.split()]
        base = max(1.0, sum(cs[0]) / 3.0)
        for c in cs:
            k = (sum(c) / 3.0) / base
            swap[c] = tuple(max(0, min(255, int(v * k))) for v in new_cols[name])
    pix = im.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            c = pix[x, y]
            if c[3] and c[:3] in swap:
                pix[x, y] = swap[c[:3]] + (c[3],)
    return im


def ghostly(src):
    """A ghost of a picture: drained of colour, a cold pale blue, and half see-through."""
    im = src.convert("RGBA").copy()
    pix = im.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = pix[x, y]
            if a:
                lum = r * 0.3 + g * 0.59 + b * 0.11
                v = 120 + lum * 0.55
                pix[x, y] = (int(v * 0.86), int(v * 0.95), min(255, int(v * 1.08)), int(a * 0.62))
    return im


def tinted(src, col, k=0.55):
    """A picture leaned towards col (its outline kept dark)."""
    im = src.convert("RGBA").copy()
    pix = im.load()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = pix[x, y]
            if a and r + g + b > 90:
                pix[x, y] = (int(r * (1 - k) + col[0] * k * (r + g + b) / 382.0),
                             int(g * (1 - k) + col[1] * k * (r + g + b) / 382.0),
                             int(b * (1 - k) + col[2] * k * (r + g + b) / 382.0), a)
    return im


def lamb(src):
    """A sheep's frame made a lamb's: smaller, whiter, standing on the same ground."""
    im = src.convert("RGBA")
    box = im.getbbox()
    if box is None:
        return im
    body = im.crop(box)
    bw, bh = body.size
    body = body.resize((max(1, int(bw * 0.72)), max(1, int(bh * 0.72))), Image.NEAREST)
    body = tinted(body, (255, 252, 240), 0.3)
    out = new()
    out.alpha_composite(body, ((S - body.size[0]) // 2, box[3] - body.size[1]))
    return out


def crowned(src):
    """A frog's frame with a little gold crown on top of its head."""
    im = src.convert("RGBA").copy()
    box = im.getbbox()
    if box is None:
        return im
    x0, y0, x1, _ = box
    cx = (x0 + x1) // 2
    d = ImageDraw.Draw(im)
    gold, dark = (232, 196, 64, 255), (150, 108, 30, 255)
    d.rectangle((cx - 3, y0 - 2, cx + 3, y0), fill=gold)
    for dx in (-3, 0, 3):
        d.point((cx + dx, y0 - 3), fill=gold)
    d.line((cx - 3, y0, cx + 3, y0), fill=dark)
    d.point((cx, y0 - 1), fill=(200, 40, 40, 255))
    return im


def clamp(f):
    """A charcoal clamp: a low dome of turf and earth, smoke leaking out of its top and sides (f: which puff)."""
    rng = random.Random("clamp")
    im = new()
    d = ImageDraw.Draw(im)
    d.ellipse((2, 14, 30, 34), fill=(84, 68, 46, 255))
    pix = im.load()
    for y in range(S):
        for x in range(S):
            if pix[x, y][3]:
                c = (96, 80, 54) if x + y < 34 else (70, 56, 38)
                if rng.random() < 0.2:
                    c = (70, 92, 46)                                  # (the turf on it)
                pix[x, y] = c + (255,)
    for x in (9, 16, 23):
        d.line((x, 16 + abs(x - 16) // 3, x, 18 + abs(x - 16) // 3), fill=(40, 30, 22, 255))   # (the vent holes)
    out = outlined(im)
    sm = new()
    ds = ImageDraw.Draw(sm)
    for i, (x, y0) in enumerate(((16, 12), (8, 17), (24, 17))):
        rise = (f * 3 + i * 4) % 12
        r = 2 + rise // 4
        alpha = max(0, 150 - rise * 11)
        ds.ellipse((x - r + (rise // 3) % 2, y0 - rise - r, x + r, y0 - rise + r), fill=(186, 182, 172, alpha))
    return Image.alpha_composite(out, sm)


def toll_bar():
    """The bar across the road: a pole striped red and white, gone pink and grey, on two posts."""
    im = new()
    d = ImageDraw.Draw(im)
    post = (92, 70, 46, 255)
    d.rectangle((2, 12, 5, 30), fill=post)
    d.rectangle((27, 14, 29, 30), fill=post)
    for x in range(1, 31):
        c = (178, 104, 100, 255) if (x // 4) % 2 else (196, 190, 176, 255)
        d.line((x, 13, x, 16), fill=c)
    d.line((1, 13, 30, 13), fill=(220, 214, 200, 255))
    d.rectangle((0, 11, 6, 14), fill=(110, 110, 112, 255))               # (the iron cap the hinge is in)
    return lit(outlined(im), (0, 27, 32, 32), 70)


def skep(f):
    """A straw bee skep on a flat stone, a few bees about its door (f: where they are)."""
    im = new()
    d = ImageDraw.Draw(im)
    d.rectangle((5, 27, 27, 30), fill=(112, 108, 100, 255))
    d.ellipse((7, 6, 25, 32), fill=(196, 160, 82, 255))
    d.rectangle((6, 27, 26, 28), fill=(112, 108, 100, 255))
    for y in range(9, 27, 3):                                        # (the coils of straw)
        d.line((8, y, 24, y), fill=(160, 124, 58, 255))
    d.ellipse((14, 21, 18, 26), fill=(40, 28, 16, 255))              # (its door)
    out = outlined(im)
    pix = out.load()
    rng = random.Random("bees%d" % f)
    for _ in range(4):
        x, y = rng.randint(6, 26), rng.randint(4, 22)
        pix[x, y] = (30, 26, 14, 255)
        if x + 1 < S:
            pix[x + 1, y] = (226, 190, 40, 255)
    return lit(out, (4, 27, 28, 32))


def honeycomb():
    im = new()
    d = ImageDraw.Draw(im)
    d.polygon([(6, 10), (24, 6), (27, 22), (9, 27)], fill=(222, 164, 40, 255))
    for y in range(9, 26, 4):
        for x in range(8 + (y // 4 % 2) * 2, 26, 4):
            d.point((x, y), fill=(170, 108, 20, 255))
            d.point((x + 1, y), fill=(246, 206, 96, 255))
    d.line((7, 11, 23, 7), fill=(250, 220, 130, 255))
    return outlined(im)


def mead():
    """A stoppered stone bottle of mead, a bee drawn on its side."""
    im = new()
    d = ImageDraw.Draw(im)
    d.rectangle((14, 4, 18, 9), fill=(150, 112, 60, 255))
    d.ellipse((8, 9, 24, 29), fill=(176, 160, 128, 255))
    d.line((11, 12, 11, 26), fill=(206, 192, 160, 255))
    d.ellipse((14, 17, 18, 21), fill=(222, 178, 40, 255))
    d.line((15, 19, 17, 19), fill=(40, 30, 16, 255))
    return outlined(im)


def fen_horn():
    """A long horn of black wood bound in iron, hung on a post by the pool."""
    im = new()
    d = ImageDraw.Draw(im)
    d.rectangle((14, 8, 17, 31), fill=(82, 64, 44, 255))
    d.line((5, 9, 27, 12), fill=(52, 44, 36, 255), width=3)
    d.polygon([(23, 8), (30, 6), (30, 16), (23, 14)], fill=(52, 44, 36, 255))     # (its bell)
    for x in (9, 16, 22):
        d.line((x, 8, x, 12), fill=(130, 128, 124, 255))              # (its iron bands)
    d.point((4, 9), fill=(150, 150, 146, 255))                        # (the mouthpiece)
    return lit(outlined(im), (9, 27, 23, 32))


def fen_coffer():
    """A small iron-bound coffer, black with peat and dripping, a frond of weed hanging off it."""
    im = new()
    d = ImageDraw.Draw(im)
    d.rectangle((6, 14, 26, 28), fill=(58, 46, 32, 255))
    d.rectangle((6, 11, 26, 16), fill=(66, 52, 36, 255))
    for x in (9, 23):
        d.line((x, 11, x, 28), fill=(84, 86, 84, 255))
    d.rectangle((14, 17, 18, 20), fill=(110, 104, 70, 255))
    d.line((20, 11, 22, 19), fill=(80, 104, 52, 255))
    d.point([(8, 29), (17, 30), (24, 29)], fill=(40, 52, 40, 255))
    return lit(outlined(im))


def heron_nest():
    """A heron's untidy platform of sticks on a willow stump, a white feather in it."""
    rng = random.Random("nest")
    im = new()
    d = ImageDraw.Draw(im)
    d.rectangle((11, 20, 21, 31), fill=(78, 62, 44, 255))
    for _ in range(26):
        x, y = rng.randint(3, 24), rng.randint(10, 19)
        d.line((x, y, x + rng.randint(4, 8), y + rng.randint(-2, 2)), fill=rng.choice(
            [(112, 88, 58, 255), (90, 70, 46, 255), (132, 106, 70, 255)]))
    d.line((19, 9, 25, 6), fill=(236, 236, 230, 255), width=2)
    return lit(outlined(im), (6, 27, 26, 32))


def pearl():
    im = new()
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, 22, 22), fill=(220, 226, 214, 255))
    d.ellipse((12, 12, 16, 16), fill=(255, 255, 250, 255))
    d.arc((10, 10, 22, 22), 20, 120, fill=(170, 196, 170, 255))
    return outlined(im)


def bottle():
    """A green bottle half in the sand, a roll of paper inside, its cork waxed over."""
    im = new()
    d = ImageDraw.Draw(im)
    d.polygon([(6, 22), (20, 16), (23, 21), (9, 27)], fill=(70, 128, 92, 255))
    d.polygon([(20, 16), (26, 13), (27, 16), (23, 21)], fill=(70, 128, 92, 255))
    d.rectangle((26, 12, 28, 15), fill=(150, 60, 50, 255))
    d.line((9, 22, 19, 18), fill=(224, 214, 180, 255), width=2)       # (the letter)
    d.line((7, 22, 19, 17), fill=(150, 200, 166, 255))                # (the light on the glass)
    out = outlined(im)
    ImageDraw.Draw(out).line((4, 27, 14, 28), fill=(196, 176, 120, 255))
    return out


def cairn():
    """Stones piled waist-high, a driftwood stick stood up in the top."""
    rng = random.Random("cairn")
    im = new()
    d = ImageDraw.Draw(im)
    for x0, y0, r in ((10, 26, 6), (21, 26, 6), (16, 22, 6), (12, 18, 5), (20, 18, 5), (16, 13, 4)):
        c = rng.choice([(140, 136, 128), (120, 118, 112), (156, 150, 140)])
        d.ellipse((x0 - r, y0 - r + 2, x0 + r, y0 + r - 1), fill=c + (255,))
        d.arc((x0 - r, y0 - r + 2, x0 + r, y0 + r - 1), 180, 270, fill=shade(c, 1.2))
    d.line((17, 10, 15, 1), fill=(170, 150, 120, 255), width=2)
    return lit(outlined(im), (3, 26, 29, 32))


def pyre(f=None):
    """Logs stacked crosswise for a beacon; f: its flames (None: not lit)."""
    im = new()
    d = ImageDraw.Draw(im)
    for i, y in enumerate((26, 22, 18, 14)):
        if i % 2 == 0:
            d.rectangle((5, y, 27, y + 3), fill=(104, 78, 50, 255))
            d.point([(5, y + 1), (27, y + 1)], fill=(170, 140, 96, 255))
        else:
            for x in (7, 15, 23):
                d.rectangle((x, y, x + 3, y + 3), fill=(120, 90, 58, 255))
                d.rectangle((x + 1, y + 1, x + 2, y + 2), fill=(176, 146, 100, 255))
    out = lit(outlined(im), (3, 27, 30, 32))
    if f is None:
        return out
    fl = new()
    df = ImageDraw.Draw(fl)
    rng = random.Random("flame%d" % f)
    for x in range(7, 26, 3):
        h = 8 + rng.randint(0, 10) + (4 if 12 <= x <= 20 else 0)
        sway = rng.choice((-1, 0, 1))
        df.polygon([(x - 2, 20), (x + 2, 20), (x + sway, 20 - h)], fill=(232, 120, 32, 230))
        df.polygon([(x - 1, 20), (x + 1, 20), (x + sway, 20 - h * 2 // 3)], fill=(252, 214, 90, 240))
    return Image.alpha_composite(out, fl)


def ward_stone(n):
    """A squat black stone of the Cinder Peaks, a pale ward-mark cut in its face."""
    rng = random.Random("ward%d" % n)
    im = new()
    d = ImageDraw.Draw(im)
    d.polygon([(9, 30), (23, 30), (22, 12), (18, 9), (12, 10), (10, 13)], fill=(58, 52, 50, 255))
    pix = im.load()
    for y in range(S):
        for x in range(S):
            if pix[x, y][3]:
                pix[x, y] = ((74, 66, 62) if x < 15 else (50, 44, 42)) + (255,)
    mark = (176, 200, 214, 255)
    if n == 1:
        d.line((16, 14, 16, 25), fill=mark)
        d.line((13, 19, 19, 19), fill=mark)
    else:
        d.ellipse((13, 15, 19, 21), outline=mark)
        d.point((16, 18), fill=mark)
    speckle(im, rng)
    return lit(outlined(im), (6, 27, 26, 32))


def plinth(f=0):
    """The circle's middle: a flat black plinth with a socket in it, a shard of light deep in the socket (f: its glow)."""
    im = new()
    d = ImageDraw.Draw(im)
    d.polygon([(4, 24), (16, 18), (28, 24), (16, 30)], fill=(64, 58, 56, 255))
    d.polygon([(4, 24), (16, 30), (16, 32), (4, 26)], fill=(44, 40, 38, 255))
    d.polygon([(28, 24), (16, 30), (16, 32), (28, 26)], fill=(34, 30, 30, 255))
    d.ellipse((12, 22, 20, 26), fill=(24, 22, 22, 255))
    glow = (150 + f * 30, 210, 236, 255)
    d.point([(16, 24), (15, 24)], fill=glow)
    out = outlined(im)
    if f:
        ImageDraw.Draw(out).ellipse((13, 21 - f, 19, 25), outline=(170, 220, 240, 60 + f * 30))
    return out


def ice_hole():
    """A round hole cut in the ice, black water in it, chips of ice round its lip."""
    im = new()
    d = ImageDraw.Draw(im)
    d.ellipse((5, 9, 27, 25), fill=(214, 232, 240, 255))
    d.ellipse((8, 11, 24, 23), fill=(26, 46, 66, 255))
    d.arc((8, 11, 24, 23), 200, 340, fill=(60, 92, 120, 255))
    for x, y in ((4, 18), (27, 14), (14, 26), (22, 25)):
        d.rectangle((x, y, x + 1, y + 1), fill=(240, 250, 255, 255))
    return im


def frozen_man(stage=0):
    """A traveller in the ice face down, his pack still on: blurred blue through it, crazed with cracks."""
    rng = random.Random("frozen")
    im = new()
    d = ImageDraw.Draw(im)
    d.ellipse((2, 6, 30, 30), fill=(190, 220, 236, 255))
    d.ellipse((9, 11, 23, 17), fill=(120, 140, 160, 255))           # (the pack)
    d.ellipse((12, 15, 20, 27), fill=(98, 110, 132, 255))           # (his back)
    d.line((10, 18, 6, 24), fill=(98, 110, 132, 255), width=2)       # (an arm out, reaching)
    d.ellipse((14, 25, 18, 29), fill=(130, 120, 118, 255))           # (his head)
    pix = im.load()
    for y in range(S):
        for x in range(S):
            c = pix[x, y]
            if c[3] and c[:3] != (190, 220, 236):
                pix[x, y] = (int(c[0] * 0.6 + 190 * 0.4), int(c[1] * 0.6 + 220 * 0.4), int(c[2] * 0.6 + 236 * 0.4), 255)
    for _ in range(4 + stage * 3):                                   # (the cracks, more as it's chipped)
        x, y = rng.randint(6, 26), rng.randint(9, 27)
        for _ in range(rng.randint(3, 7)):
            if pix[x, y][3]:
                pix[x, y] = (246, 252, 255, 255)
            x += rng.choice((-1, 0, 1))
            y += rng.choice((-1, 0, 1))
    return im


def toadstools():
    """Toadstools in an arc, red with white spots, the grass flattened between them."""
    rng = random.Random("toadstool")
    im = new()
    d = ImageDraw.Draw(im)
    for x, y in ((6, 20), (15, 14), (24, 19), (12, 26), (22, 27)):
        d.line((x, y, x, y + 4), fill=(232, 224, 200, 255), width=2)
        d.ellipse((x - 3, y - 3, x + 3, y + 1), fill=(196, 44, 40, 255))
        d.point((x - 1, y - 2), fill=(250, 240, 230, 255))
        if rng.random() < 0.6:
            d.point((x + 1, y - 1), fill=(250, 240, 230, 255))
    return outlined(im)


def ring_light(f):
    """The air in the ring, shining faintly, motes turning in it (f: where they are)."""
    im = new()
    pix = im.load()
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - 15.5, y - 17) / 14.0
            if d < 1:
                pix[x, y] = (210, 250, 220, int(46 * (1 - d)))
    d = ImageDraw.Draw(im)
    for i in range(5):
        a = f * math.pi / 2 + i * 2 * math.pi / 5
        x, y = 15.5 + 9 * math.cos(a), 17 + 6 * math.sin(a) - (i % 2) * 3
        d.point((int(x), int(y)), fill=(240, 255, 210, 220))
    return im


def average(im, under=(88, 112, 56)):
    return Image.alpha_composite(Image.new("RGBA", im.size, under + (255,)), im).convert("RGB").resize(
        (1, 1), Image.BOX).getpixel((0, 0))


# ------------------------------------------------------------------ sounds
def stone_bell(freq, secs=1.4):
    """A struck stone that rings: a hard tick, then a few out-of-tune partials dying away (the high ones first)."""
    out = []
    rng = random.Random(int(freq))
    partials = ((1.0, 1.0, 2.2), (2.71, 0.45, 4.0), (5.19, 0.2, 7.0), (0.5, 0.12, 3.0))
    for i in range(int(SK.RATE * secs)):
        t = i / SK.RATE
        v = sum(a * math.exp(-t * k) * math.sin(2 * math.pi * freq * m * t) for m, a, k in partials)
        if t < 0.012:
            v += (rng.random() * 2 - 1) * (1 - t / 0.012) * 0.8          # (the knock of the striker)
        out.append(v * min(1.0, t / 0.002))
    return out


def sounds():
    for n, f in enumerate((392.0, 440.0, 523.25, 587.33, 659.25), 1):    # (G A C D E: any order sounds like a tune)
        SK.wav("Rock_Chime%d" % n, stone_bell(f), gain=0.8)


# ------------------------------------------------------------------ data
PEOPLE = {   # new person: (drawn from, its colours, what Examine says, its verbs, how it moves)
    "Stone_Ringer": ("Woman", {"shirt": (92, 104, 120), "hair": (150, 150, 156)},
                     "A grey-haired woman in a slate-coloured shawl, a little hammer of horn in her belt. She hums.",
                     "Talk to,Examine"),
    "Collier": ("Man", {"shirt": (60, 56, 52), "legs": (48, 40, 32)},
                "A collier, black to the elbows and the eyebrows. He smells like a bonfire's morning after.",
                "Talk to,Examine"),
    "Beekeeper": ("Farmer", {"shirt": (226, 214, 160), "hair": (120, 82, 40)},
                  "A beekeeper in a straw hat and a veil pushed back. A bee walks round the brim, and is let.",
                  "Talk to,Examine"),
    "Beachcomber": ("Old_Woman", {"shirt": (84, 108, 112), "legs": (100, 84, 60)},
                    "An old woman in a fisherman's smock, her pockets heavy with things the sea gave up.",
                    "Talk to,Examine"),
    "Night_Smuggler": ("Smuggler", {}, "A smuggler with a lantern shuttered down to a slit. He's in no hurry, and "
                                       "watches the road the whole time.", "Trade,Talk to,Examine"),
    "Ice_Fisher": ("Fisherman", {"shirt": (160, 60, 52), "hair": (220, 200, 160)},
                   "A broad fisherwoman in a red coat stuffed with fleece, sitting on a creel as if it's a throne.",
                   "Talk to,Examine"),
}
GHOSTS = {   # new ghost: (drawn from, what Examine says)
    "Toll_Keeper": ("Clerk", "A thin man in an old-fashioned coat, his ledger under his arm. You can see the trees "
                             "through him."),
    "Delver_Ghost": ("Miner", "A miner, his lamp lit with no flame in it. You can see the rock through him."),
}


def people_sprites():
    e = Ini(p("data", "Entities.ini"))
    folder = p("sprites", "Walk")
    for name, (src, cols, words, verbs) in PEOPLE.items():
        parts = e.get(src, "Look.Parts") or ""
        for d in "1248":
            for f in "abc":
                a = os.path.join(folder, "%s%s%s.png" % (src, d, f))
                if os.path.exists(a):
                    write_image(os.path.join(folder, "%s%s%s.png" % (name, d, f)),
                                recolour(Image.open(a), parts, cols) if cols else Image.open(a).convert("RGBA"))
        write_image(p("sprites", "Entities", name + ".png"),
                    recolour(Image.open(p("sprites", "Entities", src + ".png")), parts, cols))
    for name, (src, words) in GHOSTS.items():
        for d in "1248":
            for f in "abc":
                a = os.path.join(folder, "%s%s%s.png" % (src, d, f))
                if os.path.exists(a):
                    write_image(os.path.join(folder, "%s%s%s.png" % (name, d, f)), ghostly(Image.open(a)))
        write_image(p("sprites", "Entities", name + ".png"), ghostly(Image.open(p("sprites", "Entities", src + ".png"))))
    for d in "1248":                                                  # (the witch of the marsh: green, not purple)
        for f in "abc":
            a = os.path.join(folder, "Witch%s%s.png" % (d, f))
            if os.path.exists(a):
                write_image(os.path.join(folder, "Marsh_Witch%s%s.png" % (d, f)), recolour(
                    Image.open(a), e.get("Witch", "Look.Parts") or "", {"shirt": (78, 96, 52), "hair": (120, 120, 110)}))
            for src, dst, fn in (("Sheep", "Stray_Lamb", lamb), ("Frog", "Frog_King", crowned)):
                a = os.path.join(folder, "%s%s%s.png" % (src, d, f))
                if os.path.exists(a):
                    write_image(os.path.join(folder, "%s%s%s.png" % (dst, d, f)), fn(Image.open(a)))
    write_image(p("sprites", "Entities", "Marsh_Witch.png"), recolour(
        Image.open(p("sprites", "Entities", "Witch.png")), e.get("Witch", "Look.Parts") or "",
        {"shirt": (78, 96, 52), "hair": (120, 120, 110)}))
    write_image(p("sprites", "Entities", "Stray_Lamb.png"), lamb(Image.open(p("sprites", "Entities", "Sheep.png"))))
    write_image(p("sprites", "Entities", "Frog_King.png"), crowned(Image.open(p("sprites", "Entities", "Frog.png"))))
    pick = tinted(Image.open(p("sprites", "Entities", "Pickaxe.png")), (150, 120, 200), 0.35)
    ImageDraw.Draw(pick).point([(9, 24), (10, 23)], fill=(230, 226, 160, 255))    # (his mark, cut in the haft)
    write_image(p("sprites", "Entities", "Pells_Pick.png"), pick)


def tiles():
    t = Ini(p("data", "Tiles.ini"))

    def tile(name, pic, walk, words, under=(88, 112, 56), **keys):
        write_image(p("sprites", "Tiles", name + ".png"), pic, decor=True)
        for k, v in (("Walkable.Data", walk), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", words),
                     ("Line.of.Sight", "1"), ("Layer", "Decor")) + tuple((k.replace("_", "."), v) for k, v in keys.items()):
            t.set(name, k, v)
        SK.minimap_colour(name, average(pic, under))
    tile("Ward_Stone001", ward_stone(1), SOLID, "A squat black stone with a cross cut deep in its face, the cut's edges "
         "still sharp.", (120, 110, 100))
    tile("Ward_Stone002", ward_stone(2), SOLID, "A squat black stone with a ring cut in its face, and a dot in the ring. "
         "It's warmer than the rock round it.", (120, 110, 100))
    tile("Ice_Hole001", ice_hole(), SOLID, "A hole cut through the ice, kept open. The water in it is very black and "
         "very still.", (214, 232, 240))
    tile("Toadstool001", toadstools(), OPEN, "Toadstools, red and spotted white, in a ring that's too round.")
    t.save(p("data", "Tiles.ini"))


def entities():
    people_sprites()
    e = Ini(p("data", "Entities.ini"))
    for name, (src, cols, words, verbs) in PEOPLE.items():
        for k, v in (("Type", "NPC"), ("Use.Words", verbs), ("Examine.Info", words), ("Roam.Radius", "1"),
                     ("Chase.Radius", "0"), ("Walk.Speed", "0.4"), ("Pause", "4-10"), ("Attitude", "Good"),
                     ("Respawn", "300"), ("Level", "1")):
            e.set(name, k, v)
    for name, (src, words) in GHOSTS.items():
        for k, v in (("Type", "NPC"), ("Use.Words", "Talk to,Examine"), ("Examine.Info", words), ("Roam.Radius", "0"),
                     ("Chase.Radius", "0"), ("Walk.Speed", "0.3"), ("Pause", "6-14"), ("Attitude", "Good"),
                     ("Respawn", "300"), ("Level", "1")):
            e.set(name, k, v)
    for k, v in (("Type", "NPC"), ("Use.Words", "Talk to,Examine"), ("Roam.Radius", "1"), ("Chase.Radius", "0"),
                 ("Walk.Speed", "0.4"), ("Pause", "4-10"), ("Attitude", "Good"), ("Respawn", "300"), ("Level", "1"),
                 ("Examine.Info", "An old woman in green, her hem wet to the knee. Frogs sit round her feet like cats.")):
        e.set("Marsh_Witch", k, v)
    for k, v in (("Type", "NPC"), ("Use.Words", "Catch,Examine"), ("Roam.Radius", "3"), ("Chase.Radius", "0"),
                 ("Walk.Speed", "0.6"), ("Pause", "2-6"), ("Attitude", "Good"), ("Respawn", "300"), ("Level", "1"),
                 ("Examine.Info", "A lamb with a blue mark on its rump, a long way from wherever it's meant to be.")):
        e.set("Stray_Lamb", k, v)
    for k, v in (("Type", "NPC"), ("Use.Words", "Talk to,Examine"), ("Roam.Radius", "1"), ("Chase.Radius", "0"),
                 ("Walk.Speed", "0.4"), ("Pause", "5-12"), ("Attitude", "Good"), ("Respawn", "300"), ("Level", "1"),
                 ("Solid", "0"), ("Calls", "Croak"), ("Layer", "Under"),
                 ("Examine.Info", "A fat old frog in a little gold crown. It wears it as if it was born in it.")):
        e.set("Frog_King", k, v)

    def thing(name, pic, keys, frames=None):
        write_image(p("sprites", "Entities", name + ".png"), pic)
        for i, f in enumerate(frames or []):
            write_image(p("sprites", "Entities", "%s%d.png" % (name, i + 1)), f)
        for k, v in keys:
            e.set(name, k, v)
    for n in range(1, 6):
        thing("Ringing_Rock%d" % n, ringing_rock(n), (
            ("Type", "StaticObject"), ("Use.Words", "Strike,Examine"), ("Solid", "1"),
            ("Examine.Info", ("A low grey stone with a purple vein in it.", "A grey stone with a blue vein running up it.",
                              "A grey stone, a green vein in it like a crack that's healed.",
                              "A tall grey stone with a yellow vein, worn shiny where it's been struck.",
                              "The tallest stone, its red vein bright. It hums when the wind's in the north.")[n - 1])))
    thing("Charcoal_Clamp", clamp(0), (("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                                       ("Anim.Frames", "4"), ("Anim.Speed", "260"),
                                       ("Examine.Info", "A charcoal clamp: wood stacked tight and turfed over, burning "
                                                        "slow inside for days. Hot to stand near.")),
          [clamp(f) for f in range(4)])
    thing("Toll_Bar", toll_bar(), (("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                                   ("Examine.Info", "A toll bar across the end of the road, striped once. Nobody's "
                                                    "paid at it in forty years, and it hasn't been lifted either.")))
    thing("Bee_Skep", skep(0), (("Type", "StaticObject"), ("Use.Words", "Smoke,Take Honey,Examine"), ("Solid", "1"),
                                ("Anim.Frames", "2"), ("Anim.Speed", "300"),
                                ("Examine.Info", "A straw skep on a flat stone, humming like a kettle.")),
          [skep(0), skep(1)])
    thing("Honeycomb", honeycomb(), (("Type", "MapItem"), ("Use.Words", "Eat"), ("Stackable", "1"), ("Value", "8"),
                                     ("Food.Value", "3"), ("Examine.Info", "A piece of honeycomb, dripping. Heals 3.")))
    thing("Mead", mead(), (("Type", "MapItem"), ("Use.Words", "Drink,Eat"), ("Stackable", "1"), ("Value", "20"),
                           ("Food.Value", "6"), ("Examine.Info", "Merrin's mead, in a stone bottle. Heals 6, and "
                                                                 "tastes of a whole summer.")))
    thing("Fen_Horn", fen_horn(), (("Type", "StaticObject"), ("Use.Words", "Blow,Examine"), ("Solid", "1"),
                                   ("Examine.Info", "A long black horn bound in iron, hung on a post at the pool's "
                                                    "edge. The mouthpiece has been worn by a great many mouths.")))
    thing("Fen_Coffer", fen_coffer(), (("Type", "StaticObject"), ("Use.Words", "Open,Examine"), ("Solid", "1"),
                                       ("Examine.Info", "A little coffer, black with peat and streaming. It came up "
                                                        "out of the pool on its own.")))
    thing("Heron_Nest", heron_nest(), (("Type", "StaticObject"), ("Use.Words", "Search,Examine"), ("Solid", "1"),
                                       ("Examine.Info", "A heron's nest on an old stump: a heap of sticks, a smell of "
                                                        "fish, and a single white feather.")))
    thing("Frog_Pearl", pearl(), (("Type", "MapItem"), ("Display.Name", "Frog Pearl"), ("Stackable", "1"),
                                  ("Value", "0"), ("Examine.Info", "A pearl the size of a frog's eye. It's warm, and "
                                                                   "faintly green inside.")))
    thing("Pells_Pick", Image.open(p("sprites", "Entities", "Pells_Pick.png")).convert("RGBA"), (
        ("Type", "MapItem"), ("Display.Name", "Pell's Pick"), ("Stackable", "1"), ("Value", "0"),
        ("Examine.Info", "An old miner's pick, its haft dark with handling. PELL is cut in it, and a little lamp.")))
    thing("Message_Bottle", bottle(), (("Type", "StaticObject"), ("Use.Words", "Open,Examine"), ("Solid", "0"),
                                       ("Examine.Info", "A green bottle washed up in the sand, its cork waxed shut. "
                                                        "There's paper inside.")))
    thing("Castaway_Cairn", cairn(), (("Type", "StaticObject"), ("Use.Words", "Dig,Examine"), ("Solid", "1"),
                                      ("Examine.Info", "Stones piled up by hand, a stick of driftwood stood in the "
                                                       "top. It isn't a grave: there's nobody's name on it.")))
    thing("Signal_Pyre", pyre(), (("Type", "StaticObject"), ("Use.Words", "Light,Examine"), ("Solid", "1"),
                                  ("Examine.Info", "Logs stacked for a beacon, a long way from anywhere that needs "
                                                   "one. The ash under it is old, and there's a lot of it.")))
    thing("Signal_Pyre_Lit", pyre(0), (("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                                       ("Light", "90"), ("Light.Flicker", "1"), ("Glow", "40"), ("Anim.Frames", "4"),
                                       ("Anim.Speed", "120"),
                                       ("Examine.Info", "The beacon, roaring. They'll see it a long way out to sea.")),
          [pyre(f) for f in range(4)])
    thing("Ward_Plinth", plinth(0), (("Type", "StaticObject"), ("Use.Words", "Wake,Examine"), ("Solid", "1"),
                                     ("Anim.Frames", "4"), ("Anim.Speed", "400"),
                                     ("Examine.Info", "A flat black plinth with a socket in the middle. Something "
                                                      "glitters far down in the socket, further down than the stone "
                                                      "is deep.")),
          [plinth(f) for f in (0, 1, 2, 1)])
    thing("Frozen_Wanderer", frozen_man(1), (
        ("Type", "StaticObject"), ("Use.Words", "Chip At,Examine"), ("Solid", "0"), ("Layer", "Under"),
        ("Examine.Info", "Under the ice, face down, a man with a pack on, one arm out. He's been there some winters.")))
    thing("Fairy_Ring", ring_light(0), (("Type", "StaticObject"), ("Use.Words", "Step In,Examine"), ("Solid", "0"),
                                        ("Layer", "Under"), ("Anim.Frames", "4"), ("Anim.Speed", "320"),
                                        ("Light", "36"),
                                        ("Examine.Info", "The grass in the ring is greener than the grass outside it, "
                                                         "and the air over it shines.")),
          [ring_light(f) for f in range(4)])
    e.save(p("data", "Entities.ini"))
    s = Ini(p("data", "Shards.ini"))
    if s.get("Shards", "Wilds.Rocks") is None:
        s.section("Shards")[1].append((None, "; Wilds.*: what the wild places give, once each (build_wilds.py)."))
    for k, v in SHARDS:
        s.set("Shards", k, v, overwrite=False)
    s.save(p("data", "Shards.ini"))


# ------------------------------------------------------------------ scripts
def talk(name, rows):
    SK.write_script("Talk to " + name, rows, MAKER)


def started(quest, words):
    return ("Display.Message", "Yellow", "Quest started: %s. %s" % (quest, words), "Quest")


def finished(quest, words):
    return ("Display.Message", "Yellow", "Quest complete: %s! %s" % (quest, words), "Quest")


def rocks_scripts():
    for n in range(1, 6):
        SK.write_script("Strike Ringing_Rock%d" % n, [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            ("Play.Sound", "Rock_Chime%d" % n),
            ("End",)] + list(FAR), MAKER)
    again = (("Ring me another.", "@play"), ("Not now.", "@end"))
    talk("Tamsin", [
        (">Conditional", "$Attr.RingingRocks=0", "@known"),
        SK.say("Stone_Ringer", "Don't touch the red one, it's in a mood. (She looks at you properly.) No, go on, touch "
                               "it. Everyone should hear these once. My grandmother found them: five stones in a "
                               "hollow, and every one a note.",
               ("What do you do with them?", "@what"), ("I'll leave you to it.", "@end")),
        ("@what",),
        SK.say("Stone_Ringer", "Play them. I ring a tune, you ring it back. There's nobody else up here to do it, and "
                               "the stones like a second pair of hands. Shall we?",
               ("Ring me one.", "@play"), ("Not now.", "@end")),
        ("@known",),
        (">Conditional", "$Attr.RingingRocks<3", "@fun"),
        SK.say("Stone_Ringer", "Back for another? Good. The stones have been talking about you.", *again),
        ("@play",),
        ("Get.Value", "ATTRIBUTE", "RingingRocks", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@second"),
        ("Display.Message", "Cyan", "Tamsin taps out a short one with her little horn hammer. Listen, then ring it "
                                    "back.", "-"),
        ("Play.Minigame", "CHIMES", "1", "@lost"),
        ("Update.Attribute", "RingingRocks", "=1"),
        ("Give.Item", "Gold_Coin(s)", "20"),
        SK.say("Stone_Ringer", "There! You've an ear. My grandmother left me a jar of the coins people paid her to "
                               "hear them, and I've never known what to do with it. Have some. Come back for a "
                               "longer one.", ("I will.", "@end")),
        ("@second",),
        (">Conditional", "$Variable.1=1", "@third"),
        ("Display.Message", "Cyan", "Tamsin rings a longer one, and doesn't slow down for you.", "-"),
        ("Play.Minigame", "CHIMES", "3", "@lost"),
        ("Update.Attribute", "RingingRocks", "=2"),
        ("Give.Item", "Emerald", "1"),
        ("Give.Item", "Gold_Coin(s)", "30"),
        SK.say("Stone_Ringer", "Well! That one took me a winter. Here: the green came out of the hollow when "
                               "grandmother dug the yellow stone straight. It rings, if you flick it. There's one "
                               "more, the old one. It's long.", ("I'll be back for it.", "@end")),
        ("@third",),
        (">Conditional", "$Variable.1=2", "@fun"),
        ("Display.Message", "Cyan", "Tamsin rings the old tune, all of it, and every stone has its say.", "-"),
        ("Play.Minigame", "CHIMES", "5", "@lost"),
        ("Update.Attribute", "RingingRocks", "=3"),
        ("Play.Sound", "Absorb"),
        ("Give.Item", "Shard", "$Shards.Wilds.Rocks"),
        ("Display.Message", "Yellow", "The last note doesn't stop. It hangs in the hollow, then runs down the veins and "
                                      "into the ground, and up into you.", "-"),
        SK.say("Stone_Ringer", "Did you feel that? They've never done that for me. (She doesn't seem to mind.) Come "
                               "and ring whenever you like. They know you now.", ("I will.", "@end")),
        ("@fun",),
        ("Display.Message", "Cyan", "Tamsin rings one for the fun of it.", "-"),
        ("Play.Minigame", "CHIMES", "3", "@lost"),
        SK.say("Stone_Ringer", "Lovely. That's how they ought to sound.", ("Another.", "@fun"), ("That's enough.", "@end")),
        ("@lost",),
        SK.say("Stone_Ringer", "Never mind. They're stones, they'll wait. So will I.",
               ("Again.", "@play"), ("Later.", "@end")),
        ("@end",),
        ("End",)])


def lamb_scripts():
    talk("Shepherd_Abel", [
        ("Get.Value", "ATTRIBUTE", "LambQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        SK.say("Shepherd", "Three lambs. Three! Over the river while I slept, and the river's up. They'll be across "
                           "the far side by now, or in the wood, or halfway to the sea. I can't leave the rest.",
               ("I'll find them.", "@take"), ("Good luck with that.", "@end")),
        ("@take",),
        ("Update.Attribute", "LambQuest", "=1"),
        started("Abel's Lambs", "Find Abel's three lambs and send them home."),
        SK.say("Shepherd", "They've a blue mark on the rump. Catch one, and it'll run straight home, they always do "
                           "once they're sorry.", ("I'll go.", "@end")),
        ("@asked",),
        (">Conditional", "$Variable.1<4", "@back"),
        SK.say("Shepherd", "Any sign? Three lambs, blue on the rump. They're daft enough to be anywhere.",
               ("I'm still looking.", "@end")),
        ("@back",),
        (">Conditional", "$Variable.1=4", "@done"),
        ("Update.Attribute", "LambQuest", "=5"),
        finished("Abel's Lambs", "All three lambs are home."),
        SK.say("Shepherd", "There they are, all three, looking like it was my fault. Here, take this, it's not much. "
                           "And some wool off their mothers: they owe you that.", ("Glad to help.", "@end")),
        ("@done",),
        SK.say("Shepherd", "They're good as gold now. For a day or two.", ("Mind the river.", "@end")),
        ("@end",),
        ("End",)])
    for n in (1, 2, 3):
        SK.write_script("Catch Stray_Lamb_%d" % n, [
            (">Distance.From.Clicked.Entity", "48", "@far"),
            (">Conditional", "$Attr.LambQuest>=1 and $Attr.LambQuest<=3", "@shy"),
            (">Conditional", "$Attr.Lamb%d=0" % n, "@shy"),
            ("Update.Attribute", "Lamb%d" % n, "=1"),
            ("Update.Attribute", "LambQuest", "+1"),
            ("Play.Sound", "Pickup"),
            ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Stray_Lamb"),
            (">Conditional", "$Attr.LambQuest=4", "@more"),
            ("Quest.Note", "LambQuest", "All three lambs caught: tell Abel."),
            ("Display.Message", "Yellow", "You catch the last lamb. It bleats, sorry at last, and runs off for home.", "-"),
            ("End",),
            ("@more",),
            ("Display.Message", "Cyan", "You catch the lamb. It bleats at you, then runs off for home as if that had "
                                        "been the idea all along."),
            ("End",),
            ("@shy",),
            ("Display.Message", "Cyan", "The lamb skips out of reach. It doesn't know you."),
            ("End",)] + list(FAR), MAKER)


def collier_scripts():
    talk("Hode", [
        ("Get.Value", "ATTRIBUTE", "CollierQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        SK.say("Collier", "Mind the clamp, it bites. Twelve days she's been going, and she wants feeding, and my axe "
                          "went through its own handle this morning. Don't laugh. It's not the first.",
               ("I could cut you some logs.", "@take"), ("What's a clamp?", "@what"), ("Good day.", "@end")),
        ("@what",),
        SK.say("Collier", "Wood in, air out, turf on top, and leave her be. What comes out is charcoal: the smiths "
                          "won't burn anything else, and the smelters pay for it in good coal.",
               ("I could cut you some logs.", "@take"), ("Good day.", "@end")),
        ("@take",),
        ("Update.Attribute", "CollierQuest", "=1"),
        started("The Collier's Clamp", "Bring Hode 5 logs."),
        SK.say("Collier", "Five'll do her. Any wood, she's not fussy.", ("Back soon.", "@end")),
        ("@asked",),
        (">Conditional", "$Variable.1=1", "@trade"),
        (">Got.Item", "Logs", "5", "@none"),
        ("Take.Item", "Logs", "5"),
        ("Update.Attribute", "CollierQuest", "=2"),
        finished("The Collier's Clamp", "Hode's clamp is fed."),
        SK.say("Collier", "Lovely. In she goes. (He feeds the clamp; it smokes harder, pleased.) Take some coal off the "
                          "last burn, it's better than you'd buy. Any time you've three logs spare, I'll swap you one.",
               ("Done.", "@end")),
        ("@none",),
        SK.say("Collier", "Five logs. She'll go out while you're counting them.", ("I'll get them.", "@end")),
        ("@trade",),
        SK.say("Collier", "Three logs for a coal, same as ever.", ("Here's three. [if $Item.Logs>=3]", "@swap"),
               ("Not today.", "@end")),
        ("@swap",),
        ("Take.Item", "Logs", "3"),
        ("Give.Item", "Coal", "1"),
        SK.say("Collier", "Pleasure.", ("Three more. [if $Item.Logs>=3]", "@swap"), ("That's all.", "@end")),
        ("@end",),
        ("End",)])


TOLL = [   # (riddle, answers (the right one first), what he says to the right one)
    ("I have a neck and no head, two arms and no hands. I go out full and come home empty. What am I?",
     ("A shirt.", "A bottle.", "A cart."), "A shirt! My mother's riddle, that. She thought it very good."),
    ("The more you take of me, the more you leave behind. What am I?",
     ("Footsteps.", "Coins.", "Years."), "Footsteps. Yes. I have watched a great many of them go by."),
    ("Every soul that came this way paid me, and I paid every coin on to the crown, and kept none, forty years. "
     "What am I?",
     ("You.", "The road.", "The toll box."), "Me. (He looks down at himself, at the trees through him.) Yes. I "
                                              "suppose I am."),
]


def toll_scripts():
    rows = [
        ("Get.Value", "ATTRIBUTE", "TollRiddles", "Variable.1$"),
        (">Conditional", "$Variable.1<3", "@free"),
        ("Get.Value", "CALCULATION", "$Clock-$Attr.TollWrong", "Variable.4$"),
        (">Conditional", "$Variable.4>=60", "@sulk"),
        (">Conditional", "$Variable.1=0", "@ask"),
        SK.say("Toll_Keeper", "Halt! Toll. (He holds out a see-through hand.) The road's closed, but the toll stands. "
                              "I take no coin these days: they fall through. A riddle, then. Answer three, and I'll "
                              "lift the bar.", ("Go on, then.", "@ask"), ("I'll go round.", "@end")),
        ("@ask",),
    ]
    for i, (riddle, answers, right) in enumerate(TOLL):
        here = "@r%d" % i
        rows += [
            (here,),
            (">Conditional", "$Variable.1=%d" % i, "@r%d" % (i + 1) if i < 2 else "@end"),
            SK.say("Toll_Keeper", riddle, (answers[1], "@wrong"), (answers[0], "@right%d" % i), (answers[2], "@wrong"))
            if i % 2 == 0 else
            SK.say("Toll_Keeper", riddle, (answers[0], "@right%d" % i), (answers[2], "@wrong"), (answers[1], "@wrong")),
            ("@right%d" % i,),
            ("Update.Attribute", "TollRiddles", "=%d" % (i + 1)),
            ("Get.Value", "ATTRIBUTE", "TollRiddles", "Variable.1$"),
        ]
        if i < 2:
            rows += [SK.say("Toll_Keeper", right + (" One more. Now then..." if i == 1 else " Two more."),
                            ("Ask it.", "@r%d" % (i + 1)), ("Later.", "@end"))]
        else:
            rows += [finished("The Toll-Keeper's Riddles", "The last toll is paid."),
                     SK.say("Toll_Keeper", right + " Well. The toll's paid, and a toll paid is a bar lifted. (He "
                                              "puts his ledger under his arm, and closes it.) Forty years. Pass, "
                                              "friend.", ("Rest well.", "@end")),
                     ("End",)]
    rows += [
        ("@wrong",),
        ("Update.Attribute", "TollWrong", "=$Clock"),
        ("Display.Message", "DarkRed", "Wrong! The toll-keeper writes it down in his ledger and turns his back on you. "
                                       "He'll talk to you again in a minute.", "Fail"),
        ("End",),
        ("@sulk",),
        ("Display.Message", "DarkRed", "The toll-keeper is still writing down your wrong answer.", "Denied"),
        ("End",),
        ("@free",),
        SK.say("Toll_Keeper", "Paid in full. Pass, friend. (He doesn't lift the bar. He's forgotten how it goes.)",
               ("Rest well.", "@end")),
        ("@end",),
        ("End",)]
    talk("Toll_Keeper_Ghost", rows)


def bee_scripts():
    talk("Merrin", [
        ("Get.Value", "ATTRIBUTE", "BeeQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        SK.say("Beekeeper", "Slowly! Slow is the whole trick with bees. (A bee lands on her lip; she talks round it.) "
                            "I'm Merrin. I'd ask you to help me take the honey, only nobody's ever said yes.",
               ("I'll say yes.", "@take"), ("I'll say no, like everyone.", "@end")),
        ("@take",),
        ("Update.Attribute", "BeeQuest", "=1"),
        started("Merrin's Mead", "Bring Merrin 3 honeycombs from her skeps."),
        SK.say("Beekeeper", "Bless you. Smoke a skep first, with a tinderbox: it calms them, a little while. Then take "
                            "the comb, quick, before they think about it. Three'll do for a batch.",
               ("Smoke first. Got it.", "@end")),
        ("@asked",),
        (">Conditional", "$Variable.1=1", "@after"),
        (">Got.Item", "Honeycomb", "3", "@none"),
        ("Take.Item", "Honeycomb", "3"),
        ("Update.Attribute", "BeeQuest", "=2"),
        finished("Merrin's Mead", "Merrin has her honey."),
        SK.say("Beekeeper", "Look at that! Not a sting on you. Well, not many. Here's last year's mead for it: it's "
                            "better than this year's will be, but don't tell the bees.", ("Thank you.", "@end")),
        ("@none",),
        SK.say("Beekeeper", "Three combs. Smoke first, then quick.", ("Right.", "@end")),
        ("@after",),
        SK.say("Beekeeper", "Help yourself to a comb now and then, if you smoke them first. They don't mind you. Much.",
               ("I will.", "@end")),
        ("@end",),
        ("End",)])
    SK.write_script("Smoke Bee_Skep", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Got.Item", "Tinderbox", "1", "@nobox"),
        ("Play.Sound", "MakeFire"),
        ("Update.Attribute", "SkepSmoked", "=$Clock"),
        ("Display.Message", "Cyan", "You puff smoke into the skep's door. The humming drops, slow and sleepy."),
        ("End",),
        ("@nobox",),
        ("Display.Message", "DarkRed", "You need a tinderbox to make smoke.", "Denied"),
        ("End",)] + list(FAR), MAKER)
    SK.write_script("Take Honey Bee_Skep", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "CALCULATION", "$Clock-$Attr.SkepSmoked", "Variable.4$"),
        (">Conditional", "$Variable.4<=30", "@stung"),
        ("Get.Value", "CALCULATION", "$Clock-$Attr.SkepHoney", "Variable.5$"),
        (">Conditional", "$Variable.5>=90", "@bare"),
        ("Update.Attribute", "SkepHoney", "=$Clock"),
        ("Update.Attribute", "SkepSmoked", "=0"),
        ("Give.Item", "Honeycomb", "1"),
        ("Display.Message", "Yellow", "You lift out a dripping comb before the bees think about it.", "Harvest"),
        ("End",),
        ("@bare",),
        ("Display.Message", "DarkRed", "You've taken what's ripe for now. Give them time.", "Denied"),
        ("End",),
        ("@stung",),
        ("Play.Sound", "Buzz"),
        ("Display.Message", "DarkRed", "The bees are awake, and say so. Ow. Smoke them first.", "Fail"),
        ("End",)] + list(FAR), MAKER)


HORN_AT = (10, 5)
COFFER_AT = (9, 3)


def horn_scripts():
    SK.write_script("Blow Fen_Horn", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Play.Sound", "Horn"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Fen_Horn"),
        ("Add.Entity", px(*COFFER_AT), "Fen_Coffer", "StaticObject", "-"),
        ("Add.Action.To.Queue", "REMOVE", "Fen_Coffer", "StaticObject", "-", "$Map.Name", px(*COFFER_AT), "60"),
        ("Add.Action.To.Queue", "ADD", "Fen_Horn", "StaticObject", "-", "$Map.Name", px(*HORN_AT), "60"),
        ("Display.Message", "Cyan", "The horn's note goes out low over the fen and comes back from the hills. The black "
                                    "pool heaves, and something bobs up against the bank, streaming. The horn slips "
                                    "off its post into the reeds."),
        ("End",)] + list(FAR), MAKER)
    SK.write_script("Open Fen_Coffer", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.FenCoffer=0", "@empty"),
        ("Update.Attribute", "FenCoffer", "=1"),
        ("Play.Sound", "Chest"),
        ("Give.Item", "Gold_Coin(s)", "40"),
        ("Give.Item", "Silver_Ring", "1"),
        ("Give.Item", "Shard", "$Shards.Wilds.Coffer"),
        ("End",),
        ("@empty",),
        ("Display.Message", "Cyan", "The coffer is empty but for black water.", "Empty"),
        ("End",)] + list(FAR), MAKER)


def frog_scripts():
    talk("Mother_Natter", [
        ("Get.Value", "ATTRIBUTE", "FrogQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@one"),
        SK.say("Marsh_Witch", "Mind my frogs. They're all somebody. (She looks you up and down.) You've the look of "
                              "someone who'll do a thing for an old woman. The king's lost his pearl, and he's "
                              "sulking, and when he sulks nobody sings.",
               ("What king?", "@king"), ("Not today.", "@end")),
        ("@king",),
        SK.say("Marsh_Witch", "The Frog King, of course. Over by the reeds. He won't talk to anything with ears. I can "
                              "fix your ears for you: a minute and a half, no more. Shall I?",
               ("Make me a frog.", "@frog"), ("I like my ears.", "@end")),
        ("@frog",),
        ("Update.Attribute", "FrogQuest", "=1"),
        started("The Frog King's Pearl", "Mother Natter made you a frog, to talk to the Frog King."),
        ("Turn.Into", "Frog", "90", "Mother Natter flicks marsh water at you. With a pop, you are a frog. She looks very "
                                    "pleased with herself."),
        ("End",),
        ("@one",),
        (">Conditional", "$Variable.1=1 or $Variable.1=3", "@two"),
        (">Conditional", "$Player.Form=-", "@hop"),
        SK.say("Marsh_Witch", "Back to see him? Hold still.", ("Make me a frog.", "@again"), ("Not now.", "@end")),
        ("@again",),
        ("Turn.Into", "Frog", "90", "With a pop, you are a frog again. It's easier the second time."),
        ("End",),
        ("@hop",),
        SK.say("Marsh_Witch", "Go on, hop along. He's by the reeds.", ("Croak.", "@end")),
        ("@two",),
        (">Conditional", "$Variable.1=2", "@three"),
        SK.say("Marsh_Witch", "The heron's nest! Of course it was the heron. Well, a frog can't climb, so you'll want "
                              "your hands back. Wait it out.", ("Fine.", "@end")),
        ("@three",),
        SK.say("Marsh_Witch", "He's singing again: hear him? The whole marsh is. Thank you, dear. Come and be a frog "
                              "whenever you like.", ("Make me a frog.", "@again"), ("Goodbye.", "@end")),
        ("@end",),
        ("End",)])
    talk("Frog_King", [
        (">Conditional", "$Player.Form=Frog", "@croak"),
        ("Get.Value", "ATTRIBUTE", "FrogQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@back"),
        SK.say("Frog_King", "A visitor! Of the proper shape, at last. Kneel. (You're already as low as you go.) Good. "
                            "We are robbed. Our pearl, from our own lily pad, taken by the heron to her nest in the "
                            "east. We would go ourself, but she eats kings.",
               ("I'll get it back.", "@take")),
        ("@take",),
        ("Update.Attribute", "FrogQuest", "=2"),
        ("Quest.Note", "FrogQuest", "The heron took the Frog King's pearl to her nest. A frog can't climb."),
        SK.say("Frog_King", "We are grateful. We are also hungry: if you see a fly, it's ours.", ("Croak.", "@end")),
        ("@back",),
        (">Conditional", "$Variable.1=2 or $Variable.1=3", "@after"),
        (">Got.Item", "Frog_Pearl", "1", "@noperl"),
        ("Take.Item", "Frog_Pearl", "1"),
        ("Update.Attribute", "FrogQuest", "=4"),
        ("Boost.Skill", "Fishing", "2", "900"),
        finished("The Frog King's Pearl", "The Frog King has his pearl again."),
        SK.say("Frog_King", "Our pearl! (He sits on it.) Hear us, marsh: sing! (The marsh sings.) For this, the fish "
                            "of our waters will come to your line a while. Kings can do that. Go well, frog.",
               ("Croak.", "@end")),
        ("@noperl",),
        SK.say("Frog_King", "You come before us without our pearl? Bold. Very bold. The heron's nest is east.",
               ("Croak.", "@end")),
        ("@after",),
        SK.say("Frog_King", "Ah, our friend the frog. Sit. There's a very good fly about somewhere.", ("Croak.", "@end")),
        ("@croak",),
        ("Display.Message", "Cyan", "The frog in the crown looks at you, and croaks. Just a croak. It seems to expect "
                                    "more of you."),
        ("Play.Sound", "Croak"),
        ("@end",),
        ("End",)])
    SK.write_script("Search Heron_Nest", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Player.Form=-", "@frog"),
        (">Conditional", "$Attr.FrogQuest=2", "@sticks"),
        ("Update.Attribute", "FrogQuest", "=3"),
        ("Give.Item", "Frog_Pearl", "1"),
        ("Quest.Note", "FrogQuest", "You have the pearl. Only a frog can give it back."),
        ("Display.Message", "Yellow", "Under the fish bones, in the very middle of the nest, something round and warm.", "-"),
        ("End",),
        ("@sticks",),
        ("Display.Message", "Cyan", "Sticks, fish bones, and a smell. Nothing you want.", "Empty"),
        ("End",),
        ("@frog",),
        ("Display.Message", "DarkRed", "A heron's nest is no place for a frog. You can't climb, and you'd rather not.",
         "Denied"),
        ("End",)] + list(FAR), MAKER)


def pell_scripts():
    talk("Pell", [
        ("Get.Value", "ATTRIBUTE", "DelverQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        SK.say("Delver_Ghost", "Ah. Another one with a lamp. Don't worry, I'm not the one to worry about down here. I'm "
                               "Pell. I worked this vein forty years, and I'd still be working it, if it wasn't for "
                               "that thing in the east tunnel.",
               ("What thing?", "@thing"), ("I'll be going.", "@end")),
        ("@thing",),
        SK.say("Delver_Ghost", "A wraith. It came up out of the deep one night and I didn't. It has my pick. You'd not "
                               "think a man could miss a pick so. I can't rest without my hands full.",
               ("I'll get your pick back.", "@take"), ("Sorry.", "@end")),
        ("@take",),
        ("Update.Attribute", "DelverQuest", "=1"),
        started("Pell's Pick", "Kill the wraith in the Stoneways' east tunnel, and bring Pell his pick."),
        SK.say("Delver_Ghost", "It's strong, mind. Stronger than me, and I was strong. Bring friends, or bring "
                               "something sharp.", ("I'll manage.", "@end")),
        ("@asked",),
        (">Conditional", "$Variable.1<3", "@rest"),
        (">Got.Item", "Pells_Pick", "1", "@nopick"),
        ("Take.Item", "Pells_Pick", "1"),
        ("Update.Attribute", "DelverQuest", "=3"),
        finished("Pell's Pick", "Pell has his pick again."),
        SK.say("Delver_Ghost", "My pick. (He takes it, and it goes as see-through as he is.) There. Now I can do a bit "
                               "more, and then I think I'll stop. Take my good one, the steel: it was always too good "
                               "for me. It wants a living hand.", ("Rest well, Pell.", "@end")),
        ("@nopick",),
        SK.say("Delver_Ghost", "East tunnel. It knows these halls. Don't let it get behind you.", ("I'll go.", "@end")),
        ("@rest",),
        SK.say("Delver_Ghost", "(He's working the rock with his old pick, very slowly, making no sound at all. He "
                               "nods to you, and goes on.)", ("Goodbye, Pell.", "@end")),
        ("@end",),
        ("End",)])
    SK.write_script("Kill Stoneways_Wraith", [
        (">Conditional", "$Attr.DelverQuest=1", "@end"),
        ("Update.Attribute", "DelverQuest", "=2"),
        ("Give.Item", "Pells_Pick", "1"),
        ("Quest.Note", "DelverQuest", "The wraith is dead and you have Pell's pick. Take it to him."),
        ("Display.Message", "Yellow", "Where the wraith fell, an old pick, its haft cut with a name: PELL.", "-"),
        ("@end",),
        ("End",)], MAKER)


LETTERS = [
    "Bottle the first. I am on an island with a palm tree and nothing else. I have named the tree Gerald. If found, "
    "come quickly. Bring bread. - T.",
    "Bottle the second. Gerald has fallen down. I have built a raft of Gerald. I shall make for the south-east, where "
    "the grass is. I have the strongbox. - T.",
    "Bottle the last. Landed. The strongbox is too heavy to carry and I am too tired to care. Buried it under a heap "
    "of stones on the grass by the shore, and stood what's left of Gerald up in the top. Going inland. Wish me luck. "
    "- Tobin.",
]


def castaway_scripts():
    talk("Salt_Agnes", [
        ("Get.Value", "ATTRIBUTE", "CastawayQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@asked"),
        SK.say("Beachcomber", "Morning. Mind the weed, it's slippery. (She shakes a bottle at you; nothing in it.) "
                              "This shore's a bottle shore. The currents bring 'em all in here, sooner or later. Most "
                              "are empty. Not all.",
               ("What's in the full ones?", "@full"), ("Good hunting.", "@end")),
        ("@full",),
        SK.say("Beachcomber", "Letters. Three, these last weeks, all the same hand, and I can't get the corks out with "
                              "these fingers. Wax, see. Find them for me, open them, and read me what they say. I "
                              "like a story.",
               ("I'll find them.", "@take"), ("Not today.", "@end")),
        ("@take",),
        ("Update.Attribute", "CastawayQuest", "=1"),
        started("The Castaway's Letters", "Find the three bottles Salt Agnes has seen on the shore."),
        SK.say("Beachcomber", "Two along this shore, and one further round, south and east, where the grass comes down "
                              "to the sand.", ("I'll look.", "@end")),
        ("@asked",),
        (">Conditional", "$Variable.1<4", "@more"),
        SK.say("Beachcomber", "Any letters? Green bottles, sealed with red.", ("Still looking.", "@end")),
        ("@more",),
        (">Conditional", "$Variable.1=4", "@dug"),
        SK.say("Beachcomber", "Gerald! Ha! A heap of stones by the shore, south and east: go and see, if you've a "
                              "spade. He'll not be coming back for it.", ("I'll go.", "@end")),
        ("@dug",),
        (">Conditional", "$Variable.1=5", "@done"),
        ("Update.Attribute", "CastawayQuest", "=6"),
        finished("The Castaway's Letters", "Salt Agnes has her story."),
        SK.say("Beachcomber", "The strongbox! And he went inland, and good luck to him. I'll keep his letters, if you "
                              "don't mind. I like a story that ends with somebody walking off.",
               ("So do I.", "@end")),
        ("@done",),
        SK.say("Beachcomber", "Nothing in the bottles today. There's always tomorrow.", ("Good hunting.", "@end")),
        ("@end",),
        ("End",)])
    for n in (1, 2, 3):
        SK.write_script("Open Castaway_Bottle_%d" % n, [
            (">Distance.From.Clicked.Entity", "48", "@far"),
            (">Conditional", "$Attr.CastawayQuest>=1 and $Attr.CastawayQuest<=3", "@shut"),
            (">Conditional", "$Attr.Bottle%d=0" % n, "@read"),
            ("Update.Attribute", "Bottle%d" % n, "=1"),
            ("Update.Attribute", "CastawayQuest", "+1"),
            ("Play.Sound", "Paper"),
            ("Quest.Note", "CastawayQuest", LETTERS[n - 1]),
            ("Display.Message", "Cyan", "You crack the wax and shake out a letter: \"%s\"" % LETTERS[n - 1]),
            (">Conditional", "$Attr.CastawayQuest=4", "@end"),
            ("Display.Message", "Yellow", "That's all three letters.", "-"),
            ("@end",),
            ("End",),
            ("@read",),
            ("Display.Message", "Cyan", "You've read this one. You put it back in the bottle, for the next person."),
            ("End",),
            ("@shut",),
            ("Display.Message", "Cyan", "A green bottle, its cork waxed shut. Somebody's message, not yours to break."),
            ("End",)] + list(FAR), MAKER)
    SK.write_script("Dig Castaway_Cairn", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Got.Item", "Spade", "1", "@nospade"),
        (">Conditional", "$Attr.CastawayQuest=4", "@nothing"),
        ("Play.Animation", "Dirt_Clods", "3", "DigHole"),
        ("Update.Attribute", "CastawayQuest", "=5"),
        ("Give.Item", "Gold_Coin(s)", "70"),
        ("Give.Item", "Ruby", "1"),
        ("Quest.Note", "CastawayQuest", "You dug up Tobin's strongbox. Tell Salt Agnes."),
        ("Display.Message", "Yellow", "Under the stones, a strongbox gone green at the corners. Tobin's. He'd want "
                                      "somebody to have it.", "-"),
        ("End",),
        ("@nothing",),
        ("Display.Message", "Cyan", "Stones, on top of stones. Whoever piled them here meant them to stay.", "-"),
        ("End",),
        ("@nospade",),
        ("Display.Message", "DarkRed", "You need a spade to dig.", "Denied"),
        ("End",)] + list(FAR), MAKER)


PYRE_AT = (2, 8)
MARRO_AT = (9, 10)


def smuggler_scripts():
    SK.write_script("Light Signal_Pyre", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Got.Item", "Tinderbox", "1", "@nobox"),
        (">Got.Item", "Logs", "3", "@nologs"),
        ("Take.Item", "Logs", "3"),
        ("Play.Sound", "MakeFire"),
        ("Remove.Entity", "$Object.under.Cursor.X,$Object.under.Cursor.Y", "Signal_Pyre"),
        ("Add.Entity", px(*PYRE_AT), "Signal_Pyre_Lit", "StaticObject", "-"),
        ("Add.Entity", px(*MARRO_AT), "Night_Smuggler", "NPC", "Attitude=Good Stand=1 Face=W Id=Smuggler_Marro "
                                                                "Name=Marro"),
        ("Add.Action.To.Queue", "REMOVE", "Signal_Pyre_Lit", "StaticObject", "-", "$Map.Name", px(*PYRE_AT), "300"),
        ("Add.Action.To.Queue", "ADD", "Signal_Pyre", "StaticObject", "-", "$Map.Name", px(*PYRE_AT), "300"),
        ("Add.Action.To.Queue", "REMOVE", "Night_Smuggler", "NPC", "-", "$Map.Name", px(*MARRO_AT), "300"),
        ("Display.Message", "Cyan", "You throw on your logs and light it. The beacon goes up with a roar. Not long after, "
                                    "oars, out on the dark water, and a boat grates on the beach."),
        ("End",),
        ("@nologs",),
        ("Display.Message", "DarkRed", "The pyre's damp and half fallen in. It wants 3 more logs on it before it'll "
                                       "burn.", "Denied"),
        ("End",),
        ("@nobox",),
        ("Display.Message", "DarkRed", "You need a tinderbox to light it.", "Denied"),
        ("End",)] + list(FAR), MAKER)
    SK.write_script("Trade Smuggler_Marro", [
        ("Display.Item.Rack", "SPECIFIC", "Night_Smuggler", "SHOP-Smuggler", "@end"),
        ("@end",),
        ("End",)], MAKER)
    talk("Smuggler_Marro", [
        SK.say("Night_Smuggler", "Evening. You lit the fire, so you know the rules: you didn't see me, I didn't see "
                                 "you, and the prices are good because nobody's paid any duty on them. Buying?",
               ("Show me.", "@shop"), ("Who are you?", "@who"), ("Not tonight.", "@end")),
        ("@who",),
        SK.say("Night_Smuggler", "Marro. My father lit that fire for his customers, and his father. The ash is three "
                                 "feet deep under it, if you dig. Don't dig. The tide won't wait long.",
               ("Show me.", "@shop"), ("Goodnight.", "@end")),
        ("@shop",),
        ("Display.Item.Rack", "SPECIFIC", "Night_Smuggler", "SHOP-Smuggler", "@end"),
        ("@end",),
        ("End",)])


def ward_scripts():
    SK.write_script("Wake Ward_Plinth", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "CALCULATION", "$Clock-$Attr.WardWoken", "Variable.4$"),
        (">Conditional", "$Variable.4>=1800", "@asleep"),
        ("Update.Attribute", "WardWoken", "=$Clock"),
        ("Play.Sound", "Stone_Wake"),
        ("Display.Message", "Cyan", "You lay your hand on the plinth. The light in the socket rises to meet it, and the "
                                    "marks on the eight stones flare white. Something answers out of the rock."),
        ("Start.Wave", "Ward_Circle_Trial"),
        ("End",),
        ("@asleep",),
        ("Display.Message", "DarkRed", "The plinth is cold. The circle's still resting from the last time you woke it.",
         "Denied"),
        ("End",)] + list(FAR), MAKER)
    SK.write_script("Ward Circle Held", [
        (">Conditional", "$Attr.WardShard=0", "@end"),
        ("Update.Attribute", "WardShard", "=1"),
        ("Play.Sound", "Absorb"),
        ("Give.Item", "Shard", "$Shards.Wilds.Ward"),
        ("Display.Message", "Yellow", "The circle's marks dim, satisfied. What was holding them up runs out of the "
                                      "stones and into you.", "-"),
        ("@end",),
        ("End",)], MAKER)
    SK.set_section(p("data", "Waves.ini"), "Ward_Circle_Trial", [
        "Name=The Ward-Circle wakes",
        "Map=21,9,0",
        "Centre=Ward_Circle",
        "Waves=Arcane_Wisp*3;Arcane_Wisp*2,Shard_Golem*1;Shard_Golem*2,Arcane_Wisp*1",
        "Gap=10",
        "Minutes=6",
        "Random.Every=0",
        "Gold.Per.Kill=4",
        "Reward.Gold=40",
        "Reward.Items=Super_Potion 1",
        "Reward.XP=1",
        "Start.Message=The Ward-Circle wakes: what it was set to keep out is coming in. Hold the circle!",
        "Win.Message=The last of it breaks on the stones. The Ward-Circle holds, and goes quiet.",
        "Lose.Message=The circle's marks gutter out, and what came through goes back where it came from.",
        "On.Win.Script=Ward Circle Held"])


def ice_scripts():
    talk("Ulla", [
        SK.say("Ice_Fisher", "Shh. You'll frighten the fish, stamping about like that. (She hasn't looked up from the "
                             "hole.) Salmon, under the ice, fat as pigs this time of year. Help yourself to the hole if "
                             "you've a rod. I'm going in a minute. I've been going in a minute since dawn.",
               ("What's that out on the ice? [if $Attr.IceChip<3]", "@man"), ("Good fishing.", "@end")),
        ("@man",),
        SK.say("Ice_Fisher", "Him? He was there when my mother fished here. Went through in a hard winter, poor soul, "
                             "and the lake's never thawed far enough to give him back. You could chip him out, with a "
                             "pick and some patience. I've the patience. I've no pick.", ("I'll see.", "@end")),
        ("@end",),
        ("End",)])
    SK.write_script("Chip At Frozen_Wanderer", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Item.Pickaxe>0 or $Item.Bronze_Pickaxe>0 or $Item.Steel_Pickaxe>0 or $Item.Mithril_Pickaxe>0",
         "@nopick"),
        (">Conditional", "$Attr.IceChip<3", "@done"),
        ("Play.Animation", "Rock_Chips", "3", "Mine"),
        ("Update.Attribute", "IceChip", "+1"),
        (">Conditional", "$Attr.IceChip=3", "@more"),
        ("Play.Sound", "Freeze"),
        ("Give.Item", "Gold_Coin(s)", "35"),
        ("Give.Item", "Sapphire_Ring", "1"),
        ("Give.Item", "Shard", "$Shards.Wilds.Ice"),
        ("Display.Message", "Yellow", "The ice gives with a crack like a bell. You don't take him out, in the end: only "
                                      "what was in his hand, held out all these winters.", "-"),
        ("End",),
        ("@more",),
        ("Display.Message", "Cyan", "Chips fly. The ice over him cracks, but holds. Again."),
        ("End",),
        ("@done",),
        ("Display.Message", "Cyan", "He has nothing more in his hands. You leave him to the lake."),
        ("End",),
        ("@nopick",),
        ("Display.Message", "DarkRed", "You need a pickaxe to chip at the ice.", "Denied"),
        ("End",)] + list(FAR), MAKER)


RINGS = [((19, 10), (3, 9)), ((10, 1), (6, 8)), ((-11, 19), (7, 15))]   # (each leads to the next, the last to the first)


def fairy_scripts():
    for i, ((mx, my), (tx, ty)) in enumerate(RINGS):
        (nmx, nmy), (ntx, nty) = RINGS[(i + 1) % len(RINGS)]
        SK.write_script("Step In Fairy_Ring_%d" % (i + 1), [
            (">Distance.From.Clicked.Entity", "48", "@far"),
            ("Update.Attribute", "FairyRing%d" % (i + 1), "=1"),
            ("Play.Sound", "Portal"),
            ("Display.Message", "Cyan", "You step into the ring. The world turns over, green, and puts you down "
                                        "somewhere else entirely, on soft grass, in another ring."),
            ("Teleport", px(ntx, nty), "%d,%d,0" % (nmx, nmy)),
            ("Update.Attribute", "FairyRing%d" % ((i + 1) % len(RINGS) + 1), "=1"),
            (">Conditional", "$Attr.FairyRing1=1 and $Attr.FairyRing2=1 and $Attr.FairyRing3=1 and $Attr.FairyShard=0",
             "@end"),
            ("Update.Attribute", "FairyShard", "=1"),
            ("Play.Sound", "Absorb"),
            ("Give.Item", "Shard", "$Shards.Wilds.Fairy"),
            ("Display.Message", "Yellow", "Somewhere, small voices laugh. You've been round them all, and something of "
                                          "the rings comes with you.", "-"),
            ("@end",),
            ("End",)] + list(FAR), MAKER)


def quests():
    def side(name, giver, attr, stages, done, markers, shards, items="", xp="", level=None, rumour=""):
        lines = ["Giver=%s" % giver, "Attribute=%s" % attr]
        lines += ["Stage%d=%s" % (n, t) for n, t in sorted(stages.items())]
        lines += ["Done=%d" % done]
        lines += ["Marker%d=%s" % (n, m) for n, m in sorted(markers.items())]
        lines += ["Type=Side", "Requires.Quests=Passage to the Mainland"]
        if level:
            lines.append("Requires.Level=%d" % level)
        lines.append("Reward.Shards=%d" % shards)
        if items:
            lines.append("Reward.Items=%s" % items)
        if xp:
            lines.append("Reward.XP=%s" % xp)
        if rumour:
            lines.append("Rumour=%s" % rumour)
        SK.set_section(SK.QUESTS, name, lines)
    side("Abel's Lambs", "Shepherd", "LambQuest", {
        0: "Abel, a shepherd on the river meadows west of Wildwood, has lost something.",
        1: "Abel's three lambs got over the river. Find them (blue on the rump) and catch them. None caught yet.",
        2: "One of Abel's lambs is home. Two to find.",
        3: "Two of Abel's lambs are home. One to find.",
        4: "All three lambs are home: tell Abel."}, 5, {0: "Abels_Pasture", 4: "Abels_Pasture"}, 4,
        "Gold_Coin(s) 30 Wool 3", rumour="A shepherd out on the river meadows has been counting his flock over and over. "
                                         "It keeps coming out short.")
    side("The Collier's Clamp", "Collier", "CollierQuest", {
        0: "A collier is burning charcoal in a clearing in the woods south of Wildwood.",
        1: "Hode the collier's clamp wants feeding: bring him 5 logs."}, 2, {0: "Collier_Clearing", 1: "Collier_Clearing"},
        3, "Coal 3 Gold_Coin(s) 20", "Woodcutting 1")
    side("The Toll-Keeper's Riddles", "Toll_Keeper", "TollRiddles", {
        0: "Where the road stops in the woods, somebody still keeps the toll.",
        1: "The toll-keeper wants three riddles answered. One answered.",
        2: "The toll-keeper wants three riddles answered. Two answered."}, 3, {0: "Old_Tollhouse", 1: "Old_Tollhouse",
                                                                              2: "Old_Tollhouse"}, 6, "Gold_Coin(s) 40",
        rumour="They say the old toll road south of the Galaith pass is still kept. By whom, nobody says.")
    side("Merrin's Mead", "Beekeeper", "BeeQuest", {
        0: "A beekeeper keeps skeps in a high meadow in the West Range.",
        1: "Bring Merrin 3 honeycombs. Smoke a skep with a tinderbox first, then take its honey quickly."}, 2,
        {0: "Merrins_Meadow", 1: "Merrins_Meadow"}, 4, "Mead 3 Gold_Coin(s) 20")
    side("The Frog King's Pearl", "Marsh_Witch", "FrogQuest", {
        0: "An old woman lives on the marsh's edge, in the far west where it meets the sea.",
        1: "Mother Natter made you a frog. Talk to the Frog King while you're one.",
        2: "The heron took the Frog King's pearl to her nest. A frog can't climb: search the nest as yourself.",
        3: "You have the pearl. Mother Natter can make you a frog again, to give it back."}, 4,
        {0: "Natters_Corner", 1: "Natters_Corner", 3: "Natters_Corner"}, 6, "Gold_Coin(s) 30",
        rumour="A woman out at the end of the Mirefen keeps frogs the way other folk keep hens. Some say they were "
               "people once.")
    side("Pell's Pick", "Delver_Ghost", "DelverQuest", {
        0: "Somebody is working the rock in the Stoneways, without a sound.",
        1: "Pell the miner's ghost wants his pick: the wraith in the Stoneways' east tunnel has it.",
        2: "You have Pell's pick. Take it back to him."}, 3, {0: "Pells_Rest", 2: "Pells_Rest"}, 6,
        "Steel_Pickaxe 1 Gold_Coin(s) 60", "Mining 2", level=14)
    side("The Castaway's Letters", "Beachcomber", "CastawayQuest", {
        0: "An old beachcomber walks the sand in the far south of the desert coast.",
        1: "Salt Agnes has seen three bottles washed up: two along her shore, one further round to the south-east. "
           "None found yet.",
        2: "One of the castaway's letters found. Two to go.",
        3: "Two of the castaway's letters found. One to go.",
        4: "The castaway buried his strongbox under a cairn on the grass by the shore. Dig it up (a spade).",
        5: "You dug up the castaway's strongbox. Tell Salt Agnes."}, 6, {0: "Agnes_Cove", 1: "Agnes_Cove",
                                                                         5: "Agnes_Cove"}, 8, "Gold_Coin(s) 20",
        rumour="An old woman down on the desert's south shore says the sea's been sending her letters.")
    SK.set_section(SK.RACKS, "SHOP-Smuggler", [
        "Type=Shop", "Buy.Rate=0.85", "Sell.Rate=0.8", "Specific=1",
        "Item1=Healing_Draught,4", "Item2=Super_Potion,2", "Item3=Warming_Draught,3", "Item4=Sapphire,1",
        "Item5=Emerald,1", "Item6=Silver_Ring,1", "Item7=Sealskin_Boots,1", "Item8=Fire_Bolt_Scroll_II,1"])


def scripts():
    rocks_scripts()
    lamb_scripts()
    collier_scripts()
    toll_scripts()
    bee_scripts()
    horn_scripts()
    frog_scripts()
    pell_scripts()
    castaway_scripts()
    smuggler_scripts()
    ward_scripts()
    ice_scripts()
    fairy_scripts()
    quests()
    for label, where in (("The Ringing Rocks", "Ringing_Rocks"), ("Abel's Pasture", "Abels_Pasture"),
                         ("The Collier's Clearing", "Collier_Clearing"), ("The Old Tollhouse", "Old_Tollhouse"),
                         ("Merrin's Meadow", "Merrins_Meadow"), ("The Fen Horn", "Fen_Horn_Pool"),
                         ("Natter's Corner", "Natters_Corner"), ("Salt Agnes's Cove", "Agnes_Cove"),
                         ("The Smugglers' Signal", "Smugglers_Signal"), ("The Ward-Circle", "Ward_Circle"),
                         ("The Ice-Fishers' Camp", "Ice_Fishers_Camp")):
        SK.place_label("Places", label, where)


# ------------------------------------------------------------------ the maps
def once(w, gx, gy, kind, name, extra="", dy=0):
    """A thing on the map, unless it's there already (by its Id, if it has one)."""
    m, _, _ = w.at(gx, gy)
    pid = [t for t in extra.split() if t.startswith("Id=")]
    for ln in m.ents:
        f = ln.split("\t")
        if f[:2] == [kind, name] and (not pid or pid[0] in ln.split("\t")[-1].split()):
            return
    w.place(gx, gy, kind, name, extra, dy)


def clear(w, cells):
    for c in cells:
        t, over = W.parts(w.cell(*c))
        if over.get("Decor") and not W.PEAKY.match(t):
            w.set(c[0], c[1], decor="")


def footpath(w, goal, reach=60, most_water=2):
    """A footpath to goal from the nearest road within reach cells, unless it'd have to bridge more than most_water."""
    gx, gy = goal
    starts = [(x, y) for y in range(gy - reach, gy + reach + 1) for x in range(gx - reach, gx + reach + 1)
              if w.has(x, y) and W.is_road(w.cell(x, y))]
    if not starts:
        return "no road near"
    if goal in starts:
        return "on the road"
    path = W.find_way(w, starts, [goal], most=80000)
    if path is None:
        return "!! no way"
    wet = sum(1 for c in path if W.WATERY.match(W.parts(w.cell(*c))[0]))
    if wet > most_water:
        return "!! left out: it'd bridge %d tiles of water" % wet
    W.lay_way(w, path, wide=False)
    return "a path of %d" % len(path)


def can_walk(w, a, b):
    """Whether there's a way on foot from a to b (no bridging)."""
    def cost(c):
        text = w.cell(*c)
        if text is None:
            return None
        t, over = W.parts(text)
        if W.WATERY.match(t) or W.PEAKY.match(t):
            return None
        return 1.0
    seen, todo = {a}, collections.deque([a])
    while todo and len(seen) < 200000:
        c = todo.popleft()
        if c == b:
            return True
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c[0] + d[0], c[1] + d[1])
            if nb not in seen and cost(nb) is not None:
                seen.add(nb)
                todo.append(nb)
    return False


def place_all(w):
    out = []

    def at(mx, my, tx, ty):
        return cell(mx, my, tx, ty)

    # the Ringing Rocks
    stones = [(9, 11), (11, 10), (13, 9), (15, 10), (17, 11)]
    clear(w, [at(1, 7, x, y) for x in range(8, 19) for y in range(8, 14)])
    for n, (x, y) in enumerate(stones, 1):
        once(w, *at(1, 7, x, y), "StaticObject", "Ringing_Rock%d" % n)
    once(w, *at(1, 7, 13, 12), "NPC", "Stone_Ringer", "Attitude=Good Stand=1 Face=N Id=Tamsin Name=Tamsin", dy=-8)
    w.place_id(*at(1, 7, 13, 13), "Ringing_Rocks")
    out.append(("Ringing Rocks", footpath(w, at(1, 7, 13, 13))))

    # Abel's lambs
    abel = at(5, 9, 6, 5)
    once(w, *abel, "NPC", "Shepherd", "Attitude=Good Zone=4,4,8,6 Pause=5-12 Id=Shepherd_Abel Name=Abel", dy=-8)
    w.place_id(*at(5, 9, 6, 6), "Abels_Pasture")
    for n, (x, y) in enumerate(((20, 12), (2, 20), (16, 4)), 1):
        zone = "%d,%d,%d,%d" % (max(1, x - 2), max(1, y - 2), min(25, x + 2), min(21, y + 2))
        once(w, *at(5, 9, x, y), "NPC", "Stray_Lamb", "Attitude=Good Zone=%s Id=Stray_Lamb_%d" % (zone, n), dy=-8)
        if not can_walk(w, abel, at(5, 9, x, y)):
            out.append(("lamb %d" % n, "!! no way on foot from Abel"))
    out.append(("Abel's Pasture", footpath(w, at(5, 9, 6, 6))))

    # Hode's clearing
    clear(w, [at(6, 14, x, y) for x in range(18, 24) for y in range(13, 18)])
    once(w, *at(6, 14, 22, 15), "StaticObject", "Charcoal_Clamp")
    once(w, *at(6, 14, 20, 16), "NPC", "Collier", "Attitude=Good Zone=19,15,21,17 Pause=6-14 Id=Hode Name=Hode", dy=-8)
    w.place_id(*at(6, 14, 20, 17), "Collier_Clearing")
    out.append(("Collier's Clearing", footpath(w, at(6, 14, 20, 17))))

    # the Old Tollhouse
    clear(w, [at(2, 14, x, y) for x in range(11, 16) for y in range(6, 9)])
    once(w, *at(2, 14, 13, 6), "StaticObject", "Toll_Bar")
    once(w, *at(2, 14, 14, 7), "NPC", "Toll_Keeper", "Attitude=Good Stand=1 Face=N Id=Toll_Keeper_Ghost "
                                                     "Name=The_Toll-Keeper", dy=-8)
    w.place_id(*at(2, 14, 12, 7), "Old_Tollhouse")
    out.append(("Old Tollhouse", footpath(w, at(2, 14, 12, 7))))

    # Merrin's meadow
    clear(w, [at(-9, 10, x, y) for x in range(5, 15) for y in range(16, 21)])
    for x, y in ((6, 18), (8, 19), (13, 19)):
        m, _, _ = w.at(*at(-9, 10, x, y))
        if not any(ln.split("\t")[:2] == ["StaticObject", "Bee_Skep"] and ln.split("\t")[2:4] ==
                   [str((x - 1) * S), str((y - 1) * S)] for ln in m.ents):
            w.place(*at(-9, 10, x, y), "StaticObject", "Bee_Skep")
    once(w, *at(-9, 10, 10, 17), "NPC", "Beekeeper", "Attitude=Good Zone=8,16,12,18 Pause=6-14 Id=Merrin Name=Merrin",
         dy=-8)
    w.place_id(*at(-9, 10, 10, 18), "Merrins_Meadow")
    out.append(("Merrin's Meadow", footpath(w, at(-9, 10, 10, 18))))

    # the Fen Horn
    clear(w, [at(-7, 8, x, y) for x, y in (HORN_AT, COFFER_AT, (10, 4), (9, 4), (10, 6))])
    once(w, *at(-7, 8, *HORN_AT), "StaticObject", "Fen_Horn")
    w.place_id(*at(-7, 8, 10, 6), "Fen_Horn_Pool")
    out.append(("Fen Horn", footpath(w, at(-7, 8, 10, 6))))

    # Natter's corner
    clear(w, [at(-11, 4, x, y) for x, y in ((21, 14), (19, 18), (24, 20), (21, 15), (22, 15))])
    once(w, *at(-11, 4, 21, 14), "NPC", "Marsh_Witch", "Attitude=Good Zone=20,13,23,15 Pause=6-14 Id=Mother_Natter "
                                                       "Name=Mother_Natter", dy=-8)
    m = w.maps[(-11, 4)]
    for i, ln in enumerate(m.ents):                                   # (its Id was its sprite's name, once)
        f = ln.split("	")
        if f[:2] == ["NPC", "Frog_King"] and "Id=Frog_King" in f[-1].split():
            f[-1] = f[-1].replace("Id=Frog_King", "Id=Marsh_Frog_King")
            m.ents[i] = "	".join(f)
            w.touch(m)
    once(w, *at(-11, 4, 19, 18), "NPC", "Frog_King", "Attitude=Good Zone=18,17,21,19 Id=Marsh_Frog_King")
    once(w, *at(-11, 4, 24, 20), "StaticObject", "Heron_Nest")
    w.place_id(*at(-11, 4, 21, 15), "Natters_Corner")
    out.append(("Natter's Corner", footpath(w, at(-11, 4, 21, 15), reach=110, most_water=0)))

    # Pell, and the wraith that has his pick
    once(w, *at(-5, 8, 4, 14), "NPC", "Delver_Ghost", "Attitude=Good Stand=1 Face=E Id=Pell Name=Pell", dy=-8)
    w.place_id(*at(-5, 8, 4, 15), "Pells_Rest")
    m = w.maps[(-5, 8)]
    for i, ln in enumerate(m.ents):
        f = ln.split("\t")
        if f[:2] == ["NPC", "Tunnel_Wraith"] and "Id=" not in ln:
            f[-1] += " Id=Stoneways_Wraith"
            m.ents[i] = "\t".join(f)
            w.touch(m)

    # Salt Agnes, her bottles, and Tobin's cairn
    once(w, *at(0, 22, 12, 7), "NPC", "Beachcomber", "Attitude=Good Zone=10,6,15,8 Pause=6-14 Id=Salt_Agnes "
                                                     "Name=Salt_Agnes", dy=-8)
    w.place_id(*at(0, 22, 12, 8), "Agnes_Cove")
    for n, (mx, my, x, y) in enumerate(((0, 22, 20, 9), (0, 22, 8, 10), (1, 23, 17, 14)), 1):
        clear(w, [at(mx, my, x, y)])
        once(w, *at(mx, my, x, y), "StaticObject", "Message_Bottle", "Id=Castaway_Bottle_%d" % n)
    clear(w, [at(1, 23, 21, 13)])
    once(w, *at(1, 23, 21, 13), "StaticObject", "Castaway_Cairn")
    out.append(("Salt Agnes's Cove", footpath(w, at(0, 22, 12, 8))))

    # the Smugglers' Signal
    clear(w, [at(27, 12, x, y) for x, y in (PYRE_AT, MARRO_AT, (3, 8), (2, 9))])
    once(w, *at(27, 12, *PYRE_AT), "StaticObject", "Signal_Pyre")
    w.place_id(*at(27, 12, 3, 9), "Smugglers_Signal")
    out.append(("Smugglers' Signal", footpath(w, at(27, 12, 3, 9))))

    # the Ward-Circle
    cx, cy = 18, 12
    for i, (dx, dy) in enumerate(((0, -3), (2, -2), (3, 0), (2, 2), (0, 3), (-2, 2), (-3, 0), (-2, -2))):
        w.set(*at(21, 9, cx + dx, cy + dy), decor="Ward_Stone%03d" % (1 + i % 2))
    clear(w, [at(21, 9, cx, cy), at(21, 9, cx, cy + 1)])
    once(w, *at(21, 9, cx, cy), "StaticObject", "Ward_Plinth")
    w.place_id(*at(21, 9, cx, cy + 1), "Ward_Circle")

    # the ice-fishers' camp
    w.set(*at(18, 23, 12, 10), decor="Ice_Hole001")
    once(w, *at(18, 23, 12, 10), "StaticObject", "Salmon_Spot")
    once(w, *at(18, 23, 17, 10), "NPC", "Ice_Fisher", "Attitude=Good Stand=1 Face=W Id=Ulla Name=Ulla", dy=-8)
    once(w, *at(18, 23, 13, 16), "StaticObject", "Frozen_Wanderer")
    w.place_id(*at(18, 23, 16, 10), "Ice_Fishers_Camp")
    out.append(("Ice-Fishers' Camp", footpath(w, at(18, 23, 16, 10))))

    # the fairy rings
    for i, ((mx, my), (tx, ty)) in enumerate(RINGS, 1):
        c = at(mx, my, tx, ty)
        clear(w, [c])
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    w.set(c[0] + dx, c[1] + dy, decor="Toadstool001")
        once(w, *c, "StaticObject", "Fairy_Ring", "Id=Fairy_Ring_%d" % i)
    return out


def main():
    sounds()
    tiles()
    entities()
    scripts()
    w = W.World(0)
    for what, how in place_all(w):
        print("  %-20s %s" % (what, how))
    w.save()
    print("The wild places: done")


if __name__ == "__main__":
    main()
