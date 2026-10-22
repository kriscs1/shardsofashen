"""Combat, combat feedback (splats, impact animations, missiles, lunges, the hurt flash), spells, the gear the player is
seen wearing, health bars, skills, hitpoints and mana."""
import os

import pygame

from . import ini
from .entity import PLAYER, NPC, MISSILE, TEMPORARY, TYPE_NAMES
from .lb import val, word, trim, lbstr, distance, random_number, rnd, parse_quantity, apply_change, pretty


class Fx:
    """One effect. kind: 1 = splat (a number that rises and goes), 2 = animation (<base>1..4), 3 = missile (flies to its
    target, then Fx.Arrive), 4 = nudge (an entity drawn a few pixels off its place), 5 = hurt flash strip (screen
    space), 6 = a skill's icon over the player's head."""

    def __init__(self, kind, image, x, y, start, end):
        self.kind = kind
        self.image = image
        self.x = x
        self.y = y
        self.draw_y = y
        self.start = start
        self.end = end
        self.base = ""
        self.target = None
        self.tag = ""
        self.ent = None
        self.mirror = False
        self.layer = TEMPORARY


class CombatMixin:
    # =================================================================================================================
    # Skills, hitpoints and mana
    # =================================================================================================================
    def skill_index(self, skill):
        s = trim(skill).upper()
        for i in range(1, self.total_skills + 1):
            if self.skill_name[i].upper() == s:
                return i
        return 0

    def level_of_xp(self, xp):
        return min(self.skill_max_level, max(1, int(xp)))

    def skill_level(self, skill):
        if skill.upper() in ("HITPOINTS", "HITS", "HP"):
            return self.player.hp
        i = self.skill_index(skill)
        if i == 0:
            return 0
        return self.level_of_xp(self.skill_xp[i])

    def skill_xp_of(self, skill):
        i = self.skill_index(skill)
        return self.skill_xp[i] if i > 0 else 0

    def skill_shown(self, i):
        return self.skill_name[i].upper() != "HITPOINTS" and self.skill_off[i] == 0

    def skill_of_row(self, row):
        for i in range(1, self.total_skills + 1):
            if self.skill_shown(i):
                row -= 1
                if row == 0:
                    return i
        return 0

    def level_progress(self, xp):
        level = self.level_of_xp(xp)
        if level >= self.skill_max_level:
            return 100
        base = level if xp >= 1 else 0
        return min(99, max(0, int((xp - base) / (level + 1 - base) * 100)))

    def level_progress_text(self, xp):
        level = self.level_of_xp(xp)
        if level >= self.skill_max_level:
            return "the highest level"
        return "%s xp / %s xp" % (self.xp_points(xp), self.xp_points(level + 1))

    @staticmethod
    def xp_points(xp):
        """Skill xp as shown to the player: a level is 100 xp (level 3 = 300 xp)."""
        return "{:,}".format(int(xp * 100 + 1e-6))

    def skill_info(self, i, long):
        xp = self.skill_xp[i]
        level = self.level_of_xp(xp)
        if long:
            if level >= self.skill_max_level:
                return "You have the highest %s level possible (%d)!" % (self.skill_name[i], self.skill_max_level)
            return "%s: %s xp / %s xp to level %d." % (self.skill_name[i], self.xp_points(xp), self.xp_points(level + 1),
                                                       level + 1)
        return "%s: level %d / %d|%s" % (self.skill_name[i], level, self.skill_max_level, self.level_progress_text(xp))

    def hitpoints_level(self):
        i = self.skill_index("Hitpoints")
        if i == 0:
            return 10
        return self.level_of_xp(self.skill_xp[i])

    def default_hitpoints_level(self):
        i = self.skill_index("Hitpoints")
        if i > 0 and self.skill_xp[i] < 1:
            self.skill_xp[i] = 10

    def update_max_hp(self):
        """Max hitpoints grow with Strength and Defence: Config [Gameplay] Hitpoints.Base + Hitpoints.Per.Level for
        each level of the two (19 + half of them: a new character has 20)."""
        levels = self.skill_level("Strength") + self.skill_level("Defence")
        self.player_max_hp = max(1, int(self.hp_base + levels * self.hp_per_level))
        self.player.max_hp = self.player_max_hp

    def max_hp_changed(self, old_max):
        """After Strength or Defence goes up: the new hitpoints are yours at once."""
        self.update_max_hp()
        gain = self.player_max_hp - old_max
        if gain > 0:
            self.player.hp = min(self.player_max_hp, self.player.hp + gain)
            self.display_message("You now have %d hitpoints." % self.player_max_hp, "LEVELUP")
        elif gain < 0:
            self.player.hp = min(self.player.hp, self.player_max_hp)

    def update_skill(self, skill, amount, pop=True):
        """amount = +Q, -Q or =Q. "Hitpoints" changes the player's current hitpoints. pop = False: no skill icon over
        the player's head (fighting, where it would get in the way)."""
        if trim(skill).upper() in ("HITPOINTS", "HITS", "HP"):
            old = self.player.hp
            new = int(min(self.player_max_hp, apply_change(old, amount)))
            if self.god_mode and new < old:
                new = old
            self.player.hp = max(0, new)
            if new > old:
                self.display_message("You gain %d hitpoint(s)." % (new - old), "ACHIEVEMENT")
                self.fx_splat("Heal", new - old, self.player)
            self.draw_skills()
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
            self.fx_skill_pop(self.skill_name[i])
        old = self.level_of_xp(self.skill_xp[i])
        amount = trim(str(amount))
        if amount[:1] == "+" and self.xp_slowdown > 0:          # each level harder than the last: at level L you
            gain = val(amount[1:]) * self.xp_slowdown / (self.xp_slowdown + old)    # learn 10/(10+L) as fast
            amount = "+" + lbstr(round(gain, 5))
        self.skill_xp[i] = min(self.skill_max_level, max(0, apply_change(self.skill_xp[i], amount)))
        new = self.level_of_xp(self.skill_xp[i])
        if new > old:
            self.display_message("LEVEL UP! Your %s level is now %d." % (self.skill_name[i], new), "LEVELUP")
            self.play_sound("LevelUp")
            self.level_up_show(self.skill_name[i], new)
        if new < old:
            self.display_message("Your %s level has dropped to %d." % (self.skill_name[i], new), "FAIL")
        if new != old and self.skill_name[i].upper() in ("STRENGTH", "DEFENCE"):
            self.max_hp_changed(self.player_max_hp)
        if new != old:
            self.draw_skills()
            self.check_locks(True)

    def update_player_health(self):
        """Hitpoints come back slowly out of combat; boosts wear off."""
        now = self.loop_start
        if self.spell_defence_until > 0 and (now >= self.spell_defence_until or now < self.spell_defence_until - 600000):
            self.spell_defence_bonus = 0
            self.spell_defence_until = 0
            self.display_message("Your extra Defence wears off.", "INFO")
        if self.spell_attack_until > 0 and (now >= self.spell_attack_until or now < self.spell_attack_until - 600000):
            self.spell_attack_bonus = 0
            self.spell_attack_until = 0
            self.display_message("Your extra Attack wears off.", "INFO")
        if self.spell_magic_until > 0 and (now >= self.spell_magic_until or now < self.spell_magic_until - 600000):
            self.spell_magic_bonus = 0
            self.spell_magic_until = 0
            self.display_message("Your extra Magic wears off.", "INFO")
        if self.spell_sight_until > 0 and (now >= self.spell_sight_until or now < self.spell_sight_until - 600000):
            self.spell_sight_bonus = 0
            self.spell_sight_until = 0
            self.fog_last_x = -99999
            self.display_message("Your eyesight is back to normal.", "INFO")
        if now < self.hp_regen_last:
            self.hp_regen_last = now
        hp = self.player.hp
        if hp <= 0 or hp >= self.player_max_hp:
            self.hp_regen_last = now
            return
        if now - self.player_last_combat < self.hp_regen_delay * 1000 and now >= self.player_last_combat:
            self.hp_regen_last = now
            return
        if now - self.hp_regen_last < self.hp_regen_every * 1000:
            return
        self.hp_regen_last = now
        self.player.hp = hp + 1
        self.draw_skills()

    def update_mana(self):
        """Mana comes back: all of it in a minute. The most is 10 + 3 per Magic level."""
        self.player_max_mana = 10 + 3 * self.skill_level("Magic")
        if self.player_mana < 0:
            self.player_mana = self.player_max_mana
        if self.player_mana < self.player_max_mana:
            self.player_mana = min(self.player_max_mana, self.player_mana + self.player_max_mana / 60 * self.loop_delta)
        if self.player_mana > self.player_max_mana:
            self.player_mana = self.player_max_mana
        if int(self.player_mana) != self.mana_shown:
            self.mana_shown = int(self.player_mana)
            if self.stats_view == 0 and self.main_setup_complete:
                self.draw_skills()

    # =================================================================================================================
    # Combat
    # =================================================================================================================
    @staticmethod
    def combat_hits(attack, defence, per=4):
        """60% when attack = defence, per% more or less per point, 10-95%."""
        chance = min(95, max(10, 60 + (attack - defence) * per))
        return rnd() * 100 < chance

    # ----- What your gear is worth in a fight. A weapon's Attack counts three times towards landing a blow and twice
    # towards its damage; Strength only a third and an eighth. Armour (the Defence of everything worn) counts one
    # and a half times against a monster landing a blow (your Defence level a quarter), and soaks a sixth of its
    # total off every blow that lands. So bare-handed and in your shirt you're in trouble, whatever your levels.
    def player_attack_value(self):
        return self.skill_level("Strength") / 3 + 3 * (self.equip_attack_total + self.spell_attack_bonus)

    def player_defence_value(self):
        return self.skill_level("Defence") / 4 + 1.5 * (self.equip_defence_total + self.spell_defence_bonus)

    def armour_soak(self):
        return max(0, int((self.equip_defence_total + self.spell_defence_bonus) / 6))

    def player_max_hit(self):
        return 1 + int(self.skill_level("Strength") / 8) + 2 * (max(0, self.equip_attack_total) + self.spell_attack_bonus)

    def npc_max_hit(self, e):
        """A monster's hardest blow: 1 + its Strength x Config [Gameplay] Monster.Damage (2)."""
        return 1 + max(0, int(e.strength * self.monster_damage))

    def start_attack(self, e):
        if e.type != NPC:
            self.display_message("You can't attack that!", "FAIL")
            return
        self.player_attack_target = e
        self.player_walk_stuck = 0

    def update_player_combat(self):
        t = self.player_attack_target
        if t is None:
            return
        if not t.alive:
            self.player_attack_target = None
            return
        p = self.player
        rng = 36 + self.reach_extra(t)
        bow = self.player_bow_range()
        if bow > 0:
            if self.in_line_of_sight(p.cx, p.cy, t.cx, t.cy):
                rng = max(rng, bow)
            else:
                bow = 0
        if self.player_distance_to(t) > rng:
            if not self.player_walk_active:
                if self.player_walk_stuck > 15:
                    self.display_message("You can't reach the %s!" % self.display_name(t), "FAIL")
                    self.player_attack_target = None
                    self.player_walk_stuck = 0
                    return
                self.walk_player_to(t.cx, t.cy, 0, rng - 4)
            return
        if self.player_walk_active and self.pending_ent is None:
            self.player_walk_active = False
        now = self.clock()
        if now - self.player_last_attack < p.attack_speed * 1000 * self.attack_slowdown():
            return
        self.player_last_attack = now
        self.player_last_combat = now
        t.in_combat = True
        t.last_combat = now
        self.npc_face(p, p.cx, p.cy, t.cx, t.cy)
        if bow > 0 and self.player_distance_to(t) > 36 + self.reach_extra(t):
            self.remove_inventory_item(self.entity_ini(self.equipped[1], "Ammo", ""), 1)
            self.play_sound("Miss")
            self.fx_shot(p, "Arrow_Missile", t, "ARROW")
            return
        self.fx_nudge(p, -self.fx_away(t, p), -self.fx_away_y(t, p), 110)
        self.player_strike(t, False)

    def player_strike(self, t, ranged):
        if not t.alive:
            return
        what = "Your arrow" if ranged else "You"
        if not self.combat_hits(self.player_attack_value(), 3 * t.defence, 3):
            self.play_sound("Miss", (t.cx, t.cy))
            self.fx_splat("Miss", 0, t)
            if ranged:
                self.display_message("Your arrow misses the %s." % self.display_name(t), "COMBAT")
            else:
                self.display_message("You miss the %s." % self.display_name(t), "COMBAT")
            return
        max_hit = self.player_max_hit()
        damage = random_number(1, max_hit)
        if rnd() * 100 < 5 + self.skill_level("Strength") / 15:
            damage = max_hit + random_number(0, int(max_hit / 2))
            self.play_sound("Crit", (t.cx, t.cy))
            self.fx_splat("Crit", damage, t)
            self.display_message("A critical hit! %s hit the %s for %d damage!" % (what, self.display_name(t), damage),
                                 "COMBAT")
        else:
            self.play_sound("Fight%d" % random_number(1, 3), (t.cx, t.cy))
            self.fx_splat("Hit", damage, t)
            if ranged:
                self.display_message("Your arrow hits the %s for %d damage!" % (self.display_name(t), damage), "COMBAT")
            else:
                self.display_message("You hit the %s for %d damage!" % (self.display_name(t), damage), "COMBAT")
        self.wear_weapon()                              # (a blow landed: the weapon wears a little)
        self.fx_anim("Slash", t.cx, t.cy, 240)
        self.fx_nudge(t, self.fx_away(self.player, t), self.fx_away_y(self.player, t), 130)
        self.update_skill("Strength", "+" + lbstr(damage * 0.01), pop=False)
        self.damage_npc(t, damage)

    @staticmethod
    def reach_extra(e):
        """Big sprites (the dragon is 64 x 64) are reached from further away: half of what's over 32 pixels."""
        return max(0, int((e.w - 32) / 2))

    def player_bow_range(self):
        weapon = self.equipped[1]
        if not weapon:
            return 0
        rng = val(self.entity_ini(weapon, "Range", "0"))
        if rng <= 0:
            return 0
        ammo = self.entity_ini(weapon, "Ammo", "")
        if ammo and self.items_held(ammo) <= 0:
            now = self.clock()
            if now - self.ammo_warned > 8000 or now < self.ammo_warned:
                self.ammo_warned = now
                self.display_message("You have no %s left: you can only club them with the bow." % pretty(ammo), "FAIL")
            return 0
        return rng

    def damage_npc(self, e, damage):
        hp = e.hp - damage
        e.hp = max(0, hp)
        if hp <= 0:
            self.kill_npc(e)

    def kill_npc(self, e):
        name, etype = e.name, e.type
        self.display_message("You have killed the %s!" % self.display_name(e), "ACHIEVEMENT")
        self.play_sound("Kill_" + (self.entity_ini(name, "Kill.Sound", "") or "Beast"), (e.cx, e.cy))
        self.add_npc_drops(e)
        if e.source == "MAP":
            respawn = e.respawn_delay if e.respawn_delay > 0 else self.npc_respawn_delay
            options = "-"
            if e.ai is not None and e.ai.options:
                options = e.ai.options
            home = self.entity_home(e)
            self.add_action_to_queue("ADD", name, TYPE_NAMES[etype], options, home,
                                     self.local_coords(home, e.orig_x, e.orig_y), respawn)
        script = self.find_action_script("Kill", name, etype, getattr(e, "npc_id", ""))
        self.fx_anim("Puff", e.cx, e.cy, 500)
        self.remove_entity(e)
        if script:
            self.start_script(script, False)

    def add_npc_drops(self, e):
        """Drops=Item,min-max,percent Item,min-max,percent ..."""
        drops = self.entity_ini(e.name, "Drops", "")
        drop_x, drop_y = e.cx, e.fy
        i = 1
        while word(drops, i) != "":
            d = word(drops, i)
            name = word(d, 1, ",")
            amount_s = word(d, 2, ",") or "1"
            percent = word(d, 3, ",") or "100"
            if rnd() * 100 < val(percent):
                amount = parse_quantity(amount_s)
                if "-" not in amount_s:
                    amount = val(amount_s)
                if amount > 0:
                    if self.stackable_quantity(name) > 1:
                        copies, each = 1, amount
                    else:
                        copies, each = min(amount, 10), 1
                    w, h = self.sprite_size_of(3, name)
                    for _ in range(int(copies)):
                        x = int(drop_x - w / 2 + random_number(-8, 8))
                        y = int(drop_y - h + random_number(-4, 6))
                        item = self.add_map_item(name, x, y, each)
                        if item is not None:
                            item.source = "DROPPED"
                            home = self.entity_home(item)
                            self.add_action_to_queue("REMOVE", name, "MapItem", lbstr(each), home,
                                                     self.local_coords(home, x, y), self.item_despawn_delay)
            i += 1

    def npc_shoot(self, e, missile):
        self.player_last_combat = self.clock()
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = e
        self.play_sound(self.entity_ini(e.name, "Missile.Sound", "Miss"), (e.cx, e.cy))
        self.fx_shot(e, missile, self.player, e)

    def npc_shot_hits(self, e):
        if e is None or not e.alive:
            return
        impact = self.entity_ini(e.name, "Missile.Impact", "")
        if impact:
            self.fx_anim(impact, self.player.cx, self.player.cy, 400)
        self.npc_ranged_hit = True
        self.npc_attack_player(e)
        self.npc_ranged_hit = False

    def npc_attack_player(self, e):
        now = self.clock()
        p = self.player
        self.player_last_combat = now
        if not self.npc_ranged_hit:
            self.fx_nudge(e, -self.fx_away(p, e), -self.fx_away_y(p, e), 110)
        if self.player_attack_target is None and not self.player_walk_active and self.pending_ent is None:
            self.player_attack_target = e
        if self.god_mode:
            self.fx_splat("Miss", 0, p)
            self.display_message("Your god-like skin shrugs off the %s's blow." % self.display_name(e), "COMBAT")
            return
        if not self.combat_hits(e.strength * 3 + 2, self.player_defence_value(), 3):
            self.fx_splat("Miss", 0, p)
            if self.equip_defence_total + self.spell_defence_bonus > 0:
                self.play_sound("Block")
                self.display_message("Your armour turns the %s's blow." % self.display_name(e), "COMBAT")
            else:
                self.display_message("The %s misses you." % self.display_name(e), "COMBAT")
            self.update_skill("Defence", "+0.03", pop=False)
            return
        self.wear_armour()                              # (a blow landed: what you're wearing takes it)
        damage = self.resist_damage(e, random_number(1, self.npc_max_hit(e))) - self.armour_soak()
        if damage <= 0:                                 # the armour took all of it
            self.fx_splat("Miss", 0, p)
            self.play_sound("Block")
            self.display_message("Your armour takes the %s's blow." % self.display_name(e), "COMBAT")
            self.update_skill("Defence", "+0.03", pop=False)
            return
        self.play_sound("Hurt")
        self.fx_splat("Hit", damage, p)
        self.fx_nudge(p, self.fx_away(e, p), self.fx_away_y(e, p), 130)
        self.fx_hurt_flash()
        self.display_message("The %s hits you for %d damage!" % (self.display_name(e), damage), "DAMAGE")
        self.update_skill("Defence", "+" + lbstr(damage * 0.01), pop=False)
        self.update_skill("Hitpoints", "-%d" % damage)
        if p.hp > 0:
            self.status_on_hit(e)                       # its poison, fire, frost... (Entities.ini On.Hit)
        hp = p.hp
        if 0 < hp <= self.player_max_hp / 4 and (now - self.low_hp_warned > 10000 or now < self.low_hp_warned):
            self.low_hp_warned = now
            self.display_message("You are badly hurt! Eat something, drink a potion or run!", "ERROR")

    def player_dies(self):
        if self.god_mode:
            self.player.hp = self.player_max_hp
            return
        self.display_message("Oh dear, you are dead!", "ERROR")
        self.play_sound("Death")
        gold = self.items_held("Gold_Coin(s)")
        lost = int(gold * self.death_gold_loss / 100)
        if lost > 0:                                    # (Config [Gameplay] Death.Gold.Loss: a share of your gold)
            self.remove_inventory_item("Gold_Coin(s)", lost)
            self.display_message("You lost %d gold coins." % lost, "DAMAGE")
        self.fx_anim("Puff", self.player.cx, self.player.cy, 500)
        self.clear_boosts()
        self.status_reset()
        self.grave_leave()                              # (what you carried stays where you fell)
        self.player.hp = self.player_max_hp
        self.player_attack_target = None
        self.stop_player_walk()
        for e in self.world:
            if e.type == NPC:
                e.in_combat = False
        if self.map_exists(self.start_map):
            self.pending_map = self.start_map
            self.pending_x, self.pending_y = self.start_x, self.start_y
            self.pending_map_change = True
        self.draw_skills()

    # =================================================================================================================
    # Health bars
    # =================================================================================================================
    def update_healthbar(self, e):
        """Shows a health bar above hurt or fighting NPCs (and the player)."""
        if not self.healthbars_available:
            e.show_bar = False
            return
        show = e.hp < e.max_hp
        if e is self.player:
            if self.clock() - self.player_last_combat < 5000:
                show = True
        else:
            if e.in_combat:
                show = True
            if not e.active:
                show = False
        e.show_bar = show

    @staticmethod
    def healthbar_image(hp, maximum):
        if maximum <= 0:
            maximum = 1
        percent = int((max(0, hp) * 10 + maximum - 1) / maximum) * 10
        return "%dPCHealth" % min(100, max(0, percent))

    # =================================================================================================================
    # Combat feedback (Sprites\Effects, loaded the first time each is needed). Up to 40 at once
    # =================================================================================================================
    def fx_load(self, name):
        if self.assets.loaded(name):
            return True
        if not self.assets.load_if_exists("Effects", name):
            self.log_missing("Effect", name)
            return False
        return True

    def fx_room(self):
        return len(self.fx) < 40

    def fx_remove(self, f):
        if f in self.fx:
            self.fx.remove(f)
        if f.kind == 4 and f.ent is not None:
            f.ent.nudge_x = f.ent.nudge_y = 0

    def fx_clear(self):
        for f in list(self.fx):
            self.fx_remove(f)

    @staticmethod
    def fx_away(src, e):
        dx = e.cx - src.cx
        if dx > 4:
            return 3
        if dx < -4:
            return -3
        return 0

    @staticmethod
    def fx_away_y(src, e):
        dy = e.cy - src.cy
        if dy > 4:
            return 2
        if dy < -4:
            return -2
        return 0

    def fx_splat(self, kind, amount, e):
        if e is None or not e.alive:
            return
        name = "Miss" if kind == "Miss" else "%s%d" % (kind, min(99, max(1, int(amount))))
        if not self.fx_load(name) or not self.fx_room():
            return
        x = int(e.cx - self.assets.width(name) / 2) + random_number(-5, 5)
        y = int(e.y + e.h * 0.25) + random_number(-3, 3)
        self.fx.append(Fx(1, name, x, y, self.loop_start, self.loop_start + 900))

    def fx_skill_pop(self, skill):
        """Using a skill: its icon in a small box over the player's head for a moment."""
        name = "SkillPop_" + skill
        if not self.assets.loaded(name):
            icon = self.config_skill_icon(skill)
            if not self.assets.loaded(icon):
                return
            surf = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.rect(surf, (214, 170, 70), (0, 0, 28, 28), border_radius=5)
            pygame.draw.rect(surf, (51, 34, 27), (2, 2, 24, 24), border_radius=4)
            self.draw_icon(surf, icon, 4, 4, 20)
            self.assets.register(name, surf)
        now = self.loop_start
        for f in list(self.fx):
            if f.kind == 6:
                if f.image == name:
                    f.end = now + 1600
                    return
                self.fx_remove(f)
        if not self.fx_room():
            return
        f = Fx(6, name, int(self.player.cx - 14), int(self.player.y - 30), now, now + 1600)
        self.fx.append(f)

    def fx_anim(self, base, x, y, ms):
        for n in range(1, 5):
            if not self.fx_load(base + str(n)):
                return
        if not self.fx_room():
            return
        first = base + "1"
        f = Fx(2, first, int(x - self.assets.width(first) / 2), int(y - self.assets.height(first) / 2),
               self.loop_start, self.loop_start + max(100, ms))
        f.base = base
        self.fx.append(f)

    def fx_shot(self, src, image, target, tag):
        """A missile flies from src to target; fx_arrive(tag) when it gets there."""
        if not (self.fx_load(image) and self.fx_room()):
            self.fx_arrive(tag, target)
            return
        w, h = self.assets.width(image), self.assets.height(image)
        f = Fx(3, image, src.cx - int(w / 2), src.cy - int(h / 2), self.loop_start, self.loop_start + 3000)
        f.mirror = target.cx < src.cx
        f.target = target
        f.tag = tag
        f.layer = MISSILE
        self.fx.append(f)

    def fx_arrive(self, tag, target):
        if tag == "ARROW":
            self.player_strike(target, True)
        elif not isinstance(tag, str):
            self.npc_shot_hits(tag)
        else:
            self.spell_hit(tag, target)

    def fx_nudge(self, e, dx, dy, ms):
        if e is None or (dx == 0 and dy == 0) or not e.active:
            return
        for f in self.fx:
            if f.kind == 4 and f.ent is e:
                return
        if not self.fx_room():
            return
        f = Fx(4, "", 0, 0, self.loop_start, self.loop_start + ms)
        f.ent = e
        e.nudge_x, e.nudge_y = dx, dy
        self.fx.append(f)

    def fx_hurt_flash(self):
        now = self.loop_start
        flashing = False
        for f in self.fx:
            if f.kind == 5:
                f.end = now + 240
                flashing = True
        if flashing:
            return
        for e, name in enumerate(("Hurt_Top", "Hurt_Bottom", "Hurt_Left", "Hurt_Right"), 1):
            if self.fx_load(name) and self.fx_room():
                x = y = 0
                if e == 2:
                    y = self.view_h - self.assets.height(name)
                if e == 4:
                    x = self.view_w - self.assets.width(name)
                self.fx.append(Fx(5, name, x, y, now, now + 240))

    def fx_update(self):
        """Every loop: moves, animates and ends the effects."""
        now = self.loop_start
        for f in list(self.fx):
            if f not in self.fx:
                continue
            done = now >= f.end or now < f.start
            if f.kind == 1:
                if not done:
                    t = (now - f.start) / max(1, f.end - f.start)
                    f.draw_y = f.y - int(14 * min(1, t * 1.6))
            elif f.kind == 2:
                if not done:
                    frame = min(4, 1 + int(4 * (now - f.start) / max(1, f.end - f.start)))
                    f.image = f.base + str(frame)
            elif f.kind == 3:
                t = f.target
                if t is None or not t.alive:
                    done = True
                elif not done:
                    w, h = self.assets.width(f.image), self.assets.height(f.image)
                    tx = t.cx - w / 2
                    ty = t.cy - h / 2
                    d = distance(f.x, f.y, tx, ty)
                    travel = 420 * self.loop_delta
                    if d <= travel + 4:
                        self.fx_remove(f)
                        self.fx_arrive(f.tag, t)
                        continue
                    f.x += (tx - f.x) * travel / d
                    f.y += (ty - f.y) * travel / d
            elif f.kind == 6:
                if not done:
                    rise = min(6, int((now - f.start) / 40))
                    f.x = int(self.player.cx - self.assets.width(f.image) / 2)
                    f.y = int(self.player.y - self.assets.height(f.image) - rise)
            if done and f in self.fx:
                self.fx_remove(f)

    # =================================================================================================================
    # Spells (Data\Spells.ini): reading a scroll casts its spell and uses it up
    # =================================================================================================================
    def spell_ini(self, spell, key, default):
        return ini.read(spell, key, default, os.path.join(self.root, "Data", "Spells.ini"))

    @staticmethod
    def spell_roll(range_text):
        a = val(word(range_text, 1, "-"))
        b = val(word(range_text, 2, "-"))
        if b < a:
            b = a
        return random_number(int(a), int(b))

    @staticmethod
    def spell_target_ok(e):
        return e is not None and e.alive and e.type == NPC and e.active

    def spell_auto_target(self, rng):
        p = self.player
        if self.spell_target_ok(self.player_attack_target):
            if self.player_distance_to(self.player_attack_target) <= rng:
                return self.player_attack_target
        best = rng + 1
        found = None
        for e in self.world:
            if e.type == NPC and e.hostile and self.spell_target_ok(e):
                d = distance(p.cx, p.cy, e.cx, e.cy)
                if d < best and self.in_line_of_sight(p.cx, p.cy, e.cx, e.cy):
                    best = d
                    found = e
        return found

    def spell_is_potion(self, spell):
        return self.spell_ini(spell, "Kind", "Scroll").upper() == "POTION"

    def spell_chance(self, spell):
        level = val(self.spell_ini(spell, "Level", "1"))
        return min(98, max(20, 60 + (self.skill_level(self.spell_ini(spell, "Skill", "Magic")) - level) * 7))

    def spell_cost(self, spell):
        return val(self.spell_ini(spell, "Cost", "0"))

    def spell_cooldown_left(self, spell):
        now = self.clock()
        until = self.cooldowns.get(spell)
        if until is not None and until > now and until - now < 3600000:
            return int((until - now) / 1000) + 1
        return 0

    def spell_start_cooldown(self, spell):
        seconds = val(self.spell_ini(spell, "Cooldown", "0"))
        if seconds <= 0:
            return
        if spell in self.cooldowns or len(self.cooldowns) < 30:
            self.cooldowns[spell] = self.clock() + seconds * 1000

    def spell_status(self, spell):
        level = val(self.spell_ini(spell, "Level", "1"))
        skill = self.spell_ini(spell, "Skill", "Magic")
        if self.skill_level(skill) < level:
            return "Needs %s %s (you have %d)" % (skill, lbstr(level), self.skill_level(skill))
        status = "%s mana, %d%% to work" % (lbstr(self.spell_cost(spell)), self.spell_chance(spell))
        wait = self.spell_cooldown_left(spell)
        status += ("|Ready in %d s" % wait) if wait > 0 else "|Ready"
        if self.player_mana < self.spell_cost(spell):
            status += " (not enough mana)"
        return status

    def clear_boosts(self):
        self.spell_defence_bonus = self.spell_defence_until = 0
        self.spell_attack_bonus = self.spell_attack_until = 0
        self.spell_magic_bonus = self.spell_magic_until = 0
        self.spell_sight_bonus = self.spell_sight_until = 0
        self.fog_last_x = -99999

    def spell_begin(self, scroll, spell):
        """The scroll is read (or the potion drunk): used up, its skill trained. A scroll may fizzle."""
        self.spell_fizzled = False
        attack = self.spell_ini(spell, "Effect", "Bolt").upper() in ("BOLT", "AREA")  # No skill icon mid-fight
        if not self.spell_is_potion(spell):
            self.player_mana = max(0, self.player_mana - self.spell_cost(spell))
            self.mana_shown = -1
            self.spell_start_cooldown(spell)
            chance = self.spell_chance(spell)
            if rnd() * 100 >= chance:
                self.remove_inventory_item(scroll, 1)
                self.player_last_cast = self.clock()
                self.play_sound("Miss")
                self.fx_anim("Puff", self.player.cx, self.player.cy, 400)
                self.display_message("The spell fizzles and the scroll crumbles to dust! (%d%% chance: it works more "
                                     "surely as your Magic grows.)" % chance, "FAIL")
                xp = val(self.spell_ini(spell, "XP", "0")) / 2
                if xp > 0:
                    self.update_skill(self.spell_ini(spell, "Skill", "Magic"), "+" + lbstr(xp), pop=not attack)
                self.spell_fizzled = True
                return
        self.remove_inventory_item(scroll, 1)
        mana_back = val(self.spell_ini(spell, "Mana", "0"))
        if mana_back > 0:
            self.player_mana = min(self.player_max_mana, self.player_mana + mana_back)
            self.mana_shown = -1
        leaves = self.spell_ini(spell, "Leaves", "")
        if leaves:
            self.add_inventory_item(leaves, 1)
        if self.spell_is_potion(spell):
            self.display_message("You drink the %s." % pretty(scroll), "SUCCESS")
        else:
            self.player_last_cast = self.clock()
            self.play_sound("SpellCast")
            self.display_message("You read the scroll of %s..." % pretty(spell), "COMBAT")
        xp = val(self.spell_ini(spell, "XP", "0"))
        if xp > 0:
            self.update_skill(self.spell_ini(spell, "Skill", "Magic"), "+" + lbstr(xp), pop=not attack)

    def cast_scroll(self, item, target):
        """Casts the spell on scroll item (an inventory item) at target (None = choose one)."""
        scroll = item.name
        spell = self.entity_ini(scroll, "Spell", "")
        if spell == "":
            self.display_message("Nothing interesting happens.", "FAIL")
            return
        name = pretty(spell)
        level = val(self.spell_ini(spell, "Level", "1"))
        skill = self.spell_ini(spell, "Skill", "Magic")
        potion = self.spell_is_potion(spell)
        if not potion and self.skill_level(skill) < level:
            self.display_message("You need level %s %s to cast %s (you have %d)." %
                                 (lbstr(level), skill, name, self.skill_level(skill)), "FAIL")
            return
        if not potion:
            wait = self.spell_cooldown_left(spell)
            if wait > 0:
                self.display_message("%s isn't ready yet: %d more second(s)." % (name, wait), "FAIL")
                return
            cost = self.spell_cost(spell)
            if self.player_mana < cost:
                self.display_message("%s needs %s mana and you have %d. It comes back over time." %
                                     (name, lbstr(cost), int(self.player_mana)), "FAIL")
                return
        now = self.clock()
        if not potion and now - self.player_last_cast < 1500 and now >= self.player_last_cast:
            self.display_message("You're still gathering your wits after the last spell.", "FAIL")
            return
        p = self.player
        pcx, pcy = p.cx, p.cy
        effect = self.spell_ini(spell, "Effect", "Bolt").upper()
        if effect == "BOLT":
            rng = val(self.spell_ini(spell, "Range", "256"))
            if target is None:
                target = self.spell_auto_target(rng)
            if not self.spell_target_ok(target):
                self.display_message("There's nothing to cast %s at. Use the scroll on a monster, or get closer." % name,
                                     "FAIL")
                return
            if self.player_distance_to(target) > rng + 8:
                self.display_message("The %s is too far away." % self.display_name(target), "FAIL")
                return
            if not self.in_line_of_sight(pcx, pcy, target.cx, target.cy):
                self.display_message("You can't see the %s from here." % self.display_name(target), "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.npc_face(p, pcx, pcy, target.cx, target.cy)
            target.in_combat = True
            target.last_combat = now
            self.player_last_combat = now
            missile = self.spell_ini(spell, "Missile", "")
            if missile == "":
                self.spell_hit(spell, target)
            else:
                self.fx_shot(p, missile, target, spell)
        elif effect == "AREA":
            radius = val(self.spell_ini(spell, "Radius", "128"))
            targets = [e for e in self.world if e.type == NPC and e.hostile and self.spell_target_ok(e) and
                       distance(pcx, pcy, e.cx, e.cy) <= radius and self.in_line_of_sight(pcx, pcy, e.cx, e.cy)]
            if not targets:
                self.display_message("There are no enemies close enough for %s." % name, "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.player_last_combat = now
            for e in targets:
                if e.alive:
                    e.in_combat = True
                    e.last_combat = now
                    self.spell_hit(spell, e)
        elif effect == "HEAL":
            if p.hp >= self.player_max_hp:
                self.display_message("You already have full health!", "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            bonus = 0
            if not potion:
                bonus = int(self.skill_level("Magic") / 3) + self.equip_magic_total
            self.update_skill("Hitpoints", "+%d" % (self.spell_roll(self.spell_ini(spell, "Heal", "5-10")) + bonus))
        elif effect in ("SHIELD", "BOOST"):
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            seconds = max(1, val(self.spell_ini(spell, "Duration", "60")))
            gains = ""
            if val(self.spell_ini(spell, "Attack", "0")) > 0:
                self.spell_attack_bonus = val(self.spell_ini(spell, "Attack", "0"))
                self.spell_attack_until = now + seconds * 1000
                gains += ", +%s Attack" % lbstr(self.spell_attack_bonus)
            if val(self.spell_ini(spell, "Defence", "0")) > 0:
                self.spell_defence_bonus = val(self.spell_ini(spell, "Defence", "0"))
                self.spell_defence_until = now + seconds * 1000
                gains += ", +%s Defence" % lbstr(self.spell_defence_bonus)
            if val(self.spell_ini(spell, "Magic", "0")) > 0:
                self.spell_magic_bonus = val(self.spell_ini(spell, "Magic", "0"))
                self.spell_magic_until = now + seconds * 1000
                gains += ", +%s Magic" % lbstr(self.spell_magic_bonus)
            if val(self.spell_ini(spell, "Sight", "0")) > 0:
                self.spell_sight_bonus = val(self.spell_ini(spell, "Sight", "0"))
                self.spell_sight_until = now + seconds * 1000
                self.fog_last_x = -99999
                if gains == "":
                    self.display_message("Your eyes sharpen: you can see much further for %s seconds." %
                                         lbstr(seconds), "ACHIEVEMENT")
                    return
                gains += ", sharper eyes"
            self.display_message("You feel stronger%s for %s seconds." % (gains, lbstr(seconds)), "ACHIEVEMENT")
        elif effect == "TELEPORT":
            m = self.spell_ini(spell, "Map", "").replace(" ", "")
            x = val(self.spell_ini(spell, "X", "0"))
            y = val(self.spell_ini(spell, "Y", "0"))
            if m == "":
                m, x, y = self.start_map, self.start_x, self.start_y
            if not self.map_exists(m):
                self.display_message("The spell fizzles: it has nowhere to take you.", "FAIL")
                return
            self.spell_begin(scroll, spell)
            if self.spell_fizzled:
                return
            self.spell_glow(spell)
            self.display_message("The world spins around you...", "SUCCESS")
            self.player_attack_target = None
            self.pending_map, self.pending_x, self.pending_y = m, x, y
            self.pending_map_change = True
        else:
            self.display_message("Nothing interesting happens.", "FAIL")

    def spell_glow(self, spell):
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, self.player.cx, self.player.cy, 600)
        self.play_sound(self.spell_ini(spell, "Sound", ""))

    def spell_hit(self, spell, e):
        if not self.spell_target_ok(e):
            return
        damage = (self.spell_roll(self.spell_ini(spell, "Damage", "1-3")) + int(self.skill_level("Magic") / 4) +
                  self.equip_magic_total + self.spell_magic_bonus)
        impact = self.spell_ini(spell, "Impact", "")
        if impact:
            self.fx_anim(impact, e.cx, e.cy, 450)
        self.play_sound(self.spell_ini(spell, "Sound", ""), (e.cx, e.cy))
        self.fx_splat("Hit", damage, e)
        self.fx_nudge(e, self.fx_away(self.player, e), self.fx_away_y(self.player, e), 130)
        self.display_message("Your %s hits the %s for %s damage!" % (pretty(spell), self.display_name(e),
                                                                     lbstr(damage)), "COMBAT")
        now = self.clock()
        e.in_combat = True
        e.last_combat = now
        slow = self.spell_ini(spell, "Slow", "")
        if slow and damage < e.hp:
            if e.slow_until is None:
                e.normal_speed = e.move_speed
            e.move_speed = e.normal_speed * max(5, val(word(slow, 1, ","))) / 100
            e.slow_until = now + max(1, val(word(slow, 2, ","))) * 1000
            self.display_message("The %s slows down." % self.display_name(e), "COMBAT")
        self.damage_npc(e, damage)

    # =================================================================================================================
    # Worn gear: Sprites\Worn\Worn_<Item><Dir><Frame>.png drawn over the player
    # =================================================================================================================
    def gear_has_art(self, item):
        if not item:
            return False
        k = self.gear_kinds.get(item)
        if k is not None:
            return k
        ok = True
        for d in "1248":
            for f in "abc":
                if not self.assets.load_if_exists("Worn", "Worn_" + item + d + f):
                    ok = False
        self.gear_kinds[item] = ok
        return ok

    def worn_items(self):
        """What is drawn over the player, lowest first (legs, feet, body, hands, head, shield, weapon)."""
        if self.player_sprite_base != "Player":
            return []
        items = []
        for s in range(1, self.equip_slots + 1):
            it = self.equipped[s]
            if it and self.gear_has_art(it):
                items.append((self.gear_rank[s], it))
        items.sort()
        return [it for _, it in items]
