"""The roads (layout.ROADS): each found by A* over the world tiles from one place's streets (or its way in) to the
other's, the easy ground cheapest (a road already there cheapest of all, so roads share their way), rivers crossed on
plank bridges, mountains, the sea, buildings and the lifted places gone round. Main roads two tiles wide, footpaths
one. Then ports and docks: a city on a coast gets a port (a wide pier, its boats), anything smaller a jetty."""
import heapq

from atlas import XT, YT, TW, h01, fbm
import land as LAND
import layout as L

GW, GH = L.W * XT, L.H * YT
COST = {"Grass001": 1.0, "Dirt001": 0.6, "Sand001": 1.3, "Snow001": 1.4, "Marsh001": 1.8, "Ash001": 1.2,
        "Cinder001": 1.3, "Forest001": 3.0, "Scorched001": 1.2, "Scorched002": 1.2, "Scorched003": 1.2, "Ice001": 2.5}
STREETS = ("Marble_Paving001", "Cobble001", "Brick_Paving001", "Mage_Flag001", "Slate_Flag001", "Red_Sandstone001",
           "Flagstone001", "Gravel001", "Basalt_Paving001", "Sandstone_Paving001", "Boardwalk001", "Paving001",
           "Plank001")
SMALL = ("Flowers", "Pebbles", "Tall_Grass", "Bush", "Berry_Bush", "Fern", "Mushroom", "Sage", "Marigold", "Reeds",
         "Nightshade", "Emberroot", "Bog_Myrtle", "Fallen_Log", "Lily_Pads")


