"""Rocks that look like rock, not a ball: a ragged outline, flat chipped faces (each its own slope, lit from the top
left), cracks along where two faces meet, a darker underside and a shadow on the ground below right. Sandstone gets
bands across it (the layers it was laid down in), a grey boulder moss and lichen on its top. Used by
region_tiles.py and nature_tiles.py (their opaque pictures) and written as see-through decor by write_decor()
(build_tiles.py runs it): the rocks are decor, laid over whatever ground they're on, so the shadow's see-through."""
import math
import random

S = 32


def _clamp(v):
    return max(0, min(255, int(round(v))))


def outline(rng, cx, cy, rx, ry, n=9, flat_base=True, flat_top=False):
    """A ragged, roughly convex outline round cx, cy: n points, each its own way out (so its sides are straight
    breaks, not a curve), the bottom flatter (it sits)."""
    pts = []
    for i in range(n):
        a = (i + rng.uniform(-0.3, 0.3)) / n * 2 * math.pi
        k = rng.uniform(0.76, 1.08)
        x, y = math.cos(a) * rx * k, math.sin(a) * ry * k
        if flat_base and y > 0:
            y *= 0.8                                       # (it sits on the ground: a flatter base)
        if flat_top and y < -ry * 0.72:
            y = -ry * 0.72 + (y + ry * 0.72) * 0.25        # (a block, worn flat on top)
        pts.append((cx + x, cy + y))
    return pts


def inside(pts, x, y):
    c = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            c = not c
        j = i
    return c


