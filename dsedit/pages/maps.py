"""Maps: maps\\X,Y,Z.txt. Paint the ground, decor (see-through tiles over any ground: chairs, trees, flowers), roofs
and the Over layer (tree tops); place the entities (items, objects, NPCs), triggers and locks; edit NPCs' zones, chase areas and patrols on the map.
A level is one big map: every map on it shows, joined, and painting, filling and dragging carry on from one map into
the next. The map last clicked is the one that's open (its frame in the layer's colour): selecting and the inspector
are its. Zoomed far out, the level's minimap stands in for the maps not changed yet."""
import collections
import copy
import threading
import time
import tkinter as tk
import types
from tkinter import ttk, messagebox

from PIL import Image, ImageEnhance

from .. import theme as T
from .. import world as WD
from ..app import Page
from ..project import MapDoc, Entity, parse_map_name, tile_family, TILE_FAMILIES, ENTITY_TYPES, HOMESTEAD_MAP
from ..render import render, walk_overlay, tile_image
from ..refs import Refs, label as use_label
from ..widgets import (PaletteGrid, photo, ConditionBuilder, PickerDialog, Tooltip, ask_text, Dialog, Segmented)
from .iniform import IniFormPage

LAYERS = [("Ground", "map"), ("Decor", "decor"), ("Roofs", "roof"), ("Over", "infront"), ("Entities", "things"),
          ("All", "all")]
# each layer's colour (the banner over the map and its frame) and what the banner says
LAYER_LOOK = {"map": ("#3d7a3a", "GROUND", "the floor of the map: grass, paths, walls, water"),
              "decor": ("#6a4c93", "DECOR", "see-through tiles over the ground (chairs, trees, flowers); the ground is "
                                            "greyed"),
              "roof": ("#9a3d2c", "ROOFS", "the ground and entities are greyed; roofs hide when the player walks under"),
              "infront": ("#2d6a73", "OVER", "the ground and entities are greyed; the Over layer (tree tops, arches) is "
                                       "drawn over the player"),
              "things": ("#a8692c", "ENTITIES", "items, objects, NPCs, triggers and locks; the ground is greyed"),
              "all": ("#3c5a9a", "ALL", "every layer and everything on it: mark an area, then drag it somewhere or "
                                         "Delete it")}
LAYER_HINTS = {"map": "Paint the ground tiles (1)",
               "decor": "Decor: a chair, a tree, a pot of flowers over any ground tile (2)",
               "roof": "Roof tiles: hidden while the player is under them (3)",
               "infront": "Over: tree tops, arches and the like, drawn over the player (4)",
               "things": "Entities - items, objects, NPCs - and triggers and locks (5)",
               "all": "Every layer at once: mark an area to move or delete all of it (6)"}
LAYER_NOUN = {"map": "tile", "decor": "decor", "roof": "roof", "infront": "over tile"}
TOOL_HINTS = {"Paint": "Click or drag to paint", "Fill": "Fill the area of the same tile (or Shift+click)",
              "Rectangle": "Drag a rectangle to fill", "Erase": "Click or drag to remove", "Pick": "Click to pick "
              "what's there into the palette (or Ctrl+click)", "Select": "Click a thing to select it; drag to move it",
              "Place": "Click to put the palette's pick down",
              "Area": "Drag over part of the map, then Copy or Cut it (the buttons on the right, or Ctrl+C / "
                      "Ctrl+X), and click where its top-left goes - here or on another map: every layer and "
                      "everything on it. On All, drag the marked area to move it, or Delete empties it",
              "Move": "Drag a tile of this layer to another spot (whatever is there swaps places with it; a bed brings "
                      "its foot); on Entities, drag an item, object or NPC"}
CURSORS = {"Paint": "pencil", "Fill": "spraycan", "Rectangle": "tcross", "Erase": "X_cursor", "Pick": "dotbox",
           "Move": "fleur", "Area": "crosshair"}
TOOLS = {"map": ["Paint", "Fill", "Rectangle", "Move", "Area", "Pick"],
         "decor": ["Paint", "Rectangle", "Move", "Erase", "Area", "Pick"],
         "roof": ["Paint", "Rectangle", "Move", "Erase", "Area", "Pick"],
         "infront": ["Paint", "Rectangle", "Move", "Erase", "Area", "Pick"],
         "things": ["Select", "Move", "Area", "Place"],
         "all": ["Area"]}
LAYER_PARTS = {"decor": ("Decor", "Under"), "roof": ("Roof",), "infront": ("Infront",)}   # (what Move carries)
# a bed's head: (its foot, where it lies from the head) - below, or beside it for one lying sideways; they move together
BED_FEET = {"Bed001": ("Bed002", 0, 1), "Bed003": ("Bed004", 1, 0), "Bed006": ("Bed005", -1, 0)}
ZOOMS = ["5%", "10%", "25%", "50%", "75%", "100%", "150%", "200%", "300%"]
FAR = 0.35              # zoomed out further than this, the level is drawn from its minimap (a colour a tile)
PICS = 48               # map pictures kept (full size, for the layer being edited)
SPECIAL = ["(Trigger)", "(Lock)", "(Place ID)"]
SPECIAL_KIND = {"(Trigger)": "Trigger", "(Lock)": "Lock", "(Place ID)": "Id"}
TILE_KINDS = ("Trigger", "Lock", "Id")      # things on a whole tile (Entity.on_tile)
TILE_LOOK = {"Trigger": ("#f0b030", 2, "⚡"), "Lock": ("#e040c0", 6, "🔒"),   # (colour, inset, symbol)
             "Id": ("#4cc9f0", 4, "📍")}
REF_LOOK = ("#ff2e88", "#ffffff")  # (the badge on anything a script, quest or data file points at: its fill, edge)


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


