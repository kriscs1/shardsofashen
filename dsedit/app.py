"""The Dragon Sword Editor: one window for the whole game. A rail of sections on the left (Maps, Scripts, Tiles,
Entities, Item Racks, Spells, Quests, Buildables, Crops, Minimaps), the section on the right, and everything linked: a
trigger opens its script, a placed entity its Entities page, an item in a rack its entity, "Used in" lists jump to the
place. Ctrl+K: go to anything. Ctrl+S save, Ctrl+Z / Ctrl+Y undo / redo (in the section you're in).
F5: play what you've made, in the browser (a local server started from these files)."""
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from tkinter import ttk, messagebox

from . import theme as T
from .project import Project
from .widgets import FilterList, Dialog


class Page(ttk.Frame):
    """A section of the editor."""
    title = "?"
    icon = "•"
    kind = "?"                 # the key used by app.goto()

    def __init__(self, app):
        super().__init__(app.content, style="TFrame")
        self.app, self.project = app, app.project
        self.undo_stack, self.redo_stack = [], []

    # --- what the app asks of a section
    def is_dirty(self):
        return False

    def save(self):
        return True

    def discard(self):
        pass

    def current(self):
        """What's open, for the header."""
        return ""

    def open(self, key, **kw):
        pass

    def search_items(self):
        """[(key, label)] for Ctrl+K."""
        return []

    def on_show(self):
        pass

    # --- undo: snapshot() before a change, push it; restore() to go back
    def snapshot(self):
        return None

    def restore(self, snap):
        pass

    def remember(self):
        """Call before changing anything: the state now goes on the undo stack."""
        snap = self.snapshot()
        if snap is None:
            return
        if self.undo_stack and self.undo_stack[-1] == snap:
            return
        self.undo_stack.append(snap)
        del self.undo_stack[:-100]
        self.redo_stack.clear()
        self.app.refresh_chrome()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.snapshot())
        self.restore(self.undo_stack.pop())
        self.app.refresh_chrome()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.snapshot())
        self.restore(self.redo_stack.pop())
        self.app.refresh_chrome()

    def clear_history(self):
        self.undo_stack, self.redo_stack = [], []

    def leave_ok(self, what=None):
        """Before something else is opened in this section: save or drop unsaved changes (False = stay)."""
        if not self.is_dirty():
            return True
        from .widgets import ask_save
        r = ask_save(self, what or self.current() or self.title)
        if r is None:
            return False
        if r == "save":
            return bool(self.save())
        self.discard()
        return True


class QuickOpen(Dialog):
    """Ctrl+K: every map, script, tile, entity, rack, spell and quest; type to filter, Enter to go."""

    def __init__(self, app):
        super().__init__(app.root, "Go to anything", ok="Go")
        self.app = app
        items = []
        for page in app.pages:
            for key, label in page.search_items():
                items.append(("%s\x1f%s" % (page.kind, key), "%s   ·  %s" % (label, page.title), page.title))
        self.list = FilterList(self.body, lambda k: None, kinds=[p.title for p in app.pages], height=18,
                               placeholder="Type part of a name")
        self.list.pack(fill="both", expand=True)
        self.list.set_items(items)
        self.list.tree.bind("<Double-1>", lambda e: self._ok())
        self.list.tree.bind("<Return>", lambda e: self._ok())
        self.list.search_entry.bind("<Return>", lambda e: self._ok())
        self.list.search_entry.bind("<Down>", lambda e: (self.list.tree.focus_set(), self.list.step(1)))
        self.after(50, self.list.search_entry.focus_set)
        self.geometry("%dx%d" % (T.px(580), T.px(580)))

    def ok(self):
        k = self.list.selected() or (self.list.shown[0] if self.list.shown else None)
        if not k:
            return False
        kind, key = k.split("\x1f", 1)
        self.after_idle(lambda: self.app.goto(kind, key))
        return True


