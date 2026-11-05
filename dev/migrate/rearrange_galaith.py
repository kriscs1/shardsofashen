"""Galaith laid out again, inside the walls that stand (the owner's sketch): from the sea side to the dragon's side, west to east,

  * the Royal quarter in the middle of the west side, walled again, its gate on the boulevard, royal guards outside it; the
    Nobles' above and below it
  * the fountain, the graveyard and the orchard, and gardens
  * the Merchants' with the market square, above and below the boulevard
  * the hovels
  * two more walls, spaced apart, and the ground before the east gate kept for war: ramparts, palisades, stores, guards
  * the grand boulevard, tree-lined, marble, from the east gate to the palace door; the east gate put back at its end.

Every building is lifted whole with its rooms upstairs and in the cellar, people, Ids, locks and places, and what names their
coordinates follows them, so every script and quest still works. The outer walls, and all outside them, stay as they are.

Run once (a second run finds it done and stops).

  python -I "dev\\migrate\\rearrange_galaith.py" [--dry]   (then build_minimaps.py, validate.py)
"""
import glob
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from build_isle import Map, XT, YT                      # noqa: E402
import build_galaith_city as G                          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DONE = os.path.join(ROOT, "dev", "migrate", ".galaith_rearranged")
TW = 32
X1, X2, Y1, Y2 = -264, -82, 268, 377                    # (what's inside the outer walls)
BLVD = (302, 307)                                       # (the boulevard's rows: the east gate's are 304 and 305)
GATE_X = -81
ROYAL = (-264, 288, -224, 322)                          # (its walls: the outer wall on its west)
NOBLES = [(-263, 268, -226, 286), (-263, 325, -226, Y2)]
GREEN = (-222, -192)
MERCHANTS = [(-190, 268, -148, 300), (-190, 310, -148, Y2)]
AVENUE = (-178, -174)                                   # (from the back gate down to the boulevard)
HOVELS = [(-146, 268, -114, 300), (-146, 310, -114, Y2)]
INNER_WALLS = (-112, -96)
ENT_KINDS = G.ENT_KINDS
# (what's moved whole, by rectangles of what they are now, to where it goes: x, y of its top left)
AREAS = {
    "graveyard": ((-112, 270, -84, 285), (-221, 268)),
    "fountain": ((-111, 286, -84, 303), (-221, 284)),
    "orchard": ((-110, 307, -83, 325), (-218, 309)),      # (its cottage on one map)
    "market": ((-197, 314, -179, 329), (-189, 311)),
}
ROOF = re.compile(r"\+Roof\(([^)]*)\.(\d+)\)")
OPT_TILES = re.compile(r"\b(Zone|Chase|Nap|Patrol|Roost|Home|Bed)=([-\d,;/]+)")


def mxy(name):
    p = name.split(",")
    return int(p[0]), int(p[1]), int(p[2])


BASE = "82d4ac2d"                                       # (the last commit with the city as it was before any of this)


def committed(path):
    """A file as git has it at BASE: the city as it was before any of this, whatever a run before left behind."""
    raw = subprocess.run(["git", "show", BASE + ":" + path], cwd=ROOT, capture_output=True).stdout
    return raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")       # (data files are CRLF, whatever git keeps them as)


