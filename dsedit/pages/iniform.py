"""The sections that edit one ini section at a time (Tiles, Entities, Spells, Quests): a filtered list on the left,
a form on the right. Fields are tk variables bound to ini keys; the form remembers what was loaded, so it knows
when there are unsaved changes, and every change can be undone."""
import time
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from ..app import Page
from ..widgets import FilterList, ScrollFrame, Tooltip, ask_text, confirm


class IniFormPage(Page):
    ini_attr = ""            # the Project's IniDoc
    kinds = None             # the list's kind filter
    list_icons = False
    allow_new = True
    new_label = "New"

    def __init__(self, app):
        super().__init__(app)
        self.ini = getattr(self.project, self.ini_attr)
        self.key = None
        self.vars = {}           # ini key -> tk var
        self.loaded = {}
        self._loading = False
        self._last_snap, self._last_field, self._last_time = None, None, 0
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Panel.TFrame", padding=10)
        self.left = left
        pw.add(left, weight=0)
        self.list = FilterList(left, self.picked, kinds=self.kinds, icon_fn=self.list_icon if self.list_icons else None)
        self.list.pack(fill="both", expand=True)
        btns = ttk.Frame(left, style="Panel.TFrame")
        btns.pack(fill="x", pady=(6, 0))
        if self.allow_new:
            ttk.Button(btns, text="＋ " + self.new_label, style="Small.TButton", command=self.new_item).pack(side="left")
            ttk.Button(btns, text="Rename", style="Small.TButton", command=self.rename_item).pack(side="left", padx=3)
            ttk.Button(btns, text="Delete", style="Small.TButton", command=self.delete_item).pack(side="left")
        nav = ttk.Frame(btns, style="Panel.TFrame")
        nav.pack(side="right")
        ttk.Button(nav, text="◀", width=3, style="Small.TButton", command=lambda: self.list.step(-1)).pack(side="left")
        ttk.Button(nav, text="▶", width=3, style="Small.TButton", command=lambda: self.list.step(1)).pack(side="left")
        right = ttk.Frame(pw, style="Card.TFrame")
        pw.add(right, weight=1)
        self.scroll = ScrollFrame(right)
        self.scroll.pack(fill="both", expand=True, padx=1, pady=1)
        self.form = self.scroll.body
        self.form.configure(padding=16)
        self.build_form(self.form)
        self.refresh_list()
        self.set_enabled(False)

    # --- to fill in
    def build_form(self, f):
        pass

    def list_items(self):
        return [(s, s, "") for s in self.ini.sections()]

    def list_icon(self, key):
        return None

    def after_load(self):
        """After a section is put in the form (enable/disable fields, previews...)."""

    def extra_save(self):
        """Anything saved besides the ini keys (return False to stop the save)."""
        return True

    def validate(self):
        """A problem with the form ("" = none)."""
        return ""

    # --- fields
    def var(self, key, kind="str", default=""):
        v = tk.BooleanVar() if kind == "bool" else tk.StringVar()
        v._ini_default = default
        v._ini_kind = kind
        self.vars[key] = v
        v.trace_add("write", lambda *a, k=key: self.changed(k))
        return v

    def value(self, key):
        v = self.vars[key]
        if v._ini_kind == "bool":
            return "1" if v.get() else "0"
        return v.get().strip()

    def form_values(self):
        return {k: self.value(k) for k in self.vars}

    def changed(self, key):
        if self._loading:
            return
        now = time.time()
        if not (key == self._last_field and now - self._last_time < 1.2):   # typing in one box = one undo step
            if self._last_snap is not None:
                self.undo_stack.append(self._last_snap)
                del self.undo_stack[:-100]
                self.redo_stack.clear()
        self._last_field, self._last_time = key, now
        self._last_snap = self.snapshot()
        self.on_change(key)
        self.app.refresh_chrome()

    def on_change(self, key):
        pass

    def snapshot(self):
        return dict(self.form_values()) if self.key else None

    def restore(self, snap):
        self._loading = True
        for k, v in snap.items():
            if k in self.vars:
                var = self.vars[k]
                if var._ini_kind == "bool":
                    var.set(v == "1")
                else:
                    var.set(v)
        self._loading = False
        self._last_snap, self._last_field = snap, None
        self.after_load()

    # --- the list and loading
    def refresh_list(self):
        self.list.set_items(self.list_items())

    def picked(self, key):
        if key == self.key:
            return
        if not self.leave_ok():
            self.list.select(self.key, notify=False)
            return
        self.load(key)

    def open(self, key, **kw):
        if key != self.key:
            if not self.leave_ok():
                return
            self.load(key)
        self.list.select(key, notify=False)

    def load(self, key):
        self.key = key
        self._loading = True
        for k, v in self.vars.items():
            raw = self.ini.get(key, k, "") if key else ""
            if v._ini_kind == "bool":
                v.set((raw or v._ini_default) in ("1", "true", "True"))
            else:
                v.set(raw)
        self._loading = False
        self.loaded = self.form_values()
        self.clear_history()
        self._last_snap, self._last_field = self.snapshot(), None
        self.set_enabled(bool(key))
        self.after_load()
        self.app.refresh_chrome()

    def set_enabled(self, on):
        def walk(w):
            for c in w.winfo_children():
                try:
                    if isinstance(c, (ttk.Entry, ttk.Combobox, ttk.Spinbox, ttk.Checkbutton, ttk.Button, ttk.Radiobutton)):
                        if isinstance(c, ttk.Combobox) and str(c.cget("state")) == "readonly" and on:
                            c.state(["!disabled"])
                        else:
                            c.state(["!disabled"] if on else ["disabled"])
                    elif isinstance(c, tk.Text):
                        c.configure(state="normal" if on else "disabled")
                except tk.TclError:
                    pass
                walk(c)
        walk(self.form)

    # --- the Page interface
    def is_dirty(self):
        return bool(self.key) and self.form_values() != self.loaded

    def current(self):
        return self.key or ""

    def save(self):
        if not self.key:
            return True
        problem = self.validate()
        if problem:
            self.app.status(problem, "error")
            return False
        if self.ini.changed_on_disk():
            snap = self.form_values()
            self.ini.load()
            self.restore(snap)
        for k, v in self.form_values().items():
            if self.vars[k]._ini_kind == "bool" and v == self.vars[k]._ini_default and \
                    self.ini.get(self.key, k, "") == "":
                continue                                    # (a default tick box needn't be written)
            self.ini.set(self.key, k, v)
        if not self.extra_save():
            return False
        self.ini.save()
        self.loaded = self.form_values()
        self.project.refresh("verbs", "attributes")
        self.app.status("Saved %s." % self.key, "ok")
        self.refresh_list()
        self.app.refresh_chrome()
        return True

    def discard(self):
        self.load(self.key)

    def on_show(self):
        if self.ini.changed_on_disk() and not self.is_dirty():
            self.ini.load()
            self.refresh_list()
            if self.key:
                self.load(self.key)

    def search_items(self):
        return [(k, t) for k, t, _ in self.list_items()]

    # --- new, rename, delete
    def new_item(self):
        if not self.leave_ok():
            return
        name = ask_text(self, self.new_label, "Name:")
        if not name:
            return
        name = name.strip()
        if self.ini.has_section(name):
            self.app.status("%s already exists." % name, "warn")
            self.open(name)
            return
        self.ini.add_section(name)
        self.init_new(name)
        self.ini.save()
        self.refresh_list()
        self.open(name)

    def init_new(self, name):
        pass

    def rename_item(self):
        if not self.key or not self.leave_ok():
            return
        name = ask_text(self, "Rename", "New name for %s:" % self.key, self.key)
        if not name or name.strip() == self.key:
            return
        name = name.strip()
        if self.ini.has_section(name):
            self.app.status("%s already exists." % name, "error")
            return
        self.ini.rename_section(self.key, name)
        self.ini.save()
        self.key = None
        self.refresh_list()
        self.open(name)
        self.app.status("Renamed to %s. (Anything that names it by its old name still does.)" % name, "warn")

    def delete_item(self):
        if not self.key:
            return
        if not confirm(self, "Delete", "Delete %s from %s?" % (self.key, self.ini.path.split("\\")[-1])):
            return
        self.ini.remove_section(self.key)
        self.ini.save()
        self.key = None
        self.refresh_list()
        self.load(None)

    # --- helpers for building forms
    def section_label(self, parent, row, text):
        ttk.Label(parent, text=text, style="Head.TLabel").grid(row=row, column=0, columnspan=4, sticky="w",
                                                               pady=(14, 4))
        ttk.Separator(parent).grid(row=row, column=0, columnspan=4, sticky="sew", pady=(0, 2))

    def row(self, parent, r, label, widget, hint=None, col=0, span=1):
        lab = ttk.Label(parent, text=label, style="Panel.TLabel")
        lab.grid(row=r, column=col, sticky="w", padx=(0 if col == 0 else 18, 10), pady=3)
        widget.grid(row=r, column=col + 1, columnspan=span, sticky="ew" if span > 1 else "w", pady=3)
        if hint:
            Tooltip(widget, hint)
            Tooltip(lab, hint)
        return widget

    def links(self, parent, r, label, entries):
        """A 'Used in' row: entries [(text, callback)], clickable."""
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=r, column=0, sticky="nw", padx=(0, 10), pady=3)
        box = ttk.Frame(parent, style="Panel.TFrame")
        box.grid(row=r, column=1, columnspan=3, sticky="ew", pady=3)
        return box

    @staticmethod
    def fill_links(box, entries, empty="nowhere yet"):
        for w in box.winfo_children():
            w.destroy()
        if not entries:
            ttk.Label(box, text=empty, style="PanelMuted.TLabel").pack(anchor="w")
            return
        line = ttk.Frame(box, style="Panel.TFrame")
        line.pack(anchor="w", fill="x")
        n = 0
        for text, cb in entries[:40]:
            if n and n % 6 == 0:
                line = ttk.Frame(box, style="Panel.TFrame")
                line.pack(anchor="w", fill="x")
            l = ttk.Label(line, text=text, style="Link.TLabel", cursor="hand2")
            l.pack(side="left", padx=(0, 10))
            l.bind("<Button-1>", lambda e, c=cb: c())
            n += 1
        if len(entries) > 40:
            ttk.Label(box, text="… and %d more" % (len(entries) - 40), style="PanelMuted.TLabel").pack(anchor="w")
