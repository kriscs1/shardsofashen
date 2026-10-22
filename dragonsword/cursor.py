"""The mouse cursor: it shows what a click will do (walk, talk, attack, chop, mine, fish, open, pick up...) and
animates when you click. The pictures are drawn here (no sprite files) and set as the operating system's colour
cursor, so it never lags behind the mouse and shows on every screen.

Game.cursor_kind is set each frame (interact.detect_mouse_movement); present_frame calls Cursors.update."""
import math

import pygame

SIZE = 32           # the cursor, in screen pixels
K = 2               # drawn at twice the size, then smoothed down
CLICK_MS = 220      # how long the click animation lasts

OUTLINE = (24, 16, 10)
GOLD = (236, 196, 92)
GOLD_DK = (168, 120, 40)
STEEL = (214, 222, 232)
STEEL_DK = (126, 138, 152)
WOOD = (150, 98, 52)
WOOD_DK = (98, 60, 30)
CREAM = (250, 242, 222)
RED = (206, 56, 44)

# verb (upper case) -> cursor kind
VERBS = {
    "WALK HERE": "walk", "TALK TO": "talk", "ATTACK": "attack",
    "EXAMINE": "look", "READ": "look", "SEARCH": "look", "INSPECT": "look", "COUNT": "look",
    "CHOP": "axe", "MINE": "pick", "DIG": "pick", "FISH": "rod",
    "CLIMB UP": "climb_up", "CLIMB DOWN": "climb_down", "CLIMB THROUGH": "climb_up",
    "UNLOCK": "key", "OPEN": "door", "TRAVEL": "door",
    "BUY 1": "coin", "BUY 5": "coin", "SELL 1": "coin", "SELL ALL": "coin", "VALUE": "coin", "BANK": "coin",
    "DEPOSIT 1": "coin", "DEPOSIT ALL": "coin", "WITHDRAW 1": "coin", "WITHDRAW ALL": "coin",
    "EAT": "eat", "DRINK": "drink",
    "MAKE": "hammer", "SMITH": "hammer", "SMELT": "hammer", "COOK": "hammer", "BREW": "hammer", "CRAFT": "hammer",
    "CAST": "magic", "USE WITH": "target",
}
SWINGS = {"attack", "axe", "pick", "hammer"}        # these swing when you click; the others press in


def kind_of_verb(verb):
    return VERBS.get(str(verb).strip().upper(), "hand")


# ---------------------------------------------------------------------------------------------------------- drawing
# Each picture is drawn on a (SIZE*K)-square canvas in 32-unit coordinates (P scales them).
def P(*pts):
    return [(x * K, y * K) for x, y in pts]


def line(s, col, a, b, w):
    pygame.draw.line(s, col, P(a)[0], P(b)[0], int(w * K))
    for pt in (a, b):
        pygame.draw.circle(s, col, P(pt)[0], int(w * K / 2))


def circle(s, col, c, r, w=0):
    pygame.draw.circle(s, col, P(c)[0], int(r * K), int(w * K))


def ellipse(s, col, x, y, w, h, width=0):
    pygame.draw.ellipse(s, col, pygame.Rect(x * K, y * K, w * K, h * K), int(width * K))


def poly(s, col, pts, w=0):
    pygame.draw.polygon(s, col, P(*pts), int(w * K))


def rect(s, col, x, y, w, h, r=0):
    pygame.draw.rect(s, col, pygame.Rect(x * K, y * K, w * K, h * K), 0, int(r * K))


def draw_pointer(s):
    poly(s, CREAM, [(2, 2), (2, 24), (8, 19), (12, 28), (16, 26), (12, 17.5), (20, 17.5)])
    poly(s, GOLD, [(4, 7), (4, 19), (8, 16), (12, 24), (13, 23.5), (9.5, 15.5), (14, 15.5)])


