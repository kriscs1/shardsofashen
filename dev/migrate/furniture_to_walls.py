"""Furniture against the back wall: an inside wall (a *_Thin_Plank tile) is floor with the wall drawn along its edge, so
a bed in the row below it stood a whole floorboard out from the wall. Beds, bookshelves, chests, sacks, haystacks and
nests in the row below a back wall move up onto it (a bed's foot follows its head), and so do the work stations
(workbenches, ranges, furnaces, anvils, alchemy tables: objects, a tile up). Tables and chairs stay where they
are, with each other; ladders and hatches stay where they meet the floor above or below. Run it again: nothing to do.

  python -I "dev\\migrate\\furniture_to_walls.py"
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_isle import Map, XT, YT  # noqa: E402

MOVES = ("Bed001", "Bookshelf", "Coin_Chest", "Sacks", "Haystack", "Nest")
STATIONS = ("Workbench", "Range", "Furnace", "Anvil", "Alchemy_Table")     # (not a chest: what's left in one is
#                                                                           kept by where it stands)
BACK_WALL = re.compile(r"_Thin_Plank001$")          # (the wall along a room's top: 001; its corners are 008, 005)


def something_at(m, x, y):
    px, py = (x - 1) * 32, (y - 1) * 32
    for ln in m.ents:
        p = ln.split("\t")
        if len(p) >= 4 and p[0] in ("NPC", "StaticObject", "MapItem"):
            try:
                if abs(float(p[2]) - px) < 16 and abs(float(p[3]) + 8 - py) < 16:
                    return True
            except ValueError:
                pass
    return False


def main():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "maps", "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.count(",") != 2 or "_Thin_Plank001" not in open(path, "rb").read().decode("cp1252"):
            continue
        m = Map(name)
        changed = False
        for y in range(2, YT + 1):
            for x in range(1, XT + 1):
                d = m.decor(x, y)
                if not d or not d.startswith(MOVES) or not BACK_WALL.search(m.tile(x, y - 1)):
                    continue
                if m.decor(x, y - 1) or something_at(m, x, y - 1) or m.roofed(x, y) != m.roofed(x, y - 1):
                    continue
                m.set(x, y - 1, decor=d)
                if d == "Bed001":                        # (its foot comes up into where its head was)
                    m.set(x, y, decor="Bed002")
                    if y < YT and m.decor(x, y + 1) == "Bed002":
                        m.set(x, y + 1, decor="")
                else:
                    m.set(x, y, decor="")
                changed = True
                n += 1
        for i, ln in enumerate(m.ents):
            p = ln.split("\t")
            if len(p) < 4 or p[0] != "StaticObject" or p[1] not in STATIONS:
                continue
            try:
                px, py = float(p[2]), float(p[3])
            except ValueError:
                continue
            x, y = int(px) // 32 + 1, int(py + 8) // 32 + 1
            if y < 2 or not BACK_WALL.search(m.tile(x, y - 1)) or m.decor(x, y - 1) or something_at(m, x, y - 1):
                continue
            p[3] = "%d" % (py - 32)
            m.ents[i] = "\t".join(p)
            changed = True
            n += 1
        if changed:
            m.save()
    print("Furniture against the back wall: %d moved" % n)


if __name__ == "__main__":
    main()
