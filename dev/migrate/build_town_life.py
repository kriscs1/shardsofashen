"""Town life: the market boards, the vendors at Ashford's stalls, the tavern (its games), digging, and monster waves.
Run it again after rebuilding the world: it makes what's missing and leaves the rest as it is.

  python -I "dev\\migrate\\build_town_life.py"

  * Market boards (Market_Board, dsengine/market.py): the global marketplace. Anyone lists things from their pack at
    their own price, and everyone sees everyone's listings at any board: in Ashford's market and by every waystone.
  * The stalls by Ashford's south road are the vendors' now (decoration): a trader behind each, with a shop.
  * The Green Dragon, Ashford's beer garden (behind the houses, north): the innkeeper (Id=Innkeeper: Three Cups, High
    or Low, ale) and dice tables (Dice_Table: a round of Dragon Dice for everyone at the table). dsengine/tavern.py.
  * Digging (dsengine/digging.py, data\\Digging.ini): a spade digs anywhere on open ground, with a small chance of
    finding something. It leaves a hole that grasses over.
  * Monster waves (dsengine/waves.py, data\\Waves.ini): attacks of several waves at once. A goblin raid on Ashford
    now and then (when enough players are about), and the farmer's goblins (a quest-style one, started by a script:
    Start.Wave Farm_Raid).
"""
import math
import os
import random
import struct
import sys
import wave as wavefile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from dragonsword import ini  # noqa: E402

DATA = os.path.join(ROOT, "data")
ENTS = os.path.join(ROOT, "sprites", "Entities")
TILES = os.path.join(ROOT, "sprites", "Tiles")
XT, YT = 25, 21
ASHFORD = "2,3,0"
TOWNS = {"2,3,0": "Ashford", "4,8,0": "Highwatch", "1,10,0": "Dunerest", "7,6,0": "Thornwick", "7,4,0": "Emberwatch"}
TAVERN_ROW = 5                                  # Ashford: the open strip behind the houses
VENDORS = [   # (NPC sprite, shop, name, what they say, [(item, stock)])
    ("Villager", "SHOP-Market_Greengrocer", "Greengrocer", "Fresh from the farms! Cabbages, potatoes, onions, berries.",
     [("Cabbage", 20), ("Potato", 20), ("Onion", 20), ("Carrot", 15), ("Berries", 15)]),
    ("Shepherd", "SHOP-Market_Fishmonger", "Fishmonger", "Caught this morning, every one of them.",
     [("Raw_Trout", 15), ("Raw_Salmon", 10), ("Cooked_Trout", 10), ("Bait", 50)]),
    ("Woman", "SHOP-Market_Weaver", "Weaver", "Wool, leather and good stout gloves.",
     [("Wool", 20), ("Ball_of_Wool", 15), ("Leather", 10), ("Leather_Gloves", 3)]),
    ("Merchant", "SHOP-Market_Tinker", "Tinker", "Pots, pails and tools: a bit of everything for the road.",
     [("Spade", 5), ("Bucket", 10), ("Empty_Vial", 20), ("Glass", 10), ("Fishing_Rod", 3)]),
    ("Man", "SHOP-Market_Butcher", "Butcher", "Meat for the pot! And eggs, while they last.",
     [("Raw_Meat", 15), ("Meat_Pie", 6), ("Egg", 20)]),
]


def write_section(path, name, values, quiet=False):
    if ini.section(name, path):
        return False
    for k, v in values.items():
        ini.write(name, k, v, path)
    if not quiet:
        print("%s [%s]" % (os.path.basename(path), name))
    return True


def has_item(name):
    return bool(ini.section(name, os.path.join(DATA, "Entities.ini")))


# ---------------------------------------------------------------- sprites
def save(img, folder, name):
    path = os.path.join(folder, name + ".png")
    if os.path.exists(path):
        return
    pygame.image.save(img, path)
    print("Made %s" % os.path.relpath(path, ROOT))


