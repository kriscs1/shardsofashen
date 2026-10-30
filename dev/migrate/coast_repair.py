"""Mends what coast_reshape.py broke (its plain ground took in Dirt, so it ate roads; its wild scenery left out
Tall_Grass, so specks of old land stood in the new sea):

  * the land it ate within a few tiles of an old road (a dirt road, a path, a bridge's end) comes back as it was;
  * the specks (old land left alone in the sea, a few tiles with nothing on them) sink;
  * the diagonal shore pieces are put in round both.

The old land is read from the commit before the reshape (git ee8674b). Run it once (a second run does nothing).

  python -I "dev\\migrate\\coast_repair.py"
"""
import os
import re
import subprocess
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import land as LAND                                     # noqa: E402
from atlas import h01                                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DONE = os.path.join(ROOT, "dev", "migrate", ".coast_repaired")
BEFORE = "ee8674b"                                      # (the last commit before coast_reshape.py ran)
XT, YT = 25, 21
SEA = "Water001"
ROAD = re.compile(r"^(Dirt|Gravel|Cobble|Path|Road|Bridge|Plank|Boardwalk|Flagstone|Sandstone_Paving|Jetty|Pier)")
GUARD = 4                                               # (a bay the sea ate this near anything is mended)
MARGIN = 10                                             # (land put back this far round things, in a big bay)
WHOLE = 400                                             # (a smaller bay that came near anything: all of it)
REACH = 16
SPECK = 8                                               # (old land this small, alone in the sea, sinks)


def watery(t):
    return t.startswith("Water") or "_Water0" in t


def read_cells(text):
    rows = text.replace("\r\n", "\n").split("\n")
    return [r.split(":") for r in rows[:YT]], rows[YT:]


def old_maps(names):
    """{name: rows of cells} at BEFORE (one git cat-file for them all)."""
    p = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, capture_output=True,
                       input="".join("%s:maps/%s.txt\n" % (BEFORE, n) for n in names).encode())
    out, data, i = {}, p.stdout, 0
    for n in names:
        nl = data.index(b"\n", i)
        head = data[i:nl].split()
        if head[-1] == b"missing":
            i = nl + 1
            continue
        size = int(head[2])
        out[n] = read_cells(data[nl + 1:nl + 1 + size].decode("cp1252"))[0]
        i = nl + 1 + size + 1
    return out


