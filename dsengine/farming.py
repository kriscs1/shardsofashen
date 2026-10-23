"""Farming: seeds sown in tilled soil grow, by the clock, into crops to harvest (Data\\Crops.ini, the Farming skill).

  * Use a seed (Entities.ini Crop=<crop>) on tilled soil (a tile whose name starts with "Soil") to sow it. On a
    homestead only its owner may sow; anywhere else (the farmer's furrows by Ashford) anyone may, on an empty plot.
  * The crop grows through <Crop>_Crop001 (sprouting), 002 (growing) and 003 (ripe) over Minutes, on the world's
    clock: it grows while nobody is looking, and while the server is off. Everyone sees it grow.
  * Only whoever sowed it may harvest it: Yield of Gives (+1 every 10 Farming levels), Farming experience, and a
    chance (Seed.Back) of a seed back. On the public plots a ripe crop nobody harvests withers after Wither minutes.

World.farms (Farms) keeps the plots; FarmMixin is the player's side (Session)."""
import logging
import random

from dragonsword import ini
from dragonsword.lb import val, trim, word, lbstr, clock_seconds

log = logging.getLogger("dragonsword.farming")

CHECK_MS = 1000
STAGES = 3


class Farms:
    def __init__(self, world):
        self.w = world
        self.d = world.data
        self.crops = self.read_crops()
        self.plots = {}                 # (map, x, y) -> {"crop", "owner", "sown" (clock seconds), "stage"}
        self.last_check = 0
        self.clock = clock_seconds      # (tests make time pass faster)

    def read_crops(self):
        path = self.d.data_file("Crops.ini")
        out = {}
        try:
            text = ini.read_text(path)
        except OSError:
            return out
        sec = None
        for ln in text.replace("\r", "").split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith(";"):
                continue
            if ln.startswith("[") and ln.endswith("]"):
                sec = ln[1:-1].strip()
                out[sec] = {"name": sec, "seed": sec + "_Seed", "gives": sec, "level": 1, "minutes": 5.0,
                            "yield": "2-4", "xp": 0.1, "seed_back": 30, "wither": 60.0}
            elif sec and "=" in ln:
                k, v = (s.strip() for s in ln.split("=", 1))
                c, k = out[sec], k.lower()
                if k == "seed":
                    c["seed"] = v
                elif k == "gives":
                    c["gives"] = v
                elif k == "level":
                    c["level"] = max(1, int(val(v)))
                elif k == "minutes":
                    c["minutes"] = max(0.05, float(val(v)))
                elif k == "yield":
                    c["yield"] = v
                elif k == "xp":
                    c["xp"] = float(val(v))
                elif k == "seed.back":
                    c["seed_back"] = float(val(v))
                elif k == "wither":
                    c["wither"] = float(val(v))
        return out

    def crop_of_seed(self, item):
        name = trim(self.d.entity_ini(item, "Crop", ""))
        return self.crops.get(name)

    @staticmethod
    def stage_tile(crop, stage):
        return "%s_Crop%03d" % (crop, stage)

    def crop_of_tile(self, name):
        """(crop, stage) of a crop tile's name, or (None, 0)."""
        if "_Crop" not in (name or ""):
            return None, 0
        crop, _, n = name.rpartition("_Crop")
        return (crop, int(val(n))) if crop in self.crops else (None, 0)

    def stage_at(self, plot, now=None):
        c = self.crops.get(plot["crop"])
        if c is None:
            return STAGES
        grown = ((self.clock() if now is None else now) - plot["sown"]) / (c["minutes"] * 60)
        return max(1, min(STAGES, 1 + int(grown * (STAGES - 1))))

    def seconds_left(self, plot):
        c = self.crops.get(plot["crop"])
        return 0 if c is None else max(0, int(plot["sown"] + c["minutes"] * 60 - self.clock()))

    def is_soil(self, tile):
        return (tile or "").startswith("Soil")

    def sow(self, m, x, y, crop, owner):
        self.plots[(m.name, x, y)] = {"crop": crop, "owner": owner, "sown": self.clock(), "stage": 1}
        self.w.change_tile(m, x, y, self.stage_tile(crop, 1))

    def clear(self, m, x, y):
        """The plot is empty again (harvested, withered, or taken down)."""
        self.plots.pop((m.name, x, y), None)
        c = m.cell(x, y)
        if self.crop_of_tile(m.decor[c])[0]:
            self.w.change_tile(m, x, y, "%s+Decor()" % m.tile[c])

    def tick(self):
        """Crops grow (once a second is plenty); ripe ones on public plots wither in the end."""
        w = self.w
        if w.now - self.last_check < CHECK_MS and w.now >= self.last_check:
            return
        self.last_check = w.now
        now = self.clock()
        for key, plot in list(self.plots.items()):
            m = w.maps.get(key[0])
            if m is None:
                continue
            stage = self.stage_at(plot, now)
            c = self.crops.get(plot["crop"])
            if (stage == STAGES and c is not None and not w.homes.is_home_map(m.name) and
                    now - plot["sown"] > (c["minutes"] + c["wither"]) * 60):
                self.clear(m, key[1], key[2])
                s = w.sessions.get(plot["owner"])
                if s is not None:
                    s.display_message("Your %s on the farm withered: nobody harvested it." % plot["crop"].lower(),
                                      "INFO")
                continue
            if stage != plot["stage"]:
                plot["stage"] = stage
                w.change_tile(m, key[1], key[2], self.stage_tile(plot["crop"], stage))

    # ----- saving
    def state(self):
        return [[k[0], k[1], k[2], p["crop"], p["owner"], p["sown"]] for k, p in self.plots.items()]

    def load(self, saved):
        """After the homes (their maps must be there): the crops back on their soil, grown as far as they have."""
        for row in saved or []:
            try:
                name, x, y, crop, owner, sown = row
                x, y, sown = int(x), int(y), float(sown)
            except (TypeError, ValueError):
                continue
            m = self.w.maps.get(name)
            if m is None or crop not in self.crops or not m.inside(x, y):
                continue
            plot = {"crop": crop, "owner": owner, "sown": sown, "stage": 1}
            plot["stage"] = self.stage_at(plot)
            self.plots[(name, x, y)] = plot
            m.change_cell(x, y, self.stage_tile(crop, plot["stage"]))


