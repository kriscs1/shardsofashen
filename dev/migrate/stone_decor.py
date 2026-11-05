"""Standing stones are decor (the owner's wish): one stands on any ground, snow, sand or grass, and the ground under it
is the cell's own. Draws Standing_Stone001 on a clear background with its outline, makes it Layer=Decor in Tiles.ini,
and turns every map cell whose ground was the stone into its neighbours' ground with the stone over it.

  python -I "dev\\migrate\\stone_decor.py"

Safe to run again: the picture is drawn the same, and a map with no stone for ground is left alone.
"""
import collections
import glob
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p

NAME = "Standing_Stone001"
XT, YT = 25, 21


def draw():
    img = pygame.Surface((32, 32), pygame.SRCALPHA)
    shadow = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 70), (9, 25, 18, 6))
    img.blit(shadow, (0, 0))
    body = pygame.Surface((32, 32), pygame.SRCALPHA)
    for y in range(3, 29):                                  # (a tall stone, a little leaning, rounded at the top)
        w = 4 if y < 5 else 5 if y < 8 else 6 if y < 24 else 7
        lean = (28 - y) // 12
        for x in range(16 - w + lean, 16 + w + lean - 1):
            side = x - (16 - w + lean)
            col = (158, 156, 148) if side < 3 else (128, 126, 118) if side < w + 1 else (96, 94, 88)
            if (x * 7 + y * 13) % 11 == 0:
                col = tuple(c - 14 for c in col)            # (pits in the stone)
            body.set_at((x, y), col + (255,))
    for x, y in ((14, 11), (15, 12), (16, 12), (17, 11), (17, 10), (16, 9), (15, 10),       # (a spiral, worn)
                 (15, 17), (16, 18), (17, 17), (16, 16)):
        body.set_at((x, y), (84, 140, 150, 255))
    for x, y in ((12, 22), (13, 23), (13, 24), (19, 20), (20, 21), (12, 15)):            # (lichen)
        if body.get_at((x, y)).a:
            body.set_at((x, y), (120, 140, 84, 255))
    mask = pygame.mask.from_surface(body)
    for x, y in mask.outline():
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 32 and 0 <= ny < 32 and not mask.get_at((nx, ny)):
                body.set_at((nx, ny), (40, 40, 38, 255))
    img.blit(body, (0, 0))
    pygame.image.save(img, p("sprites", "Tiles", NAME + ".png"))


def set_tiles_ini():
    path = p("data", "Tiles.ini")
    text = open(path, "rb").read().decode("cp1252")
    head = "[%s]\r\n" % NAME
    i = text.index(head) + len(head)
    j = text.find("\r\n[", i)
    keep = [ln for ln in text[i:j].split("\r\n") if ln and not ln.startswith(("Blend", "Layer="))]
    body = "\r\n".join(keep + ["Layer=Decor"]) + "\r\n"     # (and the blank line between sections)
    text = text[:i] + body + text[j:]
    open(path, "wb").write(text.encode("cp1252"))


def ground_of(rows, x, y, cells_of):
    """What the cells round it stand on (the commonest ground that isn't a stone)."""
    seen = collections.Counter()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        c = cells_of(x + dx, y + dy)
        if c:
            base = c.split("+")[0]
            if base != NAME and "Wall" not in base:
                seen[base] += 1
    return seen.most_common(1)[0][0] if seen else "Grass001"


def convert_maps():
    changed = 0
    for path in glob.glob(p("maps", "*.txt")):
        raw = open(path, "rb").read()
        if NAME.encode() not in raw:
            continue
        lines = raw.decode("cp1252").split("\r\n")
        rows = [lines[y].split(":") for y in range(YT)]
        if not any(c.split("+")[0] == NAME for r in rows for c in r):
            continue

        def cells_of(x, y):
            return rows[y][x] if 0 <= x < XT and 0 <= y < YT else None
        for y in range(YT):
            for x in range(XT):
                c = rows[y][x]
                parts = c.split("+")
                if parts[0] != NAME or any(q.startswith("Decor(") for q in parts[1:]):
                    continue
                rows[y][x] = "+".join([ground_of(rows, x, y, cells_of)] + parts[1:] + ["Decor(%s)" % NAME])
                changed += 1
        for y in range(YT):
            lines[y] = ":".join(rows[y])
        open(path, "wb").write("\r\n".join(lines).encode("cp1252"))
    return changed


if __name__ == "__main__":
    pygame.init()
    draw()
    set_tiles_ini()
    print("stones made decor:", convert_maps())
