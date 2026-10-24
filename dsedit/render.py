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


def forget_tiles():
    _tile_cache.clear()


def render(project, doc, roofs=True, infront=True, entities=True, dim_roofs=False, only_rows=None, ground=True,
           decor=True):
    """ground=False: transparent where there's nothing but ground (a layer to put over another picture). decor: the
    see-through tiles over the ground (they're part of it, as in the game)."""
    tw, th = project.tile_w, project.tile_h
    W, H = project.map_w, project.map_h
    im = Image.new("RGBA", (W * tw, H * th), (0, 0, 0, 255 if ground else 0))
    if ground:
        for y, row in enumerate(doc.cells):
            for x, cell in enumerate(row):
                im.paste(tile_image(project, cell.tile), (x * tw, y * th))
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
