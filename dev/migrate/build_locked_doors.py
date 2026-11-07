"""Locked doors in the towns, and two locked yards (the owner's wish).

  * Some houses are someone's private home: their door is locked for good, with words of its own that say so (no key
    anywhere, nothing to find). A few more are long empty and boarded up (Door_Boards001, planks nailed across the
    door: a decor tile over it). Never a room with a ladder or a hatch (a floor nobody could reach), nor anyone's
    Home= (they'd be shut out of their own bed).
  * Some doors can be picked (the Lock line's Pick=<Stealth level>: dsengine/locks.py): their message is the
    pickable one ("The lock looks as if you could pick it."), and what's left lying inside is yours once (Once=1).
  * Two yards behind wrought-iron railings, Northport's bonded yard and Ashford's pound: a gate chained shut (Pick=24:
    very high Stealth), and a few things lying in the yard that Grasp reaches through the railings (it needs only to
    see them, and they lie within its reach of the railings).
  * Iron_Gate001/002: a gate in the iron railings, shut and open (drawn with fence_tiles.py's iron).

Safe to run again (what's done is left as it is). Then: validate.py, tools/export_web_assets.py, build_minimaps.py.

  python -I "dev\\migrate\\build_locked_doors.py"
"""
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, write_image          # noqa: E402
import fence_tiles as F                         # noqa: E402
from build_isle import Map                      # noqa: E402

TW = 32
OPEN = "1" * 49

# (map, door tile, what it says): a private home, locked for good
PRIVATE = [
    ("11,-1,0", (10, 7), "Locked. Whoever lives here likes it that way."),
    ("16,21,0", (9, 15), "Barred on the inside, against the cold and anyone in it."),
    ("-8,15,0", (2, 11), "Locked. Somewhere inside a dog barks once, then thinks better of it."),
    ("-7,16,0", (10, 13), "A noble's door, locked. Nobody here answers to strangers."),
    ("19,5,0", (7, 11), "The handle is cold as ice and won't turn. A wizard's house keeps its own door."),
    ("25,17,0", (8, 10), "Locked. A soldier's family lives here, and they keep to themselves."),
    # Galaith (the owner's wish: more of its houses locked, most of them pickable)
    ("-10,16,0", (19, 15), "Locked. The family's at their country house, and their door's gone with them."),
    ("-8,17,0", (13, 8), "Locked tight. Whoever trades from here keeps the stock and the door shut."),
]
# (map, door tile, what it says): long empty, boarded up
BOARDED = [
    ("10,23,0", (23, 9), "Boarded up. The marsh damp has swollen the planks fast."),
    ("1,8,0", (5, 17), "Nailed shut, the planks grey with years."),
    ("-7,16,0", (3, 21), "Boarded up since the dragon's fire. Nobody's coming back to it."),
]
# (map, door tile, Stealth to pick it, what's lying inside: [(item, how many)])
PICKABLE = [
    ("21,13,0", (3, 14), 4, [("Gold_Coin(s)", 12)]),
    ("26,6,0", (16, 17), 6, [("Gold_Coin(s)", 20), ("Minor_Healing_Draught", 1)]),
    ("5,4,0", (9, 13), 7, [("Silver_Ring", 1), ("Gold_Coin(s)", 18)]),
    ("20,4,0", (12, 12), 9, [("Gold_Coin(s)", 30), ("Healing_Draught", 1)]),
    ("17,21,0", (15, 16), 10, [("Emerald", 1), ("Gold_Coin(s)", 25)]),
    ("26,19,0", (19, 14), 12, [("Gold_Ring", 1), ("Gold_Coin(s)", 40)]),
    ("-8,16,0", (14, 5), 14, [("Ruby", 1), ("Gold_Coin(s)", 60)]),
    # Galaith: a noble's, two in the Merchants' quarter, the rest the hovels (a little, and easy)
    ("-10,15,0", (17, 16), 15, [("Sapphire", 1), ("Gold_Coin(s)", 55)]),
    ("-7,12,0", (14, 21), 10, [("Silver_Ring", 1), ("Gold_Coin(s)", 30)]),
    ("-5,17,0", (5, 18), 8, [("Gold_Coin(s)", 20), ("Healing_Draught", 1)]),
    ("-5,16,0", (7, 17), 7, [("Gold_Coin(s)", 15), ("Minor_Healing_Draught", 1)]),
    ("-6,17,0", (7, 19), 6, [("Gold_Coin(s)", 14)]),
    ("-5,15,0", (9, 16), 5, [("Silver_Ring", 1)]),
    ("-6,16,0", (16, 13), 5, [("Gold_Coin(s)", 10), ("Bread", 1)]),
    ("-6,13,0", (8, 16), 4, [("Gold_Coin(s)", 8), ("Minor_Healing_Draught", 1)]),
    ("-6,17,0", (14, 6), 4, [("Gold_Coin(s)", 4), ("Minor_Healing_Draught", 1)]),
    ("-6,17,0", (22, 20), 3, [("Gold_Coin(s)", 6)]),
    ("-6,16,0", (10, 7), 3, [("Gold_Coin(s)", 5), ("Bread", 1)]),
]
YARD_PICK = 24
YARD_MESSAGE = "The gate's chained shut. The lock looks as if you could pick it."
# map, railings' corners (x1, y1, x2, y2), the gate (on the railings), what stands in it, what lies in it
YARDS = [
    ("5,5,0", (13, 13, 19, 17), (16, 17),
     [((14, 14), "Crate001"), ((18, 14), "Barrel001"), ((14, 16), "Sacks001")],
     [((16, 14), "Sapphire", 1), ((15, 15), "Gold_Coin(s)", 75), ((17, 16), "Healing_Draught", 2),
      ((18, 15), "Gold_Ring", 1)]),
    ("12,-1,0", (9, 10, 15, 14), (12, 10),
     [((10, 13), "Crate001"), ((14, 11), "Barrel001"), ((14, 13), "Crate001")],
     [((12, 12), "Emerald", 1), ((11, 11), "Gold_Coin(s)", 60), ((13, 13), "Healing_Draught", 2),
      ((10, 11), "Silver_Ring", 1)]),
]


