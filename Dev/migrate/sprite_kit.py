"""Small pixel-art toolkit for the Dragon Sword sprite generators (build_tiles.py, build_sprites.py).

An image is a list of rows of (r, g, b) tuples or None (None = transparent). Saving writes the LB sprite format:
a 24-bit BMP twice the visible height, top half = mask (black = drawn, white = see-through),
bottom half = image (black where see-through).
"""
import colorsys
import math
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p, read_bmp, write_sprite

S = 32


def clamp(v):
    return max(0, min(255, int(round(v))))


def new(w=S, h=S, fill=None):
    return [[fill] * w for _ in range(h)]


def copy(img):
    return [r[:] for r in img]


def size(img):
    return len(img[0]), len(img)


def put(img, x, y, c, wrap=False):
    w, h = size(img)
    if wrap:
        img[y % h][x % w] = c
    elif 0 <= x < w and 0 <= y < h:
        img[y][x] = c


def get(img, x, y, wrap=False):
    w, h = size(img)
    if wrap:
        return img[y % h][x % w]
    if 0 <= x < w and 0 <= y < h:
        return img[y][x]
    return None


def mul(c, f):
    return tuple(clamp(v * f) for v in c)


def add(c, d):
    return tuple(clamp(v + d) for v in c)


def mix(a, b, t):
    return tuple(clamp(a[i] + (b[i] - a[i]) * t) for i in range(3))


def jitter(c, rng, amt):
    d = rng.uniform(-amt, amt)
    return tuple(clamp(v + d) for v in c)


