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
    diag = {n.lower() for pat in shore_sets(project).values() for n in (pat % i for i in range(2, 10))}

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


def shape(project, brush, w, h):
    """brush's set laid over a w x h rectangle: rows of tile names (None leaves that cell as it is), or None when brush
    isn't a piece of a set that stretches (a roof, a rug, the walls round a room, a fence) or it's one tile."""
    st = project.tile_set_of(brush)
    if not st or (w, h) == (1, 1):
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
    if cols == 3 and rows >= 3 and all(len(r) == 3 and all(r) for r in grid):
        return stretch(grid)                        # (a roof, the walls round a room: corners, edges, the middle)
    return None


# ----- diagonal shore pieces (as dev\migrate\build_regions.py smooth_shores puts them): a water cell in the inside
# corner of a step in the coast (land on two sides that meet and on the corner between them, water on the other two)
# becomes the piece with land in that corner; the small piece where the coast steps on past it
WATER = "Water001"
SHORE_CORNER = {("N", "E"): 2, ("N", "W"): 5, ("S", "W"): 6, ("S", "E"): 8}
SHORE_SMALL = {("N", "E"): 3, ("N", "W"): 4, ("S", "W"): 7, ("S", "E"): 9}


def shore_sets(project):
    """{land tile: its pieces' name pattern}: Grass001 Water002-009, and <Land>_Water002-009 for each <Land>001."""
    tiles = set(project.tiles())
    out = {}
    if "Grass001" in tiles and all("Water%03d" % n in tiles for n in range(2, 10)):
        out["Grass001"] = "Water%03d"
    for t in tiles:
        m = re.match(r"(.+)_Water002$", t)
        if m and m.group(1) + "001" in tiles and all("%s_Water%03d" % (m.group(1), n) in tiles for n in range(2, 10)):
            out[m.group(1) + "001"] = m.group(1) + "_Water%03d"
    return out


def smooth_corners(project, get, put, changed, keep=()):
    """The diagonal pieces round the changed cells, as they should be now. get(x, y) -> tile name (None off the
    maps), put(x, y, name). A piece whose corner isn't there any more goes back to water, unless it's in keep (painted
    there on purpose). Returns how many cells changed."""
    sets = shore_sets(project)
    if not sets or not changed:
        return 0
    pieces = {pat % n: land for land, pat in sets.items() for n in range(2, 10)}
    near = {(x + dx, y + dy) for x, y in changed for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    old = {}

    def tile(x, y):
        if (x, y) not in old:
            old[(x, y)] = get(x, y)
        return old[(x, y)]
    wet = lambda t: t == WATER or t in pieces
    todo = {}
    for x, y in near:
        t = tile(x, y)
        if not wet(t):
            continue
        want = WATER
        for (ns, ew), n in SHORE_CORNER.items():
            dy, dx = (-1 if ns == "N" else 1), (1 if ew == "E" else -1)
            land = tile(x, y + dy), tile(x + dx, y), tile(x + dx, y + dy)
            if land[0] in sets and land[0] == land[1] == land[2] and wet(tile(x, y - dy)) and wet(tile(x - dx, y)):
                shallow = tile(x - dx, y + dy) == land[0] or tile(x + dx, y - dy) == land[0]
                want = sets[land[0]] % (SHORE_SMALL[(ns, ew)] if shallow else n)
                break
        if want != t and not (want == WATER and (x, y) in keep):
            todo[(x, y)] = want
    for (x, y), t in todo.items():
        put(x, y, t)
    return len(todo)
