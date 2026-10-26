"""The new mainland's own tiles (dev\\World Plan.md), drawn in code (sprites\\Tiles), with their Tiles.ini sections and
minimap colours:

  * Mountains you can't cross, pointy: Peak001-006 and the 2 x 2 Peak_Big001-004 (the grey West Range), the same
    snow-capped and white (Snow_Peak..., the Frostpeak range) and black with lava in the cracks (Cinder_Peak...).
  * The dragon's work at Galaith: Scorched001-003 (black earth, ash and embers), and Galaith's white walls and gates
    burnt black on the side that faces the dragon (Burnt_Wall001-005, Burnt_Gate001-006: Galaith_Wall/Gate, sooted).
  * Streets of local stuff: Brick_Paving001 (red brick), Cobble001 (grey cobbles), Marble_Paving001 (white flags),
    Mage_Flag001 (blue-grey flags), Slate_Flag001 (dark slate), Red_Sandstone001, Flagstone001 (grey flags),
    Gravel001, Basalt_Paving001 (black basalt), Sandstone_Paving001, Boardwalk001 (planks over the marsh).
  * Signpost (where the roads meet: which way places lie) and Moored_Boat (the ports' boats: the ferry's boat's
    frames), in sprites\Entities, with their Entities.ini sections.

Run it again to draw the same again.

  python -I "dev\\migrate\\build_world_art.py"
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import story_kit as K  # noqa: E402

TILES_DIR = os.path.join(ROOT, "sprites", "Tiles")
S = 32
SOLID = "0" * 49
OPEN = "1" * 49


def surface():
    return pygame.Surface((S, S), pygame.SRCALPHA)


def save(name, s):
    pygame.image.save(s, os.path.join(TILES_DIR, name + ".png"))


def average(s):
    r = g = b = n = 0
    for y in range(S):
        for x in range(S):
            c = s.get_at((x, y))
            if c.a > 128:
                r, g, b, n = r + c.r, g + c.g, b + c.b, n + 1
    return (r // max(1, n), g // max(1, n), b // max(1, n))


def tile_data(name, walk, los, blend=None, examine="", speed=None):
    keys = [("Walkable.Data", walk), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", examine),
            ("Line.of.Sight", los)]
    if blend is not None:
        keys.append(("Blend", str(blend)))
    if speed is not None:
        keys.append(("Walk.Speed", speed))
    K.section(K.TILES, name, keys)


def noise(rng, s, colours, n):
    for _ in range(n):
        s.set_at((rng.randrange(S), rng.randrange(S)), rng.choice(colours))


# ================================================================== mountains
KINDS = {   # prefix: (ground, ground speckles, lit face, shadow face, outline, cap, crack)
    "": ((96, 90, 84), [(84, 78, 72), (108, 102, 96)], (178, 172, 162), (112, 106, 100), (44, 40, 38),
         (238, 242, 248), None),
    "Snow_": ((214, 222, 232), [(196, 206, 220), (232, 238, 246)], (244, 248, 252), (168, 184, 204), (70, 80, 96),
              (255, 255, 255), None),
    "Cinder_": ((46, 40, 40), [(36, 30, 30), (60, 52, 50)], (92, 82, 80), (46, 40, 40), (16, 12, 12), None,
                (232, 108, 40)),
}


def peak(s, apex, left, right, base_y, kind, rng, cap=True):
    """One pointy peak: a lit face west of the ridge line, a shaded face east of it, an outline, a snow cap."""
    ground, specks, lit, shade, edge, cap_col, crack = KINDS[kind]
    ax, ay = apex
    pygame.draw.polygon(s, lit, [(left, base_y), (ax, ay), (ax, base_y)])
    pygame.draw.polygon(s, shade, [(ax, ay), (right, base_y), (ax, base_y)])
    for k in range(3):                                            # (strata on the faces)
        y = ay + (base_y - ay) * (0.35 + 0.2 * k)
        w = (y - ay) / max(1, base_y - ay)
        pygame.draw.line(s, tuple(max(0, c - 18) for c in lit), (ax - w * (ax - left) * 0.8, y), (ax - 2, y + 2))
        pygame.draw.line(s, tuple(max(0, c - 18) for c in shade), (ax + 2, y + 1), (ax + w * (right - ax) * 0.7, y))
    if cap and cap_col:
        h = (base_y - ay) * 0.28
        pygame.draw.polygon(s, cap_col, [(ax - h * (ax - left) / (base_y - ay) * 1.0, ay + h), (ax, ay),
                                         (ax + h * (right - ax) / (base_y - ay), ay + h), (ax + 1, ay + h - 2),
                                         (ax - 2, ay + h + 1)])
    if crack:
        x, y = ax, ay + 4
        for _ in range(int((base_y - ay) / 3)):
            x += rng.choice((-1, 0, 1))
            y += 2
            s.set_at((int(x), int(y)), crack)
    pygame.draw.lines(s, edge, False, [(left, base_y), (ax, ay), (right, base_y)], 1)


def mountain_tile(kind, v):
    rng = random.Random("%s%d" % (kind, v))
    ground, specks = KINDS[kind][0], KINDS[kind][1]
    s = surface()
    s.fill(ground)
    noise(rng, s, specks, 90)
    shapes = {
        1: [((16, 1), 0, 31, 31)],
        2: [((10, 6), 0, 20, 31), ((23, 3), 12, 32, 31)],
        3: [((11, 2), 0, 25, 31), ((26, 14), 18, 32, 31)],
        4: [((21, 2), 6, 32, 31), ((6, 13), 0, 14, 31)],
        5: [((8, 12), 0, 16, 31), ((17, 9), 8, 26, 31), ((26, 14), 19, 32, 31)],
        6: [((16, 4), 2, 30, 31), ((5, 18), 0, 11, 31), ((28, 19), 22, 32, 31)],
    }[v]
    for apex, left, right, base in shapes:
        peak(s, apex, left, right, base, kind, rng, cap=v != 5)
    return s


def big_mountain(kind):
    """A 2 x 2 peak (64 x 64), cut into four tiles."""
    rng = random.Random(kind + "big")
    ground, specks = KINDS[kind][0], KINDS[kind][1]
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    s.fill(ground)
    for _ in range(300):
        s.set_at((rng.randrange(64), rng.randrange(64)), rng.choice(specks))
    old = globals()["S"]
    peak(s, (30, 1), 0, 64, 63, kind, rng)
    peak(s, (52, 26), 38, 64, 63, kind, rng)
    peak(s, (9, 30), 0, 22, 63, kind, rng)
    out = []
    for oy in (0, 32):
        for ox in (0, 32):
            t = surface()
            t.blit(s, (0, 0), (ox, oy, 32, 32))
            out.append(t)
    return out


def mountains():
    made = []
    for kind, examine in (("", "Mountains: sheer, pointed and grey. There's no way over."),
                          ("Snow_", "Snow-capped peaks, sheer ice and rock. There's no way over."),
                          ("Cinder_", "Black volcanic peaks, lava glowing in the cracks. There's no way over.")):
        for v in range(1, 7):
            name = "%sPeak%03d" % (kind, v)
            s = mountain_tile(kind, v)
            save(name, s)
            tile_data(name, SOLID, "0", examine=examine)
            K.minimap_colour(name, average(s))
            made.append(name)
        for i, t in enumerate(big_mountain(kind)):
            name = "%sPeak_Big%03d" % (kind, i + 1)
            save(name, t)
            tile_data(name, SOLID, "0", examine=examine)
            K.minimap_colour(name, average(t))
            made.append(name)
    return made


# ================================================================== the dragon's work
def scorched():
    made = []
    for v in range(1, 4):
        rng = random.Random("scorch%d" % v)
        s = surface()
        s.fill((38, 32, 30))
        noise(rng, s, [(28, 24, 22), (54, 46, 42), (70, 64, 60)], 260)
        for _ in range(4):                                       # (ash drifted in streaks)
            x, y = rng.randrange(S), rng.randrange(S)
            for k in range(rng.randrange(4, 9)):
                s.set_at(((x + k) % S, (y + k // 3) % S), (110, 104, 98))
        for _ in range(3 + v):                                   # (embers)
            s.set_at((rng.randrange(S), rng.randrange(S)), rng.choice([(232, 108, 40), (200, 70, 30)]))
        for _ in range(2):                                       # (burnt stalks of grass)
            x, y = rng.randrange(2, 30), rng.randrange(4, 30)
            pygame.draw.line(s, (20, 16, 14), (x, y), (x + rng.choice((-1, 1)), y - 3))
        name = "Scorched%03d" % v
        save(name, s)
        tile_data(name, OPEN, "1", blend=3, examine="Scorched earth. Nothing grows where the dragon has breathed.")
        K.minimap_colour(name, average(s))
        made.append(name)
    return made


def burnt_walls():
    """Galaith's walls and gates, white stone, burnt black: soot thickest at the foot and in blotches."""
    made = []
    for src, dst, n in (("Galaith_Wall", "Burnt_Wall", 5), ("Galaith_Gate", "Burnt_Gate", 6)):
        for v in range(1, n + 1):
            a = "%s%03d" % (src, v)
            path = os.path.join(TILES_DIR, a + ".png")
            if not os.path.exists(path):
                continue
            im = pygame.image.load(path).convert_alpha()
            rng = random.Random(dst + str(v))
            blots = [(rng.randrange(S), rng.randrange(S), rng.randrange(6, 14)) for _ in range(4)]
            out = im.copy()
            for y in range(S):
                for x in range(S):
                    c = im.get_at((x, y))
                    if c.a < 10:
                        continue
                    k = 0.35 + 0.45 * (y / S)
                    for bx, by, r in blots:
                        d = math.hypot(x - bx, y - by)
                        if d < r:
                            k += 0.35 * (1 - d / r)
                    k = min(0.92, k + rng.uniform(-0.05, 0.05))
                    out.set_at((x, y), (int(c.r * (1 - k) + 18 * k), int(c.g * (1 - k) + 14 * k),
                                        int(c.b * (1 - k) + 12 * k), c.a))
            b = "%s%03d" % (dst, v)
            save(b, out)
            K.copy_tile(b, a, Examine_Info="Galaith's wall: white stone once, burnt black by dragon fire.")
            K.minimap_colour(b, average(out))
            made.append(b)
    return made


