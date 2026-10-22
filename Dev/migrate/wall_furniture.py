"""Furniture against the walls. The furnishing puts bookshelves, beds and plants on the floor a tile in from the walls
(the walls were whole tiles then); with thin walls (build_content.thin_walls) that leaves an empty strip round the
room and everything bunched in the middle. So a bookshelf, a plant or a bed's head next to a thin wall moves onto
it: a tile of both, the furniture standing in front of the wall strip (<Family>_<thin wall tile>, e.g.
Bookshelf_Brick_Thin_Plank001), drawn here as the maps are built (only the ones used), and the floor it left behind
is clear. Run as a build_world ROOF_HOOK after the thin walls and furniture_floors."""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import p  # noqa: E402
from farm_tiles import tile_array, to_rows  # noqa: E402

AGAINST = {"Bookshelf": ("N", "W", "E"), "Potted_Plant": ("N", "W", "E"), "Bed": ("N",),
           "Shelf_Goods": ("N", "W", "E"), "Herb_Rack": ("N", "W", "E"), "Potion_Shelf": ("N", "W", "E"),
           "Nets": ("N", "W", "E")}
FACING = {"N": "S", "S": "N", "W": "E", "E": "W"}
STEP = {"N": (0, -1), "S": (0, 1), "W": (-1, 0), "E": (1, 0)}
THIN = re.compile(r"(\w+?)_Thin_(Plank|Tile|Marble)(\d{3})$")
FLOORS = {"Plank": "Plank001", "Tile": "Tile001", "Marble": "Marble001"}
MADE = {}               # combined tile -> (furniture tile, thin wall tile): its sprite is written, Tiles.ini entry made


def family(tile):
    """("Bookshelf", "Bookshelf101") for a furniture tile that goes against a wall (Bed: only its head), else None."""
    m = re.fullmatch(r"(Bookshelf|Potted_Plant|Bed|Shelf_Goods|Herb_Rack|Potion_Shelf|Nets)(\d)(\d\d)", tile)
    if not m or (m.group(1) == "Bed" and m.group(3) != "01"):
        return None
    return m.group(1)


def edges_of(thin):
    import house_tiles as H
    m = THIN.match(thin)
    return H.THIN_EDGES[int(m.group(3)) - 1] if m else None


def combined(furniture, thin, C):
    """The tile of furniture standing against the thin wall: drawn now if new."""
    name = "%s_%s" % (family(furniture), thin)
    if name not in MADE:
        import build_tiles
        import interior_tiles
        floor = FLOORS[THIN.match(thin).group(2)]
        furniture = family(furniture) + "001" if family(furniture) != "Bed" else "Bed001"
        if floor in interior_tiles.FURNITURE_FLOORS:            # (the piece drawn on the wall's own floor)
            furniture = interior_tiles.furniture_on(furniture, floor)
        wall = tile_array(p("Sprites", "Tiles", thin + ".png"))
        furn = tile_array(p("Sprites", "Tiles", furniture + ".png"))
        ground = tile_array(p("Sprites", "Tiles", floor + ".png"))
        img = wall.copy()
        mask = np.abs(furn - ground).sum(2) > 30               # the furniture itself, without its floor
        img[mask] = furn[mask]
        build_tiles.write_sprite_bmp(p("Sprites", "Tiles", name + ".png"), to_rows(img))
        MADE[name] = (furniture, thin)
        f, t = C.TILES.get(re.sub(r"\d{3}$", "001", furniture)), C.TILES.get(thin)
        walk = "".join("1" if a == b == "1" else "0" for a, b in zip(f[0], t[0])) if f and t else "0" * 49
        C.TILES[name] = (walk, "1", "", f[3] if f else None, "0", None)
    return name


def wall_furniture(cells, C=None):
    if C is None:
        C = sys.modules.get("build_content")
    h, w = len(cells), len(cells[0])

    def base(c):
        return c.split("+")[0]

    def rest(c):
        return c[len(base(c)):]
    for y in range(h):
        for x in range(w):
            t = base(cells[y][x])
            fam = family(t)
            if not fam:
                continue
            for side in AGAINST[fam]:
                dx, dy = STEP[side]
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                thin = base(cells[ny][nx])
                e = edges_of(thin)
                if e is None or FACING[side] in e:                  # (the wall strip must be on its far side)
                    continue
                floor = {"1": "Tile001", "2": "Marble001"}.get(t[-3], "Plank001")   # (what it stood on)
                if fam == "Bed":
                    if not (y + 1 < h and base(cells[y + 1][x]).startswith("Bed") and
                            base(cells[y + 1][x]).endswith("02")):
                        continue
                    foot = base(cells[y + 1][x])
                    cells[ny][nx] = combined(t, thin, C) + rest(cells[ny][nx])
                    cells[y][x] = foot + rest(cells[y][x])
                    cells[y + 1][x] = floor + rest(cells[y + 1][x])
                else:
                    cells[ny][nx] = combined(t, thin, C) + rest(cells[ny][nx])
                    cells[y][x] = floor + rest(cells[y][x])
                break
