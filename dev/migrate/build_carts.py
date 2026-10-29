"""Horses and carts that go round a city (dsengine/carts.py): the cart and its horse drawn as one, going all four ways
(sprites\\Walk\\Horse_Cart<dir><frame>), the clip-clop of its hooves and the whistle that hails it, its Entities.ini
section, and data\\Carts.ini's routes. Northport's and Galaith's carts stood at their stops and a carter whisked you to
another; now each city has one that goes round them all, along its streets, and the carters, carts and horses that
stood there are gone. A route already in Carts.ini (the owner's, or the map editor's) is left as it is.

  python -I "dev\\migrate\\build_carts.py"      (then validate.py, export_web_assets.py)
"""
import heapq
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import story_kit as K  # noqa: E402
import build_towns as BT  # noqa: E402
from story_kit import ini  # noqa: E402

MAKER = "build_carts.py"
W, H = 72, 60                       # (one picture for every way it faces: the horse and the cart behind it)
CARTS = os.path.join(K.ROOT, "data", "Carts.ini")
MAPS = os.path.join(K.ROOT, "maps")
SCRIPTS = os.path.join(K.ROOT, "data", "Scripts")
TOWNS = {"Northport": "Northport", "Galaith": "Galaith"}     # (the cities whose stops the old carts stood at)
# where a rider stands in it, facing each way: x, their feet, the top of the panel in front of them (Entities.ini
# Seat.<dir>: the page draws them over the cart above that line, so the box hides their legs)
SEATS = {1: (36, 52, 44), 2: (18, 46, 34), 4: (36, 25, 17), 8: (54, 46, 34)}

COAT, SHADE, LIGHT, MANE, HOOF = (146, 94, 52), (108, 66, 34), (178, 124, 76), (54, 34, 22), (40, 30, 24)
WOOD, DARK, PALE = (150, 104, 60), (96, 62, 32), (190, 140, 86)
IRON = (70, 64, 60)


# ================================================================== pictures
def wheel_side(s, cx, cy, r, turn):
    pg = K.pg()
    pg.draw.circle(s, DARK, (cx, cy), r)
    pg.draw.circle(s, WOOD, (cx, cy), r - 2)
    pg.draw.circle(s, IRON, (cx, cy), r, 1)                                  # (its iron tyre)
    for k in range(4):                                                       # the spokes, turning as it goes
        a = turn + k * math.pi / 4
        pg.draw.line(s, DARK, (cx - math.cos(a) * (r - 2), cy - math.sin(a) * (r - 2)),
                     (cx + math.cos(a) * (r - 2), cy + math.sin(a) * (r - 2)))
    pg.draw.circle(s, DARK, (cx, cy), 2)


def side(step):
    """Facing east: the cart's box (boards, a pale rail), a big spoked wheel, the shafts out to the horse in front."""
    pg = K.pg()
    s = K.surface(W, H)
    turn = {"a": 0.0, "b": 0.4, "c": 0.8}[step]
    pg.draw.line(s, DARK, (30, 41), (44, 43), 2)                             # (the far shaft)
    pg.draw.rect(s, DARK, (2, 33, 32, 16))                                   # the box
    pg.draw.rect(s, WOOD, (3, 34, 30, 13))
    for x in (10, 18, 26):
        pg.draw.line(s, DARK, (x, 35), (x, 46))
    pg.draw.line(s, PALE, (3, 34), (32, 34))                                 # (the rail along its top)
    pg.draw.line(s, SHADE, (3, 46), (32, 46))
    wheel_side(s, 16, 50, 9, turn)
    horse = BT.horse(step)
    s.blit(horse, (30, H - horse.get_height()))
    pg.draw.line(s, WOOD, (30, 44), (46, 45), 2)                             # (the near shaft, along the horse's side)
    return K.outlined(s)


def legs_front(s, xs, top, step, col):
    pg = K.pg()
    lift = {"a": (0, 0, 0, 0), "b": (2, 0, 0, 2), "c": (0, 2, 2, 0)}[step]
    for x, up in zip(xs, lift):
        pg.draw.line(s, col, (x, top), (x, top + 8 - up), 3)
        pg.draw.line(s, HOOF, (x - 1, top + 9 - up), (x + 1, top + 9 - up))


def wheel_end(s, x, y1, y2, step):
    """A wheel seen edge on (the cart going away from you, or towards you): a tall narrow ellipse, its tread moving."""
    pg = K.pg()
    pg.draw.ellipse(s, DARK, (x, y1, 5, y2 - y1))
    pg.draw.ellipse(s, WOOD, (x + 1, y1 + 1, 3, y2 - y1 - 2))
    k = {"a": 0, "b": 2, "c": 4}[step]
    for y in range(y1 + 2 + k, y2 - 2, 6):
        s.set_at((x + 2, y), DARK)


