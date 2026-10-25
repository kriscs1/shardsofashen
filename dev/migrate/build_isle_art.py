"""Pictures for the Isle, drawn here (run it again to draw them again):

  python -I "dev\\migrate\\build_isle_art.py"

  * sprites\\Walk\\Tallulah2a-c / 8a-c: a small white rabbit with black patches, hopping.
  * sprites\\Walk\\Cow2a-c / 8a-c: a black-and-white cow, walking.
  * sprites\\Tiles\\Wood_Gate001-004: a gate in the white-capped picket fence (Wood_Fence), shut and open, across
    (east-west) and up-and-down (north-south). On grass: a gate is the ground (a door), not decor.
  * sprites\\Tiles\\Chapel_Stone001 (pale dressed stone, a wall), Chapel_Stone_Upper001-002 (the storey above, plain
    and with a stained-glass lancet), Stained_Glass001 (a lancet window for the wall), Steeple001-002 (the bell
    tower's face and belfry); the spire (Steeple_Spire*) is drawn over the roof by build_isle.py (it needs the roof
    under it).
  * sprites\\Tiles\\Hatch001 (a square hole in a flagstone floor, a ladder going down: a way down with a square base),
    Trapdoor001 (shut: wooden boards, iron bands, a ring) and Trapdoor002 (open: as Hatch001).
"""
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

TILES = os.path.join(ROOT, "sprites", "Tiles")
WALK = os.path.join(ROOT, "sprites", "Walk")
OUTLINE = (34, 30, 30)


def outlined(s, col=OUTLINE):
    """A one-pixel dark outline round what's drawn (as the game's creatures have)."""
    shape = pygame.mask.from_surface(s)
    out = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sil = shape.to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(s, (0, 0))
    return out


