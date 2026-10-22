"""Homesteads: every player can have a home of their own, on a map of its own, and build on it (the multiplayer
server's dsengine/homes.py). Run it again after rebuilding the world (build_world.py rewrites the maps): it makes what's
missing and leaves the rest as it is.

  python -I "Dev\\migrate\\build_homestead.py"

  * Homestones: obelisks like the waystones, one beside each town's waystone and one on every home. Touch one to go
    home (with an Access Crystal), to visit other players' homes they've opened, or (at home) to say who may visit.
  * The quest "A Place of Your Own": the settler by Ashford's homestone (Id=Homestead_Settler) wants planks and stone
    blocks, and gives you the Access Crystal. After it she sells Homestead Scrolls (Magic 12: home from anywhere) and
    her carpenter's bench (CRAFT-Construction) is free to use.
  * The Construction skill (Config [Skills]), its materials (Plank, Nails, Stone, Stone_Block: rocks can be mined for
    stone now) and Data\\Buildables.ini, what can be built: floors, walls, doors, windows, roofs, furniture, lights,
    the garden, and workshops (a chest that is your bank, a bench, a range, an anvil, a furnace, an alchemy table).
  * Data\\Homestead.txt: the land a new home starts as (a meadow in a ring of forest, the homestone where you arrive).
"""
import colorsys
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from dragonsword import ini  # noqa: E402

DATA = os.path.join(ROOT, "Data")
ENTS = os.path.join(ROOT, "Sprites", "Entities")
XT, YT = 25, 21
TOWNS = {"2,3,0": "Ashford", "4,8,0": "Highwatch", "1,10,0": "Dunerest", "7,6,0": "Thornwick", "7,4,0": "Emberwatch"}
SETTLER_TOWN = "2,3,0"
ARRIVAL = (13, 18)              # home: the tile you arrive on, and (next to it) the homestone and a carpenter's bench
HOME_STONE = (12, 18)
HOME_BENCH = (15, 18)
MAGIC_LEVEL = 12                # Homestead Scrolls need this much Magic

ITEMS = {
    "Homestone": {"Type": "StaticObject", "Use.Words": "Touch,Examine", "Light": "40",
                  "Examine.Info": "A homestone: an obelisk like the waystones, with a hearth rune that glows warm. "
                                  "Touch it to go home, or to visit a friend's home."},
    "Access_Crystal": {"Type": "MapItem", "Droppable": "0", "Value": "0",
                       "Examine.Info": "Your homestead's Access Crystal. Touch a homestone with it to go home."},
    "Homestead_Scroll": {"Type": "MapItem", "Use.Words": "Cast", "Stackable": "10", "Value": "60",
                         "Spell": "Homestead",
                         "Examine.Info": "A scroll of Homestead: takes you to your own home, wherever you are. "
                                         "Magic %d. Right-click it and Cast." % MAGIC_LEVEL},
    "Plank": {"Type": "MapItem", "Stackable": "50", "Value": "4",
              "Examine.Info": "A sawn plank. Builders use these by the stack."},
    "Nails": {"Type": "MapItem", "Stackable": "200", "Value": "1",
              "Examine.Info": "Iron nails. Every house needs a few hundred."},
    "Stone": {"Type": "MapItem", "Stackable": "30", "Value": "2",
              "Examine.Info": "A lump of stone, mined from a rock. A mason can cut it into blocks."},
    "Stone_Block": {"Type": "MapItem", "Stackable": "30", "Value": "6",
                    "Examine.Info": "A squared block of stone, for walls and paving."},
    "Home_Chest": {"Type": "StaticObject", "Use.Words": "Open,Examine",
                   "Examine.Info": "A homestead chest. It opens onto your bank, but only for whoever's home this is."},
    "Carpenters_Bench": {"Type": "StaticObject", "Use.Words": "Craft,Examine",
                         "Examine.Info": "A carpenter's bench, with a saw and a mason's chisel. Saw planks, make "
                                         "nails and cut stone blocks here (Construction)."},
}
SKILL_ICON = "Plank"

# Data\Buildables.ini: what can be built at home. Kind: Tile (the ground: floors, walls, doors), Decor (on top of the
# ground), Roof (over it: the pieces are worked out from the roof's shape) or Object (a workshop: an object on the tile).
# On: what has to be under it ("wall" = any wall, a tile name = that tile). Needs: materials. Level, XP: Construction.
B = []


def b(piece, kind, cat, name, needs, level, xp, on=""):
    B.append((piece, {"Kind": kind, "Category": cat, "Name": name, "Needs": needs, "Level": str(level),
                      "XP": str(xp), "On": on}))


