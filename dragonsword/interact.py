"""Mouse and keyboard, verbs and actions (left-click = the first verb, right-click = the verb menu, walk then act),
item racks (shops, crafting), the bank and equipment."""
import math
import os

import pygame

from . import ini
from .entity import (Entity, PLAYER, TILE, MAPITEM, STATICOBJECT, NPC, MISSILE, TEMPORARY, INFRONTTILE,
                     ROOF, ACTIONBOX, ACTIONBOXITEM, INVENTORYITEM, QUANTITYDIGIT, TYPE_NAMES)
from .lb import val, word, trim, lbstr, distance, strip_digits, pretty
from .cursor import kind_of_verb


class InteractMixin:
    # =================================================================================================================
    # Keyboard
    # =================================================================================================================
    def key_hit(self, key):
        return key in self.keys_hit

    def key_pressed(self, key):
        return self.keys_down[key] if self.keys_down is not None else False

    def detect_keyboard_input(self):
        if self.key_hit(pygame.K_ESCAPE):
            if self.rcm_open:
                self.close_right_click_menu()
                return
            if self.item_in_use is not None:
                self.item_in_use = None
                return
            if self.ab_mode:
                self.close_action_box(-1)
                return
            if self.infobox_open:
                self.hide_infobox()
                return
            self.open_quit_dialog()
            return
        if self.key_hit(pygame.K_h) or self.key_hit(pygame.K_F1):
            self.open_help()
            return
        # Zoom: + and - (or the mouse wheel over the playfield)
        if self.key_hit(pygame.K_EQUALS) or self.key_hit(pygame.K_PLUS) or self.key_hit(pygame.K_KP_PLUS):
            if not self.ab_mode:
                self.change_zoom(1)
        if self.key_hit(pygame.K_MINUS) or self.key_hit(pygame.K_KP_MINUS):
            if not self.ab_mode:
                self.change_zoom(-1)
        if self.scroll_wheel():
            pass  # The wheel scrolled the chat or a shop, bank or crafting list
        elif self.mouse_wheel and 0 <= self.cursor_x < self.view_w and 0 <= self.cursor_y < self.view_h and not self.ab_mode:
            over_admin = self.admin_open and self.admin_layout()["panel"].collidepoint(self.cursor_x, self.cursor_y)
            if not over_admin:
                self.change_zoom(1 if self.mouse_wheel > 0 else -1)
        if self.debug_mode:
            if self.key_hit(pygame.K_m):
                self.add_map_item("Axe", self.cursor_world_x, self.cursor_world_y, 1)
                self.display_message("Added Map Item", "%d %d %d" % tuple(int(self.rand() * 255) for _ in range(3)))
            if self.key_hit(pygame.K_i):
                self.show_infobox("Title", "blue", "Hello", "red")
            if self.key_hit(pygame.K_v):
                self.add_inventory_item("Full_Vial", 2)
            if self.key_hit(pygame.K_u):
                self.responses = ["Good thanks!", "I'm ok...", "Awful."]
                self.response_actions = ["", "", ""]
                self.ab_image = "Baker"
                self.ab_title = "Bank"
                self.ab_text = "Hello!|How are you today?"
                self.ab_item_defs = []
                self.show_action_box("Bank")
            if self.key_hit(pygame.K_j):
                self.hide_action_box()
        if not self.user_input_enabled or self.ab_mode:
            return
        for n, key in enumerate((pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)):
            if self.key_hit(key) or self.key_hit(pygame.K_KP1 + n):
                self.hotbar_use(n)                     # the hotbar's slots
        k = self.key_pressed
        d = 0
        if k(pygame.K_UP) or k(pygame.K_w):
            d += 1
        if k(pygame.K_RIGHT) or k(pygame.K_d):
            d += 2
        if k(pygame.K_DOWN) or k(pygame.K_s):
            d += 4
        if k(pygame.K_LEFT) or k(pygame.K_a):
            d += 8
        if d & 5 == 5:
            d -= 5
        if d & 10 == 10:
            d -= 10
        self.keyboard_direction = d

    # =================================================================================================================
    # The mouse: what is under it (and the hover text)
    # =================================================================================================================
    def detect_mouse_movement(self):
        self.option_selected = set()
        msg = ""
        self.skill_mouseover = 0
        cx, cy = self.cursor_x, self.cursor_y
        self.cursor_world_x, self.cursor_world_y = self.screen_to_world(cx, cy)
        sel = self.option_selected
        dx = self.ui_dx  # The sidebar and the chat bar's arrows sit at the right-hand end of a wider window
        if 1000 + dx <= cx <= 1020 + dx and 5 <= cy <= 25:
            msg = "Exit Game"
            sel.add(1)
        if 872 + dx <= cx <= 888 + dx and 147 <= cy <= 162:
            msg = "Zoom Out"
            sel.add(2)
        if 988 + dx <= cx <= 1000 + dx and 147 <= cy <= 162:
            msg = "Zoom In"
            sel.add(3)
        if self.help_button_under_cursor():
            msg = "Journal and help (H)"
            sel.add(6)
        self.help_button_hot = 6 in sel
        if msg == "" and self.day_night_enabled and self.clock_rect().collidepoint(cx, cy):
            msg = self.time_text()
        if self.admin_enabled:
            if self.admin_button_under_cursor():
                msg = "Admin panel|give items, set skills"
                sel.add(9)
            self.admin_button_hot = 9 in sel
        if 780 + dx <= cx <= 794 + dx and 676 <= cy <= 690:
            if self.chat_line + 4 < len(self.message_log):
                msg = "Scroll Up"
                sel.add(4)
            else:
                msg = "<No More>"
        if 780 + dx <= cx <= 794 + dx and 750 <= cy <= 764:
            if self.chat_line == 1:
                msg = "<No More>"
            else:
                msg = "Scroll Down"
                sel.add(5)
        # StatBox tabs (Stats / Gear / Quests) and, on the Equipment tab, the slots
        was_over = self.equip_mouseover
        self.equip_mouseover = 0
        self.quest_arrow = 0
        smx = cx - self.view_w
        smy = cy - self.statbar_y
        if msg == "" and 31 <= smx <= 194 and 15 <= smy <= 36:
            if smx <= 81:
                msg = "Stats|your skills"
                sel.add(7)
            if 84 <= smx <= 135:
                msg = "Equipment|what you are wearing"
                sel.add(8)
            if smx >= 138:
                msg = "Quest log|quests in progress, to start and done"
                sel.add(10)
        quest_hover = 0
        if msg == "" and self.stats_view == 2:
            if 30 <= smx <= 194 and self.quest_row_top <= smy < self.quest_row_top + self.quests_per_page * self.quest_row_height:
                row = int((smy - self.quest_row_top) / self.quest_row_height) + 1
                k = (self.quests_page - 1) * self.quests_per_page + row
                if k <= len(self.help_quests):
                    quest_hover = row
                    msg = "Click to see it in the journal"
            if self.quests_pages > 1 and 41 <= smy <= 55:
                if 146 <= smx <= 160 and self.quests_page > 1:
                    msg = "Previous page"
                    self.quest_arrow = -1
                if 182 <= smx <= 196 and self.quests_page < self.quests_pages:
                    msg = "Next page"
                    self.quest_arrow = 1
        if quest_hover != self.quest_mouseover:
            self.quest_mouseover = quest_hover
            if self.stats_view == 2:
                self.stats_dirty = True
        if msg == "" and self.stats_view == 1:
            for s in range(1, self.equip_slots + 1):
                x, y = self.equip_slot_x(s), self.equip_slot_y(s)
                if x <= smx < x + self.EQUIP_BOX and y <= smy < y + self.EQUIP_BOX:
                    self.equip_mouseover = s
                    msg = self.equip_slot_info(s)
        if self.equip_mouseover != was_over and self.stats_view == 1:
            self.stats_dirty = True                 # (the slot under the mouse lights up)
        vw = self.view_w
        k = self.stat_tile_at(cx - vw, cy - self.statbar_y) if msg == "" and self.stats_view == 0 else -1
        if k >= 0:
            if k == 0:
                msg = "%d / %d hitpoints" % (self.player.hp, self.player_max_hp)
            if k == 1:
                msg = "%d / %d mana" % (int(self.player_mana), self.player_max_mana)
            if k >= 2:
                self.skill_mouseover = self.skill_of_row(k - 1)
                if self.skill_mouseover > 0:
                    msg = self.skill_info(self.skill_mouseover, False)
        if self.infobox_open:
            if self.infobox_x + 125 <= cx <= self.infobox_x + 140 and self.infobox_y + 45 <= cy <= self.infobox_y + 60:
                msg = "Close Information"
        if self.ab_mode:
            self.response_mouseover = 0
            ax, ay = self.ab_x, self.ab_y
            if ax + 430 <= cx <= ax + 450 and ay + 10 <= cy <= ay + 25:
                msg = "Close"
            if self.action_box_arrow() == -1:
                msg = "Previous page"
            if self.action_box_arrow() == 1:
                msg = "Next page"
            rx, ry = self.rb_x, self.rb_y
            box_h = self.rb_surface.get_height() if self.rb_surface is not None else self.assets.picture_height("ResponseBox", 112)
            if rx + 20 <= cx <= rx + self.assets.width("ResponseBox") - 20 and ry <= cy <= ry + box_h:
                if ry + 7 < cy < ry + (len(self.responses) + 1) * 16:
                    self.response_mouseover = int((cy - ry - 7) / 16) + 1
            if self.response_mouseover > len(self.responses):
                self.response_mouseover = 0
            self.show_response_box(self.response_mouseover)
            if self.response_mouseover:
                msg = self.responses[self.response_mouseover - 1]
        if self.rcm_open:
            row = 0
            if (self.rcm_x <= cx <= self.rcm_x + self.rcm_w and self.rcm_y + self.rcm_row_top <= cy <
                    self.rcm_y + self.rcm_row_top + len(self.rcm_verbs) * self.rcm_row_height):
                row = int((cy - self.rcm_y - self.rcm_row_top) / self.rcm_row_height) + 1
            if row != self.rcm_highlight:
                self.rcm_highlight = row
            if self.rcm_highlight > 0:
                msg = self.rcm_labels[self.rcm_highlight - 1]
                self.cursor_kind = kind_of_verb(self.rcm_verbs[self.rcm_highlight - 1])
            self.display_quick_message(msg, "ENTITY")
            return
        self.hotbar_hover = self.hotbar_slot_at(cx, cy) if msg == "" and not self.rcm_open else -1
        if self.hotbar_hover >= 0:
            self.cursor_kind = "pointer"
            self.display_quick_message(self.hotbar_label(self.hotbar_hover), "INTERFACE")
            self.cursor_ent = None
            return
        self.cursor_ent = self.entity_under_cursor()
        mtype = "INTERFACE"
        if msg == "":
            mtype = "ENTITY"
            e = self.cursor_ent
            in_world = 0 <= self.cursor_x < self.view_w and 0 <= self.cursor_y < self.view_h and not self.ab_mode
            self.cursor_kind = "walk" if in_world and self.user_input_enabled else "pointer"
            if self.item_in_use is not None:
                self.cursor_kind = "target"
                if e is not None and e is not self.item_in_use:
                    msg = "Use %s with %s" % (self.display_name(self.item_in_use), self.display_name(e))
                else:
                    msg = "Use %s with ..." % self.display_name(self.item_in_use)
            elif e is not None:
                default = word(self.get_verbs(e), 1, ",")
                if default and default != "Walk here":
                    self.cursor_kind = kind_of_verb(default)
                if default == "Walk here":
                    if val(e.misc) == 1:
                        msg = self.display_name(e)
                else:
                    if default:
                        msg = self.verb_label(default, e)
                    if e.type == INVENTORYITEM:
                        spell = self.entity_ini(e.name, "Spell", "")
                        if spell and not self.spell_is_potion(spell):
                            msg += "|" + self.spell_status(spell)
                        if self.ab_mode == "Shop" and not self.can_sell_here(e.name):
                            msg = self.display_name(e) + "|Can't be sold here"
        self.display_quick_message(msg, mtype)

    def entity_under_cursor(self):
        """The front-most entity under the cursor that can be interacted with (None = none)."""
        cx, cy = self.cursor_x, self.cursor_y
        if cx < 0 or cy < 0 or cy >= self.view_h or cx > self.win_w:
            return None
        for rect, e in reversed(self.pick_list):  # The interface (screen pixels), over the world
            if rect.collidepoint(cx, cy):
                if e is None:  # The ActionBox: nothing behind it can be clicked
                    return None
                if cx >= self.view_w and e.type != INVENTORYITEM:
                    return None
                return e
        if cx >= self.view_w or self.ab_mode:
            return None                 # (a conversation, shop, bank or crafting box is open: the world is paused)
        wx = int(cx / self.zoom)
        wy = int(cy / self.zoom)
        for rect, e in reversed(self.pick_world):  # The world (world canvas pixels: the zoom)
            if rect.collidepoint(wx, wy):
                return e
        if cx < self.view_w:
            return self.ground_tile_at(self.cursor_world_x, self.cursor_world_y)
        return None

    # =================================================================================================================
    # The mouse: clicks
    # =================================================================================================================
    def detect_mouse_input(self):
        left, right = self.mouse_left_click, self.mouse_right_click
        if not left and not right:
            return
        if left and not self.rcm_open and self.scroll_bar_click():
            return
        sel = self.option_selected
        if left:
            if 1 in sel:
                self.open_quit_dialog()
                return
            if 2 in sel:
                self.change_minimap_zoom(0.5)
                return
            if 3 in sel:
                self.change_minimap_zoom(2)
                return
            if 4 in sel:
                self.scroll_message_display(1)
                return
            if 5 in sel:
                self.scroll_message_display(-1)
                return
            if 6 in sel:
                self.open_help()
                return
            if 9 in sel:
                self.open_admin()
                return
            if 7 in sel:
                self.set_stats_view(0)
                return
            if 8 in sel:
                self.set_stats_view(1)
                return
            if 10 in sel:
                self.set_stats_view(2)
                return
        if getattr(self, "hotbar_hover", -1) >= 0 and not self.rcm_open:
            if left:
                self.hotbar_use(self.hotbar_hover)
            else:
                self.hotbar_remove(self.hotbar_hover)
            return
        if self.rcm_open:
            if left and self.rcm_highlight > 0:
                verb = self.rcm_verbs[self.rcm_highlight - 1]
                target = self.rcm_target
                self.close_right_click_menu()
                self.verb_from_menu = True
                if verb == "Use with":
                    self.choose_verb("Use with", target)
                elif verb != "Cancel":
                    self.item_in_use = None
                    self.choose_verb(verb, target)
            else:
                self.close_right_click_menu()
            return
        if self.infobox_open:
            self.hide_infobox()
            return
        if self.ab_mode and left:
            ax, ay = self.ab_x, self.ab_y
            if ax + 430 <= self.cursor_x <= ax + 450 and ay + 10 <= self.cursor_y <= ay + 25:
                self.close_action_box(-1)
                return
            arrow = self.action_box_arrow()
            if arrow != 0:
                self.rack_page += arrow
                self.show_rack_page(False)
                return
            if 1 <= self.response_mouseover <= len(self.responses):
                self.action_box_response_chosen(self.response_mouseover)
                return
        if self.skill_mouseover > 0:
            if left:
                name = self.skill_name[self.skill_mouseover] + " Skill"
                if self.script_exists(name):
                    self.start_script(name, True)
            else:
                self.display_message(self.skill_info(self.skill_mouseover, True), "INFO")
            return
        if self.quest_arrow != 0:
            self.quests_page += self.quest_arrow
            self.quest_mouseover = 0
            self.draw_quests(False)
            return
        if self.quest_mouseover > 0:
            k = (self.quests_page - 1) * self.quests_per_page + self.quest_mouseover
            if left:
                self.help_tab = 3
                self.open_help()
                if k <= len(self.help_quests):
                    self.help_focus_quest = self.help_quests[self.help_quest_order[k - 1]]["title"]
                    self.help_page = min(self.help_pages(), (k - 1) // 7 + 1)
            else:
                if k <= len(self.help_quests):
                    q = self.help_quests[self.help_quest_order[k - 1]]
                    self.display_message("%s: %s" % (q["title"], q["text"]), "INFO")
            return
        if self.equip_mouseover > 0:
            if left:
                self.unequip_slot(self.equip_mouseover)
            else:
                self.display_message(self.equip_slot_info(self.equip_mouseover), "INFO")
            return
        if not self.user_input_enabled:
            return
        clicked = self.cursor_ent
        if clicked is not None and clicked is self.hover_tile and getattr(clicked, "off_map", False):
            clicked = None              # a tile on the next map: named on hover, but a click just walks there
        if right:
            if self.item_in_use is not None:
                self.item_in_use = None
                return
            if self.ab_mode and clicked is None:
                return                  # no menu for the (paused) world while a box is open
            self.open_right_click_menu(clicked)
            return
        if self.item_in_use is not None:
            if clicked is None or clicked is self.item_in_use:
                self.item_in_use = None
            else:
                self.choose_verb("Use with", clicked)
            return
        if clicked is None:
            if 0 <= self.cursor_x < self.view_w and 0 <= self.cursor_y < self.view_h and not self.ab_mode:
                self.choose_verb("Walk here", None)
            return
        verbs = self.get_verbs(clicked)
        if verbs:
            self.choose_verb(word(verbs, 1, ","), clicked)

    # =================================================================================================================
    # Verbs
    # =================================================================================================================
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

    # tiles you walk up to rather than look at, though they block the way: walls, woods, hedges, water
    WALK_FIRST_WORDS = ("Wall", "Forest", "Hedge", "Pond", "Pool", "_Window", "Water", "Timber0", "Plaster0", "Sandstone0",
                        "Brick0")

    def examine_first(self, e):
        """A thing on the map (its name shown, something to read when examined) that you can't walk all over: a left
        click examines it instead of walking there. Walls, woods, hedges and water still walk."""
        if val(e.misc) != 1 or self.examine_text(e) == "" or any(w in e.name for w in self.WALK_FIRST_WORDS):
            return False
        return "0" in self.tile_ini(e.name, "Walkable.Data", self.all_walkable)

    def get_verbs(self, e):
        """Comma list of verbs for the right-click menu. The first one is the left-click action."""
        if e is None or not e.alive:
            return ""
        t = e.type
        uw = e.use_words
        verbs = ""
        if t in (TILE, INFRONTTILE):
            verbs = self.add_verbs(verbs, uw)
            if self.tile_lock_of(e) > 0:              # a locked door: Open (its lock's message) and Unlock (a script)
                verbs = self.add_verb(verbs, "Open")
                verbs = self.add_verb(verbs, "Unlock")
            if verbs == "" and self.examine_first(e):
                verbs = "Examine"               # a crate, a statue, a grave...: a left click looks at it
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
                verbs = self.add_verbs(verbs, uw)
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
        elif t == NPC and e.hostile:            # a foe: Attack first (the left click), then whatever else it has
            verbs = self.add_verb(verbs, "Attack")
            verbs = self.add_verbs(verbs, uw)
            verbs = self.add_verb(verbs, "Examine")
        elif t == NPC:                          # a friend: its own words (not Attack), and Talk to
            for i in range(1, 30):
                v = trim(word(uw, i, ","))
                if v == "":
                    break
                if v.upper() != "ATTACK":
                    verbs = self.add_verb(verbs, v)
            verbs = self.add_verb(verbs, "Talk to")
            verbs = self.add_verb(verbs, "Examine")
        if self.item_in_use is not None and e is not self.item_in_use and self.ab_mode == "":
            verbs = "Use with," + verbs
        return verbs

    def verb_label(self, verb, e):
        """e.g. "Attack Goblin (8/10)", "Buy Axe (6 gold)" """
        if e is None:
            return verb
        if verb in ("Walk here", "Cancel"):
            return verb
        if verb == "Use with":
            return "Use %s with %s" % (self.display_name(self.item_in_use), self.display_name(e))
        if verb == "Attack":
            return "Attack %s (%s/%s)" % (self.display_name(e), lbstr(e.hp), lbstr(e.max_hp))
        if verb in ("Buy 1", "Buy 5"):
            return "%s %s (%d gold)" % (verb, self.display_name(e), self.item_price(e.name, self.rack_buy_rate, 1))
        if verb in ("Sell 1", "Sell All"):
            n = 1 if verb == "Sell 1" else max(1, self.items_held(e.name))
            return "%s %s (%d gold)" % (verb, self.display_name(e), self.sell_price(e.name) * n)
        if verb == "Make" and self.rack_level_short(e):
            return "Make %s (needs %s level %d)" % (self.display_name(e), self.rack_skill, self.rack_level_short(e))
        if verb == "Make" and self.rack_missing(e):
            return "Make %s (not enough %s)" % (self.display_name(e), self.rack_missing(e))
        if verb == "Pickup":
            return "Pick up " + self.display_name(e)
        if verb == "Hotbar":
            return "Put %s on the hotbar" % self.display_name(e)
        if verb == "Off hotbar":
            return "Take %s off the hotbar" % self.display_name(e)
        if verb == "Use":
            if e.type == INVENTORYITEM:
                return "Use %s..." % self.display_name(e)
            return "Use " + self.display_name(e)
        return verb + " " + self.display_name(e)

    def verb_range(self, verb, e):
        """How close the player walks before doing verb (0 = no walking needed)."""
        if e is None or e.type in (INVENTORYITEM, ACTIONBOXITEM, PLAYER, QUANTITYDIGIT):
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
                    if self.spell_ini(spell, "Effect", "Bolt").upper() == "BOLT":
                        r = max(36, val(self.spell_ini(spell, "Range", "256")) - 16)
            return r
        return 26 if e.type in (TILE, INFRONTTILE) else 36

    def pick_tile(self, e):
        """Keeps the clicked tile (the hover tile follows the mouse)."""
        if e is not None and e is self.hover_tile:
            c = Entity(TILE, e.name)
            c.x, c.y, c.w, c.h = e.x, e.y, e.w, e.h
            c.misc, c.use_words = e.misc, e.use_words
            return c
        return e

    def choose_verb(self, verb, e):
        """The player picked verb on entity e: walk there if needed, then act."""
        vx, vy = self.screen_to_world(self.cursor_x, self.cursor_y)
        if self.verb_from_menu:
            vx, vy = self.rcm_world_x, self.rcm_world_y
        self.verb_from_menu = False
        e = self.pick_tile(e)
        self.clicked_ent = e
        self.script_cursor_x, self.script_cursor_y = vx, vy
        self.clicked_tile_x = self.tile_of_x(vx)
        self.clicked_tile_y = self.tile_of_y(vy)
        if verb in ("Cancel", ""):
            return
        if verb == "Walk here":
            self.player_attack_target = None
            lk = self.tile_locked[self.clicked_tile_x][self.clicked_tile_y]
            if lk > 0:
                self.display_message(self.lock_message(lk), "FAIL")
                return
            self.walk_player_to(vx, vy - int(self.player.h / 2) + 2, 0, 2)
            return
        if verb != "Attack":
            self.player_attack_target = None
        rng = self.verb_range(verb, e)
        if rng > 0 and self.player_distance_to(e) > rng:
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
        if verb == "Open" and t == TILE:
            lk = self.tile_lock_of(e)
            if lk > 0:
                self.display_message(self.lock_message(lk), "FAIL")
                return
        if t != ACTIONBOXITEM:
            script = self.find_action_script(verb, name, t, getattr(e, "npc_id", ""))
            if script:
                self.start_script(script, True)
                return
        if verb == "Examine":
            self.examine_entity(e)
        elif verb == "Pickup":
            self.pickup_map_item(e)
        elif verb in ("Drop", "Drop All"):
            self.drop_inventory_item(e, e.quantity)
        elif verb == "Drop 1":
            self.drop_inventory_item(e, 1)
        elif verb == "Eat":
            self.eat_inventory_item(e)
        elif verb in ("Wield", "Wear"):
            if t == INVENTORYITEM:
                self.equip_item(e)
            else:
                self.display_message("You can't wear that!", "FAIL")
        elif verb == "Open":
            n = self.tile_lock_of(e) if t == TILE else 0
            if n:
                self.display_message(self.lock_message(n), "FAIL")      # (still locked: what its lock says)
                self.play_sound("Locked")
            elif t == TILE and self.door_open_tile(name):
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
        elif verb in ("Drink", "Eat") and t == INVENTORYITEM and self.entity_ini(name, "Cures", ""):
            self.drink_cure(e)
        elif verb in ("Cast", "Drink"):
            if t == INVENTORYITEM and self.entity_ini(name, "Spell", ""):
                self.cast_scroll(e, None)
            else:
                self.display_message("Nothing interesting happens.", "FAIL")
        elif verb == "Use":
            if t == INVENTORYITEM:
                self.item_in_use = e
            else:
                self.display_message("Nothing interesting happens.", "FAIL")
        elif verb == "Talk to":
            self.display_message("They don't seem interested in talking.", "FAIL")
        elif verb == "Attack":
            self.start_attack(e)
        elif verb == "Sleep":                   # (a bed: through the night or the day, daynight.py)
            self.start_sleep("Next")
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

    def use_item_with(self, target):
        """Use <item in use> With <target>: "Use A With <target's Id>", "Use A With B", "Use B With A" (and without
        digits), then "[Type]"."""
        item = self.item_in_use
        self.item_in_use = None
        if item is None or target is None or not item.alive or not target.alive:
            return
        a, b = item.name, target.name
        base = strip_digits(b)
        tname = TYPE_NAMES.get(target.type, "")
        self.item_in_use_name = a
        self.clicked_ent = target
        if self.entity_ini(a, "Spell", "") and not self.script_exists("Use %s With %s" % (a, b)):
            self.cast_scroll(item, target)
            return
        script = ""
        tid = getattr(target, "npc_id", "")
        if tid and self.script_exists("Use %s With %s" % (a, tid)):    # the one thing with that Id first
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
            return                                              # (mending a worn weapon or armour: durability.py)
        if script == "":
            self.display_message("Nothing interesting happens.", "FAIL")
        else:
            self.start_script(script, True)

    def examine_text(self, e):
        if e.type in (TILE, INFRONTTILE, ROOF):
            t = self.tile_ini(e.name, "Examine.Info", "")
            if t == "":
                t = self.tile_ini(strip_digits(e.name), "Examine.Info", "")
            return t
        return self.entity_ini(e.name, "Examine.Info", "")

    def examine_entity(self, e):
        text = self.examine_text(e) or "It's not very interesting."
        if e.type == INVENTORYITEM and self.dur_text(e.name, getattr(e, "wear", 0)):
            text += " (Condition: %s)" % self.dur_text(e.name, getattr(e, "wear", 0))
        self.display_message(text, "EXAMINE")

    def pickup_map_item(self, e):
        if self.player_distance_to(e) > 40:
            self.display_message("You are too far away to reach that!", "FAIL")
            return
        name = e.name
        quantity = max(1, e.quantity)
        space = self.inventory_slots_available(name)
        if space <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        taken = min(quantity, space)
        if getattr(e, "once", False) and taken < quantity:      # a one-time item: all of it or none (it won't be back)
            self.display_message("You need room for all %d %s." % (quantity, pretty(name)), "FAIL")
            return
        self.add_inventory_item(name, taken, getattr(e, "wear", 0))
        self.play_sound("Pickup")
        if taken > 1:
            self.display_message("You pick up %d %s." % (taken, pretty(name)), "SUCCESS")
        else:
            self.display_message("You pick up the %s." % pretty(name), "SUCCESS")
        home = self.entity_home(e)
        coords = self.local_coords(home, e.x, e.y)
        if taken < quantity:
            e.quantity = quantity - taken
            self.display_message("You don't have room for the rest.", "FAIL")
            if e.source == "MAP":
                self.remove_action_from_queue("\t".join(["SET.QUANTITY", name, "MapItem", "*", home, coords, "*"]))
                self.add_action_to_queue("SET.QUANTITY", name, "MapItem", lbstr(quantity - taken), home, coords,
                                         self.item_respawn_seconds(name))
            else:
                self.set_queue_quantity("REMOVE", name, home, coords, quantity - taken)
            return
        if getattr(e, "once", False):                            # one-time: remembered, never respawns
            x, y = (int(float(v)) for v in coords.split(","))
            self.taken_once.add(e.npc_id if e.npc_id else "%s@%d,%d" % (home, x, y))
            self.remove_action_from_queue("\t".join(["REMOVE", name, "MapItem", "*", home, coords, "*"]))
        elif e.source == "MAP":
            self.remove_action_from_queue("\t".join(["SET.QUANTITY", name, "MapItem", "*", home, coords, "*"]))
            self.add_action_to_queue("ADD", name, "MapItem", lbstr(e.orig_quantity) + (
                " Id=" + e.npc_id if getattr(e, "npc_id", "") else ""), home, coords,
                                     self.item_respawn_seconds(name))
        else:
            self.remove_action_from_queue("\t".join(["REMOVE", name, "MapItem", "*", home, coords, "*"]))
        self.remove_entity(e)

    def item_respawn_seconds(self, name):
        """How long an item picked up off the map takes to come back: its Entities.ini Respawn= (seconds) if it has
        one, else Config [Gameplay] Item.Respawn.Delay scaled by what it's worth (1.5x for a worm, 8x for armour
        worth 200), at most 2 hours."""
        own = val(self.entity_ini(name, "Respawn", "0"))
        if own > 0:
            return own
        worth = max(0, val(self.entity_ini(name, "Value", "1")))
        return int(min(7200, self.item_respawn_delay * (1 + math.sqrt(worth) / 2)))

    def drop_inventory_item(self, e, quantity):
        name = e.name
        if val(self.entity_ini(name, "Droppable", "1")) == 0 or val(self.entity_ini(name, "Undroppable", "0")) == 1:
            self.display_message("You can't drop that!", "FAIL")
            return
        quantity = min(max(1, quantity), max(1, e.quantity))
        if self.item_max_dur(name) > 0 and quantity == 1:
            self.drop_on_floor(name, 1, self.take_inventory_entity(e))      # (it keeps its wear)
        else:
            self.remove_inventory_item(name, quantity)
            self.drop_on_floor(name, quantity)
        self.play_sound("Drop")
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
        new_map = self.make_map_name(self.map_x(), self.map_y(), self.map_z() + dz)
        if not self.map_exists(new_map):
            self.display_message("It leads nowhere!", "FAIL")
            return
        self.play_sound("Ladder")
        self.display_message("You climb up." if dz > 0 else "You climb down.", "SUCCESS")
        self.pending_map = new_map
        self.pending_x, self.pending_y = self.player.x, self.player.y
        self.pending_map_change = True

    # =================================================================================================================
    # Item racks (shop, craft) and the bank
    # =================================================================================================================
    def item_price(self, name, rate, minimum):
        price = int(val(self.entity_ini(name, "Value", "0")) * rate + 0.5)
        return max(price, minimum)

    def sell_price(self, name):
        """What this shop pays for one: Value x its Sell.Rate x Config [Gameplay] Sell.Price.Factor (shops pay far
        less than they charge), at least 1 gold for anything with a value."""
        return self.item_price(name, self.rack_sell_rate * self.sell_price_factor, 1)

    def can_sell_here(self, name):
        """Will the open shop buy this? Not gold, not worthless things, and a Specific shop only what it stocks."""
        if name == "Gold_Coin(s)" or val(self.entity_ini(name, "Value", "0")) <= 0:
            return False
        return not (self.rack_specific == 1 and not any(r["item"] == name for r in self.rack))

    def rack_level_short(self, e):
        """For a crafting rack's item: the skill level it needs that the player hasn't got (0 = none)."""
        if self.ab_mode != "Craft" or e is None or e.type != ACTIONBOXITEM or not self.rack_skill:
            return 0
        i = val(e.misc)
        if not isinstance(i, int) or i < 0 or i >= len(self.rack):
            return 0
        need = self.rack[i]["level"]
        return need if need > 0 and self.skill_level(self.rack_skill) < need else 0

    def rack_missing(self, e):
        """For a crafting rack's item: what the player hasn't enough of to make it ("" = they have it all)."""
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
        """Display.Item.Rack: BANK, or a Data\\ItemRacks.ini section (Type=Shop/Craft). True if shown."""
        f = os.path.join(self.root, "Data", "ItemRacks.ini")
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
                self.log("ERROR - Item rack '%s' not found in Data\\ItemRacks.ini" % rack)
                self.display_message("There's nothing here.", "FAIL")
                return False
        self.rack_name = rack
        self.rack = []
        self.rack_page = 1
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
        self.ab_image = self.npc_image(npc)
        self.ab_title = pretty(npc) or self.rack_type
        if npc in ("You", "Player"):
            self.ab_title = self.player_name
        self.show_rack_page(True)
        return True

    def npc_image(self, npc):
        if npc in ("You", "Player", self.player_name):
            npc = self.player_sprite_base
        if self.assets.loaded(npc + "4a") or self.assets.load_if_exists("Walk", npc + "4a"):
            return npc + "4a"
        if self.assets.loaded(npc):
            return npc
        return self.fallback_sprite()

    def apply_shop_queue(self):
        for entry in self.action_queue:
            parts = entry.split("\t")
            if len(parts) > 3 and parts[2] == self.rack_name:
                if parts[0] == "ADD.SHOP.ITEM":
                    self.change_rack_stock(parts[1], -val(parts[3]))
                elif parts[0] == "REMOVE.SHOP.ITEM":
                    self.change_rack_stock(parts[1], val(parts[3]))

    def change_rack_stock(self, item, change):
        for r in self.rack:
            if r["item"] == item:
                if r["quantity"] >= 0:
                    r["quantity"] = max(0, r["quantity"] + change)
                return
        if change > 0 and len(self.rack) < 200:
            self.rack.append({"item": item, "quantity": change, "info": "", "xp": 0, "level": 0})

    def show_rack_page(self, full_redraw):
        """Fills the ActionBox from the rack (or the bank) for the current page."""
        if self.rack_type == "Bank":
            visible = [i for i in range(1, self.bank_slots + 1) if self.bank_item[i]]
        else:
            visible = [i for i, r in enumerate(self.rack) if r["quantity"] != 0]
        page_size = max(1, self.ab_columns * self.ab_rows)
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
            self.refresh_action_box_items()

    def action_box_response_chosen(self, n):
        if self.ab_mode == "Conversation":
            self.close_action_box(n)
            return
        action = self.response_actions[n - 1] if n - 1 < len(self.response_actions) else ""
        if action == "NEXT":
            self.rack_page += 1
            self.show_rack_page(False)
        elif action == "PREV":
            self.rack_page -= 1
            self.show_rack_page(False)
        else:
            self.close_action_box(-1)

    def action_box_arrow(self):
        """The page arrows on the right of the item area: -1 = previous page, 1 = next page, 0 = not on one."""
        if self.ab_mode in ("", "Conversation"):
            return 0
        cx, cy = self.cursor_x, self.cursor_y
        if cx < self.ab_x + 406 or cx > self.ab_x + 424:
            return 0
        if self.ab_y + 43 <= cy <= self.ab_y + 59:
            return -1
        if self.ab_y + 145 <= cy <= self.ab_y + 161:
            return 1
        return 0

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
            self.display_message("You don't have enough gold!", "FAIL")
            return
        quantity = min(quantity, self.inventory_slots_available(item))
        if quantity <= 0:
            self.display_message("You don't have enough room in your inventory!", "FAIL")
            return
        self.remove_inventory_item("Gold_Coin(s)", price * quantity)
        self.add_inventory_item(item, quantity)
        if r["quantity"] >= 0:
            r["quantity"] -= quantity
            self.add_action_to_queue("ADD.SHOP.ITEM", item, self.rack_name, lbstr(quantity), "-", "0,0",
                                     self.shop_restock_seconds(item))
        self.display_message("You buy (%d) %s for %d gold." % (quantity, pretty(item), price * quantity), "SUCCESS")
        self.play_sound("Coins")
        self.show_rack_page(False)

    def shop_restock_seconds(self, item):
        return int(self.shop_restock_delay * min(4, 1 + val(self.entity_ini(item, "Value", "0")) / 100))

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
        self.remove_inventory_item(item, quantity)
        if price > 0:
            self.add_inventory_item("Gold_Coin(s)", price * quantity)
        self.change_rack_stock(item, quantity)
        self.add_action_to_queue("REMOVE.SHOP.ITEM", item, self.rack_name, lbstr(quantity), "-", "0,0",
                                 self.shop_restock_seconds(item))
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
        for i in range(1, self.bank_slots + 1):
            if self.bank_item[i] == item:
                return self.bank_qty[i]
        return 0

    def bank_deposit(self, e, quantity):
        item = e.name
        quantity = min(max(1, quantity), self.items_held(item))
        slot = 0
        for i in range(1, self.bank_slots + 1):
            if self.bank_item[i] == item:
                slot = i
                break
        if slot == 0:
            for i in range(1, self.bank_slots + 1):
                if self.bank_item[i] == "":
                    slot = i
                    break
        if slot == 0:
            self.display_message("There is no more room in your bank!", "FAIL")
            return
        self.bank_item[slot] = item
        self.bank_qty[slot] += quantity
        if self.item_max_dur(item) > 0:
            self.bank_wear[slot] += self.wears_of(item, quantity)          # (each keeps its wear)
        self.remove_inventory_item(item, quantity)
        self.display_message("You bank (%d) %s." % (quantity, pretty(item)), "SUCCESS")
        self.show_rack_page(False)

    def bank_withdraw(self, e, quantity):
        slot = val(e.misc)
        if slot < 1 or slot > self.bank_slots:
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
        if self.item_max_dur(item) > 0:
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
        if r["level"] > 0 and self.rack_skill:
            if self.skill_level(self.rack_skill) < r["level"]:
                self.display_message("You need level %s %s to make that!" % (lbstr(r["level"]), self.rack_skill), "FAIL")
                return
        ingredients = r["info"]
        j = 1
        while word(ingredients, j) != "":
            if self.items_held(word(ingredients, j)) < max(1, val(word(ingredients, j + 1))):
                self.display_message("You need %s to make %s!" % (self.ingredients_text(ingredients), pretty(r["item"])),
                                     "FAIL")
                return
            j += 2
        j = 1
        while word(ingredients, j) != "":
            self.remove_inventory_item(word(ingredients, j), max(1, val(word(ingredients, j + 1))))
            j += 2
        self.add_inventory_item(r["item"], r["quantity"])
        self.display_message("You make (%s) %s." % (lbstr(r["quantity"]), pretty(r["item"])), "SUCCESS")
        self.play_sound(self.craft_sound())
        if self.rack_skill and r["xp"] != 0:
            self.update_skill(self.rack_skill, "+" + lbstr(r["xp"]))

    def craft_sound(self):
        s = self.rack_skill.upper()
        if s == "SMITHING":
            return "Smelt" if "SMELT" in self.rack_name.upper() else "Anvil"
        return {"HERBLORE": "Brew", "COOKING": "CookingFood", "MAGIC": "SpellCast"}.get(s, "Craft")

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
    # Equipment: equipped[slot] for the slots Weapon, Shield, Head, Body, Legs, Feet, Hands, Ring
    # =================================================================================================================
    def equip_slot_index(self, slot):
        s = trim(slot).upper()
        for i in range(1, self.equip_slots + 1):
            if self.equip_slot_names[i].upper() == s:
                return i
        return 0

    def item_equip_slot(self, item):
        if not item:
            return 0
        return self.equip_slot_index(self.entity_ini(item, "Slot", ""))

    def equip_verb(self, item):
        s = self.item_equip_slot(item)
        if s == 0:
            return ""
        return "Wield" if self.equip_slot_names[s].upper() in ("WEAPON", "SHIELD") else "Wear"

    def item_bonus(self, item, key):
        if not item:
            return 0
        return val(self.entity_ini(item, key, "0"))

    def items_equipped(self, item):
        if not item:
            return 0
        return sum(1 for i in range(1, self.equip_slots + 1) if self.equipped[i] == item)

    def recalc_equipment(self):
        self.equip_attack_total = self.equip_defence_total = self.equip_magic_total = 0
        for i in range(1, self.equip_slots + 1):
            it = self.equipped[i]
            if it and not self.is_broken(it, self.equip_wear[i]):           # (broken: no use till it's mended)
                self.equip_attack_total += self.item_bonus(it, "Attack")
                self.equip_defence_total += self.item_bonus(it, "Defence")
                self.equip_magic_total += self.item_bonus(it, "Magic")

    def equip_requirement(self, item):
        """What the player lacks to equip item, e.g. "level 5 Strength" ("" = nothing)."""
        req = trim(self.entity_ini(item, "Requires", "").replace(",", " "))
        k = 1
        while word(req, k) != "":
            skill = word(req, k)
            level = val(word(req, k + 1))
            if level > 0 and self.skill_level(skill) < level:
                return "level %s %s" % (lbstr(level), skill)
            k += 2
        return ""

    def equip_item(self, e):
        item = e.name
        s = self.item_equip_slot(item)
        if s == 0:
            self.display_message("You can't wear that!", "FAIL")
            return
        verb = self.equip_verb(item).lower()
        need = self.equip_requirement(item)
        if need:
            self.display_message("You need %s to %s the %s." % (need, verb, pretty(item)), "FAIL")
            return
        old = self.equipped[s]
        if old:
            room = self.inventory_slots_available(old)
            if e.quantity <= 1:
                room += 1
            if room < 1:
                self.display_message("You need room in your inventory to take off the %s." % pretty(old), "FAIL")
                return
        wear = self.take_inventory_entity(e)            # (this very one, and how worn it is)
        old_wear = self.equip_wear[s]
        self.equipped[s] = item
        self.equip_wear[s] = wear
        if old:
            self.add_inventory_item(old, 1, old_wear)
        self.display_message("You %s the %s." % (verb, pretty(item)), "SUCCESS")
        self.equipment_changed()

    def unequip_slot(self, s):
        if s < 1 or s > self.equip_slots:
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
        if self.stats_view == 1:
            self.stats_dirty = True
        self.check_locks(True)

    def equip_slot_info(self, s):
        item = self.equipped[s]
        if not item:
            return self.equip_slot_names[s] + " (empty)"
        info = "%s (%s): Attack +%s, Defence +%s" % (pretty(item), self.equip_slot_names[s],
                                                    lbstr(self.item_bonus(item, "Attack")),
                                                    lbstr(self.item_bonus(item, "Defence")))
        if self.item_bonus(item, "Magic") != 0:
            info += ", Magic +" + lbstr(self.item_bonus(item, "Magic"))
        if self.dur_text(item, self.equip_wear[s]):
            info += ". Condition: " + self.dur_text(item, self.equip_wear[s])
        return info + ". Click to take it off."

    # The Gear tab is laid out like a body: head on top, weapon / body / shield across, hands / legs / ring below,
    # feet at the bottom. Slots 1-8: Weapon Shield Head Body Legs Feet Hands Ring -> (column, row)
    EQUIP_GRID = ((0, 1), (2, 1), (1, 0), (1, 1), (1, 2), (1, 3), (0, 2), (2, 2))
    EQUIP_BOX = 28          # (four rows between the tabs and the panel's bottom edge, y 41-166)

    @classmethod
    def equip_slot_x(cls, s):
        return 49 + cls.EQUIP_GRID[s - 1][0] * 50

    @classmethod
    def equip_slot_y(cls, s):
        return 41 + cls.EQUIP_GRID[s - 1][1] * 32

    def check_saved_equipment(self, path):
        """After loading a save: an item in a slot that no longer exists (Neck) or isn't worn there any more goes back."""
        if not path:
            return
        old = trim(ini.read("Equipment", "Neck", "", path))
        if old:
            self.unequip_to_inventory(old)
        for i in range(1, self.equip_slots + 1):
            item = self.equipped[i]
            if item and self.item_equip_slot(item) != i:
                self.equipped[i] = ""
                self.unequip_to_inventory(item)

    def unequip_to_inventory(self, item):
        if self.inventory_slots_available(item) >= 1:
            self.add_inventory_item(item, 1)
            self.log("Save: %s can't be worn any more, put back in the inventory" % item)
            return
        for i in range(1, self.bank_slots + 1):
            if self.bank_item[i] == item:
                self.bank_qty[i] += 1
                self.log("Save: %s put in the bank" % item)
                return
        for i in range(1, self.bank_slots + 1):
            if self.bank_item[i] == "":
                self.bank_item[i] = item
                self.bank_qty[i] = 1
                self.log("Save: %s put in the bank" % item)
                return
        self.log("WARNING - Save: no room anywhere for %s (it was worn in a slot that no longer exists)" % item)