class Level:
    """One level's maps, as one grid of world cells, as committed before this was first run."""

    def __init__(self, z):
        self.z = z
        self.maps = {}
        self.groups = {}
        names = subprocess.run(["git", "ls-tree", "--name-only", BASE, "maps/"], cwd=ROOT, capture_output=True, text=True).stdout
        for line in names.split("\n"):
            n = os.path.basename(line.strip().strip('"'))[:-4]
            if not n.endswith(",%d" % z) or n.count(",") != 2:
                continue
            mx, my, _ = mxy(n)
            if -11 <= mx <= -4 and 12 <= my <= 17:
                m = Map(n, new=True)
                text = committed("maps/%s.txt" % n).decode("cp1252").replace("\r", "").split("\n")
                m.rows = [[c.strip() for c in text[y].split(":")][:XT] for y in range(YT)]
                m.ents = [ln for ln in text[YT:] if ln.strip()]
                self.maps[n] = m
        self.taken = set()

    def name_at(self, gx, gy):
        return "%d,%d,%d" % (gx // XT, gy // YT, self.z)

    def map_at(self, gx, gy, make=False):
        n = self.name_at(gx, gy)
        if n not in self.maps and make:
            self.maps[n] = Map(n, new=True)
        return self.maps.get(n)

    def get(self, gx, gy):
        m = self.map_at(gx, gy)
        return m.rows[gy % YT][gx % XT] if m else None

    def put(self, gx, gy, text, make=False):
        m = self.map_at(gx, gy, make)
        if m:
            m.rows[gy % YT][gx % XT] = text

    def set(self, gx, gy, tile=None, decor=None):      # (what lay_walls calls)
        c = self.get(gx, gy) or "Black001"
        bits = c.split("+")
        if tile:
            bits[0] = tile
        if decor is not None:
            bits = [b for b in bits if not b.startswith("Decor(")]
            if decor:
                bits.append("Decor(%s)" % decor)
        self.put(gx, gy, "+".join(bits))

    def new_group(self, name):
        self.groups[name] = self.groups.get(name, 20) + 1
        return self.groups[name]


def line_cell(line, name):
    """The world cell a map line stands on, or None."""
    mx, my, _ = mxy(name)
    p = line.split("\t")
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


def shift_opts(opts, dx, dy):
    """A map line's tiles in its options, moved dx, dy tiles on its own map."""
    def pts(m):
        n = [0]

        def one(num):
            v = int(num.group(0)) + (dx if n[0] % 2 == 0 else dy)
            n[0] += 1
            return str(v)
        return m.group(1) + "=" + re.sub(r"-?\d+", one, m.group(2))
    return OPT_TILES.sub(pts, opts)


def moved_line(line, name, dx, dy, z, rect=None):
    """(new map name, line) moved by dx, dy tiles. rect: what's moving with it: a home or a bed anywhere else isn't where it was
    (it's in another building, gone elsewhere, or on another map from them now): they go out by a door, as anyone with none."""
    mx, my, _ = mxy(name)
    p = line.split("\t")
    if p[0] in ENT_KINDS:
        gx = mx * XT * TW + float(p[2]) + dx * TW
        gy = my * YT * TW + float(p[3]) + dy * TW
        nx, ny = int((gx + 16) // (XT * TW)), int((gy + 28) // (YT * TW))
        p[2], p[3] = "%d" % (gx - nx * XT * TW), "%d" % max(0, gy - ny * YT * TW)
        if len(p) > 4:
            for key in ("Bed", "Home", "Nap"):
                m = re.search(r"\b%s=(-?\d+),(-?\d+)" % key, p[4])
                if m and rect is not None:
                    bx, by = mx * XT + int(m[1]) - 1, my * YT + int(m[2]) - 1
                    tx, ty = bx + dx, by + dy
                    if not in_rect(bx, by, rect):
                        p[4] = re.sub(r"\s*\b(%s|%s\.Level)=\S*" % (key, key), "", p[4]).strip()
                    elif (tx // XT, ty // YT) != (nx, ny):      # (the area runs over a map edge: on their bed's map)
                        nx, ny = tx // XT, ty // YT
                        p[2], p[3] = str((tx % XT) * TW), str(min(YT - 1, ty % YT + 1) * TW - 8)
            p[4] = shift_opts(p[4], (mx - nx) * XT + dx, (my - ny) * YT + dy)
        return "%d,%d,%d" % (nx, ny, z), "\t".join(p)
    i = 1 if p[0] == "Lock" else 2
    gx, gy = mx * XT + int(p[i]) - 1 + dx, my * YT + int(p[i + 1]) - 1 + dy
    p[i], p[i + 1] = str(gx - (gx // XT) * XT + 1), str(gy - (gy // YT) * YT + 1)
    return "%d,%d,%d" % (gx // XT, gy // YT, z), "\t".join(p)


class Lift:
    """A rectangle of a level: its cells and lines, taken off. whole: and all its rooms, however far past it they run (a
    vault under a hall is bigger than the hall)."""

    def __init__(self, level, rect, blank, margin=False, whole=False):
        x1, y1, x2, y2 = rect
        self.rect = rect
        self.cells = {}
        self.lines = []
        todo = [(gx, gy) for gy in range(y1, y2 + 1) for gx in range(x1, x2 + 1)]
        seen = set(todo)
        while todo:
            gx, gy = todo.pop()
            c = level.get(gx, gy)
            if c is None or (whole and c == "Black001"):
                continue
            self.cells[(gx, gy)] = c
            level.put(gx, gy, blank(gx, gy))
            if whole:
                for n in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
                    if n not in seen:
                        seen.add(n)
                        todo.append(n)
        if whole:
            for name, m in level.maps.items():
                keep = []
                for ln in m.ents:
                    c = line_cell(ln, name)
                    if c in self.cells:
                        self.lines.append((ln, name))
                    else:
                        keep.append(ln)
                m.ents = keep
            return
        for name, m in level.maps.items():
            keep = []
            for ln in m.ents:
                c = line_cell(ln, name)
                # (a building's sign and its notice stand just off it)
                if c and x1 - (1 if margin else 0) <= c[0] <= x2 + (1 if margin else 0) and \
                        y1 <= c[1] <= y2 + (2 if margin else 0):
                    self.lines.append((ln, name))
                else:
                    keep.append(ln)
            m.ents = keep

    def drop(self, level, dx, dy, make=False):
        regroup = {}
        for (gx, gy), text in self.cells.items():
            if text == "Black001":                      # (nothing there: what's there already, stays)
                continue
            nx, ny = gx + dx, gy + dy
            n = level.name_at(nx, ny)

            def sub(mt):
                key = (n, mt.group(2))
                if key not in regroup:
                    regroup[key] = level.new_group(n)
                return "+Roof(%s.%02d)" % (mt.group(1), regroup[key])
            if make or level.map_at(nx, ny) is not None:
                level.put(nx, ny, ROOF.sub(sub, text), make=make)
                level.taken.add((nx, ny))
        for ln, name in self.lines:
            n, moved = moved_line(ln, name, dx, dy, level.z, self.rect)
            if n not in level.maps and make:
                level.maps[n] = Map(n, new=True)
            if n in level.maps:
                level.maps[n].ents.append(moved)


def in_rect(gx, gy, r):
    return r[0] <= gx <= r[2] and r[1] <= gy <= r[3]


def paving(gx, gy):
    if BLVD[0] <= gy <= BLVD[1] and ROYAL[2] - 19 <= gx <= X2:
        return "Marble_Paving001"
    if in_rect(gx, gy, ROYAL):
        return "Royal_Paving001"
    if any(in_rect(gx, gy, r) for r in NOBLES):
        return "Noble_Paving001"
    return "Flagstone001"


def pack(blocks, rects, keep_out, gapx=2, gapy=3):
    """Blocks onto shelves in rects: [(block, x, y)], and those that didn't fit. Doors look south: a street under each shelf.
    A building stands on one map, never across an edge: a roof's group is its own map's, and half of it wouldn't lift."""
    placed, todo = [], sorted(blocks, key=lambda b: (-b.h, -b.w))
    for x1, y1, x2, y2 in rects:
        y = y1
        while todo and y < y2:
            x, tallest, left = x1, 0, []
            for b in todo:
                bx = x
                moved = True
                while moved:
                    moved = False
                    for kx1, ky1, kx2, ky2 in keep_out:
                        if bx <= kx2 + 1 and bx + b.w - 1 >= kx1 - 1 and y <= ky2 + 1 and y + b.h - 1 >= ky1 - 1:
                            bx = kx2 + 2
                            moved = True
                if bx // XT != (bx + b.w - 1) // XT:
                    bx = (bx // XT + 1) * XT
                if bx + b.w - 1 <= x2 and y + b.h - 1 <= y2 and y // YT == (y + b.h - 1) // YT:
                    placed.append((b, bx, y))
                    x = bx + b.w + gapx
                    tallest = max(tallest, b.h)
                else:
                    left.append(b)
            todo = left
            y += tallest + gapy if tallest else 1
    return placed, todo


def scatter(blocks, rects, rng, gap=2):
    """Blocks set down about rects at random, not in rows (the hovels: the owner's wish): [(block, x, y)], and those that
    found no room. Each on one map, a gap round it, and a cell clear under its door."""
    placed, left, boxes = [], [], []
    for b in sorted(blocks, key=lambda b: -(b.w * b.h)):
        for _ in range(1500):
            x1, y1, x2, y2 = rng.choice(rects)
            if x2 - x1 + 1 < b.w or y2 - y1 + 1 < b.h + 1:
                continue
            x, y = rng.randint(x1, x2 - b.w + 1), rng.randint(y1, y2 - b.h)
            if x // XT != (x + b.w - 1) // XT or y // YT != (y + b.h - 1) // YT:
                continue
            if any(x <= bx2 + gap and x + b.w - 1 >= bx1 - gap and y <= by2 + gap + 1 and y + b.h >= by1 - gap
                   for bx1, by1, bx2, by2 in boxes):
                continue
            placed.append((b, x, y))
            boxes.append((x, y, x + b.w - 1, y + b.h - 1))
            break
        else:
            left.append(b)
    return placed, left


def lines_at(level, cells_rect):
    return [(ln, n) for n, m in level.maps.items() for ln in m.ents
            if (lambda c: c and in_rect(c[0], c[1], cells_rect))(line_cell(ln, n))]


def garden(ground, rect, rng):
    """The gardens, from the orchard down to the south wall (the owner's wish: green from wall to wall): lawns in beds
    of hedge, gravel walks across them, a pond, statues, flower beds, benches and lamps, trees standing in the grass."""
    x1, y1, x2, y2 = rect
    mid = (x1 + x2) // 2
    walks_y = list(range(y1 + 2, y2 - 1, 12))
    pond = (mid - 3, (y1 + y2) // 2 - 2, mid + 3, (y1 + y2) // 2 + 2)
    for gy in range(y1, y2 + 1):
        for gx in range(x1, x2 + 1):
            c = ground.get(gx, gy)
            if c is None or c.split("+")[0] not in ("Flagstone001", "Marble_Paving001") or "+" in c:
                continue
            walk = abs(gx - mid) <= 1 or gy in walks_y or gy - 1 in walks_y or gx in (x1 + 1, x2 - 1)
            if in_rect(gx, gy, pond):
                edge = gx in (pond[0], pond[2]) or gy in (pond[1], pond[3])
                ground.put(gx, gy, "Gravel001" if edge else "Pond001")
            elif walk:
                ground.put(gx, gy, "Gravel001")
            elif gx in (x1, x2) or (gy - 1 in walks_y[:1] and False):
                ground.put(gx, gy, "Hedge001")
            else:
                ground.put(gx, gy, "Lawn001")
    for gy in range(y1, y2 + 1):                     # (each bed of lawn: hedged round, then planted)
        for gx in range(x1 + 2, x2 - 1):
            c = ground.get(gx, gy)
            if c != "Lawn001":
                continue
            near_walk = any(ground.get(gx + dx, gy + dy) == "Gravel001" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            r = rng.random()
            if near_walk and r < 0.18:
                ground.put(gx, gy, "Lawn001+Decor(Flower_Bed%03d)" % rng.randint(1, 3))
            elif near_walk and r < 0.22 and ground.get(gx, gy + 1) == "Gravel001":
                ground.put(gx, gy, "Lawn001+Decor(Bench001)")
            elif not near_walk and r < 0.07:
                ground.put(gx, gy, "Lawn001+Decor(%s)" % rng.choice(("Tree001", "Tree002", "Oak_Tree001")))
            elif not near_walk and r < 0.09:
                ground.put(gx, gy, "Lawn001+Decor(%s)" % rng.choice(("Flowers001", "Flowers002", "Flowers003")))
    for gy in walks_y:                               # (statues where the walks cross, lamps along them)
        for gx in (mid - 3, mid + 3):
            if ground.get(gx, gy - 1) == "Lawn001":
                ground.put(gx, gy - 1, "Lawn001+Decor(Statue00%d)" % rng.randint(1, 2))
        for gx in range(x1 + 4, x2 - 2, 6):
            if ground.get(gx, gy + 2) == "Lawn001":
                ground.put(gx, gy + 2, "Lawn001+Decor(Lamp_Post001)")


def main(dry=False):
    if os.path.exists(DONE) and "--again" not in sys.argv and not dry:
        print("Galaith's been laid out again already (--again does it again, from what's committed).")
        return
    rng = random.Random(77)
    ground = Level(0)
    others = [Level(z) for z in (-2, -1, 1, 2)]
    lifted = G.Lifted(ground.maps)
    blocks, used = G.lift_blocks(lifted)
    inside = (X1, Y1, X2, Y2)

    def is_in(gx, gy):
        return in_rect(gx, gy, inside)

    blocks = [b for b in blocks if is_in(b.x1, b.y1) and is_in(b.x2, b.y2)]
    orchard = AREAS["orchard"][0]
    blocks = [b for b in blocks if not in_rect(b.x1, b.y1, orchard)]
    palace = next(b for b in blocks if b.role == "palace")
    nobles = [b for b in blocks if b is not palace and b.y1 < 305]
    merchants = [b for b in blocks if b is not palace and 305 <= b.y1 < 346]
    hovels = [b for b in blocks if b is not palace and b.y1 >= 346]

    keep_out = [(AVENUE[0], Y1, AVENUE[1], BLVD[0] - 1)]
    market_at, market_rect = AREAS["market"][1], AREAS["market"][0]
    market_w, market_h = market_rect[2] - market_rect[0], market_rect[3] - market_rect[1]
    keep_out.append((market_at[0], market_at[1], market_at[0] + market_w, market_at[1] + market_h))
    placed, left = pack(nobles, NOBLES, [])
    p2, l2 = pack(merchants + left, MERCHANTS, keep_out)
    placed += p2
    p3, l3 = scatter(hovels + l2, HOVELS, rng)
    placed += p3
    if l3:
        print("No room for %d buildings" % len(l3))
        return
    print("Placed: %d buildings, the palace" % len(placed))
    if dry:
        for b, x, y in placed[:6]:
            print(b.role, b.x1, b.y1, "->", x, y)
        return

    # ----- everything inside comes off
    lifts = []                      # (the lift on each level, how far it goes)
    pal_x, pal_y = -250, BLVD[0] - palace.h             # (all on one map, -10,14: its scripts name that map's tiles)
    def plan(b, x, y):
        return (b.x1, b.y1, b.x2, b.y2), x - b.x1, y - b.y1
    moves = [plan(b, x, y) for b, x, y in placed] + [plan(palace, pal_x, pal_y)]
    for name, (rect, to) in AREAS.items():
        moves.append((rect, to[0] - rect[0], to[1] - rect[1]))
    for k, (rect, dx, dy) in enumerate(moves):
        margin = k <= len(placed)                       # (the buildings; the areas take what's in them)
        lifts.append((Lift(ground, rect, paving, margin), dx, dy, ground))
        for lv in others:
            lifts.append((Lift(lv, rect, lambda gx, gy: "Black001", whole=True), dx, dy, lv))
    # (what's left inside: walls, the old quarters' paving, and the loose people and things)
    loose = []
    for name, m in ground.maps.items():
        keep = []
        for ln in m.ents:
            c = line_cell(ln, name)
            if c and is_in(c[0], c[1]):
                loose.append((ln, name))
            else:
                keep.append(ln)
        m.ents = keep
    for gy in range(Y1, Y2 + 1):
        for gx in range(X1, X2 + 1):
            if ground.get(gx, gy) is not None:
                ground.put(gx, gy, paving(gx, gy))

    # ----- down again, in their new places
    for lift, dx, dy, lv in lifts:
        lift.drop(lv, dx, dy, make=lv is not ground)

    # ----- the walls: the Royal quarter's, the two at the war end
    royal_ring = [(gx, ROYAL[1]) for gx in range(ROYAL[0] + 1, ROYAL[2] + 1)] + \
        [(gx, ROYAL[3]) for gx in range(ROYAL[0] + 1, ROYAL[2] + 1)] + \
        [(ROYAL[2], gy) for gy in range(ROYAL[1], ROYAL[3] + 1)]
    gaps = [(ROYAL[2], gy) for gy in range(BLVD[0], BLVD[1] + 1)]
    G.lay_walls(ground, royal_ring, gaps)
    for wx in INNER_WALLS:
        cells = [(wx, gy) for gy in range(Y1, Y2 + 1)]
        G.lay_walls(ground, cells, [(wx, gy) for gy in range(BLVD[0], BLVD[1] + 1)])

    # ----- the east gate, at the boulevard's end
    for gy in (304, 305):
        ground.set(GATE_X, gy, tile="Burnt_Gate005", decor="")
    gate_map = ground.map_at(GATE_X, 304)
    gate_map.ents = [ln for ln in gate_map.ents if not (ln.startswith("Lock\t") and "GalaithQuest" in ln)]
    for gy in (304, 305):
        gate_map.ents.append("Lock\t%d\t%d\t$Attr.GalaithQuest>=2\tThe gate is barred. Something huge breathes behind you."
                             % (GATE_X % XT + 1, gy % YT + 1))

    # ----- towers either side of the gate, and the dragon's soot on the paving just inside it
    for gy, part in ((302, "Burnt_Wall003"), (303, "Burnt_Wall005"), (306, "Burnt_Wall003"), (307, "Burnt_Wall005")):
        ground.set(GATE_X, gy, tile=part, decor="")
    for gy in range(292, 318):
        for gx in range(GATE_X - 14, GATE_X):
            c = ground.get(gx, gy)
            d = abs(gx - GATE_X) + abs(gy - 304.5) * 0.8
            if c and "+" not in c and c.split("+")[0] in ("Flagstone001", "Marble_Paving001") and rng.random() < 0.85 - d / 14:
                ground.put(gx, gy, c + "+Decor(Scorch_Mark%03d)" % rng.randint(1, 3))

    # ----- the boulevard's trees, and the way from the back gate
    def tree(gx, gy):
        c = ground.get(gx, gy)
        if c and c.split("+")[0] in ("Flagstone001", "Marble_Paving001", "Royal_Paving001", "Noble_Paving001") and "+" not in c:
            ground.put(gx, gy, c + "+Under(Tree_Pit001)+Decor(%s)" % rng.choice(("Tree001", "Tree002", "Oak_Tree001")))
    for gx in range(ROYAL[2] + 3, X2 - 1, 5):
        if gx not in INNER_WALLS and abs(gx - INNER_WALLS[0]) > 1 and abs(gx - INNER_WALLS[1]) > 1:
            tree(gx, BLVD[0] - 1)
            tree(gx, BLVD[1] + 1)
    for gx in range(ROYAL[2] - 16, ROYAL[2] - 1, 5):
        tree(gx, BLVD[1] + 1)

    # ----- a garden or two round them, and the Royal quarter's
    def dress(rect, things, every):
        for gy in range(rect[1], rect[3] + 1):
            for gx in range(rect[0], rect[2] + 1):
                c = ground.get(gx, gy)
                if c and "+" not in c and c.split("+")[0] in ("Flagstone001", "Royal_Paving001", "Noble_Paving001") and \
                        (gx * 7 + gy * 13) % every == 0:
                    ground.put(gx, gy, c + "+Decor(%s)" % rng.choice(things))
    garden(ground, (GREEN[0], 329, GREEN[1], Y2 - 1), rng)
    dress((ROYAL[0] + 2, ROYAL[1] + 2, ROYAL[2] - 2, BLVD[0] - 9), ("Flower_Urn001", "Lamp_Post001"), 23)
    dress((ROYAL[0] + 2, BLVD[1] + 2, ROYAL[2] - 2, ROYAL[3] - 2), ("Flower_Urn001", "Lamp_Post001", "Bench001"), 23)

    # ----- the war end: ramparts by the walls, palisades, stores, and guards
    for wx in INNER_WALLS:
        for gy in range(Y1 + 2, Y2 - 1):
            if BLVD[0] - 1 <= gy <= BLVD[1] + 1:
                continue
            c = ground.get(wx + 2, gy)
            if c and "+" not in c:
                ground.put(wx + 2, gy, "Boardwalk001")
            c = ground.get(wx + 1, gy)
            if c and "+" not in c:
                ground.put(wx + 1, gy, "Boardwalk001")
    for bx in (-104, -89):
        for gy in range(BLVD[0] - 8, BLVD[0] - 1):
            ground.set(bx, gy, decor="Palisade002")
        for gy in range(BLVD[1] + 2, BLVD[1] + 9):
            ground.set(bx, gy, decor="Palisade002")
    for y0, y1 in ((276, 292), (318, 368)):
        for gy in range(y0, y1, 12):
            for gx in range(-106, -98):
                ground.set(gx, gy, decor="Palisade001")
            for gx in range(-92, -84):
                ground.set(gx, gy + 6, decor="Palisade001")
    for gy in range(272, 374, 3):
        for gx in (-100, -86):
            c = ground.get(gx, gy)
            if c and "+" not in c and rng.random() < 0.35:
                ground.put(gx, gy, c + "+Decor(%s)" % rng.choice(("Cellar_Crate001", "Cellar_Barrel001", "Rock001", "Sacks001")))

    def npc(kind, gx, gy, opts):
        m = ground.map_at(gx, gy)
        m.ents.append("NPC\t%s\t%d\t%d\t%s" % (kind, (gx % XT) * TW, max(0, (gy % YT) * TW - 8), opts))

    for wx in INNER_WALLS:
        for gy in list(range(272, BLVD[0] - 2, 7)) + list(range(BLVD[1] + 4, Y2 - 2, 7)):
            npc("Guard", wx + 1, gy, "Attitude=Good Stand=1 Face=E Schedule=Always")
        for gy in (BLVD[0] - 1, BLVD[1] + 1):
            npc("Guard", wx + 3, gy, "Attitude=Good Stand=1 Face=E Schedule=Always")
    for gx, gy in ((GATE_X - 2, BLVD[0] - 1), (GATE_X - 2, BLVD[1] + 1), (GATE_X - 5, BLVD[0] - 1), (GATE_X - 5, BLVD[1] + 1)):
        npc("Guard", gx, gy, "Attitude=Good Stand=1 Face=E Schedule=Always")
    for gx, gy in ((ROYAL[2] + 1, BLVD[0] - 1), (ROYAL[2] + 1, BLVD[1] + 1), (ROYAL[2] + 3, BLVD[0] - 1), (ROYAL[2] + 3, BLVD[1] + 1)):
        npc("Royal_Guard", gx, gy, "Attitude=Good Stand=1 Face=E Schedule=Always Name=Royal_Guard")

    # ----- the loose: the ones that walk the streets on the streets; what stood about, in the gardens
    def free_spot(rect):
        for _ in range(4000):
            gx, gy = rng.randint(rect[0], rect[2]), rng.randint(rect[1], rect[3])
            c = ground.get(gx, gy)
            if c and "+" not in c and c.split("+")[0] in ("Flagstone001", "Marble_Paving001"):
                return gx, gy
        return None
    for ln, name in loose:
        p = ln.split("\t")
        if p[0] == "Lock" or p[0] == "Trigger":
            continue
        if p[0] == "Id":
            if p[1] == "Galaith_West_Gate":
                m = ground.map_at(GATE_X - 1, 304)
                m.ents.append("Id\t%s\t%d\t%d" % (p[1], (GATE_X - 1) % XT + 1, 304 % YT + 1))
            else:
                print("Id with nowhere of its own:", p[1])
                m = ground.map_at(-180, BLVD[0] - 1)
                m.ents.append("Id\t%s\t%d\t%d" % (p[1], -180 % XT + 1, (BLVD[0] - 1) % YT + 1))
            continue
        spot = free_spot((GREEN[0], 329, GREEN[1], Y2)) if p[1] != "Guard" else free_spot((-190, BLVD[1] + 2, -114, BLVD[1] + 3))
        if spot is None:
            continue
        gx, gy = spot
        m = ground.map_at(gx, gy)
        p[2], p[3] = str((gx % XT) * TW), str(max(0, (gy % YT) * TW - 8))
        if len(p) > 4:
            p[4] = re.sub(r"\b(Zone|Chase|Patrol|Home|Bed|Nap|Roost)=\S*", "", p[4]).strip()
            if p[0] == "NPC" and "Stand=1" not in p[4]:
                x, y = gx % XT + 1, gy % YT + 1
                p[4] = (p[4] + " Zone=%d,%d,%d,%d" % (max(1, x - 3), max(1, y - 3), min(XT, x + 3), min(YT, y + 3))).strip()
        m.ents.append("\t".join(p))

    # ----- the town crier: no door on his map, so his tent, in the gardens
    for m in ground.maps.values():
        for ln in list(m.ents):
            if "Id=Town_Crier_Galaith" in ln:
                m.ents.remove(ln)
                p = ln.split("\t")
                g = ground.maps["-9,16,0"]
                p[2], p[3] = str(11 * TW), str(10 * TW - 8)
                g.ents.append("\t".join(p))
                g.rows[9][9] = g.rows[9][9].split("+")[0] + "+Decor(Tent001)"

    # ----- what names their coordinates
    pdx, pdy = pal_x - palace.x1, pal_y - palace.y1
    hall = next(b for b, *_ in placed if any("Archive_Hatch" in ln[3] for ln in b.lines))
    hdx, hdy = next((x - b.x1, y - b.y1) for b, x, y in placed if b is hall)
    old_palace = "%d,%d,0" % (palace.x1 // XT, palace.y1 // YT)
    new_palace = "%d,%d,0" % (pal_x // XT, pal_y // YT)
    for name in (old_palace + ".txt", "Talk to Rupert_On_Throne.txt", "Climb Down Archive_Hatch.txt"):   # (as committed)
        open(os.path.join(ROOT, "data", "Scripts", name), "wb").write(committed("data/Scripts/" + name))
    for stale in glob.glob(os.path.join(ROOT, "data", "Scripts", "-1[01],1[34],0.txt")):
        if os.path.basename(stale) != old_palace + ".txt":
            os.remove(stale)
    G.palace_script(pdx, pdy, old_palace, new_palace)
    path = os.path.join(ROOT, "data", "Scripts", "Climb Down Archive_Hatch.txt")
    s = open(path, "rb").read().decode("cp1252")

    def hatch(m):
        gx = (-8 if m.group(3) == "x" else int(m.group(3))) * XT * TW + int(m.group(1)) + hdx * TW
        gy = int(m.group(4)) * YT * TW + int(m.group(2)) + hdy * TW
        return "Teleport\t%d,%d\t%d,%d,-1" % (gx % (XT * TW), gy % (YT * TW), gx // (XT * TW), gy // (YT * TW))
    s = re.sub(r"Teleport\t(\d+),(\d+)\t(-?\d+),(\d+),-1", hatch, s)
    open(path, "wb").write(s.encode("cp1252"))
    G.carts([(X2 - 2, 305, "the east gate"), (-130, 305, "the hovels"), (-178, 305, "the market"),
             (-206, 305, "the fountain"), (ROYAL[2] - 2, 305, "the palace")])

    for lv in others:                                   # (rooms a run before left where no building is now)
        for path in glob.glob(os.path.join(ROOT, "maps", "*,%d.txt" % lv.z)):
            n = os.path.basename(path)[:-4]
            mx, my, _ = mxy(n)
            if -11 <= mx <= -4 and 12 <= my <= 17 and n not in lv.maps:
                os.remove(path)
    for lv in [ground] + others:
        for m in lv.maps.values():
            if lv is not ground and not m.ents and all(c == "Black001" for r in m.rows for c in r):
                if os.path.exists(m.path):              # (its rooms have gone with their building)
                    os.remove(m.path)
                continue
            m.save()
    open(DONE, "w").write("done\n")
    print("Galaith laid out again: palace %s" % new_palace)


if __name__ == "__main__":
    main("--dry" in sys.argv)
