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
        self.status, self.error, self.name, self.mode = "off", "", "", "local"

    def start(self, name, mode, central):
        if self.status not in ("off", "error"):
            return
        self.mode = mode if mode in ("solo", "local", "remote") else "local"
        self.name = "Your own game" if self.mode == "solo" else (name or "Shards of Ashen on " + platform.node())
        self.status, self.error = "starting", ""

        def run():
            try:
                import ds_host
                db = os.path.join(data_dir(), "solo.db" if self.mode == "solo" else "world.db")
                ds_host.start(ROOT, db, self.name, PORT, version(), self.mode == "solo", self.mode, central)
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

    def set(self, key, value):
        self.values[str(key)] = str(value)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.values, f)


class Bridge:
    """What the start screen and the game page may ask of the app (window.pywebview.api.<name>)."""

    def __init__(self):
        self.host = Host()
        self.prefs = Prefs()
        self.window = None

    def state(self):
        return json.dumps({"status": self.host.status, "error": self.host.error, "name": self.host.name,
                           "mode": self.host.mode, "port": PORT, "addresses": addresses(), "device": platform.node(),
                           "version": version()})

    def hostAs(self, name, mode, central):                # noqa: N802 (the start screen's names, as Android's)
        self.host.start(str(name or "").strip(), str(mode or "local"), str(central or ""))

    def stopHosting(self):                                # noqa: N802
        self.host.stop()

    def find(self):
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
        self.window.load_url(str(url))

    def goHome(self):                                     # noqa: N802
        self.window.load_html(home_page(self))

    def set(self, key, value):
        self.prefs.set(key, value)


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
    get: (k) => prefs[k] || "",
    set: (k, v) => { prefs[k] = String(v); later((api) => api.set(k, String(v))); },
    hostAs: (name, mode, central) => later((api) => api.hostAs(name, mode, central)),
    host: (name) => later((api) => api.hostAs(name, "local", "")),
    playAlone: () => later((api) => api.hostAs("", "solo", "")),
    stopHosting: () => later((api) => api.stopHosting()),
    find: () => later((api) => api.find().then((g) => window.onGames && window.onGames(g))),
    play: (url) => later((api) => api.play(url)),
    goHome: () => later((api) => api.goHome()),
  };
})();
</script>"""

GAME_SHIM = """(function () {
  // (the game page in the desktop app: Quit takes you back to the start screen - main.js listens for "dsapp")
  window.DSApp = window.DSApp || { kind: () => "desktop", goHome: () => window.pywebview.api.goHome() };
  window.dispatchEvent(new Event("dsapp"));
})();"""


def home_page(bridge):
    """The start screen, with the app (SHIM) and its settings (config.js) written into it."""
    with open(os.path.join(ROOT, "web", "home", "index.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(ROOT, "web", "home", "config.js"), encoding="utf-8") as f:
        config = f.read()
    shim = SHIM % (json.dumps(bridge.prefs.values), json.dumps(bridge.state()))
    page = page.replace('<script src="config.js"></script>', "<script>%s</script>%s" % (config, shim), 1)
    import base64
    for pic, kind in (("logo.png", "image/png"), ("bg.jpg", "image/jpeg")):    # (no folder behind the page: in it)
        with open(os.path.join(ROOT, "web", "home", pic), "rb") as f:
            data = "data:%s;base64,%s" % (kind, base64.b64encode(f.read()).decode())
        page = page.replace('src="%s"' % pic, 'src="%s"' % data).replace("url(%s)" % pic, "url(%s)" % data)
    return page


def main():
    import webview
    bridge = Bridge()
    window = webview.create_window("Shards of Ashen", html=home_page(bridge), js_api=bridge, width=1280, height=800,
                                   min_size=(800, 560))
    bridge.window = window

    def loaded():
        url = window.get_current_url() or ""
        if url.startswith("http"):                      # (a game: its Quit comes back here)
            window.evaluate_js(GAME_SHIM)

    window.events.loaded += loaded
    window.events.closing += lambda: bridge.host.stop()
    webview.start()


if __name__ == "__main__":
    main()
