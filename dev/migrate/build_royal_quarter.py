"""Galaith's Royal quarter made busy (the owner's wish): the palace has three storeys now, and the courtyard round it is a
working household, not an empty square of paving.

  * The palace (-10,14): the throne hall stays exactly as it was (its Ids, its door's Lock, the King and his guards, so
    the story's scenes are where they were). From it a stair goes down at (2,2) and the King's own stair up at (18,2).
    Down (-10,14,-1): the kitchens (two ranges, the cook), the servants' hall, the larder and the wine cellar. Up
    (-10,14,1): the solar (the court painter at his easel), Queen Mary's chamber (kept as she left it), the nursery, and
    the King's bedchamber. The palace's roof has the upper storey's front in it now.
  * The courtyard: the servants' quarters and the guards' lodgings down its west side (-11,14), the royal stables with
    a riding yard below them and a farrier's anvil beside them (-10,14 and -10,15), kennels for the royal hounds (-11,15),
    a drill yard with a well (-10,15), and gardens either side of the palace (-10,13, -10,14). Everyone in it has a bed,
    or stands a watch that never sleeps (guards, the cook).
  * The named folk have their own words (Talk to <Id>), never a hint.

Builds on the maps as they are (the owner's edits kept): only plain royal paving is built over, and what's built is laid
once (dev\\migrate\\.royal_quarter_built). Pictures, data and scripts are written every run.

  python -I "dev\\migrate\\build_royal_quarter.py"   (then build_minimaps.py, export_web_assets.py, validate.py)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_kit as SK                                   # noqa: E402
from story_kit import Map, obj_line, say                  # noqa: E402
import villages as V                                     # noqa: E402
from common import p                                     # noqa: E402

MAKER = "build_royal_quarter.py"
DONE = p("dev", "migrate", ".royal_quarter_built")
PALACE = "-10,14,0"
CELLAR = "-10,14,-1"
UPPER = "-10,14,1"
X1, Y1, X2, Y2 = 1, 1, 19, 8                              # (the palace's walls; its front, row 8, with the door at 10)
DOWN, UP = (2, 2), (18, 2)
PAVING = "Royal_Paving001"
EDGES = ["N", "E", "S", "W", "NE", "SE", "SW", "NW", "+NE", "+SE", "+SW", "+NW", "NS", "EW", "NES", "ESW", "NSW", "NEW"]


def thin(floor, edges):
    """The thin wall tile for a stone room's floor cell with walls on those edges (house_tiles THIN_EDGES)."""
    base = {"Flagstone001": "Flag", "Marble001": "Marble", "Plank001": "Plank"}[floor]
    order = "".join(e for e in "NESW" if e in edges)
    name = {"N": "N", "E": "E", "S": "S", "W": "W", "NE": "NE", "ES": "SE", "SW": "SW", "NW": "NW", "NS": "NS",
            "EW": "EW", "NES": "NES", "ESW": "ESW", "NSW": "NSW", "NEW": "NEW"}.get(order)
    if not order:
        return floor
    tile = "Stone_Wall_Thin_%s%03d" % (base, EDGES.index(name) + 1)
    assert os.path.exists(p("sprites", "Tiles", tile + ".png")), tile
    return tile


