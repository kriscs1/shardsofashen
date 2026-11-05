"""Drawing a map to a picture (PIL): its tiles, decor, roofs, tree tops and entities, as the editor shows them."""
import re

from PIL import Image, ImageDraw

_tile_cache = {}


def tile_image(project, name):
    """A tile sprite on an opaque square (the ground is painted solid in the game)."""
    key = (id(project), name)
    if key not in _tile_cache:
        img = project.sprite("Tiles", name)
        tw, th = project.tile_w, project.tile_h
        sq = Image.new("RGBA", (tw, th), (255, 0, 255, 255) if img is None else (0, 0, 0, 255))
        if img is not None:
            sq.paste(img, (0, 0), img)
        _tile_cache[key] = sq
    return _tile_cache[key]


def ground_image(project, name, gx, gy, near=None):
    """A ground tile at world tile gx, gy: its part of its big texture (Tiles.ini Texture=, sprites\\Textures) when
    it has one, as the game paints it (so a range or a forest is one picture, whichever of its tiles was put down), else
    its own sprite."""
    base = project.tile_values("Corner.Base").get(name.lower())
    if base:
        return _corner_piece(project, name, base, gx, gy, near)
    tex = project.tile_values("Texture").get(name.lower())
    big = _texture(project, tex) if tex else None
    if big is None:
        return tile_image(project, name)
    tw, th = project.tile_w, project.tile_h
    sx, sy = (gx * tw) % big.size[0], (gy * th) % big.size[1]
    key = (id(project), "tex", tex, sx, sy)
    if key not in _tile_cache:
        sq = Image.new("RGBA", (tw, th), (0, 0, 0, 255))
        sq.alpha_composite(big.crop((sx, sy, sx + tw, sy + th)))
        _tile_cache[key] = sq
    return _tile_cache[key]


CORNER_AT = {"NE": (1, 0), "SE": (1, 1), "SW": (0, 1), "NW": (0, 0)}
CORNER_K = {"NE": 0, "SE": 1, "SW": 2, "NW": 3}
# (a corner's two tips: the neighbour whose corner runs on from it, and which way its land is thickened: ground.js TIPS)
TIPS = [[(-1, 0, "NW", 0, 1), (0, 1, "SE", 1, 0)], [(0, -1, "NE", 1, 0), (-1, 0, "SW", 0, 1)],
        [(1, 0, "SE", 0, 1), (0, -1, "NW", 1, 0)], [(0, 1, "SW", 1, 0), (1, 0, "NE", 0, 1)]]
JOIN = 0.4


def _corner_poly(k, tw, th, leg, joins):
    """The land of corner k: a triangle, or where a tip meets its neighbour's, thickened there and curved between."""
    c = [(tw, 0), (tw, th), (0, th), (0, 0)][k]
    a = [(0, 0), (tw, 0), (tw, th), (0, th)][k]
    b = [(tw, th), (0, th), (0, 0), (tw, 0)][k]
    if not any(joins):
        a = (c[0] + (a[0] - c[0]) * leg, c[1] + (a[1] - c[1]) * leg)
        b = (c[0] + (b[0] - c[0]) * leg, c[1] + (b[1] - c[1]) * leg)
        return [c, a, b]

    def ext(tip, t):
        _, _, _, ix, iy = TIPS[k][t]
        return (tip[0] + (-1 if tip[0] else 1) * ix * tw * JOIN, tip[1] + (-1 if tip[1] else 1) * iy * th * JOIN)
    ea, eb = (ext(a, 0) if joins[0] else a), (ext(b, 1) if joins[1] else b)
    m = ((a[0] + b[0]) / 2 + (c[0] - (a[0] + b[0]) / 2) * 0.1, (a[1] + b[1]) / 2 + (c[1] - (a[1] + b[1]) / 2) * 0.1)
    curve = [((1 - t) ** 2 * ea[0] + 2 * (1 - t) * t * m[0] + t * t * eb[0],
              (1 - t) ** 2 * ea[1] + 2 * (1 - t) * t * m[1] + t * t * eb[1]) for t in (i / 10.0 for i in range(11))]
    return [c, a] + curve + [b]