# ---------------------------------------------------------------- art
def picture(img, a):
    img = np.clip(np.round(img), 0, 255).astype(np.uint8)
    a = np.clip(np.round(a), 0, 255).astype(np.uint8)
    img[a == 0] = 0
    return Image.fromarray(np.dstack([img, a]), "RGBA")


def gate_post(img, a, x0):
    """A stone-footed iron post with a gilt finial, its left edge at x0 (as the railings' posts)."""
    XS, YS, B = F.XS, F.YS, F.BASE
    black, gold = np.array((34, 34, 40)) * 1.2, np.array((214, 172, 60))
    F.shadow(img, a, (XS >= x0 + 1) & (XS <= x0 + 6) & (YS >= B + 1) & (YS <= B + 3), 0.4)
    F.put(img, a, (XS >= x0 - 1) & (XS <= x0 + 4) & (YS >= B - 2) & (YS <= B), np.array((150, 146, 140)))
    post = (XS >= x0) & (XS <= x0 + 3) & (YS >= B - 17) & (YS <= B - 3)
    F.put(img, a, post, black)
    F.shade(img, post & (XS == x0), 1.8)
    ball = ((XS + 0.5 - (x0 + 2)) ** 2 + (YS + 0.5 - (B - 19)) ** 2) <= 3.2
    F.put(img, a, ball, gold)


