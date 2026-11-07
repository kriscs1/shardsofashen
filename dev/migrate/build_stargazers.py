"""The Stargazers' Ring (the owner's wish: map 22,4,0, tile 13,16): in the hidden grass valley in the Cinder Peaks east
of the Wizards' Court, where the Court's first wizards watched the sky before they had a tower. A ring of six standing
stones (three carvings, each its own words) on the grass, and in the middle the old brass glass on its stand: Look
Through it, more than once. A footpath from the end of the Court's east road. On the world map; needed by no quest. Its Shards are in Shards.ini [Shards] (Stargazers.Glass).

Run after the owner's clearing of the valley (it's on the maps). Safe to run again.

  python -I "dev\\migrate\\build_stargazers.py"   (then build_minimaps.py, export_web_assets.py)
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import Ini, p, write_image           # noqa: E402
import story_kit as SK                           # noqa: E402
import world_edit as W                           # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

MAKER = "build_stargazers.py"
S = 32
SOLID = "1111111111111111000111100011110001111111111111111"   # (the foot of it, in its cell's middle)
OUTLINE = (24, 20, 14, 255)

MAP = (22, 4)
GLASS = (13, 16)                                               # (the map's own tiles, as the editor counts them)
STONES = [((13, 14), 1), ((15, 15), 2), ((15, 17), 3), ((13, 18), 1), ((11, 17), 2), ((11, 15), 3)]
ROAD_END = (21, 4, 22, 15)                                     # (the Court's east road: map x, y, tile x, y)
WAY_IN = (12, 15)                                              # (the gap in the ring the path comes in by)
SHARDS = [("Stargazers.Glass", "8")]


def cell(mx, my, tx, ty):
    """A map's tile (counted from 1) as a world cell."""
    return mx * W.XT + tx - 1, my * W.YT + ty - 1


# ------------------------------------------------------------------ pictures
def new(w=S, h=S):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def outlined(im):
    out = im.copy()
    a, px = im.load(), out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if a[x, y][3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + dx < w and 0 <= y + dy < h and a[x + dx, y + dy][3]:
                    px[x, y] = OUTLINE
                    break
    return out


def star_stone(n):
    """A tall pale stone, squared off by hand long ago, lit on its west; drilled with stars (n: which)."""
    rng = random.Random("star_stone%d" % n)
    im = new()
    d = ImageDraw.Draw(im)
    top = (4, 2, 6)[n - 1]
    d.polygon([(10, 30), (22, 30), (21, top + 3), (18, top), (13, top + 1), (11, top + 4)], fill=(150, 146, 136, 255))
    px = im.load()
    for y in range(S):
        for x in range(S):
            if px[x, y][3]:
                c = (150, 146, 136) if x < 16 else (112, 108, 102)    # (lit on the west, in shadow on the east)
                if rng.random() < 0.18:
                    c = tuple(int(v * rng.uniform(0.88, 1.06)) for v in c)
                if y > 25 and rng.random() < 0.4:
                    c = (98, 104, 70)                                 # (the grass and lichen at its foot)
                px[x, y] = c + (255,)
    holes = {1: [(13, 9), (15, 11), (17, 10), (19, 13), (16, 15), (14, 18), (18, 19)],
             2: [(13, 8), (15, 7), (17, 8), (19, 9), (14, 12), (18, 12), (16, 14)],
             3: []}[n]
    for x, y in holes:                                                # (the stars, drilled)
        px[x, y] = (58, 56, 54, 255)
        if x + 1 < S and px[x + 1, y][3]:
            px[x + 1, y] = (176, 172, 162, 255)
    if n == 2:
        px[16, 17] = (128, 124, 116, 255)                             # (an eighth, filled in again)
    if n == 3:
        for y in range(9, 26):                                        # (worn smooth where backs leaned on it)
            for x in range(17, 21):
                if px[x, y][3]:
                    px[x, y] = (128, 124, 118, 255)
    out = outlined(im)
    sh = new()                                                        # (its shadow, east of it on the grass)
    ImageDraw.Draw(sh).polygon([(22, 30), (28, 30), (26, 26), (22, 26)], fill=(16, 14, 10, 96))
    return Image.alpha_composite(sh, out)


def glass():
    """The brass glass on its iron stand, pointed up at the west sky: green at the joints."""
    im = new()
    d = ImageDraw.Draw(im)
    iron = (52, 50, 54, 255)
    for foot in ((8, 30), (16, 31), (24, 30)):                        # (the stand's three legs)
        d.line((16, 17) + foot, fill=iron, width=1)
    d.line((15, 17, 17, 17), fill=iron)
    tube = [(6, 6), (8, 4), (25, 15), (23, 18)]                       # (the tube, its wide end low and east)
    d.polygon(tube, fill=(176, 136, 62, 255))
    d.line((7, 5, 24, 16), fill=(226, 190, 104, 255))                  # (the light along its top)
    d.line((8, 7, 23, 17), fill=(132, 98, 44, 255))
    d.polygon([(22, 14), (25, 12), (28, 17), (24, 19)], fill=(150, 112, 50, 255))   # (the lens end)
    d.point((26, 15), fill=(150, 196, 220, 255))                      # (the lens, catching the sky)
    for x, y in ((12, 9), (18, 13), (16, 16)):
        d.point((x, y), fill=(84, 140, 108, 255))                     # (verdigris at the joints)
    d.ellipse((4, 3, 8, 7), fill=(120, 90, 40, 255))                  # (the eyepiece)
    out = outlined(im)
    sh = new()
    ImageDraw.Draw(sh).ellipse((9, 27, 27, 32), fill=(16, 14, 10, 80))
    return Image.alpha_composite(sh, out)


def average(im):
    return Image.alpha_composite(Image.new("RGBA", im.size, (88, 112, 56, 255)), im).convert("RGB").resize(
        (1, 1), Image.BOX).getpixel((0, 0))


# ------------------------------------------------------------------ data
STONE_WORDS = {
    1: "A standing stone, drilled with the stars of the Ferryman, every one where it should be. Somebody checked.",
    2: "A standing stone with the Crown cut in it, seven holes. An eighth has been drilled, and filled in again.",
    3: "A standing stone, worn smooth on the side that faces the glass. People sat with their backs to it for years.",
}


def tiles():
    t = Ini(p("data", "Tiles.ini"))
    for n, words in STONE_WORDS.items():
        name = "Star_Stone%03d" % n
        pic = star_stone(n)
        write_image(p("sprites", "Tiles", name + ".png"), pic, decor=True)
        for k, v in (("Walkable.Data", SOLID), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", words),
                     ("Line.of.Sight", "1"), ("Layer", "Decor")):
            t.set(name, k, v)
        SK.minimap_colour(name, average(pic))
    t.save(p("data", "Tiles.ini"))


def entities():
    e = Ini(p("data", "Entities.ini"))
    write_image(p("sprites", "Entities", "Star_Glass.png"), glass())
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Look Through,Examine"), ("Solid", "1"),
                 ("Examine.Info", "A long brass glass on an iron stand, green at the joints and pointed where it's "
                                  "always been pointed. The Court's mark is on the eyepiece.")):
        e.set("Star_Glass", k, v)
    e.save(p("data", "Entities.ini"))
    s = Ini(p("data", "Shards.ini"))
    if s.get("Shards", "Stargazers.Glass") is None:
        s.section("Shards")[1].append((None, "; Stargazers.*: what the Stargazers' Ring gives, once (build_stargazers.py)."))
    for k, v in SHARDS:
        s.set("Shards", k, v, overwrite=False)
    s.save(p("data", "Shards.ini"))