def draw_walk(s):
    for ox, oy, flip in ((5, 13, 1), (15, 3, -1)):          # two footprints, one ahead of the other
        ellipse(s, CREAM, ox, oy + 4, 8, 12)
        ellipse(s, CREAM, ox + 1, oy + 15, 6, 6)
        for i, (tx, ty) in enumerate(((0.5, 1.5), (2.5, 0), (4.8, 0), (6.8, 1.5))):
            circle(s, CREAM, (ox + tx + 0.6, oy + ty + 1), 1.3 if i in (1, 2) else 1.1)


def draw_hand(s):
    rect(s, CREAM, 8, 13, 15, 13, 5)                         # the palm
    for i, h in enumerate((10, 12, 11, 8)):                  # four fingers
        rect(s, CREAM, 8.5 + i * 3.6, 16 - h, 3.2, h + 2, 1.6)
    poly(s, CREAM, [(8, 18), (3, 13), (5, 11), (10, 15)])    # the thumb
    for i in range(3):
        line(s, (218, 196, 170), (12 + i * 3.6, 9), (12 + i * 3.6, 14), 0.5)


def draw_talk(s):
    ellipse(s, CREAM, 2, 3, 28, 19)
    poly(s, CREAM, [(8, 18), (5, 28), (15, 20)])
    for i in range(3):
        circle(s, (92, 74, 60), (10 + i * 6, 12.5), 1.8)


def draw_attack(s):
    poly(s, STEEL, [(2, 2), (8, 3), (22, 17), (17, 22), (3, 8)])     # the blade, point at the hotspot
    line(s, STEEL_DK, (4, 4), (19, 19), 0.8)
    line(s, GOLD, (15, 25), (25, 15), 2.6)                            # the crossguard
    line(s, WOOD_DK, (21, 21), (27, 27), 3)                           # the grip
    circle(s, GOLD, (28, 28), 2.2)


def draw_look(s):
    poly(s, CREAM, [(2, 16), (9, 9), (16, 7), (23, 9), (30, 16), (23, 23), (16, 25), (9, 23)])
    circle(s, (70, 130, 190), (16, 16), 6.5)
    circle(s, OUTLINE, (16, 16), 3.2)
    circle(s, (255, 255, 255), (14.2, 14), 1.4)


def draw_axe(s):
    line(s, WOOD, (9, 9), (28, 28), 3)
    poly(s, STEEL, [(2, 10), (4, 3), (11, 1), (15, 6), (8, 13)])     # the blade, edge at the top left
    line(s, STEEL_DK, (5, 4), (3, 9), 0.8)


def draw_pick(s):
    line(s, WOOD, (16, 10), (27, 28), 3)
    poly(s, STEEL, [(2, 2), (10, 5), (17, 5), (25, 11), (24, 13), (17, 9), (11, 9), (4, 5)])
    rect(s, STEEL_DK, 14, 5, 5, 5, 1)


def draw_rod(s):
    line(s, WOOD, (5, 29), (24, 3), 2.2)
    line(s, WOOD_DK, (5, 29), (8, 25), 3)
    circle(s, STEEL_DK, (9.5, 23.5), 2, 1)                             # the reel
    line(s, CREAM, (24, 3), (27, 18), 0.6)                             # the line and the hook
    pygame.draw.arc(s, STEEL, pygame.Rect(23 * K, 17 * K, 6 * K, 7 * K), math.pi, 2 * math.pi, int(1.2 * K))
    circle(s, RED, (27, 14), 1.6)                                      # a float


def draw_ladder(s, up):
    for x in (6, 15):
        line(s, WOOD, (x, 4), (x, 29), 2)
    for y in range(8, 29, 6):
        line(s, WOOD_DK, (6, y), (15, y), 1.6)
    tip, tail = (25, 3) if up else (25, 29), (25, 26) if up else (25, 6)
    line(s, GOLD, tail, ((tip[0]), tip[1] + (5 if up else -5)), 2.4)
    d = 1 if up else -1
    poly(s, GOLD, [(tip[0], tip[1]), (tip[0] - 5, tip[1] + 7 * d), (tip[0] + 5, tip[1] + 7 * d)])