def market_board():
    """A notice board on two legs, papers pinned to it and a coin purse on top: 32 x 48."""
    s = pygame.Surface((32, 48), pygame.SRCALPHA)
    wood, dark = (126, 86, 50), (72, 48, 28)
    for x in (5, 25):
        pygame.draw.rect(s, wood, (x, 14, 3, 34))
        pygame.draw.rect(s, dark, (x, 14, 3, 34), 1)
    pygame.draw.rect(s, (150, 104, 62), (2, 12, 28, 24))
    pygame.draw.rect(s, dark, (2, 12, 28, 24), 2)
    rng = random.Random(5)
    for x, y in ((5, 15), (16, 15), (6, 25), (17, 25)):          # the notices
        pygame.draw.rect(s, (240, 232, 206), (x, y, 9, 8))
        for k in range(3):
            pygame.draw.line(s, (120, 110, 96), (x + 1, y + 2 + 2 * k), (x + 2 + rng.randint(3, 6), y + 2 + 2 * k))
        pygame.draw.circle(s, (200, 40, 40), (x + 4, y), 1)
    pygame.draw.polygon(s, (140, 92, 52), [(1, 12), (16, 3), (31, 12)])     # the little roof
    pygame.draw.polygon(s, dark, [(1, 12), (16, 3), (31, 12)], 1)
    pygame.draw.circle(s, (232, 196, 70), (16, 8), 3)                     # a gold coin on the roof
    pygame.draw.circle(s, (150, 110, 30), (16, 8), 3, 1)
    return s


def dice_table():
    """A round table with dice and a cup on it: 32 x 32."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (70, 46, 28), (2, 8, 28, 18))
    pygame.draw.ellipse(s, (138, 94, 54), (2, 6, 28, 18))
    pygame.draw.ellipse(s, (84, 56, 32), (2, 6, 28, 18), 1)
    pygame.draw.rect(s, (84, 56, 32), (14, 22, 4, 9))
    for x, y in ((9, 11), (15, 14)):                             # two dice
        pygame.draw.rect(s, (244, 240, 230), (x, y, 5, 5))
        pygame.draw.rect(s, (60, 60, 60), (x, y, 5, 5), 1)
        pygame.draw.rect(s, (30, 30, 30), (x + 2, y + 2, 1, 1))
    pygame.draw.rect(s, (110, 60, 30), (20, 8, 5, 7))             # the dice cup
    pygame.draw.rect(s, (60, 32, 16), (20, 8, 5, 7), 1)
    return s


def ale():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (150, 104, 60), (9, 10, 13, 16))         # a wooden tankard
    for x in (12, 16, 20):
        pygame.draw.line(s, (110, 74, 40), (x, 10), (x, 25))
    pygame.draw.rect(s, (90, 60, 30), (9, 10, 13, 16), 1)
    pygame.draw.arc(s, (90, 60, 30), (18, 13, 8, 10), -1.6, 1.6, 2)
    pygame.draw.ellipse(s, (250, 246, 230), (8, 6, 15, 7))       # the froth
    return s


def hole():
    """A dug hole, a decor tile (see-through round it): 32 x 32."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (96, 70, 44), (5, 9, 22, 15))
    pygame.draw.ellipse(s, (52, 36, 22), (8, 11, 16, 10))
    for x, y in ((4, 20), (25, 13), (22, 23), (9, 8)):           # the spoil round it
        pygame.draw.circle(s, (120, 88, 56), (x, y), 2)
    return s


def make_sprites():
    pygame.init()
    save(market_board(), ENTS, "Market_Board")
    save(dice_table(), ENTS, "Dice_Table")
    save(ale(), ENTS, "Ale")
    save(hole(), TILES, "Dug_Hole001")


def make_horn():
    """sounds\\Horn.wav: a raid horn, two long low blasts."""
    path = os.path.join(ROOT, "sounds", "Horn.wav")
    if os.path.exists(path):
        return
    rate = 22050
    out = []
    for start, length, f in ((0.0, 0.7, 147), (0.85, 1.1, 165)):
        while len(out) < int(start * rate):
            out.append(0.0)
        for i in range(int(length * rate)):
            t = i / rate
            env = min(1, t / 0.08) * min(1, (length - t) / 0.25)
            v = sum(math.sin(2 * math.pi * f * h * t) / h for h in (1, 2, 3, 4, 5)) * env
            out.append(v * (1 + 0.04 * math.sin(2 * math.pi * 5 * t)))
    peak = max(abs(v) for v in out)
    with wavefile.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(v / peak * 0.6 * 32767)) for v in out))
    print("Made sounds\\Horn.wav")