class MoveToMapDialog(Dialog):
    """Where to send an entity: a map, and a tile on it."""
    def __init__(self, parent, project, here, tile):
        super().__init__(parent, "Move to another map", ok="Move it")
        self.project = project
        self.map = tk.StringVar(value=here)
        self.tx, self.ty = tk.StringVar(value=str(tile[0])), tk.StringVar(value=str(tile[1]))
        b = self.body
        ttk.Label(b, text="Map", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(b, textvariable=self.map, values=project.maps(), width=14).grid(row=0, column=1, sticky="w")
        for i, (lab, v) in enumerate((("Tile X (1-%d)" % project.map_w, self.tx),
                                      ("Tile Y (1-%d)" % project.map_h, self.ty))):
            ttk.Label(b, text=lab, style="Panel.TLabel").grid(row=i + 1, column=0, sticky="w", pady=2)
            ttk.Spinbox(b, textvariable=v, from_=1, to=99, width=6).grid(row=i + 1, column=1, sticky="w")
        ttk.Label(b, text="It keeps everything it has (its Id, name, options; an NPC's zone, chase area and patrol "
                          "move with it). Both maps are saved.", style="PanelMuted.TLabel",
                  wraplength=T.px(320)).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def ok(self):
        name = self.map.get().strip()
        try:
            tx, ty = int(self.tx.get()), int(self.ty.get())
        except ValueError:
            return False
        if name not in self.project.maps() or not (1 <= tx <= self.project.map_w and 1 <= ty <= self.project.map_h):
            return False
        return name, tx, ty


class MapPage(Page):
    title = "Maps"
    icon = "🗺"
    kind = "map"

    def __init__(self, app):
        super().__init__(app)
        P = self.project
        self.doc = None                   # the open map: the one last clicked
        self.docs = {}                    # name -> MapDoc: the maps read so far (any level)
        self.loaded = {}                  # name -> the map as saved (None: new), for the maps changed since
        self.touched = set()              # the maps changed (or about to be): what undo and Save look at
        self.level, self._slots = None, None
        self._pics = collections.OrderedDict()    # (name, view) -> its picture, full size
        self._photos = {}                 # (name, view) -> its picture at this zoom, on the canvas
        self._stale = set()               # maps changed since their pictures were made
        self._fill_job = None
        self._drawn, self._center = set(), False   # (the squares on the canvas now; scroll to the open map next)
        self._fresh, self._all_again = set(), False  # (maps to put on the canvas again; or every square in view)
        self._drawn_zoom = None           # (the zoom of the pictures on the canvas)
        self.area = None
        self.layer, self.tool = "map", "Paint"
        self.brush = None                 # the palette's pick
        self.sel_cell, self.sel_ent = None, None
        self.mode = None                  # None, "zone", "chase", "patrol"
        self.zoom = round(T.SCALE * 2) / 2 or 1
        self.show = {k: tk.BooleanVar(value=v) for k, v in (("walk", False), ("zones", False), ("grid", False))}
        for v in self.show.values():
            v.trace_add("write", lambda *a: self.redraw(full=True))
        self.opt = {k: tk.BooleanVar(value=v) for k, v in (("sets", True), ("mix", False), ("smooth", True))}
        self.opt["mix"].trace_add("write", lambda *a: self.pick_brush(self.brush, keep_tool=True))
        self.drag = None
        self._redraw_pending = None
        self._hover = None                # (map px, py, shift) of the mouse over the map, for the ghost
        self._ghosts = {}                 # (brush, layer, zoom) -> the see-through picture of what's about to go down
        self._cursor = ""
        self.refs = Refs(P)               # (what the scripts, quests and data point at: dsedit/refs.py)
        self._refs_job, self._refs_new = None, False
        self.after(500, self.watch_refs)

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
                  command=lambda: self.set_layer(self.layer_var.get()), columns=2,
                  colours={"all": LAYER_LOOK["all"][0]}).pack(fill="x")
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
        of = ttk.Frame(left, style="Panel.TFrame")
        of.pack(fill="x", pady=(4, 0))
        for k, label, tip in (("sets", "Lay out whole sets", "A roof, a rug, the walls round a room or a fence: drag "
                               "a rectangle with any piece of it and the right corners, edges and middle go down."),
                              ("mix", "Mix in look-alikes", "Paint with one tile and its look-alikes (Grass001, "
                               "Grass002...: the same name, walked on the same way) go down at random."),
                              ("smooth", "Smooth coast corners", "Where water turns a corner against grass, sand, "
                               "snow or marsh, the diagonal shore piece goes in by itself.")):
            cb = ttk.Checkbutton(of, text=label, variable=self.opt[k])
            cb.pack(anchor="w")
            Tooltip(cb, tip)
        vf = ttk.Frame(left, style="Panel.TFrame")
        vf.pack(fill="x", pady=(6, 0))
        ttk.Label(vf, text="Show", style="Head.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        for i, (k, label, key) in enumerate((("walk", "Walkable", "W"), ("zones", "All NPC zones", "Z"),
                                             ("grid", "Grid", "G"))):
            cb = ttk.Checkbutton(vf, text="%s (%s)" % (label, key), variable=self.show[k])
            cb.grid(row=1 + i // 2, column=i % 2, sticky="w")

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
        zb = ttk.Combobox(zf, textvariable=self.zoom_var, values=ZOOMS, width=6, state="readonly")
        zb.pack(side="left", padx=4)
        zb.bind("<<ComboboxSelected>>", lambda e: self.set_zoom(int(self.zoom_var.get()[:-1]) / 100, around=None))
        holder = ttk.Frame(mid)
        holder.pack(fill="both", expand=True, pady=(4, 0))
        self.canvas = tk.Canvas(holder, bg="#1a1511", highlightthickness=0)
        xs = ttk.Scrollbar(holder, orient="horizontal", command=self.canvas.xview)
        ys = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=lambda *a: (xs.set(*a), self.view_moved()),
                              yscrollcommand=lambda *a: (ys.set(*a), self.view_moved()))
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
        c.bind("<Configure>", lambda e: self.view_moved())
        # moving the view: drag with the middle button, or hold Space and drag
        c.bind("<ButtonPress-2>", lambda e: (c.scan_mark(e.x, e.y), self.set_cursor("fleur")))
        c.bind("<B2-Motion>", lambda e: c.scan_dragto(e.x, e.y, gain=1))
        c.bind("<ButtonRelease-2>", lambda e: self.update_ghost())
        self._space = False
        c.bind("<KeyPress-space>", self.space_down, add="+")
        c.bind("<KeyRelease-space>", self.space_up, add="+")
        c.bind("<MouseWheel>", lambda e: self.set_zoom(self.zoom * (1.25 if e.delta > 0 else 0.8), around=e))
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

    # ----- what points at what (dsedit/refs.py), read again in the background as the files change
    def watch_refs(self):
        if self._refs_job is None or not self._refs_job.is_alive():
            if self._refs_new:
                self._refs_new = False
                self.redraw(full=True)
                if self.winfo_ismapped():
                    self.show_inspector()
            self._refs_job = threading.Thread(target=self._check_refs, daemon=True)
            self._refs_job.start()
        self.after(2000, self.watch_refs)

    def _check_refs(self):
        try:
            if self.refs.fresh():
                self._refs_new = True
        except Exception:                                # (a file half written: next time)
            self.refs.forget()

    def uses_of(self, doc, e):
        """What points at a thing on doc: by its name (a place, an Id=), or by its kind (the NPC a quest is given by)."""
        R = self.refs
        if e.kind == "Id":
            return R.of_name(e.name)
        if e.kind in TILE_KINDS:
            return []
        return (R.of_name(e.opt("Id")) if e.opt("Id") else []) + (R.of_kind(e.name) if e.kind == "NPC" else [])

    def refs_list(self, f, uses, what="it"):
        """The inspector's list of what points at it: each a link to the script or quest."""
        if not uses:
            return
        row = tk.Frame(f, bg=REF_LOOK[0])
        row.pack(fill="x", pady=(10, 2))
        tk.Label(row, text="◆  Referenced by %d: change %s with care" % (len(uses), what), bg=REF_LOOK[0],
                 fg="white", font=T.FONT_BOLD, anchor="w", justify="left", padx=T.px(6), pady=T.px(3),
                 wraplength=T.px(290)).pack(fill="x")
        for use in uses[:20]:
            kind, name = use
            if kind in ("script", "quest"):
                self.link(f, use_label(use), lambda k=kind, n=name: self.app.goto(k, n))
            else:
                ttk.Label(f, text=use_label(use), style="Panel.TLabel").pack(anchor="w", pady=1)
        if len(uses) > 20:
            ttk.Label(f, text="and %d more" % (len(uses) - 20), style="PanelMuted.TLabel").pack(anchor="w")

    def draw_refs(self, doc, ox, oy, slot):
        """A pink badge, with how many, on everything something points at: the tiles named by their coordinates
        (top-right of the tile), the places and things named, the people quests are given by (top-right of them)."""
        P, c, z = self.project, self.canvas, self.zoom
        tw, th = P.tile_w, P.tile_h
        marks = {}
        for (m, tx, ty), uses in self.refs.tiles.items():
            if m == doc.name:
                k = (ox + tx * tw * z, oy + (ty - 1) * th * z)
                marks[k] = marks.get(k, 0) + len(uses)
        for e in doc.placed():
            uses = self.uses_of(doc, e)
            if not uses:
                continue
            if e.kind in TILE_KINDS:
                k = (ox + e.x * tw * z, oy + (e.y - 1) * th * z)
            else:
                x0, y0, x1, y1 = self.ent_rect(e)
                k = (ox + x1 * z, oy + y0 * z)
            marks[k] = marks.get(k, 0) + len(uses)
        r = min(T.px(9), max(T.px(6), T.px(8) * z))                 # (big enough to see on any screen, zoomed out too)
        for (x, y), n in marks.items():
            c.create_oval(x - 2 * r, y, x, y + 2 * r, fill=REF_LOOK[0], outline=REF_LOOK[1], width=2,
                          tags=("refmark", slot))
            if r >= T.px(7):
                c.create_text(x - r, y + r, text=str(n) if n < 10 else "9+", fill="white",
                              font=("Segoe UI", max(6, int(r * 0.95)), "bold"), tags=("refmark", slot))

    # =============================================================================================================
    # Loading and saving
    # =============================================================================================================
    def load(self, name, fill=None):
        """Opens map name (made new and filled with fill, if given). The maps not changed are read again from their
        files, as they are now."""
        for n in list(self.docs):
            if not self.dirty(n):
                del self.docs[n]
                self.loaded.pop(n, None)
                self.touched.discard(n)
        self.forget_pictures()
        if fill:
            doc = self.docs[name] = MapDoc(self.project, name)
            doc.fill(fill)
            self.loaded[name] = None
            self.touched.add(name)
        self.show_level(parse_map_name(name)[2])
        self.doc = None
        self.activate(name)
        self.redraw(full=True, center=True)
        if name == HOMESTEAD_MAP:
            self.app.status("Homestead: the land a new home starts as (data\\Homestead.txt). Each home gets its own "
                            "copy when it's made, so changes here are for new homes only. Keep the Homestone and "
                            "Home_Arrival.", "warn")

    def open(self, key, tile=None, **kw):
        key = (key or "").strip()
        if not parse_map_name(key):
            return
        if not self.doc or key != self.doc.name:
            if key not in self.project.maps() and key not in self.docs:
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
                if res[0] in self.project.maps() or res[0] in self.docs:
                    self.open(res[0])
                else:
                    self.new_doc(*res)
                return
            if self.doc is None or parse_map_name(key)[2] != self.level:
                self.show_level(parse_map_name(key)[2])
            self.activate(key)
            if not tile:
                self.scroll_to(self.project.map_w // 2, self.project.map_h // 2)
        if tile:
            self.select_cell(tile[0] - 1, tile[1] - 1)
            self.scroll_to(tile[0] - 1, tile[1] - 1)

    def new_doc(self, name, fill):
        """A new map, in memory until it's saved: on its level, open."""
        doc = self.docs[name] = MapDoc(self.project, name)
        doc.fill(fill)
        self.loaded[name] = None
        self.touched.add(name)
        self._slots = None
        if parse_map_name(name)[2] != self.level:
            self.show_level(parse_map_name(name)[2])
        self.activate(name)
        self.redraw(full=True)
        self.scroll_to(self.project.map_w // 2, self.project.map_h // 2)
        self.app.status("New map %s: Save to make the file." % name)

    # ----- the maps read, and the ones changed
    def get_doc(self, name):
        d = self.docs.get(name)
        if d is None:
            d = self.docs[name] = MapDoc(self.project, name)
        return d

    def touch(self, doc):
        """Before doc is changed: it's kept as it was saved (to tell if it's changed), the last undo step gets it as it
        is now if it hasn't it (a paint stroke carried on into it), and its picture is made again."""
        n = doc.name
        if n not in self.loaded:
            self.loaded[n] = doc.snapshot()
        if n not in self.touched:
            self.touched.add(n)
            if self.undo_stack and n not in self.undo_stack[-1][0]:
                self.undo_stack[-1][0][n] = doc.snapshot()
        self._stale.add(n)

    def dirty(self, name):
        if name not in self.touched or name not in self.docs:
            return False
        was = self.loaded.get(name)
        return was is None or self.docs[name].snapshot() != was

    def remember(self):
        if self.doc is not None:
            self.touch(self.doc)
        super().remember()

    def is_dirty(self):
        return any(self.dirty(n) for n in self.touched)

    def current(self):
        changed = [n for n in self.touched if self.dirty(n)]
        if len(changed) > 1:
            return "%d maps" % len(changed)
        return changed[0] if changed else (self.doc.name if self.doc else "")

    def save(self):
        if not self.doc:
            return True
        names = sorted(n for n in self.touched if self.dirty(n))
        for n in names:
            self.save_doc(n, minimap=False)
        self.project.refresh("maps")
        self._slots = None
        self.map_box.configure(values=self.project.maps())
        self.app.status("Saved map%s %s." % ("s" if len(names) > 1 else "", ", ".join(names) or self.doc.name), "ok")
        self.app.refresh_chrome()
        for z in sorted({parse_map_name(n)[2] for n in names if n != HOMESTEAD_MAP}):
            self.rebuild_minimap(z)
        return True

    def save_doc(self, name, minimap=True):
        """One map written to its file (and its level's minimap built again, unless minimap is False)."""
        doc = self.get_doc(name)
        doc.save()
        self.loaded[name] = doc.snapshot()
        if minimap and name != HOMESTEAD_MAP:
            self.project.refresh("maps")
            self._slots = None
            self.rebuild_minimap(parse_map_name(name)[2])

    # ----- the minimap of a saved map's level, built again (the game's minimap and world map, and the editor's
    # world view, show it): in the background, so saving isn't held up; saves while it builds go into one more build
    def rebuild_minimap(self, z):
        import subprocess
        import sys
        import threading
        self._mini_want = getattr(self, "_mini_want", set()) | {z}
        if getattr(self, "_mini_busy", False):
            return
        levels, self._mini_want, self._mini_busy = sorted(self._mini_want), set(), True
        args = [sys.executable, "-I", self.project.p("dev", "migrate", "build_minimaps.py"),
                "--levels", ",".join(str(v) for v in levels)]

        done = []                                           # (the build's result, when it's finished)

        def work():
            done.append(subprocess.run(args, cwd=self.project.root, capture_output=True, text=True))

        def check():                                        # (on the editor's own thread: Tk is only safe there)
            if done:
                self.minimap_built(done[0])
            else:
                self.after(250, check)
        threading.Thread(target=work, daemon=True).start()
        self.after(250, check)

    def minimap_built(self, r):
        self._mini_busy = False
        if r.returncode != 0:
            self.app.status("The minimap couldn't be built again: %s" % ((r.stderr or r.stdout).strip()[-200:]),
                            "error")
        else:
            self.project.config.load()                      # (its Origin.<Z> may have moved: a map at a new edge)
            for k in list(self.project._sprites):
                if k[0] == "Interface" and k[1].startswith("Minimap"):
                    del self.project._sprites[k]
            mini = self.app.page_of("minimap")
            if mini is not None and getattr(mini, "level", None) is not None:
                mini.draw()
            if self.zoom < FAR:                             # (the far view is drawn from it)
                self.redraw(full=True)
        if self._mini_want:                                 # (saved again while it built: once more)
            self.rebuild_minimap(next(iter(self._mini_want)))

    def discard(self):
        for n in list(self.touched):
            if self.loaded.get(n) is None:
                self.docs.pop(n, None)
            elif n in self.docs:
                self.docs[n].restore(self.loaded[n])
        self.touched, self.loaded = set(), {}
        self._slots = None
        self.forget_pictures()
        if self.doc is not None and self.doc.name not in self.docs:
            slots = self.level_slots()
            self.doc = None
            if slots:
                self.activate(next(iter(slots.values())))
        self.redraw(full=True)

    def snapshot(self):
        if not self.doc:
            return None
        return ({n: self.docs[n].snapshot() for n in self.touched | {self.doc.name} if n in self.docs},
                self.doc.name, self.sel_ent_index())

    def restore(self, snap):
        texts, active, sel = snap
        for n, text in texts.items():
            self.get_doc(n).restore(text)
            self._stale.add(n)
        if active != self.doc.name:
            if parse_map_name(active)[2] != self.level:
                self.show_level(parse_map_name(active)[2])
            self.activate(active)
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
        self._slots = None
        self.map_box.configure(values=self.project.maps())
        from ..project import mtime
        again = [n for n, d in self.docs.items() if not self.dirty(n) and d.exists and mtime(d.path) != d.stamp]
        for n in again:                                     # (changed on disk, by a builder or another editor)
            self.docs[n].load()
            self.loaded.pop(n, None)
            self.touched.discard(n)
            self._stale.add(n)
        if again:
            self.redraw()
        self.fill_palette()

    def search_items(self):
        return [(m, "Map " + m + (": the land a new home starts as" if m == HOMESTEAD_MAP else ""))
                for m in self.project.maps()]

    def selected_spot(self):
        """(map, tile x, tile y) of the selected tile, or on Entities the selected entity's (Quests' markers)."""
        if self.doc and self.layer == "things" and self.sel_ent is not None and self.sel_ent in self.doc.entities:
            return (self.doc.name,) + tuple(self.ent_tile(self.sel_ent))
        if self.doc and self.tile_selected():
            return self.doc.name, self.sel_cell[0] + 1, self.sel_cell[1] + 1
        return None

    def tile_selected(self):
        """The selected tile (x, y, from 0), or None: on the Entities layer there's no selected tile, only entities
        (a tile is chosen on the layer that paints it)."""
        return self.sel_cell if self.layer not in ("things", "all") else None

    # ----- the level: its maps as one big map
    def show_level(self, z):
        if z != self.level:
            self.level, self._slots = z, None
            self._photos.clear()
            self._drawn_zoom = None                     # (another level: the canvas cleared)
            self.area = None

    def level_slots(self):
        """{(x, y): map name} of the level shown (new maps not saved yet too)."""
        if self._slots is None:
            self._slots = WD.level_slots(self.project, self.level, [n for n in self.docs if n not in
                                                                    self.project.maps()])
        return self._slots

    def bounds(self):
        """(x0, y0, x1, y1): the level's maps, and a ring of empty squares round them (to make a new map in)."""
        slots = self.level_slots() or {(0, 0): None}
        xs, ys = [p[0] for p in slots], [p[1] for p in slots]
        ring = 0 if self.level == 1000 else 1               # (the homestead's land has nothing round it)
        return min(xs) - ring, min(ys) - ring, max(xs) + ring, max(ys) + ring

    def doc_xy(self, doc=None):
        """(x, y) of a map on its level."""
        x, y, _ = parse_map_name((doc or self.doc).name)
        return (x, y) if (doc or self.doc).name != HOMESTEAD_MAP else (0, 0)

    def activate(self, name):
        """Opens map name of the level shown: what's selected, the inspector and the area marked are its."""
        if self.doc is not None and name == self.doc.name:
            return
        self.doc = self.get_doc(name)
        self.sel_cell, self.sel_ent, self.mode, self.area = None, None, None, None
        self.map_var.set(name)
        for d, b in self.arrow_btns.items():
            b.state(["disabled"] if name == HOMESTEAD_MAP else ["!disabled"])     # (nothing next to it)
        self.redraw()
        self.show_inspector()
        self.app.refresh_chrome()

    def at(self, x, y):
        """(map, x, y on it) of tile x, y counted from the open map's top-left - on it, or on a map round it - or None
        where there's no map."""
        W, H = self.project.map_w, self.project.map_h
        if 0 <= x < W and 0 <= y < H:
            return self.doc, x, y
        if self.doc.name == HOMESTEAD_MAP:
            return None
        mx, my = self.doc_xy()
        dx, dy = x // W, y // H
        name = self.level_slots().get((mx + dx, my + dy))
        if not name:
            return None
        return self.get_doc(name), x - dx * W, y - dy * H

    def tile_at(self, x, y):
        a = self.at(x, y)
        return a[0].cells[a[2]][a[1]].tile if a else None

    def name_at(self, x, y):
        """The map tile x, y (from the open map's top-left) is on, made or not: (its name, made?)."""
        W, H = self.project.map_w, self.project.map_h
        mx, my = self.doc_xy()
        dx, dy = x // W, y // H
        name = self.level_slots().get((mx + dx, my + dy))
        return (name, True) if name else (WD.slot_name(mx + dx, my + dy, self.level), False)

    # --- moving between maps
    def step(self, dx, dy, dz):
        if not self.doc or self.doc.name == HOMESTEAD_MAP:
            return
        x, y, z = parse_map_name(self.doc.name)
        name = "%d,%d,%d" % (x + dx, y + dy, z + dz)
        if dz and name not in self.project.maps() and name not in self.docs:
            there = WD.level_slots(self.project, z + dz)    # (another level, nothing just there: its nearest map)
            if there:
                near = min(there, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
                self.show_level(z + dz)
                self.activate(there[near])
                self.redraw(full=True, center=True)
                self.app.status("Level %d has no map at %d,%d: opened the nearest, %s." % (z + dz, x, y, there[near]))
                return
        self.open(name)

    def new_map(self):
        r = NewMapDialog(self, self.project, self.doc.name if self.doc else "0,0,0").run()
        if not r:
            return
        name, fill = r
        if name in self.project.maps() or name in self.docs:
            self.open(name)
            return
        self.new_doc(name, fill)

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
        Segmented(self.tool_frame, self.tool_var, [(t, t, TOOL_HINTS[t], t) for t in tools],
                  command=lambda: self.set_tool(self.tool_var.get()), columns=3).pack(fill="x")   # (rows of 3: all show)
        col, name, note = LAYER_LOOK[layer]
        self.banner.configure(text="Editing:  " + name, bg=col)
        self.banner_note.configure(text=note)
        if layer == "roof":
            self.group_frame.pack(after=self.tool_frame, fill="x", pady=(4, 0))
        else:
            self.group_frame.pack_forget()
        kinds = ["All"] + ([f for f, _ in TILE_FAMILIES] + ["Other"] if layer not in ("things", "all") else
                           ["Triggers, locks & places"] + ENTITY_TYPES if layer == "things" else [])
        self.pal_kind_box.configure(values=kinds)
        self.pal_kind.set("Roofs" if layer == "roof" else "All")
        self.palette.selected = None
        self.fill_palette()
        self.pick_brush(None, keep_tool=True)
        self.sel_ent = None if layer != "things" else self.sel_ent
        self.redraw(full=True)
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
        if self.layer == "all":                         # (nothing to paint with: it's for moving and clearing)
            pass
        elif self.layer == "things":
            for s in SPECIAL:
                if k in ("All", "Triggers, locks & places") and (not q or q in s.lower()):
                    items.append((s, None, TILE_LOOK[SPECIAL_KIND[s]][2] + "\n" + s.strip("()")))
            for e in P.placeable():
                t = P.entity_type(e)
                if k not in ("All", t) or (q and q not in e.lower()):
                    continue
                items.append((e, P.sprite("Entities", e), e))
        else:
            stand = WD.stand_ins(P)                     # (a range's peaks: one of them stands for them all)
            for t in P.tiles():
                fam = tile_family(t)
                if k not in ("All", fam) or (q and q not in t.lower()) or stand.get(t, t) != t:
                    continue
                # a see-through decor tile can't be a cell's ground (it would show black): it's for the Decor layer
                flat = P.is_under(t)                     # (a rug: painted with the Decor layer, under it)
                if (self.layer == "map" and (P.is_decor(t) or flat)) or \
                        (self.layer == "decor" and not (P.is_decor(t) or flat)):
                    continue
                label = t if t not in stand else "%s (%s: any of %d)" % (
                    t, P.tile_values("Texture").get(t.lower(), ""), WD.texture_count(P, t))
                items.append((t, P.sprite("Tiles", t), label))
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
        """For a tile that's one piece of a set (data\\TileSets.ini): (the set's tiles in order, columns, None, what
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
            elif self.tool in ("Pick", "Erase", "Select", "Move", "Area"):
                self.tool = "Paint"
            self.tool_var.set(self.tool)
        if not key:
            text = "Pick something from the palette to paint with." if self.layer != "things" else \
                "Pick something from the palette to place it."
        elif self.layer == "things":
            text = ("Placing %s: click the map to put one down (Esc stops)." % key) if self.tool == "Place" else \
                "Place tool: puts down %s." % key
        elif self.shape_brush():
            text = "Painting with %s: drag a rectangle to lay out the whole %s (Esc stops)." % (
                key, self.project.tile_set_of(key)[1])
        else:
            text = "Painting with %s (Esc stops)." % key
            alike = WD.look_alikes(self.project, key) if self.opt["mix"].get() else [key]
            if len(alike) > 1:
                text += " Mixed with %s." % ", ".join(a for a in alike if a != key)
        self.brush_label.configure(text=text, wraplength=T.px(280))
        self.update_ghost()

    # =============================================================================================================
    # Drawing
    # =============================================================================================================
    def view_key(self):
        return self.layer, self.show["walk"].get()

    def forget_pictures(self, name=None):
        if name is None:
            self._pics.clear()
            self._photos.clear()
            return
        for k in [k for k in self._pics if k[0] == name]:
            del self._pics[k]
        for k in [k for k in self._photos if k[0] == name]:
            del self._photos[k]

    def layer_picture(self, doc):
        """A map as the layer being edited sees it: that layer bright, what's under it greyed (for where things
        are), and what's over it left out. The All layer shows the map as the game does."""
        P, layer = self.project, self.layer
        mx, my = self.doc_xy(doc)
        org = (mx * P.map_w, my * P.map_h)
        if layer == "all":
            img = render(P, doc, origin=org)
        elif layer == "map":
            img = render(P, doc, roofs=False, infront=False, entities=False, decor=False, origin=org)
        else:
            under = render(P, doc, roofs=False, infront=False, entities=layer not in ("things", "decor"),
                           decor=layer != "decor", origin=org).convert("RGB")
            img = ImageEnhance.Brightness(ImageEnhance.Color(under).enhance(0.4)).enhance(0.76).convert("RGBA")
            img.alpha_composite(render(P, doc, ground=False, roofs=layer == "roof", infront=layer == "infront",
                                       entities=layer == "things", decor=layer == "decor"))
        if self.show["walk"].get():
            img.alpha_composite(walk_overlay(P, doc))
        return img

    def picture(self, name):
        """A map's picture (full size), made if it isn't kept."""
        key = (name, self.view_key())
        if key in self._pics:
            self._pics.move_to_end(key)
            return self._pics[key]
        img = self.layer_picture(self.get_doc(name)).convert("RGB")
        self._pics[key] = img
        while len(self._pics) > PICS:
            self._pics.popitem(last=False)
        return img

    def set_zoom(self, z, around=None):
        """around: the mouse event to zoom about (the spot under it stays put), or None: the middle of the view."""
        z = max(0.05, min(3, z))
        c = self.canvas
        if around is not None:
            sx, sy = around.x, around.y
        else:
            sx, sy = c.winfo_width() / 2, c.winfo_height() / 2
        old = self.zoom
        self._zoom_anchor = (c.canvasx(sx) / old, c.canvasy(sy) / old, sx, sy)
        self.zoom = z
        self.zoom_var.set("%d%%" % round(z * 100))
        self._photos.clear()
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
        """Draws again soon: the open map's picture made again (and any other map changed), only those put on the
        canvas again; with full every square in view (the layer or the view changed), each picture swapped for its
        new one as it's ready, so the maps never go black. Pictures are kept by layer, so most are ready at once."""
        if not self.doc:
            return
        for n in self._stale | {self.doc.name}:
            self.forget_pictures(n)
            self._fresh.add(n)
        self._stale.clear()
        self._all_again = self._all_again or full
        self._center = getattr(self, "_center", False) or center
        if self._redraw_pending:
            self.after_cancel(self._redraw_pending)
        self._redraw_pending = self.after(1, self._redraw)

    # ----- where things are on the canvas: the level's top-left square (of the bounds) at 0, 0
    def map_origin(self, doc=None):
        """Canvas (x, y) of a map's top-left (the open map's), at this zoom."""
        P, z = self.project, self.zoom
        bx, by = self.bounds()[:2]
        mx, my = self.doc_xy(doc)
        return (mx - bx) * P.map_w * P.tile_w * z, (my - by) * P.map_h * P.tile_h * z

    def update_region(self):
        P, z = self.project, self.zoom
        x0, y0, x1, y1 = self.bounds()
        w, h = (x1 - x0 + 1) * P.map_w * P.tile_w * z, (y1 - y0 + 1) * P.map_h * P.tile_h * z
        self.canvas.configure(scrollregion=(0, 0, w, h))
        return w, h

    def visible(self):
        """Canvas (x0, y0, x1, y1) in view."""
        c = self.canvas
        return c.canvasx(0), c.canvasy(0), c.canvasx(c.winfo_width()), c.canvasy(c.winfo_height())

    def visible_slots(self):
        """[(x, y)] of the squares of the level in view, the open map first, then the nearest the middle."""
        P, z = self.project, self.zoom
        bx, by, bx1, by1 = self.bounds()
        mw, mh = P.map_w * P.tile_w * z, P.map_h * P.tile_h * z
        v0, v1, v2, v3 = self.visible()
        out = [(x, y) for y in range(max(by, by + int(v1 // mh)), min(by1, by + int(v3 // mh)) + 1)
               for x in range(max(bx, bx + int(v0 // mw)), min(bx1, bx + int(v2 // mw)) + 1)]
        cx, cy = bx + (v0 + v2) / 2 / mw, by + (v1 + v3) / 2 / mh
        me = self.doc_xy()
        out.sort(key=lambda p: (p != me, (p[0] + 0.5 - cx) ** 2 + (p[1] + 0.5 - cy) ** 2))
        return out

    def view_moved(self):
        """The view scrolled, or grew: the maps come into it are drawn (soon, and only once it's settled)."""
        if not self.doc or self._redraw_pending:
            return
        if self._fill_job:
            self.after_cancel(self._fill_job)
        if self.show["grid"].get():                     # (the grid is drawn over the view only: all again)
            self._fill_job = self.after(30, self._redraw)
        else:
            self._fill_job = self.after(30, self.fill_view)

    def _redraw(self):
        self._redraw_pending = None
        if not self.doc:
            return
        P, c, z = self.project, self.canvas, self.zoom
        fresh, everything = self._fresh, self._all_again
        self._fresh, self._all_again = set(), False
        same = self._drawn_zoom == z and z >= FAR and not self._center and not getattr(self, "_zoom_anchor", None)
        if same and not everything:                     # (just the maps changed: their squares drawn again)
            slots = {n: xy for xy, n in self.level_slots().items()}
            for n in fresh:
                if n in slots:
                    c.delete("slot%d_%d" % slots[n])
                    self._drawn.discard(slots[n])
            c.delete("marks")
        elif same:                                      # (every square again: the old pictures stay till replaced)
            for item in c.find_all():
                if "map" in c.gettags(item):
                    c.dtag(item, "map")
                    c.addtag_withtag("old", item)
                elif "old" not in c.gettags(item):
                    c.delete(item)
            self._drawn = set()
        else:
            c.delete("all")
            self._drawn = set()
        self._drawn_zoom = z
        w, h = self.update_region()
        anchor = getattr(self, "_zoom_anchor", None)
        if anchor:                                      # (zoomed: keep the spot that was under the mouse there)
            self._zoom_anchor = None
            mx, my, sx, sy = anchor
            c.xview_moveto(max(0.0, (mx * z - sx) / w))
            c.yview_moveto(max(0.0, (my * z - sy) / h))
        if self._center:
            self._center = False
            self.scroll_to(P.map_w // 2, P.map_h // 2)
        self.fill_view(first=True)
        self.draw_marks()
        self.map_title.configure(text=("Map %s" % self.doc.name) + ("" if self.doc.exists else "   (new: not saved)"))
        self.update_ghost()
        self.app.refresh_chrome()

    def fill_view(self, first=False):
        """Puts the pictures of the maps in view on the canvas: those kept at once, the rest made a few at a time (so
        the editor never stops answering), each as it's ready. Zoomed far out: one picture of the view, from the
        level's minimap and the maps changed."""
        self._fill_job = None
        if not self.doc:
            return
        if self.zoom < FAR:
            self.draw_far()
            return
        P, c, z = self.project, self.canvas, self.zoom
        slots = self.level_slots()
        mw, mh = P.map_w * P.tile_w * z, P.map_h * P.tile_h * z
        bx, by = self.bounds()[:2]
        start = time.time()
        later = False
        for xy in self.visible_slots():
            name = slots.get(xy)
            if xy in self._drawn:
                continue
            x0, y0 = (xy[0] - bx) * mw, (xy[1] - by) * mh
            slot = "slot%d_%d" % xy
            if name is None:
                self._drawn.add(xy)
                c.delete("old&&" + slot)
                if self.level != 1000:                     # (an empty square: double-click to make a map there)
                    c.create_rectangle(x0 + 2, y0 + 2, x0 + mw - 2, y0 + mh - 2, outline="#3a2f26", dash=(4, 4),
                                       tags=("empty", "under", slot))
                    c.create_text(x0 + mw / 2, y0 + mh / 2, text="＋", fill="#5a4a3c",
                                  font=("Segoe UI", max(10, int(28 * z))), tags=("empty", "under", slot))
                continue
            key = (name, self.view_key())
            ph = self._photos.get(key)
            if ph is None:
                if not first and time.time() - start > 0.08 or first and time.time() - start > 0.15:
                    later = True
                    continue
                img = self.picture(name)
                size = (max(1, int(round(mw))), max(1, int(round(mh))))
                ph = self._photos[key] = photo(img.resize(size, Image.NEAREST if z >= 1 else Image.BILINEAR))
                while len(self._photos) > 160:
                    self._photos.pop(next(iter(self._photos)))
            self._drawn.add(xy)
            c.delete("old&&" + slot)
            c.create_image(x0, y0, image=ph, anchor="nw", tags=("map", "under", slot))
            self.draw_tile_things(self.get_doc(name), x0, y0, slot)
            self.draw_refs(self.get_doc(name), x0, y0, slot)
        c.tag_lower("under")
        c.tag_raise("thing", "under")
        c.tag_raise("refmark")
        if later:
            self._fill_job = self.after(1, self.fill_view)
        else:
            c.delete("old")                                 # (squares gone out of view, or a map no longer there)

    def draw_far(self):
        """The view zoomed far out: one picture, the level's minimap (a colour a tile) with the maps changed since it
        was built drawn over it, and the maps' edges."""
        P, c, z = self.project, self.canvas, self.zoom
        c.delete("far")
        v0, v1, v2, v3 = self.visible()
        w, h = max(1, int(v2 - v0)), max(1, int(v3 - v1))
        bx, by = self.bounds()[:2]
        k = P.tile_w * z                                    # (canvas px a tile)
        gx0, gy0 = bx * P.map_w + v0 / k, by * P.map_h + v1 / k     # (the world tile at the view's top-left)
        out = Image.new("RGB", (w, h), (26, 21, 17))
        mini = P.sprite("Interface", "Minimap%d" % self.level) if self.level != 1000 else None
        origin = P.config.get("Minimap", "Origin.%d" % self.level, "")
        slots = self.level_slots()
        mine = {n for n in self.touched | set(self.docs) if n in slots.values() and (self.dirty(n) or mini is None)}
        if mini is not None and origin:
            try:
                ox, oy = (int(v) for v in origin.split(","))
                ps = max(1, int(P.config.get("Minimap", "Pixel.Size", "1") or 1))
            except ValueError:
                mini = None
            if mini is not None:
                ax, ay = (gx0 - ox * P.map_w) * ps, (gy0 - oy * P.map_h) * ps
                part = mini.convert("RGBA").transform((w, h), Image.EXTENT, (ax, ay, ax + w / k * ps, ay + h / k * ps),
                                                      Image.NEAREST)
                out.paste(part, (0, 0), part)
        if mini is None:                                    # (no minimap yet: every map in view, from its tiles)
            mine |= {slots[xy] for xy in self.visible_slots() if xy in slots}
        for n in mine:
            mx, my = self.doc_xy(self.get_doc(n))
            px, py = (mx * P.map_w - gx0) * k, (my * P.map_h - gy0) * k
            if px > w or py > h or px + P.map_w * k < 0 or py + P.map_h * k < 0:
                continue
            small = self.colours(self.get_doc(n)).resize((max(1, int(P.map_w * k)), max(1, int(P.map_h * k))),
                                                         Image.NEAREST)
            out.paste(small, (int(px), int(py)))
        self._far = photo(out)
        c.create_image(v0, v1, image=self._far, anchor="nw", tags=("far", "under"))
        mw, mh = P.map_w * k, P.map_h * k                   # (the maps' edges, and their names when there's room)
        for (x, y), n in slots.items():
            x0, y0 = (x - bx) * mw, (y - by) * mh
            if x0 > v2 or y0 > v3 or x0 + mw < v0 or y0 + mh < v1:
                continue
            c.create_rectangle(x0, y0, x0 + mw, y0 + mh, outline="#000000", tags=("far",))
            if mw > 60:
                c.create_text(x0 + 3, y0 + 2, text=n, anchor="nw", fill="#f0e6d2", font=("Segoe UI", 7),
                              tags=("far",))
        c.tag_lower("far")
        c.tag_lower("under")

    def colours(self, doc):
        """A map a pixel a tile: its roofs' colours, else its ground's (as the minimap is)."""
        P = self.project
        avg = getattr(self, "_avg", None)
        if avg is None:
            avg = self._avg = {}
        img = Image.new("RGB", (P.map_w, P.map_h))
        px = []
        for row in doc.cells:
            for cell in row:
                t = cell.roof or cell.tile
                if t not in avg:
                    spr = tile_image(P, t)
                    avg[t] = spr.convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0))
                px.append(avg[t])
        img.putdata(px)
        return img

    def draw_tile_things(self, doc, ox, oy, slot=""):
        """A map's triggers, locks and named places (a place's name under its pin), at canvas ox, oy (tagged with
        its square, slot)."""
        if self.layer not in ("things", "all"):
            return
        P, c, z = self.project, self.canvas, self.zoom
        tw, th = P.tile_w, P.tile_h
        for e in doc.placed():
            if e.kind in TILE_KINDS:
                x0, y0 = ox + (e.x - 1) * tw * z, oy + (e.y - 1) * th * z
                col, pad, sym = TILE_LOOK[e.kind]
                c.create_rectangle(x0 + pad, y0 + pad, x0 + tw * z - pad, y0 + th * z - pad, outline=col,
                                   width=2, dash=(4, 3), tags=("thing", slot))
                c.create_text(x0 + tw * z / 2, y0 + th * z / 2, text=sym,
                              fill=col, font=("Segoe UI Symbol", max(8, int(11 * z))), tags=("thing", slot))
                if e.kind == "Id":
                    for dx, dy, fill in ((1, 1, "#000000"), (0, 0, col)):
                        c.create_text(x0 + tw * z / 2 + dx, y0 + th * z + 1 + dy, text=e.name, fill=fill,
                                      anchor="n", font=("Segoe UI", max(7, int(7 * z)), "bold"), tags=("thing", slot))
        for e in doc.placed():
            if e.kind == "NPC" and (self.show["zones"].get() or e is self.sel_ent):
                self.draw_npc_areas(e, ox, oy, z, faint=e is not self.sel_ent, slot=slot)

    def draw_marks(self):
        """Over the maps: the open map's frame, the grid, what's selected, the area marked, the rectangle dragged (all
        tagged "marks": a redraw of the maps changed puts just them back)."""
        before = set(self.canvas.find_all())
        self._draw_marks()
        for item in set(self.canvas.find_all()) - before:
            self.canvas.addtag_withtag("marks", item)

    def _draw_marks(self):
        P, c, z = self.project, self.canvas, self.zoom
        tw, th = P.tile_w, P.tile_h
        ox, oy = self.map_origin()
        W, H = P.map_w * tw * z, P.map_h * th * z
        v0, v1, v2, v3 = self.visible()
        if self.show["grid"].get() and z >= 0.5:      # (Windows can't stipple lines: a dark line, a light one by it)
            gx0, gy0 = ox + ((v0 - ox) // (tw * z)) * tw * z, oy + ((v1 - oy) // (th * z)) * th * z
            x = gx0
            while x <= v2:
                c.create_line(x, v1, x, v3, fill="#000000")
                c.create_line(x + 1, v1, x + 1, v3, fill="#d8cbb4", dash=(1, 3))
                x += tw * z
            y = gy0
            while y <= v3:
                c.create_line(v0, y, v2, y, fill="#000000")
                c.create_line(v0, y + 1, v2, y + 1, fill="#d8cbb4", dash=(1, 3))
                y += th * z
        c.create_rectangle(ox - 2, oy - 2, ox + W + 1, oy + H + 1, outline=LAYER_LOOK[self.layer][0], width=3)
        if self.tile_selected():
            x, y = self.sel_cell
            c.create_rectangle(ox + x * tw * z, oy + y * th * z, ox + (x + 1) * tw * z, oy + (y + 1) * th * z,
                               outline="#ffffff", width=2)
            c.create_rectangle(ox + x * tw * z + 2, oy + y * th * z + 2, ox + (x + 1) * tw * z - 2,
                               oy + (y + 1) * th * z - 2, outline="#000000", width=1)
        if self.sel_ent is not None:
            x0, y0, x1, y1 = self.ent_rect(self.sel_ent)
            c.create_rectangle(ox + x0 * z - 2, oy + y0 * z - 2, ox + x1 * z + 2, oy + y1 * z + 2, outline="#ffe066",
                               width=2, dash=(5, 2))
        clip = getattr(self.app, "clip_region", None)
        if clip is not None and clip.cut and clip.map in self.level_slots().values():   # (cut, waiting to move)
            cx, cy = self.map_origin(self.get_doc(clip.map))
            x0, y0, x1, y1 = clip.rect
            c.create_rectangle(cx + x0 * tw * z, cy + y0 * th * z, cx + (x1 + 1) * tw * z, cy + (y1 + 1) * th * z,
                               outline="#ff9a3c", width=3, dash=(8, 4))
        if self.area:                                           # (marked: white and blue)
            x0, y0, x1, y1 = self.area
            for col, d in (("#ffffff", (6, 3)), ("#2a7fff", (3, 6))):
                c.create_rectangle(ox + x0 * tw * z, oy + y0 * th * z, ox + (x1 + 1) * tw * z,
                                   oy + (y1 + 1) * th * z, outline=col, width=2, dash=d)
        if self.drag and self.drag.get("rect"):
            (x0, y0), (x1, y1) = self.drag["rect"]
            c.create_rectangle(ox + min(x0, x1) * tw * z, oy + min(y0, y1) * th * z, ox + (max(x0, x1) + 1) * tw * z,
                               oy + (max(y0, y1) + 1) * th * z, outline="#66d9ff", width=2, dash=(6, 3),
                               tags="dragrect")

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
        ox, oy = self.map_origin()
        cursor = "arrow"
        if self.at(tx, ty) is None:                         # (no map there: double-click makes one)
            self.set_cursor("plus" if self.level != 1000 else "arrow")
            return
        x0, y0 = ox + tx * tw * z, oy + ty * th * z
        box = (x0, y0, x0 + tw * z, y0 + th * z)
        if self.mode in ("zone", "chase"):
            cursor = "crosshair"
        elif self.mode == "patrol":
            cursor = "target"
            c.create_oval(x0 + tw * z / 2 - 7, y0 + th * z / 2 - 7, x0 + tw * z / 2 + 7, y0 + th * z / 2 + 7,
                          outline="#ffd23c", width=2, tags="ghost")
        elif self.drag and self.drag.get("areamove"):
            cursor = "fleur"                                # (All: the marked area, where it would go)
            (fx, fy), (gx, gy) = self.drag["areamove"], self.drag["to"]
            x0_, y0_, x1_, y1_ = self.area
            ax, ay = x0_ + gx - fx, y0_ + gy - fy
            fits = self.fits(ax, ay, x1_ - x0_ + 1, y1_ - y0_ + 1)
            ph = self.region_photo(self.drag["region"])
            if ph is not None:
                c.create_image(ox + ax * tw * z, oy + ay * th * z, image=ph, anchor="nw", tags="ghost")
            c.create_rectangle(ox + ax * tw * z, oy + ay * th * z, ox + (ax + x1_ - x0_ + 1) * tw * z,
                               oy + (ay + y1_ - y0_ + 1) * th * z, outline="#ff9a3c" if fits else "#ff4040", width=3,
                               dash=(6, 3), tags="ghost")
        elif self.layer == "all" and self.area and self.in_area(tx, ty) and not self.drag:
            cursor = "fleur"
        elif self.tool == "Area" and getattr(self.app, "clip_region", None) is not None and not self.drag:
            cursor = "crosshair"                            # (where a click would put the area down)
            w, h = self.app.clip_region.size
            fits = self.fits(tx, ty, w, h)
            ph = self.region_photo(self.app.clip_region)
            if ph is not None:
                c.create_image(x0, y0, image=ph, anchor="nw", tags="ghost")
            c.create_rectangle(x0, y0, x0 + w * tw * z, y0 + h * th * z, outline="#ff9a3c" if fits else "#ff4040",
                               width=2, dash=(4, 3), tags="ghost")
        elif self.drag and self.drag.get("tilemove"):
            cursor = "fleur"                                # (Move: from where, to where)
            (fx, fy), (gx, gy) = self.drag["tilemove"], self.drag["to"]
            fb = (ox + fx * tw * z, oy + fy * th * z, ox + (fx + 1) * tw * z, oy + (fy + 1) * th * z)
            gb = (ox + gx * tw * z, oy + gy * th * z, ox + (gx + 1) * tw * z, oy + (gy + 1) * th * z)
            cell = self.doc.cells[fy][fx]
            name = cell.tile if self.layer == "map" else next(
                (cell._get(k) for k in LAYER_PARTS[self.layer] if cell._get(k)), "")
            ph = self.ghost_photo(name.rsplit(".", 1)[0] if self.layer == "roof" else name, self.layer)
            if ph is not None and (gx, gy) != (fx, fy):
                c.create_image(gb[0], gb[1], image=ph, anchor="nw", tags="ghost")
            c.create_rectangle(*fb, outline="#ffffff", dash=(3, 3), tags="ghost")
            c.create_rectangle(*gb, outline=LAYER_LOOK[self.layer][0], width=2, tags="ghost")
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

    def region_photo(self, region):
        """A see-through picture of an area cut, copied or being dragged (every layer and everything on it), at this
        zoom: what would go down where the mouse is."""
        P, z = self.project, self.zoom
        key = (id(region), region.map, region.rect, z)
        if getattr(self, "_region_ph", (None,))[0] != key:
            x0, y0 = region.rect[:2]
            w, h = region.size
            ents = []
            for e in region.entities:                       # (from where they stood on their map to the area's corner)
                e = copy.deepcopy(e)
                self.shift_ent(e, -x0, -y0, P.tile_w, P.tile_h)
                ents.append(e)
            doc = types.SimpleNamespace(cells=region.cells, placed=lambda: ents)
            mx, my = parse_map_name(region.map)[:2] if region.map != HOMESTEAD_MAP else (0, 0)
            img = render(P, doc, origin=(mx * P.map_w + x0, my * P.map_h + y0))
            img = img.crop((0, 0, w * P.tile_w, h * P.tile_h))
            img = img.resize((max(1, int(w * P.tile_w * z)), max(1, int(h * P.tile_h * z))),
                             Image.NEAREST if z >= 1 else Image.BILINEAR)
            img.putalpha(img.getchannel("A").point(lambda v: v * 70 // 100))
            self._region_ph = (key, photo(img))
        return self._region_ph[1]

    def set_cursor(self, cursor):
        if cursor != self._cursor:
            self._cursor = cursor
            try:
                self.canvas.configure(cursor=cursor)
            except tk.TclError:
                self.canvas.configure(cursor="arrow")

    def draw_npc_areas(self, e, ox, oy, z, faint=False, slot=""):
        P, c = self.project, self.canvas
        tw, th = P.tile_w, P.tile_h

        def rect(r, col, dash):
            x1, y1, x2, y2 = r
            c.create_rectangle(ox + (x1 - 1) * tw * z, oy + (y1 - 1) * th * z, ox + x2 * tw * z, oy + y2 * th * z,
                               outline=col, width=1 if faint else 2, dash=dash, tags=slot)
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
                c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#ffd23c", outline="#5a4100", tags=slot)
                c.create_text(cx, cy, text=str(i), font=("Segoe UI", 7, "bold"), tags=slot)
            if len(coords) > 1:
                c.create_line(*[v for p in coords for v in p], fill="#ffd23c", width=2, arrow="last", tags=slot)
                if (e.opt("PatrolMode") or "Loop").lower() != "pingpong":
                    c.create_line(*coords[-1], *coords[0], fill="#ffd23c", dash=(4, 4), tags=slot)

    # =============================================================================================================
    # Geometry
    # =============================================================================================================
    def map_px(self, e):
        """Map pixel (x, y) of a mouse event (may be outside the map)."""
        z = self.zoom
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        ox, oy = self.map_origin()
        return (cx - ox) / z, (cy - oy) / z

    def tile_of(self, px, py):
        return int(px // self.project.tile_w), int(py // self.project.tile_h)

    def inside(self, tx, ty):
        return 0 <= tx < self.project.map_w and 0 <= ty < self.project.map_h

    def fits(self, tx, ty, w, h):
        """A w x h area with its top-left at tile tx, ty lies on one map."""
        a, b = self.at(tx, ty), self.at(tx + w - 1, ty + h - 1)
        return a is not None and b is not None and a[0] is b[0]

    def in_area(self, tx, ty):
        return bool(self.area) and self.area[0] <= tx <= self.area[2] and self.area[1] <= ty <= self.area[3]

    def focus_at(self, e):
        """Opens the map under the mouse (if it isn't already): the click is on it. False where there's no map."""
        px, py = self.map_px(e)
        a = self.at(*self.tile_of(px, py))
        if a is None:
            return False
        if a[0] is not self.doc:
            self.activate(a[0].name)
        return True

    def shape_brush(self):
        """The palette's pick is a piece of a set that's laid out whole by dragging (and that's switched on)."""
        if not self.brush or self.layer in ("things", "all") or not self.opt["sets"].get():
            return False
        return WD.shape(self.project, self.brush, 2, 2) is not None

    def ent_size(self, e):
        spr = self.project.sprite("Entities", e.name) if e.kind not in TILE_KINDS else None
        return spr.size if spr is not None else (self.project.tile_w, self.project.tile_h)

    def ent_rect(self, e):
        tw, th = self.project.tile_w, self.project.tile_h
        if e.kind in TILE_KINDS:
            return (e.x - 1) * tw, (e.y - 1) * th, e.x * tw, e.y * th
        w, h = self.ent_size(e)
        return e.x, e.y, e.x + w, e.y + h

    def ents_at(self, px, py):
        """Everything under the mouse, the one a click takes first, then the rest (the next one up, the next...)."""
        hits = [e for e in self.doc.placed() if self.ent_rect(e)[0] <= px < self.ent_rect(e)[2] and
                self.ent_rect(e)[1] <= py < self.ent_rect(e)[3]]
        first = self.ent_at(px, py)
        sprites = sorted((e for e in hits if e is not first and e.kind not in TILE_KINDS),
                         key=lambda e: -self.ent_rect(e)[3])
        return ([first] if first is not None else []) + sprites + [e for e in hits if e is not first and
                                                                     e.kind in TILE_KINDS]

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
        total_w, total_h = self.update_region()
        ox, oy = self.map_origin()
        cx, cy = ox + (tx + 0.5) * tw * z, oy + (ty + 0.5) * th * z
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
        if not self.mode and not self.focus_at(e):      # (a click on another map opens it; on none, nothing)
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        shift, ctrl = e.state & 0x1, e.state & 0x4
        if self.mode in ("zone", "chase") and self.sel_ent is not None:
            self.drag = {"rect": ((tx, ty), (tx, ty)), "area": self.mode}
            self.redraw()
            return
        if self.mode == "patrol" and self.sel_ent is not None:
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
        if self.tool == "Area":                            # (marking an area: the same on every layer)
            if getattr(self.app, "clip_region", None) is not None and not (self.layer == "all" and
                                                                           self.in_area(tx, ty)):
                self.paste_area(at=(tx, ty))                   # (copied or cut: a click puts it down here)
                return
            if self.layer == "all" and self.in_area(tx, ty):   # (All: drag what's marked somewhere else)
                from .. import region as R
                self.drag = {"areamove": (tx, ty), "to": (tx, ty),
                             "region": R.grab(self.doc, self.area, self.ent_tile, False)}
                self.update_ghost()
                return
            self.drag = {"rect": ((tx, ty), (tx, ty)), "sel_area": True}
            self.redraw()
            return
        if self.layer == "things":
            self.press_things(px, py, tx, ty, shift)
            return
        self.sel_cell = (tx, ty)
        tool = "Fill" if shift else self.tool
        if tool in ("Paint", "Rectangle") and self.shape_brush():   # (a roof, a rug, a room: dragged out whole)
            self.drag = {"rect": ((tx, ty), (tx, ty)), "shape": True}
            self.redraw()
            return
        if tool == "Move":
            if not self.layer_has(self.doc.cells[ty][tx]):
                self.app.status("Nothing on the %s layer at %d,%d to move." % (LAYER_LOOK[self.layer][1].lower(),
                                                                             tx + 1, ty + 1), "warn")
                return
            self.drag = {"tilemove": (tx, ty), "to": (tx, ty)}
            self.update_ghost()
            return
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
            elif self.paint_cell(tx, ty, erase=(tool == "Erase")):
                self.smooth([(tx, ty)])
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
        if "tilemove" in self.drag:
            if self.inside(tx, ty):
                self.drag["to"] = (tx, ty)
            self.update_ghost()
            return
        if "areamove" in self.drag:
            self.drag["to"] = (tx, ty)
            self.update_ghost()
            return
        if "rect" in self.drag:
            if self.drag.get("sel_area"):                  # (an area is marked on one map: the open one)
                tx, ty = max(0, min(self.project.map_w - 1, tx)), max(0, min(self.project.map_h - 1, ty))
            if self.drag["rect"][1] != (tx, ty):
                self.drag["rect"] = (self.drag["rect"][0], (tx, ty))
                self.draw_drag()
        elif self.drag.get("paint"):                       # (on into the maps round it, as they join)
            if self.at(tx, ty) is not None and self.paint_cell(tx, ty, erase=self.drag["erase"]):
                self.smooth([(tx, ty)])
                if self.inside(tx, ty):
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

    def draw_drag(self):
        """Only the dragged rectangle drawn again (the maps under it haven't changed)."""
        c = self.canvas
        c.delete("dragrect")
        (x0, y0), (x1, y1) = self.drag["rect"]
        P, z = self.project, self.zoom
        tw, th = P.tile_w, P.tile_h
        ox, oy = self.map_origin()
        c.create_rectangle(ox + min(x0, x1) * tw * z, oy + min(y0, y1) * th * z, ox + (max(x0, x1) + 1) * tw * z,
                           oy + (max(y0, y1) + 1) * th * z, outline="#66d9ff", width=2, dash=(6, 3), tags="dragrect")
        c.create_text(ox + (max(x0, x1) + 1) * tw * z + 4, oy + (max(y0, y1) + 1) * th * z + 2, anchor="nw",
                      text="%d x %d" % (abs(x1 - x0) + 1, abs(y1 - y0) + 1), fill="#66d9ff",
                      font=("Segoe UI", 9, "bold"), tags="dragrect")

    def release(self, e):
        d, self.drag = self.drag, None
        if not d or d.get("pan"):
            return
        if "tilemove" in d:
            if d["to"] != d["tilemove"]:
                self.remember()
                if self.move_cell(d["tilemove"], d["to"]):
                    self.sel_cell = d["to"]
                    self.app.status("Moved the %s from %d,%d to %d,%d." % (
                        LAYER_NOUN[self.layer], d["tilemove"][0] + 1, d["tilemove"][1] + 1, d["to"][0] + 1,
                        d["to"][1] + 1), "ok")
                self.show_inspector()
            self.redraw()
            return
        if "areamove" in d:
            (fx, fy), (gx, gy) = d["areamove"], d["to"]
            if (gx, gy) != (fx, fy):
                self.move_area(self.area[0] + gx - fx, self.area[1] + gy - fy)
            self.redraw()
            return
        if d.get("move") and d.get("moved"):
            self.settle_ent(d["move"])
        if d.get("move") and not d.get("moved") and d.get("again"):
            self.next_here()                            # (a click on what's selected: the next thing under it)
            return
        if "rect" in d:
            (x0, y0), (x1, y1) = d["rect"]
            xa, xb, ya, yb = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
            if d.get("sel_area"):
                self.area = (xa, ya, xb, yb)
                self.app.status("Marked a %dx%d area: %s" % (
                    xb - xa + 1, yb - ya + 1, "drag it to move it, Delete to empty it, Copy or Cut (on the right) to "
                    "put it down somewhere else with a click (Esc: unmark)." if self.layer == "all" else
                    "Copy or Cut it (on the right), then click where it goes (Esc: unmark)."))
                self.redraw()
                self.show_inspector()
                return
            if d.get("area"):
                self.remember()
                key = "Zone" if d["area"] == "zone" else "Chase"
                self.sel_ent.set_opt(key, "%d,%d,%d,%d" % (xa + 1, ya + 1, xb + 1, yb + 1))
                self.mode = None
            elif d.get("shape"):
                self.remember()
                rows = WD.shape(self.project, self.brush, xb - xa + 1, yb - ya + 1)
                done = []
                for j in range(ya, yb + 1):
                    for i in range(xa, xb + 1):
                        name = rows[j - ya][i - xa] if rows else self.brush
                        if name and self.at(i, j) is not None and self.paint_cell(i, j, name=name):
                            done.append((i, j))
                self.smooth(done)
                if rows:
                    self.app.status("Laid out a %dx%d %s." % (xb - xa + 1, yb - ya + 1,
                                                              self.project.tile_set_of(self.brush)[1]), "ok")
            elif self.brush or self.tool == "Erase":
                self.remember()
                done = []
                for y in range(ya, yb + 1):
                    for x in range(xa, xb + 1):
                        if self.at(x, y) is not None and \
                                self.paint_cell(x, y, erase=(self.tool == "Erase" or not self.brush)):
                            done.append((x, y))
                self.smooth(done)
            self.show_inspector()
        self.redraw()

    def double(self, e):
        if not self.doc:
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        if self.at(tx, ty) is None:                     # (an empty square: make a map there)
            if self.level != 1000:
                self.open(self.name_at(tx, ty)[0])
            return
        if not self.inside(tx, ty):
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
        a = self.at(tx, ty)
        if a is None:
            if self.level != 1000:
                self.app.info("No map %s yet (double-click to make it)" % self.name_at(tx, ty)[0])
            return
        doc, lx, ly = a
        cell = doc.cells[ly][lx]
        parts = (["map %s" % doc.name] if doc is not self.doc else []) + ["tile %d,%d" % (lx + 1, ly + 1),
                                                                            cell.tile]
        if doc is self.doc:
            parts.insert(1, "x %d y %d" % (px, py))
        if cell.under:
            parts.append("rug %s" % cell.under)
        if cell.decor:
            parts.append("decor %s" % cell.decor)
        if cell.roof:
            parts.append("roof %s (group %s)" % (cell.roof, cell.roof_group))
        if cell.infront:
            parts.append("top %s" % cell.infront)
        for ent in doc.placed():
            if ent.kind == "Trigger" and (ent.x, ent.y) == (lx + 1, ly + 1):
                parts.append("trigger: %s" % ent.script)
            if ent.kind == "Lock" and (ent.x, ent.y) == (lx + 1, ly + 1):
                parts.append("lock: %s" % (ent.cond or "always"))
            if ent.kind == "Id" and (ent.x, ent.y) == (lx + 1, ly + 1):
                parts.append("place: %s" % ent.name)
        here = self.ents_at(px, py) if doc is self.doc and self.layer in ("things", "all") else []
        ent = here[0] if here else None
        if ent is not None and ent.kind not in TILE_KINDS:
            parts.append("%s %s" % (ent.kind, ent.name) + (" (Id %s)" % ent.opt("Id") if ent.opt("Id") else ""))
            said = self.notice_text(ent)[1] if self.default_verb(ent) == "Read" else None
            if said:
                parts.append("“%s”" % said.replace("\\", " / ")[:90])
        if len(here) > 1:
            parts.append("%d things here: click again (or Tab) for the next" % len(here))
        uses = list(self.refs.of_tile(doc.name, lx + 1, ly + 1))
        for e in [e for e in doc.placed() if e.kind == "Id" and (e.x, e.y) == (lx + 1, ly + 1)] + \
                ([ent] if ent is not None else []):
            uses += [u for u in self.uses_of(doc, e) if u not in uses]
        if uses:
            parts.append("◆ referenced by %s" % ", ".join(use_label(u) for u in uses[:3]) +
                         (" and %d more" % (len(uses) - 3) if len(uses) > 3 else ""))
        self.app.info("   ·   ".join(parts))

    def context(self, e):
        if not self.doc:
            return
        if self.mode:
            self.mode = None
            self.show_inspector()
            self.redraw()
            return
        if not self.focus_at(e):
            return
        px, py = self.map_px(e)
        tx, ty = self.tile_of(px, py)
        if self.layer not in ("things", "all") and not e.state & 0x1:   # a tile layer: right-click picks it up
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
        if self.layer == "things" and (self.brush or self.tool not in ("Select", "Paint")):
            self.palette.pick(None)                         # holding something: let go of it and select instead
            self.set_tool("Select")
            if self.inside(tx, ty):
                self.sel_ent = self.ent_at(px, py)
                self.sel_cell = (tx, ty) if self.sel_ent is not None else None
            self.app.status("Select mode: click to select (right-click again for the menu).")
            self.redraw()
            self.show_inspector()
            return
        if not self.inside(tx, ty):
            return
        cell = self.doc.cells[ty][tx]
        m = tk.Menu(self, tearoff=0)
        if self.layer not in ("things", "all"):              # (on Entities, entities are what's selected)
            m.add_command(label="Select this tile", command=lambda: self.select_cell(tx, ty))
            m.add_separator()
        if self.layer == "all" and self.in_area(tx, ty):
            m.add_command(label="Delete everything in the area", command=self.delete_area)
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
        here = self.ents_at(px, py)
        if len(here) > 1:                                    # (one over another: choose which)
            m.add_separator()
            for x in here:
                m.add_command(label="Select %s" % self.ent_label(x), command=lambda x=x: self.select_ent(x))
        ent = here[0] if here else None
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

    def ent_label(self, e):
        if e.kind == "Trigger":
            return "the trigger (%s)" % e.script
        if e.kind == "Lock":
            return "the lock"
        if e.kind == "Id":
            return "the place %s" % e.name
        return e.name.replace("_", " ") + (" (%s)" % e.opt("Id") if e.opt("Id") else "")

    def select_ent(self, e):
        if self.layer != "things":
            self.set_layer("things")
        self.sel_ent = e
        self.sel_cell = tuple(v - 1 for v in self.ent_tile(e))
        self.redraw()
        self.show_inspector()

    def next_here(self):
        """The next of the things one over another where the selected one is (round to the first again)."""
        if self.sel_ent is None or self._hover is None:
            return
        here = self.ents_at(self._hover[0], self._hover[1])
        if self.sel_ent not in here:
            here = self.ents_at(*self.ent_mid(self.sel_ent))
        if len(here) < 2 or self.sel_ent not in here:
            return
        nxt = here[(here.index(self.sel_ent) + 1) % len(here)]
        self.select_ent(nxt)
        self.app.status("Selected %s (%d of %d here: click again or Tab for the next)." % (
            self.ent_label(nxt), here.index(nxt) + 1, len(here)))

    def ent_mid(self, e):
        x0, y0, x1, y1 = self.ent_rect(e)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def key(self, e):
        k = e.keysym
        if not self.doc:
            return
        if e.state & 0x4 and k.lower() in ("x", "c", "v"):  # Ctrl: cut, copy, paste (an area, or an entity)
            if k.lower() == "v":
                if self._hover is not None:                 # (it goes on the map under the mouse)
                    a = self.at(*self.tile_of(self._hover[0], self._hover[1]))
                    if a is not None and a[0] is not self.doc:
                        ox, oy = self.map_origin()
                        self.activate(a[0].name)
                        nx, ny = self.map_origin()
                        z = self.zoom
                        self._hover = (self._hover[0] + (ox - nx) / z, self._hover[1] + (oy - ny) / z) + \
                            self._hover[2:]
                if getattr(self.app, "clip_last", "") == "region":
                    self.paste_area()
                else:
                    self.paste_ent()
            elif self.area:
                self.clip_area(cut=k.lower() == "x")
            else:
                self.clip_ent(cut=k.lower() == "x")
            return "break"
        if k in ("1", "2", "3", "4", "5", "6"):
            self.set_layer(LAYERS[int(k) - 1][1])
        elif k == "Tab" and self.sel_ent is not None:
            self.next_here()
            return "break"
        elif k.lower() == "w":
            self.show["walk"].set(not self.show["walk"].get())
        elif k.lower() == "z":
            self.show["zones"].set(not self.show["zones"].get())
        elif k.lower() == "g":
            self.show["grid"].set(not self.show["grid"].get())
        elif k in ("Delete", "BackSpace"):
            if self.layer == "all" and self.area:
                self.delete_area()
            elif self.sel_ent is not None:
                self.delete_ent(self.sel_ent)
            elif self.sel_cell and self.layer in ("decor", "roof", "infront"):
                self.remember()
                self.paint_cell(*self.sel_cell, erase=True)
                self.redraw()
        elif k == "Escape" and self.brush:                  # first, stop painting / placing
            self.palette.pick(None)
            if self.layer == "things":
                self.set_tool("Select")
        elif k == "Escape" and getattr(self.app, "clip_region", None) is not None:   # (stop pasting first)
            self.stop_pasting()
        elif k == "Escape" and self.area:                   # (unmark the area first)
            self.area = None
            self.redraw()
            self.show_inspector()
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
            elif self.sel_ent is None and not self.tile_selected():   # nothing selected: the arrows move the view
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
            elif self.tile_selected():
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
    def paint_cell(self, x, y, erase=False, name=None):
        """Paints tile x, y (from the open map's top-left: it may be on a map round it) on the layer being edited:
        with name, else the palette's pick (or one of its look-alikes, mixed in). False if nothing changed."""
        a = self.at(x, y)
        if a is None:
            return False
        doc, lx, ly = a
        cell = doc.cells[ly][lx]
        brush = name or self.brush
        if brush and not name and not erase and self.opt["mix"].get():
            brush = WD.mixed(self.project, brush)
        if self.layer_name(cell) == brush and self.layer == "map" or (erase and not self.layer_has(cell)):
            return False
        self.touch(doc)
        return self.paint_on(cell, brush, erase)

    def paint_on(self, cell, brush, erase):
        if self.layer == "map":
            if not brush or cell.tile == brush:
                return False
            cell.tile = brush
        elif self.layer == "decor":
            # (a rug goes under the decor, so a chair can stand on it; erasing takes the top one off first)
            if erase:
                if cell.decor:
                    cell.set_decor(None)
                elif cell.under:
                    cell.set_under(None)
                else:
                    return False
            elif self.project.is_under(brush):
                if cell.under == brush:
                    return False
                cell.set_under(brush)
            else:
                if cell.decor == brush:
                    return False
                cell.set_decor(brush)
        elif self.layer == "roof":
            name = None if erase else brush
            grp = "%02d" % int(float(self.group.get() or 1))
            if (cell.roof or None) == name and (not name or cell.roof_group == grp):
                return False
            cell.set_roof(name, grp)
        elif self.layer == "infront":
            name = None if erase else brush
            if (cell.infront or None) == name:
                return False
            cell.set_infront(name)
        return True

    # ----- Move: a tile of this layer to another spot (whatever was there goes where it came from)
    def layer_has(self, cell):
        if self.layer == "map":
            return True
        return any(cell._get(k) for k in LAYER_PARTS[self.layer])

    def cell_part(self, x, y):
        """The layer's part of cell x, y: the ground tile, or the overlays this layer holds."""
        cell = self.doc.cells[y][x]
        return cell.tile if self.layer == "map" else tuple(cell._get(k) for k in LAYER_PARTS[self.layer])

    def set_cell_part(self, x, y, part):
        cell = self.doc.cells[y][x]
        if self.layer == "map":
            cell.tile = part
            return
        for kind, v in zip(LAYER_PARTS[self.layer], part):
            if kind == "Decor":
                cell.set_decor(v)
            elif kind == "Under":
                cell.set_under(v)
            else:
                cell._set(kind, v)

    def move_cell(self, src, dst):
        """Moves the layer's tile at src to dst - a bed's head and foot together - and whatever was where it lands
        goes where it came from. False if it doesn't fit."""
        (sx, sy), (dx, dy) = src, dst
        block = [(sx, sy)]
        if self.layer == "decor":
            cells = self.doc.cells
            hx, hy = sx, sy
            for head, (foot, fx, fy) in BED_FEET.items():     # (the foot was dragged: the bed moves by it all the same)
                if cells[sy][sx].decor == foot and self.inside(sx - fx, sy - fy) and \
                        cells[sy - fy][sx - fx].decor == head:
                    hx, hy = sx - fx, sy - fy
            bed = BED_FEET.get(cells[hy][hx].decor)
            if bed and self.inside(hx + bed[1], hy + bed[2]) and cells[hy + bed[2]][hx + bed[1]].decor == bed[0]:
                block = [(hx, hy), (hx + bed[1], hy + bed[2])]
        ox, oy = dx - sx, dy - sy
        to = [(x + ox, y + oy) for x, y in block]
        if not all(self.inside(x, y) for x, y in to):
            self.app.status("It doesn't fit there.", "warn")
            return False
        was = {c: self.cell_part(*c) for c in set(block) | set(to)}
        now = dict(was)
        for s, d in zip(block, to):
            now[d] = was[s]
        for left, landed in zip([c for c in block if c not in to], [c for c in to if c not in block]):
            now[left] = was[landed]                         # (what was in the way, into the space it left)
        for c, part in now.items():
            if part != was[c]:
                self.set_cell_part(c[0], c[1], part)
        return True

    def flood(self, x, y):
        """Fills the ground that's all one tile round x, y with the palette's pick - on across the maps round it, as
        they join. (A range's peaks, painted from one texture, count as one tile.)"""
        if self.layer != "map" or not self.brush:
            return
        stand = WD.stand_ins(self.project)
        kind = lambda t: stand.get(t, t)
        target = kind(self.tile_at(x, y))
        if target == kind(self.brush):
            return
        todo, seen = [(x, y)], set()
        while todo:
            cx, cy = todo.pop()
            if (cx, cy) in seen:
                continue
            t = self.tile_at(cx, cy)
            if t is None or kind(t) != target:
                continue
            seen.add((cx, cy))
            if len(seen) > 200000:
                self.app.status("That's too much to fill at once (over 200,000 tiles): fence it in first.", "warn")
                return
            todo += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
        maps = {self.at(cx, cy)[0].name for cx, cy in seen}
        if len(maps) > 12 and not messagebox.askyesno(
                "Fill", "That fills %d tiles across %d maps. Go on?" % (len(seen), len(maps)), parent=self):
            return
        for cx, cy in seen:
            self.paint_cell(cx, cy)
        self.smooth(seen)
        if len(maps) > 1:
            self.app.status("Filled %d tiles across %d maps." % (len(seen), len(maps)), "ok")

    def smooth(self, cells):
        """The diagonal shore pieces round the ground just painted, where the water turns a corner (if that's
        switched on, and what was painted isn't itself a piece)."""
        if self.layer != "map" or not cells or not self.opt["smooth"].get():
            return
        sets = WD.shore_sets(self.project)
        if any(self.brush == pat % n for pat in sets.values() for n in range(2, 10)):
            return

        def put(x, y, name):
            a = self.at(x, y)
            self.touch(a[0])
            a[0].cells[a[2]][a[1]].tile = name
        WD.smooth_corners(self.project, self.tile_at, put, set(cells))

    # ----- All: everything in the marked area, moved or cleared
    def area_ents(self, doc, rect):
        from .. import region as R
        return [e for e in doc.placed() if R.inside(rect, self.ent_tile(e)[0] - 1, self.ent_tile(e)[1] - 1)]

    def delete_area(self):
        """Everything in the marked area gone: its entities, its decor, roofs and tree tops, and its ground the ground
        round it."""
        from .. import region as R
        if not self.area:
            return
        gone = self.area_ents(self.doc, self.area)
        x0, y0, x1, y1 = self.area
        used = [(e.opt("Id") or e.name) for e in gone if self.uses_of(self.doc, e)] + \
            ["tile %d,%d" % (x + 1, y + 1) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
             if self.refs.of_tile(self.doc.name, x + 1, y + 1)]
        if used and not messagebox.askyesno("Delete the area", "Scripts, quests or data point at these:\n\n%s\n\n"
                                            "Delete them anyway? (They will stop working.)" % "\n".join(used[:15]),
                                            parent=self):
            return
        self.remember()
        self.doc.entities = [e for e in self.doc.entities if e not in gone]
        R.clear(self.doc, self.area, R.ground_round(self.doc, self.area))
        self.sel_ent = None
        self.app.status("Emptied the %dx%d area (%d entities gone). Undo brings it back." % (
            self.area[2] - self.area[0] + 1, self.area[3] - self.area[1] + 1, len(gone)), "ok")
        self.redraw()
        self.show_inspector()

    def move_area(self, tx, ty):
        """The marked area, everything in it, to tile tx, ty (its new top-left, from the open map's: it may be on a
        map round it). Within its map it's an ordinary change; onto another, it's the same as cutting and pasting
        it there (both maps saved, and what points at it follows)."""
        from .. import region as R
        x0, y0, x1, y1 = self.area
        w, h = x1 - x0 + 1, y1 - y0 + 1
        if not self.fits(tx, ty, w, h):
            self.app.status("It doesn't fit there: an area stays on one map.", "warn")
            return
        doc, lx, ly = self.at(tx, ty)
        if doc is self.doc:
            self.remember()
            shift = lambda e, dx, dy: self.shift_ent(e, dx, dy, self.project.tile_w, self.project.tile_h)
            fresh = R.grab(self.doc, self.area, self.ent_tile, True)
            gone = self.area_ents(self.doc, self.area)
            self.doc.entities = [e for e in self.doc.entities if e not in gone]
            R.clear(self.doc, self.area, R.ground_round(self.doc, self.area))
            R.put(self.doc, fresh, lx, ly, shift)
            self.area = (lx, ly, lx + w - 1, ly + h - 1)
            self.app.status("Moved the area (%d entities). Scripts that name its tiles by number may need a look: "
                            "Ctrl+X / Ctrl+V moves it and follows them." % len(gone), "ok")
            self.redraw()
            self.show_inspector()
            return
        self.app.clip_region = R.grab(self.doc, self.area, self.ent_tile, True)
        self.app.clip_last = "region"
        self.activate(doc.name)
        self.paste_area(at=(lx, ly))

    def pick_under(self, px, py, tx, ty):
        cell = self.doc.cells[ty][tx]
        if self.layer == "things":
            ent = self.ent_at(px, py)
            key = ent.name if ent is not None and ent.kind not in TILE_KINDS else None
        else:
            key = self.layer_name(cell) or None
            key = WD.stand_ins(self.project).get(key, key)     # (a range's peak: the one the palette shows)
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
        if self.layer == "things":                          # (Entities: what stands on that tile, if anything)
            here = [e for e in self.doc.placed() if tuple(self.ent_tile(e)) == (x + 1, y + 1)]
            self.sel_ent = next((e for e in here if e.kind not in TILE_KINDS), here[0] if here else None)
            self.sel_cell = (x, y) if self.sel_ent is not None else None
        else:
            self.sel_cell = (x, y)
        self.redraw()
        self.show_inspector()

    # =============================================================================================================
    # Entities (the "things" layer)
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
        here = self.ents_at(px, py)
        again = self.sel_ent is not None and self.sel_ent in here and len(here) > 1
        if again:                                           # (what's selected is under the mouse: drag it, or
            ent = self.sel_ent                              # a click without a drag takes the next one under it)
        self.sel_ent = ent                                  # (nothing there: nothing selected - not the tile)
        self.sel_cell = (tx, ty) if ent is not None else None
        if ent is not None:
            self.drag = {"move": ent, "start": (px, py), "orig": (ent.x, ent.y), "again": again}
            if len(here) > 1 and not again:
                self.app.status("%d things here: click again (or Tab) for the next, or right-click to choose." %
                                len(here))
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

    # ----- moving an entity to another map: a dialog, or cut and paste (Ctrl+X / Ctrl+C, then Ctrl+V on any map)
    def ent_tile(self, ent):
        """The 1-based tile an entity stands on (its feet), or a tile thing's own tile."""
        if ent.kind in TILE_KINDS:
            return ent.x, ent.y
        w, h = self.ent_size(ent)
        tx, ty = self.tile_of(ent.x + w / 2, ent.y + h - 1)
        return tx + 1, ty + 1

    @staticmethod
    def shift_ent(ent, dtx, dty, tw, th):
        """ent moved by (dtx, dty) tiles - its spot in its tile kept - and an NPC's zone, chase area and patrol too."""
        if ent.kind in TILE_KINDS:
            ent.x, ent.y = ent.x + dtx, ent.y + dty
            return
        ent.x, ent.y = ent.x + dtx * tw, ent.y + dty * th
        for key in ("Zone", "Chase"):
            v = ent.opt(key)
            if v and len(v.split(",")) == 4:
                try:
                    a = [int(float(n)) for n in v.split(",")]
                except ValueError:
                    continue
                ent.set_opt(key, "%d,%d,%d,%d" % (a[0] + dtx, a[1] + dty, a[2] + dtx, a[3] + dty))
        pat = ent.opt("Patrol")
        if pat:
            pts = []
            for p in pat.split("/"):
                try:
                    x, y = (int(float(n)) for n in p.split(","))
                    pts.append("%d,%d" % (x + dtx, y + dty))
                except ValueError:
                    pts.append(p)
            ent.set_opt("Patrol", "/".join(pts))

    def settle_ent(self, ent):
        """An entity dragged past its map's edge goes onto the map its feet are on now (if there's one there), and it
        always lies wholly on the map it's on (the game counts one with its corner off the map as lost)."""
        if ent.kind in TILE_KINDS or ent not in self.doc.entities:
            return
        P = self.project
        tx, ty = self.ent_tile(ent)
        if not self.inside(tx - 1, ty - 1):
            a = self.at(tx - 1, ty - 1)
            if a is not None and a[0] is not self.doc:
                there, lx, ly = a
                self.touch(there)
                self.shift_ent(ent, lx + 1 - tx, ly + 1 - ty, P.tile_w, P.tile_h)
                self.doc.entities.remove(ent)
                there.entities.append(ent)
                self.activate(there.name)
                self.sel_ent = ent
                self.app.status("Moved the %s onto map %s." % (ent.name.replace("_", " "), there.name), "ok")
        w, h = self.ent_size(ent)
        ent.x = max(0, min(P.map_w * P.tile_w - w, ent.x))
        ent.y = max(0, min(P.map_h * P.tile_h - h, ent.y))

    def move_to_map(self, ent):
        if ent not in self.doc.entities:
            return
        r = MoveToMapDialog(self, self.project, self.doc.name, self.ent_tile(ent)).run()
        if not r:
            return
        name, tx, ty = r
        ox, oy = self.ent_tile(ent)
        if name == self.doc.name:                       # (the same map: just to that tile)
            self.remember()
            self.shift_ent(ent, tx - ox, ty - oy, self.project.tile_w, self.project.tile_h)
            self.redraw()
            self.show_inspector()
            return
        what = ent.name.replace("_", " ") or ent.kind
        if self.is_dirty() and not messagebox.askyesno(
                "Move to %s" % name, "There are changes not saved yet: they're saved now too (with the %s moved). "
                "Go on?" % what, parent=self):
            return
        moved = copy.deepcopy(ent)
        self.shift_ent(moved, tx - ox, ty - oy, self.project.tile_w, self.project.tile_h)
        self.remember()
        there = self.get_doc(name)
        self.touch(there)
        there.entities.append(moved)
        self.doc.entities.remove(ent)
        self.sel_ent = None
        self.save()
        self.app.status("Moved the %s to map %s, tile %d,%d (both maps saved)." % (what, name, tx, ty), "ok")
        if messagebox.askyesno("Moved", "Open map %s to see it there?" % name, parent=self):
            self.open(name)
            self.sel_ent = next((x for x in self.doc.entities if x.line() == moved.line()), None)
            if self.layer != "things":
                self.set_layer("things")
            self.scroll_to(tx - 1, ty - 1)
        self.redraw()
        self.show_inspector()

    def clip_ent(self, cut):
        """Ctrl+C / Ctrl+X: the selected entity, kept to paste (on this map or another); cut takes it off this one."""
        e = self.sel_ent
        if not self.doc or e is None or e not in self.doc.entities:
            return
        self.app.clip_entity = (copy.deepcopy(e), self.ent_tile(e))
        self.app.clip_last = "entity"
        if cut:
            self.remember()
            self.doc.entities.remove(e)
            self.sel_ent = None
            self.redraw()
            self.show_inspector()
        self.app.status("%s the %s: open any map, put the mouse where it goes and press Ctrl+V." % (
            "Cut" if cut else "Copied", e.name.replace("_", " ") or e.kind), "ok")

    def paste_ent(self):
        """Ctrl+V: the cut or copied entity, put down on the tile under the mouse (or where it was)."""
        clip = getattr(self.app, "clip_entity", None)
        if not self.doc or not clip:
            return
        ent, (ox, oy) = copy.deepcopy(clip[0]), clip[1]
        tx, ty = ox, oy
        if self._hover is not None:
            hx, hy = self.tile_of(self._hover[0], self._hover[1])
            if self.inside(hx, hy):
                tx, ty = hx + 1, hy + 1
        self.remember()
        self.shift_ent(ent, tx - ox, ty - oy, self.project.tile_w, self.project.tile_h)
        self.doc.entities.append(ent)
        if self.layer != "things":
            self.set_layer("things")
        self.sel_ent = ent
        self.redraw()
        self.show_inspector()
        self.app.status("Pasted the %s on tile %d,%d (Save to keep it)." % (ent.name.replace("_", " ") or ent.kind,
                                                                           tx, ty), "ok")

    # ----- an area: every layer and everything on it, cut or copied, pasted here or on another map (dsedit/region.py)
    def clip_area(self, cut):
        """Ctrl+X / Ctrl+C with an area marked: it's kept to paste. Cut marks it to move: it goes when it's pasted
        (taken from here and put down there at once, both maps saved), so nothing is lost if it never is."""
        from .. import region as R
        self.app.clip_region = R.grab(self.doc, self.area, self.ent_tile, cut)
        self.app.clip_last = "region"
        w, h = self.app.clip_region.size
        if self.tool != "Area":
            self.set_tool("Area")
        self.redraw()
        self.show_inspector()
        self.app.status("%s a %dx%d area of %s: click where its top-left corner goes, here or on any map (Esc: "
                        "stop)." % ("Cut" if cut else "Copied", w, h, self.doc.name), "ok")

    def stop_pasting(self):
        self.app.clip_region = None
        self.update_ghost()
        self.redraw()
        self.show_inspector()
        self.app.status("Stopped pasting.")

    def paste_area(self, at=None):
        """A click (or Ctrl+V): the area cut or copied, its top-left on the tile under the mouse (or at, a tile of the
        open map). A copy stays to put down again; a cut is moved once."""
        from .. import region as R
        clip = getattr(self.app, "clip_region", None)
        if not self.doc or clip is None:
            return
        if at is None and self._hover is None:
            self.app.status("Click where the area's top-left corner goes.", "warn")
            return
        tx, ty = at or self.tile_of(self._hover[0], self._hover[1])
        w, h = clip.size
        if not (self.inside(tx, ty) and self.inside(tx + w - 1, ty + h - 1)):
            self.app.status("It doesn't fit there: a %dx%d area needs its top-left at least %d tiles from the right "
                            "edge and %d from the bottom." % (w, h, w, h), "warn")
            return
        shift = lambda e, dx, dy: self.shift_ent(e, dx, dy, self.project.tile_w, self.project.tile_h)
        if not clip.cut:                                       # a copy: an ordinary edit (Save to keep it)
            self.remember()
            copy_ = R.Region(clip.map, clip.rect, clip.cells, R.strip_names(copy.deepcopy(clip.entities)), False)
            R.put(self.doc, copy_, tx, ty, shift)
            self.area = (tx, ty, tx + w - 1, ty + h - 1)
            self.redraw(full=True)
            self.show_inspector()
            self.app.status("Pasted a copy (its Ids and place names left off: they must be unique). Click again "
                            "for another, Esc to stop; Save to keep them.", "ok")
            return
        src, rect = clip.map, clip.rect
        if (tx, ty) == rect[:2] and src == self.doc.name:
            return
        if self.is_dirty() and not messagebox.askyesno(
                "Move an area", "Moving it saves the map%s, and the other changes not saved yet are saved too. "
                "Go on?" % ("" if src == self.doc.name else "s"), parent=self):
            return
        standing = lambda doc, r: [e for e in doc.placed() if R.inside(r, self.ent_tile(e)[0] - 1,
                                                                       self.ent_tile(e)[1] - 1)]
        here = src == self.doc.name
        source = self.doc if here else self.get_doc(src)
        self.remember()
        self.touch(source)
        own = R.own_scripts(self.project, source)
        fresh = R.grab(source, rect, self.ent_tile, True)       # (as it is now, not as it was when cut)
        gone = standing(source, rect)
        source.entities = [e for e in source.entities if e not in gone]
        R.clear(source, rect, R.ground_round(source, rect))
        already = len(standing(self.doc, (tx, ty, tx + w - 1, ty + h - 1)))
        R.put(self.doc, fresh, tx, ty, shift)
        self.save()
        changed, check = R.update_refs(self.project, src, rect, self.doc.name, tx - rect[0], ty - rect[1], own)
        self.project.refresh("scripts")
        self.app.clip_region = None
        self.area = (tx, ty, tx + w - 1, ty + h - 1)
        self.redraw(full=True)
        self.show_inspector()
        note = "Moved the area%s (%d entities; %s saved)." % ("" if here else " from %s" % src, len(gone),
                                                            "the map" if here else "both maps")
        if changed:
            note += " Updated %d place%s that pointed at it." % (len(changed), "" if len(changed) == 1 else "s")
        if already:
            note += " %d entit%s already stood where it landed: left as they were." % (
                already, "y" if already == 1 else "ies")
        self.app.status(note, "ok")
        if changed or check:
            messagebox.showinfo("Moved", ("Updated to point at its new place:\n  " + "\n  ".join(changed[:25]) + "\n\n"
                                          if changed else "") +
                                ("Look at these - coordinates in the area that couldn't be followed safely:\n  " +
                                 "\n  ".join(check[:25]) if check else ""), parent=self)

    def delete_ent(self, ent):
        if ent not in self.doc.entities:
            return
        uses = self.uses_of(self.doc, ent)
        if uses and not messagebox.askyesno("Delete %s" % ent.name, "%s is referenced by:\n\n%s\n\nDelete it anyway? "
                                            "(They will stop working.)" % (ent.name, "\n".join(use_label(u) for u in
                                                                                             uses[:15])),
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
            mv = ttk.Frame(f, style="Panel.TFrame")             # (to another map: here, or cut and paste)
            mv.pack(anchor="w", pady=(10, 0))
            ttk.Button(mv, text="Move to another map…", style="Small.TButton",
                       command=lambda: self.move_to_map(e)).pack(side="left")
            ttk.Button(mv, text="Cut (Ctrl+X)", style="Small.TButton",
                       command=lambda: self.clip_ent(True)).pack(side="left", padx=4)
        elif self.area or getattr(self.app, "clip_region", None) is not None:
            self.insp_area(f)
        elif self.tile_selected():
            self.insp_cell(f)
        else:
            self.insp_map(f)

    def insp_area(self, f):
        """An area marked, or one copied or cut and waiting to be put down: Copy, Cut (and on All, Delete)."""
        clip = getattr(self.app, "clip_region", None)
        if self.area:
            x0, y0, x1, y1 = self.area
            self.head(f, "Area %d x %d" % (x1 - x0 + 1, y1 - y0 + 1), "Tiles %d,%d to %d,%d of %s: every layer and "
                      "everything on it." % (x0 + 1, y0 + 1, x1 + 1, y1 + 1, self.doc.name))
            row = ttk.Frame(f, style="Panel.TFrame")
            row.pack(anchor="w", pady=(4, 0))
            ttk.Button(row, text="Copy", style="Accent.TButton", command=lambda: self.clip_area(False)).pack(side="left")
            ttk.Button(row, text="Cut", command=lambda: self.clip_area(True)).pack(side="left", padx=4)
            if self.layer == "all":
                ttk.Button(row, text="Delete", command=self.delete_area).pack(side="left")
        if clip is not None:
            w, h = clip.size
            ttk.Label(f, text="%s: a %d x %d area of %s" % ("Cut" if clip.cut else "Copied", w, h, clip.map),
                      style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(14, 0))
            ttk.Label(f, text="Click the map where its top-left corner goes (the outline shows it): here or on any "
                              "map. " + ("It moves there once." if clip.cut else "Click again for another copy."),
                      style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")
            ttk.Button(f, text="Stop pasting (Esc)", command=self.stop_pasting).pack(anchor="w", pady=(6, 0))

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
        self.head(f, "Map %s" % d.name, "Click a tile or a thing to see it here. Esc lets go of the palette's pick. "
                  "A pink badge on the map: a script, a quest or a data file points at it.")
        self.refs_list(f, self.refs.of_map(d.name), "the map")
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
        ttk.Label(f, text="1-6 layers · Shift+click fill · right-click a tile picks it · on Entities, right-click selects (again: a menu) · "
                          "click again or Tab: the next thing under it · "
                          "Shift+right-click menu · Delete removes · "
                          "arrows move (Shift ×8) · Ctrl+arrows next map · PgUp/PgDn levels · W Z G views · "
                          "the wheel zooms (where the mouse is: far out, the whole level) · Shift+wheel, middle-drag or "
                          "Space+drag moves the view (so do the arrows with nothing selected) · click any map to open it, "
                          "double-click a + to make one there",
                  style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")

    def insp_cell(self, f):
        x, y = self.sel_cell
        cell = self.doc.cells[y][x]
        self.head(f, "Tile %d,%d" % (x + 1, y + 1))
        self.refs_list(f, self.refs.of_tile(self.doc.name, x + 1, y + 1), "what's here")
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
        self.refs_list(f, self.uses_of(self.doc, e), "its Id, name or place" if e.opt("Id") else "it")
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
                "04\tDisplay.Message\tDarkRed\tYou can't read that from here!\tDenied",
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
        oid = e.opt("Id")
        row = ttk.Frame(f, style="Panel.TFrame")
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Id", style="Panel.TLabel", width=10).pack(side="left")
        if oid:                                         # (renamed, everything that uses it follows)
            ttk.Label(row, text=oid, style="Panel.TLabel", font=T.FONT_BOLD).pack(side="left")
            ttk.Button(row, text="Rename…", style="Small.TButton", command=lambda: self.rename_place(e)).pack(
                side="left", padx=6)
        else:
            v = tk.StringVar()
            ent = ttk.Entry(row, textvariable=v, width=16)
            ent.pack(side="left", fill="x", expand=True)
            give = lambda ev=None: v.get().strip() and self.set_opt(e, "Id", v.get().strip().replace(" ", "_"))
            ent.bind("<Return>", give)
            ent.bind("<FocusOut>", give)
        ttk.Label(f, text="Names this one (unique in the world): the game runs \"<Verb> <Id>\" before \"<Verb> %s\"."
                  % e.name, style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w")
        if not oid:
            return
        self.script_links(f, oid, self.verbs_of(e))

    def verbs_of(self, e):
        """What can be done to this thing (its left-click verb first, then its Use.Words, then Examine)."""
        words = [w.strip() for w in self.project.entities_ini.get(e.name, "Use.Words", "").split(",") if w.strip()]
        if e.kind == "NPC":
            words = ["Talk to", "Attack", "Kill"] + words
        elif e.kind == "MapItem":
            words = ["Pickup"] + words
        out = []
        for w in [self.default_verb(e)] + words + ["Examine"]:
            if w not in out:
                out.append(w)
        return out

    def script_links(self, f, oid, verbs):
        """Its own scripts, one click away: "Edit <Verb> <Id>" for each it has, "＋ <Verb> <Id>" to make the rest."""
        ttk.Label(f, text="Its own scripts", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(8, 0))
        have = self.project.scripts()
        mine = sorted(s for s in have if s.endswith(" " + oid))
        for s in mine:
            self.link(f, "Edit " + s, lambda s=s: self.app.goto("script", s))
        for verb in verbs:
            script = "%s %s" % (verb, oid)
            if script not in have:
                self.link(f, "＋ " + script, lambda s=script: (self.app.show(self.app.page_of("script")),
                                                              self.app.page_of("script").new_script(
                                                                  preset={"kind": "A trigger (any name)", "name": s})))

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
        """A named tile (an Id line) or a thing's Id=, renamed: asked for, then everything that uses it follows."""
        old = ent.name if ent.kind == "Id" else ent.opt("Id")
        new = self.ask_place_name(old, "Rename %s" % old, mine=ent)
        if new is not None:
            self.rename_everywhere(old, new, ent)

    def rename_everywhere(self, old, new, ent=None):
        """Place or Id old is new: on its map (ent, or found by its name on any map), in the quests' markers, in the
        scripts that name it, and in its own scripts' names ("Examine <old>" is "Examine <new>"). The map's saved
        with it (so the files all agree), unless it has other changes not saved yet. True if it was found."""
        if ent is None:
            pl = self.project.places().get(old.upper())
            doc = None
            for d in ([self.docs[pl[1]]] if pl and pl[1] in self.docs else []) + list(self.docs.values()) + \
                    ([self.get_doc(pl[1])] if pl else []):
                ent = next((e for e in d.placed() if (e.kind == "Id" and e.name == old) or
                            (e.kind not in TILE_KINDS and e.opt("Id") == old)), None)
                if ent is not None:
                    doc = d
                    break
            if ent is None:
                self.app.status("There's no place or thing called %s on any map." % old, "warn")
                return False
        else:
            doc = next((d for d in self.docs.values() if ent in d.entities), self.doc)
        clean = not self.dirty(doc.name)
        if doc is self.doc:
            self.remember()
        else:
            self.touch(doc)
        if ent.kind == "Id":
            ent.name = new
        else:
            ent.set_opt("Id", new)
        n = self.project.rename_place_uses(old, new)
        own = self.project.rename_own_scripts(old, new)
        if clean:
            self.save_doc(doc.name)
        qp = self.app.page_of("quest")                      # (its form shows the markers as they are now)
        if qp is not None and getattr(qp, "key", None) and not qp.is_dirty():
            qp.load(qp.key)
        self.redraw()
        self.show_inspector()
        self.app.status("Renamed %s to %s: on map %s%s, in %d script%s or quest%s that use%s it%s." % (
            old, new, doc.name, " (saved)" if clean else " (save it)", n, "" if n == 1 else "s", "" if n == 1 else "s",
            "s" if n == 1 else "", (", and its own scripts (%s)" % ", ".join(own)) if own else ""), "ok")
        return True

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
        cell = self.doc.cells[e.y - 1][e.x - 1] if 1 <= e.y <= len(self.doc.cells) else None
        on = (cell.decor or cell.tile) if cell is not None else ""       # (what's on the tile: its own verbs)
        words = [w.strip() for w in self.project.tiles_ini.get(on, "Use.Words", "").split(",") if w.strip()] if on else []
        ttk.Label(f, text="A click on this tile runs its own script first (\"<Verb> %s\"), before the %s's." % (
            e.name, on or "tile"), style="PanelMuted.TLabel", wraplength=T.px(300)).pack(anchor="w", pady=(6, 0))
        self.script_links(f, e.name, words + ["Examine"])
        uses = self.uses_of(self.doc, e)
        if uses:
            self.refs_list(f, uses, "its name")
        else:
            ttk.Label(f, text="Used by", style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w", pady=(10, 0))
            ttk.Label(f, text="nothing yet (saved files)", style="PanelMuted.TLabel").pack(anchor="w")
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
