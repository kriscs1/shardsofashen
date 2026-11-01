"""Marsh as varied tiles, not one texture (the owner's wish), its own murky water, and the mosquitoes over it.

  * Marsh001-010: wet olive ground, each with its own feature kept in from its edges (a mud patch, a puddle, moss,
    tussocks, sedge; Marsh001 plain), so any two meet without a seam; the Marsh terrain mixes them by weight (common
    plain, rarer pools) and nowhere looks like a grid. Marsh001 has no Texture= any more (build_terrain.py's marsh
    texture is left unused).
  * Bog001: marsh water, brown-green and still, scum on it; its coasts (build_ground_pieces.py: Shore_Marsh_Bog,
    Shore_Grass_Bog); the Bog terrain (lily pads, reeds standing in it, mosquitoes).
  * The Mosquito (Entities.ini; build_mosquito.py draws it): the Marsh and Bog terrains scatter them.

Safe to run again.

  python -I "dev\\migrate\\build_marsh.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, write_image          # noqa: E402
import story_kit as SK                           # noqa: E402

from PIL import Image                            # noqa: E402

S = 32
TILES, SETS = p("data", "Tiles.ini"), p("data", "TileSets.ini")
GROUND = [(71, 73, 42), (85, 97, 50), (81, 94, 47), (89, 100, 52), (75, 85, 44), (80, 88, 47)]
MUD = [(58, 54, 34), (66, 60, 38), (52, 48, 32)]
POOL = [(46, 62, 58), (52, 68, 62), (42, 56, 52)]
BLADES = [(104, 122, 58), (118, 132, 64), (92, 110, 50), (128, 128, 70)]
VARIANTS = [   # (what's on it, its weight in the terrain)
    ("plain", 8), ("tussocks", 3), ("mud", 2), ("pool", 1.2), ("moss", 2), ("sedge", 2.5), ("mud tussocks", 1.5),
    ("puddles", 1), ("plain", 4), ("tussocks", 2)]


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def ground(rng):
    """The wet olive ground every tile shares: the same speckle everywhere, so edges never show."""
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = rng.choice(GROUND)
    return im


def blob(rng, cx, cy, rx, ry):
    """The cells of a rough oval (its edge nibbled)."""
    out = []
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1 - rng.random() * 0.25 and 2 <= x < S - 2 and 2 <= y < S - 2:
                out.append((x, y))
    return out


def tuft(px, rng, x, y, cols=BLADES):
    base = rng.choice(cols)
    for _ in range(rng.randint(3, 6)):
        dx, h, lean = rng.randint(-2, 2), rng.randint(2, 5), rng.choice((-1, 0, 0, 1))
        for k in range(h):
            xx, yy = x + dx + (lean if k >= h // 2 else 0), y - k
            if 1 <= xx < S - 1 and 1 <= yy < S - 1:
                px[xx, yy] = clamp([c * (0.8 + 0.3 * k / h) for c in base])


def marsh_tile(kind, seed):
    rng = random.Random(seed)
    im = ground(rng)
    px = im.load()
    if "mud" in kind:
        for x, y in blob(rng, rng.randint(11, 21), rng.randint(11, 21), rng.randint(6, 9), rng.randint(4, 7)):
            px[x, y] = rng.choice(MUD)
    if kind == "moss":
        for x, y in blob(rng, rng.randint(12, 20), rng.randint(12, 20), rng.randint(6, 10), rng.randint(5, 8)):
            px[x, y] = clamp([c * 0.82 for c in rng.choice(GROUND)])
    if kind in ("pool", "puddles"):
        pools = [(rng.randint(12, 20), rng.randint(12, 20), rng.randint(5, 7), rng.randint(3, 5))] if kind == "pool" \
            else [(rng.randint(7, 12), rng.randint(8, 13), 3, 2), (rng.randint(19, 25), rng.randint(18, 24), 3, 2)]
        for cx, cy, rx, ry in pools:
            cells = set(blob(rng, cx, cy, rx, ry))
            for x, y in cells:
                rim = any((x + i, y + j) not in cells for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                px[x, y] = (96, 108, 74) if rim else rng.choice(POOL)
            for x, y in cells:                                   # (a glint under its top edge)
                if (x, y - 1) not in cells and (x, y + 1) in cells:
                    px[x, y + 1] = (82, 102, 94)
    if "tussocks" in kind:
        for _ in range(rng.randint(2, 4)):
            tuft(px, rng, rng.randint(5, 27), rng.randint(8, 28))
    if kind == "sedge":
        x, y = rng.randint(10, 22), rng.randint(14, 26)
        for _ in range(3):
            tuft(px, rng, x + rng.randint(-4, 4), y + rng.randint(-3, 3))
    return im.convert("RGBA")


def bog():
    """Bog001: still marsh water, brown-green, flecks of scum (no marks that would show the grid)."""
    rng = random.Random("bog")
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = rng.choice([(48, 58, 40), (52, 62, 42), (46, 54, 38), (50, 60, 44)])
    for _ in range(6):
        px[rng.randrange(S), rng.randrange(S)] = (82, 92, 58)
    return im.convert("RGBA")


def average(im):
    return im.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))


def main():
    tiles, sets = Ini(TILES), Ini(SETS)
    keys = [(k, v) for k, v in (tiles.section("Marsh001") or ["", []])[1] if k and k not in ("Texture", "Blend.Texture")]
    keys.append(("Blend.Texture", "Marsh001"))           # (its edge over lower ground is marsh, not grass)
    tiles.remove("Marsh001", "Texture")
    made, weights = 0, []
    for i, (kind, w) in enumerate(VARIANTS, 1):
        name = "Marsh%03d" % i
        pic = marsh_tile(kind, name)
        made += write_image(p("sprites", "Tiles", name + ".png"), pic)
        for k, v in keys:
            tiles.set(name, k, v)
        SK.minimap_colour(name, average(pic))
        weights.append("%s*%g" % (name, w))
    pic = bog()
    made += write_image(p("sprites", "Tiles", "Bog001.png"), pic)
    for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "0"), ("Use.Words", ""), ("Line.of.Sight", "1"),
                 ("Blend", "1"), ("Blend.Texture", "Bog001"), ("Water", "1"),
                 ("Examine.Info", "Brown, still marsh water. Something hums over it.")):
        tiles.set("Bog001", k, v)
    SK.minimap_colour("Bog001", average(pic))
    sets.set("Terrain_Marsh", "Tiles", ",".join(weights))
    ents = sets.get("Terrain_Marsh", "Entities", "")
    if "Mosquito" not in ents:
        sets.set("Terrain_Marsh", "Entities", (ents + "," if ents else "") + "Mosquito*1.5")
    if sets.section("Terrain_Bog") is None:
        for k, v in (("Title", "bog (marsh water)"), ("Kind", "Terrain"), ("Tiles", "Bog001"),
                     ("Decor", "Lily_Pads001*3,Reeds001*4"), ("Decor.Density", "10"), ("Entities", "Mosquito*1"),
                     ("Entities.Density", "0.4"), ("Water", "1")):
            sets.set("Terrain_Bog", k, v)
    tiles.save(TILES)
    sets.save(SETS)
    print("Marsh: %d pictures written" % made)


if __name__ == "__main__":
    main()
