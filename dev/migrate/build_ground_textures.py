"""The wide natural grounds painted from big seamless textures, so nothing shows as tiles (CLAUDE.md, "Nothing looks like a
grid"): grass, sand and the sea (sprites\\Textures\\Grass.png, Sand.png, Water.png), and lava, which moves: its crust
creeping over a molten glow in LAVA_FRAMES pictures that loop (Lava_0... , and Lava.png the first, for the editor), picked by
Texture.Frames and Texture.Speed in Tiles.ini. The colours are the old tiles' own, so all that's painted over them still
fits. Each tile's picture becomes one cell of its texture (for the editor and the minimap). Safe to run again.

  python -I "dev\\migrate\\build_ground_textures.py"
"""
import math
import os
import random
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sprite_kit as K                                       # noqa: E402
from build_terrain import ramp, save_texture, cell_of   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SIZE = 384
LAVA_SIZE = 192
LAVA_FRAMES = 8
LAVA_SPEED = 380            # (milliseconds a frame: a slow crawl)

GRASS = [(0.00, (60, 84, 22)), (0.28, (70, 98, 25)), (0.52, (75, 106, 27)), (0.76, (81, 115, 29)), (1.00, (92, 126, 40))]
SAND = [(0.00, (188, 164, 114)), (0.30, (203, 181, 127)), (0.55, (209, 187, 133)), (0.80, (214, 192, 138)), (1.00, (222, 201, 150))]
WATER = [(0.00, (11, 35, 148)), (0.35, (14, 40, 158)), (0.60, (18, 43, 163)), (0.85, (22, 47, 170)), (1.00, (30, 56, 188))]
LAVA = [(0.00, (52, 14, 8)), (0.24, (82, 20, 8)), (0.40, (128, 30, 6)), (0.55, (190, 54, 8)), (0.70, (236, 106, 16)),
        (0.86, (252, 170, 40)), (1.00, (255, 224, 112))]     # (crust a dark red, never grey: the owner's wish)


def soft(rng, size, beta, low=0.0):
    """Noise with no direction and no lattice, wrapping at its edges: white noise shaped by its spectrum (1/f^beta), low: the
    wavelengths longer than that part of the picture taken out."""
    np_rng = np.random.default_rng(rng.randrange(2 ** 31))
    f = np.fft.fftfreq(size)
    r = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    r[0, 0] = 1
    amp = r ** -beta
    amp[r < low] = 0
    amp[0, 0] = 0
    out = np.fft.ifft2(np.fft.fft2(np_rng.standard_normal((size, size))) * amp).real
    return (out - out.min()) / (out.max() - out.min())


def stretch(v):
    """0..1, by its own spread: the shades all used, whatever the noise did."""
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    return np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)


def steps(v, n):
    """Into n flat shades: pixel art, not an airbrush."""
    return np.floor(v * n).clip(0, n - 1) / (n - 1)


def specks(rng, shape, count, length):
    """-1, 0 or 1 here and there, in short upright marks that wrap: blades of grass, a stone in the sand."""
    out = np.zeros(shape)
    h, w = shape
    for _ in range(count):
        x, y, sign = rng.randrange(w), rng.randrange(h), rng.choice((-1, 1))
        for k in range(rng.randint(1, length)):
            out[(y + k) % h, x] = sign
    return out


