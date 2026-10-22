"""Farming (the multiplayer server's dsengine/farming.py). Run it again after rebuilding the world: it makes what's
missing and leaves the rest as it is.

  python -I "Dev\\migrate\\build_farming.py"

  * The Farming skill (Config [Skills]) and Data\\Crops.ini: what grows from which seed, at which level, how long it
    takes, and what it gives.
  * Tilled soil (Soil001): sow seeds in it (use the seed on the soil). It's on the farm by Ashford (the farmer's
    furrows, free for anyone: whoever sows a plot harvests it), and you can lay it on your homestead (Build: Garden).
  * Crops grow through three stages (<Crop>_Crop001-003, Tiles.ini); ripe ones can be harvested.
  * Seeds, sold by the farmer (SHOP-Farm); harvests sometimes give a seed back. New food: potatoes, onions, carrots,
    pumpkins, and what the range makes of them (CRAFT-Cooking).
"""
import math
import os
import random
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from dragonsword import ini  # noqa: E402

DATA = os.path.join(ROOT, "Data")
TILES = os.path.join(ROOT, "Sprites", "Tiles")
ENTS = os.path.join(ROOT, "Sprites", "Entities")
FARM_MAP = "3,3,0"
ALLOTMENT_ROWS = (14, 16)               # the farmer's furrows (tile rows) on the farm by Ashford
ALLOTMENT_X = range(3, 12)

# crop: (seed price, level, minutes to grow, yield, xp, leaf colour, produce colour, kind of plant)
CROPS = {
    "Potato": (2, 1, 4, "3-6", 0.15, (70, 130, 50), (176, 132, 80), "bush"),
    "Onion": (3, 4, 5, "3-6", 0.2, (96, 160, 70), (226, 214, 170), "spike"),
    "Cabbage": (3, 7, 6, "2-5", 0.25, (110, 170, 90), (150, 200, 120), "head"),
    "Wheat": (3, 10, 6, "4-8", 0.25, (150, 170, 70), (222, 190, 90), "grain"),
    "Carrot": (5, 14, 8, "3-6", 0.35, (80, 160, 60), (236, 130, 40), "feather"),
    "Herb": (8, 18, 9, "3-5", 0.4, (60, 150, 70), (90, 190, 90), "bush"),
    "Pumpkin": (12, 25, 12, "1-3", 0.6, (60, 120, 40), (232, 128, 30), "vine"),
}
NEW_PRODUCE = {
    "Potato": {"Examine.Info": "A knobbly potato. Bake it at a range.", "Stackable": "30", "Value": "3"},
    "Onion": {"Examine.Info": "An onion. It makes your eyes water.", "Stackable": "30", "Value": "3"},
    "Carrot": {"Use.Words": "Eat", "Examine.Info": "A crunchy carrot. Heals 2.", "Stackable": "30", "Value": "4",
               "Food.Value": "2"},
    "Pumpkin": {"Examine.Info": "A fat orange pumpkin. A pie in waiting.", "Stackable": "10", "Value": "12"},
}
FOODS = {   # cooked at a range: name: (ingredients, xp, level, heals, value, info)
    "Baked_Potato": ("Potato 1", 0.1, 2, 4, 6, "A baked potato, steaming. Heals 4."),
    "Vegetable_Stew": ("Potato 1 Carrot 1 Onion 1", 0.4, 12, 12, 22, "A thick vegetable stew. Heals 12."),
    "Pumpkin_Pie": ("Flour 1 Pumpkin 1", 0.5, 18, 15, 30, "A spiced pumpkin pie. Heals 15."),
}


def write_section(path, name, values):
    if ini.section(name, path):
        return False
    for k, v in values.items():
        ini.write(name, k, v, path)
    return True