# ---------------------------------------------------------------- data
def write_data():
    ents = os.path.join(DATA, "Entities.ini")
    write_section(ents, "Market_Board", {"Type": "StaticObject", "Use.Words": "Trade,Examine",
                                         "Examine.Info": "The market board: everyone's goods for sale, from all over. "
                                                         "Put your own up at your price."})
    write_section(ents, "Dice_Table", {"Type": "StaticObject", "Use.Words": "Play,Examine",
                                       "Examine.Info": "A dice table. Dragon Dice: everyone at the table puts in a "
                                                       "stake, and the highest roll takes the lot."})
    write_section(ents, "Ale", {"Type": "MapItem", "Use.Words": "Drink,Eat", "Examine.Info": "A tankard of ale. Heals 2.",
                                "Stackable": "1", "Value": "3", "Food.Value": "2"})
    for stall in ("Market_Stall", "Market_Stall_Open"):           # (the stalls are the vendors' now)
        ini.write(stall, "Use.Words", "Examine", ents)
        ini.write(stall, "Examine.Info", "A market stall. (Talk to the trader behind it.)", ents)
    spade = ini.read("Spade", "Use.Words", "", ents)
    if "Dig" not in spade:
        ini.write("Spade", "Use.Words", "Dig" + ("," + spade if spade else ""), ents)
        ini.write("Spade", "Examine.Info", "A sturdy spade. Dig with it (sand, or anywhere on open ground: you might "
                                           "turn something up).", ents)
        print("Entities.ini [Spade] Use.Words=Dig")
    tiles = os.path.join(DATA, "Tiles.ini")
    write_section(tiles, "Dug_Hole001", {"Walkable.Data": "1" * 49, "Show.Name": "1", "Use.Words": "",
                                         "Examine.Info": "A freshly dug hole. The grass will grow back over it.",
                                         "Line.of.Sight": "1", "Layer": "Decor"})
    racks = os.path.join(DATA, "ItemRacks.ini")
    for sprite, rack, name, words, stock in VENDORS:
        items = {"Type": "Shop", "Buy.Rate": "1.15", "Sell.Rate": "0.6", "Specific": "1"}
        for i, (item, n) in enumerate([s for s in stock if has_item(s[0])], 1):
            items["Item%d" % i] = "%s,%d" % (item, n)
        write_section(racks, rack, items)
    write_section(racks, "SHOP-Tavern", {"Type": "Shop", "Buy.Rate": "1.0", "Sell.Rate": "0.5", "Specific": "1",
                                         "Item1": "Ale,30", "Item2": "Bread,10", "Item3": "Meat_Pie,6"})
    shop = dict(ini.section("SHOP-Ashford", racks))
    if not any(v.split(",")[0] == "Spade" for k, v in shop.items() if k.startswith("Item")):
        n = sum(1 for k in shop if k.startswith("Item")) + 1
        ini.write("SHOP-Ashford", "Item%d" % n, "Spade,5", racks)
    dig = os.path.join(DATA, "Digging.ini")
    if not os.path.exists(dig):
        finds = [("Gold_Coin(s)", "1-8", 40), ("Stone", "1", 14), ("Bones", "1", 10), ("Iron_Ore", "1", 7),
                 ("Copper_Ore", "1", 7), ("Coal", "1", 6), ("Potato_Seed", "1-2", 6), ("Onion_Seed", "1-2", 5),
                 ("Sapphire", "1", 2), ("Emerald", "1", 2), ("Ruby", "1", 1)]
        lines = ["; Digging with a spade (dsengine/digging.py). Generated by dev\\migrate\\build_town_life.py; edit it here.",
                 "; Chance: in how many digs out of 100 something turns up. Ground: the tiles (without their number)",
                 "; you can dig in. Regrow: seconds before a dug hole has grassed over (and that spot can be dug again).",
                 "; [Finds]: item=how many,weight - the heavier the weight, the likelier that find.", "",
                 "[Digging]", "Chance=7", "Ground=Grass,Dirt,Sand,Field,Soil,Meadow,Marsh,Snow,Desert,Moss,Mud",
                 "Regrow=600", "Seconds=2", "", "[Finds]"]
        lines += ["%s=%s,%d" % (n, q, w) for n, q, w in finds if has_item(n)]
        with open(dig, "w", encoding="cp1252", newline="\r\n") as f:
            f.write("\n".join(lines) + "\n")
        print("Made data\\Digging.ini")
    waves = os.path.join(DATA, "Waves.ini")
    if not os.path.exists(waves):
        lines = [
            "; Monster waves: several monsters attacking at once, wave after wave (dsengine/waves.py). Generated by",
            "; dev\\migrate\\build_town_life.py; edit it here.",
            "; Map: where. Centre: a named place (or tile X,Y) they march on and the defenders hold.",
            "; Waves: one per ';', each Monster*count (Entities.ini NPCs), e.g. Goblin*3,Goblin_Archer*1.",
            "; Gap: seconds between a wave beaten and the next. Minutes: how long the defenders have before it fails.",
            "; Random.Every: about how many minutes between surprise attacks (0 = only when a script starts it:",
            ";   Start.Wave <name>). Random.Players: how many must be playing for a surprise one.",
            "; Gold.Per.Kill: for each raider killed, to whoever killed it. Reward.Gold / Reward.Items: for everyone who",
            ";   held out to the end (Items: \"Super_Potion 1 Ale 2\"). Reward.XP: Strength and Defence experience.",
            "; On.Win.Script / On.Lose.Script: a script run for each defender at the end (a quest's next step).",
            "", "[Ashford_Raid]", "Name=Goblin raid on Ashford", "Map=2,3,0", "Centre=Ashford_Market",
            "Waves=Goblin*3;Goblin*4,Goblin_Archer*1;Hobgoblin*2,Goblin*3,Goblin_Shaman*1", "Gap=12", "Minutes=8",
            "Random.Every=120", "Random.Players=2", "Gold.Per.Kill=4", "Reward.Gold=60", "Reward.Items=Super_Potion 1",
            "Reward.XP=1",
            "Start.Message=A horn sounds from the woods: goblins are attacking Ashford! Defend the market square!",
            "Win.Message=The goblins flee into the trees. Ashford is safe - thanks to its defenders!",
            "Lose.Message=The goblins loot what they can and slip away into the woods.", "",
            "[Farm_Raid]", "Name=Goblins at the farm", "Map=3,3,0", "Centre=Farmlands_Crossroads",
            "Waves=Goblin*2;Goblin*3;Goblin*2,Goblin_Archer*2", "Gap=10", "Minutes=6", "Random.Every=0",
            "Gold.Per.Kill=3", "Reward.Gold=40", "Reward.Items=Egg 3", "Reward.XP=0.5",
            "Start.Message=Here they come - goblins, out of the hedges! Keep them off the hen house!",
            "Win.Message=The last goblin bolts for its camp. The farmer's eggs are safe!",
            "Lose.Message=The goblins make off with a sack of eggs.", "On.Win.Script=Farm Raid Won", ""]
        with open(waves, "w", encoding="cp1252", newline="\r\n") as f:
            f.write("\n".join(lines) + "\n")
        print("Made data\\Waves.ini")