b("Grass001", "Tile", "Floors", "Grass", "Logs 0", 1, 0.02)
b("Dirt001", "Tile", "Floors", "Dirt path", "Logs 0", 1, 0.02)
b("Plank001", "Tile", "Floors", "Wooden floor", "Plank 1 Nails 2", 1, 0.06)
b("Paving001", "Tile", "Floors", "Paving", "Stone_Block 1", 3, 0.08)
b("Stone001", "Tile", "Floors", "Flagstones", "Stone_Block 1", 5, 0.08)
b("Sand001", "Tile", "Floors", "Sand", "Stone 1", 2, 0.04)
b("Tile001", "Tile", "Floors", "Tiled floor", "Stone_Block 1", 10, 0.1)
b("Carpet001", "Tile", "Floors", "Red carpet", "Plank 1 Ball_of_Wool 2", 14, 0.12)
b("Carpet002", "Tile", "Floors", "Blue carpet", "Plank 1 Ball_of_Wool 2", 14, 0.12)
b("Marble001", "Tile", "Floors", "Marble", "Stone_Block 2 Silver_Bar 1", 30, 0.25)
b("Timber001", "Tile", "Walls", "Timber wall", "Plank 2 Nails 4", 1, 0.12)
b("Plaster001", "Tile", "Walls", "Plaster wall", "Plank 1 Stone 2 Nails 2", 6, 0.15)
b("Brick001", "Tile", "Walls", "Brick wall", "Stone_Block 2", 12, 0.2)
b("Stone_Wall001", "Tile", "Walls", "Stone wall", "Stone_Block 3", 18, 0.25)
b("Sandstone001", "Tile", "Walls", "Sandstone wall", "Stone_Block 2 Sand 2", 24, 0.25)
b("Hedge001", "Tile", "Walls", "Hedge", "Logs 1 Herb 1", 4, 0.1)
b("Fence001", "Decor", "Walls", "Fence", "Plank 1 Nails 2", 2, 0.06)
b("Fence002", "Decor", "Walls", "Fence (posts)", "Plank 1 Nails 2", 2, 0.06)
b("Door001", "Tile", "Doors", "Wooden door", "Plank 3 Nails 6 Iron_Bar 1", 3, 0.3)
b("Door002", "Tile", "Doors", "Stout door", "Plank 4 Nails 8 Iron_Bar 1", 10, 0.4)
b("Door004", "Tile", "Doors", "Cottage door", "Plank 3 Nails 6", 5, 0.3)
b("Door005", "Tile", "Doors", "Painted door", "Plank 3 Nails 6 Iron_Bar 1", 8, 0.35)
b("Door006", "Tile", "Doors", "Arched door", "Plank 4 Nails 6 Stone_Block 2", 16, 0.45)
b("Timber_Window001", "Decor", "Windows", "Window (timber)", "Plank 1 Glass 1", 4, 0.2, "Timber001")
b("Plaster_Window001", "Decor", "Windows", "Window (plaster)", "Plank 1 Glass 1", 6, 0.2, "Plaster001")
b("Brick_Window001", "Decor", "Windows", "Window (brick)", "Stone_Block 1 Glass 1", 12, 0.25, "Brick001")
b("Stone_Wall_Window001", "Decor", "Windows", "Window (stone)", "Stone_Block 1 Glass 1", 18, 0.3, "Stone_Wall001")
b("Sandstone_Window001", "Decor", "Windows", "Window (sandstone)", "Stone_Block 1 Glass 1", 24, 0.3, "Sandstone001")
b("Thatch", "Roof", "Roofs", "Thatched roof", "Wheat 2 Logs 1", 5, 0.1)
b("Shingle", "Roof", "Roofs", "Shingle roof", "Plank 2 Nails 4", 9, 0.14)
b("Clay", "Roof", "Roofs", "Clay tile roof", "Stone 1 Plank 1", 15, 0.16)
b("Slate", "Roof", "Roofs", "Slate roof", "Stone_Block 1 Nails 2", 20, 0.2)
b("Copper", "Roof", "Roofs", "Copper roof", "Copper_Bar 1 Plank 1", 35, 0.3)
b("Table001", "Decor", "Furniture", "Table", "Plank 4 Nails 6", 2, 0.25)
b("Chair001", "Decor", "Furniture", "Chair", "Plank 2 Nails 3", 2, 0.15)
b("Chair002", "Decor", "Furniture", "Chair", "Plank 2 Nails 3", 2, 0.15)
b("Chair003", "Decor", "Furniture", "Chair", "Plank 2 Nails 3", 2, 0.15)
b("Chair004", "Decor", "Furniture", "Chair", "Plank 2 Nails 3", 2, 0.15)
b("Bench001", "Decor", "Furniture", "Bench", "Plank 3 Nails 4", 3, 0.2)
b("Bed001", "Decor", "Furniture", "Bed (sleep here: you wake here if you fall)", "Plank 4 Nails 6 Wool 4", 6, 0.4)
b("Bed002", "Decor", "Furniture", "Double bed (you wake here if you fall)", "Plank 6 Nails 8 Wool 6", 12, 0.5)
b("Bookshelf001", "Decor", "Furniture", "Bookshelf", "Plank 5 Nails 6", 10, 0.35)
b("Counter001", "Decor", "Furniture", "Counter", "Plank 4 Nails 6", 8, 0.3)
b("Shelf_Goods001", "Decor", "Furniture", "Shelves", "Plank 4 Nails 4", 8, 0.3)
b("Barrel001", "Decor", "Furniture", "Barrel", "Plank 3 Iron_Bar 1", 5, 0.2)
b("Crate001", "Decor", "Furniture", "Crate", "Plank 2 Nails 4", 3, 0.15)
b("Sacks001", "Decor", "Furniture", "Sacks", "Wheat 3 Ball_of_Wool 1", 4, 0.15)
b("Rug001", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Rug002", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Rug003", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Rug004", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Rug005", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Rug006", "Decor", "Furniture", "Rug", "Ball_of_Wool 3", 7, 0.2)
b("Potted_Plant001", "Decor", "Furniture", "Potted plant", "Herb 2", 4, 0.1)
b("Cauldron001", "Decor", "Furniture", "Cauldron", "Iron_Bar 4", 14, 0.4)
b("Herb_Rack001", "Decor", "Furniture", "Herb rack", "Plank 2 Herb 4", 11, 0.3)
b("Potion_Shelf001", "Decor", "Furniture", "Potion shelf", "Plank 3 Empty_Vial 4", 16, 0.4)
b("Coin_Chest001", "Decor", "Furniture", "Coin chest", "Plank 3 Gold_Bar 1", 25, 0.5)
b("Statue001", "Decor", "Furniture", "Statue", "Stone_Block 8", 28, 0.8)
b("Banner001", "Decor", "Furniture", "Banner", "Ball_of_Wool 4 Logs 1", 13, 0.3)
b("Fireplace001", "Tile", "Lights", "Fireplace", "Stone_Block 4 Iron_Bar 1", 9, 0.5)
b("Fireplace002", "Tile", "Lights", "Fireplace", "Stone_Block 4 Iron_Bar 1", 9, 0.5)
b("Candles001", "Decor", "Lights", "Candles", "Wheat 1 Logs 1", 3, 0.1)
b("Wall_Torch001", "Decor", "Lights", "Wall torch", "Logs 1 Coal 1", 4, 0.15, "wall")
b("Lamp_Post001", "Decor", "Lights", "Lamp post", "Iron_Bar 2 Glass 1", 12, 0.35)
b("Flowers001", "Decor", "Garden", "Flowers", "Herb 1", 1, 0.05)
b("Flowers002", "Decor", "Garden", "Flowers", "Herb 1", 1, 0.05)
b("Flowers003", "Decor", "Garden", "Flowers", "Herb 1", 1, 0.05)
b("Flower_Bed001", "Decor", "Garden", "Flower bed", "Herb 2 Plank 1", 3, 0.1)
b("Flower_Bed002", "Decor", "Garden", "Flower bed", "Herb 2 Plank 1", 3, 0.1)
b("Flower_Bed003", "Decor", "Garden", "Flower bed", "Herb 2 Plank 1", 3, 0.1)
b("Herb_Patch001", "Decor", "Garden", "Herb patch (pick herbs)", "Herb 3", 5, 0.2)
b("Berry_Bush001", "Decor", "Garden", "Berry bush (pick berries)", "Berries 3", 7, 0.25)
b("Mushroom_Patch001", "Decor", "Garden", "Mushroom patch (pick)", "Cave_Mushroom 2", 13, 0.3)
b("Wheat001", "Tile", "Garden", "Wheat (harvest)", "Wheat 2", 6, 0.2)
b("Tree001", "Decor", "Garden", "Tree (chop)", "Logs 2", 8, 0.3)
b("Oak_Tree001", "Decor", "Garden", "Oak (chop)", "Oak_Logs 2", 15, 0.4)
b("Willow_Tree001", "Decor", "Garden", "Willow (chop)", "Willow_Logs 2", 22, 0.5)
b("Yew_Tree001", "Decor", "Garden", "Yew (chop)", "Yew_Logs 2", 32, 0.7)
b("Haystack001", "Decor", "Garden", "Haystack", "Wheat 4", 4, 0.1)
b("Scarecrow001", "Decor", "Garden", "Scarecrow", "Wheat 2 Logs 1 Ball_of_Wool 1", 6, 0.15)
b("Well001", "Decor", "Garden", "Well", "Stone_Block 6 Plank 2 Iron_Bar 1", 18, 0.6)
b("Fountain001", "Decor", "Garden", "Fountain", "Stone_Block 10 Copper_Bar 2", 26, 0.9)
b("Pond001", "Tile", "Garden", "Pond", "Stone 2", 10, 0.2)
b("Rock002", "Decor", "Garden", "Rock (mine for stone)", "Stone 4", 5, 0.1)
b("Carpenters_Bench", "Object", "Workshops", "Carpenter's bench (Construction)", "Plank 4 Nails 6", 1, 0.4)
b("Home_Chest", "Object", "Workshops", "Chest (your bank)", "Plank 6 Nails 10 Iron_Bar 2", 5, 0.8)
b("Workbench", "Object", "Workshops", "Workbench (Crafting)", "Plank 6 Nails 10", 8, 0.8)
b("Range", "Object", "Workshops", "Range (Cooking)", "Stone_Block 6 Iron_Bar 2", 14, 1.0)
b("Alchemy_Table", "Object", "Workshops", "Alchemy table (Herblore)", "Plank 6 Glass 4 Nails 6", 20, 1.2)
b("Anvil", "Object", "Workshops", "Anvil (Smithing)", "Iron_Bar 10", 25, 1.4)
b("Furnace", "Object", "Workshops", "Furnace (smelting)", "Stone_Block 12 Coal 6 Iron_Bar 2", 30, 1.6)

CRAFT = [   # CRAFT-Construction, at a carpenter's bench: product, ingredients, xp, level, quantity made
    "Plank,Logs 1,0.08,1,2",
    "Nails,Iron_Bar 1,0.1,1,12",
    "Nails,Bronze_Bar 1,0.08,1,8",
    "Stone_Block,Stone 2,0.1,2,1",
    "Plank,Oak_Logs 1,0.12,10,3",
    "Plank,Willow_Logs 1,0.16,20,4",
    "Plank,Yew_Logs 1,0.2,30,5",
]


# ---------------------------------------------------------------- sprites
def load(name):
    return pygame.image.load(os.path.join(ENTS, name + ".png"))


def save(img, name):
    path = os.path.join(ENTS, name + ".png")
    if os.path.exists(path):
        return
    pygame.image.save(img, path)
    print("Made Sprites\\Entities\\%s.png" % name)


def recolour(img, hue, sat=1.0, light=1.0, only_coloured=True):
    """Each pixel's hue turned to hue (0..1) (only the coloured ones, unless only_coloured is off)."""
    out = img.copy()
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b_, a = out.get_at((x, y))
            if a == 0:
                continue
            hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b_ / 255)
            if only_coloured and ss < 0.25:
                ll = min(1, ll * light)
            else:
                hh, ss, ll = hue, min(1, ss * sat), min(1, ll * light)
            r, g, b_ = colorsys.hls_to_rgb(hh, ll, ss)
            out.set_at((x, y), (int(r * 255), int(g * 255), int(b_ * 255), a))
    return out


