"""A player's skills, hitpoints and spells, their fights (as the desktop game's combat.py; the NPC they fight is shared:
its hitpoints go down for everyone, and it fights whoever hit it), spells and status effects (extras.py)."""
from ashen.lb import val, word, trim, lbstr, distance, random_number, rnd, parse_quantity, apply_change, pretty

from .entity import NPC, PLAYER, MAPITEM, TYPE_NAMES
from .renames import SKILL_NAMES
from .shards import shard_words, SHARD, channeled_cost

EFFECTS = {
    "Poison": dict(ms=14000, every=2000, dmg=(1, 1), start="You've been poisoned!", end="The poison wears off."),
    "Burn": dict(ms=5000, every=1000, dmg=(1, 2), start="You're on fire!", end="The flames go out."),
    "Bleed": dict(ms=7000, every=1500, dmg=(1, 1), start="You're bleeding!", end="The bleeding stops."),
    "Chill": dict(ms=7000, every=0, dmg=(0, 0), start="You're chilled to the bone: slowed!", end="You warm up again."),
    # (drains: a skill lower for a while - the Stats tab shows it, 18/20)
    "Weaken": dict(ms=30000, every=0, dmg=(0, 0), skill=("Strength", -3), start="You feel weak: your Strength drains!",
                   end="Your strength comes back."),
    "Daze": dict(ms=25000, every=0, dmg=(0, 0), skill=("Channeling", -3), start="Your head spins: your Channeling "
                                                                                 "drains!",
                 end="Your head clears."),
    "Frailty": dict(ms=30000, every=0, dmg=(0, 0), skill=("Defence", -3), start="Your guard falters: your Defence "
                                                                             "drains!", end="Your guard steadies."),
}
CHILL_MOVE, CHILL_ATTACK = 0.6, 1.4


