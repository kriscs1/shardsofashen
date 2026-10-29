"""The palisade (a wall of sharpened logs round a camp) in the twelve pieces that build any wall line, as the fences have
them (fence_tiles.py PIECES): Palisade001 east-west, 002 north-south, 003-006 the corners, 007-010 the T's, 011 a
crossing, 012 a post on its own. Each is drawn from the sides it joins (N, E, S, W): an east-west wall is a row of logs
standing on the row y 27, a north-south one a column of logs down the middle (x 10-22), one behind another every 8 px,
and a knot of logs where they meet, turn or end - so pieces meet across tile edges without gaps or overlaps (the
logs are on a 4 px rhythm, the same in every tile). All of a palisade tile blocks walking and seeing.

Then every map's palisade is pieced from its neighbours (the hobgoblins' camp, 2,2,0; the smugglers', 4,5,0 and
wherever else it stands): a wall's end by a gate is its run's own piece, so the run goes right up to the opening.
Safe to run again.
Usage: python -I dev/migrate/build_palisades.py [preview.png]"""
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ini, p, read_lines, write_lines  # noqa: E402

S = 32
BASE = 27                 # (the row an east-west wall's logs stand on)
PIECES = [(1, "EW", "east-west"), (2, "NS", "north-south"),
          (3, "ES", "corner: east and south (the top left of a pen)"), (4, "SW", "corner: west and south (the top right)"),
          (5, "NE", "corner: north and east (the bottom left)"), (6, "NW", "corner: north and west (the bottom right)"),
          (7, "ESW", "a T: east, south and west"), (8, "NEW", "a T: north, east and west"),
          (9, "NES", "a T: north, east and south"), (10, "NSW", "a T: north, south and west"),
          (11, "NESW", "a crossing"), (12, "", "a post on its own")]
BY_SIDES = {sides: n for n, sides, _ in PIECES}
BY_SIDES.update({"E": 1, "W": 1, "N": 2, "S": 2})     # (a run's end, by a gate: the run's own piece, right to the gap)
INFO = "A palisade of sharpened logs: no seeing over it."
OUTLINE, LASH, CUT = (46, 30, 16), (70, 56, 40), (206, 176, 126)


def name(n):
    return "Palisade%03d" % n


def wood(x, bottom):
    """A log's colour: the same for the same spot in every tile (so runs repeat seamlessly)."""
    r = random.Random(x * 131 + bottom * 7)
    return (122 + r.randint(-12, 10), 84 + r.randint(-9, 8), 46 + r.randint(-5, 5))