def planks():
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    rng = random.Random(7)
    for i, y in enumerate((20, 13, 6)):
        x0 = 3 + i * 2
        base = (164 - i * 14, 116 - i * 10, 64 - i * 6)
        pygame.draw.rect(img, base, (x0, y, 26 - i * 2, 6))
        for k in range(4):
            gx = x0 + rng.randint(2, 22 - i * 2)
            pygame.draw.line(img, (base[0] - 30, base[1] - 26, base[2] - 18), (gx, y + 2), (gx + 3, y + 2))
        pygame.draw.rect(img, (84, 56, 30), (x0, y, 26 - i * 2, 6), 1)
    return img


def nails():
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    for i, (x, y, a) in enumerate(((8, 8, 0.6), (14, 12, 1.1), (20, 7, 0.9), (11, 18, 0.4), (19, 17, 1.3))):
        dx, dy = math.cos(a) * 9, math.sin(a) * 9
        pygame.draw.line(img, (150, 150, 158), (x, y), (x + dx, y + dy), 2)
        pygame.draw.line(img, (210, 210, 220), (x, y), (x + dx * 0.6, y + dy * 0.6), 1)
        pygame.draw.circle(img, (110, 110, 118), (x, y), 2)
    return img


def stone():
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    pts = [(7, 21), (10, 12), (17, 8), (25, 12), (27, 20), (21, 26), (12, 27)]
    pygame.draw.polygon(img, (128, 124, 116), pts)
    pygame.draw.polygon(img, (160, 156, 148), [(10, 12), (17, 8), (25, 12), (17, 15)])
    pygame.draw.polygon(img, (90, 86, 80), [(21, 26), (27, 20), (25, 12), (17, 15), (12, 27)], 0)
    pygame.draw.polygon(img, (62, 60, 56), pts, 1)
    return img


