"""Spells: data\\Spells.ini, one section a spell (a scroll or potion item casts it)."""
import tkinter as tk
from tkinter import ttk

from .. import theme as T
from ..widgets import photo
from .iniform import IniFormPage

EFFECTS = ["Bolt", "Area", "Heal", "Boost", "Teleport", "Home"]
ONLY = {   # key -> the effects it's for
    "Damage": ("Bolt", "Area"), "Range": ("Bolt",), "Slow": ("Bolt",), "Missile": ("Bolt",), "Radius": ("Area",),
    "Heal": ("Heal",), "Attack": ("Boost", "Shield"), "Defence": ("Boost", "Shield"), "Magic": ("Boost", "Shield"),
    "Sight": ("Boost", "Shield"), "Duration": ("Boost", "Shield"), "Map": ("Teleport",), "X": ("Teleport",),
    "Y": ("Teleport",)}


class SpellPage(IniFormPage):
    title = "Spells"
    icon = "✦"
    kind = "spell"
    ini_attr = "spells_ini"
    kinds = EFFECTS
    new_label = "New spell"

    def list_items(self):
        return [(s, s, self.ini.get(s, "Effect", "")) for s in self.ini.sections()]

    def build_form(self, f):
        f.columnconfigure(1, weight=1)
        f.columnconfigure(3, weight=1)
        self.widgets = {}
        head = ttk.Frame(f, style="Panel.TFrame")
        head.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.icon_label = tk.Label(head, bg=T.PANEL)
        self.icon_label.pack(side="left")
        self.name_label = ttk.Label(head, text="", style="Head.TLabel", font=T.FONT_TITLE)
        self.name_label.pack(side="left", padx=10)
        self.scroll_link = ttk.Label(head, text="", style="Link.TLabel", cursor="hand2")
        self.scroll_link.pack(side="left", padx=10)
        self.scroll_link.bind("<Button-1>", lambda e: self.open_scroll())
        r = 1
        self.section_label(f, r, "What it is")
        r += 1
        items = [""] + self.project.items()
        self.add(f, r, 0, "Effect", ttk.Combobox(f, textvariable=self.var("Effect"), values=EFFECTS, state="readonly",
                                                 width=14),
                 "Bolt: one foe. Area: every foe within Radius. Heal. Boost: Attack / Defence / Magic / Sight for a "
                 "while. Teleport. Home: to your homestead (needs the Access Crystal).")
        self.add(f, r, 2, "Kind", ttk.Combobox(f, textvariable=self.var("Kind"), values=["Scroll", "Potion"],
                                               state="readonly", width=10),
                 "Scroll: read (needs the skill level). Potion: drunk.")
        r += 1
        self.add(f, r, 0, "Cast by", ttk.Combobox(f, textvariable=self.var("Scroll"), values=items, width=22),
                 "The item that casts it (its Entities.ini Spell= names this spell).")
        self.add(f, r, 2, "Leaves", ttk.Combobox(f, textvariable=self.var("Leaves"), values=items, width=18),
                 "An item you get back (the empty vial).")
        r += 1
        self.add(f, r, 0, "Skill", ttk.Combobox(f, textvariable=self.var("Skill"), values=self.project.skills,
                                                width=14))
        self.add(f, r, 2, "Level", ttk.Spinbox(f, textvariable=self.var("Level"), from_=0, to=99, width=8))
        r += 1
        self.add(f, r, 0, "XP per cast", ttk.Entry(f, textvariable=self.var("XP"), width=10))
        r += 1
        self.section_label(f, r, "Effect")
        r += 1
        self.add(f, r, 0, "Damage", ttk.Entry(f, textvariable=self.var("Damage"), width=10), "min-max, e.g. 2-5.")
        self.add(f, r, 2, "Range (px)", ttk.Spinbox(f, textvariable=self.var("Range"), from_=0, to=2000, width=8))
        r += 1
        self.add(f, r, 0, "Radius (px)", ttk.Spinbox(f, textvariable=self.var("Radius"), from_=0, to=2000, width=8))
        self.add(f, r, 2, "Slow", ttk.Entry(f, textvariable=self.var("Slow"), width=10),
                 "percent,seconds: e.g. 50,8 = half speed for 8 seconds.")
        r += 1
        self.add(f, r, 0, "Heal", ttk.Entry(f, textvariable=self.var("Heal"), width=10), "min-max hitpoints.")
        self.add(f, r, 2, "Duration (s)", ttk.Spinbox(f, textvariable=self.var("Duration"), from_=0, to=3600, width=8))
        r += 1
        for i, key in enumerate(("Attack", "Defence", "Magic", "Sight")):
            self.add(f, r + i // 2, (i % 2) * 2, key + " +", ttk.Spinbox(f, textvariable=self.var(key), from_=0,
                                                                         to=1000, width=8))
        r += 2
        maps = [""] + self.project.maps()
        self.add(f, r, 0, "Teleport to map", ttk.Combobox(f, textvariable=self.var("Map"), values=maps, width=12),
                 "Blank = the start in Config.ini.")
        xy = ttk.Frame(f, style="Panel.TFrame")
        ttk.Spinbox(xy, textvariable=self.var("X"), from_=0, to=2000, width=6).pack(side="left")
        ttk.Label(xy, text=" , ", style="Panel.TLabel").pack(side="left")
        ttk.Spinbox(xy, textvariable=self.var("Y"), from_=0, to=2000, width=6).pack(side="left")
        self.add(f, r, 2, "at X, Y (px)", xy, key=("X", "Y"))
        r += 1
        self.section_label(f, r, "Looks and sounds")
        r += 1
        self.add(f, r, 0, "Missile", ttk.Entry(f, textvariable=self.var("Missile"), width=20),
                 "Bolt: a sprites\\Effects sprite that flies to the target.")
        self.add(f, r, 2, "Impact", ttk.Entry(f, textvariable=self.var("Impact"), width=16),
                 "sprites\\Effects\\<Impact>1..4 played on the target.")
        r += 1
        self.add(f, r, 0, "Sound", ttk.Combobox(f, textvariable=self.var("Sound"),
                                                values=[""] + [s for s in self.project.sounds() if not s.endswith(".mid")],
                                                width=20))

    def add(self, f, r, c, label, w, hint=None, key=None):
        self.row(f, r, label, w, hint, col=c)
        k = key or next((k for k, v in self.vars.items() if str(v) == str(w.cget("textvariable"))), None) \
            if hasattr(w, "cget") and "textvariable" in w.keys() else key
        if isinstance(k, tuple):
            for kk in k:
                self.widgets[kk] = w
        elif k:
            self.widgets[k] = w

    def after_load(self):
        self.name_label.configure(text=self.key or "")
        scroll = self.vars["Scroll"].get() if self.key else ""
        self.scroll_link.configure(text=("Open %s in Entities" % scroll) if scroll else "")
        img = self.project.sprite("Entities", scroll) if scroll else None
        self._ph = photo(img, (40, 40), key=("spellicon", scroll)) if img else None
        self.icon_label.configure(image=self._ph or "")
        self.apply_effect()

    def on_change(self, key):
        if key == "Effect":
            self.apply_effect()
        if key == "Scroll":
            self.after_load()

    def apply_effect(self):
        eff = self.vars["Effect"].get()
        for key, effects in ONLY.items():
            w = self.widgets.get(key)
            if w is None:
                continue
            on = bool(self.key) and (eff in effects or not eff)
            for c in [w] + list(w.winfo_children()):
                try:
                    c.state(["!disabled"] if on else ["disabled"])
                except (tk.TclError, AttributeError):
                    pass

    def open_scroll(self):
        s = self.vars["Scroll"].get().strip()
        if s:
            self.app.goto("entity", s)

    def init_new(self, name):
        self.ini.set(name, "Effect", "Bolt")
        self.ini.set(name, "Kind", "Scroll")
        self.ini.set(name, "Skill", "Channeling")
        self.ini.set(name, "Level", "1")
