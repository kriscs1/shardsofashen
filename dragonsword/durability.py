"""Weapons and armour wear out. Each has Entities.ini Durability= (how many blows it takes); the wear an item has had
is kept with it (in the inventory, worn, in the bank, dropped and picked up, and in the save). A weapon wears a
little with every blow it lands; when something hits you, one piece of what you're wearing takes it. Worn out, it
breaks: no Attack or Defence until it's mended (the warnings come first).

Mending: right-click a blacksmith (the Ashford smith, the Frosthold forgemaster, Brokk) and Repair: they mend
everything you carry and wear, for gold. Or use a worn item on an anvil yourself: a bar of its metal (leather for
leather, logs for wood), and Smithing practice."""
import math

from .lb import val, word, trim, lbstr, pretty, random_number

# what an item is made of (its name's start) -> (what mends it at an anvil, the Smithing level needed)
MATERIALS = [("Copper", "Copper_Bar", 1), ("Bronze", "Bronze_Bar", 1), ("Iron", "Iron_Bar", 5),
             ("Steel", "Steel_Bar", 15), ("Mithril", "Mithril_Bar", 25), ("Leather", "Leather", 1),
             ("Oak", "Oak_Logs", 1), ("Wooden", "Logs", 1), ("Willow", "Willow_Logs", 5), ("Yew", "Yew_Logs", 10)]
ARMOUR_SLOTS = (2, 3, 4, 5, 6, 7)          # Shield, Head, Body, Legs, Feet, Hands (1 = the weapon, 8 = a ring)


class DurabilityMixin:
    def item_max_dur(self, name):
        cache = self.__dict__.setdefault("dur_cache", {})
        if name not in cache:
            cache[name] = max(0, int(val(self.entity_ini(name, "Durability", "0")))) if name else 0
        return cache[name]

    def is_broken(self, name, wear):
        m = self.item_max_dur(name)
        return m > 0 and wear >= m

    def dur_text(self, name, wear):
        m = self.item_max_dur(name)
        if m <= 0:
            return ""
        left = max(0, m - wear)
        return "broken!" if left == 0 else "%d%%" % int(math.ceil(100.0 * left / m))

    # ----- wearing out
    def wear_slot(self, s, amount=1):
        item = self.equipped[s]
        m = self.item_max_dur(item) if item else 0
        if m <= 0:
            return
        before = self.equip_wear[s]
        self.equip_wear[s] = min(m, before + amount)
        after = self.equip_wear[s]
        if before < m <= after:
            self.display_message("Your %s has broken! It's no use until it's mended (a blacksmith, or an anvil)."
                                 % pretty(item), "DAMAGE")
            self.play_sound("Locked")
            self.recalc_equipment()
            if self.stats_view == 1:
                self.stats_dirty = True
        elif before < m * 0.8 <= after:
            self.display_message("Your %s is badly worn: get it mended soon." % pretty(item), "DAMAGE")
        if self.stats_view == 1:
            self.stats_dirty = True

    def wear_weapon(self):
        self.wear_slot(1)

    def wear_armour(self):
        worn = [s for s in ARMOUR_SLOTS if self.equipped[s] and self.item_max_dur(self.equipped[s]) > 0]
        if worn:
            self.wear_slot(worn[random_number(1, len(worn)) - 1])

    # ----- keeping the wear with the item as it moves about
    def take_inventory_entity(self, e):
        """Takes one of this very item out of the inventory (not just one of that name). Its wear."""
        wear = getattr(e, "wear", 0)
        if e in self.inv:
            e.quantity -= 1
            if e.quantity <= 0:
                e.alive = False
                self.inv.remove(e)
            self.check_locks(True)
        return wear

    def wears_of(self, name, quantity):
        """The wear of the last quantity items of that name in the inventory (the ones remove_inventory_item takes)."""
        return [getattr(x, "wear", 0) for x in reversed(self.inv) if x.name == name][:quantity]

    # ----- mending
    def repair_cost(self, name, wear):
        m = self.item_max_dur(name)
        if m <= 0 or wear <= 0:
            return 0
        worth = max(1, val(self.entity_ini(name, "Value", "10")))
        return max(1, int(math.ceil(worth * wear / float(m) * 0.4)))

    def worn_things(self):
        """[(where, what, wear, cost)] of everything carried or worn that needs mending: where = ("slot", s) or
        ("inv", entity)."""
        out = []
        for s in range(1, self.equip_slots + 1):
            it = self.equipped[s]
            if it and self.equip_wear[s] > 0 and self.item_max_dur(it) > 0:
                out.append((("slot", s), it, self.equip_wear[s], self.repair_cost(it, self.equip_wear[s])))
        for e in self.inv:
            if getattr(e, "wear", 0) > 0 and self.item_max_dur(e.name) > 0:
                out.append((("inv", e), e.name, e.wear, self.repair_cost(e.name, e.wear)))
        return out

    def mend(self, where):
        kind, what = where
        if kind == "slot":
            self.equip_wear[what] = 0
        else:
            what.wear = 0

    def repair_by_smith(self, smith):
        """A blacksmith mends everything you carry and wear, for gold (about 40% of what the wear took off it)."""
        things = self.worn_things()
        who = self.display_name(smith)
        if not things:
            self.display_message("%s looks your gear over: \"Nothing here needs mending.\"" % who, "INFO")
            return
        cost = sum(c for _, _, _, c in things)
        gold = self.items_held("Gold_Coin(s)")
        if gold < cost:
            self.display_message("%s: \"Mending all that is %d gold. You've only got %d.\"" % (who, cost, gold), "FAIL")
            return
        self.remove_inventory_item("Gold_Coin(s)", cost)
        for where, _, _, _ in things:
            self.mend(where)
        self.play_sound("Anvil")
        self.display_message("%s mends %d thing%s for %d gold. Good as new!" % (who, len(things),
                                                                               "" if len(things) == 1 else "s", cost),
                             "SUCCESS")
        self.recalc_equipment()
        self.stats_dirty = True

    def repair_at_anvil(self, item):
        """Using a worn item on an anvil: a bar of its metal (or leather, or logs) mends it, given the Smithing."""
        name, wear = item.name, getattr(item, "wear", 0)
        if self.item_max_dur(name) <= 0:
            return False
        if wear <= 0:
            self.display_message("The %s doesn't need mending." % pretty(name), "INFO")
            return True
        mat = next(((m, need, lvl) for m, need, lvl in MATERIALS if name.startswith(m)), None)
        if mat is None:
            self.display_message("Only a master smith could mend the %s." % pretty(name), "FAIL")
            return True
        _, need, level = mat
        if self.skill_level("Smithing") < level:
            self.display_message("You need level %d Smithing to mend the %s." % (level, pretty(name)), "FAIL")
            return True
        if self.items_held(need) < 1:
            self.display_message("You need %s to mend the %s." % (pretty(need), pretty(name)), "FAIL")
            return True
        self.remove_inventory_item(need, 1)
        item.wear = 0
        self.play_sound("Anvil")
        self.display_message("You hammer the %s back into shape with %s." % (pretty(name), pretty(need)), "SUCCESS")
        self.update_skill("Smithing", "+" + lbstr(0.15 + 0.02 * level))
        return True

    # ----- the save
    @staticmethod
    def split_wear(value):
        """"Iron_Sword,15" -> ("Iron_Sword", 15)."""
        name = trim(word(value, 1, ","))
        return name, max(0, int(val(word(value, 2, ",")))) if word(value, 2, ",") else 0
