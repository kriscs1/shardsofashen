"""NPC movement, as the desktop game's npc.py (see there for the states), for many players: an NPC is a foe or a friend
of each player (their own Set.NPC.Attitude), picks a fight with the nearest player it's a foe of, chases its foe (the
player it's fighting), faces whoever is near. Only NPCs on maps near a player think."""
import math

from ashen.lb import val, word, trim, distance, random_number, rnd, is_number, strip_digits, parse_quantity

from .entity import NPC, MAPITEM, NPCAI, AI_IDLE, AI_ROAM, AI_PATROL, AI_CHASE, AI_FLEE, AI_RETURN, TYPE_NAMES
from .player_combat import CombatMixin
from .remnants import death_remnants, make_remnant, LIVING, REMNANT
from .disguise import disguise_of

BLINK_HEARD = 256.0     # (a Dark Mage's jump: from as near as an animal's call)

PF_NPC_BUDGET = 400
FLOOR_ROAM = 0.3            # (one roaming a Zone on more than one level: how often its next spot is up or down)


LYING = ("Curl", "Lie", "Sleep")                       # (poses lying down: still, no turning about, sat up from)


class Area(list):
    """An NPC's Zone or Chase area, in pixels: [x0, y0, x1, y1] round it all, and its parts when it's more than one
    rectangle (Zone=3,4,8,9/8,5,12,6: an L, a ring round a pond...; the map editor paints them tile by tile)."""
    parts = None

    def has(self, x, y):
        if not (self[0] <= x <= self[2] and self[1] <= y <= self[3]):
            return False
        return self.parts is None or any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in self.parts)

    def pick(self):
        """One of its rectangles, the bigger ones the likelier (a random spot of it is a random spot of the area)."""
        if not self.parts:
            return self
        total = sum((r[2] - r[0] + 1) * (r[3] - r[1] + 1) for r in self.parts)
        k = rnd() * total
        for r in self.parts:
            k -= (r[2] - r[0] + 1) * (r[3] - r[1] + 1)
            if k <= 0:
                return r
        return self.parts[-1]

