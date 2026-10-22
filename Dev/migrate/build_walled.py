"""Wardhaven: a walled town on its own island (maps 4,2,0 to 5,3,0), over a bridge from the end of the farm road east of
Ashford (3,3,0). Its gates have been barred since the dragon came, and they stay shut until the Dragon of Ashpeak quest
is complete (DragonQuest 4): the gate is a Lock with that condition, and City_Gate001's Tiles.ini Unlocked.Tile makes
the game draw it open (City_Gate002) once it is.

Not run on its own: build_content.extend() calls extend() here after build_eastreach (whose Trader and Settler scripts
it adds a branch to) and before build_travel (so the town gets a waystone) and the scenery pass, so
`python -I "Dev\\migrate\\build_world.py"` builds it. Deterministic: the same maps every time.

  * The island: meadows and copses, a sandy shore, nothing that bites.
  * The town: villages.build() inside a ring of city walls (City_Wall001-005, two tiles tall east-west), towers at the
    corners, half way along and either side of the one gate, in the south wall. Inside: the bank, the Trader's shop
    (dragon-slayer's wares), a smithy, the Settler and a waystone.
  * Outside the gate: a guard (the Talk to Guard script sends the talk here: Wardhaven Guard) and a notice by the bridge.
"""
import math
import random

W = C = R = None        # build_world, build_content, build_regions

MX0, MX1, MY0, MY1 = 4, 5, 2, 3
GW, GH = 25, 21
GX0, GX1, GY0, GY1 = MX0 * GW, (MX1 + 1) * GW - 1, MY0 * GH, (MY1 + 1) * GH - 1
FROM_MAP, FROM_ROW = "3,3,0", 12          # the farm road east of Ashford ends at the sea on this row: the bridge goes on
BRIDGE_Y = 3 * GH + FROM_ROW - 1           # (world row)
TOWN = "Wardhaven"
CX, CY = 127, 60                           # the middle of the town square (world tiles)
HALF_W, HALF_H = 14, 12                    # the walls: CX +- HALF_W, CY +- HALF_H
GATE = (CX, CY + HALF_H)                   # the gates, and over them the arch (both have a Lock)
GATE_TOP = (CX, CY + HALF_H - 1)
CONDITION = "$Attr.DragonQuest>=4"
TOWNS = {TOWN: (CX // GW, CY // GH, None, "SHOP-Wardhaven",
                "WARDHAVEN\\Safe behind its walls since the dragon came.\\The bridge west goes to Ashford's farms.")}
SETTLER_LINES = {TOWN: "Twelve years behind these walls, and now Ignaroth is dead! They say it was you. "
                       "Drinks are on the house at every table in Wardhaven."}
VILLAGES = {}
TRADER_MAPS = []        # the maps the Trader and the Settler stand on (their scripts branch on the map)
LAND = {"Grass001", "Sand001", "Dirt001", "Plank001", "Tall_Grass001"}


def town_centre(name):
    return CX, CY


def local(gx, gy):
    mx, my = gx // GW, gy // GH
    return "%d,%d,0" % (mx, my), gx - mx * GW + 1, gy - my * GH + 1


def coast(gx, gy):
    """Tiles from the sea (under 2.2 sea, under 4.2 beach): the block's edge with rounded corners, pushed in and out by
    noise; the town, its walls and the road to the bridge kept on land."""
    sides = [gx - GX0, GX1 - gx, gy - GY0, GY1 - gy]
    if min(sides) < 1:
        return 0
    d = min(sides)
    rr = 22.0
    for a, b in ((gx - GX0, gy - GY0), (GX1 - gx, gy - GY0), (gx - GX0, GY1 - gy), (GX1 - gx, GY1 - gy)):
        if a < rr and b < rr:
            d = min(d, rr - math.hypot(rr - a, rr - b))
    d += 22 * (R.fbm(gx, gy, 11, 901) - 0.5) + 8 * (R.fbm(gx, gy, 5, 903) - 0.5) - 3
    out = max(abs(gx - CX) - HALF_W - 2, abs(gy - CY) - HALF_H - 2, 0)
    d = max(d, 7 - 1.8 * out)
    road = 0 if GX0 + 7 <= gx <= CX + 2 and abs(gy - BRIDGE_Y) <= 1 else 99     # (west of it, the bridge)
    return max(d, 6 - road)


def base_tile(gx, gy):
    c = coast(gx, gy)
    if c < 2.2:
        return "Water001"
    if c < 4.2:
        return "Sand001"
    r = R.h01("ward", gx, gy)
    if R.fbm(gx, gy, 7, 902) > 0.63 and r < 0.6:
        return ("Tree001", "Tree002", "Oak_Tree001", "Tree001")[int(r * 400) % 4]
    if r < 0.006:
        return "Herb_Patch001"
    if r < 0.012:
        return "Berry_Bush001"
    return "Grass001"


