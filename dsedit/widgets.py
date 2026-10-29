"""Widgets every section shares: the filtered list, the sprite palette, form rows, the picker, the condition builder,
the verb picker, tooltips."""
import re
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from PIL import Image, ImageTk

from . import theme as T
from .project import SLOTS

_photos = {}


def photo(img, size=None, key=None, fit=True):
    """A Tk image of a PIL image (cached by key). size: (w, h) box to fit in (keeps pixels sharp)."""
    if img is None:
        return None
    k = (key, size) if key is not None else None
    if k is not None and k in _photos:
        return _photos[k]
    im = img
    if size:
        w, h = img.size
        s = min(size[0] / w, size[1] / h) if fit else 1
        s = max(1, int(s)) if s >= 1 else s
        im = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.NEAREST)
        if im.size != size:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(im, ((size[0] - im.size[0]) // 2, (size[1] - im.size[1]) // 2), im if im.mode == "RGBA" else None)
            im = canvas
    ph = ImageTk.PhotoImage(im)
    if k is not None:
        _photos[k] = ph
    return ph


def forget_photos(key_prefix):
    for k in [k for k in _photos if k[0] and k[0][:len(key_prefix)] == key_prefix]:
        del _photos[k]


class Tooltip:
    def __init__(self, widget, text_fn):
        self.widget, self.text_fn, self.tip = widget, text_fn, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _e=None):
        text = self.text_fn() if callable(self.text_fn) else self.text_fn
        if not text:
            return
        self.hide()
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry("+%d+%d" % (x, y))
        tk.Label(self.tip, text=text, bg="#fff8e6", fg=T.TEXT, relief="solid", bd=1, font=T.FONT_SMALL,
                 justify="left", wraplength=T.px(420), padx=6, pady=4).pack()

    def hide(self, _e=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class ScrollFrame(ttk.Frame):
    """A frame whose contents (self.body) scroll up and down."""

    def __init__(self, parent, style="Panel.TFrame"):
        super().__init__(parent, style=style)
        self.canvas = tk.Canvas(self, bg=T.PANEL, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas, style=style)
        self.win = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.body.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.body.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        if self.body.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units")


class FilterList(ttk.Frame):
    """A search box, an optional kind drop-down, and a list (with small sprites when icon_fn gives them).
    items: [(key, text, kind)]. on_select(key) when the selection changes."""

    def __init__(self, parent, on_select, kinds=None, icon_fn=None, height=20, placeholder="Filter"):
        super().__init__(parent, style="Panel.TFrame")
        self.on_select, self.icon_fn = on_select, icon_fn
        self.items, self.shown = [], []
        top = ttk.Frame(self, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 4))
        self.search = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.search)
        e.pack(side="left", fill="x", expand=True)
        e.insert(0, "")
        self.search.trace_add("write", lambda *a: self.refilter())
        Tooltip(e, placeholder)
        self.kind = tk.StringVar(value="All")
        if kinds:
            self.kind_box = ttk.Combobox(top, textvariable=self.kind, values=["All"] + list(kinds), state="readonly",
                                         width=16)
            self.kind_box.pack(side="left", padx=(4, 0))
            self.kind.trace_add("write", lambda *a: self.refilter())
        style = "Icons.Treeview" if icon_fn else "Treeview"
        frame = ttk.Frame(self, style="Panel.TFrame")
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, show="tree", selectmode="browse", height=height, style=style)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._picked)
        self.count = ttk.Label(self, style="PanelMuted.TLabel")
        self.count.pack(anchor="w")
        self._quiet = False
        self.search_entry = e

    def set_items(self, items, keep=True):
        sel = self.selected() if keep else None
        self.items = items
        self.refilter()
        if sel:
            self.select(sel, notify=False)

    def refilter(self):
        q = self.search.get().strip().lower()
        k = self.kind.get()
        self._quiet = True
        self.tree.delete(*self.tree.get_children())
        self.shown = []
        for key, text, kind in self.items:
            if q and q not in text.lower() and q not in str(key).lower():
                continue
            if k not in ("", "All") and kind != k:
                continue
            self.shown.append(key)
            img = self.icon_fn(key) if self.icon_fn else None
            self.tree.insert("", "end", iid=str(key), text="  " + text, image=img or "")
        self.count.configure(text="%d of %d" % (len(self.shown), len(self.items)))
        self._quiet = False

    def _picked(self, _e=None):
        if self._quiet:
            return
        s = self.tree.selection()
        if s:
            self.on_select(s[0])

    def selected(self):
        s = self.tree.selection()
        return s[0] if s else None

    def select(self, key, notify=True):
        key = str(key)
        if not self.tree.exists(key):
            self.search.set("")
            self.kind.set("All")
        if self.tree.exists(key):
            self._quiet = not notify
            self.tree.selection_set(key)
            self.tree.see(key)
            self._quiet = False

    def step(self, d):
        if not self.shown:
            return
        cur = self.selected()
        i = self.shown.index(cur) if cur in self.shown else -1
        i = max(0, min(len(self.shown) - 1, i + d))
        self.select(self.shown[i])