def stone_block():
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.polygon(img, (176, 172, 162), [(6, 12), (16, 7), (27, 12), (17, 17)])      # top
    pygame.draw.polygon(img, (138, 134, 126), [(6, 12), (17, 17), (17, 27), (6, 22)])     # left
    pygame.draw.polygon(img, (106, 102, 96), [(17, 17), (27, 12), (27, 22), (17, 27)])    # right
    for poly in ([(6, 12), (16, 7), (27, 12), (17, 17)], [(6, 12), (17, 17), (17, 27), (6, 22)],
                 [(17, 17), (27, 12), (27, 22), (17, 27)]):
        pygame.draw.polygon(img, (70, 68, 64), poly, 1)
    return img


def make_sprites():
    pygame.init()
    save(recolour(load("Waystone"), 0.09, 1.3, 1.05), "Homestone")            # (the blue rune glows amber)
    save(recolour(load("Sapphire"), 0.36, 1.1, 1.1), "Access_Crystal")        # (an emerald-green crystal)
    save(recolour(load("Teleport_Scroll"), 0.09, 1.2), "Homestead_Scroll")
    save(recolour(load("Chest"), 0.0, 0.9, 0.85, only_coloured=False), "Home_Chest")
    bench = recolour(load("Workbench"), 0.08, 1.0, 1.08, only_coloured=False)
    pygame.draw.polygon(bench, (196, 200, 210), [(6, 9), (16, 9), (16, 12), (6, 12)])       # a saw on the bench
    pygame.draw.rect(bench, (110, 70, 40), (16, 8, 4, 5))
    save(bench, "Carpenters_Bench")
    save(planks(), "Plank")
    save(nails(), "Nails")
    save(stone(), "Stone")
    save(stone_block(), "Stone_Block")


