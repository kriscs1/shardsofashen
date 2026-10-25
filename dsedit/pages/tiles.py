"""Tiles: data\\Tiles.ini, one section per sprite in sprites\\Tiles, and each tile's minimap colour
(dev\\Minimap Colours.txt)."""
import math
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

from PIL import Image

from .. import theme as T
from ..project import tile_family, TILE_FAMILIES
from ..widgets import photo, picker_field, VerbPicker, Tooltip
from .iniform import IniFormPage

NAMED = {"white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
         "yellow": (255, 255, 0), "brown": (128, 64, 0), "darkgreen": (0, 100, 0), "darkblue": (0, 0, 139),
         "lightgray": (192, 192, 192), "darkgray": (128, 128, 128), "cyan": (0, 255, 255), "pink": (255, 192, 203),
         "darkred": (139, 0, 0), "darkcyan": (0, 139, 139), "darkpink": (231, 84, 128), "palegray": (192, 192, 192)}


def parse_colour(text):
    t = text.strip().lower()
    if t in NAMED:
        return NAMED[t]
    parts = t.replace(",", " ").split()
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return tuple(min(255, int(p)) for p in parts)
    return None


class TilePage(IniFormPage):
    @property
    def scale(self):
        return max(5, round(7 * T.SCALE))  # the preview: the 32 px tile drawn this many times

    title = "Tiles"
    icon = "▦"
    kind = "tile"
    ini_attr = "tiles_ini"
    kinds = ["Decor"] + [f for f, _ in TILE_FAMILIES] + ["Other", "No data yet"]
    list_icons = True
    allow_new = False

    def __init__(self, app):
        super().__init__(app)
        b = ttk.Button(self.left, text="Split props off their floors…", style="Small.TButton", command=self.split_props)
        b.pack(fill="x", pady=(6, 0))
        Tooltip(b, "Furniture, plants, rocks and trees drawn on a floor become see-through decor tiles for the Maps' "
                   "Decor layer, so one chair goes on any floor. You see each one first.")

    def list_items(self):
        out = []
        for t in self.project.tiles():
            kind = "Decor" if self.project.is_decor(t) else tile_family(t)
            if not self.ini.has_section(t):
                kind = "No data yet"
            out.append((t, t, kind))
        return out

    def split_props(self):
        from .decorsplit import DecorSplitDialog
        r = DecorSplitDialog(self, self.app).run()
        if not r:
            return
        backup, report = r
        self.ini.load()
        self.project.refresh()
        self.refresh_list()
        if self.key:
            self.load(self.key)
        mp = self.app.page_of("map")
        if mp.doc and not mp.is_dirty():
            mp._ghosts.clear()
            mp.load(mp.doc.name)
        self.app.status(report[0], "ok")
        if backup:
            messagebox.showinfo("Split props", "\n".join(report[:14]) + "\n\nThe files as they were are in\n" + backup,
                                parent=self)

    def list_icon(self, key):
        return photo(self.project.sprite("Tiles", key), (32, 32), key=("tile", key))

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        top = ttk.Frame(f, style="Panel.TFrame")
        top.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.canvas = tk.Canvas(top, width=32 * self.scale, height=32 * self.scale, bg="#222", highlightthickness=1,
                                highlightbackground=T.LINE, cursor="crosshair")
        self.canvas.pack(side="left")
        self.canvas.bind("<Button-1>", self.paint_start)
        self.canvas.bind("<B1-Motion>", self.paint_drag)
        side = ttk.Frame(top, style="Panel.TFrame", padding=(16, 0, 0, 0))
        side.pack(side="left", fill="both", expand=True)
        self.name_label = ttk.Label(side, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(anchor="w")
        self.family_label = ttk.Label(side, text="", style="PanelMuted.TLabel")
        self.family_label.pack(anchor="w", pady=(0, 10))
        ttk.Label(side, text="Walkable: click or drag on the picture. Red cells can't be walked on.",
                  style="PanelMuted.TLabel", wraplength=360).pack(anchor="w")
        b = ttk.Frame(side, style="Panel.TFrame")
        b.pack(anchor="w", pady=6)
        for text, fn in (("Block all", lambda: self.set_grid("0")), ("Clear", lambda: self.set_grid("1")),
                         ("Invert", self.invert)):
            ttk.Button(b, text=text, style="Small.TButton", command=fn).pack(side="left", padx=(0, 4))
        cp = ttk.Frame(side, style="Panel.TFrame")
        cp.pack(anchor="w", pady=(4, 0))
        ttk.Label(cp, text="Copy the grid of", style="Panel.TLabel").pack(side="left")
        self.copy_from = tk.StringVar()
        ttk.Combobox(cp, textvariable=self.copy_from, values=self.project.tiles(), width=18).pack(side="left", padx=4)
        ttk.Button(cp, text="Copy", style="Small.TButton", command=self.copy_grid).pack(side="left")
        self.used_box = ttk.Frame(side, style="Panel.TFrame")
        ttk.Label(side, text="Used on", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(14, 0))
        self.used_box.pack(anchor="w", fill="x")

        self.walk = self.var("Walkable.Data")
        r = 1
        self.section_label(f, r, "Interaction")
        r += 1
        uw = ttk.Frame(f, style="Panel.TFrame")
        self.use_words = self.var("Use.Words")
        ttk.Entry(uw, textvariable=self.use_words, width=34).pack(side="left")
        ttk.Button(uw, text="Pick verbs…", style="Small.TButton", command=self.pick_verbs).pack(side="left", padx=4)
        self.row(f, r, "Use words", uw, "Comma list of right-click verbs; the first is the left-click action.")
        r += 1
        self.row(f, r, "Examine text", ttk.Entry(f, textvariable=self.var("Examine.Info"), width=60))
        r += 1
        self.row(f, r, "", ttk.Checkbutton(f, text="Show its name when the mouse is over it",
                                            variable=self.var("Show.Name", "bool", "0")))
        r += 1
        self.row(f, r, "", ttk.Checkbutton(f, text="You can see through it (line of sight)",
                                            variable=self.var("Line.of.Sight", "bool", "1")))
        r += 1
        self.section_label(f, r, "Ground")
        r += 1
        self.row(f, r, "Walk speed", ttk.Combobox(f, textvariable=self.var("Walk.Speed"),
                                                  values=["", "0.5", "0.6", "0.7", "0.8", "1.2", "1.5"], width=10),
                 "x the normal walking speed on this tile (0.2 to 3); blank = normal.")
        r += 1
        self.row(f, r, "Edge blending", ttk.Combobox(f, textvariable=self.var("Blend"),
                                                     values=["", "0", "1", "2", "3", "4", "5", "6"], width=10),
                 "Where two blending tiles meet, the higher one's texture is drawn over the lower one's edge "
                 "(grass 6, snow 5, cave floor and walls 4, sand 3, dirt paths 2, open water 1; blank or 0 = never "
                 "blends).")
        r += 1
        self.section_label(f, r, "Decor")
        r += 1
        self.row(f, r, "Layer", ttk.Combobox(f, textvariable=self.var("Layer"), values=["", "Decor"], width=10,
                                             state="readonly"),
                 "Decor: a see-through tile painted on the Maps' Decor layer, over any ground tile (a chair, a tree, "
                 "flowers). Its walkable grid and line of sight add to the ground's; the mouse names it. Blank: a "
                 "ground tile.")
        r += 1
        pc = ttk.Frame(f, style="Panel.TFrame")
        ttk.Entry(pc, textvariable=self.var("Piece"), width=34).pack(side="left")
        self.set_label = ttk.Label(pc, text="", style="PanelMuted.TLabel")
        self.set_label.pack(side="left", padx=8)
        self.row(f, r, "Piece", pc,
                 "Which piece of a set it is (\"corner: top left\", \"runner: middle\"): the Maps palette says it "
                 "when you point at the tile, with its set (data\TileSets.ini) laid out and this piece marked.")
        r += 1
        tiles = lambda: [(t, t, tile_family(t)) for t in self.project.tiles()]
        icon = lambda k: photo(self.project.sprite("Tiles", k), (32, 32), key=("tile", k))
        self.section_label(f, r, "Animation and light")
        r += 1
        self.row(f, r, "Sway", ttk.Combobox(f, textvariable=self.var("Sway"),
                                            values=["", "0.9", "1.2", "1.6", "2.2", "2.6"], width=10),
                 "A plant in the wind: how many pixels its top sways (blank = it doesn't).")
        r += 1
        self.row(f, r, "Sway ground", picker_field(f, self.var("Sway.Ground"), "Sway ground", tiles, icon,
                                                   kinds=[x for x, _ in TILE_FAMILIES]),
                 "A swaying ground tile (not decor): the ground it's drawn on, so the game can tell the plant from it "
                 "(blank: its Blend texture). Decor doesn't need it.")
        r += 1
        self.row(f, r, "", ttk.Checkbutton(f, text="Flame: its fire flickers", variable=self.var("Flame", "bool", "0")),
                 "Its bright fire-coloured pixels flicker (a torch, a fireplace, a lantern).")
        r += 1
        self.row(f, r, "", ttk.Checkbutton(f, text="Water: foam laps where land meets it",
                                            variable=self.var("Water", "bool", "0")),
                 "Water tiles (ground, not decor): foam runs along the shore, round rocks and blended sand.")
        r += 1
        fr = ttk.Frame(f, style="Panel.TFrame")
        ttk.Spinbox(fr, textvariable=self.var("Anim.Frames"), from_=0, to=16, width=6).pack(side="left")
        ttk.Label(fr, text="pictures, ms each", style="Panel.TLabel").pack(side="left", padx=6)
        ttk.Spinbox(fr, textvariable=self.var("Anim.Speed"), from_=30, to=5000, increment=10, width=7).pack(side="left")
        self.row(f, r, "Frames", fr, "Drawn from its own pictures <Name>1..N in sprites\\Tiles in turn (a mill wheel, "
                                     "a bubbling pot), each cell a little out of step. 0 or blank = one picture.")
        r += 1
        self.row(f, r, "Light at night", ttk.Spinbox(f, textvariable=self.var("Light"), from_=0, to=400, increment=2,
                                                     width=8),
                 "How far (pixels) it lights the dark round it (a torch 72, a lamp post 96, a window 34). Works on "
                 "ground, decor and roof tiles. Blank = it doesn't.")
        r += 1
        ttk.Label(f, text="How fast sway, flames and foam go: data\\Config.ini [Animation].",
                  style="PanelMuted.TLabel").grid(row=r, column=1, sticky="w")
        r += 1
        gl = ttk.Frame(f, style="Panel.TFrame")
        ttk.Entry(gl, textvariable=self.var("Glow.Colour"), width=14).pack(side="left")
        ttk.Label(gl, text="match within", style="Panel.TLabel").pack(side="left", padx=6)
        ttk.Spinbox(gl, textvariable=self.var("Glow.Match"), from_=0, to=64, width=5).pack(side="left")
        self.row(f, r, "Painted glow", gl, "For \"Split props off their floors\": this tile was drawn with the floor lit "
                                           "up round it in this colour (R G B). The split keeps that as see-through "
                                           "light. Match: how near (a few if exact, more for a brightened floor).")
        r += 1
        self.section_label(f, r, "Doors")
        r += 1
        self.row(f, r, "Door", ttk.Combobox(f, textvariable=self.var("Door"), values=["", "1", "Gate"], width=10,
                                            state="readonly"),
                 "1 = a door: townsfolk (Entities.ini Schedule=Day) go home through the nearest one at night. Gate = "
                 "a gateway nobody lives behind. Either way, standing in it under a roof's edge you see inside.")
        r += 1
        self.row(f, r, "Blend texture", picker_field(f, self.var("Blend.Texture"), "Blend texture", tiles, icon,
                                                     kinds=[x for x, _ in TILE_FAMILIES]),
                 "The picture drawn over a lower neighbour's edge (default: the tile itself).")
        r += 1
        self.row(f, r, "Unlocked tile", picker_field(f, self.var("Unlocked.Tile"), "Unlocked tile", tiles, icon,
                                                     kinds=[x for x, _ in TILE_FAMILIES]),
                 "Where a map's Lock is on this tile, this tile is drawn instead while the lock is open (a gate "
                 "drawn open).")
        r += 1
        self.section_label(f, r, "Minimap")
        r += 1
        mm = ttk.Frame(f, style="Panel.TFrame")
        self.swatch = tk.Label(mm, text="      ", relief="solid", bd=1)
        self.swatch.pack(side="left")
        self.mm = tk.StringVar()
        self.mm.trace_add("write", lambda *a: self.mm_changed())
        ttk.Entry(mm, textvariable=self.mm, width=14).pack(side="left", padx=6)
        ttk.Button(mm, text="Choose…", style="Small.TButton", command=self.choose_colour).pack(side="left")
        ttk.Button(mm, text="Sprite's average", style="Small.TButton", command=self.average_colour).pack(side="left",
                                                                                                         padx=4)
        self.row(f, r, "Colour", mm, "dev\\Minimap Colours.txt: R G B (0-255) or a colour name. Rebuild the minimaps "
                                     "(Minimaps section) to see it.")
        self.mm_loaded = ""

    # --- walkable grid
    def grid_res(self):
        n = len(self.walk.get().strip())
        r = int(round(math.sqrt(n))) if n else 7
        return r if r * r == n else 7

    def grid(self):
        data = self.walk.get().strip()
        r = self.grid_res()
        if len(data) != r * r:
            data = "1" * 49
            r = 7
        return [data[i * r:(i + 1) * r] for i in range(r)], r

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.key:
            return
        img = self.project.sprite("Tiles", self.key)
        if img is not None:
            self._ph = photo(img.resize((32 * self.scale, 32 * self.scale), Image.NEAREST), key=("tilebig", self.key))
            c.create_image(0, 0, image=self._ph, anchor="nw")
        rows, r = self.grid()
        cs = 32 * self.scale / r
        for y in range(r):
            for x in range(r):
                x0, y0 = x * cs, y * cs
                if rows[y][x] == "0":
                    c.create_rectangle(x0 + 3, y0 + 3, x0 + cs - 3, y0 + cs - 3, fill="#d23b2e", outline="#7a1d14",
                                       stipple="gray50")
                    c.create_oval(x0 + cs / 2 - 4, y0 + cs / 2 - 4, x0 + cs / 2 + 4, y0 + cs / 2 + 4, fill="#ff5a48",
                                  outline="")
                c.create_rectangle(x0, y0, x0 + cs, y0 + cs, outline="#ffffff", stipple="gray25")

    def cell_at(self, e):
        rows, r = self.grid()
        cs = 32 * self.scale / r
        x, y = int(e.x // cs), int(e.y // cs)
        return (x, y) if 0 <= x < r and 0 <= y < r else None

    def set_cell(self, xy, v):
        rows, r = self.grid()
        x, y = xy
        rows[y] = rows[y][:x] + v + rows[y][x + 1:]
        self.walk.set("".join(rows))

    def paint_start(self, e):
        if not self.key:
            return
        c = self.cell_at(e)
        if c:
            rows, _ = self.grid()
            self.paint_value = "0" if rows[c[1]][c[0]] == "1" else "1"
            self.set_cell(c, self.paint_value)
            self.draw()

    def paint_drag(self, e):
        c = self.cell_at(e)
        if c and self.key:
            rows, _ = self.grid()
            if rows[c[1]][c[0]] != self.paint_value:
                self.set_cell(c, self.paint_value)
                self.draw()

    def set_grid(self, v):
        _, r = self.grid()
        self.walk.set(v * r * r)
        self.draw()

    def invert(self):
        self.walk.set("".join("1" if ch == "0" else "0" for ch in "".join(self.grid()[0])))
        self.draw()

    def copy_grid(self):
        src = self.copy_from.get().strip()
        data = self.ini.get(src, "Walkable.Data", "")
        if not data:
            self.app.status("%s has no walkable grid." % src, "warn")
            return
        self.walk.set(data)
        self.draw()

    # --- loading
    def after_load(self):
        self.name_label.configure(text=self.key or "")
        if not self.key:
            self.draw()
            return
        if not self.walk.get().strip():
            self._loading = True
            self.walk.set("1" * 49)
            self._loading = False
            self.loaded = self.form_values()
        self.family_label.configure(text="%s  ·  %s" % (tile_family(self.key),
                                                        "in Tiles.ini" if self.ini.has_section(self.key) else
                                                        "no data yet: saving adds it"))
        st = self.project.tile_set_of(self.key)
        self.set_label.configure(text=("of the set \"%s\" (data\\TileSets.ini)" % st[1]) if st else "in no set")
        self.draw()
        used = self.project.index()["tile"].get(self.key, {})
        self.fill_links(self.used_box, [(m, lambda m=m, xy=xy: self.app.goto("map", m, tile=xy))
                                        for m, xy in sorted(used.items())], "no map uses it")
        self.mm_loaded = self.project.minimap_colours.get(self.key, "")
        self.mm.set(self.mm_loaded)

    def on_change(self, key):
        if key == "Walkable.Data":
            self.draw()

    # --- minimap colour
    def mm_changed(self):
        rgb = parse_colour(self.mm.get())
        self.swatch.configure(bg="#%02x%02x%02x" % rgb if rgb else T.PANEL)
        self.app.refresh_chrome()

    def choose_colour(self):
        rgb = parse_colour(self.mm.get()) or (128, 128, 128)
        r = colorchooser.askcolor(color="#%02x%02x%02x" % rgb, parent=self)
        if r and r[0]:
            self.mm.set("%d %d %d" % tuple(int(v) for v in r[0]))

    def average_colour(self):
        img = self.project.sprite("Tiles", self.key)
        if img is None:
            return
        px = [p for p in img.getdata() if p[3] > 0]
        if px:
            self.mm.set("%d %d %d" % tuple(sum(p[i] for p in px) // len(px) for i in range(3)))

    def is_dirty(self):
        return super().is_dirty() or (bool(self.key) and self.mm.get().strip() != self.mm_loaded)

    def extra_save(self):
        v = self.mm.get().strip()
        if v != self.mm_loaded:
            if v and not parse_colour(v):
                self.app.status("The minimap colour should be R G B (0-255) or a colour name.", "error")
                return False
            if v:
                self.project.minimap_colours[self.key] = v
            else:
                self.project.minimap_colours.pop(self.key, None)
            self.project.save_minimap_colours()
            self.mm_loaded = v
        return True

    def discard(self):
        super().discard()

    def pick_verbs(self):
        r = VerbPicker(self, self.project, self.use_words.get()).run()
        if r is not None:
            self.use_words.set(r)

    def validate(self):
        w = self.walk.get().strip()
        if w and (set(w) - {"0", "1"} or int(round(math.sqrt(len(w)))) ** 2 != len(w)):
            return "The walkable grid should be a square of 0s and 1s."
        for k, lo, hi in (("Anim.Frames", 0, 64), ("Anim.Speed", 30, 10000), ("Light", 0, 1000)):
            v = self.vars[k].get().strip()
            if v:
                try:
                    if not lo <= float(v) <= hi:
                        return "%s should be between %d and %d." % (k, lo, hi)
                except ValueError:
                    return "%s should be a number." % k
        sw = self.vars["Sway"].get().strip()
        if sw:
            try:
                if not 0 <= float(sw) <= 6:
                    return "Sway should be between 0 and 6 pixels."
            except ValueError:
                return "Sway should be a number."
        ws = self.vars["Walk.Speed"].get().strip()
        if ws:
            try:
                if not 0.2 <= float(ws) <= 3:
                    return "Walk speed should be between 0.2 and 3."
            except ValueError:
                return "Walk speed should be a number."
        return ""
