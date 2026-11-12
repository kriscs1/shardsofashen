"""Players fighting players, in the arena only (Config [PvP]): Maps= the maps where it's allowed, Ground= the tiles
both players must be standing on (the arena's sand; empty = anywhere on those maps). Swords, bows and attack spells
all work; your gear, armour and skills count as they do against monsters. Beaten in the arena you lose nothing: you're
healed and wake by the gate (Respawn.Map / Respawn.X / Respawn.Y), and the arena hears who won (ArenaWins and
ArenaLosses are kept as attributes).

Open PvP (a server's setting: DS_PVP=1, or an admin's /pvp on; World.open_pvp): players may fight anywhere else too,
but never in a town (Towns.ini's maps: the Isle's too), a homestead or the Shardrealm (Config [PvP] Open.Safe.Maps),
nor in a party together, nor more than Open.Level.Gap levels apart. Strike a player who isn't marked and you're
marked for Open.Mark.Minutes (each blow you give or take while marked starts it again): the towns' guards come for
you, you can't travel away (shardstones, home, a teleport), and die before it fades and you lose everything you
carry but what's never lost (Keep.On.Death): it lies where you fell, your killer's alone to see for
[Gameplay] Loot.Private.Seconds, then anyone's. Whoever you struck keeps their 5 things and their grave, as ever.
The mark's time runs only while you're playing (a save keeps what's left), and leave the game while you're marked out
where players fight and you stay there a while (server/game.py LINGER): come back to carry on, or be fought as you
stand."""
import time

from ashen.lb import val, lbstr, random_number, trim

from .entity import PLAYER, NPC


