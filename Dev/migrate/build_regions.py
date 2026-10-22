"""The Wildlands: 36 generated maps (0,5,0 to 5,10,0) south of the Southlands, their towns, roads, monsters and quests.

Not run on its own: build_content.extend() calls extend() here (before build_scenery, so the new maps get scenery and
wildlife too), so `python -I "Dev\\migrate\\build_world.py"` builds it. Deterministic: the same maps every time.

How the maps are made
  * Every tile comes from functions of its WORLD tile (gx = map x * 25 + tile x, gy = map y * 21 + tile y), so the maps
    join up at every seam. Smooth value noise (fbm) warps the borders between the six lands:
        north  (maps y 5-6):   the Wildwood (x 0-2)       Greymoor (x 3-5)
        middle (maps y 7-8):   the Saltmarsh (x 0-2)      the Redrock hills (x 3-5)
        south  (maps y 9-10):  the Sunscar Desert (x 0-2) Frostpeak (x 3-5)
  * The sea all round (sand or ice on the shore), except the north edge of maps x 1-3, which meets the Southlands'
    forest (and the road from Tyron's Keep, 2,4,0, opened here).
  * A river from the Wildwood through the Saltmarsh to the west coast.
  * TOWNS: four houses round a square (walls, plank floors, a door, a roof), a quest giver, a Trader, Settlers, a notice.
  * ROADS between the towns (winding, 4-connected so they can always be walked, bridges over water, cleared verges), and
    footpaths out to the quest SITES.
  * Monsters suited to each land, kept to their area with Zone/Chase options.

The quests (QUESTS, Data\\Quests.ini) have several stages each; their scripts are below (S).
"""
import build_places as PL
import math
import zlib

W = C = None        # the build_world and build_content modules (set by extend)

MX0, MX1, MY0, MY1 = 0, 5, 5, 10        # the maps of the Wildlands
GW, GH = 25, 21                         # tiles per map
GX1, GY0, GY1 = (MX1 + 1) * GW - 1, MY0 * GH, (MY1 + 1) * GH - 1

# Towns: name -> (map x, map y, quest giver, its quest attribute, Trader's rack, notice text)
TOWNS = {
    "Oakhollow": (1, 6, "Ranger", "SHOP-Oakhollow",
                  "OAKHOLLOW\\A woodcutters' village in the Wildwood.\\North: Tyron's Keep. East: Moorcross. South: Fenwick."),
    "Moorcross": (3, 6, "Shepherd", "SHOP-Moorcross",
                  "MOORCROSS\\Sheep, wind and wolves on Greymoor.\\West: Oakhollow. South: Highwatch."),
    "Fenwick": (2, 8, "Witch", "SHOP-Fenwick",
                "FENWICK\\On stilts above the Saltmarsh. Mind the bog lights.\\North: Oakhollow. East: Highwatch. South: Dunerest."),
    "Highwatch": (4, 8, "Captain", "SHOP-Highwatch",
                  "HIGHWATCH\\The hill fort on the Redrock road. Bank inside.\\North: Moorcross. West: Fenwick. South: Frosthold."),
    "Dunerest": (1, 10, "Merchant", "SHOP-Dunerest",
                 "DUNEREST\\The last well before the Sunscar Desert.\\North: Fenwick. East: Frosthold."),
    "Frosthold": (4, 10, "Forgemaster", "SHOP-Frosthold",
                  "FROSTHOLD\\A forge town under Frostpeak.\\North: Highwatch. West: Dunerest."),
}
TOWN_TILE = (13, 11)        # the square's centre tile in each town's map (1-based), unless TOWN_TILE_AT says
# Each town somewhere different in its map, so no two line up; the southern towns sit back from the coast
TOWN_TILE_AT = {"Oakhollow": (10, 12), "Moorcross": (16, 9), "Fenwick": (7, 9), "Highwatch": (11, 10),
                "Dunerest": (12, 6), "Frosthold": (16, 9)}
VILLAGES = {}               # town -> villages.build()'s layout (its houses and streets), made by build_grid
HOUSE_GROUND = {"Grass001", "Sand001", "Snow001", "Marsh001", "Weed001", "Tall_Grass001", "Plank001"}   # (Fenwick: on stilts)


def town_tile(name):
    return TOWN_TILE_AT.get(name, TOWN_TILE)
ROADS = [("Keep", "Oakhollow"), ("Keep", "Moorcross"), ("Oakhollow", "Moorcross"), ("Oakhollow", "Fenwick"),
         ("Moorcross", "Highwatch"), ("Fenwick", "Highwatch"), ("Fenwick", "Dunerest"), ("Highwatch", "Frosthold"),
         ("Dunerest", "Frosthold")]
KEEP_GATE = (2 * GW + 12, GY0)          # world tile where the road from Tyron's Keep comes in (column 13 of 2,5,0)

# Quest sites: name -> (world x, world y, the road point its footpath joins)
SITES = {
    "WatchStone1": (2 * GW + 6, 5 * GH + 7),            # by the north road (2,5,0)
    "WatchStone2": (0 * GW + 18, 6 * GH + 6),           # the western woods (0,6,0)
    "WatchStone3": (1 * GW + 14, 5 * GH + 16),          # east of the river (1,5,0)
    "SpiderNest": (0 * GW + 19, 5 * GH + 13),           # the deep woods (0,5,0)
    "WolfDen": (5 * GW + 12, 6 * GH + 8),               # the eastern moor (5,6,0)
    "BanditCamp": (5 * GW + 12, 8 * GH + 10),           # the eastern hills (5,8,0)
    "CaravanWreck": (0 * GW + 13, 10 * GH + 6),         # the western desert (0,10,0)
    "TrollLair": (5 * GW + 12, 9 * GH + 12),            # a frozen lake under Frostpeak (5,9,0)
    "FrostCave": (4 * GW + 19, 9 * GH + 8),             # the way down to the Frostpeak Caverns (4,9,0 -> 4,9,-1)
}
RIVER = [(1 * GW + 18, 5 * GH + 2), (1 * GW + 8, 5 * GH + 14), (1 * GW + 2, 6 * GH + 10), (0 * GW + 20, 7 * GH + 6),
         (0 * GW + 10, 7 * GH + 16), (0, 8 * GH + 3)]

LAND = {"Grass001", "Sand001", "Snow001", "Ice001", "Marsh001", "Dirt001", "Plank001", "Weed001", "Bog_Myrtle002"}
OPEN = "1" * 49
BIG = "1111111" "1000001" "1000001" "1000001" "1000001" "1000001" "1111111"
TRUNK = "1111111" "1111111" "1111111" "1100011" "1100011" "1100011" "1111111"
REEDS = OPEN


# ------------------------------------------------------------------ noise
def h01(*parts):
    return (zlib.crc32(":".join(str(v) for v in parts).encode()) % 100000) / 100000.0


def vnoise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = h01(seed, ix, iy), h01(seed, ix + 1, iy)
    c, d = h01(seed, ix, iy + 1), h01(seed, ix + 1, iy + 1)
    return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy


def fbm(x, y, scale, seed):
    return 0.65 * vnoise(x / scale, y / scale, seed) + 0.35 * vnoise(x / (scale * 0.45), y / (scale * 0.45), seed + 99)


