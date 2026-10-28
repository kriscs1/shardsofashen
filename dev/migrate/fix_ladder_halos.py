"""The ladders' white fringes: Ladder001-003 were cut out of a white background, and kept a line of pale pixels
round their edges (a white border on the map). Ladder001 (Climb Up) becomes Ladder008's picture, the same ladder
drawn clean; on the ladder holes (002, 003) the pale greys touching the see-through part go, edge inwards, until
there are none left on the edge.

  python -I "dev\\migrate\fix_ladder_halos.py"
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

NAMES = ("Ladder002", "Ladder003")


def whitish(c):
    """Pale and grey (not the wood's browns): the old white background's fringe."""
    return c[3] > 0 and min(c[:3]) >= 130 and max(c[:3]) - min(c[:3]) <= 40


def clean(img):
    w, h = img.get_size()
    gone = 0
    while True:
        edge = []
        for y in range(h):
            for x in range(w):
                c = img.get_at((x, y))
                if not whitish(c):
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h) or img.get_at((nx, ny))[3] < 128:
                        edge.append((x, y))
                        break
        if not edge:
            return gone
        for x, y in edge:
            img.set_at((x, y), (0, 0, 0, 0))
        gone += len(edge)


def main():
    pygame.init()
    tiles = os.path.join(ROOT, "sprites", "Tiles")
    pygame.image.save(pygame.image.load(os.path.join(tiles, "Ladder008.png")), os.path.join(tiles, "Ladder001.png"))
    print("Ladder001: Ladder008's picture")
    for name in NAMES:
        path = os.path.join(ROOT, "sprites", "Tiles", name + ".png")
        img = pygame.image.load(path)
        n = clean(img)
        if n:
            pygame.image.save(img, path)
        print("%s: %d white edge pixels removed" % (name, n))


if __name__ == "__main__":
    main()
