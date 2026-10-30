"""The mainland's coast in big strokes, on the maps as they are (CLAUDE.md: the coast looked like a rectangle; the
plan's letters gave it straight sides a map long). A pass over the finished maps, not the plan: build_estforlan.py's
maps have had the owner's hand and other builders over them since, so nothing is rebuilt.

  * The coast is pushed out or eaten back by slow noise (bulges a few hundred tiles across, bays and capes), and a few
    features drawn on purpose: a gulf in the north coast, a long peninsula to the south-east, a bay under the desert.
  * Only wild ground changes, and only open sea: never a cell with a road, a building, a roof, a trigger or an Id, nor
    one within a few tiles of any of those or of a thing placed on the map (an NPC, an object, an item); never the
    Isle, nor a map the owner has drawn on by hand (KEEP), nor a settlement's maps.
  * New land takes the ground round it (a beach where it meets the sea), and a little of its scenery; the diagonal shore
    pieces are put in round every change (land.smooth_shores).
  * Islets and skerries off the long empty coasts.

Run it once (a second run finds the coast already reshaped, and changes nothing more).

  python -I "dev\\migrate\\coast_reshape.py" [--dry]
"""
import math
import os
import re
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, XT, YT                      # noqa: E402
from atlas import fbm, h01                              # noqa: E402
import land as LAND                                     # noqa: E402
import layout as L                                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DONE = os.path.join(ROOT, "dev", "migrate", ".coast_reshaped")
SEA = "Water001"
# maps the owner has drawn on in the editor (git: 71af91a, 33ff36e, d2a86e7): their coast is theirs
KEEP = set("""-10,15,0 -5,14,0 -5,15,0 -6,13,0 -6,14,0 -6,15,0 -6,16,0 -7,16,0 -8,13,0 -8,14,0 -8,15,0 -8,16,0 -9,14,0
0,2,0 1,1,0 1,2,0 1,21,0 1,6,0 15,14,0 16,15,0 16,19,0 16,20,0 17,18,0 17,19,0 17,20,0 17,21,0 2,1,0 2,2,0 2,21,0
2,4,0 2,5,0 2,6,0 24,16,0 24,17,0 24,18,0 25,16,0 25,17,0 25,18,0 26,16,0 26,17,0 26,18,0 27,16,0 27,17,0 27,18,0
27,4,0 3,1,0 3,2,0 3,20,0 3,21,0 3,22,0 3,4,0 3,5,0 3,6,0 3,7,0 4,21,0 4,4,0 4,5,0 4,6,0 4,7,0 5,4,0 5,5,0 5,6,0
5,8,0 6,5,0 6,6,0 -4,14,0 -7,14,0 3,5,0 4,4,0 6,4,0 7,5,0 7,6,0 8,5,0 8,6,0 8,8,0 9,4,0 9,5,0 9,6,0 9,7,0 9,8,0
9,9,0""".split())
PLAIN = re.compile(r"^(Grass|Sand|Snow|Marsh|Ash|Scorched|Dirt|Moss|Heath)\d{3}$")
WILD_DECOR = re.compile(r"^(Tree|Pine|Palm|Oak|Willow|Yew|Birch|Bush|Shrub|Rock|Boulder|Pebble|Flower|Grass|Fern|Reed|"
                        r"Mushroom|Weed|Cactus|Dead_Tree|Stump|Snow_Tree|Ash_Tree|Log|Heather|Thistle|Clover|Herb)")
GUARD = 3                                     # (tiles kept clear round anything made or placed)


def global_maps():
    out = {}
    for f in os.listdir(os.path.join(ROOT, "maps")):
        m = re.match(r"^(-?\d+),(-?\d+),0\.txt$", f)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = f[:-4]
    return out


