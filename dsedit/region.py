"""Moving a part of a map: a rectangle of tiles - every layer of them - and everything standing on it, to another
spot on the same map or onto another map. What points at it follows: the quests' markers and the world map's labels
("map x y"), the scripts' teleports and queued actions (they name their map), and - moved within its own map - the
coordinates in that map's own scripts (its arrival script, its triggers', its named things'). What can't be followed
safely is listed to be looked at. Scripts tied to things by name (a trigger's script, Talk to <Id>, Examine
<place>) need nothing: the names go with them.

Rectangles are (x0, y0, x1, y1), tiles from 0, both ends in. An entity is in one if the tile it stands on is. One may
run off its map onto those round it: "parts" are the maps it lies on, [(map, dx, dy, the part of the rectangle on it)],
dx, dy where that map's top-left tile is, counted from the first map's."""
import copy
import os
import re
from collections import Counter

from ashen import script_language as L

from .project import write_whole

TILE_KINDS = ("Trigger", "Lock", "Id")
LAYER_PARTS = ("Under", "Decor", "Roof", "Infront")
# script arguments that are coordinates: (command, argument number from 1, in tiles?)
COORD_ARGS = []
for _name, _args in L.COMMANDS:
    for _i, _t in enumerate(_args, 1):
        if _t in ("X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y", "REQUIRED TILE COORDINATES",
                  "DISALLOWED TILE COORDINATES"):
            COORD_ARGS.append((_name, _i, "TILE" in _t or _name in ("Change.Tile", ">Tile.In.Line.Of.Sight")))
MAPPED = {"Teleport": (1, 2), "Add.Action.To.Queue": (6, 5)}   # command: (its coordinates' arg, its map's arg)
NUM_XY = re.compile(r"^\s*(-?\d+)\s*,\s*(-?\d+)\s*$")


def inside(rect, x, y):
    x0, y0, x1, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


class Region:
    """What was taken: the cells (every layer; None where there's no map) and the entities, from a rectangle counted
    from map_name's top-left. Entities are moved as if they stood on map_name, whichever map they were on."""

    def __init__(self, map_name, rect, cells, entities, cut):
        self.map, self.rect, self.cells, self.entities, self.cut = map_name, rect, cells, entities, cut

    @property
    def size(self):
        return self.rect[2] - self.rect[0] + 1, self.rect[3] - self.rect[1] + 1


def grab(parts, map_name, rect, ent_tile, ent_shift, cut):
    """The rectangle's cells and entities (copies), as a Region. ent_tile(e) -> (tile x, tile y) from 1; ent_shift(e,
    dtx, dty) moves an entity by whole tiles. Two maps may each have a roof group 01: they're different roofs, so the
    second is given a number of its own."""
    x0, y0, x1, y1 = rect
    cells = [[None] * (x1 - x0 + 1) for _ in range(y1 - y0 + 1)]
    ents, groups = [], {}
    for doc, dx, dy, part in parts:
        for y in range(part[1], part[3] + 1):
            for x in range(part[0], part[2] + 1):
                c = copy.deepcopy(doc.cells[y][x])
                if c.roof_group:
                    key = (doc.name, c.roof_group)
                    if key not in groups:
                        used = set(groups.values())
                        groups[key] = c.roof_group if c.roof_group not in used else next(
                            g for g in ("%02d" % n for n in range(1, 100)) if g not in used)
                    c.set_roof(c.roof, groups[key])
                cells[y + dy - y0][x + dx - x0] = c
        for e in doc.placed():
            if inside(part, ent_tile(e)[0] - 1, ent_tile(e)[1] - 1):
                e = copy.deepcopy(e)
                ent_shift(e, dx, dy)
                ents.append(e)
    return Region(map_name, rect, cells, ents, cut)


def ground_round(tile_at, rect):
    """The ground most of the tiles round the rectangle have (what a gap left by cutting is filled with). tile_at(x, y):
    the tile there, None where there's no map."""
    x0, y0, x1, y1 = rect
    seen = Counter()
    for x in range(x0 - 1, x1 + 2):
        seen.update(tile_at(x, y) for y in (y0 - 1, y1 + 1))
    for y in range(y0, y1 + 1):
        seen.update(tile_at(x, y) for x in (x0 - 1, x1 + 1))
    del seen[None]
    return seen.most_common(1)[0][0] if seen else "Grass001"


