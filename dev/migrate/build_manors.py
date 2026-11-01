"""Two bandit manors where towns stood, and Fenwick's cathedral made the Drowned Abbey (the owner's wish: the towns'
interesting buildings kept, something new for the ground they left).

  * Fenmoor Hall (in the fens where Fenwick was) and Redrock Manor (on the red hills where Highwatch was): a big stone
    house each, its inside walled into rooms - an entrance hall, a dining hall, a kitchen, a bunk room, the chief's
    study and, behind an iron-bound door, the vault. Bandits hold it (Group: one that sees you raises the house), a
    pair watching the door; traps in the halls; a locked chest in the kitchen and the bunk room, the vault's key in the
    chief's (picked or keyed: Sturdy), the vault's chest the prize; a stash to Search for. Each player's own, once
    (attributes), as every chest is.
  * The Drowned Abbey: Fenwick's cathedral, left standing in the marsh, the dead risen in its pews and its reliquary
    under the altar.
  * Their keys (drawn here: Lair_Key's shape, recoloured), their names on the world map, a way to each from the road.

Safe to run again (what's built is built once; the scripts and the keys' data are written again).

  python -I "dev\\migrate\\build_manors.py"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, TW                       # noqa: E402
import story_kit as SK                                   # noqa: E402
from story_kit import Map                               # noqa: E402

ROOT = W.ROOT
MAKER = "build_manors.py"
ENTITIES = os.path.join(ROOT, "data", "Entities.ini")
MANORS = {   # Id: (the world cell it's built near, its map's ground, the vault's prize, its key's colour, its name)
    "Fenmoor_Hall": ((212, 352), "Marsh001", [("Gold_Coin(s)", 160), ("Emerald", 2), ("Steel_Helm", 1),
                                              ("Storm_Shard", 1), ("Shard", 15)], (90, 140, 120), "Fenmoor Hall"),
    "Redrock_Manor": ((405, 330), "Grass001", [("Gold_Coin(s)", 180), ("Ruby", 2), ("Iron_Platebody", 1),
                                               ("Ember_Shard", 1), ("Shard", 15)], (170, 80, 60), "Redrock Manor"),
}
X1, Y1, X2, Y2 = 3, 4, 22, 17                          # (the house on its map: walls; its front, the door's, is Y2)
DOOR = 12
WALL, THIN = "Stone_Wall001", "Stone_Wall_Thin_Plank"
SPLIT_Y = 11                                            # (the inside wall along the north edge of this row)
SPLIT_X = (9, 15)                                       # (and along the east edge of these columns)


# ================================================================== where
def site(w, near):
    """The map nearest near whose ground is wild all over (room for the house and its yard) and has nothing named."""
    best = None
    for mx in range(near[0] // XT - 2, near[0] // XT + 3):
        for my in range(near[1] // YT - 2, near[1] // YT + 3):
            m = w.maps.get((mx, my))
            if m is None:
                continue
            cells = [m.rows[y][x] for y in range(1, YT - 1) for x in range(1, XT - 1)]
            wild = sum(1 for c in cells if W.natural(c) and not W.watery(c))
            named = any(W.line_id(ln) for ln in m.ents)
            if wild < len(cells) * 0.85 or named:
                continue
            d = abs(mx * XT + 12 - near[0]) + abs(my * YT + 10 - near[1])
            if best is None or d < best[0]:
                best = (d, (mx, my))
    return best[1]


# ================================================================== the house
def put(m, x, y, tile, decor=""):
    m.rows[y - 1][x - 1] = tile + ("+Decor(%s)" % decor if decor else "")


def thin(m, x, y, edges):
    """A thin inside wall on x, y along its edges ("n", "e", "ne"...), on the floor that's there (and its roof)."""
    code = {"n": "001", "e": "002", "w": "004", "ne": "005", "nw": "008"}[edges]
    t, over = m.parts(x, y)
    m.put(x, y, THIN + code, over)