# ---------------------------------------------------------------- data files
def write_section(path, name, values):
    if ini.section(name, path):
        return False
    for k, v in values.items():
        ini.write(name, k, v, path)
    return True


def write_entities():
    path = os.path.join(DATA, "Entities.ini")
    for name, values in ITEMS.items():
        if write_section(path, name, values):
            print("Entities.ini [%s]" % name)


def write_tiles():
    """Rocks can be mined for stone now (Mine Rock), anywhere."""
    path = os.path.join(DATA, "Tiles.ini")
    for rock in ("Rock002", "Rock003"):
        if not ini.read(rock, "Use.Words", "", path):
            ini.write(rock, "Use.Words", "Mine,Examine", path)
            print("Tiles.ini [%s] Use.Words=Mine" % rock)


def write_racks():
    path = os.path.join(DATA, "ItemRacks.ini")
    craft = {"Type": "Craft", "Skill": "Construction"}
    for i, line in enumerate(CRAFT, 1):
        craft["Item%d" % i] = line
    if write_section(path, "CRAFT-Construction", craft):
        print("ItemRacks.ini [CRAFT-Construction]")
    if write_section(path, "SHOP-Homestead", {"Type": "Shop", "Buy.Rate": "1.0", "Sell.Rate": "0.5", "Specific": "1",
                                              "Item1": "Homestead_Scroll,10", "Item2": "Plank,40",
                                              "Item3": "Nails,200", "Item4": "Stone_Block,20"}):
        print("ItemRacks.ini [SHOP-Homestead]")


def write_spell():
    path = os.path.join(DATA, "Spells.ini")
    if write_section(path, "Homestead", {"Cost": "12", "Cooldown": "90", "Scroll": "Homestead_Scroll",
                                         "Effect": "Home", "Level": str(MAGIC_LEVEL), "Impact": "Teleport_Glow",
                                         "Sound": "Teleporter", "XP": "0.5"}):
        print("Spells.ini [Homestead]")


def write_skill():
    cfg = os.path.join(DATA, "Config.ini")
    skills = ini.read("Skills", "List", "", cfg)
    if "Construction" not in [s.strip() for s in skills.split(",")]:
        ini.write("Skills", "List", skills + ",Construction", cfg)
        ini.write("Skills", "Icon.Construction", SKILL_ICON, cfg)
        print("Config [Skills]: Construction")
    if not ini.read("Homestead", "Template", "", cfg):
        ini.write("Homestead", "Template", "Homestead.txt", cfg)
        ini.write("Homestead", "Arrival.X", str(ARRIVAL[0]), cfg)
        ini.write("Homestead", "Arrival.Y", str(ARRIVAL[1]), cfg)
        ini.write("Homestead", "Return.Map", SETTLER_TOWN, cfg)
        print("Config [Homestead]")


