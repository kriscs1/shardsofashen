"""The fire, drawn and alive: a campfire - a ring of stones, two crossed logs, flames that leap and sway and throw off
sparks - in six frames (Sprites\\Entities\\Fire1-6; Fire is the first). Entities.ini: Anim.Frames=6 (it burns where it
stands), Light.Flicker=1 (its light at night flickers), Glow (a warm halo round it, day or night). Run it again to
draw it again.

  python -I "Dev\\migrate\\build_fire.py"
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from dragonsword import ini  # noqa: E402

FRAMES = 6
OUTLINE = (30, 20, 16)
STONE, STONE_LT, STONE_DK = (128, 124, 120), (170, 166, 160), (84, 80, 78)
LOG, LOG_LT, LOG_DK = (112, 72, 40), (150, 102, 58), (70, 42, 22)
FLAME = [((196, 44, 22), 13), ((244, 112, 28), 10), ((255, 196, 60), 6.5), ((255, 244, 186), 3)]   # outer to core


def flame(s, cx, base, width, height, sway, col):
    """A tongue of flame: wide where it leaves the logs, narrowing to a tip that leans with the sway."""
    left, right = [], []
    steps = 12
    for k in range(steps + 1):
        t = k / steps
        y = base - t * height
        half = width / 2 * (1 - t) ** 0.8 * (0.75 + 0.25 * math.sin(math.pi * min(1, t * 1.6)))
        x = cx + sway * t * t
        left.append((x - half, y))
        right.append((x + half, y))
    pygame.draw.polygon(s, col, left + right[::-1])


def draw(frame):
    rng = random.Random(frame * 7 + 3)
    phase = 2 * math.pi * frame / FRAMES
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    # the logs, crossed, and the embers glowing under them
    pygame.draw.ellipse(s, (120, 40, 16), (8, 21, 16, 7))
    pygame.draw.ellipse(s, (220, 96, 30), (11, 22, 10, 4))
    for a, b in (((7, 27), (25, 21)), ((7, 21), (25, 27))):
        pygame.draw.line(s, LOG_DK, a, b, 4)
        pygame.draw.line(s, LOG, (a[0], a[1] - 1), (b[0], b[1] - 1), 2)
        pygame.draw.circle(s, LOG_LT, a, 1)
    # the flames: a big one in the middle, two smaller beside it, each leaping in its own time
    tongues = [(16, 1.0, 0.0), (12, 0.62, 2.1), (20, 0.66, 4.2)]
    for cx, k, off in tongues:
        h = (14 + 3 * math.sin(phase + off) + rng.uniform(-1, 1)) * k
        sway = 2.2 * math.sin(phase * 1 + off * 1.3)
        for col, wid in FLAME:
            if wid * k < 1.5:
                continue
            flame(s, cx, 24, wid * k, h * (1 - (13 - wid) * 0.035), sway, col)
    # sparks, rising and drifting
    for i in range(3):
        t = ((frame / FRAMES) + i / 3) % 1
        x = 16 + 5 * math.sin(i * 2.3 + t * 5) + (i - 1) * 2
        y = 18 - t * 16
        if t < 0.85:
            s.set_at((int(x), int(y)), (255, 226, 120) if t < 0.5 else (240, 140, 50))
    # the ring of stones, in front of the logs at the bottom, behind them at the top
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    ring = [(16 + 11 * math.cos(a), 25 + 4.2 * math.sin(a)) for a in (2 * math.pi * j / 9 + 0.3 for j in range(9))]
    for x, y in ring:
        if y < 25:
            stone(out, x, y)
    out.blit(s, (0, 0))
    for x, y in ring:
        if y >= 25:
            stone(out, x, y)
    return out


def stone(s, x, y):
    r = pygame.Rect(0, 0, 6, 4)
    r.center = (round(x), round(y))
    pygame.draw.ellipse(s, OUTLINE, r.inflate(2, 2))
    pygame.draw.ellipse(s, STONE, r)
    s.set_at((r.x + 2, r.y + 1), STONE_LT)
    s.set_at((r.x + 3, r.bottom - 1), STONE_DK)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    ents = os.path.join(ROOT, "Sprites", "Entities")
    frames = [draw(i) for i in range(FRAMES)]
    for i, img in enumerate(frames, 1):
        pygame.image.save(img, os.path.join(ents, "Fire%d.png" % i))
    pygame.image.save(frames[0], os.path.join(ents, "Fire.png"))
    path = os.path.join(ROOT, "Data", "Entities.ini")
    for k, v in (("Anim.Frames", str(FRAMES)), ("Anim.Speed", "110"), ("Light.Flicker", "1"), ("Glow", "30")):
        ini.write("Fire", k, v, path)
    print("Drew the fire: %d frames" % FRAMES)


if __name__ == "__main__":
    main()