def house(m, ground):
    for y in range(Y1 - 2, Y2 + 3):                         # (its yard: cleared to the ground)
        for x in range(X1 - 2, X2 + 3):
            put(m, x, y, ground if ground != "Marsh001" or y >= Y2 + 1 else "Grass001")
    SK.building(m, X1, Y1, X2, Y2, DOOR, wall=WALL, roof="Slate",
                windows=[x for x in range(X1 + 2, X2 - 1, 3) if abs(x - DOOR) > 1])
    for x in range(X1, X2 + 1):                             # (the inside wall across: dining|vault|study over the rest)
        if SPLIT_X[0] < x <= SPLIT_X[1]:
            continue
        if x in (6, 19):
            continue                                        # (doorways: the dining hall's, the study's)
        thin(m, x, SPLIT_Y, "nw" if x == X1 else "ne" if x in (X2,) + SPLIT_X else "n")
    for x in range(SPLIT_X[0] + 1, SPLIT_X[1] + 1):        # (the vault's front: a stone wall, its iron-bound door)
        t, over = m.parts(x, SPLIT_Y)
        m.put(x, SPLIT_Y, WALL if x != DOOR else "Door002", over)
    for sx in SPLIT_X:
        for y in range(Y1, Y2):
            if y in (14,) or y == SPLIT_Y:                  # (doorways from the hall, west and east)
                continue
            thin(m, sx, y, "ne" if y == Y1 else "e")


FURNITURE = [   # (x, y, decor) inside
    # the dining hall (west, top): a long table, its chairs, the hearth in the back wall
    (4, 7, "Chair003"), (5, 7, "Table001"), (6, 7, "Table001"), (7, 7, "Table001"), (8, 7, "Chair004"),
    (5, 8, "Chair003"), (7, 8, "Chair004"), (4, 4, "Banner001"), (8, 4, "Banner001"),
    # the kitchen (west, bottom): barrels, a counter, shelves
    (4, 11, "Barrel001"), (5, 11, "Barrel002"), (8, 11, "Shelf_Goods001"), (4, 15, "Counter001"),
    (5, 15, "Counter001"),
    # the hall (middle, bottom): plants by the door, banners on the vault's wall
    (10, 16, "Potted_Plant002"), (15, 16, "Potted_Plant004"),
    # the study (east, top): shelves of books, a desk
    (17, 4, "Bookshelf001"), (18, 4, "Bookshelf001"), (21, 4, "Bookshelf001"), (19, 7, "Desk001"),
    (22, 8, "Potted_Plant001"),
    # the bunk room (east, bottom): beds against its back wall (head and foot), a table
    (17, 11, "Bed001"), (17, 12, "Bed002"), (21, 11, "Bed001"), (21, 12, "Bed002"), (22, 11, "Bed001"),
    (22, 12, "Bed002"), (19, 15, "Table001"),
    # the vault (middle, top): its shelves of loot
    (10, 4, "Shelf_Goods001"), (15, 4, "Shelf_Goods001"), (11, 4, "Barrel001"),
]


def furnish(m):
    for x, y, d in FURNITURE:
        t, over = m.parts(x, y)
        over["Decor"] = d
        m.put(x, y, t, over)
    t, over = m.parts(6, Y1)
    m.put(6, Y1, "Fireplace001", over)                     # (the dining hall's hearth)
    for y in range(SPLIT_Y + 1, Y2):                       # (a carpet from the door to the vault)
        t, over = m.parts(DOOR, y)
        m.put(DOOR, y, "Carpet001", over)


def ent(kind, name, x, y, opts=""):
    dy = -8 if kind == "NPC" else 0
    return "%s\t%s\t%d\t%d%s" % (kind, name, (x - 1) * TW, (y - 1) * TW + dy, "\t" + opts if opts else "")


