"""What the Maps page works out that isn't drawing: a level's maps as one big map (which map a tile is on), a set of
tiles laid out over a dragged rectangle (a roof, a rug, the walls round a room, a fence), the look-alikes a tile can
be swapped for, the diagonal pieces that smooth a coast's corners, and the one tile that stands for a whole texture."""
import random
import re

from .project import parse_map_name, HOMESTEAD_MAP


def level_slots(project, z, extra=()):
    """{(x, y): map name} of level z: its saved maps, and extra (new ones not saved yet)."""
    out = {}
    for m in list(project.maps()) + list(extra):
        p = parse_map_name(m)
        if p and p[2] == z:
            out[p[:2]] = m
    return out


def own_level(z):
    """A level of its own (CLAUDE.md: the arena 10, the dragon's lair -9, the Shardrealm -10, the Shifting Deep -11
    down, homesteads 1000+): nothing joins it to the world. The others lie under or over it, in its frame."""
    return z >= 10 or z <= -9


def slot_name(x, y, z):
    return HOMESTEAD_MAP if z == 1000 else "%d,%d,%d" % (x, y, z)


# ----- textures: every tile painted from one big texture (Tiles.ini Texture=: a range's peaks, the forest canopy)
# looks the same in the game, so the palette shows one of them
def stand_ins(project):
    """{tile: the tile the palette shows for it} for the tiles that share a texture with others."""
    tex = project.tile_values("Texture")
    groups = {}
    for t in project.tiles():
        v = tex.get(t.lower())
        if v:
            groups.setdefault(v, []).append(t)
    out = {}
    for v, names in groups.items():
        if len(names) > 1:
            for n in names:
                out[n] = names[0]
    return out


def texture_count(project, name):
    v = project.tile_values("Texture").get(name.lower())
    return sum(1 for t, x in project.tile_values("Texture").items() if x == v) if v else 1


# ----- look-alikes: Grass001 and Pebbles002 go anywhere the other would (the same stem, walked on the same way, used
# the same way, not a piece of a set or a frame of an animation): painting can mix them in at random
def look_alikes(project, name):
    stem = re.sub(r"\d+$", "", name)
    if not name or stem == name:
        return [name]
    walk, words, piece = (project.tile_values(k) for k in ("Walkable.Data", "Use.Words", "Piece"))
    in_sets = {n.lower() for st in project.tile_sets() for n in st[3] if n}
    diag = {n.lower() for pieces in shore_sets(project).values() for n in pieces}

    def key(t):
        low = t.lower()
        return walk.get(low, ""), words.get(low, ""), project.is_decor(t), project.is_under(t)
    if name.lower() in in_sets | diag or piece.get(name.lower()):
        return [name]
    pat = re.compile(re.escape(stem) + r"\d+$")
    out = [t for t in project.tiles() if pat.match(t) and not project.is_tile_frame(t) and
           t.lower() not in in_sets | diag and not piece.get(t.lower()) and key(t) == key(name)]
    return out if name in out else [name]


def mixed(project, name):
    return random.choice(look_alikes(project, name))


