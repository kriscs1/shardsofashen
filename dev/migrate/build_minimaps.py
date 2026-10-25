"""Rebuild the minimap sprites (the editor's Minimaps section runs this; it does what the old MiniMap Creator's [MC.Create] button did).

Run:  python -I "dev\\migrate\\build_minimaps.py" [--pixel-size N] [--levels Z,Z...]

For every level Z that has maps (maps\\X,Y,Z.txt, not sub-folders) it writes sprites\\Interface\\Minimap<Z>.png:
  * one Pixel.Size square per map tile; the cell colour is that of the top-most layer
    (+Roof(...), then +Infront(...), then +Decor(...) if dev\\Minimap Colours.txt has a colour for it, then the
    tile), from dev\\Minimap Colours.txt ("R G B" or an LB colour name);
    a tile with no colour gets the average visible colour of its sprite (24/32-bit sprites; otherwise black);
    a tile with no sprite is magenta; an empty cell is black;
  * a 24-bit double-height LB sprite: top half the mask (black = drawn), bottom half the image;
    places with no map file are transparent (white mask, black image);
  * data\\Config.ini [Minimap] Pixel.Size=n and Origin.<Z>=X,Y (the map at the top-left), written the way
    WritePrivateProfileString does (existing keys changed in place, a missing section appended).
Pixel size: --pixel-size, else Config [Minimap] Pixel.Size, else 1 (what the Creator's textbox starts with).
Unlike the Creator it never asks to write worked-out colours back to dev\\Minimap Colours.txt.
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENC, p, read_bmp, read_lines

NAMED = {"white": (255, 255, 255), "black": (0, 0, 0), "lightgray": (192, 192, 192), "palegray": (192, 192, 192),
         "darkgray": (128, 128, 128), "red": (255, 0, 0), "darkred": (128, 0, 0), "pink": (255, 0, 255),
         "darkpink": (128, 0, 128), "blue": (0, 0, 255), "darkblue": (0, 0, 128), "green": (0, 255, 0),
         "darkgreen": (0, 128, 0), "cyan": (0, 255, 255), "darkcyan": (0, 128, 128), "yellow": (255, 255, 0),
         "brown": (128, 128, 0), "buttonface": (212, 208, 200)}


def ini_get(path, section, key, default=""):
    sec = None
    for line in read_lines(path):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].strip().lower()
        elif sec == section.lower() and "=" in s and not s.startswith(";"):
            k, v = s.split("=", 1)
            if k.strip().lower() == key.lower():
                return v.strip()
    return default


def ini_set(path, section, key, value):
    """WritePrivateProfileString: replace key=value in its section, else add it at the end of the section,
    else append the section at the end of the file."""
    lines = read_lines(path)
    while lines and lines[-1] == "":
        lines.pop()
    sec, start, end = None, None, None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if sec == section.lower():
                end = i
                break
            sec = s[1:-1].strip().lower()
            if sec == section.lower():
                start = i
        elif sec == section.lower() and "=" in s and not s.startswith(";"):
            if s.split("=", 1)[0].strip().lower() == key.lower():
                lines[i] = "%s=%s" % (key, value)
                return _save(path, lines)
    if start is None:
        lines += ["", "[%s]" % section, "%s=%s" % (key, value)]
    else:
        if end is None:
            end = len(lines)
        while end > start + 1 and lines[end - 1].strip() == "":
            end -= 1
        lines.insert(end, "%s=%s" % (key, value))
    return _save(path, lines)


def _save(path, lines):
    data = "".join(l + "\r\n" for l in lines).encode(ENC)
    with open(path, "rb") as f:
        if f.read() == data:
            return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def parse_colour(text):
    text = text.strip()
    if not text:
        return None
    parts = text.split()
    if len(parts) > 1:
        if len(parts) != 3 or not all(re.fullmatch(r"-?\d+", v) for v in parts):
            return None
        vals = [int(v) for v in parts]
        if any(v < 0 or v > 255 for v in vals):
            return None
        return tuple(vals)
    return NAMED.get(text.lower())


def average_colour(name):
    path = p("sprites", "Tiles", name + ".png")
    w, h, rows = read_bmp(path)
    half = h // 2
    vis, allp = [], []
    for y in range(half):
        for x in range(w):
            c = rows[half + y][x]
            allp.append(c)
            if sum(rows[y][x]) < 384:
                vis.append(c)
    src = vis or allp
    return tuple(int(sum(c[i] for c in src) / len(src)) for i in range(3))


def tile_colours():
    tiles = sorted(f[:-4] for f in os.listdir(p("sprites", "Tiles")) if f.lower().endswith(".png") and f[:-4] != "Thumb")
    colours = {}
    path = p("dev", "Minimap Colours.txt")
    if os.path.exists(path):
        for line in read_lines(path):
            if not line.strip():
                continue
            if "\t" in line:
                name, col = line.split("\t")[0].strip(), line.split("\t")[1].strip()
            else:
                name = line.split()[0]
                col = line.strip()[len(name):].strip()
            if name in tiles:
                c = parse_colour(col)
                if c is not None:
                    colours[name] = c
                else:
                    print("%s: invalid colour '%s'" % (name, col))
    EXPLICIT.update(colours)
    for t in tiles:
        if t not in colours:
            c = average_colour(t)
            colours[t] = c if c is not None else (0, 0, 0)
            print("%s: no colour in dev\\Minimap Colours.txt, using %d %d %d" % ((t,) + colours[t]))
    return colours


EXPLICIT = set()       # the tiles dev\Minimap Colours.txt gives a colour (tile_colours)


def top_tile(cell):
    """The tile whose colour a cell shows: its roof, tree top, decor (only one with its own colour: a tree, not the
    flowers on the grass) or ground tile."""
    parts = cell.split("+")
    base, roof, infront, decor, under = parts[0].strip(), "", "", "", ""
    for o in parts[1:]:
        inner = o[o.find("(") + 1:] if "(" in o else o
        if inner.endswith(")"):
            inner = inner[:-1]
        if o.lower().startswith("roof("):
            roof = inner.split(".")[0]
        if o.lower().startswith("infront("):
            infront = inner
        if o.lower().startswith("decor(") and inner in EXPLICIT:
            decor = inner
        if o.lower().startswith("under(") and inner in EXPLICIT:
            under = inner
    return roof or infront or decor or under or base


def write_minimap(path, cells, wide, high, ps):
    """A PNG: each cell ps x ps pixels, see-through where there's no map."""
    from common import write_sprite
    pic = [[(0, 0, 0) if c is None else c for c in row for _ in range(ps)] for row in cells for _ in range(ps)]
    mask = [[(255, 255, 255) if c is None else (0, 0, 0) for c in row for _ in range(ps)] for row in cells for _ in range(ps)]
    return write_sprite(path, mask + pic)


