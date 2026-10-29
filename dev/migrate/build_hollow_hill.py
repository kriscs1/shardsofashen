"""The Hollow Hill: a cave in the West Range where Northport's west road runs into the mountains (2,4,0, at the
road's end), and the cave under it (2,4,-1).

  * Its mouth (Hollow_Hill_Mouth, the tile Cave_Mouth001): drawn on the very part of the range's texture that falls on
    that tile (build_terrain.py's Range_Rock), so it sits in the mountain without a seam; Enter it to go down.
  * The cave: tunnels winding back under the range into three chambers - bats and rats near the way in, coal, copper
    and ore to mine, a pool, cave mushrooms, and at the back a spiders' chamber with a chest (each player's own,
    once: the attribute HollowHillChest). Steps up to the daylight (Hollow_Hill_Steps) where you came in.
  * The world map names it.

Run after build_terrain.py. Safe to run again (the cave is made once; its scripts are written again).

  python -I "dev\\migrate\\build_hollow_hill.py"
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K                       # noqa: E402
import story_kit as SK                       # noqa: E402
from story_kit import Map, obj_line, TW, XT, YT   # noqa: E402

MAKER = "build_hollow_hill.py"
ABOVE, BELOW = "2,4,0", "2,4,-1"
MOUTH = (8, 16)                   # (the range's tile at the road's end)
ROAD_END = (9, 16)
STEPS = (8, 16)                   # (below the mouth, in the cave)
ARRIVE = (9, 16)
TEX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sprites",
                   "Textures", "Range_Rock.png")


# ================================================================== pictures
def texture_cell(gx, gy):
    """The 32 x 32 of Range_Rock that the client paints on world tile gx, gy (ground.js: by its place in the world)."""
    from common import read_png
    w, h, rows = read_png(TEX)                                      # (a plain picture: no mask half)
    sx, sy = (gx * TW) % w, (gy * TW) % h
    return [[rows[(sy + y) % h][(sx + x) % w] for x in range(TW)] for y in range(TW)]


def mouth():
    """A dark opening low in the rock face, its rim lit from the top left, rubble at its lip."""
    m = Map(ABOVE)
    gx, gy = m_world(m, *MOUTH)
    img = texture_cell(gx, gy)
    for y in range(32):
        for x in range(32):
            dx, dy = (x - 16) / 13.0, (y - 32) / 24.0
            d = dx * dx + dy * dy
            if d <= 1 and y <= 31:
                depth = 1 - d
                c = int(8 + 22 * (1 - depth))
                K.put(img, x, y, (c, c - 2, c + 2))
            elif d <= 1.28 and y < 31:                               # (the rim)
                lit = x < 16 and y < 20
                K.put(img, x, y, (150, 156, 170) if lit else (58, 60, 72))
    for x, y in ((9, 30), (12, 31), (21, 30), (23, 31), (17, 31)):    # (rubble at its lip)
        K.put(img, x, y, (96, 100, 112))
        K.put(img, x + 1, y, (70, 74, 86))
    return img


def steps():
    """Rough steps up out of the cave, daylight spilling down them."""
    img = K.load("Tiles", "Cave_Floor001")
    for i, y0 in enumerate((4, 12, 20)):
        shade = 150 - i * 30
        for y in range(y0, y0 + 6):
            for x in range(5, 27):
                K.put(img, x, y, (shade, shade - 6, shade - 14) if y < y0 + 4 else (shade - 50, shade - 56, shade - 60))
    for y in range(0, 10):                                            # (the light from above)
        for x in range(8, 24):
            c = K.get(img, x, y)
            if c:
                K.put(img, x, y, tuple(min(255, v + 40 - y * 4) for v in c))
    return img


def m_world(m, x, y):
    mx, my, _ = (int(v) for v in m.name.split(","))
    return mx * XT + x - 1, my * YT + y - 1


# ================================================================== the cave
WAY = [(9, 16), (6, 14), (4, 10), (6, 6), (11, 5), (15, 8), (19, 11), (21, 15)]   # (the tunnel winds through these)
CHAMBERS = [((5, 9), 3.2), ((13, 6), 3.0), ((19, 14), 4.0)]


def cave_cells(rng):
    cells = set()
    for (x0, y0), (x1, y1) in zip(WAY, WAY[1:]):
        n = int(math.hypot(x1 - x0, y1 - y0) * 3) + 1
        for i in range(n + 1):
            t = i / n
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            r = 1.3 + rng.uniform(0, 0.6)
            cells |= {(x, y) for x in range(2, XT) for y in range(2, YT) if (x - cx) ** 2 + (y - cy) ** 2 <= r * r}
    for (cx, cy), r in CHAMBERS:
        cells |= {(x, y) for x in range(2, XT) for y in range(2, YT)
                  if ((x - cx) / r) ** 2 + ((y - cy) / (r * 0.8)) ** 2 <= 1 + rng.uniform(-0.15, 0.15)}
    return cells


def cave():
    if SK.map_exists(BELOW):
        m = Map(BELOW)                                                # (an older run's: its mushrooms given a number)
        fixed = [ln + "	1" if ln.startswith("MapItem	") and ln.count("	") == 3 else ln for ln in m.ents]
        if fixed != m.ents:
            m.ents = fixed
            m.save()
        return False
    rng = random.Random(BELOW)
    m = Map(BELOW, new=True)
    cells = cave_cells(rng)
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            if (x, y) in cells:
                m.put(x, y, rng.choice(("Cave_Floor001", "Cave_Floor001", "Cave_Floor002", "Cave_Floor003")), {})
            elif any((x + i, y + j) in cells for i in (-1, 0, 1) for j in (-1, 0, 1)):
                m.put(x, y, rng.choice(("Cave_Wall001", "Cave_Wall001", "Cave_Wall002")), {})
    m.put(STEPS[0], STEPS[1], "Cave_Steps001", {})
    floor = sorted(c for c in cells if abs(c[0] - STEPS[0]) + abs(c[1] - STEPS[1]) > 3)
    used = {STEPS, ARRIVE}

    def spot(near, r):
        options = [c for c in floor if c not in used and abs(c[0] - near[0]) + abs(c[1] - near[1]) <= r
                   and all((c[0] + i, c[1] + j) in cells for i in (-1, 0, 1) for j in (-1, 0, 1))]
        c = rng.choice(options or [c for c in floor if c not in used])
        used.add(c)
        return c
    for rock, near in (("Coal_Rock001", (5, 9)), ("Coal_Rock001", (6, 11)), ("Copper_Rock001", (12, 6)),
                       ("Copper_Rock001", (14, 7)), ("Ore_Rock001", (18, 12)), ("Ore_Rock001", (6, 7))):
        x, y = spot(near, 3)
        m.set(x, y, decor=rock)
    x, y = spot((13, 6), 2)
    m.put(x, y, "Cave_Pool001", {})
    for near in ((4, 10), (11, 5), (20, 15)):
        x, y = spot(near, 3)
        m.ents.append(obj_line("MapItem", "Cave_Mushroom", x, y, "1"))
    for kind, near, zone in (("Bat", (6, 12), (4, 8, 9, 15)), ("Bat", (12, 6), (9, 4, 16, 9)),
                             ("Rat", (7, 9), (3, 7, 8, 12)), ("Rat", (15, 8), (11, 5, 17, 10)),
                             ("Giant_Spider", (19, 13), (16, 11, 23, 17)), ("Giant_Spider", (21, 15), (16, 11, 23, 17))):
        x, y = spot(near, 3)
        m.ents.append(obj_line("NPC", kind, x, y, "Attitude=Bad Zone=%d,%d,%d,%d" % zone))
    x, y = spot((21, 14), 2)
    m.ents.append(obj_line("StaticObject", "Chest", x, y, "Id=Hollow_Hill_Chest"))
    SK.place_id(m, "Hollow_Hill_Steps", STEPS[0], STEPS[1])
    SK.place_id(m, "Hollow_Hill_Floor", ARRIVE[0], ARRIVE[1])
    m.save()
    print("Made maps\\%s.txt: the Hollow Hill's cave" % BELOW)
    return True


def above():
    m = Map(ABOVE)
    t, over = m.parts(*MOUTH)
    if t != "Cave_Mouth001":
        m.put(MOUTH[0], MOUTH[1], "Cave_Mouth001", {})
    if m.tile(*ROAD_END).startswith("Sand"):                         # (the road runs right up to it)
        m.put(ROAD_END[0], ROAD_END[1], "Dirt001", m.parts(*ROAD_END)[1])
    if not SK.has_id(m, "Hollow_Hill_Mouth"):
        SK.place_id(m, "Hollow_Hill_Mouth", MOUTH[0], MOUTH[1])
    m.save()
    SK.place_label("Places", "The Hollow Hill", "Hollow_Hill_Mouth")


# ================================================================== data and scripts
def pixel(tx, ty):
    """Where a player stands on tile tx, ty (1-based), as Teleport wants it."""
    return "%d,%d" % ((tx - 1) * TW, (ty - 1) * TW - 8)


def data():
    K.save("Tiles", "Cave_Mouth001", mouth())
    K.save("Tiles", "Cave_Steps001", steps())
    SK.copy_tile("Cave_Mouth001", "Peak001", Walkable_Data="1" * 49, Line_of_Sight="0", Show_Name="1",
                 Use_Words="Enter,Examine", Blend="8", Blend_Texture="Mountain001",
                 Examine_Info="A cave in the mountainside. Cold air breathes out of it.")
    SK.copy_tile("Cave_Steps001", "Cave_Floor001", Walkable_Data="1" * 49, Show_Name="1",
                 Use_Words="Climb Up,Examine", Examine_Info="Rough steps up to the daylight.")
    ini_tiles = SK.TILES
    from ashen import ini
    if ini.read("Cave_Mouth001", "Texture", "", ini_tiles):                # (its own picture, not the range's)
        SK.set_section(ini_tiles, "Cave_Mouth001", ["%s=%s" % kv for kv in ini.section("Cave_Mouth001", ini_tiles)
                                                   if kv[0] != "Texture"])
        ini.forget()
    SK.minimap_colour("Cave_Mouth001", (24, 20, 22))
    SK.minimap_colour("Cave_Steps001", (150, 140, 120))
    SK.write_script("Enter Hollow_Hill_Mouth", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Display.Message", "Cyan", "You duck into the cave. Somewhere ahead, water drips, and something squeaks.", "-"),
        ("Teleport", pixel(*ARRIVE), BELOW),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    SK.write_script("Climb Up Hollow_Hill_Steps", [
        (">Distance.From.Clicked.Tile", "48", "@far"),
        ("Play.Sound", "Ladder"),
        ("Teleport", pixel(*ROAD_END), ABOVE),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    SK.write_script("Open Hollow_Hill_Chest", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.HollowHillChest=0", "@empty"),
        ("Update.Attribute", "HollowHillChest", "=1"),
        ("Play.Sound", "Chest"),
        ("Give.Item", "Gold_Coin(s)", "45"),
        ("Give.Item", "Healing_Draught", "2"),
        ("Give.Item", "Shard", "12"),
        ("Give.Item", "Iron_Helm", "1"),
        ("Display.Message", "Yellow", "Under the cobwebs, someone's old cache: gold, draughts, Shards and an iron helm.",
         "-"),
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)


def main():
    data()
    above()
    cave()
    print("The Hollow Hill: done")


if __name__ == "__main__":
    main()