def write_buildables():
    path = os.path.join(DATA, "Buildables.ini")
    if os.path.exists(path):
        print("Data\\Buildables.ini is there already")
        return
    lines = ["; What players can build on their homesteads (dsengine/homes.py). Generated by Dev\\migrate\\"
             "build_homestead.py; edit it here.",
             "; Kind: Tile (the ground: floors, walls, doors), Decor (on the ground), Roof (a material: the pieces "
             "follow the roof's shape) or Object (an object, e.g. a workshop).",
             "; Needs: materials (\"Plank 2 Nails 4\"; 0 = none). Level and XP: the Construction skill. On: what must be "
             "under it (wall = any wall).", ""]
    for piece, v in B:
        lines.append("[%s]" % piece)
        needs = " ".join("%s %s" % (n, q) for n, q in zip(v["Needs"].split()[::2], v["Needs"].split()[1::2])
                         if q != "0")
        v = dict(v, Needs=needs)
        for k in ("Kind", "Category", "Name", "Needs", "Level", "XP", "On"):
            if v[k] != "":
                lines.append("%s=%s" % (k, v[k]))
        lines.append("")
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(lines))
    print("Made Data\\Buildables.ini (%d pieces)" % len(B))


def check_materials():
    path = os.path.join(DATA, "Entities.ini")
    missing = set()
    for _, v in B:
        for n in v["Needs"].split()[::2]:
            if not ini.section(n, path):
                missing.add(n)
    for line in CRAFT:
        for n in line.split(",")[1].split()[::2]:
            if not ini.section(n, path):
                missing.add(n)
    if missing:
        print("WARNING - materials not in Entities.ini: %s" % ", ".join(sorted(missing)))


def write_script(name, lines):
    path = os.path.join(DATA, "Scripts", name + ".txt")
    if os.path.exists(path):
        print("Data\\Scripts\\%s.txt is there already" % name)
        return
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// Generated by Dev\\migrate\\build_homestead.py\n" + "\n".join(lines) + "\n")
    print("Made Data\\Scripts\\%s.txt" % name)


def write_scripts():
    write_script("Craft Carpenters_Bench", [
        "01\t>Distance.From.Clicked.Entity\t48\t04",
        "02\tDisplay.Item.Rack\tGENERAL\tCarpenters_Bench\tCRAFT-Construction\t03",
        "03\tEnd",
        "04\tDisplay.Message\tDarkRed\tYou are too far away!",
        "05\tEnd",
    ])
    lines = [
        "// Rocks: needs a pickaxe; gives stone for building (cut it into blocks at a carpenter's bench).",
        "01	>Distance.From.Clicked.Tile	40	21",
        "02	Get.Value	CALCULATION	$Tile.under.Cursor.X	Variable.5$",
        "03	Get.Value	CALCULATION	$Tile.under.Cursor.Y	Variable.6$",
        "04	>Got.Item	Pickaxe	1	06",
        "05	Goto.Line	12",
        "06	>Got.Item	Bronze_Pickaxe	1	08",
        "07	Goto.Line	12",
        "08	>Got.Item	Steel_Pickaxe	1	10",
        "09	Goto.Line	12",
        "10	>Got.Item	Mithril_Pickaxe	1	23",
        "11	Goto.Line	12",
        "12	Display.Message	Cyan	You chip away at the rock...",
        "13	Play.Sound	Mine",
        "14	Wait	2",
        "15	Display.Message	Yellow	...and break off a lump of stone.",
        "16	Give.Item	Stone	1",
        "17	Update.Skill	Mining	+0.05",
        "18	Update.Skill	Construction	+0.02",
        "19	Change.Tile	$Variable.5,$Variable.6	Rock001	0	90",
        "20	End",
        "21	Display.Message	DarkRed	You are too far away!",
        "22	End",
        "23	Display.Message	DarkRed	You need a pickaxe to mine stone!",
        "24	End",
    ]
    write_script("Mine Rock", lines)
    say = "Display.Conversation\tSettler"
    write_script("Talk to Homestead_Settler", [
        "01\tGet.Value\tATTRIBUTE\tHomeQuest\tVariable.1$",
        "02\t>Conditional\t$Variable.1=0\t14",          # (a condition carries on if true, jumps if not)
        "03\t>Quest.Can.Start\tHomeQuest\t45",
        "04\t%s\tLooking for a place of your own? Every settler out here dreams of one.\\The homestone there can take "
        "you to land of your own, if you carry an Access Crystal. I'll give you mine if you show me you can build: bring "
        "me 10 planks and 4 stone blocks. Use my carpenter's bench to make them.\tI'll do it!\t07\tWhat's a "
        "homestone?\t12\tNot now.\t44" % say,
        "05\tEnd",
        "07\tUpdate.Attribute\tHomeQuest\t=1",
        "08\tQuest.Note\tHomeQuest\tSaw logs into planks at the settler's carpenter's bench (Construction).",
        "09\tQuest.Note\tHomeQuest\tMine stone from rocks with a pickaxe and cut it into blocks at the bench.",
        "10\tDisplay.Message\tYellow\tQuest started: A Place of Your Own.",
        "11\tEnd",
        "12\t%s\tLike the waystones, but they're bound to a hearth. Touch one with an Access Crystal and it takes you "
        "home; your friends can visit if you let them.\tI see.\t44" % say,
        "13\tEnd",
        "14\t>Conditional\t$Variable.1=1\t30",
        "15\tGoto.Line\t20",
        "20\t>Got.Item\tPlank\t10\t28",
        "21\t>Got.Item\tStone_Block\t4\t28",
        "22\tTake.Item\tPlank\t10",
        "23\tTake.Item\tStone_Block\t4",
        "24\t%s\tGood, square work! You'll do. Here: my Access Crystal. Touch any homestone with it and you'll be on "
        "your own land. Build what you like; nobody can come in unless you let them.\\Once you know a little magic I "
        "can sell you scrolls that take you home from anywhere.\tThank you!\t25" % say,
        "25\tGive.Item\tAccess_Crystal\t1",
        "26\tGive.Item\tNails\t40",
        "27\tGoto.Line\t50",
        "28\t%s\tI need 10 planks and 4 stone blocks. Logs make planks at my bench; for blocks, mine stone from rocks "
        "with a pickaxe and cut it at the bench too.\tI'll get them.\t44\tLet me use your bench.\t40" % say,
        "29\tEnd",
        "30\t%s\tHow's the homestead coming along?\tSell me something.\t38\tLet me use your bench.\t40\tI've lost my "
        "Access Crystal.\t42\tGoodbye.\t44" % say,
        "31\tEnd",
        "38\tDisplay.Item.Rack\tSPECIFIC\tSettler\tSHOP-Homestead\t44",
        "39\tEnd",
        "40\tDisplay.Item.Rack\tGENERAL\tCarpenters_Bench\tCRAFT-Construction\t44",
        "41\tEnd",
        "42\t>Got.Item\tAccess_Crystal\t1\t46",
        "43\t%s\tYou've still got it, look: in your pack.\tSo I have.\t44" % say,
        "44\tEnd",
        "45\t%s\tA homestead? Get your feet under you first: see the mainland, then come back.\tI will.\t44" % say,
        "46\tGive.Item\tAccess_Crystal\t1",
        "47\t%s\tCareless! Here's another. They're bound to you, not the crystal.\tThanks.\t44" % say,
        "48\tEnd",
        "50\tUpdate.Skill\tConstruction\t+3",
        "51\tUpdate.Attribute\tHomeQuest\t=2",
        "52\tQuest.Note.Done\tHomeQuest\t*",
        "53\tDisplay.Message\tYellow\tQuest complete! You receive the Access Crystal, 40 nails and Construction "
        "experience. Touch a homestone to go home.",
        "54\tEnd",
    ])


