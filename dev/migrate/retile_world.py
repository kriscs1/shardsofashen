"""Every level of the world tiled again as the map editor tiles it now (the owner's wish, once the pieces for every
corner were made): the marsh varied (each plain Marsh001 one of build_marsh.py's tiles, by the Marsh terrain's
weights) and every coast and edge smoothed (dsedit/world.py smooth_corners: every corner whose two sides are the
land; water with land on three sides, ponds, lakes, marsh water, sand into grass), over every cell of every level.

Safe to run again (the same each time).

  python -I "dev\migrate\retile_world.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, h01                      # noqa: E402
from dsedit.project import Project                      # noqa: E402
from dsedit import world as WD                           # noqa: E402
from common import Ini, p                                # noqa: E402


def marsh_weights():
    tiles = Ini(p("data", "TileSets.ini")).get("Terrain_Marsh", "Tiles", "Marsh001")
    out = []
    for part in tiles.split(","):
        name, _, w = part.strip().partition("*")
        out.append((name.strip(), float(w or 1)))
    return out


def pick(weights, r):
    total = sum(w for _, w in weights)
    for name, w in weights:
        r -= w / total
        if r <= 0:
            return name
    return weights[-1][0]


def main():
    print("Superseded: the ground rounds itself now (round_world.py), no pieces laid.")
    return
    project = Project(W.ROOT)
    bases = {s["water"] for s in WD.shores(project)}
    weights = marsh_weights()
    report = []
    for z in sorted({lv[2] for lv in W.all_levels()}):
        w = W.World(z)
        marsh = cells = 0
        todo = set()
        for (mx, my), m in w.maps.items():
            for y in range(YT):
                for x in range(XT):
                    gx, gy = mx * XT + x, my * YT + y
                    t, over = W.parts(m.rows[y][x])
                    if t == "Marsh001":
                        n = pick(weights, h01("marsh", gx, gy))
                        if n != t:
                            w.put(gx, gy, W.join(n, over))
                            marsh += 1
                    todo.add((gx, gy))

        def put(x, y, name):
            t, over = W.parts(w.cell(x, y))
            w.put(x, y, W.join(name, over))
        cells = WD.smooth_corners(project, lambda x, y: w.tile(x, y), put, todo, reach=0) if bases else 0
        n = w.save()
        if marsh or cells or n:
            report.append("level %d: %d marsh tiles varied, %d pieces laid or taken up, %d maps" % (z, marsh, cells, n))
    print("\n".join(report) or "Nothing to change.")


if __name__ == "__main__":
    main()
