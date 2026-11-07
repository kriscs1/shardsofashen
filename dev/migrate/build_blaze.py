"""The Blaze: a fire that isn't a campfire (the owner's wish, for Galaith still burning). No ring of stones, no neat logs: a
heap of charred wreckage and broken timbers with a ragged blaze standing out of it, five tongues of flame of every height
that lick and lean, a dark smoke going up from the tips in puffs, and embers thrown off. Eight frames that loop
(sprites\\Entities\\Blaze1-8; Blaze is the first). Entities.ini: Anim.Frames=8, Light.Flicker=1 (its light at night
flickers), Glow (a warm halo, day or night). Nothing cooks on it. Run it again to draw it again.

  python -I "dev\\migrate\\build_blaze.py"      (then export_web_assets.py)
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from ashen import ini  # noqa: E402

FRAMES = 8
OUTLINE = (26, 18, 14)
CHAR, CHAR_LT, CHAR_DK = (46, 34, 28), (74, 56, 44), (28, 20, 16)
GLOW = (214, 78, 24)
FLAME = [((178, 34, 18), 1.0), ((236, 92, 24), 0.78), ((252, 164, 44), 0.54), ((255, 232, 150), 0.28)]   # outer to core
# (x of its foot, how big, its own place in the loop, how far it leans)
TONGUES = [(7, 0.55, 0.3, 1.0), (12, 0.85, 2.4, 1.6), (16, 1.0, 4.7, 2.2), (21, 0.8, 1.5, 1.8), (25, 0.5, 5.6, 1.2)]
BASE = 25


def tongue(s, cx, base, width, height, lean, flick, col):
    """One tongue of flame: wide at the foot, a tip that leans and flickers, its edge ragged."""
    left, right = [], []
    steps = 10
    for k in range(steps + 1):
        t = k / steps
        y = base - t * height
        half = width / 2 * (1 - t) ** 0.75 * (0.8 + 0.2 * math.sin(math.pi * min(1, t * 1.5)))
        half += 0.7 * math.sin(t * 9 + flick) * (1 - t)               # (the ragged edge)
        x = cx + lean * t * t + 0.6 * math.sin(t * 6 + flick * 1.3)
        left.append((x - half, y))
        right.append((x + half, y))
    pygame.draw.polygon(s, col, left + right[::-1])


def wreckage(s, rng):
    """The heap the fire stands in: charred ground, burnt timbers sticking out, embers glowing in the gaps."""
    pygame.draw.ellipse(s, OUTLINE, (2, 21, 28, 11))
    pygame.draw.ellipse(s, CHAR_DK, (3, 22, 26, 9))
    pygame.draw.ellipse(s, (96, 30, 12), (8, 23, 16, 5))                  # (the red glow under it all)
    for a, b, w in (((4, 28), (17, 22), 3), ((28, 28), (15, 21), 3), ((10, 30), (27, 25), 2), ((6, 24), (13, 29), 2)):
        pygame.draw.line(s, OUTLINE, (a[0], a[1] + 1), (b[0], b[1] + 1), w + 2)
        pygame.draw.line(s, CHAR, a, b, w)
        pygame.draw.line(s, CHAR_LT, (a[0], a[1] - 1), (b[0], b[1] - 1), 1)
    for _ in range(9):                                                       # (coals: a pixel or two, here and there)
        x, y = rng.randint(6, 25), rng.randint(24, 29)
        s.set_at((x, y), rng.choice([(222, 96, 28), (250, 150, 40), (170, 48, 18)]))


def draw(frame):
    phase = 2 * math.pi * frame / FRAMES
    rng = random.Random(11)                                                  # (the same heap in every frame)
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    wreckage(s, rng)
    # a low glow lying on the ground round the foot of it
    glow = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, GLOW + (60,), (2, 20, 28, 10))
    s.blit(glow, (0, 0))
    for cx, k, off, lean in TONGUES:
        h = (17 + 5 * math.sin(phase + off) + 2 * math.sin(2 * phase + off * 1.7)) * k
        sway = lean * math.sin(phase + off * 1.3)
        for col, w in FLAME:
            tongue(s, cx, BASE, 11 * w * k + 2, h * (0.55 + 0.45 * w), sway * (1.15 - 0.4 * w), phase + off, col)
    # smoke: dark puffs rising off the tips, thinning and drifting east as they go
    smoke = pygame.Surface((32, 32), pygame.SRCALPHA)
    for i in range(3):
        t = (frame / FRAMES + i / 3) % 1
        x = 13 + 5 * i - 4 + 6 * t
        y = 9 - 11 * t
        r = 2 + 3 * t
        a = int(150 * (1 - t) ** 1.3) if t > 0.05 else 0
        pygame.draw.circle(smoke, (44, 40, 38, a), (round(x), round(y)), round(r))
        pygame.draw.circle(smoke, (74, 68, 64, a // 2), (round(x - 1), round(y - 1)), max(1, round(r - 1.5)))
    s.blit(smoke, (0, 0))
    # embers thrown off, rising and drifting
    for i in range(4):
        t = (frame / FRAMES + i / 4) % 1
        x = 9 + 4.5 * i + 3 * math.sin(i * 2.1 + t * 6)
        y = 17 - t * 15
        if 0 <= y < 32 and t < 0.9:
            s.set_at((int(x), int(y)), (255, 226, 120) if t < 0.5 else (240, 120, 40))
    return s


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    ents = os.path.join(ROOT, "sprites", "Entities")
    frames = [draw(i) for i in range(FRAMES)]
    for i, img in enumerate(frames, 1):
        pygame.image.save(img, os.path.join(ents, "Blaze%d.png" % i))
    pygame.image.save(frames[0], os.path.join(ents, "Blaze.png"))
    path = os.path.join(ROOT, "data", "Entities.ini")
    for k, v in (("Type", "StaticObject"), ("Examine.Info", "Wreckage burning. The heat is fierce."), ("Light", "110"),
                 ("Anim.Frames", str(FRAMES)), ("Anim.Speed", "95"), ("Light.Flicker", "1"), ("Glow", "42")):
        ini.write("Blaze", k, v, path)
    print("Drew the blaze: %d frames" % FRAMES)


if __name__ == "__main__":
    main()