def write_quest():
    path = os.path.join(DATA, "Quests.ini")
    if write_section(path, "A Place of Your Own", {
            "Giver": "Settler", "Attribute": "HomeQuest",
            "Stage0": "Speak to the settler by the homestone in Ashford.",
            "Stage1": "Bring the settler 10 planks and 4 stone blocks. Make them at her carpenter's bench: planks from "
                      "logs, blocks from stone you mine from rocks with a pickaxe.",
            "Done": "2", "Marker1": "Homestead_Yard", "Requires.Quests": "Passage to the Mainland"}):
        print("Quests.ini [A Place of Your Own]")


# ---------------------------------------------------------------- the land a home starts as
def template_cells():
    rng = random.Random(1234)
    cells, decor = {}, {}
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            edge = x in (1, XT) or y in (1, YT)
            cells[(x, y)] = "Forest001" if edge else "Grass001"
    for x, y in ((2, 2), (3, 2), (2, 3), (24, 2), (23, 2), (24, 3), (2, 20), (24, 20), (24, 19)):
        cells[(x, y)] = "Forest001"
    for x in range(20, 24):                                 # a pond in the corner
        for y in range(3, 7):
            if ((x - 21.5) / 2.2) ** 2 + ((y - 4.5) / 1.9) ** 2 <= 1:
                cells[(x, y)] = "Pond001"
    for y in range(ARRIVAL[1] - 1, YT):                     # a dirt path from where you arrive
        cells[(ARRIVAL[0], y)] = "Dirt001"
    keep = {ARRIVAL, HOME_STONE, HOME_BENCH, (ARRIVAL[0], ARRIVAL[1] - 1)}
    spots = [(x, y) for y in range(3, YT - 1) for x in range(3, XT - 1)
             if cells[(x, y)] == "Grass001" and (x, y) not in keep]
    rng.shuffle(spots)
    wants = ["Tree001"] * 5 + ["Oak_Tree001"] * 2 + ["Rock002"] * 3 + ["Rock003"] * 2 + ["Herb_Patch001"] + \
            ["Berry_Bush001"] + ["Flowers001", "Flowers002", "Flowers003"] * 2
    for name in wants:
        while spots:
            x, y = spots.pop()
            if all((x + i, y + j) not in decor for i in (-1, 0, 1) for j in (-1, 0, 1)):
                decor[(x, y)] = name
                break
    return cells, decor