def land_of(gx, gy):
    wx = gx + 34 * (fbm(gx, gy, 22, 1) - 0.5)
    wy = gy + 30 * (fbm(gx, gy, 22, 2) - 0.5)
    col = 0 if wx < 3 * GW else 1
    band = min(2, max(0, int((wy - GY0) // (2 * GH))))
    return [["wood", "moor"], ["marsh", "hills"], ["desert", "snow"]][band][col]


def coast(gx, gy):
    """How far (in tiles) world tile gx,gy is from the sea round the Wildlands: under 2.2 is sea, under 4.2 beach.
    The outline is the edge of the six-map block with its corners rounded right off, pushed in and out by big, slow
    noise (bays and headlands up to ~9 tiles deep) and a little fine noise; towns and quest sites are kept on land."""
    north_open = GW <= gx < 3 * GW + 15                 # joined to the Southlands (3,4,0 is sea from its column 16)
    sides = [gx, GX1 - gx, GY1 - gy] + ([] if north_open else [gy - GY0])
    d = min(sides)
    R = 42.0                                            # rounded corners
    dn = 999 if north_open else gy - GY0
    for a, b in ((gx, dn), (GX1 - gx, dn), (gx, GY1 - gy), (GX1 - gx, GY1 - gy)):
        if a < R and b < R:
            d = min(d, R - math.hypot(R - a, R - b))
    d += 46 * (fbm(gx, gy, 24, 3) - 0.5) + 9 * (fbm(gx, gy, 7, 31) - 0.5) - 5
    if min(sides) < 1:                                  # the outermost row is always sea (it meets the sea maps round)
        return 0
    for t in TOWNS:                                     # towns and quest sites stand on solid ground (fading out
        cx, cy = town_centre(t)                         # round them, so they don't make square headlands)
        d = max(d, 7 - 0.7 * max(0.0, math.hypot((gx - cx) / 1.2, gy - cy) - 11))
    for sx, sy in SITES.values():
        d = max(d, 6 - 0.7 * max(0.0, math.hypot(gx - sx, gy - sy) - 5))
    return d


# ------------------------------------------------------------------ the terrain
def base_tile(gx, gy):
    land = land_of(gx, gy)
    c = coast(gx, gy)
    if c < 2.2:
        return "Water001"
    if c < 4.2:
        return "Snow001" if land == "snow" else "Sand001"
    if GW <= gx < 4 * GW and gy - GY0 < 3 + 2 * fbm(gx, gy, 5, 4) and not (3 * GW + 15 <= gx):
        return "Forest001"                              # the Southlands' forest edge, carried on
    r = h01("cell", gx, gy)
    if land == "wood":
        n = fbm(gx, gy, 9, 5)
        if n > 0.64:
            return "Forest001"
        if n > 0.47:
            if r < 0.30:
                return "Tree001"
            if r < 0.50:
                return "Tree002"
            if r < 0.58:
                return "Oak_Tree001"
            if r < 0.61 and n > 0.6:
                return "Yew_Tree001"
        return "Grass001"
    if land == "moor":
        if fbm(gx, gy, 10, 6) > 0.76:
            return "Water001"
        if fbm(gx, gy, 6, 7) > 0.72 and r < 0.5:
            return "Rock001"
        if r < 0.015:
            return "Stone001"
        return "Grass001"
    if land == "marsh":
        m = fbm(gx, gy, 7, 8)
        if m > 0.63:
            return "Water001"
        if m > 0.55:
            return "Reeds001"
        if fbm(gx, gy, 12, 9) > 0.66:
            return "Willow_Tree001" if r < 0.12 else "Grass001"
        if r < 0.025:
            return "Bog_Myrtle001"
        if r < 0.05:
            return "Willow_Tree001"
        return "Marsh001"
    if land == "hills":
        if fbm(gx, gy, 6, 10) > 0.7 and r < 0.6:
            return "Rock001"
        if fbm(gx, gy, 9, 11) > 0.64:
            return "Dirt001"
        if r < 0.006:
            return "Coal_Rock001"
        if r < 0.010:
            return "Ore_Rock001"
        if r < 0.012:
            return "Silver_Rock001"
        if r < 0.03:
            return "Tree001"
        return "Grass001"
    if land == "desert":
        o = fbm(gx, gy, 10, 12)
        if o > 0.8:
            return "Water001"                           # an oasis
        if o > 0.75:
            return "Grass001"
        if fbm(gx, gy, 6, 13) > 0.73 and r < 0.6:
            return "Desert_Rock001"
        if r < 0.025:
            return "Cactus001"
        if r < 0.028:
            return "Gold_Rock001"
        return "Sand001"
    # snow
    if fbm(gx, gy, 11, 14) > 0.72:
        return "Ice001"                                 # a frozen lake
    n = fbm(gx, gy, 8, 15)
    if n > 0.64 and r < 0.75:
        return "Snow_Pine001"
    if fbm(gx, gy, 6, 16) > 0.72 and r < 0.5:
        return "Snow_Rock001"
    if r < 0.03:
        return "Snow_Pine001"
    if r < 0.034:
        return "Mithril_Rock001"
    return "Snow001"


def ground_for(gx, gy):
    """The plain walkable ground of the land at gx,gy (what roads' verges, towns and clearings are made of)."""
    return {"wood": "Grass001", "moor": "Grass001", "marsh": "Marsh001", "hills": "Grass001", "desert": "Sand001",
            "snow": "Snow001"}[land_of(gx, gy)]


# ------------------------------------------------------------------ the world grid
def town_centre(name):
    mx, my = TOWNS[name][0], TOWNS[name][1]
    tx, ty = town_tile(name)
    return mx * GW + tx - 1, my * GH + ty - 1


def build_grid():
    """World grid {(gx, gy): tile} for the whole Wildlands, plus roofs, the cells nothing else may be put on (busy)."""
    grid = {}
    for gy in range(GY0, GY1 + 1):
        for gx in range(0, GX1 + 1):
            grid[(gx, gy)] = base_tile(gx, gy)
    smooth_coast(grid)
    busy = set()

    def line(a, b, wobble, seed):
        """A winding 4-connected line of world tiles from a to b."""
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

    # the river
    for k, (a, b) in enumerate(zip(RIVER, RIVER[1:])):
        for (x, y) in line(a, b, 4, 70 + k):
            for dx in (0, 1):
                if (x + dx, y) in grid:
                    grid[(x + dx, y)] = "Water001"
                    for ex, ey in ((x + dx, y - 1), (x + dx, y + 1), (x + dx - 1, y), (x + dx + 1, y)):
                        if grid.get((ex, ey)) in ("Forest001", "Tree001", "Tree002", "Yew_Tree001") and h01("bank", ex, ey) < 0.6:
                            grid[(ex, ey)] = "Willow_Tree001" if h01("w", ex, ey) < 0.3 else "Grass001"

    # towns: villages.py lays each one out (a clearing, a square, winding streets, houses of different kinds)
    import villages
    roofs = []
    groups = {}
    site_cells = {(sx + dx, sy + dy) for sx, sy in SITES.values() for dx in range(-4, 5) for dy in range(-4, 5)}
    for k, name in enumerate(TOWNS):
        cx, cy = town_centre(name)
        v = villages.build(grid, busy, cx, cy, 500 + k, land_of(cx, cy), ground_for(cx, cy),
                           lambda gx, gy: coast(gx, gy) < 4.2, GW, GH, HOUSE_GROUND, keep_out=site_cells)
        VILLAGES[name] = v
        for x1, y1, x2, y2, material in v["roofs"]:
            m = (x1 // GW, y1 // GH)
            groups[m] = groups.get(m, 0) + 1
            roofs.append((x1, y1, x2, y2, groups[m], material))

    # quest sites: a clearing round each
    for name, (sx, sy) in SITES.items():
        for gy in range(sy - 3, sy + 4):
            for gx in range(sx - 3, sx + 4):
                if (gx, gy) in grid:
                    grid[(gx, gy)] = "Ice001" if name == "TrollLair" else ground_for(sx, sy)
                busy.add((gx, gy))

    # roads, then footpaths to the sites (verges cleared, bridges over water)
    def gate(name, toward):
        if name == "Keep":                  # the roads fan out below the straight way in through the forest
            return (KEEP_GATE[0], KEEP_GATE[1] + 3)
        cx, cy = town_centre(name)
        tx, ty = toward
        if abs(tx - cx) > abs(ty - cy):
            return (cx + (11 if tx > cx else -11), cy)
        return (cx, cy + (9 if ty > cy else -9))

    def lay(cells, verge):
        for (x, y) in cells:
            t = grid.get((x, y))
            if t is None or t in villages.HOUSE_TILES:
                continue
            grid[(x, y)] = "Plank001" if t in ("Water001", "Reeds001") else "Dirt001"
            if verge:
                for ex, ey in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if grid.get((ex, ey)) not in villages.HOUSE_TILES | {None, "Water001", "Dirt001", "Reeds001"} \
                            and grid[(ex, ey)] not in LAND:
                        grid[(ex, ey)] = ground_for(ex, ey)
            busy.add((x, y))

    centre = {n: town_centre(n) for n in TOWNS}
    centre["Keep"] = KEEP_GATE
    for k, (a, b) in enumerate(ROADS):
        ga, gb = gate(a, centre[b]), gate(b, centre[a])
        lay(line(ga, gb, 5, 200 + k), True)
    for k, (name, (sx, sy)) in enumerate(sorted(SITES.items())):
        # the nearest road tile
        best = min((p for p, t in grid.items() if t == "Dirt001" and p not in
                    {(gx, gy) for gx in range(sx - 4, sx + 5) for gy in range(sy - 4, sy + 5)}),
                   key=lambda p: abs(p[0] - sx) + abs(p[1] - sy))
        lay(line((sx, sy + 3), best, 2, 300 + k), True)
    # the gate from the Keep: the road runs straight in through the forest
    for gy in range(GY0, GY0 + 4):
        lay([(KEEP_GATE[0], gy)], True)
    for gy in range(GY0 + 3, GY0 + 6):                      # a clearing beside it for the notice
        for gx in range(KEEP_GATE[0] + 1, KEEP_GATE[0] + 4):
            if grid[(gx, gy)] not in ("Dirt001", "Plank001"):
                grid[(gx, gy)] = "Grass001"
    # the edge with the Southlands stays forest, but for the gate (a road's verge mustn't open another way north)
    # (the road's grass verges, two each side, meet the ones open_keep_road makes in the Keep's map)
    for gx in range(0, GX1 + 1):
        if abs(gx - KEEP_GATE[0]) in (1, 2):
            grid[(gx, GY0)] = "Grass001"
        elif gx != KEEP_GATE[0] and grid.get((gx, GY0)) in ("Grass001", "Dirt001", "Weed001", "Tall_Grass001"):
            grid[(gx, GY0)] = "Forest001"
    smooth_shores(grid)
    return grid, roofs, busy


# Diagonal shore pieces, as on the Isle: a sea cell in the corner of a step in the coast (land on two sides that meet,
# and on the corner between them; sea on the other two) becomes the piece with land in that corner. The grass pieces
# are Water002-009; region_tiles.py shore() draws them, and the same ones on sand and snow, to join the edge blending.
SHORE_CORNER = {("N", "E"): 2, ("N", "W"): 5, ("S", "W"): 6, ("S", "E"): 8}
# The small pieces (land in only a little of the corner) where the coast steps two tiles at once, as the Isle has them:
# the big piece for a 1:1 slope, the small one at the top of a 2:1 step
SHORE_SMALL = {("N", "E"): 3, ("N", "W"): 4, ("S", "W"): 7, ("S", "E"): 9}
SHORE_SET = {"Grass001": "Water%03d", "Sand001": "Sand_Water%03d", "Snow001": "Snow_Water%03d"}


def smooth_shores(grid):
    old = dict(grid)
    for (x, y), t in old.items():
        if t != "Water001":
            continue
        for (ns, ew), n in SHORE_CORNER.items():
            dy, dx = (-1 if ns == "N" else 1), (1 if ew == "E" else -1)
            land = old.get((x, y + dy)), old.get((x + dx, y)), old.get((x + dx, y + dy))
            sea = old.get((x, y - dy)), old.get((x - dx, y))
            if land[0] in SHORE_SET and land[0] == land[1] == land[2] and all(s == "Water001" for s in sea):
                # a shallow step: the coast carries on past this corner in the next row (or column) as well
                shallow = old.get((x - dx, y + dy)) == land[0] or old.get((x + dx, y - dy)) == land[0]
                grid[(x, y)] = SHORE_SET[land[0]] % (SHORE_SMALL[(ns, ew)] if shallow else n)
                break


def smooth_coast(grid):
    """Takes the one-tile bumps and notches out of the edges of the sea and lakes, so the coast runs in straight and
    diagonal stretches that the corner pieces fit (a sea tile with land on 3 sides becomes land, a land tile with sea on
    3 sides becomes sea; three times over)."""
    for _ in range(3):
        old = dict(grid)
        for (x, y), t in old.items():
            near = [old.get(c) for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))]
            if None in near:
                continue
            wet = sum(1 for v in near if v == "Water001")
            if t == "Water001" and wet <= 1:
                ground = [v for v in near if v in ("Sand001", "Snow001", "Grass001", "Marsh001")]
                grid[(x, y)] = max(set(ground), key=ground.count) if ground else "Sand001"
            elif t in ("Sand001", "Snow001", "Grass001", "Marsh001") and wet >= 3:
                grid[(x, y)] = "Water001"


# ------------------------------------------------------------------ maps
def legend_chars(tiles):
    """A legend character for every tile name used (the legend's own where it has one)."""
    import build_scenery
    rev = {}
    for ch, t in W.LEGEND.items():
        if "+" not in t and t not in rev:
            rev[t] = ch
    taken = set(W.LEGEND) | set("$%&*()[]{}<|?@`;'/0245678bglxSkqv\"") | set("+:\\ ")
    pool = [chr(c) for c in range(0x100, 0x200) if chr(c) not in taken]   # (the ASCII ones are all used)
    for t in sorted(tiles):
        if t not in rev:
            ch = pool.pop(0)
            W.LEGEND[ch] = t
            rev[t] = ch
    return rev


def map_name(mx, my):
    return "%d,%d,0" % (mx, my)


def walk_ok(tile):
    return tile in LAND or tile in ("Reeds001",)


REACHABLE = set()


def reachable(grid):
    """Every land tile you can walk to from the road in from Tyron's Keep (tile by tile, 4 ways)."""
    ok = LAND | {"Reeds001", "Door001"}
    todo, seen = [KEEP_GATE], set()
    while todo:
        c = todo.pop()
        if c in seen or grid.get(c) not in ok:
            continue
        seen.add(c)
        x, y = c
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def spots(grid, busy, mx, my, n, seed, avoid=()):
    """n spread-out free walkable tiles of map mx,my (1-based tile x, y), away from busy cells, that can be reached."""
    if not REACHABLE:
        REACHABLE.update(reachable(grid))
    cells = []
    for y in range(2, GH):
        for x in range(2, GW):
            gx, gy = mx * GW + x - 1, my * GH + y - 1
            if not walk_ok(grid[(gx, gy)]) or (gx, gy) in busy or grid[(gx, gy)] in ("Dirt001", "Plank001") or \
                    (gx, gy) not in REACHABLE:
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


MONSTERS = {   # land -> list of (BadNPC name, how many per map)
    "wood": [("Wolf", 1), ("Bear", 1)],
    "moor": [("Wolf", 2)],
    "marsh": [("Bog_Troll", 1), ("Rat", 1)],
    "hills": [("Bandit", 2), ("Goblin", 1)],
    "desert": [("Scorpion", 2), ("Skeleton", 1)],
    "snow": [("Snow_Wolf", 2)],
}
SETTLER_LINES = {   # gossip in each town: quest hints
    "Oakhollow": "Ranger Ash keeps the old watch stones. Something's been nesting in the deep woods to the west...",
    "Moorcross": "The wolves have been bold this year. The shepherd says there's a den out east, and a great black brute leading them.",
    "Fenwick": "Old Morwen brews by the bog. Elder Pike's been poorly; maybe she can help.",
    "Highwatch": "Bandits on the Redrock road again. Captain Hale wants them gone. Their camp's somewhere in the eastern hills.",
    "Dunerest": "Qadir's caravan never arrived. Lost in the Sunscar, west of here, with the scorpions.",
    "Frosthold": "Brann's forge has gone cold. Something huge broke the ice on the lake to the east.",
}


def make_maps(grid, roofs, busy):
    rev = legend_chars(set(grid.values()))
    maps = {}
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            rows = []
            for y in range(GH):
                rows.append("".join(rev[grid[(mx * GW + x, my * GH + y)]] for x in range(GW)))
            mroofs = [(r[0] - mx * GW + 1, r[1] - my * GH + 1, r[2] - mx * GW + 1, r[3] - my * GH + 1) + tuple(r[4:])
                      for r in roofs if mx * GW <= r[0] < (mx + 1) * GW and my * GH <= r[1] < (my + 1) * GH]
            maps[map_name(mx, my)] = dict(rows=rows, roofs=mroofs, entities=[], triggers=[])
    return maps


def local(gx, gy):
    """(map name, 1-based tile x, y) of world tile gx,gy."""
    mx, my = gx // GW, gy // GH
    return map_name(mx, my), gx - mx * GW + 1, gy - my * GH + 1


def set_tile(maps, grid, gx, gy, tile):
    grid[(gx, gy)] = tile
    m, x, y = local(gx, gy)
    row = maps[m]["rows"][y - 1]
    maps[m]["rows"][y - 1] = row[:x - 1] + legend_chars({tile})[tile] + row[x:]


def populate(maps, grid, busy):
    options = {}

    def add_npc(kind, name, gx, gy, opts=None):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(W.npc(kind, name, x, y))
        if opts:
            options.setdefault(m, {})[(name, x, y)] = opts

    def add(entry_fn, name, gx, gy, *rest):
        m, x, y = local(gx, gy)
        maps[m]["entities"].append(entry_fn(name, x, y, *rest))

    # towns
    for town, (mx, my, giver, rack, text) in TOWNS.items():
        cx, cy = town_centre(town)
        houses = VILLAGES[town]["houses"]                               # nearest the square first (villages.py)
        add_npc("GoodNPC", giver, cx - 2, cy - 2)
        add_npc("GoodNPC", "Trader", *houses[1]["inside"])              # the Trader's shop
        tx, ty = town_tile(town)
        add_npc("GoodNPC", "Settler", cx + 3, cy + 2, "Zone=%d,%d,%d,%d" % (tx - 3, ty - 2, tx + 4, ty + 2))
        add(W.obj, "Notice", cx + 2, cy - 2)
        m, x, y = local(cx + 2, cy - 2)
        S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]
        if town == "Fenwick":
            add_npc("GoodNPC", "Elder", *houses[2]["inside"])
        add_npc("GoodNPC", "Banker", *houses[0]["inside"])              # a bank in every town
        if town == "Highwatch":                                          # on the south street
            street = VILLAGES[town]["streets"]["S"]
            gx, gy = street[len(street) // 2]
            _, lx, ly = local(gx, gy)
            add_npc("GoodNPC", "Guard", gx, gy, "Zone=%d,%d,%d,%d" % (lx - 1, ly - 2, lx + 1, ly + 2))
        if town == "Frosthold":                                          # the smithy
            add(W.obj, "Anvil", *houses[2]["benches"][0])
            add(W.obj, "Furnace", *houses[2]["benches"][1])
        if town == "Oakhollow":
            add(W.obj, "Fire", cx - 4, cy + 1)
    # the notice where the road from Tyron's Keep comes in
    add(W.obj, "Notice", KEEP_GATE[0] + 2, KEEP_GATE[1] + 4)
    m, x, y = local(KEEP_GATE[0] + 2, KEEP_GATE[1] + 4)
    S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice",
        "THE WILDLANDS\\Beyond the King's woods: Oakhollow (west) and Moorcross (east), and further south the Saltmarsh, "
        "the Redrock hills, the Sunscar Desert and Frostpeak.\\Travellers, beware: wolves and worse.", "Okay", "@end"),
        "end:", ("End",)]

    # quest sites
    for k in (1, 2, 3):
        sx, sy = SITES["WatchStone%d" % k]
        set_tile(maps, grid, sx, sy, "Standing_Stone001")
        m, x, y = local(sx, sy)
        maps[m]["triggers"].append(("Watch Stone %d" % k, x, y + 1))
    sx, sy = SITES["SpiderNest"]
    for dx, dy in ((-2, -1), (2, -1), (0, 2), (-1, 1)):
        add_npc("BadNPC", "Giant_Spider", sx + dx, sy + dy, None)
    for dx, dy in ((0, 0), (1, -2), (-2, 2)):
        add(W.item, "Bones", sx + dx, sy + dy)
    sx, sy = SITES["WolfDen"]
    add_npc("BadNPC", "Alpha_Wolf", sx, sy - 1)
    add_npc("BadNPC", "Wolf", sx - 2, sy + 1)
    add_npc("BadNPC", "Wolf", sx + 2, sy + 1)
    add(W.item, "Bones", sx + 1, sy)
    m, x, y = local(sx, sy + 3)
    maps[m]["triggers"].append(("Wolf Den", x, y))
    sx, sy = SITES["BanditCamp"]
    set_tile(maps, grid, sx - 2, sy - 2, "Tent002")
    set_tile(maps, grid, sx + 1, sy - 3, "Tent002")
    add(W.obj, "Fire", sx, sy)
    add(W.obj, "Strongbox", sx + 2, sy - 2)
    for dx, dy in ((-2, 1), (2, 1), (0, -2)):
        add_npc("BadNPC", "Bandit", sx + dx, sy + dy)
    sx, sy = SITES["CaravanWreck"]
    for dx, dy in ((-2, -1), (2, 0), (-1, 2)):
        add(W.item, "Bones", sx + dx, sy + dy)
    add(W.item, "Caravan_Ledger", sx + 1, sy - 1)
    for dx, dy in ((-2, 1), (2, -2), (0, 2), (2, 2)):
        add_npc("BadNPC", "Scorpion", sx + dx, sy + dy)
    m, x, y = local(sx, sy + 3)
    maps[m]["triggers"].append(("Caravan Wreck", x, y))
    sx, sy = SITES["TrollLair"]
    add_npc("BadNPC", "Frost_Troll", sx, sy - 1)
    add(W.item, "Bones", sx - 1, sy)
    add(W.item, "Bones", sx + 2, sy - 1)

    sx, sy = SITES["FrostCave"]
    set_tile(maps, grid, sx, sy, "Ladder006")
    add(W.obj, "Notice", sx + 2, sy + 1)
    m, x, y = local(sx + 2, sy + 1)
    S[W.notice_script_name(m, x, y)] = [("Display.Conversation", "Notice",
        "THE FROSTPEAK CAVERNS\\Old mine workings, frozen solid. Mithril in the walls, they say.\\And things that like the cold.",
        "Okay", "@end"), "end:", ("End",)]

    # monsters out in the wild, and wildlife
    avoid = [town_centre(t) for t in TOWNS] + list(SITES.values()) + [KEEP_GATE]
    import build_scenery
    for name, (attr, loot, msg) in CHESTS.items():      # hidden chests (one per map, opened once: build_scenery's Open Chest)
        if name == CAVE:
            continue
        mx, my = (int(v) for v in name.split(",")[:2])
        spot = spots(grid, busy, mx, my, 1, "chest" + name, avoid)
        if spot:
            x, y = spot[0]
            maps[name]["entities"].append(W.obj("Chest", x, y))
            busy.add((mx * GW + x - 1, my * GH + y - 1))
        build_scenery.CHESTS[name] = (attr, loot, msg)
    import build_scenery
    for my in range(MY0, MY1 + 1):
        for mx in range(MX0, MX1 + 1):
            name = map_name(mx, my)
            land = land_of(mx * GW + 12, my * GH + 10)
            wanted = MONSTERS[land]
            total = sum(n for _, n in wanted)
            places = spots(grid, busy, mx, my, total, "mon" + name, [a for a in avoid if abs(a[0] - (mx * GW + 12)) < 30 and abs(a[1] - (my * GH + 10)) < 30])
            k = 0
            for creature, n in wanted:
                for _ in range(n):
                    if k < len(places):
                        x, y = places[k]
                        maps[name]["entities"].append(W.npc("BadNPC", creature, x, y))
                        k += 1
            if land in ("wood", "moor"):
                build_scenery.WILDLIFE[name] = [("BadNPC", "Rabbit", 2), ("GoodNPC", "Butterfly", 1)]
            elif land == "marsh":
                build_scenery.WILDLIFE[name] = [("BadNPC", "Duck", 2), ("GoodNPC", "Butterfly", 1)]
    for m, opts in options.items():
        C.NPC_OPTIONS.setdefault(m, {}).update(opts)


