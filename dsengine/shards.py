"""Shards: the world's magic, a balance each player has (shown under their health: never an item in the pack).
Spells, shardstones and anything else magical spend them; monsters, digging, quests, chests, dismantling and potions
give them. Everything that counts, pays or gives them comes through here, so the rules are the same everywhere:
never below nothing, nothing taken unless the thing goes ahead, one clear word (and the Denied sound) when you're
short. Costs are data: data/Shards.ini (every Shard number in one place), Spells.ini Cost=, Quests.ini
Reward.Shards=.

The item Shard is only a name for them: given (a script's Give.Item, a chest, a drop, an old save's pack) it goes on
the balance; asked for (>Got.Item, Take.Item, $Item.Shard) it's the balance.

Spells have ranks: a scroll with Rank=2 (Fire_Bolt_Scroll_II) raises a spell you know to rank 2, and Shards.ini
[Upgrade.<Spell>] says its scroll (Scroll.2) and what changes at that rank (Damage.2, Cost.2, Level.2...), used from
that rank up.

The server runs one player's commands at a time, so a check and its payment can't be split by another click."""
from ashen.lb import val, lbstr, trim, pretty
from .ownspell import OWN

SHARD = "Shard"
ROMAN = {1: "", 2: " II", 3: " III", 4: " IV", 5: " V"}


def shard_words(n):
    return "%s Shard%s" % (lbstr(n), "" if n == 1 else "s")


def channeled_cost(cost, channeling, data):
    """A spell's Shards a cast at a Channeling level: Shards.ini [Channeling] Saving.Per.Level percent off for each
    level past the first, never more than Saving.Max percent, and never under Min.Cost (a spell that costs nothing
    still costs nothing)."""
    cost = val(cost)
    if cost <= 0:
        return 0
    num = lambda k, dflt: val(trim(data.shards_ini("Channeling", k, "")) or dflt)
    saving = min(num("Saving.Max", 30), max(0, int(channeling) - 1) * num("Saving.Per.Level", 1.5)) / 100.0
    return max(min(cost, num("Min.Cost", 1)), int(round(cost * (1 - saving))))


def quest_xp(d):
    """A quest's Reward.XP ("Strength 3 Defence 3"): [(skill, xp)]."""
    w = trim(d.get("REWARD.XP", "")).replace(",", " ").split()
    return [(w[k], val(w[k + 1])) for k in range(0, len(w) - 1, 2) if val(w[k + 1]) > 0]


