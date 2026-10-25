"""One-off (safe to run again): windows, signs, ivy, bookshelves, beds against walls and ladders become decor.

  python migrate_wall_decor.py --dry <sheet.png>   what it would do, and a picture of every decor on its own floor
                                                   and on another
  python migrate_wall_decor.py                     do it

* Signs: <Base>_Sign001-008 (the same sign on each of the five walls) -> Sign001-008 over the wall.
* Ivy: <Base>_Ivy001-003 -> Ivy001-003 (drawn see-through by decor_sets.py) over the wall.
* Windows: each <Base>_Window001-005 keeps its name and becomes decor over its wall (the five walls' windows differ:
  frame, shutters, sill), so any window goes on any wall.
* Bookshelves: Bookshelf001 (planks), 101 (tiles), 201 (marble) and the ones against a thin wall
  (Bookshelf_<Wall>_Thin_<Floor>NNN) -> Bookshelf001 over that floor or wall.
* Beds against a wall (Bed_<Wall>_Thin_Plank001) -> the bed they are (Bed001 / Bed002, already decor).
* Ladders: the ladder, the hatch and the hole in the ground each once (Ladder001, 002, 006: the cave's 004, 005 and
  the dirt's 007 become them, drawn clean); the loft ladder and the trapdoor (008, 009) keep their own
  names (their scripts say "into the loft"). Ladder003 too.
The same as the editor's split (dsedit\\decor.py): the old opaque pictures go to Dev\\Archive\\Decor split <date> walls
(the builders draw with them), decor_map.json says what each became, maps the builders own are left for the build.
Everything changed is copied first to Dev\\Archive\\Wall decor <date>."""
import json
import os
import re
import shutil
import sys
import time

import numpy as np
from PIL import Image

from common import HERE, NEW, GEN, MAP_H, p, read_lines, write_lines

sys.path.insert(0, NEW)
from dsedit import decor as D  # noqa: E402
from dsedit.project import Project  # noqa: E402

import house_tiles as H  # noqa: E402

WALLS = H.WALL_BASES                           # wall tile -> its name's start (Brick001 -> Brick)
GROUND = ("Tile001", "Plank001", "Marble001", "Grass001", "Dirt001", "Marsh001", "Cave_Floor001", "Cave_Floor002",
          "Cave_Floor003", "Mine_Floor001", "Stone_Floor001", "Paving001", "Sand001")


def plan(P):
    """[(decor, [(old tile, its floor)], how)]: how = "matte" (one picture from them all, if they're the same: a new
    name or the first's), "same" (the same: drawn by the same code on each, only the floor differs), "first" (all of them become the
    first one's picture),
    "art" (its picture is drawn by decor_sets.py), "have" (the decor is there already)."""
    have = lambda n: P.sprite("Tiles", n) is not None
    out = []
    for i in range(1, 9):
        out.append(("Sign%03d" % i, [("%s_Sign%03d" % (b, i), w) for w, b in WALLS.items()], "same"))
    for k in range(1, 4):
        out.append(("Ivy%03d" % k, [("%s_Ivy%03d" % (b, k), w) for w, b in WALLS.items()], "art"))
    for w, b in WALLS.items():
        for n in range(1, 6):
            out.append(("%s_Window%03d" % (b, n), [("%s_Window%03d" % (b, n), w)], "matte"))
    shelves = [("Bookshelf001", "Plank001"), ("Bookshelf101", "Tile001"), ("Bookshelf201", "Marble001")]
    beds = {"Bed001": [], "Bed002": []}
    for t in P.tiles():
        m = re.fullmatch(r"(Bookshelf|Bed)_(\w+_Thin_\w+?\d{3})", t)
        if m and have(m.group(2)):
            (shelves if m.group(1) == "Bookshelf" else beds.setdefault("?", [])).append((t, m.group(2)))
    out.append(("Bookshelf001", shelves, "same"))
    for t, floor in beds.pop("?", []):
        out.append(("?bed", [(t, floor)], "have"))
    ladders = {"Ladder001": ["Ladder001", "Ladder004"], "Ladder002": ["Ladder002", "Ladder005"],
               "Ladder006": ["Ladder006", "Ladder007"], "Ladder003": ["Ladder003"], "Ladder008": ["Ladder008"],
               "Ladder009": ["Ladder009"]}
    for d, olds in ladders.items():                     # (the cave's are drawn on a speckled floor: the house's are
        out.append((d, [(o, None) for o in olds], "first"))     # clean, and the same ladder)
    return [(d, [(o, f) for o, f in olds if have(o)], how) for d, olds, how in out if any(have(o) for o, _ in olds)]


def rgb(P, n):
    return D.rgb_of(P.sprite("Tiles", n))


