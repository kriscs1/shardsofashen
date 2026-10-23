"""One player in the shared world: their character (what the desktop game kept on its Game object for the one player),
what their browser asked for, and what it is to be told.

Everything that is theirs alone lives here: inventory, skills, equipment, bank, quests and attributes, the NPCs they've
turned friend or foe, the one-time things they've taken, their own view of quest-locked doors and gates (cell_override)
and the changes their quests made to the world just for them (personal_cells, hidden_uids, ent_overrides, entities
they own). The rest of the world is World's, shared by everyone."""
import json
import logging
import math

from dragonsword.lb import val, word, trim, lbstr, distance, clock_ms

from .entity import Entity, InvItem, PLAYER, TILE, NPC, MAPITEM
from .player_items import ItemsMixin
from .player_combat import CombatMixin
from .player_actions import ActionsMixin
from .scripting import ScriptMixin
from .quests import QuestMixin
from .pvp import PvPMixin
from .homes import HomeMixin
from .farming import FarmMixin

log = logging.getLogger("dragonsword.session")

HOTBAR_SLOTS = 5
LOOK_PARTS = ("skin", "hair", "shirt", "legs")


def clean_look(look):
    """A character's colours ({"skin": "#rrggbb", ...}): only the four parts, only colours; None if there are none."""
    if not isinstance(look, dict):
        return None
    out = {}
    for k in LOOK_PARTS:
        v = str(look.get(k, "")).strip().lower()
        if len(v) == 7 and v[0] == "#" and all(c in "0123456789abcdef" for c in v[1:]):
            out[k] = v
    return out or None


