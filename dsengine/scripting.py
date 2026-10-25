"""Scripts (data\\Scripts\\*.txt), as the desktop game's script.py runs them, one per player at a time: each player has
their own script running, its variables, its waits and conversations.

What a script changes in the world is shared, except quest business: once a script has looked at the player's quest
attributes ($Attr, Get.Value ATTRIBUTE, >Quest.Can.Start), what it changes after that is the player's own (a tile they
alone see changed, an NPC that is a friend or weaker to them alone, a thing that's gone for them alone). The commands
Personal and Shared set that by hand. A map's entry script never adds a second copy of something already there."""
import os

from dragonsword import ini
from dragonsword.lb import (val, word, field, trim, lbstr, distance, strip_digits, random_number, rnd, parse_quantity,
                            apply_change, is_number, safe_eval, seconds_today, wildcard_match, pretty)

from .entity import (Entity, TILE, MAPITEM, STATICOBJECT, NPC, TYPE_NAMES, normalise_type, attitude_of_type,
                     parse_attitude)

PIXEL_ARGS = {"Remove.Entity": (1,), "Add.Entity": (1,), "Teleport": (1,), "Edit.Entity": (1,), "Move.Entity": (1, 3),
              "Move.Player": (1,), ">Distance.From.Coordinates": (1,), ">Entity.In.Line.Of.Sight": (1,),
              "Add.Action.To.Queue": (6,)}
TILE_ARGS = {"Change.Tile": (1,), ">Tile.In.Line.Of.Sight": (1,), ">On.Tile.Coordinates": (1,),
             ">Not.On.Tile.Coordinates": (1,)}
MAP_ARGS = {"Teleport": 2, "Add.Action.To.Queue": 5}
ENTITY_COMMANDS = ("Remove.Entity", "Edit.Entity", "Move.Entity")
PERSONAL_FIELDS = {"STRENGTH": "strength", "DEFENCE": "defence", "AGGRESSIVE": "aggressive",
                   "AGGRO.RANGE": "aggro_range"}


