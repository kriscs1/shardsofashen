"""The Eastreach: 16 generated maps (6,5,0 to 9,8,0) east of the Wildlands, over the old bridge from the Wolf Den on
Greymoor. Two lands, two towns, two quests.

Not run on its own: build_content.extend() calls extend() here after build_regions (whose helpers it borrows) and before
build_travel (so its towns get waystones) and the scenery pass (so its maps get scenery and wildlife), so
`python -I "Dev\\migrate\\build_world.py"` builds it. Deterministic: the same maps every time.

  * THE ELDERWOOD (map rows 5-6): ancient forest (the Forest001 canopy), oaks, yews, mushrooms and herbs. Bears, wolves and
    spiders. THORNWICK, a woodland village, and the HEARTWOOD, the wood's old heart stone (north-east).
  * THE BARROWDOWNS (map rows 7-8): open downs of standing stones, graves and ruins; coal and gem rocks. Skeletons and
    bats. RAVENSGATE, a town of gravekeepers, and the BARROW of the old king (east).
  * The sea all round; THE OLD BRIDGE, planks across the strait from the Wolf Den (5,6,0) to the Elderwood's west shore.
  * Quests: The Withering Wood (the Druid of Thornwick) and The Barrow King (the Gravekeeper of Ravensgate).
  * New people and a new foe: the Druid, the Gravekeeper and the Barrow King, recoloured from the Witch, the Elder and the
    Skeleton (Sprites\\Entities and their walking frames in Sprites\\Walk: make_art()).
"""
import math
import os
import sys

W = C = R = None        # build_world, build_content, build_regions

MX0, MX1, MY0, MY1 = 6, 9, 5, 8
GW, GH = 25, 21
GX0, GX1, GY0, GY1 = MX0 * GW, (MX1 + 1) * GW - 1, MY0 * GH, (MY1 + 1) * GH - 1

# Towns: name -> (map x, map y, quest giver, Trader's rack, notice text)
TOWNS = {
    "Thornwick": (7, 6, "Druid", "SHOP-Thornwick",
                  "THORNWICK\\A village of woodsfolk in the Elderwood.\\West: the old bridge to Greymoor. South: Ravensgate."),
    "Ravensgate": (8, 8, "Gravekeeper", "SHOP-Ravensgate",
                   "RAVENSGATE\\The gravekeepers' town on the Barrowdowns.\\North: Thornwick. East: the old king's barrow."),
}
TOWN_TILE = {"Thornwick": (11, 13), "Ravensgate": (16, 7)}     # off the middle of their maps (no grid)
VILLAGES = {}               # town -> villages.build()'s layout (its houses and streets), made by build_grid
WOLF_DEN_BRIDGE_Y = None            # the world row the bridge runs along (set from the Wolf Den by extend)
SITES = {
    "Heartwood": (8 * GW + 14, 5 * GH + 12),            # the heart of the Elderwood (8,5,0)
    "Barrow": (9 * GW + 8, 7 * GH + 13),                # the old king's barrow (9,7,0)
}
ROADS = [("Bridge", "Thornwick"), ("Thornwick", "Ravensgate")]
LAND = {"Grass001", "Sand001", "Dirt001", "Plank001", "Tall_Grass001"}


def h01(*parts):
    return R.h01("east", *parts)


def fbm(x, y, scale, seed):
    return R.fbm(x, y, scale, 500 + seed)


def town_centre(name):
    mx, my = TOWNS[name][0], TOWNS[name][1]
    tx, ty = TOWN_TILE[name]
    return mx * GW + tx - 1, my * GH + ty - 1


def land_of(gx, gy):
    wy = gy + 18 * (fbm(gx, gy, 20, 1) - 0.5)
    return "elder" if wy < GY0 + 2 * GH else "downs"