def draw_key(s):
    circle(s, GOLD, (9, 9), 7)
    circle(s, OUTLINE, (9, 9), 2.6)
    line(s, GOLD, (13, 13), (27, 27), 3)
    line(s, GOLD, (22, 22), (19, 25), 2.6)
    line(s, GOLD, (26, 26), (23, 29), 2.6)


def draw_door(s):
    poly(s, WOOD, [(7, 30), (7, 11), (9, 6), (16, 3), (23, 6), (25, 11), (25, 30)])
    for x in (12, 16, 20):
        line(s, WOOD_DK, (x, 8), (x, 29), 0.6)
    circle(s, GOLD, (21.5, 19), 1.8)


def draw_coin(s):
    for i, (x, y) in enumerate(((8, 20), (8, 16), (8, 12))):           # a stack, and one coin in front
        ellipse(s, GOLD_DK, x, y + 2, 16, 7)
        ellipse(s, GOLD, x, y, 16, 7)
    circle(s, GOLD_DK, (20, 21), 8.5)
    circle(s, GOLD, (20, 20), 8)
    circle(s, GOLD_DK, (20, 20), 5.5, 1)


def draw_eat(s):
    circle(s, RED, (12, 18), 9)
    circle(s, RED, (20, 18), 9)
    circle(s, (240, 120, 104), (11, 15), 2.6)
    line(s, WOOD_DK, (16, 10), (17, 4), 1.4)
    ellipse(s, (96, 168, 72), 17, 3, 9, 5)


def draw_drink(s):
    poly(s, (110, 170, 230), [(9, 14), (23, 14), (27, 26), (24, 30), (8, 30), (5, 26)])
    rect(s, (200, 226, 246), 12, 6, 8, 9)
    rect(s, WOOD, 11, 2, 10, 5, 1)
    circle(s, (232, 244, 255), (11, 22), 1.6)


def draw_hammer(s):
    line(s, WOOD, (12, 12), (28, 28), 3)
    poly(s, STEEL, [(2, 11), (11, 2), (17, 8), (8, 17)])
    poly(s, STEEL_DK, [(8, 17), (17, 8), (18, 9), (9, 18)])


def draw_magic(s):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 13 if i % 2 == 0 else 5.5
        pts.append((16 + r * math.cos(a), 16 + r * math.sin(a)))
    poly(s, (196, 160, 255), pts)
    circle(s, (255, 248, 220), (16, 16), 3.5)
    circle(s, (196, 160, 255), (27, 5), 1.6)
    circle(s, (196, 160, 255), (5, 26), 1.3)


def draw_target(s):
    circle(s, CREAM, (16, 16), 12, 2.6)
    circle(s, CREAM, (16, 16), 5, 2.2)
    for a, b in (((16, 1), (16, 8)), ((16, 24), (16, 31)), ((1, 16), (8, 16)), ((24, 16), (31, 16))):
        line(s, CREAM, a, b, 2)
    circle(s, RED, (16, 16), 1.6)


# kind: (draw, hotspot (in SIZE pixels))
KINDS = {
    "pointer": (draw_pointer, (2, 2)), "walk": (draw_walk, (16, 16)), "hand": (draw_hand, (14, 12)),
    "talk": (draw_talk, (16, 13)), "attack": (draw_attack, (2, 2)), "look": (draw_look, (16, 16)),
    "axe": (draw_axe, (3, 6)), "pick": (draw_pick, (2, 2)), "rod": (draw_rod, (16, 16)),
    "climb_up": (lambda s: draw_ladder(s, True), (16, 16)), "climb_down": (lambda s: draw_ladder(s, False), (16, 16)),
    "key": (draw_key, (9, 9)), "door": (draw_door, (16, 16)), "coin": (draw_coin, (16, 16)),
    "eat": (draw_eat, (16, 16)), "drink": (draw_drink, (16, 16)), "hammer": (draw_hammer, (6, 6)),
    "magic": (draw_magic, (16, 16)), "target": (draw_target, (16, 16)),
}


