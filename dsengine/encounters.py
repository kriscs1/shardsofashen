"""Random encounters (data\\Encounters.ini): now and then, out of doors, someone or something turns up near a player: a
travelling salesman with different goods every time, a jester with a joke and a trick, a Shard Abomination, a hulk of
broken magic as strong as whoever it found.

  * Each player's turn comes round about every Every.Minutes, while they're up and about under the open sky (not in a
    scene, a fight or a raid); the Isle's first days are left alone (a kind's Requires=). It's the world's, like a raid:
    whoever's near sees it, talks to it or fights it (a fight counts as any other).
  * Where= Wild keeps a kind off a settlement's maps; Min.Level= from players too new for it; Max= how many in the world.
  * It walks in from just out of sight, or (Forms=1) is drawn together out of Shard essence. It stays Minutes, then says
    its goodbye and walks off; once nobody can see it, it's gone (a monster nobody's fighting comes apart).
  * A salesman's rack (ItemRacks.ini Pick=N) shows N of its items, chosen when he arrives and the same for everyone:
    what's bought is gone till his next visit, which brings something else.
  * Nothing here is saved: a server restarting sends them all on their way."""
import logging
import math
import random
import zlib

from ashen import ini
from ashen.lb import val, trim, distance

log = logging.getLogger("ashen.encounters")

CHECK_MS = 1000
CALM_MS = 20000                     # (a player's last blow this long ago: not in a fight)
SIGHT_TILES = 15                    # (further than this from everyone: nobody sees it go)
LEAVE_MS = 90000                    # (the longest it takes to walk off: then it's gone regardless)


