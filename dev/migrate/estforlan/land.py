"""The ground of the new mainland: land and sea (the coast wandering round the plan's grid), the lands each tile is
in (their borders warped by noise, but Galaith's valley, field and pass as planned), the mountains (pointy peaks),
the rivers, beaches, and each land's ground, trees, rocks, herbs and ores. Every tile from functions of its world
tile, so the same every run."""
import math

from atlas import XT, YT, fbm, h01, map_name
import layout as L

GW, GH = L.W * XT, L.H * YT
BIOME = {}          # (gx, gy) -> the land's name (layout.LAND), for land tiles; the sea isn't in it
GROUND = {}         # (gx, gy) -> its ground tile, before the scenery
DECOR = {}          # (gx, gy) -> what stands on it
RIVER = set()       # (gx, gy) of the rivers' water

SEA = "Water001"
BEACH = {"meadow": "Sand001", "wood": "Sand001", "moor": "Sand001", "hills": "Sand001", "marsh": "Marsh001",
         "desert": "Sand001", "snow": "Snow001", "elder": "Sand001", "ash": "Sand001", "downs": "Sand001",
         "galaith": "Grass001", "field": "Scorched001", "mount": "Sand001", "cinder_mount": "Sand001",
         "snow_mount": "Snow001", "pass": "Sand001"}
PLAIN = {"meadow": "Grass001", "wood": "Grass001", "moor": "Grass001", "hills": "Grass001", "marsh": "Marsh001",
         "desert": "Sand001", "snow": "Snow001", "elder": "Grass001", "ash": "Ash001", "downs": "Grass001",
         "galaith": "Grass001", "field": "Scorched001", "mount": "Grass001", "cinder_mount": "Ash001",
         "snow_mount": "Snow001", "pass": "Dirt001"}
PEAKS = {"mount": "Peak", "cinder_mount": "Cinder_Peak", "snow_mount": "Snow_Peak", "pass": "Peak"}


def plain(land):
    return PLAIN.get(land, "Grass001")


# ------------------------------------------------------------------ land, sea and the lands
def mapped(gx, gy):
    return L.macro(gx // XT, gy // YT)


def warped(gx, gy, amp, scale, seed):
    """gx,gy moved by big slow noise (bays, headlands, the lands' borders wandering) and a little quick noise (ragged)."""
    wx = gx + amp * (fbm(gx, gy, scale, seed) - 0.5) + amp * 0.3 * (fbm(gx, gy, 9, seed + 3) - 0.5)
    wy = gy + amp * (fbm(gx, gy, scale, seed + 7) - 0.5) + amp * 0.3 * (fbm(gx, gy, 9, seed + 5) - 0.5)
    return int(math.floor(wx)), int(math.floor(wy))


def range_solid(gx, gy):
    """The part of the West Range that is always mountain: its spine down the world's west edge, and the walls of
    Galaith's valley (the half of each wall nearest the valley), so the valley stays shut but for the pass."""
    mx, my = gx // XT, gy // YT
    lx, ly = gx - mx * XT, gy - my * YT
    if mx == 0 and lx <= 12 + 6 * fbm(gx, gy, 12, 81):
        return True
    if mx < 10 and my == 10 and ly >= 9 - 5 * fbm(gx, gy, 10, 82):
        return True
    if mx < 10 and my == 15 and ly <= 11 + 5 * fbm(gx, gy, 10, 83):
        return True
    return False


def is_land_char(c):
    return c not in ("~", "I")


def island(gx, gy, maps, rx, ry, up=0):
    """Wardhaven's island: an oval in its maps (up: tiles north of their middle), its edge wandering."""
    x1, y1, x2, y2 = maps
    cx, cy = (x1 + x2 + 1) * XT / 2.0, (y1 + y2 + 1) * YT / 2.0 - up
    d = math.hypot((gx - cx) / rx, (gy - cy) / ry)
    return d < 1.0 - 0.25 * (fbm(gx, gy, 9, 41) - 0.5)


def land_here(gx, gy):
    m = mapped(gx, gy)
    if m == "I":
        return False
    if m == "v":
        return island(gx, gy, L.SETTLEMENTS["Wardhaven"]["maps"], 34, 20, up=6)  # (over two maps' rows; a bridge to the coast)
    if m == "D":
        return False                                  # (Dragon Island is lifted whole)
    if m == "M" and range_solid(gx, gy):              # (the West Range runs right to the world's edge)
        return True
    wx, wy = warped(gx, gy, 52, 34, 3)
    c = mapped(min(GW - 1, max(0, wx)), min(GH - 1, max(0, wy)))
    if c == "v" or c == "D":
        c = "~"
    if m in L.HARD:                                   # (Galaith's valley is as planned)
        return True
    return is_land_char(c) and not (gx >= GW - XT // 2 or gy >= GH - YT // 2)


def land_of(gx, gy):
    m = mapped(gx, gy)
    if m in L.HARD:
        return L.LAND[m]
    if m == "M" and range_solid(gx, gy):
        return "mount"                                # (the range's spine and the valley's walls stay mountain)
    wx, wy = warped(gx, gy, 90, 46, 11)
    c = mapped(min(GW - 1, max(0, wx)), min(GH - 1, max(0, wy)))
    if c in L.HARD or not is_land_char(c) or c in ("v", "D"):
        c = m if is_land_char(m) and m not in ("v", "D") else "g"
    if c in L.HARD:
        c = "M"
    return L.LAND[c]


# ------------------------------------------------------------------ the coast, tidied (build_regions' way)
SHORE_CORNER = {("N", "E"): 2, ("N", "W"): 5, ("S", "W"): 6, ("S", "E"): 8}
SHORE_SMALL = {("N", "E"): 3, ("N", "W"): 4, ("S", "W"): 7, ("S", "E"): 9}
SHORE_SET = {"Grass001": "Water%03d", "Sand001": "Sand_Water%03d", "Snow001": "Snow_Water%03d",
             "Marsh001": "Marsh_Water%03d"}
SMOOTHABLE = ("Sand001", "Snow001", "Grass001", "Marsh001", "Ash001", "Scorched001")


def smooth_coast(grid, cells):
    """Takes the one-tile bumps and notches out of the coast (three times)."""
    for _ in range(3):
        old = {c: grid[c] for c in cells}
        for (x, y) in cells:
            t = old[(x, y)]
            near = [old.get(c, grid.get(c)) for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))]
            if None in near:
                continue
            wet = sum(1 for v in near if v == SEA)
            if t == SEA and wet <= 1:
                ground = [v for v in near if v in SMOOTHABLE]
                grid[(x, y)] = max(set(ground), key=ground.count) if ground else "Sand001"
            elif t in SMOOTHABLE and wet >= 3:
                grid[(x, y)] = SEA


