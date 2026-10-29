"""A player's things: the inventory, dropping, the item racks (shops, crafting) and the bank, equipment and its wear
(durability), the hotbar and the gravestone left when you die. As the desktop game's entities.py, interact.py,
durability.py and extras.py, for one player of many: shop stock is shared (the world's action queue), the rest is theirs."""
import math
import os

from ashen import ini
from ashen.lb import val, word, trim, lbstr, pretty, random_number

from .entity import InvItem, Entity, ACTIONBOXITEM, MAPITEM, STATICOBJECT
from .shards import SHARD

MATERIALS = [("Copper", "Copper_Bar", 1), ("Bronze", "Bronze_Bar", 1), ("Iron", "Iron_Bar", 3),
             ("Steel", "Steel_Bar", 8), ("Mithril", "Mithril_Bar", 13), ("Leather", "Leather", 1),
             ("Oak", "Oak_Logs", 1), ("Wooden", "Logs", 1), ("Willow", "Willow_Logs", 3), ("Yew", "Yew_Logs", 5)]
ARMOUR_SLOTS = (2, 3, 4, 5, 6, 7)


class ItemsMixin:
    # =================================================================================================================
    # Inventory
    # =================================================================================================================
    def entity_ini(self, name, key, default):
        return self.data.entity_ini(name, key, default)

    def inventory_capacity(self):
        return self.data.inventory_columns * self.data.inventory_rows

    def stackable_quantity(self, name):
        return self.data.stackable_quantity(name)

    def inventory_slots_available(self, name):
        stack = self.stackable_quantity(name)
        room = max(0, self.inventory_capacity() - len(self.inv)) * stack
        for e in self.inv:
            if e.name == name:
                room += max(0, stack - e.quantity)
        return room

    def empty_inventory_slots(self):
        return max(0, self.inventory_capacity() - len(self.inv))

    def items_held(self, name):
        if name == SHARD:
            return self.shard_balance                   # (Shards are a balance: shards.py)
        return sum(e.quantity for e in self.inv if e.name == name)

    def inv_item(self, uid):
        return next((e for e in self.inv if e.uid == uid), None)

    def add_inventory_item(self, name, quantity, wear=0, quiet=False):
        if name == "" or quantity <= 0:
            return
        quantity = int(quantity)
        if name == SHARD:
            self.add_shards(quantity)                   # (onto the balance, never into the pack)
            return
        self.reward_note(name, quantity)
        room = self.inventory_slots_available(name)
        if room - quantity < 0:
            dropped = quantity - room
            self.drop_on_floor(name, dropped)
            if not quiet:
                self.display_message("There is not enough room in your inventory (Dropping %d on the ground)." %
                                     dropped, "ERROR")
            quantity = room
            if quantity <= 0:
                return
        stack = self.stackable_quantity(name)
        for e in self.inv:
            if quantity <= 0:
                break
            if e.name == name and e.quantity < stack:
                added = min(quantity, stack - e.quantity)
                quantity -= added
                e.quantity += added
        while quantity > 0 and len(self.inv) < self.inventory_capacity():
            n = min(quantity, stack)
            quantity -= n
            self.inv.append(InvItem(name, n, wear))
        self.dirty_me = True
        if not quiet:
            self.check_locks(True)

    def remove_inventory_item(self, name, quantity):
        if name == SHARD:
            self.take_shards(quantity)
            return
        quantity = min(int(quantity), self.items_held(name))
        if quantity <= 0:
            return
        if self.item_in_use is not None and self.item_in_use.name == name:
            self.item_in_use = None
        for e in reversed(list(self.inv)):
            if quantity <= 0:
                break
            if e.name == name:
                removed = min(quantity, e.quantity)
                quantity -= removed
                e.quantity -= removed
                if e.quantity <= 0:
                    e.alive = False
                    self.inv.remove(e)
        self.dirty_me = True
        self.check_locks(True)

    def drop_on_floor(self, name, quantity, wear=0):
        """Puts items on the ground at the player's feet; they despawn after a while. For the first seconds (Config
        [Gameplay] Drop.Private.Seconds, 10) only the one who dropped them sees them; then everyone does."""
        if quantity <= 0:
            return
        p = self.player
        w, h = self.data.sprite_size_of(MAPITEM, name)
        x = int(p.fx - w / 2)
        y = int(p.fy - h + 4)
        e = self.w.add_map_item(name, p.z, x, y, quantity)
        if e is not None:
            e.wear = wear
            e.source = "DROPPED"
            secs = val(self.data.config_read("Gameplay", "Drop.Private.Seconds", "10"))
            if secs > 0:
                e.private_to = self
                e.public_at = self.now + secs * 1000
            m = self.w.maps.get(e.map)
            if m is not None:
                self.w.add_action_to_queue("REMOVE", name, "MapItem", lbstr(quantity), m.name,
                                           self.w.local_coords(m, x, y), self.data.item_despawn_delay)

    def take_inventory_entity(self, e):
        """Takes one of this very item out of the inventory. Its wear."""
        wear = e.wear
        if e in self.inv:
            e.quantity -= 1
            if e.quantity <= 0:
                e.alive = False
                self.inv.remove(e)
            self.dirty_me = True
            self.check_locks(True)
        return wear

    # ----- tools (Durability, and no Slot: they work from your pack) wear with each use, and a broken one won't do
    def is_tool(self, name):
        return self.data.item_max_dur(name) > 0 and self.item_equip_slot(name) == 0

    def tools_held(self, name):
        """How many of this tool you have that still work."""
        m = self.data.item_max_dur(name)
        return sum(e.quantity for e in self.inv if e.name == name and (m <= 0 or e.wear < m))

    def use_tool(self, name):
        """A use of the tool: the most worn one that still works wears (one is worn out at a time)."""
        m = self.data.item_max_dur(name)
        working = [e for e in self.inv if e.name == name and e.wear < m]
        if m <= 0 or not working:
            return False
        e = max(working, key=lambda x: x.wear)
        before = e.wear
        e.wear = min(m, before + 1)
        if e.wear >= m:
            self.display_message("Your %s has broken! It's no use until it's mended (a blacksmith, or an anvil)."
                                 % pretty(name), "DAMAGE")
            self.play_sound("Locked")
        elif before < m * 0.8 <= e.wear:
            self.display_message("Your %s is badly worn: get it mended soon." % pretty(name), "DAMAGE")
        self.dirty_me = True
        return True

    def wears_of(self, name, quantity):
        return [x.wear for x in reversed(self.inv) if x.name == name][:quantity]

    # =================================================================================================================
    # Item racks (shops, crafting) and the bank
    # =================================================================================================================
    def item_price(self, name, rate, minimum):
        price = int(val(self.entity_ini(name, "Value", "0")) * rate + 0.5)
        return max(price, minimum)

    def sell_price(self, name):
        return self.item_price(name, self.rack_sell_rate * self.data.sell_price_factor, 1)

    def can_sell_here(self, name):
        if name == "Gold_Coin(s)" or val(self.entity_ini(name, "Value", "0")) <= 0:
            return False
        return not (self.rack_specific == 1 and not any(r["item"] == name for r in self.rack))

    def rack_pseudo(self, i):
        """An ActionBox item for rack (or bank) slot i, as the desktop game had them."""
        e = Entity(ACTIONBOXITEM, "")
        e.misc = i
        if self.rack_type == "Bank":
            if isinstance(i, int) and 1 <= i <= self.data.bank_slots:
                e.name = self.bank_item[i]
        elif isinstance(i, int) and 0 <= i < len(self.rack):
            e.name = self.rack[i]["item"]
        return e

    def rack_level_short(self, e):
        if self.ab_mode != "Craft" or e is None or e.type != ACTIONBOXITEM or not self.rack_skill:
            return 0
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return 0
        need = self.rack[i]["level"]
        return need if need > 0 and self.skill_level(self.rack_skill) < need else 0

    def rack_missing(self, e):
        if self.ab_mode != "Craft" or e is None or e.type != ACTIONBOXITEM:
            return ""
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return ""
        ingredients, j, short = self.rack[i]["info"], 1, []
        while word(ingredients, j) != "":
            if self.items_held(word(ingredients, j)) < max(1, val(word(ingredients, j + 1))):
                short.append(pretty(word(ingredients, j)))
            j += 2
        return ", ".join(short)

    def open_item_rack(self, type_name, npc, rack):
        """Display.Item.Rack: BANK, or a data\\ItemRacks.ini section (Type=Shop/Craft). True if shown."""
        f = self.data.data_file("ItemRacks.ini")
        kind = trim(type_name).upper()
        rack = trim(rack)
        if rack == "-":
            rack = ""
        if kind != "BANK" and rack:
            it = ini.read(rack, "Type", "", f).upper()
            if it:
                kind = it
        if kind == "BANK":
            self.rack_type = "Bank"
        elif kind in ("SHOP", "GENERAL", "SPECIFIC"):
            self.rack_type = "Shop"
        elif kind in ("CRAFT", "CREATABLES", "CRAFTING"):
            self.rack_type = "Craft"
        else:
            self.log("ERROR - Item rack type '%s' (%s) not supported" % (type_name, rack))
            return False
        if self.rack_type != "Bank":
            if ini.read(rack, "Type", "", f) == "" and ini.read(rack, "Item1", "", f) == "":
                self.display_message("There's nothing here.", "FAIL")
                return False
        self.rack_name = rack
        self.rack = []
        self.rack_page = 1
        self.rack_filter, self.rack_ready = "", False
        self.rack_buy_rate = val(ini.read(rack, "Buy.Rate", "1.2", f))
        self.rack_sell_rate = val(ini.read(rack, "Sell.Rate", "0.8", f))
        self.rack_specific = val(ini.read(rack, "Specific", "0", f))
        if type_name.upper() == "SPECIFIC" and self.rack_type == "Shop":
            self.rack_specific = 1
        self.rack_skill = ini.read(rack, "Skill", "", f)
        if self.rack_type != "Bank":
            for i in range(1, 201):
                item = ini.read(rack, "Item%d" % i, "", f)
                if item == "":
                    break
                r = {"item": trim(word(item, 1, ",")), "quantity": 0, "info": "", "xp": 0, "level": 0}
                if self.rack_type == "Shop":
                    stock = trim(word(item, 2, ","))
                    r["quantity"] = -1 if stock in ("+", "") or stock.lower() == "inf" else val(stock)
                else:
                    r["info"] = trim(word(item, 2, ","))
                    r["xp"] = val(word(item, 3, ","))
                    r["level"] = val(word(item, 4, ","))
                    r["quantity"] = max(1, val(word(item, 5, ",")))
                self.rack.append(r)
            if self.rack_type == "Shop":
                self.apply_shop_queue()
            elif self.rack_type == "Craft":
                self.rack.sort(key=lambda r: r["level"])          # (by the level it needs: easiest first)
        self.ab_image = self.npc_image(npc)
        self.ab_title = (self.npc_title(npc) if npc else "") or self.rack_type
        if npc in ("You", "Player"):
            self.ab_title = self.player_name
        self.show_rack_page(True)
        return True

    def npc_image(self, npc):
        d = self.data
        if npc in ("You", "Player", self.player_name):
            npc = self.player_sprite_base
        if d.loaded(npc + "4a"):
            return npc + "4a"
        if d.loaded(npc):
            return npc
        return d.fallback_sprite()

    def apply_shop_queue(self):
        """The shop's stock as everyone has left it: what's been bought and sold and not restocked yet."""
        for entry in self.w.action_queue:
            parts = entry.split("\t")
            if len(parts) > 3 and parts[2] == self.rack_name:
                if parts[0] == "ADD.SHOP.ITEM":
                    self.change_rack_stock(parts[1], -val(parts[3]))
                elif parts[0] == "REMOVE.SHOP.ITEM":
                    self.change_rack_stock(parts[1], val(parts[3]))

    def shop_restocked(self, rack_name, item, change):
        """The world's queue restocked (or sold off) a shop's item: shown if this player has that shop open."""
        if self.ab_mode == "Shop" and self.rack_name == rack_name:
            self.change_rack_stock(item, change)
            self.show_rack_page(False)

    def shop_changed_by_other(self, rack_name, item, change):
        """Someone else bought or sold at this shop while it's open here too."""
        if self.ab_mode == "Shop" and self.rack_name == rack_name:
            self.change_rack_stock(item, change)
            self.show_rack_page(False)

    def change_rack_stock(self, item, change):
        for r in self.rack:
            if r["item"] == item:
                if r["quantity"] >= 0:
                    r["quantity"] = max(0, r["quantity"] + change)
                return
        if change > 0 and len(self.rack) < 200:
            self.rack.append({"item": item, "quantity": change, "info": "", "xp": 0, "level": 0})

    def rack_shows(self, i):
        """Is rack (or bank) slot i shown: its name has what was searched for in it; with "Can make" (crafting), you
        have the level and everything it needs."""
        e = self.rack_pseudo(i)
        q = self.rack_filter.strip().lower()
        if q and q not in pretty(e.name).lower() and q not in e.name.lower():
            return False
        if self.rack_ready and self.rack_type == "Craft":
            return not self.rack_level_short(e) and not self.rack_missing(e)
        return True

    def set_rack_filter(self, q, ready):
        if self.ab_mode not in ("Shop", "Bank", "Craft"):
            return
        self.rack_filter, self.rack_ready = str(q or "")[:30], bool(ready)
        self.rack_page = 1
        self.show_rack_page(False)

    def show_rack_page(self, full_redraw):
        d = self.data
        if self.rack_type == "Bank":
            visible = [i for i in range(1, d.bank_slots + 1) if self.bank_item[i]]
        else:
            visible = [i for i, r in enumerate(self.rack) if r["quantity"] != 0]
        visible = [i for i in visible if self.rack_shows(i)]
        page_size = max(1, d.ab_columns * d.ab_rows)
        total_pages = max(1, int((len(visible) + page_size - 1) / page_size))
        self.rack_pages = total_pages
        self.rack_page = min(max(1, self.rack_page), total_pages)
        self.ab_item_defs = []
        for i in visible[(self.rack_page - 1) * page_size:self.rack_page * page_size]:
            if self.rack_type == "Bank":
                self.ab_item_defs.append((self.bank_item[i], lbstr(self.bank_qty[i]), i))
            else:
                r = self.rack[i]
                q = "+" if r["quantity"] < 0 else lbstr(r["quantity"])
                if self.rack_type == "Craft":
                    q = "1"
                self.ab_item_defs.append((r["item"], q, i))
        self.responses = []
        self.response_actions = []
        if self.rack_page < total_pages:
            self.responses.append("Next page")
            self.response_actions.append("NEXT")
        if self.rack_page > 1:
            self.responses.append("Previous page")
            self.response_actions.append("PREV")
        self.responses.append("Close")
        self.response_actions.append("CLOSE")
        if full_redraw or self.ab_mode != self.rack_type:
            self.show_action_box(self.rack_type)
        else:
            self.emit(self.box_state())

    def show_action_box(self, mode):
        """Shop Craft Bank Conversation: the box opens in this player's browser."""
        self.stop_player_walk()
        self.ab_mode = mode
        if not self.ab_image:
            self.ab_image = "Placeholder"
        if not self.ab_title:
            self.ab_title = "?"
        self.emit(self.box_state())

    def hide_action_box(self):
        if self.ab_mode == "":
            return
        self.ab_mode = ""
        self.emit({"t": "box", "mode": ""})

    def close_action_box(self, result):
        """Closes the ActionBox; a script waiting on it carries on (result -1 = cancelled)."""
        self.native_menu = None
        self.hide_action_box()
        if self.script_state in ("CONVERSATION", "RACK"):
            self.script_result = result

    def action_box_response_chosen(self, n):
        if self.ab_mode == "Conversation" and self.native_menu is not None:
            self.native_menu_chosen(n)
            return
        if self.ab_mode == "Conversation":
            self.close_action_box(n)
            return
        action = self.response_actions[n - 1] if 0 <= n - 1 < len(self.response_actions) else ""
        if action.startswith("MARKET_"):
            self.market_response(action)
        elif action.startswith("CHEST_"):
            self.chest_response(action)
        elif action == "NEXT":
            self.rack_page += 1
            self.show_market() if self.ab_mode == "Market" else self.show_rack_page(False)
        elif action == "PREV":
            self.rack_page -= 1
            self.show_market() if self.ab_mode == "Market" else self.show_rack_page(False)
        else:
            self.close_action_box(-1)

    def rack_buy(self, e, quantity):
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return
        r = self.rack[i]
        item = r["item"]
        price = self.item_price(item, self.rack_buy_rate, 1)
        if r["quantity"] >= 0:
            quantity = min(quantity, r["quantity"])
        quantity = min(quantity, int(self.items_held("Gold_Coin(s)") / price))
        if quantity <= 0:
            self.display_message("You don't have enough gold!" if r["quantity"] != 0 else "That's sold out.", "FAIL")
            return
        quantity = min(quantity, self.inventory_slots_available(item))
        if quantity <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        self.remove_inventory_item("Gold_Coin(s)", price * quantity)
        self.add_inventory_item(item, quantity)
        if r["quantity"] >= 0:
            r["quantity"] -= quantity
            self.w.add_action_to_queue("ADD.SHOP.ITEM", item, self.rack_name, lbstr(quantity), "-", "0,0",
                                       self.shop_restock_seconds(item))
            for s in self.w.sessions.values():
                if s is not self:
                    s.shop_changed_by_other(self.rack_name, item, -quantity)
        self.display_message("You buy (%d) %s for %d gold." % (quantity, pretty(item), price * quantity), "SUCCESS")
        self.play_sound("Coins")
        self.show_rack_page(False)

    def shop_restock_seconds(self, item):
        return int(self.data.shop_restock_delay * min(4, 1 + val(self.entity_ini(item, "Value", "0")) / 100))

    def rack_sell(self, e, quantity):
        item = e.name
        if item == "Gold_Coin(s)":
            self.display_message("You can't sell gold!", "FAIL")
            return
        price = self.sell_price(item)
        if val(self.entity_ini(item, "Value", "0")) <= 0:
            self.display_message("You can't sell that!", "FAIL")
            return
        if not self.can_sell_here(item):
            self.display_message("You can't sell that here!", "FAIL")
            return
        quantity = min(max(1, quantity), self.items_held(item))
        if quantity <= 0:
            return
        self.remove_inventory_item(item, quantity)
        if price > 0:
            self.add_inventory_item("Gold_Coin(s)", price * quantity)
        self.change_rack_stock(item, quantity)
        self.w.add_action_to_queue("REMOVE.SHOP.ITEM", item, self.rack_name, lbstr(quantity), "-", "0,0",
                                   self.shop_restock_seconds(item))
        for s in self.w.sessions.values():
            if s is not self:
                s.shop_changed_by_other(self.rack_name, item, quantity)
        self.display_message("You sell (%d) %s for %d gold." % (quantity, pretty(item), price * quantity), "SUCCESS")
        self.play_sound("Coins")
        self.show_rack_page(False)

    def rack_value(self, e):
        item = e.name
        if e.type == ACTIONBOXITEM:
            self.display_message("%s (buy for %d gold)" % (pretty(item), self.item_price(item, self.rack_buy_rate, 1)),
                                 "INFO")
        elif not self.can_sell_here(item):
            self.display_message("%s can't be sold here." % pretty(item), "INFO")
        else:
            self.display_message("%s (sell for %d gold)" % (pretty(item), self.sell_price(item)), "INFO")

    def bank_quantity_of(self, item):
        for i in range(1, self.data.bank_slots + 1):
            if self.bank_item[i] == item:
                return self.bank_qty[i]
        return 0

    def bank_deposit(self, e, quantity):
        item = e.name
        quantity = min(max(1, quantity), self.items_held(item))
        if quantity <= 0:
            return
        slots = self.data.bank_slots
        slot = next((i for i in range(1, slots + 1) if self.bank_item[i] == item), 0)
        if slot == 0:
            slot = next((i for i in range(1, slots + 1) if self.bank_item[i] == ""), 0)
        if slot == 0:
            self.display_message("There is no more room in your bank!", "FAIL")
            return
        self.bank_item[slot] = item
        self.bank_qty[slot] += quantity
        if self.data.item_max_dur(item) > 0:
            self.bank_wear[slot] += self.wears_of(item, quantity)
        self.remove_inventory_item(item, quantity)
        self.display_message("You bank (%d) %s." % (quantity, pretty(item)), "SUCCESS")
        self.show_rack_page(False)

    def bank_withdraw(self, e, quantity):
        slot = val(e.misc)
        if not isinstance(slot, int) or slot < 1 or slot > self.data.bank_slots or not self.bank_item[slot]:
            return
        item = self.bank_item[slot]
        if quantity < 0:
            quantity = self.bank_qty[slot]
        quantity = min(quantity, self.bank_qty[slot])
        room = self.inventory_slots_available(item)
        if room <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        if quantity > room:
            self.display_message("You can't carry any more!", "FAIL")
        quantity = min(quantity, room)
        self.bank_qty[slot] -= quantity
        if self.bank_qty[slot] <= 0:
            self.bank_item[slot] = ""
            self.bank_qty[slot] = 0
        if self.data.item_max_dur(item) > 0:
            for _ in range(quantity):
                wears = self.bank_wear[slot]
                self.add_inventory_item(item, 1, wears.pop() if wears else 0)
            if self.bank_qty[slot] <= 0:
                self.bank_wear[slot] = []
        else:
            self.add_inventory_item(item, quantity)
        self.display_message("You take (%d) %s." % (quantity, pretty(item)), "SUCCESS")
        self.show_rack_page(False)

    @staticmethod
    def ingredients_text(ingredients):
        parts = []
        j = 1
        while word(ingredients, j) != "":
            parts.append("%s %s" % (lbstr(val(word(ingredients, j + 1))), pretty(word(ingredients, j))))
            j += 2
        return ", ".join(parts)

    def craft_make(self, e):
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return
        r = self.rack[i]
        if r["level"] > 0 and self.rack_skill and self.skill_level(self.rack_skill) < r["level"]:
            self.refuse("You need level %s %s to make that!" % (lbstr(r["level"]), pretty(self.rack_skill)))
            return
        ingredients = r["info"]
        j = 1
        while word(ingredients, j) != "":
            if self.items_held(word(ingredients, j)) < max(1, val(word(ingredients, j + 1))):
                self.display_message("You need %s to make %s!" % (self.ingredients_text(ingredients),
                                                                 pretty(r["item"])), "FAIL")
                return
            j += 2
        j = 1
        while word(ingredients, j) != "":
            self.remove_inventory_item(word(ingredients, j), max(1, val(word(ingredients, j + 1))))
            j += 2
        self.add_inventory_item(r["item"], r["quantity"])
        self.display_message("You make (%s) %s." % (lbstr(r["quantity"]), pretty(r["item"])), "SUCCESS")
        self.play_sound(self.craft_sound(), (self.player.cx, self.player.cy))
        if self.rack_skill and r["xp"] != 0:
            self.update_skill(self.rack_skill, "+" + lbstr(r["xp"]))
        self.emit(self.box_state())

    def craft_sound(self):
        s, rack = self.rack_skill.upper(), self.rack_name.upper()
        if "SMELT" in rack:
            return "Smelt"
        if s == "SMITHING" or "SMITH" in rack or "FORGE" in rack:           # (Crafting at an anvil: smithing)
            return "Anvil"
        return {"POTION_MAKING": "Brew", "ALCHEMY": "Brew", "COOKING": "CookingFood", "MAGIC": "SpellCast",
                "CHANNELING": "SpellCast", "SHARDCRAFT": "SpellCast"}.get(s, "Craft")

    def craft_inspect(self, e):
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return
        r = self.rack[i]
        info = "%s needs %s" % (pretty(r["item"]), self.ingredients_text(r["info"]))
        if r["quantity"] > 1:
            info = "%s %s" % (lbstr(r["quantity"]), info)
        if r["level"] > 0:
            info += " (%s level %s)" % (self.rack_skill, lbstr(r["level"]))
        self.display_message(info + ".", "INFO")

    # =================================================================================================================
    # Equipment
    # =================================================================================================================
    def equip_slot_index(self, slot):
        s = trim(slot).upper()
        for i in range(1, self.data.equip_slots + 1):
            if self.data.equip_slot_names[i].upper() == s:
                return i
        return 0

    def item_equip_slot(self, item):
        return self.equip_slot_index(self.entity_ini(item, "Slot", "")) if item else 0

    def equip_verb(self, item):
        s = self.item_equip_slot(item)
        if s == 0:
            return ""
        return "Wield" if self.data.equip_slot_names[s].upper() in ("WEAPON", "SHIELD") else "Wear"

    def item_bonus(self, item, key):
        return val(self.entity_ini(item, key, "0")) if item else 0

    def items_equipped(self, item):
        if not item:
            return 0
        return sum(1 for i in range(1, self.data.equip_slots + 1) if self.equipped[i] == item)

    def is_broken(self, name, wear):
        m = self.data.item_max_dur(name)
        return m > 0 and wear >= m

    def dur_text(self, name, wear):
        m = self.data.item_max_dur(name)
        if m <= 0:
            return ""
        left = max(0, m - wear)
        return "broken!" if left == 0 else "%d%%" % int(math.ceil(100.0 * left / m))

    def recalc_equipment(self):
        self.equip_attack_total = self.equip_defence_total = self.equip_magic_total = 0
        for i in range(1, self.data.equip_slots + 1):
            it = self.equipped[i]
            if it and not self.is_broken(it, self.equip_wear[i]):
                self.equip_attack_total += self.item_bonus(it, "Attack")
                self.equip_defence_total += self.item_bonus(it, "Defence")
                self.equip_magic_total += self.item_bonus(it, "Magic")
        self.dirty_me = True

    def equip_requirement(self, item):
        req = trim(self.entity_ini(item, "Requires", "").replace(",", " "))
        k = 1
        while word(req, k) != "":
            skill = word(req, k)
            level = val(word(req, k + 1))
            if level > 0 and self.skill_level(skill) < level:
                return "level %s %s" % (lbstr(level), pretty(skill))
            k += 2
        return ""

    def equip_item(self, e):
        item = e.name
        s = self.item_equip_slot(item)
        if s == 0:
            self.refuse("You can't wear that!")
            return
        verb = self.equip_verb(item).lower()
        need = self.equip_requirement(item)
        if need:
            self.refuse("You need %s to %s the %s." % (need, verb, pretty(item)))
            return
        old = self.equipped[s]
        if old:
            room = self.inventory_slots_available(old)
            if e.quantity <= 1:
                room += 1
            if room < 1:
                self.display_message("You need room in your inventory to take off the %s." % pretty(old), "FAIL")
                return
        wear = self.take_inventory_entity(e)
        old_wear = self.equip_wear[s]
        self.equipped[s] = item
        self.equip_wear[s] = wear
        if old:
            self.add_inventory_item(old, 1, old_wear)
        self.display_message("You %s the %s." % (verb, pretty(item)), "SUCCESS")
        self.equipment_changed()

    def unequip_slot(self, s):
        if s < 1 or s > self.data.equip_slots:
            return
        item = self.equipped[s]
        if not item:
            return
        if self.inventory_slots_available(item) < 1:
            self.display_message("You don't have room in your inventory for the %s." % pretty(item), "FAIL")
            return
        self.equipped[s] = ""
        self.add_inventory_item(item, 1, self.equip_wear[s])
        self.equip_wear[s] = 0
        self.display_message("You take off the %s." % pretty(item), "SUCCESS")
        self.equipment_changed()

    def equipment_changed(self):
        self.recalc_equipment()
        self.check_locks(True)

    def check_saved_equipment(self):
        for i in range(1, self.data.equip_slots + 1):
            item = self.equipped[i]
            if item and self.item_equip_slot(item) != i:
                self.equipped[i] = ""
                if self.inventory_slots_available(item) >= 1:
                    self.add_inventory_item(item, 1, quiet=True)

    def worn_items(self):
        """What is drawn over the player, lowest first."""
        if self.player_sprite_base not in ("Player", "PlayerF"):
            return []                                   # (a shape a script made them: no armour drawn on it)
        d = self.data
        items = []
        for s in range(1, d.equip_slots + 1):
            it = self.equipped[s]
            it = trim(self.entity_ini(it, "Base", "")) or it if it else it     # (enchanted: drawn as it was)
            if it and d.gear_has_art(it):
                items.append((d.gear_rank[s], it))
        items.sort()
        return [it for _, it in items]

    # ----- wear
    def wear_slot(self, s, amount=1):
        item = self.equipped[s]
        m = self.data.item_max_dur(item) if item else 0
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
        elif before < m * 0.8 <= after:
            self.display_message("Your %s is badly worn: get it mended soon." % pretty(item), "DAMAGE")
        self.dirty_me = True

    def wear_weapon(self):
        self.wear_slot(1)

    def wear_armour(self):
        worn = [s for s in ARMOUR_SLOTS if self.equipped[s] and self.data.item_max_dur(self.equipped[s]) > 0]
        if worn:
            self.wear_slot(worn[random_number(1, len(worn)) - 1])

    def repair_cost(self, name, wear):
        m = self.data.item_max_dur(name)
        if m <= 0 or wear <= 0:
            return 0
        worth = max(1, val(self.entity_ini(name, "Value", "10")))
        return max(1, int(math.ceil(worth * wear / float(m) * 0.4)))

    def worn_things(self):
        out = []
        for s in range(1, self.data.equip_slots + 1):
            it = self.equipped[s]
            if it and self.equip_wear[s] > 0 and self.data.item_max_dur(it) > 0:
                out.append((("slot", s), it, self.equip_wear[s], self.repair_cost(it, self.equip_wear[s])))
        for e in self.inv:
            if e.wear > 0 and self.data.item_max_dur(e.name) > 0:
                out.append((("inv", e), e.name, e.wear, self.repair_cost(e.name, e.wear)))
        return out

    def repair_by_smith(self, smith):
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
        for (kind, what), _, _, _ in things:
            if kind == "slot":
                self.equip_wear[what] = 0
            else:
                what.wear = 0
        self.play_sound("Anvil", (smith.cx, smith.cy))
        self.display_message("%s mends %d thing%s for %d gold. Good as new!" % (
            who, len(things), "" if len(things) == 1 else "s", cost), "SUCCESS")
        self.recalc_equipment()

    def repair_at_anvil(self, item):
        name, wear = item.name, item.wear
        if self.data.item_max_dur(name) <= 0:
            return False
        if wear <= 0:
            self.display_message("The %s doesn't need mending." % pretty(name), "INFO")
            return True
        base = trim(self.entity_ini(name, "Base", "")) or name                # (enchanted: mended as it was)
        mat = next(((m, need, lvl) for m, need, lvl in MATERIALS if base.startswith(m)), None)
        if mat is None:
            self.display_message("Only a master smith could mend the %s." % pretty(name), "FAIL")
            return True
        _, need, level = mat
        if self.skill_level("Crafting") < level:
            self.refuse("You need level %d Crafting to mend the %s." % (level, pretty(name)))
            return True
        if self.items_held(need) < 1:
            self.display_message("You need %s to mend the %s." % (pretty(need), pretty(name)), "FAIL")
            return True
        self.remove_inventory_item(need, 1)
        item.wear = 0
        self.dirty_me = True
        self.play_sound("Anvil", (self.player.cx, self.player.cy))
        self.display_message("You hammer the %s back into shape with %s." % (pretty(name), pretty(need)), "SUCCESS")
        self.update_skill("Crafting", "+" + lbstr(0.15 + 0.02 * level))
        return True

    # =================================================================================================================
    # The hotbar
    # =================================================================================================================
    def hotbar_add(self, name):
        if name in self.hotbar:
            return
        free = [k for k, n in enumerate(self.hotbar) if not n]
        k = free[0] if free else len(self.hotbar) - 1
        self.hotbar[k] = name
        self.dirty_me = True
        self.display_message("%s is on your hotbar: press %d to use it." % (pretty(name), k + 1), "INFO")

    def hotbar_remove(self, k):
        if 0 <= k < len(self.hotbar) and self.hotbar[k]:
            self.display_message("%s is off your hotbar." % pretty(self.hotbar[k]), "INFO")
            self.hotbar[k] = ""
            self.dirty_me = True

    def hotbar_use(self, k):
        if not (0 <= k < len(self.hotbar)) or not self.hotbar[k] or not self.user_input_enabled or self.ab_mode:
            return
        name = self.hotbar[k]
        e = next((i for i in self.inv if i.name == name), None)
        spell = self.spell_learnable(name)
        if e is None and spell in self.spells_known:
            self.cast_spell(spell, None)                # (a known spell's scroll: the spell, scroll or no scroll)
            return
        if e is None:
            self.display_message("You have no %s left." % pretty(name), "FAIL")
            return
        verbs = [v for v in self.get_verbs(e).split(",") if v and v not in ("Hotbar", "Off hotbar")]
        if verbs:
            self.do_action(verbs[0], e)

    # =================================================================================================================
    # The gravestone (only its owner sees it)
    # =================================================================================================================
    def grave_minutes(self):
        return max(0.5, val(self.data.config_read("Gameplay", "Grave.Minutes", "10")))

    def grave_leave(self):
        old = self.grave
        if old and old.get("items"):
            self.display_message("Your old grave crumbles away, and what was in it with it.", "DAMAGE")
        self.grave_remove_entity()
        items = self.death_sort()
        self.dirty_me = True
        self.check_locks(True)
        if not items:
            self.grave = None
            return
        p = self.player
        m = self.cur_map
        self.grave = {"map": m.name, "x": int(p.fx - m.ox) - 16, "y": int(p.fy - m.oy) - 28, "items": items,
                      "left": self.grave_minutes() * 60000}
        self.display_message("Everything else you carried lies in a grave where you fell: it's marked on your "
                             "minimap. Get back to it within %s minutes!" % lbstr(self.grave_minutes()), "DAMAGE")

    def death_sort(self):
        """Dying: what you can't drop stays with you, and so do your most valuable things (Config [Gameplay]
        Death.Keep.Items, 5: single items, worn or carried; not gold). The rest goes in the grave: [(name, qty, wear)]."""
        d = self.data
        keep_n = max(0, int(val(d.config_read("Gameplay", "Death.Keep.Items", "5"))))
        units = []                      # (value, order, where, index): one per single item
        for k, e in enumerate(self.inv):
            if self.kept_on_death(e.name) or e.name == "Gold_Coin(s)":
                continue
            worth = val(self.entity_ini(e.name, "Value", "0"))
            for _ in range(min(e.quantity, keep_n)):
                units.append((worth, len(units), "inv", k))
        for i in range(1, d.equip_slots + 1):
            if self.equipped[i]:
                units.append((val(self.entity_ini(self.equipped[i], "Value", "0")), len(units), "eq", i))
        units.sort(key=lambda u: (-u[0], u[1]))
        keep_inv, keep_eq = {}, set()
        for worth, _, where, k in units[:keep_n]:
            if where == "inv":
                keep_inv[k] = keep_inv.get(k, 0) + 1
            else:
                keep_eq.add(k)
        grave, kept_inv, kept_names = [], [], []
        for k, e in enumerate(self.inv):
            if self.kept_on_death(e.name) and e.name != "Gold_Coin(s)":
                kept_inv.append(e)
                continue
            stay = keep_inv.get(k, 0)
            if stay:
                kept_names += [e.name] * stay
            if stay >= e.quantity:
                kept_inv.append(e)
                continue
            grave.append((e.name, e.quantity - stay, e.wear))
            if stay:
                e.quantity = stay
                kept_inv.append(e)
            else:
                e.alive = False
        self.inv[:] = kept_inv
        for i in range(1, d.equip_slots + 1):
            if self.equipped[i] and i not in keep_eq:
                grave.append((self.equipped[i], 1, self.equip_wear[i]))
                self.equipped[i] = ""
                self.equip_wear[i] = 0
            elif self.equipped[i]:
                kept_names.append(self.equipped[i])
        self.recalc_equipment()
        if kept_names:
            counts = {}
            for n in kept_names:
                counts[n] = counts.get(n, 0) + 1
            self.display_message("You keep your most valuable things: %s." %
                                 ", ".join(("%d %s" % (q, pretty(n)) if q > 1 else pretty(n)) for n, q in counts.items()),
                                 "INFO")
        return grave

    def kept_on_death(self, name):
        """Entities.ini Keep.On.Death=1 (by default, whatever can't be dropped: quest things, the Access Crystal)."""
        undroppable = val(self.entity_ini(name, "Droppable", "1")) == 0
        return val(self.entity_ini(name, "Keep.On.Death", "1" if undroppable else "0")) == 1

    def grave_place(self):
        g = self.grave
        if not g or self.cur_map is None:
            return
        if self.grave_ent is not None and self.grave_ent.alive:
            return
        m = self.w.map_named(g["map"])
        if m is None or m not in self.w.neighbours(self.cur_map):
            return
        self.grave_ent = self.w.add_static_object("Gravestone", m.mz, m.ox + g["x"], m.oy + g["y"], owner=self,
                                                  home=m.name)

    def grave_remove_entity(self):
        if self.grave_ent is not None:
            self.w.remove_entity(self.grave_ent)
        self.grave_ent = None

    def grave_tick(self, delta_ms):
        g = self.grave
        if not g:
            return
        g["left"] -= delta_ms
        if g["left"] <= 0:
            self.grave_remove_entity()
            self.grave = None
            self.dirty_me = True
            self.display_message("Your grave has crumbled away: what you left in it is lost.", "DAMAGE")

    def grave_search(self):
        g = self.grave
        if not g:
            self.display_message("The grave is empty.", "INFO")
            return
        left = []
        for name, qty, wear in g["items"]:
            room = self.inventory_slots_available(name)
            take = min(qty, room)
            if take > 0:
                self.add_inventory_item(name, take, wear)
            if qty - take > 0:
                left.append((name, qty - take, wear))
        if left:
            g["items"] = left
            self.display_message("You take what you can carry; the rest is still in the grave.", "INFO")
            return
        self.grave_remove_entity()
        self.grave = None
        self.dirty_me = True
        self.play_sound("Pickup")
        self.display_message("You take back everything from your grave.", "SUCCESS")
