"""Validate the Shards of Ashen data files against dev\\Data Formats.md, including data\\Gathering.ini and
data\\Quests.ini (read by the in-game Help screen) and whether every shop/craft list is opened by a script.

Run:  python -I "dev\\migrate\\validate.py"  [--quiet]
Exit code 0 = no errors (warnings allowed), 1 = errors.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (MAP_W, MAP_H, Ini, p, read_lines, sprite_names, script_commands,
                    script_command_arg_types, script_variables, SPEC_VARIABLES)

ERRORS, WARNINGS = [], []


def err(where, msg):
    ERRORS.append("%s: %s" % (where, msg))


def warn(where, msg):
    WARNINGS.append("%s: %s" % (where, msg))


TILES = set(sprite_names("Tiles"))
ENTITIES = set(sprite_names("Entities"))
NON_PLACEABLE = {"Trigger", "Placeholder"} | {e for e in ENTITIES if e.startswith("Player")}
SOUNDS = set()
if os.path.isdir(p("sounds")):
    SOUNDS = {os.path.splitext(f)[0] for f in os.listdir(p("sounds"))}
SCRIPT_DIR = p("data", "Scripts")
SCRIPTS = {f[:-4] for f in os.listdir(SCRIPT_DIR) if f.lower().endswith(".txt")}


def script_nonempty(name):
    path = os.path.join(SCRIPT_DIR, name + ".txt")
    return os.path.exists(path) and any(l.strip() for l in read_lines(path))


def rel(path):
    return os.path.relpath(path, p())


# ------------------------------------------------------------------ raw file checks
def check_raw(path):
    with open(path, "rb") as f:
        b = f.read()
    r = rel(path)
    if b.startswith(b"\xef\xbb\xbf"):
        err(r, "has a UTF-8 BOM (GetPrivateProfileString/LB won't read the first line correctly)")
    if any(c > 127 for c in b):
        warn(r, "contains non-ASCII bytes")
    if re.search(rb"(?<!\r)\n", b) or re.search(rb"\r(?!\n)", b):
        err(r, "has non-CRLF line endings")


# ------------------------------------------------------------------ ini helpers
def check_ini_syntax(path):
    """Duplicate sections/keys and value length (Read.From.Ini$ uses a 100-byte buffer)."""
    r = rel(path)
    seen_sec = {}
    cur = None
    keys = set()
    for n, line in enumerate(read_lines(path), 1):
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("["):
            if not s.endswith("]"):
                err(r, "line %d: bad section header %r" % (n, s))
                continue
            name = s[1:-1].lower()
            if name in seen_sec:
                err(r, "duplicate section [%s] (lines %d and %d)" % (s[1:-1], seen_sec[name], n))
            seen_sec[name] = n
            cur, keys = name, set()
            continue
        if "=" not in s:
            warn(r, "line %d: not a key=value line: %r" % (n, s))
            continue
        k, v = s.split("=", 1)
        k = k.strip().lower()
        if cur is None:
            err(r, "line %d: key outside any section" % n)
        if k in keys:
            err(r, "line %d: duplicate key %s in [%s]" % (n, k, cur))
        keys.add(k)
        if len(v.strip()) > 2047 and not r.lower().startswith("saves"):     # (the editor's limit; it never opens saves)
            warn(r, "line %d: value is %d chars; Read.From.Ini$ only returns 2047 (the editor reads ini values into a 2048 byte buffer)" % (n, len(v.strip())))


def is_num(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ maps
CELL_RE = re.compile(r"^([A-Za-z0-9_()]+)((?:\+[A-Za-z]+\([^()]*\))*)$")
OVERLAY_RE = re.compile(r"\+([A-Za-z]+)\(([^()]*)\)")
def name_of(f):
    return f[1].strip() if len(f) > 1 else ""


ENTITY_FIELDS = {"MapItem": 5, "StaticObject": 4, "NPC": 4, "GoodNPC": 4, "BadNPC": 4, "Trigger": 4, "Lock": 5, "Id": 4}
PLACE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
NPC_TYPES = ("NPC", "GoodNPC", "BadNPC")         # GoodNPC / BadNPC: the old types (an NPC with that attitude)
LOCKS = []          # (map name, tile x, tile y, condition, message, where) from every map's Lock lines


SEE_THROUGH = None


def see_through_tiles():
    """Tiles whose mask has see-through (white) pixels: they only work as overlays (the ground is painted solid)."""
    global SEE_THROUGH
    if SEE_THROUGH is None:
        from PIL import Image
        SEE_THROUGH = set()
        for t in TILES:
            im = Image.open(p("sprites", "Tiles", t + ".png"))
            if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 128:
                SEE_THROUGH.add(t)
    return SEE_THROUGH


def check_map(path, entities_ini, tiles_ini, report):
    check_raw(path)
    r = rel(path)
    lines = read_lines(path)
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) < MAP_H:
        report(r, "only %d lines; need %d tile rows" % (len(lines), MAP_H))
        return
    for y in range(MAP_H):
        cells = lines[y].split(":")
        if len(cells) != MAP_W:
            report(r, "row %d has %d columns (need %d)" % (y + 1, len(cells), MAP_W))
        for x, cell in enumerate(cells, 1):
            m = CELL_RE.match(cell)
            if not m:
                report(r, "row %d col %d: bad cell %r" % (y + 1, x, cell))
                continue
            tile = m.group(1)
            if tile not in TILES:
                report(r, "row %d col %d: tile %r has no sprite" % (y + 1, x, tile))
            elif (tiles_ini.get(tile, "Layer", "") or "").lower() == "decor":
                report(r, "row %d col %d: %s is a decor tile (Layer=Decor), not a ground tile: put it over one "
                          "(e.g. Plank001+Decor(%s))" % (y + 1, x, tile, tile))
            elif tile in see_through_tiles():
                report(r, "row %d col %d: %s has see-through parts, so as the cell's own tile it shows black there: "
                          "put it over another tile (e.g. Grass001+Infront(%s))" % (y + 1, x, tile, tile))
            elif tiles_ini.section(tile) is None:
                warn(r, "tile %r has no [section] in Tiles.ini" % tile)
            for kind, arg in OVERLAY_RE.findall(m.group(2)):
                if kind == "Roof":
                    rm = re.match(r"^([A-Za-z0-9_]+)\.(\d+)$", arg)
                    if not rm:
                        report(r, "row %d col %d: bad roof overlay %r (want Name.Group)" % (y + 1, x, arg))
                    elif rm.group(1) not in TILES:
                        report(r, "row %d col %d: roof tile %r has no sprite" % (y + 1, x, rm.group(1)))
                elif kind == "Infront":
                    if arg not in TILES:
                        report(r, "row %d col %d: infront tile %r has no sprite" % (y + 1, x, arg))
                elif kind == "Under":
                    if arg not in TILES:
                        report(r, "row %d col %d: rug tile %r has no sprite" % (y + 1, x, arg))
                    elif (tiles_ini.get(arg, "Layer", "") or "").lower() != "under":
                        warn(r, "row %d col %d: +Under(%s) has no Layer=Under in Tiles.ini" % (y + 1, x, arg))
                elif kind == "Decor":
                    if arg not in TILES:
                        report(r, "row %d col %d: decor tile %r has no sprite" % (y + 1, x, arg))
                    elif (tiles_ini.get(arg, "Layer", "") or "").lower() != "decor":
                        warn(r, "row %d col %d: +Decor(%s) has no Layer=Decor in Tiles.ini" % (y + 1, x, arg))
                else:
                    report(r, "row %d col %d: unknown overlay +%s(%s)" % (y + 1, x, kind, arg))
            if re.search(r"\+[A-Za-z]+(?!\()", cell) and not m.group(2):
                report(r, "row %d col %d: overlay without (arg) in %r" % (y + 1, x, cell))
    for n, line in enumerate(lines[MAP_H:], MAP_H + 1):
        if line.strip() == "":
            continue
        f = line.split("\t")
        typ = f[0]
        if typ not in ENTITY_FIELDS:
            report(r, "line %d: unknown entity type %r" % (n, typ))
            continue
        if typ == "Lock":
            # Lock<TAB>TileX<TAB>TileY<TAB>Condition<TAB>Message (the message may be left out: "It's locked.")
            if len(f) not in (4, 5):
                report(r, "line %d: Lock needs TileX, TileY, Condition and Message (tab-separated), has %d fields" % (n, len(f)))
                continue
            xs, ys = f[1], f[2]
            if not (xs.isdigit() and ys.isdigit() and 1 <= int(xs) <= MAP_W and 1 <= int(ys) <= MAP_H):
                report(r, "line %d: lock tile %s,%s is not a whole tile in 1..%d,1..%d" % (n, xs, ys, MAP_W, MAP_H))
                continue
            if os.path.dirname(os.path.abspath(path)) == os.path.abspath(p("maps")):
                LOCKS.append((os.path.splitext(os.path.basename(path))[0], int(xs), int(ys), f[3],
                              f[4] if len(f) > 4 else "", "%s line %d" % (r, n)))
            row = lines[int(ys) - 1].split(":")
            tile = ground_key(row[int(xs) - 1]) if len(row) >= int(xs) else ""
            if tile and tile_walk(tiles_ini, tile)[24] != "1":
                report(r, "line %d: lock tile %s,%s is %s, which isn't walkable even when unlocked (use a door or a floor)"
                       % (n, xs, ys, tile))
            if not f[3].strip():
                warn(r, "line %d: lock at %s,%s has an empty condition, so it is locked for ever" % (n, xs, ys))
            if ";" in "\t".join(f[3:]):
                warn(r, "line %d: ';' in a lock condition or message" % n)
            continue
        if typ == "Id":
            # Id<TAB>Name<TAB>TileX<TAB>TileY: a named tile, for scripts and quests (build_places.py)
            if len(f) != 4:
                report(r, "line %d: Id needs Name, TileX and TileY (tab-separated), has %d fields" % (n, len(f)))
            elif not PLACE_RE.match(f[1]):
                report(r, "line %d: place ID %r must be a letter, then letters, digits, _ . or -" % (n, f[1]))
            elif not (f[2].isdigit() and f[3].isdigit() and 1 <= int(f[2]) <= MAP_W and 1 <= int(f[3]) <= MAP_H):
                report(r, "line %d: place %s's tile %s,%s is not in 1..%d,1..%d" % (n, f[1], f[2], f[3], MAP_W, MAP_H))
            continue
        if typ in ("GoodNPC", "BadNPC"):
            warn(r, "line %d: %s is the old type: write NPC with Attitude=%s in its Options"
                 % (n, typ, "Good" if typ == "GoodNPC" else "Bad"))
        if typ in NPC_TYPES and len(f) == 5:
            pass                         # Name, X, Y and the Options (attitude and movement)
        elif typ == "MapItem" and len(f) == 6:           # Name, X, Y, Quantity and its Options (Id=)
            bad = [w for w in f[5].split() if "=" not in w]
            if bad:
                warn(r, "line %d: MapItem options should be Key=Value: %s" % (n, " ".join(bad)))
        elif typ == "StaticObject" and len(f) == 5:      # Name, X, Y and its Options (Id=, for a notice's script)
            bad = [w for w in f[4].split() if "=" not in w]
            if bad:
                warn(r, "line %d: StaticObject options should be Key=Value: %s" % (n, " ".join(bad)))
            oid = next((w[3:] for w in f[4].split() if w.startswith("Id=")), "")
            if oid and name_of(f) == "Notice" and not script_nonempty("Read " + oid):
                report(r, "line %d: notice Id=%s has no script data\\Scripts\\Read %s.txt" % (n, oid, oid))
        elif len(f) != ENTITY_FIELDS[typ]:
            report(r, "line %d: %s needs %d tab-separated fields%s, has %d"
                   % (n, typ, ENTITY_FIELDS[typ], " (plus Options)" if typ in NPC_TYPES else "", len(f)))
        name = f[1] if len(f) > 1 else ""
        xs, ys = (f[2] if len(f) > 2 else ""), (f[3] if len(f) > 3 else "")
        if not (is_num(xs) and is_num(ys)):
            report(r, "line %d: non-numeric coordinates" % n)
            continue
        x, y = float(xs), float(ys)
        if typ == "Trigger":
            if not (1 <= x <= MAP_W and 1 <= y <= MAP_H and x == int(x) and y == int(y)):
                report(r, "line %d: trigger tile %s,%s outside 1..%d,1..%d" % (n, xs, ys, MAP_W, MAP_H))
            if name.startswith("Trap_"):            # (a trap, not a script: deep.py world_trap)
                if name[5:] not in TRAP_KINDS:
                    report(r, "line %d: no trap kind %s (%s)" % (n, name[5:], ", ".join(TRAP_KINDS)))
            elif not script_nonempty(name):
                report(r, "line %d: trigger script data\\Scripts\\%s.txt missing or empty" % (n, name))
            if "," in name:
                warn(r, "line %d: trigger name %r contains commas; the game must read map lines with "
                        "'line input' (plain 'input' splits at commas)" % (n, name))
            continue
        decor_object = (name not in ENTITIES and name in TILES and
                        (tiles_ini.get(name, "Layer", "") or "").lower() == "decor")
        if decor_object:                    # (a decor tile placed as an object: its picture and data are the tile's)
            if typ != "StaticObject":
                report(r, "line %d: the decor tile %s can only be placed as a StaticObject" % (n, name))
        elif name not in ENTITIES:
            report(r, "line %d: entity %r has no sprite" % (n, name))
        elif entities_ini.section(name) is None:
            warn(r, "entity %r has no [section] in Entities.ini" % name)
        else:
            t = entities_ini.get(name, "Type")
            if t and t != typ and not (t == "NPC" and typ in NPC_TYPES):
                warn(r, "line %d: %s placed as %s but Entities.ini says Type=%s" % (n, name, typ, t))
        if not (0 <= x < MAP_W * 32 and 0 <= y < MAP_H * 32):
            report(r, "line %d: %s at %s,%s is off the map" % (n, name, xs, ys))
        if typ in NPC_TYPES and 0 <= x < MAP_W * 32 and 0 <= y < MAP_H * 32:
            check_npc_options(r, n, name, x, y, f[4] if len(f) > 4 else "", lines, entities_ini, tiles_ini, report)
        if typ == "MapItem":
            q = f[4] if len(f) > 4 else ""
            if not (q.isdigit() and int(q) >= 1):
                report(r, "line %d: MapItem quantity %r should be a whole number >= 1" % (n, q))


# ------------------------------------------------------------------ NPC movement Options on map lines
TRAP_KINDS = ("Darts", "Gas", "Weakness", "Pit", "Alarm", "Bucket", "Pie")
OPTION_KEYS = {"Zone", "Chase", "Patrol", "PatrolMode", "Pause", "Stand", "Attitude", "Id", "Name",
               "Face", "Cone", "Group", "Friendly.If", "Schedule", "Roost",
               "State", "Nap", "Level", "Look"}   # (Level=: a Shard Remnant's strength; State=Sit: how it rests; Nap=x,y: a spot it curls up on; Name=: its own name; Face, Cone, Group, Friendly.If: stealth; Look=N: which of its trade's colourings)
_npc_ids = None


def npc_ids():
    """{Id: [map, ...]}: the Id= of every NPC line in maps\\ (Set.NPC.Attitude names one NPC by it)."""
    global _npc_ids
    if _npc_ids is None:
        _npc_ids = {}
        for f in sorted(os.listdir(p("maps"))):
            if f.endswith(".txt"):
                for line in read_lines(p("maps", f))[MAP_H:]:
                    fl = line.split("	")
                    if fl[0] in ("NPC", "GoodNPC", "BadNPC") and len(fl) > 4:
                        for tok in fl[4].split():
                            if tok.startswith("Id="):
                                _npc_ids.setdefault(tok[3:], []).append(f[:-4])
        for f in sorted(os.listdir(SCRIPT_DIR)):          # (and one a script puts down: Add.Entity ... NPC Id=)
            if f.lower().endswith(".txt"):
                for line in read_lines(os.path.join(SCRIPT_DIR, f)):
                    fl = line.split("\t")
                    if len(fl) > 5 and fl[1].strip() == "Add.Entity" and fl[4].strip() == "NPC":
                        for tok in fl[5].split():
                            if tok.startswith("Id="):
                                _npc_ids.setdefault(tok[3:], []).append(f[:-4])
    return _npc_ids
PATROL_MODES = {"PingPong", "Loop"}
PAUSE_RE = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$")


def parse_rect(v):
    """'x1,y1,x2,y2' (1-based tiles of the NPC's map; past its edges = the next map's tiles) -> (x1, y1, x2, y2) or None."""
    parts = v.split(",")
    if len(parts) != 4 or not all(re.fullmatch(r"-?\d+", q.strip()) for q in parts):
        return None
    return tuple(int(q) for q in parts)


def rect_ok(rc):
    """A rectangle inside the NPC's map or reaching onto the maps around it (up to one map's width/height past an edge)."""
    x1, y1, x2, y2 = rc
    return 1 - MAP_W <= x1 <= x2 <= 2 * MAP_W and 1 - MAP_H <= y1 <= y2 <= 2 * MAP_H


def map_of_tile(home, tx, ty):
    """(map name, local x, local y) for tile tx,ty of map home (1-based; past its edges = the next maps), or None if
    there is no such map. Zones and patrol routes may reach over the seams (the game loads the 9 maps round you)."""
    try:
        mx, my, mz = (int(v) for v in home.split(","))
    except ValueError:
        return None if not (1 <= tx <= MAP_W and 1 <= ty <= MAP_H) else (home, tx, ty)
    dx, dy = (tx - 1) // MAP_W, (ty - 1) // MAP_H
    name = "%d,%d,%d" % (mx + dx, my + dy, mz)
    if not os.path.exists(p("maps", name + ".txt")):
        return None
    return name, tx - dx * MAP_W, ty - dy * MAP_H


def rect_has(rc, x, y):
    return rc[0] <= x <= rc[2] and rc[1] <= y <= rc[3]


def rect_in(inner, outer):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def map_walker(lines, tiles_ini):
    """(walk(tx, ty), flood(seed tiles) -> set of tiles), 0-based tiles, for one map: the walkable cells of
    Walkable.Data (7x7 per tile), staying inside the map, with every Lock tile shut (an NPC can't count on a door
    being open)."""
    R = 7
    cells = [[ground_key(c) for c in row.split(":")] for row in lines[:MAP_H]]
    locks = set()
    for line in lines[MAP_H:]:
        f = line.split("\t")
        if f[0] == "Lock" and len(f) >= 3 and f[1].isdigit() and f[2].isdigit():
            locks.add((int(f[1]) - 1, int(f[2]) - 1))
    data = {}

    def sub(sx, sy):
        tx, ty = sx // R, sy // R
        if not (0 <= tx < MAP_W and 0 <= ty < MAP_H) or ty >= len(cells) or tx >= len(cells[ty]) or (tx, ty) in locks:
            return False
        t = cells[ty][tx]
        if t not in data:
            data[t] = tile_walk(tiles_ini, t)
        return data[t][(sy % R) * R + sx % R] == "1"

    def walk(tx, ty):
        return sub(tx * R + 3, ty * R + 3)

    def flood(seeds):
        todo = [(tx * R + cx, ty * R + cy) for tx, ty in seeds for cx in range(R) for cy in range(R)]
        todo = [c for c in todo if sub(*c)]
        seen = set()
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            seen.add(c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (c[0] + dx, c[1] + dy)
                if nb not in seen and sub(*nb):
                    todo.append(nb)
        return {(sx // R, sy // R) for sx, sy in seen}
    return walk, flood


def check_npc_options(r, n, name, x, y, field, lines, entities_ini, tiles_ini, report):
    """The Options field of an NPC map line: Attitude=Good|Bad, known keys, number formats, tiles on the map, the Zone holds
    the spawn tile, the Chase rectangle holds the Zone (and the patrol), patrol waypoints are walkable and reachable
    from each other inside the map (from the spawn tile, with Lock tiles shut)."""
    where = "%s line %d (%s)" % (r, n, name)
    home = os.path.splitext(os.path.basename(r))[0]
    opts = {}
    for tok in field.split():
        if "=" not in tok:
            warn(where, "option %r isn't Key=Value (ignored by the game)" % tok)
            continue
        k, v = tok.split("=", 1)
        if k not in OPTION_KEYS:
            report(where, "unknown option %s (want %s)" % (k, ", ".join(sorted(OPTION_KEYS))))
            continue
        if k in opts:
            report(where, "option %s given twice" % k)
        if k == "Attitude" and v not in ("Good", "Bad", "Passive"):
            report(where, "Attitude=%r should be Good, Bad or Passive" % v)
        if k == "Id" and len(npc_ids().get(v, [])) > 1:
            report(where, "Id=%s is on more than one NPC (%s): an Id names one NPC" % (v, ", ".join(npc_ids()[v])))
        opts[k] = v
    if ";" in field:
        report(where, "';' in the Options field")
    sx, sy = entity_tile(name, x, y)
    spawn = (sx + 1, sy + 1)
    walk, flood = map_walker(lines, tiles_ini)
    zone = chase = None
    for k in ("Zone", "Chase"):
        if k in opts:
            rc = parse_rect(opts[k])
            if rc is None:
                report(where, "%s=%r should be x1,y1,x2,y2 (whole tile numbers)" % (k, opts[k]))
            elif not rect_ok(rc):
                report(where, "%s=%s is not a rectangle with x1<=x2 and y1<=y2 inside %d..%d,%d..%d (this map and the next ones)"
                       % (k, opts[k], 1 - MAP_W, 2 * MAP_W, 1 - MAP_H, 2 * MAP_H))
            elif any(map_of_tile(home, cx, cy) is None for cx in (rc[0], rc[2]) for cy in (rc[1], rc[3])):
                report(where, "%s=%s reaches past this map onto a map that doesn't exist" % (k, opts[k]))
            elif k == "Zone":
                zone = rc
            else:
                chase = rc
    if "Pause" in opts:
        m = PAUSE_RE.match(opts["Pause"])
        if not m:
            report(where, "Pause=%r should be min-max seconds" % opts["Pause"])
        elif float(m.group(1)) > float(m.group(2)):
            report(where, "Pause=%s: min is more than max" % opts["Pause"])
    if "Stand" in opts and opts["Stand"] not in ("0", "1"):
        report(where, "Stand=%r should be 0 or 1" % opts["Stand"])
    if "PatrolMode" in opts:
        if opts["PatrolMode"] not in PATROL_MODES:
            report(where, "PatrolMode=%r should be %s" % (opts["PatrolMode"], " or ".join(sorted(PATROL_MODES))))
        if "Patrol" not in opts:
            warn(where, "PatrolMode without a Patrol route")
    stand = opts.get("Stand") == "1"
    if stand and ("Zone" in opts or "Patrol" in opts):
        warn(where, "Stand=1 together with Zone/Patrol: it will just stand")
    if "Patrol" in opts and "Zone" in opts:
        warn(where, "has both Patrol and Zone: it patrols, so the Zone is not used for roaming")
    if zone and not rect_has(zone, *spawn):
        report(where, "Zone=%s doesn't contain its spawn tile %d,%d" % (opts["Zone"], spawn[0], spawn[1]))
    points = []
    if "Patrol" in opts:
        wps = opts["Patrol"].split("/")
        if len(wps) < 2:
            report(where, "Patrol needs at least 2 waypoints")
        for wp in wps:
            q = wp.split(",")
            if len(q) != 2 or not all(re.fullmatch(r"-?\d+", c.strip()) for c in q):
                report(where, "patrol waypoint %r should be x,y (whole tile numbers)" % wp)
                continue
            px, py = int(q[0]), int(q[1])
            if not (1 <= px <= MAP_W and 1 <= py <= MAP_H):
                # on one of the maps round it: that map must exist and the tile be walkable there (reaching it over the
                # seam isn't checked: the game's walk grid covers the 9 maps)
                there = map_of_tile(home, px, py) if (1 - MAP_W <= px <= 2 * MAP_W and 1 - MAP_H <= py <= 2 * MAP_H) else None
                if there is None:
                    report(where, "patrol waypoint %d,%d is off the map, and not on a map next to it" % (px, py))
                elif not map_walker(read_lines(p("maps", there[0] + ".txt")), tiles_ini)[0](there[1] - 1, there[2] - 1):
                    report(where, "patrol waypoint %d,%d (tile %d,%d of %s) is not walkable" % (px, py, there[1], there[2], there[0]))
                continue
            if not walk(px - 1, py - 1):
                report(where, "patrol waypoint %d,%d is not walkable" % (px, py))
                continue
            points.append((px, py))
    reach = None
    if points:
        reach = flood([(spawn[0] - 1, spawn[1] - 1)])
        for px, py in points:
            if (px - 1, py - 1) not in reach:
                report(where, "patrol waypoint %d,%d can't be reached from its spawn tile %d,%d (nor the other waypoints)"
                       % (px, py, spawn[0], spawn[1]))
    # the effective zone: explicit, or Roam.Radius tiles round the spawn tile (clipped to the map)
    roam = entities_ini.get(name, "Roam.Radius") if entities_ini is not None else None
    roam = int(float(roam)) if roam is not None and is_num(roam) else 0
    eff_zone = zone or (max(1, spawn[0] - roam), max(1, spawn[1] - roam),
                        min(MAP_W, spawn[0] + roam), min(MAP_H, spawn[1] + roam))
    if chase:
        if not rect_has(chase, *spawn):
            report(where, "Chase=%s doesn't contain its spawn tile %d,%d" % (opts["Chase"], spawn[0], spawn[1]))
        if "Patrol" not in opts and not stand and not rect_in(eff_zone, chase):
            report(where, "Chase=%s doesn't contain its Zone %s" % (opts["Chase"], ",".join(str(v) for v in eff_zone)))
        for px, py in points:
            if not rect_has(chase, px, py):
                report(where, "Chase=%s doesn't contain patrol waypoint %d,%d" % (opts["Chase"], px, py))
    swims = entities_ini is not None and (entities_ini.get(name, "Swims") or "").strip() == "1"
    if zone and "Patrol" not in opts and not stand and not swims:    # (a swimmer has the water too: it can't be stuck)
        reach = reach or flood([(spawn[0] - 1, spawn[1] - 1)])
        room = [t for t in reach if rect_has(zone, t[0] + 1, t[1] + 1)]
        if len(room) < 2:
            warn(where, "Zone=%s has no reachable walkable tile besides its spawn tile" % opts["Zone"])
    # aggressive NPCs that could chase the player over the whole map
    if entities_ini is not None and entities_ini.get(name, "Aggressive") == "1" and not stand:
        cr = entities_ini.get(name, "Chase.Radius")
        cr = int(float(cr)) if cr is not None and is_num(cr) else 0
        area = chase or (max(1, eff_zone[0] - cr), max(1, eff_zone[1] - cr),
                         min(MAP_W, eff_zone[2] + cr), min(MAP_H, eff_zone[3] + cr))
        if area == (1, 1, MAP_W, MAP_H):
            warn(where, "aggressive %s can chase the player over the whole map (give it a Chase rectangle)" % name)


DECOR_RE = re.compile(r"\+Decor\(([^()]*)\)")


def ground_key(cell):
    """What of a map cell its walking depends on: its tile, and its decor if it has one ("Plank001+Decor(Table001)")."""
    m = DECOR_RE.search(cell)
    base = cell.split("+")[0]
    return base + ("+Decor(%s)" % m.group(1) if m and m.group(1) else "")


def key_parts(key):
    """ground_key -> (tile, decor or "")."""
    m = DECOR_RE.search(key)
    return key.split("+")[0], (m.group(1) if m else "")


def tile_walk(tiles_ini, key):
    """Walkable.Data of a tile, or of a ground_key: the tile's and its decor's together (walkable where both are)."""
    tile, decor = key_parts(key)
    d = tiles_ini.get(tile, "Walkable.Data", "1" * 49)
    d = d if re.fullmatch(r"[01]{49}", d or "") else "1" * 49
    if decor:
        o = tiles_ini.get(decor, "Walkable.Data", "1" * 49)
        if re.fullmatch(r"[01]{49}", o or ""):
            d = "".join("1" if a == "1" and b == "1" else "0" for a, b in zip(d, o))
    return d


# ------------------------------------------------------------------ conditions (Lock lines)
COND_RE = re.compile(r"^\s*(.+?)\s*(<=|>=|<>|=|<|>)\s*(.*?)\s*$")
SLOTS = ["Weapon", "Shield", "Head", "Body", "Legs", "Feet", "Hands", "Ring"]     # the 8 equipment slots
REMOVED_SLOTS = {"Neck"}      # gone since equipment went down to 8 slots
VAR_RE = re.compile(r"\$[A-Za-z][A-Za-z0-9_.()]*[A-Za-z0-9_)]")


def parse_condition(cond):
    """[[(lhs, op, rhs), ...], ...]: the ' or ' branches, each a list of ' and ' clauses (op None = unreadable)."""
    out = []
    for branch in re.split(r"\s+or\s+", cond.strip(), flags=re.I):
        clauses = []
        for c in re.split(r"\s+and\s+", branch, flags=re.I):
            m = COND_RE.match(c)
            clauses.append((m.group(1), m.group(2), m.group(3)) if m else (c, None, None))
        out.append(clauses)
    return out


def check_condition(where, cond, skills, entities_ini, writes):
    """Every $Attr./$Item./$Skill./$Equipped. variable in a condition must make sense."""
    known = script_variables() | SPEC_VARIABLES
    for branch in parse_condition(cond):
        for lhs, op, rhs in branch:
            if op is None:
                err(where, "condition %r: can't read %r (want a=b, a<>b, a<b, a>b, a<=b or a>=b)" % (cond, lhs))
                continue
            for side in (lhs, rhs):
                for v in VAR_RE.findall(side):
                    kind, _, name = v[1:].partition(".")
                    if kind == "Attr":
                        if name not in writes:
                            err(where, "condition uses %s but no script sets attribute %s (Update.Attribute)" % (v, name))
                    elif kind == "Item":
                        if name not in ENTITIES:
                            err(where, "condition uses %s but %r has no sprite in sprites\\Entities" % (v, name))
                    elif kind == "Skill":
                        if name not in skills:
                            err(where, "condition uses %s but %r is not in Config.ini [Skills] List" % (v, name))
                    elif kind == "Equipped":
                        if name not in SLOTS:
                            err(where, "condition uses %s but %r is not an equipment slot (%s)" % (v, name, "/".join(SLOTS)))
                        elif side == lhs and op in ("=", "<>") and rhs.lower() != "none" and "$" not in rhs:
                            if rhs not in ENTITIES:
                                err(where, "condition compares %s with %r, which has no sprite" % (v, rhs))
                            elif (entities_ini.get(rhs, "Slot") or "") != name:
                                err(where, "condition compares %s with %s, whose Slot is %r" % (v, rhs, entities_ini.get(rhs, "Slot")))
                    elif v not in known:
                        err(where, "condition uses unknown variable %s" % v)
            if op in ("<", ">", "<=", ">=") and not (is_num(rhs) or "$" in rhs):
                warn(where, "condition %s%s%s compares with a non-number" % (lhs, op, rhs))


# ------------------------------------------------------------------ scripts
def number_of_commands():
    return None     # (the language is a list in ashen/script_language.py now: no count to fall out of step)


def command_numbers():
    return {}


ITEM_ARGS = {"ITEM NAME", "REQUIRED ITEM", "DISALLOWED ITEM"}
ENTITY_ARGS = {"ENTITY NAME"}
TILE_ARGS = {"CHANGE TO TILE", "CHANGE FROM TILE", "REQUIRED TILE NAME", "DISALLOWED TILE NAME"}
NPC_ARGS = {"NPC NAME"}
ENTITY_TYPES = {"MapItem", "StaticObject", "NPC", "GoodNPC", "BadNPC", "Missile"}
RACK_TYPES = {"BANK", "GENERAL", "SPECIFIC"}
VALUE_TYPES = {"ATTRIBUTE", "BANK", "CALCULATION", "EQUIPPED", "HITPOINTS", "INVENTORY", "SKILL", "XP"}
COLOURS = {"Black", "Blue", "Brown", "Cyan", "DarkBlue", "DarkCyan", "DarkGray", "DarkGreen", "DarkPink",
           "DarkRed", "Green", "LightGray", "Pink", "Red", "White", "Yellow"}


_quest_names = None


def quest_names():
    """Every quest's title and Attribute in data\\Quests.ini, lower case (Quest.Note's QUEST NAME is either)."""
    global _quest_names
    if _quest_names is None:
        _quest_names = set()
        ini = Ini(p("data", "Quests.ini"))
        for sec in ini.sections:
            _quest_names.add(sec[0].lower())
            att = ini.get(sec[0], "Attribute", "")
            if att:
                _quest_names.add(att.strip().lower())
    return _quest_names


def check_scripts(skills, racks):
    cmds = script_commands()
    types = script_command_arg_types()
    nums = command_numbers()
    noc = number_of_commands()
    variables = script_variables() | SPEC_VARIABLES
    used_cmds = set()
    references = set()
    for f in sorted(os.listdir(SCRIPT_DIR)):
        if not f.lower().endswith(".txt"):
            continue
        path = os.path.join(SCRIPT_DIR, f)
        check_raw(path)
        r = rel(path)
        lines = [l for l in read_lines(path)]
        while lines and lines[-1] == "":
            lines.pop()
        if not lines:
            continue                     # empty = "not found" -> engine default
        numbered = {}
        parsed = []
        for i, line in enumerate(lines, 1):
            if line.strip() == "" or line.lstrip().startswith("//"):
                continue
            fields = line.split("\t")
            no = fields[0]
            if not re.fullmatch(r"\d\d+", no):
                err(r, "line %d: line number %r is not a number of 2 digits or more" % (i, no))
            numbered[no] = True
            parsed.append((i, no, fields[1] if len(fields) > 1 else "", fields[2:]))
        expected = ["%02d" % k for k in range(1, len(parsed) + 1)]
        if [x[1] for x in parsed] != expected:
            err(r, "line numbers are not consecutive from 01")
        for i, no, cmd, args in parsed:
            where = "%s line %s" % (r, no)
            if cmd not in cmds:
                err(where, "command %r is not in ashen/script_language.py" % cmd)
                continue
            used_cmds.add(cmd)
            want = cmds[cmd]
            if cmd == "Display.Conversation":
                # The editor has 4 answers; the Python game takes up to 15 (and [if ...] answers)
                if len(args) < 4 or len(args) > 32 or len(args) % 2:
                    err(where, "Display.Conversation needs NPC, MESSAGE and 1-15 (RESPONSE, GOTO) pairs; has %d args" % len(args))
                elif len(args) > want:
                    warn(where, "Display.Conversation has %d answers: the Python game shows them all, the Script Editor "
                                "only the first 4" % ((len(args) - 2) // 2))
            elif cmd == "Display.Refusal":
                if len(args) not in (1, 2):                    # (MESSAGE, and a sound if not the usual Denied)
                    err(where, "Display.Refusal takes a message and maybe a sound; has %d args" % len(args))
            elif cmd == "Display.Message":
                if len(args) not in (2, 3):                    # (COLOUR, MESSAGE, and a sound to go with it if any)
                    err(where, "Display.Message takes a colour, a message and maybe a sound; has %d args" % len(args))
                elif len(args) == 3 and args[2] not in ("", "-") and not os.path.exists(os.path.join(p("sounds"), args[2] + ".wav")):
                    err(where, "Display.Message's sound %r is not in Sounds" % args[2])
            elif len(args) != want:
                err(where, "%s takes %d args, has %d" % (cmd, want, len(args)))
            t = types.get(cmd, {})
            for k, a in enumerate(args, 1):
                at = t.get(k, "")
                if cmd == "Display.Conversation" and k >= 3:
                    at = "GOTO LINE" if k % 2 == 0 else "RESPONSE"
                for v in re.findall(r"\$[A-Za-z][A-Za-z0-9.]*[A-Za-z0-9]", a):
                    # $Attr. $Item. $Skill. $Equipped. $Shards. are filled in in any script argument, as in conditions
                    if v not in variables and not re.match(r"\$(Attr|Item|Skill|Equipped|Shards)\.", v, re.I):
                        err(where, "unknown variable %s" % v)
                if "$" in a and at not in ("GOTO SCRIPT NAME",):
                    continue
                if "GOTO LINE" in at:
                    if a not in numbered:
                        err(where, "goto target %r does not exist" % a)
                elif at in ITEM_ARGS:
                    if a not in ENTITIES:
                        err(where, "item %r has no sprite in sprites\\Entities" % a)
                elif at in ENTITY_ARGS:
                    if a not in ENTITIES:
                        err(where, "entity %r has no sprite in sprites\\Entities" % a)
                elif at in TILE_ARGS:
                    if a not in TILES:
                        err(where, "tile %r has no sprite in sprites\\Tiles" % a)
                elif at in NPC_ARGS:
                    if a not in ENTITIES and a != "$Player.Name":
                        warn(where, "NPC name %r has no sprite in sprites\\Entities" % a)
                elif at == "SOUND FILE":
                    if a not in SOUNDS:
                        err(where, "sound %r not found in sounds\\" % a)
                elif at == "GOTO SCRIPT NAME":
                    if "$" in a:
                        pat = re.escape(a)
                        pat = re.sub(r"\\\$[A-Za-z][A-Za-z0-9.\\]*[A-Za-z0-9]", ".+", pat)
                        if not any(re.fullmatch(pat, s) for s in SCRIPTS):
                            warn(where, "no script matches the dynamic name %r" % a)
                        references.add(("re", pat))
                    else:
                        references.add(("name", a))
                        if not script_nonempty(a):
                            err(where, "Goto.Script target %r missing or empty" % a)
                elif at == "SKILL NAME":
                    if a not in skills and a != "Hits":
                        err(where, "skill %r not in Config.ini [Skills] List" % a)
                elif at == "RACK ID":
                    if a != "-" and a not in racks:
                        err(where, "item rack %r not in data\\ItemRacks.ini" % a)
                elif at == "ITEMRACK TYPE":
                    if a.upper() not in RACK_TYPES:
                        err(where, "item rack type %r not one of %s" % (a, "/".join(sorted(RACK_TYPES))))
                elif at == "ENTITY TYPE":
                    if a not in ENTITY_TYPES:
                        err(where, "entity type %r not one of %s" % (a, "/".join(sorted(ENTITY_TYPES))))
                elif at == "VALUE TYPE":
                    if a.upper() not in VALUE_TYPES:
                        err(where, "value type %r not one of %s" % (a, "/".join(sorted(VALUE_TYPES))))
                elif at == "COLOUR":
                    if a not in COLOURS:
                        warn(where, "colour %r is not in the Script Editor's colour list" % a)
                elif at == "NPC ID":
                    if a.upper() != "CLICKED" and a not in npc_ids():
                        err(where, "no NPC has Id=%s on its map line (or use CLICKED)" % a)
                elif at == "ATTITUDE":
                    if a not in ("Good", "Bad"):
                        err(where, "attitude %r should be Good or Bad" % a)
                elif at == "QUEST NAME":
                    if a.lower() not in quest_names():
                        err(where, "quest %r is not a quest's title or Attribute in data\\Quests.ini" % a)
                elif at in ("QUANTITY TO ADD", "QUANTITY TO REMOVE", "QUANTITY REQUIRED", "DISALLOWED QUANTITY"):
                    if not (a.isdigit() or re.fullmatch(r"\d+-\d+", a) or a.startswith("$")):
                        warn(where, "quantity %r is not a whole number or a min-max range" % a)
    for c in sorted(used_cmds):
        if noc is not None and nums.get(c, 0) > noc:
            warn("Dragon Sword Editor.bas [SE.Get.Commands]", "command %s is Command$(%d) but Number.Of.Commands=%d, so the editor "
                                      "doesn't list it" % (c, nums[c], noc))
    return references


PLACES = {}         # UPPER place ID -> (ID, map, tile x, tile y): Id lines and every Id= (the game's places.py)


def check_unique_ids():
    """An Id= (on any map line: NPC, item, object) names one thing in the world, so "<Verb> <Id>" scripts mean it, and
    an Id line names a tile; both are places scripts and quests can name. No two share an ID (in any case), and none is
    the name of an item, object or tile (that would be "<Verb> <Name>")."""
    seen = {}
    for f in sorted(os.listdir(p("maps"))):
        if not f.endswith(".txt"):
            continue
        for line in read_lines(p("maps", f))[MAP_H:]:
            fl = line.split("	")
            if fl[0] in ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject"):
                for w in " ".join(fl[4:]).split():
                    if w.startswith("Id="):
                        seen.setdefault(w[3:].upper(), []).append(("%s %s" % (f[:-4], fl[1].strip()), w[3:]))
                        if is_num(fl[2]) and is_num(fl[3]):
                            PLACES.setdefault(w[3:].upper(), (w[3:], f[:-4], int((float(fl[2]) + 16) // 32) + 1,
                                                              int((float(fl[3]) + 28) // 32) + 1))
            elif fl[0] == "Id" and len(fl) == 4 and fl[2].isdigit() and fl[3].isdigit():
                seen.setdefault(fl[1].upper(), []).append(("%s tile %s,%s" % (f[:-4], fl[2], fl[3]), fl[1]))
                PLACES.setdefault(fl[1].upper(), (fl[1], f[:-4], int(fl[2]), int(fl[3])))
    for key, where in sorted(seen.items()):
        oid = where[0][1]
        if len(where) > 1:
            err("Maps", "ID %s is used more than once (%s): an ID names one thing or place"
                % (oid, "; ".join(w for w, _ in where)))
        where = [w for w, _ in where]
        if oid in ENTITIES or oid in TILES:
            err("Maps", "Id=%s (%s) is also a sprite's name: pick another Id" % (oid, where[0]))


COORD_TYPES = {"X COORDINATE,Y COORDINATE", "TARGET X,TARGET Y", "REQUIRED TILE COORDINATES",
               "DISALLOWED TILE COORDINATES"}


def place_of(name):
    """The place called name (any case: (ID, map, tile x, tile y)), or None."""
    return PLACES.get(name.strip().upper())


def check_place_refs():
    """A script argument that takes coordinates may name a place instead (Teleport Isle_Landing): each name must be a
    place, and outside Teleport (which goes to the place's map) on the map the script runs on, when that's known."""
    types = script_command_arg_types()
    for s in sorted(SCRIPTS):
        own_map = s if re.fullmatch(r"-?\d+,-?\d+,-?\d+", s) else None
        for cmd, a in script_lines(s):
            for k, t in types.get(cmd, {}).items():
                i = k - 1                                       # (types are numbered from 1, a from 0)
                if t.strip() not in COORD_TYPES or i >= len(a):
                    continue
                for v in a[i].split() if "TILE COORDINATES" in t else [a[i]]:
                    v = v.strip()
                    if not v or "," in v or v[:1] in "$-+=0123456789":
                        continue
                    pl = place_of(v)
                    if pl is None:
                        err("data\\Scripts\\%s.txt" % s, "%s: %r is neither coordinates nor a place ID" % (cmd, v))
                    elif cmd != "Teleport" and own_map and pl[1] != own_map:
                        err("data\\Scripts\\%s.txt" % s, "%s: place %s is on map %s, not this one" % (cmd, pl[0], pl[1]))


def check_script_reachability(references, triggers):
    """Every non-empty script should be reachable by a lookup rule, a trigger or Goto.Script."""
    verbs = set()
    for ini_name in ("Tiles.ini", "Entities.ini"):
        ini = Ini(p("data", ini_name))
        for sec, items in ini.sections:
            for k, v in items:
                if k == "Use.Words":
                    verbs.update(w.strip() for w in v.split(",") if w.strip())
    verbs |= {"Pickup", "Drop", "Drop 1", "Examine", "Eat", "Talk to", "Attack", "Walk here", "Use", "Kill",
              "Count", "Climb Up", "Climb Down", "Bank", "Grasp"}      # (Grasp: the spell, cast at a thing)
    names = TILES | ENTITIES | {re.sub(r"\d{3}$", "", t) for t in TILES}
    with_id = set()                      # every Id= on a map line or added by a script ("Verb Id": e.g. Read Ashford)
    for f in os.listdir(p("maps")):
        if f.endswith(".txt"):
            for l in read_lines(p("maps", f))[MAP_H:]:
                fl = l.split("	")
                if fl[0] == "Id" and len(fl) > 1:      # (a tile's place ID: its own scripts - Examine Grave_Tom_Barrow)
                    with_id.add(fl[1].strip())
                for w in " ".join(fl[4:]).split():
                    if w.startswith("Id="):
                        with_id.add(w[3:])
    for sc in SCRIPTS:                   # ... and what scripts add (Add.Entity <x,y> <name> <type> Id=...)
        for l in read_lines(os.path.join(SCRIPT_DIR, sc + ".txt")):
            fl = l.split("	")
            if len(fl) > 5 and fl[1] == "Add.Entity":
                for w in fl[5].split():
                    if w.startswith("Id="):
                        with_id.add(w[3:])
    for s in sorted(SCRIPTS):
        if not script_nonempty(s):
            continue
        ok = False
        m = re.fullmatch(r"Use (.+) With (.+)", s)
        if m and m.group(1) in names and (m.group(2) in names or m.group(2) in with_id):
            ok = True    # (an item used on one thing with an Id: Use Egg With Marens_Range, tried first)
        for v in verbs:
            if s.startswith(v + " ") and (s[len(v) + 1:] in names or re.fullmatch(r"\[[A-Za-z]+\]", s[len(v) + 1:])
                                          or s[len(v) + 1:] in with_id):
                ok = True
        if os.path.exists(p("maps", s + ".txt")):
            ok = True    # map-entry script
        if s.endswith(" Skill"):
            ok = True    # run when that skill is clicked in the stat box
        if s in WAVE_SCRIPTS:
            ok = True    # a monster attack's On.Win.Script / On.Lose.Script (data\Waves.ini)
        if s in triggers or ("name", s) in references or any(k == "re" and re.fullmatch(v, s) for k, v in references):
            ok = True
        if not ok:
            warn(rel(os.path.join(SCRIPT_DIR, s + ".txt")), "not reachable by any lookup rule, trigger or Goto.Script")


# ------------------------------------------------------------------ ini files
def walkable_at(map_name, px, py, tiles_ini):
    fx, fy = px + 15, py + 28
    col, row = int(fx // 32), int(fy // 32)
    lines = read_lines(p("maps", map_name + ".txt"))
    tile = ground_key(lines[row].split(":")[col])
    data = tile_walk(tiles_ini, tile)
    sx, sy = int((fx % 32) * 7 // 32), int((fy % 32) * 7 // 32)
    return data[sy * 7 + sx] == "1", tile


CONFIG_REQUIRED = {
    "Debugging": ["Logging.Enabled"],
    "Gameplay": ["Player.Movement.Speed", "Player.Attack.Speed", "Hitpoints.Base", "Player.Visible",
                 "NPC.Respawn.Delay", "Item.Respawn.Delay", "Sell.Price.Factor", "Maximum.Bank.Slots", "FogOfWar.Enabled",
                 "FogOfWar.Viewable.Distance", "Start.Map", "Start.X", "Start.Y"],
    "Interface": ["Map.X.Tiles", "Map.Y.Tiles", "InventoryItems.Columns",
                  "InventoryItems.Rows", "ActionBox.Columns", "ActionBox.Rows"],
    "Skills": ["List"],
    "Sounds": ["Enabled", "Music"],
}


def check_config(tiles_ini):
    path = p("data", "Config.ini")
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    for sec, keys in CONFIG_REQUIRED.items():
        for k in keys:
            if ini.get(sec, k) is None:
                err(r, "[%s] %s missing" % (sec, k))
    for bad_sec, bad_key in (("Gameplay", "NPC.Repawn.Delay"), ("Debugging", "FogOfWar.Enabled"),
                             ("Interface", "Screen.X.Tiles"), ("Interface", "Screen.Y.Tiles")):
        if ini.get(bad_sec, bad_key) is not None:
            err(r, "[%s] %s should not exist" % (bad_sec, bad_key))
    if ini.get("Interface", "Map.X.Tiles", "25").strip() != str(MAP_W) or ini.get("Interface", "Map.Y.Tiles", "21").strip() != str(MAP_H):
        warn(r, "Map.X.Tiles/Map.Y.Tiles differ from the %dx%d the maps use" % (MAP_W, MAP_H))
    sm = ini.get("Gameplay", "Start.Map", "")
    if not os.path.exists(p("maps", sm + ".txt")):
        err(r, "Start.Map %r has no map file" % sm)
    else:
        try:
            ok, tile = walkable_at(sm, float(ini.get("Gameplay", "Start.X")), float(ini.get("Gameplay", "Start.Y")), tiles_ini)
            if not ok:
                err(r, "start position is on an unwalkable part of %s" % tile)
        except (TypeError, ValueError, IndexError) as e:
            err(r, "bad start position (%s)" % e)
    music = ini.get("Sounds", "Music", "")
    if music and not os.path.exists(p("sounds", music)):
        err(r, "music %r not in sounds\\" % music)
    skills = [s.strip() for s in ini.get("Skills", "List", "").split(",") if s.strip()]
    for sk in skills:                     # the StatBox tiles' icons (any sprite; none = the name in letters)
        icon = (ini.get("Skills", "Icon." + sk) or "").strip()
        if not icon:
            warn(r, "[Skills] Icon.%s missing: its StatBox tile shows letters" % sk)
        elif not any(os.path.exists(p("sprites", f, icon + ".png")) for f in ("Entities", "Interface", "Tiles")):
            err(r, "[Skills] Icon.%s=%s has no sprite" % (sk, icon))
    return skills


def check_tiles():
    path = p("data", "Tiles.ini")
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    for t in sorted(TILES):
        if ini.section(t) is None:
            err(r, "no [%s] section for tile sprite" % t)
    for sec, items in ini.sections:
        if sec not in TILES:
            warn(r, "[%s] has no sprite in sprites\\Tiles" % sec)
        for k, v in items:
            if k is None:
                continue
            if k == "Walkable.Data" and not re.fullmatch(r"[01]{49}", v):
                err(r, "[%s] Walkable.Data must be 49 chars of 0/1" % sec)
            elif k in ("Show.Name", "Line.of.Sight") and v not in ("0", "1"):
                err(r, "[%s] %s must be 0 or 1" % (sec, k))
            elif k == "Walk.Speed" and not (is_num(v) and 0.2 <= float(v) <= 3):
                err(r, "[%s] Walk.Speed must be a number from 0.2 to 3 (1 = normal)" % sec)
            elif k == "Blend" and not (v.isdigit() and 0 <= int(v) <= 9):
                err(r, "[%s] Blend must be a whole number 0 to 9 (a higher one is drawn over a lower one's edge)" % sec)
            elif k == "Blend.Texture" and v not in TILES:
                err(r, "[%s] Blend.Texture %r has no sprite in sprites\\Tiles" % (sec, v))
            elif k == "Open.Tile" and v not in TILES:
                err(r, "[%s] Open.Tile %r has no sprite in sprites\\Tiles" % (sec, v))
            elif k == "Unlocked.Tile" and v not in TILES:
                err(r, "[%s] Unlocked.Tile %r has no sprite in sprites\\Tiles" % (sec, v))
            elif k not in ("Walkable.Data", "Show.Name", "Use.Words", "Examine.Info", "Line.of.Sight", "Walk.Speed",
                           "Blend", "Blend.Texture", "Texture", "Unlocked.Tile", "Open.Tile",     # Texture: the Python game's big textures
                           "Layer", "Foam", "Sway", "Sway.Ground", "Flame", "Water", "Light", "Anim.Frames", "Anim.Speed",
                           "Door", "Glow.Colour", "Glow.Match", "Piece", "Seat",    # (Seat=S: sit on it, facing south)
                           "Overhead", "Display.Name",                              # (drawn over people too: an arch;
                                                                                    #  what it's called, shown)
                           "Joins", "Below"):                                       # (the sides a set's piece joins;
                                                                                    #  the tile under a tall one)
                warn(r, "[%s] unknown key %s" % (sec, k))       # (Layer=Decor; the rest: what moves and gives light)
            elif k in ("Sway", "Light", "Anim.Frames", "Anim.Speed") and not is_num(v):
                err(r, "[%s] %s=%r is not a number" % (sec, k, v))
            elif k in ("Flame", "Water", "Overhead") and v not in ("0", "1"):
                err(r, "[%s] %s must be 0 or 1" % (sec, k))
            elif k == "Joins" and not (v in ("*", "-") or (v and set(v) <= set("NESW"))):
                err(r, "[%s] Joins must be the sides it joins (N, E, S, W), * (any) or - (none)" % sec)
            elif k == "Below" and v not in TILES:
                err(r, "[%s] Below %r has no sprite in sprites\\Tiles" % (sec, v))
            elif k == "Seat" and v not in ("N", "E", "S", "W"):
                err(r, "[%s] Seat must be N, E, S or W (the way you face, sitting on it)" % sec)
            elif k == "Door" and v not in ("0", "1", "Gate"):
                err(r, "[%s] Door must be 1 (a door) or Gate" % sec)
            elif k == "Sway.Ground" and v not in TILES:
                err(r, "[%s] Sway.Ground %r has no sprite in sprites\\Tiles" % (sec, v))
            elif k == "Anim.Frames" and is_num(v) and int(float(v)) > 1:
                for n in range(1, int(float(v)) + 1):
                    if "%s%d" % (sec, n) not in TILES:
                        err(r, "[%s] Anim.Frames=%s but there's no sprite %s%d" % (sec, v, sec, n))
    for t in sorted(TILES):
        if not re.search(r"\d{3}$", t):
            warn("sprites\\Tiles", "tile %r doesn't end in a 3-digit variant number" % t)
    check_tile_sets()
    return ini


def check_tile_sets():
    """data\\TileSets.ini: sets of tiles that go together (Title, Columns, Tiles, Kind; a coast's Land, Water, Corners,
    Small); every tile in one is there."""
    path = p("data", "TileSets.ini")
    if not os.path.exists(path):
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    for sec, items in ini.sections:
        keys = {k: v for k, v in items if k}
        for k in keys:
            if k not in ("Title", "Columns", "Tiles", "Kind", "Land", "Water", "Corners", "Small"):
                warn(r, "[%s] unknown key %s" % (sec, k))
        if keys.get("Kind", "Set") not in ("Set", "Stretch", "Rug", "Join", "Shore"):
            err(r, "[%s] Kind must be Set, Stretch, Rug, Join or Shore" % sec)
        for k in ("Land", "Water"):
            if keys.get(k) and keys[k] not in TILES:
                err(r, "[%s] %s %r has no sprite in sprites\\Tiles" % (sec, k, keys[k]))
        for k in ("Corners", "Small"):
            for part in [x for x in keys.get(k, "").split(",") if x.strip()]:
                corner, _, tile = part.partition(":")
                if corner.strip() not in ("NE", "NW", "SE", "SW") or tile.strip() not in TILES:
                    err(r, "[%s] %s: %r should be NE, NW, SE or SW and a tile" % (sec, k, part))
        if not keys.get("Columns", "").isdigit() or int(keys["Columns"]) < 1:
            err(r, "[%s] Columns must be a whole number, 1 or more" % sec)
        names = [n.strip() for n in keys.get("Tiles", "").split(",")]
        if not any(names):
            err(r, "[%s] has no Tiles" % sec)
        for n in names:
            if n and n not in TILES:
                err(r, "[%s] tile %r has no sprite in sprites\\Tiles" % (sec, n))


def footprint_fits(name, data):
    """An object's footprint is 7 cells to 32 pixels each way of its sprite."""
    path = p("sprites", "Entities", name + ".png")
    if not os.path.exists(path):
        return True
    from PIL import Image
    w, h = Image.open(path).size
    return len(data) == max(1, round(w * 7 / 32)) * max(1, round(h * 7 / 32))


ENTITY_KEYS = {"Type", "Attitude", "Use.Words", "Examine.Info", "Stackable", "Droppable", "Value", "Food.Value",
               "Hitpoints", "Attack.Speed", "Strength", "Defence", "Aggro.Range", "Sight.Cone", "Hearing", "Weapon.Range",
               "Movement.Speed", "Aggressive", "Respawn", "Drops", "Slot", "Attack", "Requires",
               "Roam.Radius", "Chase.Radius", "Walk.Speed", "Pause", "Spell", "Magic", "Solid", "Flees", "Flap", "Light.Flicker", "Glow", "Layer", "Anim.Frames", "Anim.Speed", "Once", "On.Hit", "Cures", "Schedule", "Durability", "Resists", "Freeze.Immune", "Rank", "Level", "Swap",
               "Range", "Ammo", "Missile", "Missile.Impact", "Missile.Sound", "Kill.Sound",   # bows (Range, Ammo), NPCs that shoot (Missile...)
               "Light", "Walkable.Data",                                          # what lights the dark; an object's footprint
               "Crop", "Keep.On.Death",                                          # a seed's crop (Crops.ini); kept on death
               "Slain.By",                                                       # only that weapon gives its death blow
               "Base", "Enchanted", "Enchant",                                   # an enchanted kind's gear and word; a rare shard's word (shardcraft.py)
               "States", "Fidgets",                                              # how it may rest when it stops (Sit,Lie); a moment's pose now and then
               "Hunts",                                                          # the NPCs it goes for (Rabbit,Sheep)
               "Swims", "Calls",                                                 # at home in the water too (an otter); its call
               "Indoors",                                                        # 0: an animal that won't walk into a house
               "Look.Parts", "Looks",                                            # its parts' colours; its other colourings
               "Display.Name",                                                   # what the player sees it called
               "Sleeper.Of",                                                     # the NPC (its Id) a sleeping thing is
               "Lock", "Key", "Sturdy",                                          # a chest's lock (locks.py), its key; 1: never broken open
               "Warm",                                                           # 1: it keeps the cold off (cold.py)
               "Vehicle", "Seat.1", "Seat.2", "Seat.4", "Seat.8"}                # a cart (carts.py): where its rider stands
NUMERIC_ENTITY_KEYS = ENTITY_KEYS - {"Type", "Attitude", "Use.Words", "Examine.Info", "Drops", "Slot", "Requires", "Pause", "Spell", "Layer", "Walkable.Data",
                                     "Ammo", "Missile", "Missile.Impact", "Missile.Sound", "Kill.Sound", "On.Hit", "Cures", "Schedule", "Resists", "Crop", "Slain.By", "States", "Fidgets", "Hunts", "Calls",
                                     "Base", "Enchanted", "Enchant",
                                     "Look.Parts", "Looks", "Display.Name", "Sleeper.Of", "Key", "Seat.1", "Seat.2", "Seat.4", "Seat.8"}
MOVEMENT_KEYS = ("Roam.Radius", "Chase.Radius", "Walk.Speed", "Pause")
ENTITIES_INI = None


def check_equipment(ini, skills):
    """Equipment keys: Slot is a known slot, Attack/Defence are numbers (checked with the other numeric keys),
    Requires is 'Skill level' pairs of known skills."""
    r = rel(p("data", "Entities.ini"))
    for sec, items in ini.sections:
        slot = ini.get(sec, "Slot")
        if slot is None:
            if ini.get(sec, "Attack") is not None or ini.get(sec, "Requires") is not None or \
                    (ini.get(sec, "Defence") is not None and ini.get(sec, "Type") not in NPC_TYPES):
                warn(r, "[%s] has Attack/Defence/Requires but no Slot, so it can't be equipped" % sec)
            continue
        if slot in REMOVED_SLOTS:
            warn(r, "[%s] Slot=%s: that slot was removed (the 8 slots are %s), so it can't be worn" % (sec, slot, "/".join(SLOTS)))
        elif slot not in SLOTS:
            err(r, "[%s] Slot=%r is not one of %s" % (sec, slot, "/".join(SLOTS)))
        if ini.get(sec, "Type") != "MapItem":
            err(r, "[%s] has a Slot but Type=%s (only MapItems can be equipped)" % (sec, ini.get(sec, "Type")))
        st = ini.get(sec, "Stackable")
        if st and is_num(st) and float(st) > 1:
            warn(r, "[%s] is equipment but Stackable=%s" % (sec, st))
        if ini.get(sec, "Attack") is None and ini.get(sec, "Defence") is None:
            warn(r, "[%s] has Slot=%s but neither Attack nor Defence" % (sec, slot))
        req = (ini.get(sec, "Requires") or "").split()
        if len(req) % 2:
            err(r, "[%s] Requires=%r should be 'Skill level' pairs" % (sec, ini.get(sec, "Requires")))
        for i in range(0, len(req) - 1, 2):
            if req[i] not in skills:
                err(r, "[%s] Requires skill %r is not in Config.ini [Skills] List" % (sec, req[i]))
            if not req[i + 1].isdigit():
                err(r, "[%s] Requires level %r for %s is not a whole number" % (sec, req[i + 1], req[i]))
        words = [w.strip() for w in (ini.get(sec, "Use.Words") or "").split(",")]
        if "Wield" in words or "Wear" in words:
            warn(r, "[%s] lists Wield/Wear in Use.Words; the game adds them to equipment itself" % sec)


def check_movement_keys(ini, sec, typ, r):
    """Roam.Radius / Chase.Radius: whole numbers of tiles (0..map width); Walk.Speed: 0-1; Pause: min-max seconds."""
    vals = {k: ini.get(sec, k) for k in MOVEMENT_KEYS}
    if typ not in NPC_TYPES:
        for k, v in vals.items():
            if v is not None:
                warn(r, "[%s] has %s but Type=%s (only NPCs move)" % (sec, k, typ))
        return
    for k in ("Roam.Radius", "Chase.Radius"):
        v = vals[k]
        if v is not None and is_num(v) and not (re.fullmatch(r"\d+", v) and int(v) <= MAP_W):
            err(r, "[%s] %s=%s should be a whole number of tiles, 0 to %d" % (sec, k, v, MAP_W))
    v = vals["Walk.Speed"]
    if v is not None and is_num(v) and not (0 <= float(v) <= 1):
        err(r, "[%s] Walk.Speed=%s should be 0 to 1 (a fraction of Movement.Speed)" % (sec, v))
    elif v is not None and is_num(v) and float(v) == 0 and vals["Roam.Radius"] not in (None, "0"):
        warn(r, "[%s] Walk.Speed=0 but Roam.Radius=%s: it can never get anywhere" % (sec, vals["Roam.Radius"]))
    v = vals["Pause"]
    if v is not None:
        m = PAUSE_RE.match(v)
        if not m:
            err(r, "[%s] Pause=%r should be min-max seconds (e.g. 1-4)" % (sec, v))
        elif float(m.group(1)) > float(m.group(2)):
            err(r, "[%s] Pause=%s: min is more than max" % (sec, v))
        elif float(m.group(2)) > 60:
            warn(r, "[%s] Pause=%s: over a minute between moves" % (sec, v))


def check_entities():
    path = p("data", "Entities.ini")
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    frames = set()                      # <Name>1..N: the frames of an entity with Anim.Frames=N (it animates in place)
    for e in ENTITIES:
        n = ini.get(e, "Anim.Frames") if ini.section(e) is not None else None
        if n and n.strip().isdigit():
            frames |= {"%s%d" % (e, k) for k in range(1, int(n) + 1)}
            for k in range(1, int(n) + 1):
                if "%s%d" % (e, k) not in ENTITIES:
                    err(r, "[%s] Anim.Frames=%s but there's no sprite %s%d" % (e, n, e, k))
    for e in ENTITIES:                  # <Name>_<State>2 / 8: how an NPC with States= rests (Sit: Cat_Sit2, Cat_Sit8),
        for key in ("States", "Fidgets", "Swims"):   # (and Fidgets=: a moment's pose now and then; Swims: _Swim)
            states = ini.get(e, key) if ini.section(e) is not None else None
            if key == "Swims":
                states = "Swim" if (states or "").strip() == "1" else ""
            for st in [x.strip() for x in (states or "").split(",") if x.strip()]:
                for d in "28":
                    frames.add("%s_%s%s" % (e, st, d))
                    if "%s_%s%s" % (e, st, d) not in ENTITIES:
                        err(r, "[%s] %s=%s but there's no sprite %s_%s%s" % (e, key, states, e, st, d))
    for e in sorted(ENTITIES - NON_PLACEABLE - frames):
        if ini.section(e) is None:
            err(r, "no [%s] section for entity sprite" % e)
    for sec, items in ini.sections:
        if sec not in ENTITIES:
            warn(r, "[%s] has no sprite in sprites\\Entities" % sec)
        typ = ini.get(sec, "Type")
        call = (ini.get(sec, "Calls") or "").strip()
        if call and call not in SOUNDS:
            err(r, "[%s] Calls=%s: there's no sounds\\%s.wav" % (sec, call, call))
        for prey in [x.strip() for x in (ini.get(sec, "Hunts") or "").split(",") if x.strip()]:
            if prey not in ("Foes", "All") and (ini.get(prey, "Type") or "") != "NPC":   # (Foes: any monster that
                #  attacks; All: any creature that can be fought, a Shard Remnant's)
                err(r, "[%s] Hunts=%s: there's no NPC called %s" % (sec, ini.get(sec, "Hunts"), prey))
        if typ not in ("MapItem", "StaticObject", "NPC"):
            if typ in ("GoodNPC", "BadNPC"):
                warn(r, "[%s] Type=%s is the old type: Type=NPC with Attitude=%s" % (sec, typ, typ[:-3]))
            else:
                err(r, "[%s] Type=%r is not MapItem/StaticObject/NPC" % (sec, typ))
        if typ == "NPC" and (ini.get(sec, "Attitude") or "") not in ("Good", "Bad", "Passive"):
            err(r, "[%s] is an NPC: Attitude should be Good, Bad or Passive" % sec)
        if typ == "NPC" and not (ini.get(sec, "Respawn") or "").strip():
            err(r, "[%s] is an NPC with no Respawn= (seconds before it comes back: dev\\migrate\\respawn_times.py)" % sec)
        for k, v in items:
            if k is None:
                continue
            if k not in ENTITY_KEYS:
                err(r, "[%s] unknown key %s" % (sec, k))
            elif k in NUMERIC_ENTITY_KEYS and not is_num(v):
                err(r, "[%s] %s=%r is not a number" % (sec, k, v))
            elif k == "Droppable" and v not in ("0", "1"):
                err(r, "[%s] Droppable must be 0 or 1" % sec)
            elif k == "Solid" and v not in ("0", "1"):
                err(r, "[%s] Solid must be 0 or 1" % sec)
            elif k == "Walkable.Data" and (set(v) - {"0", "1"} or not footprint_fits(sec, v)):
                err(r, "[%s] Walkable.Data (its footprint) must be 0s and 1s, 7 cells to 32 pixels of its sprite "
                       "each way" % sec)
            elif k == "Layer" and v.strip().lower() not in ("over", "under"):
                err(r, "[%s] Layer must be Over or Under" % sec)
            elif k == "Drops":
                for d in v.split():
                    m = re.fullmatch(r"(.+),(\d+)-(\d+),(\d+(?:\.\d+)?)", d)
                    if not m:
                        err(r, "[%s] bad drop %r (want Item,min-max,percent)" % (sec, d))
                    elif m.group(1) not in ENTITIES:
                        err(r, "[%s] drop item %r has no sprite" % (sec, m.group(1)))
        check_movement_keys(ini, sec, typ, r)
        if typ not in NPC_TYPES and any(k in ("Hitpoints", "Drops", "Aggressive") for k, _ in items if k):
            warn(r, "[%s] has NPC combat keys but Type=%s" % (sec, typ))
        fv = ini.get(sec, "Food.Value")
        if fv and is_num(fv) and float(fv) > 0 and "Eat" not in (ini.get(sec, "Use.Words") or ""):
            warn(r, "[%s] is food but has no Eat verb" % sec)
    for e in sorted(ENTITIES):
        if re.search(r"[a-z][A-Z]", e) and not e.startswith("Player"):
            warn("sprites\\Entities", "%r looks like an un-renamed CamelCase name (expected underscores)" % e)
    return ini


SHARDS_KEYS = {
    "Shards": {"Start", "Old.Save.Grant", "Cast.Gap", "Shardstone", "Shardstone.Travel", "Chest.Chance", "Chest",
               "Scrolls.Rarer", "Galaith.Seam", "Galaith.Seam.Hours", "Shardgate", "Realm.Cluster",
               "Realm.Cluster.Hours", "Shardgate.Stones", "Shardgate.Level"},
    "Channeling": {"Saving.Per.Level", "Saving.Max", "Min.Cost"},
    "Shardcraft": {"Dismantle.XP", "Dismantle.XP.Min", "Shardstone.XP", "Rare.Chance", "Rare.Chance.Per.Level",
                   "Rare.Min.Value"},
    "Enchant": {"Level", "Shards", "Shards.Per.Value", "XP"},
    "Homestead": {"Bloom.Shards", "Bloom.Hours", "Bloom.Max", "Bloom.Per.Levels", "Bloom.Most"},
    "Spellwright": {"Bolt.Cost", "Burst.Cost", "Frost.Cost", "Ward.Cost", "Power.Exponent", "Far", "Write"},
    "Dismantle": {"Weapon", "Armour", "Scroll"},
    "Remnants": {"Chance", "Count", "Count.Per.Level", "Mob.Chance", "Mob.Min.Level", "Mob.Hitpoints",
                 "Mob.Hitpoints.Per.Level", "Mob.Strength", "Mob.Strength.Per.Level", "Mob.Defence",
                 "Mob.Defence.Per.Level", "Mob.Count", "Mob.Lasts", "Absorb", "Absorb.XP"},
}
UPGRADE_RANGES = {"Damage", "Heal"}             # (min-max; Slow is percent,seconds; Scroll an item; the rest numbers)


DEEP_KEYS = {"Floors", "Shift.Minutes", "Rooms", "Chests", "Secrets", "Traps", "Monsters", "Level.Base",
             "Level.Per.Floor", "Mimic.Chance", "Loot", "Secret.Loot", "Heart.Shards", "Heart.Loot"}


def check_deep():
    """data\\Deep.ini (the Shifting Deep: dsengine/deep.py): known keys, numbers or lo-hi, loot of real items."""
    path = p("data", "Deep.ini")
    if not os.path.exists(path):
        err(rel(path), "missing (dev\\migrate\build_deep.py writes it)")
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    where = rel(path) + " [Deep]"
    for k, v in (ini.section("Deep") or [None, []])[1]:
        if k is None:
            continue
        if k not in DEEP_KEYS:
            err(where, "unknown key %s" % k)
        elif k.endswith("Loot"):
            for entry in v.split():
                bits = entry.split(",")
                if len(bits) != 3 or not is_num(bits[2]) or not all(is_num(x) for x in bits[1].split("-")):
                    err(where, "%s: %r should be item,lo-hi,chance" % (k, entry))
                elif bits[0] not in ENTITIES:
                    err(where, "%s: no item %r" % (k, bits[0]))
        elif not all(is_num(x) for x in v.split("-")):
            err(where, "%s=%r is not a number (or lo-hi)" % (k, v))


def check_shards(entities_ini):
    """data\\Shards.ini: every Shard number. Its keys are known ones and numbers (lo-hi where a range is meant); a
    spell's [Upgrade.<Spell>] is a spell there is, its Scroll.<rank> an item with Spell= and Rank= saying so."""
    path = p("data", "Shards.ini")
    if not os.path.exists(path):
        err(rel(path), "missing (dev\\migrate\\build_shards.py writes it)")
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    spells = Ini(p("data", "Spells.ini"))
    rng = lambda v: all(is_num(x) for x in v.split("-")) and 1 <= len(v.split("-")) <= 2
    for sec, items in ini.sections:
        where = "%s [%s]" % (rel(path), sec)
        if sec.startswith("Upgrade."):
            spell = sec[len("Upgrade."):]
            if spells.section(spell) is None:
                err(where, "no spell [%s] in Spells.ini" % spell)
            for k, v in items:
                if k is None:
                    continue
                key, _, rank = k.rpartition(".")
                if not rank.isdigit() or int(rank) < 2:
                    err(where, "%s should be Key.<rank> (2 and up)" % k)
                elif key == "Scroll":
                    if v not in ENTITIES:
                        err(where, "%s %r has no sprite in sprites\\Entities" % (k, v))
                    elif (entities_ini.get(v, "Spell") or "").strip() != spell or (entities_ini.get(v, "Rank") or "") != rank:
                        err(where, "[%s] in Entities.ini needs Spell=%s and Rank=%s" % (v, spell, rank))
                elif key in UPGRADE_RANGES and not rng(v):
                    err(where, "%s=%r is not min-max" % (k, v))
                elif key == "Slow" and not (len(v.split(",")) == 2 and all(is_num(x) for x in v.split(","))):
                    err(where, "%s=%r is not percent,seconds" % (k, v))
                elif key not in UPGRADE_RANGES and key not in ("Slow", "Freeze.Word") and not is_num(v):
                    err(where, "%s=%r is not a number" % (k, v))
            continue
        if sec == "Terraform":                         # (a Buildables.ini piece each, and its Shards)
            pieces = Ini(p("data", "Buildables.ini"))
            for k, v in items:
                if k is not None and pieces.section(k) is None:
                    err(where, "%s: no such piece in Buildables.ini" % k)
                elif k is not None and not is_num(v):
                    err(where, "%s=%r is not a number" % (k, v))
            continue
        known = SHARDS_KEYS.get(sec)
        if known is None:
            err(where, "unknown section (%s, Upgrade.<Spell>)" % ", ".join(SHARDS_KEYS))
            continue
        for k, v in items:
            if k is None:
                continue
            if k not in known and not (sec == "Shards" and k.startswith("Shardstone.")):
                err(where, "unknown key %s" % k)
            elif not (is_num(v) or (k in ("Chest", "Count", "Mob.Count") and rng(v))):
                err(where, "%s=%r is not a number" % (k, v))
    for sec, items in entities_ini.sections:
        lv = entities_ini.get(sec, "Level")
        if lv is not None and not (is_num(lv) and 1 <= float(lv) <= 25):
            err("data\\Entities.ini [%s]" % sec, "Level=%r should be 1-25" % lv)


def check_carts():
    """data\Carts.ini: each route's points on maps there are, inside them, on one level; two stops at least."""
    path = p("data", "Carts.ini")
    if not os.path.exists(path):
        return
    check_raw(path)
    check_ini_syntax(path)
    sys.path.insert(0, p())
    from dsengine.carts import parse_point
    ini = Ini(path)
    r = rel(path)
    for sec, items in ini.sections:
        stops, levels = 0, set()
        for k, v in items:
            if k is None:
                continue
            if re.fullmatch(r"Point\d+", k):
                pt = parse_point(v)
                if pt is None:
                    err(r, "[%s] %s=%r should be MAP,X,Y[,Stop name]" % (sec, k, v))
                    continue
                if not os.path.exists(p("maps", pt[0] + ".txt")):
                    err(r, "[%s] %s: there's no map %s" % (sec, k, pt[0]))
                if not (1 <= pt[1] <= MAP_W and 1 <= pt[2] <= MAP_H):
                    err(r, "[%s] %s: tile %d,%d isn't on a map" % (sec, k, pt[1], pt[2]))
                levels.add(pt[0].split(",")[2])
                stops += 1 if pt[3] else 0
            elif k in ("Fare", "Wait"):
                if not is_num(v):
                    err(r, "[%s] %s=%r should be a number" % (sec, k, v))
            elif k == "Loop":
                if v.strip() not in ("0", "1"):
                    err(r, "[%s] Loop=%r should be 0 or 1" % (sec, v))
            elif k != "Title":
                warn(r, "[%s] %s: not a key of a cart's route" % (sec, k))
        if stops < 2:
            err(r, "[%s] has %d stops (a point with a name is one): it needs two" % (sec, stops))
        if len(levels) > 1:
            err(r, "[%s] goes over more than one level (%s)" % (sec, ", ".join(sorted(levels))))


def check_digging():
    """data\\Digging.ini: its finds are items, their how many,weight right; a place's Maps= are maps there are."""
    path = p("data", "Digging.ini")
    if not os.path.exists(path):
        return
    check_raw(path)
    check_ini_syntax(path)
    sys.path.insert(0, p())
    from dsengine.digging import parse_maps
    ini = Ini(path)
    r = rel(path)
    maps = {tuple(int(n) for n in f[:-4].split(",")) for f in os.listdir(p("maps")) if re.fullmatch(r"-?\d+,-?\d+,-?\d+\.txt", f)}
    shard_keys = ("Shards.Chance", "Shards", "Shards.Underground.Chance", "Shards.Underground", "Cache.Chance", "Cache")
    for sec, items in ini.sections:
        for k, v in items:                       # (Shards in a dug hole: chances in 100, how many lo-hi)
            if k in shard_keys and not re.fullmatch(r"\d+(\.\d+)?" if k.endswith("Chance") else r"\d+(-\d+)?", v.strip()):
                err(r, "[%s] %s=%r should be %s" % (sec, k, v, "a chance in 100" if k.endswith("Chance") else "lo-hi"))
        if sec == "Digging":
            continue
        if sec != "Finds" and not sec.startswith("Finds."):
            warn(r, "[%s] isn't [Digging], [Finds] or [Finds.<Place>]" % sec)
            continue
        for k, v in items:
            if k is None or (sec != "Finds" and k in ("Maps", "Replace", "Chance")) or k in shard_keys:
                continue
            if k not in ENTITIES:
                err(r, "[%s] %s: no such item" % (sec, k))
            if not re.fullmatch(r"\d+(-\d+)?,\d+(\.\d+)?", v.strip()):
                err(r, "[%s] %s=%r should be how many (1 or 1-3),weight" % (sec, k, v))
        if sec.startswith("Finds."):
            covered = parse_maps(ini.get(sec, "Maps") or "")
            if not covered:
                err(r, "[%s] Maps= says no maps (x,y,z or x1-x2,y1-y2,z, space-separated)" % sec)
            elif not covered & maps:
                err(r, "[%s] Maps= covers no map there is" % sec)


def check_itemracks(entities_ini, skills):
    path = p("data", "ItemRacks.ini")
    if not os.path.exists(path):
        err(rel(path), "missing")
        return set()
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    for sec, items in ini.sections:
        typ = ini.get(sec, "Type")
        if typ not in ("Shop", "Craft"):
            err(r, "[%s] Type must be Shop or Craft" % sec)
        if (ini.get(sec, "Vary.Stock") or "").strip() not in ("", "0", "1"):
            err(r, "[%s] Vary.Stock must be 0 or 1" % sec)
        for k, v in items:
            if k is None or not re.fullmatch(r"Item\d+", k):
                continue
            parts = v.split(",")
            if typ == "Shop":
                if len(parts) != 2 or not (parts[1].strip().isdigit() or parts[1].strip() == "+"):
                    err(r, "[%s] %s=%r should be Name,stock" % (sec, k, v))
                if parts[0] not in ENTITIES:
                    err(r, "[%s] %s item %r has no sprite" % (sec, k, parts[0]))
                elif not entities_ini.get(parts[0], "Value"):
                    warn(r, "[%s] %s has no Value in Entities.ini (can't be priced)" % (sec, parts[0]))
            else:
                if len(parts) not in (3, 4, 5) or not is_num(parts[2]) or                         any(not parts[n].strip().isdigit() for n in range(3, len(parts))):
                    err(r, "[%s] %s=%r should be Product,ingredients,xp[,level[,makes]]" % (sec, k, v))
                    continue
                if parts[0] not in ENTITIES:
                    err(r, "[%s] product %r has no sprite" % (sec, parts[0]))
                ing = parts[1].split()
                if len(ing) % 2:
                    err(r, "[%s] %s ingredients must be name qty pairs" % (sec, k))
                for j in range(0, len(ing) - 1, 2):
                    if ing[j] not in ENTITIES:
                        err(r, "[%s] ingredient %r has no sprite" % (sec, ing[j]))
                    if not ing[j + 1].isdigit():
                        err(r, "[%s] ingredient qty %r not a number" % (sec, ing[j + 1]))
        if typ == "Craft" and ini.get(sec, "Skill") not in skills:
            err(r, "[%s] Skill %r not in Config.ini [Skills] List" % (sec, ini.get(sec, "Skill")))
        if typ == "Craft" and not any(k and k.startswith("Item") for k, _ in items):
            warn(r, "[%s] has no recipes" % sec)
    return {s[0] for s in ini.sections}


def check_saves(skills):
    d = p("saves")
    if not os.path.isdir(d):
        err("Saves", "missing")
        return
    for f in sorted(os.listdir(d)):
        path = os.path.join(d, f)
        if not f.lower().endswith(".ini"):
            continue
        check_raw(path)
        check_ini_syntax(path)
        ini = Ini(path)
        r = rel(path)
        for k in ("Map", "X", "Y", "Hitpoints", "Direction"):
            if ini.get("Player", k) is None:
                err(r, "[Player] %s missing" % k)
        m = ini.get("Player", "Map", "")
        if not os.path.exists(p("maps", m + ".txt")):
            err(r, "map %r doesn't exist" % m)
        for s in skills:
            if ini.get("Skills", s) is None:
                warn(r, "[Skills] %s missing" % s)
        for sec in ("Inventory", "Bank"):
            s = ini.section(sec)
            if s is None:
                err(r, "[%s] missing" % sec)
                continue
            for k, v in s[1]:
                if k is None:
                    continue
                parts = v.split(",")
                if len(parts) != 2 or parts[0] not in ENTITIES or not parts[1].isdigit():
                    err(r, "[%s] %s=%r should be <entity sprite>,<qty>" % (sec, k, v))
        for k, v in (ini.section("Equipment") or ["", []])[1]:
            if k is None:
                continue
            if k in REMOVED_SLOTS:
                warn(r, "[Equipment] %s=%s: the %s slot was removed (8 slots now), so the game won't show it" % (k, v, k))
            elif k not in SLOTS:
                err(r, "[Equipment] %s is not an equipment slot" % k)
            elif v not in ENTITIES:
                err(r, "[Equipment] %s=%r has no sprite" % (k, v))
            elif ENTITIES_INI is not None and ENTITIES_INI.get(v, "Slot") != k:
                err(r, "[Equipment] %s=%s but its Slot is %r" % (k, v, ENTITIES_INI.get(v, "Slot")))
        for k, v in (ini.section("Explored") or ["", []])[1]:
            if k == "Maps":
                for mm in v.split():
                    if not os.path.exists(p("maps", mm + ".txt")):
                        warn(r, "explored map %r doesn't exist" % mm)


def check_minimap():
    path = p("dev", "Minimap Colours.txt")
    check_raw(path)
    seen = set()
    for n, line in enumerate(read_lines(path), 1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            err(rel(path), "line %d: want Name<TAB>R G B" % n)
            continue
        name, col = parts
        seen.add(name)
        if name not in TILES:
            warn(rel(path), "line %d: %r has no tile sprite" % (n, name))
        rgb = col.split()
        if len(rgb) != 3 or not all(c.isdigit() and 0 <= int(c) <= 255 for c in rgb):
            err(rel(path), "line %d: %s colour %r is not 'R G B' 0-255" % (n, name, col))
    for t in sorted(TILES - seen):
        err(rel(path), "no colour for tile %s" % t)


# ------------------------------------------------------------------ help screen data (Gathering.ini, Quests.ini)
def script_lines(name):
    """[(command, [args])] of a script, or [] when missing."""
    path = os.path.join(SCRIPT_DIR, name + ".txt")
    if not os.path.exists(path):
        return []
    out = []
    for line in read_lines(path):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        f = line.split("\t")
        if len(f) >= 2:
            out.append((f[1], f[2:]))
    return out


def script_closure(name, seen=None):
    """The script and every script it reaches with a fixed Goto.Script name."""
    seen = seen if seen is not None else set()
    if name in seen or not script_nonempty(name):
        return seen
    seen.add(name)
    for cmd, args in script_lines(name):
        if cmd == "Goto.Script" and args and "$" not in args[0]:
            script_closure(args[0].strip(), seen)
    return seen


def strip_digits(name):
    return re.sub(r"\d{3}$", "", name)


def find_verb_script(verb, source):
    for n in (verb + " " + source, verb + " " + strip_digits(source)):
        if script_nonempty(n):
            return n
    return None


def find_use_script(tool, source):
    b = strip_digits(source)
    for n in ("Use %s With %s" % (tool, source), "Use %s With %s" % (source, tool),
              "Use %s With %s" % (tool, b), "Use %s With %s" % (b, tool)):
        if script_nonempty(n):
            return n
    return None


def attribute_writes():
    """{attribute: set of values it is set to with '=' ('*' for +/- changes)} over every script."""
    out = {}
    for s in SCRIPTS:
        for cmd, args in script_lines(s):
            if cmd == "Update.Attribute" and len(args) >= 2:
                a, v = args[0].strip(), args[1].strip()
                out.setdefault(a, set()).add(v[1:] if v.startswith("=") else "*")
    return out


GATHER_KEYS = ["Gives", "Source", "Verb", "Tool", "Skill", "Level", "XP", "Where"]


def check_gathering(entities_ini, tiles_ini, skills):
    """data\\Gathering.ini: items, sources, tools and skills exist, and the script for each source gives the items."""
    path = p("data", "Gathering.ini")
    if not os.path.exists(path):
        warn(rel(path), "missing (the Help screen lists gathering from it)")
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    for sec, items in ini.sections:
        where = "%s [%s]" % (r, sec)
        for k in GATHER_KEYS:
            if ini.get(sec, k) is None:
                err(where, "%s missing" % k)
        gives = (ini.get(sec, "Gives") or "").split()
        sources = (ini.get(sec, "Source") or "").split()
        verb = (ini.get(sec, "Verb") or "").strip()
        tool = (ini.get(sec, "Tool") or "").strip().strip('"')
        skill = (ini.get(sec, "Skill") or "").strip().strip('"')
        for g in gives:
            if g not in ENTITIES:
                err(where, "Gives item %r has no sprite in sprites\\Entities" % g)
        if not gives:
            err(where, "Gives is empty")
        if not sources:
            err(where, "Source is empty")
        tools = [t for t in tool.split("/") if t]          # "A/B/C" = any one of them will do
        for t in tools:
            if t not in ENTITIES:
                err(where, "Tool %r has no sprite in sprites\\Entities" % t)
        if skill and skill not in skills:
            err(where, "Skill %r not in Config.ini [Skills] List" % skill)
        for k in ("Level", "XP"):
            if not is_num(ini.get(sec, k)):
                err(where, "%s=%r is not a number" % (k, ini.get(sec, k)))
        for src in sources:
            if src not in TILES and src not in ENTITIES:
                err(where, "Source %r is neither a tile nor an entity sprite" % src)
                continue
            if verb == "Use":
                if not tool:
                    err(where, "Verb=Use needs a Tool")
                    continue
                missing_use = [t for t in tools if not find_use_script(t, src)]
                for t in missing_use:
                    err(where, "no 'Use %s With %s' script" % (t, strip_digits(src)))
                if missing_use:
                    continue
                script = find_use_script(tools[0], src)
            elif verb == "Pickup":
                if src not in ENTITIES or (entities_ini.get(src, "Type") or "MapItem") != "MapItem":
                    err(where, "Verb=Pickup but %r is not a MapItem" % src)
                if src not in gives:
                    warn(where, "picks up %r but Gives doesn't list it" % src)
                continue
            else:
                ini_src = tiles_ini if src in TILES else entities_ini
                words = [w.strip() for w in (ini_src.get(src, "Use.Words") or "").split(",")]
                if verb not in words:
                    err(where, "Verb %r is not in the Use.Words of %s" % (verb, src))
                if verb == "Harvest" and "_Crop" in src:
                    continue                    # (a crop: the server harvests it, dsengine/farming.py, data\Crops.ini)
                script = find_verb_script(verb, src)
                if not script:
                    err(where, "no '%s %s' script" % (verb, strip_digits(src)))
                    continue
            given, checks_tool, checks_skill = set(), False, False
            for s in script_closure(script):
                for cmd, args in script_lines(s):
                    if cmd == "Give.Item" and args:
                        given.add(args[0].strip())
                    if cmd in (">Got.Item", ">Not.Got.Item") and args and args[0].strip() in tools:
                        checks_tool = True
                    if cmd == "Get.Value" and len(args) >= 2 and args[0].strip().upper() in ("SKILL", "LEVEL") \
                            and args[1].strip() == skill:
                        checks_skill = True
            for g in gives:
                if g not in given:
                    err(where, "script %r never gives %s" % (script, g))
            if tool and verb != "Use" and not checks_tool:
                warn(where, "script %r doesn't check for the %s" % (script, tool))
            lvl = ini.get(sec, "Level")
            if skill and is_num(lvl) and float(lvl) > 1 and not checks_skill:
                warn(where, "Level %s but script %r never reads the %s level" % (lvl, script, skill))


def check_spells(entities_ini, skills):
    """data\\Spells.ini: every spell's scroll exists and points back to it (Spell=, Use.Words with Cast), the Effect is
    known, its numbers parse, and its missile / impact animation / sound files exist. Every item with Spell= has one."""
    path = p("data", "Spells.ini")
    if not os.path.exists(path):
        warn(rel(path), "missing (spell scrolls can't be cast)")
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    effects_dir = p("sprites", "Effects")
    effects = {os.path.splitext(f)[0] for f in os.listdir(effects_dir)} if os.path.isdir(effects_dir) else set()
    if "Channeling" not in skills:
        err(rel(path), "there is no Channeling skill in Config.ini [Skills] List")
    spells = set()
    for sec, items in ini.sections:
        where = "%s [%s]" % (rel(path), sec)
        spells.add(sec)
        effect = (ini.get(sec, "Effect") or "Bolt").strip().upper()
        if effect not in ("BOLT", "AREA", "HEAL", "SHIELD", "BOOST", "TELEPORT", "HOME", "GRASP", "INVISIBLE", "SWAP"):
            err(where, "Effect=%r is not Bolt, Area, Heal, Shield, Boost, Teleport, Home, Grasp, Invisible or Swap" % effect)
        scroll = (ini.get(sec, "Scroll") or "").strip()
        if not scroll:
            err(where, "Scroll missing")
        elif scroll not in ENTITIES:
            err(where, "Scroll %r has no sprite in sprites\\Entities" % scroll)
        else:
            if (entities_ini.get(scroll, "Spell") or "").strip() != sec:
                err(where, "[%s] in Entities.ini needs Spell=%s" % (scroll, sec))
            verb = "drink" if (ini.get(sec, "Kind") or "").strip().lower() == "potion" else "learn"   # (a scroll only teaches)
            if verb not in [w.strip().lower() for w in (entities_ini.get(scroll, "Use.Words") or "").split(",")]:
                warn(where, "[%s] has no %s in its Use.Words" % (scroll, verb.title()))
        for k in ("Level", "XP", "Range", "Radius", "Attack", "Defence", "Magic", "Sight", "Duration", "Cost", "Cooldown", "Shards",
                  "Freeze"):
            v = ini.get(sec, k)
            if v is not None and not is_num(v):
                err(where, "%s=%r is not a number" % (k, v))
        for k in ("Damage", "Heal"):
            v = ini.get(sec, k)
            if v is not None and not all(is_num(x) for x in v.split("-")):
                err(where, "%s=%r is not min-max" % (k, v))
        if effect in ("BOLT", "AREA") and ini.get(sec, "Damage") is None:
            err(where, "a %s spell needs Damage=min-max" % effect.title())
        if effect == "HEAL" and ini.get(sec, "Heal") is None:
            err(where, "a Heal spell needs Heal=min-max")
        for k, v in items:                       # (a rank's values live in Shards.ini [Upgrade.<Spell>])
            if k and "." in k and k.rsplit(".", 1)[1].isdigit():
                err(where, "%s: a rank's value belongs in Shards.ini [Upgrade.%s]" % (k, sec))
        fw = ini.get(sec, "Freeze.Word")
        if fw is not None and fw.strip() not in ("frozen", "stunned"):
            err(where, "Freeze.Word=%r is not frozen or stunned" % fw)
        slow = ini.get(sec, "Slow")
        if slow is not None and not (len(slow.split(",")) == 2 and all(is_num(x) for x in slow.split(","))):
            err(where, "Slow=%r is not percent,seconds" % slow)
        missile = (ini.get(sec, "Missile") or "").strip()
        if missile and missile not in effects:
            err(where, "Missile %r is not in sprites\\Effects" % missile)
        impact = (ini.get(sec, "Impact") or "").strip()
        if impact and not all("%s%d" % (impact, i) in effects for i in range(1, 5)):
            err(where, "Impact %r needs %s1..%s4 in sprites\\Effects" % (impact, impact, impact))
        leaves = (ini.get(sec, "Leaves") or "").strip()
        if leaves and leaves not in ENTITIES:
            err(where, "Leaves %r has no sprite in sprites\\Entities" % leaves)
        sk = (ini.get(sec, "Skill") or "Channeling").strip()
        if sk not in skills:
            err(where, "Skill %r is not in Config.ini [Skills] List" % sk)
        sound = (ini.get(sec, "Sound") or "").strip()
        if sound and sound not in SOUNDS:
            err(where, "Sound %r is not in Sounds" % sound)
        m = (ini.get(sec, "Map") or "").replace(" ", "")
        if m and not os.path.exists(p("maps", m + ".txt")):
            err(where, "Map %r doesn't exist" % m)
    for sec, items in entities_ini.sections:
        sp = (entities_ini.get(sec, "Spell") or "").strip()
        if sp and sp not in spells:
            err("data\\Entities.ini [%s]" % sec, "Spell=%s is not in data\\Spells.ini" % sp)
    for name in ("Fight1", "Fight2", "Fight3", "Crit", "Block", "Hurt", "Death", "Miss", "SpellCast"):
        if name not in SOUNDS:
            warn("Sounds", "%s.wav (combat) is missing: run dev\\migrate\\build_sounds.py" % name)
    for name in ("Hit1", "Crit1", "Heal1", "Miss", "Puff1", "Slash1", "Hurt_Top", "Hurt_Left"):
        if name not in effects:
            warn("sprites\\Effects", "%s.png is missing: run dev\\migrate\\build_effects.py" % name)


def QUEST_SKILLS():
    """The skills there are (Config.ini [Skills] List)."""
    return [s.strip() for s in (Ini(p("data", "Config.ini")).get("Skills", "List", "") or "").split(",") if s.strip()]


def check_quests():
    """data\\Quests.ini: the giver exists, the attribute (and every $Attribute in the stage texts) is set by a
    script, there is a Stage for every value below Done, and scripts set each stage value and Done."""
    path = p("data", "Quests.ini")
    if not os.path.exists(path):
        warn(rel(path), "missing (the Help screen lists quests from it)")
        return
    check_raw(path)
    check_ini_syntax(path)
    ini = Ini(path)
    r = rel(path)
    writes = attribute_writes()
    for sec, items in ini.sections:
        where = "%s [%s]" % (r, sec)
        giver = ini.get(sec, "Giver")
        if not giver:
            err(where, "Giver missing")
        elif giver not in ENTITIES:
            err(where, "Giver %r has no sprite in sprites\\Entities" % giver)
        attr = ini.get(sec, "Attribute")
        if not attr:
            err(where, "Attribute missing")
            continue
        if attr not in writes:
            err(where, "attribute %r is never set by a script (Update.Attribute)" % attr)
        done = ini.get(sec, "Done")
        if not (done and done.isdigit()):
            err(where, "Done=%r should be a whole number" % done)
            continue
        if ini.get(sec, "Stage0") is None:
            err(where, "Stage0 missing (use Stage0= to hide the quest until it starts)")
        for n in range(1, int(done)):
            if ini.get(sec, "Stage%d" % n) is None:
                err(where, "Stage%d missing (Done=%s)" % (n, done))
        for k, v in items:
            if k is None:
                continue
            m = re.fullmatch(r"Stage(\d+)", k)
            if m:
                n = m.group(1)
                if int(n) >= int(done):
                    warn(where, "%s is never shown (Done=%s)" % (k, done))
                if int(n) > 0 and attr in writes and n not in writes[attr] and "*" not in writes[attr]:
                    err(where, "no script sets %s to %s (=%s)" % (attr, n, n))
                for var in re.findall(r"\$([A-Za-z_][A-Za-z0-9_.]*[A-Za-z0-9_])", v):
                    if var not in writes:
                        err(where, "%s uses $%s but no script sets attribute %s" % (k, var, var))
            elif re.fullmatch(r"Marker(\d+)", k):
                # Marker<N>=<place ID> or <map> <tile x> <tile y>[;...]: minimap marks while the attribute is N
                for part in v.split(";"):
                    bits = part.split()
                    if len(bits) == 1:
                        if place_of(bits[0]) is None:
                            err(where, "%s: %r is not a place ID (an Id line on a map, or an Id=)" % (k, bits[0]))
                    elif len(bits) != 3 or not re.fullmatch(r"-?\d+,-?\d+,-?\d+", bits[0]) or not all(b.isdigit() for b in bits[1:]):
                        err(where, "%s: %r is not '<map> <tile x> <tile y>'" % (k, part))
                    elif not os.path.exists(p("maps", bits[0] + ".txt")):
                        err(where, "%s: map %s doesn't exist" % (k, bits[0]))
                    elif not (1 <= int(bits[1]) <= MAP_W and 1 <= int(bits[2]) <= MAP_H):
                        err(where, "%s: tile %s,%s is off the map" % (k, bits[1], bits[2]))
            elif k == "Type":                   # the main story (the game's quests.py)
                if v not in ("Main", "Side"):
                    err(where, "Type must be Main or Side, not %r" % v)
            elif k in ("Chapter", "Requires.Level"):
                if not v.isdigit():
                    err(where, "%s must be a whole number, not %r" % (k, v))
            elif k == "Requires.Quests":
                for q in [x.strip() for x in v.split(";") if x.strip()]:
                    if ini.section(q) is None:
                        err(where, "Requires.Quests: no quest called %r" % q)
                    elif q == sec:
                        err(where, "Requires.Quests: a quest can't need itself")
            elif k == "Requires.Skills":
                words = v.replace(",", " ").split()
                if len(words) % 2 or not all(w.isdigit() for w in words[1::2]):
                    err(where, "Requires.Skills should be pairs of skill and level, e.g. Woodcutting 10, Potion Making 5")
            elif k == "Reward.Shards":
                if not v.strip().isdigit():
                    err(where, "Reward.Shards=%r should be a whole number of Shards" % v)
            elif k == "Reward.XP":                       # (skill xp pairs, given once when it's done)
                w = v.replace(",", " ").split()
                if not w or len(w) % 2 or not all(is_num(x) for x in w[1::2]):
                    err(where, "Reward.XP=%r should be pairs of skill and xp, e.g. Strength 3 Defence 3" % v)
                for sk in w[::2]:
                    if sk.lower() not in {s.lower() for s in QUEST_SKILLS()}:
                        err(where, "Reward.XP: no skill %r in Config.ini [Skills] List" % sk)
            elif k == "Reward.Items":                    # (item how-many pairs, given once when it's done)
                bits = v.split()
                if len(bits) % 2 or not all(b.isdigit() for b in bits[1::2]):
                    err(where, "Reward.Items=%r should be pairs of item and how many" % v)
                for item in bits[0::2]:
                    if item not in ENTITIES:
                        err(where, "Reward.Items: no such item %r" % item)
            elif k not in ("Giver", "Attribute", "Done"):
                warn(where, "unknown key %s" % k)
        if attr in writes and done not in writes[attr] and "*" not in writes[attr]:
            err(where, "no script sets %s to Done=%s, so the quest can never be completed" % (attr, done))


ENGINE_RACKS = {"SHOP-Tavern"}      # opened by the server itself (the innkeeper: dsengine/tavern.py)


def wave_scripts():
    """The scripts data\\Waves.ini's attacks run at the end (On.Win.Script, On.Lose.Script)."""
    out = set()
    for ln in read_lines(p("data", "Waves.ini")):
        k, _, v = ln.partition("=")
        if k.strip().lower() in ("on.win.script", "on.lose.script") and v.strip():
            out.add(v.strip())
    return out


WAVE_SCRIPTS = set()


def check_rack_use(racks):
    """Every shop and craft list should be opened by some script (an NPC, a station or a skill click)."""
    opened = set(ENGINE_RACKS)
    for s in SCRIPTS:
        for cmd, args in script_lines(s):
            if cmd == "Display.Item.Rack" and len(args) >= 3:
                opened.add(args[2].strip())
    for rack in sorted(racks):
        if rack not in opened:
            warn("data\\ItemRacks.ini", "[%s] is never opened by a script (Display.Item.Rack)" % rack)


# ------------------------------------------------------------------ world reachability and locks
LADDER_FALLBACK = {"Ladder001": (1,), "Ladder004": (1,), "Ladder002": (-1,), "Ladder005": (-1,), "Ladder006": (-1,),
                   "Ladder007": (-1,), "Ladder003": (1, -1), "Ladder008": (1,), "Ladder009": (-1,), "Stairs001": (1,),
                   "Stairs002": (-1,)}
_sprite_size = {}


def sprite_size(name):
    if name not in _sprite_size:
        path = p("sprites", "Entities", name + ".png")
        if os.path.exists(path):
            from common import read_bmp
            w, h, _ = read_bmp(path)
            _sprite_size[name] = (w, h // 2)
        else:
            _sprite_size[name] = (32, 32)
    return _sprite_size[name]


def entity_tile(name, x, y):
    """The tile (0-based) under an entity's feet (the middle of its sprite's bottom row)."""
    w, h = sprite_size(name)
    return int((x + w / 2) // 32), int((y + h - 1) // 32)


class World:
    """Walking graph of every map at the resolution of Walkable.Data (7x7 cells per tile): walkable cells, map edges
    and ladders (any walkable cell of a ladder tile leads to the same tile one level up/down). flood() starts from
    tiles (the start position, fixed Teleport targets) and returns the set of (map, tile x, tile y) it reaches."""
    R = 7

    def __init__(self, tiles_ini):
        self.cells, self.ents = {}, {}
        for f in os.listdir(p("maps")):
            m = re.fullmatch(r"(-?\d+),(-?\d+),(-?\d+)\.txt", f)
            if not m:
                continue
            name = f[:-4]
            lines = read_lines(p("maps", f))
            self.cells[name] = [[ground_key(c) for c in r.split(":")] for r in lines[:MAP_H]]
            self.ents[name] = [l.split("	") for l in lines[MAP_H:] if l.strip()]
        self.walk, self.ladder = {}, {}
        for name, cells in self.cells.items():
            for row in cells:
                for t in row:
                    if t not in self.walk:
                        self.walk[t] = tile_walk(tiles_ini, t)
                        base, decor = key_parts(t)
                        words = [w.strip() for n in (base, decor) if n
                                 for w in (tiles_ini.get(n, "Use.Words") or "").split(",")]
                        dz = tuple(d for d, v in ((1, "Climb Up"), (-1, "Climb Down")) if v in words)
                        self.ladder[t] = dz or LADDER_FALLBACK.get(base, ())

    def tile(self, m, tx, ty):
        cells = self.cells.get(m)
        if cells is None or not (0 <= tx < MAP_W and 0 <= ty < MAP_H) or ty >= len(cells) or tx >= len(cells[ty]):
            return None
        return cells[ty][tx]

    def ok(self, m, sx, sy):
        t = self.tile(m, sx // self.R, sy // self.R)
        return t is not None and self.walk.get(t, "1" * 49)[(sy % self.R) * self.R + sx % self.R] == "1"

    def neighbours(self, m, sx, sy):
        R, W, H = self.R, MAP_W * self.R, MAP_H * self.R
        mx, my, mz = (int(v) for v in m.split(","))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny, nm = sx + dx, sy + dy, m
            if nx < 0:
                nm, nx = "%d,%d,%d" % (mx - 1, my, mz), W - 1
            elif nx >= W:
                nm, nx = "%d,%d,%d" % (mx + 1, my, mz), 0
            elif ny < 0:
                nm, ny = "%d,%d,%d" % (mx, my - 1, mz), H - 1
            elif ny >= H:
                nm, ny = "%d,%d,%d" % (mx, my + 1, mz), 0
            yield nm, nx, ny
        for dz in self.ladder.get(self.tile(m, sx // R, sy // R), ()):
            for cx in range(R):
                for cy in range(R):
                    yield "%d,%d,%d" % (mx, my, mz + dz), (sx // R) * R + cx, (sy // R) * R + cy

    def tile_neighbours(self, m, tx, ty):
        mx, my, mz = (int(v) for v in m.split(","))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yield m, tx + dx, ty + dy

    def flood(self, seeds, closed=frozenset()):
        """seeds and closed are (map, tile x, tile y); returns the tiles reached."""
        R = self.R
        seen = set()
        todo = []
        for m, tx, ty in seeds:
            if (m, tx, ty) in closed:
                continue
            todo += [(m, tx * R + cx, ty * R + cy) for cx in range(R) for cy in range(R) if self.ok(m, tx * R + cx, ty * R + cy)]
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            for nb in self.neighbours(*n):
                if nb not in seen and (nb[0], nb[1] // R, nb[2] // R) not in closed and self.ok(*nb):
                    todo.append(nb)
        return {(m, sx // R, sy // R) for m, sx, sy in seen}


def reachable_entity(reach, m, tile):
    """An entity counts as reachable when its tile, or a tile next to it, can be walked to."""
    x, y = tile
    return any((m, x + dx, y + dy) in reach for dx in (-1, 0, 1) for dy in (-1, 0, 1))


def quest_needs(quests_ini, writes):
    """{attribute: (quest name, giver, done, {entity names the quest needs})} from Quests.ini and the scripts:
    the giver, the items checked or taken (>Got.Item, Take.Item) by any script that sets the quest attribute or an
    attribute shown in its stage texts, and the NPCs whose Kill script sets one of those attributes."""
    out = {}
    for sec, items in quests_ini.sections:
        attr, giver, done = quests_ini.get(sec, "Attribute"), quests_ini.get(sec, "Giver"), quests_ini.get(sec, "Done")
        if not attr:
            continue
        attrs = {attr}
        for k, v in items:
            if k and k.startswith("Stage"):
                attrs |= set(re.findall(r"\$([A-Za-z_][A-Za-z0-9_]*)", v))
        need = {giver} if giver else set()
        for s in SCRIPTS:
            sets = any(cmd == "Update.Attribute" and a and a[0].strip() in attrs for cmd, a in script_lines(s))
            if not sets:
                continue
            m = re.fullmatch(r"Kill (.+)", s)
            if m:
                need.add(m.group(1))
            for cmd, a in script_lines(s):
                if cmd in (">Got.Item", "Take.Item") and a and "$" not in a[0] and a[0].strip() != "Gold_Coin(s)":
                    need.add(a[0].strip())
        out[attr] = (sec, giver, int(done) if done and done.isdigit() else None, need)
    return out


def other_sources():
    """Items the player can get without finding them on a map: shop stock, crafted, NPC drops, Give.Item."""
    src = set()
    racks = Ini(p("data", "ItemRacks.ini"))
    for sec, items in racks.sections:
        typ = racks.get(sec, "Type")
        for k, v in items:
            if k and re.fullmatch(r"Item\d+", k):
                parts = v.split(",")
                if typ == "Craft" or (len(parts) > 1 and parts[1].strip() not in ("0", "")):
                    src.add(parts[0])
    ents = Ini(p("data", "Entities.ini"))
    for sec, items in ents.sections:
        for d in (ents.get(sec, "Drops") or "").split():
            src.add(d.split(",")[0])
    for s in SCRIPTS:
        for cmd, a in script_lines(s):
            if cmd == "Give.Item" and a:
                src.add(a[0].strip())
    return src


def check_world(tiles_ini, entities_ini, skills):
    """Locks: their conditions, and reachability. With every lock open, every map entity should be reachable from
    the start (or a fixed Teleport target). For each lock, what lies only behind it is worked out (flood fill with
    just that lock shut); it's a problem when a quest's giver is only reachable through a lock that needs that
    quest's attribute, when a lock needs a quest to be done and something the quest needs is only behind it, or when
    a lock needs $Item.X and X is only found behind it (and can't be bought, crafted, dropped or given)."""
    writes = attribute_writes()
    for m, x, y, cond, msg, where in LOCKS:
        check_condition(where, cond, skills, entities_ini, writes)
    world = World(tiles_ini)
    cfg = Ini(p("data", "Config.ini"))
    seeds = []
    try:
        sx, sy = float(cfg.get("Gameplay", "Start.X")), float(cfg.get("Gameplay", "Start.Y"))
        seeds.append((cfg.get("Gameplay", "Start.Map"), int((sx + 15) // 32), int((sy + 28) // 32)))
    except (TypeError, ValueError):
        pass
    for s in SCRIPTS:
        for cmd, a in script_lines(s):
            if cmd == "Teleport" and len(a) >= 2 and "$" not in a[0] + a[1]:
                pl = place_of(a[0]) if "," not in a[0] else None
                if pl is not None:                      # a place: its tile (and its map, unless one is given)
                    seeds.append((a[1].strip() if a[1].strip() not in ("", "-") else pl[1], pl[2] - 1, pl[3] - 1))
                    continue
                try:
                    tx, ty = (int(v) for v in a[0].split(","))
                except ValueError:
                    continue
                seeds.append((a[1].strip(), (tx + 16) // 32, (ty + 31) // 32))
    lock_tiles = {(m, x - 1, y - 1) for m, x, y, _, _, _ in LOCKS}
    open_reach = world.flood(seeds)
    placements = {}           # entity name -> [(map, tile)]
    for m, ents in world.ents.items():
        for e in ents:
            if e[0] in ("MapItem", "StaticObject") + NPC_TYPES and len(e) >= 4 and is_num(e[2]) and is_num(e[3]):
                placements.setdefault(e[1], []).append((m, entity_tile(e[1], float(e[2]), float(e[3]))))
    swimmers = {n for n in placements if ENTITIES_INI is not None and (ENTITIES_INI.get(n, "Swims") or "") == "1"}
    for name, where in sorted(placements.items()):
        for m, t in where:
            if name not in swimmers and not reachable_entity(open_reach, m, t):   # (a swimmer comes ashore)
                warn("maps\\%s.txt" % m, "%s at tile %d,%d can't be reached from the start (even with every lock open)"
                     % (name, t[0] + 1, t[1] + 1))
    for m, x, y, cond, msg, where in LOCKS:
        if not any(nb in open_reach for nb in world.tile_neighbours(m, x - 1, y - 1)):
            warn(where, "nothing next to the lock at %d,%d can be reached" % (x, y))
    quests = quest_needs(Ini(p("data", "Quests.ini")), writes)
    sources = other_sources()
    for m, x, y, cond, msg, where in LOCKS:
        shut = world.flood(seeds, closed=frozenset({(m, x - 1, y - 1)}))
        behind = {n for n in open_reach - shut}

        def only_behind(name):
            ps = placements.get(name, [])
            if not ps:
                return False
            if all(not reachable_entity(shut, pm, pt) for pm, pt in ps):
                return True
            return False
        branch_problems = []
        for branch in parse_condition(cond):
            probs = []
            for lhs, op, rhs in branch:
                if op is None:
                    continue
                v = VAR_RE.findall(lhs)
                kind, _, name = (v[0][1:].partition(".") if v else ("", "", ""))
                if kind == "Attr" and name in quests:
                    qname, giver, done, need = quests[name]
                    if giver and only_behind(giver):
                        probs.append("the giver of %r (%s) is only reachable through it" % (qname, giver))
                    val = float(rhs) if is_num(rhs) else None
                    finished = done is not None and val is not None and (
                        (op in (">=", "=") and val >= done) or (op == ">" and val >= done - 1))
                    if finished:
                        stuck = sorted(n for n in need if n != giver and only_behind(n))
                        if stuck:
                            probs.append("it needs %r done, but %s %s only behind it"
                                         % (qname, ", ".join(stuck), "is" if len(stuck) == 1 else "are"))
                elif kind == "Item" and op in (">=", ">", "=") and only_behind(name) and name not in sources:
                    probs.append("it needs a %s, which is only found behind it" % name)
            branch_problems.append(probs)
        if branch_problems and all(branch_problems):
            warn(where, "lock %d,%d (%s) can't be opened: %s" % (x, y, cond, "; or ".join("; ".join(b) for b in branch_problems)))
        REPORT.append("%s: lock at %d,%d [%s] keeps %d tile(s) behind it" % (m, x, y, cond, len(behind)))


REPORT = []


def main():
    quiet = "--quiet" in sys.argv
    tiles_ini = check_tiles()
    entities_ini = check_entities()
    skills = check_config(tiles_ini)
    global ENTITIES_INI, WAVE_SCRIPTS
    ENTITIES_INI = entities_ini
    WAVE_SCRIPTS = wave_scripts()
    check_equipment(entities_ini, skills)
    racks = check_itemracks(entities_ini, skills)
    triggers = set()
    for f in sorted(os.listdir(p("maps"))):
        if f.lower().endswith(".txt"):
            check_map(p("maps", f), entities_ini, tiles_ini, err)
            for line in read_lines(p("maps", f))[MAP_H:]:
                if line.startswith("Trigger\t"):
                    triggers.add(line.split("\t")[1])
    test_dir = p("maps", "Test")
    if os.path.isdir(test_dir):
        for f in sorted(os.listdir(test_dir)):
            if f.lower().endswith(".txt"):
                # test maps are hand-made engine tests, so their problems are warnings only
                check_map(os.path.join(test_dir, f), entities_ini, tiles_ini, warn)
    refs = check_scripts(skills, racks)
    check_script_reachability(refs, triggers)
    check_unique_ids()
    check_place_refs()
    check_saves(skills)
    check_minimap()
    check_gathering(entities_ini, tiles_ini, skills)
    check_quests()
    check_spells(entities_ini, skills)
    check_shards(entities_ini)
    check_deep()
    check_digging()
    check_carts()
    check_rack_use(racks)
    check_world(tiles_ini, entities_ini, skills)
    if not quiet:
        for line in REPORT:
            print("INFO    " + line)
        for w in WARNINGS:
            print("WARNING " + w)
    for e in ERRORS:
        print("ERROR   " + e)
    print("\n%d error(s), %d warning(s)" % (len(ERRORS), len(WARNINGS)))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