def coming(step):
    """Facing south, coming towards you: the cart behind (its open box and front board), the horse in front, head
    down, a pale blaze, its legs stepping."""
    pg = K.pg()
    s = K.surface(W, H)
    wheel_end(s, 18, 10, 34, step)                                           # the wheels, either side
    wheel_end(s, 49, 10, 34, step)
    pg.draw.rect(s, DARK, (22, 4, 28, 26))                                   # the box: inside it, from above
    pg.draw.rect(s, (110, 74, 40), (24, 6, 24, 11))
    pg.draw.rect(s, WOOD, (23, 17, 26, 12))                                  # its front board
    pg.draw.line(s, PALE, (23, 17), (48, 17))
    for x in (30, 37, 44):
        pg.draw.line(s, DARK, (x, 18), (x, 28))
    for x in (29, 43):                                                       # the shafts, down to the horse
        pg.draw.line(s, WOOD, (x, 29), (x, 40), 2)
    legs_front(s, (29, 33, 39, 43), 48, step, SHADE)
    pg.draw.ellipse(s, COAT, (27, 34, 18, 18))                               # the chest and body, end on
    pg.draw.ellipse(s, SHADE, (29, 44, 14, 6))
    pg.draw.lines(s, MANE, False, [(36, 30), (36, 36)], 4)                   # (the mane over its neck)
    pg.draw.ellipse(s, COAT, (32, 33, 9, 17))                                # the head, nose down, towards you
    pg.draw.line(s, (236, 222, 200), (36, 36), (36, 46), 2)                  # (a blaze)
    pg.draw.ellipse(s, SHADE, (33, 45, 7, 5))                                # (the muzzle)
    s.set_at((34, 39), (22, 14, 10))                                         # (its eyes)
    s.set_at((39, 39), (22, 14, 10))
    pg.draw.polygon(s, COAT, [(32, 34), (31, 30), (34, 33)])                 # its ears
    pg.draw.polygon(s, COAT, [(41, 34), (42, 30), (39, 33)])
    return K.outlined(s)


def going(step):
    """Facing north, going away from you: the horse ahead (its rump, tail and hind legs, its ears beyond), the cart
    behind it (inside the box, its tailboard)."""
    pg = K.pg()
    s = K.surface(W, H)
    pg.draw.polygon(s, COAT, [(32, 6), (31, 1), (34, 4)])                    # its ears, beyond its back
    pg.draw.polygon(s, COAT, [(40, 6), (41, 1), (38, 4)])
    pg.draw.ellipse(s, COAT, (32, 3, 8, 8))                                  # (the back of its head)
    pg.draw.lines(s, MANE, False, [(36, 4), (36, 12)], 3)
    legs_front(s, (30, 34, 38, 42), 22, step, SHADE)
    pg.draw.ellipse(s, COAT, (27, 8, 18, 20))                                # its back and rump, from behind
    pg.draw.line(s, LIGHT, (31, 12), (41, 12))
    tsw = {"a": 0, "b": 1, "c": -1}[step]
    pg.draw.lines(s, MANE, False, [(36, 18), (36 + tsw, 24), (36 + tsw, 29)], 3)   # the tail
    for x in (29, 43):                                                       # the shafts, from the cart to its sides
        pg.draw.line(s, WOOD, (x, 22), (x, 36), 2)
    wheel_end(s, 18, 38, 58, step)
    wheel_end(s, 49, 38, 58, step)
    pg.draw.rect(s, DARK, (22, 33, 28, 24))                                  # the box: inside it, from above
    pg.draw.rect(s, (110, 74, 40), (24, 35, 24, 9))
    pg.draw.rect(s, WOOD, (23, 44, 26, 12))                                  # its tailboard
    pg.draw.line(s, PALE, (23, 44), (48, 44))
    for x in (30, 37, 44):
        pg.draw.line(s, DARK, (x, 45), (x, 55))
    return K.outlined(s)


def pictures():
    pg = K.pg()
    for f in "abc":
        east = side(f)
        K.save("Walk", "Horse_Cart2" + f, east)
        K.save("Walk", "Horse_Cart8" + f, pg.transform.flip(east, True, False))
        K.save("Walk", "Horse_Cart4" + f, coming(f))
        K.save("Walk", "Horse_Cart1" + f, going(f))
    K.save("Entities", "Horse_Cart", side("a"))


