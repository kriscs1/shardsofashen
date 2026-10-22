"""Scripts: Data\\Scripts\\*.txt. Each line is a command and its arguments; the editor knows every command's arguments
(dragonsword/script_language.py) and gives each the right choices and builders. Goto lines renumber themselves."""
import os
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image

from .. import theme as T
from .. import scriptlang as SL
from ..app import Page
from ..project import ScriptDoc, ScriptLine, parse_map_name, MapDoc
from ..render import render
from ..widgets import (FilterList, PickerDialog, ConditionBuilder, Dialog, Tooltip, photo, ask_text, confirm)
from .iniform import IniFormPage


# =================================================================================================================
# Builders the "…" buttons open
# =================================================================================================================
class QuantityDialog(Dialog):
    def __init__(self, parent, value):
        super().__init__(parent, "Change by")
        v = value.strip()
        op = v[:1] if v[:1] in "+-=" else "+"
        self.op = tk.StringVar(value={"+": "Add", "-": "Take away", "=": "Set to"}[op])
        self.n = tk.StringVar(value=v[1:] if v[:1] in "+-=" else v or "1")
        for i, t in enumerate(("Add", "Take away", "Set to")):
            ttk.Radiobutton(self.body, text=t, value=t, variable=self.op).grid(row=0, column=i, padx=4, sticky="w")
        ttk.Entry(self.body, textvariable=self.n, width=12).grid(row=1, column=0, columnspan=3, sticky="w", pady=8)

    def ok(self):
        return {"Add": "+", "Take away": "-", "Set to": "="}[self.op.get()] + self.n.get().strip()


