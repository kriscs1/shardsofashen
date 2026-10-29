"""Tiles that move, all set in data\\Tiles.ini (nothing here knows a tile by its name):
  * Sway=<pixels>   a plant in the wind (grass, flowers, reeds, bushes): its top sways that far. A decor plant's
                    pixels are its see-through sprite's; a ground tile's are the ones that aren't its ground
                    (Sway.Ground=<tile>, else its Blend.Texture).
  * Flame=1         the bright fire-coloured pixels flicker (torches, fireplaces, lanterns, lamp posts).
  * Water=1         water: foam laps along wherever land meets it (land next to it, a rock in it, sand blended over it).
  * Anim.Frames=N   drawn from its own pictures <Name>1..<Name>N in sprites\\Tiles in turn, Anim.Speed ms each
                    (default 200), each cell a little out of step with the next (a mill wheel, a bubbling pot).
How many frames sway, flicker and the foam have, how fast, and the foam's colour: data\\Config.ini [Animation].
Drawn here as the ground is painted (world.paint_window_cell); anim_tick repaints the animated cells in view when their
frame changes. Decor (a see-through tile over the ground: Layer=Decor) moves the same way over whatever it is on."""
import math
import random

import pygame

from . import ini

# Config.ini [Animation] keys and their defaults
ANIM_DEFAULTS = {"Water.Frames": 6, "Water.Speed": 260, "Flame.Frames": 4, "Flame.Speed": 140, "Sway.Frames": 6,
                 "Sway.Speed": 230, "Foam.Colour": "234 244 250"}


