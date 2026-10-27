"""Quests: data\\Quests.ini. A quest's Attribute goes 0, 1, 2 ... Done; StageN is what the journal says while it is N,
and MarkerN where the minimap's crosses are then: a place's ID (an Id on a map tile, or a thing's Id=), or the old
map tile-x tile-y; several joined with ;."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from .iniform import IniFormPage


class QuestPage(IniFormPage):
    title = "Quests"
    icon = "❖"
    kind = "quest"
    ini_attr = "quests_ini"
    new_label = "New quest"
    MAX_STAGES = 12

    def list_items(self):
        return [(s, s, "") for s in self.ini.sections()]

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)
        self.name_label = ttk.Label(f, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.grid(row=0, column=0, columnspan=4, sticky="w")
        r = 1
        self.section_label(f, r, "The quest")
        r += 1
        giver = ttk.Frame(f, style="Panel.TFrame")
        self.giver = self.var("Giver")
        ttk.Combobox(giver, textvariable=self.giver, values=[""] + self.project.npcs(), width=22).pack(side="left")
        self.giver_link = ttk.Label(giver, text="", style="Link.TLabel", cursor="hand2")
        self.giver_link.pack(side="left", padx=8)
        self.giver_link.bind("<Button-1>", lambda e: self.giver.get() and self.app.goto("entity", self.giver.get()))
        self.row(f, r, "Given by", giver, "The NPC who gives it.", span=3)
        r += 1
        self.attr = self.var("Attribute")
        self.row(f, r, "Attribute", ttk.Combobox(f, textvariable=self.attr, values=self.project.attributes(), width=22),
                 "The save attribute that tracks it: scripts set it with Update.Attribute.")
        self.row(f, r, "Done at", ttk.Spinbox(f, textvariable=self.var("Done"), from_=1, to=50, width=6),
                 "The attribute's value that means finished.", col=2)
        r += 1
        self.scripts_box = self.links(f, r, "Scripts that set it", [])
        r += 1
        self.section_label(f, r, "Main story and what it needs")
        r += 1
        self.row(f, r, "Story", ttk.Combobox(f, textvariable=self.var("Type"), values=["", "Main"], width=10,
                                             state="readonly"),
                 "Main: part of the main story (first in the journal, with a gold badge). Blank: a side quest.")
        self.row(f, r, "Chapter", ttk.Spinbox(f, textvariable=self.var("Chapter"), from_=0, to=50, width=6),
                 "Its place in the main story (1, 2, 3...).", col=2)
        r += 1
        self.row(f, r, "Needs level", ttk.Spinbox(f, textvariable=self.var("Requires.Level"), from_=0, to=50, width=6),
                 "The player's level (the average of their best two of Strength, Defence and Magic: Config.ini "
                 "Level.Skills, Level.Best) before the giver will offer it. Blank or 0: any.")
        self.row(f, r, "Needs skills", ttk.Entry(f, textvariable=self.var("Requires.Skills"), width=26),
                 "Skill levels, e.g. Woodcutting 10, Potion Making 5.", col=2)
        r += 1
        qf = ttk.Frame(f, style="Panel.TFrame")
        self.requires_quests = self.var("Requires.Quests")
        ttk.Entry(qf, textvariable=self.requires_quests, width=60).pack(side="left", fill="x", expand=True)
        self.add_req = ttk.Combobox(qf, values=self.ini.sections(), width=24, state="readonly")
        self.add_req.pack(side="left", padx=4)
        ttk.Button(qf, text="＋ Add", style="Small.TButton", command=self.add_required_quest).pack(side="left")
        self.row(f, r, "Needs quests", qf, "Quests that must be finished first (joined with ;). The giver's script "
                                           "checks with >Quest.Can.Start, and says what's missing.", span=3)
        r += 1
        self.section_label(f, r, "Stages (what the journal says) and minimap markers")
        r += 1
        ttk.Label(f, text="Stage 0 is shown before it starts (blank: hidden until then). $Name in the text is that "
                          "attribute's value. Markers: a place's ID (name a tile in Maps), several joined with ;",
                  style="PanelMuted.TLabel", wraplength=760).grid(row=r, column=0, columnspan=4, sticky="w")
        r += 1
        self.stage_rows = []
        for n in range(self.MAX_STAGES):
            sv, mv = self.var("Stage%d" % n), self.var("Marker%d" % n)
            lab = ttk.Label(f, text="Stage %d" % n, style="Panel.TLabel", font=T.FONT_BOLD)
            lab.grid(row=r, column=0, sticky="nw", pady=(6, 0))
            e = ttk.Entry(f, textvariable=sv)
            e.grid(row=r, column=1, columnspan=3, sticky="ew", pady=(6, 0))
            r += 1
            mk = ttk.Frame(f, style="Panel.TFrame")
            mk.grid(row=r, column=1, columnspan=3, sticky="ew")
            ttk.Label(mk, text="marker", style="PanelMuted.TLabel").pack(side="left")
            ttk.Entry(mk, textvariable=mv, width=40).pack(side="left", padx=4, fill="x", expand=True)
            ttk.Button(mk, text="＋ the Maps tile", style="Small.TButton",
                       command=lambda m=mv: self.add_marker(m)).pack(side="left")
            ttk.Button(mk, text="＋ Place…", style="Small.TButton",
                       command=lambda m=mv: self.add_place(m)).pack(side="left", padx=(3, 0))
            ttk.Button(mk, text="Show", style="Small.TButton", command=lambda m=mv: self.show_marker(m)).pack(
                side="left", padx=3)
            r += 1
            self.stage_rows.append((lab, e, mk))

    def after_load(self):
        self.name_label.configure(text=self.key or "")
        g = self.giver.get()
        self.giver_link.configure(text=("Open %s" % g) if g else "")
        if not self.key:
            return
        attr = self.attr.get().strip()
        scripts = []
        if attr:
            from ..project import read_text_lines
            for s in self.project.scripts():
                try:
                    if any(("\t%s\t" % attr) in l or ("$Attr.%s" % attr) in l for l in
                           read_text_lines(self.project.script_path(s))):
                        scripts.append(s)
                except OSError:
                    pass
        self.fill_links(self.scripts_box, [(s, lambda s=s: self.app.goto("script", s)) for s in scripts], "none")

    def on_change(self, key):
        if key == "Giver":
            g = self.giver.get()
            self.giver_link.configure(text=("Open %s" % g) if g else "")

    def add_required_quest(self):
        q = self.add_req.get().strip()
        if not q or q == self.key:
            return
        have = [x.strip() for x in self.requires_quests.get().split(";") if x.strip()]
        if q not in have:
            self.requires_quests.set("; ".join(have + [q]))

    def add_marker(self, var):
        """The tile selected in Maps: its place ID if it has one (or one there is named now), else map x y."""
        mp = self.app.page_of("map")
        spot = mp.selected_spot() if hasattr(mp, "selected_spot") else None
        if not spot:
            self.app.status("Pick a tile in Maps first (click it), then come back here.", "warn")
            return
        name = next((e.name for e in mp.doc.placed() if e.kind == "Id" and (e.x, e.y) == spot[1:]), None)
        if name is None:
            name = mp.ask_place_name("", "Name tile %d,%d of %s for the marker" % (spot[1], spot[2], spot[0]))
            if name is None:
                return
            from ..project import Entity
            mp.remember()
            mp.doc.entities.append(Entity("Id", name, spot[1], spot[2]))
            mp.redraw()
            self.app.status("Named the tile %s: save the map in Maps too." % name, "ok")
        self.append_marker(var, name)

    def add_place(self, var):
        from ..widgets import PickerDialog
        places = sorted(self.project.places().values(), key=lambda v: v[0].lower())
        items = [(v[0], v[0], "%s %d,%d%s" % (v[1], v[2], v[3], "" if v[4] == "tile" else " (" + v[4] + ")"))
                 for v in places]
        r = PickerDialog(self, "A place for the marker", items).run()
        if r:
            self.append_marker(var, r)

    @staticmethod
    def append_marker(var, text):
        cur = var.get().strip()
        var.set((cur + ";" if cur else "") + text)

    def show_marker(self, var):
        first = var.get().split(";")[0].split()
        if len(first) == 1:
            self.app.goto("place", first[0])
        elif len(first) == 3:
            try:
                self.app.goto("map", first[0], tile=(int(first[1]), int(first[2])))
            except ValueError:
                pass

    def init_new(self, name):
        self.ini.set(name, "Attribute", name.replace(" ", "").replace("'", "") + "Quest")
        self.ini.set(name, "Stage0", "")
        self.ini.set(name, "Done", "2")

    def validate(self):
        d = self.vars["Done"].get().strip()
        if d and not d.isdigit():
            return "Done should be a whole number."
        for k in ("Chapter", "Requires.Level"):
            v = self.vars[k].get().strip()
            if v and not v.isdigit():
                return "%s should be a whole number." % k
        names = {n.lower() for n in self.ini.sections()}
        for q in [x.strip() for x in self.requires_quests.get().split(";") if x.strip()]:
            if q.lower() not in names:
                return "There's no quest called %r." % q
        w = self.vars["Requires.Skills"].get().replace(",", " ").split()
        if len(w) % 2 or not all(x.isdigit() for x in w[1::2]):
            return "Needs skills should be pairs: a skill and a level, e.g. Woodcutting 10."
        return ""