def people(m, pid):
    group = "Group=%s" % pid.upper()
    z = lambda x1, y1, x2, y2: "Zone=%d,%d,%d,%d" % (x1, y1, x2, y2)       # noqa: E731
    bad = "Attitude=Bad " + group
    out = [
        ent("NPC", "Bandit", DOOR - 2, Y2 + 2, "%s Stand=1 Face=S Look=1" % bad),                 # (at the door)
        ent("NPC", "Bandit", DOOR + 2, Y2 + 2, "%s Stand=1 Face=S Look=2" % bad),
        ent("NPC", "Bandit", 11, 14, "%s %s Look=3" % (bad, z(10, 12, 15, 16))),                # (the hall)
        ent("NPC", "Bandit", 14, 13, "%s %s" % (bad, z(10, 12, 15, 16))),
        ent("NPC", "Bandit", 5, 9, "%s %s Look=1" % (bad, z(4, 5, 8, 10))),                     # (dining)
        ent("NPC", "Bandit", 6, 13, "%s %s Look=2" % (bad, z(4, 12, 8, 16))),                   # (kitchen)
        ent("NPC", "Bandit", 19, 13, "%s %s Look=3" % (bad, z(17, 13, 22, 16))),                # (bunks)
        ent("NPC", "Bandit", 20, 6, "%s %s Name=%s_Chief" % (bad, z(17, 5, 22, 9), pid)),       # (the chief)
    ]
    chests = [
        ent("StaticObject", "Chest", 7, 11, "Id=%s_Pantry Lock=2" % pid),
        ent("StaticObject", "Chest", 18, 11, "Id=%s_Footlocker Lock=4" % pid),
        ent("StaticObject", "Chest", 22, 4, "Id=%s_Strongbox Lock=7 Sturdy=1" % pid),
        ent("StaticObject", "Chest", 13, 4, "Id=%s_Vault Lock=9 Sturdy=1" % pid),
        ent("StaticObject", "Odd_Barrel", 4, 12, "Id=%s_Stash" % pid),
    ]
    marks = ["Id\t%s\t%d\t%d" % (pid, DOOR, Y2 + 1),
             "Lock\t%d\t%d\t$Item.%s_Key>=1\tThe vault door is iron-bound and locked fast." % (DOOR, SPLIT_Y, pid),
             "Trigger\tTrap_Darts\t%d\t%d" % (DOOR, SPLIT_Y + 1),
             "Trigger\tTrap_Alarm\t%d\t%d" % (19, 10),
             "Trigger\tTrap_Pit\t%d\t%d" % (9, 14),
             "Trigger\tTrap_Gas\t%d\t%d" % (13, 6)]
    m.ents += out + chests + marks


def build(w, pid, near, ground):
    if w.find_id(pid)[0] is not None:
        return None
    mx, my = site(w, near)
    m = w.maps[(mx, my)]
    def in_yard(ln):
        c = W.line_cell(ln, mx, my)
        return c is not None and ln.split("\t")[0] in W.ENT_KINDS and \
            X1 - 3 <= c[0] - mx * XT + 1 <= X2 + 3 and Y1 - 3 <= c[1] - my * YT + 1 <= Y2 + 3
    m.ents = [ln for ln in m.ents if not in_yard(ln)]                  # (what grew or roamed there)
    house(m, ground)
    furnish(m)
    people(m, pid)
    w.changed.add(m.name)
    return mx, my


# ================================================================== Redrock Manor: a maze on three floors
MAZE = "Redrock_Manor"
# its rooms, four across and two deep on every floor, each floor's its own: the columns' (first, last) tiles, and the
# row each column's front room starts at (the owner's wish: not every room the same size and shape)
LAYOUT = {"G": ([(3, 6), (7, 12), (13, 17), (18, 22)], [10, 11, 10, 12]),
          "U": ([(3, 8), (9, 11), (12, 17), (18, 22)], [11, 9, 12, 10]),
          "C": ([(3, 7), (8, 13), (14, 16), (17, 22)], [11, 10, 9, 12])}
LAST = {"G": Y2 - 1, "U": Y2 - 2, "C": Y2 - 1}         # (each floor's last row inside: upstairs, the eaves' wall under it)
CODES = {frozenset("n"): "001", frozenset("e"): "002", frozenset("s"): "003", frozenset("w"): "004",
         frozenset("ne"): "005", frozenset("se"): "006", frozenset("sw"): "007", frozenset("nw"): "008"}
# the doorways between rooms on each floor (G ground, U upstairs, C cellar; (column, row) of a room, 0-based):
# east of a room: ("e", col, row); south of a back room into the front one: ("s", col)
GAPS = {"G": [("e", 0, 1), ("s", 1)],
        "U": [("s", 0), ("e", 2, 0), ("e", 2, 1), ("e", 0, 1)],
        "C": [("e", 0, 0), ("e", 1, 0), ("s", 3), ("s", 0), ("s", 2), ("s", 1)]}
