"""NPC movement. Each NPC's settings (from its map line's Options: Zone= Chase= Patrol= PatrolMode= Pause= Stand=, and
Entities.ini Roam.Radius Chase.Radius Walk.Speed Pause) are parsed once at spawn into e.ai. Zones are pixel rectangles
of the feet. States:
  IDLE    stands for a random Pause (looks around now and then, people face a player who comes close), then ROAM (a random
          reachable point in its Zone), PATROL (its next waypoint) or, for Stand=1 NPCs, stays put
  ROAM / PATROL  walks there at Walk.Speed x Movement.Speed, then IDLE again
  CHASE   Bad NPCs that are Aggressive and see the player within Aggro.Range in their Chase area, or any Bad NPC the player
          hits: full speed, pathfinding, attacks in range. Gives up when the player leaves the Chase area, the NPC would
          have to leave it, the player dies or hides, or it gets no closer for 5 seconds
  FLEE    a Good NPC the player hits runs away (inside its Chase area) for about 3 seconds
  RETURN  after a chase or flee: walks back to where it left off, then carries on"""
from .entity import (NPC, NPCAI, AI_IDLE, AI_ROAM, AI_PATROL, AI_CHASE, AI_FLEE, AI_RETURN)
from .lb import val, word, trim, distance, random_number, rnd, is_number


