"""The Isle's ferries (the owner's wish): two boats you ride across the strait, one from each pier, casting off together
on the bell and passing each other halfway (dsengine/carts.py: a route with its own vehicle, kept to a timetable). The
boat is drawn from above, turning through sixteen headings as it goes and coming about at the pier
(sprites\\Walk\\Ferry_Boat_H<nn><frame>: a, tied up; b and c, under way, its wake and the steering oar), with its
ferryman at the stern and room amidships for whoever's aboard. Its Entities.ini section, its two routes in Carts.ini,
the ship's bell it comes in on, and Wim's words on both piers (he tells you about them; you step aboard and pay there).
Wim's old crossing (a fade and a teleport) is gone, and so is Bess's: the boats run for everyone, but Wim takes you
only once he's seen your papers (Mary's, under the floorboard in Tobias's house) and you're no longer green.

  python -I "dev\\migrate\\build_ferry.py"      (then validate.py, export_web_assets.py)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import story_kit as K  # noqa: E402

MAKER = "build_ferry.py"
NAME = "Ferry_Boat"
HEADINGS = 16
S = 88                              # (one square picture for every heading: the boat turns about its middle)
C = S / 2
L, B = 70, 26                       # (the hull's length and beam)
CARTS = os.path.join(K.ROOT, "data", "Carts.ini")
# (where whoever's aboard stands: amidships, their feet a little aft of the middle; the page hides them below the
# third number, so they stand down in the hull)
SEAT = (int(C), int(C) + 7, int(C) - 1)

HULL, HULL_DARK, PLANK, PLANK_DARK, RAIL = (112, 72, 40), (74, 46, 24), (170, 124, 78), (132, 92, 54), (198, 156, 102)
THWART, IRON, ROPE, FOAM = (92, 58, 30), (64, 60, 58), (196, 172, 120), (232, 242, 246)
SHIRT, SHIRT_DARK, HAIR, SKIN = (56, 76, 130), (34, 47, 80), (130, 130, 128), (226, 176, 150)
GLOW = (255, 214, 120)


# ================================================================== pictures
def half_width(t):
    """The hull's half-beam at t (-1 the bow's point .. 1 the stern): a fine bow, full amidships, a blunt transom."""
    if t < -0.15:
        k = (t + 1) / 0.85                                   # (0 at the point .. 1 where it's full)
        return B / 2 * math.sin(k * math.pi / 2) ** 0.8
    if t < 0.7:
        return B / 2
    return B / 2 * (1 - 0.32 * ((t - 0.7) / 0.3) ** 2)


def outline(inset=0.0, scale=1.0):
    """The hull's edge as points (x across, y along: the bow up), inset this far."""
    pts = []
    n = 26
    for i in range(n + 1):
        t = -1 + 2 * i / n
        pts.append((half_width(t) * scale - inset, t * L / 2 * scale + (inset * 0.6 if t < 0 else -inset * 0.4)))
    left = [(-x, y) for x, y in reversed(pts)]
    return [(max(0.0, x), y) for x, y in pts] + [(min(0.0, x), y) for x, y in left]


def rot(pts, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(C + x * c - y * s, C + x * s + y * c) for x, y in pts]


def line(surf, col, a, b, deg, width=1):
    p = K.pg()
    (x1, y1), (x2, y2) = rot([a, b], deg)
    p.draw.line(surf, col, (round(x1), round(y1)), (round(x2), round(y2)), width)


def poly(surf, col, pts, deg):
    K.pg().draw.polygon(surf, col, [(round(x), round(y)) for x, y in rot(pts, deg)])


def dot(surf, col, at, r, deg):
    (x, y), = rot([at], deg)
    K.pg().draw.circle(surf, col, (round(x), round(y)), r)


