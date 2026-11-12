"""The wolves, drawn again: a lean grey wolf with a long snout, pricked ears and a bushy tail, trotting (three
frames), facing right (2) and left (8): sprites\\Walk\\Wolf2a-c, Wolf8a-c, and Snow_Wolf (white) and Alpha_Wolf (black,
red-eyed) the same. The dog beside them. They come at you, so they face towards you (4) and away (1) as well; the bear
too (its side-on frames are build_walk.py's, from its picture). Then the wolves' kin are made again from these, by
their own builders' recolourings: the Ember Hound (cinder_art.py), the Ash Hound (build_zones.py) and Old Whitefang
(build_middle_quests.py).

  python -I "dev\\migrate\\build_wolf.py"          (it overwrites them)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WALK = os.path.join(ROOT, "sprites", "Walk")
OUTLINE = (34, 30, 30)
PALETTES = {   # fur, its shadow, its light, the belly and muzzle, the eye
    "Wolf": ((118, 118, 124), (84, 84, 92), (156, 156, 162), (196, 192, 184), (236, 196, 60)),
    "Snow_Wolf": ((214, 222, 232), (168, 180, 196), (244, 248, 252), (250, 250, 250), (90, 170, 230)),
    "Alpha_Wolf": ((46, 40, 42), (22, 18, 18), (84, 74, 76), (70, 62, 64), (230, 60, 40)),
}
BEAR = ((112, 72, 39), (83, 52, 27), (150, 109, 71), (142, 101, 63), (60, 36, 19), (47, 28, 15))   # (as its picture)
LIFT = ((0, 0), (2, 0), (0, 2))   # (each frame: how far the left and the right foot are off the ground, seen end-on)
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
    return outlined(s)


def outlined(s, col=OUTLINE):
    """A dark outline all round (as the game's other sprites have)."""
    shape = pygame.mask.from_surface(s)
    if not shape.outline():
        return s
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def legs_end_on(s, xs, top, foot, frame, col, width=2, paw=OUTLINE, swap=False):
    """Two legs seen from in front or behind, each foot lifted in turn (swap: the other way about, for the far pair)."""
    for i, x in enumerate(xs):
        up = LIFT[frame][1 - i if swap else i]
        pygame.draw.rect(s, col, (x, top, width, foot - up - top + 1))
        pygame.draw.line(s, paw, (x - 1, foot - up + 1), (x + width, foot - up + 1))


def wolf_end_on(fur, dark, light, belly, eye, frame, back):
    """The wolf coming towards you (back False) or going away: the long snout and the pricked ears; the tail held
    low (hidden from the front, hanging down its middle from behind)."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    b = (0, -1, -1)[frame]
    ears = lambda y: [[(11, y + 3), (11, y - 3), (15, y + 1)], [(20, y + 3), (20, y - 3), (16, y + 1)]]   # noqa: E731
    if not back:
        legs_end_on(s, (11, 19), 19 + b, 25, frame, dark, swap=True)             # (the hind legs, beyond)
        pygame.draw.ellipse(s, fur, (10, 10 + b, 12, 11))
        pygame.draw.line(s, dark, (12, 10 + b), (19, 10 + b))                    # (the saddle, over its shoulders)
        legs_end_on(s, (13, 17), 19 + b, 27, frame, fur)
        pygame.draw.polygon(s, belly, [(13, 15 + b), (18, 15 + b), (16, 21 + b), (15, 21 + b)])    # (the chest)
        for ear in ears(4 + b):
            pygame.draw.polygon(s, fur, ear)
        pygame.draw.ellipse(s, fur, (11, 4 + b, 10, 9))
        for x in (12, 19):
            pygame.draw.line(s, dark, (x, 3 + b), (x, 5 + b))                    # (inside the ears)
        pygame.draw.line(s, light, (15, 5 + b), (16, 5 + b))
        pygame.draw.ellipse(s, belly, (13, 8 + b, 6, 5))                         # (the muzzle, pointing at you)
        for x, o in ((13, 12), (18, 19)):
            s.set_at((x, 7 + b), eye)
            s.set_at((o, 7 + b), OUTLINE)
        s.set_at((15, 9 + b), OUTLINE)                                            # (the nose)
        s.set_at((16, 9 + b), OUTLINE)
        pygame.draw.line(s, dark, (15, 11 + b), (16, 11 + b))
    else:
        legs_end_on(s, (12, 18), 19 + b, 25, frame, dark, swap=True)             # (the forelegs, beyond)
        for ear in ears(3 + b):
            pygame.draw.polygon(s, fur, ear)
        pygame.draw.ellipse(s, fur, (11, 3 + b, 10, 8))
        for x in (12, 19):
            pygame.draw.line(s, dark, (x, 1 + b), (x, 4 + b))                    # (the backs of the ears)
        pygame.draw.ellipse(s, fur, (9, 9 + b, 14, 13))
        pygame.draw.rect(s, dark, (15, 9 + b, 2, 8))                              # (the saddle, down its back)
        pygame.draw.line(s, light, (12, 11 + b), (13, 10 + b))
        pygame.draw.ellipse(s, fur, (9, 14 + b, 7, 8))                            # (the haunches)
        pygame.draw.ellipse(s, fur, (16, 14 + b, 7, 8))
        legs_end_on(s, (11, 19), 20 + b, 27, frame, fur)
        pygame.draw.polygon(s, dark, [(14, 15 + b), (17, 15 + b), (18, 22 + b), (16, 25 + b), (14, 22 + b)])
        pygame.draw.polygon(s, fur, [(15, 15 + b), (16, 15 + b), (17, 21 + b), (16, 23 + b), (15, 21 + b)])
        s.set_at((16, 24 + b), light)                                             # (its pale tip)
    return outlined(s)


def dog_end_on(fur, dark, light, chest, eye, frame, back):
    """The dog towards you or away: a round head, ears hanging, the tail up and curling (seen from behind)."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    b = (0, -1, -1)[frame]
    if not back:
        legs_end_on(s, (12, 18), 21 + b, 25, frame, dark, swap=True)
        pygame.draw.ellipse(s, fur, (11, 13 + b, 10, 9))
        legs_end_on(s, (13, 17), 20 + b, 27, frame, fur)
        pygame.draw.polygon(s, chest, [(13, 16 + b), (18, 16 + b), (16, 21 + b), (15, 21 + b)])
        pygame.draw.ellipse(s, fur, (12, 7 + b, 8, 8))
        pygame.draw.polygon(s, dark, [(11, 8 + b), (13, 8 + b), (13, 14 + b), (11, 13 + b)])        # (the ears)
        pygame.draw.polygon(s, dark, [(20, 8 + b), (18, 8 + b), (18, 14 + b), (20, 13 + b)])
        pygame.draw.ellipse(s, chest, (14, 11 + b, 4, 4))
        s.set_at((14, 10 + b), eye)
        s.set_at((17, 10 + b), eye)
        s.set_at((15, 12 + b), OUTLINE)
        s.set_at((16, 12 + b), OUTLINE)
        s.set_at((16, 15 + b), (220, 110, 120))                                   # (the tongue)
    else:
        legs_end_on(s, (13, 17), 21 + b, 25, frame, dark, swap=True)
        pygame.draw.ellipse(s, fur, (12, 6 + b, 8, 7))
        pygame.draw.polygon(s, dark, [(11, 7 + b), (13, 7 + b), (13, 13 + b), (11, 12 + b)])
        pygame.draw.polygon(s, dark, [(20, 7 + b), (18, 7 + b), (18, 13 + b), (20, 12 + b)])
        pygame.draw.ellipse(s, fur, (10, 11 + b, 12, 11))
        pygame.draw.line(s, dark, (15, 12 + b), (16, 12 + b))
        pygame.draw.line(s, light, (12, 13 + b), (13, 12 + b))
        legs_end_on(s, (12, 18), 20 + b, 27, frame, fur)
        pygame.draw.line(s, fur, (16, 16 + b), (17, 12 + b), 2)                   # (the tail, curling up)
        pygame.draw.line(s, light, (17, 12 + b), (16, 11 + b))
    return outlined(s)


def bear_end_on(fur, dark, light, muzzle, paw, line, frame, back):
    """The bear towards you or away: broad and round-eared, its legs thick (no taller than it is side-on)."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    b = 4 + (0, -1, -1)[frame]
    if not back:
        legs_end_on(s, (8, 21), 16 + b, 25, frame, dark, width=3, paw=paw, swap=True)
        pygame.draw.ellipse(s, fur, (7, 10 + b, 18, 11))
        pygame.draw.line(s, light, (11, 11 + b), (20, 11 + b))                    # (light on the hump)
        legs_end_on(s, (10, 18), 16 + b, 27, frame, fur, width=4, paw=paw)
        for x in (12, 20):
            pygame.draw.circle(s, fur, (x, 5 + b), 2)                             # (the round ears)
            s.set_at((x, 5 + b), dark)
        pygame.draw.ellipse(s, fur, (10, 4 + b, 12, 9))
        pygame.draw.line(s, light, (14, 5 + b), (17, 5 + b))
        pygame.draw.ellipse(s, muzzle, (13, 8 + b, 6, 4))
        s.set_at((13, 7 + b), line)                                               # (small dark eyes)
        s.set_at((18, 7 + b), line)
        s.set_at((15, 9 + b), line)                                               # (the nose)
        s.set_at((16, 9 + b), line)
    else:
        legs_end_on(s, (11, 18), 16 + b, 25, frame, dark, width=3, paw=paw, swap=True)
        for x in (12, 20):
            pygame.draw.circle(s, fur, (x, 3 + b), 2)
        pygame.draw.ellipse(s, fur, (11, 2 + b, 10, 8))
        pygame.draw.ellipse(s, fur, (6, 7 + b, 20, 13))
        pygame.draw.line(s, light, (11, 8 + b), (20, 8 + b))
        pygame.draw.line(s, dark, (16, 10 + b), (16, 15 + b))                     # (the line of its back)
        legs_end_on(s, (9, 19), 17 + b, 27, frame, fur, width=4, paw=paw)
        pygame.draw.circle(s, light, (16, 16 + b), 1)                             # (the stub of a tail)
    return outlined(s, line)


def save4(name, frame, img):
    """A frame's two new facings, towards you (4) and away (1)."""
    pygame.image.save(img[0], os.path.join(WALK, "%s4%s.png" % (name, "abc"[frame])))
    pygame.image.save(img[1], os.path.join(WALK, "%s1%s.png" % (name, "abc"[frame])))


def kin():
    """The wolves' kin, recoloured from the frames just drawn, so every facing reaches them."""
    import cinder_art
    import build_zones
    import build_middle_quests
    fn = next(f for src, dst, f, _ in cinder_art.ENTITY_ART if dst == "Ember_Hound")
    for d in "1248":
        for f in "abc":
            cinder_art.recolour_file(os.path.join(WALK, "Wolf%s%s.png" % (d, f)),
                                     os.path.join(WALK, "Ember_Hound%s%s.png" % (d, f)), fn)
    build_zones.mob_pictures("Ash_Hound", *build_zones.MOBS["Ash_Hound"][:2])
    base, col, scale = build_middle_quests.BOSSES["Old_Whitefang"][:3]
    build_middle_quests.kind_from("Old_Whitefang", base, col, scale)
    print("Made the Ember Hound, the Ash Hound and Old Whitefang again from them")


DOG = ((150, 96, 52), (108, 66, 34), (186, 132, 82), (236, 214, 176), (40, 26, 18))     # fur, shadow, light, chest, eye
DOG_LEGS = [(11, (0, 2, -2), True), (13, (0, -2, 2), False), (19, (0, -2, 2), True), (21, (0, 2, -2), False)]


def draw_dog(fur, dark, light, chest, eye, frame):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, -1)[frame]

    def leg(x, dx, far):
        top, foot = 21 + bob, 27
        pygame.draw.line(s, dark if far else fur, (x, top), (x + dx // 2, top + 3), 2)
        pygame.draw.line(s, dark if far else fur, (x + dx // 2, top + 3), (x + dx, foot), 2)
        pygame.draw.line(s, OUTLINE, (x + dx - 1, foot + 1), (x + dx + 1, foot + 1))
    for x, offs, far in DOG_LEGS:
        if far:
            leg(x, offs[frame], True)
    # the tail, up and curling
    pygame.draw.line(s, fur, (10, 17 + bob), (7, 13 + bob), 2)
    pygame.draw.line(s, fur, (7, 13 + bob), (8, 10 + bob), 2)
    pygame.draw.line(s, light, (8, 10 + bob), (9, 9 + bob))
    # the body: short and sturdy, a pale chest
    pygame.draw.ellipse(s, fur, (9, 15 + bob, 15, 8))
    pygame.draw.polygon(s, chest, [(18, 21 + bob), (23, 20 + bob), (24, 17 + bob), (20, 19 + bob)])
    pygame.draw.line(s, dark, (11, 15 + bob), (19, 15 + bob))
    pygame.draw.line(s, light, (12, 16 + bob), (18, 16 + bob))
    # the head: round, a short muzzle, a floppy ear
    pygame.draw.polygon(s, fur, [(20, 16 + bob), (22, 12 + bob), (25, 13 + bob), (24, 18 + bob)])
    pygame.draw.ellipse(s, fur, (21, 9 + bob, 7, 7))
    pygame.draw.polygon(s, chest, [(26, 12 + bob), (30, 13 + bob), (30, 15 + bob), (26, 15 + bob)])   # the muzzle
    pygame.draw.polygon(s, dark, [(22, 10 + bob), (25, 9 + bob), (24, 15 + bob), (22, 14 + bob)])   # the ear, hanging
    s.set_at((30, 13 + bob), OUTLINE)                                                                 # the nose
    s.set_at((26, 11 + bob), eye)                                                                     # the eye
    s.set_at((28, 16 + bob), (220, 110, 120))                                                         # the tongue
    for x, offs, far in DOG_LEGS:
        if not far:
            leg(x, offs[frame], False)
    shape = pygame.mask.from_surface(s)
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def main():
    pygame.init()
    for name, pal in PALETTES.items():
        for i, f in enumerate("abc"):
            img = draw(*pal, frame=i)
            pygame.image.save(img, os.path.join(WALK, "%s2%s.png" % (name, f)))
            pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(WALK, "%s8%s.png" % (name, f)))
            save4(name, i, [wolf_end_on(*pal, frame=i, back=bk) for bk in (False, True)])
        print("Drew sprites\\Walk\\%s1a-c, 2a-c, 4a-c and 8a-c" % name)
    for i, f in enumerate("abc"):
        img = draw_dog(*DOG, frame=i)
        pygame.image.save(img, os.path.join(WALK, "Dog2%s.png" % f))
        pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(WALK, "Dog8%s.png" % f))
        save4("Dog", i, [dog_end_on(*DOG, frame=i, back=bk) for bk in (False, True)])
        save4("Bear", i, [bear_end_on(*BEAR, frame=i, back=bk) for bk in (False, True)])
    print("Drew sprites\\Walk\\Dog1a-c, 2a-c, 4a-c and 8a-c, and Bear1a-c and 4a-c")
    kin()


if __name__ == "__main__":
    main()
