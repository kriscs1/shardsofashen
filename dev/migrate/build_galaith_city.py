"""Galaith redrawn (the owner's to-do, dev\\Roadmap.md group 9): open to the sea on its west and south, its mountains
natural to the north and east, laid out in quarters, its mine in the mountains north of it.

  * The ground: the sea west of the city and south of it (a beach, a quay and a pier at the harbour gate), mountains
    to the north (peaks of all sizes, their edge wandering) meeting the sea in the north-west; the dragon's field and the
    pass to the east as they were (the maps east of the east wall are left alone).
  * The walls: white stone round the city, burnt black on the side that faces the dragon; their outline steps in and
    out (towers at every turn); the barred east gate onto the field (GalaithQuest>=2) where it was, so the field and the
    pass meet it; a harbour gate in the south wall; a back gate north to the mine.
  * The quarters: the Royal quarter (north-west, walled inside the walls: the palace and its gardens); the Nobles'
    (north: Parliament, City Hall, the cathedral, the hotel, the banks, the grand houses, gardens); the Merchants'
    (the middle: the market square, the shops, taverns, the smithy, the armoury, the hospital, the police); the Commons
    (south and east, far from the palace: small houses, taverns, the barracks by the east gate). Each its own paving:
    marble, flagstones, cobbles, dirt.
  * Every building as it was (lifted whole: its walls, roof, furniture, people, Ids, locks and place names) and set
    down in its quarter, facing a street; the square's stalls and shardstone on the new square; the townsfolk who walk
    the streets on its streets; the notices at its streets' ends. So every script, quest and place name still works.
  * The mine moved north: its level -11,14,-1 is -7,11,-1 now, and what names it (the mouth, the ladder, the seam
    builder) too. The palace's entry script (Throne Jimmy) goes with the palace.

Run once: it reads the city as it is and writes the new one (a second run finds it done and stops).

  python -I "dev\\migrate\\build_galaith_city.py" [--dry]   (then build_minimaps.py, validate.py)
"""
import os
import random
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, XT, YT                      # noqa: E402
from atlas import Atlas, fbm, h01                       # noqa: E402
import land as LAND                                     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
MAKER = "build_galaith_city.py"
TW = 32
OLD_X, OLD_Y = range(-12, -3), range(11, 19)           # (the city's maps as they were: x -12..-4, rows 11..18)
NEW_X, NEW_Y = range(-13, 0), range(9, 21)             # (the maps drawn now: the field's own, east of the wall, kept)
EAST = -78                                              # the east wall (the field's gate: as it was)
GATE = 14 * YT + 10                                     # the east gate's first row
WEST, NORTH, SOUTH = -268, 263, 381                     # the walls' outer bounds
MINE_OLD, MINE_NEW = "-11,14,-1", "-7,11,-1"
MINE_MOUTH = (-170, 248)                                 # (in the mountains north of the back gate)
AVENUE_X = -176                                          # the north-south avenue (harbour gate to the back gate)
ROYAL = (-267, 264, -224, 300)                          # the Royal quarter's walls (inside the city)
QUARTERS = {   # name: (x1, y1, x2, y2), its paving, its street rows (the north side of each faces it)
    "Nobles": ((-222, 264, -104, 302), "Marble_Paving001"),
    "Merchants": ((-267, 306, -104, 344), "Cobble001"),
    "Commons": ((-267, 346, -82, 380), "Dirt001"),
    "Eastgate": ((-102, 264, -82, 344), "Dirt001"),
}
DONE = os.path.join(ROOT, "dev", "migrate", ".galaith_redrawn")
FIELD_KEEP = lambda gx: gx > EAST                       # (the cells east of the east wall: as they were, where they were)
KEPT = set()                                            # (cells copied over as they were)


# ================================================================== lifting the city as it is
ENT_KINDS = ("NPC", "StaticObject", "MapItem")


def mxy(name):
    p = name.split(",")
    return int(p[0]), int(p[1])


def old_maps():
    out = {}
    for mx in OLD_X:
        for my in OLD_Y:
            name = "%d,%d,0" % (mx, my)
            if os.path.exists(os.path.join(ROOT, "maps", name + ".txt")):
                out[name] = Map(name)
    return out