def scripts():
    SK.write_script("Look Through Star_Glass", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.StarGlass<3", "@spent"),
        ("Update.Attribute", "StarGlass", "+1"),
        (">Conditional", "$Attr.StarGlass<3", "@seen"),
        (">Conditional", "$Attr.StarGlass<2", "@again"),
        ("Display.Message", "Cyan", "You put your eye to the brass. It's pointed low, west, at the Court: you can count "
                                    "the slates on its tower, and the wizard up there who thinks nobody can see him."),
        ("End",),
        ("@again",),
        ("Display.Message", "Cyan", "You tilt it up. It sticks, the way old brass does, and goes no higher than one "
                                    "patch of sky with nothing in it. You look a long while anyway."),
        ("End",),
        ("@seen",),
        ("Play.Sound", "Absorb"),
        ("Give.Item", "Shard", "$Shards.Stargazers.Glass"),
        ("Display.Message", "Yellow", "Something in the empty patch winks back. The glass goes warm against your eye, "
                                      "and a thread of light runs down it and into you.", "-"),
        ("End",),
        ("@spent",),
        ("Display.Message", "Cyan", "Just sky. Whatever winked has had its look at you."),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    SK.place_label("Places", "The Stargazers' Ring", "Stargazers_Ring")


# ------------------------------------------------------------------ the map
def the_ring(w):
    mx, my = MAP
    gx, gy = cell(mx, my, *GLASS)
    stones = {cell(mx, my, *t): n for t, n in STONES}
    for y in range(gy - 3, gy + 4):                                   # (the ring cleared of what grew in it)
        for x in range(gx - 3, gx + 4):
            t, over = W.parts(w.cell(x, y))
            if W.PEAKY.match(t) or (x, y) in stones:
                continue
            if (x - gx) ** 2 + (y - gy) ** 2 <= 5:
                w.set(x, y, decor="")
    path = W.find_way(w, [cell(*ROAD_END)], [cell(mx, my, *WAY_IN)], avoid=frozenset(stones))
    if path is None:
        print("  !! no way from the Court's road to the ring")
    else:
        W.lay_way(w, path, wide=False)
    for c, n in stones.items():
        w.set(c[0], c[1], decor="Star_Stone%03d" % n)
    m, _, _ = w.at(gx, gy)
    if not any(ln.split("\t")[:2] == ["StaticObject", "Star_Glass"] for ln in m.ents):
        w.place(gx, gy, "StaticObject", "Star_Glass")
    w.place_id(gx, gy + 1, "Stargazers_Ring")
    return len(path or [])


def main():
    tiles()
    entities()
    scripts()
    w = W.World(0)
    n = the_ring(w)
    w.save()
    print("The Stargazers' Ring: done (a path of %d tiles to it)" % n)


if __name__ == "__main__":
    main()