def build_grid():
    import villages
    grid = {(gx, gy): base_tile(gx, gy) for gy in range(GY0, GY1 + 1) for gx in range(GX0, GX1 + 1)}
    R.smooth_coast(grid)
    busy = set()
    x0, x1, y0, y1 = CX - HALF_W, CX + HALF_W, CY - HALF_H, CY + HALF_H
    for gy in range(y0 - 1, y1 + 2):                       # inside the walls (and a step round them): open ground
        for gx in range(x0 - 1, x1 + 2):
            grid[(gx, gy)] = "Grass001"
    v = villages.build(grid, busy, CX, CY, 950, "moor", "Grass001", lambda gx, gy: coast(gx, gy) < 4.2, GW, GH,
                       {"Grass001", "Tall_Grass001", "Weed001"}, reach=(HALF_W - 2, HALF_H - 3), count=(7, 9))
    VILLAGES[TOWN] = v
    roofs, groups = [], {}
    for rx1, ry1, rx2, ry2, material in v["roofs"]:
        m = (rx1 // GW, ry1 // GH)
        groups[m] = groups.get(m, 0) + 1
        roofs.append((rx1, ry1, rx2, ry2, groups[m], material))
    # the walls: the north and south ones two tiles tall (battlements over the face), the east and west ones one wide;
    # towers at the corners, half way along each side and either side of the gate
    for gx in range(x0, x1 + 1):
        for gy in (y0, y1 - 1):
            grid[(gx, gy)] = "City_Wall001"
            grid[(gx, gy + 1)] = "City_Wall004"
    for gy in range(y0 + 2, y1 - 1):
        for gx in (x0, x1):
            grid[(gx, gy)] = "City_Wall002"
    for gx, gy in ((x0, y0), (x1, y0), (x0, y1 - 1), (x1, y1 - 1), (GATE[0] - 1, GATE[1] - 1), (GATE[0] + 1, GATE[1] - 1),
                   (x0, CY), (x1, CY), (CX - 7, y0), (CX + 7, y0), (CX - 7, y1 - 1), (CX + 7, y1 - 1)):
        grid[(gx, gy)] = "City_Wall003"
        grid[(gx, gy + 1)] = "City_Wall005"
    grid[GATE_TOP] = "City_Gate003"
    grid[GATE] = "City_Gate001"
    busy.update((gx, gy) for gx in range(x0 - 1, x1 + 2) for gy in range(y0 - 1, y1 + 2)
                if gx in (x0 - 1, x0, x1, x1 + 1) or gy in (y0 - 1, y0, y0 + 1, y1 - 1, y1, y1 + 1))
    # in through the gate to the south street, and out of it down to the road
    for gy in range(GATE_TOP[1] - 2, GATE_TOP[1]):
        if grid[(CX, gy)] not in villages.HOUSE_TILES:
            grid[(CX, gy)] = "Dirt001"
    # the bridge: planks east from the end of the farm road to the first dry land, then the road to the gate
    x = GX0
    while grid[(x, BRIDGE_Y)] not in LAND or grid[(x + 1, BRIDGE_Y)] not in LAND:
        grid[(x, BRIDGE_Y)] = "Plank001"
        busy.add((x, BRIDGE_Y))
        x += 1
    landing = (x, BRIDGE_Y)
    rng = random.Random(951)
    road = villages.winding(landing, (CX, BRIDGE_Y), 1.6, rng) + [(CX, gy) for gy in range(GATE[1] + 1, BRIDGE_Y)]
    for c in road:
        if grid.get(c) not in villages.HOUSE_TILES and not grid[c].startswith("City_"):
            grid[c] = "Plank001" if grid[c].startswith("Water") else "Dirt001"
            busy.add(c)
            for n in ((c[0], c[1] - 1), (c[0], c[1] + 1)):         # the verges
                if grid.get(n) in ("Tree001", "Tree002", "Oak_Tree001", "Berry_Bush001", "Herb_Patch001"):
                    grid[n] = "Grass001"
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
            maps["%d,%d,0" % (mx, my)] = dict(rows=rows, roofs=mroofs, entities=[], triggers=[], locks=[])
    return maps


def populate(maps, grid, landing):
    import build_scenery
    options = {}

    def add_npc(name, gx, gy, opts=None):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(W.npc("GoodNPC", name, x, y))
        if opts:
            options.setdefault(m, {})[(name, x, y)] = opts
        return m

    def add(fn, name, gx, gy, *rest):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(fn(name, x, y, *rest))
        return m, x, y

    houses = VILLAGES[TOWN]["houses"]
    TRADER_MAPS[:] = []
    TRADER_MAPS.append(add_npc("Trader", *houses[1]["inside"]))
    add_npc("Banker", *houses[0]["inside"])
    add(W.obj, "Anvil", *houses[2]["benches"][0])
    add(W.obj, "Furnace", *houses[2]["benches"][1])
    _, sx, sy = local(CX, CY)
    TRADER_MAPS.append(add_npc("Settler", CX + 3, CY + 2, "Zone=%d,%d,%d,%d" % (sx, sy - 2, sx + 4, sy + 2)))
    m, x, y = add(W.obj, "Notice", CX + 2, CY - 2)
    R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice", TOWNS[TOWN][4], "Okay", "@end"),
                                          "end:", ("End",)]
    # the gate: locked until the dragon is dead; a guard on the road outside it
    for cell in (GATE_TOP, GATE):
        m, x, y = local(*cell)
        maps[m]["locks"].append((x, y, CONDITION, "The gates of Wardhaven are barred. \"Not while the dragon lives!\" "
                                                  "a guard shouts down from the wall."))
    add_npc("Guard", GATE[0] + 2, GATE[1] + 2, "Stand=1")
    # a notice where the bridge comes ashore
    nx, ny = landing[0] + 1, landing[1] - 2
    while grid.get((nx, ny)) not in ("Grass001", "Sand001") and nx < landing[0] + 8:
        nx += 1
    m, x, y = add(W.obj, "Notice", nx, ny)
    R.S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice",
        "WARDHAVEN\\East: the walled town. Its gates have been barred since Ignaroth the dragon came to Ashpeak."
        "\\They open for no one while the dragon lives.", "Okay", "@end"), "end:", ("End",)]
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            name = "%d,%d,0" % (mx, my)
            build_scenery.SCATTER[name] = (70, 8, 6)
            build_scenery.WILDLIFE[name] = [("BadNPC", "Rabbit", 1), ("GoodNPC", "Butterfly", 1)]
    for m, opts in options.items():
        C.NPC_OPTIONS.setdefault(m, {}).update(opts)


