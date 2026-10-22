"""The script engine (Data\\Scripts\\*.txt; the commands are in script_language.py), conditions,
script variables, attributes and the action queue. Scripts run a few lines per game loop so waits, conversations, item
racks and Move.* never freeze the game."""
import os

from . import ini
from .entity import (MAPITEM, NPC, TILE, TYPE_NAMES, normalise_type, attitude_of_type, parse_attitude)
from .lb import (val, word, field, trim, lbstr, distance, random_number, rnd, is_number, parse_quantity, apply_change,
                 safe_eval, wildcard_match, strip_digits, wrap_text, clock_seconds, seconds_today, pretty)


class ScriptMixin:
    # =================================================================================================================
    # Running scripts
    # =================================================================================================================
    def script_path(self, name):
        return os.path.join(self.root, "Data", "Scripts", name + ".txt")

    def script_exists(self, name):
        """An empty script file counts as not found."""
        if not name:
            return False
        try:
            return os.path.getsize(self.script_path(name)) > 0
        except OSError:
            return False

    def find_action_script(self, verb, name, etype, ent_id=""):
        """Script lookup: "Verb Id" (anything placed with an Id= on its map line, e.g. Pickup CellarKey, Read Ashford,
        Talk to OldHob), then "Verb Name", "Verb Name-without-digits", "Verb [Type]"."""
        if ent_id and self.script_exists("%s %s" % (verb, ent_id)):
            return "%s %s" % (verb, ent_id)
        if self.script_exists(verb + " " + name):
            return verb + " " + name
        if strip_digits(name) != name and self.script_exists(verb + " " + strip_digits(name)):
            return verb + " " + strip_digits(name)
        if etype > 0 and self.script_exists("%s [%s]" % (verb, TYPE_NAMES.get(etype, ""))):
            return "%s [%s]" % (verb, TYPE_NAMES.get(etype, ""))
        return ""

    def start_script(self, name, user_initiated):
        name = trim(name)
        if name.lower().endswith(".txt"):
            name = name[:-4]
        if name == "":
            return
        if self.script_running:
            if user_initiated:
                self.display_message("You cannot do that right now!", "FAIL")
            elif len(self.script_queue) < 20:
                self.script_queue.append(name)
            return
        if self.load_script(name):
            self.script_running = True
            self.script_state = ""
            self.script_result = 0
            self.script_line_no = self.first_script_line(1)

    def load_script(self, name):
        path = self.script_path(name)
        if not self.script_exists(name):
            self.log_missing("Script", name)
            return False
        lines = {}                                          # (as many lines as it likes: 01, 02... 100, 101...)
        last = 0
        for text in self.read_lines(path):
            if trim(text) != "" and not trim(text).startswith("//"):
                n = int(val(field(text, 1, "\t")))
                if n < 1:
                    n = last + 1
                lines[n] = text
                last = n
        self.script_lines = [""] * (max(lines, default=0) + 2)
        for n, text in lines.items():
            self.script_lines[n] = text
        self.script_name = name
        self.log("Script started: " + name)
        return True

    def first_script_line(self, n):
        for i in range(max(1, int(n)), len(self.script_lines)):
            if self.script_lines[i] != "":
                return i
        return 0

    def end_script(self):
        self.script_running = False
        self.script_state = ""
        self.script_line_no = 0

    def script_jump(self, goto):
        n = val(goto)
        if n <= 0:
            self.end_script()
            return
        self.script_line_no = self.first_script_line(n)
        if self.script_line_no == 0:
            self.end_script()

    def script_condition(self, met, goto):
        """Conditions jump to goto when NOT met."""
        if not met:
            self.script_jump(goto)

    def run_scripts(self):
        """Called once per game loop."""
        if not self.script_running:
            if not self.script_queue:
                return
            queued = self.script_queue.pop(0)
            self.start_script(queued, False)
            if not self.script_running:
                return
        st = self.script_state
        if st == "WAIT":
            if self.clock() < self.script_wait_until:
                return
        elif st == "CONVERSATION":
            if self.script_result == 0:
                return
            if self.script_result > 0:
                line = self.script_response_line.get(self.script_result, 0)
                if line > 0:
                    self.script_jump(lbstr(line))
            else:
                # Closed with the red X: its cancel line if it has one, else the script ends
                if self.script_cancel_line > 0:
                    self.script_jump(lbstr(self.script_cancel_line))
                else:
                    self.script_state = ""
                    self.script_result = 0
                    self.end_script()
                    return
        elif st == "RACK":
            if self.script_result == 0:
                return
            if self.script_cancel_line > 0:
                self.script_jump(lbstr(self.script_cancel_line))
        elif st == "MOVE.PLAYER":
            if self.player_walk_active:
                return
        elif st == "MOVE.ENTITY":
            if self.script_move_ent is not None:
                return
        self.script_state = ""
        self.script_result = 0
        for _ in range(50):  # At most 50 lines per loop (so Goto.Line loops can't hang the game)
            if not self.script_running:
                break
            self.execute_script_line()
            if self.script_state != "" or self.pending_map_change:
                break

    # =================================================================================================================
    # Variables and conditions
    # =================================================================================================================
    def expand_data_variables(self, text):
        """$Attr.<Name>, $Item.<Name>, $Skill.<Name>, $Equipped.<Slot> -> values."""
        name_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_()'."
        p = 0
        out = []
        n = len(text)
        while p < n:
            q = text.find("$", p)
            if q < 0:
                out.append(text[p:])
                break
            out.append(text[p:q])
            kind = ""
            for prefix in ("$attr.", "$item.", "$skill.", "$equipped."):
                if text[q:q + len(prefix)].lower() == prefix:
                    kind = prefix
                    break
            if kind == "":
                out.append("$")
                p = q + 1
                continue
            e = q + len(kind)
            while e < n and text[e] in name_chars:
                e += 1
            name = text[q + len(kind):e]
            if kind == "$attr.":
                value = self.get_attribute(name) or "0"
            elif kind == "$item.":
                value = lbstr(self.items_held(name) + self.items_equipped(name))
            elif kind == "$skill.":
                value = lbstr(self.skill_level(name))
            else:
                value = "none"
                s = self.equip_slot_index(name)
                if s > 0 and self.equipped[s]:
                    value = self.equipped[s]
            out.append(value)
            p = e
        return "".join(out)

    def parse_script_variables(self, text):
        if "$" not in text and "[TAB]" not in text:
            return text
        low = text.lower()
        if "$attr." in low or "$item." in low or "$skill." in low or "$equipped." in low:
            text = self.expand_data_variables(text)
        clicked = self.clicked_ent if (self.clicked_ent is not None and self.clicked_ent.alive) else None
        p = self.player
        reps = [
            ("$Entity.under.Cursor.ID", lbstr(clicked.uid if clicked else 0)),
            ("$Object.under.Cursor.X", lbstr(int(clicked.x) if clicked else 0)),
            ("$Object.under.Cursor.Y", lbstr(int(clicked.y) if clicked else 0)),
            ("$Tile.under.Cursor.X", lbstr(self.clicked_tile_x)),
            ("$Tile.under.Cursor.Y", lbstr(self.clicked_tile_y)),
            ("$Tile.under.Player.X", lbstr(self.tile_of_x(p.fx))),
            ("$Tile.under.Player.Y", lbstr(self.tile_of_y(p.fy))),
        ]
        for a, b in reps:
            text = text.replace(a, b)
        if "$Random.Percent" in text:
            text = text.replace("$Random.Percent", lbstr(random_number(1, 100)))
        reps = [
            ("$Inventory.Slots", lbstr(self.empty_inventory_slots())),
            ("$Player.Name", self.player_name),
            ("$Player.X", lbstr(int(p.x))),
            ("$Player.Y", lbstr(int(p.y))),
            ("$Map.Name", self.screen_name),
            ("$Map.X", lbstr(self.map_x())),
            ("$Map.Y", lbstr(self.map_y())),
            ("$Map.Z", lbstr(self.map_z())),
            ("$Cursor.X", lbstr(self.script_cursor_x)),
            ("$Cursor.Y", lbstr(self.script_cursor_y)),
            ("$Time", lbstr(seconds_today())),
        ]
        for a, b in reps:
            text = text.replace(a, b)
        for i in range(1, 10):
            text = text.replace("$Variable.%d" % i, self.script_vars[i])
        return text.replace("[TAB]", "\t")

    def set_script_variable(self, variable, value):
        n = val(variable.replace("$", "").replace("Variable.", "").replace("variable.", ""))
        if n < 1 or n > 9:
            self.log("ERROR - Script %s: can't store into '%s'" % (self.script_name, variable))
            return
        self.script_vars[int(n)] = value

    def evaluate_condition(self, expression):
        """a=b, a<>b, a<b, a>b, a<=b, a>=b (numbers or text), joined with "and"/"or"."""
        expression = trim(expression)
        low = expression.lower()
        p = low.find(" or ")
        if p >= 0:
            return self.evaluate_condition(expression[:p]) or self.evaluate_condition(expression[p + 4:])
        p = low.find(" and ")
        if p >= 0:
            return self.evaluate_condition(expression[:p]) and self.evaluate_condition(expression[p + 5:])
        operator = ""
        for op in ("<=", ">=", "<>", "<", ">", "="):
            if op in expression:
                operator = op
                break
        if operator == "":
            return val(safe_eval(expression)) != 0
        p = expression.find(operator)
        a = safe_eval(expression[:p])
        b = safe_eval(expression[p + len(operator):])
        if is_number(a) and is_number(b):
            a, b = val(a), val(b)
        else:
            a, b = a.upper(), b.upper()
        if operator == "=":
            return a == b
        if operator == "<>":
            return a != b
        if operator == "<":
            return a < b
        if operator == ">":
            return a > b
        if operator == "<=":
            return a <= b
        return a >= b

    def condition_met(self, condition):
        """A condition written in data (Lock lines): the script variables plus $Attr. $Item. $Skill. $Equipped."""
        return self.evaluate_condition(self.parse_script_variables(condition))

    def direction_matches(self, directions):
        mask = 0
        directions = directions.upper()
        if is_number(directions):
            mask = int(val(directions))
        else:
            directions = directions.replace("NORTH", "N").replace("SOUTH", "S").replace("EAST", "E").replace("WEST", "W")
            if "N" in directions:
                mask += 1
            if "E" in directions:
                mask += 2
            if "S" in directions:
                mask += 4
            if "W" in directions:
                mask += 8
        return (int(self.player.direction) & mask) != 0

    def player_on_tile_coords(self, coords):
        tx = self.tile_of_x(self.player.fx)
        ty = self.tile_of_y(self.player.fy)
        i = 1
        while word(coords, i) != "":
            c = word(coords, i)
            if val(word(c, 1, ",")) == tx and val(word(c, 2, ",")) == ty:
                return True
            i += 1
        return False

    def player_on_tile_type(self, name):
        """The tile under the player, or its decor, is name (or name with any number: Reeds)."""
        x, y = self.tile_of_x(self.player.fx), self.tile_of_y(self.player.fy)
        return any(t and (t == name or strip_digits(t) == name) for t in (self.tile_name[x][y], self.decor_name[x][y]))

    @staticmethod
    def type_matches(e, type_name):
        """NPC matches any NPC; the old GoodNPC / BadNPC an NPC that is Good / Bad now."""
        if e is None or TYPE_NAMES.get(e.type, "").upper() != normalise_type(type_name).upper():
            return False
        attitude = attitude_of_type(type_name)
        return attitude == "" or e.hostile == (attitude == "Bad")

    def player_distance_to(self, e):
        p = self.player
        if e.type == TILE:
            return distance(p.cx, p.cy, self.script_cursor_x, self.script_cursor_y)
        return distance(p.cx, p.cy, e.cx, e.cy)

    # =================================================================================================================
    # One line
    # =================================================================================================================
    def execute_script_line(self):
        n = self.script_line_no
        if n <= 0 or n >= len(self.script_lines):
            self.end_script()
            return
        self.error_sub = "Execute.Script.Line %s line %d" % (self.script_name, n)
        text = self.script_lines[n]
        command = trim(field(text, 2, "\t"))
        arg = [""] * 34
        for i in range(1, 33):  # Display.Conversation may have up to 15 responses (the editor shows 4)
            arg[i] = trim(self.parse_script_variables(field(text, i + 2, "\t")))
        named = self.place_args(command, arg)              # place IDs -> coordinates (places.py)
        pid = named.name if named is not None else ""
        self.script_args = arg
        self.script_line_no = self.first_script_line(n + 1)
        if self.script_line_no == 0 and command != "End":
            self.script_line_no = len(self.script_lines)  # Runs off the end -> ends after this line
        p = self.player
        c = command
        if c == "End":
            self.end_script()
        elif c == "Play.Sound":
            self.play_sound(arg[1])
        elif c == "Display.Message":
            self.display_message(arg[2], arg[1])
        elif c == "Give.Item":
            self.add_inventory_item(arg[1], parse_quantity(arg[2] or "1"))
        elif c == "Take.Item":
            self.remove_inventory_item(arg[1], parse_quantity(arg[2] or "1"))
        elif c == "Remove.Entity":
            e = self.find_entity_at(arg[1], arg[2], pid)
            if e is not None:
                self.remove_entity(e)
            else:
                self.log("Script %s: no '%s' at %s" % (self.script_name, arg[2], arg[1]))
        elif c == "Remove.Line.From.File":
            self.remove_line_from_file(arg[1], arg[2])
        elif c == "Sleep":
            self.start_sleep(arg[1] or "Next")
        elif c == "Change.Tile":
            self.script_change_tile(arg[1], arg[2], val(arg[3]), val(arg[4]))
        elif c == "Change.All.Tiles":
            self.change_all_tiles(arg[1], arg[2])
        elif c == "Add.Entity":
            self.add_entity_of_type(arg[3], arg[2], val(word(arg[1], 1, ",")), val(word(arg[1], 2, ",")), arg[4])
        elif c == "Add.Action.To.Queue":
            self.add_action_to_queue(arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], val(arg[7]))
        elif c == "Remove.Action.From.Queue":
            self.remove_action_from_queue(arg[1])
        elif c == "Wait":
            self.script_wait_until = self.clock() + val(arg[1]) * 1000
            self.script_state = "WAIT"
        elif c == "Teleport":
            self.pending_map = arg[2]
            if self.pending_map in ("", "-"):
                self.pending_map = self.screen_name
            self.pending_x, self.pending_y = p.x, p.y
            if arg[1] != "":
                self.pending_x = val(word(arg[1], 1, ","))
                self.pending_y = val(word(arg[1], 2, ","))
            self.pending_map_change = True
        elif c == "Display.Conversation":
            self.script_conversation()
        elif c == "Display.Item.Rack":
            if self.open_item_rack(arg[1], arg[2], arg[3]):
                self.script_state = "RACK"
                self.script_result = 0
                self.script_cancel_line = val(arg[4])
            elif val(arg[4]) > 0:
                self.script_jump(arg[4])
        elif c == "Add.Line.To.File":
            self.add_line_to_file(arg[1], arg[2])
        elif c == "Goto.Line":
            self.script_jump(arg[1])
        elif c == "Goto.Script":
            self.end_script()
            self.start_script(arg[1], False)
        elif c == "Block.Player":
            self.block_player()
        elif c == "Update.Skill":
            self.update_skill(arg[1], arg[2])
        elif c == "Update.Attribute":
            cur = self.get_attribute(arg[1])
            new = arg[2][1:] if arg[2][:1] == "=" else lbstr(apply_change(val(cur), arg[2]))
            if self.quest_start_blocked(arg[1], new):          # (a quest that still needs something: quests.py)
                self.end_script()
                return
            self.update_attribute(arg[1], arg[2])
        elif c == ">Quest.Can.Start":
            self.script_condition(self.quest_can_start(arg[1]), arg[2])
        elif c == "Set.NPC.Attitude":
            self.set_npc_attitude(arg[1], arg[2])
        elif c == "Quest.Note":
            self.quest_note(arg[1], arg[2], False)
        elif c == "Quest.Note.Done":
            self.quest_note(arg[1], arg[2], True)
        elif c == "Edit.Entity":
            self.edit_entity(arg[1], arg[2], arg[3], arg[4], pid)
        elif c == "Get.Value":
            self.set_script_variable(arg[3], self.get_script_value(arg[1], arg[2]))
        elif c == "Reveal.BlackOut.Tile":
            self.reveal_fog_cell(arg[1])
        elif c == "Edit.View.Distance":
            self.fog_view_distance = val(arg[1])
            self.fog_all_disabled = self.fog_view_distance <= 0
            self.force_layer_update = True
        elif c == "Toggle.User.Input":
            self.user_input_enabled = self.on_off(arg[1])
            if not self.user_input_enabled:
                self.stop_player_walk()
                self.player_attack_target = None
        elif c == "Toggle.Player.Visibility":
            self.player_visible = self.on_off(arg[1])
        elif c == "Move.Player":
            self.walk_player_to(val(word(arg[1], 1, ",")) + p.w / 2, val(word(arg[1], 2, ",")) + p.h / 2,
                                self.speed_to_pixels(max(0.1, val(arg[2]))), 1)
            self.script_state = "MOVE.PLAYER"
        elif c == "Move.Entity":
            e = self.find_entity_at(arg[1], arg[2], pid)
            if e is not None:
                e.target_x = val(word(arg[3], 1, ",")) + e.w / 2
                e.target_y = val(word(arg[3], 2, ",")) + e.h / 2
                e.script_move = self.speed_to_pixels(max(0.1, val(arg[4])))
                self.forget_path(e)
                self.script_move_ent = e
                self.script_state = "MOVE.ENTITY"
            else:
                self.log("Script %s: Move.Entity found no '%s' at %s" % (self.script_name, arg[2], arg[1]))
        elif c == "Change.Player.Sprite":
            self.change_player_sprite(arg[1])
        # CONDITIONS (the last argument is the line to go to if the condition is NOT met)
        elif c == ">Conditional":
            self.script_condition(self.evaluate_condition(arg[1]), arg[2])
        elif c == ">Distance.From.Clicked.Entity":
            e = self.clicked_ent
            met = e is not None and e.alive and self.player_distance_to(e) <= val(arg[1])
            self.script_condition(met, arg[2])
        elif c == ">Distance.From.Clicked.Tile":
            met = distance(p.cx, p.cy, (self.clicked_tile_x - 0.5) * self.tw,
                           (self.clicked_tile_y - 0.5) * self.th) <= val(arg[1])
            self.script_condition(met, arg[2])
        elif c == ">Distance.From.Cursor":
            met = distance(p.cx, p.cy, self.script_cursor_x, self.script_cursor_y) <= val(arg[1])
            self.script_condition(met, arg[2])
        elif c == ">Distance.From.Coordinates":
            met = distance(p.cx, p.cy, val(word(arg[1], 1, ",")), val(word(arg[1], 2, ","))) <= val(arg[2])
            self.script_condition(met, arg[3])
        elif c == ">Name":
            self.script_condition(self.player_name.upper() == arg[1].upper(), arg[2])
        elif c == ">In.Direction":
            self.script_condition(self.direction_matches(arg[1]), arg[2])
        elif c == ">Not.In.Direction":
            self.script_condition(not self.direction_matches(arg[1]), arg[2])
        elif c == ">Got.Item":
            self.script_condition(self.items_held(arg[1]) >= max(1, val(arg[2])), arg[3])
        elif c == ">Not.Got.Item":
            self.script_condition(self.items_held(arg[1]) < max(1, val(arg[2])), arg[3])
        elif c == ">Line.In.File":
            self.script_condition(self.line_exists_in_file(arg[1], arg[2]) > 0, arg[3])
        elif c == ">Line.Not.In.File":
            self.script_condition(self.line_exists_in_file(arg[1], arg[2]) == 0, arg[3])
        elif c == ">Random":
            self.script_condition(rnd() * 100 < val(arg[1]), arg[2])
        elif c == ">On.Map":
            self.script_condition(arg[1].replace(" ", "") == self.screen_name, arg[2])
        elif c == ">Not.On.Map":
            self.script_condition(arg[1].replace(" ", "") != self.screen_name, arg[2])
        elif c == ">On.Tile.Coordinates":
            self.script_condition(self.player_on_tile_coords(arg[1]), arg[2])
        elif c == ">Not.On.Tile.Coordinates":
            self.script_condition(not self.player_on_tile_coords(arg[1]), arg[2])
        elif c == ">On.Tile.Type":
            self.script_condition(self.player_on_tile_type(arg[1]), arg[2])
        elif c == ">Not.On.Tile.Type":
            self.script_condition(not self.player_on_tile_type(arg[1]), arg[2])
        elif c == ">Entity.Clicked.On.Is.Type":
            goto = arg[2] or arg[3]
            self.script_condition(self.type_matches(self.clicked_ent, arg[1]), goto)
        elif c == ">Tile.In.Line.Of.Sight":
            tx = (val(word(arg[1], 1, ",")) - 0.5) * self.tw
            ty = (val(word(arg[1], 2, ",")) - 0.5) * self.th
            self.script_condition(self.in_line_of_sight(p.cx, p.cy, tx, ty), arg[2])
        elif c == ">Entity.In.Line.Of.Sight":
            self.script_condition(self.in_line_of_sight(p.cx, p.cy, val(word(arg[1], 1, ",")),
                                                        val(word(arg[1], 2, ","))), arg[2])
        elif c == "":
            pass
        else:
            self.log("ERROR - Script %s line %d: unknown command '%s'" % (self.script_name, n, command))

    @staticmethod
    def on_off(value):
        return trim(value).upper() in ("ON", "1", "TRUE", "YES")

    def script_conversation(self):
        """Display.Conversation NPC, MESSAGE, RESPONSE 1, GOTO 1 ... RESPONSE 15, GOTO 15 (the editor has 4).
        A response ending in [if <condition>] only shows when the condition is true, e.g.
        "Ashford [if $Attr.Waystone.Ashford>=1]" (the condition's $ variables are already filled in)."""
        arg = self.script_args
        self.responses = []
        self.response_actions = []
        self.script_response_line = {}
        for i in range(1, 16):
            r = arg[1 + i * 2]
            if r == "":
                continue
            p = r.lower().rfind("[if ")
            if p >= 0 and r.endswith("]"):
                if not self.evaluate_condition(r[p + 4:-1]):
                    continue
                r = trim(r[:p])
            self.responses.append(r)
            self.response_actions.append("")
            self.script_response_line[len(self.responses)] = val(arg[2 + i * 2])
        if not self.responses:
            self.responses = ["Continue"]
            self.script_response_line = {1: 0}
        npc = arg[1]
        self.ab_image = self.npc_image(npc)
        self.ab_title = pretty(npc)
        if npc in ("You", "Player"):
            self.ab_title = self.player_name
        self.ab_text = arg[2].replace("\\", "|")
        self.ab_item_defs = []
        self.show_action_box("Conversation")
        self.script_state = "CONVERSATION"
        self.script_result = 0
        self.script_cancel_line = 0

    def script_change_tile(self, coords, name, delay, change_back):
        tx = val(word(coords, 1, ","))
        ty = val(word(coords, 2, ","))
        if tx < 1 or ty < 1 or tx > self.xt or ty > self.yt:
            self.log("ERROR - Change.Tile: '%s' is not a tile" % coords)
            return
        original = self.cell_text(int(tx), int(ty))      # (the tile and its decor: what it changes back to)
        if delay <= 0:
            self.change_tile(int(tx), int(ty), name, keep_decor=False)
            if change_back > 0:
                self.add_action_to_queue("CHANGE.TILE", original, "Tile", name, self.screen_name, coords, change_back)
        else:
            self.add_action_to_queue("CHANGE.TILE", name, "Tile", "-", self.screen_name, coords, delay)
            if change_back > 0:
                self.add_action_to_queue("CHANGE.TILE", original, "Tile", "-", self.screen_name, coords,
                                         delay + change_back)

    def edit_entity(self, coords, name, value, change, pid=""):
        e = self.find_entity_at(coords, name, pid)
        if e is None:
            self.log("Script %s: Edit.Entity found no '%s' at %s" % (self.script_name, name, coords))
            return
        x, y = e.x, e.y
        v = value.upper()
        if v == "X":
            self.set_entity_position(e, apply_change(x, change), y)
        elif v == "Y":
            self.set_entity_position(e, x, apply_change(y, change))
        elif v in ("POSITION", "XY", "X,Y"):
            sign = change[:1]
            if sign not in ("=", "+", "-") or sign == "":
                sign = "="
            change2 = word(change, 2, ",")
            if change2[:1] not in ("=", "+", "-") or change2[:1] == "":
                change2 = sign + change2
            self.set_entity_position(e, apply_change(x, word(change, 1, ",")), apply_change(y, change2))
        elif v == "MISC":
            if e.type == MAPITEM:
                q = apply_change(e.quantity, change)
                if q <= 0:
                    self.remove_entity(e)
                else:
                    e.quantity = int(q)
            else:
                e.misc = lbstr(apply_change(val(e.misc), change))
        elif v == "QUANTITY":
            q = apply_change(e.quantity, change)
            if q <= 0:
                self.remove_entity(e)
            else:
                e.quantity = int(q)
        elif v in ("HP", "HITPOINTS", "HITS"):
            hp = min(apply_change(e.hp, change), max(1, e.max_hp))
            e.hp = max(0, hp)
            if hp <= 0:
                self.kill_npc(e)
        elif v in ("MAXHP", "MAX.HITPOINTS"):
            e.max_hp = max(1, apply_change(e.max_hp, change))
        elif v == "ORIGINAL.X":
            e.orig_x = apply_change(e.orig_x, change)
        elif v == "ORIGINAL.Y":
            e.orig_y = apply_change(e.orig_y, change)
        elif v in ("SPEED", "MOVEMENT.SPEED"):
            e.move_speed = self.speed_to_pixels(apply_change(e.move_speed, change))
        elif v == "AGGRESSIVE":
            e.aggressive = apply_change(e.aggressive, change)
        elif v == "STRENGTH":
            e.strength = apply_change(e.strength, change)
        elif v == "DEFENCE":
            e.defence = apply_change(e.defence, change)
        elif v == "AGGRO.RANGE":
            e.aggro_range = apply_change(e.aggro_range, change)
        elif v == "ATTITUDE" or (v == "TYPE" and e.type == NPC and attitude_of_type(change)):
            # this one NPC Good or Bad, until it is loaded again (Set.NPC.Attitude changes it for good)
            hostile = parse_attitude(change) if v == "ATTITUDE" else attitude_of_type(change) == "Bad"
            if e.type != NPC or hostile is None:
                self.log("ERROR - Edit.Entity: can't make %s '%s'" % (name, change))
            elif e.hostile != hostile:
                self.set_npc_hostile(e, hostile)
        elif v == "TYPE":
            if normalise_type(change) == "":
                self.log("ERROR - Edit.Entity: unknown type '%s'" % change)
                return
            quantity = lbstr(e.quantity)
            source = e.source
            self.remove_entity(e)
            new = self.add_entity_of_type(change, name, x, y, quantity)
            if new is not None:
                new.source = source
        elif v in ("NAME", "SPRITE"):
            self.replace_sprite(e, change)
        else:
            self.log("ERROR - Edit.Entity: unknown value '%s'" % value)

    def get_script_value(self, type_name, item):
        t = trim(type_name).upper()
        if t in ("INVENTORY", "ITEM"):
            return lbstr(self.items_held(item))
        if t == "BANK":
            return lbstr(self.bank_quantity_of(item))
        if t == "ATTRIBUTE":
            return self.get_attribute(item)
        if t in ("SKILL", "LEVEL"):
            return lbstr(self.skill_level(item))
        if t == "XP":
            return lbstr(self.skill_xp_of(item))
        if t in ("HITPOINTS", "HP"):
            return lbstr(self.player.hp)
        if t in ("EQUIPPED", "EQUIPMENT"):
            s = self.equip_slot_index(item)
            if s > 0 and self.equipped[s]:
                return self.equipped[s]
            return "none"
        if t in ("CALCULATION", "CALC"):
            if "=" in item or "<" in item or ">" in item:
                return "1" if self.evaluate_condition(item) else "0"
            return safe_eval(item)
        self.log("ERROR - Get.Value: unknown value type '%s'" % type_name)
        return safe_eval(item)

    # =================================================================================================================
    # Files (scripts may read and change text files in the game folder)
    # =================================================================================================================
    def line_exists_in_file(self, file, ln):
        path = os.path.join(self.root, file)
        if not os.path.exists(path):
            self.log_missing("File", file)
            return 0
        return sum(1 for line in self.read_lines(path) if wildcard_match(line, ln))

    def remove_line_from_file(self, file, ln):
        path = os.path.join(self.root, file)
        if not os.path.exists(path):
            self.log_missing("File", file)
            return
        text = ini.read_text(path)
        lines = text.replace("\r", "").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for i, line in enumerate(lines):
            if wildcard_match(line, ln):
                del lines[i]
                with open(path, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                return

    def add_line_to_file(self, file, ln):
        path = os.path.join(self.root, file)
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            self.log("ERROR - Add.Line.To.File: folder for '%s' not found" % file)
            return
        with open(path, "a", encoding="cp1252", errors="replace", newline="\r\n") as f:
            f.write(ln + "\n")

    # =================================================================================================================
    # Attributes (free-form save variables)
    # =================================================================================================================
    def get_attribute(self, name):
        k = trim(name).upper()
        for n, v in self.attributes:
            if n.upper() == k:
                return v
        return "0"

    def update_attribute(self, name, change):
        """=Q, +Q, -Q (=text stores text)"""
        name = trim(name)
        if name == "":
            return
        idx = -1
        for i, (n, v) in enumerate(self.attributes):
            if n.upper() == name.upper():
                idx = i
                break
        if idx < 0:
            if len(self.attributes) >= 500:
                self.log("ERROR - Too many attributes")
                return
            self.attributes.append([name, "0"])
            idx = len(self.attributes) - 1
        if change[:1] == "=" and not is_number(change[1:]):
            self.attributes[idx][1] = change[1:]
        else:
            self.attributes[idx][1] = lbstr(apply_change(val(self.attributes[idx][1]), change))
        self.check_locks(True)
        if self.stats_view == 2:
            self.draw_quests(True)
        if self.main_setup_complete:
            self.quest_markers_refresh()

    # =================================================================================================================
    # Quest notes: lines a script writes in a quest's journal entry (Quest.Note), crossed out when done (Quest.Note.Done)
    # =================================================================================================================
    def quest_title(self, quest):
        """A quest named by its title or by its Attribute -> its title in Data\\Quests.ini (or the name as given)."""
        q = trim(quest)
        for name, d in self.help_read_ini(os.path.join("Data", "Quests.ini")):
            if name.lower() == q.lower() or self.help_clean(d.get("ATTRIBUTE", "")).lower() == q.lower():
                return name
        return q

    def quest_note(self, quest, text, done):
        """Adds text to the quest's notes (once: the same text again changes nothing), or crosses it out (done; it is
        added crossed out if it wasn't there). Quest.Note.Done with text * crosses out all the quest's notes."""
        quest, text = self.quest_title(quest), trim(text)
        if not quest or not text:
            return
        found = False
        for n in self.quest_notes:
            if n[0] == quest and (text == "*" or n[2].lower() == text.lower()):
                found = True
                if done:
                    n[1] = 1
        if not found and text != "*":
            if len(self.quest_notes) >= 400:
                self.log("ERROR - Too many quest notes")
                return
            self.quest_notes.append([quest, 1 if done else 0, text])
            if not done:
                self.display_message("Journal (%s): %s" % (quest, text), "darkgreen")
        self.quest_popup = None
        if self.stats_view == 2:
            self.draw_quests(True)

    # =================================================================================================================
    # The action queue: entries are the Add.Action.To.Queue arguments joined by TAB plus the time they are due:
    #   ACTION <TAB> Name <TAB> Type <TAB> Misc <TAB> Map <TAB> X,Y <TAB> Seconds <TAB> Due
    # =================================================================================================================
    def add_action_to_queue(self, action, name, type_name, misc, map_name, coords, seconds):
        if len(self.action_queue) >= 300:
            self.log("ERROR - Action queue is full")
            return
        if misc == "":
            misc = "-"
        if map_name == "":
            map_name = self.screen_name
        self.action_queue.append("\t".join([action, name, type_name, misc, map_name, coords, lbstr(seconds),
                                            lbstr(clock_seconds() + seconds)]))

    def set_queue_quantity(self, action, name, map_name, coords, quantity):
        for i, entry in enumerate(self.action_queue):
            if (field(entry, 1, "\t") == action and field(entry, 2, "\t") == name and field(entry, 5, "\t") == map_name
                    and field(entry, 6, "\t") == coords):
                parts = entry.split("\t")
                while len(parts) < 8:
                    parts.append("")
                parts[3] = lbstr(quantity)
                self.action_queue[i] = "\t".join(parts[:8])

    def remove_action_from_queue(self, pattern):
        keep = []
        for entry in self.action_queue:
            due = field(entry, 8, "\t")
            arguments = entry[:len(entry) - len(due) - 1]
            if (wildcard_match(arguments, pattern) or wildcard_match(entry, pattern) or
                    wildcard_match(field(entry, 2, "\t"), pattern)):
                continue
            keep.append(entry)
        self.action_queue = keep

    def run_action_queue(self):
        now = clock_seconds()
        i = 0
        while i < len(self.action_queue):
            if val(field(self.action_queue[i], 8, "\t")) <= now:
                if self.do_queue_entry(i):
                    del self.action_queue[i]
                    continue
            i += 1

    def postpone_queue_entry(self, n, seconds):
        entry = self.action_queue[n]
        due = field(entry, 8, "\t")
        self.action_queue[n] = entry[:len(entry) - len(due)] + lbstr(clock_seconds() + seconds)

    def do_queue_entry(self, n):
        """True when the entry is finished with."""
        entry = self.action_queue[n]
        action = field(entry, 1, "\t").upper()
        name = field(entry, 2, "\t")
        type_name = field(entry, 3, "\t")
        misc = field(entry, 4, "\t")
        map_name = field(entry, 5, "\t")
        coords = field(entry, 6, "\t")
        x = val(word(coords, 1, ","))
        y = val(word(coords, 2, ","))
        if action in ("ADD.SHOP.ITEM", "REMOVE.SHOP.ITEM"):
            if self.ab_mode == "Shop" and self.rack_name == type_name:
                self.change_rack_stock(name, val(misc) if action == "ADD.SHOP.ITEM" else -val(misc))
                self.show_rack_page(False)
            return True
        if map_name == "-":
            map_name = self.screen_name
        if self.map_slot(map_name) == 0:
            return True
        ox, oy = self.map_ox(map_name), self.map_oy(map_name)
        if action == "CHANGE.TILE" and map_name != self.screen_name:
            k = self.map_slot(map_name)
            col = (k - 1) % 3
            row = int((k - 1) / 3)
            self.change_window_tile(int(x) + col * self.xt, int(y) + row * self.yt, name)
            return True
        if normalise_type(type_name) != "Tile":
            x += ox
            y += oy
            coords = "%s,%s" % (lbstr(x), lbstr(y))
        if action in ("ADD", "ADD.ENTITY"):
            if normalise_type(type_name) == "NPC":
                if distance(self.player.cx, self.player.cy, x + 16, y + 16) < 32:
                    self.postpone_queue_entry(n, 3)
                    return False
            if self.find_entity_at(coords, name) is None or normalise_type(type_name) == "Tile":
                e = self.add_entity_of_type(type_name, name, x, y, misc)
                if e is not None:
                    e.source = "MAP"
        elif action in ("REMOVE", "REMOVE.ENTITY"):
            if normalise_type(type_name) == "Tile":
                return True
            self.remove_entity(self.find_entity_at(coords, name))
        elif action == "SET.QUANTITY":
            pass  # Nothing to do when due: the partly-taken stack is back to full the next time the map loads
        elif action == "CHANGE.TILE":
            if self.tile_of_x(self.player.fx) == x and self.tile_of_y(self.player.fy) == y:
                if self.spec_blocks(name):
                    self.postpone_queue_entry(n, 2)
                    return False
            self.change_tile(int(x), int(y), name, keep_decor=False)
        else:
            self.log("ERROR - Unknown queue action '%s'" % action)
        return True

    def apply_queue_entities(self, map_name, ox, oy):
        """A map has just loaded onto the ground: entities waiting to respawn are taken off it, dropped things are put
        back, partly-taken stacks keep what's left."""
        for entry in list(self.action_queue):
            if field(entry, 5, "\t") != map_name:
                continue
            name = field(entry, 2, "\t")
            type_name = field(entry, 3, "\t")
            misc = field(entry, 4, "\t")
            coords = field(entry, 6, "\t")
            x = val(word(coords, 1, ",")) + ox
            y = val(word(coords, 2, ",")) + oy
            coords = "%s,%s" % (lbstr(x), lbstr(y))
            action = field(entry, 1, "\t").upper()
            if action in ("ADD", "ADD.ENTITY"):
                if normalise_type(type_name) != "Tile":
                    self.remove_entity(self.find_entity_at(coords, name))
            elif action in ("REMOVE", "REMOVE.ENTITY"):
                if normalise_type(type_name) != "Tile" and self.find_entity_at(coords, name) is None:
                    e = self.add_entity_of_type(type_name, name, x, y, misc)
                    if e is not None:
                        e.source = "DROPPED"
                        e.map = map_name
            elif action == "SET.QUANTITY":
                e = self.find_entity_at(coords, name)
                if e is not None:
                    e.quantity = max(1, int(val(misc)))