class Encounters:
    def __init__(self, world):
        self.w = world
        self.settings, self.kinds = self.read()
        self.running = {}           # uid -> {"kind", "ends", "leaving", "away", "gone_by"}
        self.next_for = {}          # player's name -> when their next one may come (world ms)
        self.visit = {}             # kind -> its visit's mark (what its rack shows goes by it)
        self.last_check = 0
        self.rng = random.Random()  # (its own dice: nothing here changes anyone else's rolls)

    def read(self):
        settings, kinds = {}, {}
        for sec, items in ini.sections(self.w.data.data_file("Encounters.ini")):
            d = {k.lower(): trim(v) for k, v in items}
            if sec.lower() == "encounters":
                settings = d
            elif d.get("npc"):
                d["key"] = sec
                kinds[sec] = d
        return settings, kinds

    def setting(self, key, default):
        return val(self.settings.get(key.lower(), default))

    # ----- every tick
    def tick(self):
        w = self.w
        if w.now - self.last_check < CHECK_MS and w.now >= self.last_check:
            return
        self.last_check = w.now
        for uid, r in list(self.running.items()):
            self.update(uid, r)
        if self.setting("On", 1) != 1:
            return
        for s in list(w.sessions.values()):
            if not s.in_world():
                continue
            due = self.next_for.get(s.player_name)
            if due is None or w.now < due - 86400000:
                self.next_for[s.player_name] = self.next_time()
            elif w.now >= due and self.free(s):
                self.next_for[s.player_name] = self.next_time()
                self.roll(s)

    def next_time(self):
        every = self.setting("Every.Minutes", 25) * 60000
        return self.w.now + every * self.rng.uniform(0.5, 1.5)

    def free(self, s):
        """Is this player up and about under the open sky, with nothing else going on? (else their turn waits)"""
        w, p = self.w, s.player
        if p.z != 0 or s.cur_map is None or not p.alive or s.script_running:
            return False
        if s.now - s.player_last_combat < CALM_MS:
            return False
        m, tx, ty = w.tile_at(p.z, p.cx, p.fy)
        if m is None or m.roof[m.cell(tx, ty)]:
            return False
        if any(r["map"] in w.neighbours(s.cur_map) for r in w.waves.running.values()):
            return False
        near = self.setting("Apart.Tiles", 40) * w.tw                 # (no two at once on one player)
        return not any(e is not None and e.z == p.z and distance(e.cx, e.cy, p.cx, p.cy) < near
                       for e in (w.by_uid.get(u) for u in self.running))

    def allowed(self, kind, s):
        d = self.kinds[kind]
        if sum(1 for r in self.running.values() if r["kind"] == kind) >= val(d.get("max", "1")):
            return False
        if s.player_level() < val(d.get("min.level", "0")):
            return False
        if d.get("where", "").lower() == "wild" and self.settled(s.cur_map):
            return False
        return not d.get("requires") or s.condition_met(d["requires"])

    def settled(self, m):
        """A settlement's map: roofs on it or on those beside it (a kind that keeps to the wild stays off them)."""
        return any(any(n.roof) for n in self.w.neighbours(m))

    def roll(self, s):
        kinds = [k for k in self.kinds if self.allowed(k, s)]
        if not kinds:
            return None
        kind = self.rng.choices(kinds, [max(0.0, val(self.kinds[k].get("weight", "1"))) for k in kinds])[0]
        return self.start(kind, s)

    # ----- turning up
    def spot_near(self, s):
        """A free cell a walk from the player, out of the way, that they could walk to: global pixels, or None."""
        w, p = self.w, s.player
        near, far = self.setting("Near.Tiles", 8), self.setting("Far.Tiles", 12)
        own = w.grid_region_at(p.z, p.fx, p.fy)
        if own is None:
            return None
        for _ in range(40):
            a, r = self.rng.uniform(0, 2 * math.pi), self.rng.uniform(near, far) * w.tw
            x, y = p.fx + math.cos(a) * r, p.fy + math.sin(a) * r
            m, tx, ty = w.tile_at(p.z, x, y)
            if m is None or not w.pixel_walkable(p.z, x, y):
                continue
            c = m.cell(tx, ty)
            if m.roof[c] or m.decor[c] or (tx, ty) in m.lock_at:
                continue
            region = w.grid_region_at(p.z, x, y)
            if region is None or (region[0] == own[0] and region[1] != own[1]) or region[1] == 0:
                continue
            return m, tx, ty
        return None

    def start(self, kind, s, spot=None):
        """It turns up near player s: the entity, or None if there's nowhere for it."""
        w, p = self.w, s.player
        d = self.kinds[kind]
        spot = spot or self.spot_near(s)
        if spot is None:
            return None
        m, tx, ty = spot
        # (where it makes for: round the player, in the tiles of its own map)
        cx, cy = int((p.fx - m.ox) // w.tw) + 1, int((p.fy - m.oy) // w.th) + 1
        hostile = d.get("attitude", "Good").lower() == "bad"
        opts = "Attitude=%s Zone=%d,%d,%d,%d" % ("Bad" if hostile else "Good", cx - 2, cy - 2, cx + 2, cy + 2)
        if not hostile:
            opts += " Schedule=Always"                         # (on the road: no house to go home to)
        if hostile:
            opts += " Chase=%d,%d,%d,%d Pause=0-1" % (cx - 24, cy - 21, cx + 24, cy + 21)
        x, y = m.ox + (tx - 1) * w.tw, m.oy + (ty - 1) * w.th - 8
        e = w.add_npc(d["npc"], p.z, x, y, opts, home=m.name)
        if e is None:
            return None
        e.source = "ENCOUNTER"
        if val(d.get("scales", "0")):
            self.scale(e, d, s.player_level())
        self.running[e.uid] = {"kind": kind, "ends": w.now + val(d.get("minutes", "6")) * 60000, "leaving": False,
                               "away": (tx, ty), "gone_by": 0}
        self.visit[kind] = int(w.now // 1000)
        if val(d.get("forms", "0")):
            w.shard_form(e)
        for o in w.hearers(e.z, e.cx, e.cy, w.sw * 1.6):
            self.announce(o, d)
        said = self.pick(d.get("say", ""))
        if said:
            w.fx({"t": "bubble", "u": e.uid, "text": said}, e.z, e.cx, e.cy)
        if hostile and e.ai is not None:
            w.npc_start_fight(e, e.ai, s, 0)
        log.info("Encounter %s near %s on %s", kind, s.player_name, m.name)
        return e

    def pick(self, text):
        options = [trim(t) for t in text.split("|") if trim(t)]
        return self.rng.choice(options) if options else ""

    def announce(self, s, d):
        """What's heard (and, for bad news, read) by whoever's near as it turns up."""
        if d.get("sound"):
            s.play_sound(d["sound"])
        if d.get("message"):
            s.display_message(d["message"], "ERROR", d.get("message.sound", "-"))

    def scale(self, e, d, level):
        """A monster as strong as the player it found: Scale.* in Encounters.ini, a number and so much a level."""
        level = max(1, int(level + val(d.get("level.plus", "0"))))
        num = lambda k, dflt: val(d.get(k.lower(), dflt))     # noqa: E731
        e.remnant_level = level                                # (monster_level: its remnants go by it)
        e.hp = e.max_hp = max(1, int(num("Hitpoints", 30) + level * num("Hitpoints.Per.Level", 10)))
        e.strength = max(1, round(num("Strength", 2) + level * num("Strength.Per.Level", 0.8)))
        e.defence = max(1, round(num("Defence", 1) + level * num("Defence.Per.Level", 0.7)))

    # ----- going again
    def update(self, uid, r):
        w = self.w
        e = w.by_uid.get(uid)
        if e is None or not e.alive:
            self.running.pop(uid, None)
            return
        if r["leaving"]:
            seen = any(s.in_world() and s.player.z == e.z and
                       distance(s.player.cx, s.player.cy, e.cx, e.cy) < SIGHT_TILES * w.tw for s in w.sessions.values())
            if not seen or w.now >= r["gone_by"]:
                self.remove(uid, e)
            return
        if w.now < r["ends"]:
            return
        if e.in_combat:                                        # (still fighting: it stays till that's over)
            return
        d = self.kinds[r["kind"]]
        if d.get("attitude", "Good").lower() == "bad":
            w.shard_fade(e)                                    # (come apart, nobody having fought it)
            self.remove(uid, e)
            return
        said = self.pick(d.get("goodbye", ""))
        if said:
            w.fx({"t": "bubble", "u": e.uid, "text": said}, e.z, e.cx, e.cy)
        r["leaving"], r["gone_by"] = True, w.now + LEAVE_MS
        if e.ai is not None:                                   # (off the way it came, and past it)
            ax, ay = r["away"]
            x0, y0 = int((e.fx - e.ai.home_ox) // w.tw) + 1, int((e.fy - e.ai.home_oy) // w.th) + 1
            fx, fy = ax + (ax - x0), ay + (ay - y0)
            w.npc_set_rect(e.ai, 0, fx - 1, fy - 1, fx + 1, fy + 1)
            e.ai.stand = 0

    def remove(self, uid, e):
        self.running.pop(uid, None)
        self.w.remove_entity(e)

    # ----- a rack that shows some of its goods each visit
    def rack_id(self, rack, picks):
        """The name a rack's stock goes by this visit: a new one each time, so what was bought last time doesn't count."""
        if picks <= 0:
            return rack
        return "%s#%d" % (rack, self.visit_of(rack))

    def visit_of(self, rack):
        for kind, d in self.kinds.items():
            if d.get("rack") == rack:
                return self.visit.get(kind, 0)
        return 0

    def picked(self, rack, goods, picks):
        """The goods this visit brings: picks of them, chosen by the visit, so everyone sees the same."""
        rng = random.Random(zlib.crc32(("%s|%d" % (rack, self.visit_of(rack))).encode()))
        return rng.sample(goods, min(int(picks), len(goods)))
