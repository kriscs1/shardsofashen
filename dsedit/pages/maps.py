"""Maps: Maps\\X,Y,Z.txt. Paint the ground, decor (see-through tiles over any ground: chairs, trees, flowers), roofs
and the Over layer (tree tops); place items, objects, NPCs, triggers and locks; edit NPCs' zones, chase areas and patrols on the map.
The maps round this one show (dimmed) round its edges."""
import re
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageEnhance

from .. import theme as T
from ..app import Page
from ..project import MapDoc, Entity, parse_map_name, tile_family, TILE_FAMILIES, ENTITY_TYPES, HOMESTEAD_MAP
from ..render import render, walk_overlay, tile_image
from ..widgets import (PaletteGrid, photo, ConditionBuilder, PickerDialog, Tooltip, ask_text, Dialog, Segmented)
from .iniform import IniFormPage

LAYERS = [("Ground", "map"), ("Decor", "decor"), ("Roofs", "roof"), ("Over", "infront"), ("Things", "things")]
# each layer's colour (the banner over the map and its frame) and what the banner says
LAYER_LOOK = {"map": ("#3d7a3a", "GROUND", "the floor of the map: grass, paths, walls, water"),
              "decor": ("#6a4c93", "DECOR", "see-through tiles over the ground (chairs, trees, flowers); the ground is "
                                            "greyed"),
              "roof": ("#9a3d2c", "ROOFS", "the ground and things are greyed; roofs hide when the player walks under"),
              "infront": ("#2d6a73", "OVER", "the ground and things are greyed; the Over layer (tree tops, arches) is "
                                       "drawn over the player"),
              "things": ("#a8692c", "THINGS", "items, objects, NPCs, triggers and locks; the ground is greyed")}
LAYER_HINTS = {"map": "Paint the ground tiles (1)",
               "decor": "Decor: a chair, a tree, a pot of flowers over any ground tile (2)",
               "roof": "Roof tiles: hidden while the player is under them (3)",
               "infront": "Over: tree tops, arches and the like, drawn over the player (4)",
               "things": "Items, objects, NPCs, triggers and locks (5)"}
LAYER_NOUN = {"map": "tile", "decor": "decor", "roof": "roof", "infront": "over tile"}
TOOL_HINTS = {"Paint": "Click or drag to paint", "Fill": "Fill the area of the same tile (or Shift+click)",
              "Rectangle": "Drag a rectangle to fill", "Erase": "Click or drag to remove", "Pick": "Click to pick "
              "what's there into the palette (or Ctrl+click)", "Select": "Click a thing to select it; drag to move it",
              "Place": "Click to put the palette's pick down"}
CURSORS = {"Paint": "pencil", "Fill": "spraycan", "Rectangle": "tcross", "Erase": "X_cursor", "Pick": "dotbox"}
TOOLS = {"map": ["Paint", "Fill", "Rectangle", "Pick"], "decor": ["Paint", "Rectangle", "Erase", "Pick"],
         "roof": ["Paint", "Rectangle", "Erase", "Pick"], "infront": ["Paint", "Rectangle", "Erase", "Pick"],
         "things": ["Select", "Place"]}
MARGIN = 3              # tiles of the neighbouring maps shown round the edges
SPECIAL = ["(Trigger)", "(Lock)", "(Place ID)"]
SPECIAL_KIND = {"(Trigger)": "Trigger", "(Lock)": "Lock", "(Place ID)": "Id"}
TILE_KINDS = ("Trigger", "Lock", "Id")      # things on a whole tile (Entity.on_tile)
TILE_LOOK = {"Trigger": ("#f0b030", 2, "⚡"), "Lock": ("#e040c0", 6, "🔒"),   # (colour, inset, symbol)
             "Id": ("#4cc9f0", 4, "📍")}


class NewMapDialog(Dialog):
    def __init__(self, parent, project, near):
        super().__init__(parent, "New map", ok="Make it")
        self.project = project
        x, y, z = parse_map_name(near) if near else (0, 0, 0)
        self.x, self.y, self.z = tk.StringVar(value=str(x + 1)), tk.StringVar(value=str(y)), tk.StringVar(value=str(z))
        self.fill = tk.StringVar(value="Grass001" if z == 0 else "Cave_Wall001" if z < 0 else "Black001")
        b = self.body
        for i, (lab, v) in enumerate((("X (east)", self.x), ("Y (south)", self.y), ("Z (level)", self.z))):
            ttk.Label(b, text=lab, style="Panel.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            ttk.Spinbox(b, textvariable=v, from_=-99, to=99, width=6).grid(row=i, column=1, sticky="w")
        ttk.Label(b, text="Fill with", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 2))
        ttk.Combobox(b, textvariable=self.fill, values=project.tiles(), width=22).grid(row=3, column=1, sticky="w")

    def ok(self):
        try:
            name = "%d,%d,%d" % (int(self.x.get()), int(self.y.get()), int(self.z.get()))
        except ValueError:
            return False
        return name, self.fill.get().strip() or "Grass001"