def iron_gate(shut):
    """The gate across an east-west run of railings: two leaves between two posts, chained and padlocked at the
    middle (shut); open, each leaf swung back against its post (seen edge on, running south)."""
    XS, YS, B, S = F.XS, F.YS, F.BASE, F.S
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    black, hi, gold = np.array((34, 34, 40)), np.array((92, 94, 106)), np.array((214, 172, 60))
    if shut:
        x0, x1 = 3, S - 4
        F.shadow(img, a, (XS >= x0) & (XS <= x1) & (YS >= B + 1) & (YS <= B + 2), 0.35)
        for y in (B - 14, B - 7, B - 1):                                   # the leaves' rails
            F.put(img, a, (XS >= x0) & (XS <= x1) & (YS == y), black)
        for px in range(x0 + 1, x1 + 1, 3):                                # bars, spear tips a little higher
            F.put(img, a, (XS == px) & (YS >= B - 16) & (YS <= B), black)
            F.put(img, a, (XS == px) & (YS == B - 17), hi)
        F.put(img, a, (XS >= x0) & (XS <= x1) & (YS == B - 15), hi * 0.9)
        for x in (15, 16):                                                 # where the leaves meet
            F.put(img, a, (XS == x) & (YS >= B - 16) & (YS <= B), black * 1.3)
        for x, y in ((13, B - 10), (14, B - 9), (17, B - 9), (18, B - 10), (13, B - 8), (18, B - 8)):
            F.put(img, a, (XS == x) & (YS == y), hi * 1.2)                 # the chain round them
        F.put(img, a, (XS >= 14) & (XS <= 17) & (YS >= B - 8) & (YS <= B - 4), gold * 0.85)    # the padlock
        F.put(img, a, (XS >= 15) & (XS <= 16) & (YS == B - 6), black)
        F.shade(img, (XS == 17) & (YS >= B - 8) & (YS <= B - 4), 0.7)
    else:
        for x0 in (4, S - 7):                                              # each leaf, edge on
            F.shadow(img, a, (XS >= x0 + 2) & (XS <= x0 + 3) & (YS >= B - 6) & (YS <= B + 9), 0.35)
            F.put(img, a, (XS >= x0) & (XS <= x0 + 1) & (YS >= B - 16) & (YS <= B + 7), black)
            for py in range(B - 15, B + 8, 3):
                F.put(img, a, (XS >= x0) & (XS <= x0 + 1) & (YS == py), hi)
    gate_post(img, a, 0)
    gate_post(img, a, S - 4)
    return picture(img, a)


def boards():
    """Two weathered planks nailed across a doorway (a decor tile: the door shows round them)."""
    S = F.S
    img, a = np.zeros((S, S, 3)), np.zeros((S, S))
    plank, dark, nail = np.array((132, 116, 94)), np.array((92, 80, 64)), np.array((58, 56, 54))
    YS, XS = F.YS, F.XS
    for y0, slope in ((8, 0.12), (19, -0.1)):
        mid = y0 + (XS - 16) * slope
        m = (np.abs(YS - mid) <= 2.5) & (XS >= 1) & (XS <= S - 2)
        F.shadow(img, a, (np.abs(YS - mid - 3) <= 1) & (XS >= 2) & (XS <= S - 1), 0.35)
        F.put(img, a, m, plank)
        F.shade(img, m & (YS > mid + 1.2), 0.75)                           # its lower edge
        F.put(img, a, m & (YS < mid - 1.6), plank * 1.15)                  # the light along its top
        for gx in (5, 13, 22):                                             # the grain
            F.put(img, a, m & (XS >= gx) & (XS <= gx + 3) & (np.abs(YS - mid) < 0.6), dark)
        for nx in (3, S - 5):
            F.put(img, a, (XS == nx) & (np.abs(YS - (y0 + (nx - 16) * slope)) < 0.7), nail)
    return picture(img, a)


