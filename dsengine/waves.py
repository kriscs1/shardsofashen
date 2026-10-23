"""Monster waves: monsters attacking a place at once, wave after wave, for everyone there to fight off together
(Data\\Waves.ini). Anything can start one: a surprise raid now and then (Random.Every, when enough players are on),
or a script, Start.Wave <name> (a quest's battle: its On.Win.Script runs for each defender afterwards).

  * Each wave's monsters come in from round the edge and make for the Centre; they go for any player near them.
  * When a wave is beaten the next comes after Gap seconds. Beat them all within Minutes and it's won: everyone who
    defended gets the reward. Run out of time, or leave the raiders to it, and they go off with what they came for.
  * Whoever kills a raider gets Gold.Per.Kill. The browsers show a banner: the wave, and how many are left.
  * The raiders are the world's (everyone sees and fights the same ones) and never come back once killed."""
import logging
import math
import random

from dragonsword import ini
from dragonsword.lb import val, word, trim

log = logging.getLogger("dragonsword.waves")

CHECK_MS = 500
NOBODY_MS = 90000                   # nobody on the map this long: the raiders give up and go
SPAWN_NEAR, SPAWN_FAR = 7, 11       # tiles from the centre the raiders come in at


class Waves:
    def __init__(self, world):
        self.w = world
        self.defs = self.read()
        self.running = {}           # name -> the attack under way
        self.next_random = {}       # name -> when its next surprise attack may come (world ms)
        self.last_check = 0

    def read(self):
        path = self.w.data.data_file("Waves.ini")
        out = {}
        try:
            text = ini.read_text(path)
        except OSError:
            return out
        sec = None
        for ln in text.replace("\r", "").split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith(";"):
                continue
            if ln.startswith("[") and ln.endswith("]"):
                sec = ln[1:-1].strip()
                out[sec] = {"key": sec}
            elif sec and "=" in ln:
                k, v = ln.split("=", 1)
                out[sec][k.strip().lower()] = v.strip()
        for d in out.values():
            d["waves"] = [[(word(p, 1, "*").strip(), max(1, int(val(word(p, 2, "*")) or 1)))
                           for p in part.split(",") if p.strip()]
                          for part in d.get("waves", "").split(";") if part.strip()]
        return {k: d for k, d in out.items() if d["waves"] and d.get("map")}

    # ----- starting
    def centre_of(self, d, m):
        """(tile x, tile y) the raiders make for: a named place, or "X,Y"."""
        c = d.get("centre", "")
        pl = self.w.data.place(c) if c else None
        if pl is not None and pl.map == m.name:
            return pl.tx, pl.ty
        if "," in c:
            return int(val(word(c, 1, ","))), int(val(word(c, 2, ",")))
        return self.w.xt // 2 + 1, self.w.yt // 2 + 1

    def start(self, name, by=None):
        """Starts attack name (Waves.ini). False if there's no such attack or it's on already."""
        d = self.defs.get(name)
        w = self.w
        if d is None:
            if by is not None:
                by.log("ERROR - Start.Wave: no [%s] in Data\\Waves.ini" % name)
            return False
        if name in self.running:
            return False
        m = w.map_named(d["map"])
        if m is None:
            return False
        self.running[name] = {"def": d, "map": m, "wave": -1, "uids": set(), "started": w.now, "next_at": w.now,
                              "kills": {}, "defenders": set(), "nobody_since": None, "centre": self.centre_of(d, m),
                              "shown": set()}
        text = d.get("start.message", "%s!" % d.get("name", name))
        for s in w.sessions.values():
            if not s.in_world():
                continue
            if s.cur_map is not None and s.cur_map.mz == m.mz and s.cur_map in w.neighbours(m):
                s.display_message(text, "ERROR")
                s.play_sound("Horn")
            else:
                s.display_message("News travels fast: %s!" % d.get("name", name), "INFO")
        log.info("Wave attack %s started%s", name, " by %s" % by.player_name if by is not None else "")
        return True

    def spawn_points(self, r):
        m, (cx, cy) = r["map"], r["centre"]
        out = []
        for ty in range(2, self.w.yt):
            for tx in range(2, self.w.xt):
                dd = math.hypot(tx - cx, ty - cy)
                if not SPAWN_NEAR <= dd <= SPAWN_FAR:
                    continue
                c = m.cell(tx, ty)
                if m.roof[c] or m.decor[c] or "1" not in m.walk[c] or (tx, ty) in m.lock_at:
                    continue
                out.append((tx, ty))
        if not out:                                 # (a small place: anywhere open)
            out = [(tx, ty) for ty in range(2, self.w.yt) for tx in range(2, self.w.xt)
                   if "1" in m.walk[m.cell(tx, ty)] and not m.roof[m.cell(tx, ty)]]
        return out

    def spawn_wave(self, name, r):
        w = self.w
        r["wave"] += 1
        r["next_at"] = None
        m, (cx, cy) = r["map"], r["centre"]
        points = self.spawn_points(r)
        random.shuffle(points)
        zone = "%d,%d,%d,%d" % (max(1, cx - 2), max(1, cy - 2), min(w.xt, cx + 2), min(w.yt, cy + 2))
        n = 0
        for monster, count in r["def"]["waves"][r["wave"]]:
            for _ in range(count):
                if not points:
                    break
                tx, ty = points[n % len(points)]
                n += 1
                e = w.add_entity_of_type("NPC", monster, m.mz, m.ox + (tx - 1) * w.tw, m.oy + (ty - 1) * w.th - 8,
                                         "Attitude=Bad Zone=%s Chase=1,1,%d,%d Pause=0-1" % (zone, w.xt, w.yt), home=m.name)
                if e is None:
                    continue
                e.source = "WAVE"
                e.aggressive = 1
                e.aggro_range = max(getattr(e, "aggro_range", 0), 288)
                r["uids"].add(e.uid)
        total = len(r["def"]["waves"])
        self.tell(r, "Wave %d of %d: %d coming!" % (r["wave"] + 1, total, len(r["uids"])), "ERROR", sound="Horn")
        self.status(name, r)

    # ----- every tick
    def tick(self):
        w = self.w
        if w.now - self.last_check < CHECK_MS and w.now >= self.last_check:
            return
        self.last_check = w.now
        self.random_attacks()
        for name, r in list(self.running.items()):
            self.update(name, r)

    def random_attacks(self):
        w = self.w
        online = [s for s in w.sessions.values() if s.in_world()]
        for name, d in self.defs.items():
            every = float(val(d.get("random.every", "0")))
            if every <= 0:
                continue
            due = self.next_random.get(name)
            if due is None:
                self.next_random[name] = w.now + every * 60000 * random.uniform(0.5, 1.5)
                continue
            if w.now < due:
                continue
            self.next_random[name] = w.now + every * 60000 * random.uniform(0.5, 1.5)
            if len(online) >= max(1, int(val(d.get("random.players", "2")))) and not self.running:
                self.start(name)

    def on_map(self, r):
        m = r["map"]
        near = self.w.neighbours(m)
        return [s for s in self.w.sessions.values() if s.in_world() and s.cur_map in near and s.player.z == m.mz]

    def update(self, name, r):
        w = self.w
        d = r["def"]
        here = self.on_map(r)
        for s in here:
            r["defenders"].add(s.player_name)
        r["uids"] = {u for u in r["uids"] if u in w.by_uid and w.by_uid[u].alive}
        if not here:
            r["nobody_since"] = r["nobody_since"] or w.now
            if w.now - r["nobody_since"] > NOBODY_MS:
                return self.finish(name, r, False)
        else:
            r["nobody_since"] = None
        if w.now - r["started"] > float(val(d.get("minutes", "8"))) * 60000:
            return self.finish(name, r, False)
        if r["next_at"] is not None:
            if w.now >= r["next_at"]:
                self.spawn_wave(name, r)
            return
        if not r["uids"]:
            if r["wave"] + 1 >= len(d["waves"]):
                return self.finish(name, r, True)
            gap = max(1, int(val(d.get("gap", "12"))))
            r["next_at"] = w.now + gap * 1000
            self.tell(r, "Wave %d beaten! The next comes in %d seconds." % (r["wave"] + 1, gap), "SUCCESS")
        self.status(name, r)

    def killed(self, e, s):
        """Player s killed NPC e: one of an attack's raiders?"""
        for name, r in self.running.items():
            if e.uid in r["uids"]:
                r["uids"].discard(e.uid)
                r["kills"][s.player_name] = r["kills"].get(s.player_name, 0) + 1
                r["defenders"].add(s.player_name)
                gold = int(val(r["def"].get("gold.per.kill", "0")))
                if gold > 0 and s.inventory_slots_available("Gold_Coin(s)") > 0:
                    s.add_inventory_item("Gold_Coin(s)", gold, quiet=True)
                self.status(name, r)
                return True
        return False

    def finish(self, name, r, won):
        w = self.w
        d = r["def"]
        self.running.pop(name, None)
        for u in list(r["uids"]):                   # (the raiders that are left slip away)
            e = w.by_uid.get(u)
            if e is not None and e.alive:
                w.remove_entity(e)
        text = d.get("win.message" if won else "lose.message", "")
        for s in w.sessions.values():
            if s.in_world():
                s.emit({"t": "wave", "name": ""})
                if text and (s.player_name in r["defenders"] or s in self.on_map(r)):
                    s.display_message(text, "ACHIEVEMENT" if won else "FAIL")
        script = d.get("on.win.script" if won else "on.lose.script", "")
        for who in sorted(r["defenders"]):
            s = w.sessions.get(who)
            if s is None or not s.in_world():
                continue
            if won:
                self.reward(s, d, r["kills"].get(who, 0))
            if script and s.script_exists(script):
                s.start_script(script, False)
        log.info("Wave attack %s %s (defenders: %s)", name, "won" if won else "lost", ", ".join(sorted(r["defenders"])))

    @staticmethod
    def reward(s, d, kills):
        got = []
        gold = int(val(d.get("reward.gold", "0")))
        if gold > 0 and s.inventory_slots_available("Gold_Coin(s)") > 0:
            s.add_inventory_item("Gold_Coin(s)", gold, quiet=True)
            got.append("%d gold" % gold)
        parts = trim(d.get("reward.items", "")).split()
        for i in range(0, len(parts) - 1, 2):
            item, n = parts[i], max(1, int(val(parts[i + 1])))
            if s.inventory_slots_available(item) >= n:
                s.add_inventory_item(item, n, quiet=True)
                got.append("%d %s" % (n, item.replace("_", " ").lower()))
        xp = float(val(d.get("reward.xp", "0")))
        if xp > 0:
            s.update_skill("Strength", "+%s" % xp)
            s.update_skill("Defence", "+%s" % xp)
        if got:
            s.display_message("For defending: %s%s." % (", ".join(got), " (and %d kill%s)" % (kills, "" if kills == 1
                                                                                               else "s") if kills else ""),
                              "ACHIEVEMENT")
        s.play_sound("Quest")

    # ----- telling the players
    def tell(self, r, text, kind, sound=None):
        for s in self.on_map(r):
            s.display_message(text, kind)
            if sound:
                s.play_sound(sound)

    def status(self, name, r):
        d = r["def"]
        left = max(0, int((float(val(d.get("minutes", "8"))) * 60000 - (self.w.now - r["started"])) / 1000))
        msg = {"t": "wave", "name": d.get("name", name), "wave": r["wave"] + 1, "waves": len(d["waves"]),
               "left": len(r["uids"]), "secs": left, "next": max(0, int((r["next_at"] - self.w.now) / 1000))
               if r["next_at"] is not None else 0}
        here = self.on_map(r)
        for s in here:
            s.emit(msg)
        names = {s.player_name for s in here}
        for who in r["shown"] - names:             # (gone from the fight: the banner goes too)
            s = self.w.sessions.get(who)
            if s is not None:
                s.emit({"t": "wave", "name": ""})
        r["shown"] = names

    def state_for(self, s):
        """(For a player arriving on a map under attack.)"""
        for name, r in self.running.items():
            if s in self.on_map(r):
                self.status(name, r)
