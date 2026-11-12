"""The desktop app (Windows, macOS, Linux): the same start screen as the Android app (web/home/), and the same choices:
play alone, host a game (local: answered on this network; remote: announced to the central server), or join one
(local: the games on this network, or by address; remote: the central server's list). The game itself is the same page
as everywhere, in the app's own window. Hosting runs the game's server here, as the Android app does (ds_host.py).

  python desktop/app.py              (pip install pywebview aiohttp; desktop/build_desktop.py makes the program)
"""
import json
import os
import platform
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
# (the game's folder: beside this file when run from the source; inside the program when built by PyInstaller)
ROOT = getattr(sys, "_MEIPASS", os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "android", "app", "src", "main", "python"))

PORT = int(os.environ.get("DS_DESKTOP_PORT", "8484"))
GAME_KEYS = ("carried",)    # (all a game's page may keep or read here: a character on its way to this device)
MODES = ("solo", "local", "remote")


def data_dir():
    """Where this computer keeps the app's worlds and settings."""
    if os.environ.get("DS_DESKTOP_DATA"):
        base = os.environ["DS_DESKTOP_DATA"]
    elif os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(base, "ShardsOfAshen")
    os.makedirs(path, exist_ok=True)
    return path


def addresses():
    """This computer's addresses on its networks (for others to join a game it hosts)."""
    out = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))           # (no packet is sent: it only picks the way out)
            out.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            out.add(info[4][0])
    except OSError:
        pass
    return sorted(a for a in out if not a.startswith("127."))


class Host:
    """The game hosted here (or played alone): its server in a thread of its own, as the Android app's HostService."""

    def __init__(self):
        self.status, self.error, self.name, self.mode = "off", "", "", "solo"

    def start(self, name, mode, central, host_key=""):
        if self.status not in ("off", "error"):
            return
        self.mode = mode if mode in MODES else "local"
        self.name = name or "Shards of Ashen on " + platform.node()
        self.status, self.error = "starting", ""

        def run():
            try:
                import ds_host
                ds_host.start(ROOT, os.path.join(data_dir(), "solo.db"), self.name, PORT, version(), central, host_key)
                self.status = "on"
            except Exception as e:                      # (the port's taken, the files are missing...)
                self.error, self.status = str(e), "error"
        threading.Thread(target=run, name="host", daemon=True).start()

    def stop(self):
        if self.status != "on":
            return
        self.status = "stopping"

        def run():
            import ds_host
            ds_host.stop()
            self.status = "off"
        threading.Thread(target=run, name="unhost", daemon=True).start()


def version():
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "-"


class Prefs:
    def __init__(self):
        self.path = os.path.join(data_dir(), "settings.json")
        try:
            with open(self.path, encoding="utf-8") as f:
                self.values = json.load(f)
        except (OSError, ValueError):
            self.values = {}

    def get(self, key):
        return self.values.get(str(key), "")

    def set(self, key, value):
        self.values[str(key)] = str(value)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.values, f)


class Bridge:
    """What the start screen and the game page may ask of the app (window.pywebview.api.<name>)."""

    def __init__(self, owning=None):                      # (private: pywebview hands the page every public attribute)
        from owning import Owning
        self._host = Host()
        self._prefs = Prefs()
        self._owning = owning or Owning(ROOT)
        self._window = None

    def _home(self):
        """Is the start screen what's showing (not a game's page, a remote server's or a friend's relayed one)? Only
        it may ask what the app knows (the Steam ticket, the sign-in) or have it host, play or open links."""
        w = self._window
        url = (w.get_current_url() or "") if w is not None else ""
        return not url.startswith(("http://", "https://"))

    def state(self):
        if not self._home():
            return "{}"
        # (full: the PC build's owned, or None while Steam's asked; no demo on a PC: owning.py)
        return json.dumps({"status": self._host.status, "error": self._host.error, "name": self._host.name,
                           "mode": self._host.mode, "port": PORT, "addresses": addresses(), "device": platform.node(),
                           "version": version(), **self._owning.state()})

    def hostAs(self, name, mode, central, host_key=""):   # noqa: N802 (the start screen's names, as Android's)
        if self._home():
            self._host.start(str(name or "").strip(), str(mode or "local"), str(central or ""), str(host_key or ""))

    def stopHosting(self):                                # noqa: N802
        if self._home():
            self._host.stop()

    def find(self):
        if not self._home():
            return []
        from server import lan
        mine = set(addresses())
        out, seen = [], set()
        for addr, answer in lan.find(1.5):
            here = addr.startswith("127.") or addr in mine
            key = ("here" if here else addr, answer.get("port"))
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(answer, address="127.0.0.1" if here else addr, here=here))
        return out

    def play(self, url):
        if self._home():
            self._window.load_url(str(url))

    def openLink(self, url):                              # noqa: N802
        """Out to the PC's own browser (Google won't sign in inside an app's window)."""
        url = str(url)
        if self._home() and url.startswith(("https://", "http://")):
            import webbrowser
            webbrowser.open(url)

    def get(self, key):
        return self._prefs.get(key) if self._home() or key in GAME_KEYS else ""

    def goHome(self):                                     # noqa: N802
        self._window.load_html(home_page(self))

    def set(self, key, value):
        if self._home() or key in GAME_KEYS:
            self._prefs.set(key, value)

    def fullscreen(self):
        """The window full screen, or back (F11 or the game's button: a page's own full screen fills only the window)."""
        self._window.toggle_fullscreen()


