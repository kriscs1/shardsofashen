"""The interface, redrawn: the original game's flat sidebar, panels, chat bar and boxes repainted as carved dark oak,
walnut panels with a gold inlay, tooled-leather wells and real parchment, and the Heart and Mana icons redrawn.

Run:  python -I "dev\\migrate\\build_gui.py"

Every sprite keeps its size, its mask and where everything is in it (the game's code knows where the minimap circle,
the close and scroll buttons, the panels and the equipment slots are), so this only changes how they're painted: each
pixel of the original is sorted into what it was (frame, panel, well, parchment, lettering, buttons, black) and that
region is painted afresh, with bevels lit from the top left worked out from the regions' edges. The originals are kept
in dev\\Archive\\Interface and are what each run starts from (so it can be run again, and undone by copying them back).
"""
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p, write_sprite, PLAIN  # noqa: E402

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

ARCHIVE = p("dev", "Archive", "Interface")
# sprite: has a mask (top half) over its picture (bottom half)
SPRITES = {"SideBar": True, "StatBox": False, "ChatBar": False, "InfoBox": False, "ResponseBox": False,
           "SideBarBorder": False, "AB_Conversation": True, "AB_Craft": True, "AB_Bank": True}
ICONS = ("Heart", "Mana")
DIGITS = "0123456789+"
BARS = ["%dPCHealth" % k for k in range(0, 101, 10)]
FONT = {   # 3 x 5 glyphs for the item counts
    "0": "111 101 101 101 111", "1": "010 110 010 010 111", "2": "111 001 111 100 111", "3": "111 001 011 001 111",
    "4": "101 101 111 001 001", "5": "111 100 111 001 111", "6": "111 100 111 101 111", "7": "111 001 010 010 010",
    "8": "111 101 111 101 111", "9": "111 101 111 001 111", "+": "000 010 111 010 000"}

FRAME, PANEL, WELL, PARCH, BLACK, KEEP, TEXT = range(7)
GOLD, GOLD_LIGHT, GOLD_DARK = np.array((204, 158, 70.0)), np.array((250, 220, 140.0)), np.array((120, 82, 30.0))


def noise(rng, h, w, blur, amp):
    n = rng.uniform(-1, 1, (h, w))
    for _ in range(blur):
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) / 5
    n /= max(1e-6, np.abs(n).max())
    return n * amp


def box_blur(a, r):
    out = a.astype(np.float64)
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, axis)
        out = acc / (2 * r + 1)
    return out


def classify(img):
    """img: h x w x 3 floats. -> h x w labels."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    lab = np.full(lum.shape, FRAME, dtype=np.int8)
    smooth = box_blur(lum, 3)
    lab[smooth < 46] = WELL                                           # the dark speckled wells
    flat = (np.abs(r - 118) < 14) & (np.abs(g - 72) < 14) & (np.abs(b - 56) < 14)
    flat_area = box_blur(flat.astype(float), 2) > 0.8
    lab[flat_area] = PANEL
    lab[(r > 150) & (g > 120) & (b > 70) & (r - b < 120)] = PARCH
    lab[(r < 6) & (g < 6) & (b < 6)] = BLACK
    sat = img.max(-1) - img.min(-1)
    green = (g > r + 50) & (g > b + 50)
    lab[green] = TEXT                                                 # the old green lettering
    other = (sat > 90) & ~green & (lab != PARCH)                      # buttons and icons: kept as they are
    grey = (sat < 18) & (lum > 40) & (lum < 140) & (lab != PANEL)     # the stone equipment slots
    lab[other | grey] = KEEP
    return lab


def distance_in(mask, n):
    """For each pixel of mask, how far (up to n) it is from the edge of its region (1 = on the edge)."""
    d = np.zeros(mask.shape, dtype=np.int8)
    cur = mask.copy()
    for k in range(1, n + 1):
        inner = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
        d[cur & ~inner] = k
        cur = inner
    d[cur] = n + 1
    return d


def edge_light(mask):
    """+1 where the region's edge faces up/left (lit), -1 where it faces down/right (shade), per pixel near it."""
    up = mask & ~np.roll(mask, 1, 0)
    left = mask & ~np.roll(mask, 1, 1)
    down = mask & ~np.roll(mask, -1, 0)
    right = mask & ~np.roll(mask, -1, 1)
    return up.astype(float) + left - down - right


