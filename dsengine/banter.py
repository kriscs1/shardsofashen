"""Banter (data\\Banter.ini): the world's people and animals carry on with each other where someone can see it. Two who
meet stop, turn to each other and have a few words over their heads (a bubble each, never the chat log); a dog goes for
a cat, a guard questions the jester; a townsperson has something to say about the chicken in a nice pair of boots.

  * A player's turn comes round about every Every.Seconds: of those near them that they could see (nothing solid between,
    no roof they're outside of), the first pair a scene fits, or one person with something to say about the player.
  * A scene is A=, B= (kinds, or a [Groups] name), Line1..N (A: or B: and what's said,
    Sound1..N with it), After=Scatter (B runs off). With B=Player: When= says what about them (Form, Sneaking, Hurt).
  * Whoever's quest it is stays out of it: nobody with a script of their own (<Verb> <Id>: a scene would stop what it's
    doing, and Mo the cat's quest goes by whether she's walking or sitting), nobody hostile,
    asleep, fighting or away. Scenes and speakers rest a while after (Scene.Rest.Minutes, Speaker.Rest.Minutes).
  * Only how things look: nobody's quest, shop or roam changes, and nothing here is saved."""
import math
import os
import random

from ashen import ini
from ashen.lb import val, trim, distance

from .entity import NPC, AI_IDLE, AI_ROAM

CHECK_MS = 250
HEAR_BANTER = 320                   # (a bark or a hiss, from close by)
SEEN_SCREENS = 1.6                  # (how far off a bubble's seen, in screens: as far as a sound carries)


