"""Forest canopy: a seamless 128 x 128 texture of overlapping tree crowns (sprites\\Textures\\Forest_Canopy.png, a plain
picture) that the Python game paints forest tiles from (Tiles.ini Forest001 Texture=Forest_Canopy), so the forest
doesn't repeat every tile. Also writes sprites\\Tiles\\Forest001.png as one tile of it (for the Liberty BASIC tools and
the edge blending). Run: python dev\\migrate\\build_forest.py
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprite_kit as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SIZE = 128


def canopy(seed=11):
    rng = random.Random(seed)
    img = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    img[:, :] = (30, 46, 20)  # Deep shade between the crowns
    ys, xs = np.mgrid[0:SIZE, 0:SIZE]
    crowns = []
    for _ in range(95):
        crowns.append((rng.uniform(0, SIZE), rng.uniform(0, SIZE), rng.uniform(6.5, 12.5), rng.uniform(-1, 1),
                       rng.uniform(-1, 1)))
    crowns.sort(key=lambda c: c[1])  # Lower crowns overlap higher ones
    for cx, cy, r, hue, var in crowns:
        # Distances on a torus, so the texture tiles seamlessly
        dx = (xs - cx + SIZE / 2) % SIZE - SIZE / 2
        dy = (ys - cy + SIZE / 2) % SIZE - SIZE / 2
        # Its shadow on what is below and to the right
        sd = np.sqrt((dx - 2) ** 2 + (dy - 3) ** 2) / r
        img[sd < 1.0] *= 0.72
        # Lumpy edge: the radius wobbles with the angle
        ang = np.arctan2(dy, dx)
        wob = 1 + 0.10 * np.sin(ang * 5 + var * 3) + 0.06 * np.sin(ang * 9 + hue * 5)
        d = np.sqrt(dx ** 2 + dy ** 2) / (r * wob)
        inside = d < 1.0
        # Lit from the top left, rounder in the middle
        k = np.clip(-(dx + dy) / (r * 1.6) + (1 - d) * 0.55, -1, 1)
        # Olive greens, like the grass round the forest
        dark = np.array((44 + 6 * hue, 70 + 8 * var, 26), dtype=np.float32)
        mid = np.array((78 + 10 * hue, 108 + 10 * var, 36 - 4 * hue), dtype=np.float32)
        light = np.array((128 + 14 * hue, 152 + 10 * var, 56 - 6 * hue), dtype=np.float32)
        t = (k + 1) / 2
        col = np.where((t < 0.5)[..., None], dark + (mid - dark) * (t * 2)[..., None],
                       mid + (light - mid) * ((t - 0.5) * 2)[..., None])
        edge = inside & (d > 0.86)
        col[edge] = col[edge] * 0.62
        img[inside] = col[inside]
    # Leafy grain
    noise = np.array([[rng.uniform(-9, 9) for _ in range(SIZE)] for _ in range(SIZE)], dtype=np.float32)
    img += noise[..., None]
    img *= 0.86  # A shade darker than the open grass round it
    return np.clip(img, 0, 255).astype(np.uint8)


def save_plain_bmp(path, arr):
    """A plain picture (no transparency) as a PNG."""
    from common import write_sprite
    write_sprite(path, [[tuple(int(v) for v in c) for c in r] for r in arr], plain=True)


def main():
    arr = canopy()
    save_plain_bmp(os.path.join(ROOT, "sprites", "Textures", "Forest_Canopy.png"), arr)
    tile = [[tuple(int(v) for v in arr[y, x]) for x in range(32)] for y in range(32)]
    K.save("Tiles", "Forest001", tile)
    print("Forest canopy written (sprites\\Textures\\Forest_Canopy.png, sprites\\Tiles\\Forest001.png)")


if __name__ == "__main__":
    main()