class PaletteGrid(tk.Frame):
    """A grid of sprite thumbnails to pick from (the map's palette). items: [(key, PIL image or None, label)]."""

    def __init__(self, parent, on_pick, on_hover=None, cell=40, preview_fn=None):
        super().__init__(parent, bg=T.PANEL)
        self.on_pick, self.on_hover, self.cell = on_pick, on_hover, cell
        self.preview_fn = preview_fn          # key -> (PIL image, caption): shown big beside the palette on hover
        self._pv, self._pv_key, self._pv_photo = None, None, None
        self.canvas = tk.Canvas(self, bg=T.FIELD, highlightthickness=1, highlightbackground=T.LINE, bd=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.items, self.selected, self.photos = [], None, []
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Button-3>", lambda e: self.pick(None))
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda e: self._preview(None))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120) * 2, "units"))

    def set_items(self, items):
        self.items = items
        if self.selected not in [k for k, _, _ in items]:
            self.selected = None
        self.draw()

    def cols(self):
        return max(1, (self.canvas.winfo_width() - 4) // self.cell)

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.photos = []
        cols, s = self.cols(), self.cell
        for i, (key, img, label) in enumerate(self.items):
            x, y = 2 + (i % cols) * s, 2 + (i // cols) * s
            if key == self.selected:
                c.create_rectangle(x, y, x + s - 1, y + s - 1, fill=T.SELECT, outline=T.ACCENT, width=2)
            ph = photo(img, (s - 8, s - 8), key=("pal", key, s)) if img is not None else None
            if ph:
                self.photos.append(ph)
                c.create_image(x + s // 2, y + s // 2, image=ph)
            else:
                c.create_rectangle(x + 3, y + 3, x + s - 4, y + s - 4, fill="#efe2cc", outline=T.LINE)
                if "\n" in label:                     # a symbol over a short name (the map's Trigger and Lock)
                    sym, name = label.split("\n", 1)
                    c.create_text(x + s // 2, y + s * 0.4, text=sym, font=("Segoe UI Symbol", -max(10, s * 2 // 5)),
                                  fill=T.ACCENT_DARK)
                    c.create_text(x + s // 2, y + s * 0.78, text=name, font=("Segoe UI", -max(8, s // 5)), fill=T.TEXT)
                else:
                    c.create_text(x + s // 2, y + s // 2, text=label, font=("Segoe UI", -max(8, s // 5)), fill=T.MUTED,
                                  width=s - 6, justify="center")
        rows = (len(self.items) + cols - 1) // cols
        c.configure(scrollregion=(0, 0, cols * s + 4, rows * s + 4))

    def _at(self, e):
        x, y = self.canvas.canvasx(e.x) - 2, self.canvas.canvasy(e.y) - 2
        cols, s = self.cols(), self.cell
        if x < 0 or y < 0 or x >= cols * s:
            return None
        i = int(y // s) * cols + int(x // s)
        return self.items[i][0] if 0 <= i < len(self.items) else None

    def _click(self, e):
        k = self._at(e)
        if k is not None:
            self.pick(k)

    def pick(self, key):
        self._preview(None)
        self.selected = key
        self.draw()
        if key is not None:
            self.see(key)
        self.on_pick(key)

    def see(self, key):
        """Scrolls so key's cell is in the middle of the palette (picked from the map, it may be far down)."""
        keys = [k for k, _, _ in self.items]
        if key not in keys:
            return
        self.canvas.update_idletasks()
        cols, s = self.cols(), self.cell
        rows = (len(self.items) + cols - 1) // cols
        total, view = rows * s + 4, max(1, self.canvas.winfo_height())
        if total <= view:
            return
        y = 2 + (keys.index(key) // cols) * s
        top, bottom = (f * total for f in self.canvas.yview())
        if top <= y and y + s <= bottom:                              # (in sight already: clicked, it stays put)
            return
        self.canvas.yview_moveto(max(0.0, min(1.0, (y + s / 2 - view / 2) / total)))

    def _motion(self, e):
        k = self._at(e)
        if self.on_hover:
            self.on_hover(k)
        self._preview(k, e)

    def _preview(self, key, e=None):
        """A big picture of the sprite under the mouse (and, for a piece of a set, the set with it marked), in a
        little window just right of the palette."""
        if key is None or self.preview_fn is None:
            if self._pv is not None:
                self._pv.destroy()
            self._pv, self._pv_key = None, None
            return
        if key != self._pv_key:
            got = self.preview_fn(key)
            if not got:
                self._preview(None)
                return
            img, caption = got
            if self._pv is None:
                self._pv = tk.Toplevel(self)
                self._pv.wm_overrideredirect(True)
                self._pv.attributes("-topmost", True)
                fr = tk.Frame(self._pv, bg=T.ACCENT_DARK, padx=1, pady=1)
                fr.pack()
                inner = tk.Frame(fr, bg=T.PANEL, padx=8, pady=6)
                inner.pack()
                self._pv_img = tk.Label(inner, bg="#1a1511")
                self._pv_img.pack()
                self._pv_text = tk.Label(inner, bg=T.PANEL, fg=T.TEXT, font=T.FONT_SMALL, justify="left",
                                         wraplength=T.px(260))
                self._pv_text.pack(anchor="w", pady=(4, 0))
            self._pv_photo = photo(img)
            self._pv_img.configure(image=self._pv_photo)
            self._pv_text.configure(text=caption)
            self._pv_key = key
        x = self.winfo_rootx() + self.winfo_width() + 10
        y = (e.y_root - T.px(40)) if e is not None else self.winfo_rooty()
        self._pv.geometry("+%d+%d" % (x, max(0, y)))


class Segmented(tk.Frame):
    """A row of buttons where one is chosen (like tabs): the chosen one is amber with white text, the rest tan with
    a border. options: [(value, text)] or [(value, text, tooltip)] or [(value, text, tooltip, icon)] (icon: a tool's
    name in icons.py, drawn left of the text in the text's colour). var: a StringVar; command() after a click.
    colours: {value: colour} for buttons in a colour of their own (white text; chosen, bold with a dark edge)."""

    def __init__(self, parent, var, options, command=None, columns=0, bg=None, colours=None):
        super().__init__(parent, bg=bg or T.PANEL)
        self.var, self.command, self.buttons, self.colours = var, command, {}, colours or {}
        for i, opt in enumerate(options):
            value, text = opt[0], opt[1]
            edge = tk.Frame(self, bg=T.BUTTON_EDGE)              # (a 1px border round each button)
            b = tk.Label(edge, text=text, font=T.FONT, padx=T.px(9), pady=T.px(3), cursor="hand2", bd=0)
            b.pack(fill="both", expand=True, padx=1, pady=1)
            b.edge = edge
            b.icon = opt[3] if len(opt) > 3 else None
            if columns:
                edge.grid(row=i // columns, column=i % columns, sticky="ew", padx=(0, 3), pady=(0, 3))
            else:
                edge.pack(side="left", padx=(0, 3))
            b.bind("<Button-1>", lambda e, v=value: self.choose(v))
            b.bind("<Enter>", lambda e, v=value: self.paint(hot=v))
            b.bind("<Leave>", lambda e: self.paint())
            if len(opt) > 2 and opt[2]:
                Tooltip(b, opt[2])
            self.buttons[value] = b
        if columns:
            for c in range(columns):
                self.columnconfigure(c, weight=1, uniform="seg")
        self._trace = var.trace_add("write", lambda *a: self.paint())
        self.bind("<Destroy>", lambda e: self._untrace() if e.widget is self else None)
        self.paint()

    def _untrace(self):
        try:
            self.var.trace_remove("write", self._trace)
        except tk.TclError:
            pass

    def choose(self, value):
        self.var.set(value)
        if self.command:
            self.command()

    def paint(self, hot=None):
        cur = self.var.get()
        for v, b in self.buttons.items():
            if not b.winfo_exists():
                continue
            own = self.colours.get(v)
            if own:
                b.configure(bg=own, fg="white", font=T.FONT_BOLD if v == cur else T.FONT)
                b.edge.configure(bg="#10131c" if v == cur else T.ACCENT if v == hot else own)
            elif v == cur:
                b.configure(bg=T.ACCENT, fg="white", font=T.FONT_BOLD)
                b.edge.configure(bg=T.ACCENT_DARK)
            else:
                b.configure(bg=T.SELECT if v == hot else T.BUTTON, fg=T.TEXT, font=T.FONT)
                b.edge.configure(bg=T.ACCENT if v == hot else T.BUTTON_EDGE)
            if b.icon:
                from .icons import icon
                b.configure(image=icon(b.icon, "#ffffff" if v == cur else T.TEXT), compound="left")


def labelled(parent, row, label, widget, hint=None, col=0, span=1):
    """A form row: a label, the widget (sticky across), and an optional muted hint under it."""
    ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=col, sticky="nw", padx=(0, 8), pady=3)
    widget.grid(row=row, column=col + 1, columnspan=span, sticky="ew", pady=3)
    if hint:
        Tooltip(widget, hint)
    return widget


class Dialog(tk.Toplevel):
    """A modal dialog: build the body in self.body, call self.run() to wait; self.result is what OK gave."""

    def __init__(self, parent, title, ok="OK"):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=T.PANEL)
        self.transient(parent.winfo_toplevel())
        self.result = None
        self.body = ttk.Frame(self, style="Panel.TFrame", padding=12)
        self.body.pack(fill="both", expand=True)
        bar = ttk.Frame(self, style="Panel.TFrame", padding=(12, 0, 12, 12))
        bar.pack(fill="x")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.ok_button = ttk.Button(bar, text=ok, style="Accent.TButton", command=self._ok)
        self.ok_button.pack(side="right", padx=(0, 6))
        self.bar = bar
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        r = self.ok()
        if r is not False:
            self.result = r
            self.destroy()

    def ok(self):
        return True

    def run(self):
        self.update_idletasks()
        p = self.master.winfo_toplevel()
        x = p.winfo_rootx() + (p.winfo_width() - self.winfo_reqwidth()) // 2
        y = p.winfo_rooty() + (p.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry("+%d+%d" % (max(0, x), max(0, y)))
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.result


class PickerDialog(Dialog):
    """Pick one of many (with a filter, kinds and sprites)."""

    def __init__(self, parent, title, items, kinds=None, icon_fn=None, current=None):
        super().__init__(parent, title, ok="Choose")
        self.list = FilterList(self.body, lambda k: None, kinds=kinds, icon_fn=icon_fn, height=16)
        self.list.pack(fill="both", expand=True)
        self.list.set_items(items)
        if current:
            self.list.select(current, notify=False)
        self.list.tree.bind("<Double-1>", lambda e: self._ok())
        self.list.tree.bind("<Return>", lambda e: self._ok())
        self.list.search_entry.bind("<Return>", lambda e: self._ok() if len(self.list.shown) == 1 or self.list.selected()
                                    else None)
        self.after(50, self.list.search_entry.focus_set)
        self.geometry("%dx%d" % (T.px(440), T.px(540)))

    def ok(self):
        k = self.list.selected()
        if k is None and len(self.list.shown) == 1:
            k = self.list.shown[0]
        return k if k is not None else False


def ask_text(parent, title, prompt, initial=""):
    return simpledialog.askstring(title, prompt, initialvalue=initial, parent=parent)


def confirm(parent, title, text):
    return messagebox.askyesno(title, text, parent=parent)


def ask_save(parent, what):
    """Yes = save, No = drop the changes, Cancel = stay. Returns "save", "drop" or None."""
    r = messagebox.askyesnocancel("Unsaved changes", "Save your changes to %s?" % what, parent=parent)
    return None if r is None else ("save" if r else "drop")


# =================================================================================================================
# Conditions: $Attr.X>=1 and $Item.Key>=1 ... (Lock lines and the script's >Conditional)
# =================================================================================================================
COND_KINDS = [("Quest/Attribute", "$Attr."), ("Item held", "$Item."), ("Skill level", "$Skill."),
              ("Equipped in slot", "$Equipped."), ("Other (typed)", "")]
OPS = ["=", "<>", "<", ">", "<=", ">="]


def parse_condition(text):
    """'a>=1 and b=2' -> [(join, lhs, op, rhs)] (join '' for the first), or None if it isn't plain clauses."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"\s+(and|or)\s+", text, flags=re.I)
    out, join = [], ""
    for i, p in enumerate(parts):
        if i % 2:
            join = p.lower()
            continue
        m = re.fullmatch(r"\s*(.+?)\s*(<>|<=|>=|=|<|>)\s*(.*?)\s*", p)
        if not m:
            return None
        out.append((join, m.group(1), m.group(2), m.group(3)))
    return out


class ConditionBuilder(Dialog):
    """Clauses joined by and / or: each a kind (quest attribute, item held, skill, equipped), a name, a test and a
    value. The text can be typed into too."""

    def __init__(self, parent, project, text, title="Condition", allow_empty=None):
        super().__init__(parent, title)
        self.project = project
        self.allow_empty = allow_empty
        b = self.body
        ttk.Label(b, text="Clauses", style="Head.TLabel").grid(row=0, column=0, sticky="w", columnspan=5)
        self.rows = []
        self.grid_frame = ttk.Frame(b, style="Panel.TFrame")
        self.grid_frame.grid(row=1, column=0, columnspan=5, sticky="ew", pady=4)
        bar = ttk.Frame(b, style="Panel.TFrame")
        bar.grid(row=2, column=0, columnspan=5, sticky="w")
        ttk.Button(bar, text="+ Add clause", style="Small.TButton", command=lambda: self.add_row()).pack(side="left")
        self.always = tk.BooleanVar()
        if allow_empty:
            ttk.Checkbutton(b, text=allow_empty, variable=self.always, command=self.sync_text).grid(
                row=3, column=0, columnspan=5, sticky="w", pady=(6, 0))
        ttk.Label(b, text="As text", style="Head.TLabel").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.text = tk.StringVar(value=text)
        e = ttk.Entry(b, textvariable=self.text, width=70, font=T.MONO)
        e.grid(row=5, column=0, columnspan=4, sticky="ew")
        ttk.Button(b, text="Text → clauses", style="Small.TButton", command=self.from_text).grid(row=5, column=4, padx=4)
        self.note = ttk.Label(b, text="", style="PanelMuted.TLabel")
        self.note.grid(row=6, column=0, columnspan=5, sticky="w")
        b.columnconfigure(3, weight=1)
        if text.strip() == "" and allow_empty:
            self.always.set(True)
        if not self.from_text(quiet=True):
            self.note.configure(text="This condition is more than plain clauses: edit it as text.")
        if not self.rows:
            self.add_row()

    def names_for(self, prefix):
        if prefix == "$Attr.":
            return self.project.attributes()
        if prefix == "$Item.":
            return self.project.items()
        if prefix == "$Skill.":
            return self.project.skills
        if prefix == "$Equipped.":
            return SLOTS
        return []

    def add_row(self, join="and", kind="Quest/Attribute", name="", op=">=", value="1"):
        f = self.grid_frame
        r = len(self.rows)
        v = dict(join=tk.StringVar(value=join), kind=tk.StringVar(value=kind), name=tk.StringVar(value=name),
                 op=tk.StringVar(value=op), value=tk.StringVar(value=value))
        widgets = []
        j = ttk.Combobox(f, textvariable=v["join"], values=["and", "or"], width=4, state="readonly")
        if r:
            j.grid(row=r, column=0, padx=2, pady=2)
        widgets.append(j)
        k = ttk.Combobox(f, textvariable=v["kind"], values=[n for n, _ in COND_KINDS], width=16, state="readonly")
        k.grid(row=r, column=1, padx=2)
        n = ttk.Combobox(f, textvariable=v["name"], width=24)
        n.grid(row=r, column=2, padx=2)
        o = ttk.Combobox(f, textvariable=v["op"], values=OPS, width=4, state="readonly")
        o.grid(row=r, column=3, padx=2)
        val = ttk.Combobox(f, textvariable=v["value"], width=16)
        val.grid(row=r, column=4, padx=2)
        x = ttk.Button(f, text="✕", width=3, style="Small.TButton", command=lambda: self.remove_row(v))
        x.grid(row=r, column=5)
        widgets += [k, n, o, val, x]
        v["widgets"] = widgets

        def kind_changed(*_a):
            prefix = dict(COND_KINDS)[v["kind"].get()]
            n.configure(values=self.names_for(prefix))
            val.configure(values=["none"] + self.project.items() if prefix == "$Equipped." else
                          ["0", "1", "2", "3", "5", "10", "20"])
            self.sync_text()
        v["kind"].trace_add("write", kind_changed)
        for key in ("join", "name", "op", "value"):
            v[key].trace_add("write", lambda *_a: self.sync_text())
        self.rows.append(v)
        kind_changed()

    def remove_row(self, v):
        for w in v["widgets"]:
            w.destroy()
        self.rows.remove(v)
        rebuilt = [(r["join"].get(), r["kind"].get(), r["name"].get(), r["op"].get(), r["value"].get()) for r in self.rows]
        for r in self.rows:
            for w in r["widgets"]:
                w.destroy()
        self.rows = []
        self._building = True
        for args in rebuilt:
            self.add_row(*args)
        self._building = False
        self.sync_text()

    def clause_text(self, r):
        prefix = dict(COND_KINDS)[r["kind"].get()]
        name = r["name"].get().strip()
        if not name:
            return ""
        return "%s%s%s%s" % (prefix, name, r["op"].get(), r["value"].get().strip())

    def sync_text(self):
        if getattr(self, "_building", False) or getattr(self, "_reading", False):
            return
        if self.always.get():
            self.text.set("")
            return
        out = ""
        for i, r in enumerate(self.rows):
            c = self.clause_text(r)
            if not c:
                continue
            out += (" %s " % r["join"].get() if out else "") + c
        self.text.set(out)

    def from_text(self, quiet=False):
        clauses = parse_condition(self.text.get())
        if clauses is None:
            if not quiet:
                self.note.configure(text="That isn't plain clauses (a=b and c<d ...): keep it as text.")
            return False
        self._reading = True
        for r in list(self.rows):
            for w in r["widgets"]:
                w.destroy()
        self.rows = []
        for join, lhs, op, rhs in clauses:
            kind, name = "Other (typed)", lhs
            for label, prefix in COND_KINDS:
                if prefix and lhs.startswith(prefix):
                    kind, name = label, lhs[len(prefix):]
            self.add_row(join or "and", kind, name, op, rhs)
        self._reading = False
        if not quiet:
            self.note.configure(text="")
        return True

    def ok(self):
        return self.text.get().strip()


class VerbPicker(Dialog):
    """Use.Words: tick the verbs (in order: the first is the left-click action)."""

    def __init__(self, parent, project, current):
        super().__init__(parent, "Use words")
        self.chosen = [w.strip() for w in current.split(",") if w.strip()]
        b = self.body
        ttk.Label(b, text="Chosen (the first is the left-click action)", style="Head.TLabel").grid(row=0, column=0,
                                                                                                    sticky="w")
        ttk.Label(b, text="Verbs the game knows", style="Head.TLabel").grid(row=0, column=2, sticky="w")
        self.lb = tk.Listbox(b, height=12, width=22, bg=T.FIELD, selectbackground=T.SELECT, relief="solid", bd=1)
        self.lb.grid(row=1, column=0, sticky="nsew")
        mid = ttk.Frame(b, style="Panel.TFrame")
        mid.grid(row=1, column=1, padx=6)
        ttk.Button(mid, text="◀ Add", command=self.add).pack(fill="x", pady=2)
        ttk.Button(mid, text="Remove ▶", command=self.remove).pack(fill="x", pady=2)
        ttk.Button(mid, text="▲ Up", command=lambda: self.move(-1)).pack(fill="x", pady=(12, 2))
        ttk.Button(mid, text="▼ Down", command=lambda: self.move(1)).pack(fill="x", pady=2)
        self.all = tk.Listbox(b, height=12, width=22, bg=T.FIELD, selectbackground=T.SELECT, relief="solid", bd=1)
        self.all.grid(row=1, column=2, sticky="nsew")
        for v in project.verbs():
            self.all.insert("end", v)
        self.all.bind("<Double-1>", lambda e: self.add())
        self.lb.bind("<Double-1>", lambda e: self.remove())
        own = ttk.Frame(b, style="Panel.TFrame")
        own.grid(row=2, column=2, sticky="ew", pady=(6, 0))
        self.own = tk.StringVar()
        ttk.Entry(own, textvariable=self.own, width=14).pack(side="left", fill="x", expand=True)
        ttk.Button(own, text="Add your own", style="Small.TButton", command=self.add_own).pack(side="left", padx=4)
        self.refresh()

    def refresh(self):
        self.lb.delete(0, "end")
        for i, v in enumerate(self.chosen):
            self.lb.insert("end", ("★ " if i == 0 else "   ") + v)

    def add(self):
        for i in self.all.curselection():
            v = self.all.get(i)
            if v not in self.chosen:
                self.chosen.append(v)
        self.refresh()

    def add_own(self):
        v = self.own.get().strip()
        if v and v not in self.chosen:
            self.chosen.append(v)
            self.own.set("")
            self.refresh()

    def remove(self):
        for i in reversed(self.lb.curselection()):
            del self.chosen[i]
        self.refresh()

    def move(self, d):
        s = self.lb.curselection()
        if not s:
            return
        i = s[0]
        j = i + d
        if 0 <= j < len(self.chosen):
            self.chosen[i], self.chosen[j] = self.chosen[j], self.chosen[i]
            self.refresh()
            self.lb.selection_set(j)

    def ok(self):
        return ",".join(self.chosen)


def combo(parent, var, values, width=20, readonly=False):
    c = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly" if readonly else "normal")
    return c


def picker_field(parent, var, title, items_fn, icon_fn=None, kinds=None, width=22):
    """An entry with a "…" button that opens a picker (items_fn() -> [(key, text, kind)])."""
    f = ttk.Frame(parent, style="Panel.TFrame")
    ttk.Entry(f, textvariable=var, width=width).pack(side="left", fill="x", expand=True)

    def pick():
        r = PickerDialog(parent, title, items_fn(), kinds=kinds, icon_fn=icon_fn, current=var.get()).run()
        if r is not None:
            var.set(r)
    ttk.Button(f, text="…", width=3, style="Small.TButton", command=pick).pack(side="left", padx=(3, 0))
    return f
