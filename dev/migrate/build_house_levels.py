"""Houses that show their levels, the owner's wish:

  * Rooms under and over the world have a south wall: a floor cell with nothing south of it gets the room's thin wall along
    that edge (house_tiles.THIN_EDGES), added to whatever walls it had already.
  * A cellar is one floor: stone right up to the walls, never planks by the wall and flags in the middle. So a flagstone floor
    has thin walls of its own, <Wall>_Thin_Flag001-018 (house_tiles.THIN_FLOORS), and a flagged room's thin pieces become them.
  * A building with an upstairs looks it from outside: its roof's lowest row becomes the upper storey's front
    (<Wall>_Upper001 and 002, in the roof's group, so they go when you're under it, as Edwin and Maren's house always did), and
    the row above takes the eave. Never a church's, or a roof too short to give a row.

Safe to run again: a room with its walls and a building with its upper storey are left alone.

  python -I "dev\\migrate\\build_house_levels.py"
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import house_tiles as H                         # noqa: E402
import decor_sets as D                          # noqa: E402
from common import p, write_sprite, Ini         # noqa: E402

THIN = re.compile(r"^(\w+?)_Thin_(Plank|Tile|Marble|Flag)(\d{3})$")
FLOORS = {"Plank001": "Plank", "Tile001": "Tile", "Marble001": "Marble", "Flagstone001": "Flag"}
LEVELS_OF_THEIR_OWN = {"0,0,10", "21,4,-10"}
ADD_SOUTH = {"": "S", "N": "NS", "E": "SE", "W": "SW", "NE": "NES", "NW": "NSW", "EW": "ESW"}   # (and with S, as they are)
ROOF = re.compile(r"Roof\(([^.)]+)\.([^)]+)\)")
ROOF_PIECE = re.compile(r"^(\w+)_Roof(\d{3})$")
WALLS = ("Brick", "Stone_Wall", "Timber", "Plaster", "Sandstone")
HOLY = ("Chapel", "Church", "Cathedral", "Abbey", "Temple")


def read(path):
    raw = open(path, "rb").read().decode("cp1252")
    return raw.split("\r\n")


def grid_lines(lines):
    """Which lines of a map file are its rows of cells (Tile:Tile:...)."""
    return [i for i, ln in enumerate(lines) if ln.count(":") >= 20 and "\t" not in ln]


def split_cell(c):
    k = c.find("+")
    return (c, "") if k < 0 else (c[:k], c[k:])


# ----- the tiles: thin walls round a flagstone floor
def draw_tiles():
    H.THIN_FLOORS.setdefault("Flagstone001", "Flag")
    ini = Ini(p("data", "Tiles.ini"))
    drawn = 0
    for wall in H.WALL_BASES:
        for k, edges in enumerate(H.THIN_EDGES):
            name = H.thin_name(wall, "Flagstone001", edges)
            mask = [[(0, 0, 0)] * 32 for _ in range(32)]
            drawn += write_sprite(p("sprites", "Tiles", name + ".png"), mask + H.thin_wall(wall, "Flagstone001", edges))
            for key, v in (("Walkable.Data", H.thin_walk(edges)), ("Show.Name", "0"), ("Use.Words", ""),
                           ("Line.of.Sight", "0"), ("Piece", D.THIN_WHAT[k])):
                if ini.get(name, key) != v:
                    ini.set(name, key, v)
    ini.save(p("data", "Tiles.ini"))
    path = p("data", "TileSets.ini")
    text = open(path, "rb").read().decode("cp1252")
    for name, title, cols, names in D.sets():
        if name.endswith("_Thin_Flag") and "[%s]" % name not in text:
            text = text.rstrip("\r\n") + "\r\n\r\n[%s]\r\nTitle=%s\r\nColumns=%d\r\nTiles=%s\r\nKind=Stretch\r\n" % (
                name, title, cols, ",".join(names))
    open(path, "wb").write(text.encode("cp1252"))
    return drawn


# ----- rooms
def room_of(rows, x0, y0, seen):
    h, w = len(rows), len(rows[0])
    out, todo = [], [(x0, y0)]
    seen.add((x0, y0))
    while todo:
        x, y = todo.pop()
        out.append((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= ny < h and 0 <= nx < len(rows[ny]) and (nx, ny) not in seen and is_floor(rows[ny][nx]):
                seen.add((nx, ny))
                todo.append((nx, ny))
    return out


def is_floor(c):
    t = split_cell(c)[0]
    return t in FLOORS or bool(THIN.match(t))


def fix_rooms(rows):
    """South walls and one floor, room by room. True if anything changed."""
    changed = False
    seen = set()
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if (x, y) in seen or not is_floor(c):
                continue
            room = room_of(rows, x, y, seen)
            plain, walls = collections.Counter(), collections.Counter()
            for cx, cy in room:
                t = split_cell(rows[cy][cx])[0]
                m = THIN.match(t)
                if m:
                    walls[m[1]] += 1
                elif t in FLOORS:
                    plain[FLOORS[t]] += 1
            if not walls:                               # (no thin wall in the room: its full walls say what it's made of)
                for cx, cy in room:
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]):
                            b = re.sub(r"\d+$", "", split_cell(rows[ny][nx])[0]).rstrip("_")
                            if b in WALLS:
                                walls[b] += 1
            if not walls:
                continue                                # (not a built room: a patch of paving in a cave)
            wall = walls.most_common(1)[0][0]
            floor = plain.most_common(1)[0][0] if plain else None
            for cx, cy in room:
                t, rest = split_cell(rows[cy][cx])
                m = THIN.match(t)
                new = t
                if m and floor == "Flag" and m[2] == "Plank":   # (flags right up to the walls)
                    new = "%s_Thin_Flag%s" % (m[1], m[3])
                    m = THIN.match(new)
                below = rows[cy + 1][cx] if cy + 1 < len(rows) and cx < len(rows[cy + 1]) else "Black001"
                if split_cell(below)[0] == "Black001":
                    edges = H.THIN_EDGES[int(m[3]) - 1] if m else ""
                    if "S" not in edges and not edges.startswith("+") and edges in ADD_SOUTH:
                        ground = m[2] if m else FLOORS[new]
                        new = "%s_Thin_%s%03d" % (m[1] if m else wall, ground, H.THIN_EDGES.index(ADD_SOUTH[edges]) + 1)
                if new != t:
                    rows[cy][cx] = new + rest
                    changed = True
    return changed


def do_rooms():
    done = 0
    for path in glob.glob(p("maps", "*.txt")):
        name = os.path.basename(path)[:-4]
        if name.endswith(",0") or name in LEVELS_OF_THEIR_OWN:
            continue
        lines = read(path)
        at = grid_lines(lines)
        rows = [lines[i].split(":") for i in at]
        if rows and fix_rooms(rows):
            for i, r in zip(at, rows):
                lines[i] = ":".join(r)
            open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
            done += 1
    return done


# ----- upper storeys, seen from outside
def wall_of(cell):
    t = split_cell(cell)[0]
    for w in WALLS:
        if t.startswith(w):
            return w
    return None


def upper_front(rows, group):
    """The building of that roof group: its upper storey's front. True if it was given one."""
    cols = collections.defaultdict(list)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            m = ROOF.search(c)
            if m and m[2] == group:
                if "_Upper" in m[1] or any(h in c for h in HOLY):
                    return False
                cols[x].append(y)
    if not cols:
        return False
    fronts = collections.Counter()
    for x, ys in cols.items():
        y = max(ys)
        if y + 1 < len(rows) and x < len(rows[y + 1]):
            w = wall_of(rows[y + 1][x])
            if w:
                fronts[w] += 1
    if not fronts or fronts.most_common(1)[0][1] * 2 < len(cols):    # (no front wall along it: not a house's roof)
        return False
    wall = fronts.most_common(1)[0][0]
    if any(max(ys) - min(ys) < 2 for ys in cols.values()):           # (too short to give a row)
        return False
    for x, ys in cols.items():
        y = max(ys)
        low = ROOF.search(rows[y][x])
        above = ROOF.search(rows[y - 1][x]) if y - 1 in ys else None
        if above is None:
            return False
        a = ROOF_PIECE.match(above[1])
        if not a or not ROOF_PIECE.match(low[1]):
            return False
    for x, ys in cols.items():
        y = max(ys)
        low = ROOF.search(rows[y][x])
        above = ROOF.search(rows[y - 1][x])
        mat, n = ROOF_PIECE.match(above[1]).groups()
        n = int(n)
        col = (n - 1) % 3 if n <= 30 else 1
        rows[y - 1][x] = ROOF.sub("Roof(%s_Roof%03d.%s)" % (mat, 13 + col, group), rows[y - 1][x])
        rows[y][x] = ROOF.sub("Roof(%s_Upper%03d.%s)" % (wall, 1 + x % 2, group), rows[y][x])
    return True


