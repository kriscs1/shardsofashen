"""Small things to scatter anywhere (the owner's wish: more decor, little rocks and stones): stones in clusters (grey,
brown, dark), mossy stones, flat stepping stones, a lone pebble, shells for a beach, twigs and fallen leaves. Each a
see-through decor tile, walked over, with the 1 px dark outline (build_wolf.py's way); several looks of each, so a
family in the palette's Auto puts down one at random. The terrains they suit scatter a few (the meadow, the moor,
sand, the woodland, the marsh).

Safe to run again.

  python -I "dev\\migrate\\build_small_decor.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, read_lines, write_image, write_lines          # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

S = 32
OUTLINE = (34, 28, 24, 255)
STONES = {"Small_Stones": [(150, 146, 140), (128, 124, 120), (168, 164, 156)],
          "Brown_Stones": [(140, 112, 84), (122, 96, 72), (158, 128, 96)],
          "Dark_Stones": [(86, 84, 88), (72, 70, 76), (100, 98, 102)]}


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def outlined(im):
    a = im.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ring = Image.new("RGBA", im.size, OUTLINE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.paste(ring, (dx, dy), a)
    out.alpha_composite(im)
    return out


def stone(d, x, y, rx, ry, col, moss=False, rng=None):
    """A stone: lit on its top left, shaded under, moss on its top if it's mossy."""
    d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=col + (255,))
    d.ellipse((x - rx + 1, y - ry + 1, x, y), fill=clamp([c * 1.15 for c in col]) + (255,))
    d.line((x - rx + 1, y + ry - 1, x + rx - 1, y + ry - 1), fill=clamp([c * 0.72 for c in col]) + (255,))
    if moss:
        for i in range(rx * 2):
            if rng.random() < 0.7:
                d.point((x - rx + 1 + i, y - ry + rng.randint(0, 1)), fill=rng.choice([(86, 118, 56), (70, 100, 46)]))


def stones(kind, n):
    rng = random.Random("%s%d" % (kind, n))
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cols = STONES.get(kind, STONES["Small_Stones"])
    for _ in range(rng.randint(2, 4)):
        stone(d, rng.randint(8, 24), rng.randint(16, 26), rng.randint(2, 4), rng.randint(2, 3), rng.choice(cols),
              moss=kind == "Mossy_Stones", rng=rng)
    return outlined(im)


def flat_stone(n):
    rng = random.Random("flat%d" % n)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = rng.choice([(150, 144, 132), (136, 130, 120)])
    x, y = rng.randint(13, 19), rng.randint(17, 21)
    d.ellipse((x - 8, y - 4, x + 8, y + 4), fill=col + (255,))
    d.ellipse((x - 7, y - 4, x + 3, y), fill=clamp([c * 1.12 for c in col]) + (255,))
    d.line((x - 3, y - 1, x + 2, y + 1), fill=clamp([c * 0.75 for c in col]) + (255,))   # (a crack)
    return outlined(im)


def pebble(n):
    rng = random.Random("pebble%d" % n)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    stone(ImageDraw.Draw(im), rng.randint(10, 22), rng.randint(16, 24), 2, 2, rng.choice(STONES["Small_Stones"]))
    return outlined(im)


def shells(n):
    rng = random.Random("shell%d" % n)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(rng.randint(1, 3)):
        x, y = rng.randint(8, 24), rng.randint(14, 26)
        col = rng.choice([(236, 220, 200), (226, 196, 176), (214, 210, 220)])
        d.pieslice((x - 3, y - 3, x + 3, y + 3), 180, 360, fill=col + (255,))
        d.line((x, y - 3, x, y), fill=clamp([c * 0.75 for c in col]) + (255,))
    return outlined(im)