# ------------------------------------------------------------------ data: tiles, entities, shops, quests
def data():
    C.TILES.update({
        "Snow001": (OPEN, "0", "", "Crisp snow.", "1", None),
        "Ice001": (OPEN, "1", "", "Thick ice. Slippery!", "1", None),
        "Marsh001": (OPEN, "0", "", "Boggy ground. It squelches.", "1", None),
        "Reeds001": (REEDS, "0", "", "Tall reeds. Hard going.", "0", None),
        "Bog_Myrtle001": (BIG, "1", "Pick", "Bog myrtle: its leaves smell of resin. A witch would want this.", "1", None),
        "Bog_Myrtle002": (OPEN, "0", "", "The bog myrtle has been picked. It will grow back.", "1", None),
        "Snow_Pine001": ("0" * 49, "1", "", "A pine, heavy with snow.", "0", None),
        "Snow_Rock001": (BIG, "1", "", "A boulder with a cap of snow.", "1", None),
        "Cactus001": (BIG, "1", "", "A cactus. Don't hug it.", "1", None),
        "Desert_Rock001": (BIG, "1", "", "A red rock, warm from the sun.", "1", None),
    })
    tiles_ini = W.Ini(W.p("Data", "Tiles.ini"))
    for n in range(2, 10):                              # sand and snow shore pieces: walkable where the grass ones are
        walk = tiles_ini.get("Water%03d" % n, "Walkable.Data", "1" * 49)
        C.TILES["Sand_Water%03d" % n] = (walk, "0", "", "Waves lap at the sand.", "1", None)
        C.TILES["Snow_Water%03d" % n] = (walk, "0", "", "Icy water at the edge of the snow.", "1", None)
    C.WALK_SPEED.update({"Snow001": "0.85", "Ice001": "1.25", "Marsh001": "0.75", "Reeds001": "0.6",
                         "Bog_Myrtle002": "0.75"})
    for t, pri in (("Snow001", 5), ("Marsh001", 4), ("Ice001", 1)):
        if all(t != x for x, _ in C.BLEND_TERRAINS):
            C.BLEND_TERRAINS.append((t, pri))
    C.ENTITIES.update({
        "Bear": C.bad("A brown bear, as big as a cart.", 30, 1.4, 5, 4, 70, 2.2, 1, 60, "Bones,1-1,100 Raw_Meat,1-2,100 Cowhide,1-1,60"),
        "Snow_Wolf": C.bad("A white wolf of the high snows.", 28, 1, 6, 5, 100, 2.6, 1, 45, "Bones,1-1,100 Raw_Meat,1-1,70"),
        "Alpha_Wolf": C.bad("The leader of the moor pack: black as night, eyes like coals.", 55, 1.2, 6, 5, 120, 2.6, 1, 180,
                            "Bones,1-1,100 Raw_Meat,2-3,100 Gold_Coin(s),10-25,100"),
        "Scorpion": C.bad("A giant desert scorpion. Mind the tail.", 24, 1.1, 6, 6, 80, 1.8, 1, 40, "Gold_Coin(s),1-4,40"),
        "Bog_Troll": C.bad("A troll of the marshes, green with slime.", 45, 1.5, 6, 5, 70, 1.2, 1, 90,
                           "Bones,1-1,100 Gold_Coin(s),5-12,80 Bog_Myrtle,1-1,40"),
        "Frost_Troll": C.bad("A troll of ice and stone. The cold comes off it in waves.", 100, 1.6, 8, 9, 90, 1.3, 1, 240,
                             "Bones,1-1,100 Gold_Coin(s),20-40,100 Mithril_Ore,1-2,100 Sapphire,1-1,40"),
        "Bandit": C.bad("A road bandit with a rusty blade and no manners.", 26, 1.2, 5, 5, 90, 2, 1, 50,
                        "Bones,1-1,100 Gold_Coin(s),3-10,80 Leather_Cap,1-1,8"),
        "Ranger": C.good("Ranger Ash, keeper of the Wildwood's watch stones."),
        "Shepherd": C.good("A weather-beaten shepherd. His sheep are fewer than they were."),
        "Witch": C.good("Old Morwen, the bog witch. Her cottage smells of smoke and herbs."),
        "Elder": C.good("Elder Pike of Fenwick. He looks pale and tired."),
        "Captain": C.good("Captain Hale of Highwatch, in battered armour."),
        "Merchant": C.good("Qadir the merchant. His caravan is late."),
        "Forgemaster": C.good("Brann the forgemaster, staring at his cold forge."),
        "Trader": C.good("A trader with a little of everything."),
        "Settler": C.good("One of the Wildlands' settlers."),
        "Bog_Myrtle": C.item(6, "A sprig of bog myrtle. It smells of resin.", 20),
        "Witch_Brew": C.item(0, "Morwen's brew for Elder Pike. It bubbles on its own.", 1, droppable=0),
        "Stolen_Goods": C.item(0, "A sack of goods the bandits stole from Highwatch.", 1, droppable=0),
        "Caravan_Ledger": C.item(0, "Qadir's caravan ledger, half buried in sand.", 1),
        "Strongbox": C.station("Open", "The bandits' iron strongbox."),
    })
    C.MOVEMENT.update({
        "Ranger": (1, 0, "0.5", "3-8"), "Shepherd": (1, 0, "0.5", "3-8"), "Witch": (1, 0, "0.4", "4-10"),
        "Elder": (0, 0, "0.4", "5-12"), "Captain": (1, 0, "0.5", "3-8"), "Merchant": (1, 0, "0.5", "3-8"),
        "Forgemaster": (1, 0, "0.5", "3-8"), "Trader": (0, 0, "0.5", "4-10"), "Settler": (3, 0, "0.5", "2-6"),
        "Bear": (3, 4, "0.5", "2-6"), "Snow_Wolf": (5, 5, "0.6", "1-4"), "Alpha_Wolf": (2, 4, "0.5", "2-5"),
        "Scorpion": (3, 3, "0.6", "1-4"), "Bog_Troll": (2, 3, "0.4", "3-8"), "Frost_Troll": (2, 3, "0.4", "4-10"),
        "Bandit": (3, 5, "0.6", "2-5"),
    })
    C.NEW_SHOPS.update({
        "SHOP-Oakhollow": ("1.2", "0.7", ["Oak_Bow,3", "Yew_Bow,1", "Arrows,500", "Bronze_Axe,3", "Axe,3", "Steel_Axe,1", "Tinderbox,3", "Fishing_Rod,2", "Bait,40",
                                          "Bucket,3", "Logs,10", "Oak_Logs,0", "Meat_Pie,4"]),
        "SHOP-Moorcross": ("1.2", "0.7", ["Meat_Pie,5", "Stew,3", "Cooked_Fish,6", "Wool,10", "Leather,5", "Leather_Body,2",
                                          "Leather_Boots,2", "Shears,2", "Raw_Meat,0"]),
        "SHOP-Fenwick": ("1.2", "0.7", ["Empty_Vial,10", "Herb,8", "Basic_Potion,5", "Antidote,3", "Owl_Potion,2", "Defence_Potion,1",
                                        "Bog_Myrtle,0", "Fishing_Rod,2", "Bait,40"]),
        "SHOP-Highwatch": ("1.25", "0.65", ["Steel_Sword,2", "Steel_Shield,2", "Steel_Helm,2", "Steel_Platelegs,1",
                                            "Steel_Platebody,1", "Iron_Sword,3", "Leather_Cap,3", "Healing_Scroll,5"]),
        "SHOP-Dunerest": ("1.2", "0.7", ["Bucket_of_Water,5", "Healing_Scroll,4", "Teleport_Scroll,3", "Fire_Bolt_Scroll,6",
                                         "Sapphire,1", "Ruby,1", "Gold_Bar,0"]),
        "SHOP-Frosthold": ("1.25", "0.7", ["Coal,20", "Steel_Pickaxe,2", "Mithril_Pickaxe,0", "Mithril_Bar,1", "Mithril_Helm,0",
                                           "Mithril_Shield,0", "Stew,4", "Mithril_Ore,0"]),
    })
    shores = " ".join("%s_Water%03d" % (t, n) for t in ("Sand", "Snow") for n in range(2, 10))
    for _, g in C.GATHERING:
        if "Water002" in g.get("Source", "") and "Sand_Water002" not in g["Source"]:
            g["Source"] += " " + shores
    C.CAVE_MAPS.append(CAVE)
    C.GATHERING.append(("Bog myrtle", dict(Gives="Bog_Myrtle", Source="Bog_Myrtle001", Verb="Pick", Tool="", Skill="Herblore",
                                           Level="5", XP="0.15", Where="Bog myrtle bushes in the Saltmarsh")))
    C.QUESTS.extend(QUESTS)


