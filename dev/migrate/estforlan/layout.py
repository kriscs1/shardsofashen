"""The plan of the new mainland (dev\\World Plan.md): the grid of what each map is, the settlements, the quest places
lifted from the old maps, the rivers and the roads."""
import json
import os

from atlas import XT, YT

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(HERE, "world_parts")

ISLE = {"0,0,0", "0,1,0", "1,0,0", "1,1,0", "1,2,0", "2,0,0", "2,1,0", "2,2,0", "3,0,0", "3,1,0", "3,2,0", "4,0,0",
        "4,1,0"}
# I the Isle (left alone) ~ sea  M the West Range  C the Cinder Peaks  N the Frostpeak range  G Galaith  F the dragon's
# field  P the pass  g fields  w the Wildwood  o Greymoor  h the Redrock hills  s the Saltmarsh  d the Sunscar Desert
# n the Frostpeak snowfields  e the Elderwood  a the Ashwold  u the downs  v Wardhaven's island  D Dragon Island
GRID = [
    "IIIII~~~~~~~~~~~~~~~~~~~~",
    "IIIII~~~~~~~vvv~~~~~~~~~~",
    "~III~~~~~~~~vvv~~~~~~~~~~",
    "~~~~~~~~~~~~vvv~~~~~~~~~~",
    "MMgggggggggggggggggCCaaa~",
    "MMwggggggggggggggggCCaaa~",
    "MMwwwwgggggggggggggCCaaa~",
    "MMwwwwwwwgoooooggggCCaaa~",
    "MMwwwwwwwoooooooeeeCCaa~~",
    "MMwwwwwwwooooooeeeeehhuu~",
    "MMMMMMMMMMoooooeeeeehggg~",
    "MGGGGGGFFPooooeeeeeehggg~",
    "MGGGGGGFFPhhooeeeeeehggg~",
    "MGGGGGGFFPhhhhheeeeuuggg~",
    "MGGGGGGFFPhhhhhhuuuuuuuu~",
    "MMMMMMMMMMhhhhhhuuuuuuuu~",
    "Mdddddsssshnnnnnuuuuuuuu~",
    "Mdddddsssssnnnnnuuuuuuuu~",
    "Mdddddsssssnnnnnuuuuuuu~~",
    "MdddddssssNNNNNNuuuuu~~~~",
    "~~~~~~sssss~~~~~~~~~~~D~~",
    "~~~~~~~~~~~~~~~~~~~~~~~~~",
]
W, H = 25, 22                       # the grid's maps (x 0-24, y 0-21)


def macro(mx, my):
    """What map mx,my is ('~' off the grid)."""
    if 0 <= my < H and 0 <= mx < W:
        row = GRID[my]
        c = row[mx] if mx < len(row) else "~"
        return "u" if c == "U" else c
    return "~"


LAND = {"g": "meadow", "w": "wood", "o": "moor", "h": "hills", "s": "marsh", "d": "desert", "n": "snow", "e": "elder",
        "a": "ash", "u": "downs", "M": "mount", "C": "cinder_mount", "N": "snow_mount", "G": "galaith", "F": "field",
        "P": "pass", "v": "meadow", "D": "meadow"}
MOUNTAINS = {"M", "C", "N", "P"}
HARD = {"G", "F", "P"}             # (drawn as planned: the borders of the rest wander with noise)