def picture(kind):
    """The kind's picture, outlined, on the big canvas."""
    draw = KINDS[kind][0]
    big = SIZE * K
    art = pygame.Surface((big, big), pygame.SRCALPHA)
    draw(art)
    sil = pygame.mask.from_surface(art).to_surface(setcolor=OUTLINE + (255,), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((big, big), pygame.SRCALPHA)
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            out.blit(sil, (dx, dy))
    shadow = sil.copy()
    shadow.fill((0, 0, 0, 90), special_flags=pygame.BLEND_RGBA_MULT)
    under = pygame.Surface((big, big), pygame.SRCALPHA)
    under.blit(shadow, (3, 4))
    under.blit(out, (0, 0))
    under.blit(art, (0, 0))
    return under


def frame(big, hot, scale, angle):
    """The picture scaled and turned round its hotspot, at cursor size."""
    n = big.get_width()
    hx, hy = hot[0] * K, hot[1] * K
    if scale != 1 or angle:
        img = pygame.transform.rotozoom(big, angle, scale)
        # where the hotspot ends up: rotozoom turns about the centre and grows the canvas
        c = n / 2
        a = math.radians(-angle)
        vx, vy = (hx - c) * scale, (hy - c) * scale
        rx, ry = vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
        tx, ty = img.get_width() / 2 + rx, img.get_height() / 2 + ry
        canvas = pygame.Surface((n, n), pygame.SRCALPHA)
        canvas.blit(img, (round(hx - tx), round(hy - ty)))
        big = canvas
    return pygame.transform.smoothscale(big, (SIZE, SIZE))


def click_pose(kind, t):
    """(scale, angle) t of the way (0-1) through the click animation."""
    if kind in SWINGS:                      # a swing: back, through, and settle
        k = math.sin(t * math.pi)
        return 1.0 + 0.08 * k, (-38 * k if t < 0.5 else -38 * k + 10 * math.sin((t - 0.5) * 2 * math.pi))
    squash = 1 - 0.24 * math.sin(min(1, t / 0.45) * math.pi / 2) if t < 0.45 else \
        0.76 + 0.24 * (1 + 0.25 * math.sin((t - 0.45) / 0.55 * math.pi))
    return min(1.06, squash), 0


class Cursors:
    def __init__(self):
        self.big = {}
        self.cache = {}
        self.kind = None
        self.shown = None
        self.click_at = None
        self.click_kind = None
        self.ok = True

    def _frame(self, kind, step):
        key = (kind, step)
        if key not in self.cache:
            if kind not in self.big:
                self.big[kind] = picture(kind)
            if step < 0:
                scale, angle = 1, 0
            else:
                scale, angle = click_pose(kind, step / 6.0)
            self.cache[key] = frame(self.big[kind], KINDS[kind][1], scale, angle)
        return self.cache[key]

    def click(self, now):
        self.click_at = now
        self.click_kind = self.kind

    def update(self, kind, now):
        """Shows the cursor for kind (animating a click that was just made). now: milliseconds."""
        if not self.ok:
            return
        if kind not in KINDS:
            kind = "pointer"
        self.kind = kind
        step = -1
        if self.click_at is not None:
            t = (now - self.click_at) / CLICK_MS
            if 0 <= t < 1:
                kind = self.click_kind or kind
                step = min(6, int(t * 7))
            else:
                self.click_at = None
        if (kind, step) == self.shown:
            return
        try:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(KINDS[kind][1], self._frame(kind, step)))
            self.shown = (kind, step)
        except (pygame.error, AttributeError, TypeError):
            self.ok = False                 # no colour cursors here: keep the system arrow