QUESTS = [
    ("The Wildwood Watch", [
        ("Giver", "Ranger"), ("Attribute", "RangerQuest"),
        ("Stage0", "Speak to Ranger Ash in Oakhollow, in the Wildwood south of Tyron's Keep."),
        ("Stage1", "Visit the three old watch stones of the Wildwood ($WatchStones of 3): one by the north road, one in the western woods and one by the river."),
        ("Stage2", "Report to Ranger Ash in Oakhollow."),
        ("Stage3", "Clear the spider nest in the deep woods west of Oakhollow: slay five giant spiders ($WildSpidersSlain of 5), then return to Ranger Ash."),
        ("Done", "4")]),
    ("Wolves of the Moor", [
        ("Giver", "Shepherd"), ("Attribute", "WolfQuest"),
        ("Stage0", "Speak to the shepherd in Moorcross, on Greymoor."),
        ("Stage1", "Thin out the moor wolves: slay six wolves ($WolvesSlain of 6), then tell the shepherd."),
        ("Stage2", "Find the wolf den on the eastern moor and slay the great Alpha Wolf."),
        ("Stage3", "Return to the shepherd in Moorcross."),
        ("Done", "4")]),
    ("Bog Lights", [
        ("Giver", "Witch"), ("Attribute", "BogQuest"),
        ("Stage0", "Speak to Old Morwen the witch in Fenwick, in the Saltmarsh."),
        ("Stage1", "Gather 4 bog myrtle in the Saltmarsh (Herblore 5) and bring them to Morwen."),
        ("Stage2", "Take Morwen's brew to Elder Pike in Fenwick."),
        ("Stage3", "Tell Morwen that the Elder has drunk her brew."),
        ("Done", "4")]),
    ("Bandits on the Road", [
        ("Giver", "Captain"), ("Attribute", "BanditQuest"),
        ("Stage0", "Speak to Captain Hale in Highwatch, the hill fort on the Redrock road."),
        ("Stage1", "Slay five bandits ($BanditsSlain of 5) on the roads and hills, then report to Captain Hale."),
        ("Stage2", "Find the bandits' camp in the eastern hills and take back the stolen goods from their strongbox."),
        ("Stage3", "Bring the stolen goods to Captain Hale in Highwatch."),
        ("Done", "4")]),
    ("The Lost Caravan", [
        ("Giver", "Merchant"), ("Attribute", "CaravanQuest"),
        ("Stage0", "Speak to Qadir the merchant in Dunerest, on the edge of the Sunscar Desert."),
        ("Stage1", "Search the desert west of Dunerest for Qadir's lost caravan."),
        ("Stage2", "Slay the scorpions at the wreck ($ScorpionsSlain of 4), find the caravan's ledger and bring it to Qadir."),
        ("Done", "3")]),
    ("The Frozen Forge", [
        ("Giver", "Forgemaster"), ("Attribute", "ForgeQuest"),
        ("Stage0", "Speak to Brann the forgemaster in Frosthold, under Frostpeak."),
        ("Stage1", "Bring Brann 5 coal to light his forge."),
        ("Stage2", "Slay the Frost Troll on the frozen lake east of Frosthold, which smashed Brann's waterwheel."),
        ("Stage3", "Bring Brann 2 mithril bars (smelt mithril ore at a furnace)."),
        ("Done", "4")]),
]