class CombatMixin:
    # =================================================================================================================
    # Skills
    # =================================================================================================================
    def skill_index(self, skill):
        s = trim(skill).upper()
        d = self.data
        for i in range(1, d.total_skills + 1):
            if d.skill_name[i].upper() == s:
                return i
        new = next((n for o, n in SKILL_NAMES.items() if o.upper() == s), None)   # (an old name: the skill now)
        return self.skill_index(new) if new else 0

    def level_of_xp(self, xp):
        return min(self.data.skill_max_level, max(1, int(xp)))

    def skill_level(self, skill):
        """A skill as it is now: its usual level, and whatever drains or boosts it for a while (what anything asking
        for a level goes by)."""
        if skill.upper() in ("HITPOINTS", "HITS", "HP"):
            return self.player.hp
        i = self.skill_index(skill)
        if not i:
            return 0
        return max(1, self.level_of_xp(self.skill_xp[i]) + self.skill_change(self.data.skill_name[i]))

    def base_skill_level(self, skill):
        """A skill's usual level, drains and boosts aside (hitpoints and your level go by it)."""
        i = self.skill_index(skill)
        return self.level_of_xp(self.skill_xp[i]) if i else 0

    def skill_change(self, skill):
        """How far drains (status effects) and boosts (a script's Boost.Skill) move a skill just now."""
        k = skill.upper()
        n = sum(EFFECTS[s]["skill"][1] for s in self.status if "skill" in EFFECTS[s] and
                EFFECTS[s]["skill"][0].upper() == k)
        b = self.skill_boosts.get(k)
        return n + (b["n"] if b and b["until"] > self.now else 0)

    def boost_skill(self, skill, n, seconds):
        """A skill up (or down) by n for a while (Boost.Skill): the last one for a skill replaces the one before."""
        i = self.skill_index(skill)
        if not i:
            return
        name = self.data.skill_name[i]
        self.skill_boosts[name.upper()] = {"n": int(n), "until": self.now + int(seconds * 1000), "skill": name}
        self.dirty_me = True

    def skill_boosts_tick(self):
        for k, b in list(self.skill_boosts.items()):
            if self.now >= b["until"]:
                del self.skill_boosts[k]
                self.display_message("Your %s is back to normal." % pretty(b["skill"]), "INFO")
                self.dirty_me = True

    def skills_now(self):
        """Every skill as it is now (the Stats tab shows it beside its usual level, when they differ)."""
        return [self.skill_level(self.data.skill_name[i]) if self.data.skill_name[i].upper() != "HITPOINTS"
                else self.level_of_xp(self.skill_xp[i]) for i in range(1, self.data.total_skills + 1)]

    def skill_xp_of(self, skill):
        i = self.skill_index(skill)
        return self.skill_xp[i] if i > 0 else 0

    def default_hitpoints_level(self):
        i = self.skill_index("Hitpoints")
        if i > 0 and self.skill_xp[i] < 1:
            self.skill_xp[i] = 10

    def update_max_hp(self):
        d = self.data
        levels = self.base_skill_level("Strength") + self.base_skill_level("Defence")
        self.player_max_hp = max(1, int(d.hp_base + levels * d.hp_per_level))
        self.player.max_hp = self.player_max_hp

    def max_hp_changed(self, old_max):
        self.update_max_hp()
        gain = self.player_max_hp - old_max
        if gain > 0:
            self.player.hp = min(self.player_max_hp, self.player.hp + gain)
            self.display_message("You now have %d hitpoints." % self.player_max_hp, "LEVELUP")
        elif gain < 0:
            self.player.hp = min(self.player.hp, self.player_max_hp)

    def update_skill(self, skill, amount, pop=True):
        """amount = +Q, -Q or =Q. "Hitpoints" changes the player's current hitpoints."""
        d = self.data
        if trim(skill).upper() in ("HITPOINTS", "HITS", "HP"):
            if self.dead_wait:              # (dead: nothing hurts or heals until they respawn)
                return
            old = self.player.hp
            new = int(min(self.player_max_hp, apply_change(old, amount)))
            if self.god_mode and new < old:
                new = old
            self.player.hp = max(0, new)
            if new > old:
                self.display_message("You gain %d hitpoint(s)." % (new - old), "ACHIEVEMENT")
                self.fx_splat("Heal", new - old, self.player)
            self.dirty_me = True
            if new <= 0:
                self.player_dies()
            return
        i = self.skill_index(skill)
        if i == 0:
            self.log("ERROR - Update.Skill: no skill '%s' in Config [Skills] List" % skill)
            return
        if self.skill_off[i] == 1:
            return
        if pop and trim(str(amount))[:1] == "+":
            self.fx_skill_pop(d.skill_name[i])
        old = self.level_of_xp(self.skill_xp[i])
        amount = trim(str(amount))
        if amount[:1] == "+":                    # (Config XP.Scale: every gain, and slower as you go)
            gain = val(amount[1:]) * d.xp_scale
            if d.xp_slowdown > 0:
                gain *= d.xp_slowdown / (d.xp_slowdown + old)
            amount = "+" + lbstr(round(gain, 5))
        self.skill_xp[i] = min(d.skill_max_level, max(0, apply_change(self.skill_xp[i], amount)))
        if amount[:1] == "+":
            self.reward_xp(d.skill_name[i], val(amount[1:]))     # (a quest's reward screen lists it)
        new = self.level_of_xp(self.skill_xp[i])
        self.dirty_me = True
        if new > old:
            self.display_message("LEVEL UP! Your %s level is now %d." % (pretty(d.skill_name[i]), new), "LEVELUP")
            self.play_sound("LevelUp")
            self.level_up_show(d.skill_name[i], new)
        if new < old:
            self.display_message("Your %s level has dropped to %d." % (pretty(d.skill_name[i]), new), "FAIL")
        if new != old and d.skill_name[i].upper() in ("STRENGTH", "DEFENCE"):
            self.max_hp_changed(self.player_max_hp)
        if new != old:
            self.dirty_quests = True
            self.check_locks(True)

    def player_level(self):
        names = [s.strip() for s in self.data.config_read("Gameplay", "Level.Skills", "Strength,Defence,Channeling").split(",")
                 if s.strip()]
        levels = sorted((self.base_skill_level(s) for s in names if self.skill_index(s) > 0), reverse=True)
        best = max(1, int(val(self.data.config_read("Gameplay", "Level.Best", "2")) or 2))
        top = levels[:best]
        return max(1, int(sum(top) / len(top))) if top else 1

    # =================================================================================================================
    # Hitpoints coming back, boosts wearing off
    # =================================================================================================================
    BOOST_WORDS = {   # kind: (what it does, +N, said when it wears off)
        "attack": ("+%s Attack (you hit harder)", "you hit as hard as before"),
        "defence": ("+%s Defence (harder to hurt)", "your Defence is back to normal"),
        "magic": ("+%s spell damage", "your spells are back to normal"),
        "sight": ("you see much further in the dark and fog", "your eyesight is back to normal"),
    }

    def update_player_health(self):
        now = self.now
        for kind in ("defence", "attack", "magic", "sight"):
            until = getattr(self, "spell_%s_until" % kind)
            if until > 0 and (now >= until or now < until - 600000):
                setattr(self, "spell_%s_bonus" % kind, 0)
                setattr(self, "spell_%s_until" % kind, 0)
                source = self.boost_from.pop(kind, "")
                what = self.BOOST_WORDS[kind][1]
                self.display_message("Your %s has worn off: %s." % (pretty(source), what) if source else
                                     "Your boost has worn off: %s." % what, "ERROR")
                self.play_sound("Miss")
                self.recalc_equipment()
                self.dirty_me = True
        if now < self.hp_regen_last:
            self.hp_regen_last = now
        hp = self.player.hp
        d = self.data
        if hp <= 0 or hp >= self.player_max_hp:
            self.hp_regen_last = now
            return
        if now - self.player_last_combat < d.hp_regen_delay * 1000 and now >= self.player_last_combat:
            self.hp_regen_last = now
            return
        if now - self.hp_regen_last < d.hp_regen_every * 1000:
            return
        self.hp_regen_last = now
        self.player.hp = hp + 1
        self.dirty_me = True

    def clear_boosts(self):
        self.clear_boosts_values()
        self.boost_from = {}
        self.dirty_me = True

    @staticmethod
    def how_long(seconds):
        seconds = int(seconds)
        if seconds >= 60 and seconds % 60 == 0:
            m = seconds // 60
            return "%d minute%s" % (m, "" if m == 1 else "s")
        return "%d seconds" % seconds

    def boost_words(self, spell):
        """What a Boost/Shield spell or potion does, in words: ["+5 spell damage", ...] (the potion's tooltip too)."""
        out = []
        for key in ("Attack", "Defence", "Magic"):
            n = val(self.spell_ini(spell, key, "0"))
            if n > 0:
                out.append(self.BOOST_WORDS[key.lower()][0] % lbstr(n))
        if val(self.spell_ini(spell, "Sight", "0")) > 0:
            out.append(self.BOOST_WORDS["sight"][0])
        return out

    # =================================================================================================================
    # Fighting
    # =================================================================================================================
    @staticmethod
    def combat_hits(attack, defence, per=4):
        chance = min(95, max(10, 60 + (attack - defence) * per))
        return rnd() * 100 < chance

    def player_attack_value(self):
        return self.skill_level("Strength") * 2 / 3 + 3 * (self.equip_attack_total + self.spell_attack_bonus)

    def player_defence_value(self):
        return self.skill_level("Defence") / 2 + 1.5 * (self.equip_defence_total + self.spell_defence_bonus)

    def armour_soak(self):
        return max(0, int((self.equip_defence_total + self.spell_defence_bonus) / 6))

    def player_max_hit(self):
        return 1 + int(self.skill_level("Strength") / 4) + 2 * (max(0, self.equip_attack_total) + self.spell_attack_bonus)

    def npc_max_hit(self, e):
        return 1 + max(0, int(self.w.stat_for(e, self, "strength") * self.data.monster_damage))

    def start_attack(self, e):
        self.stand_up()                       # (no fighting from a bench)
        if e.type == PLAYER and self.pvp_ok(self.session_of(e)):
            self.player_attack_target = e
            self.player_walk_stuck = 0
            self.dirty_me = True
            return
        if e.type != NPC:
            self.display_message("You can't attack that!", "FAIL")
            return
        self.player_attack_target = e
        self.player_walk_stuck = 0
        self.dirty_me = True

    def reach_extra(self, e):
        return max(0, int((e.w - 32) / 2))

    def player_distance_to(self, e):
        p = self.player
        if e.type == 2:     # TILE: where it was clicked
            return distance(p.cx, p.cy, self.script_cursor_x, self.script_cursor_y)
        return distance(p.cx, p.cy, e.cx, e.cy)

    def provoke(self, t):
        """This player hit NPC t: it fights back (or runs) at them."""
        if t.type == PLAYER:
            return
        t.in_combat = True
        t.last_combat = self.now
        if t.ai is not None and (t.target is None or not t.target.in_world() or t.ai.state not in (3, 4)):
            t.target = self
            self.w.npc_start_fight(t, t.ai, self, self.player_distance_to(t))

    def update_player_combat(self):
        t = self.player_attack_target
        if t is None:
            return
        if not t.alive or not self.w.visible_to(t, self) or t.z != self.player.z:
            self.player_attack_target = None
            self.dirty_me = True
            return
        if t.type == PLAYER and not self.pvp_ok(self.session_of(t)):
            self.player_attack_target = None
            self.dirty_me = True
            self.display_message("You can only fight other players on the arena's sand.", "FAIL")
            return
        p = self.player
        rng = 36 + self.reach_extra(t)
        bow = self.player_bow_range()
        if bow > 0:
            if self.w.in_line_of_sight(p.z, p.cx, p.cy, t.cx, t.cy):
                rng = max(rng, bow)
            else:
                bow = 0
        if self.player_distance_to(t) > rng:
            if not self.player_walk_active:
                if self.player_walk_stuck > 15:
                    self.display_message("You can't reach the %s!" % self.display_name(t), "FAIL")
                    self.player_attack_target = None
                    self.player_walk_stuck = 0
                    self.dirty_me = True
                    return
                self.walk_player_to(t.cx, t.cy, 0, rng - 4)
            return
        if self.player_walk_active and self.pending_ent is None:
            self.player_walk_active = False
        now = self.now
        if now - self.player_last_attack < p.attack_speed * 1000 * self.attack_slowdown():
            return
        self.player_last_attack = now
        self.player_last_combat = now
        self.provoke(t)
        self.w.npc_face(p, p.cx, p.cy, t.cx, t.cy)
        if bow > 0 and self.player_distance_to(t) > 36 + self.reach_extra(t):
            self.remove_inventory_item(self.entity_ini(self.equipped[1], "Ammo", ""), 1)
            self.play_sound("Miss", (p.cx, p.cy))
            self.w.fx_shot(p, "Arrow_Missile", t, "ARROW", self)
            return
        self.fx_nudge(p, -self.w.fx_away(t, p), -self.w.fx_away_y(t, p), 110)
        self.player_strike(t, False)

    def player_strike(self, t, ranged):
        if not t.alive:
            return
        if t.type == PLAYER:
            self.pvp_strike(t, ranged)
            return
        w = self.w
        if not self.combat_hits(self.player_attack_value(), 3 * w.stat_for(t, self, "defence"), 3):
            self.play_sound("Miss", (t.cx, t.cy))
            self.fx_splat("Miss", 0, t)                 # (each blow shows over who it lands on, not in the chat)
            return
        max_hit = self.player_max_hit()
        damage = random_number(1, max_hit)
        if rnd() * 100 < 5 + self.skill_level("Strength") * 2 / 15:
            damage = max_hit + random_number(0, int(max_hit / 2))
            self.play_sound("Crit", (t.cx, t.cy))
            self.fx_splat("Crit", damage, t)
        else:
            self.play_sound("Fight%d" % random_number(1, 3), (t.cx, t.cy))
            self.fx_splat("Hit", damage, t)
        self.wear_weapon()
        self.fx_anim("Slash", t.cx, t.cy, 240)
        self.fx_nudge(t, w.fx_away(self.player, t), w.fx_away_y(self.player, t), 130)
        self.update_skill("Strength", "+" + lbstr(damage * 0.01), pop=False)
        self.damage_npc(t, damage)

    def player_bow_range(self):
        weapon = self.equipped[1]
        if not weapon:
            return 0
        rng = val(self.entity_ini(weapon, "Range", "0"))
        if rng <= 0:
            return 0
        ammo = self.entity_ini(weapon, "Ammo", "")
        if ammo and self.items_held(ammo) <= 0:
            now = self.now
            if now - self.ammo_warned > 8000 or now < self.ammo_warned:
                self.ammo_warned = now
                self.display_message("You have no %s left: you can only club them with the bow." % pretty(ammo), "FAIL")
            return 0
        return rng

    def damage_npc(self, e, damage):
        self.break_invisibility()                           # (a blow struck: seen)
        self.w.waves.hit(e, self)
        hp = e.hp - damage
        slayer = self.entity_ini(e.name, "Slain.By", "")         # (only one weapon gives it its death blow)
        if hp <= 0 and slayer:
            s = self.equip_slot_index("Weapon")
            if not (s > 0 and self.equipped[s] == slayer):
                hp = 1
                if self.now - getattr(self, "slayer_warned", -10 ** 9) > 6000:
                    self.slayer_warned = self.now
                    self.display_message("Your blows can't reach its heart. Only the %s can." % pretty(slayer), "FAIL")
        e.hp = max(0, hp)
        if hp <= 0:
            self.kill_npc(e)

    def kill_npc(self, e):
        """This player killed NPC e: gone for everyone (it comes back later), its loot on the ground for anyone."""
        w = self.w
        name, etype = e.name, e.type
        self.display_message("You have killed the %s!" % self.display_name(e), "ACHIEVEMENT")
        self.play_sound("Kill_" + (self.entity_ini(name, "Kill.Sound", "") or "Beast"), (e.cx, e.cy))
        self.add_npc_drops(e)
        w.waves.killed(e, self)
        m = w.maps.get(e.map)
        if e.source == "MAP" and e.owner is None and m is not None:
            respawn = e.respawn_delay if e.respawn_delay > 0 else self.data.npc_respawn_delay
            options = e.ai.options if e.ai is not None and e.ai.options else "-"
            w.add_action_to_queue("ADD", name, TYPE_NAMES[etype], options, m.name,
                                  w.local_coords(m, e.orig_x, e.orig_y), respawn)
        script = self.find_action_script("Kill", name, etype, e.npc_id)
        self.fx_anim("Puff", e.cx, e.cy, 500)
        w.remove_entity(e)
        if script:
            self.start_script(script, False)

    def add_npc_drops(self, e):
        """Its Drops on the ground (the killer's to pick up first), and its Shard Remnants, if it leaves any
        (remnants.py: a kill gives no Shards of itself)."""
        w = self.w
        drops = self.entity_ini(e.name, "Drops", "")
        drop_x, drop_y = e.cx, e.fy
        loot_secs = val(self.data.config_read("Gameplay", "Loot.Private.Seconds", "10"))

        def drop(name, amount):
            copies, each = (1, amount) if self.stackable_quantity(name) > 1 else (min(amount, 10), 1)
            iw, ih = self.data.sprite_size_of(3, name)
            for _ in range(int(copies)):
                x = int(drop_x - iw / 2 + random_number(-8, 8))
                y = int(drop_y - ih + random_number(-4, 6))
                item = w.add_map_item(name, e.z, x, y, each, e.owner)
                if item is not None:
                    item.source = "DROPPED"
                    if item.owner is None and loot_secs > 0:          # (the killer's to pick up first)
                        item.private_to = self
                        item.public_at = self.now + loot_secs * 1000
                    m = w.maps.get(item.map)
                    if m is not None and item.owner is None:
                        w.add_action_to_queue("REMOVE", name, "MapItem", lbstr(each), m.name,
                                              w.local_coords(m, x, y), self.data.item_despawn_delay)
        i = 1
        while word(drops, i) != "":
            dd = word(drops, i)
            name = word(dd, 1, ",")
            amount_s = word(dd, 2, ",") or "1"
            percent = word(dd, 3, ",") or "100"
            if rnd() * 100 < val(percent):
                amount = parse_quantity(amount_s) if "-" in amount_s else val(amount_s)
                if amount > 0:
                    drop(name, amount)
            i += 1
        self.remnants_on_death(e, drop)

    # ----- NPCs hitting this player (the world's NPC AI calls these)
    def npc_shoot(self, e, missile):
        self.player_last_combat = self.now
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = e
            self.dirty_me = True
        self.w.sound(self.entity_ini(e.name, "Missile.Sound", "Miss"), e.z, e.cx, e.cy)
        self.w.fx_shot(e, missile, self.player, e, self)

    def npc_shot_hits(self, e):
        if e is None or not e.alive:
            return
        impact = self.entity_ini(e.name, "Missile.Impact", "")
        if impact:
            self.fx_anim(impact, self.player.cx, self.player.cy, 400)
        self.npc_attack_player(e, ranged=True)

    def npc_attack_player(self, e, ranged=False):
        now = self.now
        p = self.player
        w = self.w
        self.player_last_combat = now
        if not ranged:
            w.fx_nudge(e, -w.fx_away(p, e), -w.fx_away_y(p, e), 110)
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = e
            self.dirty_me = True
        if self.god_mode:
            self.fx_splat("Miss", 0, p)
            return
        if not self.combat_hits(w.stat_for(e, self, "strength") * 3 + 2, self.player_defence_value(), 3):
            self.fx_splat("Miss", 0, p)
            if self.equip_defence_total + self.spell_defence_bonus > 0:
                self.play_sound("Block", (p.cx, p.cy))
            self.update_skill("Defence", "+0.03", pop=False)
            return
        self.wear_armour()
        damage = self.resist_damage(e, random_number(1, self.npc_max_hit(e))) - self.armour_soak()
        if damage <= 0:
            self.fx_splat("Miss", 0, p)
            self.play_sound("Block", (p.cx, p.cy))
            self.update_skill("Defence", "+0.03", pop=False)
            return
        self.play_sound("Hurt", (p.cx, p.cy))
        self.fx_splat("Hit", damage, p)
        w.fx_nudge(p, w.fx_away(e, p), w.fx_away_y(e, p), 130)
        self.fx_hurt_flash()
        self.update_skill("Defence", "+" + lbstr(damage * 0.01), pop=False)
        self.update_skill("Hitpoints", "-%d" % damage)
        if p.hp > 0:
            self.status_on_hit(e)
        hp = p.hp
        if 0 < hp <= self.player_max_hp / 4 and (now - self.low_hp_warned > 10000 or now < self.low_hp_warned):
            self.low_hp_warned = now
            self.display_message("You are badly hurt! Eat something, drink a potion or run!", "ERROR")

    def player_dies(self):
        if self.dead_wait:                  # (dead already)
            return
        if self.god_mode:
            self.player.hp = self.player_max_hp
            return
        if self.in_arena():
            self.arena_defeat()
            return
        d = self.data
        self.display_message("Oh dear, you are dead!", "ERROR")
        self.play_sound("Death", (self.player.cx, self.player.cy))
        self.play_sound("Death")                            # (to them, whatever the distance)
        gold = self.items_held("Gold_Coin(s)")
        lost = int(gold * d.death_gold_loss / 100)
        if lost > 0:
            self.remove_inventory_item("Gold_Coin(s)", lost)
            self.display_message("You lost %d gold coins." % lost, "DAMAGE")
        self.fx_anim("Puff", self.player.cx, self.player.cy, 500)
        self.clear_boosts()
        self.status_reset()
        self.grave_leave()
        self.player.hp = self.player_max_hp
        self.player_attack_target = None
        self.stop_player_walk()
        for e in self.w.ents:
            if e.type == NPC and e.target is self and e.ai is not None:
                self.w.npc_give_up(e, e.ai)
        # Dead: they stay where they fell (unseen, nothing can touch them) until they choose to wake (Respawn).
        # Nothing carries on: no walking (a key held down when they fell), no fighting, no bleeding
        self.keyboard_direction = 0
        self.pending_verb, self.pending_ent = "", None
        self.item_in_use = None
        bed = self.home_respawn()
        if bed is not None:
            self.dead_wait = (bed[0], bed[1], bed[2], True)
        else:
            self.dead_wait = (d.start_map, d.start_x, d.start_y, False)
        self.player_visible = False
        self.emit({"t": "died", "lost": lost, "grave": bool(self.grave), "minutes": self.grave_minutes(),
                   "bed": bed is not None})
        self.dirty_me = True

    def respawn(self):
        """The player chose to wake up again (after dying): at their bed at home, or the start."""
        if not self.dead_wait:
            return
        m, x, y, bed = self.dead_wait
        self.dead_wait = None
        self.keyboard_direction = 0
        self.stop_player_walk()
        self.status_reset()
        self.player_visible = val(self.data.config_read("Gameplay", "Player.Visible", "1")) == 1
        self.player.hp = self.player_max_hp
        if self.w.map_named(m) is not None:
            self.teleport(m, x, y)
        self.display_message("You wake in your own bed." if bed else "You wake up, alive again.", "INFO")
        self.emit({"t": "respawned"})
        self.dirty_me = True

    # =================================================================================================================
    # Spells (data\\Spells.ini): reading a scroll teaches its spell for good; casting it spends Shards (shards.py)
    # =================================================================================================================
    def spell_ini(self, spell, key, default):
        """Spells.ini, at the rank they know the spell to (Damage.2 from rank 2 on: shards.py)."""
        return self.spell_ini_at(spell, key, default, max(1, self.spells_known.get(spell, 1)))

    @staticmethod
    def spell_roll(range_text):
        a = val(word(range_text, 1, "-"))
        b = val(word(range_text, 2, "-"))
        return random_number(int(a), int(max(a, b)))

    def spell_target_ok(self, e):
        if e is not None and e.type == PLAYER:
            return self.pvp_ok(self.session_of(e))
        return e is not None and e.alive and e.type == NPC and e.active and self.w.visible_to(e, self)

    def spell_auto_target(self, rng):
        p = self.player
        if self.spell_target_ok(self.player_attack_target):
            if self.player_distance_to(self.player_attack_target) <= rng:
                return self.player_attack_target
        best = rng + 1
        found = None
        for e in self.w.ents:
            if e.type == NPC and e.z == p.z and self.w.hostile_for(e, self) and self.spell_target_ok(e):
                dd = distance(p.cx, p.cy, e.cx, e.cy)
                if dd < best and self.w.in_line_of_sight(p.z, p.cx, p.cy, e.cx, e.cy):
                    best, found = dd, e
        return found

    def spell_is_potion(self, spell):
        return self.spell_ini(spell, "Kind", "Scroll").upper() == "POTION"

    def spell_chance(self, spell):
        level = val(self.spell_ini(spell, "Level", "1"))
        return min(98, max(20, 60 + (self.skill_level(self.spell_ini(spell, "Skill", "Channeling")) - level) * 14))

    def spell_cost(self, spell):
        """A spell's Shards a cast: its Cost, less the saving your Channeling gives (channeled_cost)."""
        return channeled_cost(val(self.spell_ini(spell, "Cost", "0")), self.skill_level("Channeling"), self.data)

    def spell_cooldown_left(self, spell):
        until = self.cooldowns.get(spell)
        if until is not None and until > self.now and until - self.now < 3600000:
            return int((until - self.now) / 1000) + 1
        return 0

    def spell_start_cooldown(self, spell):
        seconds = val(self.spell_ini(spell, "Cooldown", "0"))
        if seconds > 0 and (spell in self.cooldowns or len(self.cooldowns) < 30):
            self.cooldowns[spell] = self.now + seconds * 1000

    def spell_begin(self, scroll, spell):
        """The cast going ahead: its cooldown starts, then it takes hold (its Shards spent) or it fizzles (nothing
        spent). A potion is drunk."""
        self.spell_fizzled = False
        attack = self.spell_ini(spell, "Effect", "Bolt").upper() in ("BOLT", "AREA")
        p = self.player
        potion = self.spell_is_potion(spell)
        if not potion:
            self.break_invisibility()                       # (a spell cast: seen)
        if not potion:
            self.spell_start_cooldown(spell)
            self.player_last_cast = self.now
            chance = self.spell_chance(spell)
            if rnd() * 100 >= chance:
                self.play_sound("Fizzle", (p.cx, p.cy))
                self.fx_anim("Puff", p.cx, p.cy, 400)
                self.display_message("The spell slips from your grasp: no Shards spent. (%d%% chance: it works more "
                                     "surely as your Magic grows.)" % chance, "FAIL")
                xp = val(self.spell_ini(spell, "XP", "0")) / 2
                if xp > 0:
                    self.update_skill(self.spell_ini(spell, "Skill", "Channeling"), "+" + lbstr(xp), pop=not attack)
                self.spell_fizzled = True
                return
            if not self.spend_shards(self.spell_cost(spell), pretty(spell)):
                self.spell_fizzled = True
                return
        else:
            self.remove_inventory_item(scroll, 1)
        leaves = self.spell_ini(spell, "Leaves", "")
        if leaves:
            self.add_inventory_item(leaves, 1)
        if potion:
            effect = self.spell_ini(spell, "Effect", "").upper()
            if effect not in ("BOOST", "SHIELD"):                   # (a boost says what it does itself)
                self.display_message("You drink the %s." % pretty(scroll), "SUCCESS")
            self.give_shards(int(val(self.spell_ini(spell, "Shards", "0"))), "Its magic settles into Shards")
        else:
            self.play_sound("SpellCast", (p.cx, p.cy))
        xp = val(self.spell_ini(spell, "XP", "0"))
        if xp > 0:
            self.update_skill(self.spell_ini(spell, "Skill", "Channeling"), "+" + lbstr(xp), pop=not attack)
        self.dirty_me = True

    def spell_terms(self, spell):
        """What a cast takes: "3 Shards a cast, ready again after 0.8 s"."""
        cd = val(self.spell_ini(spell, "Cooldown", "0"))
        return "%s a cast%s" % (shard_words(int(self.spell_cost(spell))),
                                (", ready again after %s s" % lbstr(cd)) if cd > 0 else "")

    def learn_spell(self, item, spell):
        """A spell's scroll read: the spell is theirs for good, or (an upgrade's scroll, Rank=2...) raised to its rank.
        The scroll goes, unless it's one that Keep=1."""
        rank = self.scroll_rank(item.name)
        title = self.spell_title(spell, rank)
        if self.spell_rank(spell) < rank - 1:
            self.refuse("This scroll raises %s to %s: learn %s first." %
                        (pretty(spell), title, self.spell_title(spell, rank - 1)))
            return
        level = val(self.spell_ini_at(spell, "Level", "1", rank))
        skill = self.spell_ini(spell, "Skill", "Channeling")
        if self.skill_level(skill) < level:
            self.refuse("You need level %s %s to learn %s (you have %d). Keep the scroll till you're ready." %
                        (lbstr(level), pretty(skill), title, self.skill_level(skill)))
            return
        self.spells_known[spell] = rank
        if val(self.spell_ini(spell, "Keep", "0")) != 1:
            self.remove_inventory_item(item.name, 1)
        self.play_sound("SpellCast")
        self.fx_anim(self.spell_ini(spell, "Impact", "") or "Teleport_Glow", self.player.cx, self.player.cy, 500)
        if rank > 1:
            self.display_message("Your %s grows stronger: it's %s now (%s)." %
                                 (pretty(spell), title, self.spell_terms(spell)), "ACHIEVEMENT")
        else:
            self.display_message("You learn %s! It's yours for good: %s. Cast it from Channeling, in the Stats "
                                 "box." % (title, self.spell_terms(spell)), "ACHIEVEMENT")
        self.dirty_me = True
        self.dirty_quests = True

    def spell_learnable(self, name):
        """The spell an item teaches, if it's a spell's scroll (not a potion), else ""."""
        spell = self.entity_ini(name, "Spell", "")
        return spell if spell and not self.spell_is_potion(spell) else ""

    def cast_scroll(self, item, target):
        """A scroll or potion used: a potion is drunk; a scroll teaches its spell (it's used up), and that's all it
        does - a spell is cast from Channeling, not from a scroll."""
        spell = self.entity_ini(item.name, "Spell", "")
        if spell == "":
            self.display_message("Nothing interesting happens.", "FAIL")
            return
        if not self.spell_learnable(item.name):
            self.cast_spell(spell, target, item)        # (a potion: drunk)
        elif self.spell_rank(spell) < self.scroll_rank(item.name):
            self.learn_spell(item, spell)
        else:
            self.refuse("You already know this.")

    def ready_spell(self, spell, name, what="who"):
        """A spell that needs something to be cast at, and nothing chosen: it's held ready, and the next thing
        clicked is what it's cast at (the browser sends it back with the spell)."""
        self.emit({"t": "ready", "spell": spell})
        self.display_message("Choose %s to cast %s at: click %s. (Right-click or Esc: let it go.)" % (
            what, name, "them" if what == "who" else "it"), "INFO")

    def cast_spell(self, spell, target, item=None):
        """Casts a known spell (or drinks a potion, item): at target, or (a bolt, none chosen) the foe you're
        fighting or the nearest, or else held ready for a click on who it's for."""
        scroll = item.name if item is not None else ""
        if not self.spell_is_potion(spell) and spell not in self.spells_known:
            self.refuse("You don't know %s yet: read its scroll to learn it." % pretty(spell))
            return
        w = self.w
        name = self.spell_title(spell) if not self.spell_is_potion(spell) else pretty(spell)
        level = val(self.spell_ini(spell, "Level", "1"))
        skill = self.spell_ini(spell, "Skill", "Channeling")
        potion = self.spell_is_potion(spell)
        if not potion and self.skill_level(skill) < level:
            self.refuse("You need level %s %s to cast %s (you have %d)." %
                        (lbstr(level), pretty(skill), name, self.skill_level(skill)))
            return
        if not potion:
            wait = self.spell_cooldown_left(spell)
            if wait > 0:
                self.display_message("%s isn't ready yet: %d more second(s)." % (name, wait), "FAIL")
                return
            cost = self.spell_cost(spell)
            if self.shards() < cost:
                self.short_of_shards(cost, name)
                return
        now = self.now
        gap = self.shard_setting("Cast.Gap", 0.8) * 1000
        if not potion and now - self.player_last_cast < gap and now >= self.player_last_cast:
            self.display_message("You're still gathering your wits after the last spell.", "FAIL")
            return
        p = self.player
        pcx, pcy = p.cx, p.cy
        effect = self.spell_ini(spell, "Effect", "Bolt").upper()
        if effect == "BOLT":
            rng = val(self.spell_ini(spell, "Range", "256"))
            if target is None and item is None:
                target = self.spell_auto_target(rng)    # (from Channeling or the hotbar: your foe, or the nearest)
                if target is None:
                    self.ready_spell(spell, name)
                    return
            if target is None:
                # (no target yet: the scroll is held ready - the next thing clicked is what it's cast at)
                self.item_in_use = item
                self.emit({"t": "use", "uid": item.uid})
                self.display_message("Choose who to cast %s at: click them. (Right-click or Esc: put it away.)" % name,
                                     "INFO")
                return
            if not self.spell_target_ok(target):
                self.display_message("There's nothing to cast %s at there." % name, "FAIL")
                return
            if self.player_distance_to(target) > rng + 8:
                self.display_message("The %s is too far away." % self.display_name(target), "FAIL")
                return
            if not w.in_line_of_sight(p.z, pcx, pcy, target.cx, target.cy):
                self.display_message("You can't see the %s from here." % self.display_name(target), "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            w.npc_face(p, pcx, pcy, target.cx, target.cy)
            self.provoke(target)
            self.player_last_combat = now
            missile = self.spell_ini(spell, "Missile", "")
            if missile == "":
                self.spell_hit(spell, target)
            else:
                w.fx_shot(p, missile, target, spell, self)
        elif effect == "GRASP":
            rng = val(self.spell_ini(spell, "Range", "192"))
            if target is None and item is None:
                self.ready_spell(spell, name, "what")
                return
            if target is None:
                self.item_in_use = item
                self.emit({"t": "use", "uid": item.uid})
                self.display_message("Choose what to cast %s at: click it. (Right-click or Esc: put it away.)" % name,
                                     "INFO")
                return
            script = ""
            if target.type != MAPITEM:
                script = self.find_action_script("Grasp", target.name, target.type, getattr(target, "npc_id", ""))
                if not script:
                    self.display_message("%s finds nothing there to take hold of." % name, "FAIL")
                    return
            elif not w.visible_to(target, self):
                return
            if self.player_distance_to(target) > rng + 8:
                self.display_message("The %s is too far away." % self.display_name(target), "FAIL")
                return
            if not w.in_line_of_sight(p.z, pcx, pcy, target.cx, target.cy):
                self.display_message("You can't see the %s from here." % self.display_name(target), "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            w.npc_face(p, pcx, pcy, target.cx, target.cy)
            self.spell_glow(spell)
            self.fx_anim(self.spell_ini(spell, "Impact", "Puff") or "Puff", target.cx, target.cy, 500)
            if script:
                self.clicked_ent = target
                self.start_script(script, True)
            else:
                self.display_message("An unseen hand takes hold of the %s..." % self.display_name(target), "COMBAT")
                self.pickup_map_item(target, reach=rng + 40)
        elif effect == "AREA":
            radius = val(self.spell_ini(spell, "Radius", "128"))
            targets = [e for e in w.ents if e.type == NPC and e.z == p.z and w.hostile_for(e, self) and
                       self.spell_target_ok(e) and distance(pcx, pcy, e.cx, e.cy) <= radius and
                       w.in_line_of_sight(p.z, pcx, pcy, e.cx, e.cy)]
            targets += [s.player for s in w.sessions.values() if self.pvp_ok(s) and
                        distance(pcx, pcy, s.player.cx, s.player.cy) <= radius and
                        w.in_line_of_sight(p.z, pcx, pcy, s.player.cx, s.player.cy)]
            if not targets:
                self.display_message("There are no enemies close enough for %s." % name, "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.player_last_combat = now
            held = []
            for e in targets:
                if e.alive:
                    self.provoke(e)
                    if self.spell_hit(spell, e) and e.alive:
                        held.append(e)
            if held:                                    # (one line for the lot, not one a foe)
                how = self.spell_ini(spell, "Freeze.Word", "frozen") or "frozen"
                who = "The %s is" % self.display_name(held[0]) if len(held) == 1 else "%d foes are" % len(held)
                self.display_message("%s %s for %s seconds!" % (who, how, lbstr(val(self.spell_ini(spell, "Freeze", "0")))),
                                     "COMBAT")
        elif effect == "HEAL":
            if p.hp >= self.player_max_hp:
                self.display_message("You already have full health!", "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            bonus = 0 if potion else int(self.skill_level("Channeling") * 2 / 3) + self.equip_magic_total
            self.update_skill("Hitpoints", "+%d" % (self.spell_roll(self.spell_ini(spell, "Heal", "5-10")) + bonus))
        elif effect in ("SHIELD", "BOOST"):
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            seconds = max(1, val(self.spell_ini(spell, "Duration", "60")))
            for key in ("Attack", "Defence", "Magic", "Sight"):
                amount = val(self.spell_ini(spell, key, "0"))
                if amount > 0:
                    setattr(self, "spell_%s_bonus" % key.lower(), amount)
                    setattr(self, "spell_%s_until" % key.lower(), now + seconds * 1000)
                    self.boost_from[key.lower()] = scroll
            what = ", ".join(self.boost_words(spell)) or "you feel stronger"
            done = "You drink the %s" % pretty(scroll) if potion else "You cast %s" % pretty(spell)
            self.display_message("%s: %s for %s." % (done, what, self.how_long(seconds)), "ACHIEVEMENT")
            self.recalc_equipment()
            self.dirty_me = True
        elif effect == "TELEPORT":
            m = self.spell_ini(spell, "Map", "").replace(" ", "")
            x = val(self.spell_ini(spell, "X", "0"))
            y = val(self.spell_ini(spell, "Y", "0"))
            if m == "":
                m, x, y = self.data.start_map, self.data.start_x, self.data.start_y
            if not self.data.map_exists(m):
                self.display_message("The spell fizzles: it has nowhere to take you.", "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            self.display_message("The world spins around you...", "SUCCESS")
            self.player_attack_target = None
            self.teleport(m, x, y)
        elif effect == "INVISIBLE":                          # (tricks.py)
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.go_invisible(max(1, val(self.spell_ini(spell, "Duration", "45"))),
                              "You drink the %s" % pretty(scroll) if potion else "You cast %s" % pretty(spell))
        elif effect == "SWAP":
            if target is None and item is None:             # (from the spellbook or the hotbar: the nearest one)
                rng = val(self.spell_ini(spell, "Range", "160"))
                near = [e for e in w.ents if e.z == p.z and self.swap_ok(e) and not e.hostile and
                        w.visible_to(e, self) and self.player_distance_to(e) <= rng]
                target = min(near, key=self.player_distance_to) if near else None
                if target is None:
                    self.display_message("There's no creature in reach to swap bodies with.", "FAIL")
                    return
            if target is None:
                self.item_in_use = item
                self.emit({"t": "use", "uid": item.uid})
                self.display_message("Choose who to swap bodies with: click them. (Right-click or Esc: put it "
                                     "away.)", "INFO")
                return
            if self.swap or not self.swap_ok(target):
                self.display_message("You can't swap bodies with %s." % ("anyone just now" if self.swap else
                                                                        "that"), "FAIL")
                return
            if self.player_distance_to(target) > val(self.spell_ini(spell, "Range", "160")) + 8:
                self.display_message("The %s is too far away." % self.display_name(target), "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.swap_with(target, max(1, val(self.spell_ini(spell, "Duration", "30"))), "You cast %s" % name)
        elif effect == "HOME":
            if not self.home_spell_ok():
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            self.display_message("The world spins around you...", "SUCCESS")
            self.go_home()
        else:
            self.display_message("Nothing interesting happens.", "FAIL")

    def spell_glow(self, spell):
        p = self.player
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, p.cx, p.cy, 600)
        self.play_sound(self.spell_ini(spell, "Sound", ""), (p.cx, p.cy))

    def spell_hit(self, spell, e):
        if not self.spell_target_ok(e):
            return
        w = self.w
        damage = (self.spell_roll(self.spell_ini(spell, "Damage", "1-3")) + int(self.skill_level("Channeling") / 2) +
                  self.equip_magic_total + self.spell_magic_bonus)
        if e.type == PLAYER:
            self.pvp_spell_hit(spell, e, damage)
            return
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, e.cx, e.cy, 450)
        self.play_sound(self.spell_ini(spell, "Sound", ""), (e.cx, e.cy))
        self.fx_splat("Hit", damage, e)
        self.fx_nudge(e, w.fx_away(self.player, e), w.fx_away_y(self.player, e), 130)
        self.provoke(e)
        slow = self.spell_ini(spell, "Slow", "")
        if slow and damage < e.hp:
            if e.slow_until is None:
                e.normal_speed = e.move_speed
            e.move_speed = e.normal_speed * max(5, val(word(slow, 1, ","))) / 100
            e.slow_until = self.now + max(1, val(word(slow, 2, ","))) * 1000
            self.display_message("The %s slows down." % self.display_name(e), "COMBAT")
        held = False
        freeze = val(self.spell_ini(spell, "Freeze", "0"))
        if freeze > 0 and damage < e.hp and val(self.entity_ini(e.name, "Freeze.Immune", "0")) != 1:
            e.frozen_until = self.now + freeze * 1000
            e.frozen_word = self.spell_ini(spell, "Freeze.Word", "frozen") or "frozen"
            held = True
        self.damage_npc(e, damage)
        return held

    # =================================================================================================================
    # Status effects
    # =================================================================================================================
    def status_reset(self):
        for name in list(self.status):
            self.status_end(name, quiet=True)
        self.status = {}
        self.skill_boosts = {}                  # (boosts and drains end on death, as buffs do)

    def status_start(self, name):
        fx = EFFECTS.get(name)
        if fx is None or self.god_mode or self.resists(name):
            return
        if name not in self.status:
            self.display_message(fx["start"], "DAMAGE")
            if name == "Chill":
                self.player.move_speed *= CHILL_MOVE
        self.status[name] = {"until": self.now + fx["ms"], "next": self.now + fx["every"]}
        self.dirty_me = True

    @staticmethod
    def status_words(name):
        """What a status effect does, in a few words (the effects bar's hover)."""
        fx = EFFECTS.get(name)
        if fx is None:
            return ""
        if name == "Chill":
            return "Slowed: you move and strike slower"
        if "skill" in fx:
            return "%s %d" % (fx["skill"][0], fx["skill"][1])
        lo, hi = fx["dmg"]
        every = fx["every"] / 1000.0
        return "%s damage every %s" % (lo if lo == hi else "%d-%d" % (lo, hi),
                                       "second" if every == 1 else "%g s" % every)

    def status_end(self, name, quiet=False):
        if name not in self.status:
            return
        del self.status[name]
        if name == "Chill":
            self.player.move_speed /= CHILL_MOVE
        if not quiet:
            self.display_message(EFFECTS[name]["end"], "INFO")
        self.dirty_me = True

    def status_tick(self):
        self.tricks_tick()
        if self.skill_boosts:
            self.skill_boosts_tick()
        if not self.status:
            return
        now = self.now
        for name in list(self.status):
            s, fx = self.status[name], EFFECTS[name]
            if now >= s["until"] or now < s["until"] - fx["ms"] - 1000:
                self.status_end(name)
                continue
            if fx["every"] and now >= s["next"]:
                s["next"] = now + fx["every"]
                dmg = random_number(*fx["dmg"])
                if dmg > 0 and self.player.hp > 0:
                    self.fx_splat("Hit", dmg, self.player)
                    self.player_last_combat = now
                    self.update_skill("Hitpoints", "-%d" % dmg)
                    if self.player.hp <= 0:
                        return

    def status_on_hit(self, e):
        on = trim(self.entity_ini(e.name, "On.Hit", ""))
        if not on:
            return
        name, chance = word(on, 1), val(word(on, 2)) or 100
        if name in EFFECTS and rnd() * 100 < chance:
            self.status_start(name)

    def resists(self, effect):
        for s in range(1, self.data.equip_slots + 1):
            it = self.equipped[s]
            if it and effect in trim(self.entity_ini(it, "Resists", "")).split():
                return True
        return False

    def resist_damage(self, e, damage):
        on = word(trim(self.entity_ini(e.name, "On.Hit", "")), 1)
        if on and self.resists(on):
            return damage - max(1, damage // 3) if damage > 1 else damage
        return damage

    def attack_slowdown(self):
        return CHILL_ATTACK if "Chill" in self.status else 1.0

    def drink_cure(self, e):
        cures = trim(self.entity_ini(e.name, "Cures", "")).split()
        self.remove_inventory_item(e.name, 1)
        self.play_sound("EatFood")
        ended = [c for c in cures if c in self.status]
        for c in ended:
            self.status_end(c, quiet=True)
        self.display_message("You drink the %s.%s" % (pretty(e.name), " You feel much better!" if ended else ""),
                             "SUCCESS")
        food = val(self.entity_ini(e.name, "Food.Value", "0"))
        if food > 0:
            self.update_skill("Hitpoints", "+" + lbstr(food))
