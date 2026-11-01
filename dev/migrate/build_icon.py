"""The game's icon, in the logo's look (build_logo.py: its gold, ember and Shard colours, and its crystal): a cluster of
violet Shard crystals rising out of glowing ash in a gold ring, drawn on the game's 1 px grid (64 x 64) and scaled up
square, so it's crisp at every size.

  python -I "dev\\migrate\\build_icon.py"

  * web/img/icon.png (256 x 256): the Docker container's icon (Unraid: the template's Icon), and for phones' home
    screens (apple-touch-icon). build_android.py makes the Android app's icons from it: run it after this.
  * web/img/favicon.png (64 x 64): the browser tab's icon (the grid itself, pixel for pixel).
  * web/img/icon.ico (16 to 256): the desktop app's program icon (desktop/build_desktop.py gives it to the .exe).
  * sprites/Interface/Magic_Burst.png (32 x 32): the Magic skill's icon (Config [Skills] Icon.Magic), a magical blast.
The server serves them at /img/icon.png and /img/favicon.png. Run it again to redraw them (it overwrites them)."""
import io
import math
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame  # noqa: E402
from build_logo import GOLD, EMBER, OUTLINE, SHARD, shard  # noqa: E402  (one palette and one crystal: the logo's)

OUT = os.path.join(ROOT, "web", "img")
GRID = 64                       # (the icon's own pixels: drawn at this size, then scaled up square)
SIZE = 256
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
ASH = [(30, 18, 13), (38, 22, 15), (54, 30, 20), (84, 43, 22)]      # the ground inside the ring, dark to warm
GLOW = [(44, 26, 58), (60, 36, 86)]                                 # the crystals' violet light behind them


def ring_shade(dx, dy, d):
    """The gold ring's colour where it is: lit from the top left, darker round to the bottom right."""
    lit = (-dx - dy) / (d * math.sqrt(2)) if d else 0       # (1 at the top left, -1 at the bottom right)
    return GOLD[min(len(GOLD) - 1, max(0, int((1 - lit) / 2 * 5)))]


def badge():
    """The round ground and its gold ring, at GRID (each pixel worked out: stepped bands, dithered at their edges)."""
    s = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
    c = (GRID - 1) / 2
    for y in range(GRID):
        for x in range(GRID):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            if d > c + 0.5:
                continue
            if d > c - 0.5 or c - 4.5 < d <= c - 3.5:
                s.set_at((x, y), OUTLINE)                   # (the ring's dark edges, outside and in)
            elif d > c - 3.5:
                s.set_at((x, y), ring_shade(dx, dy, d))
            else:
                warm = 1 - min(1.0, math.hypot(dx, (y - (c + 16)) * 1.3) / 34)    # (the ash glows up from below)
                band = warm * (len(ASH) - 1) + (0.25 if (x + y) % 2 else -0.25)
                s.set_at((x, y), ASH[max(0, min(len(ASH) - 1, int(band + 0.5)))])
    for gx, gy, r in ((32, 26, 17), (32, 26, 11)):          # (the crystals' light: two rings, stepped)
        for y in range(GRID):
            for x in range(GRID):
                if math.hypot(x - gx, (y - gy) * 0.9) <= r and math.hypot(x - c, y - c) < c - 4.5:
                    s.set_at((x, y), GLOW[0 if r > 11 else 1])
    return s


