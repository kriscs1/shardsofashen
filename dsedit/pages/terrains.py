"""Terrains: what the Maps page's big brushes paint (data\\TileSets.ini, Kind=Terrain), each its ground tiles, the
decor and creatures scattered over it (a weight after *: Tree001*30 comes up thirty times as often as Bush001*1) and
how thick they lie. The Maps palette's Auto view shows each one as a single entry."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from .. import terrain as TR
from ..render import tile_image
from ..widgets import PickerDialog, photo, ask_text
from .iniform import IniFormPage

FIELDS = (("Title", "Title", "What it's called (the palette's name for it)."),
          ("Tiles", "Ground", "Its ground tiles, mixed: Grass001*6,Grass002*1."),
          ("Decor", "Decor", "Decor scattered over it: Tree001*30,Bush001*4."),
          ("Decor.Density", "Decor in 100", "How many of a hundred of its tiles get decor."),
          ("Entities", "Creatures", "Creatures (or objects) scattered too: Rabbit*3,Butterfly*2."),
          ("Entities.Density", "Creatures in 100", "How many of a hundred of its tiles get one."),
          ("Face", "Wall's face", "A wall only (cave rock): what its rock shows where open ground lies south of it: "
                                  "Cave_Wall002*12,Cave_Wall003*1."))


def is_terrain(ini, sec):
    return ini.get(sec, "Kind", "").strip().lower() == "terrain"


class TerrainPage(IniFormPage):
    title = "Terrains"
    icon = "⛰"
    kind = "terrain"
    ini_attr = "tilesets_ini"
    new_label = "New terrain"
    list_icons = True

    def list_items(self):
        return [(s, s[8:] if s.startswith("Terrain_") else s, "") for s in self.ini.sections()
                if is_terrain(self.ini, s)]

    def list_icon(self, key):
        tiles = TR.weighted(self.ini.get(key, "Tiles", ""))
        img = tile_image(self.project, tiles[0][0]) if tiles else None
        return photo(img, (20, 20), key=("terrain", tiles[0][0])) if img else None

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        self.name_label = ttk.Label(f, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        for i, (key, label, tip) in enumerate(FIELDS):
            narrow = "Density" in key
            w = self.row(f, i + 1, label, ttk.Entry(f, textvariable=self.var(key), width=10 if narrow else 60), tip,
                         span=1)
            if not narrow:
                w.grid_configure(sticky="ew")
            if key in ("Tiles", "Decor", "Entities", "Face"):
                ttk.Button(f, text="＋", width=3, style="Small.TButton",
                           command=lambda k=key: self.add_to(k)).grid(row=i + 1, column=2, padx=(4, 0))
        r = len(FIELDS) + 1
        ttk.Checkbutton(f, text="Water (its coasts get their diagonal pieces)", variable=self.var("Water", "bool", "0")
                        ).grid(row=r, column=1, sticky="w", pady=(4, 0))
        ttk.Label(f, text="A weight after * says how often each comes up (Tree001*30 thirty times as often as "
                          "Bush001*1). Painting rolls the decor and creatures afresh on each tile, and takes off what "
                          "another terrain scattered there; what was put down by hand stays. On the Maps page, pick it "
                          "in the palette's Auto view and paint, fill, or draw an Outline round a place.",
                  style="PanelMuted.TLabel", wraplength=T.px(560)).grid(row=r + 1, column=1, sticky="w", pady=(10, 0))

    def after_load(self):
        self.name_label.configure(text=(self.key[8:] if (self.key or "").startswith("Terrain_") else self.key) or "")

    def extra_save(self):
        if not self.vars["Water"].get():                   # (land: no Water= line at all)
            self.ini.set(self.key, "Water", "")
        return True

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

    def new_item(self):
        if not self.leave_ok():
            return
        name = "_".join((ask_text(self, self.new_label, "Its name (one word, e.g. Heath):") or "").split())
        if not name:
            return
        sec = "Terrain_" + name
        if self.ini.has_section(sec):
            self.app.status("There's a terrain %s already." % name, "warn")
            self.open(sec)
            return
        for k, v in (("Title", name.replace("_", " ").lower()), ("Kind", "Terrain"), ("Tiles", "Grass001")):
            self.ini.set(sec, k, v)
        self.ini.save()
        self.refresh_list()
        self.open(sec)
