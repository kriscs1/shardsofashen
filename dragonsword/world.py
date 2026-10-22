"""The world: the 3 x 3 maps round the player (the "ground"), tiles, decor, edge blending, roofs, fog of war, locks, the
walk grid and pathfinding, map loading and changing maps, line of sight, the minimap and day and night.

DECOR: a see-through tile (Tiles.ini Layer=Decor) over a cell's ground tile, painted into the ground with it, so one
chair, tree or pot of flowers goes on any floor. Its walk mask and line of sight join the tile's; the mouse names it
(not the floor under it); a script's Change.Tile with a decor tile changes just the decor.

GROUND: tiles, roofs and fog are not drawn one by one each frame. They are painted into one big picture of the current
map and the 8 around it (slots 1-9, row by row, 5 = the current map). Ground pixel 0,0 is current-map pixel
ground_ox, ground_oy. Two pictures the same size: the clean ground (tiles with their neighbours' blended edges, roofs
unless hidden, tree tops) and the shown ground (the clean ground with night and the fog over it, made by ground_refresh).

THE WINDOW STORE: the tiles of all 9 maps, so painting and edge blending work across the seams. Window tile wx,wy
(1 to 3*xt, 1 to 3*yt; the current map is the middle) is in slot (wx-1)//xt + 3*((wy-1)//yt) + 1.
"""
import heapq
import math
import os

import pygame

from . import ini
from .assets import sprite_file
from .entity import (TILE, INFRONTTILE, ROOF, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, Entity, attitude_of_type,
                     normalise_type)
from .lb import val, word, field, trim, lbstr, distance, strip_digits


def grid2(xt, yt, value):
    return [[value] * (yt + 2) for _ in range(xt + 2)]


class SlotStore:
    """The tiles of one map of the ground (cell = (y-1)*xt+x, 1-based)."""

    def __init__(self, cells):
        n = cells + 1
        self.tile = [""] * n
        self.decor = [""] * n       # a see-through tile over the ground (Tiles.ini Layer=Decor): a chair, a tree
        self.roof = [""] * n
        self.infront = [""] * n
        self.tex = [""] * n
        self.blend = [0] * n
        self.walk = [""] * n
        self.lock = [0] * n
        self.los = [1] * n
        self.locks = []     # its Lock lines with an Unlocked.Tile: (x, y, condition, closed tile, open tile)


