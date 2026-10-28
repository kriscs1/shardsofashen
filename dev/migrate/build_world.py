"""Build the expanded Dragon Sword world: the Southlands (new maps), their scripts and data.

Run:  python -I "dev\\migrate\\build_world.py"            (then validate.py, build_minimaps.py)
Re-runnable: every file is rewritten from the definitions below, and only when its content changes.

It never touches the original 13 maps (PROTECTED_MAPS). It adds:
  * maps\\X,Y,Z.txt for every map in MAPS (hand-drawn ASCII layouts, LEGEND below)
  * data\\Scripts\\*.txt from SCRIPTS (labels instead of hand-numbered gotos)
  * sections/keys in data\\Tiles.ini, data\\Entities.ini, data\\ItemRacks.ini and lines in dev\\Minimap Colours.txt
New tile sprites come from build_tiles.py (run it first).

How the Southlands connect to the original island (whose edges are all sea, so nothing can be walked to):
  * A ferry. "1,2,0.txt" (the entry script of the island's pier map) puts the ferrywoman (Woman) at the
    end of the pier and a notice by it; talking to her sails to the Northgate pier (1,3,0) and back.
  * The Wizard in the palace tower on the Royal Isle (4,4,1) can also send you back to the island.
Ladders: Ladder001/Ladder004 = Climb Up (Z+1), Ladder002/005/006/007 = Climb Down (Z-1), always to the
same X,Y. (The house on the Isle, 1,1,0, used to have a ladder UP to 1,1,-1; build_content.py turned it into a
hatch down to what is now its cellar, so there are no special cases any more.)

After building, the checks at the bottom print every problem found:
  * entity feet on unwalkable ground,
  * edge crossings between any two neighbouring maps (existing or new): if the player can walk off one
    map at some point, the spot where the engine puts their feet on the neighbour must be walkable
    (Check.if.Player.is.Off.Screen keeps the feet X when going N/S, the feet Y when going E/W, and puts
    the feet at x=1 / x=798 / y=18 / y=670),
  * ladders: the map they lead to exists, has the opposite ladder on the same tile, and every walkable
    spot around the ladder is walkable there too (climbing keeps the player's X,Y).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAP_W, MAP_H, GEN, Ini, p, read_lines, write_generated, write_lines, decor_cells, \
    built_base, DECOR_MAP
import build_places as PL  # noqa: E402  (named places: build_places.py)

PROTECTED_MAPS = {"0,0,0", "0,1,0", "0,2,0", "1,0,0", "1,1,-1", "1,1,0", "1,2,0", "2,0,0", "2,1,0", "2,2,0",
                  "3,0,0", "3,1,0", "3,2,0"}

# ------------------------------------------------------------------------------------------- legend
LEGEND = {
    "~": "Water001",
    "1": "Water002",    # shore pieces, named by where the WATER is (keypad): 1 = water bottom-left
    "3": "Water005",    # water bottom-right
    "7": "Water008",    # water top-left
    "9": "Water006",    # water top-right
    ".": "Grass001",
    ",": "Weed001",
    "o": "Stone001",
    "O": "Stone002",
    "s": "Sand001",
    "=": "Dirt001",     # roads
    "d": "Dirt001",     # fields, camp ground
    "#": "Brick001",
    "W": "Stone_Wall001",
    "_": "Tile001",
    "p": "Plank001",    # floors, piers, bridges
    "D": "Door001",
    "T": "Tree001",
    "t": "Tree002",
    "Y": "Grass001+Infront(Pine_Tree002)",   # pine top (drawn over the player)
    "P": "Pine_Tree001",                     # pine trunk
    "u": "Tree_Stump001",
    "F": "Forest001",   # dense forest, impassable (used for map-edge woodland so borders are clean)
    "v": "Cliff001",
    "c": "Cliff003",
    "-": "Cliff004",
    ">": "Cliff005",
    "X": "Cave_Wall001",
    "f": "Cave_Floor001",
    "R": "Ore_Rock001",
    "K": "Black001",
    "U": "Ladder001",   # Climb Up
    "H": "Ladder002",   # Climb Down
}
# Functions run on every map's cells (list of rows of tile names) after the legend and the shore pass.
# build_content.py adds the cave dressing (wall faces, floor variety) here.
CELL_HOOKS = []
# and on the cells with their +Roof(...) on (build_content.py: the thin walls inside houses)
ROOF_HOOKS = []
# Ladder tiles: +1 = Climb Up (Z+1), -1 = Climb Down (Z-1); special links that don't go straight up/down
LADDER_DIR = {"Ladder001": 1, "Ladder002": -1}
LADDER_SPECIAL = {}
# Extra data steps (each returns a list of changed files) and extra checks (problems, report), run by main().
EXTRA_STEPS = []
EXTRA_CHECKS = []
# Maps generated as one continuous grid (build_regions.py): their seams with each other match by construction.
SEAMLESS_MAPS = set()


def at(tx, ty, dx=0, dy=0):
    """Pixel top-left for an entity standing on tile tx,ty (1-based)."""
    return (tx - 1) * 32 + dx, (ty - 1) * 32 + dy


def npc(kind, name, tx, ty):
    """An NPC on a map. kind GoodNPC / BadNPC (the builders' tables) is its attitude: entity_line() writes it as an
    NPC line with Attitude=Good / Bad first in its Options."""
    x, y = at(tx, ty)
    return (kind, name, x, y)


NPC_KINDS = {"GoodNPC": "Good", "BadNPC": "Bad"}


def entity_line(e):
    """A map file's line for entity tuple e: (type, name, x, y[, quantity or Options]). The builders' GoodNPC / BadNPC
    are written as `NPC<TAB>name<TAB>x<TAB>y<TAB>Attitude=Good|Bad [Options]` (Data Formats.md)."""
    e = [str(v) for v in e]
    if e[0] in NPC_KINDS:
        opts = e[4].strip() if len(e) > 4 else ""
        if "ATTITUDE=" not in opts.upper():
            opts = ("Attitude=%s %s" % (NPC_KINDS[e[0]], opts)).strip()
        e = ["NPC"] + e[1:4] + [opts]
    return "\t".join(e)


def npc_line_text(line):
    """An old GoodNPC / BadNPC line of a map file -> the NPC line (anything else unchanged)."""
    f = line.split("\t")
    if f[0].strip() in NPC_KINDS and len(f) >= 4:
        return entity_line([f[0].strip()] + f[1:4] + ([f[4]] if len(f) > 4 else []))
    return line


def place(name, tx, ty):
    """Top-left pixel that puts an entity sprite centred on tile tx,ty with its feet on that tile's bottom row."""
    from render_maps import sprite
    spr = sprite("Entities", name)
    w, h = (spr[0], spr[1]) if spr else (32, 32)
    return at(tx, ty, (32 - w) // 2, 32 - h)


def item(name, tx, ty, qty=1):
    x, y = place(name, tx, ty)
    return ("MapItem", name, x, y, qty)


def obj(name, tx, ty):
    x, y = place(name, tx, ty)
    return ("StaticObject", name, x, y)


def notice_script_name(map_name, tx, ty):
    x, y = place("Notice", tx, ty)
    return "Read Notice%s-%d,%d" % (map_name, x, y)


# ------------------------------------------------------------------------------------------- maps
MAPS = {}

# 1,3,0  Northgate: the ferry pier, a beach and a fisher's hut. Road east to Ashford, south to the woods.
MAPS["1,3,0"] = dict(
    rows=[
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~ppppp~~~~~~~~~~",
        "~~~~~~~~~~~pp~~~~~~~~~~~~",
        "~~~~~~~~~~~pp~~~~~~~~~~~~",
        "~~~~~ssssssssssssssssssss",
        "~~~~sssssssssssssssssssss",
        "~~~sssssssss=ss.....,....",
        "~~~ss.......=............",
        "~~s.........=......o.....",
        "~~s.........=============",
        "~~.#####....=............",
        "~~.#ppp#....=........,...",
        "~~.#ppp#....=..........T.",
        "~~.##D##....=....O.......",
        "~~...========............",
        "~~T.........=............",
        "~TT.........=..T.........",
        "~TtT........=.......t....",
        "~~..........=............",
    ],
    roofs=[(4, 13, 8, 15, 1)],
    entities=[
        npc("GoodNPC", "Woman", 15, 4),
        obj("Notice", 14, 9),
        item("Fishing_Rod", 18, 8),
        item("Bait", 19, 8, 5),
        item("Tinderbox", 5, 14),
        item("Logs", 7, 15, 2),
        item("Herb", 21, 18),
    ],
)

# 2,3,0  Ashford: the village. Bakery and general store north of the high street, bank and smithy south of it (their
# doors on their south sides, like every house: a path from each joins the road down the middle).
MAPS["2,3,0"] = dict(
    rows=[
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~sssssssssssssssssss~~~",
        "~~sssssssssssssssssssss~~",
        "ss#######ssssss#######sss",
        "s.#_____#......#ppppp#..s",
        "..#_____#......#ppppp#...",
        "..#_____#......#ppppp#...",
        "..###D###......###D###...",
        "=========================",
        "............=............",
        "..#######...=...#######..",
        "..#_____#...=...#ppppp#..",
        "..#_____#...=...#ppppp#..",
        "..#_____#...=...#ppppp#..",
        "..###D###...=...###D###..",
        ".T...===============...T.",
        "....,..t....=.....t....,.",
        "............=............",
    ],
    roofs=[(3, 7, 9, 10, 1), (16, 7, 22, 10, 2), (3, 14, 9, 17, 3), (17, 14, 23, 17, 4)],
    entities=[
        npc("GoodNPC", "Baker", 5, 9),
        npc("GoodNPC", "Shopkeeper", 19, 9),
        npc("GoodNPC", "Banker", 6, 16),
        npc("GoodNPC", "Blacksmith", 18, 16),
        npc("GoodNPC", "Beggar", 10, 13),
        obj("Fire", 8, 8),
        obj("Fire", 21, 15),
        obj("Notice", 14, 10),
        item("Herb", 2, 20),
        item("Egg", 24, 13),
    ],
)

# 3,3,0  Farmlands: a farm and cabbage fields, a river with a bridge, the herbalist's cottage by the sea.
MAPS["3,3,0"] = dict(
    rows=[
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~~~~~~",
        "~~~sssssssssssss~~ssss~~~",
        "~~ssssssssssssss~~sssss~~",
        "ssssssssssssssss~~sssss~~",
        "ss######........~~.....s~",
        "..#pppp#........~~.....s~",
        "..#pppp#........~~......~",
        "..##D###........~~......~",
        "================pp======~",
        "............=...~~......~",
        "..ddddddddd.=...~~.#####~",
        "............=...~~.#ppp#~",
        "..ddddddddd.=...~~.#ppp#~",
        "............=...~~.##D##~",
        "..ddddddddd.=..~~~~..=.~~",
        ".T..........=.~~~~~~.=.~~",
        ".T...t......=..~~~~..=.~~",
        "............==========.~~",
    ],
    roofs=[(3, 8, 8, 10, 1), (20, 14, 24, 16, 2)],
    entities=[
        npc("GoodNPC", "Farmer", 12, 15),
        npc("GoodNPC", "Herbalist", 22, 16),
        npc("BadNPC", "Chicken", 10, 9),
        npc("BadNPC", "Chicken", 13, 9),
        npc("BadNPC", "Chicken", 11, 10),
        obj("Notice", 14, 13),
        item("Cabbage", 4, 14), item("Cabbage", 7, 14), item("Cabbage", 10, 14),
        item("Cabbage", 5, 16), item("Cabbage", 9, 16),
        item("Cabbage", 3, 18), item("Cabbage", 6, 18), item("Cabbage", 11, 18),
        item("Egg", 14, 10),
        item("Bucket", 6, 9),
        item("Herb", 23, 19),
        item("Herb", 23, 11),
    ],
)

# 1,4,0  Whispering Woods: forest, the road bend, and the hatch down into the old iron mine.
MAPS["1,4,0"] = dict(
    rows=[
        "~~..........=............",
        "~TTt..t.....=.......t....",
        "FTtT....T...=............",
        "FTT.........=....YY......",
        "FT..XXXXX...=....PP...t..",
        "F..XXXXXXX..=..........T.",
        "F..XXXXXXX..=......t.....",
        "FT.XXdHdXX..=............",
        "F..XXdddXX..=............",
        "FT.XXXDXXX..=............",
        "F.....dddddd=============",
        "FT.......................",
        "FtT.....t.........t....TF",
        "FFTt.......T.....YY...tTF",
        "FFTTT..t.....T...PP..TTFF",
        "FFtTTT.......t.....TTtTFF",
        "FFFTtTT...T......TTTTtFFF",
        "FFFFFTTT.....TTTTTTTFFFFF",
        "FFFFFFFFTTTTTTTTtFFFFFFFF",
        "FFFFFFFFFFFFFFFFFFFFFFFFF",
        "FFFFFFFFFFFFFFFFFFFFFFFFF",
    ],
    roofs=[],
    entities=[
        obj("Notice", 11, 10),
        item("Logs", 15, 12, 2),
        item("Herb", 20, 10),
        item("Herb", 4, 12),
        item("Egg", 22, 4),
    ],
)

# 2,4,0  Tyron's Keep: a walled castle with the throne hall (King_Tyron) and the wizard's tower.
MAPS["2,4,0"] = dict(
    rows=[
        "............=............",
        "............=............",
        ".....====================",
        ".....=...................",
        ".....=..WWWWWWWWWWWWW....",
        ".....=..W_#########_W....",
        ".....=..W_#ppppppp#_W....",
        ".T...=..W_#ppppppp#_W..T.",
        ".....=..W_#ppppppp#_W....",
        ".....=..W_####D####_W....",
        "=========___________W...F",
        "........W______WWWWWW...F",
        "F.t.....W______WWWWWW.tFF",
        "F.......WWWWWWWW___WW..FF",
        "F.......WppppppW_U_WW..FF",
        "FF......WppppppW___WW..FF",
        "F.......WWWDWWWWWDWWW...F",
        "FT.....................tF",
        "FF.t..........T......tFFF",
        "FFFFF..T.........T..FFFFF",
        "FFFFFFFFFFFFFFFFFFFFFFFFF",
    ],
    # the hall, the tower and the storeroom (all with their doors in their south walls, the last two in the keep's
    # outer wall): slate over the whole of each stone building, eaves over its walls
    roofs=[(9, 5, 21, 9, 1, "Slate"), (16, 12, 21, 16, 2, "Slate"), (9, 14, 15, 16, 3, "Slate")],
    entities=[
        npc("GoodNPC", "King_Tyron", 15, 7),
        obj("Notice", 7, 12),
        item("Logs", 4, 18),
    ],
)

# 3,4,0  Goblin camp: a cliff ridge with one gap, then the camp: fires, bones, goblins and hobgoblins.
MAPS["3,4,0"] = dict(
    rows=[
        "............=..........~~",
        ".T..........=.........~~~",
        "=============.........~~~",
        "..v.........=...t.....~~~",
        "..v.........=..........~~",
        "..c---------=--------->~~",
        "....ddddddddddddddddd..~~",
        "...ddddddddddddddddddd.~~",
        "...ddddddddddddddddddd..~",
        "...dddddddddddddddddd...~",
        "F..ddddddddddddddddddd..~",
        "F...dddddddddddddddddd..~",
        "Ft..ddddddddddddddddd...~",
        "FT...ddddddddddddddd...~~",
        "FTt....ddddddddddd....~~~",
        "FFT.....t.......t....~~~~",
        "FFtT..........T.....~~~~~",
        "FFFTt....T.........~~~~~~",
        "FFFFTTt.......t...~~~~~~~",
        "FFFFFFFFTt...TTT~~~~~~~~~",
        "FFFFFFFFFFFFFFF~~~~~~~~~~",
    ],
    roofs=[],
    entities=[
        obj("Notice", 14, 4),
        npc("BadNPC", "Goblin", 6, 9),
        npc("BadNPC", "Goblin", 9, 12),
        npc("BadNPC", "Goblin", 17, 8),
        npc("BadNPC", "Hobgoblin", 12, 10),
        npc("BadNPC", "Hobgoblin", 19, 11),
        npc("BadNPC", "Hobgoblin", 14, 14),
        obj("Fire", 10, 9),
        obj("Fire", 16, 12),
        item("Bones", 5, 8), item("Bones", 15, 10), item("Bones", 20, 13), item("Bones", 8, 14),
        item("Raw_Meat", 11, 9),
        item("Gold_Coin(s)", 13, 12, 5),
    ],
)

# 1,4,-1 (the old iron mine), 2,4,-1 (mine depths) and 2,4,-2 (the hobgoblin warren) were redone with the cave
# tileset and are defined in build_content.py (cave_maps), together with the new caves 1,1,-1, 2,1,-1 and 2,4,-3.

# 2,4,1  The wizard's study at the top of the tower in Tyron's Keep.
MAPS["2,4,1"] = dict(
    rows=["K" * 25] * 10 + [
        "KKKKKKKKKKKKKKWWWWWWWKKKK",
        "KKKKKKKKKKKKKKWpppppWKKKK",
        "KKKKKKKKKKKKKKWpppppWKKKK",
        "KKKKKKKKKKKKKKWppHppWKKKK",
        "KKKKKKKKKKKKKKWpppppWKKKK",
        "KKKKKKKKKKKKKKWpppppWKKKK",
        "KKKKKKKKKKKKKKWWWWWWWKKKK",
    ] + ["K" * 25] * 4,
    roofs=[],
    entities=[
        npc("GoodNPC", "Wizard", 16, 12),
        item("Empty_Vial", 20, 12, 2),
        item("Basic_Potion", 20, 16),
        item("Full_Vial", 16, 16),
    ],
)

NEW_MAPS = list(MAPS)

# ------------------------------------------------------------------------------------------- notices
NOTICES = {
    ("1,2,0", 23, 10): "FERRY TO NORTHGATE\\Sailings every day from the end of the pier.",
    ("1,3,0", 14, 9): "NORTHGATE\\North: the ferry to the Isle\\East: Ashford village\\South: Whispering Woods and the old iron mine",
    ("2,3,0", 14, 10): "ASHFORD\\West: Northgate docks\\East: the farmlands\\South: Tyron's Keep",
    ("3,3,0", 14, 13): "WEST: Ashford\\SOUTH: GOBLIN CAMP\\Travellers beware!",
    ("1,4,0", 11, 10): "ASHFORD IRON MINE\\Closed by order of King Tyron. Hobgoblins below!\\The guard lets no one through the gate without\\body armour, unless they are on the King's business.",
    ("2,4,0", 7, 12): "TYRON'S KEEP\\The gate is open to all honest folk.\\East: the goblin camp road",
    ("3,4,0", 14, 4): "GO AWAY HOOMANS!\\This is GOBLIN land now.\\- the Goblins",
}

# ------------------------------------------------------------------------------------------- scripts
# Each script: list of steps. A step is "label:" or a tuple (Command, arg, ...).
# build_content.py replaces some of these (the ladders, Talk to Herbalist/Beggar, Kill Hobgoblin, Mine Ore_Rock,
# Use Fishing_Rod With Water) with extended versions: see scripts() there. "@label" in an argument is
# replaced by that label's line number. Empty arguments are written as a single space.
S = {}

S["Climb Up Ladder001"] = [
    "// Ladder001 = Climb Up (Z+1). The original house 1,1,0 leads to the room stored as 1,1,-1",
    "// (in the old game Climb Up went to Z-1), so that one ladder is special.",
    (">On.Map", "1,1,0", "@generic"),
    ("Play.Sound", "Ladder"),
    ("Display.Message", "Cyan", "You climb up the ladder."),
    ("Teleport", "$Player.X,$Player.Y", "1,1,-1"),
    ("End",),
    "generic:",
    "// Elsewhere: the same X,Y one level up. If that map doesn't exist the engine says it leads nowhere",
    "// and the player stays put, so the climb message is only shown once the map has really changed.",
    ("Get.Value", "CALCULATION", "$Map.Z+1", "Variable.9$"),
    ("Get.Value", "CALCULATION", "$Map.Name", "Variable.8$"),
    ("Teleport", "$Player.X,$Player.Y", "$Map.X,$Map.Y,$Variable.9"),
    (">Conditional", "$Map.Name<>$Variable.8", "@end"),
    ("Play.Sound", "Ladder"),
    ("Display.Message", "Cyan", "You climb up."),
    "end:",
    ("End",),
]

S["Climb Down Ladder002"] = [
    "// Ladder002 (a hatch) = Climb Down (Z-1). The room 1,1,-1 leads back to the house in 1,1,0.",
    (">On.Map", "1,1,-1", "@generic"),
    ("Play.Sound", "Ladder"),
    ("Display.Message", "Cyan", "You climb down the ladder."),
    ("Teleport", "$Player.X,$Player.Y", "1,1,0"),
    ("End",),
    "generic:",
    "// Elsewhere: the same X,Y one level down (see Climb Up Ladder001)",
    ("Get.Value", "CALCULATION", "$Map.Z-1", "Variable.9$"),
    ("Get.Value", "CALCULATION", "$Map.Name", "Variable.8$"),
    ("Teleport", "$Player.X,$Player.Y", "$Map.X,$Map.Y,$Variable.9"),
    (">Conditional", "$Map.Name<>$Variable.8", "@end"),
    ("Play.Sound", "Ladder"),
    ("Display.Message", "Cyan", "You climb down."),
    "end:",
    ("End",),
]

# --- the ferry
S["1,2,0"] = [
    "// Map entry script for the island pier: the ferrywoman and her notice (the map file itself is unchanged)",
    ("Add.Entity", PL.feet("Isle_Ferry_Pier", "1,2,0", 640, 384), "Woman", "NPC", "-"),
    ("Add.Entity", PL.tile("Isle_Ferry_Notice", "1,2,0", 23, 10), "Notice", "StaticObject", "-"),
    ("End",),
]

# The first crossing (from the Isle) needs a Ferry_Ticket, from the quest Passage to the Mainland (FerryQuest, Done=4:
# build_content.py QUESTS and Talk to Milkmaid); after that each crossing costs 1 gold.
S["Talk to Woman"] = [
    ("Get.Value", "ATTRIBUTE", "FerryQuest", "Variable.1$"),
    (">On.Map", "1,2,0", "@south"),
    (">Conditional", "$Variable.1>=4", "@first"),
    ("Display.Conversation", "Woman", "Ahoy again! Northgate, is it? The fare is 1 gold coin.",
     "Yes, take me to Northgate (1 gold).", "@go", "Not today.", "@bye"),
    "go:",
    (">Got.Item", "Gold_Coin(s)", "1", "@broke"),
    ("Take.Item", "Gold_Coin(s)", "1"),
    ("Goto.Script", "Ferry to Southport"),
    ("End",),
    "first:",
    (">Got.Item", "Ferry_Ticket", "1", "@noticket"),
    ("Display.Conversation", "Woman", "A ticket, stamped by my sister! Hop aboard. After this it's a gold coin a crossing.",
     "Take me to Northgate.", "@sail", "Not yet.", "@bye"),
    "sail:",
    ("Take.Item", "Ferry_Ticket", "1"),
    ("Update.Attribute", "FerryQuest", "=4"),
    ("Display.Message", "Yellow", "Quest complete: Passage to the Mainland! The ferry is yours for 1 gold a crossing."),
    ("Goto.Script", "Ferry to Southport"),
    ("End",),
    "noticket:",
    (">Conditional", "$Variable.1=0", "@remind"),
    ("Display.Conversation", "Woman", "Ahoy there! I sail across the strait to Northgate, on the southern mainland.\\First crossing is by ticket only. My sister the milkmaid keeps the ticket book, on the farm up north.",
     "I'll get a ticket.", "@start", "Not today.", "@bye"),
    "start:",
    ("Update.Attribute", "FerryQuest", "=1"),
    ("Display.Message", "Yellow", "Quest started: Passage to the Mainland."),
    ("End",),
    "remind:",
    ("Display.Conversation", "Woman", "No ticket, no crossing, I'm afraid. My sister the milkmaid has the ticket book, on the farm in the north of the Isle.",
     "I'll get one.", "@bye"),
    ("End",),
    "south:",
    (">On.Map", "1,3,0", "@other"),
    ("Display.Conversation", "Woman", "Back to the Isle, is it? That's 1 gold coin, then climb aboard.",
     "Yes, back to the Isle (1 gold).", "@back", "Not yet.", "@bye"),
    "back:",
    (">Got.Item", "Gold_Coin(s)", "1", "@broke"),
    ("Take.Item", "Gold_Coin(s)", "1"),
    (">Conditional", "$Variable.1<4", "@sailback"),
    ("Update.Attribute", "FerryQuest", "=4"),       # a save from before the ticket: you've crossed already
    "sailback:",
    ("Goto.Script", "Ferry to the Isle"),
    ("End",),
    "broke:",
    ("Display.Message", "DarkRed", "You need 1 gold coin for the ferry fare."),
    ("End",),
    "other:",
    ("Display.Conversation", "Woman", "Fair winds to you!", "Goodbye.", "@bye"),
    "bye:",
    ("End",),
]

S["Ferry to Southport"] = [
    ("Display.Message", "Cyan", "You climb aboard the ferry and cast off..."),
    ("Play.Sound", "Boat"),
    ("Toggle.User.Input", "OFF"),
    ("Wait", "2"),
    ("Toggle.User.Input", "ON"),
    ("Teleport", PL.tile("Southport_Pier", "1,3,0", 12, 5), "-"),
    ("Display.Message", "Yellow", "...and tie up at the Northgate pier."),
    ("End",),
]

S["Ferry to the Isle"] = [
    ("Display.Message", "Cyan", "You climb aboard the ferry and cast off..."),
    ("Play.Sound", "Boat"),
    ("Toggle.User.Input", "OFF"),
    ("Wait", "2"),
    ("Toggle.User.Input", "ON"),
    ("Teleport", PL.tile("Isle_Pier", "1,2,0", 21, 12), "-"),
    ("Display.Message", "Yellow", "...and arrive back at the Isle."),
    ("End",),
]

# --- map entry flavour
S["1,3,0"] = [("Display.Message", "Cyan", "Northgate. Gulls wheel over the harbour."), ("End",)]
S["2,3,0"] = [("Display.Message", "Cyan", "Ashford village. You smell fresh bread."), ("End",)]
S["3,3,0"] = [("Display.Message", "Cyan", "The farmlands of Ashford."), ("End",)]
S["1,4,0"] = [("Display.Message", "Cyan", "The Whispering Woods. The trees creak in the wind."), ("End",)]
S["2,4,0"] = [("Display.Message", "Cyan", "Tyron's Keep."), ("End",)]
S["3,4,0"] = [("Display.Message", "DarkRed", "Smoke and the stink of goblins... this is their camp!"), ("End",)]
S["1,4,-1"] = [("Display.Message", "Cyan", "The old iron mine. The air is cold and smells of rust."), ("End",)]
S["2,4,-1"] = [("Display.Message", "DarkRed", "Something growls in the dark tunnels ahead."), ("End",)]
S["2,4,-2"] = [("Display.Message", "DarkRed", "The hobgoblin warren! Bones crunch underfoot."), ("End",)]
S["2,4,1"] = [("Display.Message", "Cyan", "The wizard's study. Strange smells drift from the bubbling vials."), ("End",)]

# --- shops and services
S["Talk to Baker"] = [
    ("Display.Conversation", "Baker", "Morning! Everything's fresh out of the oven.\\You can cook on my oven fire too, if you've got your own meat.",
     "Let me see your bread.", "@shop", "Goodbye.", "@bye"),
    "shop:",
    ("Display.Item.Rack", "SPECIFIC", "Baker", "SHOP-Baker", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Shopkeeper"] = [
    ("Display.Conversation", "Shopkeeper", "Welcome to the Ashford General Store!\\Tools, buckets, fishing gear: if you need it, I've got it.",
     "Show me your wares.", "@shop", "Goodbye.", "@bye"),
    "shop:",
    ("Display.Item.Rack", "GENERAL", "Shopkeeper", "SHOP-Ashford", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Banker"] = [
    ("Display.Conversation", "Banker", "Good day. Your valuables are safe with the Bank of Ashford.",
     "I'd like to use my bank.", "@bank", "No thanks.", "@bye"),
    "bank:",
    ("Display.Item.Rack", "BANK", "Banker", "-", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Blacksmith"] = [
    ("Display.Conversation", "Blacksmith", "Mind the forge, it's hot!\\Bring me iron ore from the mine and I'll show you how to smelt it into bars.\\With bars and some logs you can make your own tools.",
     "Let me use the forge.", "@forge", "What do you sell?", "@shop", "Where is the mine?", "@mine", "Goodbye.", "@bye"),
    "forge:",
    ("Display.Item.Rack", "GENERAL", "Blacksmith", "CRAFT-Smithing", "@bye"),
    ("End",),
    "shop:",
    ("Display.Item.Rack", "SPECIFIC", "Blacksmith", "SHOP-Smith", "@bye"),
    ("End",),
    "mine:",
    ("Display.Conversation", "Blacksmith", "In the Whispering Woods, south-west of Northgate. There's a hatch in the rocks.\\You'll want a pickaxe, and some armour: the King's guard won't let you through the gate without it.",
     "Thanks.", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Herbalist"] = [
    ("Display.Conversation", "Herbalist", "Herbs, potions, remedies... what ails you, dear?\\Bring me three herbs and an empty vial and I'll brew you a healing potion.",
     "Brew me a potion.", "@brew", "Show me your potions.", "@shop", "Goodbye.", "@bye"),
    "brew:",
    (">Got.Item", "Herb", "3", "@noherbs"),
    (">Got.Item", "Empty_Vial", "1", "@novial"),
    ("Take.Item", "Herb", "3"),
    ("Take.Item", "Empty_Vial", "1"),
    ("Display.Message", "Cyan", "The herbalist grinds the herbs and stirs them into the vial..."),
    ("Wait", "1.5"),
    ("Give.Item", "Basic_Potion", "1"),
    ("Display.Message", "Yellow", "She hands you a healing potion!"),
    ("End",),
    "noherbs:",
    ("Display.Conversation", "Herbalist", "I need three herbs, dear. They grow wild all over the Southlands.", "I'll find some.", "@bye"),
    ("End",),
    "novial:",
    ("Display.Conversation", "Herbalist", "You'll need an empty vial to carry it in. I sell them, or drink a potion and keep the vial.", "I see.", "@bye"),
    ("End",),
    "shop:",
    ("Display.Item.Rack", "SPECIFIC", "Herbalist", "SHOP-Herbalist", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Farmer"] = [
    ("Display.Conversation", "Farmer", "Ah, a visitor! Help yourself to a cabbage or two, there's plenty.\\Just don't go chasing my chickens... unless you're buying.",
     "What do you sell?", "@shop", "Seen any goblins?", "@goblins", "Goodbye.", "@bye"),
    "shop:",
    ("Display.Item.Rack", "SPECIFIC", "Farmer", "SHOP-Farm", "@bye"),
    ("End",),
    "goblins:",
    ("Display.Conversation", "Farmer", "Seen them? They steal my eggs every night!\\Their camp is just down the road to the south. King Tyron ought to do something.",
     "I'll speak to the King.", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Miner"] = [
    ("Display.Conversation", "Miner", "Careful, friend! The hobgoblins dug up from the deep and drove us all out.\\There's still good iron in these rocks, though.",
     "How do I mine?", "@how", "Where did the hobgoblins come from?", "@hob", "Goodbye.", "@bye"),
    "how:",
    (">Got.Item", "Pickaxe", "1", "@nopick"),
    ("Display.Conversation", "Miner", "Click on a rock with orange ore in it and swing that pickaxe of yours.\\Take the ore to the Ashford blacksmith to smelt it.\\Once you can mine at level 10, the guild's deep seam in the depths is open to you. Coal and gold in there!", "Thanks!", "@bye"),
    ("End",),
    "nopick:",
    ("Display.Conversation", "Miner", "You'll need a pickaxe. I dropped my spare by the ladder when I ran.\\The Ashford blacksmith sells them too.", "Thanks!", "@bye"),
    ("End",),
    "hob:",
    ("Display.Conversation", "Miner", "There's a hatch in the tunnels to the east that goes down to their warren.\\I saw them carry off all sorts down there. Keys, coins, gems...", "I'll take a look.", "@bye"),
    "bye:",
    ("End",),
]

S["Talk to Beggar"] = [
    ("Display.Conversation", "Beggar", "Spare a coin for a poor old man?", "Here's a coin.", "@give", "Sorry, no.", "@bye"),
    "give:",
    (">Got.Item", "Gold_Coin(s)", "1", "@broke"),
    ("Take.Item", "Gold_Coin(s)", "1"),
    ("Display.Conversation", "Beggar", "Bless you! I wasn't always like this, you know.\\I had a fine brick house on the Isle, but I lost the key in the old iron mine when the hobgoblins chased me out. They took it down to their warren.\\If you ever find it, the house is yours. I'll never go back.",
     "I'll look for it.", "@bye"),
    ("End",),
    "broke:",
    ("Display.Message", "DarkRed", "You don't have any gold!"),
    "bye:",
    ("End",),
]

S["Talk to Wizard"] = [
    ("Display.Conversation", "Wizard", "Hmm? Ah, a visitor. I study the arcane arts up here, far from the noise of the court.\\I can send you anywhere I have been. Where to?",
     "To the Isle.", "@isle", "To Northgate.", "@port", "Nowhere, thanks.", "@bye"),
    "isle:",
    ("Play.Sound", "Teleporter"),
    ("Display.Message", "Yellow", "The wizard waves his hands and the world spins..."),
    ("Teleport", PL.feet("Isle_Landing", "1,1,0", 300, 300), "-"),
    ("End",),
    "port:",
    ("Play.Sound", "Teleporter"),
    ("Display.Message", "Yellow", "The wizard waves his hands and the world spins..."),
    ("Teleport", PL.tile("Southport_Landing", "1,3,0", 12, 11), "-"),
    ("End",),
    "bye:",
    ("End",),
]

# --- the quest
S["Talk to King_Tyron"] = [
    ("Get.Value", "ATTRIBUTE", "HobgoblinQuest", "Variable.1$"),
    (">Conditional", "$Variable.1=0", "@active"),
    ("Display.Conversation", "King_Tyron", "Welcome to my palace, traveller.\\Hobgoblins have crawled up from the deep, overrun the old iron mine and joined the goblins in their camp to the east. My people live in fear.\\Slay five hobgoblins and I shall reward you handsomely.",
     "I will do it, your majesty.", "@accept", "Not now.", "@bye"),
    "accept:",
    ("Update.Attribute", "HobgoblinQuest", "=1"),
    ("Update.Attribute", "HobgoblinsSlain", "=0"),
    ("Display.Message", "Yellow", "Quest started: slay five hobgoblins for King Tyron."),
    ("End",),
    "active:",
    (">Conditional", "$Variable.1=1", "@done"),
    ("Get.Value", "ATTRIBUTE", "HobgoblinsSlain", "Variable.2$"),
    (">Conditional", "$Variable.2>=5", "@notyet"),
    ("Display.Conversation", "King_Tyron", "Five hobgoblins slain! The Southlands are in your debt.\\Take this gold and this ruby. And my treasury in the courtyard is open to you: the chest inside is yours.",
     "Thank you, your majesty.", "@reward"),
    "reward:",
    ("Give.Item", "Gold_Coin(s)", "100"),
    ("Give.Item", "Ruby", "1"),
    ("Update.Skill", "Strength", "+1"),
    ("Update.Attribute", "HobgoblinQuest", "=2"),
    ("Display.Message", "Yellow", "Quest complete! You receive 100 gold and a ruby. The royal treasury is open to you."),
    ("End",),
    "notyet:",
    ("Display.Conversation", "King_Tyron", "You have slain $Variable.2 of the five hobgoblins.\\They lurk in the old iron mine and in the goblin camp. Go!\\My treasury opens to the one who finishes the job.",
     "I'll keep at it.", "@bye"),
    ("End",),
    "done:",
    ("Display.Conversation", "King_Tyron", "Hail, hero of the Southlands! My hall, and my treasury, are always open to you.", "Thank you.", "@bye"),
    "bye:",
    ("End",),
]

S["Kill Hobgoblin"] = [
    "// Run by the engine (Kill.NPC looks up Kill <Name>) whenever a hobgoblin dies",
    ("Get.Value", "ATTRIBUTE", "HobgoblinQuest", "Variable.1$"),
    (">Conditional", "$Variable.1=1", "@end"),
    ("Update.Attribute", "HobgoblinsSlain", "+1"),
    ("Get.Value", "ATTRIBUTE", "HobgoblinsSlain", "Variable.2$"),
    (">Conditional", "$Variable.2<5", "@enough"),
    ("Display.Message", "Yellow", "Hobgoblins slain for King Tyron: $Variable.2 of 5."),
    ("End",),
    "enough:",
    (">Conditional", "$Variable.2=5", "@end"),
    ("Display.Message", "Yellow", "That's five hobgoblins! Return to King Tyron for your reward."),
    "end:",
    ("End",),
]

# --- skills
S["Mine Ore_Rock"] = [
    (">Distance.From.Clicked.Tile", "40", "@far"),
    (">Got.Item", "Pickaxe", "1", "@nopick"),
    ("Display.Message", "Cyan", "You swing your pickaxe at the rock..."),
    ("Play.Sound", "DigHole"),
    ("Wait", "3"),
    ("Get.Value", "SKILL", "Mining", "Variable.1$"),
    (">Conditional", "($Variable.1+50)>$Random.Percent", "@fail"),
    ("Display.Message", "Yellow", "...and mine some iron ore!"),
    ("Give.Item", "Iron_Ore", "1"),
    ("Update.Skill", "Mining", "+0.1"),
    ("Change.Tile", "$Tile.under.Cursor.X,$Tile.under.Cursor.Y", "Ore_Rock002", "0", "30"),
    ("End",),
    "fail:",
    ("Display.Message", "DarkRed", "...but only chip the rock."),
    ("End",),
    "nopick:",
    ("Display.Message", "DarkRed", "You need a pickaxe!"),
    ("End",),
    "far:",
    ("Display.Message", "DarkRed", "You are too far away!"),
    ("End",),
]

S["Use Pickaxe With Ore_Rock"] = [("Goto.Script", "Mine Ore_Rock"), ("End",)]

S["Use Fishing_Rod With Water"] = [
    (">Distance.From.Cursor", "45", "@far"),
    ("Display.Message", "Cyan", "You cast your line into the water..."),
    ("Play.Sound", "Splash"),
    ("Wait", "4"),
    ("Get.Value", "SKILL", "Fishing", "Variable.1$"),
    (">Conditional", "($Variable.1+35)>$Random.Percent", "@fail"),
    ("Display.Message", "Yellow", "...and catch a fish!"),
    ("Give.Item", "Raw_Fish", "1"),
    ("Update.Skill", "Fishing", "+0.1"),
    ("End",),
    "fail:",
    ("Display.Message", "DarkRed", "...but nothing bites."),
    ("End",),
    "far:",
    ("Display.Message", "DarkRed", "You need to stand at the water's edge!"),
    ("End",),
]

S["Use Raw_Fish With Fire"] = [
    (">Distance.From.Clicked.Entity", "30", "@far"),
    ("Take.Item", "Raw_Fish", "1"),
    ("Display.Message", "Cyan", "You place the Raw Fish on the Fire.."),
    ("Play.Sound", "CookingFood"),
    ("Wait", "3"),
    ("Get.Value", "SKILL", "Cooking", "Variable.1$"),
    (">Conditional", "($Variable.1+40)>$Random.Percent", "@burn"),
    ("Display.Message", "Yellow", "..and cook it perfectly!"),
    ("Update.Skill", "Cooking", "+0.05"),
    ("Give.Item", "Cooked_Fish", "1"),
    ("End",),
    "burn:",
    ("Display.Message", "DarkRed", "..but accidentally burn it!"),
    ("Give.Item", "Burnt_Fish", "1"),
    ("End",),
    "far:",
    ("Display.Message", "DarkRed", "You are too far away!"),
    ("End",),
]

S["Drink Basic_Potion"] = [
    ("Take.Item", "Basic_Potion", "1"),
    ("Display.Message", "Cyan", "You drink the potion. It tastes of mint and mud."),
    ("Update.Skill", "Hitpoints", "+15"),
    ("Give.Item", "Empty_Vial", "1"),
    ("End",),
]

for (m, tx, ty), text in NOTICES.items():
    S[notice_script_name(m, tx, ty)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]


# ------------------------------------------------------------------------------------------- data
NEW_TILE_SECTIONS = [
    ("Sand001", [("Walkable.Data", "1" * 49), ("Examine.Info", "Soft golden sand.")]),
    ("Dirt001", [("Walkable.Data", "1" * 49)]),
    ("Cave_Floor001", [("Walkable.Data", "1" * 49)]),
    ("Cave_Wall001", [("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Examine.Info", "Solid rock."),
                      ("Line.of.Sight", "0")]),
    ("Ore_Rock001", [("Walkable.Data", "1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111"),
                     ("Show.Name", "1"), ("Use.Words", "Mine"), ("Examine.Info", "A rock streaked with iron ore.")]),
    ("Ore_Rock002", [("Walkable.Data", "1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111"),
                     ("Show.Name", "1"), ("Examine.Info", "This rock has been mined out. The ore may come back in time.")]),
    ("Stone_Wall001", [("Walkable.Data", "0" * 49), ("Line.of.Sight", "0")]),
    ("Forest001", [("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Examine.Info", "The trees grow too thickly to pass."),
                   ("Line.of.Sight", "0")]),
]

MINIMAP_COLOURS = {
    "Sand001": "208 186 132",
    "Dirt001": "126 92 56",
    "Cave_Floor001": "80 72 64",
    "Cave_Wall001": "58 52 47",
    "Ore_Rock001": "176 100 52",
    "Ore_Rock002": "92 88 84",
    "Stone_Wall001": "120 120 120",
    "Forest001": "44 74 19",
}

# Keys to set in Entities.ini (existing sections are updated, values overwritten)
ENTITY_KEYS = {
    "Woman": [("Use.Words", "Talk to"), ("Examine.Info", "The ferrywoman. She smells of salt and tar.")],
    "Baker": [("Use.Words", "Talk to"), ("Examine.Info", "The Ashford baker, dusted in flour.")],
    "Shopkeeper": [("Use.Words", "Talk to"), ("Examine.Info", "He runs the Ashford General Store.")],
    "Banker": [("Use.Words", "Talk to,Bank"), ("Examine.Info", "A very serious man with a very large ledger.")],
    "Blacksmith": [("Use.Words", "Talk to"), ("Examine.Info", "Arms like tree trunks. She works the forge.")],
    "Herbalist": [("Use.Words", "Talk to"), ("Examine.Info", "She knows every herb in the Southlands.")],
    "Farmer": [("Use.Words", "Talk to"), ("Examine.Info", "A farmer, worried about his chickens.")],
    "Miner": [("Use.Words", "Talk to"), ("Examine.Info", "Old Tom, the last miner in the iron mine.")],
    "Beggar": [("Use.Words", "Talk to"), ("Examine.Info", "A ragged old man. He looks like he has seen better days.")],
    "Wizard": [("Use.Words", "Talk to"), ("Examine.Info", "The court wizard. His hat is very pointy.")],
    "King_Tyron": [("Use.Words", "Talk to"), ("Examine.Info", "King Tyron, ruler of the Southlands.")],
    "Hobgoblin": [("Examine.Info", "A big, ugly hobgoblin. It looks tougher than a goblin."), ("Hitpoints", "15"),
                  ("Attack.Speed", "1.2"), ("Strength", "2"), ("Defence", "2"), ("Aggro.Range", "60"),
                  ("Weapon.Range", "0"), ("Movement.Speed", "1.5"), ("Aggressive", "1"), ("Respawn", "30"),
                  ("Drops", "Bones,1-1,100 Gold_Coin(s),2-6,60 Iron_Ore,1-1,25 Leather_Cap,1-1,4")],
    "Goblin": [("Examine.Info", "A nasty little goblin.")],
    "Chicken": [("Examine.Info", "Cluck.")],
    "Iron_Ore": [("Examine.Info", "A lump of iron ore. The blacksmith can smelt it."), ("Value", "3")],
    "Iron_Bar": [("Value", "8")],
    "Pickaxe": [("Value", "12")],
    "Fishing_Rod": [("Examine.Info", "Use it on water to catch fish."), ("Value", "6")],
    "Bait": [("Examine.Info", "Wriggly worms."), ("Stackable", "100"), ("Value", "1")],
    "Raw_Fish": [("Examine.Info", "A fresh fish. Cook it on a fire."), ("Value", "3")],
    "Cooked_Fish": [("Use.Words", "Eat"), ("Examine.Info", "Nicely cooked fish."), ("Value", "6"), ("Food.Value", "3")],
    "Burnt_Fish": [("Examine.Info", "Charcoal with fins.")],
    "Herb": [("Examine.Info", "A fragrant green herb. The herbalist could use this."), ("Stackable", "50"), ("Value", "3")],
    "Basic_Potion": [("Use.Words", "Drink"), ("Examine.Info", "A healing potion. Drink it to restore 15 hitpoints."), ("Value", "15")],
    "Empty_Vial": [("Examine.Info", "An empty glass vial."), ("Value", "2")],
    "Full_Vial": [("Examine.Info", "A vial of something murky. Better not drink it."), ("Value", "4")],
    "Bread": [("Value", "2")],
    "Egg": [("Use.Words", "Eat"), ("Examine.Info", "A fresh egg."), ("Food.Value", "1")],
    "Cabbage": [("Value", "1")],
    "Meat_Sandwich": [("Value", "8")],
    "Ruby": [("Examine.Info", "A beautiful red gem."), ("Value", "50")],
    "Beggars_House_Key": [("Examine.Info", "An old iron key: the beggar in Ashford lost the key to his house on "
                                           "the Isle. This must be it.")],
    "Raw_Meat": [("Examine.Info", "Raw meat. Cook it on a fire."), ("Value", "2")],
}

ITEM_RACKS = {
    "SHOP-Baker": [("Type", "Shop"), ("Buy.Rate", "1.2"), ("Sell.Rate", "0.6"), ("Specific", "1"),
                   ("Item1", "Bread,10"), ("Item2", "Meat_Sandwich,4"), ("Item3", "Cooked_Poultry,4"), ("Item4", "Egg,6")],
    "SHOP-Ashford": [("Type", "Shop"), ("Buy.Rate", "1.25"), ("Sell.Rate", "0.75"),
                     ("Item1", "Tinderbox,5"), ("Item2", "Bucket,5"), ("Item3", "Axe,2"), ("Item4", "Fishing_Rod,3"),
                     ("Item5", "Bait,50"), ("Item6", "Empty_Vial,10")],
    "SHOP-Smith": [("Type", "Shop"), ("Buy.Rate", "1.3"), ("Sell.Rate", "0.7"), ("Specific", "1"),
                   ("Item1", "Pickaxe,3"), ("Item2", "Axe,3"), ("Item3", "Iron_Bar,5"), ("Item4", "Iron_Ore,0")],
    "SHOP-Herbalist": [("Type", "Shop"), ("Buy.Rate", "1.2"), ("Sell.Rate", "0.8"), ("Specific", "1"),
                       ("Item1", "Basic_Potion,5"), ("Item2", "Empty_Vial,10"), ("Item3", "Herb,0")],
    "SHOP-Farm": [("Type", "Shop"), ("Buy.Rate", "1.2"), ("Sell.Rate", "0.6"), ("Specific", "1"),
                  ("Item1", "Cabbage,20"), ("Item2", "Egg,10"), ("Item3", "Raw_Poultry,5")],
}
# CRAFT-Smithing exists (empty); fill it: Product,ingredients,xp[,level]
SMITHING = [("Type", "Craft"), ("Skill", "Smithing"),
            ("Item1", "Iron_Bar,Iron_Ore 2,0.2"),
            ("Item2", "Axe,Iron_Bar 1 Logs 1,0.25"),
            ("Item3", "Pickaxe,Iron_Bar 2 Logs 1,0.3")]


# ------------------------------------------------------------------------------------------- content
# The caves, gathering, crafting, shops, more NPCs and the quests added on top of the Southlands are defined in
# build_content.py: it adds to MAPS, S, LEGEND, the data tables and the hooks above, and patches the original maps.
import build_content  # noqa: E402
build_content.extend(sys.modules[__name__])
NEW_MAPS = list(MAPS)


# ------------------------------------------------------------------------------------------- writers
def map_cells(rows, roofs):
    assert len(rows) == MAP_H, "need %d rows, got %d" % (MAP_H, len(rows))
    cells = []
    for y, r in enumerate(rows, 1):
        assert len(r) == MAP_W, "row %d is %d wide: %r" % (y, len(r), r)
        row = []
        for ch in r:
            assert ch in LEGEND, "unknown legend char %r in row %d" % (ch, y)
            row.append(LEGEND[ch])
        cells.append(row)
    auto_shore(cells)
    for hook in CELL_HOOKS:
        hook(cells)
    for roof in roofs:
        # (x1, y1, x2, y2, group[, material]): a village roof (villages.py) has eaves, a ridge and gable ends
        x1, y1, x2, y2, g = roof[:5]
        material = roof[5] if len(roof) > 5 else None
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if material:
                    import villages
                    name = villages.roof_piece(material, x, y, x1, y1, x2, y2)
                else:
                    name = "Roof001"
                cells[y - 1][x - 1] += "+Roof(%s.%02d)" % (name, g)
    for hook in ROOF_HOOKS:
        hook(cells)
    return cells


LANDISH = {"Grass001", "Weed001", "Stone001", "Stone002"}
# shore piece for a water cell by which two sides have land: (N/S, E/W) -> tile (Water002 has its land NE, etc.)
SHORE = {("N", "E"): "Water002", ("N", "W"): "Water005", ("S", "W"): "Water006", ("S", "E"): "Water008"}


def auto_shore(cells):
    """Round off coast corners: a Water001 cell (not on the map edge, so borders stay as drawn) with grass on
    exactly two adjacent sides (one N/S, one E/W) and water on the other two becomes the matching shore piece."""
    def land(x, y):
        return cells[y][x].split("+")[0] in LANDISH
    def water(x, y):
        return cells[y][x] == "Water001"
    out = [row[:] for row in cells]
    for y in range(1, MAP_H - 1):
        for x in range(1, MAP_W - 1):
            if cells[y][x] != "Water001":
                continue
            for (ns, ew), tile in SHORE.items():
                ny, oy = (y - 1, y + 1) if ns == "N" else (y + 1, y - 1)
                ex, ox = (x + 1, x - 1) if ew == "E" else (x - 1, x + 1)
                if land(x, ny) and land(ex, y) and water(x, oy) and water(ox, y) and land(ex, ny):
                    out[y][x] = tile
    cells[:] = out


def write_map(name, spec):
    assert name not in PROTECTED_MAPS, name
    cells = decor_cells(map_cells(spec["rows"], spec["roofs"]))      # (furniture, trees...: Floor+Decor(Name))
    lines = [":".join(r) for r in cells]
    for e in spec["entities"]:
        lines.append(entity_line(e))
    for t in spec.get("triggers", []):
        lines.append("\t".join(["Trigger"] + [str(v) for v in t]))
    for lk in spec.get("locks", []):
        lines.append("\t".join(["Lock"] + [str(v) for v in lk]))
    return write_generated(p("maps", name + ".txt"), lines)    # (not if you've edited the map since: common.GEN)


def convert_old_npc_lines():
    """The map files no builder writes whole (the original Isle maps, after build_content's patches, and maps\\Test):
    their old GoodNPC / BadNPC lines become NPC lines with that Attitude."""
    changed = []
    for folder, _, files in os.walk(p("maps")):
        for f in sorted(files):
            if not f.endswith(".txt") or (os.path.samefile(folder, p("maps")) and f[:-4] in MAPS):
                continue
            path = os.path.join(folder, f)
            lines = read_lines(path)
            new = lines[:MAP_H] + [npc_line_text(ln) for ln in lines[MAP_H:]]
            if new != lines and write_lines(path, new):
                changed.append(os.path.relpath(path, p()))
    return changed


def script_lines(steps):
    labels, n = {}, 0
    for s in steps:
        if isinstance(s, str) and s.endswith(":") and not s.startswith("//"):
            labels[s[:-1]] = n + 1
        elif isinstance(s, tuple):
            n += 1
    out, n = [], 0
    for s in steps:
        if isinstance(s, str):
            if s.startswith("//"):
                out.append(s)
            continue
        n += 1
        args = []
        for a in s[1:]:
            if a.startswith("@"):
                a = "%02d" % labels[a[1:]]
            args.append(a if a != "" else " ")
        out.append("\t".join(["%02d" % n, s[0]] + args))
    comments = [l for l in out if l.startswith("//")]
    return comments + [l for l in out if not l.startswith("//")]


def update_data():
    changed = []
    ini = Ini(p("data", "Tiles.ini"))
    for sec, keys in NEW_TILE_SECTIONS:
        for k, v in keys:
            ini.set(sec, k, v)
    if ini.save(p("data", "Tiles.ini")):
        changed.append("data\\Tiles.ini")

    ini = Ini(p("data", "Entities.ini"))
    for sec, keys in ENTITY_KEYS.items():
        assert ini.section(sec) is not None, sec
        for k, v in keys:
            ini.set(sec, k, v)
    if ini.save(p("data", "Entities.ini")):
        changed.append("data\\Entities.ini")

    ini = Ini(p("data", "ItemRacks.ini"))
    ini.replace_section("CRAFT-Smithing", list(SMITHING))
    for sec, keys in ITEM_RACKS.items():
        ini.replace_section(sec, list(keys))
    if ini.save(p("data", "ItemRacks.ini")):
        changed.append("data\\ItemRacks.ini")

    path = p("dev", "Minimap Colours.txt")
    lines = [l for l in read_lines(path) if l.strip()]
    have = {l.split("\t")[0] for l in lines}
    for name, col in MINIMAP_COLOURS.items():
        if name not in have:
            lines.append("%s\t%s" % (name, col))
    if write_lines(path, lines):
        changed.append("dev\\Minimap Colours.txt")
    return changed


# ------------------------------------------------------------------------------------------- checks
_tiles_ini = None
_map_cache = {}


def walk_data(tile):
    global _tiles_ini
    if _tiles_ini is None:
        _tiles_ini = Ini(p("data", "Tiles.ini"))
    if tile in DECOR_MAP:                   # (split into a floor and its decor: walkable where both are)
        floor, decor = DECOR_MAP[tile]
        f = _tiles_ini.get(floor, "Walkable.Data", "1" * 49)
        d = _tiles_ini.get(decor, "Walkable.Data", "1" * 49)
        return "".join("1" if a == "1" and b == "1" else "0" for a, b in zip(f, d))
    return _tiles_ini.get(tile, "Walkable.Data", "1" * 49)


def load_cells(name):
    if name not in _map_cache:
        path = p("maps", name + ".txt")
        if not os.path.exists(path):
            _map_cache[name] = None
        else:
            rows = read_lines(path)[:MAP_H]
            _map_cache[name] = [[built_base(c) for c in r.split(":")] for r in rows]      # (decor: as the old tiles)
    return _map_cache[name]


def walkable(name, x, y):
    cells = load_cells(name)
    if cells is None or x < 0 or y < 0 or x >= MAP_W * 32 or y >= MAP_H * 32:
        return False
    tx, ty = int(x // 32), int(y // 32)
    d = walk_data(cells[ty][tx])
    sx, sy = int((x - tx * 32) / 32 * 7), int((y - ty * 32) / 32 * 7)
    return d[sy * 7 + sx] == "1"


def parse_name(n):
    return tuple(int(v) for v in n.split(","))


def all_maps():
    return sorted(f[:-4] for f in os.listdir(p("maps")) if re.fullmatch(r"-?\d+,-?\d+,-?\d+\.txt", f))


def check_entities(problems):
    for name in NEW_MAPS:
        if not GEN.untouched(p("maps", name + ".txt")):
            continue                    # (a map you've edited: the build didn't write it, its own things are checked by validate.py)
        for e in MAPS[name]["entities"]:
            kind, ent, x, y = e[:4]
            if kind == "Id":
                continue                        # (a named tile, not a thing)
            if ent in getattr(sys.modules[__name__], "WATER_ENTITIES", ()):
                continue                        # (fishing spots float on the water)
            from render_maps import sprite
            spr = sprite("Entities", ent)
            w, h = (spr[0], spr[1]) if spr else (32, 32)
            fx, fy = x + w / 2, y + h - 1
            cx, cy = x + w / 2, y + h / 2
            if not walkable(name, fx, fy):
                problems.append("%s: %s %s feet at %d,%d (tile %d,%d) are on unwalkable ground"
                                % (name, kind, ent, fx, fy, fx // 32 + 1, fy // 32 + 1))
            if kind in ("GoodNPC", "BadNPC") and not walkable(name, cx, cy):
                problems.append("%s: %s %s centre (tile %d,%d) is on unwalkable ground" % (name, kind, ent, cx // 32 + 1, cy // 32 + 1))


def check_edges(problems, report):
    names = set(all_maps())
    W, H = MAP_W * 32, MAP_H * 32
    for n in sorted(names):
        x, y, z = parse_name(n)
        east, south = "%d,%d,%d" % (x + 1, y, z), "%d,%d,%d" % (x, y + 1, z)
        if n in SEAMLESS_MAPS:
            east = east if east not in SEAMLESS_MAPS else None
            south = south if south not in SEAMLESS_MAPS else None
        if east in names and (n in MAPS or east in MAPS):
            ok, bad1, bad2 = [], [], []
            for fy in range(16, H, 2):
                a_out, b_in = walkable(n, W - 1, fy), walkable(east, 1, fy)
                b_out, a_in = walkable(east, 0, fy), walkable(n, W - 2, fy)
                if a_out and not b_in:
                    bad1.append(fy // 32 + 1)
                if b_out and not a_in:
                    bad2.append(fy // 32 + 1)
                if a_out and b_in:
                    ok.append(fy // 32 + 1)
            if bad1:
                problems.append("%s -> %s (east): walk off at rows %s but arrive on unwalkable ground" % (n, east, spans(bad1)))
            if bad2:
                problems.append("%s -> %s (west): walk off at rows %s but arrive on unwalkable ground" % (east, n, spans(bad2)))
            report.append("%s <-> %s: crossable at rows %s" % (n, east, spans(ok)))
        if south in names and (n in MAPS or south in MAPS):
            ok, bad1, bad2 = [], [], []
            for fx in range(0, W, 2):
                a_out, b_in = walkable(n, fx, H - 1), walkable(south, fx, 18)
                b_out, a_in = walkable(south, fx, 15), walkable(n, fx, H - 2)
                if a_out and not b_in:
                    bad1.append(fx // 32 + 1)
                if b_out and not a_in:
                    bad2.append(fx // 32 + 1)
                if a_out and b_in:
                    ok.append(fx // 32 + 1)
            if bad1:
                problems.append("%s -> %s (south): walk off at columns %s but arrive on unwalkable ground" % (n, south, spans(bad1)))
            if bad2:
                problems.append("%s -> %s (north): walk off at columns %s but arrive on unwalkable ground" % (south, n, spans(bad2)))
            report.append("%s <-> %s: crossable at columns %s" % (n, south, spans(ok)))


def spans(nums):
    nums = sorted(set(nums))
    if not nums:
        return "(none)"
    out, start, prev = [], nums[0], nums[0]
    for v in nums[1:] + [None]:
        if v is not None and v == prev + 1:
            prev = v
            continue
        out.append(str(start) if start == prev else "%d-%d" % (start, prev))
        if v is not None:
            start = prev = v
    return ",".join(out)


# (LADDER_DIR and LADDER_SPECIAL are defined with the legend, at the top)


def check_ladders(problems, report):
    names = set(all_maps())
    for n in sorted(names):
        cells = load_cells(n)
        x, y, z = parse_name(n)
        for ty, row in enumerate(cells, 1):
            for tx, t in enumerate(row, 1):
                if t not in LADDER_DIR:
                    continue
                target = LADDER_SPECIAL.get((n, t), "%d,%d,%d" % (x, y, z + LADDER_DIR[t]))
                if target not in names:
                    if n in MAPS:
                        problems.append("%s: %s at %d,%d leads to missing map %s" % (n, t, tx, ty, target))
                    continue
                other = load_cells(target)[ty - 1][tx - 1]
                want = sorted(k for k, v in LADDER_DIR.items() if v == -LADDER_DIR[t])
                if other not in want:
                    problems.append("%s: %s at %d,%d -> %s has %s there (want %s)" % (n, t, tx, ty, target, other, " or ".join(want)))
                bad = 0
                for py in range((ty - 2) * 32, (ty + 1) * 32, 4):
                    for px in range((tx - 2) * 32, (tx + 1) * 32, 4):
                        if walkable(n, px, py) and not walkable(target, px, py):
                            bad += 1
                if bad:
                    problems.append("%s: around %s at %d,%d, %d walkable spots are unwalkable in %s" % (n, t, tx, ty, bad, target))
                report.append("%s %s at tile %d,%d -> %s" % (n, t, tx, ty, target))


def check_scripts_exist(problems):
    sdir = p("data", "Scripts")
    for name in NEW_MAPS:
        for e in MAPS[name]["entities"]:
            if e[1] == "Notice":
                nid = e[4][3:] if len(e) > 4 and str(e[4]).startswith("Id=") else ""
                sn = ("Read " + nid) if nid else "Read Notice%s-%d,%d" % (name, e[2], e[3])
                if not os.path.exists(os.path.join(sdir, sn + ".txt")):
                    problems.append("missing notice script " + sn)
            if e[0] in ("GoodNPC", "NPC") and not os.path.exists(os.path.join(sdir, "Talk to %s.txt" % e[1])):
                problems.append("missing Talk to %s" % e[1])


def wrap_text(text, width=48):
    """wrap_text in dragonsword\\lb.py: a backslash is a line break, and a space at or past width chars breaks the line."""
    out, n = "", 0
    for c in text.replace("\\", "|"):
        if c == "|":
            n = 0
        if c == " " and n >= width:
            c, n = "|", 0
        elif c != "|":
            n += 1
        out += c
    return out.split("|")


def check_conversations(problems):
    """The conversation box shows at most 8 lines (about 56 characters each) of the wrapped message."""
    for sname, steps in S.items():
        for st in steps:
            if isinstance(st, tuple) and st[0] == "Display.Conversation":
                lines = wrap_text(st[2])
                if len(lines) > 8 or max(len(l) for l in lines) > 56 or "" in lines:
                    problems.append("%s: conversation text wraps to %d lines (longest %d chars): %r"
                                    % (sname, len(lines), max(len(l) for l in lines), st[2][:40]))


def check_teleports(problems, report):
    """Teleport X,Y is the player's top-left (32x32 sprite), so the feet are at X+16, Y+31."""
    for sname, steps in S.items():
        for st in steps:
            if isinstance(st, tuple) and st[0] == "Teleport" and "$" not in st[1] + st[2]:
                m = st[2]
                if "," in st[1]:
                    x, y = (int(v) for v in st[1].split(","))
                else:                                   # a place's name (build_places)
                    import build_places as PL
                    if st[1] not in PL.PLACES:
                        problems.append("%s: Teleport to %s, which isn't a place" % (sname, st[1]))
                        continue
                    pm, x, y = PL.pixels(st[1])
                    m = m if m not in ("", "-") else pm
                ok = walkable(m, x + 16, y + 31)
                report.append("%s: Teleport to %s feet %d,%d %s" % (sname, m, x + 16, y + 31, "ok" if ok else "BLOCKED"))
                if not ok:
                    problems.append("%s: Teleport lands on unwalkable ground in %s" % (sname, m))


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import story_kit as K
    if K.new_mainland():
        sys.exit("Superseded: build_estforlan.py rebuilt the mainland. This one would put back the old mainland's maps.")
    GEN.enable()            # what you've changed in the editors since the last build is kept (common.Generated)
    changed = []
    import build_places as PL                   # the named places' Id lines: in the maps the build writes whole...
    for pid, (m, tx, ty) in sorted(PL.PLACES.items()):
        if m in NEW_MAPS:
            MAPS[m]["entities"].append(("Id", pid, tx, ty))
    for name in NEW_MAPS:
        if write_map(name, MAPS[name]):
            changed.append("maps\\%s.txt" % name)
    # upper floors (level 1) a rebuild no longer makes (the village houses moved), unless you've edited them since
    for f in os.listdir(p("maps")):
        if re.fullmatch(r"-?\d+,-?\d+,1\.txt", f) and f[:-4] not in MAPS and GEN.untouched(p("maps", f)):
            os.remove(p("maps", f))
            GEN.forget(p("maps", f))
            changed.append("removed maps\\" + f)
    # notice scripts from an earlier run whose notice has since moved
    for f in os.listdir(p("data", "Scripts")):
        if f.startswith("Read ") and f[:-4] not in S and GEN.untouched(p("data", "Scripts", f)):
            os.remove(p("data", "Scripts", f))          # a notice's script the build no longer makes (an old name)
            changed.append("removed data\\Scripts\\" + f)
            continue
        m = re.fullmatch(r"Read Notice(-?\d+,-?\d+,-?\d+)-\d+,\d+\.txt", f)
        if m and f[:-4] not in S and (m.group(1) in MAPS or m.group(1) == "1,2,0" or
                                      GEN.untouched(p("data", "Scripts", f))):
            os.remove(p("data", "Scripts", f))
            changed.append("removed data\\Scripts\\" + f)
    for sname, steps in S.items():
        if write_generated(p("data", "Scripts", sname + ".txt"), script_lines(steps)):
            changed.append("data\\Scripts\\%s.txt" % sname)
    changed += update_data()
    for step in EXTRA_STEPS:
        changed += step()
    changed += PL.write_ids()                   # ...and in the others (the original maps, the ones you've edited)
    changed += convert_old_npc_lines()
    for c in changed:
        print("wrote", c)
    print("%d file(s) changed" % len(changed))
    GEN.report()
    GEN.save()

    problems, report = [], []
    check_entities(problems)
    check_edges(problems, report)
    check_ladders(problems, report)
    check_scripts_exist(problems)
    check_conversations(problems)
    check_teleports(problems, report)
    for chk in EXTRA_CHECKS:
        chk(problems, report)
    print("\nConnections:")
    for r in report:
        print("  " + r)
    print("\n%d problem(s)" % len(problems))
    for pr in problems:
        print("  PROBLEM " + pr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