def faceted_rock(img, rng, cx, cy, rx, ry, lit, mid, dark, line, strata=0.0, moss=None, faces=7, marks=None,
                 flat_top=False):
    """Draws a rock on img (rows of (r, g, b), changed in place). lit/mid/dark: its colours in light, half light
    and shade; line: its outline. strata: how strongly it's banded (sandstone); moss: colours for its top, or None.
    marks: a dict told which pixels are its shadow ("shadow") and which the rock ("rock")."""
    marks = {} if marks is None else marks
    pts = outline(rng, cx, cy, rx, ry, flat_top=flat_top)
    body = [[inside(pts, x + 0.5, y + 0.5) for x in range(S)] for y in range(S)]
    # its shadow on the ground, below right
    for y in range(S):
        for x in range(S):
            dx, dy = (x + 0.5 - cx - 2.5) / (rx + 1), (y + 0.5 - cy - ry * 0.55) / (ry * 0.55 + 0.5)
            if dx * dx + dy * dy <= 1 and not body[y][x]:
                img[y][x] = tuple(_clamp(v * 0.62) for v in img[y][x])
                marks.setdefault((x, y), "shadow")
    # the faces: points inside it, each with its own slope (leaning out from the middle, the top ones skyward)
    seeds = []
    while len(seeds) < faces:
        x, y = rng.uniform(cx - rx * 0.8, cx + rx * 0.8), rng.uniform(cy - ry * 0.8, cy + ry * 0.8)
        if inside(pts, x, y):
            ox, oy = (x - cx) / rx, (y - cy) / ry
            nz = max(0.2, 0.85 - 0.7 * math.hypot(ox, oy)) + rng.uniform(-0.2, 0.2)
            nx, ny = ox * 1.2 + rng.uniform(-0.6, 0.6), oy * 1.2 + rng.uniform(-0.6, 0.6)
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            seeds.append((x, y, nx / ln, ny / ln, nz / ln))
    L = (-0.55, -0.6, 0.58)                                 # (the light: from the top left, above)
    owner = [[-1] * S for _ in range(S)]
    for y in range(S):
        for x in range(S):
            if not body[y][x]:
                continue
            best, k = 1e9, 0
            for i, (sx, sy, _, _, _) in enumerate(seeds):
                d = (x + 0.5 - sx) ** 2 + ((y + 0.5 - sy) * 1.2) ** 2
                if d < best:
                    best, k = d, i
            owner[y][x] = k
            marks[(x, y)] = "rock"
            _, _, nx, ny, nz = seeds[k]
            b = nx * L[0] + ny * L[1] + nz * L[2]           # (-1..1: how much light this face catches)
            b = max(0.0, min(1.0, 0.5 + b * 1.05))
            if y + 0.5 > cy + ry * 0.25:                     # (the underside, out of the sun)
                b *= 0.78
            col = [m + (l - m) * (b - 0.5) * 2 if b >= 0.5 else d + (m - d) * b * 2 for l, m, d in zip(lit, mid, dark)]
            if strata:
                band = math.sin((y + 0.5 + (x - cx) * 0.1) * 1.3 + seeds[k][0] * 0.25)
                col = [c * (1 + strata * (0.1 * band + (0.08 if band > 0.8 else -0.06 if band < -0.85 else 0)))
                       for c in col]
            n = rng.uniform(-6, 6)
            img[y][x] = tuple(_clamp(c + n) for c in col)
    # where two faces meet: a crack (darker), now and then
    for y in range(S - 1):
        for x in range(S - 1):
            o = owner[y][x]
            if o < 0:
                continue
            if (owner[y][x + 1] not in (o, -1) or owner[y + 1][x] not in (o, -1)) and rng.random() < 0.7:
                img[y][x] = tuple(_clamp(v * 0.8) for v in img[y][x])
    if moss:                                                  # (moss and lichen on the top, where the rain sits)
        for y in range(S):
            for x in range(S):
                if owner[y][x] >= 0 and y + 0.5 < cy - ry * 0.2 and rng.random() < 0.45 * (1 - (y - (cy - ry)) / ry):
                    img[y][x] = rng.choice(moss)
        for _ in range(4):
            x, y = int(rng.uniform(cx - rx * 0.6, cx + rx * 0.6)), int(rng.uniform(cy - ry * 0.3, cy + ry * 0.5))
            if 0 <= x < S and 0 <= y < S and owner[y][x] >= 0:
                img[y][x] = (196, 192, 150)                   # (a fleck of pale lichen)
    # the outline: dark below and right, lighter at the top left (the sun on its edge)
    for y in range(S):
        for x in range(S):
            if not body[y][x]:
                continue
            edge = any(not (0 <= x + a < S and 0 <= y + b < S and body[y + b][x + a])
                       for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                if y + 0.5 < cy - ry * 0.3 and x + 0.5 < cx + rx * 0.3:
                    img[y][x] = tuple(_clamp((v + lv) / 2 * 1.02) for v, lv in zip(img[y][x], lit))
                else:
                    img[y][x] = line
    return img


def chips(img, rng, cx, cy, rx, ry, cols, n=3, marks=None):
    """A few chips fallen from it, on the ground round its foot."""
    marks = {} if marks is None else marks
    for _ in range(n):
        a = rng.uniform(0.1, math.pi - 0.1)
        x = int(cx + math.cos(a) * (rx + rng.uniform(1.5, 3)))
        y = int(cy + math.sin(a) * (ry * 0.8 + rng.uniform(0.5, 2)))
        if 0 <= x < S - 1 and 0 <= y < S:
            img[y][x] = rng.choice(cols)
            marks[(x, y)] = "rock"
            if rng.random() < 0.5:
                img[y][x + 1] = tuple(_clamp(v * 0.7) for v in img[y][x])
                marks[(x + 1, y)] = "rock"
    return img


# ---------------------------------------------------------------- the rocks
SAND = ((240, 176, 116), (198, 112, 66), (112, 54, 34), (70, 34, 22))
GREY = ((190, 188, 178), (134, 130, 122), (70, 68, 68), (42, 40, 40))
MOSS = [(78, 116, 52), (92, 132, 60), (70, 104, 48)]


def desert_rock(img, marks=None):
    rng = random.Random(1102)
    chips(img, rng, 16, 19, 11, 8, [(170, 104, 72), (150, 90, 60)], marks=marks)
    return faceted_rock(img, rng, 16, 18, 11.5, 9, *SAND, strata=1.0, marks=marks, flat_top=True)


def boulder(img, marks=None):
    rng = random.Random(1104)
    return faceted_rock(img, rng, 16, 17, 12, 10, *GREY, moss=MOSS, faces=8, marks=marks)


def stone(img, marks=None):
    rng = random.Random(1103)
    chips(img, rng, 16, 20, 8, 6, [(120, 118, 112), (96, 94, 90)], n=2, marks=marks)
    return faceted_rock(img, rng, 16, 19, 8.5, 6.5, *GREY, moss=MOSS, faces=5, marks=marks)


ROCKS = {"Desert_Rock001": desert_rock, "Rock002": boulder, "Rock001": stone}


def decor_image(draw):
    """The rock alone, see-through round it (its shadow half see-through), as a PIL RGBA picture."""
    from PIL import Image
    img = [[(128, 128, 128)] * S for _ in range(S)]
    marks = {}
    draw(img, marks)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for (x, y), what in marks.items():
        im.putpixel((x, y), tuple(img[y][x]) + (255,) if what == "rock" else (16, 14, 10, 96))
    return im


def write_decor():
    from common import p, write_image
    return [n for n, draw in ROCKS.items() if write_image(p("sprites", "Tiles", n + ".png"), decor_image(draw), decor=True)]