def coast(gx, gy):
    """Tiles from the sea round the Eastreach (under 2.2 sea, under 4.2 beach): the block's edge with rounded corners,
    pushed in and out by noise; towns, sites and the bridge's landing kept on land."""
    sides = [gx - GX0, GX1 - gx, gy - GY0, GY1 - gy]
    d = min(sides)
    rr = 36.0
    for a, b in ((gx - GX0, gy - GY0), (GX1 - gx, gy - GY0), (gx - GX0, GY1 - gy), (GX1 - gx, GY1 - gy)):
        if a < rr and b < rr:
            d = min(d, rr - math.hypot(rr - a, rr - b))
    d += 34 * (fbm(gx, gy, 20, 3) - 0.5) + 8 * (fbm(gx, gy, 7, 4) - 0.5) - 4
    if min(sides) < 1:
        return 0
    for t in TOWNS:
        cx, cy = town_centre(t)
        d = max(d, 7 - 0.7 * max(0.0, math.hypot((gx - cx) / 1.2, gy - cy) - 11))
    for sx, sy in SITES.values():
        d = max(d, 6 - 0.7 * max(0.0, math.hypot(gx - sx, gy - sy) - 5))
    return d


def base_tile(gx, gy):
    c = coast(gx, gy)
    if c < 2.2:
        return "Water001"
    if c < 4.2:
        return "Sand001"
    r = h01("cell", gx, gy)
    if land_of(gx, gy) == "elder":
        n = fbm(gx, gy, 9, 5)
        if n > 0.58:
            return "Forest001"
        if n > 0.44:
            if r < 0.22:
                return "Oak_Tree001"
            if r < 0.30:
                return "Yew_Tree001"
            if r < 0.48:
                return "Tree001"
            if r < 0.60:
                return "Tree002"
        if r < 0.008:
            return "Mushroom_Patch001"
        if r < 0.014:
            return "Herb_Patch001"
        if r < 0.019:
            return "Fallen_Log001"
        if r < 0.05:
            return "Tall_Grass001"
        return "Grass001"
    # the downs
    if fbm(gx, gy, 7, 6) > 0.74 and r < 0.55:
        return "Rock001"
    if fbm(gx, gy, 10, 7) > 0.78:
        return "Water001" if fbm(gx, gy, 4, 8) > 0.5 else "Grass001"
    if fbm(gx, gy, 8, 9) > 0.72 and r < 0.22:
        return ("Grave001", "Grave002", "Grave003")[int(r * 300) % 3]
    if r < 0.010:
        return "Stone001"
    if r < 0.016:
        return "Stone002"
    if r < 0.019:
        return "Standing_Stone001"
    if r < 0.022:
        return "Coal_Rock001"
    if r < 0.024:
        return "Gem_Rock001"
    if r < 0.040:
        return "Tree002"
    if fbm(gx, gy, 9, 10) > 0.68:
        return "Dirt001"
    return "Grass001"


def line(a, b, wobble, seed):
    """A winding 4-connected line of world tiles from a to b (as build_regions makes roads)."""
    (ax, ay), (bx, by) = a, b
    n = max(abs(bx - ax), abs(by - ay), 1)
    px, py = -(by - ay) / float(n), (bx - ax) / float(n)
    ln = math.hypot(px, py) or 1
    px, py = px / ln, py / ln
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        off = wobble * (fbm(i, 0, 9, seed) - 0.5) * 2 * math.sin(math.pi * t)
        pts.append((int(round(ax + (bx - ax) * t + px * off)), int(round(ay + (by - ay) * t + py * off))))
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        x, y = x0, y0
        while (x, y) != (x1, y1):
            out.append((x, y))
            if x != x1:
                x += 1 if x1 > x else -1
                out.append((x, y))
            if y != y1:
                y += 1 if y1 > y else -1
        out.append((x1, y1))
    return out