class App:
    def __init__(self, root_dir):
        try:            # Windows: draw at the screen's real pixels (sharp text), not stretched by display scaling
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Dragon Sword Editor")
        T.setup(self.root)
        self.project = Project(root_dir)
        self.root.geometry("1440x900")
        self.root.minsize(1100, 700)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.page, self.pages, self.rail_items = None, [], {}
        self.build_chrome()
        from .pages import all_pages
        for cls in all_pages():
            self.pages.append(cls(self))
        for i, pg in enumerate(self.pages):
            self.add_rail_item(pg, i)
        self.add_rail_footer()
        self.bind_keys()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.show(self.pages[0])
        self.root.deiconify()
        self.root.after(600, self.watch)

    # --- the window
    def build_chrome(self):
        r = self.root
        self.rail = tk.Frame(r, bg=T.RAIL, width=T.px(200))
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)
        tk.Label(self.rail, text="⚔  Dragon Sword", bg=T.RAIL, fg="#f2c46d", font=("Segoe UI Semibold", 14),
                 anchor="w", padx=16).pack(fill="x", pady=(18, 0))
        tk.Label(self.rail, text="EDITOR", bg=T.RAIL, fg="#9c8a74", font=("Segoe UI", 8, "bold"), anchor="w",
                 padx=18).pack(fill="x", pady=(0, 16))
        self.rail_list = tk.Frame(self.rail, bg=T.RAIL)
        self.rail_list.pack(fill="x")
        main = ttk.Frame(r)
        main.pack(side="left", fill="both", expand=True)
        head = ttk.Frame(main, padding=(18, 12, 18, 8))
        head.pack(fill="x")
        self.head_title = ttk.Label(head, text="", style="Title.TLabel")
        self.head_title.pack(side="left")
        self.head_item = ttk.Label(head, text="", style="HeadBG.TLabel", foreground=T.MUTED)
        self.head_item.pack(side="left", padx=(12, 0), pady=(4, 0))
        self.save_btn = ttk.Button(head, text="Save", style="Accent.TButton", command=self.save_current)
        self.save_btn.pack(side="right")
        self.redo_btn = ttk.Button(head, text="Redo ↷", command=lambda: self.page and self.page.redo())
        self.redo_btn.pack(side="right", padx=(0, 6))
        self.undo_btn = ttk.Button(head, text="↶ Undo", command=lambda: self.page and self.page.undo())
        self.undo_btn.pack(side="right", padx=(0, 4))
        ttk.Button(head, text="Go to…  Ctrl+K", command=self.quick_open).pack(side="right", padx=(0, 18))
        ttk.Separator(main).pack(fill="x")
        self.content = ttk.Frame(main, padding=(14, 10, 14, 4))
        self.content.pack(fill="both", expand=True)
        bar = tk.Frame(main, bg="#e3d8c5", height=26)
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = tk.Label(bar, textvariable=self.status_var, bg="#e3d8c5", fg=T.TEXT, anchor="w",
                                     font=T.FONT_SMALL, padx=12)
        self.status_label.pack(side="left", fill="x", expand=True)
        self.info_var = tk.StringVar()
        tk.Label(bar, textvariable=self.info_var, bg="#e3d8c5", fg=T.MUTED, font=T.FONT_SMALL, padx=12).pack(side="right")

    def add_rail_item(self, page, i):
        f = tk.Frame(self.rail_list, bg=T.RAIL, cursor="hand2")
        f.pack(fill="x")
        icon = tk.Label(f, text=page.icon, bg=T.RAIL, fg="#d9a75a", font=("Segoe UI Symbol", 13), width=3)
        icon.pack(side="left", padx=(10, 0), pady=7)
        lab = tk.Label(f, text=page.title, bg=T.RAIL, fg=T.RAIL_TEXT, font=("Segoe UI", 11), anchor="w")
        lab.pack(side="left", fill="x", expand=True)
        dot = tk.Label(f, text="", bg=T.RAIL, fg="#f2c46d", font=("Segoe UI", 11))
        dot.pack(side="right", padx=12)
        key = tk.Label(f, text="Ctrl+%d" % (i + 1), bg=T.RAIL, fg="#6f5f4e", font=("Segoe UI", 7))
        key.pack(side="right")
        widgets = (f, icon, lab, dot, key)
        for w in widgets:
            w.bind("<Button-1>", lambda e, p=page: self.show(p))
            w.bind("<Enter>", lambda e, p=page: self.rail_hover(p, True))
            w.bind("<Leave>", lambda e, p=page: self.rail_hover(p, False))
        self.rail_items[page] = (widgets, dot)

    def add_rail_footer(self):
        foot = tk.Frame(self.rail, bg=T.RAIL)
        foot.pack(side="bottom", fill="x", pady=14)
        for text, cmd in (("▶  Play in the browser   F5", self.play), ("⌕  Go to anything   Ctrl+K", self.quick_open)):
            l = tk.Label(foot, text=text, bg=T.RAIL, fg="#c9b89f", font=("Segoe UI", 9), anchor="w", padx=18,
                         cursor="hand2")
            l.pack(fill="x", pady=2)
            l.bind("<Button-1>", lambda e, c=cmd: c())

    def rail_hover(self, page, on):
        widgets, _ = self.rail_items[page]
        bg = T.RAIL_SEL if page is self.page else (T.RAIL_HOT if on else T.RAIL)
        for w in widgets:
            w.configure(bg=bg)

    def refresh_chrome(self):
        for pg, (widgets, dot) in self.rail_items.items():
            bg = T.RAIL_SEL if pg is self.page else T.RAIL
            for w in widgets:
                w.configure(bg=bg)
            dot.configure(text="●" if pg.is_dirty() else "")
        p = self.page
        if p is None:
            return
        self.head_title.configure(text=p.title)
        cur = p.current()
        self.head_item.configure(text=("›  " + cur) if cur else "")
        self.save_btn.configure(text="Save ●" if p.is_dirty() else "Save",
                                state="normal" if p.is_dirty() else "disabled")
        self.undo_btn.configure(state="normal" if p.undo_stack else "disabled")
        self.redo_btn.configure(state="normal" if p.redo_stack else "disabled")

    # --- moving about
    def show(self, page):
        if self.page is page:
            return
        if self.page is not None:
            self.page.pack_forget()
        self.page = page
        page.pack(fill="both", expand=True)
        page.on_show()
        self.refresh_chrome()

    def page_of(self, kind):
        return next(p for p in self.pages if p.kind == kind)

    def goto(self, kind, key, **kw):
        """Opens key in the section kind (map, script, tile, entity, rack, spell, quest, buildable, crop, minimap, or
        place: a named place's map, at its tile)."""
        if kind == "place":
            pl = self.project.places().get(key.upper())
            if pl is None:
                self.status("There's no place called %s (an Id on a map tile, or a thing's Id=)." % key, "warn")
                return
            kind, key, kw = "map", pl[1], dict(kw, tile=(pl[2], pl[3]))
        page = self.page_of(kind)
        self.show(page)
        page.open(key, **kw)
        self.refresh_chrome()

    def quick_open(self):
        QuickOpen(self).run()

    def status(self, text, kind="info"):
        colours = {"info": T.TEXT, "ok": T.OK, "warn": T.WARN, "error": T.DANGER}
        self.status_var.set(text)
        self.status_label.configure(fg=colours.get(kind, T.TEXT))

    def info(self, text):
        self.info_var.set(text)

    def save_current(self):
        if self.page and self.page.is_dirty():
            if self.page.save():
                self.status("Saved %s." % (self.page.current() or self.page.title), "ok")
        self.refresh_chrome()

    PLAY_PORT = 8080
    play_news = queue.Queue()

    def play(self):
        """F5: the game as it is in these files, in the browser. The pictures are made again (only what changed), the
        local server (in a window of its own) is started, or restarted to read the changes, and the game opens.
        Its players and world are kept in server-data\ (not the real server's)."""
        if getattr(self, "_playing", False):
            return
        for p in self.pages:
            if p.is_dirty():
                p.save()
        self._playing = True
        self.status("Getting the game ready: making the pictures...", "info")
        threading.Thread(target=self._play_thread, daemon=True).start()

    def _play_thread(self):
        root = self.project.root
        url = "http://localhost:%d/" % self.PLAY_PORT
        say = lambda text, kind="info": self.play_news.put((text, kind))       # (shown by watch(), in Tk's thread)
        try:
            r = subprocess.run([sys.executable, os.path.join(root, "tools", "export_web_assets.py")], cwd=root,
                               capture_output=True, text=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode != 0:
                say("Making the pictures failed: %s" % (r.stderr.strip().splitlines() or ["?"])[-1], "error")
                return
            proc = getattr(self, "_server", None)
            if proc is not None and proc.poll() is None:
                say("Restarting the local server...")
                proc.terminate()
                proc.wait(10)
            elif self._server_up(url):
                say("A server is already running at %s (not one F5 started): opened it. Restart it to see changes."
                    % url, "warn")
                webbrowser.open(url)
                return
            env = dict(os.environ, DS_PORT=str(self.PLAY_PORT))
            self._server = subprocess.Popen([sys.executable, "-m", "server"], cwd=root, env=env,
                                            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
            for _ in range(60):
                if self._server.poll() is not None:
                    say("The local server stopped: look at its window for why.", "error")
                    return
                if self._server_up(url):
                    break
                time.sleep(0.5)
            webbrowser.open(url)
            say("Playing at %s (the server runs in its own window; F5 again restarts it with your changes)." % url,
                "ok")
        except Exception as e:      # (anything at all: the editor carries on)
            say("Couldn't start the game: %s" % e, "error")
        finally:
            self._playing = False

    @staticmethod
    def _server_up(url):
        try:
            with urllib.request.urlopen(url + "health", timeout=1) as r:
                return r.status == 200
        except Exception:
            return False

    def bind_keys(self):
        r = self.root

        def in_text():
            w = r.focus_get()
            return isinstance(w, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox, ttk.Spinbox))
        r.bind_all("<Control-s>", lambda e: (self.save_current(), "break")[1])
        r.bind_all("<Control-k>", lambda e: (self.quick_open(), "break")[1])
        r.bind_all("<Control-z>", lambda e: None if in_text() else (self.page.undo(), "break")[1])
        r.bind_all("<Control-y>", lambda e: None if in_text() else (self.page.redo(), "break")[1])
        r.bind_all("<F5>", lambda e: self.play())
        for i in range(min(9, len(self.pages))):              # (Ctrl+1..9: the first nine sections)
            r.bind_all("<Control-Key-%d>" % (i + 1), lambda e, i=i: self.show(self.pages[i]))

    def watch(self):
        """Every so often: the dots and buttons, and files changed by something else (a rebuild)."""
        try:
            while not self.play_news.empty():
                self.status(*self.play_news.get_nowait())
            self.refresh_chrome()
        finally:
            self.root.after(800, self.watch)

    def quit(self):
        dirty = [p for p in self.pages if p.is_dirty()]
        if dirty:
            names = ", ".join("%s (%s)" % (p.title, p.current()) for p in dirty)
            r = messagebox.askyesnocancel("Unsaved changes", "Save your changes before closing?\n\n" + names,
                                          parent=self.root)
            if r is None:
                return
            if r:
                for p in dirty:
                    if not p.save():
                        self.show(p)
                        return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    App(root).run()
