"""The starting island (the Isle), done up. Run it once (again: it sees what's done and leaves it).

  python -I "Dev\\migrate\\build_isle.py"

  * The village (1,1,0): its houses are timber with thatched roofs; the old bank is the Isle's general store now (a
    storekeeper, Id=Isle_Storekeeper: starter tools and food). There's no bank on the Isle.
  * The dairy (2,0,0): the dairymaid's hut, a barn with hay, a fenced pasture for the cows, a hen coop with the nests
    in it (Id=Hen_Nests), a wheat field with a scarecrow, and a shepherd with the sheep (Id=Isle_Shepherd).
  * The chapel (3,1,0) by the graveyard: pews, an altar, and stairs down to its cellar (3,1,-1), where a hole in the
    floor goes down into the grotto (the caves under the Isle). The grotto's old hole on 2,1,0 is gone; its ladder
    now climbs up into the chapel cellar.
  * The land: dirt paths from the pier to the village, the dairy and the chapel; a lily pond; woods; an old orchard;
    a rocky outcrop (rocks to mine for stone); a flower meadow; a bench at the lookout over the sea.
  * Monsters notice you from further off (Entities.ini Aggro.Range: a third more, done once).
"""
import math
import os
import random
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from dragonsword import ini  # noqa: E402
from dsengine.homes import roof_piece  # noqa: E402

DATA = os.path.join(ROOT, "Data")
TILES_INI = os.path.join(DATA, "Tiles.ini")
XT, YT, TW = 25, 21, 32
GRASSY = ("Grass", "Dirt")
SMALL_DECOR = ("Flowers", "Pebbles", "Tall_Grass", "Fern", "Grass_Tuft", "Clover", "Daisies", "Weeds")


# ---------------------------------------------------------------- a map file, cell by cell
class Map:
    def __init__(self, name, new=False):
        self.name = name
        self.path = os.path.join(ROOT, "Maps", name + ".txt")
        if new:
            self.rows = [["Black001"] * XT for _ in range(YT)]
            self.ents = []
            return
        lines = ini.read_text(self.path).replace("\r", "").split("\n")
        self.rows = [[c.strip() for c in lines[y].split(":")][:XT] for y in range(YT)]
        self.ents = [ln for ln in lines[YT:] if ln.strip()]

    def parts(self, x, y):
        c = self.rows[y - 1][x - 1]
        bits = c.split("+")
        over = {}
        for b in bits[1:]:
            kind, _, arg = b.partition("(")
            over[kind] = arg.rstrip(")")
        return bits[0], over

    def put(self, x, y, tile, over):
        s = tile
        for kind in ("Decor", "Roof", "Infront", "Trigger"):
            if over.get(kind):
                s += "+%s(%s)" % (kind, over[kind])
        self.rows[y - 1][x - 1] = s

    def tile(self, x, y):
        return self.parts(x, y)[0]

    def decor(self, x, y):
        return self.parts(x, y)[1].get("Decor", "")

    def roofed(self, x, y):
        return bool(self.parts(x, y)[1].get("Roof"))

    def set(self, x, y, tile=None, decor=None, roof=None):
        """tile: the ground; decor: "" clears it; roof: "" clears it."""
        t, over = self.parts(x, y)
        if tile is not None:
            t = tile
        if decor is not None:
            over["Decor"] = decor
        if roof is not None:
            over["Roof"] = roof
        self.put(x, y, t, over)

    def groups(self):
        out = set()
        for row in self.rows:
            for c in row:
                if "Roof(" in c:
                    try:
                        out.add(int(c.split("Roof(")[1].split(")")[0].split(".")[1]))
                    except (IndexError, ValueError):
                        pass
        return out

    def open_ground(self, x, y, edge=1):
        if not (1 + edge <= x <= XT - edge and 1 + edge <= y <= YT - edge):
            return False
        t, over = self.parts(x, y)
        return t.startswith(GRASSY) and not over.get("Roof") and (not over.get("Decor") or
                                                                    over["Decor"].startswith(SMALL_DECOR))

    def ent_near(self, x, y, r=20):
        px, py = (x - 1) * TW, (y - 1) * TW
        for ln in self.ents:
            p = ln.split("\t")
            if len(p) >= 4 and p[0] in ("NPC", "StaticObject", "MapItem"):
                try:
                    if abs(float(p[2]) - px) < r + 8 and abs(float(p[3]) - py) < r + 16:
                        return True
                except ValueError:
                    pass
        return False

    def has_line(self, text):
        return any(text in ln for ln in self.ents)

    def save(self):
        lines = [":".join(r) for r in self.rows] + self.ents
        with open(self.path, "w", encoding="cp1252", newline="\r\n") as f:
            f.write("\n".join(lines) + "\n")