def write_minimap_bmp(path, cells, wide, high, ps):
    width, height = wide * ps, high * ps * 2
    row_size = (width * 3 + 3) // 4 * 4
    pad = b"\0" * (row_size - width * 3)
    body = []
    for half in (1, 2):                                  # image rows first: BMP rows are bottom-up
        for cy in range(high - 1, -1, -1):
            row = b""
            for cx in range(wide):
                c = cells[cy][cx]
                if half == 1:
                    px = b"\0\0\0" if c is None else bytes((c[2], c[1], c[0]))
                else:
                    px = b"\xff\xff\xff" if c is None else b"\0\0\0"
                row += px * ps
            body.append((row + pad) * ps)
    data = b"".join(body)
    head = b"BM" + struct.pack("<IIi", 54 + len(data), 0, 54)
    head += struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(head + data)


def main():
    config = p("data", "Config.ini")
    mw = int(ini_get(config, "Interface", "Map.X.Tiles", "25") or 25) or 25
    mh = int(ini_get(config, "Interface", "Map.Y.Tiles", "21") or 21) or 21
    ps = int(float(ini_get(config, "Minimap", "Pixel.Size", "1") or 1))
    if "--pixel-size" in sys.argv:
        ps = int(sys.argv[sys.argv.index("--pixel-size") + 1])
    ps = max(1, ps)
    colours = tile_colours()
    maps = []
    for f in os.listdir(p("maps")):
        m = re.fullmatch(r"(-?\d+),(-?\d+),(-?\d+)\.txt", f)
        if m and os.path.isfile(p("maps", f)):
            maps.append(tuple(int(v) for v in m.groups()))
    only = None
    if "--levels" in sys.argv:          # (the editor's Minimaps section: just these levels, e.g. --levels 0,-1)
        only = {int(v) for v in sys.argv[sys.argv.index("--levels") + 1].split(",") if v.strip()}
    for z in sorted({m[2] for m in maps}):
        if only is not None and z not in only:
            continue
        lv = [m for m in maps if m[2] == z]
        sx, ex = min(m[0] for m in lv), max(m[0] for m in lv)
        sy, ey = min(m[1] for m in lv), max(m[1] for m in lv)
        wide, high = (ex - sx + 1) * mw, (ey - sy + 1) * mh
        cells = [[None] * wide for _ in range(high)]
        for (x, y, _) in lv:
            lines = read_lines(p("maps", "%d,%d,%d.txt" % (x, y, z)))
            ox, oy = (x - sx) * mw, (y - sy) * mh
            for ty in range(mh):
                line = lines[ty] if ty < len(lines) else ""
                words = line.split(":")
                for tx in range(mw):
                    name = top_tile(words[tx]) if tx < len(words) else ""
                    if name == "":
                        c = (0, 0, 0)
                    elif name in colours:
                        c = colours[name]
                    else:
                        c = (255, 0, 255)
                        print("Unknown tile '%s' in %d,%d,%d.txt (drawn magenta)" % (name, x, y, z))
                    cells[oy + ty][ox + tx] = c
        out = p("sprites", "Interface", "Minimap%d.png" % z)
        write_minimap(out, cells, wide, high, ps)
        ini_set(config, "Minimap", "Pixel.Size", str(ps))
        ini_set(config, "Minimap", "Origin.%d" % z, "%d,%d" % (sx, sy))
        print("Minimap%d.png: maps %d,%d to %d,%d (%d x %d pixels)" % (z, sx, sy, ex, ey, wide * ps, high * ps))
    print("Wrote [Minimap] Pixel.Size and Origin.<Z> to data\\Config.ini")


if __name__ == "__main__":
    main()
