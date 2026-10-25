"""The Cinderlands (12 maps, 6,2,0 to 9,4,0, north of the Elderwood over the Heartwood bridge), the main story and the
side quests' requirements, the banks' new look and Wardhaven's Dragonforge.

Not run on its own: build_content.extend() calls extend() here after build_palace (it needs build_regions' helpers) and
before the interiors, the waystones and the scenery pass (so its town is furnished and gets a waystone, its maps
scenery and wildlife), and finish() at the very end (when every quest and script is made). `python -I
"Dev\\migrate\\build_world.py"` builds it. Deterministic: the same maps every time.

  * THE ASHWOLD (map row 4 and the south of row 3): heath burnt to ash, dead trees, ember hounds and the Ashen Hand's
    cultists. EMBERWATCH, a frontier town with a bank, a trader, a smithy, the Warden and a Scout; three burnt SHRINES.
  * THE CINDER PEAKS (map rows 2-3): basalt, lava pools that glow at night, ember vents, coal, gold and mithril, and the
    CINDER FORT, the cult's stronghold, where the Ashen Priest waits.
  * THE HEARTWOOD BRIDGE: a path north from the Heartwood's clearing (8,5,0) to the shore and planks over the strait.
  * THE MAIN STORY (Quests.ini Type=Main, Chapter): Passage to the Mainland, King's Hobgoblin Hunt, The Ashen Hand (new,
    here), The Ashen Omens, The Dragon of Ashpeak. Every other quest is a side quest with Requires (REQUIREMENTS): a
    level, quests done first, skills. finish() puts a >Quest.Can.Start before every quest giver's offer.
  * SIDE QUEST: The Lost Patrol (the Scout): three Scout's Tags from the ember hounds.
  * BANKS: every bank (a house with a Banker in it) gets a copper roof (house_tiles Copper), white columns either side of
    its door and a gilt plaque over its sign. The Isle, Southport, Tyron's Keep and the Royal Isle get a Banker (behind
    a marble counter where there's room) in a house there, which then becomes their bank (stalls_indoors).
    (patch_files(): the maps you've edited since the last build get them too.)
  * WARDHAVEN, once the dragon is dead: the DRAGONFORGE in its square, where the Wyrmsmith forges Dragonscale armour from
    Ignaroth's scales (the dragon drops them; it can be fought again), a gilt statue of the dragon-slayer and the
    dragon's skull on a plinth.
Pictures: cinder_art.py."""
import math
import os
import random

W = C = R = None        # build_world, build_content, build_regions

MX0, MX1, MY0, MY1 = 6, 9, 2, 4
GW, GH = 25, 21
GX0, GX1, GY0, GY1 = MX0 * GW, (MX1 + 1) * GW - 1, MY0 * GH, (MY1 + 1) * GH - 1
BRIDGE_MAP, BRIDGE_COL, BRIDGE_FROM_ROW = "8,5,0", 15, 15      # the path starts by the Heartwood's clearing
BRIDGE_X = 8 * GW + BRIDGE_COL - 1
TOWN = "Emberwatch"
TOWNS = {TOWN: (7, 4, "Warden", "SHOP-Emberwatch",
                "EMBERWATCH\\The last fort before the Cinderlands.\\South: the bridge to the Heartwood and the Elderwood."
                "\\North: the Cinder Peaks.")}
TOWN_TILE = {TOWN: (12, 10)}
SITES = {
    "Shrine1": (6 * GW + 8, 4 * GH + 9),        # the western Ashwold
    "Shrine2": (9 * GW + 13, 4 * GH + 7),       # the eastern Ashwold
    "Shrine3": (7 * GW + 17, 3 * GH + 16),      # under the peaks, north of the town
    "Fort": (8 * GW + 12, 2 * GH + 9),          # the Cinder Fort, high in the peaks
}
FORT_HALF = (5, 4)                              # the fort's walls: Fort +- these
VILLAGES = {}
TRADER_MAPS = []        # the maps the Trader and the Settler stand on (build_eastreach.trader_scripts branches on them)
LAND_ASH = {"Ash001", "Grass001", "Sand001", "Dirt001", "Plank001", "Cinder001"}
SETTLER_LINES = {TOWN: "The Warden says the cult burnt the shrines first. Then the farms. Now there's a fire in the "
                       "Cinder Fort every night. Ask her if you want work."}
MARKERS = {}            # quest -> {stage: "place;place"} (build_places), filled once the sites are known


def h01(*parts):
    return R.h01("cinder", *parts)


def fbm(x, y, scale, seed):
    return R.fbm(x, y, scale, 900 + seed)


def town_centre(name):
    mx, my = TOWNS[name][0], TOWNS[name][1]
    tx, ty = TOWN_TILE[name]
    return mx * GW + tx - 1, my * GH + ty - 1


def local(gx, gy):
    mx, my = gx // GW, gy // GH
    return "%d,%d,0" % (mx, my), gx - mx * GW + 1, gy - my * GH + 1


def land_of(gx, gy):
    wy = gy + 10 * (fbm(gx, gy, 14, 1) - 0.5)
    return "cinder" if wy < GY0 + int(1.45 * GH) else "ash"


def coast(gx, gy):
    """Tiles from the sea (under 2.2 sea, under 4.2 beach); the town, the sites and the bridge's landing on land."""
    sides = [gx - GX0, GX1 - gx, gy - GY0, GY1 - gy]
    if min(sides) < 1:
        return 0
    d = min(sides)
    rr = 30.0
    for a, b in ((gx - GX0, gy - GY0), (GX1 - gx, gy - GY0), (gx - GX0, GY1 - gy), (GX1 - gx, GY1 - gy)):
        if a < rr and b < rr:
            d = min(d, rr - math.hypot(rr - a, rr - b))
    d += 26 * (fbm(gx, gy, 18, 3) - 0.5) + 8 * (fbm(gx, gy, 6, 4) - 0.5) - 3
    cx, cy = town_centre(TOWN)
    d = max(d, 7 - 0.7 * max(0.0, math.hypot((gx - cx) / 1.2, gy - cy) - 12))
    for sx, sy in SITES.values():
        d = max(d, 6 - 0.7 * max(0.0, math.hypot(gx - sx, gy - sy) - 6))
    d = max(d, 6 - 0.6 * max(0.0, math.hypot(gx - BRIDGE_X, (gy - (GY1 - 5)) * 0.8) - 3))   # (the landing)
    return d


DECOR = "%s+Decor(%s)"


def base_tile(gx, gy):
    c = coast(gx, gy)
    if c < 2.2:
        return "Water001"
    if c < 4.2:
        return "Sand001"
    r = h01("cell", gx, gy)
    if land_of(gx, gy) == "ash":
        if fbm(gx, gy, 9, 5) > 0.6 and r < 0.45:
            return DECOR % ("Ash001", "Dead_Tree00%d" % (1 + int(r * 100) % 2))
        if fbm(gx, gy, 8, 6) > 0.68:
            return "Grass001" if r > 0.08 else DECOR % ("Grass001", "Tall_Grass001")
        if r < 0.006:
            return DECOR % ("Ash001", "Basalt_Rock001")
        if r < 0.010:
            return DECOR % ("Ash001", "Tree_Stump001")
        if r < 0.012:
            return DECOR % ("Ash001", "Coal_Rock001")
        return "Ash001"
    n = fbm(gx, gy, 8, 7)
    if n > 0.71:
        return "Lava001"
    if r < 0.012 and n < 0.66:
        return DECOR % ("Cinder001", "Basalt_Rock001")
    if r < 0.018 and n < 0.66:
        return DECOR % ("Cinder001", "Ember_Vent001")
    if r < 0.022:
        return DECOR % ("Cinder001", "Coal_Rock001")
    if r < 0.024:
        return DECOR % ("Cinder001", "Gold_Rock001")
    if r < 0.0255:
        return DECOR % ("Cinder001", "Mithril_Rock001")
    return "Cinder001"


