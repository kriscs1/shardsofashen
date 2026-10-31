"""Entities: data\\Entities.ini, one section per sprite in sprites\\Entities: items, objects and NPCs."""
import tkinter as tk
from tkinter import ttk

from PIL import Image

from .. import theme as T
from ..project import SLOTS, ENTITY_TYPES
from ..widgets import photo, VerbPicker, Dialog, picker_field
from .iniform import IniFormPage


class DropsDialog(Dialog):
    """Drops=Item,min-max,percent ... as rows."""

    def __init__(self, parent, project, text):
        super().__init__(parent, "What it drops")
        self.project = project
        b = self.body
        for i, h in enumerate(("Item", "Min", "Max", "Chance %")):
            ttk.Label(b, text=h, style="Head.TLabel").grid(row=0, column=i, sticky="w", padx=2)
        self.rows = []
        self.frame = b
        for d in text.split():
            p = d.split(",")
            mn, mx = (p[1].split("-") + [p[1]])[:2] if len(p) > 1 else ("1", "1")
            self.add(p[0], mn, mx, p[2] if len(p) > 2 else "100")
        ttk.Button(b, text="+ Add a drop", style="Small.TButton", command=lambda: self.add()).grid(
            row=99, column=0, sticky="w", pady=(6, 0))

    def add(self, item="", mn="1", mx="1", pct="100"):
        r = len(self.rows) + 1
        vs = [tk.StringVar(value=v) for v in (item, mn, mx, pct)]
        ws = [ttk.Combobox(self.frame, textvariable=vs[0], values=self.project.items(), width=22)]
        ws += [ttk.Spinbox(self.frame, textvariable=v, from_=0, to=1000, width=6) for v in vs[1:3]]
        ws.append(ttk.Spinbox(self.frame, textvariable=vs[3], from_=0, to=100, width=6))
        for i, w in enumerate(ws):
            w.grid(row=r, column=i, padx=2, pady=2)
        x = ttk.Button(self.frame, text="✕", width=3, style="Small.TButton")
        x.grid(row=r, column=4)
        row = (vs, ws + [x])
        x.configure(command=lambda: self.remove(row))
        self.rows.append(row)

    def remove(self, row):
        for w in row[1]:
            w.destroy()
        self.rows.remove(row)

    def ok(self):
        out = []
        for vs, _ in self.rows:
            item, mn, mx, pct = (v.get().strip() for v in vs)
            if item:
                out.append("%s,%s-%s,%s" % (item, mn or "1", mx or mn or "1", pct or "100"))
        return " ".join(out)


class RequiresDialog(Dialog):
    """Requires=Skill level Skill level."""

    def __init__(self, parent, project, text):
        super().__init__(parent, "Needed to equip")
        self.project, self.rows = project, []
        w = text.split()
        pairs = [(w[i], w[i + 1]) for i in range(0, len(w) - 1, 2)]
        ttk.Label(self.body, text="Skill and level needed to equip it", style="Head.TLabel").grid(row=0, column=0,
                                                                                                    columnspan=3)
        for s, l in pairs:
            self.add(s, l)
        ttk.Button(self.body, text="+ Add", style="Small.TButton", command=lambda: self.add()).grid(row=99, column=0,
                                                                                                    sticky="w")

    def add(self, skill="", level="1"):
        r = len(self.rows) + 1
        a, b = tk.StringVar(value=skill), tk.StringVar(value=level)
        ws = [ttk.Combobox(self.body, textvariable=a, values=[s.replace(" ", "") for s in self.project.skills],
                           width=16, state="readonly"),
              ttk.Spinbox(self.body, textvariable=b, from_=1, to=99, width=6)]
        for i, w in enumerate(ws):
            w.grid(row=r, column=i, padx=2, pady=2)
        self.rows.append((a, b))

    def ok(self):
        return " ".join("%s %s" % (a.get(), b.get()) for a, b in self.rows if a.get())