def shifted(m, n, axis):
    """m moved n pixels along axis, what comes in from the edge False (np.roll wraps round: a region touching the
    top would have an edge at the bottom)."""
    out = np.zeros_like(m)
    if axis == 0:
        if n > 0:
            out[n:] = m[:-n]
        else:
            out[:n] = m[-n:]
    else:
        if n > 0:
            out[:, n:] = m[:, :-n]
        else:
            out[:, :n] = m[:, -n:]
    return out


def paint(img, seed):
    h, w, _ = img.shape
    rng = np.random.default_rng(seed)
    lab = classify(img)
    out = img.copy()
    ys, xs = np.mgrid[0:h, 0:w]

    # --- the frame: dark oak, grain running along the longer side, a raised bevel
    along = xs if w >= h else ys
    across = ys if w >= h else xs
    warp = noise(rng, h, w, 6, 2.2) + np.sin(along * 0.035) * 1.2
    grain = np.sin(across * 1.7 + warp) * 0.5 + 0.5
    grain = grain ** 1.6                                              # thin dark lines in lighter wood
    oak = np.stack([62 + 34 * grain, 36 + 19 * grain, 24 + 11 * grain], -1)
    streak = noise(rng, h, w, 0, 1)
    oak *= (1 + 0.06 * streak)[..., None]
    m = lab == FRAME
    out[m] = oak[m]
    # --- the panels: warm walnut boards, finer grain
    board = (across // 22) % 3
    g2 = np.sin(across * 0.55 + noise(rng, h, w, 6, 2.5) + board * 2.1 + np.sin(along * 0.05) * 0.8) * 0.5 + 0.5
    walnut = np.stack([118 + 26 * g2 - board * 7, 74 + 16 * g2 - board * 5, 46 + 9 * g2 - board * 3], -1)
    walnut *= (1 + noise(rng, h, w, 0, 0.035))[..., None]
    seam = (across % 22) == 0                                         # the joins between the boards
    walnut[seam] *= 0.62
    walnut[(across % 22) == 1] *= 1.12
    m = lab == PANEL
    out[m] = walnut[m]
    # --- the wells: dark tooled leather, sunk in (shadow along the top and left inside, light along the bottom)
    leather = np.stack([44 + np.zeros((h, w)), 29 + np.zeros((h, w)), 22 + np.zeros((h, w))], -1)
    leather *= (1 + noise(rng, h, w, 1, 0.14))[..., None]
    m = lab == WELL
    out[m] = leather[m]
    d = distance_in(m, 6)
    tooled = m & (d == 4)                                              # a tooled line round the inside
    out[tooled] *= 0.7
    out[tooled & np.roll(tooled, 1, 0)] *= 1.0
    # --- the parchment: fibres, blotches, darker towards its edges
    m = lab == PARCH
    fib = noise(rng, h, w, 0, 1) * 0.5 + noise(rng, h, w, 3, 1)
    parch = np.stack([222 + 14 * fib, 202 + 12 * fib, 156 + 10 * fib], -1)
    dp = distance_in(m, 10).astype(float)
    edge_dark = np.clip(1 - (10 - dp) * 0.035, 0.68, 1)[..., None]
    out[m] = (parch * edge_dark)[m]
    # --- the lettering: engraved gold, dark outline
    m = lab == TEXT
    if m.any():
        rows = np.where(m.any(1))[0]
        t = np.clip((ys - rows.min()) / max(1, rows.max() - rows.min()), 0, 1)[..., None]
        gold = GOLD_LIGHT * (1 - t) + GOLD_DARK * t
        out[m] = gold[m]
        ring = (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)) & ~m & (lab != KEEP)
        out[ring] = (40, 22, 12)
    # --- the old bright yellow buttons (the minimap's - and +): gold, shaded by how bright they were
    yellow = (lab == KEEP) & (img[..., 0] > 170) & (img[..., 1] > 170) & (img[..., 2] < 110)
    if yellow.any():
        k = (img[..., 0] + img[..., 1]) / 510.0
        out[yellow] = (GOLD_DARK + (GOLD_LIGHT - GOLD_DARK) * k[..., None])[yellow]
    # --- bevels: raised frame and panels, sunk wells and parchment
    for cls, depth, k in ((FRAME, 3, 0.22), (PANEL, 2, 0.16), (WELL, 3, -0.3), (PARCH, 3, -0.2)):
        m = lab == cls
        light = np.zeros((h, w))
        cur = m.copy()
        for step in range(depth):
            light += edge_light(cur) * (1 - step / depth)
            cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
        out[m] *= (1 + k * light)[m][:, None]
    # --- the gold inlay: a line round every well and parchment, on the wood side
    for cls in (WELL, PARCH):
        m = lab == cls
        near = (shifted(m, 1, 0) | shifted(m, -1, 0) | shifted(m, 1, 1) | shifted(m, -1, 1)) & ~m
        inlay = near & np.isin(lab, (FRAME, PANEL))
        lit = (shifted(m, -1, 0) | shifted(m, -1, 1))                  # the inlay above/left of the well: lit
        out[inlay] = GOLD
        out[inlay & lit] = GOLD_LIGHT * 0.85 + GOLD * 0.15
        out[inlay & ~lit] = GOLD * 0.75 + GOLD_DARK * 0.25
    return np.clip(out, 0, 255)