class NPCMixin:
    def update_npcs(self):
        p = self.player
        pcx, pcy = p.cx, p.cy
        self.ai_player_fx, self.ai_player_fy = p.fx, p.fy
        for etype in (NPC,):
            for e in list(self.world):
                if e.type != etype or not e.alive:
                    continue
                a = e.ai
                now_turn = True
                if a is not None and not e.in_combat:
                    # Out of sight: bigger, rarer steps (the same speed for much less work)
                    if abs(e.cx - pcx) > self.sw * 0.75 or abs(e.cy - pcy) > self.sh * 0.75:
                        a.skip_delta += self.loop_delta
                        if a.skip_delta < 0.06:
                            now_turn = False
                if now_turn:
                    was = self.loop_delta
                    if a is not None and a.skip_delta > 0:
                        self.loop_delta = min(0.1, a.skip_delta)
                        a.skip_delta = 0
                    if e is not self.script_move_ent:
                        self.update_npc(e, etype, pcx, pcy)
                    self.loop_delta = was
                    self.update_healthbar(e)

    def init_npc_ai(self, e, options):
        a = NPCAI()
        e.ai = a
        n = e.name
        a.solid = 0 if self.entity_ini(n, "Solid", "1") == "0" else 1
        layer = trim(self.entity_ini(n, "Layer", "")).upper()
        a.under = 1 if layer == "UNDER" else 0
        a.flying = 1 if layer == "OVER" else 0
        options = trim(options.replace("\t", " "))
        if options == "-":
            options = ""
        a.options = options
        roam = max(0, val(self.entity_ini(n, "Roam.Radius", "3")))
        chase = max(0, val(self.entity_ini(n, "Chase.Radius", "4")))
        walk = val(self.entity_ini(n, "Walk.Speed", "0.5"))
        if walk <= 0:
            walk = 0.5
        a.walk_speed = max(4, min(1, walk) * e.move_speed)
        pause = self.entity_ini(n, "Pause", "1-4")
        zone = chase_r = patrol = ""
        stand = ping = 0
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
            k += 1
        home = self.entity_home(e)
        a.home_ox = self.map_ox(home)
        a.home_oy = self.map_oy(home)
        spawn_tx = int((e.fx - a.home_ox) / self.tw) + 1
        spawn_ty = int((e.fy - a.home_oy) / self.th) + 1
        a.way = []
        k = 1
        while word(patrol, k, "/") != "" and len(a.way) < 16:
            point = word(patrol, k, "/")
            if "," in point:
                a.way.append((min(2 * self.xt, max(1 - self.xt, int(val(word(point, 1, ","))))),
                              min(2 * self.yt, max(1 - self.yt, int(val(word(point, 2, ",")))))))
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
        a.state = AI_IDLE
        a.timer = self.clock() + int(rnd() * (p_max * 1000 + 1500))
        a.turn_at = a.timer + 1
        if a.under:
            self.force_layer_update = True

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

    def spawn_options(self, name, x, y):
        """The Options of a map's NPC line for name spawned at current-map pixel x,y."""
        m = self.map_at(x, y)
        lx = x - self.map_ox(m)
        ly = y - self.map_oy(m)
        for n, nx, ny, opts, nm in self.map_npcs:
            if nm == m and n == name and abs(nx - lx) <= 2 and abs(ny - ly) <= 2:
                return opts
        return ""

    def update_npc(self, e, etype, pcx, pcy):
        a = e.ai
        if a is None:
            return
        if self.schedule_npc(e):            # home for the night (or a night creature by day): daynight.py
            return
        now = self.loop_start
        cx, cy = e.cx, e.cy
        d = distance(cx, cy, pcx, pcy)
        state = a.state
        if e.slow_until is not None:
            if now >= e.slow_until or now < e.slow_until - 60000:
                e.move_speed = e.normal_speed
                e.slow_until = None
                e.normal_speed = None
        if state not in (AI_CHASE, AI_FLEE):
            start = e.in_combat
            if not start and e.hostile and self.player_visible and (now >= a.calm_until or now < a.calm_until - 10000):
                if e.aggressive == 1 and d <= e.aggro_range:
                    if self.in_chase_area(a, self.ai_player_fx, self.ai_player_fy):
                        if self.in_line_of_sight(cx, cy, pcx, pcy):
                            start = True
            if start:
                self.npc_start_fight(e, a, etype, d)
                state = a.state

        if state == AI_CHASE:
            give_up = not e.in_combat or not self.player_visible
            near = 36 + self.reach_extra(e)
            reach = near + e.weapon_range
            shot = ""
            if d > near + 8:
                shot = self.entity_ini(e.name, "Missile", "")
                if shot and not self.in_line_of_sight(cx, cy, pcx, pcy):
                    shot = ""
                    reach = near
            if not give_up and d <= reach:
                self.npc_face(e, cx, cy, pcx, pcy)
                a.progress_time = now
                a.best_d = d
                if now - e.last_attack >= e.attack_speed * 1000 or now < e.last_attack:
                    e.last_attack = now
                    if shot:
                        self.npc_shoot(e, shot)
                    else:
                        self.npc_attack_player(e)
                return
            if not give_up:
                if not self.in_chase_area(a, self.ai_player_fx, self.ai_player_fy):
                    give_up = True
                if d > max(e.aggro_range, 100) * 3:
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
                self.npc_walk_to(e, pcx, pcy, e.move_speed, 32 + e.weapon_range, False)
                if was_inside and not self.in_chase_area(a, e.fx, e.fy):
                    self.set_entity_position(e, old_x, old_y)
                    give_up = True
            if give_up:
                self.npc_give_up(e, a)
        elif state == AI_FLEE:
            if now >= a.timer or now < a.timer - 10000:
                self.npc_give_up(e, a)
            else:
                if d < 1:
                    d = 1
                old_x, old_y = e.x, e.y
                was_inside = self.in_chase_area(a, e.fx, e.fy)
                self.move_entity_toward(e, cx + (cx - pcx) / d * 64, cy + (cy - pcy) / d * 64, e.move_speed)
                if was_inside and not self.in_chase_area(a, e.fx, e.fy):
                    self.set_entity_position(e, old_x, old_y)
                    self.animate_entity(e, False)
        elif state in (AI_ROAM, AI_PATROL, AI_RETURN):
            arrived = failed = False
            if distance(cx, cy, a.goal_x, a.goal_y) <= 3:
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
            if self.player_visible and d < self.tw * 2.5 and (not e.hostile or a.stand == 1):
                self.npc_face(e, cx, cy, pcx, pcy)
                faced = True
            if not faced and now >= a.turn_at:
                e.direction = (1, 2, 4, 8)[random_number(1, 4) - 1]
                self.animate_entity(e, False)
                a.turn_at = now + random_number(2000, 5000)
            if now >= a.timer or now < a.timer - 600000:
                self.npc_next_move(e, a)

    def npc_face(self, e, cx, cy, tx, ty):
        d = distance(cx, cy, tx, ty)
        if d < 1:
            return
        e.direction = self.vector_direction((tx - cx) / d, (ty - cy) / d)
        self.animate_entity(e, False)

    def npc_start_fight(self, e, a, etype, d):
        now = self.loop_start
        if a.stand == 0:
            if a.state == AI_ROAM:
                a.back_x, a.back_y = a.goal_x, a.goal_y
            if a.state == AI_IDLE and self.in_zone(a, e.fx, e.fy):
                a.back_x, a.back_y = e.cx, e.cy
        self.forget_path(e)
        e.in_combat = True
        e.last_combat = now
        if not e.hostile:
            a.state = AI_FLEE
            a.timer = now + random_number(2500, 3500)
        else:
            a.state = AI_CHASE
            a.progress_time = now
            a.best_d = d

    def npc_give_up(self, e, a):
        now = self.loop_start
        e.in_combat = False
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
        a.goal_until = self.loop_start + int(seconds * 2500) + 3000

    def npc_set_idle(self, e, a, quick):
        now = self.loop_start
        a.state = AI_IDLE
        secs = a.pause_min + rnd() * (a.pause_max - a.pause_min)
        if quick:
            secs = 0.5 + rnd()
        a.timer = now + int(secs * 1000)
        if secs > 1.5 and rnd() < 0.4:
            a.turn_at = now + int(secs * 1000 * (0.3 + rnd() * 0.4))
        else:
            a.turn_at = a.timer + 1
        self.animate_entity(e, False)

    def npc_next_move(self, e, a):
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
        k = min(max(1, a.way_index), max(1, len(a.way)))
        if not a.way:
            return
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
        if self.grid_regions_dirty:
            self.label_grid_regions()
        fx, fy = e.fx, e.fy
        feet_offset = fy - e.cy
        own = self.grid_region_at(fx, fy)
        zone_w = a.zone[2] - a.zone[0] + 1
        zone_h = a.zone[3] - a.zone[1] + 1
        min_dist = self.tw * 1.5
        if zone_w <= self.tw * 2 and zone_h <= self.th * 2:
            min_dist = self.tw * 0.5
        for attempt in range(1, 11):
            gx = a.zone[0] + self.tw / 4 + rnd() * max(0, zone_w - self.tw / 2)
            gy = a.zone[1] + self.th / 4 + rnd() * max(0, zone_h - self.th / 2)
            ok = True
            if distance(fx, fy, gx, gy) < min_dist and attempt < 10:
                ok = False
            if ok:
                if self.grid_w > 0:
                    region = self.grid_region_at(gx, gy)
                    if region == 0 or (own > 0 and region != own):
                        ok = False
                elif not self.pixel_walkable(e, gx, gy):
                    ok = False
            if ok:
                a.goal_x = gx
                a.goal_y = gy - feet_offset
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

    def update_script_move(self):
        """Move.Entity script command: one entity at a time."""
        e = self.script_move_ent
        if e is None:
            return
        if not e.alive:
            self.script_move_ent = None
            return
        tx, ty = e.target_x, e.target_y
        moved = self.npc_walk_to(e, tx, ty, e.script_move, 1, True)
        done = distance(e.cx, e.cy, tx, ty) < 1
        if not moved and not e.path:
            done = True
        if e.path_stuck > 60:
            done = True
        if done:
            self.forget_path(e)
            self.animate_entity(e, False)
            e.target_x = e.target_y = None
            e.script_move = 0
            self.script_move_ent = None
            if e.type == NPC:
                self.npc_script_move_done(e)
