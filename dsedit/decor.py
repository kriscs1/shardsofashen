"""Splitting props off their floors. A tile drawn on a floor (a chair on planks, a tree on grass) becomes a see-through
decor tile (Tiles.ini Layer=Decor), and the maps say Floor+Decor(Name) where they had it, so the same chair goes on any
floor and Chair101 (the chair again on Tile001) isn't needed.

How a tile is split: its floor is another tile (the builders draw furniture on Plank001, a tree on Grass001), the one
that matches most of it. A pixel the same as the floor's is see-through; a pixel that is the floor made darker (k times
its colour, the same k for red, green and blue) is shadow: black, 1-k of it; the rest is the thing itself. A pixel or
two inside the thing that happen to match the floor (the table top and the planks) are filled. Put back over its floor
the decor is the tile again: that's checked.

apply() keeps a copy of everything it changes in Dev\\Archive\\Decor split <date time>\\ (Tiles.ini, the maps, the
sprites), so it can be put back by copying them back.

Run it on its own (python -m dsedit.decor) for a report of what it would split, or with --contact <file.png> for a
picture of it."""
import os
import re
import shutil
import time

import numpy as np
from PIL import Image

from .project import Cell, read_text_lines, write_text_lines, tile_family

PROP_FAMILIES = {"Furniture & Props", "Trees", "Rocks & Ore", "Plants", "Other"}
FLOOR_FAMILIES = {"Ground", "Walls & Buildings", "Cave", "Water"}
SAME = 2            # a pixel within this of the floor's (each of r, g, b) is the floor
MIN_FLOOR = 0.12    # at least this much of the tile must be its floor (or shadow on it) to be split
GOOD_FLOOR = 0.25   # ...and this much to be ticked to begin with
HOLE = 3            # see-through bits this small, shut in by the thing, are part of it
# split, but not ticked to begin with: built into a wall, or covering the floor (a rug's middle can't be split)
UNTICKED = ("Fireplace", "Rug", "Carpet", "Hedge", "Bookshelf", "Stairs", "Bed_")


def rgb_of(img):
    return np.asarray(img.convert("RGB"), dtype=np.int32)


def opaque(img):
    return img.mode != "RGBA" or img.getchannel("A").getextrema()[0] == 255


# =====================================================================================================================
# One tile
# =====================================================================================================================
def classify(t, b):
    """t, b: (h, w, 3) int arrays, the tile and a floor. -> (same, shadow, k): where the tile is the floor, where it is
    the floor in shadow, and how dark (k = the tile / the floor)."""
    same = np.abs(t - b).max(axis=-1) <= SAME
    bs = b.sum(axis=-1).astype(np.float64)
    k = t.sum(axis=-1) / np.maximum(bs, 1.0)
    err = np.abs(b * k[..., None] - t).max(axis=-1)
    shadow = ~same & (bs >= 90) & (k >= 0.3) & (k <= 0.93) & (err <= 2.5)
    return same, shadow, k


