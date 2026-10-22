"""Buildables: Data\\Buildables.ini, what players can build on their homesteads (the server's dsengine/homes.py).
A section is a piece, named after its tile (Tile, Decor), roof material (Roof) or object (Object)."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from ..widgets import photo
from .iniform import IniFormPage

KINDS = ["Tile", "Decor", "Roof", "Object"]
CATEGORIES = ["Floors", "Walls", "Doors", "Windows", "Roofs", "Furniture", "Lights", "Garden", "Workshops"]
ROOFS = ["Thatch", "Shingle", "Slate", "Clay", "Copper"]


def parse_needs(text):
    """"Plank 2 Nails 4" -> ([("Plank", 2), ("Nails", 4)], problem or "")."""
    parts = text.split()
    if len(parts) % 2:
        return [], "Needs should be pairs: an item and how many (e.g. Plank 2 Nails 4)."
    out = []
    for i in range(0, len(parts), 2):
        try:
            q = int(parts[i + 1])
        except ValueError:
            return [], "'%s' isn't a number (Needs: an item and how many)." % parts[i + 1]
        out.append((parts[i], q))
    return out, ""


class BuildablePage(IniFormPage):
    title = "Buildables"
    icon = "⌂"
    kind = "buildable"
    ini_attr = "buildables_ini"
    kinds = KINDS
    new_label = "New piece"
    list_icons = True

    def list_items(self):
        return [(s, "%s  (%s)" % (self.ini.get(s, "Name", "") or s, s), self.ini.get(s, "Kind", ""))
                for s in self.ini.sections()]

    def list_icon(self, key):
        return self.preview(key, (20, 20))

    def image_of(self, key, kind=None):
        """(sprite folder, name) of a piece's picture."""
        kind = kind or self.ini.get(key, "Kind", "Decor")
        if kind == "Roof":
            return "Tiles", key + "_Roof005"
        if kind == "Object":
            return "Entities", key
        return "Tiles", key

    def preview(self, key, size):
        folder, name = self.image_of(key)
        img = self.project.sprite(folder, name)
        return photo(img, size, key=("buildable", folder, name)) if img else None

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)
        head = ttk.Frame(f, style="Panel.TFrame")
        head.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.icon_label = tk.Label(head, bg=T.PANEL)
        self.icon_label.pack(side="left")
        self.name_label = ttk.Label(head, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(side="left", padx=10)
        self.open_link = ttk.Label(head, text="", style="Link.TLabel", cursor="hand2")
        self.open_link.pack(side="left", padx=10)
        self.open_link.bind("<Button-1>", lambda e: self.open_piece())
        r = 1
        self.section_label(f, r, "The piece")
        r += 1
        self.row(f, r, "Kind", ttk.Combobox(f, textvariable=self.var("Kind"), values=KINDS, state="readonly", width=10),
                 "Tile: the ground (floors, walls, doors). Decor: on the ground (furniture, windows, plants). Roof: a "
                 "roof material, its pieces <Material>_Roof001-015 follow the roof's shape. Object: an Entities.ini "
                 "object (workshops).")
        self.row(f, r, "Category", ttk.Combobox(f, textvariable=self.var("Category"), values=CATEGORIES, width=14),
                 "The tab of the Build panel it's on.", col=2)
        r += 1
        self.row(f, r, "Name", ttk.Entry(f, textvariable=self.var("Name"), width=40),
                 "What the Build panel calls it.", span=3)
        r += 1
        on = [""] + ["wall"] + [t for t in self.project.tiles() if not self.project.is_decor(t)]
        self.row(f, r, "Goes on", ttk.Combobox(f, textvariable=self.var("On"), values=on, width=20),
                 "What must be under it: blank = any ground you can walk on; wall = any wall; or one tile (a window "
                 "on its own wall).")
        r += 1
        self.section_label(f, r, "What it takes")
        r += 1
        self.row(f, r, "Needs", ttk.Entry(f, textvariable=self.var("Needs"), width=40),
                 "Materials, an item and how many: Plank 2 Nails 4. Blank = free. Taking it down gives half back.",
                 span=3)
        r += 1
        self.needs_box = self.links(f, r, "Materials", [])
        r += 1
        self.row(f, r, "Construction level", ttk.Spinbox(f, textvariable=self.var("Level"), from_=1, to=99, width=8))
        self.row(f, r, "XP", ttk.Entry(f, textvariable=self.var("XP"), width=8),
                 "Construction experience for building one (a tenth to a whole level, roughly).", col=2)
        r += 1
        ttk.Label(f, text="Players build at home with B (Build mode). Roofs: a joined-up patch of one material is one "
                          "roof; the pieces are worked out by the server.",
                  style="PanelMuted.TLabel", wraplength=560).grid(row=r, column=0, columnspan=4, sticky="w", pady=(12, 0))

    def after_load(self):
        self.name_label.configure(text=self.key or "")
        self._ph = self.preview(self.key, (48, 48)) if self.key else None
        self.icon_label.configure(image=self._ph or "")
        kind = self.vars["Kind"].get()
        self.open_link.configure(text=("Open in %s" % ("Entities" if kind == "Object" else "Tiles")) if self.key else "")
        needs, _ = parse_needs(self.vars["Needs"].get())
        self.fill_links(self.needs_box, [("%d %s" % (q, n), lambda n=n: self.app.goto("entity", n)) for n, q in needs],
                        empty="nothing")

    def on_change(self, key):
        if key in ("Needs", "Kind"):
            self.after_load()

    def open_piece(self):
        if not self.key:
            return
        folder, name = self.image_of(self.key, self.vars["Kind"].get())
        self.app.goto("entity" if folder == "Entities" else "tile", name)

    def validate(self):
        kind = self.vars["Kind"].get()
        needs, problem = parse_needs(self.vars["Needs"].get())
        if problem:
            return problem
        items = set(self.project.items())
        missing = [n for n, _ in needs if n not in items]
        if missing:
            return "No such item: %s." % ", ".join(missing)
        try:
            float(self.vars["XP"].get() or 0)
            int(self.vars["Level"].get() or 1)
        except ValueError:
            return "Level should be a whole number and XP a number."
        tiles = set(self.project.tiles())
        if kind in ("Tile", "Decor") and self.key not in tiles:
            return "There's no tile called %s (a Tile or Decor piece is named after its tile)." % self.key
        if kind == "Roof" and self.key + "_Roof001" not in tiles:
            return "There are no roof tiles %s_Roof001-015 (a Roof piece is named after its material: %s)." % (
                self.key, ", ".join(ROOFS))
        if kind == "Object" and self.project.entity_type(self.key) != "StaticObject":
            return "%s isn't an object in Entities.ini (Type=StaticObject)." % self.key
        if kind == "Decor" and not self.project.is_decor(self.key):
            return "%s isn't a decor tile (Tiles.ini Layer=Decor): make it a Tile piece." % self.key
        return ""

    def init_new(self, name):
        kind = "Object" if self.project.entity_type(name) == "StaticObject" else (
            "Roof" if name in ROOFS else ("Decor" if self.project.is_decor(name) else "Tile"))
        self.ini.set(name, "Kind", kind)
        self.ini.set(name, "Category", {"Object": "Workshops", "Roof": "Roofs", "Decor": "Furniture"}.get(kind, "Floors"))
        self.ini.set(name, "Name", name.rstrip("0123456789").replace("_", " "))
        self.ini.set(name, "Level", "1")
        self.ini.set(name, "XP", "0.1")