# the ways up and down (the lower floor's, the upper's; where, the same on both): the only ways between most rooms.
# The way through: in at the front (G 1,1), west (G 0,1), up the stairs, north (U 0,0), down a hatch into a room shut
# off below (G 0,0), down again to the cellar, east along it (C 2,0), up into another shut room (G 2,0), up the stairs,
# east (U 3,0), down, down (C 3,0), south (C 3,1), up (G 3,1), up the stairs, west (U 2,1), and down into the vault
# (G 2,1), which has no door at all. The rest are dead ends: a pantry, a footlocker, traps.
LINKS = [("G", "U", (4, 13), "stairs"), ("G", "U", (6, 6), "ladder"), ("C", "G", (4, 8), "ladder"),
         ("C", "G", (14, 6), "ladder"), ("G", "U", (16, 8), "stairs"), ("G", "U", (19, 6), "ladder"),
         ("C", "G", (21, 8), "ladder"), ("C", "G", (19, 13), "ladder"), ("G", "U", (21, 15), "stairs"),
         ("G", "U", (14, 13), "ladder"), ("G", "U", (9, 6), "stairs")]
FLOORS = {"C": -1, "G": 0, "U": 1}
PEOPLE = {   # floor: [(kind, x, y, its room (col, row) or None: outside, other options)]
    "G": [("Bandit", DOOR - 2, Y2 + 2, None, "Stand=1 Face=S Look=1"),
          ("Bandit", DOOR + 2, Y2 + 2, None, "Stand=1 Face=S Look=2"),
          ("Bandit", 10, 14, (1, 1), ""), ("Bandit", 5, 15, (0, 1), "Look=3"), ("Bandit", 16, 5, (2, 0), ""),
          ("Bandit", 20, 12, (3, 1), "Look=1"), ("Bandit", 15, 15, (2, 1), "Name=%s_Chief" % MAZE)],
    "U": [("Bandit", 4, 5, (0, 0), "Look=2"), ("Bandit", 20, 8, (3, 0), ""), ("Bandit", 16, 14, (2, 1), "Look=3")],
    "C": [("Bandit", 10, 7, (1, 0), ""), ("Rat", 6, 14, (0, 1), ""), ("Rat", 15, 14, (2, 1), ""),
          ("Bandit", 21, 14, (3, 1), "Look=1")],
}
THINGS = {
    "G": [("Chest", 11, 4, "Id=%s_Pantry Lock=2" % MAZE), ("Chest", 16, 11, "Id=%s_Vault Lock=9 Sturdy=1" % MAZE),
          ("Chest", 13, 11, "Id=%s_Strongbox Lock=7 Sturdy=1" % MAZE)],
    "U": [("Chest", 11, 11, "Id=%s_Footlocker Lock=4" % MAZE)],
    "C": [("Odd_Barrel", 11, 15, "Id=%s_Stash" % MAZE)],
}
TRAPS = [("G", "Bucket", 5, 12), ("C", "Darts", 9, 7), ("U", "Gas", 17, 7), ("G", "Pit", 20, 14), ("U", "Alarm", 15, 13),
         ("C", "Weakness", 20, 12), ("U", "Pie", 10, 7)]
