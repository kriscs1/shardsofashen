"""Shard Remnants: what a monster's magic leaves when it dies (Shards.ini [Remnants]). Killing a monster gives no
Shards of itself: it may leave Shard Remnants on the ground (an item: pick them up, then Absorb them for Shards), or,
less often, its magic rises as a Shard Remnant (a monster of its own, as strong as the one that died: Entities.ini
Level=) and goes for whoever killed it. Killed, a Shard Remnant leaves more remnants, and never rises again.

Only monsters with a Level= leave them (the hostile ones: dev/migrate/build_shards.py gives them theirs)."""
from dragonsword.lb import val, trim, rnd, parse_quantity

REMNANT = "Shard_Remnant"           # (the item on the ground)
LIVING = "Living_Remnant"           # (the monster: "Shard Remnant" over its head)


class RemnantMixin:
    def remnant_setting(self, key, default):
        return trim(self.data.shards_ini("Remnants", key, "")) or str(default)

    def remnant_num(self, key, default):
        return val(self.remnant_setting(key, default))

    def monster_level(self, e):
        """Its Entities.ini Level= (a Shard Remnant: the level it rose at)."""
        lv = getattr(e, "remnant_level", 0)
        return int(lv) if lv else int(val(self.entity_ini(e.name, "Level", "0")))

    def remnants_on_death(self, e, drop):
        """A monster died: remnants on the ground (drop(name, count) puts them there, the killer's first), or a Shard
        Remnant rising, or nothing."""
        level = self.monster_level(e)
        if level <= 0:
            return
        if e.name == LIVING:
            n = parse_quantity(self.remnant_setting("Mob.Count", "3-6")) + \
                int(level * self.remnant_num("Count.Per.Level", 0.25))
            drop(REMNANT, max(1, n))
            return
        if level >= self.remnant_num("Mob.Min.Level", 2) and rnd() * 100 < self.remnant_num("Mob.Chance", 6):
            self.remnant_rise(e, level)
            return
        if rnd() * 100 < self.remnant_num("Chance", 45):
            n = parse_quantity(self.remnant_setting("Count", "1-2")) + int(level * self.remnant_num("Count.Per.Level", 0.25))
            drop(REMNANT, max(1, n))

    def remnant_rise(self, dead, level):
        """The dead monster's magic rises as a Shard Remnant, as strong as it was, and goes for its killer."""
        w = self.w
        e = w.add_npc(LIVING, dead.z, dead.x, dead.y, "-", "Bad")
        if e is None:
            return
        e.remnant_level = level
        e.display = "Shard Remnant"
        num = self.remnant_num
        e.hp = e.max_hp = max(1, int(num("Mob.Hitpoints", 5) + level * num("Mob.Hitpoints.Per.Level", 5)))
        e.strength = max(1, round(num("Mob.Strength", 1) + level * num("Mob.Strength.Per.Level", 0.5)))
        e.defence = max(1, round(num("Mob.Defence", 1) + level * num("Mob.Defence.Per.Level", 0.5)))
        e.fades_at = w.now + int(num("Mob.Lasts", 120) * 1000)
        w.sound("Remnant_Rise", e.z, e.cx, e.cy)
        self.fx_anim("Teleport_Glow", e.cx, e.cy, 600)
        self.display_message("The %s's magic rises from it: a Shard Remnant!" % self.display_name(dead), "DAMAGE", "-")
        if e.ai is not None:
            w.npc_start_fight(e, e.ai, self, 0)

    # ----- absorbing them, from the pack
    def absorb_remnants(self, item):
        """All the remnants in the pack, into Shards (Shards.ini [Remnants] Absorb each), and a little Magic."""
        n = self.items_held(item.name)
        if n <= 0:
            return
        each = self.remnant_num("Absorb", 1)
        shards = int(n * each)
        self.remove_inventory_item(item.name, n)
        self.play_sound("Absorb")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 500)
        self.give_shards(shards, "You absorb %d Shard Remnant%s" % (n, "" if n == 1 else "s"))
        xp = self.remnant_num("Absorb.Magic.XP", 0.05) * n
        if xp > 0:
            self.update_skill("Magic", "+%s" % round(xp, 3), pop=False)


def fade_remnants(w):
    """Shard Remnants nobody is fighting fade away once their time is up (the world's tick)."""
    for e in [e for e in w.ents if e.alive and e.name == LIVING]:
        if w.now >= getattr(e, "fades_at", 0) and not e.in_combat:
            w.fx_anim("Puff", e.z, e.cx, e.cy, 500)
            w.remove_entity(e)