def main():
    if os.path.exists(DONE):
        print("The coast's been mended already (delete %s to do it again)." % DONE)
        return
    # (the maps east of Galaith: west of it, the Galaith and Mirefen passes made their own sea since)
    names = sorted(f[:-4] for f in os.listdir(os.path.join(ROOT, "maps")) if re.match(r"^\d+,-?\d+,0\.txt$", f))
    old = old_maps(names)
    now, rest, placed = {}, {}, set()
    for n in names:
        raw = open(os.path.join(ROOT, "maps", n + ".txt"), "rb").read().decode("cp1252")
        now[n], rest[n] = read_cells(raw)
        mx, my = (int(v) for v in n.split(",")[:2])
        for ln in rest[n]:
            p = ln.split("\t")
            if len(p) >= 4 and p[0] in ("NPC", "StaticObject", "MapItem"):
                try:
                    placed.add((mx * XT + int(float(p[2]) // 32), my * YT + int(float(p[3]) // 32)))
                except ValueError:
                    pass

    def cells(src):
        out = {}
        for n, rows in src.items():
            mx, my = (int(v) for v in n.split(",")[:2])
            for y in range(YT):
                for x in range(XT):
                    out[(mx * XT + x, my * YT + y)] = (n, x, y, rows[y][x])
        return out
    o, c = cells(old), cells(now)
    ground = lambda cell: cell.split("+")[0]                                    # noqa: E731
    eaten = {g for g, v in c.items() if ground(v[3]) == SEA and g in o and not watery(ground(o[g][3]))}
    # (what the sea mustn't come near: an old road or anything made, and anything placed)
    made = {g for g, v in o.items() if ROAD.match(ground(v[3])) or "Roof(" in v[3] or "Trigger" in v[3]} | placed
    near = {}
    q = deque()
    for g in made:
        near[g] = 0
        q.append(g)
    while q:                                            # (how far each eaten tile is from them, up to REACH)
        a = q.popleft()
        if near[a] >= REACH:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (a[0] + dx, a[1] + dy)
            if n in eaten and n not in near:
                near[n] = near[a] + 1
                q.append(n)
    new = {g: v[3] for g, v in c.items()}
    back = set()
    seen = set()
    for g in eaten:                                     # each bay it ate: as it was, or kept back from things
        if g in seen:
            continue
        comp, q = [g], deque([g])
        seen.add(g)
        while q:
            a = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (a[0] + dx, a[1] + dy)
                if n in eaten and n not in seen:
                    seen.add(n)
                    comp.append(n)
                    q.append(n)
        if not any(near.get(a, 99) <= GUARD for a in comp):
            continue                                    # (nowhere near anything: the bay stays)
        whole = len(comp) <= WHOLE
        for a in comp:
            if whole or near.get(a, 99) <= MARGIN + 3 * (h01("mend", a[0], a[1]) - 0.5):
                back.add(a)
    for g in back:
        new[g] = o[g][3]
    # the pools: water all of eaten land, cut off from the water there was before
    wet = {g for g in eaten if ground(new[g]) == SEA}
    seen = set()
    for g in wet:
        if g in seen:
            continue
        comp, q, open_sea = [g], deque([g]), False
        seen.add(g)
        while q:
            a = q.popleft()
            for n in ((a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)):
                if n in wet and n not in seen:
                    seen.add(n)
                    comp.append(n)
                    q.append(n)
                elif n not in wet and n in new and watery(ground(new[n])):
                    open_sea = True
        if not open_sea or len(comp) <= 12:
            for a in comp:
                new[a] = o[a][3]
                back.add(a)
    # the specks: small bits of old land alone in water (nothing on them, nothing made)
    land = {g for g, t in new.items() if not watery(ground(t))}
    seen, sunk = set(), set()
    for g in land:
        if g in seen:
            continue
        comp, q = [g], deque([g])
        seen.add(g)
        while q:                                        # (all of it: a big land's never a speck)
            a = q.popleft()
            for n in ((a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)):
                if n in land and n not in seen:
                    seen.add(n)
                    comp.append(n)
                    q.append(n)
        if len(comp) > SPECK:
            continue
        if any(p in placed or p not in o or watery(ground(o[p][3])) or "Roof(" in new[p] or "Trigger" in new[p]
               for p in comp):
            continue                                    # (an islet of the reshape's, or something on it)
        if not any(p in eaten or any((p[0] + dx, p[1] + dy) in eaten for dx in (-2, 0, 2) for dy in (-2, 0, 2))
                   for p in comp):
            continue                                    # (not left behind by the reshape: as it was)
        sunk.update(comp)
    for g in sunk:
        new[g] = SEA
    changed = {g for g in new if new[g] != c[g][3]}
    for g in list(changed) + [(a[0] + dx, a[1] + dy) for a in changed for dx in (-1, 0, 1) for dy in (-1, 0, 1)]:
        t = ground(new.get(g, SEA))
        if g in new and "_Water0" in t and not any(not watery(ground(new.get((g[0] + dx, g[1] + dy), SEA)))
                                                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            new[g] = SEA                                # (a shore piece with no land by it now)
            changed.add(g)
    near = {(g[0] + dx, g[1] + dy) for g in changed for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)}
    grid = {g: ground(new[g]) for g in near if g in new}
    LAND.smooth_shores(grid, [g for g in grid if grid[g] == SEA])
    for g, t in grid.items():
        if t != ground(new[g]):
            new[g] = t                                  # (a shore piece: no scenery on water)
            changed.add(g)
    touched = set()
    for g in changed:
        n, x, y, _ = c[g]
        now[n][y][x] = new[g]
        touched.add(n)
    for n in touched:
        text = "\r\n".join([":".join(r) for r in now[n]] + rest[n])
        open(os.path.join(ROOT, "maps", n + ".txt"), "wb").write(text.encode("cp1252"))
    open(DONE, "w").write("mended\n")
    print("The coast mended: %d tiles of land back by the roads, %d specks sunk; %d maps changed" %
          (len(back), len(sunk), len(touched)))


if __name__ == "__main__":
    main()
