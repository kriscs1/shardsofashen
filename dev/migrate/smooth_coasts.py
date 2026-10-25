"""No right angles on a coast: wherever grass or sand meets water in a square corner, a diagonal coast tile
(Water002-009 for grass, Sand_Water002-009 for sand, as the starting island's shores are drawn) cuts the corner off
(land sticking out into the water) or fills it in (water reaching into the land). Snow has its own (Snow_Water),
and so does marsh (Marsh_Water002-009, made here from the grass ones with the marsh's ground). Run it again any
time: it only changes square corners it finds. It also remakes the Isle's pond as open water with diagonal banks,
lilies (Lily_Pads001-004, drawn here) and reeds.

  python -I "dev\\migrate\\smooth_coasts.py"

Only plain Grass001/Sand001/Water001 cells change, and none with anything on them (decor, a roof, a trigger, a
thing standing there, an Id or a Lock).
"""
import glob
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from dragonsword import ini  # noqa: E402
from build_isle import Map, XT, YT, TW, TILES_INI  # noqa: E402

N, E, S, W = (0, -1), (1, 0), (0, 1), (-1, 0)
# a diagonal coast tile: which corner is water -> its two variants; and the water edges of each
WET_CORNER = {(S, W): (2, 3), (S, E): (4, 5), (N, E): (6, 7), (N, W): (8, 9)}
WET_EDGES = {v: set(k) for k, vs in WET_CORNER.items() for v in vs}
WATER = ("Water001", "Sea_Rock")
LAND = {"Grass001": "Water", "Sand001": "Sand_Water", "Snow001": "Snow_Water", "Marsh001": "Marsh_Water"}
SHORE = dict(LAND, Dirt001="Water", Forest001="Water")        # (what a filled corner's land is drawn as)
FAMILIES = ("Sand_Water", "Snow_Water", "Marsh_Water", "Water")   # (a mixed corner: the first of these)
SMALL = ("Flowers", "Pebbles", "Tall_Grass", "Grass_Tuft", "Clover", "Daisies", "Weeds", "Fern", "Reeds")


def diagonal(tile):
    """(family "Water"/"Sand_Water", variant 2-9) or None."""
    for fam in FAMILIES:
        if tile.startswith(fam) and tile[len(fam):].isdigit():
            v = int(tile[len(fam):])
            if v in WET_EDGES:
                return fam, v
    return None