def rect(img, x0, y0, x1, y1, c, wrap=False):
    """Inclusive rectangle."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(img, x, y, c, wrap)


def line(img, x0, y0, x1, y1, c, wrap=False):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        put(img, int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n)), c, wrap)


def shaded_ellipse(img, cx, cy, rx, ry, base, light, dark, rng=None, noise=0, outline=None, wrap=False,
                   light_dir=(-0.7, -0.7), hi=None):
    """Filled ellipse lit from the top-left: light / base / dark bands, optional outline and highlight."""
    rng = rng or random.Random(1)
    for y in range(int(math.floor(cy - ry)) - 1, int(math.ceil(cy + ry)) + 2):
        for x in range(int(math.floor(cx - rx)) - 1, int(math.ceil(cx + rx)) + 2):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = dx * dx + dy * dy
            if d > 1.0:
                continue
            k = (dx * light_dir[0] + dy * light_dir[1]) + (rng.uniform(-noise, noise) if noise else 0)
            if outline and d > 0.80:
                c = outline
            elif hi and k > 0.55 and d < 0.45:
                c = hi
            elif k > 0.35:
                c = light
            elif k < -0.4:
                c = dark
            else:
                c = base
            if noise:
                c = jitter(c, rng, 5)
            put(img, x, y, c, wrap)


def outline_img(img, col, diagonal=False):
    """Adds a 1px outline (col) on transparent pixels next to drawn ones."""
    w, h = size(img)
    out = copy(img)
    for y in range(h):
        for x in range(w):
            if img[y][x] is not None:
                continue
            nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            if diagonal:
                nb += [(1, 1), (-1, -1), (1, -1), (-1, 1)]
            for dx, dy in nb:
                if get(img, x + dx, y + dy) is not None:
                    out[y][x] = col
                    break
    return out


def paste(dst, src, ox=0, oy=0, wrap=False):
    for y, row in enumerate(src):
        for x, c in enumerate(row):
            if c is not None:
                put(dst, ox + x, oy + y, c, wrap)


def from_ascii(rows, pal, width=S, height=S, ox=None, oy=0):
    """rows: strings; pal: char -> colour (space and '.' are transparent). Centred horizontally unless ox given."""
    img = new(width, height)
    wmax = max(len(r) for r in rows)
    if ox is None:
        ox = (width - wmax) // 2
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in " .":
                continue
            if ch not in pal:
                raise KeyError("no colour for %r in %r" % (ch, r))
            if pal[ch] is not None:
                put(img, ox + x, oy + y, pal[ch])
    return img


def lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0


def gradient_map(img, stops):
    """Recolours by luminance. stops: list of (lum 0..1, colour)."""
    out = copy(img)
    stops = sorted(stops)
    for y, row in enumerate(img):
        for x, c in enumerate(row):
            if c is None:
                continue
            l = lum(c)
            if l <= stops[0][0]:
                out[y][x] = stops[0][1]
                continue
            if l >= stops[-1][0]:
                out[y][x] = stops[-1][1]
                continue
            for (l0, c0), (l1, c1) in zip(stops, stops[1:]):
                if l0 <= l <= l1:
                    out[y][x] = mix(c0, c1, (l - l0) / max(1e-6, l1 - l0))
                    break
    return out


def hue_shift(img, target_hue=None, dh=0.0, sat=None, sat_mul=1.0, val_mul=1.0, pred=None):
    """Changes hue (absolute target_hue 0..1, or relative dh), saturation and value. pred(c) limits which pixels."""
    out = copy(img)
    for y, row in enumerate(img):
        for x, c in enumerate(row):
            if c is None or (pred and not pred(c)):
                continue
            h, s, v = colorsys.rgb_to_hsv(*(t / 255.0 for t in c))
            h = target_hue if target_hue is not None else (h + dh) % 1.0
            s = min(1.0, (sat if sat is not None else s) * sat_mul)
            v = min(1.0, v * val_mul)
            out[y][x] = tuple(clamp(t * 255) for t in colorsys.hsv_to_rgb(h, s, v))
    return out


def flip_h(img):
    return [list(reversed(r)) for r in img]


def shift(img, dx, dy):
    w, h = size(img)
    out = new(w, h)
    for y in range(h):
        for x in range(w):
            if img[y][x] is not None:
                put(out, x + dx, y + dy, img[y][x])
    return out


def bbox(img):
    xs = [x for row in img for x, c in enumerate(row) if c is not None]
    ys = [y for y, row in enumerate(img) for c in row if c is not None]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)


def centre_bottom(img, bottom=30):
    """Centres the drawn part horizontally and puts its lowest pixel on row `bottom`."""
    x0, y0, x1, y1 = bbox(img)
    w, h = size(img)
    return shift(img, (w - 1 - x1 - x0) // 2, bottom - y1)


def noise_field(rng, w, h, amp, blur=1):
    """Tileable smooth noise in -amp..amp (box blur on a torus)."""
    f = [[rng.uniform(-1, 1) for _ in range(w)] for _ in range(h)]
    for _ in range(blur):
        g = [[0.0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                t = 0.0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        t += f[(y + dy) % h][(x + dx) % w]
                g[y][x] = t / 9.0
        f = g
    m = max(abs(v) for r in f for v in r) or 1
    return [[v / m * amp for v in r] for r in f]


# ---------------------------------------------------------------- io
def load(kind, name):
    """Loads Sprites\\<kind>\\<name>.png as an image with None where it is see-through."""
    w, h, rows = read_bmp(p("Sprites", kind, name + ".png"))
    half = h // 2
    return [[(rows[half + y][x] if sum(rows[y][x]) < 384 else None) for x in range(w)] for y in range(half)]


def save(kind, name, img):
    """Writes Sprites\\<kind>\\<name>.png only if it changed (None = see-through). Returns True when written."""
    rows = [[(0, 0, 0) if c is not None else (255, 255, 255) for c in r] for r in img]
    rows += [[c if c is not None else (0, 0, 0) for c in r] for r in img]
    return write_sprite(p("Sprites", kind, name + ".png"), rows)


def write_png(path, img, bg=None):
    w, h = size(img)
    rows = []
    for y in range(h):
        r = []
        for x in range(w):
            c = img[y][x]
            if c is None:
                c = bg(x, y) if bg else (0, 0, 0)
            r.append(c)
        rows.append(r)
    from render_maps import write_png as wp
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wp(path, rows)


def checker(x, y):
    return (70, 40, 70) if ((x // 4 + y // 4) % 2) else (50, 28, 50)


def sheet(path, items, scale=3, cols=8, label_h=0, tile_repeat=1):
    """Preview sheet: items = list of images. tile_repeat>1 tiles each image NxN (seam check)."""
    cw = max(size(i)[0] for i in items) * tile_repeat * scale + 6
    ch = max(size(i)[1] for i in items) * tile_repeat * scale + 6
    rows = (len(items) + cols - 1) // cols
    W, H = min(cols, len(items)) * cw, rows * ch
    out = [[(30, 30, 30)] * W for _ in range(H)]
    for n, img in enumerate(items):
        w, h = size(img)
        ox, oy = (n % cols) * cw + 3, (n // cols) * ch + 3
        for y in range(h * tile_repeat * scale):
            for x in range(w * tile_repeat * scale):
                sx, sy = (x // scale) % w, (y // scale) % h
                c = img[sy][sx]
                out[oy + y][ox + x] = c if c is not None else checker(x, y)
    from render_maps import write_png as wp
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wp(path, out)