def twigs(n):
    rng = random.Random("twig%d" % n)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(rng.randint(2, 3)):
        x, y = rng.randint(6, 22), rng.randint(14, 26)
        dx, dy = rng.randint(5, 9), rng.randint(-3, 3)
        col = rng.choice([(110, 80, 50), (96, 70, 44)])
        d.line((x, y, x + dx, y + dy), fill=col + (255,))
        d.line((x + dx // 2, y + dy // 2, x + dx // 2 + 2, y + dy // 2 - 2), fill=col + (255,))
    return outlined(im)


def leaves(n):
    rng = random.Random("leaf%d" % n)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(rng.randint(3, 5)):
        x, y = rng.randint(6, 26), rng.randint(10, 28)
        col = rng.choice([(176, 112, 40), (196, 150, 52), (150, 76, 36), (120, 120, 40)])
        d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=col + (255,))
    return im                                            # (too small to outline: specks on the ground)


KINDS = [   # (name, how many looks, how it's drawn, what Examine says)
    ("Small_Stones", 4, lambda n: stones("Small_Stones", n), "A few small stones."),
    ("Brown_Stones", 3, lambda n: stones("Brown_Stones", n), "Brown stones, half sunk in the earth."),
    ("Dark_Stones", 3, lambda n: stones("Dark_Stones", n), "Dark stones, smooth and cold."),
    ("Mossy_Stones", 3, lambda n: stones("Mossy_Stones", n), "Stones with moss on their tops."),
    ("Flat_Stone", 2, flat_stone, "A flat stone, good for stepping on."),
    ("Pebble", 3, pebble, "A pebble."),
    ("Shells", 3, shells, "Shells, washed up."),
    ("Twigs", 3, twigs, "Twigs and bits of bark."),
    ("Fallen_Leaves", 3, leaves, "Fallen leaves."),
]
TERRAINS = {   # terrain: what it scatters of these (weights among its other decor)
    "Terrain_Meadow": "Small_Stones001*1,Pebble001*1,Flat_Stone001*0.4",
    "Terrain_Moor": "Small_Stones002*2,Mossy_Stones001*1.5,Dark_Stones001*1",
    "Terrain_Sand": "Shells001*1.5,Pebble002*1,Small_Stones003*0.5",
    "Terrain_Woodland": "Twigs001*3,Fallen_Leaves001*3,Mossy_Stones002*1.5",
    "Terrain_Marsh": "Mossy_Stones003*1,Twigs002*1",
}


# (on the minimap, the ground they lie on: specks of stone would dot it all over)
GROUND = {"Shells": "Sand001"}


def minimap_colours():
    path = p("dev", "Minimap Colours.txt")
    lines = read_lines(path)
    while lines and not lines[-1]:
        lines.pop()                                      # (the last line's ending, read as one more line)
    have = {ln.split("	")[0]: ln.split("	")[1] for ln in lines if "	" in ln}
    for kind, count, _, _ in KINDS:
        for n in range(1, count + 1):
            name = "%s%03d" % (kind, n)
            if name not in have:
                lines.append("%s	%s" % (name, have[GROUND.get(kind, "Grass001")]))
    write_lines(path, lines)


def main():
    tiles, sets = Ini(p("data", "Tiles.ini")), Ini(p("data", "TileSets.ini"))
    made = 0
    for kind, count, draw, words in KINDS:
        for n in range(1, count + 1):
            name = "%s%03d" % (kind, n)
            made += write_image(p("sprites", "Tiles", name + ".png"), draw(n))
            for k, v in (("Walkable.Data", "1" * 49), ("Show.Name", "0"), ("Use.Words", ""),
                         ("Examine.Info", words), ("Line.of.Sight", "1"), ("Layer", "Decor")):
                tiles.set(name, k, v)
    for terrain, add in TERRAINS.items():
        have = sets.get(terrain, "Decor", "")
        if have is not None and not any(a.split("*")[0] in have for a in add.split(",")):
            sets.set(terrain, "Decor", (have + "," if have else "") + add)
    tiles.save(p("data", "Tiles.ini"))
    sets.save(p("data", "TileSets.ini"))
    minimap_colours()
    print("Small decor: %d pictures written" % made)


if __name__ == "__main__":
    main()
