"""Sheep a little smaller (the owner's wish): every sheep picture scaled on its own canvas, on the same ground line and in
the same middle. Safe to run again: a sheep already at its height is left alone."""
import glob
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HEIGHT = 18         # (the tallest a sheep stands, in pixels: a person is about 30)


def shrink(path, scale):
    im = pygame.image.load(path).convert_alpha()
    box = im.get_bounding_rect()
    w, h = max(1, round(box.w * scale)), max(1, round(box.h * scale))
    small = pygame.transform.scale(im.subsurface(box), (w, h))
    out = pygame.Surface(im.get_size(), pygame.SRCALPHA)
    out.blit(small, (box.centerx - w // 2, box.bottom - h))
    pygame.image.save(out, path)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    paths = []
    for folder in ("sprites/Walk", "sprites/Entities", "sprites/Poses"):
        paths += [p for p in glob.glob(os.path.join(ROOT, folder, "Sheep*.png")) if os.path.basename(p)[5:6] in ("", ".", "2", "8", "_")]
    tallest = max(pygame.image.load(p).get_bounding_rect().h for p in paths)
    if tallest <= HEIGHT:
        print("Sheep: already %d high" % tallest)
        return
    scale = HEIGHT / tallest                    # (the one scale for every pose: they stay one size, on one line)
    for p in paths:
        shrink(p, scale)
    print("Sheep: %d pictures, %d high to %d" % (len(paths), tallest, HEIGHT))


if __name__ == "__main__":
    main()