def grass_texture(seed=31):
    rng = random.Random(seed)
    patches = soft(rng, SIZE, 1.6)                           # (wide drifts of lusher and drier)
    tufts = soft(rng, SIZE, 0.7, low=0.08)
    v = stretch(0.6 * stretch(patches) + 0.4 * stretch(tufts))
    v = np.clip(steps(v, 6) + 0.17 * specks(rng, v.shape, SIZE * SIZE // 26, 3), 0, 1)
    return ramp(v, GRASS)


def sand_texture(seed=32):
    rng = random.Random(seed)
    drift = stretch(soft(rng, SIZE, 1.7))
    warp = soft(rng, SIZE, 1.8)
    ys = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    ripple = np.sin((ys * 8 / SIZE + warp * 3.0) * 2 * math.pi) * 0.5 + 0.5    # (wind's ripples: whole waves, so it wraps)
    grain = stretch(soft(rng, SIZE, 0.5, low=0.1))
    v = stretch(0.5 * drift + 0.22 * ripple + 0.28 * grain)
    v = np.clip(steps(v, 6) + 0.2 * specks(rng, v.shape, SIZE * SIZE // 90, 1), 0, 1)
    return ramp(v, SAND)


def water_texture(seed=33):
    rng = random.Random(seed)
    deep = stretch(soft(rng, SIZE, 1.8))
    warp = soft(rng, SIZE, 1.9)
    ys = np.arange(SIZE)[:, None] * np.ones((1, SIZE))
    swell = np.sin((ys * 14 / SIZE + warp * 3.5) * 2 * math.pi) * 0.5 + 0.5    # (long lines of swell, bending)
    chop = stretch(soft(rng, SIZE, 0.8, low=0.05))
    v = stretch(0.5 * deep + 0.28 * swell + 0.22 * chop)
    return ramp(steps(v, 6), WATER)


def lava_frames(seed=34):
    """Glowing cracks between dark plates of crust, the two fields of noise fading into each other and back, so the frames
    loop: the crust moves, it never jumps."""
    rng = random.Random(seed)
    fields = [1 - np.abs(2 * soft(rng, LAVA_SIZE, 2.1) - 1) for _ in range(3)]     # (ridges: the cracks' lines)
    heat = stretch(soft(rng, LAVA_SIZE, 1.9))
    out = []
    for f in range(LAVA_FRAMES):
        t = f / LAVA_FRAMES * 2 * math.pi
        w = [0.5 + 0.5 * math.cos(t + k * 2 * math.pi / 3) for k in range(3)]
        mix = sum(a * b for a, b in zip(w, fields)) / sum(w)
        glow = stretch(mix) ** 2.6                           # (crust, and plenty of bright veins)
        v = np.clip(0.26 + 0.7 * glow + 0.22 * (heat - 0.5) + 0.05 * math.sin(t), 0, 1)
        out.append(ramp(steps(v, 12), LAVA))
    return out


def main():
    for name, tile, arr in (("Grass", "Grass001", grass_texture()), ("Sand", "Sand001", sand_texture()),
                            ("Water", "Water001", water_texture())):
        save_texture(name, arr.astype(np.uint8))
        K.save("Tiles", tile, cell_of(arr.astype(np.uint8), 0))
    frames = lava_frames()
    for f, arr in enumerate(frames):
        save_texture("Lava_%d" % f, arr.astype(np.uint8))
    save_texture("Lava", frames[0].astype(np.uint8))
    K.save("Tiles", "Lava001", cell_of(frames[0].astype(np.uint8), 0))

    # (cp1252, CRLF: each tile's Texture lines, once)
    path = os.path.join(ROOT, "data", "Tiles.ini")
    text = open(path, "rb").read().decode("cp1252")
    for tile, adds in (("Grass001", ["Texture=Grass"]), ("Sand001", ["Texture=Sand"]), ("Water001", ["Texture=Water"]),
                       ("Lava001", ["Texture=Lava", "Texture.Frames=%d" % LAVA_FRAMES, "Texture.Speed=%d" % LAVA_SPEED,
                                    "Blend=9"])):                # (lava runs over what's round it, not under)
        head = "[%s]\r\n" % tile
        at = text.index(head) + len(head)
        end = text.find("\r\n[", at)
        have = text[at:end]
        for line in adds:
            if not re.search("(?m)^" + re.escape(line.split("=")[0]) + "=", have):
                text = text[:at] + line + "\r\n" + text[at:]
    open(path, "wb").write(text.encode("cp1252"))
    print("Grass, sand, water and %d frames of lava written" % LAVA_FRAMES)


if __name__ == "__main__":
    main()