class FarmMixin:
    """The player's side of farming (on Session)."""

    @property
    def farms(self):
        return self.w.farms

    def tile_xy(self, e):
        m = self.w.map_at(e.z if hasattr(e, "z") else self.player.z, e.x + 1, e.y + 1)
        if m is None:
            return None, 0, 0
        return m, int((e.x + 1 - m.ox) // self.tw) + 1, int((e.y + 1 - m.oy) // self.th) + 1

    def sow_seed(self, item, target):
        """Using a seed on something: True if it was farming (whether or not it worked)."""
        farms = self.farms
        c = farms.crop_of_seed(item.name)
        if c is None:
            return False
        from .entity import TILE
        if target is None or target.type != TILE:
            self.display_message("Sow seeds in tilled soil: use them on it.", "FAIL")
            return True
        if self.player_distance_to(target) > 48:
            self.display_message("You are too far away!", "FAIL")
            return True
        m, x, y = self.tile_xy(target)
        if m is None:
            return True
        cell = m.cell(x, y)
        if not farms.is_soil(m.tile[cell]):
            self.display_message("Seeds only grow in tilled soil.", "FAIL")
            return True
        if m.decor[cell] or (m.name, x, y) in farms.plots:
            self.display_message("Something is growing there already.", "FAIL")
            return True
        owner = self.w.homes.owner_of(m.name)
        if owner is not None and owner != self.player_name:
            self.display_message("This is %s's homestead: only they can sow here." % owner, "FAIL")
            return True
        level = self.skill_level("Farming")
        if level < c["level"]:
            self.refuse("You need level %d Farming to grow %s (you have %d)." % (c["level"], c["name"].lower(), level))
            return True
        self.remove_inventory_item(item.name, 1)
        farms.sow(m, x, y, c["name"], self.player_name)
        self.play_sound("Dig" if self.data.loaded("Dig") else "Pickup")
        self.update_skill("Farming", "+" + lbstr(round(c["xp"] / 4, 3)))
        mins = c["minutes"]
        self.display_message("You sow the %s. It'll be ripe in about %s minute%s." %
                             (item.name.replace("_", " ").lower(), lbstr(round(mins, 1)), "" if mins == 1 else "s"),
                             "SUCCESS")
        return True

    def crop_action(self, verb, e):
        """Harvest or Examine on a crop: True if it was one."""
        farms = self.farms
        crop, stage = farms.crop_of_tile(e.name)
        if crop is None or verb not in ("Harvest", "Examine"):
            return False
        m, x, y = self.tile_xy(e)
        plot = farms.plots.get((m.name, x, y)) if m is not None else None
        if plot is None:
            self.display_message("%s, gone wild." % crop, "EXAMINE")
            return True
        mine = plot["owner"] == self.player_name
        whose = "Your" if mine else "%s's" % plot["owner"]
        what = crop.lower() if crop != "Herb" else "herbs"
        if verb == "Examine" or stage < STAGES:
            if stage < STAGES:
                left = farms.seconds_left(plot)
                when = "about %d minute%s" % ((left + 59) // 60, "" if (left + 59) // 60 == 1 else "s") \
                    if left >= 60 else "less than a minute"
                self.display_message("%s %s: %s, ripe in %s." % (whose, what, ("sprouting", "growing")[stage - 1], when),
                                     "EXAMINE")
            else:
                self.display_message("%s %s, ripe for harvesting." % (whose, what), "EXAMINE")
            return True
        if not mine:
            self.display_message("That's %s's %s: they sowed it." % (plot["owner"], what), "FAIL")
            return True
        if self.player_distance_to(e) > 48:
            self.display_message("You are too far away!", "FAIL")
            return True
        c = farms.crops[crop]
        lo, hi = (int(val(v)) for v in (word(c["yield"], 1, "-"), word(c["yield"], 2, "-") or word(c["yield"], 1, "-")))
        n = random.randint(max(1, lo), max(lo, hi)) + self.skill_level("Farming") // 10
        room = self.inventory_slots_available(c["gives"])
        if room <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return True
        got = min(n, room)
        self.add_inventory_item(c["gives"], got, quiet=True)
        farms.clear(m, x, y)
        self.update_skill("Farming", "+" + lbstr(c["xp"]))
        extra = ""
        if random.uniform(0, 100) < c["seed_back"] and self.inventory_slots_available(c["seed"]) > 0:
            self.add_inventory_item(c["seed"], 1, quiet=True)
            extra = " and a seed"
        self.play_sound("Pickup")
        self.display_message("You harvest %d %s%s." % (got, c["gives"].replace("_", " ").lower(), extra), "SUCCESS")
        return True
