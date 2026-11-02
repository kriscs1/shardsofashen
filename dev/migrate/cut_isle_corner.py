"""The Isle's north-west corner cut away (the owner's wish: it looked too much like a box): the coast comes down on the
slant, wandering, from the inlet on the north coast to the top of the west coast, a beach along it, and the sea where
the corner was.

  * Edwin and Maren's house stood in that corner, so it moves one whole map east, 0,-2 to 1,-2, every tile and thing in
    it keeping its place on its map (as move_lawyers_house.py moved it): the ground floor's walls, floor and roof, its
    brass plate and its Id, Edwin, Maren and Noops; the upstairs map 0,-2,1 renamed 1,-2,1. It's still in the Isle's
    north-west, by the sea. Open ground round it (the inlet's end filled in behind it), a path from its door to the
    Isle's roads; the old path to where it stood is gone.
  * Whatever stood in the sea now (a wolf, a rabbit) walks to the nearest land.

Run it once (a second run finds the house moved and stops).

  python -I "dev\\migrate\\cut_isle_corner.py"
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, h01                      # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
OLD, NEW = (0, -2), (1, -2)                             # (the house's maps: ground floor; upstairs at z 1)
HOUSE = (11, 1, 22, 7)                                  # (its walls and roof, on its map)
DOOR = (16, 8)                                          # (the step outside its door)
FOLK = ("Maren_At_Counter", "Edwin_At_Desk", "Noops", "Isle_Bank_Notice", "Isle_Bank")
BOX = (0, -63, 46, 2)                                   # (where the coast is cut)
KEEP_OFF = 29                                           # (no sea past this column beside the house: its beach and lawn)


def shore(gy):
    """The column the sea reaches in row gy: a slant, wandering in bays and points."""
    x = 29 - 0.6 * (gy + 40) + 8 * (W.fbm(0, gy, 7, 2501) - 0.5) + 3 * (W.fbm(0, gy, 2.5, 2502) - 0.5)
    if -46 <= gy <= -28:
        x = min(x, KEEP_OFF)
    return int(round(x))


def house(w):
    """The ground floor lifted from OLD to NEW (by whole maps: the same tiles on its map), and its people."""
    dx, dy = (NEW[0] - OLD[0]) * XT, (NEW[1] - OLD[1]) * YT
    ox, oy = OLD[0] * XT - 1, OLD[1] * YT - 1
    x1, y1, x2, y2 = HOUSE
    lift = [(ox + x, oy + y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)] + [(ox + DOOR[0], oy + DOOR[1])]
    # (open ground round its new place: the wood cleared, the inlet's end filled in behind it)
    for gx in range(ox + x1 + dx - 3, ox + x2 + dx + 4):
        for gy in range(oy + y1 + dy - 3, oy + y2 + dy + 7):
            c = w.cell(gx, gy)
            if c is not None and not W.is_road(c):
                w.put(gx, gy, "Grass001")
    for c in lift:
        w.put(c[0] + dx, c[1] + dy, w.cell(*c))
    m = w.maps[OLD]
    for ln in [ln for ln in m.ents if W.line_id(ln) in FOLK]:
        w.drop(m, ln)
        w.add_line(ln, OLD, dx, dy)
    W.rename_level_map(W.mname(*OLD, 1), W.mname(*NEW, 1))
    return (ox + DOOR[0] + dx, oy + DOOR[1] + dy)


def cut(w, lawn):
    """The sea over the corner; sand where the land meets it, a shell or a pebble on it."""
    x1, y1, x2, y2 = BOX
    edge = set()
    for gy in range(y1, y2 + 1):
        s = shore(gy)
        for gx in range(x1, min(s, x2 + 1)):
            if w.cell(gx, gy) is not None and (gx, gy) not in lawn:
                if w.cell(gx, gy) != W.SEA:
                    edge.add((gx, gy))
                w.put(gx, gy, W.SEA)
    wet = lambda c: w.cell(*c) is None or W.watery(w.cell(*c))
    near = {(c[0] + i, c[1] + j) for c in edge for i in range(-3, 4) for j in range(-3, 4)} | lawn_rim(w, lawn)
    for c in sorted(near):
        t = w.cell(*c)
        if t is None or W.watery(t) or not W.natural(t) or c in lawn:
            continue
        one = any(wet((c[0] + i, c[1] + j)) for i in (-1, 0, 1) for j in (-1, 0, 1))
        two = any(wet((c[0] + i, c[1] + j)) for i in range(-2, 3) for j in range(-2, 3))
        if one or (two and h01("cut beach", *c) < 0.75):
            r = h01("beach things", *c)
            w.put(c[0], c[1], "Sand001" + ("+Decor(Shells00%d)" % (1 + int(r * 300) % 3) if r < 0.03 else
                                           "+Decor(Pebble002)" if r < 0.05 else ""))


def lawn_rim(w, lawn):
    return {(c[0] + i, c[1] + j) for c in lawn for i in range(-3, 4) for j in range(-3, 4)}


def old_path(w):
    """The road that went to where the house stood, and on up what's now the beach: grass again."""
    for gx in range(0, 32):
        for gy in range(-46, -15):
            c = w.cell(gx, gy)
            if c is not None and not W.watery(c) and W.is_road(c):
                near_sea = any(W.watery(w.cell(gx + i, gy + j) or W.SEA) for i in (-1, 0, 1) for j in (-1, 0, 1))
                w.put(gx, gy, "Sand001" if near_sea else "Grass001")


