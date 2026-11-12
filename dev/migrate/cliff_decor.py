"""The cliffs and the stones on the grass are decor (the owner's wish): drawn on a clear background, they stand on any
ground, grass, sand or snow, and the ground under them is the cell's own. Cliff001-005 are drawn by farm_tiles.py
(write_cliff_decor); Stone001/002 were the old game's grass with a stone or two on it, so the stones are lifted off
that grass (dsedit's split, the green round them turned to shadow). Both are made Layer=Decor in Tiles.ini, learnt by
decor_map.json (so the builders that put them down make Grass001+Decor(Name)), and every map cell standing on one
becomes its neighbours' ground with it over it. The old pictures go to dev\\Archive\\Decor split 2026-11-12 cliffs.
Flagstones (a homestead's floor, and the editor's stone floor brush) were Stone001 too: they're Flagstone001 now
(build_homestead.py, build_terrains.py, and homes.py for floors already laid).

  python -I "dev\\migrate\\cliff_decor.py"

Safe to run again: the pictures are drawn the same, the archive is kept as it was first made, and a map with no cliff
or stone for ground is left alone.
"""
import glob
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from common import p, write_image, read_lines, write_lines
import farm_tiles
from stone_decor import set_tiles_ini

CLIFFS = list(farm_tiles.CLIFFS)
STONES = ["Stone001", "Stone002"]
NAMES = CLIFFS + STONES
ARCHIVE = p("dev", "Archive", "Decor split 2026-11-12 cliffs", "Sprites", "Tiles")
OLD_GRASS = p("dev", "Archive", "Before Cinderlands 2026-10-21 224547", "Sprites", "Tiles", "Grass001.png")
XT, YT = 25, 21
SHADOW = (16, 14, 10)


def archive():
    """The old opaque pictures, kept once (the first run's: a later run finds them there)."""
    os.makedirs(ARCHIVE, exist_ok=True)
    for n in NAMES:
        to = os.path.join(ARCHIVE, n + ".png")
        if not os.path.exists(to):
            shutil.copyfile(p("sprites", "Tiles", n + ".png"), to)


def stone(name):
    """The stones of an old stone-on-grass tile alone: what isn't the old grass, the green fringe round them shadow."""
    from PIL import Image
    from dsedit import decor
    t = decor.rgb_of(Image.open(os.path.join(ARCHIVE, name + ".png")))
    b = decor.rgb_of(Image.open(OLD_GRASS))
    out, _, _ = decor.split(t, b, name)
    rgb = out[..., :3].astype(int)
    green = (out[..., 3] > 0) & (rgb[..., 1] > rgb[..., 0] + 8) & (rgb[..., 1] > rgb[..., 2] + 8)
    out[green] = SHADOW + (96,)
    soft = (out[..., 3] > 0) & (out[..., 3] < 255)
    out[soft, :3] = SHADOW
    out[soft, 3] = np.minimum(out[soft, 3], 110)
    return Image.fromarray(out, "RGBA")


def decor_map():
    path = os.path.join(HERE, "decor_map.json")
    with open(path, encoding="utf-8") as f:
        dm = json.load(f)
    if all(dm.get(n) == ["Grass001", n] for n in NAMES):
        return
    dm.update({n: ["Grass001", n] for n in NAMES})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(dm.items())), f, indent=1)


def minimap_colours():
    """A cliff shows on the minimap as rock (a stone or two keeps the grass's colour)."""
    path = p("dev", "Minimap Colours.txt")
    lines = [ln for ln in read_lines(path) if ln.strip()]
    lines = [("%s\t112 100 86" % ln.split("\t")[0]) if ln.split("\t")[0] in CLIFFS else ln for ln in lines]
    write_lines(path, lines)


def ground_of(cells_of, x, y):
    """What the cells round it stand on (the commonest ground that isn't one of these)."""
    import collections
    seen = collections.Counter()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        c = cells_of(x + dx, y + dy)
        if c:
            base = c.split("+")[0]
            if base not in NAMES and "Wall" not in base:
                seen[base] += 1
    return seen.most_common(1)[0][0] if seen else "Grass001"


def convert_maps():
    """Every cell on a cliff or a stone: its neighbours' ground, the cliff or stone as its decor (a cell with a decor
    already, a pine on a stone, keeps its own and loses the stone)."""
    changed = 0
    for path in glob.glob(p("maps", "**", "*.map"), recursive=True):     # (and the test maps, maps\Test)
        raw = open(path, "rb").read()
        if not any(n.encode() in raw for n in NAMES):
            continue
        lines = raw.decode("cp1252").split("\r\n")
        rows = [lines[y].split(":") for y in range(YT)]
        if not any(c.split("+")[0] in NAMES for r in rows for c in r):
            continue

        def cells_of(x, y):
            return rows[y][x] if 0 <= x < XT and 0 <= y < YT else None
        new = [r[:] for r in rows]
        for y in range(YT):
            for x in range(XT):
                parts = rows[y][x].split("+")
                if parts[0] not in NAMES:
                    continue
                has = any(q.startswith("Decor(") for q in parts[1:])
                new[y][x] = "+".join([ground_of(cells_of, x, y)] + parts[1:] + ([] if has else ["Decor(%s)" % parts[0]]))
                changed += 1
        for y in range(YT):
            lines[y] = ":".join(new[y])
        open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
        print("%s: moved over" % os.path.basename(path)[:-4])
    return changed


if __name__ == "__main__":
    archive()
    for n in farm_tiles.write_cliff_decor():
        print("drew " + n)
    for n in STONES:
        if write_image(p("sprites", "Tiles", n + ".png"), stone(n), decor=True):
            print("drew " + n)
    for n in NAMES:
        set_tiles_ini(n)
    decor_map()
    minimap_colours()
    print("cells made decor:", convert_maps())
