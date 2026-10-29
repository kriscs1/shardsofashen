"""Chests: what's in them is shown before it's yours. When a player Opens (or Searches) an object and its script gives
them things (Give.Item), the things go into that chest instead, and when the script ends the chest opens as a box:
Take 1, Take all, or Take everything. What's left stays in that chest for that player (saved with them), so they can
come back for it when they've room. It works for every chest's script as it is: nothing in the scripts changes.

Each player's chests are their own: the chest scripts already give each player their reward once."""
import random

from ashen.lb import lbstr, pretty

from .entity import ACTIONBOXITEM, INVENTORYITEM, STATICOBJECT

VERBS = ("Open", "Search")
MAX_KEPT = 200                      # chests a player can have things left in


class ChestMixin:
    def init_chests(self):
        self.chests = {}                # "map|x|y|name" -> [[item, qty]] left in it
        self.loot_key = None            # the chest a script is filling now
        self.loot_collect = None        # what its script has given so far
        self.loot_hold = False          # (Goto.Script: the same chest, the script goes on)
        self.chest_open = None          # the chest shown in the box

    def chest_key(self, e):
        return "%s|%d|%d|%s" % (e.map, int(e.x), int(e.y), e.name)

    def chest_action(self, verb, e, script):
        """Before a chest's script: anything left in it is shown at once; else its Give.Items fill it. True if the
        chest was shown (the script isn't run)."""
        if verb not in VERBS or e is None or e.type != STATICOBJECT:
            return False
        key = self.chest_key(e)
        if self.chests.get(key):
            if self.player_distance_to(e) > 56:
                self.display_message("You are too far away!", "FAIL")
                return True
            self.play_sound("Chest")
            self.show_chest(key, full=True)
            return True
        if script:
            self.loot_key, self.loot_collect = key, []
        return False

    def loot_give(self, item, qty):
        """Give.Item while a chest's script runs: into the chest. True if it went there."""
        if self.loot_collect is None or not item or qty <= 0:
            return False
        for it in self.loot_collect:
            if it[0] == item:
                it[1] += qty
                return True
        self.loot_collect.append([item, qty])
        return True

    def loot_finish(self):
        """The chest's script has ended: if it gave anything, the chest opens."""
        key, got = self.loot_key, self.loot_collect
        self.loot_key = self.loot_collect = None
        if not key or not got:
            return
        if random.uniform(0, 100) < self.shard_setting("Chest.Chance", 40):    # (Shards among the treasure, now and
            from .digging import roll                                         #  then: only when it gave something,
            got.append(["Shard", roll(self.data.shards_ini("Shards", "Chest", "3-15"))])   # once)
        have = self.chests.setdefault(key, [])
        for item, qty in got:
            same = next((it for it in have if it[0] == item), None)
            if same:
                same[1] += qty
            else:
                have.append([item, qty])
        if len(self.chests) > MAX_KEPT:              # (forget the oldest-filled first)
            for k in list(self.chests)[:len(self.chests) - MAX_KEPT]:
                if k != key:
                    del self.chests[k]
        self.show_chest(key, full=True)

    def show_chest(self, key, full=False):
        items = [it for it in self.chests.get(key, []) if it[1] > 0]
        self.chests[key] = items
        if not items:
            self.chests.pop(key, None)
            self.close_action_box(-1)
            self.display_message("You've taken everything from the chest.", "INFO")
            return
        self.chest_open = key
        self.rack_type = "Chest"
        self.rack = [{"item": n, "quantity": q} for n, q in items]
        self.ab_item_defs = [(n, lbstr(q), i) for i, (n, q) in enumerate(items)]
        self.rack_pages = 1
        self.responses = ["Take everything", "Close"]
        self.response_actions = ["CHEST_ALL", "CLOSE"]
        name = key.rsplit("|", 1)[-1]
        self.ab_image = name
        self.ab_title = pretty(name)
        self.ab_text = ""
        if full or self.ab_mode != "Chest":
            self.show_action_box("Chest")
        else:
            self.emit(self.box_state())

    def chest_verbs(self, e):
        if e.type == ACTIONBOXITEM:
            return "Take 1,Take all,Examine"
        if e.type == INVENTORYITEM:
            return "Examine"
        return ""

    def take_from_chest(self, i, qty):
        items = self.chests.get(self.chest_open or "", [])
        if not 0 <= i < len(items):
            return 0
        item, have = items[i]
        n = min(have, qty, self.inventory_slots_available(item))
        if n <= 0:
            self.display_message("You don't have room in your inventory for the %s!" % pretty(item), "FAIL")
            return 0
        self.add_inventory_item(item, n, quiet=True)
        items[i][1] -= n
        return n

    def chest_do(self, verb, e):
        """Take 1 / Take all in the chest's box: True if it was one."""
        if self.ab_mode != "Chest" or e.type != ACTIONBOXITEM or verb not in ("Take 1", "Take all"):
            return False
        i = e.misc if isinstance(e.misc, int) else -1
        items = self.chests.get(self.chest_open or "", [])
        if 0 <= i < len(items):
            name = items[i][0]
            n = self.take_from_chest(i, 1 if verb == "Take 1" else items[i][1])
            if n:
                self.play_sound("Coins" if name == "Gold_Coin(s)" else "Pickup")
                self.display_message("You take %s %s." % (lbstr(n), pretty(name)), "SUCCESS")
        self.show_chest(self.chest_open)
        return True

    def chest_response(self, action):
        if action != "CHEST_ALL":
            return False
        items = self.chests.get(self.chest_open or "", [])
        took = []
        for i in range(len(items)):
            name = items[i][0]
            n = self.take_from_chest(i, items[i][1])
            if n:
                took.append("%s %s" % (lbstr(n), pretty(name)))
        if took:
            self.play_sound("Pickup")
            self.display_message("You take %s." % ", ".join(took), "SUCCESS")
        self.show_chest(self.chest_open)
        return True

    # ----- saving (with the character)
    def chests_state(self):
        return {k: [list(it) for it in v if it[1] > 0] for k, v in self.chests.items() if v}

    def load_chests(self, saved):
        self.chests = {}
        for k, v in (saved or {}).items():
            try:
                self.chests[str(k)] = [[str(n), int(q)] for n, q in v if int(q) > 0]
            except (TypeError, ValueError):
                continue
