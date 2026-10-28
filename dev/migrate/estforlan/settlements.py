"""The settlements (dev\\World Plan.md), each the size it's given, with what that size has:

  * The market square near the middle, paved; avenues straight out of it north and south, its top and foot rows
    running on east and west as streets, then more east-west streets every 8 rows, the buildings along each on its
    north side, facing it (their doors open onto it). Near the middle the streets are straight and paved in the
    place's own stone; further out they wander, give out unevenly and turn to its outer stuff, then dirt. Lanes
    join neighbouring streets near their ends.
  * The big buildings (the halls, the cathedral, the parliament) face the square or its top row; the lanes of shops
    (bread, meat, fish, greens...) are the streets nearest it; the rest of the civic buildings take the plots nearest
    the middle, the houses the rest: every house its own size, walls, roof and furniture, a gap between.
  * Inside each building what its kind needs, and its people (dev\\migrate\\towns.py furnishes the civic ones), a
    notice at each street's end, a shardstone and a homestone by the square.
"""
import random

import story_kit as K
import towns as OLD
import villages as V
from atlas import XT, YT, TW, h01, map_xy
import land as LAND

MAKER = "build_estforlan.py"

# what each size has: its square (w, h), the civic buildings (kind, name, how many), its lanes of shops
# (kinds, shops), its streets of houses, how many houses to a street, gardens, carts
SIZES = {
    "huge": dict(square=(17, 9), paved=48, streets=20, per=8, gardens=4, carts=True, civic=[
        ("parliament", "Parliament", 1), ("cathedral", "Cathedral", 1), ("hall", "City Hall", 1),
        ("hall", "Town Hall", 1), ("hotel", "", 1), ("bank", "", 2), ("police", "", 1), ("hospital", "", 1),
        ("armoury", "", 1), ("barracks", "", 1), ("tavern", "", 10), ("smithy", "", 1)],
        lanes=[("bakery", 3), ("butcher", 3), ("fish", 3), ("greens", 3)],
        posh=dict(square=(11, 5), lanes=[("clothes+shoes", 4)]), arms=[("armour+weapons", 4)]),
    "large": dict(square=(15, 9), paved=36, streets=10, per=7, gardens=3, carts=True, civic=[
        ("parliament", "City Hall", 1), ("cathedral", "Cathedral", 1), ("hall", "Town Hall", 1), ("bank", "", 1),
        ("police", "", 1), ("hospital", "", 1), ("tavern", "", 5), ("smithy", "", 1)],
        lanes=[("bakery", 3), ("butcher", 3), ("fish", 3), ("greens", 3)]),
    "medium": dict(square=(13, 9), paved=30, streets=10, per=6, gardens=1, carts=False, civic=[
        ("hall", "City Hall", 1), ("cathedral", "Cathedral", 1), ("hall", "Town Hall", 1), ("bank", "", 1),
        ("sheriff", "", 1), ("hospital", "", 1), ("tavern", "", 5), ("smithy", "", 1)],
        lanes=[("bakery", 2), ("butcher", 2), ("fish", 2), ("greens", 2)]),
    "small": dict(square=(11, 9), paved=22, streets=5, per=4, gardens=1, carts=False, civic=[
        ("hall", "City Hall", 1), ("church", "Church", 1), ("hall", "Town Hall", 1), ("bank", "", 1),
        ("sheriff", "", 1), ("medical", "", 1), ("tavern", "", 2), ("smithy", "", 1)],
        lanes=[("bakery+fish", 2), ("greens+butcher", 2)]),
    "town": dict(square=(9, 9), paved=16, streets=5, per=4, gardens=0, carts=False, civic=[
        ("hall", "Town Hall", 1), ("church", "Church", 1), ("bank", "", 1), ("jail", "", 1), ("doctor", "", 1),
        ("tavern", "", 1), ("smithy", "", 1)],
        lanes=[("bakery+fish", 2), ("greens+butcher", 2)]),
    "village": dict(square=(7, 7), paved=10, streets=5, per=4, gardens=0, carts=False, civic=[
        ("hall", "Village Hall", 1), ("chapel", "Chapel", 1), ("jail", "", 1), ("doctor", "", 1), ("inn", "", 1),
        ("smithy", "", 1)], lanes=[]),
    "hamlet": dict(square=None, paved=0, streets=2, per=4, gardens=0, carts=False, civic=[
        ("inn", "", 1), ("chapel", "Chapel", 1)], lanes=[]),
}
SIZE = {   # kind: ((width range), (height range)) of its walls; its front (with the door) is its bottom row
    "house": ((4, 7), (4, 6)), "tavern": ((7, 9), (5, 6)), "inn": ((6, 8), (5, 5)), "hotel": ((10, 11), (6, 6)),
    "bank": ((6, 8), (5, 5)), "shop": ((5, 6), (5, 5)), "hall": ((8, 10), (5, 6)), "parliament": ((12, 13), (7, 7)),
    "police": ((6, 7), (5, 5)), "sheriff": ((6, 7), (5, 5)), "jail": ((6, 6), (5, 5)), "hospital": ((9, 10), (5, 6)),
    "medical": ((6, 7), (5, 5)), "doctor": ((5, 6), (5, 5)), "barracks": ((9, 10), (5, 6)), "armoury": ((7, 8), (5, 5)),
    "cathedral": ((11, 13), (9, 9)), "church": ((9, 9), (7, 7)), "chapel": ((7, 7), (6, 6)), "smithy": ((6, 7), (5, 5)),
    "garden": ((7, 9), (5, 5)),
}
SPREAD = 10                        # (how far past its maps a place may grow)
PERIOD = 8                         # (rows of buildings: 5-6 high, a street, a back garden's row)


def snap_north(y):
    """A street row y, moved north if the buildings along it (up to 6 above it) would cross into the map above."""
    return y if y % YT >= 7 else y - y % YT - 1


def snap_south(y):
    """A street row y, moved south past the seam if the buildings along it would cross it."""
    return y if y % YT >= 7 else y - y % YT + 7
NORTH_BLOCK = 11                   # (above the square: room for a cathedral)
GROUND = {"meadow": "Grass001", "wood": "Grass001", "moor": "Grass001", "hills": "Grass001", "marsh": "Marsh001",
          "desert": "Sand001", "snow": "Snow001", "elder": "Grass001", "ash": "Ash001", "downs": "Grass001",
          "galaith": "Grass001"}
CLEARABLE = ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001", "Cinder001", "Dirt001", "Forest001")
STREET_NAMES = OLD.NAMES["street"] + [
    "Lantern Row", "Kingfisher Lane", "Cloth Street", "Stonegate", "Highgate", "Lowgate", "Gull Street",
    "Pennyworth Row", "Mercers' Lane", "Chandler Street", "Tallow Row", "Hay Lane", "Furlong Street", "Oriel Row",
    "Gilt Street", "Ravens Row", "Saltway", "Brewers' Lane", "Cartwright Row", "Vintner Street", "Thatchers' Row"]
USED_STREETS = set()