def best_floor(P, t):
    """The ground a ladder is drawn on (of GROUND, the one most of it is)."""
    best, score = None, -1
    for f in GROUND:
        if P.sprite("Tiles", f) is None:
            continue
        same, shadow, _ = D.classify(t, rgb(P, f))
        s = (same | shadow).mean()
        if s > score:
            best, score = f, s
    return best


def work_out(P):
    """[(decor, rgba or None, [(old, floor)], how, notes)] with each decor's picture, and the groups that turned out
    not to be the same thing split up."""
    out = []
    bed_rgba = {b: np.asarray(P.sprite("Tiles", b).convert("RGBA")) for b in ("Bed001", "Bed002")}
    for decor, olds, how in plan(P):
        olds = [(o, f or best_floor(P, rgb(P, o))) for o, f in olds]
        if how == "have":                          # a bed against a wall: the bed it is
            o, f = olds[0]
            got, _, _ = D.split(rgb(P, o), rgb(P, f), o)
            diff = {b: (np.abs(got[..., 3].astype(int) - a[..., 3].astype(int)) > 8).mean() for b, a in
                    bed_rgba.items()}
            b = min(diff, key=diff.get)
            out.append((b, None, olds, "have", "%s looks most like %s (%.0f%% differ)" % (o, b, diff[b] * 100)))
            continue
        if how == "art":
            out.append((decor, None, olds, how, ""))
            continue
        splits = [(o, f, D.split(rgb(P, o), rgb(P, f), o)[0]) for o, f in olds]
        base_floors = {"Plank001", "Tile001", "Marble001", "Grass001", "Dirt001", "Marsh001"} | set(WALLS) | \
            set(GROUND)
        first = splits[0][2]
        same = [s for s in splits if how == "same" or D.same_decor(s[2], first) or s[1] not in base_floors]
        apart = [s for s in splits if s not in same]
        pairs = [(rgb(P, o), rgb(P, f)) for o, f, _ in same if f in base_floors]
        if how == "first":
            same, apart = splits, []
        rgba = D.matte(pairs, first) if len(pairs) > 1 and how != "first" else first
        out.append((decor, rgba, [(o, f) for o, f, _ in same], how, ""))
        for o, f, r in apart:                     # (not the same after all: decor of its own)
            out.append((o, r, [(o, f)], how, "%s isn't the same as %s: decor of its own" % (o, decor)))
    return out


