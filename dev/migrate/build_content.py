"""Content for Dragon Sword v2 on top of the Southlands: caves, more NPCs and monsters, items, gathering,
crafting, shops and quests.

Not run on its own: build_world.py imports it and calls extend() (so `python -I "dev\\migrate\\build_world.py"`
builds everything, and running it again rewrites only what changed). Order of the whole build:
    python -I "dev\\migrate\\build_tiles.py"      tile sprites (cave set, ores, berries, wheat, nests, ladders)
    python -I "dev\\migrate\\build_sprites.py"    entity sprites (items, stations, NPCs, monsters)
    python -I "dev\\migrate\\build_people.py"     people and goblins on the player's body
    python -I "dev\\migrate\\build_walk.py"       NPC walking frames (sprites\\Walk)
    python -I "dev\\migrate\\build_worn.py"       worn equipment drawn over the player (sprites\\Worn)
    python -I "dev\\migrate\\build_effects.py"    combat and spell effects (sprites\\Effects)
    python -I "dev\\migrate\\build_sounds.py"     combat and spell sounds (Sounds)
    python -I "dev\\migrate\\build_world.py"      maps, scripts, data\\*.ini (this file is part of it)
    python -I "dev\\migrate\\build_minimaps.py"   minimaps
    python -I "dev\\migrate\\render_maps.py" <maps>   renders in dev\\Renders
    python -I "dev\\migrate\\validate.py"         checks everything

What it does to existing hand data (so re-running never clobbers it unexpectedly):
  * The 13 original island maps are only patched: single tiles (old -> new, only if the cell still has the old
    tile) and added entity lines. Every patch is recorded in dev\\migrate\\content_patches.txt so a later run can
    undo patches that were removed from PATCHES here; nothing else in those files is touched.
  * Entities.ini / Tiles.ini: the keys listed here are set; other keys and sections are left alone.
  * ItemRacks.ini: new racks are written in full; for the existing racks (SHOP-General, SHOP-Smith...) items are
    only appended when missing (stock of existing rows is left alone).
  * Config.ini: only [Skills] List is changed (Potion Making and Crafting appended if missing).
  * Gathering.ini / Quests.ini are generated from GATHERING / QUESTS; sections there that aren't in those tables
    (hand-written ones) are kept.
"""
import build_places as PL
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAP_W, MAP_H, Ini, p, read_lines, write_lines, read_bmp, built_cell, built_base, decor_cells

W = None      # the build_world module, set by extend()

# =========================================================================================== legend
CAVE_LEGEND = {
    "f": "CAVEFLOOR",        # cave floor: Cave_Floor001/002/003 picked per cell by dress()
    "g": "Cave_Floor002",    # gravel
    "m": "Cave_Floor003",    # damp, mossy
    "X": "Cave_Wall001",     # rock (dress() turns it into the Cave_Wall002 face when open ground is south of it)
    "Z": "Cave_Wall003",     # rock face with a burning torch
    "r": "Cave_Rubble001",
    "A": "Stalagmite001",
    "w": "Cave_Pool001",     # deep water (fishing: cave eels)
    "q": "Cave_Puddle001",
    "M": "Mushroom_Patch001",
    "R": "Ore_Rock001",      # iron
    "C": "Copper_Rock001",
    "L": "Coal_Rock001",
    "N": "Gold_Rock001",
    "G": "Gem_Rock001",
    "I": "Tin_Rock001",
    "Q": "Silver_Rock001",
    "z": "Mithril_Rock001",
    "a": "Oak_Tree001",
    "e": "Willow_Tree001",
    "j": "Yew_Tree001",
    "i": "Mine_Track001",    # rails running north-south
    "h": "Mine_Track002",    # rails running east-west
    "J": "Mine_Support001",
    "^": "Ladder004",        # cave ladder: Climb Up
    "V": "Ladder005",        # cave hatch: Climb Down
    "!": "Ladder007",        # hole in the dirt: Climb Down
    "B": "Berry_Bush001",
    "E": "Herb_Patch001",
    "y": "Field001",         # ploughed earth: the wheat plants on it are entities (wheat_field below)
    "n": "Nest001",
}

WALLS = {"Cave_Wall001", "Cave_Wall002", "Cave_Wall003", "Black001", "Brick001", "Brick002", "Stone_Wall001",
         "Forest001"}
DAMP_NEAR = {"Cave_Pool001", "Cave_Puddle001", "Mushroom_Patch001", "Mushroom_Patch002"}


def dress(cells):
    """Cave dressing: rock with open ground south of it shows its face (Cave_Wall002); plain cave floor gets
    a deterministic mix of the three floor variants, damp next to water and mushrooms."""
    H, Wd = len(cells), len(cells[0])
    base = [[c.split("+")[0] for c in row] for row in cells]
    sig = zlib.crc32(("|".join(":".join(r) for r in base)).encode())
    for y in range(H):
        for x in range(Wd):
            b = base[y][x]
            if b == "Cave_Wall001" and y + 1 < H and base[y + 1][x] not in WALLS and not base[y + 1][x].startswith("Water"):
                cells[y][x] = cells[y][x].replace("Cave_Wall001", "Cave_Wall002", 1)
            elif b == "CAVEFLOOR":
                near = {base[yy][xx] for yy in range(max(0, y - 1), min(H, y + 2)) for xx in range(max(0, x - 1), min(Wd, x + 2))}
                v = zlib.crc32(("%d,%d,%d" % (x, y, sig)).encode()) % 100
                t = "Cave_Floor003" if near & DAMP_NEAR else "Cave_Floor001" if v < 64 else "Cave_Floor002" if v < 86 else "Cave_Floor003"
                cells[y][x] = cells[y][x].replace("CAVEFLOOR", t, 1)


# =========================================================================================== cave maps
def cave_maps():
    npc, item, obj = W.npc, W.item, W.obj
    M = {}

    # 1,1,-1  The beggar's cellar (under his house on the Isle). Its south-west wall has fallen into a grotto
    # with rats, mushrooms, copper and coal. East to 2,1,-1. Ladder up at 21,4 to the house (1,1,0).
    M["1,1,-1"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKK#####KKK",
            "KKKKKKKKKKKKKKKKK#__U#KKK",
            "KKKKKKKKKKKKKKKKK#___#KKK",
            "KKKKKKKKKKKKKKKKK#___#KKK",
            "KKKKKKKKXXXXXXXXX#r###KKK",
            "KKKKKKXXXffMffffXrrXXKKKK",
            "KKKKKXXfffqfffffffffXKKKK",
            "KKKKXXfffffXXXXfffffAXXKK",
            "KKKXXffCffXXKKXXfffffffXX",
            "KKKXffffffXKKKKXXffffffff",
            "KKXXfLfffXXKKKKKXfrffffff",
            "KKXfffAffffXXXXXXffffffXX",
            "KKXXfffffffffffffffffXXKK",
            "KKKXXMffCffffffqfffffXKKK",
            "KKKKXXXffffffAffffMXXKKKK",
            "KKKKKKXXXXfffffLfXXXKKKKK",
            "KKKKKKKKKXXXXXXXXXKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            ("MapItem", "Axe", 580, 158, 1),          # (from the original room)
            ("BadNPC", "Goblin", 580, 160),
            npc("BadNPC", "Rat", 9, 9),
            npc("BadNPC", "Rat", 8, 14),
            npc("BadNPC", "Rat", 17, 15),
            npc("BadNPC", "Bat", 13, 16),
            item("Bones", 12, 15),
            item("Bones", 20, 13),
            item("Empty_Vial", 18, 9),
        ],
    )

    # 2,1,-1  The eastern grotto: a black pool (cave eels), iron, mushrooms, bats and spiders.
    # The hole under the cliff in 2,1,0 (tile 20,10) comes down the ladder at 20,10.
    M["2,1,-1"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKXXXXXXXKKKKKKKKKKK",
            "KKKKKKXXwwwwwXXKKXXXXXXKK",
            "KKKKKXXwwwwwwwXXXXffffXXK",
            "KKKKXXmwwwwwwwmfffffAffXK",
            "KKKXXffmwwwwwmmffRXffffXK",
            "KKKXfffffmmmfffffXffffXXK",
            "KKXXffAfffffffXXXXf^fffXK",
            "KXXfffffMffffXXKKXfffffXK",
            "fffffRffffffXXKKKXfffRfXK",
            "fffffffXXfffffXXXXfffffXK",
            "XXXXfffXXXffffffffffffXKK",
            "KKKXXfffffffAffMfffffXXKK",
            "KKKKXXXfffffffffffXXXXKKK",
            "KKKKKKXXXXfffqfffXXKKKKKK",
            "KKKKKKKKKXXXXXXXXXKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            npc("BadNPC", "Bat", 10, 9),
            npc("BadNPC", "Bat", 19, 7),
            npc("BadNPC", "Giant_Spider", 13, 14),
            npc("BadNPC", "Giant_Spider", 21, 13),
            npc("BadNPC", "Rat", 5, 12),
            item("Bones", 16, 9),
            item("Gold_Coin(s)", 7, 15, 4),
        ],
    )

    # 1,4,-1  The old iron mine (redone): rails from the ladder to the tunnel east, supports, a cart, torches,
    # and a new southern gallery with copper, mushrooms and puddles. Ladder up at 7,8 (to 1,4,0); tunnel east
    # at rows 10-11 (to 2,4,-1).
    M["1,4,-1"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKXXXXXXXXKKKKKKKKKKKKK",
            "KKKXXffgfRfXXXXXXKKKKKKKK",
            "KKXXfffffffffZfffXXKKKKKK",
            "KKXCffffffffffffffffXKKKK",
            "KXXffXXXXffffJfffffffXXKK",
            "KXRfff^hhhhhhhhhhhhhhffXK",
            "KXXffffffffffffffffffiffX",
            "KKXXffRffXXXXXXXXXXffiJff",
            "KKKXffffXXKKKKKKKKXffhhhh",
            "KKKXmffXXKKKKKKKKKXffffXX",
            "KKXXMqffXXKKKKKKKXXffffXK",
            "KKXffffffXXXXXXXXXfffrfXK",
            "KKXffCffffffJfffffffffXKK",
            "KKXXffAffffffffqffffMXXKK",
            "KKKXXfffMffffCfffAffXXKKK",
            "KKKKXXXmmMfffffffffXXKKKK",
            "KKKKKKXXXXXXXXXXXXXXKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            npc("GoodNPC", "Miner", 10, 6),
            item("Pickaxe", 5, 6),
            item("Iron_Ore", 4, 7),
            item("Iron_Ore", 20, 12),
            obj("Mine_Cart", 20, 8),
            npc("BadNPC", "Hobgoblin", 21, 13),
            npc("BadNPC", "Rat", 9, 15),
            npc("BadNPC", "Rat", 16, 17),
            npc("BadNPC", "Bat", 5, 13),
            item("Bones", 16, 15),
        ],
    )

    # 2,4,-1  Mine depths: hobgoblin tunnels with coal and iron, giant spider webs in the south. Tunnel west at
    # rows 10-11 (to 1,4,-1); the hatch at 20,6 goes down to the warren (2,4,-2). North-west, behind the mining
    # guild's door at 7,8 (a Lock: Mining 10), the deep seam: coal, iron and a gold rock.
    M["2,4,-1"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKXXXXZXXXKKKKKKKKKKKKKK",
            "KKXXffLfffXXKKKKKKKKKKKKK",
            "KXXfffffNfXKKKKXXXZXXXKKK",
            "KXRffAfffLXKKKXXffffffXXK",
            "KXXffffffXXKKXXLfffVfLXKK",
            "KKXXffffXXKKXXffffffffffX",
            "KKKKXXDXXKKXXffRffffAffXK",
            "KKKXXfffXXXXfffffffffXXKK",
            "hhhhhhhhhhhhhhhhfffffXKKK",
            "ffffffffffffffffffffXXKKK",
            "KKXXffLffXXXfffffffffXKKK",
            "KKKXXfffXXKXXffffffffXXKK",
            "KKKKXXrXXKKXXfffAffffMXKK",
            "KKKKKXfXKKXXmmfffffqfffXK",
            "KKKKXXffXXXmmMfffffffAfXK",
            "KKKXXfffffffffRffffLffXXK",
            "KKKXffAffffffffffffXXXKKK",
            "KKKXXXXXXXXXXXXXXXXXKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            npc("BadNPC", "Hobgoblin", 10, 11),
            npc("BadNPC", "Hobgoblin", 16, 12),
            npc("BadNPC", "Hobgoblin", 18, 8),
            npc("BadNPC", "Giant_Spider", 15, 16),
            npc("BadNPC", "Giant_Spider", 9, 18),
            npc("BadNPC", "Giant_Spider", 21, 17),
            npc("BadNPC", "Bat", 6, 10),
            item("Iron_Ore", 5, 12),
            item("Bones", 12, 10),
            item("Bones", 17, 15),
            item("Spider_Silk", 7, 17),
            obj("Notice", 6, 9),
        ],
        locks=[(7, 8, "$Skill.Mining>=10", "You need to be able to mine at level 10 to enter the deep seam.")],
    )

    # 2,4,-2  The hobgoblin warren: bones, rubble and stalagmites, hobgoblins and the first skeletons.
    # Ladder up at 20,6 (to 2,4,-1); a hatch at 5,12 goes down to the Deep Hollow (2,4,-3).
    M["2,4,-2"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKXXXXXXXXKK",
            "KKKKKKKXXXXXXXXXfffffffXK",
            "KKKKKKXXffrffffffff^fffXK",
            "KKKKKXXfffffffffffffffffX",
            "KKKKXXffffRffffAfffffrffX",
            "KKKXXfffffffXXffffffffffX",
            "KKKXffAfffXXXXXffffffRffX",
            "KKXfffffffXXXXXfffffffffX",
            "KKXfVfffffffrfffAfffffXXX",
            "KKXffffffffffffffffffXXKK",
            "KKXXffffrfffffffffffXXKKK",
            "KKKXXfffffffAffffffXXKKKK",
            "KKKKXXXfffffffffffXXKKKKK",
            "KKKKKKXXXXXXXXXXXXXKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            npc("BadNPC", "Hobgoblin", 10, 7),
            npc("BadNPC", "Hobgoblin", 17, 9),
            npc("BadNPC", "Hobgoblin", 9, 14),
            npc("BadNPC", "Hobgoblin", 15, 13),
            npc("BadNPC", "Hobgoblin", 20, 11),
            npc("BadNPC", "Skeleton", 6, 9),
            item("Beggars_House_Key", 5, 14),
            item("Ruby", 9, 16),
            item("Gold_Coin(s)", 12, 6, 25),
            item("Basic_Potion", 22, 12),
            item("Bones", 16, 10), item("Bones", 8, 10), item("Bones", 14, 15), item("Bones", 21, 8),
        ],
    )

    # 2,4,-3  The Deep Hollow (new): Brokk the dwarf's torch-lit hall with a forge, the crystal cavern (gems and
    # gold), an underground lake (cave eels, mushrooms), skeletons and the cave troll's lair. Ladder up at 5,12.
    # West of the hall, behind the door at 6,5 (a Lock: open once the Dwarf's Grudge is done), Brokk's vault.
    M["2,4,-3"] = dict(
        rows=[
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKXXXXXXXXXXXKKKKKKK",
            "KXXXXXXXZXXXZXXXZXXXXXXKK",
            "KXfffXXgggggggggggXXGfXXK",
            "KXfffDggggggggggggXffffXK",
            "KXGffXgggggggggggggfGNffX",
            "KXXXXJggggggggggggXffffAX",
            "KKXXfffXXXggggXXXXXfNfffX",
            "KXXffffXKXXggXXKKKXfffGXX",
            "KXfffAffXKXffXXKKXXffNffX",
            "KXffffffXXXffXXXXXfffffXX",
            "KXff^ffffffffffffffAfffXK",
            "KXXfffffffffffffffffffXXK",
            "KKXXfffMXXmmmmmmXXrfffffX",
            "KKKXXfmmmwwwwwmmmXrrffAfX",
            "KKKKXmmwwwwwwwwmmffffrffX",
            "KKKKXXmmwwwwwwmmXXfrfffXX",
            "KKKKKXXmmMmmmMmXXXffffXXK",
            "KKKKKKXXXXXXXXXXKXXXXXXKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
            "KKKKKKKKKKKKKKKKKKKKKKKKK",
        ],
        roofs=[],
        entities=[
            npc("GoodNPC", "Dwarf", 12, 5),
            obj("Furnace", 8, 4),
            obj("Anvil", 10, 4),
            obj("Workbench", 15, 4),
            obj("Fire", 13, 7),
            npc("BadNPC", "Skeleton", 22, 5),
            npc("BadNPC", "Skeleton", 21, 9),
            npc("BadNPC", "Skeleton", 4, 10),
            npc("BadNPC", "Skeleton", 16, 13),
            npc("BadNPC", "Skeleton", 6, 16),
            npc("BadNPC", "Cave_Troll", 21, 16),
            npc("BadNPC", "Bat", 11, 12),
            item("Bones", 20, 15), item("Bones", 23, 17), item("Bones", 19, 18),
            item("Gold_Coin(s)", 22, 18, 30),
            item("Super_Potion", 3, 12),
            obj("Chest", 4, 4),
        ],
        locks=[(6, 5, "$Attr.DwarfQuest>=2", "Brokk's vault. The door is barred, and Brokk only opens it for a friend of the deep.")],
    )
    return M


# Tin, silver and mithril rocks, put into the caves above: map -> [(tile x, tile y, legend letter)], 1-based.
# Each must land on plain cave floor (checked), off the paths.
ORE_ROCKS = {
    "1,1,-1": [(7, 12, "I"), (11, 16, "I")],                   # tin by the copper in the cellar grotto
    "1,4,-1": [(5, 15, "I"), (19, 16, "I")],                   # tin by the copper in the old mine's south gallery
    "2,4,-1": [(8, 5, "Q"), (11, 17, "Q")],                    # silver in the guild's deep seam and the spider tunnels
    "2,4,-2": [(8, 8, "Q"), (19, 13, "Q")],                    # silver in the hobgoblin warren
    "2,4,-3": [(24, 16, "z"), (20, 14, "z"), (3, 4, "z")],     # mithril in the cave troll's lair and Brokk's vault
}


def place_ores(maps):
    for name, rocks in ORE_ROCKS.items():
        rows = maps[name]["rows"]
        for x, y, ch in rocks:
            assert rows[y - 1][x - 1] in "fgm", (name, x, y, rows[y - 1][x - 1])
        maps[name]["rows"] = set_cells(rows, rocks)


# Better trees on the Southlands maps (made here, so it's the same every build): some ordinary trees become
# willows (by the water), oaks or rare yews. map -> (oak %, willow % of trees near water, yew %)
TREE_MIX = {"1,3,0": (30, 50, 0), "2,3,0": (40, 60, 0), "3,3,0": (40, 60, 0), "1,4,0": (25, 50, 7),
            "2,4,0": (40, 0, 0), "3,4,0": (25, 50, 9)}
WATER_CHARS = set("~1379")
# ... and on the original Isle maps (patched): (x, y, old tile, new tile)
ISLE_TREES = {"0,1,0": [(11, 9, "Tree001", "Oak_Tree001"), (12, 12, "Tree001", "Oak_Tree001"),
                        (16, 13, "Tree001", "Oak_Tree001"), (8, 8, "Tree001", "Willow_Tree001")],
              "2,1,0": [(13, 5, "Tree001", "Oak_Tree001"), (16, 15, "Tree001", "Oak_Tree001")],
              "1,1,0": [(5, 17, "Tree002", "Willow_Tree001")]}


def place_trees(maps):
    report = {}
    for name, (oak, willow, yew) in TREE_MIX.items():
        rows = maps[name]["rows"]
        changes = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in "Tt":
                    continue
                v = zlib.crc32(("%s:%d,%d" % (name, x, y)).encode()) % 100
                wet = any(rows[yy][xx] in WATER_CHARS for yy in range(max(0, y - 2), min(len(rows), y + 3))
                          for xx in range(max(0, x - 2), min(len(row), x + 3)))
                if wet and v < willow:
                    changes.append((x + 1, y + 1, "e"))
                elif not wet and v < yew:
                    changes.append((x + 1, y + 1, "j"))
                elif v >= 100 - oak:
                    changes.append((x + 1, y + 1, "a"))
        maps[name]["rows"] = set_cells(rows, changes)
        report[name] = changes
    return report


# =========================================================================================== surface changes
def set_cells(rows, changes):
    rows = [list(r) for r in rows]
    for tx, ty, ch in changes:
        rows[ty - 1][tx - 1] = ch
    return ["".join(r) for r in rows]


def surface_changes():
    """New things on the Southlands maps that build_world.py already defines (tiles and entities)."""
    npc, item, obj = W.npc, W.item, W.obj
    M = W.MAPS
    # Northgate: the fisherman in his hut, a villager, berry bushes and herb patches by the woods.
    m = M["1,3,0"]
    m["rows"] = set_cells(m["rows"], [(19, 18, "B"), (22, 20, "B"), (10, 19, "E"), (3, 11, "B")])
    m["entities"] += [npc("GoodNPC", "Fisherman", 5, 14), npc("GoodNPC", "Villager", 16, 13), npc("GoodNPC", "Dog", 9, 12),
                      npc("GoodNPC", "Man", 17, 9)]
    # Ashford: a range in the bakery, anvil and furnace in the smithy, a guard and villagers on the high street.
    m = M["2,3,0"]
    m["entities"] += [obj("Range", 4, 8), obj("Anvil", 20, 17), obj("Furnace", 22, 17),
                      npc("GoodNPC", "Guard", 13, 13), npc("GoodNPC", "Villager", 7, 13), npc("GoodNPC", "Villager", 21, 20),
                      npc("GoodNPC", "Dog", 17, 13)]
    m["rows"] = set_cells(m["rows"], [(2, 19, "B"), (11, 20, "E")])
    # Farmlands: a wheat field, nests by the farmhouse, cows and sheep, a workbench and the alchemy table.
    m = M["3,3,0"]
    m["rows"] = set_cells(m["rows"], [(x, 19, "y") for x in range(4, 12)] + [(x, 20, "y") for x in range(7, 12)] +
                          [(12, 8, "n"), (15, 9, "n"), (21, 20, "E"), (23, 13, "E"), (23, 21, "B")])
    m["entities"] += wheat_field([(x, 19) for x in range(4, 12)] + [(x, 20) for x in range(7, 12)], "farm")
    m["entities"] += [obj("Workbench", 4, 9), obj("Alchemy_Table", 21, 15),
                      npc("BadNPC", "Cow", 14, 15), npc("BadNPC", "Cow", 14, 18), npc("BadNPC", "Sheep", 9, 13),
                      npc("BadNPC", "Sheep", 6, 17), npc("GoodNPC", "Villager", 20, 12)]
    # Whispering Woods: wolves in the southern woods, berries and herbs; the hatch becomes a hole in the dirt.
    m = M["1,4,0"]
    m["rows"] = set_cells(m["rows"], [(7, 8, "!"), (16, 11, "B"), (21, 9, "B"), (5, 11, "E"), (14, 16, "E"),
                                      (3, 9, "B")])
    m["entities"] += [npc("BadNPC", "Wolf", 9, 15), npc("BadNPC", "Wolf", 15, 17), npc("BadNPC", "Wolf", 20, 14),
                      npc("GoodNPC", "Guard", 8, 11)]
    # the guard post at the gate of the yard round the mine hatch: body armour, or the King's commission. Once the
    # player has stood in the yard (triggers on its south row set MineGatePassed) the guard lets them through both
    # ways, so nobody who comes up the ladder without armour is shut in.
    m["locks"] = [(7, 10, "$Equipped.Body<>none or $Attr.HobgoblinQuest>=1 or $Attr.MineGatePassed>=1",
                   "The guard blocks the gate: no one goes down the mine without body armour, unless the King sent them.")]
    m["triggers"] = [("Mine Gate", x, 9) for x in (6, 7, 8)]
    # Tyron's Keep: guards at the gate and the hall, the quartermaster in the courtyard, and the royal treasury
    # (south of the courtyard, door 12,14: a Lock, open once King Tyron's hunt is done) with a chest.
    m = M["2,4,0"]
    m["entities"] += [npc("GoodNPC", "Guard", 8, 10), npc("GoodNPC", "Guard", 14, 11), npc("GoodNPC", "Quartermaster", 10, 13),
                      obj("Notice", 14, 13), obj("Chest", 15, 15)]
    m["locks"] = [(12, 14, "$Attr.HobgoblinQuest>=2", "The royal treasury is locked. Only a hero of King Tyron may enter.")]
    # The wizard's study gets an alchemy table.
    M["2,4,1"]["entities"] += [obj("Alchemy_Table", 20, 14)]
    # Goblin camp: a few more goblins and a wolf at the edge.
    M["3,4,0"]["entities"] += [npc("BadNPC", "Goblin", 19, 8), npc("BadNPC", "Wolf", 6, 17)]


