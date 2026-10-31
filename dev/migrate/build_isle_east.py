"""The Isle grows east: new land across 3,0,0's sea and new maps 4,0,0 and 4,1,0, and on it the cottage where a new
character wakes - a bed, a range to cook on, a table. Run it once (again: it sees it's done).

  python -I "dev\\migrate\\build_isle_east.py"

  * Land only ever replaces sea (nothing built is touched); the chapel's bench still looks out over open water,
    and the sea still runs between the Isle and the walled town to the south-east. Its coast is rounded off
    afterwards (smooth_coasts.py).
  * The cottage (4,0,0): timber and thatch, thin walls inside, a bed (where you wake: Config Start.*, and
    saves\\TEMPLATE.ini for new characters), a range (Cook), a table, a rug; a name board by its door; a path to the chapel; trees, flowers, rocks, rabbits.
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ashen import ini  # noqa: E402
from build_isle import Map, XT, YT, TW, DATA, obj_line, house, maps_cache, path, gpos, scatter, write_script  # noqa: E402

CENTRE = (97.0, 18.0)                 # (the new land's middle, in global tiles: 3,0,0's east, 4,0,0's west)
RADII = (17.0, 11.5)
COTTAGE = (5, 9, 10, 13)              # on 4,0,0; its door at 7,13
DOOR_X = 7
BED = (6, 10)
START = (8, 12)                       # where a new character stands: by the bed, on open floor


HEADLAND = ((108.0, 12.0), (10.0, 8.5))   # (a second, rounder piece: the cottage's headland, in 4,0,0)


def blob(gx, gy, centre, radii, phase=0.0):
    cx, cy = centre
    rx, ry = radii
    a = math.atan2(gy - cy, gx - cx)
    wobble = 1 + 0.12 * math.sin(3 * a + 0.7 + phase) + 0.08 * math.sin(5 * a + 2.1) + 0.05 * math.sin(9 * a)
    return ((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2 <= wobble ** 2


def in_land(gx, gy):
    """The new land's shape: two ellipses with wandering edges, run together."""
    return blob(gx, gy, CENTRE, RADII) or blob(gx, gy, *HEADLAND, phase=1.9)


def new_map(name):
    m = Map(name, new=True)
    m.rows = [["Water001"] * XT for _ in range(YT)]
    m.ents = []
    m.save()
    return Map(name)