def wake(surf, deg, step):
    """Foam peeling off the bow and a trail behind the stern, under the boat (it's drawn first)."""
    shift = 3 if step == "c" else 0
    for k, (w, y) in enumerate(((B / 2 + 3, -L / 2 + 14), (B / 2 + 6, -L / 2 + 26), (B / 2 + 8, L / 2 - 6))):
        y += shift
        line(surf, FOAM + (200 - k * 40,), (w - 3, y - 6), (w + 1, y + 2), deg)
        line(surf, FOAM + (200 - k * 40,), (-w + 3, y - 6), (-w - 1, y + 2), deg)
    for k in range(3):
        y = L / 2 + 3 + k * 4 + shift
        line(surf, FOAM + (170 - k * 50,), (-5 + k, y), (5 - k, y), deg)


def boat(deg, step):
    pg = K.pg()
    s = K.surface(S, S)
    if step != "a":
        wake(s, deg, step)
    shadow = K.surface(S, S)                                  # (its shadow on the water, a little south and east)
    poly(shadow, (10, 30, 50, 70), [(x + 2, y + 3) for x, y in outline()], deg)
    s.blit(shadow, (2, 3))
    hull = K.surface(S, S)
    poly(hull, HULL_DARK, outline(), deg)                     # the hull's sides
    poly(hull, HULL, outline(1.2), deg)
    poly(hull, RAIL, outline(2.6), deg)                       # (the gunwale, pale along its top)
    poly(hull, PLANK, outline(4.4), deg)                      # the bottom boards
    for k in range(-5, 6):                                    # (the boards' seams, fore and aft)
        x = k * 2.2
        if abs(x) < B / 2 - 5:
            line(hull, PLANK_DARK, (x, -L / 2 + 14 + abs(k) * 1.6), (x, L / 2 - 6), deg)
    for y in (-L / 2 + 16, L / 2 - 14):                       # two thwarts to sit on, the middle left for standing
        hw = half_width(2 * y / L) - 3
        line(hull, THWART, (-hw, y), (hw, y), deg, 3)
        line(hull, PLANK_DARK, (-hw, y + 1), (hw, y + 1), deg)
    line(hull, HULL_DARK, (0, -L / 2 + 3), (0, -L / 2 + 10), deg, 2)    # (the stem)
    dot(hull, ROPE, (0, -L / 2 + 10), 3, deg)                 # a coil of rope in the bow
    dot(hull, PLANK_DARK, (0, -L / 2 + 10), 1, deg)
    dot(hull, IRON, (B / 2 - 6, -L / 2 + 20), 2, deg)         # the lantern on its post, lit
    dot(hull, GLOW, (B / 2 - 6, -L / 2 + 20), 1, deg)
    # the ferryman at the stern, side on to the steering oar over the transom
    sweep = {"a": 0.0, "b": -7.0, "c": 7.0}[step]
    line(hull, HULL_DARK, (3, L / 2 - 8), (3 + sweep * 0.6, L / 2 + 12), deg, 2)
    line(hull, PLANK_DARK, (3 + sweep * 0.6, L / 2 + 8), (3 + sweep * 0.7, L / 2 + 14), deg, 3)    # (its blade)
    dot(hull, SHIRT_DARK, (-1, L / 2 - 8), 5, deg)            # (his shoulders)
    dot(hull, SHIRT, (-1, L / 2 - 8), 4, deg)
    line(hull, SKIN, (1, L / 2 - 8), (3, L / 2 - 6), deg, 2)  # (an arm on the oar)
    dot(hull, HAIR, (-1, L / 2 - 9), 2, deg)                  # (his grey head, from above)
    s.blit(K.outlined(hull), (0, 0))
    return s


def pictures():
    for h in range(HEADINGS):
        deg = h * 360.0 / HEADINGS
        for step in "abc":
            K.save("Walk", "%s_H%02d%s" % (NAME, h, step), boat(deg, step))
    K.save("Entities", NAME, boat(90.0, "a"))