RUG = ["Woven_Rug%03d" % n for n in range(1, 10)]           # (a 3 x 3 rug: its corners, edges and middle)
FURNITURE = {   # floor: [(x, y, decor)]; a rug: ("rug", x, y) at its top left. Each room what it is.
    "G": [  # a storeroom; the kitchen; the guardroom; a scullery; the sitting room; the hall; the vault; the dining hall
          (3, 4, "Barrel001"), (4, 4, "Barrel002"), (3, 5, "Sacks001"), (3, 9, "Crate001"), (5, 9, "Crate002"),
          (7, 4, "Shelf_Goods001"), (8, 4, "Shelf_Goods001"), (12, 4, "Barrel001"), (11, 8, "Table001"),
          (10, 8, "Chair003"), (12, 10, "Sacks001"), (7, 10, "Herb_Rack001"),
          (13, 4, "Banner001"), (17, 4, "Crate001"), (17, 5, "Crate002"), (13, 9, "Bench001"), (14, 9, "Bench002"),
          (15, 9, "Bench003"),
          (18, 4, "Fish_Barrel001"), (22, 4, "Barrel002"), (22, 11, "Sacks001"), (18, 11, "Crate001"),
          (3, 10, "Bookshelf001"), (6, 16, "Potted_Plant002"), (3, 16, "Chair001"), (6, 10, "Candles001"),
          (7, 11, "Potted_Plant001"), (12, 11, "Potted_Plant003"), (7, 16, "Bench001"), (8, 16, "Bench002"),
          (9, 16, "Bench003"), ("rug", 9, 12),
          (17, 10, "Potion_Shelf001"), (13, 10, "Shelf_Goods001"), (17, 16, "Coin_Chest001"), (13, 16, "Candles001"),
          (21, 13, "Dining_Table001"), (22, 13, "Dining_Table002"), (21, 12, "Chair001"), (22, 12, "Chair001"),
          (22, 14, "Chair002"), (18, 12, "Banner001"), (18, 16, "Potted_Plant004")],
    "U": [  # a bedroom; the linen closet; the library; the study; a bedroom; the bunk room; the master's; the gallery
          (3, 4, "Bed001"), (3, 5, "Bed002"), (8, 4, "Bookshelf001"), (8, 10, "Potted_Plant004"), ("rug", 4, 7),
          (10, 4, "Shelf_Goods001"), (11, 4, "Shelf_Goods001"),
          (12, 4, "Bookshelf001"), (13, 4, "Bookshelf001"), (14, 4, "Bookshelf001"), (15, 4, "Bookshelf001"),
          (13, 8, "Desk001"), (13, 9, "Chair002"), (12, 11, "Candles001"),
          (21, 5, "Desk001"), (21, 6, "Chair002"), (22, 4, "Bookshelf001"), (18, 4, "Potion_Shelf001"),
          (8, 11, "Bed001"), (8, 12, "Bed002"), (3, 11, "Shelf_Goods001"), (6, 15, "Chair003"),
          (9, 9, "Bed001"), (9, 10, "Bed002"), (10, 13, "Bed001"), (10, 14, "Bed002"), (11, 15, "Barrel001"),
          (12, 12, "Double_Bed001"), (13, 12, "Double_Bed002"), (12, 13, "Double_Bed003"),
          (13, 13, "Double_Bed004"), (17, 15, "Potted_Plant005"),
          (18, 10, "Statue002"), (22, 10, "Banner001"), (18, 15, "Potted_Plant001"), (19, 12, "Bench001"),
          (20, 12, "Bench002"), (21, 12, "Bench003")],
    "C": [  # the wine cellar; a storeroom; the root cellar; the cold store; a workshop; the old cells; a narrow store;
            # the servants' room
          (3, 4, "Cellar_Barrel001"), (5, 4, "Cellar_Barrel001"), (7, 4, "Cellar_Barrel001"), (3, 6, "Barrel002"),
          (8, 4, "Cellar_Crate001"), (13, 4, "Cellar_Crate001"), (13, 5, "Cellar_Crate001"), (8, 9, "Sacks001"),
          (16, 4, "Sacks001"), (16, 8, "Barrel001"),
          (17, 4, "Fish_Barrel001"), (22, 4, "Cellar_Crate001"), (22, 5, "Barrel001"),
          (3, 11, "Table001"), (4, 11, "Chair003"), (7, 16, "Crate002"),
          (8, 10, "Cellar_Barrel001"), (13, 10, "Candles001"),
          (14, 16, "Crate001"), (16, 9, "Sacks001"),
          (22, 12, "Bed001"), (22, 13, "Bed002"), (17, 16, "Table001"), (18, 16, "Chair004")],
}


def room_box(floor, col, row):
    """(x1, y1, x2, y2) of the room at (col, row) on a floor."""
    cols, splits = LAYOUT[floor]
    a, b = cols[col]
    return (a, Y1, b, splits[col] - 1) if row == 0 else (a, splits[col], b, LAST[floor])


def room_of(floor, x, y):
    for col in range(4):
        for row in (0, 1):
            x1, y1, x2, y2 = room_box(floor, col, row)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return col, row
    return None


def door_y(floor, col, row):
    """The row of the doorway east of room (col, row): the middle of where it and the room east of it overlap."""
    a, b = room_box(floor, col, row), room_box(floor, col + 1, row)
    return (max(a[1], b[1]) + min(a[3], b[3])) // 2


def door_x(floor, col):
    a, _, b, _ = room_box(floor, col, 0)
    return (a + b) // 2


def maze_edges(floor, x, y, last):
    """The thin walls' edges of cell x, y on a floor (last: its last row inside)."""
    e = set()
    if y == Y1:
        e.add("n")
    if x == X1:
        e.add("w")
    if x == X2:
        e.add("e")
    if floor == "C" and y == last:
        e.add("s")
    gaps = GAPS[floor]
    col, row = room_of(floor, x, y)
    cols, splits = LAYOUT[floor]
    if y == splits[col] and not (("s", col) in gaps and x == door_x(floor, col)):
        e.add("n")
    if col < 3 and x == cols[col][1] and not (("e", col, row) in gaps and y == door_y(floor, col, row)):
        e.add("e")
    return e


