"""The Shifting Deep: an old Shard mine south of Moorcross whose tunnels rearrange themselves (data/Deep.ini).

Its floors are made, not drawn: rooms joined by tunnels, a way down, monsters (stronger the deeper), chests (now and
then one bites: a mimic), hidden traps underfoot (darts, gas, a weakness rune, a pit that drops you a floor, an alarm),
and a cracked wall or two with a secret room behind (Search it). At the bottom, the Deep's Heart: Shards for whoever
reaches it. Every Shift.Minutes, once nobody is down there, the Deep shifts: every floor made again, a new seed.

Each player finds each chest (and the Heart) once a shift (the attribute DeepLoot: the seed and what they've had).
The floors are maps made in memory (maps.MapData from text, as a homestead's), never files: 40,40,-11 and down."""
import random

from dragonsword.lb import val, trim, parse_quantity, pretty
from .maps import MapData
from .shards import shard_words
from .entity import PLAYER

MX, MY, Z0 = 40, 40, -11              # (floor 1's map: 40,40,-11; floor 2: 40,40,-12...)
FLOOR_TILES = ("Flagstone001", "Flagstone001", "Cave_Floor001", "Cave_Floor002")
WALL, ROCK, CRACKED = "Cave_Wall001", "Black001", "Cave_Wall_Cracked001"
TRAPS = ("Darts", "Darts", "Gas", "Weakness", "Pit", "Alarm")
MONSTERS = {1: ("Giant_Spider", "Skeleton", "Rat", "Living_Remnant"),
            2: ("Skeleton", "Skeleton_Archer", "Giant_Spider", "Living_Remnant"),
            3: ("Cave_Troll", "Tomb_Guardian", "Skeleton_Archer", "Living_Remnant")}


