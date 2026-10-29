"""Towns and cities, grown into the free ground of the maps a settlement is given (build_towns.py says which, and
what each has). Nothing that's there already moves: buildings, roads, quest places and the people with Ids stay;
new buildings go only on open ground (grass, dirt, sand, snow, ash...) with nothing on it but grass and flowers.

  * Ground: the maps of a settlement as one grid of world tiles (25 x 21 a map). New maps are made as land.
  * Buildings face the viewer, their door in the front (bottom) wall, a street below it; each stays inside one map
    (so its roof is whole). Every door is joined to the town's roads by a path (cobbles in a city, dirt elsewhere).
  * Streets of houses: two to four houses side by side on one street, the street named on a notice at its end.
  * A market square: paving, stalls with their traders, a fountain; the market's lanes (bakers, butchers...) are
    shops placed nearest it.
  * Inside each building (furnish): what its kind needs - a tavern's bar, barrels and tables, a bank's counter,
    a hospital's beds, a hall's benches, a jail's cells - and its people, their scripts and shops.
"""
import math
import random
from collections import deque

import story_kit as K
from story_kit import Map, TW, XT, YT, say
import villages as V

OPEN = ("Grass", "Dirt001", "Sand001", "Snow001", "Ash001", "Cinder001", "Marsh001", "Soil001", "Forest001")
SMALL = ("Flowers", "Pebbles", "Tall_Grass", "Fern", "Grass_Tuft", "Clover", "Daisies", "Weeds", "Bush", "Tree",
         "Oak_Tree", "Pine", "Snow_Pine", "Willow_Tree", "Yew_Tree", "Dead_Tree", "Cactus", "Berry_Bush", "Rock",
         "Desert_Rock", "Basalt_Rock", "Fallen_Log", "Mushroom_Patch", "Reeds", "Snow_Rock", "Ivy")
ROADS = ("Dirt001", "Paving001", "Plank001")
WILD = {"Rabbit", "Butterfly", "Blue_Butterfly", "Duck", "Rat", "Chicken", "Sheep", "Cow", "Dog", "Cat", "Black_Cat",
        "Ginger_Cat", "Bat"}
MAKER = "build_towns.py"


_WALK = {}


def walk_middle(name):
    """Can you stand in the middle of tile `name` (its Tiles.ini Walkable.Data, 7 x 7)?"""
    if name not in _WALK:
        data = K.ini.read(name, "Walkable.Data", "", K.TILES).strip()
        _WALK[name] = len(data) < 49 or data[24] == "1"
    return _WALK[name]