def write_script(name, lines):
    path = os.path.join(DATA, "Scripts", name + ".txt")
    if os.path.exists(path):
        return
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// Generated by dev\\migrate\\build_town_life.py\n" + "\n".join(lines) + "\n")
    print("Made data\\Scripts\\%s.txt" % name)


def write_scripts():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import story_kit as K
    if K.new_mainland():
        return                                         # (Southport's old vendors: the new markets have their own)
    for n, (sprite, rack, name, words, stock) in enumerate(VENDORS, 1):
        write_script("Talk to Market_Vendor_%d" % n, [
            "01\tDisplay.Conversation\t%s\t%s\\Want to sell your own things? Use the market board: everyone's goods, "
            "at their prices.\tWhat have you got?\t02\tGoodbye.\t04" % (sprite, words),
            "02\tDisplay.Item.Rack\tSPECIFIC\t%s\t%s\t04" % (sprite, rack),
            "03\tEnd",
            "04\tEnd",
        ])
    write_script("Farm Raid Won", [
        "01\tUpdate.Attribute\tFarmRaidsBeaten\t+1",
        "02\tDisplay.Message\tYellow\tThe farmer waves his hat at you: \"Come back any time those goblins do!\"",
        "03\tEnd",
    ])
    farmer = os.path.join(DATA, "Scripts", "Talk to Farmer.txt")
    text = ini.read_text(farmer)
    if "Start.Wave" not in text:
        lines = text.replace("\r", "").rstrip("\n").split("\n")
        out = []
        for ln in lines:
            if ln.startswith("04\tDisplay.Conversation\tFarmer"):
                ln = ln.rstrip() + "\tThey're here now? I'll fight them off!\t06"
            out.append(ln)
        out += ["06\tDisplay.Message\tYellow\tThe farmer points at the hedges: \"There! Here they come!\"",
                "07\tStart.Wave\tFarm_Raid", "08\tEnd"]
        with open(farmer, "w", encoding="cp1252", newline="") as f:
            f.write("\r\n".join(out) + "\r\n")
        print("The farmer can call his goblin raid (Start.Wave Farm_Raid)")