def roof_over(m, x1, y1, x2, y2, material="Thatch"):
    g = max(m.groups() | {0}) + 1
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            m.set(x, y, roof="%s.%02d" % (roof_piece(material, x, y, x1, y1, x2, y2), g))


def house(m, x1, y1, x2, y2, door, windows=(), wall="Timber001", floor="Plank001", roof="Thatch"):
    """A building: walls round, a floor inside, the front (bottom) row with the door and windows, the roof over the
    rest (as the village houses are built)."""
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            edge = x in (x1, x2) or y in (y1, y2)
            m.set(x, y, tile=wall if edge else floor, decor="", roof="")
    m.set(door, y2, tile="Door001")
    for wx in windows:
        m.set(wx, y2, decor="Timber_Window001")
    roof_over(m, x1, y1, x2, y2 - 1, roof)


def fence(m, x1, y1, x2, y2, gates=()):
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if (x in (x1, x2) or y in (y1, y2)) and (x, y) not in gates:
                m.set(x, y, decor="Fence001" if y in (y1, y2) else "Fence002")


def obj_line(kind, name, x, y, extra="", dy=0):
    s = "%s\t%s\t%d\t%d" % (kind, name, (x - 1) * TW, (y - 1) * TW + dy)
    return s + ("\t" + extra if extra else "")


def write_script(name, lines):
    path = os.path.join(DATA, "Scripts", name + ".txt")
    if os.path.exists(path):
        return
    with open(path, "w", encoding="cp1252", newline="\r\n") as f:
        f.write("// Generated by Dev\\migrate\\build_isle.py\n" + "\n".join(lines) + "\n")
    print("Made Data\\Scripts\\%s.txt" % name)


