"""Ways over the wet and the wall round Galaith, drawn again (the owner's wish: the boardwalk grittier and raised off the
marsh, Galaith's wall better, a fancy bridge to put down whole).

  * Boardwalk001: weathered planks from a big seamless texture (sprites/Textures/Boardwalk), rows of their own lengths,
    thin gaps with the mud showing, nails, knots and moss, the joins between tiles not showing. Raised=1: the
    page (ground.js) casts its shadow on the marsh south and east of it, shows its plank ends and the posts it stands
    on, and the marsh doesn't blend over its edge (Blend=0).
  * Galaith's wall (Galaith_Wall001-005: the top of an east-west run, its face, a north-south run, a corner tower's top
    and face): pale ashlar, its courses and joints, a parapet of merlons, soot rising from its foot where the dragon's
    fire took it; the west gate (005 shut, 006 open) in it; the gate pieces that opened into the town wall's open
    Galaith's own again.
  * A fancy bridge, two sets the Maps palette puts down by dragging a rectangle (TileSets.ini Kind=Stretch):
    Fancy_Bridge_NS (walked north and south) and Fancy_Bridge_EW. Pale stone with a carved inlay down the middle, a
    balustrade along its sides (walked into, not over), a lamp on each corner's post that lights at night, and stone
    thresholds at its ends.

Safe to run again.

  python -I "dev\\migrate\\build_crossings.py"
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, write_image          # noqa: E402
import story_kit as SK                           # noqa: E402

from PIL import Image, ImageDraw                 # noqa: E402

S = 32
TILES, SETS = p("data", "Tiles.ini"), p("data", "TileSets.ini")


def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)


def shade(c, k):
    return clamp((c[0] * k, c[1] * k, c[2] * k))


def mix(a, b, t):
    return clamp(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def new(fill=(0, 0, 0)):
    return Image.new("RGBA", (S, S), fill + (255,))


def save(name, im):
    return write_image(p("sprites", "Tiles", name + ".png"), im)


def average(im):
    return im.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))


# ================================================================== the boardwalk
BOARD_SIZE = 256


def boardwalk():
    """A big seamless texture (Tiles.ini Texture=): rows of planks of their own lengths, the same thin gap everywhere and
    round the edges, so no tile's join shows and nothing lines up from one tile to the next."""
    rng = random.Random("boardwalk")
    size = BOARD_SIZE
    im = Image.new("RGBA", (size, size), (44, 36, 28, 255))       # (the mud between the planks)
    px = im.load()
    woods = [(112, 96, 76), (98, 86, 68), (120, 104, 84), (92, 80, 64), (106, 92, 70)]
    heights = [4] * 32 + [5] * 16                                 # (with a gap under each: 256 exactly, so it wraps)
    rng.shuffle(heights)
    y = 0
    for height in heights:
        x0 = rng.randrange(size)                                  # (where this row's first plank starts: wraps round)
        along = 0
        while along < size:
            length = rng.randrange(26, 72)
            if size - along < length + 26:
                length = size - along                             # (the last plank butts against the row's first)
            wood, worn = rng.choice(woods), rng.random() * 0.2
            streaks = [rng.randrange(height) for _ in range(2)]
            for i in range(length - 1):                           # (one pixel left at its end: where two planks butt)
                px_x = (x0 + along + i) % size
                for dy in range(height):
                    k = 1.12 if dy == 0 else 0.8 if dy == height - 1 else 1.0     # (lit along its top, rounded below)
                    c = shade(wood, k)
                    if dy in streaks and rng.random() < 0.3:
                        c = shade(c, 0.88)                        # (grain, along the plank)
                    if rng.random() < 0.18:
                        c = shade(c, 0.9)
                    if rng.random() < worn:
                        c = mix(c, (150, 138, 116), 0.25)         # (worn pale where feet go)
                    px[px_x, y + dy] = c + (255,)
            for i in (2, length - 4):                             # (its nails, near each end)
                ny = y + rng.randrange(1, height - 1)
                px[(x0 + along + i) % size, ny] = (58, 50, 42, 255)
            if rng.random() < 0.5:                                # (a knot)
                px[(x0 + along + rng.randrange(4, max(5, length - 5))) % size, y + rng.randrange(1, height - 1)] = (70, 58, 44, 255)
            along += length
        y += height + 1
    for _ in range(size // 2):                                    # (moss and mud in the gaps, wherever it's gathered)
        x, y = rng.randrange(size), rng.randrange(size)
        if px[x, y][:3] == (44, 36, 28):
            colour = rng.choice([(70, 92, 46), (58, 78, 40), (84, 70, 50), (66, 54, 40)])
            for i in range(rng.randrange(1, 4)):
                if px[(x + i) % size, y][:3] == (44, 36, 28):
                    px[(x + i) % size, y] = colour + (255,)
    return im


# ================================================================== Galaith's wall
STONE = [(210, 204, 190), (198, 192, 178), (218, 212, 198), (190, 184, 170)]
MORTAR, SOOT = (118, 112, 104), (52, 48, 46)


def soot(im, rng, strength, from_bottom=True):
    """The dragon's fire: darker towards the foot, in licks."""
    px = im.load()
    licks = [rng.randrange(S) for _ in range(4)]
    for y in range(S):
        for x in range(S):
            t = (y / (S - 1.0)) if from_bottom else 0.5
            lick = max(0.0, 1 - min(abs(x - l) for l in licks) / 5.0) * 0.35
            k = min(0.85, strength * (t ** 1.6 + lick * t) + rng.random() * 0.05)
            r, g, b, a = px[x, y]
            px[x, y] = mix((r, g, b), SOOT, k) + (a,)


def ashlar(im, rng, y0, y1, course=7):
    """Courses of cut blocks between rows y0 and y1, each block lit along its top and left, its joints mortar."""
    px = im.load()
    d = ImageDraw.Draw(im)
    for row, y in enumerate(range(y0, y1, course)):
        h = min(course, y1 - y)
        x = -rng.randrange(0, 10) if row % 2 else 0
        while x < S:
            w = rng.randrange(11, 17)
            c = rng.choice(STONE)
            d.rectangle((x, y, x + w - 1, y + h - 1), fill=c)
            for i in range(x, x + w):
                for j in range(y, y + h):
                    if 0 <= i < S and 0 <= j < S and rng.random() < 0.12:
                        px[i, j] = shade(c, 0.93) + (255,)           # (the stone's own grain)
            d.line((x, y, x + w - 2, y), fill=shade(c, 1.07))         # (lit edges)
            d.line((x, y, x, y + h - 2), fill=shade(c, 1.04))
            d.line((x + 1, y + h - 2, x + w - 2, y + h - 2), fill=shade(c, 0.84))
            d.line((x + w - 1, y, x + w - 1, y + h - 1), fill=MORTAR)
            x += w
        d.line((0, y + h - 1, S, y + h - 1), fill=MORTAR)


def wall_face(rng, tower=False):
    im = new(MORTAR)
    d = ImageDraw.Draw(im)
    ashlar(im, rng, 3, 28)
    d.rectangle((0, 0, S, 2), fill=(222, 216, 202))                     # (the coping along its top)
    d.line((0, 3, S, 3), fill=(120, 114, 106))                          # (its shadow)
    d.rectangle((0, 28, S, S), fill=(150, 144, 132))                    # (the plinth it stands on)
    d.line((0, 28, S, 28), fill=(176, 170, 158))
    if tower:
        d.rectangle((0, 3, 2, 27), fill=(176, 170, 158))                # (its corners' buttresses)
        d.rectangle((29, 3, 31, 27), fill=(150, 144, 132))
        d.rectangle((14, 9, 17, 21), fill=(26, 22, 22))                 # (an arrow slit)
        d.line((14, 9, 17, 9), fill=(200, 194, 180))
    soot(im, rng, 0.9 if tower else 0.75)
    return im


def walkway(im, rng, box):
    """Flagstones along the top of the wall, worn and cracked."""
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    y = y0
    while y < y1:
        h = min(rng.randrange(6, 10), y1 - y)
        x = x0 - rng.randrange(0, 6)
        while x < x1:
            w = rng.randrange(7, 12)
            c = shade(rng.choice(STONE), 0.92)
            d.rectangle((max(x, x0), y, min(x + w - 1, x1 - 1), y + h - 1), fill=c, outline=MORTAR)
            if rng.random() < 0.3:
                cx = rng.randrange(max(x, x0) + 1, max(max(x, x0) + 2, min(x + w - 1, x1 - 1)))
                d.line((cx, y + 1, cx + 2, y + h - 2), fill=shade(c, 0.78))   # (a crack)
            x += w
        y += h


def merlons(im, side):
    """A parapet of merlons along one side (N, S, E, W): their tops lit, the gaps between them dark (the drop)."""
    d = ImageDraw.Draw(im)
    along = side in ("N", "S")
    for k, a in enumerate(range(0, S, 8)):
        for b in range(0, 6):
            for c in range(a, min(a + 8, S)):
                x, y = (c, b if side == "N" else S - 1 - b) if along else (b if side == "W" else S - 1 - b, c)
                merlon = (c - a) < 5
                col = ((224, 218, 204) if b < 4 else (172, 166, 154)) if merlon else (40, 36, 34)
                im.putpixel((x, y), col + (255,))
    if along:
        y = 6 if side == "N" else S - 7
        d.line((0, y, S, y), fill=(130, 124, 114))                      # (the shadow it casts on the walk)
    else:
        x = 6 if side == "W" else S - 7
        d.line((x, 0, x, S), fill=(130, 124, 114))


def wall_top(rng):
    im = new(MORTAR)
    walkway(im, rng, (0, 7, S, 27))
    merlons(im, "N")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 27, S, 31), fill=(214, 208, 194))                   # (the low inner wall at the walk's edge)
    d.line((0, 31, S, 31), fill=(150, 144, 132))
    soot(im, rng, 0.35, from_bottom=False)
    return im


