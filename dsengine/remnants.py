"""What a monster's magic leaves when it dies (Shards.ini [Remnants]). Killing a monster gives no Shards of itself:
it may leave Shards on the ground where it fell (picked up, they fly to your Shard bar and are counted there, never
in the bag), or, less often, its magic rises as a Shard Remnant (a monster of its own, as strong as the one that
died: Entities.ini Level=) and goes for whoever killed it. Killed, a Shard Remnant leaves more Shards, and never
rises again. (Shard Remnants were an item once, to Absorb from the pack: renames.py makes an old save's Shards.)

Only monsters with a Level= leave them (the hostile ones: dev/migrate/build_shards.py gives them theirs)."""
from ashen.lb import val, trim, rnd, parse_quantity
from .shards import SHARD

REMNANT = SHARD                     # (what's left on the ground: Shards, picked up straight onto the balance)
LIVING = "Living_Remnant"           # (the monster: "Shard Remnant" over its head)
RISE_MS = 1100                      # (risen, it's unseen this long: its Shards fly off for the bar, and turn back to it)


def make_remnant(data, e, level):
    """A Shard Remnant as strong as level: Shards.ini [Remnants] Mob.Hitpoints... (risen, or a map's: Level=)."""
    num = lambda k, d: val(trim(data.shards_ini("Remnants", k, "")) or str(d))
    e.remnant_level = level
    e.display = "Shard Remnant"
    e.hp = e.max_hp = max(1, int(num("Mob.Hitpoints", 5) + level * num("Mob.Hitpoints.Per.Level", 5)))
    e.strength = max(1, round(num("Mob.Strength", 1) + level * num("Mob.Strength.Per.Level", 0.5)))
    e.defence = max(1, round(num("Mob.Defence", 1) + level * num("Mob.Defence.Per.Level", 0.5)))


def monster_level(data, e):
    """Its level: as it was placed (world.py set_npc_level), else its kind's Entities.ini Level= (a Shard Remnant: the
    level it rose at). A creature that isn't a monster's leaves no remnants, whatever its level."""
    lv = getattr(e, "remnant_level", 0)
    if lv:
        return int(lv)
    kind = int(val(data.entity_ini(e.name, "Level", "0")))
    if kind <= 0 or trim(data.entity_ini(e.name, "Attitude", "")) == "Good":
        return 0
    return int(getattr(e, "npc_level", 0) or kind)


def death_remnants(data, e, drop, rise):
    """A monster died (to a player or to another NPC): remnants on the ground (drop(name, count) puts them there), or
    its magic rising (rise(level)), or nothing."""
    setting = lambda k, d: trim(data.shards_ini("Remnants", k, "")) or str(d)
    num = lambda k, d: val(setting(k, d))
    level = monster_level(data, e)
    if level <= 0:
        return
    if e.name == LIVING:
        drop(REMNANT, max(1, parse_quantity(setting("Mob.Count", "3-6")) + int(level * num("Count.Per.Level", 0.25))))
        return
    if level >= num("Mob.Min.Level", 2) and rnd() * 100 < num("Mob.Chance", 15):
        rise(level)
        return
    if rnd() * 100 < num("Chance", 53):
        drop(REMNANT, max(1, parse_quantity(setting("Count", "1-2")) + int(level * num("Count.Per.Level", 0.25))))


class RemnantMixin:
    def remnant_setting(self, key, default):
        return trim(self.data.shards_ini("Remnants", key, "")) or str(default)

    def remnant_num(self, key, default):
        return val(self.remnant_setting(key, default))

    def monster_level(self, e):
        return monster_level(self.data, e)

    def remnant_rise(self, dead, level):
        """The dead monster's magic rises as a Shard Remnant, as strong as it was, and goes for its killer."""
        w = self.w
        e = w.add_npc(LIVING, dead.z, dead.x, dead.y, "-", "Bad")
        if e is None:
            return
        make_remnant(self.data, e, level)
        e.fades_at = w.now + int(self.remnant_num("Mob.Lasts", 120) * 1000)
        e.rises_at = w.now + RISE_MS                             # (view.py "rz": the page shows it once it's formed)
        w.sound("Remnant_Rise", e.z, e.cx, e.cy)
        w.fx_anim("Shard_Form", e.z, e.cx, e.fy - 20, 700, delay=RISE_MS - 300)
        # (to its killer, its Shards set off for the Shard bar as if picked up, then turn and fly back into it)
        self.emit({"t": "shardfly", "x": int(dead.cx), "y": int(dead.cy), "n": 5, "back": [int(e.cx), int(e.fy - 20)],
                   "ms": RISE_MS})
        if self.get_attribute("Unmade") == "1":                  # (the Seam unmade: its scraps hunt no more)
            e.aggressive = 0                                     # (passive: it only fights back)
            self.display_message("The %s's magic rises from it, and drifts, and does not come for you." % self.display_name(dead),
                                 "DAMAGE", "-")
            return
        self.display_message("The %s's magic rises from it: a Shard Remnant!" % self.display_name(dead), "DAMAGE", "-")
        if e.ai is not None:
            w.npc_start_fight(e, e.ai, self, 0)

    # ----- Shards off the ground
    def gather_shards(self, n, x, y):
        """n Shards picked up (or drunk) off the ground at x,y: onto the balance, flying there on the page (the
        bar counts them as they land, with their sound), a little Shardcraft, and counted (RemnantsAbsorbed: Wim's
        check, The Spellwright)."""
        n = int(n)
        if n <= 0:
            return
        self.add_shards(n)
        p = self.player
        self.emit({"t": "shardfly", "x": int(x), "y": int(y), "n": n, "to": self.shard_balance,
                   "px": int(p.cx), "py": int(p.cy)})
        self.update_attribute("RemnantsAbsorbed", "+%d" % n)
        xp = self.remnant_num("Absorb.XP", self.remnant_num("Absorb.Magic.XP", 0.05)) * n
        if xp > 0:
            self.update_skill("Shardcraft", "+%s" % round(xp, 3), pop=False)


def fade_remnants(w):
    """Risen Shard Remnants nobody is fighting fade away once their time is up (the world's tick; a map's stay)."""
    for e in [e for e in w.ents if e.alive and e.name == LIVING and getattr(e, "fades_at", None) is not None]:
        if w.now >= e.fades_at and not e.in_combat:
            w.shard_fade(e)
            w.remove_entity(e)
