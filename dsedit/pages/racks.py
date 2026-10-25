"""Item Racks: data\\ItemRacks.ini, the shops ([SHOP-...]) and crafting lists ([CRAFT-...])."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from ..app import Page
from ..widgets import FilterList, photo, ask_text, confirm, Tooltip

SETTINGS = ("Type", "Buy.Rate", "Sell.Rate", "Specific", "Skill")


def parse_row(kind, text):
    p = [x.strip() for x in text.split(",")]
    if kind == "Craft":
        ing = p[1].split() if len(p) > 1 else []
        return dict(item=p[0], ingredients=[(ing[i], ing[i + 1] if i + 1 < len(ing) else "1")
                                            for i in range(0, len(ing), 2)],
                    xp=p[2] if len(p) > 2 else "0", level=p[3] if len(p) > 3 else "", makes=p[4] if len(p) > 4 else "")
    return dict(item=p[0], stock=p[1] if len(p) > 1 else "+")


def row_text(kind, r):
    if kind == "Craft":
        out = [r["item"], " ".join("%s %s" % (n, q) for n, q in r["ingredients"]), r.get("xp") or "0"]
        if r.get("level") or r.get("makes"):
            out.append(r.get("level") or "0")
        if r.get("makes") and r.get("makes") != "1":
            out.append(r["makes"])
        return ",".join(out)
    return "%s,%s" % (r["item"], r.get("stock") or "+")


class RackPage(Page):
    title = "Item Racks"
    icon = "⚖"
    kind = "rack"

    def __init__(self, app):
        super().__init__(app)
        self.ini = self.project.racks_ini
        self.rack, self.rows, self.settings, self.other = None, [], {}, []
        self.loaded = None
        self.sel = None
        self._quiet = False
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Panel.TFrame", padding=10)
        pw.add(left, weight=0)
        self.list = FilterList(left, self.picked, kinds=["Shops", "Crafting"])
        self.list.pack(fill="both", expand=True)
        b = ttk.Frame(left, style="Panel.TFrame")
        b.pack(fill="x", pady=(6, 0))
        ttk.Button(b, text="＋ Shop", style="Small.TButton", command=lambda: self.new_rack("SHOP-")).pack(side="left")
        ttk.Button(b, text="＋ Crafting", style="Small.TButton", command=lambda: self.new_rack("CRAFT-")).pack(
            side="left", padx=3)
        ttk.Button(b, text="Rename", style="Small.TButton", command=self.rename_rack).pack(side="left")
        ttk.Button(b, text="Delete", style="Small.TButton", command=self.delete_rack).pack(side="left", padx=3)

        right = ttk.Frame(pw, style="Card.TFrame", padding=16)
        pw.add(right, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(side="left")
        self.kind_label = ttk.Label(head, text="", style="PanelMuted.TLabel")
        self.kind_label.pack(side="left", padx=10, pady=(6, 0))
        opened = ttk.Frame(right, style="Panel.TFrame")
        opened.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        ttk.Label(opened, text="Opened by", style="Panel.TLabel", font=T.FONT_BOLD).pack(side="left")
        self.opened_box = ttk.Frame(opened, style="Panel.TFrame")
        self.opened_box.pack(side="left", padx=8)

        st = ttk.Frame(right, style="Panel.TFrame")
        st.grid(row=2, column=0, sticky="ew")
        self.v = {k: tk.StringVar() for k in ("Buy.Rate", "Sell.Rate", "Skill")}
        self.specific = tk.BooleanVar()
        self.shop_widgets, self.craft_widgets = [], []
        ttk.Label(st, text="Player pays Value ×", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        w = ttk.Spinbox(st, textvariable=self.v["Buy.Rate"], from_=0, to=10, increment=0.05, width=6)
        w.grid(row=0, column=1, padx=(4, 16))
        self.shop_widgets.append(w)
        ttk.Label(st, text="and gets Value ×", style="Panel.TLabel").grid(row=0, column=2, sticky="w")
        w = ttk.Spinbox(st, textvariable=self.v["Sell.Rate"], from_=0, to=10, increment=0.05, width=6)
        w.grid(row=0, column=3, padx=(4, 16))
        self.shop_widgets.append(w)
        w = ttk.Checkbutton(st, text="Only buys what it sells", variable=self.specific)
        w.grid(row=0, column=4)
        self.shop_widgets.append(w)
        ttk.Label(st, text="Skill", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        w = ttk.Combobox(st, textvariable=self.v["Skill"], values=self.project.skills, width=14)
        w.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=(6, 0))
        self.craft_widgets.append(w)
        for var in list(self.v.values()) + [self.specific]:
            var.trace_add("write", lambda *a: self.settings_changed())

        mid = ttk.PanedWindow(right, orient="horizontal")
        mid.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        tbl = ttk.Frame(mid, style="Panel.TFrame")
        mid.add(tbl, weight=3)
        self.tree = ttk.Treeview(tbl, columns=("a", "b"), show="tree headings", style="Icons.Treeview", height=12)
        self.tree.heading("#0", text="Item")
        self.tree.heading("a", text="")
        self.tree.heading("b", text="")
        self.tree.column("#0", width=T.px(230))
        self.tree.column("a", width=T.px(260))
        self.tree.column("b", width=T.px(120))
        sb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.row_picked())
        self.tree.bind("<Double-1>", lambda e: self.open_item())
        rb = ttk.Frame(tbl, style="Panel.TFrame")
        rb.pack(side="bottom", fill="x")

        ed = ttk.LabelFrame(mid, text="Row", padding=10)
        mid.add(ed, weight=2)
        self.editor = ed
        bar = ttk.Frame(right, style="Panel.TFrame")
        bar.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        for text, cmd in (("＋ Add row", self.add_row), ("Remove", self.remove_row), ("▲", lambda: self.move(-1)),
                          ("▼", lambda: self.move(1)), ("Open item", self.open_item)):
            ttk.Button(bar, text=text, style="Small.TButton", command=cmd).pack(side="left", padx=(0, 4))
        self.price = ttk.Label(bar, text="", style="PanelMuted.TLabel")
        self.price.pack(side="right")
        self.build_editor()
        self.refresh_list()

    # --- the row editor
    def build_editor(self):
        ed = self.editor
        self.e_item, self.e_stock, self.e_unl = tk.StringVar(), tk.StringVar(), tk.BooleanVar()
        self.e_xp, self.e_level, self.e_makes = tk.StringVar(), tk.StringVar(), tk.StringVar()
        ttk.Label(ed, text="Item", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.item_box = ttk.Combobox(ed, textvariable=self.e_item, values=self.project.items(), width=24)
        self.item_box.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        self.shop_ed = ttk.Frame(ed, style="Panel.TFrame")
        self.shop_ed.grid(row=1, column=0, columnspan=4, sticky="ew")
        ttk.Label(self.shop_ed, text="In stock", style="Panel.TLabel").pack(side="left")
        self.stock_spin = ttk.Spinbox(self.shop_ed, textvariable=self.e_stock, from_=0, to=10000, width=7)
        self.stock_spin.pack(side="left", padx=6)
        ttk.Checkbutton(self.shop_ed, text="Never runs out", variable=self.e_unl).pack(side="left")
        self.craft_ed = ttk.Frame(ed, style="Panel.TFrame")
        self.craft_ed.grid(row=2, column=0, columnspan=4, sticky="nsew")
        c = self.craft_ed
        ttk.Label(c, text="Ingredients", style="Panel.TLabel", font=T.FONT_BOLD).grid(row=0, column=0, columnspan=4,
                                                                                      sticky="w", pady=(4, 0))
        self.ing = tk.Listbox(c, height=5, bg=T.FIELD, selectbackground=T.SELECT, relief="solid", bd=1)
        self.ing.grid(row=1, column=0, columnspan=4, sticky="ew")
        self.ing_item, self.ing_qty = tk.StringVar(), tk.StringVar(value="1")
        ttk.Combobox(c, textvariable=self.ing_item, values=self.project.items(), width=18).grid(row=2, column=0,
                                                                                               sticky="ew", pady=2)
        ttk.Spinbox(c, textvariable=self.ing_qty, from_=1, to=100, width=4).grid(row=2, column=1, padx=2)
        ttk.Button(c, text="Add", style="Small.TButton", command=self.add_ing).grid(row=2, column=2)
        ttk.Button(c, text="Remove", style="Small.TButton", command=self.remove_ing).grid(row=2, column=3, padx=2)
        for i, (lab, var, hint) in enumerate((("XP", self.e_xp, "Skill XP for making one."),
                                              ("Level", self.e_level, "Skill level needed (blank = none)."),
                                              ("Makes", self.e_makes, "How many one making gives (blank = 1)."))):
            ttk.Label(c, text=lab, style="Panel.TLabel").grid(row=3 + i, column=0, sticky="w", pady=2)
            w = ttk.Entry(c, textvariable=var, width=8)
            w.grid(row=3 + i, column=1, sticky="w")
            Tooltip(w, hint)
        for v in (self.e_item, self.e_stock, self.e_unl, self.e_xp, self.e_level, self.e_makes):
            v.trace_add("write", lambda *a: self.editor_changed())
        ed.columnconfigure(1, weight=1)

    def rack_kind(self):
        return "Craft" if (self.settings.get("Type", "").lower() == "craft" or
                           (self.rack or "").upper().startswith("CRAFT")) else "Shop"

    # --- loading
    def refresh_list(self):
        out = []
        for s in self.ini.sections():
            t = self.ini.get(s, "Type", "")
            k = "Crafting" if t.lower() == "craft" or s.upper().startswith("CRAFT") else "Shops"
            out.append((s, s, k))
        self.list.set_items(out)

    def picked(self, key):
        if key == self.rack:
            return
        if not self.leave_ok():
            self.list.select(self.rack, notify=False)
            return
        self.load(key)

    def open(self, key, **kw):
        if key != self.rack:
            if not self.leave_ok():
                return
            self.load(key)
        self.list.select(key, notify=False)

    def load(self, key):
        self.rack = key
        self.settings, self.rows, self.other = {}, [], []
        if key:
            items = self.ini.items(key)
            for k, v in items:
                if k in SETTINGS:
                    self.settings[k] = v
            kind = self.rack_kind()
            for k, v in items:
                if k.lower().startswith("item") and k[4:].isdigit():
                    self.rows.append(parse_row(kind, v))
                elif k not in SETTINGS:
                    self.other.append((k, v))
        self.loaded = self.serialize()
        self.sel = None
        self.clear_history()
        self.show()

    def show(self):
        self._quiet = True
        kind = self.rack_kind()
        self.name_label.configure(text=self.rack or "")
        self.kind_label.configure(text=("Shop" if kind == "Shop" else "Crafting") if self.rack else "")
        for k, v in self.v.items():
            v.set(self.settings.get(k, ""))
        self.specific.set(self.settings.get("Specific", "0") == "1")
        for w in self.shop_widgets:
            w.state(["!disabled"] if self.rack and kind == "Shop" else ["disabled"])
        for w in self.craft_widgets:
            w.state(["!disabled"] if self.rack and kind == "Craft" else ["disabled"])
        if kind == "Shop":
            self.craft_ed.grid_remove()
            self.shop_ed.grid()
            self.tree.heading("a", text="Stock")
            self.tree.heading("b", text="Buy / sell")
        else:
            self.shop_ed.grid_remove()
            self.craft_ed.grid()
            self.tree.heading("a", text="Ingredients")
            self.tree.heading("b", text="XP · level")
        self.draw_rows()
        self.load_editor()
        scripts = self.project.index()["rack"].get(self.rack, []) if self.rack else []
        from .iniform import IniFormPage
        IniFormPage.fill_links(self.opened_box, [(s, lambda s=s: self.app.goto("script", s)) for s in scripts],
                               "no script opens it")
        self._quiet = False
        self.app.refresh_chrome()

    def draw_rows(self):
        self.tree.delete(*self.tree.get_children())
        kind = self.rack_kind()
        buy, sell = self.rate("Buy.Rate", 1.2), self.rate("Sell.Rate", 0.8)
        for i, r in enumerate(self.rows):
            img = photo(self.project.sprite("Entities", r["item"]), (28, 28), key=("ent28", r["item"]))
            if kind == "Shop":
                val = self.value(r["item"])
                a = "never runs out" if r.get("stock", "+") == "+" else r.get("stock")
                b = "%d / %d gold" % (round(val * buy), round(val * sell)) if val else ""
            else:
                a = ", ".join("%s × %s" % (q, n.replace("_", " ")) for n, q in r["ingredients"])
                b = "%s xp" % r.get("xp", "0") + (" · lv %s" % r["level"] if r.get("level") not in ("", "0") else "") + \
                    (" · makes %s" % r["makes"] if r.get("makes") not in ("", "1") else "")
            self.tree.insert("", "end", iid=str(i), text="  " + r["item"].replace("_", " "), image=img or "",
                             values=(a, b))
        if self.sel is not None and self.sel < len(self.rows):
            self.tree.selection_set(str(self.sel))

    def rate(self, key, default):
        try:
            return float(self.settings.get(key) or default)
        except ValueError:
            return default

    def value(self, item):
        try:
            return float(self.project.entities_ini.get(item, "Value", "0") or 0)
        except ValueError:
            return 0

    # --- editing
    def row_picked(self):
        s = self.tree.selection()
        self.sel = int(s[0]) if s else None
        self.load_editor()

    def load_editor(self):
        self._quiet = True
        r = self.rows[self.sel] if self.sel is not None and self.sel < len(self.rows) else None
        self.e_item.set(r["item"] if r else "")
        self.e_stock.set("" if not r or r.get("stock") == "+" else r.get("stock", ""))
        self.e_unl.set(bool(r) and r.get("stock") == "+")
        self.e_xp.set(r.get("xp", "") if r else "")
        self.e_level.set(r.get("level", "") if r else "")
        self.e_makes.set(r.get("makes", "") if r else "")
        self.ing.delete(0, "end")
        for n, q in (r.get("ingredients", []) if r else []):
            self.ing.insert("end", "%s × %s" % (q, n))
        self._quiet = False
        if r and self.rack_kind() == "Shop":
            val = self.value(r["item"])
            self.price.configure(text="Value %g: the player pays %d, gets %d" % (
                val, round(val * self.rate("Buy.Rate", 1.2)), round(val * self.rate("Sell.Rate", 0.8))))
        else:
            self.price.configure(text="")

    def editor_changed(self):
        if self._quiet or self.sel is None or self.sel >= len(self.rows):
            return
        self.remember()
        r = self.rows[self.sel]
        r["item"] = self.e_item.get().strip()
        if self.rack_kind() == "Shop":
            r["stock"] = "+" if self.e_unl.get() else (self.e_stock.get().strip() or "0")
        else:
            r["xp"], r["level"], r["makes"] = self.e_xp.get().strip(), self.e_level.get().strip(), self.e_makes.get().strip()
        self.draw_rows()
        self.app.refresh_chrome()

    def add_ing(self):
        if self.sel is None:
            return
        n = self.ing_item.get().strip()
        if not n:
            return
        self.remember()
        self.rows[self.sel]["ingredients"].append((n, self.ing_qty.get().strip() or "1"))
        self.draw_rows()
        self.load_editor()

    def remove_ing(self):
        if self.sel is None or not self.ing.curselection():
            return
        self.remember()
        del self.rows[self.sel]["ingredients"][self.ing.curselection()[0]]
        self.draw_rows()
        self.load_editor()

    def add_row(self):
        if not self.rack:
            return
        self.remember()
        self.rows.append(dict(item="", stock="+") if self.rack_kind() == "Shop" else
                         dict(item="", ingredients=[], xp="0", level="", makes=""))
        self.sel = len(self.rows) - 1
        self.draw_rows()
        self.load_editor()
        self.item_box.focus_set()

    def remove_row(self):
        if self.sel is None:
            return
        self.remember()
        del self.rows[self.sel]
        self.sel = min(self.sel, len(self.rows) - 1) if self.rows else None
        self.draw_rows()
        self.load_editor()

    def move(self, d):
        i = self.sel
        if i is None or not 0 <= i + d < len(self.rows):
            return
        self.remember()
        self.rows[i], self.rows[i + d] = self.rows[i + d], self.rows[i]
        self.sel = i + d
        self.draw_rows()

    def open_item(self):
        if self.sel is not None and self.rows[self.sel]["item"]:
            self.app.goto("entity", self.rows[self.sel]["item"])

    def settings_changed(self):
        if self._quiet or not self.rack:
            return
        self.remember()
        for k, v in self.v.items():
            self.settings[k] = v.get().strip()
        self.settings["Specific"] = "1" if self.specific.get() else ""
        self.draw_rows()
        self.app.refresh_chrome()

    # --- the Page interface
    def serialize(self):
        if not self.rack:
            return None
        kind = self.rack_kind()
        items = [("Type", self.settings.get("Type") or kind)]
        keys = ("Buy.Rate", "Sell.Rate", "Specific") if kind == "Shop" else ("Skill",)
        items += [(k, self.settings[k]) for k in keys if self.settings.get(k)]
        items += list(self.other)
        items += [("Item%d" % (i + 1), row_text(kind, r)) for i, r in enumerate(self.rows)]
        return items

    def snapshot(self):
        if not self.rack:
            return None
        import copy
        return copy.deepcopy((self.settings, self.rows, self.sel))

    def restore(self, snap):
        import copy
        self.settings, self.rows, self.sel = copy.deepcopy(snap)
        self.show()

    def is_dirty(self):
        return bool(self.rack) and self.serialize() != self.loaded

    def current(self):
        return self.rack or ""

    def save(self):
        if not self.rack:
            return True
        for i, r in enumerate(self.rows):
            if not r["item"]:
                self.app.status("Row %d has no item." % (i + 1), "error")
                return False
            if self.rack_kind() == "Craft" and not r["ingredients"]:
                self.app.status("Row %d (%s) has no ingredients." % (i + 1, r["item"]), "error")
                return False
        if self.ini.changed_on_disk():
            self.ini.load()
        self.ini.set_items(self.rack, self.serialize())
        self.ini.save()
        self.loaded = self.serialize()
        self.project.refresh()
        self.app.status("Saved %s." % self.rack, "ok")
        self.app.refresh_chrome()
        return True

    def discard(self):
        self.load(self.rack)

    def on_show(self):
        if self.ini.changed_on_disk() and not self.is_dirty():
            self.ini.load()
            self.refresh_list()
            if self.rack:
                self.load(self.rack)

    def search_items(self):
        return [(s, s) for s in self.ini.sections()]

    def new_rack(self, prefix):
        if not self.leave_ok():
            return
        name = ask_text(self, "New", "Name (after %s):" % prefix)
        if not name:
            return
        sec = prefix + name.strip().replace(" ", "_")
        if self.ini.has_section(sec):
            self.open(sec)
            return
        self.ini.add_section(sec)
        if prefix == "SHOP-":
            self.ini.set_items(sec, [("Type", "Shop"), ("Buy.Rate", "1.2"), ("Sell.Rate", "0.8")])
        else:
            self.ini.set_items(sec, [("Type", "Craft"), ("Skill", self.project.skills[0] if self.project.skills else "")])
        self.ini.save()
        self.refresh_list()
        self.open(sec)

    def rename_rack(self):
        if not self.rack or not self.leave_ok():
            return
        name = ask_text(self, "Rename", "New name:", self.rack)
        if not name or name.strip() == self.rack:
            return
        self.ini.rename_section(self.rack, name.strip())
        self.ini.save()
        self.rack = None
        self.refresh_list()
        self.open(name.strip())
        self.app.status("Renamed. Scripts that open it by its old name still use the old name.", "warn")

    def delete_rack(self):
        if not self.rack or not confirm(self, "Delete", "Delete the rack %s?" % self.rack):
            return
        self.ini.remove_section(self.rack)
        self.ini.save()
        self.refresh_list()
        self.load(None)