def clear(doc, rect, fill):
    """The rectangle emptied: its ground fill, nothing over it."""
    x0, y0, x1, y1 = rect
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = doc.cells[y][x]
            c.tile = fill
            for k in LAYER_PARTS:
                c._set(k, None)


def roof_groups(doc, skip=None):
    """The roof groups used on a map ({"01", ...}), not counting the cells in skip (a rectangle)."""
    out = set()
    for y, row in enumerate(doc.cells):
        for x, c in enumerate(row):
            if c.roof_group and not (skip and inside(skip, x, y)):
                out.add(c.roof_group)
    return out


def put(at, region, tx, ty, ent_tile, ent_shift):
    """region's cells laid down with their top-left on tile (tx, ty) and its entities added, moved there, each on the
    map it lands on. at(x, y) -> (map, x on it, y on it), None where there's no map. Roof groups a map already uses
    elsewhere are given free numbers (so the roofs don't join another house's), map by map. Returns the entities
    added."""
    landed = {}
    for j, row in enumerate(region.cells):
        for i, cell in enumerate(row):
            a = at(tx + i, ty + j) if cell is not None else None
            if a is not None:
                landed.setdefault(id(a[0]), (a[0], []))[1].append((a[1], a[2], cell))
    for doc, cells in landed.values():
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        taken = roof_groups(doc, skip=(min(xs), min(ys), max(xs), max(ys)))
        mine = sorted({c[2].roof_group for c in cells if c[2].roof_group})
        free = (("%02d" % n) for n in range(1, 100) if "%02d" % n not in taken | set(mine))
        renumber = {g: (next(free) if g in taken else g) for g in mine}
        for x, y, cell in cells:
            c = copy.deepcopy(cell)
            if c.roof_group:
                c.set_roof(c.roof, renumber[c.roof_group])
            doc.cells[y][x] = c
    dtx, dty = tx - region.rect[0], ty - region.rect[1]
    added = []
    for e in region.entities:
        e = copy.deepcopy(e)
        ent_shift(e, dtx, dty)
        fx, fy = ent_tile(e)
        a = at(fx - 1, fy - 1)
        if a is None:
            continue
        ent_shift(e, a[1] - (fx - 1), a[2] - (fy - 1))
        a[0].entities.append(e)
        added.append(e)
    return added


def moves(parts, rect, dest_parts, tx, ty):
    """What a rectangle (its parts) moved to (tx, ty) (dest_parts, the maps it lands on) comes to, map to map: [(map, the
    rectangle on it, the map it went to, dtx, dty)]. The tiles of one source part can land on several maps."""
    out = []
    sx, sy = tx - rect[0], ty - rect[1]
    for doc, dx, dy, part in parts:
        for dest, ddx, ddy, there in dest_parts:
            x0, y0 = max(part[0] + dx + sx, there[0] + ddx), max(part[1] + dy + sy, there[1] + ddy)
            x1, y1 = min(part[2] + dx + sx, there[2] + ddx), min(part[3] + dy + sy, there[3] + ddy)
            if x0 <= x1 and y0 <= y1:
                out.append((doc.name, (x0 - sx - dx, y0 - sy - dy, x1 - sx - dx, y1 - sy - dy), dest.name,
                            dx + sx - ddx, dy + sy - ddy))
    return out


def strip_names(ents):
    """A copy can't keep what must be unique in the world: its Ids and its place names (dropped)."""
    out = []
    for e in ents:
        if e.kind == "Id":
            continue
        if e.opt("Id"):
            e.set_opt("Id", "")
        out.append(e)
    return out