class ScriptMixin:
    def init_scripts(self):
        self.script_running = False
        self.script_name = ""
        self.script_lines = [""]
        self.script_line_no = 0
        self.script_state = ""
        self.script_wait_until = 0
        self.script_result = 0
        self.script_cancel_line = 0
        self.script_move_ent = None
        self.script_queue = []
        self.script_vars = [""] * 10
        self.script_args = [""] * 34
        self.script_response_line = {}
        self.script_entry = False           # the map's entry script
        self.script_personal = False        # what it changes now is this player's own
        self.script_forced = None           # Personal / Shared said so
        self.work_from = None               # (x, y) the player stood at when its Play.Animation began (they stay put)

    # =================================================================================================================
    # Starting, stopping
    # =================================================================================================================
    def script_path(self, name):
        return os.path.join(self.data.root, "data", "Scripts", name + ".txt")

    def script_exists(self, name):
        if not name:
            return False
        try:
            return os.path.getsize(self.script_path(name)) > 0
        except OSError:
            return False

    def find_action_script(self, verb, name, etype, ent_id=""):
        if ent_id and self.script_exists("%s %s" % (verb, ent_id)):
            return "%s %s" % (verb, ent_id)
        if self.script_exists(verb + " " + name):
            return verb + " " + name
        if strip_digits(name) != name and self.script_exists(verb + " " + strip_digits(name)):
            return verb + " " + strip_digits(name)
        if etype > 0 and self.script_exists("%s [%s]" % (verb, TYPE_NAMES.get(etype, ""))):
            return "%s [%s]" % (verb, TYPE_NAMES.get(etype, ""))
        return ""

    def start_script(self, name, user_initiated, entry=False):
        name = trim(name)
        if name.lower().endswith(".txt"):
            name = name[:-4]
        if name == "":
            return
        if self.script_running:
            if user_initiated:
                self.display_message("You cannot do that right now!", "FAIL")
            elif len(self.script_queue) < 20:
                self.script_queue.append((name, entry))
            return
        if self.load_script(name):
            self.begin_script(entry)

    def begin_script(self, entry=False):
        self.script_running = True
        self.script_state = ""
        self.script_result = 0
        self.script_entry = entry
        self.script_personal = False
        self.script_forced = None
        self.script_line_no = self.first_script_line(1)

    def run_script_lines(self, title, lines):
        """Runs these lines (NN<TAB>Command<TAB>args) now, as a script called title (the admin panel's): False if
        another script is running."""
        if self.script_running:
            return False
        self.script_lines = [""] + list(lines) + [""]
        self.script_name = title
        self.script_tools_used = set()
        self.begin_script()
        return True

    def load_script(self, name):
        path = self.script_path(name)
        if not self.script_exists(name):
            return False
        lines = {}
        last = 0
        for text in self.data.read_lines(path):
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
        self.script_tools_used = set()             # (a tool wears once a go: a swing of the axe, a cast of the line)
        return True

    def first_script_line(self, n):
        for i in range(max(1, int(n)), len(self.script_lines)):
            if self.script_lines[i] != "":
                return i
        return 0

    def end_script(self):
        if self.loot_collect is not None and not self.loot_hold:
            self.loot_finish()
        self.script_running = False
        self.script_state = ""
        self.script_line_no = 0
        self.script_personal = False                # (no script running: nothing done now is a quest's own)
        self.script_forced = None
        self.work_from = None
        if self.script_move_ent is not None:
            self.script_move_ent.script_moving = False
            self.script_move_ent = None

    def script_jump(self, goto):
        n = val(goto)
        if n <= 0:
            self.end_script()
            return
        self.script_line_no = self.first_script_line(n)
        if self.script_line_no == 0:
            self.end_script()

    def script_condition(self, met, goto):
        if not met:
            self.script_jump(goto)

    def run_scripts(self):
        """Once a tick."""
        if not self.script_running:
            if not self.script_queue:
                return
            name, entry = self.script_queue.pop(0)
            self.start_script(name, False, entry)
            if not self.script_running:
                return
        st = self.script_state
        if st == "WAIT":
            if self.work_from is not None and distance(self.player.x, self.player.y, *self.work_from) > 8:
                self.end_script()                   # (walked off from a tree, a rock, the water: no logs for that)
                self.emit({"t": "work_stop"})
                return
            if self.now < self.script_wait_until:
                return
        elif st == "CONVERSATION":
            if self.script_result == 0:
                return
            if self.script_result > 0:
                line = self.script_response_line.get(self.script_result, 0)
                if line > 0:
                    self.script_jump(lbstr(line))
                else:
                    self.end_script()
                    return
            else:
                if self.script_cancel_line > 0:
                    self.script_jump(lbstr(self.script_cancel_line))
                else:
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
        elif st == "SLEEP":
            if self.sleep_state is not None:
                return
        self.script_state = ""
        self.script_result = 0
        for _ in range(50):
            if not self.script_running:
                break
            self.execute_script_line()
            if self.script_state != "" or self.pending_map is not None:
                break

    def personal_now(self):
        """Does what the script changes now belong to this player alone?"""
        if self.script_forced is not None:
            return self.script_forced
        return self.script_personal

    # =================================================================================================================
    # Variables and conditions
    # =================================================================================================================
    def expand_data_variables(self, text):
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
                if self.script_running:
                    self.script_personal = True
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
        if "$" not in text:
            return text.replace("[TAB]", "\t")
        clicked = self.clicked_ent if (self.clicked_ent is not None and self.clicked_ent.alive) else None
        p = self.player
        ox, oy = self.map_ox(), self.map_oy()
        reps = [
            ("$Entity.under.Cursor.ID", lbstr(clicked.uid if clicked else 0)),
            ("$Object.under.Cursor.X", lbstr(int(clicked.x - ox) if clicked else 0)),
            ("$Object.under.Cursor.Y", lbstr(int(clicked.y - oy) if clicked else 0)),
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
            ("$Player.X", lbstr(int(p.x - ox))),
            ("$Player.Y", lbstr(int(p.y - oy))),
            ("$Map.Name", self.screen_name),
            ("$Map.X", lbstr(self.map_x())),
            ("$Map.Y", lbstr(self.map_y())),
            ("$Map.Z", lbstr(self.map_z())),
            ("$Cursor.X", lbstr(int(self.script_cursor_x - ox))),
            ("$Cursor.Y", lbstr(int(self.script_cursor_y - oy))),
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
            return
        self.script_vars[int(n)] = value

    def evaluate_condition(self, expression):
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
        """A condition written in data (Lock lines): $Attr. $Item. $Skill. $Equipped. (never taints a script)."""
        was = self.script_personal
        r = self.evaluate_condition(self.parse_script_variables(condition))
        self.script_personal = was
        return r

    def direction_matches(self, directions):
        mask = 0
        directions = directions.upper()
        if is_number(directions):
            mask = int(val(directions))
        else:
            directions = directions.replace("NORTH", "N").replace("SOUTH", "S").replace("EAST", "E").replace("WEST", "W")
            mask = (1 if "N" in directions else 0) + (2 if "E" in directions else 0) + \
                   (4 if "S" in directions else 0) + (8 if "W" in directions else 0)
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
        m = self.cur_map
        if m is None:
            return False
        x, y = self.tile_of_x(self.player.fx), self.tile_of_y(self.player.fy)
        tile, decor = self.cell_names(m, x, y)
        return any(t and (t == name or strip_digits(t) == name) for t in (tile, decor))

    def type_matches(self, e, type_name):
        if e is None or TYPE_NAMES.get(e.type, "").upper() != normalise_type(type_name).upper():
            return False
        attitude = attitude_of_type(type_name)
        return attitude == "" or self.w.hostile_for(e, self) == (attitude == "Bad")

    # =================================================================================================================
    # Places: IDs in place of coordinates (as the desktop game's places.py)
    # =================================================================================================================
    def place_args(self, command, arg):
        tiles = TILE_ARGS.get(command, ())
        pixels = PIXEL_ARGS.get(command, ())
        if command == "Add.Action.To.Queue" and arg[1].upper() == "CHANGE.TILE":
            tiles, pixels = pixels, ()
        named = None
        for i in tiles + pixels:
            if command in (">On.Tile.Coordinates", ">Not.On.Tile.Coordinates"):
                parts = []
                for part in arg[i].split():
                    pl = self.data.place(part)
                    parts.append("%d,%d" % (pl.tx, pl.ty) if pl else part)
                arg[i] = " ".join(parts)
                continue
            pl = self.data.place(arg[i])
            if pl is None:
                continue
            if i == 1 and command in ENTITY_COMMANDS and pl.kind != "TILE":
                named = pl
            if command == "Add.Entity" and pl.kind == "TILE":
                w, h = self.data.size_of(arg[2])
                arg[i] = "%d,%d" % (pl.px + (self.tw - w) // 2, pl.py + self.th - h)
            else:
                arg[i] = "%d,%d" % ((pl.tx, pl.ty) if i in tiles else (pl.px, pl.py))
            m = MAP_ARGS.get(command)
            if m and arg[m] in ("", "-"):
                arg[m] = pl.map
        return named

    def global_xy(self, coords):
        """Map-local "x,y" (pixels on the player's map) -> global x, y."""
        return val(word(coords, 1, ",")) + self.map_ox(), val(word(coords, 2, ",")) + self.map_oy()

    def find_entity_here(self, coords, name, pid=""):
        x, y = self.global_xy(coords)
        return self.w.find_entity_at(self.player.z, x, y, name, pid, self)

    # =================================================================================================================
    # One line
    # =================================================================================================================
    def execute_script_line(self):
        n = self.script_line_no
        if n <= 0 or n >= len(self.script_lines):
            self.end_script()
            return
        text = self.script_lines[n]
        command = trim(field(text, 2, "\t"))
        arg = [""] * 34
        for i in range(1, 33):
            arg[i] = trim(self.parse_script_variables(field(text, i + 2, "\t")))
        named = self.place_args(command, arg)
        pid = named.name if named is not None else ""
        self.script_args = arg
        self.script_line_no = self.first_script_line(n + 1)
        if self.script_line_no == 0 and command != "End":
            self.script_line_no = len(self.script_lines)
        p = self.player
        w = self.w
        c = command
        if c == "End":
            self.end_script()
        elif c == "Personal":
            self.script_forced = True
        elif c == "Shared":
            self.script_forced = False
        elif c == "Play.Sound":
            self.play_sound(arg[1], (p.cx, p.cy) if arg[2].lower() == "near" else None)
        elif c == "Show.Skill":
            self.show_skill(arg[1])
        elif c == "Play.Animation":
            self.play_work(arg[1], arg[2], arg[3])
        elif c == "Display.Message":
            self.display_message(arg[2], arg[1], sound=trim(arg[3]))   # (the script says what's heard: maybe nothing)
        elif c == "Give.Item":
            if not self.loot_give(arg[1], parse_quantity(arg[2] or "1")):      # (a chest's script fills the chest)
                self.add_inventory_item(arg[1], parse_quantity(arg[2] or "1"))
        elif c == "Take.Item":
            self.remove_inventory_item(arg[1], parse_quantity(arg[2] or "1"))
        elif c == "Remove.Entity":
            e = self.find_entity_here(arg[1], arg[2], pid)
            if e is not None:
                if self.personal_now() and e.owner is not self:
                    self.hidden_uids.add(e.uid)
                else:
                    w.remove_entity(e)
        elif c == "Remove.Line.From.File":
            self.remove_line_from_file(arg[1], arg[2])
        elif c == "Sleep":
            if self.start_sleep(arg[1] or "Next"):
                self.script_state = "SLEEP"
        elif c == "Change.Tile":
            self.script_change_tile(arg[1], arg[2], val(arg[3]), val(arg[4]))
        elif c == "Change.All.Tiles":
            if self.cur_map is not None:
                if self.personal_now():
                    m = self.cur_map
                    for y in range(1, self.yt + 1):
                        for x in range(1, self.xt + 1):
                            for nm in self.cell_names(m, x, y):
                                if nm and (nm == arg[1] or strip_digits(nm) == arg[1]):
                                    self.personal_change_tile(m, x, y, arg[2])
                                    break
                else:
                    w.change_all_tiles(self.cur_map, arg[1], arg[2])
        elif c == "Add.Entity":
            self.script_add_entity(arg)
        elif c == "Add.Action.To.Queue":
            map_name = arg[5] if arg[5] not in ("", "-") or arg[1].upper().endswith("SHOP.ITEM") else self.screen_name
            w.add_action_to_queue(arg[1], arg[2], arg[3], arg[4], map_name, arg[6], val(arg[7]))
        elif c == "Remove.Action.From.Queue":
            w.remove_action_from_queue(arg[1])
        elif c == "Wait":
            self.script_wait_until = self.now + val(arg[1]) * 1000
            self.script_state = "WAIT"
        elif c == "Display.Refusal":
            # Display.Refusal <message> [sound]: a no (a locked door; an empty chest's "duh-derr"): in red, with a sound
            self.refuse(arg[1], trim(arg[2]) if len(arg) > 2 and trim(arg[2]) else "Denied")
        elif c == "Start.Wave":
            # Start.Wave <name>: a data\Waves.ini attack starts (a quest's battle; for everyone there)
            self.w.waves.start(trim(arg[1]), by=self)
        elif c == "Teleport":
            target = arg[2] if arg[2] not in ("", "-") else self.screen_name
            x, y = p.x - self.map_ox(), p.y - self.map_oy()
            if arg[1] != "":
                x, y = val(word(arg[1], 1, ",")), val(word(arg[1], 2, ","))
            self.teleport(target.replace(" ", ""), x, y)
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
            personal, forced, entry = self.script_personal, self.script_forced, self.script_entry
            self.loot_hold = True                       # (a chest's script going on in another file: same chest)
            self.end_script()
            self.loot_hold = False
            self.start_script(arg[1], False, entry)
            if not self.script_running and self.loot_collect is not None:
                self.loot_finish()
            if self.script_running:
                self.script_personal, self.script_forced = personal, forced
        elif c == "Block.Player":
            self.block_player()
        elif c == "Update.Skill":
            self.update_skill(arg[1], arg[2])
        elif c == "Update.Attribute":
            cur = self.get_attribute(arg[1])
            new = arg[2][1:] if arg[2][:1] == "=" else lbstr(apply_change(val(cur), arg[2]))
            if self.quest_start_blocked(arg[1], new):
                self.end_script()
                return
            self.update_attribute(arg[1], arg[2])
        elif c == ">Quest.Can.Start":
            self.script_personal = True
            self.script_condition(self.quest_can_start(arg[1]), arg[2])
        elif c == "Set.NPC.Attitude":
            self.set_npc_attitude(arg[1], arg[2])
        elif c == "Follow.Player":
            self.set_follower(arg[1], arg[2])
        elif c == "Quest.Note":
            self.quest_note(arg[1], arg[2], False)
        elif c == "Quest.Note.Done":
            self.quest_note(arg[1], arg[2], True)
        elif c == "Edit.Entity":
            self.edit_entity(arg[1], arg[2], arg[3], arg[4], pid, n)
        elif c == "Get.Value":
            if trim(arg[1]).upper() == "ATTRIBUTE":
                self.script_personal = True
            self.set_script_variable(arg[3], self.get_script_value(arg[1], arg[2]))
        elif c == "Reveal.BlackOut.Tile":
            self.emit({"t": "reveal", "map": self.screen_name, "cell": arg[1]})
        elif c == "Edit.View.Distance":
            self.fog_view_distance = val(arg[1])
            self.dirty_me = True
        elif c == "Toggle.User.Input":
            self.user_input_enabled = self.on_off(arg[1])
            if not self.user_input_enabled:
                self.stop_player_walk()
                self.player_attack_target = None
                self.keyboard_direction = 0
            self.dirty_me = True
        elif c == "Toggle.Player.Visibility":
            self.player_visible = self.on_off(arg[1])
            self.dirty_me = True
        elif c == "Move.Player":
            x, y = self.global_xy(arg[1])
            self.walk_player_to(x + p.w / 2, y + p.h / 2, self.data.speed_to_pixels(max(0.1, val(arg[2]))), 1)
            self.script_state = "MOVE.PLAYER"
        elif c == "Move.Entity":
            e = self.find_entity_here(arg[1], arg[2], pid)
            if e is not None and not getattr(e, "script_moving", False):
                x, y = self.global_xy(arg[3])
                e.target_x = x + e.w / 2
                e.target_y = y + e.h / 2
                e.script_move = self.data.speed_to_pixels(max(0.1, val(arg[4])))
                w.forget_path(e)
                e.script_moving = True
                self.script_move_ent = e
                self.script_state = "MOVE.ENTITY"
        elif c == "Change.Player.Sprite":
            self.change_player_sprite(arg[1])
        # CONDITIONS (the last argument is the line to go to if the condition is NOT met)
        elif c == ">Conditional":
            self.script_condition(self.evaluate_condition(arg[1]), arg[2])
        elif c == ">Distance.From.Clicked.Entity":
            e = self.clicked_ent
            self.script_condition(e is not None and e.alive and self.player_distance_to(e) <= val(arg[1]), arg[2])
        elif c == ">Distance.From.Clicked.Tile":
            met = distance(p.cx, p.cy, self.map_ox() + (self.clicked_tile_x - 0.5) * self.tw,
                           self.map_oy() + (self.clicked_tile_y - 0.5) * self.th) <= val(arg[1])
            self.script_condition(met, arg[2])
        elif c == ">Distance.From.Cursor":
            met = distance(p.cx, p.cy, self.script_cursor_x, self.script_cursor_y) <= val(arg[1])
            self.script_condition(met, arg[2])
        elif c == ">Distance.From.Coordinates":
            x, y = self.global_xy(arg[1])
            self.script_condition(distance(p.cx, p.cy, x, y) <= val(arg[2]), arg[3])
        elif c == ">Name":
            self.script_condition(self.player_name.upper() == arg[1].upper(), arg[2])
        elif c == ">In.Direction":
            self.script_condition(self.direction_matches(arg[1]), arg[2])
        elif c == ">Not.In.Direction":
            self.script_condition(not self.direction_matches(arg[1]), arg[2])
        elif c == ">Follower.Near":
            e = self.npc_by_id(arg[1])
            self.script_condition(e is not None and e.z == p.z and distance(p.cx, p.cy, e.cx, e.cy) <= val(arg[2]),
                                  arg[3])
        elif c == ">Got.Item":
            tool = self.is_tool(arg[1])
            ok = (self.tools_held(arg[1]) if tool else self.items_held(arg[1])) >= max(1, val(arg[2]))
            if ok and tool and not self.script_name.upper().startswith("TALK TO"):     # (it's being used: it wears)
                used = getattr(self, "script_tools_used", set())
                if arg[1].upper() not in used:
                    used.add(arg[1].upper())
                    self.use_tool(arg[1])
            self.script_condition(ok, arg[3])
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
            self.script_condition(self.type_matches(self.clicked_ent, arg[1]), arg[2] or arg[3])
        elif c == ">Tile.In.Line.Of.Sight":
            tx = self.map_ox() + (val(word(arg[1], 1, ",")) - 0.5) * self.tw
            ty = self.map_oy() + (val(word(arg[1], 2, ",")) - 0.5) * self.th
            self.script_condition(w.in_line_of_sight(p.z, p.cx, p.cy, tx, ty), arg[2])
        elif c == ">Entity.In.Line.Of.Sight":
            x, y = self.global_xy(arg[1])
            self.script_condition(w.in_line_of_sight(p.z, p.cx, p.cy, x, y), arg[2])
        elif c == "":
            pass
        else:
            self.log("ERROR - Script %s line %d: unknown command '%s'" % (self.script_name, n, command))

    @staticmethod
    def on_off(value):
        return trim(value).upper() in ("ON", "1", "TRUE", "YES")

    WORK_BEAT = 800                                 # (ms between the beats of Play.Animation: swings of the axe)

    def show_skill(self, skill):
        """The skill's picture over the player's head (its name as Config.ini [Skills] has it)."""
        want = skill.replace("_", " ").strip().upper()
        name = next((n for n in self.data.skill_name[1:] if n.upper() == want), "")
        if name:
            self.fx_skill_pop(name)

    def npc_by_id(self, npc_id):
        """The NPC with that Id this player sees (their own copy first), or CLICKED: the one they clicked."""
        if trim(npc_id).upper() == "CLICKED":
            e = self.clicked_ent
            return e if e is not None and e.alive else None
        return self.w.placed_entity(trim(npc_id), self)

    def set_follower(self, npc_id, on):
        """Follow.Player: the NPC with that Id (the one this player sees: their own, a quest's) walks after them (ON),
        or stops where it is and stays there (OFF)."""
        e = self.npc_by_id(npc_id)
        if e is None or e.type != NPC or e.ai is None:
            self.log("ERROR - Script %s: Follow.Player: no NPC with Id %s here" % (self.script_name, npc_id))
            return
        a = e.ai
        if self.on_off(on):
            e.follow = self
            a.solid = 0                             # (it doesn't block the doorway behind you)
            e.pose = ""
        else:
            e.follow = None
            a.solid = 0 if self.data.entity_ini(e.name, "Solid", "1") == "0" else 1
            a.back_x, a.back_y = e.cx, e.cy
            a.stand = 1
            self.w.npc_set_idle(e, a, True)

    def play_work(self, anim, times, sound, at=None):
        """Play.Animation: TIMES beats of work at what was clicked (or at) - the animation there, the player's lunge
        towards it, the sound - everyone near sees and hears it."""
        p, w = self.player, self.w
        self.work_from = (p.x, p.y)
        x, y = at if at is not None else (self.script_cursor_x, self.script_cursor_y)
        if not x and not y:
            x, y = p.cx, p.cy
        d = max(1.0, distance(p.cx, p.cy, x, y))
        dx, dy = round((x - p.cx) / d * 3), round((y - p.cy) / d * 3)
        for k in range(max(1, min(8, int(val(times) or 1)))):
            delay = k * self.WORK_BEAT
            if anim:
                w.fx({"t": "anim", "base": anim, "x": int(x), "y": int(y), "ms": 450, "delay": delay}, p.z, x, y)
            if dx or dy:
                w.fx({"t": "nudge", "uid": p.uid, "dx": dx, "dy": dy, "ms": 140, "delay": delay}, p.z, p.cx, p.cy)
            if trim(sound):
                for s in w.hearers(p.z, x, y):
                    s.emit({"t": "sound", "name": sound, "x": int(x), "y": int(y), "delay": delay})

    def script_conversation(self):
        arg = self.script_args
        self.responses = []
        self.response_actions = []
        self.script_response_line = {}
        for i in range(1, 16):
            r = arg[1 + i * 2]
            if r == "":
                continue
            pp = r.lower().rfind("[if ")
            if pp >= 0 and r.endswith("]"):
                if not self.evaluate_condition(r[pp + 4:-1]):
                    continue
                r = trim(r[:pp])
            self.responses.append(r)
            self.response_actions.append("")
            self.script_response_line[len(self.responses)] = val(arg[2 + i * 2])
        if not self.responses:
            self.responses = ["Continue"]
            self.script_response_line = {1: 0}
        npc = arg[1]
        self.ab_image = self.npc_image(npc)
        self.ab_title = self.npc_title(npc)
        if npc in ("You", "Player"):
            self.ab_title = self.player_name
        self.ab_text = arg[2].replace("\\", "|")
        self.ab_item_defs = []
        self.show_action_box("Conversation")
        self.script_state = "CONVERSATION"
        self.script_result = 0
        self.script_cancel_line = 0

    def script_change_tile(self, coords, name, delay, change_back):
        m = self.cur_map
        tx = val(word(coords, 1, ","))
        ty = val(word(coords, 2, ","))
        if m is None or tx < 1 or ty < 1 or tx > self.xt or ty > self.yt:
            return
        tx, ty = int(tx), int(ty)
        if self.personal_now():
            self.personal_change_tile(m, tx, ty, name, delay, change_back)
            return
        w = self.w
        original = m.cell_text(tx, ty)
        coords = "%d,%d" % (tx, ty)
        if delay <= 0:
            w.change_tile(m, tx, ty, name, keep_decor=False)
            if change_back > 0:
                w.add_action_to_queue("CHANGE.TILE", original, "Tile", name, m.name, coords, change_back)
        else:
            w.add_action_to_queue("CHANGE.TILE", name, "Tile", "-", m.name, coords, delay)
            if change_back > 0:
                w.add_action_to_queue("CHANGE.TILE", original, "Tile", "-", m.name, coords, delay + change_back)

    def script_add_entity(self, arg):
        w = self.w
        x, y = self.global_xy(arg[1])
        z = self.player.z
        personal = self.personal_now()
        if (self.script_entry or personal) and w.find_entity_at(z, x, y, arg[2], "", self) is not None:
            return                                  # (already there: entry scripts run each time someone comes)
        e = w.add_entity_of_type(arg[3], arg[2], z, x, y, arg[4], owner=self if personal else None)
        if e is not None and self.script_entry and not personal:
            e.source = "SCRIPT"

    def edit_entity(self, coords, name, value, change, pid="", line=0):
        w = self.w
        e = self.find_entity_here(coords, name, pid)
        if e is None:
            return
        v = value.upper()
        personal = self.personal_now() and e.owner is not self
        if personal and v in PERSONAL_FIELDS:
            f = PERSONAL_FIELDS[v]
            o = self.ent_overrides.setdefault(e.uid, {})
            o[f] = apply_change(o.get(f, getattr(e, f)), change)
            return
        if personal and (v == "ATTITUDE" or (v == "TYPE" and e.type == NPC and attitude_of_type(change))):
            hostile = parse_attitude(change) if v == "ATTITUDE" else attitude_of_type(change) == "Bad"
            if hostile is not None:
                self.ent_attitudes[e.uid] = hostile
                if not hostile and e.target is self and e.ai is not None:
                    w.npc_give_up(e, e.ai)
            return
        if personal:
            key = (self.script_name, line)          # (shared things a quest changes: once each time it's there)
            if key in e.edits_done:
                return
            e.edits_done.add(key)
        x, y = e.x, e.y
        if v == "X":
            w.set_entity_position(e, apply_change(x - self.map_ox(), change) + self.map_ox(), y)
        elif v == "Y":
            w.set_entity_position(e, x, apply_change(y - self.map_oy(), change) + self.map_oy())
        elif v in ("POSITION", "XY", "X,Y"):
            sign = change[:1] if change[:1] in ("=", "+", "-") else "="
            change2 = word(change, 2, ",")
            if change2[:1] not in ("=", "+", "-"):
                change2 = sign + change2
            w.set_entity_position(e, apply_change(x - self.map_ox(), word(change, 1, ",")) + self.map_ox(),
                                  apply_change(y - self.map_oy(), change2) + self.map_oy())
        elif v in ("STATE", "POSE"):                       # (=Sit: it rests sitting from now on; = or =- to stand)
            pose = trim(change.lstrip("="))
            pose = "" if pose in ("", "-") else pose
            e.pose = pose
            if e.ai is not None:
                e.ai.fixed_pose = pose
            w.animate_entity(e, False)
        elif v in ("MISC", "QUANTITY"):
            if e.type == MAPITEM or v == "QUANTITY":
                q = apply_change(e.quantity, change)
                if q <= 0:
                    w.remove_entity(e)
                else:
                    e.quantity = int(q)
            else:
                e.misc = lbstr(apply_change(val(e.misc), change))
        elif v in ("HP", "HITPOINTS", "HITS"):
            hp = min(apply_change(e.hp, change), max(1, e.max_hp))
            e.hp = max(0, hp)
            if hp <= 0:
                if personal:
                    e.hp = 1                         # (a quest weakens it; killing it is still a fight)
                else:
                    self.kill_npc(e)
        elif v in ("MAXHP", "MAX.HITPOINTS"):
            e.max_hp = max(1, apply_change(e.max_hp, change))
        elif v == "ORIGINAL.X":
            e.orig_x = apply_change(e.orig_x - self.map_ox(), change) + self.map_ox()
        elif v == "ORIGINAL.Y":
            e.orig_y = apply_change(e.orig_y - self.map_oy(), change) + self.map_oy()
        elif v in ("SPEED", "MOVEMENT.SPEED"):
            e.move_speed = self.data.speed_to_pixels(apply_change(e.move_speed, change))
        elif v in PERSONAL_FIELDS:
            f = PERSONAL_FIELDS[v]
            setattr(e, f, apply_change(getattr(e, f), change))
        elif v == "ATTITUDE" or (v == "TYPE" and e.type == NPC and attitude_of_type(change)):
            hostile = parse_attitude(change) if v == "ATTITUDE" else attitude_of_type(change) == "Bad"
            if e.type == NPC and hostile is not None and e.hostile != hostile:
                w.set_npc_hostile(e, hostile)
        elif v == "TYPE":
            if normalise_type(change) == "":
                return
            quantity = lbstr(e.quantity)
            source, owner, home = e.source, e.owner, e.map
            w.remove_entity(e)
            new = w.add_entity_of_type(change, name, e.z, x, y, quantity, owner, home)
            if new is not None:
                new.source = source
        elif v in ("NAME", "SPRITE"):
            w.replace_sprite(e, change)

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
            return self.equipped[s] if s > 0 and self.equipped[s] else "none"
        if t in ("CALCULATION", "CALC"):
            if "=" in item or "<" in item or ">" in item:
                return "1" if self.evaluate_condition(item) else "0"
            return safe_eval(item)
        return safe_eval(item)

    def set_npc_attitude(self, which, attitude):
        """Set.NPC.Attitude: one NPC Good or Bad, for this player, for good (their save's [NPC.Attitudes])."""
        hostile = parse_attitude(attitude)
        which = trim(which)
        if hostile is None or not which:
            return
        if which.upper() == "CLICKED":
            e = self.clicked_ent
            if e is None or e.type != NPC:
                return
            key = self.w.npc_key(e)
        else:
            key = which
        self.npc_attitudes[key] = "Bad" if hostile else "Good"
        for e in self.w.ents:
            if e.type == NPC and e.alive and self.w.npc_key(e) == key:
                self.ent_attitudes.pop(e.uid, None)
                if not hostile and e.target is self and e.ai is not None:
                    self.w.npc_give_up(e, e.ai)
                if not hostile and self.player_attack_target is e:
                    self.player_attack_target = None

    def change_player_sprite(self, name):
        d = self.data
        if not d.loaded(name) and not d.animation_available(name):
            return
        self.player_sprite_base = name
        self.w.replace_sprite(self.player, name)
        self.w.animate_entity(self.player, False)
        self.dirty_me = True

    def update_script_move(self):
        """Move.Entity: this player's script walks an entity somewhere."""
        e = self.script_move_ent
        if e is None:
            return
        w = self.w
        if not e.alive:
            self.script_move_ent = None
            return
        tx, ty = e.target_x, e.target_y
        moved = w.npc_walk_to(e, tx, ty, e.script_move, 1, True)
        done = distance(e.cx, e.cy, tx, ty) < 1
        if not moved and not e.path:
            done = True
        if e.path_stuck > 60:
            done = True
        if done:
            w.forget_path(e)
            w.animate_entity(e, False)
            e.target_x = e.target_y = None
            e.script_move = 0
            e.script_moving = False
            self.script_move_ent = None
            if e.type == NPC:
                w.npc_script_move_done(e)

    # =================================================================================================================
    # Files (scripts may read and change text files in the game folder: the server's, shared by everyone)
    # =================================================================================================================
    def safe_path(self, file):
        root = os.path.abspath(self.data.root)
        path = os.path.abspath(os.path.join(root, file))
        return path if path.startswith(root + os.sep) else None

    def line_exists_in_file(self, file, ln):
        path = self.safe_path(file)
        if path is None or not os.path.exists(path):
            return 0
        return sum(1 for line in self.data.read_lines(path) if wildcard_match(line, ln))

    def remove_line_from_file(self, file, ln):
        path = self.safe_path(file)
        if path is None or not os.path.exists(path):
            return
        lines = ini.read_text(path).replace("\r", "").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        for i, line in enumerate(lines):
            if wildcard_match(line, ln):
                del lines[i]
                with open(path, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                return

    def add_line_to_file(self, file, ln):
        path = self.safe_path(file)
        if path is None or not os.path.isdir(os.path.dirname(path)):
            return
        with open(path, "a", encoding="cp1252", errors="replace", newline="\r\n") as f:
            f.write(ln + "\n")

    # =================================================================================================================
    # Attributes (free-form save variables: quest stages, flags, counters)
    # =================================================================================================================
    def get_attribute(self, name):
        k = trim(name).upper()
        for n, v in self.attributes:
            if n.upper() == k:
                return v
        return "0"

    def update_attribute(self, name, change):
        name = trim(name)
        if name == "":
            return
        idx = next((i for i, (n, v) in enumerate(self.attributes) if n.upper() == name.upper()), -1)
        if idx < 0:
            if len(self.attributes) >= 500:
                return
            self.attributes.append([name, "0"])
            idx = len(self.attributes) - 1
        if change[:1] == "=" and not is_number(change[1:]):
            self.attributes[idx][1] = change[1:]
        else:
            self.attributes[idx][1] = lbstr(apply_change(val(self.attributes[idx][1]), change))
        self.dirty_me = True
        self.dirty_quests = True
        self.check_locks(True)
