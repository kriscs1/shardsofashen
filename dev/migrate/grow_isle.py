"""The Isle twice as big, grown north (the owner's wish): its north coast just as it was, three maps further north, and
new land filling the middle; the hobgoblins' camp moved to its north-west corner and the ring of standing stones to its
south-east; new places in the new land.

  * The north coast: the old one's shape (the rows above CAP, inlets and all) laid down SHIFT cells further north, on
    new maps (0..4, -3..-1); between it and the old land, new land, its west and east coasts wandering (bays and
    headlands a few maps across) and meeting the old ones at both ends. The old north shore, inland now, is grass and
    wood; nothing built on it moves, so no story's coordinates change.
  * The new land: Hollow Wood in the west (wolves, mushrooms, a hollow stump to Search), meadow in the middle with
    Mirror Tarn (fish, ducks, frogs, reeds), the Tin Braes in the east (hills with copper and tin to mine), and the Old
    Beacon, a ruined beacon on the north headland (its hearth to Search). Paths join them to the Isle's roads.
  * The hobgoblins' camp (palisade, tents, fire, chest, its two hobgoblins) is lifted whole to the north-west corner.
    Their bolt-hole tent stays where it was, over their lair (2,2,-2): the hidden ladder still comes up in it, as
    ladders line up with what's over them. The camp's chest is Hob_Camp_Chest (its own script, the same attribute).
    (move_lawyers_house.py put the camp back, and Edwin and Maren's house in the corner instead.)
  * The standing stones and their chest (Stone_Circle_Chest, the same attribute) to the south-east shore; the Hermit and
    the villager who talk of them say where.
  * The new maps on the Isle's lists: easy locks (Locks.ini), music and ambience, the world map's labels.

Run it once (a second run finds the Isle grown and stops).

  python -I "dev\\migrate\\grow_isle.py"
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
import world_edit as W                                   # noqa: E402
from world_edit import XT, YT, fbm, h01                 # noqa: E402
import story_kit as SK                                   # noqa: E402

ROOT = W.ROOT
DATA = os.path.join(ROOT, "data")
DONE = os.path.join(HERE, ".isle_grown")
MAKER = "grow_isle.py"
SHIFT = 56                                              # (the north coast moves this many cells north)
CAP = 17                                                # (the old rows above this are the north coast's shape)
GX1, GX2 = 0, 124                                       # (the Isle's maps, 0..4)
NEW = (0, -3, 4, -1)                                    # (the new maps)
TOP = -3 * YT
CAMP = (56, 43, 68, 54)                                 # (the camp, its gate's path too)
BOLT_HOLE = (66, 51)                                    # (the tent over the lair's ladder: it stays)
STONES = [(16, 8), (13, 9), (19, 9), (13, 13), (19, 13), (16, 14)]
STONE_MIDDLE = (16, 11)


# ================================================================== the land
def snapshot(w):
    return {(gx, gy): w.cell(gx, gy) for gx in range(GX1, GX2 + 1) for gy in range(0, CAP)}


def was_land(old, gx, gy):
    text = old.get((gx, gy))
    return text is not None and not W.watery(text) and W.parts(text)[0] != "Black001"


def extents(old, gy):
    xs = [gx for gx in range(GX1, GX2 + 1) if was_land(old, gx, gy)]
    return (xs[0], xs[-1]) if xs else (10, 115)


def make_shape(old):
    """new_land(gx, gy): the old north coast's shape SHIFT further north, the middle filled, its sides wandering."""
    lw, le = extents(old, CAP - 1)
    top, bottom = CAP - SHIFT, CAP                      # (the middle's rows: from under the moved coast to the old)

    def side(gy, seed, gx):
        k = math.sin(math.pi * (gy - top + 1) / (bottom - top + 1))      # (none at the ends: the coasts meet there)
        return k * (16 * (fbm(0, gy, 26, seed) - 0.5) + 6 * (fbm(0, gy, 9, seed + 1) - 0.5)) + \
            2.5 * (fbm(gx, gy, 4, seed + 2) - 0.5)

    def new_land(gx, gy):
        if gy < TOP + 2 or gy >= CAP:
            return False
        if gy < top:
            return was_land(old, gx, gy + SHIFT)
        if gy >= 0 and was_land(old, gx, gy):
            return True
        west = max(3, lw + side(gy, 2301, gx))
        east = min(GX2 - 4, le - side(gy, 2311, gx))
        return west <= gx <= east
    return new_land