class AnimMixin:
    def anim_setting(self, key):
        """Config.ini [Animation] key (ANIM_DEFAULTS has the defaults): a whole number, or a colour (r, g, b)."""
        cache = self.__dict__.setdefault("anim_settings", {})
        if key not in cache:
            default = ANIM_DEFAULTS[key]
            v = ini.read("Animation", key, str(default), self.config_path).strip()
            if key.endswith("Colour"):
                try:
                    c = tuple(max(0, min(255, int(float(p)))) for p in v.replace(",", " ").split()[:3])
                except ValueError:
                    c = ()
                cache[key] = c if len(c) == 3 else tuple(int(p) for p in default.split())
            else:
                try:
                    cache[key] = max(1, int(float(v)))
                except ValueError:
                    cache[key] = default
        return cache[key]

    def tile_flag(self, name, key):
        """A Tiles.ini 0/1 key of tile name (Flame, Water)."""
        cache = self.__dict__.setdefault("tile_flags", {})
        if (name, key) not in cache:
            cache[(name, key)] = bool(name) and self.tile_ini(name, key, "0").strip() in ("1", "yes", "Yes", "true")
        return cache[(name, key)]

    def tile_frames(self, name):
        """(N, ms) of a tile drawn from its pictures <Name>1..N (Tiles.ini Anim.Frames, Anim.Speed), or None."""
        cache = self.__dict__.setdefault("tile_frame_info", {})
        if name not in cache:
            info = None
            try:
                n = int(float(self.tile_ini(name, "Anim.Frames", "0") or 0)) if name else 0
                ms = max(30, int(float(self.tile_ini(name, "Anim.Speed", "200") or 200)))
            except ValueError:
                n, ms = 0, 200
            if n > 1 and all(self.assets.loaded("%s%d" % (name, k)) or
                             self.assets.load_if_exists("Tiles", "%s%d" % (name, k)) for k in range(1, n + 1)):
                info = (n, ms)
            cache[name] = info
        return cache[name]

    def is_water_tile(self, tile):
        return self.tile_flag(tile, "Water")

    def anim_kind(self, tile):
        """How a cell's own tile moves (a decor tile used as one doesn't: it's see-through): "water", "frames:<ms>",
        "flame", "sway" or None."""
        cache = self.__dict__.setdefault("anim_kinds", {})
        if tile not in cache:
            kind = None
            if tile and not self.is_decor_tile(tile):
                frames = self.tile_frames(tile)
                if self.tile_flag(tile, "Water"):
                    kind = "water"
                elif frames:
                    kind = "frames:%d" % frames[1]
                elif self.tile_flag(tile, "Flame"):
                    kind = "flame"
                elif self.decor_sway(tile) > 0:
                    kind = "sway"
            cache[tile] = kind
        return cache[tile]

    def decor_sway(self, name):
        """How far (pixels) a plant tile's top sways: Tiles.ini Sway= (0 = it doesn't)."""
        cache = self.__dict__.setdefault("decor_sway_px", {})
        if name not in cache:
            try:
                cache[name] = max(0.0, float(self.tile_ini(name, "Sway", "0").strip() or 0)) if name else 0.0
            except ValueError:
                cache[name] = 0.0
        return cache[name]

    def decor_anim_kind(self, name):
        """How a decor moves: "frames:<ms>" (its own pictures), "sway" (a plant in the wind), "flame" (a torch) or
        None."""
        cache = self.__dict__.setdefault("decor_kinds", {})
        if name not in cache:
            frames = self.tile_frames(name)
            cache[name] = ("frames:%d" % frames[1] if frames else "sway" if self.decor_sway(name) > 0 else
                           "flame" if self.tile_flag(name, "Flame") else None)
        return cache[name]

    def anim_frame(self, kind, wx=0):
        now = self.loop_start if getattr(self, "loop_start", None) is not None else 0
        if kind == "water":
            return int(now // self.anim_setting("Water.Speed")) % self.anim_setting("Water.Frames")
        if kind == "sway":                          # (a gust rolls east across the map: later the further east)
            return int(now // self.anim_setting("Sway.Speed") - (wx + self.w_origin_tx) // 2) % \
                self.anim_setting("Sway.Frames")
        return int(now // self.anim_setting("Flame.Speed")) % self.anim_setting("Flame.Frames")

    def kind_counter(self, kind):
        """A number that changes whenever cells of this kind (anim_cells) show a new frame."""
        now = self.loop_start if getattr(self, "loop_start", None) is not None else 0
        if ":" in kind:                                 # frames:<ms>, decor_frames:<ms>
            return int(now // int(kind.split(":")[1]))
        if kind in ("sway", "sway_full", "decor_sway"):
            return int(now // self.anim_setting("Sway.Speed"))
        if kind == "water":
            return self.anim_frame("water")
        return self.anim_frame("flame")                 # (flame, decor_flame)

    def tile_has_land(self, tile):
        """Does water tile's own picture have land in it (a shore piece, a rock), so foam laps round it?"""
        cache = self.__dict__.setdefault("tile_land", {})
        if tile not in cache:
            import numpy as np
            sp = self.ground_bmp(tile)
            if sp is None:
                cache[tile] = False
            else:
                rgb = pygame.surfarray.array3d(sp.image).astype(int)
                r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
                cache[tile] = bool((~((b > r + 20) & (b >= g - 10))).any())
        return cache[tile]

    def frames_image(self, name, wx, wy):
        """The picture a frame-animated tile (tile_frames) shows now at window tile wx,wy (each cell a little out of
        step with its neighbours), or None."""
        info = self.tile_frames(name)
        if not info:
            return None
        n, ms = info
        now = self.loop_start if getattr(self, "loop_start", None) is not None else 0
        k = (int(now // ms) + (wx + self.w_origin_tx) * 3 + (wy + self.w_origin_ty) * 5) % n + 1
        return self.assets.get("%s%d" % (name, k))

    # ----- plants in the wind
    def sway_frames(self, tile):
        """The tile's plant (the pixels that aren't its ground: Sway.Ground, else its Blend.Texture) bent over by the
        wind, its top furthest, its roots still: Sway.Frames pictures."""
        import numpy as np
        cache = self.__dict__.setdefault("sway_cache", {})
        if tile in cache:
            return cache[tile]
        sp = self.ground_bmp(tile)
        ground = self.tile_ini(tile, "Sway.Ground", "").strip() or self.tile_ini(tile, "Blend.Texture", "").strip()
        gs = self.ground_bmp(ground) if ground and ground != tile and self.assets.loaded(ground) else None
        if sp is None or gs is None or gs.image.get_size() != sp.image.get_size():
            cache[tile] = None
            return None
        img = pygame.surfarray.array3d(sp.image).astype(int)
        base = pygame.surfarray.array3d(gs.image).astype(int)
        plant = np.abs(img - base).sum(2) > 45
        if plant.mean() > 0.6:
            cache[tile] = None
            return None
        w, h = plant.shape                          # (surfarray: x first)
        frames = []
        count = self.anim_setting("Sway.Frames")
        for k in range(count):
            lean = self.decor_sway(tile) * math.sin(2 * math.pi * k / count)
            out = base.copy()
            for y in range(h - 1, -1, -1):          # the roots first, then up the stalks
                dx = int(round(lean * ((h - 1 - y) / float(h - 1)) ** 1.3))
                xs = np.nonzero(plant[:, y])[0]
                if xs.size == 0:
                    continue
                nx = np.clip(xs + dx, 0, w - 1)
                out[nx, y] = img[xs, y]
            surf = pygame.Surface((w, h)).convert() if pygame.display.get_surface() else pygame.Surface((w, h))
            pygame.surfarray.blit_array(surf, out.astype(np.uint8))
            frames.append(surf)
        cache[tile] = frames
        return frames

    def anim_base(self, tile, wx, wy, dx, dy):
        """Called by paint_window_cell instead of drawing a moving tile as it is: the plant as the wind has it now, or
        its picture of the moment (Anim.Frames). True if it drew it."""
        kind = self.anim_kind(tile)
        if kind and kind.startswith("frames:"):
            sp = self.frames_image(tile, wx, wy)
            if sp is None:
                return False
            self.clean.blit(sp.image, (dx, dy))
            return True
        if kind != "sway":
            return False
        frames = self.sway_frames(tile)
        if not frames:
            return False
        self.clean.blit(frames[self.anim_frame("sway", wx)], (dx, dy))
        return True

    # ----- decor (world.paint_window_cell): drawn over the ground, bent by the wind or flickering
    def decor_sway_frames(self, name):
        """A see-through plant bent over by the wind, its top furthest and its roots still: Sway.Frames pictures with
        their transparency. Its pixels are the ones that aren't see-through, so it works on any ground."""
        import numpy as np
        cache = self.__dict__.setdefault("decor_sway_cache", {})
        if name in cache:
            return cache[name]
        sp = self.ground_bmp(name)
        lean_max = self.decor_sway(name)
        if sp is None or lean_max <= 0:
            cache[name] = None
            return None
        src = sp.masked
        rgb = pygame.surfarray.array3d(src)
        alpha = pygame.surfarray.array_alpha(src)
        w, h = alpha.shape                          # (surfarray: x first)
        frames = []
        count = self.anim_setting("Sway.Frames")
        for k in range(count):
            lean = lean_max * math.sin(2 * math.pi * k / count)
            out_rgb = np.zeros_like(rgb)
            out_a = np.zeros_like(alpha)
            for y in range(h - 1, -1, -1):          # the roots first, then up the stalks
                dx = int(round(lean * ((h - 1 - y) / float(max(1, h - 1))) ** 1.3))
                xs = np.nonzero(alpha[:, y])[0]
                if xs.size == 0:
                    continue
                nx = np.clip(xs + dx, 0, w - 1)
                out_rgb[nx, y] = rgb[xs, y]
                out_a[nx, y] = alpha[xs, y]
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            if pygame.display.get_surface():
                surf = surf.convert_alpha()
            pygame.surfarray.blit_array(surf, out_rgb)
            a = pygame.surfarray.pixels_alpha(surf)
            a[:, :] = out_a
            del a
            frames.append(surf)
        cache[name] = frames
        return frames

    def paint_decor(self, name, wx, wy, dx, dy, covered=False):
        """Decor name over the ground already painted at dx,dy (window tile wx,wy), as the wind or the flame has it
        now. A moving one in the open keeps the ground under it (decor_under), so its next frame is two blits."""
        kind = self.decor_anim_kind(name)
        under = self.__dict__.setdefault("decor_under", {})
        if kind and not covered:
            under[(wx, wy)] = (self.anim_cell_key(), self.clean.subsurface((dx, dy, self.tw, self.th)).copy())
        else:
            under.pop((wx, wy), None)
        img = None
        if kind and kind.startswith("frames:"):
            sp = self.frames_image(name, wx, wy)
            img = sp.masked if sp else None
        elif kind == "sway":
            frames = self.decor_sway_frames(name)
            if frames:
                img = frames[self.anim_frame("sway", wx)]
        elif kind == "flame":
            img = self.flame_frame(name, self.anim_frame("flame"), see_through=True)
        if img is None:
            sp = self.ground_bmp(name)
            img = sp.masked if sp else None
        if img is not None:
            self.clean.blit(img, (dx, dy))

    # ----- foam
    def foam_sides(self, wx, wy):
        """Which sides of water cell wx,wy have land next to them: N, E, S, W."""
        out = ""
        for side, dx, dy in (("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0)):
            f = self.w_find(wx + dx, wy + dy)
            if f is None:
                continue
            st, c = f
            t = st.tile[c]
            if t and not self.is_water_tile(t):
                out += side
        return out

    def foam_distance(self, painted, sides):
        """How far (0-5) each pixel of a cell is from land: land in the cell as painted (a shore piece, a rock, the
        sand or grass blended over its edge) and along the sides that have land beyond them. None if no land."""
        import numpy as np
        tw, th = self.tw, self.th
        land = np.zeros((th + 8, tw + 8), dtype=bool)
        rgb = pygame.surfarray.array3d(painted).astype(int).transpose(1, 0, 2)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        land[4:4 + th, 4:4 + tw] = ~((b > r + 20) & (b >= g - 10))
        if "N" in sides:
            land[:4, :] = True
        if "S" in sides:
            land[th + 4:, :] = True
        if "W" in sides:
            land[:, :4] = True
        if "E" in sides:
            land[:, tw + 4:] = True
        if not land.any():
            return None
        dist = np.full(land.shape, 9, dtype=np.int8)
        cur = land.copy()
        dist[cur] = 0
        for d in range(1, 6):                       # grow the land a pixel at a time (8-way)
            grown = cur.copy()
            grown[1:, :] |= cur[:-1, :]
            grown[:-1, :] |= cur[1:, :]
            grown[:, 1:] |= cur[:, :-1]
            grown[:, :-1] |= cur[:, 1:]
            grown[1:, 1:] |= cur[:-1, :-1]
            grown[:-1, :-1] |= cur[1:, 1:]
            grown[1:, :-1] |= cur[:-1, 1:]
            grown[:-1, 1:] |= cur[1:, :-1]
            dist[grown & ~cur] = d
            cur = grown
        return dist[4:4 + th, 4:4 + tw]

    def anim_cell_key(self):
        return self.ground_window, getattr(self, "anim_gen", 0)

    def foam_frame(self, cell, k):
        entry = self.foam_cells.get(cell)
        if entry is None or entry[2] is None:
            return None
        if k not in entry[3]:
            entry[3][k] = self.foam_overlay(entry[2], k)
        return entry[3][k]

    def foam_overlay(self, dist, k):
        """The foam on a water cell for frame k: white along the land, in waves that run along the shore (the same
        pattern every 16 pixels, so it carries on from one cell to the next), the line of it creeping in and out."""
        import numpy as np
        th, tw = dist.shape
        ys, xs = np.mgrid[0:th, 0:tw]
        phase = k * 2 * math.pi / self.anim_setting("Water.Frames")
        wave = 0.5 + 0.5 * np.sin(2 * math.pi * (xs + ys) / 16.0 + phase)
        swell = 1 if math.sin(phase) > 0.3 else 0          # the waterline creeps in a pixel, then back
        d = dist - swell
        alpha = np.zeros(dist.shape, dtype=float)
        alpha[(d >= 0) & (d <= 1) & (dist > 0)] = 140
        alpha[d == 2] = 70
        alpha[d == 3] = 30
        alpha *= 0.55 + 0.45 * wave
        alpha[(d == 3) & (wave > 0.85)] = 120                # a crest further out now and then
        alpha[dist == 0] = 0
        surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        surf.fill(self.anim_setting("Foam.Colour") + (0,))
        a = pygame.surfarray.pixels_alpha(surf)
        a[:, :] = np.clip(alpha, 0, 255).astype(np.uint8).T
        del a
        return surf

    # ----- flames
    def flame_frame(self, tile, k, see_through=False):
        """The tile with its fire-coloured pixels brighter or dimmer (frame k), and the tips of the flames higher
        or lower. see_through: with its transparency (a torch on the decor layer)."""
        import numpy as np
        cache = self.__dict__.setdefault("flame_cache", {})
        key = (tile, k, see_through)
        if key in cache:
            return cache[key]
        sp = self.ground_bmp(tile)
        if sp is None:
            cache[key] = None
            return None
        img = sp.masked.copy() if see_through else sp.image.copy()
        rgb = pygame.surfarray.pixels3d(img)
        r, g, b = (rgb[..., i].astype(int) for i in range(3))
        flame = (r > 215) & (g > 110) & (b < 150) & (r > b + 80) & (r + g > 370)   # (bright fire, not red brick)
        if see_through:                                     # (the flame itself, not the see-through glow round it)
            flame &= pygame.surfarray.array_alpha(img) == 255
        if not flame.any():
            del rgb
            cache[key] = None
            return None
        rng = random.Random(hash(tile) % 1000 + k * 7919)
        w, h = flame.shape
        noise = np.array([[rng.uniform(0.72, 1.22) for _ in range(h)] for _ in range(w)])
        k2 = 0.88 + 0.16 * math.sin(k * 2 * math.pi / self.anim_setting("Flame.Frames"))
        for i in range(3):
            ch = rgb[..., i].astype(float)
            ch[flame] = np.clip(ch[flame] * noise[flame] * k2 + (18 if i == 0 else 0), 0, 255)
            rgb[..., i] = ch.astype(np.uint8)
        if k % 2:                                           # the tips: a pixel above each flame column, lit
            tips = flame & ~np.roll(flame, 1, axis=1)
            tips[:, 0] = False
            up = np.roll(tips, -1, axis=1) & ~flame
            rgb[up] = (255, 200, 90)
        del rgb
        if see_through and k % 2 and up.any():
            a = pygame.surfarray.pixels_alpha(img)
            a[up] = 255
            del a
        cache[key] = img
        return img

    # ----- painting and the tick
    def anim_paint(self, tile, wx, wy, dx, dy):
        """Called by paint_window_cell once the tile is down: foam over water by land, a flickering flame."""
        kind = self.anim_kind(tile)
        if kind == "water":
            sides = self.foam_sides(wx, wy)
            f = self.w_find(wx, wy)
            if sides or self.tile_has_land(tile) or (f and f[0].decor[f[1]]):
                painted = self.clean.subsurface((dx, dy, self.tw, self.th)).copy()
                dist = self.foam_distance(painted, sides)
                # kept: the cell without its foam and how far each pixel is from land, so the next frames are a
                # copy and a blit (anim_tick), not the whole cell painted again
                self.__dict__.setdefault("foam_cells", {})[(wx, wy)] = (self.anim_cell_key(), painted, dist, {})
                surf = self.foam_frame((wx, wy), self.anim_frame("water"))
                if surf is not None:
                    self.clean.blit(surf, (dx, dy))
        elif kind == "flame":
            img = self.flame_frame(tile, self.anim_frame("flame"))
            if img is not None:
                self.clean.blit(img, (dx, dy))

    def anim_cells(self):
        """The animated cells in view (window tiles), found again when the view moves to other tiles or the maps
        change."""
        xt, yt = self.xt, self.yt
        x0 = int(self.cam_x // self.tw) + xt
        y0 = int(self.cam_y // self.th) + yt
        cols = int(self.world_w // self.tw) + 3
        rows = int(self.world_h // self.th) + 3
        key = (x0, y0, cols, rows, self.ground_window, getattr(self, "anim_gen", 0))
        if getattr(self, "anim_key", None) == key:
            return self.anim_list
        cells = []
        for wy in range(y0, y0 + rows + 1):
            for wx in range(x0, x0 + cols + 1):
                f = self.w_find(wx, wy)
                if f is None:
                    continue
                st, c = f
                t = st.tile[c]
                d = st.decor[c]
                kind = self.anim_kind(t) if t else None
                if kind == "water" and not d and not self.tile_has_land(t) and not self.foam_sides(wx, wy):
                    continue                        # (open water: no foam to move)
                if kind == "sway" and (st.roof[c] or st.infront[c] or d or
                                       self.blended_over(wx, wy, st.blend[c])):
                    kind = "sway_full"              # (something over it: painted whole each frame)
                if kind is None and d and self.decor_anim_kind(d):
                    kind = "decor_" + self.decor_anim_kind(d)       # a plant, a torch, a wheel on still ground
                if kind:
                    cells.append((wx, wy, kind))
        self.anim_key, self.anim_list = key, cells
        return cells

    def blended_over(self, wx, wy, b):
        """Does a neighbour with a higher Blend paint its edge over this cell?"""
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dx or dy) and self.blend_level_at(wx + dx, wy + dy)[0] > b:
                    return True
        return False

    def anim_tick(self):
        if not getattr(self, "ground_ready", False) or getattr(self, "ground_hold", False):
            return
        frames = {k: self.kind_counter(k) for k in {kind for _, _, kind in self.anim_cells()}}
        last = self.__dict__.setdefault("anim_last", {})
        changed = {k for k, v in frames.items() if last.get(k) != v}
        if not changed:
            return
        last.update(frames)
        cells = self.__dict__.setdefault("foam_cells", {})
        unders = self.__dict__.setdefault("decor_under", {})
        key = self.anim_cell_key()
        if getattr(self, "foam_cells_key", None) != key:            # (the maps moved or a tile changed)
            cells.clear()
            unders.clear()
            self.foam_cells_key = key
        for wx, wy, kind in self.anim_cells():
            if kind not in changed:
                continue
            if kind.startswith("decor_"):           # decor that moves: the ground under it, its new picture
                under = unders.get((wx, wy))
                f = self.w_find(wx, wy)
                if under is not None and under[0] == key and f:
                    dx, dy = (wx - 1) * self.tw, (wy - 1) * self.th
                    self.clean.blit(under[1], (dx, dy))
                    self.paint_decor(f[0].decor[f[1]], wx, wy, dx, dy)
                else:
                    self.paint_window_cell(wx, wy)
                continue
            if kind == "sway":                      # a plant in the open: just its new picture
                f = self.w_find(wx, wy)
                fr = self.sway_frames(f[0].tile[f[1]]) if f else None
                if fr:
                    self.clean.blit(fr[self.anim_frame("sway", wx)], ((wx - 1) * self.tw, (wy - 1) * self.th))
                continue
            entry = cells.get((wx, wy)) if kind == "water" else None
            if entry is not None and entry[0] == key:              # the shore: the cell as it was, its new foam
                dx, dy = (wx - 1) * self.tw, (wy - 1) * self.th
                self.clean.blit(entry[1], (dx, dy))
                surf = self.foam_frame((wx, wy), frames["water"])
                if surf is not None:
                    self.clean.blit(surf, (dx, dy))
            else:
                self.paint_window_cell(wx, wy)
