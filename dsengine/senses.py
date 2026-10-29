"""A thief's eye (Stealth; Stances.ini [Senses]): as you come near a hidden trap (a map's Trigger Trap_<Kind>, or the
Shifting Deep's) or a secret (a thing with Id=Secret_..., not yet found), you may notice it: more surely sneaking,
and with Stealth. A trap you've seen is marked for you; Disarm it (Stealth), or sneak over it and it doesn't spring.
A secret you've noticed glints, once: Search it as ever. Each player's own."""
from ashen.lb import val, trim, lbstr, distance, rnd

from .entity import STATICOBJECT


class SenseMixin:
    def sense_num(self, key, default):
        v = trim(self.data.ini_read("Stances.ini", "Senses", key, ""))
        return val(v) if v else default

    def sense_chance(self):
        c = self.sense_num("Chance", 15) + self.stealth_level() * self.sense_num("Chance.Per.Level", 3)
        return min(95, c + (self.sense_num("Sneaking", 30) if self.sneaking() else 0))

    def sense_tick(self):
        """Every half second: the traps and secrets within reach not looked at yet this time near them, a roll each."""
        if self.now < self.sense_at:
            return
        self.sense_at = self.now + 500
        m = self.cur_map
        if m is None:
            return
        p = self.player
        reach = self.sense_num("Reach", 80)
        near = set()
        w, tw, th = self.w, self.tw, self.th
        tx0, ty0 = int((p.cx - m.ox) // tw) + 1, int((p.cy - m.oy) // th) + 1
        span = int(reach // tw) + 1
        for ty in range(ty0 - span, ty0 + span + 1):
            for tx in range(tx0 - span, tx0 + span + 1):
                if not m.inside(tx, ty):
                    continue
                trig = m.trigger[m.cell(tx, ty)]
                if trig.startswith(("Trap_", "Deep_Trap_")):
                    key = (m.name, tx, ty)
                    if key in self.traps_seen or distance(p.cx, p.cy, m.ox + (tx - 0.5) * tw, m.oy + (ty - 0.5) * th) > reach:
                        continue
                    near.add(key)
                    if key not in self.sense_tried and rnd() * 100 < self.sense_chance():
                        self.traps_seen.add(key)
                        self.display_message("You spot a trap set in the floor.", "INFO")
                        self.play_sound("Sneak_Past")
                        self.update_skill("Stealth", "+" + lbstr(self.sense_num("Trap.XP", 0.2)))
                        self.dirty_me = True
        for e in w.ents:
            sid = getattr(e, "npc_id", "") or ""
            if e.type != STATICOBJECT or not sid.startswith("Secret_") or e.z != p.z or not e.alive:
                continue
            key = ("secret", sid)
            if key in self.secrets_seen or val(self.get_attribute(sid)) > 0 or \
                    distance(e.cx, e.cy, p.cx, p.cy) > reach * 1.2:
                continue
            near.add(key)
            if key not in self.sense_tried and rnd() * 100 < self.sense_chance() * 0.6:
                self.secrets_seen.add(key)
                self.fx_anim("Teleport_Glow", e.cx, e.cy, 700)
                self.display_message("Something about the %s catches your eye." % self.display_name(e), "INFO")
                self.update_skill("Stealth", "+" + lbstr(self.sense_num("Secret.XP", 0.2)))
        self.sense_tried = (self.sense_tried & near) | near       # (one roll each while you're near; again next time)

    def trap_known(self, m, tx, ty):
        return (m.name, tx, ty) in self.traps_seen

    def trap_spared(self, m, tx, ty):
        """Does a trap underfoot hold its fire? Disarmed by you, or one you've seen that you're sneaking over."""
        key = (m.name, tx, ty)
        return key in self.traps_disarmed or (key in self.traps_seen and self.sneaking())

    def disarm_trap(self, m, tx, ty):
        key = (m.name, tx, ty)
        trig = m.trigger[m.cell(tx, ty)]
        if key not in self.traps_seen or not trig.startswith(("Trap_", "Deep_Trap_")):
            return
        if key in self.traps_disarmed:
            self.display_message("You've made that one safe already.", "INFO")
            return
        level = self.sense_num("Trap.Level", 3) + (self.deep.floor_of(m.name) * 2 if trig.startswith("Deep_") else 0)
        chance = max(10, min(95, 60 + (self.stealth_level() - level) * 5))
        self.play_sound("Lockpick")
        if rnd() * 100 < chance:
            self.traps_disarmed.add(key)
            self.display_message("You wedge the plate and cut the cord: the trap's harmless now.", "SUCCESS", "Unlock")
            self.update_skill("Stealth", "+" + lbstr(self.sense_num("Disarm.XP", 0.4)))
            self.dirty_me = True
            self.act_done(True)
        else:
            self.display_message("Your hand slips...", "DAMAGE", "-")
            kind = trig.split("Trap_", 1)[1]
            self.spring_trap(kind, m, pit_down=trig.startswith("Deep_"))
            self.act_done(False)

    def traps_state(self):
        """The traps you've seen on the maps round you (the page marks them), and which are safe."""
        m = self.cur_map
        if m is None:
            return {"traps": []}
        names = {n.name for n in self.w.neighbours(m)}
        return {"traps": [[k[0], k[1], k[2], 1 if k in self.traps_disarmed else 0]
                          for k in self.traps_seen if k[0] in names]}