def raise_land():
    for name in ("4,0,0", "4,1,0"):
        if not os.path.exists(os.path.join(ROOT, "maps", name + ".txt")):
            new_map(name)
    cache, get = maps_cache()
    n = 0
    for gy in range(0, 2 * YT):
        for gx in range(3 * XT, 5 * XT):
            m = get(gx // XT, gy // YT)
            if m is None or not in_land(gx, gy):
                continue
            x, y = gx % XT + 1, gy % YT + 1
            if m.tile(x, y).startswith("Water") or m.tile(x, y).startswith(("Sand_Water", "Sea_Rock")):
                if m.decor(x, y) or m.ent_near(x, y):
                    continue
                m.set(x, y, tile="Grass001", decor="")
                n += 1
    wet = lambda t: t.startswith(("Water", "Sand_Water", "Sea_Rock"))
    for _ in range(2):                                # (a puddle of sea left inland, a rock in it: grass too)
        for gy in range(1, 2 * YT - 1):
            for gx in range(3 * XT, 5 * XT):
                m = get(gx // XT, gy // YT)
                if m is None:
                    continue
                x, y = gx % XT + 1, gy % YT + 1
                if not wet(m.tile(x, y)) or not in_land(gx, gy) and not (2 <= x <= XT - 1):
                    continue
                around = [get((gx + dx) // XT, (gy + dy) // YT) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                land = sum(1 for (dx, dy), mm in zip(((1, 0), (-1, 0), (0, 1), (0, -1)), around)
                           if mm is not None and not wet(mm.tile((gx + dx) % XT + 1, (gy + dy) % YT + 1)))
                if land >= 3:
                    m.set(x, y, tile="Grass001", decor="")
                    n += 1
    for m in cache.values():
        if m is not None:
            m.save()
    print("New land: %d squares of sea are grass now" % n)


def cottage():
    m = Map("4,0,0")
    if m.has_line("Id\tCottage"):
        print("The cottage is there already")
        return
    x1, y1, x2, y2 = COTTAGE
    house(m, x1, y1, x2, y2, door=DOOR_X, windows=(x1 + 1, x2 - 1))
    bx, by = BED
    m.set(bx, by, decor="Bed001")
    m.set(x2 - 2, by + 1, decor="Table001")
    m.set(x2 - 3, by + 1, decor="Chair002")
    m.set(DOOR_X, y2 - 1, decor="")
    for x in range(x1 + 2, x2 - 1):                               # a rug, the table and chair on it
        t, over = m.parts(x, by + 1)
        over["Under"] = "Rug011" if x == x1 + 2 else ("Rug013" if x == x2 - 2 else "Rug012")
        m.put(x, by + 1, t, over)
    m.ents += [
        obj_line("StaticObject", "Range", x2 - 1, by),               # the stove: cook on it
        obj_line("StaticObject", "Notice", DOOR_X + 1, y2 + 1, "Id=Cottage_Notice", 2),
        "Id\tCottage\t%d\t%d" % START,
        "Id\tCottage_Door\t%d\t%d" % (DOOR_X, y2 + 1),
    ]
    m.save()
    write_script("Read Cottage_Notice", [
        "01\t>Distance.From.Clicked.Entity\t64\t04",
        "02\tDisplay.Conversation\tNotice\tROSE COTTAGE\\Built by old Tam the thatcher, the year the great storm took the pier.\tOkay\t03",
        "03\tEnd",
        "04\tDisplay.Message\tDarkRed\tYou can't read that from here!",
        "05\tEnd",
    ])
    print("The cottage, its bed, range, table and rug; the notice by its door")


def surroundings():
    cache, get = maps_cache()
    m = get(4, 0)
    if any(m.decor(x, y).startswith("Oak_Tree") for y in range(1, YT + 1) for x in range(12, 25)):
        print("The new land is dressed already")
        return
    rng = random.Random(4004)
    path(get, [gpos("4,0,0", DOOR_X, COTTAGE[3] + 1), gpos("4,0,0", 6, 18), gpos("3,1,0", 20, 4),
               gpos("3,1,0", 17, 6), gpos("3,1,0", 16, 13)], rng)
    n = scatter(m, rng, (12, 6, 20, 16), ["Tree001", "Oak_Tree001", "Tree001"], 9)
    n += scatter(m, rng, (2, 15, 12, 20), ["Flowers001", "Flowers002", "Flowers003", "Tall_Grass001"], 12, 0)
    n += scatter(get(3, 0), rng, (12, 8, 24, 20), ["Tree001", "Flowers002", "Rock002", "Flowers001"], 10)
    n += scatter(get(4, 1), rng, (1, 1, 14, 8), ["Rock003", "Flowers003", "Tree001"], 5)
    if not m.has_line("NPC\tRabbit"):
        m.ents += [obj_line("NPC", "Rabbit", 15, 17, "Attitude=Passive Zone=12,14,19,19"),
                   obj_line("NPC", "Rabbit", 3, 17, "Attitude=Passive Zone=2,15,10,19")]
    for mm in cache.values():
        if mm is not None:
            mm.save()
    print("The new land: a path to the chapel, trees, flowers, rocks, rabbits (%d things)" % n)


def start_here():
    """New characters wake in the cottage; so does anyone who dies without a bed of their own."""
    sx, sy = START
    x, y = (sx - 1) * TW, (sy - 1) * TW - 16
    cfg = os.path.join(DATA, "Config.ini")
    for k, v in (("Start.Map", "4,0,0"), ("Start.X", str(x)), ("Start.Y", str(y))):
        ini.write("Gameplay", k, v, cfg) if ini.read("Gameplay", k, "", cfg) else None
    tpl = os.path.join(ROOT, "saves", "TEMPLATE.ini")
    for k, v in (("Map", "4,0,0"), ("X", str(x)), ("Y", str(y))):
        ini.write("Player", k, v, tpl)
    for f in ("Music.ini", "Ambient.ini"):
        p = os.path.join(DATA, f)
        for name in ("4,0,0", "4,1,0"):
            if not ini.read("Maps", name, "", p):
                like = ini.read("Maps", "3,1,0", "", p)
                if like:
                    ini.write("Maps", name, like, p)
    wm = os.path.join(DATA, "WorldMap.ini")
    if not ini.read("Places", "The Cottage", "", wm):
        ini.write("Places", "The Cottage", "Cottage", wm)
    print("New characters start in the cottage (4,0,0 %d,%d)" % (x, y))


def main():
    raise_land()
    cottage()
    surroundings()
    start_here()


if __name__ == "__main__":
    main()