# ----- a set laid out over a rectangle (data\TileSets.ini, each piece named by its Tiles.ini Piece=)
def _pick(i, n, k):
    """Which of k pieces in a row (an end, the middles, the other end) goes at i of n: the ends at the ends; with five
    or more, the middle one in the middle and the ones either side stretched (a roof's slopes either side of its
    ridge)."""
    if n == 1:
        return k // 2
    if i == 0:
        return 0
    if i == n - 1:
        return k - 1
    if k < 5:
        return min(1, k - 1)
    c = (n - 1) // 2
    return 1 if i < c else (k // 2 if i == c else k - 2)


def set_kind(project, st):
    """How a set is laid out (TileSets.ini Kind=: Stretch, Rug, Join, Shore, Set)."""
    return (project.set_info(st[0]).get("Kind") or "Set").strip().capitalize() if st else ""


def drags(project, brush):
    """Is brush laid out by dragging (a set that stretches, or pieces that join)?"""
    st = project.tile_set_of(brush) if brush else None
    return set_kind(project, st) in ("Stretch", "Rug", "Join")


def whole(project, name):
    """A piece of one thing more than a tile big (TileSets.ini Kind=Whole: a bed's head and foot, a double bed's
    four): [(dx, dy, piece)] of every piece, from name's own cell; [] for anything else. It goes down, and comes up,
    whole."""
    st = project.tile_set_of(name) if name else None
    if not st or set_kind(project, st) != "Whole":
        return []
    _, _, cols, names = st
    at = names.index(next(n for n in names if n.lower() == name.lower()))
    return [(i % cols - at % cols, i // cols - at // cols, n) for i, n in enumerate(names) if n]


def joins(project, brush):
    """Is brush a piece of a set that joins its neighbours (a fence, a palisade, a town wall)?"""
    return bool(brush) and set_kind(project, project.tile_set_of(brush)) == "Join"


def shape(project, brush, w, h):
    """brush's set laid over a w x h rectangle: rows of tile names (None leaves that cell as it is), or None when brush
    isn't a piece of a set that stretches (a roof, a rug, the walls round a room) or it's one tile. (A Join set's
    pieces are chosen by lay_joins instead.)"""
    st = project.tile_set_of(brush)
    if not st or (w, h) == (1, 1) or set_kind(project, st) not in ("Stretch", "Rug"):
        return None
    _, _, cols, names = st
    rows = (len(names) + cols - 1) // cols
    grid = [names[r * cols:(r + 1) * cols] for r in range(rows)]
    pieces = {n: project.tiles_ini.get(n, "Piece", "").lower() for n in names if n}

    def stretch(g):
        return [[g[_pick(j, h, len(g))][_pick(i, w, len(g[0]))] for i in range(w)] for j in range(h)]
    if cols == 4 and rows == 4 and any("runner" in p for p in pieces.values()):
        # (a rug: its 3x3 corners, edges and middle; a runner down the last column, one across the last row)
        if w == 1:
            return [[grid[_pick(j, h, 3)][3]] for j in range(h)]
        if h == 1:
            return [[grid[3][_pick(i, w, 3)] for i in range(w)]]
        return stretch([r[:3] for r in grid[:3]])
    find = lambda start: next((n for n, p in pieces.items() if p.startswith(start)), None)
    if find("corner: east and south"):
        # (a fence: round the rectangle's edge, nothing inside it)
        ew, ns = find("east-west"), find("north-south")
        if w == 1:
            return [[ns] for _ in range(h)]
        if h == 1:
            return [[ew] * w]
        out = [[None] * w for _ in range(h)]
        for i in range(w):
            out[0][i] = out[h - 1][i] = ew
        for j in range(h):
            out[j][0] = out[j][w - 1] = ns
        out[0][0], out[0][w - 1] = find("corner: east and south"), find("corner: west and south")
        out[h - 1][0], out[h - 1][w - 1] = find("corner: north and east"), find("corner: north and west")
        return out
    body = []
    for r in grid:                                  # (the rows before a gap: after it, pieces put down by hand - the
        if len(r) != 3 or not all(r):               #  inner corners and ends of a room that isn't a rectangle)
            break
        body.append(r)
    if cols == 3 and len(body) >= 3:
        return stretch(body)                        # (a roof, the walls round a room: corners, edges, the middle)
    return None


# ----- pieces that join (TileSets.ini Kind=Join; each piece's Tiles.ini Joins=: the sides it joins, * any, - none;
# Below=: the tile drawn in the cell under it, a town wall's face): each cell takes the piece that joins what's round it
SIDES = (("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0))


def join_pieces(project, brush):
    """{piece: the sides it joins ("" none, "*" any)}, {piece: the tile under it} of brush's set."""
    st = project.tile_set_of(brush)
    names = [n for n in (st[3] if st else []) if n]
    out, below = {}, {}
    for n in names:
        j = project.tiles_ini.get(n, "Joins", "").strip().upper()
        out[n] = "" if j == "-" else j
        b = project.tiles_ini.get(n, "Below", "").strip()
        if b:
            below[n] = b
    return out, below


def join_pick(pieces, mask, below_of=None):
    """The piece for a cell joined on the sides in mask: the one that joins just those, else one that joins any
    (a tower), else the straight one along them (an end), else the post."""
    want = set(mask)
    exact = [n for n, j in pieces.items() if j != "*" and set(j) == want]
    if exact:
        return exact[0]
    anyway = [n for n, j in pieces.items() if j == "*"]
    if "S" in want and ("N" in want or {"E", "W"} <= want):            # (a wall running on south has no tower's face
        through = next((n for n, j in pieces.items() if set(j) == {"N", "S"}), None)   # cutting it: a T keeps the straight piece)
        if through and not (below_of or {}).get(through):
            return through
    if anyway and want:
        return anyway[0]
    if want <= {"E", "W"} and want:
        return next((n for n, j in pieces.items() if set(j) == {"E", "W"}), None)
    if want <= {"N", "S"} and want:
        return next((n for n, j in pieces.items() if set(j) == {"N", "S"}), None)
    if anyway:
        return anyway[0]
    best = sorted(pieces.items(), key=lambda kv: (len(set(kv[1]) ^ want), kv[0]))
    return best[0][0] if best else None


def lay_joins(project, brush, cells, get, put, erased=()):
    """brush's set laid on cells (tile x, y), each the piece that joins its neighbours, and the set's pieces already
    round them changed to join them too (and those by erased cells, to join what's left). get(x, y) -> the tile of the
    layer there (None off the maps), put(x, y, name). Returns how many cells changed."""
    pieces, below = join_pieces(project, brush)
    if not pieces:
        return 0
    faces = set(below.values())
    path = set(cells)
    st = project.tile_set_of(brush)
    also = {n.strip() for n in project.set_info(st[0]).get("Joins.Too", "").split(",") if n.strip()}

    def member(x, y):                                                  # (Joins.Too: a gate in the wall, its burnt part)
        return (x, y) in path or get(x, y) in pieces or get(x, y) in also

    def face(x, y):
        return get(x, y) in faces and (x, y) not in path

    def mask(x, y):
        m = ""
        for side, dx, dy in SIDES:
            nx, ny = x + dx, y + dy
            if member(nx, ny) or (side == "N" and face(nx, ny)):       # (a tower's face above it: it joins that)
                m += side
        return m
    todo = sorted(path | {(x + dx, y + dy) for x, y in path | set(erased) for _, dx, dy in SIDES
                          if get(x + dx, y + dy) in pieces}, key=lambda c: (c[1], c[0]))
    changed, faced = 0, set()
    for x, y in todo:
        if (x, y) in faced:
            continue
        name = join_pick(pieces, mask(x, y), below)
        if name is None:
            continue
        if get(x, y) != name:
            put(x, y, name)
            changed += 1
        under = below.get(name)
        if under and "S" in mask(x, y):                                # (the wall goes on south: no face cutting it, a corner
            under = None                                               #  turning south keeps the wall below it)
        if under:                                                    # (two tiles tall: its face in the cell below)
            if get(x, y + 1) != under:
                put(x, y + 1, under)
                changed += 1
            faced.add((x, y + 1))
            path.discard((x, y + 1))
        elif get(x, y + 1) in faces and (x, y + 1) not in path:
            pass                                                       # (someone else's face: left alone)
    return changed


def line_cells(a, b):
    """The tiles from a to b (without a), each next to the last along a side: a stroke the mouse outran has no gaps, and
    a wall drawn on the slant still joins."""
    (x, y), (x1, y1) = a, b
    dx, dy = abs(x1 - x), abs(y1 - y)
    sx, sy = (1 if x1 > x else -1), (1 if y1 > y else -1)
    out, err = [], dx - dy
    while (x, y) != (x1, y1):
        if y == y1 or (err >= 0 and x != x1):
            x, err = x + sx, err - dy
        else:
            y, err = y + sy, err + dx
        out.append((x, y))
    return out


def join_cells(w, h):
    """The cells a Join set is laid on over a dragged w x h rectangle: a line if it's one wide, else its edge."""
    if w == 1 or h == 1:
        return [(i, j) for j in range(h) for i in range(w)]
    return [(i, j) for j in range(h) for i in range(w) if i in (0, w - 1) or j in (0, h - 1)]


# ----- pieces where two grounds meet on the slant (TileSets.ini Kind=Shore: its Land, its Water - the ground it's laid
# on, the sea, a lake or sand - and its pieces: Corners=, Small= one corner each, Pieces=NE+NW:name for more): a cell of
# the base ground whose two sides at a corner are both the land takes that corner (whatever is on the diagonal or the
# far side: water with land on three sides takes two), and the piece with every corner it takes; one corner alone, the
# Small piece where the coast steps on past it (build_ground_pieces.py made every piece)
WATER = "Water001"
CORNERS = (("N", "E"), ("S", "E"), ("S", "W"), ("N", "W"))


def _corners(text):
    out = {}
    for part in text.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip().upper()
            if len(k) == 2:
                out[(k[0], k[1])] = v.strip()
    return out


def _pieces(text):
    out = {}
    for part in text.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            out[frozenset(c.strip().upper() for c in k.split("+") if c.strip())] = v.strip()
    return out


def shores(project):
    """[{land, water, corner: {(ns, ew): piece}, small: {...}, pieces: {frozenset of "NE"...: piece}}] of every Shore
    set in TileSets.ini (water: the ground its pieces are laid on)."""
    out = []
    for st in project.tile_sets():
        info = project.set_info(st[0])
        if (info.get("Kind") or "").strip().lower() != "shore" or not info.get("Land"):
            continue
        s = {"land": info["Land"].strip(), "water": info.get("Water", "").strip() or WATER,
             "corner": _corners(info.get("Corners", "")), "small": _corners(info.get("Small", "")),
             "pieces": _pieces(info.get("Pieces", ""))}
        for (ns, ew), n in s["corner"].items():
            s["pieces"].setdefault(frozenset([ns + ew]), n)
        out.append(s)
    return out


def shore_sets(project):
    """{land tile: [every piece with that land in its corners]} (for the palette's look-alikes and the smoothing)."""
    out = {}
    for s in shores(project):
        out.setdefault(s["land"], []).extend(list(s["pieces"].values()) + list(s["small"].values()))
    return out


def smooth_corners(project, get, put, changed, keep=(), reach=2):
    """The pieces round the changed cells (reach out: 0 for a pass over every cell given), as they should be now. get(x, y) -> tile name (None off the
    maps), put(x, y, name). A piece none of whose corners are there any more goes back to its base ground, unless
    it's in keep (painted there on purpose). Returns how many cells changed."""
    sets = shores(project)
    if not sets or not changed:
        return 0
    by = {(s["water"], s["land"]): s for s in sets}
    bases = {s["water"] for s in sets}
    lands = {s["land"] for s in sets}
    piece_of = {}                                   # (a piece: the base it's laid on)
    for s in sets:
        for n in list(s["pieces"].values()) + list(s["small"].values()):
            piece_of[n] = s["water"]
    near = {(x + dx, y + dy) for x, y in changed for dx in range(-reach, reach + 1) for dy in range(-reach, reach + 1)}
    old = {}

    def tile(x, y):
        if (x, y) not in old:
            old[(x, y)] = get(x, y)
        return old[(x, y)]

    def ground(t):
        """What a tile counts as here: a piece its base; a look-alike its own (Grass002 is Grass001's grass)."""
        if not t:
            return t
        if t in piece_of:
            return piece_of[t]
        if t in bases or t in lands:
            return t
        base = re.sub(r"\d+$", "", t) + "001"
        return base if base in bases or base in lands else t
    todo = {}
    for x, y in near:
        t = tile(x, y)
        b = ground(t)
        if b not in bases or (t not in piece_of and t != b):
            continue                                # (not a base ground, nor a piece of one)
        took = {}                                   # land -> [the corners it takes]
        for ns, ew in CORNERS:
            dy, dx = (-1 if ns == "N" else 1), (1 if ew == "E" else -1)
            a, c = ground(tile(x, y + dy)), ground(tile(x + dx, y))
            if a and a == c and a != b and (b, a) in by:
                took.setdefault(a, []).append(ns + ew)
        want = b
        if took:
            land = max(took, key=lambda k: len(took[k]))
            s, mask = by[(b, land)], took[land]
            if len(mask) == 1:
                ns, ew = mask[0][0], mask[0][1]
                dy, dx = (-1 if ns == "N" else 1), (1 if ew == "E" else -1)
                shallow = ground(tile(x - dx, y + dy)) == land or ground(tile(x + dx, y - dy)) == land
                want = (s["small"] if shallow else s["corner"]).get((ns, ew)) or s["corner"].get((ns, ew), b)
            else:
                want = s["pieces"].get(frozenset(mask), b)
        if want != t and not (want == b and (x, y) in keep):
            todo[(x, y)] = want
    for (x, y), t in todo.items():
        put(x, y, t)
    return len(todo)