def fill_holes(clear, limit=HOLE):
    """The see-through pixels (clear) that are in small pockets shut in by the thing: those pockets."""
    h, w = clear.shape
    seen = np.zeros_like(clear)
    out = np.zeros_like(clear)
    for y0 in range(h):
        for x0 in range(w):
            if not clear[y0, x0] or seen[y0, x0]:
                continue
            todo, part, edge = [(y0, x0)], [], False
            seen[y0, x0] = True
            while todo:
                y, x = todo.pop()
                part.append((y, x))
                if y in (0, h - 1) or x in (0, w - 1):
                    edge = True
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and clear[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        todo.append((ny, nx))
            if not edge and len(part) <= limit:
                for y, x in part:
                    out[y, x] = True
    return out


# The tiles drawn with the floor lit up round them (a torch, a lamp post): Tiles.ini Glow.Colour=R G B (the light's
# colour: the floor is drawn towards it) and Glow.Match=<how near, 0-255> (exact as see-through light: a few; a
# brightened floor that see-through light only matches closely: more). Read by analyse(): {tile: (colour, match)}
LIGHTS = {}


def read_lights(project):
    LIGHTS.clear()
    ini = project.tiles_ini
    for sec in ini.sections():
        c = ini.get(sec, "Glow.Colour", "")
        if c:
            try:
                colour = tuple(max(0, min(255, int(float(p)))) for p in c.replace(",", " ").split()[:3])
                LIGHTS[sec] = (colour, float(ini.get(sec, "Glow.Match", "4") or 4))
            except ValueError:
                pass


def light_of(name):
    """(light colour, tolerance) of a tile that lights the floor round it, or None."""
    return LIGHTS.get(name)


def glow(t, b, colour, tol):
    """Where tile t is floor b lit by a light of colour (b drawn towards it by some amount, the same for r, g and b),
    and how much (where, alpha 0-1). tol: how near that has to be."""
    L = np.array(colour, dtype=np.float64)
    tf, bf = t.astype(np.float64), b.astype(np.float64)
    dL = L - bf
    a = np.clip((((tf - bf) * dL).sum(axis=-1)) / np.maximum((dL * dL).sum(axis=-1), 1.0), 0, 1)
    err = np.abs(bf + a[..., None] * dL - tf).max(axis=-1)
    return (a > 0) & (a <= 0.85) & (err <= tol), a


def split(t, b, name=""):
    """The decor of tile t on floor b: (rgba uint8 array, holes filled, the worst error drawn back over b). A light
    (Tiles.ini Glow.Colour: a torch, a lamp post) keeps the floor lit up round it as see-through light."""
    same, shadow, k = classify(t, b)
    light = light_of(name)
    lit, lit_a = glow(t, b, *light) if light else (np.zeros_like(same), None)
    lit &= ~same & ~shadow
    thing = ~same & ~shadow & ~lit
    pad = np.pad(thing, 1, constant_values=False)
    shut_in = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    shadow &= ~shut_in                             # (a "shadow" or "glow" pixel with the thing all round it is the thing)
    lit &= ~shut_in
    holes = fill_holes(same | shadow | lit)
    thing = ~same & ~shadow & ~lit | holes
    shadow &= ~holes
    lit &= ~holes
    h, w = same.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[thing, :3] = t[thing]
    out[thing, 3] = 255
    out[shadow, 3] = np.clip(np.round((1 - k[shadow]) * 255), 1, 255).astype(np.uint8)
    if lit.any():
        out[lit, :3] = light[0]
        out[lit, 3] = np.clip(np.round(lit_a[lit] * 255), 1, 255).astype(np.uint8)
    back = over(out, b)
    return out, int(holes.sum()), int(np.abs(back - t).max()) if back.size else 0


def over(rgba, b):
    a = rgba[..., 3:4].astype(np.float64) / 255
    return np.round(rgba[..., :3] * a + b * (1 - a)).astype(np.int32)


def walk_without_floor(walk, floor_walk, rgba):
    """The decor's walk mask: the tile's, but a cell blocked only by its floor (a wall, with nothing of the thing on
    that part of it) is open, so the decor doesn't carry the wall about with it."""
    n = len(walk)
    r = int(round(n ** 0.5))
    if r * r != n or len(floor_walk) != n:
        return walk
    h, w = rgba.shape[:2]
    out = list(walk)
    for i in range(n):
        if walk[i] == "0" and floor_walk[i] == "0":
            cx, cy = i % r, i // r
            x0, x1 = cx * w // r, (cx + 1) * w // r
            y0, y1 = cy * h // r, (cy + 1) * h // r
            if not (rgba[y0:y1, x0:x1, 3] == 255).any():
                out[i] = "1"
    return "".join(out)


# =====================================================================================================================
# Every tile
# =====================================================================================================================
class Split:
    """A tile that can be split: name, its floor, its decor (rgba), how much of it was floor or shadow (score), holes
    filled, the error drawn back; group: the identical decor it is merged into (the canonical name) or None."""

    def __init__(self, name, floor, rgba, score, holes, error, uses):
        self.name, self.floor, self.rgba, self.score = name, floor, rgba, score
        self.holes, self.error, self.uses = holes, error, uses
        self.canon = name           # the name it goes on the maps as (the first of its identical ones)
        self.merged = []            # (canonical only) the identical ones that become it
        self.keep_name = False      # named somewhere (a script, a save): not merged into another
        self.blocked = ""           # why it can't be split on its own (a script changes it to a tile that can't)
        self.linked = set()         # what has to be split with it (scripts change one to the other)
        self.walk = ""              # its Walkable.Data as decor (walk_without_floor)

    @property
    def good(self):
        light = light_of(self.name)                     # (a lamp's light is a close match, not exact)
        return (self.score >= GOOD_FLOOR and self.error <= (light[1] if light else 4) and self.holes <= 12 and
                not self.blocked and not self.name.startswith(UNTICKED))

    def image(self):
        return Image.fromarray(self.rgba, "RGBA")


def map_uses(project):
    """{tile: number of map cells with it as their ground}."""
    uses = {}
    H = project.map_h
    for m in project.maps():
        try:
            lines = read_text_lines(project.map_path(m))
        except OSError:
            continue
        for row in lines[:H]:
            for c in row.split(":"):
                t = c.split("+", 1)[0].strip()
                if t:
                    uses[t] = uses.get(t, 0) + 1
    return uses


def references(project):
    """{word: [where]}: every name-like word in the scripts, the Data ini files (but Tiles.ini, whose sections are the
    tiles themselves; its Open.Tile, Unlocked.Tile and Blend.Texture values do count) and the saves."""
    refs = {}

    def add(text, where):
        for w in set(re.findall(r"[A-Za-z][A-Za-z0-9_]*\d{3}", text)):
            refs.setdefault(w, []).append(where)
    for s in project.scripts():
        try:
            add("\n".join(read_text_lines(project.script_path(s))), "script " + s)
        except OSError:
            pass
    for folder, label in ((("Data",), "Data"), (("Saves",), "save")):
        d = project.p(*folder)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.lower().endswith(".ini") and f.lower() != "tiles.ini":
                try:
                    add("\n".join(read_text_lines(os.path.join(d, f))), "%s %s" % (label, f))
                except OSError:
                    pass
    for sec in project.tiles_ini.sections():
        for key in ("Open.Tile", "Unlocked.Tile", "Blend.Texture"):
            v = project.tiles_ini.get(sec, key, "")
            if v and v != sec:
                refs.setdefault(v, []).append("Tiles.ini [%s] %s" % (sec, key))
    return refs


def script_links(project):
    """[(stem, tile)]: a script <Verb> <Stem> that does Change.Tile to tile (Chop Oak_Tree -> Tree_Stump001)."""
    out = []
    for s in project.scripts():
        if " " not in s:
            continue
        stem = s.split(" ", 1)[1].strip()
        try:
            lines = read_text_lines(project.script_path(s))
        except OSError:
            continue
        for l in lines:
            f = l.split("\t")
            if len(f) > 3 and f[1].strip() == "Change.Tile":
                out.append((stem, f[3].strip()))
    return out


def stem(name):
    return name[:-3] if len(name) > 3 and name[-3:].isdigit() else name


def analyse(project, progress=None):
    """Every tile that can be split, as Splits (identical decor merged, script-linked ones tied together)."""
    P = project
    read_lights(P)
    names = [t for t in P.tiles() if not P.is_decor(t)]
    imgs, opaque_names = {}, []
    for n in names:
        img = P.sprite("Tiles", n)
        if img is None or img.size != (P.tile_w, P.tile_h) or not opaque(img):
            continue
        imgs[n] = rgb_of(img)
        opaque_names.append(n)
    props = [n for n in opaque_names if tile_family(n) in PROP_FAMILIES]
    # a prop on a wall is named after the prop (Potion_Shelf_Brick_Thin_Plank001): a prop, not a floor
    prop_stems = tuple(stem(n) + "_" for n in props)
    floors = [n for n in opaque_names if tile_family(n) in FLOOR_FAMILIES and not n.startswith(prop_stems)]
    props += [n for n in opaque_names if tile_family(n) in FLOOR_FAMILIES and n.startswith(prop_stems)]
    if not floors:
        return []
    F = np.stack([imgs[n] for n in floors]).astype(np.int32)

    def best_floor(t, skip=None, name=""):
        same, shadow, _ = classify(t[None], F)
        score = (same | shadow).mean(axis=(1, 2)) + same.mean(axis=(1, 2)) * 1e-3    # (more floor wins a tie)
        if skip is not None:
            score[skip] = -1
        j = int(score.argmax())
        if name and light_of(name):         # a light: of the likeliest floors, the one that leaves least of it solid
            top = [int(i) for i in np.argsort(-score)[:5] if score[i] >= MIN_FLOOR]
            if top:
                j = min(top, key=lambda i: ((split(t, F[i], name)[0][..., 3] == 255).sum(), -score[i]))
        return j, float(score[j])
    # a "floor" that is mostly another floor with something on it (Stone001: a stone on the grass) isn't one. Which is
    # the floor and which the thing on it looks the same both ways round: the floor is the one the maps use more
    uses = map_uses(P)
    plain = []
    for i, n in enumerate(floors):
        j, sc = best_floor(imgs[n], skip=i)
        if sc < 0.6 or sc >= 0.999 or uses.get(floors[j], 0) <= uses.get(n, 0) or \
                (split(imgs[n], F[j])[0][..., 3] == 255).mean() < 0.01:
            plain.append(i)
        elif progress is None and __name__ == "__main__":
            print("(not a floor: %s is %s with something on it)" % (n, floors[j]))
    floors = [floors[i] for i in plain]
    F = F[plain]
    found = {}
    for i, n in enumerate(props):
        if progress:
            progress(i, len(props), n)
        t = imgs[n]
        j, sc = best_floor(t, name=n)
        if sc < MIN_FLOOR:
            continue
        rgba, holes, error = split(t, F[j], n)                  # (a picked bush can be just its floor: an empty
        #                                                          decor, still named)
        s = found[n] = Split(n, floors[j], rgba, sc, holes, error, uses.get(n, 0))
        walk = P.tiles_ini.get(n, "Walkable.Data", "")
        floor_walk = P.tiles_ini.get(floors[j], "Walkable.Data", "")
        s.walk = walk_without_floor(walk, floor_walk, rgba) if walk and floor_walk else walk
    refs = references(P)
    # identical decor: one tile (the first by name; one that's named somewhere keeps its own)
    order = sorted(found, key=str.lower)
    for n in order:
        s = found[n]
        s.keep_name = n in refs
    canon_of = {}
    for n in order:
        s = found[n]
        if s.keep_name:
            continue
        for c in order:
            if c == n:
                break
            o = found[c]
            if o.canon == c and same_decor(s.rgba, o.rgba) and s.walk == o.walk:   # (a plant by a west wall and
                #                                                     one by a north wall look alike but block apart)
                s.canon = c
                o.merged.append(n)
                canon_of[n] = c
                break
    for n in order:                                 # (the same thing drawn on two floors says exactly what it is)
        o = found[n]
        if o.merged:
            o.rgba = matte([(imgs[x], imgs[found[x].floor]) for x in [n] + o.merged], o.rgba)
    # what scripts change into each other (Chop Oak_Tree: Oak_Tree001 -> Tree_Stump001) goes together or not at all
    by_stem = {}
    for n in names:
        by_stem.setdefault(stem(n), []).append(n)
    floor_set = set(floors)
    for st, target in script_links(P):
        group = [t for t in by_stem.get(st, []) if t not in floor_set] + ([target] if target not in floor_set else [])
        group = [g for g in group if g in imgs or g in found]
        for a in group:
            for b in group:
                if a != b and a in found:
                    found[a].linked.add(b)
    changed = True
    while changed:                                  # (a tile linked to one that can't be split can't be either)
        changed = False
        for s in found.values():
            if s.blocked:
                continue
            bad = [x for x in s.linked if x not in found or found[x].blocked]
            if bad:
                s.blocked = "a script changes it to or from %s, which can't be split" % bad[0]
                changed = True
    return [found[n] for n in order]


def matte(pairs, rgba):
    """The decor of one thing drawn on several floors ([(tile, floor)] arrays): where two floors differ, the tiles say
    exactly how see-through each pixel is and what colour (tile1 - tile2 = (1 - alpha) (floor1 - floor2)), so a chair
    as brown as the planks or a shadow as dark as the thing is told apart. Elsewhere rgba (the split on one floor)."""
    out = rgba.copy()
    best = np.zeros(rgba.shape[:2])
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            ti, fi = (a.astype(np.float64) for a in pairs[i])
            tj, fj = (a.astype(np.float64) for a in pairs[j])
            df = fi - fj
            norm = (df * df).sum(axis=-1)
            use = (norm > best) & (norm >= 30 ** 2)          # (this pair's floors differ most here, and enough)
            if not use.any():
                continue
            best = np.where(use, norm, best)
            clear = np.clip(((ti - tj) * df).sum(axis=-1) / np.maximum(norm, 1), 0, 1)     # 1 - alpha
            alpha = 1 - clear
            colour = np.clip((ti - fi * clear[..., None]) / np.maximum(alpha, 1e-3)[..., None], 0, 255)
            a8 = np.round(alpha * 255).astype(np.uint8)
            a8[a8 < 6] = 0
            c8 = np.round(colour).astype(np.uint8)
            c8[a8 == 0] = 0
            out[use, :3] = c8[use]
            out[use, 3] = a8[use]
    return out


def same_decor(a, b):
    if a.shape != b.shape:
        return False
    alpha = np.abs(a[..., 3].astype(int) - b[..., 3].astype(int)) > 8
    colour = (a[..., 3] == 255) & (np.abs(a[..., :3].astype(int) - b[..., :3].astype(int)).max(axis=-1) > 3)
    return (alpha | colour).mean() <= 0.01


# =====================================================================================================================
# Doing it
# =====================================================================================================================
def apply(project, splits, chosen):
    """Splits the tiles named in chosen (and the ones merged into them): their sprites become the decor, Tiles.ini
    says Layer=Decor, the merged ones go (sprite and section), and every map cell with one as its ground tile becomes
    Floor+Decor(Name). Returns (backup folder, report lines)."""
    P = project
    by_name = {s.name: s for s in splits}
    todo = [by_name[n] for n in chosen if n in by_name and by_name[n].canon == n and not by_name[n].blocked]
    mapping = {}                                        # ground tile on a map -> (floor, decor)
    for s in todo:
        mapping[s.name] = (s.floor, s.name)
        for m in s.merged:
            mapping[m] = (by_name[m].floor, s.name)
    if not mapping:
        return None, ["Nothing to split."]
    stamp = time.strftime("%Y-%m-%d %H%M%S")
    backup = P.p("Dev", "Archive", "Decor split " + stamp)
    os.makedirs(backup, exist_ok=True)

    def keep(*rel):
        src = P.p(*rel)
        if os.path.exists(src):
            dst = os.path.join(backup, *rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    report = []
    keep("Data", "Tiles.ini")
    # the maps
    H, W = P.map_h, P.map_w
    cells_done, skipped = 0, 0
    files = []                                          # (every map, and the old ones in Maps\Test and the like)
    for folder, _, names in os.walk(P.p("Maps")):
        for f in sorted(names):
            if re.fullmatch(r"-?\d+,-?\d+,-?\d+\.txt", f):
                files.append(os.path.relpath(os.path.join(folder, f), P.p("Maps")))
    for rel in files:
        m = rel[:-4]
        path = P.p("Maps", rel)
        lines = read_text_lines(path)
        changed = False
        for y in range(min(H, len(lines))):
            cells = [Cell(c) for c in lines[y].split(":")]
            row_changed = False
            for cell in cells:
                if cell.tile in mapping:
                    if cell.decor:
                        skipped += 1
                        report.append("Map %s: a %s already has decor %s: left as it is" % (m, cell.tile, cell.decor))
                        continue
                    floor, decor = mapping[cell.tile]
                    cell.tile = floor
                    cell.set_decor(decor)
                    cells_done += 1
                    row_changed = True
            if row_changed:
                lines[y] = ":".join(c.text() for c in cells)
                changed = True
        if changed:
            keep("Maps", rel)
            write_text_lines(path, lines)
    # the sprites and Tiles.ini
    ini = P.tiles_ini
    for s in todo:
        keep("Sprites", "Tiles", s.name + ".png")
        Image.fromarray(s.rgba, "RGBA").save(P.p("Sprites", "Tiles", s.name + ".png"))
        if s.walk:
            ini.set(s.name, "Walkable.Data", s.walk)
        ini.set(s.name, "Layer", "Decor")
        for key in ("Blend", "Blend.Texture", "Texture"):      # (the ground under it blends; it doesn't)
            ini.remove(s.name, key)
        P.forget_sprite("Tiles", s.name)
        for m in s.merged:
            src = P.p("Sprites", "Tiles", m + ".png")
            if os.path.exists(src):
                dst = os.path.join(backup, "Sprites", "Tiles", m + ".png")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
            ini.remove_section(m)
            P.forget_sprite("Tiles", m)
    record_for_builders(P, mapping)
    gone = [m for s in todo for m in s.merged if m in P.minimap_colours]
    if gone:                                            # (their minimap colours: the one they became has its own)
        keep("Dev", "Minimap Colours.txt")
        for m in gone:
            del P.minimap_colours[m]
        P.save_minimap_colours()
    ini.save()
    P.refresh()
    merged = sum(len(s.merged) for s in todo)
    report.insert(0, "Split %d tiles into decor (%d copies on other floors merged into them); %d map cells now say "
                     "Floor+Decor(...)." % (len(todo), merged, cells_done))
    if skipped:
        report.insert(1, "%d cells already had decor and were left as they were." % skipped)
    with open(os.path.join(backup, "README.txt"), "w", encoding="utf-8") as f:
        f.write("Made by the editor's \"Split props off their floors\" on %s.\n"
                "These are the files as they were before. To undo it, copy them back over the game's (and remove\n"
                "Layer=Decor from those tiles if you only put some back).\n\n%s\n" % (stamp, "\n".join(report)))
    return backup, report


def record_for_builders(project, mapping):
    """Dev\\migrate\\decor_map.json: what each split tile became ({tile: [floor, decor]}), so the builders keep drawing
    with the old pictures (kept in the archive), leave the decor sprites alone and put Floor+Decor(Name) on new maps."""
    import json
    path = project.p("Dev", "migrate", "decor_map.json")
    if not os.path.isdir(os.path.dirname(path)):
        return
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    old.update({k: list(v) for k, v in mapping.items()})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(old.items())), f, indent=1)