def kind_of(gx, gy):
    """Which land: Hollow Wood west, the Tin Braes east, meadow between (their edges ragged)."""
    u = gx + 14 * (fbm(gx, gy, 18, 2321) - 0.5)
    v = gy + 14 * (fbm(gx, gy, 18, 2322) - 0.5)
    if u < 40 and -48 < v < 12:
        return "wood"
    if u > 86 and -44 < v < 6:
        return "hills"
    return "meadow"


def ground_for(gx, gy):
    import land as LAND
    g, d = LAND.scenery(kind_of(gx, gy), gx, gy, h01("isle", gx, gy))
    if g == "Water001" or d == "STONE":
        g, d = "Grass001", ""
    return g + ("+Decor(%s)" % d if d else "")


def sea_near(w, gx, gy, r=2):
    return any(w.cell(gx + dx, gy + dy) is not None and W.watery(w.cell(gx + dx, gy + dy))
               for dx in range(-r, r + 1) for dy in range(-r, r + 1))


def grow(w):
    x1, y1, x2, y2 = NEW
    for mx in range(x1, x2 + 1):
        for my in range(y1, y2 + 1):
            w.new_map(mx, my)
    old = snapshot(w)
    new_land = make_shape(old)
    made = []
    for gy in range(TOP, CAP):
        for gx in range(GX1, GX2 + 1):
            text = w.cell(gx, gy)
            if text is None or not new_land(gx, gy) or not (W.watery(text) or W.parts(text)[0] == "Black001"):
                continue
            w.put(gx, gy, ground_for(gx, gy))
            made.append((gx, gy))
    for c in made:                                       # (a beach where the new land meets the sea)
        if sea_near(w, *c):
            w.put(c[0], c[1], "Sand001")
    for gy in range(0, CAP):                             # (the old north shore's sand, inland now: grass and wood)
        for gx in range(GX1, GX2 + 1):
            text = w.cell(gx, gy)
            if W.parts(text)[0] == "Sand001" and W.natural(text) and not sea_near(w, gx, gy):
                w.put(gx, gy, ground_for(gx, gy))
    w.smooth_shores({(gx, gy) for gx in range(GX1, GX2 + 1) for gy in range(TOP, CAP + 3)})
    return set(made)


# ================================================================== places
def clear(w, gx, gy, made, water=2):
    """Open new ground, nothing on it, no sea near."""
    return (gx, gy) in made and W.natural(w.cell(gx, gy)) and not sea_near(w, gx, gy, water)


def site(w, made, size, xs, ys, score, taken=()):
    """The best spot (by score) whose size box is all clear new ground, apart from what's taken."""
    best = None
    for gx in xs:
        for gy in ys:
            box = [(gx + i, gy + j) for i in range(size[0]) for j in range(size[1])]
            if any(abs(gx - t[0]) < 20 and abs(gy - t[1]) < 20 for t in taken):
                continue
            if all(clear(w, x, y, made) for x, y in box):
                s = score(gx, gy)
                if best is None or s > best[0]:
                    best = (s, (gx, gy))
    return best[1] if best else None


def bare(w, gx, gy, tile="Grass001"):
    w.put(gx, gy, tile)


