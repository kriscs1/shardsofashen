"""More to look at indoors (the owner's wish: picture frames, cupboards, desks...).

  * Pictures: on the wall, walked past: framed paintings (hills, the sea, a portrait, flowers, the mountains, a dragon),
    a mirror, tapestries, coat pegs, a wall shelf, antlers. Furniture: stands against the wall, solid: cupboards, a
    wardrobe, a dresser, writing desks, a side table, a washstand, a long clock. Each a decor tile, with the 1 px dark
    outline (build_wolf.py's way).
  * Put about the houses: every room with a roof over it, and every room upstairs, gets some against its back wall by
    its size and by what it is (a home, a shop, a tavern, a study, a hall; a smithy only a shelf or pegs; a chapel a
    tapestry; a barn or a coop nothing): never by a door or a stair, where a thing or a person stands, or where a script puts someone,
    and a room's floor stays all one (a piece that would shut part of it off is left out).
  * The side walls too, seen side on (Side_*_W against a west wall, _E the same mirrored for an east one): a
    painting squeezed narrow along the wall, a mirror, a tapestry, a shelf end on, a cloak on a peg, a candle in a
    sconce; and standing, a cupboard, a bookcase, a dresser, a bench, a desk. Never where you couldn't get past.
  * Redrock Manor has its own furniture (build_manors.py) and is left alone.

Safe to run again (a room that has any of these already is left as it is).

  python -I "dev\\migrate\\build_interiors.py"
"""
import glob
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "estforlan"))
from common import Ini, p, read_lines, write_image, write_lines          # noqa: E402
import world_edit as W                           # noqa: E402
from house_tiles import THIN_EDGES               # noqa: E402
from world_edit import XT, YT                    # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

S = 32
OUTLINE = (34, 26, 20, 255)
OAK, DARK, PINE = (122, 82, 48), (84, 54, 34), (158, 114, 66)
GOLD, BROWN = (196, 156, 66), (104, 70, 40)


