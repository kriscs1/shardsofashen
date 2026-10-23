"""The wolves, drawn again: a lean grey wolf with a long snout, pricked ears and a bushy tail, trotting (three
frames), facing right (2) and left (8): Sprites\\Walk\\Wolf2a-c, Wolf8a-c, and Snow_Wolf the same in white.

  python -I "Dev\\migrate\\build_wolf.py"          (it overwrites them)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

WALK = os.path.join(ROOT, "Sprites", "Walk")
OUTLINE = (34, 30, 30)
PALETTES = {   # fur, its shadow, its light, the belly and muzzle, the eye
    "Wolf": ((118, 118, 124), (84, 84, 92), (156, 156, 162), (196, 192, 184), (236, 196, 60)),
    "Snow_Wolf": ((214, 222, 232), (168, 180, 196), (244, 248, 252), (250, 250, 250), (90, 170, 230)),
}
# legs: (x of the top, foot's x offset per frame a/b/c) - the near legs drawn darker last, the far ones first
LEGS = [(8, (0, 2, -2), True), (11, (0, -2, 2), False), (20, (0, -2, 2), True), (23, (0, 2, -2), False)]


def draw(fur, dark, light, belly, eye, frame):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, -1)[frame]                                     # (the body rises a little mid-stride)

    def leg(x, dx, far):
        col = dark if far else fur
        top, foot = 19 + bob, 27
        pygame.draw.line(s, col, (x, top), (x + dx // 2, top + 4), 2)
        pygame.draw.line(s, col, (x + dx // 2, top + 4), (x + dx, foot), 2)
        pygame.draw.line(s, OUTLINE, (x + dx - 1, foot + 1), (x + dx + 2, foot + 1))    # the paw
    for x, offs, far in LEGS:
        if far:
            leg(x, offs[frame], True)
    # the tail: bushy, held low behind
    pygame.draw.polygon(s, dark, [(7, 13 + bob), (3, 15 + bob), (0, 20 + bob), (2, 23 + bob), (5, 19 + bob),
                                  (8, 16 + bob)])
    pygame.draw.polygon(s, fur, [(7, 13 + bob), (4, 15 + bob), (2, 19 + bob), (4, 20 + bob), (7, 16 + bob)])
    pygame.draw.line(s, light, (1, 21 + bob), (2, 22 + bob))                 # its pale tip
    # the body: long and low, a deep chest tapering to the hips
    pygame.draw.ellipse(s, fur, (5, 12 + bob, 21, 9))
    pygame.draw.ellipse(s, fur, (17, 11 + bob, 9, 10))
    pygame.draw.polygon(s, belly, [(12, 20 + bob), (23, 20 + bob), (25, 17 + bob), (17, 19 + bob)])
    pygame.draw.line(s, dark, (8, 12 + bob), (20, 12 + bob))                  # the dark saddle along the back
    pygame.draw.line(s, dark, (6, 13 + bob), (17, 13 + bob))
    pygame.draw.line(s, light, (20, 12 + bob), (23, 12 + bob))               # light catching the shoulders
    # the neck and the head, held forward
    pygame.draw.polygon(s, fur, [(21, 12 + bob), (24, 9 + bob), (28, 11 + bob), (26, 17 + bob)])
    pygame.draw.ellipse(s, fur, (23, 8 + bob, 7, 6))
    pygame.draw.polygon(s, fur, [(28, 9 + bob), (31, 11 + bob), (31, 12 + bob), (27, 13 + bob)])      # the snout
    pygame.draw.polygon(s, belly, [(27, 12 + bob), (31, 12 + bob), (27, 14 + bob)])                  # the jaw
    pygame.draw.polygon(s, dark, [(23, 9 + bob), (24, 5 + bob), (26, 8 + bob)])                      # far ear
    pygame.draw.polygon(s, fur, [(24, 9 + bob), (26, 4 + bob), (28, 9 + bob)])                       # near ear
    pygame.draw.line(s, dark, (26, 6 + bob), (26, 8 + bob))
    s.set_at((31, 10 + bob), OUTLINE)                                                                 # the nose
    s.set_at((28, 10 + bob), eye)                                                                     # the eye
    s.set_at((27, 10 + bob), OUTLINE)
    for x, offs, far in LEGS:
        if not far:
            leg(x, offs[frame], False)
    # a dark outline all round (as the game's other sprites have)
    shape = pygame.mask.from_surface(s)
    edge = shape.outline()
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out if edge else s


def main():
    pygame.init()
    for name, pal in PALETTES.items():
        for i, f in enumerate("abc"):
            img = draw(*pal, frame=i)
            pygame.image.save(img, os.path.join(WALK, "%s2%s.png" % (name, f)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(WALK, "%s8%s.png" % (name, f)))
        print("Drew Sprites\\Walk\\%s2a-c and 8a-c" % name)


if __name__ == "__main__":
    main()