def smooth_shores(grid, cells):
    old = {c: grid[c] for c in cells}
    for (x, y) in cells:
        if old[(x, y)] != SEA:
            continue
        for (ns, ew), n in SHORE_CORNER.items():
            dy, dx = (-1 if ns == "N" else 1), (1 if ew == "E" else -1)
            g = lambda c: old.get(c, grid.get(c))           # noqa: E731
            land = g((x, y + dy)), g((x + dx, y)), g((x + dx, y + dy))
            sea = g((x, y - dy)), g((x - dx, y))
            if land[0] in SHORE_SET and land[0] == land[1] == land[2] and all(s == SEA for s in sea):
                shallow = g((x - dx, y + dy)) == land[0] or g((x + dx, y - dy)) == land[0]
                grid[(x, y)] = SHORE_SET[land[0]] % (SHORE_SMALL[(ns, ew)] if shallow else n)
                break


# ------------------------------------------------------------------ rivers
def river_cells():
    out = set()
    for pts in L.RIVERS:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = int(max(abs(x2 - x1), abs(y2 - y1))) * 2
            for k in range(n + 1):
                t = k / max(1, n)
                x = x1 + (x2 - x1) * t + 4 * (fbm(x1 + k, y1, 9, 51) - 0.5)
                y = y1 + (y2 - y1) * t + 4 * (fbm(x1, y1 + k, 9, 52) - 0.5)
                for dx in (0, 1):
                    for dy in (0, 1):
                        out.add((int(x) + dx, int(y) + dy))
    return out


