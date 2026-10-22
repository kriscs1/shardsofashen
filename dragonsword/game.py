"""DRAGON SWORD - the game engine, in Python (pygame). A port of Dragon Sword.bas (Liberty BASIC 4.04).
File formats: Dev\\Data Formats.md. Script language: dragonsword\\script_language.py (Dev\\Script Commands.txt).

The game state lives on one Game object; its routines are grouped in the mixins (world, entities, npc, combat, script,
interact, ui, screens, save), each named after the parts of the original program."""
import datetime
import math
import os
import random
import sys
import time
import traceback

import pygame

from . import ini
from .assets import Assets
from .combat import CombatMixin
from .cursor import Cursors, kind_of_verb
from .entities import EntityMixin
from .extras import ExtrasMixin
from .anim import AnimMixin
from .daynight import DayNightMixin
from .weather import WeatherMixin
from .durability import DurabilityMixin
from .entity import (Entity, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, TYPE_NAMES,
                     DEFAULT_LIMITS)
from .interact import InteractMixin
from .lb import val, word, trim, lbstr, clock_ms, frame_ms
from .npc import NPCMixin
from .places import PlacesMixin
from .quests import QuestMixin
from .save import SaveMixin
from .screens import ScreensMixin
from .script import ScriptMixin
from .ui import UIMixin
from .world import WorldMixin


class QuitGame(Exception):
    pass