# ------------------------------------------------------------------ the settlements
# key: title, size, maps (x1, y1, x2, y2), its streets near the middle / further out, its walls, coast side, extras
SETTLEMENTS = {
    "Galaith": dict(title="Galaith", size="huge", maps=(1, 11, 6, 14), street="Marble_Paving001", outer="Cobble001",
                    walls=[("Plaster001", 4), ("Stone_Wall001", 4), ("Brick001", 2)], grand="Stone_Wall001", coast=None,
                    land="meadow"),
    "Southport": dict(title="Southport", size="large", maps=(2, 4, 5, 6), street="Brick_Paving001", outer="Cobble001",
                      walls=[("Brick001", 5), ("Plaster001", 3), ("Timber001", 2)], grand="Stone_Wall001", coast="N",
                      land="meadow"),
    "Keep": dict(title="King Rupert's Keep", size="medium", maps=(21, 10, 23, 12), street="Cobble001",
                 outer="Gravel001", walls=[("Stone_Wall001", 5), ("Plaster001", 3), ("Brick001", 2)],
                 grand="Stone_Wall001", coast="E", land="meadow"),
    "Court": dict(title="the Wizards' Court", size="medium", maps=(16, 4, 18, 6), street="Mage_Flag001",
                  outer="Gravel001", walls=[("Stone_Wall001", 4), ("Plaster001", 4), ("Timber001", 2)],
                  grand="Stone_Wall001", coast="N", land="meadow"),
    "Fenwick": dict(title="Fenwick", size="medium", maps=(6, 16, 8, 17), street="Boardwalk001", outer="Boardwalk001",
                    walls=[("Timber001", 5), ("Plaster001", 4), ("Brick001", 1)], grand="Plaster001", coast=None,
                    land="marsh"),
    "Ravensgate": dict(title="Ravensgate", size="medium", maps=(21, 15, 23, 16), street="Slate_Flag001",
                       outer="Gravel001", walls=[("Stone_Wall001", 5), ("Plaster001", 3), ("Brick001", 2)],
                       grand="Stone_Wall001", coast="E", land="downs"),
    "Ashford": dict(title="Ashford", size="small", maps=(9, 4, 10, 5), street="Brick_Paving001", outer="Gravel001",
                    walls=[("Brick001", 4), ("Timber001", 3), ("Plaster001", 3)], grand="Brick001", coast="N",
                    land="meadow"),
    "Highwatch": dict(title="Highwatch", size="town", maps=(12, 13, 13, 14), street="Red_Sandstone001",
                      outer="Dirt001", walls=[("Stone_Wall001", 5), ("Brick001", 3), ("Plaster001", 2)],
                      grand="Stone_Wall001", coast=None, land="hills"),
    "Frosthold": dict(title="Frosthold", size="town", maps=(13, 17, 14, 18), street="Flagstone001", outer="Dirt001",
                      walls=[("Stone_Wall001", 5), ("Timber001", 5)], grand="Stone_Wall001", coast=None, land="snow"),
    "Wardhaven": dict(title="Wardhaven", size="town", maps=(12, 1, 14, 3), street="Cobble001", outer="Cobble001",
                      walls=[("Stone_Wall001", 5), ("Plaster001", 3), ("Brick001", 2)], grand="Stone_Wall001",
                      coast="N", land="meadow"),
    "Oakhollow": dict(title="Oakhollow", size="village", maps=(7, 8, 8, 9), street="Gravel001", outer="Dirt001",
                      walls=[("Timber001", 5), ("Plaster001", 3), ("Brick001", 2)], grand="Timber001", coast=None,
                      land="wood"),
    "Thornwick": dict(title="Thornwick", size="village", maps=(17, 10, 18, 11), street="Gravel001", outer="Dirt001",
                      walls=[("Timber001", 5), ("Plaster001", 3), ("Stone_Wall001", 2)], grand="Timber001",
                      coast=None, land="elder"),
    "Emberwatch": dict(title="Emberwatch", size="village", maps=(22, 5, 23, 6), street="Basalt_Paving001",
                       outer="Dirt001", walls=[("Stone_Wall001", 7), ("Plaster001", 3)], grand="Stone_Wall001",
                       coast="E", land="ash"),
    "Moorcross": dict(title="Moorcross", size="hamlet", maps=(12, 8, 12, 8), street="Dirt001", outer="Dirt001",
                      walls=[("Stone_Wall001", 4), ("Plaster001", 3), ("Brick001", 3)], grand="Stone_Wall001",
                      coast=None, land="moor"),
    "Wildwood": dict(title="Wildwood", size="hamlet", maps=(2, 8, 2, 8), street="Dirt001", outer="Dirt001",
                     walls=[("Timber001", 5), ("Plaster001", 3)], grand="Timber001", coast=None, land="wood"),
    "Dunerest": dict(title="Dunerest", size="hamlet", maps=(3, 18, 3, 18), street="Sandstone_Paving001",
                     outer="Sand001", walls=[("Sandstone001", 6), ("Plaster001", 4)], grand="Sandstone001", coast=None,
                     land="desert"),
    "Saltmarsh": dict(title="Saltmarsh", size="hamlet", maps=(9, 20, 9, 20), street="Boardwalk001",
                      outer="Boardwalk001", walls=[("Timber001", 5), ("Plaster001", 4)], grand="Timber001", coast="S",
                      land="marsh"),
}