def sheet(P, work, path):
    s = 34
    rows = []
    for decor, rgba, olds, how, note in work:
        if rgba is None:
            continue
        o, f = olds[0]
        alt = "Plank001" if f != "Plank001" else "Stone_Wall001"
        rows.append([P.sprite("Tiles", o).convert("RGBA"), Image.fromarray(rgba, "RGBA"), (f, rgba), (alt, rgba)])
    cols = 4
    per = 4                                         # (groups across)
    out = Image.new("RGBA", (per * (cols * s + 10), ((len(rows) + per - 1) // per) * s), (50, 40, 34, 255))
    check = Image.new("RGBA", (32, 32), (255, 0, 255, 255))
    for i, r in enumerate(rows):
        x0, y = (i % per) * (cols * s + 10), (i // per) * s
        for j, cell in enumerate(r):
            if isinstance(cell, tuple):
                im = P.sprite("Tiles", cell[0]).convert("RGBA").copy()
                im.alpha_composite(Image.fromarray(cell[1], "RGBA"))
            else:
                im = check.copy()
                im.alpha_composite(cell)
            out.alpha_composite(im, (x0 + j * s, y))
    out.resize((out.size[0] * 2, out.size[1] * 2), Image.NEAREST).save(path)


def main():
    P = Project(NEW)
    D.read_lights(P)
    if "--dry" not in sys.argv and P.tiles_ini.get("Ivy001", "Layer", "") == "Decor":
        print("Already done: Ivy001 is decor.")              # (the signs it made are gone: remove_wall_signs.py)
        return
    work = work_out(P)
    for decor, rgba, olds, how, note in work:
        print("%-22s <- %s%s" % (decor, ", ".join("%s (on %s)" % of for of in olds), ("   ! " + note) if note else ""))
    if "--dry" in sys.argv:
        sheet(P, work, sys.argv[-1])
        return
    import decor_sets
    mapping = {}                                   # old tile -> (floor, decor)
    for decor, rgba, olds, how, note in work:
        for o, f in olds:
            mapping[o] = (f, decor)
    stamp = time.strftime("%Y-%m-%d %H%M%S")
    backup = p("Dev", "Archive", "Wall decor " + stamp)
    opaque = p("Dev", "Archive", "Decor split %s walls" % stamp, "Sprites", "Tiles")     # (the builders read these)
    os.makedirs(opaque, exist_ok=True)

    def keep(*rel):
        src = p(*rel)
        if os.path.exists(src):
            dst = os.path.join(backup, *rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    for rel in (("Data", "Tiles.ini"), ("Dev", "Minimap Colours.txt"), ("Dev", "migrate", "decor_map.json")):
        keep(*rel)
    # the maps (not the ones the builders own: the next build makes them with the decor)
    GEN.enable()
    n_cells = n_maps = left = 0
    covered = []
    for folder, _, names in os.walk(p("Maps")):
        for fn in sorted(names):
            if not re.fullmatch(r"-?\d+,-?\d+,-?\d+\.txt", fn):
                continue
            path = os.path.join(folder, fn)
            if GEN.untouched(path):
                left += 1
                continue
            lines = read_lines(path)
            changed = False
            for y in range(min(MAP_H, len(lines))):
                cells = lines[y].split(":")
                for x, cell in enumerate(cells):
                    parts = cell.split("+")
                    if parts[0] in mapping:
                        floor, decor = mapping[parts[0]]
                        if any(q.startswith("Decor(") for q in parts[1:]):     # (a bank's column over a window:
                            cells[x] = "+".join([floor] + parts[1:])            # the column stays, the window goes)
                            covered.append("%s %d,%d: %s" % (fn[:-4], x + 1, y + 1, cell))
                        else:
                            cells[x] = "+".join([floor, "Decor(%s)" % decor] + parts[1:])
                        n_cells += 1
                        changed = True
                lines[y] = ":".join(cells)
            if changed:
                keep(os.path.relpath(path, NEW))
                write_lines(path, lines)
                n_maps += 1
    # the sprites: every old one kept for the builders; the merged ones go; the decor pictures written
    ini = P.tiles_ini
    gone = []
    for o, (f, d) in mapping.items():
        src = p("Sprites", "Tiles", o + ".png")
        if os.path.exists(src):
            keep("Sprites", "Tiles", o + ".png")
            shutil.copy2(src, os.path.join(opaque, o + ".png"))
    for decor, rgba, olds, how, note in work:
        if how == "have":
            continue
        first = olds[0][0]
        if decor != first and not ini.has_section(decor):         # a new name: what the first one said
            for k, v in ini.items(first):
                if k not in ("Blend", "Blend.Texture", "Texture"):
                    ini.set(decor, k, v)
        if how == "art":
            im = decor_sets.TILE_ART[decor]()
            rgba = np.asarray(im)
        Image.fromarray(rgba, "RGBA").save(p("Sprites", "Tiles", decor + ".png"))
        walk = ini.get(decor, "Walkable.Data", "")
        floor_walk = ini.get(olds[0][1], "Walkable.Data", "")
        if olds[0][1] in WALLS:                     # (flat on a wall: the wall blocks, the decor needn't)
            ini.set(decor, "Walkable.Data", "1" * 49)
            ini.set(decor, "Line.of.Sight", "1")
        elif walk and floor_walk:
            ini.set(decor, "Walkable.Data", D.walk_without_floor(walk, floor_walk, rgba))
        ini.set(decor, "Layer", "Decor")
        for k in ("Blend", "Blend.Texture", "Texture"):
            ini.remove(decor, k)
    for o, (f, d) in mapping.items():
        if d != o:
            gone.append(o)
            src = p("Sprites", "Tiles", o + ".png")
            if os.path.exists(src):
                os.remove(src)
            ini.remove_section(o)
    ini.save()
    mm = p("Dev", "Minimap Colours.txt")
    lines = [l for l in read_lines(mm) if l.strip()]
    colour = {l.split("\t")[0]: l.split("\t")[1] for l in lines if "\t" in l}
    for decor, rgba, olds, how, note in work:          # (a new name: the colour of the first it was)
        if decor not in colour and olds[0][0] in colour:
            lines.append("%s\t%s" % (decor, colour[olds[0][0]]))
            colour[decor] = colour[olds[0][0]]
    write_lines(mm, [l for l in lines if l.split("\t")[0] not in set(gone)])
    dm_path = os.path.join(HERE, "decor_map.json")
    with open(dm_path, encoding="utf-8") as f:
        dm = json.load(f)
    dm.update({k: list(v) for k, v in mapping.items()})
    with open(dm_path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(dm.items())), f, indent=1)
    with open(os.path.join(backup, "README.txt"), "w", encoding="utf-8") as f:
        f.write("Made by Dev\\migrate\\migrate_wall_decor.py on %s: the files as they were before.\n" % stamp)
    for c in covered:
        print("  under other decor, dropped:", c)
    print("%d cells in %d maps (%d left for the build); %d tiles merged away. Backup: %s" % (
        n_cells, n_maps, left, len(gone), backup))


if __name__ == "__main__":
    main()