def tone(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


def blank():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def outlined(im):
    a = im.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ring = Image.new("RGBA", im.size, OUTLINE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.paste(ring, (dx, dy), a)
    out.alpha_composite(im)
    return out


def wood(d, x0, y0, x1, y1, col):
    """A block of wood, lit along its top and left, shaded along its bottom, with a grain to it."""
    d.rectangle((x0, y0, x1, y1), fill=tone(col, 1))
    for y in range(y0 + 2, y1, 3):
        d.line((x0 + 1, y, x1 - 1, y), fill=tone(col, 0.9))
    d.line((x0, y0, x1, y0), fill=tone(col, 1.25))
    d.line((x0, y0, x0, y1), fill=tone(col, 1.12))
    d.line((x0, y1, x1, y1), fill=tone(col, 0.68))
    d.line((x1, y0, x1, y1), fill=tone(col, 0.78))


# ----- paintings: a canvas in a frame, hung high on the wall
def frame(w, h, col, paint):
    im, d = blank()
    x0, y0 = (S - w) // 2, 1
    x1, y1 = x0 + w - 1, y0 + h - 1
    d.rectangle((x0, y0, x1, y1), fill=tone(col, 1))
    d.line((x0, y0, x1, y0), fill=tone(col, 1.3))
    d.line((x0, y0, x0, y1), fill=tone(col, 1.15))
    d.line((x0, y1, x1, y1), fill=tone(col, 0.65))
    d.line((x1, y0, x1, y1), fill=tone(col, 0.75))
    paint(d, x0 + 2, y0 + 2, x1 - 2, y1 - 2)
    return outlined(im)


def hills(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(150, 196, 226, 255))
    d.rectangle((x0, y0 + (y1 - y0) // 2, x1, y1), fill=(92, 140, 66, 255))
    d.polygon([(x0, y0 + 4), (x0 + 5, y0 + 2), (x0 + 10, y0 + 5), (x0, y0 + 6)], fill=(70, 116, 54, 255))
    d.point((x1 - 3, y0 + 1), fill=(250, 232, 150, 255))


def sea(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(176, 206, 224, 255))
    d.rectangle((x0, y0 + 4, x1, y1), fill=(44, 90, 150, 255))
    mid = (x0 + x1) // 2
    d.line((mid, y0, mid, y0 + 4), fill=(70, 50, 34, 255))
    d.polygon([(mid + 1, y0), (mid + 4, y0 + 3), (mid + 1, y0 + 3)], fill=(240, 236, 224, 255))
    d.line((mid - 3, y0 + 5, mid + 3, y0 + 5), fill=(70, 50, 34, 255))


def portrait(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(58, 48, 62, 255))
    mid = (x0 + x1) // 2
    d.rectangle((mid - 3, y1 - 3, mid + 3, y1), fill=(116, 36, 40, 255))
    d.ellipse((mid - 2, y0 + 2, mid + 2, y0 + 6), fill=(226, 190, 156, 255))
    d.line((mid - 2, y0 + 2, mid + 2, y0 + 2), fill=(60, 40, 28, 255))


def flowers(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(88, 72, 58, 255))
    mid = (x0 + x1) // 2
    d.rectangle((mid - 1, y1 - 3, mid + 1, y1), fill=(170, 176, 196, 255))
    for i, j, c in ((-3, 2, (214, 70, 70)), (0, 1, (240, 214, 90)), (3, 2, (214, 120, 170)), (-1, 3, (230, 230, 220)),
                    (2, 4, (214, 70, 70))):
        d.point((mid + i, y0 + j), fill=c + (255,))


def peaks(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(186, 200, 216, 255))
    d.polygon([(x0, y1), (x0 + 4, y0 + 1), (x0 + 8, y1)], fill=(110, 112, 128, 255))
    d.polygon([(x0 + 5, y1), (x0 + 9, y0 + 2), (x1, y1)], fill=(90, 92, 110, 255))
    d.point([(x0 + 4, y0 + 1), (x0 + 9, y0 + 2)], fill=(250, 250, 250, 255))


def dragon(d, x0, y0, x1, y1):
    d.rectangle((x0, y0, x1, y1), fill=(70, 34, 30, 255))
    mid = (x0 + x1) // 2
    d.polygon([(mid - 5, y1 - 1), (mid, y0 + 2), (mid + 5, y1 - 1), (mid, y1 - 3)], fill=(180, 52, 36, 255))
    d.point((mid, y0 + 1), fill=(240, 180, 70, 255))


# ----- on the wall
def mirror():
    im, d = blank()
    d.ellipse((10, 1, 21, 16), fill=tone(GOLD, 1))
    d.ellipse((12, 3, 19, 14), fill=(178, 208, 220, 255))
    d.line((14, 5, 16, 9), fill=(232, 244, 248, 255))
    return outlined(im)


def tapestry(col, trim, motif):
    im, d = blank()
    d.line((7, 1, 24, 1), fill=tone(BROWN, 1))
    d.rectangle((9, 2, 22, 21), fill=tone(col, 1))
    d.rectangle((10, 3, 21, 20), outline=tone(trim, 1))
    for x in range(10, 22, 2):                           # (a fringe)
        d.line((x, 22, x, 23), fill=tone(trim, 1))
    motif(d, trim)
    return outlined(im)


def sword_motif(d, trim):
    d.line((15, 6, 15, 17), fill=tone(trim, 1))
    d.line((16, 6, 16, 17), fill=tone(trim, 1))
    d.line((12, 13, 19, 13), fill=tone(trim, 1))


def tree_motif(d, trim):
    d.line((15, 12, 15, 18), fill=tone(trim, 0.8))
    d.ellipse((11, 5, 20, 13), fill=tone(trim, 1))


def coat_pegs():
    im, d = blank()
    wood(d, 6, 3, 25, 5, OAK)
    d.rectangle((9, 6, 14, 18), fill=(70, 86, 110, 255))     # (a cloak)
    d.line((9, 6, 9, 18), fill=(92, 110, 136, 255))
    d.rectangle((19, 6, 22, 10), fill=(120, 60, 44, 255))    # (and a hat)
    d.line((17, 10, 24, 10), fill=(92, 46, 34, 255))
    return outlined(im)


def wall_shelf():
    im, d = blank()
    wood(d, 5, 12, 26, 14, OAK)
    d.rectangle((8, 7, 11, 11), fill=(170, 112, 70, 255))    # (a pot)
    d.line((8, 7, 11, 7), fill=(204, 146, 96, 255))
    d.rectangle((14, 8, 17, 11), fill=(120, 136, 150, 255))  # (a jar)
    d.rectangle((20, 5, 23, 11), fill=(120, 50, 44, 255))    # (a book or two, on end)
    d.line((22, 5, 22, 11), fill=(60, 86, 110, 255))
    return outlined(im)


def antlers():
    im, d = blank()
    bone = (214, 200, 170, 255)
    d.rectangle((13, 9, 18, 14), fill=tone(BROWN, 1))
    for sx in (-1, 1):
        d.line((15.5 + sx * 2, 9, 15.5 + sx * 8, 3), fill=bone)
        d.line((15.5 + sx * 5, 6, 15.5 + sx * 5, 2), fill=bone)
        d.line((15.5 + sx * 7, 4, 15.5 + sx * 10, 5), fill=bone)
    return outlined(im)


# ----- against the wall
def cupboard(col):
    im, d = blank()
    wood(d, 5, 2, 26, 29, col)
    d.rectangle((7, 5, 15, 26), outline=tone(col, 0.7))
    d.rectangle((16, 5, 24, 26), outline=tone(col, 0.7))
    d.point([(14, 15), (17, 15)], fill=tone(GOLD, 1))
    d.line((4, 2, 27, 2), fill=tone(col, 1.3))
    return outlined(im)


def wardrobe():
    im, d = blank()
    wood(d, 3, 1, 28, 29, DARK)
    d.rectangle((5, 4, 15, 27), outline=tone(DARK, 0.65))
    d.rectangle((16, 4, 26, 27), outline=tone(DARK, 0.65))
    d.rectangle((7, 7, 13, 15), fill=tone(DARK, 1.2))
    d.rectangle((18, 7, 24, 15), fill=tone(DARK, 1.2))
    d.point([(14, 17), (17, 17)], fill=tone(GOLD, 1))
    return outlined(im)


def dresser():
    im, d = blank()
    wood(d, 4, 12, 27, 29, OAK)
    for y in (14, 19, 24):
        d.rectangle((6, y, 25, y + 3), outline=tone(OAK, 0.7))
        d.point([(11, y + 2), (20, y + 2)], fill=tone(GOLD, 1))
    d.rectangle((9, 6, 13, 11), fill=(190, 196, 210, 255))   # (a jug on it)
    d.line((14, 7, 14, 9), fill=(150, 156, 170, 255))
    d.rectangle((19, 9, 24, 11), fill=(120, 50, 44, 255))    # (a little box)
    return outlined(im)


def writing_desk(col, n):
    im, d = blank()
    wood(d, 3, 13, 28, 18, col)
    wood(d, 4, 19, 9, 29, col)
    wood(d, 22, 19, 27, 29, col)
    d.rectangle((11, 19, 20, 22), fill=tone(col, 0.8))       # (a drawer)
    d.point((15, 20), fill=tone(GOLD, 1))
    d.rectangle((7, 9, 14, 13), fill=(232, 226, 204, 255))   # (papers)
    d.line((8, 10, 13, 10), fill=(120, 110, 96, 255))
    if n == 1:
        d.line((19, 6, 22, 13), fill=(240, 240, 236, 255))   # (a quill in its pot)
        d.rectangle((20, 10, 23, 13), fill=(40, 40, 60, 255))
    else:
        d.rectangle((18, 9, 25, 13), fill=(110, 46, 40, 255))    # (a ledger)
        d.line((18, 11, 25, 11), fill=(216, 206, 176, 255))
    return outlined(im)


def side_table():
    im, d = blank()
    wood(d, 8, 15, 23, 18, OAK)
    d.line((11, 19, 11, 29), fill=tone(OAK, 0.8), width=2)
    d.line((20, 19, 20, 29), fill=tone(OAK, 0.8), width=2)
    d.rectangle((14, 10, 17, 14), fill=(232, 224, 196, 255))     # (a candle)
    d.point((15, 8), fill=(250, 200, 90, 255))
    d.point((15, 9), fill=(250, 170, 70, 255))
    return outlined(im)


def washstand():
    im, d = blank()
    wood(d, 6, 14, 25, 29, PINE)
    d.rectangle((8, 19, 23, 27), outline=tone(PINE, 0.7))
    d.ellipse((9, 9, 22, 15), fill=(206, 212, 222, 255))     # (a basin)
    d.ellipse((11, 10, 20, 13), fill=(120, 166, 196, 255))
    d.rectangle((23, 8, 26, 14), fill=(190, 196, 210, 255))  # (and its jug)
    return outlined(im)


def long_clock():
    im, d = blank()
    wood(d, 10, 1, 21, 29, DARK)
    d.ellipse((11, 3, 20, 12), fill=(232, 226, 204, 255))    # (its face)
    d.line((15, 8, 15, 5), fill=(30, 26, 22, 255))
    d.line((15, 8, 18, 8), fill=(30, 26, 22, 255))
    d.rectangle((13, 14, 18, 26), fill=tone(DARK, 0.6))      # (its pendulum, behind glass)
    d.line((15, 14, 15, 22), fill=tone(GOLD, 1))
    d.ellipse((14, 21, 17, 24), fill=tone(GOLD, 1))
    return outlined(im)


# ----- on the side walls, seen side on: drawn against the west wall (its strip is the tile's first 9 pixels), and
# mirrored for the east
EDGE = 9


def side_picture(col, a, b):
    """A painting seen along the wall: squeezed narrow, its far edge a little shorter."""
    im, d = blank()
    x0, x1 = EDGE, EDGE + 5
    d.polygon([(x0, 5), (x1, 7), (x1, 19), (x0, 21)], fill=tone(col, 1))
    d.polygon([(x0 + 1, 7), (x1 - 1, 8), (x1 - 1, 18), (x0 + 1, 19)], fill=tone(a, 1))
    d.polygon([(x0 + 1, 13), (x1 - 1, 13), (x1 - 1, 18), (x0 + 1, 19)], fill=tone(b, 1))
    d.line((x1, 7, x1, 19), fill=tone(col, 1.25))
    return outlined(im)


def side_mirror():
    im, d = blank()
    d.ellipse((EDGE, 4, EDGE + 5, 20), fill=tone(GOLD, 1))
    d.ellipse((EDGE + 1, 6, EDGE + 4, 18), fill=(178, 208, 220, 255))
    d.line((EDGE + 2, 8, EDGE + 2, 12), fill=(232, 244, 248, 255))
    return outlined(im)


def side_tapestry():
    im, d = blank()
    x0, x1 = EDGE, EDGE + 4
    d.rectangle((x0, 3, x1, 23), fill=(128, 40, 44, 255))
    d.line((x1, 3, x1, 23), fill=(216, 176, 86, 255))
    d.line((x0, 3, x1 + 1, 3), fill=tone(BROWN, 1))
    for y in (8, 13, 18):
        d.line((x0, y, x1 - 1, y), fill=(216, 176, 86, 255))
    d.point([(x0 + 1, 24), (x0 + 3, 24)], fill=(216, 176, 86, 255))
    return outlined(im)


def side_shelf():
    """A shelf running out from the wall, end on, its pots on top."""
    im, d = blank()
    wood(d, EDGE, 15, EDGE + 12, 17, OAK)
    d.line((EDGE, 18, EDGE + 4, 21), fill=tone(OAK, 0.7))    # (its bracket)
    d.rectangle((EDGE + 1, 10, EDGE + 4, 14), fill=(170, 112, 70, 255))
    d.line((EDGE + 1, 10, EDGE + 4, 10), fill=(204, 146, 96, 255))
    d.rectangle((EDGE + 7, 11, EDGE + 10, 14), fill=(120, 136, 150, 255))
    return outlined(im)


def side_pegs():
    im, d = blank()
    wood(d, EDGE, 6, EDGE + 2, 8, OAK)
    d.rectangle((EDGE + 1, 9, EDGE + 7, 25), fill=(70, 86, 110, 255))   # (a cloak hung on it)
    d.line((EDGE + 7, 9, EDGE + 7, 25), fill=(92, 110, 136, 255))
    d.line((EDGE + 1, 25, EDGE + 7, 25), fill=(50, 62, 82, 255))
    return outlined(im)


def side_sconce():
    im, d = blank()
    d.line((EDGE, 15, EDGE + 4, 15), fill=(70, 62, 56, 255))     # (its iron arm)
    d.line((EDGE, 16, EDGE + 2, 18), fill=(70, 62, 56, 255))
    d.rectangle((EDGE + 3, 9, EDGE + 5, 14), fill=(232, 224, 196, 255))
    d.point((EDGE + 4, 7), fill=(250, 200, 90, 255))
    d.point((EDGE + 4, 8), fill=(250, 170, 70, 255))
    return outlined(im)


def side_cupboard():
    """Its end against the room: a plain side, and the edge of its doors at the front."""
    im, d = blank()
    wood(d, EDGE, 3, EDGE + 14, 29, OAK)
    d.rectangle((EDGE + 2, 6, EDGE + 11, 26), outline=tone(OAK, 0.75))
    d.rectangle((EDGE + 13, 4, EDGE + 14, 28), fill=tone(OAK, 1.2))
    return outlined(im)


def side_bookcase():
    """Its end, and the books' edges showing past it."""
    im, d = blank()
    wood(d, EDGE, 2, EDGE + 11, 29, DARK)
    for y0 in (5, 13, 21):
        for i, c in enumerate(((120, 50, 44), (60, 86, 110), (176, 150, 90), (70, 104, 66), (120, 50, 44), (60, 86, 110))):
            d.line((EDGE + 8, y0 + i, EDGE + 10, y0 + i), fill=c + (255,))
    return outlined(im)


def side_dresser():
    im, d = blank()
    wood(d, EDGE, 14, EDGE + 14, 29, OAK)
    d.rectangle((EDGE + 2, 17, EDGE + 11, 26), outline=tone(OAK, 0.75))
    d.rectangle((EDGE + 13, 15, EDGE + 14, 28), fill=tone(OAK, 1.2))
    d.rectangle((EDGE + 4, 8, EDGE + 8, 13), fill=(190, 196, 210, 255))   # (a jug on it)
    d.line((EDGE + 9, 9, EDGE + 9, 11), fill=(150, 156, 170, 255))
    return outlined(im)


def side_bench():
    """A bench along the wall: its long seat, and its near end."""
    im, d = blank()
    wood(d, EDGE, 3, EDGE + 9, 23, PINE)
    wood(d, EDGE, 24, EDGE + 9, 29, tuple(int(v * 0.72) for v in PINE))
    return outlined(im)


def side_desk():
    """A desk along the wall: its top, papers and a pot of ink on it, and its near end."""
    im, d = blank()
    wood(d, EDGE, 4, EDGE + 14, 22, OAK)
    wood(d, EDGE, 23, EDGE + 14, 29, tuple(int(v * 0.72) for v in OAK))
    d.rectangle((EDGE + 3, 7, EDGE + 10, 14), fill=(232, 226, 204, 255))
    d.line((EDGE + 4, 9, EDGE + 9, 9), fill=(120, 110, 96, 255))
    d.line((EDGE + 4, 11, EDGE + 9, 11), fill=(120, 110, 96, 255))
    d.rectangle((EDGE + 5, 17, EDGE + 8, 20), fill=(40, 40, 60, 255))
    d.line((EDGE + 7, 14, EDGE + 10, 18), fill=(240, 240, 236, 255))
    return outlined(im)


SIDE_HUNG = {   # (the west wall's; _E the east's, mirrored)
    "Side_Picture_W001": (lambda: side_picture(GOLD, (150, 196, 226), (92, 140, 66)), "A painting of green hills."),
    "Side_Picture_W002": (lambda: side_picture(BROWN, (176, 206, 224), (44, 90, 150)), "A painting of the sea."),
    "Side_Picture_W003": (lambda: side_picture(GOLD, (58, 48, 62), (116, 36, 40)), "A dark portrait of someone important."),
    "Side_Mirror_W001": (side_mirror, "A mirror on the wall."),
    "Side_Tapestry_W001": (side_tapestry, "A tapestry hanging along the wall."),
    "Side_Shelf_W001": (side_shelf, "A shelf of pots and jars."),
    "Side_Pegs_W001": (side_pegs, "A cloak hung on a peg."),
    "Side_Sconce_W001": (side_sconce, "A candle in an iron sconce."),
}
SIDE_STANDING = {
    "Side_Cupboard_W001": (side_cupboard, "A cupboard against the wall."),
    "Side_Bookcase_W001": (side_bookcase, "A bookcase against the wall."),
    "Side_Dresser_W001": (side_dresser, "A chest of drawers, a jug on top."),
    "Side_Bench_W001": (side_bench, "A plain bench along the wall."),
    "Side_Desk_W001": (side_desk, "A desk along the wall: papers and ink."),
}
SIDES = {n: n.replace("_W00", "_%s00") for n in list(SIDE_HUNG) + list(SIDE_STANDING)}
PICTURES_SIDE = ["Side_Picture_W001", "Side_Picture_W002", "Side_Picture_W003"]
SIDE_ROOMS = {   # kind: (what may stand along a side wall, what may hang there)
    "home": (["Side_Cupboard_W001", "Side_Dresser_W001", "Side_Bench_W001"],
             PICTURES_SIDE + ["Side_Mirror_W001", "Side_Pegs_W001", "Side_Shelf_W001", "Side_Sconce_W001"]),
    "shop": (["Side_Cupboard_W001", "Side_Bench_W001"], PICTURES_SIDE + ["Side_Shelf_W001", "Side_Sconce_W001"]),
    "tavern": (["Side_Bench_W001", "Side_Dresser_W001"],
               PICTURES_SIDE + ["Side_Sconce_W001", "Side_Pegs_W001", "Side_Shelf_W001"]),
    "study": (["Side_Bookcase_W001", "Side_Desk_W001"], PICTURES_SIDE + ["Side_Sconce_W001", "Side_Mirror_W001"]),
    "hall": (["Side_Bookcase_W001", "Side_Bench_W001"], PICTURES_SIDE + ["Side_Tapestry_W001", "Side_Sconce_W001"]),
    "work": ([], ["Side_Shelf_W001", "Side_Pegs_W001", "Side_Sconce_W001"]),
    "chapel": (["Side_Bench_W001"], ["Side_Tapestry_W001", "Side_Sconce_W001"]),
    "barn": ([], []),
}


HUNG = {   # name: (picture, what Examine says)
    "Picture_Frame001": (lambda: frame(16, 13, GOLD, hills), "A painting of green hills, somewhere you'd rather be."),
    "Picture_Frame002": (lambda: frame(16, 13, BROWN, sea), "A ship under sail. The painter had never seen one."),
    "Picture_Frame003": (lambda: frame(12, 15, GOLD, portrait), "A portrait of someone's stern great-grandmother."),
    "Picture_Frame004": (lambda: frame(12, 15, BROWN, flowers), "Flowers in a jug, in oils."),
    "Picture_Frame005": (lambda: frame(16, 13, BROWN, peaks), "The mountains, as they look from a long way off."),
    "Picture_Frame006": (lambda: frame(16, 13, GOLD, dragon), "A dragon over a burning city. Not a cheerful thing to hang."),
    "Mirror001": (mirror, "A mirror. You've looked better."),
    "Tapestry001": (lambda: tapestry((128, 40, 44), (216, 176, 86), sword_motif), "A tapestry worked with a sword."),
    "Tapestry002": (lambda: tapestry((44, 66, 116), (210, 200, 160), tree_motif), "A tapestry worked with a tree."),
    "Coat_Pegs001": (coat_pegs, "Coat pegs: a cloak and a hat."),
    "Wall_Shelf001": (wall_shelf, "A shelf of odds and ends."),
    "Antlers001": (antlers, "Antlers. Whoever shot it tells the story often."),
}
STANDING = {
    "Cupboard001": (lambda: cupboard(OAK), "A cupboard, shut."),
    "Cupboard002": (lambda: cupboard(PINE), "A pine cupboard, its doors a little warped."),
    "Wardrobe001": (wardrobe, "A big dark wardrobe."),
    "Dresser001": (dresser, "A chest of drawers, a jug on top."),
    "Writing_Desk001": (lambda: writing_desk(OAK, 1), "A writing desk: papers and a quill."),
    "Writing_Desk002": (lambda: writing_desk(DARK, 2), "A writing desk with a ledger on it."),
    "Side_Table001": (side_table, "A little table with a candle on it."),
    "Washstand001": (washstand, "A washstand, a basin and a jug."),
    "Long_Clock001": (long_clock, "A long clock, ticking slowly."),
}
PICTURES = ["Picture_Frame%03d" % n for n in range(1, 7)]
ROOMS = {   # kind: (what may stand there, what may hang there)
    "home": (["Wardrobe001", "Dresser001", "Cupboard001", "Cupboard002", "Washstand001", "Side_Table001"],
             PICTURES + ["Mirror001", "Coat_Pegs001", "Wall_Shelf001"]),
    "shop": (["Cupboard001", "Cupboard002", "Side_Table001", "Long_Clock001"], PICTURES + ["Wall_Shelf001"]),
    "tavern": (["Cupboard001", "Side_Table001", "Dresser001"], PICTURES + ["Antlers001", "Wall_Shelf001", "Coat_Pegs001"]),
    "study": (["Writing_Desk001", "Writing_Desk002", "Long_Clock001", "Cupboard001"], PICTURES + ["Tapestry001", "Mirror001"]),
    "hall": (["Long_Clock001", "Writing_Desk002", "Side_Table001"], PICTURES + ["Tapestry001", "Tapestry002", "Mirror001"]),
    "work": ([], ["Wall_Shelf001", "Coat_Pegs001"]),
    "barn": ([], []),
    "chapel": ([], ["Tapestry001", "Tapestry002"]),
}
BARN = re.compile(r"(?i)hay|straw|nest|trough|stable|manger|pig|sty")
WORK = re.compile(r"(?i)anvil|forge|furnace|loom")
CHAPEL = re.compile(r"(?i)altar|pew|font")
SHOP = re.compile(r"(?i)shelf_goods|counter|potion_shelf|rack")
TAVERN = re.compile(r"(?i)dining_table|keg|barrel")
STUDY = re.compile(r"(?i)bookshelf|desk")
HOME = re.compile(r"(?i)^(double_)?bed\d")
FLOOR = re.compile(r"^(Plank|Tile|Marble|Carpet)\d{3}$|_Thin_(Plank|Tile|Marble)\d{3}$")
KEEP_CLEAR = re.compile(r"(?i)door|stairs|ladder|hatch|trapdoor|gate|cave_mouth")
SKIP_MAPS = re.compile(r"^(15,15|16,15|15,16|16,16),")         # (Redrock Manor's)
NEW = set(HUNG) | set(STANDING)
SIDE_ON = re.compile(r"^Side_.+_[WE]\d{3}$")
WALL = re.compile(r"(?i).*(wall|brick|plaster|timber|sandstone\d)")
SOLID = re.compile(r"^(?!Picture_|Mirror|Tapestry|Coat_Pegs|Wall_Shelf|Antlers|Woven_Rug|Rug|Flower|"
                   r"Side_(Picture|Mirror|Tapestry|Shelf|Pegs|Sconce))")   # (what stands in the way: not what's hung or lies flat)
NARROW = re.compile(r"^(Picture_Frame|Mirror|Tapestry)")   # (narrow enough for a corner, clear of the side wall)


def art():
    made = 0
    for table in (HUNG, STANDING):
        for name, (draw, _) in table.items():
            made += write_image(p("sprites", "Tiles", name + ".png"), draw())
    for table in (SIDE_HUNG, SIDE_STANDING):
        for name, (draw, _) in table.items():
            made += write_image(p("sprites", "Tiles", name + ".png"), draw())
            made += write_image(p("sprites", "Tiles", SIDES[name] % "E" + ".png"),
                                draw().transpose(Image.Transpose.FLIP_LEFT_RIGHT))
    return made


def data():
    tiles = Ini(p("data", "Tiles.ini"))
    for table, mask in ((HUNG, "1" * 49), (STANDING, "0" * 49)):
        for name, (_, words) in table.items():
            for k, v in (("Walkable.Data", mask), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", words),
                         ("Line.of.Sight", "1"), ("Layer", "Decor")):
                tiles.set(name, k, v)
    for table, mask in ((SIDE_HUNG, "1" * 49), (SIDE_STANDING, "0" * 49)):
        for name, (_, words) in table.items():
            for one in (name, SIDES[name] % "E"):
                for k, v in (("Walkable.Data", mask), ("Show.Name", "0"), ("Use.Words", ""), ("Examine.Info", words),
                             ("Line.of.Sight", "1"), ("Layer", "Decor")):
                    tiles.set(one, k, v)
    tiles.save(p("data", "Tiles.ini"))
    path = p("dev", "Minimap Colours.txt")
    lines = read_lines(path)
    while lines and not lines[-1]:
        lines.pop()
    have = {ln.split("\t")[0]: ln.split("\t")[1] for ln in lines if "\t" in ln}
    every = NEW | set(SIDES) | {SIDES[n] % "E" for n in SIDES}
    for name in sorted(every):                           # (the floor's colour: nothing to see from outside)
        if name not in have:
            lines.append("%s\t%s" % (name, have["Plank001"]))
    write_lines(path, lines)


# ================================================================== where
def script_spots():
    """Cells (on any map) that a script sends someone or puts something: furniture never stands there."""
    out = set()
    for f in glob.glob(p("data", "Scripts", "*.txt")):
        for ln in W.read(f).split("\n"):
            q = ln.split("\t")
            if len(q) > 2 and q[1] in ("Teleport", "Add.Entity"):
                m = re.match(r"^(\d+),(\d+)$", q[2].strip())
                if m:
                    out.add((int(m.group(1)) // 32 + 1, int(m.group(2)) // 32 + 1))
    return out


def rooms_of(m, z):
    """Each room on map m: the set of its floor cells (columns and rows from 1), joined side by side."""
    floor = set()
    for y in range(1, YT + 1):
        for x in range(1, XT + 1):
            t, over = W.parts(m.rows[y - 1][x - 1])
            if FLOOR.search(t) and (z > 0 or over.get("Roof")):
                floor.add((x, y))
    seen, out = set(), []
    for c in sorted(floor):
        if c in seen:
            continue
        room, todo = set(), [c]
        while todo:
            n = todo.pop()
            if n in room or n not in floor:
                continue
            room.add(n)
            todo += [(n[0] + 1, n[1]), (n[0] - 1, n[1]), (n[0], n[1] + 1), (n[0], n[1] - 1)]
        seen |= room
        out.append(room)
    return out


def line_cells(m):
    """Where its map lines put a thing or a person, and the cells they name (a bed, a nap), columns and rows from 1."""
    mx, my, _ = W.mxyz(m.name)
    cells, names = set(), []
    for ln in m.ents:
        c = W.line_cell(ln, mx, my)
        if c is not None:
            cells.add((c[0] - mx * XT + 1, c[1] - my * YT + 1))
            cells.add((c[0] - mx * XT + 1, c[1] - my * YT + 2))
            names.append((c[0] - mx * XT + 1, c[1] - my * YT + 1, ln.split("\t")[1] if "\t" in ln else ""))
        for a, b in re.findall(r"\b(?:Bed|Nap)=(\d+),(\d+)", ln):
            cells.add((int(a), int(b)))
    return cells, names


def kind_of(words):
    if any(CHAPEL.search(w) for w in words):
        return "chapel"
    if any(BARN.search(w) for w in words):
        return "barn"
    if any(WORK.search(w) for w in words):
        return "work"
    if any(SHOP.search(w) for w in words):
        return "shop"
    if any(HOME.search(w) for w in words):
        return "home"
    if any(STUDY.search(w) for w in words):
        return "study"
    if any(TAVERN.search(w) for w in words):
        return "tavern"
    return "hall"


def at_back_wall(m, c):
    """Has the cell the wall behind it (its own thin wall on its north, or a wall tile there: not a fireplace)?"""
    t = W.parts(m.rows[c[1] - 1][c[0] - 1])[0]
    thin = re.search(r"_Thin_[A-Za-z]+(\d{3})$", t)
    if thin:
        return "N" in THIN_EDGES[int(thin.group(1)) - 1] and not THIN_EDGES[int(thin.group(1)) - 1].startswith("+")
    north = W.parts(m.rows[c[1] - 2][c[0] - 1])[0] if c[1] > 1 else ""
    return bool(re.match(r"(?i).*(wall|brick|plaster|timber|sandstone\d)", north))


def still_one(room, solid):
    """Is what's left of the room's floor all joined up?"""
    left = room - solid
    if not left:
        return False
    todo, seen = [next(iter(left))], set()
    while todo:
        n = todo.pop()
        if n in seen or n not in left:
            continue
        seen.add(n)
        todo += [(n[0] + 1, n[1]), (n[0] - 1, n[1]), (n[0], n[1] + 1), (n[0], n[1] - 1)]
    return seen == left


def by_a_way(m, c):
    """Is the cell by a door, a stair or a ladder?"""
    for i in (-1, 0, 1):
        for j in (-1, 0, 1, 2):
            n = (c[0] + i, c[1] + j)
            if 1 <= n[0] <= XT and 1 <= n[1] <= YT and KEEP_CLEAR.search(m.rows[n[1] - 1][n[0] - 1]):
                return True
    return False


def room_kind(m, room, over, names):
    words = [o.get("Decor", "") for o in over.values() if o.get("Decor") and o.get("Decor") not in NEW and
             not SIDE_ON.match(o.get("Decor"))]
    words += [n for x, y, n in names if (x, y) in room]
    rows = [W.parts(m.rows[c[1] - 1][c[0] - 1])[0] for c in room]
    kind = kind_of(words)
    if kind == "hall" and len(room) < 30 and sum(r.startswith(("Tile", "Marble")) or "_Thin_" in r and "Plank" not in r
                                                 for r in rows) == 0:
        kind = "home"                                    # (a plain little room: somebody's)
    return kind


def furnish(m, z, spots):
    cells, names = line_cells(m)
    placed = 0
    for room in rooms_of(m, z):
        over = {c: W.parts(m.rows[c[1] - 1][c[0] - 1])[1] for c in room}
        if any(o.get("Decor") in NEW for o in over.values()) or len(room) < 6:
            continue
        kind = room_kind(m, room, over, names)
        rng = random.Random("%s %d" % (m.name, min(room)[0] * 100 + min(room)[1]))
        backs = [c for c in room if at_back_wall(m, c) and (c[0], c[1] - 1) not in room and not over[c].get("Decor") and
                 c not in cells and (c[0] - 1, c[1]) in room and (c[0] + 1, c[1]) in room and   # (not in a corner: over a wall)
                 not by_a_way(m, c)]
        backs.sort()
        rng.shuffle(backs)
        size = len(room)
        stand_n = 0 if size < 12 else 1 if size < 30 else 2 if size < 70 else 3
        hang_n = 1 if size < 20 else 2 if size < 70 else 3
        stand, hang = ROOMS[kind]
        stand, hang = rng.sample(stand, min(stand_n, len(stand))), rng.sample(hang, min(hang_n, len(hang)))
        solid = {c for c in room if W.parts(m.rows[c[1] - 1][c[0] - 1])[1].get("Decor") and
                 W.parts(m.rows[c[1] - 1][c[0] - 1])[1].get("Decor") in STANDING}
        chosen = []
        for name in stand:
            for c in backs:
                ok = c not in spots and (c[0], c[1] + 1) in room and all(
                    abs(c[0] - o[0]) > 1 or c[1] != o[1] for o, _ in chosen) and still_one(room, solid | {c})
                if ok:
                    chosen.append((c, name))
                    solid.add(c)
                    backs.remove(c)
                    break
        # (what hangs isn't in anyone's way: by a door, over where someone stands, and if it's narrow, in a corner)
        walls = sorted(c for c in room if at_back_wall(m, c) and (c[0], c[1] - 1) not in room and not over[c].get("Decor"))
        rng.shuffle(walls)
        taken = {c for c, _ in chosen}
        for name in hang:
            narrow = NARROW.match(name)
            for c in walls:
                corner = (c[0] - 1, c[1]) not in room or (c[0] + 1, c[1]) not in room
                if c not in taken and (narrow or not corner) and not any(abs(c[0] - o[0]) <= 1 and c[1] == o[1] for o in taken):
                    chosen.append((c, name))
                    taken.add(c)
                    break
        for c, name in chosen:
            t, o = W.parts(m.rows[c[1] - 1][c[0] - 1])
            o["Decor"] = name
            m.rows[c[1] - 1][c[0] - 1] = W.join(t, o)
            placed += 1
    return placed


def side_wall(m, c, room):
    """Which side wall the cell's against, not in a corner: "W", "E" or ""."""
    if (c[0], c[1] - 1) not in room or (c[0], c[1] + 1) not in room:
        return ""
    t = W.parts(m.rows[c[1] - 1][c[0] - 1])[0]
    thin = re.search(r"_Thin_[A-Za-z]+(\d{3})$", t)
    if thin:
        edges = THIN_EDGES[int(thin.group(1)) - 1]
        return edges if edges in ("W", "E") else ""
    for side, dx in (("W", -1), ("E", 1)):
        x = c[0] + dx
        if (x, c[1]) not in room and 1 <= x <= XT and WALL.match(W.parts(m.rows[c[1] - 1][x - 1])[0]):
            return side
    return ""


def furnish_sides(m, z, spots):
    """The same for the side walls: what's there seen side on."""
    cells, names = line_cells(m)
    placed = 0
    for room in rooms_of(m, z):
        over = {c: W.parts(m.rows[c[1] - 1][c[0] - 1])[1] for c in room}
        if len(room) < 9 or any(SIDE_ON.match(o.get("Decor", "")) for o in over.values()):
            continue
        kind = room_kind(m, room, over, names)
        rng = random.Random("sides %s %d" % (m.name, min(room)[0] * 100 + min(room)[1]))
        walls = sorted((c, side_wall(m, c, room)) for c in room if not over[c].get("Decor"))
        walls = [(c, s) for c, s in walls if s]
        rng.shuffle(walls)
        size = len(room)
        stand_n = 0 if size < 16 else 1 if size < 40 else 2
        hang_n = 1 if size < 16 else 2 if size < 40 else 3
        stand, hang = SIDE_ROOMS[kind]
        stand, hang = rng.sample(stand, min(stand_n, len(stand))), rng.sample(hang, min(hang_n, len(hang)))
        solid = {c for c, o in over.items() if o.get("Decor") and SOLID.search(o["Decor"])}
        chosen = []

        def apart(c, side):
            return all(s != side or abs(c[1] - o[1]) > 1 for o, s, _ in chosen)
        for name in stand:
            for c, side in walls:
                inward = 1 if side == "W" else -1
                if c in cells or c in spots or by_a_way(m, c) or not apart(c, side):
                    continue
                if (c[0] + inward, c[1]) not in room or (c[0] + inward * 2, c[1]) not in room:
                    continue                             # (room to get past it)
                if still_one(room, solid | {c}):
                    chosen.append((c, side, name))
                    solid.add(c)
                    break
        for name in hang:
            for c, side in walls:
                if not any(c == o for o, _, _ in chosen) and apart(c, side):
                    chosen.append((c, side, name))
                    break
        for c, side, name in chosen:
            t, o = W.parts(m.rows[c[1] - 1][c[0] - 1])
            o["Decor"] = SIDES[name] % side
            m.rows[c[1] - 1][c[0] - 1] = W.join(t, o)
            placed += 1
    return placed


def place():
    spots = script_spots()
    placed, maps = 0, 0
    for z in (0, 1, 2, 3):
        w = W.World(z)
        for m in w.maps.values():
            if SKIP_MAPS.match(m.name):
                continue
            n = furnish(m, z, spots) + furnish_sides(m, z, spots)
            if n:
                w.touch(m)
                placed += n
        maps += w.save()
    return placed, maps


def main():
    made = art()
    data()
    placed, maps = place()
    print("Interiors: %d pictures written; %d things put about, on %d maps" % (made, placed, maps))


if __name__ == "__main__":
    main()
