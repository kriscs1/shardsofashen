"""The pieces where two grounds meet on the slant: a coast's land in the corners of the water by it, and grass in the
corners of sand. Every way the corners can go (one, two, three or all four: water with land on three sides is two
corners), for the sea, for inland water (Lake001, new) and for sand meeting grass.

  * A piece says what it's made of (Tiles.ini Corner.Base: the ground it is; Corner.Land: the ground in its corners;
    Corner.Mask: which corners, NE,SE,SW,NW; Corner.Small=1: a shallow one). The game (ground.js) and the editor
    (render.py) paint it from those, the land from its own texture, so a marsh coast is the marsh it's beside.
    Corner.Leg: how far along the tile's sides its corners reach (one or two side by side: the whole side, the coast
    on the slant; three, four or two opposite: half, so the water's still a pool; a shallow single: SMALL). The
    pictures here are what the palette and the minimap see.
  * Its walk mask: the water's (none) with its land corners walkable; sand's all walkable.
  * TileSets.ini: each coast's set (Shore_<Land>) gets its pieces of more than one corner (Pieces=NE+NW:name,...);
    the lake's coasts (Shore_<Land>_Lake) and sand meeting grass (Edge_Sand_Grass) are new sets; the editor's Auto
    puts them down (dsedit/world.py smooth_corners). The terrains: water is the sea, and a lake (Terrain_Lake) is new.

Safe to run again (only what changed is written).

  python -I "dev\\migrate\\build_ground_pieces.py"
"""
import hashlib
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, write_image          # noqa: E402
import story_kit as SK                           # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

TW = 32
CORNERS = ("NE", "SE", "SW", "NW")
LANDS = {"Grass": "Grass001", "Marsh": "Marsh001", "Sand": "Sand001", "Snow": "Snow001"}
SEA, LAKE = "Water001", "Lake001"
SMALL = 0.68                                     # (a shallow corner's legs, of a tile)
POOL = 0.55                                      # (three or four corners, or two opposite: the water left a pool)
TILES, SETS = p("data", "Tiles.ini"), p("data", "TileSets.ini")


def masks(least=1):
    return [m for n in range(least, 5) for m in combinations(CORNERS, n)]


def leg_of(mask, small):
    if small:
        return SMALL
    opposite = ("NE" in mask and "SW" in mask) or ("NW" in mask and "SE" in mask)
    return POOL if len(mask) >= 3 or opposite else 1.0


def name_of(prefix, base_word, mask, small=False):
    return "%s_%s_%s%s001" % (prefix, base_word, "_".join(mask), "_Small" if small else "")   # (a variant number, as
                                                                                                  #  every tile has)


# ================================================================== pictures
def ground(tiles, name):
    """A ground tile's picture: its part of its big texture at the top left (Texture=), else its own sprite."""
    tex = tiles.get(name, "Texture", "")
    if tex and os.path.exists(p("sprites", "Textures", tex + ".png")):
        return Image.open(p("sprites", "Textures", tex + ".png")).convert("RGBA").crop((0, 0, TW, TW))
    out = Image.new("RGBA", (TW, TW), (0, 0, 0, 255))
    pic = Image.open(p("sprites", "Tiles", name + ".png")).convert("RGBA")
    out.alpha_composite(pic.crop((0, 0, TW, TW)))
    return out


def corner_points(corner, leg, seed):
    """The corner's triangle, its legs leg of a tile, its long side a little rough (as ground.js cornerPath draws it)."""
    leg = TW * leg
    cx, cy = {"NE": (TW, 0), "SE": (TW, TW), "SW": (0, TW), "NW": (0, 0)}[corner]
    sx, sy = (-1 if cx else 1), (1 if cy == 0 else -1)
    a, b = (cx + sx * leg, cy), (cx, cy + sy * leg)
    pts = [(cx, cy), a]
    for i in range(1, 6):
        t = i / 6.0
        h = int(hashlib.md5(("%s%d%s" % (seed, i, corner)).encode()).hexdigest(), 16) % 5 - 2
        pts.append((a[0] + (b[0] - a[0]) * t + h * 0.7, a[1] + (b[1] - a[1]) * t + h * 0.7))
    pts.append(b)
    return pts


def compose(tiles, base, land, mask, small, seed):
    out = ground(tiles, base)
    cut = Image.new("L", (TW, TW), 0)
    d = ImageDraw.Draw(cut)
    for c in mask:
        d.polygon(corner_points(c, leg_of(mask, small), seed), fill=255)
    out.paste(ground(tiles, land), (0, 0), cut)
    return out, cut


