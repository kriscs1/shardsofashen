"""The boardwalks wander a little (the owner's wish), not ruler lines across the marsh: Mirefold's way out to the Mire
Tunnel and its long spur to the hut on the east, and in the marsh round Fenmoor Hall the old road west and east of it
and the way up to the Drowned Abbey, each a single line of planks. Mirefold's square, its short spurs and Saltmarsh's
streets stay straight (a street near the middle is).

Each route is laid again between the same two ends, along a line that bends by a few tiles either way and goes round
anything built or placed; the planks it leaves are marsh or marsh water again, as what's beside them is. Run after
marsh_water.py. Safe to run again.

  python -I "dev\migrate\wind_boardwalks.py"   (then build_minimaps.py)
"""
import heapq
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_edit import World, natural, parts, line_cell, XT, YT, PEAKY    # noqa: E402
from atlas import h01                                                    # noqa: E402

BOARD = "Boardwalk001"
BOG = "Bog001"
MARSH = ["Marsh001"] * 8 + ["Marsh002"] * 3 + ["Marsh003"] * 2 + ["Marsh005"] * 2 + ["Marsh006"] * 2 + ["Marsh009"] * 4
BAND = 10                  # (how far a route may stray from its line, to get round something)
TURN = 2                   # (what a turn costs: straight runs and a bend, not a staircase of single steps)
SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))
ROUND = SIDES + ((1, 1), (1, -1), (-1, 1), (-1, -1))

# (from, to, how far it bends, how long a bend is, where the old planks are: (x1, y1, x2, y2) boxes)
ROUTES = [
    ((-145, 104), (-11, 124), 5, 40, [(-144, 103, -125, 110), (-124, 100, -12, 126)]),      # (Mirefold to the tunnel)
    ((-150, 109), (-128, 109), 2, 15, [(-149, 109, -129, 109)]),                            # (the spur to the east hut)
    ((175, 361), (199, 361), 3, 24, [(175, 360, 175, 360), (176, 357, 199, 365)]),          # (the old road, west of the Hall)
    ((229, 360), (258, 360), 3, 24, [(230, 355, 258, 365)]),                                # (and east of it)
    ((227, 348), (227, 358), 3, 20, [(224, 348, 232, 358)]),                                # (up to the Abbey's door)
]


def built(w):
    """The cells nothing may be laid on or hard by: what's roofed, and what's placed to stay where it is."""
    out = set()
    for (mx, my), m in w.maps.items():
        for y, row in enumerate(m.rows):
            for x, c in enumerate(row):
                if parts(c)[1].get("Roof"):
                    out.add((mx * XT + x, my * YT + y))
        for ln in m.ents:
            p = ln.split("\t")
            if p[0] == "Id" or (p[0] == "NPC" and "Stand=1" not in ln):
                continue                                 # (a place's name, and what roams, can be on planks)
            c = line_cell(ln, mx, my)
            if c:
                out.add(c)
    return out | {(x + dx, y + dy) for x, y in out for dx, dy in ROUND}


def layable(w, near, c):
    text = w.cell(*c)
    if text is None or c in near:
        return False
    t, over = parts(text)
    if PEAKY.match(t) or t == "Water001":
        return False
    if t in (BOARD, BOG) or t.startswith("Dirt"):
        return not (over.get("Roof") or over.get("Trigger") or over.get("Infront") or over.get("Under"))
    return natural(text)


def line_of(a, b, bend, wave, key):
    """Points along a to b, pushed to either side by two slow waves; none at the ends."""
    (x0, y0), (x1, y1) = a, b
    length = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    p1, p2 = 6.283 * h01("wind", key, 1), 6.283 * h01("wind", key, 2)
    out = []
    for i in range(int(length * 2) + 1):
        t = i / (length * 2)
        o = bend * min(1, 5 * t, 5 * (1 - t)) * (0.72 * math.sin(6.283 * t * length / wave + p1)
                                                  + 0.38 * math.sin(6.283 * t * length / (wave * 0.57) + p2))
        out.append((x0 + (x1 - x0) * t + nx * o, y0 + (y1 - y0) * t + ny * o))
    return out


def way(w, near, a, b, line):
    """The cheapest steps from a to b, side to side, keeping to the line (dearer the further from it, and at a turn)."""
    off = {}
    for lx, ly in line:
        for x in range(int(lx) - BAND, int(lx) + BAND + 1):
            for y in range(int(ly) - BAND, int(ly) + BAND + 1):
                d = math.hypot(x - lx, y - ly)
                if d < off.get((x, y), BAND):
                    off[(x, y)] = d

    def fits(c):
        return c in (a, b) or (c in off and layable(w, near, c))
    start = (a, None)
    best, came, todo, end = {start: 0}, {}, [(0, a, None)], None
    while todo:
        cost, c, d = heapq.heappop(todo)
        if c == b:
            end = (c, d)
            break
        if cost > best[(c, d)]:
            continue
        for side in SIDES:
            n = (c[0] + side[0], c[1] + side[1])
            if not fits(n):
                continue
            step = cost + 1 + 0.9 * off.get(n, 0) ** 2 + (TURN if d not in (None, side) else 0)
            if step < best.get((n, side), 1e18):
                best[(n, side)], came[(n, side)] = step, (c, d)
                heapq.heappush(todo, (step, n, side))
    assert end, "no way from %s to %s" % (a, b)
    path, at = [end[0]], end
    while at != start:
        at = came[at]
        path.append(at[0])
    return path[::-1]


def ground_for(w, c, gone):
    """What an old plank's cell is now: what most of the wild ground round it is."""
    bog = marsh = 0
    others = {}
    for dx, dy in ROUND:
        n = (c[0] + dx, c[1] + dy)
        t = w.tile(*n)
        if t is None or n in gone or t == BOARD or t.startswith("Dirt"):
            continue
        if t == BOG:
            bog += 1
        elif t.startswith("Marsh"):
            marsh += 1
        elif re.match(r"(Grass|Sand)\d", t):
            others[t] = others.get(t, 0) + 1
    if bog > marsh and bog >= sum(others.values()):
        return BOG
    if others and max(others.values()) > marsh:
        return max(sorted(others), key=others.get)
    return MARSH[int(h01("old_plank", c[0], c[1]) * len(MARSH))]


def main():
    w = World(0)
    near = built(w)
    for a, b, bend, wave, old in ROUTES:
        line = line_of(a, b, bend, wave, "%d,%d" % a)
        path = way(w, near, a, b, line)
        new = set(path)
        gone = {(x, y) for x1, y1, x2, y2 in old for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)
                if (x, y) not in new and (w.tile(x, y) == BOARD or (w.tile(x, y) or "").startswith("Dirt"))}
        for c in sorted(gone):
            w.set(c[0], c[1], tile=ground_for(w, c, gone))
        for c in new:
            w.set(c[0], c[1], tile=BOARD, decor="")
        print("%s to %s: %d tiles, %d old planks up" % (a, b, len(path), len(gone)))
    w.save()


if __name__ == "__main__":
    main()