class World:
    def __init__(self):
        self.maps = {}
        for path in glob.glob(os.path.join(ROOT, "maps", "*,0.txt")):
            name = os.path.basename(path)[:-4]
            bits = name.split(",")
            if len(bits) == 3 and all(b.lstrip("-").isdigit() for b in bits):
                self.maps[(int(bits[0]), int(bits[1]))] = Map(name)
        self.busy = set()                 # (global cells with a thing, an Id or a Lock on them)
        for (mx, my), m in self.maps.items():
            for ln in m.ents:
                p = ln.split("\t")
                try:
                    if p[0] in ("NPC", "StaticObject", "MapItem") and len(p) >= 4:
                        x, y = float(p[2]), float(p[3])
                        for tx in {int(x // TW), int((x + 24) // TW)}:
                            for ty in {int(y // TW), int((y + 30) // TW)}:
                                self.busy.add((mx * XT + tx, my * YT + ty))
                    elif p[0] in ("Id", "Lock") and len(p) >= 4:
                        self.busy.add((mx * XT + int(p[2]) - 1, my * YT + int(p[3]) - 1))
                except ValueError:
                    pass
        self.changed = set()

    def at(self, gx, gy):
        m = self.maps.get((gx // XT, gy // YT))
        return (m, gx % XT + 1, gy % YT + 1) if m else (None, 0, 0)

    def parts(self, gx, gy):
        m, x, y = self.at(gx, gy)
        return m.parts(x, y) if m else ("Water001", {})       # (no map: the open sea)

    def side(self, gx, gy, d):
        """What the cell beside gx,gy in direction d shows on the edge they share: "W" water, "L" land, "?"."""
        tile, _ = self.parts(gx + d[0], gy + d[1])
        dg = diagonal(tile)
        if dg:
            return "W" if (-d[0], -d[1]) in WET_EDGES[dg[1]] else "L"
        if tile.startswith(WATER):
            return "W"
        if tile.startswith(("Pond", "Lava", "Ice", "Black")):
            return "?"
        return "L"

    def family(self, gx, gy):
        tile, _ = self.parts(gx, gy)
        dg = diagonal(tile)
        if dg:
            return dg[0]
        return SHORE.get(tile)

    def free(self, gx, gy, tile):
        t, over = self.parts(gx, gy)
        m, _, _ = self.at(gx, gy)
        return (m is not None and t == tile and (gx, gy) not in self.busy and not over.get("Roof")
                and not over.get("Infront") and not over.get("Trigger")
                and (not over.get("Decor") or over["Decor"].startswith(SMALL)))

    def put(self, gx, gy, tile):
        m, x, y = self.at(gx, gy)
        keep = m.decor(x, y) if m.decor(x, y).startswith("Reeds") else ""     # (reeds grow in the shallows too)
        m.set(x, y, tile=tile, decor=keep)
        self.changed.add(m.name)

    def cells(self):
        for (mx, my) in self.maps:
            for y in range(YT):
                for x in range(XT):
                    yield mx * XT + x, my * YT + y


def corner(sides, want):
    """The pair of perpendicular directions showing want, if exactly those two do and the other two don't."""
    hits = [d for d in (N, E, S, W) if sides[d] == want]
    if len(hits) != 2 or any(sides[d] == "?" for d in (N, E, S, W)):
        return None
    a, b = hits
    if a[0] == -b[0] and a[1] == -b[1]:
        return None                                            # (opposite sides: a strip, not a corner)
    return (a, b) if (a, b) in WET_CORNER else (b, a)


def tidy(w):
    """Before the corners: a lone square of sand in the grass is grass; a one-square point of land with water on
    three sides is water; a one-square inlet with land on three sides is land. (Nothing can round those off.)"""
    n = 0
    for gx, gy in list(w.cells()):
        tile, _ = w.parts(gx, gy)
        if tile == "Sand001" and w.free(gx, gy, tile):
            near = [w.parts(gx + d[0], gy + d[1])[0] for d in (N, E, S, W)]
            if not any(t.startswith("Sand") for t in near) and sum(t == "Grass001" for t in near) >= 2:
                w.put(gx, gy, "Grass001")
                n += 1
                continue
        sides = [w.side(gx, gy, d) for d in (N, E, S, W)]
        if tile in LAND and w.free(gx, gy, tile) and sides.count("W") == 3:
            w.put(gx, gy, "Water001")
            n += 1
        elif tile == "Water001" and w.free(gx, gy, tile) and sides.count("L") == 3 and "?" not in sides:
            lands = [w.parts(gx + d[0], gy + d[1])[0] for d in (N, E, S, W)]
            lands = [t for t in lands if t in LAND]
            if len(lands) == 3:
                w.put(gx, gy, max(set(lands), key=lands.count))
                n += 1
    return n


def smooth(w, rng, only=None):
    cut = fill = 0
    for _ in range(3):
        if not tidy(w):
            break
    for _ in range(6):
        changes = 0
        for gx, gy in list(w.cells()):                         # land jutting out: cut its corner off
            if only and (gx, gy) not in only:
                continue
            tile, _ = w.parts(gx, gy)
            if tile not in LAND or not w.free(gx, gy, tile):
                continue
            wet = corner({d: w.side(gx, gy, d) for d in (N, E, S, W)}, "W")
            if wet:
                fam = LAND[tile]
                w.put(gx, gy, "%s%03d" % (fam, rng.choice(WET_CORNER[wet])))
                cut += 1
                changes += 1
        for gx, gy in list(w.cells()):                         # water reaching into the land: fill its corner
            if only and (gx, gy) not in only:
                continue
            if not w.free(gx, gy, "Water001"):
                continue
            sides = {d: w.side(gx, gy, d) for d in (N, E, S, W)}
            dry = corner(sides, "L")
            if not dry:
                continue
            (a, b) = dry
            fams = {w.family(gx + a[0], gy + a[1]), w.family(gx + b[0], gy + b[1])}
            diag, _ = w.parts(gx + a[0] + b[0], gy + a[1] + b[1])
            if None in fams or diagonal(diag) or diag.startswith(WATER):
                continue                                       # (a jetty, a wall: or not a real inside corner)
            wet = ((-a[0], -a[1]), (-b[0], -b[1]))
            wet = wet if wet in WET_CORNER else (wet[1], wet[0])
            fam = next(f for f in FAMILIES if f in fams)
            w.put(gx, gy, "%s%03d" % (fam, rng.choice(WET_CORNER[wet])))
            fill += 1
            changes += 1
        if not changes:
            break
    return cut, fill


# ---------------------------------------------------------------- marsh shores, and lily pads
def wet_pixel(c):
    return c[3] > 0 and c[2] > c[1] + 30


def make_marsh_shores():
    import pygame
    pygame.init()
    folder = os.path.join(ROOT, "sprites", "Tiles")
    marsh = pygame.image.load(os.path.join(folder, "Marsh001.png"))
    plain = pygame.image.load(os.path.join(folder, "Grass001.png"))
    colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
    lines = ini.read_text(colours).splitlines()
    for i in range(2, 10):
        name = "Marsh_Water%03d" % i
        grass = pygame.image.load(os.path.join(folder, "Water%03d.png" % i))
        out = grass.copy()
        for y in range(32):
            for x in range(32):
                c = grass.get_at((x, y))
                if not wet_pixel(c):
                    m = marsh.get_at((x, y))
                    g = plain.get_at((x, y))                            # (darker than the plain grass there:
                    shade = max(0.45, min(1.0, (sum(c[:3]) + 1) / (sum(g[:3]) + 1)))   # the bank's edge)
                    out.set_at((x, y), tuple(max(0, min(255, int(v * shade))) for v in m[:3]) + (255,))
        pygame.image.save(out, os.path.join(folder, name + ".png"))
        if not ini.section(name, TILES_INI):
            for k, v in ini.section("Water%03d" % i, TILES_INI):
                ini.write(name, k, v, TILES_INI)
            ini.write(name, "Examine.Info", "Still, brown water at the edge of the marsh.", TILES_INI)
        if not any(ln.startswith(name + "\t") for ln in lines):
            colour = next((ln.split("\t", 1)[1] for ln in lines if ln.startswith("Water%03d\t" % i)), "47 73 95")
            with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
                f.write("%s\t%s\n" % (name, colour.strip()))
    print("Made sprites\\Tiles\\Marsh_Water002-009")


def draw_lilies():
    import pygame
    pygame.init()
    folder = os.path.join(ROOT, "sprites", "Tiles")
    rng = random.Random(77)
    layouts = [[(10, 12, 6), (21, 20, 5)], [(9, 9, 5), (20, 13, 6), (12, 22, 4)], [(16, 16, 7)],
               [(8, 20, 4), (17, 9, 4), (24, 22, 3), (15, 18, 3)]]
    flowers = [None, (12, 22), (16, 16), None]
    for i, pads in enumerate(layouts):
        path = os.path.join(folder, "Lily_Pads%03d.png" % (i + 1))
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        for x, y, r in pads:
            col = rng.choice([(70, 140, 50), (62, 128, 46), (84, 150, 58)])
            pygame.draw.circle(s, (34, 70, 30), (x, y), r + 1)
            pygame.draw.circle(s, col, (x, y), r)
            pygame.draw.circle(s, tuple(min(255, c + 30) for c in col), (x - r // 3, y - r // 3), max(1, r // 3))
            ang = rng.choice([(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1)])     # (the notch)
            pygame.draw.polygon(s, (0, 0, 0, 0), [(x, y), (x + ang[0] * r + ang[1] * 2, y + ang[1] * r - ang[0] * 2),
                                                   (x + ang[0] * r - ang[1] * 2, y + ang[1] * r + ang[0] * 2)])
            pygame.draw.line(s, (34, 70, 30), (x, y), (x + ang[0] * (r - 1), y + ang[1] * (r - 1)))
        if flowers[i]:
            fx, fy = flowers[i]
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                pygame.draw.circle(s, (238, 160, 200), (fx + dx, fy + dy), 2)
            pygame.draw.circle(s, (250, 220, 90), (fx, fy), 1)
        pygame.image.save(s, path)
        name = "Lily_Pads%03d" % (i + 1)
        if not ini.section(name, TILES_INI):
            for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "0"), ("Use.Words", ""),
                         ("Examine.Info", "Lily pads, floating on the still water."), ("Line.of.Sight", "0"),
                         ("Layer", "Decor")):
                ini.write(name, k, v, TILES_INI)
        colours = os.path.join(ROOT, "dev", "Minimap Colours.txt")
        if name not in ini.read_text(colours):
            water = next((ln.split("\t", 1)[1] for ln in ini.read_text(colours).splitlines()
                          if ln.startswith("Water001\t")), "40 70 200")
            with open(colours, "a", encoding="cp1252", newline="\r\n") as f:
                f.write("%s\t%s\n" % (name, water.strip()))
    print("Drew sprites\\Tiles\\Lily_Pads001-004")


# ---------------------------------------------------------------- the Isle's pond, open water now
# W water; the banks' diagonals: a top-left, b top-right, c bottom-left, d bottom-right (no square corner anywhere)
POND = ["...aWWWb...",
        ".aWWWWWWWb.",
        "aWWWWWWWWWb",
        "WWWWWWWWWWW",
        "cWWWWWWWWWd",
        ".cWWWWWWWd.",
        "...cWWWd..."]
BANK = {"a": (S, E), "b": (S, W), "c": (N, E), "d": (N, W)}   # (which corner of the tile is water)
POND_NEAR = (11, 16)                                           # (on 2,1,0: as near here as there's room)


def pond(w, rng):
    m = w.maps[(2, 1)]
    for y in range(1, YT + 1):                                 # (the old pond: lily tiles, or a first try at this)
        for x in range(1, XT + 1):
            t, d = m.tile(x, y), m.decor(x, y)
            if t == "Pond001" or (t == "Water001" or diagonal(t)) and 4 <= x <= 19 and 11 <= y <= 21:
                m.set(x, y, tile="Grass001", decor="")
            elif d.startswith(("Reeds", "Lily_Pads")):
                m.set(x, y, decor="")
    h, wd = len(POND), len(POND[0])

    def cost(ox, oy):
        """How many trees and rocks it'd clear to go here (None: a path, a building, a creature in the way)."""
        n = 0
        for j in range(h):
            for i in range(wd):
                x, y = ox + i, oy + j
                if POND[j][i] == ".":
                    continue
                t, over = m.parts(x, y)
                if t != "Grass001" or over.get("Roof") or over.get("Trigger") or m.ent_near(x, y):
                    return None
                if over.get("Decor") and not m.open_ground(x, y):
                    n += 1
        return n
    cx, cy = POND_NEAR
    spots = [(c, (ox + wd / 2 - cx) ** 2 + (oy + h / 2 - cy) ** 2, ox, oy)
             for oy in range(2, YT - h) for ox in range(2, XT - wd) for c in [cost(ox, oy)] if c is not None]
    if not spots:
        print("No room for the pond on 2,1,0!")
        return []
    _, _, ox, oy = min(spots)
    water, banks = [], []
    for j in range(h):
        for i in range(wd):
            ch, x, y = POND[j][i], ox + i, oy + j
            if ch == "W":
                m.set(x, y, tile="Water001", decor="")
                water.append((x, y))
            elif ch in BANK:
                m.set(x, y, tile="Water%03d" % rng.choice(WET_CORNER[BANK[ch]]), decor="")
                banks.append((x, y))
    rng.shuffle(water)
    inner = [(x, y) for x, y in water if all(m.tile(x + dx, y + dy) == "Water001" for dx, dy in (N, E, S, W))]
    for k, (x, y) in enumerate(inner[:5]):
        m.set(x, y, decor="Lily_Pads%03d" % (k % 4 + 1))
    rng.shuffle(banks)
    for x, y in banks[:3]:
        m.set(x, y, decor="Reeds001")
    m.ents = [ln for ln in m.ents if not ln.startswith("Id\tIsle_Pond")]
    m.ents.append("Id\tIsle_Pond\t%d\t%d" % (ox + wd // 2, oy - 1))
    w.changed.add(m.name)
    print("The Isle's pond at 2,1,0 %d,%d: open water, diagonal banks, lilies and reeds" % (ox, oy))
    return water


def main():
    rng = random.Random(2026)
    make_marsh_shores()
    draw_lilies()
    w = World()
    pond(w, rng)
    cut, fill = smooth(w, rng)
    for (mx, my), m in w.maps.items():
        if m.name in w.changed:
            m.save()
    print("Coasts: %d corners cut, %d filled, on %d maps" % (cut, fill, len(w.changed)))


if __name__ == "__main__":
    main()