def lay_rooms(m, floor, rooms, doors, south_wall):
    """Rooms (x1, y1, x2, y2), side by side: each cell's thin walls where it meets another room or the outside, except
    through doors (pairs of cells). south_wall: the row below the rooms is a solid front wall (no south edge drawn)."""
    owner = {}
    for i, (a, b, c, d) in enumerate(rooms):
        for y in range(b, d + 1):
            for x in range(a, c + 1):
                owner[(x, y)] = i
    open_ = {frozenset(pr) for pr in doors}
    for (x, y), i in owner.items():
        edges = ""
        for e, (dx, dy) in (("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("W", (-1, 0))):
            n = (x + dx, y + dy)
            if owner.get(n) == i or frozenset(((x, y), n)) in open_:
                continue
            if e == "S" and south_wall and n not in owner:
                continue
            edges += e
        m.put(x, y, thin(floor, edges), {})


# ================================================================== the palace's three storeys
def palace():
    hall = Map(PALACE)
    hall.set(*DOWN, tile="Stairs002")
    hall.set(*UP, tile="Stairs001")
    # (the upper storey's front in the roof's group, over the hall's last row: gone when you're inside, as a house's is)
    spec = V.roof_spec("Slate", "Stone_Wall001", -1, [])
    groups = {c.split("Roof(")[1].split(")")[0].split(".")[1] for c in hall.rows[Y2 - 2] if "Roof(" in c}
    g = sorted(groups)[0] if groups else "21"
    for x in range(X1, X2 + 1):
        piece = V.roof_piece(spec, x, Y2 - 1, X1, Y1, X2, Y2 - 1)
        hall.set(x, Y2 - 1, roof="%s.%s" % (piece, g))
    hall.save()

    # ----- the cellars: kitchens, servants' hall, larder, wine cellar
    m = SK.black_map(CELLAR)
    m.rows = [["Black001"] * 25 for _ in range(21)]
    rooms = [(1, 1, 7, 8), (8, 1, 12, 8), (13, 1, 15, 8), (16, 1, 19, 8)]
    doors = [((7, 6), (8, 6)), ((7, 7), (8, 7)), ((12, 7), (13, 7)), ((15, 7), (16, 7))]
    lay_rooms(m, "Flagstone001", rooms, doors, south_wall=False)
    m.set(*DOWN, tile="Stairs001")
    for x, y, dec in ((1, 4, "Side_Shelf_W001"), (3, 1, "Barrel002"), (5, 4, "Cauldron001"), (4, 6, "Table001"),
                      (5, 6, "Table001"), (6, 1, "Herb_Rack001"), (7, 8, "Barrel001"), (1, 8, "Sacks001"),
                      # (the servants' hall)
                      (9, 3, "Dining_Table001"), (10, 3, "Dining_Table001"), (11, 3, "Dining_Table001"), (9, 4, "Bench001"),
                      (10, 4, "Bench001"), (11, 4, "Bench001"), (10, 1, "Long_Clock001"), (12, 1, "Cupboard001"),
                      (8, 1, "Wall_Shelf001"),
                      # (the larder)
                      (13, 1, "Shelf_Goods001"), (14, 1, "Shelf_Goods001"), (15, 1, "Shelf_Goods001"), (13, 4, "Sacks001"),
                      (15, 4, "Fruit_Crate001"), (13, 6, "Fish_Barrel001"), (15, 8, "Herb_Rack001"),
                      # (the wine cellar)
                      (16, 1, "Cellar_Barrel001"), (17, 1, "Cellar_Barrel001"), (18, 1, "Cellar_Barrel001"),
                      (19, 1, "Cellar_Barrel001"), (19, 3, "Cellar_Barrel001"), (19, 5, "Cellar_Crate001"),
                      (17, 4, "Cellar_Barrel001"), (18, 4, "Cellar_Barrel001"), (19, 8, "Cellar_Crate001")):
        m.set(x, y, decor=dec)
    m.ents = [obj_line("StaticObject", "Range", 4, 1, "Id=Palace_Range_1"),
              obj_line("StaticObject", "Range", 5, 1, "Id=Palace_Range_2"),
              obj_line("NPC", "Baker", 4, 3, "Attitude=Good Zone=2,2,6,7 Pause=4-10 Schedule=Always Id=Palace_Cook "
                                         "Name=Mrs_Brisket", dy=-8),
              obj_line("NPC", "Barmaid", 10, 6, "Attitude=Good Zone=2,5,14,7 Pause=4-10 Schedule=Always Id=Palace_Scullion "
                                              "Name=Polly", dy=-8),
              "Id\tPalace_Kitchens\t4\t4", "Id\tPalace_Wine_Cellar\t17\t6"]
    m.save()

    # ----- upstairs: the solar, Queen Mary's chamber, the nursery, the King's bedchamber
    u = SK.black_map(UPPER)
    u.rows = [["Black001"] * 25 for _ in range(21)]
    rooms = [(1, 1, 5, 6), (6, 1, 9, 6), (10, 1, 12, 6), (13, 1, 19, 6)]
    doors = [((5, 5), (6, 5)), ((5, 6), (6, 6)), ((9, 6), (10, 6)), ((12, 6), (13, 6)), ((12, 5), (13, 5))]
    lay_rooms(u, "Marble001", rooms, doors, south_wall=True)
    for x in range(X1, X2 + 1):                            # (its front: under the eaves, windows every other column)
        u.put(x, Y2 - 1, "Stone_Wall001", {"Decor": V.window_tile("Stone_Wall001") if V.upper_window(x, X1, X2) else ""})
    u.set(*UP, tile="Stairs002")
    for x, y, dec in ((2, 1, "Bookshelf001"), (3, 1, "Writing_Desk001"), (4, 1, "Bookshelf001"),
                      (1, 3, "Side_Picture_W001"), (5, 3, "Chair001"), (3, 4, "~Rug001"),
                      # (Queen Mary's chamber, as she left it)
                      (7, 1, "Bed001"), (7, 2, "Bed002"), (9, 1, "Dresser001"), (6, 1, "Mirror001"), (8, 4, "Woven_Rug001"),
                      (9, 3, "Wardrobe001"),
                      # (the nursery)
                      (11, 1, "Bed003"), (12, 1, "Bed004"), (10, 3, "~Rug002"), (12, 4, "Cupboard001"),
                      # (the King's bedchamber)
                      (15, 1, "Double_Bed001"), (16, 1, "Double_Bed002"), (15, 2, "Double_Bed003"), (16, 2, "Double_Bed004"),
                      (13, 1, "Potted_Plant002"), (17, 1, "Long_Clock001"), (19, 3, "Side_Dresser_E001"),
                      (14, 4, "~Rug003"), (17, 5, "Writing_Desk002"), (13, 4, "Wardrobe001"), (19, 1, "Banner001")):
        if dec.startswith("~"):                            # (a rug: under whatever stands there)
            t, over = u.parts(x, y)
            over["Under"] = dec[1:]
            u.put(x, y, t, over)
        else:
            u.set(x, y, decor=dec)
    u.ents = [obj_line("StaticObject", "Royal_Easel", 3, 3, "Id=Court_Easel"),
              obj_line("NPC", "Painter", 4, 4, "Attitude=Good Stand=1 Face=W Schedule=Always Id=Court_Painter "
                                             "Name=Master_Corin", dy=-8),
              obj_line("NPC", "Nurse", 11, 4, "Attitude=Good Zone=10,2,12,6 Pause=8-20 Schedule=Always Id=Nurse_Agnes "
                                            "Name=Old_Agnes", dy=-8),
              "Id\tQueen_Marys_Bed\t7\t1", "Id\tRoyal_Cot\t11\t1", "Id\tKings_Bedchamber\t16\t4",
              "Id\tPalace_Solar\t3\t5"]
    u.save()
    print("The palace: cellars on %s, the royal floor on %s" % (CELLAR, UPPER))


# ================================================================== the courtyard
def free(m, x1, y1, x2, y2):
    """Every cell plain royal paving, nothing standing on it."""
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            if m.rows[y - 1][x - 1] != PAVING:
                return False
    for ln in m.ents:
        f = ln.split("\t")
        if f[0] in ("NPC", "StaticObject", "MapItem") and len(f) >= 4:
            tx, ty = int(float(f[2])) // 32 + 1, (int(float(f[3])) + 16) // 32 + 1
            if x1 - 1 <= tx <= x2 + 1 and y1 - 1 <= ty <= y2 + 1:
                return False
    return True


def clear(m, x1, y1, x2, y2):
    """Lamps and benches and such standing where a building goes (the paving's own decor) lifted off it."""
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            c = m.rows[y - 1][x - 1]
            if c.startswith(PAVING) and "Roof(" not in c:
                m.rows[y - 1][x - 1] = PAVING


def deco(m, x, y, name):
    if m.rows[y - 1][x - 1] in (PAVING, "Plank001", "Flagstone001", "Marble001") or "_Thin_" in m.rows[y - 1][x - 1]:
        m.set(x, y, decor=name)


def house(m, x1, y1, x2, y2, door, roof="Slate"):
    clear(m, x1, y1, x2, y2)
    if not free(m, x1, y1, x2, y2):
        print("Something stands in the way at %s %d,%d-%d,%d: built anyway over the paving" % (m.name, x1, y1, x2, y2))
    SK.building(m, x1, y1, x2, y2, door=door, wall="Stone_Wall001", roof=roof, chimney=x1 + 2)


def west_side():
    """The servants' quarters and the guards' lodgings (-11,14)."""
    m = Map("-11,14,0")
    # (the servants' quarters: a dormitory, the steward's room at its east end)
    house(m, 13, 2, 23, 9, door=17)
    SK.partition(m, 19, 3, 8, gaps=(7, 8))
    for x in (14, 16, 18):
        m.set(x, 2, decor="Bed001")
        m.set(x, 3, decor="Bed002")
    m.set(21, 2, decor="Bed001")
    m.set(21, 3, decor="Bed002")
    for x, y, dec in ((15, 6, "Table001"), (16, 6, "Chair001"), (14, 8, "Wardrobe001"), (22, 2, "Writing_Desk001"),
                      (23, 5, "Side_Cupboard_E001"), (13, 5, "Side_Picture_W001"), (18, 8, "Washstand001")):
        deco(m, x, y, dec)
    m.ents.append(obj_line("StaticObject", "Valuables", 22, 7))
    home = "Home=14,3,18,8 "
    for x, y, kind, pid, name, bed, zone in ((15, 11, "Barmaid", "Palace_Maid_Ada", "Ada", "14,2", "12,10,25,21"),
                                             (19, 12, "Woman", "Palace_Maid_Joan", "Joan", "16,2", "12,10,25,21"),
                                             (21, 11, "Woman", "Palace_Laundress", "Hettie", "18,2", "12,10,25,13")):
        m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Good Zone=%s Pause=4-12 Id=%s Name=%s %sBed=%s" % (
            zone, pid, name, home, bed), dy=-8))
    m.ents.append(obj_line("NPC", "Manor_Steward", 22, 11, "Attitude=Good Zone=20,10,25,13 Pause=6-14 Id=Royal_Steward "
                                                          "Name=Pemberton Home=20,3,22,8 Bed=21,2", dy=-8))
    m.ents.append("Id\tServants_Quarters\t17\t6")
    # (the guards' lodgings: bunks, the sergeant's table, armour in crates)
    house(m, 13, 13, 23, 20, door=18)
    for x in (14, 16, 18, 20, 22):
        m.set(x, 13, decor="Bed001")
        m.set(x, 14, decor="Bed002")
    for x, y, dec in ((15, 17, "Table001"), (16, 17, "Table001"), (15, 18, "Bench001"), (16, 18, "Bench001"),
                      (13, 16, "Side_Shelf_W001"), (23, 16, "Side_Cupboard_E001"), (21, 19, "Crate001"),
                      (22, 19, "Crate002"), (14, 19, "Barrel001")):
        deco(m, x, y, dec)
    m.ents.append(obj_line("NPC", "Quartermaster", 19, 17, "Attitude=Good Zone=17,16,22,19 Pause=6-14 Schedule=Always "
                                                          "Id=Royal_Sergeant Name=Sergeant_Brannock", dy=-8))
    m.ents.append(obj_line("NPC", "Royal_Guard", 14, 16, "Attitude=Good Zone=14,15,18,19 Pause=8-20 Schedule=Always "
                                                        "Name=Royal_Guard", dy=-8))
    m.ents.append("Id\tGuards_Lodgings\t18\t17")
    m.save()

    # (the kennels below them: a pen of fence, straw, the royal hounds)
    k = Map("-11,15,0")
    clear(k, 13, 1, 20, 6)
    for x in range(13, 21):
        for y in (1, 6):
            deco(k, x, y, "Wood_Fence001")
    for y in range(2, 6):
        deco(k, 13, y, "Wood_Fence002")
        deco(k, 20, y, "Wood_Fence002")
    k.set(17, 6, decor="")                                  # (its gate, open)
    deco(k, 15, 2, "Haystack001")
    deco(k, 18, 2, "Barrel001")
    for x, y, name in ((15, 4, "Bramble"), (18, 4, "Sable")):
        k.ents.append(obj_line("NPC", "Dog", x, y, "Attitude=Good Zone=14,2,19,5 Home=14,2,19,5 Schedule=Always "
                                                   "Name=%s" % name, dy=-8))
    k.ents.append(obj_line("NPC", "Royal_Guard", 22, 3, "Attitude=Good Zone=21,1,25,7 Pause=6-16 Schedule=Always "
                                                       "Name=Royal_Guard", dy=-8))
    k.ents.append("Id\tRoyal_Kennels\t16\t3")
    k.save()


