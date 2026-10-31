"""Terrains and the palette's Auto groups, for the Maps page's big brushes.

A terrain (data\\TileSets.ini, Kind=Terrain: dev\\migrate\\build_terrains.py) is what a stretch of land is made of:
its ground tiles mixed by weight, the decor scattered over it (Decor.Density in a hundred tiles) and the creatures
(Entities.Density). A wall's terrain (cave rock) has a Face=: the tiles its rock shows where open ground lies
south of it (Cave_Wall002, now and then Cave_Wall003's torch), turned back to rock when that ground is filled in.
Painting one - a brush of any size, a rectangle, a flood fill, or an outline drawn round a place
and filled - lays its ground, rolls its decor and creatures afresh on each tile (once a stroke), and takes off the
natural things another terrain would have put there (a meadow's flowers under new water, a rabbit in a lake); what
was built (a chair, a fence, a named NPC) stays. Water's coasts get their diagonal pieces (TileSets.ini Kind=Shore)
from the Maps page, as for any painting.

The palette's Auto view shows a terrain, a set (a roof, a fence, a rug: TileSets.ini) or a family of look-alikes
(Flowers001-003) as one entry, which paints with the right piece itself; Detail shows every tile."""
import os
import random
import re

from .project import IniDoc, mtime, Entity
from . import world as WD


class Terrain:
    def __init__(self, key, info):
        self.key = key
        self.title = info.get("Title", "") or key.replace("_", " ")
        self.tiles = weighted(info.get("Tiles", ""))
        self.decor = weighted(info.get("Decor", ""))
        self.ents = weighted(info.get("Entities", ""))
        self.decor_density = number(info.get("Decor.Density", "0"))
        self.ents_density = number(info.get("Entities.Density", "0"))
        self.water = info.get("Water", "0").strip() == "1"
        self.face = weighted(info.get("Face", ""))     # (a wall: what it shows with open ground south of it)

    @property
    def swatch(self):
        return self.tiles[0][0] if self.tiles else "Black001"


def number(text):
    try:
        return float(text)
    except ValueError:
        return 0.0


def weighted(text):
    """"Tree001*30,Tree002*18,Bush001" -> [(name, weight)] (a weight left off is 1)."""
    out = []
    for part in text.split(","):
        name, _, w = part.strip().partition("*")
        if name.strip():
            out.append((name.strip(), number(w) if w.strip() else 1.0))
    return out


def pick(pairs, rng=random):
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[0][0] if pairs else None
    k = rng.random() * total
    for name, w in pairs:
        k -= w
        if k <= 0:
            return name
    return pairs[-1][0]


def terrains(project):
    """[Terrain] from TileSets.ini, in its order (read again when the file changes)."""
    path = project.p("data", "TileSets.ini")
    stamp = mtime(path)
    kept = getattr(project, "_terrains", None)
    if kept is None or kept[0] != stamp:
        out = []
        if os.path.exists(path):
            doc = IniDoc(path)
            for sec in doc.sections():
                if doc.get(sec, "Kind", "").strip().lower() == "terrain":
                    out.append(Terrain(sec[8:] if sec.startswith("Terrain_") else sec, dict(doc.items(sec))))
        kept = project._terrains = (stamp, out)
    return kept[1]


def named(project, key):
    return next((t for t in terrains(project) if t.key == key), None)


def natural(project):
    """(decor, creatures): what any terrain scatters (lower case) - what painting another terrain over it takes off."""
    ts = terrains(project)
    return ({n.lower() for t in ts for n, _ in t.decor}, {n.lower() for t in ts for n, _ in t.ents})


# ----- where a brush paints
def disc(cx, cy, size):
    """The tiles of a round brush size tiles across, centred on tile cx, cy."""
    if size <= 1:
        return [(cx, cy)]
    r = (size - 1) / 2
    lo, hi = -int(r + 0.5), int(r + 0.5)
    return [(cx + dx, cy + dy) for dy in range(lo, hi + 1) for dx in range(lo, hi + 1)
            if dx * dx + dy * dy <= r * r + r * 0.8]