class WorldMixin:
    # =================================================================================================================
    # Set up
    # =================================================================================================================
    def world_init_arrays(self):
        xt, yt = self.xt, self.yt
        self.tile_name = grid2(xt, yt, "")
        self.decor_name = grid2(xt, yt, "")
        self.tile_walk = grid2(xt, yt, "")
        self.tile_los = grid2(xt, yt, 1)
        self.tile_speed = grid2(xt, yt, 1.0)
        self.roof_name = grid2(xt, yt, "")
        self.roof_group = grid2(xt, yt, 0)
        self.roof_shown = grid2(xt, yt, 0)
        self.infront_ents = {}
        self.trigger_script = grid2(xt, yt, "")
        self.tile_locked = grid2(xt, yt, 0)
        self.fog_disabled = grid2(50, 50, 0)
        self.locks = []  # [x, y, condition, message, locked]
        cells = xt * yt
        self.slot_map = [""] * 10
        self.store = [None] + [SlotStore(cells) for _ in range(9)]
        fcells = self.fog_xt * self.fog_yt + 1
        self.wfog_shown = [None] + [[1] * fcells for _ in range(9)]
        self.wfog_black = [None] + [[1] * fcells for _ in range(9)]
        self.hid = []  # [(slot, cell)] uncovered fog cells
        self.walk_grid = bytearray()
        self.object_blocks = {}     # (wx, wy) window tile -> the walk cells (0..walk_res^2-1) objects' footprints block
        self.object_sig = None
        self.grid_region = []
        self.grid_w = self.grid_h = 0
        self.grid_regions_dirty = True
        self.ground_window = ""
        self.w_origin_tx = self.w_origin_ty = 0
        self.blend_highest = 0
        self.under_roof_group = None
        self.cam_min_x = self.cam_max_x = self.cam_min_y = self.cam_max_y = 0

    def ground_init(self):
        """Once, after the window opens: the ground pictures."""
        self.ground_w = 3 * self.sw
        self.ground_h = 3 * self.sh
        self.ground_ox = -self.sw
        self.ground_oy = -self.sh
        # Python draws night and fog over the playfield every frame, so the clean ground is all there is
        self.clean = pygame.Surface((self.ground_w, self.ground_h)).convert()
        self.clean.fill((0, 0, 0))
        self.ground = self.clean
        self.ground_ready = True
        self.ground_hold = False
        self.blend_ready = self.assets.loaded("Blend_N1") and self.assets.loaded("Blend_NW2")
        if not self.blend_ready:
            self.log("WARNING - Edge blending is off (no Sprites\\Interface\\Blend_* masks)")
        self.bl_dirs = [(0, -1, "N"), (1, 0, "E"), (0, 1, "S"), (-1, 0, "W"), (1, -1, "NE"), (1, 1, "SE"),
                        (-1, 1, "SW"), (-1, -1, "NW")]
        self.blend_cache = {}
        self.textures = {}

    # =================================================================================================================
    # Map names
    # =================================================================================================================
    def map_x(self):
        return val(word(self.screen_name, 1, ","))

    def map_y(self):
        return val(word(self.screen_name, 2, ","))

    def map_z(self):
        return val(word(self.screen_name, 3, ","))

    @staticmethod
    def make_map_name(x, y, z):
        return "%s,%s,%s" % (lbstr(x), lbstr(y), lbstr(z))

    def map_path(self, name):
        return os.path.join(self.root, "Maps", name + ".txt")

    def map_exists(self, name):
        return bool(name) and os.path.exists(self.map_path(name))

    def first_map(self):
        try:
            files = sorted(f for f in os.listdir(os.path.join(self.root, "Maps")) if f.lower().endswith(".txt"))
        except OSError:
            return ""
        return files[0][:-4] if files else ""

    def map_slot(self, name):
        if not name:
            return 0
        for k in range(1, 10):
            if self.slot_map[k] == name:
                return k
        return 0

    def map_ox(self, name):
        k = self.map_slot(name)
        return (((k - 1) % 3) - 1) * self.sw if k > 0 else 0

    def map_oy(self, name):
        k = self.map_slot(name)
        return (int((k - 1) / 3) - 1) * self.sh if k > 0 else 0

    def map_at(self, x, y):
        """The map that current-map pixel x,y is on (the current map if it is off the ground or no map is there)."""
        if x + self.sw < 0 or y + self.sh < 0:
            return self.screen_name
        sx = int((x + self.sw) / self.sw)
        sy = int((y + self.sh) / self.sh)
        if sx > 2 or sy > 2:
            return self.screen_name
        m = self.slot_map[sy * 3 + sx + 1]
        return m if m else self.screen_name

    def local_coords(self, name, x, y):
        return "%s,%s" % (lbstr(int(x - self.map_ox(name))), lbstr(int(y - self.map_oy(name))))

    def entity_home(self, e):
        return e.map if e.map else self.screen_name

    def tile_of_x(self, px):
        tx = int(px / self.tw) + 1
        if px < 0:
            tx = 1
        return min(max(tx, 1), self.xt)

    def tile_of_y(self, py):
        ty = int(py / self.th) + 1
        if py < 0:
            ty = 1
        return min(max(ty, 1), self.yt)

    # =================================================================================================================
    # Window store
    # =================================================================================================================
    def w_find(self, wx, wy):
        """Window tile wx,wy -> (store, cell), or None when it is outside the window."""
        xt, yt = self.xt, self.yt
        if wx < 1 or wy < 1 or wx > 3 * xt or wy > 3 * yt:
            return None
        sx = int((wx - 1) / xt)
        sy = int((wy - 1) / yt)
        return self.store[sy * 3 + sx + 1], (wy - 1 - sy * yt) * xt + wx - sx * xt

    def w_set(self, wx, wy, tile):
        f = self.w_find(wx, wy)
        if f is None:
            return
        self.anim_gen = getattr(self, "anim_gen", 0) + 1     # (the animated cells in view are found again)
        st, c = f
        st.tile[c] = tile
        st.blend[c] = 0
        st.tex[c] = ""
        st.lock[c] = 0
        st.walk[c] = ""
        st.los[c] = 1
        if tile == "":
            return
        st.walk[c], st.los[c] = self.cell_walk_los(tile, st.decor[c])
        st.blend[c] = min(9, max(0, int(val(self.tile_ini(tile, "Blend", "0")))))
        if st.blend[c] > 0:
            st.tex[c] = self.tile_ini(tile, "Blend.Texture", tile)
            if self.blend_highest < st.blend[c]:
                self.blend_highest = st.blend[c]

    def w_set_decor(self, wx, wy, decor):
        """The decor of window tile wx,wy ("" = none): its walk mask and line of sight join the tile's."""
        f = self.w_find(wx, wy)
        if f is None:
            return
        self.anim_gen = getattr(self, "anim_gen", 0) + 1
        st, c = f
        st.decor[c] = decor
        if st.tile[c]:
            st.walk[c], st.los[c] = self.cell_walk_los(st.tile[c], decor)

    def w_change_cell(self, wx, wy, spec, keep_decor=True):
        """Window tile wx,wy changes to spec (cell_spec): its ground tile, its decor or both."""
        tile, decor = self.cell_spec(spec)
        f = self.w_find(wx, wy)
        if f is None or (not tile and decor is None):
            return
        if tile and decor is None and not keep_decor:
            decor = ""
        if decor is not None:
            f[0].decor[f[1]] = decor
        if tile:
            self.w_set(wx, wy, tile)
        elif decor is not None:
            self.w_set_decor(wx, wy, decor)

    # ----- Decor (Tiles.ini Layer=Decor): a see-through tile drawn over a cell's ground tile, so one chair, tree or
    # pot of flowers goes on any floor. The map cell says it as Tile+Decor(Name)
    def is_decor_tile(self, name):
        cache = self.__dict__.setdefault("decor_tile_cache", {})
        if name not in cache:
            cache[name] = bool(name) and self.tile_ini(name, "Layer", "").strip().lower() == "decor"
        return cache[name]

    def cell_spec(self, spec):
        """What a cell is to change to: (ground tile or "", decor or None = leave the decor as it is).
        "Grass001" -> ("Grass001", None); a decor tile "Tree_Stump001" -> ("", "Tree_Stump001");
        "Grass001+Decor(Oak_Tree001)" -> ("Grass001", "Oak_Tree001"); "Grass001+Decor()" -> ("Grass001", "")."""
        spec = trim(spec)
        tile = trim(word(spec, 1, "+"))
        decor = None
        k = 2
        while word(spec, k, "+") != "":
            overlay = word(spec, k, "+")
            if trim(word(overlay, 1, "(")) == "Decor":
                decor = trim(word(word(overlay, 2, "("), 1, ")"))
            k += 1
        if decor is None and self.is_decor_tile(tile):
            return "", tile
        return tile, decor

    def cell_text(self, x, y):
        """Current-map tile x,y as a cell spec: its tile, and its decor if it has one."""
        decor = self.decor_name[x][y]
        return self.tile_name[x][y] + ("+Decor(%s)" % decor if decor else "")

    def tile_walk_data(self, name):
        walk = self.tile_ini(name, "Walkable.Data", self.all_walkable)
        if len(walk) < len(self.all_walkable):
            walk = (walk + self.all_walkable)[:len(self.all_walkable)]
        return walk

    def cell_walk_los(self, tile, decor):
        """A cell's walk mask and line of sight: the tile's, with its decor's over them (the feet can stand only where
        both let them; either can block the view)."""
        walk = self.tile_walk_data(tile)
        los = val(self.tile_ini(tile, "Line.of.Sight", "1"))
        if decor:
            over = self.tile_walk_data(decor)
            walk = "".join("1" if a == "1" and b == "1" else "0" for a, b in zip(walk, over))
            if val(self.tile_ini(decor, "Line.of.Sight", "1")) == 0:
                los = 0
        return walk, los

    def cell_speed(self, tile, decor):
        """How fast you walk over a cell: its decor's Walk.Speed (tall grass), else its tile's."""
        s = self.tile_ini(decor, "Walk.Speed", "") if decor else ""
        if trim(s) == "":
            s = self.tile_ini(tile, "Walk.Speed", "1")
        return min(3, max(0.2, val(s)))

    def blend_level_at(self, wx, wy):
        f = self.w_find(wx, wy)
        if f is None:
            return 0, ""
        st, c = f
        return st.blend[c], st.tex[c]

    def ground_bmp(self, name):
        if not name:
            name = "Black001"
        if self.assets.loaded(name):
            return self.assets.get(name)
        self.log_missing("Sprite", name)
        return self.assets.get(self.fallback_sprite())

    def paint_window_cell(self, wx, wy):
        """One tile into the clean ground: the tile, the edges of higher-Blend neighbours over it, its decor, its roof
        (unless hidden: the current map's roofs) and its tree top."""
        f = self.w_find(wx, wy)
        if f is None:
            return
        st, c = f
        dx = (wx - 1) * self.tw
        dy = (wy - 1) * self.th
        tile = st.tile[c]
        if tile == "":
            self.clean.fill((0, 0, 0), (dx, dy, self.tw, self.th))
            return
        tex = self.tile_texture(tile)
        if tex is not None:
            self.clean.blit(self.texture_cell(tex, wx, wy), (dx, dy))
        elif not self.anim_base(tile, wx, wy, dx, dy):        # (a plant swaying: anim.py)
            sp = self.ground_bmp(tile)
            if sp:
                self.clean.blit(sp.image, (dx, dy))
        b = st.blend[c]
        if self.blend_ready and 0 < b < self.blend_highest:
            self.blend_edges(wx, wy, b, dx, dy)
        roof = st.roof[c]
        roof_shown = bool(roof)
        if roof and st is self.store[5]:
            roof_shown = self.roof_shown[wx - self.xt][wy - self.yt] == 1
        decor = st.decor[c]
        sea = decor and self.anim_kind(tile) == "water"
        if sea:                                         # (a rock in the sea: the foam laps round it)
            self.paint_decor(decor, wx, wy, dx, dy, roof_shown or st.infront[c])
        self.anim_paint(tile, wx, wy, dx, dy)           # foam where the water meets land, a flickering flame (anim.py)
        if decor and not sea:
            self.paint_decor(decor, wx, wy, dx, dy, roof_shown or st.infront[c])
        if roof_shown:
            sp = self.ground_bmp(roof)
            if sp:
                self.clean.blit(sp.masked, (dx, dy))
        if st.infront[c]:
            sp = self.ground_bmp(st.infront[c])
            if sp:
                self.clean.blit(sp.masked, (dx, dy))

    def blend_edges(self, wx, wy, b, dx, dy):
        found = []
        for k, (ddx, ddy, side) in enumerate(self.bl_dirs):
            level, tex = self.blend_level_at(wx + ddx, wy + ddy)
            if level > b and k >= 4:
                if self.blend_level_at(wx + ddx, wy)[0] >= level or self.blend_level_at(wx, wy + ddy)[0] >= level:
                    level = 0
            if level > b and tex:
                variant = 1 + (abs((wx + self.w_origin_tx) * 7 + (wy + self.w_origin_ty) * 13) % 2)
                found.append((level, len(found), tex, "Blend_%s%d" % (side, variant)))
        if not found:
            return
        found.sort()
        for level, _, tex, mask in found:
            surf = self.blend_surface(tex, mask, wx, wy)
            if surf is not None:
                self.clean.blit(surf, (dx, dy))

    # ----- Big textures (Tiles.ini Texture=<name>: Sprites\Textures\<name>.png, a plain picture). A tile with one is
    # painted from the part of the picture at its place in the world, so a forest doesn't repeat every tile
    def tile_texture(self, tile):
        name = self.tile_ini(tile, "Texture", "") if tile else ""
        if not name:
            return None
        if name not in self.textures:
            path = sprite_file(self.root, "Textures", name)
            try:
                self.textures[name] = pygame.image.load(path).convert()
            except Exception:
                self.log_missing("Texture", name)
                self.textures[name] = None
        return self.textures[name]

    def texture_cell(self, tex, wx, wy):
        """The tile-sized part of texture tex for window tile wx,wy (wrapping round the picture's edges)."""
        tw, th = self.tw, self.th
        w, h = tex.get_size()
        sx = ((wx + self.w_origin_tx - 1) * tw) % w
        sy = ((wy + self.w_origin_ty - 1) * th) % h
        if sx + tw <= w and sy + th <= h:
            return tex.subsurface((sx, sy, tw, th))
        cell = pygame.Surface((tw, th)).convert()
        for ox in (0, w):
            for oy in (0, h):
                cell.blit(tex, (ox - sx, oy - sy))
        return cell

    def blend_surface(self, tex, mask, wx=0, wy=0):
        """The texture tex through the blend mask: its picture where the mask's picture half is white."""
        big = self.tile_texture(tex)
        if big is not None:  # From the big texture at this tile's place, so it carries on from the tile beside it
            w, h = big.get_size()
            key = (tex, mask, ((wx + self.w_origin_tx - 1) * self.tw) % w, ((wy + self.w_origin_ty - 1) * self.th) % h)
        else:
            key = (tex, mask)
        s = self.blend_cache.get(key)
        if s is None:
            t = self.ground_bmp(tex)
            m = self.assets.get(mask)
            if t is None or m is None:
                self.blend_cache[key] = False
                return None
            import numpy as np
            s = (self.texture_cell(big, wx, wy) if big is not None else t.image).copy().convert_alpha()
            mk = pygame.surfarray.array3d(m.image)
            alpha = pygame.surfarray.pixels_alpha(s)
            w = min(alpha.shape[0], mk.shape[0])
            h = min(alpha.shape[1], mk.shape[1])
            alpha[:, :] = 0
            alpha[:w, :h] = np.where(mk[:w, :h].astype(np.int32).sum(axis=2) >= 384, 255, 0).astype(np.uint8)
            del alpha
            self.blend_cache[key] = s
        return s or None

    def ground_refresh(self, gx1, gy1, gx2, gy2):
        """The original copied the clean ground into the shown one with night and fog over it. Here night and fog are
        drawn over the playfield every frame (draw_fog, render), so there is nothing to do."""
        return

    def fog_alpha_grid(self):
        """How dark the fog is over every cell of the 9 maps (rows = y): 255 never seen, fog_seen_alpha seen before,
        0 in view."""
        import numpy as np
        xt, yt = self.fog_xt, self.fog_yt
        grid = np.full((3 * yt, 3 * xt), 255, dtype=np.uint8)
        seen = self.fog_seen_alpha
        for slot in range(1, 10):
            if not self.slot_map[slot]:
                continue
            shown = np.frombuffer(bytes(self.wfog_shown[slot][1:xt * yt + 1]), dtype=np.uint8).reshape(yt, xt)
            black = np.frombuffer(bytes(self.wfog_black[slot][1:xt * yt + 1]), dtype=np.uint8).reshape(yt, xt)
            a = np.where(shown == 1, np.where(black == 1, 255, seen), 0).astype(np.uint8)
            i = (slot - 1) % 3
            j = int((slot - 1) / 3)
            grid[j * yt:(j + 1) * yt, i * xt:(i + 1) * xt] = a
        return grid

    def draw_fog(self, scr, cam_x, cam_y):
        """The fog over the playfield: one pixel per cell, scaled up (smoothly, so its edges are soft, when
        FogOfWar.Smooth=1). Made again only when the fog changes or the view moves into other cells."""
        import numpy as np
        s = self.fog_w
        gx0 = int((cam_x - self.ground_ox) // s) - 1
        gy0 = int((cam_y - self.ground_oy) // s) - 1
        cols = int(self.world_w / s) + 3
        rows = int(self.world_h / s) + 3
        key = (self.fog_version, gx0, gy0, cols, rows)
        if key != self.fog_overlay_key:
            self.fog_overlay_key = key
            grid = self.fog_alpha_grid()
            h, w = grid.shape
            part = np.full((rows, cols), 255, dtype=np.uint8)
            x1, y1 = max(0, gx0), max(0, gy0)
            x2, y2 = min(w, gx0 + cols), min(h, gy0 + rows)
            if x2 > x1 and y2 > y1:
                part[y1 - gy0:y2 - gy0, x1 - gx0:x2 - gx0] = grid[y1:y2, x1:x2]
            self.fog_overlay = self.fog_paint(part, cols, rows, s, gx0 * s, gy0 * s)
        scr.blit(self.fog_overlay, (gx0 * s + self.ground_ox - cam_x, gy0 * s + self.ground_oy - cam_y))

    FOG_TEX = 256

    def fog_texture(self):
        """A wrap-round picture (FOG_TEX square, a Surface) the fog is painted with: warm darkness, faint smoke."""
        import numpy as np
        tex = getattr(self, "_fog_tex", None)
        if tex is not None:
            return tex
        n = self.FOG_TEX
        rng = np.random.default_rng(4242)
        acc = np.zeros((n, n))
        for octave, weight in ((8, 1.0), (16, 0.5), (32, 0.25), (64, 0.12)):
            coarse = rng.uniform(-1, 1, (octave, octave))
            idx = np.arange(n) * octave / n                      # smooth, wrapping, up to n x n
            i0 = np.floor(idx).astype(int)
            f = idx - i0
            i1 = (i0 + 1) % octave
            f = f * f * (3 - 2 * f)
            top = coarse[i0][:, i0] * (1 - f)[None, :] + coarse[i0][:, i1] * f[None, :]
            bottom = coarse[i1][:, i0] * (1 - f)[None, :] + coarse[i1][:, i1] * f[None, :]
            acc += weight * (top * (1 - f)[:, None] + bottom * f[:, None])
        acc = (acc - acc.min()) / max(1e-6, acc.max() - acc.min())
        dark, light = np.array((7, 5, 4.0)), np.array((27, 21, 17.0))       # warm black, the faintest smoke
        rgb = dark[None, None] + (light - dark)[None, None] * (acc ** 2.2)[..., None]
        self._fog_tex = pygame.surfarray.make_surface(np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        return self._fog_tex

    def fog_paint(self, part, cols, rows, s, gx, gy):
        """The fog overlay from part (how thick, cell by cell: rows x cols, 0-255): the cloud picture anchored to the
        ground (the clouds stay put as you walk), a pale misty rim where the fog thins, and its shape (smoothed when
        FogOfWar.Smooth=1). All blits, so it's quick to make again as you walk."""
        import numpy as np
        w, h = cols * s, rows * s
        scale = pygame.transform.smoothscale if self.fog_smooth else pygame.transform.scale
        tex = self.fog_texture()
        n = self.FOG_TEX
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        for ty in range(-(gy % n), h, n):                       # the clouds, tiled in ground coordinates
            for tx in range(-(gx % n), w, n):
                out.blit(tex, (tx, ty))
        t = part.astype(np.float64) / 255.0
        rim = np.clip(1 - np.abs(t * 2 - 1) * 1.4, 0, 1) * 0.6
        glow = pygame.surfarray.make_surface((rim.T[..., None] * np.array((92, 58, 22.0))).astype(np.uint8))  # lamplight
        out.blit(scale(glow, (w, h)), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        shape = pygame.Surface((cols, rows), pygame.SRCALPHA)
        shape.fill((255, 255, 255, 255))
        alpha = pygame.surfarray.pixels_alpha(shape)
        alpha[:, :] = part.T
        del alpha
        out.blit(scale(shape, (w, h)), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    def paint_ground(self, x1, y1, x2, y2):
        """Paints the current map's tiles over its pixels x1,y1 to x2,y2 (and the ring round them) into the clean
        ground, then shows them with their fog."""
        if not self.ground_ready or self.ground_hold:
            return
        tx1 = self.tile_of_x(x1) - 1
        ty1 = self.tile_of_y(y1) - 1
        tx2 = self.tile_of_x(x2 - 1) + 1
        ty2 = self.tile_of_y(y2 - 1) + 1
        for ty in range(ty1, ty2 + 1):
            for tx in range(tx1, tx2 + 1):
                self.paint_window_cell(tx + self.xt, ty + self.yt)
        self.ground_refresh((tx1 - 1) * self.tw - self.ground_ox, (ty1 - 1) * self.th - self.ground_oy,
                            tx2 * self.tw - self.ground_ox, ty2 * self.th - self.ground_oy)

    def shift_ground(self, surf, sx, sy):
        """Moves the 3 x 3 maps in a ground picture: slot i,j gets old slot i+sx,j+sy."""
        tmp = surf.copy()
        surf.fill((0, 0, 0))
        surf.blit(tmp, (-sx * self.sw, -sy * self.sh))

    # =================================================================================================================
    # Changing maps
    # =================================================================================================================
    def ground_recentre(self):
        """At a map change (before the new map loads): the 3 x 3 maps move so the new one is in the middle."""
        if not self.ground_ready:
            return
        new_x, new_y, new_z = self.map_x(), self.map_y(), self.map_z()
        shift_x = shift_y = 9
        if self.ground_window:
            old_x = val(word(self.ground_window, 1, ","))
            old_y = val(word(self.ground_window, 2, ","))
            old_z = val(word(self.ground_window, 3, ","))
            if old_z == new_z and abs(new_x - old_x) <= 1 and abs(new_y - old_y) <= 1:
                shift_x, shift_y = new_x - old_x, new_y - old_y
        self.ground_window = self.screen_name
        xt, yt = self.xt, self.yt
        self.w_origin_tx = (new_x - 1) * xt
        self.w_origin_ty = (new_y - 1) * yt
        mw, mh = self.sw, self.sh
        slot_new = [0] * 10
        for slot in range(1, 10):
            i = ((slot - 1) % 3) - 1
            j = int((slot - 1) / 3) - 1
            if shift_x == 9 or abs(i + shift_x) > 1 or abs(j + shift_y) > 1:
                slot_new[slot] = 1
        if shift_x == 9:
            self.remove_world_entities()
        else:
            for slot in range(1, 10):
                i = ((slot - 1) % 3) - 1
                j = int((slot - 1) / 3) - 1
                if abs(i - shift_x) > 1 or abs(j - shift_y) > 1:
                    self.unload_map_entities(self.slot_map[slot])
        self.time_mark("unload")
        cells = xt * yt
        if shift_x != 9:
            self.shift_ground(self.clean, shift_x, shift_y)
            self.shift_fog(shift_x, shift_y)
            self.shift_walk_grid(shift_x, shift_y)
            old = list(self.store)
            for slot in range(1, 10):
                if slot_new[slot] == 0:
                    o = (int((slot - 1) / 3) + shift_y) * 3 + ((slot - 1) % 3) + shift_x + 1
                    self.store[slot] = old[o]
                else:
                    self.store[slot] = SlotStore(cells)
        else:
            self.hid = []
            self.store = [None] + [SlotStore(cells) for _ in range(9)]
        self.time_mark("shift")
        for slot in range(1, 10):
            i = ((slot - 1) % 3) - 1
            j = int((slot - 1) / 3) - 1
            name = self.make_map_name(new_x + i, new_y + j, new_z)
            if not self.map_exists(name):
                name = ""
            self.slot_map[slot] = name
            if slot_new[slot] == 1:
                self.fog_reset_slot(slot)
                self.w_fill_slot(slot, name)
        self.time_mark("read-maps")
        if shift_x == 9 or self.grid_w == 0:
            self.build_walk_grid()
        else:
            # The map that was current keeps its doors as they are now (its Lock lines' state), not as its file has them
            was_slot = (1 - shift_y) * 3 + (1 - shift_x) + 1
            st = self.store[was_slot]
            for lk in self.locks:
                if 1 <= lk[0] <= xt and 1 <= lk[1] <= yt:
                    st.lock[(lk[1] - 1) * xt + lk[0]] = lk[4]
            x1 = ((was_slot - 1) % 3) * xt
            y1 = int((was_slot - 1) / 3) * yt
            for wy in range(y1 + 1, y1 + yt + 1):
                for wx in range(x1 + 1, x1 + xt + 1):
                    self.update_walk_grid_wtile(wx, wy)
            for slot in range(1, 10):
                if slot_new[slot] == 1:
                    x1 = ((slot - 1) % 3) * xt
                    y1 = int((slot - 1) / 3) * yt
                    for wy in range(y1 + 1, y1 + yt + 1):
                        for wx in range(x1 + 1, x1 + xt + 1):
                            self.update_walk_grid_wtile(wx, wy)
        self.time_mark("walk-grid")
        for slot in range(1, 10):
            if slot_new[slot] == 1 and self.slot_map[slot]:
                ox = (((slot - 1) % 3) - 1) * mw
                oy = (int((slot - 1) / 3) - 1) * mh
                self.load_map_entities(self.slot_map[slot], ox, oy)
                self.apply_queue_entities(self.slot_map[slot], ox, oy)
        for slot in range(1, 10):
            if slot_new[slot] == 1 and slot != 5:
                i = ((slot - 1) % 3) - 1
                j = int((slot - 1) / 3) - 1
                x1 = (i + 1) * xt + 1
                y1 = (j + 1) * yt + 1
                x2 = x1 + xt - 1
                y2 = y1 + yt - 1
                for wy in range(y1, y2 + 1):
                    for wx in range(x1, x2 + 1):
                        self.paint_window_cell(wx, wy)
                # The edge tiles of the kept maps beside it (not the current map: change_screen paints that and its ring)
                for wy in range(y1 - 1, y2 + 2):
                    for wx in range(x1 - 1, x2 + 2):
                        if wx < x1 or wx > x2 or wy < y1 or wy > y2:
                            if 1 <= wx <= 3 * xt and 1 <= wy <= 3 * yt:
                                other = int((wy - 1) / yt) * 3 + int((wx - 1) / xt) + 1
                                if slot_new[other] == 0 and other != 5:
                                    self.paint_window_cell(wx, wy)
                self.ground_refresh((i + 1) * mw - self.tw, (j + 1) * mh - self.th, (i + 2) * mw + self.tw,
                                    (j + 2) * mh + self.th)
        self.cam_min_x = -mw if self.slot_map[4] else 0
        self.cam_max_x = mw if self.slot_map[6] else 0
        self.cam_min_y = -mh if self.slot_map[2] else 0
        self.cam_max_y = mh if self.slot_map[8] else 0
        self.fog_last_x = -99999

    def w_fill_slot(self, slot, name):
        """Reads a map around the current one into the window store: its file's tiles, decor, roofs and tree tops, its
        locks and the tile changes waiting in the action queue ("" = no map there)."""
        xt, yt = self.xt, self.yt
        ox = ((slot - 1) % 3) * xt
        oy = int((slot - 1) / 3) * yt
        st = self.store[slot]
        for c in range(1, xt * yt + 1):
            st.decor[c] = ""
            st.roof[c] = ""
            st.infront[c] = ""
        st.locks = []
        if not name:
            for y in range(1, yt + 1):
                for x in range(1, xt + 1):
                    self.w_set(ox + x, oy + y, "")
            return
        lines = self.read_lines(self.map_path(name))
        for y in range(1, yt + 1):
            row = trim(lines[y - 1]) if y - 1 < len(lines) else ""
            for x in range(1, xt + 1):
                cell = trim(word(row, x, ":"))
                tile = word(cell, 1, "+") or "Black001"
                self.w_set(ox + x, oy + y, tile)
                c = (y - 1) * xt + x
                k = 2
                while word(cell, k, "+") != "":
                    overlay = word(cell, k, "+")
                    arg = word(word(overlay, 2, "("), 1, ")")
                    kind = word(overlay, 1, "(")
                    if kind == "Decor":
                        self.w_set_decor(ox + x, oy + y, arg)
                    if kind == "Infront":
                        st.infront[c] = arg
                    if kind == "Roof":
                        st.roof[c] = word(arg, 1, ".")
                    k += 1
        for row in lines[yt:]:
            if trim(field(row, 1, "\t")) == "Lock":
                x = val(field(row, 2, "\t"))
                y = val(field(row, 3, "\t"))
                condition = trim(field(row, 4, "\t"))
                if 1 <= x <= xt and 1 <= y <= yt:
                    locked = 1
                    if condition and self.condition_met(condition):
                        locked = 0
                    closed = st.tile[(y - 1) * xt + x]
                    opened = self.tile_ini(closed, "Unlocked.Tile", "")
                    if opened:                              # e.g. a town gate: drawn open while its lock is
                        st.locks.append((int(x), int(y), condition, closed, opened))
                        if not locked:
                            self.w_set(ox + x, oy + y, opened)
                    st.lock[(y - 1) * xt + x] = locked
        for entry in self.action_queue:
            if field(entry, 5, "\t") == name and field(entry, 1, "\t").upper() == "CHANGE.TILE":
                misc = field(entry, 4, "\t")
                coords = field(entry, 6, "\t")
                x = val(word(coords, 1, ","))
                y = val(word(coords, 2, ","))
                if misc not in ("-", "") and 1 <= x <= xt and 1 <= y <= yt:
                    self.w_change_cell(ox + x, oy + y, misc, keep_decor=False)

    @staticmethod
    def read_lines(path):
        try:
            text = ini.read_text(path)
        except OSError:
            return []
        return [ln.replace("\r", "") for ln in text.split("\n")]

    def load_map_entities(self, name, ox, oy):
        """name's NPCs, items and objects (from its file), at its place on the ground."""
        path = self.map_path(name)
        if not os.path.exists(path):
            return
        self.forget_map_npcs(name)
        lines = self.read_lines(path)
        for line in lines[self.yt:]:
            etype = trim(field(line, 1, "\t"))
            ename = trim(field(line, 2, "\t"))
            x = val(field(line, 3, "\t"))
            y = val(field(line, 4, "\t"))
            misc = trim(field(line, 5, "\t"))
            if etype == "MapItem" and trim(field(line, 6, "\t")):
                misc = trim(misc + " " + trim(field(line, 6, "\t")))       # the quantity, then its options (Id=, Once=)
            if etype == "MapItem" and self.once_key(ename, name, x, y, misc) in self.taken_once:
                continue                                                    # (a one-time item, already picked up)
            if etype in ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject", "Object", "Static"):
                if etype in ("GoodNPC", "BadNPC") and "ATTITUDE=" not in misc.upper():   # an old line: the type is
                    misc = trim(misc + " Attitude=" + attitude_of_type(etype))           # its attitude
                if etype in ("NPC", "GoodNPC", "BadNPC") and len(self.map_npcs) < 400:
                    self.map_npcs.append((ename, x, y, misc, name))
                e = self.add_entity_of_type(etype, ename, x + ox, y + oy, misc)
                if e is not None:
                    e.source = "MAP"
                    e.map = name

    def forget_map_npcs(self, name):
        self.map_npcs = [n for n in self.map_npcs if n[4] != name]

    def unload_map_entities(self, name):
        if not name:
            return
        for e in list(self.world):
            if e.map == name:
                self.remove_entity(e)
        self.forget_map_npcs(name)

    def remove_world_entities(self):
        """A teleport (or the first map): every NPC, item, object, missile, effect and health bar goes."""
        for e in list(self.world):
            self.remove_entity(e)
        self.world = []
        self.fx_clear()
        self.player.show_bar = False
        self.player_attack_target = None
        self.map_npcs = []

    def shift_entities(self, dx, dy):
        """Over a seam the current map changes: everything in the world moves by dx,dy (as the player did)."""
        for e in self.world:
            e.x += dx
            e.y += dy
            e.orig_x += dx
            e.orig_y += dy
            if e.target_x is not None:
                e.target_x += dx
            if e.target_y is not None:
                e.target_y += dy
            self.forget_path(e)
            a = e.ai
            if a is not None:
                a.zone = [a.zone[0] + dx, a.zone[1] + dy, a.zone[2] + dx, a.zone[3] + dy]
                a.chase = [a.chase[0] + dx, a.chase[1] + dy, a.chase[2] + dx, a.chase[3] + dy]
                a.goal_x += dx
                a.goal_y += dy
                a.back_x += dx
                a.back_y += dy
                a.home_ox += dx
                a.home_oy += dy
        for f in self.fx:
            f.x += dx
            f.y += dy

    def remove_old_screen_entities(self):
        xt, yt = self.xt, self.yt
        self.roof_name = grid2(xt, yt, "")
        self.roof_group = grid2(xt, yt, 0)
        self.roof_shown = grid2(xt, yt, 0)
        self.decor_name = grid2(xt, yt, "")
        st = self.store[5]
        for c in range(1, xt * yt + 1):
            st.decor[c] = ""
            st.roof[c] = ""
            st.infront[c] = ""
        self.fog_disabled = grid2(50, 50, 0)
        self.trigger_script = grid2(xt, yt, "")
        self.tile_locked = grid2(xt, yt, 0)
        self.locks = []
        self.doors_open = {}
        self.infront_ents = {}
        self.ab_items = []
        self.script_move_ent = None
        self.clicked_ent = None
        self.cursor_ent = None
        if self.item_in_use is not None and self.item_in_use.type != 14:
            self.item_in_use = None
        if self.rcm_open:
            self.close_right_click_menu()

    def load_and_draw_screen(self):
        self.log("Starting [Load.and.Draw.Screen] - " + self.screen_name)
        self.ground_hold = True
        self.remove_old_screen_entities()
        path = self.map_path(self.screen_name)
        xt, yt = self.xt, self.yt
        if not os.path.exists(path):
            self.log("ERROR - Map file '" + path + "' not found")
            for y in range(1, yt + 1):
                for x in range(1, xt + 1):
                    self.add_tile("Black001", x, y)
                    self.update_walk_grid_tile(x, y)
            return
        lines = self.read_lines(path)
        for y in range(1, yt + 1):
            data = trim(lines[y - 1]) if y - 1 < len(lines) else ""
            for x in range(1, xt + 1):
                cell = trim(word(data, x, ":"))
                tile = word(cell, 1, "+")
                if tile == "":
                    tile = "Black001"
                    self.log("ERROR - Map %s has no tile at %d,%d" % (self.screen_name, x, y))
                self.add_tile(tile, x, y)
                k = 2
                while word(cell, k, "+") != "":
                    overlay = word(cell, k, "+")
                    kind = word(overlay, 1, "(")
                    arg = word(word(overlay, 2, "("), 1, ")")
                    if kind == "Decor":
                        self.add_decor(arg, x, y)
                    elif kind == "Infront":
                        self.add_infront_tile(arg, x, y)
                    elif kind == "Roof":
                        self.add_roof(word(arg, 1, "."), val(word(arg, 2, ".")), x, y)
                    elif kind == "Trigger":
                        self.add_trigger(arg, x, y)
                    else:
                        self.log("ERROR - Unknown map overlay '%s' in %s" % (overlay, self.screen_name))
                    k += 1
            if self.loading_active and y % 3 == 0:
                self.loading_progress(0.2 + 0.7 * y / yt, "Drawing the map...")
        for data in lines[yt:]:
            etype = trim(field(data, 1, "\t"))
            ename = trim(field(data, 2, "\t"))
            ex = val(field(data, 3, "\t"))
            ey = val(field(data, 4, "\t"))
            misc = trim(field(data, 5, "\t"))
            if etype in ("NPC", "GoodNPC", "BadNPC", "MapItem", "StaticObject", "Object", "Static", ""):
                continue
            if etype == "Trigger":
                self.add_trigger(ename, ex, ey)
            elif etype == "Id":                                 # a named tile, for scripts and quests (places.py)
                pass
            elif etype == "Lock":
                self.add_lock(val(ename), ex, trim(field(data, 4, "\t")), misc)
            else:
                self.log("ERROR - Map entity type '%s' not recognised (%s)" % (etype, self.screen_name))
        self.check_locks(False)
        for y in range(1, yt + 1):
            for x in range(1, xt + 1):
                self.update_walk_grid_tile(x, y)
        self.log("Completed [Load.and.Draw.Screen]")

    def change_screen(self):
        ini.forget()  # Tiles.ini/Entities.ini are read again once per map, so edits made in the tools show up
        for cache in ("decor_tile_cache", "decor_object_cache", "anim_settings", "tile_flags", "tile_frame_info",
                      "anim_kinds", "decor_kinds", "decor_sway_px", "sway_cache", "decor_sway_cache", "flame_cache",
                      "tile_land", "tile_light_cache", "entity_light_cache", "footprint_cache", "door_kind_cache",
                      "warm_glows", "climate_cache"):
            self.__dict__.pop(cache, None)
        self.ground_recentre()
        self.time_mark("maps-round")
        self.load_and_draw_screen()
        self.time_mark("this-map")
        if self.fog_enabled:
            self.fog_last_x = -99999
        self.time_mark("fog")
        self.ground_hold = False
        self.paint_ground(0, 0, self.sw, self.sh)
        self.time_mark("paint")
        self.check_object_blocks(force=True)
        self.apply_queue_tiles()
        self.add_explored_map(self.screen_name)
        self.grave_place()
        self.build_minimap()
        self.time_mark("minimap")
        self.reset_player_tile()
        self.under_roof_group = None
        self.force_layer_update = True
        self.minimap_last = ""
        if self.script_exists(self.screen_name):
            self.start_script(self.screen_name, False)
        if self.main_setup_complete and (self.clock() - self.last_auto_save >= 60000 or self.clock() < self.last_auto_save):
            self.save_player()
            self.last_auto_save = self.clock()
            self.time_mark("save")

    def do_pending_map_change(self):
        self.pending_map_change = False
        if self.pending_map == "":
            self.pending_map = self.screen_name
        seam_x, seam_y = self.seam_shift_x, self.seam_shift_y
        self.seam_shift_x = self.seam_shift_y = 0
        seam_walk = None
        seam_action = None
        if (seam_x != 0 or seam_y != 0) and self.player_walk_active and self.pending_ent is None:
            seam_walk = (self.player_walk_x + seam_x, self.player_walk_y + seam_y, self.player_walk_speed,
                         self.player_walk_range)
        elif (seam_x != 0 or seam_y != 0) and self.player_walk_active and self.pending_ent is not None:
            # walking to do something on the next map: keep going and do it (what it was, where it was)
            e = self.pending_ent
            seam_action = (self.pending_verb, e, e.type, e.name, e.x, e.y, self.player_walk_speed,
                           self.player_walk_range)
        self.stop_player_walk()
        self.fx_clear()
        if self.pending_map == self.screen_name:
            self.set_entity_position(self.player, self.pending_x, self.pending_y)
            self.reset_player_tile()
            self.force_layer_update = True
            return
        if not self.map_exists(self.pending_map):
            self.log("ERROR - Map '%s' not found (teleport cancelled)" % self.pending_map)
            self.display_message("That leads nowhere!", "FAIL")
            return
        self.screen_name = self.pending_map
        self.player.x = self.pending_x
        self.player.y = self.pending_y
        if self.ab_mode:
            self.close_action_box(-1)
        self.cam_x += seam_x
        self.cam_y += seam_y
        self.cam_fx += seam_x
        self.cam_fy += seam_y
        if seam_x == 0 and seam_y == 0:
            self.cam_snap = True  # A teleport or a ladder: the view jumps there
        if seam_x != 0 or seam_y != 0:
            self.shift_entities(seam_x, seam_y)
        start = self.frame_clock()
        self.time_marks = []
        self.time_mark_last = start
        self.change_screen()
        self.log("Map change to %s took %d ms (%s)" % (self.screen_name, self.frame_clock() - start,
                                                      " ".join(self.time_marks)))
        self.time_mark_last = 0
        if seam_walk is not None:
            self.walk_player_to(*seam_walk)
        if seam_action is not None:
            self.resume_seam_action(seam_action, seam_x, seam_y)

    def resume_seam_action(self, action, dx, dy):
        """After crossing a seam: walk on to the thing the player was going to (moved by dx,dy with the maps), and
        do the verb there. A tile moves with them; an entity is the same one, or the one like it at its new place."""
        verb, e, etype, name, ex, ey, speed, rng = action
        if etype == TILE:
            e.x, e.y = ex + dx, ey + dy
            self.script_cursor_x += dx
            self.script_cursor_y += dy
            self.clicked_tile_x = self.tile_of_x(self.script_cursor_x)
            self.clicked_tile_y = self.tile_of_y(self.script_cursor_y)
        elif e not in self.world or not e.alive:
            e = next((w for w in self.world if w.alive and w.type == etype and w.name == name and
                      abs(w.x - (ex + dx)) < 2 and abs(w.y - (ey + dy)) < 2), None)
            if e is None:
                return
        self.walk_player_to(e.cx, e.cy, speed, rng)
        self.pending_verb = verb
        self.pending_ent = e

    def time_mark(self, label):
        now = self.frame_clock()
        if self.time_mark_last > 0 and now >= self.time_mark_last:
            self.time_marks.append("%s %d" % (label, now - self.time_mark_last))
        self.time_mark_last = now

    def check_player_off_screen(self):
        edge = self.pixel_off_screen(self.player.fx, self.player.fy)
        if edge == 0:
            return
        mx, my, mz = self.map_x(), self.map_y(), self.map_z()
        shift_x = shift_y = 0
        if edge == 1:
            my -= 1
            shift_y = self.sh
        elif edge == 2:
            mx += 1
            shift_x = -self.sw
        elif edge == 4:
            my += 1
            shift_y = -self.sh
        elif edge == 8:
            mx -= 1
            shift_x = self.sw
        new_map = self.make_map_name(mx, my, mz)
        if self.map_exists(new_map):
            self.pending_map = new_map
            self.pending_x = self.player.x + shift_x
            self.pending_y = self.player.y + shift_y
            self.seam_shift_x, self.seam_shift_y = shift_x, shift_y
            self.do_pending_map_change()
        else:
            self.set_entity_position(self.player, self.player_prev_x, self.player_prev_y)
            self.stop_player_walk()

    def pixel_off_screen(self, x, y):
        """x,y are the feet. 1 = north, 2 = east, 4 = south, 8 = west"""
        if x < 0:
            return 8
        if x >= self.sw:
            return 2
        if y < 0:
            return 1
        if y >= self.sh:
            return 4
        return 0

    def check_player_tile(self):
        """Fires trigger scripts when the player walks onto a new tile."""
        tx = self.tile_of_x(self.player.fx)
        ty = self.tile_of_y(self.player.fy)
        if tx == self.player_tile_x and ty == self.player_tile_y:
            return
        self.player_entry_x, self.player_entry_y = self.player_prev_x, self.player_prev_y
        self.player_tile_x, self.player_tile_y = tx, ty
        if self.trigger_script[tx][ty]:
            self.start_script(self.trigger_script[tx][ty], False)

    def reset_player_tile(self):
        self.player_tile_x = self.tile_of_x(self.player.fx)
        self.player_tile_y = self.tile_of_y(self.player.fy)
        self.player_entry_x, self.player_entry_y = self.player.x, self.player.y
        self.player_prev_x, self.player_prev_y = self.player_entry_x, self.player_entry_y

    # =================================================================================================================
    # Tiles, roofs, tree tops, triggers
    # =================================================================================================================
    def add_tile(self, name, x, y):
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            return
        decor = self.decor_name[x][y]
        self.tile_walk[x][y], self.tile_los[x][y] = self.cell_walk_los(name, decor)
        self.tile_speed[x][y] = self.cell_speed(name, decor)
        self.tile_name[x][y] = name
        self.w_set(x + self.xt, y + self.yt, name)
        self.paint_ground((x - 1) * self.tw, (y - 1) * self.th, x * self.tw, y * self.th)

    def add_decor(self, name, x, y):
        """Current-map tile x,y's decor ("" takes it away)."""
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            return
        self.decor_name[x][y] = name
        self.w_set_decor(x + self.xt, y + self.yt, name)
        tile = self.tile_name[x][y]
        if tile:
            self.tile_walk[x][y], self.tile_los[x][y] = self.cell_walk_los(tile, name)
            self.tile_speed[x][y] = self.cell_speed(tile, name)
        self.paint_ground((x - 1) * self.tw, (y - 1) * self.th, x * self.tw, y * self.th)

    def ground_speed(self, e):
        """How fast entity e can walk on the tile under its feet (Tiles.ini Walk.Speed). Fliers ignore it."""
        if e.ai is not None and e.ai.flying:
            return 1
        s = self.tile_speed[self.tile_of_x(e.fx)][self.tile_of_y(e.fy)]
        return s if s > 0 else 1

    def change_tile(self, x, y, name, keep_decor=True):
        """name is a cell spec (cell_spec): a ground tile, a decor tile (only the decor changes) or Tile+Decor(Name).
        keep_decor=False (a script's Change.Tile): a ground tile on its own takes the decor away, as the cell becomes
        that tile (a fallen log chopped to grass). Doors and gates keep theirs."""
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            self.log("ERROR - Change.Tile: tile %s,%s is off the map" % (lbstr(x), lbstr(y)))
            return
        tile, decor = self.cell_spec(name)
        if not tile and decor is None:
            return
        if tile and decor is None and not keep_decor:
            decor = ""
        if decor is not None:
            self.decor_name[x][y] = decor                # (so add_tile works the walk mask out with it)
        if tile:
            self.add_tile(tile, x, y)
        if decor is not None:
            self.add_decor(decor, x, y)
        self.update_walk_grid_tile(x, y)
        self.force_layer_update = True

    def change_all_tiles(self, source, target):
        """Every tile (or decor) of the current map that is source, or source with any number (Tree), becomes target."""
        for y in range(1, self.yt + 1):
            for x in range(1, self.xt + 1):
                for name in (self.tile_name[x][y], self.decor_name[x][y]):
                    if name and (name == source or strip_digits(name) == source):
                        self.change_tile(x, y, target, keep_decor=False)
                        break

    def spec_blocks(self, spec):
        """Would changing a cell to spec put something you can't walk through on it?"""
        tile, decor = self.cell_spec(spec)
        return any(n and self.tile_walk_data(n) != self.all_walkable for n in (tile, decor))

    def add_roof(self, name, group, x, y):
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            return
        self.roof_name[x][y] = name
        self.roof_group[x][y] = group
        self.roof_shown[x][y] = 1
        f = self.w_find(x + self.xt, y + self.yt)
        if f:
            f[0].roof[f[1]] = name
        self.paint_ground((x - 1) * self.tw, (y - 1) * self.th, x * self.tw, y * self.th)

    def add_infront_tile(self, name, x, y):
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            return
        f = self.w_find(x + self.xt, y + self.yt)
        if f:
            f[0].infront[f[1]] = name
        e = Entity(INFRONTTILE, name)
        e.x = (x - 1) * self.tw
        e.y = (y - 1) * self.th
        e.w, e.h = self.tw, self.th
        e.misc = self.tile_ini(name, "Show.Name", "0")
        e.use_words = self.tile_ini(name, "Use.Words", "")
        e.image = name
        self.infront_ents[(x, y)] = e

    def add_trigger(self, script, x, y):
        script = trim(script)
        if script.lower().endswith(".txt"):
            script = script[:-4]
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            self.log("ERROR - Trigger '%s' at %s,%s is off the map" % (script, lbstr(x), lbstr(y)))
            return
        self.trigger_script[x][y] = script
        self.log("Trigger Added: %s at %s,%s" % (script, lbstr(x), lbstr(y)))

    # ----- Doors (Tiles.ini Open.Tile): a door opens as someone (the player, an NPC) comes to it, and shuts behind them
    DOOR_REACH = 34             # pixels from the feet to the door tile's middle
    DOOR_SHUT_MS = 1500         # how long a door stays open once nobody is at it

    def door_kind(self, name):
        """Tiles.ini Door=: "1" a door (townsfolk go home through it at night), "Gate" a gateway nobody lives behind,
        "" neither. Either is a doorway: standing in it under a roof's edge you see inside."""
        cache = self.__dict__.setdefault("door_kind_cache", {})
        if name not in cache:
            v = trim(self.tile_ini(name, "Door", "")) if name else ""
            cache[name] = "" if v in ("", "0") else ("Gate" if v.lower() == "gate" else "1")
        return cache[name]

    def is_door_tile(self, name):
        return self.door_kind(name) == "1"

    def door_open_tile(self, name):
        cache = self.__dict__.setdefault("door_open_cache", {})
        if name not in cache:
            cache[name] = self.tile_ini(name, "Open.Tile", "") if name else ""
        return cache[name]

    def update_doors(self):
        now = self.loop_start
        if 0 <= now - getattr(self, "door_check_at", -10 ** 9) < 100:
            return
        self.door_check_at = now
        opened = self.__dict__.setdefault("doors_open", {})
        near = set()
        for e in [self.player] + [e for e in self.world if e.type == NPC and e.alive and e.active]:
            fx, fy = e.fx, e.fy
            tx, ty = self.tile_of_x(fx), self.tile_of_y(fy)
            for y in range(max(1, ty - 1), min(self.yt, ty + 1) + 1):
                for x in range(max(1, tx - 1), min(self.xt, tx + 1) + 1):
                    if distance(fx, fy, (x - 0.5) * self.tw, (y - 0.5) * self.th) <= self.DOOR_REACH:
                        near.add((x, y))
        for x, y in near:
            if (x, y) in opened:
                opened[(x, y)][1] = now
                continue
            name = self.tile_name[x][y]
            o = self.door_open_tile(name)
            if not o or self.tile_locked[x][y] or any(lk[0] == x and lk[1] == y and lk[6] for lk in self.locks):
                continue                    # (not a door, locked, or a gate its lock draws open and shut)
            opened[(x, y)] = [name, now]
            self.change_tile(x, y, o)
            self.play_sound("Door", ((x - 0.5) * self.tw, (y - 0.5) * self.th))
        for (x, y), (closed, t) in list(opened.items()):
            if (x, y) not in near and not 0 <= now - t < self.DOOR_SHUT_MS:
                del opened[(x, y)]
                if self.tile_name[x][y] == self.door_open_tile(closed):
                    self.change_tile(x, y, closed)

    def update_roof_tiles(self):
        """Standing under a roof hides every roof tile of its group; so does standing in a doorway with your head
        under the roof's edge (going in at the front). Outside a house's back or side wall it doesn't: no peeking in."""
        pl = self.player
        group = 0
        fx, fy = self.tile_of_x(pl.fx), self.tile_of_y(pl.fy)
        in_door = bool(self.door_open_tile(self.tile_name[fx][fy])) or bool(self.door_kind(self.tile_name[fx][fy]))
        for py in ((pl.fy, pl.y + pl.h / 4) if in_door else (pl.fy,)):    # the feet (then the head, in a doorway)
            rx, ry = self.tile_of_x(pl.fx), self.tile_of_y(py)
            if self.roof_name[rx][ry]:
                group = self.roof_group[rx][ry]
                break
        if group == self.under_roof_group and not self.force_layer_update:
            return
        if bool(group) != bool(self.under_roof_group):
            self.last_music_check = -10 ** 9           # in or out of a building: the music and sounds see it next frame
        self.under_roof_group = group
        for y in range(1, self.yt + 1):
            for x in range(1, self.xt + 1):
                if self.roof_name[x][y]:
                    shown = 0 if (self.roof_group[x][y] == group and group != 0) else 1
                    if shown != self.roof_shown[x][y]:
                        self.roof_shown[x][y] = shown
                        self.paint_ground((x - 1) * self.tw, (y - 1) * self.th, x * self.tw, y * self.th)

    def ground_tile_at(self, px, py):
        """The tile at world pixel px,py as a Tile entity (None = none, or a roof or black fog is over it): its decor
        if it has one (the chair, not the floor under it). px,py can be on any of the maps round the current one that
        are on the screen."""
        sx, sy = math.floor(px / self.sw), math.floor(py / self.sh)      # -1, 0 or 1: which map, from the current one
        if not (-1 <= sx <= 1 and -1 <= sy <= 1):
            return None
        slot = (sy + 1) * 3 + sx + 2
        if not self.slot_map[slot]:
            return None
        if self.roof_covers(px, py):
            return None
        lx, ly = px - sx * self.sw, py - sy * self.sh                    # pixel on that map
        if self.fog_enabled:
            c = (self.fog_cell_y(ly) - 1) * self.fog_xt + self.fog_cell_x(lx)
            if self.wfog_shown[slot][c] == 1 and self.wfog_black[slot][c] == 1:
                return None
        tx = self.tile_of_x(lx)
        ty = self.tile_of_y(ly)
        if slot == 5:
            name = self.decor_name[tx][ty] or self.tile_name[tx][ty]
        else:
            f = self.w_find((sx + 1) * self.xt + tx, (sy + 1) * self.yt + ty)
            name = (f[0].decor[f[1]] or f[0].tile[f[1]]) if f else ""
        if not name or name == "Black001":
            return None
        tx += sx * self.xt                                              # where it is, from the current map
        ty += sy * self.yt
        e = self.hover_tile
        if e.name != name or e.x != (tx - 1) * self.tw or e.y != (ty - 1) * self.th or getattr(e, "off_map", False) != (slot != 5):
            e = Entity(TILE, name)
            e.x = (tx - 1) * self.tw
            e.y = (ty - 1) * self.th
            e.w, e.h = self.tw, self.th
            e.misc = self.tile_ini(name, "Show.Name", "0")
            e.use_words = self.tile_ini(name, "Use.Words", "")
            e.off_map = slot != 5
            self.hover_tile = e
        return e

    # =================================================================================================================
    # Fog of war: each slot's cells are in wfog_shown/wfog_black[slot][cell], cell = (y-1)*fog_xt+x
    # =================================================================================================================
    def fog_cell_left(self, x):
        return (x - 1) * (self.fog_w - self.fog_border * 2) + self.fog_x_offset - self.fog_border

    def fog_cell_top(self, y):
        return (y - 1) * (self.fog_h - self.fog_border * 2) - self.fog_border

    def fog_cell_x(self, px):
        step = max(1, self.fog_w - self.fog_border * 2)
        return min(max(int((px - self.fog_x_offset) / step) + 1, 1), max(1, self.fog_xt))

    def fog_cell_y(self, py):
        step = max(1, self.fog_h - self.fog_border * 2)
        return min(max(int(py / step) + 1, 1), max(1, self.fog_yt))

    def fog_covers(self, px, py):
        if not self.fog_enabled:
            return False
        sx = int((px + self.sw) / self.sw)
        sy = int((py + self.sh) / self.sh)
        if px + self.sw < 0 or py + self.sh < 0 or sx > 2 or sy > 2:
            return True
        lx = px - (sx - 1) * self.sw
        ly = py - (sy - 1) * self.sh
        return self.wfog_shown[sy * 3 + sx + 1][(self.fog_cell_y(ly) - 1) * self.fog_xt + self.fog_cell_x(lx)] == 1

    def roof_covers(self, px, py):
        """A roof that is showing is over pixel px,py (the other maps' roofs always show)."""
        if px < 0 or py < 0 or px >= self.sw or py >= self.sh:
            f = self.w_find(int((px + self.sw) / self.tw) + 1, int((py + self.sh) / self.th) + 1)
            return bool(f and f[0].roof[f[1]])
        tx = self.tile_of_x(px)
        ty = self.tile_of_y(py)
        return bool(self.roof_name[tx][ty]) and self.roof_shown[tx][ty] == 1

    def fog_cell_explored(self, name, x, y):
        return name in self.explored_all or (x, y) in self.explored_cells.get(name, ())

    def mark_explored(self, name, x, y):
        self.explored_cells.setdefault(name, set()).add((x, y))

    def fog_set(self, slot, x, y, shown):
        c = (y - 1) * self.fog_xt + x
        if self.wfog_shown[slot][c] == shown:
            return
        self.wfog_shown[slot][c] = shown
        if shown == 0:
            self.wfog_black[slot][c] = 0
            name = self.slot_map[slot]
            if not self.fog_cell_explored(name, x, y):
                self.mark_explored(name, x, y)
                self.add_explored_map(name)
            self.hid.append((slot, c))
        self.fog_version += 1

    def update_window_fog(self, px, py):
        """px,py = the player's centre (current map pixels)."""
        v = self.fog_view_distance + self.spell_sight_bonus
        mw, mh = self.sw, self.sh
        xt, yt = self.fog_xt, self.fog_yt
        half_w = self.fog_w / 2
        half_h = self.fog_h / 2
        k = 0
        while k < len(self.hid):
            slot, c = self.hid[k]
            x = ((c - 1) % xt) + 1
            y = int((c - 1) / xt) + 1
            i = ((slot - 1) % 3) - 1
            j = int((slot - 1) / 3) - 1
            keep = self.fog_all_disabled
            if slot == 5 and self.fog_disabled[x][y]:
                keep = True
            if distance(i * mw + self.fog_cell_left(x) + half_w, j * mh + self.fog_cell_top(y) + half_h, px, py) < v:
                keep = True
            if not keep:
                self.hid[k] = self.hid[-1]
                self.hid.pop()
                self.fog_set(slot, x, y, 1)
            else:
                k += 1
        for slot in range(1, 10):
            if not self.slot_map[slot]:
                continue
            i = ((slot - 1) % 3) - 1
            j = int((slot - 1) / 3) - 1
            lx = px - i * mw
            ly = py - j * mh
            if self.fog_all_disabled:
                fx1, fx2, fy1, fy2 = 1, xt, 1, yt
            else:
                fx1 = self.fog_cell_x(lx - v)
                fx2 = self.fog_cell_x(lx + v)
                fy1 = self.fog_cell_y(ly - v)
                fy2 = self.fog_cell_y(ly + v)
                if lx + v < -self.fog_w or lx - v > mw + self.fog_w or ly + v < -self.fog_h or ly - v > mh + self.fog_h:
                    fx2 = 0
            shown = self.wfog_shown[slot]
            for y in range(fy1, fy2 + 1):
                for x in range(fx1, fx2 + 1):
                    if shown[(y - 1) * xt + x] == 1:
                        if self.fog_all_disabled:
                            self.fog_set(slot, x, y, 0)
                        elif distance(self.fog_cell_left(x) + half_w, self.fog_cell_top(y) + half_h, lx, ly) < v:
                            self.fog_set(slot, x, y, 0)

    def fog_reset_slot(self, slot):
        name = self.slot_map[slot]
        xt = self.fog_xt
        shown = self.wfog_shown[slot]
        black = self.wfog_black[slot]
        for y in range(1, self.fog_yt + 1):
            for x in range(1, xt + 1):
                c = (y - 1) * xt + x
                shown[c] = 1
                black[c] = 1
                if name and self.fog_cell_explored(name, x, y):
                    black[c] = 0
        self.fog_version += 1

    def shift_fog(self, sx, sy):
        old_shown = list(self.wfog_shown)
        old_black = list(self.wfog_black)
        n = self.fog_xt * self.fog_yt + 1
        for slot in range(1, 10):
            oi = ((slot - 1) % 3) - 1 + sx
            oj = int((slot - 1) / 3) - 1 + sy
            if abs(oi) <= 1 and abs(oj) <= 1:
                o = (oj + 1) * 3 + oi + 2
                self.wfog_shown[slot] = old_shown[o]
                self.wfog_black[slot] = old_black[o]
            else:
                self.wfog_shown[slot] = [1] * n
                self.wfog_black[slot] = [1] * n
        hid = []
        for slot, c in self.hid:
            i = ((slot - 1) % 3) - 1 - sx
            j = int((slot - 1) / 3) - 1 - sy
            if abs(i) <= 1 and abs(j) <= 1:
                hid.append(((j + 1) * 3 + i + 2, c))
        self.hid = hid
        self.fog_version += 1

    def update_fog_of_war(self):
        pcx, pcy = self.player.cx, self.player.cy
        if not self.force_layer_update and abs(pcx - self.fog_last_x) < 4 and abs(pcy - self.fog_last_y) < 4:
            return
        self.fog_last_x, self.fog_last_y = pcx, pcy
        self.update_window_fog(pcx, pcy)

    def reveal_fog_cell(self, cell):
        """Reveal.BlackOut.Tile: a cell number on the fog grid (row-major, 1 = top-left) or "x,y"."""
        if "," in cell:
            x = val(word(cell, 1, ","))
            y = val(word(cell, 2, ","))
        else:
            n = val(cell)
            x = ((n - 1) % max(1, self.fog_xt)) + 1
            y = int((n - 1) / max(1, self.fog_xt)) + 1
        if x < 1 or y < 1 or x > self.fog_xt or y > self.fog_yt:
            self.log("ERROR - Reveal.BlackOut.Tile: no fog cell '%s'" % cell)
            return
        self.mark_explored(self.screen_name, x, y)
        self.fog_disabled[x][y] = 1
        if self.ground_ready and self.fog_enabled:
            self.fog_set(5, x, y, 0)
        self.force_layer_update = True

    def add_explored_map(self, name):
        if name and name not in self.explored_maps:
            self.explored_maps.append(name)
            if self.minimap_available:
                self.build_minimap()

    # =================================================================================================================
    # Walkability
    # =================================================================================================================
    def pixel_walkable(self, who, x, y):
        """x,y in the current map's pixels; the maps around it are walkable too. who = the player sets lock_bumped."""
        if x < 0 or y < 0 or x >= self.sw or y >= self.sh:
            return self.window_pixel_walkable(x, y)
        tx = int(x / self.tw) + 1
        ty = int(y / self.th) + 1
        if self.tile_locked[tx][ty] > 0:
            if who is self.player:
                self.lock_bumped = self.tile_locked[tx][ty]
            return False
        res = self.walk_res
        xp = int(((x - (tx - 1) * self.tw) / self.tw) * res)
        yp = int(((y - (ty - 1) * self.th) / self.th) * res)
        walk = self.tile_walk[tx][ty]
        p = xp + res * yp
        if not (p < len(walk) and walk[p] == "1"):
            return False
        blocked = self.object_blocks.get((tx + self.xt, ty + self.yt))
        return not (blocked and p in blocked)

    def window_pixel_walkable(self, x, y):
        if x + self.sw < 0 or y + self.sh < 0:
            return False
        wx = int((x + self.sw) / self.tw) + 1
        wy = int((y + self.sh) / self.th) + 1
        f = self.w_find(wx, wy)
        if f is None:
            return False
        st, c = f
        if st.tile[c] == "" or st.lock[c] == 1:
            return False
        res = self.walk_res
        xp = int(((x + self.sw - (wx - 1) * self.tw) / self.tw) * res)
        yp = int(((y + self.sh - (wy - 1) * self.th) / self.th) * res)
        walk = st.walk[c]
        p = xp + res * yp
        if not (p < len(walk) and walk[p] == "1"):
            return False
        blocked = self.object_blocks.get((wx, wy))
        return not (blocked and p in blocked)

    # =================================================================================================================
    # Object footprints: Entities.ini Walkable.Data on an object (or a decor tile placed as one: its Tiles.ini grid) is
    # a grid of 0 (blocked) and 1 over its sprite, walk_res cells to a tile each way (a 32 x 32 object: 7 x 7, as a
    # tile's). Its blocked cells go on the walk grid where it stands, so nobody walks through a workbench.
    # =================================================================================================================
    def object_footprint(self, name, w, h):
        """(cols, rows, data) of object name's footprint at its size w x h, or None (you walk through it)."""
        cache = self.__dict__.setdefault("footprint_cache", {})
        key = (name, w, h)
        if key not in cache:
            data = trim(self.entity_ini(name, "Walkable.Data", ""))
            res = self.walk_res
            cols = max(1, int(round(w * res / self.tw)))
            rows = max(1, int(round(h * res / self.th)))
            fp = None
            if data and "0" in data:
                if len(data) == cols * rows and not set(data) - {"0", "1"}:
                    fp = (cols, rows, data)
                else:
                    self.log("ERROR - %s: Walkable.Data has %d cells; its %dx%d sprite needs %d x %d = %d" % (
                        name, len(data), w, h, cols, rows, cols * rows))
            cache[key] = fp
        return cache[key]

    def check_object_blocks(self, force=False):
        """The objects' footprints on the walk grid again, if an object came, went, moved or changed (once a frame)."""
        sig = tuple((e.uid, int(e.x), int(e.y), e.name) for e in self.world if e.type == STATICOBJECT and e.alive)
        if sig == self.object_sig and not force:
            return
        self.object_sig = sig
        res, tw, th = self.walk_res, self.tw, self.th
        new = {}
        for e in self.world:
            if e.type != STATICOBJECT or not e.alive:
                continue
            fp = self.object_footprint(e.name, e.w, e.h)
            if fp is None:
                continue
            cols, rows, data = fp
            cw, ch = e.w / cols, e.h / rows
            for i, v in enumerate(data):
                if v != "0":
                    continue
                for fx in (0.25, 0.75):             # (four points of each blocked cell: no gaps when it's off the grid)
                    for fy in (0.25, 0.75):
                        gx = e.x + (i % cols + fx) * cw + self.sw
                        gy = e.y + (i // cols + fy) * ch + self.sh
                        if gx < 0 or gy < 0:
                            continue
                        wx, wy = int(gx // tw) + 1, int(gy // th) + 1
                        p = int((gx % tw) * res / tw) + res * int((gy % th) * res / th)
                        new.setdefault((wx, wy), set()).add(p)
        old = self.object_blocks
        self.object_blocks = new
        for cell in set(old) | set(new):
            if old.get(cell) != new.get(cell):
                self.update_walk_grid_wtile(*cell)

    # =================================================================================================================
    # Line of sight
    # =================================================================================================================
    def window_los(self, wx, wy):
        lx = wx - self.xt
        ly = wy - self.yt
        if 1 <= lx <= self.xt and 1 <= ly <= self.yt:
            return self.tile_los[lx][ly]
        f = self.w_find(wx, wy)
        if f:
            return f[0].los[f[1]]
        return 1

    def in_line_of_sight(self, x1, y1, x2, y2):
        """False if a tile with Line.of.Sight=0 lies between the two points."""
        d = distance(x1, y1, x2, y2)
        if d < 1:
            return True
        sw, sh, tw, th = self.sw, self.sh, self.tw, self.th
        start = (int((x1 + sw) / tw) + 1, int((y1 + sh) / th) + 1)
        finish = (int((x2 + sw) / tw) + 1, int((y2 + sh) / th) + 1)
        steps = int(d / 4) + 1
        for i in range(1, steps + 1):
            t = (int((x1 + (x2 - x1) * i / steps + sw) / tw) + 1, int((y1 + (y2 - y1) * i / steps + sh) / th) + 1)
            if t == start or t == finish:
                continue
            if self.window_los(t[0], t[1]) == 0:
                return False
        return True

    # =================================================================================================================
    # Locks: map lines Lock<TAB>TileX<TAB>TileY<TAB>Condition<TAB>Message. tile_locked[x][y] = lock number while locked
    # =================================================================================================================
    def add_lock(self, x, y, condition, message):
        if x < 1 or y < 1 or x > self.xt or y > self.yt:
            self.log("ERROR - Lock at %s,%s is off the map (%s)" % (lbstr(x), lbstr(y), self.screen_name))
            return
        if len(self.locks) >= 100:
            self.log("ERROR - Too many Lock lines in " + self.screen_name)
            return
        # [5], [6]: the tile as the map has it, and Tiles.ini Unlocked.Tile (the picture while it's open, "" = the same)
        closed = self.tile_name[int(x)][int(y)]
        self.locks.append([x, y, condition, message or "It's locked.", 0, closed,
                           self.tile_ini(closed, "Unlocked.Tile", "") if closed else ""])

    def check_locks(self, announce):
        """Evaluates every Lock's condition again; a lock that opens or closes changes the walk grid (and the tile, if
        it has an Unlocked.Tile: a gate drawn shut while locked and open once its condition is met)."""
        for i, lk in enumerate(self.locks, 1):
            locked = 1
            if trim(lk[2]) != "" and self.condition_met(lk[2]):
                locked = 0
            if lk[6]:
                want = lk[5] if locked else lk[6]
                if self.tile_name[lk[0]][lk[1]] != want:
                    self.change_tile(lk[0], lk[1], want)
            if locked != lk[4]:
                lk[4] = locked
                x, y = lk[0], lk[1]
                self.tile_locked[x][y] = i if locked == 1 else 0
                self.update_walk_grid_tile(x, y)
                if locked == 0 and announce:
                    if distance(self.player.cx, self.player.cy, (x - 0.5) * self.tw, (y - 0.5) * self.th) < 160:
                        self.display_message("You hear a click.", "INFO")
                        self.play_sound("Door", ((x - 0.5) * self.tw, (y - 0.5) * self.th))
        self.check_neighbour_locks()

    def check_neighbour_locks(self):
        """The maps round the current one: their locked tiles with an Unlocked.Tile (a town gate seen from outside the
        town's map) open or shut with their condition too."""
        xt, yt = self.xt, self.yt
        for slot in range(1, 10):
            st = self.store[slot]
            if slot == 5 or not st.locks:
                continue
            ox = ((slot - 1) % 3) * xt
            oy = int((slot - 1) / 3) * yt
            for x, y, condition, closed, opened in st.locks:
                locked = 0 if condition and self.condition_met(condition) else 1
                c = (y - 1) * xt + x
                want = closed if locked else opened
                if st.tile[c] != want:
                    self.w_set(ox + x, oy + y, want)
                    for wy in range(oy + y - 1, oy + y + 2):
                        for wx in range(ox + x - 1, ox + x + 2):
                            self.paint_window_cell(wx, wy)
                if st.lock[c] != locked:
                    st.lock[c] = locked
                    self.update_walk_grid_wtile(ox + x, oy + y)

    def lock_at(self, tx, ty):
        for i, lk in enumerate(self.locks, 1):
            if lk[0] == tx and lk[1] == ty:
                return i
        return 0

    def tile_lock_of(self, e):
        if e is None or e.type != TILE:
            return 0
        return self.tile_locked[self.tile_of_x(e.x)][self.tile_of_y(e.y)]

    def lock_message(self, n):
        return self.locks[n - 1][3] if 1 <= n <= len(self.locks) else "It's locked."

    def lock_bump(self, n):
        now = self.loop_start
        if n != self.lock_bump_last or now - self.lock_bump_time > 1500 or now < self.lock_bump_time:
            self.display_message(self.lock_message(n), "FAIL")
            self.play_sound("Locked")
        self.lock_bump_last = n
        self.lock_bump_time = now

    # =================================================================================================================
    # Pathfinding: walk_grid has one cell per half tile (grid_cell pixels, grid_w x grid_h, index = y*grid_w+x), 1 = the
    # feet can stand there. It covers the 9 maps: cell 0,0 is at current-map pixel grid_ox, grid_oy.
    # =================================================================================================================
    def build_walk_grid(self):
        self.grid_w = 0
        self.grid_cell = max(4, int(min(self.tw, self.th) / 2))
        if int(3 * self.sw / self.grid_cell) * int(3 * self.sh / self.grid_cell) > 19000:
            self.log("ERROR - The maps are too big for the walk grid: no pathfinding")
            return
        self.grid_h = int(3 * self.sh / self.grid_cell)
        self.grid_w = int(3 * self.sw / self.grid_cell)
        self.grid_ox = -self.sw
        self.grid_oy = -self.sh
        self.walk_grid = bytearray(self.grid_w * self.grid_h)
        for wy in range(1, 3 * self.yt + 1):
            for wx in range(1, 3 * self.xt + 1):
                self.update_walk_grid_wtile(wx, wy)
        self.grid_regions_dirty = True

    def shift_walk_grid(self, sx, sy):
        if self.grid_w == 0:
            return
        w, h = self.grid_w, self.grid_h
        dx = sx * int(w / 3)
        dy = sy * int(h / 3)
        old = self.walk_grid
        new = bytearray(w * h)
        for cy in range(h):
            oy = cy + dy
            if oy < 0 or oy >= h:
                continue
            x1 = max(0, -dx)
            x2 = min(w, w - dx)
            if x2 > x1:
                new[cy * w + x1:cy * w + x2] = old[oy * w + x1 + dx:oy * w + x2 + dx]
        self.walk_grid = new
        self.grid_regions_dirty = True

    def update_walk_grid_tile(self, tx, ty):
        if tx < 1 or ty < 1 or tx > self.xt or ty > self.yt:
            return
        self.update_walk_grid_wtile(tx + self.xt, ty + self.yt)

    def update_walk_grid_wtile(self, wx, wy):
        if self.grid_w == 0:
            return
        if wx < 1 or wy < 1 or wx > 3 * self.xt or wy > 3 * self.yt:
            return
        self.grid_regions_dirty = True
        uniform = -1
        lx = wx - self.xt
        ly = wy - self.yt
        if 1 <= lx <= self.xt and 1 <= ly <= self.yt:
            if self.tile_locked[lx][ly] > 0:
                uniform = 0
            else:
                walk = self.tile_walk[lx][ly]
                if "0" not in walk:
                    uniform = 1
                if "1" not in walk:
                    uniform = 0
        else:
            f = self.w_find(wx, wy)
            if f is None:
                return
            st, c = f
            if st.tile[c] == "" or st.lock[c] == 1:
                uniform = 0
            else:
                if "0" not in st.walk[c]:
                    uniform = 1
                if "1" not in st.walk[c]:
                    uniform = 0
        if uniform == 1 and (wx, wy) in self.object_blocks:
            uniform = -1                            # (an object's footprint on it: cell by cell)
        cell = self.grid_cell
        left = (wx - 1) * self.tw
        top = (wy - 1) * self.th
        for cy in range(int(top / cell), min(self.grid_h - 1, int((top + self.th - 1) / cell)) + 1):
            for cx in range(int(left / cell), min(self.grid_w - 1, int((left + self.tw - 1) / cell)) + 1):
                inside = (cx * cell >= left and (cx + 1) * cell <= left + self.tw and cy * cell >= top and
                          (cy + 1) * cell <= top + self.th)
                if inside and uniform >= 0:
                    self.walk_grid[cy * self.grid_w + cx] = uniform
                else:
                    self.walk_grid[cy * self.grid_w + cx] = self.cell_walkable_calc(cx, cy)

    def cell_walkable_calc(self, cx, cy):
        """A cell is walkable if the feet can stand at its centre and at 7 of the 8 points around it."""
        cell = self.grid_cell
        x0 = cx * cell + self.grid_ox
        y0 = cy * cell + self.grid_oy
        m = int(cell / 2)
        q = int(cell / 5)
        f = cell - q
        pw = self.pixel_walkable
        if not pw(None, x0 + m, y0 + m):
            return 0
        count = (pw(None, x0 + q, y0 + q) + pw(None, x0 + m, y0 + q) + pw(None, x0 + f, y0 + q) +
                 pw(None, x0 + q, y0 + m) + pw(None, x0 + f, y0 + m) + pw(None, x0 + q, y0 + f) +
                 pw(None, x0 + m, y0 + f) + pw(None, x0 + f, y0 + f))
        return 1 if count >= 7 else 0

    def path_goal_key(self, x, y, rng):
        return "%d,%d,%s" % (int(x / self.grid_cell), int(y / self.grid_cell), lbstr(rng))

    def grid_line_walkable(self, x1, y1, x2, y2):
        if self.grid_w == 0:
            return True
        d = distance(x1, y1, x2, y2)
        steps = int(d / 6) + 1
        cell = self.grid_cell
        ox, oy = self.grid_ox, self.grid_oy
        w, h = self.grid_w, self.grid_h
        grid = self.walk_grid
        last_x = int((x1 - ox) / cell)
        last_y = int((y1 - oy) / cell)
        for i in range(1, steps + 1):
            cx = int((x1 + (x2 - x1) * i / steps - ox) / cell)
            cy = int((y1 + (y2 - y1) * i / steps - oy) / cell)
            if cx != last_x or cy != last_y:
                if cx < 0 or cy < 0 or cx >= w or cy >= h:
                    return False
                if grid[cy * w + cx] == 0:
                    return False
                if cx != last_x and cy != last_y:
                    if 0 <= last_x < w and 0 <= last_y < h:
                        if grid[last_y * w + cx] == 0 or grid[cy * w + last_x] == 0:
                            return False
                last_x, last_y = cx, cy
        return True

    PF_DIRS = ((0, -1, 10), (1, 0, 10), (0, 1, 10), (-1, 0, 10), (1, -1, 14), (1, 1, 14), (-1, 1, 14), (-1, -1, 14))

    def plan_path(self, e, target_x, target_y, rng, budget):
        """A path for entity e so its centre gets within rng of the target (A*, 8 directions, no corner cutting,
        octile heuristic x1.2, then string pulling). The waypoints go in e.path (empty = walk straight)."""
        e.path = []
        e.path_best = None
        e.path_stuck = 0
        e.path_time = self.loop_start + 400
        if not self.pathfinding_enabled or self.grid_w == 0:
            return False
        self.pf_searches += 1
        feet_offset = e.fy - e.cy
        sx, sy = e.fx, e.fy
        tx = target_x
        ty = target_y + feet_offset
        ox, oy = self.grid_ox, self.grid_oy
        cell, w, h = self.grid_cell, self.grid_w, self.grid_h
        tx = min(max(tx, ox), ox + w * cell - 1)
        ty = min(max(ty, oy), oy + h * cell - 1)
        d = distance(sx, sy, tx, ty)
        if d <= rng:
            return True
        reach = (d - max(0, rng - 2)) / d
        if self.grid_line_walkable(sx, sy, sx + (tx - sx) * reach, sy + (ty - sy) * reach):
            return True
        grid = self.walk_grid
        radius = max(rng - 2, int(cell * 0.75))
        r2 = radius * radius
        range_cost = int(radius / cell * 10)
        scx = min(max(int((sx - ox) / cell), 0), w - 1)
        scy = min(max(int((sy - oy) / cell), 0), h - 1)
        start = scy * w + scx
        if grid[start] == 0:
            best_d = 999999
            new_start = -1
            for ddx, ddy, _ in self.PF_DIRS:
                mx, my = scx + ddx, scy + ddy
                if 0 <= mx < w and 0 <= my < h and grid[my * w + mx] == 1:
                    dd = abs(mx * cell + cell / 2 + ox - sx) + abs(my * cell + cell / 2 + oy - sy)
                    if dd < best_d:
                        best_d = dd
                        new_start = my * w + mx
            if new_start < 0:
                e.path_time = self.loop_start + 2000
                return False
            start = new_start
            scx, scy = start % w, int(start / w)
        gcx = min(max(int((tx - ox) / cell), 0), w - 1)
        gcy = min(max(int((ty - oy) / cell), 0), h - 1)

        def octile(x, y):
            hx = abs(x - gcx)
            hy = abs(y - gcy)
            return 10 * hx + 4 * hy if hx > hy else 10 * hy + 4 * hx

        g_cost = {start: 0}
        parent = {start: -1}
        done = set()
        hm = octile(scx, scy)
        best_node, best_h = start, hm
        heap = [(max(0, hm - range_cost), 0, start)]
        counter = 0
        found = -1
        expansions = 0
        half = cell / 2
        while heap:
            _, _, n = heapq.heappop(heap)
            if n in done:
                continue
            done.add(n)
            nx, ny = n % w, int(n / w)
            ddx = nx * cell + half + ox - tx
            ddy = ny * cell + half + oy - ty
            if ddx * ddx + ddy * ddy <= r2:
                found = n
                break
            hm = octile(nx, ny)
            if hm < best_h:
                best_h, best_node = hm, n
            expansions += 1
            if expansions > budget:
                break
            g = g_cost[n]
            for k, (sdx, sdy, cost) in enumerate(self.PF_DIRS):
                mx, my = nx + sdx, ny + sdy
                if mx < 0 or my < 0 or mx >= w or my >= h:
                    continue
                m = my * w + mx
                if grid[m] != 1 or m in done:
                    continue
                if k >= 4 and (grid[ny * w + mx] == 0 or grid[my * w + nx] == 0):
                    continue
                ng = g + cost
                old = g_cost.get(m)
                if old is None or ng < old:
                    g_cost[m] = ng
                    parent[m] = n
                    hm2 = max(0, octile(mx, my) - range_cost)
                    counter += 1
                    heapq.heappush(heap, (ng + hm2 * 1.2, counter, m))
        if found < 0:
            e.path_time = self.loop_start + 2000
            if best_node == start:
                return False
            found = best_node
        cells = []
        n = found
        while n >= 0 and len(cells) < 19000:
            cells.append(n)
            n = parent.get(n, -1)
        # cells[0] = goal ... cells[-1] = start. Keep only the cells where the direction changes
        corners = []
        total = len(cells)
        for i in range(total - 2, -1, -1):
            keep = True
            if i > 0 and cells[i] - cells[i + 1] == cells[i - 1] - cells[i]:
                keep = False
            if keep:
                corners.append(((cells[i] % w) * cell + half + ox, int(cells[i] / w) * cell + half + oy))
        path = []
        ax, ay = sx, sy
        j = 0
        while j < len(corners):
            k = j
            while k < len(corners) - 1:
                if not self.grid_line_walkable(ax, ay, corners[k + 1][0], corners[k + 1][1]):
                    break
                k += 1
            path.append((corners[k][0], corners[k][1] - feet_offset))
            ax, ay = corners[k]
            j = k + 1
        e.path = path
        return True

    def path_steer(self, e, target_x, target_y):
        """Sets pf_steer to e's next waypoint (dropping those it has reached) or the target."""
        self.pf_steer_x, self.pf_steer_y = target_x, target_y
        if not e.path:
            return False
        cx, cy = e.cx, e.cy
        dropped = False
        while e.path:
            wx, wy = e.path[0]
            reached = abs(cx - wx) < 3 and abs(cy - wy) < 3
            if e.path_stuck > 8 and abs(cx - wx) < 12 and abs(cy - wy) < 12:
                reached = True
            if not reached:
                self.pf_steer_x, self.pf_steer_y = wx, wy
                break
            e.path.pop(0)
            e.path_best = None
            e.path_stuck = 0
            dropped = True
        return dropped

    def path_progress(self, e):
        d = distance(e.cx, e.cy, self.pf_steer_x, self.pf_steer_y)
        if e.path_best is None:
            e.path_best = d
            e.path_stuck = 0
        elif d < e.path_best - 0.25:
            e.path_best = d
            e.path_stuck = 0
        else:
            e.path_stuck += 1

    def forget_path(self, e):
        e.path = []
        e.path_goal = ""
        e.path_stuck = 0
        e.path_best = None

    def grid_region_at(self, x, y):
        if self.grid_w == 0:
            return 0
        gx = int((x - self.grid_ox) / self.grid_cell)
        gy = int((y - self.grid_oy) / self.grid_cell)
        if x - self.grid_ox < 0 or y - self.grid_oy < 0 or gx >= self.grid_w or gy >= self.grid_h:
            return 0
        return self.grid_region[gy * self.grid_w + gx]

    def label_grid_regions(self):
        """grid_region[cell] = which connected walkable area a cell belongs to (0 = blocked)."""
        self.grid_regions_dirty = False
        if self.grid_w == 0:
            return
        w = self.grid_w
        total = w * self.grid_h
        region = [0] * total
        grid = self.walk_grid
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
        self.grid_region = region

    # =================================================================================================================
    # Camera
    # =================================================================================================================
    def apply_zoom(self):
        """The world is drawn at 1:1 on a canvas of world_w x world_h (the playfield divided by the zoom), then
        scaled to the playfield."""
        self.world_w = int(self.view_w / self.zoom)
        self.world_h = int(self.view_h / self.zoom)
        self.world_surf = pygame.Surface((self.world_w, self.world_h)).convert()
        self.night_layer = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        self.fog_overlay_key = None
        self.cam_snap = True
        r = int(self.night_light)
        self.light_mask = None
        if r > 0:
            import numpy as np
            size = 2 * r
            ys, xs = np.mgrid[0:size, 0:size]
            d = np.sqrt((xs - r + 0.5) ** 2 + (ys - r + 0.5) ** 2) / r
            # 0 = no night in the middle, 1 = full night at the edge (a smooth fall-off)
            k = np.clip((d - 0.35) / 0.65, 0, 1)
            k = k * k * (3 - 2 * k)
            mask = pygame.Surface((size, size), pygame.SRCALPHA)
            mask.fill((255, 255, 255, 255))
            alpha = pygame.surfarray.pixels_alpha(mask)
            alpha[:, :] = (k.T * 255).astype(np.uint8)
            del alpha
            self.light_mask = mask

    def change_zoom(self, step):
        levels = self.zoom_levels
        i = levels.index(self.zoom) if self.zoom in levels else 1
        i = min(len(levels) - 1, max(0, i + step))
        if levels[i] == self.zoom:
            return
        self.zoom = levels[i]
        self.apply_zoom()
        ini.write("Interface", "Zoom", lbstr(self.zoom), self.config_path)
        self.display_message("Zoom %d%%" % int(self.zoom * 100), "INFO")

    def screen_to_world(self, sx, sy):
        """The world pixel under screen pixel sx,sy of the playfield."""
        return self.cam_x + sx / self.zoom, self.cam_y + sy / self.zoom

    def camera_update(self):
        """Centres the view on the player, as far as the maps that exist go (a view wider or taller than the maps
        there are is centred on them). The camera eases towards where it should be (Config [Interface]
        Camera.Smooth: how quickly, 0 = it sticks to the player) and jumps there after a teleport."""
        mw, mh = self.sw, self.sh
        ww, wh = self.world_w, self.world_h
        left = -mw if self.slot_map[4] else 0
        right = 2 * mw if self.slot_map[6] else mw
        top = -mh if self.slot_map[2] else 0
        bottom = 2 * mh if self.slot_map[8] else mh
        want_x = self.player.cx - ww / 2
        want_y = self.player.cy - wh / 2
        if right - left >= ww:
            want_x = min(max(want_x, left), right - ww)
        else:
            want_x = (left + right - ww) / 2
        if bottom - top >= wh:
            want_y = min(max(want_y, top), bottom - wh)
        else:
            want_y = (top + bottom - wh) / 2
        if self.cam_snap or self.camera_smooth <= 0:
            self.cam_fx, self.cam_fy = want_x, want_y
            self.cam_snap = False
        else:
            k = 1 - math.exp(-self.camera_smooth * self.loop_delta)
            self.cam_fx += (want_x - self.cam_fx) * k
            self.cam_fy += (want_y - self.cam_fy) * k
            if abs(want_x - self.cam_fx) < 0.3:
                self.cam_fx = want_x
            if abs(want_y - self.cam_fy) < 0.3:
                self.cam_fy = want_y
        self.cam_x = int(round(self.cam_fx))
        self.cam_y = int(round(self.cam_fy))
        self.cursor_world_x, self.cursor_world_y = self.screen_to_world(self.cursor_x, self.cursor_y)
        self.cursor_world_x = self.cursor_x + self.cam_x
        self.cursor_world_y = self.cursor_y + self.cam_y

    # =================================================================================================================
    # Minimap: Sprites\Interface\Minimap<Z>.png, positioned with Config [Minimap] Pixel.Size and Origin.<Z>
    # =================================================================================================================
    def build_minimap(self):
        z = self.map_z()
        key = "%s|%d" % (lbstr(z), len(self.explored_maps))
        if key == self.minimap_built_key and self.minimap_available:
            self.minimap_last = ""
            return
        self.minimap_built_key = key
        bmp = "Minimap" + lbstr(z)
        if not self.assets.loaded(bmp):
            self.log_missing("Minimap", bmp)
            self.minimap_available = False
            return
        config = self.config_path
        self.minimap_pixel_size = val(ini.read("Minimap", "Pixel.Size", "0", config))
        origin = ini.read("Minimap", "Origin." + lbstr(z), "", config)
        lowest_x = lowest_y = 9999
        highest_x = -9999
        maps = []
        try:
            files = os.listdir(os.path.join(self.root, "Maps"))
        except OSError:
            files = []
        for f in files:
            if not f.lower().endswith(".txt"):
                continue
            m = f[:-4]
            if word(m, 3, ",") != "" and val(word(m, 3, ",")) == z:
                maps.append(m)
                lowest_x = min(lowest_x, val(word(m, 1, ",")))
                lowest_y = min(lowest_y, val(word(m, 2, ",")))
                highest_x = max(highest_x, val(word(m, 1, ",")))
        if origin:
            self.minimap_origin_x = val(word(origin, 1, ","))
            self.minimap_origin_y = val(word(origin, 2, ","))
        else:
            if lowest_x == 9999:
                lowest_x, lowest_y, highest_x = self.map_x(), self.map_y(), self.map_x()
            self.minimap_origin_x, self.minimap_origin_y = lowest_x, lowest_y
        sp = self.assets.get(bmp)
        width, height = sp.w, sp.h
        if self.minimap_pixel_size <= 0:
            self.minimap_pixel_size = max(1, int(width / max(1, (highest_x - self.minimap_origin_x + 1) * self.xt)))
        if self.minimap_zoom <= 0:
            self.minimap_zoom = max(1, 4 / self.minimap_pixel_size)
        image = sp.image
        if self.minimap_blackout:
            image = image.copy()
            map_w = self.xt * self.minimap_pixel_size
            map_h = self.yt * self.minimap_pixel_size
            for m in maps:
                if m not in self.explored_maps:
                    cx = (val(word(m, 1, ",")) - self.minimap_origin_x) * map_w
                    cy = (val(word(m, 2, ",")) - self.minimap_origin_y) * map_h
                    if 0 <= cx < width and 0 <= cy < height:
                        image.fill((18, 18, 28), (cx, cy, map_w, map_h))
        self.minimap_image = image
        self.minimap_available = True
        self.minimap_last = ""

    def update_minimap(self):
        if not self.minimap_available:
            return
        ps = self.minimap_pixel_size * self.minimap_zoom
        mx = self.minimap_centre_x - ((self.player.cx / self.tw) * ps) - ((self.map_x() - self.minimap_origin_x) * self.xt * ps)
        my = self.minimap_centre_y - ((self.player.cy / self.th) * ps) - ((self.map_y() - self.minimap_origin_y) * self.yt * ps)
        key = "%d %d %d %s" % (int(mx), int(my), id(self.minimap_image), lbstr(ps))
        if key == self.minimap_last:
            return
        self.minimap_last = key
        self.minimap_paint(int(mx), int(my))

    def minimap_paint(self, mx, my):
        """Paints the part of the zoomed minimap (its top-left at screen mx,my) that shows through the circle."""
        size = self.minimap_view_size
        vx = self.minimap_centre_x - size / 2
        vy = self.minimap_centre_y - size / 2
        zoom = self.minimap_zoom
        image = self.minimap_image
        w, h = image.get_size()
        view = self.minimap_view
        view.fill((0, 0, 0))
        sx1 = max(0, int((vx - mx) / zoom))
        sy1 = max(0, int((vy - my) / zoom))
        sx2 = min(w, int((vx + size - mx) / zoom) + 1)
        sy2 = min(h, int((vy + size - my) / zoom) + 1)
        if sx2 > sx1 and sy2 > sy1:
            dx = int(mx + sx1 * zoom - vx)
            dy = int(my + sy1 * zoom - vy)
            dw = int((sx2 - sx1) * zoom)
            dh = int((sy2 - sy1) * zoom)
            if dw > 0 and dh > 0:
                part = image.subsurface((sx1, sy1, sx2 - sx1, sy2 - sy1))
                view.blit(pygame.transform.scale(part, (dw, dh)), (dx, dy))
        if self.quest_markers_enabled and self.qmarks:
            z = self.map_z()
            ps = self.minimap_pixel_size
            for m, qx, qy in self.qmarks:
                if word(m, 3, ",") != "" and val(word(m, 3, ",")) == z:
                    u = ((val(word(m, 1, ",")) - self.minimap_origin_x) * self.xt + qx - 0.5) * ps
                    v = ((val(word(m, 2, ",")) - self.minimap_origin_y) * self.yt + qy - 0.5) * ps
                    px = int(mx + u * zoom - vx)
                    py = int(my + v * zoom - vy)
                    if 5 <= px <= size - 6 and 5 <= py <= size - 6:
                        self.mark_cross(view, (0, 0, 0), px, py, 5, 2)
                        self.mark_cross(view, (255, 220, 40), px, py, 4, 1)
        self.minimap_view_pos = (int(vx), int(vy))

    @staticmethod
    def mark_cross(surf, col, px, py, arm, half):
        surf.fill(col, (px - arm, py - half, 2 * arm + 1, 2 * half + 1))
        surf.fill(col, (px - half, py - arm, 2 * half + 1, 2 * arm + 1))

    def change_minimap_zoom(self, factor):
        if not self.minimap_available:
            return
        new_size = self.minimap_pixel_size * self.minimap_zoom * factor
        if new_size < 1 or new_size > 32:
            return
        self.minimap_zoom *= factor
        self.minimap_last = ""

    # =================================================================================================================
    # Day and night: outdoors (level 0) the ground darkens at night
    # =================================================================================================================
    def day_night_update(self):
        """The time of day's messages and who's out (daynight.py; the sky itself is drawn every frame)."""
        self.sky_update()

    def apply_queue_tiles(self):
        for entry in self.action_queue:
            if field(entry, 5, "\t") == self.screen_name and field(entry, 1, "\t").upper() == "CHANGE.TILE":
                misc = field(entry, 4, "\t")
                coords = field(entry, 6, "\t")
                if misc not in ("-", ""):
                    self.change_tile(val(word(coords, 1, ",")), val(word(coords, 2, ",")), misc, keep_decor=False)

    def change_window_tile(self, wx, wy, tile):
        """A tile of one of the maps around the current one changes (its regrowing tree, ...): a cell spec, as a
        script's Change.Tile."""
        if self.w_find(wx, wy) is None or tile == "":
            return
        self.w_change_cell(wx, wy, tile, keep_decor=False)
        for y in range(wy - 1, wy + 2):
            for x in range(wx - 1, wx + 2):
                self.paint_window_cell(x, y)
        self.ground_refresh((wx - 2) * self.tw, (wy - 2) * self.th, (wx + 1) * self.tw, (wy + 1) * self.th)
        self.update_walk_grid_wtile(wx, wy)