SHIM = """<script>
// (the desktop app, as the start screen and the game page know an app: window.DSApp, answering at once - pywebview's
//  own answers come later, so the state is kept up to date here, and what's set is kept here too)
(function () {
  const prefs = %s;
  let state = %s;
  const later = (fn) => { if (window.pywebview && window.pywebview.api) fn(window.pywebview.api);
                          else window.addEventListener("pywebviewready", () => fn(window.pywebview.api)); };
  later((api) => setInterval(() => api.state().then((s) => { state = s; }), 500));
  window.DSApp = {
    kind: () => "desktop",
    state: () => state,
    fullGame: () => { try { return JSON.parse(state).full; } catch (e) { return null; } },   // (owning.py)
    steamTicket: () => { try { return JSON.parse(state).steam_ticket || ""; } catch (e) { return ""; } },
    pcStore: () => { try { return JSON.parse(state).store || ""; } catch (e) { return ""; } },
    notOwned: () => { try { return JSON.parse(state).why || ""; } catch (e) { return ""; } },
    get: (k) => prefs[k] || "",
    set: (k, v) => { prefs[k] = String(v); later((api) => api.set(k, String(v))); },
    hostAs: (name, mode, central, key) => later((api) => api.hostAs(name, mode, central, key || "")),
    host: (name) => later((api) => api.hostAs(name, "local", "")),
    playAlone: () => later((api) => api.hostAs("", "solo", "")),
    stopHosting: () => later((api) => api.stopHosting()),
    find: () => later((api) => api.find().then((g) => window.onGames && window.onGames(g))),
    play: (url) => later((api) => api.play(url)),
    openLink: (url) => later((api) => api.openLink(url)),
    goHome: () => later((api) => api.goHome()),
    fullscreen: () => later((api) => api.fullscreen()),
  };
})();
</script>"""

GAME_SHIM = """(function () {
  // (the game page in the desktop app: Quit takes you back to the start screen - main.js listens for "dsapp")
  window.DSApp = window.DSApp || { kind: () => "desktop", goHome: () => window.pywebview.api.goHome(),
    get: (k) => window.pywebview.api.get(k), set: (k, v) => window.pywebview.api.set(k, v),
    fullscreen: () => window.pywebview.api.fullscreen() };
  window.dispatchEvent(new Event("dsapp"));
})();"""


def home_page(bridge):
    """The start screen, with the app (SHIM) and its settings (config.js) written into it."""
    with open(os.path.join(ROOT, "web", "home", "index.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(ROOT, "web", "home", "config.js"), encoding="utf-8") as f:
        config = f.read()
    shim = SHIM % (json.dumps(bridge._prefs.values), json.dumps(bridge.state()))
    page = page.replace('<script src="config.js"></script>', "<script>%s</script>%s" % (config, shim), 1)
    import base64
    for pic, kind in (("logo.png", "image/png"), ("bg.jpg", "image/jpeg"), ("favicon.png", "image/png")):    # (no folder behind the page: in it)
        with open(os.path.join(ROOT, "web", "home", pic), "rb") as f:
            data = "data:%s;base64,%s" % (kind, base64.b64encode(f.read()).decode())
        page = page.replace('src="%s"' % pic, 'src="%s"' % data).replace("url(%s)" % pic, "url(%s)" % data)
        page = page.replace('href="%s"' % pic, 'href="%s"' % data)
    return page


def main():
    import webview
    bridge = Bridge()
    if bridge._owning.ask() == "restart":               # (the Steam build, started outside Steam: Steam starts it)
        return
    threading.Thread(target=bridge._owning.ticket_later, name="steam-ticket", daemon=True).start()
    window = webview.create_window("Shards of Ashen", html=home_page(bridge), js_api=bridge, width=1280, height=800,
                                   min_size=(800, 560))
    bridge._window = window

    def loaded():
        url = window.get_current_url() or ""
        if url.startswith("http"):                      # (a game: its Quit comes back here)
            window.evaluate_js(GAME_SHIM)

    window.events.loaded += loaded
    window.events.closing += lambda: bridge._host.stop()
    webview.start()


if __name__ == "__main__":
    main()