class MapPage(Page):
    title = "Maps"
    icon = "🗺"
    kind = "map"

    def __init__(self, app):
        super().__init__(app)
        P = self.project
        self.doc, self.loaded = None, None
        self.layer, self.tool = "map", "Paint"
        self.brush = None                 # the palette's pick
        self.sel_cell, self.sel_ent = None, None
        self.mode = None                  # None, "zone", "chase", "patrol"
        self.zoom = round(T.SCALE * 2) / 2 or 1
        self.neighbours = {}
        self.show = {k: tk.BooleanVar(value=v) for k, v in (("preview", False), ("walk", False), ("zones", False),
                                                             ("grid", False))}
        for v in self.show.values():
            v.trace_add("write", lambda *a: self.redraw(full=True))
        self.drag = None
        self._redraw_pending = None
        self._hover = None                # (map px, py, shift) of the mouse over the map, for the ghost
        self._ghosts = {}                 # (brush, layer, zoom) -> the see-through picture of what's about to go down
        self._cursor = ""

        # ----- left: maps, layers, tools, palette
        left = ttk.Frame(self, style="Panel.TFrame", padding=10, width=T.px(300))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        nav = ttk.Frame(left, style="Panel.TFrame")
        nav.pack(fill="x")
        self.map_var = tk.StringVar()
        self.map_box = ttk.Combobox(nav, textvariable=self.map_var, values=P.maps(), width=12)
        self.map_box.pack(side="left")
        self.map_box.bind("<<ComboboxSelected>>", lambda e: self.open(self.map_var.get()))
        self.map_box.bind("<Return>", lambda e: self.open(self.map_var.get().strip()))
        ttk.Button(nav, text="＋ New", style="Small.TButton", command=self.new_map).pack(side="left", padx=4)
        ttk.Button(nav, text="World…", style="Small.TButton",
                   command=lambda: self.app.goto("minimap", str(parse_map_name(self.doc.name)[2]) if self.doc else "0")
                   ).pack(side="left")
        arrows = ttk.Frame(left, style="Panel.TFrame")
        arrows.pack(fill="x", pady=(6, 0))
        self.arrow_btns = {}
        for text, d, col, row in (("▲", (0, -1, 0), 1, 0), ("◀", (-1, 0, 0), 0, 1), ("▶", (1, 0, 0), 2, 1),
                                  ("▼", (0, 1, 0), 1, 2), ("Up a level", (0, 0, 1), 4, 0),
                                  ("Down a level", (0, 0, -1), 4, 2)):
            b = ttk.Button(arrows, text=text, style="Small.TButton", width=3 if len(text) == 1 else 12,
                           command=lambda d=d: self.step(*d))
            b.grid(row=row, column=col, padx=1, pady=1)
            self.arrow_btns[d] = b
        arrows.columnconfigure(3, minsize=16)

        ttk.Label(left, text="Layer", style="Head.TLabel").pack(anchor="w", pady=(12, 2))
        lay = ttk.Frame(left, style="Panel.TFrame")
        lay.pack(fill="x")
        self.layer_var = tk.StringVar(value="map")
        Segmented(lay, self.layer_var, [(key, "%d  %s" % (i + 1, label), LAYER_HINTS[key])
                                        for i, (label, key) in enumerate(LAYERS)],
                  command=lambda: self.set_layer(self.layer_var.get()), columns=2).pack(fill="x")
        ttk.Label(left, text="Tool", style="Head.TLabel").pack(anchor="w", pady=(10, 2))
        self.tool_frame = ttk.Frame(left, style="Panel.TFrame")
        self.tool_frame.pack(fill="x")
        self.tool_var = tk.StringVar(value="Paint")
        self.group_frame = ttk.Frame(left, style="Panel.TFrame")
        ttk.Label(self.group_frame, text="Roof group", style="Panel.TLabel").pack(side="left")
        self.group = tk.StringVar(value="01")
        ttk.Spinbox(self.group_frame, textvariable=self.group, from_=1, to=99, width=4, format="%02.0f").pack(
            side="left", padx=6)
        Tooltip(self.group_frame, "All roofs of a group hide together when the player is under any of them.")

        ttk.Label(left, text="Palette", style="Head.TLabel").pack(anchor="w", pady=(10, 2))
        pf = ttk.Frame(left, style="Panel.TFrame")
        pf.pack(fill="x")
        self.pal_kind = tk.StringVar(value="All")
        self.pal_kind_box = ttk.Combobox(pf, textvariable=self.pal_kind, state="readonly", width=16)
        self.pal_kind_box.pack(side="left")
        self.pal_kind.trace_add("write", lambda *a: self.fill_palette())
        self.pal_search = tk.StringVar()
        e = ttk.Entry(pf, textvariable=self.pal_search, width=12)
        e.pack(side="left", padx=4, fill="x", expand=True)
        Tooltip(e, "Filter by name")
        self.pal_search.trace_add("write", lambda *a: self.fill_palette())
        self.palette = PaletteGrid(left, self.pick_brush, on_hover=lambda k: self.app.info(k or ""), cell=T.px(40),
                                   preview_fn=self.palette_preview)
        self.palette.pack(fill="both", expand=True, pady=4)
        self.brush_label = ttk.Label(left, text="", style="PanelMuted.TLabel")
        self.brush_label.pack(anchor="w")
        vf = ttk.Frame(left, style="Panel.TFrame")
        vf.pack(fill="x", pady=(6, 0))
        ttk.Label(vf, text="Show", style="Head.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        for i, (k, label, key) in enumerate((("preview", "Everything, as in the game", "P"), ("walk", "Walkable", "W"),
                                             ("zones", "All NPC zones", "Z"), ("grid", "Grid", "G"))):
            cb = ttk.Checkbutton(vf, text="%s (%s)" % (label, key), variable=self.show[k])
            cb.grid(row=1 + (i + 1) // 2, column=(i + 1) % 2 if i else 0, columnspan=1 if i else 2, sticky="w")
            if k == "preview":
                Tooltip(cb, "All the layers at once, roofs and all, with nothing greyed. (The layer you edit still "
                            "takes the clicks.)")

        # ----- right: the inspector
        self.inspector = ttk.Frame(self, style="Card.TFrame", padding=12, width=T.px(340))
        self.inspector.pack(side="right", fill="y")
        self.inspector.pack_propagate(False)

        # ----- middle: the map
        mid = ttk.Frame(self, style="TFrame")
        mid.pack(side="left", fill="both", expand=True, padx=8)
        top = ttk.Frame(mid)
        top.pack(fill="x")
        self.map_title = ttk.Label(top, text="", style="HeadBG.TLabel")
        self.map_title.pack(side="left")
        self.banner = tk.Label(top, text="", fg="white", font=T.FONT_BOLD, padx=T.px(10), pady=T.px(2))
        self.banner.pack(side="left", padx=(12, 0))
        self.banner_note = ttk.Label(top, text="", style="Muted.TLabel")
        self.banner_note.pack(side="left", padx=(8, 0))
        zf = ttk.Frame(top)
        zf.pack(side="right")
        ttk.Label(zf, text="Zoom").pack(side="left")
        self.zoom_var = tk.StringVar(value="150%")
        zb = ttk.Combobox(zf, textvariable=self.zoom_var, values=["50%", "75%", "100%", "150%", "200%", "300%"],
                          width=6, state="readonly")
        zb.pack(side="left", padx=4)
        zb.bind("<<ComboboxSelected>>", lambda e: self.set_zoom(int(self.zoom_var.get()[:-1]) / 100, around=None))
        holder = ttk.Frame(mid)
        holder.pack(fill="both", expand=True, pady=(4, 0))
        self.canvas = tk.Canvas(holder, bg="#1a1511", highlightthickness=0)
        xs = ttk.Scrollbar(holder, orient="horizontal", command=self.canvas.xview)
        ys = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        c = self.canvas
        c.bind("<Button-1>", self.press)
        c.bind("<B1-Motion>", self.motion_drag)
        c.bind("<ButtonRelease-1>", self.release)
        c.bind("<Double-Button-1>", self.double)
        c.bind("<Button-3>", self.context)
        c.bind("<Motion>", self.hover)
        c.bind("<Leave>", lambda e: (setattr(self, "_hover", None), self.canvas.delete("ghost")))
        c.bind("<Control-MouseWheel>", lambda e: self.set_zoom(self.zoom * (1.25 if e.delta > 0 else 0.8), around=e))
        # moving the view: drag with the middle button, or hold Space and drag
        c.bind("<ButtonPress-2>", lambda e: (c.scan_mark(e.x, e.y), self.set_cursor("fleur")))
        c.bind("<B2-Motion>", lambda e: c.scan_dragto(e.x, e.y, gain=1))
        c.bind("<ButtonRelease-2>", lambda e: self.update_ghost())
        self._space = False
        c.bind("<KeyPress-space>", self.space_down, add="+")
        c.bind("<KeyRelease-space>", self.space_up, add="+")
        c.bind("<MouseWheel>", lambda e: c.yview_scroll(int(-e.delta / 120) * 3, "units"))
        c.bind("<Shift-MouseWheel>", lambda e: c.xview_scroll(int(-e.delta / 120) * 3, "units"))
        for k in ("<Key>",):
            c.bind(k, self.key)
        c.bind("<Enter>", lambda e: c.focus_set())

        self.set_layer("map")
        maps = P.maps()
        start = P.config.get("Gameplay", "Start.Map", "") or (maps[0] if maps else None)
        if start in maps:
            self.load(start)
        self.show_inspector()

    # =============================================================================================================
    # Loading and saving
    # =============================================================================================================
    def load(self, name, fill=None):
        self.doc = MapDoc(self.project, name)
        if fill:
            self.doc.fill(fill)
        self.loaded = None if fill else self.doc.snapshot()
        self.sel_cell, self.sel_ent, self.mode = None, None, None
        self.clear_history()
        self.map_var.set(name)
        self.neighbours = {}
        self.render_neighbours()
        self.redraw(full=True, center=True)
        self.show_inspector()
        if name == HOMESTEAD_MAP:
            self.app.status("Homestead: the land a new home starts as (Data\Homestead.txt). Each home gets its own "
                            "copy when it's made, so changes here are for new homes only. Keep the Homestone and "
                            "Home_Arrival.", "warn")
        for d, b in self.arrow_btns.items():
            b.state(["disabled"] if name == HOMESTEAD_MAP else ["!disabled"])     # (nothing next to it)
        self.app.refresh_chrome()

    def open(self, key, tile=None, **kw):
        key = (key or "").strip()
        if not parse_map_name(key):
            return
        if not self.doc or key != self.doc.name:
            if not self.leave_ok():
                self.map_var.set(self.doc.name if self.doc else "")
                return
            if key not in self.project.maps():
                if not messagebox.askyesno("New map", "There's no map %s yet. Make it?" % key, parent=self):
                    return
                r = NewMapDialog(self, self.project, key)
                x, y, z = parse_map_name(key)
                r.x.set(str(x))
                r.y.set(str(y))
                r.z.set(str(z))
                res = r.run()
                if not res:
                    return
                self.load(res[0], fill=res[1])
                return
            self.load(key)
        if tile:
            self.select_cell(tile[0] - 1, tile[1] - 1)
            self.scroll_to(tile[0] - 1, tile[1] - 1)

    def is_dirty(self):
        return bool(self.doc) and (self.loaded is None or self.doc.snapshot() != self.loaded)

    def current(self):
        return self.doc.name if self.doc else ""

    def save(self):
        if not self.doc:
            return True
        self.doc.save()
        self.loaded = self.doc.snapshot()
        self.project.refresh("maps")
        self.map_box.configure(values=self.project.maps())
        self.app.status("Saved map %s." % self.doc.name, "ok")
        self.app.refresh_chrome()
        return True

    def discard(self):
        if self.doc and self.loaded is not None:
            self.doc.restore(self.loaded)
        self.redraw(full=True)

    def snapshot(self):
        return (self.doc.snapshot(), self.sel_ent_index()) if self.doc else None

    def restore(self, snap):
        text, sel = snap
        self.doc.restore(text)
        ents = self.doc.placed()
        self.sel_ent = ents[sel] if sel is not None and sel < len(ents) else None
        self.redraw(full=True)
        self.show_inspector()

    def sel_ent_index(self):
        if self.sel_ent is None:
            return None
        ents = self.doc.placed()
        return ents.index(self.sel_ent) if self.sel_ent in ents else None

    def on_show(self):
        self.project.refresh("maps")
        self.map_box.configure(values=self.project.maps())
        if self.doc and self.doc.exists and not self.is_dirty():
            from ..project import mtime
            if mtime(self.doc.path) != self.doc.stamp:
                self.load(self.doc.name)
        self.fill_palette()

    def search_items(self):
        return [(m, "Map " + m + (": the land a new home starts as" if m == HOMESTEAD_MAP else ""))
                for m in self.project.maps()]

    def selected_spot(self):
        """(map, tile x, tile y) of the selected tile (Quests' markers), or None."""
        if self.doc and self.sel_cell:
            return self.doc.name, self.sel_cell[0] + 1, self.sel_cell[1] + 1
        return None

    # --- moving between maps
    def step(self, dx, dy, dz):
        if not self.doc or self.doc.name == HOMESTEAD_MAP:
            return
        x, y, z = parse_map_name(self.doc.name)
        self.open("%d,%d,%d" % (x + dx, y + dy, z + dz))

    def new_map(self):
        if not self.leave_ok():
            return
        r = NewMapDialog(self, self.project, self.doc.name if self.doc else "0,0,0").run()
        if not r:
            return
        name, fill = r
        if name in self.project.maps():
            self.open(name)
            return
        self.load(name, fill=fill)
        self.app.status("New map %s: Save to make the file." % name)

    # =============================================================================================================
    # Layers, tools, the palette
    # =============================================================================================================
    def set_layer(self, layer):
        self.layer = layer
        self.layer_var.set(layer)
        for w in self.tool_frame.winfo_children():
            w.destroy()
        tools = TOOLS[layer]
        if self.tool not in tools:
            self.tool = tools[0]
        self.tool_var.set(self.tool)
        Segmented(self.tool_frame, self.tool_var, [(t, t, TOOL_HINTS[t]) for t in tools],
                  command=lambda: self.set_tool(self.tool_var.get())).pack(anchor="w")
        col, name, note = LAYER_LOOK[layer]
        self.banner.configure(text="Editing:  " + name, bg=col)
        self.banner_note.configure(text=note)
        if layer == "roof":
            self.group_frame.pack(after=self.tool_frame, fill="x", pady=(4, 0))
        else:
            self.group_frame.pack_forget()
        kinds = ["All"] + ([f for f, _ in TILE_FAMILIES] + ["Other"] if layer != "things" else
                           ["Triggers, locks & places"] + ENTITY_TYPES)
        self.pal_kind_box.configure(values=kinds)
        self.pal_kind.set("Roofs" if layer == "roof" else "All")
        self.palette.selected = None
        self.fill_palette()
        self.pick_brush(None, keep_tool=True)
        self.sel_ent = None if layer != "things" else self.sel_ent
        self.redraw()
        self.show_inspector()

    def set_tool(self, tool):
        self.tool = tool
        self.tool_var.set(tool)
        self.pick_brush(self.brush, keep_tool=True)
        self.update_ghost()

    def fill_palette(self):
        P = self.project
        q = self.pal_search.get().strip().lower()
        k = self.pal_kind.get()
        items = []
        if self.layer == "things":
            for s in SPECIAL:
                if k in ("All", "Triggers, locks & places") and (not q or q in s.lower()):
                    items.append((s, None, TILE_LOOK[SPECIAL_KIND[s]][2] + "\n" + s.strip("()")))
            for e in P.placeable():
                t = P.entity_type(e)
                if k not in ("All", t) or (q and q not in e.lower()):
                    continue
                items.append((e, P.sprite("Entities", e), e))
        else:
            for t in P.tiles():
                fam = tile_family(t)
                if k not in ("All", fam) or (q and q not in t.lower()):
                    continue
                # a see-through decor tile can't be a cell's ground (it would show black): it's for the Decor layer
                flat = P.is_under(t)                     # (a rug: painted with the Decor layer, under it)
                if (self.layer == "map" and (P.is_decor(t) or flat)) or \
                        (self.layer == "decor" and not (P.is_decor(t) or flat)):
                    continue
                items.append((t, P.sprite("Tiles", t), t))
        self.palette.set_items(items)
        if self.layer == "decor" and not items and not q and k == "All":
            self.app.status("No decor tiles yet. Tiles ▸ \"Split props off their floors…\" makes them from furniture "
                            "and plants, or tick \"Decor\" on a see-through tile.", "warn")

    def palette_preview(self, key):
        """The palette's hover picture: the sprite three times over, its name, and for a piece of a set (a roof, a rug)
        the whole set laid out with this piece marked, so you can see which corner or edge it is."""
        P = self.project
        if key in SPECIAL:
            return None
        sheet = self.piece_set(key)
        img = (P.sprite("Tiles", key) if self.layer != "things" else P.sprite("Entities", key))
        if img is None:
            return None
        if self.layer == "map":
            img = tile_image(P, key)
        big = img.convert("RGBA").resize((img.size[0] * 2, img.size[1] * 2), Image.NEAREST)
        if not sheet:
            return big, key.replace("_", " ")
        names, cols, mark, caption = sheet
        if key not in names:
            return big, "%s: %s" % (key.replace("_", " "), caption)
        s = P.tile_w + 2                                # (each piece at its own size, a thin line between them)
        rows = (len(names) + cols - 1) // cols
        gap = 12
        out = Image.new("RGBA", (big.size[0] + gap + cols * s, max(big.size[1], rows * s)), (26, 21, 17, 255))
        out.alpha_composite(big, (0, (out.size[1] - big.size[1]) // 2))
        from PIL import ImageDraw
        d = ImageDraw.Draw(out)
        x0 = big.size[0] + gap
        for i, n in enumerate(names):
            spr = P.sprite("Tiles", n) if n else None
            x, y = x0 + (i % cols) * s, (i // cols) * s
            if spr is not None:
                piece = spr.convert("RGBA")
                if n != key:
                    piece.putalpha(piece.getchannel("A").point(lambda v: v * 55 // 100))
                out.alpha_composite(piece, (x, y))
        for i, n in enumerate(names):                   # (a piece can be in a set more than once: a fence's middle)
            if n == key:
                x, y = x0 + (i % cols) * s, (i // cols) * s
                d.rectangle((x - 1, y - 1, x + s - 2, y + s - 2), outline=(255, 224, 102, 255), width=2)
        return out, "%s\n%s" % (key.replace("_", " "), caption)

    def piece_set(self, key):
        """For a tile that's one piece of a set (Data\TileSets.ini): (the set's tiles in order, columns, None, what
        it is: the set's title and the tile's Tiles.ini Piece=)."""
        st = self.project.tile_set_of(key)
        if not st:
            piece = self.project.tiles_ini.get(key, "Piece", "")
            return ([key], 1, None, piece) if piece else None
        _, title, cols, names = st
        piece = self.project.tiles_ini.get(key, "Piece", "")
        return names, cols, None, "%s: %s" % (title[:1].upper() + title[1:], piece) if piece else title

    def pick_brush(self, key, keep_tool=False):
        self.brush = key
        if key and not keep_tool:
            if self.layer == "things":
                self.tool = "Place"
            elif self.tool in ("Pick", "Erase", "Select"):
                self.tool = "Paint"
            self.tool_var.set(self.tool)
        if not key:
            text = "Pick something from the palette to paint with." if self.layer != "things" else \
                "Pick something from the palette to place it."
        elif self.layer == "things":
            text = ("Placing %s: click the map to put one down (Esc stops)." % key) if self.tool == "Place" else \
                "Place tool: puts down %s." % key
        else:
            text = "Painting with %s (Esc stops)." % key
        self.brush_label.configure(text=text, wraplength=T.px(280))
        self.update_ghost()

    # =============================================================================================================
    # Drawing
    # =============================================================================================================
    def render_neighbours(self):
        """The maps round this one (dimmed), for the edges."""
        if not self.doc:
            return
        x, y, z = parse_map_name(self.doc.name)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == dy == 0:
                    continue
                name = "%d,%d,%d" % (x + dx, y + dy, z)
                if name in self.project.maps():
                    img = render(self.project, MapDoc(self.project, name), roofs=False, infront=False).convert("RGB")
                    img = ImageEnhance.Brightness(ImageEnhance.Color(img).enhance(0.35)).enhance(0.55)
                    self.neighbours[(dx, dy)] = img
                else:
                    self.neighbours[(dx, dy)] = None

    def composite(self):
        P = self.project
        tw, th = P.tile_w, P.tile_h
        W, H = P.map_w * tw, P.map_h * th
        m = MARGIN
        big = Image.new("RGB", (W + 2 * m * tw, H + 2 * m * th), (26, 21, 17))
        for (dx, dy), img in self.neighbours.items():
            if img is None:
                continue
            sx = 0 if dx == 1 else (W - m * tw if dx == -1 else 0)
            sy = 0 if dy == 1 else (H - m * th if dy == -1 else 0)
            sw = m * tw if dx else W
            sh = m * th if dy else H
            crop = img.crop((sx, sy, sx + sw, sy + sh))
            px = {-1: 0, 0: m * tw, 1: m * tw + W}[dx]
            py = {-1: 0, 0: m * th, 1: m * th + H}[dy]
            big.paste(crop, (px, py))
        cur = self.layer_picture()
        if self.show["walk"].get():
            cur.alpha_composite(walk_overlay(P, self.doc))
        big.paste(cur.convert("RGB"), (m * tw, m * th))
        return big

    def layer_picture(self):
        """The map as the layer being edited sees it: that layer bright, what's under it greyed (for where things
        are), and what's over it left out. "Everything" shows the map as the game does."""
        P, d, layer = self.project, self.doc, self.layer
        if self.show["preview"].get():
            return render(P, d)
        if layer == "map":
            return render(P, d, roofs=False, infront=False, entities=False, decor=False)
        under = render(P, d, roofs=False, infront=False, entities=layer not in ("things", "decor"),
                       decor=layer != "decor").convert("RGB")
        under = ImageEnhance.Brightness(ImageEnhance.Color(under).enhance(0.4)).enhance(0.76).convert("RGBA")
        over = render(P, d, ground=False, roofs=layer == "roof", infront=layer == "infront",
                      entities=layer == "things", decor=layer == "decor")
        under.alpha_composite(over)
        return under

    def set_zoom(self, z, around=None):
        """around: the mouse event to zoom about (the spot under it stays put), or None: the middle of the view."""
        z = max(0.5, min(3, z))
        c = self.canvas
        if around is not None:
            sx, sy = around.x, around.y
        else:
            sx, sy = c.winfo_width() / 2, c.winfo_height() / 2
        old = self.zoom
        self._zoom_anchor = (c.canvasx(sx) / old, c.canvasy(sy) / old, sx, sy)
        self.zoom = z
        self.zoom_var.set("%d%%" % round(z * 100))
        self.redraw(full=True)

    def space_down(self, e):
        if not self._space:
            self._space = True
            self.set_cursor("fleur")
        return "break"

    def space_up(self, e):
        self._space = False
        self.update_ghost()

    def redraw(self, full=False, center=False):
        if not self.doc:
            return
        if self._redraw_pending:
            self.after_cancel(self._redraw_pending)
        self._redraw_pending = self.after(1, lambda: self._redraw(center))

    def _redraw(self, center=False):
        self._redraw_pending = None
        P, c, z = self.project, self.canvas, self.zoom
        big = self.composite()
        w, h = int(big.size[0] * z), int(big.size[1] * z)
        self._ph = photo(big.resize((w, h), Image.NEAREST if z >= 1 else Image.BILINEAR))
        c.delete("all")
        c.create_image(0, 0, image=self._ph, anchor="nw")
        c.configure(scrollregion=(0, 0, w, h))
        anchor = getattr(self, "_zoom_anchor", None)
        if anchor:                                      # (zoomed: keep the spot that was under the mouse there)
            self._zoom_anchor = None
            mx, my, sx, sy = anchor
            c.xview_moveto(max(0.0, (mx * z - sx) / w))
            c.yview_moveto(max(0.0, (my * z - sy) / h))
        tw, th = P.tile_w, P.tile_h
        ox, oy = MARGIN * tw * z, MARGIN * th * z
        W, H = P.map_w * tw * z, P.map_h * th * z
        c.create_rectangle(ox - 2, oy - 2, ox + W + 1, oy + H + 1, outline=LAYER_LOOK[self.layer][0], width=3)
        if self.show["grid"].get():                     # (Windows can't stipple lines: a dark line, a light one by it)
            for x in range(1, P.map_w):
                gx = ox + x * tw * z
                c.create_line(gx, oy, gx, oy + H, fill="#000000")
                c.create_line(gx + 1, oy, gx + 1, oy + H, fill="#d8cbb4", dash=(1, 3))
            for y in range(1, P.map_h):
                gy = oy + y * th * z
                c.create_line(ox, gy, ox + W, gy, fill="#000000")
                c.create_line(ox, gy + 1, ox + W, gy + 1, fill="#d8cbb4", dash=(1, 3))
        # triggers, locks and named places (a place's name under its pin)
        if self.layer == "things" or self.show["preview"].get():
            for e in self.doc.placed():
                if e.kind in TILE_KINDS:
                    x0, y0 = ox + (e.x - 1) * tw * z, oy + (e.y - 1) * th * z
                    col, pad, sym = TILE_LOOK[e.kind]
                    c.create_rectangle(x0 + pad, y0 + pad, x0 + tw * z - pad, y0 + th * z - pad, outline=col,
                                       width=2, dash=(4, 3))
                    c.create_text(x0 + tw * z / 2, y0 + th * z / 2, text=sym,
                                  fill=col, font=("Segoe UI Symbol", max(8, int(11 * z))))
                    if e.kind == "Id":
                        for dx, dy, fill in ((1, 1, "#000000"), (0, 0, col)):
                            c.create_text(x0 + tw * z / 2 + dx, y0 + th * z + 1 + dy, text=e.name, fill=fill,
                                          anchor="n", font=("Segoe UI", max(7, int(7 * z)), "bold"))
        # NPC zones
        for e in self.doc.placed():
            if e.kind == "NPC" and (self.show["zones"].get() or e is self.sel_ent):
                self.draw_npc_areas(e, ox, oy, z, faint=e is not self.sel_ent)
        # the selection
        if self.sel_cell:
            x, y = self.sel_cell
            c.create_rectangle(ox + x * tw * z, oy + y * th * z, ox + (x + 1) * tw * z, oy + (y + 1) * th * z,
                               outline="#ffffff", width=2)
            c.create_rectangle(ox + x * tw * z + 2, oy + y * th * z + 2, ox + (x + 1) * tw * z - 2,
                               oy + (y + 1) * th * z - 2, outline="#000000", width=1)
        if self.sel_ent is not None:
            x0, y0, x1, y1 = self.ent_rect(self.sel_ent)
            c.create_rectangle(ox + x0 * z - 2, oy + y0 * z - 2, ox + x1 * z + 2, oy + y1 * z + 2, outline="#ffe066",
                               width=2, dash=(5, 2))
        if self.drag and self.drag.get("rect"):
            (x0, y0), (x1, y1) = self.drag["rect"]
            c.create_rectangle(ox + min(x0, x1) * tw * z, oy + min(y0, y1) * th * z, ox + (max(x0, x1) + 1) * tw * z,
                               oy + (max(y0, y1) + 1) * th * z, outline="#66d9ff", width=2, dash=(6, 3))
        if center:
            self.after(10, lambda: self.scroll_to(P.map_w // 2, P.map_h // 2))
        self.map_title.configure(text=("Map %s" % self.doc.name) + ("" if self.doc.exists else "   (new: not saved)"))
        self.update_ghost()
        self.app.refresh_chrome()

    def ghost_photo(self, name, layer):
        """The see-through picture of name at this zoom (a tile, or an entity's sprite)."""
        key = (name, layer, self.zoom)
        if key not in self._ghosts:
            P = self.project
            img = (tile_image(P, name) if layer == "map" else P.sprite("Tiles", name)) if layer != "things" else \
                P.sprite("Entities", name)
            if img is None:
                return None
            img = img.convert("RGBA")
            w, h = max(1, int(img.size[0] * self.zoom)), max(1, int(img.size[1] * self.zoom))
            img = img.resize((w, h), Image.NEAREST)
            img.putalpha(img.getchannel("A").point(lambda v: v * 62 // 100))
            if len(self._ghosts) > 40:
                self._ghosts.clear()
            self._ghosts[key] = photo(img)
        return self._ghosts[key]

    def place_xy(self, name, px, py, tx, ty, shift):
        """Where a new thing goes: on the tile, its feet on its bottom row (Shift: right under the mouse)."""
        w, h = self.ent_size(Entity(self.project.entity_type(name), name, 0, 0))
        if shift:
            return int(px - w / 2), int(py - h + 4)
        return tx * self.project.tile_w + (self.project.tile_w - w) // 2, (ty + 1) * self.project.tile_h - h

    def update_ghost(self):
        """Show what the click would do, where the mouse is: the tile or thing about to go down (see-through), the
        rectangle it would fill, or what it would rub out. And the cursor to match."""
        c = self.canvas
        c.delete("ghost")
        h = self._hover
        if not self.doc or h is None:
            return
        px, py, shift, ctrl = h
        P, z = self.project, self.zoom
        tw, th = P.tile_w, P.tile_h
        tx, ty = self.tile_of(px, py)
        ox, oy = MARGIN * tw * z, MARGIN * th * z
        cursor = "arrow"
        if not self.inside(tx, ty):
            x, y, lz = parse_map_name(self.doc.name)
            dx = -1 if tx < 0 else (1 if tx >= P.map_w else 0)
            dy = -1 if ty < 0 else (1 if ty >= P.map_h else 0)
            self.set_cursor("hand2" if "%d,%d,%d" % (x + dx, y + dy, lz) in P.maps() else "arrow")
            return
        x0, y0 = ox + tx * tw * z, oy + ty * th * z
        box = (x0, y0, x0 + tw * z, y0 + th * z)
        if self.mode in ("zone", "chase"):
            cursor = "crosshair"
        elif self.mode == "patrol":
            cursor = "target"
            c.create_oval(x0 + tw * z / 2 - 7, y0 + th * z / 2 - 7, x0 + tw * z / 2 + 7, y0 + th * z / 2 + 7,
                          outline="#ffd23c", width=2, tags="ghost")
        elif ctrl:
            cursor = CURSORS["Pick"]
            c.create_rectangle(*box, outline="#ffffff", dash=(2, 2), tags="ghost")
        elif self.layer == "things":
            if self.drag and self.drag.get("move"):
                cursor = "fleur"
            elif self.tool == "Place" and self.brush:
                cursor = "plus"
                if self.brush in SPECIAL:
                    col, _, sym = TILE_LOOK[SPECIAL_KIND[self.brush]]
                    c.create_rectangle(box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2, outline=col, width=2,
                                       dash=(4, 3), tags="ghost")
                    c.create_text((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, fill=col, tags="ghost",
                                  text=sym, font=("Segoe UI Symbol", max(8, int(11 * z))))
                else:
                    ex, ey = self.place_xy(self.brush, px, py, tx, ty, shift)
                    ph = self.ghost_photo(self.brush, "things")
                    if ph is not None:
                        c.create_image(ox + ex * z, oy + ey * z, image=ph, anchor="nw", tags="ghost")
                        c.create_rectangle(ox + ex * z, oy + ey * z, ox + ex * z + ph.width(),
                                           oy + ey * z + ph.height(), outline="#ffe066", dash=(3, 3), tags="ghost")
            elif self.ent_at(px, py) is not None:
                cursor = "fleur"
        else:
            tool = "Fill" if shift and self.layer == "map" else self.tool
            cursor = CURSORS.get(tool, "arrow")
            if tool == "Erase":
                c.create_rectangle(*box, outline="#ff5040", width=2, tags="ghost")
                c.create_line(box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4, fill="#ff5040", width=2, tags="ghost")
                c.create_line(box[0] + 4, box[3] - 4, box[2] - 4, box[1] + 4, fill="#ff5040", width=2, tags="ghost")
            elif tool == "Pick":
                c.create_rectangle(*box, outline="#ffffff", dash=(2, 2), tags="ghost")
            elif not self.brush:
                cursor = "arrow"
            elif not (self.drag and self.drag.get("rect")):
                ph = self.ghost_photo(self.brush, self.layer)
                if ph is not None:
                    c.create_image(x0, y0, image=ph, anchor="nw", tags="ghost")
                c.create_rectangle(*box, outline=LAYER_LOOK[self.layer][0] if tool != "Fill" else "#66d9ff", width=2,
                                   tags="ghost")
        self.set_cursor(cursor)

    def set_cursor(self, cursor):
        if cursor != self._cursor:
            self._cursor = cursor
            try:
                self.canvas.configure(cursor=cursor)
            except tk.TclError:
                self.canvas.configure(cursor="arrow")

    def draw_npc_areas(self, e, ox, oy, z, faint=False):
        P, c = self.project, self.canvas
        tw, th = P.tile_w, P.tile_h

        def rect(r, col, dash):
            x1, y1, x2, y2 = r
            c.create_rectangle(ox + (x1 - 1) * tw * z, oy + (y1 - 1) * th * z, ox + x2 * tw * z, oy + y2 * th * z,
                               outline=col, width=1 if faint else 2, dash=dash)
        zone, chase = self.npc_zone(e), self.npc_chase(e)
        if zone:
            rect(zone[0], "#5fd35f", None if zone[1] else (4, 4))
        if chase:
            rect(chase[0], "#ff6050", None if chase[1] else (4, 4))
        pts = self.patrol(e)
        if pts:
            coords = []
            for i, (px, py) in enumerate(pts, 1):
                cx, cy = ox + (px - 0.5) * tw * z, oy + (py - 0.5) * th * z
                coords.append((cx, cy))
                c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#ffd23c", outline="#5a4100")
                c.create_text(cx, cy, text=str(i), font=("Segoe UI", 7, "bold"))
            if len(coords) > 1:
                c.create_line(*[v for p in coords for v in p], fill="#ffd23c", width=2, arrow="last")
                if (e.opt("PatrolMode") or "Loop").lower() != "pingpong":
                    c.create_line(*coords[-1], *coords[0], fill="#ffd23c", dash=(4, 4))

    # =============================================================================================================
    # Geometry
    # =============================================================================================================
    def map_px(self, e):
        """Map pixel (x, y) of a mouse event (may be outside the map)."""
        z = self.zoom
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        return cx / z - MARGIN * self.project.tile_w, cy / z - MARGIN * self.project.tile_h

    def tile_of(self, px, py):
        return int(px // self.project.tile_w), int(py // self.project.tile_h)

    def inside(self, tx, ty):
        return 0 <= tx < self.project.map_w and 0 <= ty < self.project.map_h

    def ent_size(self, e):
        spr = self.project.sprite("Entities", e.name) if e.kind not in TILE_KINDS else None
        return spr.size if spr is not None else (self.project.tile_w, self.project.tile_h)

    def ent_rect(self, e):
        tw, th = self.project.tile_w, self.project.tile_h
        if e.kind in TILE_KINDS:
            return (e.x - 1) * tw, (e.y - 1) * th, e.x * tw, e.y * th
        w, h = self.ent_size(e)
        return e.x, e.y, e.x + w, e.y + h

    def ent_at(self, px, py, prefer_tile_kind=None):
        hits = [e for e in self.doc.placed() if self.ent_rect(e)[0] <= px < self.ent_rect(e)[2] and
                self.ent_rect(e)[1] <= py < self.ent_rect(e)[3]]
        if not hits:
            return None
        if prefer_tile_kind:
            for e in hits:
                if e.kind == prefer_tile_kind:
                    return e
        # the lock's padlock (the middle of its tile) wins over a trigger on the same tile
        sprites = [e for e in hits if e.kind not in TILE_KINDS]
        if sprites:
            return max(sprites, key=lambda e: self.ent_rect(e)[3])
        tw = self.project.tile_w
        locks = [e for e in hits if e.kind == "Lock"]
        if locks and abs(px % tw - tw / 2) < tw / 3 and abs(py % tw - tw / 2) < tw / 3:
            return locks[0]
        return hits[0]

    def scroll_to(self, tx, ty):
        z = self.zoom
        tw, th = self.project.tile_w, self.project.tile_h
        total_w = (self.project.map_w + 2 * MARGIN) * tw * z
        total_h = (self.project.map_h + 2 * MARGIN) * th * z
        cx, cy = (MARGIN + tx + 0.5) * tw * z, (MARGIN + ty + 0.5) * th * z
        vw, vh = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.xview_moveto(max(0, (cx - vw / 2) / total_w))
        self.canvas.yview_moveto(max(0, (cy - vh / 2) / total_h))

    # =============================================================================================================
    # The NPC options
    # =============================================================================================================
    def npc_zone(self, e):
        """((x1, y1, x2, y2), from the map line?) or None."""
        z = e.opt("Zone")
        if z:
            try:
                return tuple(int(v) for v in z.split(",")), True
            except ValueError:
                return None
        try:
            r = int(float(self.project.entities_ini.get(e.name, "Roam.Radius", "3") or 3))
        except ValueError:
            r = 3
        tx, ty = self.spawn_tile(e)
        return (tx - r, ty - r, tx + r, ty + r), False

    def npc_chase(self, e):
        ch = e.opt("Chase")
        if ch:
            try:
                return tuple(int(v) for v in ch.split(",")), True
            except ValueError:
                return None
        zone = self.npc_zone(e)
        try:
            r = int(float(self.project.entities_ini.get(e.name, "Chase.Radius", "4") or 4))
        except ValueError:
            r = 4
        if not zone:
            return None
        x1, y1, x2, y2 = zone[0]
        return (x1 - r, y1 - r, x2 + r, y2 + r), False

    def spawn_tile(self, e):
        w, h = self.ent_size(e)
        return int((e.x + w / 2) // self.project.tile_w) + 1, int((e.y + h - 1) // self.project.tile_h) + 1

    def patrol(self, e):
        out = []
        for p in (e.opt("Patrol") or "").split("/"):
            try:
                x, y = (int(v) for v in p.split(","))
                out.append((x, y))
            except ValueError:
                pass
        return out

    # =============================================================================================================
    # The mouse
    # =============================================================================================================
    def press(self, e):
        if not self.doc:
            return
        self.canvas.focus_set()
        if self._space:                                 # Space held: drag the view about
            self.canvas.scan_mark(e.x, e.y)
            self.drag = {"pan": True}
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        shift, ctrl = e.state & 0x1, e.state & 0x4
        if self.mode in ("zone", "chase") and self.sel_ent is not None:
            self.drag = {"rect": ((tx, ty), (tx, ty)), "area": self.mode}
            self.redraw()
            return
        if self.mode == "patrol" and self.sel_ent is not None:
            if self.inside(tx, ty) or True:
                self.remember()
                pts = self.patrol(self.sel_ent) + [(tx + 1, ty + 1)]
                self.sel_ent.set_opt("Patrol", "/".join("%d,%d" % p for p in pts))
                self.redraw()
                self.show_inspector()
            return
        if not self.inside(tx, ty):
            return
        if ctrl:
            self.pick_under(px, py, tx, ty)
            return
        if self.layer == "things":
            self.press_things(px, py, tx, ty, shift)
            return
        self.sel_cell = (tx, ty)
        tool = "Fill" if shift else self.tool
        if tool == "Pick":
            self.pick_under(px, py, tx, ty)
            return
        if tool == "Rectangle":
            self.drag = {"rect": ((tx, ty), (tx, ty))}
            self.redraw()
            return
        if tool in ("Paint", "Erase", "Fill"):
            if tool != "Erase" and not self.brush:
                self.show_inspector()
                self.redraw()
                return
            self.remember()
            if tool == "Fill":
                self.flood(tx, ty)
            else:
                self.paint_cell(tx, ty, erase=(tool == "Erase"))
            self.drag = {"paint": True, "erase": tool == "Erase"}
            self.redraw()
            self.show_inspector()

    def motion_drag(self, e):
        if not self.drag or not self.doc:
            return
        if self.drag.get("pan"):
            self.canvas.scan_dragto(e.x, e.y, gain=1)
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        self._hover = (px, py, bool(e.state & 0x1), bool(e.state & 0x4))
        if "rect" in self.drag:
            self.drag["rect"] = (self.drag["rect"][0], (tx, ty) if self.drag.get("area") else
                                 (max(0, min(self.project.map_w - 1, tx)), max(0, min(self.project.map_h - 1, ty))))
            self.redraw()
        elif self.drag.get("paint"):
            if self.inside(tx, ty):
                if self.paint_cell(tx, ty, erase=self.drag["erase"]):
                    self.sel_cell = (tx, ty)
                    self.redraw()
        elif self.drag.get("move"):
            ent = self.drag["move"]
            dx, dy = px - self.drag["start"][0], py - self.drag["start"][1]
            if not self.drag.get("moved") and abs(dx) + abs(dy) < 3:
                return
            if not self.drag.get("moved"):
                self.remember()
                self.drag["moved"] = True
            if ent.kind in TILE_KINDS:
                nx, ny = tx + 1, ty + 1
                if self.inside(tx, ty) and (nx, ny) != (ent.x, ent.y):
                    ent.x, ent.y = nx, ny
                    self.redraw()
            else:
                ox, oy = self.drag["orig"]
                nx, ny = int(ox + dx), int(oy + dy)
                if e.state & 0x1:                       # Shift: snap to the tile (feet on its bottom row)
                    w, h = self.ent_size(ent)
                    tx, ty = self.tile_of(nx + w / 2, ny + h - 1)
                    nx, ny = tx * self.project.tile_w + (self.project.tile_w - w) // 2, (ty + 1) * self.project.tile_h - h
                ent.x, ent.y = nx, ny
                self.redraw()
            self.show_inspector(light=True)

    def release(self, e):
        d, self.drag = self.drag, None
        if not d or d.get("pan"):
            return
        if "rect" in d:
            (x0, y0), (x1, y1) = d["rect"]
            xa, xb, ya, yb = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
            if d.get("area"):
                self.remember()
                key = "Zone" if d["area"] == "zone" else "Chase"
                self.sel_ent.set_opt(key, "%d,%d,%d,%d" % (xa + 1, ya + 1, xb + 1, yb + 1))
                self.mode = None
            elif self.brush or self.tool == "Erase":
                self.remember()
                for y in range(ya, yb + 1):
                    for x in range(xa, xb + 1):
                        self.paint_cell(x, y, erase=(self.tool == "Erase" or not self.brush))
            self.show_inspector()
        self.redraw()

    def double(self, e):
        if not self.doc:
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        if not self.inside(tx, ty):
            x, y, z = parse_map_name(self.doc.name)
            dx = -1 if tx < 0 else (1 if tx >= self.project.map_w else 0)
            dy = -1 if ty < 0 else (1 if ty >= self.project.map_h else 0)
            self.open("%d,%d,%d" % (x + dx, y + dy, z))
            return
        if self.layer == "things":
            ent = self.ent_at(px, py)
            if ent is not None:
                self.sel_ent = ent
                if ent.kind == "Trigger":
                    self.edit_script(ent)
                elif ent.kind == "Lock":
                    self.edit_lock(ent)
                elif ent.kind == "Id":
                    self.rename_place(ent)
                elif self.default_verb(ent) == "Read":
                    self.show_inspector()
                    if getattr(self, "_notice_text", None) is not None:
                        self._notice_text.focus_set()
                else:
                    self.open_thing(ent.name)

    def hover(self, e):
        if not self.doc:
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        self._hover = (px, py, bool(e.state & 0x1), bool(e.state & 0x4))
        self.update_ghost()
        if not self.inside(tx, ty):
            x, y, z = parse_map_name(self.doc.name)
            dx = -1 if tx < 0 else (1 if tx >= self.project.map_w else 0)
            dy = -1 if ty < 0 else (1 if ty >= self.project.map_h else 0)
            self.app.info("Map %d,%d,%d (double-click to open it)" % (x + dx, y + dy, z))
            return
        cell = self.doc.cells[ty][tx]
        parts = ["tile %d,%d" % (tx + 1, ty + 1), "x %d y %d" % (px, py), cell.tile]
        if cell.under:
            parts.append("rug %s" % cell.under)
        if cell.decor:
            parts.append("decor %s" % cell.decor)
        if cell.roof:
            parts.append("roof %s (group %s)" % (cell.roof, cell.roof_group))
        if cell.infront:
            parts.append("top %s" % cell.infront)
        for ent in self.doc.placed():
            if ent.kind == "Trigger" and (ent.x, ent.y) == (tx + 1, ty + 1):
                parts.append("trigger: %s" % ent.script)
            if ent.kind == "Lock" and (ent.x, ent.y) == (tx + 1, ty + 1):
                parts.append("lock: %s" % (ent.cond or "always"))
            if ent.kind == "Id" and (ent.x, ent.y) == (tx + 1, ty + 1):
                parts.append("place: %s" % ent.name)
        ent = self.ent_at(px, py) if self.layer == "things" or self.show["preview"].get() else None
        if ent is not None and ent.kind not in TILE_KINDS:
            parts.append("%s %s" % (ent.kind, ent.name) + (" (Id %s)" % ent.opt("Id") if ent.opt("Id") else ""))
            said = self.notice_text(ent)[1] if self.default_verb(ent) == "Read" else None
            if said:
                parts.append("“%s”" % said.replace("\\", " / ")[:90])
        self.app.info("   ·   ".join(parts))

    def context(self, e):
        if not self.doc:
            return
        if self.mode:
            self.mode = None
            self.show_inspector()
            self.redraw()
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        if self.layer != "things" and not e.state & 0x1:      # a tile layer: right-click picks up what's there
            if not self.inside(tx, ty):
                return
            cell = self.doc.cells[ty][tx]
            if not self.layer_name(cell):
                self.app.status("No %s on tile %d,%d to pick (Shift+right-click for the menu)." % (
                    LAYER_NOUN[self.layer], tx + 1, ty + 1), "warn")
                return
            if self.tool not in ("Paint", "Fill", "Rectangle"):
                self.set_tool("Paint")
            self.pick_under(px, py, tx, ty)
            self.app.status("Picked %s: paint with it (Shift+right-click for the menu)." % self.brush)
            return
        if self.brush or self.tool not in ("Select", "Paint"):  # holding something: let go of it and select instead
            self.palette.pick(None)
            self.set_tool("Select" if self.layer == "things" else "Paint")
            if self.inside(tx, ty):
                self.sel_cell = (tx, ty)
                self.sel_ent = self.ent_at(px, py) if self.layer == "things" else None
            self.app.status("Select mode: click to select (right-click again for the menu).")
            self.redraw()
            self.show_inspector()
            return
        if not self.inside(tx, ty):
            return
        cell = self.doc.cells[ty][tx]
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Select this tile", command=lambda: self.select_cell(tx, ty))
        m.add_separator()
        m.add_command(label="Edit the tile %s in Tiles" % cell.tile, command=lambda: self.app.goto("tile", cell.tile))
        if cell.decor:
            m.add_command(label="Edit the decor %s in Tiles" % cell.decor,
                          command=lambda: self.app.goto("tile", cell.decor))
        if cell.roof:
            m.add_command(label="Edit the roof %s in Tiles" % cell.roof, command=lambda: self.app.goto("tile", cell.roof))
        if cell.infront:
            m.add_command(label="Edit the over tile %s in Tiles" % cell.infront,
                          command=lambda: self.app.goto("tile", cell.infront))
        ent = self.ent_at(px, py)
        if ent is not None:
            m.add_separator()
            if ent.kind == "Trigger":
                m.add_command(label="Edit the script %s" % ent.script, command=lambda: self.edit_script(ent))
            elif ent.kind == "Lock":
                m.add_command(label="Edit the lock's condition…", command=lambda: self.edit_lock(ent))
            elif ent.kind == "Id":
                m.add_command(label="Rename the place %s…" % ent.name, command=lambda: self.rename_place(ent))
            else:
                m.add_command(label="Open %s in %s" % (ent.name, self.thing_page(ent.name)),
                              command=lambda: self.open_thing(ent.name))
            m.add_command(label="Delete %s" % (ent.name or ent.kind), command=lambda: self.delete_ent(ent))
        m.add_separator()
        m.add_command(label="Add a trigger here…", command=lambda: self.add_tile_thing("Trigger", tx, ty))
        m.add_command(label="Add a lock here…", command=lambda: self.add_tile_thing("Lock", tx, ty))
        m.add_command(label="Name this tile (a place ID)…", command=lambda: self.add_tile_thing("Id", tx, ty))
        m.add_command(label="Pick what's here into the palette", command=lambda: self.pick_under(px, py, tx, ty))
        m.tk_popup(e.x_root, e.y_root)

    def key(self, e):
        k = e.keysym
        if not self.doc:
            return
        if k in ("1", "2", "3", "4", "5"):
            self.set_layer(LAYERS[int(k) - 1][1])
        elif k.lower() == "p":
            self.show["preview"].set(not self.show["preview"].get())
        elif k.lower() == "w":
            self.show["walk"].set(not self.show["walk"].get())
        elif k.lower() == "z":
            self.show["zones"].set(not self.show["zones"].get())
        elif k.lower() == "g":
            self.show["grid"].set(not self.show["grid"].get())
        elif k in ("Delete", "BackSpace"):
            if self.sel_ent is not None:
                self.delete_ent(self.sel_ent)
            elif self.sel_cell and self.layer in ("decor", "roof", "infront"):
                self.remember()
                self.paint_cell(*self.sel_cell, erase=True)
                self.redraw()
        elif k == "Escape" and self.brush:                  # first, stop painting / placing
            self.palette.pick(None)
            if self.layer == "things":
                self.set_tool("Select")
        elif k == "Escape":
            self.mode, self.sel_ent, self.sel_cell = None, None, None
            self.redraw()
            self.show_inspector()
        elif k in ("Return",) and self.mode == "patrol":
            self.mode = None
            self.show_inspector()
        elif k in ("Left", "Right", "Up", "Down"):
            dx = {"Left": -1, "Right": 1}.get(k, 0)
            dy = {"Up": -1, "Down": 1}.get(k, 0)
            if e.state & 0x4:
                self.step(dx, dy, 0)
            elif self.sel_ent is None and not self.sel_cell:     # nothing selected: the arrows move the view
                self.canvas.xview_scroll(dx * 4, "units")
                self.canvas.yview_scroll(dy * 4, "units")
            elif self.sel_ent is not None:
                self.remember()
                step = 8 if e.state & 0x1 else 1
                if self.sel_ent.kind in TILE_KINDS:
                    self.sel_ent.x += dx
                    self.sel_ent.y += dy
                else:
                    self.sel_ent.x += dx * step
                    self.sel_ent.y += dy * step
                self.redraw()
                self.show_inspector(light=True)
            elif self.sel_cell:
                x, y = self.sel_cell
                if self.inside(x + dx, y + dy):
                    self.select_cell(x + dx, y + dy)
        elif k == "Prior":
            self.step(0, 0, 1)
        elif k == "Next":
            self.step(0, 0, -1)

    # =============================================================================================================
    # Painting
    # =============================================================================================================
    def paint_cell(self, x, y, erase=False):
        cell = self.doc.cells[y][x]
        if self.layer == "map":
            if not self.brush or cell.tile == self.brush:
                return False
            cell.tile = self.brush
        elif self.layer == "decor":
            # (a rug goes under the decor, so a chair can stand on it; erasing takes the top one off first)
            if erase:
                if cell.decor:
                    cell.set_decor(None)
                elif cell.under:
                    cell.set_under(None)
                else:
                    return False
            elif self.project.is_under(self.brush):
                if cell.under == self.brush:
                    return False
                cell.set_under(self.brush)
            else:
                if cell.decor == self.brush:
                    return False
                cell.set_decor(self.brush)
        elif self.layer == "roof":
            name = None if erase else self.brush
            grp = "%02d" % int(float(self.group.get() or 1))
            if (cell.roof or None) == name and (not name or cell.roof_group == grp):
                return False
            cell.set_roof(name, grp)
        elif self.layer == "infront":
            name = None if erase else self.brush
            if (cell.infront or None) == name:
                return False
            cell.set_infront(name)
        return True

    def flood(self, x, y):
        if self.layer != "map" or not self.brush:
            return
        target = self.doc.cells[y][x].tile
        if target == self.brush:
            return
        todo, seen = [(x, y)], set()
        while todo:
            cx, cy = todo.pop()
            if (cx, cy) in seen or not self.inside(cx, cy) or self.doc.cells[cy][cx].tile != target:
                continue
            seen.add((cx, cy))
            self.doc.cells[cy][cx].tile = self.brush
            todo += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]

    def pick_under(self, px, py, tx, ty):
        cell = self.doc.cells[ty][tx]
        if self.layer == "things":
            ent = self.ent_at(px, py)
            key = ent.name if ent is not None and ent.kind not in TILE_KINDS else None
        else:
            key = self.layer_name(cell) or None
            if self.layer == "roof" and cell.roof_group:
                self.group.set(cell.roof_group)
        if key:
            self.pal_search.set("")
            self.pal_kind.set("All")
            self.palette.pick(key)
            self.app.status("Picked %s." % key)

    def thing_page(self, name):
        """Where a placed thing's data is: Tiles for a decor tile placed as an object, else Entities."""
        return "Tiles" if self.project.is_decor_object(name) else "Entities"

    def open_thing(self, name):
        self.app.goto("tile" if self.project.is_decor_object(name) else "entity", name)

    def layer_name(self, cell):
        """What the layer being edited has on cell ("" = nothing)."""
        return {"map": cell.tile, "decor": cell.decor, "roof": cell.roof, "infront": cell.infront}.get(self.layer, "")

    def select_cell(self, x, y):
        self.sel_cell = (x, y)
        if self.layer == "things":
            self.sel_ent = None
        self.redraw()
        self.show_inspector()

    # =============================================================================================================
    # Things
    # =============================================================================================================
    def press_things(self, px, py, tx, ty, shift):
        ent = self.ent_at(px, py, prefer_tile_kind=None)
        if self.tool == "Place" and self.brush:            # (placing goes down wherever the ghost shows, over anything)
            if self.brush in SPECIAL:                      # a trigger, lock or place: on any tile, one of each
                kind = SPECIAL_KIND[self.brush]
                there = next((x for x in self.doc.placed() if x.kind == kind and (x.x, x.y) == (tx + 1, ty + 1)), None)
                if there is not None:
                    self.sel_ent, self.sel_cell = there, (tx, ty)
                    self.app.status("There's already a %s on tile %d,%d: it's selected." % (
                        "place ID" if kind == "Id" else kind.lower(), tx + 1, ty + 1), "warn")
                    self.redraw()
                    self.show_inspector()
                    return
                self.add_tile_thing(kind, tx, ty)
                return
            self.remember()
            name = self.brush
            kind = self.project.entity_type(name)
            ent = Entity(kind, name, 0, 0)
            ent.x, ent.y = self.place_xy(name, px, py, tx, ty, shift)
            if kind == "NPC":
                att = self.project.entities_ini.get(name, "Attitude", "")
                ent.opts = "Attitude=%s" % (att if att in ("Good", "Bad") else "Good")
            self.doc.entities.append(ent)
            self.sel_ent, self.sel_cell = ent, (tx, ty)
            self.redraw()
            self.show_inspector()
            return
        self.sel_cell = (tx, ty)
        self.sel_ent = ent
        if ent is not None:
            self.drag = {"move": ent, "start": (px, py), "orig": (ent.x, ent.y)}
        self.redraw()
        self.show_inspector()

    def add_tile_thing(self, kind, tx, ty):
        there = next((x for x in self.doc.placed() if x.kind == kind and (x.x, x.y) == (tx + 1, ty + 1)), None)
        if there is not None:                               # one of each per tile: show the one there
            self.sel_ent, self.sel_cell = there, (tx, ty)
            if self.layer != "things":
                self.set_layer("things")
            self.redraw()
            self.show_inspector()
            return
        if kind == "Trigger":
            script = self.choose_script("")
            if script is None:
                return
            self.remember()
            ent = Entity("Trigger", x=tx + 1, y=ty + 1, script=script)
        elif kind == "Id":
            name = self.ask_place_name("", "Name tile %d,%d" % (tx + 1, ty + 1))
            if name is None:
                return
            self.remember()
            ent = Entity("Id", name, tx + 1, ty + 1)
        else:
            cond = ConditionBuilder(self, self.project, "$Attr.SomeQuest>=1", title="Lock: open when…",
                                    allow_empty="Always locked").run()
            if cond is None:
                return
            self.remember()
            ent = Entity("Lock", x=tx + 1, y=ty + 1, cond=cond, msg="It's locked.")
        self.doc.entities.append(ent)
        self.sel_ent, self.sel_cell = ent, (tx, ty)
        if self.layer != "things":
            self.set_layer("things")
        self.redraw()
        self.show_inspector()

    def choose_script(self, current):
        from .. import scriptlang as SL
        items = [("＋ New script…", "＋ New script…", "")] + [(s, s, SL.kind_of(self.project, s))
                                                               for s in self.project.scripts()]
        r = PickerDialog(self, "Script for the trigger", items, kinds=SL.KINDS, current=current).run()
        if r == "＋ New script…":
            name = ask_text(self, "New script", "Name for the trigger's script:")
            if not name:
                return None
            return name.strip()
        return r

    def delete_ent(self, ent):
        if ent not in self.doc.entities:
            return
        uses = self.project.place_uses(ent.name) if ent.kind == "Id" else []
        if uses and not messagebox.askyesno("Delete %s" % ent.name, "%s is used by:\n\n%s\n\nDelete it anyway? (They "
                                            "will stop working.)" % (ent.name, "\n".join("%s %s" % u for u in uses[:15])),
                                            parent=self):
            return
        self.remember()
        self.doc.entities.remove(ent)
        if self.sel_ent is ent:
            self.sel_ent = None
        self.redraw()
        self.show_inspector()

    def edit_script(self, ent):
        name = ent.script.strip()
        if not name:
            return
        if name not in self.project.scripts():
            sp = self.app.page_of("script")
            self.app.show(sp)
            sp.new_script(preset={"kind": "A trigger (any name)", "name": name})
            return
        self.app.goto("script", name)

    def edit_lock(self, ent):
        r = ConditionBuilder(self, self.project, ent.cond, title="Lock: open when…", allow_empty="Always locked").run()
        if r is not None and r != ent.cond:
            self.remember()
            ent.cond = r
            self.redraw()
            self.show_inspector()

    # =============================================================================================================
    # The inspector (right)
    # =============================================================================================================
    def show_inspector(self, light=False):
        if light and getattr(self, "_xy_vars", None) and self.sel_ent is not None:
            self._quiet = True
            self._xy_vars[0].set(str(self.sel_ent.x))
            self._xy_vars[1].set(str(self.sel_ent.y))
            self._quiet = False
            return
        f = self.inspector
        for w in f.winfo_children():
            w.destroy()
        self._xy_vars = None
        self._quiet = False
        if not self.doc:
            ttk.Label(f, text="No map open.", style="PanelMuted.TLabel").pack(anchor="w")
            return
        e = self.sel_ent
        if e is not None and e in self.doc.entities:
            {"Trigger": self.insp_trigger, "Lock": self.insp_lock, "NPC": self.insp_npc,
             "Id": self.insp_place}.get(e.kind, self.insp_thing)(f, e)
        elif self.sel_cell:
            self.insp_cell(f)
        else:
            self.insp_map(f)

    def head(self, f, title, sub=""):
        ttk.Label(f, text=title, style="Head.TLabel", font=T.FONT_TITLE, wraplength=T.px(300)).pack(anchor="w")
        if sub:
            ttk.Label(f, text=sub, style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w", pady=(0, 8))

    def link(self, parent, text, cb):
        l = ttk.Label(parent, text=text, style="Link.TLabel", cursor="hand2")
        l.pack(anchor="w", pady=1)
        l.bind("<Button-1>", lambda e: cb())
        return l

    def field(self, parent, label, value, on_set, values=None, width=26):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, style="Panel.TLabel", width=10).pack(side="left")
        v = tk.StringVar(value=value)
        w = ttk.Combobox(row, textvariable=v, values=values, width=width) if values is not None else \
            ttk.Entry(row, textvariable=v, width=width)
        w.pack(side="left", fill="x", expand=True)
        v.trace_add("write", lambda *a: None if self._quiet else on_set(v.get()))
        return v

    def changer(self, ent, attr, conv=str):
        state = {"t": 0}

        def set_(value):
            import time
            try:
                value = conv(value)
            except ValueError:
                return
            if getattr(ent, attr) == value:
                return
            now = time.time()
            if now - state["t"] > 1.2:
                self.remember()
            state["t"] = now
            setattr(ent, attr, value)
            self.redraw()
        return set_

    def insp_map(self, f):
        d = self.doc
        self.head(f, "Map %s" % d.name, "Click a tile or a thing to see it here. Esc lets go of the palette's pick.")
        n = {k: sum(1 for e in d.placed() if e.kind == k) for k in ("MapItem", "StaticObject", "NPC", "Trigger", "Lock",
                                                                    "Id")}
        ttk.Label(f, text="%d NPCs · %d objects · %d items · %d triggers · %d locks · %d places" % (
            n["NPC"], n["StaticObject"], n["MapItem"], n["Trigger"], n["Lock"], n["Id"]), style="Panel.TLabel",
                  wraplength=T.px(300)).pack(anchor="w")
        ttk.Label(f, text="When the player arrives", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w",
                                                                                                    pady=(12, 0))
        if d.name in self.project.scripts():
            self.link(f, "Edit the map's script (%s)" % d.name, lambda: self.app.goto("script", d.name))
        else:
            self.link(f, "＋ Add a script that runs on arrival", lambda: (
                self.app.show(self.app.page_of("script")),
                self.app.page_of("script").new_script(preset={"kind": "When a map is entered", "map": d.name})))
        ttk.Label(f, text="Keys", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(14, 0))
        ttk.Label(f, text="1-5 layers · Shift+click fill · right-click a tile picks it · on Things, right-click selects (again: a menu) · "
                          "Shift+right-click menu · Delete removes · "
                          "arrows move (Shift ×8) · Ctrl+arrows next map · PgUp/PgDn levels · P W Z G views · "
                          "Ctrl+wheel zoom (where the mouse is) · middle-drag or Space+drag moves the view (so do "
                          "the arrows with nothing selected) · double-click an edge to go there",
                  style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")

    def insp_cell(self, f):
        x, y = self.sel_cell
        cell = self.doc.cells[y][x]
        self.head(f, "Tile %d,%d" % (x + 1, y + 1))
        for label, name in (("Ground", cell.tile), ("Rug", cell.under), ("Decor", cell.decor), ("Roof", cell.roof),
                            ("Over", cell.infront)):
            row = ttk.Frame(f, style="Panel.TFrame")
            row.pack(fill="x", pady=3)
            img = self.project.sprite("Tiles", name) if name else None
            ph = photo(img, (32, 32), key=("tile", name)) if img else None
            tk.Label(row, image=ph or "", bg=T.PANEL, width=34, height=34).pack(side="left")
            box = ttk.Frame(row, style="Panel.TFrame")
            box.pack(side="left", padx=6)
            ttk.Label(box, text="%s%s" % (label, (" (group %s)" % cell.roof_group) if label == "Roof" and name else ""),
                      style="PanelMuted.TLabel").pack(anchor="w")
            if name:
                self.link(box, name, lambda n=name: self.app.goto("tile", n))
            else:
                ttk.Label(box, text="none", style="Panel.TLabel").pack(anchor="w")
        things = [e for e in self.doc.placed() if e.kind in TILE_KINDS and (e.x, e.y) == (x + 1, y + 1)]
        ttk.Separator(f).pack(fill="x", pady=8)
        for e in things:
            self.link(f, "%s: %s" % ("Place" if e.kind == "Id" else e.kind, e.script if e.kind == "Trigger" else
                                     e.name if e.kind == "Id" else (e.cond or "always locked")),
                      lambda e=e: (setattr(self, "sel_ent", e), self.set_layer("things") if self.layer != "things"
                                   else None, self.redraw(), self.show_inspector()))
        b = ttk.Frame(f, style="Panel.TFrame")
        b.pack(fill="x", pady=4)
        ttk.Button(b, text="＋ Trigger", style="Small.TButton",
                   command=lambda: self.add_tile_thing("Trigger", x, y)).pack(side="left")
        ttk.Button(b, text="＋ Lock", style="Small.TButton",
                   command=lambda: self.add_tile_thing("Lock", x, y)).pack(side="left", padx=4)
        ttk.Button(b, text="＋ Place ID", style="Small.TButton",
                   command=lambda: self.add_tile_thing("Id", x, y)).pack(side="left")
        ttk.Label(f, text="(Name a tile to use it in scripts and quest markers instead of coordinates: Teleport "
                          "<name>, Change.Tile <name>, Marker1=<name>. Quests: \"＋ the Maps tile\".)",
                  style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w", pady=(10, 0))

    def insp_common(self, f, e, title):
        img = self.project.sprite("Entities", e.name)
        row = ttk.Frame(f, style="Panel.TFrame")
        row.pack(fill="x")
        ph = photo(img, (56, 56), key=("ent56", e.name)) if img else None
        tk.Label(row, image=ph or "", bg=T.PANEL).pack(side="left")
        box = ttk.Frame(row, style="Panel.TFrame")
        box.pack(side="left", padx=8)
        ttk.Label(box, text=e.name.replace("_", " "), style="Head.TLabel", font=T.FONT_TITLE).pack(anchor="w")
        ttk.Label(box, text=title, style="PanelMuted.TLabel").pack(anchor="w")
        self.link(box, "Open in " + self.thing_page(e.name), lambda: self.open_thing(e.name))
        ttk.Separator(f).pack(fill="x", pady=8)
        self.field(f, "Name", e.name, self.changer(e, "name"), values=self.project.placeable())
        xv = self.field(f, "X (px)", str(e.x), self.changer(e, "x", int), width=8)
        yv = self.field(f, "Y (px)", str(e.y), self.changer(e, "y", int), width=8)
        self._xy_vars = (xv, yv)
        ttk.Label(f, text="Drag it on the map (Shift snaps to the tile), or arrows to nudge.",
                  style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")

    def insp_thing(self, f, e):
        self.insp_common(f, e, "Item on the ground" if e.kind == "MapItem" else "Object")
        if e.kind == "MapItem":
            self.field(f, "Quantity", e.qty, self.changer(e, "qty"), width=8)
            every = self.project.entities_ini.get(e.name, "Once", "0") == "1"
            once = tk.BooleanVar(value=every or e.opt("Once") == "1")
            cb = ttk.Checkbutton(f, text="Only once: picked up, it never comes back", variable=once,
                                 command=lambda: self.set_opt(e, "Once", "1" if once.get() else ""))
            cb.pack(anchor="w", pady=(4, 0))
            if every:
                cb.state(["disabled"])
                ttk.Label(f, text="(every %s is: Entities.ini Once=1)" % e.name, style="PanelMuted.TLabel").pack(anchor="w")
        if e.kind == "StaticObject" and self.default_verb(e) == "Read":
            self.notice_box(f, e)
        self.id_field(f, e)
        self.field(f, "Type", e.kind, self.changer(e, "kind"), values=ENTITY_TYPES, width=14)
        ttk.Button(f, text="Delete", style="Danger.TButton", command=lambda: self.delete_ent(e)).pack(anchor="w",
                                                                                                    pady=(10, 0))

    # --- a notice (anything read): its words, kept in its script "Read <Id>" (the first Display.Conversation)
    def notice_text(self, e):
        """(the ScriptDoc, the text with \\ for new lines, the line) of a thing that's read, or (doc/None, None, None)."""
        from ..project import ScriptDoc
        oid = e.opt("Id")
        if not oid:
            return None, None, None
        name = "Read " + oid
        if name not in self.project.scripts():
            return None, None, None
        doc = ScriptDoc(self.project, name)
        for line in doc.commands():
            if line.command == "Display.Conversation" and len(line.args) > 1:
                return doc, line.args[1], line
        return doc, None, None

    def notice_box(self, f, e):
        ttk.Label(f, text="What it says", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 2))
        self._notice_text = None
        oid = e.opt("Id")
        doc, text, line = self.notice_text(e)
        if not oid or doc is None:
            ttk.Label(f, text="Nothing yet: its words go in a script, \"Read <its Id>\"." if not oid else
                      "There's no script \"Read %s\" yet." % oid, style="PanelMuted.TLabel",
                      wraplength=T.px(300)).pack(anchor="w")
            ttk.Button(f, text="＋ Give it words", style="Small.TButton", command=lambda: self.make_notice(e)).pack(
                anchor="w", pady=(2, 0))
            return
        if line is None:
            ttk.Label(f, text="Its script doesn't show words in a Display.Conversation.", style="PanelMuted.TLabel",
                      wraplength=T.px(300)).pack(anchor="w")
            self.link(f, "Edit " + doc.name, lambda: self.app.goto("script", doc.name))
            return
        box = tk.Text(f, height=7, wrap="word", font=T.FONT, bg=T.FIELD, fg=T.TEXT, relief="solid", bd=1,
                      highlightthickness=1, highlightcolor=T.ACCENT, highlightbackground=T.LINE, padx=6, pady=4,
                      undo=True)
        box.insert("1.0", text.replace("\\", "\n"))
        box.pack(fill="x")
        self._notice_text = box
        ttk.Label(f, text="Each new line here is a new line on the notice. Saved as you type, in %s." % doc.name,
                  style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")
        row = ttk.Frame(f, style="Panel.TFrame")
        row.pack(fill="x", pady=(2, 0))
        ttk.Label(row, text="Button", style="Panel.TLabel", width=10).pack(side="left")
        btn = tk.StringVar(value=line.args[2] if len(line.args) > 2 else "Okay")
        ttk.Entry(row, textvariable=btn, width=16).pack(side="left")
        self.link(f, "Edit the whole script", lambda: self.app.goto("script", doc.name))
        state = {"job": None}

        def write():
            state["job"] = None
            if not box.winfo_exists():
                return
            words = box.get("1.0", "end-1c").replace("\t", " ").strip().replace("\r", "").replace("\n", "\\")
            label = btn.get().replace("\t", " ").strip() or "Okay"
            while len(line.args) < 3:
                line.args.append("")
            if line.args[1] == words and line.args[2] == label:
                return
            line.args[1], line.args[2] = words, label
            doc.save()
            self.app.status("Saved what %s says (%s)." % (oid, doc.name), "ok")

        def later(*_a):
            if state["job"]:
                self.after_cancel(state["job"])
            state["job"] = self.after(700, write)
        box.bind("<KeyRelease>", later)
        box.bind("<FocusOut>", lambda ev: write())
        btn.trace_add("write", later)

    def make_notice(self, e):
        """Give a notice an Id (if it hasn't one) and the script Read <Id> with words to fill in."""
        from ..project import write_text_lines
        oid = e.opt("Id")
        if not oid:
            x, y, z = parse_map_name(self.doc.name)
            tx, ty = self.spawn_tile(e)
            oid = ask_text(self, "Give it words", "An Id for this %s (one word, unique in the world): its words go in "
                                                  "the script \"Read <Id>\"." % e.name.replace("_", " "),
                           "%s_%d_%d_%d_%d_%d" % (e.name, x, y, z, tx, ty))
            oid = (oid or "").strip().replace(" ", "_")
            if not oid:
                return
            if oid in self.project.entities() or oid in self.project.items():
                self.app.status("%s is a sprite's name: pick another Id." % oid, "error")
                return
            self.set_opt(e, "Id", oid)
        name = "Read " + oid
        if name not in self.project.scripts():
            write_text_lines(self.project.script_path(name), [
                "// What the %s %s on %s says (its map line has Id=%s). Made in the editor." % (
                    e.name.replace("_", " "), oid, self.doc.name, oid),
                "01\t>Distance.From.Clicked.Entity\t64\t04",
                "02\tDisplay.Conversation\t%s\t...\tOkay\t03" % e.name,
                "03\tEnd",
                "04\tDisplay.Message\tDarkRed\tYou can't read that from here!",
                "05\tEnd"])
            self.project.refresh("scripts")
            self.app.status("Made the script %s: type its words in." % name, "ok")
        self.show_inspector()
        if getattr(self, "_notice_text", None) is not None:
            self._notice_text.focus_set()
            self._notice_text.tag_add("sel", "1.0", "end-1c")

    def default_verb(self, e):
        """The left-click verb on this thing (its Use.Words' first, or the game's own)."""
        if e.kind == "MapItem":
            return "Pickup"
        if e.kind == "NPC":
            return "Attack" if (e.opt("Attitude") or "Good") == "Bad" else "Talk to"
        words = [w.strip() for w in self.project.entities_ini.get(e.name, "Use.Words", "").split(",") if w.strip()]
        return words[0] if words else "Use"

    def id_field(self, f, e):
        """Id= names this one thing: scripts "<Verb> <Id>" (e.g. Pickup CellarKey, Read Ashford, Talk to OldHob) come
        before "<Verb> <Name>". A link to its script for the left-click verb."""
        self.field(f, "Id", e.opt("Id"), lambda v: self.set_opt(e, "Id", v.strip().replace(" ", "_")), width=16)
        ttk.Label(f, text="Names this one (unique in the world): the game runs \"<Verb> <Id>\" before \"<Verb> %s\"."
                  % e.name, style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")
        oid = e.opt("Id")
        if not oid:
            return
        verb = self.default_verb(e)
        mine = sorted(s for s in self.project.scripts() if s.endswith(" " + oid))
        for s in mine:
            self.link(f, "Edit " + s, lambda s=s: self.app.goto("script", s))
        script = "%s %s" % (verb, oid)
        if script not in mine:
            self.link(f, "＋ Make " + script, lambda: (self.app.show(self.app.page_of("script")),
                                                      self.app.page_of("script").new_script(
                                                          preset={"kind": "A trigger (any name)", "name": script})))

    def insp_npc(self, f, e):
        self.insp_common(f, e, "NPC")
        row = ttk.Frame(f, style="Panel.TFrame")
        row.pack(fill="x", pady=(6, 2))
        att = tk.StringVar(value=e.opt("Attitude") or "Good")
        for v, text in (("Good", "Friendly"), ("Bad", "Foe")):
            ttk.Radiobutton(row, text=text, value=v, variable=att,
                            command=lambda: self.set_opt(e, "Attitude", att.get())).pack(side="left", padx=(0, 10))
        stand = tk.BooleanVar(value=e.opt("Stand") == "1")
        ttk.Checkbutton(row, text="Stands still", variable=stand,
                        command=lambda: self.set_opt(e, "Stand", "1" if stand.get() else "")).pack(side="left")
        self.id_field(f, e)
        ttk.Label(f, text="Moving about", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 2))
        zone, chase = self.npc_zone(e), self.npc_chase(e)
        for key, label, val, mode, colour in (("Zone", "Roams in", zone, "zone", "green"),
                                              ("Chase", "Chases in", chase, "chase", "red")):
            r = ttk.Frame(f, style="Panel.TFrame")
            r.pack(fill="x", pady=1)
            text = "%d,%d to %d,%d" % val[0] if val else "?"
            ttk.Label(r, text="%s (%s)" % (label, colour), style="Panel.TLabel", width=16).pack(side="left")
            ttk.Label(r, text=text + ("" if val and val[1] else "  (default)"), style="Panel.TLabel").pack(side="left")
            b = ttk.Frame(f, style="Panel.TFrame")
            b.pack(fill="x")
            ttk.Button(b, text="Draw on the map", style="Small.TButton",
                       command=lambda m=mode: self.start_mode(m)).pack(side="left")
            ttk.Button(b, text="Default", style="Small.TButton",
                       command=lambda k=key: self.set_opt(e, k, "")).pack(side="left", padx=4)
        pts = self.patrol(e)
        r = ttk.Frame(f, style="Panel.TFrame")
        r.pack(fill="x", pady=(8, 1))
        ttk.Label(r, text="Patrol (yellow)", style="Panel.TLabel", width=16).pack(side="left")
        ttk.Label(r, text=("%d points" % len(pts)) if pts else "none (it roams)", style="Panel.TLabel").pack(side="left")
        b = ttk.Frame(f, style="Panel.TFrame")
        b.pack(fill="x")
        ttk.Button(b, text="Add points" if self.mode != "patrol" else "Done (Enter)", style="Small.TButton",
                   command=lambda: self.start_mode("patrol" if self.mode != "patrol" else None)).pack(side="left")
        ttk.Button(b, text="Clear", style="Small.TButton", command=lambda: self.set_opt(e, "Patrol", "")).pack(
            side="left", padx=4)
        mode = tk.StringVar(value=e.opt("PatrolMode") or "Loop")
        cb = ttk.Combobox(b, textvariable=mode, values=["Loop", "PingPong"], width=9, state="readonly")
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda ev: self.set_opt(e, "PatrolMode", "" if mode.get() == "Loop" else
                                                                mode.get()))
        self.field(f, "Pause (s)", e.opt("Pause"), lambda v: self.set_opt(e, "Pause", v.strip()), width=8)
        if self.mode:
            ttk.Label(f, text={"zone": "Drag a rectangle on the map for where it roams.",
                               "chase": "Drag a rectangle on the map for where it may chase you.",
                               "patrol": "Click tiles in order. Enter or right-click to finish."}[self.mode],
                      style="Warn.TLabel", wraplength=T.px(300)).pack(anchor="w", pady=6)
        ttk.Label(f, text="All options", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 0))
        opts = tk.StringVar(value=e.opts)
        ent = ttk.Entry(f, textvariable=opts)
        ent.pack(fill="x")
        opts.trace_add("write", lambda *a: None if self._quiet else self.set_opts_text(e, opts.get()))
        ttk.Button(f, text="Delete", style="Danger.TButton", command=lambda: self.delete_ent(e)).pack(anchor="w",
                                                                                                    pady=(10, 0))

    def set_opt(self, e, key, value):
        if e.opt(key) == value:
            return
        self.remember()
        e.set_opt(key, value)
        self.redraw()
        self.show_inspector()

    def set_opts_text(self, e, text):
        if text == e.opts:
            return
        self.remember()
        e.opts = text
        self.redraw()

    def start_mode(self, mode):
        self.mode = mode
        self.show_inspector()
        self.redraw()

    def insp_trigger(self, f, e):
        self.head(f, "Trigger", "Runs a script when the player walks onto tile %d,%d." % (e.x, e.y))
        v = self.field(f, "Script", e.script, self.changer(e, "script"), values=self.project.scripts())
        b = ttk.Frame(f, style="Panel.TFrame")
        b.pack(fill="x", pady=4)
        ttk.Button(b, text="Choose…", style="Small.TButton",
                   command=lambda: self.choose_into(e, v)).pack(side="left")
        ttk.Button(b, text="Edit the script", style="Small.TButton", command=lambda: self.edit_script(e)).pack(
            side="left", padx=4)
        if e.script and e.script not in self.project.scripts():
            ttk.Label(f, text="There's no script called that yet: Edit makes it.", style="Warn.TLabel").pack(anchor="w")
        self.field(f, "Tile X", str(e.x), self.changer(e, "x", int), width=6)
        self.field(f, "Tile Y", str(e.y), self.changer(e, "y", int), width=6)
        ttk.Button(f, text="Delete", style="Danger.TButton", command=lambda: self.delete_ent(e)).pack(anchor="w",
                                                                                                    pady=(10, 0))

    def choose_into(self, e, var):
        r = self.choose_script(e.script)
        if r:
            var.set(r)

    # --- named places: an Id line names its tile, for scripts (Teleport <name>) and quest markers (Marker1=<name>)
    def place_taken(self, name, mine=None):
        """Where else name (any case) is used as an ID (this map as it is now, the other maps as saved), or ""."""
        key = name.upper()
        for e in self.doc.placed():
            if e is not mine and ((e.kind == "Id" and e.name.upper() == key) or
                                  (e.kind != "Id" and not e.on_tile and e.opt("Id").upper() == key)):
                return "this map, tile %d,%d" % (e.x, e.y) if e.kind == "Id" else "this map's %s" % e.name
        pl = self.project.places().get(key)
        if pl is not None and pl[1] != self.doc.name:
            return "map %s (%s)" % (pl[1], "tile %d,%d" % (pl[2], pl[3]) if pl[4] == "tile" else pl[4])
        return ""

    def ask_place_name(self, current, title, mine=None):
        """A new place ID from the user (a letter, then letters, digits, _ . -; unique in the world), or None."""
        from ..project import PLACE_RE
        name = current
        while True:
            name = ask_text(self, title, "A name for this place, unique in the world (e.g. Old_Well, Ferry_Pier).\n"
                                         "Scripts can use it instead of coordinates; quests as a marker.", name)
            if name is None:
                return None
            name = name.strip().replace(" ", "_")
            if not name or name == current:
                return None
            other = self.place_taken(name, mine)
            if not PLACE_RE.match(name):
                self.app.status("%s: start with a letter, then letters, digits, _ . or -." % name, "warn")
            elif other:
                self.app.status("%s is already used on %s: an ID names one place." % (name, other), "warn")
            elif name in self.project.entities() or name in self.project.tiles():
                self.app.status("%s is a sprite's name: pick another." % name, "warn")
            else:
                return name

    def rename_place(self, ent):
        old = ent.name
        new = self.ask_place_name(old, "Rename the place %s" % old, mine=ent)
        if new is None:
            return
        uses = self.project.place_uses(old)
        self.remember()
        ent.name = new
        self.redraw()
        self.show_inspector()
        if uses and messagebox.askyesno(
                "Rename %s" % old, "%d script(s) and quest(s) use %s:\n\n%s\n\nChange them to %s too?" % (
                    len(uses), old, "\n".join("%s %s" % u for u in uses[:15]), new), parent=self):
            n = self.project.rename_place_uses(old, new)
            self.app.status("Renamed %s to %s in the map and %d file(s): save the map so they match." % (old, new, n),
                            "ok")
        else:
            self.app.status("Renamed %s to %s (save the map)." % (old, new), "ok")

    def insp_place(self, f, e):
        self.head(f, "Place  %s" % e.name, "Tile %d,%d of map %s, named so scripts and quests can use it instead of "
                                           "coordinates." % (e.x, e.y, self.doc.name))
        b = ttk.Frame(f, style="Panel.TFrame")
        b.pack(fill="x", pady=4)
        ttk.Button(b, text="Rename…", style="Small.TButton", command=lambda: self.rename_place(e)).pack(side="left")
        ttk.Button(b, text="Copy the name", style="Small.TButton",
                   command=lambda: (self.clipboard_clear(), self.clipboard_append(e.name),
                                    self.app.status("Copied %s." % e.name))).pack(side="left", padx=4)
        other = self.place_taken(e.name, e)
        if other:
            ttk.Label(f, text="%s is also used on %s: IDs must be unique." % (e.name, other), style="Warn.TLabel",
                      wraplength=T.px(300)).pack(anchor="w")
        ttk.Label(f, text="Use it in a script", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 0))
        ttk.Label(f, text="Teleport  %s  -\nChange.Tile  %s  Well002  0  60\n"
                          "Add.Entity  %s  Rabbit  NPC  -\nQuest marker:  Marker1=%s" % ((e.name,) * 4),
                  style="PanelMuted.TLabel", font=T.MONO, justify="left").pack(anchor="w")
        uses = self.project.place_uses(e.name)
        ttk.Label(f, text="Used by", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 0))
        if not uses:
            ttk.Label(f, text="nothing yet (saved files)", style="PanelMuted.TLabel").pack(anchor="w")
        for kind, what in uses:
            self.link(f, "%s %s" % ("Script" if kind == "script" else "Quest", what),
                      lambda k=kind, w=what: self.app.goto(k, w))
        self.field(f, "Tile X", str(e.x), self.changer(e, "x", int), width=6)
        self.field(f, "Tile Y", str(e.y), self.changer(e, "y", int), width=6)
        ttk.Label(f, text="Drag it to another tile, or arrows to move it.", style="PanelMuted.TLabel").pack(anchor="w")
        ttk.Button(f, text="Delete", style="Danger.TButton", command=lambda: self.delete_ent(e)).pack(anchor="w",
                                                                                                    pady=(10, 0))

    def insp_lock(self, f, e):
        self.head(f, "Lock", "Tile %d,%d can't be walked onto until its condition is true." % (e.x, e.y))
        ttk.Label(f, text="Open when", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w")
        ttk.Label(f, text=e.cond or "never (always locked)", style="Panel.TLabel", wraplength=T.px(300),
                  font=T.MONO).pack(anchor="w")
        ttk.Button(f, text="Edit the condition…", style="Small.TButton", command=lambda: self.edit_lock(e)).pack(
            anchor="w", pady=4)
        ttk.Label(f, text="Message when it's locked", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w",
                                                                                                    pady=(8, 0))
        msg = tk.StringVar(value=e.msg)
        ttk.Entry(f, textvariable=msg).pack(fill="x")
        setter = self.changer(e, "msg")
        msg.trace_add("write", lambda *a: setter(msg.get()))
        self.field(f, "Tile X", str(e.x), self.changer(e, "x", int), width=6)
        self.field(f, "Tile Y", str(e.y), self.changer(e, "y", int), width=6)
        ttk.Button(f, text="Delete", style="Danger.TButton", command=lambda: self.delete_ent(e)).pack(anchor="w",
                                                                                                    pady=(10, 0))
