"""Mirror Tarn (grow_isle.py) is inland water: Lake001 (build_ground_pieces.py), its shore's pieces laid as the map
editor lays them (dsedit/world.py smooth_corners), not the sea's.

Safe to run again.

  python -I "dev\\migrate\\tarn_to_lake.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import world_edit as W                                   # noqa: E402
from dsedit.project import Project                      # noqa: E402
from dsedit import world as WD                           # noqa: E402

BOX = (48, -24, 72, -6)                                 # (round the tarn, on 1,-2 and 2,-2 / 2,-1)


def main():
    print("Superseded: the ground rounds itself now (round_world.py), no pieces laid.")
    return
    w = W.World(0)
    _, at = w.find_id("Mirror_Tarn")
    water = {(gx, gy) for gx in range(BOX[0], BOX[2] + 1) for gy in range(BOX[1], BOX[3] + 1)
             if w.cell(gx, gy) is not None and W.watery(w.cell(gx, gy))}
    for gx, gy in water:
        t, over = W.parts(w.cell(gx, gy))
        if not (t.startswith("Lake") or "_Lake_" in t):          # (the sea's: lake water now)
            w.put(gx, gy, W.join("Lake001", over))

    def put(x, y, name):
        t, over = W.parts(w.cell(x, y))
        w.put(x, y, W.join(name, over))
    n = WD.smooth_corners(Project(W.ROOT), lambda x, y: w.tile(x, y), put, water)
    print("Mirror Tarn (by %s): %d cells of lake water, %d shore pieces; %d maps changed" % (at, len(water), n, w.save()))


if __name__ == "__main__":
    main()
