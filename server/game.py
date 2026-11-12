"""The game server: one shared World, up to MAX_PLAYERS players connected over WebSockets, the world ticking 20 times
a second, and everything saved to the database (every minute, when someone leaves, and when the server stops)."""
import asyncio
import collections
import hashlib
import hmac
import ipaddress
import gzip
import json
import logging
import os
import platform
import socket
import sqlite3
import time

from aiohttp import web, WSMsgType

from ashen.lb import local_offset
from dsengine import World, Session
from dsengine.view import snapshot

from . import auth
from .store import Store

log = logging.getLogger("ashen.server")

TICK = 0.05
SAVE_EVERY = 60
SAVE_SOON = 1.0             # (seconds: the soonest everyone is saved again when something's changed hands)
SAVE_RETRY = 10             # (seconds: a save that failed is tried again so soon, whatever was asked)
SIGN_IN_SECONDS = 30        # (a friend's connection through the relay that hasn't signed in by then: closed)
PASS_RETRY, PASS_TRIES = 60, 5  # (a time pass run out, the central server not answering: asked again so often, so many times)
WHERE_EVERY = 1.0           # (seconds between the minimap's dots for the other players)
LINGER = 30                 # (seconds a player marked in open PvP stays in the world once they've gone: pvp.py)
CHAT_MAX = 200
CHAT_LINES, CHAT_SECONDS = 6, 5.0   # (the most lines anyone can say in those seconds: no flooding everyone's chat)
TALKING = ("/p ", "/party ", "/r ", "/reply ", "/w ", "/whisper ", "/tell ", "/msg ", "/letter ")  # (commands that talk)


BACKLOG = 100           # messages a connection may fall behind (5 s of ticks) before it's let go: a slow one
UNNAMED = "A Shards of Ashen server"    # (a remote server nobody's named: DS_NAME, or Options)
MOST_CHARACTERS = 5     # (an account's, or a device's, on one server)
LOG_LINES = 2000        # (the log's last lines kept in memory: Options' Send log)
LOG_SENT = 150000       # (characters of it that go: the end, if there's more)
LOG_CLIENT = 60000      # (characters of the player's own side that go with it: what the page saw, its end)
LOG_EVERY = 3600        # (seconds between logs sent from one server: the central server holds to it too)


class RecentLog(logging.Handler):
    """The log's last lines, kept in memory as they're written: what the host or an admin sends to support (Options'
    Send log), shown to them first."""

    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = collections.deque(maxlen=LOG_LINES)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    def emit(self, record):
        if record.name.startswith("aiohttp.access"):   # (a line for every picture fetched: no help to anyone)
            return
        if record.name == "asyncio" and record.exc_info and isinstance(record.exc_info[1], ConnectionResetError):
            return                                      # (Windows, when a browser goes: asyncio's noise, nothing wrong)
        try:
            self.lines.append(self.format(record))
        except Exception:                               # (a line that won't format is no reason to stop)
            pass

    def text(self):
        text = "\n".join(self.lines)
        if len(text) > LOG_SENT:                        # (its end, from a whole line)
            text = text[-LOG_SENT:].partition("\n")[2]
        return text


RECENT_LOG = RecentLog()


def shift_due(entry, seconds):
    """An action queue entry with its due time (the last field) moved by seconds."""
    parts = entry.split("\t")
    try:
        parts[-1] = str(int(float(parts[-1]) + seconds))
    except ValueError:
        pass
    return "\t".join(parts)


class Client:
    """One browser connection. What's sent to it waits in its own queue, written out in order by its own task, so a
    slow connection holds up only itself - never the world's tick."""

    def __init__(self, ws, addr):
        self.ws = ws
        self.addr = addr
        self.session = None
        self.owner = None           # (who's playing, once they've said: "a:<Hallisium account>" or "d:<device>")
        self.account = ""           # (their Hallisium account's name, if they came in by one)
        self.host = False           # (the host, by the key its app started the server with)
        self.grant = ""             # (the central server's key to their friends, from their ticket)
        self.friends_got = None     # (their friends, as the ticket's check said)
        self.full = True            # (the full game, or the demo: Game.full_of)
        self.pass_until = 0         # (a time pass's end, when that's all it is: asked again then)
        self.device_full = False    # (the host's app says it's bought on the device)
        self.msg_times = []
        self.log_shown = ""         # (the log as it was shown to them: what Send sends)
        self.closed = False
        self.queue = asyncio.Queue()
        self.writer = None

    async def write(self):
        try:
            while True:
                msg = await self.queue.get()
                try:
                    if not self.closed:
                        await self.ws.send_str(msg)     # (made into JSON already, as it was queued: send)
                except (ConnectionResetError, RuntimeError):
                    self.closed = True
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            pass

    async def flush(self, seconds=1.0):
        """Wait (a moment at most) for what's queued to go: before closing it, say why."""
        try:
            await asyncio.wait_for(self.queue.join(), seconds)
        except asyncio.TimeoutError:
            pass


