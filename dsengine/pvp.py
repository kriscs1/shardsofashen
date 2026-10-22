"""Players fighting players, in the arena only (Config [PvP]): Maps= the maps where it's allowed, Ground= the tiles
both players must be standing on (the arena's sand; empty = anywhere on those maps). Swords, bows and attack spells
all work; your gear, armour and skills count as they do against monsters. Beaten in the arena you lose nothing: you're
healed and wake by the gate (Respawn.Map / Respawn.X / Respawn.Y), and the arena hears who won (ArenaWins and
ArenaLosses are kept as attributes)."""
from dragonsword.lb import val, lbstr, random_number, rnd, trim

from .entity import PLAYER


class PvPMixin:
    # ----- where you may fight
    def pvp_rules(self):
        c = self.data.config_read
        maps = set(c("PvP", "Maps", "").replace(";", " ").split())          # 0,0,5;3,3,5 (or spaces between)
        ground = {trim(g) for g in c("PvP", "Ground", "").replace(";", ",").split(",") if trim(g)}
        return maps, ground

    def in_arena(self):
        maps, _ = self.pvp_rules()
        return self.in_world() and self.cur_map is not None and self.cur_map.name in maps

    def on_arena_ground(self):
        """Standing where you can fight (and be fought)."""
        if not self.in_arena():
            return False
        _, ground = self.pvp_rules()
        if not ground:
            return True
        p = self.player
        m, tx, ty = self.w.tile_at(p.z, p.fx, p.fy)
        if m is None or not m.inside(tx, ty):
            return False
        return any(n in ground for n in self.cell_names(m, tx, ty) if n)

    def session_of(self, e):
        if e is None or e.type != PLAYER:
            return None
        return next((s for s in self.w.sessions.values() if s.player is e), None)

    def pvp_ok(self, other):
        """Can this player fight that one (a Session) now?"""
        return (other is not None and other is not self and other.in_world() and self.in_world() and
                other.player.z == self.player.z and other.player.hp > 0 and self.player.hp > 0 and
                not other.sleeping() and not self.sleeping() and other.player_visible and
                self.on_arena_ground() and other.on_arena_ground())

    # ----- blows
    def pvp_strike(self, t, ranged):
        v = self.session_of(t)
        if not self.pvp_ok(v):
            self.player_attack_target = None
            self.dirty_me = True
            return
        what = "Your arrow" if ranged else "You"
        if not self.combat_hits(self.player_attack_value(), v.player_defence_value() * 2, 3):
            self.play_sound("Miss", (t.cx, t.cy))
            self.fx_splat("Miss", 0, t)
            self.display_message("%s miss%s %s." % (what, "es" if ranged else "", v.player_name), "COMBAT")
            v.display_message("%s misses you." % self.player_name, "COMBAT")
            v.pvp_fight_back(self)
            return
        max_hit = self.player_max_hit()
        damage = random_number(1, max_hit)
        crit = rnd() * 100 < 5 + self.skill_level("Strength") / 15
        if crit:
            damage = max_hit + random_number(0, int(max_hit / 2))
        damage -= v.armour_soak()
        self.wear_weapon()
        if damage <= 0:
            self.fx_splat("Miss", 0, t)
            self.play_sound("Block", (t.cx, t.cy))
            self.display_message("%s's armour takes your blow." % v.player_name, "COMBAT")
            v.display_message("Your armour takes %s's blow." % self.player_name, "COMBAT")
            v.update_skill("Defence", "+0.03", pop=False)
            v.pvp_fight_back(self)
            return
        self.play_sound("Crit" if crit else "Fight%d" % random_number(1, 3), (t.cx, t.cy))
        self.display_message("%s%s hit %s for %d damage!" % ("A critical hit! " if crit else "", what, v.player_name,
                                                              damage), "COMBAT")
        self.fx_anim("Slash", t.cx, t.cy, 240)
        self.update_skill("Strength", "+" + lbstr(damage * 0.005), pop=False)
        v.pvp_take_hit(self, damage, "Crit" if crit else "Hit")

    def pvp_spell_hit(self, spell, t, damage):
        v = self.session_of(t)
        if not self.pvp_ok(v):
            return
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, t.cx, t.cy, 450)
        self.play_sound(self.spell_ini(spell, "Sound", ""), (t.cx, t.cy))
        self.display_message("Your %s hits %s for %s damage!" % (spell.replace("_", " "), v.player_name, lbstr(damage)),
                             "COMBAT")
        v.pvp_take_hit(self, damage, "Hit")

    def pvp_take_hit(self, attacker, damage, kind):
        p = self.player
        self.player_last_combat = self.now
        self.last_hit_by = attacker
        self.pvp_fight_back(attacker)
        if self.god_mode:
            self.fx_splat("Miss", 0, p)
            self.display_message("Your god-like skin shrugs off %s's blow." % attacker.player_name, "COMBAT")
            return
        self.wear_armour()
        self.play_sound("Hurt", (p.cx, p.cy))
        self.fx_splat(kind, damage, p)
        w = self.w
        w.fx_nudge(p, w.fx_away(attacker.player, p), w.fx_away_y(attacker.player, p), 130)
        self.fx_hurt_flash()
        self.display_message("%s hits you for %d damage!" % (attacker.player_name, damage), "DAMAGE")
        self.update_skill("Defence", "+" + lbstr(damage * 0.005), pop=False)
        self.update_skill("Hitpoints", "-%d" % damage)

    def pvp_fight_back(self, attacker):
        """Hit, you turn on whoever hit you (unless you're busy with something else)."""
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = attacker.player
            self.dirty_me = True

    # ----- beaten
    last_hit_by = None

    def arena_defeat(self):
        """Beaten in the arena: nothing lost; healed, by the gate; the arena hears who won."""
        winner = self.last_hit_by if (self.last_hit_by is not None and self.last_hit_by.in_world() and
                                      self.last_hit_by.in_arena()) else None
        self.last_hit_by = None
        p = self.player
        self.fx_anim("Puff", p.cx, p.cy, 500)
        self.play_sound("Death", (p.cx, p.cy))
        self.update_attribute("ArenaLosses", "+1")
        if winner is not None:
            winner.update_attribute("ArenaWins", "+1")
            winner.play_sound("Quest")
            winner.display_message("You have beaten %s in the arena! (%s wins)" % (
                self.player_name, winner.get_attribute("ArenaWins")), "ACHIEVEMENT")
            if winner.player_attack_target is p:
                winner.player_attack_target = None
                winner.dirty_me = True
            news = "%s has beaten %s in the arena!" % (winner.player_name, self.player_name)
        else:
            news = "%s has fallen in the arena." % self.player_name
        for s in self.w.sessions.values():
            if s.in_arena() and s is not winner:
                s.display_message(news, "COMBAT")
            if s.player_attack_target is p:
                s.player_attack_target = None
                s.dirty_me = True
        self.display_message("You're beaten! You wake by the arena's gate, none the worse.", "INFO")
        self.status_reset()
        p.hp = self.player_max_hp
        self.player_attack_target = None
        self.stop_player_walk()
        c = self.data.config_read
        m = c("PvP", "Respawn.Map", "").replace(" ", "") or self.screen_name
        self.teleport(m, val(c("PvP", "Respawn.X", "352")), val(c("PvP", "Respawn.Y", "536")))
        self.dirty_me = True
