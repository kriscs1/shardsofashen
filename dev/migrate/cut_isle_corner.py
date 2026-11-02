"""The Isle's north-east corner cut away (the owner's wish: it looked too much like a box): the coast comes down on the
slant, wandering, from just east of the little bay on the north coast to where the east coast already slants in above
the cottage, a beach along it, and the sea where the corner was.

  * The Tin Braes keep their place. Tin rocks that would be in the sea are set down again on open grass near the Braes,
    so there's as much tin to mine; other rocks and trees out there go with the land.
  * The cottage's own cape, further south, is left as it is (BOX).

Run it once (a second run finds the corner gone and stops).

  python -I "dev\\migrate\\cut_isle_corner.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import h01                               # noqa: E402

BOX = (76, -63, 124, 0)                                  # (where the coast is cut)
CORNER = (115, -40)                                      # (land before, sea after: done already?)
BRAES = (102, -16)                                       # (near the Tin_Braes place: where the tin goes)


def shore(gy):
    """The column the sea starts at in row gy: a slant, wandering in bays and points."""
    return int(round(92 + 0.43 * (gy + 50) + 7 * (W.fbm(0, gy, 7, 2601) - 0.5) + 3 * (W.fbm(0, gy, 2.5, 2602) - 0.5)))


def cut(w):
    """The sea over the corner; sand where the land meets it, a shell or a pebble on it. Returns the tin rocks lost."""
    x1, y1, x2, y2 = BOX
    edge, tin = set(), 0
    for gy in range(y1, y2 + 1):
        for gx in range(max(x1, shore(gy) + 1), x2 + 1):
            c = w.cell(gx, gy)
            if c is None or W.watery(c):
                continue
            if W.parts(c)[1].get("Decor", "").startswith("Tin_Rock"):
                tin += 1
            edge.add((gx, gy))
            w.put(gx, gy, W.SEA)
    wet = lambda c: w.cell(*c) is None or W.watery(w.cell(*c))
    for c in sorted({(c[0] + i, c[1] + j) for c in edge for i in range(-3, 4) for j in range(-3, 4)}):
        t = w.cell(*c)
        if t is None or W.watery(t) or not W.natural(t) or W.parts(t)[1].get("Decor", "").startswith("Tin_Rock"):
            continue
        one = any(wet((c[0] + i, c[1] + j)) for i in (-1, 0, 1) for j in (-1, 0, 1))
        two = any(wet((c[0] + i, c[1] + j)) for i in range(-2, 3) for j in range(-2, 3))
        if one or (two and h01("cut beach", *c) < 0.75):
            r = h01("beach things", *c)
            w.put(c[0], c[1], "Sand001" + ("+Decor(Shells00%d)" % (1 + int(r * 300) % 3) if r < 0.03 else
                                           "+Decor(Pebble002)" if r < 0.05 else ""))
    return tin


def tin_back(w, n):
    """n tin rocks on open grass near the Braes, a little apart."""
    spots = sorted(((gx, gy) for gx in range(BRAES[0] - 9, BRAES[0] + 6) for gy in range(BRAES[1] - 8, BRAES[1] + 5)
                    if w.cell(gx, gy) == "Grass001" and gx < shore(gy) - 3), key=lambda c: h01("tin back", *c))
    put = []
    for c in spots:
        if len(put) == n:
            break
        if all(abs(c[0] - o[0]) + abs(c[1] - o[1]) > 1 for o in put):
            w.put(c[0], c[1], "Grass001+Decor(Tin_Rock001)")
            put.append(c)
    return len(put)


def main():
    w = W.World(0)
    if W.watery(w.cell(*CORNER)):
        print("The Isle's north-east corner is cut already.")
        return
    tin = cut(w)
    back = tin_back(w, tin)
    print("The north-east corner's cut; %d tin rocks moved near the Braes (of %d); %d maps changed" % (back, tin, w.save()))


if __name__ == "__main__":
    main()