# ---------------------------------------------------------------------------------------------------------------
# What points at the moved tiles
# ---------------------------------------------------------------------------------------------------------------
def _moved(all_moves, map_name, x, y, tiles):
    """(map, x, y) after the move, if map_name's (x, y) - tiles from 1, or pixels - was in a moved rectangle (only ever
    one: where a thing went isn't looked up again)."""
    tx, ty = (x - 1, y - 1) if tiles else (x // 32, y // 32)
    for src, rect, dst, dtx, dty in all_moves:
        if map_name == src and inside(rect, tx, ty):
            return dst, x + (dtx if tiles else dtx * 32), y + (dty if tiles else dty * 32)
    return None


def update_refs(project, all_moves, own_scripts):
    """Points at the moved rectangles (moves()) made to point where they went. own_scripts: {map: its own scripts (its
    arrival script, its triggers' and its named things')}: their bare coordinates follow if the move stays on that
    map, and are listed to look at if it doesn't. Returns (changed: [text], to_check: [text])."""
    changed, check = [], []

    def fix_markers(path, label):
        if not os.path.exists(path):
            return
        raw = open(path, "rb").read().decode("cp1252")
        nl = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(nl)
        hit = False
        for i, ln in enumerate(lines):
            if "=" not in ln or ln.lstrip().startswith(";"):
                continue
            key, val = ln.split("=", 1)
            parts = val.split(";")
            for k, part in enumerate(parts):
                w = part.split()
                if len(w) == 3 and re.fullmatch(r"-?\d+,-?\d+,-?\d+", w[0]) and w[1].isdigit() and w[2].isdigit():
                    m = _moved(all_moves, w[0], int(w[1]), int(w[2]), True)
                    if m:
                        parts[k] = "%s%s %d %d" % (part[:len(part) - len(part.lstrip())], m[0], m[1], m[2])
                        changed.append("%s: %s" % (label, key.strip()))
                        hit = True
            lines[i] = key + "=" + ";".join(parts)
        if hit:
            write_whole(path, nl.join(lines).encode("cp1252"))

    fix_markers(project.p("data", "Quests.ini"), "Quests.ini")
    fix_markers(project.p("data", "WorldMap.ini"), "WorldMap.ini")
    folder = project.p("data", "Scripts")
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".txt"):
            continue
        name = fname[:-4]
        path = os.path.join(folder, fname)
        raw = open(path, "rb").read().decode("cp1252")
        nl = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.split(nl)
        hit = False
        for i, ln in enumerate(lines):
            f = ln.split("\t")
            if len(f) < 2 or not f[0].strip().isdigit():
                continue
            cmd = f[1]
            if cmd in MAPPED:                                  # (names its map: followed wherever it went)
                ci, mi = MAPPED[cmd]
                if len(f) > max(ci, mi) + 1:
                    xy = NUM_XY.match(f[ci + 1])
                    if xy:
                        m = _moved(all_moves, f[mi + 1].strip(), int(xy.group(1)), int(xy.group(2)), False)
                        if m:
                            f[mi + 1], f[ci + 1] = m[0], "%d,%d" % (m[1], m[2])
                            lines[i] = "\t".join(f)
                            changed.append("%s line %s (%s)" % (name, f[0], cmd))
                            hit = True
                continue
            for c, ai, tiles in COORD_ARGS:                    # (bare coordinates: on whatever map it runs on)
                if c != cmd or len(f) <= ai + 1:
                    continue
                xy = NUM_XY.match(f[ai + 1])
                if not xy:
                    continue
                x, y = int(xy.group(1)), int(xy.group(2))
                for src in own_scripts:                        # (on the first map that could be it)
                    mine = name in own_scripts[src]
                    if not mine and ("\t%s\t" % src) not in raw and ("\t%s%s" % (src, nl)) not in raw:
                        continue
                    m = _moved(all_moves, src, x, y, tiles)
                    if not m:
                        continue
                    if mine and m[0] == src:
                        f[ai + 1] = "%d,%d" % (m[1], m[2])
                        lines[i] = "\t".join(f)
                        changed.append("%s line %s (%s)" % (name, f[0], cmd))
                        hit = True
                    else:
                        check.append("%s line %s: %s %s" % (name, f[0], cmd, f[ai + 1]))
                    break
        if hit:
            write_whole(path, nl.join(lines).encode("cp1252"))
    return changed, check


def own_scripts(project, doc):
    """The scripts that run on this map: its arrival script, its triggers', and those of its named things
    (<Verb> <Id>, <Verb> <place>)."""
    names = {doc.name}
    ids = set()
    for e in doc.placed():
        if e.kind == "Trigger" and e.script:
            names.add(e.script.strip())
        elif e.kind == "Id":
            ids.add(e.name)
        elif e.opt("Id"):
            ids.add(e.opt("Id"))
    for s in project.scripts():
        if " " in s and s.rsplit(" ", 1)[1] in ids:
            names.add(s)
    return names