# =========================================================================================== original island maps
# Single tiles (TileX, TileY, old, new) and entity lines added to the original maps (see the module docstring).
def patches():
    npc, item, obj = W.npc, W.item, W.obj
    nx, ny = W.place("Notice", 22, 11)
    hx, hy = W.place("Notice", HOUSE_NOTICE[0], HOUSE_NOTICE[1])
    out = {
        "1,1,0": dict(
            tiles=[(21, 4, "Ladder001", "Ladder002"),          # the house ladder is now a hatch down to the cellar
                   (6, 9, "Grass001", "Berry_Bush001"), (6, 14, "Grass001", "Herb_Patch001"),   # (west of the bank)
                   # the beggar's house, furnished like the others: a table and chair, a plant, a runner rug
                   (19, 4, "Tile001", "Table101"), (19, 5, "Tile001", "Chair102"), (19, 6, "Tile001", "Potted_Plant101"),
                   (20, 5, "Tile001", "Rug041"), (21, 5, "Tile001", "Rug043")],
            entities=[npc("GoodNPC", "Villager", 11, 10), npc("GoodNPC", "Dog", 14, 12),
                      # the beggar's house: the door (20,7) is a Lock instead of the old Door1 trigger hack; walking
                      # in with the key (the trigger just inside) completes the Beggar's Lost Key quest
                      ("Lock", 20, 7, "$Attr.Door1Open>=1 or $Item.Beggars_House_Key>=1",
                       "The door is locked. They say the beggar in Ashford lost the key to this house."),
                      ("Trigger", "Beggar House", 20, 6),
                      ("StaticObject", "Notice", hx, hy)],
            remove=["Trigger\tDoor1 1,1,0\t20\t7"]),
        "2,1,0": dict(
            tiles=[(20, 10, "Grass001", "Ladder006"),          # a hole under the cliff, down to the grotto
                   (7, 4, "Grass001", "Herb_Patch001"), (22, 17, "Grass001", "Berry_Bush001")],
            entities=[("StaticObject", "Notice", nx, ny), npc("GoodNPC", "Villager", 8, 13)],
            remove=["GoodNPC\tMan\t103\t350"]),          # the original game's test man (his Talk to opened a shop and the bank)
        "2,0,0": dict(
            tiles=[(10, 7, "Grass001", "Nest001"), (14, 8, "Grass001", "Nest001"), (12, 11, "Grass001", "Nest001"),
                   (4, 14, "Grass001", "Berry_Bush001"), (5, 16, "Grass001", "Berry_Bush001")],
            entities=[npc("GoodNPC", "Milkmaid", 9, 9), npc("BadNPC", "Cow", 6, 9), npc("BadNPC", "Cow", 8, 12),
                      npc("BadNPC", "Sheep", 13, 14), npc("BadNPC", "Sheep", 16, 12), npc("BadNPC", "Sheep", 11, 16),
                      obj("Workbench", 7, 6), obj("Range", 11, 6)]),
        "1,0,0": dict(
            tiles=[(4, 10, "Grass001", "Berry_Bush001"), (6, 12, "Grass001", "Herb_Patch001"),
                   (20, 12, "Grass001", "Herb_Patch001"), (18, 18, "Grass001", "Berry_Bush001")],
            entities=[npc("BadNPC", "Chicken", 19, 14), npc("BadNPC", "Chicken", 21, 15)]),
        "3,0,0": dict(
            tiles=[(4, 14, "Grass001", "Herb_Patch001")],
            entities=[npc("BadNPC", "Wolf", 5, 10), npc("BadNPC", "Wolf", 3, 16)]),
        "3,1,0": dict(
            tiles=[(8, 9, "Grass001", "Berry_Bush001"), (14, 16, "Grass001", "Herb_Patch001")],
            entities=[npc("GoodNPC", "Villager", 12, 8), npc("BadNPC", "Sheep", 16, 12), npc("BadNPC", "Sheep", 17, 14)]),
        "0,0,0": dict(
            tiles=[(18, 14, "Grass001", "Berry_Bush001")],
            entities=[npc("BadNPC", "Wolf", 20, 17)]),
        "2,2,0": dict(
            tiles=[(6, 9, "Grass001", "Herb_Patch001")],
            entities=[npc("BadNPC", "Goblin", 14, 9)]),
        "1,2,0": dict(
            tiles=[(21, 5, "Grass001", "Berry_Bush001")],
            entities=[]),
    }
    for name, tiles in ISLE_TREES.items():                  # oaks and willows among the Isle's trees
        out.setdefault(name, dict(tiles=[], entities=[]))["tiles"] += tiles
    import build_scenery                                    # scenery, landmarks, wildlife (build_scenery.py)
    for name, spec in build_scenery.isle_patches().items():
        o = out.setdefault(name, dict(tiles=[], entities=[]))
        taken = {(x, y) for x, y, _, _ in o["tiles"]}
        o["tiles"] += [t for t in spec["tiles"] if (t[0], t[1]) not in taken]
        o["entities"] += spec["entities"]
    for name, spec in out.items():
        spec["entities"] = with_options(name, spec["entities"])
    import build_fishing                                    # fishing spots on the original Isle maps
    for m, ents in build_fishing.protected_spots(W, sys.modules[__name__]).items():
        out.setdefault(m, dict(tiles=[], entities=[]))["entities"] += ents
    import build_boats                                      # the ferry's boat at the Isle's pier
    for m, ents in build_boats.protected_places(W).items():
        out.setdefault(m, dict(tiles=[], entities=[]))["entities"] += ents
    ids = getattr(W, "NOTICE_IDS", {})                      # the notices' Id= (notice_ids)
    m, x, y, _ = ISLE_NOTICE                                # the Isle's own notice: its line again, with its Id
    if (m, x, y) in ids:
        spec = out.setdefault(m, dict(tiles=[], entities=[]))
        spec.setdefault("remove", []).append("StaticObject\tNotice\t%d\t%d" % (x, y))
        spec["entities"].append(("StaticObject", "Notice", x, y))
    for m, spec in out.items():
        spec["entities"] = [tuple(e[:4]) + ("Id=" + ids[(m, e[2], e[3])],)
                            if tuple(e[:2]) == ("StaticObject", "Notice") and (m, e[2], e[3]) in ids else e
                            for e in spec["entities"]]
    return out


HOUSE_NOTICE = (22, 8)      # the notice by the beggar's house on the Isle (1,1,0)
PATCH_LOG = p("dev", "migrate", "content_patches.txt")


def apply_patches():
    """Applies patches() to the original maps; undoes recorded patches that are no longer wanted."""
    want = patches()
    old_log = [l.split("\t") for l in read_lines(PATCH_LOG) if l.strip() and not l.startswith("//")] \
        if os.path.exists(PATCH_LOG) else []
    changed, problems = [], []
    new_log = []
    maps = sorted(set(want) | {r[1] for r in old_log})
    for name in maps:
        path = p("maps", name + ".txt")
        lines = read_lines(path)
        while lines and lines[-1] == "":
            lines.pop()
        rows = [[built_cell(c) for c in r.split(":")] for r in lines[:MAP_H]]     # (decor: as the old tiles)
        ents = lines[MAP_H:]
        spec = want.get(name, dict(tiles=[], entities=[]))
        want_tiles = {(tx, ty): (old, new) for tx, ty, old, new in spec["tiles"]}
        want_ents = [W.entity_line(e) for e in spec["entities"]]
        want_removed = list(spec.get("remove", []))
        # undo what an earlier run added and isn't wanted any more
        for rec in old_log:
            if rec[1] != name:
                continue
            if rec[0] == "TILE":
                tx, ty, old, new = int(rec[2]), int(rec[3]), rec[4], rec[5]
                if want_tiles.get((tx, ty)) != (old, new):
                    cell = rows[ty - 1][tx - 1]
                    if cell.split("+")[0] == new:
                        rows[ty - 1][tx - 1] = old + cell[len(new):]
            elif rec[0] == "ENTITY":
                line = "\t".join(rec[2:])
                if line not in want_ents and line in ents:
                    ents.remove(line)
            elif rec[0] == "REMOVE":
                # an original line an earlier run took out: put it back if that's no longer wanted
                line = "\t".join(rec[2:])
                if line not in want_removed and line not in ents:
                    ents.append(line)
        for (tx, ty), (old, new) in want_tiles.items():
            cell = rows[ty - 1][tx - 1]
            b = cell.split("+")[0]
            if b == old:
                rows[ty - 1][tx - 1] = new + cell[len(old):]
            elif b != new:
                problems.append("%s: patch %d,%d wants %s -> %s but the cell is %s" % (name, tx, ty, old, new, b))
                continue
            new_log.append("\t".join(["TILE", name, str(tx), str(ty), old, new]))
        for line in want_ents:
            if line not in ents:
                ents.append(line)
            new_log.append("\t".join(["ENTITY", name, line]))
        for line in want_removed:
            while line in ents:
                ents.remove(line)
            new_log.append("\t".join(["REMOVE", name, line]))
        out = [":".join(r) for r in decor_cells(rows)] + [""] + [e for e in ents if e.strip()]
        if write_lines(path, out):
            changed.append("maps\\%s.txt" % name)
    if write_lines(PATCH_LOG, ["// Patches build_content.py made to the original maps (TILE map x y old new / ENTITY map line"
                               " / REMOVE map original-line)"] + new_log):
        changed.append("dev\\migrate\\content_patches.txt")
    PATCH_PROBLEMS[:] = problems
    return changed


PATCH_PROBLEMS = []


# =========================================================================================== scripts
def L(*steps):
    return list(steps)


def too_far():
    return ["far:", ("Display.Message", "DarkRed", "You are too far away!"), ("End",)]


def tile_coords():
    """Remember the clicked tile at once (the player may click elsewhere while the script waits)."""
    return [("Get.Value", "CALCULATION", "$Tile.under.Cursor.X", "Variable.5$"),
            ("Get.Value", "CALCULATION", "$Tile.under.Cursor.Y", "Variable.6$")]


# Tool tiers, best first: (item, bonus to the success chance in percent, tier). A better tool makes gathering more
# likely to work, and some rocks need at least a given tier (Mithril: a steel pickaxe). The player's best tool counts.
PICKAXES = [("Mithril_Pickaxe", 24, 4), ("Steel_Pickaxe", 14, 3), ("Pickaxe", 6, 2), ("Bronze_Pickaxe", 0, 1)]
AXES = [("Mithril_Axe", 24, 4), ("Steel_Axe", 14, 3), ("Axe", 6, 2), ("Bronze_Axe", 0, 1)]
TIER_NAMES = {1: "bronze", 2: "iron", 3: "steel", 4: "mithril"}
ROCKS = ("Ore_Rock", "Copper_Rock", "Tin_Rock", "Coal_Rock", "Silver_Rock", "Gold_Rock", "Gem_Rock", "Mithril_Rock")
IRON_BONUS = 6       # the chances below were set for the iron tools, so an iron tool still has exactly those odds


def best_tool(tools, missing):
    """Finds the best tool the player carries: Variable.2 = its bonus, Variable.3 = its tier (1 = bronze ...).
    Jumps to @missing if they have none."""
    steps = []
    for i, (name, bonus, tier) in enumerate(tools):
        last = i == len(tools) - 1
        nxt = missing if last else "@tool%d" % (i + 1)
        if i:
            steps.append("tool%d:" % i)
        steps += [(">Got.Item", name, "1", nxt),
                  ("Get.Value", "CALCULATION", str(bonus), "Variable.2$"),
                  ("Get.Value", "CALCULATION", str(tier), "Variable.3$")]
        if not last:
            steps.append(("Goto.Line", "@gottool"))
    return steps + ["gottool:"]


# Trees: (tile base name, what it's called, logs, Woodcutting level, XP, chance base %, seconds as a stump)
TREES = [("Tree", "tree", "Logs", 1, "0.1", 50, 20),
         ("Oak_Tree", "oak", "Oak_Logs", 10, "0.25", 40, 30),
         ("Willow_Tree", "willow", "Willow_Logs", 20, "0.4", 32, 45),
         ("Yew_Tree", "yew", "Yew_Logs", 35, "0.9", 22, 90)]
# Logs on a fire: (logs, chance % that they catch, seconds the fire burns). (No skill: anyone with a tinderbox.)
FIRE_LOGS = [("Logs", 75, 30), ("Oak_Logs", 70, 45), ("Willow_Logs", 65, 60), ("Yew_Logs", 60, 90)]


def chop_script(tree, what, logs, level, xp, base, regrow):
    """Woodcutting: an axe (the better, the likelier), the Woodcutting level; half the time the tree becomes a stump."""
    steps = ["// Woodcutting a %s (Woodcutting %d): needs an axe. Generated by build_content.py" % (what, level),
             (">Distance.From.Clicked.Tile", "35", "@far")] + tile_coords() + best_tool(AXES, "@noaxe") + [
        ("Get.Value", "SKILL", "Woodcutting", "Variable.1$")]
    if level > 1:
        steps.append((">Conditional", "$Variable.1>=%d" % level, "@low"))
    steps += [("Play.Sound", "WoodChop"),
              ("Display.Message", "Cyan", "You swing your axe at the %s.." % what),
              ("Wait", "3.5"),
              (">Conditional", "($Variable.1+$Variable.2+%d)>$Random.Percent" % (base - IRON_BONUS), "@fail"),
              ("Display.Message", "Yellow", "..and manage to get some %s!" % logs.replace("_", " ").lower()),
              ("Give.Item", logs, "1"),
              ("Update.Skill", "Woodcutting", "+" + xp),
              (">Random", "50", "@stump"),
              ("End",),
              "fail:",
              ("Display.Message", "DarkRed", "..but fail to get any logs!"),
              ("End",),
              "stump:",
              ("Change.Tile", "$Variable.5,$Variable.6", "Tree_Stump001", "0", str(regrow)),
              ("End",)]
    if level > 1:
        steps += ["low:", ("Display.Message", "DarkRed", "You need level %d Woodcutting to chop this %s." % (level, what)), ("End",)]
    return steps + ["noaxe:", ("Display.Message", "DarkRed", "You need an axe!"), ("End",)] + too_far()


def fire_script(logs, chance, burn):
    """Lighting a fire: better logs burn longer (but are a little harder to get going)."""
    lp = logs.replace("_", " ").lower()
    steps = ["// Lighting a fire with %s. Generated by build_content.py" % lp,
             (">Got.Item", logs, "1", "@nologs"),
             (">Got.Item", "Tinderbox", "1", "@nobox")]
    steps += [("Display.Message", "Cyan", "You strike the flint.."),
              ("Play.Sound", "StrikeFlint"),
              ("Wait", "1"),
              (">Conditional", "%d>$Random.Percent" % chance, "@fail"),
              ("Display.Message", "Yellow", "..and the %s catch! The fire will burn for %d seconds." % (lp, burn)),
              ("Play.Sound", "MakeFire"),
              ("Take.Item", logs, "1"),
              ("Add.Entity", "$Player.X,$Player.Y", "Fire", "StaticObject", "-"),
              ("Add.Action.To.Queue", "REMOVE", "Fire", "StaticObject", "-", "$Map.Name", "$Player.X,$Player.Y", str(burn)),
              ("End",),
              "fail:",
              ("Display.Message", "DarkRed", "..but the %s won't catch." % lp),
              ("End",)]
    return steps + ["nologs:", ("Display.Message", "DarkRed", "You need to be holding the logs!"), ("End",),
                    "nobox:", ("Display.Message", "DarkRed", "You need to be holding a tinderbox!"), ("End",)]


def mine_script(rock, ore_name, gives, level, xp, regrow, chance_base=40, extra=None, tier=1):
    """Mining: a pickaxe (the better it is, the likelier a strike), Mining level, a chance that grows with the
    level, then the rock is mined out for a while. tier = the weakest pickaxe that can break it."""
    steps = ["// %s: needs a pickaxe and Mining %d. Generated by build_content.py" % (rock, level),
             (">Distance.From.Clicked.Tile", "40", "@far")] + tile_coords() + best_tool(PICKAXES, "@nopick") + [
        ("Get.Value", "SKILL", "Mining", "Variable.1$"),
        (">Conditional", "$Variable.1>=%d" % level, "@low"),
    ]
    if tier > 1:
        steps.append((">Conditional", "$Variable.3>=%d" % tier, "@weak"))
    steps += [
        ("Display.Message", "Cyan", "You swing your pickaxe at the %s..." % ore_name),
        ("Play.Sound", "Mine"),
        ("Wait", "3"),
        (">Conditional", "($Variable.1+$Variable.2+%d)>$Random.Percent" % (chance_base - IRON_BONUS), "@fail"),
    ]
    if extra:
        steps += extra
    else:
        steps += [("Display.Message", "Yellow", "...and mine some %s!" % gives.replace("_", " ").lower()),
                  ("Give.Item", gives, "1")]
    steps += [
        "done:",
        ("Update.Skill", "Mining", "+%s" % xp),
        ("Change.Tile", "$Variable.5,$Variable.6", "Ore_Rock002", "0", str(regrow)),
        ("End",),
        "fail:",
        ("Display.Message", "DarkRed", "...but only chip the rock."),
        ("End",),
        "low:",
        ("Display.Message", "DarkRed", "You need level %d Mining to mine this %s." % (level, ore_name)),
        ("End",),
    ]
    if tier > 1:
        steps += ["weak:",
                  ("Display.Message", "DarkRed", "Your pickaxe just bounces off! You need a %s pickaxe or better."
                   % TIER_NAMES[tier]),
                  ("End",)]
    steps += [
        "nopick:",
        ("Display.Message", "DarkRed", "You need a pickaxe!"),
        ("End",),
    ] + too_far()
    return steps