class Deep:
    def __init__(self, world):
        self.w = world
        self.d = world.data
        self.seed = 0
        self.floors = []                  # [{map, up: (x, y) px, down: (x, y) px or None, heart: bool}]
        self.next_shift = 0
        self.warned = False

    def num(self, key, default):
        return val(trim(self.d.deep_ini(key, "")) or str(default))

    def text(self, key, default):
        return trim(self.d.deep_ini(key, "")) or str(default)

    def map_name(self, f):
        return "%d,%d,%d" % (MX, MY, Z0 - (f - 1))

    def floor_of(self, map_name):
        for i, fl in enumerate(self.floors, 1):
            if fl["map"] == map_name:
                return i
        return 0

    # ----- making it
    def make(self, seed=None):
        """Every floor made again (a new seed): what was down there goes."""
        w = self.w
        self.seed = seed if seed is not None else random.randrange(1, 10 ** 9)
        for fl in self.floors:
            for e in [e for e in w.ents if e.map == fl["map"] and e.type != PLAYER]:
                w.remove_entity(e)
            w.action_queue = [q for q in w.action_queue if ("\t%s\t" % fl["map"]) not in q]
        self.floors = []
        n = max(1, int(self.num("Floors", 3)))
        for f in range(1, n + 1):
            lines, info = self.generate(f, n, random.Random("%d:%d" % (self.seed, f)))
            name = self.map_name(f)
            m = MapData(self.d, name, lines)
            old = w.maps.get(name)
            m.version = (old.version + 1) if old is not None else 0
            w.maps[name] = m
            w.by_pos[(m.mx, m.my, m.mz)] = m
            w.spawn_map_entities(m)
            w.objects_dirty.add(name)
            info["map"] = name
            self.floors.append(info)
        self.next_shift = w.now + int(self.num("Shift.Minutes", 60) * 60000)
        self.warned = False
        for s in w.sessions.values():                       # (new tunnels: nobody's seen them yet)
            for fl in self.floors:
                s.explored.pop(fl["map"], None)

    def generate(self, f, n, rng):
        """One floor: (its map's text lines, {up, down, heart})."""
        xt, yt = self.d.xt, self.d.yt
        floor = set()
        rooms = []
        want = int(parse_quantity(self.text("Rooms", "6-8")))
        for _ in range(200):
            if len(rooms) >= want:
                break
            rw, rh = rng.randint(4, 7), rng.randint(3, 5)
            x0, y0 = rng.randint(3, xt - rw - 2), rng.randint(3, yt - rh - 2)
            r = (x0, y0, x0 + rw - 1, y0 + rh - 1)
            if any(not (r[2] + 2 < q[0] or q[2] + 2 < r[0] or r[3] + 2 < q[1] or q[3] + 2 < r[1]) for q in rooms):
                continue
            rooms.append(r)
        rooms.sort(key=lambda r: (r[0] + r[2], r[1]))           # (west to east, roughly: the way down far away)
        for r in rooms:
            for y in range(r[1], r[3] + 1):
                for x in range(r[0], r[2] + 1):
                    floor.add((x, y))
        centre = lambda r: ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2)
        for a, b in zip(rooms, rooms[1:]):                      # (tunnels joining each room to the next)
            (ax, ay), (bx, by) = centre(a), centre(b)
            if rng.random() < 0.5:
                path = [(x, ay) for x in range(min(ax, bx), max(ax, bx) + 1)] + \
                       [(bx, y) for y in range(min(ay, by), max(ay, by) + 1)]
            else:
                path = [(ax, y) for y in range(min(ay, by), max(ay, by) + 1)] + \
                       [(x, by) for x in range(min(ax, bx), max(ax, bx) + 1)]
            floor.update(path)
        # (a secret room, off one of the rooms, behind a cracked wall)
        secret, crack = set(), None
        for _ in range(60):
            if int(parse_quantity(self.text("Secrets", "1"))) <= 0:
                break
            r = rng.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]
            side = rng.choice(("n", "s", "e", "w"))
            cx, cy = centre(r)
            if side in ("n", "s"):
                wy = r[1] - 1 if side == "n" else r[3] + 1
                sy0 = wy - 3 if side == "n" else wy + 1
                cells = {(x, y) for x in range(cx - 1, cx + 2) for y in range(sy0, sy0 + 3)}
                wall = (cx, wy)
            else:
                wx = r[0] - 1 if side == "w" else r[2] + 1
                sx0 = wx - 3 if side == "w" else wx + 1
                cells = {(x, y) for x in range(sx0, sx0 + 3) for y in range(cy - 1, cy + 2)}
                wall = (wx, cy)
            ok = all(2 <= x <= xt - 1 and 2 <= y <= yt - 1 for x, y in cells | {wall})
            if ok and not ((cells | {wall}) & floor) and not any(
                    (x + dx, y + dy) in floor for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (x + dx, y + dy) != wall):
                secret, crack = cells, wall
                break
        rows = []
        for y in range(1, yt + 1):
            row = []
            for x in range(1, xt + 1):
                if (x, y) in floor or (x, y) in secret:
                    row.append(rng.choice(FLOOR_TILES))
                elif (x, y) == crack:
                    row.append(CRACKED)
                elif any((x + dx, y + dy) in floor or (x + dx, y + dy) in secret
                         for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    row.append(WALL)
                else:
                    row.append(ROCK)
            rows.append(":".join(row))
        px = lambda x, y, dy=-8: "%d\t%d" % ((x - 1) * 32, (y - 1) * 32 + dy)
        ents = []
        up = centre(rooms[0])
        ents.append("StaticObject\tDeep_Stairs_Up\t%s" % px(up[0], up[1], 0))
        info = {"up": ((up[0] - 1) * 32, (up[1]) * 32 - 8), "down": None, "heart": f == n}
        last = rooms[-1]
        dn = centre(last)
        if f < n:
            ents.append("StaticObject\tDeep_Stairs_Down\t%s" % px(dn[0], dn[1], 0))
            info["down"] = ((dn[0] - 1) * 32, (dn[1]) * 32 - 8)
        else:
            ents.append("StaticObject\tDeep_Heart\t%s" % px(dn[0], dn[1] - 1, 0))
            ents.append("NPC\tShard_Warden\t%s\tAttitude=Bad Zone=%d,%d,%d,%d" % ((px(dn[0] - 1, dn[1]),) + last))
        taken = {up, dn, (dn[0], dn[1] - 1)}

        def spot(r):
            for _ in range(30):
                c = (rng.randint(r[0], r[2]), rng.randint(r[1], r[3]))
                if c not in taken:
                    taken.add(c)
                    return c
            return None
        chests = int(parse_quantity(self.text("Chests", "2-3")))
        for k in range(chests):
            c = spot(rng.choice(rooms[1:] or rooms))
            if c:
                ents.append("StaticObject\tDeep_Chest\t%s\tId=Deep_Chest_%d_%d" % (px(c[0], c[1], 0), f, k + 1))
        if secret:
            c = sorted(secret)[len(secret) // 2]
            ents.append("StaticObject\tDeep_Chest\t%s\tId=Deep_Chest_%d_S" % (px(c[0], c[1], 0), f))
        level = int(self.num("Level.Base", 4) + self.num("Level.Per.Floor", 3) * (f - 1))
        kinds = MONSTERS.get(min(f, 3))
        for k in range(int(parse_quantity(self.text("Monsters", "5-7")))):
            r = rng.choice(rooms[1:] or rooms)
            c = spot(r)
            if not c:
                continue
            kind = rng.choice(kinds)
            opts = "Attitude=Bad Zone=%d,%d,%d,%d" % r
            if kind == "Living_Remnant":
                opts += " Level=%d" % level
            ents.append("NPC\t%s\t%s\t%s" % (kind, px(c[0], c[1]), opts))
        cells = sorted(floor - {up, dn} - {(x, y) for r in rooms[:1] for x in range(r[0] - 1, r[2] + 2)
                                             for y in range(r[1] - 1, r[3] + 2)})
        for k in range(int(parse_quantity(self.text("Traps", "3-5")))):
            if not cells:
                break
            c = rng.choice(cells)
            cells.remove(c)
            kind = rng.choice(TRAPS if f < n else [t for t in TRAPS if t != "Pit"])
            ents.append("Trigger\tDeep_Trap_%s\t%d\t%d" % (kind, c[0], c[1]))
        return rows + ents, info

    # ----- shifting
    def players_inside(self):
        names = {fl["map"] for fl in self.floors}
        return [s for s in self.w.sessions.values() if s.cur_map is not None and s.cur_map.name in names]

    def tick(self):
        if not self.floors:
            self.make()
            return
        if self.w.now < self.next_shift:
            return
        inside = self.players_inside()
        if inside:
            if not self.warned:
                self.warned = True
                for s in inside:
                    s.display_message("The Deep groans around you: it will shift once you're out of it.", "INFO",
                                      "Rumble")
            return
        self.make()


class DeepMixin:
    @property
    def deep(self):
        return self.w.deep

    def deep_do(self, verb, e):
        """The Deep's own things: True if verb on e was one of them."""
        name = e.name
        if verb == "Enter" and name == "Deep_Entrance":
            self.deep_enter(e)
        elif verb in ("Climb Down", "Climb Up") and name in ("Deep_Stairs_Down", "Deep_Stairs_Up"):
            self.deep_stairs(e, verb == "Climb Down")
        elif verb == "Open" and name == "Deep_Chest":
            self.deep_chest(e)
        elif verb == "Touch" and name == "Deep_Heart":
            self.deep_heart(e)
        elif verb == "Search" and name.startswith("Cave_Wall_Cracked"):
            m, tx, ty = self.w.tile_at(e.z, e.cx, e.cy)
            if m is None or self.player_distance_to(e) > 56:
                self.refuse("You are too far away!")
            else:
                self.deep_search_wall(m, tx, ty)
        else:
            return False
        return True

    def deep_enter(self, e):
        if self.player_distance_to(e) > 64:
            self.refuse("You are too far away!")
            return
        fl = self.deep.floors[0]
        self.play_sound("Ladder")
        self.display_message("You climb down into the Shifting Deep. The tunnels aren't where they were last time.", "INFO")
        self.teleport(fl["map"], *fl["up"])

    def deep_stairs(self, e, down):
        f = self.deep.floor_of(e.map)
        if not f or self.player_distance_to(e) > 64:
            self.refuse("You are too far away!") if f else None
            return
        floors = self.deep.floors
        self.play_sound("Ladder")
        if down and f < len(floors):
            self.display_message("Down, to the Deep's floor %d." % (f + 1), "INFO")
            self.teleport(floors[f]["map"], *floors[f]["up"])
        elif not down and f > 1:
            back = floors[f - 2]
            self.display_message("Up, to floor %d." % (f - 1), "INFO")
            self.teleport(back["map"], *(back["down"] or back["up"]))
        elif not down:
            self.display_message("You climb out of the Deep into the daylight.", "INFO")
            self.teleport_to_place("Deep_Entrance_Site")

    def teleport_to_place(self, pid):
        pl = self.data.place(pid)
        if pl is None:
            return
        m = self.w.map_named(pl.map)
        if m is not None:
            self.teleport(m.name, (pl.tx - 1) * self.w.tw, (pl.ty - 1) * self.w.th - 8)

    def deep_had(self):
        """What this player has had from the Deep this shift: the attribute DeepLoot, 'seed:id,id'."""
        v = self.get_attribute("DeepLoot")
        seed, _, ids = str(v).partition(":")
        return set(ids.split(",")) if seed == str(self.deep.seed) else set()

    def deep_have(self, key):
        had = self.deep_had() | {key}
        self.update_attribute("DeepLoot", "=%d:%s" % (self.deep.seed, ",".join(sorted(k for k in had if k))))

    def deep_loot(self, table, f):
        got = []
        for entry in self.deep.text(table, "").split():
            bits = entry.split(",")
            if len(bits) < 3:
                continue
            if random.uniform(0, 100) < val(bits[2]):
                n = int(parse_quantity(bits[1]) * (1 + 0.5 * (f - 1)))
                if n > 0:
                    self.add_inventory_item(bits[0], n)
                    got.append(shard_words(n) if bits[0] == "Shard" else "%d %s" % (n, pretty(bits[0])))
        return got

    def deep_chest(self, e):
        if self.player_distance_to(e) > 56:
            self.refuse("You are too far away!")
            return
        f = self.deep.floor_of(e.map)
        key = e.npc_id or "chest"
        if key in self.deep_had():
            self.display_message("The chest is empty.", "FAIL", "Empty")
            return
        if random.uniform(0, 100) < self.deep.num("Mimic.Chance", 12) and not key.endswith("_S"):
            from .remnants import make_remnant
            w = self.w
            m = w.add_npc("Living_Remnant", e.z, e.x, e.y, "-", "Bad")
            w.remove_entity(e)
            if m is not None:
                make_remnant(self.data, m, int(self.deep.num("Level.Base", 4) + self.deep.num("Level.Per.Floor", 3) * f))
                m.display = "Mimic"
                if m.ai is not None:
                    w.npc_start_fight(m, m.ai, self, 0)
            self.play_sound("Remnant_Rise")
            self.display_message("The chest opens its lid... and its teeth. A mimic!", "DAMAGE", "-")
            return
        self.deep_have(key)
        got = self.deep_loot("Secret.Loot" if key.endswith("_S") else "Loot", f)
        self.play_sound("Chest")
        self.display_message("You open the chest: %s." % (", ".join(got) or "dust, and a very old sock"), "SUCCESS")

    def deep_heart(self, e):
        if self.player_distance_to(e) > 64:
            self.refuse("You are too far away!")
            return
        if "heart" in self.deep_had():
            self.display_message("The Heart's light is dim for you: come back when the Deep has shifted.", "FAIL",
                                 "Empty")
            return
        if any(o.alive and o.name == "Shard_Warden" and o.map == e.map for o in self.w.ents):
            self.refuse("The Deep's Warden stands between you and its Heart.")
            return
        self.deep_have("heart")
        n = int(parse_quantity(self.deep.text("Heart.Shards", "15-30")))
        self.add_inventory_item("Shard", n)
        got = self.deep_loot("Heart.Loot", 3)
        self.play_sound("Absorb")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 600)
        self.display_message("You lay your hand on the Deep's Heart: %d Shards%s. Somewhere, the tunnels creak." %
                             (n, (", and " + ", ".join(got)) if got else ""), "ACHIEVEMENT")

    def deep_search_wall(self, m, x, y):
        if self.w.change_tile(m, x, y, self.deep_floor_tile(), keep_decor=False):
            self.play_sound("Door")
            self.display_message("You press on the cracked stones... and a whole slab swings back: a hidden room!",
                                 "SUCCESS")

    @staticmethod
    def deep_floor_tile():
        return "Flagstone001"

    def world_trap(self, kind, m, x, y):
        """A trap in an old dungeon (a map's Trigger line Trap_<Kind>): it springs, then rests ten minutes for
        whoever sprang it (it isn't spent, as the Deep's are)."""
        if self.god_mode:
            return
        rest = self.__dict__.setdefault("trap_rest", {})
        key = (m.name, x, y)
        if rest.get(key, 0) > self.now:
            return
        rest[key] = self.now + 600000
        self.play_sound("Click")
        self.spring_trap(kind, m, pit_down=False)

    def deep_trap(self, kind, m, x, y):
        """A trap underfoot, sprung (it's spent, for this shift: the plate shows)."""
        if self.god_mode:
            return
        m.trigger[m.cell(x, y)] = ""
        self.w.change_tile(m, x, y, "Trap_Sprung001")
        self.play_sound("Click")
        self.spring_trap(kind, m, pit_down=True)

    def spring_trap(self, kind, m, pit_down):
        if kind == "Darts":
            self.play_sound("Darts")
            dmg = random.randint(2, 4 + self.deep.floor_of(m.name) * 2)
            self.display_message("Click. Darts fly out of the walls!", "DAMAGE", "-")
            self.update_skill("Hitpoints", "-%d" % dmg)
            if random.random() < 0.4:
                self.status_start("Bleed")
        elif kind == "Gas":
            self.display_message("Click. A puff of green gas: your head swims.", "DAMAGE", "-")
            self.status_start("Daze")
            self.status_start("Poison")
        elif kind == "Weakness":
            self.display_message("A rune flares under your foot: your strength drains away.", "DAMAGE", "-")
            self.status_start("Weaken")
        elif kind == "Alarm":
            self.display_message("A bell clangs somewhere in the dark. Something's coming.", "DAMAGE", "Denied")
            from .remnants import make_remnant
            f = self.deep.floor_of(m.name)
            lv = int(self.deep.num("Level.Base", 4) + self.deep.num("Level.Per.Floor", 3) * max(0, f - 1)) if f else 6
            for dx in (-48, 48):
                r = self.w.add_npc("Living_Remnant", self.player.z, self.player.x + dx, self.player.y, "-", "Bad")
                if r is not None:
                    make_remnant(self.data, r, lv)
                    r.fades_at = self.w.now + 90000
                    if r.ai is not None:
                        self.w.npc_start_fight(r, r.ai, self, 48)
        elif kind == "Bucket":
            self.play_sound("Splosh")
            self.display_message("Click. A bucket of icy water tips over your head. Somewhere, someone giggles.",
                                 "DAMAGE", "-")
            self.status_start("Chill")
        elif kind == "Pie":
            self.play_sound("Splosh")
            self.display_message("Click. A custard pie flies out of the wall and hits you square in the face. Whoever "
                                 "built this dungeon had a sense of humour, and not a nice one.", "DAMAGE", "-")
            self.boost_skill("Channeling", -1, 20)
        elif kind == "Pit" and not pit_down:
            self.display_message("The floor gives way into a shallow pit! You climb out, bruised and muddy.",
                                 "DAMAGE", "-")
            self.update_skill("Hitpoints", "-%d" % random.randint(2, 5))
            self.status_start("Frailty")
        elif kind == "Pit":
            f = self.deep.floor_of(m.name)
            floors = self.deep.floors
            if f and f < len(floors):
                self.display_message("The floor gives way! You fall, and land hard a floor below.", "DAMAGE", "-")
                self.update_skill("Hitpoints", "-%d" % random.randint(2, 5))
                self.teleport(floors[f]["map"], *floors[f]["up"])
