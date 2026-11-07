"""Minimaps: sprites\\Interface\\Minimap<Z>.png, one per level, built from the maps and the tiles' minimap colours
(dev\\migrate\\build_minimaps.py does the building). The preview is also a world map: click a square to open it,
or an empty one (round the maps, or between them) to make a new map there."""
import math
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from PIL import Image

from .. import theme as T
from ..app import Page
from ..project import parse_map_name, Cell, read_text_lines
from ..widgets import photo
from ..world import own_level
from .iniform import IniFormPage

MOST_PX = 24            # zoomed in no further than this many screen pixels a tile


def overlaps(a, b, pad=2):
    """Two (x0, y0, x1, y1) boxes overlap (or come within pad pixels)."""
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


class MinimapPage(Page):
    title = "Minimaps"
    icon = "◩"
    kind = "minimap"

    def __init__(self, app):
        super().__init__(app)
        self.level = None
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Panel.TFrame", padding=12)
        pw.add(left, weight=0)
        ttk.Label(left, text="Levels", style="Head.TLabel").pack(anchor="w")
        self.levels = ttk.Treeview(left, columns=("maps",), show="tree headings", height=10, selectmode="extended")
        self.levels.heading("#0", text="Level")
        self.levels.heading("maps", text="Maps")
        self.levels.column("#0", width=T.px(150))
        self.levels.column("maps", width=T.px(60), anchor="e")
        self.levels.pack(fill="x", pady=4)
        self.levels.bind("<<TreeviewSelect>>", lambda e: self.picked())
        ttk.Label(left, text="Pixels per tile", style="Panel.TLabel").pack(anchor="w", pady=(10, 0))
        self.ps = tk.StringVar(value=self.project.config.get("Minimap", "Pixel.Size", "1"))
        ttk.Spinbox(left, textvariable=self.ps, from_=1, to=4, width=6).pack(anchor="w")
        ttk.Label(left, text="(shared by every level: changing it rebuilds them all)", style="PanelMuted.TLabel",
                  wraplength=220).pack(anchor="w")
        self.names = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Place names (WorldMap.ini)", variable=self.names,
                        command=lambda: self.queue_draw()).pack(anchor="w", pady=(10, 0))
        ttk.Button(left, text="Build the selected levels", style="Accent.TButton",
                   command=lambda: self.build(False)).pack(fill="x", pady=(12, 4))
        ttk.Button(left, text="Build every level", command=lambda: self.build(True)).pack(fill="x")
        ttk.Label(left, text="Tiles with no minimap colour", style="Head.TLabel").pack(anchor="w", pady=(18, 2))
        self.unknown = ttk.Frame(left, style="Panel.TFrame")
        self.unknown.pack(anchor="w", fill="x")
        ttk.Label(left, text="(they get the sprite's average colour; set one in Tiles)", style="PanelMuted.TLabel",
                  wraplength=220).pack(anchor="w")

        right = ttk.Frame(pw, style="Card.TFrame", padding=12)
        pw.add(right, weight=1)
        top = ttk.Frame(right, style="Card.TFrame")
        top.pack(fill="x")
        self.title_label = ttk.Label(top, text="", style="Head.TLabel")
        self.title_label.pack(side="left")
        ttk.Button(top, text="Fit", command=self.fit).pack(side="right")
        self.zoom_label = ttk.Label(top, text="", style="PanelMuted.TLabel")
        self.zoom_label.pack(side="right", padx=8)
        ttk.Label(right, text="Click a map to open it in Maps; click an empty square (+) to make a new map there. "
                              "The wheel zooms; drag (or middle-drag, Shift+wheel) moves the view.",
                  style="PanelMuted.TLabel").pack(anchor="w")
        holder = ttk.Frame(right, style="Panel.TFrame")
        holder.pack(fill="both", expand=True, pady=6)
        self.canvas = tk.Canvas(holder, bg="#1d1712", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.views = {}                                     # {frame key: (zoom, left, top)}: left, top in tiles
        self._drag = None
        self._queued = False
        self._fonts = {}
        c = self.canvas
        c.bind("<Configure>", lambda e: self.queue_draw())
        c.bind("<ButtonPress-1>", self.press)
        c.bind("<B1-Motion>", self.drag)
        c.bind("<ButtonRelease-1>", self.release)
        c.bind("<ButtonPress-2>", self.press)
        c.bind("<B2-Motion>", lambda e: self.drag(e, at_once=True))
        c.bind("<ButtonRelease-2>", lambda e: setattr(self, "_drag", None))
        c.bind("<MouseWheel>", self.wheel)
        c.bind("<Shift-MouseWheel>", lambda e: self.pan(-e.delta / 120 * 60, 0))
        c.bind("<Motion>", self.hover)
        self.log = tk.Text(right, height=6, bg=T.FIELD, relief="solid", bd=1, font=T.MONO)
        self.log.pack(fill="x")

    # --- levels
    def level_maps(self):
        out = {}
        for m in self.project.maps():
            x, y, z = parse_map_name(m)
            out.setdefault(z, []).append((x, y))
        return out

    def on_show(self):
        self.project.refresh("maps")
        lv = self.level_maps()
        sel = self.levels.selection()
        self._labels = None                             # (read again: a place may have moved)
        self.levels.delete(*self.levels.get_children())
        names = {0: "Ground", 1: "Upstairs"}
        for z in sorted(lv, reverse=True):
            label = names.get(z, "Underground %d" % -z if z < 0 else "Up %d" % z)
            self.levels.insert("", "end", iid=str(z), text="%s  (Z %d)" % (label, z), values=(len(lv[z]),))
        if sel and all(self.levels.exists(s) for s in sel):
            self.levels.selection_set(sel)
        elif self.levels.exists("0"):
            self.levels.selection_set("0")
        self.show_unknown()

    def labels(self):
        """[(name, section, map, tile x, tile y)]: the world map's labels (data\WorldMap.ini), each where its place
        Id or "map tx ty" puts it. Read once each time the page is shown (finding the Ids reads every map)."""
        if getattr(self, "_labels", None) is not None:
            return self._labels
        out, places, section = [], None, "Places"
        try:
            lines = read_text_lines(self.project.p("data", "WorldMap.ini"))
        except OSError:
            lines = []
        for l in lines:
            l = l.strip()
            if not l or l.startswith(";"):
                continue
            if l.startswith("[") and l.endswith("]"):
                section = l[1:-1]
                continue
            name, _, where = l.partition("=")
            where = where.split("[if")[0].strip()       # (shown to some players only: the editor shows it anyway)
            f = where.split()
            if len(f) == 3 and parse_map_name(f[0]):
                try:
                    out.append((name.strip(), section, f[0], int(f[1]), int(f[2])))
                except ValueError:
                    pass
                continue
            if places is None:
                with self.app.busy("Finding the world map's places…"):
                    places = self.project.places()
            hit = places.get(where.upper())
            if hit:
                out.append((name.strip(), section, hit[1], hit[2], hit[3]))
        self._labels = out
        return out

    def font(self, spec):
        f = self._fonts.get(spec)
        if f is None:
            f = self._fonts[spec] = tkfont.Font(font=spec)
        return f

    def place_labels(self, s, mw, mh, left, top, cw, ch):
        """[(text, font, fill, x, y, box)]: the world map's place names as the game's map sets them (towns largest,
        regions in gold capitals, the rest smaller once a map's square is big enough), laid out so none lies over
        another: towns first, then regions, then the rest; one that would overlap tries just above and below its spot,
        and is left out if those are taken too (zoom in and there's room for it)."""
        big = max(7, min(16, int(mw * s / 5)))
        styles = {"Towns": (("Segoe UI", big, "bold"), "#fff4dc", False),
                  "Regions": (("Segoe UI", max(7, big - 1), "bold"), "#f2c46d", True)}
        order = {"Towns": 0, "Regions": 1}
        out, boxes = [], []
        for name, section, m, tx, ty in sorted(self.labels(), key=lambda l: order.get(l[1], 2)):
            x, y, z = parse_map_name(m)
            if z != self.level or section not in styles and mw * s < 30:
                continue                                # (the small places only once there's room for them)
            spec, fill, caps = styles.get(section, (("Segoe UI", max(7, big - 3)), "#e8dcc4", False))
            px, py = (x * mw + tx - 0.5 - left) * s, (y * mh + ty - 0.5 - top) * s
            text = name.upper() if caps else name
            f = self.font(spec)
            w, h = f.measure(text) + 4, f.metrics("linespace")
            if px + w / 2 < 0 or px - w / 2 > cw or py + h < 0 or py - h > ch:
                continue                                # (out of the view)
            for dy in (0, -h, h):
                box = (px - w / 2, py + dy - h / 2, px + w / 2, py + dy + h / 2)
                if not any(overlaps(box, o) for o in boxes):
                    boxes.append(box)
                    out.append((text, spec, fill, px, py + dy, box))
                    break
        return out

    def picked(self):
        s = self.levels.selection()
        if s:
            self.level = int(s[0])
            self.queue_draw()

    def show_unknown(self):
        if self.project._index is None:                 # (the first time, every map and script is read: a while)
            with self.app.busy("Finding the tiles every map uses…"):
                self.project.index()
        used = set(self.project.index()["tile"])
        missing = sorted(t for t in used if t not in self.project.minimap_colours)
        IniFormPage.fill_links(self.unknown, [(t, lambda t=t: self.app.goto("tile", t)) for t in missing], "none")

    # --- the preview: the minimap image with the map grid over it, fitted to the view and zoomed from there (the wheel,
    # about the mouse), dragged about; only what's in view is drawn (the picture cropped to it, then scaled)
    def frame_key(self):
        return self.level if own_level(self.level) else "world"   # (the levels in the world's frame share one view)

    def queue_draw(self):
        if not self._queued:
            self._queued = True
            self.after_idle(self.draw)

    def draw(self):
        self._queued = False
        c = self.canvas
        c.delete("all")
        if self.level is None:
            return
        z = self.level
        self.title_label.configure(text="Minimap%d.png" % z)
        img = self.project.sprite("Interface", "Minimap%d" % z)
        lv = self.level_maps().get(z, [])
        if not lv:
            return
        try:
            ox, oy = (int(v) for v in self.project.config.get("Minimap", "Origin.%d" % z, "").split(","))
        except ValueError:
            ox, oy = min(x for x, _ in lv), min(y for _, y in lv)
        mw, mh = self.project.map_w, self.project.map_h
        nx = max(x for x, _ in lv) - ox + 1
        ny = max(y for _, y in lv) - oy + 1
        # (every level under or over the world in the world's frame: the same squares, the same size, wherever its own
        # maps are, so going from one to the next keeps every square where it was; a level of its own, its own frame)
        frame = lv if own_level(z) else [xy for zz, l in self.level_maps().items() if not own_level(zz) for xy in l]
        gx, gy = min([ox] + [x for x, _ in frame]) - 1, min([oy] + [y for _, y in frame]) - 1   # (a ring of empty
        cols, rows = max(x for x, _ in frame) - gx + 2, max(y for _, y in frame) - gy + 2       # squares all round)
        cw, ch = max(50, c.winfo_width()), max(50, c.winfo_height())
        fit = min(cw / (cols * mw), ch / (rows * mh))
        zoom, left, top = self.views.get(self.frame_key(), (1.0, None, None))
        zoom = max(1.0, min(zoom, MOST_PX / fit))
        s = fit * zoom
        vw, vh = cw / s, ch / s                             # (the view's size in tiles)
        W, H = cols * mw, rows * mh
        left = gx * mw - (vw - W) / 2 if vw >= W else max(gx * mw, min(gx * mw + W - vw, gx * mw if left is None else left))
        top = gy * mh - (vh - H) / 2 if vh >= H else max(gy * mh, min(gy * mh + H - vh, gy * mh if top is None else top))
        self.views[self.frame_key()] = (zoom, left, top)
        self.geom = (s, mw, mh, left, top, fit)
        self.zoom_label.configure(text="%d%%" % round(zoom * 100))
        X = lambda tx: (tx - left) * s                      # (a tile's edge, counted from the world's 0,0, on screen)
        Y = lambda ty: (ty - top) * s
        if img is not None:                                 # the part of the picture in view, scaled
            kx, ky = img.size[0] / (nx * mw), img.size[1] / (ny * mh)      # (the picture's pixels a tile)
            ix0 = max(0, min(img.size[0], math.floor((left - ox * mw) * kx)))
            ix1 = max(0, min(img.size[0], math.ceil((left + vw - ox * mw) * kx)))
            iy0 = max(0, min(img.size[1], math.floor((top - oy * mh) * ky)))
            iy1 = max(0, min(img.size[1], math.ceil((top + vh - oy * mh) * ky)))
            if ix1 > ix0 and iy1 > iy0:
                sx0, sx1 = round(X(ox * mw + ix0 / kx)), round(X(ox * mw + ix1 / kx))
                sy0, sy1 = round(Y(oy * mh + iy0 / ky)), round(Y(oy * mh + iy1 / ky))
                part = img.crop((ix0, iy0, ix1, iy1)).resize((max(1, sx1 - sx0), max(1, sy1 - sy0)), Image.NEAREST)
                self._ph = photo(part)
                c.create_image(sx0, sy0, image=self._ph, anchor="nw")
        labels = self.place_labels(s, mw, mh, left, top, cw, ch) if self.names.get() else []
        taken = [l[5] for l in labels]                      # (what's under a name isn't written: the name wins)
        have = set(lv)
        small = self.font(T.FONT_SMALL)
        plus = ("Segoe UI", max(8, min(40, int(min(mw, mh) * s / 3))))
        pw, ph = self.font(plus).measure("+"), self.font(plus).metrics("linespace")
        for my in range(max(gy, math.floor(top / mh)), min(gy + rows, math.floor((top + vh) / mh) + 1)):
            for mx in range(max(gx, math.floor(left / mw)), min(gx + cols, math.floor((left + vw) / mw) + 1)):
                x0, y0, x1, y1 = X(mx * mw), Y(my * mh), X((mx + 1) * mw), Y((my + 1) * mh)
                if (mx, my) not in have:                    # an empty square, round the maps or between them: a new
                    c.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill="#1d1712", outline="#4a3d30",
                                       dash=(2, 4))         # map can go in one
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    if not any(overlaps((cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2), b) for b in taken):
                        c.create_text(cx, cy, text="+", fill="#6b5a46", font=plus)
                    continue
                c.create_rectangle(x0, y0, x1, y1, outline="#f2c46d", dash=(2, 3))
                text = "%d,%d" % (mx, my)
                tw, th = small.measure(text), small.metrics("linespace")
                box = (x0 + 4, y0 + 3, x0 + 4 + tw, y0 + 3 + th)
                if tw + 8 <= x1 - x0 and th + 6 <= y1 - y0 and not any(overlaps(box, b) for b in taken):
                    c.create_text(x0 + 4, y0 + 3, text=text, anchor="nw", fill="#fff4dc", font=T.FONT_SMALL)
        for text, spec, fill, px, py, _ in labels:          # the names last, over everything (a dark edge so they
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):   # read over any ground)
                c.create_text(px + dx, py + dy, text=text, fill="#120d09", font=spec, tags=("label",))
            c.create_text(px, py, text=text, fill=fill, font=spec, tags=("label",))

    def fit(self):
        if self.level is not None:
            self.views.pop(self.frame_key(), None)
            self.queue_draw()

    def wheel(self, e):
        """The wheel zooms about the spot under the mouse: a notch a quarter in or out (a touchpad's small turns a
        little at a time)."""
        if not e.delta or not hasattr(self, "geom") or self.level is None:
            return
        c = self.canvas
        mx, my = e.x_root - c.winfo_rootx(), e.y_root - c.winfo_rooty()   # (the event's own x, y can be another
        s, mw, mh, left, top, fit = self.geom                              # window's on Windows)
        zoom = self.views.get(self.frame_key(), (1.0,))[0]
        new = max(1.0, min(MOST_PX / fit, zoom * 1.25 ** (max(-480, min(480, e.delta)) / 120)))
        tx, ty = left + mx / s, top + my / s                # (the tile under the mouse stays under it)
        s2 = fit * new
        self.views[self.frame_key()] = (new, tx - mx / s2, ty - my / s2)
        self.geom = (s2, mw, mh, tx - mx / s2, ty - my / s2, fit)
        self.queue_draw()

    def pan(self, dx, dy):
        """The view moved by dx, dy screen pixels (the world the other way)."""
        if not hasattr(self, "geom") or self.level is None:
            return
        s, mw, mh, left, top, fit = self.geom
        zoom = self.views.get(self.frame_key(), (1.0,))[0]
        self.views[self.frame_key()] = (zoom, left + dx / s, top + dy / s)
        self.geom = (s, mw, mh, left + dx / s, top + dy / s, fit)
        self.queue_draw()

    def press(self, e):
        self._drag = [e.x, e.y, False]                      # (where it began; moved far enough to be a drag yet?)

    def drag(self, e, at_once=False):
        d = self._drag
        if d is None:
            return
        if not d[2] and (at_once or abs(e.x - d[0]) + abs(e.y - d[1]) > 4):
            d[2] = True
            self.canvas.configure(cursor="fleur")
        if d[2]:
            self.pan(d[0] - e.x, d[1] - e.y)
            d[0], d[1] = e.x, e.y

    def release(self, e):
        d, self._drag = self._drag, None
        self.canvas.configure(cursor="hand2")
        if d is not None and not d[2]:
            self.click(e)                                   # (a click, not a drag)

    def map_at(self, e):
        """The map name of the square under the mouse (one there or not), or None off the grid."""
        if not hasattr(self, "geom") or self.level is None or e.x < 0 or e.y < 0:
            return None
        s, mw, mh, left, top, _ = self.geom
        x, y = math.floor((left + e.x / s) / mw), math.floor((top + e.y / s) / mh)
        return "%d,%d,%d" % (x, y, self.level)

    def click(self, e):
        m = self.map_at(e)
        if m:
            self.app.goto("map", m)                         # (no map there yet: Maps asks to make it)

    def hover(self, e):
        if self._drag is not None and self._drag[2]:
            return
        m = self.map_at(e)
        self.app.info("" if not m else m if m in self.project.maps() else "%s: no map yet - click to make it" % m)

    # --- building
    def build(self, every):
        levels = [] if every else [s for s in self.levels.selection()]
        if not every and not levels:
            self.app.status("Pick a level (or Build every level).", "warn")
            return
        try:
            ps = max(1, int(self.ps.get()))
        except ValueError:
            ps = 1
        if str(ps) != self.project.config.get("Minimap", "Pixel.Size", "1"):
            levels = []                     # a new pixel size: every level
        args = [sys.executable, "-I", self.project.p("dev", "migrate", "build_minimaps.py"), "--pixel-size", str(ps)]
        if levels:
            args += ["--levels", ",".join(levels)]
        self.log.delete("1.0", "end")
        self.log.insert("end", "Building...\n")
        self.app.status("Building the minimaps...")

        done = []                                           # (the build's result, when it's finished)

        def work():
            done.append(subprocess.run(args, cwd=self.project.root, capture_output=True, text=True))

        def check():                                        # (on the editor's own thread: Tk is only safe there)
            if done:
                self.built(done[0])
            else:
                self.after(250, check)
        threading.Thread(target=work, daemon=True).start()
        self.after(250, check)

    def built(self, r):
        self.log.delete("1.0", "end")
        self.log.insert("end", (r.stdout or "") + (r.stderr or ""))
        self.project.config.load()
        for k in list(self.project._sprites):
            if k[0] == "Interface" and k[1].startswith("Minimap"):
                del self.project._sprites[k]
        self.draw()
        self.app.status("Minimaps built." if r.returncode == 0 else "Building the minimaps failed (see the log).",
                        "ok" if r.returncode == 0 else "error")

    def search_items(self):
        return [(str(z), "Minimap level %d" % z) for z in sorted(self.level_maps())]

    def open(self, key, **kw):
        if self.levels.exists(str(key)):
            self.levels.selection_set(str(key))