def walkable(t):
    """Can the feet go there (bare ground, or ground with grass or a stump on it)?"""
    return t.split("+")[0] in LAND_ASH and ("Decor(" not in t or "Tall_Grass" in t or "Tree_Stump" in t)


def build_grid():
    import villages
    grid = {(gx, gy): base_tile(gx, gy) for gy in range(GY0, GY1 + 1) for gx in range(GX0, GX1 + 1)}
    R.smooth_coast(grid)
    busy = set()
    cx, cy = town_centre(TOWN)
    v = villages.build(grid, busy, cx, cy, 930, "hills", "Ash001", lambda gx, gy: coast(gx, gy) < 4.2, GW, GH,
                       {"Ash001", "Grass001", "Cinder001"},
                       keep_out={(sx + dx, sy + dy) for sx, sy in SITES.values() for dx in range(-6, 7)
                                 for dy in range(-6, 7)})
    VILLAGES[TOWN] = v
    roofs, groups = [], {}
    for x1, y1, x2, y2, material in v["roofs"]:
        m = (x1 // GW, y1 // GH)
        groups[m] = groups.get(m, 0) + 1
        roofs.append((x1, y1, x2, y2, groups[m], material))
    # the sites' clearings
    for name, (sx, sy) in SITES.items():
        rx, ry = (FORT_HALF[0] + 2, FORT_HALF[1] + 2) if name == "Fort" else (3, 3)
        for gy in range(sy - ry, sy + ry + 1):
            for gx in range(sx - rx, sx + rx + 1):
                if (gx, gy) in grid:
                    grid[(gx, gy)] = "Cinder001" if land_of(sx, sy) == "cinder" else "Ash001"
                busy.add((gx, gy))
    # the fort: stone walls round a basalt yard (as Wardhaven's: the north and south ones two tiles tall, towers at the
    # corners), an open gateway in the south wall
    fx, fy = SITES["Fort"]
    hx, hy = FORT_HALF
    x0, x1, y0, y1 = fx - hx, fx + hx, fy - hy, fy + hy
    for gx in range(x0, x1 + 1):
        for gy in (y0, y1 - 1):
            if gy == y1 - 1 and abs(gx - fx) <= 1:
                grid[(gx, gy)] = grid[(gx, gy + 1)] = "Cinder001"         # (the gateway)
                continue
            grid[(gx, gy)] = "City_Wall001"
            grid[(gx, gy + 1)] = "City_Wall004"
    for gy in range(y0 + 2, y1 - 1):
        for gx in (x0, x1):
            grid[(gx, gy)] = "City_Wall002"
    for gx, gy in ((x0, y0), (x1, y0), (x0, y1 - 1), (x1, y1 - 1), (fx - 2, y1 - 1), (fx + 2, y1 - 1)):
        grid[(gx, gy)] = "City_Wall003"
        grid[(gx, gy + 1)] = "City_Wall005"
    grid[(fx, fy - 2)] = DECOR % ("Cinder001", "Cult_Shrine001")
    for gx, gy in ((fx - 3, fy - 2), (fx + 3, fy - 2)):
        grid[(gx, gy)] = DECOR % ("Cinder001", "Ember_Vent001")
    # the shrines
    for k in (1, 2, 3):
        sx, sy = SITES["Shrine%d" % k]
        grid[(sx, sy)] = DECOR % ("Ash001", "Cult_Shrine001")
        for dx, dy in ((-2, -1), (2, -1), (-2, 2), (2, 2)):
            grid[(sx + dx, sy + dy)] = DECOR % ("Ash001", "Dead_Tree00%d" % (1 + (dx > 0)))
    # the bridge: planks north from the south edge to the first dry land
    y = GY1
    while y > GY0 and not (walkable(grid[(BRIDGE_X, y)]) and walkable(grid[(BRIDGE_X, y - 1)])):
        if not walkable(grid[(BRIDGE_X, y)]):
            grid[(BRIDGE_X, y)] = "Plank001"
        busy.add((BRIDGE_X, y))
        y -= 1
    landing = (BRIDGE_X, y)

    def lay(cells):
        for (x, y) in cells:
            t = grid.get((x, y))
            if t is None or t in villages.HOUSE_TILES or t.startswith(("Ruined_Wall", "City_Wall")):
                continue
            if "Cult_Shrine" in t:
                continue
            grid[(x, y)] = "Plank001" if t.startswith(("Water", "Sand_Water")) else "Dirt001"
            busy.add((x, y))

    def gate(toward):
        tx, ty = toward
        if abs(tx - cx) > abs(ty - cy):
            return (cx + (11 if tx > cx else -11), cy)
        return (cx, cy + (9 if ty > cy else -9))
    import build_eastreach as E
    lay(E.line(landing, gate(landing), 3, 960))
    fort_gate = (fx, fy + hy + 1)
    lay(E.line(gate(fort_gate), fort_gate, 6, 961))
    lay([(fx, fy + hy - d) for d in range(0, 3)])                  # in through the gate
    for k in (1, 2, 3):
        sx, sy = SITES["Shrine%d" % k]
        best = min((p for p, t in grid.items() if t == "Dirt001" and abs(p[0] - sx) + abs(p[1] - sy) > 6),
                   key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))
        lay(E.line((sx, sy + 3), best, 2, 970 + k))
    R.smooth_shores(grid)
    return grid, roofs, busy, landing


def make_maps(grid, roofs):
    rev = R.legend_chars(set(grid.values()))
    maps = {}
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            rows = ["".join(rev[grid[(mx * GW + x, my * GH + y)]] for x in range(GW)) for y in range(GH)]
            mroofs = [(r[0] - mx * GW + 1, r[1] - my * GH + 1, r[2] - mx * GW + 1, r[3] - my * GH + 1) + tuple(r[4:])
                      for r in roofs if mx * GW <= r[0] < (mx + 1) * GW and my * GH <= r[1] < (my + 1) * GH]
            maps["%d,%d,0" % (mx, my)] = dict(rows=rows, roofs=mroofs, entities=[], triggers=[])
    return maps


def spots(grid, busy, mx, my, n, seed, avoid=()):
    cells = []
    for y in range(2, GH):
        for x in range(2, GW):
            gx, gy = mx * GW + x - 1, my * GH + y - 1
            if grid[(gx, gy)] not in ("Ash001", "Cinder001", "Grass001") or (gx, gy) in busy:
                continue
            if any(abs(gx - ax) + abs(gy - ay) < 6 for ax, ay in avoid):
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


MONSTERS = {"ash": [("Ember_Hound", 2), ("Ashen_Cultist", 1)], "cinder": [("Ashen_Cultist", 2), ("Ember_Hound", 1)]}