class Ways:
    def __init__(self, atlas, plans):
        self.atlas = atlas
        self.plans = plans
        self.road = {}                         # cell -> "road" or "path"

    # ---------------------------------------------------------------- the ground's cost
    def cost(self, c):
        """The cost of a road through c (None: can't)."""
        a = self.atlas
        if c in a.roads:
            return 0.25
        if c in a.taken:
            return None
        g = LAND.GROUND.get(c)
        if g is None:
            return None
        if c in LAND.RIVER:
            return 6.0                                 # (a bridge: worth going round for, not far)
        if g in STREETS:
            return 0.3
        base = COST.get(g)
        if base is None:
            return None                                # (the sea, peaks, lava, walls)
        d = LAND.DECOR.get(c, "")
        if d and not d.startswith(SMALL):
            base += 2.5                                # (a tree or a rock, cleared)
        return base * (0.5 + 1.2 * fbm(c[0], c[1], 7, 91))      # (so a road wanders, as country roads do)

    def anchors(self, name):
        """The cells a road may start or end at for a place: a settlement's streets, else the place's way in."""
        if name in self.plans:
            p = self.plans[name]
            return {c for c in p.street if LAND.GROUND.get(c) != "Plank001"} or {p.centre}
        (mx, my), (tx, ty), _ = L.POIS[name]
        return {(mx * XT + tx - 1, my * YT + ty - 1)}

    def find(self, starts, goals):
        goal_list = list(goals)
        gx = sum(c[0] for c in goal_list) / len(goal_list)
        gy = sum(c[1] for c in goal_list) / len(goal_list)
        h = lambda c: 0.25 * (abs(c[0] - gx) + abs(c[1] - gy))      # noqa: E731
        best = {}
        came = {}
        q = []
        for s in starts:
            best[s] = 0.0
            came[s] = None
            heapq.heappush(q, (h(s), 0.0, s))
        while q:
            f, g, c = heapq.heappop(q)
            if g > best.get(c, 1e18):
                continue
            if c in goals:
                path = []
                while c is not None:
                    path.append(c)
                    c = came[c]
                return path[::-1]
            x, y = c
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= n[0] < GW and 0 <= n[1] < GH):
                    continue
                k = 0.0 if n in goals else self.cost(n)
                if k is None:
                    continue
                if c in LAND.RIVER and n in LAND.RIVER and (n[0] - x, n[1] - y) != getattr(self, "_dir", None):
                    k += 0.5                           # (a bridge goes straight across)
                ng = g + k
                if ng < best.get(n, 1e18):
                    best[n] = ng
                    came[n] = c
                    heapq.heappush(q, (ng + h(n), ng, n))
        return None

    # ---------------------------------------------------------------- laying them
    def lay(self, path, kind):
        a = self.atlas
        for i, c in enumerate(path):
            if c in a.taken and c not in a.roads:
                continue
            if c in a.roads and LAND.GROUND.get(c) in STREETS and LAND.GROUND.get(c) != "Plank001":
                continue                               # (a town's street: it stays its own stuff)
            self.put(c, "Plank001" if c in LAND.RIVER else "Dirt001")
            self.road[c] = kind
            if kind == "road" and 0 < i < len(path) - 1:                 # (a main road: two abreast)
                p, n = path[i - 1], path[i + 1]
                side = (c[0], c[1] + 1) if p[1] == n[1] else (c[0] + 1, c[1])
                if self.cost(side) is not None and side not in a.taken and LAND.GROUND.get(side) not in STREETS:
                    self.put(side, "Plank001" if side in LAND.RIVER else "Dirt001")
                    self.road[side] = kind

    def put(self, c, tile):
        self.atlas.set(c[0], c[1], tile=tile, decor="")
        LAND.GROUND[c], LAND.DECOR[c] = tile, ""
        self.atlas.roads.add(c)

    def build(self):
        missed = []
        for i, (a, b) in enumerate(L.ROADS):
            kind = "path" if (b in L.POIS and L.POIS[b][2] == "path") else "road"
            path = self.find(self.anchors(a), self.anchors(b))
            if path is None:
                missed.append("%s - %s" % (a, b))
                continue
            self.lay(path, kind)
        return missed

    # ---------------------------------------------------------------- signposts
    def signposts(self, scripts):
        """A signpost where roads meet out in the country: which way each place lies (no more)."""
        a = self.atlas
        made = 0
        for c, kind in sorted(self.road.items()):
            if kind != "road" or c in a.taken:
                continue
            x, y = c
            arms = [n for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if self.road.get(n) == "road"]
            if len(arms) < 3 or any(p.box_has(c, 30) for p in self.plans.values()):
                continue
            spot = next((s for s in ((x + 2, y + 2), (x - 2, y - 2), (x + 2, y - 2), (x - 2, y + 2))
                         if LAND.GROUND.get(s) in ("Grass001", "Sand001", "Snow001", "Ash001", "Marsh001")
                         and s not in a.taken and s not in a.roads), None)
            if spot is None or any(abs(spot[0] - o[0]) + abs(spot[1] - o[1]) < 40 for o in getattr(self, "posts", [])):
                continue
            self.posts = getattr(self, "posts", []) + [spot]
            made += 1
            m, lx, ly = a.at(*spot)
            pid = "Signpost_%d_%d" % spot
            m.ents.append("StaticObject\tSignpost\t%d\t%d\tId=%s" % ((lx - 1) * TW, (ly - 1) * TW, pid))
            a.taken.add(spot)
            ways = []
            for k, p in sorted(self.plans.items()):
                dx, dy = p.centre[0] - spot[0], p.centre[1] - spot[1]
                d = abs(dx) + abs(dy)
                if d < 260:
                    ways.append((d, p.title, compass(dx, dy)))
            ways.sort()
            text = "\\".join("%s: %s" % (t, w) for _, t, w in ways[:4])
            scripts["Read " + pid] = [
                (">Distance.From.Clicked.Entity", "64", "@far"),
                ("Display.Conversation", "Signpost", text, "Okay", "@end"),
                ("@end",), ("End",),
                ("@far",), ("Display.Message", "DarkRed", "You can't read that from here!", "Denied"), ("End",)]
        return made


def compass(dx, dy):
    ns = "north" if dy < -abs(dx) * 0.4 else "south" if dy > abs(dx) * 0.4 else ""
    ew = "west" if dx < -abs(dy) * 0.4 else "east" if dx > abs(dy) * 0.4 else ""
    return (ns + ("-" if ns and ew else "") + ew) or "here"