def build_grid():
    grid = {}
    for gy in range(GY0, GY1 + 1):
        for gx in range(GX0, GX1 + 1):
            grid[(gx, gy)] = base_tile(gx, gy)
    R.smooth_coast(grid)
    busy = set()
    roofs = {}
    import villages
    for k, name in enumerate(TOWNS):                    # villages.py lays each one out
        cx, cy = town_centre(name)
        v = villages.build(grid, busy, cx, cy, 800 + k, land_of(cx, cy), "Grass001",
                           lambda gx, gy: coast(gx, gy) < 4.2, GW, GH, {"Grass001", "Tall_Grass001", "Weed001"},
                           keep_out={(sx + dx, sy + dy) for sx, sy in SITES.values() for dx in range(-4, 5)
                                     for dy in range(-4, 5)})
        VILLAGES[name] = v
        groups = {}
        for x1, y1, x2, y2, material in v["roofs"]:
            m = (x1 // GW, y1 // GH)
            groups[m] = groups.get(m, 0) + 1
            roofs.setdefault(name, []).append((x1, y1, x2, y2, groups[m], material))
    for name, (sx, sy) in SITES.items():
        for gy in range(sy - 3, sy + 4):
            for gx in range(sx - 3, sx + 4):
                if (gx, gy) in grid:
                    grid[(gx, gy)] = "Grass001"
                busy.add((gx, gy))

    # the old bridge: straight planks east from the strait to the first dry land, where the road begins
    x = GX0
    while x < GX1 and not (grid[(x, WOLF_DEN_BRIDGE_Y)] in LAND and grid[(x + 1, WOLF_DEN_BRIDGE_Y)] in LAND):
        if grid[(x, WOLF_DEN_BRIDGE_Y)] not in LAND:
            grid[(x, WOLF_DEN_BRIDGE_Y)] = "Plank001"
        busy.add((x, WOLF_DEN_BRIDGE_Y))
        x += 1
    landing = (x, WOLF_DEN_BRIDGE_Y)

    def gate(name, toward):
        if name == "Bridge":
            return landing
        cx, cy = town_centre(name)
        tx, ty = toward
        if abs(tx - cx) > abs(ty - cy):
            return (cx + (11 if tx > cx else -11), cy)
        return (cx, cy + (9 if ty > cy else -9))

    def lay(cells):
        for (x, y) in cells:
            t = grid.get((x, y))
            if t is None or t in villages.HOUSE_TILES:
                continue
            grid[(x, y)] = "Plank001" if t.startswith("Water") or t.startswith("Sand_Water") else "Dirt001"
            for ex, ey in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                v = grid.get((ex, ey))
                if v not in villages.HOUSE_TILES | {None, "Dirt001"} and not v.startswith("Water") \
                        and v not in LAND:
                    grid[(ex, ey)] = "Grass001"
            busy.add((x, y))

    centre = {n: town_centre(n) for n in TOWNS}
    centre["Bridge"] = landing
    for k, (a, b) in enumerate(ROADS):
        lay(line(gate(a, centre[b]), gate(b, centre[a]), 5 if a != "Bridge" else 3, 600 + k))
    for k, (name, (sx, sy)) in enumerate(sorted(SITES.items())):
        best = min((p for p, t in grid.items() if t == "Dirt001" and abs(p[0] - sx) + abs(p[1] - sy) > 8),
                   key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))
        lay(line((sx, sy + 3), best, 2, 700 + k))
    R.smooth_shores(grid)
    return grid, roofs, busy


def local(gx, gy):
    mx, my = gx // GW, gy // GH
    return "%d,%d,0" % (mx, my), gx - mx * GW + 1, gy - my * GH + 1


def make_maps(grid, roofs):
    rev = R.legend_chars(set(grid.values()))
    maps = {}
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            rows = ["".join(rev[grid[(mx * GW + x, my * GH + y)]] for x in range(GW)) for y in range(GH)]
            mroofs = []
            for town, rs in roofs.items():
                for r in rs:
                    if mx * GW <= r[0] < (mx + 1) * GW and my * GH <= r[1] < (my + 1) * GH:
                        mroofs.append((r[0] - mx * GW + 1, r[1] - my * GH + 1, r[2] - mx * GW + 1, r[3] - my * GH + 1)
                                      + tuple(r[4:]))
            maps["%d,%d,0" % (mx, my)] = dict(rows=rows, roofs=mroofs, entities=[], triggers=[])
    return maps


def set_tile(maps, grid, gx, gy, tile):
    grid[(gx, gy)] = tile
    m, x, y = local(gx, gy)
    row = maps[m]["rows"][y - 1]
    maps[m]["rows"][y - 1] = row[:x - 1] + R.legend_chars({tile})[tile] + row[x:]


