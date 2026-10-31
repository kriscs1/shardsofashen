"""The Maps page's Terrains window: the terrains its big brushes paint (data\\TileSets.ini, Kind=Terrain), each its
ground tiles, the decor and creatures scattered over it (a weight after *: Tree001*30 comes up thirty times as often
as Bush001*1) and how thick they lie. Saved to TileSets.ini when OK is pressed."""
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from . import terrain as TR
from .project import IniDoc
from .widgets import Dialog, PickerDialog, Tooltip, ask_text

FIELDS = (("Title", "Title", "What it's called (the palette's name for it)."),
          ("Tiles", "Ground", "Its ground tiles, mixed: Grass001*6,Grass002*1."),
          ("Decor", "Decor", "Decor scattered over it: Tree001*30,Bush001*4."),
          ("Decor.Density", "Decor in 100", "How many of a hundred of its tiles get decor."),
          ("Entities", "Creatures", "Creatures (or objects) scattered too: Rabbit*3,Butterfly*2."),
          ("Entities.Density", "Creatures in 100", "How many of a hundred of its tiles get one."),
          ("Face", "Wall's face", "A wall only (cave rock): what its rock shows where open ground lies south of it: "
                                  "Cave_Wall002*12,Cave_Wall003*1."))


class TerrainsDialog(Dialog):
    def __init__(self, parent, project):
        super().__init__(parent, "Terrains", ok="Save")
        self.project = project
        self.ini = IniDoc(project.p("data", "TileSets.ini"))
        self.cur = None
        b = self.body
        left = ttk.Frame(b, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.list = tk.Listbox(left, height=18, width=22, exportselection=False, font=T.FONT, bg=T.FIELD,
                               relief="solid", bd=1)
        self.list.pack(fill="y", expand=True)
        self.list.bind("<<ListboxSelect>>", lambda e: self.show())
        row = ttk.Frame(left, style="Panel.TFrame")
        row.pack(fill="x", pady=(6, 0))
        ttk.Button(row, text="＋ New", style="Small.TButton", command=self.new).pack(side="left")
        ttk.Button(row, text="Delete", style="Small.TButton", command=self.delete).pack(side="left", padx=4)
        form = ttk.Frame(b, style="Panel.TFrame")
        form.grid(row=0, column=1, sticky="nsew")
        self.vars = {}
        for i, (key, label, tip) in enumerate(FIELDS):
            lab = ttk.Label(form, text=label, style="Panel.TLabel")
            lab.grid(row=i, column=0, sticky="w", pady=3)
            v = self.vars[key] = tk.StringVar()
            w = ttk.Entry(form, textvariable=v, width=10 if "Density" in key else 54)
            w.grid(row=i, column=1, sticky="w" if "Density" in key else "ew", pady=3)
            Tooltip(w, tip)
            if key in ("Tiles", "Decor", "Entities", "Face"):
                ttk.Button(form, text="＋", width=3, style="Small.TButton",
                           command=lambda k=key: self.add_to(k)).grid(row=i, column=2, padx=(4, 0))
        self.water = tk.BooleanVar()
        ttk.Checkbutton(form, text="Water (its coasts get their diagonal pieces)", variable=self.water).grid(
            row=len(FIELDS), column=1, sticky="w", pady=(4, 0))
        ttk.Label(form, text="A weight after * says how often each comes up (Tree001*30 thirty times as often as "
                             "Bush001*1). Painting rolls the decor and creatures afresh on each tile, and takes off "
                             "what another terrain scattered there; what was put down by hand stays.",
                  style="PanelMuted.TLabel", wraplength=T.px(480)).grid(row=len(FIELDS) + 1, column=1, sticky="w",
                                                                      pady=(10, 0))
        form.columnconfigure(1, weight=1)
        self.fill_list()
        if self.list.size():
            self.list.selection_set(0)
            self.show()

    def sections(self):
        return [s for s in self.ini.sections() if self.ini.get(s, "Kind", "").strip().lower() == "terrain"]

    def fill_list(self):
        self.list.delete(0, "end")
        for s in self.sections():
            self.list.insert("end", s[8:] if s.startswith("Terrain_") else s)

    def keep(self):
        """The form back into the file's text (not saved yet)."""
        if self.cur is None or not self.ini.has_section(self.cur):
            return
        for key, _, _ in FIELDS:
            self.ini.set(self.cur, key, " ".join(self.vars[key].get().split()))
        self.ini.set(self.cur, "Water", "1" if self.water.get() else "")

    def show(self):
        self.keep()
        sel = self.list.curselection()
        if not sel:
            return
        self.cur = self.sections()[sel[0]]
        for key, _, _ in FIELDS:
            self.vars[key].set(self.ini.get(self.cur, key, ""))
        self.water.set(self.ini.get(self.cur, "Water", "0") == "1")

    def add_to(self, key):
        P = self.project
        if key == "Entities":
            items = [(e, e, P.entity_type(e)) for e in P.placeable() if P.entity_type(e) in ("NPC", "StaticObject")]
        else:
            test = TR.layer_test(P, "decor" if key == "Decor" else "map")
            items = [(t, t, "Decor" if key == "Decor" else "Ground") for t in P.tiles() if test(t)]
        r = PickerDialog(self, "Add to %s" % key, items).run()
        if r:
            v = self.vars[key].get().strip()
            self.vars[key].set((v + "," if v else "") + r + "*1")

    def new(self):
        name = ask_text(self, "New terrain", "Its name (one word, e.g. Heath):")
        name = "_".join((name or "").split())
        if not name:
            return
        sec = "Terrain_" + name
        if self.ini.has_section(sec):
            messagebox.showinfo("Terrains", "There's a terrain %s already." % name, parent=self)
            return
        self.keep()
        self.cur = None
        for k, v in (("Title", name.replace("_", " ").lower()), ("Kind", "Terrain"), ("Tiles", "Grass001")):
            self.ini.set(sec, k, v)
        self.fill_list()
        i = self.sections().index(sec)
        self.list.selection_clear(0, "end")
        self.list.selection_set(i)
        self.show()

    def delete(self):
        if self.cur is None or not messagebox.askyesno("Terrains", "Delete the terrain %s?" % self.cur, parent=self):
            return
        self.ini.remove_section(self.cur)
        self.cur = None
        self.fill_list()

    def ok(self):
        self.keep()
        self.ini.save()
        return True