def inside_outline(points):
    """The tiles an outline drawn round a place takes in: [(x, y)] of the tiles whose middles are inside the
    polygon points (tile units, floats), and those the line itself goes over."""
    if len(points) < 3:
        return [(int(x), int(y)) for x, y in points]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    out = set()
    for ty in range(int(min(ys)), int(max(ys)) + 1):
        y = ty + 0.5
        cross = []                                     # (where the outline crosses this row's middle)
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
            if (y1 <= y < y2) or (y2 <= y < y1):
                cross.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        cross.sort()
        for a, b in zip(cross[::2], cross[1::2]):
            for tx in range(int(round(a)), int(round(b))):
                if a <= tx + 0.5 <= b:
                    out.add((tx, ty))
    for (x1, y1), (x2, y2) in zip(points, points[1:]):   # (the line itself, in small steps)
        n = int(max(abs(x2 - x1), abs(y2 - y1)) * 3) + 1
        for i in range(n + 1):
            out.add((int(x1 + (x2 - x1) * i / n), int(y1 + (y2 - y1) * i / n)))
    return sorted(out, key=lambda c: (c[1], c[0]))


# ----- painting a terrain
def ent_tile(project, e):
    """The tile (from 0) a placed thing stands on (its feet)."""
    spr = project.sprite("Entities", e.name)
    w, h = spr.size if spr is not None else (project.tile_w, project.tile_h)
    return int((e.x + w / 2) // project.tile_w), int((e.y + h - 1) // project.tile_h)


def new_creature(project, name, tx, ty):
    """A creature of name put down on tile tx, ty (from 0) of a map: its feet on the tile, its kind's attitude."""
    spr = project.sprite("Entities", name)
    w, h = spr.size if spr is not None else (project.tile_w, project.tile_h)
    kind = project.entity_type(name)
    e = Entity(kind, name, tx * project.tile_w + (project.tile_w - w) // 2, (ty + 1) * project.tile_h - h)
    if kind == "NPC":
        att = project.entities_ini.get(name, "Attitude", "")
        e.opts = "Attitude=%s" % (att if att in ("Good", "Bad", "Passive") else "Good")
    return e


def plain(e):
    """Put there by a terrain, not by hand for a reason: no Id, no name of its own, no zone or patrol."""
    return e.kind in ("NPC", "StaticObject", "MapItem") and not any(
        e.opt(k) for k in ("Id", "Name", "Zone", "Patrol", "Project"))


def paint(project, terrain, cells, at, touch, creatures=True, rng=random):
    """terrain laid on cells (tile x, y as at() takes them: at(x, y) -> (map, x, y on it) or None; touch(map) before
    a map is changed). Returns the cells painted (for the coasts' diagonal pieces round them)."""
    nat_decor, nat_ents = natural(project)
    own = {n for n, _ in terrain.tiles}
    mine = {n.lower() for n, _ in terrain.ents}
    done, by_doc = [], {}
    for x, y in cells:
        a = at(x, y)
        if a is None:
            continue
        by_doc.setdefault(id(a[0]), (a[0], []))[1].append((x, y, a[1], a[2]))
    for doc, spots in by_doc.values():
        touch(doc)
        standing = {}
        for e in doc.placed():
            if not e.on_tile:
                standing.setdefault(ent_tile(project, e), []).append(e)
        gone = []
        for x, y, lx, ly in spots:
            cell = doc.cells[ly][lx]
            if cell.tile not in own:                   # (one of its own tiles already: kept, so it doesn't flicker)
                cell.tile = pick(terrain.tiles, rng)
            if not cell.decor or cell.decor.lower() in nat_decor:
                put = pick(terrain.decor, rng) if terrain.decor and rng.random() * 100 < terrain.decor_density \
                    else None
                cell.set_decor(put)
            here = standing.get((lx, ly), [])
            for e in here:                             # (another terrain's creature: not here any more)
                if plain(e) and e.name.lower() in nat_ents and e.name.lower() not in mine:
                    gone.append(e)
            if creatures and terrain.ents and not [e for e in here if e not in gone] and \
                    rng.random() * 100 < terrain.ents_density:
                doc.entities.append(new_creature(project, pick(terrain.ents, rng), lx, ly))
            done.append((x, y))
        if gone:
            doc.entities = [e for e in doc.entities if e not in gone]
    fix_faces(project, done, at, touch, rng)
    return done


def fix_faces(project, cells, at, touch, rng=random):
    """Walls' faces round cells just painted (and the row over them): a wall terrain's rock with open ground south of
    it shows its Face, and a face with rock south of it again is rock. Returns how many tiles changed."""
    walls = [t for t in terrains(project) if t.face]
    if not walls or not cells:
        return 0
    n = 0
    for t in walls:
        rock, faces = {r for r, _ in t.tiles}, {f for f, _ in t.face}
        solid = rock | faces
        for x, y in {(x, y + dy) for x, y in cells for dy in (-1, 0)}:
            a, b = at(x, y), at(x, y + 1)
            if a is None:
                continue
            cell = a[0].cells[a[2]][a[1]]
            if cell.tile not in solid:
                continue
            below = b[0].cells[b[2]][b[1]].tile if b is not None else None
            want_face = below is not None and below not in solid and not below.startswith("Black")
            if want_face and cell.tile in rock:
                touch(a[0])
                cell.tile = pick(t.face, rng)
                n += 1
            elif not want_face and cell.tile in faces:
                touch(a[0])
                cell.tile = pick(t.tiles, rng)
                n += 1
    return n


# ----- the palette's Auto view: a terrain, a set or a family of look-alikes as one entry
class Group:
    def __init__(self, kind, key, title, tiles, brush):
        self.kind, self.key, self.title, self.tiles, self.brush = kind, key, title, tiles, brush


def groups(project, layer):
    """{key: Group} for the palette's Auto view of a tile layer ("map", "decor", "roof", "infront"), and the tiles
    each one stands for (so they aren't shown on their own). Kept till Tiles.ini or TileSets.ini change."""
    stamp = (layer, project.tiles_ini.version, id(project.tiles_ini), mtime(project.p("data", "TileSets.ini")),
             len(project.tiles()))
    kept = getattr(project, "_auto_groups", {})
    if kept.get(layer, (None,))[0] == stamp:
        return kept[layer][1]
    out = {}
    if layer == "map":
        for t in terrains(project):
            out["terrain:" + t.key] = Group("Terrain", "terrain:" + t.key, t.title,
                                            [n for n, _ in t.tiles] + [n for n, _ in t.decor], t.swatch)
    on_layer = layer_test(project, layer)
    for sec, title, cols, names in project.tile_sets():
        kind = WD.set_kind(project, (sec, title, cols, names))
        pieces = [n for n in names if n]
        if not pieces or not all(on_layer(n) for n in pieces):
            continue
        if kind == "Shore":                            # (a coast's diagonal pieces go in by themselves)
            out["hide:" + sec] = Group("Hidden", "hide:" + sec, title, pieces, None)
        elif kind in ("Stretch", "Rug", "Join"):
            mid = names[len(names) // 2] or pieces[0]
            out["set:" + sec] = Group("Set", "set:" + sec, title, pieces, mid)
    taken = {n for g in out.values() if g.kind != "Terrain" for n in g.tiles}   # (a terrain's own tiles still show)
    stems = {}
    for t in project.tiles():
        if on_layer(t) and t not in taken:
            stem = re.sub(r"\d+$", "", t)
            if stem != t:
                stems.setdefault(stem, []).append(t)
    for stem, names in stems.items():
        if len(names) > 1:
            alike = WD.look_alikes(project, names[0])
            if len(alike) > 1:
                out["fam:" + stem] = Group("Family", "fam:" + stem, stem.replace("_", " ").lower(), alike, names[0])
    kept[layer] = (stamp, out)
    project._auto_groups = kept
    return out


def layer_test(project, layer):
    """Is a tile one the layer paints with?"""
    if layer == "map":
        return lambda t: not project.is_decor(t) and not project.is_under(t)
    if layer == "decor":
        return lambda t: project.is_decor(t) or project.is_under(t)
    return lambda t: True
