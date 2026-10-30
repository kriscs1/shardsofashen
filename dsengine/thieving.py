"""The hands of a thief (Sneaking only: stances.py). Every number is in data\\Thieving.ini.

  Pickpocket  townsfolk (anyone you can talk to who isn't an animal): gold and a thing or two, by their trade
              ([Pickpocket.<Trade>]); once in a while for each of them (personal).
  Steal       a shop's shelves (Shelf_Goods*): one of the nearest shopkeeper's wares; harder under their eye.
              Or a house's Valuables (a box of someone's precious things: [Valuables]), harder with anyone about.

Caught, the one you robbed shouts for the guard: a guard comes for you (a few levels above you), seen by everyone
but after you alone, gone after a while or when you're out of reach; and a shopkeeper won't serve you for a time."""
import random

from ashen.lb import val, word, trim, lbstr, distance, rnd, parse_quantity, pretty, strip_digits
from .entity import NPC, TILE, STATICOBJECT

THIEVES = "Thieving.ini"


class ThiefMixin:
    def thief_num(self, sec, key, default):
        v = trim(self.data.ini_read(THIEVES, sec, key, ""))
        return val(v) if v else default

    def thief_text(self, sec, key, default=""):
        return trim(self.data.ini_read(THIEVES, sec, key, "")) or default

    # ----- who and what can be robbed (player_actions.get_verbs asks)
    def can_pickpocket(self, e):
        if not self.sneaking() or e.type != NPC or e.owner is not None or self.w.hostile_for(e, self):
            return False
        d = self.data
        if "Talk to" not in (e.use_words or "") or trim(d.entity_ini(e.name, "Calls", "")) or \
                trim(d.entity_ini(e.name, "Vehicle", "")) == "1" or trim(d.entity_ini(e.name, "Flees", "")) == "1":
            return False
        return True

    def can_steal(self, e):
        return self.sneaking() and ((e.type == TILE and e.name.startswith("Shelf_Goods")) or
                                    (e.type == STATICOBJECT and e.name.startswith("Valuables")))

    def trade_of(self, e):
        """Its trade, for Thieving.ini [Pickpocket.<Trade>]: the kind (Baker), or the trade in its Id
        (Galaith_Baker_336 -> Baker)."""
        for name in (e.name, e.npc_id or ""):
            for part in strip_digits(name).strip("_").split("_")[::-1]:
                if part and self.data.ini_read(THIEVES, "Pickpocket." + part, "Level", ""):
                    return part
        return ""

    def thief_chance(self, level, watched):
        """In 100: equal Stealth and level, Chance; each level either way, Chance.Per.Level; watched, less."""
        c = self.thief_num("Pickpocket", "Chance", 55) + (self.stealth_level() - level) * \
            self.thief_num("Pickpocket", "Chance.Per.Level", 6)
        if watched:
            c -= self.thief_num("Pickpocket", "Watched", 30)
        return max(5, min(95, c))

    def watching(self, e):
        """Does NPC e see you now (its line of sight, and the way it faces if it looks one way)?"""
        p = self.player
        d = distance(e.cx, e.cy, p.cx, p.cy)
        if d > 200 or not self.w.in_line_of_sight(e.z, e.cx, e.cy, p.cx, p.cy):
            return False
        dr = e.direction or 4
        fx = (1 if dr & 2 else 0) - (1 if dr & 8 else 0)
        fy = (1 if dr & 4 else 0) - (1 if dr & 1 else 0)
        return (p.cx - e.cx) * fx + (p.cy - e.cy) * fy > 0      # (in front of it: it sees your hands)

    # ----- the deeds
    def pickpocket(self, e):
        if not self.can_pickpocket(e):
            return
        key = "pick:" + self.w.npc_key(e)
        if self.thief_until.get(key, 0) > self.now:
            self.display_message("You've had your hand in that pocket once already. Best wait.", "FAIL")
            self.play_sound("Denied")
            self.act_done(False)
            return
        trade = self.trade_of(e)
        sec = "Pickpocket." + trade if trade else "Pickpocket"
        level = int(self.thief_num(sec, "Level", self.thief_num("Pickpocket", "Level", 1)))
        if self.stealth_level() < level - self.thief_num("Pickpocket", "Reach", 8):
            self.refuse("You'd never get your hand in there unseen (Stealth %d, about)." % level)
            self.act_done(False)
            return
        self.thief_until[key] = self.now + int(self.thief_num("Pickpocket", "Again.Minutes", 10) * 60000)
        if rnd() * 100 >= self.thief_chance(level, self.watching(e)):
            self.caught(e, "pocket")
            return
        got = []
        gold = parse_quantity(self.thief_text(sec, "Gold", self.thief_text("Pickpocket", "Gold", "2-6")))
        if gold > 0:
            self.add_inventory_item("Gold_Coin(s)", gold)
            got.append("%d gold" % gold)
        for entry in self.thief_text(sec, "Loot", "").split():
            name, amount, percent = word(entry, 1, ","), word(entry, 2, ",") or "1", word(entry, 3, ",") or "100"
            if name and rnd() * 100 < val(percent):
                n = parse_quantity(amount)
                if n > 0 and self.inventory_slots_available(name) > 0:
                    self.add_inventory_item(name, n)
                    got.append(pretty(name) if n == 1 else "%d %s" % (n, pretty(name)))
        self.play_sound("Coins" if gold else "Pickup")
        self.display_message("You lift %s from the %s, unseen." % (" and ".join(got) or "nothing worth having",
                                                                    self.display_name(e)), "SUCCESS")
        self.update_skill("Stealth", "+" + lbstr(self.thief_num("Pickpocket", "XP", 0.25) * max(1, level) ** 0.5))
        self.act_done(True)

    def steal_valuables(self, e):
        """A house's precious things ([Valuables]): one of them, if nobody who lives there catches your hand."""
        key = "valuables:%s@%d,%d" % (e.map, int(e.x), int(e.y))
        if self.thief_until.get(key, 0) > self.now:
            self.display_message("You've been through these already. There's nothing left worth the risk.", "FAIL")
            self.play_sound("Empty")
            self.act_done(False)
            return
        loot = []
        for part in self.thief_text("Valuables", "Items", "Gold_Coin(s),3-10").split():
            bits = part.split(",")
            if len(bits) >= 2 and self.data.entity_ini(bits[0], "Type", ""):
                loot.append((bits[0], bits[1], val(bits[2]) if len(bits) > 2 else 10))
        if not loot:
            return
        level = int(self.thief_num("Valuables", "Level", 4))
        watcher = None
        for n in self.w.npcs_near(e.z, e.cx, e.cy):     # (whoever's about: anyone you could talk to, looking your way)
            if n.alive and n.type == NPC and "Talk to" in (n.use_words or "") and not self.w.hostile_for(n, self) \
                    and distance(n.cx, n.cy, e.cx, e.cy) <= self.thief_num("Valuables", "Watch.Range", 192) \
                    and self.watching(n):
                watcher = n
                break
        self.thief_until[key] = self.now + int(self.thief_num("Valuables", "Again.Minutes", 30) * 60000)
        if rnd() * 100 >= self.thief_chance(level, watcher is not None):
            if watcher is not None:
                self.caught(watcher, "house")
            else:
                self.display_message("Something rattles as you reach in. You freeze, and leave it.", "FAIL", "Fail")
                self.act_done(False)
            return
        total = sum(w for _, _, w in loot)
        roll, name, amount = rnd() * total, loot[0][0], loot[0][1]
        for n_, a_, w_ in loot:
            roll -= w_
            if roll < 0:
                name, amount = n_, a_
                break
        qty = max(1, parse_quantity(amount)) if "-" in amount else max(1, int(val(amount)))
        if self.inventory_slots_available(name) <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            self.act_done(False)
            return
        self.add_inventory_item(name, qty)
        self.play_sound("Coins" if name == "Gold_Coin(s)" else "Pickup")
        self.display_message("You lift %s from among someone's precious things." %
                             ("%d gold" % qty if name == "Gold_Coin(s)" else "the " + pretty(name)), "SUCCESS")
        self.update_skill("Stealth", "+" + lbstr(self.thief_num("Valuables", "XP", 0.4) * max(1, level) ** 0.5))
        self.act_done(True)

    def shopkeeper_near(self, e):
        """(the shopkeeper NPC, its rack) nearest shelf e, on its map: someone whose Talk to shows a shop."""
        best = None
        for n in self.w.ents:
            if n.type != NPC or not n.alive or n.z != e.z or distance(n.cx, n.cy, e.cx, e.cy) > 320:
                continue
            rack = self.shop_rack_of(n)
            if rack and (best is None or distance(n.cx, n.cy, e.cx, e.cy) < best[2]):
                best = (n, rack, distance(n.cx, n.cy, e.cx, e.cy))
        return best[:2] if best else (None, "")

    def shop_rack_of(self, n):
        script = self.find_action_script("Talk to", n.name, NPC, n.npc_id)
        if not script:
            return ""
        cache = self.data.cache("shop_rack")
        if script not in cache:
            rack = ""
            for ln in self.data.read_lines(self.script_path(script)):
                parts = ln.split("\t")
                if len(parts) > 4 and parts[1] == "Display.Item.Rack" and parts[4].upper().startswith("SHOP"):
                    rack = parts[4]
                    break
            cache[script] = rack
        return cache[script]

    def steal_from(self, e):
        if not self.can_steal(e):
            return
        if e.type == STATICOBJECT:
            self.steal_valuables(e)
            return
        keeper, rack = self.shopkeeper_near(e)
        if keeper is None:
            self.display_message("There's nothing on these shelves worth the risk.", "FAIL")
            self.play_sound("Empty")
            self.act_done(False)
            return
        key = "steal:%s@%d,%d" % (e.map, int(e.x), int(e.y))
        if self.thief_until.get(key, 0) > self.now:
            self.display_message("You've taken from these shelves already. They'd notice.", "FAIL")
            self.play_sound("Denied")
            self.act_done(False)
            return
        f = self.data.data_file("ItemRacks.ini")
        from ashen import ini
        wares = []
        for k in range(1, 40):
            entry = ini.read(rack, "Item%d" % k, "", f)
            if not entry:
                continue
            name = trim(word(entry, 1, ","))
            if name and self.data.entity_ini(name, "Type", ""):
                wares.append(name)
        if not wares:
            self.display_message("There's nothing on these shelves worth the risk.", "FAIL")
            self.play_sound("Empty")
            self.act_done(False)
            return
        name = random.choice(wares)
        level = int(min(25, 1 + val(self.data.entity_ini(name, "Value", "1")) * self.thief_num("Steal", "Level.Per.Value",
                                                                                               0.2)))
        self.thief_until[key] = self.now + int(self.thief_num("Steal", "Again.Minutes", 5) * 60000)
        if rnd() * 100 >= self.thief_chance(level, self.watching(keeper)):
            self.caught(keeper, "shop")
            return
        if self.inventory_slots_available(name) <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            self.act_done(False)
            return
        self.add_inventory_item(name, 1)
        self.play_sound("Pickup")
        self.display_message("You slip the %s off the shelf and into your pack." % pretty(name), "SUCCESS")
        self.update_skill("Stealth", "+" + lbstr(self.thief_num("Steal", "XP", 0.3) * max(1, level) ** 0.5))
        self.act_done(True)

    def caught(self, e, how):
        """Caught in the act: they shout; a guard comes for you; a shopkeeper won't serve you a while."""
        self.display_message("The %s catches your hand: \"Thief! Guard!\"" % self.display_name(e), "DAMAGE", "Spotted")
        self.end_sneaking()
        self.w.fx({"t": "mark", "kind": "spotted", "u": e.uid}, e.z, e.cx, e.cy, self)
        self.banned_until[self.w.npc_key(e)] = self.now + int(self.thief_num("Pickpocket", "Caught.Minutes", 15) * 60000)
        self.summon_guard(e)
        self.act_done(False)

    def summon_guard(self, near):
        """A guard comes from a little way off, a few levels above you: everyone sees them, and they're after you
        alone (a foe to you, a guard like any other to the rest)."""
        w, p = self.w, self.player
        kind = self.thief_text("Pickpocket", "Guard", "Guard")
        for r in (96, 128, 64, 160):
            for k in range(8):
                ang = k * 0.785
                import math
                x, y = near.cx + math.cos(ang) * r, near.cy + math.sin(ang) * r
                if w.pixel_walkable(p.z, x, y + 12, self):
                    g = w.add_npc(kind, p.z, x - 16, y - 16, "Attitude=Good", "Good")
                    if g is None:
                        return
                    self.ent_attitudes[g.uid] = True              # (a foe to you alone)
                    level = self.player_level() + int(self.thief_num("Pickpocket", "Guard.Levels.Above", 2))
                    g.hp = g.max_hp = max(g.max_hp, 10 + level * 4)
                    g.strength = max(g.strength, round(level * 0.8))
                    g.defence = max(g.defence, round(level * 0.8))
                    g.aggressive, g.aggro_range = 1, max(g.aggro_range, 300)
                    g.summoned_until = self.now + int(self.thief_num("Pickpocket", "Guard.Lasts", 120) * 1000)
                    g.display = "Guard"
                    if g.ai is not None:
                        w.npc_start_fight(g, g.ai, self, distance(g.cx, g.cy, p.cx, p.cy))
                    self.guards_after.append(g)
                    return

    def thief_tick(self):
        """The guards that came for you go once their time's up (and they aren't fighting you), or you've left."""
        if not self.guards_after:
            return
        keep = []
        for g in self.guards_after:
            if not g.alive:
                continue
            gone = g.z != self.player.z or distance(g.cx, g.cy, self.player.cx, self.player.cy) > 900
            if gone or (self.now >= g.summoned_until and not g.in_combat):
                self.w.fx_anim("Puff", g.z, g.cx, g.cy, 400)
                self.w.remove_entity(g)
            else:
                keep.append(g)
        self.guards_after = keep

    def shop_refused(self, npc):
        """A shopkeeper who caught you stealing won't serve you for a while: True (and they say so)."""
        if npc is None:
            return False
        until = self.banned_until.get(self.w.npc_key(npc), 0)
        if until <= self.now:
            return False
        self.display_message("The %s won't serve you: they remember your hand in their till." % self.display_name(npc),
                             "FAIL", "Denied")
        return True