def reachable(grid):
    ok = LAND | {"Door001"}
    todo, seen = [(GX0 + 1, WOLF_DEN_BRIDGE_Y)], set()
    while todo:
        c = todo.pop()
        if c in seen or grid.get(c) not in ok:
            continue
        seen.add(c)
        x, y = c
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def spots(grid, busy, reach, mx, my, n, seed, avoid=()):
    cells = []
    for y in range(2, GH):
        for x in range(2, GW):
            gx, gy = mx * GW + x - 1, my * GH + y - 1
            t = grid[(gx, gy)]
            if t not in ("Grass001", "Sand001", "Tall_Grass001") or (gx, gy) in busy or (gx, gy) not in reach:
                continue
            if any(abs(gx - ax) + abs(gy - ay) < 4 for ax, ay in avoid):
                continue
            cells.append((h01(seed, x, y), x, y))
    cells.sort()
    out = []
    for _, x, y in cells:
        if all(abs(x - ox) + abs(y - oy) > 5 for ox, oy in out):
            out.append((x, y))
        if len(out) == n:
            break
    return out


MONSTERS = {"elder": [("Wolf", 1), ("Bear", 1), ("Giant_Spider", 1)], "downs": [("Skeleton", 2), ("Bat", 1)]}
SETTLER_LINES = {
    "Thornwick": "The Druid says the Heartwood is sickening. Even the bears have gone mad. It's out north-east, deep in the trees.",
    "Ravensgate": "The old king won't stay in his barrow. The Gravekeeper wants someone brave. The barrow's east, out on the downs.",
}
CHESTS = {
    "6,6,0": ("ElderwoodChest", [("Yew_Logs", 5), ("Super_Potion", 2), ("Gold_Coin(s)", 90)],
              "Wedged in a hollow oak: five yew logs, two super potions and 90 gold!"),
    "7,8,0": ("DownsChest", [("Emerald", 1), ("Sapphire", 1), ("Gold_Coin(s)", 110)],
              "Under a toppled standing stone: an emerald, a sapphire and 110 gold!"),
}