def small(img, k):
    """img drawn smaller (nearest pixel: no blur), standing on the same ground line, in the middle."""
    w = round(32 * k)
    out = pygame.Surface((32, 32), pygame.SRCALPHA)
    out.blit(pygame.transform.scale(img, (w, w)), ((32 - w) // 2, 29 - round(29 * k)))
    return out


def save_walk(name, frames):
    for f, img in zip("abc", frames):
        pygame.image.save(img, os.path.join(WALK, "%s2%s.png" % (name, f)))
        pygame.image.save(pygame.transform.flip(img, True, False), os.path.join(WALK, "%s8%s.png" % (name, f)))


def tile(name):
    return pygame.image.load(os.path.join(TILES, name + ".png")).convert_alpha()


# ---------------------------------------------------------------- Tallulah: a small, round, patchy rabbit
def rabbit(frame):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    white, shade, black, pink = (246, 244, 238), (214, 210, 204), (40, 36, 38), (236, 160, 170)
    lift = (0, -3, -1)[frame]                    # (crouched, mid-hop, landing)
    stretch = (0, 3, 1)[frame]
    # the hind leg, long and folded (stretched out behind, mid-hop)
    if frame == 1:
        pygame.draw.ellipse(s, shade, (6, 22 + lift, 8, 4))
    else:
        pygame.draw.ellipse(s, shade, (9, 25 + lift, 8, 3))
    # the body: a round rump, a smaller chest
    pygame.draw.circle(s, white, (13, 22 + lift), 6)
    pygame.draw.ellipse(s, white, (12, 18 + lift, 9 + stretch, 9))
    pygame.draw.circle(s, white, (8, 20 + lift), 2)                         # the tail, a puff
    pygame.draw.ellipse(s, black, (12, 18 + lift, 5, 4))                     # a patch on its back
    pygame.draw.circle(s, black, (10, 24 + lift), 2)
    # the front paws
    fx = 20 + stretch
    pygame.draw.line(s, shade, (fx, 25 + lift), (fx + (1 if frame == 1 else 0), 27 + lift + (0 if frame == 1 else 0)), 2)
    # the head: round, with a pink nose and a dark eye
    hx, hy = 21 + stretch, 18 + lift
    pygame.draw.circle(s, white, (hx, hy), 4)
    pygame.draw.circle(s, white, (hx + 2, hy + 1), 3)
    pygame.draw.ellipse(s, black, (hx - 2, hy - 3, 4, 4))                    # a patch round the eye
    s.set_at((hx, hy - 1), (250, 250, 250))
    s.set_at((hx + 1, hy - 1), (20, 18, 20))
    s.set_at((hx + 4, hy + 1), pink)
    # the ears: long, laid back a little when it hops
    tilt = (0, 2, 1)[frame]
    for ex, h in ((hx - 2, 9), (hx, 8)):
        pygame.draw.polygon(s, white, [(ex, hy - 2), (ex - 1 - tilt, hy - h), (ex + 1 - tilt, hy - h - 1), (ex + 2, hy - 2)])
        pygame.draw.line(s, pink, (ex, hy - 3), (ex - tilt, hy - h + 1))
    pygame.draw.line(s, black, (hx - 3 - tilt, hy - 10), (hx - 2 - tilt, hy - 9))   # (black tips)
    return outlined(s, (60, 54, 56))


# ---------------------------------------------------------------- the cow
COW = dict(hide=(244, 242, 236), shade=(206, 200, 192), patch=(36, 32, 32), nose=(236, 168, 160),
           horn=(232, 222, 190), hoof=(70, 60, 52))
COW_LEGS = [(8, (0, 2, -2), True), (11, (0, -2, 2), False), (20, (0, -2, 2), True), (23, (0, 2, -2), False)]


def cow(frame):
    c = COW
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    bob = (0, -1, 0)[frame]

    def leg(x, dx, far):
        col = c["shade"] if far else c["hide"]
        pygame.draw.line(s, col, (x, 20 + bob), (x + dx // 2, 27), 3)
        pygame.draw.rect(s, c["hoof"], (x + dx // 2 - 1, 27, 3, 2))
    for x, offs, far in COW_LEGS:
        if far:
            leg(x, offs[frame], True)
    # the tail, hanging, a dark tuft
    pygame.draw.line(s, c["shade"], (5, 13 + bob), (3, 21 + bob), 1)
    pygame.draw.circle(s, c["patch"], (3, 22 + bob), 1)
    # the body: deep and long, the back straight
    pygame.draw.rect(s, c["hide"], (5, 11 + bob, 20, 11), border_radius=4)
    pygame.draw.line(s, c["shade"], (6, 21 + bob), (23, 21 + bob))           # (the belly's shadow)
    for px, py, pw, ph in ((7, 12, 6, 5), (16, 11, 5, 4), (11, 17, 4, 3), (20, 16, 3, 3)):   # its patches
        pygame.draw.ellipse(s, c["patch"], (px, py + bob, pw, ph))
    pygame.draw.ellipse(s, c["nose"], (12, 20 + bob, 6, 3))                  # the udder
    # the head: long, a pink muzzle, ears out and short horns
    hx, hy = 23, 8 + bob
    pygame.draw.polygon(s, c["hide"], [(22, 12 + bob), (hx + 2, hy), (hx + 6, hy + 1), (hx + 7, hy + 7), (24, 16 + bob)])
    pygame.draw.ellipse(s, c["patch"], (hx + 1, hy, 4, 4))                    # a patch over the eye
    pygame.draw.ellipse(s, c["nose"], (hx + 4, hy + 5, 5, 4))
    s.set_at((hx + 7, hy + 6), (120, 70, 70))
    s.set_at((hx + 3, hy + 2), (12, 10, 10))
    pygame.draw.line(s, c["patch"], (hx + 1, hy + 1), (hx - 2, hy - 1), 2)   # the ear
    pygame.draw.line(s, c["horn"], (hx + 3, hy), (hx + 3, hy - 3))           # the horn
    for x, offs, far in COW_LEGS:
        if not far:
            leg(x, offs[frame], False)
    return outlined(s)


# ---------------------------------------------------------------- gates in the picket fence
CAP, POST_L, POST, POST_D, PICKET, RAIL, SHADOW = ((200, 200, 200), (160, 80, 40), (120, 80, 40), (80, 40, 0),
                                                    (160, 120, 80), (160, 120, 40), (0, 0, 0, 90))


BOARD, BOARD_L, BOARD_D, IRON = (132, 86, 46), (166, 114, 64), (84, 52, 26), (40, 40, 44)


def post(s, x, top=3, bottom=21):
    """A gate post: taller than the fence's, a round knob on top (so the gate stands out from the pickets)."""
    pygame.draw.rect(s, POST_L, (x, top + 3, 1, bottom - top - 2))
    pygame.draw.rect(s, POST, (x + 1, top + 3, 2, bottom - top - 2))
    pygame.draw.rect(s, POST_D, (x + 3, top + 3, 1, bottom - top - 2))
    pygame.draw.circle(s, CAP, (x + 2, top + 2), 2)
    s.set_at((x + 1, top + 1), (250, 250, 250))


def boards(s, rect, upright=True):
    """A gate's leaf: solid boards (not pickets), a dark Z-brace, iron hinges."""
    x, y, w, h = rect
    pygame.draw.rect(s, BOARD, rect)
    if upright:
        for bx in range(x + 3, x + w, 4):
            pygame.draw.line(s, BOARD_D, (bx, y), (bx, y + h - 1))
    else:
        for by in range(y + 3, y + h, 4):
            pygame.draw.line(s, BOARD_D, (x, by), (x + w - 1, by))
    pygame.draw.line(s, BOARD_L, (x, y), (x + w - 1, y))
    pygame.draw.rect(s, BOARD_D, (x, y + 1, w, 2))                          # the top rail
    pygame.draw.rect(s, BOARD_D, (x, y + h - 3, w, 2))                      # the bottom rail
    pygame.draw.line(s, BOARD_D, (x + 1, y + h - 3), (x + w - 2, y + 2), 2) # the brace
    pygame.draw.rect(s, (0, 0, 0), rect, 1)


def gate_across(open_):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)          # (see-through: decor, over whatever ground it's on)
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(sh, SHADOW, (0, 22, 32, 3))
    if open_:
        pygame.draw.rect(sh, SHADOW, (6, 10, 4, 20))
    s.blit(sh, (0, 0))
    if open_:                                     # swung in, against the left post: seen edge-on, going down
        boards(s, pygame.Rect(4, 9, 5, 19), upright=False)
        for y in (11, 24):
            pygame.draw.rect(s, IRON, (3, y, 3, 2))
    else:
        boards(s, pygame.Rect(4, 9, 24, 13))
        for y in (11, 18):                       # hinges, on the left post
            pygame.draw.rect(s, IRON, (3, y, 5, 2))
        pygame.draw.rect(s, IRON, (25, 13, 3, 4))                            # the latch
        pygame.draw.circle(s, IRON, (24, 15), 1)
    post(s, 0)
    post(s, 28)
    return s


def gate_upright(open_):
    s = pygame.Surface((32, 32), pygame.SRCALPHA)          # (see-through: decor, over whatever ground it's on)
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(sh, SHADOW, (19, 2, 3, 30))
    if open_:
        pygame.draw.rect(sh, SHADOW, (18, 13, 12, 3))
    s.blit(sh, (0, 0))
    for y in (0, 27):                            # a post at each end, with its knob
        pygame.draw.circle(s, CAP, (16, y + 2), 2)
        pygame.draw.rect(s, POST_L, (14, y + 3, 1, 3))
        pygame.draw.rect(s, POST, (15, y + 3, 2, 3))
        pygame.draw.rect(s, POST_D, (17, y + 3, 1, 3))
    if open_:                                     # swung back against the top post: its face, toward you
        boards(s, pygame.Rect(18, 5, 12, 9))
        pygame.draw.rect(s, IRON, (17, 6, 3, 2))
        pygame.draw.rect(s, IRON, (17, 11, 3, 2))
    else:                                         # along the fence line, edge-on: thick, dark, ironed
        pygame.draw.rect(s, BOARD, (13, 6, 6, 21))
        pygame.draw.rect(s, BOARD_L, (13, 6, 1, 21))
        pygame.draw.rect(s, BOARD_D, (18, 6, 1, 21))
        for y in range(9, 26, 4):
            pygame.draw.line(s, BOARD_D, (14, y), (17, y))
        for y in (8, 22):                        # hinge straps
            pygame.draw.rect(s, IRON, (12, y, 8, 2))
        pygame.draw.rect(s, IRON, (12, 15, 2, 3))                            # the latch
        pygame.draw.rect(s, (0, 0, 0), (13, 6, 6, 21), 1)
    return s


# ---------------------------------------------------------------- the chapel's stone
STONE = (208, 202, 188)
MORTAR = (148, 140, 128)


def ashlar(seed, rows=((0, 8), (8, 8), (16, 8), (24, 8))):
    rng = random.Random(seed)
    s = pygame.Surface((32, 32))
    s.fill(MORTAR)
    for i, (y, h) in enumerate(rows):
        off = 0 if i % 2 == 0 else -8
        x = off
        while x < 32:
            w = 16
            k = rng.uniform(-10, 10)
            col = tuple(max(0, min(255, int(v + k))) for v in STONE)
            pygame.draw.rect(s, col, (x + 1, y + 1, w - 1, h - 1))
            pygame.draw.line(s, tuple(min(255, v + 18) for v in col), (x + 1, y + 1), (x + w - 2, y + 1))   # (lit top)
            for _ in range(6):
                px, py = rng.randrange(x + 1, x + w), rng.randrange(y + 1, y + h)
                if 0 <= px < 32:
                    s.set_at((px, py), tuple(max(0, v - 14) for v in col))
            x += w
    return s


def lancet(s, x, y, w, h, glass=True):
    """A pointed window: a pale stone surround, coloured glass in lead."""
    rng = random.Random(x * 31 + y)
    surround = (230, 226, 214)
    top = y + w // 2

    def shape(dx, dy, ww, hh):
        r = ww / 2
        pts = [(dx, top + dy), (dx, y + hh), (dx + ww, y + hh), (dx + ww, top + dy)]
        arc = [(dx + r - r * math.cos(a), top + dy - r * math.sin(a) * 1.25) for a in [i * math.pi / 8 for i in range(9)]]
        return pts[:1] + arc + pts[3:] + pts[2:3] + pts[1:2]
    pygame.draw.polygon(s, surround, shape(x - 2, -1, w + 4, h + 1))
    pygame.draw.polygon(s, (40, 32, 40), shape(x, 0, w, h))
    if not glass:
        return
    colours = [(196, 40, 48), (40, 80, 200), (232, 190, 40), (50, 150, 70), (130, 50, 160)]
    clip = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(clip, (255, 255, 255, 255), shape(x + 1, 1, w - 2, h - 2))
    pane = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    for py in range(y - 2, y + h, 3):
        for px in range(x, x + w, 3):
            pygame.draw.rect(pane, rng.choice(colours) + (255,), (px, py, 2, 2))
    pane.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(pane, (0, 0))
    pygame.draw.line(s, (40, 32, 40), (x + w // 2, top - w // 2 + 1), (x + w // 2, y + h - 1))    # (the mullion)
    pygame.draw.line(s, (255, 250, 220), (x + 2, top + 1), (x + 2, y + h - 3))                   # (a glint)


def chapel_upper(window):
    s = ashlar(71 if window else 72, rows=((0, 8), (8, 8), (16, 8)))
    pygame.draw.rect(s, (226, 220, 206), (0, 24, 32, 5))                    # the string course under it
    pygame.draw.line(s, (248, 244, 232), (0, 24), (31, 24))
    pygame.draw.rect(s, (118, 110, 100), (0, 29, 32, 3))
    if window:
        lancet(s, 11, 3, 10, 19)
    return s


def stained_glass():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    lancet(s, 10, 5, 12, 22)
    pygame.draw.rect(s, (230, 226, 214), (8, 27, 16, 2))                     # the sill
    return s


def steeple_face():
    """The bell tower's face over the door: dressed stone, quoins at its edges, a tall stained-glass lancet."""
    s = ashlar(81)
    for y in range(0, 32, 8):                    # (quoins: the corner stones, paler and bigger)
        for x, w in ((0, 5), (27, 5)):
            pygame.draw.rect(s, (232, 228, 216), (x, y + 1, w, 7))
    lancet(s, 10, 2, 12, 28)
    return s


def steeple_belfry():
    """Its belfry: an arched opening, louvres, the bell in the dark; a cornice above."""
    s = ashlar(82)
    for y in range(0, 32, 8):
        for x, w in ((0, 5), (27, 5)):
            pygame.draw.rect(s, (232, 228, 216), (x, y + 1, w, 7))
    pygame.draw.rect(s, (226, 220, 206), (0, 0, 32, 4))                      # the cornice
    pygame.draw.rect(s, (120, 112, 100), (0, 4, 32, 1))
    lancet(s, 9, 8, 14, 22, glass=False)
    pygame.draw.circle(s, (210, 170, 60), (16, 19), 4)                       # the bell
    pygame.draw.rect(s, (210, 170, 60), (12, 19, 9, 3))
    pygame.draw.circle(s, (250, 220, 120), (15, 17), 1)
    for y in (24, 27):                           # louvres
        pygame.draw.line(s, (90, 70, 50), (10, y), (21, y))
    return s


def spire(base, part):
    """The spire, in slate over the roof under it: part 0 its foot, 1 its middle, 2 its tip with the cross."""
    s = base.copy()
    widths = [(26, 18), (18, 10), (10, 2)][part]
    top_y = 14 if part == 2 else 0
    w0, w1 = widths
    pts = [(16 - w1 / 2, top_y), (16 + w1 / 2, top_y), (16 + w0 / 2, 32), (16 - w0 / 2, 32)]
    pygame.draw.polygon(s, (78, 86, 100), pts)
    pygame.draw.polygon(s, (104, 114, 130), [pts[0], (16, top_y), (16, 32), pts[3]])   # (the lit side)
    for y in range(top_y + 3, 32, 4):            # courses of slate
        half = (w1 + (w0 - w1) * (y - top_y) / (32 - top_y)) / 2
        pygame.draw.line(s, (60, 66, 78), (16 - half + 1, y), (16 + half - 1, y))
    if part == 2:                                # the cross, gilt
        pygame.draw.rect(s, (230, 190, 70), (15, 2, 2, 13))
        pygame.draw.rect(s, (230, 190, 70), (12, 5, 8, 2))
        s.set_at((15, 2), (255, 236, 150))
    return s


# ---------------------------------------------------------------- a square way down, and the chapel's trapdoor
def hatch(open_=True, floor="Tile001"):
    """floor: the ground it's cut into (a tile), or None for a hatch that sits on any floor (decor)."""
    s = tile(floor).copy() if floor else pygame.Surface((32, 32), pygame.SRCALPHA)
    frame = (70, 56, 44)
    pygame.draw.rect(s, (40, 34, 30), (2, 2, 28, 28))                        # (its edge, shadowed)
    pygame.draw.rect(s, frame, (3, 3, 26, 26))
    if open_:
        hole = pygame.Rect(5, 5, 22, 22)
        pygame.draw.rect(s, (10, 8, 8), hole)
        for i in range(22):                      # (darker going down)
            pygame.draw.line(s, (26 - i, 22 - i, 20 - i) if i < 20 else (6, 5, 5), (5, 5 + i), (26, 5 + i))
        rail = (150, 110, 64)
        for x in (10, 21):
            pygame.draw.line(s, rail, (x, 5), (x, 26), 2)
        for k, y in enumerate((8, 13, 18, 23)):
            shade = max(40, 150 - k * 30)
            pygame.draw.line(s, (shade, int(shade * 0.74), int(shade * 0.44)), (11, y), (21, y), 2)
        pygame.draw.rect(s, (120, 92, 60), (3, 0, 26, 3))                    # the lid, thrown back
        pygame.draw.line(s, (160, 124, 80), (3, 0), (28, 0))
    else:
        for x in range(5, 27, 5):                # boards
            pygame.draw.rect(s, (128, 92, 56), (x, 5, 4, 22))
            pygame.draw.line(s, (156, 116, 72), (x, 5), (x, 26))
        for y in (8, 22):                        # iron bands, nailed
            pygame.draw.rect(s, (70, 70, 76), (4, y, 24, 3))
            for x in (6, 15, 24):
                s.set_at((x, y + 1), (170, 170, 176))
        pygame.draw.circle(s, (60, 60, 66), (16, 15), 3, 1)                  # the ring
        pygame.draw.rect(s, (120, 120, 126), (14, 12, 4, 1))
        pygame.draw.rect(s, (40, 40, 44), (14, 17, 4, 2))                    # the keyhole plate
        s.set_at((16, 18), (0, 0, 0))
    return s


# ---------------------------------------------------------------- a bench seen from the side (Bench001 faces you)
def side_bench():
    """Facing east: the seat a strip running up the tile, its back along the west side, raised a little."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    lit, wood, dark = (180, 120, 60), (150, 90, 30), (90, 60, 30)
    sh = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 110), (12, 26, 10, 3))                   # (its shadow, on the ground)
    pygame.draw.rect(sh, (0, 0, 0, 110), (20, 9, 3, 19))
    s.blit(sh, (0, 0))
    for x, y0, y1 in ((10, 21, 27), (14, 24, 28), (18, 24, 28)):           # legs
        pygame.draw.line(s, dark, (x, y0), (x, y1), 2)
    pygame.draw.rect(s, wood, (13, 8, 7, 17))                               # the seat: two boards
    pygame.draw.line(s, lit, (13, 8), (13, 24))
    pygame.draw.line(s, dark, (16, 8), (16, 24))
    pygame.draw.line(s, dark, (13, 24), (19, 24))
    pygame.draw.rect(s, wood, (8, 3, 4, 19))                                # the back, standing up behind
    pygame.draw.line(s, lit, (8, 3), (8, 21))
    pygame.draw.line(s, lit, (8, 3), (11, 3))
    for y in (7, 18):                                                       # its posts down to the seat
        pygame.draw.rect(s, dark, (11, y, 3, 2))
    return s


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    save_walk("Tallulah", [small(rabbit(i), 0.8) for i in range(3)])
    save_walk("Cow", [cow(i) for i in range(3)])
    for name, img in (("Wood_Gate001", gate_across(False)), ("Wood_Gate002", gate_across(True)),
                      ("Wood_Gate003", gate_upright(False)), ("Wood_Gate004", gate_upright(True)),
                      ("Chapel_Stone001", ashlar(70)), ("Chapel_Stone_Upper001", chapel_upper(False)),
                      ("Chapel_Stone_Upper002", chapel_upper(True)), ("Stained_Glass001", stained_glass()),
                      ("Steeple001", steeple_face()), ("Steeple002", steeple_belfry()),
                      ("Bench002", side_bench()), ("Bench003", pygame.transform.flip(side_bench(), True, False)),
                      ("Hatch001", hatch(True, None)), ("Trapdoor001", hatch(False)), ("Trapdoor002", hatch(True))):
        pygame.image.save(img, os.path.join(TILES, name + ".png"))
    print("Drew Tallulah, the cow, the gates, the chapel's stone, glass and tower, the hatch and the trapdoor")


if __name__ == "__main__":
    main()