# ------------------------------------------------------------------ each land's ground and what grows on it
def scenery(land, gx, gy, r):
    """(ground, decor) for an open tile of land (r: this tile's own dice, 0-1)."""
    n1 = fbm(gx, gy, 11, 61)                  # (woods and copses)
    n2 = fbm(gx, gy, 7, 62)                   # (rocks, pools)
    n3 = fbm(gx, gy, 15, 63)                  # (wetter, drier)
    if land == "meadow":
        if n2 > 0.8:
            return "Water001", ""                                            # (a pond)
        if n1 > 0.7:
            return "Grass001", ("Tree001" if r < 0.45 else "Tree002" if r < 0.75 else "Oak_Tree001" if r < 0.9 else "")
        if n2 > 0.76 and r < 0.4:
            return "Grass001", "Rock001"
        return "Grass001", ("Flowers%03d" % (1 + int(r * 300) % 3) if r < 0.05 else "Tall_Grass001" if r < 0.09
                            else "Pebbles%03d" % (1 + int(r * 900) % 3) if r < 0.11 else "Bush001" if r < 0.115
                            else "Berry_Bush001" if r < 0.118 else "")
    if land in ("wood", "elder"):
        deep = 0.6 if land == "elder" else 0.64
        if n1 > deep:
            return "Forest001", ""
        if n1 > deep - 0.16:
            return "Grass001", ("Tree001" if r < 0.3 else "Tree002" if r < 0.48 else "Oak_Tree001" if r < 0.6
                                else "Yew_Tree001" if r < 0.63 and n1 > deep - 0.06 else "Bush001" if r < 0.67 else "")
        return "Grass001", ("Mushroom_Patch001" if r < 0.01 else "Sage_Patch001" if r < 0.017 else
                            "Berry_Bush001" if r < 0.025 else "Fallen_Log001" if r < 0.03 else
                            "Tall_Grass001" if r < 0.09 else "Flowers%03d" % (1 + int(r * 300) % 3) if r < 0.12 else "")
    if land == "moor":
        if n2 > 0.79:
            return "Water001", ""
        if n2 > 0.7 and r < 0.5:
            return "Grass001", "Rock001"
        return "Grass001", ("Tall_Grass001" if r < 0.16 else "Pebbles%03d" % (1 + int(r * 900) % 3) if r < 0.2
                            else "STONE" if r < 0.2015 else "Marigold_Patch001" if r < 0.206 else "")
    if land == "hills":
        if n2 > 0.72 and r < 0.55:
            return "Grass001", "Rock001"
        ground = "Dirt001" if n3 > 0.68 else "Grass001"
        return ground, ("Copper_Rock001" if r < 0.006 else "Tin_Rock001" if r < 0.012 else "Ore_Rock001" if r < 0.017
                        else "Coal_Rock001" if r < 0.021 else "Silver_Rock001" if r < 0.0225 else
                        "Tree001" if r < 0.04 else "Tall_Grass001" if r < 0.08 else "Nightshade_Patch001" if r < 0.083
                        else "")
    if land == "marsh":
        if n2 > 0.66:
            return "Water001", ("Lily_Pads001" if r < 0.08 else "")
        if n2 > 0.6:
            return "Marsh001", ("Reeds001" if r < 0.6 else "")
        return "Marsh001", ("Willow_Tree001" if r < 0.04 else "Bog_Myrtle001" if r < 0.055 else
                            "Reeds001" if r < 0.1 else "Marigold_Patch001" if r < 0.105 else "")
    if land == "desert":
        if n2 > 0.84:
            return "Water001", ""                                            # (an oasis)
        if n2 > 0.79:
            return "Grass001", ("Tree001" if r < 0.2 else "")
        if fbm(gx, gy, 6, 64) > 0.74 and r < 0.6:
            return "Sand001", "Desert_Rock001"
        return "Sand001", ("Cactus001" if r < 0.022 else "Gold_Rock001" if r < 0.0245 else "Dead_Tree001" if r < 0.028
                           else "")
    if land == "snow":
        if n2 > 0.78:
            return "Ice001", ""                                              # (a frozen pond)
        if n1 > 0.63 and r < 0.8:
            return "Snow001", "Snow_Pine001"
        if fbm(gx, gy, 6, 65) > 0.74 and r < 0.5:
            return "Snow001", "Snow_Rock001"
        return "Snow001", ("Snow_Pine001" if r < 0.025 else "Mithril_Rock001" if r < 0.029 else "Gem_Rock001" if r < 0.031
                           else "")
    if land == "ash":
        if n2 > 0.82:
            return "Lava001", ""
        ground = "Cinder001" if n3 > 0.6 else "Ash001"
        return ground, ("Dead_Tree%03d" % (1 + int(r * 500) % 2) if r < 0.06 else "Ember_Vent001" if r < 0.068 else
                        "Basalt_Rock001" if r < 0.085 else "Coal_Rock001" if r < 0.092 else
                        "Emberroot_Patch001" if r < 0.097 else "")
    if land == "downs":
        if n2 > 0.75 and r < 0.4:
            return "Grass001", "Rock001"
        return "Grass001", ("Tall_Grass001" if r < 0.12 else "Flowers%03d" % (1 + int(r * 300) % 3) if r < 0.15 else
                            "Pebbles%03d" % (1 + int(r * 900) % 3) if r < 0.18 else "Tree001" if r < 0.19 else
                            "Gem_Rock001" if r < 0.1915 else "")
    if land == "field":
        return "Scorched%03d" % (1 + int(r * 700) % 3), ("Dead_Tree%03d" % (1 + int(r * 500) % 2) if r < 0.03 else
                                                          "Dragon_Skull001" if r < 0.036 else "")
    return plain(land), ""