def maze_floor(m, floor, floor_tile, last):
    for y in range(Y1, last + 1):
        for x in range(X1, X2 + 1):
            t, over = m.parts(x, y)
            over.pop("Decor", None)
            over.pop("Under", None)
            e = maze_edges(floor, x, y, last)
            m.put(x, y, THIN + CODES[frozenset(e)] if e else floor_tile, over)


def kept_clear(floor):
    """Where nothing may stand: the ways up and down, the chests, the traps, where people start, the doorways."""
    out = set()
    for lower, upper, (x, y), _ in LINKS:
        if floor in (lower, upper):
            out.add((x, y))
    out |= {(x, y) for _, x, y, _ in THINGS.get(floor, [])}
    out |= {(x, y) for f, _, x, y in TRAPS if f == floor}
    out |= {(x, y) for _, x, y, _, _ in PEOPLE[floor]}
    for g in GAPS[floor]:
        if g[0] == "e":
            y = door_y(floor, g[1], g[2])
            b = LAYOUT[floor][0][g[1]][1]
            out |= {(b, y), (b + 1, y)}
        else:
            x = door_x(floor, g[1])
            s = LAYOUT[floor][1][g[1]]
            out |= {(x, s), (x, s - 1)}
    return out


def furnish(m, floor):
    """Each room's furniture (FURNITURE), checked: in a room, and clear of what must be kept clear."""
    clear = kept_clear(floor)
    for f in FURNITURE[floor]:
        rug = f[0] == "rug"                           # (a rug's decor too, walked over: anyone may start on it)
        cells = [(f[1] + i, f[2] + j, RUG[j * 3 + i]) for j in range(3) for i in range(3)] if rug else [f]
        for x, y, name in cells:
            assert room_of(floor, x, y) is not None, (floor, x, y, name)
            assert rug or (x, y) not in clear, ("in the way", floor, x, y, name)
            t, over = m.parts(x, y)
            over["Decor"] = name
            m.put(x, y, t, over)


def lay_out(maps):
    """Every floor's rooms, its ways up and down, its furniture (maps: {"G": ..., "U": ..., "C": ...})."""
    maze_floor(maps["G"], "G", "Plank001", LAST["G"])
    maze_floor(maps["U"], "U", "Plank001", LAST["U"])
    maze_floor(maps["C"], "C", "Flagstone001", LAST["C"])
    for lower, upper, (x, y), kind in LINKS:
        if kind == "stairs":
            t, over = maps[lower].parts(x, y)
            maps[lower].put(x, y, "Stairs001", over)
            t, over = maps[upper].parts(x, y)
            maps[upper].put(x, y, "Stairs002", over)
        else:
            maps[lower].set(x, y, decor="Ladder001")
            maps[upper].set(x, y, decor="Hatch001")
    for floor, m in maps.items():
        furnish(m, floor)


def people(maps, inside):
    """The bandits and rats, each roaming its own room (what was there before taken off first)."""
    bad = "Attitude=Bad Group=%s" % MAZE.upper()
    for floor, m in maps.items():
        m.ents = [ln for ln in m.ents if not (ln.split("\t")[0] == "NPC" and ln.split("\t")[1] in ("Bandit", "Rat")
                                              and inside(ln))]
        for kind, x, y, at, opts in PEOPLE[floor]:
            zone = "" if at is None else "Zone=%d,%d,%d,%d" % room_box(floor, *at)
            words = " ".join(w for w in ((bad if kind == "Bandit" else "Attitude=Bad"), zone, opts) if w)
            m.ents.append(ent("NPC", kind, x, y, words))