class Lifted:
    """Everything on the old maps by world cell: the cell's text, and the map lines (things, Ids, locks, triggers) by
    the world cell they stand on."""

    def __init__(self, maps):
        self.cell = {}
        self.lines = []                   # (kind, gx, gy, map line, map name)
        for name, m in maps.items():
            mx, my = mxy(name)
            for y in range(1, YT + 1):
                for x in range(1, XT + 1):
                    self.cell[(mx * XT + x - 1, my * YT + y - 1)] = m.rows[y - 1][x - 1]
            for ln in m.ents:
                p = ln.split("\t")
                if p[0] in ENT_KINDS and len(p) >= 4:
                    w, h = 32, 32
                    gx = mx * XT + int((float(p[2]) + w / 2) // TW)
                    gy = my * YT + int((float(p[3]) + h - 4) // TW)
                elif p[0] in ("Id", "Trigger") and len(p) >= 4:
                    gx, gy = mx * XT + int(p[2]) - 1, my * YT + int(p[3]) - 1
                elif p[0] == "Lock" and len(p) >= 3:
                    gx, gy = mx * XT + int(p[1]) - 1, my * YT + int(p[2]) - 1
                else:
                    continue
                self.lines.append((p[0], gx, gy, ln, name))

    def roof_groups(self):
        """{(map, group): set of cells} of every roof."""
        out = {}
        for c, text in self.cell.items():
            m = re.search(r"\+Roof\(([^)]*)\.(\d+)\)", text)
            if m:
                name = "%d,%d,0" % (c[0] // XT, c[1] // YT)
                out.setdefault((name, m.group(2)), set()).add(c)
        return out


ROLES = [   # (what's in it, by its people's names) -> what it is
    ("palace", ("King_Rupert", "Royal_Guard", "Guard_Captain")), ("parliament", ("Chancellor", "Speaker")),
    ("hall", ("Archivist", "Clerk")), ("cathedral", ("Priest",)), ("hotel", ("Hotelier",)), ("bank", ("Banker",)),
    ("hospital", ("Doctor", "Nurse")), ("police", ("Constable", "Sheriff")), ("barracks", ("Soldier",)),
    ("tavern", ("Barkeep", "Barmaid")), ("smithy", ("Smith",)), ("armoury", ("Armourer",)),
    ("shop", ("Baker", "Butcher", "Fishmonger", "Greengrocer", "Tailor", "Cobbler")),
]
QUARTER_OF = {"palace": "Royal", "parliament": "Nobles", "hall": "Nobles", "cathedral": "Nobles", "hotel": "Nobles",
              "bank": "Nobles", "hospital": "Merchants", "police": "Merchants", "tavern": "Merchants",
              "smithy": "Merchants", "armoury": "Merchants", "shop": "Merchants", "barracks": "Eastgate"}


class Block:
    """A building lifted whole: its cells (world rect x1..x2, y1..y2) and the map lines on them."""

    def __init__(self, lifted, cells):
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        self.x1, self.y1, self.x2, self.y2 = min(xs), min(ys), max(xs), max(ys) + 1      # (+ its front wall's row)
        self.cells = {(x, y): lifted.cell.get((x, y), "Grass001") for x in range(self.x1, self.x2 + 1)
                      for y in range(self.y1, self.y2 + 1)}
        self.lines = [ln for ln in lifted.lines if self.x1 - 1 <= ln[1] <= self.x2 + 1 and
                      self.y1 <= ln[2] <= self.y2 + 2]
        names = " ".join(ln[3].split("\t")[1] for ln in self.lines if ln[0] == "NPC")
        self.role = next((r for r, words in ROLES if any(w in names for w in words)), "house")
        self.w, self.h = self.x2 - self.x1 + 1, self.y2 - self.y1 + 1
        self.size = self.w * self.h


def lift_blocks(lifted):
    blocks = []
    for (name, grp), cells in lifted.roof_groups().items():
        if len(cells) >= 4:
            blocks.append(Block(lifted, cells))
    # (a building's roof in two groups, or two buildings sharing walls: one block)
    blocks.sort(key=lambda b: -b.size)
    out = []
    for b in blocks:
        if any(o.x1 <= b.x1 and b.x2 <= o.x2 and o.y1 <= b.y1 and b.y2 <= o.y2 for o in out):
            continue
        out.append(b)
    taken = set()
    for b in out:                                               # (a line on the margin of two: the bigger one's)
        b.lines = [t for t in b.lines if id(t) not in taken]
        taken.update(id(t) for t in b.lines)
    used = {id(t) for b in out for t in b.lines}               # (the map lines that go with a building)
    return out, used


# ================================================================== the new ground
def coast_west(gy):
    return -312 + int(22 * fbm(0, gy, 40, 901) + 6 * fbm(0, gy, 9, 902))


def coast_south(gx):
    return 398 + int(8 * fbm(gx, 0, 24, 903) + 3 * fbm(gx, 0, 7, 904))


def mountains_north(gx):
    return 252 - int(16 * fbm(gx, 0, 26, 905) + 6 * fbm(gx, 0, 8, 906))


def is_sea(gx, gy):
    """West and south of the coast; and the north-west, where the mountains run down to the sea."""
    if gx < coast_west(gy) or gy > coast_south(gx):
        return True
    return gx + (gy - 189) * 0.9 < -250 + int(20 * fbm(gx, gy, 18, 907))


def jog(t, seed, near_gate):
    """How far a wall stands in from its line at t: in steps of three, up to six, none by a gate."""
    if near_gate:
        return 0
    return 3 * int(2.99 * fbm(t, seed, 30, seed))


def city(gx, gy):
    """Inside the walls (their own cells too): a rectangle whose sides step in and out, its corners stepped in."""
    if not (WEST <= gx <= EAST and NORTH <= gy <= SOUTH):
        return False
    if gx < WEST + jog(gy, 911, False) or gy < NORTH + jog(gx, 912, abs(gx - AVENUE_X) < 8) or \
            gy > SOUTH - jog(gx, 913, abs(gx - AVENUE_X) < 8) or gx > EAST - jog(gy, 914, abs(gy - GATE) < 6):
        return False
    for cx, cy, sx, sy in ((WEST, SOUTH, 1, -1), (EAST, NORTH, -1, 1), (EAST, SOUTH, -1, -1)):
        steps = [(9, 4), (5, 8)]                                               # (two steps in at each corner)
        for w, h in steps:
            if (gx - cx) * sx < w and (gy - cy) * sy < h:
                return False
    return True


def wall_cells():
    cells = set()
    for gx in range(WEST - 1, EAST + 2):
        for gy in range(NORTH - 1, SOUTH + 2):
            if city(gx, gy) and any(not city(gx + dx, gy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                cells.add((gx, gy))
    return cells


def royal_wall_cells():
    x1, y1, x2, y2 = ROYAL
    return {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)
            if (x in (x1, x2) or y in (y1, y2)) and city(x, y)} - wall_cells()


def lay_walls(atlas, cells, gaps, burnt_from=None, keep=()):
    """The wall round cells: battlements over a face east-west, one tile north-south, a tower (over its face) at every
    turn, end and T; burnt black east of burnt_from; nothing on gaps (gates)."""
    walls = set(cells) - set(gaps)
    face = set()
    for gx, gy in sorted(walls, key=lambda c: (c[1], c[0])):
        if (gx, gy) in face:
            continue
        n = lambda dx, dy: (gx + dx, gy + dy) in walls or ((gx + dx, gy + dy) in face and dy == -1)  # noqa: E731
        e, w, s, nn = n(1, 0), n(-1, 0), n(0, 1), n(0, -1)
        kind = "Burnt_Wall%03d" if burnt_from is not None and gx >= burnt_from else "Galaith_Wall%03d"
        if (e or w) and not (s or nn):
            top, under = 1, 4
        elif (s or nn) and not (e or w):
            top, under = 2, 0
        else:
            top, under = 3, 5
        atlas.set(gx, gy, tile=kind % top, decor="")
        atlas.taken.add((gx, gy))
        if under and (gx, gy + 1) not in keep:
            atlas.set(gx, gy + 1, tile=kind % under, decor="")
            face.add((gx, gy + 1))
            atlas.taken.add((gx, gy + 1))
            walls.discard((gx, gy + 1))
    return face


def ground(atlas):
    """Sea, beach, mountains and the valley floor of every new map; the cells east of the east wall left as they were."""
    peaks = []
    for name in atlas.maps:
        mx, my = mxy(name)
        for y in range(YT):
            for x in range(XT):
                gx, gy = mx * XT + x, my * YT + y
                if (gx, gy) in KEPT:
                    continue
                if is_sea(gx, gy):
                    atlas.set(gx, gy, tile="Water001", decor="")
                elif any(is_sea(gx + dx, gy + dy) for dx in (-2, 0, 2) for dy in (-2, 0, 2)):
                    atlas.set(gx, gy, tile="Sand001", decor="")
                elif gy < mountains_north(gx) and not (abs(gx - AVENUE_X - 6) <= 1 and gy > MINE_MOUTH[1]):
                    peaks.append((gx, gy))
                else:
                    r = h01("vale", gx, gy)
                    decor = "" if city(gx, gy) else ("Tree002" if r < 0.04 else "Rock001" if r < 0.06 else
                                                     "Flowers00%d" % (1 + int(r * 100) % 3) if r < 0.1 else "")
                    atlas.set(gx, gy, tile="Grass001", decor=decor)
    for c in peaks:
        LAND.GROUND[c] = "Peak001"
        atlas.set(c[0], c[1], tile="Peak%03d" % (1 + int(h01("pk", *c) * 6)), decor="")
    xs, ys = [c[0] for c in peaks], [c[1] for c in peaks]
    if peaks:
        LAND.repeak(atlas, min(xs), min(ys), max(xs), max(ys))


# ================================================================== streets and quarters
def pave(atlas, cells, tile):
    for c in cells:
        if atlas.inside(*c) and c not in atlas.taken:
            atlas.set(c[0], c[1], tile=tile, decor="")
            atlas.roads.add(c)


def streets(atlas):
    """The avenues, and each quarter's streets every 9 rows: [(quarter, y, x1, x2)] (the buildings go on their north
    side)."""
    rows = []
    # the main avenue: the east gate to the Royal quarter's gate
    for gx in range(ROYAL[2] + 1, EAST):
        tile = "Marble_Paving001" if gx < -200 else "Cobble001"
        pave(atlas, [(gx, GATE), (gx, GATE + 1)], tile)
    # the north-south avenue: the harbour gate to the back gate
    for gy in range(NORTH + 1, SOUTH):
        tile = "Marble_Paving001" if gy < 304 else "Cobble001" if gy < 352 else "Dirt001"
        pave(atlas, [(AVENUE_X, gy), (AVENUE_X + 1, gy)], tile)
    for q, ((x1, y1, x2, y2), tile) in QUARTERS.items():
        y = y1 + 8
        while y <= y2:
            rows.append((q, y, x1, x2))
            y += 9
    return rows


def pave_rows(atlas, rows, placed):
    """Each street where its buildings stand (and on to the nearest avenue or lane), lanes joining a quarter's rows at
    their ends: straight and paved near the middle, dirt further out."""
    for q, y, x1, x2 in rows:
        tile = QUARTERS[q][1]
        xs = [(x, x + w) for (qq, yy, x, w) in placed if qq == q and yy == y]
        if not xs:
            continue
        a, b = min(x for x, _ in xs) - 2, max(e for _, e in xs) + 1
        if a > AVENUE_X + 1:
            a = AVENUE_X + 1
        elif b < AVENUE_X:
            b = AVENUE_X
        cells = [(x, y) for x in range(a, b + 1) if city(x, y)]
        pave(atlas, cells, tile if abs((a + b) // 2 - AVENUE_X) < 70 else "Dirt001")
        for x in (a, b):                                       # (a lane down from each end to the next street)
            pave(atlas, [(x, yy) for yy in range(y + 1, y + 10) if city(x, yy) and (x, yy) not in atlas.taken],
                 "Dirt001")


def greenery(atlas):
    """What's open inside the walls: gardens and greens, trees, flowers, a bench now and then (thicker among the
    nobles), so no plot stands bare."""
    for name, m in atlas.maps.items():
        mx, my = mxy(name)
        for y in range(YT):
            for x in range(XT):
                c = (mx * XT + x, my * YT + y)
                if not city(*c) or c in atlas.taken or c in atlas.roads or atlas.tile(*c) != "Grass001":
                    continue
                if any((c[0] + dx, c[1] + dy) in atlas.roads or (c[0] + dx, c[1] + dy) in atlas.taken
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    continue
                r = h01("green", *c)
                rich = QUARTERS["Nobles"][0][1] <= c[1] <= QUARTERS["Nobles"][0][3] or c[0] < ROYAL[2]
                if r < (0.07 if rich else 0.035):
                    atlas.set(c[0], c[1], decor="Tree002" if h01("kind", *c) < 0.6 else "Oak_Tree001")
                elif r < (0.12 if rich else 0.06):
                    atlas.set(c[0], c[1], decor="Flowers00%d" % (1 + int(r * 1000) % 3))
                elif r < 0.075 and not rich:
                    atlas.set(c[0], c[1], decor="Bush001")


def royal(atlas):
    """The Royal quarter: its own wall (a gate onto the avenue), lawns, hedged paths, a fountain."""
    x1, y1, x2, y2 = ROYAL
    for gx in range(x1 + 1, x2):
        for gy in range(y1 + 1, y2):
            if city(gx, gy) and (gx, gy) not in atlas.taken:
                r = h01("royal", gx, gy)
                atlas.set(gx, gy, tile="Grass001", decor="Flowers001" if r < 0.05 else "Bush001" if r < 0.08 else "")
    pave(atlas, [((x1 + x2) // 2, gy) for gy in range(y1 + 1, y2 + 1)] +
         [((x1 + x2) // 2 + 1, gy) for gy in range(y1 + 1, y2 + 1)], "Marble_Paving001")
    mid = (x1 + x2) // 2                                        # (the gate: in the south wall, at the path's end)
    gate = [(mid, y2), (mid + 1, y2)]
    lay_walls(atlas, royal_wall_cells(), gate, keep=wall_cells())
    lane = [(x, y) for x in (mid, mid + 1) for y in range(y2, GATE + 2)] +         [(x, y) for x in range(mid, x2 + 1) for y in (GATE, GATE + 1)]     # (and on to the avenue)
    pave(atlas, lane, "Marble_Paving001")


# ================================================================== setting the buildings down
def place_blocks(atlas, blocks, rows, rng):
    """Each building on the north side of a street in its quarter (biggest first), its front on the street's row
    above, within one map, a gap round it. Returns {block: (dx, dy)} and the ones that didn't fit."""
    spots = {q: [] for q in QUARTERS}
    for q, y, x1, x2 in rows:                                   # (each row in two: either side of the avenue)
        spots[q].append([y, x1 + 2, AVENUE_X - 2, x1 + 2])      # (street y; the next free x; the row's end; its start)
        spots[q].append([y, AVENUE_X + 4, x2 - 1, AVENUE_X + 4])
    where, left, placed = {}, [], []
    street = {(x, y) for _, y, x1, x2 in rows for x in range(x1, x2 + 1)}     # (paved after: kept clear now)
    houses = sorted((b for b in blocks if b.role == "house"), key=lambda b: -b.size)
    rank = {id(b): i / max(1, len(houses)) for i, b in enumerate(houses)}

    def fits(x, y0, b):
        if (x // XT) != ((x + b.w - 1) // XT) or (y0 // YT) != ((y0 + b.h - 1) // YT):
            return False                                          # (one map: its roof one group)
        cells = [(x + i, y0 + j) for i in range(-1, b.w + 1) for j in range(-1, b.h)]
        return all(city(*c) and c not in atlas.taken and c not in atlas.roads and c not in street for c in cells)

    for b in sorted(blocks, key=lambda b: -b.size):
        if b.role == "palace":
            continue
        home = QUARTER_OF.get(b.role) or ("Nobles" if rank[id(b)] < 0.25 else "Merchants" if rank[id(b)] < 0.45 else
                                          "Eastgate" if rank[id(b)] > 0.92 else "Commons")
        order = [home, "Merchants", "Commons", "Eastgate", "Nobles"]
        done = False
        for q in order:
            for row in sorted(spots.get(q, []), key=lambda r: r[1] - r[3]):   # (the emptiest row first)
                y, x, end, _ = row
                y0 = y - b.h
                while x + b.w - 1 <= end:
                    if fits(x, y0, b):
                        where[id(b)] = (x - b.x1, y0 - b.y1)
                        for i in range(b.w):
                            for j in range(b.h):
                                atlas.taken.add((x + i, y0 + j))
                        row[1] = x + b.w + 2 + rng.randint(0, 3)
                        placed.append((q, y, x, b.w))
                        done = True
                        break
                    x += 1
                if done:
                    break
            if done:
                break
        if not done:
            left.append(b)
    return where, left, placed


def palace_spot(atlas, b):
    x1, y1, x2, y2 = ROYAL
    x = max(x1 + 3, (x1 + x2) // 2 - b.w // 2)
    y = y1 + 3
    while (y // YT) != ((y + b.h - 1) // YT) and y + b.h < y2 - 2:
        y += 1                                                  # (one map, up and down too: its roof one group)
    while (x // XT) != ((x + b.w - 1) // XT) and x + b.w < x2 - 2:
        x += 1                                                  # (within one map, clear of the quarter's walls)
    for i in range(b.w):
        for j in range(b.h):
            atlas.taken.add((x + i, y + j))
    return x - b.x1, y - b.y1


GROUPS = {}


def new_group(map_name):
    GROUPS[map_name] = GROUPS.get(map_name, 0) + 1
    return GROUPS[map_name]


def set_block(atlas, b, dx, dy):
    """The building's cells and map lines, moved by dx, dy (its roofs a new group on the map it lands on)."""
    regroup = {}
    for (gx, gy), text in b.cells.items():
        nx, ny = gx + dx, gy + dy
        m, _, _ = atlas.at(nx, ny)
        if m is None:
            continue

        def sub(mt):
            key = (m.name, mt.group(2), b)
            if key not in regroup:
                regroup[key] = new_group(m.name)
            return "+Roof(%s.%02d)" % (mt.group(1), regroup[key])
        atlas.put(nx, ny, re.sub(r"\+Roof\(([^)]*)\.(\d+)\)", sub, text))
        atlas.taken.add((nx, ny))
    for kind, gx, gy, ln, old in b.lines:
        put_line(atlas, ln, old, dx, dy)


def put_line(atlas, ln, old, dx, dy, at=None):
    """A map line from map old, moved by dx, dy tiles (or to world cell at), onto the map it lands on: its pixels or
    tiles, and its Zone/Chase/Nap/Patrol tiles, local to that map."""
    p = ln.split("\t")
    omx, omy = mxy(old)
    if p[0] in ENT_KINDS:
        gx = omx * XT * TW + float(p[2]) + dx * TW
        gy = omy * YT * TW + float(p[3]) + dy * TW
        if at is not None:
            gx, gy = at[0] * TW, at[1] * TW - 8
        mx, my = int((gx + 16) // (XT * TW)), int((gy + 28) // (YT * TW))
        name = "%d,%d,0" % (mx, my)
        if name not in atlas.maps:
            return False
        tdx, tdy = (omx - mx) * XT + (dx if at is None else 0), (omy - my) * YT + (dy if at is None else 0)
        p[2], p[3] = "%d" % (gx - mx * XT * TW), "%d" % (gy - my * YT * TW)
        if len(p) > 4:
            p[4] = shift_opts(p[4], tdx, tdy) if at is None else re.sub(r"(Zone|Chase)=\S+", "", p[4]).strip() + \
                (" Zone=%s" % atlas.zone(at[0] - 3, at[1] - 3, at[0] + 3, at[1] + 3) if p[0] == "NPC" else "")
        atlas.maps[name].ents.append("\t".join(p))
        return True
    i = 1 if p[0] == "Lock" else 2
    gx, gy = omx * XT + int(p[i]) - 1 + dx, omy * YT + int(p[i + 1]) - 1 + dy
    m, x, y = atlas.at(gx, gy)
    if m is None:
        return False
    p[i], p[i + 1] = str(x), str(y)
    m.ents.append("\t".join(p))
    return True


def shift_opts(opts, dx, dy):
    def pts(v):
        nums = [int(n) for n in re.findall(r"-?\d+", v)]
        out = [str(n + (dx if k % 2 == 0 else dy)) for k, n in enumerate(nums)]
        seps = re.findall(r"[,;]", v)
        return "".join(o + (seps[k] if k < len(seps) else "") for k, o in enumerate(out))
    return re.sub(r"\b(Zone|Chase|Nap|Patrol|Roost)=([-\d,;]+)", lambda m: m.group(1) + "=" + pts(m.group(2)), opts)


# ================================================================== the rest: the square, the people, the mine
SQUARE = (AVENUE_X - 12, 318)
SQ_W, SQ_H = 19, 9


def lay_square(atlas):
    cx, cy = SQUARE
    for gx in range(cx - SQ_W // 2, cx + SQ_W // 2 + 1):
        for gy in range(cy - SQ_H // 2, cy + SQ_H // 2 + 1):
            if city(gx, gy):
                atlas.set(gx, gy, tile="Marble_Paving001", decor="")
                atlas.roads.add((gx, gy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        atlas.taken.add((gx + dx, gy + dy))


def square(atlas, lifted, used, rng):
    """The market square in the middle of the Merchants' quarter, and the stalls, shardstone and all that stood on the
    old one, set on it as they stood."""
    ids = [ln for ln in lifted.lines if ln[0] == "Id" and ln[3].split("\t")[1] == "Galaith_Square"]
    cx0, cy0 = ids[0][1], ids[0][2]
    cx, cy = SQUARE                                             # (its middle now)
    moved = 0
    for t in lifted.lines:
        kind, gx, gy, ln, old = t
        if id(t) in used or abs(gx - cx0) > 10 or abs(gy - cy0) > 7:
            continue
        if kind in ("Id", "StaticObject", "NPC"):             # (the stalls, the shardstone and its Id, the stallholders)
            if put_line(atlas, ln, old, cx - cx0, cy - cy0):
                used.add(id(t))
                moved += 1
    return moved


def loose_people(atlas, lifted, used, rows, rng):
    """Everyone and everything not in a building or on the square: on a street of the quarter they belong to (the
    notices at its ends, the townsfolk along it)."""
    street_cells = sorted(c for c in atlas.roads if city(*c) and c not in atlas.taken)
    n = 0
    for t in lifted.lines:
        kind, gx, gy, ln, old = t
        if id(t) in used or FIELD_KEEP(gx):
            continue
        name = ln.split("\t")[1]
        if kind in ("Lock", "Trigger") or name in ("Galaith_West_Gate", "Galaith_Mine", "Galaith_Square") or \
                name.startswith(("Bones", "Galaith_Dragon")):
            continue
        if kind == "Id":
            continue
        if kind == "MapItem" or (kind == "StaticObject" and not name.startswith(("Notice", "Sign", "Galaith")) and
                                 "Id=" not in ln):
            continue                                            # (a barrel, a tree in a garden: drawn anew)
        c = street_cells[rng.randrange(len(street_cells))]
        if put_line(atlas, ln, old, 0, 0, at=(c[0], c[1])):
            used.add(id(t))
            n += 1
    return n


def gates(atlas):
    """The east gate (barred till the dragon's dead) where it was, the harbour gate and its quay and pier, the back
    gate to the mine and the mine's mouth."""
    for k in (0, 1):
        atlas.set(EAST, GATE + k, tile="Burnt_Gate005", decor="")
        m, x, y = atlas.at(EAST, GATE + k)
        m.ents.append("Lock\t%d\t%d\t$Attr.GalaithQuest>=2\tThe gate is barred. Something huge breathes behind you."
                      % (x, y))
    atlas.place_id(EAST - 1, GATE, "Galaith_West_Gate")
    hx = AVENUE_X                                               # the harbour gate: a gap in the south wall
    for gy in range(SOUTH - 1, coast_south(hx) + 1):
        for gx in (hx, hx + 1):
            atlas.set(gx, gy, tile="Cobble001", decor="")
            atlas.roads.add((gx, gy))
    quay = [(gx, gy) for gx in range(hx - 9, hx + 11) for gy in range(SOUTH + 1, coast_south(gx) + 1)]
    pave(atlas, quay, "Cobble001")
    for gy in range(coast_south(hx + 4) + 1, coast_south(hx + 4) + 9):     # (the pier, out into the sea)
        for gx in (hx + 4, hx + 5):
            atlas.set(gx, gy, tile="Boardwalk001", decor="")
    atlas.place_id(hx + 4, coast_south(hx + 4) + 2, "Galaith_Port")
    atlas.line(hx - 3, SOUTH + 2, "NPC", "Fisherman", "Attitude=Good Stand=1 Face=S Id=Galaith_Harbour_Master "
               "Name=Harbour_Master_Pell", dy=-8)
    for gy in range(MINE_MOUTH[1] + 1, NORTH + 2):             # the back gate, and the way up to the mine
        for gx in (AVENUE_X, AVENUE_X + 1):
            atlas.set(gx, gy, tile="Dirt001", decor="")
            atlas.roads.add((gx, gy))
    mx, my = MINE_MOUTH
    atlas.set(mx, my, tile="Mine_Mouth001", decor="")
    m, x, y = atlas.at(mx, my)
    m.ents.append("Lock\t%d\t%d\t$Attr.KingQuest>=1\tThe mine is shut, by the King's order." % (x, y))
    atlas.place_id(mx, my + 1, "Galaith_Mine")
    for gx in range(mx, AVENUE_X):
        atlas.set(gx, my + 1, tile="Dirt001", decor="")
        atlas.roads.add((gx, my + 1))
    return [(AVENUE_X, NORTH), (AVENUE_X + 1, NORTH), (AVENUE_X, SOUTH), (AVENUE_X + 1, SOUTH),
            (EAST, GATE), (EAST, GATE + 1), (ROYAL[2], GATE), (ROYAL[2], GATE + 1)]


def harbour_master_script():
    """The harbour master's words, like every port's (build_estforlan's)."""
    p = os.path.join(ROOT, "data", "Scripts", "Talk to Galaith_Harbour_Master.txt")
    text = ("// Generated by dev\\migrate\\build_galaith_city.py\r\n"
            "01\tDisplay.Conversation\tFisherman\tThe harbour of Galaith. Twenty years the gulls have had it to "
            "themselves.\tGoodbye.\t02\r\n02\tEnd\r\n")
    open(p, "wb").write(text.encode("cp1252"))


def move_mine():
    """The mine's level under its new mouth, and everything that names it."""
    a, b = os.path.join(ROOT, "maps", MINE_OLD + ".txt"), os.path.join(ROOT, "maps", MINE_NEW + ".txt")
    if os.path.exists(a) and not os.path.exists(b):
        shutil.move(a, b)
    mx, my = MINE_MOUTH
    m_name = "%d,%d,0" % (mx // XT, my // YT)
    lx, ly = mx - (mx // XT) * XT, my - (my // YT) * YT                # (0-based tile in its map)
    changes = {"Enter Mine_Mouth": (MINE_OLD, MINE_NEW), "Climb Up Mine_Ladder": (
        "736,344\t-11,14,0", "%d,%d\t%s" % (lx * TW, (ly + 1) * TW, m_name))}
    for script, (old, new) in changes.items():
        p = os.path.join(ROOT, "data", "Scripts", script + ".txt")
        s = open(p, "rb").read().decode("cp1252")
        open(p, "wb").write(s.replace(old, new).encode("cp1252"))
    p = os.path.join(HERE, "build_kings_seam.py")
    s = open(p, "rb").read().decode("utf-8")
    open(p, "wb").write(s.replace('MINE = "%s"' % MINE_OLD, 'MINE = "%s"' % MINE_NEW).encode("utf-8"))


def palace_script(dx, dy, old_map, new_map):
    """The palace's entry script (Throne Jimmy: build_heir_mainland.py, throne_jimmy.py) on the palace's new map."""
    src = os.path.join(ROOT, "data", "Scripts", old_map + ".txt")
    if not os.path.exists(src):
        return
    s = open(src, "rb").read().decode("cp1252")
    omx, omy = mxy(old_map)
    nmx, nmy = mxy(new_map)
    tdx, tdy = (omx - nmx) * XT + dx, (omy - nmy) * YT + dy

    def at(m):
        return "%d,%d" % (int(m.group(1)) + tdx * TW, int(m.group(2)) + tdy * TW)
    def move(text):
        text = re.sub(r"\tAdd\.Entity\t(-?\d+),(-?\d+)\t", lambda m: "\tAdd.Entity\t%s\t" % at(m), text)
        return re.sub(r"\b(Zone|Nap)=([-\d,]+)", lambda m: shift_opts(m.group(0), tdx, tdy), text)
    os.remove(src)
    open(os.path.join(ROOT, "data", "Scripts", new_map + ".txt"), "wb").write(move(s).encode("cp1252"))
    # (the King's own script puts Jimmy on the throne too, on the palace's map: the same move)
    p = os.path.join(ROOT, "data", "Scripts", "Talk to Rupert_On_Throne.txt")
    lines = open(p, "rb").read().decode("cp1252").split("\r\n")
    lines = [move(ln) if "Id=Throne_Jimmy" in ln else ln for ln in lines]
    open(p, "wb").write("\r\n".join(lines).encode("cp1252"))


def carts(stops):
    """Galaith's cart (data\\Carts.ini [Galaith]): its stops along the new avenues."""
    path = os.path.join(ROOT, "data", "Carts.ini")
    s = open(path, "rb").read().decode("cp1252")
    a = s.index("[Galaith]")
    b = s.find("\r\n[", a + 1)
    b = len(s) if b < 0 else b
    head = [ln for ln in s[a:b].split("\r\n") if ln and not ln.startswith("Point")]
    pts = []
    for i, (gx, gy, label) in enumerate(stops):
        mx, my = gx // XT, gy // YT
        pts.append("Point%d=%d,%d,0,%d,%d%s" % (i + 1, mx, my, gx - mx * XT + 1, gy - my * YT + 1,
                                                 "," + label if label else ""))
    rest = s[b:].lstrip("\r\n")
    out = s[:a] + "\r\n".join(head + pts) + "\r\n" + ("\r\n" + rest if rest else "")
    open(path, "wb").write(out.encode("cp1252"))


# ================================================================== all of it
def main(dry=False):
    if os.path.exists(DONE) and not dry:
        print("Galaith's been redrawn already (delete %s to do it again)." % DONE)
        return
    rng = random.Random(14)
    maps = old_maps()
    lifted = Lifted(maps)
    blocks, used = lift_blocks(lifted)
    names = ["%d,%d,0" % (x, y) for x in NEW_X for y in NEW_Y]
    atlas = Atlas(names)
    for name in names:                                          # (the cells east of the wall: as they were)
        mx, my = mxy(name)
        if mx >= -3 and os.path.exists(os.path.join(ROOT, "maps", name + ".txt")):
            atlas.maps.pop(name)                                # (the field and the pass's maps: left alone)
            continue
        if name in maps:                                        # (only the cells east of the wall come over)
            for y in range(YT):
                for x in range(XT):
                    if FIELD_KEEP(mx * XT + x):
                        atlas.maps[name].rows[y][x] = maps[name].rows[y][x]
                        KEPT.add((mx * XT + x, my * YT + y))
            atlas.maps[name].ents = [t[3] for t in lifted.lines if t[4] == name and FIELD_KEEP(t[1])]
    ground(atlas)
    walls = wall_cells()
    gaps = gates(atlas)
    lay_walls(atlas, walls, gaps, burnt_from=EAST - 6)
    royal(atlas)
    rows = streets(atlas)
    lay_square(atlas)
    palace = next((b for b in blocks if b.role == "palace"), None)
    report = {}
    if palace is not None:
        pdx, pdy = palace_spot(atlas, palace)
        set_block(atlas, palace, pdx, pdy)
    where, left, placed = place_blocks(atlas, [b for b in blocks if b is not palace], rows, rng)
    for b in blocks:
        if id(b) in where:
            set_block(atlas, b, *where[id(b)])
            report[b.role] = report.get(b.role, 0) + 1
    for b in left:                                              # (no room: its people on its quarter's streets)
        for t in b.lines:
            used.discard(id(t))
    pave_rows(atlas, rows, placed)
    sq = square(atlas, lifted, used, rng)
    loose = loose_people(atlas, lifted, used, rows, rng)
    greenery(atlas)
    print("Galaith: %d buildings set down (%s); %d didn't fit; %d on the square; %d on the streets" %
          (len(where) + (palace is not None), ", ".join("%s %d" % kv for kv in sorted(report.items())), len(left), sq,
           loose))
    if dry:                                                    # (a look first: the maps to a folder of their own)
        out = dry if isinstance(dry, str) else os.path.join(ROOT, "dev", "Renders", "Galaith dry")
        os.makedirs(out, exist_ok=True)
        for m in atlas.maps.values():
            m.path = os.path.join(out, m.name + ".txt")
            m.save()
        print("dry: the maps in %s" % out)
        return atlas
    atlas.save()
    move_mine()
    harbour_master_script()
    if palace is not None:
        old = "%d,%d,0" % (palace.x1 // XT, palace.y1 // YT)
        new = "%d,%d,0" % ((palace.x1 + pdx) // XT, (palace.y1 + pdy) // YT)
        palace_script(pdx, pdy, old, new)
    carts([(EAST - 3, GATE, "the east gate"), (AVENUE_X + 2, GATE, "the market"), (AVENUE_X + 2, SOUTH - 2, "the harbour"),
           (AVENUE_X + 2, 270, "the nobles' quarter"), (ROYAL[2] + 2, GATE, "the palace")])
    open(DONE, "w").write("redrawn\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--dry") + 1] if "--dry" in sys.argv and len(sys.argv) > sys.argv.index("--dry") + 1
         else "--dry" in sys.argv)