# ---------------------------------------------------------------- sprites
def save(img, folder, name):
    path = os.path.join(folder, name + ".png")
    if os.path.exists(path):
        return
    pygame.image.save(img, path)
    print("Made %s.png" % os.path.relpath(path, ROOT))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def plant(surf, kind, x, y, stage, leaf, crop, rng):
    """One plant with its base at x,y; stage 1 a sprout, 2 growing, 3 ripe."""
    s = (0.45, 0.75, 1.0)[stage - 1]
    dark = shade(leaf, 0.7)
    if kind == "grain":
        for k in range(3 + stage):
            dx = rng.randint(-3, 3)
            h = int((5 + 6 * s) * rng.uniform(0.85, 1.1))
            pygame.draw.line(surf, leaf if stage < 3 else shade(crop, 0.85), (x + dx, y), (x + dx, y - h))
            if stage == 3:
                pygame.draw.ellipse(surf, crop, (x + dx - 1, y - h - 3, 3, 5))
        return
    if kind in ("spike", "feather"):
        for k in range(2 + stage):
            dx = rng.randint(-3, 3)
            h = int((4 + 6 * s) * rng.uniform(0.8, 1.1))
            col = leaf if kind == "spike" else shade(leaf, rng.uniform(0.85, 1.15))
            pygame.draw.line(surf, col, (x, y), (x + dx, y - h))
            if kind == "feather":
                pygame.draw.circle(surf, col, (x + dx, y - h), 1)
        if stage == 3:
            if kind == "spike":
                pygame.draw.ellipse(surf, crop, (x - 3, y - 2, 6, 4))
            else:
                pygame.draw.polygon(surf, crop, [(x - 2, y - 1), (x + 2, y - 1), (x, y + 2)])
        return
    if kind == "head":
        r = int(2 + 3 * s)
        pygame.draw.circle(surf, dark, (x, y - r), r + 1)
        pygame.draw.circle(surf, leaf if stage < 3 else crop, (x, y - r), r)
        pygame.draw.arc(surf, dark, (x - r, y - 2 * r, 2 * r, 2 * r), 0.5, 2.6)
        return
    if kind == "vine":
        r = int(2 + 3 * s)
        for k in range(3):
            pygame.draw.circle(surf, shade(leaf, rng.uniform(0.85, 1.1)), (x + rng.randint(-4, 4), y - rng.randint(1, 4)), r - 1)
        if stage >= 2:
            pygame.draw.circle(surf, crop if stage == 3 else (120, 160, 60), (x + 1, y - 2), 2 + stage)
            if stage == 3:
                pygame.draw.line(surf, shade(crop, 0.6), (x + 1, y - 6), (x + 1, y + 2))
        return
    r = int(2 + 3 * s)                                  # a bush
    for k in range(3):
        pygame.draw.circle(surf, shade(leaf, rng.uniform(0.8, 1.15)), (x + rng.randint(-3, 3), y - r - rng.randint(0, 2)), r)
    if stage == 3:
        for k in range(2):
            pygame.draw.circle(surf, crop, (x + rng.randint(-3, 3), y - rng.randint(1, 4)), 2)


def crop_tile(name, stage):
    price, level, minutes, yld, xp, leaf, crop, kind = CROPS[name]
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    rng = random.Random(sum(map(ord, name)) * 10 + stage)
    for row in (13, 27):
        for col in (6, 16, 26):
            plant(surf, kind, col + rng.randint(-1, 1), row, stage, leaf, crop, rng)
    return surf


def seed_pouch(name):
    crop = CROPS[name][6]
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (176, 146, 96), (7, 11, 18, 17))
    pygame.draw.polygon(surf, (176, 146, 96), [(11, 13), (21, 13), (19, 7), (13, 7)])
    pygame.draw.line(surf, (110, 80, 50), (12, 12), (20, 12), 2)
    pygame.draw.ellipse(surf, (110, 84, 54), (7, 11, 18, 17), 1)
    pygame.draw.circle(surf, crop, (16, 20), 4)
    pygame.draw.circle(surf, shade(crop, 0.6), (16, 20), 4, 1)
    return surf


