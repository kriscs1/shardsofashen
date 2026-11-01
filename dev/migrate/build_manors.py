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
COLS = [(3, 7), (8, 12), (13, 17), (18, 22)]            # (its rooms: four across, two deep, on every floor)
SPLIT = 11                                              # (the back rooms over this row, the front rooms from it)
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
    if y == SPLIT:
        col = next(i for i, (a, b) in enumerate(COLS) if a <= x <= b)
        if not (("s", col) in gaps and x == (COLS[col][0] + COLS[col][1]) // 2):
            e.add("n")
    for i, (a, b) in enumerate(COLS[:-1]):
        if x == b:
            row = 0 if y < SPLIT else 1
            mid = 7 if row == 0 else 13
            if not (("e", i, row) in gaps and y == mid):
                e.add("e")
    return e


def maze_floor(m, floor, floor_tile, last):
    for y in range(Y1, last + 1):
        for x in range(X1, X2 + 1):
            t, over = m.parts(x, y)
            over.pop("Decor", None)
            e = maze_edges(floor, x, y, last)
            m.put(x, y, THIN + CODES[frozenset(e)] if e else floor_tile, over)


def maze(w, pid):
    m, c = w.find_id(pid)
    mx, my, _ = W.mxyz(m.name)
    up_name, down_name = W.mname(mx, my, 1), W.mname(mx, my, -1)
    if SK.map_exists(up_name) or SK.map_exists(down_name):
        return False
    up, down = SK.black_map(up_name), SK.black_map(down_name)
    maze_floor(m, "G", "Plank001", Y2 - 1)
    for x in range(X1, X2 + 1):                             # (upstairs: its front under the eaves, windows in it)
        up.put(x, Y2 - 1, WALL, {"Decor": "Stone_Wall_Window001"} if x % 3 == 0 and X1 < x < X2 else {})
    maze_floor(up, "U", "Plank001", Y2 - 2)
    maze_floor(down, "C", "Flagstone001", Y2 - 1)
    maps = {"G": m, "U": up, "C": down}
    for lower, upper, (x, y), kind in LINKS:
        if kind == "stairs":
            t, over = maps[lower].parts(x, y)
            maps[lower].put(x, y, "Stairs001", over)
            t, over = maps[upper].parts(x, y)
            maps[upper].put(x, y, "Stairs002", over)
        else:
            maps[lower].set(x, y, decor="Ladder001")
            maps[upper].set(x, y, decor="Hatch001")
    # (what was in the house, out; what's in the maze, in)
    def inside(ln):
        q = W.line_cell(ln, mx, my)
        return q is not None and X1 - 3 <= q[0] - mx * XT + 1 <= X2 + 3 and Y1 <= q[1] - my * YT + 1 <= Y2 + 3 \
            and W.line_id(ln) != pid
    m.ents = [ln for ln in m.ents if not inside(ln)]
    bad = "Attitude=Bad Group=%s" % pid.upper()
    room = lambda floor, col, row: "Zone=%d,%d,%d,%d" % (          # noqa: E731
        COLS[col][0], Y1 if row == 0 else SPLIT, COLS[col][1],
        SPLIT - 1 if row == 0 else (Y2 - 2 if floor == "U" else Y2 - 1))
    people = {
        "G": [("Bandit", DOOR - 2, Y2 + 2, "Stand=1 Face=S Look=1"), ("Bandit", DOOR + 2, Y2 + 2, "Stand=1 Face=S Look=2"),
              ("Bandit", 10, 14, room("G", 1, 1)), ("Bandit", 5, 15, room("G", 0, 1) + " Look=3"),
              ("Bandit", 16, 5, room("G", 2, 0)), ("Bandit", 20, 12, room("G", 3, 1) + " Look=1"),
              ("Bandit", 15, 15, room("G", 2, 1) + " Name=%s_Chief" % pid)],
        "U": [("Bandit", 4, 5, room("U", 0, 0) + " Look=2"), ("Bandit", 20, 8, room("U", 3, 0)),
              ("Bandit", 16, 14, room("U", 2, 1) + " Look=3")],
        "C": [("Bandit", 10, 7, room("C", 1, 0)), ("Rat", 6, 14, room("C", 0, 1)), ("Rat", 15, 14, room("C", 2, 1)),
              ("Bandit", 21, 14, room("C", 3, 1) + " Look=1")],
    }
    for floor, folk in people.items():
        for kind, x, y, opts in folk:
            maps[floor].ents.append(ent("NPC", kind, x, y, "%s %s" % (bad if kind == "Bandit" else "Attitude=Bad",
                                                                      opts)))
    things = {
        "G": [("Chest", 11, 4, "Id=%s_Pantry Lock=2" % pid), ("Chest", 16, 11, "Id=%s_Vault Lock=9 Sturdy=1" % pid),
              ("Chest", 13, 11, "Id=%s_Strongbox Lock=7 Sturdy=1" % pid)],
        "U": [("Chest", 11, 11, "Id=%s_Footlocker Lock=4" % pid)],
        "C": [("Odd_Barrel", 11, 15, "Id=%s_Stash" % pid)],
    }
    for floor, objs in things.items():
        for kind, x, y, opts in objs:
            maps[floor].ents.append(ent("StaticObject", kind, x, y, opts))
    for floor, kind, x, y in (("G", "Bucket", 5, 12), ("C", "Darts", 9, 7), ("U", "Gas", 17, 7), ("G", "Pit", 20, 14),
                              ("U", "Alarm", 15, 13), ("C", "Weakness", 20, 12), ("U", "Pie", 10, 7)):
        maps[floor].ents.append("Trigger\tTrap_%s\t%d\t%d" % (kind, x, y))
    for x, y, d in ((X1, Y1, "Barrel001"), (X2, Y1, "Bookshelf001"), (17, SPLIT, "Bed001"), (17, SPLIT + 1, "Bed002"),
                    (X1, SPLIT, "Shelf_Goods001")):
        if not up.decor(x, y) and up.tile(x, y) not in ("Stairs002",):
            up.set(x, y, decor=d)
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


def chest_script(pid, attr, items):
    rows = [(">Distance.From.Clicked.Entity", "48", "@far"),
            (">Conditional", "$Attr.%s=0" % attr, "@empty"),
            ("Update.Attribute", attr, "=1"),
            ("Play.Sound", "Chest")]
    rows += [("Give.Item", item, str(n)) for item, n in items]
    rows += [("End",),
             ("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",),
             ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
    SK.write_script("Open %s" % pid, rows, MAKER)


def scripts(pid, prize):
    chest_script(pid + "_Pantry", pid + "Pantry", [("Bread", 2), ("Cooked_Meat", 2), ("Ale", 1),
                                                   ("Gold_Coin(s)", 15)])
    chest_script(pid + "_Footlocker", pid + "Footlocker", [("Gold_Coin(s)", 40), ("Healing_Draught", 2),
                                                           ("Leather_Cap", 1)])
    chest_script(pid + "_Strongbox", pid + "Strongbox", [(pid + "_Key", 1), ("Gold_Coin(s)", 30)] if pid != MAZE else
                 [("Gold_Coin(s)", 70), ("Super_Potion", 1)])
    chest_script(pid + "_Vault", pid + "Vault", prize)
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