class EntityPage(IniFormPage):
    title = "Entities"
    icon = "♟"
    kind = "entity"
    ini_attr = "entities_ini"
    kinds = ENTITY_TYPES + ["No data yet"]
    list_icons = True
    allow_new = False

    def list_items(self):
        out = []
        for e in self.project.placeable():
            if self.project.is_decor_object(e):           # (a decor tile placed as an object: edited in Tiles)
                continue
            out.append((e, e, self.project.entity_type(e) if self.ini.has_section(e) else "No data yet"))
        return out

    def list_icon(self, key):
        return photo(self.project.sprite("Entities", key), (32, 32), key=("ent", key))

    def build_form(self, f):
        f.columnconfigure(4, weight=1)          # (the boxes keep their own widths; the space goes to the right)
        top = ttk.Frame(f, style="Panel.TFrame")
        top.grid(row=0, column=0, columnspan=5, sticky="ew")
        self.preview = tk.Label(top, bg=T.FIELD, relief="solid", bd=1)
        self.preview.pack(side="left")
        info = ttk.Frame(top, style="Panel.TFrame", padding=(16, 0, 0, 0))
        info.pack(side="left", fill="both", expand=True)
        self.name_label = ttk.Label(info, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(anchor="w")
        self.sub_label = ttk.Label(info, text="", style="PanelMuted.TLabel")
        self.sub_label.pack(anchor="w", pady=(0, 8))
        self.used = {}
        for what in ("Placed on", "Sold / made in", "Dropped by", "Mentioned in scripts"):
            row = ttk.Frame(info, style="Panel.TFrame")
            row.pack(anchor="w", fill="x", pady=1)
            ttk.Label(row, text=what, style="Panel.TLabel", font=T.FONT_BOLD, width=18).pack(side="left", anchor="n")
            box = ttk.Frame(row, style="Panel.TFrame")
            box.pack(side="left", fill="x", expand=True)
            self.used[what] = box

        r = 1
        self.section_label(f, r, "General")
        r += 1
        self.type_var = self.var("Type")
        self.row(f, r, "Type", ttk.Combobox(f, textvariable=self.type_var, values=ENTITY_TYPES, state="readonly",
                                            width=16),
                 "What the Map Editor places it as: an item you can pick up, an object, or an NPC.")
        r += 1
        uw = ttk.Frame(f, style="Panel.TFrame")
        self.use_words = self.var("Use.Words")
        ttk.Entry(uw, textvariable=self.use_words, width=34).pack(side="left")
        ttk.Button(uw, text="Pick verbs…", style="Small.TButton", command=self.pick_verbs).pack(side="left", padx=4)
        self.row(f, r, "Use words", uw, "The first is the left-click action. Wield / Wear come by themselves for "
                                        "equipment.", span=3)
        r += 1
        self.row(f, r, "Examine text", ttk.Entry(f, textvariable=self.var("Examine.Info"), width=70), span=3)
        r += 1

        self.groups = {}
        g = self.group(f, r, "Item", "MapItem")
        r += 1
        self.row(g, 0, "Value (gold)", ttk.Spinbox(g, textvariable=self.var("Value"), from_=0, to=100000, width=8))
        self.row(g, 0, "Stack up to", ttk.Spinbox(g, textvariable=self.var("Stackable"), from_=0, to=100000, width=8),
                 "Most per inventory slot (blank or 1 = not stackable).", col=2)
        self.row(g, 1, "Heals when eaten", ttk.Spinbox(g, textvariable=self.var("Food.Value"), from_=0, to=1000,
                                                       width=8))
        self.row(g, 1, "", ttk.Checkbutton(g, text="Can be dropped", variable=self.var("Droppable", "bool", "1")),
                 col=2)
        self.row(g, 3, "", ttk.Checkbutton(g, text="Only once (never respawns)", variable=self.var("Once", "bool", "0")),
                 "Every one placed on a map is picked up once and never comes back.", col=2)
        self.row(g, 3, "Seed of crop", ttk.Combobox(g, textvariable=self.var("Crop"),
                                                    values=[""] + self.project.crops_ini.sections(), width=18),
                 "A seed: the data\\Crops.ini crop it grows into when used on tilled soil (see the Crops section).")
        self.row(g, 4, "Kept when you die", ttk.Combobox(g, textvariable=self.var("Keep.On.Death"),
                                                         values=["", "1", "0"], width=6),
                 "1: always kept when the player dies. 0: never (it can go in the grave). Blank: kept if it can't be "
                 "dropped. (Besides this, players keep their 5 most valuable things.)")
        self.row(g, 2, "Casts spell", ttk.Combobox(g, textvariable=self.var("Spell"),
                                                   values=[""] + self.project.spells_ini.sections(), width=18),
                 "A scroll or potion: the data\\Spells.ini section it casts (give it Use.Words=Cast or Drink).")
        self.row(g, 2, "Respawn (s)", ttk.Spinbox(g, textvariable=self.var("Respawn"), from_=0, to=100000, width=8),
                 "Items: seconds before one picked up off a map comes back (blank = by its value). NPCs: seconds "
                 "before it respawns.", col=2)

        g = self.group(f, r, "Equipment", "MapItem")
        r += 1
        self.slot_var = self.var("Slot")
        self.row(g, 0, "Slot", ttk.Combobox(g, textvariable=self.slot_var, values=[""] + SLOTS, state="readonly",
                                            width=12), "Blank = not equippable.")
        req = ttk.Frame(g, style="Panel.TFrame")
        self.requires = self.var("Requires")
        ttk.Entry(req, textvariable=self.requires, width=20).pack(side="left")
        ttk.Button(req, text="…", width=3, style="Small.TButton", command=self.pick_requires).pack(side="left", padx=3)
        self.row(g, 0, "Needs", req, "Skill and level to equip it, e.g. Strength 5 Defence 10.", col=2)
        self.row(g, 1, "Attack +", ttk.Spinbox(g, textvariable=self.var("Attack"), from_=0, to=100, width=8))
        self.defence = self.var("Defence")
        self.row(g, 1, "Defence +", ttk.Spinbox(g, textvariable=self.defence, from_=0, to=100, width=8), col=2)
        self.row(g, 2, "Magic +", ttk.Spinbox(g, textvariable=self.var("Magic"), from_=0, to=100, width=8),
                 "Staffs: added to every spell's damage and healing.")
        self.row(g, 2, "Bow range", ttk.Spinbox(g, textvariable=self.var("Range"), from_=0, to=1000, width=8),
                 "Bows: how far it shoots (pixels).", col=2)
        self.row(g, 3, "Ammo", ttk.Combobox(g, textvariable=self.var("Ammo"), values=[""] + self.project.items(),
                                            width=18), "Bows: the item each shot uses.")

        g = self.group(f, r, "NPC: fighting", "NPC")
        r += 1
        self.row(g, 3, "Attitude", ttk.Combobox(g, textvariable=self.var("Attitude"), values=["", "Good", "Bad", "Passive"],
                                                state="readonly", width=8),
                 "Good = friendly (Talk to), Bad = a foe (Attack). Each map line can say its own.", col=2)
        nums = (("Hitpoints", "Hitpoints"), ("Strength", "Strength"), ("Defence", None), ("Attack speed", "Attack.Speed"),
                ("Movement speed", "Movement.Speed"), ("Aggro range", "Aggro.Range"), ("Weapon range", "Weapon.Range"))
        for i, (label, key) in enumerate(nums):
            v = self.defence if key is None else self.var(key)
            self.row(g, i // 2, label, ttk.Spinbox(g, textvariable=v, from_=0, to=10000, increment=1, width=8),
                     col=(i % 2) * 2)
        self.row(g, 4, "", ttk.Checkbutton(g, text="Aggressive (a Bad one attacks on sight)",
                                           variable=self.var("Aggressive", "bool", "0")), span=3)
        drops = ttk.Frame(g, style="Panel.TFrame")
        self.drops = self.var("Drops")
        ttk.Entry(drops, textvariable=self.drops, width=58).pack(side="left")
        ttk.Button(drops, text="Edit…", style="Small.TButton", command=self.pick_drops).pack(side="left", padx=3)
        self.row(g, 5, "Drops", drops, "Item,min-max,percent ...", span=3)
        effects = lambda: [(n, n, "") for n in self.effect_names()]
        self.row(g, 6, "Shoots", picker_field(g, self.var("Missile"), "Missile", effects), "A sprites\\Effects missile.")
        self.row(g, 6, "Impact", picker_field(g, self.var("Missile.Impact"), "Impact", effects), col=2)
        sounds = [""] + [s for s in self.project.sounds()]
        self.row(g, 7, "Shot sound", ttk.Combobox(g, textvariable=self.var("Missile.Sound"), values=sounds, width=18))
        self.row(g, 7, "Death sound", ttk.Combobox(g, textvariable=self.var("Kill.Sound"), values=sounds, width=18),
                 col=2)

        g = self.group(f, r, "NPC: moving about", "NPC")
        r += 1
        self.row(g, 0, "Default roam", ttk.Spinbox(g, textvariable=self.var("Roam.Radius"), from_=0, to=50, width=6),
                 "Only for the NPCs with no roam box drawn on the map (the Maps inspector's \"Draw on the map\"): "
                 "tiles it wanders from where it's placed (0 = stands still).")
        self.row(g, 0, "Default chase", ttk.Spinbox(g, textvariable=self.var("Chase.Radius"), from_=0, to=50, width=6),
                 "Only for the NPCs with no chase box drawn on the map: tiles beyond its roam area it follows you.",
                 col=2)
        ttk.Label(g, text="tiles · used only where no box is drawn on the map", style="PanelMuted.TLabel").grid(
            row=0, column=4, sticky="w", padx=(8, 0))
        self.row(g, 1, "Walk speed", ttk.Combobox(g, textvariable=self.var("Walk.Speed"),
                                                  values=["", "0.25", "0.4", "0.5", "0.6", "0.75", "1"], width=8),
                 "A fraction of Movement speed, when roaming, patrolling or going back.")
        self.row(g, 1, "Pause (s)", ttk.Entry(g, textvariable=self.var("Pause"), width=10),
                 "min-max seconds between moves, e.g. 2-5.", col=2)
        self.row(g, 2, "", ttk.Checkbutton(g, text="Solid (you bump into it, and it into you)",
                                           variable=self.var("Solid", "bool", "1")),
                 "Untick for something small you walk over (a rabbit, a duck).", span=3)

        g = self.group(f, r, "NPC: daily life", "NPC")      # (its kind's: a map line's options can say otherwise)
        r += 1
        self.row(g, 0, "Hours", ttk.Combobox(g, textvariable=self.var("Schedule"), values=["", "Day", "Night"],
                                             width=8),
                 "Day: out by day, home at night (townsfolk walk to a door; creatures with a Roost go to it). Night: "
                 "hidden by day. Blank: always out. One placed on a map can have its own (the Maps inspector's "
                 "Hours).")
        self.row(g, 0, "", ttk.Checkbutton(g, text="Flees (prey: runs, never fights back)",
                                           variable=self.var("Flees", "bool", "0")), col=2)
        self.row(g, 1, "", ttk.Checkbutton(g, text="Goes indoors (untick: an animal that stays out of houses)",
                                           variable=self.var("Indoors", "bool", "1")), span=3)
        self.row(g, 2, "Rests as", ttk.Entry(g, textvariable=self.var("States"), width=16),
                 "How it may rest when it stops: Sit, Lie, Curl (commas between). A cat sits before it lies down.")
        self.row(g, 2, "Fidgets", ttk.Entry(g, textvariable=self.var("Fidgets"), width=16),
                 "A moment's pose now and then (Stretch).", col=2)
        self.row(g, 3, "Hunts", ttk.Entry(g, textvariable=self.var("Hunts"), width=16),
                 "The NPCs it goes after: Rabbit,Sheep (All: any that can be fought).")
        self.row(g, 3, "Calls", ttk.Combobox(g, textvariable=self.var("Calls"), values=sounds, width=16),
                 "A sound it makes now and then (a frog's croak), heard from close by.", col=2)
        self.row(g, 4, "Sight (°)", ttk.Spinbox(g, textvariable=self.var("Sight.Cone"), from_=0, to=360, width=6),
                 "How wide it sees (360: all round). One placed on a map can look one way (Faces) as a lookout.")
        self.row(g, 4, "Hearing", ttk.Spinbox(g, textvariable=self.var("Hearing"), from_=0, to=5, increment=0.1,
                                              width=6),
                 "How far your noise carries to it (a bat 2, a skeleton 0.6).", col=2)
        self.row(g, 5, "", ttk.Checkbutton(g, text="Swims (at home in the water too)",
                                           variable=self.var("Swims", "bool", "0")), span=3)

        g = self.group(f, r, "Object", "StaticObject")
        r += 1
        fp = ttk.Frame(g, style="Panel.TFrame")
        self.fp_canvas = tk.Canvas(fp, width=T.px(160), height=T.px(160), bg="#222", highlightthickness=1,
                                   highlightbackground=T.LINE, cursor="crosshair")
        self.fp_canvas.pack(side="left")
        self.fp_canvas.bind("<Button-1>", self.fp_start)
        self.fp_canvas.bind("<B1-Motion>", self.fp_drag)
        side = ttk.Frame(fp, style="Panel.TFrame", padding=(10, 0, 0, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text="Footprint: click or drag on it. Red can't be walked through; none red = you walk "
                             "through it.", style="PanelMuted.TLabel", wraplength=T.px(220)).pack(anchor="w")
        for text, which in (("Bottom half", "bottom"), ("Block all", "all"), ("Walk through", "none")):
            ttk.Button(side, text=text, style="Small.TButton",
                       command=lambda w=which: self.fp_preset(w)).pack(anchor="w", pady=(4, 0))
        self.fp_size_label = ttk.Label(side, text="", style="PanelMuted.TLabel")
        self.fp_size_label.pack(anchor="w", pady=(6, 0))
        self.footprint = self.var("Walkable.Data")
        self.row(g, 0, "", fp, span=4)
        self.row(g, 1, "Drawn", ttk.Combobox(g, textvariable=self.var("Layer"), values=["", "Under", "Over"],
                                             state="readonly", width=10),
                 "Under = under the player (something you step over); Over = it flies.", col=2)
        self.row(g, 2, "Animation frames", ttk.Spinbox(g, textvariable=self.var("Anim.Frames"), from_=0, to=16,
                                                       width=8),
                 "It animates where it stands, cycling sprites <Name>1..N.")
        self.row(g, 2, "ms per frame", ttk.Spinbox(g, textvariable=self.var("Anim.Speed"), from_=30, to=5000,
                                                   increment=10, width=8), col=2)
        self.row(g, 3, "Light at night", ttk.Spinbox(g, textvariable=self.var("Light"), from_=0, to=400, increment=2,
                                                     width=8),
                 "How far (pixels) it lights the dark round it (a fire, a range). Blank = it doesn't.")

    def group(self, f, r, title, applies):
        g = ttk.LabelFrame(f, text=title, padding=10)
        g.grid(row=r, column=0, columnspan=5, sticky="ew", pady=(10, 0))
        g.columnconfigure(5, weight=1)
        self.groups[title] = (g, applies)
        return g

    def effect_names(self):
        import os
        d = self.project.p("sprites", "Effects")
        return sorted({f[:-4] for f in os.listdir(d) if f.lower().endswith((".png", ".bmp"))}) if os.path.isdir(d) else []

    # --- after loading / on change: which groups apply, the preview, where it's used
    def after_load(self):
        self.name_label.configure(text=self.key or "")
        self.apply_groups()
        self.show_preview()
        self.fp_draw()
        if not self.key:
            return
        ix = self.project.index()
        places = ix["entity"].get(self.key, {})
        self.fill_links(self.used["Placed on"], [(m, lambda m=m, xy=xy: self.app.goto("map", m, tile=xy))
                                                 for m, xy in sorted(places.items())], "no map")
        self.fill_links(self.used["Sold / made in"], [(rk, lambda rk=rk: self.app.goto("rack", rk))
                                                      for rk in sorted(set(ix["item_rack"].get(self.key, [])))], "none")
        self.fill_links(self.used["Dropped by"], [(n, lambda n=n: self.app.goto("entity", n))
                                                  for n in sorted(set(ix["drops"].get(self.key, [])))], "nothing")
        self.fill_links(self.used["Mentioned in scripts"], [(s, lambda s=s: self.app.goto("script", s))
                                                            for s in sorted(set(ix["script_mention"].get(self.key, [])))],
                        "none")

    def apply_groups(self):
        t = self.type_var.get() or "MapItem"
        has = bool(self.key)
        self.sub_label.configure(text=("%s  ·  %s" % (t, "in Entities.ini" if self.ini.has_section(self.key)
                                                      else "no data yet: saving adds it")) if has else "")
        for title, (g, applies) in self.groups.items():   # only the boxes for its type show
            if has and t == applies:
                g.grid()
            else:
                g.grid_remove()
        g = self.groups["Equipment"][0]                     # and of Equipment, only the Slot until it has one
        if not hasattr(g, "_rows"):
            g._rows = [(c, c.grid_info()) for c in g.winfo_children() if int(c.grid_info().get("row", 0)) > 0]
        for c, info in g._rows:
            if self.slot_var.get():
                c.grid(**{k: v for k, v in info.items() if k != "in"})
            else:
                c.grid_remove()

    def _state(self, w, on):
        try:
            if isinstance(w, (ttk.Entry, ttk.Spinbox, ttk.Checkbutton, ttk.Button)):
                w.state(["!disabled"] if on else ["disabled"])
            elif isinstance(w, ttk.Combobox):
                w.state(["!disabled"] if on else ["disabled"])
        except tk.TclError:
            pass
        for c in w.winfo_children():
            self._state(c, on)

    def on_change(self, key):
        if key in ("Type", "Slot"):
            self.apply_groups()
        if key == "Walkable.Data":
            self.fp_draw()
        if key in ("Anim.Frames",):
            self.show_preview()

    def show_preview(self):
        self._anim = getattr(self, "_anim", None)
        if self._anim:
            self.after_cancel(self._anim)
            self._anim = None
        if not self.key:
            self.preview.configure(image="")
            return
        frames = [self.project.sprite("Entities", self.key)]
        try:
            n = int(self.vars["Anim.Frames"].get() or 0)
        except ValueError:
            n = 0
        if n > 1:
            got = [self.project.sprite("Entities", "%s%d" % (self.key, k)) for k in range(1, n + 1)]
            if all(got):
                frames = got
        frames = [f for f in frames if f is not None]
        if not frames:
            self.preview.configure(image="")
            return
        size = (T.px(128), T.px(128))
        phs = [photo(fr, size, key=("entbig", self.key, i)) for i, fr in enumerate(frames)]
        self._phs = phs

        def step(i=0):
            self.preview.configure(image=phs[i % len(phs)])
            if len(phs) > 1:
                ms = int(self.vars["Anim.Speed"].get() or 220) if self.vars["Anim.Speed"].get().isdigit() else 220
                self._anim = self.after(max(60, ms), lambda: step(i + 1))
        step()

    # --- the footprint (Walkable.Data over the sprite: 7 cells to 32 pixels each way, as a tile's grid)
    def fp_grid(self):
        img = self.project.sprite("Entities", self.key) if self.key else None
        w, h = img.size if img is not None else (self.project.tile_w, self.project.tile_h)
        return max(1, round(w * 7 / self.project.tile_w)), max(1, round(h * 7 / self.project.tile_h))

    def fp_cells(self):
        cols, rows = self.fp_grid()
        data = self.footprint.get().strip()
        return list(data) if len(data) == cols * rows else ["1"] * (cols * rows)

    def fp_geometry(self):
        img = self.project.sprite("Entities", self.key) if self.key else None
        w, h = img.size if img is not None else (self.project.tile_w, self.project.tile_h)
        k = max(1, int(T.px(160) / max(w, h)))
        return img, w * k, h * k

    def fp_draw(self):
        c = self.fp_canvas
        c.delete("all")
        if not self.key:
            return
        img, W, H = self.fp_geometry()
        c.configure(width=W, height=H)
        if img is not None:
            self._fp_ph = photo(img.resize((W, H), Image.NEAREST), key=("entfp", self.key, W))
            c.create_image(0, 0, image=self._fp_ph, anchor="nw")
        cols, rows = self.fp_grid()
        cw, ch = W / cols, H / rows
        for i, v in enumerate(self.fp_cells()):
            x0, y0 = (i % cols) * cw, (i // cols) * ch
            if v == "0":
                c.create_rectangle(x0 + 1, y0 + 1, x0 + cw - 1, y0 + ch - 1, fill="#d23b2e", outline="#7a1d14",
                                   stipple="gray50")
            c.create_rectangle(x0, y0, x0 + cw, y0 + ch, outline="#ffffff", stipple="gray25")
        self.fp_size_label.configure(text="%d x %d cells" % (cols, rows))

    def fp_at(self, e):
        _, W, H = self.fp_geometry()
        cols, rows = self.fp_grid()
        x, y = int(e.x // (W / cols)), int(e.y // (H / rows))
        return y * cols + x if 0 <= x < cols and 0 <= y < rows else None

    def fp_set(self, cells):
        self.footprint.set("" if "0" not in cells else "".join(cells))      # (none blocked: walk through it)
        self.fp_draw()

    def fp_start(self, e):
        i = self.fp_at(e)
        if i is None or not self.key:
            return
        cells = self.fp_cells()
        self._fp_value = "0" if cells[i] == "1" else "1"
        cells[i] = self._fp_value
        self.fp_set(cells)

    def fp_drag(self, e):
        i = self.fp_at(e)
        if i is None or not self.key:
            return
        cells = self.fp_cells()
        if cells[i] != getattr(self, "_fp_value", "0"):
            cells[i] = self._fp_value
            self.fp_set(cells)

    def fp_preset(self, which):
        cols, rows = self.fp_grid()
        if which == "none":
            self.fp_set(["1"] * (cols * rows))
        elif which == "all":
            self.fp_set(["0"] * (cols * rows))
        else:                                       # the lower half: what stands on the ground
            self.fp_set(["0" if i // cols >= rows // 2 else "1" for i in range(cols * rows)])

    # --- builders
    def pick_verbs(self):
        r = VerbPicker(self, self.project, self.use_words.get()).run()
        if r is not None:
            self.use_words.set(r)

    def pick_drops(self):
        r = DropsDialog(self, self.project, self.drops.get()).run()
        if r is not None:
            self.drops.set(r)

    def pick_requires(self):
        r = RequiresDialog(self, self.project, self.requires.get()).run()
        if r is not None:
            self.requires.set(r)

    def validate(self):
        num = ("Value", "Stackable", "Food.Value", "Hitpoints", "Strength", "Defence", "Attack.Speed",
               "Movement.Speed", "Aggro.Range", "Weapon.Range", "Attack", "Magic", "Range", "Respawn",
               "Roam.Radius", "Chase.Radius", "Walk.Speed", "Anim.Frames", "Anim.Speed", "Light")
        for k in num:
            v = self.vars[k].get().strip()
            if v:
                try:
                    float(v)
                except ValueError:
                    return "%s should be a number, not %r." % (k, v)
        w = self.footprint.get().strip()
        if w:
            cols, rows = self.fp_grid()
            if set(w) - {"0", "1"} or len(w) != cols * rows:
                return "The footprint should be %d x %d cells of 0 and 1 (its sprite's size)." % (cols, rows)
        p = self.vars["Pause"].get().strip()
        if p and not all(x.replace(".", "").isdigit() for x in p.split("-")):
            return "Pause should be min-max seconds, e.g. 2-5."
        return ""