def produce(name):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    col = {"Potato": (176, 132, 80), "Onion": (214, 180, 120), "Carrot": (236, 130, 40), "Pumpkin": (232, 128, 30)}[name]
    if name == "Potato":
        pygame.draw.ellipse(surf, col, (7, 11, 18, 13))
        pygame.draw.ellipse(surf, shade(col, 0.65), (7, 11, 18, 13), 1)
        for p in ((12, 15), (18, 17), (15, 20)):
            pygame.draw.circle(surf, shade(col, 0.7), p, 1)
    elif name == "Onion":
        pygame.draw.circle(surf, col, (16, 19), 8)
        pygame.draw.circle(surf, shade(col, 0.7), (16, 19), 8, 1)
        pygame.draw.polygon(surf, (120, 170, 80), [(14, 12), (18, 12), (16, 4)])
        pygame.draw.arc(surf, shade(col, 0.8), (11, 12, 10, 14), 1.2, 1.9)
    elif name == "Carrot":
        pygame.draw.polygon(surf, col, [(8, 10), (14, 8), (25, 25)])
        pygame.draw.polygon(surf, shade(col, 0.7), [(8, 10), (14, 8), (25, 25)], 1)
        for d in (-3, 0, 3):
            pygame.draw.line(surf, (80, 160, 60), (10, 9), (6 + d, 3))
    else:
        pygame.draw.ellipse(surf, col, (5, 10, 22, 16))
        for x in (11, 16, 21):
            pygame.draw.line(surf, shade(col, 0.7), (x, 11), (x, 24))
        pygame.draw.rect(surf, (90, 110, 50), (15, 6, 3, 5))
    return surf


def food(name):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    if name == "Baked_Potato":
        pygame.draw.ellipse(surf, (150, 104, 60), (6, 11, 20, 14))
        pygame.draw.ellipse(surf, (250, 236, 170), (10, 13, 12, 6))
        pygame.draw.ellipse(surf, (90, 60, 30), (6, 11, 20, 14), 1)
    elif name == "Vegetable_Stew":
        pygame.draw.ellipse(surf, (110, 80, 50), (5, 13, 22, 13))
        pygame.draw.ellipse(surf, (176, 96, 40), (7, 14, 18, 8))
        for c, p in (((236, 130, 40), (12, 17)), ((226, 214, 170), (18, 16)), ((176, 132, 80), (15, 19))):
            pygame.draw.circle(surf, c, p, 2)
        for x in (12, 17, 22):
            pygame.draw.arc(surf, (230, 230, 230), (x - 2, 5, 4, 7), 0, 3.1)
    else:
        pygame.draw.ellipse(surf, (200, 160, 100), (4, 12, 24, 14))
        pygame.draw.ellipse(surf, (214, 120, 40), (7, 13, 18, 9))
        pygame.draw.ellipse(surf, (140, 100, 60), (4, 12, 24, 14), 1)
        pygame.draw.circle(surf, (250, 240, 220), (16, 16), 2)
    return surf


def make_sprites():
    pygame.init()
    soil = os.path.join(TILES, "Soil001.png")
    if not os.path.exists(soil):
        shutil.copy(os.path.join(TILES, "Field001.png"), soil)
        print("Made Sprites\\Tiles\\Soil001.png")
    for name in CROPS:
        for stage in (1, 2, 3):
            save(crop_tile(name, stage), TILES, "%s_Crop%03d" % (name, stage))
        save(seed_pouch(name), ENTS, name + "_Seed")
    for name in NEW_PRODUCE:
        save(produce(name), ENTS, name)
    for name in FOODS:
        save(food(name), ENTS, name)