# ------------------------------------------------------------------ scripts
S = {}


def kill_count(quest, stage, counter, need, what, done_msg, then=None):
    steps = ["// Run when one dies: counts it for the quest %s (stage %d). Generated by build_regions.py" % (quest, stage),
             ("Get.Value", "ATTRIBUTE", quest, "Variable.1$"),
             (">Conditional", "$Variable.1=%d" % stage, "@end"),
             ("Get.Value", "ATTRIBUTE", counter, "Variable.2$"),
             (">Conditional", "$Variable.2<%d" % need, "@end"),
             ("Update.Attribute", counter, "+1"),
             ("Get.Value", "CALCULATION", "$Variable.2+1", "Variable.2$"),
             (">Conditional", "$Variable.2<%d" % need, "@enough"),
             ("Display.Message", "Yellow", "%s: $Variable.2 of %d." % (what, need)),
             ("End",),
             "enough:"]
    if then is not None:
        steps.append(("Update.Attribute", quest, "=%d" % then))
    steps += [("Display.Message", "Yellow", done_msg), "end:", ("End",)]
    return steps


def talk(name, attr, stages, done_lines):
    """A quest giver: stages = list of (stage number, [steps for that stage]); done_lines = what they say afterwards."""
    steps = ["// %s's quest (%s). Generated by build_regions.py" % (name, attr),
             ("Get.Value", "ATTRIBUTE", attr, "Variable.1$")]
    for n, (stage, body) in enumerate(stages):
        nxt = "@s%d" % (n + 1)
        steps.append((">Conditional", "$Variable.1=%d" % stage, nxt))
        steps += body
        steps.append(("End",))
        steps.append("s%d:" % (n + 1))
    steps += [("Display.Conversation", name, done_lines, "Goodbye.", "@bye"), "bye:", ("End",)]
    return steps


def conv(name, text, *answers):
    args = []
    for a, target in answers:
        args += [a, target]
    return ("Display.Conversation", name, text) + tuple(args)


