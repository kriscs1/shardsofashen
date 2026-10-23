"""The old flat roofs (Roof001: one tile, the same all over the roof) made into proper ones: each roof (a group of
Roof001 cells) gets the pieces of a real roof (eaves, ridge, gable ends: <Material>_Roof001-015, the pieces worked out
from its shape as on the homesteads) in a material that suits the house's walls.

  python -I "Dev\\migrate\\fix_flat_roofs.py"          (only Roof001 roofs change; run it again: nothing to do)
"""
import collections
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dsengine.homes import roof_piece  # noqa: E402

XT, YT = 25, 21
OLD = "Roof001"
BY_WALL = [("Brick", "Clay"), ("Stone_Wall", "Slate"), ("Timber", "Thatch"), ("Plaster", "Thatch"),
           ("Sandstone", "Clay"), ("Wood", "Shingle")]
ROOF_RE = re.compile(r"\+Roof\(" + OLD + r"\.(\d+)\)")


def material(walls):
    for wall, _ in collections.Counter(walls).most_common():
        for prefix, mat in BY_WALL:
            if wall.startswith(prefix):
                return mat
    return "Shingle"


def fix(path):
    raw = open(path, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    rows = [lines[y].split(":") for y in range(YT)]
    groups = collections.defaultdict(set)
    for y in range(YT):
        for x in range(XT):
            m = ROOF_RE.search(rows[y][x]) if x < len(rows[y]) else None
            if m:
                groups[m.group(1)].add((x + 1, y + 1))
    if not groups:
        return 0
    for g, cells in groups.items():
        walls = []
        for x, y in cells:                                  # (the walls under the roof, and the front below it)
            for yy in (y, y + 1):
                if 1 <= yy <= YT and (x, yy) in cells or (x, yy - 1) in cells:
                    t = rows[yy - 1][x - 1].split("+")[0] if yy <= YT else ""
                    if t and not t.startswith(("Tile0", "Plank0", "Carpet", "Marble", "Stone0", "Door")):
                        walls.append(t)
        mat = material(walls)
        for x, y in cells:
            x1 = x
            while (x1 - 1, y) in cells:
                x1 -= 1
            x2 = x
            while (x2 + 1, y) in cells:
                x2 += 1
            y1 = y
            while (x, y1 - 1) in cells:
                y1 -= 1
            y2 = y
            while (x, y2 + 1) in cells:
                y2 += 1
            piece = roof_piece(mat, x, y, x1, y1, x2, y2)
            rows[y - 1][x - 1] = ROOF_RE.sub("+Roof(%s.%s)" % (piece, g), rows[y - 1][x - 1])
    for y in range(YT):
        lines[y] = ":".join(rows[y])
    open(path, "wb").write(nl.join(lines).encode("cp1252"))
    return len(groups)


def main():
    n = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "Maps", "*.txt"))):
        k = fix(path)
        if k:
            n += 1
            print("%s: %d roof%s" % (os.path.basename(path)[:-4], k, "" if k == 1 else "s"))
    print("%d maps had flat roofs" % n if n else "No flat roofs left")


if __name__ == "__main__":
    main()