def wheat_field(cells, seed):
    """Ripe wheat plants (StaticObjects Ripe_Wheat001-003) on the field cells: two a cell, one behind the other, each a
    few pixels off its place and a different clump, and now and then one missing at the edge, so the field isn't a
    block."""
    import random
    rng = random.Random(seed)
    cellset = set(cells)
    out = []
    for (tx, ty) in cells:
        edge = any((tx + dx, ty + dy) not in cellset for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        for bx, by in ((-6, -10), (6, 0)):
            if edge and rng.random() < 0.15:
                continue
            x, y = W.at(tx, ty, bx + rng.randint(-3, 3), by + rng.randint(-2, 2))
            out.append(("StaticObject", "Ripe_Wheat%03d" % rng.randint(1, 3), x, y))
    return out


def wheat_script(name):
    """Harvest a wheat plant: a sheaf of Wheat; stubble stands there for a minute, then it has grown back."""
    return ["// Harvesting ripe wheat. Generated by build_content.py",
            (">Distance.From.Clicked.Entity", "40", "@far"),
            ("Get.Value", "CALCULATION", "$Object.under.Cursor.X", "Variable.5$"),
            ("Get.Value", "CALCULATION", "$Object.under.Cursor.Y", "Variable.6$"),
            ("Display.Message", "Cyan", "You cut an armful of wheat..."),
            ("Play.Sound", "Pickup"),
            ("Wait", "1.5"),
            ("Display.Message", "Yellow", "...and tie it into a sheaf."),
            ("Give.Item", "Wheat", "1"),
            ("Remove.Entity", "$Variable.5,$Variable.6", name),
            ("Add.Entity", "$Variable.5,$Variable.6", "Stubble", "StaticObject", "-"),
            ("Add.Action.To.Queue", "REMOVE", "Stubble", "StaticObject", "-", "$Map.Name", "$Variable.5,$Variable.6", "60"),
            ("Add.Action.To.Queue", "ADD", name, "StaticObject", "-", "$Map.Name", "$Variable.5,$Variable.6", "60"),
            ("End",)] + too_far()


def pick_script(what, gives, used_tile, regrow, skill, level, xp, deplete, msg_try, msg_ok, sound="Pickup",
                extra_give=None):
    steps = ["// Gathering %s. Generated by build_content.py" % what,
             (">Distance.From.Clicked.Tile", "40", "@far")] + tile_coords()
    if skill and level > 1:
        steps += [("Get.Value", "SKILL", skill, "Variable.1$"),
                  (">Conditional", "$Variable.1>=%d" % level, "@low")]
    steps += [("Display.Message", "Cyan", msg_try),
              ("Play.Sound", sound),
              ("Wait", "1.5"),
              ("Display.Message", "Yellow", msg_ok),
              ("Give.Item", gives, "1")]
    if extra_give:
        steps += extra_give
    if skill:
        steps += [("Update.Skill", skill, "+%s" % xp)]
    if deplete < 100:
        steps += [(">Random", str(deplete), "@end")]
    steps += [("Change.Tile", "$Variable.5,$Variable.6", used_tile, "0", str(regrow)),
              "end:", ("End",)]
    if skill and level > 1:
        steps += ["low:", ("Display.Message", "DarkRed", "You need level %d %s for that." % (level, skill)), ("End",)]
    return steps + too_far()


def cook_script(raw, cooked, burnt, level, xp, station, base=40):
    rp, cp = raw.replace("_", " "), cooked.replace("_", " ")
    steps = ["// Cooking %s on a %s (Cooking %d). Generated by build_content.py" % (rp, station.lower(), level),
             (">Distance.From.Clicked.Entity", "40", "@far")]
    if level > 1:
        steps += [("Get.Value", "SKILL", "Cooking", "Variable.1$"),
                  (">Conditional", "$Variable.1>=%d" % level, "@low")]
    steps += [(">Got.Item", raw, "1", "@none"),
              ("Take.Item", raw, "1"),
              ("Display.Message", "Cyan", "You place the %s on the %s.." % (rp, station.lower().replace("_", " "))),
              ("Play.Sound", "CookingFood"),
              ("Wait", "3"),
              ("Get.Value", "SKILL", "Cooking", "Variable.1$"),
              (">Conditional", "($Variable.1+%d)>$Random.Percent" % base, "@burn"),
              ("Display.Message", "Yellow", "..and cook it perfectly!"),
              ("Update.Skill", "Cooking", "+%s" % xp),
              ("Give.Item", cooked, "1"),
              ("End",),
              "burn:",
              ("Display.Message", "DarkRed", "..but accidentally burn it!"),
              ("Give.Item", burnt, "1"),
              ("End",),
              "none:",
              ("Display.Message", "DarkRed", "You don't have any %s." % rp),
              ("End",)]
    if level > 1:
        steps += ["low:", ("Display.Message", "DarkRed", "You need level %d Cooking to cook %s." % (level, rp)), ("End",)]
    return steps + too_far()


def station_script(verb, station, rack, who):
    return ["// %s %s: opens the %s list. Generated by build_content.py" % (verb, station, rack),
            (">Distance.From.Clicked.Entity", "48", "@far"),
            ("Display.Item.Rack", "GENERAL", who, rack, "@end"),
            "end:", ("End",)] + too_far()


def forge_choice(who, text):
    """Smith NPCs: smelt at the furnace (CRAFT-Smelting) or smith at the anvil (CRAFT-Smithing). Needs a @bye label."""
    return [("Display.Conversation", who, text + "\\Smelt ore into bars at the furnace, then hammer the bars into tools and armour on the anvil.",
             "The furnace: smelt ore.", "@smelt", "The anvil: smith bars.", "@smith", "Never mind.", "@bye"),
            "smelt:",
            ("Display.Item.Rack", "GENERAL", who, "CRAFT-Smelting", "@bye"),
            ("End",),
            "smith:",
            ("Display.Item.Rack", "GENERAL", who, "CRAFT-Smithing", "@bye"),
            ("End",)]


def drink_script(potion, heal=0, skill=None, xp=0, msg=""):
    steps = [("Take.Item", potion, "1"), ("Display.Message", "Cyan", msg)]
    if heal:
        steps.append(("Update.Skill", "Hitpoints", "+%d" % heal))
    if skill:
        steps.append(("Update.Skill", skill, "+%s" % xp))
    steps += [("Give.Item", "Empty_Vial", "1"), ("End",)]
    return steps


def scripts():
    S = {}
    # ----- ladders: no special cases any more (the house ladder on the Isle is now a hatch down to its cellar)
    for name, verb, dz, msg in (("Climb Up Ladder001", "up", "+1", "You climb up the ladder."),
                                ("Climb Down Ladder002", "down", "-1", "You climb down the ladder."),
                                ("Climb Up Ladder008", "up", "+1", "You climb up the ladder into the loft."),
                                ("Climb Down Ladder009", "down", "-1", "You climb down the ladder."),
                                ("Climb Up Stairs", "up", "+1", "You go up the stairs."),
                                ("Climb Down Stairs", "down", "-1", "You go down the stairs.")):
        S[name] = [
            "// The same X,Y one level %s. If that map doesn't exist the engine says it leads nowhere" % verb,
            "// and the player stays put, so the message is only shown once the map has really changed.",
            ("Get.Value", "CALCULATION", "$Map.Z%s" % dz, "Variable.9$"),
            ("Get.Value", "CALCULATION", "$Map.Name", "Variable.8$"),
            ("Teleport", "$Player.X,$Player.Y", "$Map.X,$Map.Y,$Variable.9"),
            (">Conditional", "$Map.Name<>$Variable.8", "@end"),
            ("Play.Sound", "Ladder"),
            ("Display.Message", "Cyan", msg),
            "end:", ("End",)]

    # ----- map entry
    S["1,1,-1"] = [("Display.Message", "Cyan", "A damp cellar. The far wall has fallen in, and something squeaks in the dark."), ("End",)]
    S["2,1,-1"] = [("Display.Message", "Cyan", "The grotto under the Isle. Water drips into a black pool."), ("End",)]
    S["2,4,-3"] = [("Display.Message", "DarkRed", "The Deep Hollow. Torchlight flickers ahead... and bones rattle in the dark."), ("End",)]

    # ----- gathering
    for tree, what, logs, level, xp, base, regrow in TREES:
        S["Chop " + tree] = chop_script(tree, what, logs, level, xp, base, regrow)
    S["Mine Ore_Rock"] = mine_script("Ore_Rock", "iron rock", "Iron_Ore", 1, "0.1", 30, chance_base=50)
    S["Mine Copper_Rock"] = mine_script("Copper_Rock", "copper rock", "Copper_Ore", 1, "0.08", 20, chance_base=55)
    S["Mine Coal_Rock"] = mine_script("Coal_Rock", "coal rock", "Coal", 5, "0.15", 40, chance_base=40)
    S["Mine Gold_Rock"] = mine_script("Gold_Rock", "gold rock", "Gold_Ore", 15, "0.3", 60, chance_base=25)
    S["Mine Gem_Rock"] = mine_script("Gem_Rock", "crystal rock", "", 20, "0.5", 90, chance_base=15, extra=[
        (">Random", "50", "@notsapphire"),
        ("Display.Message", "Yellow", "...and prise out a sapphire!"),
        ("Give.Item", "Sapphire", "1"),
        ("Goto.Line", "@done"),
        "notsapphire:",
        (">Random", "60", "@ruby"),
        ("Display.Message", "Yellow", "...and prise out an emerald!"),
        ("Give.Item", "Emerald", "1"),
        ("Goto.Line", "@done"),
        "ruby:",
        ("Display.Message", "Yellow", "...and prise out a ruby!"),
        ("Give.Item", "Ruby", "1")])
    S["Mine Tin_Rock"] = mine_script("Tin_Rock", "tin rock", "Tin_Ore", 1, "0.08", 20, chance_base=55)
    S["Mine Silver_Rock"] = mine_script("Silver_Rock", "silver rock", "Silver_Ore", 12, "0.25", 50, chance_base=30)
    S["Mine Mithril_Rock"] = mine_script("Mithril_Rock", "mithril rock", "Mithril_Ore", 25, "0.7", 120,
                                         chance_base=12, tier=3)
    for rock in ROCKS:
        for tool, _, _ in PICKAXES:
            S["Use %s With %s" % (tool, rock)] = [("Goto.Script", "Mine %s" % rock), ("End",)]
    for tool, _, _ in AXES:
        for tree in TREES:
            S["Use %s With %s" % (tool, tree[0])] = [("Goto.Script", "Chop " + tree[0]), ("End",)]

    S["Pick Mushroom_Patch"] = pick_script("cave mushrooms", "Cave_Mushroom", "Mushroom_Patch002", 60, "Potion_Making", 1, "0.1",
                                           50, "You pick a glowing mushroom...", "...it's still warm to the touch.")
    S["Pick Berry_Bush"] = pick_script("berries", "Berries", "Berry_Bush002", 45, "Potion_Making", 1, "0.05", 40,
                                       "You reach into the bush...", "...and pick a handful of berries.")
    S["Pick Herb_Patch"] = pick_script("herbs", "Herb", "Herb_Patch002", 50, "Potion_Making", 1, "0.1", 60,
                                       "You search the patch for good leaves...", "...and pick a fragrant herb.")
    for k in (1, 2, 3):
        S["Harvest Ripe_Wheat%03d" % k] = wheat_script("Ripe_Wheat%03d" % k)
    S["Collect Nest"] = pick_script("eggs", "Egg", "Nest002", 45, "", 0, "0", 100,
                                    "You feel around in the straw...", "...and find a fresh egg!")
    S["Use Fishing_Rod With Water"] = [
        "// Fishing in the sea or a river needs Bait (each catch uses one; a miss keeps it): a fish, or sometimes",
        "// something better: a trout (Fishing 10), a salmon (20), a swordfish (35). Generated by build_content.py",
        (">Distance.From.Cursor", "45", "@far"),
        (">Got.Item", "Bait", "1", "@nobait"),
        ("Display.Message", "Cyan", "You bait the hook and cast your line into the water..."),
        ("Play.Sound", "Splash"),
        ("Wait", "4"),
        ("Get.Value", "SKILL", "Fishing", "Variable.1$"),
        (">Conditional", "($Variable.1+35)>$Random.Percent", "@fail"),
        (">Conditional", "$Variable.1>=35", "@salmon"),
        (">Random", "30", "@salmon"),
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and after a long fight you land a swordfish!"),
        ("Give.Item", "Raw_Swordfish", "1"),
        ("Update.Skill", "Fishing", "+0.6"),
        ("End",),
        "salmon:",
        (">Conditional", "$Variable.1>=20", "@trout"),
        (">Random", "35", "@trout"),
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and a silver salmon leaps onto the hook!"),
        ("Give.Item", "Raw_Salmon", "1"),
        ("Update.Skill", "Fishing", "+0.35"),
        ("End",),
        "trout:",
        (">Conditional", "$Variable.1>=10", "@fish"),
        (">Random", "40", "@fish"),
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and a trout takes the bait!"),
        ("Give.Item", "Raw_Trout", "1"),
        ("Update.Skill", "Fishing", "+0.2"),
        ("End",),
        "fish:",
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and catch a fish!"),
        ("Give.Item", "Raw_Fish", "1"),
        ("Update.Skill", "Fishing", "+0.1"),
        ("End",),
        "fail:",
        ("Display.Message", "DarkRed", "...but nothing bites."),
        ("End",),
        "nobait:",
        ("Display.Message", "DarkRed", "You need bait on the hook. Fishing shops sell worms."),
        ("End",),
        "far:",
        ("Display.Message", "DarkRed", "You need to stand at the water's edge!"),
        ("End",)]
    S["Use Fishing_Rod With Cave_Pool"] = [
        "// Fishing in an underground pool: cave eels, Fishing 15. Needs Bait (each catch uses one).",
        (">Distance.From.Cursor", "45", "@far"),
        ("Get.Value", "SKILL", "Fishing", "Variable.1$"),
        (">Conditional", "$Variable.1>=15", "@low"),
        (">Got.Item", "Bait", "1", "@nobait"),
        ("Display.Message", "Cyan", "You bait the hook and lower your line into the black water..."),
        ("Play.Sound", "Splash"),
        ("Wait", "5"),
        (">Conditional", "($Variable.1+20)>$Random.Percent", "@fail"),
        ("Take.Item", "Bait", "1"),
        ("Display.Message", "Yellow", "...and haul out a wriggling cave eel!"),
        ("Give.Item", "Raw_Cave_Eel", "1"),
        ("Update.Skill", "Fishing", "+0.3"),
        ("End",),
        "fail:",
        ("Display.Message", "DarkRed", "...something pale circles the hook, then slips away."),
        ("End",),
        "low:",
        ("Display.Message", "DarkRed", "You need level 15 Fishing to catch anything in here."),
        ("End",),
        "nobait:",
        ("Display.Message", "DarkRed", "You need bait on the hook. Fishing shops sell worms."),
        ("End",),
        "far:",
        ("Display.Message", "DarkRed", "You need to stand at the water's edge!"),
        ("End",)]
    S["Use Bucket With Cave_Pool"] = [("Goto.Script", "Use Bucket With Water"), ("End",)]
    S["Use Bucket With Cow"] = [
        "// Milking: an empty bucket on a cow.",
        (">Distance.From.Clicked.Entity", "45", "@far"),
        ("Display.Message", "Cyan", "You crouch down and milk the cow..."),
        ("Play.Sound", "FillBucket"),
        ("Wait", "2"),
        (">Got.Item", "Bucket", "1", "@nobucket"),
        ("Take.Item", "Bucket", "1"),
        ("Give.Item", "Bucket_of_Milk", "1"),
        ("Display.Message", "Yellow", "...and fill the bucket with warm milk."),
        ("End",),
        "nobucket:",
        ("Display.Message", "DarkRed", "You need an empty bucket!"),
        ("End",)] + too_far()
    S["Use Shears With Sheep"] = [
        "// Shearing: shears on a sheep.",
        (">Distance.From.Clicked.Entity", "45", "@far"),
        (">Got.Item", "Shears", "1", "@noshears"),
        ("Display.Message", "Cyan", "You grab the sheep and start to shear..."),
        ("Wait", "2"),
        (">Random", "70", "@fail"),
        ("Give.Item", "Wool", "1"),
        ("Display.Message", "Yellow", "...and get a fluffy clump of wool."),
        ("Update.Skill", "Crafting", "+0.05"),
        ("End",),
        "fail:",
        ("Display.Message", "DarkRed", "...but the sheep wriggles free!"),
        ("End",),
        "noshears:",
        ("Display.Message", "DarkRed", "You need shears!"),
        ("End",)] + too_far()

    # ----- cooking on fires and ranges
    for raw, cooked, burnt, lvl, xp in (("Raw_Trout", "Cooked_Trout", "Burnt_Fish", 10, "0.15"),
                                        ("Raw_Cave_Eel", "Cooked_Cave_Eel", "Burnt_Fish", 15, "0.25"),
                                        ("Raw_Salmon", "Cooked_Salmon", "Burnt_Fish", 20, "0.35"),
                                        ("Raw_Swordfish", "Cooked_Swordfish", "Burnt_Fish", 35, "0.6")):
        S["Use %s With Fire" % raw] = cook_script(raw, cooked, burnt, lvl, xp, "Fire")
    for raw, cooked, burnt, lvl, xp in (("Raw_Meat", "Cooked_Meat", "Burnt_Meat", 1, "0.05"),
                                        ("Raw_Poultry", "Cooked_Poultry", "Burnt_Poultry", 1, "0.05"),
                                        ("Raw_Fish", "Cooked_Fish", "Burnt_Fish", 1, "0.05"),
                                        ("Raw_Trout", "Cooked_Trout", "Burnt_Fish", 10, "0.15"),
                                        ("Raw_Cave_Eel", "Cooked_Cave_Eel", "Burnt_Fish", 15, "0.25"),
                                        ("Raw_Salmon", "Cooked_Salmon", "Burnt_Fish", 20, "0.35"),
                                        ("Raw_Swordfish", "Cooked_Swordfish", "Burnt_Fish", 35, "0.6")):
        S["Use %s With Range" % raw] = cook_script(raw, cooked, burnt, lvl, xp, "Range", base=50)

    # ----- crafting stations
    S["Smelt Furnace"] = station_script("Smelt", "Furnace", "CRAFT-Smelting", "Furnace")
    S["Talk to Blacksmith"] = [
        ("Display.Conversation", "Blacksmith", "Mind the forge, it's hot!\\Bring me ore from the mines: copper and tin make bronze, iron makes iron, and iron with coal makes steel.\\With bars and some logs you can make your own tools. Better tools dig and chop faster.",
         "Let me use the forge.", "@forge", "What do you sell?", "@shop", "Where are the mines?", "@mine", "Goodbye.", "@bye"),
        "forge:"] + forge_choice("Blacksmith", "Help yourself.") + [
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Blacksmith", "SHOP-Smith", "@bye"),
        ("End",),
        "mine:",
        ("Display.Conversation", "Blacksmith", "Copper, tin and coal: in the grotto under the beggar's cellar.\\Iron: the old mine in the Whispering Woods, past the King's guard. Wear armour.\\Silver lies deeper down. Brokk the dwarf has found mithril in the Deep Hollow.",
         "Thanks.", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Miner"] = [
        ("Display.Conversation", "Miner", "Careful, friend! The hobgoblins dug up from the deep and drove us all out.\\There's still good iron in these rocks, though. Copper and tin too, in the south gallery.",
         "How do I mine?", "@how", "Where did the hobgoblins come from?", "@hob", "Goodbye.", "@bye"),
        "how:"] + best_tool(PICKAXES, "@nopick") + [
        ("Display.Conversation", "Miner", "Click a rock with ore in it and swing. Better pickaxes strike more often.\\Smelt the ore at a furnace.\\At Mining 10 the guild's deep seam opens: coal, silver and gold!", "Thanks!", "@bye"),
        ("End",),
        "nopick:",
        ("Display.Conversation", "Miner", "You'll need a pickaxe. I dropped my spare by the ladder when I ran.\\The Ashford blacksmith sells them too.", "Thanks!", "@bye"),
        ("End",),
        "hob:",
        ("Display.Conversation", "Miner", "There's a hatch in the tunnels to the east that goes down to their warren.\\I saw them carry off all sorts down there. Keys, coins, gems...", "I'll take a look.", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Wizard"] = [
        "// The wizard: gives new visitors some scrolls once (attribute WizardGift), sells scrolls, teaches scroll writing",
        "// (CRAFT-Scrolls, Magic) and teleports. Generated by build_content.py",
        ("Get.Value", "ATTRIBUTE", "WizardGift", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@main"),
        ("Display.Conversation", "Wizard", "A new face! Every adventurer should know a little magic. Take these.\\Right-click a scroll and choose Cast, or use it on a monster. Reading it uses it up.",
         "Thank you!", "@gift"),
        "gift:",
        ("Give.Item", "Fire_Bolt_Scroll", "3"),
        ("Give.Item", "Healing_Scroll", "2"),
        ("Update.Attribute", "WizardGift", "=1"),
        ("Display.Message", "Yellow", "The wizard gives you 3 Fire Bolt scrolls and 2 Healing scrolls."),
        "main:",
        ("Display.Conversation", "Wizard", "I study the arcane arts up here, far from the noise of the court.\\I sell spell scrolls, and I can teach you to write your own. Or I can send you anywhere I have been.",
         "Show me your scrolls.", "@shop", "Teach me to write scrolls.", "@write", "Can you teleport me?", "@tele", "Goodbye.", "@bye"),
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Wizard", "SHOP-Wizard", "@bye"),
        ("End",),
        "write:",
        ("Display.Item.Rack", "GENERAL", "Wizard", "CRAFT-Scrolls", "@bye"),
        ("End",),
        "tele:",
        ("Display.Conversation", "Wizard", "Where to?", "To the Isle.", "@isle", "To Northgate.", "@south", "Nowhere, thanks.", "@bye"),
        "isle:",
        ("Play.Sound", "Teleporter"),
        ("Display.Message", "Yellow", "The wizard waves his hands and the world spins..."),
        ("Teleport", PL.feet("Isle_Landing", "1,1,0", 300, 300), "-"),
        ("End",),
        "south:",
        ("Play.Sound", "Teleporter"),
        ("Display.Message", "Yellow", "The wizard waves his hands and the world spins..."),
        ("Teleport", PL.feet("Southport_Landing", "1,3,0", 352, 320), "-"),
        ("End",),
        "bye:",
        ("End",)]
    S["Smith Anvil"] = station_script("Smith", "Anvil", "CRAFT-Smithing", "Anvil")
    S["Cook Range"] = station_script("Cook", "Range", "CRAFT-Cooking", "Range")
    S["Brew Alchemy_Table"] = station_script("Brew", "Alchemy_Table", "CRAFT-Potion_Making", "Alchemy_Table")
    S["Craft Workbench"] = station_script("Craft", "Workbench", "CRAFT-Crafting", "Workbench")
    S["Search Mine_Cart"] = [
        (">Distance.From.Clicked.Entity", "40", "@far"),
        ("Display.Message", "Cyan", "You rummage through the cart. Just rusty nails and rock dust."),
        ("End",)] + too_far()

    # ----- drinks
    S["Drink Super_Potion"] = drink_script("Super_Potion", heal=40, msg="You drink the potion. It fizzes and glows!")
    S["Drink Strength_Potion"] = drink_script("Strength_Potion", heal=5, skill="Strength", xp="0.5",
                                              msg="You drink the potion. Your arms tingle with strength!")
    S["Drink Bucket_of_Milk"] = [("Take.Item", "Bucket_of_Milk", "1"),
                                 ("Display.Message", "Cyan", "You drink the milk. Delicious!"),
                                 ("Update.Skill", "Hitpoints", "+3"),
                                 ("Give.Item", "Bucket", "1"), ("End",)]
    S["Pet Dog"] = [(">Distance.From.Clicked.Entity", "40", "@far"),
                    ("Display.Message", "Cyan", "The dog wags its tail and licks your hand."), ("End",)] + too_far()

    # ----- lighting a fire
    for logs, chance, burn in FIRE_LOGS:
        S["Use %s With Tinderbox" % logs] = fire_script(logs, chance, burn)

    # ----- clicking a skill in the stat box: where to train it (Cooking Skill opens the cooking list, as before)
    for skill, text in (
            ("Smithing", "Smithing: smelt ore and forge tools at a furnace or anvil (the Ashford smithy, Brokk's hall)."),
            ("Mining", "Mining: use a pickaxe on rocks in the mines. Copper and iron at level 1, coal 5, gold 15, gems 20."),
            ("Fishing", "Fishing: use a rod on water, with bait in your pack (one per catch). Trout need level 10, cave eels level 15."),
            ("Woodcutting", "Woodcutting: chop trees with an axe."),
            ("Potion_Making", "Potion Making: pick herbs, berries and mushrooms, and brew potions at an alchemy table."),
            ("Crafting", "Crafting: shear sheep, then tan, spin and make jewellery at a workbench.")):
        S["%s Skill" % skill] = [("Display.Message", "Cyan", text), ("End",)]

    # ----- locked rooms (see the Lock lines): their chests give a reward once
    S["Open Chest"] = [
        "// Chests behind Locks: the royal treasury (4,4,0) and Brokk's vault (2,4,-3). Each gives its reward once.",
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">On.Map", "4,4,0", "@vault"),
        ("Get.Value", "ATTRIBUTE", "TreasuryLooted", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@empty"),
        ("Update.Attribute", "TreasuryLooted", "=1"),
        ("Play.Sound", "Pickup"),
        ("Give.Item", "Gold_Coin(s)", "80"),
        ("Give.Item", "Iron_Platebody", "1"),
        ("Give.Item", "Super_Potion", "1"),
        ("Display.Message", "Yellow", "The King's chest holds 80 gold, an iron platebody and a super potion!"),
        ("End",),
        "vault:",
        (">On.Map", "2,4,-3", "@empty"),
        ("Get.Value", "ATTRIBUTE", "VaultLooted", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@empty"),
        ("Update.Attribute", "VaultLooted", "=1"),
        ("Play.Sound", "Pickup"),
        ("Give.Item", "Gold_Coin(s)", "120"),
        ("Give.Item", "Steel_Helm", "1"),
        ("Give.Item", "Emerald", "2"),
        ("Display.Message", "Yellow", "Brokk's chest holds 120 gold, a steel helm and two emeralds!"),
        ("End",),
        "empty:",
        ("Display.Message", "Cyan", "The chest is empty."),
        ("End",)] + too_far()
    S["Mine Gate"] = [
        "// Triggers on the south row of the yard round the mine hatch (1,4,0): once the player has been in the yard",
        "// the guard lets them through the gate (its Lock checks MineGatePassed), so coming up the ladder without",
        "// armour never shuts them in.",
        ("Get.Value", "ATTRIBUTE", "MineGatePassed", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@end"),
        ("Update.Attribute", "MineGatePassed", "=1"),
        "end:",
        ("End",)]

    S.update(npc_scripts())
    S.update(quest_scripts())
    return S


def npc_scripts():
    S = {}
    S["Talk to Guard"] = [
        (">On.Map", "5,3,0", "@notwardhaven"),                # the guard outside Wardhaven's gate: build_walled.py
        ("Goto.Script", "Wardhaven Guard"),
        ("End",),
        "notwardhaven:",
        (">On.Map", "1,4,0", "@notmine"),
        ("Display.Conversation", "Guard", "Halt! The mine is closed by order of King Tyron.\\No one goes through this gate without body armour on. The hobgoblins down there would gut you.\\Unless the King himself sent you, of course.",
         "Where can I get armour?", "@armour", "Goodbye.", "@bye"),
        ("End",),
        "armour:",
        ("Display.Conversation", "Guard", "The quartermaster at the keep sells leather and iron. Or tan some cowhide and make your own on a workbench.\\And wear it! In your pack it won't stop a hobgoblin's axe.",
         "Thanks.", "@bye"),
        ("End",),
        "notmine:",
        (">On.Map", "2,3,0", "@keep"),
        ("Display.Conversation", "Guard", "Keep the peace in Ashford, citizen.\\If you're looking for work, the King pays well for hobgoblin ears.\\His palace is on the Royal Isle: south to his keep, east along the goblin camp road, then over the causeway.",
         "Any other news?", "@news", "Goodbye.", "@bye"),
        ("End",),
        "keep:",
        ("Display.Conversation", "Guard", "Halt! ...ah, you look honest enough. Go on in.\\The King holds court in the great hall.\\The quartermaster in the courtyard sells arms.",
         "Any other news?", "@news", "Goodbye.", "@bye"),
        ("End",),
        "news:",
        (">Random", "50", "@news2"),
        ("Display.Conversation", "Guard", "Three of the lads were bitten by giant spiders down the old mine. The herbalist is trying to brew something for them.", "I'll ask her.", "@bye"),
        ("End",),
        "news2:",
        ("Display.Conversation", "Guard", "They say a dwarf lives right at the bottom of the mine, below the hobgoblin warren. Mad, if you ask me.", "Interesting.", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Quartermaster"] = [
        ("Display.Conversation", "Quartermaster", "Swords, shields, armour and supplies for the King's men... and for anyone else with coin.\\Leather for beginners, iron for the brave. I'll buy good steel too, if you forge any.",
         "Show me your stock.", "@shop", "Goodbye.", "@bye"),
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Quartermaster", "SHOP-Keep", "@bye"),
        "bye:",
        ("End",)]
    # The townsman in Northgate (the original game's "Talk to Man" opened a shop and the bank: it was for testing)
    S["Talk to Man"] = [
        (">Random", "50", "@two"),
        ("Display.Conversation", "Man", "Northgate's a quiet place, mostly. The ferry brings folk over from the Isle, and the fish come in at dawn.", "Thanks.", "@bye"),
        ("End",),
        "two:",
        ("Display.Conversation", "Man", "Heading inland? Ashford's east of here. Mind the woods to the south: wolves, and worse past the old mine.", "Thanks.", "@bye"),
        ("End",),
        "bye:",
        ("End",)]
    S["Talk to Villager"] = [
        (">Conditional", "$Map.Y<3", "@south"),
        (">Random", "50", "@isle2"),
        ("Display.Conversation", "Villager", "Lovely day on the Isle! If you're bored, there's a hole under the cliffs to the east. Bats down there, mind.", "Thanks.", "@bye"),
        ("End",),
        "isle2:",
        ("Display.Conversation", "Villager", "The milkmaid up north keeps cows and sheep. She'll sell you shears if you fancy some wool.\\The ferry to the mainland leaves from the pier in the south.", "Thanks.", "@bye"),
        ("End",),
        "south:",
        (">Random", "50", "@south2"),
        ("Display.Conversation", "Villager", "Fresh bread at the bakery, tools at the general store, and the smithy has a furnace if you've ore to smelt.", "Thanks.", "@bye"),
        ("End",),
        "south2:",
        ("Display.Conversation", "Villager", "Watch out for wolves in the Whispering Woods. And goblins. And hobgoblins. Honestly, I never leave the village.", "I'll be careful.", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Milkmaid"] = [
        ("Display.Conversation", "Milkmaid", "Morning! Mind the cows, they're friendly but they tread on toes.\\Use a bucket on a cow for milk, shears on a sheep for wool. The hens lay in the nests about.",
         "What do you sell?", "@shop", "What's wool for?", "@wool", "About a ferry ticket...", "@ticket", "Goodbye.", "@bye"),
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Milkmaid", "SHOP-Dairy", "@bye"),
        ("End",),
        "ticket:",
        # Passage to the Mainland (FerryQuest): 1 = sent here by the ferrywoman, 2 = eggs wanted, 3 = has the ticket
        ("Get.Value", "ATTRIBUTE", "FerryQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=0", "@t1"),
        ("Display.Conversation", "Milkmaid", "A ferry ticket? My sister sails the ferry, down at the pier in the south. Ask her first.", "I will.", "@bye"),
        ("End",),
        "t1:",
        (">Conditional", "$Variable.1=1", "@t2"),
        ("Update.Attribute", "FerryQuest", "=2"),
        ("Display.Conversation", "Milkmaid", "She sent you? I keep her ticket book.\\A ticket costs three eggs: the hens lay in the nests round the farm. Bring me three and it's yours.", "I'll find some eggs.", "@bye"),
        ("End",),
        "t2:",
        (">Conditional", "$Variable.1=2", "@t3"),
        (">Got.Item", "Egg", "3", "@noeggs"),
        ("Take.Item", "Egg", "3"),
        ("Give.Item", "Ferry_Ticket", "1"),
        ("Update.Attribute", "FerryQuest", "=3"),
        ("Display.Conversation", "Milkmaid", "Three lovely eggs! Here's your ticket, stamped and all. Show it to my sister on the pier.", "Thank you!", "@tdone"),
        "tdone:",
        ("Display.Message", "Yellow", "Passage to the Mainland: take the ticket to the ferrywoman on the pier."),
        ("End",),
        "noeggs:",
        ("Display.Conversation", "Milkmaid", "Three eggs, love. Use Collect on the hens' nests round the farm.", "I'll keep looking.", "@bye"),
        ("End",),
        "t3:",
        ("Display.Conversation", "Milkmaid", "You've had your ticket. After the first crossing my sister just charges a gold coin.", "Right.", "@bye"),
        ("End",),
        "wool:",
        ("Display.Conversation", "Milkmaid", "Spin it into balls of wool on a workbench, there's one behind me. Cowhide can be tanned into leather there too.", "Thanks!", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Fisherman"] = [
        ("Display.Conversation", "Fisherman", "Fish are biting today! Bait your hook with a worm and anything in the sea will bite.\\Once you're handy with a rod, the trout go mad for it.",
         "What do you sell?", "@shop", "Any big catches about?", "@eels", "Goodbye.", "@bye"),
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Fisherman", "SHOP-Fishing", "@bye"),
        ("End",),
        "eels:",
        ("Display.Conversation", "Fisherman", "Cave eels! Pale as ghosts, they live in the black pools deep underground. You'll want real skill (Fishing 15) to land one.\\I pay well for them, cooked or raw.", "I'll look for them.", "@bye"),
        "bye:",
        ("End",)]
    S["Talk to Dog"] = [("Display.Conversation", "Dog", "Woof! Woof!\\(The dog wags its tail hopefully.)", "Good dog.", "@bye"),
                        "bye:", ("End",)]
    return S


def quest_scripts():
    S = {}
    # ---------------------------------------------------------------- The Herbalist's Remedy (RemedyQuest 0-2)
    S["Talk to Herbalist"] = [
        ("Get.Value", "ATTRIBUTE", "RemedyQuest", "Variable.1$"),
        ("Display.Conversation", "Herbalist", "Herbs, potions, remedies... what ails you, dear?\\Bring me three herbs and an empty vial and I'll brew you a healing potion.",
         "Brew me a potion.", "@brew", "Show me your potions.", "@shop", "Can I help you?", "@quest", "Goodbye.", "@bye"),
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
        ("End",),
        "quest:",
        (">Conditional", "$Variable.1=0", "@q1"),
        ("Display.Conversation", "Herbalist", "Bless you, I could use a hand. Three of the King's guards were bitten by giant spiders down the mine.\\For a poultice I need 3 cave mushrooms (they glow in the old iron mine) and 2 spider silk from the spiders in the mine depths.",
         "I'll gather them.", "@accept", "Not now.", "@bye"),
        ("End",),
        "accept:",
        ("Update.Attribute", "RemedyQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Herbalist's Remedy."),
        ("End",),
        "q1:",
        (">Conditional", "$Variable.1=1", "@qdone"),
        (">Got.Item", "Cave_Mushroom", "3", "@notyet"),
        (">Got.Item", "Spider_Silk", "2", "@notyet"),
        ("Take.Item", "Cave_Mushroom", "3"),
        ("Take.Item", "Spider_Silk", "2"),
        ("Display.Conversation", "Herbalist", "You found them all! The guards will be on their feet in no time.\\Take these potions, and let me show you a thing or two about potion making. My alchemy table is yours to use.",
         "Thank you!", "@reward"),
        "reward:",
        ("Give.Item", "Super_Potion", "2"),
        ("Give.Item", "Gold_Coin(s)", "60"),
        ("Update.Skill", "Potion_Making", "+2"),
        ("Update.Attribute", "RemedyQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete! You receive 2 super potions, 60 gold and Potion Making experience."),
        ("End",),
        "notyet:",
        ("Display.Conversation", "Herbalist", "I still need 3 cave mushrooms and 2 spider silk, dear.\\Pick the mushrooms in the old iron mine; the giant spiders live in the mine depths beyond it.",
         "I'll keep looking.", "@bye"),
        ("End",),
        "qdone:",
        ("Display.Conversation", "Herbalist", "The guards are mending nicely, thanks to you. Use my alchemy table whenever you like.", "Glad to help.", "@bye"),
        "bye:",
        ("End",)]

    # ---------------------------------------------------------------- The Dwarf's Grudge (DwarfQuest 0-2)
    S["Talk to Dwarf"] = [
        ("Get.Value", "ATTRIBUTE", "DwarfQuest", "Variable.1$"),
        ("Display.Conversation", "Dwarf", "Well met! Brokk Stonebeard, last of the deep miners.\\Gold, gems, good steel: I trade in all of it. And my forge is hot if you've ore to work.",
         "What do you trade?", "@shop", "Can I use your forge?", "@forge", "Do you need help?", "@work", "Goodbye.", "@bye"),
        "shop:",
        ("Display.Item.Rack", "SPECIFIC", "Dwarf", "SHOP-Dwarf", "@bye"),
        ("End",),
        "forge:"] + forge_choice("Dwarf", "Furnace's on the left, anvil on the right. Mind your beard.") + [
        "work:",
        (">Conditional", "$Variable.1=0", "@w1"),
        ("Display.Conversation", "Dwarf", "Help? Aye. The dead walk in my halls: skeletons of the old miners, raised by who knows what.\\And a cave troll has taken the crystal vein by the lake. Smash four skeletons and kill the troll, and I'll make it worth your while.",
         "Consider it done.", "@accept", "Not now.", "@bye"),
        ("End",),
        "accept:",
        ("Update.Attribute", "DwarfQuest", "=1"),
        ("Update.Attribute", "SkeletonsSlain", "=0"),
        ("Update.Attribute", "TrollSlain", "=0"),
        ("Display.Message", "Yellow", "Quest started: The Dwarf's Grudge."),
        ("End",),
        "w1:",
        (">Conditional", "$Variable.1=1", "@wdone"),
        ("Get.Value", "ATTRIBUTE", "SkeletonsSlain", "Variable.2$"),
        ("Get.Value", "ATTRIBUTE", "TrollSlain", "Variable.3$"),
        (">Conditional", "$Variable.2>=4 and $Variable.3>=1", "@wnot"),
        ("Display.Conversation", "Dwarf", "Ha! The troll is dead and the bones lie still. My halls are mine again!\\Take this blade: dwarf steel, the best there is. And some stones from the vein.\\My vault, west of the forge, is open to you now.",
         "Thank you, Brokk.", "@reward"),
        "reward:",
        ("Give.Item", "Steel_Sword", "1"),
        ("Give.Item", "Sapphire", "2"),
        ("Give.Item", "Gold_Coin(s)", "150"),
        ("Update.Skill", "Mining", "+2"),
        ("Update.Attribute", "DwarfQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete! You receive a steel sword, 2 sapphires, 150 gold and Mining experience. Brokk's vault is open to you."),
        ("End",),
        "wnot:",
        ("Display.Conversation", "Dwarf", "Skeletons smashed: $Variable.2 of 4. Trolls slain: $Variable.3 of 1.\\The skeletons wander all over the Hollow; the troll lairs south-east, past the lake.",
         "I'll get back to it.", "@bye"),
        ("End",),
        "wdone:",
        ("Display.Conversation", "Dwarf", "My halls are quiet again, friend. Mine the crystal vein any time you like, if you've the skill for it.\\And help yourself to what's in my vault, west of the forge.", "Thanks.", "@bye"),
        "bye:",
        ("End",)]
    S["Kill Skeleton"] = [
        "// Counts skeletons for Brokk (DwarfQuest=1), up to 4",
        ("Get.Value", "ATTRIBUTE", "DwarfQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Get.Value", "ATTRIBUTE", "SkeletonsSlain", "Variable.2$"),
        (">Conditional", "$Variable.2<4", "@end"),
        ("Update.Attribute", "SkeletonsSlain", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.2+1", "Variable.3$"),
        ("Display.Message", "Yellow", "Skeletons smashed for Brokk: $Variable.3 of 4."),
        "end:",
        ("End",)]
    S["Kill Cave_Troll"] = [
        "// The troll for Brokk (DwarfQuest=1)",
        ("Get.Value", "ATTRIBUTE", "DwarfQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Update.Attribute", "TrollSlain", "=1"),
        ("Display.Message", "Yellow", "The cave troll is dead! Brokk will want to hear about this."),
        "end:",
        ("End",)]

    # ---------------------------------------------------------------- The Beggar's Lost Key (BeggarQuest 0-2)
    S["Talk to Beggar"] = [
        ("Get.Value", "ATTRIBUTE", "BeggarQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=2", "@normal"),
        ("Display.Conversation", "Beggar", "You found my old key? Then the house on the Isle is yours, friend.\\Mind the cellar. The back wall fell in years ago, and there are rats down there the size of dogs.",
         "Thanks!", "@bye"),
        ("End",),
        "normal:",
        ("Display.Conversation", "Beggar", "Spare a coin for a poor old man?", "Here's a coin.", "@give", "Sorry, no.", "@bye"),
        "give:",
        (">Got.Item", "Gold_Coin(s)", "1", "@broke"),
        ("Take.Item", "Gold_Coin(s)", "1"),
        ("Display.Conversation", "Beggar", "Bless you! I wasn't always like this, you know.\\I had a fine brick house on the Isle, but I lost the key in the old iron mine when the hobgoblins chased me out. They took it down to their warren.\\If you ever find it, the house is yours. I'll never go back.",
         "I'll look for it.", "@story"),
        "story:",
        (">Conditional", "$Variable.1=0", "@bye"),
        ("Update.Attribute", "BeggarQuest", "=1"),
        ("Display.Message", "Yellow", "Quest started: The Beggar's Lost Key."),
        ("End",),
        "broke:",
        ("Display.Message", "DarkRed", "You don't have any gold!"),
        "bye:",
        ("End",)]
    # The house door on the Isle (1,1,0 tile 20,7) is a Lock: open while Door1Open>=1 or the player carries the Key.
    # Unlocking it (the Unlock verb, using the key on it, or walking in with the key: the Beggar House trigger)
    # sets Door1Open and completes the quest.
    S["Unlock Door001"] = [
        "// The beggar's house door (1,1,0). Its Lock line opens it while Door1Open>=1 or the player has the Beggars_House_Key.",
        (">On.Map", "1,1,0", "@other"),
        (">Got.Item", "Beggars_House_Key", "1", "@nokey"),
        ("Get.Value", "ATTRIBUTE", "Door1Open", "Variable.2$"),
        (">Conditional", "$Variable.2=0", "@open"),
        ("Display.Message", "Cyan", "You unlock the door with the beggar's old key!"),
        ("Play.Sound", "Door"),
        ("Update.Attribute", "Door1Open", "=1"),
        "quest:",
        ("Get.Value", "ATTRIBUTE", "BeggarQuest", "Variable.1$"),
        (">Conditional", "$Variable.1<2", "@end"),
        ("Update.Attribute", "BeggarQuest", "=2"),
        ("Display.Message", "Yellow", "Quest complete: the beggar's house on the Isle is yours!"),
        "end:",
        ("End",),
        "open:",
        ("Display.Message", "Cyan", "The door is already unlocked."),
        ("Goto.Line", "@quest"),
        "nokey:",
        ("Display.Message", "DarkRed", "It's locked, and you don't have the key."),
        ("End",),
        "other:",
        ("Display.Message", "DarkRed", "You don't have a key for this door."),
        ("End",)]
    S["Use Beggars_House_Key With Door001"] = [("Goto.Script", "Unlock Door001"), ("End",)]
    # the other doors (Door002 in stone, Door003 in rock) find this by their name without the number
    S["Use Beggars_House_Key With Door"] = [("Goto.Script", "Unlock Door001"), ("End",)]
    S["Beggar House"] = [
        "// Trigger just inside the beggar's house door (1,1,0 tile 20,6): walking in with the key unlocks it for good",
        "// and completes the quest (coming up from the cellar without the key does nothing).",
        (">Got.Item", "Beggars_House_Key", "1", "@end"),
        ("Get.Value", "ATTRIBUTE", "Door1Open", "Variable.2$"),
        (">Conditional", "$Variable.2=0", "@end"),
        ("Goto.Script", "Unlock Door001"),
        "end:",
        ("End",)]
    return S


# Hobgoblin counter: only count up to five, so the quest log never shows "7 of 5".
def kill_hobgoblin():
    return [
        "// Run by the engine (Kill.NPC looks up Kill <Name>) whenever a hobgoblin dies",
        ("Get.Value", "ATTRIBUTE", "HobgoblinQuest", "Variable.1$"),
        (">Conditional", "$Variable.1=1", "@end"),
        ("Get.Value", "ATTRIBUTE", "HobgoblinsSlain", "Variable.2$"),
        (">Conditional", "$Variable.2<5", "@end"),
        ("Update.Attribute", "HobgoblinsSlain", "+1"),
        ("Get.Value", "CALCULATION", "$Variable.2+1", "Variable.2$"),
        (">Conditional", "$Variable.2<5", "@enough"),
        ("Display.Message", "Yellow", "Hobgoblins slain for King Tyron: $Variable.2 of 5."),
        ("End",),
        "enough:",
        ("Display.Message", "Yellow", "That's five hobgoblins! Return to King Tyron for your reward."),
        "end:",
        ("End",)]


# =========================================================================================== data tables
TILES = {
    # name: (walkable, show_name, use_words, examine, line_of_sight, minimap colour or None = average of sprite)
    "Cave_Floor001": ("1" * 49, None, None, None, None, "80 72 64"),
    "Cave_Floor002": ("1" * 49, "0", "", "Loose gravel crunches underfoot.", "1", None),
    "Cave_Floor003": ("1" * 49, "0", "", "Damp rock, slick with moss.", "1", None),
    "Cave_Wall001": ("0" * 49, "1", None, "Solid rock.", "0", "58 52 47"),
    "Cave_Wall002": ("0" * 49, "1", "", "A wall of rough rock.", "0", None),
    "Cave_Wall003": ("0" * 49, "1", "", "A torch burns in an iron bracket.", "0", None),
    # the house door in a grey stone wall and in cave rock (farm_tiles.py; put in place by door_walls below)
    "Door002": ("1" * 49, "1", "Open,Unlock", None, "0", None),
    "Door003": ("1" * 49, "1", "Open,Unlock", None, "0", None),
    # the villages' other walls and their doors (house_tiles.py; laid out by villages.py)
    "Timber001": ("0" * 49, "1", "", "A wall of stout timber boards.", "0", None),
    "Plaster001": ("0" * 49, "1", "", "Whitewashed plaster between dark oak beams.", "0", None),
    "Sandstone001": ("0" * 49, "1", "", "Warm, sand-coloured stone.", "0", None),
    "Door004": ("1" * 49, "1", "Open,Unlock", None, "0", None),
    "Door005": ("1" * 49, "1", "Open,Unlock", None, "0", None),
    "Door006": ("1" * 49, "1", "Open,Unlock", None, "0", None),
    # furniture, stairs and ladders in the village houses (interior_tiles.py; put in by villages.lay_house)
    "Bed001": ("0" * 49, "1", "", "A bed with a patchwork quilt. It looks very comfortable.", "1", None),
    "Bed002": ("0" * 49, "1", "", "A bed with a patchwork quilt. It looks very comfortable.", "1", None),
    "Table001": ("0" * 49, "1", "", "A sturdy kitchen table, with a candle and a fresh loaf on it.", "1", None),
    "Chair001": ("1" * 49, "1", "", "A wooden chair.", "1", None),
    "Chair002": ("1" * 49, "1", "", "A wooden chair.", "1", None),
    "Chair003": ("1" * 49, "1", "", "A wooden chair.", "1", None),
    "Chair004": ("1" * 49, "1", "", "A wooden chair.", "1", None),
    "Potted_Plant001": ("1111111" "1111111" "1100011" "1100011" "1100011" "1111111" "1111111", "1", "",
                        "A leafy plant in a clay pot. Someone waters it every day.", "1", None),
    "Bookshelf001": ("0" * 49, "1", "", "Shelves of well-thumbed books: almanacs, ballads and a herbal.", "1", None),
    "Fireplace001": ("0" * 49, "1", "", "A stone hearth with a crackling fire. Good for cooking on, too.", "0", None),
    "Fireplace002": ("0" * 49, "1", "", "A stone hearth with a crackling fire. Good for cooking on, too.", "0", None),
    "Fireplace003": ("0" * 49, "1", "", "A red brick hearth with a crackling fire. Good for cooking on, too.", "0", None),
    # rugs (interior_tiles.py: Rug001-009 on planks, Rug011-019 on stone tiles; put down by villages.lay_rug)
    **{"Rug%03d" % (b + k): ("1" * 49, "1", "", "A woven rug, warm underfoot.", "1", None)
       for b in (1, 31) for k in list(range(9)) + list(range(10, 17))},
    # King Tyron's palace on the Royal Isle (palace_tiles.py; laid out by build_palace.py)
    "Paving001": ("1" * 49, "0", "", "", "1", None),
    "Marble001": ("1" * 49, "0", "", "", "1", None),
    "Carpet001": ("1" * 49, "1", "", "The royal carpet, red and gold.", "1", None),
    "Carpet002": ("1" * 49, "1", "", "The dais before the throne.", "1", None),
    "Throne001": ("0" * 49, "1", "", "The throne of the Southlands, gilded and cushioned in red.", "1", None),
    "Pillar001": ("0" * 49, "1", "", "A marble column, fluted and gilded at the top.", "0", None),
    "Banner001": ("0" * 49, "1", "", "The royal banner: a gold crown on blue.", "0", None),
    "Wall_Torch001": ("0" * 49, "1", "", "A torch burns in an iron sconce.", "0", None),
    "Statue001": ("0" * 49, "1", "", "A stone knight of old, sword raised, keeps watch.", "1", None),
    "Statue002": ("0" * 49, "1", "", "A stone knight of old, sword raised, keeps watch.", "1", None),
    "Fountain001": ("0" * 49, "1", "", "A fountain of clear water. Coins glint on the bottom.", "1", None),
    "Hedge001": ("0" * 49, "1", "", "A neatly clipped box hedge.", "1", None),
    "Stairs001": ("1" * 49, "1", "Climb Up", "Stairs going up to the floor above.", "1", "255 0 0"),
    "Stairs002": ("1" * 49, "1", "Climb Down", "Stairs going down.", "1", "255 0 0"),
    "Ladder008": ("1" * 49, "1", "Climb Up", "A ladder up to the loft.", "1", "255 0 0"),
    "Ladder009": ("1" * 49, "1", "Climb Down", "A trapdoor with a ladder going down.", "1", "255 0 0"),
    # the walls of Wardhaven (build_walled.py); the gate opens (Unlocked.Tile, TILE_EXTRA) when its Lock does
    "City_Wall001": ("0" * 49, "1", "", "The town wall: dressed stone, battlements and arrow slits.", "0", "128 124 116"),
    "City_Wall002": ("0" * 49, "1", "", "The town wall: dressed stone, battlements and arrow slits.", "0", "128 124 116"),
    "City_Wall004": ("0" * 49, "1", "", "The town wall: dressed stone, battlements and arrow slits.", "0", "128 124 116"),
    "City_Wall003": ("0" * 49, "1", "", "A squat tower on the town wall.", "0", "112 108 100"),
    "City_Wall005": ("0" * 49, "1", "", "A squat tower on the town wall.", "0", "112 108 100"),
    "City_Gate001": ("1" * 49, "1", "", "Great oak gates, bound with iron and barred shut.", "0", "112 72 42"),
    "City_Gate003": ("1" * 49, "1", "", "The gatehouse arch, with the town's arms over it. The gates below are barred shut.", "0", "112 72 42"),
    "City_Gate002": ("1" * 49, "1", "", "The town gates stand open.", "1", "126 92 56"),
    "City_Gate004": ("1" * 49, "1", "", "The gatehouse arch, with the town's arms over it.", "1", "126 92 56"),
    "Cave_Rubble001": ("1" * 49, "1", "", "Rubble from a rockfall.", "1", None),
    "Stalagmite001": ("1111111" "1111111" "1110111" "1100011" "1100011" "1100011" "1111111", "1", "",
                      "A stalagmite, built up drip by drip over thousands of years.", "1", None),
    "Cave_Pool001": ("0" * 49, "1", "", "Black, still water. Something pale moves beneath the surface.", "1", None),
    "Cave_Puddle001": ("1" * 49, "0", "", "A shallow puddle of cold water.", "1", None),
    "Mushroom_Patch001": ("1" * 49, "1", "Pick", "Mushrooms that glow a soft blue. The herbalist would love these.", "1", None),
    "Mushroom_Patch002": ("1" * 49, "1", "", "Someone has picked these mushrooms. They'll grow back.", "1", None),
    "Ore_Rock001": (None, None, None, "A rock streaked with iron ore.", None, "176 100 52"),
    "Ore_Rock002": (None, None, None, "This rock has been mined out. The ore may come back in time.", None, "92 88 84"),
    "Copper_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                       "A rock with green and orange copper ore in it.", "1", None),
    "Coal_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                     "A rock studded with black coal. (Mining 5)", "1", None),
    "Gold_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                     "Gold glitters in the rock! (Mining 15)", "1", None),
    "Gem_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                    "Crystals grow out of this rock. There may be gems inside. (Mining 20)", "1", None),
    "Tin_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                    "A rock with dull grey tin ore in it. Smelt tin with copper to make bronze.", "1", None),
    "Silver_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                       "Bright veins of silver run through this rock. (Mining 12)", "1", None),
    "Mithril_Rock001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Mine",
                        "Blue-green mithril shimmers in the rock. (Mining 25, and a steel pickaxe or better)", "1", None),
    "Mine_Track001": ("1" * 49, "1", "", "Old mine cart rails.", "1", None),
    "Mine_Track002": ("1" * 49, "1", "", "Old mine cart rails.", "1", None),
    "Mine_Support001": ("0111110" * 7, "1", "", "Timber props hold up the roof. Hopefully.", "1", None),
    "Ladder004": ("1" * 49, "1", "Climb Up", "A ladder up into the dark.", "1", "255 0 0"),
    "Ladder005": ("1" * 49, "1", "Climb Down", "A hatch with a ladder going down.", "1", "255 0 0"),
    "Ladder006": ("1" * 49, "1", "Climb Down", "A hole in the ground with a ladder going down into a cave.", "1", "255 0 0"),
    "Ladder007": ("1" * 49, "1", "Climb Down", "A hole in the ground with a ladder going down into the mine.", "1", "255 0 0"),
    "Oak_Tree001": ("1111111" "1000001" "1000000" "1000000" "1000001" "1100001" "1111111", "1", "Chop",
                    "A sturdy oak. Its logs burn long and make good handles. (Woodcutting 10)", "0", "60 92 30"),
    "Willow_Tree001": ("1111111" "1000001" "1000000" "1000000" "1000001" "1100001" "1111111", "1", "Chop",
                       "A weeping willow, trailing its branches in the water. (Woodcutting 20)", "0", "130 168 66"),
    "Yew_Tree001": ("1111111" "1000001" "1000000" "1000000" "1000001" "1100001" "1111111", "1", "Chop",
                    "An ancient yew, dark and twisted. Its wood is prized by staff-makers. (Woodcutting 35)", "0", "24 64 46"),
    "Berry_Bush001": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "Pick",
                      "A bush heavy with ripe red berries.", "1", None),
    "Berry_Bush002": ("1111111" "1100011" "1000001" "1000001" "1000001" "1100011" "1111111", "1", "",
                      "No berries left. They'll ripen again soon.", "1", None),
    "Herb_Patch001": ("1" * 49, "1", "Pick", "A patch of fragrant herbs.", "1", None),
    "Herb_Patch002": ("1" * 49, "1", "", "The herbs have been picked. They'll grow back.", "1", None),
    # "Walk here" first, so a left click still walks across the field; Harvest is in the right-click menu
    "Field001": ("1" * 49, "1", "", "Ploughed earth.", "1", None),
    "Nest001": ("1" * 49, "1", "Collect", "A hen's nest with fresh eggs in it.", "1", None),
    "Nest002": ("1" * 49, "1", "", "An empty nest. The hens will lay again soon.", "1", None),
}


PALACE_TILES = {"Paving001", "Marble001", "Carpet001", "Carpet002", "Throne001", "Pillar001", "Banner001",
                "Wall_Torch001", "Statue001", "Statue002", "Fountain001", "Hedge001"}      # (they keep their edges)

# Tiles.ini keys besides the six in TILES: {tile: [(key, value)]}
TILE_EXTRA = {"City_Gate001": [("Unlocked.Tile", "City_Gate002")], "City_Gate003": [("Unlocked.Tile", "City_Gate004")],
              "Paving001": [("Blend", "2")]}       # (the brick road blends as the dirt path does)


def item(value, examine, stack=1, food=0, use="", droppable=None):
    keys = [("Type", "MapItem")]
    if use:
        keys.append(("Use.Words", use))
    keys += [("Examine.Info", examine), ("Stackable", str(stack))]
    if droppable is not None:
        keys.append(("Droppable", str(droppable)))
    keys.append(("Value", str(value)))
    if food:
        keys.append(("Food.Value", str(food)))
    return keys


def good(examine, use="Talk to", speed=None):
    keys = [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", use), ("Examine.Info", examine)]
    if speed:
        keys.append(("Movement.Speed", speed))
    return keys


def bad(examine, hp, aspeed, strength, defence, aggro, move, aggressive, respawn, drops):
    return [("Type", "NPC"), ("Attitude", "Bad"), ("Examine.Info", examine), ("Hitpoints", str(hp)), ("Attack.Speed", str(aspeed)),
            ("Strength", str(strength)), ("Defence", str(defence)), ("Aggro.Range", str(aggro)),
            ("Weapon.Range", "0"), ("Movement.Speed", str(move)), ("Aggressive", str(aggressive)),
            ("Respawn", str(respawn)), ("Drops", drops)]


def station(use, examine):
    return [("Type", "StaticObject"), ("Use.Words", use), ("Examine.Info", examine)]


ENTITIES = {
    # the wheat field (farm_tiles.py draws them): plants you harvest, and the stubble left for a while
    "Ripe_Wheat001": [("Type", "StaticObject"), ("Use.Words", "Harvest"), ("Examine.Info", "Ripe golden wheat."), ("Solid", "0")],
    "Ripe_Wheat002": [("Type", "StaticObject"), ("Use.Words", "Harvest"), ("Examine.Info", "Ripe golden wheat."), ("Solid", "0")],
    "Ripe_Wheat003": [("Type", "StaticObject"), ("Use.Words", "Harvest"), ("Examine.Info", "Ripe golden wheat."), ("Solid", "0")],
    "Stubble": [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Examine.Info", "Stubble. The wheat will grow again."),
                ("Solid", "0")],
    # ores, gems and bars
    "Copper_Ore": item(2, "A lump of copper ore. Smelt it into a copper bar.", 50),
    "Coal": item(4, "A lump of coal. A smith needs it to make steel.", 50),
    "Gold_Ore": item(12, "Gold ore, flecked with yellow. Smelt it into a gold bar.", 50),
    "Sapphire": item(40, "A deep blue sapphire.", 20),
    "Emerald": item(60, "A brilliant green emerald.", 20),
    "Copper_Bar": item(5, "A bar of copper. Soft, but pretty.", 20),
    "Steel_Bar": item(20, "A bar of strong steel, made from iron and coal.", 20),
    "Gold_Bar": item(30, "A heavy bar of gold. A jeweller could use this.", 20),
    "Tin_Ore": item(2, "A lump of tin ore. Smelt it with copper ore to make bronze.", 50),
    "Silver_Ore": item(15, "Silver ore, bright where it's broken. Smelt it into a silver bar.", 50),
    "Mithril_Ore": item(40, "Mithril ore. It's light as a feather and shimmers blue-green.", 50),
    "Bronze_Bar": item(6, "A bar of bronze, made from copper and tin.", 20),
    "Silver_Bar": item(35, "A bar of shining silver. A jeweller could use this.", 20),
    "Mithril_Bar": item(90, "A bar of mithril. Only a master smith can work it.", 20),
    # tools: the better the tool, the likelier a strike (see PICKAXES and AXES)
    # logs (Woodcutting tiers): burn longer (Firemaking), make better handles (Smithing) and staffs (Crafting)
    "Oak_Logs": item(6, "Oak logs: heavy and strong. They burn long, and make good tool handles.", 20),
    "Willow_Logs": item(12, "Pale, springy willow logs.", 20),
    "Yew_Logs": item(30, "Dark red yew logs, hard as iron. Staff-makers pay well for these.", 20),
    # fish and food (Fishing and Cooking tiers: the better the food, the more it heals)
    "Raw_Salmon": item(14, "A fat silver salmon. Cook it on a fire or a range (Cooking 20).", 1),
    "Cooked_Salmon": item(20, "Pink, flaky salmon. Heals 9.", 1, food=9, use="Eat"),
    "Raw_Swordfish": item(30, "A swordfish, as long as your arm. Cook it on a fire or a range (Cooking 35).", 1),
    "Cooked_Swordfish": item(45, "A thick swordfish steak. Heals 14.", 1, food=14, use="Eat"),
    "Meat_Pie": item(15, "A meat pie with a golden crust. Heals 7.", 1, food=7, use="Eat"),
    "Stew": item(22, "A hearty bowl of stew. Heals 10.", 1, food=10, use="Eat"),
    # potions that boost you for a while (data\\Spells.ini, Kind=Potion)
    "Defence_Potion": item(45, "An amber potion: +4 Defence for two minutes. Drink it before a fight.", 1, use="Drink") + [("Spell", "Defence_Potion")],
    "Combat_Potion": item(70, "A purple potion: +3 Attack and +3 Defence for two minutes.", 1, use="Drink") + [("Spell", "Combat_Potion")],
    "Magic_Potion": item(90, "A violet potion: your spells do 5 more damage for two minutes.", 1, use="Drink") + [("Spell", "Magic_Potion")],
    "Ferry_Ticket": item(0, "A ticket for the Northgate ferry, stamped by the milkmaid. Good for one crossing.", 1, droppable=0),
    "Owl_Potion": item(40, "A smoky blue potion that smells of the night: you see far further through the fog for three minutes.", 1, use="Drink") + [("Spell", "Owl_Potion")],
    "Mega_Potion": item(120, "A brilliant green potion that heals almost any wound (45-55 hitpoints).", 1, use="Drink") + [("Spell", "Mega_Potion")],
    "Bronze_Pickaxe": item(8, "A bronze pickaxe. It'll do, for soft rock.", 1),
    "Steel_Pickaxe": item(60, "A steel pickaxe. It bites deep, and can break mithril rock.", 1),
    "Mithril_Pickaxe": item(160, "A mithril pickaxe, light and keen. The best there is.", 1),
    "Bronze_Axe": item(7, "A bronze axe. A bit blunt.", 1),
    "Steel_Axe": item(50, "A sharp steel axe.", 1),
    "Mithril_Axe": item(140, "A mithril axe. Trees practically fall over by themselves.", 1),
    # smithing and crafting products
    "Shears": item(8, "For shearing sheep.", 1),
    "Leather": item(8, "A piece of tanned leather.", 20),
    "Ball_of_Wool": item(5, "A ball of spun wool.", 20),
    # equipment (see EQUIPMENT below for the table it's generated from)
    # crafting stations and props
    "Chest": station("Open", "A sturdy iron-bound chest."),
    # gathered and farm goods
    "Berries": item(1, "A handful of juicy red berries.", 30, food=1, use="Eat"),
    "Cave_Mushroom": item(3, "A glowing cave mushroom. Edible, just about.", 30, food=1, use="Eat"),
    "Wheat": item(1, "A sheaf of wheat. Grind it into flour at a range.", 30),
    "Flour": item(3, "A sack of flour. Bake it into bread.", 20),
    "Wool": item(2, "A clump of sheep's wool.", 30),
    "Cowhide": item(4, "The hide of a cow. Tan it into leather on a workbench.", 20),
    "Spider_Silk": item(6, "Strong, sticky spider silk. The herbalist uses it for bandages.", 30),
    "Bucket_of_Milk": item(8, "A bucket of fresh milk.", 1, use="Drink"),
    # food
    "Raw_Trout": item(6, "A speckled trout. Cook it on a fire or a range (Cooking 10).", 1),
    "Cooked_Trout": item(10, "A nicely cooked trout.", 1, food=5, use="Eat"),
    "Raw_Cave_Eel": item(10, "A pale, wriggling cave eel. Cook it on a fire or a range (Cooking 15).", 1),
    "Cooked_Cave_Eel": item(16, "Smoky cave eel. Surprisingly good!", 1, food=7, use="Eat"),
    "Berry_Pie": item(12, "A berry pie with a lattice crust.", 1, food=6, use="Eat"),
    "Fish_Pie": item(18, "A hearty fish pie.", 1, food=8, use="Eat"),
    # potions
    "Super_Potion": item(40, "A strong healing potion. Drink it to restore 40 hitpoints.", 1, use="Drink"),
    "Strength_Potion": item(60, "A fiery red potion. It makes you stronger.", 1, use="Drink"),
    # crafting stations and props
    "Furnace": station("Smelt", "A furnace, roaring hot. Smelt ore into bars here."),
    "Anvil": station("Smith", "A heavy anvil. Hammer bars into tools and weapons here."),
    "Range": station("Cook", "A cooking range. Cook raw food on it, or bake."),
    "Alchemy_Table": station("Brew", "Bottles, burners and a mortar. Brew potions here."),
    "Workbench": station("Craft", "A sturdy workbench for leather, wool and jewellery."),
    "Mine_Cart": station("Search", "An old mine cart, still half full of ore."),
    # people
    "Guard": good("A guard of King Tyron, spear in hand."),
    "Quartermaster": good("The keep's quartermaster. He counts everything twice."),
    "Villager": good("A local, going about their business.", speed="1"),
    "Milkmaid": good("The milkmaid, who looks after the Isle's cows and sheep."),
    "Fisherman": good("An old fisherman in a yellow oilskin. He smells of the sea."),
    "Dwarf": good("Brokk Stonebeard, a dwarf miner. His beard reaches his belt."),
    "Dog": good("A friendly brown dog.", use="Pet,Talk to", speed="2"),
    # animals and monsters (easy -> hard)
    "Rat": bad("A big, filthy rat.", 4, 1, 1, 1, 50, 1.5, 1, 20, "Bones,1-1,40"),
    "Bat": bad("A cave bat. It flits about in the dark.", 5, 0.8, 1, 2, 80, 2.5, 1, 20, "Bones,1-1,30"),
    "Cow": bad("A big brown and white cow. Moo.", 10, 1.5, 1, 1, 0, 0.8, 0, 30,
               "Bones,1-1,100 Raw_Meat,1-2,100 Cowhide,1-1,100"),
    "Sheep": bad("A woolly sheep. Baa.", 7, 1.5, 1, 1, 0, 1, 0, 30, "Bones,1-1,100 Raw_Meat,1-1,100 Wool,1-2,100"),
    "Wolf": bad("A grey wolf. It looks hungry.", 14, 1, 3, 2, 90, 2.5, 1, 30, "Bones,1-1,100 Raw_Meat,1-1,70"),
    "Giant_Spider": bad("A giant spider, as big as a dog.", 12, 1, 2, 2, 70, 2, 1, 30,
                        "Spider_Silk,1-1,60 Gold_Coin(s),1-3,20"),
    "Skeleton": bad("The bones of a long-dead miner, still swinging a rusty sword.", 22, 1.3, 4, 4, 70, 1.5, 1, 40,
                    "Bones,1-2,100 Gold_Coin(s),3-10,60 Iron_Sword,1-1,5 Iron_Helm,1-1,4 Lightning_Scroll,1-1,5 "
                    "Teleport_Scroll,1-1,6 Stone_Skin_Scroll,1-1,5"),
    "Cave_Troll": bad("A huge cave troll. Its club is the size of a tree.", 60, 1.6, 7, 6, 80, 1.2, 1, 120,
                      "Bones,2-3,100 Gold_Coin(s),20-40,100 Gold_Ore,1-2,50 Sapphire,1-1,30 Emerald,1-1,20 Steel_Helm,1-1,15 "
                      "Fire_Storm_Scroll,1-1,35"),
}

# ----- equipment: name -> (value, examine, slot, attack, defence, requires)
# Balanced against the monsters (Strength/Defence 1 for rats and goblins, 2-3 for wolves and hobgoblins, 4 for
# skeletons, 7/6 for the cave troll): a full leather set is +6 defence, iron about +11, steel about +17.
# Weapons: copper dagger +1, iron sword +3, steel sword +5. Rings give small bonuses. Requires = "Skill level" pairs.
EQUIPMENT = {
    # weapons
    "Copper_Dagger": (10, "A short copper dagger. Better than your fists.", "Weapon", 1, 0, ""),
    "Iron_Sword": (30, "A plain iron sword. Heavy and honest.", "Weapon", 3, 0, ""),
    "Steel_Sword": (70, "A fine steel sword with a gilded guard.", "Weapon", 5, 0, "Strength 10"),
    # shields
    "Iron_Shield": (35, "A round iron shield with a red cross.", "Shield", 0, 2, "Defence 5"),
    "Steel_Shield": (80, "A steel kite shield with a gold chevron.", "Shield", 0, 4, "Defence 10"),
    # leather (Crafting, workbench)
    "Leather_Cap": (12, "A snug leather cap.", "Head", 0, 1, ""),
    "Leather_Body": (30, "A laced leather jerkin. Light, and better than nothing.", "Body", 0, 2, ""),
    "Leather_Legs": (22, "Stout leather leggings.", "Legs", 0, 1, ""),
    "Leather_Gloves": (12, "Supple leather gloves.", "Hands", 0, 1, ""),
    "Leather_Boots": (20, "Sturdy leather boots.", "Feet", 0, 1, ""),
    # iron (Smithing, anvil)
    "Iron_Helm": (25, "An iron helm with a nose guard.", "Head", 0, 2, "Defence 5"),
    "Iron_Platebody": (60, "A heavy iron breastplate.", "Body", 0, 3, "Defence 5"),
    "Iron_Platelegs": (40, "Iron leg plates. They clank.", "Legs", 0, 2, "Defence 5"),
    # steel (Smithing, anvil)
    "Steel_Helm": (55, "A polished steel helm with a gilded crest.", "Head", 0, 3, "Defence 10"),
    "Steel_Platebody": (140, "A gleaming steel breastplate, trimmed with gold.", "Body", 0, 5, "Defence 15"),
    "Steel_Platelegs": (90, "Steel leg plates, light for their strength.", "Legs", 0, 3, "Defence 10"),
    # bronze (Smithing, anvil): between leather and iron
    "Bronze_Sword": (18, "A short bronze sword.", "Weapon", 2, 0, ""),
    "Bronze_Helm": (12, "A bronze helm. It rings when you knock on it.", "Head", 0, 1, ""),
    "Bronze_Shield": (16, "A round bronze shield.", "Shield", 0, 1, ""),
    "Bronze_Platebody": (30, "A bronze breastplate.", "Body", 0, 2, ""),
    "Bronze_Platelegs": (22, "Bronze leg plates.", "Legs", 0, 2, ""),
    # iron and steel boots and gauntlets
    "Iron_Boots": (20, "Iron-shod boots. Heavy going.", "Feet", 0, 2, "Defence 5"),
    "Iron_Gauntlets": (20, "Iron gauntlets. A solid grip on your sword.", "Hands", 1, 1, "Defence 5"),
    "Steel_Boots": (45, "Steel boots with gilded toes.", "Feet", 0, 3, "Defence 10"),
    "Steel_Gauntlets": (45, "Steel gauntlets with gilded cuffs.", "Hands", 1, 2, "Defence 10"),
    # mithril (Smithing, anvil): the best armour there is
    "Mithril_Sword": (220, "A mithril sword. It weighs nothing and cuts like the wind.", "Weapon", 7, 0, "Strength 20"),
    "Mithril_Helm": (160, "A mithril helm, shimmering blue-green.", "Head", 0, 4, "Defence 20"),
    "Mithril_Shield": (240, "A mithril kite shield.", "Shield", 0, 6, "Defence 20"),
    "Mithril_Platebody": (400, "A mithril breastplate. Light as linen, hard as dragon scale.", "Body", 0, 7, "Defence 25"),
    "Mithril_Platelegs": (260, "Mithril leg plates.", "Legs", 0, 5, "Defence 20"),
    "Mithril_Boots": (130, "Mithril boots. You hardly know you're wearing them.", "Feet", 0, 3, "Defence 20"),
    "Mithril_Gauntlets": (130, "Mithril gauntlets.", "Hands", 2, 2, "Defence 20"),
    # rings and circlets (Crafting, workbench)
    "Silver_Ring": (30, "A silver ring. Your sword arm feels steadier.", "Ring", 1, 0, ""),
    "Silver_Tiara": (70, "A silver circlet. Elegant, and it turns a glancing blow.", "Head", 1, 1, ""),
    "Gold_Ring": (45, "A plain gold ring. It feels lucky.", "Ring", 0, 1, ""),
    # wooden shields (Crafting, workbench)
    "Wooden_Shield": (8, "A round wooden shield with an iron boss.", "Shield", 0, 1, ""),
    "Oak_Shield": (30, "A heavy oak shield, rimmed with brass.", "Shield", 0, 2, "Defence 5"),
    "Sapphire_Ring": (100, "A gold ring set with a sapphire. It wards off blows.", "Ring", 0, 2, ""),
    "Ruby_Ring": (120, "A gold ring set with a ruby. It burns with fighting spirit.", "Ring", 2, 0, ""),
    "Emerald_Ring": (140, "A gold ring set with an emerald. Sharp eyes, steady hand.", "Ring", 1, 1, ""),
}


def equip(value, examine, slot, attack, defence, requires):
    keys = [("Type", "MapItem"), ("Examine.Info", examine), ("Stackable", "1"), ("Value", str(value)),
            ("Slot", slot), ("Attack", str(attack)), ("Defence", str(defence))]
    if requires:
        keys.append(("Requires", requires))
    return keys


# Bows: Entities.ini Range = how far it shoots (pixels), Ammo = the item each shot uses up (see Update.Player.Combat)
ENTITIES.update({
    "Arrows": item(1, "Arrows with grey goose feathers. A bow uses one a shot.", 999),
    "Oak_Bow": equip(60, "An oak shortbow. Carry arrows and attack from a distance.", "Weapon", 2, 0, "") + [("Range", "160"), ("Ammo", "Arrows")],
    "Yew_Bow": equip(260, "A yew longbow: it shoots further and hits harder than oak.", "Weapon", 5, 0, "Strength 15") + [("Range", "224"), ("Ammo", "Arrows")],
})


for _n, _e in EQUIPMENT.items():
    ENTITIES[_n] = equip(*_e)

# ----- staffs (Crafting, workbench): Magic= is added to the damage (and healing) of every spell while wielded
STAFFS = {
    "Oak_Staff": (40, "A knotted oak staff. Spells come easier with it: +2 to their damage.", 1, 2, ""),
    "Willow_Staff": (120, "A willow staff set with a sapphire: +4 spell damage.", 1, 4, "Magic 10"),
    "Yew_Staff": (300, "A yew staff crowned with a ruby that glows like an ember: +7 spell damage.", 2, 7, "Magic 20"),
}
for _n, (_v, _ex, _att, _mag, _req) in STAFFS.items():
    ENTITIES[_n] = equip(_v, _ex, "Weapon", _att, 0, _req) + [("Magic", str(_mag))]

# Existing entities that get new keys (other keys are left alone)
ENTITY_KEYS = {
    "Goblin": [("Drops", "Bones,1-1,100 Gold_Coin(s),1-2,50 Fire_Bolt_Scroll,1-1,8")],
    "Hobgoblin": [("Drops", "Bones,1-1,100 Gold_Coin(s),2-6,60 Iron_Ore,1-1,25 Leather_Cap,1-1,4 Fire_Bolt_Scroll,1-1,10 "
                            "Ice_Bolt_Scroll,1-1,5 Healing_Scroll,1-1,6")],
    "Ruby": [("Stackable", "20")],
    "Chefs_Hat": [("Examine.Info", "A tall white hat. Very professional, and no use at all in a fight."),
                  ("Slot", "Head"), ("Attack", "0"), ("Defence", "0")],
    "Bucket": [("Examine.Info", "An empty bucket. Fill it with water, or milk a cow.")],
    "Pickaxe": [("Examine.Info", "An iron pickaxe, for mining rocks."), ("Stackable", "1")],
    "Logs": [("Examine.Info", "Ordinary logs. Burn them, or make handles and shields with them.")],
    "Axe": [("Examine.Info", "An iron axe. Sharp!")],
    "Iron_Ore": [("Examine.Info", "A lump of iron ore. Smelt two into an iron bar at a furnace."), ("Stackable", "50")],
    "Iron_Bar": [("Stackable", "20")],
    "Egg": [("Value", "3"), ("Stackable", "12")],               # a dozen to a slot
    "Raw_Meat": [("Stackable", "10")],
    "Bones": [("Stackable", "20")],
    "Raw_Poultry": [("Examine.Info", "Raw poultry. Cook it on a fire or a range.")],
    "Herb": [("Examine.Info", "A fragrant green herb. Used in potions.")],
    "Miner": [("Examine.Info", "Old Tom, the last miner in the iron mine.")],
}

# ----- NPC movement defaults (Entities.ini Roam.Radius, Chase.Radius, Walk.Speed, Pause; see dev\Data Formats.md)
# name: (roam radius in tiles, chase radius in tiles beyond the zone, walk speed as a fraction of Movement.Speed,
#        pause "min-max" seconds between moves). A map line's Options (NPC_OPTIONS below) override these per NPC.
MOVEMENT = {
    # people who must always be easy to find: they stand at their counter / throne
    "Shopkeeper": (0, 0, "0.5", "4-10"),
    "Banker": (0, 0, "0.5", "4-10"),
    "King_Tyron": (0, 0, "0.4", "5-12"),
    "Woman": (0, 0, "0.5", "4-10"),          # the ferrywoman, at the end of the pier
    "Beggar": (0, 0, "0.4", "5-12"),
    # tradesfolk and quest givers: a step or two around their spot
    "Baker": (1, 0, "0.5", "3-8"),
    "Blacksmith": (1, 0, "0.5", "3-8"),
    "Herbalist": (1, 0, "0.5", "3-8"),
    "Quartermaster": (1, 0, "0.5", "3-8"),
    "Wizard": (1, 0, "0.4", "5-12"),
    "Dwarf": (1, 0, "0.5", "3-8"),
    "Miner": (1, 0, "0.5", "3-8"),
    "Fisherman": (1, 0, "0.5", "3-8"),
    "Farmer": (2, 0, "0.5", "3-8"),
    "Milkmaid": (2, 0, "0.5", "3-8"),
    # townsfolk and pets
    "Villager": (3, 0, "0.5", "2-6"),
    "Man": (3, 0, "0.5", "2-6"),
    "Guard": (2, 0, "0.6", "2-5"),
    "Dog": (4, 0, "0.6", "1-4"),
    "Tallulah": (3, 0, "0.5", "2-6"),
    # farm animals: potter about, long pauses (they only chase if attacked, and not far)
    "Chicken": (3, 1, "0.6", "3-8"),
    "Cow": (2, 1, "0.4", "6-15"),
    "Sheep": (3, 1, "0.5", "4-12"),
    # vermin dart about: short pauses, fast walk
    "Rat": (3, 3, "0.8", "0.5-2"),
    "Bat": (4, 3, "0.9", "0.3-1.5"),
    # monsters
    "Goblin": (3, 4, "0.6", "1-4"),
    "Hobgoblin": (3, 4, "0.5", "2-5"),
    "Wolf": (5, 6, "0.6", "1-4"),           # roam wide, chase far (maps pin them to their woods with Chase=)
    "Giant_Spider": (2, 4, "0.5", "3-8"),   # lurk by their webs
    "Skeleton": (2, 3, "0.4", "2-5"),       # slow and steady
    "Cave_Troll": (2, 2, "0.4", "4-10"),    # guards its lair
}

# ----- per-NPC Options on the map lines (dev\Data Formats.md): map -> {(name, tile x, tile y): "Key=Value ..."}
# Tile x,y is the NPC's spawn tile (1-based). Zones contain the spawn tile, Chase rectangles contain the Zone, and
# patrol waypoints are walkable tiles reachable from each other (validate.py checks all of it).
CAMP_CHASE = "Chase=2,7,23,17"        # the goblin camp below the ridge: they give up once you're through the gap
NPC_OPTIONS = {
    # Ashford: shopkeepers and the banker stay put, the guard walks the high street, villagers wander
    "2,3,0": {
        ("Baker", 5, 9): "Zone=5,9,7,10 Pause=4-10",
        ("Shopkeeper", 19, 9): "Stand=1",
        ("Banker", 6, 16): "Stand=1",
        ("Blacksmith", 18, 16): "Zone=18,15,20,16 Pause=3-8",
        ("Beggar", 10, 13): "Stand=1",
        ("Guard", 13, 13): "Patrol=4,12/22,12/13,12/13,20 PatrolMode=PingPong Pause=2-5",
        ("Villager", 7, 13): "Zone=2,12,12,13 Pause=2-6",
        ("Villager", 21, 20): "Zone=14,19,24,21 Pause=2-6",
        ("Dog", 17, 13): "Zone=10,12,24,13 Pause=1-3",
    },
    # Tyron's Keep: the gate guard walks round the outside of the walls, the other paces the courtyard
    "2,4,0": {
        ("King_Tyron", 15, 7): "Stand=1",
        ("Guard", 8, 10): "Patrol=8,10/8,4/22,4/22,18/8,18 Pause=2-4",
        ("Guard", 14, 11): "Patrol=11,11/19,11 PatrolMode=PingPong Pause=3-6",
        ("Quartermaster", 10, 13): "Zone=10,12,11,13 Pause=4-10",
    },
    # Whispering Woods: the mine guard paces by his gate; the wolves keep to the southern woods, off the road
    "1,4,0": {
        ("Guard", 8, 11): "Patrol=5,11/11,11 PatrolMode=PingPong Pause=3-6",
        ("Wolf", 9, 15): "Zone=5,13,13,18 Chase=3,12,16,18",
        ("Wolf", 15, 17): "Zone=10,15,18,18 Chase=7,12,20,18",
        ("Wolf", 20, 14): "Zone=16,12,22,15 Chase=13,12,23,17",
    },
    # Farmlands: hens by the farmhouse, cows by the river, sheep in the meadows, the farmer by his fields
    "3,3,0": {
        ("Farmer", 12, 15): "Zone=12,14,13,16 Pause=3-8",
        ("Herbalist", 22, 16): "Zone=22,15,23,16 Pause=4-10",
        ("Chicken", 10, 9): "Zone=9,8,15,10",
        ("Chicken", 13, 9): "Zone=9,8,15,10",
        ("Chicken", 11, 10): "Zone=9,8,15,10",
        ("Cow", 14, 15): "Zone=13,14,15,18",
        ("Cow", 14, 18): "Zone=13,14,15,18",
        ("Sheep", 9, 13): "Zone=3,13,11,15",
        ("Sheep", 6, 17): "Zone=2,17,11,21",
        ("Villager", 20, 12): "Zone=19,7,23,12",
    },
    # Goblin camp: everyone stays in the camp, and nobody follows you north of the ridge
    "3,4,0": {
        ("Goblin", 6, 9): "Zone=4,7,11,12 " + CAMP_CHASE,
        ("Goblin", 9, 12): "Zone=5,10,13,14 " + CAMP_CHASE,
        ("Goblin", 17, 8): "Zone=14,7,21,10 " + CAMP_CHASE,
        ("Goblin", 19, 8): "Zone=15,7,22,11 " + CAMP_CHASE,
        ("Hobgoblin", 12, 10): "Zone=9,8,15,12 " + CAMP_CHASE,
        ("Hobgoblin", 19, 11): "Zone=16,9,22,13 " + CAMP_CHASE,
        ("Hobgoblin", 14, 14): "Zone=10,12,19,15 " + CAMP_CHASE,
        ("Wolf", 6, 17): "Zone=4,15,12,19 Chase=3,14,14,20",
    },
    # Northgate
    "1,3,0": {
        ("Woman", 15, 4): "Stand=1",
        ("Fisherman", 5, 14): "Zone=4,14,6,15 Pause=4-10",
        ("Villager", 16, 13): "Zone=14,10,22,15",
        ("Dog", 9, 12): "Zone=4,9,12,13",
        ("Man", 17, 9): "Zone=14,7,24,9",
    },
    "2,4,1": {("Wizard", 16, 12): "Zone=16,12,19,13 Pause=5-12"},
    # the Isle (lines added to the original maps)
    "1,1,0": {("Villager", 11, 10): "Zone=8,8,15,13", ("Dog", 14, 12): "Zone=10,9,18,15"},
    "2,1,0": {("Villager", 8, 13): "Zone=5,11,12,16"},
    "3,1,0": {("Villager", 12, 8): "Zone=9,5,15,10",
              ("Sheep", 16, 12): "Zone=13,11,20,16", ("Sheep", 17, 14): "Zone=13,11,20,16"},
    "2,0,0": {("Milkmaid", 9, 9): "Zone=7,8,12,11 Pause=3-8",
              ("Cow", 6, 9): "Zone=3,8,9,13", ("Cow", 8, 12): "Zone=3,8,9,13",
              ("Sheep", 13, 14): "Zone=10,11,17,17", ("Sheep", 16, 12): "Zone=10,11,17,17",
              ("Sheep", 11, 16): "Zone=10,11,17,17"},
    "1,0,0": {("Chicken", 19, 14): "Zone=17,12,22,17", ("Chicken", 21, 15): "Zone=17,12,22,17"},
    "0,0,0": {("Wolf", 20, 17): "Zone=15,13,24,20 Chase=12,10,25,21"},
    "3,0,0": {("Wolf", 5, 10): "Zone=2,7,8,13 Chase=1,4,9,16", ("Wolf", 3, 16): "Zone=1,13,7,19 Chase=1,10,9,21"},
    "2,2,0": {("Goblin", 14, 9): "Zone=10,6,18,11 Chase=6,3,22,13"},
    # caves: everything keeps to its own cavern
    "1,1,-1": {
        ("Goblin", 19, 6): "Zone=19,4,21,6 Chase=17,4,22,10",      # the goblin in the beggar's cellar
        ("Rat", 9, 9): "Zone=7,8,12,11",
        ("Rat", 8, 14): "Zone=4,12,11,17",
        ("Rat", 17, 15): "Zone=14,13,21,17",
        ("Bat", 13, 16): "Zone=9,14,18,17",
    },
    "2,1,-1": {
        ("Bat", 10, 9): "Zone=5,7,14,12",
        ("Bat", 19, 7): "Zone=18,6,23,11",
        ("Giant_Spider", 13, 14): "Zone=9,12,16,16",
        ("Giant_Spider", 21, 13): "Zone=18,11,22,15",
        ("Rat", 5, 12): "Zone=2,11,8,14",
    },
    "1,4,-1": {
        ("Miner", 10, 6): "Zone=8,5,12,6 Pause=3-8",
        ("Hobgoblin", 21, 13): "Zone=19,10,23,14 Chase=17,8,25,17",
        ("Rat", 9, 15): "Zone=4,14,12,17",
        ("Rat", 16, 17): "Zone=12,15,19,18",
        ("Bat", 5, 13): "Zone=4,11,8,16",
    },
    "2,4,-1": {
        # a hobgoblin patrols the rail tunnel between the old mine and the depths
        ("Hobgoblin", 10, 11): "Patrol=2,10/16,11 PatrolMode=PingPong Pause=1-3 Chase=1,8,20,13",
        ("Hobgoblin", 16, 12): "Zone=13,11,21,15",
        ("Hobgoblin", 18, 8): "Zone=14,5,22,9",
        ("Giant_Spider", 15, 16): "Zone=12,15,20,17",
        ("Giant_Spider", 9, 18): "Zone=5,16,13,18",
        ("Giant_Spider", 21, 17): "Zone=18,15,22,17",
        ("Bat", 6, 10): "Zone=2,9,9,12",
    },
    "2,4,-2": {
        ("Hobgoblin", 10, 7): "Zone=7,5,14,9",
        ("Hobgoblin", 17, 9): "Zone=14,6,22,10",
        ("Hobgoblin", 9, 14): "Zone=5,12,12,16",
        ("Hobgoblin", 15, 13): "Zone=12,11,19,15",
        ("Hobgoblin", 20, 11): "Zone=17,9,23,13",
        ("Skeleton", 6, 9): "Zone=4,8,9,12",
    },
    # the Deep Hollow: Brokk stays by his forge; the crystal-cavern skeletons never follow you into his hall
    "2,4,-3": {
        ("Dwarf", 12, 5): "Zone=11,5,14,6 Pause=3-8",
        ("Skeleton", 22, 5): "Zone=20,4,23,7 Chase=19,4,24,13",
        ("Skeleton", 21, 9): "Zone=19,8,23,11 Chase=19,4,24,13",
        ("Skeleton", 4, 10): "Zone=3,8,7,12 Chase=2,8,9,14",
        ("Skeleton", 16, 13): "Patrol=12,12/19,13/14,14 Pause=2-5 Chase=9,9,22,17",
        ("Skeleton", 6, 16): "Zone=5,15,8,18",
        ("Cave_Troll", 21, 16): "Zone=19,14,23,17 Chase=17,12,24,18",
        ("Bat", 11, 12): "Zone=8,11,16,13",
    },
}
NPC_OPTION_PROBLEMS = []


def npc_tile(e):
    """Spawn tile (1-based) of an NPC entity tuple: the tile under its feet (32x32 sprites)."""
    return int(e[2] + 16) // 32 + 1, int(e[3] + 31) // 32 + 1


def with_options(map_name, entities):
    """The entity list with each NPC's Options (from NPC_OPTIONS) as a 5th field; records the NPC_OPTIONS
    entries that match no NPC (or more than one)."""
    want = NPC_OPTIONS.get(map_name, {})
    used = {}
    out = []
    for e in entities:
        if e[0] in ("GoodNPC", "BadNPC"):
            tx, ty = npc_tile(e)
            key = (e[1], tx, ty)
            e = tuple(e[:4])
            if key in want:
                used[key] = used.get(key, 0) + 1
                e = e + (want[key],)
        out.append(e)
    for key in want:
        if used.get(key) != 1:
            NPC_OPTION_PROBLEMS.append("%s: NPC_OPTIONS %s at %d,%d matches %d NPC(s)" % ((map_name,) + key + (used.get(key, 0),)))
    return out


SKILLS_ADD = ["Potion_Making", "Crafting", "Magic"]

# ----- item racks
CRAFT = {
    "CRAFT-Cooking": ("Cooking", [
        "Meat_Sandwich,Cooked_Meat 1 Bread 1,0.05",
        "Flour,Wheat 2,0.05",
        "Bread,Flour 1,0.1",
        "Berry_Pie,Flour 1 Berries 3,0.25,5",
        "Meat_Pie,Flour 1 Cooked_Meat 1,0.3,8",
        "Fish_Pie,Flour 1 Cooked_Trout 1,0.4,12",
        "Stew,Cooked_Meat 1 Cabbage 1 Bucket_of_Water 1,0.45,15",
    ]),
    # Furnace: ore -> bars (Smithing). Listed by level.
    "CRAFT-Smelting": ("Smithing", [
        "Copper_Bar,Copper_Ore 1,0.1",
        "Bronze_Bar,Copper_Ore 1 Tin_Ore 1,0.15",
        "Iron_Bar,Iron_Ore 2,0.2",
        "Steel_Bar,Iron_Ore 1 Coal 2,0.4,8",
        "Silver_Bar,Silver_Ore 1,0.35,10",
        "Gold_Bar,Gold_Ore 1,0.5,12",
        "Mithril_Bar,Mithril_Ore 1 Coal 4,0.9,22",
    ]),
    # Anvil: bars -> tools, weapons and armour (Smithing). Listed by level.
    "CRAFT-Smithing": ("Smithing", [
        "Copper_Dagger,Copper_Bar 1,0.15",
        "Bronze_Pickaxe,Bronze_Bar 1 Logs 1,0.15",
        "Bronze_Axe,Bronze_Bar 1 Logs 1,0.15",
        "Bronze_Sword,Bronze_Bar 1 Logs 1,0.2,2",
        "Bronze_Helm,Bronze_Bar 1,0.2,2",
        "Bronze_Shield,Bronze_Bar 2,0.3,3",
        "Bronze_Platelegs,Bronze_Bar 2,0.35,4",
        "Axe,Iron_Bar 1 Logs 1,0.25",
        "Pickaxe,Iron_Bar 2 Logs 1,0.3",
        "Bronze_Platebody,Bronze_Bar 3,0.5,5",
        "Shears,Iron_Bar 1,0.2,5",
        "Iron_Sword,Iron_Bar 2 Logs 1,0.5,5",
        "Iron_Helm,Iron_Bar 2,0.4,6",
        "Iron_Boots,Iron_Bar 1,0.3,6",
        "Iron_Gauntlets,Iron_Bar 1,0.3,7",
        "Iron_Shield,Iron_Bar 3,0.6,7",
        "Iron_Platelegs,Iron_Bar 3,0.7,9",
        "Steel_Axe,Steel_Bar 1 Oak_Logs 1,0.6,10",
        "Iron_Platebody,Iron_Bar 5,1,11",
        "Steel_Sword,Steel_Bar 2 Oak_Logs 1,1,12",
        "Steel_Pickaxe,Steel_Bar 2 Oak_Logs 1,0.8,12",
        "Steel_Helm,Steel_Bar 2,0.9,13",
        "Steel_Boots,Steel_Bar 1,0.7,14",
        "Steel_Gauntlets,Steel_Bar 1,0.7,14",
        "Steel_Shield,Steel_Bar 3,1.2,15",
        "Steel_Platelegs,Steel_Bar 3,1.3,16",
        "Steel_Platebody,Steel_Bar 5,1.8,18",
        "Mithril_Sword,Mithril_Bar 2 Willow_Logs 1,2,22",
        "Mithril_Helm,Mithril_Bar 2,1.8,23",
        "Mithril_Boots,Mithril_Bar 1,1.5,24",
        "Mithril_Gauntlets,Mithril_Bar 1,1.5,24",
        "Mithril_Axe,Mithril_Bar 1 Willow_Logs 1,1.4,25",
        "Mithril_Pickaxe,Mithril_Bar 2 Willow_Logs 1,1.6,26",
        "Mithril_Shield,Mithril_Bar 3,2.4,27",
        "Mithril_Platelegs,Mithril_Bar 3,2.6,28",
        "Mithril_Platebody,Mithril_Bar 5,3.5,30",
    ]),
    "CRAFT-Potion_Making": ("Potion_Making", [
        "Basic_Potion,Herb 3 Empty_Vial 1,0.3",
        "Super_Potion,Herb 2 Cave_Mushroom 2 Empty_Vial 1,0.6,5",
        "Strength_Potion,Cave_Mushroom 3 Berries 2 Empty_Vial 1,0.8,10",
        "Defence_Potion,Herb 2 Iron_Ore 1 Empty_Vial 1,0.9,15",
        "Combat_Potion,Herb 2 Spider_Silk 1 Cave_Mushroom 1 Empty_Vial 1,1.2,22",
        "Owl_Potion,Herb 2 Egg 1 Empty_Vial 1,0.7,8",
        "Magic_Potion,Cave_Mushroom 2 Sapphire 1 Empty_Vial 1,1.5,28",
        "Mega_Potion,Herb 3 Cave_Mushroom 2 Emerald 1 Empty_Vial 1,2,35",
    ]),
    "CRAFT-Crafting": ("Crafting", [
        "Leather,Cowhide 1,0.15",
        "Ball_of_Wool,Wool 2,0.1",
        "Fishing_Rod,Logs 1 Ball_of_Wool 1,0.2,1",       # wool spun into line
        "Arrows,Logs 1 Bronze_Bar 1,0.2,3,25",            # a 5th field: how many one making gives
        "Wooden_Shield,Logs 3,0.2,2",
        "Leather_Gloves,Leather 1,0.2,2",
        "Leather_Cap,Leather 1,0.25,3",
        "Leather_Boots,Leather 2,0.3,4",
        "Leather_Body,Leather 3,0.5,5",
        "Leather_Legs,Leather 2,0.4,6",
        "Silver_Ring,Silver_Bar 1,0.35,6",
        "Gold_Ring,Gold_Bar 1,0.5,8",
        "Silver_Tiara,Silver_Bar 2,0.6,9",
        "Oak_Staff,Oak_Logs 2,0.5,10",
        "Oak_Shield,Oak_Logs 3,0.6,12",
        "Oak_Bow,Oak_Logs 2 Ball_of_Wool 1,0.5,10",
        "Yew_Bow,Yew_Logs 2 Ball_of_Wool 1,1.5,28",
        "Willow_Staff,Willow_Logs 2 Sapphire 1,1,20",
        "Yew_Staff,Yew_Logs 2 Ruby 1,2,30",
        "Sapphire_Ring,Gold_Bar 1 Sapphire 1,0.8,12",
        "Ruby_Ring,Gold_Bar 1 Ruby 1,0.9,14",
        "Emerald_Ring,Gold_Bar 1 Emerald 1,1,16",
    ]),
}
# ----- Spells (data\\Spells.ini, see dev\\Data Formats.md). A scroll item has Spell=<section> and Use.Words=Cast;
# reading it casts the spell and uses the scroll up. Damage/Heal get + Magic level / 4 (/ 3 for healing).
SPELLS = [
    ("Fire_Bolt", dict(Cost="3", Cooldown="0", Scroll="Fire_Bolt_Scroll", Effect="Bolt", Level="1", Damage="2-5", Range="256",
                       Missile="Fire_Bolt_Missile", Impact="Fire_Burst", Sound="SpellFire", XP="0.3",
                       Info="hurls a ball of fire at one foe")),
    ("Healing", dict(Cost="5", Cooldown="6", Scroll="Healing_Scroll", Effect="Heal", Level="2", Heal="8-14", Impact="Heal_Glow",
                     Sound="SpellHeal", XP="0.3", Info="heals your wounds")),
    ("Teleport_Home", dict(Cost="10", Cooldown="60", Scroll="Teleport_Scroll", Effect="Teleport", Level="5", Map="", X="", Y="",
                           Impact="Teleport_Glow", Sound="Teleporter", XP="0.4",
                           Info="takes you home to the Isle, wherever you are")),
    ("Ice_Bolt", dict(Cost="6", Cooldown="4", Scroll="Ice_Bolt_Scroll", Effect="Bolt", Level="10", Damage="2-6", Range="256", Slow="50,8",
                      Missile="Ice_Bolt_Missile", Impact="Ice_Burst", Sound="SpellIce", XP="0.4",
                      Info="a shard of ice that hurts a foe and slows it to half speed for 8 seconds")),
    ("Stone_Skin", dict(Cost="10", Cooldown="60", Scroll="Stone_Skin_Scroll", Effect="Shield", Level="14", Defence="5", Duration="60",
                        Impact="Stone_Glow", Sound="SpellShield", XP="0.5",
                        Info="hardens your skin: +5 Defence for a minute")),
    ("Farsight", dict(Cost="6", Cooldown="30", Scroll="Farsight_Scroll", Effect="Boost", Level="8", Sight="150", Duration="90",
                      Impact="Teleport_Glow", Sound="SpellShield", XP="0.4",
                      Info="lets you see much further through the fog of war for a minute and a half")),
    ("Lightning", dict(Cost="12", Cooldown="10", Scroll="Lightning_Scroll", Effect="Bolt", Level="20", Damage="6-14", Range="320",
                       Missile="Lightning_Missile", Impact="Spark", Sound="SpellLightning", XP="0.8",
                       Info="a bolt of lightning at one foe")),
    ("Defence_Potion", dict(Scroll="Defence_Potion", Kind="Potion", Effect="Boost", Skill="Potion_Making", Level="1",
                            Defence="4", Duration="120", Leaves="Empty_Vial", Impact="Stone_Glow", Sound="SpellShield",
                            XP="0", Info="+4 Defence for two minutes")),
    ("Combat_Potion", dict(Scroll="Combat_Potion", Kind="Potion", Effect="Boost", Skill="Potion_Making", Level="1",
                           Attack="3", Defence="3", Duration="120", Leaves="Empty_Vial", Impact="Stone_Glow",
                           Sound="SpellShield", XP="0", Info="+3 Attack and +3 Defence for two minutes")),
    ("Magic_Potion", dict(Scroll="Magic_Potion", Kind="Potion", Effect="Boost", Skill="Potion_Making", Level="1",
                          Magic="5", Mana="30", Duration="120", Leaves="Empty_Vial", Impact="Teleport_Glow", Sound="SpellShield",
                          XP="0", Info="30 mana back, and +5 spell damage for two minutes")),
    ("Owl_Potion", dict(Scroll="Owl_Potion", Kind="Potion", Effect="Boost", Skill="Potion_Making", Level="1",
                        Sight="120", Duration="180", Leaves="Empty_Vial", Impact="Teleport_Glow", Sound="SpellShield",
                        XP="0", Info="see further through the fog for three minutes")),
    ("Mega_Potion", dict(Scroll="Mega_Potion", Kind="Potion", Effect="Heal", Skill="Potion_Making", Level="1",
                         Heal="45-55", Leaves="Empty_Vial", Impact="Heal_Glow", Sound="SpellHeal", XP="0",
                         Info="heals 45-55 hitpoints")),
    ("Fire_Storm", dict(Cost="25", Cooldown="30", Scroll="Fire_Storm_Scroll", Effect="Area", Level="30", Damage="5-12", Radius="128",
                        Impact="Fire_Burst", Sound="SpellFire", XP="1.2",
                        Info="fire rains on every foe within four tiles of you")),
]
SCROLL_VALUES = {"Fire_Bolt_Scroll": 15, "Healing_Scroll": 15, "Teleport_Scroll": 20, "Ice_Bolt_Scroll": 25,
                 "Stone_Skin_Scroll": 30, "Farsight_Scroll": 25, "Lightning_Scroll": 60, "Fire_Storm_Scroll": 120}
ENTITIES["Blank_Scroll"] = item(4, "A blank sheet of parchment. The wizard can teach you to write spells on it.", 20)
for _spell, _d in SPELLS:
    if _d.get("Kind") == "Potion":
        continue                                  # potions are items of their own (above)
    _dmg = (" (%s damage)" % _d["Damage"]) if "Damage" in _d else (" (%s hitpoints)" % _d["Heal"]) if "Heal" in _d else ""
    ENTITIES[_d["Scroll"]] = item(SCROLL_VALUES[_d["Scroll"]],
                                  "A scroll of %s: %s%s. Magic %s. Right-click it and Cast, or use it on a monster."
                                  % (_spell.replace("_", " "), _d["Info"], _dmg, _d["Level"]), 10, use="Cast") + \
        [("Spell", _spell)]
CRAFT["CRAFT-Scrolls"] = ("Magic", [
    "Fire_Bolt_Scroll,Blank_Scroll 1 Coal 1,0.2",
    "Healing_Scroll,Blank_Scroll 1 Herb 2,0.2",
    "Teleport_Scroll,Blank_Scroll 1 Spider_Silk 1,0.3,3",
    "Ice_Bolt_Scroll,Blank_Scroll 1 Bucket_of_Water 1,0.35,5",
    "Farsight_Scroll,Blank_Scroll 1 Sapphire 1,0.45,6",
    "Stone_Skin_Scroll,Blank_Scroll 1 Iron_Ore 2,0.4,8",
    "Lightning_Scroll,Blank_Scroll 1 Silver_Bar 1,0.7,15",
    "Fire_Storm_Scroll,Blank_Scroll 1 Coal 3 Ruby 1,1,20",
])
NEW_SHOPS = {
    "SHOP-Wizard": ("1.2", "0.6", ["Blank_Scroll,30", "Fire_Bolt_Scroll,10", "Healing_Scroll,10", "Teleport_Scroll,5",
                                   "Ice_Bolt_Scroll,5", "Stone_Skin_Scroll,3", "Farsight_Scroll,3", "Lightning_Scroll,2",
                                   "Oak_Staff,1", "Magic_Potion,0", "Owl_Potion,0", "Willow_Staff,0", "Yew_Staff,0"]),
    "SHOP-Dairy": ("1.2", "0.7", ["Bucket_of_Milk,5", "Wool,10", "Egg,10", "Bucket,5", "Shears,3", "Cowhide,0",
                                  "Leather,4", "Leather_Gloves,2"]),
    "SHOP-Fishing": ("1.2", "0.8", ["Fishing_Rod,5", "Bait,100", "Raw_Fish,10", "Raw_Trout,4", "Cooked_Fish,5",
                                    "Raw_Cave_Eel,0", "Cooked_Trout,0", "Cooked_Cave_Eel,0", "Raw_Salmon,0",
                                    "Cooked_Salmon,2", "Raw_Swordfish,0", "Cooked_Swordfish,0"]),
    "SHOP-Keep": ("1.3", "0.7", ["Oak_Bow,2", "Arrows,300", "Iron_Sword,3", "Iron_Shield,3", "Steel_Sword,1", "Leather_Cap,3", "Leather_Body,3",
                                 "Leather_Legs,2", "Leather_Gloves,3", "Leather_Boots,2", "Iron_Helm,2",
                                 "Iron_Platelegs,1", "Iron_Platebody,1", "Basic_Potion,5", "Bread,10"]),
    "SHOP-Dwarf": ("1.3", "0.9", ["Pickaxe,3", "Coal,20", "Steel_Bar,5", "Gold_Bar,2", "Super_Potion,3",
                                  "Sapphire,0", "Emerald,0", "Ruby,0", "Gold_Ore,0", "Gold_Ring,0",
                                  "Sapphire_Ring,0", "Emerald_Ring,0", "Ruby_Ring,0", "Steel_Helm,1", "Steel_Shield,1",
                                  "Steel_Platelegs,1", "Steel_Platebody,0", "Silver_Ore,0", "Silver_Bar,2",
                                  "Mithril_Ore,0", "Mithril_Bar,0", "Steel_Pickaxe,1", "Steel_Axe,1", "Silver_Ring,0",
                                  "Silver_Tiara,0", "Steel_Boots,1", "Steel_Gauntlets,1", "Mithril_Helm,0",
                                  "Mithril_Sword,0"]),
}
SHOP_ADD = {      # appended to existing shops when missing
    # (SHOP-General went with the original game's test man, who opened it: the general store is SHOP-Ashford)
    "SHOP-Smith": ["Iron_Sword,2", "Iron_Shield,2", "Shears,3", "Copper_Bar,5", "Steel_Bar,0", "Coal,0", "Copper_Ore,0",
                   "Copper_Dagger,3", "Iron_Helm,2", "Iron_Platelegs,1", "Iron_Platebody,0", "Tin_Ore,0",
                   "Bronze_Bar,5", "Bronze_Pickaxe,2", "Bronze_Axe,2", "Bronze_Sword,2", "Bronze_Helm,2",
                   "Bronze_Shield,1", "Iron_Boots,1", "Iron_Gauntlets,1"],
    "SHOP-Herbalist": ["Super_Potion,2", "Cave_Mushroom,0", "Spider_Silk,0", "Berries,0", "Defence_Potion,2", "Antidote,3"],
    "SHOP-Farm": ["Wheat,20", "Flour,10", "Wool,0", "Bucket_of_Milk,0", "Cowhide,0"],
    "SHOP-Baker": ["Berry_Pie,3", "Fish_Pie,2", "Flour,5", "Meat_Pie,3", "Stew,0"],
}

# ----- Gathering.ini (read by the in-game Help screen). Keys: Gives, Source, Verb, Tool, Skill, Level, XP, Where
GATHERING = [
    ("Logs from trees", dict(Gives="Logs", Source="Tree001 Tree002", Verb="Chop", Tool="Bronze_Axe/Axe/Steel_Axe/Mithril_Axe", Skill="Woodcutting",
                             Level="1", XP="0.1", Where="Trees all over the Isle and the Southlands")),
    ("Oak logs", dict(Gives="Oak_Logs", Source="Oak_Tree001", Verb="Chop", Tool="Bronze_Axe/Axe/Steel_Axe/Mithril_Axe", Skill="Woodcutting",
                      Level="10", XP="0.25", Where="Oaks in the Isle's woods, around Northgate and Ashford and in the Whispering Woods")),
    ("Willow logs", dict(Gives="Willow_Logs", Source="Willow_Tree001", Verb="Chop", Tool="Bronze_Axe/Axe/Steel_Axe/Mithril_Axe", Skill="Woodcutting",
                         Level="20", XP="0.4", Where="Willows grow by the water: the Isle's woods, the shores of the Southlands")),
    ("Yew logs", dict(Gives="Yew_Logs", Source="Yew_Tree001", Verb="Chop", Tool="Bronze_Axe/Axe/Steel_Axe/Mithril_Axe", Skill="Woodcutting",
                      Level="35", XP="0.9", Where="A few ancient yews deep in the Whispering Woods and the eastern woods")),
    ("Fish from the sea", dict(Gives="Raw_Fish", Source="Water001 Water002 Water003 Water004 Water005 Water006 Water007 Water008 Water009",
                               Verb="Use", Tool="Fishing_Rod", Skill="Fishing", Level="1", XP="0.1",
                               Where="Any shore, with Bait in your pack: stand at the water's edge and use the rod on the water")),
    ("Trout", dict(Gives="Raw_Trout", Source="Water001 Water002 Water003 Water004 Water005 Water006 Water007 Water008 Water009",
                   Verb="Use", Tool="Fishing_Rod", Skill="Fishing", Level="10", XP="0.2",
                   Where="Any shore, with Bait in your pack (each trout uses one)")),
    ("Salmon", dict(Gives="Raw_Salmon", Source="Water001 Water002 Water003 Water004 Water005 Water006 Water007 Water008 Water009",
                    Verb="Use", Tool="Fishing_Rod", Skill="Fishing", Level="20", XP="0.35",
                    Where="Any shore, with Bait in your pack (each salmon uses one)")),
    ("Swordfish", dict(Gives="Raw_Swordfish", Source="Water001 Water002 Water003 Water004 Water005 Water006 Water007 Water008 Water009",
                       Verb="Use", Tool="Fishing_Rod", Skill="Fishing", Level="35", XP="0.6",
                       Where="Any shore, with Bait in your pack (each swordfish uses one)")),
    ("Cave eels", dict(Gives="Raw_Cave_Eel", Source="Cave_Pool001", Verb="Use", Tool="Fishing_Rod", Skill="Fishing",
                       Level="15", XP="0.3", Where="The black pools in the grotto under the Isle and in the Deep Hollow, with Bait")),
    ("Water", dict(Gives="Bucket_of_Water", Source="Water001 Water002 Water003 Water004 Water005 Water006 Water007 Water008 Water009 Cave_Pool001",
                   Verb="Use", Tool="Bucket", Skill="", Level="0", XP="0", Where="Any shore or cave pool")),
    ("Iron ore", dict(Gives="Iron_Ore", Source="Ore_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining", Level="1",
                      XP="0.1", Where="The old iron mine, the mine depths, the grotto under the Isle and the warren")),
    ("Copper ore", dict(Gives="Copper_Ore", Source="Copper_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining",
                        Level="1", XP="0.08", Where="The cellar grotto under the Isle and the old iron mine")),
    ("Tin ore", dict(Gives="Tin_Ore", Source="Tin_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining",
                     Level="1", XP="0.08", Where="The cellar grotto under the Isle and the old iron mine. Smelt it with copper ore for bronze")),
    ("Coal", dict(Gives="Coal", Source="Coal_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining", Level="5",
                  XP="0.15", Where="The cellar grotto under the Isle, the mine depths and the guild's deep seam")),
    ("Silver ore", dict(Gives="Silver_Ore", Source="Silver_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining",
                        Level="12", XP="0.25", Where="The mine depths, the guild's deep seam and the hobgoblin warren")),
    ("Gold ore", dict(Gives="Gold_Ore", Source="Gold_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining", Level="15",
                      XP="0.3", Where="The crystal cavern in the Deep Hollow below the hobgoblin warren, and the guild's deep seam in the mine depths (Mining 10 to enter)")),
    ("Gems", dict(Gives="Sapphire Emerald Ruby", Source="Gem_Rock001", Verb="Mine", Tool="Bronze_Pickaxe/Pickaxe/Steel_Pickaxe/Mithril_Pickaxe", Skill="Mining",
                  Level="20", XP="0.5", Where="The crystal cavern in the Deep Hollow, and Brokk's vault")),
    ("Mithril ore", dict(Gives="Mithril_Ore", Source="Mithril_Rock001", Verb="Mine", Tool="Steel_Pickaxe/Mithril_Pickaxe",
                         Skill="Mining", Level="25", XP="0.7",
                         Where="The cave troll's lair in the Deep Hollow and Brokk's vault. Only a steel or mithril pickaxe will break it")),
    ("Cave mushrooms", dict(Gives="Cave_Mushroom", Source="Mushroom_Patch001", Verb="Pick", Tool="", Skill="Potion_Making",
                            Level="1", XP="0.1", Where="Damp corners of every cave and mine")),
    ("Herbs", dict(Gives="Herb", Source="Herb_Patch001", Verb="Pick", Tool="", Skill="Potion_Making", Level="1", XP="0.1",
                   Where="Herb patches in the grass on the Isle and in the Southlands")),
    ("Wild herbs", dict(Gives="Herb", Source="Herb", Verb="Pickup", Tool="", Skill="", Level="0", XP="0",
                        Where="Loose herbs lying about in the Southlands (they grow back after a while)")),
    ("Berries", dict(Gives="Berries", Source="Berry_Bush001", Verb="Pick", Tool="", Skill="Potion_Making", Level="1",
                     XP="0.05", Where="Berry bushes on the Isle, around Northgate and in the Whispering Woods")),
    ("Wheat", dict(Gives="Wheat", Source="Ripe_Wheat001 Ripe_Wheat002 Ripe_Wheat003", Verb="Harvest", Tool="", Skill="", Level="0", XP="0",
                   Where="The wheat field on the Ashford farmlands")),
    ("Cabbages", dict(Gives="Cabbage", Source="Cabbage", Verb="Pickup", Tool="", Skill="", Level="0", XP="0",
                      Where="The cabbage rows on the Ashford farmlands")),
    ("Eggs", dict(Gives="Egg", Source="Nest001", Verb="Collect", Tool="", Skill="", Level="0", XP="0",
                  Where="Hens' nests on the Isle's farm and by the Ashford farmhouse")),
    ("Milk", dict(Gives="Bucket_of_Milk", Source="Cow", Verb="Use", Tool="Bucket", Skill="", Level="0", XP="0",
                  Where="The cows on the Isle's farm and the Ashford farmlands")),
    ("Wool", dict(Gives="Wool", Source="Sheep", Verb="Use", Tool="Shears", Skill="Crafting", Level="1", XP="0.05",
                  Where="The sheep on the Isle and the Ashford farmlands")),
]

# ----- Quests.ini (read by the in-game Help screen)
QUESTS = [
    ("Passage to the Mainland", [
        ("Giver", "Woman"), ("Attribute", "FerryQuest"),
        ("Stage0", "Speak to the ferrywoman at the end of the pier in the south of the Isle."),
        ("Stage1", "The first crossing needs a ticket. Ask the milkmaid, the ferrywoman's sister, on the farm in the north of the Isle."),
        ("Stage2", "Bring the milkmaid 3 eggs from the hens' nests on her farm."),
        ("Stage3", "Show your ferry ticket to the ferrywoman on the pier and sail to Northgate."),
        ("Done", "4")]),
    ("King's Hobgoblin Hunt", [
        ("Giver", "King_Tyron"), ("Attribute", "HobgoblinQuest"),
        ("Stage0", "Speak to King Tyron in his keep, south of Ashford."),
        ("Stage1", "Slay five hobgoblins ($HobgoblinsSlain of 5) in the old iron mine, the mine depths, the warren or the goblin camp, then return to King Tyron."),
        ("Done", "2")]),
    ("The Herbalist's Remedy", [
        ("Giver", "Herbalist"), ("Attribute", "RemedyQuest"),
        ("Stage0", "Ask the Herbalist in her cottage on the Ashford farmlands if she needs a hand."),
        ("Stage1", "Bring the Herbalist 3 Cave Mushrooms (pick them in the old iron mine) and 2 Spider Silk (dropped by the giant spiders in the mine depths)."),
        ("Done", "2")]),
    ("The Dwarf's Grudge", [
        ("Giver", "Dwarf"), ("Attribute", "DwarfQuest"),
        ("Stage0", "Find Brokk the dwarf in the Deep Hollow (through the hatch in the hobgoblin warren) and ask if he needs help."),
        ("Stage1", "Smash four skeletons ($SkeletonsSlain of 4) and slay the cave troll ($TrollSlain of 1) in the Deep Hollow, then return to Brokk."),
        ("Done", "2")]),
    ("The Beggar's Lost Key", [
        ("Giver", "Beggar"), ("Attribute", "BeggarQuest"),
        ("Stage0", "Give the beggar in Ashford a coin and listen to his story."),
        ("Stage1", "Find the beggar's lost key (the hobgoblins took it down to their warren, below the old iron mine) and unlock his house on the Isle with it."),
        ("Done", "2")]),
]


# =========================================================================================== data writers
def avg_colour(tile):
    w, h, rows = read_bmp(p("sprites", "Tiles", tile + ".png"))
    px = [c for r in rows[h // 2:] for c in r]
    return "%d %d %d" % tuple(sum(c[i] for c in px) // len(px) for i in range(3))


# ----- Walking speed on a tile (Tiles.ini Walk.Speed: x the normal speed; 1 = normal, the key is left out). Roads and
# floors are quicker, sand, rubble, crops and undergrowth slower. Set for any tile in Tiles.ini, old or new.
WALK_SPEED = {
    "Dirt001": "1.2", "Stone001": "1.15", "Stone002": "1.15", "Plank001": "1.1", "Tile001": "1.1",
    "Mine_Track001": "1.1", "Mine_Track002": "1.1",
    "Sand001": "0.8", "Tall_Grass001": "0.8", "Weed001": "0.85", "Field001": "0.85",
    "Forest001": "0.75", "Flowers001": "0.95", "Flowers002": "0.95", "Flowers003": "0.95",
    "Cave_Rubble001": "0.7", "Cave_Puddle001": "0.8", "Mushroom_Patch001": "0.85", "Mushroom_Patch002": "0.85",
    "Mushroom_Ring001": "0.85", "Herb_Patch001": "0.85", "Herb_Patch002": "0.85", "Berry_Bush001": "0.8",
    "Berry_Bush002": "0.8", "Bush001": "0.75", "Haystack001": "0.8",
}


# ----- Edge blending (Tiles.ini Blend=<priority> and Blend.Texture=<tile>): where two tiles of different terrain meet,
# the game paints the higher one's texture a few wavy pixels over the lower one's edge (sprites\Interface\Blend_*).
# The terrain of a tile is worked out from the colours round its edge, so flowers, boulders, bushes... on grass all
# count as grass. Tiles that match none (walls, cliffs, the diagonal shore pieces Water002-009) don't blend:
# region_tiles.py shore() draws those to join the bands round them.
# Each terrain its own priority, so any two that meet blend (sand over the dirt paths, grass over both...);
# build_regions.py adds snow 5, marsh 4 and ice 1
BLEND_TERRAINS = [("Grass001", 6), ("Sand001", 3), ("Dirt001", 2), ("Water001", 1)]   # (texture tile, priority)
# the cave walls: as high as the cave floor (so inside a cave they don't blend), so where a cave's rock meets grass
# (a mine's mouth) the grass laps over it in a ragged line, and the rock over a dirt path
CAVE_WALL_BLEND = 4


def blend_terrains():
    """{tile: (priority, texture tile)} for every tile sprite whose border matches a terrain."""
    import glob
    from common import read_bmp

    def border(name):
        w, h, rows = read_bmp(p("sprites", "Tiles", name + ".png"))
        img, mask = rows[h // 2:], rows[:h // 2]
        n = len(img)
        ring = [(x, y) for y in range(n) for x in range(n) if x in (0, 1, n - 2, n - 1) or y in (0, 1, n - 2, n - 1)]
        if any(sum(mask[y][x]) > 384 for x, y in ring):      # see-through edges: an overlay, not ground
            return None
        return [img[y][x] for x, y in ring]

    def mean(px):
        return tuple(sum(c[i] for c in px) / len(px) for i in range(3))

    refs = []
    for tex, pri in BLEND_TERRAINS:
        refs.append((tex, pri, mean(border(tex))))
    out = {}
    for path in sorted(glob.glob(p("sprites", "Tiles", "*.png"))):
        name = os.path.basename(path)[:-4]
        import villages
        if name in villages.WALL_DOORS or name in villages.WALL_DOORS.values() or "_Roof" in name or "_Upper" in name \
                or (name in villages.HOUSE_TILES and name != "Plank001") or name.startswith(("City_", "Door", "Fireplace")) or "_Window" in name or name in PALACE_TILES \
                or "_Thin_" in name:
            continue                                # walls, doors, windows, furniture and roofs keep their edges
        px = border(name)
        if not px:
            continue
        best = None
        for tex, pri, ref in refs:
            close = sum(1 for c in px if sum(abs(c[i] - ref[i]) for i in range(3)) < 70) / float(len(px))
            if close >= 0.9 and (best is None or close > best[0]):
                best = (close, tex, pri)
        if best:
            out[name] = (best[2], best[1])
    for k in range(1, 6):           # the cliff pieces stand on grass: blended alike, so they meet without a gap
        out["Cliff%03d" % k] = (6, "Grass001")
    for k in range(1, 4):
        out["Cave_Wall%03d" % k] = (CAVE_WALL_BLEND, "Cave_Wall001")
    return out


# Kill.Sound: sounds\Kill_<kind>.wav (made by build_sounds.py), by the words in a monster's name; Beast otherwise
KILL_SOUNDS = (("Dragon", ("Dragon",)), ("Troll", ("Troll",)), ("Undead", ("Skeleton", "Barrow_King", "Zombie", "Ghost")),
               ("Bug", ("Spider", "Scorpion", "Beetle")), ("Small", ("Rat", "Rabbit", "Bat")),
               ("Bird", ("Chicken", "Duck", "Crow")), ("Livestock", ("Cow", "Sheep", "Goat", "Pig")),
               ("Humanoid", ("Bandit", "Goblin", "Orc", "Guard", "Knight", "Man", "Hob")))


def kill_sound(name):
    for kind, words in KILL_SOUNDS:
        if any(w.lower() in name.lower() for w in words):
            return kind
    return "Beast"


def update_content_data():
    changed = []
    # Tiles.ini
    ini = Ini(p("data", "Tiles.ini"))
    from common import DECOR_MAP
    merged = {n for n, (_, d) in DECOR_MAP.items() if d != n}    # (split into decor and merged into another: gone)
    for name, (walk, show, use, exa, los, _) in TILES.items():
        if name in merged:
            continue
        for k, v in (("Walkable.Data", walk), ("Show.Name", show), ("Use.Words", use), ("Examine.Info", exa),
                     ("Line.of.Sight", los)):
            if v is not None:
                ini.set(name, k, v)
    for name, keys in TILE_EXTRA.items():
        if name in merged:
            continue
        for k, v in keys:
            ini.set(name, k, v)
    for name, speed in WALK_SPEED.items():
        if ini.section(name) is not None:
            ini.set(name, "Walk.Speed", speed)
    for name, (pri, tex) in blend_terrains().items():
        if ini.section(name) is not None:
            ini.set(name, "Blend", str(pri))
            ini.set(name, "Blend.Texture", tex)
    if ini.save(p("data", "Tiles.ini")):
        changed.append("data\\Tiles.ini")
    # Minimap colours
    path = p("dev", "Minimap Colours.txt")
    lines = [l for l in read_lines(path) if l.strip()]
    have = {l.split("\t")[0]: i for i, l in enumerate(lines)}
    from common import DECOR_MAP
    for name, t in TILES.items():
        if name in DECOR_MAP and DECOR_MAP[name][1] != name:
            continue                        # (split into decor and merged into another: there's no such tile now)
        if name not in have:
            col = t[5] or avg_colour(name)
            lines.append("%s\t%s" % (name, col))
    if write_lines(path, lines):
        changed.append("dev\\Minimap Colours.txt")
    # Entities.ini
    ini = Ini(p("data", "Entities.ini"))
    for name, keys in list(ENTITIES.items()) + list(ENTITY_KEYS.items()):
        for k, v in keys:
            ini.set(name, k, v)
    for sec, _ in ini.sections:              # every NPC: Type=NPC and an Attitude (the old GoodNPC / BadNPC types)
        typ = ini.get(sec, "Type", "") or ""
        if typ in W.NPC_KINDS:
            if not ini.get(sec, "Attitude", ""):
                ini.set(sec, "Attitude", W.NPC_KINDS[typ])
            ini.set(sec, "Type", "NPC")
    # the commented [Default] block at the top documents the NPC movement keys too
    if not any(l.startswith(";Roam.Radius=") for l in ini.header):
        at_ = next((i + 1 for i, l in enumerate(ini.header) if l.startswith(";Drops=")), len(ini.header))
        ini.header[at_:at_] = [
            ";Roam.Radius=0               ; tiles it wanders from its spawn (0 = stands still), unless the map line gives a Zone",
            ";Chase.Radius=0              ; tiles beyond its zone it follows the player",
            ";Walk.Speed=0.5              ; roaming/patrol speed as a fraction of Movement.Speed (chasing = full speed)",
            ";Pause=1-4                   ; seconds it stands still between moves (min-max)"]
    for name, (roam, chase, walk, pause) in MOVEMENT.items():
        for k, v in (("Roam.Radius", str(roam)), ("Chase.Radius", str(chase)), ("Walk.Speed", walk), ("Pause", pause)):
            ini.set(name, k, v)
    for sec in ini.sections:                               # the sound each monster makes as it dies
        if (ini.get(sec[0], "Type", "") or "").lower() == "npc" and (ini.get(sec[0], "Attitude", "") or "") == "Bad":
            ini.set(sec[0], "Kill.Sound", kill_sound(sec[0]))
    if ini.save(p("data", "Entities.ini")):
        changed.append("data\\Entities.ini")
    # ItemRacks.ini
    ini = Ini(p("data", "ItemRacks.ini"))
    for rack, (skill, rows) in CRAFT.items():             # whole racks, unless you've edited one since (common.GEN)
        ini.replace_section(rack, [("Type", "Craft"), ("Skill", skill)] + [("Item%d" % (i + 1), r) for i, r in enumerate(rows)])
    for rack, (buy, sell, rows) in NEW_SHOPS.items():
        ini.replace_section(rack, [("Type", "Shop"), ("Buy.Rate", buy), ("Sell.Rate", sell), ("Specific", "1")] +
                            [("Item%d" % (i + 1), r) for i, r in enumerate(rows)])
    for rack, rows in SHOP_ADD.items():
        s = ini.section(rack)
        if s is None:
            continue
        items = [v for k, v in s[1] if k and re.fullmatch(r"Item\d+", k)]
        have = {v.split(",")[0] for v in items}
        n = len(items)
        for r in rows:
            if r.split(",")[0] not in have:
                n += 1
                s[1].append(("Item%d" % n, r))
    if ini.save(p("data", "ItemRacks.ini")):
        changed.append("data\\ItemRacks.ini")
    # Config.ini [Skills] List (edited in place so the rest of the file stays exactly as it is)
    path = p("data", "Config.ini")
    lines = read_lines(path)
    while lines and lines[-1] == "":
        lines.pop()
    sec = None
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].lower()
        elif sec == "skills" and s.lower().startswith("list") and "=" in s:
            k, v = l.split("=", 1)
            skills = [x.strip() for x in v.split(",") if x.strip()]
            for sk in SKILLS_ADD:
                if sk not in skills:
                    skills.append(sk)
            lines[i] = "%s=%s" % (k.rstrip(), ",".join(skills))
    if write_lines(path, lines):
        changed.append("data\\Config.ini")
    # Gathering.ini and Quests.ini
    for fname, table, header in (
            ("Gathering.ini", [(n, list(d.items())) for n, d in GATHERING],
             ["; Things the player can gather, for the in-game Help screen (see dev\\Data Formats.md).",
              "; Generated by dev\\migrate\\build_content.py (GATHERING). Edit it here or there: a rebuild keeps your edits.",
              "; The gathering itself is done by scripts, e.g. data\\Scripts\\Mine Coal_Rock.txt or Pick Berry_Bush.txt."]),
            ("Spells.ini", [(n, [(k, v) for k, v in d.items() if k != "Info"]) for n, d in SPELLS],
             ["; Spells, cast by reading a scroll (an item with Spell=<section> and Use.Words=Cast). See dev\\Data Formats.md.",
              "; Generated by dev\\migrate\\build_content.py (SPELLS). Edit it in the Spell Editor (or there): a rebuild keeps your edits."]),
            ("Quests.ini", QUESTS,
             ["; Quests, for the in-game Help screen (see dev\\Data Formats.md).",
              "; Generated by dev\\migrate\\build_content.py (QUESTS). Edit it in the Quest Editor (or there): a rebuild keeps your edits.",
              "; StageN is shown while the save attribute is N; $Name is replaced with the value of attribute Name."])):
        path = p("data", fname)
        ini = Ini(path)                                   # each section whole, unless you've edited it since (common.GEN)
        ini.header = header
        for name, keys in table:
            ini.replace_section(name, list(keys))
        if ini.save(path):
            changed.append("data\\" + fname)
    changed += apply_patches()
    for name in OBSOLETE_SCRIPTS:
        path = p("data", "Scripts", name + ".txt")
        if os.path.exists(path):
            os.remove(path)
            changed.append("removed data\\Scripts\\%s.txt" % name)
    return changed


# =========================================================================================== checks
def walk_ok(tile):
    return W.walk_data(tile)[24] == "1"


def check_caves(problems, report):
    """Every walkable cell of the cave maps can be reached from a ladder or a map edge (tile-level flood fill),
    and every NPC and item stands on a reachable tile."""
    for name in CAVE_MAPS:
        cells = W.load_cells(name)
        seen, todo = set(), []
        for y in range(MAP_H):
            for x in range(MAP_W):
                t = cells[y][x]
                if t.startswith("Ladder") or ((x in (0, MAP_W - 1) or y in (0, MAP_H - 1)) and walk_ok(t)):
                    todo.append((x, y))
        while todo:
            x, y = todo.pop()
            if (x, y) in seen or not (0 <= x < MAP_W and 0 <= y < MAP_H) or not walk_ok(cells[y][x]):
                continue
            seen.add((x, y))
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        lost = [(x + 1, y + 1) for y in range(MAP_H) for x in range(MAP_W) if walk_ok(cells[y][x]) and (x, y) not in seen
                and cells[y][x] != "Black001"]
        if lost:
            problems.append("%s: walkable tiles not reachable: %s" % (name, " ".join("%d,%d" % c for c in lost[:12])))
        for e in W.MAPS[name]["entities"]:
            if e[0] == "Id":
                continue                                        # (a named tile: build_places)
            tx, ty = int((e[2] + 16) // 32), int((e[3] + 28) // 32)
            if e[1] in getattr(W, "WATER_ENTITIES", ()):          # a fishing spot: fished from the shore next to it
                if not any(c in seen for c in ((tx + 1, ty), (tx - 1, ty), (tx, ty + 1), (tx, ty - 1))):
                    problems.append("%s: %s at tile %d,%d has no reachable shore" % (name, e[1], tx + 1, ty + 1))
                continue
            if (tx, ty) not in seen:
                problems.append("%s: %s %s at tile %d,%d is not reachable" % (name, e[0], e[1], tx + 1, ty + 1))
        report.append("%s: %d reachable tiles" % (name, len(seen)))
    for pr in PATCH_PROBLEMS:
        problems.append(pr)
    for pr in sorted(set(NPC_OPTION_PROBLEMS)):
        problems.append(pr)
    for name in NPC_MOVERS():
        if name not in MOVEMENT:
            problems.append("Entities.ini [%s] is an NPC with no MOVEMENT defaults in build_content.py" % name)
    # entity feet in the patched original maps
    for name, spec in patches().items():
        for e in spec["entities"]:
            if e[0] not in ("MapItem", "StaticObject", "GoodNPC", "BadNPC") or e[1] in getattr(W, "WATER_ENTITIES", ()):
                continue
            from render_maps import sprite
            spr = sprite("Entities", e[1])
            w, h = (spr[0], spr[1]) if spr else (32, 32)
            if not W.walkable(name, e[2] + w / 2, e[3] + h - 1):
                problems.append("%s: patched %s %s stands on unwalkable ground" % (name, e[0], e[1]))


CAVE_MAPS = []


def NPC_MOVERS():
    ini = Ini(p("data", "Entities.ini"))
    return [s for s, _ in ini.sections if ini.get(s, "Type") in ("NPC", "GoodNPC", "BadNPC")]

# Notices next to the Locks (map, tile x, tile y): text
LOCK_NOTICES = {
    ("1,1,0", HOUSE_NOTICE[0], HOUSE_NOTICE[1]):
        "THE OLD BRICK HOUSE\\Locked up since the owner went to the mainland.\\They say he begs in Ashford now, and lost his key\\to the hobgoblins.",
    ("2,4,0", 14, 13): "ROYAL TREASURY\\By order of King Tyron this door stays locked,\\save for the hero who drives the hobgoblins\\from the mine.",
    ("2,4,-1", 6, 9): "THE DEEP SEAM\\Ashford Mining Guild: members only.\\Coal, iron and gold within.",
}
# Scripts an earlier version used that are gone now (deleted from data\Scripts if still there)
OBSOLETE_SCRIPTS = ["Door1 1,1,0",     # the old door hack on the Isle: replaced by the Lock line and Beggar House
                    "2,4,1",           # the wizard's study moved to the palace tower on the Royal Isle (4,4,1)
                    "Wizard Quests", "Wizard Omens", "Wizard Main",  # Talk to Wizard split up (scripts were 99 lines at most)
                    "Use Key With Door001", "Use Key With Door",     # the Key is the Beggars_House_Key now
                    "Unlock Door",
                    "Firemaking Skill"]   # Firemaking is no longer a skill     # doors have no Unlock word now: a locked one gets Open and Unlock from the game


def cliff_runs(cells):
    """An upright run of cliff: Cliff001 (the rounded top end) only at the top, Cliff002 (straight) below it."""
    for y in range(1, len(cells)):
        for x in range(len(cells[0])):
            base, _, rest = cells[y][x].partition("+")
            if base == "Cliff001" and cells[y - 1][x].split("+")[0] in ("Cliff001", "Cliff002"):
                cells[y][x] = "Cliff002" + ("+" + rest if rest else "")


def door_walls(cells):
    """A door (Door001, red brick round it) in a grey stone wall becomes Door002, and in a cave Door003."""
    h, w = len(cells), len(cells[0])
    for y in range(h):
        for x in range(w):
            base, _, rest = cells[y][x].partition("+")
            if base != "Door001":
                continue
            near = [cells[y + dy][x + dx].split("+")[0] for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if 0 <= x + dx < w and 0 <= y + dy < h]
            if any(n.startswith("Brick") for n in near):
                continue
            if any(n.startswith("Stone_Wall") for n in near):
                cells[y][x] = "Door002" + ("+" + rest if rest else "")
            elif any(n.startswith("Cave_") for n in near):
                cells[y][x] = "Door003" + ("+" + rest if rest else "")


def door_facing(cells):
    """Each door is drawn with its foot at the bottom, for a house front with the street below. A door with the outside
    to the north, west or east becomes the same door turned that way (house_tiles.DOOR_TURNS). The outside is the
    side with more open ground behind it (the map edge counts as no end); a tie leaves a north-south doorway as it is."""
    import house_tiles
    from collections import deque
    h, w = len(cells), len(cells[0])
    cap = 400

    def base(x, y):
        return cells[y][x].split("+")[0]

    def is_open(x, y):
        b = base(x, y)
        if b.startswith("Door"):
            return False
        return (TILES[b][0] if b in TILES and TILES[b][0] else W.walk_data(b))[24] == "1"

    def reach(x, y):
        if not (0 <= x < w and 0 <= y < h) or not is_open(x, y):
            return -1
        seen, todo = {(x, y)}, deque([(x, y)])
        while todo and len(seen) < cap:
            cx, cy = todo.popleft()
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if not (0 <= nx < w and 0 <= ny < h):
                    return cap                                      # off the map: out in the world
                if (nx, ny) not in seen and is_open(nx, ny):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        return len(seen)

    for y in range(h):
        for x in range(w):
            b, _, rest = cells[y][x].partition("+")
            if b not in house_tiles.DOOR_WALLS:
                continue
            n, s, wv, e = reach(x, y - 1), reach(x, y + 1), reach(x - 1, y), reach(x + 1, y)
            if min(n, s) < 0 <= min(wv, e):                         # a doorway in a north-south wall
                side = "W" if wv > e else "E"
            elif n > s:
                side = "N"
            else:
                continue
            cells[y][x] = house_tiles.DOOR_TURNS[(b, side)] + ("+" + rest if rest else "")


def hearths(regions):
    """Ashford's bakery and smithy had a campfire burning on the floor: a hearth in the wall instead (it cooks like a
    fire): red brick (Fireplace003), in each one's back (north) wall."""
    chars = regions.legend_chars({"Fireplace003"})
    m = W.MAPS["2,3,0"]
    m["rows"] = set_cells(m["rows"], [(8, 7, chars["Fireplace003"]), (21, 14, chars["Fireplace003"])])
    m["entities"] = [e for e in m["entities"] if e != W.obj("Fire", 8, 8) and e != W.obj("Fire", 21, 15)]
    import glob
    fire = {k for k in W.S if k.startswith("Use Raw_") and k.endswith(" With Fire")}
    fire |= {os.path.basename(f)[:-4] for f in glob.glob(p("data", "Scripts", "Use Raw_* With Fire.txt"))}
    for k in sorted(fire):                              # (the hand-made ones too: meat, chicken)
        W.S[k + "place"] = [("Goto.Script", k), ("End",)]


def furnish_old_houses(regions):
    """The hand-drawn houses (Northgate, Ashford, the farm, the Keep) get what the villages' houses have: a table and
    chairs, a bookshelf against a wall, a potted plant and a rug, kept clear of the doors, the people and the work
    stations, with every bit of floor still reachable. A room that already has furniture is left as it is."""
    import random
    import villages
    floors = set(villages.RUG_FLOORS)
    for name, spec in W.MAPS.items():
        if name in W.PROTECTED_MAPS or name in getattr(W, "NO_SCENERY", ()) or not spec.get("roofs"):
            continue
        rows = spec["rows"]
        grid = {(x, y): W.LEGEND[ch].split("+")[0] for y, row in enumerate(rows, 1) for x, ch in enumerate(row, 1)}
        people, stations = set(), set()
        for e in spec["entities"]:
            try:
                tx, ty = int(float(e[2]) + 16) // 32 + 1, int(float(e[3]) + 28) // 32 + 1
            except (ValueError, IndexError):
                continue
            if e[0] in W.NPC_KINDS:
                people |= {(tx, ty), (tx - 1, ty), (tx + 1, ty), (tx, ty - 1), (tx, ty + 1)}
            else:
                stations |= {(tx, ty), (tx, ty + 1)}          # a range, an anvil...: and the spot to use it from
        marks = {(int(l[0]), int(l[1])) for l in spec.get("locks", [])} |                 {(int(t[1]), int(t[2])) for t in spec.get("triggers", [])}
        changes, done = {}, set()
        for roof in spec["roofs"]:
            x1, y1, x2, y2 = roof[:4]
            seeds = [(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1) if grid.get((x, y)) in floors]
            if not seeds or seeds[0] in done:
                continue
            if any(grid.get((x, y)) == "Table001" or grid.get((x, y)) in villages.RUGS
                   for y in range(y1 - 1, y2 + 2) for x in range(x1, x2 + 1)):
                continue                                      # (a village house: furnished already)
            room, todo = {seeds[0]}, [seeds[0]]                # the room: its floor, flood-filled
            floor = grid[seeds[0]]
            while todo:
                x, y = todo.pop()
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n not in room and grid.get(n) == floor:
                        room.add(n)
                        todo.append(n)
            done |= room
            if len(room) < 6 or len(room) > 60:
                continue
            doors = [c for c in room if any(grid.get(n, "").startswith("Door")
                                            for n in ((c[0], c[1] - 1), (c[0], c[1] + 1), (c[0] - 1, c[1]), (c[0] + 1, c[1])))]
            if not doors:
                continue
            start = doors[0]
            keep = set(doors) | people | stations | marks
            rng = random.Random(zlib.crc32(name.encode()) % 1000 + x1 * 37 + y1)
            placed = {}
            xs, ys = [c[0] for c in room], [c[1] for c in room]
            cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
            tables = sorted(room, key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), rng.random()))
            villages.furnish(placed, room, start, keep, set(), [p for (tx, ty) in tables[:8] for p in (
                {(tx, ty): "Table001", (tx - 1, ty): "Chair003", (tx + 1, ty): "Chair004"},
                {(tx, ty): "Table001", (tx - 1, ty): "Chair003"},
                {(tx, ty): "Table001", (tx + 1, ty): "Chair004"},
                {(tx, ty): "Table001", (tx, ty + 1): "Chair002"})] + [p for (tx, ty) in tables for p in (
                {(tx, ty): "Table001", (tx + 1, ty): "Chair004"}, {(tx, ty): "Table001", (tx - 1, ty): "Chair003"},
                {(tx, ty): "Table001"})], most=1)
            against = sorted((c for c in room if not grid.get((c[0], c[1] - 1), "Grass001") in floors
                              and not grid.get((c[0], c[1] - 1), "").startswith("Door")), key=lambda _: rng.random())
            villages.furnish(placed, room, start, keep, set(), [{c: "Bookshelf001"} for c in against], most=1)
            corners = sorted((c for c in room if sum(n in room for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]),
                                                                       (c[0], c[1] + 1), (c[0], c[1] - 1))) <= 2),
                             key=lambda _: rng.random())
            villages.furnish(placed, room, start, keep, set(), [{c: "Potted_Plant001"} for c in corners], most=1)
            villages.lay_rug(placed, room - set(placed) - (stations - people), rng, floor=floor)
            changes.update(placed)
        if changes:
            chars = regions.legend_chars(set(changes.values()))
            spec["rows"] = set_cells(rows, [(x, y, chars[t]) for (x, y), t in changes.items()])


NOTICE_SCRIPT = re.compile(r"Read Notice(-?\d+,-?\d+,-?\d+)-(\d+),(\d+)$")


# Notices whose title doesn't make a good Id: (how its text starts, the Id)
NOTICE_NAMES = [("EAST: the bridge to Wardhaven", "Wardhaven_Bridge"), ("GO AWAY HOOMANS", "Goblin_Camp_Sign"),
                ("WEST: Ashford\\SOUTH", "Farmlands_Crossroads"), ("WARDHAVEN\\East: the walled town", "Wardhaven_Road"),
                ("KEEP OUT OF THE WATER", "Keep_Out_Of_The_Water")]
# The Isle's own notice (an original map, so its line is replaced through patches()): map, x, y, text
ISLE_NOTICE = ("1,1,0", 212, 594, "KEEP OUT OF THE WATER!")


def notice_id(title, text=""):
    """A notice's Id from its title: "THE OLD BRICK HOUSE" -> The_Old_Brick_House (at most 4 words), or its
    NOTICE_NAMES name."""
    for start, nid in NOTICE_NAMES:
        if text.startswith(start):
            return nid
    words = [w.replace("'", "") for w in re.findall(r"[A-Za-z0-9']+", title)]
    return "_".join(w.capitalize() for w in words[:4]) or "Notice"


def notice_ids():
    """Every notice gets an Id= (like an NPC), and its script is "Read <Id>" (the game tries "<Verb> <Id>" first),
    instead of a name made of its map and pixel position. W.NOTICE_IDS[(map, x, y)] = Id, for patches() and the
    map-entry scripts that Add.Entity a notice."""
    W.NOTICE_IDS = {}
    used = set()
    m, x, y, text = ISLE_NOTICE                       # (its script was hand-made: made here now)
    W.S.setdefault("Read Notice%s-%d,%d" % (m, x, y),
                   [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)])
    for name in sorted(k for k in W.S if NOTICE_SCRIPT.match(k)):
        m, x, y = NOTICE_SCRIPT.match(name).groups()
        x, y = int(x), int(y)
        steps = W.S.pop(name)
        text = next((st[2] for st in steps if isinstance(st, tuple) and st[0] == "Display.Conversation"), "")
        nid = notice_id(text.split("\\")[0], text)
        if nid in used:
            nid += "_" + m.replace(",", "_").replace("-", "m")
        used.add(nid)
        W.NOTICE_IDS[(m, x, y)] = nid
        body = [st for st in steps if not (isinstance(st, str) and not st.endswith(":")) or st.startswith("//")]
        W.S["Read " + nid] = (["// The notice %s on %s (its map line has Id=%s). Generated by build_content.py"
                                      % (nid, m, nid),
                                      (">Distance.From.Clicked.Entity", "64", "@far")] + body +
                                     ["far:", ("Display.Message", "DarkRed", "You can't read that from here!"),
                                      ("End",)])
        spec = W.MAPS.get(m)
        if spec is not None:
            spec["entities"] = [tuple(e[:4]) + ("Id=" + nid,) if tuple(e[:4]) == ("StaticObject", "Notice", x, y)
                                else e for e in spec["entities"]]
    for sname, steps in W.S.items():                 # notices a map-entry script adds (the Isle's pier)
        for i, st in enumerate(steps):
            if isinstance(st, tuple) and st[0] == "Add.Entity" and st[2] == "Notice":
                if st[1] in PL.PLACES:                      # a place: the notice stands on its tile (as the game
                    _, tx, ty = PL.PLACES[st[1]]            # puts it there)
                    x, y = W.place("Notice", tx, ty)
                else:
                    try:
                        x, y = (int(v) for v in st[1].split(","))
                    except ValueError:
                        continue
                nid = W.NOTICE_IDS.get((sname, x, y))
                if nid:
                    steps[i] = st[:4] + ("Id=" + nid,) + st[5:]


def furniture_floors(cells):
    """Furniture is drawn standing on planks; in a room with a tiled (or marble) floor it's the same piece drawn on that
    floor (interior_tiles: Table101 on tiles, Table201 on marble), picked by the floor round it."""
    import interior_tiles as I
    h, w = len(cells), len(cells[0])
    plain = set(I.FURNITURE)

    def floor_of(t):
        if t in ("Plank001", "Tile001", "Marble001"):
            return t
        if t.startswith("Rug") and t[3:].isdigit():
            return "Tile001" if int(t[3:]) >= 31 else "Plank001"
        for f in ("Plank", "Tile", "Marble"):
            if "_Thin_" + f in t:
                return f + "001"
        return None
    out = [row[:] for row in cells]
    for y in range(h):
        for x in range(w):
            b = cells[y][x].split("+")[0]
            if b not in plain:
                continue
            near = [floor_of(cells[y + dy][x + dx].split("+")[0]) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                    if (dx or dy) and 0 <= x + dx < w and 0 <= y + dy < h]
            near = [f for f in near if f]
            if not near:
                continue
            f = max(set(near), key=near.count)
            if f in I.FURNITURE_FLOORS:
                out[y][x] = I.furniture_on(b, f) + cells[y][x][len(b):]
    cells[:] = out


def thin_walls(cells):
    """Under every roof, the house's side and back walls (a wall tile with the outside beyond it) become the floor
    with a thin wall along that edge (house_tiles: <Wall>_Thin_<Floor>NNN), so the rooms reach nearly to the walls.
    The front wall (outside the roof, with the door) stays as it is, and so do walls between rooms, fireplaces,
    windows and doors, and any wall beside a window or a door (a house's front). The floor is the one next to it in
    the room (a rug's or the furniture's floor underneath). An upper floor (no roofs: rooms on black) is the same,
    the black being the outside."""
    import house_tiles as H
    h, w = len(cells), len(cells[0])

    def base(c):
        return c.split("+")[0]

    flat = [base(c) for row in cells for c in row]
    upper = (not any("+Roof(" in c for row in cells for c in row) and "Black001" in flat and
             not any(t.startswith("Cave_") for t in flat))      # (not a cellar dug in the rock: it matches a house above)

    def group(c):
        if upper:
            return None if base(c) == "Black001" else "1"
        m = re.search(r"\+Roof\([^)]*\.(\d+)\)", c)
        return m.group(1) if m else None

    def floor_of(c):
        t = base(c)
        if t in H.THIN_FLOORS:
            return t
        m = re.fullmatch(r"Rug(\d{3})", t)
        if m:
            return "Tile001" if int(m.group(1)) >= 31 else "Plank001"
        return None

    def opening(t):
        return "_Window" in t or t.startswith("Door")

    def in_front(x, y):
        """Is x,y in a straight run of wall with a window or a door in it (a house's front, left whole)?"""
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            while 0 <= nx < w and 0 <= ny < h:
                t = base(cells[ny][nx])
                if opening(t):
                    return True
                if t not in H.WALL_BASES:
                    break
                nx, ny = nx + dx, ny + dy
        return False

    out = [row[:] for row in cells]
    for y in range(h):
        for x in range(w):
            c = cells[y][x]
            g = group(c)
            if g is None or base(c) not in H.WALL_BASES:
                continue
            edges, inward, mixed = "", [], in_front(x, y)
            for side, dx, dy in (("N", 0, -1), ("S", 0, 1), ("W", -1, 0), ("E", 1, 0)):
                nx, ny = x + dx, y + dy
                ng = group(cells[ny][nx]) if 0 <= nx < w and 0 <= ny < h else None
                if ng is None:
                    nt = base(cells[ny][nx]) if 0 <= nx < w and 0 <= ny < h else ""
                    solid = (nt in H.WALL_BASES or opening(nt) or nt.startswith("Fireplace") or
                             any(nt.startswith(v + "_") for v in H.WALL_BASES.values()))   # (ivy, a lantern, a sign)
                    if not solid:
                        edges += side               # (against the house's solid front wall: no strip, it's there)
                elif ng != g:
                    mixed = True                    # (a wall between two buildings: left whole)
                else:
                    inward.append(cells[ny][nx])
            edges = {"NE": "NE", "EN": "NE", "SE": "SE", "ES": "SE", "SW": "SW", "WS": "SW", "NW": "NW",
                     "WN": "NW"}.get(edges, edges)
            if mixed or edges not in H.THIN_EDGES:
                continue
            floors = [f for f in (floor_of(n) for n in inward) if f]
            if not floors:                          # (furniture all round it: the house's own floor)
                near = [floor_of(cells[yy][xx]) for yy in range(max(0, y - 3), min(h, y + 4))
                        for xx in range(max(0, x - 3), min(w, x + 4)) if group(cells[yy][xx]) == g]
                near = [f for f in near if f]
                floors = [max(set(near), key=near.count)] if near else ["Plank001"]
            name = H.thin_name(base(c), max(set(floors), key=floors.count), edges)
            if name:
                out[y][x] = name + c[len(base(c)):]
    cells[:] = out


def restyle_old_houses(regions):
    """The Southlands' hand-drawn brick houses (Northgate, Ashford, the farm) get the villages' look: a shingle roof with
    eaves, a ridge and a chimney, and where the front wall with the door is just below the roof, an upper storey under
    the eaves and windows either side of the door. Houses facing north (the roof below the wall) get the roof, and
    windows upside down (Brick_Window003, the sill at the top) either side of the door in the wall above it;
    the Keep's stone halls (any roof over Stone_Wall001) keep the plain Roof001."""
    import random
    import villages
    chars = regions.legend_chars({"Brick_Window001", "Brick_Window003"})
    win, win_n = chars["Brick_Window001"], chars["Brick_Window003"]
    for name, spec in W.MAPS.items():
        if name in W.PROTECTED_MAPS:
            continue
        rows = spec["rows"]
        out = []
        for r in spec["roofs"]:
            if len(r) > 5:
                out.append(r)
                continue
            x1, y1, x2, y2, g = r
            below = [W.LEGEND[c] for c in rows[y2][x1 - 1:x2]] if y2 < len(rows) else []
            inside = {W.LEGEND[c] for row in rows[y1 - 1:y2] for c in row[x1 - 1:x2]}
            if "Stone_Wall001" in below or "Stone_Wall001" in inside:
                out.append(r)
            elif "Door001" in below and set(below) <= {"Brick001", "Door001"} and y2 - y1 >= 2:
                door = x1 + below.index("Door001")
                row = list(rows[y2])
                for x in range(x1 + 1, x2):
                    if x != door and (x - door) % 2 == 1:
                        row[x - 1] = win
                rows[y2] = "".join(row)
                material = villages.pick(random.Random("%s:%d:%d" % (name, x1, y1)), villages.ROOFS["Brick001"])
                out.append((x1, y1, x2, y2, g, villages.roof_spec(material, "Brick001", x2 - x1 - 1, [])))
            else:
                above = [W.LEGEND[c] for c in rows[y1 - 2][x1 - 1:x2]] if y1 >= 2 else []
                if "Door001" in above and set(above) <= {"Brick001", "Door001"}:
                    door = x1 + above.index("Door001")
                    row = list(rows[y1 - 2])
                    for x in range(x1 + 1, x2):
                        if x != door and (x - door) % 2 == 1:
                            row[x - 1] = win_n
                    rows[y1 - 2] = "".join(row)
                out.append((x1, y1, x2, y2, g, villages.pick(random.Random("%s:%d:%d" % (name, x1, y1)),
                                                             villages.ROOFS["Brick001"])))
        spec["roofs"] = out


# =========================================================================================== hook
def extend(world):
    global W
    W = world
    W.LEGEND.update(CAVE_LEGEND)
    W.CELL_HOOKS.append(dress)
    W.CELL_HOOKS.append(door_walls)
    W.CELL_HOOKS.append(door_facing)
    W.CELL_HOOKS.append(cliff_runs)
    import house_tiles                                  # the villages' roofs: like Roof001, an overlay
    for k in house_tiles.DOOR_TURNS.values():           # the doors turned to face north, west or east
        TILES[k] = ("1" * 49, "1", "", None, "0", None)
    for w in house_tiles.WALL_BASES:                     # thin walls inside the houses (thin_walls below)
        for f in house_tiles.THIN_FLOORS:
            for e in house_tiles.THIN_EDGES:
                TILES[house_tiles.thin_name(w, f, e)] = (house_tiles.thin_walk(e), "0", "", None, "0", None)
    W.ROOF_HOOKS.append(thin_walls)
    import interior_tiles                                # the furniture on tiled and marble floors
    for n in interior_tiles.FURNITURE:
        for f in interior_tiles.FURNITURE_FLOORS:
            TILES[interior_tiles.furniture_on(n, f)] = TILES[n]
    W.ROOF_HOOKS.append(furniture_floors)
    import wall_furniture                                # bookshelves, beds and plants back against the walls
    W.ROOF_HOOKS.append(wall_furniture.wall_furniture)
    import village_decor                                 # the houses' character and the villages' decorations
    TILES.update(village_decor.TILE_DATA)
    import interior_props                                # a house furnished for its trade (interiors.py)
    TILES.update(interior_props.TILE_DATA)
    for k, o in house_tiles.DOOR_OPEN.items():           # every door opens as you go through (and shuts after you)
        if k in TILES:
            TILES[k] = TILES[k][:2] + ("",) + TILES[k][3:]  # (no Open / Unlock: a locked one says so when bumped)
        else:
            TILES[k] = ("1" * 49, "1", "", None, "0", None)
        TILES[o] = ("1" * 49, "1", "", "An open door.", "0", None)
        TILE_EXTRA.setdefault(k, []).append(("Open.Tile", o))
    for k in house_tiles.TILES:
        if "_Roof" in k or "_Upper" in k:               # (the upper storeys' fronts are part of the roof)
            TILES[k] = ("0" * 49, "0", "", "", "1", None)
        elif k.endswith(("_Window001", "_Window003")):
            TILES[k] = ("0" * 49, "1", "", "A window. Through the glass: a snug room, a fire in the hearth.", "0", None)
        elif k.endswith("_Window002"):
            TILES[k] = ("0" * 49, "1", "Climb Through,Examine",
                        "A window with a loose shutter. The catch is broken: you could climb through.", "0", None)
    import farm_tiles                                   # the cliff pieces' walk data, from their drawn shapes
    for k in range(1, 6):
        TILES["Cliff%03d" % k] = (farm_tiles.walk_data("Cliff%03d" % k), None, None, None, None, None)
    W.PROTECTED_MAPS.discard("1,1,-1")
    caves = cave_maps()
    place_ores(caves)
    W.MAPS.update(caves)
    CAVE_MAPS[:] = list(caves)
    surface_changes()
    place_trees(W.MAPS)
    import build_regions                                    # the Wildlands: 36 maps south of the Southlands, 6 quests
    import build_status                                     # archers and casters, status effects, the gravestone
    import build_eastreach
    build_status.before_regions(build_regions, build_eastreach)
    build_regions.extend(W, sys.modules[__name__])
    import build_eastreach                                  # the Eastreach: 16 maps over the old bridge, 2 quests
    build_eastreach.extend(W, sys.modules[__name__], build_regions)
    import build_walled                                     # Wardhaven: a walled town, shut until the dragon is dead
    build_walled.extend(W, sys.modules[__name__], build_regions)
    import build_palace                                     # King Tyron's palace on the Royal Isle (4,4,0)
    build_palace.extend(W, sys.modules[__name__], build_regions)
    import build_cinder                                     # the Cinderlands, the main story, banks, the Dragonforge
    build_cinder.extend(W, sys.modules[__name__], build_regions)
    restyle_old_houses(build_regions)
    hearths(build_regions)
    furnish_old_houses(build_regions)
    import interiors                                     # shops, banks, the herbalist's... furnished for their trade
    interiors.theme_interiors(W, build_regions, sys.modules[__name__])
    build_status.extend(W, sys.modules[__name__])
    village_decor.dress_villages(W, build_regions, sys.modules[__name__])
    import build_travel                                     # waystones (fast travel), quest markers, ambience
    build_travel.extend(W, sys.modules[__name__], build_regions)
    import build_music                                      # which music plays where (data\Music.ini)
    build_music.extend(W, build_regions)
    import build_fishing                                    # fishing spots (before the scenery, which keeps clear)
    build_fishing.extend(W, sys.modules[__name__], build_regions)
    import build_boats                                      # the ferry's boats at the two piers
    build_boats.extend(W, sys.modules[__name__])
    import build_scenery                                    # scenery, landmarks, wildlife and secrets
    build_scenery.extend(W, sys.modules[__name__])
    for g_name, g in GATHERING:                             # the pond can be fished, wells and the pond give water
        if "Water001" in g.get("Source", "") and g.get("Tool") in ("Fishing_Rod", "Bucket"):
            extra = " Pond001" + (" Well001" if g.get("Tool") == "Bucket" else "")
            if "Pond001" not in g["Source"]:
                g["Source"] += extra
    for name, spec in W.MAPS.items():
        spec["entities"] = with_options(name, spec["entities"])
    W.S.update(scripts())
    W.S.update(build_scenery.scripts())
    W.S["Kill Hobgoblin"] = kill_hobgoblin()
    W.LADDER_DIR.update({"Ladder004": 1, "Ladder005": -1, "Ladder006": -1, "Ladder007": -1,
                         "Ladder008": 1, "Ladder009": -1, "Stairs001": 1, "Stairs002": -1})
    W.LADDER_SPECIAL.clear()
    # the notice by the grotto hole on the Isle (2,1,0 is an original map: the notice itself is a patch)
    text = "THE GROTTO\\A ladder goes down into the caves under the Isle.\\Rats and bats below. Bring a lantern... and a sword."
    W.S[W.notice_script_name("2,1,0", 22, 11)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]
    # notices that hint at the Locks
    for (mname, tx, ty), text in LOCK_NOTICES.items():
        W.S[W.notice_script_name(mname, tx, ty)] = [("Display.Conversation", "Notice", text, "Okay", "@end"), "end:", ("End",)]
    # keep build_world's own tables in step with ours, so the two data passes agree (no flip-flopping files)
    for rack, rows in SHOP_ADD.items():
        if rack in W.ITEM_RACKS:
            keys = W.ITEM_RACKS[rack]
            have = {v.split(",")[0] for k, v in keys if k.startswith("Item")}
            n = sum(1 for k, _ in keys if k.startswith("Item"))
            for r in rows:
                if r.split(",")[0] not in have:
                    n += 1
                    keys.append(("Item%d" % n, r))
    W.SMITHING[:] = [("Type", "Craft"), ("Skill", "Smithing")] +         [("Item%d" % (i + 1), r) for i, r in enumerate(CRAFT["CRAFT-Smithing"][1])]
    for name, keys in ENTITY_KEYS.items():
        if name in W.ENTITY_KEYS:
            mine = dict(keys)
            W.ENTITY_KEYS[name] = [(k, mine.pop(k, v)) for k, v in W.ENTITY_KEYS[name]] + list(mine.items())
    W.EXTRA_STEPS.append(update_content_data)
    W.EXTRA_CHECKS.append(check_caves)
    import build_omens                                      # The Ashen Omens: the chain that leads to the dragon
    build_omens.extend(W, sys.modules[__name__], build_regions)
    import build_dragon                                     # the last quest: last, as it adds to the wizard's script
    build_dragon.extend(W, sys.modules[__name__])
    build_omens.after_dragon()
    import build_hob                                        # Old Hob: an NPC who changes sides (a side quest:
    build_hob.extend(W, sys.modules[__name__], build_regions)   # after the dragon, which doesn't wait for it)
    import build_herbs                                      # more herbs, the herb redrawn (last: every map is
    build_herbs.extend(W, sys.modules[__name__])            # there, the scenery down)
    build_palace.finish()                                   # the palace's notices and words, over scripts()'
    notice_ids()                                            # every notice: an Id=, and its script by that Id
    build_fishing.finish()                                  # fishing only at the spots (over the water scripts)
    build_travel.add_markers()                              # last: every quest is in QUESTS by now
    import quest_notes                                      # the journal's notes, in every quest's scripts
    build_cinder.finish()                                   # the main story, every quest's Requires and their gates
    unused = quest_notes.apply(W.S, QUESTS)
    W.EXTRA_CHECKS.append(lambda problems, report: problems.extend(unused))