def write_template():
    path = os.path.join(DATA, "Homestead.txt")
    if os.path.exists(path):
        print("Data\\Homestead.txt is there already")
        return
    cells, decor = template_cells()
    rows = []
    for y in range(1, YT + 1):
        row = []
        for x in range(1, XT + 1):
            c = cells[(x, y)]
            if (x, y) in decor:
                c += "+Decor(%s)" % decor[(x, y)]
            row.append(c)
        rows.append(":".join(row))
    px = lambda t: ((t[0] - 1) * 32, (t[1] - 1) * 32)
    lines = rows + [
        "StaticObject\tHomestone\t%d\t%d" % px(HOME_STONE),
        "StaticObject\tCarpenters_Bench\t%d\t%d" % px(HOME_BENCH),
        "Id\tHome_Arrival\t%d\t%d" % ARRIVAL,
    ]
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    print("Made Data\\Homestead.txt")


# ---------------------------------------------------------------- homestones (and the settler) in the towns
def map_lines(name):
    return ini.read_text(os.path.join(ROOT, "Maps", name + ".txt")).replace("\r", "").split("\n")


def write_map(name, lines):
    while lines and lines[-1] == "":
        lines.pop()
    with open(os.path.join(ROOT, "Maps", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def taken_spots(lines):
    taken = []
    for ln in lines[YT:]:
        parts = ln.split("\t")
        if len(parts) >= 4 and parts[0] not in ("Lock", "Trigger", "Id"):
            try:
                taken.append((float(parts[2]), float(parts[3])))
            except ValueError:
                pass
    return taken


def clear_tile(lines, tx, ty):
    if not (2 <= tx < XT and 2 <= ty < YT):
        return False
    c = lines[ty - 1].split(":")[tx - 1]
    tiles = os.path.join(DATA, "Tiles.ini")
    return "+" not in c and "0" not in ini.read(c.strip(), "Walkable.Data", "1" * 49, tiles)


def clear_spot_near(lines, px, py, avoid, rings=4):
    """A clear tile near map pixel px,py, away from everything else (and avoid): its top-left pixel."""
    taken = taken_spots(lines) + list(avoid)
    tx0, ty0 = int(px // 32) + 1, int(py // 32) + 1
    best = None
    for ty in range(ty0 - rings, ty0 + rings + 1):
        for tx in range(tx0 - rings, tx0 + rings + 1):
            if (tx, ty) == (tx0, ty0) or not clear_tile(lines, tx, ty) or not clear_tile(lines, tx, ty + 1):
                continue
            x, y = (tx - 1) * 32, (ty - 1) * 32
            if any(math.hypot(x - ax, y - ay) < 44 for ax, ay in taken):
                continue
            d = math.hypot(tx - tx0, ty - ty0) + (0.3 if ty < ty0 else 0)
            if best is None or d < best[0]:
                best = (d, x, y)
    return None if best is None else best[1:]


def place_homestones():
    for name, town in TOWNS.items():
        lines = map_lines(name)
        if any(ln.split("\t")[:2] == ["StaticObject", "Homestone"] for ln in lines):
            print("%s has its homestone already" % town)
            continue
        way = next((ln.split("\t") for ln in lines if ln.split("\t")[:2] == ["StaticObject", "Waystone"]), None)
        if way is None:
            print("WARNING - no waystone in %s" % town)
            continue
        spot = clear_spot_near(lines, float(way[2]), float(way[3]), [])
        if spot is None:
            print("WARNING - no room for a homestone in %s" % town)
            continue
        lines.append("StaticObject\tHomestone\t%d\t%d" % spot)
        if name == SETTLER_TOWN:
            npc = clear_spot_near(lines, spot[0], spot[1], [spot], 5)
            bench = clear_spot_near(lines, npc[0], npc[1], [spot, npc], 3) if npc else None
            if npc and bench:
                lines.append("NPC\tSettler\t%d\t%d\tAttitude=Good Stand=1 Id=Homestead_Settler" % (npc[0], npc[1] - 8))
                lines.append("StaticObject\tCarpenters_Bench\t%d\t%d" % bench)
                lines.append("Id\tHomestead_Yard\t%d\t%d" % (npc[0] // 32 + 1, npc[1] // 32 + 1))
                print("The settler and her bench are in %s" % town)
            else:
                print("WARNING - no room for the settler in %s" % town)
        write_map(name, lines)
        print("A homestone stands in %s at %d,%d" % (town, spot[0], spot[1]))


def main():
    make_sprites()
    write_entities()
    write_tiles()
    write_racks()
    write_spell()
    write_skill()
    write_buildables()
    check_materials()
    write_scripts()
    write_quest()
    write_template()
    place_homestones()


if __name__ == "__main__":
    main()