class NPCMixin:
    def update_npcs(self):
        sw, sh = self.sw, self.sh
        self.pf_searches = 0
        players = [s for s in self.sessions.values() if s.in_world()]
        self.players_all = players
        self.drawers = [s for s in players if s.draw_reach() > 0]      # (Shieldwall: monsters near come for them)
        pmap = {}                                       # (mx, my, z) -> the players on it (nearest_player looks round)
        for s in players:
            p = s.player
            pmap.setdefault((math.floor(p.x / sw), math.floor(p.y / sh), p.z), []).append(s)
        self.players_by_map, self.players_round_cache = pmap, {}
        by_map = {}                                     # (mx, my, z) -> its live NPCs, for hunting (npc_prey)
        for e in self.ents:
            if e.type == NPC and e.alive and e.ai is not None:
                by_map.setdefault((math.floor(e.x / sw), math.floor(e.y / sh), e.z), []).append(e)
        self.npcs_by_map = by_map
        # (only the maps someone's near think: the rest wait, as they always have)
        for e in [e for key in self.active for e in by_map.get(key, ())]:
            if not e.alive or e.ai is None:
                continue
            a = e.ai
            near = self.nearest_player(e, players)
            now_turn = True
            if not e.in_combat:
                # Out of everyone's sight: bigger, rarer steps (the same speed for much less work)
                if near is None or abs(e.cx - near[0].player.cx) > sw * 0.75 or abs(e.cy - near[0].player.cy) > sh * 0.75:
                    a.skip_delta += self.dt
                    if a.skip_delta < 0.06:
                        now_turn = False
            if now_turn:
                was = self.dt
                if a.skip_delta > 0:
                    self.dt = min(0.1, a.skip_delta)
                    a.skip_delta = 0
                if not getattr(e, "script_moving", False):
                    self.update_npc(e, players, near)
                self.dt = was
            self.update_npc_healthbar(e)

    SEEN_CLOSE = 44         # (right beside it: it knows you're there, whichever way it looks)
    ROUSE_HEAR = 160        # (how far a fight's din carries to a monster of Hearing 1)

    def npc_spotted(self, e, a, s):
        """A watchman (Spotted.Script=) has seen s: its script runs for them (a cargo found and taken), once in a
        while; it doesn't fight, and goes on with its round."""
        rest = s.spotted_rest if hasattr(s, "spotted_rest") else {}
        if self.now < rest.get(e.uid, 0):
            return
        rest[e.uid] = self.now + 8000
        s.spotted_rest = rest
        s.spotted_by(e)
        s.start_script(a.spotted, False)

    def npc_listen(self, e, a, s, d):
        """A monster hears s (their noise, as far as its Hearing carries it, nothing solid between). One that looks
        one way turns to look (if they're in its sight now, it's seen them next time it looks); one that sees all round
        comes for them. True if it came."""
        p = s.player
        if d > s.noise_radius() * getattr(a, "hearing", 1.0) or not self.in_line_of_sight(e.z, e.cx, e.cy, p.cx, p.cy):
            return False
        cone = getattr(a, "cone", 0)
        if cone <= 0 or cone >= 360:
            if not self.in_chase_area(a, p.fx, p.fy):
                return False
            e.target = s
            self.npc_start_fight(e, a, s, d)
            self.npc_alarm(e, a, s)
            s.spotted_by(e)
            return True
        before = e.direction
        self.npc_face(e, e.cx, e.cy, p.cx, p.cy)
        if e.direction != before and self.now - getattr(a, "heard_at", -10 ** 9) > 4000:
            a.heard_at = self.now
            a.turn_at = max(a.turn_at, self.now + 4000)       # (it looks that way a while before it turns back)
            s.heard_by(e)
        return False

    def npc_sees(self, e, a, s, d):
        """Does NPC e see player s, d away? Walls, tents and stacked cargo hide you (line of sight); one with a
        Sight.Cone (or Cone=) sees only that wide a wedge in front of it, so you can creep up behind."""
        p = s.player
        if not self.in_line_of_sight(e.z, e.cx, e.cy, p.cx, p.cy):
            return False
        cone = getattr(a, "cone", 0)
        if cone <= 0 or cone >= 360 or d < self.SEEN_CLOSE:
            return True
        cone *= s.cone_factor()                                  # (Stealth: it sees less of you)
        dr = e.direction or 4
        fx = (1 if dr & 2 else 0) - (1 if dr & 8 else 0)
        fy = (1 if dr & 4 else 0) - (1 if dr & 1 else 0)
        if fx == 0 and fy == 0:
            return True
        ang = math.degrees(math.atan2(p.cy - e.cy, p.cx - e.cx) - math.atan2(fy, fx))
        ang = (ang + 180) % 360 - 180
        return abs(ang) <= cone / 2

    def npc_alarm(self, e, a, s):
        """e has seen s: its Group= (the camp it belongs to) all come for them."""
        group = getattr(a, "group", "")
        if not group or s.silent():                             # (hushed: it can't shout)
            return
        said = False
        for o in self.ents:
            oa = o.ai
            if (o is e or o.type != NPC or not o.alive or oa is None or getattr(oa, "group", "") != group or
                    o.in_combat or o.z != e.z or not self.hostile_for(o, s)):
                continue
            od = distance(o.cx, o.cy, s.player.cx, s.player.cy)
            if od > 480:
                continue
            o.target = s
            self.npc_start_fight(o, oa, s, od, rouse=False)
            said = True
        if said:
            s.display_message("The %s shouts: \"Intruder!\" The whole camp is after you!" % s.display_name(e), "DAMAGE")
            self.sound("Alarm" if self.data.loaded("Alarm") else "Denied", e.z, e.cx, e.cy)

    def players_round(self, e):
        """The players on e's map and the eight round it, this tick (nobody further off matters to it)."""
        key = (math.floor(e.x / self.sw), math.floor(e.y / self.sh), e.z)
        got = self.players_round_cache.get(key)
        if got is None:
            pmap = self.players_by_map
            got = [s for i in (-1, 0, 1) for j in (-1, 0, 1) for s in pmap.get((key[0] + i, key[1] + j, key[2]), ())]
            self.players_round_cache[key] = got
        return got

    def nearest_player(self, e, players, want=None):
        """(session, distance) of the nearest player on e's level who sees it (want(session) must be true too).
        Everyone in the world (players: this tick's list): only those on the maps round it are looked at."""
        best = None
        ex, ey = e.cx, e.cy
        if players is getattr(self, "players_all", None):
            players = self.players_round(e)
        for s in players:
            p = s.player
            if p.z != e.z:
                continue
            d = math.hypot(ex - p.cx, ey - p.cy)        # (the cheap test first: the rest only for a nearer one)
            if best is not None and d >= best[1]:
                continue
            if p.hp <= 0 or not self.visible_to(e, s) or s.sleeping():
                continue
            if want is not None and not want(s):
                continue
            best = (s, d)
        return best

    def update_npc_healthbar(self, e):
        e.show_bar = (e.hp < e.max_hp or e.in_combat) and e.active

    # =================================================================================================================
    # Setting up
    # =================================================================================================================
    def init_npc_ai(self, e, options):
        a = NPCAI()
        e.ai = a
        d = self.data
        n = e.name
        a.solid = 0 if d.entity_ini(n, "Solid", "1") == "0" else 1
        a.flees = trim(d.entity_ini(n, "Flees", "0")) == "1"         # (prey: runs from whoever hits it, never fights)
        a.swims = trim(d.entity_ini(n, "Swims", "0")) == "1"         # (an otter, a seal: at home in the water too)
        layer = trim(d.entity_ini(n, "Layer", "")).upper()
        a.under = 1 if layer == "UNDER" else 0
        a.flying = 1 if layer == "OVER" else 0
        options = trim(options.replace("\t", " "))
        if options == "-":
            options = ""
        a.options = options
        roam = max(0, val(d.entity_ini(n, "Roam.Radius", "3")))
        chase = max(0, val(d.entity_ini(n, "Chase.Radius", "4")))
        walk = val(d.entity_ini(n, "Walk.Speed", "0.5"))
        if walk <= 0:
            walk = 0.5
        a.walk_speed = max(4, min(1, walk) * e.move_speed)
        pause = d.entity_ini(n, "Pause", "1-4")
        zone = chase_r = patrol = home_area = bed = nap = bed_level = home_level = zone_levels = ""
        stand = ping = 0
        # (stealth: which way it looks, how wide it sees, who it raises the alarm with, when it's a friend)
        a.cone = max(0, val(d.entity_ini(n, "Sight.Cone", "0")))
        a.hearing = max(0.0, val(d.entity_ini(n, "Hearing", "1")))     # (how far your noise carries to it: build_senses.py)
        a.group = a.friendly_if = a.fixed_pose = a.spotted = ""
        a.disguise = disguise_of(d, n)                 # (Friend.If.Wearing=: their robe fools them - disguise.py)
        a.absorbs = val(d.entity_ini(n, "Absorbs.Remnants", "0")) != 0   # (it heals by remnants near it)
        a.absorb_at = 0
        a.poses = [trim(p) for p in d.entity_ini(n, "States", "").split(",") if trim(p)]   # (Sit,Lie: when it stops)
        a.fidgets = [trim(p) for p in d.entity_ini(n, "Fidgets", "").split(",") if trim(p)]   # (Stretch: now and then)
        a.fidget_until, a.fidget_at, a.pose_back = 0, self.now + random_number(5000, 30000), ""
        a.pose_next, a.pose_next_at = "", 0           # (lying down: it sits first, then lies; npc_pose_step)
        a.hunts = {trim(h).upper() for h in d.entity_ini(n, "Hunts", "").split(",") if trim(h)}   # (Hunts=Rabbit,Sheep)
        a.hunt_at = self.now + random_number(2000, 8000)
        a.call = trim(d.entity_ini(n, "Calls", ""))                   # (a frog's croak, a seal's bark, now and then)
        a.call_at = self.now + random_number(5000, 40000)
        a.growl, a.growl_at = trim(d.entity_ini(n, "Growl", "")), 0     # (a goblin's snarl as it comes for you)
        e.npc_foe = None
        k = 1
        while word(options, k) != "":
            pair = word(options, k)
            eq = pair.find("=")
            if eq > 0:
                value = trim(pair[eq + 1:])
                key = trim(pair[:eq]).upper()
                if key == "ZONE":
                    zone = value
                elif key == "CHASE":
                    chase_r = value
                elif key == "PATROL":
                    patrol = value
                elif key == "PATROLMODE":
                    if value.upper() == "PINGPONG":
                        ping = 1
                elif key == "PAUSE":
                    if value:
                        pause = value
                elif key == "STAND":
                    if val(value) != 0:
                        stand = 1
                elif key == "FACE":                  # (N, E, S, W - or 1, 2, 4, 8 - the way it looks, standing)
                    face = {"N": 1, "E": 2, "S": 4, "W": 8}.get(value.upper()[:1], int(val(value)) or 4)
                    e.direction = a.face = face
                elif key == "TURN":                  # (seconds between glances about; 0: only to a sound)
                    a.turn_every = max(0.0, val(value))
                elif key == "CONE":
                    a.cone = max(0, val(value))
                elif key == "GROUP":
                    a.group = value.upper()
                elif key == "SCHEDULE":                # (this one's hours, not its kind's: Always = never goes home)
                    a.schedule = value
                elif key == "FRIENDLY.IF":
                    a.friendly_if = value
                elif key == "SPOTTED.SCRIPT":          # (a watchman: seeing you runs this, for you, and it doesn't fight)
                    a.spotted = value
                elif key in ("HOME", "ROOST"):         # (where it is while its hours keep it in: a house, a coop)
                    home_area = value
                elif key == "BED":                     # (its own bed, x,y: asleep in it at night)
                    bed = value
                elif key == "BED.LEVEL":               # (its bed's on another level: upstairs, up the stairs to it)
                    bed_level = value
                elif key == "HOME.LEVEL":
                    home_level = value
                elif key == "ZONE.LEVELS":             # (its Zone on these levels too, the same tiles: 0,1 - up the
                    zone_levels = value                  #  stairs or a ladder to roam the room above)
                elif key == "STATE":                   # (how it always rests: State=Sit)
                    a.fixed_pose = value
                elif key == "NAP":                     # (a spot it hops up onto to curl up: Nap=13,7, the throne)
                    nap = value
            k += 1
        home = self.maps.get(e.map)
        a.home_ox = home.ox if home else math.floor(e.x / self.sw) * self.sw
        a.home_oy = home.oy if home else math.floor(e.y / self.sh) * self.sh
        spawn_tx = int((e.fx - a.home_ox) / self.tw) + 1
        spawn_ty = int((e.fy - a.home_oy) / self.th) + 1
        a.way = []
        k = 1
        xt, yt = self.xt, self.yt
        while word(patrol, k, "/") != "" and len(a.way) < 16:
            point = word(patrol, k, "/")
            if "," in point:
                a.way.append((min(2 * xt, max(1 - xt, int(val(word(point, 1, ","))))),
                              min(2 * yt, max(1 - yt, int(val(word(point, 2, ",")))))))
            k += 1
        a.way_index = 1
        a.way_step = 1
        a.pingpong = ping
        zone_parts = self.npc_rects(zone)
        if zone_parts:
            x1, y1, x2, y2 = (min(r[0] for r in zone_parts), min(r[1] for r in zone_parts),
                              max(r[2] for r in zone_parts), max(r[3] for r in zone_parts))
        else:
            x1 = x2 = spawn_tx
            y1 = y2 = spawn_ty
            if a.way:
                for wx, wy in a.way:
                    x1, x2 = min(x1, wx), max(x2, wx)
                    y1, y2 = min(y1, wy), max(y2, wy)
            else:
                x1, y1, x2, y2 = x1 - roam, y1 - roam, x2 + roam, y2 + roam
                if roam == 0:
                    stand = 1
        self.npc_set_rect(a, 0, x1, y1, x2, y2, zone_parts)
        chase_parts = self.npc_rects(chase_r)
        if chase_parts:
            self.npc_set_rect(a, 1, min(r[0] for r in chase_parts), min(r[1] for r in chase_parts),
                              max(r[2] for r in chase_parts), max(r[3] for r in chase_parts), chase_parts)
        else:
            self.npc_set_rect(a, 1, min(x1, x2) - chase, min(y1, y2) - chase, max(x1, x2) + chase, max(y1, y2) + chase)
        a.home = None
        home_parts = self.npc_rects(home_area)
        if home_parts:                                  # (its Home: the zone it has while its hours keep it in)
            a.day_zone, a.day_chase = a.zone, a.chase
            self.npc_set_rect(a, 0, min(r[0] for r in home_parts), min(r[1] for r in home_parts),
                              max(r[2] for r in home_parts), max(r[3] for r in home_parts), home_parts)
            a.home, a.zone = a.zone, a.day_zone
        a.bed, a.bed_from, a.asleep, a.bed_tries = None, None, False, 0
        a.spawn_at = (e.fx, e.fy)                       # (where it was put: back out, it's somewhere it can walk from)
        if word(bed, 2, ",") and is_number(word(bed, 1, ",")) and is_number(word(bed, 2, ",")):
            a.bed = (a.home_ox + (val(word(bed, 1, ",")) - 1) * self.tw, a.home_oy + (val(word(bed, 2, ",")) - 1) * self.th)
        a.base_z = e.z                                  # (its own level, where it's put: its days)
        a.bed_z = int(val(bed_level)) if a.bed and is_number(bed_level) else e.z
        a.home_z = int(val(home_level)) if a.home and is_number(home_level) else e.z
        a.zone_levels = {e.z} | {int(val(v)) for v in zone_levels.split(",") if is_number(trim(v))}
        a.goal_z = e.z
        a.levels = a.bed_z != e.z or a.home_z != e.z or len(a.zone_levels) > 1   # (a bed upstairs, a home in the
                                                                                    #  cellar: it climbs to them)
        a.stair_tries = 0
        p_min = val(word(pause, 1, "-"))
        p_max = p_min
        if "-" in pause:
            p_max = val(word(pause, 2, "-"))
        p_min = max(0, p_min)
        p_max = max(p_min, p_max)
        a.pause_min, a.pause_max = p_min, p_max
        a.stand = stand
        a.resume = AI_PATROL if (a.way and stand == 0) else AI_ROAM
        a.back_x, a.back_y = e.cx, e.cy
        a.calm_until = 0
        a.goal_x, a.goal_y = a.back_x, a.back_y
        a.nap = a.nap_from = None
        a.napping = a.nap_walk = False
        if word(nap, 2, ",") and is_number(word(nap, 1, ",")) and is_number(word(nap, 2, ",")):
            a.nap = (a.home_ox + (val(word(nap, 1, ",")) - 0.5) * self.tw, a.home_oy + (val(word(nap, 2, ",")) - 0.5) * self.th)
            if distance(e.cx, e.cy, *a.nap) < 20:            # (put down on it: asleep there already)
                a.napping, a.nap_from = True, (e.x, e.y + self.th)
        a.state = AI_IDLE
        a.timer = self.now + int(rnd() * (p_max * 1000 + 1500))
        a.turn_at = a.timer + 1
        e.pose = "Curl" if a.napping else a.fixed_pose
        if a.napping:
            a.timer = self.now + random_number(40000, 120000)
            a.turn_at = a.timer + 1
        if e.pose:
            self.animate_entity(e, False)                     # (drawn as it rests from the start: curled, sitting)

    @staticmethod
    def npc_rect_valid(rect):
        if word(rect, 4, ",") == "" or word(rect, 5, ",") != "":
            return False
        return all(is_number(trim(word(rect, k, ","))) for k in range(1, 5))

    @classmethod
    def npc_rects(cls, text):
        """"x1,y1,x2,y2", or several joined by / (tiles) -> [(x1, y1, x2, y2)], or [] if any of them isn't one."""
        parts = [trim(p) for p in str(text or "").split("/") if trim(p)]
        if not parts or not all(cls.npc_rect_valid(p) for p in parts):
            return []
        return [tuple(val(word(p, i, ",")) for i in range(1, 5)) for p in parts]

    def npc_set_rect(self, a, which, x1, y1, x2, y2, parts=None):
        xt, yt, tw, th = self.xt, self.yt, self.tw, self.th

        def px(x1, y1, x2, y2):
            left = min(2 * xt, max(1 - xt, int(min(x1, x2))))
            right = min(2 * xt, max(1 - xt, int(max(x1, x2))))
            top = min(2 * yt, max(1 - yt, int(min(y1, y2))))
            bottom = min(2 * yt, max(1 - yt, int(max(y1, y2))))
            return [(left - 1) * tw + a.home_ox, (top - 1) * th + a.home_oy, right * tw - 1 + a.home_ox,
                    bottom * th - 1 + a.home_oy]
        rect = Area(px(x1, y1, x2, y2))
        if parts and len(parts) > 1:                   # (more than one rectangle: an L, a ring...)
            rect.parts = [px(*r) for r in parts]
        if which == 0:
            a.zone = rect
        else:
            a.chase = rect

    @staticmethod
    def in_chase_area(a, x, y):
        c = a.chase
        return c.has(x, y) if isinstance(c, Area) else c[0] <= x <= c[2] and c[1] <= y <= c[3]

    @staticmethod
    def in_zone(a, x, y):
        z = a.zone
        return z.has(x, y) if isinstance(z, Area) else z[0] <= x <= z[2] and z[1] <= y <= z[3]

    # =================================================================================================================
    # Thinking
    # =================================================================================================================
    def npc_walk_to(self, e, x, y, speed, rng, forced):
        if not self.data.pathfinding_enabled:
            return self.move_entity_toward(e, x, y, speed)
        goal = self.path_goal_key(x, y, rng)
        need = goal != e.path_goal or e.path_stuck > 20
        if need:
            allowed = forced or self.pf_searches < 3
            if e.path_goal != "" and self.now < e.path_time and e.path_time - self.now <= 5000:
                allowed = False
            if allowed:
                self.pf_searches += 1
                e.path_goal = goal
                self.plan_path(e, x, y, rng, PF_NPC_BUDGET)
        sx, sy = self.path_steer(e, x, y)
        moved = self.move_entity_toward(e, sx, sy, speed)
        self.path_progress(e, sx, sy)
        return moved

    def update_npc(self, e, players, near):
        a = e.ai
        if a.call and not e.in_combat and (self.now >= a.call_at or self.now < a.call_at - 600000):
            a.call_at = self.now + random_number(15000, 60000)
            self.sound(a.call, e.z, e.cx, e.cy, radius=256.0)   # (a croak from the reeds, a bark off the rocks)
        if e.follow is not None:
            self.npc_follow(e, a)
            return
        if self.schedule_npc(e, near):
            return
        now = self.now
        cx, cy = e.cx, e.cy
        state = a.state
        if e.slow_until is not None:
            if now >= e.slow_until or now < e.slow_until - 60000:
                e.move_speed = e.normal_speed
                e.slow_until = None
                e.normal_speed = None
        if e.frozen_until is not None:
            if e.frozen_until - 60000 <= now < e.frozen_until:
                return                                  # (frozen, or stunned: it does nothing till it thaws)
            e.frozen_until = None
        if a.absorbs and self.npc_absorb(e, a):
            return                                      # (off to the remnants lying near it, to heal by them)
        # Its foe: the player it's fighting; else the nearest it's a foe of (to pick a fight with)
        foe = e.target if (e.in_combat and e.target is not None and e.target.in_world() and
                           e.target.player.z == e.z and e.target.player.hp > 0) else None
        if e.in_combat and foe is None and state in (AI_CHASE, AI_FLEE):
            self.npc_give_up(e, a)
            return
        if state not in (AI_CHASE, AI_FLEE):
            if e.in_combat and foe is not None:
                self.npc_start_fight(e, a, foe, distance(cx, cy, foe.player.cx, foe.player.cy))
                state = a.state
            elif now >= a.calm_until or now < a.calm_until - 10000:
                cand = self.nearest_player(e, players, lambda s: s.player_visible and self.hostile_for(e, s))
                if cand is not None:
                    s, d = cand
                    if self.stat_for(e, s, "aggressive") == 1 and d <= self.stat_for(e, s, "aggro_range") * s.sight_factor():
                        if self.in_chase_area(a, s.player.fx, s.player.fy):
                            if a.spotted and self.npc_sees(e, a, s, d):
                                self.npc_spotted(e, a, s)
                            elif not a.spotted and self.npc_sees(e, a, s, d):
                                e.target = s
                                self.npc_start_fight(e, a, s, d)
                                state = a.state
                                foe = s
                                self.npc_alarm(e, a, s)
                                s.spotted_by(e)
                    if foe is None and self.stat_for(e, s, "aggressive") == 1 and self.npc_listen(e, a, s, d):
                        state = a.state
                        foe = s
        if state not in (AI_CHASE, AI_FLEE) and not e.in_combat and (e.npc_foe is not None or a.hunts):
            if self.npc_versus_npc(e, a):
                return
            state = a.state
        if state == AI_CHASE and self.drawers and foe is not None:
            drawn = self.shieldwall_draw(e, a, foe)
            if drawn is not None:
                foe = e.target = drawn
        if state == AI_CHASE:
            s = foe
            p = s.player if s is not None else None
            give_up = s is None or not e.in_combat or not s.player_visible
            d = distance(cx, cy, p.cx, p.cy) if p is not None else 9999
            if not give_up and self.npc_blink(e, a, s, d):
                return
            near_r = CombatMixin.melee_reach(e)
            reach = near_r + e.weapon_range
            shot = ""
            if not give_up and d > near_r + 8:
                shot = self.data.entity_ini(e.name, "Missile", "")
                if shot and not self.in_line_of_sight(e.z, cx, cy, p.cx, p.cy):
                    shot = ""
                    reach = near_r
            if not give_up and d <= reach:
                self.npc_face(e, cx, cy, p.cx, p.cy)
                a.progress_time = now
                a.best_d = d
                if now - e.last_attack >= e.attack_speed * 1000 or now < e.last_attack:
                    e.last_attack = now
                    if shot:
                        s.npc_shoot(e, shot)
                    else:
                        s.npc_attack_player(e)
                return
            if not give_up:
                if not self.in_chase_area(a, p.fx, p.fy):
                    give_up = True
                if d > max(self.stat_for(e, s, "aggro_range"), 100) * 3:
                    give_up = True
            if not give_up:
                if d < a.best_d - 4:
                    a.best_d = d
                    a.progress_time = now
                if now - a.progress_time > 5000 or now < a.progress_time:
                    give_up = True
            if not give_up:
                old_x, old_y = e.x, e.y
                was_inside = self.in_chase_area(a, e.fx, e.fy)
                self.npc_walk_to(e, p.cx, p.cy, e.move_speed, 32 + e.weapon_range, False)
                if was_inside and not self.in_chase_area(a, e.fx, e.fy):
                    self.set_entity_position(e, old_x, old_y)
                    give_up = True
            if give_up:
                self.npc_give_up(e, a)
        elif state == AI_FLEE:
            p = foe.player if foe is not None else None
            if now >= a.timer or now < a.timer - 10000 or p is None:
                self.npc_give_up(e, a)
            else:
                d = max(1, distance(cx, cy, p.cx, p.cy))
                old_x, old_y = e.x, e.y
                was_inside = self.in_chase_area(a, e.fx, e.fy)
                self.move_entity_toward(e, cx + (cx - p.cx) / d * 64, cy + (cy - p.cy) / d * 64, e.move_speed)
                if was_inside and not self.in_chase_area(a, e.fx, e.fy):
                    self.set_entity_position(e, old_x, old_y)
                    self.animate_entity(e, False)
        elif state in (AI_ROAM, AI_PATROL, AI_RETURN) and getattr(a, "goal_z", e.z) != e.z:
            went = None                                 # (its next spot is up or down: the climb first)
            if not (now > a.goal_until or now < a.goal_until - 600000):
                went = self.npc_go_level(e, a, a.goal_z, a.goal_x, a.goal_y, near)
            if went is None:
                a.goal_z = e.z                          # (no way there, or too long: it roams on where it is)
                self.forget_path(e)
                self.npc_set_idle(e, a, True)
        elif state in (AI_ROAM, AI_PATROL, AI_RETURN):
            arrived = failed = False
            if distance(cx, cy, a.goal_x, a.goal_y) <= 3 or (a.nap_walk and distance(cx, cy, *a.nap) <= 44):
                arrived = True
            else:
                self.npc_walk_to(e, a.goal_x, a.goal_y, a.walk_speed, 2, False)
                if distance(e.cx, e.cy, a.goal_x, a.goal_y) <= 3:
                    arrived = True
                if now > a.goal_until or now < a.goal_until - 600000:
                    failed = True
                if e.path_stuck > 90:
                    failed = True
            if arrived or failed:
                self.forget_path(e)
                self.animate_entity(e, False)
                if state == AI_RETURN:
                    if arrived or self.in_zone(a, e.fx, e.fy) or a.stand == 1:
                        if a.resume == AI_PATROL and a.stand == 0:
                            self.npc_next_waypoint(a)
                        self.npc_set_idle(e, a, failed)
                    elif not self.npc_pick_roam_goal(e, a):
                        self.npc_set_idle(e, a, True)
                else:
                    if state == AI_PATROL:
                        self.npc_next_waypoint(a)
                    self.npc_set_idle(e, a, failed)
        else:
            faced = False
            if near is not None and near[0].player_visible and near[1] < self.tw * 2.5 and (
                    not self.hostile_for(e, near[0]) or (a.stand == 1 and not getattr(a, "cone", 0))):
                p = near[0].player
                if e.pose not in LYING and not a.napping:   # (asleep, it doesn't turn to look)
                    self.npc_face(e, cx, cy, p.cx, p.cy)
                faced = True
            if a.napping and not self.nap_free(e, a):
                self.npc_wake(e, a)                       # (someone's sat down on it: off it hops)
                self.npc_next_move(e, a)
                return
            lying = e.pose in LYING or a.napping
            if a.pose_next and now >= a.pose_next_at:
                self.npc_pose_step(e, a)
            if a.fidgets and not a.fixed_pose and not lying and not a.pose_next:
                self.npc_fidget(e, a, now)
            if not faced and now >= a.turn_at and not lying:
                every = getattr(a, "turn_every", None)
                if every == 0:                            # (never glances about: back the way it faces, after a sound)
                    if getattr(a, "face", 0) and e.direction != a.face:
                        e.direction = a.face
                        self.animate_entity(e, False)
                    a.turn_at = now + 4000
                else:
                    e.direction = (1, 2, 4, 8)[random_number(1, 4) - 1]
                    if getattr(a, "face", 0) and rnd() < 0.75:   # (a lookout: mostly the way it's set to look)
                        e.direction = a.face
                    self.animate_entity(e, False)
                    a.turn_at = now + (random_number(2000, 5000) if every is None else
                                       int(every * 1000 * (0.7 + rnd() * 0.6)))
            if now >= a.timer or now < a.timer - 600000:
                self.npc_next_move(e, a)

    def npc_absorb(self, e, a):
        """Absorbs.Remnants=1: hurt, it goes to the Shard Remnants lying near it and heals by them (Shards.ini
        [Remnants] Drawn.Reach, Drawn.Heal), unless someone picks them up first. True while it's at it."""
        it = getattr(a, "absorb_to", None)
        if e.hp >= e.max_hp:
            a.absorb_to = None
            return False
        if it is None or not it.alive:
            a.absorb_to = None
            if self.now < a.absorb_at:
                return False
            a.absorb_at = self.now + 500
            reach = val(trim(self.data.shards_ini("Remnants", "Drawn.Reach", "")) or "224")
            piles = [m for m in self.ents if m.type == MAPITEM and m.alive and m.name == REMNANT and m.z == e.z and
                     m.owner is e.owner and distance(e.cx, e.cy, m.cx, m.cy) <= reach]
            if not piles:
                return False
            it = a.absorb_to = min(piles, key=lambda m: distance(e.cx, e.cy, m.cx, m.cy))
        if distance(e.cx, e.cy, it.cx, it.cy) <= 20:
            share = val(trim(self.data.shards_ini("Remnants", "Drawn.Heal", "")) or "0.04")
            e.hp = min(e.max_hp, e.hp + max(1, int(e.max_hp * share * it.quantity)))
            self.sound("Absorb", e.z, e.cx, e.cy)
            self.fx_anim("Teleport_Glow", e.z, e.cx, e.cy, 500)
            self.remove_entity(it)
            a.absorb_to = None
            self.animate_entity(e, False)
            return True
        self.npc_walk_to(e, it.cx, it.cy, e.move_speed, 2, True)
        return True

    def npc_blink(self, e, a, s, d):
        """Entities.ini Blink.Every (seconds; a Dark Mage): in a fight it won't stand to be caught. Come within Blink.Near
        of it, or hit it, or give it long enough, and it's gone in a wisp of Shard essence and stands somewhere else,
        as far as it can shoot, in sight of you. Then it needs a moment before it can throw anything: that, the walk
        and being held still (frozen or stunned: its tick never gets here) are how it's beaten."""
        every = getattr(a, "blink_every", None)
        if every is None:
            every = a.blink_every = val(self.data.entity_ini(e.name, "Blink.Every", "0")) * 1000
            a.blink_at, a.blink_hp = self.now + min(every, 1500), e.hp      # (not as a fight starts: a sneak attack lands)
        if not every:
            return False
        now = self.now
        a.blink_hp = max(a.blink_hp, e.hp)
        if now < a.blink_at and a.blink_at - now <= every * 2:
            return False
        near = val(self.data.entity_ini(e.name, "Blink.Near", "64"))
        if d > near and e.hp >= a.blink_hp and now < a.blink_at + every:
            return False
        spot = self.npc_blink_spot(e, a, s.player)
        if spot is None:
            a.blink_at = now + 500                      # (nowhere just now: it tries again soon)
            return False
        self.fx_anim("Shard_Fade", e.z, e.cx, e.fy - 20, 500)
        self.sound("Mage_Blink", e.z, e.cx, e.cy, radius=BLINK_HEARD)
        self.forget_path(e)
        self.set_entity_position(e, spot[0] - e.w / 2, spot[1] - (e.fy - e.y))
        self.fx_anim("Shard_Form", e.z, e.cx, e.fy - 20, 600)
        self.npc_face(e, e.cx, e.cy, s.player.cx, s.player.cy)
        a.blink_at = now + int(every * (0.8 + rnd() * 0.4))
        a.blink_hp = e.hp
        a.best_d = distance(e.cx, e.cy, s.player.cx, s.player.cy)
        a.progress_time = e.last_attack = now
        return True

    def npc_blink_spot(self, e, a, p):
        """Where it can land: a walkable spot in its chase area, the same ground it stands on (never over a fence, into
        or out of a house), in sight of its foe, out of arm's reach and far enough that it's a jump (the page glides
        anything nearer: state.js)."""
        far = max(128, e.weapon_range)
        here, roofed = self.grid_region_at(e.z, e.fx, e.fy), self.roofed(e.z, e.fx, e.fy)
        for _ in range(24):
            angle, r = rnd() * 6.2832, 96 + rnd() * (far - 96)
            x, y = p.fx + math.cos(angle) * r, p.fy + math.sin(angle) * r
            if distance(x, y, e.fx, e.fy) < 140 or not self.in_chase_area(a, x, y):
                continue
            if not self.pixel_walkable(e.z, x, y) or self.roofed(e.z, x, y) != roofed:
                continue
            if here is not None and self.grid_region_at(e.z, x, y) != here:
                continue
            if self.in_line_of_sight(e.z, x, y - 12, p.cx, p.cy):
                return x, y
        return None

    def npc_state(self, e):
        """What NPC e is doing now, for scripts (>Entity.State): Fighting, Following, Walking, its pose (Sit, Curl,
        Stretch, Butt: a cat's; Curl too when it's asleep on its Nap= spot) or Standing."""
        a = e.ai
        if a is None:
            return "Standing"
        if e.in_combat or e.npc_foe is not None or a.state in (AI_CHASE, AI_FLEE):
            return "Fighting"
        if e.follow is not None:
            return "Following"
        if a.state in (AI_ROAM, AI_PATROL, AI_RETURN):
            return "Walking"
        return e.pose or "Standing"

    def set_npc_pose(self, e, pose):
        """It rests this way from now on (Sit: <Name>_Sit<dir>); "" or "-": it stands, and may sit as its kind does."""
        pose = "" if trim(pose) in ("", "-") else trim(pose)
        e.pose = pose
        if e.ai is not None:
            e.ai.fixed_pose = pose
            e.ai.fidget_until = 0
        self.animate_entity(e, False)

    def npc_follow(self, e, a):
        """Follow.Player: it walks after the player leading it, a step or two behind; if they're gone up a ladder,
        through a door or far off, it waits where it is till they come back for it."""
        s = e.follow
        if not s.in_world():
            e.follow = None
            return
        p = s.player
        d = distance(e.cx, e.cy, p.cx, p.cy)
        if p.z != e.z or d > self.sw:
            self.animate_entity(e, False)
        elif d > 48:
            self.npc_walk_to(e, p.cx, p.cy, max(a.walk_speed, e.move_speed), 40, True)
        else:
            self.forget_path(e)
            self.npc_face(e, e.cx, e.cy, p.cx, p.cy)

    def npc_face(self, e, cx, cy, tx, ty):
        d = distance(cx, cy, tx, ty)
        if d < 1:
            return
        e.direction = self.vector_direction((tx - cx) / d, (ty - cy) / d)
        self.animate_entity(e, False)

    def npc_rouse(self, e, s):
        """e has come for s: the din of it brings the others of its side near it, any that would see it (their own
        Aggro.Range) or hear it (ROUSE_HEAR by their Hearing), nothing solid between, that could chase s from where
        they are. Only those: they don't bring more. Not while s is hushed (Silence: tricks.py)."""
        if s.silent() or not s.in_world():
            return
        p = s.player
        mx, my = math.floor(e.x / self.sw), math.floor(e.y / self.sh)
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                for o in self.npcs_by_map.get((mx + i, my + j, e.z), ()):
                    oa = o.ai
                    if (o is e or oa is None or not o.alive or not o.active or o.in_combat or o.owner is not None or
                            oa.flees or o.npc_foe is not None or getattr(o, "script_moving", False)):
                        continue
                    if not self.hostile_for(o, s) or self.stat_for(o, s, "aggressive") != 1:
                        continue
                    d = distance(o.cx, o.cy, e.cx, e.cy)
                    if d > max(self.stat_for(o, s, "aggro_range"), self.ROUSE_HEAR * getattr(oa, "hearing", 1.0)):
                        continue
                    if not self.in_chase_area(oa, p.fx, p.fy) or not self.visible_to(o, s) or                             not self.in_line_of_sight(o.z, o.cx, o.cy, e.cx, e.cy):
                        continue
                    o.target = s
                    self.npc_start_fight(o, oa, s, distance(o.cx, o.cy, p.cx, p.cy), rouse=False)
                    self.fx({"t": "mark", "kind": "spotted", "u": o.uid}, o.z, o.cx, o.cy, s)

    def shieldwall_draw(self, e, a, foe):
        """A monster after someone: a Shieldwall (forms.py) near it, not who it's after, draws it to them."""
        if foe in self.drawers:
            return None
        for s in self.drawers:
            p = s.player
            if p.z == e.z and p.hp > 0 and s.player_visible and distance(e.cx, e.cy, p.cx, p.cy) <= s.draw_reach() \
                    and self.hostile_for(e, s) and self.visible_to(e, s) and self.in_chase_area(a, p.fx, p.fy):
                s.fought(e)
                return s
        return None

    def npc_start_fight(self, e, a, foe, d, rouse=True):
        """foe: the player it fights (it chases them if it's their foe, else runs from them); rouse: and the others
        near it come too (npc_rouse)."""
        if getattr(a, "flees", False) and foe.calms_animals():
            return                                            # (Ranger's Tread: prey doesn't run from you)
        now = self.now
        fresh = not e.in_combat
        if a.stand == 0:
            if a.state == AI_ROAM:
                a.back_x, a.back_y = a.goal_x, a.goal_y
            if a.state == AI_IDLE and self.in_zone(a, e.fx, e.fy):
                a.back_x, a.back_y = e.cx, e.cy
        self.forget_path(e)
        self.npc_wake(e, a)
        e.pose, a.fidget_until, a.pose_next = "", 0, ""       # (on its feet to fight, or to run)
        e.npc_foe = None                                      # (a player first: whatever it was hunting can wait)
        e.in_combat = True
        e.target = foe
        e.last_combat = now
        if not self.hostile_for(e, foe) or getattr(a, "flees", False):
            a.state = AI_FLEE
            a.timer = now + random_number(2500, 3500)
        else:
            a.state = AI_CHASE
            a.progress_time = now
            a.best_d = d
            if fresh and rouse and getattr(a, "growl", "") and not 0 <= a.growl_at - now:
                a.growl_at = now + 8000                       # (the one that saw you, and not every time it turns)
                self.sound("Growl_" + a.growl, e.z, e.cx, e.cy, radius=256.0)
            if rouse:
                self.npc_rouse(e, foe)

    # =================================================================================================================
    # NPCs against NPCs: a wolf after the sheep (Hunts=), the sheep running, a rat biting back
    # =================================================================================================================
    def npc_versus_npc(self, e, a):
        """e hunts (Hunts=Rabbit,Sheep: the nearest of those it sees, within its chase area), or is hunted: prey that
        flees (Flees=1) runs, the rest fight back. True while that's what it's doing (not roaming)."""
        now = self.now
        foe = e.npc_foe
        if foe is None:
            if a.napping or (now < a.hunt_at and now >= a.hunt_at - 600000):
                return False
            a.hunt_at = now + 1000
            foe = self.npc_prey(e, a)
            if foe is None:
                return False
            self.npc_set_foe(e, foe)
            self.npc_set_foe(foe, e)                          # (it knows: it runs, or turns to fight)
        cx, cy = e.cx, e.cy
        d = distance(cx, cy, foe.cx, foe.cy)
        if (not foe.alive or foe.z != e.z or d > 480 or now - a.progress_time > 6000 or now < a.progress_time or
                (a.flees and (now >= a.timer or now < a.timer - 10000))):
            self.npc_end_versus(e, a)
            return True
        if a.flees:
            old_x, old_y = e.x, e.y
            was_inside = self.in_chase_area(a, e.fx, e.fy)
            dd = max(1, d)
            self.move_entity_toward(e, cx + (cx - foe.cx) / dd * 64, cy + (cy - foe.cy) / dd * 64, e.move_speed)
            if was_inside and not self.in_chase_area(a, e.fx, e.fy):
                self.set_entity_position(e, old_x, old_y)
                self.animate_entity(e, False)
            a.progress_time = now
            return True
        if d <= CombatMixin.melee_reach(e) + e.weapon_range:
            self.npc_face(e, cx, cy, foe.cx, foe.cy)
            a.progress_time = now
            a.best_d = d
            if now - e.last_attack >= e.attack_speed * 1000 or now < e.last_attack:
                e.last_attack = now
                self.npc_strikes_npc(e, foe)
            return True
        if d < a.best_d - 4:
            a.best_d = d
            a.progress_time = now
        old_x, old_y = e.x, e.y
        was_inside = self.in_chase_area(a, e.fx, e.fy)
        self.npc_walk_to(e, foe.cx, foe.cy, e.move_speed, 32 + e.weapon_range, False)
        if was_inside and not self.in_chase_area(a, e.fx, e.fy):
            self.set_entity_position(e, old_x, old_y)
            self.npc_end_versus(e, a)
        return True

    def npc_prey(self, e, a):
        """The nearest NPC of a kind e hunts that it can see, in its chase area (not someone's own, not in a fight).
        Hunts=Foes (the guards): any monster that attacks on sight, even one fighting a player (they come to help);
        not one with an Id (a quest's) nor one only its bane can kill."""
        rng = e.aggro_range if e.aggro_range > 0 else 128
        foes = "FOES" in a.hunts
        every = "ALL" in a.hunts                        # (a Shard Remnant: any creature that can be fought)
        best = None
        mx, my = math.floor(e.x / self.sw), math.floor(e.y / self.sh)
        near = []                                       # (the NPCs on its map and the maps round it: no further)
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                near += self.npcs_by_map.get((mx + i, my + j, e.z), ())
        for o in near:
            if o is e or not o.alive or not o.active or o.owner is not None:
                continue
            d = distance(e.cx, e.cy, o.cx, o.cy)
            if d > rng or (best is not None and d >= best[1]):
                continue
            if foes and o.hostile and o.aggressive and not o.ai.flees and not o.npc_id and \
                    not self.data.entity_ini(o.name, "Slain.By", ""):
                pass
            elif every and o.hostile and o.name != e.name and not o.npc_id and o.ai is not None and \
                    not self.data.entity_ini(o.name, "Slain.By", ""):
                pass
            elif o.in_combat or o.npc_foe is not None or strip_digits(o.name).upper() not in a.hunts:
                continue
            if not self.in_chase_area(a, o.fx, o.fy):
                continue
            if self.in_line_of_sight(e.z, e.cx, e.cy, o.cx, o.cy):
                best = (o, d)
        return best[0] if best is not None else None

    def npc_set_foe(self, e, foe):
        a = e.ai
        if a is None or e.in_combat:                          # (busy with a player)
            return
        now = self.now
        if e.npc_foe is None and a.stand == 0 and self.in_zone(a, e.fx, e.fy):
            a.back_x, a.back_y = e.cx, e.cy
        e.npc_foe = foe
        e.pose, a.fidget_until, a.pose_next = "", 0, ""
        a.state = AI_IDLE
        a.progress_time, a.best_d = now, 9999
        if a.flees:
            a.timer = now + random_number(2500, 3500)
        self.forget_path(e)

    def npc_end_versus(self, e, a):
        e.npc_foe = None
        a.hunt_at = self.now + random_number(8000, 20000)     # (a rest before it hunts again)
        self.npc_give_up(e, a)

    def npc_strikes_npc(self, e, foe):
        """e bites (or hits) NPC foe: a miss, or the damage over its head; at 0 it's dead, with nothing left behind."""
        self.fx_nudge(e, -self.fx_away(foe, e), -self.fx_away_y(foe, e), 110)
        if foe.npc_foe is None:
            self.npc_set_foe(foe, e)
        if not CombatMixin.combat_hits(e.strength * 3 + 2, foe.defence * 3, 3):
            self.fx_splat("Miss", 0, foe)
            return
        damage = random_number(1, 1 + max(0, int(e.strength * self.data.monster_damage)))
        self.sound("Fight%d" % random_number(1, 3), foe.z, foe.cx, foe.cy)
        self.fx_splat("Hit", damage, foe)
        self.fx_nudge(foe, self.fx_away(e, foe), self.fx_away_y(e, foe), 130)
        foe.hp = max(0, foe.hp - damage)
        if foe.hp <= 0 and self.data.entity_ini(foe.name, "Slain.By", ""):
            foe.hp = 1                                        # (only its own bane kills it)
        if foe.hp <= 0:
            self.npc_killed_by_npc(foe, e)

    def npc_killed_by_npc(self, e, killer=None):
        """An NPC killed by another: gone (it comes back later, as one a player kills), its loot and remnants on the
        ground for anyone, or its magic rising to go for its killer."""
        self.sound("Kill_" + (self.data.entity_ini(e.name, "Kill.Sound", "") or "Beast"), e.z, e.cx, e.cy)
        self.npc_loot(e, killer)
        self.queue_respawn(e)
        self.shard_fade(e)
        self.waves.gone(e)                                    # (a raider the guards cut down)
        self.remove_entity(e)
        s = getattr(killer, "owner", None) if killer is not None else None
        if s is not None and e.owner is None and hasattr(s, "find_action_script"):
            script = s.find_action_script("Kill", e.name, e.type, e.npc_id)
            if script:                                        # (your own men's kill is yours: a quest's count)
                s.start_script(script, False)

    def queue_respawn(self, e):
        """A map's own NPC that died (to a player or another NPC) comes back where its map line puts it, after its
        Respawn= (else Config's) delay."""
        m = self.maps.get(e.map)
        if e.source == "MAP" and e.owner is None and m is not None:
            respawn = e.respawn_delay if e.respawn_delay > 0 else self.data.npc_respawn_delay
            options = e.ai.options if e.ai is not None and e.ai.options else "-"
            self.add_action_to_queue("ADD", e.name, TYPE_NAMES[e.type], options, m.name,
                                     self.local_coords(m, e.orig_x, e.orig_y), respawn)

    def npc_loot(self, e, killer):
        """What an NPC killed by another leaves: its Drops and its remnants, anyone's to pick up (a player's own kill
        is theirs first: player_combat.add_npc_drops)."""
        if e.owner is not None:
            return                                            # (someone's own quest creature: nothing for the world)
        self.drop_kill_loot(e, lambda level: self.npc_remnant_rise(e, level, killer))

    def drop_kill_loot(self, e, rise, first=None):
        """A dead NPC's Drops (Entities.ini: item,amount,percent ...) on the ground round where it fell, then its
        Shard Remnants, or its magic rising (rise(level): remnants.py). first: the player who killed it, theirs to
        pick up first (Config Loot.Private.Seconds). A quest's own creature's loot is only its player's."""
        drops = self.data.entity_ini(e.name, "Drops", "")
        drop_x, drop_y = e.cx, e.fy
        secs = val(self.data.config_read("Gameplay", "Loot.Private.Seconds", "10")) if first is not None else 0

        def drop(name, amount):
            copies, each = (1, amount) if self.data.stackable_quantity(name) > 1 else (min(amount, 10), 1)
            iw, ih = self.data.sprite_size_of(3, name)
            for _ in range(int(copies)):
                x = int(drop_x - iw / 2 + random_number(-8, 8))
                y = int(drop_y - ih + random_number(-4, 6))
                self.drop_item(name, e.z, x, y, each, e.owner, first, secs)
        i = 1
        while word(drops, i) != "":
            dd = word(drops, i)
            name, amount_s, percent = word(dd, 1, ","), word(dd, 2, ",") or "1", word(dd, 3, ",") or "100"
            if rnd() * 100 < val(percent):
                amount = parse_quantity(amount_s) if "-" in amount_s else val(amount_s)
                if amount > 0:
                    drop(name, amount)
            i += 1
        death_remnants(self.data, e, drop, rise)

    def npc_remnant_rise(self, dead, level, killer):
        """Its magic rises as a Shard Remnant and goes for the NPC that killed it."""
        e = self.add_npc(LIVING, dead.z, dead.x, dead.y, "-", "Bad")
        if e is None:
            return
        make_remnant(self.data, e, level)
        e.fades_at = self.now + int(val(trim(self.data.shards_ini("Remnants", "Mob.Lasts", "")) or "120") * 1000)
        self.sound("Remnant_Rise", e.z, e.cx, e.cy)
        self.fx_anim("Teleport_Glow", e.z, e.cx, e.cy, 600)
        if killer is not None and killer.alive and e.ai is not None:
            self.npc_set_foe(e, killer)

    def npc_give_up(self, e, a):
        now = self.now
        if e.target is not None and e.hp < e.max_hp * 0.75 and hasattr(e.target, "player_name"):
            self.wonders.grudge_noted(e.target, e)       # (hurt, and they got away: it remembers)
        e.in_combat = False
        e.target = None
        self.forget_path(e)
        a.calm_until = now + 3000
        if a.resume == AI_PATROL and a.stand == 0:
            self.npc_waypoint_goal(e, a)
        else:
            a.goal_x, a.goal_y = a.back_x, a.back_y
        self.npc_walk_started(e, a, AI_RETURN)

    def npc_walk_started(self, e, a, new_state):
        a.state = new_state
        a.goal_z = e.z                                  # (on its own level: npc_pick_floor_goal says otherwise)
        seconds = distance(e.cx, e.cy, a.goal_x, a.goal_y) / max(1, a.walk_speed)
        a.goal_until = self.now + int(seconds * 2500) + 3000

    def npc_fidget(self, e, a, now):
        """Now and then, at rest, a moment of its kind's own: a cat stretches, or turns its back on you (Fidgets=)."""
        if a.fidget_until:
            if now >= a.fidget_until or now < a.fidget_until - 60000:
                e.pose, a.fidget_until = a.pose_back, 0
                self.animate_entity(e, False)
        elif now >= a.fidget_at or now < a.fidget_at - 600000:
            a.pose_back = e.pose
            e.pose = a.fidgets[random_number(1, len(a.fidgets)) - 1]
            a.fidget_until = now + random_number(1500, 2500)
            a.fidget_at = now + random_number(20000, 60000)
            self.animate_entity(e, False)

    def nap_free(self, e, a):
        """Nobody's sitting on its nap spot (a player on the throne: Seat=)."""
        for s in self.sessions.values():
            if s.in_world() and s.seat is not None and s.player.z == e.z:
                x, y = s.seat[1]
                if distance(x + s.player.w / 2, y + s.player.h / 2 + 8, *a.nap) < 20:
                    return False
        return True

    def npc_wake(self, e, a):
        """Off its nap spot, back down where it hopped up from."""
        if getattr(a, "napping", False):
            a.napping = False
            e.pose = ""
            if a.nap_from is not None:
                self.set_entity_position(e, *a.nap_from)

    def npc_pose_step(self, e, a):
        """The next pose in a change of pose: from sitting to lying down, or from sitting up to its feet."""
        e.pose, a.pose_next, a.pose_next_at = ("" if a.pose_next == "-" else a.pose_next), "", 0
        self.animate_entity(e, False)

    def npc_ease_pose(self, e, a, pose):
        """Into pose: a cat lying down sits first (Sit, if it has one), for a moment, then lies."""
        now = self.now
        if pose in LYING and e.pose != pose and "Sit" in a.poses and self.data.loaded("%s_Sit2" % e.name):
            e.pose, a.pose_next, a.pose_next_at = "Sit", pose, now + random_number(700, 1100)
        else:
            e.pose, a.pose_next = pose, ""

    def npc_set_idle(self, e, a, quick):
        now = self.now
        a.fidget_until, a.pose_next = 0, ""
        if getattr(a, "nap_walk", False):
            a.nap_walk = False
            if not quick and self.nap_free(e, a):
                a.napping, a.nap_from = True, (e.x, e.y)
                self.set_entity_position(e, a.nap[0] - e.w / 2, a.nap[1] - e.h / 2 - 2)   # (on its cushion)
                e.pose = "Curl"                               # (up it hops, and curls up)
                a.state = AI_IDLE
                a.timer = now + random_number(40000, 120000)
                a.turn_at = a.timer + 1
                self.animate_entity(e, False)
                return
        a.state = AI_IDLE
        secs = a.pause_min + rnd() * (a.pause_max - a.pause_min)
        if quick:
            secs = 0.5 + rnd()
        a.timer = now + int(secs * 1000)
        if secs > 1.5 and rnd() < 0.4:
            a.turn_at = now + int(secs * 1000 * (0.3 + rnd() * 0.4))
        else:
            a.turn_at = a.timer + 1
        if getattr(a, "fixed_pose", ""):
            e.pose = a.fixed_pose
        else:                                                 # (a long rest: it may sit down, or lie, as its kind does)
            poses = getattr(a, "poses", [])
            self.npc_ease_pose(e, a, poses[int(rnd() * len(poses)) % len(poses)] if poses and secs > 2 and
                               rnd() < 0.6 else "")
        self.animate_entity(e, False)

    def npc_next_move(self, e, a):
        if a.fixed_pose:                                      # (held in its pose, State= / Set.NPC.State: it stays)
            self.npc_set_idle(e, a, False)
            return
        if e.pose in LYING and not getattr(a, "napping", False) and "Sit" in a.poses and \
                self.data.loaded("%s_Sit2" % e.name):
            e.pose, a.pose_next = "Sit", ""               # (up from lying: it sits up a moment first)
            a.timer = self.now + random_number(500, 900)
            self.animate_entity(e, False)
            return
        if getattr(a, "napping", False):
            self.npc_wake(e, a)
        elif getattr(a, "nap", None) and rnd() < 0.35 and self.nap_free(e, a):
            a.nap_walk = True                                 # (off for a nap on its spot)
            a.goal_x, a.goal_y = a.nap[0], a.nap[1] + self.th
            self.npc_walk_started(e, a, AI_ROAM)
            return
        if a.stand == 1:
            if distance(e.cx, e.cy, a.back_x, a.back_y) > 4:
                a.goal_x, a.goal_y = a.back_x, a.back_y
                self.npc_walk_started(e, a, AI_RETURN)
            else:
                self.npc_set_idle(e, a, False)
            return
        if a.resume == AI_PATROL:
            self.npc_waypoint_goal(e, a)
            self.npc_walk_started(e, a, AI_PATROL)
            return
        if not self.npc_pick_roam_goal(e, a):
            self.npc_set_idle(e, a, True)

    def npc_waypoint_goal(self, e, a):
        if not a.way:
            return
        k = min(max(1, a.way_index), len(a.way))
        feet_offset = e.fy - e.cy
        wx, wy = a.way[k - 1]
        a.goal_x = (wx - 0.5) * self.tw + a.home_ox
        a.goal_y = (wy - 0.5) * self.th - feet_offset + a.home_oy

    @staticmethod
    def npc_next_waypoint(a):
        total = len(a.way)
        if total <= 1:
            return
        if a.pingpong == 1:
            k = a.way_index + a.way_step
            if k > total or k < 1:
                a.way_step = -a.way_step
                k = a.way_index + a.way_step
            a.way_index = min(total, max(1, k))
        else:
            a.way_index = (a.way_index % total) + 1

    def npc_pick_roam_goal(self, e, a):
        """A random point of its Zone that it can walk to (same walk-grid area) and that is worth the walk."""
        if a.swims:
            return self.npc_pick_swim_goal(e, a)
        if len(getattr(a, "zone_levels", ())) > 1 and rnd() < FLOOR_ROAM and self.npc_pick_floor_goal(e, a):
            return True
        fx, fy = e.fx, e.fy
        feet_offset = fy - e.cy
        own = self.grid_region_at(e.z, fx, fy)
        zone_w = a.zone[2] - a.zone[0] + 1
        zone_h = a.zone[3] - a.zone[1] + 1
        min_dist = self.tw * 1.5
        if zone_w <= self.tw * 2 and zone_h <= self.th * 2:
            min_dist = self.tw * 0.5
        for attempt in range(1, 11):
            r = a.zone.pick() if isinstance(a.zone, Area) else a.zone     # (one of its parts, if it has them)
            gx = r[0] + self.tw / 4 + rnd() * max(0, r[2] - r[0] + 1 - self.tw / 2)
            gy = r[1] + self.th / 4 + rnd() * max(0, r[3] - r[1] + 1 - self.th / 2)
            ok = not (distance(fx, fy, gx, gy) < min_dist and attempt < 10)
            if ok:
                region = self.grid_region_at(e.z, gx, gy)
                if region is None or region[1] == 0:
                    ok = False
                elif own is not None and own[1] > 0 and region[0] == own[0] and region[1] != own[1]:
                    ok = False
                elif (own is None or region[0] != own[0]) and not self.pixel_walkable(e.z, gx, gy):
                    ok = False
            if ok:
                a.goal_x = gx
                a.goal_y = gy - feet_offset
                self.npc_walk_started(e, a, AI_ROAM)
                return True
        return False

    def npc_pick_swim_goal(self, e, a):
        """A swimmer's next spot in its Zone: mostly the water; now and then out onto the land (or a rock) by it, to
        sit a while before it slips back in."""
        want_water = rnd() < (0.7 if self.in_water(e) else 0.9)
        feet_offset = e.fy - e.cy
        for _ in range(16):
            r = a.zone.pick() if isinstance(a.zone, Area) else a.zone
            gx = r[0] + rnd() * (r[2] - r[0])
            gy = r[1] + rnd() * (r[3] - r[1])
            if not self.pixel_walkable(e.z, gx, gy, None, True) or distance(e.fx, e.fy, gx, gy) < self.tw:
                continue
            m, tx, ty = self.tile_at(e.z, gx, gy)
            if m is None or m.tile_is_water(tx, ty) != want_water:
                continue
            a.goal_x, a.goal_y = gx, gy - feet_offset
            self.npc_walk_started(e, a, AI_ROAM)
            return True
        return False

    def npc_script_move_done(self, e):
        a = e.ai
        if a is None or not e.alive:
            return
        if a.stand == 1:
            a.back_x, a.back_y = e.cx, e.cy
        self.npc_set_idle(e, a, False)

    # =================================================================================================================
    # Who's out (Entities.ini Schedule=Day / Night, a map line's own Schedule=): townsfolk go home at night and to
    # their beds, night creatures hide by day. One with a Bed= sleeps in it at night; one with a Home= goes there
    # (a house, a coop) for the hours it's in; a person with neither (Maren at her counter: her night self is
    # upstairs) goes out of the nearest door; an animal with neither slips away once nobody's near
    # =================================================================================================================
    def schedule_npc(self, e, near):
        """True while it's away or asleep (it thinks no more this tick)."""
        a = e.ai
        sched = self.data.npc_schedule(e.name)
        own = getattr(a, "schedule", None) if a is not None else None
        if own is not None:
            sched = "" if own.upper() in ("ALWAYS", "NONE", "") else own.capitalize()
        if getattr(a, "levels", False) and self.data.day_night_enabled and not e.in_combat:
            busy, near = self.npc_to_level(e, a, sched, near)
            if busy:
                return True
        if getattr(a, "bed", None) and self.data.day_night_enabled and (own or "").upper() != "ALWAYS":
            sleepy = not self.is_night() if sched == "Night" else self.is_night()   # (a night owl sleeps by day;
            if sleepy and not e.in_combat and not e.sched_away and                     self.now >= getattr(a, "woken_until", 0):                       #  Always: up all night)
                return self.npc_bedtime(e, a, near)
            if a.asleep:
                self.npc_get_up(e, a)
        if getattr(a, "home", None) and sched in ("Day", "Night") and self.data.day_night_enabled and \
                not e.in_combat:
            return self.npc_go_home(e, a, sched, near)
        indoors_own = own is not None and e.z > 0           # (its own hours upstairs: at home only at night)
        if not sched or not self.data.day_night_enabled or (e.z != 0 and not indoors_own) or e.in_combat:
            if e.sched_away and not sched:
                e.sched_away = False
                e.active = True
            return e.sched_away and bool(sched)
        night = self.is_night()
        away_now = (sched == "Day" and night) or (sched == "Night" and not night)
        far = near is None or near[1] > 380 or indoors_own   # (upstairs at home: gone at once, downstairs the while)
        if away_now and not e.sched_away:
            person = self.data.animation_available(e.name) == 4
            tent = self.nearest_shelter(e) if sched == "Day" and person and self.nearest_door(e) is None else None
            if sched == "Day" and not far:
                door = self.bed_of(e)                                # (a cat to its bed: Sleeping_Jimmy is it, abed)
                if door is None and person:
                    door = self.nearest_door(e) or (tent and tent[1])   # (a person with no home of its own here;
                if door is None:                                     #  no door at all: a tent's front)
                    return False                                     # (an animal: it slips away once nobody's near)
                d = distance(e.cx, e.cy, door[0], door[1])
                if door is not None and d > 14:
                    if a is not None:                                    # (on its feet: this walk is all it does)
                        self.npc_wake(e, a)
                        e.pose, a.fidget_until, a.pose_next = "", 0, ""
                    moved = self.npc_walk_to(e, door[0], door[1], e.ai.walk_speed if e.ai else e.move_speed, 6, False)
                    self.animate_entity(e, bool(moved))
                    if moved and d < getattr(e, "sched_best", 1e9) - 0.5:     # (getting nearer: on its way)
                        e.sched_best, e.sched_stuck = d, 0
                        return True
                    e.sched_stuck += 1                                   # (no nearer: stuck, or walking on the spot)
                    if e.sched_stuck < 240:
                        return True
            elif sched == "Night" and not far:
                return False
            e.sched_away, e.sched_stuck, e.sched_best = True, 0, 1e9
            e.active = False
            if tent is not None:                                   # (in the tent, asleep: zzz over it)
                e.tent_front = tent[1]
                self.set_entity_position(e, tent[0][0] - e.w / 2, tent[0][1] - e.h / 2)
            self.hours_check_at = -10 ** 9                         # (its sleeping self shows at once)
            return True
        if not away_now and e.sched_away:
            e.sched_away = False
            e.active = True
            front = getattr(e, "tent_front", None)
            if front is not None:                                  # (out of the tent in the morning)
                e.tent_front = None
                self.set_entity_position(e, front[0] - e.w / 2, front[1] - (e.fy - e.y))
            self.hours_check_at = -10 ** 9
            return False
        return e.sched_away

    def npc_go_home(self, e, a, sched, near):
        """One with a Home: for the hours it's in (Day: the night; Night: the day) its Home is its zone - it walks in
        and stays, roaming only inside it (townsfolk in their house, hens in their coop); then back out. Nobody near,
        it's simply there."""
        if e.sched_away:
            e.sched_away, e.active = False, True
        inside = (sched == "Day") == self.is_night()
        zone, chase = (a.home, a.home) if inside else (a.day_zone, a.day_chase)
        if a.zone is not zone:
            a.zone, a.chase = zone, chase
            if not self.in_zone(a, e.fx, e.fy):
                self.forget_path(e)
                if near is None or near[1] > 380:
                    self.npc_put_in_zone(e, a)
                else:
                    a.goal_x, a.goal_y = (zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2
                    self.npc_walk_started(e, a, AI_RETURN)
        return False

    def npc_put_in_zone(self, e, a):
        """Straight to a walkable spot of its zone (nobody's there to see it walk) - out of its home, one joined to
        where it was put on the map (not over a fence the zone's rectangle reaches past)."""
        feet = e.fy - e.y
        want = None
        if a.zone is not getattr(a, "home", None) and getattr(a, "spawn_at", None):
            want = self.grid_region_at(e.z, *a.spawn_at)
            if want is not None and not want[1]:
                want = None
        for _ in range(40):
            r = a.zone.pick() if isinstance(a.zone, Area) else a.zone
            gx, gy = r[0] + rnd() * (r[2] - r[0]), r[1] + rnd() * (r[3] - r[1])
            if want is not None and self.grid_region_at(e.z, gx, gy) != want:
                continue
            if self.pixel_walkable(e.z, gx, gy):
                self.set_entity_position(e, gx - e.w / 2, gy - feet)
                a.back_x, a.back_y = e.cx, e.cy
                self.npc_set_idle(e, a, True)
                return True
        return False

    # =================================================================================================================
    # Stairs and ladders (Tiles.ini Climb=1): townsfolk climb them as a player does, to a bed upstairs (Bed.Level=), a
    # home on another level (Home.Level=), or as they roam a Zone on more than one level (Zone.Levels=0,1). A climb
    # leads to the same spot of the next level, where one the other way stands (a ladder up to a hatch); never a cave's
    # hole or a quest's ladder, nor one behind a Lock
    # =================================================================================================================
    def climb_spots(self, m):
        """Map m's stairs and ladders that lead somewhere: [(x, y, dz)], the middle of each tile and the way it goes."""
        cache = self.data.cache("climb_spots")
        got = cache.get(m.name)
        if got is None or got[0] != m.version:
            spots = []
            cd = self.data.climb_dir
            for y in range(1, self.yt + 1):
                for x in range(1, self.xt + 1):
                    c = m.cell(x, y)
                    dz = cd(m.tile[c]) or cd(m.decor[c])
                    o = self.by_pos.get((m.mx, m.my, m.mz + dz)) if dz else None
                    if o is None or (x, y) in m.lock_at or (x, y) in o.lock_at:
                        continue                                # (a Lock: each player's own, nobody else's way)
                    if -dz in (cd(o.tile[c]), cd(o.decor[c])):  # (one the other way there)
                        spots.append((m.ox + (x - 0.5) * self.tw, m.oy + (y - 0.5) * self.th, dz))
            got = cache[m.name] = (m.version, spots)
        return got[1]

    def climb_toward(self, e, dz):
        """The nearest climb going dz (1 up, -1 down) on e's map and those round it that it can walk to, or None."""
        m = self.map_at(e.z, e.fx, e.fy)
        if m is None:
            return None
        own = self.grid_region_at(e.z, e.fx, e.fy)
        best = None
        for n in self.neighbours(m):
            for x, y, d in self.climb_spots(n):
                if d != dz:
                    continue
                region = self.grid_region_at(e.z, x, y)
                if own is not None and own[1] and region is not None and region[0] == own[0] and region != own:
                    continue                                    # (the other side of a wall)
                dd = distance(e.fx, e.fy, x, y)
                if best is None or dd < best[2]:
                    best = (x, y, dd)
        return best[:2] if best else None

    def anyone_sees(self, z, x, y, r=380):
        """Could a player on level z within r see x,y (an NPC on its way up the stairs there): nothing solid between,
        and not in a house they're outside of?"""
        for s in getattr(self, "players_all", ()):
            p = s.player
            if p.z == z and abs(p.cx - x) <= r and abs(p.cy - y) <= r and distance(p.cx, p.cy, x, y) <= r and                     self.sees_spot(s, z, x, y):
                return True
        return False

    def npc_level_now(self, e, a, sched):
        """(level, x, y): the level its hours keep it on now, and where on it it's going - its bed's at night, its
        Home's for the hours it's in, else its own (where it stands or roams by day: any of its Zone.Levels)."""
        night = self.is_night()
        if a.bed and night and not e.sched_away:
            return a.bed_z, a.bed[0] + self.tw / 2, a.bed[1] + self.th
        if a.home and sched in ("Day", "Night") and (sched == "Day") == night:
            h = a.home
            return a.home_z, (h[0] + h[2]) / 2, (h[1] + h[3]) / 2
        if e.z in a.zone_levels:
            return e.z, e.cx, e.cy
        return a.base_z, a.back_x, a.back_y

    def npc_to_level(self, e, a, sched, near):
        """Off up (or down) the stairs to the level its hours keep it on. (busy, near): busy while it's on its way to a
        climb or just up it; near None once it's simply been put there (nobody near either end to see it go)."""
        z, tx, ty = self.npc_level_now(e, a, sched)
        if z == e.z:
            a.stair_tries = 0
            return False, near
        if a.asleep:
            self.npc_get_up(e, a)                               # (morning, and its bed's upstairs: up, and down to work)
        went = self.npc_go_level(e, a, z, tx, ty, near)
        if went is None:
            return False, near                                  # (no way up it can walk: it stays, as it was)
        if went != "walking":
            self.npc_set_idle(e, a, True)
        return (False, None) if went == "put" else (True, near)

    def npc_go_level(self, e, a, z, tx, ty, near):
        """A step toward level z, where it's going to tx,ty (its centre): to a climb it can walk to, and up or down it;
        or, nobody near either end to see, straight there. "walking", "climbed", "put", or None (no way there)."""
        dz = 1 if z > e.z else -1
        spot = self.climb_toward(e, dz)
        seen = self.anyone_sees(e.z, e.cx, e.cy) or (spot is not None and self.anyone_sees(e.z + dz, *spot))
        if not seen:
            self.forget_path(e)
            e.z = z
            self.set_entity_position(e, tx - e.w / 2, ty - e.h / 2)
            a.stair_tries = 0
            return "put"
        if spot is None:
            return None
        sx, sy = spot
        if distance(e.fx, e.fy, sx, sy) > 8 and a.stair_tries < 600:
            a.stair_tries += 1                                  # (off to the stairs; half a minute stuck and it's up them)
            moved = self.npc_walk_to(e, sx, sy - (e.fy - e.cy), a.walk_speed, 4, False)
            self.animate_entity(e, bool(moved))
            return "walking"
        self.npc_climb(e, a, sx, sy, dz)
        return "climbed"

    def npc_climb(self, e, a, x, y, dz):
        """Up (or down) the stair or ladder it's on, onto the one at the same spot of the next level: heard at both
        ends, from close by only (as a door), and only by those who could see it (never through a wall or a roof)."""
        self.sound("Ladder", e.z, e.cx, e.cy, radius=192.0, seen=True)
        self.forget_path(e)
        e.z += dz
        self.set_entity_position(e, x - e.w / 2, y - (e.fy - e.y))
        self.sound("Ladder", e.z, e.cx, e.cy, radius=192.0, seen=True)
        a.stair_tries = 0
        self.animate_entity(e, False)

    def npc_pick_floor_goal(self, e, a):
        """Now and then its roam takes it up or down (Zone.Levels=0,1: its Zone, the same tiles, on each): a spot of
        its Zone on the next level, joined to where the climb it can walk to comes out."""
        others = [z for z in a.zone_levels if abs(z - e.z) == 1]
        if not others:
            return False
        z = others[random_number(1, len(others)) - 1]
        spot = self.climb_toward(e, z - e.z)
        if spot is None:
            return False
        comes_out = self.grid_region_at(z, *spot)
        feet_offset = e.fy - e.cy
        for _ in range(10):
            r = a.zone.pick() if isinstance(a.zone, Area) else a.zone
            gx = r[0] + self.tw / 4 + rnd() * max(0, r[2] - r[0] + 1 - self.tw / 2)
            gy = r[1] + self.th / 4 + rnd() * max(0, r[3] - r[1] + 1 - self.th / 2)
            region = self.grid_region_at(z, gx, gy)
            if region is None or not region[1] or not self.pixel_walkable(z, gx, gy):
                continue
            if comes_out is not None and region[0] == comes_out[0] and region != comes_out:
                continue                                        # (another room up there: not this way)
            a.goal_x, a.goal_y = gx, gy - feet_offset
            self.npc_walk_started(e, a, AI_ROAM)
            a.goal_z = z
            a.goal_until += 20000                               # (the climb too)
            return True
        return False

    def nearest_shelter(self, e):
        """((tent's middle), (the spot in front of it)) of the nearest shelter on its map (Tiles.ini Shelter=1: a
        canvas tent) with open ground in front, where a person with no house and no door near sleeps; or None."""
        m = self.maps.get(e.map) or self.map_at(e.z, e.x, e.y)
        if m is None:
            return None
        cache = self.data.cache("shelter_spots")
        key = (m.name, m.version)
        spots = cache.get(key)
        if spots is None:
            spots = []
            for y in range(1, self.yt + 1):
                for x in range(1, self.xt + 1):
                    c = m.cell(x, y)
                    if "1" in (trim(self.data.tile_ini(m.tile[c], "Shelter", "")),
                               trim(self.data.tile_ini(m.decor[c], "Shelter", "") if m.decor[c] else "")):
                        mid = (m.ox + (x - 0.5) * self.tw, m.oy + (y - 0.5) * self.th)
                        front = (mid[0], mid[1] + self.th)
                        if y < self.yt and self.pixel_walkable(m.mz, front[0], front[1]):
                            spots.append((mid, front))
            cache[key] = spots
        if not spots:
            return None
        return min(spots, key=lambda sp: distance(e.cx, e.cy, sp[1][0], sp[1][1]))

    def nearest_door(self, e):
        m = self.maps.get(e.map) or self.map_at(e.z, e.x, e.y)
        if m is None:
            return None
        cache = self.data.cache("door_spots")
        key = (m.name, m.version)
        doors = cache.get(key)
        if doors is None:
            doors = []
            for y in range(1, self.yt + 1):
                for x in range(1, self.xt + 1):
                    c = m.cell(x, y)
                    if "1" in (self.data.door_kind(m.tile[c]), self.data.door_kind(m.decor[c])):   # (a gate too)
                        doors.append((m.ox + (x - 0.5) * self.tw, m.oy + (y - 0.5) * self.th))
            cache[key] = doors
        if not doors:
            return None
        return min(doors, key=lambda dd: distance(e.cx, e.cy, dd[0], dd[1]))

    def bed_side(self, e, a):
        """Where it gets into its bed from: the walkable spot nearest it beside the bed's head or foot."""
        bx, by = a.bed
        tw, th = self.tw, self.th
        best = None
        for dx, dy in ((0, 2), (-1, 0), (1, 0), (-1, 1), (1, 1), (0, -1)):
            x, y = bx + dx * tw + tw / 2, by + dy * th + th * 0.6
            if self.pixel_walkable(e.z, x, y):
                d = distance(e.fx, e.fy, x, y)
                if best is None or d < best[0]:
                    best = (d, x, y)
        return best[1:] if best else None

    def npc_bedtime(self, e, a, near):
        """Night, and it has a bed: it walks to it and gets in (its head on the pillow: <Name>_Sleep4, or out of
        sight if it has none), asleep till the morning. Nobody near, it's in bed already."""
        if a.asleep:
            return True
        far = near is None or near[1] > 380
        side = self.bed_side(e, a)
        if not far and side is not None and distance(e.fx, e.fy, *side) > 12 and a.bed_tries < 600:
            a.bed_tries += 1                            # (off to bed; half a minute stuck and it's in it anyway)
            moved = self.npc_walk_to(e, side[0], side[1] - (e.fy - e.cy), a.walk_speed, 6, False)
            self.animate_entity(e, bool(moved))
            return True
        self.forget_path(e)
        a.bed_from, a.asleep, a.bed_tries = (e.x, e.y), True, 0
        if side is not None:
            a.bed_from = (side[0] - e.w / 2, side[1] - (e.fy - e.y))
        e.direction = 4
        self.set_entity_position(e, a.bed[0] + (self.tw - e.w) / 2, a.bed[1] + 2)
        if self.data.loaded("%s_Sleep4" % e.name):
            e.pose = "Sleep"
        else:
            e.active = False
        self.animate_entity(e, False)
        return True

    def npc_get_up(self, e, a):
        """Morning (or a fight): out of bed, beside it, and about its day."""
        a.asleep, a.bed_tries = False, 0
        e.pose, e.active = a.fixed_pose, True
        if a.bed_from is not None:
            self.set_entity_position(e, *a.bed_from)
        self.npc_set_idle(e, a, True)