def populate(maps, grid, busy, landing):
    import build_scenery
    options = {}

    def add_npc(kind, name, gx, gy, opts=None):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(W.npc(kind, name, x, y))
        if opts:
            options.setdefault(m, {})[(name, x, y)] = opts
        return m

    def add(fn, name, gx, gy, *rest):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(fn(name, x, y, *rest))
        return m, x, y

    cx, cy = town_centre(TOWN)
    TRADER_MAPS[:] = []
    tx, ty = TOWN_TILE[TOWN]
    houses = VILLAGES[TOWN]["houses"]
    add_npc("GoodNPC", "Warden", cx - 2, cy - 2, "Stand=1")
    add_npc("GoodNPC", "Scout", cx + 4, cy - 2, "Stand=1")
    add_npc("GoodNPC", "Banker", *houses[0]["inside"])
    TRADER_MAPS.append(add_npc("GoodNPC", "Trader", *houses[1]["inside"]))
    add(W.obj, "Furnace", *houses[2]["benches"][0])
    add(W.obj, "Anvil", *houses[2]["benches"][1])
    TRADER_MAPS.append(add_npc("GoodNPC", "Settler", cx + 3, cy + 2,
                               "Zone=%d,%d,%d,%d" % (tx - 3, ty - 2, tx + 4, ty + 2)))
    m, x, y = add(W.obj, "Notice", cx + 2, cy - 2)
    R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice", TOWNS[TOWN][4], "Okay", "@end"), "end:",
                                          ("End",)]
    m, x, y = add(W.obj, "Notice", landing[0] + 1, landing[1] - 1)
    R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice",
        "THE CINDERLANDS\\North: Emberwatch, the last fort. Beyond it the Ashwold, and the Cinder Peaks.\\Ember hounds "
        "on the heath. Worse in the hills.", "Okay", "@end"), "end:", ("End",)]
    # the shrines: a trigger in front of each; a cultist keeps watch
    for k in (1, 2, 3):
        sx, sy = SITES["Shrine%d" % k]
        m, x, y = local(sx, sy + 1)
        maps[m]["triggers"].append(("Ashen Shrine %d" % k, x, y))
        add_npc("BadNPC", "Ashen_Cultist", sx + 2, sy + 1)
    # the fort: the priest by the altar, his cultists, the way in
    fx, fy = SITES["Fort"]
    add_npc("BadNPC", "Ashen_Priest", fx, fy - 1, "Stand=1")
    for dx, dy in ((-3, 1), (3, 1), (-1, 2), (2, -1)):
        add_npc("BadNPC", "Ashen_Cultist", fx + dx, fy + dy)
    m, x, y = local(fx, fy + FORT_HALF[1])
    maps[m]["triggers"].append(("Cinder Fort Gate", x, y))
    # monsters and a hidden chest on every map, kept off the roads, the town and the sites
    avoid = [town_centre(TOWN)] + list(SITES.values()) + [landing]
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            name = "%d,%d,0" % (mx, my)
            wanted = MONSTERS[land_of(mx * GW + 12, my * GH + 10)]
            places = spots(grid, busy, mx, my, sum(n for _, n in wanted), "mon" + name, avoid)
            k = 0
            for creature, n in wanted:
                for _ in range(n):
                    if k < len(places):
                        maps[name]["entities"].append(W.npc("BadNPC", creature, *places[k]))
                        k += 1
            build_scenery.SCATTER[name] = (25, 3, 0)
    for name, (attr, loot, msg) in CHESTS.items():
        mx, my = (int(v) for v in name.split(",")[:2])
        spot = spots(grid, busy, mx, my, 1, "chest" + name, avoid)
        if spot:
            maps[name]["entities"].append(W.obj("Chest", *spot[0]))
            busy.add((mx * GW + spot[0][0] - 1, my * GH + spot[0][1] - 1))
        build_scenery.CHESTS[name] = (attr, loot, msg)
    for m, opts in options.items():
        C.NPC_OPTIONS.setdefault(m, {}).update(opts)
    import build_places as PL                               # (each marker a named place)
    town = lambda name, dx=-2, dy=-2: PL.marker(name, "%s %d %d" % local(cx + dx, cy + dy))
    site = lambda name, s, dy=0: PL.marker(name, "%s %d %d" % local(SITES[s][0], SITES[s][1] + dy))
    MARKERS["The Ashen Hand"] = {1: ";".join(site("Burnt_Shrine_%d" % k, "Shrine%d" % k, 1) for k in (1, 2, 3)),
                                 2: town("Emberwatch_Square"), 3: site("Cinder_Fort", "Fort", FORT_HALF[1]),
                                 4: town("Emberwatch_Square")}
    MARKERS["The Lost Patrol"] = {1: town("Emberwatch_Scout", 4)}


CHESTS = {
    "6,3,0": ("CinderChest1", [("Mithril_Ore", 3), ("Super_Potion", 2), ("Gold_Coin(s)", 140)],
              "Under a fallen slab of basalt: three lumps of mithril ore, two super potions and 140 gold!"),
    "9,2,0": ("CinderChest2", [("Ruby", 2), ("Fire_Storm_Scroll", 2), ("Gold_Coin(s)", 160)],
              "A cultist's cache in a cooled lava tube: two rubies, two fire storm scrolls and 160 gold!"),
}


# ------------------------------------------------------------------ data
QUESTS = [
    ("The Ashen Hand", [
        ("Giver", "Warden"), ("Attribute", "AshenHandQuest"),
        ("Stage0", "Rumours of a cult, the Ashen Hand, in the Cinderlands north of the Elderwood. Cross the Heartwood "
                   "bridge and speak to the Warden in Emberwatch."),
        ("Stage1", "Find the Ashen Hand's three burnt shrines in the Ashwold ($ShrinesFound of 3)."),
        ("Stage2", "Report to the Warden in Emberwatch."),
        ("Stage3", "Storm the Cinder Fort, high in the Cinder Peaks, and defeat the Ashen Priest."),
        ("Stage4", "Bring the Ashen Codex to the Warden in Emberwatch."),
        ("Done", "5")]),
    ("The Lost Patrol", [
        ("Giver", "Scout"), ("Attribute", "PatrolQuest"),
        ("Stage0", "Speak to the Scout in Emberwatch: her patrol went out on the Ashwold and didn't come back."),
        ("Stage1", "Recover three Scout's Tags from the ember hounds on the Ashwold and bring them to the Scout."),
        ("Done", "2")]),
]
# The main story and what every quest needs before it can be started: Type=Main and Chapter for the story; Requires.
REQUIREMENTS = {
    "Passage to the Mainland": dict(Type="Main", Chapter="1"),
    "King's Hobgoblin Hunt": dict(Type="Main", Chapter="2", Quests="Passage to the Mainland"),
    "The Ashen Hand": dict(Type="Main", Chapter="3", Quests="King's Hobgoblin Hunt", Level="12"),
    "The Ashen Omens": dict(Type="Main", Chapter="4", Quests="The Ashen Hand", Level="15"),
    "The Dragon of Ashpeak": dict(Type="Main", Chapter="5", Quests="The Ashen Omens", Level="18"),
    "The Beggar's Lost Key": dict(Level="3"),
    "The Herbalist's Remedy": dict(Quests="Passage to the Mainland", Level="3"),
    "The Hermit's Fire": dict(Skills="Woodcutting 10"),
    "The Wildwood Watch": dict(Quests="King's Hobgoblin Hunt", Level="5"),
    "Wolves of the Moor": dict(Level="6"),
    "Bog Lights": dict(Level="6", Skills="Herblore 5"),
    "The Dwarf's Grudge": dict(Quests="King's Hobgoblin Hunt", Level="8"),
    "Old Hob": dict(Quests="Bog Lights"),
    "Bandits on the Road": dict(Level="9"),
    "The Lost Caravan": dict(Quests="Bandits on the Road", Level="11"),
    "The Withering Wood": dict(Quests="Wolves of the Moor", Level="12"),
    "The Frozen Forge": dict(Level="13"),
    "The Lost Patrol": dict(Level="14"),
    "The Barrow King": dict(Quests="The Withering Wood", Level="15"),
}
STAGE0 = {   # quests whose first step now reads differently (the story leads into them)
    "The Ashen Omens": "The Ashen Codex says the cult means to wake a dragon. Take the news to the court wizard at the "
                       "top of the palace tower on the Royal Isle.",
    "The Dragon of Ashpeak": "Once the omens are read, the court wizard on the Royal Isle will know what to do.",
}


