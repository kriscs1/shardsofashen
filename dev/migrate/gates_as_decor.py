"""Gates are decor, as the fences they stand in are: see-through (Wood_Gate001-004, drawn again without the grass
they used to have under them), Layer=Decor, over whatever ground is there - and so in the editor's Decor palette.
Doors work in the decor as on the ground (dsengine: world.py's doors, npcs.py nearest_door), and a gate built at
home before this is put right as the home loads (homes.py GATES). Run it again: nothing left to do.

  python -I "dev\\migrate\\gates_as_decor.py"

  * sprites\\Tiles\\Wood_Gate001-004: drawn again (build_isle_art.py's gate_across, gate_upright).
  * Tiles.ini: Layer=Decor on each. Buildables.ini: Kind=Decor.
  * Maps: a gate that's a cell's ground becomes its decor, over the ground most of its neighbours have.
"""
import collections
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from build_isle import Map, XT, YT  # noqa: E402

GATES = ("Wood_Gate001", "Wood_Gate002", "Wood_Gate003", "Wood_Gate004")


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    import build_isle_art as art
    tiles = os.path.join(ROOT, "sprites", "Tiles")
    for name, img in zip(GATES, (art.gate_across(False), art.gate_across(True), art.gate_upright(False),
                                 art.gate_upright(True))):
        pygame.image.save(img, os.path.join(tiles, name + ".png"))


def data():
    tiles, builds = os.path.join(ROOT, "data", "Tiles.ini"), os.path.join(ROOT, "data", "Buildables.ini")
    for g in GATES:
        ini.write(g, "Layer", "Decor", tiles)
        if ini.section(g, builds):
            ini.write(g, "Kind", "Decor", builds)


def maps():
    n = 0
    for path in glob.glob(os.path.join(ROOT, "maps", "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.count(",") != 2 or "Wood_Gate" not in open(path, "rb").read().decode("cp1252"):
            continue
        m = Map(name)
        changed = False
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                if m.tile(x, y) not in GATES or m.decor(x, y):
                    continue
                around = collections.Counter(m.tile(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                             if 1 <= x + dx <= XT and 1 <= y + dy <= YT
                                             and m.tile(x + dx, y + dy) not in GATES)
                ground = around.most_common(1)[0][0] if around else "Grass001"
                m.set(x, y, tile=ground, decor=m.tile(x, y))
                changed = True
                n += 1
        if changed:
            m.save()
    print("Gates are decor: %d on the maps moved off the ground" % n)


if __name__ == "__main__":
    pictures()
    data()
    maps()
