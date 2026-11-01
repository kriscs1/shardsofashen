"""The overworld (or any level) as one grid of world cells, for passes over the finished maps: what's natural and
what's made, rewilding what was made, lifting what's made from one place and setting it down in another, maps
moved whole (every level), and new maps (the sea, for land to be grown on).

A world cell: gx = map x * 25 + tile x - 1, gy = map y * 21 + tile y - 1. Map lines (things, Ids, locks, triggers)
are kept per map as they are, and found by the world cell they stand on (a thing's feet)."""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, XT, YT, TW                  # noqa: E402
from atlas import fbm, h01                              # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
MAPS = os.path.join(ROOT, "maps")
SCRIPTS = os.path.join(ROOT, "data", "Scripts")
ENT_KINDS = ("NPC", "StaticObject", "MapItem")
SEA = "Water001"

NATURAL = re.compile(r"^(Grass|Sand|Snow|Marsh|Ash|Cinder|Scorched|Moss|Heath|Forest|Ice|Lava|Water|Sand_Water|"
                     r"Marsh_Water|Snow_Water|Peak|Peak_Big|Peak_Huge|Snow_Peak|Snow_Peak_Big|Snow_Peak_Huge|"
                     r"Cinder_Peak|Cinder_Peak_Big|Cinder_Peak_Huge|Sea_Rock)\d{3}$")
WATERY = re.compile(r"^(Water|Sand_Water|Marsh_Water|Snow_Water)\d{3}$")
PEAKY = re.compile(r"^(Snow_|Cinder_)?Peak(_Big|_Huge)?\d{3}$")
WILD_DECOR = re.compile(r"^(Tall_Grass|Tree|Pine|Palm|Oak_Tree|Willow_Tree|Yew_Tree|Birch|Bush|Berry_Bush|Shrub|Rock|"
                        r"Boulder|Pebbles|Flowers|Grass|Fern|Reeds|Mushroom_Patch|Weed|Cactus|Dead_Tree|Stump|"
                        r"Snow_Pine|Snow_Rock|Desert_Rock|Basalt_Rock|Ember_Vent|Fallen_Log|Heather|Thistle|Clover|"
                        r"Lily_Pads|Bog_Myrtle|Marigold_Patch|Sage_Patch|Nightshade_Patch|Emberroot_Patch|Sea_Rock|"
                        r"Dragon_Skull|\w+_Rock)\d{3}$")
ROADS = ("Dirt001", "Gravel001", "Plank001")


def mname(mx, my, mz=0):
    return "%d,%d,%d" % (mx, my, mz)


def mxyz(name):
    p = name.split(",")
    return int(p[0]), int(p[1]), int(p[2])


def maps_on(z):
    out = []
    for f in os.listdir(MAPS):
        m = re.fullmatch(r"(-?\d+),(-?\d+),(-?\d+)\.txt", f)
        if m and int(m.group(3)) == z:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def all_levels():
    out = []
    for f in os.listdir(MAPS):
        m = re.fullmatch(r"(-?\d+),(-?\d+),(-?\d+)\.txt", f)
        if m:
            out.append(tuple(int(v) for v in m.groups()))
    return out


def parts(text):
    bits = text.split("+")
    over = {}
    for b in bits[1:]:
        kind, _, arg = b.partition("(")
        over[kind] = arg.rstrip(")")
    return bits[0], over


def join(tile, over):
    s = tile
    for kind in ("Under", "Decor", "Roof", "Infront", "Trigger"):
        if over.get(kind):
            s += "+%s(%s)" % (kind, over[kind])
    return s


def natural(text):
    """Wild ground: a natural tile, nothing built on it (a tree or a rock may stand there)."""
    t, over = parts(text)
    if not NATURAL.match(t) or over.get("Roof") or over.get("Under") or over.get("Infront") or over.get("Trigger"):
        return False
    d = over.get("Decor", "")
    return not d or bool(WILD_DECOR.match(d))