def data():
    C.NEW_SHOPS["SHOP-Wardhaven"] = ("1.3", "0.8", ["Mithril_Sword,1", "Mithril_Platebody,1", "Mithril_Shield,1",
                                                    "Yew_Bow,2", "Yew_Staff,1", "Arrows,300", "Mega_Potion,3",
                                                    "Super_Potion,6", "Fire_Storm_Scroll,4", "Lightning_Scroll,4",
                                                    "Meat_Pie,10"])


def scripts():
    conv = R.conv
    R.S["Wardhaven Guard"] = [
        "// The guard at Wardhaven's gate (Talk to Guard comes here on its maps). Generated by build_walled.py",
        (">Conditional", CONDITION, "@shut"),
        conv("Guard", "The dragon-slayer! Welcome to Wardhaven. The gates are open, and they're staying open.",
             ("Thank you.", "@bye")),
        ("End",),
        "shut:",
        conv("Guard", "Halt! Wardhaven's gates have been barred since Ignaroth came to Ashpeak, and they stay barred while "
                      "it lives.\\Kill the dragon, and the whole town will open its doors to you. Until then: off you go.",
             ("Who could kill a dragon?", "@who"), ("Goodbye.", "@bye")),
        ("End",),
        "who:",
        conv("Guard", "Ask the court wizard at the top of the palace tower, on the Royal Isle. They say he only talks of it to proven heroes.",
             ("I'll ask him.", "@bye")),
        "bye:", ("End",)]


def open_bridge():
    """The farm road east of Ashford (3,3,0) runs on over the sea: its last cell, in the east column, becomes planks."""
    rows = W.MAPS[FROM_MAP]["rows"]
    row = rows[FROM_ROW - 1]
    assert W.LEGEND[row[-1]] == "Water001" and W.LEGEND[row[-2]] == "Dirt001", (row[-2:],)
    rows[FROM_ROW - 1] = row[:-1] + "p"
    W.MAPS[FROM_MAP]["entities"].append(W.obj("Notice", 23, FROM_ROW - 1))
    W.S[W.notice_script_name(FROM_MAP, 23, FROM_ROW - 1)] = [("Display.Conversation", "Notice",
        "EAST: the bridge to Wardhaven\\(The town's gates are barred while the dragon lives.)", "Okay", "@end"),
        "end:", ("End",)]


def extend(world, content, regions):
    global W, C, R
    W, C, R = world, content, regions
    open_bridge()
    grid, roofs, busy, landing = build_grid()
    maps = make_maps(grid, roofs)
    maps.update(R.upper_maps(VILLAGES[TOWN]["houses"], GW, GH))
    data()
    populate(maps, grid, landing)
    scripts()
    import build_eastreach
    build_eastreach.trader_scripts()        # again, now with Wardhaven's branch (TRADER_MAPS)
    W.MAPS.update(maps)
    W.SEAMLESS_MAPS.update(m for m in maps if m.endswith(",0"))
    W.S.update(R.S)