def _corner_piece(project, name, base, gx, gy, near=None):
    """A piece where two grounds meet on the slant (Tiles.ini Corner.*, build_ground_pieces.py): its base, and its
    corners' land, each from its own ground at this tile (as ground.js paints it); near(dx, dy): the tile beside it,
    for the corners that round into a neighbour's."""
    tw, th = project.tile_w, project.tile_h
    land = project.tiles_ini.get(name, "Corner.Land", "")
    try:
        leg = float(project.tiles_ini.get(name, "Corner.Leg", "1") or 1)
    except ValueError:
        leg = 1.0
    mask = [c.strip() for c in (project.tiles_ini.get(name, "Corner.Mask", "") or "").split(",") if c.strip() in CORNER_K]

    def joined(k):
        if leg < 1 or near is None:
            return (False, False)
        out = []
        for ox, oy, want, _, _ in TIPS[k]:
            o = near(ox, oy) or ""
            try:
                oleg = float(project.tiles_ini.get(o, "Corner.Leg", "0") or 0)
            except ValueError:
                oleg = 0
            out.append(oleg >= 1 and want in (project.tiles_ini.get(o, "Corner.Mask", "") or "").split(","))
        return tuple(out)
    joins = tuple(joined(CORNER_K[c]) for c in mask)
    key = (id(project), "corner", name, gx, gy, joins)   # (where it is: the textures under it carry on unbroken)
    if key not in _tile_cache:
        out = ground_image(project, base, gx, gy).copy()
        cut = Image.new("L", (tw, th), 0)
        d = ImageDraw.Draw(cut)
        for c, j in zip(mask, joins):
            d.polygon(_corner_poly(CORNER_K[c], tw, th, leg, j), fill=255)
        if land:
            out.paste(ground_image(project, land, gx, gy), (0, 0), cut)
        _tile_cache[key] = out
    return _tile_cache[key]


def _texture(project, tex):
    key = (id(project), "texture", tex)
    if key not in _tile_cache:
        img = project.sprite("Textures", tex)
        _tile_cache[key] = img.convert("RGBA") if img is not None else None
    return _tile_cache[key]


def forget_tiles():
    _tile_cache.clear()


