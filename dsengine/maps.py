"""One map of the world as the server keeps it: its tiles, decor, roofs, tree tops, triggers, locks and named tiles,
the lines that place its NPCs, items and objects, and its walk grid.

Maps sit side by side on a grid per level: map "X,Y,Z" covers global pixels X*sw .. X*sw+sw-1 and Y*sh .. on level Z,
so a point anywhere in the world is (z, x, y) and nothing moves when you walk over a seam. Cells are numbered as in the
desktop game: tile x,y (1-based) is cell (y-1)*xt+x."""
from dragonsword.lb import val, word, field, trim

ENTITY_LINE_TYPES = ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject", "Object", "Static")


class Lock:
    """A map's Lock line: tile x,y is locked unless condition is true (for the player asking: it reads their
    attributes and items). closed = the tile as the map has it, opened = Tiles.ini Unlocked.Tile ("" = the same)."""
    __slots__ = ("n", "x", "y", "condition", "message", "closed", "opened")

    def __init__(self, n, x, y, condition, message, closed, opened):
        self.n, self.x, self.y = n, x, y
        self.condition, self.message = condition, message or "It's locked."
        self.closed, self.opened = closed, opened


class MapData:
    def __init__(self, data, name, lines=None):
        """lines: the map's text, when it isn't a file in Maps (a homestead: homes.py)."""
        self.data = data
        self.name = name
        self.mx = int(val(word(name, 1, ",")))
        self.my = int(val(word(name, 2, ",")))
        self.mz = int(val(word(name, 3, ",")))
        self.ox = self.mx * data.sw
        self.oy = self.my * data.sh
        xt, yt = data.xt, data.yt
        n = xt * yt + 1
        self.tile = [""] * n
        self.decor = [""] * n
        self.under = [""] * n           # (flat things on the floor, under the decor: rugs)
        self.roof = [""] * n
        self.roof_group = [0] * n
        self.infront = [""] * n
        self.trigger = [""] * n
        self.walk = [""] * n
        self.los = [1] * n
        self.speed = [1.0] * n
        self.locks = []
        self.lock_at = {}               # (x, y) -> Lock
        self.ids = []                   # (name, x, y): named tiles (places.py)
        self.entity_lines = []          # (type, name, x, y, misc) in map pixels
        self.object_blocks = {}         # (x, y) -> walk cells (0..walk_res^2-1) blocked by objects' footprints
        self.grid = None                # walk grid (grid_cell cells, locks open): bytearray gw x gh, or None = stale
        self.swim_grid = None           # (the same, and every cell of a water tile too: for Swims=1 NPCs)
        self.regions = None
        self.version = 0                # goes up whenever a tile changes (the browsers ask for it again)
        self.changes = []               # (version, cell) of the latest changes: a door opening sends that one tile
        self.load(lines)

    # ----- reading the file
    def load(self, lines=None):
        d = self.data
        xt, yt = d.xt, d.yt
        if lines is None:
            lines = d.read_lines(d.map_path(self.name))
        for y in range(1, yt + 1):
            row = trim(lines[y - 1]) if y - 1 < len(lines) else ""
            for x in range(1, xt + 1):
                cell = trim(word(row, x, ":"))
                tile = word(cell, 1, "+") or "Black001"
                c = (y - 1) * xt + x
                self.tile[c] = tile
                k = 2
                while word(cell, k, "+") != "":
                    overlay = word(cell, k, "+")
                    arg = word(word(overlay, 2, "("), 1, ")")
                    kind = word(overlay, 1, "(")
                    if kind == "Decor":
                        self.decor[c] = arg
                    elif kind == "Under":
                        self.under[c] = arg
                    elif kind == "Infront":
                        self.infront[c] = arg
                    elif kind == "Roof":
                        self.roof[c] = word(arg, 1, ".")
                        self.roof_group[c] = val(word(arg, 2, "."))
                    elif kind == "Trigger":
                        self.trigger[c] = self.script_name(arg)
                    k += 1
                self.refresh_cell(c)
        for line in lines[yt:]:
            etype = trim(field(line, 1, "\t"))
            ename = trim(field(line, 2, "\t"))
            if etype in ENTITY_LINE_TYPES:
                x = val(field(line, 3, "\t"))
                y = val(field(line, 4, "\t"))
                misc = trim(field(line, 5, "\t"))
                if etype == "MapItem" and trim(field(line, 6, "\t")):
                    misc = trim(misc + " " + trim(field(line, 6, "\t")))
                self.entity_lines.append((etype, ename, x, y, misc))
            elif etype == "Trigger":
                x, y = int(val(field(line, 3, "\t"))), int(val(field(line, 4, "\t")))
                if 1 <= x <= xt and 1 <= y <= yt:
                    self.trigger[(y - 1) * xt + x] = self.script_name(ename)
            elif etype == "Id":
                self.ids.append((ename, int(val(field(line, 3, "\t"))), int(val(field(line, 4, "\t")))))
            elif etype == "Lock":
                x, y = int(val(ename)), int(val(field(line, 3, "\t")))
                if 1 <= x <= xt and 1 <= y <= yt and len(self.locks) < 100:
                    closed = self.tile[(y - 1) * xt + x]
                    lk = Lock(len(self.locks) + 1, x, y, trim(field(line, 4, "\t")), trim(field(line, 5, "\t")),
                              closed, d.unlocked_tile(closed))
                    self.locks.append(lk)
                    self.lock_at[(x, y)] = lk

    @staticmethod
    def script_name(s):
        s = trim(s)
        return s[:-4] if s.lower().endswith(".txt") else s

    # ----- cells
    def cell(self, x, y):
        return (y - 1) * self.data.xt + x

    def inside(self, x, y):
        return 1 <= x <= self.data.xt and 1 <= y <= self.data.yt

    def refresh_cell(self, c):
        d = self.data
        t = self.tile[c]
        if not t:
            self.walk[c], self.los[c], self.speed[c] = "", 1, 1.0
            return
        self.walk[c], self.los[c] = d.cell_walk_los(t, self.decor[c])
        self.speed[c] = d.cell_speed(t, self.decor[c])

    def cell_text(self, x, y):
        c = self.cell(x, y)
        return (self.tile[c] + ("+Under(%s)" % self.under[c] if self.under[c] else "") +
                ("+Decor(%s)" % self.decor[c] if self.decor[c] else ""))

    def change_cell(self, x, y, spec, keep_decor=True):
        """Tile x,y becomes spec (a cell spec: a ground tile, a decor tile, or Tile+Decor(Name)). True if it changed."""
        if not self.inside(x, y):
            return False
        tile, decor = self.data.cell_spec(spec)
        under = self.data.cell_under(spec)
        if not tile and decor is None and under is None:
            return False
        if tile and decor is None and not keep_decor:
            decor = ""
        c = self.cell(x, y)
        before = (self.tile[c], self.decor[c], self.under[c])
        if under is not None:
            self.under[c] = under
        if decor is not None:
            self.decor[c] = decor
        if tile:
            self.tile[c] = tile
        if (self.tile[c], self.decor[c], self.under[c]) == before:
            return False
        self.refresh_cell(c)
        self.grid_dirty()
        self.version += 1
        self.logged(c)
        return True

    def set_roofs(self, roofs):
        """roofs: cell -> (roof tile, group) for every roofed cell (the rest have none). True if anything changed."""
        changed = False
        for c in range(1, len(self.roof)):
            r, g = roofs.get(c, ("", 0))
            if (self.roof[c], self.roof_group[c]) != (r, g):
                self.roof[c], self.roof_group[c] = r, g
                changed = True
        if changed:
            self.version += 1
            self.logged(None)               # (roofs: the whole map again)
        return changed

    CHANGES_KEPT = 48

    def logged(self, c):
        self.changes.append((self.version, c))
        if len(self.changes) > self.CHANGES_KEPT:
            del self.changes[0]

    def changes_since(self, v):
        """The cells changed after version v, if each change since is one tile (else None: send the whole map)."""
        if v is None or v > self.version or self.version - v > self.CHANGES_KEPT:
            return None
        log = dict(self.changes)
        cells = set()
        for ver in range(v + 1, self.version + 1):
            c = log.get(ver)
            if c is None:
                return None
            cells.add(c)
        return sorted(cells)

    def grid_dirty(self):
        self.grid = None
        self.swim_grid = None
        self.regions = None

    # ----- walking
    def local_walkable(self, lx, ly, walk_override=None):
        """Can the feet stand at map pixel lx,ly (locks open)? walk_override: this cell's walk mask for one player."""
        d = self.data
        tx = int(lx / d.tw) + 1
        ty = int(ly / d.th) + 1
        if not self.inside(tx, ty):
            return False
        c = (ty - 1) * d.xt + tx
        if not self.tile[c]:
            return False
        res = d.walk_res
        xp = int(((lx - (tx - 1) * d.tw) / d.tw) * res)
        yp = int(((ly - (ty - 1) * d.th) / d.th) * res)
        walk = self.walk[c] if walk_override is None else walk_override
        p = xp + res * yp
        if not (p < len(walk) and walk[p] == "1"):
            return False
        blocked = self.object_blocks.get((tx, ty))
        return not (blocked and p in blocked)

    def tile_is_water(self, tx, ty):
        if not self.inside(tx, ty):
            return False
        name = self.tile[(ty - 1) * self.data.xt + tx]
        return bool(name) and self.data.tile_water(name)

    def local_swimmable(self, lx, ly):
        """For a swimmer (Swims=1: an otter, a seal, a frog): the land it can walk, and any water (a sea rock too)."""
        tx, ty = int(lx / self.data.tw) + 1, int(ly / self.data.th) + 1
        return self.tile_is_water(tx, ty) or self.local_walkable(lx, ly)

    def get_swim_grid(self):
        if self.swim_grid is None:
            d = self.data
            grid = bytearray(self.get_grid())
            cell = d.grid_cell
            per_x, per_y = max(1, d.tw // cell), max(1, d.th // cell)
            for ty in range(1, d.yt + 1):
                for tx in range(1, d.xt + 1):
                    if self.tile_is_water(tx, ty):
                        for j in range(per_y):
                            for i in range(per_x):
                                cx, cy = (tx - 1) * per_x + i, (ty - 1) * per_y + j
                                if cx < self.gw and cy < self.gh:
                                    grid[cy * self.gw + cx] = 1
            self.swim_grid = grid
        return self.swim_grid

    def build_grid(self):
        """The walk grid: a cell is walkable if the feet can stand at its centre and at 7 of the 8 points around it."""
        d = self.data
        cell = d.grid_cell
        gw, gh = int(d.sw / cell), int(d.sh / cell)
        grid = bytearray(gw * gh)
        m = int(cell / 2)
        q = int(cell / 5)
        f = cell - q
        pw = self.local_walkable
        per_tile_x = max(1, d.tw // cell)
        per_tile_y = max(1, d.th // cell)
        for ty in range(1, d.yt + 1):
            for tx in range(1, d.xt + 1):
                c = (ty - 1) * d.xt + tx
                walk = self.walk[c]
                uniform = -1
                if not self.tile[c] or "1" not in walk:
                    uniform = 0
                elif "0" not in walk and (tx, ty) not in self.object_blocks:
                    uniform = 1
                for j in range(per_tile_y):
                    cy = (ty - 1) * per_tile_y + j
                    for i in range(per_tile_x):
                        cx = (tx - 1) * per_tile_x + i
                        if cx >= gw or cy >= gh:
                            continue
                        if uniform >= 0:
                            grid[cy * gw + cx] = uniform
                            continue
                        x0, y0 = cx * cell, cy * cell
                        if not pw(x0 + m, y0 + m):
                            continue
                        count = (pw(x0 + q, y0 + q) + pw(x0 + m, y0 + q) + pw(x0 + f, y0 + q) + pw(x0 + q, y0 + m) +
                                 pw(x0 + f, y0 + m) + pw(x0 + q, y0 + f) + pw(x0 + m, y0 + f) + pw(x0 + f, y0 + f))
                        grid[cy * gw + cx] = 1 if count >= 7 else 0
        self.grid = grid
        self.gw, self.gh = gw, gh
        return grid

    def get_grid(self):
        return self.grid if self.grid is not None else self.build_grid()

    def get_regions(self):
        """region[cell] = which connected walkable area a grid cell belongs to (0 = blocked)."""
        if self.regions is not None and self.grid is not None:
            return self.regions
        grid = self.get_grid()
        w = self.gw
        total = len(grid)
        region = [0] * total
        n = 0
        for i in range(total):
            if grid[i] == 1 and region[i] == 0:
                n += 1
                region[i] = n
                stack = [i]
                while stack:
                    c = stack.pop()
                    cx = c % w
                    for nb in ((c - 1) if cx > 0 else -1, (c + 1) if cx < w - 1 else -1,
                               (c - w) if c >= w else -1, (c + w) if c + w < total else -1):
                        if nb >= 0 and grid[nb] == 1 and region[nb] == 0:
                            region[nb] = n
                            stack.append(nb)
        self.regions = region
        return region

    # ----- for the browsers
    def cells_to_client(self, cells):
        """Just those cells, as the browser keeps them: [cell, tile, decor, under] (cells numbered from 1)."""
        return {"name": self.name, "v": self.version,
                "cells": [[c, self.tile[c], self.decor[c], self.under[c]] for c in cells]}

    def to_client(self):
        """The map as the browser draws it (tiles as the world has them; each player's own changes are sent apart)."""
        return {"name": self.name, "v": self.version, "tile": self.tile[1:], "decor": self.decor[1:], "under": self.under[1:],
                "roof": self.roof[1:], "group": self.roof_group[1:], "infront": self.infront[1:]}