class Plan(OLD.Town):
    """One settlement: its ground (the atlas), its streets and plots, then everything towns.furnish puts in."""

    def __init__(self, atlas, key, spec, reserved, seed=1):
        style = {"walls": [w for w, n in spec["walls"] for _ in range(n)], "grand": spec["grand"]}
        OLD.Town.__init__(self, key, spec["title"], atlas, None, style,
                          city=spec["size"] in ("huge", "large", "medium", "small"), seed=seed)
        self.title = spec["title"][0].upper() + spec["title"][1:]
        self.atlas = atlas
        self.spec = spec
        self.size = SIZES[spec["size"]]
        x1, y1, x2, y2 = spec["maps"]
        self.box = (x1 * XT, y1 * YT, (x2 + 1) * XT - 1, (y2 + 1) * YT - 1)
        self.reserved = reserved
        self.street = {}                   # cell -> its stuff
        self.cells = set()
        self.ground = GROUND.get(spec["land"], "Grass001")
        self.sq = None
        self.rows = []                     # [(y, side, [cells from the middle out])]
        self.avenues = []                  # [(N or S, [cells from the square out])]
        self.avenue_x = None
        self.missing = []
        self.lane_signs = []
        self.house_groups = {}
        self.wild = {}                     # cell -> (its cell, ground, decor) before it was cleared
        self.shardstone = None
        self.n = 300                       # (its people's Ids: clear of the old towns' numbers, which quests use)

    # ------------------------------------------------------------------ the ground it has
    def usable(self, c):
        return c in self.cells and c not in self.atlas.taken and c not in self.street

    def prepare(self, keep=None):
        """Its maps' open land (and a little beyond, if it needs it), cleared of what grows wild (the sea, rivers,
        mountains and lifted places stay)."""
        import layout as L
        others = [o["maps"] for k, o in L.SETTLEMENTS.items() if k != self.key]
        bx1, by1, bx2, by2 = self.box
        for gy in range(by1 - SPREAD, by2 + SPREAD + 1):
            for gx in range(bx1 - SPREAD, bx2 + SPREAD + 1):
                c = (gx, gy)
                if c in self.reserved or c in self.atlas.taken or c in LAND.RIVER:
                    continue
                if any(x1 * XT - SPREAD <= gx < (x2 + 1) * XT + SPREAD and y1 * YT - SPREAD <= gy < (y2 + 1) * YT + SPREAD
                       for x1, y1, x2, y2 in others):
                    continue
                if keep is not None and not keep(c):
                    continue
                g = LAND.GROUND.get(c)
                pond = g is not None and g.startswith(("Water", "Marsh_Water", "Sand_Water", "Snow_Water", "Ice", "Lava"))                     and c in LAND.BIOME and LAND.near_land(c)
                if g is None or not (g in CLEARABLE or g.startswith("Scorched") or pond):
                    continue
                if g == "Sand001" and self.ground != "Sand001" and self.spec.get("coast"):
                    continue                                # (the beach stays the beach)
                self.cells.add(c)
                self.wild[c] = (self.atlas.cell(gx, gy), g, LAND.DECOR.get(c, ""))    # (what grew there: rewild)
                own = LAND.plain(LAND.BIOME.get(c, "")) if c in LAND.BIOME else self.ground
                own = own if own in ("Grass001", "Sand001", "Snow001", "Marsh001", "Ash001") else self.ground
                self.atlas.set(gx, gy, tile=own, decor="")         # (its own land's ground: no edge where it ends)
                LAND.GROUND[c], LAND.DECOR[c] = own, ""

    def edge_ok(self, gx, gy):
        """Not on a map's outer row or column (the walk across the seam stays open, and a roof is whole)."""
        lx, ly = gx % XT, gy % YT
        return 1 <= lx <= XT - 2 and 1 <= ly <= YT - 2

    # ------------------------------------------------------------------ streets
    def far(self, c):
        """How far out c is: 0 at the middle, 1 at the paved middle's edge."""
        d = abs(c[0] - self.centre[0]) + abs(c[1] - self.centre[1]) * 1.2
        return d / max(6.0, self.size["paved"])

    def material(self, c):
        f = self.far(c) + 0.25 * (h01("mat", self.key, c) - 0.5)
        if f <= 1.0:
            return self.spec["street"]
        if f <= 1.7:
            return self.spec["outer"]
        return "Dirt001"

    def lay(self, c, material=None):
        if c not in self.cells and c not in LAND.RIVER:
            return False
        if c in self.atlas.taken:
            return False
        m = material or self.material(c)
        if c in LAND.RIVER:
            m = "Plank001"                                      # (a bridge)
        self.street[c] = m
        self.atlas.roads.add(c)
        self.atlas.set(c[0], c[1], tile=m, decor="")
        LAND.GROUND[c], LAND.DECOR[c] = m, ""
        return True

    def unlay(self, c):
        if c not in self.street:
            return
        del self.street[c]
        self.atlas.roads.discard(c)
        g = "Water001" if c in LAND.RIVER else self.ground
        self.atlas.set(c[0], c[1], tile=g, decor="")
        LAND.GROUND[c], LAND.DECOR[c] = g, ""

    def bridgeable(self, c, step):
        """A river ahead of c: is there land within 5 tiles across it?"""
        x, y = c
        for i in range(1, 6):
            n = (x + step[0] * i, y + step[1] * i)
            if n in self.cells:
                return True
            if n not in LAND.RIVER:
                return False
        return False

    def run(self, start, step, wobble=True, material=None, stop=999):
        """A street from start, step by step (dx, dy); beyond the paved middle it wanders a tile or two off its line
        and may give out. Returns its cells, in order."""
        x, y = start
        base = (x, y)
        out = []
        for i in range(stop):
            c = (x, y)
            if c in LAND.RIVER and (out and self.bridgeable(out[-1], step) or c in self.street):
                self.lay(c)
                out.append(c)
                x, y = x + step[0], y + step[1]
                continue
            if c not in self.cells or c in self.atlas.taken:
                break
            far = self.far(c)
            if far > 1.1 and h01("end", self.key, base, i) < 0.02 * far:
                break                                           # (it gives out, unevenly, out there)
            self.lay(c, material)
            out.append(c)
            if wobble and far > 1.0 and h01("wob", self.key, base, i) < 0.12 * far:
                d = 1 if h01("wd", self.key, base, i) < 0.5 else -1
                side = (x, y + d) if step[1] == 0 else (x + d, y)
                off = (side[1] - base[1]) if step[1] == 0 else (side[0] - base[0])
                if abs(off) <= 2 and side in self.cells and side not in self.atlas.taken:
                    self.lay(side, material)
                    out.append(side)
                    x, y = side
            x, y = x + step[0], y + step[1]
        return out

    def choose_centre(self, hint=None):
        """The middle of its land (or hint), where a square fits."""
        if hint:
            self.centre = hint
            return
        bx1, by1, bx2, by2 = self.box
        inside = [c for c in self.cells if bx1 <= c[0] <= bx2 and by1 <= c[1] <= by2]
        xs = sorted(c[0] for c in inside)
        ys = sorted(c[1] for c in inside)
        cx, cy = xs[len(xs) // 2], ys[len(ys) // 2]
        self.centre = min(inside, key=lambda c: abs(c[0] - cx) + abs(c[1] - cy) + (0 if self.clear_round(c, 8)
                                                                                         else 60))

    def clear_round(self, c, r):
        return all((c[0] + dx, c[1] + dy) in self.cells and (c[0] + dx, c[1] + dy) not in self.atlas.taken
                   for dx in range(-r, r + 1, 2) for dy in range(-r, r + 1, 2))

    def find_rect(self, w, h, near, reach=14, margin=1, low=False):
        """The free w x h nearest near (low: its top row 10-12 down its map, so the big buildings fit above it)."""
        best = None
        cx, cy = near
        for dy in range(-reach, reach + 1):
            for dx in range(-reach - 4, reach + 5):
                x1, y1 = cx + dx - w // 2, cy + dy - h // 2
                ok = all((x, y) in self.cells and (x, y) not in self.atlas.taken and (x, y) not in self.street
                         for y in range(y1 - margin, y1 + h + margin) for x in range(x1 - margin, x1 + w + margin))
                if ok:
                    d = abs(dx) + abs(dy) + (0 if not low or YT - 1 - h <= y1 % YT <= YT - h else 25)
                    if best is None or d < best[0]:
                        best = (d, x1, y1)
        return None if best is None else (best[1], best[2], best[1] + w - 1, best[2] + h - 1)

    def on_a_street(self, size, near):
        """Room for a square whose foot is a street's row (joined to it), nearest near."""
        w, h = size
        for y, side, cells in sorted(self.rows, key=lambda r: abs(r[0] - near[1])):
            for x in sorted({c[0] for c in cells}, key=lambda v: abs(v - near[0])):
                x1 = x - w // 2
                above = [(cx, cy) for cy in range(y - h, y) for cx in range(x1 - 1, x1 + w + 1)]
                foot = [(cx, y) for cx in range(x1, x1 + w)]
                if all(self.usable(c) for c in above) and all(c in self.street or self.usable(c) for c in foot)                         and self.edge_ok(x1, y - h + 1) and self.edge_ok(x1 + w - 1, y):
                    return (x1, y - h + 1, x1 + w - 1, y)
        return None

    def lay_square(self, size, name="Market_Square", stalls=4, goods=0, near=None, rect=None):
        """A paved square: a fountain in its middle, lamps at its corners, stalls and their traders."""
        w, h = size
        rect = rect or self.find_rect(w, h, near or self.centre, margin=2, low=name == "Market_Square")
        if rect is None:
            self.missing.append(name)
            return None
        x1, y1, x2, y2 = rect
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.lay((x, y), self.spec["street"])
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        self.atlas.set(mx, my, decor="Fountain001")
        self.atlas.taken.add((mx, my))
        spots = [(x1 + 2, y1 + 2), (x2 - 2, y1 + 2), (x1 + 2, y2 - 2), (x2 - 2, y2 - 2), (mx - 3, my),
                 (mx + 3, my)][:stalls]
        for i, (sx, sy) in enumerate(spots):
            self.stall(sx, sy, i + goods)
            self.atlas.taken.add((sx, sy))
        for x, y in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            self.atlas.set(x, y, decor="Lamp_Post001")
            self.atlas.taken.add((x, y))
        if name == "Market_Square":                              # (the market board: everyone's goods, their prices)
            m, x, y = self.atlas.at(mx, y1 + 1)
            self.statics.append((m.name, K.obj_line("StaticObject", "Market_Board", x, y)))
            self.atlas.taken.add((mx, y1 + 1))
        m, lx, ly = self.atlas.at(mx, my + 1)
        self.ids.append((m.name, "%s_%s" % (self.key, name), lx, ly))
        return rect

    STALL_GOODS = OLD.Town.STALL_GOODS[:4] + [("Merchant", "SHOP-Market_Tinker", "Pots, pails and tools: a bit of "
                                                                         "everything for the road.")] +         OLD.Town.STALL_GOODS[4:]

    def stall(self, gx, gy, i):
        who, rack, cry = self.STALL_GOODS[i % len(self.STALL_GOODS)]
        m, x, y = self.atlas.at(gx, gy)
        self.statics.append((m.name, K.obj_line("StaticObject", "Market_Stall_Open", x, y)))
        pid = self.uid("Stall")
        self.person(m.name, who, x, y - 1, pid, "Stand=1 Face=S", self.rng.choice(OLD.NAMES["person"]))
        self.shop_script(pid, who, cry, rack)

    def lay_streets(self, rows_wanted):
        """The avenues out of the square, its top and foot rows on east and west, and more rows every PERIOD (north
        of the square past a block tall enough for its big buildings), nearest first."""
        bx1, by1, bx2, by2 = self.box
        if self.sq:
            x1, y1, x2, y2 = self.sq
            mid = (x1 + x2) // 2
            self.avenue_x = mid
            wide = self.spec["size"] in ("huge", "large")
            for dx in ((0, 1) if wide else (0,)):
                self.avenues.append(("N", self.run((mid + dx, y1 - 1), (0, -1), wobble=False)))
                self.avenues.append(("S", self.run((mid + dx, y2 + 1), (0, 1), wobble=False)))
            ys = [y1, y2]
            north, south = [], []
            y = y1 - NORTH_BLOCK + PERIOD
            for k in range(12):
                y = snap_north(y - PERIOD)
                north.append(y)
            y = y2
            for k in range(12):
                y = snap_south(y + PERIOD)
                south.append(y)
            for a, b in zip(north, south):
                ys += [b, a]
            starts = {y1: (x1 - 1, x2 + 1), y2: (x1 - 1, x2 + 1)}
        else:
            cx, cy = self.centre
            mid = cx
            self.avenue_x = mid
            ys, yn, ysouth = [cy], cy, cy
            for k in range(5):
                ysouth, yn = snap_south(ysouth + PERIOD), snap_north(yn - PERIOD)
                ys += [ysouth, yn]
            starts = {}
            self.avenues.append(("N", self.run((cx, cy - 1), (0, -1), stop=PERIOD * 2 + 1)))
            self.avenues.append(("S", self.run((cx, cy + 1), (0, 1), stop=PERIOD * 2 + 1)))
        made = 0
        for y in ys:
            if made >= rows_wanted:
                break
            if not by1 - SPREAD + 2 <= y <= by2 + SPREAD - 1:
                continue
            w_start, e_start = starts.get(y, (mid - 1, mid + 1))
            if (mid, y) in self.cells and y not in starts:
                self.lay((mid, y))
            west = self.run((w_start, y), (-1, 0))
            east = self.run((e_start, y), (1, 0))
            if len(west) + len(east) >= 8:
                made += 1
                self.rows.append((y, "W", west))
                self.rows.append((y, "E", east))
        return made

    # ------------------------------------------------------------------ plots
    def fits(self, x1, y1, x2, y2, door, margin=1):
        """A building's walls x1..x2, y1..y2 fit: in one map, off its edges, on clear ground, a street under the door,
        nothing within margin of it but ground and street."""
        if not (self.edge_ok(x1, y1) and self.edge_ok(x2, y2)):
            return False
        if x1 // XT != x2 // XT or y1 // YT != y2 // YT:
            return False
        if (door, y2 + 1) not in self.street:
            return False
        for y in range(y1 - margin, y2 + 1):
            for x in range(x1 - margin, x2 + margin + 1):
                c = (x, y)
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if not self.usable(c):
                        return False
                elif c in self.atlas.taken or c in self.reserved:
                    return False
        for x in range(x1, x2 + 1):                                  # (its front looks onto the street or ground)
            c = (x, y2 + 1)
            if c in self.atlas.taken or (c not in self.street and c not in self.cells):
                return False
        return True

    def take(self, lot):
        for y in range(lot.y1, lot.y2 + 1):
            for x in range(lot.x1, lot.x2 + 1):
                self.atlas.taken.add((x, y))
        self.lots.append(lot)

    def frontage(self, near=None):
        """Every street cell a door could open onto (open ground above it), nearest `near` first."""
        near = near or self.centre
        out = [c for c in self.street if (c[0], c[1] - 1) in self.cells and (c[0], c[1] - 1) not in self.street
               and (c[0], c[1] - 1) not in self.atlas.taken]
        out.sort(key=lambda c: (abs(c[0] - near[0]) + abs(c[1] - near[1]) * 1.3, c))
        return out

    def place(self, kind, name="", near=None, w=None, h=None, margin=1, spots=None):
        (wa, wb), (ha, hb) = SIZE[kind]
        spots = spots if spots is not None else self.frontage(near)
        widths = [w] if w else list(range(wb, wa - 1, -1))
        heights = [h] if h else list(range(hb, ha - 1, -1))
        for sx, sy in spots[:3000]:
            for width in widths:
                for height in heights:
                    for off in sorted(range(1, width - 1), key=lambda o: abs(o - width // 2)):
                        x1 = sx - off
                        x2, y2 = x1 + width - 1, sy - 1
                        y1 = y2 - height + 1
                        if self.fits(x1, y1, x2, y2, sx, margin):
                            lot = OLD.Lot(kind, x1, y1, x2, y2, sx, name)
                            self.take(lot)
                            return lot
        self.missing.append(kind + (" " + name if name else ""))
        return None

    def civic(self):
        """The big buildings facing the square (or its top row), then the rest nearest the middle."""
        big = [(k, n) for k, n, c in self.size["civic"] for _ in range(c) if k in ("parliament", "cathedral",
                                                                                     "church", "chapel", "hall")]
        rest = [(k, n) for k, n, c in self.size["civic"] for _ in range(c) if k not in ("parliament", "cathedral",
                                                                                         "church", "chapel", "hall",
                                                                                         "palace")]
        near_top = ((self.sq[0] + self.sq[2]) // 2, self.sq[1]) if self.sq else self.centre
        for kind, name in big:
            lot = None
            if self.sq:
                lot = self.place(kind, name, spots=[c for c in self.frontage(near_top) if c[1] == self.sq[1]])
                if lot is None:
                    self.missing.pop()
            if lot is None:
                self.place(kind, name, near=near_top)
        self.lanes()
        for kind, name in rest:
            self.place(kind, name)

    def extra_rows(self, most=4):
        """Where the rows left room unused (a small island, a narrow valley): more short streets, nearest the middle
        first, each with room for buildings along it, joined to the rest."""
        made = 0
        ys = sorted({c[1] for c in self.cells}, key=lambda y: abs(y - self.centre[1]))
        for y in ys:
            if made >= most:
                break
            if y % YT < 6:
                continue                                   # (its buildings would cross into the map above)
            run = []
            best = []
            for x in sorted(c[0] for c in self.cells if c[1] == y):
                room = all(self.usable((x, y - k)) for k in range(0, 6)) and                     not any((x, y + k) in self.street for k in range(-7, 6) if k)    # (clear of the other streets)
                if room and (not run or x == run[-1] + 1):
                    run.append(x)
                else:
                    best = max(best, run, key=len)
                    run = [x] if room else []
            best = max(best, run, key=len)
            if len(best) < 12:
                continue
            cells = [(x, y) for x in best]
            for c in cells:
                self.lay(c)
            if not self.connect(cells[len(cells) // 2]):
                for c in cells:
                    self.unlay(c)
                continue
            self.rows.append((y, "W" if best[0] < self.avenue_x else "E", cells))
            made += 1
        return made

    def lanes(self):
        """The shops: a lane's shops side by side along the street nearest the square that has room."""
        for kinds, per in self.size["lanes"]:
            self.lane(kinds, per, self.centre)
        if "arms" in self.size:
            armoury = [lt for lt in self.lots if lt.kind == "armoury"]
            for kinds, per in self.size["arms"]:
                self.lane(kinds, per, (armoury[0].door, armoury[0].y2 + 1) if armoury else self.centre)

    def lane(self, kinds, per, near):
        kinds = kinds.split("+")
        made = []
        for k in range(per):
            spots = self.frontage(near)
            if made:                                              # (next door along the same street)
                last = made[-1]
                same = [c for c in spots if c[1] == last.y2 + 1]
                if same:
                    spots = sorted(same, key=lambda c: min(abs(c[0] - (last.x2 + 4)), abs(c[0] - (last.x1 - 4))))
            lot = self.place("shop", kinds[k % len(kinds)], spots=spots, w=5, h=5)
            if lot:
                made.append(lot)
        if made:
            a = min(made, key=lambda lt: lt.x1)
            self.lane_signs.append(((a.x1 - 1, a.y2), " & ".join(OLD.LANES[k][3] for k in kinds),
                                    "A lane off the market square."))

    def gardens(self, n):
        for _ in range(n):
            if self.place("garden", "Gardens", margin=1) is None:
                self.missing.pop()
                return

    def houses(self):
        """Houses along the streets, nearest the middle first, each its own width and height and a gap of 1 to 3
        between; so many streets of them, so many to a street."""
        groups = self.house_groups                       # (more on a second go: after extra_rows)
        want, per = self.size["streets"], self.size["per"]
        row_of = {}
        for y, side, cells in self.rows:
            for c in cells:
                row_of[c] = (y, side == "W" if self.sq else h01("end", self.key, y) < 0.5)
        for c in self.frontage():
            if (c[0], c[1] - 1) in self.atlas.taken or LAND.DECOR.get(c):
                continue
            g = row_of.get(c)
            if g is None:
                continue                                    # (an avenue, a lane: the houses face the rows)
            if g not in groups and len(groups) >= want:
                continue
            if len(groups.get(g, [])) >= per:
                continue
            (wa, wb), (ha, hb) = SIZE["house"]
            w = wa + int(h01("hw", self.key, c) * (wb - wa + 1))
            h = ha + int(h01("hh", self.key, c) * (hb - ha + 1))
            gap = 1 + int(h01("gap", self.key, c) * 2)
            for off in sorted(range(1, w - 1), key=lambda o: abs(o - w // 2)):
                x1 = c[0] - off
                if self.fits(x1, c[1] - h, x1 + w - 1, c[1] - 1, c[0], margin=gap):
                    lot = OLD.Lot("house", x1, c[1] - h, x1 + w - 1, c[1] - 1, c[0])
                    self.take(lot)
                    groups.setdefault(g, []).append(lot)
                    break
        self.house_groups = groups
        return sum(len(v) for v in groups.values())

    def trim(self):
        """Each row's street ends a few tiles past the last thing on it (unevenly)."""
        fronts = {(x, lt.y2 + 1) for lt in self.lots for x in range(lt.x1 - 1, lt.x2 + 2)}
        for y, side, cells in self.rows:
            last = -1
            for i, c in enumerate(cells):
                crossing = any(n in self.street and n not in cells for n in ((c[0], c[1] - 1), (c[0], c[1] + 1)))
                if c in fronts or crossing:
                    last = i
            keep = last + 2 + int(h01("trim", self.key, y, side) * 4)
            for c in cells[keep:]:
                if not any(n in self.street and n not in cells for n in ((c[0], c[1] - 1), (c[0], c[1] + 1))):
                    self.unlay(c)
            del cells[keep:]
        both = {c for _, cells in self.avenues for c in cells}
        for side, cells in self.avenues:                     # (and the avenues, past the last street they cross)
            last = -1
            for i, c in enumerate(cells):
                if any(n in self.street and n not in both for n in ((c[0] - 1, c[1]), (c[0] + 1, c[1]))):
                    last = i
            keep = last + 3 + int(h01("trim", self.key, side) * 4)
            for c in cells[keep:]:
                self.unlay(c)
            del cells[keep:]

    def lanes_between(self):
        """North-south lanes joining each row to the next near their ends (so the streets make blocks)."""
        by_side = {}
        for y, side, cells in self.rows:
            if cells:
                by_side.setdefault(side, []).append((y, cells))
        for side, rows in by_side.items():
            rows.sort()
            for (ya, a), (yb, b) in zip(rows, rows[1:]):
                if yb - ya > NORTH_BLOCK + 2:
                    continue
                xa, xb = sorted(c[0] for c in a), sorted(c[0] for c in b)
                if side == "W":
                    xs = range(max(xa[0], xb[0]) + 1, max(xa[0], xb[0]) + 9)
                else:
                    xs = range(min(xa[-1], xb[-1]) - 1, min(xa[-1], xb[-1]) - 9, -1)
                for x in xs:
                    col = [(x, y) for y in range(ya + 1, yb)]
                    if (x, ya) in self.street and (x, yb) in self.street and all(
                            c in self.cells and c not in self.atlas.taken for c in col):
                        for c in col:
                            self.lay(c)
                        break

    # ------------------------------------------------------------------ signs, stones
    def street_sign(self, c, title, words):
        if c not in self.cells or c in self.atlas.taken or c in self.street:
            return False
        m, x, y = self.atlas.at(*c)
        pid = self.uid("Notice")
        self.statics.append((m.name, "StaticObject\tNotice\t%d\t%d\tId=%s" % ((x - 1) * TW, (y - 1) * TW + 2, pid)))
        self.atlas.taken.add(c)
        self.scripts["Read " + pid] = [
            (">Distance.From.Clicked.Entity", "64", "@far"),
            K.say("Notice", "%s\\%s" % (title.upper(), words), ("Okay", "@end")),
            ("@end",), ("End",),
            ("@far",), ("Display.Message", "DarkRed", "You can't read that from here!", "Denied"), ("End",),
        ]
        return True

    def notice(self, gx, gy, title, text):
        """(towns.furnish's: a notice by a building's door: on the ground beside it, not the street)"""
        for c in ((gx, gy - 1), (gx + 1, gy - 1), (gx - 1, gy - 1), (gx, gy), (gx + 1, gy)):
            if self.street_sign(c, title, text):
                return

    def name_streets(self):
        """A notice at the outer end of each street of houses: its name."""
        names = list(STREET_NAMES)
        random.Random(self.key).shuffle(names)
        for (y, west), lots in sorted(self.house_groups.items()):
            if len(lots) < 2:
                continue
            end = min(lots, key=lambda lt: lt.x1) if west else max(lots, key=lambda lt: lt.x2)
            name = next((n for n in names if n not in USED_STREETS), "Long Row")
            USED_STREETS.add(name)
            spots = ((end.x1 - 1, y - 1), (end.x1 - 2, y - 1)) if west else ((end.x2 + 1, y - 1), (end.x2 + 2, y - 1))
            for c in spots:
                if self.street_sign(c, name, "Houses of %s." % self.title):
                    self.streets += 1
                    break

    def stones(self):
        """A shardstone and a homestone by the square (or the middle), unless the place has its own already."""
        near = ((self.sq[0] + self.sq[2]) // 2, self.sq[3] + 2) if self.sq else self.centre
        have = set()
        for m in self.maps_of():
            for ln in m.ents:
                f = ln.split("\t")
                if f[0] == "StaticObject" and f[1] in ("Shardstone", "Homestone"):
                    have.add(f[1])
        for kind in ("Shardstone", "Homestone"):
            if kind in have:
                continue
            spot = self.free_spot(near)
            if spot is None:
                self.missing.append(kind)
                continue
            m, x, y = self.atlas.at(*spot)
            self.statics.append((m.name, "StaticObject\t%s\t%d\t%d" % (kind, (x - 1) * TW, (y - 1) * TW)))
            self.atlas.taken.add(spot)
            if kind == "Shardstone":
                self.ids.append((m.name, "Waystone_%s" % self.key, x, min(YT, y + 1)))
                self.shardstone = (m.name, x, y)

    def free_spot(self, near, r=12):
        """The nearest open cell to near with street beside it (a stone, a sign: by the road, not on it)."""
        best = None
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                c = (near[0] + dx, near[1] + dy)
                if c not in self.cells or c in self.atlas.taken or c in self.street or not self.edge_ok(*c):
                    continue
                if not any(n in self.street for n in ((c[0], c[1] + 1), (c[0] + 1, c[1]), (c[0] - 1, c[1]))):
                    continue
                if (c[0], c[1] + 1) in self.atlas.taken:
                    continue
                d = abs(dx) + abs(dy)
                if best is None or d < best[0]:
                    best = (d, c)
        return None if best is None else best[1]

    def box_has(self, c, r=0):
        x1, y1, x2, y2 = self.box
        return x1 - r <= c[0] <= x2 + r and y1 - r <= c[1] <= y2 + r

    def connect(self, c, material=None):
        """A street from c to the nearest street (over the town's free ground)."""
        from collections import deque
        seen = {c: None}
        q = deque([c])
        while q:
            p = q.popleft()
            if p != c and p in self.street:
                while p is not None:
                    if p not in self.street and p not in self.atlas.taken:
                        self.lay(p, material)
                    p = seen[p]
                return True
            for n in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                if n not in seen and (n in self.street or n in self.cells and n not in self.atlas.taken):
                    seen[n] = p
                    q.append(n)
        return False

    def rewild(self):
        """The wild comes back round the town: its ground cleared near its streets and buildings, then a fringe of the
        land's own open ground (meadow flowers and long grass on green land; bare snow, ash or sand), then what grew
        there before (woods, rocks, ponds), the edges wandering."""
        from collections import deque
        from atlas import fbm
        used = {c for c in self.cells if c in self.street or c in self.atlas.taken}
        dist = {c: 0 for c in used}
        q = deque(used)
        while q:
            x, y = q.popleft()
            if dist[(x, y)] >= 14:
                continue
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in self.cells and n not in dist:
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        forest = self.spec.get("forest")
        for c, (cell, ground, decor) in self.wild.items():
            if c in used or c in self.atlas.roads:
                continue
            d = dist.get(c, 99)
            edge = 2 + 7 * fbm(c[0], c[1], 11, 91)
            if forest:                                         # (a forest town: the trees close round it, in it)
                self.forest_cell(c, d)
                continue
            if d <= edge:
                continue                                       # (cleared, round the town)
            if d > edge + 3 + 4 * fbm(c[0], c[1], 7, 92):     # (the wild, as it was)
                m, x, y = self.atlas.at(*c)
                m.rows[y - 1][x - 1] = cell
                LAND.GROUND[c], LAND.DECOR[c] = ground, decor
                continue
            r = h01("meadow", c)                               # (the fringe: open, a little growing on it)
            green = self.atlas.tile(*c) == "Grass001"
            d2 = ("Flowers%03d" % (1 + int(r * 300) % 3) if r < 0.08 else "Tall_Grass001" if r < 0.2 else
                  "Bush001" if r < 0.23 else "") if green else ("Pebbles%03d" % (1 + int(r * 900) % 3) if r < 0.05
                                                                else "")
            if d2:
                self.atlas.set(c[0], c[1], decor=d2)
                LAND.DECOR[c] = d2

    TREES = ("Tree001", "Tree002", "Oak_Tree001", "Yew_Tree001", "Tree001", "Oak_Tree001", "Bush001")

    def forest_cell(self, c, d):
        """A forest town's ground at c, d tiles from its streets and buildings: a tree or two among the houses, thick
        trees a few tiles out, then the deep forest."""
        from atlas import fbm
        r = h01("forest", c)
        if d <= 1:
            return
        if d >= 3 + 2 * fbm(c[0], c[1], 6, 94) and r < 0.75:
            tile, tree = "Forest001", ""
        else:
            tile = "Grass001"
            tree = self.TREES[int(r * 70) % len(self.TREES)] if r < (0.4 if d < 3 else 0.9) else ""
        self.atlas.set(c[0], c[1], tile=tile, decor=tree)
        LAND.GROUND[c], LAND.DECOR[c] = tile, tree

    def deep_woods(self, reach=30):
        """Round a forest town, beyond the ground it cleared: the woods thick for reach tiles."""
        cx, cy = self.centre
        for gy in range(cy - reach, cy + reach + 1):
            for gx in range(cx - reach, cx + reach + 1):
                c = (gx, gy)
                if c in self.cells or c in self.atlas.taken or c in self.atlas.roads or c in LAND.RIVER:
                    continue
                if LAND.GROUND.get(c) != "Grass001" or (LAND.DECOR.get(c) or "").startswith(("Rock", "Standing")):
                    continue
                far = ((gx - cx) ** 2 + (gy - cy) ** 2) ** 0.5
                if far > reach * (0.7 + 0.3 * h01("rim", gx // 4, gy // 4)):
                    continue
                self.forest_cell(c, 12)

    def maps_of(self):
        x1, y1, x2, y2 = self.spec["maps"]
        return [m for n, m in self.atlas.maps.items() if x1 <= int(n.split(",")[0]) <= x2 and
                y1 <= int(n.split(",")[1]) <= y2]

    def entrance_sign(self):
        """A notice with the place's name by its middle."""
        spot = self.free_spot(((self.sq[0] + self.sq[2]) // 2 - 3, self.sq[3] + 1) if self.sq else self.centre)
        if spot:
            self.street_sign(spot, self.title, {"huge": "The royal city.", "large": "A port city.",
                                                "medium": "A city of Ashen.", "small": "A small city.",
                                                "town": "A town of Ashen.", "village": "A village.",
                                                "hamlet": "A hamlet."}[self.spec["size"]])

    # ------------------------------------------------------------------ its people
    def reached(self):
        """(towns.cart_stops': where you can get to in the town)"""
        return self.cells | set(self.street)

    def name_places(self):
        """Its places' names (quest markers, the world map): <key>_Square at its middle, and each hall's."""
        m, x, y = self.atlas.at(self.centre[0], self.centre[1] + 1)
        self.ids.append((m.name, "%s_Square" % self.key, x, y))
        for lot in self.lots:
            if lot.kind in ("hall", "parliament", "cathedral", "church", "chapel"):
                m, x, y = self.atlas.at(lot.door, lot.y2 + 1)
                pid = "%s_%s" % (self.key, (lot.name or lot.kind.capitalize()).replace(" ", "_"))
                if not any(i[1] == pid for i in self.ids):
                    self.ids.append((m.name, pid, x, y))

    PETS = ("Cat", "Dog", "Black_Cat", "Ginger_Cat")

    def pets(self, n):
        """The town's cats and dogs, about its middle."""
        for i in range(n):
            kind = self.PETS[(len(self.key) + i * 3 + sum(map(ord, self.key))) % len(self.PETS)]
            spot = self.free_spot((self.centre[0] + 4 * (i - n // 2), self.centre[1] + 3))
            if spot is None:
                continue
            m, x, y = self.atlas.at(*spot)
            self.npcs.append((m.name, "NPC\t%s\t%d\t%d\tAttitude=Good Zone=%d,%d,%d,%d Pause=4-12" % (
                kind, (x - 1) * TW, (y - 1) * TW - 8, max(2, x - 5), max(2, y - 4), min(XT - 1, x + 5),
                min(YT - 1, y + 4))))
            self.atlas.taken.add(spot)

    def home_map(self):
        """The map its middle (its square) is on."""
        return self.atlas.at(*self.centre)[0].name

    def spot_on(self, map_name, r=40):
        """A free cell of the town on map_name for someone to stand, nearest its middle (or the map's middle)."""
        mx, my = map_xy(map_name)
        near = self.centre if self.atlas.at(*self.centre)[0].name == map_name else (mx * XT + XT // 2,
                                                                                    my * YT + YT // 2)
        best = None
        for c in self.cells:
            if c[0] // XT != mx or c[1] // YT != my or c in self.atlas.taken or not self.edge_ok(*c):
                continue
            if (c[0], c[1] - 1) in self.atlas.taken or LAND.DECOR.get(c):
                continue
            d = abs(c[0] - near[0]) + abs(c[1] - near[1]) + (3 if c in self.street else 0)
            if d <= r and (best is None or d < best[0]):
                best = (d, c)
        if best is None:
            return None
        self.atlas.taken.add(best[1])
        return best[1]

    def adopt(self, staff):
        """Quest people at the desks of their buildings (staff: [(building's name, kind, their map line)]), in place
        of the clerk furnish put there."""
        for name, kind, line in staff:
            lot = next((lt for lt in self.lots if lt.kind == kind and lt.name == name), None)
            if lot is None or not getattr(lot, "speaker", None):
                self.missing.append("desk for " + line.split("Id=")[1].split()[0])
                continue
            for i, (map_name, npc) in enumerate(self.npcs):
                if ("Id=%s" % lot.speaker) in npc.split():
                    f, g = npc.split("\t"), line.split("\t")
                    self.npcs[i] = (map_name, "\t".join(g[:2] + f[2:4] + g[4:]))
                    self.scripts.pop("Talk to " + lot.speaker, None)
                    break

    # ------------------------------------------------------------------ furnishing
    def furnish_all(self):
        for lot in list(self.lots):
            if lot.kind in ("tavern", "inn") and not lot.name:
                names = [n for n in OLD.NAMES["tavern"] if n not in OLD.USED_TAVERNS]
                lot.name = self.rng.choice(names) if names else "The %s Arms" % self.title
                OLD.USED_TAVERNS.add(lot.name)
            if lot.kind == "house":
                house(self, lot)
            elif lot.kind in ("cathedral", "church", "chapel"):
                church(self, lot)
            elif lot.kind == "smithy":
                smithy(self, lot)
            elif lot.kind == "garden":
                garden(self, lot)
            else:
                OLD.furnish(self, lot)
        for (x, y), title, words in self.lane_signs:
            self.notice(x, y + 1, title, words)

    def write(self):
        for map_name, line in self.npcs + self.statics:
            self.atlas.maps[map_name].ents.append(line)
        for map_name, pid, x, y in self.ids:
            K.place_id(self.atlas.maps[map_name], pid, x, y)
        for name, rows in self.scripts.items():
            K.write_script(name, rows, MAKER)


# ================================================================== the buildings this file draws itself
BACKS = [   # a house's back wall, left to right ("bed": a bed, its foot below; "double": a double bed; "": nothing)
    ["bed", "", "Bookshelf001"], ["Bookshelf001", "bed", ""], ["bed", "bed", ""], ["", "Fireplace001", "bed"],
    ["bed", "Sacks001", "Barrel001"], ["double", "", "Bookshelf001"], ["Bookshelf001", "Potted_Plant002", "bed"],
    ["bed", "", "Crate001"], ["Fireplace001", "", "double"], ["Barrel001", "bed", "Bookshelf001"],
]
MIDDLES = [["Table001"], ["Table001", "Chair003"], ["Chair004", "Table001"], ["Dining_Table001"],
           ["Chair004", "Table001", "Chair003"], ["Desk001"]]


def interior(plan, lot):
    m, x1, y1 = plan.atlas.at(lot.x1, lot.y1)
    _, x2, y2 = plan.atlas.at(lot.x2, lot.y2)
    return m, x1, y1, x2, y2, lot.door - (lot.x1 - x1)


def house(plan, lot):
    """A house: its own walls and roof (the place's style), a chimney or not, its own furniture, perhaps someone home."""
    rng = random.Random("%s%d%d" % (plan.key, lot.x1, lot.y2))
    m, x1, y1, x2, y2, door = interior(plan, lot)
    wall = rng.choice(plan.style["walls"])
    roof = V.pick(rng, V.ROOFS.get(wall, [("Slate", 1)]))
    chimney = x1 + 1 + rng.randrange(max(1, x2 - x1 - 1)) if rng.random() < 0.7 else None
    windows = [x for x in range(x1 + 1, x2) if x != door and ((x - door) % 2 == 0 or rng.random() < 0.25)]
    K.building(m, x1, y1, x2, y2, door, wall=wall, roof=roof, windows=windows, chimney=chimney)
    back = BACKS[rng.randrange(len(BACKS))]
    cols = list(range(x1 + 1, x2))
    picks = [cols[0], cols[len(cols) // 2], cols[-1]] if len(cols) >= 3 else cols
    if rng.random() < 0.5:
        picks = picks[::-1]
    deep = y2 - y1 >= 4
    for x, piece in zip(picks, back):
        if not piece or m.decor(x, y1):
            continue
        if piece == "Fireplace001":
            m.set(x, y1, tile="Fireplace001")
        elif piece == "bed" and deep:
            m.set(x, y1, decor="Bed001")
            m.set(x, y1 + 1, decor="Bed002")
        elif piece == "double" and deep and x + 1 < x2 and not m.decor(x + 1, y1):
            m.set(x, y1, decor="Double_Bed001")
            m.set(x + 1, y1, decor="Double_Bed002")
            m.set(x, y1 + 1, decor="Double_Bed003")
            m.set(x + 1, y1 + 1, decor="Double_Bed004")
        elif piece not in ("bed", "double"):
            m.set(x, y1, decor=piece)
    if deep:
        middle = MIDDLES[rng.randrange(len(MIDDLES))]
        my = y2 - 2
        start = max(x1 + 1, (x1 + x2) // 2 - len(middle) // 2)
        for i, piece in enumerate(middle):
            x = start + i
            if x1 < x < x2 and x != door and not m.decor(x, my) and not m.decor(x, my - 1).startswith(("Bed", "Double")):
                m.set(x, my, decor=piece)
    for c in ((lot.x1 - 1, lot.y2), (lot.x2 + 1, lot.y2)):          # (a flower tub, a barrel by the wall)
        if rng.random() < 0.35 and c in plan.cells and c not in plan.atlas.taken and c not in plan.street:
            plan.atlas.set(*c, decor=rng.choice(("Flower_Bed001", "Flower_Bed002", "Flower_Bed003", "Barrel001",
                                                 "Potted_Plant002")))
            plan.atlas.taken.add(c)
    if rng.random() < 0.5:
        folk = rng.choice(("Villager", "Man", "Woman", "Farmer"))
        pid = plan.uid("Resident")
        plan.person(m.name, folk, (x1 + x2) // 2, y2 - 1, pid, "Zone=%d,%d,%d,%d Pause=5-15" % (
            x1 + 1, y1 + 1, x2 - 1, y2 - 1), rng.choice(OLD.NAMES["person"]))
        plan.scripts["Talk to " + pid] = [
            K.say(folk, rng.choice(OLD.HOME_LINES).replace("TOWN", plan.title), ("Goodbye.", "@end")),
            ("@end",), ("End",)]


def church(plan, lot):
    """A church (a cathedral, a chapel), as the Isle's chapel is built: stone, stained glass in its front, its steeple
    over the door (a cathedral three), pews either side of the aisle, the altar and candles at the back, the priest."""
    m, x1, y1, x2, y2, door = interior(plan, lot)
    K.building(m, x1, y1, x2, y2, door, wall="Stone_Wall001", roof="Slate", windows=[], floor="Tile001")
    for y in range(y1, y2):                                      # (stone walls round tiles, as the chapel's)
        for x in range(x1, x2 + 1):
            t = m.tile(x, y)
            if "_Thin_Plank" in t:
                m.set(x, y, tile=t.replace("_Thin_Plank", "_Thin_Tile"))
    for x in range(x1, x2 + 1):
        if x != door:
            m.set(x, y2, tile="Chapel_Stone001", decor="Stained_Glass001" if (x - x1) % 2 == 1 else "")
    g = max(m.groups() | {0})
    for x in range(x1, x2 + 1):                                  # its roof, then the gable's stone under the eaves
        for y in range(y1, y2 - 1):
            m.set(x, y, roof="%s.%02d" % (V.roof_piece("Slate", x, y, x1, y1, x2, y2 - 2), g))
        m.set(x, y2 - 1, roof="Chapel_Stone_Upper%03d.%02d" % (2 if (x - x1) in (1, x2 - x1 - 1) else 1, g))
    towers = [door] if lot.kind != "cathedral" else [x1 + 1, x2 - 1, door]
    for tx in towers:
        for i, piece in enumerate(("Steeple001", "Steeple002", "Steeple_Spire003", "Steeple_Spire002",
                                   "Steeple_Spire001")):
            y = y2 - 1 - i
            if y >= y1:
                m.set(tx, y, roof="%s.%02d" % (piece, g))
    for y in range(y1 + 3, y2 - 1):
        for x in range(x1 + 1, x2):
            if x != door:
                m.set(x, y, decor="Bench001")
    m.set(door, y1 + 1, decor="Table001")                              # the altar
    for x in (door - 1, door + 1):
        if x1 < x < x2:
            m.set(x, y1 + 1, decor="Candles001")
    for x in range(x1 + 1, x2):
        if (x - x1) % 3 == 1 and abs(x - door) > 1:
            m.set(x, y1, decor="Banner001")
    pid = plan.uid("Priest")
    lot.pid = pid
    plan.person(m.name, "Villager", door, y1 + 2, pid, "Stand=1 Face=S", plan.rng.choice(OLD.NAMES["person"]))
    words = {"cathedral": "Welcome to the cathedral of TOWN. Sit a while: the light through the glass is lovely.",
             "church": "Welcome to TOWN's church. All are welcome here.",
             "chapel": "A quiet chapel. Sit, and rest your feet."}[lot.kind]
    plan.scripts["Talk to " + pid] = [K.say("Villager", words.replace("TOWN", plan.title), ("Thank you.", "@end")),
                                      ("@end",), ("End",)]
    plan.notice(lot.door + 2, lot.y2 + 1, "%s of %s" % (lot.name or "Church", plan.title), "All are welcome.")


def smithy(plan, lot):
    """A smithy: the forge (a furnace), an anvil, its racks, the smith."""
    m, x1, y1, x2, y2, door = interior(plan, lot)
    K.building(m, x1, y1, x2, y2, door, wall="Stone_Wall001", roof="Slate", chimney=x1 + 1)
    for x in range(x1 + 2, x2 - 1):
        m.set(x, y1, decor="Shelf_Goods001")
    plan.statics.append((m.name, K.obj_line("StaticObject", "Furnace", x1 + 1, y1 + 1)))
    plan.statics.append((m.name, K.obj_line("StaticObject", "Anvil", x2 - 1, y1 + 1)))
    pid = plan.uid("Smith")
    lot.pid = pid
    plan.person(m.name, "Blacksmith", (x1 + x2) // 2, y1 + 2, pid, "Stand=1 Face=S",
                plan.rng.choice(OLD.NAMES["person"]))
    plan.shop_script(pid, "Blacksmith", "Need something forged? Or use my furnace and anvil yourself.", "SHOP-Smith")
    plan.notice(lot.door + 2, lot.y2 + 1, "Smithy", "The forge of %s." % plan.title)


def garden(plan, lot):
    """A little park: paths crossing, flower beds, trees, benches, a statue or a fountain in the middle."""
    rng = random.Random("g%s%d%d" % (plan.key, lot.x1, lot.y1))
    cx, cy = lot.door, (lot.y1 + lot.y2) // 2
    for y in range(lot.y1, lot.y2 + 1):
        for x in range(lot.x1, lot.x2 + 1):
            if x == cx or y == cy:
                plan.atlas.set(x, y, tile="Gravel001", decor="")
            elif (x + y) % 3 == 0:
                plan.atlas.set(x, y, tile="Grass001", decor=rng.choice(("Flower_Bed001", "Flower_Bed002",
                                                                        "Flower_Bed003")))
            elif (x * 7 + y) % 5 == 0:
                plan.atlas.set(x, y, tile="Grass001", decor=rng.choice(("Tree001", "Oak_Tree001", "Bush001")))
            else:
                plan.atlas.set(x, y, tile="Grass001", decor="")
    plan.atlas.set(cx, cy, tile=plan.spec["street"], decor=rng.choice(("Statue001", "Fountain001")))
    for x, y in ((cx - 1, cy - 1), (cx + 1, cy + 1)):
        plan.atlas.set(x, y, decor="Bench001")
    m, x, y = plan.atlas.at(cx, lot.y2 + 1)
    plan.ids.append((m.name, plan.uid("Gardens"), x, y))


# ================================================================== a settlement, all of it
def settle(atlas, key, reserved, hint=None, keep=None, carts=None, staff=(), hooks=()):
    """Grows settlement key (layout.SETTLEMENTS) on its maps' open land; returns the plan (its .missing: what didn't
    fit)."""
    import layout as L
    spec = L.SETTLEMENTS[key]
    plan = Plan(atlas, key, spec, reserved, seed=key)
    plan.prepare(keep)
    plan.choose_centre(hint)
    size = plan.size
    if size["square"]:
        plan.sq = plan.lay_square(size["square"], stalls=5 if spec["size"] in ("huge", "large") else 4)
        if plan.sq:
            plan.centre = ((plan.sq[0] + plan.sq[2]) // 2, (plan.sq[1] + plan.sq[3]) // 2)
    rows = (size["streets"] + 1) // 2 + 3 + (2 if size["lanes"] else 0) + len(size["civic"]) // 4
    plan.lay_streets(rows)
    if "posh" in size:                                 # (the posh end: its own square on a street, its lane)
        posh = size["posh"]
        east = plan.centre[0] < (plan.box[0] + plan.box[2]) // 2
        rect = plan.on_a_street(posh["square"], (plan.centre[0] + (30 if east else -30), plan.centre[1] - 12))
        sq = plan.lay_square(posh["square"], name="Posh_Square", stalls=2, goods=5, rect=rect) if rect else None
        if sq:
            for kinds, per in posh["lanes"]:
                plan.lane(kinds, per, ((sq[0] + sq[2]) // 2, sq[3]))
        else:
            plan.missing.append("posh square")
    plan.civic()
    plan.gardens(size["gardens"])
    left = [m for m in plan.missing if m.split()[0] in SIZE]
    if left and plan.extra_rows():                     # (no room for some: more streets, and try again)
        plan.missing = [m for m in plan.missing if m not in left]
        for m in left:
            kind, _, name = m.partition(" ")
            if kind == "shop":
                plan.lane(name, 1, plan.centre)
            else:
                plan.place(kind, name)
    plan.houses()
    if len(plan.house_groups) < size["streets"] and plan.extra_rows():
        plan.houses()                                  # (streets of houses short: more streets, more houses)
    plan.trim()
    plan.lanes_between()
    plan.name_streets()
    plan.stones()
    plan.entrance_sign()
    plan.pets({"huge": 4, "large": 3, "medium": 2, "small": 2, "town": 1, "village": 1, "hamlet": 1}[spec["size"]])
    for hook in hooks:                       # (its port, its gates: before its people and scripts are written)
        hook(plan)
    if carts and size["carts"]:
        OLD.cart_stops(plan, carts(plan))
    plan.furnish_all()
    plan.adopt(staff)
    plan.name_places()
    plan.rewild()
    if spec.get("forest"):
        plan.deep_woods()
    plan.write()
    return plan