def data():
    E = C.ENTITIES
    E.update({
        "Warden": C.good("The Warden of Emberwatch, in a scorched red cloak. She hasn't slept much lately."),
        "Scout": C.good("A scout of Emberwatch, ash in her hair and a bow on her back."),
        "Wyrmsmith": C.good("The Wyrmsmith of Wardhaven: they say she was waiting twelve years for someone to kill a "
                            "dragon.", use="Talk to,Forge"),
        "Ashen_Cultist": C.bad("A cultist of the Ashen Hand. The ash on his hands is still warm.", 40, 1.3, 6, 6, 90, 2, 1,
                               60, "Bones,1-1,100 Gold_Coin(s),10-25,100 Fire_Bolt_Scroll,1-1,15")
                         + [("On.Hit", "Burn 10")],
        "Ashen_Priest": C.bad("The Ashen Priest, who sings to the dragon under Ashpeak. His robes smoulder.", 130, 1.4, 9,
                              9, 120, 2, 1, 600, "Bones,1-1,100 Gold_Coin(s),60-120,100 Fire_Storm_Scroll,1-1,50")
                        + [("On.Hit", "Burn 25")],
        "Ember_Hound": C.bad("An ember hound: a wolf of the burnt heath, its mane smouldering.", 30, 1.0, 6, 4, 100, 3, 1,
                             45, "Bones,1-1,100 Scout_Tag,1-1,35") + [("On.Hit", "Burn 15")],
        "Ashen_Codex": C.item(0, "The Ashen Priest's codex: page after page of a song to wake the dragon under Ashpeak. "
                                 "The Warden must see this.", droppable=0),
        "Scout_Tag": C.item(5, "A dented steel tag on a chain: one of Emberwatch's lost scouts.", 10),
        "Dragon_Scale": C.item(120, "A scale from Ignaroth's hide, still warm. The Wyrmsmith of Wardhaven knows what to "
                                    "do with these.", 50),
        "Dragonforge": C.station("Forge", "The Dragonforge: obsidian and dragonfire. Only dragon scale will take its "
                                          "heat.") + [("Light", "60"),
                                                      ("Walkable.Data", "1" * 21 + "0" * 28)],
        "Dragonscale_Helm": C.equip(900, "A helm of dragon scale on a mithril frame.", "Head", 0, 6, "Defence 30"),
        "Dragonscale_Platebody": C.equip(2200, "Dragonscale armour: fire slides off it like rain.", "Body", 0, 10,
                                         "Defence 35") + [("Resists", "Burn")],
        "Dragonscale_Platelegs": C.equip(1500, "Dragonscale greaves.", "Legs", 0, 8, "Defence 32"),
        "Dragonscale_Shield": C.equip(1600, "A shield faced with dragon scale. It turns blows and flame alike.",
                                      "Shield", 0, 9, "Defence 32"),
        "Dragonscale_Boots": C.equip(700, "Boots of dragon scale.", "Feet", 0, 4, "Defence 30"),
    })
    C.MOVEMENT.update({"Warden": (0, 0, "0.4", "4-10"), "Scout": (0, 0, "0.4", "4-10"), "Wyrmsmith": (0, 0, "0.4", "4-10"),
                       "Ashen_Cultist": (2, 3, "0.4", "3-8"), "Ashen_Priest": (1, 2, "0.4", "3-8"),
                       "Ember_Hound": (3, 4, "0.5", "2-6")})
    C.NEW_SHOPS["SHOP-Emberwatch"] = ("1.3", "0.8", ["Super_Potion,6", "Antidote,6", "Meat_Pie,8", "Arrows,300",
                                                     "Coal,10", "Fire_Bolt_Scroll,6", "Mithril_Ore,0", "Dragon_Scale,0",
                                                     "Scout_Tag,0"])
    C.CRAFT["CRAFT-Dragonforge"] = ("Smithing", [
        "Dragonscale_Boots,Dragon_Scale 2 Mithril_Bar 1,3.0,30",
        "Dragonscale_Helm,Dragon_Scale 3 Mithril_Bar 1,3.5,32",
        "Dragonscale_Shield,Dragon_Scale 4 Mithril_Bar 2,4.5,34",
        "Dragonscale_Platelegs,Dragon_Scale 5 Mithril_Bar 2,5.0,36",
        "Dragonscale_Platebody,Dragon_Scale 6 Mithril_Bar 3,6.0,38",
    ])
    for t, (walk, show, use, exa, los, col) in TILE_DATA.items():
        C.TILES[t] = (walk, show, use, exa, los, col)
    for t, keys in TILE_KEYS.items():
        C.TILE_EXTRA.setdefault(t, []).extend(keys)
    C.QUESTS.extend([(n, list(k)) for n, k in QUESTS])


BLOCKED, OPEN = "0" * 49, "1" * 49
TILE_DATA = {   # name: (Walkable.Data, Show.Name, Use.Words, Examine.Info, Line.of.Sight, minimap colour)
    "Ash001": (OPEN, "0", "", "Ash, ankle deep. Nothing grows here but weeds.", "1", "112 106 100"),
    "Cinder001": (OPEN, "0", "", "Black rock, cracked as it cooled.", "1", "64 58 60"),
    "Lava001": (BLOCKED, "1", "", "Molten rock. Don't.", "1", "230 110 30"),
    "Dead_Tree001": ("1111111" * 3 + "1110111" * 3 + "1111111", "1", "", "A tree burnt to a black stick.", "1",
                     "54 46 42"),
    "Dead_Tree002": ("1111111" * 3 + "1110111" * 3 + "1111111", "1", "", "A tree burnt to a black stick.", "1",
                     "54 46 42"),
    "Basalt_Rock001": ("1111111" + "1000001" * 5 + "1111111", "1", "", "A lump of black basalt.", "1", "70 64 70"),
    "Ember_Vent001": ("1111111" * 2 + "1000001" * 3 + "1111111" * 2, "1", "", "A crack in the rock, glowing with heat.",
                      "1", "200 100 40"),
    "Cult_Shrine001": ("1111111" + "1000001" * 5 + "1111111", "1", "Examine",
                       "An altar of the Ashen Hand: black stone, a burnt red handprint, candles that never go out.", "1",
                       "40 30 36"),
    "Bank_Column001": (BLOCKED, "0", "", "A white marble column. Only the bank can afford those.", "0", None),
    "Bank_Plaque001": (BLOCKED, "1", "", "A gilt plaque with a gold coin: the bank.", "0", None),
    "Bank_Counter001": ("1111111" * 2 + "0000000" * 4 + "1111111", "1", "",
                        "The bank's counter: marble, a ledger, and coins stacked just out of reach.", "1", "232 228 220"),
    "Hero_Statue001": ("1111111" * 2 + "1000001" * 4 + "1111111", "1", "Examine",
                       "A gilt statue of the dragon-slayer, sword raised to the sky.", "1", "214 172 60"),
    "Dragon_Skull001": ("1111111" * 2 + "1000001" * 4 + "1111111", "1", "Examine",
                        "The skull of Ignaroth, on a black plinth. One socket still glows, faintly.", "1",
                        "222 212 188"),
}
TILE_KEYS = {   # the other Tiles.ini keys
    "Ash001": [("Blend", "3"), ("Blend.Texture", "Ash001")],
    "Cinder001": [("Blend", "2"), ("Blend.Texture", "Cinder001")],
    "Lava001": [("Flame", "1"), ("Light", "40")],
    "Ember_Vent001": [("Layer", "Decor"), ("Flame", "1"), ("Light", "36")],
    "Cult_Shrine001": [("Layer", "Decor"), ("Flame", "1"), ("Light", "30")],
    "Dead_Tree001": [("Layer", "Decor")], "Dead_Tree002": [("Layer", "Decor")],
    "Basalt_Rock001": [("Layer", "Decor")], "Bank_Column001": [("Layer", "Decor")],
    "Bank_Plaque001": [("Layer", "Decor")], "Bank_Counter001": [("Layer", "Decor")],
    "Hero_Statue001": [("Layer", "Decor")], "Dragon_Skull001": [("Layer", "Decor")],
}
import fence_tiles                         # the wooden and iron fences (decor)
TILE_DATA.update(fence_tiles.TILE_DATA)
TILE_KEYS.update(fence_tiles.TILE_KEYS)
import decor_sets                           # rugs, potted plants, and which piece of a set each tile is
TILE_DATA.update(decor_sets.TILE_DATA)
for _t, _keys in decor_sets.TILE_KEYS.items():
    TILE_KEYS[_t] = [kv for kv in TILE_KEYS.get(_t, []) if kv[0] not in dict(_keys)] + _keys