def wall_run_ns(rng):
    im = new(MORTAR)
    walkway(im, rng, (7, 0, 25, S))
    merlons(im, "W")
    merlons(im, "E")
    soot(im, rng, 0.35, from_bottom=False)
    return im


def tower_top(rng):
    im = new(MORTAR)
    walkway(im, rng, (6, 6, 26, 26))
    for side in "NESW":
        merlons(im, side)
    d = ImageDraw.Draw(im)
    d.ellipse((12, 12, 19, 19), fill=(96, 74, 50), outline=(60, 46, 32))  # (the hatch down into the tower)
    d.line((15, 12, 15, 19), fill=(60, 46, 32))
    soot(im, rng, 0.4, from_bottom=False)
    return im


def gate_ns(rng, open_):
    """The west gate, in a north-south run: an arch through it, its doors barred shut or standing open."""
    im = wall_run_ns(rng)
    d = ImageDraw.Draw(im)
    d.rectangle((7, 0, 24, S), fill=(30, 26, 24))
    if not open_:
        d.rectangle((8, 1, 23, 30), fill=(82, 54, 32))
        for x in (11, 15, 19):
            d.line((x, 1, x, 30), fill=(54, 34, 20))
        for y in (8, 22):
            d.line((8, y, 23, y), fill=(52, 52, 58), width=2)
    else:
        d.rectangle((7, 0, 9, S), fill=(82, 54, 32))
        d.rectangle((22, 0, 24, S), fill=(82, 54, 32))
    return im