def do_uppers():
    done = 0
    for path in glob.glob(p("maps", "*,1.txt")):
        name = os.path.basename(path)[:-4]
        mx, my, _ = name.split(",")
        ground = p("maps", "%s,%s,0.txt" % (mx, my))
        if not os.path.exists(ground):
            continue
        upstairs = [ln.split(":") for ln in (read(path)[i] for i in grid_lines(read(path)))]
        lines = read(ground)
        at = grid_lines(lines)
        rows = [lines[i].split(":") for i in at]
        groups = set()
        for y, row in enumerate(upstairs):
            for x, c in enumerate(row):
                if split_cell(c)[0] != "Black001" and y < len(rows) and x < len(rows[y]):
                    m = ROOF.search(rows[y][x])
                    if m:
                        groups.add(m[2])
        changed = False
        for g in sorted(groups):
            if upper_front(rows, g):
                changed = True
                done += 1
        if changed:
            for i, r in zip(at, rows):
                lines[i] = ":".join(r)
            open(ground, "wb").write("\r\n".join(lines).encode("cp1252"))
    return done


def main():
    print("Thin flagstone walls: %d drawn" % draw_tiles())
    print("Rooms' maps changed: %d" % do_rooms())
    print("Buildings given an upper storey's front: %d" % do_uppers())


if __name__ == "__main__":
    main()