def walk_ashore(w):
    """Whatever stood where the sea is now: the nearest land east of it."""
    moved = []
    for m, ln, c in w.lines(BOX):
        if not W.watery(w.cell(*c)):
            continue
        p = ln.split("\t")
        if p[0] not in ("NPC", "StaticObject", "MapItem"):
            raise SystemExit("!! %s is in the sea now: %s" % (m.name, ln))
        dx = next((d for d in range(1, 60) if w.cell(c[0] + d, c[1]) is not None and
                   W.natural(w.cell(c[0] + d + 2, c[1]) or "") and not W.watery(w.cell(c[0] + d + 2, c[1]))), None)
        if dx is None:
            raise SystemExit("!! no land east of %s on %s" % (ln, m.name))
        mx, my, _ = W.mxyz(m.name)
        w.drop(m, ln)
        w.add_line(ln, (mx, my), dx + 2, 0)
        moved.append(p[1])
    return moved


def path(w, door):
    """A path from the house's door to the Isle's roads (its own step isn't one)."""
    net = {(gx, gy) for gx in range(0, 125) for gy in range(-63, 63)
           if w.cell(gx, gy) is not None and W.is_road(w.cell(gx, gy)) and abs(gx - door[0]) + abs(gy - door[1]) > 4}
    return W.join_roads(w, [(door[0], door[1] + 1)], network=net)


def words():
    up_old, up_new = W.mname(*OLD, 1), W.mname(*NEW, 1)
    for f in ("Locks.ini", "Music.ini", "Ambient.ini"):
        p = os.path.join(DATA, f)
        s = W.read(p)
        t = re.sub(r"(?<![-\d,])%s(?![\d,])" % re.escape(up_old), up_new, s)
        if t != s:
            W.write(p, t)


def main():
    if os.path.exists(os.path.join(ROOT, "maps", W.mname(*NEW, 1) + ".txt")):
        print("The Isle's north-west corner is cut already.")
        return
    w = W.World(0)
    door = house(w)
    x1, y1, x2, y2 = HOUSE
    ox, oy = NEW[0] * XT - 1, NEW[1] * YT - 1
    lawn = {(gx, gy) for gx in range(ox + x1 - 3, ox + x2 + 4) for gy in range(oy + y1 - 3, oy + y2 + 7)}
    cut(w, lawn)
    old_path(w)
    moved = walk_ashore(w)
    n = path(w, door)
    changed = w.save()
    words()
    print("The corner's cut; the house on %s (its door at %s, %d path); ashore: %s; %d maps changed" %
          (W.mname(*NEW), door, n, ", ".join(moved) or "nothing", changed))


if __name__ == "__main__":
    main()