def contact_sheet(project, splits, path, alt="Marble001"):
    """A picture of every split: the tile, its floor, the decor (on a check), the decor on another floor."""
    tw, th = project.tile_w, project.tile_h
    s2 = 2
    cw, ch = tw * s2, th * s2
    rows = len(splits)
    im = Image.new("RGB", (cw * 4 + 12 * 3, rows * (ch + 4)), (30, 26, 22))
    check = Image.new("RGBA", (tw, th))
    for y in range(th):
        for x in range(tw):
            check.putpixel((x, y), (200, 200, 200, 255) if (x // 4 + y // 4) % 2 else (150, 150, 150, 255))
    for i, s in enumerate(splits):
        y = i * (ch + 4)
        floor = project.sprite("Tiles", s.floor).convert("RGBA")
        other = project.sprite("Tiles", alt_floor(s.floor, alt)).convert("RGBA")
        pics = [project.sprite("Tiles", s.name).convert("RGBA"), floor,
                Image.alpha_composite(check, s.image()), Image.alpha_composite(other, s.image())]
        for j, p in enumerate(pics):
            im.paste(p.resize((cw, ch), Image.NEAREST).convert("RGB"), (j * (cw + 12), y))
    im.save(path)


def alt_floor(floor, default="Marble001"):
    """Another floor to show a decor on, of the same sort (inside: other boards; outside: other ground)."""
    return {"Plank001": "Marble001", "Tile001": "Plank001", "Marble001": "Plank001", "Grass001": "Sand001",
            "Sand001": "Grass001", "Snow001": "Grass001", "Marsh001": "Grass001", "Water001": "Sand001",
            "Cave_Floor001": "Grass001"}.get(floor, "Plank001" if "Thin" in floor or "Plank" in floor else default)


def main():
    import sys
    from .project import Project
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    P = Project(root)
    splits = analyse(P)
    for s in splits:
        note = ("merged into %s" % s.canon) if s.canon != s.name else (
            ("+ %s" % ", ".join(s.merged)) if s.merged else "")
        print("%-3s %-38s on %-26s floor %.2f holes %2d err %d uses %4d %s%s" % (
            "ok" if s.good else "--", s.name, s.floor, s.score, s.holes, s.error, s.uses, note,
            ("  BLOCKED: " + s.blocked) if s.blocked else ""))
    print("%d can be split, %d look good" % (len(splits), sum(1 for s in splits if s.good)))
    if "--contact" in sys.argv:
        contact_sheet(P, splits, sys.argv[sys.argv.index("--contact") + 1])


if __name__ == "__main__":
    main()
