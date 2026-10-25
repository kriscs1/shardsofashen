"""Beds lying sideways: the tile-and-a-half bed (long_beds.py) turned a quarter round, so it matches - its head in one
tile, its foot in the near half of the tile beside it. Two ways round: the head on the left (Bed003, its foot Bed004
to the right) and on the right (Bed006, its foot Bed005 to the left). Built at home like the bed (Buildables.ini);
head and foot go up, come down and move in the editor together (BED_FEET in dsengine/homes.py and
dsedit/pages/maps.py). Run it again to draw them again.

  python -I "dev\\migrate\\sideways_beds.py"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402
from long_beds import long_bed, LONG  # noqa: E402

TILES = os.path.join(ROOT, "sprites", "Tiles")
HALF = LONG - 32                    # (the foot's width: 16 px into the tile beside the head)
# name: (what it is, which columns of its tile it fills - the walk grid's 7 across: 0 there, 1 free)
PIECES = {"Bed003": ("a bed lying sideways, its head on the left", "0000000"),
          "Bed004": ("the foot of a bed lying sideways, the bed to its left", "0001111"),
          "Bed005": ("the foot of a bed lying sideways, the bed to its right", "1111000"),
          "Bed006": ("a bed lying sideways, its head on the right", "0000000")}


def pictures():
    pygame.init()
    pygame.display.set_mode((1, 1))
    left = pygame.transform.rotate(long_bed(), 90)                  # (48 x 32: the head on the left)
    right = pygame.transform.flip(left, True, False)                # (the head on the right)
    pygame.image.save(left.subsurface((0, 0, 32, 32)).copy(), os.path.join(TILES, "Bed003.png"))
    foot = pygame.Surface((32, 32), pygame.SRCALPHA)
    foot.blit(left.subsurface((32, 0, HALF, 32)), (0, 0))              # (the near half of the tile to the right)
    pygame.image.save(foot, os.path.join(TILES, "Bed004.png"))
    foot = pygame.Surface((32, 32), pygame.SRCALPHA)
    foot.blit(right.subsurface((0, 0, HALF, 32)), (32 - HALF, 0))     # (the near half of the tile to the left)
    pygame.image.save(foot, os.path.join(TILES, "Bed005.png"))
    pygame.image.save(right.subsurface((HALF, 0, 32, 32)).copy(), os.path.join(TILES, "Bed006.png"))


def data():
    tiles = os.path.join(ROOT, "data", "Tiles.ini")
    builds = os.path.join(ROOT, "data", "Buildables.ini")
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    examine = ini.read("Bed001", "Examine.Info", "", tiles)
    for name, (piece, cols) in PIECES.items():
        if not ini.section(name, tiles):
            for k, v in (("Walkable.Data", cols * 7), ("Show.Name", "1"), ("Use.Words", "Sleep"),
                         ("Examine.Info", examine), ("Line.of.Sight", "1"), ("Layer", "Decor"), ("Piece", piece)):
                ini.write(name, k, v, tiles)
    for name, label in (("Bed003", "Bed, lying sideways (head on the left)"),
                        ("Bed006", "Bed, lying sideways (head on the right)")):
        if not ini.section(name, builds):
            for k in ("Kind", "Category", "Needs", "Level", "XP"):
                ini.write(name, k, ini.read("Bed001", k, "", builds), builds)
            ini.write(name, "Name", label, builds)
    text = open(colours, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in text else "\n"
    line = next((ln for ln in text.split(nl) if ln.startswith("Bed001\t")), "Bed001\t148 103 81")
    add = [line.replace("Bed001", n, 1) for n in PIECES if "\n%s\t" % n not in "\n" + text]
    if add:
        text = text.replace(line + nl, line + nl + nl.join(add) + nl, 1)
        open(colours, "wb").write(text.encode("cp1252"))


if __name__ == "__main__":
    pictures()
    data()
    print("Drew the beds lying sideways: Bed003-006")