def settlement_maps():
    out = set()
    for spec in L.SETTLEMENTS.values():
        x1, y1, x2, y2 = spec["maps"]
        out |= {"%d,%d,0" % (x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    return out


def main(dry=False):
    if os.path.exists(DONE) and not dry:
        print("The coast's been reshaped already (delete %s to do it again)." % DONE)
        return
    names = global_maps()
    dragon_isle = {"%d,%d,0" % (x, y) for x in range(25, 29) for y in range(21, 25)}     # (Dragon Island: as it is)
    frozen = KEEP | settlement_maps() | set(L.ISLE) | dragon_isle
    maps = {k: Map(n) for k, n in names.items()}
    tile, wild, keep = {}, set(), set()
    for (mx, my), m in maps.items():
        locked = m.name in frozen
        placed = []
        for ln in m.ents:
            p = ln.split("\t")
            if len(p) >= 4 and p[0] in ("NPC", "StaticObject", "MapItem", "Trigger"):
                try:
                    placed.append((int(float(p[2]) // 32) + 1, int(float(p[3]) // 32) + 1))
                except ValueError:
                    pass
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                g = (mx * XT + x - 1, my * YT + y - 1)
                t, over = m.parts(x, y)
                tile[g] = t
                is_wild = (PLAIN.match(t) or t == SEA) and not over.get("Roof") and not over.get("Trigger") and \
                    not over.get("Under") and (not over.get("Decor") or WILD_DECOR.match(over["Decor"]))
                if locked or not is_wild:
                    keep.add(g)
                else:
                    wild.add(g)
        for (x, y) in placed:
            for dy in range(-GUARD, GUARD + 1):
                for dx in range(-GUARD, GUARD + 1):
                    keep.add((mx * XT + x - 1 + dx, my * YT + y - 1 + dy))
    # (a margin round everything made: a road, a wall, a pier)
    made = [g for g in keep if g in tile and tile[g] != SEA and not PLAIN.match(tile[g])]
    for gx, gy in made:
        for dy in range(-GUARD, GUARD + 1):
            for dx in range(-GUARD, GUARD + 1):
                keep.add((gx + dx, gy + dy))
    land = {g for g, t in tile.items() if t != SEA and not t.startswith("Water0") and "_Water0" not in t}

    def dist_from(seeds, within):
        d = {g: 0 for g in seeds}
        q = deque(seeds)
        while q:
            c = q.popleft()
            for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                if n in within and n not in d and d[c] < 90:
                    d[n] = d[c] + 1
                    q.append(n)
        return d
    # (the open sea only: water joined to the world's edge - not a river, a lake or a marsh pool)
    water = set(tile) - land
    xs, ys = [g[0] for g in tile], [g[1] for g in tile]
    edge = [g for g in water if g[0] in (min(xs), max(xs)) or g[1] in (min(ys), max(ys)) or
            any(n not in tile for n in ((g[0] + 1, g[1]), (g[0] - 1, g[1]), (g[0], g[1] + 1), (g[0], g[1] - 1)))]
    seen = set(edge)
    q = deque(edge)
    while q:
        c = q.popleft()
        for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
            if n in water and n not in seen:
                seen.add(n)
                q.append(n)
    sea_cells = seen
    for g in list(wild):                                # (rivers, lakes; and the Isle's strait stays as it is)
        if (g not in land and g not in sea_cells) or (g[0] < 7 * XT and g[1] < 4 * YT):
            wild.discard(g)
            keep.add(g)
    to_land = dist_from([g for g in sea_cells if any(n in land for n in ((g[0] + 1, g[1]), (g[0] - 1, g[1]),
                                                                          (g[0], g[1] + 1), (g[0], g[1] - 1)))],
                        sea_cells)
    to_sea = dist_from([g for g in land if any(n in sea_cells for n in ((g[0] + 1, g[1]), (g[0] - 1, g[1]),
                                                                         (g[0], g[1] + 1), (g[0], g[1] - 1)))], land)

    def bulge(gx, gy):
        b = 2 * fbm(gx, gy, 140, 701) - 1 + 0.6 * (2 * fbm(gx, gy, 45, 702) - 1)
        # (on purpose: a gulf in the north coast, a peninsula to the south-east, a bay under the desert)
        for cx, cy, rx, ry, w in ((15.5 * XT, 4.4 * YT, 55, 30, -1.8), (21.5 * XT, 22.8 * YT, 75, 20, 1.8),
                                  (5.2 * XT, 20.2 * YT, 40, 24, -1.6)):
            d = math.hypot((gx - cx) / rx, (gy - cy) / ry)
            if d < 1:
                b += w * (1 - d)
        return b
    grow, eat = [], []
    for g in wild:
        b = bulge(*g)
        if g not in land and g in to_land and to_land[g] <= max(0.0, b) * 34 and to_land[g] >= 1:
            grow.append(g)
        elif g in land and g in to_sea and to_sea[g] < max(0.0, -b) * 26:
            eat.append(g)
    # islets: in open sea far from any coast, where the noise peaks
    islets = [g for g in wild if g not in land and to_land.get(g, 99) >= 12 and fbm(g[0], g[1], 7, 711) > 0.8]
    new = dict(tile)
    for g in eat:
        new[g] = SEA
    for g in grow + islets:
        new[g] = "?"

    def ground_near(g):
        """The plain ground most common round g (the biome it grows from), within 6 tiles."""
        seen = {}
        for r in range(1, 7):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    t = tile.get((g[0] + dx, g[1] + dy), "")
                    if PLAIN.match(t):
                        base = re.sub(r"\d+$", "001", t)
                        seen[base] = seen.get(base, 0) + 1
            if seen:
                return max(seen, key=seen.get)
        return "Grass001"
    for g in grow + islets:
        base = ground_near(g) if g in grow else "Grass001"
        coast = any(new.get(n) == SEA for n in ((g[0] + 1, g[1]), (g[0] - 1, g[1]), (g[0], g[1] + 1), (g[0], g[1] - 1)))
        if coast and base in ("Grass001", "Dirt001", "Heath001", "Moss001"):
            base = "Sand001"
        new[g] = base
    changed = {g for g in new if new[g] != tile[g]}
    if dry:
        print("dry: %d grown, %d eaten, %d islets" % (len(grow), len(eat), len(islets)))
        import pygame                                  # (a picture of it: dev\Renders\Coast preview.png)
        xs, ys = [g[0] for g in tile], [g[1] for g in tile]
        x0, y0 = min(xs), min(ys)
        img = pygame.Surface((max(xs) - x0 + 1, max(ys) - y0 + 1))
        img.fill((0, 0, 0))
        grown, eaten, isl = set(grow), set(eat), set(islets)
        for g, t in tile.items():
            col = (40, 80, 160) if g not in land else (170, 170, 170) if g in keep else (90, 150, 70)
            if g in grown:
                col = (240, 220, 80)
            elif g in eaten:
                col = (220, 60, 50)
            elif g in isl:
                col = (250, 140, 230)
            img.set_at((g[0] - x0, g[1] - y0), col)
        pygame.image.save(img, os.path.join(ROOT, "dev", "Renders", "Coast preview.png"))
        return
    # the diagonal shore pieces round every change
    near = {(g[0] + dx, g[1] + dy) for g in changed for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    grid = {c: new[c] for c in near if c in new}
    sea_near = [c for c in near if grid.get(c) == SEA and c not in keep]
    LAND.smooth_shores(grid, sea_near)
    for c, t in grid.items():
        if t != new[c]:
            new[c] = t
            changed.add(c)
    touched = set()
    for (gx, gy) in changed:
        mx, my = gx // XT, gy // YT
        m = maps.get((mx, my))
        if m is None:
            continue
        x, y = gx - mx * XT + 1, gy - my * YT + 1
        t, over = m.parts(x, y)
        over = dict(over)
        if new[(gx, gy)] == SEA or "Water0" in new[(gx, gy)]:
            over.pop("Decor", None)
            over.pop("Infront", None)
        elif (gx, gy) in grow or (gx, gy) in islets:
            if h01("scen", gx, gy) < 0.07 and new[(gx, gy)] not in ("Sand001",):
                over["Decor"] = "Bush001" if h01("bush", gx, gy) < 0.5 else "Rock001"
        m.put(x, y, new[(gx, gy)], over)
        touched.add(m)
    for m in touched:
        m.save()
    open(DONE, "w").write("reshaped\n")
    print("The coast: %d tiles grown, %d eaten back, %d islet tiles; %d maps changed" %
          (len(grow), len(eat), len(islets), len(touched)))


if __name__ == "__main__":
    main("--dry" in sys.argv)