# ------------------------------------------------------------------ scripts
def scripts():
    S = R.S
    talk, conv = R.talk, R.conv
    S["Talk to Warden"] = talk("Warden", "AshenHandQuest", [
        (0, [conv("Warden", "You came over the Heartwood bridge? Then you've seen the smoke.\\The Ashen Hand: a cult that "
                            "worships fire, and worse. They burnt their shrines into the heath and then the farms round "
                            "them. Find their three shrines on the Ashwold and tell me what they're doing.",
                  ("I'll find the shrines.", "@w_ok"), ("Not now.", "@bye")),
             ("End",), "w_ok:", ("Update.Attribute", "AshenHandQuest", "=1"),
             ("Display.Message", "Yellow", "Quest started: The Ashen Hand.")]),
        (1, [conv("Warden", "Three shrines: one west on the heath, one east, one north under the peaks.",
                  ("I'm on my way.", "@bye"))]),
        (2, [conv("Warden", "All three burning, and all three facing Ashpeak? Then it's not the farms they want.\\Their "
                            "priest holds the Cinder Fort, up in the peaks. Go up there and stop him, whatever he's "
                            "doing.", ("I'll storm the fort.", "@w_fort"), ("Later.", "@bye")),
             ("End",), "w_fort:", ("Update.Attribute", "AshenHandQuest", "=3"),
             ("Display.Message", "Yellow", "The Ashen Hand: storm the Cinder Fort and defeat the Ashen Priest.")]),
        (3, [conv("Warden", "The fort's north of here, in the peaks. Follow the road and mind the lava.",
                  ("I'm going.", "@bye"))]),
        (4, [(">Got.Item", "Ashen_Codex", "1", "@w_nobook"),
             ("Take.Item", "Ashen_Codex", "1"),
             ("Update.Attribute", "AshenHandQuest", "=5"),
             ("Give.Item", "Gold_Coin(s)", "300"), ("Give.Item", "Super_Potion", "3"),
             ("Update.Skill", "Strength", "+2"), ("Update.Skill", "Defence", "+2"),
             conv("Warden", "The priest is dead? And this is his codex...\\A song, page after page, to wake a dragon. "
                            "Ignaroth, under Ashpeak. They mean to wake it, and they're nearly there.\\This is beyond "
                            "Emberwatch. Take it to the court wizard on the Royal Isle, and quickly. And take this gold: "
                            "you've earned it.", ("I'll go to the wizard.", "@w_done")),
             "w_done:", ("Display.Message", "Yellow", "Quest complete: The Ashen Hand! You receive 300 gold, three super "
                                                      "potions and experience. The court wizard must hear of this."),
             ("End",), "w_nobook:",
             conv("Warden", "The priest had a book with him, always. Bring it to me.", ("I'll find it.", "@bye"))]),
    ], "The Cinder Fort is quiet. Now see the wizard about that dragon.")
    for k in (1, 2, 3):
        S["Ashen Shrine %d" % k] = [
            "// A burnt shrine of the Ashen Hand (The Ashen Hand). Generated by build_cinder.py",
            ("Get.Value", "ATTRIBUTE", "AshenHandQuest", "Variable.1$"),
            (">Conditional", "$Variable.1=1", "@end"),
            ("Get.Value", "ATTRIBUTE", "Shrine%dFound" % k, "Variable.2$"),
            (">Conditional", "$Variable.2=0", "@end"),
            ("Update.Attribute", "Shrine%dFound" % k, "=1"),
            ("Update.Attribute", "ShrinesFound", "+1"),
            ("Get.Value", "ATTRIBUTE", "ShrinesFound", "Variable.3$"),
            (">Conditional", "$Variable.3>=3", "@more"),
            ("Update.Attribute", "AshenHandQuest", "=2"),
            ("Display.Message", "Yellow", "The last shrine: like the others, its burnt hand points north, to Ashpeak. "
                                          "Report to the Warden in Emberwatch."),
            ("End",),
            "more:",
            ("Display.Message", "Yellow", "A burnt shrine of the Ashen Hand, its handprint pointing north to Ashpeak. "
                                          "Shrines found: $Variable.3 of 3."),
            "end:", ("End",)]
    S["Cinder Fort Gate"] = [
        "// The way into the Cinder Fort (The Ashen Hand). Generated by build_cinder.py",
        ("Get.Value", "ATTRIBUTE", "AshenHandQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@end"),
        ("Display.Message", "Red", "Chanting, and the smell of burning. In the yard, a priest in smouldering robes raises "
                                   "his hands to Ashpeak."),
        "end:", ("End",)]
    S["Kill Ashen_Priest"] = [
        "// The Ashen Priest falls (The Ashen Hand). Generated by build_cinder.py",
        ("Get.Value", "ATTRIBUTE", "AshenHandQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=3", "@end"),
        ("Update.Attribute", "AshenHandQuest", "=4"),
        ("Give.Item", "Ashen_Codex", "1"),
        ("Display.Message", "Yellow", "The Ashen Priest falls, and his codex drops from his hands. Take it to the "
                                      "Warden in Emberwatch."),
        "end:", ("End",)]
    S["Talk to Scout"] = talk("Scout", "PatrolQuest", [
        (0, [conv("Scout", "Three of my scouts went out on the Ashwold a week ago. The hounds got them, I'm sure of "
                           "it.\\They'd have their tags on them. Bring me three, so their families know.",
                  ("I'll bring the tags.", "@s_ok"), ("Not now.", "@bye")),
             ("End",), "s_ok:", ("Update.Attribute", "PatrolQuest", "=1"),
             ("Display.Message", "Yellow", "Quest started: The Lost Patrol.")]),
        (1, [(">Got.Item", "Scout_Tag", "3", "@s_notyet"),
             ("Take.Item", "Scout_Tag", "3"),
             ("Update.Attribute", "PatrolQuest", "=2"),
             ("Give.Item", "Gold_Coin(s)", "200"), ("Give.Item", "Yew_Bow", "1"), ("Give.Item", "Arrows", "100"),
             conv("Scout", "All three... thank you. Take my old bow. I can't look at it any more.",
                  ("Thank you.", "@s_done")),
             "s_done:", ("Display.Message", "Yellow", "Quest complete: The Lost Patrol! You receive 200 gold, a yew bow "
                                                      "and arrows."),
             ("End",), "s_notyet:",
             conv("Scout", "Three tags. The hounds roam the heath west and east of town.", ("I'll keep looking.", "@bye"))]),
    ], "The patrol can rest now. The heath's a little less cruel for it.")
    S["Talk to Wyrmsmith"] = [
        "// The Wyrmsmith of Wardhaven: the Dragonforge (CRAFT-Dragonforge). Generated by build_cinder.py",
        conv("Wyrmsmith", "Twelve years I've kept this forge hot, waiting for someone to bring me dragon scale.\\Ignaroth's "
                          "scales and mithril bars: I'll show you how they're worked. Nothing else on this earth will "
                          "turn its fire.", ("Show me the Dragonforge.", "@forge"), ("Goodbye.", "@bye")),
        ("End",),
        "forge:",
        ("Display.Item.Rack", "GENERAL", "Wyrmsmith", "CRAFT-Dragonforge", "@bye"),
        "bye:", ("End",)]
    S["Forge Wyrmsmith"] = S["Talk to Wyrmsmith"][:1] + [
        ("Display.Item.Rack", "GENERAL", "Wyrmsmith", "CRAFT-Dragonforge", "@bye"), "bye:", ("End",)]
    S["Forge Dragonforge"] = C.station_script("Forge", "Dragonforge", "CRAFT-Dragonforge", "Wyrmsmith")
    m, _, _ = local(*town_centre(TOWN))                     # arriving
    S[m] = ["// Arriving in Emberwatch. Generated by build_cinder.py",
            ("Display.Message", "Yellow", "Emberwatch, the last fort before the Cinderlands. Smoke on the wind."), ("End",)]
    m, _, _ = local(*SITES["Fort"])
    S[m] = ["// The Cinder Peaks. Generated by build_cinder.py",
            ("Display.Message", "Red", "The Cinder Peaks. The air shimmers over the lava, and somewhere above, men are "
                                       "chanting."), ("End",)]
    S["Examine Hero_Statue"] = [
        "// Wardhaven's statue of the dragon-slayer. Generated by build_cinder.py",
        ("Display.Message", "Yellow", "A gilt statue on a plinth. The words cut into it: \"$Player.Name, who slew "
                                      "Ignaroth under Ashpeak. Wardhaven remembers.\""), ("End",)]


