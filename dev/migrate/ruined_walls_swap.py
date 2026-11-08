"""Every old ruined wall on the maps (the single blocks Ruined_Wall001, tall, and Ruined_Wall002, low, laid as decor)
becomes the piece of its Join set (build_ruined_walls.py) that joins the ruined walls beside it, tall or low, so a run
is one wall. Run once (a second run finds no old blocks).

  python -I "dev\\migrate\\ruined_walls_swap.py"      (then build_minimaps.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_edit as W                                              # noqa: E402
from build_ruined_walls import name_of, OLD, SETS_                  # noqa: E402

DIRS = (("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0))
PIECES = {name_of(s, "".join(c for i, c in enumerate("NESW") if b >> i & 1)) for s in SETS_ for b in range(16)}


def decor(w, gx, gy):
    c = w.cell(gx, gy)
    return W.parts(c)[1].get("Decor", "") if c is not None else ""


def main():
    n = 0
    for z in sorted({int(f[:-4].split(",")[2]) for f in os.listdir(W.MAPS) if f.endswith(".txt") and f.count(",") == 2}):
        w = W.World(z)
        old = {}
        for (mx, my), m in w.maps.items():
            for y, row in enumerate(m.rows):
                for x, c in enumerate(row):
                    d = W.parts(c)[1].get("Decor", "")
                    if d in OLD:
                        old[(mx * W.XT + x, my * W.YT + y)] = d
        if not old:
            continue
        for (gx, gy), d in sorted(old.items()):
            mask = "".join(s for s, dx, dy in DIRS if (gx + dx, gy + dy) in old
                           or decor(w, gx + dx, gy + dy) in PIECES)
            w.set(gx, gy, decor=name_of("Ruined_Wall" if d == OLD[0] else "Ruined_Wall_Low", mask))
            n += 1
        print("level %d: %d ruined walls joined, %d maps" % (z, len(old), w.save()))
    if not n:
        print("No old ruined walls left: done already.")


if __name__ == "__main__":
    main()
