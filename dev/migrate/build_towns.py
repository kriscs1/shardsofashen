"""Every settlement the size the owner asked for (towns.py grows them). Run it once on the world as it was: it marks
each settlement it has grown (an Id <Key>_Grown on its centre's map) and leaves it alone after.

  python -I "dev\\migrate\\build_towns.py"       (then smooth_coasts.py, validate.py, build_minimaps.py)

  Large city    5 taverns, a bank, a main market square with four lanes off it (bread and pastries; butchers and
                pies; fish; vegetables), a police station, a hospital, 10 streets of houses, gardens and parks, a
                City Hall, a Town Hall, carts and horses between its parts. (Southport; its City Hall is Estforlan's
                Parliament until Galaith opens again.)
  Medium city   5 taverns, a bank, a market square with four small lanes, a sheriff's office and jail, a hospital,
                10 streets of houses, a City Hall, a Town Hall. (King Rupert's Keep, with its keep and bailey;
                the Wizards' Court, with its court and tower; Fenwick; Ravensgate.)
  Small city    2 taverns, a small bank, a market square with two small lanes (bread, pastries and fish; vegetables,
                butchers and pies), a sheriff's office and jail, a medical office, 5 streets, a City Hall, a Town
                Hall. (Ashford.)
  Town          a tavern, a small bank, a market square with the two small lanes, a sheriff's office, a doctor's
                office in a house, 5 streets, a Town Hall. (Highwatch, Frosthold.)
  Village       a pub, a market square, a sheriff's office, a doctor's office in a house, 5 streets, a village
                hall. (Oakhollow, Thornwick, Emberwatch.)
  Hamlet        a pub, 2 streets. (Wildwood and Saltmarsh, new; Moorcross on Greymoor; Dunerest.)
A bank a town has already isn't built twice. New land: Southport's west (0,3,0 and 0,4,0) and an island east of the
Royal Isle for the Wizards' Court (5,4,0 and 5,5,0, over a bridge from the palace's south lawn).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
import towns as T  # noqa: E402
from story_kit import Map, ini  # noqa: E402

XT, YT = K.XT, K.YT

CIVIC = lambda *kinds: [("building", k, n) for k, n in kinds]
LARGE = [("square",)] + CIVIC(("parliament", "City Hall"), ("hall", "Town Hall"), ("bank", ""), ("police", ""),
                               ("hospital", "")) + [("building", "tavern", "")] * 5 + \
        [("lanes", ["bakery", "butcher", "fish", "greens"], 2), ("park", 2), ("streets", 10, 3)]
MEDIUM = [("square",)] + CIVIC(("hall", "City Hall"), ("hall", "Town Hall"), ("bank", ""), ("sheriff", ""),
                                ("hospital", "")) + [("building", "tavern", "")] * 5 + \
         [("lanes", ["bakery", "butcher", "fish", "greens"], 2), ("streets", 10, 2)]
SMALL = [("square", 7, 6, 3)] + CIVIC(("hall", "City Hall"), ("hall", "Town Hall")) + \
        [("building", "tavern", "")] * 2 + CIVIC(("bank", ""), ("sheriff", ""), ("medical", "")) + \
        [("lanes", ["bakery+fish", "greens+butcher"], 2), ("streets", 5, 2)]
TOWN = [("square", 7, 6, 3)] + CIVIC(("hall", "Town Hall"), ("bank", ""), ("jail", ""), ("doctor", ""),
                                      ("tavern", "")) + [("lanes", ["bakery+fish", "greens+butcher"], 2), ("streets", 5, 2)]
VILLAGE = [("square", 7, 5, 2)] + CIVIC(("hall", "Village Hall"), ("jail", ""), ("doctor", ""), ("inn", "")) + \
          [("streets", 5, 2)]
HAMLET = [("building", "inn", ""), ("streets", 2, 2)]

STYLES = {
    "brick": {"walls": ["Brick001", "Brick001", "Plaster001", "Timber001"], "grand": "Brick001"},
    "stone": {"walls": ["Stone_Wall001", "Stone_Wall001", "Plaster001", "Brick001"], "grand": "Stone_Wall001"},
    "wood": {"walls": ["Timber001", "Timber001", "Plaster001"]},
    "marsh": {"walls": ["Timber001", "Plaster001"]},
    "desert": {"walls": ["Sandstone001", "Plaster001"], "grand": "Sandstone001"},
    "snow": {"walls": ["Stone_Wall001", "Timber001"], "grand": "Stone_Wall001"},
    "wizard": {"walls": ["Plaster001", "Stone_Wall001", "Brick001"], "grand": "Stone_Wall001"},
}

# key, title, its own maps (built round), the maps it grows over (streets laid through them first), its centre
# (map, tile), size, style, a city (cobbled)?
SETTLEMENTS = [
    ("Southport", "Southport", ["1,3,0"], ["0,3,0", "0,4,0", "0,2,0", "1,4,0"], ("1,3,0", 16, 13), LARGE, "brick", True),
    ("Ashford", "Ashford", ["2,3,0", "3,3,0"], ["3,4,0", "3,5,0"], ("2,3,0", 13, 11), SMALL, "brick", True),
    ("Keep", "King Rupert's Keep", ["2,4,0"], ["2,5,0", "1,5,0", "2,6,0"], ("2,4,0", 13, 18), MEDIUM, "stone", True),
    ("Court", "the Wizards' Court", ["4,4,0", "4,5,0", "5,6,0"], ["5,4,0", "5,5,0"], ("5,4,0", 12, 11), MEDIUM, "wizard", True),
    ("Fenwick", "Fenwick", ["2,8,0"], ["3,8,0", "2,9,0", "1,8,0"], ("2,8,0", 13, 11), MEDIUM, "marsh", True),
    ("Ravensgate", "Ravensgate", ["8,8,0"], ["7,8,0", "8,7,0", "7,7,0"], ("8,8,0", 13, 11), MEDIUM, "stone", True),
    ("Highwatch", "Highwatch", ["4,8,0"], ["4,7,0"], ("4,8,0", 13, 11), TOWN, "stone", False),
    ("Frosthold", "Frosthold", ["4,10,0"], ["4,9,0", "3,9,0"], ("4,10,0", 13, 11), TOWN, "snow", False),
    ("Oakhollow", "Oakhollow", ["1,6,0"], ["1,7,0"], ("1,6,0", 13, 11), VILLAGE, "wood", False),
    ("Thornwick", "Thornwick", ["7,6,0"], ["8,6,0"], ("7,6,0", 13, 11), VILLAGE, "wood", False),
    ("Emberwatch", "Emberwatch", ["7,4,0"], ["8,4,0"], ("7,4,0", 13, 11), VILLAGE, "stone", False),
    ("Moorcross", "Moorcross", ["3,6,0"], [], ("3,6,0", 13, 11), HAMLET, "stone", False),
    ("Dunerest", "Dunerest", ["1,10,0"], [], ("1,10,0", 13, 11), HAMLET, "desert", False),
    ("Wildwood", "Wildwood", [], ["0,6,0"], ("0,6,0", 13, 11), HAMLET, "wood", False),
    ("Saltmarsh", "Saltmarsh", [], ["0,8,0"], ("0,8,0", 13, 11), HAMLET, "marsh", False),
]


RACKS = {   # the lanes' shops, the pubs, the cobbler's stall
    "SHOP-Bakery": [("Bread", 20), ("Berry_Pie", 6), ("Pumpkin_Pie", 6), ("Meat_Pie", 6), ("Fish_Pie", 4)],
    "SHOP-Butchery": [("Raw_Meat", 15), ("Raw_Poultry", 10), ("Meat_Pie", 8),
                      ("Meat_Sandwich", 6), ("Stew", 4)],
    "SHOP-Fishmongery": [("Raw_Fish", 15), ("Raw_Trout", 10), ("Raw_Salmon", 6), ("Cooked_Fish", 8), ("Fish_Pie", 6)],
    "SHOP-Greengrocery": [("Cabbage", 15), ("Carrot", 15), ("Potato", 15), ("Onion", 12), ("Pumpkin", 6),
                          ("Berries", 10)],
    "SHOP-Tailor": [("Leather_Cap", 4), ("Leather_Body", 3), ("Leather_Legs", 3), ("Leather_Gloves", 4),
                    ("Silver_Tiara", 1), ("Chefs_Hat", 2)],
    "SHOP-Cobbler": [("Leather_Boots", 5), ("Iron_Boots", 2)],
    "SHOP-Armour": [("Iron_Helm", 3), ("Iron_Platebody", 2), ("Iron_Platelegs", 2), ("Iron_Shield", 3),
                    ("Iron_Gauntlets", 3), ("Steel_Helm", 2), ("Steel_Platebody", 1), ("Steel_Platelegs", 1),
                    ("Steel_Shield", 2), ("Steel_Gauntlets", 2), ("Steel_Boots", 2)],
    "SHOP-Weapons": [("Copper_Dagger", 4), ("Iron_Sword", 3), ("Steel_Sword", 2), ("Oak_Bow", 3), ("Yew_Bow", 1),
                     ("Arrows", 200)],
    "SHOP-Pub": [("Ale", 30), ("Bread", 10), ("Stew", 8), ("Vegetable_Stew", 8), ("Meat_Pie", 6), ("Fish_Pie", 6),
                 ("Baked_Potato", 8)],
}


# ================================================================== pictures: a horse and a cart, a pub's sign
def horse(step):
    """A brown horse, side-on facing west (sprites\\Walk: 8a-c and 2a-c, east the same turned)."""
    pg = K.pg()
    s = K.surface()
    coat, dark, mane = (140, 90, 50), (100, 62, 32), (60, 38, 22)
    pg.draw.ellipse(s, coat, (8, 11, 18, 10))                                # the body
    pg.draw.polygon(s, coat, [(9, 15), (5, 6), (8, 5), (12, 13)])            # the neck
    pg.draw.ellipse(s, coat, (1, 4, 8, 6))                                   # the head
    s.set_at((3, 6), (20, 14, 10))
    pg.draw.line(s, mane, (7, 4), (12, 12), 2)                               # the mane
    pg.draw.line(s, mane, (25, 13), (28, 22), 2)                             # the tail
    legs = {"a": (0, 0, 0, 0), "b": (2, -2, -2, 2), "c": (-2, 2, 2, -2)}[step]
    for (x, d) in zip((10, 13, 21, 24), legs):
        pg.draw.line(s, dark, (x, 19), (x + d, 28), 2)
        s.set_at((x + d, 29), (30, 24, 20))
    return K.outlined(s)


def cart():
    pg = K.pg()
    s = K.surface()
    wood, dark, light = (150, 104, 60), (96, 62, 32), (190, 140, 86)
    pg.draw.rect(s, dark, (3, 9, 26, 12))
    pg.draw.rect(s, wood, (4, 8, 24, 10))
    for x in (8, 14, 20, 26):
        pg.draw.line(s, dark, (x - 2, 8), (x - 2, 17))
    pg.draw.line(s, light, (4, 8), (27, 8))
    pg.draw.circle(s, dark, (10, 22), 6, 2)                                  # the wheel
    pg.draw.line(s, dark, (10, 16), (10, 28))
    pg.draw.line(s, dark, (4, 22), (16, 22))
    pg.draw.line(s, dark, (0, 14), (4, 14), 2)                               # the shafts
    return K.outlined(s)


def pictures():
    for f in "abc":
        img = horse(f)
        K.save("Walk", "Horse8" + f, img)
        K.save("Walk", "Horse2" + f, K.pg().transform.flip(img, True, False))
    K.save("Entities", "Horse", horse("a"))
    K.save("Entities", "Cart", cart())
    K.copy_sprite("Entities", "Sign_Tavern", "Sign_Pub")


def data():
    E = K.ENTS
    K.people_sections()
    K.section(E, "Horse", [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Stroke,Examine"),
                           ("Examine.Info", "A patient carthorse, chewing."), ("Roam.Radius", "0"),
                           ("Chase.Radius", "0"), ("Walk.Speed", "0.4"), ("Pause", "4-12"), ("Respawn", "300"),
                           ("Kill.Sound", "Livestock")])
    K.section(E, "Cart", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "1"),
                          ("Examine.Info", "A cart, its seats worn smooth by the city's travellers.")])
    for name, info in (("Sign_Pub", "A pub's sign: a foaming tankard."),):
        K.section(E, name, [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Examine.Info", info)])
    for rack, items in RACKS.items():
        lines = ["Type=Shop", "Buy.Rate=1.2", "Sell.Rate=0.6", "Specific=0"]
        lines += ["Item%d=%s,%d" % (i, n, q) for i, (n, q) in enumerate(
            [(n, q) for n, q in items if ini.section(n, E)], 1)]
        K.set_section(K.RACKS, rack, lines)
    K.write_script("Stroke Horse", [("Play.Sound", "Pickup"), ("Display.Message", "Cyan",
                                                             "The horse snorts softly and noses your hand."),
                                    ("End",)], T.MAKER)
    K.minimap_colour("Paving001", (170, 170, 164))


# ================================================================== new land
def land_west_of_southport():
    """0,3,0 and 0,4,0: Southport's west, on the coast (water along the west and the north, as the maps round)."""
    for name in ("0,3,0", "0,4,0"):
        if K.map_exists(name):
            continue
        m = Map(name, new=True)
        sp = Map("1,3,0") if name == "0,3,0" else Map("1,4,0")
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                if x == 1:
                    t = "Water001"
                elif x == 2:
                    t = "Sand001"
                elif name == "0,3,0" and y <= 7:
                    t = "Water001" if y <= 6 else "Sand001"
                elif x >= 22 and sp.tile(1, y).startswith(("Water", "Sand_Water")):
                    t = "Water001" if x >= 24 else "Sand001"
                else:
                    t = "Grass001"
                m.put(x, y, t, {})
        m.save()
        print("Made maps\\%s.txt: Southport's west" % name)
    if Map("0,2,0").tile(12, 15) == "Water001":                # (and the sea north of them, land now too)
        m = Map("0,2,0")
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                if y >= 4 and 2 <= x <= 20:
                    m.put(x, y, "Sand001" if y == 4 or x in (2, 20) else "Grass001", {})
        m.save()
        n3 = Map("0,3,0")
        for y in range(1, 8):
            for x in range(2, 21):
                n3.put(x, y, "Sand001" if x in (2, 20) else "Grass001", {})
        n3.save()
    sp = Map("1,3,0")
    changed = False
    for y in range(9, YT + 1):                               # (Southport's west shore meets the new land)
        for x in range(1, 5):
            t, over = sp.parts(x, y)
            if (t.startswith(("Water", "Sand_Water")) or t == "Sand001") and not over:
                sp.put(x, y, "Grass001", {})
                changed = True
    if changed:
        sp.save()


