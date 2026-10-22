"""The editor's look: warm parchment panels, a dark oak navigation rail and amber highlights (the game's own colours)."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG = "#efe7d8"          # the window
PANEL = "#f8f3ea"       # cards and lists
FIELD = "#fffdf8"       # text boxes
LINE = "#d6c8b0"        # borders
TEXT = "#2d241c"
MUTED = "#7b6a58"
ACCENT = "#a8692c"      # amber
ACCENT_DARK = "#7c4a1c"
SELECT = "#f0d3a8"
BUTTON = "#e6d5b8"      # buttons: a darker tan than the panels, so they stand out
BUTTON_EDGE = "#b9a27f"
RAIL = "#2b221b"        # the navigation rail
RAIL_TEXT = "#e9dcc6"
RAIL_HOT = "#43352a"
RAIL_SEL = "#5a4330"
DANGER = "#b23b2e"
OK = "#3d7a3a"
WARN = "#b07a12"

FONT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI Semibold", 10)
FONT_TITLE = ("Segoe UI Semibold", 15)
FONT_HEAD = ("Segoe UI Semibold", 11)
MONO = ("Consolas", 10)
SCALE = 1.0             # the display's scaling (1.5 on a 150% screen): set by setup(); px() sizes things with it


def px(n):
    """n pixels at 100% display scaling, in real pixels."""
    return int(round(n * SCALE))


def setup(root):
    global SCALE
    try:
        SCALE = max(1.0, float(root.tk.call("tk", "scaling")) / (96 / 72))
    except (tk.TclError, ValueError):
        SCALE = 1.0
    root.configure(bg=BG)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        except tk.TclError:
            pass
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=TEXT, fieldbackground=FIELD, bordercolor=LINE, lightcolor=PANEL,
                darkcolor=LINE, troughcolor=BG, focuscolor=ACCENT, font=FONT, selectbackground=SELECT,
                selectforeground=TEXT, insertcolor=TEXT)
    s.configure("TFrame", background=BG)
    s.configure("Panel.TFrame", background=PANEL)
    s.configure("Card.TFrame", background=PANEL, relief="solid", borderwidth=1)
    s.configure("TLabel", background=BG, foreground=TEXT)
    s.configure("Panel.TLabel", background=PANEL)
    s.configure("Muted.TLabel", foreground=MUTED, font=FONT_SMALL)
    s.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=FONT_SMALL)
    s.configure("Title.TLabel", font=FONT_TITLE)
    s.configure("Head.TLabel", font=FONT_HEAD, background=PANEL)
    s.configure("HeadBG.TLabel", font=FONT_HEAD)
    s.configure("Warn.TLabel", foreground=WARN, background=PANEL, font=FONT_SMALL)
    s.configure("Bad.TLabel", foreground=DANGER, background=PANEL, font=FONT_SMALL)
    s.configure("Link.TLabel", foreground=ACCENT_DARK, background=PANEL, font=("Segoe UI", 9, "underline"))
    s.configure("TButton", padding=(10, 4), background=BUTTON, bordercolor=BUTTON_EDGE, lightcolor="#f3e8d6",
                darkcolor=BUTTON_EDGE, relief="raised")
    s.map("TButton", background=[("pressed", "#d8c29e"), ("active", SELECT), ("disabled", BG)],
          foreground=[("disabled", "#b4a796")], bordercolor=[("active", ACCENT), ("disabled", LINE)])
    s.configure("Accent.TButton", background=ACCENT, foreground="white", bordercolor=ACCENT_DARK)
    s.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", "#cdb79c")],
          foreground=[("disabled", "#f3eadc")])
    s.configure("Small.TButton", padding=(6, 1), font=FONT_SMALL)
    s.configure("Tool.TButton", padding=(6, 2))
    s.configure("Danger.TButton", foreground=DANGER)
    for w in ("TCheckbutton", "TRadiobutton"):         # (the tick boxes: a clear box, an amber tick)
        s.configure(w, background=PANEL, indicatorbackground=FIELD, indicatorforeground=ACCENT_DARK,
                    upperbordercolor=BUTTON_EDGE, lowerbordercolor=BUTTON_EDGE, indicatormargin=(0, 1, 5, 1),
                    indicatorsize=px(13))
        s.map(w, indicatorbackground=[("disabled", BG), ("pressed", SELECT), ("active", "#fff4de")],
              upperbordercolor=[("active", ACCENT)], lowerbordercolor=[("active", ACCENT)],
              background=[("active", PANEL)])
    s.configure("BG.TCheckbutton", background=BG)
    s.configure("Seg.TRadiobutton", background=PANEL, padding=(8, 3), indicatorrelief="flat")
    s.configure("TEntry", padding=3)
    s.configure("TCombobox", padding=2)
    s.configure("TSpinbox", padding=2)
    s.configure("TNotebook", background=PANEL, borderwidth=0)
    s.configure("TNotebook.Tab", padding=(10, 4), background=BG)
    s.map("TNotebook.Tab", background=[("selected", PANEL)])
    s.configure("TLabelframe", background=PANEL, bordercolor=LINE)
    s.configure("TLabelframe.Label", background=PANEL, foreground=ACCENT_DARK, font=FONT_BOLD)
    s.configure("Treeview", background=FIELD, fieldbackground=FIELD, rowheight=px(22), bordercolor=LINE)
    s.configure("Treeview.Heading", background=PANEL, font=FONT_BOLD, relief="flat")
    s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    s.configure("Icons.Treeview", rowheight=px(36))
    s.configure("TPanedwindow", background=BG)
    s.configure("Sash", sashthickness=6, gripcount=0)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", FONT)
    return s