def scripts():
    # ----- The Wildwood Watch
    S["Talk to Ranger"] = talk("Ranger", "RangerQuest", [
        (0, [conv("Ranger", "Well met. I'm Ash, warden of the Wildwood.\\Three old watch stones stand in these woods, and I can't leave the village to check them. Will you visit them for me?",
                  ("I'll check the stones.", "@r_ok"), ("Not now.", "@bye")),
             ("End",), "r_ok:", ("Update.Attribute", "RangerQuest", "=1"), ("Display.Message", "Yellow", "Quest started: The Wildwood Watch.")]),
        (1, [conv("Ranger", "One stone by the north road, one in the western woods, one by the river. Touch each one.", ("I'm on it.", "@bye"))]),
        (2, [conv("Ranger", "All three stones? Then my fears are true: their moss is torn, webs everywhere.\\Spiders. A nest of them in the deep woods to the west. Clear it out: five of them, at least.",
                  ("I'll deal with them.", "@r_sp"), ("Later.", "@bye")),
             ("End",), "r_sp:", ("Update.Attribute", "RangerQuest", "=3"), ("Display.Message", "Yellow", "The Wildwood Watch: slay five giant spiders in the deep woods.")]),
        (3, [("Get.Value", "ATTRIBUTE", "WildSpidersSlain", "Variable.2$"),
             (">Conditional", "$Variable.2>=5", "@r_notyet"),
             ("Update.Attribute", "RangerQuest", "=4"),
             ("Give.Item", "Gold_Coin(s)", "120"), ("Give.Item", "Yew_Staff", "1"),
             ("Update.Skill", "Woodcutting", "+2"), ("Update.Skill", "Strength", "+1"),
             conv("Ranger", "The nest is gone? The woods will breathe easier. Take my old yew staff, and this gold. You've earned them.", ("Thank you!", "@r_done")),
             "r_done:", ("Display.Message", "Yellow", "Quest complete: The Wildwood Watch! You receive 120 gold, a yew staff and experience."),
             ("End",), "r_notyet:", conv("Ranger", "Five spiders, friend. The nest is west of the village, deep in the trees.", ("I'll keep at it.", "@bye"))]),
    ], "The stones are quiet and the spiders are gone. The Wildwood thanks you.")
    for k in (1, 2, 3):
        S["Watch Stone %d" % k] = [
            "// A watch stone of the Wildwood (The Wildwood Watch). Generated by build_regions.py",
            ("Get.Value", "ATTRIBUTE", "RangerQuest", "Variable.1$"),
            (">Conditional", "$Variable.1=1", "@end"),
            ("Get.Value", "ATTRIBUTE", "Watch%d" % k, "Variable.2$"),
            (">Conditional", "$Variable.2=0", "@end"),
            ("Update.Attribute", "Watch%d" % k, "=1"),
            ("Update.Attribute", "WatchStones", "+1"),
            ("Get.Value", "ATTRIBUTE", "WatchStones", "Variable.3$"),
            (">Conditional", "$Variable.3>=3", "@more"),
            ("Update.Attribute", "RangerQuest", "=2"),
            ("Display.Message", "Yellow", "The last watch stone! The moss is torn and there are webs everywhere. Report to Ranger Ash."),
            ("End",),
            "more:",
            ("Display.Message", "Yellow", "You touch the old watch stone. Watch stones visited: $Variable.3 of 3."),
            "end:", ("End",)]
    S["Kill Giant_Spider"] = kill_count("RangerQuest", 3, "WildSpidersSlain", 5, "Giant spiders slain for Ranger Ash",
                                        "Five spiders! Return to Ranger Ash in Oakhollow.")

    # ----- Wolves of the Moor
    S["Talk to Shepherd"] = talk("Shepherd", "WolfQuest", [
        (0, [conv("Shepherd", "Wolves! Every night another lamb gone. I can't fight them with a crook.\\Thin them out for me? Six should make them think twice.",
                  ("I'll hunt them.", "@w_ok"), ("Not now.", "@bye")),
             ("End",), "w_ok:", ("Update.Attribute", "WolfQuest", "=1"), ("Display.Message", "Yellow", "Quest started: Wolves of the Moor.")]),
        (1, [("Get.Value", "ATTRIBUTE", "WolvesSlain", "Variable.2$"),
             (">Conditional", "$Variable.2>=6", "@w_more"),
             ("Update.Attribute", "WolfQuest", "=2"),
             conv("Shepherd", "Six! But they'll be back while their leader lives: a great black brute with a den on the eastern moor.\\Kill the Alpha and the pack will scatter.", ("I'll find the den.", "@bye")),
             ("End",), "w_more:", conv("Shepherd", "Six wolves, friend. They prowl the whole moor.", ("I'll keep hunting.", "@bye"))]),
        (2, [conv("Shepherd", "The den is east, out on the open moor. Be careful: the Alpha is no ordinary wolf.", ("I'll be careful.", "@bye"))]),
        (3, [("Update.Attribute", "WolfQuest", "=4"),
             ("Give.Item", "Gold_Coin(s)", "150"), ("Give.Item", "Steel_Shield", "1"), ("Update.Skill", "Defence", "+2"),
             conv("Shepherd", "The Alpha's dead? Then my flock is safe. Take this shield; it was my father's. And the gold, all I've saved.", ("Thank you!", "@w_done")),
             "w_done:", ("Display.Message", "Yellow", "Quest complete: Wolves of the Moor! You receive 150 gold, a steel shield and Defence experience.")]),
    ], "Not a wolf howl in a week. Bless you.")
    S["Kill Wolf"] = kill_count("WolfQuest", 1, "WolvesSlain", 6, "Wolves slain for the shepherd", "Six wolves! Tell the shepherd in Moorcross.")
    S["Kill Alpha_Wolf"] = ["// The Alpha Wolf dies (Wolves of the Moor). Generated by build_regions.py",
                            ("Get.Value", "ATTRIBUTE", "WolfQuest", "Variable.1$"),
                            (">Conditional", "$Variable.1=2", "@end"),
                            ("Update.Attribute", "WolfQuest", "=3"),
                            ("Display.Message", "Yellow", "The Alpha Wolf is dead! Return to the shepherd in Moorcross."),
                            "end:", ("End",)]
    S["Wolf Den"] = ["// The way into the wolf den. Generated by build_regions.py",
                     ("Get.Value", "ATTRIBUTE", "WolfQuest", "Variable.1$"),
                     (">Conditional", "$Variable.1=2", "@end"),
                     ("Display.Message", "Red", "Bones everywhere... and a low growl. The Alpha Wolf!"),
                     "end:", ("End",)]

    # ----- Bog Lights
    S["Talk to Witch"] = talk("Witch", "BogQuest", [
        (0, [conv("Witch", "Heh. A stranger in the bog. Elder Pike is sick with marsh fever, and only my brew will cure him.\\Fetch me four sprigs of bog myrtle from the marsh. You'll need a little Herblore to pick it.",
                  ("I'll gather some.", "@b_ok"), ("Not now.", "@bye")),
             ("End",), "b_ok:", ("Update.Attribute", "BogQuest", "=1"), ("Display.Message", "Yellow", "Quest started: Bog Lights.")]),
        (1, [(">Got.Item", "Bog_Myrtle", "4", "@b_more"),
             ("Take.Item", "Bog_Myrtle", "4"), ("Give.Item", "Witch_Brew", "1"),
             ("Update.Attribute", "BogQuest", "=2"), ("Play.Sound", "Brew"),
             conv("Witch", "Good, good. Into the pot... there. Take this to Elder Pike, and don't you dare sip it.", ("I won't.", "@bye")),
             ("End",), "b_more:", conv("Witch", "Four sprigs of bog myrtle, dearie. It grows among the reeds.", ("I'll keep looking.", "@bye"))]),
        (2, [conv("Witch", "Off you go! The Elder's house is in the south-west of the village.", ("On my way.", "@bye"))]),
        (3, [("Update.Attribute", "BogQuest", "=4"),
             ("Give.Item", "Mega_Potion", "2"), ("Give.Item", "Gold_Coin(s)", "80"), ("Update.Skill", "Herblore", "+2"),
             conv("Witch", "He drank it? Then he'll live, the old goat. Here: two of my best potions, and some coin.", ("Thank you!", "@b_done")),
             "b_done:", ("Display.Message", "Yellow", "Quest complete: Bog Lights! You receive 2 mega potions, 80 gold and Herblore experience.")]),
    ], "Mind the bog lights, dearie. They lead the foolish astray.")
    S["Talk to Elder"] = [
        "// Elder Pike (Bog Lights). Generated by build_regions.py",
        ("Get.Value", "ATTRIBUTE", "BogQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=2", "@other"),
        (">Got.Item", "Witch_Brew", "1", "@nobrew"),
        ("Take.Item", "Witch_Brew", "1"),
        ("Update.Attribute", "BogQuest", "=3"),
        conv("Elder", "From Morwen? *cough* ...ugh, vile... but... I feel warmer already. Thank her for me.", ("I will.", "@bye")),
        ("Display.Message", "Yellow", "Bog Lights: tell Morwen the Elder has drunk her brew."),
        ("End",),
        "nobrew:", conv("Elder", "*cough* Morwen said she'd send something... have you got it?", ("Not yet.", "@bye")),
        ("End",),
        "other:", conv("Elder", "Welcome to Fenwick, traveller. Keep to the boardwalks.", ("Thanks.", "@bye")),
        "bye:", ("End",)]
    S["Pick Bog_Myrtle"] = C.pick_script("bog myrtle", "Bog_Myrtle", "Bog_Myrtle002", 60, "Herblore", 5, "0.15", 60,
                                         "You pick some bog myrtle...", "...its leaves smell of resin.")

    # ----- Bandits on the Road
    S["Talk to Captain"] = talk("Captain", "BanditQuest", [
        (0, [conv("Captain", "You look handy with a blade. Bandits are robbing every cart on the Redrock road, and my men are too few.\\Kill five of them and come back to me.",
                  ("Consider it done.", "@c_ok"), ("Not now.", "@bye")),
             ("End",), "c_ok:", ("Update.Attribute", "BanditQuest", "=1"), ("Display.Message", "Yellow", "Quest started: Bandits on the Road.")]),
        (1, [("Get.Value", "ATTRIBUTE", "BanditsSlain", "Variable.2$"),
             (">Conditional", "$Variable.2>=5", "@c_more"),
             ("Update.Attribute", "BanditQuest", "=2"),
             conv("Captain", "Five! Now for their camp: somewhere in the eastern hills. They keep what they steal in an iron strongbox. Bring the goods back.", ("I'll find it.", "@bye")),
             ("End",), "c_more:", conv("Captain", "Five bandits. They lurk on the roads and up in the hills.", ("Yes, captain.", "@bye"))]),
        (2, [conv("Captain", "The camp is in the eastern hills. Look for their tents.", ("On my way.", "@bye"))]),
        (3, [(">Got.Item", "Stolen_Goods", "1", "@c_nogoods"),
             ("Take.Item", "Stolen_Goods", "1"),
             ("Update.Attribute", "BanditQuest", "=4"),
             ("Give.Item", "Gold_Coin(s)", "200"), ("Give.Item", "Steel_Platebody", "1"), ("Update.Skill", "Strength", "+2"),
             conv("Captain", "The town's goods! You've done Highwatch a great service. Take this armour, and the reward.", ("Thank you!", "@c_done")),
             "c_done:", ("Display.Message", "Yellow", "Quest complete: Bandits on the Road! You receive 200 gold, a steel platebody and Strength experience."),
             ("End",), "c_nogoods:", conv("Captain", "Where are the goods? Did you lose them?", ("I'll get them.", "@bye"))]),
    ], "The road is safe again. Highwatch salutes you.")
    S["Kill Bandit"] = kill_count("BanditQuest", 1, "BanditsSlain", 5, "Bandits slain for Captain Hale", "Five bandits! Report to Captain Hale in Highwatch.")
    S["Open Strongbox"] = [
        "// The bandits' strongbox (Bandits on the Road). Generated by build_regions.py",
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Get.Value", "ATTRIBUTE", "BanditQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=2", "@other"),
        ("Update.Attribute", "BanditQuest", "=3"),
        ("Play.Sound", "Chest"),
        ("Give.Item", "Stolen_Goods", "1"),
        ("Display.Message", "Yellow", "You break open the strongbox: the stolen goods! Take them to Captain Hale."),
        ("End",),
        "other:", ("Display.Message", "Cyan", "The strongbox is empty."),
        ("End",),
        "far:", ("Display.Message", "DarkRed", "You are too far away!"),
        ("End",)]

    # ----- The Lost Caravan
    S["Talk to Merchant"] = talk("Merchant", "CaravanQuest", [
        (0, [conv("Merchant", "My caravan! Three camels, two drivers, and all my ledgers: lost somewhere in the desert west of here.\\Will you look for it?",
                  ("I'll search the desert.", "@m_ok"), ("Not now.", "@bye")),
             ("End",), "m_ok:", ("Update.Attribute", "CaravanQuest", "=1"), ("Display.Message", "Yellow", "Quest started: The Lost Caravan.")]),
        (1, [conv("Merchant", "West, into the Sunscar. Follow the path past the cacti.", ("I'll keep looking.", "@bye"))]),
        (2, [("Get.Value", "ATTRIBUTE", "ScorpionsSlain", "Variable.2$"),
             (">Conditional", "$Variable.2>=4", "@m_more"),
             (">Got.Item", "Caravan_Ledger", "1", "@m_noledger"),
             ("Take.Item", "Caravan_Ledger", "1"),
             ("Update.Attribute", "CaravanQuest", "=3"),
             ("Give.Item", "Gold_Coin(s)", "180"), ("Give.Item", "Ruby", "2"), ("Update.Skill", "Crafting", "+1.5"),
             conv("Merchant", "My ledger! So the scorpions got them... At least my debts are on paper. Take these rubies, and my thanks.", ("Thank you!", "@m_done")),
             "m_done:", ("Display.Message", "Yellow", "Quest complete: The Lost Caravan! You receive 180 gold, two rubies and Crafting experience."),
             ("End",),
             "m_more:", conv("Merchant", "The scorpions are still there? Clear them out, please.", ("I will.", "@bye")),
             ("End",),
             "m_noledger:", conv("Merchant", "And my ledger? It must be by the wreck.", ("I'll look again.", "@bye"))]),
    ], "Business is slow, but I'm alive, thanks to you.")
    S["Caravan Wreck"] = ["// The caravan's wreck (The Lost Caravan). Generated by build_regions.py",
                          ("Get.Value", "ATTRIBUTE", "CaravanQuest", "Variable.1$"),
                          (">Conditional", "$Variable.1=1", "@end"),
                          ("Update.Attribute", "CaravanQuest", "=2"),
                          ("Display.Message", "Red", "The caravan! Bones in the sand... and scorpions. Find Qadir's ledger."),
                          "end:", ("End",)]
    S["Kill Scorpion"] = kill_count("CaravanQuest", 2, "ScorpionsSlain", 4, "Scorpions slain at the wreck",
                                    "Four scorpions! Find the ledger and return to Qadir in Dunerest.")

    # ----- The Frozen Forge
    S["Talk to Forgemaster"] = talk("Forgemaster", "ForgeQuest", [
        (0, [conv("Forgemaster", "My forge is stone cold, and I've no coal.\\Bring me five lumps and we'll talk about the real trouble.",
                  ("I'll bring coal.", "@f_ok"), ("Not now.", "@bye")),
             ("End",), "f_ok:", ("Update.Attribute", "ForgeQuest", "=1"), ("Display.Message", "Yellow", "Quest started: The Frozen Forge.")]),
        (1, [(">Got.Item", "Coal", "5", "@f_coal"),
             ("Take.Item", "Coal", "5"),
             ("Update.Attribute", "ForgeQuest", "=2"),
             conv("Forgemaster", "Coal! Now, the trouble: a Frost Troll smashed my waterwheel and lairs on the frozen lake east of town. Slay it.", ("I'll slay it.", "@bye")),
             ("End",), "f_coal:", conv("Forgemaster", "Five coal. Mine it in the hills, or buy it from the trader.", ("I'll get it.", "@bye"))]),
        (2, [conv("Forgemaster", "The Frost Troll lairs on the frozen lake to the east. Bring warm clothes.", ("Right.", "@bye"))]),
        (3, [(">Got.Item", "Mithril_Bar", "2", "@f_bars"),
             ("Take.Item", "Mithril_Bar", "2"),
             ("Update.Attribute", "ForgeQuest", "=4"),
             ("Give.Item", "Mithril_Sword", "1"), ("Give.Item", "Gold_Coin(s)", "250"), ("Update.Skill", "Smithing", "+3"),
             ("Play.Sound", "Anvil"),
             conv("Forgemaster", "With the troll gone and the wheel turning... *clang* *clang*... there. A mithril sword, for the one who saved my forge.", ("Thank you!", "@f_done")),
             "f_done:", ("Display.Message", "Yellow", "Quest complete: The Frozen Forge! You receive a mithril sword, 250 gold and Smithing experience."),
             ("End",), "f_bars:", conv("Forgemaster", "Two mithril bars and I'll forge you something special.", ("I'll find them.", "@bye"))]),
    ], "The forge roars again. Come back if you need anything mended.")
    S["Kill Frost_Troll"] = ["// The Frost Troll dies (The Frozen Forge). Generated by build_regions.py",
                             ("Get.Value", "ATTRIBUTE", "ForgeQuest", "Variable.1$"),
                             (">Conditional", "$Variable.1=2", "@end"),
                             ("Update.Attribute", "ForgeQuest", "=3"),
                             ("Display.Message", "Yellow", "The Frost Troll is slain! Bring Brann 2 mithril bars."),
                             "end:", ("End",)]

    # ----- fishing and filling a bucket at the sand and snow shores: the same as at any water
    for shore in ("Sand_Water", "Snow_Water"):
        S["Use Fishing_Rod With %s" % shore] = [("Goto.Script", "Use Fishing_Rod With Water"), ("End",)]
        S["Use Bucket With %s" % shore] = [("Goto.Script", "Use Bucket With Water"), ("End",)]

    # ----- traders and settlers
    trader = ["// The Wildlands' traders: each town's own wares. Generated by build_regions.py"]
    for k, (town, (mx, my, giver, rack, text)) in enumerate(TOWNS.items()):
        trader += [(">On.Map", map_name(mx, my), "@t%d" % (k + 1)),
                   conv("Trader", "Welcome to %s! Have a look at my wares." % town, ("Show me.", "@shop%d" % k), ("Goodbye.", "@bye")),
                   ("End",),
                   "shop%d:" % k, ("Display.Item.Rack", "SPECIFIC", "Trader", rack, "@bye"), ("End",),
                   "t%d:" % (k + 1)]
    trader += [conv("Trader", "Nothing to sell here, I'm afraid.", ("Goodbye.", "@bye")), "bye:", ("End",)]
    S["Talk to Trader"] = trader
    settler = ["// The Wildlands' settlers: gossip that hints at the quests. Generated by build_regions.py"]
    for k, (town, (mx, my, giver, rack, text)) in enumerate(TOWNS.items()):
        settler += [(">On.Map", map_name(mx, my), "@g%d" % (k + 1)),
                    conv("Settler", SETTLER_LINES[town], ("Thanks.", "@bye")),
                    ("End",), "g%d:" % (k + 1)]
    settler += [conv("Settler", "Safe travels.", ("Thanks.", "@bye")), "bye:", ("End",)]
    S["Talk to Settler"] = settler


