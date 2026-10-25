"""Homesteads: a home of your own, on a map of its own, to build on; other players may visit if you let them.

  * Each home is a map "0,0,<1000+n>" (a level of its own, so nothing joins it). When it's made it gets its own copy
    of Data\\Homestead.txt (the land a home starts as: changing that file later only changes new homes); what its owner
    builds is kept on top of that copy. It's part of the shared world: visitors see it as it is.
  * Homestones (Entities.ini [Homestone], placed by Dev\\migrate\\build_homestead.py) take you home, if you carry an
    Access Crystal (the quest "A Place of Your Own"), or to a home someone has let you visit. On your own home, the
    homestone also sets who may visit: only you (the start), your friends, or anyone. Closing it sends visitors back.
  * The Homestead Scroll (Spells.ini Effect=Home) takes you home from anywhere.
  * Building (the browser's Build mode): Data\\Buildables.ini says what can be built, of what, and at which level of
    the Construction skill. Floors, walls and doors are the ground (Kind=Tile); furniture, windows, lights and the
    garden go on it (Decor); roofs go over it (Roof: the pieces follow the roof's shape); workshops are objects
    (Object). Taking something down gives back half of what it took.
  * A bed you sleep in at home is where you wake if you fall (not in the arena). A Home_Chest opens onto its owner's
    bank, and only for them.

World.homes (Homes) keeps every home; HomeMixin is the player's side (Session)."""
import logging

from dragonsword import ini
from dragonsword.lb import val, trim, lbstr, strip_digits

from .entity import STATICOBJECT
from .fences import is_fence, fence_piece, join_around
from .maps import MapData

log = logging.getLogger("dragonsword.homes")

HOME_LEVEL = 1000               # home n is the map 0,0,<HOME_LEVEL + n>
VISIT = ("closed", "friends", "open")
VISIT_WORDS = {"closed": "only you", "friends": "you and your friends", "open": "anyone"}
REFUND = 0.5
# a bed's head: (its foot, and where it lies from the head): below, or beside it for a bed lying sideways
BED_FEET = {"Bed001": ("Bed002", 0, 1), "Bed003": ("Bed004", 1, 0), "Bed006": ("Bed005", -1, 0)}


def bed_foot_of(head_x, head_y, name):
    """(foot tile, x, y) of the bed whose head is name at head_x, head_y; None if name isn't a bed's head."""
    f = BED_FEET.get(name)
    return (f[0], head_x + f[1], head_y + f[2]) if f else None


def bed_head_of(foot_x, foot_y, name):
    """(head tile, x, y) of the bed whose foot is name at foot_x, foot_y; None if name isn't a bed's foot."""
    for head, (foot, dx, dy) in BED_FEET.items():
        if foot == name:
            return head, foot_x - dx, foot_y - dy
    return None
GATES = ("Wood_Gate001", "Wood_Gate002", "Wood_Gate003", "Wood_Gate004")   # (decor now, over the ground: once tiles)                 # (a bed's head: its foot, in the tile below)
MENU_MAX = 10


def parse_needs(text):
    """"Plank 2 Nails 4" -> [("Plank", 2), ("Nails", 4)]."""
    parts = trim(text).split()
    out = []
    for i in range(0, len(parts) - 1, 2):
        q = int(val(parts[i + 1]))
        if q > 0:
            out.append((parts[i], q))
    return out


