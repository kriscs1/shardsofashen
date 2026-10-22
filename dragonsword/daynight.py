"""The day going round: the sky's colour (pink dawn, the warm light of evening, deep blue night), lamps, fires and
windows lighting the dark, the sun or the moon by the minimap, and who's out: townsfolk go home through their door
at night and come out again in the morning (Entities.ini Schedule=Day), and some creatures only come out after dark
(Schedule=Night, on the surface).

The time of day is a fraction of a day (0 = midnight, 0.5 = noon); a day lasts Config [Gameplay] Day.Minutes (24).
It's kept in the save ([Player] Time). The sky's colours, when night falls, what the times are called, the glow round
lights and sleeping are Data\\DayNight.ini's; townsfolk go home by the nearest Tiles.ini Door=1 tile."""
import math
import os

import pygame

from . import ini
from .entity import NPC
from .lb import trim, distance, val


def numbers(text):
    """"8 12 42 168" -> (8, 12, 42, 168)."""
    out = []
    for p in text.replace(",", " ").split():
        try:
            out.append(int(float(p)))
        except ValueError:
            pass
    return tuple(out)


class DayNightMixin:
    # ----- DayNight.ini
    def dn_path(self):
        return os.path.join(self.root, "Data", "DayNight.ini")

    def dn(self, section, key, default=""):
        """Data\\DayNight.ini [section] key."""
        return ini.read(section, key, str(default), self.dn_path())

    def dn_table(self, section):
        """[(time, value)] of a DayNight.ini section of <time>=<value> lines, in time order."""
        out = []
        for k, v in ini.section(section, self.dn_path()):
            try:
                out.append((float(k), v))
            except ValueError:
                pass
        return sorted(out)

    @property
    def night_from(self):
        return val(self.dn("Night", "From", "0.83"))

    @property
    def night_to(self):
        return val(self.dn("Night", "To", "0.21"))

    # ----- the time
    def day_fraction(self):
        t0 = getattr(self, "day_time0", 0.3)
        if self.day_seconds <= 0:
            return t0
        return (t0 + (self.clock() - self.day_start_ms) / 1000.0 / self.day_seconds) % 1.0

    def set_day_fraction(self, t):
        self.day_time0 = t % 1.0
        self.day_start_ms = self.clock()

    def is_night(self, t=None):
        t = self.day_fraction() if t is None else t
        return t >= self.night_from or t < self.night_to

    def time_text(self):
        t = self.day_fraction()
        name = next((n for limit, n in self.dn_table("Periods") if t < limit), "Day")
        h = int(t * 24)
        hour = "%d %s" % (12 if h % 12 == 0 else h % 12, "am" if h < 12 else "pm")
        return "%s, about %s" % (name, hour)

    def sky(self, t):
        """(r, g, b, strength) laid over the world at time t: DayNight.ini [Sky], eased between its times."""
        table = [(t0, numbers(v)) for t0, v in self.dn_table("Sky")]
        table = [(t0, c) for t0, c in table if len(c) == 4]
        if not table:
            return (0, 0, 0, 0)
        for (t0, a), (t1, b) in zip(table, table[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / max(1e-6, t1 - t0)
                k = k * k * (3 - 2 * k)
                return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(4))
        return table[0][1]

    def sky_update(self):
        """About once a second: the dark coming or going (messages), and who's out."""
        night = self.day_night_enabled and self.map_z() == 0 and self.is_night()
        was = getattr(self, "night_now", None)
        if was is not None and night != was and self.map_z() == 0 and self.day_night_enabled:
            words = self.dn("Night", "Falls" if night else "Ends", "")
            if words:
                self.display_message(words, "INFO")
        self.night_now = night
        self.night_alpha = self.sky(self.day_fraction())[3] if self.day_night_enabled and self.map_z() == 0 else 0
        self.night_shown = self.night_alpha

    # ----- lights
    def light_spot(self, r):
        """A soft round hole in the dark, radius r (multiplied into the night's alpha)."""
        cache = self.__dict__.setdefault("light_spots", {})
        if r not in cache:
            import numpy as np
            size = 2 * r
            ys, xs = np.mgrid[0:size, 0:size]
            d = np.sqrt((xs - r + 0.5) ** 2 + (ys - r + 0.5) ** 2) / r
            k = np.clip((d - 0.15) / 0.85, 0, 1)
            k = k * k * (3 - 2 * k)
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            s.fill((255, 255, 255, 255))
            a = pygame.surfarray.pixels_alpha(s)
            a[:, :] = (k.T * 255).astype(np.uint8)
            del a
            cache[r] = s
        return cache[r]

    def warm_glow(self, r):
        """A warm orange glow, added to what's under it."""
        cache = self.__dict__.setdefault("warm_glows", {})
        if r not in cache:
            import numpy as np
            size = 2 * r
            ys, xs = np.mgrid[0:size, 0:size]
            d = np.clip(np.sqrt((xs - r + 0.5) ** 2 + (ys - r + 0.5) ** 2) / r, 0, 1)
            k = (1 - d) ** 2
            arr = np.zeros((size, size, 3), dtype=np.uint8)
            glow = numbers(self.dn("Night", "Glow.Colour", "70 38 8")) + (0, 0, 0)
            for i in range(3):
                arr[..., i] = (k * max(0, min(255, glow[i]))).astype(np.uint8)
            s = pygame.Surface((size, size))
            pygame.surfarray.blit_array(s, arr.transpose(1, 0, 2))
            cache[r] = s
        return cache[r]

    def sky_lights(self):
        """(x, y, radius, warm) of what lights the dark in view, in the current map's pixels: every tile, decor and
        roof with Tiles.ini Light= (torches, fireplaces, lanterns, lamp posts, lit windows) and every thing with
        Entities.ini Light= (fires, ranges)."""
        xt, yt = self.xt, self.yt
        x0 = int(self.cam_x // self.tw) + xt - 2
        y0 = int(self.cam_y // self.th) + yt - 2
        cols = int(self.world_w // self.tw) + 5
        rows = int(self.world_h // self.th) + 5
        key = (x0, y0, cols, rows, self.ground_window, getattr(self, "anim_gen", 0))
        if getattr(self, "sky_lights_key", None) != key:
            out = []
            for wy in range(y0, y0 + rows):
                for wx in range(x0, x0 + cols):
                    f = self.w_find(wx, wy)
                    if f is None:
                        continue
                    st, c = f
                    t, d, roof = st.tile[c], st.decor[c], st.roof[c]
                    cx, cy = (wx - xt - 0.5) * self.tw, (wy - yt - 0.5) * self.th
                    cell = (wx - xt, wy - yt)
                    # (under a roof: only seen while you're inside with the roof off; an upper window in the roof
                    # only while the roof shows)
                    r = max(self.tile_light(t), self.tile_light(d))
                    if r:
                        out.append((cx, cy, r, True, (cell, False) if roof else None))
                    if roof and self.tile_light(roof):
                        out.append((cx, cy, self.tile_light(roof), True, (cell, True)))
            self.sky_lights_key, self.sky_lights_list = key, out
        lights = list(self.sky_lights_list)
        for e in self.world:
            if e.alive and e.active:
                r = self.entity_light(e.name)
                if r:
                    lights.append((e.cx, e.cy, r, True, None))
        return lights

    def tile_light(self, name):
        """How far (pixels) a tile lights the dark round it at night: Tiles.ini Light= (0 = it doesn't)."""
        cache = self.__dict__.setdefault("tile_light_cache", {})
        if name not in cache:
            try:
                cache[name] = max(0, int(float(self.tile_ini(name, "Light", "0") or 0))) if name else 0
            except ValueError:
                cache[name] = 0
        return cache[name]

    def entity_light(self, name):
        """How far (pixels) a thing (a fire, a range, a glowing creature) lights the dark round it: Entities.ini
        Light= (a decor tile placed as an object: its Tiles.ini Light=)."""
        cache = self.__dict__.setdefault("entity_light_cache", {})
        if name not in cache:
            try:
                cache[name] = max(0, int(float(self.entity_ini(name, "Light", "0") or 0)))
            except ValueError:
                cache[name] = 0
        return cache[name]

    def draw_sky(self, scr, cam_x, cam_y):
        """The sky's colour over the world, with holes in the dark round the lights and a warm glow from them."""
        if not self.day_night_enabled or self.map_z() != 0:
            return
        r, g, b, a = self.sky(self.day_fraction())
        if getattr(self, "under_roof_group", 0):
            a = int(a * val(self.dn("Night", "Indoors", "0.55")))      # (indoors: the lamps are lit)
        if a < 4:
            return
        dark = max(0.0, min(1.0, (a - 40) / 110.0))
        night = self.night_layer
        night.fill((r, g, b, a))
        lights = self.sky_lights() if dark > 0 else []
        shown_roof = self.roof_shown
        lit = []
        for x, y, rad, warm, roof_cell in lights:
            if roof_cell is not None:
                (rx, ry), want_shown = roof_cell
                on_map = 1 <= rx <= self.xt and 1 <= ry <= self.yt
                shown = shown_roof[rx][ry] if on_map else 1
                if bool(shown) != want_shown:
                    continue
            lit.append((x, y, rad, warm, roof_cell))
            sx, sy = int(x - cam_x), int(y - cam_y)
            if -rad < sx < self.world_w + rad and -rad < sy < self.world_h + rad:
                night.blit(self.light_spot(rad), (sx - rad, sy - rad), special_flags=pygame.BLEND_RGBA_MULT)
        if self.light_mask is not None:
            rr = self.light_mask.get_width() // 2
            night.blit(self.light_mask, (int(self.player.cx) - cam_x - rr, int(self.player.cy) - cam_y - rr),
                       special_flags=pygame.BLEND_RGBA_MULT)
        scr.blit(night, (0, 0))
        if dark > 0.3:
            for x, y, rad, warm, roof_cell in lit:
                if warm and (roof_cell is None or not roof_cell[1]):
                    gr = max(10, rad // 2)
                    sx, sy = int(x - cam_x), int(y - cam_y)
                    if -gr < sx < self.world_w + gr and -gr < sy < self.world_h + gr:
                        scr.blit(self.warm_glow(gr), (sx - gr, sy - gr), special_flags=pygame.BLEND_ADD)

    # ----- sleeping (DayNight.ini [Sleep]): in a bed (Use.Words Sleep) or a script's Sleep, through the night to the
    # morning or through the day to the evening. The screen goes dark, the time moves on, and it comes back
    def sleep_refusal(self):
        """Why you can't sleep now ("" = you can)."""
        if not self.day_night_enabled or self.day_seconds <= 0:
            return self.dn("Sleep", "No.Day", "There's no day or night to sleep through.")
        p = self.player
        now = self.clock()
        secs = val(self.dn("Sleep", "Fight.Seconds", "10"))
        if self.player_last_combat and 0 <= now - self.player_last_combat < secs * 1000:
            return self.dn("Sleep", "Fighting", "You're too wound up to sleep after that fight.")
        reach = val(self.dn("Sleep", "Foe.Range", "320"))
        for e in self.world:
            if e.type == NPC and e.alive and e.hostile and distance(e.cx, e.cy, p.cx, p.cy) < reach:
                return self.dn("Sleep", "Foes", "You can't sleep with enemies nearby!")
        return ""

    def start_sleep(self, until="Next"):
        """Goes to sleep: until "Morning", "Evening", a time of day (0-1), or "Next" (the morning if it's night, else
        the evening). False (and says why) if you can't."""
        why = self.sleep_refusal()
        if why:
            self.display_message(why, "FAIL")
            return False
        u = trim(until).lower()
        morning = val(self.dn("Sleep", "Morning", "0.27")) % 1.0
        evening = val(self.dn("Sleep", "Evening", "0.80")) % 1.0
        if u == "morning":
            target = morning
        elif u == "evening":
            target = evening
        elif u and u.replace(".", "", 1).isdigit():
            target = val(u) % 1.0
        else:
            target = morning if self.is_night() else evening
        self.stop_player_walk()
        self.player_attack_target = None
        self.sleep_state = {"start": self.frame_clock(), "target": target, "woken": False}
        return True

    def sleep_times(self):
        return max(50, val(self.dn("Sleep", "Fade", "1200"))), max(0, val(self.dn("Sleep", "Hold", "1400")))

    def sleep_tick(self):
        """Every frame while asleep (the world waits): at the darkest the time moves on and you're healed; at the end
        you're awake."""
        st = self.sleep_state
        fade, hold = self.sleep_times()
        t = self.frame_clock() - st["start"]
        if not st["woken"] and t >= fade:
            st["woken"] = True
            self.set_day_fraction(st["target"])
            if val(self.dn("Sleep", "Heal", "1")) == 1:
                self.player.hp = self.player_max_hp
                if getattr(self, "player_max_mana", 0) > 0:
                    self.player_mana = self.player_max_mana
            self.sky_update()
            self.night_shown = -1
            self.last_music_check = -10 ** 9
            self.force_layer_update = True
        if t >= 2 * fade + hold:
            self.sleep_state = None
            night_wake = abs(st["target"] - val(self.dn("Sleep", "Morning", "0.27")) % 1.0) < 1e-6
            words = self.dn("Sleep", "Wake.Morning" if night_wake else "Wake.Evening", "")
            if words:
                self.display_message(words, "INFO")
            if self.main_setup_complete:
                self.save_player()

    def draw_sleep(self, scr):
        """The dark of sleep over the frame: coming down, held (with the words), lifting."""
        st = self.sleep_state
        fade, hold = self.sleep_times()
        t = self.frame_clock() - st["start"]
        if t < fade:
            k = t / fade
        elif t < fade + hold:
            k = 1.0
        else:
            k = max(0.0, 1 - (t - fade - hold) / fade)
        layer = self.__dict__.get("sleep_layer")
        if layer is None or layer.get_size() != scr.get_size():
            layer = self.sleep_layer = pygame.Surface(scr.get_size(), pygame.SRCALPHA)
        layer.fill((0, 0, 0, int(255 * k)))
        scr.blit(layer, (0, 0))
        text = self.dn("Sleep", "Text", "")
        if text and k > 0.6:
            f = self.assets.font(16, True)
            img = f.render(text, True, (200, 200, 220))
            img.set_alpha(int(255 * (k - 0.6) / 0.4))
            scr.blit(img, ((self.world_w - img.get_width()) // 2, (self.world_h - img.get_height()) // 2))

    # ----- the sun or the moon by the minimap
    def clock_rect(self):
        return pygame.Rect(self.minimap_centre_x - 11, 1, 22, 22)

    def draw_clock(self, scr):
        if not self.day_night_enabled:
            return
        r = self.clock_rect()
        t = self.day_fraction()
        pygame.draw.circle(scr, (34, 22, 14), r.center, 11)
        pygame.draw.circle(scr, (214, 170, 70), r.center, 11, 1)
        if self.is_night(t):
            pygame.draw.circle(scr, (226, 228, 240), r.center, 7)
            pygame.draw.circle(scr, (34, 22, 14), (r.centerx + 3, r.centery - 2), 6)
        else:
            k = math.sin(math.pi * (t - self.night_to) / max(1e-6, self.night_from - self.night_to))
            col = (255, int(170 + 70 * k), int(60 + 60 * k))
            for i in range(8):
                ang = i * math.pi / 4
                pygame.draw.line(scr, col, (r.centerx + 6 * math.cos(ang), r.centery + 6 * math.sin(ang)),
                                 (r.centerx + 9 * math.cos(ang), r.centery + 9 * math.sin(ang)), 1)
            pygame.draw.circle(scr, col, r.center, 5)

    # ----- who's out
    def npc_schedule(self, e):
        cache = self.__dict__.setdefault("schedule_cache", {})
        if e.name not in cache:
            cache[e.name] = trim(self.entity_ini(e.name, "Schedule", "")).capitalize()
        return cache[e.name]

    def schedule_npc(self, e):
        """Before an NPC thinks: should it be out now? Day folk walk home to the nearest door at night (and come out
        of it in the morning); night creatures keep out of sight by day. True if it's away (do nothing more)."""
        sched = self.npc_schedule(e)
        if not sched or not self.day_night_enabled or self.map_z() != 0 or e.in_combat:
            if getattr(e, "sched_away", False) and not sched:
                e.sched_away = False
            return getattr(e, "sched_away", False) and bool(sched)
        night = self.is_night()
        away_now = (sched == "Day" and night) or (sched == "Night" and not night)
        p = self.player
        far = distance(e.cx, e.cy, p.cx, p.cy) > 380
        if away_now and not getattr(e, "sched_away", False):
            if sched == "Day" and not far:
                door = self.nearest_door(e)
                if door is not None and distance(e.cx, e.cy, door[0], door[1]) > 14:
                    if self.npc_walk_to(e, door[0], door[1], e.ai.walk_speed if e.ai else e.move_speed, 6, False):
                        return False
                    e.sched_stuck = getattr(e, "sched_stuck", 0) + 1
                    if e.sched_stuck < 240:
                        return False
            elif sched == "Night" and not far:
                return False                        # (it slinks off once you're not looking)
            e.sched_away, e.sched_stuck = True, 0
            e.active = False
            return True
        if not away_now and getattr(e, "sched_away", False):
            e.sched_away = False                    # out again (from the door it went in by, or where it was)
            e.active = not self.entity_is_hidden(e)
            return False
        return getattr(e, "sched_away", False)

    def nearest_door(self, e):
        """The middle of the nearest door (a tile with Tiles.ini Door=1) on the current map (in its pixels), or None."""
        doors = self.__dict__.get("door_spots")
        if doors is None or getattr(self, "door_spots_map", None) != (self.screen_name, getattr(self, "anim_gen", 0)):
            doors = []
            for y in range(1, self.yt + 1):
                for x in range(1, self.xt + 1):
                    if self.is_door_tile(self.tile_name[x][y]):
                        doors.append(((x - 0.5) * self.tw, (y - 0.5) * self.th))
            self.door_spots, self.door_spots_map = doors, (self.screen_name, getattr(self, "anim_gen", 0))
        if not doors:
            return None
        return min(doors, key=lambda d: distance(e.cx, e.cy, d[0], d[1]))