# ------------------------------------------------------------------------------------------- icons
def icon_heart():
    ys, xs = np.mgrid[0:32, 0:32] + 0.5
    x, y = (xs - 16) / 13.0, (17.5 - ys) / 13.0
    inside = (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0
    img = np.zeros((32, 32, 3))
    shade = np.clip(1.25 - 0.9 * ((xs - 11) ** 2 + (ys - 10) ** 2) ** 0.5 / 20, 0.45, 1.25)
    img[...] = np.array((200, 30, 40.0))[None, None] * shade[..., None]
    shine = ((xs - 11) / 4.0) ** 2 + ((ys - 10) / 2.6) ** 2 <= 1
    img[shine & inside] = (255, 190, 190)
    return img, inside


def icon_mana():
    ys, xs = np.mgrid[0:32, 0:32] + 0.5
    # a drop: a circle below with a point above
    body = ((xs - 16) / 9.5) ** 2 + ((ys - 20) / 9.5) ** 2 <= 1
    tip = (ys >= 3) & (ys <= 20) & (np.abs(xs - 16) <= (ys - 3) * 0.56)
    inside = body | tip
    img = np.zeros((32, 32, 3))
    shade = np.clip(1.3 - ((xs - 12) ** 2 + (ys - 16) ** 2) ** 0.5 / 18, 0.5, 1.3)
    img[...] = np.array((50, 110, 230.0))[None, None] * shade[..., None]
    swirl = (np.abs(((xs - 16) ** 2 + (ys - 20) ** 2) ** 0.5 - 5.5) < 0.9) & (xs > 16)
    img[swirl & inside] = (170, 210, 255)
    img[(((xs - 12.5) / 2.2) ** 2 + ((ys - 17) / 3.2) ** 2 <= 1) & inside] = (225, 240, 255)
    return img, inside


def digit(ch):
    """InterfaceNumber<ch>: a 3 x 5 glyph, cream fading to gold, in a dark outline (5 x 7)."""
    rows = FONT[ch].split()
    glyph = np.zeros((7, 5), dtype=bool)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            glyph[y + 1, x + 1] = c == "1"
    img = np.zeros((7, 5, 3))
    for y in range(7):
        t = (y - 1) / 4.0
        img[y] = np.array((255, 244, 206.0)) * (1 - t) + np.array((228, 184, 100.0)) * t
    ring = np.zeros_like(glyph)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ring |= np.roll(np.roll(glyph, dy, 0), dx, 1)
    ring &= ~glyph
    img[ring] = (28, 16, 10)
    return img, glyph | ring


def health_bar(percent):
    """<n>PCHealth: 26 x 6, a dark outline with rounded ends, the filled part green / amber / red by how much is
    left, lighter along its top, and the empty part a dark track."""
    w, h = 26, 6
    inside = np.ones((h, w), dtype=bool)
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        inside[y, x] = False
    img = np.zeros((h, w, 3))
    img[...] = (24, 14, 10)
    fill = int(round(24 * percent / 100.0))
    col = np.array((70, 196, 70.0)) if percent > 50 else (np.array((232, 168, 40.0)) if percent > 20 else np.array((214, 52, 40.0)))
    for y in range(1, h - 1):
        k = {1: 1.3, 2: 1.0, 3: 0.85, 4: 0.65}[y]
        img[y, 1:1 + fill] = np.clip(col * k, 0, 255)
        img[y, 1 + fill:w - 1] = np.array((62, 30, 26.0)) * (1.15 if y == 1 else 0.9)
    if 0 < fill < 24:
        img[1:h - 1, fill] *= 1.15                                    # the bright leading edge
    return img, inside


def outlined(img, inside):
    ring = (np.roll(inside, 1, 0) | np.roll(inside, -1, 0) | np.roll(inside, 1, 1) | np.roll(inside, -1, 1)) & ~inside
    img = img.copy()
    img[ring] = (36, 14, 14)
    return img, inside | ring


# ------------------------------------------------------------------------------------------- files
def to_array(surf):
    return pygame.surfarray.array3d(surf).transpose(1, 0, 2).astype(np.float64)


def to_surface(arr):
    return pygame.surfarray.make_surface(np.clip(arr, 0, 255).astype(np.uint8).transpose(1, 0, 2))


def save_if_changed(surf, path):
    """Writes the picture (in the mask layout, or plain: common.PLAIN) as a PNG, only if it changed."""
    arr = pygame.surfarray.array3d(surf).transpose(1, 0, 2)
    rows = [[tuple(int(v) for v in c) for c in r] for r in arr]
    name = os.path.splitext(os.path.basename(path))[0]
    return write_sprite(path, rows, plain=name in PLAIN)


def main():
    os.makedirs(ARCHIVE, exist_ok=True)
    for name in list(SPRITES) + list(ICONS) + ["InterfaceNumber" + c for c in DIGITS] + BARS:   # keep the originals
        src, keep = p("sprites", "Interface", name + ".bmp"), os.path.join(ARCHIVE, name + ".bmp")
        if not os.path.exists(keep):
            shutil.copyfile(src, keep)
    for k, (name, masked) in enumerate(SPRITES.items()):
        surf = pygame.image.load(os.path.join(ARCHIVE, name + ".bmp"))
        arr = to_array(surf)
        if masked:
            h = arr.shape[0] // 2
            mask, pic = arr[:h], arr[h:]
            drawn = mask.sum(-1) < 384
            if name == "SideBar":
                # the old hover-text box at the bottom: the chat bar's own box covers it from y 672, so the strip of
                # it above showed as a line through the hover text. Plain panel there instead.
                pic = pic.copy()
                pic[650:, 20:205] = (118, 72, 56)
            new = paint(pic, 1000 + k)
            new[~drawn] = pic[~drawn]                  # (hidden pixels left alone)
            arr = np.concatenate([mask, new], 0)
        else:
            arr = paint(arr, 1000 + k)
        print(("wrote " if save_if_changed(to_surface(arr), p("sprites", "Interface", name + ".png")) else "unchanged ") + name)
    small = [("InterfaceNumber" + c, (lambda c=c: digit(c)), False) for c in DIGITS] +             [("%dPCHealth" % k, (lambda k=k: health_bar(k)), False) for k in range(0, 101, 10)]
    for name, make, ring in [("Heart", icon_heart, True), ("Mana", icon_mana, True)] + small:
        img, inside = outlined(*make()) if ring else make()
        mask = np.where(inside[..., None], 0.0, 255.0) * np.ones((1, 1, 3))
        pic = np.where(inside[..., None], img, 0.0)
        print(("wrote " if save_if_changed(to_surface(np.concatenate([mask, pic], 0)),
                                           p("sprites", "Interface", name + ".png")) else "unchanged ") + name)


if __name__ == "__main__":
    pygame.init()
    main()
