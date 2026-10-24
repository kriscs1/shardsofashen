"""Butterflies, smaller: their pictures (Sprites\\Walk\\Butterfly2a-8c, Sprites\\Entities\\Butterfly) shrunk to SCALE,
kept centred where they were. The originals are kept in Dev\\Archive\\Sprites and shrunk from there, so running it
again gives the same (not smaller still).

  python -I "Dev\\migrate\\small_butterflies.py"
"""
import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

SCALE = 0.55
ARCHIVE = os.path.join(ROOT, "Dev", "Archive", "Sprites", "Butterfly")


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    os.makedirs(ARCHIVE, exist_ok=True)
    files = glob.glob(os.path.join(ROOT, "Sprites", "Walk", "Butterfly*.png")) + \
        [os.path.join(ROOT, "Sprites", "Entities", "Butterfly.png")]
    for path in files:
        keep = os.path.join(ARCHIVE, os.path.basename(os.path.dirname(path)) + "_" + os.path.basename(path))
        if not os.path.exists(keep):
            shutil.copy(path, keep)
        img = pygame.image.load(keep).convert_alpha()
        box = img.get_bounding_rect()
        if not box.w:
            continue
        part = img.subsurface(box).copy()
        w, h = max(1, round(box.w * SCALE)), max(1, round(box.h * SCALE))
        small = pygame.transform.scale(part, (w, h))
        out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        out.blit(small, (round(box.centerx - w / 2), round(box.centery - h / 2)))
        pygame.image.save(out, path)
    print("Butterflies at %d%% of their size (%d pictures)" % (SCALE * 100, len(files)))


if __name__ == "__main__":
    main()
