"""Ruined walls that join (the owner's wish: two old blocks side by side never looked like one wall). Two Join sets
(TileSets.ini Ruined_Wall, tall, no seeing past it, and Ruined_Wall_Low, a few courses you see over), sixteen pieces
each by the sides they join (Joins= NESW, `X` a lone stub), decor on any ground. Each is the same footprint of stone
(a run 10 px thick down the middle of the tile, out to every side it joins) raised and seen from the south: the face's
courses below, the capstones on top, the top crumbling between joins and slumping at a broken end, whole height where
it meets the next piece, so a run is one wall. A tall run and a low one join each other (Joins.Too), a step between.
Ruined_Wall001/002, the old single blocks, are Retired (ruined_walls_swap.py lays these over them).

  python -I "dev\\migrate\\build_ruined_walls.py"      (then ruined_walls_swap.py once, export_web_assets.py,
                                                         build_minimaps.py)

Safe to run again (it draws the same).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p                          # noqa: E402
import story_kit as SK                             # noqa: E402
from build_crossings import S, TILES, SETS, save, average, clamp   # noqa: E402
from PIL import Image                              # noqa: E402

SIDES = "NESW"
X0, X1, Y0, Y1 = 11, 21, 16, 26                    # (the footprint's middle: the run's width, and its depth)
# set: (its pieces' prefix, title, height, how far its top crumbles, words, line of sight)
SETS_ = {
    "Ruined_Wall": ("Ruined_Wall_", "ruined wall", 15, 6, "The broken wall of something old. You can't see past it.", "0"),
    "Ruined_Wall_Low": ("Ruined_Wall_Low_", "ruined wall, low", 7, 3,
                        "What's left of a wall: a few courses of stone.", "1"),
}
OLD = ("Ruined_Wall001", "Ruined_Wall002")
FACE = [(150, 144, 132), (138, 132, 120), (156, 150, 138), (130, 124, 114)]
CAP, CAP_LIT, CAP_DK = (172, 166, 152), (196, 190, 176), (140, 134, 122)
MORTAR = (96, 92, 84)
LINE = (44, 42, 38)
MOSS = [(92, 124, 60), (110, 140, 70)]


def name_of(set_name, mask):
    return "%s%s001" % (SETS_[set_name][0], mask or "X")


def footprint(mask):
    """{(x, y)} of the wall's ground: the middle square, and out to each side it joins."""
    xa = 0 if "W" in mask else X0
    xb = S if "E" in mask else X1
    ya = 0 if "N" in mask else Y0
    yb = S if "S" in mask else Y1
    cells = {(x, y) for x in range(xa, xb) for y in range(Y0, Y1)}
    cells |= {(x, y) for x in range(X0, X1) for y in range(ya, yb)}
    return cells


def heights(mask, cells, tall, crumble, rng):
    """{(x, y): height}: whole by a joined edge, its top's line crumbling in between along an east-west run (a broken
    notch now and then), and slumping towards an end that joins nothing. (A north-south run's top stays level: seen
    from the south, every dip in it would show a sliver of its face, in stripes.)"""
    along_x = [rng.uniform(0, crumble) for _ in range(S)]
    for i in range(1, S):
        along_x[i] = 0.7 * along_x[i - 1] + 0.3 * along_x[i]   # (smoothed, so it's a broken line, not noise)
    for _ in range(rng.randint(1, 2)):                           # (a stone or two gone off the top)
        k = rng.randint(6, S - 9)
        for i in range(k, k + rng.randint(2, 4)):
            along_x[i] += rng.choice((2, 3))
    out = {}
    for x, y in cells:
        drop = along_x[x] if Y0 <= y < Y1 else 0
        if "N" in mask or "S" in mask:                          # (whole where it turns north or south, rising to it)
            drop *= min(1.0, max(0, X0 - x, x - X1 + 1) / 4.0)
        near = min([x if "W" in mask else 99, S - 1 - x if "E" in mask else 99,
                    y if "N" in mask else 99, S - 1 - y if "S" in mask else 99])
        drop *= min(1.0, max(0, near - 1) / 5.0)                # (whole height where it meets the next piece)
        ends = []                                               # (how near an end that joins nothing)
        if not mask:
            ends.append(0)
        if len(mask) == 1:
            side = mask
            ends.append({"N": Y1 - 1 - y, "S": y - Y0, "W": X1 - 1 - x, "E": x - X0}[side])
        if ends:
            drop += max(0, 4 - min(ends)) * 0.25 * crumble + (crumble * 0.4 if not mask else 0)
        out[(x, y)] = max(2, int(round(tall - drop)))
    return out


