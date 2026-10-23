"""The shared world: every map, everything on them, the action queue (respawns, regrowing trees, dropped things, shop
stock), doors, the time of day and the weather. One per server; the players are Sessions (session.py).

Coordinates are global pixels on a level: map "X,Y,Z" covers x = X*sw .. X*sw+sw-1, y = Y*sh .. Y*sh+sh-1 on level Z.
Map files, scripts, the action queue and the saves still say map-local coordinates; they are turned into global ones
where they come in."""
import heapq
import logging
import math
import random

from dragonsword.lb import (val, word, field, trim, lbstr, distance, strip_digits, parse_quantity, wildcard_match,
                            clock_ms, clock_seconds, rnd, random_number)

from .data import GameData
from .entity import (Entity, NPCAI, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, INFRONTTILE,
                     TYPE_NAMES, normalise_type, attitude_of_type, parse_attitude)
from .maps import MapData
from .homes import Homes
from .farming import Farms
from .market import Market
from .npcs import NPCMixin

log = logging.getLogger("dragonsword.world")

PF_DIRS = ((0, -1, 10), (1, 0, 10), (0, 1, 10), (-1, 0, 10), (1, -1, 14), (1, 1, 14), (-1, 1, 14), (-1, -1, 14))
DOOR_REACH = 34
DOOR_SHUT_MS = 1500
HEAR_NEAR, HEAR_FAR = 96.0, 600.0


