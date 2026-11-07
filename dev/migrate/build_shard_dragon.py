"""The dragon of Galaith, Shard-grown (the owner's wish: it should look what it is). The dragon is the devourer the first
king cut down, and Shards are scraps of it; eighteen years unfed behind its barrier, it has been eating what Shards it
could find, and they've grown back into it: crystal through its spine and shoulders, along its wing-arms and its tail,
tipping its horns, its belly's scales gone to Shard plate, violet light cracking through its black hide. Its eyes stay
a forge's. Drawn over build_galaith.py's dragon (the old one, half as big again and black), every frame from the
old Dragon's own, so a second run draws the same; direction 8 is 2 mirrored.

  python -I "dev\\migrate\\build_shard_dragon.py"      (then export_web_assets.py)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import story_kit as K  # noqa: E402
import build_galaith  # noqa: E402

MAKER = "build_shard_dragon.py"
NAME = "Galaith_Dragon"
CRYSTAL, LIT, DEEP, CORE, WHITE = (150, 110, 226), (214, 190, 255), (88, 58, 170), (232, 168, 255), (255, 250, 255)
OUTLINE = (20, 14, 30)
INFO = ("The dragon of Galaith: black as a coal, and Shard crystal grown through its hide like frost through a "
        "window. Its eyes are a forge. Its belly is a jewel box. It is hungry.")


def is_ember(c):
    r, g, b, a = c
    return a > 0 and r > 200 and 120 < g < 200 and b < 90


def body(s):
    """(the belly's middle, the top of the head) found on the picture, so every frame's crystal sits where its body is"""
    w, h = s.get_size()
    belly = [(x, y) for y in range(h // 2, h) for x in range(w) if is_ember(s.get_at((x, y)))]
    bx = sum(x for x, _ in belly) / len(belly)
    by = sum(y for _, y in belly) / len(belly)
    return bx, by, belly


def crystal(layer, x, y, h, lean, wide=3):
    """One Shard spike rising from x, y: lit on its left face, deep down its right edge."""
    pg = K.pg()
    tip = (x + lean, y - h)
    pg.draw.polygon(layer, CRYSTAL, [(x - wide, y), tip, (x + wide, y)])
    pg.draw.polygon(layer, LIT, [(x - wide, y), tip, (x - 1, y)])
    pg.draw.line(layer, DEEP, (x + wide, y), tip)
    layer.set_at((round(tip[0]), round(tip[1])), WHITE + (255,))


def crack(s, rng, x, y, steps, dx):
    """A crack of Shard light wandering through the hide (only over the hide itself)."""
    w, h = s.get_size()
    for _ in range(steps):
        if 0 <= x < w and 0 <= y < h:
            r, g, b, a = s.get_at((int(x), int(y)))
            if a > 0 and r < 90 and not is_ember((r, g, b, a)):
                s.set_at((int(x), int(y)), (CORE if rng.random() < 0.3 else CRYSTAL) + (255,))
        x += dx + rng.choice((-1, 0, 0, 1)) * 0.6
        y += rng.choice((0, 1, 1))


# (the crystal, from the belly's middle: (dx, dy, height, lean, width); left of the body as drawn, mirrored right)
PAIRED = [
    (-14, -30, 9, -2, 3), (-19, -27, 7, -3, 2),                     # (out of the shoulders, at the wings' roots)
    (-27, -36, 6, -2, 2), (-36, -41, 5, -2, 2), (-44, -45, 4, -1, 2),  # (along the wing-arms)
    (-9, -46, 5, -1, 2),                                            # (behind the horns)
    (-12, -6, 5, -3, 2),                                            # (its flanks)
]
SPINE = [(0, -24, 7, 0, 3)]                                         # (the back of the neck, between the shoulders)
TAIL = [(-26, 16, 6, -2, 2), (-34, 19, 5, -2, 2), (-40, 21, 4, -1, 2)]


def shard_grown(src, seed):
    pg = K.pg()
    s = src.copy()
    w, h = s.get_size()
    bx, by, belly = body(s)
    for x, y in belly:                                              # (the belly's scales, Shard plate now)
        r, g, b, a = s.get_at((x, y))
        s.set_at((x, y), (LIT if g > 170 else CRYSTAL if g > 150 else DEEP) + (255,))
    rng = random.Random(seed)
    for k in range(5):                                              # (light cracking through the hide)
        crack(s, rng, bx + rng.choice((-1, 1)) * rng.randint(8, 20), by - rng.randint(10, 34), rng.randint(6, 11),
              rng.choice((-0.5, 0.5)))
    layer = K.surface(w, h)
    spikes = list(SPINE) + list(TAIL)
    for dx, dy, hh, lean, wide in PAIRED:
        spikes += [(dx, dy, hh, lean, wide), (-dx, dy, hh, -lean, wide)]
    for dx, dy, hh, lean, wide in spikes:
        x, y = round(bx + dx), round(by + dy)
        if 0 <= x < w and 0 <= y < h and s.get_at((x, y))[3] > 0:  # (only where there's dragon to grow from)
            crystal(layer, x, y, hh, lean, wide)
    for y in range(h):                                              # (its horns' tips gone to crystal)
        for x in range(w):
            r, g, b, a = s.get_at((x, y))
            if a and y < by - 57 and abs(x - bx) < 18 and r > 60 and not is_ember((r, g, b, a)):
                s.set_at((x, y), (LIT if r > 80 else CRYSTAL) + (255,))
    s.blit(K.outlined(layer, OUTLINE), (0, 0))
    return s


def pictures():
    pg = K.pg()
    for f in "abc":
        two = shard_grown(build_galaith.big_dragon(K.load("Walk", "Dragon2%s" % f)), "dragon" + f)
        K.save("Walk", "%s2%s" % (NAME, f), two)
        K.save("Walk", "%s8%s" % (NAME, f), pg.transform.flip(two, True, False))
        if f == "a":
            K.save("Entities", NAME, two)


def main():
    pictures()
    K.section(K.ENTS, NAME, [("Examine.Info", INFO)])
    print("The dragon of Galaith, Shard-grown: 7 pictures")


if __name__ == "__main__":
    main()
