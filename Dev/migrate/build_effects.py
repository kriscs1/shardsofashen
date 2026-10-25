"""Combat and spell effects (Sprites\\Effects\\*.png): damage splats, impact animations, missiles, the hurt flash.

Run:  python -I "Dev\\migrate\\build_effects.py" [--preview]
Deterministic and re-runnable: only files that change are written. --preview writes Dev\\Renders\\Effects preview.png.
The game loads these the first time each one is needed (fx_load in dragonsword\\combat.py), so there can be many.

  Hit<N>, Crit<N>, Heal<N>  N = 1..99: a red splat, a yellow star (critical hit), a green drop (healing), with N on it
  Miss                     a blue splat with 0 on it (a miss, or a blow the armour turned)
  <Anim>1..4               four-frame animations, 32 x 32: Puff (smoke when something dies), Slash (a sword stroke),
                           Fire_Burst, Ice_Burst, Spark (lightning), Heal_Glow, Stone_Glow, Teleport_Glow; and
                           for work: Wood_Chips, Rock_Chips, Splash, Dirt_Clods, Wool_Tufts
  <Spell>_Missile          16 x 16 projectiles: Fire_Bolt_Missile, Ice_Bolt_Missile, Lightning_Missile
  Hurt_Top, Hurt_Side      the red flash round the edge of the map when the player is hurt (screen width x 8, 8 x height)
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_kit as K
from common import p, read_bmp, Ini

OUT = "Effects"

# 5 x 7 digits
DIGITS = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
}


def number(img, text, cx, cy, fg=(255, 255, 255), outline=(20, 10, 10)):
    w = len(text) * 6 - 1
    x0, y0 = cx - w // 2, cy - 3
    pts = []
    for i, ch in enumerate(text):
        for y, row in enumerate(DIGITS[ch]):
            for x, c in enumerate(row):
                if c == "#":
                    pts.append((x0 + i * 6 + x, y0 + y))
    for x, y in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                K.put(img, x + dx, y + dy, outline)
    for x, y in pts:
        K.put(img, x, y, fg)


def blob(w, h, base, light, dark, outline, seed, spikes=0, spike_len=0.0):
    """A splat: an irregular blob (or a star with spikes) filling a w x h image."""
    img = K.new(w, h)
    rng = random.Random(seed)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    n = 14
    radii = [0.82 + rng.random() * 0.18 for _ in range(n)]
    for y in range(h):
        for x in range(w):
            dx, dy = (x - cx) / (w / 2.0 - 1), (y - cy) / (h / 2.0 - 1)
            a = math.atan2(dy, dx)
            t = (a + math.pi) / (2 * math.pi) * n
            i = int(t) % n
            f = t - int(t)
            r = radii[i] * (1 - f) + radii[(i + 1) % n] * f
            if spikes:
                r = 0.62 + spike_len * max(0.0, math.cos(a * spikes)) ** 3
            d = math.hypot(dx, dy)
            if d <= r:
                k = (-dx - dy) * 0.5 + (1 - d / r) * 0.4
                img[y][x] = light if k > 0.35 else dark if d / r > 0.8 and k < 0 else base
    return K.outline_img(img, outline)


SPLATS = {   # kind: (w, h, base, light, dark, outline, digits colour, spikes, spike length)
    "Hit": (22, 18, (200, 24, 20), (246, 80, 64), (130, 10, 10), (60, 0, 0), (255, 255, 255), 0, 0),
    "Crit": (26, 22, (250, 190, 30), (255, 240, 130), (210, 120, 10), (90, 40, 0), (120, 10, 0), 8, 0.42),
    "Heal": (22, 18, (40, 170, 60), (110, 230, 120), (20, 110, 40), (0, 50, 10), (255, 255, 255), 0, 0),
    "Miss": (20, 16, (40, 90, 210), (100, 150, 250), (20, 50, 140), (0, 20, 70), (255, 255, 255), 0, 0),
}


def splat(kind, n):
    w, h, b, l, d, o, fg, spikes, sl = SPLATS[kind]
    img = blob(w, h, b, l, d, o, seed={"Hit": 3, "Crit": 5, "Heal": 7, "Miss": 9}[kind], spikes=spikes, spike_len=sl)
    number(img, str(n), w // 2, h // 2, fg=fg, outline=(30, 10, 0) if kind != "Crit" else (255, 250, 220))
    return img


# ------------------------------------------------------------------ four-frame animations (32 x 32)
def frames(fn, n=4):
    return [fn(i, n) for i in range(n)]


def particles(i, n, seed, count, colours, spread, rise=0.0, size=(1.5, 3.0), centre=(16, 18), fade_to=None):
    img = K.new()
    rng = random.Random(seed)
    t = (i + 1) / float(n)
    for k in range(count):
        a = rng.random() * 2 * math.pi
        sp = (0.4 + rng.random() * 0.6) * spread
        x = centre[0] + math.cos(a) * sp * t
        y = centre[1] + math.sin(a) * sp * t * 0.8 - rise * t * (0.5 + rng.random())
        r = (size[0] + rng.random() * (size[1] - size[0])) * (1.15 - 0.55 * t)
        col = colours[min(len(colours) - 1, int(t * len(colours) - 0.001 + rng.random() * 0.8))]
        K.shaded_ellipse(img, x, y, r, r, col, K.mix(col, (255, 255, 255), 0.4), K.mul(col, 0.7))
    return img


def puff(i, n):
    return particles(i, n, 11, 9, [(230, 230, 230), (190, 190, 196), (150, 150, 160), (110, 110, 120)], 11, rise=6,
                     size=(3, 5))


def fire_burst(i, n):
    img = particles(i, n, 21, 14, [(255, 250, 200), (255, 210, 60), (250, 120, 20), (180, 40, 10)], 13, rise=4,
                    size=(2, 4))
    if i == 0:
        K.shaded_ellipse(img, 16, 17, 6, 6, (255, 230, 120), (255, 255, 230), (250, 150, 30))
    return img


def ice_burst(i, n):
    img = K.new()
    t = (i + 1) / float(n)
    for k in range(8):
        a = k * math.pi / 4 + 0.3
        ln = 4 + 10 * t
        x1, y1 = 16 + math.cos(a) * ln, 17 + math.sin(a) * ln
        x0, y0 = 16 + math.cos(a) * ln * 0.3, 17 + math.sin(a) * ln * 0.3
        steps = 12
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s / steps
            y = y0 + (y1 - y0) * s / steps
            K.put(img, int(round(x)), int(round(y)), (210, 240, 255) if s > steps * 0.6 else (110, 190, 250))
            K.put(img, int(round(x)) + 1, int(round(y)), (60, 140, 230))
    if i < 2:
        K.shaded_ellipse(img, 16, 17, 5 - i, 5 - i, (170, 220, 255), (240, 250, 255), (90, 160, 240))
    return K.outline_img(img, (20, 50, 110)) if i < 3 else img


def spark(i, n):
    img = K.new()
    rng = random.Random(31 + i)
    for b in range(5):                   # jagged bolts out from the centre
        x, y = 16.0, 16.0
        a = rng.random() * 2 * math.pi
        for s in range(5 + i):
            nx = x + math.cos(a) * 3 + rng.uniform(-1.5, 1.5)
            ny = y + math.sin(a) * 3 + rng.uniform(-1.5, 1.5)
            for k in range(5):
                px, py = x + (nx - x) * k / 4, y + (ny - y) * k / 4
                K.put(img, int(px), int(py), (255, 255, 220))
                K.put(img, int(px) + 1, int(py), (250, 230, 90))
            x, y = nx, ny
    K.shaded_ellipse(img, 16, 16, 4 - i * 0.7, 4 - i * 0.7, (255, 255, 200), (255, 255, 255), (250, 220, 60))
    return img


def sparkles(i, n, seed, colours, rise):
    img = K.new()
    rng = random.Random(seed)
    t = (i + 1) / float(n)
    for k in range(10):
        x = 6 + rng.random() * 20
        y = 26 - rng.random() * 8 - rise * t * (0.6 + rng.random() * 0.6)
        c = colours[k % len(colours)]
        if (k + i) % 3 != 2:
            K.put(img, int(x), int(y), (255, 255, 255))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                K.put(img, int(x) + dx, int(y) + dy, c)
    return img


def heal_glow(i, n):
    return sparkles(i, n, 41, [(90, 230, 110), (170, 255, 170), (60, 190, 90)], 16)


def stone_glow(i, n):
    img = K.new()
    t = (i + 1) / float(n)
    r = 6 + 9 * t
    for a in range(0, 360, 6):
        x = 16 + math.cos(math.radians(a)) * r
        y = 18 + math.sin(math.radians(a)) * r * 0.75
        K.put(img, int(x), int(y), (176, 150, 110) if a % 24 else (230, 210, 160))
        if i < 3:
            K.put(img, int(x), int(y) + 1, (110, 92, 64))
    return img


def teleport_glow(i, n):
    return sparkles(i, n, 51, [(190, 110, 255), (240, 200, 255), (130, 60, 220)], 24)


def slash(i, n):
    img = K.new()
    # a crescent sweeping from the top right down to the bottom left: it grows, then thins away
    sweep = [0.45, 1.0, 1.0, 1.0][i]
    fade = [1.0, 1.0, 0.65, 0.35][i]
    start = [0.0, 0.0, 0.25, 0.55][i]
    for s in range(60):
        f = s / 59.0
        if f < start or f > sweep:
            continue
        a = -0.9 + 2.4 * f                      # radians, from up-right round to down-left
        r = 12
        x, y = 16 + math.cos(a - 0.6) * r * 0.9, 16 + math.sin(a - 0.6) * r
        w = 3.4 * math.sin(math.pi * f) * fade
        if w > 0.5:
            K.shaded_ellipse(img, x, y, w, w, (226, 232, 246), (255, 255, 255), (150, 170, 210))
    return K.outline_img(img, (60, 70, 100)) if i < 2 else img


# (the work of the hands: what flies off what you're working at - a script's Play.Animation)
def wood_chips(i, n):
    return particles(i, n, 31, 9, [(236, 206, 150), (196, 150, 90), (150, 100, 52)], 13, rise=7, size=(1.2, 2.4))


def rock_chips(i, n):
    img = particles(i, n, 41, 9, [(210, 210, 214), (160, 160, 168), (110, 110, 118)], 12, rise=5, size=(1.2, 2.2))
    if i < 2:                                     # (a spark where the pick strikes)
        for x, y in ((15, 16), (17, 15), (16, 18), (18, 17)):
            K.put(img, x, y, (255, 240, 150))
    return img


def splash(i, n):
    return particles(i, n, 51, 10, [(240, 250, 255), (170, 210, 250), (90, 150, 220)], 10, rise=8, size=(1.2, 2.4),
                     centre=(16, 20))


def dirt_clods(i, n):
    return particles(i, n, 61, 8, [(150, 110, 70), (118, 82, 48), (86, 58, 32)], 12, rise=6, size=(1.4, 2.8),
                     centre=(16, 22))


def wool_tufts(i, n):
    return particles(i, n, 71, 7, [(255, 255, 250), (236, 232, 222), (210, 204, 192)], 10, rise=5, size=(2, 3.2))


ANIMS = {"Puff": puff, "Slash": slash, "Fire_Burst": fire_burst, "Ice_Burst": ice_burst, "Spark": spark,
         "Heal_Glow": heal_glow, "Stone_Glow": stone_glow, "Teleport_Glow": teleport_glow,
         "Wood_Chips": wood_chips, "Rock_Chips": rock_chips, "Splash": splash, "Dirt_Clods": dirt_clods,
         "Wool_Tufts": wool_tufts}


# ------------------------------------------------------------------ missiles (16 x 16)
def missile(core, glow, dark, tail):
    img = K.new(16, 16)
    for k in range(5):                            # a short trail behind (to the left; the game doesn't rotate it)
        K.shaded_ellipse(img, 4 + k * 1.6, 8, 1 + k * 0.5, 1 + k * 0.5, tail, K.mix(tail, (255, 255, 255), 0.3), dark)
    K.shaded_ellipse(img, 10, 8, 4.5, 4.5, glow, core, dark)
    K.put(img, 9, 6, (255, 255, 255))
    return img


def ice_missile():
    img = K.new(16, 16)
    for y in range(16):
        for x in range(16):
            dx, dy = abs(x - 8) / 7.0, abs(y - 8) / 4.0
            if dx + dy <= 1:
                img[y][x] = (230, 248, 255) if y < 8 and x < 9 else (120, 196, 250) if dx + dy < 0.7 else (60, 130, 220)
    return K.outline_img(img, (20, 50, 110))


def arrow_missile():
    """An arrow in flight, pointing right (the game mirrors it when it flies left)."""
    img = K.new(16, 16)
    for x in range(1, 13):
        K.put(img, x, 8, (150, 104, 60))                    # the shaft
    for x, y in ((12, 7), (13, 7), (13, 8), (14, 8), (12, 9), (13, 9)):
        K.put(img, x, y, (200, 204, 214))                   # the head
    K.put(img, 15, 8, (150, 154, 164))
    for x, y in ((1, 6), (2, 7), (1, 10), (2, 9), (3, 6), (3, 10)):
        K.put(img, x, y, (236, 236, 236))                   # the feathers
    return img


def dragon_fire():
    """A big gout of dragon fire: a hot white core in an orange and red flame with a ragged tail."""
    img = K.new(16, 16)
    for k in range(6):
        K.shaded_ellipse(img, 2 + k * 1.4, 8 + (1 if k % 2 else -1) * 0.6, 1.2 + k * 0.45, 1.0 + k * 0.4,
                         (230, 70, 20), (255, 150, 40), (140, 20, 10))
    K.shaded_ellipse(img, 10.5, 8, 5, 5, (255, 140, 30), (255, 230, 120), (190, 40, 10))
    K.shaded_ellipse(img, 11, 7.5, 2.2, 2.2, (255, 250, 210), (255, 255, 255), (255, 210, 120))
    return img


MISSILES = {
    "Arrow_Missile": arrow_missile,
    "Dragon_Fire_Missile": dragon_fire,
    "Fire_Bolt_Missile": lambda: missile((255, 250, 200), (255, 170, 40), (190, 50, 10), (250, 110, 20)),
    "Ice_Bolt_Missile": ice_missile,
    "Lightning_Missile": lambda: missile((255, 255, 255), (250, 240, 120), (200, 170, 30), (240, 230, 150)),
}


# ------------------------------------------------------------------ the hurt flash
def screen_size():
    ini = Ini(p("Data", "Config.ini"))
    tx = int(float(ini.get("Interface", "Map.X.Tiles") or 25))
    ty = int(float(ini.get("Interface", "Map.Y.Tiles") or 21))
    w = read_bmp(p("Sprites", "Tiles", "Black001.png"))[0]
    return tx * w, ty * w


def hurt_strip(w, h, horizontal):
    """Red, dithered (so the map shows through), strongest at the outer edge."""
    img = K.new(w, h)
    depth = h if horizontal else w
    for y in range(h):
        for x in range(w):
            d = y if horizontal else x                 # 0 = the outer edge (the game mirrors it for the far side)
            keep = (depth - d) / float(depth)          # 1 at the edge -> 0 inside
            on = ((x + y) % 2 == 0) if keep < 0.7 else True
            if keep > 0.12 and on:
                img[y][x] = (230, 20, 20) if keep > 0.6 else (170, 10, 10)
    return img


# ------------------------------------------------------------------ main
def build():
    made = {}
    for kind in ("Hit", "Crit", "Heal"):
        for n in range(1, 100):
            made["%s%d" % (kind, n)] = splat(kind, n)
    made["Miss"] = splat("Miss", 0)
    for name, fn in ANIMS.items():
        for i, im in enumerate(frames(fn)):
            made["%s%d" % (name, i + 1)] = im
    for name, fn in MISSILES.items():
        made[name] = fn()
    w, h = screen_size()
    made["Hurt_Top"] = hurt_strip(w, 8, True)
    made["Hurt_Bottom"] = [list(r) for r in reversed(hurt_strip(w, 8, True))]
    made["Hurt_Left"] = hurt_strip(8, h, False)
    made["Hurt_Right"] = K.flip_h(hurt_strip(8, h, False))
    return made


def main():
    os.makedirs(p("Sprites", OUT), exist_ok=True)
    made = build()
    written = sum(1 for name, im in made.items() if K.save(OUT, name, im))
    stale = [f for f in os.listdir(p("Sprites", OUT)) if f.lower().endswith(".png") and f[:-4] not in made]
    for f in stale:
        os.remove(p("Sprites", OUT, f))
    print("%d effect sprites, %d written, %d stale removed" % (len(made), written, len(stale)))
    if "--preview" in sys.argv:
        show = ["Hit1", "Hit7", "Hit23", "Hit99", "Crit12", "Crit45", "Heal5", "Heal40", "Miss",
                "Fire_Bolt_Missile", "Ice_Bolt_Missile", "Lightning_Missile"]
        for name in ANIMS:
            show += ["%s%d" % (name, i) for i in range(1, 5)]
        K.sheet(p("Dev", "Renders", "Effects preview.png"), [made[s] for s in show], scale=3, cols=12)
        print("preview: Dev\\Renders\\Effects preview.png")


if __name__ == "__main__":
    main()