# ---------------------------------------------------------------- the village: timber and thatch, a store, no bank
def village():
    m = Map("1,1,0")
    if m.has_line("Id=Isle_Storekeeper"):
        print("The village is done already")
        return
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            t, over = m.parts(x, y)
            if not over.get("Roof") and not (t.startswith(("Brick", "Tile0")) and any(
                    m.roofed(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if 1 <= x + dx <= XT and 1 <= y + dy <= YT)):
                continue
            t = {"Brick001": "Timber001", "Tile001": "Plank001"}.get(t, t)
            d = over.get("Decor", "")
            d = {"Bank_Counter001": "Counter001", "Bank_Plaque001": "", "Bank_Column001": "Timber_Window001"}.get(d, d)
            over["Decor"] = d
            if over.get("Roof"):
                piece, _, g = over["Roof"].partition(".")
                over["Roof"] = "Thatch_Roof" + piece.split("_Roof")[-1] + "." + g
            m.put(x, y, t, over)
    m.set(13, 16, decor="")                         # (three columns made three windows: two will do)
    ents = []
    for ln in m.ents:
        p = ln.split("\t")
        if len(p) >= 2 and p[0] == "NPC" and p[1] == "Banker":
            ln = "NPC\tMerchant\t%s\t%s\tAttitude=Good Stand=1 Id=Isle_Storekeeper" % (p[2], p[3])
        ents.append(ln)
    m.ents = ents
    m.ents.append(obj_line("StaticObject", "Sign_General", 12, 17, dy=-16))
    m.ents.append("Id\tIsle_Store\t11\t17")
    m.save()
    print("The village: timber and thatch; the bank is the Isle Store")
    racks = os.path.join(DATA, "ItemRacks.ini")
    if not ini.section("SHOP-Isle", racks):
        stock = [("Bronze_Axe", 3), ("Bronze_Pickaxe", 3), ("Fishing_Rod", 3), ("Bait", 40), ("Bucket", 4),
                 ("Spade", 3), ("Bread", 15), ("Basic_Potion", 5), ("Empty_Vial", 10)]
        items = {"Type": "Shop", "Buy.Rate": "1.1", "Sell.Rate": "0.6", "Specific": "0"}
        n = 0
        for name, q in stock:
            if ini.section(name, os.path.join(DATA, "Entities.ini")):
                n += 1
                items["Item%d" % n] = "%s,%d" % (name, q)
        for k, v in items.items():
            ini.write("SHOP-Isle", k, v, racks)
        print("ItemRacks.ini [SHOP-Isle]")
    write_script("Talk to Isle_Storekeeper", [
        "01\tDisplay.Conversation\tMerchant\tWelcome to the Isle Store! This old place was a bank once, but there's "
        "precious little money on the Isle. Tools, bait and a bite to eat: that's what folk need here.\tLet me see "
        "your goods.\t02\tGoodbye.\t04",
        "02\tDisplay.Item.Rack\tGENERAL\tMerchant\tSHOP-Isle\t04",
        "03\tEnd",
        "04\tEnd",
    ])


# ---------------------------------------------------------------- the dairy: a hut, a barn, a fence, a coop, wheat
def dairy():
    m = Map("2,0,0")
    if m.has_line("Id=Isle_Shepherd"):
        print("The dairy is done already")
        return
    house(m, 2, 3, 6, 6, door=4, windows=(3, 5))                 # the dairymaid's hut
    m.set(3, 4, decor="Bed001")
    m.set(5, 4, decor="Table001")
    m.set(5, 5, decor="Barrel001")
    house(m, 16, 4, 22, 8, door=19, windows=(17, 21))            # the barn
    for x, y, d in ((17, 5, "Haystack001"), (18, 5, "Haystack001"), (21, 5, "Sacks001"), (21, 7, "Barrel001"),
                    (17, 7, "Crate001")):
        m.set(x, y, decor=d)
    fence(m, 2, 8, 8, 14, gates=((8, 11),))                     # the cows' pasture, its gate to the east
    house(m, 20, 11, 24, 14, door=22)                            # the hen coop
    for x in (21, 22, 23):
        m.set(x, 12, decor="Nest001")
    for x, y in ((10, 7), (14, 8), (12, 11)):                    # (the old nests out in the field)
        if m.decor(x, y).startswith("Nest"):
            m.set(x, y, decor="")
    for y in range(18, 21):                                      # a wheat field, and its scarecrow
        for x in range(13, 18):
            if m.open_ground(x, y):
                m.set(x, y, tile="Wheat001", decor="")
    m.set(18, 19, decor="Scarecrow001")
    ents = []
    for ln in m.ents:
        p = ln.split("\t")
        if len(p) >= 4 and p[0] == "NPC" and p[1] == "Cow":                 # (in the pasture)
            cx, cy = min(max(int(p[2]) // TW + 1, 3), 7), min(max(int(p[3]) // TW + 1, 9), 13)
            ln = "NPC\tCow\t%d\t%d\tAttitude=Bad Zone=3,9,7,13" % ((cx - 1) * TW, (cy - 1) * TW)
        elif len(p) >= 4 and p[0] == "NPC" and p[1] == "Chicken":
            continue
        elif p[:2] == ["Id", "Hen_Nests"]:
            ln = "Id\tHen_Nests\t22\t13"
        ents.append(ln)
    for x, y in ((19, 15), (21, 16), (23, 15)):
        ents.append(obj_line("NPC", "Chicken", x, y, "Attitude=Bad Zone=18,15,24,18"))
    ents.append(obj_line("NPC", "Shepherd", 13, 15, "Attitude=Good Zone=10,11,17,17 Pause=4-10 Id=Isle_Shepherd", -8))
    ents += ["Id\tDairy_Barn\t19\t9", "Id\tHen_Coop\t22\t15"]
    m.ents = ents
    m.save()
    print("The dairy: a hut, a barn, a fenced pasture, a hen coop, a wheat field and a shepherd")
    write_script("Talk to Isle_Shepherd", [
        "01\tDisplay.Conversation\tShepherd\tBaa! Ha, sorry - you talk to sheep all day, you start sounding like one."
        "\\Mind you don't spook them. If you're after wool, they'll let you shear them if you're gentle.\tHow do I "
        "shear a sheep?\t02\tGoodbye.\t03",
        "02\tDisplay.Conversation\tShepherd\tUse shears on one - the tinker in Ashford sells them, or a shop will. Then "
        "spin the wool at a spinning wheel, or sell it to a weaver.\tThanks.\t03",
        "03\tEnd",
    ])


# ---------------------------------------------------------------- the chapel, its cellar, and the way down
def chapel():
    m = Map("3,1,0")
    if m.has_line("Id=Isle_Chapel"):
        print("The chapel is there already")
        return
    house(m, 13, 7, 19, 12, door=16, windows=(14, 18))
    for x in (14, 15, 17, 18):                                   # the pews, an aisle down the middle
        for y in (10, 11):
            m.set(x, y, decor="Bench001")
    m.set(16, 8, decor="Table001")                               # the altar, candles either side
    m.set(15, 8, decor="Candles001")
    m.set(17, 8, decor="Candles001")
    m.set(18, 8, tile="Stairs002", decor="")                     # the steps down to the cellar
    m.ents.append(obj_line("StaticObject", "Notice", 15, 13, "Id=Isle_Chapel", 2))
    m.ents.append("Id\tChapel_Door\t16\t13")
    m.save()
    print("The chapel by the graveyard")
    write_script("Read Isle_Chapel", [
        "01\t>Distance.From.Clicked.Entity\t64\t04",
        "02\tDisplay.Conversation\tNotice\tTHE ISLE CHAPEL\\Rest in peace, all who sleep in the yard.\\The steps "
        "behind the altar go down to the cellar. Mind the hole in its floor: it drops into the grotto, the caves under "
        "the Isle.\tOkay\t03",
        "03\tEnd",
        "04\tDisplay.Message\tDarkRed\tYou can't read that from here!",
        "05\tEnd",
    ])
    # the cellar: a stone room under the chapel, on a map of its own under it (its edges solid rock)
    c = Map("3,1,-1", new=True)
    for y in range(6, 14):
        for x in range(12, 21):
            edge = x in (12, 20) or y in (6, 13)
            c.set(x, y, tile="Stone_Wall001" if edge else "Tile001")
    c.set(18, 8, tile="Stairs001")                               # (under the chapel's: up)
    c.set(14, 9, decor="Basement_Hole001")                       # the hole down into the grotto
    for x, y, d in ((13, 7, "Barrel001"), (13, 12, "Barrel001"), (19, 12, "Crate001"), (17, 12, "Crate001"),
                    (13, 11, "Sacks001"), (19, 10, "Candles001")):
        c.set(x, y, decor=d)
    for x in (15, 17):
        c.set(x, 6, decor="Wall_Torch001")
    c.ents = ["Id\tChapel_Cellar\t15\t10"]
    c.save()
    print("Made Maps\\3,1,-1.txt (the chapel cellar)")
    # the grotto: no hole on the surface any more; its ladder climbs into the cellar
    g = Map("2,1,0")
    if g.decor(20, 10).startswith("Ladder"):
        g.set(20, 10, decor="")
        g.save()
    u = Map("2,1,-1")
    if u.decor(20, 10) == "Ladder001":
        u.set(20, 10, decor="Cave_Ladder001")
        u.save()
    tiles = os.path.join(ROOT, "Sprites", "Tiles")
    for new, old, words, info in (
            ("Basement_Hole001", "Ladder006", "Climb Down,Examine",
             "A hole in the cellar floor, a ladder going down into the dark: the grotto."),
            ("Cave_Ladder001", "Ladder001", "Climb Up,Examine", "A ladder up to the chapel cellar.")):
        if not os.path.exists(os.path.join(tiles, new + ".png")):
            shutil.copy(os.path.join(tiles, old + ".png"), os.path.join(tiles, new + ".png"))
        if not ini.section(new, TILES_INI):
            for k, v in ini.section(old, TILES_INI):
                ini.write(new, k, v, TILES_INI)
            ini.write(new, "Use.Words", words, TILES_INI)
            ini.write(new, "Examine.Info", info, TILES_INI)
        colours = os.path.join(ROOT, "Dev", "Minimap Colours.txt")
        if new not in ini.read_text(colours):
            with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
                f.write("%s\t255 0 0\n" % new)
    write_script("Climb Down Basement_Hole", [
        "01\tPlay.Sound\tLadder",
        "02\tDisplay.Message\tCyan\tYou climb down the ladder, into the grotto.",
        "03\tTeleport\t%d,%d\t2,1,-1" % (19 * TW, 10 * TW - 8),
        "04\tEnd",
    ])
    write_script("Climb Up Cave_Ladder", [
        "01\tPlay.Sound\tLadder",
        "02\tDisplay.Message\tCyan\tYou climb up the ladder, into the chapel cellar.",
        "03\tTeleport\t%d,%d\t3,1,-1" % (13 * TW, 9 * TW - 8),
        "04\tEnd",
    ])
    grotto = os.path.join(DATA, "Scripts", "Read The_Grotto.txt")
    text = ini.read_text(grotto)
    if "chapel" not in text:
        text = text.replace("A ladder goes down into the caves under the Isle.",
                            "The way down into the caves is through the chapel, east past the graveyard: the hole in "
                            "its cellar floor.")
        with open(grotto, "w", encoding="cp1252", newline="") as f:
            f.write(text)


# ---------------------------------------------------------------- the land: paths, a pond, woods, rocks, flowers
def gpos(name, x, y):
    mx, my, _ = (int(v) for v in name.split(","))
    return mx * XT + x - 1, my * YT + y - 1


def maps_cache():
    cache = {}

    def get(mx, my):
        key = "%d,%d,0" % (mx, my)
        if key not in cache:
            cache[key] = Map(key) if os.path.exists(os.path.join(ROOT, "Maps", key + ".txt")) else None
        return cache[key]
    return cache, get


def path(get, points, rng):
    """A dirt path through points (global tiles), wandering a little; it only ever lays dirt on open grass."""
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        n = max(abs(bx - ax), abs(by - ay), 1)
        phase = rng.uniform(0, 6.3)
        last = None
        for i in range(n + 1):
            t = i / n
            x = round(ax + (bx - ax) * t + (0 if abs(bx - ax) > abs(by - ay) else 1.2 * math.sin(phase + t * 5)))
            y = round(ay + (by - ay) * t + (1.2 * math.sin(phase + t * 5) if abs(bx - ax) > abs(by - ay) else 0))
            steps = [(x, y)]
            if last and last[0] != x and last[1] != y:
                steps.insert(0, (x, last[1]))                  # (no diagonal gaps: a path you can walk)
            for gx, gy in steps:
                m = get(gx // XT, gy // YT)
                lx, ly = gx % XT + 1, gy % YT + 1
                if m is not None and m.open_ground(lx, ly, 0) and m.tile(lx, ly).startswith("Grass"):
                    m.set(lx, ly, tile="Dirt001", decor="")
            last = (x, y)


def scatter(m, rng, box, names, count, gap=1):
    x1, y1, x2, y2 = box
    spots = [(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1) if m.open_ground(x, y) and
             not m.ent_near(x, y)]
    rng.shuffle(spots)
    placed = []
    for x, y in spots:
        if len(placed) >= count:
            break
        if all(abs(x - px) > gap or abs(y - py) > gap for px, py in placed):
            m.set(x, y, decor=rng.choice(names))
            placed.append((x, y))
    return len(placed)


def land():
    cache, get = maps_cache()
    if get(2, 1) and get(2, 1).tile(10, 17) == "Pond001":
        print("The land is done already")
        return
    rng = random.Random(1801)
    pier = gpos("1,2,0", 21, 11)
    square = gpos("1,1,0", 15, 10)
    east = gpos("2,1,0", 6, 5)
    path(get, [pier, gpos("1,1,0", 16, 19), square], rng)                       # the pier to the village
    path(get, [square, gpos("1,1,0", 23, 8), east, gpos("2,0,0", 10, 16), gpos("2,0,0", 10, 12)], rng)   # the dairy
    path(get, [east, gpos("2,1,0", 16, 12), gpos("3,1,0", 3, 13), gpos("3,1,0", 16, 13)], rng)           # the chapel
    path(get, [gpos("2,0,0", 10, 12), gpos("2,0,0", 19, 10)], rng)                                     # the barn
    # a lily pond, reeds round it
    pond = get(2, 1)
    for y in range(16, 19):
        for x in range(9, 13):
            if ((x - 10.5) / 2.1) ** 2 + ((y - 17) / 1.5) ** 2 <= 1 and pond.open_ground(x, y):
                pond.set(x, y, tile="Pond001", decor="")
    scatter(pond, rng, (8, 15, 13, 19), ["Reeds001"], 4, 0)
    # woods, an old orchard, a rocky outcrop, a flower meadow
    n = scatter(get(0, 1), rng, (4, 3, 10, 7), ["Tree001", "Tree001", "Oak_Tree001"], 8)
    n += scatter(get(3, 2), rng, (13, 3, 19, 8), ["Tree001", "Oak_Tree001", "Willow_Tree001"], 7)
    n += scatter(get(1, 0), rng, (10, 10, 16, 14), ["Tree001"], 6, 1)
    n += scatter(get(3, 2), rng, (4, 4, 9, 8), ["Rock002", "Rock003"], 6)
    n += scatter(get(0, 0), rng, (12, 8, 19, 15), ["Flowers001", "Flowers002", "Flowers003"], 14, 0)
    look = get(3, 1)                                                           # a bench at the lookout, east
    if look.open_ground(20, 10):
        look.set(20, 10, decor="Bench001")
        look.set(19, 9, decor="Flowers002")
    for key, m in cache.items():
        if m is not None:
            m.save()
    print("The land: paths, a pond, woods, an orchard, an outcrop, a meadow, a lookout (%d things placed)" % n)


def aggro():
    path_ = os.path.join(DATA, "Entities.ini")
    if ini.read("Gameplay", "Aggro.Raised", "", os.path.join(DATA, "Config.ini")):
        print("Aggro ranges were raised already")
        return
    text = ini.read_text(path_)
    sec, n = None, 0
    for ln in text.replace("\r", "").split("\n"):
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1]
        elif sec and s.lower().startswith("aggressive=1"):
            old = int(float(ini.read(sec, "Aggro.Range", "0", path_) or 0))
            if old > 0:
                ini.write(sec, "Aggro.Range", str(int(round(old * 1.3 / 10.0)) * 10), path_)
                n += 1
    ini.write("Gameplay", "Aggro.Raised", "1.3", os.path.join(DATA, "Config.ini"))
    print("Aggro ranges a third more for %d monsters" % n)


def main():
    village()
    dairy()
    chapel()
    land()
    aggro()


if __name__ == "__main__":
    main()