def tarn(w, made):
    """Mirror Tarn: a little lake in the meadow, reeds round it, fish in it, ducks and frogs."""
    at = site(w, made, (17, 11), range(48, 62), range(-30, -8), lambda x, y: -abs(x - 54) - abs(y + 20))
    cx, cy = at[0] + 8, at[1] + 5
    water = set()
    for gx in range(cx - 8, cx + 9):
        for gy in range(cy - 5, cy + 6):
            r = ((gx - cx) / 7.0) ** 2 + ((gy - cy) / 4.2) ** 2
            if r <= 0.75 + 0.45 * fbm(gx, gy, 3, 2331):
                water.add((gx, gy))
                w.put(gx, gy, W.SEA)
    for gx, gy in {(x + dx, y + dy) for x, y in water for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - water:
        if h01("reeds", gx, gy) < 0.45:
            w.put(gx, gy, "Grass001+Decor(Reeds001)")
        else:
            bare(w, gx, gy)
    w.smooth_shores(water)
    north = min((c for c in water if c[0] == cx), key=lambda c: c[1])
    w.place(north[0], north[1], "StaticObject", "Fish_Spot")      # (at the edge, where you can reach it)
    w.place_id(cx, north[1] - 2, "Mirror_Tarn")
    bare(w, cx, north[1] - 2)
    z = lambda x1, y1, x2, y2, gx, gy: w.zone(x1, y1, x2, y2, gx, gy)            # noqa: E731
    shore = sorted({(x + i, y + j) for x, y in water for i in (-1, 0, 1) for j in (-1, 0, 1)} - water,
                   key=lambda c: (c[1], c[0]))
    shore = [c for c in shore if "Decor" not in w.cell(*c)]
    box = (min(c[0] for c in shore), min(c[1] for c in shore), max(c[0] for c in shore), max(c[1] for c in shore))
    for c in (shore[len(shore) // 4], shore[3 * len(shore) // 4]):     # (ducks on the shore: they don't swim)
        w.place(c[0], c[1], "NPC", "Duck", "Attitude=Passive Zone=%s" % z(*box, *c))
    for k, (dx, dy) in enumerate(((-7, 4), (7, -3))):
        gx, gy = cx + dx, cy + dy
        bare(w, gx, gy)
        w.place(gx, gy, "NPC", "Frog", "Attitude=Passive Zone=%s" % z(gx - 2, gy - 2, gx + 2, gy + 2, gx, gy))
    return (cx, north[1] - 2), water


def wood(w, made):
    """Hollow Wood: its stump to Search, two wolves in it."""
    at = site(w, made, (5, 5), range(12, 36), range(-34, -6), lambda x, y: -abs(x - 24) - abs(y + 18))
    gx, gy = at[0] + 2, at[1] + 2
    bare(w, gx, gy)
    w.place(gx, gy, "StaticObject", "Hollow_Stump", "Id=Hollow_Wood_Stump")
    w.place_id(gx, gy + 2, "Hollow_Wood")
    for dx, dy in ((-6, -4), (5, 6)):
        x, y = gx + dx, gy + dy
        if (x, y) in made:
            bare(w, x, y)
            w.place(x, y, "NPC", "Wolf", "Attitude=Bad Zone=%s Chase=%s" % (
                w.zone(x - 4, y - 4, x + 4, y + 4, x, y), w.zone(x - 7, y - 7, x + 7, y + 7, x, y)))
    for dx, dy in ((3, -2), (-2, 3)):
        if (gx + dx, gy + dy) in made:
            w.put(gx + dx, gy + dy, "Grass001+Decor(Mushroom_Patch001)")
    return (gx, gy + 3)


def braes(w, made):
    """The Tin Braes: a few more rocks to mine where the label stands, copper and tin."""
    at = site(w, made, (5, 5), range(88, 110), range(-30, -6), lambda x, y: -abs(x - 100) - abs(y + 16))
    gx, gy = at[0] + 2, at[1] + 2
    w.place_id(gx, gy, "Tin_Braes")
    for k, (dx, dy) in enumerate(((-2, -1), (2, -2), (1, 2), (-1, 2))):
        w.put(gx + dx, gy + dy, "Grass001+Decor(%s)" % ("Copper_Rock001", "Tin_Rock001")[k % 2])
    return (gx, gy + 3)


def beacon(w, made):
    """The Old Beacon: a ruined ring of stone on the northern headland, its hearth to Search."""
    at = site(w, made, (9, 9), range(GX1 + 4, GX2 - 10), range(TOP + 2, -30), lambda x, y: -y * 3 - abs(x - 60))
    x0, y0 = at[0] + 2, at[1] + 2
    for i in range(5):
        for j in range(5):
            gx, gy = x0 + i, y0 + j
            edge = i in (0, 4) or j in (0, 4)
            if not edge:
                w.put(gx, gy, "Flagstone001" if h01("beacon", gx, gy) < 0.7 else "Grass001")
            elif (i, j) in ((2, 4), (4, 1), (0, 3)):     # (gaps where it fell)
                w.put(gx, gy, "Grass001+Decor(Pebbles00%d)" % (1 + (i + j) % 3))
            else:
                w.put(gx, gy, "Ruined_Wall00%d" % (1 if (i + j) % 3 else 2))
    w.place(x0 + 2, y0 + 2, "StaticObject", "Loose_Cobble", "Id=Old_Beacon_Hearth")
    w.place_id(x0 + 2, y0 + 6, "Old_Beacon")
    return (x0 + 2, y0 + 5)


def move_camp(w, made):
    """The camp lifted whole to the north-west corner; its bolt-hole tent left over the lair."""
    x1, y1, x2, y2 = CAMP
    at = site(w, made, (x2 - x1 + 5, y2 - y1 + 5), range(GX1 + 3, 50), range(TOP + 2, -12),
              lambda x, y: -x * 2 - (y - TOP))
    dx, dy = at[0] + 2 - x1, at[1] + 2 - y1
    cells = [(gx, gy) for gx in range(x1, x2 + 1) for gy in range(y1, y2 + 1)]
    for gx, gy in cells:
        text = w.cell(gx, gy)
        if (gx, gy) == BOLT_HOLE:
            text = "Grass001+Decor(Tent002)"              # (the new camp's tent in its place)
        w.put(gx + dx, gy + dy, text)
    for m, ln, c in w.lines(CAMP):
        if W.line_id(ln) == "Hob_Camp_Tent" or c == BOLT_HOLE:
            continue
        w.drop(m, ln)
        p = ln.split("\t")
        if p[0] == "StaticObject" and p[1] == "Chest":
            ln = "\t".join(p[:4] + [(p[4] + " " if len(p) > 4 else "") + "Id=Hob_Camp_Chest"])
        mx, my, _ = W.mxyz(m.name)
        w.add_line(ln, (mx, my), dx, dy)
    gone = [c for c in cells if c != BOLT_HOLE]
    w.rewild(gone, seed="hobcamp")
    bx, by = BOLT_HOLE
    for c, d in (((bx - 1, by), "Crate001"), ((bx, by + 1), "Sacks001")):   # (a bolt-hole, kept a little)
        w.set(c[0], c[1], decor=d)
    return (62 + dx, 43 + dy)


def move_stones(w, made):
    """The ring of standing stones (and its chest) to the south-east shore."""
    ox, oy = STONE_MIDDLE
    cands = [(gx, gy) for gx in range(70, 98) for gy in range(26, 54)]

    def ok(gx, gy):
        for i in range(-4, 5):
            for j in range(-4, 5):
                c = w.cell(gx + i, gy + j)
                if c is None or not W.natural(c) or W.watery(c) or W.is_road(c):
                    return False
        return True
    taken = {c for _, _, c in w.lines((60, 20, 110, 60))}
    spots = [c for c in cands if ok(*c) and not any(abs(c[0] - t[0]) <= 5 and abs(c[1] - t[1]) <= 5 for t in taken)]
    nx, ny = max(spots, key=lambda c: c[0] + c[1])
    for sx, sy in STONES:
        w.put(sx, sy, "Grass001")                          # (a standing stone is a tile of its own)
        w.put(nx + sx - ox, ny + sy - oy, "Standing_Stone001")
    for i in range(-2, 3):
        for j in range(-2, 3):
            if (nx + i, ny + j) not in [(nx + sx - ox, ny + sy - oy) for sx, sy in STONES]:
                w.put(nx + i, ny + j, "Grass001")
    for m, ln, c in w.lines((ox - 1, oy - 1, ox + 1, oy + 2)):
        p = ln.split("\t")
        if p[0] == "StaticObject" and p[1] == "Chest":
            w.drop(m, ln)
            ln = "\t".join(p[:4] + [(p[4] + " " if len(p) > 4 else "") + "Id=Stone_Circle_Chest"])
            w.add_line(ln, (0, 0), nx - ox, ny - oy)
    w.place_id(nx, ny + 4, "Standing_Stones")
    return (nx, ny)


def paths(w, ends):
    """Paths from each new place to the Isle's roads."""
    net = {(gx, gy) for gx in range(GX1, GX2 + 1) for gy in range(0, 3 * YT)
           if w.cell(gx, gy) is not None and W.is_road(w.cell(gx, gy))}
    return W.join_roads(w, ends, network=net)


# ================================================================== scripts and data
FAR = [("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]


def chest(pid, attr, items):
    SK.write_script("Open %s" % pid, [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.%s=0" % attr, "@empty"),
        ("Update.Attribute", attr, "=1"),
        ("Play.Sound", "Chest")] + [("Give.Item", i, str(n)) for i, n in items] + [
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "The chest is empty.", "Empty"), ("End",)] + FAR, MAKER)


def search(pid, line, items):
    SK.write_script("Search %s" % pid, [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.%s=0" % pid, "@empty"),
        ("Update.Attribute", pid, "=1"),
        ("Play.Sound", "Pickup"),
        ("Display.Message", "Yellow", line, "-")] + [("Give.Item", i, str(n)) for i, n in items] + [
        ("End",),
        ("@empty",), ("Display.Message", "Cyan", "You've found what was here already.", "-"), ("End",)] + FAR, MAKER)


def scripts():
    chest("Hob_Camp_Chest", "GoblinChest", [("Bronze_Sword", 1), ("Gold_Coin(s)", 30)])          # (Open Chest 2's)
    chest("Stone_Circle_Chest", "StoneCircleChest", [("Magic_Potion", 1), ("Lightning_Scroll", 1),  # (Open Chest's)
                                                     ("Gold_Coin(s)", 40)])
    search("Hollow_Wood_Stump", "Deep in the hollow stump: a squirrel's winter store, and under it somebody's purse, "
                                "green with age. The squirrel was saving it for something.",
           [("Gold_Coin(s)", 15), ("Shard", 4)])
    search("Old_Beacon_Hearth", "The hearthstone of the old beacon lifts: a keeper's tinderbox, wrapped in oilcloth, "
                                "and a little pouch of Shards. Somebody meant to light it again.",
           [("Tinderbox", 1), ("Shard", 6)])
    old, new = "on the north-west headland", "by the south-east shore"
    for path in (os.path.join(DATA, "Scripts", "Talk to Hermit.script"), os.path.join(DATA, "Scripts", "Talk to Villager.script"),
                 os.path.join(HERE, "build_scenery.py")):
        text = W.read(path) if path.endswith(".script") else open(path, encoding="utf-8").read()
        if old in text:
            text = text.replace(old, new)
            if path.endswith(".script"):
                W.write(path, text)
            else:
                open(path, "w", encoding="utf-8", newline="").write(text)


def lists(w):
    names = [W.mname(mx, my) for mx in range(NEW[0], NEW[2] + 1) for my in range(NEW[1], NEW[3] + 1)]
    path = os.path.join(DATA, "Locks.ini")
    s = W.read(path)
    m = re.search(r"(?m)^Isle\.Maps=([^\r\n]*)", s)
    have = m.group(1).split()
    s = s.replace(m.group(0), "Isle.Maps=" + " ".join(have + [n for n in names if n not in have]))
    W.write(path, s)
    for f, sea, land in (("Music.ini", "Sea", "Forest"), ("Ambient.ini", "Waves", "Forest")):
        path = os.path.join(DATA, f)
        s = W.read(path)
        for name in names:
            if re.search(r"(?m)^%s=" % re.escape(name), s):
                continue
            mx, my, _ = W.mxyz(name)
            wet = sum(1 for row in w.maps[(mx, my)].rows for c in row if W.watery(c))
            s = s.replace("[Maps]\r\n", "[Maps]\r\n%s=%s\r\n" % (name, sea if wet > XT * YT * 0.6 else land), 1)
        W.write(path, s)
    path = os.path.join(DATA, "WorldMap.ini")
    s = W.read(path)
    s = s.replace("The Isle=2,1,0 3 4\r\n", "The Isle=2,-1,0 13 12\r\n")
    W.write(path, s)
    for label, pid in (("Mirror Tarn", "Mirror_Tarn"), ("Hollow Wood", "Hollow_Wood"), ("The Tin Braes", "Tin_Braes"),
                       ("The Old Beacon", "Old_Beacon"), ("The Standing Stones", "Standing_Stones")):
        SK.place_label("Places", label, pid)


def main():
    if os.path.exists(DONE):
        print("The Isle's grown already (delete %s to do it again)." % DONE)
        return
    w = W.World(0)
    made = grow(w)
    camp = move_camp(w, made)
    stones = move_stones(w, made)
    made -= {c for c in made if not W.natural(w.cell(*c))}
    t, _ = tarn(w, made)
    ends = [camp, t, wood(w, made), braes(w, made), beacon(w, made), (stones[0] - 5, stones[1])]
    n = paths(w, ends)
    changed = w.save()
    scripts()
    lists(w)
    print("The Isle: %d cells of new land, the camp to %s, the stones to %s, %d paths, %d maps changed" %
          (len(made), camp, stones, n, changed))
    open(DONE, "w").write("grown\n")


if __name__ == "__main__":
    main()