def piece(set_name, mask):
    _, _, tall, crumble, _, _ = SETS_[set_name]
    rng = random.Random("ruined %s %s" % (set_name, mask))
    cells = footprint(mask)
    h = heights(mask, cells, tall, crumble, rng)
    if "S" in mask:                                             # (the next piece south's top shows at this one's foot,
        for y in range(S, S + tall + 1):                        #  raised into it: drawn here as it goes on)
            for x in range(X0, X1):
                h[(x, y)] = tall
    px = {}                                                     # (x, y on screen): colour
    kind = {}                                                   # (x, y): "cap" or "face"
    for x, y in sorted(h, key=lambda c: (c[1], c[0])):          # (north to south: what's nearer covers what's behind)
        top = h[(x, y)]
        for k in range(top):                                    # the face: courses of stone, 4 px high, bonded
            sy = y - k
            if not 0 <= sy < S:
                continue
            course = k // 4
            joint = k % 4 == 3 or (x + course * 3 + (course % 2) * 4) % 8 == 0
            c = MORTAR if joint else FACE[(x // 8 + course * 3 + (x + y) % 2) % len(FACE)]
            c = clamp(tuple(v * (0.78 + 0.22 * min(1.0, k / 6.0)) for v in c))   # (darker down by the ground)
            px[(x, sy)], kind[(x, sy)] = c, "face"
        sy = y - top                                            # the capstones on top: big flat stones
        if 0 <= sy < S:
            seam = (x + (y // 5) * 3) % 7 == 0 or y % 5 == 0
            c = clamp(tuple(v * 0.86 for v in CAP_DK)) if seam else CAP if (x // 7 + y // 5) % 3 else CAP_DK
            px[(x, sy)], kind[(x, sy)] = c, "cap"
    for (x, y), k in list(kind.items()):                        # its edge to the north catches the light, the south's in shade
        if k == "cap" and kind.get((x, y - 1)) is None:
            px[(x, y)] = CAP_LIT
        elif k == "cap" and kind.get((x, y + 1)) == "face":
            px[(x, y)] = CAP_DK
    for _ in range(5):                                          # moss in the cracks and on the tops
        x, y = rng.randrange(S), rng.randrange(S)
        if (x, y) in px and px[(x, y)] != MORTAR:
            px[(x, y)] = rng.choice(MOSS)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for x, y in cells:                                          # its shadow on the ground, south and east
        for dx, dy in ((1, 1), (2, 1), (2, 2), (3, 2)):
            sx, sy = x + dx, y + dy
            if 0 <= sx < S and 0 <= sy < S and (sx, sy) not in cells:
                im.putpixel((sx, sy), (0, 0, 0, 56))
    for (x, y), c in px.items():
        im.putpixel((x, y), c + (255,))
    for y in range(S):                                          # the outline, where it meets the open (never a tile's edge)
        for x in range(S):
            if (x, y) in px:
                continue
            if any((x + dx, y + dy) in px for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                im.putpixel((x, y), LINE + (255,))
    for _ in range(2 if len(mask) <= 1 else 0):                 # a fallen stone or two by a broken end
        x, y = rng.randint(3, 25), rng.randint(27, 28)
        if all((x + dx, y + dy) not in px and (x + dx, y + dy) not in cells for dx in range(-1, 5) for dy in range(-1, 4)):
            for dx in range(4):                                 # (a block, its top lit, its front in shade, outlined)
                im.putpixel((x + dx, y), CAP + (255,))
                im.putpixel((x + dx, y + 1), FACE[3] + (255,))
                im.putpixel((x + dx, y - 1), LINE + (255,))
                im.putpixel((x + dx, y + 2), LINE + (255,))
            for dy in (0, 1):
                im.putpixel((x - 1, y + dy), LINE + (255,))
                im.putpixel((x + 4, y + dy), LINE + (255,))
    return im


def walk(mask):
    """The 7x7 walk mask: its footprint can't be walked through (a cell whose middle it covers)."""
    cells = footprint(mask)
    return "".join("0" if (int((i + 0.5) * S / 7), int((j + 0.5) * S / 7)) in cells else "1"
                   for j in range(7) for i in range(7))


def main():
    tiles, sets = Ini(TILES), Ini(SETS)
    order = {}
    for set_name, (_, title, _, _, words, sight) in SETS_.items():
        order[set_name] = []
        for bits in range(16):
            mask = "".join(s for i, s in enumerate(SIDES) if bits >> i & 1)
            nm = name_of(set_name, mask)
            order[set_name].append(nm)
            im = piece(set_name, mask)
            save(nm, im)
            for k, v in (("Walkable.Data", walk(mask)), ("Show.Name", "1"), ("Use.Words", ""), ("Examine.Info", words),
                         ("Line.of.Sight", sight), ("Layer", "Decor"),
                         ("Piece", "%s: %s" % (title, "joined " + ", ".join(mask) if mask else "a lone stub")),
                         ("Joins", mask or "-")):
                tiles.set(nm, k, v)
            SK.minimap_colour(nm, (109, 114, 84))
    for set_name, (_, title, *_r) in SETS_.items():
        other = [n for s, ns in order.items() if s != set_name for n in ns]
        for k, v in (("Title", title), ("Columns", "4"), ("Tiles", ",".join(order[set_name])), ("Kind", "Join"),
                     ("Joins.Too", ",".join(other + list(OLD)))):
            sets.set(set_name, k, v)
    for n in OLD:
        tiles.set(n, "Retired", "1")
    tiles.save(TILES)
    sets.save(SETS)
    print("Ruined walls: 2 sets of 16 pieces drawn (Ruined_Wall, Ruined_Wall_Low); %s retired" % ", ".join(OLD))


if __name__ == "__main__":
    main()
