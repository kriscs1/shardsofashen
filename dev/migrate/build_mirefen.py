"""The west of the map finished (dev\\Roadmap.md group 9): what was black round Galaith is land and sea now.

  * The Mirefen: a swamp between the sea and the West Range, north of Galaith's mountains (maps -13..-1, 2..8):
    marsh, pools with lily pads and their diagonal shores, reeds, bog myrtle and willows, frogs and ducks. The way in
    is the beach along the West Range's north end (0,4,0), its peaks there worn back to sand.
  * Mirefold: a hamlet of thatched huts round a square of boardwalk, boardwalks out to the beach; its people.
  * South of Galaith (maps -13..-1, 21..23): the sea.
  * Its labels on the world map, its music and its background sound (the marsh's).

Safe to run again (the maps are drawn the same; the data only added where it's missing).

  python -I "dev\\migrate\\build_mirefen.py"   (then build_minimaps.py)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, XT, YT                      # noqa: E402
from atlas import Atlas, fbm, h01                       # noqa: E402
import land as LAND                                     # noqa: E402
import build_galaith_city as GALAITH                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
FEN_X, FEN_Y = range(-13, 0), range(2, 9)
SEA_Y = range(21, 24)
SQUARE = (-150, 104)                                    # Mirefold's square (world tiles)
HUTS = [(-162, 95), (-152, 94), (-141, 96), (-163, 113), (-150, 114), (-139, 112), (-129, 104)]
PEOPLE = [("Villager", "Mirefold_Villager_1", "Old_Nell"), ("Villager", "Mirefold_Villager_2", "Hobb"),
          ("Villager", "Mirefold_Villager_3", "Marigold"), ("Fisherman", "Mirefold_Fisherman", "Ewan")]


def land(gx, gy):
    west = -296 + int(90 * (fbm(0, gy, 55, 951) - 0.5) + 18 * (fbm(0, gy, 11, 952) - 0.5))   # (bays and capes)
    north = 46 + int(70 * (fbm(gx, 0, 60, 953) - 0.5) + 16 * (fbm(gx, 0, 12, 954) - 0.5))
    if gy >= 132 + int(50 * (fbm(gx, 0, 26, 960) - 0.5)) and GALAITH.is_sea(gx, gy):
        return False                                   # (the sea north-west of Galaith, on round into the fen)
    return gx > west and gy > north


def mountain(gx, gy):
    """The West Range's foot on the east, and Galaith's mountains rising in the south."""
    east = min(-3, -18 + int(90 * (fbm(0, gy, 40, 955) - 0.5) + 14 * (fbm(0, gy, 9, 958) - 0.5)))  # (its foot wanders)
    south = 170 + int(60 * (fbm(gx, 0, 40, 956) - 0.5) + 12 * (fbm(gx, 0, 9, 959) - 0.5))
    beach = gy < 92 and gx > -26                                 # (the way in, along the range's north end)
    return (gx > east or gy > south) and not beach


def hut(atlas, gx, gy, w, h, grp, door_side):
    """A thatched hut, walls of timber round a plank floor (x, y its top left; h rows under the roof, its front below)."""
    def pick(i, n, k):
        return 0 if i == 0 else k - 1 if i == n - 1 else min(1, k - 1) if k < 5 else (1 if i < (n - 1) // 2 else
                                                                                      k // 2 if i == (n - 1) // 2 else k - 2)
    walls = [["Timber_Thin_Plank008", "Timber_Thin_Plank001", "Timber_Thin_Plank005"],
             ["Timber_Thin_Plank004", "Plank001", "Timber_Thin_Plank002"],
             ["Timber_Thin_Plank007", "Timber_Thin_Plank003", "Timber_Thin_Plank006"]]
    roof = [["Thatch_Roof%03d" % (r * 3 + c + 1) for c in range(3)] for r in range(5)]
    for j in range(h):
        for i in range(w):
            t = walls[pick(j, h, 3)][pick(i, w, 3)]
            atlas.put(gx + i, gy + j, "%s+Roof(%s.%02d)" % (t, roof[pick(j, h, 5)][pick(i, w, 3)], grp))
            atlas.taken.add((gx + i, gy + j))
    door = gx + (w // 2 if door_side == 0 else 1 if door_side < 0 else w - 2)
    for i in range(w):
        x = gx + i
        if x == door:
            atlas.put(x, gy + h, "Door001")
        elif i in (1, w - 2) and w >= 5:
            atlas.put(x, gy + h, "Timber001+Decor(Timber_Window001)")
        else:
            atlas.put(x, gy + h, "Timber001")
        atlas.taken.add((x, gy + h))
    atlas.set(gx + 1, gy + 1, decor="Bed001")                     # (a bed against the back wall, its foot below)
    atlas.set(gx + 1, gy + 2, decor="Bed002")
    if w >= 5:
        atlas.set(gx + w - 2, gy + 1, decor="Table001")
    return door, gy + h + 1


def boardwalk(atlas, a, b):
    """A boardwalk from a to b: along, then up or down (over water and marsh alike)."""
    (x0, y0), (x1, y1) = a, b
    for x in range(min(x0, x1), max(x0, x1) + 1):
        if (x, y0) not in atlas.taken:
            atlas.set(x, y0, tile="Boardwalk001", decor="")
            atlas.roads.add((x, y0))
    for y in range(min(y0, y1), max(y0, y1) + 1):
        if (x1, y) not in atlas.taken:
            atlas.set(x1, y, tile="Boardwalk001", decor="")
            atlas.roads.add((x1, y))


def fen(atlas):
    peaks, cells = [], []
    for name in atlas.maps:
        mx, my = (int(v) for v in name.split(",")[:2])
        for y in range(YT):
            for x in range(XT):
                gx, gy = mx * XT + x, my * YT + y
                if my in SEA_Y or not land(gx, gy):
                    atlas.set(gx, gy, tile="Water001", decor="")
                    LAND.GROUND[(gx, gy)] = "Water001"
                elif mountain(gx, gy):
                    peaks.append((gx, gy))
                    LAND.GROUND[(gx, gy)] = "Peak001"
                    atlas.set(gx, gy, tile="Peak%03d" % (1 + int(h01("pk", gx, gy) * 6)), decor="")
                elif any(not land(gx + dx, gy + dy) for dx in (-2, 0, 2) for dy in (-2, 0, 2)):
                    atlas.set(gx, gy, tile="Sand001", decor="")
                    LAND.GROUND[(gx, gy)] = "Sand001"
                else:
                    pool = fbm(gx, gy, 9, 957) > 0.62 and abs(gx - SQUARE[0]) + abs(gy - SQUARE[1]) > 22
                    if pool:
                        lily = h01("lily", gx, gy) < 0.12
                        atlas.set(gx, gy, tile="Water001",
                                  decor="Lily_Pads%03d" % (1 + int(h01("lp", gx, gy) * 4)) if lily else "")
                        LAND.GROUND[(gx, gy)] = "Water001"
                    else:
                        r = h01("fen", gx, gy)
                        decor = "Reeds001" if r < 0.14 else "Bog_Myrtle00%d" % (1 + int(r * 100) % 2) if r < 0.19 else \
                            "Willow_Tree001" if r < 0.23 else ""
                        atlas.set(gx, gy, tile="Marsh001", decor=decor)
                        LAND.GROUND[(gx, gy)] = "Marsh001"
                    cells.append((gx, gy))
    if peaks:
        xs, ys = [c[0] for c in peaks], [c[1] for c in peaks]
        LAND.repeak(atlas, min(xs), min(ys), max(xs), max(ys))
    grid = {c: LAND.GROUND[c] for c in LAND.GROUND}            # (the pools' and the coast's diagonal shores)
    LAND.smooth_shores(grid, [c for c in grid if grid[c] == "Water001"])
    for c, t in grid.items():
        if t != LAND.GROUND[c] and "Lily" not in atlas.decor(*c):
            atlas.set(c[0], c[1], tile=t, decor="")


def village(atlas):
    cx, cy = SQUARE
    for gx in range(cx - 4, cx + 5):                           # the square: boardwalk, a well of sorts, a notice
        for gy in range(cy - 2, cy + 3):
            atlas.set(gx, gy, tile="Boardwalk001", decor="")
            atlas.roads.add((gx, gy))
            atlas.taken.add((gx, gy))
    atlas.place_id(cx, cy, "Mirefold_Square")
    fronts = []
    for k, (hx, hy) in enumerate(HUTS):
        w, h = 5 + k % 2, 4
        for gx in range(hx - 1, hx + w + 1):                   # (dry ground under it)
            for gy in range(hy - 1, hy + h + 2):
                atlas.set(gx, gy, tile="Marsh001", decor="")
        m, _, _ = atlas.at(hx, hy)
        grp = 1 + sum(1 for j in range(k) if atlas.at(*HUTS[j])[0] is m)
        fronts.append(hut(atlas, hx, hy, w, h, grp, (-1, 0, 1)[k % 3]))
    for door in fronts:
        boardwalk(atlas, door, (cx, cy))
    boardwalk(atlas, (cx + 4, cy), (-24, 86))                 # (out to the beach and the way along the range)
    for k, (kind, pid, name) in enumerate(PEOPLE):
        x, y = cx - 3 + k * 2, cy + (2 if k % 2 else -1)    # (cy + 1 is a map's top row)
        zone = atlas.zone(cx - 9, cy - 6, cx + 9, cy + 6, x, y)
        extra = "Attitude=Good Zone=%s Pause=3-9 Id=%s Name=%s" % (zone, pid, name)
        atlas.line(x, y, "NPC", kind, extra, dy=-8)
    for k in range(6):                                          # frogs and ducks round the pools
        x, y = cx - 30 + k * 11, cy + (-14 if k % 2 else 16)
        if atlas.inside(x, y) and atlas.tile(x, y).startswith(("Marsh", "Water", "Lily")):
            atlas.line(x, y, "NPC", "Frog" if k % 3 else "Duck",
                       "Attitude=Passive Zone=%s" % atlas.zone(x - 5, y - 4, x + 5, y + 4, x, y), dy=-8)


def range_beach():
    """The West Range's north end on 0,4,0: its first peaks worn back to sand, so the beach runs on into the fen."""
    m = Map("0,4,0")
    changed = False
    for y in range(2, 4):
        for x in range(1, 10):
            if m.tile(x, y).startswith(("Peak", "Water")):       # (and the inlet between them: the beach whole)
                m.set(x, y, tile="Sand001", decor="")
                changed = True
    if changed:
        m.save()
    m = Map("1,4,0")                                            # (and on east, round the range's last peak: a whole one)
    changed = False
    for x, y in ((22, 1), (23, 1), (24, 1), (25, 1), (24, 2), (25, 2)):
        if m.tile(x, y).startswith(("Peak", "Water")):
            m.set(x, y, tile="Sand001", decor="")
            changed = True
    if changed:
        m.save()


def data():
    def add(path, section, key, value):
        s = open(path, "rb").read().decode("cp1252")
        if re.search(r"(?m)^%s=" % re.escape(key), s):
            return s
        i = s.index("[%s]" % section)
        j = s.index("\r\n", i) + 2
        s = s[:j] + "%s=%s\r\n" % (key, value) + s[j:]
        open(path, "wb").write(s.encode("cp1252"))
        return s
    wm = os.path.join(ROOT, "data", "WorldMap.ini")
    add(wm, "Towns", "Mirefold", "Mirefold_Square")
    add(wm, "Regions", "The Mirefen", "-7,5,0 12 10")
    amb = os.path.join(ROOT, "data", "Ambient.ini")
    for mx in FEN_X:
        for my in FEN_Y:
            add(amb, "Maps", "%d,%d,0" % (mx, my), "Marsh")


def main():
    names = ["%d,%d,0" % (x, y) for x in FEN_X for y in list(FEN_Y) + list(SEA_Y)]
    atlas = Atlas(names)
    fen(atlas)
    village(atlas)
    atlas.save()
    range_beach()
    data()
    print("The Mirefen and Mirefold: %d maps" % len(names))


if __name__ == "__main__":
    main()
