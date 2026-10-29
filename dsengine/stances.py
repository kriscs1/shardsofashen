"""Stances: how you hold yourself (data\\Stances.ini has every number). One at a time; changing takes a moment
(Change.Seconds), and nothing changes in the middle of a blow.

  (none)       travelling: as you are.
  Fighting     harder blows and a firmer guard, but magic and what it brings (a monster's poison, a drain) hurt more.
  Channelling  your spells stronger and your wards and spell boosts longer, and you shrug off drains and the like;
               but you walk slowly and your guard drops. (Not potions: they're herbs, and Shards can't touch them.)
  Sneaking     quieter and harder to see (better with Stealth), the lookouts' sight shown to you, and the hands of a
               thief (Pickpocket, Steal, Pick Lock); you walk slowly. A blow struck or a spell cast ends it."""
from ashen.lb import val, trim, lbstr, distance
from .entity import NPC

STANCES = ("", "Fighting", "Channelling", "Sneaking")
WORDS = {"": "You stand easy.", "Fighting": "You stand ready to fight.",
         "Channelling": "You gather the Shards about you.", "Sneaking": "You move softly, keeping low."}


class StanceMixin:
    def stance_num(self, key, default=1.0, stance=None):
        """A number of the stance you're in (Stances.ini [<stance>] key; 1 or default when it says nothing)."""
        st = self.stance if stance is None else stance
        if not st:
            return default
        v = trim(self.data.ini_read("Stances.ini", st, key, ""))
        return val(v) if v else default

    def stance_setting(self, key, default):
        v = trim(self.data.ini_read("Stances.ini", "Stances", key, ""))
        return val(v) if v else default

    def choose_stance(self, name):
        """The player picked a stance (the same again: back to none). It takes hold after Change.Seconds."""
        name = trim(name).capitalize()
        if name not in STANCES:
            return
        if name == self.stance and not self.stance_next:
            name = ""
        if name == (self.stance_next or self.stance):
            return
        self.stance_next = name or "-"
        self.stance_at = self.now + int(self.stance_setting("Change.Seconds", 1) * 1000)
        self.dirty_me = True

    def stance_tick(self):
        if self.stance_next and self.now >= self.stance_at:
            name = "" if self.stance_next == "-" else self.stance_next
            self.stance_next = ""
            if name == self.stance:
                return
            self.stance = name
            self.display_message(WORDS[name], "INFO")
            self.play_sound("Stance_" + (name or "None"))
            self.dirty_me = True

    def end_sneaking(self):
        """A blow struck or a spell cast: you're seen for what you are."""
        if self.stance == "Sneaking" or self.stance_next == "Sneaking":
            self.stance, self.stance_next = "", ""
            self.dirty_me = True

    def stance_walk(self):
        """How fast you walk in this stance (a part of your usual pace)."""
        return self.stance_num("Walk")

    def stealth_level(self):
        return self.skill_level("Stealth") if self.skill_index("Stealth") > 0 else 0

    def sneaking(self):
        return self.stance == "Sneaking"

    # ----- being seen and heard (npcs.py asks these)
    def stealth_cut(self, prefix, least):
        """1, less a little for each Stealth level (Stances.ini [Sneaking] <prefix>.Per.Level), never under least."""
        per = self.stance_num(prefix + ".Per.Level", 0.0, "Sneaking")
        return max(least, 1 - self.stealth_level() * per)

    def sight_factor(self):
        """How far off a monster sees you, a part of its Aggro.Range: less sneaking, and less with Stealth."""
        if not self.sneaking():
            return 1.0
        return max(self.stance_num("Sight.Least", 0.3), self.stance_num("Sight", 0.6) *
                   self.stealth_cut("Sight", self.stance_num("Sight.Least", 0.3)))

    def cone_factor(self):
        """How wide a lookout's sight is for you: narrower, sneaking with Stealth."""
        return self.stealth_cut("Cone", 0.5) if self.sneaking() else 1.0

    def noise_radius(self):
        """How far off you're heard: walking, standing still, fighting; softer sneaking, and with Stealth."""
        n = self.stance_setting("Noise.Walk", 110) if self.player_moved else self.stance_setting("Noise.Still", 24)
        if self.player_last_combat and 0 <= self.now - self.player_last_combat < 4000:
            n = max(n, self.stance_setting("Noise.Fight", 220))
        return n * self.stance_num("Noise", 1.0) * self.stealth_cut("Noise", 0.3)

    def spotted_by(self, e):
        """A monster has seen you (sneaking): a ! over it and a sound, so you know."""
        if self.sneaking():
            self.w.fx({"t": "mark", "kind": "spotted", "u": e.uid}, e.z, e.cx, e.cy, self)
            self.play_sound("Spotted")

    def heard_by(self, e):
        """A lookout heard you and turned to look: a ? over it."""
        self.w.fx({"t": "mark", "kind": "heard", "u": e.uid}, e.z, e.cx, e.cy, self)

    def unseen_by(self, t):
        """Is a blow at t one it never saw coming? Sneaking, and it isn't fighting anyone; or it looks only one way
        (a lookout) and you're behind it."""
        if t.type != NPC or t.ai is None or t.in_combat or getattr(t, "npc_foe", None) is not None:
            return False
        if self.sneaking():
            return True
        a = t.ai
        if getattr(a, "cone", 0) <= 0:
            return False
        p = self.player
        return not self.w.npc_sees(t, a, self, distance(t.cx, t.cy, p.cx, p.cy))

    def sneak_tick(self):
        """Sneaking past a monster that would have come for you, unseen: a little Stealth, and a soft sound."""
        if not self.sneaking():
            self.sneak_near = {}
            return
        w, p = self.w, self.player
        mx, my = int(p.x // w.sw), int(p.y // w.sh)
        near = {}
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                for e in w.npcs_by_map.get((mx + i, my + j, p.z), ()):
                    if e.alive and e.active and e.ai is not None and w.hostile_for(e, self) and \
                            w.stat_for(e, self, "aggressive") == 1:
                        near[e.uid] = (e, distance(e.cx, e.cy, p.cx, p.cy), w.stat_for(e, self, "aggro_range"))
        for uid, (e, d, rng) in near.items():
            if d <= rng and not e.in_combat:
                self.sneak_near[uid] = True
        for uid in list(self.sneak_near):
            e, d, rng = near.get(uid, (None, 1e9, 0))
            if e is None or e.in_combat:
                self.sneak_near.pop(uid)                       # (seen after all, or gone)
            elif d > rng * 1.5:
                self.sneak_near.pop(uid)
                self.play_sound("Sneak_Past")
                self.update_skill("Stealth", "+" + lbstr(self.stance_setting("Sneak.Past.XP", 0.15)))

    def stance_state(self):
        return {"stance": self.stance, "stance_next": "" if self.stance_next == "-" else self.stance_next,
                "stance_ms": max(0, self.stance_at - self.now) if self.stance_next else 0}