# ---------------------------------------------------------------- the maps
TILES_INI = os.path.join(DATA, "Tiles.ini")


def map_lines(name):
    return ini.read_text(os.path.join(ROOT, "maps", name + ".txt")).replace("\r", "").split("\n")


def write_map(name, lines):
    while lines and lines[-1] == "":
        lines.pop()
    with open(os.path.join(ROOT, "maps", name + ".txt"), "w", encoding="cp1252", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def cell(lines, x, y):
    return lines[y - 1].split(":")[x - 1].strip() if 1 <= x <= XT and 1 <= y <= YT else ""


def clear(lines, x, y, taken):
    if not (2 <= x <= XT - 1 and 2 <= y <= YT - 1):
        return False
    c = cell(lines, x, y)
    t = c.split("+")[0]
    if "+" in c or t.startswith("Door") or "0" in ini.read(t, "Walkable.Data", "1" * 49, TILES_INI):
        return False
    return all(math.hypot((x - 1) * 32 - ax, (y - 1) * 32 - ay) > 30 for ax, ay in taken)


def taken_spots(lines):
    out = []
    for ln in lines[YT:]:
        p = ln.split("\t")
        if len(p) >= 4 and p[0] not in ("Lock", "Trigger", "Id"):
            try:
                out.append((float(p[2]), float(p[3]) + (16 if p[1].startswith(("Sign_", "Market_", "Dice_")) else 0)))
            except ValueError:
                pass
    return out


def stalls_to_vendors():
    lines = map_lines(ASHFORD)
    if any("Id=Market_Vendor_" in ln for ln in lines[YT:]):
        print("Ashford's stalls have their vendors already")
        return
    out, n = lines[:YT], 0
    for ln in lines[YT:]:
        p = ln.split("\t")
        if len(p) >= 4 and p[0] == "StaticObject" and p[1] in ("Market_Stall", "Market_Stall_Open"):
            out.append("StaticObject\tMarket_Stall_Open\t%s\t%s" % (p[2], p[3]))       # (no Id: decoration)
            if n < len(VENDORS):              # (inside the stall, behind its counter: not on the road)
                n += 1
                sprite = VENDORS[n - 1][0]
                out.append("NPC\t%s\t%d\t%d\tAttitude=Good Stand=1 Id=Market_Vendor_%d" %
                           (sprite, int(float(p[2])), int(float(p[3])) + 4, n))
            continue
        out.append(ln)
    write_map(ASHFORD, out)
    print("Ashford's stalls: %d vendors behind them" % n)


def place_near(lines, px, py, avoid, rings=4, row=None):
    taken = taken_spots(lines) + list(avoid)
    tx0, ty0 = int(px // 32) + 1, int(py // 32) + 1
    best = None
    for ty in ([row] if row else range(ty0 - rings, ty0 + rings + 1)):
        for tx in range(tx0 - rings, tx0 + rings + 1):
            if not clear(lines, tx, ty, taken):
                continue
            d = math.hypot(tx - tx0, ty - ty0)
            if best is None or d < best[0]:
                best = (d, tx, ty)
    return best[1:] if best else None


def place_boards():
    for name, town in TOWNS.items():
        lines = map_lines(name)
        if any(ln.split("\t")[:2] == ["StaticObject", "Market_Board"] for ln in lines[YT:]):
            continue
        anchor = next((ln.split("\t") for ln in lines[YT:] if ln.split("\t")[:2] == ["StaticObject", "Waystone"]), None)
        if name == ASHFORD:                                     # (Ashford's: at the market, by its sign)
            anchor = next((ln.split("\t") for ln in lines[YT:] if ln.split("\t")[:2] == ["StaticObject", "Sign_Market"]),
                          anchor)
        if anchor is None:
            continue
        spot = place_near(lines, float(anchor[2]), float(anchor[3]) + 16, [], 4)
        if spot is None:
            print("WARNING - no room for a market board in %s" % town)
            continue
        x, y = spot
        lines.append("StaticObject\tMarket_Board\t%d\t%d" % ((x - 1) * 32, (y - 1) * 32 - 16))
        write_map(name, lines)
        print("%s: a market board at tile %d,%d" % (town, x, y))


def place_tavern():
    lines = map_lines(ASHFORD)
    if any("Id=Innkeeper" in ln for ln in lines[YT:]):
        print("Ashford has its tavern already")
        return
    taken = taken_spots(lines)
    row = [x for x in range(3, XT - 1) if clear(lines, x, TAVERN_ROW, taken) and clear(lines, x, TAVERN_ROW + 1, taken)]
    if len(row) < 8:
        print("WARNING - no room for the tavern in Ashford")
        return
    mid = row[len(row) // 2]
    keeper = min(row, key=lambda x: abs(x - mid))
    tables = [x for x in row if abs(x - keeper) in (3, 6)][:3]
    lines.append("NPC\tMan\t%d\t%d\tAttitude=Good Stand=1 Id=Innkeeper" % ((keeper - 1) * 32, (TAVERN_ROW - 1) * 32 - 8))
    for n, x in enumerate(tables, 1):
        lines.append("StaticObject\tDice_Table\t%d\t%d\tId=Dice_Table_%d" % ((x - 1) * 32, (TAVERN_ROW - 1) * 32, n))
    decor = [x for x in row if x not in tables and abs(x - keeper) >= 2][:4]
    rows = [ln.split(":") for ln in lines[:YT]]
    for x in decor[:2]:
        rows[TAVERN_ROW - 1][x - 1] += "+Decor(Barrel001)"
    for x in decor[2:4]:
        rows[TAVERN_ROW - 1][x - 1] += "+Decor(Bench001)"
    for y in range(YT):
        lines[y] = ":".join(rows[y])
    sign = next((x for x in row if x not in tables + decor and abs(x - keeper) >= 1), None)
    if sign is not None:
        lines.append("StaticObject\tSign_Tavern\t%d\t%d" % ((sign - 1) * 32, (TAVERN_ROW - 1) * 32 - 16))
    lines.append("Id\tThe_Green_Dragon\t%d\t%d" % (keeper, TAVERN_ROW + 1))
    write_map(ASHFORD, lines)
    print("Ashford: the Green Dragon (innkeeper at %d, dice tables at %s)" % (keeper, tables))


def make_tavern_sign():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_market
    if build_market.save(build_market.sign("Ale"), "Sign_Tavern"):
        pass
    write_section(os.path.join(DATA, "Entities.ini"), "Sign_Tavern", {
        "Type": "StaticObject", "Use.Words": "Examine",
        "Examine.Info": "A sign: The Green Dragon - ale, and games of chance (the innkeeper; the dice tables)."})


def main():
    make_sprites()
    make_horn()
    write_data()
    make_tavern_sign()
    write_scripts()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import story_kit as K
    if not K.new_mainland():                 # (build_estforlan.py places these in the new mainland)
        stalls_to_vendors()
        place_boards()
        place_tavern()


if __name__ == "__main__":
    main()