# ================================================================== the fancy bridge
DECK, DECK_DARK, INLAY = (204, 198, 184), (176, 170, 156), (120, 92, 70)
PIECES = [("TL", "corner: top left"), ("T", "edge: top"), ("TR", "corner: top right"),
          ("L", "edge: left"), ("M", "middle"), ("R", "edge: right"),
          ("BL", "corner: bottom left"), ("B", "edge: bottom"), ("BR", "corner: bottom right")]


def deck(rng, inlay=True):
    """The deck of a bridge walked north and south: pale stone slabs, a carved inlay down its middle (the middle
    column's pieces only: one runner down the bridge, however wide)."""
    im = new(DECK)
    d = ImageDraw.Draw(im)
    for y in range(0, S, 8):
        for x in range(0, S, 16):
            ox = 8 if (y // 8) % 2 else 0
            c = rng.choice([DECK, shade(DECK, 0.96), shade(DECK, 1.03)])
            d.rectangle((x - ox, y, x - ox + 15, y + 7), fill=c, outline=DECK_DARK)
    if not inlay:
        return im
    d.rectangle((13, 0, 18, S), fill=(150, 116, 88))                   # (the inlay: a runner of red stone,
    for y in range(0, S, 8):                                           #  diamonds carved in it)
        d.polygon([(15.5, y + 1), (18, y + 4), (15.5, y + 7), (13, y + 4)], fill=INLAY, outline=(196, 168, 120))
    d.line((12, 0, 12, S), fill=(150, 144, 132))
    d.line((19, 0, 19, S), fill=(150, 144, 132))
    return im


def balustrade(im, side):
    """Along one side (W or E), the outer ten pixels: a rail on little turned posts, the water's shadow under it."""
    d = ImageDraw.Draw(im)
    x0 = 0 if side == "W" else S - 10
    d.rectangle((x0, 0, x0 + 9, S), fill=(150, 144, 132))
    for y in range(1, S, 6):
        d.ellipse((x0 + 2, y, x0 + 7, y + 4), fill=(228, 222, 208), outline=(130, 124, 114))   # (the balusters)
    rail = x0 + (1 if side == "W" else 6)
    d.rectangle((rail, 0, rail + 2, S), fill=(236, 230, 216))           # (the rail along their top)
    d.line((rail + 3 if side == "W" else rail - 1, 0, rail + 3 if side == "W" else rail - 1, S), fill=(120, 114, 106))


def threshold(im, side):
    """The bridge's end (N or S): a band of darker granite across it, where it meets the road."""
    d = ImageDraw.Draw(im)
    y0 = 0 if side == "N" else S - 6
    d.rectangle((0, y0, S, y0 + 5), fill=(150, 146, 140))
    for x in range(0, S, 8):
        d.line((x, y0, x, y0 + 5), fill=(118, 114, 108))
    d.line((0, y0 + (5 if side == "N" else 0), S, y0 + (5 if side == "N" else 0)), fill=(120, 114, 106))


def newel(im, corner):
    """A corner's post: a square pedestal, a lantern on it (it lights at night: Light=)."""
    d = ImageDraw.Draw(im)
    x0 = 0 if "L" in corner else S - 12
    y0 = 0 if "T" in corner else S - 12
    d.rectangle((x0, y0, x0 + 11, y0 + 11), fill=(222, 216, 202), outline=(130, 124, 114))
    d.rectangle((x0 + 2, y0 + 2, x0 + 9, y0 + 9), fill=(190, 184, 170))
    d.rectangle((x0 + 4, y0 + 3, x0 + 7, y0 + 8), fill=(60, 52, 44))   # (the lantern's iron cage)
    d.rectangle((x0 + 5, y0 + 4, x0 + 6, y0 + 7), fill=(255, 214, 120))  # (and its flame)


def bridge_ns(piece, rng):
    im = deck(rng, inlay=piece in ("T", "M", "B"))
    if piece in ("TL", "L", "BL"):
        balustrade(im, "W")
    if piece in ("TR", "R", "BR"):
        balustrade(im, "E")
    if piece in ("TL", "T", "TR"):
        threshold(im, "N")
    if piece in ("BL", "B", "BR"):
        threshold(im, "S")
    if piece in ("TL", "TR", "BL", "BR"):
        newel(im, piece)
    return im


def walk_ns(piece):
    """Its walk mask: the balustrade's two outer columns and the posts' corners are not walked."""
    grid = [["1"] * 7 for _ in range(7)]
    for r in range(7):
        if piece in ("TL", "L", "BL"):
            grid[r][0] = grid[r][1] = "0"
        if piece in ("TR", "R", "BR"):
            grid[r][5] = grid[r][6] = "0"
    for corner in ("TL", "TR", "BL", "BR"):
        if piece == corner:
            rows = (0, 1, 2) if "T" in corner else (4, 5, 6)
            cols = (0, 1, 2) if "L" in corner else (4, 5, 6)
            for r in rows:
                for c in cols:
                    grid[r][c] = "0"
    return grid


EW_OF = {"TL": "TL", "T": "L", "TR": "BL", "L": "T", "M": "M", "R": "B", "BL": "TR", "B": "R", "BR": "BR"}


def bridges():
    """{name: (picture, walk mask, piece words, light)} for both sets."""
    out = {}
    for piece, words in PIECES:
        rng = random.Random("bridge" + piece)
        im, grid = bridge_ns(piece, rng), walk_ns(piece)
        light = piece in ("TL", "TR", "BL", "BR")
        out["Fancy_Bridge_NS_%s001" % piece] = (im, grid, words, light)
    for piece, words in PIECES:                            # (walked east and west: the same, turned on its side)
        src = [k for k, v in EW_OF.items() if v == piece][0]
        im, grid, _, light = out["Fancy_Bridge_NS_%s001" % src]
        out["Fancy_Bridge_EW_%s001" % piece] = (im.transpose(Image.Transpose.TRANSPOSE),
                                            [list(r) for r in zip(*grid)], words, light)
    return out


# ================================================================== all of it
def main():
    tiles, sets = Ini(TILES), Ini(SETS)
    made = 0
    big = boardwalk()
    made += write_image(p("sprites", "Textures", "Boardwalk.png"), big)
    im = big.crop((0, 0, S, S))                                   # (its picture where a tile has to have one: the palette)
    made += save("Boardwalk001", im)
    for k, v in (("Blend", "0"), ("Raised", "1"), ("Texture", "Boardwalk"),
                 ("Examine.Info", "A boardwalk over the marsh, on posts. It creaks.")):
        tiles.set("Boardwalk001", k, v)
    SK.minimap_colour("Boardwalk001", average(im))
    rng = random.Random("galaith")
    walls = {"Galaith_Wall001": wall_top(rng), "Galaith_Wall004": wall_face(rng), "Galaith_Wall002": wall_run_ns(rng),
             "Galaith_Wall003": tower_top(rng), "Galaith_Wall005": wall_face(rng, tower=True),
             "Galaith_Gate005": gate_ns(rng, False), "Galaith_Gate006": gate_ns(rng, True)}
    for name, pic in walls.items():
        made += save(name, pic)
    tiles.set("Galaith_Gate001", "Unlocked.Tile", "Galaith_Gate002")      # (they opened into the town wall's gate)
    tiles.set("Galaith_Gate003", "Unlocked.Tile", "Galaith_Gate004")
    names = {"NS": [], "EW": []}
    for name, (pic, grid, words, light) in bridges().items():
        made += save(name, pic)
        names[name.split("_")[2]].append(name)
        for k, v in (("Walkable.Data", "".join("".join(r) for r in grid)), ("Show.Name", "1"), ("Use.Words", ""),
                     ("Examine.Info", "A fine stone bridge, its rails carved, a lamp on every corner."),
                     ("Line.of.Sight", "1"), ("Piece", words), ("Blend", "0")):
            tiles.set(name, k, v)
        if light:
            tiles.set(name, "Light", "60")
        SK.minimap_colour(name, average(pic))
    for way, title in (("NS", "fancy bridge, walked north and south"), ("EW", "fancy bridge, walked east and west")):
        for k, v in (("Title", title), ("Columns", "3"), ("Tiles", ",".join(names[way])), ("Kind", "Stretch")):
            sets.set("Fancy_Bridge_" + way, k, v)
    tiles.save(TILES)
    sets.save(SETS)
    print("Crossings and walls: %d pictures written" % made)


if __name__ == "__main__":
    main()
