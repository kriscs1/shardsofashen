"""The quest places lifted from the old maps (world_parts\\parts.json), set down at the same tiles of their new maps
(so every script's coordinates stay right), and the people of the old towns (world_parts\\people.json) put in their
new ones."""
import re

from atlas import XT, YT, TW, map_xy
import layout as L
import land as LAND

# The old towns' maps: which settlement each was (their people go to it)
OLD_TOWN = {"0,3,0": "Southport", "1,3,0": "Southport", "0,6,0": "Wildwood", "0,8,0": "Saltmarsh", "1,8,0": "Fenwick",
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
    "Southport": [("City Hall", "parliament", "NPC\tSpeaker\t0\t0\tAttitude=Good Stand=1 Face=S Id=Southport_Speaker_20")],
    "Galaith": [("Parliament", "parliament", "NPC\tChancellor\t0\t0\tAttitude=Good Stand=1 Face=S "
                                             "Id=Galaith_Speaker_70 Name=Lord_Chancellor_Vane"),
                ("City Hall", "hall", "NPC\tArchivist\t0\t0\tAttitude=Good Stand=1 Face=S Id=Galaith_Clerk_73 "
                                      "Name=Archivist_Sefton")],
    "Ashford": [("Town Hall", "hall", "NPC\tMayor\t0\t0\tAttitude=Good Stand=1 Face=S Id=Ashford_Clerk_13 "
                                      "Name=Mayor_Hollis")],
}
# lifted lines that don't come along (the old cart network: the new city has its own)
LEFT = re.compile(r"^(NPC\t(Carter|Horse)\t|StaticObject\tCart\t)")


def world(part, x, y):
    mx, my = map_xy(part["new"])
    return mx * XT + x - 1, my * YT + y - 1


def rect_cells(part, grow=0):
    for x1, y1, x2, y2 in part["rects"]:
        for y in range(y1 - grow, y2 + grow + 1):
            for x in range(x1 - grow, x2 + grow + 1):
                yield world(part, x, y)


def reserved():
    """Every world cell of the lifted places and two tiles round them (kept clear: their ways in and round them)."""
    out = set()
    for part in L.parts()["parts"].values():
        out.update(rect_cells(part, 2))
    return out


ROOF = re.compile(r"Roof\(([A-Za-z_0-9]+)\.(\d+)\)")
OPEN_GROUND = ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Scorched001")
ROADLIKE = ("Dirt001", "Paving001", "Plank001", "Cobble001", "Brick_Paving001", "Gravel001")


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
        for x1, y1, x2, y2 in part["rects"]:
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    c = world(part, x, y)
                    cell = part["cells"].get("%d,%d" % (x, y))
                    if cell is None:
                        if whole:
                            continue
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
            if not LEFT.match(ln):
                m.ents.append(ln)


def levels():
    """The levels under and over the places that moved: {new map name: its file}."""
    import os
    out = {}
    for new in L.parts()["levels"].values():
        out[new] = os.path.join(L.PARTS, "levels", new + ".txt")
    return out


# ------------------------------------------------------------------ the old towns' people
def home_of_old(plans):
    """{old map: the new map its people (and its scripts' >On.Map) go to}: a lifted part's map if it came from there,
    else its settlement's middle."""
    out = {}
    for part in L.parts()["parts"].values():
        out.setdefault(part["old"], part["new"])
    for old, key in OLD_TOWN.items():
        if old not in out and key in plans:
            out[old] = plans[key].home_map()
    return out


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
            elif f[0] == "NPC" and not any(e.split("\t")[:2] == ["Id", pid] for e in atlas.maps[m.name].ents):
                atlas.place_id(spot[0], spot[1], pid)
            placed.setdefault(old, []).append((int(float(f[2])) // TW + 1, (int(float(f[3])) + 24) // TW + 1, pid))
    return homes, placed
