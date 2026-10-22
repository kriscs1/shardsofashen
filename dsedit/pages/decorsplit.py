"""Tiles ▸ "Split props off their floors…": the furniture, plants, rocks and trees drawn on a floor, each shown as it is,
its floor, the decor it splits into and that decor on another floor. Tick the ones to split; the maps are changed to
Floor+Decor(Name) and a copy of everything changed is kept (dsedit\\decor.py does the work)."""
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image

from .. import theme as T
from .. import decor as D
from ..render import forget_tiles
from ..widgets import Dialog, ScrollFrame, photo, forget_photos

SHOW = ["All", "Ticked", "Not ticked"]


def checker(w, h):
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (205, 205, 205, 255) if (x // 4 + y // 4) % 2 else (160, 160, 160, 255)
    return im


class DecorSplitDialog(Dialog):
    def __init__(self, parent, app):
        super().__init__(parent, "Split props off their floors", ok="Split the ticked ones")
        self.app, self.project = app, app.project
        self.result_report = None
        b = self.body
        ttk.Label(b, text="Furniture, plants, rocks and trees drawn on a floor become see-through decor, so the same "
                          "chair goes on any floor and the copies drawn on other floors (Chair101, Chair201…) aren't "
                          "needed. The maps keep looking exactly as they do: each cell becomes its floor with the "
                          "decor over it. A copy of everything changed goes in Dev\\Archive first.",
                  style="Panel.TLabel", wraplength=T.px(760)).pack(anchor="w")
        ttk.Label(b, text="Each row: the tile now  ·  its floor  ·  the decor (on a check)  ·  the decor on another "
                          "floor.", style="PanelMuted.TLabel").pack(anchor="w", pady=(6, 6))
        bar = ttk.Frame(b, style="Panel.TFrame")
        bar.pack(fill="x")
        ttk.Button(bar, text="Tick the good ones", style="Small.TButton", command=self.tick_good).pack(side="left")
        ttk.Button(bar, text="Untick all", style="Small.TButton", command=self.untick).pack(side="left", padx=4)
        ttk.Label(bar, text="Show", style="Panel.TLabel").pack(side="left", padx=(16, 4))
        self.show = tk.StringVar(value="All")
        cb = ttk.Combobox(bar, textvariable=self.show, values=SHOW, state="readonly", width=12)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill())
        self.count = ttk.Label(bar, text="", style="PanelMuted.TLabel")
        self.count.pack(side="right")
        self.list = ScrollFrame(b)
        self.list.pack(fill="both", expand=True, pady=(6, 0))
        self.wait = ttk.Label(self.list.body, text="Looking at the tiles…", style="Panel.TLabel")
        self.wait.pack(anchor="w", pady=20)
        self.geometry("%dx%d" % (T.px(900), T.px(760)))
        self.splits, self.rows, self.ticks = [], [], {}
        self.after(50, self.analyse)

    # --- finding them
    def analyse(self):
        if self.splits:
            return
        self.configure(cursor="watch")

        def progress(i, n, name):
            if i % 8 == 0:
                self.wait.configure(text="Looking at the tiles… %d of %d (%s)" % (i, n, name))
                self.update_idletasks()
        self.splits = D.analyse(self.project, progress)
        self.configure(cursor="")
        self.by_name = {s.name: s for s in self.splits}
        self.shown = [s for s in self.splits if s.canon == s.name]
        self.ticks = {s.name: tk.BooleanVar(value=s.good) for s in self.shown}
        for v in self.ticks.values():
            v.trace_add("write", lambda *a: self.update_count())
        self.wait.destroy()
        self.fill()

    def canon(self, name):
        s = self.by_name.get(name)
        return s.canon if s else None

    # --- the list
    def fill(self):
        for w in self.list.body.winfo_children():
            w.destroy()
        P = self.project
        tw, th = P.tile_w, P.tile_h
        size = (tw * 2, th * 2)
        check = checker(tw, th)
        want = self.show.get()
        for s in self.shown:
            ticked = self.ticks[s.name].get()
            if (want == "Ticked" and not ticked) or (want == "Not ticked" and ticked):
                continue
            row = ttk.Frame(self.list.body, style="Panel.TFrame", padding=(0, 4))
            row.pack(fill="x")
            c = ttk.Checkbutton(row, variable=self.ticks[s.name], command=lambda s=s: self.toggled(s))
            c.pack(side="left", padx=(0, 6))
            if s.blocked:
                c.state(["disabled"])
            decor = s.image()
            other = P.sprite("Tiles", D.alt_floor(s.floor))
            pics = [P.sprite("Tiles", s.name), P.sprite("Tiles", s.floor), Image.alpha_composite(check, decor),
                    Image.alpha_composite(other.convert("RGBA"), decor) if other is not None else None]
            for i, img in enumerate(pics):
                ph = photo(img, size, key=("decorsplit", s.name, i)) if img is not None else None
                tk.Label(row, image=ph or "", bg=T.PANEL, width=size[0], height=size[1]).pack(side="left", padx=2)
            text = ttk.Frame(row, style="Panel.TFrame")
            text.pack(side="left", fill="x", expand=True, padx=(10, 0))
            ttk.Label(text, text=s.name.replace("_", " "), style="Panel.TLabel", font=T.FONT_BOLD).pack(anchor="w")
            uses = s.uses + sum(self.by_name[m].uses for m in s.merged)
            ttk.Label(text, text="on %s  ·  %s on the maps" % (s.floor, "%d cells" % uses if uses else "not"),
                      style="PanelMuted.TLabel").pack(anchor="w")
            notes = []
            if s.merged:
                notes.append("the same picture as %s: they become this one" % ", ".join(s.merged))
            if s.linked:
                notes.append("goes with %s (a script changes one to the other)" % ", ".join(sorted(s.linked)))
            if s.blocked:
                notes.append("can't be split: " + s.blocked)
            elif not s.good:
                why = []
                if s.name.startswith(D.UNTICKED):
                    why.append("built into a wall, covering the floor, or with a glow that only partly comes away")
                if s.score < D.GOOD_FLOOR:
                    why.append("little of its floor shows, so the floor may be the wrong one")
                if s.holes > 12:
                    why.append("%d pixels of it matched the floor and were filled in" % s.holes)
                if s.error > 4:
                    why.append("not quite the same drawn back on its floor")
                notes.append("check it: " + "; ".join(why))
            if notes:
                ttk.Label(text, text="\n".join(notes), style="PanelMuted.TLabel",
                          wraplength=T.px(420)).pack(anchor="w")
        self.update_count()

    def toggled(self, s):
        """Things a script changes into each other are ticked together (a tree and its stump)."""
        on = self.ticks[s.name].get()
        todo, seen = [s.name], set()
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            x = self.by_name.get(n)
            if x is None:
                continue
            c = x.canon
            if c in self.ticks and self.ticks[c].get() != on and not self.by_name[c].blocked:
                self.ticks[c].set(on)
            todo += list(x.linked) + [c]

    def tick_good(self):
        for s in self.shown:
            self.ticks[s.name].set(s.good)
        self.fill()

    def untick(self):
        for v in self.ticks.values():
            v.set(False)
        self.fill()

    def update_count(self):
        n = sum(1 for v in self.ticks.values() if v.get())
        cells = sum(s.uses + sum(self.by_name[m].uses for m in s.merged) for s in self.shown
                    if self.ticks[s.name].get())
        self.count.configure(text="%d of %d ticked  ·  %d map cells change" % (n, len(self.shown), cells))

    # --- doing it
    def ok(self):
        chosen = [n for n, v in self.ticks.items() if v.get()]
        if not chosen:
            messagebox.showinfo("Split props", "Nothing is ticked.", parent=self)
            return False
        busy = [p for p in self.app.pages if p.kind in ("map", "tile") and p.is_dirty()]
        if busy:
            messagebox.showwarning("Split props", "Save or undo your changes in %s first: the split changes the maps "
                                   "and Tiles.ini." % " and ".join(p.title for p in busy), parent=self)
            return False
        merged = sum(len(self.by_name[n].merged) for n in chosen)
        if not messagebox.askyesno(
                "Split props", "Split %d tiles into decor%s?\n\nTheir sprites become see-through, Tiles.ini marks them "
                "Layer=Decor, and every map cell with one becomes its floor with the decor over it. A copy of "
                "everything changed goes in Dev\\Archive\\Decor split <date>." % (
                    len(chosen), (" (and merge %d copies drawn on other floors into them)" % merged) if merged else ""),
                parent=self):
            return False
        self.configure(cursor="watch")
        self.update_idletasks()
        backup, report = D.apply(self.project, self.splits, chosen)
        self.configure(cursor="")
        names = set(chosen) | {m for n in chosen for m in self.by_name[n].merged}
        for n in names:
            forget_photos(("tile", n))
            forget_photos(("tilebig", n))
        forget_tiles()
        return backup, report

    def destroy(self):
        forget_photos(("decorsplit",))
        super().destroy()