def crystals():
    """The Shard cluster: a tall one in the middle and two leaning out from it, outlined as one."""
    layer = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
    for cx, top, h, w, lean in ((18, 21, 28, 5, 26), (46, 21, 28, 5, -26)):
        one = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
        shard(one, GRID // 2, (GRID - h) // 2, h, w)
        one = pygame.transform.rotate(one, lean)                # (square pixels kept: rotate never smooths)
        layer.blit(one, (cx - one.get_width() // 2, top + h // 2 - one.get_height() // 2))
    shard(layer, 33, 7, 44, 8)
    mask = pygame.mask.from_surface(layer)
    out = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
    for x, y in [(x, y) for x in range(GRID) for y in range(GRID) if mask.get_at((x, y))]:
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if 0 <= x + ox < GRID and 0 <= y + oy < GRID and not mask.get_at((x + ox, y + oy)):
                out.set_at((x + ox, y + oy), OUTLINE)
    out.blit(layer, (0, 0))
    return out


def ash_and_embers(s):
    """The heap of ash the crystals rise from, embers in it and sparks rising (and a few Shard motes)."""
    c = (GRID - 1) / 2
    for y in range(GRID):
        for x in range(GRID):
            e = ((x - 32) / 23) ** 2 + ((y - 53) / 7.5) ** 2
            if e <= 1 and math.hypot(x - c, y - c) < c - 4.5:
                top = e > 0.72 and y < 53                   # (its top edge smoulders)
                s.set_at((x, y), EMBER[5] if top and e > 0.88 else ASH[1] if (x * 7 + y * 3) % 5 else ASH[2])
    for x, y, k in ((22, 50, 2), (27, 48, 1), (33, 49, 3), (39, 48, 2), (44, 50, 3), (30, 52, 4), (37, 53, 2),
                    (25, 54, 4), (41, 54, 3)):
        s.set_at((x, y), EMBER[k])                          # (embers glowing in the ash)
    for x, y, k in ((13, 38, 2), (51, 35, 1), (11, 30, 3), (54, 43, 2), (24, 14, 1), (41, 12, 2)):
        s.set_at((x, y), EMBER[k])                          # (sparks going up)
    for x, y in ((16, 18), (49, 21), (20, 44)):
        s.set_at((x, y), SHARD[1])                          # (motes of Shard essence)


def icon_grid():
    s = badge()
    s.blit(crystals(), (0, 0))
    ash_and_embers(s)
    return s


def at_size(grid, n):
    """The icon at n pixels: square-scaled where the grid goes into it whole, else doubled up sharp and smoothed down
    (pixel art neither blurred nor jagged, as build_android.py makes the launcher's)."""
    if n % GRID == 0:
        return pygame.transform.scale(grid, (n, n))
    return pygame.transform.smoothscale(pygame.transform.scale(grid, (GRID * 4, GRID * 4)), (n, n))


def save_ico(grid, path):
    """A Windows icon of every size in ICO_SIZES, each a PNG inside (as Windows has read them since Vista)."""
    pngs = []
    for n in ICO_SIZES:
        buf = io.BytesIO()
        pygame.image.save(at_size(grid, n), buf, "png")
        pngs.append((n, buf.getvalue()))
    head = struct.pack("<HHH", 0, 1, len(pngs))
    at, entries, blobs = 6 + 16 * len(pngs), b"", b""
    for n, png in pngs:
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(png), at + len(blobs))
        blobs += png
    with open(path, "wb") as f:
        f.write(head + entries + blobs)


def star(c, r_out, r_in, points, turn=0.0, wobble=None):
    pts = []
    for i in range(points * 2):
        a = turn + i * math.pi / points
        r = r_out if i % 2 == 0 else r_in
        if wobble:
            r *= wobble[i % len(wobble)]
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    return pts


def magic_burst():
    """A magical blast, drawn 4 times bigger and smoothed down to 32 x 32."""
    k = 4
    n = 32 * k
    s = pygame.Surface((n, n), pygame.SRCALPHA)
    c = n / 2
    wob = [1.0, 0.82, 1.08, 0.9, 0.95, 0.78, 1.04, 0.88]
    pygame.draw.polygon(s, (60, 20, 90), star(c, 15.5 * k, 7.5 * k, 10, 0.1, wob))         # the dark edge
    pygame.draw.polygon(s, (150, 60, 220), star(c, 14 * k, 6.5 * k, 10, 0.1, wob))         # violet flame
    pygame.draw.polygon(s, (236, 120, 255), star(c, 10.5 * k, 5 * k, 8, 0.45, wob[::-1]))  # magenta
    pygame.draw.polygon(s, (255, 214, 110), star(c, 7.5 * k, 3.6 * k, 8, 0.1))             # gold
    pygame.draw.circle(s, (255, 250, 230), (int(c), int(c)), int(3.2 * k))                  # the white-hot core
    for x, y, r in ((5, 6, 1.3), (26, 5, 1.1), (28, 24, 1.4), (4, 25, 1.0), (16, 2, 0.9)):  # sparks
        pygame.draw.circle(s, (255, 240, 180), (x * k, y * k), int(r * k))
    return pygame.transform.smoothscale(s, (32, 32))


def main():
    pygame.init()
    pygame.image.save(magic_burst(), os.path.join(ROOT, "sprites", "Interface", "Magic_Burst.png"))
    grid = icon_grid()
    os.makedirs(OUT, exist_ok=True)
    pygame.image.save(at_size(grid, SIZE), os.path.join(OUT, "icon.png"))
    pygame.image.save(grid, os.path.join(OUT, "favicon.png"))
    save_ico(grid, os.path.join(OUT, "icon.ico"))
    print("Made web/img/icon.png, favicon.png and icon.ico, and sprites/Interface/Magic_Burst.png")


if __name__ == "__main__":
    main()
