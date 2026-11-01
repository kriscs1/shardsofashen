"""Drawing a map to a picture (PIL): its tiles, decor, roofs, tree tops and entities, as the editor shows them."""
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


def ground_image(project, name, gx, gy):
    """A ground tile at world tile gx, gy: its part of its big texture (Tiles.ini Texture=, sprites\\Textures) when
    it has one, as the game paints it (so a range or a forest is one picture, whichever of its tiles was put down), else
    its own sprite."""
    base = project.tiles_ini.get(name, "Corner.Base", "")
    if base:
        return _corner_piece(project, name, base, gx, gy)
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


def _corner_piece(project, name, base, gx, gy):
    """A piece where two grounds meet on the slant (Tiles.ini Corner.*, build_ground_pieces.py): its base, and its
    corners' land, each from its own ground at this tile (as ground.js paints it)."""
    tw, th = project.tile_w, project.tile_h
    land = project.tiles_ini.get(name, "Corner.Land", "")
    key = (id(project), "corner", name, gx, gy)       # (where it is: the textures under it carry on unbroken)
    if key not in _tile_cache:
        out = ground_image(project, base, gx, gy).copy()
        cut = Image.new("L", (tw, th), 0)
        d = ImageDraw.Draw(cut)
        try:
            leg = float(project.tiles_ini.get(name, "Corner.Leg", "1") or 1)
        except ValueError:
            leg = 1.0
        for c in (project.tiles_ini.get(name, "Corner.Mask", "") or "").split(","):
            at = CORNER_AT.get(c.strip())
            if at is None:
                continue
            cx, cy = at[0] * tw, at[1] * th
            sx, sy = (-1 if at[0] else 1), (-1 if at[1] else 1)
            d.polygon([(cx, cy), (cx + sx * tw * leg, cy), (cx, cy + sy * th * leg)], fill=255)
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
           decor=True, origin=None):
    """ground=False: transparent where there's nothing but ground (a layer to put over another picture). decor: the
    see-through tiles over the ground (they're part of it, as in the game). origin: the world tile of the map's
    top-left, for the tiles painted from a texture."""
    tw, th = project.tile_w, project.tile_h
    W, H = project.map_w, project.map_h
    im = Image.new("RGBA", (W * tw, H * th), (0, 0, 0, 255 if ground else 0))
    if ground:
        for y, row in enumerate(doc.cells):
            for x, cell in enumerate(row):
                im.paste(tile_image(project, cell.tile) if origin is None else
                         ground_image(project, cell.tile, origin[0] + x, origin[1] + y), (x * tw, y * th))
        _raised_turns(project, doc, im, origin)
        _raised_shadows(project, doc, im)
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


def _raised_turns(project, doc, im, origin):
    """A boardwalk running east and west: its planks across the way, turned a quarter (as ground.js draws it)."""
    tw, th = project.tile_w, project.tile_h
    raised = lambda x, y: (0 <= y < len(doc.cells) and 0 <= x < len(doc.cells[y]) and          # noqa: E731
                           project.tiles_ini.get(doc.cells[y][x].tile, "Raised", "") == "1")
    for y, row in enumerate(doc.cells):
        for x, cell in enumerate(row):
            if raised(x, y) and not raised(x, y - 1) and not raised(x, y + 1) and (raised(x - 1, y) or raised(x + 1, y)):
                pic = tile_image(project, cell.tile) if origin is None else                     ground_image(project, cell.tile, origin[0] + x, origin[1] + y)
                im.paste(pic.rotate(-90), (x * tw, y * th))


def _raised_shadows(project, doc, im):
    """What's raised off the ground (Tiles.ini Raised=1: a boardwalk) casts its shadow south and east of it, as the
    game draws it (ground.js paintRaised), and shows its front edge."""
    tw, th = project.tile_w, project.tile_h
    raised = lambda x, y: (0 <= y < len(doc.cells) and 0 <= x < len(doc.cells[y]) and          # noqa: E731
                           project.tiles_ini.get(doc.cells[y][x].tile, "Raised", "") == "1")
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