class Banter:
    def __init__(self, world):
        self.w = world
        self.settings, self.groups, self.scenes = self.read()
        self.running = []           # scenes under way
        self.next_for = {}          # player's name -> when they may see the next (world ms)
        self.scene_rest = {}        # scene -> when it may play again (world ms)
        self.speaker_rest = {}      # uid -> when it may join in again (world ms)
        self.last_check = 0
        self.has_scripts = None
        self.rng = random.Random()  # (its own dice: nothing here changes anyone else's rolls)

    def read(self):
        settings, groups, scenes = {}, {}, {}
        for sec, items in ini.sections(self.w.data.data_file("Banter.ini")):
            d = {k.lower(): trim(v) for k, v in items}
            if sec.lower() == "banter":
                settings = d
            elif sec.lower() == "groups":
                groups = {k: {trim(n) for n in v.split(",") if trim(n)} for k, v in d.items()}
            elif d.get("a") and d.get("b"):
                lines = []
                for k in range(1, 12):
                    who, _, said = d.get("line%d" % k, "").partition(":")
                    if said:
                        lines.append((trim(who).upper(), trim(said), d.get("sound%d" % k, "")))
                d["key"], d["lines"] = sec, lines
                d["a_kinds"], d["b_kinds"] = self.kinds_of(d["a"], groups), self.kinds_of(d["b"], groups)
                scenes[sec] = d
        return settings, groups, scenes

    @staticmethod
    def kinds_of(text, groups):
        out = set()
        for part in text.split(","):
            out |= groups.get(trim(part).lower(), {trim(part)})
        return out

    def setting(self, key, default):
        return val(self.settings.get(key.lower(), default))

    # ----- every tick
    def tick(self):
        w = self.w
        if w.now - self.last_check < CHECK_MS and w.now >= self.last_check:
            return
        self.last_check = w.now
        for r in list(self.running):
            self.update(r)
        if self.setting("On", 1) != 1 or len(self.running) >= self.setting("Most.At.Once", 3):
            return
        for s in list(w.sessions.values()):
            if not s.in_world():
                continue
            due = self.next_for.get(s.player_name)
            if due is None or w.now < due - 3600000:
                self.next_for[s.player_name] = self.next_time(0.5)
            elif w.now >= due:
                self.next_for[s.player_name] = self.next_time(1.0)
                if not s.script_running and not s.ab_mode:
                    self.roll(s)

    def next_time(self, k):
        return self.w.now + self.setting("Every.Seconds", 40) * 1000 * k * self.rng.uniform(0.6, 1.4)

    # ----- who's about
    def free_to_talk(self, e, s):
        a = e.ai
        if e.type != NPC or a is None or not e.alive or e.hostile or e.owner is not None or e.in_combat:
            return False
        if not e.active or e.sched_away or getattr(a, "asleep", False) or getattr(a, "napping", False):
            return False
        if e.source == "CART" or self.speaker_rest.get(e.uid, 0) > self.w.now:
            return False
        return not (e.npc_id and e.npc_id in self.scripted(s))

    def scripted(self, s):
        """The Ids with a script of their own (<Verb> <Id>.script): read the once."""
        if self.has_scripts is None:
            folder = os.path.dirname(s.script_path("x"))
            self.has_scripts = {f[:-7].rsplit(" ", 1)[-1] for f in os.listdir(folder) if f.endswith(".script") and " " in f}
        return self.has_scripts

    def people_near(self, s):
        w, p = self.w, s.player
        reach = self.setting("Sight.Tiles", 9) * w.tw
        return [e for e in w.ents if e.type == NPC and e.z == p.z and distance(e.cx, e.cy, p.cx, p.cy) < reach and
                self.free_to_talk(e, s) and w.sees_spot(s, e.z, e.cx, e.cy)]

    def resting(self, key):
        return self.scene_rest.get(key, 0) > self.w.now

    def roll(self, s):
        """Something for this player to see: about them, now and then, if there's anything to say; else a pair."""
        near = self.people_near(s)
        if not near:
            return None
        self.rng.shuffle(near)
        about = [d for d in self.scenes.values() if d["b"].lower() == "player" and not self.resting(d["key"]) and
                 self.applies(d.get("when", ""), s) and self.in_town(d, s)]
        self.rng.shuffle(about)
        for d in about:
            a = next((e for e in near if e.name in d["a_kinds"]), None)
            if a is not None:
                return self.start(d, a, None, s)
        scenes = [d for d in self.scenes.values() if d["b"].lower() != "player" and not self.resting(d["key"]) and
                  (not d.get("when") or self.applies(d["when"], s)) and self.in_town(d, s)]
        self.rng.shuffle(scenes)
        close = self.setting("Near.Tiles", 5) * self.w.tw
        for d in scenes:
            for a in near:
                if a.name not in d["a_kinds"]:
                    continue
                for b in near:
                    if b is not a and b.name in d["b_kinds"] and distance(a.cx, a.cy, b.cx, b.cy) < close:
                        return self.start(d, a, b, s)
        return None

    @staticmethod
    def in_town(d, s):
        """A scene with Town= is only played in that town (Towns.ini: standing.py)."""
        want = d.get("town", "")
        return not want or (s.cur_map is not None and s.town_of_map(s.cur_map.name).lower() == want.lower())

    def applies(self, when, s):
        """Is what this scene says about them true of player s just now?"""
        kind = when.lower()
        if kind.startswith("$"):                                # (a condition: $Attr.SmugglerSide=2)
            return s.condition_met(when)
        if kind == "thief":                                     # (something stolen, ever: thieving.py)
            return val(s.get_attribute("Thefts")) >= 1
        if kind == "sneaking":
            return s.stance == "Sneaking"
        if kind == "hurt":
            return s.player.hp < s.player_max_hp * 0.3
        if kind in ("outlaw", "distrusted", "welcome", "trusted", "honoured"):    # (the town you're in: standing.py)
            town = s.town_of_map(s.cur_map.name) if s.cur_map is not None else ""
            return bool(town) and s.rank(town).lower() == kind
        form = s.player_form() or ""
        if kind == "form":
            return bool(form)
        return bool(when) and form.lower() == kind

    # ----- playing one
    def start(self, d, a, b, s):
        w = self.w
        beat = int(self.setting("Beat.Seconds", 2.6) * 1000)
        ms = beat * len(d["lines"])
        for e, other in ((a, b or s.player), (b, a)):
            if e is None:
                continue
            self.hold(e, other, ms + 500)
            self.speaker_rest[e.uid] = w.now + self.setting("Speaker.Rest.Minutes", 5) * 60000
        self.scene_rest[d["key"]] = w.now + self.setting("Scene.Rest.Minutes", 10) * 60000
        r = {"d": d, "a": a, "b": b, "player": s.player_name, "line": 0, "next": w.now, "beat": beat}
        self.running.append(r)
        return r

    def hold(self, e, other, ms):
        """It stops where it is and turns to face the other, for as long as this takes."""
        w, ai = self.w, e.ai
        w.forget_path(e)
        ai.state, ai.timer = AI_IDLE, w.now + ms
        ai.turn_at = ai.timer + 1
        dx, dy = other.cx - e.cx, other.cy - e.cy
        e.direction = (2 if dx > 0 else 8) if abs(dx) >= abs(dy) else (4 if dy > 0 else 1)
        e.pose, ai.fidget_until = "", 0
        w.animate_entity(e, False)

    def update(self, r):
        w = self.w
        a, b = r["a"], r["b"]
        if not a.alive or a.in_combat or (b is not None and (not b.alive or b.in_combat)):
            self.running.remove(r)                             # (something else came up)
            return
        if w.now < r["next"]:
            return
        lines = r["d"]["lines"]
        if r["line"] >= len(lines):
            self.running.remove(r)
            self.finish(r)
            return
        who, said, sound = lines[r["line"]]
        e = b if who == "B" and b is not None else a
        self.say(e, said)
        if sound:
            w.sound(sound, e.z, e.cx, e.cy, radius=HEAR_BANTER)
        r["line"] += 1
        r["next"] = w.now + r["beat"]

    def say(self, e, text):
        """A bubble over its head, for whoever could see it (never through a wall, nor a roof they're outside of)."""
        w = self.w
        for s in w.hearers(e.z, e.cx, e.cy, w.sw * SEEN_SCREENS):
            if w.sees_spot(s, e.z, e.cx, e.cy):
                s.emit({"t": "bubble", "u": e.uid, "text": text})

    def finish(self, r):
        d, a, b = r["d"], r["a"], r["b"]
        if d.get("after", "").lower() == "scatter" and b is not None:
            self.scatter(b, a)

    def scatter(self, e, away_from):
        """It's off: a few tiles straight away from the other, then it goes back to what it was doing."""
        w, ai = self.w, e.ai
        far = self.setting("Scatter.Tiles", 4) * w.tw
        turn = math.atan2(e.fy - away_from.fy, e.fx - away_from.fx)
        for k in (0, 0.5, -0.5, 1.0, -1.0):
            x, y = e.fx + math.cos(turn + k) * far, e.fy + math.sin(turn + k) * far
            if w.pixel_walkable(e.z, x, y):
                ai.goal_x, ai.goal_y = x, y - (e.fy - e.cy)
                w.npc_walk_started(e, ai, AI_ROAM)
                return
