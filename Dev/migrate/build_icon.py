"""The game's icon: the dragon and the Dragon Sword on a round shield, drawn from the game's own sprites.

  python -I "Dev\\migrate\\build_icon.py"

  * web/img/icon.png (256 x 256): the Docker container's icon (Unraid: the template's Icon), and for phones' home
    screens (apple-touch-icon).
  * web/img/favicon.png (64 x 64): the browser tab's icon.
The server serves them at /img/icon.png and /img/favicon.png. Run it again to redraw them (it overwrites them)."""
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

OUT = os.path.join(ROOT, "web", "img")
SIZE = 256


def sprite(folder, name):
    return pygame.image.load(os.path.join(ROOT, "Sprites", folder, name + ".png"))


def icon():
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    c = SIZE // 2
    for r in range(c - 4, 0, -1):                       # the shield: deep blue, lighter in the middle
        k = r / (c - 4)
        col = (int(44 - 30 * k), int(74 - 50 * k), int(118 - 70 * k))
        pygame.draw.circle(s, col, (c, c), r)
    pygame.draw.circle(s, (214, 170, 70), (c, c), c - 4, 8)          # the gold rim
    pygame.draw.circle(s, (120, 86, 30), (c, c), c - 4, 2)
    pygame.draw.circle(s, (120, 86, 30), (c, c), c - 12, 2)
    for i in range(12):                                             # rivets round the rim
        a = i * math.pi / 6
        pygame.draw.circle(s, (250, 220, 130), (int(c + (c - 8) * math.cos(a)), int(c + (c - 8) * math.sin(a))), 3)
    dragon = pygame.transform.scale(sprite("Entities", "Dragon"), (176, 176))     # (big square pixels, like the game)
    s.blit(dragon, (c - 88, c - 104))
    sword = pygame.transform.rotate(pygame.transform.scale(sprite("Entities", "Dragon_Sword"), (128, 128)), -10)
    x, y = c - sword.get_width() // 2, c - sword.get_height() // 2 + 20
    shape = pygame.mask.from_surface(sword)                         # (a gold edge, so it stands out on the dragon)
    outline = shape.to_surface(setcolor=(255, 214, 90, 255), unsetcolor=(0, 0, 0, 0))
    dark = shape.to_surface(setcolor=(30, 16, 8, 255), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-6, 0), (6, 0), (0, -6), (0, 6), (-5, -5), (5, 5), (-5, 5), (5, -5)):
        s.blit(dark, (x + dx, y + dy))
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
        s.blit(outline, (x + dx, y + dy))
    s.blit(sword, (x, y))
    mask = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)            # (round: nothing outside the rim)
    pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), c - 1)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


def main():
    pygame.init()
    img = icon()
    os.makedirs(OUT, exist_ok=True)
    pygame.image.save(img, os.path.join(OUT, "icon.png"))
    pygame.image.save(pygame.transform.smoothscale(img, (64, 64)), os.path.join(OUT, "favicon.png"))
    print("Made web/img/icon.png and web/img/favicon.png")


if __name__ == "__main__":
    main()