def south_side():
    """The royal stables, the farrier, the riding yard and the drill yard (-10,14 and -10,15)."""
    m = Map(PALACE)
    # (the stables: stalls of fence, a loft at the west end where the grooms sleep)
    house(m, 1, 15, 14, 21, door=8)
    SK.partition(m, 4, 16, 20, gaps=(19, 20))
    for x in (2, 3):
        m.set(x, 15, decor="Bed001")
        m.set(x, 16, decor="Bed002")
    deco(m, 2, 19, "Chair001")
    stalls = [(6, 7), (9, 10), (12, 13)]
    for a, b in stalls:
        for y in (18,):
            deco(m, a, y, "Wood_Fence001")
            deco(m, b, y, "Wood_Fence001")
        if b < 14:
            for y in (15, 16, 17):
                deco(m, b + 1, y, "Wood_Fence002")
    for x, y, dec in ((5, 15, "Haystack001"), (14, 20, "Sacks001"), (5, 20, "Barrel001")):
        deco(m, x, y, dec)
    for (a, b), (look, name) in zip(stalls, (("Royal_Horse", "Thunder"), ("Royal_Horse_Black", "Midnight"),
                                             ("Royal_Horse", "Bellflower"))):
        m.ents.append(obj_line("NPC", look, a, 16, "Attitude=Good Zone=%d,15,%d,17 Home=%d,15,%d,17 Schedule=Always "
                                                   "Name=%s" % (a, b, a, b, name), dy=-8))
    m.ents.append(obj_line("NPC", "Carter", 9, 19, "Attitude=Good Zone=5,19,13,20 Pause=4-10 Id=Royal_Groom Name=Will "
                                                  "Home=2,16,3,20 Bed=2,15", dy=-8))
    m.ents.append("Id\tRoyal_Stables\t8\t19")
    # (the farrier's anvil, out in the air beside them)
    clear(m, 17, 16, 21, 19)
    m.ents.append(obj_line("StaticObject", "Anvil", 18, 17, "Id=Royal_Anvil"))
    deco(m, 20, 16, "Barrel001")
    deco(m, 21, 16, "Crate001")
    m.ents.append(obj_line("NPC", "Blacksmith", 19, 18, "Attitude=Good Zone=17,17,21,19 Pause=4-10 Id=Royal_Farrier "
                                                       "Name=Osric Home=2,16,3,20 Bed=3,15", dy=-8))
    # (the gardens east of the palace)
    for x, y, dec in ((21, 1, "Flower_Bed001"), (22, 1, "Flower_Bed001"), (23, 1, "Flower_Bed001"), (24, 1, "Flower_Bed001"),
                      (21, 3, "Potted_Plant002"), (21, 4, "Potted_Plant003"),
                      (21, 5, "Potted_Plant002"), (24, 3, "Flower_Urn001"),
                      (24, 6, "Flower_Urn001"), (23, 4, "Bench001"), (25, 2, "Flowers002"), (25, 5, "Flowers001")):
        if m.rows[y - 1][x - 1] == PAVING:
            m.set(x, y, decor=dec)
    m.ents.append(obj_line("NPC", "Farmer", 23, 2, "Attitude=Good Zone=21,1,25,7 Pause=6-14 Schedule=Day Id=Royal_Gardener "
                                                  "Name=Silas Home=2,16,3,20 Bed=2,15", dy=-8))
    m.ents.append(obj_line("NPC", "Courier", 20, 11, "Attitude=Good Zone=11,9,24,13 Pause=1-4 Schedule=Day "
                                                    "Id=Royal_Messenger Name=Robin Home=2,16,3,20 Bed=3,15", dy=-8))
    for x in (16, 22):                                     # (the guard down the way to the door)
        m.ents.append(obj_line("NPC", "Royal_Guard", x, 9, "Attitude=Good Stand=1 Face=S Schedule=Always Name=Royal_Guard",
                               dy=-8))
    m.save()

    s = Map("-10,15,0")
    # (the riding yard, fenced, below the stables)
    clear(s, 1, 2, 12, 6)
    for x in range(1, 13):
        deco(s, x, 2, "Wood_Fence001")
        deco(s, x, 6, "Wood_Fence001")
    for y in range(3, 6):
        deco(s, 12, y, "Wood_Fence002")
    s.set(8, 2, decor="")                                   # (its gate from the stable door)
    deco(s, 3, 3, "Haystack001")
    deco(s, 10, 5, "Barrel001")
    for x, look, name in ((5, "Royal_Horse_Black", "Ember"), (9, "Royal_Horse", "Gallant")):
        s.ents.append(obj_line("NPC", look, x, 4, "Attitude=Good Zone=2,3,11,5 Home=2,3,11,5 Schedule=Always "
                                                  "Name=%s" % name, dy=-8))
    s.ents.append("Id\tRoyal_Riding_Yard\t6\t4")
    # (the drill yard: a well, benches, guards at their practice)
    clear(s, 15, 1, 24, 7)
    deco(s, 20, 3, "Well001")
    deco(s, 16, 1, "Bench001")
    deco(s, 23, 1, "Bench001")
    for x, y in ((17, 4), (19, 5), (22, 4)):
        s.ents.append(obj_line("NPC", "Royal_Guard", x, y, "Attitude=Good Zone=15,2,24,6 Pause=2-6 Schedule=Always "
                                                          "Name=Royal_Guard", dy=-8))
    s.ents.append("Id\tRoyal_Drill_Yard\t20\t5")
    s.save()

    n = Map("-10,13,0")
    # (the north garden behind the palace: a walk of urns and flower beds, a lady and a lord taking the air)
    for x in range(2, 20, 3):
        deco(n, x, 18, "Flower_Bed001")
        deco(n, x + 1, 18, "Flower_Urn001")
    for x in (5, 11, 17):
        deco(n, x, 20, "Bench001")
    n.ents.append(obj_line("NPC", "Woman", 7, 19, "Attitude=Good Zone=2,19,19,20 Pause=6-16 Schedule=Day Id=Lady_Ellery "
                                                 "Name=Lady_Ellery Look=2", dy=-8))
    n.ents.append(obj_line("NPC", "Merchant", 14, 19, "Attitude=Good Zone=2,19,19,20 Pause=6-16 Schedule=Day Id=Lord_Ashby "
                                                     "Name=Lord_Ashby", dy=-8))
    n.save()
    print("The courtyard: quarters, lodgings, stables, kennels, yards and gardens")


