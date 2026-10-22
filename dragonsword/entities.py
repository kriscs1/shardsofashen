"""Entities in the world (items, objects, NPCs), their pictures and walking animation, movement, player walking and the
inventory."""
import math
import os

from .entity import (Entity, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, INFRONTTILE,
                     ROOF, INVENTORYITEM, ACTIONBOXITEM, TYPE_NAMES, DEFAULT_LIMITS, normalise_type,
                     attitude_of_type, parse_attitude)
from .lb import val, word, trim, lbstr, distance, strip_digits, parse_quantity


class EntityMixin:
    WALK_STEP = 14  # Pixels walked per frame of the walking animation

    # =================================================================================================================
    # Pictures
    # =================================================================================================================
    def fallback_sprite(self):
        if self.assets.loaded("Placeholder"):
            return "Placeholder"
        return next(iter(self.assets.sprites), "")

    def interface_sprite(self, name):
        if self.assets.loaded(name):
            return name
        self.log_missing("Sprite", name)
        return self.fallback_sprite()

    def animation_available(self, base):
        """Walking frames <base><Dir><Frame>: 4 = all four directions, 2 = side-on (2 and 8 only), 0 = none."""
        if not base:
            return 0
        k = self.walk_kinds.get(base)
        if k is not None:
            return k
        kind = 0
        if self.walk_frames_loaded(base, "1248"):
            kind = 4
        elif self.walk_frames_loaded(base, "28"):
            kind = 2
        self.walk_kinds[base] = kind
        return kind

    def walk_frames_loaded(self, base, dirs):
        for d in dirs:
            for f in "abc":
                name = base + d + f
                if not self.assets.loaded(name):
                    if not self.assets.load_if_exists("Walk", name):
                        return False
        return True

    def first_image(self, etype, name):
        """The picture an entity of etype called name starts with, and whether it is animated."""
        if etype in (PLAYER, NPC) and self.animation_available(name) > 0:
            if self.animation_available(name) == 2:
                return name + "2a", True
            return name + "1a", True
        if self.assets.loaded(name):
            return name, False
        self.log_missing("Sprite", name)
        return self.fallback_sprite(), False

    def set_sprite_size(self, e, image, animated):
        if e.type in (ROOF, TILE, INFRONTTILE):
            e.w, e.h = self.tw, self.th
        else:
            e.w, e.h = self.assets.width(image), self.assets.height(image)
        e.image = image
        e.animated = animated

    def sprite_size_of(self, etype, name):
        image, _ = self.first_image(etype, name)
        return self.assets.width(image), self.assets.height(image)

    def init_entity(self, e, x, y):
        """Add.Sprite: picture, size, verbs, where it started."""
        image, animated = self.first_image(e.type, e.name)
        self.set_sprite_size(e, image, animated)
        if e.type in (MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY):
            e.map = self.map_at(x, y)
        if e.type in (TILE, INFRONTTILE, ROOF):
            e.misc = self.tile_ini(e.name, "Show.Name", "0")
            e.use_words = self.tile_ini(e.name, "Use.Words", "")
        else:
            e.use_words = self.entity_ini(e.name, "Use.Words", "")
        e.x, e.y = x, y
        if e.animated:
            self.animate_entity(e, False)
        e.orig_x, e.orig_y = x, y
        self.force_layer_update = True

    def count_type(self, etype):
        return sum(1 for e in self.world if e.type == etype)

    def new_world_entity(self, etype, name, x, y):
        limit = self.type_limits.get(etype)
        if limit is not None and self.count_type(etype) >= limit:
            self.log("ERROR - No free IDs left for entity type %s (%d)" % (TYPE_NAMES[etype], limit))
            return None
        e = Entity(etype, name)
        self.init_entity(e, x, y)
        self.world.append(e)
        self.set_entity_position(e, x, y)
        return e

    # =================================================================================================================
    # Adding and removing
    # =================================================================================================================
    def add_map_item(self, name, x, y, quantity):
        e = self.new_world_entity(MAPITEM, name, x, y)
        if e is None:
            return None
        e.quantity = max(1, int(quantity))
        e.orig_quantity = e.quantity
        return e

    def is_once(self, name, options):
        """A one-time item: Once=1 in its map line's options, or Once=1 in its Entities.ini section (every one placed).
        Picked up, it never comes back (Taken.Once in the save)."""
        v = self.option_value(options, "Once") or self.entity_ini(name, "Once", "0")
        return trim(v) in ("1", "yes", "Yes", "true", "True")

    def once_key(self, name, map_name, x, y, options):
        """How the save remembers a one-time item: its Id, or map@x,y (where its map line puts it), or "" if it isn't
        one-time."""
        if not self.is_once(name, options):
            return ""
        oid = self.option_value(options, "Id")
        return oid if oid else "%s@%d,%d" % (map_name, int(x), int(y))

    def add_static_object(self, name, x, y):
        return self.new_world_entity(STATICOBJECT, name, x, y)

    def add_npc(self, name, x, y, options, attitude=""):
        """An NPC: friendly (Good) or a foe (Bad), from npc_attitude(); a script may have changed that for good for
        this one NPC (Set.NPC.Attitude: npc_attitudes, kept in the save; npc_key says which NPC)."""
        e = self.new_world_entity(NPC, name, x, y)
        if e is None:
            return None
        e.npc_id = self.option_value(options, "Id")
        e.hostile = self.npc_attitude(name, options, attitude)
        self.load_npc_stats(e)
        self.set_entity_position(e, x, y)
        self.init_npc_ai(e, options)
        changed = self.npc_attitude_override(e)
        if changed is not None and changed != e.hostile:
            self.set_npc_hostile(e, changed)
        return e

    def npc_attitude(self, name, options, attitude=""):
        """True if the NPC is Bad: its map line's Attitude= option, else the old type it was given as (GoodNPC /
        BadNPC), else Entities.ini Attitude= (or the old Type=GoodNPC / BadNPC), else Good."""
        v = parse_attitude(self.option_value(options, "Attitude"))
        if v is not None:
            return v
        for v in (parse_attitude(attitude) if attitude else None, parse_attitude(self.entity_ini(name, "Attitude", ""))):
            if v is not None:
                return v
        return attitude_of_type(self.entity_ini(name, "Type", "")) == "Bad"

    @staticmethod
    def option_value(options, key):
        """The value of Key= in an NPC map line's Options ("" if it isn't there)."""
        for pair in str(options).replace("\t", " ").split():
            if pair.upper().startswith(key.upper() + "="):
                return pair[len(key) + 1:]
        return ""

    def npc_key(self, e):
        """Which NPC this is, for Set.NPC.Attitude and the save: its map line's Id= if it has one, else its map and
        where its map line puts it (e.g. 1,6,0@320,288), the same each time it is loaded or respawns."""
        if e.npc_id:
            return e.npc_id
        home = self.entity_home(e)
        return "%s@%s" % (home, self.local_coords(home, e.orig_x, e.orig_y))

    def npc_attitude_override(self, e):
        """What Set.NPC.Attitude made this one NPC (True = Bad); None if it was never changed."""
        v = self.npc_attitudes.get(self.npc_key(e))
        return None if v is None else v == "Bad"

    def set_npc_hostile(self, e, hostile):
        """Turns an NPC into a foe (it attacks on sight, like a monster) or a friend (it stops fighting and walks back
        to what it was doing)."""
        e.hostile = hostile
        if hostile:
            e.aggressive = 1
            e.aggro_range = max(e.aggro_range, 100)
        else:
            if self.player_attack_target is e:
                self.player_attack_target = None
            if e.in_combat and e.ai is not None:
                self.npc_give_up(e, e.ai)
            e.in_combat = False
        self.force_layer_update = True

    def set_npc_attitude(self, which, attitude):
        """Set.NPC.Attitude: one NPC becomes Good or Bad, now and whenever it is loaded or respawns (kept in the save,
        [NPC.Attitudes]). which: the Id= on its map line, or CLICKED (the NPC the player clicked to start the script:
        talked to, attacked, used an item on)."""
        hostile = parse_attitude(attitude)
        which = trim(which)
        if hostile is None or not which:
            self.log("ERROR - Set.NPC.Attitude: '%s' is not Good or Bad (%s)" % (attitude, which))
            return
        if which.upper() == "CLICKED":
            e = self.clicked_ent
            if e is None or e.type != NPC:
                self.log("ERROR - Set.NPC.Attitude CLICKED: the script wasn't started on an NPC")
                return
            key = self.npc_key(e)
        else:
            key = which
        self.npc_attitudes[key] = "Bad" if hostile else "Good"
        for e in list(self.world):
            if e.type == NPC and e.alive and self.npc_key(e) == key and e.hostile != hostile:
                self.set_npc_hostile(e, hostile)

    def load_npc_stats(self, e):
        n = e.name
        default_aggro = "60" if e.hostile else "0"
        hp = max(1, val(self.entity_ini(n, "Hitpoints", "5")))
        e.hp = hp
        e.max_hp = hp
        e.attack_speed = max(0.1, val(self.entity_ini(n, "Attack.Speed", "0.8")))
        e.strength = val(self.entity_ini(n, "Strength", "1"))
        e.defence = val(self.entity_ini(n, "Defence", "1"))
        e.aggro_range = val(self.entity_ini(n, "Aggro.Range", default_aggro))
        e.weapon_range = val(self.entity_ini(n, "Weapon.Range", "0"))
        e.move_speed = self.speed_to_pixels(val(self.entity_ini(n, "Movement.Speed", "1")))
        e.aggressive = val(self.entity_ini(n, "Aggressive", "0"))
        e.respawn_delay = val(self.entity_ini(n, "Respawn", lbstr(self.npc_respawn_delay)))
        e.in_combat = False
        e.direction = 4

    def speed_to_pixels(self, speed):
        """Speeds below 10 are tiles per second (old data), otherwise pixels per second."""
        return speed * self.tw if speed < 10 else speed

    def add_entity_of_type(self, type_name, name, x, y, misc):
        """Returns the new entity (None if nothing was added)."""
        if name == "":
            self.log("ERROR - Add.Entity with no name")
            return None
        if misc == "-":
            misc = ""
        t = normalise_type(type_name)
        if t == "MapItem":                     # misc: the quantity, then any options ("3 Id=CellarKey")
            qty = next((w for w in misc.split() if "=" not in w), "1")
            e = self.add_map_item(name, x, y, max(1, parse_quantity(qty)))
            if e is not None:
                e.npc_id = self.option_value(misc, "Id")
                e.once = self.is_once(name, misc)
            return e
        if t == "StaticObject":
            e = self.add_static_object(name, x, y)
            if e is not None:
                e.npc_id = self.option_value(misc, "Id")      # a notice's (or any object's) Id=, like an NPC's
            return e
        if t == "NPC":
            if misc == "":
                misc = self.spawn_options(name, x, y)
            return self.add_npc(name, x, y, misc, attitude_of_type(type_name))
        if t == "Missile":
            return self.new_world_entity(MISSILE, name, x, y)
        if t == "TemporaryEntity":
            return self.new_world_entity(TEMPORARY, name, x, y)
        if t == "Tile":
            self.change_tile(int(x), int(y), name, keep_decor=False)
            return None
        self.log("ERROR - Entity type '%s' not recognised (%s)" % (type_name, name))
        return None

    def remove_entity(self, e):
        """Removes a map entity (and its health bar)."""
        if e is None or not e.alive:
            return
        e.alive = False
        e.show_bar = False
        if self.player_attack_target is e:
            self.player_attack_target = None
        if self.pending_ent is e:
            self.stop_player_walk()
        if self.item_in_use is e:
            self.item_in_use = None
        if self.script_move_ent is e:
            self.script_move_ent = None
        if e in self.world:
            self.world.remove(e)
        self.force_layer_update = True

    def replace_sprite(self, e, name):
        """Gives entity e another picture (Edit.Entity NAME, Change.Player.Sprite)."""
        image, animated = self.first_image(e.type, name)
        e.name = name
        self.set_sprite_size(e, image, animated)
        self.force_layer_update = True

    def find_entity_at(self, coords, name, pid=""):
        """The map entity called name nearest to "x,y" (within 24 pixels); with pid (a place ID), the one with that
        Id= wherever it is now (name, if given, must match too)."""
        if pid:
            e = self.placed_entity(pid)
            if e is not None and (name == "" or e.name == name):
                return e
        x = val(word(coords, 1, ","))
        y = val(word(coords, 2, ","))
        best = 25
        found = None
        for etype in (MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY):
            for e in self.world:
                if e.type != etype:
                    continue
                if e.name == name or name == "":
                    d = distance(x, y, e.x, e.y)
                    d2 = distance(x, y, e.orig_x, e.orig_y)
                    if d2 < d:
                        d = d2
                    if d < best:
                        best = d
                        found = e
        return found

    # =================================================================================================================
    # Where things are
    # =================================================================================================================
    def entity_is_hidden(self, e):
        """Hidden behind a roof that is showing, or under fog of war (tree tops: only fog)."""
        if e is self.player or e.source in ("EFFECT", "SCREENFX"):
            return False
        if getattr(e, "sched_away", False):
            return True                     # (gone home for the night, or out of sight by day: daynight.py)
        cx, cy = e.cx, e.cy
        if e.type != INFRONTTILE and self.roof_covers(cx, cy):
            return True
        return self.fog_covers(cx, cy)

    def set_entity_position(self, e, x, y):
        e.x, e.y = x, y
        e.active = not self.entity_is_hidden(e)

    def display_name(self, e):
        if e is None:
            return ""
        shown = strip_digits(e.name)        # Tree001 -> Tree, Ripe_Wheat002 -> Ripe Wheat
        if e is self.player:
            shown = self.player_name
        return shown.replace("_", " ")

    # =================================================================================================================
    # Movement
    # =================================================================================================================
    def move_entity(self, e, direction):
        """Keyboard movement in a compass direction (1 N, 2 E, 4 S, 8 W, added up), scaled by the loop time."""
        if direction == 0:
            return False
        dist = e.move_speed * self.loop_delta * self.ground_speed(e)
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
        return self.try_move_entity(e, x, y)

    def move_entity_toward(self, e, tx, ty, speed):
        """Moves an entity's centre toward a point. True if it moved."""
        cx, cy = e.cx, e.cy
        d = distance(cx, cy, tx, ty)
        if d < 0.5 or speed <= 0:
            return False
        travel = min(speed * self.loop_delta * self.ground_speed(e), d)
        vx = (tx - cx) / d
        vy = (ty - cy) / d
        e.direction = self.vector_direction(vx, vy)
        moved = self.try_move_entity(e, vx * travel, vy * travel)
        if e is not self.player:
            self.animate_entity(e, moved)
        return moved

    @staticmethod
    def vector_direction(vx, vy):
        d = 0
        if vy < -0.38:
            d += 1
        if vx > 0.38:
            d += 2
        if vy > 0.38:
            d += 4
        if vx < -0.38:
            d += 8
        return d or 4

    def try_move_entity(self, e, x, y):
        """Moves by x,y if the feet stay on walkable ground, sliding along walls when possible."""
        fx, fy = e.fx, e.fy
        sx, sy = e.x, e.y
        for _ in range(4):
            if self.entity_can_stand(e, fx + x, fy + y, fx, fy):
                self.set_entity_position(e, sx + x, sy + y)
                e.anim_dist += math.hypot(x, y)
                return True
            if x != 0 and y != 0:
                if self.entity_can_stand(e, fx, fy + y, fx, fy):
                    self.set_entity_position(e, sx, sy + y)
                    e.anim_dist += abs(y)
                    return True
                if self.entity_can_stand(e, fx + x, fy, fx, fy):
                    self.set_entity_position(e, sx + x, sy)
                    e.anim_dist += abs(x)
                    return True
            x /= 2
            y /= 2
            if abs(x) < 0.25 and abs(y) < 0.25:
                break
        return False

    def entity_can_stand(self, e, x, y, old_x, old_y):
        if not self.pixel_walkable(e, x, y):
            if self.pixel_walkable(e, old_x, old_y):
                return False  # Stuck entities (e.g. after a tile change) may walk out
        if e is self.player:
            for n in self.world:
                if n.type == NPC and self.npc_is_solid(n) and self.npc_blocks(n, x, y, old_x, old_y):
                    return False
        else:
            if self.npc_is_solid(e) and self.npc_blocks(self.player, x, y, old_x, old_y):
                return False
        return True

    @staticmethod
    def npc_is_solid(e):
        if e.type == NPC and e.ai is not None:
            return e.ai.solid == 1
        return True

    @staticmethod
    def npc_blocks(e, x, y, old_x, old_y):
        """True if moving the feet from old_x,old_y to x,y walks into entity e."""
        if not e.active:
            return False
        bx, by = e.fx, e.fy
        if abs(x - bx) >= 14 or abs(y - by) >= 14:
            return False
        nd = math.hypot(x - bx, y - by)
        return nd < 14 and nd < math.hypot(old_x - bx, old_y - by)

    def animate_entity(self, e, moving):
        """Walking animation: frames <Name><Dir>a/b/c, so it faces the way it moves."""
        if not e.animated:
            return
        direction = int(e.direction)
        if self.animation_available(e.name) == 2:
            d = "8"
            old = e.image
            if len(old) >= 2 and old[-2] == "2":
                d = "2"
            if direction & 2:
                d = "2"
            if direction & 8:
                d = "8"
        else:
            d = "4"
            if direction & 1:
                d = "1"
            if direction & 4:
                d = "4"
            if direction & 2:
                d = "2"
            if direction & 8:
                d = "8"
        frame = e.frame
        if moving:
            # A step every WALK_STEP pixels walked, so the feet keep pace however fast it goes (roads, sand, a
            # quick monster); the original stepped every 150 ms whatever the speed
            if e.anim_dist >= self.WALK_STEP:
                frame = (frame + 1) % 4
                e.anim_dist = min(e.anim_dist - self.WALK_STEP, self.WALK_STEP)
        else:
            frame = 0
            e.anim_dist = 0.0
        e.frame = frame
        e.image = e.name + d + "abac"[frame]

    def change_player_sprite(self, name):
        if not self.assets.loaded(name) and not self.animation_available(name):
            self.log_missing("Player sprite", name)
            return
        self.player_sprite_base = name
        self.replace_sprite(self.player, name)
        if self.player.animated:
            self.animate_entity(self.player, False)
        self.force_layer_update = True

    # =================================================================================================================
    # Player walking (click to walk, walk then act)
    # =================================================================================================================
    def walk_player_to(self, x, y, speed, rng):
        """x,y = where the player's centre should go (around obstacles when Pathfinding=1)."""
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
        p.path_goal = self.path_goal_key(x, y, rng)
        if self.pathfinding_enabled:
            self.plan_path(p, x, y, rng, self.pf_player_budget)

    def stop_player_walk(self):
        self.player_walk_active = False
        self.pending_verb = ""
        self.pending_ent = None
        self.player.path = []

    def block_player(self):
        """Returns the player to where they were before stepping onto the current tile."""
        self.stop_player_walk()
        self.set_entity_position(self.player, self.player_entry_x, self.player_entry_y)
        self.reset_player_tile()

    def update_player_walk(self):
        p = self.player
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
        if self.pathfinding_enabled and self.pending_ent is not None:
            goal = self.path_goal_key(self.player_walk_x, self.player_walk_y, self.player_walk_range)
            if goal != p.path_goal:
                if self.loop_start >= p.path_time or p.path_time - self.loop_start > 5000:
                    p.path_goal = goal
                    self.plan_path(p, self.player_walk_x, self.player_walk_y, self.player_walk_range,
                                   self.pf_player_budget)
        self.path_steer(p, self.player_walk_x, self.player_walk_y)
        if self.move_entity_toward(p, self.pf_steer_x, self.pf_steer_y, speed):
            self.player_moved = True
        self.path_progress(p)
        self.player_walk_stuck = p.path_stuck
        if self.player_walk_stuck > 15:
            if self.pathfinding_enabled and self.player_walk_replans < 2:
                self.player_walk_replans += 1
                self.plan_path(p, self.player_walk_x, self.player_walk_y, self.player_walk_range, self.pf_player_budget)
                self.player_walk_stuck = 0
            else:
                self.finish_player_walk()

    def finish_player_walk(self):
        verb, e = self.pending_verb, self.pending_ent
        self.stop_player_walk()
        if verb and e is not None:
            self.do_action(verb, e)

    def npc_walk_to(self, e, x, y, speed, rng, forced):
        """Moves NPC e toward x,y (its centre) along a path. True if it moved."""
        if not self.pathfinding_enabled or self.grid_w == 0:
            return self.move_entity_toward(e, x, y, speed)
        goal = self.path_goal_key(x, y, rng)
        need = goal != e.path_goal or e.path_stuck > 20
        if need:
            allowed = forced or self.pf_searches < self.pf_max_searches
            if e.path_goal != "" and self.loop_start < e.path_time and e.path_time - self.loop_start <= 5000:
                allowed = False
            if allowed:
                e.path_goal = goal
                self.plan_path(e, x, y, rng, self.pf_npc_budget)
        self.path_steer(e, x, y)
        moved = self.move_entity_toward(e, self.pf_steer_x, self.pf_steer_y, speed)
        self.path_progress(e)
        return moved

    def move_player(self):
        self.player_prev_x, self.player_prev_y = self.player.x, self.player.y
        if self.keyboard_direction != 0:
            self.stop_player_walk()
            self.player_attack_target = None
            if self.move_entity(self.player, self.keyboard_direction):
                self.player_moved = True
        elif self.player_walk_active:
            self.update_player_walk()

    # =================================================================================================================
    # Inventory (self.inv: the slots in order; each an InventoryItem entity with a quantity)
    # =================================================================================================================
    def inventory_capacity(self):
        return self.inventory_columns * self.inventory_rows

    def stackable_quantity(self, name):
        return max(1, val(self.entity_ini(name, "Stackable", "1")))

    def inventory_slots_available(self, name):
        """How many more of name the inventory can hold."""
        stack = self.stackable_quantity(name)
        room = max(0, self.inventory_capacity() - len(self.inv)) * stack
        for e in self.inv:
            if e.name == name:
                room += max(0, stack - e.quantity)
        return room

    def empty_inventory_slots(self):
        return max(0, self.inventory_capacity() - len(self.inv))

    def items_held(self, name):
        return sum(e.quantity for e in self.inv if e.name == name)

    def add_inventory_item(self, name, quantity, wear=0):
        """wear: how worn it is (weapons and armour: durability.py), for each one added that isn't stacked."""
        if name == "" or quantity <= 0:
            return
        quantity = int(quantity)
        room = self.inventory_slots_available(name)
        if room - quantity < 0:
            dropped = quantity - room
            self.drop_on_floor(name, dropped)
            self.display_message("There is not enough room in your inventory (Dropping %d on the ground)." % dropped,
                                 "ERROR")
            quantity = room
            if quantity <= 0:
                return
        stack = self.stackable_quantity(name)
        for e in self.inv:
            if quantity <= 0:
                break
            if e.name == name and e.quantity < stack:
                added = min(quantity, stack - e.quantity)
                quantity -= added
                e.quantity += added
        while quantity > 0 and len(self.inv) < self.inventory_capacity():
            n = min(quantity, stack)
            quantity -= n
            e = Entity(INVENTORYITEM, name)
            self.init_entity(e, 0, 0)
            e.quantity = n
            e.wear = wear
            self.inv.append(e)
        self.check_locks(True)

    def drop_on_floor(self, name, quantity, wear=0):
        """Puts items on the ground at the player's feet; they despawn after Item.Despawn.Delay."""
        if quantity <= 0:
            return
        w, h = self.sprite_size_of(MAPITEM, name)
        x = int(self.player.fx - w / 2)
        y = int(self.player.fy - h + 4)
        e = self.add_map_item(name, x, y, quantity)
        if e is not None:
            e.wear = wear
            e.source = "DROPPED"
            home = self.entity_home(e)
            self.add_action_to_queue("REMOVE", name, "MapItem", lbstr(quantity), home, self.local_coords(home, x, y),
                                     self.item_despawn_delay)

    def remove_inventory_item(self, name, quantity):
        quantity = min(int(quantity), self.items_held(name))
        if quantity <= 0:
            return
        if self.item_in_use is not None and self.item_in_use.name == name:
            self.item_in_use = None
        for e in reversed(list(self.inv)):
            if quantity <= 0:
                break
            if e.name == name:
                removed = min(quantity, e.quantity)
                quantity -= removed
                e.quantity -= removed
                if e.quantity <= 0:
                    e.alive = False
                    self.inv.remove(e)
        self.check_locks(True)

    def inventory_slot_pos(self, index):
        """Where inventory slot index (0-based) is drawn."""
        col = index % self.inventory_columns
        row = int(index / self.inventory_columns)
        return self.inventory_x + self.inventory_gap * col, self.inventory_y + self.inventory_gap * row
