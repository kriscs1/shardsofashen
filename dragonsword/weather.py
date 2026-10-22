"""The weather: clear, cloudy, rain, storms (lightning and thunder), snow and blizzards in the north, fog over the
marshes, all as Data\\Weather.ini has them: each kind ([Kind.<name>]: how dark, what falls, its sound, what it is
instead somewhere else) and each climate ([Climate.<sound>]: how likely each kind is where the map's Data\\Ambient.ini
sound is that). It changes every few minutes to what suits where you are, fading in and out. Not in caves, and indoors
you only hear it. Config [Gameplay] Weather=0 turns it off (so does there being no Weather.ini)."""
import math
import os
import random

import pygame

from . import ini
from .lb import trim, val


def span(text, default):
    """"120-300" -> (120.0, 300.0); "60" -> (60.0, 60.0)."""
    try:
        parts = [float(p) for p in str(text).replace(" ", "").split("-") if p != ""]
    except ValueError:
        return default
    if not parts:
        return default
    return parts[0], parts[-1]


class WeatherMixin:
    def weather_path(self):
        return os.path.join(self.root, "Data", "Weather.ini")

    def weather_on(self):
        return val(self.config_read("Gameplay", "Weather", "1")) == 1 and os.path.exists(self.weather_path())

    def weather_set(self, key, default=""):
        """Weather.ini [Weather] key."""
        return ini.read("Weather", key, str(default), self.weather_path())

    def weather_of(self, kind, key, default=""):
        """Weather.ini [Kind.<kind>] key."""
        return ini.read("Kind." + kind, key, str(default), self.weather_path())

    @staticmethod
    def weather_colour(text, default):
        try:
            c = tuple(max(0, min(255, int(float(p)))) for p in text.replace(",", " ").split()[:3])
        except ValueError:
            return default
        return c if len(c) == 3 else default

    def climate_odds(self, clim):
        """{kind: how likely} in climate clim ("" = the default one)."""
        items = ini.section("Climate." + clim, self.weather_path()) if clim else []
        if not items:
            items = ini.section("Climate.Default", self.weather_path())
        out = {}
        for k, v in items:
            try:
                if float(v) > 0:
                    out[trim(k)] = float(v)
            except ValueError:
                pass
        return out or {"clear": 1}

    def climate(self):
        """The climate here: the map's Ambient.ini sound if Weather.ini has a [Climate.<it>], else "" (the default
        one); None underground (no weather)."""
        if self.map_z() != 0:
            return None
        cache = self.__dict__.setdefault("climate_cache", {})
        if self.screen_name not in cache:
            amb = trim(ini.read("Maps", self.screen_name, "", os.path.join(self.root, "Data", "Ambient.ini")))
            cache[self.screen_name] = amb if amb and ini.section("Climate." + amb, self.weather_path()) else ""
        return cache[self.screen_name]

    def weather_kind(self):
        """What it's doing here and now (Becomes: rain falls as snow in the snow; Otherwise: the desert stays dry)."""
        w = getattr(self, "weather", None)
        clim = self.climate()
        if not w or clim is None:
            return "clear", 0.0
        kind = w["kind"]
        odds = self.climate_odds(clim)
        if kind not in odds:
            kind = trim(self.weather_of(kind, "Becomes", ""))
            if kind not in odds:
                kind = trim(self.weather_set("Otherwise", "cloudy"))
        return kind, w["level"]

    def weather_tick(self):
        """Every frame: the weather fading in or out, and changing now and then."""
        if not self.weather_on():
            self.weather = None
            return
        now = self.clock()
        w = self.__dict__.get("weather")
        if w is None:
            first = val(self.weather_set("First", "60"))
            w = self.weather = {"kind": "clear", "level": 0.0, "next": now + first * 1000, "fading": False}
        dt = max(0.0, min(0.1, self.loop_delta))
        clim = self.climate()
        if now >= w["next"] and not w["fading"] and clim is not None:
            w["fading"] = True                      # fade out what's here, then the next weather fades in
        if w["fading"]:
            w["level"] = max(0.0, w["level"] - dt / max(0.1, val(self.weather_set("Fade.Out", "12"))))
            if w["level"] <= 0:
                rng = random.Random(now)
                odds = self.climate_odds(clim or "")
                kinds = list(odds)
                w["kind"] = rng.choices(kinds, [odds[k] for k in kinds])[0]
                lo, hi = span(self.weather_set("Lasts", "120-300"), (120, 300))
                w["next"] = now + int(rng.uniform(lo, hi) * 1000)
                w["fading"] = False
                kind, _ = self.weather_kind()
                words = self.weather_of(kind, "Message", "")
                if words and self.map_z() == 0:
                    self.display_message(words, "INFO")
        elif w["kind"] != "clear":
            w["level"] = min(1.0, w["level"] + dt / max(0.1, val(self.weather_set("Fade.In", "15"))))
        self.weather_lightning(now)

    def weather_ambient(self, want):
        """The background sound: the rain's in place of the place's own while it rains outside."""
        kind, level = self.weather_kind()
        if level < 0.3 or self.map_z() != 0 or getattr(self, "under_roof_group", 0):
            return want
        return trim(self.weather_of(kind, "Ambient", "")) or want

    # ----- drawing (over the world, under the night)
    def draw_weather(self, scr, cam_x, cam_y):
        kind, level = self.weather_kind()
        if level <= 0.01 or kind == "clear":
            self.weather_flash_draw(scr)
            return
        indoors = getattr(self, "under_roof_group", 0)
        shade = int(val(self.weather_of(kind, "Shade", "0")) * level * (0.5 if indoors else 1))
        if shade > 0:
            layer = self.__dict__.get("weather_shade")
            if layer is None or layer.get_size() != scr.get_size():
                layer = self.weather_shade = pygame.Surface(scr.get_size(), pygame.SRCALPHA)
            layer.fill(self.weather_colour(self.weather_set("Shade.Colour", "40 46 58"), (40, 46, 58)) +
                       (min(255, shade),))
            scr.blit(layer, (0, 0))
        if not indoors:
            draw = trim(self.weather_of(kind, "Draw", "")).lower()
            amount = level * (val(self.weather_of(kind, "Amount", "1")) or 1)
            if draw == "rain":
                self.draw_rain(scr, amount, self.weather_colour(self.weather_of(kind, "Colour", ""), (168, 182, 206)))
            elif draw == "snow":
                self.draw_snow(scr, amount, val(self.weather_of(kind, "Wind", "18")))
            elif draw == "fog":
                self.draw_fog_weather(scr, cam_x, cam_y, level)
        self.weather_flash_draw(scr)

    def weather_particles(self, n, make, kind):
        ps = self.__dict__.setdefault("weather_ps_" + kind, [])
        while len(ps) < n:
            ps.append(make(True))
        del ps[n:]
        return ps

    def draw_rain(self, scr, amount, col=(168, 182, 206)):
        w, h = scr.get_size()
        rng = random.Random()
        dt = max(0.0, min(0.1, self.loop_delta))

        def make(anywhere):
            return [rng.uniform(-40, w + 40), rng.uniform(0, h) if anywhere else rng.uniform(-60, -5),
                    rng.uniform(520, 760), rng.randint(9, 15)]
        ps = self.weather_particles(int(150 * amount), make, "rain")
        splash = tuple(min(255, c + 30) for c in col)
        for p in ps:
            p[1] += p[2] * dt
            p[0] -= p[2] * dt * 0.22
            if p[1] > h or p[0] < -50:
                if p[1] > h * 0.2 and rng.random() < 0.3:          # a splash where it lands
                    pygame.draw.circle(scr, splash, (int(p[0]), int(min(h - 2, p[1] - rng.uniform(0, h * 0.6)))), 1)
                p[:] = make(False)
            pygame.draw.line(scr, col, (int(p[0]), int(p[1])), (int(p[0] + p[3] * 0.22), int(p[1] - p[3])), 1)

    def draw_snow(self, scr, amount, wind=18):
        w, h = scr.get_size()
        rng = random.Random()
        dt = max(0.0, min(0.1, self.loop_delta))
        t = self.clock() / 1000.0
        blizzard = wind > 60                    # (a gale: the flakes come in from the side too)

        def make(anywhere):
            return [rng.uniform(-20, w + 20), rng.uniform(0, h) if anywhere else rng.uniform(-30, -3),
                    rng.uniform(30, 70), rng.choice((1, 2, 2)), rng.uniform(0, 6.3)]
        ps = self.weather_particles(int(130 * amount), make, "snow")
        for p in ps:
            p[1] += p[2] * dt
            p[0] += (wind + 14 * math.sin(t * 1.3 + p[4])) * dt
            if p[1] > h or p[0] > w + 30:
                p[:] = make(False)
                if blizzard:
                    p[0] = rng.uniform(-w * 0.5, w)
            x, y = int(p[0]), int(p[1])
            pygame.draw.circle(scr, (140, 150, 172), (x + 1, y + 1), p[3])   # (a soft shadow: it shows on snow)
            pygame.draw.circle(scr, (252, 253, 255), (x, y), p[3])

    def draw_fog_weather(self, scr, cam_x, cam_y, level):
        tex = self.__dict__.get("fog_weather_tex")
        if tex is None:                     # soft drifting banks of mist: noise, smoothly scaled up, seamless
            import numpy as np
            rng = np.random.default_rng(7)
            n = 256
            small = rng.random((8, 8))
            src = pygame.Surface((8, 8))
            v = (small * 255).astype(np.uint8)
            pygame.surfarray.blit_array(src, np.stack([v, v, v], axis=-1))
            tiled = pygame.Surface((24, 24))                    # (3 x 3 copies, so the scaling wraps round)
            for ty in range(3):
                for tx in range(3):
                    tiled.blit(src, (tx * 8, ty * 8))
            big = pygame.transform.smoothscale(tiled, (n * 3, n * 3)).subsurface((n, n, n, n))
            g = pygame.surfarray.array3d(big)[:, :, 0].astype(float) / 255.0
            for _ in range(4):                                  # (softened, wrapping round so it stays seamless)
                for sh in (9, 18):
                    g = (g + np.roll(g, sh, 0) + np.roll(g, -sh, 0) + np.roll(g, sh, 1) + np.roll(g, -sh, 1)) / 5
            g = (g - g.min()) / max(1e-6, g.max() - g.min())
            tex = pygame.Surface((n, n), pygame.SRCALPHA)
            tex.fill((220, 224, 228, 0))
            a = pygame.surfarray.pixels_alpha(tex)
            a[:, :] = (g * g * 150 + 25).astype(np.uint8)
            del a
            self.fog_weather_tex = tex
        layer = self.__dict__.get("fog_weather_layer")
        w, h = scr.get_size()
        if layer is None or layer.get_size() != (w, h):
            layer = self.fog_weather_layer = pygame.Surface((w, h), pygame.SRCALPHA)
        layer.fill((0, 0, 0, 0))
        drift = int(self.clock() / 1000.0 * 9)
        ox, oy = -((cam_x + drift) % 256), -(cam_y % 256)
        for y in range(int(oy), h, 256):
            for x in range(int(ox), w, 256):
                layer.blit(tex, (x, y))
        layer.set_alpha(int(220 * level))
        scr.blit(layer, (0, 0))

    # ----- lightning
    def weather_lightning(self, now):
        kind, level = self.weather_kind()
        if (val(self.weather_of(kind, "Lightning", "0")) != 1 or level < 0.5 or getattr(self, "under_roof_group", 0)
                or self.map_z() != 0):
            return
        nxt = self.__dict__.setdefault("lightning_next", now + 8000)
        if now >= nxt:
            lo, hi = span(self.weather_set("Lightning.Every", "7-18"), (7, 18))
            tlo, thi = span(self.weather_set("Thunder.After", "0.4-2.2"), (0.4, 2.2))
            self.lightning_at = now
            self.lightning_next = now + int(random.uniform(lo, hi) * 1000)
            self.thunder_at = now + int(random.uniform(tlo, thi) * 1000)
        if getattr(self, "thunder_at", 0) and now >= self.thunder_at:
            self.thunder_at = 0
            self.play_sound(trim(self.weather_set("Thunder.Sound", "Thunder")))

    def weather_flash_draw(self, scr):
        at = getattr(self, "lightning_at", None)
        if at is None:
            return
        t = self.clock() - at
        if t > 450 or t < 0:
            self.lightning_at = None
            return
        a = int(170 * (1 - t / 450.0) * (1.0 if t > 80 or (t // 40) % 2 == 0 else 0.4))
        layer = self.__dict__.get("flash_layer")
        if layer is None or layer.get_size() != scr.get_size():
            layer = self.flash_layer = pygame.Surface(scr.get_size(), pygame.SRCALPHA)
        layer.fill((236, 240, 255, a))
        scr.blit(layer, (0, 0))
