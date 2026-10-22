"""Saves\\<Name>.ini (the same format the Liberty BASIC game wrote, so old saves load), sounds, music and the background
sounds."""
import math
import os

import pygame

from . import ini
from .lb import val, word, trim, lbstr


class SaveMixin:
    # =================================================================================================================
    # Saves
    # =================================================================================================================
    def list_saves(self):
        try:
            files = sorted(os.listdir(os.path.join(self.root, "Saves")), key=str.lower)
        except OSError:
            return []
        return [f[:-4] for f in files if f.lower().endswith(".ini") and f[:-4].upper() != "TEMPLATE"]

    @staticmethod
    def clean_player_name(entered):
        ok = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 _-"
        name = trim("".join(c for c in entered if c in ok))[:20]
        if name.upper() == "TEMPLATE":
            return ""
        return name

    def load_player(self):
        path = os.path.join(self.root, "Saves", self.player_name + ".ini")
        new_player = False
        if not os.path.exists(path):
            new_player = True
            path = os.path.join(self.root, "Saves", "TEMPLATE.ini")
            if not os.path.exists(path):
                self.log("WARNING - Saves\\TEMPLATE.ini not found, using defaults for the new player")
                path = ""
        self.load_player_data(path, new_player)
        if not self.map_exists(self.screen_name):
            self.log("ERROR - Saved map '%s' not found, using the start map" % self.screen_name)
            self.screen_name = self.start_map
            self.player.x, self.player.y = self.start_x, self.start_y
        if not self.map_exists(self.screen_name):
            self.screen_name = self.first_map()
        self.init_entity(self.player, self.player.x, self.player.y)
        self.load_player_inventory(path)
        self.check_saved_equipment(path)
        self.recalc_equipment()
        self.draw_skills()
        if new_player:
            self.display_message("A new adventure begins!", "ACHIEVEMENT")

    def load_player_data(self, path, new_player):
        p = self.player
        self.screen_name = self.start_map
        p.x, p.y = self.start_x, self.start_y
        p.hp = self.player_max_hp
        p.direction = 4
        self.player_sprite_base = "Player"
        p.name = "Player"
        self.skill_xp = [0.0] * (self.total_skills + 1)
        self.attributes = []
        self.quest_notes = []
        self.npc_attitudes = {}
        self.taken_once = set()
        self.grave_reset()
        self.hotbar_reset()
        self.status = {}
        self.default_hitpoints_level()
        self.update_max_hp()
        p.hp = self.player_max_hp
        self.clear_boosts()
        self.player_last_cast = 0
        self.low_hp_warned = 0
        self.bank_item = [""] * (self.bank_slots + 2)
        self.bank_qty = [0] * (self.bank_slots + 2)
        self.bank_wear = [[] for _ in range(self.bank_slots + 2)]
        self.equip_wear = [0] * 12
        self.equipped = [""] * (self.equip_slots + 1)
        self.explored_maps = []
        self.explored_cells = {}
        self.explored_all = set()
        self.action_queue = []
        if not path:
            return
        self.log("Loading player from " + path)
        r = lambda s, k, d: ini.read(s, k, d, path)
        self.screen_name = r("Player", "Map", self.start_map).replace(" ", "")
        p.x = val(r("Player", "X", lbstr(self.start_x)))
        p.y = val(r("Player", "Y", lbstr(self.start_y)))
        self.player_mana = val(r("Player", "Mana", "-1"))
        self.mana_shown = -1
        self.cooldowns = {}
        hp = val(r("Player", "Hitpoints", "0"))
        p.direction = max(1, int(val(r("Player", "Direction", "4"))))
        tod = r("Player", "Time", "")
        if tod:
            self.set_day_fraction(val(tod))     # (the time of day where you left off)
        sprite = r("Player", "Sprite", "Player")
        if self.assets.loaded(sprite) or self.animation_available(sprite) > 0:
            self.player_sprite_base = sprite
        p.name = self.player_sprite_base
        for i in range(1, self.total_skills + 1):
            self.skill_xp[i] = min(self.skill_max_level, max(0, val(r("Skills", self.skill_name[i], "0"))))
        self.default_hitpoints_level()
        self.update_max_hp()
        if hp <= 0 or hp > self.player_max_hp:
            hp = self.player_max_hp
        p.hp = hp
        for k, v in ini.section("Attributes", path)[:500]:
            self.attributes.append([k, v])
        for k, v in ini.section("Quest.Notes", path)[:400]:          # NoteN=<quest>|<0 or 1 = crossed out>|<text>
            parts = v.split("|", 2)
            if len(parts) == 3 and trim(parts[0]) and trim(parts[2]):
                self.quest_notes.append([trim(parts[0]), 1 if val(parts[1]) else 0, trim(parts[2])])
        self.grave_load(ini.section("Grave", path))                   # where you last died, and what's there
        self.hotbar_load(ini.section("Hotbar", path))
        for k, v in ini.section("Taken.Once", path)[:2000]:          # ItemN=<Id, or map@x,y>: one-time items taken
            if trim(v):
                self.taken_once.add(trim(v))
        for k, v in ini.section("NPC.Attitudes", path)[:400]:        # <Id, or map@x,y>=Good or Bad: one NPC each
            if trim(k) and trim(v).capitalize() in ("Good", "Bad"):
                self.npc_attitudes[trim(k)] = trim(v).capitalize()
        for i in range(1, self.equip_slots + 1):                     # <Slot>=<item>[,<wear>]
            name, wear = self.split_wear(r("Equipment", self.equip_slot_names[i], ""))
            self.equipped[i] = self.renamed(name)
            self.equip_wear[i] = wear
        for i in range(1, self.bank_slots + 1):
            slot = r("Bank", "Slot%d" % i, "")
            if slot:
                self.bank_item[i] = self.renamed(trim(word(slot, 1, ",")))
                self.bank_qty[i] = max(1, val(word(slot, 2, ",")))
                wears = trim(word(slot, 3, ","))                     # (each one's wear: 15;0;3)
                self.bank_wear[i] = [int(val(w)) for w in wears.split(";") if trim(w)] if wears else []
        explored = ini.section("Explored", path)
        grid = "5x5"
        for k, v in explored:
            if k.upper() == "GRID":
                grid = v
        self.explored_grid_x = max(1, val(word(grid, 1, "x")))
        self.explored_grid_y = max(1, val(word(grid, 2, "x")))
        maps = r("Explored", "Maps", "")
        for m in maps.split():
            self.add_explored_map(m)
            cells = ""
            for k, v in explored:
                if k == m:
                    cells = v
            if cells == "":
                self.explored_all.add(m)
            else:
                self.load_explored_cells(m, cells)
        if new_player:
            return
        total = val(r("Action.Queue", "Total", "0"))
        for i in range(1, min(int(total), 300) + 1):
            entry = r("Action.Queue", "Entry%d" % i, "").replace("[TAB]", "\t")
            if entry:
                self.action_queue.append(entry)

    def load_explored_cells(self, name, cells):
        """Cell numbers are row-major on the save's Grid (default 5x5); converted to this fog grid."""
        step_x = max(1, self.fog_w - self.fog_border * 2)
        step_y = max(1, self.fog_h - self.fog_border * 2)
        gx, gy = self.explored_grid_x, self.explored_grid_y
        same = gx == self.fog_xt and gy == self.fog_yt
        found = self.explored_cells.setdefault(name, set())
        for c in cells.split():
            cell = int(val(c))
            if cell < 1:
                continue
            ox = ((cell - 1) % gx) + 1
            oy = int((cell - 1) / gx) + 1
            if same:
                found.add((ox, oy))
                continue
            # A save from another grid: every cell of this grid whose centre is inside the saved cell
            left = (ox - 1) * self.sw / gx
            right = ox * self.sw / gx
            top = (oy - 1) * self.sh / gy
            bottom = oy * self.sh / gy
            fx1 = max(1, int((left - self.fog_x_offset) / step_x))
            fx2 = min(self.fog_xt, int((right - self.fog_x_offset) / step_x) + 1)
            fy1 = max(1, int(top / step_y))
            fy2 = min(self.fog_yt, int(bottom / step_y) + 1)
            for fy in range(fy1, fy2 + 1):
                for fx in range(fx1, fx2 + 1):
                    cx = (fx - 0.5) * step_x + self.fog_x_offset
                    cy = (fy - 0.5) * step_y
                    if left <= cx < right and top <= cy < bottom:
                        found.add((fx, fy))

    def explored_cells_of(self, name):
        cells = sorted(((fy - 1) * self.fog_xt + fx) for (fx, fy) in self.explored_cells.get(name, ())
                       if 1 <= fx <= self.fog_xt and 1 <= fy <= self.fog_yt)
        return " ".join(str(c) for c in cells)

    # Items renamed since a save was made: old name -> new name (inventory, bank and equipment)
    ITEM_RENAMES = {"Key": "Beggars_House_Key"}

    def renamed(self, item):
        return self.ITEM_RENAMES.get(item, item)

    def load_player_inventory(self, path):
        if not path:
            return
        for i in range(1, self.inventory_capacity() + 1):
            slot = ini.read("Inventory", "Slot%d" % i, "", path)
            if slot:                                                 # SlotN=<item>,<how many>[,<wear>]
                self.add_inventory_item(self.renamed(trim(word(slot, 1, ","))), max(1, val(word(slot, 2, ","))),
                                        int(val(word(slot, 3, ","))) if word(slot, 3, ",") else 0)

    def save_player(self):
        if not self.player_name:
            return
        folder = os.path.join(self.root, "Saves")
        os.makedirs(folder, exist_ok=True)
        p = self.player
        out = ["; Dragon Sword save game (written by the game)", "", "[Player]",
               "Name=" + self.player_name, "Map=" + self.screen_name, "X=%d" % int(p.x), "Y=%d" % int(p.y),
               "Time=%.4f" % self.day_fraction(),
               "Hitpoints=" + lbstr(p.hp), "Mana=%d" % int(self.player_mana),
               "Direction=%d" % max(1, int(p.direction)), "Sprite=" + self.player_sprite_base, "", "[Skills]"]
        for i in range(1, self.total_skills + 1):
            out.append("%s=%s" % (self.skill_name[i], lbstr(self.skill_xp[i])))
        out += ["", "[Inventory]"]
        for n, e in enumerate(self.inv, 1):
            wear = getattr(e, "wear", 0)
            out.append("Slot%d=%s,%d" % (n, e.name, e.quantity) + (",%d" % wear if wear else ""))
        out += ["", "[Equipment]"]
        for i in range(1, self.equip_slots + 1):
            if self.equipped[i]:
                out.append("%s=%s" % (self.equip_slot_names[i], self.equipped[i]) +
                           (",%d" % self.equip_wear[i] if self.equip_wear[i] else ""))
        out += ["", "[Bank]"]
        slot = 0
        for i in range(1, self.bank_slots + 1):
            if self.bank_item[i]:
                slot += 1
                wears = self.bank_wear[i][:self.bank_qty[i]]
                out.append("Slot%d=%s,%s" % (slot, self.bank_item[i], lbstr(self.bank_qty[i])) +
                           ("," + ";".join(str(w) for w in wears) if any(wears) else ""))
        out += ["", "[Attributes]"]
        for n, v in self.attributes:
            out.append("%s=%s" % (n, v))
        out += ["", "[NPC.Attitudes]"]
        for key, v in sorted(self.npc_attitudes.items()):
            out.append("%s=%s" % (key, v))
        out += ["", "[Taken.Once]"]
        for i, key in enumerate(sorted(self.taken_once), 1):
            out.append("Item%d=%s" % (i, key))
        out += self.grave_save_lines() + self.hotbar_save_lines()
        out += ["", "[Quest.Notes]"]
        for i, (quest, done, text) in enumerate(self.quest_notes, 1):
            out.append("Note%d=%s|%d|%s" % (i, quest, done, text))
        out += ["", "[Explored]", "Grid=%dx%d" % (self.fog_xt, self.fog_yt), "Maps=" + " ".join(self.explored_maps)]
        for m in self.explored_maps:
            if m not in self.explored_all:
                cells = self.explored_cells_of(m)
                if cells:
                    out.append("%s=%s" % (m, cells))
        out += ["", "[Action.Queue]", "Total=%d" % len(self.action_queue)]
        for i, entry in enumerate(self.action_queue, 1):
            out.append("Entry%d=%s" % (i, entry.replace("\t", "[TAB]")))
        path = os.path.join(folder, self.player_name + ".ini")
        with open(path, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
            f.write("\n".join(out) + "\n")
        ini.forget(path)
        if self.main_setup_complete:
            self.save_snapshot()                     # Saves\<Name>.png, the character select's backdrop
        self.log("Saved player " + self.player_name)

    # =================================================================================================================
    # Sounds and music
    # =================================================================================================================
    def sound_path(self, name):
        name = trim(name)
        if "." not in name:
            if os.path.exists(os.path.join(self.root, "Sounds", name + ".wav")) or \
                    not os.path.exists(os.path.join(self.root, "Sounds", name + ".mid")):
                name += ".wav"
            else:
                name += ".mid"
        return name, os.path.join(self.root, "Sounds", name)

    def sound_place(self, at):
        """(left, right) volume for a sound made at world point at: quieter further from the player and louder on
        the side it comes from. None = all of it in both ears."""
        if at is None:
            return None
        dx = at[0] - self.player.cx
        d = math.hypot(dx, at[1] - self.player.cy)
        near, far = 96.0, 600.0
        f = 1.0 if d <= near else max(0.0, 1 - (d - near) / (far - near))
        pan = max(-1.0, min(1.0, dx / 400.0))
        return f * min(1.0, 1 - pan * 0.7), f * min(1.0, 1 + pan * 0.7)

    def play_sound(self, sound, at=None):
        """A sound effect. at = the world point it is made at (it gets quieter with distance and pans), or None."""
        if not self.sounds_enabled or not self.audio_ok or trim(sound) == "":
            return
        place = self.sound_place(at)
        if place is not None and max(place) < 0.03:
            return
        name, path = self.sound_path(sound)
        if not os.path.exists(path):
            self.log_missing("Sound", name)
            return
        if name.lower().endswith(".mid"):
            # A midi sound replaces the music for as long as it plays (check_music starts the music again, from
            # where it was)
            try:
                pos = self.music_position()
                if pos and not self.midi_effect:
                    self.__dict__.setdefault("music_resume", {})[self.music_theme_now] = pos
                self.music_fade = None
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.sound_volume / 100)
                pygame.mixer.music.play()
                self.midi_effect = True
            except Exception:
                self.log_missing("Sound", name)
            return
        s = self.assets.sound(path)
        if s is not None:
            s.set_volume(self.sound_volume / 100)
            ch = pygame.mixer.find_channel(True)
            if ch is None or ch is self.ambient_channel:
                ch = s.play()
            else:
                ch.play(s)
            if ch is not None:
                if place is None:
                    ch.set_volume(1.0, 1.0)
                else:
                    ch.set_volume(*place)

    INDOORS_KEEP = ("Palace", "Lair")      # (music by place: places whose own music plays inside their buildings too)
    MUSIC_FADE_OUT = 1100                  # ms: the music fades out this long before the next starts...
    MUSIC_FADE_IN = 1600                   # ...and fades in over this

    def music_theme(self):
        """The music for where the player is. "" = Config [Sounds] Music (the game's own tune), everywhere outside;
        Hearth inside a building (under a roof). With Config [Sounds] Music.By.Place=1, each map's theme from
        Data\\Music.ini [Maps] instead of the one tune outside."""
        if getattr(self, "music_override", None):            # (the login and loading screens: Title)
            return self.music_override
        theme = ""
        if self.config_read("Sounds", "Music.By.Place", "0") == "1":
            theme = trim(ini.read("Maps", self.screen_name, "", os.path.join(self.root, "Data", "Music.ini")))
        if getattr(self, "under_roof_group", 0) and theme not in self.INDOORS_KEEP:
            return "Hearth"
        return theme

    def music_files(self, theme):
        files = [trim(f) for f in ini.read("Themes", theme, "", os.path.join(self.root, "Data", "Music.ini")).split(",")
                 if trim(f)] if theme else []
        return files or ([self.music_file] if self.music_file else [])

    def start_music(self, fade_in=False):
        """Plays the music for where the player is: carrying on where that tune left off if it was playing before
        (going back outside after a house), else the next of its theme's tracks from the start."""
        self.music_playing = False
        self.music_want = None
        if not self.sounds_enabled or not self.music_enabled or not self.audio_ok:
            return
        theme = self.music_theme()
        files = self.music_files(theme)
        self.music_theme_now = theme
        if not files:
            return
        resume = self.__dict__.setdefault("music_resume", {}).pop(theme, None)     # (file, ms into it)
        if resume and resume[0] in files:
            name, offset = resume
        else:
            turns = self.__dict__.setdefault("music_turns", {})
            n = turns.get(theme, 0)
            turns[theme] = n + 1
            name, offset = files[n % len(files)], 0
        path = os.path.join(self.root, "Sounds", name)
        if not os.path.exists(path):
            self.log_missing("Music", name)
            return
        play = path
        if offset > 0 and name.lower().endswith(".mid"):
            play = self.music_from(path, offset)
            if play is None:
                play, offset = path, 0
        try:
            pygame.mixer.music.load(play)
            pygame.mixer.music.set_volume(0 if fade_in else self.music_level())
            pygame.mixer.music.play(0)                      # (when it ends, music_tick starts it again)
            self.music_playing = True
            self.music_now = (name, offset, self.clock())
            self.music_fade = {"stage": "in", "t0": self.clock()} if fade_in else None
        except Exception as ex:
            self.log("WARNING - The music %s didn't play (%s)" % (name, ex))

    def music_from(self, path, offset):
        """A copy of the MIDI file path starting offset ms in (pygame can't seek in MIDI), in the temp folder."""
        from . import midi
        m = midi.load(path)
        if m is None or m.length_ms <= 0 or offset >= m.length_ms - 2000:
            return None
        import tempfile
        self.music_copy_n = 1 - getattr(self, "music_copy_n", 0)          # (two names: the one playing stays loaded)
        out = os.path.join(tempfile.gettempdir(), "dragonsword_music%d.mid" % self.music_copy_n)
        try:
            with open(out, "wb") as f:
                f.write(m.from_ms(offset))
        except OSError:
            return None
        return out

    def music_position(self):
        """(file, ms into it) of the music playing now, or None."""
        now = getattr(self, "music_now", None)
        if not now or not self.music_playing:
            return None
        name, offset, started = now
        return name, offset + max(0, self.clock() - started)

    def change_music(self):
        """Fade the music out, then (music_tick) in with the music for where the player is now. The tune that was
        playing is remembered, to carry on with when its place's music is wanted again."""
        pos = self.music_position()
        if pos:
            self.__dict__.setdefault("music_resume", {})[self.music_theme_now] = pos
        self.music_fade = {"stage": "out", "t0": self.clock()}

    def music_tick(self):
        """Every frame: the fades, and a tune that has ended starting again."""
        if not self.audio_ok or self.midi_effect:
            return
        fade = getattr(self, "music_fade", None)
        now = self.clock()
        if fade:
            t = now - fade["t0"]
            if t < 0:
                fade["t0"], t = now, 0
            if fade["stage"] == "out":
                if t < self.MUSIC_FADE_OUT and self.music_playing:
                    pygame.mixer.music.set_volume(self.music_level() * (1 - t / float(self.MUSIC_FADE_OUT)))
                    return
                pygame.mixer.music.stop()
                self.start_music(fade_in=True)
                return
            if t < self.MUSIC_FADE_IN:
                pygame.mixer.music.set_volume(self.music_level() * t / float(self.MUSIC_FADE_IN))
                return
            pygame.mixer.music.set_volume(self.music_level())
            self.music_fade = None
        if self.music_playing and not pygame.mixer.music.get_busy():
            self.start_music()                          # (the tune ended: from the top, or the theme's next)

    def start_title_music(self):
        """The title music (Data\\Music.ini [Themes] Title) for the login and loading screens."""
        self.music_override = "Title"
        self.start_music()

    def end_title_music(self):
        """Into the game: the music for where the player is from now on (faded in by the caller's start_music)."""
        if getattr(self, "music_override", None):
            self.music_override = None
            self.stop_music()

    def title_music_tick(self):
        """On the login screen: when one title piece ends, the other plays."""
        self.music_tick()

    def check_music(self):
        """A few times a second: a MIDI sound effect done (the music back), and the music for where the player is
        changing (in or out of a building, or, by place, a new theme) after a moment there (so a doorway or a border
        walked along doesn't flip it back and forth): faded across."""
        if not self.audio_ok:
            return
        if self.midi_effect:
            if not pygame.mixer.music.get_busy():
                self.midi_effect = False
                self.start_music(fade_in=True)
            return
        if not self.music_playing or getattr(self, "music_fade", None):
            return
        want = self.music_theme()
        if want != getattr(self, "music_theme_now", want):
            now = self.clock()
            if getattr(self, "music_want", None) != want:
                self.music_want, self.music_want_at = want, now
            elif now - self.music_want_at >= (300 if "Hearth" in (want, self.music_theme_now) else 2500) \
                    or now < self.music_want_at:
                self.music_want = None
                self.change_music()
            return
        self.music_want = None

    def stop_music(self):
        if not self.audio_ok:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.music_playing = False
        self.midi_effect = False
        self.music_fade = None

    def music_level(self):
        """0-1: the music's volume (Options: Volume x Music volume)."""
        return self.sound_volume / 100 * self.music_volume / 100

    def apply_volume(self):
        if not self.audio_ok:
            return
        try:
            pygame.mixer.music.set_volume(self.music_level())
        except Exception:
            pass
        self.ambient_set_volume()

    def ambient_update(self):
        """Starts, changes or stops the background sound for the map the player is on (Data\\Ambient.ini)."""
        want = ""
        if self.sounds_enabled and self.ambient_enabled:
            if self.screen_name != self.ambient_map:
                self.ambient_map = self.screen_name
                self.ambient_want = trim(ini.read("Maps", self.screen_name, "",
                                                  os.path.join(self.root, "Data", "Ambient.ini")))
            want = self.ambient_want
            if getattr(self, "under_roof_group", 0) and want not in ("Cave", "Lair"):
                want = "Indoors"            # inside a building: the hearth crackling, not the weather outside
            want = self.weather_ambient(want)   # (the rain, outside while it rains)
        if want == self.ambient_current:
            return
        self.ambient_stop()
        if want == "":
            return
        path = os.path.join(self.root, "Sounds", "Ambient_" + want + ".wav")
        self.ambient_current = want
        if not os.path.exists(path):
            self.log_missing("Sound", "Ambient_" + want)
            return
        s = self.assets.sound(path)
        if s is None or self.ambient_channel is None:
            self.log("WARNING - Background sound %s didn't open" % want)
            return
        self.ambient_level = self.ambient_target = self.ambient_nearness()  # Starts at the right volume
        self.ambient_channel.play(s, loops=-1)
        self.ambient_set_volume()

    def ambient_stop(self):
        if self.ambient_current and self.ambient_channel is not None:
            self.ambient_channel.stop()
        self.ambient_current = ""

    def ambient_set_volume(self):
        if self.ambient_current and self.ambient_channel is not None:
            # Volume x Background volume, under the effects and the music (0.25 at full)
            self.ambient_channel.set_volume(self.sound_volume / 100 * self.ambient_volume / 100 * 0.25 *
                                            self.ambient_level)

    # Background sounds that belong to a kind of tile are only heard near it (none now: the sea is quiet)
    NEAR_TILES = {}

    def ambient_nearness(self):
        """0 to 1: how close the player is to what makes the background sound (1 = right by it). Sounds without
        tiles of their own (forest, wind, cave...) are heard everywhere on their maps."""
        kinds = self.NEAR_TILES.get(self.ambient_current)
        if not kinds:
            return 1.0
        p = self.player
        wx = int((p.cx + self.sw) / self.tw) + 1
        wy = int((p.cy + self.sh) / self.th) + 1
        radius, count, nearest = 10, 0, 99.0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                f = self.w_find(wx + dx, wy + dy)
                if f is None:
                    continue
                name = f[0].tile[f[1]]
                if name and any(k in name for k in kinds):
                    count += 1
                    nearest = min(nearest, math.hypot(dx, dy))
        if count < 12:  # A pond or a stream is no sea
            return 0.0
        return max(0.0, min(1.0, 1 - (nearest - 2) / 8))

    def ambient_tick(self):
        """Every loop: the background sound's volume follows how near its source is (checked 4 times a second)."""
        if not self.ambient_current or self.ambient_channel is None:
            return
        now = self.loop_start
        if now - self.ambient_checked >= 250 or now < self.ambient_checked:
            self.ambient_checked = now
            self.ambient_target = self.ambient_nearness()
        if self.ambient_level != self.ambient_target:  # Fades over a second or so as you walk
            level = self.ambient_level + (self.ambient_target - self.ambient_level) * min(1.0, self.loop_delta * 2)
            if abs(level - self.ambient_target) < 0.01:
                level = self.ambient_target
            self.ambient_level = level
            self.ambient_set_volume()
