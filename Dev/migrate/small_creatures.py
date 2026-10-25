"""Small creatures, smaller: their pictures (Sprites\\Walk\\<Kind>2a-8c, Sprites\\Entities\\<Kind>) shrunk to their
SCALES, their feet kept where they were (on the ground, in the middle), crisp (pixel art, not blurred). The originals
are kept in Dev\\Archive\\Sprites\\<Kind> and shrunk from there, so running it again gives the same (not smaller still).

  python -I "Dev\\migrate\\small_creatures.py"
"""
import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

SCALES = {"Chicken": 0.7, "Rabbit": 0.6}


def shrink(kind, scale):
    archive = os.path.join(ROOT, "Dev", "Archive", "Sprites", kind)
    os.makedirs(archive, exist_ok=True)
    files = glob.glob(os.path.join(ROOT, "Sprites", "Walk", kind + "[0-9]*.png")) + \
        [os.path.join(ROOT, "Sprites", "Entities", kind + ".png")]
    for path in files:
        keep = os.path.join(archive, os.path.basename(os.path.dirname(path)) + "_" + os.path.basename(path))
        if not os.path.exists(keep):
            shutil.copy(path, keep)
        img = pygame.image.load(keep).convert_alpha()
        box = img.get_bounding_rect()
        if not box.w:
            continue
        part = img.subsurface(box).copy()
        w, h = max(1, round(box.w * scale)), max(1, round(box.h * scale))
        small = pygame.transform.scale(part, (w, h))                        # (crisp: pixel art, not blurred)
        out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        out.blit(small, (round(box.centerx - w / 2), box.bottom - h))      # (its feet where they were)
        pygame.image.save(out, path)
    return len(files)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    for kind, scale in SCALES.items():
        print("%s at %d%% of its size (%d pictures)" % (kind, scale * 100, shrink(kind, scale)))


if __name__ == "__main__":
    main()