class Homes:
    def __init__(self, world):
        self.w = world
        self.d = d = world.data
        self.homes = {}                 # owner -> {"n", "visit", "friends", "cells", "cleared", "objects", "bed"}
        self.by_map = {}                # map name -> owner
        cfg = lambda k, default: d.config_read("Homestead", k, default)
        self.template_lines = d.read_lines(d.data_file(trim(cfg("Template", "Homestead.txt"))))
        self.arrival = (int(val(cfg("Arrival.X", "13"))), int(val(cfg("Arrival.Y", "18"))))
        self.return_map = trim(cfg("Return.Map", d.start_map))
        self.catalog = self.read_catalog()
        while self.template_lines and not self.template_lines[-1].strip():
            self.template_lines.pop()
        self.template = MapData(d, "0,0,%d" % HOME_LEVEL, self.template_lines) if self.template_lines else None
        self.bases = {}                 # owner -> their land as it was made (a MapData not in the world)

    @property
    def available(self):
        return self.template is not None

    # ----- what can be built (Data\Buildables.ini)
    def read_catalog(self):
        path = self.d.data_file("Buildables.ini")
        out = {}
        try:
            text = ini.read_text(path)
        except OSError:
            return out
        sec = None
        for ln in text.replace("\r", "").split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith(";"):
                continue
            if ln.startswith("[") and ln.endswith("]"):
                sec = ln[1:-1].strip()
                out[sec] = {"id": sec, "kind": "Decor", "cat": "Other", "name": sec.replace("_", " "), "needs": [],
                            "level": 1, "xp": 0.0, "on": ""}
            elif sec and "=" in ln:
                k, v = ln.split("=", 1)
                k, v = k.strip().lower(), v.strip()
                p = out[sec]
                if k == "kind":
                    p["kind"] = v.capitalize()
                elif k == "category":
                    p["cat"] = v
                elif k == "name":
                    p["name"] = v
                elif k == "needs":
                    p["needs"] = parse_needs(v)
                elif k == "level":
                    p["level"] = max(1, int(val(v)))
                elif k == "xp":
                    p["xp"] = float(val(v))
                elif k == "on":
                    p["on"] = v
        for p in out.values():
            if p["kind"] == "Roof":
                p["image"] = "%s_Roof005" % p["id"]
            else:
                p["image"] = p["id"]
        return out

    def catalog_for_client(self):
        return [{"id": p["id"], "kind": p["kind"], "cat": p["cat"], "name": p["name"], "needs": p["needs"],
                 "level": p["level"], "xp": p["xp"], "on": p["on"], "image": p["image"]}
                for p in self.catalog.values()]

    # ----- the homes
    def map_name(self, n):
        return "0,0,%d" % (HOME_LEVEL + n)

    @staticmethod
    def is_home_map(name):
        parts = (name or "").split(",")
        return len(parts) == 3 and parts[0] == "0" and parts[1] == "0" and val(parts[2]) >= HOME_LEVEL

    def owner_of(self, map_name):
        return self.by_map.get(map_name)

    def home_of(self, owner):
        return self.homes.get(owner)

    def map_of(self, owner):
        h = self.homes.get(owner)
        return self.w.maps.get(self.map_name(h["n"])) if h else None

    def create(self, owner):
        if owner in self.homes:
            return self.homes[owner]
        used = {h["n"] for h in self.homes.values()}
        n = 1
        while n in used:
            n += 1
        h = {"n": n, "visit": "closed", "friends": [], "cells": {}, "cleared": [], "objects": {}, "bed": None,
             "land": list(self.template_lines)}          # (its own copy of the land: later changes to it don't come)
        self.homes[owner] = h
        self.make_map(owner)
        return h

    def make_map(self, owner):
        """The home's map, from its own land and what's been built on it, put into the world."""
        h = self.homes[owner]
        w, d = self.w, self.d
        name = self.map_name(h["n"])
        old = w.maps.get(name)
        if old is not None:
            return old
        m = MapData(d, name, h["land"])
        for key in h["cleared"]:
            x, y = (int(v) for v in key.split(","))
            if m.inside(x, y):
                m.decor[m.cell(x, y)] = ""
        for key, cell in h["cells"].items():
            x, y = (int(v) for v in key.split(","))
            if not m.inside(x, y):
                continue
            c = m.cell(x, y)
            if cell.get("tile") in GATES and not cell.get("decor"):      # (a gate built when gates were ground)
                cell["decor"] = cell.pop("tile")
            if cell.get("tile"):
                m.tile[c] = cell["tile"]
            if cell.get("decor"):
                m.decor[c] = cell["decor"]
            if cell.get("under"):
                m.under[c] = cell["under"]
        fence_at = lambda x, y: m.inside(x, y) and is_fence(m.decor[m.cell(x, y)])
        for key, cell in h["cells"].items():
            x, y = (int(v) for v in key.split(","))
            if not m.inside(x, y):
                continue
            c = m.cell(x, y)
            if cell.get("tile") in ("Wheat001", "Wheat002"):
                cell["tile"] = m.tile[c] = "Field001"
            if cell.get("decor") in ("Bed102", "Bed201"):                 # (the double bed's gone: a bed)
                cell["decor"] = m.decor[c] = "Bed001"
            foot = bed_foot_of(x, y, cell.get("decor"))
            if foot and m.inside(foot[1], foot[2]) and not m.decor[m.cell(foot[1], foot[2])]:   # (built before feet)
                h["cells"].setdefault("%d,%d" % foot[1:], {})["decor"] = m.decor[m.cell(foot[1], foot[2])] = foot[0]
            if is_fence(cell.get("decor")):
                cell["decor"] = m.decor[c] = fence_piece(fence_at, x, y)
        for c in range(1, len(m.tile)):
            m.refresh_cell(c)
        m.set_roofs(self.roof_cells(h, m))
        m.version = 0
        w.maps[name] = m
        w.by_pos[(m.mx, m.my, m.mz)] = m
        self.by_map[name] = owner
        w.spawn_map_entities(m)
        for key, obj in h["objects"].items():
            x, y = (int(v) for v in key.split(","))
            self.spawn_object(m, obj, x, y)
        w.objects_dirty.add(name)
        return m

    def spawn_object(self, m, name, x, y):
        w = self.w
        e = w.add_entity_of_type("StaticObject", name, m.mz, m.ox + (x - 1) * w.tw, m.oy + (y - 1) * w.th, "",
                                 home=m.name)
        if e is not None:
            e.source = "HOME"
            w.objects_dirty.add(m.name)
        return e

    def base_of(self, owner):
        """The owner's land as it was when the home was made (what taking a floor up goes back to)."""
        b = self.bases.get(owner)
        if b is None:
            h = self.homes[owner]
            b = self.bases[owner] = MapData(self.d, self.map_name(h["n"]), h["land"])
        return b

    def protected_of(self, owner):
        """Tiles nobody can build on at this home: where you arrive, and where its land's objects (the homestone)
        stand."""
        d = self.d
        out = {self.arrival}
        for etype, name, x, y, misc in self.base_of(owner).entity_lines:
            out.add((int(x // d.tw) + 1, int(y // d.th) + 1))
        return out

    def object_at(self, m, x, y):
        w = self.w
        gx, gy = m.ox + (x - 1) * w.tw, m.oy + (y - 1) * w.th
        for e in w.ents:
            if e.type == STATICOBJECT and e.alive and e.z == m.mz and e.owner is None and \
                    abs(e.x - gx) < 2 and abs(e.y - gy) < 2:
                return e
        return None

    # ----- saving
    def load(self, saved):
        """saved: Homes.state() from the database (before the action queue is put back: it may change their tiles)."""
        for owner, h in (saved or {}).items():
            try:
                rec = {"n": int(h["n"]), "visit": h.get("visit") if h.get("visit") in VISIT else "closed",
                       "friends": [str(f) for f in h.get("friends", [])][:50],
                       "cells": {str(k): {kk: str(vv) for kk, vv in v.items() if kk in ("tile", "decor", "roof")}
                                 for k, v in h.get("cells", {}).items()},
                       "cleared": [str(k) for k in h.get("cleared", [])],
                       "objects": {str(k): str(v) for k, v in h.get("objects", {}).items()},
                       "bed": list(h["bed"]) if h.get("bed") else None,
                       # (a home saved before homes had their own land gets the land as it is now, once)
                       "land": [str(ln) for ln in h["land"]] if h.get("land") else list(self.template_lines)}
            except (KeyError, TypeError, ValueError):
                log.error("A broken home for %s was left out", owner)
                continue
            self.homes[owner] = rec
            self.make_map(owner)

    def state(self):
        return {o: dict(h) for o, h in self.homes.items()}

    # ----- visiting
    def may_visit(self, owner, visitor):
        h = self.homes.get(owner)
        if h is None:
            return False
        if visitor == owner or h["visit"] == "open":
            return True
        return h["visit"] == "friends" and visitor in h["friends"]

    def visitable_by(self, visitor):
        return sorted(o for o in self.homes if o != visitor and self.may_visit(o, visitor))

    # ----- roofs: the pieces follow each roof's shape
    def roof_cells(self, h, m):
        """cell -> (roof tile, group): each joined-up patch of one material is a roof (its own group, so standing
        under it hides just that roof); a cell's piece comes from its row and column within the patch."""
        mat = {}
        for key, cell in h["cells"].items():
            if cell.get("roof"):
                x, y = (int(v) for v in key.split(","))
                mat[(x, y)] = cell["roof"]
        out = {}
        group = 0
        seen = set()
        for start in sorted(mat):
            if start in seen:
                continue
            group += 1
            stack, patch = [start], []
            seen.add(start)
            while stack:
                x, y = stack.pop()
                patch.append((x, y))
                for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nb not in seen and mat.get(nb) == mat[start]:
                        seen.add(nb)
                        stack.append(nb)
            cells = set(patch)
            for x, y in patch:
                x1 = x
                while (x1 - 1, y) in cells:
                    x1 -= 1
                x2 = x
                while (x2 + 1, y) in cells:
                    x2 += 1
                y1 = y
                while (x, y1 - 1) in cells:
                    y1 -= 1
                y2 = y
                while (x, y2 + 1) in cells:
                    y2 += 1
                out[m.cell(x, y)] = (roof_piece(mat[start], x, y, x1, y1, x2, y2), group)
        return out


ROW_KINDS = {1: "R", 2: "TB", 3: "TRB", 4: "TRDB", 5: "TURDB", 6: "TURDDB"}


def roof_piece(material, x, y, x1, y1, x2, y2):
    """<Material>_Roof001-015: piece = row * 3 + column + 1 (rows T U R D B: eave, upper slope, ridge, lower slope,
    eave; columns W M E: the gables and the middle). A roof deeper than 6 repeats its slopes."""
    depth = y2 - y1 + 1
    if depth <= 6:
        rows = ROW_KINDS[depth]
        rk = rows[y - y1]
    else:
        i, mid = y - y1, depth // 2
        rk = "T" if i == 0 else ("B" if i == depth - 1 else ("R" if i == mid else ("U" if i < mid else "D")))
    if x1 == x2:
        ck = "M"
    else:
        ck = "W" if x == x1 else ("E" if x == x2 else "M")
    return "%s_Roof%03d" % (material, "TURDB".index(rk) * 3 + "WME".index(ck) + 1)


class HomeMixin:
    """The player's side of homesteads (on Session)."""

    def init_home(self):
        self.home_return = None         # (map, x, y): where the homestone sends you back to
        self.native_menu = None         # [callable per response] of a menu the engine shows (the homestone's)

    @property
    def homes(self):
        return self.w.homes

    def on_own_home(self):
        m = self.cur_map
        return m is not None and self.homes.owner_of(m.name) == self.player_name

    def home_state(self):
        h = self.homes.home_of(self.player_name)
        m = self.cur_map
        here = self.homes.owner_of(m.name) if m is not None else None
        own = here is not None and here == self.player_name
        return {"has": h is not None, "own": own, "here": here, "visit": h["visit"] if h else "closed",
                "protected": sorted(self.homes.protected_of(self.player_name)) if own else []}

    def has_home_access(self):
        return self.items_held("Access_Crystal") > 0

    # ----- menus the engine shows itself (a conversation whose answers call back here)
    def show_menu(self, title, image, text, options):
        """options: [(words, callable)]."""
        if self.ab_mode:
            self.hide_action_box()
        self.responses = [o[0] for o in options]
        self.response_actions = [""] * len(options)
        self.native_menu = [o[1] for o in options]
        self.ab_image, self.ab_title, self.ab_text = image, title, text
        self.ab_item_defs = []
        self.show_action_box("Conversation")

    def native_menu_chosen(self, n):
        menu, self.native_menu = self.native_menu, None
        self.hide_action_box()
        if menu and 1 <= n <= len(menu) and menu[n - 1] is not None:
            menu[n - 1]()

    # ----- homestones
    def homestone_touched(self, e):
        if self.player_distance_to(e) > 56:
            self.display_message("You are too far away!", "FAIL")
            return
        homes = self.homes
        if not homes.available:
            self.display_message("The homestone is cold. (This world has no homesteads.)", "FAIL")
            return
        self.play_sound("Teleporter")
        m = self.cur_map
        owner = homes.owner_of(m.name) if m is not None else None
        opts = []
        if owner is None:
            if self.has_home_access():
                opts.append(("Take me home.", self.go_home))
                text = "The hearth rune glows warm under your hand. Your Access Crystal hums in answer."
            else:
                text = ("The hearth rune glows warm under your hand, but nothing happens: you need an Access Crystal "
                        "to go home. (Ask the settler by Ashford's homestone.)")
            if homes.visitable_by(self.player_name):
                opts.append(("Visit someone's home...", self.visit_menu))
        elif owner == self.player_name:
            h = homes.home_of(owner)
            text = ("Your homestead. Who may visit: %s.\\Press B (or the Build button) to build."
                    % VISIT_WORDS[h["visit"]])
            opts.append(("Take me back.", self.leave_home))
            opts.append(("Who may visit...", self.visit_setting_menu))
            opts.append(("My friends...", self.friends_menu))
            if self.home_bed_ok():
                opts.append(("Forget my bed (wake in town if I fall).", self.forget_bed))
        else:
            text = "%s's homestead." % owner
            opts.append(("Take me back.", self.leave_home))
            if self.has_home_access():
                opts.append(("Take me to my own home.", self.go_home))
        opts.append(("Never mind.", None))
        self.show_menu("Homestone", "Homestone", text, opts)

    def visit_menu(self):
        names = self.homes.visitable_by(self.player_name)
        if not names:
            self.display_message("Nobody has let you visit their home.", "INFO")
            return
        opts = [("%s's home%s" % (o, " (here now)" if o in self.w.sessions else ""),
                 (lambda o=o: self.visit_home(o))) for o in names[:MENU_MAX]]
        opts.append(("Never mind.", None))
        self.show_menu("Homestone", "Homestone", "Whose home? These are the ones you may visit.", opts)

    def visit_setting_menu(self):
        h = self.homes.home_of(self.player_name)
        opts = []
        for v, words in (("closed", "Only me."), ("friends", "Me and my friends."), ("open", "Anyone.")):
            opts.append((words + (" (now)" if h["visit"] == v else ""), (lambda v=v: self.set_visit(v))))
        opts.append(("Never mind.", None))
        self.show_menu("Homestone", "Homestone", "Who may come to your homestead? Now: %s." % VISIT_WORDS[h["visit"]],
                       opts)

    def friends_menu(self):
        h = self.homes.home_of(self.player_name)
        opts = [("Forget %s." % f, (lambda f=f: self.remove_friend(f))) for f in h["friends"][:MENU_MAX // 2]]
        others = [n for n, s in self.w.sessions.items() if n != self.player_name and s.in_world() and
                  n not in h["friends"]]
        opts += [("Add %s." % n, (lambda n=n: self.add_friend(n))) for n in sorted(others)[:MENU_MAX // 2]]
        opts.append(("Never mind.", None))
        text = ("Your friends may visit when you let friends in. Friends: %s.\\You can add players who are here now."
                % (", ".join(h["friends"]) or "none yet"))
        self.show_menu("Homestone", "Homestone", text, opts)

    def set_visit(self, v):
        h = self.homes.home_of(self.player_name)
        if h is None or v not in VISIT:
            return
        h["visit"] = v
        self.display_message("Your homestead: now %s may visit." % VISIT_WORDS[v], "SUCCESS")
        self.send_out_visitors()
        self.dirty_me = True

    def add_friend(self, name):
        h = self.homes.home_of(self.player_name)
        if h is None or name in h["friends"] or len(h["friends"]) >= 50:
            return
        h["friends"].append(name)
        self.display_message("%s is your friend now: they may visit when you let friends in." % name, "SUCCESS")
        s = self.w.sessions.get(name)
        if s is not None:
            s.display_message("%s has made you a friend of their homestead." % self.player_name, "INFO")

    def remove_friend(self, name):
        h = self.homes.home_of(self.player_name)
        if h is None or name not in h["friends"]:
            return
        h["friends"].remove(name)
        self.display_message("%s is no longer a friend of your homestead." % name, "INFO")
        self.send_out_visitors()

    def send_out_visitors(self):
        """Whoever may no longer be on this player's home is sent back."""
        m = self.homes.map_of(self.player_name)
        if m is None:
            return
        for s in list(self.w.sessions.values()):
            if s is not self and s.in_world() and s.cur_map is m and not self.homes.may_visit(self.player_name,
                                                                                               s.player_name):
                s.display_message("%s has closed their homestead: the homestone sends you back." % self.player_name,
                                  "INFO")
                s.leave_home()

    # ----- going and coming back
    def remember_return(self):
        m = self.cur_map
        if m is None or self.homes.is_home_map(m.name) or self.in_arena():
            return
        p = self.player
        self.home_return = (m.name, int(p.x - m.ox), int(p.y - m.oy))

    def arrival_xy(self):
        ax, ay = self.homes.arrival
        return (ax - 1) * self.tw, (ay - 1) * self.th - 8

    def go_home(self):
        if not self.has_home_access():
            self.display_message("You need your Access Crystal to go home.", "FAIL")
            return
        h = self.homes.create(self.player_name)
        self.remember_return()
        x, y = self.arrival_xy()
        self.player_attack_target = None
        self.display_message("The homestone carries you home.", "SUCCESS")
        self.teleport(self.homes.map_name(h["n"]), x, y)

    def visit_home(self, owner):
        if not self.homes.may_visit(owner, self.player_name):
            self.display_message("%s's homestead is closed to you." % owner, "FAIL")
            return
        h = self.homes.home_of(owner)
        self.remember_return()
        x, y = self.arrival_xy()
        self.player_attack_target = None
        self.display_message("The homestone carries you to %s's homestead." % owner, "SUCCESS")
        self.teleport(self.homes.map_name(h["n"]), x, y)
        o = self.w.sessions.get(owner)
        if o is not None and o is not self:
            o.display_message("%s has come to visit your homestead." % self.player_name, "INFO")

    def return_point(self):
        r = self.home_return
        if r and self.w.map_named(r[0]) is not None and not self.homes.is_home_map(r[0]):
            return r
        town = self.w.map_named(self.homes.return_map)
        if town is not None:
            for e in self.w.ents:
                if e.name == "Homestone" and e.alive and e.map == town.name:
                    return town.name, int(e.x - town.ox), int(e.y - town.oy + 36)
        d = self.data
        return d.start_map, d.start_x, d.start_y

    def leave_home(self):
        name, x, y = self.return_point()
        self.player_attack_target = None
        self.teleport(name, x, y)

    def check_home_entry(self):
        """Coming into the world on a home: still allowed there?"""
        m = self.cur_map
        if m is None or not self.homes.is_home_map(m.name):
            return
        owner = self.homes.owner_of(m.name)
        if owner is None or not self.homes.may_visit(owner, self.player_name):
            self.display_message("That homestead is closed to you now: you're back in town.", "INFO")
            self.leave_home()

    # ----- the Homestead spell (Spells.ini Effect=Home)
    def home_spell_ok(self):
        if not self.homes.available:
            self.display_message("The spell fizzles: this world has no homesteads.", "FAIL")
            return False
        if not self.has_home_access():
            self.display_message("The spell needs an Access Crystal to find your home. (The settler in Ashford.)",
                                 "FAIL")
            return False
        return True

    # ----- beds and chests at home
    def home_bed_ok(self):
        h = self.homes.home_of(self.player_name)
        if h is None or not h.get("bed"):
            return False
        m = self.homes.map_of(self.player_name)
        x, y = h["bed"]
        return m is not None and m.inside(x, y) and self.data.tile_ini(m.decor[m.cell(x, y)], "Use.Words",
                                                                       "").find("Sleep") >= 0

    def forget_bed(self):
        h = self.homes.home_of(self.player_name)
        if h:
            h["bed"] = None
        self.display_message("If you fall, you'll wake in town again.", "INFO")

    def slept_at_home(self, e):
        """Sleeping in a bed at home: that's where you wake if you fall."""
        if not self.on_own_home() or e is None:
            return
        m = self.cur_map
        x, y = int((e.x - m.ox) // self.tw) + 1, int((e.y - m.oy) // self.th) + 1
        h = self.homes.home_of(self.player_name)
        if h.get("bed") != [x, y]:
            h["bed"] = [x, y]
            self.display_message("This is your bed now: if you fall, you'll wake here.", "SUCCESS")

    def home_respawn(self):
        """(map, x, y) of the player's bed at home, or None."""
        if not self.home_bed_ok():
            return None
        h = self.homes.home_of(self.player_name)
        m = self.homes.map_of(self.player_name)
        x, y = h["bed"]
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1), (1, 1), (-1, 1)):
            tx, ty = x + dx, y + dy
            if m.inside(tx, ty) and "1" in m.walk[m.cell(tx, ty)] and self.homes.object_at(m, tx, ty) is None:
                return m.name, (tx - 1) * self.tw, (ty - 1) * self.th - 8
        ax, ay = self.arrival_xy()
        return m.name, ax, ay

    def open_home_chest(self, e):
        if self.player_distance_to(e) > 56:
            self.display_message("You are too far away!", "FAIL")
            return
        owner = self.homes.owner_of(e.map)
        if owner != self.player_name:
            self.display_message("It's locked: it's %s's chest." % owner if owner else "It's locked.", "FAIL")
            return
        self.play_sound("Door")
        self.open_item_rack("BANK", "Home_Chest", "-")

    # ----- building
    def build_fail(self, text):
        self.display_message(text, "FAIL")
        return False

    def build_where(self, x, y):
        """The map if this player may build on its tile x,y (a message and None if not)."""
        m = self.cur_map
        if m is None or self.homes.owner_of(m.name) != self.player_name:
            self.build_fail("You can only build on your own homestead.")
            return None
        if not (2 <= x <= self.xt - 1 and 2 <= y <= self.yt - 1):
            self.build_fail("That's the edge of your land.")
            return None
        if (x, y) in self.homes.protected_of(self.player_name):
            self.build_fail("Leave that clear: it's where the homestone puts you down.")
            return None
        return m

    def someone_on(self, m, x, y):
        for s in self.w.sessions.values():
            p = s.player
            if s.in_world() and p.z == m.mz:
                tm, tx, ty = self.w.tile_at(p.z, p.fx, p.fy)
                if tm is m and (tx, ty) == (x, y):
                    return True
        return False

    def is_wall(self, name):
        return bool(name) and "1" not in self.data.tile_walk_data(name)

    def build(self, x, y, piece_id):
        homes = self.homes
        p = homes.catalog.get(piece_id)
        if p is None:
            return self.build_fail("You can't build that.")
        x, y = int(x), int(y)
        m = self.build_where(x, y)
        if m is None:
            return False
        level = self.skill_level("Construction")
        if level < p["level"]:
            self.refuse("You need level %d Construction to build that (you have %d)." % (p["level"], level))
            return False
        h = homes.home_of(self.player_name)
        key = "%d,%d" % (x, y)
        cell = h["cells"].get(key, {})
        c = m.cell(x, y)
        tile, decor = m.tile[c], m.decor[c]
        obj = homes.object_at(m, x, y)
        kind = p["kind"]
        d = self.data
        if kind == "Roof":
            if cell.get("roof") == piece_id:
                return False
        elif obj is not None:
            return self.build_fail("The %s is in the way." % self.display_name(obj))
        elif kind == "Tile":
            if tile == piece_id or cell.get("tile") == piece_id:
                return False
            if decor and (self.is_wall(piece_id) or not cell.get("decor")):
                return self.build_fail("Clear the %s away first." % pretty_tile(decor))
            if self.is_wall(piece_id) and self.someone_on(m, x, y):
                return self.build_fail("Someone is standing there.")
        elif kind == "Decor" and d.is_under_tile(piece_id):        # (a rug: under whatever stands there)
            if m.under[c]:
                return self.build_fail("Take the %s away first." % pretty_tile(m.under[c]))
            if self.is_wall(tile):
                return self.build_fail("You can't put that on a wall.")
        elif kind == "Decor":
            on = p["on"]
            if decor:
                return self.build_fail("Take the %s away first." % pretty_tile(decor))
            if on.lower() == "wall":
                if not self.is_wall(tile):
                    return self.build_fail("That goes on a wall.")
            elif on:
                if tile != on:
                    return self.build_fail("That goes on a %s." % pretty_tile(on))
            elif self.is_wall(tile):
                return self.build_fail("You can't put that on a wall.")
            elif "1" not in m.walk[c]:
                return self.build_fail("There's no room there.")
            if self.someone_on(m, x, y) and d.spec_blocks(piece_id):
                return self.build_fail("Someone is standing there.")
            if piece_id in BED_FEET and not self.room_for_foot(m, h, *bed_foot_of(x, y, piece_id)[1:]):
                return self.build_fail("There's no room for its foot.")
        elif kind == "Object":
            if decor:
                return self.build_fail("Clear the %s away first." % pretty_tile(decor))
            if self.is_wall(tile) or "1" not in m.walk[c]:
                return self.build_fail("There's no room there.")
            if self.someone_on(m, x, y):
                return self.build_fail("Someone is standing there.")
        else:
            return self.build_fail("You can't build that.")
        for item, qty in p["needs"]:
            if self.items_held(item) < qty:
                return self.build_fail("You need %s." % ", ".join(
                    "%d %s" % (q, pretty_item(i)) for i, q in p["needs"]))
        for item, qty in p["needs"]:
            self.remove_inventory_item(item, qty)
        w = self.w
        if kind == "Tile":
            if cell.get("tile"):
                self.refund(cell["tile"])
            cell["tile"] = piece_id
            h["cells"][key] = cell
            self.forget_regrowth(m, x, y)
            w.change_tile(m, x, y, piece_id, keep_decor=True)
        elif kind == "Decor" and d.is_under_tile(piece_id):
            cell["under"] = piece_id
            h["cells"][key] = cell
            w.change_tile(m, x, y, piece_id)
        elif kind == "Decor":
            cell["decor"] = piece_id
            h["cells"][key] = cell
            self.forget_regrowth(m, x, y)
            w.change_tile(m, x, y, piece_id)
            if piece_id in BED_FEET:
                foot, fx, fy = bed_foot_of(x, y, piece_id)
                h["cells"].setdefault("%d,%d" % (fx, fy), {})["decor"] = foot
                self.forget_regrowth(m, fx, fy)
                w.change_tile(m, fx, fy, foot)
            if is_fence(piece_id):
                self.join_fences(m, h, x, y)
        elif kind == "Roof":
            if cell.get("roof"):
                self.refund(cell["roof"])
            cell["roof"] = piece_id
            h["cells"][key] = cell
            m.set_roofs(homes.roof_cells(h, m))
        else:
            h["objects"][key] = piece_id
            homes.spawn_object(m, piece_id, x, y)
        if p["xp"] > 0:
            self.update_skill("Construction", "+" + lbstr(p["xp"]))
        self.play_sound("Build" if d.loaded("Build") else "Pickup")
        return True

    def room_for_foot(self, m, h, x, y):
        """Can a bed's foot go on tile x,y (below its head, or beside it)?"""
        if not (2 <= x <= self.xt - 1 and 2 <= y <= self.yt - 1) or (x, y) in self.homes.protected_of(self.player_name):
            return False
        c = m.cell(x, y)
        return (not m.decor[c] and not self.is_wall(m.tile[c]) and "1" in m.walk[c]
                and self.homes.object_at(m, x, y) is None and not self.someone_on(m, x, y))

    def refund(self, piece_id):
        if is_fence(piece_id):
            piece_id = "Wood_Fence001"                  # (any piece of fence: it was built as a fence)
        p = self.homes.catalog.get(piece_id)
        if p is None:
            return
        back = []
        for item, qty in p["needs"]:
            q = int(qty * REFUND)
            if q > 0 and self.inventory_slots_available(item) >= q:
                self.add_inventory_item(item, q, quiet=True)
                back.append("%d %s" % (q, pretty_item(item)))
        if back:
            self.display_message("You get back %s." % ", ".join(back), "INFO")

    def join_fences(self, m, h, x, y):
        """A fence built or taken down at x,y: it and the fences beside it show the pieces that meet now."""
        fence_at = lambda fx, fy: m.inside(fx, fy) and is_fence(m.decor[m.cell(fx, fy)])
        for fx, fy, piece in join_around(fence_at, x, y):
            if m.decor[m.cell(fx, fy)] != piece:
                self.w.change_tile(m, fx, fy, piece)
            cell = h["cells"].get("%d,%d" % (fx, fy))
            if cell and is_fence(cell.get("decor")):
                cell["decor"] = piece

    def forget_regrowth(self, m, x, y):
        """Something growing back here (a picked bush, a chopped tree) would undo the building: forget it."""
        w = self.w
        coords = "%d,%d" % (x, y)
        w.action_queue = [e for e in w.action_queue
                          if not (e.split("\t")[0].upper() == "CHANGE.TILE" and len(e.split("\t")) > 5 and
                                  e.split("\t")[4] == m.name and e.split("\t")[5] == coords)]

    def unbuild(self, x, y):
        """Takes down the top thing on tile x,y: the roof, then an object, then what's on the ground, then the
        ground itself (back to the land as it was). Half the materials come back."""
        x, y = int(x), int(y)
        m = self.build_where(x, y)
        if m is None:
            return False
        homes = self.homes
        h = homes.home_of(self.player_name)
        key = "%d,%d" % (x, y)
        cell = h["cells"].get(key, {})
        c = m.cell(x, y)
        w = self.w
        base = homes.base_of(self.player_name)
        if cell.get("roof"):
            self.refund(cell.pop("roof"))
            m.set_roofs(homes.roof_cells(h, m))
        elif key in h["objects"]:
            name = h["objects"].pop(key)
            w.remove_entity(homes.object_at(m, x, y))
            w.objects_dirty.add(m.name)
            self.refund(name)
        elif (m.name, x, y) in w.farms.plots:
            w.farms.clear(m, x, y)
            self.display_message("You pull up the crop.", "INFO")
        elif m.decor[c]:
            head = bed_head_of(x, y, m.decor[c])
            if head and m.inside(head[1], head[2]) and m.decor[m.cell(head[1], head[2])] == head[0]:
                return self.unbuild(head[1], head[2])                       # (a bed's foot: the bed comes down)
            foot = bed_foot_of(x, y, m.decor[c])
            if foot and m.inside(foot[1], foot[2]) and m.decor[m.cell(foot[1], foot[2])] == foot[0]:
                key2 = "%d,%d" % foot[1:]
                there = h["cells"].get(key2, {})
                if there.pop("decor", None) is None and key2 not in h["cleared"]:   # (the map's own bed's foot)
                    h["cleared"].append(key2)
                if not there:
                    h["cells"].pop(key2, None)
                w.change_tile(m, foot[1], foot[2], "%s+Decor()" % m.tile[m.cell(foot[1], foot[2])])
            if cell.get("decor"):
                self.refund(cell.pop("decor"))
            elif key not in h["cleared"]:
                h["cleared"].append(key)
                self.display_message("You clear the %s away." % pretty_tile(m.decor[c]), "INFO")
            self.forget_regrowth(m, x, y)
            w.change_tile(m, x, y, "%s+Decor()" % m.tile[c])
            self.join_fences(m, h, x, y)
        elif m.under[c]:                                   # (then the rug under it)
            if cell.get("under"):
                self.refund(cell.pop("under"))
            w.change_tile(m, x, y, "%s+Under()" % m.tile[c])
        elif cell.get("tile"):
            self.refund(cell.pop("tile"))
            self.forget_regrowth(m, x, y)
            w.change_tile(m, x, y, base.tile[base.cell(x, y)], keep_decor=True)
        else:
            self.display_message("There's nothing there to take down.", "INFO")
            return False
        if not cell:
            h["cells"].pop(key, None)
        else:
            h["cells"][key] = cell
        self.play_sound("Pickup")
        return True


def pretty_item(name):
    return name.replace("_", " ").replace("(s)", "s")


def pretty_tile(name):
    return strip_digits(name).replace("_", " ").lower()
