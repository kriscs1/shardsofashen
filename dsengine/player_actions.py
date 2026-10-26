"""What a player does: the verbs on things (as the desktop game's interact.py), walking there first, and the commands
their browser sends. The browser works out the verbs to show; the server works them out again and only does a verb
the player really has."""
import math

from dragonsword.lb import val, word, trim, lbstr, distance, strip_digits, pretty

from .entity import (Entity, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, INFRONTTILE, ROOF,
                     ACTIONBOXITEM, INVENTORYITEM, TYPE_NAMES)

SEAT_FACES = {"N": 1, "E": 2, "S": 4, "W": 8}    # (Seat= in Tiles.ini: the way you face, sitting on it)
WALK_FIRST_WORDS = ("Wall", "Forest", "Hedge", "Pond", "Pool", "_Window", "Water", "Timber0", "Plaster0", "Sandstone0",
                    "Brick0")


class ActionsMixin:
    # =================================================================================================================
    # Names and verbs
    # =================================================================================================================
    def display_name(self, e):
        if e is None:
            return ""
        if e is self.player:
            return self.player_name
        if getattr(e, "display", ""):
            return e.display
        return strip_digits(e.name).replace("_", " ")

    def npc_title(self, npc):
        """A conversation's or shop's title: the one you clicked by its own name, if it has one (Name= on the map)."""
        e = self.clicked_ent
        if e is not None and e.alive and getattr(e, "display", "") and strip_digits(e.name) == strip_digits(npc):
            return e.display
        return pretty(npc)

    @staticmethod
    def add_verb(lst, verb):
        verb = trim(verb)
        if verb == "":
            return lst
        i = 1
        while word(lst, i, ",") != "":
            if trim(word(lst, i, ",")).upper() == verb.upper():
                return lst
            i += 1
        return verb if lst == "" else lst + "," + verb

    def add_verbs(self, lst, verbs):
        i = 1
        while word(verbs, i, ",") != "":
            lst = self.add_verb(lst, word(verbs, i, ","))
            i += 1
        return lst

    def examine_text(self, e):
        return self.data.examine_text(e.name, e.type)

    def examine_first(self, e):
        if val(e.misc) != 1 or self.examine_text(e) == "" or any(w in e.name for w in WALK_FIRST_WORDS):
            return False
        return "0" in self.data.tile_ini(e.name, "Walkable.Data", self.data.all_walkable)

    def tile_lock_of(self, e):
        """The Lock on a clicked tile that is shut for this player (or None)."""
        if e is None or e.type != TILE:
            return None
        m, tx, ty = self.w.tile_at(self.player.z, e.x + 1, e.y + 1)
        if m is None:
            return None
        lk = m.lock_at.get((tx, ty))
        return lk if lk is not None and self.lock_closed(m, lk) else None

    def get_verbs(self, e):
        """Comma list of verbs for the right-click menu. The first one is the left-click action."""
        if e is None or not e.alive:
            return ""
        t = e.type
        uw = e.use_words
        verbs = ""
        if self.ab_mode == "Market" and t in (INVENTORYITEM, ACTIONBOXITEM):
            return self.market_verbs(e)
        if self.ab_mode == "Chest" and t in (INVENTORYITEM, ACTIONBOXITEM):
            return self.chest_verbs(e)
        if t in (TILE, INFRONTTILE):
            verbs = self.add_verbs(verbs, uw)
            if self.tile_lock_of(e) is not None:
                verbs = self.add_verb(verbs, "Open")
                verbs = self.add_verb(verbs, "Unlock")
            if verbs == "" and self.examine_first(e):
                verbs = "Examine"
            verbs = self.add_verb(verbs, "Walk here")
            if val(e.misc) == 1 or uw != "" or self.examine_text(e) != "":
                verbs = self.add_verb(verbs, "Examine")
        elif t == MAPITEM:
            verbs = "Pickup,Examine"
        elif t == INVENTORYITEM:
            if self.ab_mode == "Shop":
                verbs = "Sell 1,Sell All,Value,Examine" if self.can_sell_here(e.name) else "Examine"
            elif self.ab_mode == "Bank":
                verbs = "Deposit 1,Deposit All,Examine"
            else:
                verbs = self.add_verbs(verbs, self.entity_ini(e.name, "Use.Words", ""))
                verbs = self.add_verb(verbs, self.equip_verb(e.name))
                verbs = self.add_verb(verbs, "Use")
                if e.quantity > 1:
                    verbs = self.add_verb(verbs, "Drop All")
                    verbs = self.add_verb(verbs, "Drop 1")
                else:
                    verbs = self.add_verb(verbs, "Drop")
                verbs = self.add_verb(verbs, "Examine")
                verbs = self.add_verb(verbs, "Off hotbar" if e.name in self.hotbar else "Hotbar")
        elif t == ACTIONBOXITEM:
            if self.ab_mode == "Shop":
                verbs = "Buy 1,Buy 5,Value,Examine"
            elif self.ab_mode == "Bank":
                verbs = "Withdraw 1,Withdraw All,Examine"
            elif self.ab_mode == "Craft":
                verbs = "Make,Inspect,Examine"
            else:
                verbs = "Examine"
        elif t in (STATICOBJECT, TEMPORARY, MISSILE):
            verbs = self.add_verbs(verbs, uw)
            if verbs == "":
                verbs = "Use"
            verbs = self.add_verb(verbs, "Examine")
        elif t == NPC and self.w.hostile_for(e, self):
            verbs = self.add_verb(verbs, "Attack")
            verbs = self.add_verbs(verbs, uw)
            verbs = self.add_verb(verbs, "Examine")
        elif t == NPC:
            for i in range(1, 30):
                v = trim(word(uw, i, ","))
                if v == "":
                    break
                if v.upper() != "ATTACK":
                    verbs = self.add_verb(verbs, v)
            verbs = self.add_verb(verbs, "Talk to")
            verbs = self.add_verb(verbs, "Examine")
        elif t == PLAYER:
            verbs = "Attack,Examine" if self.pvp_ok(self.session_of(e)) else "Examine"
        return verbs

    def verb_range(self, verb, e):
        if e is None or e.type in (INVENTORYITEM, ACTIONBOXITEM, PLAYER):
            return 0
        if verb in ("Examine", "Value", "Inspect", "Walk here", "Cancel"):
            return 0
        if verb == "Pickup":
            return 28
        if verb == "Talk to":
            return 48
        if verb == "Attack":
            return 36 + e.weapon_range
        if verb == "Use with":
            r = 36
            if self.item_in_use is not None:
                spell = self.entity_ini(self.item_in_use.name, "Spell", "")
                if spell:
                    r = 0
                    if self.spell_ini(spell, "Effect", "Bolt").upper() in ("BOLT", "GRASP"):
                        r = max(36, val(self.spell_ini(spell, "Range", "256")) - 16)
            return r
        return 26 if e.type in (TILE, INFRONTTILE) else 36

    # =================================================================================================================
    # What was clicked: the browser names it, the server finds it
    # =================================================================================================================
    def tile_entity_at(self, gx, gy):
        """The tile at global pixel gx,gy as a Tile entity (its decor if it has one), as this player sees it."""
        z = self.player.z
        m, tx, ty = self.w.tile_at(z, gx, gy)
        if m is None or not m.inside(tx, ty):
            return None
        tile, decor = self.cell_names(m, tx, ty)
        name = decor or tile
        if not name or name == "Black001":
            return None
        e = Entity(TILE, name)
        e.z = z
        e.x = m.ox + (tx - 1) * self.tw
        e.y = m.oy + (ty - 1) * self.th
        e.w, e.h = self.tw, self.th
        e.misc = self.data.tile_ini(name, "Show.Name", "0")
        e.use_words = self.data.tile_ini(name, "Use.Words", "")
        e.map = m.name
        e.npc_id = self.data.tile_place(m.name, tx, ty)     # (a tile named in the editor: its own scripts first)
        return e

    def infront_entity_at(self, gx, gy):
        z = self.player.z
        m, tx, ty = self.w.tile_at(z, gx, gy)
        if m is None or not m.inside(tx, ty):
            return None
        name = m.infront[m.cell(tx, ty)]
        if not name:
            return None
        e = Entity(INFRONTTILE, name)
        e.z = z
        e.x, e.y = m.ox + (tx - 1) * self.tw, m.oy + (ty - 1) * self.th
        e.w, e.h = self.tw, self.th
        e.misc = self.data.tile_ini(name, "Show.Name", "0")
        e.use_words = self.data.tile_ini(name, "Use.Words", "")
        e.map = m.name
        return e

    def resolve_target(self, t):
        """{"k": "ent", "uid"} / {"k": "tile"} (at the click) / {"k": "infront"} / {"k": "inv", "uid"} /
        {"k": "rack", "i"} -> the entity, or None."""
        if not isinstance(t, dict):
            return None
        k = t.get("k")
        if k == "ent":
            e = self.w.by_uid.get(t.get("uid"))
            if e is None or not e.alive or not self.w.visible_to(e, self) or e.z != self.player.z:
                return None
            return e
        if k == "player":
            s = next((s for s in self.w.sessions.values() if s.player.uid == t.get("uid") and s.in_world()), None)
            return s.player if s is not None and s.player.z == self.player.z else None
        if k == "tile":
            return self.tile_entity_at(self.script_cursor_x, self.script_cursor_y)
        if k == "infront":
            return self.infront_entity_at(self.script_cursor_x, self.script_cursor_y)
        if k == "inv":
            return self.inv_item(t.get("uid"))
        if k == "rack" and self.ab_mode in ("Shop", "Bank", "Craft", "Market", "Chest"):
            i = t.get("i")
            if not isinstance(i, int):
                return None
            e = self.rack_pseudo(i)
            return e if e.name else None
        return None

    # =================================================================================================================
    # Doing it
    # =================================================================================================================
    def choose_verb(self, verb, e, vx, vy):
        """The player picked verb on entity e (vx,vy: where they clicked, global): walk there if needed, then act."""
        if not self.user_input_enabled and e is not None and e.type not in (INVENTORYITEM, ACTIONBOXITEM):
            return
        self.clicked_ent = e
        self.script_cursor_x, self.script_cursor_y = vx, vy
        self.clicked_tile_x = self.tile_of_x(vx)
        self.clicked_tile_y = self.tile_of_y(vy)
        if verb in ("Cancel", ""):
            return
        if verb == "Walk here":
            if not self.user_input_enabled or self.ab_mode:
                return
            self.player_attack_target = None
            m, tx, ty = self.w.tile_at(self.player.z, vx, vy)
            if m is not None:
                lk = m.lock_at.get((tx, ty))
                if lk is not None and self.lock_closed(m, lk):
                    self.display_message(lk.message, "FAIL")
                    return
            self.walk_player_to(vx, vy - int(self.player.h / 2) + 2, 0, 2)
            return
        if e is None:
            return
        allowed = [v for v in self.get_verbs(e).split(",") if v]
        if verb == "Use with":
            if self.item_in_use is None or (e is self.item_in_use):
                return
        elif verb not in allowed:
            return
        if verb != "Attack":
            self.player_attack_target = None
        rng = self.verb_range(verb, e)
        if rng > 0 and self.player_distance_to(e) > rng:
            if self.ab_mode:
                return
            self.walk_player_to(e.cx, e.cy, 0, rng)
            self.pending_verb = verb
            self.pending_ent = e
            return
        self.stop_player_walk()
        self.do_action(verb, e)

    def do_action(self, verb, e):
        """Runs the script for verb on entity e, or the engine's built-in default."""
        if e is None or not e.alive:
            return
        name, t = e.name, e.type
        self.clicked_ent = e
        if verb == "Use with":
            self.use_item_with(e)
            return
        if (self.chest_do(verb, e) or self.market_do(verb, e, self.verb_price, self.verb_qty) or
                self.board_action(verb, e) or
                self.tavern_action(verb, e)):
            return
        if verb == "Open" and t == TILE:
            lk = self.tile_lock_of(e)
            if lk is not None:
                self.display_message(lk.message, "FAIL")
                return
        if t == TILE and self.crop_action(verb, e):
            return
        if verb == "Dig" and t == INVENTORYITEM:
            self.dig()
            return
        if name == "Homestone" and verb in ("Touch", "Travel", "Use"):
            self.homestone_touched(e)
            return
        if name == "Home_Chest" and verb == "Open":
            self.open_home_chest(e)
            return
        if t != ACTIONBOXITEM:
            script = self.find_action_script(verb, name, t, e.npc_id)
            if self.chest_action(verb, e, script):
                return
            if script:
                self.start_script(script, True)
                if not (self.script_running and self.script_name == script):
                    self.loot_key = self.loot_collect = None        # (it didn't start: nothing to fill)
                return
        if verb == "Examine":
            self.examine_entity(e)
        elif verb == "Pickup":
            self.pickup_map_item(e)
        elif verb in ("Drop", "Drop All"):
            self.drop_inventory_item(e, e.quantity)
        elif verb == "Drop 1":
            self.drop_inventory_item(e, 1)
        elif verb == "Eat" and t == INVENTORYITEM and self.entity_ini(name, "Cures", ""):
            self.drink_cure(e)
        elif verb == "Eat":
            self.eat_inventory_item(e)
        elif verb in ("Wield", "Wear"):
            if t == INVENTORYITEM:
                self.equip_item(e)
            else:
                self.display_message("You can't wear that!", "FAIL")
        elif verb == "Open":
            if t == TILE and self.data.door_open_tile(name):
                self.display_message("It opens as you go through.", "INFO")
            else:
                self.display_message("Nothing interesting happens.", "FAIL")
        elif verb == "Count":
            self.display_message("You have %d %s." % (self.items_held(name), pretty(name)), "INFO")
        elif verb == "Repair" and t == NPC:
            self.repair_by_smith(e)
        elif verb == "Hotbar":
            self.hotbar_add(name)
        elif verb == "Off hotbar":
            self.hotbar_remove(self.hotbar.index(name) if name in self.hotbar else -1)
        elif verb == "Search" and name == "Gravestone":
            self.grave_search()
        elif verb == "Drink" and t == INVENTORYITEM and self.entity_ini(name, "Cures", ""):
            self.drink_cure(e)
        elif verb == "Drink" and t == INVENTORYITEM and val(self.entity_ini(name, "Food.Value", "0")) > 0:
            self.eat_inventory_item(e)
        elif verb in ("Cast", "Drink"):
            if t == INVENTORYITEM and self.entity_ini(name, "Spell", ""):
                self.cast_scroll(e, None)
            else:
                self.display_message("Nothing interesting happens.", "FAIL")
        elif verb == "Use":
            if t == INVENTORYITEM:
                self.item_in_use = e
                self.emit({"t": "use", "uid": e.uid})
            else:
                self.display_message("Nothing interesting happens.", "FAIL")
        elif verb == "Talk to":
            self.display_message("They don't seem interested in talking.", "FAIL")
        elif verb == "Attack":
            self.start_attack(e)
        elif verb == "Sit" and t == TILE:
            self.sit_on(e)
        elif verb == "Sleep":
            if self.start_sleep("Next"):
                self.slept_at_home(e)
        elif verb == "Climb Up":
            self.climb_ladder(1)
        elif verb == "Climb Down":
            self.climb_ladder(-1)
        elif verb == "Bank":
            self.open_item_rack("BANK", name, "-")
        elif verb == "Buy 1":
            self.rack_buy(e, 1)
        elif verb == "Buy 5":
            self.rack_buy(e, 5)
        elif verb == "Value":
            self.rack_value(e)
        elif verb == "Sell 1":
            self.rack_sell(e, 1)
        elif verb == "Sell All":
            self.rack_sell(e, self.items_held(name))
        elif verb == "Deposit 1":
            self.bank_deposit(e, 1)
        elif verb == "Deposit All":
            self.bank_deposit(e, self.items_held(name))
        elif verb == "Withdraw 1":
            self.bank_withdraw(e, 1)
        elif verb == "Withdraw All":
            self.bank_withdraw(e, -1)
        elif verb == "Make":
            self.craft_make(e)
        elif verb == "Inspect":
            self.craft_inspect(e)
        else:
            self.display_message("Nothing interesting happens.", "FAIL")

    # =================================================================================================================
    # Sitting: on a bench or a chair, till you move again
    # =================================================================================================================
    def sit_on(self, e):
        face = SEAT_FACES.get(trim(self.data.tile_ini(e.name, "Seat", "")).upper()[:1])
        if face is None:
            self.display_message("Nothing interesting happens.", "FAIL")
            return
        p = self.player
        x, y = e.x + {2: 2, 8: -2}.get(face, 0), e.y - 8              # (the seat under them, their feet on the floor)
        for s in self.w.sessions.values():
            if s is not self and s.in_world() and s.seat is not None and s.seat[1] == (x, y) and s.player.z == p.z:
                self.display_message("Someone is already sitting there.", "FAIL")
                return
        stood = self.seat[0] if self.seat is not None else (p.x, p.y)
        self.w.set_entity_position(p, x, y)
        self.seat = (stood, (x, y))
        p.direction = face
        p.pose = "Sit"
        self.w.animate_entity(p, False)

    def stand_up(self):
        if self.seat is None:
            return
        (x, y), _ = self.seat
        self.seat = None
        self.player.pose = ""
        self.w.set_entity_position(self.player, x, y)                 # (back where they stood: off the bench)
        self.w.animate_entity(self.player, False)

    def stand_x(self):
        return self.seat[0][0] if self.seat is not None else self.player.x

    def stand_y(self):
        return self.seat[0][1] if self.seat is not None else self.player.y

    def use_item_with(self, target):
        item = self.item_in_use
        self.item_in_use = None
        self.emit({"t": "use", "uid": 0})
        if item is None or target is None or not item.alive or not target.alive:
            return
        a, b = item.name, target.name
        base = strip_digits(b)
        tname = TYPE_NAMES.get(target.type, "")
        self.item_in_use_name = a
        self.clicked_ent = target
        if self.sow_seed(item, target):
            return
        if self.entity_ini(a, "Spell", "") and not self.script_exists("Use %s With %s" % (a, b)):
            self.cast_scroll(item, target)
            return
        script = ""
        tid = target.npc_id if hasattr(target, "npc_id") else ""
        if tid and self.script_exists("Use %s With %s" % (a, tid)):
            script = "Use %s With %s" % (a, tid)
        for cand in ("Use %s With %s" % (a, b), "Use %s With %s" % (b, a)):
            if script == "" and self.script_exists(cand):
                script = cand
        if script == "" and base != b:
            for cand in ("Use %s With %s" % (a, base), "Use %s With %s" % (base, a)):
                if script == "" and self.script_exists(cand):
                    script = cand
        for cand in ("Use %s With [%s]" % (a, tname), "Use [%s] With %s" % (tname, a)):
            if script == "" and self.script_exists(cand):
                script = cand
        if script == "" and base == "Anvil" and item.type == INVENTORYITEM and self.repair_at_anvil(item):
            return
        if script == "":
            self.display_message("Nothing interesting happens.", "FAIL")
        else:
            self.start_script(script, True)

    def examine_entity(self, e):
        if e.type == PLAYER:
            s = next((s for s in self.w.sessions.values() if s.player is e), None)
            if s is not None:
                record = ""
                if val(s.get_attribute("ArenaWins")) or val(s.get_attribute("ArenaLosses")):
                    record = " Arena: %s wins, %s losses." % (s.get_attribute("ArenaWins"), s.get_attribute("ArenaLosses"))
                self.display_message("%s, level %d (%d/%d hitpoints).%s" % (s.player_name, s.player_level(), e.hp,
                                                                           s.player_max_hp, record), "EXAMINE")
            return
        text = self.examine_text(e) or "It's not very interesting."
        if e.type == INVENTORYITEM and self.dur_text(e.name, e.wear):
            text += " (Condition: %s)" % self.dur_text(e.name, e.wear)
        self.display_message(text, "EXAMINE")

    def pickup_map_item(self, e, reach=40):
        """Picks up an item off the map (it's gone for everyone till it respawns; a one-time item is only gone for
        whoever took it: everyone gets their own). reach: how far off it can be (further with a Grasp spell)."""
        w = self.w
        if self.player_distance_to(e) > reach:
            self.display_message("You are too far away to reach that!", "FAIL")
            return
        name = e.name
        quantity = max(1, e.quantity)
        space = self.inventory_slots_available(name)
        if space <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        taken = min(quantity, space)
        once = getattr(e, "once", False)
        if once and taken < quantity:
            self.display_message("You need room for all %d %s." % (quantity, pretty(name)), "FAIL")
            return
        self.add_inventory_item(name, taken, e.wear)
        self.play_sound("Pickup")
        if taken > 1:
            self.display_message("You pick up %d %s." % (taken, pretty(name)), "SUCCESS")
        else:
            self.display_message("You pick up the %s." % pretty(name), "SUCCESS")
        if once:
            key = w.once_key(e)
            if key:
                self.taken_once.add(key)
            if e.owner is self:
                w.remove_entity(e)
            return
        m = w.maps.get(e.map)
        if m is None or e.owner is not None:
            if taken < quantity:
                e.quantity = quantity - taken
            else:
                w.remove_entity(e)
            return
        coords = w.local_coords(m, e.x, e.y)
        if taken < quantity:
            e.quantity = quantity - taken
            self.display_message("You don't have room for the rest.", "FAIL")
            if e.source == "MAP":
                w.remove_action_from_queue("\t".join(["SET.QUANTITY", name, "MapItem", "*", m.name, coords, "*"]))
                w.add_action_to_queue("SET.QUANTITY", name, "MapItem", lbstr(quantity - taken), m.name, coords,
                                      self.item_respawn_seconds(name))
            else:
                w.set_queue_quantity("REMOVE", name, m.name, coords, quantity - taken)
            return
        if e.source == "MAP":
            w.remove_action_from_queue("\t".join(["SET.QUANTITY", name, "MapItem", "*", m.name, coords, "*"]))
            w.add_action_to_queue("ADD", name, "MapItem", lbstr(e.orig_quantity) + (
                " Id=" + e.npc_id if e.npc_id else ""), m.name, w.local_coords(m, e.orig_x, e.orig_y),
                                  self.item_respawn_seconds(name))
        else:
            w.remove_action_from_queue("\t".join(["REMOVE", name, "MapItem", "*", m.name, coords, "*"]))
        w.remove_entity(e)

    def item_respawn_seconds(self, name):
        own = val(self.entity_ini(name, "Respawn", "0"))
        if own > 0:
            return own
        worth = max(0, val(self.entity_ini(name, "Value", "1")))
        return int(min(7200, self.data.item_respawn_delay * (1 + math.sqrt(worth) / 2)))

    def drop_inventory_item(self, e, quantity):
        name = e.name
        if val(self.entity_ini(name, "Droppable", "1")) == 0 or val(self.entity_ini(name, "Undroppable", "0")) == 1:
            self.display_message("You can't drop that!", "FAIL")
            return
        quantity = min(max(1, quantity), max(1, e.quantity))
        if self.data.item_max_dur(name) > 0 and quantity == 1:
            self.drop_on_floor(name, 1, self.take_inventory_entity(e))
        else:
            self.remove_inventory_item(name, quantity)
            self.drop_on_floor(name, quantity)
        self.play_sound("Drop", (self.player.cx, self.player.cy))
        if quantity > 1:
            self.display_message("You drop %d %s." % (quantity, pretty(name)), "SUCCESS")
        else:
            self.display_message("You drop the %s." % pretty(name), "SUCCESS")

    def eat_inventory_item(self, e):
        name = e.name
        food = val(self.entity_ini(name, "Food.Value", "0"))
        if food <= 0:
            self.display_message("You can't eat that!", "FAIL")
            return
        if self.player.hp >= self.player_max_hp:
            self.display_message("You already have full health!", "FAIL")
            return
        self.remove_inventory_item(name, 1)
        self.play_sound("EatFood")
        self.display_message("You eat the %s." % pretty(name), "SUCCESS")
        self.update_skill("Hitpoints", "+" + lbstr(food))

    def climb_ladder(self, dz):
        m = self.cur_map
        name = "%d,%d,%d" % (m.mx, m.my, m.mz + dz)
        if not self.data.map_exists(name):
            self.display_message("It leads nowhere!", "FAIL")
            return
        self.play_sound("Ladder")
        self.display_message("You climb up." if dz > 0 else "You climb down.", "SUCCESS")
        self.teleport(name, self.player.x - m.ox, self.player.y - m.oy)

    # =================================================================================================================
    # The browser's commands
    # =================================================================================================================
    def handle(self, msg):
        """One command from the browser (a dict). Anything malformed is ignored."""
        t = msg.get("t")
        if not self.in_world():
            return
        if self.dead_wait:                  # (dead: nothing but waking up again, and looking at things)
            if t == "respawn":
                self.respawn()
            if t not in ("journal", "explored", "look", "close"):
                return
        if t == "move":
            d = int(msg.get("dir", 0)) & 15
            if d & 5 == 5:
                d -= 5
            if d & 10 == 10:
                d -= 10
            self.keyboard_direction = d if self.user_input_enabled and not self.ab_mode else 0
        elif t == "verb":
            if self.sleep_state:
                return
            vx, vy = float(msg.get("x", self.player.cx)), float(msg.get("y", self.player.cy))
            if abs(vx - self.player.cx) > 3 * self.sw or abs(vy - self.player.cy) > 3 * self.sh:
                return
            self.script_cursor_x, self.script_cursor_y = vx, vy
            verb = str(msg.get("verb", ""))
            self.verb_price, self.verb_qty = msg.get("price", 0), msg.get("qty", 0)
            if verb == "Use with":
                item = self.inv_item(msg.get("item"))
                if item is None:
                    return
                self.item_in_use = item
            target = self.resolve_target(msg.get("target"))
            if verb not in ("Walk here",) and target is None:
                return
            self.choose_verb(verb, target, vx, vy)
        elif t == "use_cancel":
            self.item_in_use = None
        elif t == "respond":
            n = int(msg.get("n", 0))
            if self.ab_mode and 1 <= n <= len(self.responses):
                self.action_box_response_chosen(n)
        elif t == "close":
            if self.ab_mode:
                self.close_action_box(-1)
        elif t == "rack_filter":
            self.set_rack_filter(msg.get("q", ""), msg.get("ready", False))
        elif t == "page":
            if self.ab_mode in ("Shop", "Bank", "Craft", "Market"):
                self.rack_page = int(msg.get("page", 1))
                self.show_market() if self.ab_mode == "Market" else self.show_rack_page(False)
        elif t == "hotbar":
            self.hotbar_use(int(msg.get("k", -1)))
        elif t == "hotbar_remove":
            self.hotbar_remove(int(msg.get("k", -1)))
        elif t == "unequip":
            self.unequip_slot(int(msg.get("slot", 0)))
        elif t == "skill":
            i = int(msg.get("i", 0))
            if 1 <= i <= self.data.total_skills:
                name = self.data.skill_name[i] + " Skill"
                if self.script_exists(name):
                    self.start_script(name, True)
        elif t == "explored":
            cells = msg.get("cells")
            if isinstance(cells, list):
                self.note_explored(str(msg.get("map", "")), cells)
        elif t == "journal":
            self.emit(self.journal_data())
        elif t == "stop":
            self.stop_player_walk()
            self.player_attack_target = None
            self.dirty_me = True
        elif t == "look":
            from .session import clean_look
            self.look = clean_look(msg.get("look"))
            self.dirty_me = True
            self.save_requested = True
        elif t in ("build", "unbuild"):
            if self.sleep_state:
                return
            try:
                x, y = int(msg.get("x", 0)), int(msg.get("y", 0))
            except (TypeError, ValueError):
                return
            if t == "build":
                self.build(x, y, str(msg.get("piece", "")))
            else:
                self.unbuild(x, y)
        elif t == "game":
            self.game_input(msg)
        elif t == "admin" and self.admin_enabled:
            self.admin_command(msg)

    # =================================================================================================================
    # The admin panel (Config [Admin] Players): give yourself items, set skill levels, switch skills off, god mode
    # =================================================================================================================
    def admin_items(self):
        import os
        path = self.data.data_file("Entities.ini")
        items = []
        section = ""
        for line in self.data.read_lines(path):
            ln = trim(line.replace("\t", " ")).strip()
            if ln.startswith("["):
                section = ln[1:-1] if ln.endswith("]") else ln[1:]
            if ln.upper().replace(" ", "") == "TYPE=MAPITEM" and section and len(items) < 1000:
                items.append(section)
        return sorted(items, key=str.lower)

    def admin_places(self):
        """[[group, label, where]] for Go to: the world map's names, then every named tile, person and thing (Id=).
        where is a place ID or "map tx ty"."""
        from dragonsword import ini
        d = self.data
        out = []
        for sec, items in ini.sections(d.data_file("WorldMap.ini")):
            if sec in ("Towns", "Regions", "Places"):
                out += [["On the world map", k, trim(v)] for k, v in items if k]
        groups = {"TILE": "Places", "NPC": "People"}
        for pl in sorted(d.places().values(), key=lambda pl: (groups.get(pl.kind, "Things"), pl.name.lower())):
            out.append([groups.get(pl.kind, "Things"), "%s (%s)" % (pl.name, pl.map), pl.name])
        return out

    def admin_command(self, msg):
        from dragonsword import ini
        what = msg.get("do")
        d = self.data
        if what == "items":
            self.emit({"t": "admin_items", "items": self.admin_items()})
        elif what == "places":
            self.emit({"t": "admin_places", "places": self.admin_places()})
        elif what == "commands":
            from dragonsword import script_language as L
            self.emit({"t": "admin_commands", "commands": [[n, a, L.help_for(n).replace("|", " "),
                                                             [L.help_for(t).replace("|", " ") for t in a]]
                                                            for n, a in L.commands().items()]})
        elif what == "script":
            # (any script command, run now as a script of one line: the same as a script file's)
            from dragonsword import script_language as L
            cmd = str(msg.get("command", ""))
            kinds = L.commands().get(cmd)
            if kinds is None:
                self.emit({"t": "admin_status", "text": "Pick a command first."})
                return
            args = [str(a).replace("\t", " ").strip() or " " for a in list(msg.get("args", []))[:len(kinds)]]
            line = "\t".join(["01", cmd] + args).rstrip()
            if not self.run_script_lines("(admin) " + cmd, [line, "02\tEnd"]):
                self.emit({"t": "admin_status", "text": "A script is running: try again when it's done."})
                return
            self.emit({"t": "admin_status", "text": "Ran %s." % " | ".join([cmd] + [a.strip() for a in args])})
        elif what == "give":
            item = str(msg.get("item", ""))
            if item not in self.admin_items():
                self.emit({"t": "admin_status", "text": "Pick an item first."})
                return
            qty = max(1, min(100000, int(val(msg.get("qty", 1)))))
            room = self.inventory_slots_available(item)
            if room <= 0:
                self.emit({"t": "admin_status", "text": "No room in the inventory for that."})
                return
            qty = min(qty, room)
            self.add_inventory_item(item, qty)
            self.play_sound("Pickup")
            self.emit({"t": "admin_status", "text": "Gave you %d %s." % (qty, pretty(item))})
        elif what == "skills":
            off = []
            ticks = msg.get("on", [])
            levels = msg.get("levels", [])
            for k in range(1, d.total_skills + 1):
                on = bool(ticks[k - 1]) if k - 1 < len(ticks) else True
                if not on and d.skill_name[k].upper() != "HITPOINTS":
                    off.append(d.skill_name[k])
                level = int(val(levels[k - 1])) if k - 1 < len(levels) else 0
                if level >= 1 and level != self.level_of_xp(self.skill_xp[k]):
                    self.skill_xp[k] = min(d.skill_max_level, level)
            ini.write("Skills", "Disabled", ",".join(off), d.config_path)
            for s in self.w.sessions.values():
                s.read_disabled_skills()
                s.dirty_me = True
            self.update_max_hp()
            self.check_locks(True)
            self.save_requested = True
            self.emit({"t": "admin_status", "text": "Saved." if not off else "Saved. Off: " + ",".join(off)})
        elif what == "goto":
            # (a named place: an Id tile or a thing's Id=, e.g. Ashford_Market, Waystone_Highwatch, The_Green_Dragon;
            # or "map tx ty", as the world map's labels have: 1,1,0 13 15)
            where = str(msg.get("place", "")).strip()
            pl = d.place(where)
            spot = (pl.map, pl.tx, pl.ty, pl.name) if pl is not None else None
            if spot is None and len(where.split()) == 3:
                mp, tx, ty = where.split()
                spot = (mp, int(val(tx)), int(val(ty)), mp)
            if spot is None or self.w.map_named(spot[0]) is None:
                self.emit({"t": "admin_status", "text": "No place called that (an Id on a map: e.g. Ashford_Market)."})
                return
            self.teleport(spot[0], (spot[1] - 1) * self.tw, spot[2] * self.th - 8)
            self.emit({"t": "admin_status", "text": "Off to %s (%s)." % (spot[3], spot[0])})
        elif what == "wave":
            name = str(msg.get("name", "")).strip()
            if name not in self.w.waves.defs:
                self.emit({"t": "admin_status", "text": "No such attack. data\\Waves.ini has: %s." %
                           ", ".join(sorted(self.w.waves.defs))})
            elif self.w.waves.start(name, by=self):
                self.emit({"t": "admin_status", "text": "%s has begun." % name})
            else:
                self.emit({"t": "admin_status", "text": "%s is on already." % name})
        elif what == "god":
            self.god_mode = 1 if msg.get("on") else 0
            ini.write("Admin", "GodMode", lbstr(self.god_mode), d.config_path)
            if self.god_mode:
                self.player.hp = self.player_max_hp
                self.display_message("God mode is on: nothing can hurt you.", "INFO")
            else:
                self.display_message("God mode is off.", "INFO")
            self.dirty_me = True