# ================================================================== the ground: maps as one grid
class Ground:
    def __init__(self, names, base="Grass001"):
        self.maps = {}
        self.new = set()
        for n in names:
            if K.map_exists(n):
                self.maps[n] = Map(n)
            else:
                m = Map(n, new=True)
                for y in range(1, YT + 1):
                    for x in range(1, XT + 1):
                        m.put(x, y, base, {})
                self.maps[n] = m
                self.new.add(n)
        self.taken = set()                      # (gx, gy): new buildings and their walls
        self.blocked = set()                    # what stands there already: things, places, locks, triggers
        for n, m in self.maps.items():
            mx, my = self.mxy(n)
            for ln in m.ents:
                f = ln.split("\t")
                try:
                    if f[0] in ("NPC", "StaticObject", "MapItem"):
                        if f[0] == "NPC" and f[1] in WILD and "Id=" not in ln:
                            continue
                        x, y = int(float(f[2])) // TW + 1, (int(float(f[3])) + 24) // TW + 1
                        for yy in (y - 1, y):
                            self.blocked.add((mx * XT + x - 1, my * YT + yy - 1))
                    elif f[0] in ("Id", "Trigger"):
                        self.blocked.add((mx * XT + int(f[2]) - 1, my * YT + int(f[3]) - 1))
                    elif f[0] == "Lock":
                        self.blocked.add((mx * XT + int(f[1]) - 1, my * YT + int(f[2]) - 1))
                except (ValueError, IndexError):
                    pass
            for y in range(1, YT + 1):                  # (and the ground round every door: its way in stays open)
                for x in range(1, XT + 1):
                    c = m.rows[y - 1][x - 1]
                    if c.startswith("Door") or "Decor(Door" in c or c.startswith("Stairs"):
                        for dx, dy in ((0, 0), (0, 1), (0, 2), (0, -1), (1, 0), (-1, 0)):
                            self.blocked.add((mx * XT + x - 1 + dx, my * YT + y - 1 + dy))

    @staticmethod
    def mxy(name):
        x, y, _ = name.split(",")
        return int(x), int(y)

    def at(self, gx, gy):
        mx, my = gx // XT, gy // YT
        m = self.maps.get("%d,%d,0" % (mx, my))
        if m is None:
            return None, 0, 0
        return m, gx - mx * XT + 1, gy - my * YT + 1

    def inside(self, gx, gy):
        return self.at(gx, gy)[0] is not None

    def cell(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m.rows[y - 1][x - 1] if m is not None else ""

    def tile(self, gx, gy):
        return self.cell(gx, gy).split("+")[0]

    def decor(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m.decor(x, y) if m is not None else ""

    def set(self, gx, gy, tile=None, decor=None):
        m, x, y = self.at(gx, gy)
        if m is not None:
            m.set(x, y, tile=tile, decor=decor)

    def free(self, gx, gy):
        """Open ground, nothing on it a building would have to knock down."""
        if (gx, gy) in self.taken or (gx, gy) in self.blocked:
            return False
        c = self.cell(gx, gy)
        if not c or "Roof(" in c or "Infront(" in c or "Under(" in c:
            return False
        t = c.split("+")[0]
        if not t.startswith(OPEN):
            return False
        d = self.decor(gx, gy)
        return not d or d.startswith(SMALL)

    def road(self, gx, gy):
        return (gx, gy) not in self.taken and self.tile(gx, gy) in ROADS and "Roof(" not in self.cell(gx, gy) \
            and not self.decor(gx, gy)

    def save(self):
        for m in self.maps.values():
            m.save()


# ================================================================== what goes where
class Lot:
    def __init__(self, kind, x1, y1, x2, y2, door, name=""):
        self.kind, self.x1, self.y1, self.x2, self.y2, self.door, self.name = kind, x1, y1, x2, y2, door, name
        self.pid = ""


SIZES = {   # kind: (width, height) - a building's walls, its front (the door's) its bottom row; 5 high fits any row
    "house": (4, 5), "tavern": (7, 5), "inn": (6, 5), "hotel": (10, 6), "bank": (6, 5), "shop": (5, 5),
    "hall": (8, 5), "parliament": (10, 6), "police": (6, 5), "sheriff": (6, 5), "jail": (6, 5), "hospital": (8, 5),
    "medical": (6, 5), "doctor": (5, 5), "barracks": (8, 5), "armoury": (6, 5), "palace": (13, 6),
}
HOSTILE_GONE = ("Wolf", "Bear", "Giant_Spider", "Bandit", "Goblin", "Hobgoblin", "Skeleton", "Snow_Wolf", "Scorpion",
                "Ember_Hound", "Ashen_Cultist", "Bog_Troll", "Rat", "Bat")


class Town:
    """One settlement being grown: its ground, its kind of road, the lots placed, the people and the scripts."""

    def __init__(self, key, title, ground, centre, style, city=False, seed=1):
        self.key, self.title, self.g, self.centre = key, title, ground, centre
        self.style, self.city = style, city
        self.rng = random.Random(seed)
        self.lots = []
        self.scripts = {}
        self.npcs = []                     # (map name, line)
        self.statics = []
        self.ids = []                      # (map name, pid, x, y)
        self.streets = 0
        self.missed = []
        self.pave = "Paving001" if city else "Dirt001"
        self.n = 0

    # ---------------------------------------------------------------- placing
    def uid(self, what):
        self.n += 1
        return "%s_%s_%d" % (self.key, what, self.n)

    def lot_ok(self, x1, y1, x2, y2, door):
        g = self.g
        m1, _, _ = g.at(x1, y1)
        m2, _, _ = g.at(x2, y2 + 1)
        if m1 is None or m1 is not m2:
            return False
        mx, my = x1 // XT, y1 // YT
        if not (mx * XT + 1 <= x1 and x2 <= mx * XT + XT - 2 and my * YT + 1 <= y1 and y2 + 1 <= my * YT + YT - 1):
            return False                         # (not on a map's edge: the walk across stays open)
        for y in range(y1 - 1, y2 + 2):
            for x in range(x1 - 1, x2 + 2):
                if (x, y) in g.taken:
                    return False
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if not g.free(x, y):
                    return False
        front = (door, y2 + 1)
        return g.free(*front) or g.road(*front)

    def walkable(self, c):
        """Roughly, can you walk here: open ground, a road, nothing big on it, no roof (water and walls can't)."""
        g = self.g
        if not g.inside(*c) or c in g.taken:
            return False
        cell = g.cell(*c)
        if "Roof(" in cell or "Water" in cell.split("+")[0]:       # (a shore's diagonal: no way across)
            return False
        return all(walk_middle(n) for n in (cell.split("+")[0], g.decor(*c)) if n)

    def reached(self):
        """Every cell you can walk to from the town's middle (a road only joins the town if it's one of them)."""
        if getattr(self, "_reach", None) is None:
            start = min((c for c in ((self.centre[0] + dx, self.centre[1] + dy) for dx in range(-6, 7)
                                     for dy in range(-6, 7)) if self.walkable(c)),
                        key=lambda c: abs(c[0] - self.centre[0]) + abs(c[1] - self.centre[1]), default=None)
            seen = set()
            q = deque([start] if start else [])
            seen.update(q)
            while q:
                x, y = q.popleft()
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n not in seen and self.walkable(n):
                        seen.add(n)
                        q.append(n)
            self._reach = seen
        return self._reach

    def road_distance(self):
        """{cell: steps to the nearest road} over open ground (a lot whose street is a road needs no new path)."""
        g = self.g
        reach = self.reached()
        dist = {}
        q = deque()
        for name in g.maps:
            mx, my = g.mxy(name)
            for y in range(my * YT, my * YT + YT):
                for x in range(mx * XT, mx * XT + XT):
                    if g.road(x, y) and (x, y) in reach:
                        dist[(x, y)] = 0
                        q.append((x, y))
        while q:
            x, y = q.popleft()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in dist and g.inside(*n) and n not in g.taken and g.free(*n):
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        return dist

    def candidates(self, w, h, near):
        """Every lot of w x h with its door in the middle of its front: ones on a road, nearest `near`, first."""
        dist = self.road_distance()
        out = []
        for name, m in self.g.maps.items():
            mx, my = self.g.mxy(name)
            for y2 in range(my * YT + h, my * YT + YT - 1):
                for x1 in range(mx * XT + 1, mx * XT + XT - w):
                    y1, x2 = y2 - h + 1, x1 + w - 1
                    door = x1 + w // 2
                    front = dist.get((door, y2 + 1))
                    if front is None:
                        continue
                    d = abs(x1 + w / 2.0 - near[0]) + abs(y2 - near[1]) + 8 * front
                    out.append((d, x1, y1, x2, y2, door))
        out.sort()
        return out

    def place(self, kind, near=None, size=None):
        """A lot for kind (narrower, down to 5 wide, if it won't fit as it is)."""
        w0, h = size or SIZES[kind]
        near = near or self.centre
        for w in range(w0, min(w0, 5) - 1, -1):
            for _, x1, y1, x2, y2, door in self.candidates(w, h, near):
                if self.lot_ok(x1, y1, x2, y2, door) and self.join((door, y2 + 1), dry=True):
                    lot = Lot(kind, x1, y1, x2, y2, door)
                    self.take(lot)
                    self.join((door, y2 + 1))
                    return lot
        self.missed.append(kind)
        return None

    def place_row(self, kind, count, near=None):
        """count buildings side by side on one street (a gap of one between), or as many as fit, at least 2."""
        w, h = SIZES[kind]
        near = near or self.centre
        for n in range(count, 1, -1):
            total = n * w + (n - 1)
            for _, x1, y1, x2, y2, door in self.candidates(total, h, near):
                spots = [(x1 + i * (w + 1), x1 + i * (w + 1) + w - 1) for i in range(n)]
                if not all(self.lot_ok(a, y1, b, y2, a + w // 2) for a, b in spots):
                    continue
                street = [(x, y2 + 1) for x in range(x1, x1 + total)]
                if not all(self.g.free(*c) or self.g.road(*c) for c in street):
                    continue
                if not self.join(street[0], dry=True, extra=street):
                    continue
                lots = []
                for a, b in spots:
                    lot = Lot(kind, a, y1, b, y2, a + w // 2)
                    self.take(lot)
                    lots.append(lot)
                for c in street:
                    self.lay(c)
                self.join(street[0], extra=street)
                return lots
        lot = self.place(kind, near)
        return [lot] if lot else []

    def take(self, lot):
        for y in range(lot.y1, lot.y2 + 1):
            for x in range(lot.x1, lot.x2 + 1):
                self.g.taken.add((x, y))
        self.lots.append(lot)
        self.clear_wildlife(lot)
        self._reach = None                          # (a building can cut a way off: what's reached, again)

    def clear_wildlife(self, lot):
        """Creatures and things left lying where a building now stands go (they'd be inside its walls)."""
        for name, m in self.g.maps.items():
            mx, my = self.g.mxy(name)
            keep = []
            for ln in m.ents:
                f = ln.split("\t")
                if len(f) > 3 and "Id=" not in ln and (f[0] == "MapItem" or f[0] == "NPC" and (
                        f[1] in WILD or f[1] in HOSTILE_GONE)):      # (creatures and things: never a person)
                    try:
                        gx = mx * XT + int(float(f[2])) // TW
                        gy = my * YT + (int(float(f[3])) + 24) // TW
                    except ValueError:
                        keep.append(ln)
                        continue
                    if lot.x1 - 1 <= gx <= lot.x2 + 1 and lot.y1 - 1 <= gy <= lot.y2 + 1:
                        if f[1] in ("Cat", "Black_Cat", "Ginger_Cat", "Dog"):     # (the town's pets: out on the street)
                            f[2], f[3] = str((lot.door - mx * XT) * TW), str((lot.y2 + 1 - my * YT) * TW - 8)
                            f[4:] = [" ".join(o for o in " ".join(f[4:]).split() if not o.startswith("Zone="))]
                            keep.append("\t".join(f))
                        continue
                keep.append(ln)
            m.ents = keep

    def lay(self, c):
        g = self.g
        if g.free(*c) and not g.road(*c):
            g.set(c[0], c[1], tile=self.pave, decor="")
        if getattr(self, "_reach", None) is not None and any(n in self._reach for n in (
                (c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1), c)):
            self._reach.add(c)                       # (a road laid on from the town's: part of the town)

    def join(self, start, dry=False, extra=()):
        """A path from start to the nearest road (or street being laid), over open ground; False if there's none."""
        g = self.g
        extra = set(extra)
        seen = {start: None}
        q = deque([start])
        end = None
        while q:
            c = q.popleft()
            if c != start and c not in extra and g.road(*c) and c in self.reached():
                end = c
                break
            if len(seen) > 4000:
                break
            x, y = c
            for n in ((x, y + 1), (x + 1, y), (x - 1, y), (x, y - 1)):
                if n not in seen and g.inside(*n) and n not in g.taken and (g.free(*n) or g.road(*n)):
                    seen[n] = c
                    q.append(n)
        if end is None:
            return False
        if not dry:
            c = end
            while c is not None:
                self.lay(c)
                c = seen[c]
        return True

    # ---------------------------------------------------------------- squares, parks, avenues
    def square(self, w=9, h=7, near=None, stalls=4, kind="market", name="Market_Square", goods=0):
        """A paved square (a market's stalls and their traders, or a garden's), joined to the roads."""
        near = near or self.centre
        for _, x1, y1, x2, y2, _ in self.candidates(w, h, near):
            if not all(self.g.free(x, y) or self.g.road(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)):
                continue
            if any((x, y) in self.g.taken for y in range(y1 - 1, y2 + 2) for x in range(x1 - 1, x2 + 2)):
                continue
            if not self.join((x1 + w // 2, y2 + 1), dry=True):
                continue
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if kind == "market":
                        self.g.set(x, y, tile="Paving001", decor="")     # (shops may face onto it)
                    else:
                        self.g.set(x, y, tile="Grass001", decor="")
                        self.g.taken.add((x, y))
            cx, cy = x1 + w // 2, y1 + h // 2
            if kind == "market":
                self.g.set(cx, cy, decor="Fountain001")
                spots = [(x1 + 1, y1 + 1), (x2 - 1, y1 + 1), (x1 + 1, y2 - 1), (x2 - 1, y2 - 1), (cx, y1 + 1),
                         (cx, y2 - 1)][:stalls]
                for i, (sx, sy) in enumerate(spots):
                    self.stall(sx, sy, i + goods)
                for x, y in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                    self.g.set(x, y, decor="Lamp_Post001")
            else:
                for y in range(y1, y2 + 1):                       # a garden: paths, flower beds, trees, benches
                    for x in range(x1, x2 + 1):
                        if x == cx or y == cy:
                            self.g.set(x, y, tile="Dirt001")
                        elif (x + y) % 3 == 0:
                            self.g.set(x, y, decor=self.rng.choice(("Flower_Bed001", "Flower_Bed002", "Flower_Bed003")))
                        elif (x * 7 + y) % 5 == 0:
                            self.g.set(x, y, decor=self.rng.choice(("Tree001", "Oak_Tree001", "Bush001")))
                self.g.set(cx, cy, tile="Paving001", decor=self.rng.choice(("Statue001", "Fountain001")))
                for x, y in ((cx - 1, cy - 1), (cx + 1, cy + 1)):
                    if self.g.inside(x, y):
                        self.g.set(x, y, decor="Bench001")
            self.join((x1 + w // 2, y2 + 1))
            for x in range(x1, x2 + 1):
                self.lay((x, y2 + 1))
            pid = "%s_%s" % (self.key, name if kind == "market" else "Gardens_%d" % self.n)
            self.n += 1
            m, lx, ly = self.g.at(cx, y2 + 1)
            self.ids.append((m.name, pid, lx, ly))
            return (x1, y1, x2, y2)
        self.missed.append(kind + " square")
        return None

    STALL_GOODS = [("Greengrocer", "SHOP-Market_Greengrocer", "Fresh from the farms!"),
                   ("Fishmonger", "SHOP-Market_Fishmonger", "Caught this morning!"),
                   ("Butcher", "SHOP-Market_Butcher", "Finest cuts in town!"),
                   ("Baker", "SHOP-Baker", "Still warm from the oven!"),
                   ("Tailor", "SHOP-Market_Weaver", "Cloth and wool, the best!"),
                   ("Cobbler", "SHOP-Cobbler", "Boots that last!")]

    def stall(self, gx, gy, i):
        who, rack, cry = self.STALL_GOODS[i % len(self.STALL_GOODS)]
        m, x, y = self.g.at(gx, gy)
        self.statics.append((m.name, K.obj_line("StaticObject", "Market_Stall_Open", x, y)))
        pid = self.uid("Stall")
        self.person(m.name, who, x, y - 1, pid, "Stand=1 Face=S")                  # (behind the stall)
        self.shop_script(pid, who, cry, rack)

    def tame(self, names):
        """The beasts that roamed what is a street now go (one with an Id stays: a quest's own)."""
        for n in names:
            m = self.g.maps[n]
            m.ents = [ln for ln in m.ents if not (ln.split("\t")[0] == "NPC" and ln.split("\t")[1] in HOSTILE_GONE
                                                  and "Id=" not in ln)]

    def avenues(self, names):
        """New land gets streets first: east-west along its rows 7, 14 and 21 (three rows of buildings face them, four
        houses to a row), joined at the ends of the land by north-south streets, and to the roads there already."""
        grid = []
        for n in names:
            mx, my = self.g.mxy(n)
            for y in range(YT):
                row = [x for x in range(XT) if self.g.free(mx * XT + x, my * YT + y) or self.g.road(mx * XT + x, my * YT + y)]
                if not row:
                    continue
                if y in (6, 13, 20):
                    grid += [(mx * XT + x, my * YT + y) for x in row]
                grid += [(mx * XT + min(row), my * YT + y), (mx * XT + max(row), my * YT + y)]
        for c in grid:
            self.lay(c)
        cells = set(grid)
        touching = any(self.g.road(x + dx, y + dy) and (x + dx, y + dy) not in cells
                       for x, y in grid for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if grid and not touching:                        # (joined to the roads there already, if it isn't)
            start = min(grid, key=lambda c: abs(c[0] - self.centre[0]) + abs(c[1] - self.centre[1]))
            self.join(start, extra=grid)

    # ---------------------------------------------------------------- people and scripts
    def person(self, map_name, sprite, x, y, pid, opts="", name=""):
        name = NAMED.get(pid, name)
        line = "NPC\t%s\t%d\t%d\tAttitude=Good %s Id=%s" % (sprite, (x - 1) * TW, (y - 1) * TW - 8, opts, pid)
        if name:
            line += " Name=%s" % name.replace(" ", "_")
        self.npcs.append((map_name, " ".join(line.split(" "))))

    def shop_script(self, pid, sprite, hello, rack, kind="GENERAL"):
        self.scripts["Talk to " + pid] = [
            say(sprite, hello, ("Let me see your goods.", "@shop"), ("Goodbye.", "@end")),
            ("@shop",), ("Display.Item.Rack", kind, sprite, rack, "@end"),
            ("@end",), ("End",),
        ]

    def notice(self, gx, gy, title, text):
        m, x, y = self.g.at(gx, gy)
        if m is None:
            return
        self.lay((gx, gy))                          # (a notice stands on the street: nothing growing there)
        pid = self.uid("Notice")
        self.statics.append((m.name, "StaticObject\tNotice\t%d\t%d\tId=%s" % ((x - 1) * TW, (y - 1) * TW + 2, pid)))
        self.scripts["Read " + pid] = [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            say("Notice", "%s\\%s" % (title.upper(), text), ("Okay", "@end")),
            ("@end",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You can't read that from here!", "Denied"), ("End",),
        ]

    def write(self):
        g = self.g
        for map_name, line in self.npcs + self.statics:
            g.maps[map_name].ents.append(line)
        for map_name, pid, x, y in self.ids:
            K.place_id(g.maps[map_name], pid, x, y)
        for name, rows in self.scripts.items():
            K.write_script(name, rows, MAKER)


# ================================================================== the buildings and their insides
NAMES = {
    "tavern": ["The Gull and Anchor", "The Prancing Pony", "The Golden Goose", "The Rusty Lantern", "The Old Oak",
               "The Drowned Rat", "The Silver Stag", "The Crooked Kettle", "The Merry Miller", "The Red Lion",
               "The Three Barrels", "The Laughing Fox", "The Wayfarer's Rest", "The Sleeping Giant",
               "The King's Head", "The Blue Boar", "The Jolly Ferryman", "The Hearth and Hound", "The White Hart",
               "The Painted Mermaid", "The Owl and Ivy", "The Bell and Candle", "The Green Man", "The Black Swan",
               "The Wheatsheaf", "The Anchor", "The Fiddler's Elbow", "The Plough", "The Rose and Crown",
               "The Weary Traveller", "The Salty Dog", "The Grey Mare", "The Copper Kettle", "The Half Moon",
               "The Lamb and Flag", "The Shepherd's Crook", "The Star", "The Mermaid's Purse", "The Boar's Tusk",
               "The Hop Pole", "The Old Mill", "The Lantern", "The Harp", "The Drover's Rest", "The Brass Monkey",
               "The Two Ravens", "The Smoking Chimney", "The Crown and Anchor"],
    "street": ["Mill Lane", "Church Street", "Rose Row", "Tanners' Way", "Cooper's Row", "Willow Walk", "Bell Street",
               "Lark Lane", "Orchard Row", "Weavers' Way", "Candle Street", "Fountain Row", "Harbour Street",
               "Chapel Lane", "Kingsway", "Queen's Row", "Linden Lane", "Market Row", "Hill Street", "Well Lane",
               "Copper Street", "Ivy Row", "Swan Lane", "Pear Tree Row", "Barley Street", "Lantern Lane",
               "Thistle Row", "Heron Street", "Fox Lane", "Garden Row", "Sparrow Street", "Hollow Lane",
               "North Street", "South Row", "East Lane", "West Row", "Abbey Street", "Mason's Row", "Smith's Lane",
               "Bakers' Row", "Glass Street", "Rope Walk", "Saddlers' Row", "Wren Lane", "Elm Street", "Ash Row"],
    "person": ["Agnes", "Albert", "Alice", "Amos", "Bertha", "Cedric", "Clara", "Colin", "Dora", "Edgar", "Edith",
               "Elsie", "Ernest", "Florence", "Fred", "Gilbert", "Greta", "Harold", "Hattie", "Hugh", "Ida", "Ivor",
               "Jane", "Jasper", "Kit", "Lettie", "Lionel", "Mabel", "Martha", "Ned", "Nell", "Oswald", "Peggy",
               "Percy", "Polly", "Quentin", "Rosie", "Rufus", "Sid", "Sybil", "Tilly", "Toby", "Ulric", "Vera",
               "Walter", "Winnie"],
}
USED_TAVERNS = set()                # (every tavern in the world its own name)
LANES = {   # the market's lanes: kind of shop -> (who keeps it, its rack, what they say, the lane's name)
    "bakery": ("Baker", "SHOP-Bakery", "Fresh bread and pastries, still warm!", "Baker's Lane"),
    "butcher": ("Butcher", "SHOP-Butchery", "Prime cuts, and pies to die for!", "Butchers' Row"),
    "fish": ("Fishmonger", "SHOP-Fishmongery", "Fresh off the boats this morning!", "Fish Street"),
    "greens": ("Greengrocer", "SHOP-Greengrocery", "Cabbages, carrots and potatoes, all fresh!", "Green Lane"),
    "clothes": ("Tailor", "SHOP-Tailor", "The finest cloth in the land, made to measure.", "Silk Street"),
    "shoes": ("Cobbler", "SHOP-Cobbler", "Boots and shoes, stitched to last.", "Cordwainers' Row"),
    "armour": ("Armourer", "SHOP-Armour", "Plate, mail and shields. Try something on!", "Armourers' Row"),
    "weapons": ("Armourer", "SHOP-Weapons", "Swords, daggers and bows, sharp and true.", "Blade Street"),
}


def walls(town, lot):
    """The building, its walls and roof in the town's style."""
    m, x1, y1 = town.g.at(lot.x1, lot.y1)
    _, x2, y2 = town.g.at(lot.x2, lot.y2)
    door = lot.door - (lot.x1 - x1)
    wall = town.rng.choice(town.style["walls"])
    if lot.kind in ("hall", "parliament", "bank", "hospital", "palace", "hotel") and "grand" in town.style:
        wall = town.style["grand"]
    roof = town.rng.choice(V.ROOFS[wall])[0] if wall in V.ROOFS else "Slate"
    chimney = x1 + 1 + town.rng.randrange(max(1, x2 - x1 - 1)) if lot.kind in ("house", "tavern", "inn", "shop") else None
    grand = lot.kind in ("palace", "parliament", "hotel") and "grand" in town.style
    if lot.kind == "palace":
        roof = "Slate"
    K.building(m, x1, y1, x2, y2, door, wall=wall, roof=roof, chimney=chimney,
               floor="Marble001" if grand else "Plank001")
    return m, x1, y1, x2, y2, door, wall


def furnish(town, lot):
    """The building's walls, what's inside it, its people, its sign and its scripts."""
    m, x1, y1, x2, y2, door, wall = walls(town, lot)
    rng = town.rng
    k = lot.kind
    put = lambda x, y, d: m.set(x, y, decor=d)
    inside = [(x, y) for y in range(y1 + 1, y2) for x in range(x1 + 1, x2)]
    back = [(x, y1) for x in range(x1 + 1, x2)]                  # the back wall's row: beds, shelves, stations
    name = lot.name
    pid = town.uid(k.capitalize())
    lot.pid = pid
    sign_at = (lot.door + 1, lot.y2 + 1)                        # (beside the door, on the street)
    if k == "house":
        bx = x1 + 1 if rng.random() < 0.5 else x2 - 1
        other = x2 - 1 if bx == x1 + 1 else x1 + 1
        put(bx, y1, "Bed001")
        put(bx, y1 + 1, "Bed002")
        put(other, y1, "Bookshelf001")
        put(other, y1 + 2, "Table001")
        if rng.random() < 0.6:
            folk = rng.choice(("Villager", "Man", "Woman", "Farmer"))
            who = rng.choice(NAMES["person"])
            town.person(m.name, folk, (x1 + x2) // 2, y2 - 1, town.uid("Resident"), "Zone=%d,%d,%d,%d Pause=5-15" % (
                x1 + 1, y1 + 1, x2 - 1, y2 - 1), who)
            town.scripts["Talk to " + town.npcs[-1][1].split("Id=")[1].split()[0]] = [
                say(folk, rng.choice(HOME_LINES).replace("TOWN", town.title), ("Goodbye.", "@end")),
                ("@end",), ("End",)]
    elif k in ("tavern", "inn"):
        for x in range(x1 + 1, x2 - 1):
            put(x, y1 + 2, "Counter001")                           # the bar
        put(x1 + 1, y1, "Barrel001")
        put(x1 + 2, y1, "Barrel002")
        m.set(x2 - 1, y1, tile="Fireplace001")           # (the hearth, in the back wall)
        for tx in range(x1 + 2, x2 - 1, 3):
            if y2 - 2 > y1 + 3:
                put(tx, y2 - 2, "Table001")
                put(tx - 1, y2 - 2, "Chair003")
                put(tx + 1, y2 - 2, "Chair004")
        bar = town.uid("Barkeep")
        town.person(m.name, "Barkeep", (x1 + x2) // 2, y1 + 1, bar, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        town.person(m.name, "Barmaid", x2 - 2, y2 - 1, town.uid("Barmaid"), "Zone=%d,%d,%d,%d Pause=3-9" % (
            x1 + 1, y1 + 3, x2 - 1, y2 - 1), rng.choice(NAMES["person"]))
        town.scripts["Talk to " + town.npcs[-1][1].split("Id=")[1].split()[0]] = [
            say("Barmaid", "Sit anywhere you like, love. The barkeep will see to you.", ("Thanks.", "@end")),
            ("@end",), ("End",)]
        town.scripts["Talk to " + bar] = tavern_script(name, "Barkeep", 5 if town.city else 3)
        town.statics.append((m.name, K.obj_line("StaticObject", "Sign_Pub", *town_xy(town, sign_at), dy=-16)))
        town.notice(lot.door - 2, lot.y2 + 1, name, "A tavern of %s." % town.title)
    elif k == "hotel":
        for x in range(x1 + 2, x1 + 5):
            put(x, y1 + 3, "Desk001" if x == x1 + 3 else "Counter001")
        for x in range(x1 + 1, x2, 2):
            if (x, y1) in back:
                put(x, y1, "Double_Bed001")
                put(x + 1, y1, "Double_Bed002")
                put(x, y1 + 1, "Double_Bed003")
                put(x + 1, y1 + 1, "Double_Bed004")
        for x, y in ((x2 - 1, y2 - 1), (x1 + 1, y2 - 1)):
            put(x, y, "Potted_Plant%03d" % rng.randint(1, 5))
        host = town.uid("Hotelier")
        town.person(m.name, "Hotelier", x1 + 3, y1 + 2, host, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        town.scripts["Talk to " + host] = room_script(name, "Hotelier", 25, posh=True)
        town.notice(lot.door + 2, lot.y2 + 1, name, "A grand hotel.")
    elif k == "bank":
        for x in range(x1 + 1, x2 - 1):
            put(x, y1 + 2, "Bank_Counter001")               # (a gap at its end: the clerks' way round)
        put(x1 + 1, y1, "Bookshelf001")
        put(x2 - 1, y1, "Bookshelf001")
        m.set(door - 1 if door - 1 > x1 else door + 1, y2, decor="Bank_Plaque001")
        b = town.uid("Banker")
        town.person(m.name, "Banker", (x1 + x2) // 2, y1 + 1, b, "Stand=1 Face=S")
        town.scripts["Talk to " + b] = [
            say("Banker", "Welcome to the bank of %s. Your valuables are safe with us." % town.title,
                ("I'd like to use the bank.", "@bank"), ("Goodbye.", "@end")),
            ("@bank",), ("Display.Item.Rack", "BANK", "Banker", "-", "@end"),
            ("@end",), ("End",)]
    elif k == "shop":
        who, rack, hello, _lane = LANES[lot.name]
        for x, y in back:
            put(x, y, "Shelf_Goods001")
        for x in range(x1 + 1, x2 - 1):
            put(x, y1 + 2, "Counter001")
        s = town.uid(who)
        town.person(m.name, who, (x1 + x2) // 2, y1 + 1, s, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        town.shop_script(s, who, hello, rack)
    elif k in ("hall", "parliament"):
        for y in range(y1 + 3, y2 - 1):
            for x in range(x1 + 1, x2):
                if x != (x1 + x2) // 2:
                    put(x, y, "Bench001")
        put((x1 + x2) // 2, y1 + 2, "Desk001")
        for x, y in back:
            if (x - x1) % 3 == 1:
                put(x, y, "Banner001" if k == "parliament" else "Bookshelf001")
        for x in (x1 + 1, x2 - 1):
            put(x, y1 + 1, "Potted_Plant%03d" % rng.randint(1, 5))
        who = "Speaker" if k == "parliament" else "Clerk"
        c = town.uid(who)
        town.person(m.name, who, (x1 + x2) // 2, y1 + 1, c, "Stand=1 Face=S")
        lot.speaker = c
        town.scripts["Talk to " + c] = [
            say(who, HALL_LINES[lot.name].replace("TOWN", town.title), ("Goodbye.", "@end")),
            ("@end",), ("End",)]
        town.notice(lot.door + 2, lot.y2 + 1, lot.name.replace("TOWN", town.title), HALL_SIGNS[lot.name])
    elif k in ("police", "sheriff", "jail"):
        cells = x2 - 3
        for y in range(y1, y2):
            m.set(cells, y, decor="Iron_Fence002" if y != y1 + 2 else "")
        for x in range(cells + 1, x2):
            put(x, y1, "Bed001")
            put(x, y1 + 1, "Bed002")
        put(x1 + 2, y1 + 1, "Desk001")
        who = "Constable" if k == "police" else "Sheriff"
        c = town.uid(who)
        town.person(m.name, who, x1 + 2, y1 + 2, c, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        town.scripts["Talk to " + c] = [
            say(who, LAW_LINES[k].replace("TOWN", town.title), ("Goodbye.", "@end")),
            ("@end",), ("End",)]
        title = {"police": "Police Station", "sheriff": "Sheriff's Office and Jail", "jail": "Sheriff's Office"}[k]
        town.notice(lot.door + 2, lot.y2 + 1, title, "The watch house of %s." % town.title)
    elif k in ("hospital", "medical", "doctor"):
        for x, y in back:
            if (x - x1) % 2 == 1:
                put(x, y, "Bed001")
                put(x, y + 1, "Bed002")
        put(x2 - 1, y2 - 1, "Potted_Plant002")
        d = town.uid("Doctor")
        town.person(m.name, "Doctor", (x1 + x2) // 2, y2 - 2, d, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        cost = {"hospital": 10, "medical": 8, "doctor": 6}[k]
        town.scripts["Talk to " + d] = doctor_script(cost)
        if k == "hospital":
            town.person(m.name, "Nurse", x1 + 2, y2 - 1, town.uid("Nurse"), "Zone=%d,%d,%d,%d Pause=4-10" % (
                x1 + 1, y1 + 2, x2 - 1, y2 - 1), rng.choice(NAMES["person"]))
            town.scripts["Talk to " + town.npcs[-1][1].split("Id=")[1].split()[0]] = [
                say("Nurse", "The doctor will see you. Mind the beds.", ("Thank you.", "@end")), ("@end",), ("End",)]
        title = {"hospital": "Hospital", "medical": "Medical Office", "doctor": "Doctor's House"}[k]
        town.notice(lot.door + 2, lot.y2 + 1, title, "Of %s." % town.title)
    elif k == "barracks":
        for x, y in back:
            put(x, y, "Bed001")
            put(x, y + 1, "Bed002")
        for x in range(x1 + 1, x2, 3):
            if abs(x - door) > 1:                                   # (the doorway kept clear)
                put(x, y2 - 1, "Shelf_Goods001")
        for i in range(2):
            town.person(m.name, "Royal_Guard" if town.city else "Guard", x1 + 2 + i * 3, y2 - 2, town.uid("Soldier"),
                        "Zone=%d,%d,%d,%d Pause=4-12" % (x1 + 1, y1 + 2, x2 - 1, y2 - 1))
        town.notice(lot.door + 2, lot.y2 + 1, "Barracks", "The city guard's quarters.")
    elif k == "palace":
        mid = (x1 + x2) // 2
        m.set(mid, y1 + 1, tile="Throne001")                         # the throne, on its dais, before the back wall
        for x in range(mid - 1, mid + 2):
            if x != mid:
                put(x, y1 + 1, "Banner001")
        for y in range(y1 + 2, y2):                                 # the royal carpet, door to throne
            m.set(mid, y, tile="Carpet001" if y > y1 + 2 else "Carpet002")
        for x in (x1 + 2, x2 - 2, mid - 3, mid + 3):
            for y in range(y1 + 2, y2 - 1, 2):
                if x1 < x < x2:
                    put(x, y, "Pillar001")
        for x, y in back:
            if (x - x1) % 4 == 2 and abs(x - mid) > 2:
                put(x, y, "Banner001")
        for x in (x1 + 1, x2 - 1):
            put(x, y2 - 1, "Potted_Plant%03d" % rng.randint(1, 5))
        mx, my = town.g.mxy(m.name)
        for x in (x1, x2, mid - 4, mid + 4):                         # its spires, high over the city
            town.statics.append((m.name, "StaticObject\tPalace_Spire\t%d\t%d" % ((x - 1) * TW, (y1 - 3) * TW)))
        lot.throne = (m.name, mid, y1 + 1)
    elif k == "armoury":
        for x, y in back:
            put(x, y, "Shelf_Goods001")
        for x in range(x1 + 1, x2 - 1):
            put(x, y1 + 2, "Counter001")
        a = town.uid("Armourer")
        town.person(m.name, "Armourer", (x1 + x2) // 2, y1 + 1, a, "Stand=1 Face=S", rng.choice(NAMES["person"]))
        town.shop_script(a, "Armourer", "The city's armoury: arms and armour for its guard, and for you.",
                         "SHOP-Armour")
        town.notice(lot.door + 2, lot.y2 + 1, "The Armoury", "Arms and armour of the city guard.")
    return pid


def town_xy(town, c):
    m, x, y = town.g.at(*c)
    return x, y


HOME_LINES = [
    "Morning! Lovely day in TOWN, isn't it?",
    "Mind the step. My husband keeps meaning to fix it.",
    "You're not from round here, are you? TOWN's a friendly place, mostly.",
    "Have you tried the bakery? Best bread in TOWN.",
    "The tavern's lively tonight, I hear. Not that I'd know.",
    "Can't stop: the stew's on.",
    "My grandmother lived in this very house. Her grandmother too.",
]
HALL_LINES = {
    "City Hall": "Welcome to TOWN's City Hall. The council meets here: rates, roads and rubbish, mostly.",
    "Town Hall": "This is TOWN's Town Hall. Births, weddings and deeds are written here.",
    "Village Hall": "The village hall. Dances on a Saturday, meetings on a Monday.",
    "Parliament": "This is the Parliament of Ashen.",
}
HALL_SIGNS = {
    "City Hall": "The seat of the city's council.",
    "Town Hall": "Births, marriages and deeds recorded.",
    "Village Hall": "Meetings, dances and harvest suppers.",
    "Parliament": "The Parliament of Ashen.",
}
LAW_LINES = {
    "police": "TOWN's watch keeps the peace. Keep your sword in its scabbard and we'll get along.",
    "sheriff": "I'm the sheriff here. The cells are empty and I like them that way.",
    "jail": "I'm the sheriff here. Trouble goes in the cells; you don't look like trouble.",
}


def tavern_script(name, who, room):
    return [
        say(who, "Welcome to %s! What'll it be?" % name, ("Something to eat and drink.", "@shop"),
            ("A room for the night (%d gold)." % room, "@room"), ("Goodbye.", "@end")),
        ("@shop",), ("Display.Item.Rack", "GENERAL", who, "SHOP-Pub", "@end"),
        ("End",),
        ("@room",), (">Got.Item", "Gold_Coin(s)", str(room), "@poor"),
        ("Take.Item", "Gold_Coin(s)", str(room)),
        ("Display.Message", "Cyan", "You take a room upstairs and sleep the night through.", "-"),
        ("Sleep", "Morning"),
        ("End",),
        ("@poor",), ("Display.Refusal", "You need %d gold coins for a room." % room),
        ("@end",), ("End",),
    ]


def room_script(name, who, price, posh=False):
    return [
        say(who, "Welcome to %s. A room for the night is %d gold." % (name, price),
            ("I'll take a room.", "@room"), ("Goodbye.", "@end")),
        ("@room",), (">Got.Item", "Gold_Coin(s)", str(price), "@poor"),
        ("Take.Item", "Gold_Coin(s)", str(price)),
        ("Display.Message", "Cyan", "Feather pillows, silk sheets: you sleep like a king." if posh else
         "You sleep the night through.", "-"),
        ("Sleep", "Morning"),
        ("End",),
        ("@poor",), ("Display.Refusal", "You need %d gold coins for a room." % price),
        ("@end",), ("End",),
    ]


NAMED = {   # (people given their own name, not one drawn from NAMES: Id -> name)
    "Northport_Doctor_349": "Doctor Foster",                  # (Northport's doctor)
}


def doctor_script(cost):
    return [
        say("Doctor", "Hurt? Let me see. I'll patch you up for %d gold." % cost, ("Heal me (%d gold)." % cost, "@heal"),
            ("Goodbye.", "@end")),
        ("@heal",), (">Conditional", "$Player.Health<$Player.Health.Max", "@well"),
        (">Got.Item", "Gold_Coin(s)", str(cost), "@poor"),
        ("Take.Item", "Gold_Coin(s)", str(cost)),
        ("Play.Sound", "SpellHeal"),
        ("Update.Skill", "Hitpoints", "+500"),
        ("Display.Message", "Yellow", "The doctor cleans and binds your wounds. You feel much better.", "-"),
        ("End",),
        ("@poor",), ("Display.Refusal", "You need %d gold coins." % cost),
        ("End",),
        ("@well",), say("Doctor", "Heal you? I've looked you over: not a scratch on you. You're as fit as a fiddle. "
                                  "Keep your gold, and come back when something's actually bleeding.", ("Thank you.", "@end")),
        ("@end",), ("End",),
    ]


# ================================================================== carts and horses between a city's quarters
def cart_stops(town, targets):
    """A cart stop near each target (label, world cell): a cart and its horse on free ground beside a road, the carter
    on the road; each carter drives you to any of the other stops for 2 coins."""
    g = town.g
    stops = []
    for label, (tx, ty) in targets:
        best = None
        for y in range(ty - 14, ty + 15):
            for x in range(tx - 16, tx + 17):
                ok = lambda c: g.free(*c) or g.road(*c) and g.road(c[0], c[1] - 1)    # (on a wide road, too)
                if not (ok((x, y)) and ok((x + 1, y)) and g.road(x, y + 1) and g.road(x + 1, y + 1)):
                    continue
                m1, _, _ = g.at(x, y)
                m2, _, _ = g.at(x + 1, y + 1)
                if m1 is None or m1 is not m2 or (x, y + 1) not in town.reached():
                    continue
                d = abs(x - tx) + abs(y - ty)
                if best is None or d < best[0]:
                    best = (d, x, y)
        if best is None:
            town.missed.append("cart stop " + label)
            continue
        _, x, y = best
        g.taken.update({(x, y), (x + 1, y)})
        m, lx, ly = g.at(x, y)
        town.statics.append((m.name, K.obj_line("StaticObject", "Cart", lx, ly)))
        town.npcs.append((m.name, "NPC\tHorse\t%d\t%d\tAttitude=Good Stand=1 Face=E Id=%s_Horse_%d" % (
            lx * TW - 6, (ly - 1) * TW - 2, town.key, len(stops) + 1)))   # (east of its cart, in its shafts; 40x34)
        pid = "%s_Cart_Stop_%d" % (town.key, len(stops) + 1)
        carter = "%s_Carter_%d" % (town.key, len(stops) + 1)
        town.npcs.append((m.name, "NPC\tCarter\t%d\t%d\tAttitude=Good Stand=1 Face=S Id=%s Name=%s" % (
            (lx - 1) * TW, ly * TW - 8, carter, town.rng.choice(NAMES["person"]))))
        town.ids.append((m.name, pid, lx + 1, ly + 1))
        stops.append((label, pid, carter))
    for label, pid, carter in stops:
        rows = [say("Carter", "A ride across %s? Two coins, anywhere the carts go." % town.title,
                    *([("To %s." % other, "@to%d" % i) for i, (other, opid, _) in enumerate(stops) if opid != pid][:3]
                      + [("Not today.", "@end")]))]
        for i, (other, opid, _) in enumerate(stops):
            if opid == pid:
                continue
            rows += [("@to%d" % i,), (">Got.Item", "Gold_Coin(s)", "2", "@poor"),
                     ("Take.Item", "Gold_Coin(s)", "2"),
                     ("Display.Message", "Cyan", "The cart rattles off through the streets of %s.." % town.title, "-"),
                     ("Play.Sound", "Boat"), ("Toggle.User.Input", "OFF"), ("Wait", "2"), ("Toggle.User.Input", "ON"),
                     ("Teleport", opid, "-"),
                     ("Display.Message", "Cyan", "..and pulls up %s." % other, "-"), ("End",)]
        rows += [("@poor",), ("Display.Refusal", "You need 2 gold coins for the cart."), ("@end",), ("End",)]
        town.scripts["Talk to " + carter] = rows
    return stops


# ================================================================== a settlement, all of it
def grow(town, plan, carts=None):
    """plan: what the settlement gets, in order: ("square",), ("lanes", [kinds], per lane), ("building", kind, name),
    ("streets", n), ("park", n). Each is placed nearest the centre that's still free; then any building a later one
    has cut off from the town is joined to it again (or goes), and only then furnished."""
    rng = town.rng
    sq = None
    signs = []                                   # (the lots of a street or lane, its notice's place and words)
    for item in plan:
        what = item[0]
        if what == "square":
            w, h, stalls = (item[1:4] + (9, 7, 4)[len(item[1:4]):]) if len(item) > 1 else (9, 7, 4)
            if len(item) > 4:                        # (a second square, a posh one: fine clothes and shoes)
                sq = town.square(w, h, stalls=stalls, name=item[4].capitalize() + "_Square", goods=4)
            else:
                sq = town.square(w, h, stalls=stalls)
        elif what == "lanes":
            kinds, per = item[1], item[2]
            near = ((sq[0] + sq[2]) // 2, sq[3] + 1) if sq else town.centre
            by = [lt for lt in town.lots if len(item) > 3 and lt.kind == item[3]]
            if by:                                       # (a lane by a building: arms and armour by the armoury)
                near = (by[0].door, by[0].y2 + 1)
            for kind in kinds:
                lots = town.place_row("shop", per, near)
                for i, lot in enumerate(lots):
                    lot.name = kind.split("+")[i % len(kind.split("+"))]
                if lots:
                    a = lots[0]
                    signs.append((lots, (a.x1 - 1 if town.g.inside(a.x1 - 1, a.y2 + 1) else a.x1, a.y2 + 1),
                                  " & ".join(LANES[k][3] for k in kind.split("+")), "A lane off the market square."))
        elif what == "building":
            kind, name = item[1], item[2]
            lot = town.place(kind, size=(6, 5) if name == "Village Hall" else None)
            if lot:
                lot.name = name
        elif what == "streets":
            names = list(NAMES["street"])
            rng.shuffle(names)
            for i in range(item[1]):
                per = item[2] if len(item) > 2 else 3
                lots = town.place_row("house", per)
                if not lots:
                    break
                a = lots[0]
                signs.append((lots, (a.x1, a.y2 + 1), names[i], "Houses of %s." % town.title))
        elif what == "park":
            for _ in range(item[1]):
                town.square(7, 5, kind="garden")
    town._reach = None                           # (a later building may have cut an earlier one's way off)
    for lot in list(town.lots):
        front = (lot.door, lot.y2 + 1)
        if front not in town.reached() and not town.join(front):
            town.lots.remove(lot)
            for y in range(lot.y1, lot.y2 + 1):
                for x in range(lot.x1, lot.x2 + 1):
                    town.g.taken.discard((x, y))
            town.missed.append(lot.kind + " (cut off)")
    for lots, (x, y), title, words in signs:
        if any(lot in town.lots for lot in lots):
            if lots[0].kind == "house":
                town.streets += 1
            town.notice(x, y, title, words)
    if carts:                                    # (carts and horses between its quarters)
        cart_stops(town, carts(town))
    for lot in list(town.lots):
        if lot.kind in ("tavern", "inn") and not lot.name:
            names = [n for n in NAMES["tavern"] if n not in USED_TAVERNS]
            lot.name = rng.choice(names) if names else "The %s Arms" % town.title
            USED_TAVERNS.add(lot.name)
        furnish(town, lot)
    town.write()
    return town