class Session(ItemsMixin, CombatMixin, ActionsMixin, ScriptMixin, QuestMixin, PvPMixin, HomeMixin, FarmMixin):
    def __init__(self, world, name, admin=False):
        self.w = world
        self.data = world.data
        self.player_name = name
        self.admin_enabled = admin
        self.god_mode = 0
        self.out = []                       # events waiting to go to the browser
        self.connected = True
        self.ready = False                  # in the world (not still loading)
        d = self.data
        self.tw, self.th, self.sw, self.sh, self.xt, self.yt = d.tw, d.th, d.sw, d.sh, d.xt, d.yt
        p = Entity(PLAYER, "Player")
        p.attack_speed = d.player_attack_speed
        p.move_speed = d.player_move_speed
        self.player = p
        self.init_state()

    # =================================================================================================================
    # State
    # =================================================================================================================
    def init_state(self):
        d = self.data
        self.inv = []
        self.skill_xp = [0.0] * (d.total_skills + 1)
        self.skill_off = [0] * (d.total_skills + 1)
        self.read_disabled_skills()
        self.equipped = [""] * (d.equip_slots + 1)
        self.equip_wear = [0] * 12
        self.equip_attack_total = self.equip_defence_total = self.equip_magic_total = 0
        self.bank_item = [""] * (d.bank_slots + 2)
        self.bank_qty = [0] * (d.bank_slots + 2)
        self.bank_wear = [[] for _ in range(d.bank_slots + 2)]
        self.attributes = []
        self.quest_notes = []
        self.npc_attitudes = {}
        self.taken_once = set()
        self.explored = {}                  # map -> "all" or a set of fog cell numbers
        self.hotbar = [""] * HOTBAR_SLOTS
        self.grave = None
        self.look = None                    # their colours (skin, hair, shirt, legs), or None
        self.grave_ent = None
        self.status = {}
        self.cooldowns = {}
        self.clear_boosts_values()
        self.player_sprite_base = "Player"
        self.player_max_hp = int(d.hp_base + 2 * d.hp_per_level)
        self.player_mana = -1
        self.player_max_mana = 10
        self.hp_regen_last = 0
        self.low_hp_warned = 0
        self.ammo_warned = 0
        self.player_last_attack = self.player_last_combat = self.player_last_cast = 0
        self.player_attack_target = None
        self.keyboard_direction = 0
        self.player_walk_active = False
        self.player_walk_x = self.player_walk_y = 0
        self.player_walk_speed = self.player_walk_range = 0
        self.player_walk_stuck = self.player_walk_replans = 0
        self.pending_verb = ""
        self.pending_ent = None
        self.pending_map = None             # (map, x, y): a teleport waiting for the end of the tick
        self.player_moved = False
        self.player_prev_x = self.player_prev_y = 0
        self.player_entry_x = self.player_entry_y = 0
        self.player_tile = None
        self.cur_map = None
        self.item_in_use = None
        self.clicked_ent = None
        self.clicked_tile_x = self.clicked_tile_y = 1
        self.script_cursor_x = self.script_cursor_y = 0
        self.user_input_enabled = True
        self.player_visible = val(d.config_read("Gameplay", "Player.Visible", "1")) == 1
        self.lock_bumped = None
        self.lock_bump_last = None
        self.lock_bump_time = 0
        self.lock_cache = {}
        self.lock_seen = {}
        self.lock_cells = {}                # (map, x, y) -> the Unlocked.Tile this player sees there
        self.personal_cells = {}            # (map, x, y) -> a cell spec: their quest's own Change.Tile
        self.cell_override = {}             # (map, x, y) -> (tile, decor, walk, los): the two above, worked out
        self.hidden_uids = set()            # world entities their quest took away (for them)
        self.ent_overrides = {}             # uid -> {field: value}: NPC stats their quest changed (for them)
        self.ent_attitudes = {}             # uid -> True/False: Edit.Entity ATTITUDE for them
        self.personal_timers = []           # [due ms, map, x, y, spec]: their quest's tile changes coming back
        self.fog_view_distance = d.fog_view_distance
        self.sleep_state = None
        self.ab_mode = ""
        self.ab_image = self.ab_title = self.ab_text = ""
        self.ab_item_defs = []
        self.responses = []
        self.response_actions = []
        self.rack_type = self.rack_name = ""
        self.rack = []
        self.rack_page = 1
        self.rack_pages = 1
        self.rack_buy_rate, self.rack_sell_rate = 1.2, 0.8
        self.rack_specific = 0
        self.rack_skill = ""
        self.message_log_last = ("", 0)
        self.last_auto_save = clock_ms()
        self.dirty_me = True                # inventory, skills... changed: the browser is sent them again
        self.dirty_quests = True
        self.weather_dirty = True
        self.cells_dirty = True
        self.sent_maps = {}                 # map -> version the browser has
        self.view_known = {}                # uid -> what the browser last had of it
        self.init_home()
        self.init_scripts()

    def clear_boosts_values(self):
        self.spell_defence_bonus = self.spell_defence_until = 0
        self.spell_attack_bonus = self.spell_attack_until = 0
        self.spell_magic_bonus = self.spell_magic_until = 0
        self.spell_sight_bonus = self.spell_sight_until = 0

    @property
    def now(self):
        return self.w.now

    @property
    def loop_start(self):
        return self.w.now

    def in_world(self):
        return self.ready and self.connected

    def sleeping(self):
        return self.sleep_state is not None

    @property
    def screen_name(self):
        return self.cur_map.name if self.cur_map is not None else ""

    def map_x(self):
        return self.cur_map.mx if self.cur_map else 0

    def map_y(self):
        return self.cur_map.my if self.cur_map else 0

    def map_z(self):
        return self.player.z

    def map_ox(self):
        return self.cur_map.ox if self.cur_map else 0

    def map_oy(self):
        return self.cur_map.oy if self.cur_map else 0

    def local_x(self, gx):
        return gx - self.map_ox()

    def local_y(self, gy):
        return gy - self.map_oy()

    def tile_of_x(self, gx):
        """The current map's tile column of global x (1..xt)."""
        tx = int((gx - self.map_ox()) / self.tw) + 1
        return min(max(tx, 1), self.xt)

    def tile_of_y(self, gy):
        ty = int((gy - self.map_oy()) / self.th) + 1
        return min(max(ty, 1), self.yt)

    def log(self, text):
        log.info("[%s] %s", self.player_name, text)

    # =================================================================================================================
    # Talking to the browser
    # =================================================================================================================
    def emit(self, ev):
        if self.connected:
            self.out.append(ev)

    def display_message(self, message, mtype):
        last, at = self.message_log_last
        if message == last and 0 <= self.now - at < 500:
            return
        self.message_log_last = (message, self.now)
        if message[:14].upper() == "QUEST COMPLETE":
            self.play_sound("Quest")
        self.emit({"t": "msg", "text": message, "kind": str(mtype)})

    def play_sound(self, sound, at=None):
        """A sound: at = the global point it is made at (everyone near hears it), None = only this player."""
        if not trim(sound):
            return
        if at is None:
            self.emit({"t": "sound", "name": sound})
        else:
            self.w.sound(sound, self.player.z, at[0], at[1])

    def fx_splat(self, kind, amount, e):
        self.w.fx_splat(kind, amount, e, e.owner)

    def fx_anim(self, base, x, y, ms):
        self.w.fx_anim(base, self.player.z, x, y, ms)

    def fx_nudge(self, e, dx, dy, ms):
        self.w.fx_nudge(e, dx, dy, ms, e.owner)

    def fx_skill_pop(self, skill):
        self.w.fx({"t": "skillpop", "uid": self.player.uid, "skill": skill}, self.player.z, self.player.cx,
                  self.player.cy)

    def fx_hurt_flash(self):
        self.emit({"t": "hurt"})

    def level_up_show(self, skill, level):
        self.emit({"t": "levelup", "skill": skill, "level": level})
        self.w.fx({"t": "burst", "uid": self.player.uid}, self.player.z, self.player.cx, self.player.cy)

    def draw_skills(self):
        self.dirty_me = True

    # =================================================================================================================
    # Saves: the same fields as the desktop game's Saves\<Name>.ini, kept as a dict (JSON in the database)
    # =================================================================================================================
    def load_state(self, st):
        """st: a saved character (a dict), or None for a new one (Saves\\TEMPLATE.ini's start)."""
        d = self.data
        p = self.player
        st = st or {}
        m = self.w.map_named(st.get("map", d.start_map)) or self.w.map_named(d.start_map)
        if m is None:
            m = next(iter(self.w.maps.values()))
            x, y = d.start_x, d.start_y
        else:
            x = val(st.get("x", d.start_x))
            y = val(st.get("y", d.start_y))
        self.player_sprite_base = st.get("sprite", "Player") if (
            d.loaded(st.get("sprite", "")) or d.animation_available(st.get("sprite", "")) > 0) else "Player"
        p.name = self.player_sprite_base
        self.w.init_entity(p, m.mz, m.ox + x, m.oy + y, m.name)
        p.direction = max(1, int(val(st.get("direction", 4))))
        for i in range(1, d.total_skills + 1):
            self.skill_xp[i] = min(d.skill_max_level, max(0, val(st.get("skills", {}).get(d.skill_name[i], 0))))
        self.default_hitpoints_level()
        self.update_max_hp()
        hp = val(st.get("hp", 0))
        p.hp = hp if 0 < hp <= self.player_max_hp else self.player_max_hp
        self.player_mana = val(st.get("mana", -1))
        for name, qty, wear in st.get("inventory", []):
            self.add_inventory_item(self.renamed(name), max(1, int(qty)), int(wear), quiet=True)
        for i, (name, wear) in enumerate(st.get("equipped", [])[:d.equip_slots], 1):
            self.equipped[i] = self.renamed(name)
            self.equip_wear[i] = int(wear)
        for i, (name, qty, wears) in enumerate(st.get("bank", [])[:d.bank_slots], 1):
            self.bank_item[i] = self.renamed(name)
            self.bank_qty[i] = max(1, int(qty))
            self.bank_wear[i] = [int(w) for w in wears]
        self.attributes = [[k, v] for k, v in st.get("attributes", [])][:500]
        self.quest_notes = [[q, int(dn), t] for q, dn, t in st.get("quest_notes", [])][:400]
        self.npc_attitudes = dict(st.get("npc_attitudes", {}))
        self.taken_once = set(st.get("taken_once", []))
        self.hotbar = (list(st.get("hotbar", [])) + [""] * HOTBAR_SLOTS)[:HOTBAR_SLOTS]
        self.hotbar = [self.renamed(h) for h in self.hotbar]
        self.explored = {k: ("all" if v == "all" else set(v)) for k, v in st.get("explored", {}).items()}
        g = st.get("grave")
        self.look = clean_look(st.get("look"))
        r = st.get("home_return")
        if isinstance(r, list) and len(r) == 3:
            self.home_return = (str(r[0]), val(r[1]), val(r[2]))
        if g and g.get("items"):
            self.grave = {"map": g["map"], "x": val(g["x"]), "y": val(g["y"]), "left": val(g["left"]),
                          "items": [tuple(i) for i in g["items"]]}
        self.check_saved_equipment()
        self.recalc_equipment()
        if not st:
            self.new_player_start()
        self.cur_map = m
        self.player_tile = None

    def new_player_start(self):
        """A new character: Saves\\TEMPLATE.ini's skills, inventory, equipment and bank."""
        from dragonsword import ini
        path = self.data.path("Saves", "TEMPLATE.ini")
        d = self.data
        r = lambda s, k, default: ini.read(s, k, default, path)
        m = self.w.map_named(r("Player", "Map", d.start_map)) or self.w.map_named(d.start_map)
        if m is not None:
            self.w.init_entity(self.player, m.mz, m.ox + val(r("Player", "X", lbstr(d.start_x))),
                               m.oy + val(r("Player", "Y", lbstr(d.start_y))), m.name)
            self.cur_map = m
        for i in range(1, d.total_skills + 1):
            self.skill_xp[i] = min(d.skill_max_level, max(0, val(r("Skills", d.skill_name[i], "0"))))
        self.default_hitpoints_level()
        self.update_max_hp()
        self.player.hp = self.player_max_hp
        for i in range(1, 100):
            slot = r("Inventory", "Slot%d" % i, "")
            if slot:
                self.add_inventory_item(trim(word(slot, 1, ",")), max(1, val(word(slot, 2, ","))), quiet=True)
        for i in range(1, d.equip_slots + 1):
            item = trim(r("Equipment", d.equip_slot_names[i], ""))
            if item:
                self.equipped[i] = item
        for i in range(1, d.bank_slots + 1):
            slot = r("Bank", "Slot%d" % i, "")
            if slot:
                self.bank_item[i] = trim(word(slot, 1, ","))
                self.bank_qty[i] = max(1, val(word(slot, 2, ",")))
        self.recalc_equipment()

    def save_state(self):
        d = self.data
        p = self.player
        m = self.cur_map or self.w.map_at(p.z, p.fx, p.fy)
        st = {
            "map": m.name if m else d.start_map,
            "x": int(p.x - m.ox) if m else d.start_x, "y": int(p.y - m.oy) if m else d.start_y,
            "hp": p.hp, "mana": int(self.player_mana), "direction": max(1, int(p.direction)),
            "sprite": self.player_sprite_base,
            "skills": {d.skill_name[i]: self.skill_xp[i] for i in range(1, d.total_skills + 1)},
            "inventory": [[e.name, e.quantity, e.wear] for e in self.inv],
            "equipped": [[self.equipped[i], self.equip_wear[i]] for i in range(1, d.equip_slots + 1)],
            "bank": [[self.bank_item[i], self.bank_qty[i], self.bank_wear[i][:self.bank_qty[i]]]
                     for i in range(1, d.bank_slots + 1) if self.bank_item[i]],
            "attributes": [[n, v] for n, v in self.attributes],
            "quest_notes": [[q, dn, t] for q, dn, t in self.quest_notes],
            "npc_attitudes": dict(self.npc_attitudes),
            "taken_once": sorted(self.taken_once),
            "hotbar": list(self.hotbar),
            "explored": {k: ("all" if v == "all" else sorted(v)) for k, v in self.explored.items()},
            "grave": self.grave,
            "look": self.look,
            "home_return": list(self.home_return) if self.home_return else None,
        }
        return st

    ITEM_RENAMES = {"Key": "Beggars_House_Key"}

    def renamed(self, item):
        return self.ITEM_RENAMES.get(item, item)

    def read_disabled_skills(self):
        off = self.data.disabled_skills()
        for i in range(1, self.data.total_skills + 1):
            name = self.data.skill_name[i].upper()
            self.skill_off[i] = 1 if name in off and name != "HITPOINTS" else 0

    # =================================================================================================================
    # Coming into the world, leaving it
    # =================================================================================================================
    def enter_world(self):
        self.ready = True
        self.god_mode = self.data.god_mode_setting() if self.admin_enabled else 0
        self.cur_map = None
        self.emit(self.w.clock_event())
        self.check_map()
        self.emit({"t": "buildables", "pieces": self.homes.catalog_for_client()})
        self.check_home_entry()
        self.display_message("Welcome to Dragon Sword, %s!" % self.player_name, "INFORMATION")
        self.display_message("Press H (or F1) for your journal: what you can make and gather, quests and controls.",
                             "INFO")

    def leave_world(self):
        """Gone: their own things go with them, NPCs fighting them give up."""
        self.ready = False
        for e in list(self.w.ents):
            if e.owner is self:
                self.w.remove_entity(e)
            elif e.type == NPC and e.target is self and e.ai is not None:
                self.w.npc_give_up(e, e.ai)
        self.grave_ent = None

    def entity_gone(self, e):
        """A world entity has gone: forget it wherever this player was using it."""
        if self.player_attack_target is e:
            self.player_attack_target = None
        if self.pending_ent is e:
            self.stop_player_walk()
        if self.script_move_ent is e:
            e.script_moving = False
            self.script_move_ent = None
        if self.item_in_use is e:
            self.item_in_use = None
        if self.grave_ent is e:
            self.grave_ent = None

    # =================================================================================================================
    # Every tick
    # =================================================================================================================
    def tick_before_npcs(self):
        if not self.in_world():
            return
        now = self.now
        self.status_tick()
        self.grave_tick(self.w.dt * 1000)
        if self.sleep_state:
            self.sleep_tick()
            return
        self.player_moved = False
        self.lock_bumped = None
        paused = bool(self.ab_mode)                 # (a box is open: you stand still, the world goes on)
        if not paused:
            self.move_player()
        if self.lock_bumped is not None:
            self.lock_bump(self.lock_bumped)
        self.check_map()
        self.check_player_tile()

    def tick_after_npcs(self):
        if not self.in_world():
            return
        if self.sleep_state:
            return
        self.update_script_move()
        if not self.ab_mode:
            self.update_player_combat()
        self.update_player_health()
        self.update_mana()
        self.w.animate_entity(self.player, self.player_moved)
        self.run_scripts()
        self.run_personal_timers()
        if self.pending_map is not None:
            self.do_pending_map_change()
        if self.now - self.last_auto_save >= 60000 or self.now < self.last_auto_save:
            self.last_auto_save = self.now
            self.save_requested = True

    # =================================================================================================================
    # Moving
    # =================================================================================================================
    def move_player(self):
        p = self.player
        self.player_prev_x, self.player_prev_y = p.x, p.y
        if self.keyboard_direction != 0 and self.user_input_enabled:
            self.stop_player_walk()
            self.player_attack_target = None
            if self.move_entity(p, self.keyboard_direction):
                self.player_moved = True
        elif self.player_walk_active:
            self.update_player_walk()

    def move_entity(self, e, direction):
        if direction == 0:
            return False
        dist = e.move_speed * self.w.dt * self.w.ground_speed(e)
        if dist <= 0:
            return False
        x = y = 0.0
        if direction & 1:
            y = -dist
        if direction & 4:
            y = dist
        if direction & 2:
            x = dist
        if direction & 8:
            x = -dist
        if x != 0 and y != 0:
            x *= 0.7071067811865476
            y *= 0.7071067811865476
        e.direction = direction
        return self.w.try_move_entity(e, x, y, self)

    def walk_player_to(self, x, y, speed, rng):
        p = self.player
        self.player_walk_active = True
        self.player_walk_x, self.player_walk_y = x, y
        self.player_walk_speed = speed
        self.player_walk_range = rng
        self.player_walk_stuck = 0
        self.player_walk_replans = 0
        p.path = []
        p.path_best = None
        p.path_stuck = 0
        p.path_goal = self.w.path_goal_key(x, y, rng)
        self.w.plan_path(p, x, y, rng, 2200, self)

    def stop_player_walk(self):
        self.player_walk_active = False
        self.pending_verb = ""
        self.pending_ent = None
        self.player.path = []

    def block_player(self):
        self.stop_player_walk()
        self.w.set_entity_position(self.player, self.player_entry_x, self.player_entry_y)
        self.player_tile = None

    def update_player_walk(self):
        p = self.player
        w = self.w
        if self.pending_ent is not None:
            if not self.pending_ent.alive:
                self.stop_player_walk()
                return
            self.player_walk_x, self.player_walk_y = self.pending_ent.cx, self.pending_ent.cy
            if self.pending_ent.type == TILE:
                self.player_walk_x, self.player_walk_y = self.script_cursor_x, self.script_cursor_y
        d = distance(p.cx, p.cy, self.player_walk_x, self.player_walk_y)
        if d <= self.player_walk_range:
            self.finish_player_walk()
            return
        speed = self.player_walk_speed if self.player_walk_speed > 0 else p.move_speed
        if self.pending_ent is not None:
            goal = w.path_goal_key(self.player_walk_x, self.player_walk_y, self.player_walk_range)
            if goal != p.path_goal and (self.now >= p.path_time or p.path_time - self.now > 5000):
                p.path_goal = goal
                w.plan_path(p, self.player_walk_x, self.player_walk_y, self.player_walk_range, 2200, self)
        sx, sy = w.path_steer(p, self.player_walk_x, self.player_walk_y)
        if w.move_entity_toward(p, sx, sy, speed, self):
            self.player_moved = True
        w.path_progress(p, sx, sy)
        self.player_walk_stuck = p.path_stuck
        if self.player_walk_stuck > 15:
            if self.player_walk_replans < 2:
                self.player_walk_replans += 1
                w.plan_path(p, self.player_walk_x, self.player_walk_y, self.player_walk_range, 2200, self)
                self.player_walk_stuck = 0
            else:
                self.finish_player_walk()

    def finish_player_walk(self):
        verb, e = self.pending_verb, self.pending_ent
        self.stop_player_walk()
        if verb and e is not None:
            self.do_action(verb, e)

    def lock_bump(self, bumped):
        m, lk = bumped
        now = self.now
        key = (m.name, lk.n)
        if key != self.lock_bump_last or now - self.lock_bump_time > 1500 or now < self.lock_bump_time:
            self.display_message(lk.message, "FAIL")
            self.play_sound("Locked")
        self.lock_bump_last = key
        self.lock_bump_time = now

    def check_map(self):
        """Which map the player is on now: a new one has its entry script run and its locks looked at."""
        p = self.player
        m = self.w.map_at(p.z, p.fx, p.fy) or self.cur_map
        if m is None or m is self.cur_map:
            return
        arenas = self.pvp_rules()[0]
        if self.cur_map is not None and self.cur_map.name in arenas and m.name not in arenas:
            self.fog_view_distance = self.data.fog_view_distance      # (the arena lifts the fog; out of it, it's back)
            self.dirty_me = True
        home_before = self.cur_map is not None and self.homes.is_home_map(self.cur_map.name)
        if self.homes.is_home_map(m.name):
            self.fog_view_distance = 0                                  # (no fog on a homestead: you can see it all)
            self.dirty_me = True
        elif home_before:
            self.fog_view_distance = self.data.fog_view_distance
            self.dirty_me = True
        self.cur_map = m
        self.player_tile = None
        self.add_explored_map(m.name)
        self.check_locks(False)
        self.grave_place()
        self.cells_dirty = True
        self.weather_dirty = True
        self.emit({"t": "map", "name": m.name, "x": m.mx, "y": m.my, "z": m.mz})
        if self.script_exists(m.name):
            self.start_script(m.name, False, entry=True)

    def check_player_tile(self):
        """Trigger scripts when the player walks onto a tile that has one."""
        p = self.player
        m = self.cur_map
        if m is None:
            return
        tx, ty = self.tile_of_x(p.fx), self.tile_of_y(p.fy)
        if (m.name, tx, ty) == self.player_tile:
            return
        if self.player_tile is not None:
            self.player_entry_x, self.player_entry_y = self.player_prev_x, self.player_prev_y
        else:
            self.player_entry_x, self.player_entry_y = p.x, p.y
        self.player_tile = (m.name, tx, ty)
        trig = m.trigger[m.cell(tx, ty)]
        if trig:
            self.start_script(trig, False)

    def teleport(self, map_name, x, y):
        """Off to map_name's pixel x,y at the end of this tick (scripts, ladders, spells, dying)."""
        self.pending_map = (map_name, x, y)

    def do_pending_map_change(self):
        map_name, x, y = self.pending_map
        self.pending_map = None
        self.stop_player_walk()
        m = self.w.map_named(map_name)
        if m is None:
            self.display_message("That leads nowhere!", "FAIL")
            return
        if self.ab_mode:
            self.close_action_box(-1)
        p = self.player
        p.x, p.y, p.z = m.ox + x, m.oy + y, m.mz
        self.player_tile = None
        self.emit({"t": "teleport"})
        self.check_map()

    # =================================================================================================================
    # Locks and this player's own view of the tiles
    # =================================================================================================================
    def lock_closed(self, m, lk):
        key = (m.name, lk.n)
        v = self.lock_cache.get(key)
        if v is None:
            v = not (trim(lk.condition) != "" and self.condition_met(lk.condition))
            self.lock_cache[key] = v
        return v

    def check_locks(self, announce):
        """Their locks again (after their items, attributes, skills or gear changed): doors and gates that open or
        shut for them, a click when one near them opens."""
        self.lock_cache = {}
        if self.cur_map is None:
            return
        changed = False
        p = self.player
        for m in self.w.neighbours(self.cur_map):
            for lk in m.locks:
                closed = self.lock_closed(m, lk)
                key = (m.name, lk.n)
                prev = self.lock_seen.get(key)
                self.lock_seen[key] = closed
                if prev != closed:
                    self.cells_dirty = True
                cell = (m.name, lk.x, lk.y)
                if lk.opened:
                    want = None if closed else lk.opened
                    if self.lock_cells.get(cell) != want:
                        if want is None:
                            self.lock_cells.pop(cell, None)
                        else:
                            self.lock_cells[cell] = want
                        changed = True
                if announce and prev is True and not closed and m is self.cur_map:
                    cx, cy = m.ox + (lk.x - 0.5) * self.tw, m.oy + (lk.y - 0.5) * self.th
                    if distance(p.cx, p.cy, cx, cy) < 160:
                        self.display_message("You hear a click.", "INFO")
                        self.play_sound("Door")
        if changed:
            self.rebuild_cell_override()

    def rebuild_cell_override(self):
        d = self.data
        out = {}
        for (name, x, y), tile in self.lock_cells.items():
            m = self.w.maps.get(name)
            if m is None:
                continue
            decor = m.decor[m.cell(x, y)]
            walk, los = d.cell_walk_los(tile, decor)
            out[(name, x, y)] = (tile, decor, walk, los)
        for (name, x, y), spec in self.personal_cells.items():
            m = self.w.maps.get(name)
            if m is None:
                continue
            base = out.get((name, x, y))
            tile, decor = (base[0], base[1]) if base else (m.tile[m.cell(x, y)], m.decor[m.cell(x, y)])
            t, dc = d.cell_spec(spec)
            if t:
                tile = t
                if dc is None:
                    dc = ""
            if dc is not None:
                decor = dc
            walk, los = d.cell_walk_los(tile, decor)
            out[(name, x, y)] = (tile, decor, walk, los)
        self.cell_override = out
        self.cells_dirty = True

    def personal_change_tile(self, m, x, y, spec, delay=0, change_back=0):
        """Their quest changed a tile, for them alone."""
        key = (m.name, int(x), int(y))
        original = self.personal_cells.get(key) or m.cell_text(int(x), int(y))
        if delay > 0:
            self.personal_timers.append([self.now + delay * 1000, m.name, int(x), int(y), spec])
            if change_back > 0:
                self.personal_timers.append([self.now + (delay + change_back) * 1000, m.name, int(x), int(y), original])
            return
        self.personal_cells[key] = spec
        if change_back > 0:
            self.personal_timers.append([self.now + change_back * 1000, m.name, int(x), int(y), original])
        self.rebuild_cell_override()

    def run_personal_timers(self):
        if not self.personal_timers:
            return
        due = [t for t in self.personal_timers if t[0] <= self.now]
        if not due:
            return
        self.personal_timers = [t for t in self.personal_timers if t[0] > self.now]
        for _, name, x, y, spec in due:
            m = self.w.maps.get(name)
            if m is not None and spec == m.cell_text(x, y):
                self.personal_cells.pop((name, x, y), None)
            else:
                self.personal_cells[(name, x, y)] = spec
        self.rebuild_cell_override()

    def cells_for_view(self):
        """[(map, x, y, tile, decor)] of this player's own tiles on the maps round them (for their browser)."""
        names = {m.name for m in self.w.neighbours(self.cur_map)} if self.cur_map else set()
        return [[n, x, y, o[0], o[1]] for (n, x, y), o in self.cell_override.items() if n in names]

    def locks_for_view(self):
        """[(map, x, y, message)] of the locks shut for this player on the maps round them."""
        if self.cur_map is None:
            return []
        return [[m.name, lk.x, lk.y, lk.message] for m in self.w.neighbours(self.cur_map) for lk in m.locks
                if self.lock_closed(m, lk)]

    def cell_names(self, m, x, y):
        return self.w.cell_names(m, x, y, self)

    def attitude_of(self, e):
        """What this player made NPC e (True = foe), or None if they never changed it."""
        v = self.ent_attitudes.get(e.uid)
        if v is not None:
            return v
        a = self.npc_attitudes.get(self.w.npc_key(e)) if e.type == NPC else None
        return None if a is None else a == "Bad"

    def once_taken(self, e):
        key = self.w.once_key(e)
        return bool(key) and key in self.taken_once

    # =================================================================================================================
    # Fog of war: the browser works it out; what's been seen is kept here
    # =================================================================================================================
    def add_explored_map(self, name):
        if name and name not in self.explored:
            self.explored[name] = set()
            self.dirty_me = True

    def note_explored(self, name, cells):
        if name not in self.w.maps:
            return
        cur = self.explored.setdefault(name, set())
        if cur == "all":
            return
        for c in cells[:2000]:
            if isinstance(c, int) and 0 < c < 10000:
                cur.add(c)

    def explored_for_client(self):
        return {k: ("all" if v == "all" else sorted(v)) for k, v in self.explored.items()}

    # =================================================================================================================
    # Sleeping (DayNight.ini [Sleep]): the screen goes dark and you're healed. The time only jumps on when everyone
    # who's playing is asleep (one sky for everyone)
    # =================================================================================================================
    def sleep_refusal(self):
        w = self.w
        if not self.data.day_night_enabled or self.data.day_seconds <= 0:
            return w.dn("Sleep", "No.Day", "There's no day or night to sleep through.")
        p = self.player
        secs = val(w.dn("Sleep", "Fight.Seconds", "10"))
        if self.player_last_combat and 0 <= self.now - self.player_last_combat < secs * 1000:
            return w.dn("Sleep", "Fighting", "You're too wound up to sleep after that fight.")
        reach = val(w.dn("Sleep", "Foe.Range", "320"))
        for e in w.ents:
            if (e.type == NPC and e.alive and e.z == p.z and w.hostile_for(e, self) and w.visible_to(e, self) and
                    distance(e.cx, e.cy, p.cx, p.cy) < reach):
                return w.dn("Sleep", "Foes", "You can't sleep with enemies nearby!")
        return ""

    def start_sleep(self, until="Next"):
        why = self.sleep_refusal()
        if why:
            self.display_message(why, "FAIL")
            return False
        w = self.w
        u = trim(until).lower()
        morning = val(w.dn("Sleep", "Morning", "0.27")) % 1.0
        evening = val(w.dn("Sleep", "Evening", "0.80")) % 1.0
        if u == "morning":
            target = morning
        elif u == "evening":
            target = evening
        elif u and u.replace(".", "", 1).isdigit():
            target = val(u) % 1.0
        else:
            target = morning if w.is_night() else evening
        self.stop_player_walk()
        self.player_attack_target = None
        fade = max(50, val(w.dn("Sleep", "Fade", "1200")))
        hold = max(0, val(w.dn("Sleep", "Hold", "1400")))
        self.sleep_state = {"start": self.now, "target": target, "woken": False, "fade": fade, "hold": hold}
        self.emit({"t": "sleep", "fade": fade, "hold": hold, "text": w.dn("Sleep", "Text", "")})
        return True

    def sleep_tick(self):
        st = self.sleep_state
        w = self.w
        t = self.now - st["start"]
        if not st["woken"] and t >= st["fade"]:
            st["woken"] = True
            others = [s for s in w.sessions.values() if s is not self and s.in_world()]
            if all(s.sleeping() for s in others):
                w.set_day_fraction(st["target"])
            elif others:
                self.display_message("You doze for a while; the others are still up and about.", "INFO")
            if val(w.dn("Sleep", "Heal", "1")) == 1:
                self.player.hp = self.player_max_hp
                if self.player_max_mana > 0:
                    self.player_mana = self.player_max_mana
                self.dirty_me = True
        if t >= 2 * st["fade"] + st["hold"]:
            self.sleep_state = None
            night_wake = abs(st["target"] - val(w.dn("Sleep", "Morning", "0.27")) % 1.0) < 1e-6
            words = w.dn("Sleep", "Wake.Morning" if night_wake else "Wake.Evening", "")
            if words:
                self.display_message(words, "INFO")
            self.save_requested = True

    save_requested = False

    # =================================================================================================================
    # What the browser is told about the player themselves
    # =================================================================================================================
    def me_state(self):
        d = self.data
        p = self.player
        return {
            "t": "me", "name": self.player_name, "uid": p.uid, "admin": self.admin_enabled, "god": self.god_mode,
            "hp": p.hp, "max_hp": self.player_max_hp, "mana": int(self.player_mana), "max_mana": self.player_max_mana,
            "xp": self.skill_xp[1:], "skill_off": self.skill_off[1:],
            "inv": [[e.uid, e.name, e.quantity, e.wear] for e in self.inv],
            "equipped": self.equipped[1:], "wear": self.equip_wear[1:d.equip_slots + 1],
            "totals": [self.equip_attack_total, self.equip_defence_total, self.equip_magic_total],
            "hotbar": self.hotbar, "status": sorted(self.status), "input": self.user_input_enabled,
            "visible": self.player_visible, "sprite": self.player_sprite_base, "worn": self.worn_items(), "look": self.look,
            "view": self.fog_view_distance + self.spell_sight_bonus,
            "target": self.player_attack_target.uid if self.player_attack_target is not None else 0,
            "level": self.player_level(), "arena": self.on_arena_ground(), "home": self.home_state(), "cooldowns": {k: max(0, v - self.now) for k, v in self.cooldowns.items() if v > self.now},
            "boosts": {"attack": self.spell_attack_bonus, "defence": self.spell_defence_bonus,
                       "magic": self.spell_magic_bonus, "sight": self.spell_sight_bonus},
            "grave": ({"map": self.grave["map"], "left": int(self.grave["left"])} if self.grave else None),
        }

    def quests_state(self):
        return {"t": "quests", "quests": self.quest_list(), "marks": self.quest_markers(),
                "level": self.player_level()}

    def box_state(self):
        """The ActionBox (a conversation, a shop, the bank, crafting) as the browser draws it, or closed."""
        if not self.ab_mode:
            return {"t": "box", "mode": ""}
        items = []
        for name, qty, misc in self.ab_item_defs:
            it = {"name": name, "qty": qty, "i": misc}
            if self.ab_mode == "Craft":
                e = self.rack_pseudo(misc)
                it["short"] = self.rack_level_short(e)
                it["missing"] = self.rack_missing(e)
            items.append(it)
        return {"t": "box", "mode": self.ab_mode, "image": self.ab_image, "title": self.ab_title,
                "text": self.ab_text, "items": items, "responses": self.responses, "page": self.rack_page,
                "pages": self.rack_pages, "rack": self.rack_name, "buy_rate": self.rack_buy_rate,
                "sell_rate": self.rack_sell_rate * self.data.sell_price_factor, "specific": self.rack_specific,
                "stock": [r["item"] for r in self.rack], "skill": self.rack_skill}
