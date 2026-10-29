"""The quest places lifted from the old maps (world_parts\\parts.json), set down at the same tiles of their new maps
(so every script's coordinates stay right), and the people of the old towns (world_parts\\people.json) put in their
new ones."""
import os
import re

import story_kit as K
from atlas import fbm

from atlas import XT, YT, TW, map_xy
import layout as L
import land as LAND
import towns as OLD

OPEN_GROUND = ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Dirt001")

# The old towns' maps: which settlement each was (their people go to it)
OLD_TOWN = {"0,3,0": "Northport", "1,3,0": "Northport", "0,6,0": "Wildwood", "0,8,0": "Saltmarsh", "1,8,0": "Fenwick",
            "1,10,0": "Dunerest", "1,9,0": "Dunerest", "1,6,0": "Oakhollow", "1,7,0": "Oakhollow",
            "2,3,0": "Ashford", "3,4,0": "Ashford", "2,4,0": "Keep", "2,5,0": "Keep", "2,8,0": "Fenwick",
            "3,8,0": "Fenwick", "3,6,0": "Moorcross", "4,8,0": "Highwatch", "4,9,0": "Frosthold",
            "4,10,0": "Frosthold", "5,4,0": "Court", "7,4,0": "Emberwatch", "8,4,0": "Emberwatch", "7,6,0": "Thornwick",
            "8,7,0": "Ravensgate", "8,8,0": "Ravensgate", "12,6,0": "Galaith", "13,6,0": "Galaith",
            "5,2,0": "Wardhaven", "5,3,0": "Wardhaven", "4,2,0": "Wardhaven", "4,3,0": "Wardhaven",
            "3,3,0": "Wardhaven"}
# who isn't moved: each new town has its own (bankers, sheriffs, constables, its stalls, a smithy's anvil), or they
# belonged to chapters that are gone
DROPPED = {"Banker", "Sheriff", "Constable", "Anvil", "Furnace", "Notice", "Ashen_Acolyte"}
DROPPED_IDS = re.compile(r"Id=Market_Vendor_\d")
# the quest people who work in a town's building (settlements.Plan.adopt puts them at its desk): settlement ->
# [(the building's name, its kind, their map line)]
STAFF = {
    "Northport": [("City Hall", "parliament", "NPC\tSpeaker\t0\t0\tAttitude=Good Stand=1 Face=S Id=Northport_Speaker_20")],
    "Galaith": [("Parliament", "parliament", "NPC\tChancellor\t0\t0\tAttitude=Good Stand=1 Face=S "
                                             "Id=Galaith_Speaker_70 Name=Lord_Chancellor_Vane"),
                ("City Hall", "hall", "NPC\tArchivist\t0\t0\tAttitude=Good Stand=1 Face=S Id=Galaith_Clerk_73 "
                                      "Name=Archivist_Sefton")],
    "Ashford": [("Town Hall", "hall", "NPC\tMayor\t0\t0\tAttitude=Good Stand=1 Face=S Id=Ashford_Clerk_13 "
                                      "Name=Mayor_Hollis")],
}
# lifted lines that don't come along (the old cart network: the new city has its own)
LEFT = re.compile(r"^(NPC\t(Carter|Horse)\t|StaticObject\tCart\t)")


# parts lifted as a whole map whose coast faced another way: only their land is set down (its sand and sea left to
# the new coast), and what stood at the water (moved: rook_pier) is built again where the new shore is
TRIM = {"rooks_pier": [(1, 1, 11, 20)]}
MOVED_LINES = {"rooks_pier": re.compile(r"^(NPC\tSea_Captain\t|StaticObject\t(Boat001|Swordfish_Spot)\t|Id\tRooks_Pier\t)")}
SHORE = ("Sand", "Water", "Sand_Water", "Snow_Water", "Marsh_Water")


def rects(name, part):
    return TRIM.get(name, part["rects"])


def world(part, x, y):
    mx, my = map_xy(part["new"])
    return mx * XT + x - 1, my * YT + y - 1


def rect_cells(part, grow=0, name=None):
    for x1, y1, x2, y2 in rects(name, part):
        for y in range(y1 - grow, y2 + grow + 1):
            for x in range(x1 - grow, x2 + grow + 1):
                yield world(part, x, y)


