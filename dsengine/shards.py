"""Shards: the world's magic, in your pack (the item Shard). Spells and waystones spend them; monsters, digging,
quests, chests and potions give them. Everything that counts, pays or gives them comes through here, so the rules
are the same everywhere: never below nothing, nothing taken unless the thing goes ahead, one clear word (and the
Denied sound) when you're short. Costs are data: Spells.ini Cost=, Config.ini [Shards], Quests.ini Reward.Shards=.

The server runs one player's commands at a time, so a check and its payment can't be split by another click."""
from dragonsword.lb import val, lbstr, trim

SHARD = "Shard"


def shard_words(n):
    return "%s Shard%s" % (lbstr(n), "" if n == 1 else "s")


class ShardMixin:
    def shards(self):
        """How many Shards the player carries (the bank's don't count: magic is spent from your pack)."""
        return self.items_held(SHARD)

    def shard_setting(self, key, default=0):
        """A number from Config.ini [Shards]: key itself, else (Waystone.Galaith) its first part (Waystone)."""
        v = trim(self.data.config_read("Shards", key, ""))
        if v == "" and "." in key:
            v = trim(self.data.config_read("Shards", key.split(".")[0], ""))
        return int(val(v)) if v != "" else int(default)

    def short_of_shards(self, n, what):
        self.refuse("%s needs %s and you have %d." % (what, shard_words(n), self.shards()))

    def spend_shards(self, n, what):
        """Takes n Shards for what, if the player has them: True. If not, nothing is taken, they're told: False."""
        n = int(n)
        if n <= 0:
            return True
        if self.shards() < n:
            self.short_of_shards(n, what)
            return False
        self.remove_inventory_item(SHARD, n)
        self.dirty_me = True
        return True

    def give_shards(self, n, why=""):
        """n Shards into the pack (what won't fit falls at their feet), and a line saying so."""
        n = int(n)
        if n <= 0:
            return
        self.add_inventory_item(SHARD, n, quiet=True)
        self.display_message(("%s: %s." % (why, shard_words(n))) if why else "You gain %s." % shard_words(n), "SUCCESS")

    def shard_quest_reward(self, attribute, value):
        """A quest just reached Done: its Quests.ini Reward.Shards, once (a flag says it's been paid)."""
        for name, d in self.help_read_ini("Quests.ini"):
            if trim(d.get("ATTRIBUTE", "")).upper() != attribute.upper():
                continue
            done, reward = val(d.get("DONE", "0")), int(val(d.get("REWARD.SHARDS", "0")))
            flag = "ShardsPaid." + attribute
            if reward > 0 and done > 0 and value >= done and val(self.get_attribute(flag)) < 1:
                self.update_attribute(flag, "=1")
                self.give_shards(reward, "%s: your reward" % name)
            return

    def shard_start(self, new_character):
        """A new character's Shards (Config [Shards] Start), or, once, those for a character from before Shards."""
        flag = "ShardsGiven"
        if val(self.get_attribute(flag)) >= 1:
            return
        self.update_attribute(flag, "=1")
        n = self.shard_setting("Start" if new_character else "Old.Save.Grant", 12 if new_character else 20)
        if n > 0:
            self.add_inventory_item(SHARD, n, quiet=True)
            if not new_character:
                self.display_message("Magic in Estforlan now runs on Shards, and you have %s to begin with. Read a "
                                     "spell's scroll to learn it for good (H: the journal's Spells)." % shard_words(n),
                                     "ACHIEVEMENT")

    def spellbook(self):
        """The journal's Spells: every spell a scroll teaches (not potions), easiest first: its scroll, level, Shards,
        cooldown and what it does. Whether it's known, and its cooldown now, the page reads from "me"."""
        out = []
        for name, d in self.help_read_ini("Spells.ini"):
            scroll = trim(d.get("SCROLL", ""))
            if not scroll or trim(d.get("KIND", "")).upper() == "POTION":
                continue
            info = self.entity_ini(scroll, "Examine.Info", "")
            what = info.split(": ", 1)[1] if ": " in info else info
            what = what.split(" Magic %s." % trim(d.get("LEVEL", "1")), 1)[0].rstrip(". ")
            out.append({"spell": name, "scroll": scroll, "level": int(val(d.get("LEVEL", "1"))),
                        "skill": trim(d.get("SKILL", "")) or "Magic", "cost": int(val(d.get("COST", "0"))),
                        "cooldown": val(d.get("COOLDOWN", "0")), "effect": trim(d.get("EFFECT", "Bolt")).title(),
                        "what": what})
        return sorted(out, key=lambda r: (r["level"], r["spell"]))
