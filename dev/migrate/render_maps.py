"""Render Dragon Sword maps to PNG (pure Python, no PIL) for checking layouts by eye.

Run:  python -I "dev\\migrate\\render_maps.py" [map names ...] [--out DIR] [--scale N] [--zones]
  * With map names (e.g. 4,1,0) renders each map to <out>\\<name>.png (and <name> noroof.png if it has roofs).
  * --zones also writes <out>\\<name> zones.png (no roofs) with each NPC's movement drawn faintly, one colour per
    NPC: its Zone (solid outline), Chase rectangle (dashed), patrol route (line and waypoint dots), or a box
    round the spawn tile when it stands still. Lines without Options show their Entities.ini defaults.
  * Always writes <out>\\World Z<z>.png: every map on each level stitched together (with roofs),
    at --scale (default 0.5: every second pixel).
Default out folder: dev\\Renders.
"""
import os
import re
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MAP_W, MAP_H, p, read_bmp, read_lines

TW = TH = 32
_cache = {}


def sprite(kind, name):
    key = (kind, name)
    if key not in _cache:
        path = p("sprites", kind, name + ".png")
        if not os.path.exists(path):
            _cache[key] = None
        else:
            w, h, rows = read_bmp(path)
            half = h // 2
            mask = [[sum(c) < 384 for c in r] for r in rows[:half]]
            _cache[key] = (w, half, rows[half:], mask)
    return _cache[key]


def blit(img, W, H, spr, x0, y0):
    if spr is None:
        return
    w, h, pix, mask = spr
    for y in range(h):
        yy = y0 + y
        if yy < 0 or yy >= H:
            continue
        row, mrow, dst = pix[y], mask[y], img[yy]
        for x in range(w):
            xx = x0 + x
            if 0 <= xx < W and mrow[x]:
                dst[xx] = row[x]


def parse_map(path):
    lines = read_lines(path)
    cells = [l.split(":") for l in lines[:MAP_H]]
    ents = [l.split("\t") for l in lines[MAP_H:] if l.strip()]
    return cells, ents


def draw_map(img, W, H, ox, oy, path, roofs=True, triggers=True):
    cells, ents = parse_map(path)
    over = []
    for ty, row in enumerate(cells):
        for tx, cell in enumerate(row):
            parts = cell.split("+")
            blit(img, W, H, sprite("Tiles", parts[0]), ox + tx * TW, oy + ty * TH)
            for o in parts[1:]:
                m = re.match(r"(\w+)\((.*)\)", o)
                if m and m.group(1) == "Decor":             # (part of the ground: under the entities)
                    blit(img, W, H, sprite("Tiles", m.group(2)), ox + tx * TW, oy + ty * TH)
                elif m:
                    over.append((m.group(1), m.group(2), tx, ty))
    for e in ents:
        if e[0] in ("MapItem", "StaticObject", "NPC", "GoodNPC", "BadNPC"):
            blit(img, W, H, (sprite("Entities", e[1]) or sprite("Tiles", e[1])), ox + int(float(e[2])), oy + int(float(e[3])))
        elif e[0] in ("Trigger", "Lock") and triggers:
            # triggers: a magenta frame; locks: a red frame (single-map renders only)
            col = (255, 0, 255) if e[0] == "Trigger" else (255, 40, 40)
            tx, ty = (int(e[2]) - 1, int(e[3]) - 1) if e[0] == "Trigger" else (int(e[1]) - 1, int(e[2]) - 1)
            for i in range(TW):
                for (xx, yy) in ((ox + tx * TW + i, oy + ty * TH), (ox + tx * TW + i, oy + ty * TH + TH - 1),
                                 (ox + tx * TW, oy + ty * TH + i), (ox + tx * TW + TW - 1, oy + ty * TH + i)):
                    if 0 <= xx < W and 0 <= yy < H:
                        img[yy][xx] = col
    for kind, arg, tx, ty in over:
        if kind == "Infront":
            blit(img, W, H, sprite("Tiles", arg), ox + tx * TW, oy + ty * TH)
    if roofs:
        for kind, arg, tx, ty in over:
            if kind == "Roof":
                blit(img, W, H, sprite("Tiles", arg.split(".")[0]), ox + tx * TW, oy + ty * TH)
    return any(k == "Roof" for k, _, _, _ in over)