def populate(maps, grid, busy):
    import build_scenery
    options = {}
    reach = reachable(grid)

    def add_npc(kind, name, gx, gy, opts=None):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(W.npc(kind, name, x, y))
        if opts:
            options.setdefault(m, {})[(name, x, y)] = opts

    def add(fn, name, gx, gy, *rest):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(fn(name, x, y, *rest))

    for town, (mx, my, giver, rack, text) in TOWNS.items():
        cx, cy = town_centre(town)
        tx, ty = TOWN_TILE[town]
        add_npc("GoodNPC", giver, cx - 2, cy - 2)
        houses = VILLAGES[town]["houses"]               # nearest the square first (villages.py)
        add_npc("GoodNPC", "Trader", *houses[1]["inside"])
        add_npc("GoodNPC", "Settler", cx + 3, cy + 2, "Zone=%d,%d,%d,%d" % (tx - 3, ty - 2, tx + 4, ty + 2))
        add_npc("GoodNPC", "Banker", *houses[0]["inside"])
        add(W.obj, "Notice", cx + 2, cy - 2)
        m, x, y = local(cx + 2, cy - 2)
        R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]
        if town == "Thornwick":
            add(W.obj, "Workbench", *houses[2]["benches"][0])
            add(W.obj, "Alchemy_Table", *houses[2]["benches"][1])
        else:
            add(W.obj, "Furnace", *houses[2]["benches"][0])
            add(W.obj, "Anvil", *houses[2]["benches"][1])
        build_scenery.SCATTER["%d,%d,0" % (mx, my)] = (60, 6, 0)
    # the landing at the end of the bridge: a notice
    lx, ly = GX0 + 4, WOLF_DEN_BRIDGE_Y - 2
    while grid.get((lx, ly)) not in ("Grass001", "Sand001", "Tall_Grass001") and lx < GX0 + 20:
        lx += 1
    add(W.obj, "Notice", lx, ly)
    m, x, y = local(lx, ly)
    R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice",
        "THE EASTREACH\\The Elderwood. Thornwick village is east.\\South of the woods: the Barrowdowns and Ravensgate."
        "\\Bears in the woods. Worse on the downs.", "Okay", "@end"), "end:", ("End",)]
    # the Heartwood: a standing stone in a ring of mushrooms, with yews round it
    sx, sy = SITES["Heartwood"]
    set_tile(maps, grid, sx, sy, "Standing_Stone001")
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        set_tile(maps, grid, sx + dx, sy + dy, "Mushroom_Ring001")
    for dx, dy in ((-3, 0), (3, 0), (0, -3)):
        set_tile(maps, grid, sx + dx, sy + dy, "Yew_Tree001")
    m, x, y = local(sx, sy + 1)
    maps[m]["triggers"].append(("Heartwood", x, y))
    add_npc("BadNPC", "Bear", sx - 1, sy + 2)
    # the Barrow: graves and broken walls round the old king, and his guards
    sx, sy = SITES["Barrow"]
    for dx, dy in ((-3, -3), (-2, -3), (-1, -3), (1, -3), (2, -3), (3, -3), (-3, -2), (3, -2)):
        set_tile(maps, grid, sx + dx, sy + dy, "Ruined_Wall001" if (dx + dy) % 2 else "Ruined_Wall002")
    for dx, dy, g in ((-2, 1, 1), (2, 1, 2), (-1, -1, 3), (1, -1, 1)):
        set_tile(maps, grid, sx + dx, sy + dy, "Grave00%d" % g)
    m, x, y = local(sx, sy + 3)
    maps[m]["triggers"].append(("Barrow Door", x, y))
    add_npc("BadNPC", "Barrow_King", sx, sy - 2)
    add_npc("BadNPC", "Skeleton", sx - 2, sy)
    add_npc("BadNPC", "Skeleton", sx + 2, sy)
    add(W.item, "Bones", sx - 1, sy + 1)
    add(W.item, "Bones", sx + 1, sy + 2)
    # hidden chests, then monsters and wildlife
    avoid = [town_centre(t) for t in TOWNS] + list(SITES.values()) + [(GX0, WOLF_DEN_BRIDGE_Y)]
    for name, (attr, loot, msg) in CHESTS.items():
        mx, my = (int(v) for v in name.split(",")[:2])
        spot = spots(grid, busy, reach, mx, my, 1, "chest" + name, avoid)
        if spot:
            x, y = spot[0]
            maps[name]["entities"].append(W.obj("Chest", x, y))
            busy.add((mx * GW + x - 1, my * GH + y - 1))
        build_scenery.CHESTS[name] = (attr, loot, msg)
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            name = "%d,%d,0" % (mx, my)
            land = land_of(mx * GW + 12, my * GH + 10)
            wanted = MONSTERS[land]
            places = spots(grid, busy, reach, mx, my, sum(n for _, n in wanted), "mon" + name,
                           [a for a in avoid if abs(a[0] - (mx * GW + 12)) < 30 and abs(a[1] - (my * GH + 10)) < 30])
            k = 0
            for creature, n in wanted:
                for _ in range(n):
                    if k < len(places):
                        x, y = places[k]
                        maps[name]["entities"].append(W.npc("BadNPC", creature, x, y))
                        k += 1
            if land == "elder":
                build_scenery.WILDLIFE[name] = [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 1)]
    for m, opts in options.items():
        C.NPC_OPTIONS.setdefault(m, {}).update(opts)


QUESTS = [
    ("The Withering Wood", [
        ("Giver", "Druid"), ("Attribute", "DruidQuest"),
        ("Stage0", "Speak to the Druid in Thornwick, in the Elderwood over the old bridge east of Greymoor."),
        ("Stage1", "Find the Heartwood, the old heart stone of the Elderwood, north-east of Thornwick, and touch it."),
        ("Stage2", "The blight has maddened the bears: slay four of them ($BlightBears of 4), then return to the Druid."),
        ("Stage3", "Return to the Druid in Thornwick."),
        ("Done", "4")]),
    ("The Barrow King", [
        ("Giver", "Gravekeeper"), ("Attribute", "BarrowQuest"),
        ("Stage0", "Speak to the Gravekeeper in Ravensgate, on the Barrowdowns."),
        ("Stage1", "Find the old king's barrow, out on the downs east of Ravensgate."),
        ("Stage2", "Lay the Barrow King to rest."),
        ("Stage3", "Return to the Gravekeeper in Ravensgate."),
        ("Done", "4")]),
]