def watery(text):
    return bool(WATERY.match(parts(text)[0]))


def line_cell(ln, mx, my):
    """The world cell a map line stands on (a thing's feet), or None."""
    p = ln.split("\t")
    try:
        if p[0] in ENT_KINDS and len(p) >= 4:
            return mx * XT + int((float(p[2]) + 16) // TW), my * YT + int((float(p[3]) + 28) // TW)
        if p[0] in ("Id", "Trigger") and len(p) >= 4:
            return mx * XT + int(p[2]) - 1, my * YT + int(p[3]) - 1
        if p[0] == "Lock" and len(p) >= 3:
            return mx * XT + int(p[1]) - 1, my * YT + int(p[2]) - 1
    except ValueError:
        return None
    return None


def line_id(ln):
    """A map line's own name: an Id line's, a thing's Id= (else its Name=), else ''."""
    p = ln.split("\t")
    if p[0] in ("Id", "Trigger"):
        return p[1]
    if p[0] in ENT_KINDS and len(p) > 4:
        m = re.search(r"\bId=(\S+)", p[4])
        return m.group(1) if m else ""
    return ""


def shift_opts(opts, dx, dy):
    """A thing's Zone/Chase/Nap/Patrol/Home/Roost tiles and Bed= moved dx, dy tiles (on its own map's tiles)."""
    def pts(v):
        nums = [int(n) for n in re.findall(r"-?\d+", v)]
        out = [str(n + (dx if k % 2 == 0 else dy)) for k, n in enumerate(nums)]
        seps = re.findall(r"[,;/]", v)
        return "".join(o + (seps[k] if k < len(seps) else "") for k, o in enumerate(out))
    return re.sub(r"\b(Zone|Chase|Nap|Patrol|Roost|Home|Bed)=([-\d,;/]+)",
                  lambda m: m.group(1) + "=" + pts(m.group(2)), opts)


class World:
    """Every map of a level (z), cell by cell; new maps made as asked (filled with fill)."""

    def __init__(self, z=0):
        self.z = z
        self.maps = {}
        for mx, my in maps_on(z):
            self.maps[(mx, my)] = Map(mname(mx, my, z))
        self.changed = set()

    # ---- cells
    def at(self, gx, gy):
        mx, my = gx // XT, gy // YT
        return self.maps.get((mx, my)), gx - mx * XT + 1, gy - my * YT + 1

    def has(self, gx, gy):
        return (gx // XT, gy // YT) in self.maps

    def cell(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m.rows[y - 1][x - 1] if m is not None else None

    def tile(self, gx, gy):
        c = self.cell(gx, gy)
        return parts(c)[0] if c is not None else None

    def put(self, gx, gy, text):
        m, x, y = self.at(gx, gy)
        if m is not None and m.rows[y - 1][x - 1] != text:
            m.rows[y - 1][x - 1] = text
            self.changed.add(m.name)

    def set(self, gx, gy, tile=None, decor=None):
        c = self.cell(gx, gy)
        if c is None:
            return
        t, over = parts(c)
        if tile is not None:
            t = tile
        if decor is not None:
            over["Decor"] = decor
        self.put(gx, gy, join(t, over))

    def new_map(self, mx, my, fill=SEA):
        if (mx, my) not in self.maps:
            m = Map(mname(mx, my, self.z), new=True)
            m.rows = [[fill] * XT for _ in range(YT)]
            self.maps[(mx, my)] = m
            self.changed.add(m.name)
        return self.maps[(mx, my)]

    def touch(self, m):
        self.changed.add(m.name)

    # ---- map lines
    def lines(self, box=None):
        """[(map, line, world cell)] of every map line (within box: gx1, gy1, gx2, gy2)."""
        out = []
        for (mx, my), m in self.maps.items():
            if box is not None and not (box[0] // XT - 1 <= mx <= box[2] // XT + 1 and
                                        box[1] // YT - 1 <= my <= box[3] // YT + 1):
                continue
            for ln in m.ents:
                c = line_cell(ln, mx, my)
                if c is None:
                    continue
                if box is None or (box[0] <= c[0] <= box[2] and box[1] <= c[1] <= box[3]):
                    out.append((m, ln, c))
        return out

    def drop(self, m, ln):
        if ln in m.ents:
            m.ents.remove(ln)
            self.changed.add(m.name)

    def add_line(self, ln, from_map, dx, dy):
        """A map line from map from_map (mx, my) moved dx, dy cells, onto the map it lands on (local tiles, zones)."""
        p = ln.split("\t")
        omx, omy = from_map
        if p[0] in ENT_KINDS:
            px = omx * XT * TW + float(p[2]) + dx * TW
            py = omy * YT * TW + float(p[3]) + dy * TW
            mx, my = int((px + 16) // (XT * TW)), int((py + 28) // (YT * TW))
            if (mx, my) not in self.maps:
                return None
            p[2], p[3] = "%d" % (px - mx * XT * TW), "%d" % (py - my * YT * TW)
            if len(p) > 4:
                p[4] = shift_opts(p[4], (omx - mx) * XT + dx, (omy - my) * YT + dy)
        else:
            i = 1 if p[0] == "Lock" else 2
            gx, gy = omx * XT + int(p[i]) - 1 + dx, omy * YT + int(p[i + 1]) - 1 + dy
            mx, my = gx // XT, gy // YT
            if (mx, my) not in self.maps:
                return None
            p[i], p[i + 1] = str(gx - mx * XT + 1), str(gy - my * YT + 1)
        m = self.maps[(mx, my)]
        m.ents.append("\t".join(p))
        self.changed.add(m.name)
        return m

    def place(self, gx, gy, kind, name, extra="", dy=0):
        m, x, y = self.at(gx, gy)
        ln = "%s\t%s\t%d\t%d" % (kind, name, (x - 1) * TW, (y - 1) * TW + dy) + ("\t" + extra if extra else "")
        m.ents.append(ln)
        self.changed.add(m.name)
        return m

    def place_id(self, gx, gy, pid):
        m, x, y = self.at(gx, gy)
        m.ents = [ln for ln in m.ents if ln.split("\t")[:2] != ["Id", pid]]
        m.ents.append("Id\t%s\t%d\t%d" % (pid, x, y))
        self.changed.add(m.name)

    def find_id(self, pid):
        """(map, world cell) of a place Id or a thing's Id=."""
        for (mx, my), m in self.maps.items():
            for ln in m.ents:
                if line_id(ln) == pid:
                    return m, line_cell(ln, mx, my)
        return None, None

    def zone(self, gx1, gy1, gx2, gy2, gx, gy):
        """A Zone= box in the local tiles of the map of world cell gx, gy."""
        mx, my = gx // XT, gy // YT
        return "%d,%d,%d,%d" % (gx1 - mx * XT + 1, gy1 - my * YT + 1, gx2 - mx * XT + 1, gy2 - my * YT + 1)

    def save(self):
        for (mx, my), m in self.maps.items():
            if m.name in self.changed:
                m.save()
        n = len(self.changed)
        self.changed = set()
        return n

    # ---- the wild
    def rewild(self, cells, seed="rewild"):
        """Every cell of cells made wild again: the ground most of the wild round it has (water where the water's
        most), and now and then what grows there (a donor cell's decor, so as thick as round about)."""
        cells = set(cells)
        for c in sorted(cells, key=lambda c: (c[1], c[0])):
            near = []
            for r in (3, 6, 10, 16, 26):
                near = [n for n in ((c[0] + dx, c[1] + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1))
                        if n not in cells and self.cell(*n) is not None and natural(self.cell(*n))]
                if len(near) >= 8:
                    break
            if not near:
                self.put(c[0], c[1], "Grass001")
                continue
            close = [n for n in near if abs(n[0] - c[0]) <= 1 and abs(n[1] - c[1]) <= 1]
            if close and sum(1 for n in close if watery(self.cell(*n))) * 2 > len(close):
                self.put(c[0], c[1], SEA)
                continue
            counts = {}
            for n in near:
                t = parts(self.cell(*n))[0]
                if WATERY.match(t) or PEAKY.match(t) or t.startswith("Sea_Rock"):
                    continue
                counts[t] = counts.get(t, 0) + 1
            ground = max(counts, key=counts.get) if counts else "Grass001"
            donors = [n for n in near if parts(self.cell(*n))[0] == ground] or near
            d = donors[int(h01(seed, *c) * len(donors)) % len(donors)]
            decor = parts(self.cell(*d))[1].get("Decor", "")
            self.put(c[0], c[1], ground + ("+Decor(%s)" % decor if decor else ""))

    def smooth_shores(self, cells):
        """The diagonal shore pieces round cells (and plain water/land put back where a piece no longer fits)."""
        import land as LAND
        near = {(c[0] + dx, c[1] + dy) for c in cells for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)}
        grid = {}
        for c in near:
            t = self.tile(*c)
            if t is None:
                continue
            if WATERY.match(t) and t != SEA:
                t = SEA                                     # (an old shore piece: worked out again)
            grid[c] = t
        sea = [c for c in grid if grid[c] == SEA]
        LAND.smooth_shores(grid, sea)
        for c, t in grid.items():
            old = self.tile(*c)
            if old != t and (WATERY.match(old) or old == SEA):
                o = parts(self.cell(*c))[1]
                if t != SEA:
                    o.pop("Decor", None)
                self.put(c[0], c[1], join(t, o))


STREETS = ("Marble_Paving001", "Cobble001", "Brick_Paving001", "Mage_Flag001", "Slate_Flag001", "Red_Sandstone001",
           "Flagstone001", "Gravel001", "Basalt_Paving001", "Sandstone_Paving001", "Boardwalk001", "Paving001",
           "Plank001", "Dirt001")


def is_road(text):
    t, over = parts(text)
    return t in STREETS and not over.get("Roof")


def road_cost(w, c):
    """What a road through c costs (None: it can't): the wild cheapest where it's open, a road already there
    cheaper still, a pond or a river bridged (dearly), never the sea's open water, a peak or anything built."""
    text = w.cell(*c)
    if text is None:
        return None
    if is_road(text):
        return 0.3
    t, over = parts(text)
    if WATERY.match(t):
        return 7.0
    if not natural(text) or PEAKY.match(t):
        return None
    base = {"Forest001": 3.0, "Marsh001": 1.6, "Sand001": 1.3, "Snow001": 1.4}.get(t, 1.0)
    d = over.get("Decor", "")
    if d and not d.startswith(("Flowers", "Pebbles", "Tall_Grass", "Reeds", "Lily_Pads", "Marigold", "Clover")):
        base += 2.5
    return base * (0.5 + fbm(c[0], c[1], 9, 91))             # (roads wander)


def find_way(w, starts, goals, avoid=frozenset(), most=40000):
    """A* from any of starts to any of goals over road_cost (cells in avoid can't be crossed)."""
    import heapq
    goals = set(goals)
    gl = list(goals)
    gx, gy = sum(c[0] for c in gl) / len(gl), sum(c[1] for c in gl) / len(gl)
    best, came, q = {}, {}, []
    for s in starts:
        best[s], came[s] = 0.0, None
        heapq.heappush(q, (0.0, 0.0, s))
    n = 0
    while q and n < most * 10:
        n += 1
        _, g, c = heapq.heappop(q)
        if g > best.get(c, 1e18):
            continue
        if c in goals:
            path = []
            while c is not None:
                path.append(c)
                c = came[c]
            return path[::-1]
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (c[0] + d[0], c[1] + d[1])
            if nb in avoid and nb not in goals:
                continue
            k = 0.0 if nb in goals else road_cost(w, nb)
            if k is None:
                continue
            ng = g + k
            if ng < best.get(nb, 1e18):
                best[nb], came[nb] = ng, c
                heapq.heappush(q, (ng + 0.3 * (abs(nb[0] - gx) + abs(nb[1] - gy)), ng, nb))
    return None


def lay_way(w, path, wide=True):
    """A road along path: dirt (a boardwalk over marsh, planks over water), two abreast where it can be."""
    def put(c):
        text = w.cell(*c)
        if text is None or is_road(text):
            return
        t, over = parts(text)
        if not natural(text) or PEAKY.match(t):
            return
        tile = "Plank001" if WATERY.match(t) else "Boardwalk001" if t.startswith("Marsh") else "Dirt001"
        w.put(c[0], c[1], tile)
    for i, c in enumerate(path):
        put(c)
        if wide and 0 < i < len(path) - 1:
            p, nx = path[i - 1], path[i + 1]
            side = (c[0], c[1] + 1) if p[1] == nx[1] else (c[0] + 1, c[1])
            if road_cost(w, side) is not None:
                put(side)


def join_roads(w, ends, network=(), avoid=frozenset()):
    """Each of ends (road cells left hanging) joined to the rest: the first to network (cells already on the roads,
    e.g. a town's streets), or, with none, the ends to each other, nearest first. Returns how many were joined."""
    joined = set(network)
    ends = list(ends)
    if not joined and ends:
        joined.add(ends.pop(0))
    n = 0
    while ends:
        ends.sort(key=lambda e: min(abs(e[0] - j[0]) + abs(e[1] - j[1]) for j in joined))
        e = ends.pop(0)
        path = find_way(w, [e], joined, avoid)
        if path is None:
            print("  !! no way from %s to the roads" % (e,))
            continue
        lay_way(w, path)
        joined |= set(path)
        n += 1
    return n


def road_ends(w, box, gone):
    """The roads that ran into box and stop at its edge now (gone: the cells made wild): one cell of each."""
    x1, y1, x2, y2 = box
    ring = [(x, y) for x in range(x1 - 3, x2 + 4) for y in range(y1 - 3, y2 + 4)
            if not (x1 <= x <= x2 and y1 <= y <= y2)]
    stubs = [c for c in ring if w.cell(*c) is not None and is_road(w.cell(*c)) and
             any((c[0] + dx, c[1] + dy) in gone for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    out, seen = [], set()
    for s in stubs:                                       # (a road two wide: one end of it)
        if s in seen:
            continue
        group, todo = set(), [s]
        while todo:
            c = todo.pop()
            if c in group:
                continue
            group.add(c)
            todo += [n for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if n in stubs]
        seen |= group
        out.append(min(group))
    return out


def rename_level_map(old, new):
    """maps\\old.txt -> new.txt, and the map's entry script with it."""
    a, b = os.path.join(MAPS, old + ".txt"), os.path.join(MAPS, new + ".txt")
    assert not os.path.exists(b), "%s is there already" % new
    shutil.move(a, b)
    sa, sb = os.path.join(SCRIPTS, old + ".txt"), os.path.join(SCRIPTS, new + ".txt")
    if os.path.exists(sa):
        shutil.move(sa, sb)


def read(path):
    return open(path, "rb").read().decode("cp1252")


def write(path, text):
    open(path, "wb").write(text.encode("cp1252"))


def replace_in_files(paths, pairs):
    """Each (old, new) of pairs replaced in each file (cp1252, as it is). Returns the files changed."""
    done = []
    for p in paths:
        s = read(p)
        t = s
        for a, b in pairs:
            t = t.replace(a, b)
        if t != s:
            write(p, t)
            done.append(p)
    return done


def scripts():
    return [os.path.join(SCRIPTS, f) for f in os.listdir(SCRIPTS) if f.endswith(".txt")]