# ---------------------------------------------------------------- data
def write_data():
    tiles = os.path.join(DATA, "Tiles.ini")
    if write_section(tiles, "Soil001", {"Walkable.Data": "1" * 49, "Show.Name": "1", "Use.Words": "Examine",
                                        "Examine.Info": "Tilled soil. Use seeds on it to sow them.",
                                        "Line.of.Sight": "1", "Walk.Speed": "0.85", "Blend": "4",
                                        "Blend.Texture": "Marsh001"}):
        print("Tiles.ini [Soil001]")
    words = {1: "sprouting", 2: "growing", 3: "ripe"}
    for name in CROPS:
        for stage in (1, 2, 3):
            write_section(tiles, "%s_Crop%03d" % (name, stage), {
                "Walkable.Data": "1" * 49, "Show.Name": "1", "Use.Words": "Harvest,Examine" if stage == 3 else "Examine",
                "Examine.Info": "%s, %s." % (name.lower() if name != "Herb" else "herbs", words[stage]),
                "Line.of.Sight": "1", "Walk.Speed": "0.8", "Layer": "Decor", "Sway": "1.0"})
    ents = os.path.join(DATA, "Entities.ini")
    for name, (price, level, *_rest) in CROPS.items():
        write_section(ents, name + "_Seed", {
            "Type": "MapItem", "Stackable": "50", "Value": str(price), "Crop": name,
            "Examine.Info": "%s seeds. Use them on tilled soil to sow them (Farming %d)." %
                            (name if name != "Herb" else "Herb", level)})
    for name, values in NEW_PRODUCE.items():
        write_section(ents, name, dict({"Type": "MapItem"}, **values))
    for name, (ingredients, xp, level, heals, value, info) in FOODS.items():
        write_section(ents, name, {"Type": "MapItem", "Use.Words": "Eat", "Examine.Info": info, "Stackable": "1",
                                   "Value": str(value), "Food.Value": str(heals)})
    crops = os.path.join(DATA, "Crops.ini")
    if not os.path.exists(crops):
        lines = ["; What grows on tilled soil (dsengine/farming.py). Generated by Dev\\migrate\\build_farming.py; edit it "
                 "here.", "; Seed: the item you sow. Gives: what a harvest gives (Yield of them, +1 every 10 Farming "
                 "levels). Minutes: from sowing to ripe.", "; Seed.Back: the chance (percent) a harvest gives a seed back. "
                 "Wither: minutes a ripe crop waits on the public allotment before it's gone.", ""]
        for name, (price, level, minutes, yld, xp, *_rest) in CROPS.items():
            lines += ["[%s]" % name, "Seed=%s_Seed" % name, "Gives=%s" % name, "Level=%d" % level,
                      "Minutes=%d" % minutes, "Yield=%s" % yld, "XP=%s" % xp, "Seed.Back=35", "Wither=60", ""]
        with open(crops, "w", encoding="cp1252", newline="\r\n") as f:
            f.write("\n".join(lines))
        print("Made Data\\Crops.ini")
    cfg = os.path.join(DATA, "Config.ini")
    skills = ini.read("Skills", "List", "", cfg)
    if "Farming" not in [s.strip() for s in skills.split(",")]:
        ini.write("Skills", "List", skills + ",Farming", cfg)
        ini.write("Skills", "Icon.Farming", "Potato", cfg)
        print("Config [Skills]: Farming")
    racks = os.path.join(DATA, "ItemRacks.ini")
    shop = dict(ini.section("SHOP-Farm", racks))
    have = {v.split(",")[0] for k, v in shop.items() if k.startswith("Item")}
    n = sum(1 for k in shop if k.startswith("Item"))
    for name in CROPS:
        if name + "_Seed" not in have:
            n += 1
            ini.write("SHOP-Farm", "Item%d" % n, "%s_Seed,30" % name, racks)
    for name in ("Potato", "Onion", "Carrot"):
        if name not in have:
            n += 1
            ini.write("SHOP-Farm", "Item%d" % n, "%s,10" % name, racks)
    cook = dict(ini.section("CRAFT-Cooking", racks))
    have = {v.split(",")[0] for k, v in cook.items() if k.startswith("Item")}
    n = sum(1 for k in cook if k.startswith("Item"))
    for name, (ingredients, xp, level, *_rest) in FOODS.items():
        if name not in have:
            n += 1
            ini.write("CRAFT-Cooking", "Item%d" % n, "%s,%s,%s,%d" % (name, ingredients, xp, level), racks)
    gathering = os.path.join(DATA, "Gathering.ini")
    for name, (price, level, minutes, yld, xp, *_rest) in CROPS.items():
        write_section(gathering, "%s (farming)" % name, {
            "Gives": name, "Source": "%s_Crop003" % name, "Verb": "Harvest", "Tool": name + "_Seed",
            "Skill": "Farming", "Level": str(level), "XP": str(xp),
            "Where": "Sow the seeds in tilled soil: the farmer's furrows by Ashford, or your homestead"})
    build = os.path.join(DATA, "Buildables.ini")
    if os.path.exists(build) and not ini.section("Soil001", build):
        for k, v in (("Kind", "Tile"), ("Category", "Garden"), ("Name", "Tilled soil (sow seeds here)"),
                     ("Level", "1"), ("XP", "0.02")):
            ini.write("Soil001", k, v, build)
        print("Buildables.ini [Soil001]")