def render(project, doc, roofs=True, infront=True, entities=True, dim_roofs=False, only_rows=None, ground=True,
           decor=True, origin=None, around=None):
    """ground=False: transparent where there's nothing but ground (a layer to put over another picture). decor: the
    see-through tiles over the ground (they're part of it, as in the game). origin: the world tile of the map's
    top-left, for the tiles painted from a texture. around(gx, gy): the tile at a world tile off this map (so the
    ground rounds into its neighbours' across the edge), None if it isn't known."""
    tw, th = project.tile_w, project.tile_h
    W, H = len(doc.cells[0]), len(doc.cells)            # (a map; or an area cut or copied, any size)
    im = Image.new("RGBA", (W * tw, H * th), (0, 0, 0, 255 if ground else 0))
    if ground:
        for y, row in enumerate(doc.cells):
            for x, cell in enumerate(row):
                near = lambda ox, oy, x=x, y=y: _tile_at(doc, x + ox, y + oy, origin, around)     # noqa: E731
                im.paste(tile_image(project, cell.tile) if origin is None else
                         ground_image(project, cell.tile, origin[0] + x, origin[1] + y, near), (x * tw, y * th))
        if origin is not None:
            _rounds(project, doc, im, origin, around)
        _raised_turns(project, doc, im, origin, around)
        _raised_shadows(project, doc, im, origin, around)
    if decor:
        for y, row in enumerate(doc.cells):
            for x, cell in enumerate(row):
                if cell.under:                     # (a rug first: the decor stands on it)
                    spr = project.sprite("Tiles", cell.under)
                    if spr is not None:
                        im.alpha_composite(spr.convert("RGBA"), (x * tw, y * th))
                if cell.decor:
                    spr = project.sprite("Tiles", cell.decor)
                    if spr is not None:
                        im.alpha_composite(spr.convert("RGBA"), (x * tw, y * th))
    if entities:
        ents = [e for e in doc.placed() if e.kind in ("MapItem", "StaticObject", "NPC")]
        ents.sort(key=lambda e: (e.kind != "MapItem", e.y + (project.sprite("Entities", e.name).size[1]
                                                              if project.sprite("Entities", e.name) else 32)))
        for e in ents:
            spr = project.sprite("Entities", e.name)
            if spr is not None:
                im.paste(spr, (int(e.x), int(e.y)), spr)       # (clips at the map's edges)
    for y, row in enumerate(doc.cells):
        for x, cell in enumerate(row):
            if infront and cell.infront:
                spr = project.sprite("Tiles", cell.infront)
                if spr is not None:
                    im.paste(spr, (x * tw, y * th), spr)
            if roofs and cell.roof:
                spr = project.sprite("Tiles", cell.roof)
                if spr is not None:
                    if dim_roofs:
                        spr = spr.copy()
                        a = spr.getchannel("A").point(lambda v: v * 45 // 100)
                        spr.putalpha(a)
                    im.paste(spr, (x * tw, y * th), spr)
    return im


# ----- where natural grounds meet: rounded at every corner of the grid from the four cells round it (Tiles.ini
# Round=1), as ground.js paintRounds draws it
QUAD = [(1, -1), (1, 1), (-1, 1), (-1, -1)]


def _round_of(project, name):
    key = (id(project), "round", name)
    if key not in _tile_cache:
        on = (bool(name) and project.tiles_ini.get(name, "Round", "") == "1" and
              not project.tiles_ini.get(name, "Corner.Base", ""))
        try:
            rank = max(0, min(9, int(project.tiles_ini.get(name, "Blend", "0") or 0)))
        except ValueError:
            rank = 0
        _tile_cache[key] = (re.sub(r"\d+$", "", name) if on else "", rank)
    return _tile_cache[key]


def round_fills(project, get, x, y):
    """[(corner 0-3, the tile whose ground fills it)] of the cell at x, y; get(x, y): a tile name or None."""
    me, mine = _round_of(project, get(x, y) or "")
    if not me:
        return []
    out = []
    for k, (sx, sy) in enumerate(QUAD):
        an, bn, dn = get(x + sx, y), get(x, y + sy), get(x + sx, y + sy)
        a, ar = _round_of(project, an or "")
        b, _ = _round_of(project, bn or "")
        d, _ = _round_of(project, dn or "")
        if not a or a != b or a == me:
            continue
        if d == me and (ar < mine or (ar == mine and a < me)):
            continue
        out.append((k, an))
    return out


def round_poly(k, tw, th, vx, vy):
    """The corner's fill: from the corner to the middle of its two edges, a curve between that runs on from each,
    pulled toward the corner by the grid corner's own amount (the same hash as ground.js roundPath). The game's curve
    runs round the bands a higher ground lays over the edges; the editor draws no bands, so no inset here."""
    c = [(tw, 0), (tw, th), (0, th), (0, 0)][k]
    p, q = (tw / 2, c[1]), (c[0], th / 2)
    h = (((vx * 73856093) & 0xffffffff) ^ ((vy * 19349663) & 0xffffffff)) & 0xffffffff
    pull = 0.4 + (h % 1000) / 1000.0 * 0.3
    a = (p[0] + (c[0] - p[0]) * pull, p[1] + (c[1] - p[1]) * pull)
    b = (q[0] + (c[0] - q[0]) * pull, q[1] + (c[1] - q[1]) * pull)
    curve = [tuple((1 - t) ** 3 * p[i] + 3 * (1 - t) ** 2 * t * a[i] + 3 * (1 - t) * t * t * b[i] + t ** 3 * q[i]
                   for i in (0, 1)) for t in (j / 12.0 for j in range(13))]
    return [c] + curve


def _rounds(project, doc, im, origin, around):
    tw, th = project.tile_w, project.tile_h
    H, W = len(doc.cells), len(doc.cells[0]) if doc.cells else 0

    def get(x, y):
        if 0 <= y < H and 0 <= x < W:
            return doc.cells[y][x].tile
        return around(origin[0] + x, origin[1] + y) if around else None
    for y in range(H):
        for x in range(W):
            fills = round_fills(project, get, x, y)
            if not fills:
                continue
            gx, gy = origin[0] + x, origin[1] + y
            for k, other in fills:
                sx, sy = QUAD[k]
                cut = Image.new("L", (tw, th), 0)
                ImageDraw.Draw(cut).polygon(round_poly(k, tw, th, gx + (sx > 0), gy + (sy > 0)), fill=255)
                im.paste(ground_image(project, other, gx, gy), (x * tw, y * th), cut)


def _tile_at(doc, x, y, origin, around):
    """The tile at x, y of a map; off its edges, the map beside it's (around), so nothing looks like it stops there."""
    if 0 <= y < len(doc.cells) and 0 <= x < len(doc.cells[y]):
        return doc.cells[y][x].tile
    return around(origin[0] + x, origin[1] + y) if around and origin is not None else None


def _raised_test(project, doc, origin, around):
    high = project.tile_values("Raised")
    return lambda x, y: high.get((_tile_at(doc, x, y, origin, around) or "").lower()) == "1"


def _raised_turns(project, doc, im, origin, around=None):
    """A boardwalk running east and west: its planks across the way, turned a quarter (as ground.js draws it)."""
    tw, th = project.tile_w, project.tile_h
    raised = _raised_test(project, doc, origin, around)
    for y, row in enumerate(doc.cells):
        for x, cell in enumerate(row):
            if raised(x, y) and not raised(x, y - 1) and not raised(x, y + 1) and (raised(x - 1, y) or raised(x + 1, y)):
                pic = tile_image(project, cell.tile) if origin is None else                     ground_image(project, cell.tile, origin[1] + y, -(origin[0] + x))     # (carrying on along the run)
                im.paste(pic.rotate(-90), (x * tw, y * th))


def _raised_shadows(project, doc, im, origin=None, around=None):
    """What's raised off the ground (Tiles.ini Raised=1: a boardwalk) casts its shadow south and east of it, as the
    game draws it (ground.js paintRaised), and shows its front edge: over the maps' edges as anywhere (a boardwalk
    running on into the next map has no front here, and one coming from the last map casts its shadow on this)."""
    tw, th = project.tile_w, project.tile_h
    raised = _raised_test(project, doc, origin, around)
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for y, row in enumerate(doc.cells):
        for x, _ in enumerate(row):
            if raised(x, y):
                if not raised(x, y + 1):
                    d.rectangle((x * tw, y * th + th - 3, x * tw + tw - 1, y * th + th - 1), fill=(34, 24, 16, 230))
                continue
            for k in range(8 if raised(x, y - 1) else 0):
                d.line((x * tw, y * th + k, x * tw + tw - 1, y * th + k), fill=(10, 8, 6, int(128 * (1 - k / 8.0))))
            for k in range(5 if raised(x - 1, y) else 0):
                d.line((x * tw + k, y * th, x * tw + k, y * th + th - 1), fill=(10, 8, 6, int(100 * (1 - k / 5.0))))
    im.alpha_composite(over)


def walk_overlay(project, doc):
    """Red where the tiles can't be walked on (Tiles.ini Walkable.Data: the tile's and its decor's)."""
    tw, th = project.tile_w, project.tile_h
    W, H = project.map_w, project.map_h
    im = Image.new("RGBA", (W * tw, H * th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cache = {}

    def walk(name):
        if name not in cache:
            cache[name] = project.tiles_ini.get(name, "Walkable.Data", "") or "1" * 49
        return cache[name]
    for y, row in enumerate(doc.cells):
        for x, cell in enumerate(row):
            data = walk(cell.tile)
            if cell.decor:
                over = walk(cell.decor)
                if len(over) == len(data):
                    data = "".join("1" if a == "1" and b == "1" else "0" for a, b in zip(data, over))
            r = int(round(len(data) ** 0.5)) or 7   # (objects' footprints: below)
            cw, ch = tw / r, th / r
            for i, v in enumerate(data[:r * r]):
                if v == "0":
                    cx, cy = x * tw + (i % r) * cw, y * th + (i // r) * ch
                    d.rectangle((cx, cy, cx + cw - 1, cy + ch - 1), fill=(220, 40, 30, 110))
    for e in doc.placed():                      # objects' footprints (Entities.ini Walkable.Data over the sprite)
        if e.kind != "StaticObject":
            continue
        spr = project.sprite("Entities", e.name)
        if spr is None:
            continue
        ini = project.tiles_ini if project.is_decor_object(e.name) else project.entities_ini
        data = ini.get(e.name, "Walkable.Data", "")
        w, h = spr.size
        cols, rows = max(1, round(w * 7 / tw)), max(1, round(h * 7 / th))
        if "0" not in data or len(data) != cols * rows:
            continue
        cw, ch = w / cols, h / rows
        for i, v in enumerate(data):
            if v == "0":
                cx, cy = e.x + (i % cols) * cw, e.y + (i // cols) * ch
                d.rectangle((cx, cy, cx + cw - 1, cy + ch - 1), fill=(240, 140, 30, 130))
    return im