def data():
    C.ENTITIES.update({
        "Druid": C.good("The Druid of Thornwick, in robes the colour of moss."),
        "Gravekeeper": C.good("The Gravekeeper of Ravensgate. He smells faintly of earth."),
        "Barrow_King": C.bad("The old king of the downs, crowned and long dead. He does not want to rest.", 90, 1.4, 8, 8,
                             90, 1.5, 1, 300, "Bones,1-1,100 Gold_Coin(s),30-60,100 Ruby,1-1,40 Silver_Bar,1-2,60"),
    })
    C.MOVEMENT.update({"Druid": (1, 0, "0.4", "4-10"), "Gravekeeper": (1, 0, "0.4", "4-10"),
                       "Barrow_King": (2, 3, "0.4", "3-8")})
    C.NEW_SHOPS.update({
        "SHOP-Thornwick": ("1.2", "0.7", ["Herb,10", "Empty_Vial,8", "Basic_Potion,4", "Bread,8", "Arrows,200",
                                          "Spade,2", "Oak_Logs,0", "Yew_Logs,0", "Super_Potion,0"]),
        "SHOP-Ravensgate": ("1.2", "0.7", ["Healing_Scroll,4", "Blank_Scroll,10", "Basic_Potion,4", "Meat_Pie,4",
                                           "Coal,10", "Iron_Ore,6", "Steel_Helm,0"]),
    })
    C.QUESTS.extend(QUESTS)