def write_farm():
    """The farmer's furrows become tilled soil anyone may sow (the cabbages lying on them go)."""
    path = os.path.join(ROOT, "Maps", FARM_MAP + ".txt")
    lines = ini.read_text(path).replace("\r", "").split("\n")
    if "Soil001" in "\n".join(lines[:21]):
        print("The farm by Ashford has its allotment already")
        return
    for ty in ALLOTMENT_ROWS:
        row = lines[ty - 1].split(":")
        for tx in ALLOTMENT_X:
            if row[tx - 1].strip() == "Dirt001":
                row[tx - 1] = "Soil001"
        lines[ty - 1] = ":".join(row)
    keep = lines[:21]
    for ln in lines[21:]:
        parts = ln.split("\t")
        if len(parts) >= 4 and parts[0] == "MapItem" and parts[1] == "Cabbage":
            ty = int(float(parts[3]) // 32) + 1
            if ty in ALLOTMENT_ROWS:
                continue
        keep.append(ln)
    while keep and keep[-1] == "":
        keep.pop()
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(keep) + "\n")
    print("The farmer's furrows (Maps\\%s.txt) are tilled soil now" % FARM_MAP)
    script = os.path.join(DATA, "Scripts", "Talk to Farmer.txt")
    text = ini.read_text(script)
    if "furrows" not in text:
        text = text.replace("Help yourself to a cabbage or two, there's plenty.",
                            "Help yourself to a cabbage or two, there's plenty. And the tilled furrows by the "
                            "cabbages are free for anyone to sow: buy seeds from me, use them on the soil, and "
                            "what you sow is yours to harvest.")
        with open(script, "w", encoding="cp1252", newline="") as f:
            f.write(text)
        print("The farmer tells you about the furrows")


def write_minimap_colours():
    """Dev\\Minimap Colours.txt: a colour for each new tile (its picture over the soil, averaged)."""
    path = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
    raw = open(path, "rb").read().decode("cp1252")
    nl = "\r\n" if "\r\n" in raw else "\n"
    have = {ln.split("\t")[0] for ln in raw.splitlines() if ln.strip()}
    soil = pygame.image.load(os.path.join(TILES, "Soil001.png"))
    add = []
    for name in ["Soil001"] + ["%s_Crop%03d" % (c, n) for c in CROPS for n in (1, 2, 3)]:
        if name in have or not os.path.exists(os.path.join(TILES, name + ".png")):
            continue
        t = soil.copy()
        t.blit(pygame.image.load(os.path.join(TILES, name + ".png")), (0, 0))
        r, g, b, _ = pygame.transform.smoothscale(t, (1, 1)).get_at((0, 0))
        add.append("%s\t%d %d %d" % (name, r, g, b))
    if add:
        with open(path, "wb") as f:
            f.write((raw.rstrip("\r\n") + nl + nl.join(add) + nl).encode("cp1252"))
        print("Minimap colours for %d tiles" % len(add))


def main():
    make_sprites()
    write_data()
    write_farm()
    write_minimap_colours()


if __name__ == "__main__":
    main()
