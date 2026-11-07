"""Planks and marble drawn nicer (the owner's wish).

  * Plank001 (house floors, jetties, roads of planks): four boards a tile tall, each its own warm brown with long grain
    along it, a lit top edge and a dark gap below, butt joints that don't line up from board to board, a nail at each end
    and the odd knot. It still tiles (the grain wraps).
  * Marble001 (the indoor marble floor: palace_tiles.marble_floor, polished squares, veined, a glint) and Marble_Paving001
    (the streets' marble: a big seamless texture of slabs, sheen and long veins; build_terrain.marble_slabs).
  * Everything with one of those floors drawn into it is drawn again on the new one: the thin walls of Plank and Marble rooms
    (house_tiles.thin_wall), the furniture made for marble floors (Table201...), and the palace's carpet runner.

Safe to run again.

  python -I "dev\\migrate\\build_nicer_floors.py"      (then export_web_assets.py, build_minimaps.py)
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprite_kit as K                                       # noqa: E402
from common import p, write_sprite                           # noqa: E402

S = 32
BOARD = [(150, 98, 48), (140, 90, 42), (158, 104, 54), (132, 84, 40), (146, 94, 46)]


def plank_floor():
    rng = random.Random(4417)
    img = np.zeros((S, S, 3), dtype=np.float32)
    joints = [10, 26, 4, 19]                                        # (where each board's butt joint falls)
    for b in range(4):
        y0 = b * 8
        base = np.array(BOARD[(b * 2 + rng.randrange(2)) % len(BOARD)], dtype=np.float32)
        grain = np.cumsum(np.array([rng.uniform(-1, 1) for _ in range(S)]))      # (long streaks along the board)
        for y in range(8):
            row = base * (1.0 + 0.045 * np.sin((y + b * 3) * 1.7))
            for x in range(S):
                tone = 1.0 + 0.012 * grain[(x + b * 5) % S] + rng.uniform(-0.03, 0.03)
                img[y0 + y, x] = row * tone
            if y in (3, 4, 6):                                       # (a fine dark streak or two in the grain)
                streak = rng.randrange(S)
                for x in range(streak, streak + rng.randint(6, 14)):
                    img[y0 + y, x % S] *= 0.9
        img[y0] *= 1.12                                              # (the board's lit top edge)
        img[y0 + 6] *= 0.94
        img[y0 + 7] = (74, 46, 24)                                   # (the gap under it)
        j = joints[b]
        img[y0:y0 + 7, j] = (84, 52, 27)                             # (butt joint, with a lit edge after it)
        img[y0 + 1:y0 + 7, (j + 1) % S] *= 1.08
        for nx in (j - 3, j + 3):                                    # (a nail each side of it)
            img[y0 + 3, nx % S] = (58, 36, 20)
            img[y0 + 2, nx % S] = (196, 150, 90)
        if b % 2 == 0:                                               # (a knot)
            kx, ky = (j + 11) % S, y0 + 3
            for dx, dy, k in ((0, 0, 0.62), (1, 0, 0.72), (-1, 0, 0.72), (0, 1, 0.8), (0, -1, 0.8)):
                img[(ky + dy) % S, (kx + dx) % S] *= k
    return np.clip(img, 0, 255)


def rows_of(img):
    return [[tuple(int(v) for v in img[y, x]) for x in range(S)] for y in range(S)]


def save_tile(name, rows):
    return K.save("Tiles", name, rows)


def redraw_dependents():
    import house_tiles as H
    import interior_tiles as I
    import palace_tiles as P
    n = 0
    for wall in H.WALL_BASES:
        for floor in ("Plank001", "Marble001"):
            for edges in H.THIN_EDGES:
                name = H.thin_name(wall, floor, edges)
                n += bool(save_tile(name, rows_of(np.array(H.thin_wall(wall, floor, edges)))))
    for f in ("Marble001",):                                          # (furniture drawn on a marble floor: Table201...)
        for base in I.FURNITURE:
            name = I.furniture_on(base, f)
            n += bool(save_tile(name, I.TILES[name]()))
    n += bool(save_tile("Carpet001", P.TILES["Carpet001"]()))
    return n


def main():
    changed = []
    if write_sprite(p("sprites", "Tiles", "Plank001.png"), [[(0, 0, 0)] * S for _ in range(S)] + rows_of(plank_floor())):
        changed.append("Plank001")
    import palace_tiles as P
    if save_tile("Marble001", P.TILES["Marble001"]()):
        changed.append("Marble001")
    import build_terrain as T
    arr = T.STREETS["Marble_Paving001"][1](random.Random("Street_Marble"))
    T.save_texture("Street_Marble", arr)
    save_tile("Marble_Paving001", T.cell_of(arr, 0))
    n = redraw_dependents()
    print("Nicer floors: %s; Street_Marble redrawn; %d baked tiles redrawn" % (", ".join(changed) or "no floor changed", n))


if __name__ == "__main__":
    main()