def reserved():
    """Every world cell of the lifted places and two tiles round them (kept clear: their ways in and round them)."""
    out = set()
    for name, part in L.parts()["parts"].items():
        out.update(rect_cells(part, 2, name))
    return out


ROOF = re.compile(r"Roof\(([A-Za-z_0-9]+)\.(\d+)\)")
OPEN_GROUND = ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Scorched001")
ROADLIKE = ("Dirt001", "Paving001", "Plank001", "Cobble001", "Brick_Paving001", "Gravel001")


def local_ground(c, r=9):
    """The open ground most common round c (a clearing in the desert is sand)."""
    from collections import Counter
    seen = Counter(g for g in (LAND.GROUND.get((c[0] + dx, c[1] + dy), "") for dx in range(-r, r + 1, 2)
                               for dy in range(-r, r + 1, 2))
                   if g in ("Grass001", "Sand001", "Snow001", "Ash001", "Marsh001", "Dirt001"))
    return seen.most_common(1)[0][0] if seen else "Grass001"


def clearings(atlas):
    """Room round each lifted place: mountains within a few tiles of it (an edge that wanders) give way to the
    land's own ground, so it stands in the open and a path can come to it."""
    from atlas import fbm
    for name, part in L.parts()["parts"].items():
        if len(part["cells"]) == XT * YT and name not in TRIM:
            continue
        boxes = [(world(part, x1, y1), world(part, x2, y2)) for x1, y1, x2, y2 in rects(name, part)]
        for c in set(rect_cells(part, 8, name)):
            g = LAND.GROUND.get(c, "")
            if "Peak" not in g:
                continue
            d = min(((max(a[0] - c[0], 0, c[0] - b[0])) ** 2 + (max(a[1] - c[1], 0, c[1] - b[1])) ** 2) ** 0.5
                    for a, b in boxes)
            if d <= 2 + 6 * fbm(c[0], c[1], 6, 79):              # (round, its edge wandering)
                ground = local_ground(c)
                atlas.set(c[0], c[1], tile=ground, decor="")
                m, x, y = atlas.at(*c)
                m.rows[y - 1][x - 1] = ground
                LAND.GROUND[c], LAND.DECOR[c] = ground, ""


def stamp(atlas):
    """Every part, set down on its new map at its old tiles: its tiles (what was water there is the sea again), roof
    groups renumbered after the map's own, and its lines."""
    for name, part in sorted(L.parts()["parts"].items()):
        m = atlas.maps.get(part["new"])
        if m is None:
            continue
        shift = max(m.groups() | {0})
        regroup = (lambda c: ROOF.sub(lambda mm: "Roof(%s.%02d)" % (mm.group(1), int(mm.group(2)) + shift), c)) \
            if shift else (lambda c: c)
        whole = len(part["cells"]) == XT * YT
        trimmed = name in TRIM
        for x1, y1, x2, y2 in rects(name, part):
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    c = world(part, x, y)
                    cell = part["cells"].get("%d,%d" % (x, y))
                    if trimmed and "+" not in cell and cell.startswith(SHORE):
                        continue                           # (the new coast's own sand and sea)
                    if not whole and cell in ("Grass001", "Sand001") and \
                            min(x - x1, x2 - x, y - y1, y2 - y) <= int(3 * fbm(c[0], c[1], 5, 98)) and \
                            LAND.GROUND.get(c) in OPEN_GROUND:
                        if LAND.DECOR.get(c) and not OLD.walk_middle(LAND.DECOR[c]):
                            LAND.DECOR[c] = ""                 # (no tree or rock in its way out)
                            m.rows[y - 1][x - 1] = LAND.GROUND[c]
                        continue                           # (its plain edge: the land round it, so no ruled line)
                    if cell is None:
                        if whole:
                            continue
                        alone = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                    if "%d,%d" % (x + dx, y + dy) not in part["cells"]) < 2
                        edge = min(x - x1, x2 - x, y - y1, y2 - y)
                        dry = not LAND.GROUND.get(c, "").startswith("Water")
                        if alone or dry and edge <= 1 + int(4 * fbm(c[0], c[1], 5, 95)):
                            continue                       # (a lone tile, or its edge by dry land: the new land's)
                        cell = "Water001"
                        if c not in LAND.BIOME:
                            LAND.BIOME[c] = "meadow"
                    m.rows[y - 1][x - 1] = regroup(cell)
                    t = cell.split("+")[0]
                    LAND.GROUND[c] = t
                    LAND.DECOR[c] = ""
                    if t in ROADLIKE and "Roof(" not in cell:
                        atlas.roads.add(c)
                    elif "+" in cell or t not in OPEN_GROUND:
                        atlas.taken.add(c)                 # (what stands there; its open ground stays passable)
        for ln in part["lines"]:
            if not LEFT.match(ln) and not (name in MOVED_LINES and MOVED_LINES[name].match(ln)):
                m.ents.append(ln)