# ------------------------------------------------------------------ the quests: main story, requirements, gates
def apply_requirements():
    """Every quest's Type, Chapter and Requires (REQUIREMENTS), its new first step (STAGE0) and markers (MARKERS)."""
    for name, keys in C.QUESTS:
        want = REQUIREMENTS.get(name, {})
        extra = [("Type", want.get("Type")), ("Chapter", want.get("Chapter")), ("Requires.Level", want.get("Level")),
                 ("Requires.Quests", want.get("Quests")), ("Requires.Skills", want.get("Skills"))]
        keys[:] = [(k, v) for k, v in keys if k not in {e[0] for e in extra}] + [(k, v) for k, v in extra if v]
        if name in STAGE0:
            keys[:] = [(k, STAGE0[name] if k == "Stage0" else v) for k, v in keys]
        for stage, where in MARKERS.get(name, {}).items():
            if not any(k == "Marker%d" % stage for k, _ in keys):
                keys.append(("Marker%d" % stage, where))


NOT_READY = {   # giver: (what they say while their quest is locked, your answer); the chat says exactly what it needs
    "King_Tyron": ("Another stranger off the Isle boats, wanting the King's ear? Hobgoblins are soldiers' work. Show me "
                   "you can get yourself to my kingdom first, then we'll talk.", "As you say, Your Majesty."),
    "Herbalist": ("Mind the jars, dear, mind the jars! A remedy? Oh, it's not a job for someone still green as my "
                  "sage. See a bit of the world first, and come and find me.", "I'll come back."),
    "Dwarf": ("Hah! My grudge is with things that bite back, beanpole. Get the King's hobgoblins seen to and some "
              "muscle on those arms, and then we'll talk.", "Fair enough."),
    "Beggar": ("Spare a coin? ...I lost something, out where it's not safe. You'd not last a night there, the state "
               "of you. Toughen up, then ask me again.", "I'll be back."),
    "Ranger": ("The Wildwood eats the careless. Prove yourself to the King, and come back with a steadier sword "
               "arm. Then I'll show you the trees.", "Understood."),
    "Shepherd": ("Wolves took three of my ewes this week. I'd ask you to help, but they'd have you just as quick. "
                 "Get some fight in you first.", "I'll be back."),
    "Witch": ("Hee hee. The bog lights want someone who knows their herbs and can hold their own. You're neither "
              "yet, dearie. Off you go.", "Charming."),
    "Captain": ("The road's no place for civilians while it's crawling with bandits. When you can swing a sword like "
                "you mean it, report back to me.", "Yes, Captain."),
    "Merchant": ("My caravan? Gone, and I'll not send a stranger after it. The Captain vouches for anyone who clears "
                 "the road of bandits. Earn that first.", "I'll talk to the Captain."),
    "Forgemaster": ("The cold up there splits stone, and the things in it split skulls. You'd freeze before you got "
                    "a hammer up. Harden yourself, then come back.", "I will."),
    "Hermit": ("You want to sit by my fire? Then you can keep it fed. Learn to swing an axe properly, and we'll "
               "talk.", "I'll go and chop some wood."),
    "Druid": ("The wood is sick, and the sickness began with the wolves on the moor. Deal with them first, and "
              "grow strong. What waits in the Withering Wood is worse.", "I'll see to the wolves."),
    "Gravekeeper": ("The Barrow King doesn't wake for just anyone. The dead still walk in the Withering Wood. Put "
                    "them to rest first, then come to me.", "I'll be back."),
    "Hob": ("Hob's not talkin' to strangers. Not while the lights is still in the bog. Ask the witch. Witch knows.",
            "...Right."),
    "Warden": ("Emberwatch has buried enough brave young fools this year. If the King trusts you, good. Come back "
               "when you can stand in front of a cultist and live.", "I'll be ready."),
    "Scout": ("The patrol went up past the Cinder Peaks. Nobody comes back from there at your strength. Train, and "
              "then I'll take you.", "I'll train."),
}
NOT_READY_ANY = ("You've a long road ahead of you before I'd ask this of you. Come back when you're stronger.",
                 "I'll be back.")


def gate_quest_starts():
    """Before each quest giver offers a quest with Requires, a >Quest.Can.Start: if the player can't take it on yet,
    the game says what it needs and the giver says to come back (the wizard goes on to his usual business)."""
    gated = 0
    for name, keys in C.QUESTS:
        k = dict(keys)
        attr, giver = k.get("Attribute"), k.get("Giver", "")
        if not attr or not any(key.startswith("Requires.") for key in k):
            continue
        for sname, steps in W.S.items():
            start = ("Update.Attribute", attr, "=1")
            if start not in steps or any(isinstance(s, tuple) and s[:2] == (">Quest.Can.Start", attr) for s in steps):
                continue
            i = steps.index(start)
            label = steps[i - 1] if i and isinstance(steps[i - 1], str) and steps[i - 1].endswith(":") else None
            at = i
            if label:
                offer = next((j for j in range(i - 1, -1, -1) if isinstance(steps[j], tuple) and
                              steps[j][0] == "Display.Conversation" and "@" + label[:-1] in steps[j]), None)
                if offer is not None:
                    at = offer
            target = "main" if "main:" in steps and sname == "Talk to Wizard" else "qn_%s" % attr
            steps.insert(at, (">Quest.Can.Start", attr, "@" + target))
            if target != "main":
                who = giver if giver and sname.startswith("Talk to") else "Notice"
                if sname.startswith("Talk to"):
                    line, answer = NOT_READY.get(sname[8:], NOT_READY_ANY)
                    steps += [target + ":", R.conv(sname[8:], line, (answer, "@" + target + "_end")),
                              target + "_end:", ("End",)]
                else:
                    steps += [target + ":", ("End",)]
            gated += 1
    return gated


# ------------------------------------------------------------------ the maps you've edited: patches (idempotent)
def cells_of(path):
    from common import read_lines, MAP_H
    lines = read_lines(path)
    while lines and lines[-1] == "":
        lines.pop()
    return [r.split(":") for r in lines[:MAP_H]], lines[MAP_H:]


def save_cells(path, cells, ents):
    from common import write_lines
    return write_lines(path, [":".join(r) for r in cells] + [e for e in ents if e.strip()])


def has_overlay(cell, kind):
    return "+%s(" % kind in cell


def set_decor(cell, decor):
    """The cell with decor as its Decor (any other decor replaced)."""
    parts = cell.split("+")
    parts = [p_ for p_ in parts if not p_.startswith("Decor(")]
    return "+".join([parts[0], "Decor(%s)" % decor] + parts[1:])


