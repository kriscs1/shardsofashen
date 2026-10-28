"""Galaith, Ashen's capital, on the far east of the mainland (maps 10,5,0 to 14,7,0), and the way to it. Run it
again: it draws the same, and leaves the maps it has made alone.

  python -I "dev\\migrate\\build_galaith.py"     (then smooth_coasts.py, validate.py, build_minimaps.py)

  * The way: a stone causeway from the Elderwood's east shore (9,6,0) to a mountain range (10,5,0 and 10,7,0 are
    peaks) with a gap in it, the pass (10,6,0). Across the gap the dragon's barrier: violet light, a Lock on each of
    its cells (GalaithQuest>=1, Bert's spell cast with the staff); open, it's a faint shimmer (Unlocked.Tile).
  * Behind it the scorched ground before the city, skulls and burnt trees, and the dragon: Galaith_Dragon, black as
    a coal, its death blow only the Sword of Valour's (Entities.ini Slain.By). The city's west wall, white stone
    blackened by its fire, the gate in it shut (a Lock: GalaithQuest>=2, the dragon dead).
  * The city (11,5,0 to 14,7,0, a huge city: towns.py): walls round it, the mountains meeting again behind it, the
    mouth of the gold and Shards mine in them (14,6,-1, shut until you are king). The palace, the tallest building in
    the land, its spires over the city's north; Parliament, a City Hall and a Town Hall, a fancy hotel, two banks,
    ten taverns, the main market square with its lanes of bakers, butchers, fishmongers and greengrocers, a posh
    square with lanes of clothes and shoes, an armoury with its lane of arms and armour, barracks, a police station,
    a hospital, twenty streets of houses, gardens and parks, and carts and horses between its quarters.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_kit as K  # noqa: E402
import towns as T  # noqa: E402
from story_kit import Map, obj_line, ini  # noqa: E402

XT, YT, TW = K.XT, K.YT, K.TW
MAKER = "build_galaith.py"
PASS = "10,6,0"
CITY = ["%d,%d,0" % (x, y) for y in (5, 6, 7) for x in (11, 12, 13, 14)]
EAST = 14                            # the city's east column of maps: its wall, the mountains and the mine
BARRIER_X = 7                        # the barrier's column on the pass, rows GAP
GAP = range(6, 17)
NECK = range(10, 13)                 # (where the peaks close in, the barrier across them: three cells)
GATE = (1, 11)                       # the city's west gate on 11,6,0 (two cells: rows 11 and 12)
EAST_WALL = 21                       # the city's east wall's column on 14,*,0
NORTH_WALL = (3, 4)                  # rows of the north wall on 1x,5,0
SOUTH_WALL = (18, 19)                # rows of the south wall on 1x,7,0
PALACE = ("12,5,0", 4, 6, 22, 13)    # the palace's walls (one map)
MINE = (23, 11)                      # the mine's mouth on 14,6,0


# ================================================================== pictures
def recolour(img, fn):
    out = img.copy()
    w, h = img.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.get_at((x, y))
            if a:
                out.set_at((x, y), fn(r, g, b, x, y) + (a,))
    return out


def white_and_burnt(seed):
    """City stone turned white, then blackened with soot in streaks from below (the dragon's fire)."""
    rng = random.Random(seed)
    streaks = [(rng.randrange(32), rng.uniform(0.3, 0.9)) for _ in range(5)]

    def fn(r, g, b, x, y):
        l = (r + g + b) / 3.0
        w = min(255, int(120 + l * 0.6))
        soot = max(0.0, max(s * (1 - abs(x - sx) / 5.0) for sx, s in streaks)) * (0.4 + y / 40.0)
        soot = min(0.85, soot + (0.25 if (x * 7 + y * 3) % 11 == 0 else 0))
        v = int(w * (1 - soot))
        return (v, v, min(255, v + 4))
    return fn


def mountain(seed):
    """A rocky peak, grey with a snowy top: a tile you can't walk or see through."""
    pg = K.pg()
    rng = random.Random(seed)
    s = K.surface()
    s.fill((92, 88, 84, 255))
    for _ in range(60):
        x, y = rng.randrange(32), rng.randrange(32)
        c = rng.choice(((70, 66, 62), (110, 106, 100), (80, 76, 72)))
        pg.draw.circle(s, c + (255,), (x, y), rng.randint(1, 3))
    peak = rng.randint(8, 24)
    pts = [(0, 31), (peak - 10, 14), (peak, 3 + rng.randint(0, 4)), (peak + 9, 12), (31, 31)]
    pg.draw.polygon(s, (128, 124, 118), pts)
    pg.draw.polygon(s, (150, 146, 140), [(peak, pts[2][1]), (peak + 9, 12), (peak + 2, 31), (peak - 3, 31)])
    pg.draw.polygon(s, (238, 240, 246), [(peak - 4, 9), (peak, pts[2][1]), (peak + 4, 8), (peak + 1, 11)])
    pg.draw.lines(s, (54, 50, 48), False, pts[1:4], 1)
    return s


def barrier(k):
    """The dragon's barrier: violet light rippling over the pass's stones (frame k of 4); and, open, a faint shimmer."""
    pg = K.pg()
    s = K.surface()
    s.fill((86, 80, 92, 255))
    for y in range(32):
        for x in range(32):
            v = math.sin((y + k * 4) * 0.45 + math.sin(x * 0.3 + k) * 1.4)
            a = 0.55 + 0.35 * v
            base = s.get_at((x, y))
            c = (int(base[0] * (1 - a) + 170 * a), int(base[1] * (1 - a) + 70 * a), int(base[2] * (1 - a) + 240 * a))
            s.set_at((x, y), c + (255,))
    for i in range(6):
        x = (i * 7 + k * 5) % 32
        pg.draw.line(s, (236, 200, 255), (x, 0), (x + 2, 31), 1)
    return s


def barrier_open():
    pg = K.pg()
    s = K.surface()
    s.fill((86, 80, 92, 255))
    for i in range(8):
        pg.draw.circle(s, (190, 140, 240), ((i * 11) % 30 + 1, (i * 7) % 30 + 1), 1)
    return s


def big_dragon(src):
    """The dragon of Galaith: the dragon half as big again, its scales black as coal, its eyes and belly embers."""
    pg = K.pg()
    w, h = src.get_size()
    big = pg.transform.scale(src, (w * 3 // 2, h * 3 // 2))

    def fn(r, g, b, x, y):
        l = (r + g + b) / 3.0
        if r > 180 and g > 140 and b < 120:                       # (gold: belly and eyes) -> ember orange
            return (255, 140 + int(g / 6), 40)
        v = int(26 + l * 0.42)
        return (v, v - 4, v + 8)
    return recolour(big, fn)


def gate_west(open_):
    """A gate in a north-south wall (the city's west gate): the burnt white wall, a dark arch, doors shut or open."""
    pg = K.pg()
    s = K.load("Tiles", "Galaith_Wall002").copy()
    if open_:
        pg.draw.rect(s, (24, 20, 20), (8, 2, 16, 30))
    else:
        pg.draw.rect(s, (70, 44, 24), (8, 2, 16, 30))
        for x in (11, 16, 21):
            pg.draw.line(s, (44, 26, 14), (x, 2), (x, 31))
        for y in (8, 22):
            pg.draw.line(s, (40, 40, 44), (8, y), (23, y), 2)
    return s


def spire():
    """A palace spire: a slender white tower with a gold roof, 32 x 96, standing up out of the palace's roof."""
    pg = K.pg()
    s = K.surface(32, 96)
    pg.draw.rect(s, (226, 226, 230), (9, 30, 14, 66))
    pg.draw.rect(s, (196, 196, 204), (19, 30, 4, 66))
    for y in range(36, 92, 12):
        pg.draw.rect(s, (60, 70, 110), (14, y, 4, 6))                # windows
    pg.draw.polygon(s, (230, 186, 60), [(7, 32), (16, 2), (25, 32)])  # the gold roof
    pg.draw.polygon(s, (190, 140, 30), [(16, 2), (25, 32), (16, 32)])
    pg.draw.line(s, (240, 60, 60), (16, 2), (16, -6))
    pg.draw.polygon(s, (200, 30, 50), [(16, 0), (24, 3), (16, 6)])   # its pennant
    return K.outlined(s)


def mine_mouth():
    pg = K.pg()
    s = mountain(99).copy()
    pg.draw.ellipse(s, (16, 12, 10), (6, 8, 20, 26))
    pg.draw.rect(s, (110, 76, 40), (5, 8, 4, 24))                    # timber props
    pg.draw.rect(s, (110, 76, 40), (23, 8, 4, 24))
    pg.draw.rect(s, (130, 90, 50), (4, 6, 24, 4))
    return s


def draw_pictures():
    made = []
    for n in range(1, 6):
        made += ["Galaith_Wall%03d" % n] if K.save("Tiles", "Galaith_Wall%03d" % n, recolour(
            K.load("Tiles", "City_Wall%03d" % n), white_and_burnt(n))) else []
    for n in range(1, 5):
        K.save("Tiles", "Galaith_Gate%03d" % n, recolour(K.load("Tiles", "City_Gate%03d" % n), white_and_burnt(10 + n)))
    K.save("Tiles", "Galaith_Gate005", gate_west(False))
    K.save("Tiles", "Galaith_Gate006", gate_west(True))
    for n in range(1, 5):
        K.save("Tiles", "Mountain%03d" % n, mountain(n))
    K.save("Tiles", "Barrier001", barrier(0))
    K.save("Entities", "Barrier_Light", barrier(0))                # (the light itself rippling: an object, each
    for k in range(4):                                             # player's own until they break it)
        K.save("Entities", "Barrier_Light%d" % (k + 1), barrier(k))
        old = os.path.join(K.SPR, "Tiles", "Barrier001%d.png" % (k + 1))
        if os.path.exists(old):
            os.remove(old)
    K.save("Tiles", "Barrier_Open001", barrier_open())
    K.save("Tiles", "Mine_Mouth001", mine_mouth())
    K.save("Entities", "Palace_Spire", spire())
    K.save("Entities", "Galaith_Dragon", big_dragon(K.load("Entities", "Dragon")))
    for d in "28":
        for f in "abc":
            K.save("Walk", "Galaith_Dragon%s%s" % (d, f), big_dragon(K.load("Walk", "Dragon%s%s" % (d, f))))
    print("Pictures: the burnt white walls and gates, mountains, the barrier, the mine's mouth, the spires, the dragon")


# ================================================================== data
def data():
    T_ = K.TILES
    for n in range(1, 6):
        K.copy_tile("Galaith_Wall%03d" % n, "City_Wall%03d" % n,
                    Examine_Info="Galaith's walls: white stone once, blackened by the dragon's fire.")
    for n in range(1, 5):
        K.copy_tile("Galaith_Gate%03d" % n, "City_Gate%03d" % n, Examine_Info="The gate of Galaith, scorched black.")
    K.copy_tile("Galaith_Gate005", "City_Wall002", Walkable_Data="1" * 49, Line_of_Sight="0",
                Examine_Info="The west gate of Galaith, barred and blackened.", Unlocked_Tile="Galaith_Gate006")
    K.copy_tile("Galaith_Gate006", "City_Wall002", Walkable_Data="1" * 49, Line_of_Sight="1",
                Examine_Info="The west gate of Galaith, standing open.", Door="Gate")
    for n in range(1, 5):
        K.copy_tile("Mountain%03d" % n, "Cliff001", Walkable_Data="0" * 49, Line_of_Sight="0", Show_Name="0",
                    Examine_Info="Mountains: sheer rock and snow.", Use_Words="Examine")
    K.copy_tile("Barrier001", "Paving001", Walkable_Data="1" * 49, Show_Name="1",
                Use_Words="Examine", Examine_Info="The dragon's barrier: a wall of violet light across the pass.",
                Unlocked_Tile="Barrier_Open001", Light="70")
    keys = ini.section("Barrier001", K.TILES)                   # (its light moves on Barrier_Light, not the tile)
    if any(k.startswith("Anim.") for k, _ in keys):
        K.set_section(K.TILES, "Barrier001", ["%s=%s" % kv for kv in keys if not kv[0].startswith("Anim.")])
        ini.forget()
    K.section(K.ENTS, "Barrier_Light", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Solid", "0"),
                                        ("Anim.Frames", "4"), ("Anim.Speed", "160"), ("Light", "80"),
                                        ("Examine.Info", "The dragon's barrier: a wall of violet light across the pass.")])
    K.copy_tile("Barrier_Open001", "Paving001", Walkable_Data="1" * 49, Examine_Info="Where the barrier stood: a "
                "shimmer, and nothing more.")
    K.copy_tile("Mine_Mouth001", "Cliff001", Walkable_Data="1" * 49, Line_of_Sight="0", Use_Words="Enter,Examine",
                Examine_Info="The mouth of Galaith's mine: gold and Shards, deep in the mountain.")
    for t, rgb in [("Galaith_Wall%03d" % n, (60, 60, 64)) for n in range(1, 6)] + \
                  [("Galaith_Gate%03d" % n, (60, 60, 64)) for n in range(1, 7)] + \
                  [("Mountain%03d" % n, (120, 116, 110)) for n in range(1, 5)] + \
                  [("Barrier001", (170, 70, 240)), ("Barrier_Open001", (120, 110, 130)), ("Mine_Mouth001", (30, 24, 20))]:
        K.minimap_colour(t, rgb)
    K.section(K.ENTS, "Galaith_Dragon", [
        ("Type", "NPC"), ("Attitude", "Bad"), ("Use.Words", "Attack,Examine"),
        ("Examine.Info", "The dragon of Galaith: black as a coal, eyes like a forge, the curse of your house."),
        ("Hitpoints", "420"), ("Attack.Speed", "1.4"), ("Strength", "12"), ("Defence", "13"), ("Aggro.Range", "300"),
        ("Weapon.Range", "190"), ("Movement.Speed", "1.6"), ("Aggressive", "1"), ("Respawn", "1800"),
        ("Drops", "Gold_Coin(s),300-500,100 Dragon_Scale,5-8,100 Ruby,1-2,100 Bones,1-1,100"),
        ("Roam.Radius", "3"), ("Chase.Radius", "6"), ("Walk.Speed", "0.4"), ("Pause", "3-8"),
        ("Missile", "Dragon_Fire_Missile"), ("Missile.Impact", "Fire_Burst"), ("Missile.Sound", "SpellFire"),
        ("Kill.Sound", "Dragon"), ("On.Hit", "Burn 50"), ("Slain.By", "Sword_of_Valour")])
    K.section(K.ENTS, "Palace_Spire", [("Type", "StaticObject"), ("Use.Words", "Examine"), ("Layer", "Over"),
                                       ("Solid", "0"), ("Examine.Info", "A spire of the palace of Galaith.")])
    amb = os.path.join(K.DATA, "Ambient.ini")
    for n in [PASS, "10,5,0", "10,7,0"]:
        ini.write("Maps", n, "Wind", amb)
    K.place_label("Towns", "Galaith", "Galaith_Market_Square")
    K.place_label("Regions", "The Pass of Galaith", "%s 4 4" % PASS)
    print("Data: the walls, gates, mountains and barrier; the dragon of Galaith (only the Sword of Valour kills it)")


# ================================================================== the land
def peaks(m, cells, rng):
    for x, y in cells:
        m.put(x, y, "Mountain%03d" % rng.randint(1, 4), {})


def mountains_and_pass():
    if K.map_exists(PASS):
        return False
    rng = random.Random(1066)
    for name in ("10,5,0", "10,7,0"):
        m = Map(name, new=True)
        peaks(m, [(x, y) for y in range(1, YT + 1) for x in range(1, XT + 1)], rng)
        m.save()
    p = Map(PASS, new=True)
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if y not in GAP or x in (BARRIER_X - 1, BARRIER_X) and y not in NECK:
                p.put(x, y, "Mountain%03d" % rng.randint(1, 4), {})
            elif x < BARRIER_X:
                p.put(x, y, "Paving001" if y in (11, 12) else "Dirt001", {})
            elif x == BARRIER_X:
                p.put(x, y, "Barrier001", {})
            else:                                               # (the scorched ground before the walls)
                p.put(x, y, rng.choice(("Ash001", "Ash001", "Cinder001")), {})
    for x, y in ((10, 7), (13, 15), (19, 8), (21, 14), (16, 6), (11, 13)):
        p.set(x, y, decor=rng.choice(("Dead_Tree001", "Dead_Tree002")))
    for x, y in ((14, 9), (18, 13), (20, 10)):
        p.set(x, y, decor="Dragon_Skull001")
    p.ents = ["Lock\t%d\t%d\t$Attr.GalaithQuest>=1\tThe barrier holds: violet light, hard as glass." % (BARRIER_X, y)
              for y in NECK]
    p.ents += ["Trigger\tThe Dragon Speaks\t%d\t%d" % (BARRIER_X + 1, y) for y in NECK]
    p.ents += [obj_line("NPC", "Galaith_Dragon", 16, 12, "Attitude=Bad Zone=11,7,22,16 Chase=8,6,24,16 "
                                                        "Id=Galaith_Dragon_Boss", -64),
               "MapItem\tBones\t%d\t%d\t1" % ((12 - 1) * TW, (9 - 1) * TW),
               "MapItem\tBones\t%d\t%d\t1" % ((20 - 1) * TW, (15 - 1) * TW)]
    K.place_id(p, "Galaith_Barrier", BARRIER_X - 1, 11)
    K.place_id(p, "Dragons_Field", 16, 11)
    p.save()
    # the causeway from the Elderwood's east shore
    c = Map("9,6,0")
    for x in range(1, XT + 1):
        for y in (11, 12):
            if c.tile(x, y).startswith(("Water", "Sand_Water", "Sea_Rock")):
                c.set(x, y, tile="Paving001", decor="")
    c.save()
    print("10,5,0 to 10,7,0: the mountains, the pass, the barrier, the dragon's field; a causeway from 9,6,0")
    return True


def city_walls():
    """The city's ground, its walls, and the mountains round it (the city's buildings come after: towns.py)."""
    if K.map_exists("12,6,0"):
        return False
    rng = random.Random(2066)
    for name in CITY:
        mx, my = (int(v) for v in name.split(",")[:2])
        m = Map(name, new=True)
        for y in range(1, YT + 1):
            for x in range(1, XT + 1):
                m.put(x, y, "Grass001", {})
        if my == 5:
            peaks(m, [(x, y) for y in (1, 2) for x in range(1, XT + 1)], rng)
            for x in range(1, XT + 1):
                m.put(x, NORTH_WALL[0], "Galaith_Wall001", {})
                m.put(x, NORTH_WALL[1], "Galaith_Wall004", {})
        if my == 7:
            peaks(m, [(x, y) for y in (20, 21) for x in range(1, XT + 1)], rng)
            for x in range(1, XT + 1):
                m.put(x, SOUTH_WALL[0], "Galaith_Wall001", {})
                m.put(x, SOUTH_WALL[1], "Galaith_Wall004", {})
        if mx == 11:
            top = NORTH_WALL[0] if my == 5 else 1
            bottom = SOUTH_WALL[1] if my == 7 else YT
            for y in range(top, bottom + 1):
                m.put(1, y, "Galaith_Wall002", {})
        if mx == EAST:
            top = NORTH_WALL[0] if my == 5 else 1
            bottom = SOUTH_WALL[1] if my == 7 else YT
            for y in range(top, bottom + 1):
                m.put(EAST_WALL, y, "Galaith_Wall002", {})
            peaks(m, [(x, y) for y in range(1, YT + 1) for x in range(EAST_WALL + 1, XT + 1)], rng)
        for (tx, ty) in ((1, NORTH_WALL[0]), (EAST_WALL, NORTH_WALL[0]), (1, SOUTH_WALL[0]), (EAST_WALL, SOUTH_WALL[0])):
            if (mx == 11 and tx == 1 or mx == EAST and tx == EAST_WALL) and (my == 5 and ty == NORTH_WALL[0] or
                                                                         my == 7 and ty == SOUTH_WALL[0]):
                m.put(tx, ty, "Galaith_Wall003", {})                # (the corner towers)
                m.put(tx, ty + 1, "Galaith_Wall005", {})
        if name == "11,6,0":                                     # the west gate, onto the dragon's field
            m.put(GATE[0], GATE[1], "Galaith_Gate005", {})
            m.put(GATE[0], GATE[1] + 1, "Galaith_Gate005", {})
            m.ents += ["Lock\t%d\t%d\t$Attr.GalaithQuest>=2\tThe gate is barred. Something huge breathes behind you."
                       % (GATE[0], GATE[1] + k) for k in (0, 1)]
            K.place_id(m, "Galaith_West_Gate", GATE[0] + 1, GATE[1])
        if name == "14,6,0":                                     # the east gate, and the mine's mouth beyond it
            m.put(EAST_WALL, 11, "Galaith_Gate006", {})
            m.put(EAST_WALL, 12, "Galaith_Gate006", {})
            for x in range(EAST_WALL + 1, MINE[0]):
                m.put(x, 11, "Dirt001", {})
                m.put(x, 12, "Dirt001", {})
            m.put(MINE[0], MINE[1], "Mine_Mouth001", {})
            m.ents += ["Lock\t%d\t%d\t$Attr.KingQuest>=1\tThe mine is shut, by the King's order." % MINE]
            K.place_id(m, "Galaith_Mine", MINE[0] - 1, MINE[1])
        m.save()
    print("11,5,0 to 14,7,0: Galaith's ground, its walls (white, burnt black) and gates, the mountains behind it")
    return True


def mine():
    if K.map_exists("14,6,-1"):
        return
    rng = random.Random(77)
    m = Map("14,6,-1", new=True)
    cave = {(x, y) for y in range(4, 19) for x in range(3, 24) if ((x - 13) / 10.5) ** 2 + ((y - 11) / 7.5) ** 2 <= 1}
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if (x, y) in cave:
                m.put(x, y, rng.choice(("Cave_Floor001", "Cave_Floor001", "Cave_Floor002", "Cave_Floor003")), {})
            elif any((x + i, y + j) in cave for i in (-1, 0, 1) for j in (-1, 0, 1)):
                m.put(x, y, "Cave_Wall001", {})
    m.set(MINE[0] - 1, MINE[1], decor="Mine_Ladder001")
    for x, y in ((6, 8), (9, 14), (12, 6), (16, 15), (19, 9), (8, 11), (17, 7)):
        if (x, y) in cave:
            m.set(x, y, decor=rng.choice(("Gold_Rock001", "Gold_Rock001", "Gem_Rock001")))
    for x, y in ((11, 11), (15, 11)):
        m.set(x, y, tile="Mine_Support001")
    m.ents = []
    K.place_id(m, "Galaith_Mine_Floor", 13, 11)
    m.save()
    K.write_script("Enter Mine_Mouth", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You go down into the mine: gold glitters in the walls.", "-"),
        ("Teleport", "%d,%d" % ((MINE[0] - 2) * TW, MINE[1] * TW - 8), "14,6,-1"),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    K.copy_sprite("Tiles", "Cave_Ladder001", "Mine_Ladder001")
    K.copy_tile("Mine_Ladder001", "Cave_Ladder001", Use_Words="Climb Up,Examine",
                Examine_Info="A ladder up to the mine's mouth.")
    K.minimap_colour("Mine_Ladder001", (255, 0, 0))
    K.write_script("Climb Up Mine_Ladder", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Teleport", "%d,%d" % ((MINE[0] - 2) * TW, MINE[1] * TW - 8), "14,6,0"),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    print("Made maps\\14,6,-1.txt: Galaith's mine")


# ================================================================== the city
def plan():
    civic = [("building", "parliament", "Parliament"), ("building", "hall", "City Hall"),
             ("building", "hall", "Town Hall"), ("building", "hotel", "The Golden Crown Hotel"),
             ("building", "bank", ""), ("building", "bank", ""), ("building", "police", ""),
             ("building", "hospital", ""), ("building", "barracks", ""), ("building", "armoury", "")]
    return ([("square", 11, 7, 6), ("lanes", ["bakery", "butcher", "fish", "greens"], 3)] + civic +
            [("lanes", ["armour", "weapons"], 3, "armoury"),
             ("square", 9, 6, 4, "posh"), ("lanes", ["clothes", "shoes"], 3)] +
            [("building", "tavern", "")] * 10 + [("park", 3), ("streets", 20, 3)])


def city():
    first = Map(CITY[0])
    if K.has_id(first, "Galaith_Grown"):
        return None
    g = T.Ground(CITY)
    town = T.Town("Galaith", "Galaith", g, (12 * XT + 24, 6 * YT + 10), {"walls": ["Plaster001", "Stone_Wall001",
                                                                                     "Brick001"],
                                                                           "grand": "Stone_Wall001"}, True, seed=1453)
    pm, x1, y1, x2, y2 = PALACE
    mx, my = g.mxy(pm)
    lot = T.Lot("palace", mx * XT + x1 - 1, my * YT + y1 - 1, mx * XT + x2 - 1, my * YT + y2 - 1,
                mx * XT + (x1 + x2) // 2 - 1, "The Palace")
    town.take(lot)
    town.avenues(CITY)
    T.grow(town, plan(), carts=lambda t: [("the palace", (lot.door, lot.y2 + 1)),
                                          ("the market", t.centre),
                                          ("the west gate", (11 * XT + 4, 6 * YT + 11)),
                                          ("the east gate", (EAST * XT + 16, 6 * YT + 11))])
    K.place_id(first, "Galaith_Grown", 12, 12)
    g.save()
    kinds = {}
    for lt in town.lots:
        kinds[lt.kind] = kinds.get(lt.kind, 0) + 1
    print("Galaith: %s; %d streets%s" % (", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items())), town.streets,
                                        ("; no room for: " + ", ".join(town.missed)) if town.missed else ""))
    return town


def main():
    if K.new_mainland():
        sys.exit("Superseded: build_estforlan.py rebuilt the mainland. This one would put back the old Galaith in the east.")
    draw_pictures()
    data()
    mountains_and_pass()
    city_walls()
    mine()
    city()


if __name__ == "__main__":
    main()