def log(d, x, w, bottom, height):
    """One upright log, its point at the top: lit on its left, in shadow on its right, the cut wood pale."""
    col = wood(x, bottom)
    top = bottom - height
    d.rectangle((x, top + 3, x + w - 1, bottom - 1), fill=col)
    d.polygon([(x, top + 3), (x + (w - 1) / 2, top), (x + w - 1, top + 3)], fill=col)
    d.line((x, top + 3, x, bottom - 1), fill=tuple(min(255, c + 32) for c in col))
    d.line((x + w - 1, top + 3, x + w - 1, bottom - 1), fill=(64, 42, 22))
    d.point((x + (w - 1) // 2, top + 1), fill=CUT)


def picture(sides):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    posts = []                                          # (bottom, x, width, height): drawn back to front
    for side, x0, x1 in (("W", 0, 16), ("E", 16, 32)):
        if side in sides:
            for x in range(x0, x1, 4):
                posts.append((BASE, x, 4, 21 + random.Random(x).randint(0, 3)))
            sd.rectangle((x0, BASE - 1, x1 - 1, BASE + 2), fill=(0, 0, 0, 80))
    for side, bottoms in (("N", (8, 16)), ("S", (24, 32))):
        if side in sides:
            for b in bottoms:
                for x in (10, 14, 18):
                    posts.append((b, x, 4, 22))
            sd.rectangle((9, bottoms[0] - 10, 22, bottoms[1] - 1), fill=(0, 0, 0, 60))
    knot = not ("E" in sides or "W" in sides) or not ("N" in sides or "S" in sides) or len(sides) != 2 or True
    if sides not in ("EW", "NS") and knot:               # (where the wall turns, meets or stands alone: a knot of logs)
        for x in (10, 14, 18):
            posts.append((BASE, x, 4, 23 + random.Random(x * 3).randint(0, 2)))
        sd.ellipse((8, BASE - 2, 23, BASE + 3), fill=(0, 0, 0, 80))
    img.alpha_composite(shadow)
    for bottom, x, w, h in sorted(posts):
        log(d, x, w, bottom, h)
    if "W" in sides or "E" in sides:                    # the lashings, across the logs
        for y in (BASE - 16, BASE - 6):
            x0 = 0 if "W" in sides else 10
            x1 = 31 if "E" in sides else 21
            d.line((x0, y, x1, y), fill=LASH)
    # the dark outline round it, where nothing else is (the camp reads against any ground)
    a = img.getchannel("A")
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        m = Image.new("L", (S, S), 0)
        m.paste(a, (dx, dy))
        out.paste(Image.new("RGBA", (S, S), OUTLINE + (255,)), (0, 0), m)
    out.alpha_composite(img)
    for side, edge in (("W", (0, 0, 0, S - 1)), ("E", (S - 1, 0, S - 1, S - 1)), ("N", (0, 0, S - 1, 0)),
                       ("S", (0, S - 1, S - 1, S - 1))):
        if side in sides:                                # (no outline where it carries on into the next tile)
            x0, y0, x1, y1 = edge
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    if out.getpixel((x, y)) == OUTLINE + (255,) and img.getpixel((x, y))[3] == 0:
                        out.putpixel((x, y), (0, 0, 0, 0))
    return out


def pictures():
    for n, sides, _ in PIECES:
        picture(sides).save(p("sprites", "Tiles", name(n) + ".png"))


def data():
    tiles = Ini(p("data", "Tiles.ini"))
    for n, sides, piece in PIECES:
        for k, v in (("Walkable.Data", "0" * 49), ("Show.Name", "1"), ("Use.Words", ""), ("Examine.Info", INFO),
                     ("Line.of.Sight", "0"), ("Layer", "Decor"), ("Piece", piece)):
            tiles.set(name(n), k, v)
    tiles.save(p("data", "Tiles.ini"))
    sets = Ini(p("data", "TileSets.ini"))
    layout = (3, 7, 1, 4, 9, 11, 1, 10, 2, 2, 12, 2, 5, 8, 1, 6)       # (as the fences: a pen, every piece in it)
    sets.set("Palisade", "Title", "palisade")
    sets.set("Palisade", "Columns", "4")
    sets.set("Palisade", "Tiles", ",".join(name(n) for n in layout))
    sets.save(p("data", "TileSets.ini"))
    colours = p("dev", "Minimap Colours.txt")
    lines = read_lines(colours)
    have = {ln.split("\t")[0] for ln in lines}
    lines += ["%s\t110 76 40" % name(n) for n, _, _ in PIECES if name(n) not in have]
    write_lines(colours, lines)


def join_maps():
    """Every palisade on every map pieced from its neighbours on the same map."""
    import re
    done = 0
    for f in sorted(os.listdir(p("maps"))):
        if not f.endswith(".txt"):
            continue
        path = p("maps", f)
        lines = read_lines(path)
        rows = [ln.split(":") for ln in lines[:21]]
        if len(rows) < 21 or not any("Palisade" in c for row in rows for c in row):
            continue
        pal = lambda x, y: 0 <= y < 21 and 0 <= x < len(rows[y]) and re.search(r"Decor\(Palisade\d{3}\)", rows[y][x])
        changed = False
        for y in range(21):
            for x in range(len(rows[y])):
                if not pal(x, y):
                    continue
                sides = "".join(s for s, (dx, dy) in zip("NESW", ((0, -1), (1, 0), (0, 1), (-1, 0)))
                                if pal(x + dx, y + dy))
                cell = re.sub(r"Decor\(Palisade\d{3}\)", "Decor(%s)" % name(BY_SIDES[sides]), rows[y][x])
                if cell != rows[y][x]:
                    rows[y][x], changed = cell, True
        if changed:
            write_lines(path, [":".join(r) for r in rows] + lines[21:])
            done += 1
    print("Palisades joined on %d maps" % done)


def preview(path):
    grass = Image.open(p("sprites", "Tiles", "Grass001.png")).convert("RGBA")
    layout = [[3, 7, 1, 4], [9, 11, 1, 10], [2, 2, 12, 2], [5, 8, 1, 6]]
    out = Image.new("RGBA", (S * 4, S * 4))
    sides = {n: s for n, s, _ in PIECES}
    for y, row in enumerate(layout):
        for x, n in enumerate(row):
            out.alpha_composite(grass, (x * S, y * S))
            out.alpha_composite(picture(sides[n]), (x * S, y * S))
    out.resize((out.size[0] * 4, out.size[1] * 4), Image.NEAREST).save(path)


def main():
    pictures()
    data()
    join_maps()
    print("Drew the palisade's twelve pieces")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        preview(sys.argv[1])
    else:
        main()