class World(NPCMixin):
    def __init__(self, root):
        self.data = d = GameData(root)
        self.root = root
        self.sw, self.sh, self.tw, self.th, self.xt, self.yt = d.sw, d.sh, d.tw, d.th, d.xt, d.yt
        self.now = clock_ms()
        self.dt = 0.0
        self.maps = {}
        self.by_pos = {}
        self.ents = []
        self.by_uid = {}
        self.sessions = {}              # player name -> Session
        self.action_queue = []
        self.map_npcs = {}              # map -> [(name, x, y, options)] its NPC lines (for respawns)
        self.doors_open = {}            # (map, x, y) -> [closed tile, when last someone was near]
        self.door_check_at = 0
        self.missiles = []
        self.objects_dirty = set()      # maps whose objects' footprints must be worked out again
        self.day_time0 = 0.3
        self.day_start_ms = self.now
        self.weather = None
        self.lightning_next = 0
        self.last_queue_check = 0
        self.active = set()             # (mx, my, mz) of maps someone is near: their NPCs think
        self.tile_listeners = []        # callables (map, x, y) when a tile changes
        self.load_maps()
        self.homes = Homes(self)        # players' homesteads (their maps join self.maps as they're made)
        self.farms = Farms(self)        # what's growing in tilled soil
        self.market = Market(self)      # the players' market stalls

    # =================================================================================================================
    # Maps
    # =================================================================================================================
    def load_maps(self):
        for name in self.data.map_names():
            if len(name.split(",")) != 3:
                continue
            m = MapData(self.data, name)
            self.maps[name] = m
            self.by_pos[(m.mx, m.my, m.mz)] = m
        for m in self.maps.values():
            self.spawn_map_entities(m)

    def map_at(self, z, x, y):
        """The map that global pixel x,y on level z is on (None = no map there)."""
        return self.by_pos.get((math.floor(x / self.sw), math.floor(y / self.sh), int(z)))

    def map_named(self, name):
        return self.maps.get(trim(name).replace(" ", ""))

    def neighbours(self, m):
        """The map and the (up to) 8 round it, on its level."""
        out = []
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                n = self.by_pos.get((m.mx + i, m.my + j, m.mz))
                if n is not None:
                    out.append(n)
        return out

    def tile_at(self, z, x, y):
        """(map, tile x, tile y) of global pixel x,y, or (None, 0, 0)."""
        m = self.map_at(z, x, y)
        if m is None:
            return None, 0, 0
        return m, int((x - m.ox) / self.tw) + 1, int((y - m.oy) / self.th) + 1

    def cell_names(self, m, x, y, viewer=None):
        """(tile, decor) of map m's tile x,y as the viewer sees it (their own changes and open gates over the world's)."""
        if viewer is not None:
            o = viewer.cell_override.get((m.name, x, y))
            if o is not None:
                return o[0], o[1]
        c = m.cell(x, y)
        return m.tile[c], m.decor[c]

    # =================================================================================================================
    # Changing tiles (shared)
    # =================================================================================================================
    def change_tile(self, m, x, y, spec, keep_decor=True):
        if m is None or not m.change_cell(int(x), int(y), spec, keep_decor):
            return False
        for f in self.tile_listeners:
            f(m, int(x), int(y))
        return True

    def change_all_tiles(self, m, source, target):
        for y in range(1, self.yt + 1):
            for x in range(1, self.xt + 1):
                c = m.cell(x, y)
                for name in (m.tile[c], m.decor[c]):
                    if name and (name == source or strip_digits(name) == source):
                        self.change_tile(m, x, y, target, keep_decor=False)
                        break

    # =================================================================================================================
    # Entities
    # =================================================================================================================
    def entity_home(self, e):
        return e.map

    def local_coords(self, m, x, y):
        return "%s,%s" % (lbstr(int(x - m.ox)), lbstr(int(y - m.oy)))

    def init_entity(self, e, z, x, y, home=None):
        d = self.data
        image, animated = d.first_image(e.type, e.name)
        e.image, e.animated = image, animated
        e.w, e.h = d.size_of(image)
        e.z = int(z)
        if home is None:
            m = self.map_at(z, x, y)
            home = m.name if m else ""
        e.map = home
        e.use_words = d.entity_ini(e.name, "Use.Words", "")
        e.x, e.y = x, y
        e.orig_x, e.orig_y = x, y
        if e.animated:
            self.animate_entity(e, False)

    def count_type(self, etype):
        return sum(1 for e in self.ents if e.type == etype)

    def new_world_entity(self, etype, name, z, x, y, owner=None, home=None):
        limit = self.data.type_limits.get(etype)
        if limit is not None and self.count_type(etype) >= limit * 20:      # (the whole world, not one screen)
            log.error("No room for another %s (%s)", TYPE_NAMES[etype], name)
            return None
        e = Entity(etype, name)
        e.owner = owner
        self.init_entity(e, z, x, y, home)
        self.ents.append(e)
        self.by_uid[e.uid] = e
        if etype == STATICOBJECT:
            self.object_moved(e)
        return e

    def remove_entity(self, e):
        if e is None or not e.alive:
            return
        e.alive = False
        e.show_bar = False
        if e in self.ents:
            self.ents.remove(e)
        self.by_uid.pop(e.uid, None)
        if e.type == STATICOBJECT:
            self.object_moved(e)
        for s in self.sessions.values():
            s.entity_gone(e)

    def set_entity_position(self, e, x, y):
        if e.type == STATICOBJECT and (int(x), int(y)) != (int(e.x), int(e.y)):
            self.object_moved(e)
            e.x, e.y = x, y
            self.object_moved(e)
            return
        e.x, e.y = x, y

    def visible_to(self, e, viewer):
        """Does this player see (and can they touch) entity e? Not another player's own things, not a one-time item
        they've already taken, not something their quest took away."""
        if e.owner is not None and e.owner is not viewer:
            return False
        if e.private_to is not None:
            if self.now < e.public_at:
                if viewer is not e.private_to:
                    return False
            else:
                e.private_to = None
        if viewer is not None:
            if e.uid in viewer.hidden_uids:
                return False
            if e.type == MAPITEM and e.once and viewer.once_taken(e):
                return False
        return True

    def add_map_item(self, name, z, x, y, quantity, owner=None, home=None):
        e = self.new_world_entity(MAPITEM, name, z, x, y, owner, home)
        if e is None:
            return None
        e.quantity = max(1, int(quantity))
        e.orig_quantity = e.quantity
        return e

    @staticmethod
    def option_value(options, key):
        for pair in str(options).replace("\t", " ").split():
            if pair.upper().startswith(key.upper() + "="):
                return pair[len(key) + 1:]
        return ""

    def is_once(self, name, options):
        v = self.option_value(options, "Once") or self.data.entity_ini(name, "Once", "0")
        return trim(v) in ("1", "yes", "Yes", "true", "True")

    def once_key(self, e):
        """How a one-time item is remembered: its Id, or map@x,y (where its map line puts it)."""
        if e.npc_id:
            return e.npc_id
        m = self.maps.get(e.map)
        if m is None:
            return ""
        return "%s@%d,%d" % (e.map, int(e.orig_x - m.ox), int(e.orig_y - m.oy))

    def add_static_object(self, name, z, x, y, owner=None, home=None):
        return self.new_world_entity(STATICOBJECT, name, z, x, y, owner, home)

    def npc_attitude(self, name, options, attitude=""):
        v = parse_attitude(self.option_value(options, "Attitude"))
        if v is not None:
            return v
        for v in (parse_attitude(attitude) if attitude else None,
                  parse_attitude(self.data.entity_ini(name, "Attitude", ""))):
            if v is not None:
                return v
        return attitude_of_type(self.data.entity_ini(name, "Type", "")) == "Bad"

    def add_npc(self, name, z, x, y, options, attitude="", owner=None, home=None):
        e = self.new_world_entity(NPC, name, z, x, y, owner, home)
        if e is None:
            return None
        e.npc_id = self.option_value(options, "Id")
        e.hostile = self.npc_attitude(name, options, attitude)
        self.load_npc_stats(e)
        self.init_npc_ai(e, options)
        return e

    def npc_key(self, e):
        """Which NPC this is, for Set.NPC.Attitude and the saves: its Id=, else map@x,y of its map line."""
        if e.npc_id:
            return e.npc_id
        m = self.maps.get(e.map)
        if m is None:
            return "@%d,%d" % (int(e.orig_x), int(e.orig_y))
        return "%s@%s" % (e.map, self.local_coords(m, e.orig_x, e.orig_y))

    def load_npc_stats(self, e):
        d = self.data
        n = e.name
        hp = max(1, val(d.entity_ini(n, "Hitpoints", "5")))
        e.hp = e.max_hp = hp
        e.attack_speed = max(0.1, val(d.entity_ini(n, "Attack.Speed", "0.8")))
        e.strength = val(d.entity_ini(n, "Strength", "1"))
        e.defence = val(d.entity_ini(n, "Defence", "1"))
        e.aggro_range = val(d.entity_ini(n, "Aggro.Range", "60" if e.hostile else "0"))
        e.weapon_range = val(d.entity_ini(n, "Weapon.Range", "0"))
        e.move_speed = d.speed_to_pixels(val(d.entity_ini(n, "Movement.Speed", "1")))
        e.aggressive = val(d.entity_ini(n, "Aggressive", "0"))
        e.respawn_delay = val(d.entity_ini(n, "Respawn", lbstr(d.npc_respawn_delay)))
        e.in_combat = False
        e.direction = 4

    def set_npc_hostile(self, e, hostile):
        """Turns an NPC into a foe (for everyone) or a friend."""
        e.hostile = hostile
        if hostile:
            e.aggressive = 1
            e.aggro_range = max(e.aggro_range, 100)
        elif e.in_combat and e.ai is not None:
            self.npc_give_up(e, e.ai)

    def hostile_for(self, e, s):
        """Is NPC e a foe of player s? Their own Set.NPC.Attitude / quest edits first, else what it is for everyone."""
        if s is not None:
            o = s.attitude_of(e)
            if o is not None:
                return o
        return e.hostile

    def stat_for(self, e, s, field_name):
        """NPC e's strength / defence / aggressive / aggro_range as player s meets it (their quest may have changed
        it for them alone)."""
        value = getattr(e, field_name)
        if s is not None:
            o = s.ent_overrides.get(e.uid)
            if o and field_name in o:
                value = o[field_name]
            if field_name in ("aggressive", "aggro_range") and not e.hostile and s.attitude_of(e) is True:
                value = max(value, 1 if field_name == "aggressive" else 100)     # (made a foe just for them)
        return value

    def add_entity_of_type(self, type_name, name, z, x, y, misc, owner=None, home=None):
        if name == "":
            return None
        if misc == "-":
            misc = ""
        t = normalise_type(type_name)
        if t == "MapItem":
            qty = next((w for w in misc.split() if "=" not in w), "1")
            e = self.add_map_item(name, z, x, y, max(1, parse_quantity(qty)), owner, home)
            if e is not None:
                e.npc_id = self.option_value(misc, "Id")
                e.once = self.is_once(name, misc)
            return e
        if t == "StaticObject":
            e = self.add_static_object(name, z, x, y, owner, home)
            if e is not None:
                e.npc_id = self.option_value(misc, "Id")
            return e
        if t == "NPC":
            if misc == "":
                misc = self.spawn_options(name, z, x, y)
            return self.add_npc(name, z, x, y, misc, attitude_of_type(type_name), owner, home)
        if t == "Missile":
            return self.new_world_entity(MISSILE, name, z, x, y, owner, home)
        if t == "TemporaryEntity":
            return self.new_world_entity(TEMPORARY, name, z, x, y, owner, home)
        if t == "Tile":
            m, tx, ty = self.tile_at(z, x, y)
            self.change_tile(m, tx, ty, name, keep_decor=False)
            return None
        log.error("Entity type '%s' not recognised (%s)", type_name, name)
        return None

    def spawn_options(self, name, z, x, y):
        """The Options of a map's NPC line for name spawned at global pixel x,y."""
        m = self.map_at(z, x, y)
        if m is None:
            return ""
        lx, ly = x - m.ox, y - m.oy
        for n, nx, ny, opts in self.map_npcs.get(m.name, ()):
            if n == name and abs(nx - lx) <= 2 and abs(ny - ly) <= 2:
                return opts
        return ""

    def spawn_map_entities(self, m):
        """A map's NPCs, items and objects from its file."""
        npcs = self.map_npcs[m.name] = []
        for etype, ename, x, y, misc in m.entity_lines:
            if etype in ("GoodNPC", "BadNPC") and "ATTITUDE=" not in misc.upper():
                misc = trim(misc + " Attitude=" + attitude_of_type(etype))
            if etype in ("NPC", "GoodNPC", "BadNPC"):
                npcs.append((ename, x, y, misc))
            e = self.add_entity_of_type(etype, ename, m.mz, x + m.ox, y + m.oy, misc, home=m.name)
            if e is not None:
                e.source = "MAP"

    def find_entity_at(self, z, x, y, name, pid="", viewer=None):
        """The entity called name nearest to global x,y (within 24 pixels); with pid (a place ID), the one with that
        Id= wherever it is now."""
        if pid:
            e = self.placed_entity(pid, viewer)
            if e is not None and (name == "" or e.name == name):
                return e
        best = 25
        found = None
        for etype in (MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY):
            for e in self.ents:
                if e.type != etype or e.z != z or (viewer is not None and not self.visible_to(e, viewer)):
                    continue
                if viewer is None and e.owner is not None:
                    continue
                if e.name == name or name == "":
                    dd = min(distance(x, y, e.x, e.y), distance(x, y, e.orig_x, e.orig_y))
                    if dd < best:
                        best = dd
                        found = e
        return found

    def placed_entity(self, pid, viewer=None):
        pid = pid.upper()
        for e in self.ents:
            if e.npc_id and e.npc_id.upper() == pid and e.alive and (viewer is None or self.visible_to(e, viewer)):
                return e
        return None

    def ents_near(self, z, x, y, radius):
        r2 = radius * radius
        return [e for e in self.ents if e.z == z and (e.cx - x) ** 2 + (e.cy - y) ** 2 <= r2]

    # ----- walking frames
    WALK_STEP = 14

    def animate_entity(self, e, moving):
        if not e.animated:
            return
        direction = int(e.direction)
        base = e.name
        if self.data.animation_available(base) == 2:
            d = "8"
            if len(e.image) >= 2 and e.image[-2] == "2":
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
            if e.anim_dist >= self.WALK_STEP:
                frame = (frame + 1) % 4
                e.anim_dist = min(e.anim_dist - self.WALK_STEP, self.WALK_STEP)
        else:
            frame = 0
            e.anim_dist = 0.0
        e.frame = frame
        e.image = base + d + "abac"[frame]

    def replace_sprite(self, e, name):
        image, animated = self.data.first_image(e.type, name)
        e.name = name
        e.image, e.animated = image, animated
        e.w, e.h = self.data.size_of(image)

    # =================================================================================================================
    # Objects' footprints on the walk grid
    # =================================================================================================================
    def object_moved(self, e):
        m = self.map_at(e.z, e.x, e.y)
        if m is not None:
            for n in self.neighbours(m):
                self.objects_dirty.add(n.name)

    def update_object_blocks(self):
        if not self.objects_dirty:
            return
        dirty, self.objects_dirty = self.objects_dirty, set()
        d = self.data
        res, tw, th = d.walk_res, self.tw, self.th
        for name in dirty:
            m = self.maps.get(name)
            if m is None:
                continue
            new = {}
            x0, y0 = m.ox - 2 * tw, m.oy - 2 * th
            x1, y1 = m.ox + self.sw + tw, m.oy + self.sh + th
            for e in self.ents:
                if e.type != STATICOBJECT or not e.alive or e.z != m.mz or e.owner is not None:
                    continue
                if not (x0 <= e.x <= x1 and y0 <= e.y <= y1):
                    continue
                fp = d.object_footprint(e.name, e.w, e.h)
                if fp is None:
                    continue
                cols, rows, data = fp
                cw, ch = e.w / cols, e.h / rows
                for i, v in enumerate(data):
                    if v != "0":
                        continue
                    for fx in (0.25, 0.75):
                        for fy in (0.25, 0.75):
                            gx = e.x + (i % cols + fx) * cw - m.ox
                            gy = e.y + (i // cols + fy) * ch - m.oy
                            if not (0 <= gx < self.sw and 0 <= gy < self.sh):
                                continue
                            tx, ty = int(gx // tw) + 1, int(gy // th) + 1
                            p = int((gx % tw) * res / tw) + res * int((gy % th) * res / th)
                            new.setdefault((tx, ty), set()).add(p)
            if new != m.object_blocks:
                m.object_blocks = new
                m.grid_dirty()

    # =================================================================================================================
    # Walking
    # =================================================================================================================
    def lock_closed_for(self, m, lk, mover):
        """Is lock lk shut for whoever is walking (a Session, or None for NPCs: locks stay shut for them)?"""
        if mover is None:
            return True
        return mover.lock_closed(m, lk)

    def pixel_walkable(self, z, x, y, mover=None):
        """Can the feet of mover (a Session, or None for an NPC) stand at global pixel x,y on level z?"""
        m = self.map_at(z, x, y)
        if m is None:
            return False
        lx, ly = x - m.ox, y - m.oy
        tx, ty = int(lx / self.tw) + 1, int(ly / self.th) + 1
        override = None
        if mover is not None:
            lk = m.lock_at.get((tx, ty))
            if lk is not None and self.lock_closed_for(m, lk, mover):
                mover.lock_bumped = (m, lk)
                return False
            o = mover.cell_override.get((m.name, tx, ty))
            if o is not None:
                override = o[2]
        elif (tx, ty) in m.lock_at:
            return False
        return m.local_walkable(lx, ly, override)

    def ground_speed(self, e):
        if e.ai is not None and e.ai.flying:
            return 1
        m, tx, ty = self.tile_at(e.z, e.fx, e.fy)
        if m is None or not m.inside(tx, ty):
            return 1
        s = m.speed[m.cell(tx, ty)]
        return s if s > 0 else 1

    @staticmethod
    def npc_is_solid(e):
        if e.type == NPC and e.ai is not None:
            return e.ai.solid == 1
        return True

    @staticmethod
    def blocks(bx, by, x, y, old_x, old_y):
        if abs(x - bx) >= 14 or abs(y - by) >= 14:
            return False
        nd = math.hypot(x - bx, y - by)
        return nd < 14 and nd < math.hypot(old_x - bx, old_y - by)

    def entity_can_stand(self, e, x, y, old_x, old_y, mover=None):
        """mover: the Session whose player e is (None for NPCs)."""
        z = e.z
        if not self.pixel_walkable(z, x, y, mover):
            if self.pixel_walkable(z, old_x, old_y, mover):
                return False                        # (stuck entities, e.g. after a tile change, may walk out)
        if mover is not None:
            for n in self.ents:
                if (n.type == NPC and n.z == z and n.active and self.npc_is_solid(n) and
                        self.visible_to(n, mover) and self.blocks(n.fx, n.fy, x, y, old_x, old_y)):
                    return False
        elif self.npc_is_solid(e):
            for s in self.sessions.values():
                p = s.player
                if (p.z == z and s.player_visible and p.hp > 0 and self.visible_to(e, s) and
                        self.blocks(p.fx, p.fy, x, y, old_x, old_y)):
                    return False
        return True

    def try_move_entity(self, e, x, y, mover=None):
        fx, fy = e.fx, e.fy
        sx, sy = e.x, e.y
        for _ in range(4):
            if self.entity_can_stand(e, fx + x, fy + y, fx, fy, mover):
                self.set_entity_position(e, sx + x, sy + y)
                e.anim_dist += math.hypot(x, y)
                return True
            if x != 0 and y != 0:
                if self.entity_can_stand(e, fx, fy + y, fx, fy, mover):
                    self.set_entity_position(e, sx, sy + y)
                    e.anim_dist += abs(y)
                    return True
                if self.entity_can_stand(e, fx + x, fy, fx, fy, mover):
                    self.set_entity_position(e, sx + x, sy)
                    e.anim_dist += abs(x)
                    return True
            x /= 2
            y /= 2
            if abs(x) < 0.25 and abs(y) < 0.25:
                break
        return False

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

    def move_entity_toward(self, e, tx, ty, speed, mover=None):
        cx, cy = e.cx, e.cy
        dd = distance(cx, cy, tx, ty)
        if dd < 0.5 or speed <= 0:
            return False
        travel = min(speed * self.dt * self.ground_speed(e), dd)
        vx = (tx - cx) / dd
        vy = (ty - cy) / dd
        e.direction = self.vector_direction(vx, vy)
        moved = self.try_move_entity(e, vx * travel, vy * travel, mover)
        if mover is None:
            self.animate_entity(e, moved)
        return moved

    # =================================================================================================================
    # Line of sight
    # =================================================================================================================
    def tile_los_at(self, z, x, y):
        m, tx, ty = self.tile_at(z, x, y)
        if m is None or not m.inside(tx, ty):
            return 1
        return m.los[m.cell(tx, ty)]

    def in_line_of_sight(self, z, x1, y1, x2, y2):
        d = distance(x1, y1, x2, y2)
        if d < 1:
            return True
        tw, th = self.tw, self.th
        start = (math.floor(x1 / tw), math.floor(y1 / th))
        finish = (math.floor(x2 / tw), math.floor(y2 / th))
        steps = int(d / 4) + 1
        for i in range(1, steps + 1):
            px = x1 + (x2 - x1) * i / steps
            py = y1 + (y2 - y1) * i / steps
            t = (math.floor(px / tw), math.floor(py / th))
            if t == start or t == finish:
                continue
            if self.tile_los_at(z, px, py) == 0:
                return False
        return True

    # =================================================================================================================
    # Pathfinding: A* over the maps' walk grids (half-tile cells), global cell coordinates on the level
    # =================================================================================================================
    def grid_walkable(self, z, gx, gy, mover=None):
        cell = self.data.grid_cell
        gw, gh = int(self.sw / cell), int(self.sh / cell)
        m = self.by_pos.get((math.floor(gx / gw), math.floor(gy / gh), z))
        if m is None:
            return 0
        lx, ly = gx - m.mx * gw, gy - m.my * gh
        tx, ty = int(lx * cell / self.tw) + 1, int(ly * cell / self.th) + 1
        lk = m.lock_at.get((tx, ty))
        if lk is not None and self.lock_closed_for(m, lk, mover):
            return 0
        if mover is not None and (m.name, tx, ty) in mover.cell_override:
            px, py = m.ox + lx * cell + cell / 2, m.oy + ly * cell + cell / 2
            return 1 if self.pixel_walkable(z, px, py, mover) else 0
        return m.get_grid()[ly * gw + lx]

    def grid_line_walkable(self, z, x1, y1, x2, y2, mover=None):
        d = distance(x1, y1, x2, y2)
        steps = int(d / 6) + 1
        cell = self.data.grid_cell
        last_x = math.floor(x1 / cell)
        last_y = math.floor(y1 / cell)
        gwk = self.grid_walkable
        for i in range(1, steps + 1):
            cx = math.floor((x1 + (x2 - x1) * i / steps) / cell)
            cy = math.floor((y1 + (y2 - y1) * i / steps) / cell)
            if cx != last_x or cy != last_y:
                if gwk(z, cx, cy, mover) == 0:
                    return False
                if cx != last_x and cy != last_y:
                    if gwk(z, cx, last_y, mover) == 0 or gwk(z, last_x, cy, mover) == 0:
                        return False
                last_x, last_y = cx, cy
        return True

    def path_goal_key(self, x, y, rng):
        cell = self.data.grid_cell
        return "%d,%d,%s" % (int(x / cell), int(y / cell), lbstr(rng))

    def plan_path(self, e, target_x, target_y, rng, budget, mover=None):
        """A path for e so its centre gets within rng of the target (A*, 8 directions, no corner cutting, then string
        pulling). Waypoints (centres) go in e.path (empty = walk straight). False if there's no way."""
        e.path = []
        e.path_best = None
        e.path_stuck = 0
        e.path_time = self.now + 400
        if not self.data.pathfinding_enabled:
            return False
        z = e.z
        feet_offset = e.fy - e.cy
        sx, sy = e.fx, e.fy
        tx, ty = target_x, target_y + feet_offset
        d = distance(sx, sy, tx, ty)
        if d <= rng:
            return True
        reach = (d - max(0, rng - 2)) / d
        if self.grid_line_walkable(z, sx, sy, sx + (tx - sx) * reach, sy + (ty - sy) * reach, mover):
            return True
        cell = self.data.grid_cell
        gwk = self.grid_walkable
        radius = max(rng - 2, int(cell * 0.75))
        r2 = radius * radius
        range_cost = int(radius / cell * 10)
        scx, scy = math.floor(sx / cell), math.floor(sy / cell)
        if gwk(z, scx, scy, mover) == 0:
            best_d = 999999
            new_start = None
            for ddx, ddy, _ in PF_DIRS:
                mx, my = scx + ddx, scy + ddy
                if gwk(z, mx, my, mover) == 1:
                    dd = abs(mx * cell + cell / 2 - sx) + abs(my * cell + cell / 2 - sy)
                    if dd < best_d:
                        best_d, new_start = dd, (mx, my)
            if new_start is None:
                e.path_time = self.now + 2000
                return False
            scx, scy = new_start
        gcx, gcy = math.floor(tx / cell), math.floor(ty / cell)

        def octile(x, y):
            hx = abs(x - gcx)
            hy = abs(y - gcy)
            return 10 * hx + 4 * hy if hx > hy else 10 * hy + 4 * hx

        start = (scx, scy)
        g_cost = {start: 0}
        parent = {start: None}
        done = set()
        hm = octile(scx, scy)
        best_node, best_h = start, hm
        heap = [(max(0, hm - range_cost), 0, start)]
        counter = 0
        found = None
        expansions = 0
        half = cell / 2
        walk_cache = {}

        def walkable(x, y):
            k = (x, y)
            v = walk_cache.get(k)
            if v is None:
                v = walk_cache[k] = gwk(z, x, y, mover)
            return v

        while heap:
            _, _, n = heapq.heappop(heap)
            if n in done:
                continue
            done.add(n)
            nx, ny = n
            ddx = nx * cell + half - tx
            ddy = ny * cell + half - ty
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
            for k, (sdx, sdy, cost) in enumerate(PF_DIRS):
                mx, my = nx + sdx, ny + sdy
                m = (mx, my)
                if m in done or walkable(mx, my) != 1:
                    continue
                if k >= 4 and (walkable(mx, ny) == 0 or walkable(nx, my) == 0):
                    continue
                ng = g + cost
                old = g_cost.get(m)
                if old is None or ng < old:
                    g_cost[m] = ng
                    parent[m] = n
                    counter += 1
                    heapq.heappush(heap, (ng + max(0, octile(mx, my) - range_cost) * 1.2, counter, m))
        if found is None:
            e.path_time = self.now + 2000
            if best_node == start:
                return False
            found = best_node
        cells = []
        n = found
        while n is not None and len(cells) < 19000:
            cells.append(n)
            n = parent.get(n)
        corners = []
        total = len(cells)
        for i in range(total - 2, -1, -1):
            keep = True
            if i > 0:
                a, b, c = cells[i + 1], cells[i], cells[i - 1]
                if (b[0] - a[0], b[1] - a[1]) == (c[0] - b[0], c[1] - b[1]):
                    keep = False
            if keep:
                corners.append((cells[i][0] * cell + half, cells[i][1] * cell + half))
        path = []
        ax, ay = sx, sy
        j = 0
        while j < len(corners):
            k = j
            while k < len(corners) - 1:
                if not self.grid_line_walkable(z, ax, ay, corners[k + 1][0], corners[k + 1][1], mover):
                    break
                k += 1
            path.append((corners[k][0], corners[k][1] - feet_offset))
            ax, ay = corners[k]
            j = k + 1
        e.path = path
        return True

    @staticmethod
    def path_steer(e, target_x, target_y):
        """e's next waypoint (dropping those it has reached), or the target."""
        if not e.path:
            return target_x, target_y
        cx, cy = e.cx, e.cy
        while e.path:
            wx, wy = e.path[0]
            reached = abs(cx - wx) < 3 and abs(cy - wy) < 3
            if e.path_stuck > 8 and abs(cx - wx) < 12 and abs(cy - wy) < 12:
                reached = True
            if not reached:
                return wx, wy
            e.path.pop(0)
            e.path_best = None
            e.path_stuck = 0
        return target_x, target_y

    @staticmethod
    def path_progress(e, steer_x, steer_y):
        d = distance(e.cx, e.cy, steer_x, steer_y)
        if e.path_best is None:
            e.path_best = d
            e.path_stuck = 0
        elif d < e.path_best - 0.25:
            e.path_best = d
            e.path_stuck = 0
        else:
            e.path_stuck += 1

    @staticmethod
    def forget_path(e):
        e.path = []
        e.path_goal = ""
        e.path_stuck = 0
        e.path_best = None

    def grid_region_at(self, z, x, y):
        m = self.map_at(z, x, y)
        if m is None:
            return None
        cell = self.data.grid_cell
        regions = m.get_regions()
        gx, gy = int((x - m.ox) / cell), int((y - m.oy) / cell)
        if not (0 <= gx < m.gw and 0 <= gy < m.gh):
            return None
        return (m.name, regions[gy * m.gw + gx])

    # =================================================================================================================
    # Doors (Tiles.ini Open.Tile): a door opens as someone comes to it and shuts behind them
    # =================================================================================================================
    def update_doors(self):
        now = self.now
        if 0 <= now - self.door_check_at < 100:
            return
        self.door_check_at = now
        near = {}                                       # (map, x, y) -> who's there (a Session, or None for an NPC)
        movers = [(s.player, s) for s in self.sessions.values() if s.in_world()]
        movers += [(e, None) for e in self.ents if e.type == NPC and e.alive and e.active and
                   (math.floor(e.x / self.sw), math.floor(e.y / self.sh), e.z) in self.active]
        for e, s in movers:
            fx, fy = e.fx, e.fy
            for ddy in (-self.th, 0, self.th):
                for ddx in (-self.tw, 0, self.tw):
                    m, tx, ty = self.tile_at(e.z, fx + ddx, fy + ddy)
                    if m is None or not m.inside(tx, ty):
                        continue
                    if distance(fx, fy, m.ox + (tx - 0.5) * self.tw, m.oy + (ty - 0.5) * self.th) <= DOOR_REACH:
                        key = (m.name, tx, ty)
                        if key not in near or s is not None:
                            near[key] = s
        for key, s in near.items():
            if key in self.doors_open:
                self.doors_open[key][1] = now
                continue
            m = self.maps[key[0]]
            x, y = key[1], key[2]
            name = m.tile[m.cell(x, y)]
            o = self.data.door_open_tile(name)
            if not o:
                continue
            lk = m.lock_at.get((x, y))
            if lk is not None and (lk.opened or self.lock_closed_for(m, lk, s)):
                continue                    # (locked for whoever's there, or a gate its lock draws open and shut)
            self.doors_open[key] = [name, now]
            self.change_tile(m, x, y, o)
            self.sound("Door", m.mz, m.ox + (x - 0.5) * self.tw, m.oy + (y - 0.5) * self.th)
        for key, (closed, t) in list(self.doors_open.items()):
            if key not in near and not 0 <= now - t < DOOR_SHUT_MS:
                del self.doors_open[key]
                m = self.maps[key[0]]
                if m.tile[m.cell(key[1], key[2])] == self.data.door_open_tile(closed):
                    self.change_tile(m, key[1], key[2], closed)

    # =================================================================================================================
    # Events for the players
    # =================================================================================================================
    def hearers(self, z, x, y, radius=HEAR_FAR):
        for s in self.sessions.values():
            p = s.player
            if s.in_world() and p.z == z and distance(p.cx, p.cy, x, y) <= radius:
                yield s

    def sound(self, name, z, x, y, only=None):
        """A sound made at global x,y: everyone near enough hears it (quieter further off), or only that player."""
        if not trim(name):
            return
        for s in ([only] if only is not None else self.hearers(z, x, y)):
            s.emit({"t": "sound", "name": name, "x": int(x), "y": int(y)})

    def fx(self, ev, z, x, y, owner=None):
        """A visual effect at x,y for everyone who can see it (or just the owner of a personal thing)."""
        targets = [owner] if owner is not None else self.hearers(z, x, y, self.sw * 1.6)
        for s in targets:
            s.emit(ev)

    def fx_splat(self, kind, amount, e, owner=None):
        if e is None:
            return
        self.fx({"t": "splat", "kind": kind, "n": int(amount), "uid": e.uid, "x": int(e.cx),
                 "y": int(e.y + e.h * 0.25) + random_number(-3, 3), "dx": random_number(-5, 5)}, e.z, e.cx, e.cy, owner)

    def fx_anim(self, base, z, x, y, ms, owner=None):
        self.fx({"t": "anim", "base": base, "x": int(x), "y": int(y), "ms": int(ms)}, z, x, y, owner)

    def fx_nudge(self, e, dx, dy, ms, owner=None):
        if e is None or (dx == 0 and dy == 0):
            return
        self.fx({"t": "nudge", "uid": e.uid, "dx": dx, "dy": dy, "ms": ms}, e.z, e.cx, e.cy, owner)

    @staticmethod
    def fx_away(src, e):
        dx = e.cx - src.cx
        return 3 if dx > 4 else (-3 if dx < -4 else 0)

    @staticmethod
    def fx_away_y(src, e):
        dy = e.cy - src.cy
        return 2 if dy > 4 else (-2 if dy < -4 else 0)

    # ----- missiles: they fly (here and in the browsers), and land when they get there
    def fx_shot(self, src, image, target, tag, shooter=None):
        """A missile flies from src to target (entities); on arrival missile_arrive(tag, target, shooter)."""
        w, h = self.data.size_of(image) if self.data.loaded(image) else (16, 16)
        f = {"image": image, "x": src.cx - w / 2, "y": src.cy - h / 2, "w": w, "h": h, "target": target, "tag": tag,
             "shooter": shooter, "z": src.z, "until": self.now + 3000}
        self.missiles.append(f)
        self.fx({"t": "shot", "image": image, "from": src.uid, "to": target.uid, "x": int(src.cx), "y": int(src.cy)},
                src.z, src.cx, src.cy, src.owner)

    def update_missiles(self):
        for f in list(self.missiles):
            t = f["target"]
            if t is None or not t.alive or self.now >= f["until"]:
                self.missiles.remove(f)
                continue
            tx, ty = t.cx - f["w"] / 2, t.cy - f["h"] / 2
            dd = distance(f["x"], f["y"], tx, ty)
            travel = 420 * self.dt
            if dd <= travel + 4:
                self.missiles.remove(f)
                self.missile_arrive(f["tag"], t, f["shooter"])
                continue
            f["x"] += (tx - f["x"]) * travel / dd
            f["y"] += (ty - f["y"]) * travel / dd

    def missile_arrive(self, tag, target, shooter):
        if isinstance(tag, Entity):                     # an NPC's shot at a player
            s = shooter
            if s is not None and s.in_world():
                s.npc_shot_hits(tag)
        elif shooter is not None and shooter.in_world():
            if tag == "ARROW":
                shooter.player_strike(target, True)
            else:
                shooter.spell_hit(tag, target)

    # =================================================================================================================
    # The action queue: ACTION <TAB> Name <TAB> Type <TAB> Misc <TAB> Map <TAB> X,Y <TAB> Seconds <TAB> Due
    # (X,Y in the map's own pixels; tile x,y for CHANGE.TILE)
    # =================================================================================================================
    def add_action_to_queue(self, action, name, type_name, misc, map_name, coords, seconds):
        if len(self.action_queue) >= 3000:
            log.error("Action queue is full")
            return
        if misc == "":
            misc = "-"
        self.action_queue.append("\t".join([action, name, type_name, misc, map_name, coords, lbstr(seconds),
                                            lbstr(clock_seconds() + seconds)]))

    def set_queue_quantity(self, action, name, map_name, coords, quantity):
        for i, entry in enumerate(self.action_queue):
            if (field(entry, 1, "\t") == action and field(entry, 2, "\t") == name and field(entry, 5, "\t") == map_name
                    and field(entry, 6, "\t") == coords):
                parts = entry.split("\t")
                while len(parts) < 8:
                    parts.append("")
                parts[3] = lbstr(quantity)
                self.action_queue[i] = "\t".join(parts[:8])

    def remove_action_from_queue(self, pattern):
        keep = []
        for entry in self.action_queue:
            due = field(entry, 8, "\t")
            arguments = entry[:len(entry) - len(due) - 1]
            if (wildcard_match(arguments, pattern) or wildcard_match(entry, pattern) or
                    wildcard_match(field(entry, 2, "\t"), pattern)):
                continue
            keep.append(entry)
        self.action_queue = keep

    def run_action_queue(self):
        now = clock_seconds()
        i = 0
        while i < len(self.action_queue):
            if val(field(self.action_queue[i], 8, "\t")) <= now:
                if self.do_queue_entry(i):
                    del self.action_queue[i]
                    continue
            i += 1

    def postpone_queue_entry(self, n, seconds):
        entry = self.action_queue[n]
        due = field(entry, 8, "\t")
        self.action_queue[n] = entry[:len(entry) - len(due)] + lbstr(clock_seconds() + seconds)

    def do_queue_entry(self, n):
        """True when the entry is finished with."""
        entry = self.action_queue[n]
        action = field(entry, 1, "\t").upper()
        name = field(entry, 2, "\t")
        type_name = field(entry, 3, "\t")
        misc = field(entry, 4, "\t")
        map_name = field(entry, 5, "\t")
        coords = field(entry, 6, "\t")
        x = val(word(coords, 1, ","))
        y = val(word(coords, 2, ","))
        if action in ("ADD.SHOP.ITEM", "REMOVE.SHOP.ITEM"):
            for s in self.sessions.values():
                s.shop_restocked(type_name, name, val(misc) if action == "ADD.SHOP.ITEM" else -val(misc))
            return True
        m = self.map_named(map_name)
        if m is None:
            return True
        if action == "CHANGE.TILE":
            for s in self.sessions.values():
                p = s.player
                if s.in_world() and p.z == m.mz:
                    pm, ptx, pty = self.tile_at(p.z, p.fx, p.fy)
                    if pm is m and (ptx, pty) == (int(x), int(y)) and self.data.spec_blocks(name):
                        self.postpone_queue_entry(n, 2)
                        return False
            self.change_tile(m, int(x), int(y), name, keep_decor=False)
            return True
        gx, gy = x + m.ox, y + m.oy
        if action in ("ADD", "ADD.ENTITY"):
            if normalise_type(type_name) == "NPC":
                for s in self.sessions.values():
                    p = s.player
                    if s.in_world() and p.z == m.mz and distance(p.cx, p.cy, gx + 16, gy + 16) < 32:
                        self.postpone_queue_entry(n, 3)
                        return False
            if self.find_entity_at(m.mz, gx, gy, name) is None or normalise_type(type_name) == "Tile":
                e = self.add_entity_of_type(type_name, name, m.mz, gx, gy, misc, home=m.name)
                if e is not None:
                    e.source = "MAP"
        elif action in ("REMOVE", "REMOVE.ENTITY"):
            if normalise_type(type_name) != "Tile":
                self.remove_entity(self.find_entity_at(m.mz, gx, gy, name))
        elif action == "SET.QUANTITY":
            e = self.find_entity_at(m.mz, gx, gy, name)
            if e is not None and e.type == MAPITEM:
                e.quantity = max(e.quantity, e.orig_quantity)      # (a partly-taken stack is whole again)
        else:
            log.error("Unknown queue action '%s'", action)
        return True

    def apply_saved_queue(self):
        """After a restart: the world as the queue says it was (things waiting to respawn gone, dropped things back,
        partly-taken stacks short, tiles changed for a while still changed)."""
        for entry in list(self.action_queue):
            m = self.map_named(field(entry, 5, "\t"))
            action = field(entry, 1, "\t").upper()
            if m is None:
                continue
            name = field(entry, 2, "\t")
            type_name = field(entry, 3, "\t")
            misc = field(entry, 4, "\t")
            coords = field(entry, 6, "\t")
            x = val(word(coords, 1, ","))
            y = val(word(coords, 2, ","))
            if action == "CHANGE.TILE":
                if misc not in ("-", ""):
                    m.change_cell(int(x), int(y), misc, keep_decor=False)
                continue
            gx, gy = x + m.ox, y + m.oy
            if action in ("ADD", "ADD.ENTITY"):
                if normalise_type(type_name) != "Tile":
                    self.remove_entity(self.find_entity_at(m.mz, gx, gy, name))
            elif action in ("REMOVE", "REMOVE.ENTITY"):
                if normalise_type(type_name) != "Tile" and self.find_entity_at(m.mz, gx, gy, name) is None:
                    e = self.add_entity_of_type(type_name, name, m.mz, gx, gy, misc, home=m.name)
                    if e is not None:
                        e.source = "DROPPED"
            elif action == "SET.QUANTITY":
                e = self.find_entity_at(m.mz, gx, gy, name)
                if e is not None:
                    e.quantity = max(1, int(val(misc)))

    # =================================================================================================================
    # The time of day (one clock for everyone)
    # =================================================================================================================
    def day_fraction(self):
        if self.data.day_seconds <= 0:
            return self.day_time0
        return (self.day_time0 + (self.now - self.day_start_ms) / 1000.0 / self.data.day_seconds) % 1.0

    def set_day_fraction(self, t):
        self.day_time0 = t % 1.0
        self.day_start_ms = self.now
        for s in self.sessions.values():
            s.emit(self.clock_event())

    def dn(self, section, key, default=""):
        from dragonsword import ini
        return ini.read(section, key, str(default), self.data.data_file("DayNight.ini"))

    def is_night(self, t=None):
        t = self.day_fraction() if t is None else t
        return t >= val(self.dn("Night", "From", "0.83")) or t < val(self.dn("Night", "To", "0.21"))

    def clock_event(self):
        return {"t": "clock", "day": self.day_fraction(), "secs": self.data.day_seconds,
                "on": bool(self.data.day_night_enabled)}

    # =================================================================================================================
    # The weather (Data\\Weather.ini): one sky for everyone; what it does where you are depends on the place's climate
    # =================================================================================================================
    def weather_path(self):
        return self.data.data_file("Weather.ini")

    def weather_on(self):
        import os
        return val(self.data.config_read("Gameplay", "Weather", "1")) == 1 and os.path.exists(self.weather_path())

    def weather_set(self, key, default=""):
        from dragonsword import ini
        return ini.read("Weather", key, str(default), self.weather_path())

    def weather_of(self, kind, key, default=""):
        from dragonsword import ini
        return ini.read("Kind." + kind, key, str(default), self.weather_path())

    def climate_odds(self, clim):
        from dragonsword import ini
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

    def climate(self, map_name, z):
        """The climate on a map: its Ambient.ini sound if Weather.ini has a [Climate.<it>]; None underground."""
        from dragonsword import ini
        if z != 0:
            return None
        cache = self.data.cache("climate")
        if map_name not in cache:
            amb = trim(ini.read("Maps", map_name, "", self.data.data_file("Ambient.ini")))
            cache[map_name] = amb if amb and ini.section("Climate." + amb, self.weather_path()) else ""
        return cache[map_name]

    def weather_kind(self, map_name, z):
        w = self.weather
        clim = self.climate(map_name, z)
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
        if not self.weather_on():
            if self.weather is not None:
                self.weather = None
                self.weather_changed()
            return
        now = self.now
        w = self.weather
        if w is None:
            first = val(self.weather_set("First", "60"))
            w = self.weather = {"kind": "clear", "level": 0.0, "next": now + first * 1000, "fading": False}
        dt = max(0.0, min(0.1, self.dt))
        if now >= w["next"] and not w["fading"]:
            w["fading"] = True
            self.weather_changed()
        if w["fading"]:
            w["level"] = max(0.0, w["level"] - dt / max(0.1, val(self.weather_set("Fade.Out", "12"))))
            if w["level"] <= 0:
                rng = random.Random(now)
                odds = self.climate_odds("")
                kinds = list(odds)
                w["kind"] = rng.choices(kinds, [odds[k] for k in kinds])[0]
                lo, hi = self.span(self.weather_set("Lasts", "120-300"), (120, 300))
                w["next"] = now + int(rng.uniform(lo, hi) * 1000)
                w["fading"] = False
                self.weather_changed()
                for s in self.sessions.values():
                    if s.in_world() and s.player.z == 0:
                        kind, _ = self.weather_kind(s.screen_name, 0)
                        words = self.weather_of(kind, "Message", "")
                        if words:
                            s.display_message(words, "INFO")
        elif w["kind"] != "clear":
            w["level"] = min(1.0, w["level"] + dt / max(0.1, val(self.weather_set("Fade.In", "15"))))
        self.weather_lightning(now)

    @staticmethod
    def span(text, default):
        try:
            parts = [float(p) for p in str(text).replace(" ", "").split("-") if p != ""]
        except ValueError:
            return default
        return (parts[0], parts[-1]) if parts else default

    def weather_changed(self):
        for s in self.sessions.values():
            s.weather_dirty = True

    def weather_lightning(self, now):
        if now < self.lightning_next:
            return
        lo, hi = self.span(self.weather_set("Lightning.Every", "7-18"), (7, 18))
        tlo, thi = self.span(self.weather_set("Thunder.After", "0.4-2.2"), (0.4, 2.2))
        self.lightning_next = now + int(random.uniform(lo, hi) * 1000)
        thunder = int(random.uniform(tlo, thi) * 1000)
        for s in self.sessions.values():
            if not s.in_world() or s.player.z != 0:
                continue
            kind, level = self.weather_kind(s.screen_name, 0)
            if val(self.weather_of(kind, "Lightning", "0")) == 1 and level >= 0.5:
                s.emit({"t": "lightning", "thunder": thunder,
                        "sound": trim(self.weather_set("Thunder.Sound", "Thunder"))})

    def weather_state_for(self, s):
        if not s.in_world():
            return {"t": "weather", "kind": "clear", "level": 0, "fading": False}
        kind, level = self.weather_kind(s.screen_name, s.player.z)
        w = self.weather or {}
        return {"t": "weather", "kind": kind, "level": round(level, 3), "fading": bool(w.get("fading")),
                "fade_in": val(self.weather_set("Fade.In", "15")), "fade_out": val(self.weather_set("Fade.Out", "12"))}

    # =================================================================================================================
    # Every tick
    # =================================================================================================================
    def update_active(self):
        act = set()
        for s in self.sessions.values():
            if not s.in_world():
                continue
            p = s.player
            mx, my = math.floor(p.x / self.sw), math.floor(p.y / self.sh)
            for j in (-1, 0, 1):
                for i in (-1, 0, 1):
                    act.add((mx + i, my + j, p.z))
        self.active = act

    def tick(self, dt, now=None):
        """now: the time in clock_ms (tests run the world faster than the clock)."""
        self.now = clock_ms() if now is None else now
        self.dt = max(0.0, min(0.1, dt))
        self.update_active()
        self.update_object_blocks()
        for s in list(self.sessions.values()):
            s.tick_before_npcs()
        self.update_npcs()
        self.update_missiles()
        for s in list(self.sessions.values()):
            s.tick_after_npcs()
        if self.now - self.last_queue_check >= 250 or self.now < self.last_queue_check:
            self.last_queue_check = self.now
            self.run_action_queue()
        self.update_doors()
        self.farms.tick()
        self.weather_tick()
