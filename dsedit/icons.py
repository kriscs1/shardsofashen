"""The tool buttons' icons, drawn here (no image files): a pencil (Paint), a paint pot (Fill), a dashed box
(Rectangle), four arrows (Move), an eraser (Erase), an eyedropper (Pick), a pointer (Select), a plus (Place).
Drawn four times over and shrunk, so they're smooth at any display scaling; in any colour (a button's text colour,
so they turn white with it when chosen)."""
from PIL import Image, ImageDraw, ImageTk

from . import theme as T

BIG = 64                    # (drawn on a 64 x 64 canvas, then shrunk)
_cache = {}


def _pencil(d, c):
    d.polygon([(12, 44), (40, 16), (48, 24), (20, 52)], outline=c, width=5)
    d.polygon([(12, 44), (20, 52), (8, 56)], fill=c)                  # (the point)
    d.line([(36, 20), (44, 28)], fill=c, width=5)                     # (where the wood meets the end)


def _fill(d, c):
    d.polygon([(10, 30), (30, 10), (52, 32), (32, 52)], outline=c, width=5)      # (the pot, tipped)
    d.line([(10, 30), (52, 32)], fill=c, width=5)
    d.ellipse([(46, 40), (58, 56)], fill=c)                           # (a drop of paint)


def _rect(d, c):
    for x0, y0, x1, y1 in ((8, 12, 56, 12), (8, 52, 56, 52), (8, 12, 8, 52), (56, 12, 56, 52)):
        n = 6                                                         # (dashed)
        for k in range(n):
            if k % 2 == 0:
                a, b = k / n, (k + 1) / n
                d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                       fill=c, width=5)


def _move(d, c):
    d.line([(32, 8), (32, 56)], fill=c, width=5)
    d.line([(8, 32), (56, 32)], fill=c, width=5)
    for tip, l, r in (((32, 4), (22, 16), (42, 16)), ((32, 60), (22, 48), (42, 48)),
                      ((4, 32), (16, 22), (16, 42)), ((60, 32), (48, 22), (48, 42))):
        d.polygon([tip, l, r], fill=c)


def _erase(d, c):
    d.polygon([(8, 40), (32, 16), (52, 36), (28, 60)], outline=c, width=5)
    d.polygon([(8, 40), (20, 28), (40, 48), (28, 60)], fill=c)         # (the rubber end)
    d.line([(30, 58), (58, 58)], fill=c, width=4)


def _pick(d, c):
    d.line([(14, 50), (38, 26)], fill=c, width=7)                     # (the glass)
    d.ellipse([(36, 8), (56, 28)], fill=c)                            # (the bulb)
    d.line([(10, 54), (14, 50)], fill=c, width=4)                     # (the tip)


def _select(d, c):
    d.polygon([(14, 6), (14, 50), (25, 40), (33, 58), (41, 54), (33, 37), (48, 37)], fill=c)


def _area(d, c):
    for x0, y0, x1, y1 in ((10, 10, 54, 10), (10, 54, 54, 54), (10, 10, 10, 54), (54, 10, 54, 54)):
        n = 8                                                         # (a marching-ants frame...)
        for k in range(0, n, 2):
            a, b = k / n, (k + 1) / n
            d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                   fill=c, width=4)
    for x, y in ((10, 10), (54, 10), (10, 54), (54, 54)):            # (...with a handle at each corner)
        d.rectangle([x - 6, y - 6, x + 6, y + 6], fill=c)


def _place(d, c):
    d.line([(32, 10), (32, 54)], fill=c, width=8)
    d.line([(10, 32), (54, 32)], fill=c, width=8)


DRAW = {"Paint": _pencil, "Fill": _fill, "Rectangle": _rect, "Move": _move, "Erase": _erase, "Pick": _pick,
        "Select": _select, "Place": _place, "Area": _area}


def icon(name, colour):
    """The tool's icon in this colour (a PhotoImage, kept), or None for a tool with none."""
    if name not in DRAW:
        return None
    size = max(12, T.px(16))
    key = (name, colour, size)
    if key not in _cache:
        img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
        DRAW[name](ImageDraw.Draw(img), colour)
        _cache[key] = ImageTk.PhotoImage(img.resize((size, size), Image.LANCZOS))
    return _cache[key]
