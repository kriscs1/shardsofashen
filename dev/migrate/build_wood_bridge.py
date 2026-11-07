"""The wooden bridge: a proper autotile set (the owner's wish), for every jetty, pier and plank bridge. A Join set
(TileSets.ini Wood_Bridge): each piece's deck runs on into the sides it joins (Joins=, NESW) and has a raised rail on
every side it doesn't: rail beam, turned posts, a toe-board, and the support beams' ends showing under the deck's edge
on the open sides, the water's shadow below. Boards run across the way you walk. The rails aren't walked through
(the outer column or row of the 7x7 walk mask), a landward end is simply left open (the migration joins it to the
land). Sixteen pieces (every mix of N, E, S, W; `Wood_Bridge_X001` the lone platform).

  python -I "dev\migrate\build_wood_bridge.py"      (then wood_bridges_swap.py once, export_web_assets.py, build_minimaps.py)

Safe to run again (it draws the same).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                          # noqa: E402
import story_kit as SK                             # noqa: E402
from build_crossings import S, TILES, SETS, new, save, shade, average, clamp   # noqa: E402
from PIL import ImageDraw                          # noqa: E402

BOARDS = [(150, 104, 58), (140, 95, 52), (158, 112, 64), (132, 90, 48), (146, 100, 56)]
BEAM = (96, 64, 34)
BEAM_DK = (58, 38, 20)
RAIL = (170, 122, 70)
WATER_SHADOW = (24, 44, 58)
SIDES = "NESW"


def name_of(mask):
    return "Wood_Bridge_%s001" % (mask or "X")


def deck(joined, rng):
    """Boards across the way it's walked (a run going east and west has them upright), each its own brown, butt joints that
    don't line up, a nail at each end."""
    im = new(BOARDS[0])
    d = ImageDraw.Draw(im)
    across_x = ("E" in joined or "W" in joined) and "N" not in joined and "S" not in joined
    for i in range(0, S, 8):
        c = rng.choice(BOARDS)
        if across_x:
            d.rectangle((i, 0, i + 6, S - 1), fill=c)
            d.line((i + 7, 0, i + 7, S - 1), fill=BEAM_DK)
            d.line((i, 0, i, S - 1), fill=shade(c, 1.12))
            j = rng.randint(6, 24)
            d.line((i + 1, j, i + 6, j), fill=BEAM_DK)
            for y in (3, S - 4):
                d.point((i + 3, y), fill=(60, 40, 24))
        else:
            d.rectangle((0, i, S - 1, i + 6), fill=c)
            d.line((0, i + 7, S - 1, i + 7), fill=BEAM_DK)
            d.line((0, i, S - 1, i), fill=shade(c, 1.12))
            j = rng.randint(6, 24)
            d.line((j, i + 1, j, i + 6), fill=BEAM_DK)
            for x in (3, S - 4):
                d.point((x, i + 3), fill=(60, 40, 24))
    return im


def post(d, x, y, big=False):
    w = 5 if big else 4
    d.rectangle((x, y, x + w, y + w + 1), fill=BEAM, outline=BEAM_DK)
    d.rectangle((x + 1, y + 1, x + w - 1, y + 2), fill=shade(RAIL, 1.1))


def rails(im, joined):
    d = ImageDraw.Draw(im)
    for side in SIDES:
        if side in joined:
            continue
        if side in "NS":
            y0 = 0 if side == "N" else S - 9
            # the support beams' ends showing past the deck's edge, and the water's shadow beyond
            if side == "S":
                d.rectangle((0, S - 3, S, S), fill=WATER_SHADOW)
                for x in range(2, S, 10):
                    d.rectangle((x, S - 4, x + 3, S - 1), fill=BEAM, outline=BEAM_DK)
            else:
                d.rectangle((0, 0, S, 1), fill=WATER_SHADOW)
            ty = y0 + (3 if side == "N" else 2)
            d.rectangle((0, ty + 3, S, ty + 5), fill=BEAM_DK)           # (the toe-board)
            d.rectangle((0, ty, S, ty + 2), fill=RAIL)                  # (the rail beam)
            d.line((0, ty, S, ty), fill=shade(RAIL, 1.2))
            for x in range(0, S, 10):
                post(d, x + 2, ty - 1)
        else:
            x0 = 0 if side == "W" else S - 9
            if side == "E":
                d.rectangle((S - 3, 0, S, S), fill=WATER_SHADOW)
                for y in range(2, S, 10):
                    d.rectangle((S - 4, y, S - 1, y + 3), fill=BEAM, outline=BEAM_DK)
            else:
                d.rectangle((0, 0, 1, S), fill=WATER_SHADOW)
            tx = x0 + (3 if side == "W" else 2)
            d.rectangle((tx + 3, 0, tx + 5, S), fill=BEAM_DK)
            d.rectangle((tx, 0, tx + 2, S), fill=RAIL)
            d.line((tx, 0, tx, S), fill=shade(RAIL, 1.2))
            for y in range(0, S, 10):
                post(d, tx - 1, y + 2)
    for a in "NS":                                                      # (a corner has its one big post)
        for b in "EW":
            if a not in joined and b not in joined:
                post(d, 1 if b == "W" else S - 8, 1 if a == "N" else S - 9, big=True)


def walk(joined):
    g = [["1"] * 7 for _ in range(7)]
    for side in SIDES:
        if side in joined:
            continue
        for k in range(7):
            if side == "N":
                g[0][k] = "0"
            elif side == "S":
                g[6][k] = "0"
            elif side == "W":
                g[k][0] = "0"
            else:
                g[k][6] = "0"
    return g


def piece(mask):
    rng = random.Random("wood_bridge")                                  # (the same boards in every piece: they run on)
    im = deck(mask, rng)
    rails(im, mask)
    return im


def main():
    tiles, sets = Ini(TILES), Ini(SETS)
    order = []
    for bits in range(16):
        mask = "".join(s for i, s in enumerate(SIDES) if bits >> i & 1)
        nm = name_of(mask)
        order.append(nm)
        im = piece(mask)
        save(nm, im)
        words = ("a wooden bridge: " + ("joined " + ", ".join(mask) if mask else "a lone platform"))
        for k, v in (("Walkable.Data", "".join("".join(r) for r in walk(mask))), ("Show.Name", "1"), ("Use.Words", ""),
                     ("Examine.Info", "A wooden bridge, its rails on posts over the water. It creaks."),
                     ("Line.of.Sight", "1"), ("Piece", words), ("Blend", "0"), ("Joins", mask or "-")):
            tiles.set(nm, k, v)
        SK.minimap_colour(nm, average(im))
    for k, v in (("Title", "wooden bridge"), ("Columns", "4"), ("Tiles", ",".join(order)), ("Kind", "Join")):
        sets.set("Wood_Bridge", k, v)
    tiles.save(TILES)
    sets.save(SETS)
    print("Wooden bridge: 16 pieces drawn, set Wood_Bridge")


if __name__ == "__main__":
    main()