def rook_pier(atlas, home=(L.tname("23,17,0"), 5, 11)):
    """Captain Rook's pier, out from the new shore nearest his house (home: its map and tile): planks four long into
    the sea, Rook at its foot looking out, his boat by it, the swordfish beyond; returns its foot (where the road
    comes)."""
    hx, hy = map_xy(home[0])
    hx, hy = hx * XT + home[1] - 1, hy * YT + home[2] - 1
    best = None
    for name in (home[0],) + tuple("%d,%d,0" % (map_xy(home[0])[0] + dx, map_xy(home[0])[1] + dy)
                                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
        m = atlas.maps.get(name)
        if m is None:
            continue
        mx, my = map_xy(name)
        wet = lambda x, y: m.rows[y - 1][x - 1].split("+")[0] == "Water001"      # noqa: E731
        for y in range(3, YT - 2):
            for x in range(2, XT - 6):
                if wet(x, y) or (mx * XT + x - 1, my * YT + y - 1) in atlas.taken:
                    continue
                if all(wet(x + k, y) for k in range(1, 6)) and all(wet(x + k, y + d) for k in range(2, 6)
                                                                     for d in (-1, 1)):
                    d = abs(mx * XT + x - 1 - hx) + abs(my * YT + y - 1 - hy)
                    if best is None or d < best[0]:
                        best = (d, name, x, y)
    if best is None:
        return None
    _, name, x, y = best
    m = atlas.maps[name]
    mx, my = map_xy(name)
    for k in range(1, 5):
        m.rows[y - 1][x + k - 1] = "Plank001"
        LAND.GROUND[(mx * XT + x + k - 1, my * YT + y - 1)] = "Plank001"
    m.ents += ["NPC\tSea_Captain\t%d\t%d\tAttitude=Good Stand=1 Face=E Id=Captain_Rook Name=Captain_Rook"
               % ((x - 1) * TW, (y - 1) * TW - 8),
               "StaticObject\tBoat001\t%d\t%d" % ((x + 2) * TW, (y - 2) * TW + 16),
               "StaticObject\tSwordfish_Spot\t%d\t%d" % ((x + 4) * TW, (y - 1) * TW)]     # (off its end)
    K.place_id(m, "Rooks_Pier", x, y)
    gx, gy = mx * XT + x - 1, my * YT + y - 1
    for k in range(0, 5):
        atlas.taken.add((gx + k, gy))
    atlas.roads.add((gx, gy))
    return gx, gy

def levels():
    """The levels under and over the places that moved: {new map name: its file}."""
    import os
    out = {}
    for new, saved in L.parts()["level_files"].items():
        out[new] = os.path.join(L.PARTS, "levels", saved + ".txt")
    return out


# ------------------------------------------------------------------ the old towns' people
def home_of_old(plans):
    """{old map: the new map its people (and its scripts' >On.Map) go to}: a lifted part's map if it came from there,
    else its settlement's middle."""
    out = {}
    for part in L.parts()["parts"].values():
        out.setdefault(part["old"], part["new"])
    for old, key in OLD_TOWN.items():
        if key in plans and (old not in out or not in_town(plans[key], out[old])):
            out[old] = plans[key].home_map()
    return out


def in_town(plan, map_name):
    mx, my = map_xy(map_name)
    return plan.box_has((mx * XT + XT // 2, my * YT + YT // 2), 10)


def strays(plans):
    """{a lifted part's map: its town's middle} for the old towns' maps whose part now lies out of town (its people
    are in the town instead, so the scripts that ask which map they're on must ask for that one)."""
    out = {}
    for part in L.parts()["parts"].values():
        key = OLD_TOWN.get(part["old"])
        if key in plans and not in_town(plans[key], part["new"]):
            out[part["new"]] = plans[key].home_map()
    return out


_NAMED = []


def wanted(pid):
    """Whether a quest's marker, the world map or a script names this place (an NPC's place nobody names isn't
    marked: it would only clutter the editor)."""
    if not _NAMED:
        text = ""
        for f in ("Quests.ini", "WorldMap.ini"):
            with open(os.path.join(K.DATA, f), "rb") as fh:
                text += fh.read().decode("cp1252") + "\n"
        for f in os.listdir(K.SCRIPTS):
            with open(os.path.join(K.SCRIPTS, f), "rb") as fh:
                text += f + "\n" + fh.read().decode("cp1252", "replace") + "\n"
        _NAMED.append(set(re.findall(r"[A-Za-z0-9_']+", text)))
    return pid in _NAMED[0]


def rehouse(atlas, plans):
    """The old towns' people, near the middle of their new town (on its map), Zone= round where they stand now."""
    homes = home_of_old(plans)
    placed = {}                                                    # old map: [(old tile x, y, their place's name)]
    for old, lines in sorted(L.people().items()):
        key = OLD_TOWN.get(old)
        for ln in lines:
            f = ln.split("\t")
            if f[1] in DROPPED or DROPPED_IDS.search(ln):
                continue
            if f[1] == "Galaith_Dragon" or any(("Id=%s" % s[2].split("Id=")[1].split()[0]) in ln
                                               for v in STAFF.values() for s in v):
                continue                                           # (the dragon's on its field; staff at desks)
            new = homes.get(old)
            if new is None or key is None or key not in plans:
                continue
            plan = plans[key]
            if new != plan.home_map() and new in atlas.maps and f[1] in ("Guard",) and "Patrol=" in ln:
                atlas.maps[new].ents.append(ln)                    # (the keep's patrol: the keep's at its old tiles)
                continue
            spot = plan.spot_on(new)
            if spot is None:
                plan.missing.append("room for " + f[1])
                continue
            m, x, y = atlas.at(*spot)
            opts = " ".join(o for o in (f[4] if len(f) > 4 else "").split()
                            if not o.startswith(("Zone=", "Patrol=", "Pause=")))
            if f[0] == "NPC" and "Stand=1" not in opts:
                opts += " Zone=%d,%d,%d,%d Pause=4-12" % (max(2, x - 3), max(2, y - 2), min(XT - 1, x + 3),
                                                         min(YT - 1, y + 2))
            line = "%s\t%s\t%d\t%d" % (f[0], f[1], (x - 1) * TW, (y - 1) * TW - (8 if f[0] == "NPC" else 0))
            atlas.maps[m.name].ents.append(line + ("\t" + opts.strip() if opts.strip() else ""))
            if f[1] == "Painter" and (spot[0] + 1, spot[1]) not in atlas.taken:
                atlas.line(spot[0] + 1, spot[1], "StaticObject", "Easel")      # (her easel, which she faces)
                atlas.taken.add((spot[0] + 1, spot[1]))
            pid = "%s_%s" % (key, f[1])                            # (a place by them: quest markers point at it)
            if "Id=" in ln:
                pid = ln.split("Id=")[1].split()[0]                # (they have a name already)
            elif f[0] == "NPC" and wanted(pid) and not any(e.split("\t")[:2] == ["Id", pid]
                                                           for e in atlas.maps[m.name].ents):
                atlas.place_id(spot[0], spot[1], pid)      # (only if a quest or a script points at it)
            placed.setdefault(old, []).append((int(float(f[2])) // TW + 1, (int(float(f[3])) + 24) // TW + 1, pid))
    return homes, placed