# ================================================================== the bell it comes in on
def bell():
    """Two strokes of a ship's bell, low and round (its partials a bell's, not a string's), each dying away."""
    def stroke(secs=2.0):
        out = []
        for i in range(int(K.RATE * secs)):
            t = i / K.RATE
            v = 0.0
            for ratio, amp, decay in ((0.5, 0.3, 1.4), (1.0, 1.0, 0.9), (2.0, 0.45, 0.55), (2.76, 0.3, 0.4),
                                      (5.4, 0.1, 0.18)):
                v += amp * math.exp(-t / decay) * math.sin(2 * math.pi * 196 * ratio * t)
            out.append(v * min(1.0, t / 0.003))
        return out
    one, gap = stroke(), int(K.RATE * 0.6)
    out = one + [0.0] * gap
    for i, v in enumerate(stroke()):
        out[gap + i] += 0.85 * v
    return out


# ================================================================== data
def data():
    keys = [("Type", "NPC"), ("Attitude", "Good"), ("Vehicle", "1"), ("Vehicle.Noun", "ferry"),
            ("Headings", str(HEADINGS)), ("Use.Words", "Get In,Examine"),
            ("Examine.Info", "The strait ferry: a broad, flat boat that's been tarred more times than anyone can count. "
                             "Its ferryman leans on the steering oar and watches the water, not you."),
            ("Display.Name", "Ferry"), ("Solid", "0"), ("Hitpoints", "100"), ("Respawn", "300"),
            ("Seat", "%d,%d,%d" % SEAT), ("Arrive.Sound", "Ferry_Bell"), ("Board.Sound", "Boat"),
            ("Board.Words", "%s: a boat leaves each pier on the bell, and they pass in the strait. A crossing is %s, "
                            "paid aboard."),
            ("Menu.Image", "%s_H04a" % NAME)]
    K.section(K.ENTS, NAME, keys)
    K.set_section(CARTS, "Isle_Ferry_East", route("east"))
    K.set_section(CARTS, "Isle_Ferry_West", route("west"))


# (the two lanes across the strait, a boat on each, so they pass and never meet: 1-based tiles; both tie up at the one
# berth by the Isle's pier stem, and at the one on the north of Northport's harbour pier, by Wim: they leave together,
# so only one is ever in at either, and the boat you watched go comes back to where it left)
LANES = {
    "east": ["3,2,0,14,15,the Isle", "3,2,0,14,21", "4,3,0,2,8", "4,4,0,7,3", "4,4,0,13,3,Northport"],
    "west": ["3,2,0,14,15,the Isle", "3,2,0,14,21", "3,3,0,23,8", "3,3,0,25,18", "3,4,0,25,3", "4,4,0,13,3,Northport"],
}
# (the boats cross for everyone; it's you they won't take: no papers, or too green yet)
NOT_YET = ("The ferryman shakes his head. \"Papers first, friend. Since the raids, Northport sends back anyone off the "
           "Isle without them. Wim on the pier will look them over.\"")      # (not begun with a quote: the ini drops it)
GREEN = ("The ferryman holds up a hand. \"You're green as grass yet, and you've never had a beast's leavings in your "
         "hands, by the look of you. See Brother Aldous, and come back at level 3.\"")


def route(lane):
    lines = ["Title=The strait ferry", "Vehicle=%s" % NAME, "Fare=1", "Wait=15", "Loop=0", "Timetable=1", "Speed=1.2",
             "Every=45", "Start=%s" % ("the Isle" if lane == "east" else "Northport"),
             "Requires=$Attr.Passage>=5", "Refused=%s" % NOT_YET,
             "Requires.2=$Attr.RemnantsAbsorbed>=1 and $Player.Level>=3", "Refused.2=%s" % GREEN,
             "Refused.Script=Talk to Ferryman"]          # (not yet: Wim says why, in a talk, not a chat line)
    lines += ["Point%d=%s" % (n, pt) for n, pt in enumerate(LANES[lane], 1)]
    return lines


def moored_boats_gone():
    """The boats tied up at the piers that never went anywhere (build_boats.py's): the ferries are the boats now."""
    for name, boat in (("3,2,0", "Boat002"), ("1,3,0", "Boat001")):
        if not K.map_exists(name):
            continue
        m = K.Map(name)
        kept = [ln for ln in m.ents if not ln.startswith("StaticObject\t%s\t" % boat)]
        if kept != m.ents:
            m.ents = kept
            m.save()
            print("%s: the moored %s taken away" % (name, boat))