class MapPointDialog(Dialog):
    """Click a point on a map: pixels (Teleport, Add.Entity...) or a tile (1-based)."""

    def __init__(self, parent, project, map_name, value, tiles=False):
        super().__init__(parent, "Pick a tile" if tiles else "Pick a point")
        self.project, self.tiles = project, tiles
        top = ttk.Frame(self.body, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Map", style="Panel.TLabel").pack(side="left")
        self.map = tk.StringVar(value=map_name if map_name in project.maps() else (project.maps() or [""])[0])
        cb = ttk.Combobox(top, textvariable=self.map, values=project.maps(), width=12, state="readonly")
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self.draw())
        self.value = tk.StringVar(value=value)
        ttk.Label(top, text="  value", style="Panel.TLabel").pack(side="left")
        ttk.Entry(top, textvariable=self.value, width=14).pack(side="left", padx=6)
        ttk.Label(top, text=("click a tile" if tiles else "click where (the point is the top-left of a sprite)"),
                  style="PanelMuted.TLabel").pack(side="left")
        self.canvas = tk.Canvas(self.body, width=project.map_w * project.tile_w, height=project.map_h * project.tile_h,
                                highlightthickness=1, highlightbackground=T.LINE, cursor="crosshair")
        self.canvas.pack(pady=6)
        self.canvas.bind("<Button-1>", self.click)
        self.draw()

    def draw(self):
        doc = MapDoc(self.project, self.map.get())
        self._ph = photo(render(self.project, doc, dim_roofs=True))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._ph, anchor="nw")
        self.mark()

    def mark(self):
        self.canvas.delete("mark")
        p = self.value.get().split(",")
        try:
            x, y = int(p[0]), int(p[1])
        except (ValueError, IndexError):
            return
        tw, th = self.project.tile_w, self.project.tile_h
        if self.tiles:
            self.canvas.create_rectangle((x - 1) * tw, (y - 1) * th, x * tw, y * th, outline="#ffcc00", width=3,
                                         tags="mark")
        else:
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, outline="#ffcc00", width=3, tags="mark")

    def click(self, e):
        tw, th = self.project.tile_w, self.project.tile_h
        self.value.set("%d,%d" % ((e.x // tw + 1, e.y // th + 1) if self.tiles else (e.x, e.y)))
        self.mark()

    def ok(self):
        return self.value.get().strip()


class NewScriptDialog(Dialog):
    """A new script: its name built from what starts it."""
    PATTERNS = [("Talk to an NPC", "Talk to {npc}"), ("Use an item on something", "Use {item} With {thing}"),
                ("A verb on a thing", "{verb} {thing}"), ("When an NPC is killed", "Kill {npc}"),
                ("When a map is entered", "{map}"), ("A skill clicked in the Stats tab", "{skill} Skill"),
                ("A trigger (any name)", "{name}")]

    def __init__(self, parent, project, preset=None):
        super().__init__(parent, "New script", ok="Create")
        self.project = project
        b = self.body
        b.columnconfigure(1, weight=1)
        ttk.Label(b, text="It runs", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.kind = tk.StringVar(value=self.PATTERNS[0][0])
        cb = ttk.Combobox(b, textvariable=self.kind, values=[k for k, _ in self.PATTERNS], state="readonly", width=34)
        cb.grid(row=0, column=1, sticky="ew", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.fields())
        self.parts = {k: tk.StringVar() for k in ("npc", "item", "thing", "verb", "map", "skill", "name")}
        for v in self.parts.values():
            v.trace_add("write", lambda *a: self.update_name())
        self.part_frame = ttk.Frame(b, style="Panel.TFrame")
        self.part_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Label(b, text="Name", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.name = tk.StringVar()
        ttk.Entry(b, textvariable=self.name, width=40).grid(row=2, column=1, sticky="ew")
        ttk.Label(b, text="Start with", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.template = tk.StringVar(value="A message")
        ttk.Combobox(b, textvariable=self.template, values=["Nothing (just End)", "A message", "A conversation",
                                                             "A distance check and a message"],
                     state="readonly", width=34).grid(row=3, column=1, sticky="w", pady=(8, 0))
        if preset:
            self.kind.set(preset.get("kind", self.kind.get()))
            for k, v in preset.items():
                if k in self.parts:
                    self.parts[k].set(v)
        self.fields()

    def fields(self):
        for w in self.part_frame.winfo_children():
            w.destroy()
        pat = dict(self.PATTERNS)[self.kind.get()]
        values = {"npc": self.project.npcs(), "item": self.project.items(),
                  "thing": self.project.placeable() + self.project.tiles(), "verb": self.project.verbs(),
                  "map": self.project.maps(), "skill": self.project.skills, "name": []}
        r = 0
        for key in ("npc", "item", "verb", "thing", "map", "skill", "name"):
            if "{%s}" % key in pat:
                ttk.Label(self.part_frame, text=key.capitalize(), style="Panel.TLabel", width=8).grid(row=r, column=0,
                                                                                                     sticky="w")
                ttk.Combobox(self.part_frame, textvariable=self.parts[key], values=values[key], width=34).grid(
                    row=r, column=1, sticky="ew", pady=1)
                r += 1
        self.update_name()

    def update_name(self):
        pat = dict(self.PATTERNS)[self.kind.get()]
        name = pat
        for k, v in self.parts.items():
            name = name.replace("{%s}" % k, v.get().strip())
        self.name.set(name.strip())

    def ok(self):
        name = self.name.get().strip()
        if not name or "{" in name:
            return False
        bad = set('\\/:*?"<>|') & set(name)
        if bad:
            self.bell()
            return False
        return name, self.template.get()


TEMPLATES = {
    "Nothing (just End)": [("End", [])],
    "A message": [("Display.Message", ["Yellow", "Something happens."]), ("End", [])],
    "A conversation": [("Display.Conversation", ["{npc}", "Hello there!", "Goodbye.", "02"]), ("End", [])],
    "A distance check and a message": [(">Distance.From.Clicked.Entity", ["40", "04"]),
                                       ("Display.Message", ["Yellow", "Something happens."]), ("End", []),
                                       ("Display.Message", ["DarkRed", "You are too far away!"]), ("End", [])],
}


# =================================================================================================================
# The section
# =================================================================================================================
class ScriptPage(Page):
    title = "Scripts"
    icon = "📜"
    kind = "script"

    def __init__(self, app):
        super().__init__(app)
        self.doc = None
        self.loaded = None
        self.sel = None              # index into doc.lines
        self._edit_key, self._edit_time = None, 0
        self._quiet = False
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True)
        left = ttk.Frame(pw, style="Panel.TFrame", padding=10)
        pw.add(left, weight=0)
        self.list = FilterList(left, self.picked, kinds=SL.KINDS)
        self.list.pack(fill="both", expand=True)
        b = ttk.Frame(left, style="Panel.TFrame")
        b.pack(fill="x", pady=(6, 0))
        ttk.Button(b, text="＋ New", style="Small.TButton", command=self.new_script).pack(side="left")
        ttk.Button(b, text="Duplicate", style="Small.TButton", command=self.duplicate).pack(side="left", padx=3)
        ttk.Button(b, text="Rename", style="Small.TButton", command=self.rename).pack(side="left")
        ttk.Button(b, text="Delete", style="Small.TButton", command=self.delete).pack(side="left", padx=3)

        right = ttk.Frame(pw, style="Card.TFrame", padding=12)
        pw.add(right, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(side="left")
        self.kind_label = ttk.Label(head, text="", style="PanelMuted.TLabel")
        self.kind_label.pack(side="left", padx=10, pady=(6, 0))
        self.runs = ttk.Frame(right, style="Panel.TFrame")
        self.runs.grid(row=1, column=0, sticky="ew", pady=(2, 6))

        body = ttk.PanedWindow(right, orient="vertical")
        body.grid(row=2, column=0, sticky="nsew")
        tbl = ttk.Frame(body, style="Panel.TFrame")
        body.add(tbl, weight=3)
        tools = ttk.Frame(tbl, style="Panel.TFrame")
        tools.pack(fill="x", pady=(0, 4))
        for text, cmd, tip in (("＋ Line below", lambda: self.insert(1), "Insert (adds a line below)"),
                               ("＋ Above", lambda: self.insert(0), ""), ("// Comment", self.insert_comment, ""),
                               ("Duplicate", self.dup_line, ""), ("▲", lambda: self.move(-1), "Ctrl+Up"),
                               ("▼", lambda: self.move(1), "Ctrl+Down"), ("Delete line", self.delete_line, "Delete")):
            w = ttk.Button(tools, text=text, style="Small.TButton", command=cmd)
            w.pack(side="left", padx=(0, 3))
            if tip:
                Tooltip(w, tip)
        self.tree = ttk.Treeview(tbl, columns=("cmd", "args"), show="headings", selectmode="browse")
        self.tree.heading("cmd", text="Command")
        self.tree.heading("args", text="Arguments")
        self.tree.column("cmd", width=T.px(230), stretch=False)
        self.tree.column("args", width=T.px(600))
        self.tree["show"] = ("tree", "headings")
        self.tree.heading("#0", text="#")
        self.tree.column("#0", width=T.px(56), stretch=False)
        sb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("comment", foreground="#8a7a66", font=("Segoe UI", 9, "italic"))
        self.tree.tag_configure("cond", foreground="#2f5f8a")
        self.tree.tag_configure("bad", background="#f7d9d2")
        self.tree.tag_configure("warn", background="#f8ecc8")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.line_picked())
        self.tree.bind("<Insert>", lambda e: self.insert(1))
        self.tree.bind("<Delete>", lambda e: self.delete_line())
        self.tree.bind("<Control-Up>", lambda e: (self.move(-1), "break")[1])
        self.tree.bind("<Control-Down>", lambda e: (self.move(1), "break")[1])

        lower = ttk.PanedWindow(body, orient="horizontal")
        body.add(lower, weight=2)
        self.editor = ttk.LabelFrame(lower, text="Line", padding=10)
        lower.add(self.editor, weight=3)
        probs = ttk.LabelFrame(lower, text="Problems", padding=6)
        lower.add(probs, weight=1)
        self.problems = tk.Listbox(probs, bg=T.FIELD, relief="flat", font=T.FONT_SMALL, activestyle="none",
                                   selectbackground=T.SELECT)
        self.problems.pack(fill="both", expand=True)
        self.problems.bind("<<ListboxSelect>>", lambda e: self.problem_picked())
        self.problem_lines = []
        self.refresh_list()

    # --- the list
    def refresh_list(self):
        self.project.refresh("scripts")
        self.list.set_items([(s, s, SL.kind_of(self.project, s)) for s in self.project.scripts()])

    def picked(self, key):
        if self.doc and key == self.doc.name:
            return
        if not self.leave_ok():
            self.list.select(self.doc.name if self.doc else "", notify=False)
            return
        self.load(key)

    def open(self, key, line=None, **kw):
        if not self.doc or key != self.doc.name:
            if not self.leave_ok():
                return
            self.load(key)
        self.list.select(key, notify=False)
        if line:
            self.select_command(int(line))

    def load(self, name):
        self.doc = ScriptDoc(self.project, name) if name else None
        self.loaded = self.doc.text_lines() if self.doc else None
        self.sel = None
        self.clear_history()
        self.show()

    def show(self):
        d = self.doc
        self.name_label.configure(text=d.name if d else "")
        self.kind_label.configure(text=(SL.kind_of(self.project, d.name) + ("" if d.exists else "  ·  not saved yet"))
                                  if d else "")
        self.show_runs()
        self.draw_lines()
        self.build_editor()
        self.app.refresh_chrome()

    def show_runs(self):
        for w in self.runs.winfo_children():
            w.destroy()
        if not self.doc:
            return
        n = self.doc.name
        links, text = [], ""
        trig = self.project.index()["script_trigger"].get(n, [])
        if n.startswith("Talk to "):
            text = "When the player talks to"
            links = [(n[8:], lambda: self.app.goto("entity", n[8:]))]
        elif n.startswith("Kill "):
            text = "When the player kills"
            links = [(n[5:], lambda: self.app.goto("entity", n[5:]))]
        elif n.startswith("Use ") and " With " in n:
            a, b = n[4:].split(" With ", 1)
            text = "When the player uses"
            links = [(a, lambda: self.app.goto("entity", a)), ("with " + b, lambda: self.goto_thing(b))]
        elif parse_map_name(n):
            text = "Each time this map is entered:"
            links = [(n, lambda: self.app.goto("map", n))]
        elif n.endswith(" Skill"):
            text = "When the skill is clicked in the Stats tab"
        elif " " in n and n.split(" ")[0] in self.project.verbs():
            v, thing = n.split(" ", 1)
            text = "When the player does %s on" % v
            links = [(thing, lambda: self.goto_thing(thing))]
        if trig:
            text = (text + "   ·   " if text else "") + "Trigger on"
            links += [("%s %d,%d" % t, lambda t=t: self.app.goto("map", t[0], tile=(t[1], t[2]))) for t in trig]
        ttk.Label(self.runs, text=text or "Runs when another script goes to it (Goto.Script).",
                  style="PanelMuted.TLabel").pack(side="left")
        box = ttk.Frame(self.runs, style="Panel.TFrame")
        box.pack(side="left", padx=6)
        IniFormPage.fill_links(box, links, "")

    def goto_thing(self, name):
        import re
        base = re.sub(r"\d{3}$", "", name)
        if name in self.project.tiles() or any(t.startswith(base) for t in self.project.tiles() if base == name):
            t = name if name in self.project.tiles() else next(t for t in self.project.tiles() if t.startswith(base))
            self.app.goto("tile", t)
        else:
            self.app.goto("entity", name)

    # --- the lines
    def number_of(self, index):
        """The command number (1-based) of doc.lines[index] (None for a comment)."""
        n = 0
        for i, l in enumerate(self.doc.lines):
            if not l.is_comment:
                n += 1
            if i == index:
                return None if l.is_comment else n
        return None

    def index_of(self, number):
        n = 0
        for i, l in enumerate(self.doc.lines):
            if not l.is_comment:
                n += 1
                if n == number:
                    return i
        return None

    def summary(self, number):
        i = self.index_of(number)
        if i is None:
            return "%02d" % number
        l = self.doc.lines[i]
        return "%02d  %s  %s" % (number, l.command, " | ".join(a.strip() for a in l.args if a.strip())[:60])

    def draw_lines(self):
        t = self.tree
        t.delete(*t.get_children())
        if not self.doc:
            self.problems.delete(0, "end")
            return
        probs = SL.check(self.project, self.doc)
        worst = {}
        for n, level, _ in probs:
            if n and (level == "error" or n not in worst):
                worst[n] = level
        num = 0
        for i, l in enumerate(self.doc.lines):
            if l.is_comment:
                t.insert("", "end", iid=str(i), text="//", values=("", l.comment.strip()), tags=("comment",))
                continue
            num += 1
            types = SL.COMMANDS.get(l.command, [])
            parts = []
            for k, a in enumerate(l.args):
                a = a.strip()
                if not a:
                    continue
                if k < len(types) and SL.is_goto(types[k]):
                    parts.append("→ " + a)
                else:
                    parts.append(a.replace("\\", " ⏎ "))
            tags = ["cond"] if l.command.startswith(">") else []
            if num in worst:
                tags.append("bad" if worst[num] == "error" else "warn")
            t.insert("", "end", iid=str(i), text="%02d" % num, values=(l.command, "  |  ".join(parts)), tags=tags)
        self.problems.delete(0, "end")
        self.problem_lines = []
        for n, level, text in probs:
            self.problems.insert("end", ("✖ " if level == "error" else "⚠ ") + ("%02d  " % n if n else "") + text)
            self.problems.itemconfigure("end", foreground=T.DANGER if level == "error" else T.WARN)
            self.problem_lines.append(n)
        if not probs:
            self.problems.insert("end", "✔ No problems found.")
            self.problems.itemconfigure("end", foreground=T.OK)
        if self.sel is not None and self.sel < len(self.doc.lines):
            self._quiet = True
            t.selection_set(str(self.sel))
            t.see(str(self.sel))
            self._quiet = False

    def problem_picked(self):
        s = self.problems.curselection()
        if s and s[0] < len(self.problem_lines) and self.problem_lines[s[0]]:
            self.select_command(self.problem_lines[s[0]])

    def select_command(self, number):
        i = self.index_of(number)
        if i is not None:
            self.sel = i
            self.tree.selection_set(str(i))
            self.tree.see(str(i))

    def line_picked(self):
        if self._quiet:
            return
        s = self.tree.selection()
        self.sel = int(s[0]) if s else None
        self.build_editor()

    # --- the line editor
    def build_editor(self):
        ed = self.editor
        for w in ed.winfo_children():
            w.destroy()
        self.arg_vars = []
        if not self.doc or self.sel is None or self.sel >= len(self.doc.lines):
            ttk.Label(ed, text="Pick a line to edit it." if self.doc else "Pick a script, or make a new one.",
                      style="PanelMuted.TLabel").pack(anchor="w")
            return
        l = self.doc.lines[self.sel]
        ed.columnconfigure(1, weight=1)
        if l.is_comment:
            ttk.Label(ed, text="Comment", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
            v = tk.StringVar(value=l.comment.strip())
            e = ttk.Entry(ed, textvariable=v)
            e.grid(row=0, column=1, sticky="ew")
            v.trace_add("write", lambda *a: self.set_comment(v.get()))
            ttk.Label(ed, text="Comments are notes for you: the game skips them.", style="PanelMuted.TLabel").grid(
                row=1, column=1, sticky="w")
            return
        ttk.Label(ed, text="Command", style="Panel.TLabel", font=T.FONT_BOLD).grid(row=0, column=0, sticky="w")
        self.cmd_var = tk.StringVar(value=l.command)
        cb = ttk.Combobox(ed, textvariable=self.cmd_var, values=SL.COMMAND_NAMES, width=34)
        cb.grid(row=0, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_command(self.cmd_var.get()))
        cb.bind("<Return>", lambda e: self.set_command(self.cmd_var.get()))
        cb.bind("<FocusOut>", lambda e: self.set_command(self.cmd_var.get()))
        cb.bind("<KeyRelease>", lambda e, c=cb: self.filter_commands(c))
        help_text = SL.help_for(l.command)
        ttk.Label(ed, text=help_text, style="PanelMuted.TLabel", wraplength=640, justify="left").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 8))
        types = SL.COMMANDS.get(l.command, [])
        cmd_lines = [(x.command, x.args) for x in self.doc.commands()]
        for k, t in enumerate(types):
            r = 2 + k
            val = l.args[k] if k < len(l.args) else ""
            lab = ttk.Label(ed, text=t.strip().capitalize(), style="Panel.TLabel")
            lab.grid(row=r, column=0, sticky="w", padx=(0, 10), pady=2)
            Tooltip(lab, SL.help_for(t))
            v = tk.StringVar(value=val.strip() if val.strip() else "")
            opts = SL.options(self.project, t, l.args, cmd_lines, self.summary)
            box = ttk.Combobox(ed, textvariable=v, values=opts, width=60)
            box.grid(row=r, column=1, sticky="ew", pady=2)
            Tooltip(box, SL.help_for(t))
            box.bind("<Button-3>", lambda e, b=box, vv=v: self.variable_menu(e, b, vv))
            if SL.is_goto(t):
                box.bind("<<ComboboxSelected>>", lambda e, vv=v: vv.set(vv.get().split()[0] if vv.get() else ""))
            v.trace_add("write", lambda *a, kk=k, vv=v: self.set_arg(kk, vv.get()))
            kind = SL.builder_kind(t, l.args, l.command)
            if kind:
                ttk.Button(ed, text="…", width=3, style="Small.TButton",
                           command=lambda kk=k, tt=t, vv=v, kd=kind: self.builder(kd, tt, vv)).grid(row=r, column=2,
                                                                                                    padx=2)
            jump = ttk.Button(ed, text="↗", width=3, style="Small.TButton",
                              command=lambda tt=t, vv=v: self.jump(tt, vv.get()))
            jump.grid(row=r, column=3)
            Tooltip(jump, "Open what this names")
            self.arg_vars.append(v)
        if not types and l.command not in SL.COMMANDS:
            ttk.Label(ed, text="The game doesn't know this command: pick one from the list.", style="Bad.TLabel").grid(
                row=2, column=0, columnspan=4, sticky="w")

    def filter_commands(self, cb):
        q = self.cmd_var.get().lower().lstrip(">")
        cb.configure(values=[c for c in SL.COMMAND_NAMES if q in c.lower()] or SL.COMMAND_NAMES)

    def variable_menu(self, e, box, var):
        m = tk.Menu(self, tearoff=0)
        for name, desc in SL.VARIABLES:
            m.add_command(label="%s   (%s)" % (name, desc[:50]),
                          command=lambda n=name: (box.insert("insert", n), var.set(box.get())))
        m.tk_popup(e.x_root, e.y_root)

    def remember_edit(self, key):
        now = time.time()
        if not (key == self._edit_key and now - self._edit_time < 1.2):
            self.remember()
        self._edit_key, self._edit_time = key, now

    def set_command(self, name):
        name = name.strip()
        l = self.doc.lines[self.sel]
        if name == l.command or not name:
            return
        self.remember()
        l.command = name
        n = len(SL.COMMANDS.get(name, l.args))
        l.args = (l.args + [""] * n)[:n] if name in SL.COMMANDS else l.args
        l.normalise()
        self.draw_lines()
        self.build_editor()
        self.app.refresh_chrome()

    def set_arg(self, k, value):
        l = self.doc.lines[self.sel]
        types = SL.COMMANDS.get(l.command, [])
        if k < len(types) and SL.is_goto(types[k]) and value.strip() and not value.strip().isdigit():
            value = value.split()[0]
        old = l.args[k].strip() if k < len(l.args) else ""
        if value.strip() == old:
            return
        self.remember_edit((self.sel, k))
        while len(l.args) <= k:
            l.args.append("")
        if k < len(types) and SL.is_goto(types[k]) and value.strip().isdigit():
            value = "%02d" % int(value)
        l.args[k] = value
        l.normalise()
        self.draw_lines()
        self.app.refresh_chrome()

    def set_comment(self, text):
        l = self.doc.lines[self.sel]
        if l.comment.strip() == text.strip():
            return
        self.remember_edit((self.sel, "c"))
        l.comment = " " + text if text else ""
        self.draw_lines()
        self.app.refresh_chrome()

    def builder(self, kind, t, var):
        cur = var.get()
        r = None
        if kind == "COND":
            r = ConditionBuilder(self, self.project, cur, title="Requirement").run()
        elif kind == "QTY":
            r = QuantityDialog(self, cur).run()
        elif kind in ("COORD", "TILE"):
            r = MapPointDialog(self, self.project, self.guess_map(), cur, tiles=(kind == "TILE")).run()
        elif kind == "PICK":
            n = SL.norm(t)
            l = self.doc.lines[self.sel]
            items = SL.options(self.project, t, l.args, [(x.command, x.args) for x in self.doc.commands()],
                               self.summary)
            icon = None
            if n in SL.ITEM_TYPES | SL.ENTITY_TYPES | {"NPC NAME"}:
                icon = lambda k: photo(self.project.sprite("Entities", k), (32, 32), key=("ent", k))
            elif n in SL.TILE_TYPES:
                icon = lambda k: photo(self.project.sprite("Tiles", k), (32, 32), key=("tile", k))
            r = PickerDialog(self, t.strip().capitalize(), [(o, o, "") for o in items], icon_fn=icon, current=cur).run()
        if r is not None:
            var.set(r)

    def guess_map(self):
        n = self.doc.name if self.doc else ""
        if parse_map_name(n):
            return n
        trig = self.project.index()["script_trigger"].get(n)
        if trig:
            return trig[0][0]
        mp = self.app.page_of("map")
        return mp.doc.name if getattr(mp, "doc", None) else ""

    def jump(self, t, value):
        if SL.is_goto(t) and value.strip().isdigit():
            self.select_command(int(value))
            return
        link = SL.link_of(t, value)
        if link:
            if link[0] == "script" and link[1] not in self.project.scripts():
                self.app.status("There's no script %s yet: make it with New." % link[1], "warn")
                return
            self.app.goto(*link)
        else:
            self.app.status("Nothing to open for that.", "warn")

    # --- line operations (gotos follow their lines)
    def renumber(self, order_before):
        """After lines moved, were added or removed: every goto points at the same line it did (a removed line's
        gotos go to the line now in its place)."""
        before = [id(l) for l in order_before if not l.is_comment]
        after = [id(l) for l in self.doc.lines if not l.is_comment]
        pos = {lid: i + 1 for i, lid in enumerate(after)}
        for l in self.doc.lines:
            if l.is_comment:
                continue
            types = SL.COMMANDS.get(l.command, [])
            for k, t in enumerate(types):
                if k < len(l.args) and SL.is_goto(t) and l.args[k].strip().isdigit():
                    old = int(l.args[k])
                    if 1 <= old <= len(before):
                        target = before[old - 1]
                        new = pos.get(target)
                        if new is None:                     # its line was removed: the one now in its place
                            new = min(old, len(after))
                        l.args[k] = "%02d" % new if new else ""

    def insert(self, below):
        if not self.doc:
            return
        self.remember()
        before = list(self.doc.lines)
        at = (self.sel + below) if self.sel is not None else len(self.doc.lines)
        self.doc.lines.insert(at, ScriptLine("Display.Message", ["Yellow", ""]))
        self.renumber(before)
        self.sel = at
        self.draw_lines()
        self.build_editor()
        self.app.refresh_chrome()

    def insert_comment(self):
        if not self.doc:
            return
        self.remember()
        at = self.sel if self.sel is not None else 0
        self.doc.lines.insert(at, ScriptLine(comment=" "))
        self.sel = at
        self.draw_lines()
        self.build_editor()

    def dup_line(self):
        if self.sel is None:
            return
        self.remember()
        before = list(self.doc.lines)
        self.doc.lines.insert(self.sel + 1, self.doc.lines[self.sel].copy())
        self.renumber(before)
        self.sel += 1
        self.draw_lines()
        self.build_editor()

    def delete_line(self):
        if self.sel is None or not self.doc.lines:
            return
        self.remember()
        before = list(self.doc.lines)
        del self.doc.lines[self.sel]
        self.renumber(before)
        self.sel = min(self.sel, len(self.doc.lines) - 1) if self.doc.lines else None
        self.draw_lines()
        self.build_editor()
        self.app.refresh_chrome()

    def move(self, d):
        i = self.sel
        if i is None or not 0 <= i + d < len(self.doc.lines):
            return
        self.remember()
        before = list(self.doc.lines)
        L = self.doc.lines
        L[i], L[i + d] = L[i + d], L[i]
        self.renumber(before)
        self.sel = i + d
        self.draw_lines()
        self.build_editor()

    # --- undo, saving
    def snapshot(self):
        return (self.doc.snapshot(), self.sel) if self.doc else None

    def restore(self, snap):
        lines, self.sel = snap
        self.doc.restore(lines)
        self.draw_lines()
        self.build_editor()

    def is_dirty(self):
        return bool(self.doc) and (self.doc.text_lines() != self.loaded or not self.doc.exists)

    def current(self):
        return self.doc.name if self.doc else ""

    def save(self):
        if not self.doc:
            return True
        errors = [p for p in SL.check(self.project, self.doc) if p[1] == "error"]
        self.doc.save()
        self.loaded = self.doc.text_lines()
        self.project.refresh("scripts", "attributes")
        self.refresh_list()
        self.list.select(self.doc.name, notify=False)
        self.show()
        if errors:
            self.app.status("Saved %s, but it has %d problem(s): see Problems." % (self.doc.name, len(errors)), "warn")
        else:
            self.app.status("Saved %s." % self.doc.name, "ok")
        return True

    def discard(self):
        if self.doc and not self.doc.exists:
            self.doc = None
            self.show()
            return
        self.load(self.doc.name if self.doc else None)

    def search_items(self):
        return [(s, s) for s in self.project.scripts()]

    def on_show(self):
        if self.doc and self.doc.exists and not self.is_dirty():
            from ..project import mtime
            if mtime(self.doc.path) != self.doc.stamp:
                self.load(self.doc.name)
        names = set(self.project.scripts())
        self.project.refresh("scripts")
        if set(self.project.scripts()) != names:
            self.refresh_list()

    # --- new, duplicate, rename, delete
    def new_script(self, preset=None):
        if not self.leave_ok():
            return None
        r = NewScriptDialog(self, self.project, preset).run()
        if not r:
            return None
        name, template = r
        if name in self.project.scripts():
            self.open(name)
            self.app.status("%s already exists: opened it." % name, "warn")
            return name
        self.doc = ScriptDoc(self.project, name)
        npc = name[8:] if name.startswith("Talk to ") else "Someone"
        self.doc.lines = [ScriptLine(c, [a.replace("{npc}", npc) for a in args]) for c, args in TEMPLATES[template]]
        self.loaded = []
        self.sel = 0
        self.clear_history()
        self.show()
        self.app.status("New script %s: Save to keep it." % name)
        return name

    def duplicate(self):
        if not self.doc or not self.leave_ok():
            return
        name = ask_text(self, "Duplicate", "Name for the copy:", self.doc.name + " copy")
        if not name or name in self.project.scripts():
            return
        lines = [l.copy() for l in self.doc.lines]
        self.doc = ScriptDoc(self.project, name)
        self.doc.lines = lines
        self.loaded = []
        self.show()

    def rename(self):
        if not self.doc or not self.doc.exists or not self.leave_ok():
            return
        name = ask_text(self, "Rename", "New name:", self.doc.name)
        if not name or name == self.doc.name:
            return
        if name in self.project.scripts():
            self.app.status("There's already a script called %s." % name, "error")
            return
        os.replace(self.doc.path, self.project.script_path(name))
        trig = self.project.index()["script_trigger"].get(self.doc.name, [])
        self.refresh_list()
        self.load(name)
        self.list.select(name, notify=False)
        if trig:
            self.app.status("Renamed. %d trigger(s) still name the old script: update them in Maps." % len(trig), "warn")
        else:
            self.app.status("Renamed to %s." % name, "ok")

    def delete(self):
        if not self.doc:
            return
        if not confirm(self, "Delete", "Delete the script %s?" % self.doc.name):
            return
        if os.path.exists(self.doc.path):
            os.remove(self.doc.path)
        self.doc = None
        self.refresh_list()
        self.show()