class Game(WorldMixin, EntityMixin, NPCMixin, CombatMixin, ScriptMixin, InteractMixin, UIMixin, ScreensMixin,
           SaveMixin, ExtrasMixin, AnimMixin, DayNightMixin, WeatherMixin, DurabilityMixin, QuestMixin, PlacesMixin):
    def __init__(self, root):
        self.root = root
        self.config_path = os.path.join(root, "Data", "Config.ini")
        self.logging_enabled = val(ini.read("Debugging", "Logging.Enabled", "1", self.config_path))
        self.debug_mode = 0
        self.main_setup_complete = False
        self.presenter = None               # shows frames, with the menus at the screen's resolution (sharp.py)
        self.sharp_layers = []
        self.logged_missing = set()
        self.log_ready = False
        self.error_sub = ""
        self.error_location = ""
        self.assets = Assets(root, self.log_missing)
        self.rand = random.random

    # =================================================================================================================
    # Logging and data files
    # =================================================================================================================
    def log(self, text):
        if self.logging_enabled != 1:
            return
        if self.main_setup_complete and self.debug_mode:
            self.display_message(text, "LOG")
        folder = os.path.join(self.root, "Dev")
        if not self.log_ready:
            os.makedirs(folder, exist_ok=True)
            self.log_ready = True
        if text != "":
            text = datetime.datetime.now().strftime("%H:%M:%S") + " " + text
        try:
            with open(os.path.join(folder, "Log.txt"), "a", encoding="cp1252", errors="replace") as f:
                f.write(text + "\n")
        except OSError:
            pass

    def log_missing(self, what, name):
        key = (what, name)
        if key in self.logged_missing:
            return
        self.logged_missing.add(key)
        self.log("ERROR - %s '%s' not found" % (what, name))

    def config_read(self, section, key, default):
        return ini.read(section, key, default, self.config_path)

    def tile_ini(self, section, key, default):
        return ini.read(section, key, default, os.path.join(self.root, "Data", "Tiles.ini"))

    def entity_ini(self, section, key, default):
        """Entities.ini [section] key. A decor tile placed as an object (it has no Entities.ini section of its own)
        reads its Tiles.ini section instead: its verbs, its examine text, its footprint, its light."""
        if self.is_decor_object(section):
            return self.tile_ini(section, key, default)
        return ini.read(section, key, default, os.path.join(self.root, "Data", "Entities.ini"))

    def is_decor_object(self, name):
        """A decor tile (Tiles.ini Layer=Decor) used as an entity: no Entities.ini section, so its data is the tile's."""
        cache = self.__dict__.setdefault("decor_object_cache", {})
        if name not in cache:
            cache[name] = bool(name) and self.is_decor_tile(name) and not ini.section(
                name, os.path.join(self.root, "Data", "Entities.ini"))
        return cache[name]

    @staticmethod
    def clock():
        return clock_ms()

    @staticmethod
    def frame_clock():
        return frame_ms()

    # =================================================================================================================
    # Settings ([Get.Variables] of the original)
    # =================================================================================================================
    def set_admin(self):
        """The Admin button (and god mode) for the characters named in Config [Admin] Players, no one else."""
        self.admin_enabled = self.player_name.strip().lower() in self.admin_players
        self.god_mode = val(ini.read("Admin", "GodMode", "0", self.config_path)) if self.admin_enabled else 0

    def get_variables(self):
        c = self.config_read
        self.logging_enabled = val(c("Debugging", "Logging.Enabled", "1"))
        self.debug_mode = val(c("Debugging", "Debug", "0"))
        self.log("")
        self.log("----------------- %s -----------------" % datetime.date.today().strftime("%b %d, %Y"))
        self.log("")
        self.log("Starting [Get.Variables]")
        self.fullscreen = val(c("Debugging", "Fullscreen", "1"))
        self.xt = val(c("Interface", "Map.X.Tiles", "25"))
        self.yt = val(c("Interface", "Map.Y.Tiles", "21"))
        if self.xt < 1 or self.xt > 50:
            self.xt = 25
        if self.yt < 1 or self.yt > 50:
            self.yt = 21
        a = self.assets
        self.tw = a.width("Black001")
        self.th = a.height("Black001")
        allw = "1" * 49
        self.walk_res = int(math.sqrt(len(self.tile_ini("Black001", "Walkable.Data", allw))) + 0.5)
        if self.walk_res < 1:
            self.walk_res = 7
        self.all_walkable = "1" * (self.walk_res ** 2)
        self.sw = self.tw * self.xt
        self.sh = self.th * self.yt
        # Fog of war: square cells of FogOfWar.Cell.Size pixels (they should divide the map's width and height so
        # the cells line up at the seams). Drawn by the program, so no FogOfWar/BlackOfWar pictures are needed
        cell = int(val(c("Interface", "FogOfWar.Cell.Size", "16")))
        cell = max(4, min(128, cell))
        self.fog_w = self.fog_h = cell
        self.fog_border = 0
        self.fog_smooth = val(c("Interface", "FogOfWar.Smooth", "1")) == 1
        self.fog_seen_alpha = min(255, max(0, val(c("Interface", "FogOfWar.Seen.Darkness", "130"))))
        self.fog_xt = int((self.sw + cell - 1) / cell)
        self.fog_yt = int((self.sh + cell - 1) / cell)
        self.fog_x_offset = 0
        if self.fog_xt * cell != self.sw or self.fog_yt * cell != self.sh:
            self.log("WARNING - FogOfWar.Cell.Size %d doesn't divide the map size: cells won't line up at map edges" % cell)
        # The screen: the playfield is as wide as the window allows (the sidebar and chat bar keep their size)
        self.view_w = self.win_w - 224
        self.view_h = 768 - 96
        self.ui_dx = self.win_w - 1024  # How far the right-hand interface moved from where the 1024 wide layout had it
        self.page_x = int((self.win_w - 1024) / 2)  # The 1024 x 768 pages (loading, character select, journal)
        # Playfield zoom (mouse wheel or + / -), the camera's easing and the light round the player at night
        self.zoom_levels = (0.75, 1.0, 1.5, 2.0, 3.0)
        zoom = val(c("Interface", "Zoom", "1"))
        self.zoom = min(self.zoom_levels, key=lambda z: abs(z - zoom))
        self.camera_smooth = val(c("Interface", "Camera.Smooth", "8"))
        self.night_light = max(0, val(c("Gameplay", "Night.Light.Radius", "130")))
        self.ab_x = int((self.view_w - a.width("AB_Conversation")) / 2)
        self.ab_y = int((self.view_h - (a.height("AB_Conversation") + a.picture_height("ResponseBox"))) / 2)
        self.ab_columns = min(9, max(1, val(c("Interface", "ActionBox.Columns", "9"))))
        self.ab_rows = min(3, max(1, val(c("Interface", "ActionBox.Rows", "3"))))
        self.rb_x = int((self.view_w - a.width("ResponseBox")) / 2)
        self.rb_y = self.ab_y + a.height("AB_Conversation")
        self.infobox_x = int((self.view_w - a.width("InfoBox")) / 2)
        self.infobox_y = int((self.view_h - a.picture_height("InfoBox")) / 2)
        self.statbar_y = 175
        self.inventory_columns = max(1, val(c("Interface", "InventoryItems.Columns", "5")))
        self.inventory_rows = max(1, val(c("Interface", "InventoryItems.Rows", "7")))
        self.inventory_x = self.view_w + 34
        self.inventory_y = 413
        self.inventory_gap = self.tw
        self.minimap_centre_x = self.view_w + 140
        self.minimap_centre_y = 84
        self.minimap_blackout = val(c("Minimap", "Blackout", "1"))
        self.npc_respawn_delay = val(c("Gameplay", "NPC.Respawn.Delay", c("Gameplay", "NPC.Repawn.Delay", "10")))
        self.shop_restock_delay = val(c("Gameplay", "Shop.Restock.Seconds", "300"))
        self.item_respawn_delay = val(c("Gameplay", "Item.Respawn.Delay", "600"))
        # shops pay Value x Sell.Rate x this for what you sell them (far less than they charge)
        self.sell_price_factor = val(c("Gameplay", "Sell.Price.Factor", "0.25"))
        self.autosave_ms = 60000 * val(c("Gameplay", "AutoSave.Minutes", "3"))
        self.item_despawn_delay = val(c("Gameplay", "Item.Despawn.Delay", "180"))
        self.bank_slots = min(500, max(1, val(c("Gameplay", "Maximum.Bank.Slots", "50"))))
        self.fog_enabled = val(c("Gameplay", "FogOfWar.Enabled", "0")) == 1
        self.fog_view_distance = val(c("Gameplay", "FogOfWar.Viewable.Distance", "200"))
        self.start_map = c("Gameplay", "Start.Map", "1,1,0").replace(" ", "")
        self.start_x = val(c("Gameplay", "Start.X", "300"))
        self.start_y = val(c("Gameplay", "Start.Y", "300"))
        if not self.map_exists(self.start_map):
            self.log("ERROR - Start.Map '%s' not found" % self.start_map)
            self.start_map = self.first_map()
        self.sounds_enabled = val(c("Sounds", "Enabled", "1"))
        self.music_file = c("Sounds", "Music", "")
        font = trim(c("Interface", "Font", "Palatino Linotype")).replace(" ", "_") or "Palatino_Linotype"
        self.ui_font = font
        self.assets.font_name = font.replace("_", " ")
        self.sound_volume = min(100, max(0, val(c("Sounds", "Volume", "100"))))
        self.music_volume = min(100, max(0, val(c("Sounds", "Music.Volume", "80"))))       # Options' sliders
        self.ambient_volume = min(100, max(0, val(c("Sounds", "Ambient.Volume", "70"))))
        self.music_enabled = val(c("Sounds", "Music.On", "1"))
        self.ambient_enabled = val(c("Sounds", "Ambient", "1"))
        self.day_night_enabled = val(c("Gameplay", "DayNight", "1"))
        self.day_seconds = 60 * val(c("Gameplay", "Day.Minutes", "24"))
        self.quest_markers_enabled = val(c("Gameplay", "QuestMarkers", "1"))
        self.user_input_enabled = True
        self.player_visible = val(c("Gameplay", "Player.Visible", "1")) == 1
        skills = c("Skills", "List", "Strength,Defence,Hitpoints,Cooking,Smithing,Fishing,Mining,Woodcutting")
        names = [trim(s) for s in skills.split(",") if s != ""][:30]
        self.total_skills = len(names)
        self.skill_name = [""] + names
        self.skill_xp = [0.0] * (self.total_skills + 1)
        self.skill_off = [0] * (self.total_skills + 1)
        self.read_disabled_skills()
        # Admin: only for the characters named in [Admin] Players (set once the character is chosen: set_admin)
        self.admin_players = [trim(n).lower() for n in c("Admin", "Players", "Admin").split(",") if trim(n)]
        self.admin_enabled = False
        self.god_mode = 0
        self.pathfinding_enabled = val(c("Gameplay", "Pathfinding", "1")) == 1
        self.grid_cell = max(4, int(min(self.tw, self.th) / 2))
        self.pf_player_budget = 2200
        self.pf_npc_budget = 400
        self.pf_max_searches = 1
        self.quests_per_page = 7
        self.quest_row_top = 58
        self.quest_row_height = 16
        self.quests_page = 1
        self.quests_pages = 1
        self.equip_slots = 8
        self.equip_slot_names = [""] + "Weapon Shield Head Body Legs Feet Hands Ring".split()
        self.gear_rank = [0, 7, 6, 5, 3, 1, 2, 4, 8]
        self.type_limits = {}
        for t, default in DEFAULT_LIMITS.items():
            self.type_limits[t] = max(1, val(c("Entities", "total.%s.IDs" % TYPE_NAMES[t], lbstr(default))))
        self.healthbars_available = True
        for i in range(0, 101, 10):
            if not a.loaded("%dPCHealth" % i):
                self.healthbars_available = False
                self.log_missing("Sprite", "%dPCHealth" % i)
        self.hp_base = max(0, val(c("Gameplay", "Hitpoints.Base", "19")))
        self.hp_per_level = max(0.0, val(c("Gameplay", "Hitpoints.Per.Level", "0.5")))
        self.hp_regen_delay = max(0, val(c("Gameplay", "HP.Regen.Delay", "6")))
        self.hp_regen_every = max(0.2, val(c("Gameplay", "HP.Regen.Every", "3")))
        self.skill_max_level = max(2, int(val(c("Gameplay", "Skill.Max.Level", "50"))))
        # combat and levelling (Config [Gameplay]: see the notes there)
        self.xp_slowdown = max(0.0, val(c("Gameplay", "XP.Slowdown", "10")))
        self.monster_damage = max(0.1, val(c("Gameplay", "Monster.Damage", "2")))
        self.death_gold_loss = min(100, max(0, val(c("Gameplay", "Death.Gold.Loss", "25"))))
        self.player_max_hp = int(self.hp_base + 2 * self.hp_per_level)
        p = Entity(PLAYER, "Player")
        p.attack_speed = max(0.1, val(c("Gameplay", "Player.Attack.Speed", "0.8")))
        p.move_speed = self.speed_to_pixels(val(c("Gameplay", "Player.Movement.Speed", "4")))
        p.hp = p.max_hp = self.player_max_hp
        self.player = p
        self.log("Completed [Get.Variables]")
        self.log("")

    def init_state(self):
        """Everything the game keeps track of while it runs, at its starting value."""
        self.world = []
        self.inv = []
        self.fx = []
        self.map_npcs = []
        self.walk_kinds = {}
        self.gear_kinds = {}
        self.icon_cache = {}
        self.screen_name = ""
        self.cam_x = self.cam_y = 0
        self.cam_fx = self.cam_fy = 0.0
        self.cam_snap = True
        self.cursor_x = self.cursor_y = 0
        self.cursor_world_x = self.cursor_world_y = 0
        self.cursor_kind = "pointer"       # the mouse cursor's picture (cursor.py): what a click will do
        self.cursors = Cursors()
        self.loop_start = self.clock()
        self.loop_delta = 0.0
        self.force_layer_update = True
        self.pending_map_change = False
        self.pending_map = ""
        self.pending_x = self.pending_y = 0
        self.seam_shift_x = self.seam_shift_y = 0
        self.player_walk_active = False
        self.player_walk_x = self.player_walk_y = 0
        self.player_walk_speed = 0
        self.player_walk_range = 0
        self.player_walk_stuck = 0
        self.player_walk_replans = 0
        self.pending_verb = ""
        self.pending_ent = None
        self.player_attack_target = None
        self.player_last_attack = 0
        self.player_last_combat = 0
        self.player_last_cast = 0
        self.player_moved = False
        self.player_prev_x = self.player_prev_y = 0
        self.player_entry_x = self.player_entry_y = 0
        self.player_tile_x = self.player_tile_y = 0
        self.player_sprite_base = "Player"
        self.player_name = ""
        self.player_mana = -1
        self.player_max_mana = 10
        self.mana_shown = -1
        self.cooldowns = {}
        self.hp_regen_last = 0
        self.low_hp_warned = 0
        self.ammo_warned = 0
        self.spell_fizzled = False
        self.npc_ranged_hit = False
        self.clear_boosts_values()
        self.keyboard_direction = 0
        self.item_in_use = None
        self.item_in_use_name = ""
        self.clicked_ent = None
        self.cursor_ent = None
        self.hover_tile = Entity(TILE, "")
        self.clicked_tile_x = self.clicked_tile_y = 1
        self.script_cursor_x = self.script_cursor_y = 0
        self.verb_from_menu = False
        self.lock_bumped = 0
        self.lock_bump_last = 0
        self.lock_bump_time = 0
        self.pf_searches = 0
        self.pf_steer_x = self.pf_steer_y = 0
        self.ai_player_fx = self.ai_player_fy = 0
        self.fog_last_x = self.fog_last_y = -99999
        self.fog_all_disabled = False
        self.explored_maps = []
        self.explored_cells = {}
        self.explored_all = set()
        self.fog_version = 0
        self.fog_overlay_key = None
        self.fog_overlay = None
        self.explored_grid_x = self.explored_grid_y = 5
        self.action_queue = []
        self.attributes = []
        self.bank_item = [""] * (self.bank_slots + 2)
        self.bank_qty = [0] * (self.bank_slots + 2)
        self.bank_wear = [[] for _ in range(self.bank_slots + 2)]     # the wear of each one in a bank slot
        self.equipped = [""] * (self.equip_slots + 1)
        self.equip_attack_total = self.equip_defence_total = self.equip_magic_total = 0
        self.equip_wear = [0] * 12                                      # each worn slot's wear (durability.py)
        # Scripts
        self.script_running = False
        self.script_name = ""
        self.script_lines = [""] * 101
        self.script_line_no = 0
        self.script_state = ""
        self.script_wait_until = 0
        self.script_result = 0
        self.script_cancel_line = 0
        self.script_move_ent = None
        self.script_queue = []
        self.script_vars = [""] * 10
        self.script_args = [""] * 16
        self.script_response_line = {}
        # ActionBox, racks, menus, chat
        self.ab_mode = ""
        self.ab_image = ""
        self.ab_title = ""
        self.ab_text = ""
        self.ab_item_defs = []
        self.ab_items = []
        self.ab_surface = None
        self.responses = []
        self.response_actions = []
        self.response_mouseover = 0
        self.rb_surface = None
        self.rb_highlight = -2
        self.rack_type = ""
        self.rack_name = ""
        self.rack = []
        self.rack_page = 1
        self.rack_buy_rate = 1.2
        self.rack_sell_rate = 0.8
        self.rack_specific = 0
        self.rack_skill = ""
        self.infobox_open = False
        self.infobox_surface = None
        self.rcm_open = False
        self.rcm_verbs = []
        self.rcm_labels = []
        self.rcm_target = None
        self.rcm_highlight = 0
        self.rcm_x = self.rcm_y = self.rcm_w = self.rcm_h = 0
        self.rcm_row_top = 6
        self.rcm_row_height = 18
        self.rcm_world_x = self.rcm_world_y = 0
        self.message_log = []
        self.chat_line = 1
        self.chat_dirty = True
        self.qm_message = None
        self.qm_lines = []
        self.qm_size = 9
        self.qm_colour = (0, 0, 0)
        self.qm_line_h = 13
        self.qm_y = 20
        self.option_selected = set()
        self.skill_mouseover = 0
        self.equip_mouseover = 0
        self.quest_mouseover = 0
        self.quest_arrow = 0
        self.stats_view = 0
        self.stats_dirty = True
        self.stat_rows = 1
        self.stat_row_top = 41
        self.stat_row_height = 0
        self.pick_list = []
        self.pick_world = []
        self.scroll_drag = ""
        self.rack_pages = 1
        self.help_button_hot = False
        self.admin_button_hot = False
        # Journal, dialogs, admin
        self.help_open = False
        self.help_tab = 1
        self.help_page = 1
        self.help_focus_quest = ""
        self.help_hover = 0
        self.help_dirty = True
        self.help_crafts = []
        self.help_craft_order = []
        self.help_craft_ready = 0
        self.help_gathers = []
        self.help_gather_order = []
        self.help_gather_ready = 0
        self.help_quests = []
        self.help_quest_order = []
        self.help_quest_active = self.help_quest_done = 0
        self.quest_notes = []               # [quest title, done 0/1, text]: the scripts' journal notes (Quest.Note)
        self.npc_attitudes = {}             # NPC (npc_key: its Id, or map@x,y) -> "Good" / "Bad": Set.NPC.Attitude, saved
        self.taken_once = set()             # one-time items picked up (Once=1): their Id, or map@x,y (saved: Taken.Once)
        self.quest_popup = None             # (key, surface): the checklist shown while a quest is pointed at
        self.help_hover_quest = -1          # the quest card under the mouse in the journal (index in help_quests)
        self.help_pen_x = 0
        self.help_line_right = 0
        self.help_line_full = False
        self.quit_dialog_open = False
        self.quit_confirmed = False
        self.quit_hover = 0
        self.quit_x = self.quit_y = 0
        self.options_open = False
        self.options_hover = 0
        self.options_x = self.options_y = 0
        self.admin_open = False
        self.admin_items = []
        self.admin_focus = ""
        self.loading_active = False
        self.loading_last_percent = -1
        self.loading_status = ""
        self.login_saves = []
        self.login_name = ""
        self.login_hover = 0
        self.login_note = ""
        # Minimap, day and night, sound
        self.minimap_available = False
        self.minimap_image = None
        self.minimap_pixel_size = 1
        self.minimap_zoom = 0
        self.minimap_origin_x = self.minimap_origin_y = 0
        self.minimap_last = ""
        self.minimap_built_key = ""
        self.minimap_view_size = 160
        self.minimap_view_pos = (0, 0)
        self.qmarks = []
        self.night_alpha = 0
        self.night_shown = 0
        self.day_start_ms = self.clock()
        self.music_playing = False
        self.midi_effect = False
        self.ambient_current = ""
        self.ambient_map = ""
        self.ambient_want = ""
        self.ambient_level = self.ambient_target = 1.0
        self.ambient_checked = 0
        self.last_auto_save = self.clock()
        self.last_queue_check = 0
        self.last_music_check = 0
        self.time_marks = []
        self.time_mark_last = 0
        self.ground_ready = False
        self.under_roof_group = None
        # Input
        self.keys_hit = set()
        self.keys_down = None
        self.text_events = []
        self.mouse_left_click = False
        self.mouse_right_click = False
        self.mouse_wheel = 0

    def clear_boosts_values(self):
        self.spell_defence_bonus = self.spell_defence_until = 0
        self.spell_attack_bonus = self.spell_attack_until = 0
        self.spell_magic_bonus = self.spell_magic_until = 0
        self.spell_sight_bonus = self.spell_sight_until = 0

    # =================================================================================================================
    # Starting
    # =================================================================================================================
    def main_setup(self):
        # Scaling the 768 high game up to the screen: smooth (linear) keeps text readable; 0 = sharp pixels (nearest)
        smooth = val(ini.read("Interface", "Smooth.Scaling", "1", self.config_path)) == 1
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "linear" if smooth else "nearest"
        os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = os.environ["SDL_RENDER_SCALE_QUALITY"]
        try:                # Windows: draw at the screen's real pixels, not stretched by the display scaling (blurry)
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
        pygame.mixer.pre_init(44100, -16, 2, 1024)
        pygame.init()
        self.audio_ok = pygame.mixer.get_init() is not None
        self.ambient_channel = None
        if self.audio_ok:
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.ambient_channel = pygame.mixer.Channel(0)
        full = val(ini.read("Debugging", "Fullscreen", "1", self.config_path)) == 1
        # The game is 768 pixels high and as wide as the display's shape needs (1024 on 4:3, 1366 on 16:9, at most
        # 1792 for 21:9), then scaled to fill the screen. [Interface] Widescreen=0 keeps the old 1024 x 768
        self.win_w = 1024
        if val(ini.read("Interface", "Widescreen", "1", self.config_path)) == 1:
            try:
                dw, dh = pygame.display.get_desktop_sizes()[0]
                self.win_w = max(1024, min(1792, int(768 * dw / max(1, dh) / 2 + 0.5) * 2))
            except Exception:
                pass
        flags = pygame.SCALED | (pygame.FULLSCREEN if full else 0)
        try:
            self.screen = pygame.display.set_mode((self.win_w, 768), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((self.win_w, 768))
        pygame.display.set_caption("Dragon Sword")
        from .sharp import Presenter
        self.presenter = Presenter(self.screen)
        self.log("Starting Load.Sprites (1)")
        for name in self.assets.folder_names("Interface"):
            self.assets.load_file("Interface", name)
        self.assets.load_file("Tiles", "Black001")
        icon = None
        if self.assets.load_if_exists("Entities", "Player4a"):
            icon = self.assets.get("Player4a").masked
        if icon is not None:
            pygame.display.set_icon(icon)
        self.get_variables()
        self.init_state()
        self.world_init_arrays()
        self.apply_zoom()
        self.chat_surface = pygame.Surface((self.win_w, 96)).convert()
        self.chat_bg = self.make_chat_background()
        self.stats_surface = pygame.Surface((224, 200)).convert()
        self.help_surface = pygame.Surface((1024, 768)).convert()
        self.page = pygame.Surface((1024, 768)).convert()
        self.page_backdrop = None                   # behind the page: the character select's blurred picture
        self.minimap_view = pygame.Surface((self.minimap_view_size, self.minimap_view_size)).convert()
        self.start_title_music()
        self.draw_loading_screen("Loading...")
        tiles = self.assets.folder_names("Tiles")
        for n, name in enumerate(tiles, 1):
            self.assets.load_file("Tiles", name)
            if n % 10 == 0:
                self.loading_progress(0.02 + 0.43 * n / max(1, len(tiles)), "Loading tiles...")
        ents = self.assets.folder_names("Entities")
        for n, name in enumerate(ents, 1):
            self.assets.load_file("Entities", name)
            if n % 10 == 0:
                self.loading_progress(0.45 + 0.45 * n / max(1, len(ents)), "Loading entities...")
        self.log("Completed Load.Sprites")
        self.log("")
        self.ground_init()
        self.hide_loading_screen()
        self.select_player()
        self.set_admin()
        self.draw_loading_screen("Loading %s..." % self.player_name)
        self.loading_progress(0.1, "Loading %s..." % self.player_name)
        self.load_player()
        self.loading_progress(0.2, "Loading the map...")
        self.change_screen()
        self.loading_progress(1, "Ready!")
        self.end_title_music()
        self.start_music(fade_in=True)
        self.apply_volume()
        self.quest_markers_refresh()
        self.day_start_ms = self.clock()
        self.night_shown = 0
        self.ambient_update()
        self.force_layer_update = True
        self.hide_loading_screen()
        self.main_setup_complete = True
        self.display_message("Welcome to Dragon Sword, %s!" % self.player_name, "INFORMATION")
        self.last_auto_save = self.clock()
        self.display_message("Press H (or F1) for your journal: what you can make and gather, quests and controls.",
                             "INFO")
        self.frame_last = self.frame_clock()
        self.camera_update()
        pygame.key.start_text_input()

    # =================================================================================================================
    # The game loop
    # =================================================================================================================
    def run(self):
        try:
            self.main_setup()
            self.pg_clock = pygame.time.Clock()
            while True:
                self.game_loop()
        except QuitGame:
            pass
        except Exception:
            self.error_handler()
        finally:
            pygame.quit()

    def read_input(self):
        self.keys_hit = set()
        self.text_events = []
        self.mouse_left_click = self.mouse_right_click = False
        self.mouse_wheel = 0
        focused = pygame.key.get_focused()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                if self.main_setup_complete:
                    self.quit_confirmed = True
                else:
                    self.quit_game(save=False)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    continue
                if ev.key == pygame.K_KP_ENTER:
                    self.keys_hit.add(pygame.K_RETURN)
                self.keys_hit.add(ev.key)
            elif ev.type == pygame.TEXTINPUT:
                self.text_events.append(ev.text)
            elif ev.type == pygame.MOUSEBUTTONDOWN and focused:
                if ev.button in (1, 3):
                    self.cursors.click(self.frame_clock())
                if ev.button == 1:
                    self.mouse_left_click = True
                elif ev.button == 3:
                    self.mouse_right_click = True
            elif ev.type == pygame.MOUSEWHEEL:
                self.mouse_wheel += ev.y
            elif ev.type == pygame.WINDOWFOCUSGAINED:
                self.mouse_left_click = self.mouse_right_click = False
        self.keys_down = pygame.key.get_pressed() if focused else None
        self.cursor_x, self.cursor_y = pygame.mouse.get_pos()
        return focused

    def game_loop(self):
        self.pg_clock.tick(60)
        self.loop_start = self.clock()
        self.music_tick()                   # (the music's fades, and a tune that ended starting again)
        if self.main_setup_complete and not getattr(self, "help_open", False):
            self.status_tick()                  # poison, burning... and the grave's time running out
            self.grave_tick(max(0, min(1000, self.loop_start - getattr(self, "grave_last_tick", self.loop_start))))
        self.grave_last_tick = self.loop_start
        if self.main_setup_complete:
            self.anim_tick()                    # the shore's foam and the flames (anim.py)
            self.weather_tick()                 # rain, snow, fog... (weather.py)
        now_f = self.frame_clock()
        self.loop_delta = max(0.0, min(0.1, (now_f - self.frame_last) / 1000))
        self.frame_last = now_f
        focused = self.read_input()
        self.cursor_kind = "pointer"
        if self.quit_confirmed:
            self.close_window()
        if self.quit_dialog_open or self.options_open:
            # The "Save and quit?" box or the Options screen: the world is paused until it closes
            if focused:
                if self.quit_dialog_open:
                    self.update_quit_dialog()
                else:
                    self.update_options_dialog()
            self.render()
            self.present_frame()
            return
        if getattr(self, "sleep_state", None):
            # Asleep (daynight.py): the world waits while the dark comes down, the time moves on, and it lifts
            self.sleep_tick()
            self.render()
            if self.sleep_state:
                self.draw_sleep(self.screen)
            self.present_frame()
            return
        if self.autosave_ms > 0 and self.main_setup_complete:
            if self.loop_start - self.last_auto_save >= self.autosave_ms or self.loop_start < self.last_auto_save:
                self.last_auto_save = self.loop_start
                if not self.script_running:
                    self.save_player()
                    self.display_message("Game saved.", "INFO")
        if self.help_open:
            # The journal: the world is paused until it closes
            if focused:
                self.help_update()
            if self.loop_start - self.last_music_check >= 1000 or self.loop_start < self.last_music_check:
                self.last_music_check = self.loop_start
                self.check_music()
            if self.help_open:
                if getattr(self.help_surface, "k", 1.0) != (self.presenter.k if self.presenter and self.presenter.active else 1.0):
                    self.help_dirty = True          # the window changed size (F11): draw it again at the new scale
                if self.help_dirty:
                    self.help_draw()
                self.screen.fill((24, 14, 10))
                self.show_layer(self.screen, self.help_surface, (self.page_x, 0))
            else:
                self.render()
            self.present_frame()
            return
        self.player_moved = False
        self.keyboard_direction = 0
        self.pf_searches = 0
        self.lock_bumped = 0
        if focused:
            used = self.admin_handle() if self.admin_open else False
            if used:
                self.mouse_left_click = False
            if self.admin_open and self.admin_focus:
                self.keys_down = None  # Typing in the admin panel doesn't walk the player
            self.error_location = "Detect.User.Keyboard.Input"
            self.detect_keyboard_input()
            self.error_location = "Detect.User.Mouse.Movement"
            self.detect_mouse_movement()
            self.error_location = "Detect.User.Mouse.Input"
            self.detect_mouse_input()
            self.update_scroll_drag()
        paused = bool(self.ab_mode)     # a conversation, shop, bank or crafting box is open: the world waits
        self.error_location = "Check.Object.Blocks"
        self.check_object_blocks()      # (objects' footprints on the walk grid, if one came, went or moved)
        self.error_location = "Move.Player"
        if not paused:
            self.move_player()
        if self.lock_bumped > 0:
            self.lock_bump(self.lock_bumped)
        self.error_location = "Check.Player.Tile"
        self.check_player_tile()
        self.error_location = "Check.if.Player.is.Off.Screen"
        self.check_player_off_screen()
        self.error_location = "Update.NPCs"
        if not paused:
            self.update_npcs()
        self.error_location = "Update.Script.Move"
        self.update_script_move()
        self.error_location = "Update.Player.Combat"
        if not paused:
            self.update_player_combat()
        self.error_location = "Fx.Update"
        self.fx_update()
        self.error_location = "Update.Player.Health"
        self.update_player_health()
        self.update_mana()
        self.update_healthbar(self.player)
        self.animate_entity(self.player, self.player_moved)
        if self.loop_start - self.last_queue_check >= 250 or self.loop_start < self.last_queue_check:
            self.last_queue_check = self.loop_start
            self.error_location = "Run.Action.Queue"
            self.run_action_queue()
        self.error_location = "Run.Scripts"
        self.run_scripts()
        if self.pending_map_change:
            self.error_location = "Do.Pending.Map.Change"
            self.do_pending_map_change()
        if self.fog_enabled:
            self.error_location = "Update.FogOfWar"
            self.update_fog_of_war()
        self.error_location = "Update.Roof.Tiles"
        self.update_roof_tiles()
        self.error_location = "Update.Doors"
        self.update_doors()
        self.error_location = "Update.Layers"
        for e in self.world:
            e.active = not self.entity_is_hidden(e)
        self.force_layer_update = False
        music_every = 250 if getattr(self, "music_want", None) else 1000      # (quicker while a change is coming)
        if self.loop_start - self.last_music_check >= music_every or self.loop_start < self.last_music_check:
            self.last_music_check = self.loop_start
            self.check_music()
            self.ambient_update()
            self.day_night_update()
        self.ambient_tick()
        self.camera_update()
        self.error_location = "Update.Minimap"
        self.update_minimap()
        self.error_location = "Draw"
        self.render()
        self.present_frame()

    # =================================================================================================================
    # Closing
    # =================================================================================================================
    def quit_game(self, save=True):
        if save and self.main_setup_complete:
            self.save_player()
        raise QuitGame()

    def close_window(self):
        if self.main_setup_complete:
            self.save_player()
        self.main_setup_complete = False
        self.stop_music()
        self.ambient_stop()
        self.log("END")
        raise QuitGame()

    def error_handler(self):
        info = traceback.format_exc()
        where = "Game step: %s | Routine: %s | Map %s, cursor %s,%s" % (
            getattr(self, "error_location", ""), getattr(self, "error_sub", ""), getattr(self, "screen_name", ""),
            getattr(self, "cursor_x", ""), getattr(self, "cursor_y", ""))
        self.log("!!UNHANDLED ERROR!! " + where + " | " + info.replace("\n", " | "))
        saved = ""
        try:
            if self.main_setup_complete:
                self.save_player()
                saved = "Your game was saved. "
        except Exception:
            pass
        message = ("Dragon Sword error\n\n%s\n%s\n\n%s(This is also in Dev\\Log.txt.) The game will close." %
                   (info.strip().splitlines()[-1], where, saved))
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "Dragon Sword", 0x10)
        except Exception:
            print(message, file=sys.stderr)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    Game(root).run()