class GameServer:
    def __init__(self, root, db_path, max_players=5, registration="open", invite_code="", backup_dir=None, admins=""):
        self.root = root
        # (DS_ADMINS: the Hallisium accounts the server's owner gives the Admin button, besides the characters
        # tools/admin.py made admin)
        self.admins = {a.strip().lower() for a in str(admins or "").split(",") if a.strip()}
        from .version import version_info
        self.version = version_info(root)
        if RECENT_LOG not in logging.getLogger().handlers:
            logging.getLogger().addHandler(RECENT_LOG)  # (from now on: Options' Send log)
        self.assets_seen = (None, "")                   # (web/assets' manifest: when it was written, its version)
        self.code_seen = None                           # (the page's own code: its version, worked out once)
        self.store = Store(db_path)
        self.max_players = max_players
        self.registration = registration
        self.invite_code = invite_code
        self.central_http = None        # (the one connection to the central server: central_post)
        self.central_away = False       # (it didn't answer last time: said once in the log)
        self.network_changed = self.internet_changed = None     # (make_app's: what opening it means to the machine)
        self.host_grant = self.store.setting("host_grant", "")     # (the host's key to the central server: relay.py)
        self.host_account = self.store.setting("host_account", "")
        try:
            self.host_friends = json.loads(self.store.setting("host_friends", "[]"))
        except ValueError:
            self.host_friends = []
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")
        t0 = time.time()
        self.world = World(root)
        self.world.central_friend = self.central_friend     # (friends by account: together.py asks)
        self.world.open_pvp = self.pvp_open()
        self.load_world()
        self.world.data.places()                        # (read now, not on the first player's login: they'd wait)
        self.world.data.quest_table()
        log.info("World ready: %d maps, %d things (%.1fs)", len(self.world.maps), len(self.world.ents),
                 time.time() - t0)
        self.clients = {}                   # Session -> Client
        self.signups = {}                   # address -> the days it made characters on (DS_REGISTER_PER_DAY)
        self.conns = {}                     # address -> how many connections it has open (DS_CONNECTIONS_PER_ADDRESS)
        self.turned_away = set()            # (addresses at their limit, told of in the log once)
        self.running = False
        self.last_save = time.time()
        self.unsaved = {}                   # name -> the save of one who left when saving failed (save_all)
        self.tick_failed = set()            # (the tick's parts that have gone wrong: logged once)
        self.last_where = 0.0
        self.last_where_sent = None     # (the minimap's dots as last sent: again only when they move)
        self.last_backup_day = None
        self.tick_ms = 0.0
        self.up_since = time.time()

    # =================================================================================================================
    # Saving
    # =================================================================================================================
    def load_world(self):
        st = self.store.load_world()
        w = self.world
        if not st:
            return
        from dsengine.renames import renamed
        st = renamed(st)                                # (items renamed since it was saved: their new names)
        if st.get("clock") != "utc":                    # (saved by local time, before: put on UTC as the clock is now)
            shift = local_offset()
            st["queue"] = [shift_due(e, -shift) for e in st.get("queue", []) if isinstance(e, str)]
            st["farms"] = [row[:5] + [float(row[5]) - shift] for row in st.get("farms") or []
                           if isinstance(row, list) and len(row) == 6]
        w.homes.load(st.get("homes"))
        w.farms.load(st.get("farms"))
        w.market.load(st.get("market"), old_stalls=st.get("stalls"))
        w.wonders.load(st.get("wonders"))
        w.together.load(st.get("together"))            # (projects, records, guestbooks, gifts: together.py)
        w.action_queue = [e for e in st.get("queue", []) if isinstance(e, str)]
        w.apply_saved_queue()
        if "day" in st:
            w.set_day_fraction(float(st["day"]))
        wt = st.get("weather")
        if wt:
            w.weather = {"kind": wt.get("kind", "clear"), "level": float(wt.get("level", 0)),
                         "next": w.now + int(wt.get("left", 60000)), "fading": bool(wt.get("fading"))}

    def world_state(self):
        w = self.world
        wt = None
        if w.weather:
            wt = {"kind": w.weather["kind"], "level": w.weather["level"], "fading": w.weather["fading"],
                  "left": max(0, w.weather["next"] - w.now)}
        return {"clock": "utc", "queue": list(w.action_queue), "day": w.day_fraction(), "weather": wt, "homes": w.homes.state(), "farms": w.farms.state(), "market": w.market.state(),
                "together": w.together.state(), "wonders": w.wonders.state()}

    def save_all(self, also=None):
        """Everyone in the world, and the world, in one go: what's changed hands between them (a trade, a gift, the
        market) is never saved in two places, or in none, whenever the server stops. also: one leaving, saved too."""
        ss = [s for s in self.world.sessions.values() if s.ready]
        if also is not None and also not in ss:
            ss.append(also)
        rows = {s.player_name: s.save_state() for s in ss}
        for name, st in self.unsaved.items():           # (one who left while saving failed: kept till it's saved)
            rows.setdefault(name, st)
        try:
            self.store.save_characters(list(rows.items()), self.world_state())
        except Exception:
            log.exception("Saving failed (tried again in %d seconds)", SAVE_RETRY)
            live = {s.player_name for s in self.world.sessions.values()}
            self.unsaved.update((name, st) for name, st in rows.items() if name not in live)
            self.world.save_soon = True                 # (nothing is cleared: it's all still to save)
            self.last_save = time.time() + SAVE_RETRY - SAVE_SOON
            return False
        self.unsaved = {}
        self.last_save = time.time()
        self.world.save_soon = False
        for s in ss:
            s.save_requested = False
        return True

    def failed_once(self, what):
        """The tick's part what went wrong: logged the first time, not 20 times a second."""
        if what not in self.tick_failed:
            self.tick_failed.add(what)
            log.exception("%s failed", what)

    def save_session(self, s):
        self.save_all(also=s)

    def nightly_backup(self):
        day = time.strftime("%Y-%m-%d")
        if self.last_backup_day == day:
            return
        self.last_backup_day = day
        try:
            out = self.store.backup(self.backup_dir)
            log.info("Backup: %s", out)
        except Exception:
            log.exception("Backup failed")

    # =================================================================================================================
    # The tick
    # =================================================================================================================
    async def run(self):
        self.running = True
        last = next_at = time.perf_counter()
        self.nightly_backup()
        while self.running:
            start = time.perf_counter()
            dt = start - last
            last = start
            try:
                self.world.tick(dt)
            except Exception:
                self.failed_once("Tick")
            try:                                        # (the world went wrong: everyone's still sent what there is)
                await self.send_updates()
            except Exception:
                self.failed_once("Sending")
            try:
                self.lingered()
            except Exception:
                self.failed_once("Lingering")
            wanted = self.world.save_soon or any(s.save_requested for s in self.world.sessions.values())
            if wanted and time.time() - self.last_save >= SAVE_SOON:
                self.save_all()
            if time.time() - self.last_where >= WHERE_EVERY:
                self.last_where = time.time()
                self.passes_ran_out()
                self.friend_passes()
                where = self.where_message()
                if where != self.last_where_sent:       # (nobody's moved: nothing to send everyone)
                    self.last_where_sent = where
                    self.broadcast(where)
            if time.time() - self.last_save >= SAVE_EVERY:
                self.save_all()
                self.nightly_backup()
            spent = time.perf_counter() - start
            self.tick_ms = self.tick_ms * 0.95 + spent * 1000 * 0.05
            next_at += TICK
            if next_at < time.perf_counter() - TICK:
                next_at = time.perf_counter()           # (fell behind: carry on from now, no rush to catch up)
            while time.perf_counter() < next_at:        # (a sleep can end early, on Windows: 20 ticks a second)
                await asyncio.sleep(max(0.001, next_at - time.perf_counter()))

    async def send_updates(self):
        sends = []
        shared = {}                                     # (what's the same for every viewer, worked out once)
        for s, c in list(self.clients.items()):
            if c.closed or not s.ready:
                continue
            msgs = self.world.guarded(s, "view", snapshot, self.world, s, shared) or []
            if s.out:
                msgs += s.take_out()
            if msgs:
                sends.append(self.send(c, msgs))
        if sends:
            await asyncio.gather(*sends, return_exceptions=True)

    async def send(self, c, msg):
        """msg queued for c (its writer sends it, in order). A connection too far behind is closed (its player's
        game is saved as they go): it would only fall further behind."""
        if c.closed:
            return
        if c.queue.qsize() >= BACKLOG:
            log.warning("%s is too far behind: closing the connection", c.session.player_name if c.session else c.addr)
            c.closed = True
            await c.ws.close()
            return
        try:
            text = json.dumps(msg, separators=(",", ":"))  # (here, in the tick's time, where it's counted)
        except (TypeError, ValueError):                 # (one that can't be written: skipped, the rest still go)
            log.exception("A message that can't be sent: %.200r", msg)
            return
        c.queue.put_nowait(text)

    def broadcast(self, msg, exclude=None):
        for s in self.world.sessions.values():
            if s is not exclude and s.ready:
                s.emit(msg)

    def where_message(self):
        """Where everyone is (for the dots on each other's minimaps): the dead and the hidden aren't anywhere."""
        out = []
        for s in self.world.sessions.values():
            p = s.player
            if s.in_world() and p is not None and s.player_visible and not s.dead_wait:
                # (to 16 pixels: finer than a minimap's dot; pt: the party it's in, the page marks yours)
                out.append({"name": s.player_name, "x": round(p.cx / 16) * 16, "y": round(p.cy / 16) * 16, "z": p.z,
                            "pt": s.party_id})
        return {"t": "where", "list": out}

    def players_message(self):
        return {"t": "players", "list": [{"name": s.player_name, "map": s.screen_name, "level": s.player_level()}
                                         for s in self.world.sessions.values() if s.ready],
                "max": self.max_players}

    # =================================================================================================================
    # Connections
    # =================================================================================================================
    def assets_version(self):
        """web/assets' version (export_web_assets.py's): a page loaded before they changed loads again. Read again
        only when the manifest is written again."""
        path = os.path.join(self.root, "web", "assets", "manifest.json")
        try:
            mtime = os.path.getmtime(path)
            if mtime != self.assets_seen[0]:
                with open(path, encoding="utf-8") as f:
                    self.assets_seen = (mtime, str(json.load(f).get("version", "")))
        except (OSError, ValueError):
            return ""
        return self.assets_seen[1]

    def code_version(self):
        """The page's own code (web/index.html, js, css), as a version: a page loaded from other code loads again, and
        the central server keeps a game's files by it. Not the build number: a desktop app has none."""
        if self.code_seen is None:
            web_dir, h = os.path.join(self.root, "web"), hashlib.sha1()
            paths = [os.path.join(web_dir, "index.html")]
            for sub in ("js", "css"):
                for folder, _, names in sorted(os.walk(os.path.join(web_dir, sub))):
                    paths += [os.path.join(folder, n) for n in sorted(names)]
            for path in paths:
                try:
                    with open(path, "rb") as f:
                        h.update(os.path.relpath(path, web_dir).replace(os.sep, "/").encode() + b"\0" + f.read() + b"\0")
                except OSError:
                    pass
            self.code_seen = h.hexdigest()[:12]
        return self.code_seen

    LOCAL = ("127.0.0.1", "::1", "localhost")
    own = False                 # (an app's own game: this machine's till its host opens it, in Options)

    def remote(self):
        """A server of its own, joined to a central server, is a remote server, whatever network it's on: listed once it's
        approved, a Hallisium account always, and nothing different for its own network. Only an app's game is local."""
        return not self.own and bool(self.central_url())

    def server_name(self):
        """The game's name: what the host called it in Options, else DS_NAME, else this machine's (a public server's
        machine is a container's number, new each time it's made, and a new name takes it off the list till it's approved
        again: a plain name, till it's given one)."""
        saved = self.store.setting("name", "")
        if saved == UNNAMED:                            # (Options saved with only the plain name in it: no name at all)
            saved = ""
        named = saved or getattr(self, "default_name", "") or os.environ.get("DS_NAME", "")
        if named:
            return named
        if self.remote():
            return UNNAMED
        return "Shards of Ashen on " + socket.gethostname()

    def pvp_open(self):
        """Open PvP: players may fight outside the arena (dsengine/pvp.py). An admin's /pvp, else DS_PVP (off)."""
        v = self.store.setting("pvp", "") or os.environ.get("DS_PVP", "")
        return v.strip().lower() in ("1", "yes", "on", "true")

    def pvp_command(self, s, text):
        """/pvp on|off (an admin or the host): open PvP for this server, kept with the world. /pvp: which it is."""
        words = text.split()
        c = self.clients.get(s)
        if len(words) < 2 or words[1].lower() not in ("on", "off"):
            s.emit({"t": "chat", "from": "", "text": "Players %s fight outside the arena here. (/pvp on or /pvp off)" %
                    ("may" if self.world.open_pvp else "can't")})
            return
        if not (s.admin_enabled or (c is not None and (c.host or self.is_local(c.addr)))):
            s.emit({"t": "chat", "from": "", "text": "Only an admin or the host can change that."})
            return
        on = words[1].lower() == "on"
        self.store.set_setting("pvp", "1" if on else "0")
        self.world.open_pvp = on
        log.info("%s turned open PvP %s", s.player_name, "on" if on else "off")
        for o in list(self.world.sessions.values()):
            o.open_seen = None
            o.dirty_me = True                               # (the PvP badge shows, or goes)
            if on:
                o.pvp_open_told()
            else:
                o.display_message("Players can no longer fight each other outside the arena.", "INFO")
                if o.pvp_mark_until:
                    o.pvp_mark_until = o.now                # (no mark lasts: it fades next tick)

    @property
    def lan_open(self):
        """An app's own game, opened to the network by its host (closed each time it starts)."""
        return self.store.setting("lan_open", "0").strip() == "1"

    def is_local(self, addr):
        return (addr or "") in self.LOCAL or (addr or "").startswith("127.")

    RESERVED = {"admin", "administrator", "moderator", "mod", "server", "system", "gm", "staff", "support",
                "owner", "shards of ashen"}

    @staticmethod
    def client_addr(request):
        """Who's connecting (auth.client_address: behind a proxy, the player's own address). The wrong-password wait
        and the sign-up limit go by it: behind a proxy without it, everyone would share the proxy's."""
        return auth.client_address(request)

    def setting_int(self, env, default):
        try:
            return int(os.environ.get(env, default))
        except ValueError:
            return default

    def signups_left(self, addr):
        """How many more accounts an address may make today (DS_REGISTER_PER_DAY; 0: no limit)."""
        most = self.setting_int("DS_REGISTER_PER_DAY", 5)
        if most <= 0:
            return 99
        day = time.strftime("%Y%m%d")
        made = [d for d in self.signups.get(addr, []) if d == day]
        if made:
            self.signups[addr] = made
        else:
            self.signups.pop(addr, None)                # (yesterday's forgotten: the list doesn't grow for ever)
        return most - len(made)

    def banned(self, name):
        return self.store.setting("ban:" + name.lower(), "")

    @staticmethod
    def origin_ok(request):
        """A browser says which page opened the connection: only the game's own pages (served from here, whatever
        address they were reached by) may, never another site's open on a host's computer (DS_ORIGINS: others)."""
        origin = request.headers.get("Origin", "")
        if not origin or origin == "null":
            return True                         # (not a web page: the tests, the bots, a file page in an app)
        from urllib.parse import urlsplit
        try:
            host = urlsplit(origin).netloc.lower()
        except ValueError:
            return False
        more = [o.strip().lower() for o in os.environ.get("DS_ORIGINS", "").split(",") if o.strip()]
        return host == (request.host or "").lower() or origin.lower() in more

    def conns_ok(self, addr):
        """One address may hold only so many connections open (DS_CONNECTIONS_PER_ADDRESS; 0: no limit): enough for a
        family behind one router, not thousands left idle to use up the memory. This machine's own and a relay's
        visitors aren't counted (each relayed visit is an address of its own)."""
        most = self.setting_int("DS_CONNECTIONS_PER_ADDRESS", 10)
        return most <= 0 or self.is_local(addr) or self.relayed(addr) or self.conns.get(addr, 0) < most

    async def handle_ws(self, request):
        if not self.origin_ok(request):
            log.warning("A page from %s tried to join from %s", request.headers.get("Origin"), request.remote)
            return web.Response(status=403, text="Only this game's own page may join it.")
        addr = self.client_addr(request)
        if not self.conns_ok(addr):
            if addr not in self.turned_away:
                self.turned_away.add(addr)
                log.warning("Too many connections from %s: turning more away", addr)     # (once, not each try)
            return web.Response(status=429, text="Too many connections from here.")
        self.conns[addr] = self.conns.get(addr, 0) + 1
        try:
            return await self.serve_ws(request, addr)
        finally:
            left = self.conns.get(addr, 1) - 1
            if left > 0:
                self.conns[addr] = left
            else:
                self.conns.pop(addr, None)                      # (all gone: the table doesn't grow for ever)
                self.turned_away.discard(addr)

    async def serve_ws(self, request, addr):
        # (a closed browser: gone in seconds; an app's own game takes a character brought from a public server)
        ws = web.WebSocketResponse(heartbeat=5, max_msg_size=8 * 1024 * 1024 if self.own else 65536)
        await ws.prepare(request)
        c = Client(ws, addr)
        c.writer = asyncio.ensure_future(c.write())
        if self.own and not self.lan_open and not self.is_local(c.addr) and not self.relayed(c.addr):
            await self.send(c, {"t": "closed", "text": "This game isn't open to the network just now."})
            await asyncio.sleep(0.2)
            await ws.close()
            return ws
        if self.relayed(c.addr):           # (through the relay, a few at once: one that never signs in is put out)
            asyncio.get_running_loop().call_later(SIGN_IN_SECONDS, self.signed_in_yet, c)
        await self.send(c, {"t": "hello", "online": len(self.world.sessions), "max": self.max_players,
                            "name": self.server_name(), "id": self.server_id(), "central": bool(self.central_url()),
                            "registration": self.registration, "invite": bool(self.invite_code),
                            "assets": self.assets_version(), "code": self.code_version(),
                            "home": self.central_url(), **self.version})
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    if msg.type == WSMsgType.ERROR:
                        break
                    continue
                if not self.rate_ok(c):
                    continue
                try:
                    data = json.loads(msg.data)
                except ValueError:
                    continue
                if not isinstance(data, dict):
                    continue
                if c.session is None:
                    await self.handle_login(c, data)
                else:
                    self.handle_game(c, data)
        finally:
            c.closed = True
            if c.writer is not None:
                c.writer.cancel()
            self.disconnect(c)
        return ws

    @staticmethod
    def signed_in_yet(c):
        if not c.closed and c.owner is None and not c.ws.closed:
            asyncio.ensure_future(c.ws.close())

    @staticmethod
    def rate_ok(c):
        now = time.monotonic()
        c.msg_times = [t for t in c.msg_times if now - t < 1.0]
        if len(c.msg_times) >= 120:
            return False
        c.msg_times.append(now)
        return True

    # ----- the central server (central/): one account for every game, a ticket to come in by, and the server list
    def central_url(self):
        return os.environ.get("DS_CENTRAL", "").strip().rstrip("/")

    def server_id(self):
        """This server's own id (made once, kept with the world): what a ticket is made out to, what the network and
        the central server know it by."""
        sid = self.store.setting("server_id", "")
        if not sid:
            sid = os.urandom(8).hex()
            self.store.set_setting("server_id", sid)
        return sid

    def id_proof(self):
        """What proves the id is this server's (made once, kept with the world): the central server keeps the id for
        the first to bring it, so another game that gave this one's id can't use its players' tickets."""
        got = self.store.setting("id_proof", "")
        if not got:
            got = os.urandom(24).hex()
            self.store.set_setting("id_proof", got)
        return got

    async def central_post(self, path, body, packed=False):
        """A question for the central server, on one connection kept open (a new one is a new TLS handshake: several
        KB, each player each minute). packed: it's big enough to be worth zipping."""
        import aiohttp
        try:
            if self.central_http is None or self.central_http.closed:
                self.central_http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8),
                                                          connector=aiohttp.TCPConnector(keepalive_timeout=120))
            ask = {"data": gzip.compress(json.dumps(body, separators=(",", ":")).encode("utf-8")),
                   "headers": {"Content-Type": "application/json", "Content-Encoding": "gzip"}} if packed else {"json": body}
            async with self.central_http.post(self.central_url() + path, **ask) as r:
                got = await r.json(content_type=None)
                if self.central_away:
                    log.info("The central server is answering again")
                self.central_away = False
                return got
        except Exception as e:                          # (no network, the central server down: said once, not each call)
            if not self.central_away:
                log.warning("The central server didn't answer %s: %s", path, e)
            self.central_away = True
            return None

    async def send_log(self, s, c, data):
        """The host's or an admin's Send log: first the log as it is (what will go: it has players' names and
        addresses), then that same text to the central server, which emails it to support. One an hour from a server."""
        if not self.central_url():
            s.emit({"t": "log", "error": "There's no central server to send it through."})
            return
        if data.get("do") != "send":
            c.log_shown = self.log_header(s) + "\n\n" + (RECENT_LOG.text() or "(nothing written down yet)")
            s.emit({"t": "log", "text": c.log_shown})
            return
        if not c.log_shown:
            return
        try:
            left = LOG_EVERY - (time.time() - float(self.store.setting("log_sent", "0") or 0))
        except ValueError:
            left = 0
        if left > 0:
            s.emit({"t": "log", "error": "A log went from this server not long ago: try again in %d minutes."
                    % max(1, round(left / 60))})
            return
        note = " ".join(str(data.get("note", "")).split())[:1000]
        mine = data.get("client")                       # (the page's own side, which it showed beside this)
        mine = mine[-LOG_CLIENT:] if isinstance(mine, str) else ""
        got = await self.central_post("/api/game/log", {**self.reporter.about(), "log": c.log_shown, "note": note,
                                                        "client": mine}, packed=True)
        if got and got.get("ok"):
            self.store.set_setting("log_sent", str(int(time.time())))
            log.info("%s sent the log to support", s.player_name)
            c.log_shown = ""
            s.emit({"t": "log", "sent": True})
        else:
            s.emit({"t": "log", "error": str((got or {}).get("text") or
                                            "The central server didn't answer: try again later.")[:200]})

    def log_header(self, s):
        """The game as it is now, at the top of a log sent to support: what it's running, how it's keeping up, who's
        where (a problem's often about a place)."""
        up = int(time.time() - self.up_since)
        lines = ["Shards of Ashen %s, Python %s on %s" % (self.version.get("version", "?"), platform.python_version(),
                                                           platform.platform(terse=True)),
                 "Kind: %s; up %dh %02dm; a tick takes %.1f ms (of %d); saved %d s ago" % (
                     self.reporter.about()["kind"], up // 3600, up % 3600 // 60, self.tick_ms, TICK * 1000,
                     time.time() - self.last_save),
                 "Sent by: %s" % s.player_name,
                 "Playing (%d of %d):" % (len(self.world.sessions), self.max_players)]
        for o in self.world.sessions.values():
            p = o.player
            where = "%s %d,%d" % (o.screen_name, o.tile_of_x(p.cx), o.tile_of_y(p.cy)) if p is not None else "not in yet"
            lines.append("  %s at %s%s%s" % (o.player_name, where, "" if o.connected else " (connection lost)",
                                             " (dead)" if o.dead_wait else ""))
        if self.tick_failed:
            lines.append("Gone wrong in the tick (logged once): %s" % ", ".join(sorted(self.tick_failed)))
        return "\n".join(lines)

    async def close_central(self):
        if self.central_http is not None:
            await self.central_http.close()

    # ----- friends by Hallisium account: the central server keeps them; this game asks it with the key a player's ticket
    # brought (only their friends), says where they're playing, and tells the engine (Session.central_friends)
    def took_friends(self, s, got):
        """The central server's word on s's friends: theirs, asks either way, where friends are playing."""
        s.central_friends = {k: [str(a) for a in got.get(k) or []] for k in ("friends", "asking", "asked")}
        s.central_friends["playing"] = got.get("playing") if isinstance(got.get("playing"), dict) else {}
        self.world.together.account_friends[s.account.lower()] = list(s.central_friends["friends"])
        s.dirty_me = s.journal_wanted = True            # (the Friends page, if it's open: sent from the tick)

    async def friends_now(self, s, **ask):
        """s's friends from the central server (and where s is playing: here), asking or removing one first."""
        got = await self.central_post("/api/game/friends", {"grant": s.grant, "playing": s.player_name,
                                                            "place": self.server_name(),
                                                            "have": getattr(s, "friends_have", ""), **ask})
        if got and got.get("ok") and s.connected and not got.get("same"):     # (same: as they had it, nothing to tell)
            s.friends_have = got.get("have", "")
            self.took_friends(s, got)
        elif got and got.get("banned"):
            await self.turn_away(s)
        return got

    async def welcome_friends(self, s):
        """Come in by an account: it's playing here; the world's friends of this character whose characters are
        Hallisium accounts' are asked by account instead (when both have come in, they're friends again)."""
        got = await self.friends_now(s)
        if not got or not got.get("ok"):
            return
        t = self.world.together
        known = {a.lower() for k in ("friends", "asked") for a in s.central_friends.get(k, [])}
        for n in list(t.friends.get(s.player_name, [])):
            acct = t.accounts.get(n, "")
            if not acct or acct.lower() == s.account.lower():
                continue
            if acct.lower() not in known:
                await self.friends_now(s, name=acct)
            t.friends[s.player_name].remove(n)

    def central_friend(self, s, account, remove):
        """The engine's ask (Add friend, Remove friend, the journal's Accept and Decline) for a Hallisium account."""
        if not getattr(s, "grant", ""):
            s.refuse("Friends by account are kept by the central server: come in from the start screen, signed in.")
            return
        asyncio.ensure_future(self.change_friend(s, account, remove))

    async def change_friend(self, s, account, remove):
        got = await self.friends_now(s, name=account, remove=bool(remove))
        if not got or not got.get("ok"):
            s.refuse((got or {}).get("text") or "The central server didn't answer: try again soon.")
            return
        done = got.get("done")
        who = next((a for k in ("friends", "asking", "asked") for a in s.central_friends.get(k, [])
                    if a.lower() == account.lower()), account)
        if done == "removed":
            s.display_message("%s is no longer on your friends list." % who, "INFO")
        elif done == "friends":
            s.display_message("%s is your friend now." % who, "SUCCESS")
        elif done == "asked":
            s.display_message("You've asked %s to be your friend." % who, "INFO")
        else:
            s.display_message("You've asked %s already." % who, "INFO")
        for o in list(self.world.sessions.values()):    # (their characters here hear it at once)
            if o is not s and o.account and o.account.lower() == who.lower() and getattr(o, "grant", ""):
                if done == "asked":
                    o.display_message("%s (%s) asks to be your friend: see the journal's Friends page." %
                                      (s.player_name, s.account), "INFO")
                elif done == "friends":
                    o.display_message("%s is your friend now." % s.account, "SUCCESS")
                asyncio.ensure_future(self.friends_now(o))

    async def keep_friends(self):
        """Every minute: everyone in by an account is still playing here, and hears their friends' news; and the host's
        friends, who may come in through the central server."""
        for s in list(self.world.sessions.values()):
            if not s.connected:
                continue
            if getattr(s, "grant", ""):
                got = await self.friends_now(s)
                if got is None or got.get("ok") or got.get("banned"):
                    continue
            # (come straight back, no key to their friends; or their key's no good: run out, or the account's deleted)
            if s.account and await self.central_banned(s.account):
                await self.turn_away(s)
        await self.host_friends_now()

    async def central_banned(self, account):
        """Has the central server banned this account? No answer (no central server, or it's away) isn't a ban."""
        if not self.central_url() or not account:
            return False
        got = await self.central_post("/api/game/standing", {"name": account})
        return bool(got and got.get("banned"))

    async def turn_away(self, s):
        """The central server has banned s's account while s plays here (never the host, in their own game)."""
        c = self.clients.get(s)
        if c is None or c.host:
            return
        self.save_session(s)
        await self.send(c, {"t": "kicked", "reason": "Your Hallisium account is banned."})
        await c.flush()                                 # (said before it's closed: a closed one sends nothing)
        c.closed = c.sent_away = True
        try:
            await c.ws.close()
        except Exception:
            pass
        log.info("%s's account is banned on the central server: turned away", s.player_name)

    def hosted_by(self, account, grant):
        self.host_account, self.host_grant = account, grant
        self.store.set_setting("host_account", account)
        self.store.set_setting("host_grant", grant)
        if self.for_friends():
            asyncio.ensure_future(self.host_friends_now())

    async def host_friends_now(self):
        if not (self.for_friends() and self.host_grant and self.central_url()):
            return
        got = await self.central_post("/api/game/friends", {"grant": self.host_grant})
        if got and got.get("ok"):
            self.host_friends = [str(a) for a in got.get("friends") or []]
            self.store.set_setting("host_friends", json.dumps(self.host_friends))

    async def announce(self, bye=False):
        """A remote server tells the central server it's there: its id, name, address (DS_PUBLIC_URL,
        or where it calls from and its port), how many are playing. Every minute; goodbye as it stops."""
        if not self.remote():
            return
        key, secret = self.server_id(), self.store.setting("central_secret", "")
        if bye:
            await self.central_post("/api/goodbye", {"key": key, "secret": secret})
            return
        got = await self.central_post("/api/announce", {
            "key": key, "secret": secret, "proof": self.id_proof(), "name": self.server_name(), "url": os.environ.get("DS_PUBLIC_URL", ""),
            "port": int(os.environ.get("DS_PUBLIC_PORT", os.environ.get("DS_PORT", "8484"))),
            "online": len([s for s in self.world.sessions.values() if s.ready]), "max": self.max_players,
            "version": self.version.get("version", "")})
        if got and got.get("ok"):
            if got.get("secret") and got.get("secret") != secret:
                self.store.set_setting("central_secret", got["secret"])
            if got.get("key") and got["key"] != key:
                self.store.set_setting("server_id", got["key"])     # (the central server gave it another)

    # ----- who's playing: a Hallisium account (the central server's ticket), the host (the key its app started the server
    # with) or a device (a key of its own: on this machine and its network only); then one of their characters
    def devices_welcome(self, addr):
        """A device's own key (no Hallisium account) is enough here: on an app's own game, from this machine and its
        network; from anywhere on a server with no central server (there's no other way in); never on a remote one."""
        if not self.central_url():
            return True
        if self.remote():
            return False
        try:
            ip = ipaddress.ip_address(addr or "")
        except ValueError:
            return False
        return ip.is_loopback or ip.is_private

    def joined_token(self):
        """What a remote server's page gets once it's been let in, for its address: a reload is still welcome, and nothing
        else shows the page but a ticket."""
        key = self.store.setting("joined_key", "")
        if not key:
            key = os.urandom(24).hex()
            self.store.set_setting("joined_key", key)
        return hmac.new(key.encode("utf-8"), b"joined", hashlib.sha256).hexdigest()[:32]

    def joined_ok(self, token):
        return bool(token) and auth.same(token, self.joined_token())

    def place_of(self, c):
        """What kind of place this is to c, for what the character screen tells them about where a character lives."""
        if self.remote():
            return "public"
        if self.own:
            return "own" if c.host else "theirs"
        return "server"

    @staticmethod
    def relayed(addr):
        return (addr or "").startswith("relay:")

    def for_friends(self):
        """Open to the internet (its host's say, in Options): it still runs here, and the central server passes the host's
        friends' visits to it."""
        return self.store.setting("internet_open", "0") == "1"

    def lan_address(self):
        """Where others on this network open an app's own game (a machine in Docker can't tell: it's never one)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("10.255.255.255", 1))        # (no packet goes: it only picks the way out)
                ip = s.getsockname()[0]
        except OSError:
            return ""
        return "http://%s:%d" % (ip, self.port) if self.own and not ip.startswith("127.") else ""

    def reach_of(self, c):
        """What the host's Options show of who can reach an app's own game."""
        signed = c.account and c.account.lower() == (self.host_account or "").lower() and self.host_grant
        return {"own": self.own and self.is_local(c.addr), "internet": self.for_friends(), "signed": bool(signed),
                "address": self.lan_address(), "link": "%s/play/%s/" % (self.central_url(), self.server_id())
                if self.central_url() else ""}

    def friend_of_host(self, owner):
        """A relayed visitor is let in only as the host's Hallisium account, or a friend's."""
        if not owner.startswith("a:") or not self.host_account:
            return False
        who = owner[2:].lower()
        return who == self.host_account.lower() or who in [f.lower() for f in self.host_friends]

    @staticmethod
    def device_owner(key):
        return "d:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]

    def banned_owner(self, owner):
        return self.store.setting("banowner:" + owner.lower(), "")

    @staticmethod
    def ban_words(start, why):
        """Why they can't come in, with the admin's reason if they gave one (/ban with none keeps the word "banned")."""
        return "%s: %s" % (start, why) if why and why != "banned" else start + "."

    async def ticket_name(self, ticket, relayed=False):
        """The Hallisium account a ticket from the central server is for, why not, and what else it said (their friends
        and a key to them): (name, "", got) or ("", why, None). relayed: it came through a friend's link."""
        if not self.central_url():
            return "", "This game isn't joined to the central server.", None
        got = await self.central_post("/api/verify", {"ticket": str(ticket)[:100], "server": self.server_id(),
                                                      "proof": self.id_proof(), "relayed": bool(relayed)})
        if got and got.get("taken"):
            # (another game had this one's id first: a new one, and the player comes in again by it)
            self.store.set_setting("server_id", os.urandom(8).hex())
            log.warning("This game's id was another's on the central server: it's %s now", self.server_id())
        if not got or not got.get("ok"):
            return "", (got or {}).get("text") or "The central server couldn't be reached just now.", None
        return auth.clean_name(got.get("name", "")), "", got

    async def handle_login(self, c, data):
        t = data.get("t")
        if t == "auth":
            await self.authenticate(c, data)
        elif t in ("play", "create"):
            if c.owner is None:
                await self.send(c, {"t": "login_fail", "reason": "Join from the start screen first."})
            elif t == "play":
                await self.choose(c, data)
            else:
                await self.create(c, data)
        elif t in ("export", "import"):
            if c.owner is None:
                await self.send(c, {"t": "login_fail", "reason": "Join from the start screen first."})
            elif t == "export":
                await self.export_character(c, data)
            else:
                await self.import_character(c, data)

    async def authenticate(self, c, data):
        """Who's playing (a ticket, the host's key or a device's key): their characters here."""
        device = str(data.get("device", ""))[:100]
        device = self.device_owner(device) if len(device) >= 16 else ""
        linked = self.store.setting("dev:" + device[2:], "") if device else ""
        owner, why, got = "", "", None
        if data.get("ticket"):
            name, why, got = await self.ticket_name(data["ticket"], self.relayed(c.addr))
            owner = "a:" + name if name else ""
        key = os.environ.get("DS_HOST_KEY", "")
        if key and self.is_local(c.addr) and auth.same(data.get("host", ""), key):
            name = auth.clean_name(data.get("account", ""))
            mine = "a:" + name if name else linked or device
            if mine.lower() != owner.lower():
                got = None                              # (a ticket for someone else: the host's say goes)
            owner, c.host = mine, True
        came_from = self.store.setting("devat:" + device[2:], "") if linked else ""
        if not owner and linked and came_from and came_from != c.addr:
            # (a device's key only ever given to one place: from somewhere new, the start screen's ticket again, so a
            # game that took another's id, and was handed the key for it, can't come in here as you)
            linked, why = "", why or "You've come from somewhere new: join from the start screen to sign in again."
        if not owner and linked:
            if await self.central_banned(linked[2:]):   # (come straight back: a central ban still counts)
                await self.send(c, {"t": "login_fail", "reason": "Your Hallisium account is banned. Sign in on the start "
                                                                 "screen to see why."})
                return
            owner = linked                              # (this device came in by its account here before)
        elif not owner and device and self.devices_welcome(c.addr):
            owner = device
        if not owner:
            await self.send(c, {"t": "login_fail", "reason": why or "Sign in with your Hallisium account on the start "
                                                                   "screen to play here."})
            return
        if self.banned_owner(owner):
            await self.send(c, {"t": "login_fail", "reason": self.ban_words("You're banned from this server",
                                                                            self.banned_owner(owner))})
            return
        if self.relayed(c.addr) and not self.friend_of_host(owner):
            await self.send(c, {"t": "login_fail", "reason": "This game is for %s's friends: ask them to be yours."
                                % (self.host_account or "its host")})
            return
        if device and owner.startswith("a:") and linked.lower() != owner.lower():
            self.store.set_setting("dev:" + device[2:], owner)    # (a reload, or the central server away: still you)
        if device and owner.startswith("a:") and (got is not None or not came_from):
            self.store.set_setting("devat:" + device[2:], c.addr)  # (from where: a ticket says so again, from anywhere)
        c.owner, c.account = owner, owner[2:] if owner.startswith("a:") else ""
        c.grant, c.friends_got = (got.get("grant") or "", got) if got else ("", None)
        c.pass_until = int((got or {}).get("pass_until") or 0)
        c.full = self.full_of(c, data, got)
        if c.host and c.grant and c.account and c.grant != self.host_grant:
            self.hosted_by(c.account, c.grant)          # (the host's key: the relay opens with it, for friends)
        await self.send_characters(c)

    def full_of(self, c, data, got):
        """Whether they have the full game, or play the demo (dsengine/demo.py). The central server says, with their
        ticket (what they've bought; whether there's a demo yet at all); without one, the last it said for their
        account here (a linked device, the central server away). The host of an app's own game: its app says too
        (bought on the device; and whether there's a demo, signed in or not). No demo yet, or a server of its own
        with no central server: everyone has it."""
        if got is not None:
            self.store.set_setting("demo", "1" if got.get("demo") else "")
        if c.host and "demo" in data:                   # (an app's own game, signed in or not: its app says)
            self.store.set_setting("demo", "1" if data.get("demo") else "")
        if self.store.setting("demo", "") != "1" or not (self.central_url() or self.own):
            return True
        key = "full:" + c.account.lower() if c.account else ""
        if got is not None:
            full = bool(got.get("full", True))
            if key:
                self.remember_full(c.account, full, c.pass_until)
        else:
            full, c.pass_until = self.full_remembered(c.account) if key else (False, 0)
        c.device_full = c.host and bool(data.get("full")) and not full
        if c.host:
            self.store.set_setting("host_full", "1" if full or c.device_full else "")   # (its Friend Pass: the host's)
        return full or c.device_full

    def friend_passes(self):
        """The Friend Pass (dsengine/demo.py): a demo player has the full game while someone who owns it is in a game
        whose host owns it (an app's own game: its host's device or account), or, on a public server (no host),
        while one of their Hallisium friends who owns it is in the game (not any owner: a busy server would be the
        full game for everyone)."""
        w = self.world
        here = [s for s in w.sessions.values() if s.ready and s.connected]
        owners = {s.account.lower(): s for s in here if s.full and s.account}
        host = ""
        if self.store.setting("host_full", "") == "1":
            host = self.host_account or next((s.player_name for s in here if s.full), "")
        for s in here:
            if s.full:
                s.want_friend_pass(False)
            elif self.own and self.relayed(getattr(self.clients.get(s), "addr", "")):
                # (a friend through the relay: only an owner by account, never an app's word for its device, which a
                # tampered app could give: the central server's what counts out on the internet)
                s.want_friend_pass(any(o.full and not getattr(self.clients.get(o), "device_full", False)
                                       for o in here), host)
            elif self.own:
                s.want_friend_pass(any(o.full for o in here), host)
            else:
                mates = w.together.account_friends.get(s.account.lower(), []) if s.account else []
                mate = next((owners[a.lower()] for a in mates if a.lower() in owners), None)
                s.want_friend_pass(mate is not None, mate.account if mate is not None else "")

    def remember_full(self, account, full, until):
        """What the central server last said of an account's full game, for coming in without a ticket: bought ("1"),
        a time pass ("until:<its end>": over when it's over, asked or not) or neither ("")."""
        self.store.set_setting("full:" + account.lower(), ("until:%d" % until if until else "1") if full else "")

    def full_remembered(self, account):
        said = self.store.setting("full:" + account.lower(), "")
        if said.startswith("until:"):
            until = int(said[6:] or 0) if said[6:].isdigit() else 0
            return time.time() < until, until
        return said == "1", 0

    async def owns_now(self, s):
        """A time pass run out: whether they have the full game still (bought since?), asked of the central server.
        No answer: asked again in a minute, and after a few the pass is over (till it says otherwise)."""
        s.pass_until = 0
        got = await self.central_post("/api/game/owns", {"grant": s.grant})
        if not (got and (got.get("ok") or got.get("banned"))) and s.connected:
            s.pass_tries = getattr(s, "pass_tries", 0) + 1
            s.pass_until = int(time.time()) + PASS_RETRY
            if s.pass_tries >= PASS_TRIES and s.full:
                s.set_full(getattr(self.clients.get(s), "device_full", False))
            return
        s.pass_tries = 0
        if got and got.get("ok") and s.connected:
            s.pass_until = int(got.get("pass_until") or 0)
            self.remember_full(s.account, bool(got.get("full")), s.pass_until)
            c = self.clients.get(s)
            if c is not None and got.get("full"):
                c.device_full = False                   # (the account's now: no longer only the device's word)
            s.set_full(bool(got.get("full")) or getattr(c, "device_full", False))
        elif got and got.get("banned"):
            await self.turn_away(s)

    def passes_ran_out(self):
        now = time.time()
        for s in list(self.world.sessions.values()):
            if s.connected and getattr(s, "pass_until", 0) and now >= s.pass_until:
                if getattr(s, "grant", ""):
                    asyncio.ensure_future(self.owns_now(s))
                else:                                   # (come in without a ticket: nobody to ask, so it's over)
                    s.pass_until = 0
                    s.set_full(getattr(self.clients.get(s), "device_full", False))

    async def send_characters(self, c, text=""):
        mine = []
        for name in self.store.characters_of(c.owner):
            st = self.store.load_character(name) or {}
            mine.append({"name": name, "level": st.get("level") or 1, "look": st.get("look")})
        demo = self.world.data.demo
        await self.send(c, {"t": "characters", "list": mine, "account": c.account, "most": MOST_CHARACTERS,
                            "demo": demo["level"] if demo["area"] and not getattr(c, "full", True) else 0,
                            "make": self.registration == "open", "invite": bool(self.invite_code), "text": text,
                            "place": self.place_of(c), "joined": self.joined_token() if self.remote() else ""})

    # ----- a character copied from a public server to the player's own device: one way, never back (an app's own game
    # takes it; nothing ever takes one from a device, so nothing made at home reaches a public server)
    async def export_character(self, c, data):
        name = auth.clean_name(data.get("name", ""))
        acct = self.store.account(name) if name else None
        if not self.remote() or acct is None or (self.store.owner(acct[0]) or "").lower() != c.owner.lower():
            await self.send(c, {"t": "login_fail", "reason": "That isn't one of your characters here."})
            return
        live = self.world.sessions.get(acct[0])
        if live is not None:                            # (playing somewhere just now: what it is this moment)
            self.save_session(live)
        await self.send(c, {"t": "exported", "name": acct[0], "save": self.store.load_character(acct[0]) or {}})

    async def import_character(self, c, data):
        fail = lambda text: self.send(c, {"t": "login_fail", "reason": text})     # noqa: E731
        save = data.get("save")
        if not (self.own and c.host):
            return await fail("A character can only be brought to your own game, on your own device.")
        if not isinstance(save, dict):
            return await fail("That isn't a character.")
        if len(self.store.characters_of(c.owner)) >= MOST_CHARACTERS:
            return await fail("You have %d characters here already: that's the most." % MOST_CHARACTERS)
        base = auth.clean_name(data.get("name", ""))
        if not base:
            return await fail("That isn't a character.")
        name, n = base, 1
        while self.store.account(name) is not None or name.lower() in self.RESERVED:
            n += 1
            name = "%s%d" % (base[:18], n)              # (Ash2: a new name never has a space)
        try:
            Session(self.world, name).load_state(save)  # (one that won't load never gets a place on the list)
        except Exception:
            return await fail("That character can't be read.")
        self.store.create_account(name, "", False, c.owner)
        self.store.save_character(name, save)
        log.info("Character %s copied to this device", name)
        await self.send_characters(c, "%s is here now." % name)

    async def choose(self, c, data):
        name = auth.clean_name(data.get("name", ""))
        acct = self.store.account(name) if name else None
        if acct is None or (self.store.owner(acct[0]) or "").lower() != c.owner.lower():
            await self.send(c, {"t": "login_fail", "reason": "That isn't one of your characters here."})
        elif self.banned(acct[0]):
            await self.send(c, {"t": "login_fail", "reason": self.ban_words("%s is banned from this server" % acct[0],
                                                                            self.banned(acct[0]))})
        else:
            await self.enter_game(c, acct, data)

    async def create(self, c, data):
        """A new character: its name one of a kind here."""
        fail = lambda text, **more: self.send(c, {"t": "login_fail", "reason": text, **more})     # noqa: E731
        name = auth.clean_name(data.get("name", ""))
        if auth.new_name_refused(name):
            return await fail(auth.new_name_refused(name))
        if self.registration != "open":
            return await fail("New characters can't be made on this server.")
        if self.invite_code and str(data.get("invite", "")) != self.invite_code:
            return await fail("That invite code isn't right.", invite=True)
        if len(self.store.characters_of(c.owner)) >= MOST_CHARACTERS:
            return await fail("You have %d characters here already: that's the most." % MOST_CHARACTERS)
        if name.lower() in self.RESERVED:
            return await fail("That name is kept for the server: pick another.")
        if self.store.account(name) is not None:
            return await fail("Someone here has a character called %s already: pick another name." % name)
        if self.signups_left(c.addr) <= 0:
            return await fail("Too many new characters from here today: try again tomorrow.")
        self.signups.setdefault(c.addr, []).append(time.strftime("%Y%m%d"))
        try:
            self.store.create_account(name, "", False, c.owner)
        except sqlite3.IntegrityError:
            return await fail("Someone here has a character called %s already: pick another name." % name)
        log.info("New character %s (%s) from %s", name, c.account or "a device", c.addr)
        await self.enter_game(c, self.store.account(name), data)

    async def enter_game(self, c, acct, data):
        """One of theirs chosen, or a new one made: into the world."""
        name, _, admin = acct
        w = self.world
        old = w.sessions.get(name)
        if old is None and len([s for s in w.sessions.values() if s.ready]) >= self.max_players:
            await self.send(c, {"t": "login_fail", "reason": "The server is full (%d players). Try again soon." %
                                self.max_players})
            return
        if old is not None:                     # logged in again (another tab, a lost connection): this one takes over
            old.linger_until = 0                # (left while marked, and back in time)
            oc = self.clients.pop(old, None)
            if oc is not None:
                oc.session = None
                await self.send(oc, {"t": "kicked", "reason": "You logged in somewhere else."})
                await oc.flush()
                await oc.ws.close()
            s = old
            s.connected = True
            s.out = []
            s.sent_maps = {}
            s.view_known = {}
            s.dirty_me = s.dirty_quests = s.cells_dirty = s.weather_dirty = True
            if getattr(s, "trade", None):           # (the new page never saw it: off, rather than open unseen)
                s.trade_close("The trade is off.")
            if s.ab_mode:
                s.emit(s.box_state())               # (a box that was open: open on the new page too)
            if not s.ready:
                s.enter_world()
            if s.dead_wait:                 # (they died and went: back to life, where they'd have woken)
                s.respawn()
        else:
            s = Session(w, name, admin=bool(admin) or c.account.lower() in self.admins)
            s.full = c.full                             # (the demo, or not, before they're anywhere: demo.py)
            saved = self.unsaved.pop(name, None) or self.store.load_character(name)   # (left while saves failed)
            s.load_state(saved)
            s.muted_until = float(self.store.setting("mute:" + name.lower(), "0") or 0)   # (a mute outlasts a reload)
            if saved is None and data.get("t") == "create":
                s.set_look(data.get("look"))
            w.sessions[name] = s
            s.enter_world()
            self.save_session(s)
            self.broadcast({"t": "chat", "from": "", "text": "%s has joined the game." % name}, exclude=s)
            s.friends_hear("Your friend %s has come into Ashen." % name)
        s.account = c.account
        s.pass_until = c.pass_until
        s.set_full(c.full)
        if c.account:
            w.together.accounts[name] = c.account
        if c.grant:
            s.grant = c.grant
            s.friends_have = ""                         # (come in again: told the whole of it, not "the same")
            self.took_friends(s, c.friends_got or {})
            asyncio.ensure_future(self.welcome_friends(s))
        c.session = s
        self.clients[s] = c
        self.last_where_sent = None                     # (the one come in hasn't had the dots yet)
        log.info("%s logged in from %s (%d online)", name, c.addr, len(w.sessions))
        await self.send(c, {"t": "welcome", "name": name, "admin": s.admin_enabled, "uid": s.player.uid,
                            "account": c.account, "server": self.server_name(),
                            "host": s.admin_enabled or c.host or self.is_local(c.addr), "lan": self.lan_open,
                            "logs": bool(self.central_url()),
                            "reach": self.reach_of(c),
                            "explored": s.explored_for_client(), "time": w.clock_event(), "labels": s.my_labels()})
        self.broadcast(self.players_message())

    WHISPER = ("/w ", "/whisper ", "/tell ", "/msg ")

    def moderate(self, s, text):
        """An admin's commands for a public server: /kick Name, /ban Name [why], /unban Name, /mute Name [minutes],
        /unmute Name, /bans. True if it was one."""
        words = text.split()
        cmd = words[0].lower()
        if cmd not in ("/kick", "/ban", "/unban", "/mute", "/unmute", "/bans"):
            return False
        say = lambda words: s.emit({"t": "chat", "from": "", "text": words})     # noqa: E731
        if cmd == "/bans":
            rows = self.store.db.execute("SELECT key, value FROM world WHERE key LIKE 'set:ban:%' AND value != ''"
                                         ).fetchall()
            say("Banned: " + (", ".join("%s (%s)" % (k[8:], v) for k, v in rows) or "nobody"))
            return True
        if len(words) < 2:
            say("Who? %s Name" % cmd)
            return True
        name, extra = words[1], " ".join(words[2:])
        for k in range(len(words) - 1, 1, -1):          # (names may have spaces: the longest that's a character)
            maybe = " ".join(words[1:k + 1])
            if self.store.account(maybe) or maybe in self.world.sessions:
                name, extra = maybe, " ".join(words[k + 1:])
                break
        acct = self.store.account(name)
        name = acct[0] if acct else name
        o = self.world.sessions.get(name)
        own = self.store.owner(name) or ""             # (a ban is on whose it is too: not just a new character away)
        if cmd == "/unban":
            self.store.drop_setting("ban:" + name.lower())
            if own:
                self.store.drop_setting("banowner:" + own.lower())
            say("%s may play again." % name)
        elif cmd == "/unmute":
            self.store.drop_setting("mute:" + name.lower())
            if o is not None:
                o.muted_until = 0
            say("%s may talk again." % name)
        elif cmd == "/mute":
            minutes = int(extra) if extra.strip().isdigit() else 30
            self.store.set_setting("mute:" + name.lower(), str(int(time.time() + minutes * 60)))   # (kept past a reload)
            if o is not None:
                o.muted_until = time.time() + minutes * 60
                o.emit({"t": "chat", "from": "", "text": "An admin has muted you for %d minutes." % minutes})
            say("%s is muted for %d minutes." % (name, minutes))
        else:
            if cmd == "/ban":
                if acct is None:
                    say("There's no character called %s." % name)
                    return True
                self.store.set_setting("ban:" + name.lower(), (extra or "banned")[:100])
                if own:
                    self.store.set_setting("banowner:" + own.lower(), (extra or "banned")[:100])
            c = self.clients.get(o) if o is not None else None
            if c is not None:
                self.save_session(o)
                asyncio.ensure_future(self.send(c, {"t": "kicked", "reason": "An admin has %s you." %
                                                    ("banned" if cmd == "/ban" else "removed")}))
                c.closed = c.sent_away = True                   # (gone at once, marked or not)
                asyncio.ensure_future(c.ws.close())
            say("%s is %s." % (name, "banned" if cmd == "/ban" else "kicked"))
            log.info("%s %sed %s", s.player_name, cmd[1:], name)
        return True

    def chat_command(self, s, text):
        """/w <name> <words>: only they hear it (names may have spaces: the longest online name that fits).
        /r <words>: answers whoever whispered to you last. /p <words>: your party hears it. /leave: leave your
        party. /records: the hall of records."""
        low = text.lower()
        if low.startswith("/p ") or low.startswith("/party "):
            words = text.split(" ", 1)[1].strip()
            if not s.party_names():
                s.emit({"t": "chat", "from": "", "text": "You're not in a party. (Right-click a player: Invite to party.)"})
                return
            for o in [s] + s.party_members():
                o.emit({"t": "chat", "from": s.player_name, "text": words, "party": 1})
            return
        if low.strip() in ("/leave", "/leaveparty"):
            s.leave_party()
            return
        if low.split(" ", 1)[0] == "/pvp":
            self.pvp_command(s, text)
            return
        if low.strip() == "/records":
            s.records_menu()
            return
        if s.admin_enabled and self.moderate(s, text):
            return
        if low.startswith("/friend ") or low.startswith("/unfriend "):
            name = text.split(" ", 1)[1].strip()
            (s.remove_friend_named if low.startswith("/unfriend") else s.add_friend_named)(name)
            return
        if low.startswith("/letter "):                  # (to a friend who's away: a courier finds them)
            bits = text.split(" ", 2)
            if len(bits) < 3:
                s.refuse("/letter Name your message (or /letter Name +Item_Name your message)")
            else:
                self.world.wonders.send_letter(s, bits[1], bits[2])
            return
        if low.startswith("/r ") or low.startswith("/reply "):
            to = getattr(s, "last_whisper_from", "")
            words = text.split(" ", 1)[1].strip()
            if not to:
                s.emit({"t": "chat", "from": "", "text": "Nobody has whispered to you yet."})
                return
            return self.whisper(s, to, words)
        for cmd in self.WHISPER:
            if low.startswith(cmd):
                rest = text[len(cmd):].strip()
                names = sorted(self.world.sessions, key=len, reverse=True)
                to = next((n for n in names if rest.lower().startswith(n.lower()) and
                           (len(rest) == len(n) or rest[len(n)] == " ")), None)
                if to is None:
                    who = rest.split(" ", 1)[0]
                    s.emit({"t": "chat", "from": "", "text": "%s isn't here. (Whisper: /w <name> <words>)" % who})
                    return
                return self.whisper(s, to, rest[len(to):].strip())
        s.emit({"t": "chat", "from": "", "text": "Chat: just type to talk to everyone. /w <name> <words> whispers to "
                                                  "one player; /r <words> answers the last whisper."})

    def whisper(self, s, to, words):
        o = self.world.sessions.get(to)
        if o is None or not o.connected:
            s.emit({"t": "chat", "from": "", "text": "%s isn't here." % to})
            return
        if not words:
            return
        if o is s:
            s.emit({"t": "chat", "from": "", "text": "You mutter to yourself."})
            return
        o.last_whisper_from = s.player_name
        o.emit({"t": "chat", "from": s.player_name, "text": words, "whisper": "from"})
        s.emit({"t": "chat", "from": s.player_name, "to": to, "text": words, "whisper": "to"})

    def handle_game(self, c, data):
        s = c.session
        t = data.get("t")
        if t == "chat":
            text = " ".join(str(data.get("text", "")).split())[:CHAT_MAX]
            talks = not text.startswith("/") or text.lower().startswith(TALKING)
            if getattr(s, "muted_until", 0) > time.time() and talks:
                s.emit({"t": "chat", "from": "", "text": "You're muted for now."})
                return
            if talks and text:
                now = time.monotonic()
                said = [t for t in getattr(s, "chat_times", []) if now - t < CHAT_SECONDS]
                if len(said) >= CHAT_LINES:
                    s.emit({"t": "chat", "from": "", "text": "You're talking too fast: a moment."})
                    return
                s.chat_times = said + [now]
            if text.startswith("/"):
                self.world.guarded(s, "chat command", self.chat_command, s, text)
            elif text:
                self.broadcast({"t": "chat", "from": s.player_name, "text": text})
            return
        if t == "quit":
            if time.time() - self.last_save >= SAVE_SOON:
                self.save_session(s)
            else:
                s.save_requested = True         # (saved with everyone in a moment: not a save a message)
            return
        if t == "server_name":                          # (Options: the host names the game)
            if s.admin_enabled or self.is_local(c.addr):
                name = " ".join(str(data.get("name", "")).split())[:40]
                if name:
                    self.store.set_setting("name", name)
                    self.broadcast({"t": "server_name", "name": name})
            return
        if t == "log":                                  # (Options: the server's log, shown, then sent to support)
            if s.admin_enabled or c.host or self.is_local(c.addr):
                asyncio.ensure_future(self.send_log(s, c, data))
            return
        if t == "ping":
            s.emit({"t": "pong", "c": data.get("c"), "tick": round(self.tick_ms, 1)})
            return
        if t == "lan":                                  # (open to the network or not: an app's own game's host)
            if self.own and (s.admin_enabled or self.is_local(c.addr)):
                self.store.set_setting("lan_open", "1" if data.get("open") else "0")
                log.info("%s %s the game to the network", s.player_name, "opened" if self.lan_open else "closed")
                if not self.lan_open:
                    for o, oc in list(self.clients.items()):
                        if not self.is_local(oc.addr) and not o.admin_enabled:
                            o.emit({"t": "chat", "from": "", "text": "The host has closed the game to the network."})
                            self.save_session(o)
                            oc.closed = True
                            asyncio.ensure_future(oc.ws.close())
                if self.network_changed:
                    asyncio.ensure_future(self.network_changed())
                self.broadcast({"t": "lan", "open": self.lan_open})
            return
        if t == "internet":                             # (open to the internet or not: an app's own game's host, signed in)
            if self.own and self.is_local(c.addr):
                on = bool(data.get("open")) and self.reach_of(c)["signed"]
                self.store.set_setting("internet_open", "1" if on else "0")
                log.info("%s %s the game to the internet", s.player_name, "opened" if on else "closed")
                if not on:
                    for o, oc in list(self.clients.items()):
                        if self.relayed(oc.addr):
                            o.emit({"t": "chat", "from": "", "text": "The host has closed the game to the internet."})
                            self.save_session(o)
                            oc.closed = True
                            asyncio.ensure_future(oc.ws.close())
                asyncio.ensure_future(self.internet_changed())
                self.broadcast({"t": "internet", "internet": on})
            return
        self.world.guarded(s, "command %s" % str(t)[:20], s.handle, data)    # (a bad one logged once, not each time)

    def disconnect(self, c):
        s = c.session
        if s is None or self.clients.get(s) is not c:
            return
        del self.clients[s]
        if s.pvp_lingers() and not getattr(c, "sent_away", False):
            # (marked, out where players fight: they stay a while, to be fought; back in time, they carry on)
            s.game_close()
            self.save_session(s)
            s.linger_until = time.time() + LINGER
            s.stop_player_walk()
            s.player_attack_target = None
            log.info("%s left while marked: in the world %ds more", s.player_name, LINGER)
            return
        self.gone(s)

    def lingered(self):
        """Those who left while marked (disconnect): gone once their time's up, they've died, or the mark's faded."""
        for s in list(self.world.sessions.values()):
            if getattr(s, "linger_until", 0) and s not in self.clients:
                s.out = []                              # (nobody to send it to)
                if time.time() >= s.linger_until or s.dead_wait or not s.pvp_marked():
                    self.gone(s)

    def gone(self, s):
        s.linger_until = 0
        s.leave_world()
        s.connected = False
        self.world.sessions.pop(s.player_name, None)
        self.save_session(s)                            # (as they left it: a stake given back, kept)
        log.info("%s left (%d online)", s.player_name, len(self.world.sessions))
        self.broadcast({"t": "chat", "from": "", "text": "%s has left the game." % s.player_name})
        s.friends_hear("Your friend %s has left Ashen." % s.player_name)
        self.broadcast(self.players_message())
        if getattr(s, "grant", ""):                     # (not playing here now, as their friends see it)
            asyncio.ensure_future(self.central_post("/api/game/friends", {"grant": s.grant, "playing": ""}))

    async def shutdown(self):
        self.running = False
        for s, c in list(self.clients.items()):
            await self.send(c, {"t": "kicked", "reason": "The server is stopping (your game is saved)."})
        self.save_all()
        for c in list(self.clients.values()):
            await c.flush()
            try:
                await c.ws.close()
            except Exception:
                pass
        self.store.close()
