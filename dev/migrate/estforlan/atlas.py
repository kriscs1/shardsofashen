"""The overworld's maps as one grid of world tiles (gx = map x * 25 + tile x - 1, gy = map y * 21 + tile y - 1), each
map a build_isle.Map underneath; what stands on them (map lines) kept per map; and the noise everything is drawn from."""
import math
import os
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import story_kit as K  # noqa: E402
from story_kit import Map, XT, YT, TW  # noqa: E402

ROOT = K.ROOT
OPEN = ("Grass001", "Dirt001", "Sand001", "Snow001", "Ash001", "Cinder001", "Marsh001", "Scorched001", "Scorched002",
        "Scorched003")
SMALL = ("Flowers", "Pebbles", "Tall_Grass", "Grass_Tuft", "Clover", "Daisies", "Weeds")


# ------------------------------------------------------------------ noise (the same every run)
def h01(*parts):
    return (zlib.crc32(":".join(str(v) for v in parts).encode()) % 100000) / 100000.0


def vnoise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = h01(seed, ix, iy), h01(seed, ix + 1, iy)
    c, d = h01(seed, ix, iy + 1), h01(seed, ix + 1, iy + 1)
    top = a + (b - a) * sx
    return top + ((c + (d - c) * sx) - top) * sy


def fbm(x, y, scale, seed):
    return (0.55 * vnoise(x / scale, y / scale, seed) + 0.3 * vnoise(x / (scale * 0.47), y / (scale * 0.47), seed + 99)
            + 0.15 * vnoise(x / (scale * 0.2), y / (scale * 0.2), seed + 199))


def map_name(mx, my, z=0):
    return "%d,%d,%d" % (mx, my, z)


def map_xy(name):
    p = name.split(",")
    return int(p[0]), int(p[1])


# ------------------------------------------------------------------ the atlas
class Atlas:
    def __init__(self, names):
        self.maps = {n: Map(n, new=True) for n in names}
        self.taken = set()          # world cells something stands on (a building, a lifted place, a square...)
        self.roads = set()          # world cells that are a road or a street
        self.no_build = set()       # world cells kept clear (the ways in to lifted places, docks...)

    # ---- where things are
    def at(self, gx, gy):
        """(map, tile x, tile y) of world cell gx,gy (tiles 1-based), or (None, 0, 0)."""
        mx, my = gx // XT, gy // YT
        m = self.maps.get(map_name(mx, my))
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

    def put(self, gx, gy, text):
        """The whole cell, as a map file writes it (Tile+Decor(...)...)."""
        m, x, y = self.at(gx, gy)
        if m is not None:
            m.rows[y - 1][x - 1] = text

    def set(self, gx, gy, tile=None, decor=None, roof=None):
        m, x, y = self.at(gx, gy)
        if m is not None:
            m.set(x, y, tile=tile, decor=decor, roof=roof)

    def line(self, gx, gy, kind, name, extra="", dy=0, dx=0):
        """A thing standing on world cell gx,gy (its map line: NPC / StaticObject / MapItem)."""
        m, x, y = self.at(gx, gy)
        if m is None:
            return None
        ln = "%s\t%s\t%d\t%d" % (kind, name, (x - 1) * TW + dx, (y - 1) * TW + dy)
        if extra:
            ln += "\t" + extra
        m.ents.append(ln)
        return m

    def place_id(self, gx, gy, pid):
        m, x, y = self.at(gx, gy)
        if m is not None:
            K.place_id(m, pid, x, y)
        return m

    def zone(self, gx1, gy1, gx2, gy2, gx=None, gy=None):
        """A Zone=/Chase= box in the local tiles of the map of (gx, gy) (default: of its first corner), clipped to it."""
        m, _, _ = self.at(gx1 if gx is None else gx, gy1 if gy is None else gy)
        mx, my = map_xy(m.name)
        x1, y1 = max(1, gx1 - mx * XT + 1), max(1, gy1 - my * YT + 1)
        x2, y2 = min(XT, gx2 - mx * XT + 1), min(YT, gy2 - my * YT + 1)
        return "%d,%d,%d,%d" % (x1, y1, x2, y2)

    # ---- (towns.py's Ground, for its furnish and cart_stops)
    @staticmethod
    def mxy(name):
        return map_xy(name)

    def road(self, gx, gy):
        return (gx, gy) in self.roads

    def free(self, gx, gy):
        """Open ground, nothing on it, nothing built there."""
        if (gx, gy) in self.taken or (gx, gy) in self.roads or not self.inside(gx, gy):
            return False
        cell = self.cell(gx, gy)
        return cell.split("+")[0] in OPEN and "Roof(" not in cell and (
            not self.decor(gx, gy) or self.decor(gx, gy).startswith(SMALL))

    def same_map(self, cells):
        names = {self.at(x, y)[0].name if self.at(x, y)[0] else None for x, y in cells}
        return len(names) == 1 and None not in names

    def save(self):
        for m in self.maps.values():
            m.save()