class ShardMixin:
    # ----- the balance
    def shards(self):
        return self.shard_balance

    def shard_setting(self, key, default=0, section="Shards"):
        """A number from Shards.ini [Shards]: key itself, else (Shardstone.Galaith) its first part (Shardstone)."""
        v = trim(self.data.shards_ini(section, key, ""))
        if v == "" and "." in key:
            v = trim(self.data.shards_ini(section, key.split(".")[0], ""))
        return val(v) if v != "" else default

    def short_of_shards(self, n, what):
        self.refuse("%s needs %s and you have %d." % (what, shard_words(n), self.shards()))

    def spend_shards(self, n, what):
        """Takes n Shards for what, if the player has them: True. If not, nothing is taken, they're told: False."""
        n = int(n)
        if n <= 0:
            return True
        if self.shard_balance < n:
            self.short_of_shards(n, what)
            return False
        self.shard_balance -= n
        self.dirty_me = True
        return True

    def take_shards(self, n):
        """As many as there are, up to n (a script's Take.Item Shard): never below nothing."""
        self.shard_balance = max(0, self.shard_balance - max(0, int(n)))
        self.dirty_me = True

    def add_shards(self, n):
        self.shard_balance += max(0, int(n))
        self.dirty_me = True
        self.reward_note(SHARD, n)

    def give_shards(self, n, why=""):
        """n Shards on the balance, and a line saying so."""
        n = int(n)
        if n <= 0:
            return
        self.add_shards(n)
        self.display_message(("%s: +%s." % (why, shard_words(n))) if why else "+%s." % shard_words(n), "SUCCESS")

    def shards_from_bank(self):
        """Shards an old save banked (when they were an item): onto the balance."""
        for i in range(1, self.data.bank_slots + 1):
            if self.bank_item[i] == SHARD:
                self.add_shards(self.bank_qty[i])
                self.bank_item[i], self.bank_qty[i], self.bank_wear[i] = "", 0, []

    def shard_start(self, new_character):
        """A new character's Shards (Shards.ini [Shards] Start), or, once, those for a character from before Shards."""
        flag = "ShardsGiven"
        if val(self.get_attribute(flag)) >= 1:
            return
        self.update_attribute(flag, "=1")
        n = int(self.shard_setting("Start" if new_character else "Old.Save.Grant", 12 if new_character else 20))
        self.add_shards(n)
        if n > 0 and not new_character:
            self.display_message("Magic in Ashen now runs on Shards, and you have %s to begin with. Learn a "
                                 "spell from its scroll, for good, and cast it from Channeling (the Stats box)." % shard_words(n),
                                 "ACHIEVEMENT")

    # ----- quests' rewards, and the screen that shows them
    def quest_reward(self, attribute, value):
        """A quest just reached Done: its Quests.ini Reward.Shards, Reward.Items and Reward.XP (skill and xp pairs,
        given as a script's Update.Skill +n is), once (a flag says they've been given); the reward screen opens,
        listing them and whatever the quest's script gives as it finishes."""
        for name, d in self.help_read_ini("Quests.ini"):
            if trim(d.get("ATTRIBUTE", "")).upper() != attribute.upper():
                continue
            done = val(d.get("DONE", "0"))
            flag = "ShardsPaid." + attribute
            if done <= 0 or value < done or val(self.get_attribute(flag)) >= 1:
                return
            self.update_attribute(flag, "=1")
            self.reward_begin(name)
            n = int(val(d.get("REWARD.SHARDS", "0")))
            if n > 0:
                self.give_shards(n, "%s: your reward" % name)
            items = trim(d.get("REWARD.ITEMS", "")).split()
            for k in range(0, len(items) - 1, 2):
                self.add_inventory_item(items[k], max(1, int(val(items[k + 1]))))
            for skill, xp in quest_xp(d):
                self.update_skill(skill, "+" + lbstr(xp), pop=False)
            return

    def reward_begin(self, quest):
        self.reward = {"quest": quest, "got": {}, "xp": {}, "at": self.now}

    def reward_note(self, item, n):
        """Something given while a quest's reward screen is gathering (its script still running): listed on it."""
        r = getattr(self, "reward", None)
        if r is not None and n > 0:
            r["got"][item] = r["got"].get(item, 0) + int(n)

    def reward_xp(self, skill, n):
        r = getattr(self, "reward", None)
        if r is not None and n > 0:
            r["xp"][skill] = r["xp"].get(skill, 0) + n

    def reward_tick(self):
        """The quest's script has finished (or a moment has passed, if it ran in none): the screen is shown."""
        r = getattr(self, "reward", None)
        if r is None or (self.script_running and self.now - r["at"] < 20000):
            return
        self.reward = None
        if not r["got"] and not r["xp"]:
            return                                      # (it gave nothing: no screen to say so)
        got = sorted(r["got"].items(), key=lambda kv: (kv[0] != SHARD, kv[0]))
        self.emit({"t": "reward", "quest": r["quest"], "items": [[k, n] for k, n in got if k != SHARD],
                   "shards": r["got"].get(SHARD, 0), "xp": [[k, round(v, 2)] for k, v in sorted(r["xp"].items())]})

    def channeled(self, cost):
        return channeled_cost(cost, self.skill_level("Channeling"), self.data)

    # ----- spells' ranks
    def spell_rank(self, spell):
        return int(self.spells_known.get(spell, 0))

    def scroll_rank(self, name):
        return max(1, int(val(self.entity_ini(name, "Rank", "1"))))

    def spell_title(self, spell, rank=None):
        if spell == OWN:
            return self.own_spell_title()
        return pretty(spell) + ROMAN.get(rank or max(1, self.spell_rank(spell)), "")

    def spell_ini_at(self, spell, key, default, rank):
        """A spell's value at a rank: Shards.ini [Upgrade.<Spell>] Key.<rank> (or the nearest lower rank's), else its
        Spells.ini Key. (Your own spell: what you wrote at the lectern, ownspell.py.)"""
        if spell == OWN:
            v = self.own_spell_values()
            if v is not None:
                return v.get(key, default)
        for r in range(int(rank), 1, -1):
            v = self.data.shards_ini("Upgrade." + spell, "%s.%d" % (key, r), "")
            if v != "":
                return v
        return self.data.spell_ini(spell, key, default)

    def upgrade_scroll(self, spell, rank):
        return trim(self.data.shards_ini("Upgrade." + spell, "Scroll.%d" % rank, ""))

    def spellbook(self):
        """The journal's Spells: every spell a scroll teaches (not potions), easiest first, at the rank you have (or
        its first): scroll, level, Shards, cooldown, what it does; and its next rank, if there's one."""
        out = []
        for name, d in self.help_read_ini("Spells.ini"):
            scroll = trim(d.get("SCROLL", ""))
            if not scroll or trim(d.get("KIND", "")).upper() == "POTION" or (name == OWN and OWN not in self.spells_known):
                continue
            rank = max(1, self.spell_rank(name))
            at = lambda k, dflt="0", r=rank: self.spell_ini_at(name, k, dflt, r)
            row = {"spell": name, "title": self.spell_title(name, rank), "scroll": scroll, "rank": self.spell_rank(name),
                   "level": int(val(at("Level", "1"))), "skill": trim(d.get("SKILL", "")) or "Channeling",
                   "cost": int(self.channeled(at("Cost"))), "cooldown": val(at("Cooldown")),
                   "what": self.spell_what(name, rank)}
            up = self.upgrade_scroll(name, rank + 1)
            if up:
                row["next"] = {"title": self.spell_title(name, rank + 1), "scroll": up,
                               "level": int(val(self.spell_ini_at(name, "Level", "1", rank + 1))),
                               "cost": int(self.channeled(self.spell_ini_at(name, "Cost", "0", rank + 1))),
                               "what": self.spell_what(name, rank + 1)}
            out.append(row)
        return sorted(out, key=lambda r: (r["level"], r["spell"]))

    def spell_what(self, spell, rank):
        """What a spell does, at a rank, in a few words."""
        at = lambda k, dflt="": self.spell_ini_at(spell, k, dflt, rank)
        eff = trim(at("Effect", "Bolt")).upper()
        if eff in ("BOLT", "AREA"):
            words = "%s damage" % at("Damage")
            if eff == "AREA":
                words += " to every foe within %s tiles" % lbstr(round(val(at("Radius", "128")) / 32))
            if val(at("Freeze", "0")) > 0:
                words += ", %s for %s s" % (at("Freeze.Word", "frozen") or "frozen", at("Freeze"))
            slow = at("Slow")
            if slow:
                words += ", slowed to %s%% for %s s" % tuple(slow.split(",")[:2])
            return words
        if eff == "HEAL":
            return "heals %s hitpoints" % at("Heal")
        info = self.entity_ini(trim(self.data.spell_ini(spell, "Scroll", "")), "Examine.Info", "")
        what = info.split(": ", 1)[1] if ": " in info else info
        return what.split(" Magic ", 1)[0].rstrip(". ")

    # ----- dismantling: gear, or a scroll whose spell you know already, broken down into its Shards
    def dismantle_worth(self, name):
        """How many Shards dismantling it gives (0: it can't be): one for every Shards.ini [Dismantle] Weapon (or
        Armour: anything worn) gold of its value, at least one; Scroll for a scroll whose spell (at its rank) you
        know (worth what a wizard would ask for it, even one a quest gave: dev/migrate/rare_scrolls.py). Not quest
        things (Droppable=0)."""
        spell = self.spell_learnable(name)
        if name == SHARD or (self.entity_ini(name, "Droppable", "1").strip() == "0" and not spell):
            return 0
        value = val(self.entity_ini(name, "Value", "0"))
        if spell:
            if self.spell_rank(spell) < self.scroll_rank(name):
                return 0                                # (not learnt yet: learn it)
            value = value or 100 + 40 * val(self.spell_ini(spell, "Level", "1"))
            per = self.shard_setting("Scroll", 10, "Dismantle")
        elif self.equip_verb(name):
            per = self.shard_setting("Weapon" if self.equip_verb(name) == "Wield" else "Armour", 25, "Dismantle")
        else:
            return 0
        return max(1, int(value // max(1, per)))

    def dismantle(self, item):
        """Asks first (it's gone for good), then breaks it down."""
        n = self.dismantle_worth(item.name)
        if n <= 0:
            self.refuse("There's no magic in the %s to break down." % pretty(item.name))
            return
        uid = item.uid
        self.show_menu("Dismantle", item.name, "Break down the %s? It's gone for good, and its magic gives you %s." %
                       (pretty(item.name), shard_words(n)),
                       [("Dismantle it (+%s)" % shard_words(n), lambda: self.dismantle_now(uid, n)), ("Keep it", None)])

    def dismantle_now(self, uid, n):
        item = self.inv_item(uid)
        if item is None or self.dismantle_worth(item.name) != n:
            return                                      # (gone, or changed, while they were asked)
        name = item.name
        self.remove_inventory_item(name, 1)
        self.play_sound("Craft")
        self.fx_anim("Teleport_Glow", self.player.cx, self.player.cy, 500)
        self.give_shards(n, "You break down the %s" % pretty(name))
        self.dismantled(name, n)                        # (its Shardcraft, and maybe a rare shard: shardcraft.py)