def wim():
    """Wim on either pier: what the boats are; on the Isle, nobody aboard without papers (Passage to the Mainland: he
    reads yours, Mary's, and the quest's done), nor a green hand."""
    K.write_script("Talk to Ferryman", [
        ("Get.Value", "ATTRIBUTE", "Passage", "Variable.1$"),
        (">On.Map", "4,4,0", "@isle"),
        K.say("Ferryman", "Back to the Isle? The boats cross together, one from each pier, whenever the bell goes. Step "
                          "aboard when one's tied up here, and a coin's the fare.\\They pass each other halfway. "
                          "Wave, if you like. Nobody does.", ("Thanks, Wim.", "@end")),
        ("End",),
        ("@isle",),
        (">Conditional", "$Variable.1>=5", "@papers"),
        (">Conditional", "$Attr.RemnantsAbsorbed>=1 and $Player.Level>=3", "@green"),
        K.say("Ferryman", "Northport, is it? Step aboard when a boat's in, and pay a coin. They leave both piers on the "
                          "bell and pass in the strait.\\Nobody's lost a passenger in years. Well. Nobody's lost one "
                          "this year.", ("Thanks, Wim.", "@end")),
        ("End",),
        ("@green",),
        K.say("Ferryman", "Hold up, friend. You're green as grass yet, and you've never had a beast's leavings in your "
                          "hands, by the look of you. The mainland eats the likes of you: see Brother Aldous first, and "
                          "come back at level 3.", ("Fair enough.", "@end")),
        ("End",),
        ("@papers",),
        (">Conditional", "$Variable.1=4 and $Item.Marys_Papers>=1", "@none"),
        K.say("Ferryman", "Papers? Let's have a look, then.\\He unfolds them, and stops at the seal, and looks at you for "
                          "a long while.\\Well. That's not my business, and I'll not make it mine. Those'll get you past "
                          "any guard in Northport.\\And when you land: there's a shardstone by the market. Feed it a few "
                          "Shards and it wakes, and after that it'll carry you to any other shardstone you've woken. Mind "
                          "your Shards.", ("Thank you, Wim.", "@done")),
        ("@done",),
        ("Update.Attribute", "Passage", "=5"),
        ("Display.Message", "Yellow", "Quest complete: Passage to the Mainland!", "Quest"),
        (">Conditional", "$Attr.RemnantsAbsorbed>=1 and $Player.Level>=3", "@green"),
        K.say("Ferryman", "Step aboard when a boat's in, and a coin's the fare. They leave both piers on the bell.",
              ("Thanks, Wim.", "@end")),
        ("End",),
        ("@none",),
        (">Conditional", "$Variable.1=0", "@nopapers"),
        (">Quest.Can.Start", "Passage", "@nopapers"),
        K.say("Ferryman", "Cross the strait? Papers first, friend. Since the raids, Northport's guards send back anyone "
                          "off the Isle without papers, and I'm the one who has to bring them home again.\\Old Tobias "
                          "always wrote them, him keeping the Isle's roll, but nobody's seen him since the hobgoblins "
                          "came. Ask Bess, up at the farm: she's his daughter.", ("I will.", "@start")),
        ("@start",),
        ("Update.Attribute", "Passage", "=1"),
        ("Display.Message", "Yellow", "Quest started: Passage to the Mainland.", "Quest"),
        ("End",),
        ("@nopapers",),
        K.say("Ferryman", "Got your papers? No? Then no passage, friend. Northport would only send you back, and I'd "
                          "be the one bringing you.", ("I see.", "@end")),
        ("@end",), ("End",),
    ], MAKER)
    for old in ("Ferry to Northport", "Ferry to the Isle"):
        K.remove_script(old)


def main():
    pictures()
    K.wav("Ferry_Bell", bell(), 0.6)
    data()
    moored_boats_gone()
    wim()
    print("The strait ferries: %d pictures, two routes, Wim's words" % (HEADINGS * 3 + 1))


if __name__ == "__main__":
    main()