def scripts():
    S = R.S
    talk, conv, kill_count = R.talk, R.conv, R.kill_count
    S["Talk to Druid"] = talk("Druid", "DruidQuest", [
        (0, [conv("Druid", "You came over the old bridge? Then the wood let you in.\\The Heartwood, the old heart stone of the Elderwood, is sickening. Go to it, north-east of here, and lay your hand on it. Tell me what you feel.",
                  ("I'll go to the Heartwood.", "@d_ok"), ("Not now.", "@bye")),
             ("End",), "d_ok:", ("Update.Attribute", "DruidQuest", "=1"),
             ("Display.Message", "Yellow", "Quest started: The Withering Wood.")]),
        (1, [conv("Druid", "North-east, where the yews are oldest. You'll know the stone when you see it.", ("I'm on my way.", "@bye"))]),
        (2, [conv("Druid", "Cold, you say? Then the blight is in the beasts. Four maddened bears must be put down before the wood can heal.", ("I'll hunt them.", "@bye"))]),
        (3, [("Update.Attribute", "DruidQuest", "=4"),
             ("Give.Item", "Gold_Coin(s)", "150"), ("Give.Item", "Emerald_Ring", "1"),
             ("Update.Skill", "Herblore", "+2"), ("Update.Skill", "Woodcutting", "+2"),
             conv("Druid", "I can feel it: the Heartwood is warm again. Take this ring; the emerald is from the old roots. And my thanks.", ("Thank you!", "@d_done")),
             "d_done:", ("Display.Message", "Yellow", "Quest complete: The Withering Wood! You receive 150 gold, an emerald ring and experience.")]),
    ], "The Elderwood is breathing easy again. Walk softly under the old trees.")
    S["Heartwood"] = [
        "// The Heartwood stone (The Withering Wood). Generated by build_eastreach.py",
        ("Get.Value", "ATTRIBUTE", "DruidQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "DruidQuest", "=2"),
        ("Display.Message", "Yellow", "The heart stone is cold as a grave... and from the trees, a bear roars. Slay four maddened bears."),
        "end:", ("End",)]
    S["Kill Bear"] = kill_count("DruidQuest", 2, "BlightBears", 4, "Maddened bears slain for the Druid",
                                "Four bears! Return to the Druid in Thornwick.", then=3)
    S["Talk to Gravekeeper"] = talk("Gravekeeper", "BarrowQuest", [
        (0, [conv("Gravekeeper", "Every night the old king walks his barrow, and his dead walk with him.\\Someone must go in and lay him to rest. His barrow is out on the downs, east of Ravensgate. Will you?",
                  ("I'll find the barrow.", "@g_ok"), ("Not now.", "@bye")),
             ("End",), "g_ok:", ("Update.Attribute", "BarrowQuest", "=1"),
             ("Display.Message", "Yellow", "Quest started: The Barrow King.")]),
        (1, [conv("Gravekeeper", "East, on the open downs. Look for the broken walls.", ("I'll look.", "@bye"))]),
        (2, [conv("Gravekeeper", "You've seen him? Then you know. Strike him down, and the downs will sleep.", ("I will.", "@bye"))]),
        (3, [("Update.Attribute", "BarrowQuest", "=4"),
             ("Give.Item", "Gold_Coin(s)", "250"), ("Give.Item", "Mithril_Helm", "1"), ("Update.Skill", "Defence", "+2"),
             conv("Gravekeeper", "He's at rest? Truly? Ravensgate will sleep tonight. Take his helm, it's mithril, and this gold.", ("Thank you!", "@g_done")),
             "g_done:", ("Display.Message", "Yellow", "Quest complete: The Barrow King! You receive 250 gold, a mithril helm and Defence experience.")]),
    ], "The downs are quiet. Even the crows have stopped complaining.")
    S["Barrow Door"] = [
        "// The way into the barrow (The Barrow King). Generated by build_eastreach.py",
        ("Get.Value", "ATTRIBUTE", "BarrowQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "BarrowQuest", "=2"),
        ("Display.Message", "Red", "Broken walls, open graves... and a crowned skeleton rising from its tomb. The Barrow King!"),
        "end:", ("End",)]
    S["Kill Barrow_King"] = [
        "// The Barrow King falls (The Barrow King). Generated by build_eastreach.py",
        ("Get.Value", "ATTRIBUTE", "BarrowQuest", "Variable.1$"),
        (">Conditional", "$Variable.1<=2", "@end"),
        ("Update.Attribute", "BarrowQuest", "=3"),
        ("Display.Message", "Yellow", "The Barrow King crumbles to dust. Return to the Gravekeeper in Ravensgate."),
        "end:", ("End",)]


def trader_scripts():
    """The traders and settlers of every town (the Wildlands' and the Eastreach's): one script each, a branch a town."""
    towns = [(t, v[0], v[1], v[3]) for t, v in R.TOWNS.items()] + [(t, v[0], v[1], v[3]) for t, v in TOWNS.items()]
    lines = dict(R.SETTLER_LINES)
    lines.update(SETTLER_LINES)
    import build_walled                     # Wardhaven: a branch for each map its Trader and Settler stand on
    for m in dict.fromkeys(build_walled.TRADER_MAPS):
        mx, my = (int(v) for v in m.split(",")[:2])
        towns.append((build_walled.TOWN, mx, my, build_walled.TOWNS[build_walled.TOWN][3]))
    lines.update(build_walled.SETTLER_LINES)
    import build_cinder                     # Emberwatch, once it's been built
    for m in dict.fromkeys(build_cinder.TRADER_MAPS):
        mx, my = (int(v) for v in m.split(",")[:2])
        towns.append((build_cinder.TOWN, mx, my, build_cinder.TOWNS[build_cinder.TOWN][3]))
    lines.update(build_cinder.SETTLER_LINES)
    conv = R.conv
    trader = ["// The traders: each town's own wares. Generated by build_regions.py and build_eastreach.py"]
    for k, (town, mx, my, rack) in enumerate(towns):
        trader += [(">On.Map", "%d,%d,0" % (mx, my), "@t%d" % (k + 1)),
                   conv("Trader", "Welcome to %s! Have a look at my wares." % town, ("Show me.", "@shop%d" % k), ("Goodbye.", "@bye")),
                   ("End",), "shop%d:" % k, ("Display.Item.Rack", "SPECIFIC", "Trader", rack, "@bye"), ("End",),
                   "t%d:" % (k + 1)]
    trader += [conv("Trader", "Nothing to sell here, I'm afraid.", ("Goodbye.", "@bye")), "bye:", ("End",)]
    settler = ["// The settlers: gossip that hints at the quests. Generated by build_regions.py and build_eastreach.py"]
    for k, (town, mx, my, rack) in enumerate(towns):
        settler += [(">On.Map", "%d,%d,0" % (mx, my), "@g%d" % (k + 1)),
                    conv("Settler", lines[town], ("Thanks.", "@bye")), ("End",), "g%d:" % (k + 1)]
    settler += [conv("Settler", "Safe travels.", ("Thanks.", "@bye")), "bye:", ("End",)]
    R.S["Talk to Trader"] = trader
    R.S["Talk to Settler"] = settler


def bridge():
    """The old bridge: from the Wolf Den's clearing (5,6,0) east to the edge of the map, planks over the sea."""
    global WOLF_DEN_BRIDGE_Y
    sx, sy = R.SITES["WolfDen"]
    WOLF_DEN_BRIDGE_Y = sy + 3
    rev = R.legend_chars({"Dirt001", "Plank001"})
    for gx in range(sx + 3, R.GX1 + 1):
        m, x, y = R.local(gx, WOLF_DEN_BRIDGE_Y)
        row = W.MAPS[m]["rows"][y - 1]
        tile = W.LEGEND.get(row[x - 1], "")
        new = "Plank001" if tile.startswith("Water") or tile.startswith("Sand_Water") else "Dirt001"
        W.MAPS[m]["rows"][y - 1] = row[:x - 1] + rev[new] + row[x:]


# ------------------------------------------------------------------ the new people's pictures (recolours)
def make_art():
    """The Druid (the Witch in moss green), the Gravekeeper (the Elder in charcoal) and the Barrow King (the Skeleton,
    bones gone grey-green, with a gold crown): Sprites\\Entities and the 12 walking frames in Sprites\\Walk."""
    import colorsys
    import sprite_kit as K
    from common import p

    def druid(c):
        r, g, b = (v / 255 for v in c)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if 0.66 < h < 0.95 and s > 0.25:          # the purple robe and hat
            r, g, b = colorsys.hsv_to_rgb(0.28, min(1, s * 0.85), v * 0.9)
        return tuple(int(round(x * 255)) for x in (r, g, b))

    def gravekeeper(c):
        r, g, b = (v / 255 for v in c)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s < 0.18 and 0.2 < v < 0.78:           # the grey robe (not the white beard or the skin)
            r, g, b = colorsys.hsv_to_rgb(0.62, 0.15, v * 0.42)
        return tuple(int(round(x * 255)) for x in (r, g, b))

    def wight(c):
        r, g, b = c
        if min(c) > 120:                          # bone: a deathly grey-green
            return (int(r * 0.72), int(g * 0.86), int(b * 0.70))
        return c

    def recolour(img, fn):
        return [[None if px is None else fn(px) for px in row] for row in img]

    def crown(img):
        """A small gold crown on the topmost row of the skull."""
        w, h = K.size(img)
        top = next((y for y in range(h) for x in range(w // 2 - 4, w // 2 + 4) if img[y][x] is not None), None)
        if top is None or top < 3:
            return img
        xs = [x for x in range(w) if img[top][x] is not None]
        cx = (min(xs) + max(xs)) // 2
        gold, shine = (214, 170, 40), (250, 220, 90)
        for x in range(cx - 3, cx + 4):
            K.put(img, x, top - 1, gold)
        for x in (cx - 3, cx, cx + 3):
            K.put(img, x, top - 2, gold)
            K.put(img, x, top - 3, shine)
        return img

    made = []
    jobs = [("Witch", "Druid", druid, False), ("Elder", "Gravekeeper", gravekeeper, False),
            ("Skeleton", "Barrow_King", wight, True)]
    for src, dst, fn, crowned in jobs:
        frames = [("Entities", src, dst)]
        for d in "1248":
            for f in "abc":
                if os.path.exists(p("Sprites", "Walk", src + d + f + ".png")):
                    frames.append(("Walk", src + d + f, dst + d + f))
        for kind, a, b in frames:
            img = recolour(K.load(kind, a), fn)
            if crowned:
                img = crown(img)
            if K.save(kind, b, img):
                made.append("Sprites\\%s\\%s.png" % (kind, b))
    return made


# ------------------------------------------------------------------ hook
def extend(world, content, regions):
    global W, C, R
    W, C, R = world, content, regions
    bridge()                                # first: the bridge row is worked out from the Wolf Den
    grid, roofs, busy = build_grid()
    maps = make_maps(grid, roofs)
    maps.update(R.upper_maps([hs for v in VILLAGES.values() for hs in v["houses"]], GW, GH))
    data()
    populate(maps, grid, busy)
    scripts()
    trader_scripts()
    W.MAPS.update(maps)
    W.SEAMLESS_MAPS.update(maps)
    W.SEAMLESS_MAPS.update({"5,6,0": True})
    W.S.update(R.S)
    W.EXTRA_STEPS.insert(0, make_art)