def maze(w, pid, again=False):
    """Its three floors laid out (again=True: over the floors there are now, the rooms and their people and furniture
    drawn afresh; the chests, traps and stash where they were)."""
    m, c = w.find_id(pid)
    mx, my, _ = W.mxyz(m.name)
    up_name, down_name = W.mname(mx, my, 1), W.mname(mx, my, -1)
    there = SK.map_exists(up_name) or SK.map_exists(down_name)
    if there and not again:
        return False
    if there:
        up, down = Map(up_name), Map(down_name)
    else:
        up, down = SK.black_map(up_name), SK.black_map(down_name)
        for x in range(X1, X2 + 1):                         # (upstairs: its front under the eaves, windows in it)
            up.put(x, Y2 - 1, WALL, {"Decor": "Stone_Wall_Window001"} if x % 3 == 0 and X1 < x < X2 else {})
    maps = {"G": m, "U": up, "C": down}
    lay_out(maps)

    def inside(ln):
        q = W.line_cell(ln, 0, 0)
        return q is not None and X1 - 3 <= q[0] + 1 <= X2 + 3 and Y1 <= q[1] + 1 <= Y2 + 3
    if not there:
        m.ents = [ln for ln in m.ents if not (inside(ln) and W.line_id(ln) != pid)]
        for floor, objs in THINGS.items():
            for kind, x, y, opts in objs:
                maps[floor].ents.append(ent("StaticObject", kind, x, y, opts))
        for floor, kind, x, y in TRAPS:
            maps[floor].ents.append("Trigger\tTrap_%s\t%d\t%d" % (kind, x, y))
    people(maps, inside)
    up.save()
    down.save()
    w.changed.add(m.name)
    amb = os.path.join(ROOT, "data", "Ambient.ini")
    s = W.read(amb)
    for name in (up_name, down_name):
        if "\r\n%s=" % name not in s:
            s = s.replace("[Maps]\r\n", "[Maps]\r\n%s=Indoors\r\n" % name, 1)
    W.write(amb, s)
    return True