# ------------------------------------------------------------------ the Frostpeak Caverns (4,9,-1) and the hidden chests
CAVE = "4,9,-1"
CAVE_ROWS = [                       # cave legend (build_content CAVE_LEGEND); @ = ice. The ladder up (^) is under FrostCave
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXzfffXXXXXXXXXXXXXXXXXXX",
    "XXff@ffXXXXXXXZXXXXXXXXXX",
    "XXGf@@fffXXXXffffXXXXXXXX",
    "XXXff@fffffffffffffXXXXXX",
    "XXXXfffffAfff@@ffffffXXXX",
    "XXXXXXfffff@@@@fffAfffXXX",
    "XXXXXXXffffff@@fffffffXXX",
    "XXXQffffwwfffffffff^ffXXX",
    "XXXfffffwwwffffAfffffffXX",
    "XXXXfffffffff@@@ffffffXXX",
    "XXXXXAffff@@@@@ffffzfXXXX",
    "XXXXXXfffff@@@fffffffXXXX",
    "XXXXXXXZfffffffffGffXXXXX",
    "XXXXXXXXXffffffffffXXXXXX",
    "XXXXXXXXXXfffzfffffXXXXXX",
    "XXXXXXXXXXXXffffffXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXX",
]
CHESTS = {   # map: (attribute, [(item, quantity)], what you find) -- added to build_scenery.CHESTS
    "0,5,0": ("WildwoodChest", [("Willow_Staff", 1), ("Super_Potion", 2), ("Gold_Coin(s)", 80)],
              "Under the roots of an old tree: a willow staff, two super potions and 80 gold!"),
    "3,6,0": ("MoorChest", [("Steel_Helm", 1), ("Gold_Coin(s)", 70)],
              "A shepherd's lost strongbox: a steel helm and 70 gold!"),
    "2,8,0": ("BogChest", [("Mega_Potion", 1), ("Owl_Potion", 2), ("Gold_Coin(s)", 60)],
              "Half sunk in the bog: a mega potion, two owl potions and 60 gold!"),
    "5,7,0": ("HillsChest", [("Steel_Platelegs", 1), ("Gold_Coin(s)", 90)],
              "A bandit's hidden stash: steel platelegs and 90 gold!"),
    "2,10,0": ("DesertChest", [("Ruby", 2), ("Teleport_Scroll", 2), ("Gold_Coin(s)", 120)],
               "Buried in the sand: two rubies, two teleport scrolls and 120 gold!"),
    CAVE: ("CavernChest", [("Mithril_Helm", 1), ("Ice_Bolt_Scroll", 3), ("Gold_Coin(s)", 150)],
           "Frozen into the ice: a mithril helm, three ice bolt scrolls and 150 gold!"),
}


