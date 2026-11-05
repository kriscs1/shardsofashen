"""More to find in the marshes (the owner's wish), each on the world map, none of it needed by any quest:

  In the Mirefen:
  * The Sunken Barge (-131,132 in world tiles): a barge gone down in the big pool south of Mirefold, a rickety boardwalk
    out to it from the door of the hut by the pool; a locked chest in what's left of it.
  * The Peat Cuttings (map -4,3): trenches in a patch of black peat, stacks nobody came back for, a tent, the cutters'
    box, the man they dug up (Search him), and the Bog Troll that saw them off.
  * The Wisp Ring (-49,137): a ring of leaning stones and the lights that hang in it. Reach for them, more than once.

  In the marsh round Saltmarsh:
  * The Eel-Catcher's Hut (map 10,21): Old Silt, his hut and his jetty on the stream, an eel spot off the end of it.
  * The Drowned Bell (214,393): the Abbey's bell, as far as whoever stole it got. Ring it.

Run after marsh_water.py and wind_boardwalks.py. The Shards they give are in Shards.ini [Shards] (Marsh.*). Safe to run
again.

  python -I "dev\\migrate\\build_marsh_places.py"   (then build_minimaps.py, export_web_assets.py)
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from common import Ini, p, write_image           # noqa: E402
import story_kit as SK                           # noqa: E402
from world_edit import World, parts, join        # noqa: E402
from atlas import fbm                            # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

MAKER = "build_marsh_places.py"
S = 32
OPEN, NONE = "1" * 49, "0" * 49
SOLID = "1111111111111111000111100011110001111111111111111"   # (the foot of it, in its cell's middle)
TRENCH = "1" * 14 + "0" * 21 + "1" * 14                        # (the cut across the cell's middle)
OUTLINE = (24, 20, 14, 255)

BARGE = (-131, 132)                                           # (its top left; three tiles by two)
SPUR = [(-135, 118), (-135, 120), (-133, 120), (-133, 123), (-135, 123), (-135, 126), (-133, 126), (-133, 129),
        (-134, 129), (-134, 131), (-132, 131), (-132, 133)]   # (from the hut's door out to it, a bit at a time)
PEAT = (-88, 79, 9, 4.5)                                      # (its middle, and how far it goes each way)
CUTS = [(76, -93, -87), (79, -94, -85), (82, -92, -86)]       # (row, from, to)
RING = (-49, 137)
RING_STONES = [(0, -3), (2, -2), (3, 0), (2, 2), (0, 3), (-2, 2), (-3, 0), (-2, -2)]
HUT = (263, 450)                                              # (five wide, four deep, its front below)
JETTY = [(265, 455), (265, 456), (262, 456), (262, 455), (260, 455)]
BELL = (214, 393)
SHARDS = [("Marsh.Wisp", "12"), ("Marsh.Peat.Man", "8"), ("Marsh.Bell", "6")]


# ------------------------------------------------------------------ pictures
def new(w=S, h=S):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def outlined(im):
    """The 1 px dark outline, round what's drawn."""
    out = im.copy()
    a, px = im.load(), out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            if a[x, y][3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + dx < w and 0 <= y + dy < h and a[x + dx, y + dy][3]:
                    px[x, y] = OUTLINE
                    break
    return out


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


def peat_ground():
    """Black peat: speckled alike all over, so no edge shows; a few pale fibres."""
    rng = random.Random("peat")
    im = new()
    px = im.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = rng.choice([(46, 36, 26), (52, 40, 28), (40, 32, 24), (48, 38, 28)]) + (255,)
    for _ in range(9):
        x, y = rng.randrange(S - 2), rng.randrange(S)
        for k in range(rng.randint(1, 3)):
            px[x + k, y] = (74, 60, 40, 255)
    return im


def peat_cut(left, right):
    """A cut across the peat: its far wall in shadow, black water in the bottom; spade-straight (a thing dug is)."""
    rng = random.Random("cut%d%d" % (left, right))
    im = new()
    px = im.load()
    x0, x1 = 5 if left else 0, S - 6 if right else S - 1
    for x in range(x0, x1 + 1):
        for y in range(8, 25):
            if y < 13:
                c = rng.choice([(26, 20, 16), (30, 24, 18), (22, 18, 14)])       # (the far wall)
            elif y < 22:
                c = rng.choice([(24, 26, 18), (20, 22, 16), (28, 28, 20)])       # (the water in it)
            else:
                c = rng.choice([(58, 46, 32), (52, 42, 30)])                     # (the near lip)
            px[x, y] = c + (255,)
        if x % 7 == 3:
            px[x, 11] = (50, 40, 30, 255)                                         # (the marks of the spade)
    return im


def peat_stack(n):
    """Peat cut into bricks and stacked to dry, turf side up."""
    rng = random.Random("stack%d" % n)
    im = new()
    d = ImageDraw.Draw(im)
    rows = ((6, 26, 6), (7, 22, 5), (8, 18, 4), (6, 14, 3)) if n == 1 else ((5, 26, 6), (6, 22, 5), (9, 18, 3))
    for x0, y0, count in rows:
        for i in range(count):
            c = rng.choice([(60, 46, 32), (70, 54, 36), (52, 40, 28), (64, 48, 34)])
            x = x0 + i * 4
            d.rectangle((x, y0, x + 3, y0 + 3), fill=c + (255,))
            d.point((x, y0), fill=shade(c, 1.3))
            d.line((x, y0 + 3, x + 3, y0 + 3), fill=shade(c, 0.65))
    return outlined(im)


def peat_spade():
    """A long turf-spade, left standing in the peat."""
    im = new()
    d = ImageDraw.Draw(im)
    d.line((19, 5, 15, 21), fill=(112, 88, 56, 255), width=2)
    d.line((15, 5, 22, 5), fill=(92, 72, 46, 255), width=2)
    d.polygon(((11, 21), (18, 22), (17, 28), (12, 27)), fill=(92, 92, 92, 255))
    d.line((11, 21, 12, 27), fill=(130, 130, 128, 255))
    return outlined(im)


def fen_stone(n):
    """A leaning stone, black with wet, moss up its north side; no two lean alike."""
    rng = random.Random("fen_stone%d" % n)
    lean = (-3, 2)[n - 1]
    im = new()
    d = ImageDraw.Draw(im)
    d.polygon([(10, 29), (22, 29), (20 + lean, 8), (16 + lean, 3), (12 + lean, 7)], fill=(62, 62, 60, 255))
    px = im.load()
    for y in range(S):
        for x in range(S):
            if px[x, y][3]:
                t = rng.random()
                c = (62, 62, 60)
                if x < 15 + lean * (29 - y) // 26:
                    c = (78, 78, 74)                                  # (lit on the west)
                if t < 0.2:
                    c = shade(c, 0.86)[:3]
                if (y < 16 and t > 0.72) or (y > 24 and t > 0.8):
                    c = (72, 92, 44)                                  # (moss)
                px[x, y] = c + (255,)
    return outlined(im)


def barge():
    """The whole wreck, three tiles by two: down by the stern, ribs showing, the mast's stump and a rag of sail."""
    rng = random.Random("barge")
    im = new(S * 3, S * 2)
    d = ImageDraw.Draw(im)
    d.polygon([(8, 36), (82, 22), (92, 30), (86, 44), (58, 56), (18, 58), (6, 48)], fill=(62, 48, 34, 255))
    px = im.load()
    for y in range(S * 2):                                       # (its planks, along the slope of it)
        for x in range(S * 3):
            if px[x, y][3]:
                band = (y + x // 6) // 5
                c = [(66, 50, 36), (58, 44, 32), (72, 56, 40), (54, 42, 30)][band % 4]
                if rng.random() < 0.12:
                    c = shade(c, 0.8)[:3]
                if rng.random() < 0.05 + 0.25 * (y > 46):
                    c = (70, 84, 46)                              # (weed, thick at the waterline)
                px[x, y] = c + (255,)
    d.polygon([(22, 40), (74, 28), (80, 32), (72, 40), (50, 48), (24, 50)], fill=(30, 24, 18, 255))   # (the hold)
    for x in (32, 44, 56, 66):                                    # (ribs across it)
        top = 39 - (x - 22) // 4
        d.line((x, top, x + 2, top + 12), fill=(84, 66, 46, 255), width=2)
    d.line((52, 36, 66, 3), fill=(82, 62, 42, 255), width=3)      # (the mast, broken off and leaning)
    d.polygon([(63, 9), (78, 15), (74, 24), (60, 16)], fill=(120, 112, 86, 255))     # (a rag of sail)
    d.line((70, 15, 66, 22), fill=(86, 80, 60, 255))
    d.rectangle((82, 28, 90, 34), fill=(96, 74, 48, 255))         # (the board on its stern, what's left of a name)
    d.line((83, 30, 89, 30), fill=(40, 30, 22, 255))
    out = outlined(im)
    d = ImageDraw.Draw(out)
    for x0, y0, x1 in ((4, 53, 14), (10, 60, 40), (46, 59, 62), (64, 52, 78), (88, 43, 94)):       # (scum round it)
        d.line((x0, y0, x1, y0), fill=(104, 106, 66, 255))
    return out


def peat_man():
    """What the cutters found: leather-brown, curled on his side in the peat, a band at his neck."""
    im = new()
    d = ImageDraw.Draw(im)
    d.ellipse((4, 12, 28, 29), fill=(36, 28, 20, 255))            # (the hollow he lies in)
    body = (108, 70, 38, 255)
    d.ellipse((17, 13, 25, 20), fill=body)                        # (the head)
    d.ellipse((8, 17, 22, 26), fill=shade(body, 0.86))            # (the back, curled)
    d.line((8, 23, 15, 27), fill=shade(body, 0.72), width=3)      # (the knees, drawn up)
    d.line((20, 21, 15, 24), fill=shade(body, 1.1), width=2)      # (an arm)
    d.point([(21, 16), (23, 16)], fill=(30, 20, 14, 255))
    d.line((17, 20, 22, 21), fill=(88, 112, 70, 255), width=1)    # (the torc)
    return outlined(im)


def lights(frame):
    """Three soft lights, greeny white, each drifting round its own spot, bright at the heart."""
    im = new()
    px = im.load()
    for i, (cx, cy, r) in enumerate(((10, 13, 7), (22, 11, 6), (16, 22, 6.5))):
        a = frame * math.pi / 2 + i * 2.1
        ox, oy = cx + 2 * math.cos(a), cy + 2 * math.sin(a * 2)
        for y in range(S):
            for x in range(S):
                d = math.hypot(x - ox, y - oy) / r
                if d < 1:
                    alpha = int(255 * (1 - d) ** 1.1)
                    if alpha > px[x, y][3]:
                        px[x, y] = (244, 255, 214, alpha) if d < 0.3 else (190, 240, 150, alpha)
    return im


def bell():
    """The great bell, tipped over and sunk to its shoulder: its crown up, bronze gone green, its flare under the scum."""
    rng = random.Random("bell")
    im = new()
    d = ImageDraw.Draw(im)
    d.arc((13, 1, 21, 9), 150, 390, fill=(120, 116, 70, 255), width=2)                 # (the crown it hung by)
    d.ellipse((7, 6, 26, 20), fill=(112, 104, 56, 255))                                # (its shoulder)
    d.polygon([(7, 13), (26, 13), (28, 24), (31, 28), (2, 28), (5, 24)], fill=(112, 104, 56, 255))    # (its waist, its flare)
    px = im.load()
    for y in range(S):
        for x in range(S):
            if y > 9 and px[x, y][3]:
                c = (112, 104, 56)
                if x < 11:
                    c = (148, 138, 78)                                                 # (the light on its west)
                elif x > 22:
                    c = (78, 72, 40)
                if y in (15, 16):
                    c = shade(c, 0.72)[:3]                                             # (a band cast round it)
                if rng.random() < 0.08 + 0.25 * (rng.randrange(6) == x % 6):
                    c = (84, 134, 104)                                                 # (verdigris, running down it)
                px[x, y] = c + (255,)
    out = outlined(im)
    d = ImageDraw.Draw(out)
    d.line((0, 28, 31, 28), fill=(104, 106, 66, 255))                                  # (the scum where it goes in)
    d.line((3, 30, 28, 30), fill=(88, 90, 56, 255))
    return out


def torc():
    im = new()
    d = ImageDraw.Draw(im)
    d.arc((7, 8, 25, 26), 40, 320, fill=(150, 110, 58, 255), width=3)
    d.ellipse((21, 8, 26, 13), fill=(176, 136, 70, 255))
    d.ellipse((21, 21, 26, 26), fill=(176, 136, 70, 255))
    return outlined(im)


def average(im):
    return Image.alpha_composite(Image.new("RGBA", im.size, (68, 66, 36, 255)), im).convert("RGB").resize(
        (1, 1), Image.BOX).getpixel((0, 0))


# ------------------------------------------------------------------ data
def tiles():
    t = Ini(p("data", "Tiles.ini"))

    def tile(name, pic, walk, words, **keys):
        write_image(p("sprites", "Tiles", name + ".png"), pic)
        for k, v in (("Walkable.Data", walk), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", words),
                     ("Line.of.Sight", "1")) + tuple((k.replace("_", "."), v) for k, v in keys.items()):
            t.set(name, k, v)
        SK.minimap_colour(name, average(pic))
    tile("Peat001", peat_ground(), OPEN, "Black peat, cut over and cut again.", Walk_Speed="0.7", Blend="6",
         Blend_Texture="Peat001", Round="1")
    for i, (left, right) in enumerate(((True, False), (False, False), (False, True)), 1):
        tile("Peat_Cut%03d" % i, peat_cut(left, right), TRENCH, "A peat cutting, a spade wide. The water in it is "
             "black and has no bottom you'd care to find.", Layer="Decor", Foam="0")
    for n in (1, 2):
        tile("Peat_Stack%03d" % n, peat_stack(n), SOLID, "Peat stacked to dry. It has been dry for years, and wet "
             "again, and dry.", Layer="Decor")
        tile("Fen_Stone%03d" % n, fen_stone(n), SOLID, "A leaning stone, black with wet. Whoever set it up meant "
             "it to stand straight.", Layer="Decor")
    tile("Peat_Spade001", peat_spade(), OPEN, "A turf-spade, left standing. Nobody leaves a good spade.", Layer="Decor")
    wreck = barge()
    for j in range(2):
        for i in range(3):
            pic = wreck.crop((i * S, j * S, (i + 1) * S, (j + 1) * S))
            tile("Sunken_Barge%03d" % (j * 3 + i + 1), pic, NONE, "A barge gone down by the stern. What's left of the "
                 "board on it reads THE UNSINKABLE.", Layer="Decor", Foam="0")
    t.save(p("data", "Tiles.ini"))


def entities():
    e = Ini(p("data", "Entities.ini"))
    for name, pic, keys in (
            ("Peat_Man", peat_man(), (("Type", "StaticObject"), ("Use.Words", "Search,Examine"), ("Solid", "1"),
                                      ("Examine.Info", "A man the peat kept: leather-brown, curled up as if asleep, "
                                                       "older than any name you know. He looks better than most of "
                                                       "the foremen you've met."))),
            ("Drowned_Bell", bell(), (("Type", "StaticObject"), ("Use.Words", "Ring,Examine"), ("Solid", "1"),
                                      ("Examine.Info", "A great bell, sunk to its shoulder, green with age. The "
                                                       "Abbey's arms are on it. Whoever stole it got this far."))),
            ("Old_Torc", torc(), (("Type", "MapItem"), ("Display.Name", "Old Torc"), ("Stackable", "1"), ("Value", "60"),
                                  ("Examine.Info", "A neck-ring of twisted bronze, old past telling. It smells of "
                                                   "peat, and always will.")))):
        write_image(p("sprites", "Entities", name + ".png"), pic)
        for k, v in keys:
            e.set(name, k, v)
    write_image(p("sprites", "Entities", "Marsh_Lights.png"), lights(0))
    for f in range(4):
        write_image(p("sprites", "Entities", "Marsh_Lights%d.png" % (f + 1)), lights(f))
    for k, v in (("Type", "StaticObject"), ("Use.Words", "Reach For,Examine"), ("Solid", "0"), ("Light", "70"),
                 ("Anim.Frames", "4"), ("Anim.Speed", "380"),
                 ("Examine.Info", "Lights where no lamp is, hanging in the ring at about the height of a hand.")):
        e.set("Marsh_Lights", k, v)
    e.save(p("data", "Entities.ini"))
    s = Ini(p("data", "Shards.ini"))
    if s.get("Shards", "Marsh.Wisp") is None:
        s.section("Shards")[1].append((None, "; Marsh.*: what the marshes' places give, once each (build_marsh_places.py)."))
    for k, v in SHARDS:
        s.set("Shards", k, v, overwrite=False)
    s.save(p("data", "Shards.ini"))


def scripts():
    def chest(name, attr, items, empty="The chest is empty."):
        rows = [(">Distance.From.Clicked.Entity", "48", "@far"), (">Conditional", "$Attr.%s=0" % attr, "@empty"),
                ("Update.Attribute", attr, "=1"), ("Play.Sound", "Chest")]
        rows += [("Give.Item", item, n) for item, n in items]
        rows += [("End",), ("@empty",), ("Display.Message", "Cyan", empty, "Empty"), ("End",),
                 ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)]
        SK.write_script(name, rows, MAKER)
    chest("Open Sunken_Barge_Hold", "SunkenBargeHold", [("Gold_Coin(s)", 45), ("Ale", 2), ("Emerald", 1),
                                                        ("Healing_Draught", 1)])
    chest("Open Peat_Cutters_Box", "PeatCuttersBox", [("Gold_Coin(s)", 25), ("Bread", 2), ("Cooked_Meat", 1)])
    chest("Search Peat_Man", "PeatManSearched", [("Old_Torc", 1), ("Shard", "$Shards.Marsh.Peat.Man")],
          "He has nothing more to give you, and has been very good about it.")
    SK.write_script("Reach For Marsh_Lights", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        (">Conditional", "$Attr.MarshLights<3", "@spent"),
        ("Update.Attribute", "MarshLights", "+1"),
        (">Conditional", "$Attr.MarshLights<3", "@caught"),
        (">Conditional", "$Attr.MarshLights<2", "@again"),
        ("Display.Message", "Cyan", "The light slides off between your fingers, the way a fish does."),
        ("End",),
        ("@again",),
        ("Display.Message", "Cyan", "You reach again. It waits until you've nearly got it. You'd swear it's enjoying this."),
        ("End",),
        ("@caught",),
        ("Play.Sound", "Absorb"),
        ("Give.Item", "Shard", "$Shards.Marsh.Wisp"),
        ("Display.Message", "Yellow", "Your hand closes on something cold, and it's gone, up your arm and into you. The "
                                      "other lights back off and look at you differently.", "-"),
        ("End",),
        ("@spent",),
        ("Display.Message", "Cyan", "The lights keep just out of reach now. They've learned."),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    SK.write_script("Ring Drowned_Bell", [
        (">Distance.From.Clicked.Entity", "48", "@far"),
        ("Play.Sound", "Bell"),
        ("Display.Message", "Cyan", "The bell speaks once, low and green, and every frog in the marsh stops to listen."),
        ("Wait", "2"),
        (">Conditional", "$Attr.DrownedBell=0", "@again"),
        ("Update.Attribute", "DrownedBell", "=1"),
        ("Play.Sound", "Splash"),
        ("Give.Item", "Shard", "$Shards.Marsh.Bell"),
        ("Give.Item", "Gold_Coin(s)", "30"),
        ("Display.Message", "Yellow", "Out in the water something answers, a little flat, and what the ringing shook "
                                      "loose comes up out of the mud at your feet.", "-"),
        ("End",),
        ("@again",),
        ("Display.Message", "Cyan", "The frogs start up again, louder, as if they've been told."),
        ("End",),
        ("@far",), ("Display.Message", "DarkRed", "You are too far away!", "Denied"), ("End",)], MAKER)
    more = (("Something else...", "@top"), ("I'll leave you to it.", "@end"))
    SK.write_script("Talk to Eel_Catcher", [
        ("@top",),
        SK.say("Fisherman", "Mind the third plank. And the fifth. Truth be told, mind all of 'em.",
               ("What do you catch out here?", "@eels"), ("Seen anything odd?", "@odd"),
               ("Is that eel I can smell?", "@gift"), ("I'll leave you to it.", "@end")),
        ("@eels",),
        SK.say("Fisherman", "Eels. Long ones. A short one's only an eel that hasn't finished. There's a fat lot lie off "
                            "the end of my jetty, if you've the patience and a rod. I've the patience.",
               ("Doesn't the damp get to you?", "@damp"), *more),
        ("@damp",),
        SK.say("Fisherman", "What damp? (Water runs off the brim of his hat and into his boot.)", *more),
        ("@odd",),
        SK.say("Fisherman", "There's a bell north of here that rings when nobody's by. Doesn't bother the eels. They "
                            "say there's lights out west in the Mirefen, too, but they say a lot of things in the "
                            "Mirefen. They've nobody to stop 'em.", *more),
        ("@gift",),
        (">Conditional", "$Attr.EelCatcherGift=0", "@none"),
        ("Update.Attribute", "EelCatcherGift", "=1"),
        ("Give.Item", "Cooked_Cave_Eel", "1"),
        SK.say("Fisherman", "That's the smell of a good eel. Here. Don't ask me how long it's been smoked, I've lost "
                            "count and so has it.", *more),
        ("@none",),
        SK.say("Fisherman", "You've had yours. The rest are spoken for. I've spoken for them.", *more),
        ("@end",),
        ("End",)], MAKER)
    for label, where in (("The Sunken Barge", "Sunken_Barge"), ("The Peat Cuttings", "Peat_Cuttings"),
                         ("The Wisp Ring", "Wisp_Ring"), ("The Eel-Catcher's Hut", "Eel_Catchers_Hut"),
                         ("The Drowned Bell", "Drowned_Bell_Site")):
        SK.place_label("Places", label, where)


# ------------------------------------------------------------------ the maps
def steps(points):
    """Every cell along these straight stretches."""
    out = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        x, y = x0, y0
        while (x, y) != (x1, y1):
            if x != x1:
                x += 1 if x1 > x else -1
            else:
                y += 1 if y1 > y else -1
            out.append((x, y))
    return out


def once(w, gx, gy, kind, name, extra="", dy=0):
    """A thing on the map, unless it's there already."""
    m, _, _ = w.at(gx, gy)
    if not any(ln.split("\t")[:2] == [kind, name] and (not extra or extra in ln) for ln in m.ents):
        w.place(gx, gy, kind, name, extra, dy)


def planks(w, cells):
    for x, y in cells:
        w.set(x, y, tile="Boardwalk001", decor="")


def the_barge(w):
    planks(w, steps(SPUR))
    x0, y0 = BARGE
    for j in range(2):
        for i in range(3):
            w.set(x0 + i, y0 + j, tile="Bog001", decor="Sunken_Barge%03d" % (j * 3 + i + 1))
    once(w, x0, y0 + 1, "StaticObject", "Chest", "Id=Sunken_Barge_Hold Lock=3")
    w.place_id(SPUR[-1][0], SPUR[-1][1], "Sunken_Barge")


def the_cuttings(w):
    cx, cy, rx, ry = PEAT
    for gy in range(cy - int(ry) - 3, cy + int(ry) + 4):
        for gx in range(cx - rx - 3, cx + rx + 4):
            d = ((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2
            if d < 0.45 + 1.2 * fbm(gx, gy, 3, 961):           # (a ragged edge: it was dug where it was good)
                w.set(gx, gy, tile="Peat001", decor="")
    for y, x0, x1 in CUTS:
        for x in range(x0, x1 + 1):
            w.set(x, y, decor="Peat_Cut%03d" % (1 if x == x0 else 3 if x == x1 else 2))
    for (x, y), d in (((-85, 76), "Peat_Stack001"), ((-84, 76), "Peat_Stack002"), ((-84, 82), "Peat_Stack001"),
                      ((-85, 82), "Peat_Spade001"), ((-96, 78), "Tent001")):
        w.set(x, y, decor=d)
    once(w, -95, 78, "StaticObject", "Chest", "Id=Peat_Cutters_Box Lock=2")
    once(w, -84, 79, "StaticObject", "Peat_Man")
    zone = w.zone(cx - rx - 1, 74, cx + rx + 1, 83, -83, 78)
    once(w, -83, 78, "NPC", "Bog_Troll", "Attitude=Bad Zone=%s Id=Peat_Cuttings_Troll" % zone, dy=-8)
    w.place_id(-90, 78, "Peat_Cuttings")


def the_ring(w):
    cx, cy = RING
    for gy in range(cy - 4, cy + 5):
        for gx in range(cx - 4, cx + 5):
            if (gx - cx) ** 2 + (gy - cy) ** 2 <= 18:
                w.set(gx, gy, decor="")
    for i, (dx, dy) in enumerate(RING_STONES):
        w.set(cx + dx, cy + dy, decor="Fen_Stone%03d" % (1 + i % 2))
    once(w, cx, cy, "StaticObject", "Marsh_Lights")
    w.place_id(cx, cy + 1, "Wisp_Ring")


def the_hut(w):
    hx, hy = HUT
    for gy in range(hy - 1, hy + 7):                               # (firm ground round it: nothing growing in the way)
        for gx in range(hx - 1, hx + 6):
            if (w.tile(gx, gy) or "").startswith("Marsh"):
                w.set(gx, gy, decor="")
    walls = [["Timber_Thin_Plank008", "Timber_Thin_Plank001", "Timber_Thin_Plank005"],
             ["Timber_Thin_Plank004", "Plank001", "Timber_Thin_Plank002"],
             ["Timber_Thin_Plank007", "Timber_Thin_Plank003", "Timber_Thin_Plank006"]]
    roofs = [0, 2, 3, 4]                                           # (its roof's rows, ridge to eaves)
    for j in range(4):
        for i in range(5):
            col = 0 if i == 0 else 2 if i == 4 else 1
            wall = walls[0 if j == 0 else 2 if j == 3 else 1][col]
            w.put(hx + i, hy + j, "%s+Roof(Thatch_Roof%03d.77)" % (wall, roofs[j] * 3 + col + 1))
    for i in range(5):
        w.put(hx + i, hy + 4, "Door001" if i == 2 else "Timber001+Decor(Timber_Window001)" if i in (1, 3) else "Timber001")
    for (dx, dy), d in (((1, 0), "Bed001"), ((1, 1), "Bed002"), ((3, 0), "Table001")):
        t, over = parts(w.cell(hx + dx, hy + dy))
        over["Decor"] = d
        w.put(hx + dx, hy + dy, join(t, over))
    planks(w, steps(JETTY))
    end = JETTY[-1]
    once(w, end[0] - 1, end[1], "StaticObject", "Eel_Spot")
    once(w, 261, 456, "NPC", "Fisherman", "Attitude=Good Stand=1 Face=W Schedule=Always Id=Eel_Catcher Name=Old_Silt",
         dy=-8)
    w.place_id(hx + 2, hy + 5, "Eel_Catchers_Hut")


def the_bell(w):
    x, y = BELL
    w.set(x, y, tile="Bog001", decor="")
    once(w, x, y, "StaticObject", "Drowned_Bell")
    w.place_id(x, y + 1, "Drowned_Bell_Site")


def main():
    tiles()
    entities()
    scripts()
    w = World(0)
    the_barge(w)
    the_cuttings(w)
    the_ring(w)
    the_hut(w)
    the_bell(w)
    w.save()
    print("The marshes' places: done")


if __name__ == "__main__":
    main()