def wizards_island():
    """5,4,0 and 5,5,0, sea until now: an island for the Wizards' Court's town, a bridge from the palace's lawn."""
    a, b = Map("5,4,0"), Map("5,5,0")
    if a.tile(12, 10) != "Water001":
        return
    rng = random.Random(54)
    for m, top, bottom in ((a, 2, 21), (b, 1, 20)):
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                t, over = m.parts(x, y)
                if not t.startswith("Water"):
                    continue
                inland = 3 <= x <= 23 and top <= y <= bottom
                edge = (x in (3, 22) or y in (top, bottom)) and inland
                if inland:
                    m.put(x, y, "Sand001" if edge else "Grass001", {})
    for x in range(1, 4):                                    # the bridge from the palace's south lawn
        a.set(x, 18, tile="Plank001", decor="")
    a.save()
    b.save()
    r = Map("4,4,0")
    if r.tile(25, 18) != "Plank001":
        r.set(25, 18, tile="Plank001", decor="")
        r.save()
    print("5,4,0 and 5,5,0: an island for the Wizards' Court's town, bridged from the palace lawn")


# ================================================================== names: the Keep and the Court
def renames():
    path = os.path.join(K.SCRIPTS, "Read Tyrons_Keep.txt")
    if os.path.exists(path):
        K.write_script("Read Tyrons_Keep", [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            K.say("Notice", "KING RUPERT'S KEEP\\The King's keep and its bailey, held by his Steward while the King "
                            "is away.", ("Okay", "@end")),
            ("@end",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You can't read that from here!", "Denied"), ("End",)], T.MAKER)
    K.drop_label("Places", "King's Castle")
    K.place_label("Towns", "Wizards' Court", "4,4,0 13 3")
    K.place_label("Towns", "King Rupert's Keep", "2,4,0 13 8")
    K.place_label("Towns", "Ashford", "Waystone_Ashford")
    K.place_label("Towns", "Southport", "Southport_Market_Square")
    for key in ("Wildwood", "Saltmarsh"):
        K.place_label("Towns", key, "%s_Grown" % key)


def main():
    pictures()
    data()
    land_west_of_southport()
    wizards_island()
    renames()
    for key, title, own, grown, (cm, cx, cy), plan, style, city in SETTLEMENTS:
        names = own + grown
        if K.has_id(Map(cm), key + "_Grown"):           # (the mark is on its centre's map)
            continue
        g = T.Ground(names)
        mx, my = g.mxy(cm)
        town = T.Town(key, title, g, (mx * XT + cx - 1, my * YT + cy - 1), STYLES[style], city,
                      seed=sum(map(ord, key)))
        if any(ln.split("\t")[:2] == ["NPC", "Banker"] for m in g.maps.values() for ln in m.ents):
            plan = [p for p in plan if p[:2] != ("building", "bank")]      # (a bank there already)
        town.tame(grown)
        town.avenues(grown)
        T.grow(town, plan)
        K.place_id(g.maps[cm], key + "_Grown", cx, cy)
        g.save()
        kinds = {}
        for lot in town.lots:
            kinds[lot.kind] = kinds.get(lot.kind, 0) + 1
        print("%-11s %s; %d streets%s" % (title[:11], ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items())),
                                          town.streets, ("; no room for: " + ", ".join(town.missed)) if town.missed
                                          else ""))
    southport_carts()
    ini.forget()


def southport_carts():
    """Southport's carts and horses between its quarters (the city grew before the carts did: added to it as it is)."""
    names = ["1,3,0", "0,3,0", "0,4,0", "0,2,0", "1,4,0"]
    if K.has_id(Map(names[0]), "Southport_Cart_Stop_1"):
        return
    g = T.Ground(names)
    def cell(name, x, y):
        mx, my = g.mxy(name)
        return mx * XT + x - 1, my * YT + y - 1
    town = T.Town("Southport", "Southport", g, cell("1,3,0", 16, 13), STYLES["brick"], True, seed=77)
    stops = T.cart_stops(town, [("the market", cell("1,3,0", 16, 13)), ("the west quarter", cell("0,4,0", 13, 8)),
                                ("the north quarter", cell("0,2,0", 13, 14))])
    town.write()
    g.save()
    print("Southport: %d cart stops%s" % (len(stops), ("; no room for: " + ", ".join(town.missed)) if town.missed
                                          else ""))


if __name__ == "__main__":
    main()