def cave_map():
    ice = legend_chars({"Ice001"})["Ice001"]
    rows = [r.replace("@", ice) for r in CAVE_ROWS]
    sx, sy = SITES["FrostCave"]
    _, lx, ly = local(sx, sy)
    assert rows[ly - 1][lx - 1] == "^", (lx, ly)
    ents = [W.npc("BadNPC", "Snow_Wolf", 8, 6), W.npc("BadNPC", "Snow_Wolf", 17, 14),
            W.npc("BadNPC", "Skeleton", 5, 4), W.npc("BadNPC", "Skeleton", 17, 11), W.npc("BadNPC", "Skeleton", 7, 9),
            W.obj("Chest", 4, 2), W.item("Ice_Bolt_Scroll", 15, 16, 2), W.item("Bones", 12, 8), W.item("Bones", 8, 12)]
    return dict(rows=rows, roofs=[], entities=ents, triggers=[])


# ------------------------------------------------------------------ the houses' upper floors, and the locked house
def upper_maps(houses, gw, gh):
    """The level-1 maps over the villages: the upper floors of the houses that have one (villages.lay_house), with
    nothing round them (Black001)."""
    import villages
    out = {}
    for name, cells in villages.upper_floors(houses, gw, gh).items():
        rev = legend_chars(set(cells.values()) | {"Black001"})
        rows = ["".join(rev[cells.get((x, y), "Black001")] for x in range(1, gw + 1)) for y in range(1, gh + 1)]
        out[name] = dict(rows=rows, roofs=[], entities=[], triggers=[])
    return out


GRID, BUSY = {}, set()     # the Wildlands' world grid and its busy cells, once build_grid has made them
LOCKED_TOWN = "Oakhollow"
LOCKED = {}         # the locked house: map, door, window (1-based tiles), the window's tile, the chest (map, x, y)


def locked_house(grid):
    """Old Hob's house in Oakhollow: the door is locked for good, but one window's shutter hangs loose and you can
    climb in. Inside (upstairs if it has an upper floor): his chest."""
    import villages
    houses = VILLAGES[LOCKED_TOWN]["houses"]
    mx, my = TOWNS[LOCKED_TOWN][0], TOWNS[LOCKED_TOWN][1]
    mine = [hs for hs in houses[3:] if hs["x0"] // GW == mx and hs["y0"] // GH == my] or houses[3:]
    hs = max(mine, key=lambda hs: (hs["w"] * hs["h"], hs["x0"]))           # the roomiest
    door, win = villages.lock_house(grid, hs)
    m, dx, dy = local(*door)
    _, wx, wy = local(*win)
    x0, y0, w, h = hs["x0"], hs["y0"], hs["w"], hs["h"]
    chest = None
    tries = ([(hs["upper"], 1, next(c for c, t in hs["upper"].items() if t in ("Stairs002", "Ladder009")))]
             if hs["upper"] else []) + [(grid, 0, (win[0], win[1] - 1))]
    for cells, z, start in tries:                          # upstairs if there's room, else downstairs
        free = {c for c, t in cells.items() if t == "Plank001" and x0 < c[0] < x0 + w - 1
                and y0 < c[1] < y0 + h - (2 if z else 1)} | {start}
        for c in sorted(free, key=lambda c: (c[1], -abs(c[0] - start[0]))):
            gap = max(abs(c[0] - start[0]), abs(c[1] - start[1])) if z else abs(c[0] - start[0]) + abs(c[1] - start[1])
            if gap > (1 if z else 0) and c != (hs["door"][0], hs["door"][1] - 1) and villages.connected(free, {c}, start):
                chest = c
                break
        if chest:
            break
    cm, cx, cy = local(*chest)
    # his diary (build_hob.py, the quest Old Hob): on the ground floor, out of the way of the chest and the doorways
    start = (win[0], win[1] - 1)
    inside = {(x, y) for x in range(x0 + 1, x0 + w - 1) for y in range(y0 + 1, y0 + h - 1)}
    taken = {chest} if z == 0 else set()
    diary = None
    for clear in (False, True):            # a small house: his bed and things go (he ran off), making room for it
        if clear:
            for c in inside:
                if grid[c] in villages.BLOCKING and grid[c] != "Table001":
                    grid[c] = "Plank001"
        floor = {c for c in inside if grid[c] == "Plank001"}
        diary = next((c for c in sorted(floor - taken, key=lambda c: (c[1], c[0]))
                      if c not in (start, (hs["door"][0], hs["door"][1] - 1))
                      and villages.connected(floor | {start}, taken | {c}, start)), None)
        if diary:
            break
    _, ix, iy = local(*diary) if diary else (None, 0, 0)
    LOCKED.update(map=m, door=(dx, dy), window=(wx, wy), tile=villages.window_tile(hs["wall"], 2),
                  chest=("%s,%d" % (cm.rsplit(",", 1)[0], z), cx, cy), diary=(ix, iy) if diary else None)


def locked_house_content(maps):
    m, (dx, dy), (wx, wy) = LOCKED["map"], LOCKED["door"], LOCKED["window"]
    maps[m].setdefault("locks", []).append(
        (dx, dy, "$Attr.HobsDoorOpen>=1", "Boarded up since old Hob went missing. The door won't budge... but one of the shutters hangs loose."))
    cm, cx, cy = LOCKED["chest"]
    maps[cm]["entities"].append(W.obj("Chest", cx, cy))
    import build_scenery
    build_scenery.CHESTS[cm] = ("HobsChest", [("Gold_Coin(s)", 150), ("Silver_Ring", 1), ("Super_Potion", 1)],
                                "Old Hob's savings: 150 gold, a silver ring and a super potion. He won't be needing them.")
    inside_feet = (wy - 2) * 32 + 20                        # the floor just inside the window, and just outside it
    outside_feet = wy * 32 + 14
    S["Climb Through " + LOCKED["tile"]] = [
        "// The loose window of old Hob's locked house in %s (%s). Generated by build_regions.py" % (LOCKED_TOWN, m),
        (">On.Map", m, "@end"),
        (">Distance.From.Clicked.Tile", "70", "@far"),
        (">Conditional", "$Player.Y>=%d" % ((wy - 1) * 32 - 15), "@inside"),     # outside (south of the wall): in
        ("Play.Sound", "Door"),
        ("Teleport", PL.feet("Hobs_Window_Inside", m, (wx - 1) * 32, inside_feet - 31), "-"),
        ("Display.Message", "Cyan", "You squeeze in through the window. Dust everywhere: nobody has been here for a long time."),
        ("Get.Value", "ATTRIBUTE", "HobsDoorOpen", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@done"),
        ("Update.Attribute", "HobsDoorOpen", "=1"),                     # (the door's Lock opens)
        ("Display.Message", "Cyan", "You slide back the bolt on the door: now you can come and go that way."),
        "done:",
        ("End",),
        "inside:",
        ("Teleport", PL.feet("Hobs_Window_Outside", m, (wx - 1) * 32, outside_feet - 31), "-"),
        ("Display.Message", "Cyan", "You climb back out through the window."),
        ("End",),
        "far:", ("Display.Message", "DarkRed", "You are too far away!"),
        "end:", ("End",)]


# ------------------------------------------------------------------ hook
def open_keep_road():
    """Tyron's Keep (2,4,0): a road out of its south wall of forest, down into the Wildlands."""
    rows = W.MAPS["2,4,0"]["rows"]
    for y in range(17, 21):                 # rows 18-21: from the grass below the walls through the forest edge
        row = rows[y][:12] + "=" + rows[y][13:]
        if y == 20:
            row = row[:10] + ".." + row[12] + ".." + row[15:]
        rows[y] = row


def extend(world, content):
    global W, C
    W, C = world, content
    grid, roofs, busy = build_grid()
    GRID.update(grid)                       # (kept for build_hob.py, which places Old Hob in the woods)
    BUSY.update(busy)
    locked_house(grid)
    maps = make_maps(grid, roofs, busy)
    maps.update(upper_maps([hs for v in VILLAGES.values() for hs in v["houses"]], GW, GH))
    data()
    populate(maps, grid, busy)
    locked_house_content(maps)
    scripts()
    W.MAPS.update(maps)
    W.MAPS[CAVE] = cave_map()
    import build_scenery
    build_scenery.CHESTS[CAVE] = CHESTS[CAVE]
    # one continuous grid, so its seams always match (build_world's check_edges skips them)
    W.SEAMLESS_MAPS.update(maps)
    import build_scenery
    for town, t in TOWNS.items():
        build_scenery.SCATTER[map_name(t[0], t[1])] = (60, 6, 0)
    open_keep_road()
    W.S.update(S)
