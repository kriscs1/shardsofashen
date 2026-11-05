"""The marsh's water is marsh water (the owner's wish: a greeny brown, not the sea's blue). Both marshes, the Mirefen and
the one round Saltmarsh, had their pools and streams in the sea's own tile, Water001; build_marsh.py's Bog001 is now
laid where it belongs:

  * a body of water cut off from the sea, whose shore is mostly marsh (the pools, the stream down to Saltmarsh);
  * an inlet of the sea (too narrow for the open sea, INLET tiles from one side to the other), its shore mostly marsh.

The sea itself, and any lake or river in other country, stays as it is. Lily pads, reeds and what stands in the water
stay too. Safe to run again.

  python -I "dev\migrate\marsh_water.py"   (then build_minimaps.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world_edit import World, parts, SEA, XT, YT       # noqa: E402

BOG = "Bog001"
INLET = 4                  # (how far the open sea is from land at the least: any narrower is an inlet)
LEAST_INLET = 12           # (fewer tiles than this is only a nick in the coast)
SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))
ROUND = SIDES + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def bodies(cells):
    """cells split into what joins up, side to side."""
    left, out = set(cells), []
    while left:
        start = left.pop()
        todo, body = [start], [start]
        while todo:
            x, y = todo.pop()
            for dx, dy in SIDES:
                c = (x + dx, y + dy)
                if c in left:
                    left.discard(c)
                    todo.append(c)
                    body.append(c)
        out.append(body)
    return out


def marshy(w, body):
    """Is most of this water's shore marsh? (a boardwalk over it was laid on marsh; marsh water already there counts)"""
    marsh = other = 0
    wet = set(body)
    for x, y in body:
        for dx, dy in SIDES:
            c = (x + dx, y + dy)
            t = w.tile(*c)
            if c in wet or t is None or t == SEA:
                continue
            if t.startswith(("Marsh", "Boardwalk", "Bog")):
                marsh += 1
            else:
                other += 1
    return marsh > 0 and marsh >= other


def narrow_parts(sea, r):
    """The cells of the sea that no r-from-land stretch of open water reaches."""
    dist, ring = {}, []
    for x, y in sea:
        if any((x + dx, y + dy) not in sea and w_has(x + dx, y + dy) for dx, dy in ROUND):
            dist[(x, y)] = 1
            ring.append((x, y))
    d = 1
    while ring and d < r:                                 # (eaten in from the land, r deep)
        d += 1
        nxt = []
        for x, y in ring:
            for dx, dy in ROUND:
                c = (x + dx, y + dy)
                if c in sea and c not in dist:
                    dist[c] = d
                    nxt.append(c)
        ring = nxt
    core = [c for c in sea if c not in dist]
    held, ring = set(core), core
    for _ in range(r):                                    # (and grown back out as far: what it can't reach is narrow)
        nxt = []
        for x, y in ring:
            for dx, dy in ROUND:
                c = (x + dx, y + dy)
                if c in sea and c not in held:
                    held.add(c)
                    nxt.append(c)
        ring = nxt
    return [c for c in sea if c not in held]


def main():
    global w_has
    w = World(0)
    w_has = w.has                                         # (past the last map is open sea, not land)
    water = []
    for (mx, my), m in w.maps.items():
        for y in range(YT):
            for x in range(XT):
                if parts(m.rows[y][x])[0] == SEA:
                    water.append((mx * XT + x, my * YT + y))
    found = bodies(water)
    sea = set(max(found, key=len))
    pools = [b for b in found if len(b) < len(sea) and marshy(w, b)]
    inlets = [b for b in bodies(narrow_parts(sea, INLET)) if len(b) >= LEAST_INLET and marshy(w, b)]
    for body in pools + inlets:
        for gx, gy in body:
            w.set(gx, gy, tile=BOG)
    w.save()
    print("Marsh water: %d pools, %d inlets, %d tiles, %d maps" % (
        len(pools), len(inlets), sum(len(b) for b in pools + inlets), len(w.changed)))


if __name__ == "__main__":
    main()