# ------------------------------------------------------------------ ports and docks
def harbour(atlas, plan, big):
    """A pier out from the settlement's shore nearest its middle, joined to its streets: a city's port (three planks
    wide, six long, boats moored along it, crates and barrels, a harbour master) or a jetty (one wide, four long, a
    fishing spot off its end). Returns the pier's foot (or None)."""
    side = plan.spec.get("coast")
    if not side:
        return None
    best = None
    cx, cy = plan.centre
    wet = lambda r: LAND.GROUND.get(r, "").startswith("Water") and r not in LAND.RIVER and r not in atlas.taken  # noqa
    d = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}.get(side)
    across = (1, 0) if d and d[1] else (0, 1)
    for c in plan.cells if d else ():
        if c in atlas.taken:
            continue
        x, y = c
        beach = []
        k = 1
        while k < 9:                                         # (over the beach to the water's edge)
            r = (x + d[0] * k, y + d[1] * k)
            if wet(r) or r in atlas.taken or LAND.GROUND.get(r) is None:
                break
            beach.append(r)
            k += 1
        run = [(x + d[0] * j + across[0] * w, y + d[1] * j + across[1] * w)
               for j in range(k, k + 7) for w in (-1, 0, 1)]
        if all(wet(r) for r in run):
            score = abs(x - cx) + abs(y - cy) + 2 * len(beach)
            if best is None or score < best[0]:
                best = (score, c, d, beach)
    if best is None:
        plan.missing.append("harbour")
        return None
    _, foot, d, beach = best
    for r in beach:                                          # (the way down to it)
        plan.cells.add(r)
        plan.lay(r)
    if beach:
        foot = beach[-1]
    length, width = (6, 3) if big else (4, 1)
    cells = []
    for k in range(1, length + 1):
        for w in range(-(width // 2), width // 2 + 1):
            c = (foot[0] + d[0] * k + across[0] * w, foot[1] + d[1] * k + across[1] * w)
            cells.append(c)
            atlas.set(c[0], c[1], tile="Plank001", decor="")
            m, lx, ly = atlas.at(*c)
            m.rows[ly - 1][lx - 1] = "Plank001"
            LAND.GROUND[c], LAND.DECOR[c] = "Plank001", ""
            atlas.roads.add(c)
            atlas.taken.add(c)
    end = (foot[0] + d[0] * (length + 1), foot[1] + d[1] * (length + 1))
    boats = [(foot[0] + d[0] * (length - 1) + across[0] * (width // 2 + 1),
              foot[1] + d[1] * (length - 1) + across[1] * (width // 2 + 1))]
    if big:
        boats.append((foot[0] + d[0] * (length - 3) - across[0] * (width // 2 + 1),
                      foot[1] + d[1] * (length - 3) - across[1] * (width // 2 + 1)))
    for b in boats if big else ():                          # (a jetty: just the one boat that comes and goes)
        m, lx, ly = atlas.at(*b)
        if m is not None and 1 < lx < XT and 1 < ly < YT - 1:
            m.ents.append("StaticObject\t%s\t%d\t%d" % ("Moored_Boat", (lx - 1) * TW,
                                                       (ly - 1) * TW))
    m, lx, ly = atlas.at(*end)
    if m is not None:
        m.ents.append("StaticObject\tFish_Spot\t%d\t%d" % ((lx - 1) * TW, (ly - 1) * TW))
    if big:
        for k, t in ((2, "Crate001"), (3, "Barrel001"), (5, "Crate002")):
            c = (foot[0] + d[0] * k + across[0] * (width // 2), foot[1] + d[1] * k + across[1] * (width // 2))
            atlas.set(c[0], c[1], decor=t)
        pid = plan.uid("Harbour_Master")
        m, lx, ly = atlas.at(foot[0] + d[0] * 2 - across[0] * (width // 2), foot[1] + d[1] * 2 - across[1] * (width // 2))
        plan.person(m.name, "Fisherman", lx, ly, pid, "Stand=1 Face=S", plan.rng.choice(("Rufus", "Ned", "Agnes",
                                                                                          "Ivor")))
        plan.scripts["Talk to " + pid] = [
            ("Display.Conversation", "Fisherman", "Welcome to the port of %s. Mind the ropes." % plan.title,
             "Goodbye.", "@end"), ("@end",), ("End",)]
    plan.harbour = (foot, cells)
    m, lx, ly = atlas.at(foot[0] + d[0], foot[1] + d[1])
    plan.ids.append((m.name, "%s_%s" % (plan.key, "Port" if big else "Dock"), lx, ly))
    return foot
