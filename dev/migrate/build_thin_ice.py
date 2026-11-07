"""Thin, cracked ice for the rivers and lakes that freeze in winter (the owner's wish: not walkable). It isn't the thick
Ice001 of the Rime's frozen lakes (that one carries you): Thin_Ice001 is dark water under a skin of pale ice, split by
cracks that run on across tile after tile (a big seamless texture, sprites\\Textures\\Thin_Ice.png, never one picture
repeated). Nothing walks on it: it's the water's own walk mask, so a frozen river stops you as the river did.

  * data\\Seasons.ini: Ice=Thin_Ice001 (dsengine/seasons.py turns a river's Water001 to it in winter and back).
  * data\\Tiles.ini: Thin_Ice001 (Texture=Thin_Ice, Round=1, sight clear, not walkable).

Safe to run again.

  python -I "dev\\migrate\\build_thin_ice.py"        (then export_web_assets.py)
"""
import os
import random
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprite_kit as K                                       # noqa: E402
from build_terrain import ramp, save_texture, cell_of        # noqa: E402
from build_ground_textures import soft, stretch, steps       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SIZE = 384
# (dark water showing through, to the pale skin of ice)
SKIN = [(0.00, (70, 108, 156)), (0.30, (102, 142, 186)), (0.55, (136, 174, 208)), (0.80, (170, 202, 226)),
        (1.00, (200, 224, 240))]
CRACK = (232, 242, 250)
CRACK_DEEP = (22, 40, 84)


def voronoi_edges(rng, count):
    """How close each pixel is to the line between its two nearest seeds, on a torus (so it tiles); the lines wander (the
    ground is warped by noise first) and are all as wide, whatever the seeds' angles."""
    pts = np.array([(rng.random() * SIZE, rng.random() * SIZE) for _ in range(count)])
    ys, xs = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    xs = (xs + (soft(rng, SIZE, 1.7) - 0.5) * 22) % SIZE
    ys = (ys + (soft(rng, SIZE, 1.7) - 0.5) * 22) % SIZE
    d = []
    for px, py in pts:
        dx = np.abs(xs - px)
        dy = np.abs(ys - py)
        dx = np.minimum(dx, SIZE - dx)
        dy = np.minimum(dy, SIZE - dy)
        d.append(np.sqrt(dx * dx + dy * dy))
    d = np.sort(np.stack(d), axis=0)
    gap = d[1] - d[0]
    gy, gx = np.gradient(gap)
    return gap / np.maximum(np.sqrt(gx * gx + gy * gy), 0.35)


def thin_ice_texture(seed=41):
    rng = random.Random(seed)
    water = stretch(soft(rng, SIZE, 1.9))                               # (where the water shows dark through the skin)
    frost = stretch(soft(rng, SIZE, 0.9, low=0.05))
    v = stretch(0.65 * water + 0.35 * frost)
    img = ramp(steps(v, 6), SKIN)
    big = voronoi_edges(rng, 46)                                        # (long cracks, the plates of ice)
    fine = voronoi_edges(rng, 150)                                      # (a finer web in some of the plates)
    web = stretch(soft(rng, SIZE, 1.6)) > 0.58
    line = (big < 1.3) | ((fine < 0.9) & web)
    deep = ((big >= 1.3) & (big < 2.4) & (np.roll(big, 1, axis=0) < 1.3)) | \
           ((fine >= 0.9) & (fine < 1.8) & web & (np.roll(fine, 1, axis=1) < 0.9))
    img[deep] = 0.55 * img[deep] + 0.45 * np.array(CRACK_DEEP)          # (a dark edge under each crack: it's open to the water)
    img[line] = 0.2 * img[line] + 0.8 * np.array(CRACK)
    spark = np.random.default_rng(seed).random((SIZE, SIZE)) < 0.004    # (a glint here and there)
    img[spark & ~line] = 0.4 * img[spark & ~line] + 0.6 * 255
    return img


def main():
    arr = thin_ice_texture().astype(np.uint8)
    save_texture("Thin_Ice", arr)
    K.save("Tiles", "Thin_Ice001", cell_of(arr, 0))

    sys.path.insert(0, HERE)
    from common import p, Ini
    ini = Ini(p("data", "Tiles.ini"))
    for key, v in (("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Use.Words", ""),
                   ("Examine.Info", "Thin ice, cracked and dark over the water. It wouldn't hold a cat."),
                   ("Line.of.Sight", "1"), ("Blend", "1"), ("Blend.Texture", "Thin_Ice001"), ("Round", "1"),
                   ("Texture", "Thin_Ice")):
        if ini.get("Thin_Ice001", key) != v:
            ini.set("Thin_Ice001", key, v)
    ini.save(p("data", "Tiles.ini"))

    for path in (os.path.join(ROOT, "data", "Seasons.ini"),):
        text = open(path, "rb").read().decode("cp1252")
        new = re.sub(r"(?m)^Ice=.*$", "Ice=Thin_Ice001", text)
        if new != text:
            open(path, "wb").write(new.encode("cp1252"))
    print("Thin_Ice001 and its texture written; the seasons freeze rivers to it")


if __name__ == "__main__":
    main()