# ================================================================== data, pictures and words
def data():
    from PIL import Image
    import numpy as np
    for src, dst, col in (("Horse", "Royal_Horse", (236, 232, 222)), ("Horse", "Royal_Horse_Black", (70, 64, 66))):
        import glob
        for path in [p("sprites", "Entities", src + ".png")] + glob.glob(p("sprites", "Walk", src + "[1248][abc].png")):
            if not os.path.exists(path):
                continue
            a = np.array(Image.open(path).convert("RGBA"), dtype=np.float32)
            lum = a[..., 0] * 0.3 + a[..., 1] * 0.59 + a[..., 2] * 0.11
            body = (a[..., 0] > a[..., 2] + 18) & (lum > 50)          # (its brown coat, not its tack or outline)
            k = np.clip(lum / 150.0, 0, 1.3)[..., None]
            a[..., :3] = np.where(body[..., None], np.array(col)[None, None, :] * k, a[..., :3])
            folder = "Entities" if "Entities" in path else "Walk"
            name = dst + os.path.basename(path)[len(src):-4]
            from common import write_image
            write_image(p("sprites", folder, name + ".png"), Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA"))
    for name, words in (("Royal_Horse", "A royal charger, groomed till it shines. It looks at you as if you might be an apple."),
                        ("Royal_Horse_Black", "A black royal charger with a white blaze, and opinions.")):
        SK.section(SK.ENTS, name, [("Type", "NPC"), ("Attitude", "Good"), ("Use.Words", "Stroke,Examine"),
                                   ("Examine.Info", words), ("Roam.Radius", "1"), ("Chase.Radius", "0"),
                                   ("Movement.Speed", "0.8"), ("Walk.Speed", "0.3"), ("Pause", "6-18"), ("Respawn", "300"),
                                   ("Level", "3"), ("Schedule", "Always")])
    SK.section(SK.ENTS, "Royal_Easel", [("Type", "StaticObject"), ("Use.Words", "Examine"),
                                        ("Walkable.Data", "1111111111111111000111100011110001111000111100011"),
                                        ("Examine.Info", "The King, half painted. He's in it twice: the painter hasn't "
                                         "decided which one stays.")])
    for name in ("Royal_Easel",):
        SK.copy_sprite("Entities", "Easel", name)
    for place, words in (("Queen_Marys_Bed", "Queen Mary's bed, made up fresh every morning for twenty years. Nobody has "
                                             "slept in it."),
                         ("Royal_Cot", "A royal cot, carved with little dragons. Every heir of Galaith slept in it, for a "
                                       "while."),
                         ("Kings_Bedchamber", "The King's bedchamber: a great bed, a cold hearth, and a window over the "
                                              "boulevard to the east gate.")):
        SK.write_script("Examine %s" % place, [("Display.Message", "Cyan", words, "-"), ("End",)], MAKER)
    for horse in ("Royal_Horse", "Royal_Horse_Black"):
        SK.write_script("Stroke %s" % horse, [
            (">Distance.From.Clicked.Entity", "48", "@far"),
            (">Random", "50", "@b"),
            ("Display.Message", "Cyan", "You stroke its nose. It leans into your hand, and then checks your pockets.", "-"),
            ("End",),
            ("@b",), ("Display.Message", "Cyan", "It whickers softly and goes back to its hay.", "-"), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    words = {   # Id: (sprite, three things they might say, what they say to the crowned)
        "Palace_Cook": ("Baker", ["Out of my kitchen unless you're carrying onions.",
                                  "Forty years I've cooked for this palace, and twenty of them for nobody. Now there's "
                                  "a king to feed again and I can't find the big pans.",
                                  "Taste that. No, don't, it's for the King. Well. A little."],
                        "Your Majesty! In my kitchen! Sit, sit. You're too thin. Everyone's too thin."),
        "Palace_Scullion": ("Barmaid", ["The cellar's colder than a fish's handshake. Mind the third step.",
                                        "Mrs Brisket says I'm to scrub till I can see my face. I can see my face. It's "
                                        "tired.", "There's a barrel down there nobody's allowed to open. I've not "
                                        "opened it. Twice."], "Your Majesty! Sorry! I'll get out of the way!"),
        "Court_Painter": ("Painter", ["Hold still. No, not you. The light.",
                                      "A king, they told me, paint a king. Which way does a king face? Left, for "
                                      "wisdom? Right, for valour? I've done both. Now there are two of him.",
                                      "Twenty years nobody wanted a portrait in this palace. Now everybody does."],
                          "Your Majesty: would you turn a little to the light? A little more. Perfect. Don't breathe."),
        "Nurse_Agnes": ("Nurse", ["I nursed every royal child born in this palace for forty years. Every one of them.",
                                  "The cot's kept aired. I keep it aired. Somebody has to.",
                                  "Mind the rug. The little ones used to slide on it."],
                        "Look at you. Look at you. I'd have known you anywhere, you know. You have her chin."),
        "Royal_Steward": ("Manor_Steward", ["The silver is counted, the linen is folded, and the cook is shouting. All is "
                                            "as it should be.", "A household of forty, and I am the only one who knows "
                                            "where the candles are kept. It is a heavy burden.",
                                            "Please don't walk on the paving with mud on your boots. Ever."],
                          "Your Majesty. The household is at your service. The candles are in the second cupboard."),
        "Palace_Maid_Ada": ("Barmaid", ["Morning! Or is it? I've been up since it was yesterday.",
                                        "Twelve beds to make, and the King's makes itself, he's that tidy.",
                                        "If you see a cat on the throne, it's not mine."], "Your Majesty! I'll curtsey. "
                                                                                         "There. Did I do it right?"),
        "Palace_Maid_Joan": ("Woman", ["Lord Ashby wants his shirts starched. Lord Ashby can starch his own shirts.",
                                       "The garden's lovely this time of year. Every time of year. The gardener sees to "
                                       "that.", "I've worked here four years and I've never once been in the cellar. "
                                                "Polly says it's haunted. Polly says everything's haunted."],
                             "Your Majesty. Will you be wanting anything? Only I'm carrying all this."),
        "Palace_Laundress": ("Woman", ["Sheets, sheets, sheets. Royal people do sleep a great deal.",
                                       "Don't touch the line, the shirts are drying.",
                                       "Twenty years we washed for an empty palace. Kept it ready. You never know."],
                             "Your Majesty. Your shirts are drying. They're very nice shirts."),
        "Royal_Sergeant": ("Quartermaster", ["Boots by the bunk, blades on the rack, and no dice after the bell.",
                                             "The Royal Guard stood at a locked door for twenty years. Kept us sharp, "
                                             "the captain says. Kept us bored, I say.",
                                             "You want to drill with the lads? Mind the big one. He doesn't know his own "
                                             "strength. Neither does his mother."],
                           "Your Majesty! Guard, ATTEN-tion! ...Well. Those that are awake."),
        "Royal_Groom": ("Carter", ["Thunder bites. Midnight kicks. Bellflower does both, but sweetly.",
                                   "I sleep up in the loft with the smell of hay. Best bed in Galaith.",
                                   "Royal horses. They eat better than I do. They're prettier, too."],
                        "Your Majesty! They're all saddled, if you want a ride. Well. Thunder isn't. Thunder never is."),
        "Royal_Farrier": ("Blacksmith", ["Shoes for the horses, buckles for the guard, and a pot for the cook when she "
                                         "throws one.", "Hold that hoof. No, the other one. No, the horse's.",
                                         "Iron's iron, whoever's king. But it's good to have a king again."],
                          "Your Majesty. I'll shoe your horse, mend your mail and say nothing of either."),
        "Royal_Gardener": ("Farmer", ["Roses don't care who's king. They just want feeding.",
                                      "Kept these beds for an empty palace twenty years. Looks like I did it for "
                                      "somebody after all.", "Mind the hedge. I've just cut it straight."],
                           "Your Majesty. The roses are blooming for you. Well, they'd bloom anyway. But for you."),
        "Royal_Messenger": ("Courier", ["Can't stop! Letters for the Chancellor! Then letters from the Chancellor!",
                                        "I've run this courtyard nine times today. I counted.",
                                        "Did you know there are a hundred and twelve flagstones from the gate to the "
                                        "door? I've had time to count."],
                            "Your Majesty! A letter for you! Oh. No. It's for the cook. Sorry!"),
        "Lady_Ellery": ("Woman", ["The court's coming back to life. Slowly. Like a cold hand.",
                                  "Lord Ashby says the roses are vulgar. Lord Ashby says most things are vulgar.",
                                  "Twenty years at our country house waiting for the barrier to fall. I've seen enough "
                                  "of the country to last me."], "Your Majesty. You honour the garden. It's been dull "
                                                                 "without honour."),
        "Lord_Ashby": ("Merchant", ["The roses are vulgar. Don't tell the gardener.",
                                    "In my father's day there were balls in this courtyard. Now there are horses.",
                                    "One hears the most extraordinary things about the new heir. One hopes some of them "
                                    "are true."], "Your Majesty. Delighted. Truly. Have you considered a ball?"),
    }
    for pid, (sprite, lines, king) in words.items():
        rows = [(">Conditional", "$Attr.KingQuest>=1", "@talk"), ("Display.Conversation", sprite, king, "Goodbye.", "@end"),
                ("End",), ("@talk",), (">Random", "34", "@two"),
                ("Display.Conversation", sprite, lines[0], "Goodbye.", "@end"), ("End",),
                ("@two",), (">Random", "50", "@three"),
                ("Display.Conversation", sprite, lines[1], "Goodbye.", "@end"), ("End",),
                ("@three",), ("Display.Conversation", sprite, lines[2], "Goodbye.", "@end"), ("@end",), ("End",)]
        SK.write_script("Talk to %s" % pid, rows, MAKER)
    for label, where in (("The Royal Stables", "Royal_Stables"), ("The Servants' Quarters", "Servants_Quarters"),
                         ("The Guards' Lodgings", "Guards_Lodgings")):
        SK.place_label("Places", label, where)


def join_fences():
    """The pens' and yards' fences joined at their corners: each fence cell's piece by which of its neighbours are fence
    too (Tiles.ini Joins=). Safe to run again."""
    from ashen import ini
    pieces = {}
    for i in range(1, 13):
        name = "Wood_Fence%03d" % i
        j = ini.read(name, "Joins", "", SK.TILES)
        if j:
            pieces.setdefault(frozenset(j), name)
    for name, box in (("-11,15,0", (13, 1, 20, 6)), ("-10,14,0", (1, 15, 14, 21)), ("-10,15,0", (1, 2, 12, 6))):
        m = Map(name)
        x1, y1, x2, y2 = box
        fence = {(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1) if m.decor(x, y).startswith("Wood_Fence")}
        for x, y in fence:
            j = frozenset(d for d, (dx, dy) in (("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("W", (-1, 0)))
                          if (x + dx, y + dy) in fence)
            want = pieces.get(j) or (pieces[frozenset("NS")] if j & set("NS") and not j & set("EW") else pieces[frozenset("EW")])
            m.set(x, y, decor=want)
        m.save()


def main():
    data()
    join_fences()
    if os.path.exists(DONE):
        print("The Royal quarter is built already (delete %s to build it again)" % DONE)
        return
    palace()
    west_side()
    south_side()
    open(DONE, "w").write("built\n")


if __name__ == "__main__":
    main()
