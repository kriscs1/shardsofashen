"""Minimaps: sprites\\Interface\\Minimap<Z>.png, one per level, built from the maps and the tiles' minimap colours
(dev\\migrate\\build_minimaps.py does the building). The preview is also a world map: click a square to open it,
or an empty one (round the maps, or between them) to make a new map there."""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image

from .. import theme as T
from ..app import Page
from ..project import parse_map_name, Cell, read_text_lines
from ..widgets import photo
from ..world import own_level
from .iniform import IniFormPage


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
                        command=lambda: self.draw()).pack(anchor="w", pady=(10, 0))
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
        self.title_label = ttk.Label(right, text="", style="Head.TLabel")
        self.title_label.pack(anchor="w")
        ttk.Label(right, text="Click a map to open it in Maps; click an empty square (+) to make a new map there.",
                  style="PanelMuted.TLabel").pack(anchor="w")
        holder = ttk.Frame(right, style="Panel.TFrame")
        holder.pack(fill="both", expand=True, pady=6)
        self.canvas = tk.Canvas(holder, bg="#1d1712", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Motion>", self.hover)
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

    def draw_labels(self, c, gx, gy, s, mw, mh):
        """The world map's place names over the minimap, as the game's map sets them: towns largest, regions in gold
        capitals, the rest smaller (once a map's square is big enough); a dark edge so they read over any ground."""
        big = max(7, min(14, int(mw * s / 5)))
        styles = {"Towns": (("Segoe UI", big, "bold"), "#fff4dc", False),
                  "Regions": (("Segoe UI", max(7, big - 1), "bold"), "#f2c46d", True)}
        for name, section, m, tx, ty in self.labels():
            x, y, z = parse_map_name(m)
            if z != self.level or section not in styles and mw * s < 30:
                continue                                # (the small places only once there's room for them)
            font, fill, caps = styles.get(section, (("Segoe UI", max(7, big - 3)), "#e8dcc4", False))
            px, py = ((x - gx) * mw + tx - 0.5) * s, ((y - gy) * mh + ty - 0.5) * s
            text = name.upper() if caps else name
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                c.create_text(px + dx, py + dy, text=text, fill="#120d09", font=font, tags=("label",))
            c.create_text(px, py, text=text, fill=fill, font=font, tags=("label",))

    def picked(self):
        s = self.levels.selection()
        if s:
            self.level = int(s[0])
            self.draw()

    def show_unknown(self):
        if self.project._index is None:                 # (the first time, every map and script is read: a while)
            with self.app.busy("Finding the tiles every map uses…"):
                self.project.index()
        used = set(self.project.index()["tile"])
        missing = sorted(t for t in used if t not in self.project.minimap_colours)
        IniFormPage.fill_links(self.unknown, [(t, lambda t=t: self.app.goto("tile", t)) for t in missing], "none")

    # --- the preview: the minimap image, scaled to fit, with the map grid over it
    def draw(self):
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
        s = min(cw / (cols * mw), ch / (rows * mh))
        self.geom = (gx, gy, s, mw, mh)
        if img is not None:
            big = img.resize((max(1, int(img.size[0] * s * mw * nx / img.size[0])),
                              max(1, int(img.size[1] * s * mh * ny / img.size[1]))), Image.NEAREST)
            self._ph = photo(big)
            c.create_image((ox - gx) * mw * s, (oy - gy) * mh * s, image=self._ph, anchor="nw")
        for j in range(rows):                               # the empty squares - round the maps and between them,
            for i in range(cols):                           # over the picture: a new map can go in one
                if (gx + i, gy + j) in lv:
                    continue
                x0, y0 = i * mw * s, j * mh * s
                c.create_rectangle(x0 + 2, y0 + 2, x0 + mw * s - 2, y0 + mh * s - 2, fill="#1d1712", outline="#4a3d30",
                                   dash=(2, 4))
                c.create_text(x0 + mw * s / 2, y0 + mh * s / 2, text="+", fill="#6b5a46",
                              font=("Segoe UI", max(8, int(min(mw, mh) * s / 3))))
        for x, y in lv:
            x0, y0 = (x - gx) * mw * s, (y - gy) * mh * s
            c.create_rectangle(x0, y0, x0 + mw * s, y0 + mh * s, outline="#f2c46d", dash=(2, 3))
            if mw * s > 40:
                c.create_text(x0 + 4, y0 + 3, text="%d,%d" % (x, y), anchor="nw", fill="#fff4dc", font=T.FONT_SMALL)
        if self.names.get():
            self.draw_labels(c, gx, gy, s, mw, mh)

    def map_at(self, e):
        """The map name of the square under the mouse (one there or not), or None off the grid."""
        if not hasattr(self, "geom") or self.level is None or e.x < 0 or e.y < 0:
            return None
        gx, gy, s, mw, mh = self.geom
        x, y = int(e.x // (mw * s)) + gx, int(e.y // (mh * s)) + gy
        return "%d,%d,%d" % (x, y, self.level)

    def click(self, e):
        m = self.map_at(e)
        if m:
            self.app.goto("map", m)                         # (no map there yet: Maps asks to make it)

    def hover(self, e):
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