# ================================================================== the abbey
def abbey(w):
    m, c = w.find_id("Fenwick_Cathedral")
    if m is None:
        return False
    mx, my, _ = W.mxyz(m.name)
    m.ents = [ln if W.line_id(ln) != "Fenwick_Cathedral" else ln.replace("Fenwick_Cathedral", "Drowned_Abbey")
              for ln in m.ents]
    inside = [(x, y) for x in range(1, XT + 1) for y in range(1, YT + 1)
              if m.roofed(x, y) and m.tile(x, y) in ("Tile001", "Plank001", "Marble001") and not m.decor(x, y).startswith(
                  ("Altar", "Bench"))]
    inside.sort(key=lambda t: (t[1], t[0]))
    if len(inside) < 6:
        print("  !! the abbey's floor: too little room")
        return True
    xs, ys = [t[0] for t in inside], [t[1] for t in inside]
    zone = "Zone=%d,%d,%d,%d" % (min(xs), min(ys), max(xs), max(ys))
    picks = inside[::max(1, len(inside) // 5)][:4]
    for i, (x, y) in enumerate(picks):
        m.ents.append(ent("NPC", "Skeleton" if i % 2 == 0 else "Skeleton_Archer", x, y, "Attitude=Bad " + zone))
    top = min(inside, key=lambda t: (t[1], abs(t[0] - sum(xs) // len(xs))))
    m.ents.append(ent("StaticObject", "Chest", top[0], top[1], "Id=Drowned_Abbey_Reliquary Lock=5"))
    mid = inside[len(inside) // 2]
    m.ents.append("Trigger\tTrap_Weakness\t%d\t%d" % mid)
    w.changed.add(m.name)
    return True


# ================================================================== the keys, the scripts, the names
def key_art(pid, rgb):
    """The key's picture: Lair_Key's, its metal tinted (its dark outline kept)."""
    out = SK.load("Entities", "Lair_Key").copy()
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))
            if a and not (r < 50 and g < 50 and b < 50):
                k = (r + g + b) / (3 * 255.0)
                out.set_at((x, y), tuple(min(255, int(v * (0.5 + k))) for v in rgb) + (a,))
    SK.save("Entities", pid + "_Key", out)


def key_data(pid, name):
    SK.set_section(ENTITIES, pid + "_Key", [
        "Type=MapItem", "Use.Words=Examine",
        "Examine.Info=A heavy iron key, worn bright where a thumb has turned it. It came from %s." % name,
        "Stackable=1", "Droppable=0", "Value=0"])


def gone_key(pid):
    """(the maze needs no key: its way through is the lock)"""
    path = os.path.join(ROOT, "sprites", "Entities", pid + "_Key.png")
    if os.path.exists(path):
        os.remove(path)
    s = W.read(ENTITIES)
    a = s.find("[%s_Key]\r\n" % pid)
    if a >= 0:
        b = s.find("\r\n[", a + 1)
        W.write(ENTITIES, s[:a] + (s[b + 2:] if b >= 0 else ""))


def chest_script(pid, attr, items, more=None):
    """more: (attribute, items) found there once too, by its own attribute (put in after the chest was first opened:
    whoever emptied it before still finds them)."""
    give_more = [("Update.Attribute", more[0], "=1")] + [("Give.Item", item, str(n)) for item, n in more[1]]         if more else []
    rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
            (">Conditional", "$Attr.%s=0" % attr, "@more" if more else "@empty"),
            ("Update.Attribute", attr, "=1"),
            ("Play.Sound", "Chest")]
    rows += [("Give.Item", item, str(n)) for item, n in items] + give_more
    rows += [("End",)]
    if more:
        rows += [("@more",), (">Conditional", "$Attr.%s=0" % more[0], "@empty"), ("Play.Sound", "Chest")] + give_more +             [("End",)]
    rows += [("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",),
             ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    SK.write_script("Open %s" % pid, rows, MAKER)


def scripts(pid, prize):
    chest_script(pid + "_Pantry", pid + "Pantry", [("Bread", 2), ("Cooked_Meat", 2), ("Ale", 1),
                                                   ("Gold_Coin(s)", 15)])
    chest_script(pid + "_Footlocker", pid + "Footlocker", [("Gold_Coin(s)", 40), ("Healing_Draught", 2),
                                                           ("Leather_Cap", 1)])
    chest_script(pid + "_Strongbox", pid + "Strongbox", [(pid + "_Key", 1), ("Gold_Coin(s)", 30)] if pid != MAZE else
                 [("Gold_Coin(s)", 70), ("Super_Potion", 1)])
    chest_script(pid + "_Vault", pid + "Vault", prize,      # (the maze's: the signet and the old lord's scroll too,
                 (pid + "Signet", [("Redrock_Signet", 1), ("Dread_Scroll", 1)]) if pid == MAZE else None)   # hush_and_dread)
    SK.write_script("Search %s_Stash" % pid, [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.%sStash=0" % pid, "@empty"),
        ("Update.Attribute", "%sStash" % pid, "=1"),
        ("Play.Sound", "Pickup"),
        ("Display.Message", "Yellow", "The barrel's false bottom lifts out: somebody's share of the takings, kept from "
                                      "the others.", "-"),
        ("Give.Item", "Gold_Coin(s)", "35"),
        ("Give.Item", "Shard", "6"),
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "You've found what was here already.", "-"), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def abbey_scripts():
    chest_script("Drowned_Abbey_Reliquary", "AbbeyReliquary", [("Gold_Coin(s)", 60), ("Silver_Ring", 1),
                                                                ("Healing_Draught", 2), ("Ward_Shard", 1),
                                                                ("Shard", 12)])


def roads(w, spots):
    """A way from each manor's door (and the abbey's) to the roads near."""
    for gx, gy in spots:
        net = {(x, y) for x in range(gx - 70, gx + 71) for y in range(gy - 70, gy + 71)
               if w.cell(x, y) is not None and W.is_road(w.cell(x, y)) and abs(x - gx) + abs(y - gy) > 6}
        if net:
            W.join_roads(w, [(gx, gy)], network=net)


def main():
    w = W.World(0)
    doors = []
    for pid, (near, ground, prize, rgb, name) in MANORS.items():
        at = build(w, pid, near, ground)
        if at is not None:
            print("%s: built on %d,%d,0" % (name, at[0], at[1]))
            doors.append((at[0] * XT + DOOR - 1, at[1] * YT + Y2 + 1))
        if pid == MAZE:
            if maze(w, pid):
                print("%s: a maze on three floors" % name)
            gone_key(pid)
        else:
            key_art(pid, rgb)
            key_data(pid, name)
        scripts(pid, prize)
        SK.place_label("Places", name, pid)
    if abbey(w):
        print("The Drowned Abbey: its dead and its reliquary")
        m, c = w.find_id("Drowned_Abbey")
        doors.append((c[0], c[1] + 1))
    abbey_scripts()
    SK.place_label("Places", "The Drowned Abbey", "Drowned_Abbey")
    roads(w, doors)
    print("%d maps changed" % w.save())


if __name__ == "__main__":
    main()