def ground(cell):
    """Just the ground: no decor (a tree, a rock cleared off)."""
    return "+".join(p_ for p_ in cell.split("+") if not p_.startswith("Decor("))


def bridge_patch():
    """The Heartwood bridge on 8,5,0: a path north from the clearing to the shore, planks over the water."""
    from common import p
    path = p("Maps", BRIDGE_MAP + ".txt")
    cells, ents = cells_of(path)
    x = BRIDGE_COL - 1
    for y in range(BRIDGE_FROM_ROW - 1, -1, -1):
        c = cells[y][x]
        base = c.split("+")[0]
        if base.startswith(("Water", "Sand_Water")):
            new = "Plank001"
        elif base in ("Sand001", "Plank001", "Dirt001"):
            new = ground(c)
        else:
            new = "Dirt001" + "".join("+" + q for q in ground(c).split("+")[1:])
        cells[y][x] = new
    return ["Maps\\%s.txt" % BRIDGE_MAP] if save_cells(path, cells, ents) else []


def bank_houses(cells, ents):
    """The banks on a map: [(front row, door x, x1, x2, roof cells)] (0-based) for each house with a Banker in it."""
    H, Wd = len(cells), len(cells[0])
    out = []
    for e in ents:
        f = e.split("\t")
        if len(f) < 4 or f[1] != "Banker":
            continue
        try:
            bx, by = int(float(f[2]) + 16) // 32, int(float(f[3]) + 28) // 32
        except ValueError:
            continue
        if not (0 <= bx < Wd and 0 <= by < H) or not has_overlay(cells[by][bx], "Roof"):
            continue
        seen, todo = set(), [(bx, by)]
        while todo:                                         # the roof over the banker
            x, y = todo.pop()
            if (x, y) in seen or not (0 <= x < Wd and 0 <= y < H) or not has_overlay(cells[y][x], "Roof"):
                continue
            seen.add((x, y))
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        y2 = max(y for x, y in seen if x == bx)
        x1, x2 = min(x for x, _ in seen), max(x for x, _ in seen)
        fy = y2 + 1
        if fy >= H:
            continue
        doors = [x for x in range(x1, x2 + 1) if cells[fy][x].split("+")[0].startswith("Door")]
        if not doors:
            continue
        out.append((fy, doors[0], x1, x2, seen))
    return out


def dress_bank_cells(cells, ents):
    """Every bank on the map: copper roof, columns either side of the door, the plaque over its sign. True if changed."""
    import re
    changed = False
    for fy, door, x1, x2, roof in bank_houses(cells, ents):
        for x, y in roof:
            new = re.sub(r"Roof\((Thatch|Shingle|Slate|Clay)_Roof(\d{3})\.", r"Roof(Copper_Roof\2.", cells[y][x])
            if new != cells[y][x]:
                cells[y][x], changed = new, True
        row = cells[fy]
        wall = lambda x: x1 <= x <= x2 and not row[x].split("+")[0].startswith("Door")
        sign = next((x for x in range(x1, x2 + 1) if "Decor(Bank_Plaque001)" in row[x]), None)    # (done before)
        if sign is None:
            sign = next((x for x in range(x1, x2 + 1) if re.search(r"(^|_|\()Sign\d{3}", row[x])), None)
        plaque = sign if sign is not None else next((x for x in (door - 2, door + 2, door - 3, door + 3) if wall(x)), None)
        cols = [x for x in (door - 1, door + 1) if wall(x) and x != plaque]
        cols += [x for x in (x1, x2) if wall(x) and x != plaque and x not in cols and abs(x - door) > 1]
        for x, d in [(x, "Bank_Column001") for x in cols] + ([(plaque, "Bank_Plaque001")] if plaque is not None else []):
            if not has_overlay(row[x], "Decor") or on_wall(row[x]):      # (over a window or a sign: it goes)
                row[x] = set_decor(row[x], d)
                changed = True
    return changed


def on_wall(cell):
    """Is the cell's decor a window, a sign, ivy (something on a wall that a bank's column or plaque goes over)?"""
    import re
    return bool(re.search(r"Decor\((\w+_Window|Sign|Ivy)\d{3}\)", cell))


def dress_banks():
    from common import p
    out = []
    for f in sorted(os.listdir(p("Maps"))):
        if not f.endswith(".txt"):
            continue
        path = p("Maps", f)
        cells, ents = cells_of(path)
        if any("\tBanker\t" in e for e in ents) and dress_bank_cells(cells, ents) and save_cells(path, cells, ents):
            out.append("Maps\\" + f)
    return out


# the towns that had a bank stall out in the open (map, near): stalls_indoors() puts their Banker in a house there
STALLS = [("1,1,0", (13, 14)), ("1,3,0", (12, 13)), ("2,4,0", (15, 18)), ("4,4,0", (16, 16))]
OPEN_GROUND = ("Grass001", "Dirt001", "Sand001", "Paving001", "Stone001", "Stone002", "Ash001", "Marble001",
               "Plank001", "Tile001")


def free(cells, x, y, taken):
    H, Wd = len(cells), len(cells[0])
    if not (1 <= x < Wd - 1 and 1 <= y < H - 1) or (x, y) in taken:
        return False
    c = cells[y][x]
    return c.split("+")[0] in OPEN_GROUND and not has_overlay(c, "Decor") and not has_overlay(c, "Roof")


INDOOR_FLOORS = ("Plank001", "Tile001", "Marble001", "Carpet001", "Carpet002", "Paving001", "Stone001", "Stone002")