# ------------------------------------------------------------------ the quest places, lifted (world_parts\parts.json)
_parts = None


# (parts set down somewhere other than where lift_world_parts.py first meant them)
MOVED = {"hobs_house": "7,9,0", "old_hob": "3,9,0", "troll_lair": "11,18,0", "shrine_2": "22,8,0"}


def parts():
    global _parts
    if _parts is None:
        with open(os.path.join(PARTS, "parts.json"), encoding="utf-8") as f:
            _parts = json.load(f)
        for name, new in MOVED.items():
            _parts["parts"][name]["new"] = new
        for part in _parts["parts"].values():
            part["new"] = tname(part["new"])
        _parts["level_files"] = {tname(new): new for new in _parts["levels"].values()}    # (saved as first named)
        _parts["levels"] = {old: tname(new) for old, new in _parts["levels"].items()}
    return _parts


def people():
    with open(os.path.join(PARTS, "people.json"), encoding="utf-8") as f:
        return json.load(f)


# Where a road comes to each quest place: (its new map x, y, the tile on it), and whether a road or a footpath
POIS = {
    "Iron_Mine": ((20, 10), (7, 13), "road"),
    "Spider_Nest": ((4, 9), (17, 18), "path"),
    "Buried_Library": ((3, 16), (13, 13), "path"),
    "Caravan_Wreck": ((1, 18), (14, 11), "path"),
    "Frost_Caverns": ((12, 16), (20, 11), "path"),
    "Wolf_Den": ((14, 9), (11, 13), "path"),
    "Bandit_Camp": ((15, 14), (12, 14), "path"),
    "Troll_Lair": ((11, 18), (13, 17), "path"),
    "Cinder_Fort": ((23, 4), (13, 16), "road"),
    "Shrine_1": ((21, 4), (9, 13), "path"),
    "Shrine_3": ((21, 7), (18, 20), "path"),
    "Shrine_2": ((22, 8), (14, 11), "path"),
    "Heartwood": ((19, 12), (15, 16), "path"),
    "Barrow": ((18, 17), (9, 18), "path"),
    "Rooks_Pier": ((23, 17), (9, 12), "road"),
    "Downs_Graves": ((17, 14), (20, 14), "path"),
    "Hill_Graves": ((19, 18), (10, 17), "path"),
    "Hollow_Barrel": ((13, 4), (12, 17), "road"),
    "Smugglers_Cove": ((14, 4), (10, 20), "path"),
    "Farm": ((11, 4), (13, 13), "road"),
    "Herbalist": ((11, 4), (21, 19), "path"),
    "Watch_Stone_1": ((5, 7), (7, 10), "path"),
    "Watch_Stone_2": ((2, 9), (19, 9), "path"),
    "Watch_Stone_3": ((8, 6), (15, 19), "path"),
    "Galaith_Pass": ((9, 12), (24, 11), "road"),
    "Wardhaven_Bridge": ((12, 4), (13, 8), "road"),
}

