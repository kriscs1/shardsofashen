"""The game's data as the server reads it: data\\Config.ini and the other INI files, the sprites' sizes (for the
footprints and positions of things; the pictures themselves are the browser's), named places and the quests.
Everything that doesn't change while the game runs; the INI files are read again when they change on disk."""
import os

from dragonsword import ini
from dragonsword.entity import PLAYER, NPC, TILE, INFRONTTILE, ROOF, TYPE_NAMES, DEFAULT_LIMITS
from dragonsword.lb import val, trim, lbstr, strip_digits
from dragonsword.places import read_places

from .imgsize import sprite_size

# The order the desktop game loaded its sprite folders in (the first one loaded keeps a name)
SPRITE_FOLDERS = ("Interface", "Tiles", "Entities", "Walk", "Worn", "Effects")
EXTS = (".png", ".bmp")


class GameData:
    def __init__(self, root):
        self.root = root
        self.config_path = os.path.join(root, "data", "Config.ini")
        self.sprites = {}           # name -> (folder, path); sizes read when first wanted
        self._sizes = {}
        self._caches = {}
        self.index_sprites()
        self.read_config()

    # =================================================================================================================
    # Files
    # =================================================================================================================
    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def data_file(self, name):
        return os.path.join(self.root, "data", name)

    def config_read(self, section, key, default):
        return ini.read(section, key, default, self.config_path)

    def tile_ini(self, section, key, default):
        return ini.read(section, key, default, self.data_file("Tiles.ini"))

    def spell_ini(self, spell, key, default):
        return ini.read(spell, key, default, self.data_file("Spells.ini"))

    def entity_ini(self, section, key, default):
        """Entities.ini [section] key. A decor tile placed as an object (no Entities.ini section of its own) reads its
        Tiles.ini section instead."""
        if self.is_decor_object(section):
            return self.tile_ini(section, key, default)
        return ini.read(section, key, default, self.data_file("Entities.ini"))

    def cache(self, name):
        return self._caches.setdefault(name, {})

    def forget_caches(self):
        """The data files may have changed (the editor): the derived caches are worked out again."""
        self._caches = {}
        ini.forget()

    @staticmethod
    def read_lines(path):
        try:
            text = ini.read_text(path)
        except OSError:
            return []
        return [ln.replace("\r", "") for ln in text.split("\n")]

    # =================================================================================================================
    # Config ([Get.Variables] of the original)
    # =================================================================================================================
    def read_config(self):
        c = self.config_read
        self.xt = val(c("Interface", "Map.X.Tiles", "25"))
        self.yt = val(c("Interface", "Map.Y.Tiles", "21"))
        if not 1 <= self.xt <= 50:
            self.xt = 25
        if not 1 <= self.yt <= 50:
            self.yt = 21
        self.tw, self.th = self.size_of("Black001")
        allw = "1" * 49
        self.walk_res = int(len(self.tile_ini("Black001", "Walkable.Data", allw)) ** 0.5 + 0.5) or 7
        self.all_walkable = "1" * (self.walk_res ** 2)
        self.sw = self.tw * self.xt
        self.sh = self.th * self.yt
        self.grid_cell = max(4, int(min(self.tw, self.th) / 2))
        self.npc_respawn_delay = val(c("Gameplay", "NPC.Respawn.Delay", c("Gameplay", "NPC.Repawn.Delay", "10")))
        self.shop_restock_delay = val(c("Gameplay", "Shop.Restock.Seconds", "300"))
        self.item_respawn_delay = val(c("Gameplay", "Item.Respawn.Delay", "600"))
        self.sell_price_factor = val(c("Gameplay", "Sell.Price.Factor", "0.25"))
        self.item_despawn_delay = val(c("Gameplay", "Item.Despawn.Delay", "180"))
        self.bank_slots = min(500, max(1, val(c("Gameplay", "Maximum.Bank.Slots", "50"))))
        self.fog_view_distance = val(c("Gameplay", "FogOfWar.Viewable.Distance", "200"))
        self.start_map = c("Gameplay", "Start.Map", "1,1,0").replace(" ", "")
        self.start_x = val(c("Gameplay", "Start.X", "300"))
        self.start_y = val(c("Gameplay", "Start.Y", "300"))
        if not self.map_exists(self.start_map):
            self.start_map = self.first_map()
        self.day_night_enabled = val(c("Gameplay", "DayNight", "1"))
        self.day_seconds = 60 * max(0.1, val(c("Gameplay", "Day.Minutes", "24")))   # (0 would stop the clock dead)
        self.pathfinding_enabled = val(c("Gameplay", "Pathfinding", "1")) == 1
        skills = c("Skills", "List", "Strength,Defence,Hitpoints,Cooking,Smithing,Fishing,Mining,Woodcutting")
        names = [trim(s) for s in skills.split(",") if s != ""][:30]
        self.total_skills = len(names)
        self.skill_name = [""] + names
        self.admin_players = [trim(n).lower() for n in c("Admin", "Players", "Admin").split(",") if trim(n)]
        self.hp_base = max(0, val(c("Gameplay", "Hitpoints.Base", "19")))
        self.hp_per_level = max(0.0, val(c("Gameplay", "Hitpoints.Per.Level", "0.5")))
        self.hp_regen_delay = max(0, val(c("Gameplay", "HP.Regen.Delay", "6")))
        self.hp_regen_every = max(0.2, val(c("Gameplay", "HP.Regen.Every", "3")))
        self.skill_max_level = max(2, int(val(c("Gameplay", "Skill.Max.Level", "50"))))
        self.xp_slowdown = max(0.0, val(c("Gameplay", "XP.Slowdown", "10")))
        self.monster_damage = max(0.1, val(c("Gameplay", "Monster.Damage", "2")))
        self.death_gold_loss = min(100, max(0, val(c("Gameplay", "Death.Gold.Loss", "25"))))
        self.player_attack_speed = max(0.1, val(c("Gameplay", "Player.Attack.Speed", "0.8")))
        self.player_move_speed = self.speed_to_pixels(val(c("Gameplay", "Player.Movement.Speed", "4")))
        self.inventory_columns = max(1, val(c("Interface", "InventoryItems.Columns", "5")))
        self.inventory_rows = max(1, val(c("Interface", "InventoryItems.Rows", "7")))
        self.ab_columns = min(9, max(1, val(c("Interface", "ActionBox.Columns", "9"))))
        self.ab_rows = min(3, max(1, val(c("Interface", "ActionBox.Rows", "3"))))
        self.equip_slots = 8
        self.equip_slot_names = [""] + "Weapon Shield Head Body Legs Feet Hands Ring".split()
        self.gear_rank = [0, 7, 6, 5, 3, 1, 2, 4, 8]
        self.type_limits = {}
        for t, default in DEFAULT_LIMITS.items():
            self.type_limits[t] = max(1, val(c("Entities", "total.%s.IDs" % TYPE_NAMES[t], lbstr(default))))

    def speed_to_pixels(self, speed):
        """Speeds below 10 are tiles per second (old data), otherwise pixels per second."""
        return speed * self.tw if speed < 10 else speed

    def disabled_skills(self):
        return {trim(s).upper() for s in self.config_read("Skills", "Disabled", "").split(",") if trim(s)}

    def god_mode_setting(self):
        return val(self.config_read("Admin", "GodMode", "0"))

    # =================================================================================================================
    # Maps
    # =================================================================================================================
    def map_path(self, name):
        return os.path.join(self.root, "maps", name + ".txt")

    def map_exists(self, name):
        return bool(name) and os.path.exists(self.map_path(name))

    def map_names(self):
        try:
            files = sorted(f for f in os.listdir(os.path.join(self.root, "maps")) if f.lower().endswith(".txt"))
        except OSError:
            return []
        return [f[:-4] for f in files if os.path.isfile(os.path.join(self.root, "maps", f))]

    def first_map(self):
        names = self.map_names()
        return names[0] if names else ""

    # =================================================================================================================
    # Sprites: only their sizes (and whether walking frames exist) matter here
    # =================================================================================================================
    def index_sprites(self):
        self.sprites = {}
        for folder in SPRITE_FOLDERS:
            base = os.path.join(self.root, "sprites", folder)
            try:
                files = sorted(os.listdir(base), key=str.lower)
            except OSError:
                continue
            for f in files:
                n, ext = os.path.splitext(f)
                if ext.lower() in EXTS and n not in self.sprites and n != "Thumb":
                    # (a PNG first, an old BMP if that's what there is)
                    png = os.path.join(base, n + ".png")
                    self.sprites[n] = (folder, png if os.path.exists(png) else os.path.join(base, f))

    def loaded(self, name):
        return bool(name) and name in self.sprites

    def size_of(self, name):
        """(w, h) of a sprite (32 x 32 if there's no such sprite, as the original's assets.width/height)."""
        s = self._sizes.get(name)
        if s is None:
            entry = self.sprites.get(name)
            s = sprite_size(entry[1]) if entry else None
            s = s or (32, 32)
            self._sizes[name] = s
        return s

    def width(self, name):
        return self.size_of(name)[0]

    def height(self, name):
        return self.size_of(name)[1]

    def fallback_sprite(self):
        return "Placeholder" if self.loaded("Placeholder") else next(iter(self.sprites), "")

    def animation_available(self, base):
        """Walking frames <base><Dir><Frame>: 4 = all four directions, 2 = side-on (2 and 8 only), 0 = none."""
        if not base:
            return 0
        cache = self.cache("walk_kinds")
        k = cache.get(base)
        if k is None:
            def frames(dirs):
                return all(self.loaded(base + d + f) for d in dirs for f in "abc")
            k = 4 if frames("1248") else (2 if frames("28") else 0)
            cache[base] = k
        return k

    def first_image(self, etype, name):
        """The picture an entity of etype called name starts with, and whether it is animated."""
        if etype in (PLAYER, NPC) and self.animation_available(name) > 0:
            return (name + "2a", True) if self.animation_available(name) == 2 else (name + "1a", True)
        if self.loaded(name):
            return name, False
        return self.fallback_sprite(), False

    def sprite_size_of(self, etype, name):
        image, _ = self.first_image(etype, name)
        return self.size_of(image)

    def gear_has_art(self, item):
        if not item:
            return False
        cache = self.cache("gear_art")
        if item not in cache:
            cache[item] = all(self.loaded("Worn_" + item + d + f) for d in "1248" for f in "abc")
        return cache[item]

    # =================================================================================================================
    # Tiles
    # =================================================================================================================
    def is_decor_tile(self, name):
        cache = self.cache("decor_tile")
        if name not in cache:
            cache[name] = bool(name) and self.tile_ini(name, "Layer", "").strip().lower() == "decor"
        return cache[name]

    def is_under_tile(self, name):
        """Tiles.ini Layer=Under: something flat on the floor (a rug), under the decor: a chair can stand on it."""
        cache = self.cache("under_tile")
        if name not in cache:
            cache[name] = bool(name) and self.tile_ini(name, "Layer", "").strip().lower() == "under"
        return cache[name]

    def cell_under(self, spec):
        """What a cell spec puts on the floor under its decor: +Under(Name), or a Layer=Under tile on its own
        (None: leave it as it is)."""
        from dragonsword.lb import word
        spec = trim(spec)
        k = 2
        while word(spec, k, "+") != "":
            overlay = word(spec, k, "+")
            if trim(word(overlay, 1, "(")) == "Under":
                return trim(word(word(overlay, 2, "("), 1, ")"))
            k += 1
        first = trim(word(spec, 1, "+"))
        return first if self.is_under_tile(first) else None

    def is_decor_object(self, name):
        cache = self.cache("decor_object")
        if name not in cache:
            cache[name] = bool(name) and self.is_decor_tile(name) and not ini.section(
                name, self.data_file("Entities.ini"))
        return cache[name]

    def tile_walk_data(self, name):
        cache = self.cache("walk_data")
        w = cache.get(name)
        if w is None:
            w = self.tile_ini(name, "Walkable.Data", self.all_walkable)
            if len(w) < len(self.all_walkable):
                w = (w + self.all_walkable)[:len(self.all_walkable)]
            cache[name] = w
        return w

    def tile_los(self, name):
        cache = self.cache("tile_los")
        if name not in cache:
            cache[name] = val(self.tile_ini(name, "Line.of.Sight", "1"))
        return cache[name]

    def cell_walk_los(self, tile, decor):
        """A cell's walk mask and line of sight: the tile's, with its decor's over them."""
        walk = self.tile_walk_data(tile)
        los = self.tile_los(tile)
        if decor:
            over = self.tile_walk_data(decor)
            walk = "".join("1" if a == "1" and b == "1" else "0" for a, b in zip(walk, over))
            if self.tile_los(decor) == 0:
                los = 0
        return walk, los

    def cell_speed(self, tile, decor):
        """How fast you walk over a cell: its decor's Walk.Speed (tall grass), else its tile's."""
        s = self.tile_ini(decor, "Walk.Speed", "") if decor else ""
        if trim(s) == "":
            s = self.tile_ini(tile, "Walk.Speed", "1")
        return min(3, max(0.2, val(s)))

    def door_kind(self, name):
        """Tiles.ini Door=: "1" a door, "Gate" a gateway, "" neither."""
        cache = self.cache("door_kind")
        if name not in cache:
            v = trim(self.tile_ini(name, "Door", "")) if name else ""
            cache[name] = "" if v in ("", "0") else ("Gate" if v.lower() == "gate" else "1")
        return cache[name]

    def door_open_tile(self, name):
        cache = self.cache("door_open")
        if name not in cache:
            cache[name] = self.tile_ini(name, "Open.Tile", "") if name else ""
        return cache[name]

    def unlocked_tile(self, name):
        cache = self.cache("unlocked_tile")
        if name not in cache:
            cache[name] = self.tile_ini(name, "Unlocked.Tile", "") if name else ""
        return cache[name]

    def cell_spec(self, spec):
        """What a cell is to change to: (ground tile or "", decor or None = leave the decor as it is)."""
        from dragonsword.lb import word
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
        if self.is_under_tile(tile):                # (a rug: it goes under the decor, not in place of the floor)
            return "", decor
        return tile, decor

    def spec_blocks(self, spec):
        tile, decor = self.cell_spec(spec)
        return any(n and self.tile_walk_data(n) != self.all_walkable for n in (tile, decor))

    def object_footprint(self, name, w, h):
        """(cols, rows, data) of object name's footprint at its size w x h, or None (you walk through it)."""
        cache = self.cache("footprint")
        key = (name, w, h)
        if key not in cache:
            data = trim(self.entity_ini(name, "Walkable.Data", ""))
            res = self.walk_res
            cols = max(1, int(round(w * res / self.tw)))
            rows = max(1, int(round(h * res / self.th)))
            fp = None
            if data and "0" in data and len(data) == cols * rows and not set(data) - {"0", "1"}:
                fp = (cols, rows, data)
            cache[key] = fp
        return cache[key]

    def entity_light(self, name):
        cache = self.cache("entity_light")
        if name not in cache:
            try:
                cache[name] = max(0, int(float(self.entity_ini(name, "Light", "0") or 0)))
            except ValueError:
                cache[name] = 0
        return cache[name]

    def npc_schedule(self, name):
        cache = self.cache("schedule")
        if name not in cache:
            cache[name] = trim(self.entity_ini(name, "Schedule", "")).capitalize()
        return cache[name]

    def item_max_dur(self, name):
        cache = self.cache("durability")
        if name not in cache:
            cache[name] = max(0, int(val(self.entity_ini(name, "Durability", "0")))) if name else 0
        return cache[name]

    def stackable_quantity(self, name):
        return max(1, val(self.entity_ini(name, "Stackable", "1")))

    def examine_text(self, name, etype):
        if etype in (TILE, INFRONTTILE, ROOF):
            t = self.tile_ini(name, "Examine.Info", "")
            if t == "":
                t = self.tile_ini(strip_digits(name), "Examine.Info", "")
            return t
        return self.entity_ini(name, "Examine.Info", "")

    # =================================================================================================================
    # Places and quests
    # =================================================================================================================
    def places(self):
        folder = os.path.join(self.root, "maps")
        try:
            stamp = max((e.stat().st_mtime for e in os.scandir(folder) if e.name.lower().endswith(".txt")), default=0)
        except OSError:
            stamp = 0
        cache = self._caches.get("places_cache")
        if cache is None or cache[0] != stamp:
            found, _ = read_places(folder, self.yt, self.tw)
            cache = self._caches["places_cache"] = (stamp, found)
        return cache[1]

    def tile_place(self, map_name, tx, ty):
        """The place ID on tile tx,ty of a map (an Id line, put on a tile in the editor), or "": a tile's own name,
        so a script can be its own - Examine Grave_Tom_Barrow, not every grave's."""
        found = self.places()
        cache = self._caches.get("tile_places")
        if cache is None or cache[0] is not found:
            cache = self._caches["tile_places"] = (found, {(p.map, p.tx, p.ty): p.name for p in found.values()
                                                           if p.kind == "TILE"})
        return cache[1].get((map_name, tx, ty), "")

    def place(self, name):
        name = trim(name)
        if not name or "," in name or " " in name or name[:1] in "$-+=0123456789":
            return None
        return self.places().get(name.upper())

    def quest_table(self):
        """[(name, {KEY: value})] of every quest, in file order."""
        path = self.data_file("Quests.ini")
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            return []
        cache = self._caches.get("quest_table")
        if cache is None or cache[0] != stamp:
            table = [(name, {k.upper(): trim(v) for k, v in items}) for name, items in ini.sections(path)]
            cache = self._caches["quest_table"] = (stamp, table)
        return cache[1]

    def quest_named(self, name_or_attr):
        want = trim(name_or_attr).lower()
        for name, d in self.quest_table():
            if name.lower() == want or d.get("ATTRIBUTE", "").lower() == want:
                return name, d
        return None, None

    def quest_of_attribute(self, attr):
        want = trim(attr).lower()
        for name, d in self.quest_table():
            if d.get("ATTRIBUTE", "").lower() == want:
                return name, d
        return None, None