TILES = {   # name: (picture, Tiles.ini keys, minimap colour)
    "Iron_Gate001": (lambda: iron_gate(True), [
        ("Walkable.Data", OPEN), ("Show.Name", "1"), ("Use.Words", ""),
        ("Examine.Info", "A wrought-iron gate in the railings."), ("Line.of.Sight", "1"),
        ("Open.Tile", "Iron_Gate002"), ("Door", "1"), ("Piece", "a gate, shut (east-west)"), ("Layer", "Decor")],
        "40 40 46"),
    "Iron_Gate002": (lambda: iron_gate(False), [
        ("Walkable.Data", OPEN), ("Show.Name", "1"), ("Use.Words", ""), ("Examine.Info", "An open gate."),
        ("Line.of.Sight", "1"), ("Door", "1"), ("Piece", "a gate, open (east-west)"), ("Layer", "Decor")],
        "40 40 46"),
    "Door_Boards001": (boards, [
        ("Walkable.Data", OPEN), ("Show.Name", "1"), ("Use.Words", ""),     # (its Lock holds it shut, as a gate's)
        ("Examine.Info", "Planks nailed across a door."), ("Line.of.Sight", "0"), ("Layer", "Decor")],
        "112 96 76"),
}


def make_tiles():
    made = [n for n, (fn, _, _) in TILES.items() if write_image(p("sprites", "Tiles", n + ".png"), fn())]
    ini = Ini(p("data", "Tiles.ini"))
    for n, (_, keys, _) in TILES.items():
        for k, v in keys:
            ini.set(n, k, v, overwrite=True)                               # (this builder's own tiles)
    ini.save(p("data", "Tiles.ini"))
    colours = p("dev", "Minimap Colours.txt")
    have = "\n" + open(colours, encoding="cp1252").read()
    with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
        for n, (_, _, col) in TILES.items():
            if "\n%s\t" % n not in have:
                f.write("%s\t%s\n" % (n, col))
    print("Tiles: %s" % (", ".join(made) or "as they were"))


# ---------------------------------------------------------------- maps
def room_of(m, door):
    """The roofed cells behind a door (the room north of it: the roof group of the cell above it)."""
    x, y = door
    _, over = m.parts(x, y - 1)
    grp = over.get("Roof", "").rpartition(".")[2]
    if not grp:
        sys.exit("%s: no room behind the door at %d,%d" % (m.name, x, y))
    room, todo = set(), [(x, y - 1)]
    while todo:
        a, b = todo.pop()
        if (a, b) in room or not (1 <= a <= 25 and 1 <= b <= 21):
            continue
        r = m.parts(a, b)[1].get("Roof", "")
        if not r or r.rpartition(".")[2] != grp:
            continue
        room.add((a, b))
        todo += [(a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)]
    return room


def homes_on(m):
    """The tiles named in the map's NPCs' Home= (where they go to bed)."""
    out = set()
    for ln in m.ents:
        h = re.search(r"\bHome=(\S+)", ln) if ln.startswith("NPC\t") else None
        for box in (h.group(1).split("/") if h else []):
            x1, y1, x2, y2 = (int(v) for v in box.split(","))
            out |= {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)}
    return out