# ================================================================== sounds
def hooves():
    """Clip, clop, clip, clop: hollow knocks on the cobbles, and the cart's wheels creaking under them."""
    out = []
    for i, f in enumerate((780, 620, 760, 600)):
        knock = K.tone(f, 0.05, harmonics=(1.0, 0.5, 0.25), attack=0.002, release=0.045)
        out += knock + K.silence(0.16 if i % 2 == 0 else 0.22)
    creak = K.tone(240, 0.3, harmonics=(1.0, 0.6, 0.4, 0.3), attack=0.05, release=0.12, glide=0.25, vibrato=0.04)
    return [a + 0.25 * (creak[i] if i < len(creak) else 0) for i, a in enumerate(out)]


def whistle():
    """Two fingers in the mouth: a sharp rising note, a gap, a long one falling away (hailing a cart)."""
    return (K.tone(1700, 0.13, attack=0.01, release=0.03, glide=0.25) + K.silence(0.05) +
            K.tone(2300, 0.32, attack=0.01, release=0.12, glide=-0.25, vibrato=0.01))


def sounds():
    K.wav("Hooves", hooves(), 0.7)
    # (Hail, a carter's "hoy!": build_soundscape.py)


# ================================================================== data
def data():
    keys = [("Type", "NPC"), ("Attitude", "Good"), ("Vehicle", "1"), ("Use.Words", "Hail,Get In,Examine"),
            ("Examine.Info", "A carthorse and its cart, going round the city. The horse knows the way. It has "
                             "always known the way."),
            ("Display.Name", "Horse and Cart"), ("Solid", "0"), ("Hitpoints", "100"), ("Respawn", "300"), ("Indoors", "0")]
    keys += [("Seat.%d" % d, "%d,%d,%d" % v) for d, v in sorted(SEATS.items())]
    K.section(K.ENTS, "Horse_Cart", keys)


# ================================================================== the routes, from the old carts' stops
def read_map(name):
    return open(os.path.join(MAPS, name + ".txt"), "rb").read().decode("cp1252").split("\r\n")


def old_stops(town):
    """[(place Id, its map, x, y, what the carters called it)] of the town's cart stops."""
    names = {}
    for fn in os.listdir(SCRIPTS):
        if fn.startswith("Talk to %s_Carter_" % town):
            text = open(os.path.join(SCRIPTS, fn), "rb").read().decode("cp1252")
            words = re.findall(r"\tTo (.+?)\.\t", text)
            dests = re.findall(r"Teleport\t(\S+)", text)
            for w, pid in zip(words, dests):
                names[pid] = w
    out = []
    for fn in os.listdir(MAPS):
        if not fn.endswith(".txt"):
            continue
        name = fn[:-4]
        for line in read_map(name):
            p = line.split("\t")
            if p[0] == "Id" and len(p) >= 4 and p[1].startswith("%s_Cart_Stop_" % town):
                out.append((p[1], name, int(p[2]), int(p[3]), names.get(p[1], p[1])))
    return sorted(out, key=lambda s: int(s[0].rsplit("_", 1)[1]))


ROADISH = ("Paving", "Cobble", "Flag", "Boardwalk", "Gravel", "Dirt001", "Plank001")