# ------------------------------------------------------------------ NPC movement overlay (--zones)
ZONE_COLOURS = [(255, 220, 0), (0, 230, 255), (255, 90, 200), (120, 255, 80), (255, 140, 30), (170, 120, 255),
                (255, 255, 255), (60, 160, 255)]


def npc_movement(e, ents_ini):
    """(spawn, zone, chase, patrol points, stand) of an NPC map line, in 1-based tiles: the line's Options, else the
    Entities.ini defaults (Roam.Radius round the spawn tile, the zone grown by Chase.Radius), clipped to the map."""
    spr = sprite("Entities", e[1])
    w, h = (spr[0], spr[1]) if spr else (32, 32)
    sx, sy = int((float(e[2]) + w / 2) // TW) + 1, int((float(e[3]) + h - 1) // TH) + 1
    opts = dict(t.split("=", 1) for t in (e[4] if len(e) > 4 else "").split() if "=" in t)

    def num(k, d=0):
        try:
            return int(float(ents_ini.get(e[1], k, str(d))))
        except ValueError:
            return d

    def rect(v):
        try:
            r = tuple(int(q) for q in v.split(","))
            return r if len(r) == 4 else None
        except ValueError:
            return None

    def clip(r):
        return max(1, r[0]), max(1, r[1]), min(MAP_W, r[2]), min(MAP_H, r[3])
    stand = opts.get("Stand") == "1"
    roam = 0 if stand else num("Roam.Radius")
    zone = rect(opts.get("Zone", "")) or clip((sx - roam, sy - roam, sx + roam, sy + roam))
    patrol = []
    for wp in opts.get("Patrol", "").split("/"):
        try:
            x, y = (int(q) for q in wp.split(","))
            patrol.append((x, y))
        except ValueError:
            pass
    cr = num("Chase.Radius")
    chase = rect(opts.get("Chase", "")) or clip((zone[0] - cr, zone[1] - cr, zone[2] + cr, zone[3] + cr))
    return (sx, sy), zone, chase, patrol, stand


def blend(img, W, H, x, y, col, a):
    if 0 <= x < W and 0 <= y < H:
        o = img[y][x]
        img[y][x] = tuple(int(o[i] * (1 - a) + col[i] * a) for i in range(3))


def draw_rect(img, W, H, ox, oy, r, col, a, inset=0, dash=0):
    x0, y0 = ox + (r[0] - 1) * TW + inset, oy + (r[1] - 1) * TH + inset
    x1, y1 = ox + r[2] * TW - 1 - inset, oy + r[3] * TH - 1 - inset
    for t in range(2):
        for x in range(x0, x1 + 1):
            if not dash or (x // dash) % 2 == 0:
                blend(img, W, H, x, y0 + t, col, a)
                blend(img, W, H, x, y1 - t, col, a)
        for y in range(y0, y1 + 1):
            if not dash or (y // dash) % 2 == 0:
                blend(img, W, H, x0 + t, y, col, a)
                blend(img, W, H, x1 - t, y, col, a)


def draw_line(img, W, H, p0, p1, col, a):
    (x0, y0), (x1, y1) = p0, p1
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x, y = x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n
        for d in ((0, 0), (1, 0), (0, 1)):
            blend(img, W, H, x + d[0], y + d[1], col, a)


def draw_movement(img, W, H, ox, oy, path):
    """Faint outlines of each NPC's movement: its Zone (solid), Chase rectangle (dashed), patrol route (a line
    through the waypoints, back to the first unless PatrolMode=PingPong) and a box round the spawn tile of
    NPCs that stand still. One colour per NPC."""
    from common import Ini
    ents_ini = Ini(p("data", "Entities.ini"))
    _, ents = parse_map(path)
    k = 0
    for e in ents:
        if e[0] not in ("NPC", "GoodNPC", "BadNPC") or len(e) < 4:
            continue
        col = ZONE_COLOURS[k % len(ZONE_COLOURS)]
        k += 1
        (sx, sy), zone, chase, patrol, stand = npc_movement(e, ents_ini)
        inset = 2 + (k % 4) * 2          # neighbouring rectangles don't draw on top of each other
        if stand or (zone == (sx, sy, sx, sy) and not patrol):
            draw_rect(img, W, H, ox, oy, (sx, sy, sx, sy), col, 0.8, inset=1)
            continue
        if patrol:
            pts = [(ox + (x - 1) * TW + 16, oy + (y - 1) * TH + 16) for x, y in patrol]
            route = pts if "PatrolMode=PingPong" in (e[4] if len(e) > 4 else "") else pts + pts[:1]
            for a, b in zip(route, route[1:]):
                draw_line(img, W, H, a, b, col, 0.75)
            for x, y in pts:
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        blend(img, W, H, x + dx, y + dy, col, 0.8)
        else:
            draw_rect(img, W, H, ox, oy, zone, col, 0.55, inset=inset)
        if chase != zone:
            draw_rect(img, W, H, ox, oy, chase, col, 0.35, inset=inset, dash=6)


def write_png(path, img, scale=1.0):
    if scale != 1.0:
        step = int(round(1 / scale))
        img = [r[::step] for r in img[::step]]
    h, w = len(img), len(img[0])
    raw = b"".join(b"\x00" + bytes(c for px in r for c in px) for r in img)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def blank(W, H, col=(40, 0, 40)):
    return [[col] * W for _ in range(H)]


def map_names():
    out = []
    for f in os.listdir(p("maps")):
        m = re.fullmatch(r"(-?\d+),(-?\d+),(-?\d+)\.txt", f)
        if m:
            out.append(tuple(int(v) for v in m.groups()))
    return out


def main():
    args = sys.argv[1:]
    out = p("dev", "Renders")
    scale = 0.5
    zones = False
    names = []
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out = args[i + 1]; i += 2; continue
        if args[i] == "--scale":
            scale = float(args[i + 1]); i += 2; continue
        if args[i] == "--zones":
            zones = True; i += 1; continue
        names.append(args[i]); i += 1
    MW, MH = MAP_W * TW, MAP_H * TH
    for n in names:
        path = p("maps", n + ".txt")
        img = blank(MW, MH)
        has_roof = draw_map(img, MW, MH, 0, 0, path)
        write_png(os.path.join(out, n + ".png"), img)
        if has_roof:
            img = blank(MW, MH)
            draw_map(img, MW, MH, 0, 0, path, roofs=False)
            write_png(os.path.join(out, n + " noroof.png"), img)
        if zones:
            img = blank(MW, MH)
            draw_map(img, MW, MH, 0, 0, path, roofs=False)
            draw_movement(img, MW, MH, 0, 0, path)
            write_png(os.path.join(out, n + " zones.png"), img)
        print("wrote", n)
    maps = map_names()
    for z in sorted({m[2] for m in maps}):
        lv = [m for m in maps if m[2] == z]
        x0, x1 = min(m[0] for m in lv), max(m[0] for m in lv)
        y0, y1 = min(m[1] for m in lv), max(m[1] for m in lv)
        W, H = (x1 - x0 + 1) * MW, (y1 - y0 + 1) * MH
        img = blank(W, H)
        for (x, y, _) in lv:
            draw_map(img, W, H, (x - x0) * MW, (y - y0) * MH, p("maps", "%d,%d,%d.txt" % (x, y, z)), triggers=False)
        for gx in range(0, W, MW):
            for yy in range(H):
                img[yy][gx] = (255, 255, 0)
        for gy in range(0, H, MH):
            for xx in range(W):
                img[gy][xx] = (255, 255, 0)
        fn = os.path.join(out, "World Z%d.png" % z)
        write_png(fn, img, scale)
        print("wrote", fn, "origin", x0, y0)


if __name__ == "__main__":
    main()