def check_room(m, door, sealed):
    """Stops if locking this door would shut someone out or cut off a floor."""
    room = room_of(m, door)
    if room & homes_on(m):
        sys.exit("%s: the room behind %d,%d is someone's home (Home=)" % (m.name, door[0], door[1]))
    for ln in m.ents:
        q = ln.split("\t")
        if q[0] == "NPC" and (int(float(q[2])) // TW + 1, int(float(q[3])) // TW + 1) in room:
            sys.exit("%s: someone lives behind %d,%d (%s)" % (m.name, door[0], door[1], q[1]))
    if sealed and any(re.match(r"(Ladder|Hatch)", m.decor(x, y)) for x, y in room):
        sys.exit("%s: the room behind %d,%d has a ladder or a hatch: never sealed for good" % (m.name, *door))
    return room


def lock_line(m, at, cond, message, pick=0):
    """Adds the Lock line (if the tile hasn't one already)."""
    x, y = at
    if any(re.match(r"Lock\t%d\t%d\t" % (x, y), ln) for ln in m.ents):
        return False
    m.ents.append("\t".join(["Lock", str(x), str(y), cond, message] + (["Pick=%d" % pick] if pick else [])))
    return True


def item_line(m, at, name, qty):
    x, y = at
    px, py = (x - 1) * TW, (y - 1) * TW
    if any(ln.startswith("MapItem\t%s\t%d\t%d\t" % (name, px, py)) for ln in m.ents):
        return False
    m.ents.append("\t".join(["MapItem", name, str(px), str(py), str(qty), "Once=1"]))
    return True


def free_floor(m, room, door):
    """The room's open floor (no decor, not by the door), nearest its middle first."""
    cx = sum(x for x, _ in room) / len(room)
    cy = sum(y for _, y in room) / len(room)
    cells = [(x, y) for x, y in room if not m.decor(x, y) and "Thin" not in m.tile(x, y) and
             abs(x - door[0]) + abs(y - door[1]) > 1]
    return sorted(cells, key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2, c))


def doors():
    n = 0
    maps = {}

    def get(name):
        if name not in maps:
            maps[name] = Map(name)
        return maps[name]
    for name, at, message in PRIVATE:
        m = get(name)
        check_room(m, at, True)
        n += lock_line(m, at, "", message)
    for name, at, message in BOARDED:
        m = get(name)
        check_room(m, at, True)
        if m.decor(*at) != "Door_Boards001":
            m.set(at[0], at[1], decor="Door_Boards001")
        n += lock_line(m, at, "", message)
    for name, at, pick, loot in PICKABLE:
        m = get(name)
        room = check_room(m, at, False)
        n += lock_line(m, at, "", "", pick)
        spots = free_floor(m, room, at)
        if len(spots) < len(loot):
            sys.exit("%s: no room for the loot behind %d,%d" % (name, *at))
        for spot, (item, qty) in zip(spots, loot):
            n += item_line(m, spot, item, qty)
    for m in maps.values():
        m.save()
    print("Doors: %d lines added" % n)


def yards():
    n = 0
    for name, (x1, y1, x2, y2), gate, things, loot in YARDS:
        m = Map(name)
        ring = {(x, y) for x in range(x1, x2 + 1) for y in (y1, y2)} | \
               {(x, y) for y in range(y1, y2 + 1) for x in (x1, x2)}
        for x, y in ring | {c for c, _ in things} | {c for c, _, _ in loot}:
            t, over = m.parts(x, y)
            if over.get("Roof") or (over.get("Decor") and not re.match(r"(Iron_Fence|Iron_Gate|Crate|Barrel|Sacks)",
                                                                         over["Decor"])):
                sys.exit("%s: %d,%d isn't open ground (%s)" % (name, x, y, m.rows[y - 1][x - 1]))
        for x, y in sorted(ring):
            if (x, y) == gate:
                m.set(x, y, decor="Iron_Gate001")
            else:
                m.set(x, y, decor=F.name("Iron", PIECE[joins(ring, x, y)]))
        for (x, y), decor in things:
            m.set(x, y, decor=decor)
        n += lock_line(m, gate, "", YARD_MESSAGE, YARD_PICK)
        for at, item, qty in loot:
            n += item_line(m, at, item, qty)
        m.save()
    print("Yards: %d lines added" % n)


PIECE = {sides: num for num, sides, _ in F.PIECES}


def joins(ring, x, y):
    """Which sides of x,y the railings run on (a gate counts as railings: it stands in the line)."""
    return "".join(k for k, (dx, dy) in zip("NESW", ((0, -1), (1, 0), (0, 1), (-1, 0))) if (x + dx, y + dy) in ring)


def main():
    make_tiles()
    doors()
    yards()


if __name__ == "__main__":
    main()
