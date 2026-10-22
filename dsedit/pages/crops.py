"""Crops: Data\\Crops.ini, what grows on tilled soil (the server's dsengine/farming.py). A crop grows through its
tiles <Crop>_Crop001 (sprouting), 002 (growing) and 003 (ripe: harvested); its seed is an item with Crop=<crop>."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from ..widgets import photo
from .iniform import IniFormPage

STAGES = ("sprouting", "growing", "ripe")


class CropPage(IniFormPage):
    title = "Crops"
    icon = "❦"
    kind = "crop"
    ini_attr = "crops_ini"
    new_label = "New crop"
    list_icons = True

    def list_items(self):
        return [(s, s, "") for s in self.ini.sections()]

    def list_icon(self, key):
        img = self.project.sprite("Tiles", "%s_Crop003" % key)
        return photo(img, (20, 20), key=("crop", key)) if img else None

    def stage_tile(self, n):
        return "%s_Crop%03d" % (self.key, n)

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)
        head = ttk.Frame(f, style="Panel.TFrame")
        head.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.name_label = ttk.Label(head, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(side="left", padx=(0, 16))
        self.stage_labels = []
        for i in range(3):
            box = ttk.Frame(head, style="Panel.TFrame")
            box.pack(side="left", padx=6)
            pic = tk.Label(box, bg=T.PANEL, cursor="hand2")
            pic.pack()
            pic.bind("<Button-1>", lambda e, n=i + 1: self.key and self.app.goto("tile", self.stage_tile(n)))
            ttk.Label(box, text=STAGES[i], style="PanelMuted.TLabel").pack()
            self.stage_labels.append(pic)
        r = 1
        self.section_label(f, r, "Sowing and harvesting")
        r += 1
        items = [""] + self.project.items()
        self.row(f, r, "Seed", ttk.Combobox(f, textvariable=self.var("Seed"), values=items, width=22),
                 "The item that's sown (used on tilled soil). Saving sets its Entities.ini Crop= to this crop.")
        self.row(f, r, "Gives", ttk.Combobox(f, textvariable=self.var("Gives"), values=items, width=22),
                 "What a harvest gives.", col=2)
        r += 1
        self.row(f, r, "Yield", ttk.Entry(f, textvariable=self.var("Yield"), width=10),
                 "How many a harvest gives: min-max, e.g. 3-6 (and one more every 10 Farming levels).")
        self.row(f, r, "Seed back (%)", ttk.Spinbox(f, textvariable=self.var("Seed.Back"), from_=0, to=100, width=8),
                 "The chance a harvest also gives a seed.", col=2)
        r += 1
        self.row(f, r, "Farming level", ttk.Spinbox(f, textvariable=self.var("Level"), from_=1, to=99, width=8))
        self.row(f, r, "XP", ttk.Entry(f, textvariable=self.var("XP"), width=8),
                 "Farming experience for a harvest (a quarter of it for sowing).", col=2)
        r += 1
        self.section_label(f, r, "Time")
        r += 1
        self.row(f, r, "Minutes to ripe", ttk.Entry(f, textvariable=self.var("Minutes"), width=8),
                 "Real minutes from sowing to ripe; it grows while players are away, and while the server is off.")
        self.row(f, r, "Withers after", ttk.Entry(f, textvariable=self.var("Wither"), width=8),
                 "Minutes a ripe crop waits on a public plot before it's gone (crops on homesteads wait for ever).",
                 col=2)
        r += 1
        self.uses = self.links(f, r, "Links", [])
        r += 1
        self.warn = ttk.Label(f, text="", style="PanelMuted.TLabel", wraplength=560)
        self.warn.grid(row=r, column=0, columnspan=4, sticky="w", pady=(12, 0))

    def after_load(self):
        self.name_label.configure(text=self.key or "")
        self._phs = []
        missing = []
        for i, pic in enumerate(self.stage_labels):
            img = self.project.sprite("Tiles", self.stage_tile(i + 1)) if self.key else None
            ph = photo(img, (48, 48), key=("cropstage", self.key, i)) if img else None
            self._phs.append(ph)
            pic.configure(image=ph or "", text="" if ph or not self.key else "?", fg=T.TEXT)
            if self.key and img is None:
                missing.append(self.stage_tile(i + 1))
        links = []
        for k in ("Seed", "Gives"):
            v = self.vars[k].get().strip()
            if v:
                links.append(("%s: %s" % (k.lower(), v), lambda v=v: self.app.goto("entity", v)))
        self.fill_links(self.uses, links, empty="")
        self.warn.configure(text=("Missing pictures: Sprites\\Tiles\\%s.png. Saving makes their Tiles.ini sections." %
                                  ", ".join(missing)) if missing else
                            "Players sow by using the seed on tilled soil (Soil001): the farmer's furrows, or soil laid "
                            "on a homestead. Only whoever sowed it can harvest it.")

    def on_change(self, key):
        if key in ("Seed", "Gives"):
            self.after_load()

    def validate(self):
        items = set(self.project.items())
        for k in ("Seed", "Gives"):
            v = self.vars[k].get().strip()
            if not v:
                return "Choose the %s." % k.lower()
            if v not in items:
                return "No such item: %s." % v
        y = self.vars["Yield"].get().strip()
        try:
            [int(p) for p in y.split("-")]
            for k in ("Minutes", "Wither", "XP", "Seed.Back", "Level"):
                float(self.vars[k].get() or 0)
        except ValueError:
            return "Yield is min-max (e.g. 3-6); the rest are numbers."
        return ""

    def extra_save(self):
        """The seed knows its crop; the stages have their Tiles.ini sections."""
        ents = self.project.entities_ini
        seed = self.vars["Seed"].get().strip()
        if ents.get(seed, "Crop", "") != self.key:
            ents.set(seed, "Crop", self.key)
            ents.save()
        tiles = self.project.tiles_ini
        made = False
        for n in (1, 2, 3):
            t = self.stage_tile(n)
            if not tiles.has_section(t):
                tiles.add_section(t)
                for k, v in (("Walkable.Data", "1" * 49), ("Show.Name", "1"),
                             ("Use.Words", "Harvest,Examine" if n == 3 else "Examine"),
                             ("Examine.Info", "%s, %s." % (self.key.lower(), STAGES[n - 1])), ("Line.of.Sight", "1"),
                             ("Walk.Speed", "0.8"), ("Layer", "Decor"), ("Sway", "1.0")):
                    tiles.set(t, k, v)
                made = True
        if made:
            tiles.save()
            self.project.refresh("tiles")
        return True

    def init_new(self, name):
        for k, v in (("Seed", name + "_Seed"), ("Gives", name), ("Level", "1"), ("Minutes", "5"), ("Yield", "2-4"),
                     ("XP", "0.1"), ("Seed.Back", "35"), ("Wither", "60")):
            self.ini.set(name, k, v)