def walk_of(cut, base_walk):
    """The 7 x 7 walk mask: the base's, and walkable wherever the corner's land is."""
    out = []
    for i in range(49):
        x, y = int((i % 7 + 0.5) * TW / 7), int((i // 7 + 0.5) * TW / 7)
        out.append("1" if base_walk[i] == "1" or cut.getpixel((x, y)) > 127 else "0")
    return "".join(out)


def lake_water():
    """Lake001: still fresh water, greener and darker than the sea (no marks of its own: they'd show the grid)."""
    sea = Image.open(p("sprites", "Tiles", SEA + ".png")).convert("RGB")
    out = Image.new("RGB", sea.size)
    px = out.load()
    for y in range(sea.size[1]):
        for x in range(sea.size[0]):
            r, g, b = sea.getpixel((x, y))
            l = (r + g + b) / 3.0
            px[x, y] = (int(18 + l * 0.22), int(58 + l * 0.42), int(70 + l * 0.38))
    return out.convert("RGBA")


def average(im):
    small = im.convert("RGB").resize((1, 1), Image.BOX)
    return small.getpixel((0, 0))


# ================================================================== data
def kinds(sets):
    """Every family of pieces: (set name, title, base, land, prefix, base word, walk of the base, the singles there
    are already {(corner, small): name}, the keys every piece of it has)."""
    out = []
    for word, land in LANDS.items():
        old = {}
        info = {k: v for k, v in (sets.section("Shore_" + word) or ["", []])[1] if k}
        for key, small in (("Corners", False), ("Small", True)):
            for part in info.get(key, "").split(","):
                if ":" in part:
                    c, n = part.split(":", 1)
                    old[(c.strip(), small)] = n.strip()
        out.append(("Shore_" + word, "%s coast: diagonal pieces" % word.lower(), SEA, land, word, "Water", "0" * 49,
                    old, [("Water", "1"), ("Show.Name", "0"), ("Use.Words", ""), ("Line.of.Sight", "1")]))
        out.append(("Shore_%s_Lake" % word, "%s by a lake: diagonal pieces" % word.lower(), LAKE, land, word, "Lake",
                    "0" * 49, {}, [("Water", "1"), ("Show.Name", "0"), ("Use.Words", ""), ("Line.of.Sight", "1"),
                                   ("Examine.Info", "Still water at the edge of the %s." % word.lower())]))
    out.append(("Edge_Sand_Grass", "sand meets grass: diagonal pieces", "Sand001", "Grass001", "Sand", "Grass",
                "1" * 49, {}, [("Show.Name", "0"), ("Use.Words", "Walk here,Dig"), ("Walk.Speed", "0.8"),
                               ("Blend", "3"), ("Blend.Texture", "Sand001"), ("Line.of.Sight", "1")]))
    return out


def main():
    tiles, sets = Ini(TILES), Ini(SETS)
    made = 0
    if write_image(p("sprites", "Tiles", LAKE + ".png"), lake_water()):
        made += 1
    for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "0"), ("Use.Words", ""), ("Line.of.Sight", "1"),
                 ("Blend", "1"), ("Blend.Texture", LAKE), ("Water", "1"),
                 ("Examine.Info", "Still fresh water, deep and green.")):
        tiles.set(LAKE, k, v)
    SK.minimap_colour(LAKE, average(lake_water()))
    for set_name, title, base, land, prefix, word, base_walk, old, keys in kinds(sets):
        singles, smalls, pieces, names = [], [], [], []
        for mask in masks():
            for small in ((False, True) if len(mask) == 1 else (False,)):
                name = old.get((mask[0], small)) if len(mask) == 1 else None
                fresh = name is None
                name = name or name_of(prefix, word, mask, small)
                pic, cut = compose(tiles, base, land, mask, small, name)
                if fresh:
                    if write_image(p("sprites", "Tiles", name + ".png"), pic):
                        made += 1
                    SK.minimap_colour(name, average(pic))
                    for k, v in keys:
                        tiles.set(name, k, v)
                    tiles.set(name, "Walkable.Data", walk_of(cut, base_walk))
                for k, v in (("Corner.Base", base), ("Corner.Land", land), ("Corner.Mask", ",".join(mask)),
                             ("Corner.Leg", "%g" % leg_of(mask, small))):
                    tiles.set(name, k, v)
                tiles.remove(name, "Corner.Small")
                names.append(name)
                if len(mask) == 1:
                    (smalls if small else singles).append("%s:%s" % (mask[0], name))
                else:
                    pieces.append("%s:%s" % ("+".join(mask), name))
        have = {k: v for k, v in (sets.section(set_name) or ["", []])[1] if k}
        for k, v in (("Title", have.get("Title", title)), ("Columns", "4"), ("Tiles", ",".join(names)),
                     ("Kind", "Shore"), ("Land", land), ("Water", base), ("Corners", ",".join(singles)),
                     ("Small", ",".join(smalls)), ("Pieces", ",".join(pieces))):
            sets.set(set_name, k, v)
    sets.set("Terrain_Water", "Title", "sea")
    if sets.section("Terrain_Lake") is None:
        for k, v in (("Title", "lake (inland water)"), ("Kind", "Terrain"), ("Tiles", LAKE),
                     ("Decor", "Lily_Pads001*3"), ("Decor.Density", "6"), ("Water", "1")):
            sets.set("Terrain_Lake", k, v)
    tiles.save(TILES)
    sets.save(SETS)
    print("Ground pieces: %d pictures written" % made)


if __name__ == "__main__":
    main()
