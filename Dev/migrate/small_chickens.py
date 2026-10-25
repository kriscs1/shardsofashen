"""Hens, smaller: their pictures (Sprites\\Walk\\Chicken2a-8c, Sprites\\Entities\\Chicken) shrunk to SCALE, their
feet kept where they were (on the ground, in the middle). The originals are kept in Dev\\Archive\\Sprites\\Chicken and
shrunk from there, so running it again gives the same (not smaller still).

  python -I "Dev\\migrate\\small_chickens.py"
"""
import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

SCALE = 0.7
ARCHIVE = os.path.join(ROOT, "Dev", "Archive", "Sprites", "Chicken")


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    os.makedirs(ARCHIVE, exist_ok=True)
    files = glob.glob(os.path.join(ROOT, "Sprites", "Walk", "Chicken[0-9]*.png")) + \
        [os.path.join(ROOT, "Sprites", "Entities", "Chicken.png")]
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
        small = pygame.transform.scale(part, (w, h))                        # (crisp: pixel art, not blurred)
        out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        out.blit(small, (round(box.centerx - w / 2), box.bottom - h))      # (its feet where they were)
        pygame.image.save(out, path)
    print("Hens at %d%% of their size (%d pictures)" % (SCALE * 100, len(files)))


if __name__ == "__main__":
    main()
