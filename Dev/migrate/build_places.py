"""Named places: tiles with an ID, which scripts and quests use instead of coordinates (the game's places.py).

A map line  Id<TAB>Name<TAB>TileX<TAB>TileY  (1-25, 1-21, as a Trigger's) names that tile. Names are unique across the
whole world (and don't clash with any Id= on a map line: an NPC's, an item's or an object's, which are places too), so a
name alone says which map. Scripts take a name wherever they take coordinates (Teleport Isle_Landing, Change.Tile
Old_Well Well002) and Quests.ini markers can be names (Marker1=Milkmaid_Farm;Hen_Nests).

The builders register the places they use with tile() (or feet(): where an entity drawn at pixel x,y stands) and use
the name it returns; write_ids() (a step after the maps are built) puts their Id lines in the map files. Id lines you
add yourself (in the Map Editor) are left alone: Dev\\migrate\\place_ids.txt lists the ones the builders wrote, so a
rebuild only takes out or moves its own."""
import os
import re

from common import MAP_H, p, read_lines, write_lines

PLACES = {}         # name -> (map, tile x, tile y), 1-based
LOG = p("Dev", "migrate", "place_ids.txt")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def tile(name, map_name, tx, ty):
    """Registers the place name at tile tx,ty (1-based) of map_name; returns name (to write in a script or marker)."""
    if not NAME_RE.match(name):
        raise ValueError("place ID %r: a letter first, then letters, digits, _ . or -" % name)
    want = (map_name, int(tx), int(ty))
    if PLACES.get(name, want) != want:
        raise ValueError("place ID %r is both %s and %s" % (name, PLACES[name], want))
    PLACES[name] = want
    return name


def feet(name, map_name, x, y):
    """The place where something drawn at pixel x,y (a 32 x 32 sprite's top-left: the player) stands."""
    return tile(name, map_name, (int(x) + 16) // 32 + 1, (int(y) + 31) // 32 + 1)


def marker(name, spec):
    """A quest marker "<map> <x> <y>" registered as the place name."""
    m, tx, ty = spec.split()
    return tile(name, m, int(tx), int(ty))


def pixels(name):
    """(map, x, y): the top-left pixel of the place's tile (where Teleport puts the player)."""
    m, tx, ty = PLACES[name]
    return m, (tx - 1) * 32, (ty - 1) * 32


def id_line(name):
    m, tx, ty = PLACES[name]
    return "Id\t%s\t%d\t%d" % (name, tx, ty)


def write_ids():
    """Each map's Id lines as the builders want them: new ones added, moved or dropped ones of theirs updated or taken
    out (only the lines this step wrote before: see place_ids.txt). Re-running changes nothing."""
    old = {}                                               # map -> {line} written last time
    if os.path.exists(LOG):
        for l in read_lines(LOG):
            if l and not l.startswith("//"):
                m, line = l.split("\t", 1)
                old.setdefault(m, set()).add(line)
    want = {}
    for name in sorted(PLACES):
        want.setdefault(PLACES[name][0], []).append(id_line(name))
    changed, problems = [], []
    for m in sorted(set(old) | set(want)):
        path = p("Maps", m + ".txt")
        if not os.path.exists(path):
            problems.append("place IDs for map %s, which doesn't exist: %s" % (m, ", ".join(want.get(m, []))))
            continue
        lines = read_lines(path)
        while lines and lines[-1] == "":
            lines.pop()
        rows, ents = lines[:MAP_H], lines[MAP_H:]
        mine = set(want.get(m, []))
        drop = [e for e in ents if e in old.get(m, set()) and e not in mine]
        ents = [e for e in ents if e not in drop]
        theirs = {e.split("\t")[1] for e in ents if e.startswith("Id\t") and e not in old.get(m, set())}
        add = []
        for line in want.get(m, []):
            name = line.split("\t")[1]
            if name in theirs:
                problems.append("%s: your own Id line for %s is kept (the builders wanted %s)" % (m, name, line))
            elif line not in ents:
                add.append(line)
        if (drop or add) and write_lines(path, rows + ents + add):   # (a map already right isn't written again: the
            changed.append("Maps\\%s.txt" % m)                       # build's own maps stay as it wrote them)
    log = ["// Id lines Dev\\migrate\\build_places.py wrote into the maps (map<TAB>line): a rebuild only changes these"]
    log += ["%s\t%s" % (PLACES[n][0], id_line(n)) for n in sorted(PLACES)]
    if write_lines(LOG, log):
        changed.append("Dev\\migrate\\place_ids.txt")
    for pr in problems:
        print("  PLACES:", pr)
    return changed
