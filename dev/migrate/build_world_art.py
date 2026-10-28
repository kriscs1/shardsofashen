"""The new mainland's own tiles (dev\\World Plan.md), drawn in code (sprites\\Tiles), with their Tiles.ini sections and
minimap colours:

  * Mountains you can't cross, pointy: Peak001-006 and the 2 x 2 Peak_Big001-004 and the 3 x 3 Peak_Huge001-009 (the blue-grey West Range), the same
    snow-capped and white (Snow_Peak..., the Frostpeak range) and black with lava in the cracks (Cinder_Peak...).
  * The dragon's work at Galaith: Scorched001-003 (black earth, ash and embers), and Galaith's white walls and gates
    burnt black on the side that faces the dragon (Burnt_Wall001-005, Burnt_Gate001-006: Galaith_Wall/Gate, sooted).
  * Streets of local stuff: Brick_Paving001 (red brick), Cobble001 (grey cobbles), Marble_Paving001 (white flags),
    Mage_Flag001 (blue-grey flags), Slate_Flag001 (dark slate), Red_Sandstone001, Flagstone001 (grey flags),
    Gravel001, Basalt_Paving001 (black basalt), Sandstone_Paving001, Boardwalk001 (planks over the marsh).
  * Signpost (where the roads meet: which way places lie) and Moored_Boat (the ports' boats: the ferry's boat's
    frames), in sprites\\Entities, with their Entities.ini sections.

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
# Flat-shaded, like a painted range: each mountain a lit face west of a wandering ridge line and a shaded face east of
# it, rock ribs down both, a jagged snow cap; behind them a paler, hazy range; the rock fills each tile, so the
# tiles side by side are one mass.
KINDS = {   # prefix: the rock (body), the far range (haze), the lit face, the shaded face, the deep folds, cap, cracks
    "": dict(body=(116, 128, 152), haze=(150, 162, 184), lit=(170, 182, 204), shade=(104, 115, 141),
             dark=(78, 87, 112), cap=(238, 243, 250), crack=None),
    "Snow_": dict(body=(178, 194, 214), haze=(206, 218, 232), lit=(240, 245, 251), shade=(160, 178, 204),
                  dark=(126, 146, 178), cap=(255, 255, 255), crack=None),
    "Cinder_": dict(body=(84, 66, 60), haze=(110, 90, 82), lit=(138, 106, 88), shade=(74, 58, 54),
                    dark=(48, 38, 36), cap=None, crack=(236, 112, 40)),
}


def slope(a, b, rng, n, wob):
    """Points from a to b, a little uneven (a mountain's shoulders)."""
    (x1, y1), (x2, y2) = a, b
    return [(x1 + (x2 - x1) * i / n + rng.uniform(-wob, wob), y1 + (y2 - y1) * i / n + rng.uniform(-wob, wob))
            for i in range(1, n)]


def peak(s, apex, left, right, base_y, kind, rng, cap=True, far=False):
    """One mountain: its outline with shoulders, the shaded face, the lit face west of the ridge line, ribs, a cap."""
    k = KINDS[kind]
    ax, ay = apex
    h = base_y - ay
    lside = slope((left, base_y), (ax, ay), rng, 3, h * 0.06)
    rside = slope((ax, ay), (right, base_y), rng, 3, h * 0.06)
    outline = [(left, base_y)] + lside + [(ax, ay)] + rside + [(right, base_y)]
    if far:                                                     # (the range behind: one hazy shape)
        pygame.draw.polygon(s, k["haze"], outline)
        return
    pygame.draw.polygon(s, k["shade"], outline)
    ridge = [(ax, ay)] + [(ax + rng.uniform(-2, 3) + (right - ax) * 0.12 * t, ay + h * t) for t in (0.3, 0.55, 0.8)]
    ridge.append((ax + (right - ax) * 0.18, base_y))
    pygame.draw.polygon(s, k["lit"], [(left, base_y)] + lside + ridge)
    for t in (0.35, 0.6, 0.85):                                 # rock ribs: dark down the shade, pale down the lit
        y0 = ay + h * t * 0.7
        x0 = ax + (right - ax) * 0.12 * t + 1
        pygame.draw.line(s, k["dark"], (x0, y0), (x0 + (right - ax) * 0.35, y0 + h * 0.3))
        x1 = ax - (ax - left) * t * 0.6
        pygame.draw.line(s, k["body"], (x1, ay + h * t), (x1 + (ax - left) * 0.15, ay + h * (t + 0.22)))
    if cap and k["cap"]:                                        # a jagged snow cap, dripping down the gullies
        ch = h * rng.uniform(0.22, 0.32)
        lx = ax - (ax - left) * ch / h
        rx = ax + (right - ax) * ch / h * 0.85
        teeth = [(lx, ay + ch)]
        for i in range(1, 4):
            teeth.append((lx + (rx - lx) * i / 4, ay + ch * (0.55 if i % 2 else 1.25)))
        teeth.append((rx, ay + ch * 0.85))
        pygame.draw.polygon(s, k["cap"], [(ax, ay)] + teeth[::-1])
        pygame.draw.line(s, k["shade"], (ax + 1, ay + 2), (ax + 2, ay + ch * 0.8))    # (the cap's shaded side)
    if k["crack"]:                                              # (lava glowing in a crack)
        x, y = ax + 1, ay + h * 0.3
        for _ in range(int(h * 0.25)):
            x += rng.choice((-1, 0, 1))
            y += 2
            s.set_at((int(x), int(y)), k["crack"])
    pygame.draw.lines(s, k["dark"], False, outline, 1)


def range_surface(kind, w, h, seed, peaks, far):
    rng = random.Random(seed)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(KINDS[kind]["body"])
    for apex, left, right in far:
        peak(s, apex, left, right, h - 1, kind, rng, far=True)
    for apex, left, right in peaks:
        peak(s, apex, left, right, h - 1, kind, rng)
    return s


def cut(s, n):
    out = []
    for oy in range(0, n * S, S):
        for ox in range(0, n * S, S):
            t = surface()
            t.blit(s, (0, 0), (ox, oy, S, S))
            out.append(t)
    return out


def mountain_tile(kind, v):
    near, far = {   # (the near peaks: apex, left, right), (the far ones)
        1: ([((16, 2), 0, 32)], [((6, 10), -8, 18), ((27, 8), 14, 40)]),
        2: ([((10, 7), -2, 21), ((23, 3), 11, 34)], [((17, 4), 4, 30)]),
        3: ([((11, 3), -2, 26), ((27, 15), 18, 34)], [((24, 6), 12, 36)]),
        4: ([((21, 3), 6, 34), ((6, 13), -4, 15)], [((10, 5), -6, 24)]),
        5: ([((8, 12), -2, 17), ((18, 8), 8, 27), ((27, 14), 19, 34)], [((14, 3), 0, 30)]),
        6: ([((16, 5), 2, 31), ((4, 18), -4, 11), ((29, 19), 22, 36)], [((8, 6), -6, 20), ((26, 7), 12, 40)]),
    }[v]
    return range_surface(kind, S, S, "%s%d" % (kind, v), near, far)


def big_mountain(kind):
    """A 2 x 2 mountain (64 x 64), cut into four tiles."""
    return cut(range_surface(kind, 64, 64, kind + "big", [((30, 2), -2, 66), ((54, 28), 40, 68), ((9, 32), -4, 24)],
                             [((14, 14), -10, 38), ((48, 10), 26, 70)]), 2)


def huge_mountain(kind):
    """A 3 x 3 summit (96 x 96), its shoulders and a lesser peak, cut into nine tiles."""
    return cut(range_surface(kind, 96, 96, kind + "huge", [((46, 3), -4, 100), ((78, 34), 58, 100),
                                                           ((14, 40), -6, 38)],
                             [((24, 18), -10, 56), ((70, 14), 40, 104)]), 3)


def mountains():
    made = []
    for kind, examine in (("", "Mountains: sheer, pointed and blue-grey. There's no way over."),
                          ("Snow_", "Snow-capped peaks, sheer ice and rock. There's no way over."),
                          ("Cinder_", "Black volcanic peaks, lava glowing in the cracks. There's no way over.")):
        for v in range(1, 7):
            name = "%sPeak%03d" % (kind, v)
            s = mountain_tile(kind, v)
            save(name, s)
            tile_data(name, SOLID, "0", examine=examine)
            K.minimap_colour(name, average(s))
            made.append(name)
        for size, tiles in (("Big", big_mountain(kind)), ("Huge", huge_mountain(kind))):
            for i, t in enumerate(tiles):
                name = "%sPeak_%s%03d" % (kind, size, i + 1)
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
