"""Moving a part of a map: a rectangle of tiles - every layer of them - and everything standing on it, to another
spot on the same map or onto another map. What points at it follows: the quests' markers and the world map's labels
("map x y"), the scripts' teleports and queued actions (they name their map), and - moved within its own map - the
coordinates in that map's own scripts (its arrival script, its triggers', its named things'). What can't be followed
safely is listed to be looked at. Scripts tied to things by name (a trigger's script, Talk to <Id>, Examine
<place>) need nothing: the names go with them.

Rectangles are (x0, y0, x1, y1), tiles from 0, both ends in. An entity is in one if the tile it stands on is."""
import copy
import os
import re
from collections import Counter

from dragonsword import script_language as L

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
    """What was taken: the cells (every layer) and the entities, from a rectangle of a map."""

    def __init__(self, map_name, rect, cells, entities, cut):
        self.map, self.rect, self.cells, self.entities, self.cut = map_name, rect, cells, entities, cut

    @property
    def size(self):
        return self.rect[2] - self.rect[0] + 1, self.rect[3] - self.rect[1] + 1


def grab(doc, rect, ent_tile, cut):
    """The rectangle's cells and entities (copies), as a Region. ent_tile(e) -> (tile x, tile y) from 1."""
    x0, y0, x1, y1 = rect
    cells = [[copy.deepcopy(doc.cells[y][x]) for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    ents = [copy.deepcopy(e) for e in doc.placed() if inside(rect, ent_tile(e)[0] - 1, ent_tile(e)[1] - 1)]
    return Region(doc.name, rect, cells, ents, cut)


def ground_round(doc, rect):
    """The ground most of the tiles round the rectangle have (what a gap left by cutting is filled with)."""
    x0, y0, x1, y1 = rect
    h, w = len(doc.cells), len(doc.cells[0])
    seen = Counter()
    for y in range(y0 - 1, y1 + 2):
        for x in range(x0 - 1, x1 + 2):
            if 0 <= x < w and 0 <= y < h and not inside(rect, x, y):
                seen[doc.cells[y][x].tile] += 1
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


def put(doc, region, tx, ty, ent_shift, also_free=None):
    """region's cells laid down with their top-left on tile (tx, ty) (from 0) and its entities added, moved there.
    Roof groups the map already uses elsewhere are given free numbers (so the roofs don't join another house's).
    ent_shift(e, dtx, dty) moves an entity by whole tiles. Returns the entities added."""
    w, h = region.size
    target = (tx, ty, tx + w - 1, ty + h - 1)
    taken = roof_groups(doc, skip=target) - (also_free or set())
    mine = sorted({c.roof_group for row in region.cells for c in row if c.roof_group})
    free = (("%02d" % n) for n in range(1, 100) if "%02d" % n not in taken | set(mine))
    renumber = {g: (next(free) if g in taken else g) for g in mine}
    for j, row in enumerate(region.cells):
        for i, cell in enumerate(row):
            c = copy.deepcopy(cell)
            if c.roof_group:
                c.set_roof(c.roof, renumber[c.roof_group])
            doc.cells[ty + j][tx + i] = c
    dtx, dty = tx - region.rect[0], ty - region.rect[1]
    added = []
    for e in region.entities:
        e = copy.deepcopy(e)
        ent_shift(e, dtx, dty)
        doc.entities.append(e)
        added.append(e)
    return added


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
def _moved(src, rect, dst, dtx, dty, map_name, x, y, tiles):
    """(map, x, y) after the move, if map_name's (x, y) - tiles from 1, or pixels - was in the moved rectangle."""
    if map_name != src:
        return None
    tx, ty = (x - 1, y - 1) if tiles else (x // 32, y // 32)
    if not inside(rect, tx, ty):
        return None
    return dst, x + (dtx if tiles else dtx * 32), y + (dty if tiles else dty * 32)


def update_refs(project, src, rect, dst, dtx, dty, own_scripts):
    """Points at the moved rectangle made to point where it went. own_scripts: the source map's own scripts (its
    arrival script, its triggers' and its named things'): their bare coordinates follow if the move stays on that
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
                    m = _moved(src, rect, dst, dtx, dty, w[0], int(w[1]), int(w[2]), True)
                    if m:
                        parts[k] = "%s%s %d %d" % (part[:len(part) - len(part.lstrip())], m[0], m[1], m[2])
                        changed.append("%s: %s" % (label, key.strip()))
                        hit = True
            lines[i] = key + "=" + ";".join(parts)
        if hit:
            open(path, "wb").write(nl.join(lines).encode("cp1252"))

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
        mine = name in own_scripts
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
                        m = _moved(src, rect, dst, dtx, dty, f[mi + 1].strip(), int(xy.group(1)), int(xy.group(2)),
                                   False)
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
                m = _moved(src, rect, src, dtx, dty, src, x, y, tiles)
                if not m:
                    continue
                if mine and dst == src:
                    f[ai + 1] = "%d,%d" % (m[1], m[2])
                    lines[i] = "\t".join(f)
                    changed.append("%s line %s (%s)" % (name, f[0], cmd))
                    hit = True
                elif mine or ("\t%s\t" % src) in raw or ("\t%s%s" % (src, nl)) in raw:
                    check.append("%s line %s: %s %s" % (name, f[0], cmd, f[ai + 1]))
        if hit:
            open(path, "wb").write(nl.join(lines).encode("cp1252"))
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