def house_of(cells, x, y):
    """The roof cells over (x, y) (a house), or an empty set."""
    H, Wd = len(cells), len(cells[0])
    seen, todo = set(), [(x, y)]
    while todo:
        x, y = todo.pop()
        if (x, y) in seen or not (0 <= x < Wd and 0 <= y < H) or not has_overlay(cells[y][x], "Roof"):
            continue
        seen.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def taken_cells(ents):
    """The tiles where the map's people, things and triggers are."""
    taken = set()
    for e in ents:
        f = e.split("\t")
        try:
            if f[0] in ("Trigger", "Lock"):
                taken.add((int(f[1 if f[0] == "Lock" else 2]) - 1, int(f[2 if f[0] == "Lock" else 3]) - 1))
            elif len(f) >= 4:
                taken.add((int(float(f[2]) + 16) // 32, int(float(f[3]) + 28) // 32))
        except (ValueError, IndexError):
            pass
    return taken


def bank_spot(cells, roof, taken):
    """Where a Banker goes in a house: (score, x, y, counter) - at the back of the room, the counter in front of them
    and room in front of that for the player (counter False: no room for one, the Banker stands alone)."""
    def floor(x, y):
        c = cells[y][x] if 0 <= y < len(cells) and 0 <= x < len(cells[0]) else ""
        decor = [q for q in c.split("+")[1:] if q.startswith("Decor(")]
        return ((x, y) in roof and c.split("+")[0] in INDOOR_FLOORS and (x, y) not in taken and
                all(d.startswith("Decor(Rug") for d in decor))
    fy = max(y for _, y in roof) + 1
    doors = [x for x, _ in roof if fy < len(cells) and cells[fy][x].split("+")[0].startswith("Door")]
    door = doors[0] if doors else None
    best = None
    for x, y in roof:
        if (x, y) == (door, fy - 1) or not floor(x, y):
            continue                                        # (not in the doorway)
        if floor(x, y + 1) and floor(x, y + 2) and (x, y + 1) != (door, fy - 1):
            score, counter = 0, True
        elif floor(x, y + 1):
            score, counter = 100, False
        else:
            continue
        score += (0 if x == door else 10 + abs(x - door) if door is not None else 10) + y
        if best is None or score < best[0]:
            best = (score, x, y, counter)
    return best


def special_houses(cells, ents):
    """Roof cells of houses that mustn't become a bank: a locked door (Lock) or a trigger inside (a quest's house)."""
    out = set()
    for e in ents:
        f = e.split("\t")
        try:
            if f[0] == "Lock":
                x, y = int(f[1]) - 1, int(f[2]) - 1
                out |= house_of(cells, x, y - 1)            # (the lock is on the door; the house is behind it)
            elif f[0] == "Trigger":
                out |= house_of(cells, int(f[2]) - 1, int(f[3]) - 1)
        except (ValueError, IndexError):
            pass
    return out


# The Isle has one house, the beggar's (locked): its bank is a copy of it put up on the green, (from, to, size),
# below where a new player starts (Config.ini Start.X/Y)
ISLE_BANK = ("1,1,0", (17, 2), (8, 11), (5, 5))


def isle_bank_house():
    """The Isle's bank building: the beggar's brick house copied (walls, tiled floor, roof; not its furniture) onto
    open ground, its roof a group of its own. Done once (nothing changes if the copy's there)."""
    import re
    from common import p
    m, (fx, fy), (tx, ty), (w, h) = ISLE_BANK
    path = p("Maps", m + ".txt")
    cells, ents = cells_of(path)
    if has_overlay(cells[ty + 1][tx + 1], "Roof"):
        return []
    groups = [int(g) for r in cells for c in r for g in re.findall(r"Roof\(\w+?\.(\d+)\)", c)]
    group = "%02d" % (max(groups or [0]) + 1)
    for j in range(h):
        for i in range(w):
            src = cells[fy + j][fx + i]
            parts = [q for q in src.split("+") if not q.startswith("Decor(")]
            cells[ty + j][tx + i] = re.sub(r"(Roof\(\w+?\.)\d+\)", r"\g<1>%s)" % group, "+".join(parts))
    return ["Maps\\%s.txt" % m] if save_cells(path, cells, ents) else []


def stalls_indoors():
    """The bank stalls of STALLS (a marble counter and a Banker out on open ground) moved indoors: each map's stall
    cleared and its Banker put in a house there, behind the counter if there's room (a house nobody lives in first,
    then the nearest). dress_banks() then makes that house a bank. Does nothing on a map with a Banker indoors."""
    from common import p
    out = []
    for m, (nx, ny) in STALLS:
        path = p("Maps", m + ".txt")
        cells, ents = cells_of(path)
        changed = False
        for y, row in enumerate(cells):                     # the stall: its counter and its Banker out of doors
            for x, c in enumerate(row):
                if "Decor(Bank_Counter001)" in c and not has_overlay(c, "Roof"):
                    row[x], changed = ground(c), True
        keep, indoors = [], False
        for e in ents:
            f = e.split("\t")
            if len(f) >= 4 and f[0] == "NPC" and f[1] == "Banker":
                try:
                    bx, by = int(float(f[2]) + 16) // 32, int(float(f[3]) + 28) // 32
                except ValueError:
                    bx = by = -1
                c = cells[by][bx] if 0 <= by < len(cells) and 0 <= bx < len(cells[0]) else ""
                if has_overlay(c, "Roof") and c.split("+")[0] in INDOOR_FLOORS:     # (on a floor, not in a wall)
                    indoors = True
                else:
                    changed = True
                    continue
            keep.append(e)
        ents = keep
        if not indoors:
            taken = taken_cells(ents)
            houses, seen = [], special_houses(cells, ents)
            for y, row in enumerate(cells):
                for x, c in enumerate(row):
                    if has_overlay(c, "Roof") and (x, y) not in seen:
                        roof = house_of(cells, x, y)
                        seen |= roof
                        spot = bank_spot(cells, roof, taken)
                        if spot is not None:
                            lived_in = any(t in roof for t in taken)
                            cx = sum(x_ for x_, _ in roof) / len(roof)
                            cy = sum(y_ for _, y_ in roof) / len(roof)
                            houses.append(((lived_in, spot[0], abs(cx - (nx - 1)) + abs(cy - (ny - 1))), spot))
            if houses:
                _, (_, x, y, counter) = min(houses)
                if counter:
                    cells[y + 1][x] = set_decor(cells[y + 1][x], "Bank_Counter001")
                ents.append("NPC\tBanker\t%d\t%d\tAttitude=Good Stand=1" % (x * 32, y * 32))
                changed = True
        if changed and save_cells(path, cells, ents):
            out.append("Maps\\%s.txt" % m)
    return out


def wardhaven_patch():
    """Wardhaven's square: the Dragonforge with the Wyrmsmith beside it, the hero's statue and the dragon's skull."""
    from common import p
    import build_walled as WL
    m, sx, sy = WL.local(WL.CX, WL.CY)
    path = p("Maps", m + ".txt")
    cells, ents = cells_of(path)
    out = []
    if not any("\tWyrmsmith\t" in e for e in ents):
        taken = set()
        for e in ents:
            f = e.split("\t")
            try:
                taken.add((int(float(f[2]) + 16) // 32, int(float(f[3]) + 28) // 32))
            except (ValueError, IndexError):
                pass
        want = [(-3, -1, "Hero_Statue001"), (3, -1, "Dragon_Skull001")]
        for dx, dy, d in want:
            x, y = sx - 1 + dx, sy - 1 + dy
            for ox, oy in ((0, 0), (0, -1), (1, 0), (-1, 0), (0, 1), (2, 0), (-2, 0)):
                if free(cells, x + ox, y + oy, taken):
                    cells[y + oy][x + ox] = set_decor(cells[y + oy][x + ox], d)
                    taken.add((x + ox, y + oy))
                    break
        for ox, oy in ((0, 2), (1, 2), (-1, 2), (0, 3), (2, 2), (-2, 2), (0, -3)):
            x, y = sx - 1 + ox, sy - 1 + oy
            if free(cells, x, y, taken) and free(cells, x + 1, y, taken) and free(cells, x, y + 1, taken):
                ents.append("StaticObject\tDragonforge\t%d\t%d" % (x * 32, y * 32))
                ents.append("NPC\tWyrmsmith\t%d\t%d\tAttitude=Good Stand=1" % ((x + 1) * 32, y * 32))
                break
        if save_cells(path, cells, ents):
            out.append("Maps\\%s.txt" % m)
    return out


def patch_files():
    """The patches above, on the map files as they are (your edits kept): safe to run every build."""
    return bridge_patch() + isle_bank_house() + stalls_indoors() + dress_banks() + wardhaven_patch()


def make_art():
    import cinder_art
    return cinder_art.make_art()


# ------------------------------------------------------------------ hooks
def extend(world, content, regions):
    global W, C, R
    W, C, R = world, content, regions
    grid, roofs, busy, landing = build_grid()
    maps = make_maps(grid, roofs)
    maps.update(R.upper_maps(VILLAGES[TOWN]["houses"], GW, GH))
    data()
    populate(maps, grid, busy, landing)
    scripts()
    import build_eastreach
    build_eastreach.trader_scripts()        # again, now with Emberwatch's branch (TRADER_MAPS)
    W.MAPS.update(maps)
    W.SEAMLESS_MAPS.update(m for m in maps if m.endswith(",0"))
    W.S.update(R.S)
    W.EXTRA_STEPS.insert(0, make_art)
    W.EXTRA_STEPS.insert(0, decor_sets.make_art)
    W.EXTRA_STEPS.append(patch_files)
    W.EXTRA_STEPS.append(decor_sets.write_tile_sets)


def finish():
    """At the very end of build_content.extend: the dragon drops its scales, the quests' requirements and the gates."""
    drops = dict(C.ENTITIES.get("Dragon", []))
    if "Dragon_Scale" not in drops.get("Drops", ""):
        C.ENTITIES["Dragon"] = [(k, (v + " Dragon_Scale,4-7,100") if k == "Drops" else v)
                                for k, v in C.ENTITIES.get("Dragon", [])]
    apply_requirements()
    return gate_quest_starts()