# ================================================================== streets
def bricks(s, rng, colours, mortar, bw=8, bh=4):
    s.fill(mortar)
    for row in range(S // bh):
        off = (bw // 2) * (row % 2)
        for col in range(-1, S // bw + 1):
            x, y = col * bw + off, row * bh
            c = rng.choice(colours)
            pygame.draw.rect(s, c, (x + 1, y + 1, bw - 1, bh - 1))
            s.set_at(((x + 1) % S, y + 1), tuple(min(255, v + 18) for v in c))


def flags(s, rng, colours, joint, sizes=(10, 16)):
    """Irregular rectangular flagstones, packed row by row."""
    s.fill(joint)
    y = 0
    while y < S:
        h = rng.randrange(*sizes)
        x = -rng.randrange(0, 6)
        while x < S:
            w = rng.randrange(*sizes)
            c = rng.choice(colours)
            pygame.draw.rect(s, c, (x + 1, y + 1, w - 1, h - 1))
            pygame.draw.line(s, tuple(min(255, v + 16) for v in c), (x + 1, y + 1), (x + w - 2, y + 1))
            x += w
        y += h
    noise(rng, s, [tuple(max(0, v - 14) for v in colours[0])], 30)


def cobbles(s, rng, colours, gap):
    """Round stones in staggered rows (drawn wrapped, so the tile repeats without a seam)."""
    s.fill(gap)
    for row in range(4):
        y = row * 8
        for col in range(4):
            x = col * 8 + (4 if row % 2 else 0) + rng.randrange(-1, 1)
            c = rng.choice(colours)
            for ox in (-S, 0, S):
                for oy in (-S, 0, S):
                    pygame.draw.ellipse(s, c, (x + ox, y + oy, 7, 7))
                    pygame.draw.arc(s, tuple(min(255, v + 30) for v in c), (x + ox, y + oy, 7, 7), 1.6, 3.2)
                    pygame.draw.arc(s, tuple(max(0, v - 30) for v in c), (x + ox, y + oy, 7, 7), 4.7, 6.2)


def gravel(s, rng, base, colours):
    s.fill(base)
    noise(rng, s, colours, 330)


def planks(s, rng, colours, gap):
    s.fill(gap)
    for y in range(0, S, 6):
        c = rng.choice(colours)
        pygame.draw.rect(s, c, (0, y, S, 5))
        for x in range(0, S, 16):
            pygame.draw.line(s, gap, (x + (y // 6) * 5 % 16, y), (x + (y // 6) * 5 % 16, y + 4))
        s.set_at((rng.randrange(S), y + 2), (60, 40, 22))         # (a nail)


def basalt(s, rng):
    s.fill((26, 22, 22))
    for y in range(0, S + 8, 8):
        for x in range(0, S + 8, 9):
            ox = 4 if (y // 8) % 2 else 0
            pts = [(x + ox + dx, y + dy) for dx, dy in ((0, -3), (4, -1), (4, 3), (0, 5), (-4, 3), (-4, -1))]
            pygame.draw.polygon(s, rng.choice([(58, 54, 56), (66, 60, 62), (50, 46, 48)]), pts)
            pygame.draw.line(s, (84, 78, 80), pts[0], pts[1])


STREETS = {   # name: (how it's drawn, what Examine says)
    "Brick_Paving001": (lambda s, r: bricks(s, r, [(150, 62, 46), (166, 74, 54), (132, 54, 40), (156, 84, 60)],
                                              (98, 82, 72)), "A street of red brick."),
    "Cobble001": (lambda s, r: cobbles(s, r, [(132, 130, 126), (118, 116, 112), (146, 142, 136)], (70, 66, 62)),
                  "Grey cobbles, worn round."),
    "Marble_Paving001": (lambda s, r: flags(s, r, [(232, 230, 224), (222, 220, 214), (240, 238, 232)],
                                            (176, 172, 166), (12, 17)), "White marble flags."),
    "Mage_Flag001": (lambda s, r: flags(s, r, [(112, 124, 146), (100, 112, 134), (124, 136, 158)], (62, 68, 84)),
                     "Blue-grey flagstones, faintly glittering."),
    "Slate_Flag001": (lambda s, r: flags(s, r, [(74, 76, 84), (66, 68, 76), (84, 86, 94)], (38, 40, 46)),
                      "Dark slate flags."),
    "Red_Sandstone001": (lambda s, r: flags(s, r, [(176, 104, 78), (164, 94, 70), (186, 116, 88)], (110, 66, 50)),
                         "Red sandstone setts, from the hills."),
    "Flagstone001": (lambda s, r: flags(s, r, [(140, 138, 132), (128, 126, 120), (152, 150, 144)], (86, 84, 80)),
                     "Grey flagstones, swept clear of snow."),
    "Gravel001": (lambda s, r: gravel(s, r, (146, 132, 108), [(120, 108, 88), (170, 160, 140), (132, 126, 116),
                                                               (100, 90, 74)]), "A gravel path."),
    "Basalt_Paving001": (lambda s, r: basalt(s, r), "Black basalt setts, warm underfoot."),
    "Sandstone_Paving001": (lambda s, r: flags(s, r, [(216, 192, 142), (206, 182, 132), (226, 202, 152)],
                                               (160, 138, 96)), "Pale sandstone slabs."),
    "Boardwalk001": (lambda s, r: planks(s, r, [(130, 94, 58), (118, 84, 50), (140, 104, 64)], (60, 52, 40)),
                     "A boardwalk over the marsh."),
}


def streets():
    made = []
    for name, (draw, examine) in STREETS.items():
        s = surface()
        draw(s, random.Random(name))
        save(name, s)
        tile_data(name, OPEN, "1", blend=2, examine=examine, speed="1.2")
        K.minimap_colour(name, average(s))
        made.append(name)
    return made


# ------------------------------------------------------------------ things on the roads and at the ports
OUTLINE = (34, 26, 20)


def outlined(s):
    """The 1 px dark outline round it (the mask's silhouette, a pixel out each way: build_cats.py's way)."""
    sil = pygame.mask.from_surface(s).to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    out = surface()
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def signpost():
    """A signpost: a weathered post, three arms pointing three ways."""
    s = surface()
    wood, dark, light = (128, 92, 56), (92, 64, 38), (164, 124, 80)
    pygame.draw.rect(s, wood, (15, 6, 3, 25))
    pygame.draw.line(s, light, (15, 6), (15, 30))
    pygame.draw.line(s, dark, (17, 6), (17, 30))
    for y, x1, x2, tip in ((7, 17, 28, 1), (13, 5, 15, -1), (19, 17, 26, 1)):
        pygame.draw.rect(s, wood, (x1, y, x2 - x1, 4))
        pygame.draw.line(s, light, (x1, y), (x2 - 1, y))
        pygame.draw.line(s, dark, (x1, y + 3), (x2 - 1, y + 3))
        tx = x2 if tip > 0 else x1 - 1
        pygame.draw.polygon(s, wood, [(tx, y), (tx + 2 * tip, y + 2), (tx, y + 3)])
        for k in range(2):
            s.set_at((x1 + 2 + k * 3, y + 1 + k % 2), dark)
    pygame.draw.ellipse(s, (70, 60, 40, 120), (11, 28, 11, 4))
    pygame.image.save(outlined(s), os.path.join(ROOT, "sprites", "Entities", "Signpost.png"))
    K.section(K.ENTS, "Signpost", [("Type", "StaticObject"), ("Use.Words", "Read"),
                                   ("Examine.Info", "A signpost: which way the roads go.")])
    return ["Signpost"]


def moored_boat():
    """The ports' boats: the ferry's boat (its frames) moored, someone else's."""
    for frame in ("", "1", "2"):
        src = os.path.join(ROOT, "sprites", "Entities", "Boat001%s.png" % frame)
        dst = os.path.join(ROOT, "sprites", "Entities", "Moored_Boat%s.png" % frame)
        pygame.image.save(pygame.image.load(src), dst)
    K.section(K.ENTS, "Moored_Boat", [("Type", "StaticObject"), ("Use.Words", "Examine"),
                                      ("Examine.Info", "A fishing boat, moored at the pier, rocking on the swell."),
                                      ("Solid", "0"), ("Anim.Frames", "2"), ("Anim.Speed", "900")])
    return ["Moored_Boat"]


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    made = mountains() + scorched() + burnt_walls() + streets() + signpost() + moored_boat()
    print("Drew %d tiles: %s" % (len(made), ", ".join(made)))


if __name__ == "__main__":
    main()
