"""NPC movement, as the desktop game's npc.py (see there for the states), for many players: an NPC is a foe or a friend
of each player (their own Set.NPC.Attitude), picks a fight with the nearest player it's a foe of, chases its foe (the
player it's fighting), faces whoever is near. Only NPCs on maps near a player think."""
import math

from ashen.lb import val, word, trim, lbstr, distance, random_number, rnd, is_number, strip_digits, parse_quantity

from .entity import NPC, NPCAI, AI_IDLE, AI_ROAM, AI_PATROL, AI_CHASE, AI_FLEE, AI_RETURN, TYPE_NAMES
from .player_combat import CombatMixin
from .remnants import death_remnants, make_remnant, LIVING

PF_NPC_BUDGET = 400


LYING = ("Curl", "Lie")                                # (poses lying down: still, no turning about, sat up from)

class NPCMixin:
    def update_npcs(self):
        sw, sh = self.sw, self.sh
        self.pf_searches = 0
        players = [s for s in self.sessions.values() if s.in_world()]
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
        if not group:
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
            self.npc_start_fight(o, oa, s, od)
            said = True
        if said:
            s.display_message("The %s shouts: \"Intruder!\" The whole camp is after you!" % s.display_name(e), "DAMAGE")
            self.sound("Alarm" if self.data.loaded("Alarm") else "Denied", e.z, e.cx, e.cy)

    def nearest_player(self, e, players, want=None):
        """(session, distance) of the nearest player on e's level who sees it (want(session) must be true too)."""
        best = None
        ex, ey = e.cx, e.cy
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
        a.indoors = trim(d.entity_ini(n, "Indoors", "1")) != "0"     # (0: an animal kept out of houses; cats come in)
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
        zone = chase_r = patrol = roost = nap = ""
        stand = ping = 0
        # (stealth: which way it looks, how wide it sees, who it raises the alarm with, when it's a friend)
        a.cone = max(0, val(d.entity_ini(n, "Sight.Cone", "0")))
        a.hearing = max(0.0, val(d.entity_ini(n, "Hearing", "1")))     # (how far your noise carries to it: build_senses.py)
        a.group = a.friendly_if = a.fixed_pose = ""
        a.poses = [trim(p) for p in d.entity_ini(n, "States", "").split(",") if trim(p)]   # (Sit,Lie: when it stops)
        a.fidgets = [trim(p) for p in d.entity_ini(n, "Fidgets", "").split(",") if trim(p)]   # (Stretch: now and then)
        a.fidget_until, a.fidget_at, a.pose_back = 0, self.now + random_number(5000, 30000), ""
        a.pose_next, a.pose_next_at = "", 0           # (lying down: it sits first, then lies; npc_pose_step)
        a.hunts = {trim(h).upper() for h in d.entity_ini(n, "Hunts", "").split(",") if trim(h)}   # (Hunts=Rabbit,Sheep)
        a.hunt_at = self.now + random_number(2000, 8000)
        a.call = trim(d.entity_ini(n, "Calls", ""))                   # (a frog's croak, a seal's bark, now and then)
        a.call_at = self.now + random_number(5000, 40000)
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
                elif key == "CONE":
                    a.cone = max(0, val(value))
                elif key == "GROUP":
                    a.group = value.upper()
                elif key == "SCHEDULE":                # (this one's hours, not its kind's: Always = never goes home)
                    a.schedule = value
                elif key == "FRIENDLY.IF":
                    a.friendly_if = value
                elif key == "ROOST":                   # (where it spends the night, not gone home: hens in their coop)
                    roost = value
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
        if self.npc_rect_valid(zone):
            x1, y1, x2, y2 = (val(word(zone, i, ",")) for i in range(1, 5))
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
        self.npc_set_rect(a, 0, x1, y1, x2, y2)
        if self.npc_rect_valid(chase_r):
            self.npc_set_rect(a, 1, *(val(word(chase_r, i, ",")) for i in range(1, 5)))
        else:
            self.npc_set_rect(a, 1, min(x1, x2) - chase, min(y1, y2) - chase, max(x1, x2) + chase, max(y1, y2) + chase)
        a.roost = None
        if self.npc_rect_valid(roost):
            a.day_zone, a.day_chase = a.zone, a.chase
            self.npc_set_rect(a, 0, *(val(word(roost, i, ",")) for i in range(1, 5)))
            a.roost, a.zone = a.zone, a.day_zone
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

    def npc_set_rect(self, a, which, x1, y1, x2, y2):
        xt, yt, tw, th = self.xt, self.yt, self.tw, self.th
        left = min(2 * xt, max(1 - xt, int(min(x1, x2))))
        right = min(2 * xt, max(1 - xt, int(max(x1, x2))))
        top = min(2 * yt, max(1 - yt, int(min(y1, y2))))
        bottom = min(2 * yt, max(1 - yt, int(max(y1, y2))))
        rect = [(left - 1) * tw + a.home_ox, (top - 1) * th + a.home_oy, right * tw - 1 + a.home_ox,
                bottom * th - 1 + a.home_oy]
        if which == 0:
            a.zone = rect
        else:
            a.chase = rect

    @staticmethod
    def in_chase_area(a, x, y):
        return a.chase[0] <= x <= a.chase[2] and a.chase[1] <= y <= a.chase[3]

    @staticmethod
    def in_zone(a, x, y):
        return a.zone[0] <= x <= a.zone[2] and a.zone[1] <= y <= a.zone[3]

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
                            if self.npc_sees(e, a, s, d):
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
        if state == AI_CHASE:
            s = foe
            p = s.player if s is not None else None
            give_up = s is None or not e.in_combat or not s.player_visible
            d = distance(cx, cy, p.cx, p.cy) if p is not None else 9999
            near_r = 36 + self.reach_extra(e)
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
                e.direction = (1, 2, 4, 8)[random_number(1, 4) - 1]
                if getattr(a, "face", 0) and rnd() < 0.75:   # (a lookout: mostly the way it's set to look)
                    e.direction = a.face
                self.animate_entity(e, False)
                a.turn_at = now + random_number(2000, 5000)
            if now >= a.timer or now < a.timer - 600000:
                self.npc_next_move(e, a)

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

    @staticmethod
    def reach_extra(e):
        return max(0, int((e.w - 32) / 2))

    def npc_face(self, e, cx, cy, tx, ty):
        d = distance(cx, cy, tx, ty)
        if d < 1:
            return
        e.direction = self.vector_direction((tx - cx) / d, (ty - cy) / d)
        self.animate_entity(e, False)

    def npc_start_fight(self, e, a, foe, d):
        """foe: the player it fights (it chases them if it's their foe, else runs from them)."""
        now = self.now
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
        if d <= 36 + self.reach_extra(e) + e.weapon_range:
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
        m = self.maps.get(e.map)
        if e.source == "MAP" and e.owner is None and m is not None:
            respawn = e.respawn_delay if e.respawn_delay > 0 else self.data.npc_respawn_delay
            options = e.ai.options if e.ai is not None and e.ai.options else "-"
            self.add_action_to_queue("ADD", e.name, TYPE_NAMES[e.type], options, m.name,
                                     self.local_coords(m, e.orig_x, e.orig_y), respawn)
        self.shard_fade(e)
        self.waves.gone(e)                                    # (a raider the guards cut down)
        self.remove_entity(e)

    def npc_loot(self, e, killer):
        """What an NPC killed by another leaves: its Drops and its remnants, anyone's to pick up (a player's own kill
        is theirs first: player_combat.add_npc_drops)."""
        if e.owner is not None:
            return                                            # (someone's own quest creature: nothing for the world)
        drops = self.data.entity_ini(e.name, "Drops", "")
        drop_x, drop_y = e.cx, e.fy

        def drop(name, amount):
            copies, each = (1, amount) if self.data.stackable_quantity(name) > 1 else (min(amount, 10), 1)
            iw, ih = self.data.sprite_size_of(3, name)
            for _ in range(int(copies)):
                x = int(drop_x - iw / 2 + random_number(-8, 8))
                y = int(drop_y - ih + random_number(-4, 6))
                item = self.add_map_item(name, e.z, x, y, each)
                if item is not None:
                    item.source = "DROPPED"
                    m = self.maps.get(item.map)
                    if m is not None:
                        self.add_action_to_queue("REMOVE", name, "MapItem", lbstr(each), m.name,
                                                 self.local_coords(m, x, y), self.data.item_despawn_delay)
        i = 1
        while word(drops, i) != "":
            dd = word(drops, i)
            name, amount_s, percent = word(dd, 1, ","), word(dd, 2, ",") or "1", word(dd, 3, ",") or "100"
            if rnd() * 100 < val(percent):
                amount = parse_quantity(amount_s) if "-" in amount_s else val(amount_s)
                if amount > 0:
                    drop(name, amount)
            i += 1
        death_remnants(self.data, e, drop, lambda level: self.npc_remnant_rise(e, level, killer))

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
        fx, fy = e.fx, e.fy
        feet_offset = fy - e.cy
        own = self.grid_region_at(e.z, fx, fy)
        zone_w = a.zone[2] - a.zone[0] + 1
        zone_h = a.zone[3] - a.zone[1] + 1
        min_dist = self.tw * 1.5
        if zone_w <= self.tw * 2 and zone_h <= self.th * 2:
            min_dist = self.tw * 0.5
        for attempt in range(1, 11):
            gx = a.zone[0] + self.tw / 4 + rnd() * max(0, zone_w - self.tw / 2)
            gy = a.zone[1] + self.th / 4 + rnd() * max(0, zone_h - self.th / 2)
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
            gx = a.zone[0] + rnd() * (a.zone[2] - a.zone[0])
            gy = a.zone[1] + rnd() * (a.zone[3] - a.zone[1])
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
    # Who's out (Entities.ini Schedule=Day / Night): townsfolk go home at night, night creatures hide by day
    # =================================================================================================================
    def schedule_npc(self, e, near):
        sched = self.data.npc_schedule(e.name)
        own = getattr(e.ai, "schedule", None) if e.ai is not None else None
        if own is not None:
            sched = "" if own.upper() in ("ALWAYS", "NONE", "") else own.capitalize()
        if getattr(e.ai, "roost", None) and sched == "Day" and self.data.day_night_enabled and not e.in_combat:
            return self.npc_roost(e, e.ai)
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
            if sched == "Day" and not far:
                door = self.bed_of(e) or self.nearest_door(e)          # (a cat to its bed; townsfolk out of a door)
                d = distance(e.cx, e.cy, door[0], door[1]) if door is not None else 0
                if door is not None and d > 14:
                    moved = self.npc_walk_to(e, door[0], door[1], e.ai.walk_speed if e.ai else e.move_speed, 6, False)
                    if moved and d < getattr(e, "sched_best", 1e9) - 0.5:     # (getting nearer: on its way)
                        e.sched_best, e.sched_stuck = d, 0
                        return False
                    e.sched_stuck += 1                                   # (no nearer: stuck, or walking on the spot)
                    if e.sched_stuck < 240:
                        return False
            elif sched == "Night" and not far:
                return False
            e.sched_away, e.sched_stuck, e.sched_best = True, 0, 1e9
            e.active = False
            self.hours_check_at = -10 ** 9                         # (its sleeping self shows at once)
            return True
        if not away_now and e.sched_away:
            e.sched_away = False
            e.active = True
            self.hours_check_at = -10 ** 9
            return False
        return e.sched_away

    def npc_roost(self, e, a):
        """A creature with a Roost: by night it goes there and stays (roaming only inside it); by day, back out."""
        if e.sched_away:
            e.sched_away, e.active = False, True
        night = self.is_night()
        zone, chase = (a.roost, a.roost) if night else (a.day_zone, a.day_chase)
        if a.zone is not zone:
            a.zone, a.chase = zone, chase
            if not self.in_zone(a, e.fx, e.fy):
                self.forget_path(e)
                a.goal_x, a.goal_y = (zone[0] + zone[2]) / 2, (zone[1] + zone[3]) / 2
                self.npc_walk_started(e, a, AI_RETURN)
        return False

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