class PvPMixin:
    # ----- where you may fight
    def pvp_rules(self):
        got = self.data.cache("pvp_rules")              # (asked of every player for every other, every tick)
        if got and time.monotonic() - got["at"] < 5:
            return got["rules"]
        c = self.data.config_read
        maps = set(c("PvP", "Maps", "").replace(";", " ").split())          # 0,0,10;3,3,5 (or spaces between)
        ground = {trim(g) for g in c("PvP", "Ground", "").replace(";", ",").split(",") if trim(g)}
        got.update(at=time.monotonic(), rules=(maps, ground))
        return maps, ground

    def open_rules(self):
        """Open PvP's numbers: (the mark's ms, the level gap, the safe maps)."""
        got = self.data.cache("pvp_open")
        if got and time.monotonic() - got["at"] < 5:
            return got["rules"]
        c = self.data.config_read
        rules = (max(1.0, val(c("PvP", "Open.Mark.Minutes", "5")) or 5) * 60000,
                 int(val(c("PvP", "Open.Level.Gap", "5"))),
                 set(c("PvP", "Open.Safe.Maps", "21,4,-10").replace(";", " ").split()))
        got.update(at=time.monotonic(), rules=rules)
        return rules

    def open_ground(self):
        """Open PvP's on, and this player is where they may fight (and be fought): not a town, a homestead, the
        Shardrealm, nor the arena (its own rules)."""
        if not self.w.open_pvp or not self.in_world() or self.cur_map is None:
            return False
        name = self.cur_map.name
        got = getattr(self, "open_seen", None)
        if got is not None and got[0] == name:
            return got[1]
        here = not (name in self.pvp_rules()[0] or name in self.open_rules()[2] or self.town_of_map(name) or
                    self.w.homes.is_home_map(name))
        self.open_seen = (name, here)
        return here

    def pvp_badge(self):
        """The badge under the Online line (ui.js drawPvpBadge): 2 open ground, 1 safe, 0 open PvP's off or this is
        the arena (its banner says it)."""
        if not self.w.open_pvp or self.cur_map is None or self.in_arena():
            return 0
        return 2 if self.open_ground() else 1

    def in_arena(self):
        maps, _ = self.pvp_rules()
        return self.in_world() and self.cur_map is not None and self.cur_map.name in maps

    def on_arena_ground(self):
        """Standing where you can fight (and be fought)."""
        p = self.player
        where = (self.cur_map.name if self.cur_map is not None else "", p.fx, p.fy, self.in_world())
        got = getattr(self, "arena_seen", None)
        if got is not None and got[0] == where:
            return got[1]                               # (still standing where it was worked out)
        here = self.on_arena_ground_now()
        self.arena_seen = (where, here)
        return here

    def on_arena_ground_now(self):
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
        if not (other is not None and other is not self and other.in_world() and self.in_world() and
                other.player.z == self.player.z and other.player.hp > 0 and self.player.hp > 0 and
                not other.sleeping() and not self.sleeping() and other.player_visible):
            return False
        if self.on_arena_ground() and other.on_arena_ground():
            return True
        return self.open_pvp_ok(other)

    def open_pvp_ok(self, other):
        if not (self.open_ground() and other.open_ground()):
            return False
        pid = getattr(self, "party_id", 0)
        if pid and pid == getattr(other, "party_id", 0):
            return False                                # (a party never fights itself)
        gap = self.open_rules()[1]
        return gap <= 0 or abs(self.player_level() - other.player_level()) <= gap

    def pvp_why_not(self, other):
        """Why this player can't fight that one (said when a fight stops)."""
        if not self.w.open_pvp or self.in_arena():
            return "You can only fight other players on the arena's sand."
        if other is not None and other.in_world() and self.open_ground() and other.open_ground():
            gap = self.open_rules()[1]
            if gap > 0 and abs(self.player_level() - other.player_level()) > gap:
                return "%s is too far from your level to fight (more than %d apart)." % (other.player_name, gap)
            pid = getattr(self, "party_id", 0)
            if pid and pid == getattr(other, "party_id", 0):
                return "You don't fight your own party."
        return "Nobody fights other players in towns, homesteads or the Shardrealm."

    # ----- the mark (open PvP: who struck first)
    pvp_mark_until = 0
    pvp_hit_at = 0

    def pvp_marked(self):
        return self.pvp_mark_until > self.now

    def pvp_blow(self, v):
        """This player strikes v (a Session) outside the arena: striking one who isn't marked marks you, and a
        blow while you're marked keeps you marked; v too, if they are."""
        if self.on_arena_ground():
            return
        ms = self.open_rules()[0]
        if not self.pvp_marked() and not v.pvp_marked():
            self.pvp_mark_until = self.now + ms
            self.dirty_me = True
            self.display_message("You struck first: you're marked for %s! Die before it fades and you lose "
                                 "everything you carry, and the towns' guards are after you." %
                                 self.how_long(ms / 1000), "ERROR")
            self.play_sound("Denied")
        elif self.pvp_marked():
            self.pvp_mark_until = self.now + ms
            self.dirty_me = True                        # (the time shown starts again)
        if v.pvp_marked():
            v.pvp_mark_until = v.now + ms
            v.dirty_me = True

    def pvp_mark_still(self):
        """Marked where no player or guard can reach you (the arena, the Shardrealm, a homestead): it doesn't fade."""
        if not self.pvp_marked() or self.cur_map is None:
            return False
        name = self.cur_map.name
        return name in self.pvp_rules()[0] or name in self.open_rules()[2] or self.w.homes.is_home_map(name)

    def pvp_mark_tick(self):
        if self.pvp_mark_still():
            self.pvp_mark_until += self.w.dt * 1000
        if self.pvp_mark_until and not self.pvp_marked():
            self.pvp_mark_until = 0
            self.dirty_me = True
            for e in self.w.ents:                       # (the watch stops hunting you)
                if e.type == NPC and e.target is self and e.ai is not None and self.guard_town(e):
                    self.w.npc_give_up(e, e.ai)
            self.display_message("The mark on you fades: you're no longer hunted.", "SUCCESS")

    def pvp_open_told(self):
        gap = self.open_rules()[1]
        self.display_message("Players may fight each other here, outside towns, homesteads and the Shardrealm%s. "
                             "Strike one who isn't marked and you're marked: die then and you lose everything you "
                             "carry." % (" (within %d levels of each other)" % gap if gap > 0 else ""), "INFO")

    def pvp_guard_foe(self, e):
        """Marked: every town's guards are your foes (session.attitude_of asks)."""
        if e.owner is not None or getattr(e, "comp_of", None) is not None or getattr(e, "summoned_until", 0):
            return False
        return bool(self.guard_town(e))

    def pvp_lingers(self):
        """Marked, alive, out where players fight: gone from the game, they stay in the world a while (server/game.py)."""
        return self.pvp_marked() and not self.dead_wait and self.open_ground()

    def pvp_held(self):
        """Marked, you can't slip away (shardstones, home, a teleport): True (and said) if so."""
        if not self.pvp_marked():
            return False
        self.refuse("You can't slip away while you're marked: %s more." %
                    self.how_long(max(1, (self.pvp_mark_until - self.now) / 1000)))
        return True

    # ----- blows
    def pvp_strike(self, t, ranged):
        v = self.session_of(t)
        if not self.pvp_ok(v):
            self.player_attack_target = None
            self.dirty_me = True
            return
        self.pvp_blow(v)
        if not self.combat_hits(self.player_attack_value(), v.player_defence_value() * 2, 3):
            self.play_sound("Miss", (t.cx, t.cy))
            self.fx_splat("Miss", 0, t)
            v.pvp_fight_back(self)
            return
        max_hit = self.player_max_hit()
        damage = random_number(1, max_hit)
        crit = self.lands_crit()
        if crit:
            damage = max_hit + random_number(0, int(max_hit / 2))
        damage -= v.armour_soak()
        self.wear_weapon()
        if damage <= 0:
            self.fx_splat("Miss", 0, t)
            self.play_sound("Block", (t.cx, t.cy))
            v.fight_xp("Defence", 0.03)
            v.pvp_fight_back(self)
            return
        self.play_sound("Crit" if crit else "Fight%d" % random_number(1, 3), (t.cx, t.cy))
        self.fx_anim("Slash", t.cx, t.cy, 240)
        self.fight_xp("Attack", damage * 0.005)
        v.pvp_take_hit(self, damage, "Crit" if crit else "Hit")

    def pvp_spell_hit(self, spell, t, damage):
        v = self.session_of(t)
        if not self.pvp_ok(v):
            return
        self.pvp_blow(v)
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, t.cx, t.cy, 450)
        self.play_sound(self.spell_ini(spell, "Sound", ""), (t.cx, t.cy))
        v.pvp_take_hit(self, damage, "Hit")

    def pvp_take_hit(self, attacker, damage, kind):
        p = self.player
        self.player_last_combat = self.now
        self.last_hit_by, self.pvp_hit_at = attacker, self.now
        self.pvp_fight_back(attacker)
        if self.god_mode:
            self.fx_splat("Miss", 0, p)
            return
        self.wear_armour()
        self.play_sound("Hurt", (p.cx, p.cy))
        self.fx_splat(kind, damage, p)
        w = self.w
        w.fx_nudge(p, w.fx_away(attacker.player, p), w.fx_away_y(attacker.player, p), 130)
        self.fx_hurt_flash()
        self.fight_xp("Defence", damage * 0.005)
        self.update_skill("Hitpoints", "-%d" % damage)

    def pvp_fight_back(self, attacker):
        """Hit, you turn on whoever hit you (unless you're busy with something else)."""
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = attacker.player
            self.dirty_me = True

    # ----- beaten
    last_hit_by = None

    def pvp_killer(self):
        """The player whose blow this was, if the last blow was a player's, lately."""
        k = self.last_hit_by
        if k is None or not k.in_world() or not 0 <= self.now - self.pvp_hit_at < 30000:
            return None
        return k

    def pvp_lose_all(self):
        """Dying marked: everything goes but what's never lost (Keep.On.Death), on the ground where you fell, the
        killer's alone to see a while (Loot.Private.Seconds), then anyone's. No grave (older ones stay). The
        gold lost."""
        killer = self.pvp_killer()
        self.last_hit_by = None
        self.pvp_mark_until = 0
        d, w, p = self.data, self.w, self.player
        lost = []
        for e in self.inv:
            if self.kept_on_death(e.name) and e.name != "Gold_Coin(s)":
                continue
            lost.append((e.name, e.quantity, e.wear, e.stolen))
            e.alive = False
        self.inv[:] = [e for e in self.inv if e.alive]
        for i in range(1, d.equip_slots + 1):
            if self.equipped[i] and not self.kept_on_death(self.equipped[i]):
                lost.append((self.equipped[i], 1, self.equip_wear[i], self.equip_stolen[i]))
                self.equipped[i], self.equip_wear[i], self.equip_stolen[i] = "", 0, False
        self.recalc_equipment()
        self.check_locks(True)
        secs = val(d.config_read("Gameplay", "Loot.Private.Seconds", "10")) if killer is not None else 0
        for name, qty, wear, stolen in lost:
            copies, each = (1, qty) if d.stackable_quantity(name) > 1 else (qty, 1)
            iw, ih = d.sprite_size_of(3, name)
            for _ in range(int(copies)):
                w.drop_item(name, p.z, int(p.cx - iw / 2 + random_number(-14, 14)),
                            int(p.fy - ih + random_number(-8, 8)), each, first=killer, first_secs=secs, wear=wear,
                            stolen=stolen)
        if lost:
            self.display_message("You died marked: everything you carried lies where you fell.", "DAMAGE")
        if killer is not None:
            killer.display_message("%s died marked: what they carried lies where they fell, yours alone to take "
                                   "for a while." % self.player_name, "ACHIEVEMENT")
            killer.play_sound("Quest")
        self.dirty_me = True
        return sum(q for n, q, _, _ in lost if n == "Gold_Coin(s)")

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
            self.w.wonders.arena_kill(winner)
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