# The roads: settlement to settlement or place, the main ones first (they're laid first; the rest join them)
ROADS = [
    ("Southport", "Ashford"), ("Ashford", "Farm"), ("Farm", "Wardhaven_Bridge"), ("Farm", "Hollow_Barrel"),
    ("Hollow_Barrel", "Court"), ("Southport", "Oakhollow"), ("Oakhollow", "Wildwood"), ("Oakhollow", "Moorcross"),
    ("Ashford", "Moorcross"), ("Moorcross", "Galaith_Pass"), ("Moorcross", "Thornwick"), ("Thornwick", "Keep"),
    ("Keep", "Iron_Mine"), ("Court", "Emberwatch"), ("Emberwatch", "Cinder_Fort"), ("Thornwick", "Emberwatch"),
    ("Moorcross", "Highwatch"), ("Highwatch", "Frosthold"), ("Highwatch", "Fenwick"), ("Fenwick", "Saltmarsh"),
    ("Fenwick", "Dunerest"), ("Highwatch", "Ravensgate"), ("Keep", "Ravensgate"), ("Ravensgate", "Rooks_Pier"),
    ("Frosthold", "Ravensgate"),
    # footpaths out to the quest places
    ("Oakhollow", "Spider_Nest"), ("Dunerest", "Buried_Library"), ("Dunerest", "Caravan_Wreck"),
    ("Frosthold", "Frost_Caverns"), ("Moorcross", "Wolf_Den"), ("Highwatch", "Bandit_Camp"),
    ("Frosthold", "Troll_Lair"), ("Emberwatch", "Shrine_1"), ("Emberwatch", "Shrine_3"), ("Emberwatch", "Shrine_2"),
    ("Thornwick", "Heartwood"), ("Ravensgate", "Barrow"), ("Ravensgate", "Downs_Graves"), ("Ravensgate", "Hill_Graves"),
    ("Court", "Smugglers_Cove"), ("Farm", "Herbalist"), ("Southport", "Watch_Stone_1"), ("Wildwood", "Watch_Stone_2"),
    ("Oakhollow", "Watch_Stone_3"),
]

# Rivers: world tiles (gx, gy) from the hills to the sea
RIVERS = [
    [(3 * XT + 10, 9 * YT + 15), (5 * XT + 4, 8 * YT + 10), (7 * XT + 6, 7 * YT + 2), (7 * XT + 20, 5 * YT + 10),
     (8 * XT + 4, 4 * YT + 2)],                                         # the Wildwood's river, out by Southport
    [(13 * XT + 3, 15 * YT + 8), (11 * XT + 6, 16 * YT + 8), (9 * XT + 12, 17 * YT + 14), (8 * XT + 20, 19 * YT + 16),
     (7 * XT + 12, 20 * YT + 18)],                                     # (on through the new fens to the sea)
    [(19 * XT + 2, 9 * YT + 10), (20 * XT + 6, 12 * YT + 19), (21 * XT + 10, 13 * YT + 12), (24 * XT + 2, 14 * YT + 3)],
]


# ------------------------------------------------------------------ the world stretched: more room between the places
# Everything above is the plan as first drawn; a new column (row) of maps goes in before each of these, like the one
# west of (above) it, so the wild country between the settlements is wider. Map names east and south of each move on.
INSERT_COLS = (6, 9, 12, 20)
INSERT_ROWS = (7, 9, 18)


def tx(mx):
    """Map column mx of the plan as first drawn -> its column now."""
    return mx + sum(1 for c in INSERT_COLS if c <= mx)


def ty(my):
    return my + sum(1 for r in INSERT_ROWS if r <= my)


def tname(name):
    x, y, z = name.split(",")
    return "%d,%d,%s" % (tx(int(x)), ty(int(y)), z)


def tpoint(gx, gy):
    """A world tile of the plan as first drawn -> where it is now."""
    return tx(gx // XT) * XT + gx % XT, ty(gy // YT) * YT + gy % YT


def _stretch():
    global GRID, W, H
    rows = []
    for my, row in enumerate(GRID):
        if my in INSERT_ROWS:
            rows.append(rows[-1])
        rows.append(row)
    grid = []
    for row in rows:
        out = ""
        for mx, c in enumerate(row):
            if mx in INSERT_COLS:
                out += out[-1]
            out += c
        grid.append(out)
    GRID, W, H = grid, len(grid[0]), len(grid)
    for spec in SETTLEMENTS.values():
        x1, y1, x2, y2 = spec["maps"]
        spec["maps"] = (tx(x1), ty(y1), tx(x2), ty(y2))
    for name, ((mx, my), tile, kind) in list(POIS.items()):
        POIS[name] = ((tx(mx), ty(my)), tile, kind)
    RIVERS[:] = [[tpoint(*p) for p in pts] for pts in RIVERS]


_stretch()