def peak_at(land, gx, gy):
    """The mountain tile at gx,gy: a 2 x 2 big peak where one fits (on even tiles), else one of six."""
    kind = PEAKS[land]
    bx, by = gx - gx % 2, gy - gy % 2
    if h01("big", bx, by) < 0.16 and all(BIOME.get((bx + i, by + j)) == land and GROUND.get((bx + i, by + j)) is None
                                          for i in (0, 1) for j in (0, 1)):
        return "%s_Big%03d" % (kind, 1 + (gx - bx) + 2 * (gy - by))
    return "%s%03d" % (kind, 1 + int(h01("pk", gx, gy) * 6))


# ------------------------------------------------------------------ all of it
def generate(atlas):
    names = set(atlas.maps)
    cells = []
    for n in names:
        mx, my = (int(v) for v in n.split(",")[:2])
        for y in range(YT):
            for x in range(XT):
                cells.append((mx * XT + x, my * YT + y))
    grid = {}
    for c in cells:
        if land_here(*c):
            BIOME[c] = land_of(*c)
            grid[c] = "LAND"
        else:
            grid[c] = SEA
    rivers = river_cells()
    for c in rivers:
        if c in grid and grid[c] == "LAND" and BIOME[c] not in ("mount", "cinder_mount", "snow_mount", "galaith",
                                                                "field", "pass"):
            grid[c] = SEA
            RIVER.add(c)
    # beaches: land within reach of the sea (not of a river), as each land has them
    for c in cells:
        if grid[c] != "LAND":
            continue
        x, y = c
        reach = 2 + (1 if fbm(x, y, 8, 71) > 0.6 else 0)
        near_sea = any(grid.get((x + dx, y + dy)) == SEA and (x + dx, y + dy) not in RIVER
                       for dx in range(-reach, reach + 1) for dy in range(-reach, reach + 1))
        land = BIOME[c]
        if land in PEAKS and land != "pass":
            grid[c] = "PEAK"
        elif near_sea:
            grid[c] = BEACH[land]
        else:
            grid[c] = "OPEN"
    for c in cells:                                    # (mountains first, so the big peaks can see their neighbours)
        if grid[c] == "PEAK":
            GROUND[c] = peak_at(BIOME[c], *c)
            DECOR[c] = ""
    for c in cells:
        t = grid[c]
        if t == "OPEN":
            g, d = scenery(BIOME[c], c[0], c[1], h01("cell", *c))
            if d == "STONE":
                g, d = "Standing_Stone001", ""                 # (a tile of its own, on the moor's grass)
            GROUND[c], DECOR[c] = g, d
        elif t not in ("PEAK",):
            GROUND[c], DECOR[c] = t, ""
    shore = {c: GROUND[c] for c in cells}
    smooth_coast(shore, cells)
    smooth_shores(shore, cells)
    for c in cells:
        if shore[c] != GROUND[c]:
            GROUND[c] = shore[c]
            DECOR[c] = ""
            if shore[c] in SMOOTHABLE and c not in BIOME:
                BIOME[c] = "meadow"
        if GROUND[c] == SEA and h01("searock", *c) < 0.004 and c not in RIVER:
            if h01("sr", *c) < 0.5:
                DECOR[c] = "Sea_Rock001"                        # (a rock: over the water)
            else:
                GROUND[c] = "Sea_Rock002"                       # (two rocks: a tile of their own)
    for c in cells:
        m, x, y = atlas.at(*c)
        g, d = GROUND[c], DECOR.get(c, "")
        m.rows[y - 1][x - 1] = g + ("+Decor(%s)" % d if d else "")


def near_land(c, r=3):
    """A pond (water with land all round it), not the sea's edge or a river."""
    x, y = c
    if c in RIVER:
        return False
    return all(GROUND.get((x + dx, y + dy)) not in (SEA, None) or (x + dx, y + dy) in BIOME
               for dx in range(-r, r + 1, r) for dy in range(-r, r + 1, r))


def open_at(c):
    """Walkable open ground (land, nothing standing on it)?"""
    g, d = GROUND.get(c), DECOR.get(c, "")
    return g in ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Dirt001", "Scorched001",
                 "Scorched002", "Scorched003", "Ice001") and (not d or d.startswith(("Flowers", "Tall_Grass", "Pebbles",
                                                                                       "Fern")))


def wild_map(name):
    return name not in L.ISLE