class Ground:
    """Level 0 a tile at a time, for the cart's way along the streets: what's walkable, what's a road."""
    def __init__(self):
        from dsengine.data import GameData
        from dsengine.maps import MapData
        self.d = GameData(K.ROOT)
        self.MapData = MapData
        self.maps = {}

    def map(self, mx, my):
        key = (mx, my)
        if key not in self.maps:
            name = "%d,%d,0" % (mx, my)
            self.maps[key] = self.MapData(self.d, name) if os.path.exists(os.path.join(MAPS, name + ".txt")) else None
        return self.maps[key]

    def cost(self, gx, gy):
        """What a step onto world tile gx, gy costs: a road 1, open ground 8, anything else (walls, water, a roof, a
        tree) can't be gone on."""
        xt, yt = self.d.xt, self.d.yt
        m = self.map(gx // xt, gy // yt)
        if m is None:
            return None
        c = m.cell(gx % xt + 1, gy % yt + 1)
        res = self.d.walk_res
        mid = res // 2 + res * (res // 2)                    # (its middle: where a wheel's line goes over it)
        if not m.tile[c] or m.roof[c] or len(m.walk[c]) <= mid or m.walk[c][mid] != "1":
            return None
        return 1 if m.tile[c].startswith(ROADISH) and not m.decor[c] else 8

    def way(self, a, b):
        """The cheapest way from world tile a to b: [tiles]."""
        best, came = {a: 0}, {}
        todo = [(0, 0, a)]
        while todo:
            _, d, c = heapq.heappop(todo)
            if c == b:
                break
            if d > best.get(c, 1e18) or d > 40000:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                k = self.cost(*n)
                if k is None and n != b:
                    continue
                nd = d + (k or 1)
                if nd < best.get(n, 1e18):
                    best[n], came[n] = nd, c
                    heapq.heappush(todo, (nd + abs(n[0] - b[0]) + abs(n[1] - b[1]), nd, n))
        if b not in came:
            return None
        out = [b]
        while out[-1] != a:
            out.append(came[out[-1]])
        return out[::-1]


def corners(tiles):
    """Only the tiles where the way turns (and its ends)."""
    out = [tiles[0]]
    for i in range(1, len(tiles) - 1):
        a, b, c = tiles[i - 1], tiles[i], tiles[i + 1]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(b)
    out.append(tiles[-1])
    return out


def routes(ground):
    have = {s for s, _ in ini.sections(CARTS)} if os.path.exists(CARTS) else set()
    xt, yt = ground.d.xt, ground.d.yt
    blocks = []
    for town, title in TOWNS.items():
        if town in have:
            print("%s: its route is in Carts.ini already (left as it is)" % town)
            continue
        stops = old_stops(town)
        if len(stops) < 2:
            continue
        world = []
        for pid, name, x, y, word in stops:
            mx, my, _ = (int(v) for v in name.split(","))
            world.append(((mx * xt + x - 1, my * yt + y - 1), word))
        order = [min(world, key=lambda s: s[0])]                # (from the westmost, each next the nearest)
        left = [s for s in world if s is not order[0]]
        while left:
            nxt = min(left, key=lambda s: abs(s[0][0] - order[-1][0][0]) + abs(s[0][1] - order[-1][0][1]))
            order.append(nxt)
            left.remove(nxt)
        points = []
        for i, (tile, word) in enumerate(order):
            if i == len(order) - 1:
                points.append((tile, word))
                break
            nxt = order[i + 1][0]
            way = ground.way(tile, nxt)
            if way is None:
                print("%s: no way from %s to the next stop" % (town, word))
                way = [tile, nxt]
            for k, t in enumerate(corners(way)[:-1]):
                points.append((t, word if k == 0 else ""))
        lines = ["Title=%s" % title, "Fare=2", "Wait=6", "Loop=0"]
        for n, ((gx, gy), word) in enumerate(points, 1):
            lines.append("Point%d=%d,%d,0,%d,%d%s" % (n, gx // xt, gy // yt, gx % xt + 1, gy % yt + 1,
                                                    "," + word if word else ""))
        blocks.append((town, lines))
        print("%s: %d stops, %d points" % (town, len(order), len(points)))
    if not blocks:
        return
    text = []
    if not os.path.exists(CARTS):
        text = ["; Horses and carts (dsengine/carts.py, dev/migrate/build_carts.py; the map editor draws and edits them).",
                "; [Route]: Title= (what it's called), Fare= (gold a ride), Wait= (seconds at each stop), Loop=1 (round",
                "; and round; else to the end and back). PointN=MAP,X,Y[,Stop name]: its way, a 1-based tile of map MAP",
                "; at a time, in a straight line from each to the next; a point with a name is a stop.", ""]
    else:
        text = open(CARTS, "rb").read().decode("cp1252").rstrip("\r\n").split("\r\n") + [""]
    for town, lines in blocks:
        text += ["[%s]" % town] + lines + [""]
    open(CARTS, "wb").write("\r\n".join(text).encode("cp1252"))
    ini.forget()


def clear_old(town):
    """The carts, horses and carters that stood at the stops, and the carters' scripts."""
    stops = old_stops(town)
    near = {}
    for _, name, x, y, _ in stops:
        near.setdefault(name, []).append((x, y))
    for name, spots in near.items():
        lines = read_map(name)
        keep = []
        for line in lines:
            p = line.split("\t")
            gone = p[0] == "NPC" and len(p) > 4 and re.search(r"\bId=%s_(Horse|Carter)_\d+\b" % town, p[4])
            if p[0] == "StaticObject" and len(p) > 3 and p[1] == "Cart":
                tx, ty = int(p[2]) // 32 + 1, int(p[3]) // 32 + 1
                gone = any(abs(tx - x) <= 3 and abs(ty - y) <= 3 for x, y in spots)
            if not gone:
                keep.append(line)
        if keep != lines:
            open(os.path.join(MAPS, name + ".txt"), "wb").write("\r\n".join(keep).encode("cp1252"))
            print("%s: its old cart stop cleared" % name)
    for fn in os.listdir(SCRIPTS):
        if fn.startswith("Talk to %s_Carter_" % town):
            K.remove_script(fn[:-4])


def main():
    pictures()
    sounds()
    data()
    routes(Ground())                    # (from the old stops' places: before the carters' scripts go)
    for town in TOWNS:
        clear_old(town)
    ini.forget()


if __name__ == "__main__":
    main()
