"""The game server: one shared World, up to MAX_PLAYERS players connected over WebSockets, the world ticking 20 times
a second, and everything saved to the database (every minute, when someone leaves, and when the server stops)."""
import asyncio
import json
import logging
import os
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
WHERE_EVERY = 1.0           # (seconds between the minimap's dots for the other players)
CHAT_MAX = 200
CHAT_LINES, CHAT_SECONDS = 6, 5.0   # (the most lines anyone can say in those seconds: no flooding everyone's chat)
TALKING = ("/p ", "/party ", "/r ", "/reply ", "/w ", "/whisper ", "/tell ", "/msg ")    # (commands that talk)


BACKLOG = 100           # messages a connection may fall behind (5 s of ticks) before it's let go: a slow one
FAILS, FAIL_WINDOW, FAIL_WAIT = 5, 60.0, 30.0     # wrong passwords (a name or an address) before a wait, and how long


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
        self.msg_times = []
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
        # (DS_ADMINS: names the server's owner gives the Admin button, besides the accounts tools/admin.py made admin)
        self.admins = {a.strip().lower() for a in str(admins or "").split(",") if a.strip()}
        from .version import version_info
        self.version = version_info(root)
        self.assets_seen = (None, "")                   # (web/assets' manifest: when it was written, its version)
        self.store = Store(db_path)
        # (an admin named in DS_ADMINS with no character yet: made only with the code from this log, as its invite
        # code, or with tools/admin.py; else whoever took the name first would have the Admin button)
        self.claims = {}
        for n in sorted(self.admins):
            if self.store.account(n) is None:
                self.claims[n] = auth.recovery_code()
                log.warning("DS_ADMINS names %s, who has no character yet: make it with the invite code %s", n,
                            self.claims[n])
        self.max_players = max_players
        self.registration = registration
        self.invite_code = invite_code
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")
        t0 = time.time()
        self.world = World(root)
        self.load_world()
        self.world.data.places()                        # (read now, not on the first player's login: they'd wait)
        self.world.data.quest_table()
        log.info("World ready: %d maps, %d things (%.1fs)", len(self.world.maps), len(self.world.ents),
                 time.time() - t0)
        self.clients = {}                   # Session -> Client
        self.login_fails = {}               # ("name" or "addr", which) -> when its passwords were wrong (monotonic)
        self.signups = {}                   # address -> the days it made characters on (DS_REGISTER_PER_DAY)
        self.running = False
        self.last_save = time.time()
        self.last_where = 0.0
        self.last_where_sent = None     # (the minimap's dots as last sent: again only when they move)
        self.last_backup_day = None
        self.tick_ms = 0.0

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
                "together": w.together.state()}

    def save_all(self, also=None):
        """Everyone in the world, and the world, in one go: what's changed hands between them (a trade, a gift, the
        market) is never saved in two places, or in none, whenever the server stops. also: one leaving, saved too."""
        ss = [s for s in self.world.sessions.values() if s.ready]
        if also is not None and also not in ss:
            ss.append(also)
        try:
            self.store.save_characters([(s.player_name, s.save_state()) for s in ss], self.world_state())
        except Exception:
            log.exception("Saving failed")
        self.last_save = time.time()
        self.world.save_soon = False
        for s in ss:
            s.save_requested = False

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
                await self.send_updates()
            except Exception:
                log.exception("Tick failed")
            wanted = self.world.save_soon or any(s.save_requested for s in self.world.sessions.values())
            if wanted and time.time() - self.last_save >= SAVE_SOON:
                self.save_all()
            if time.time() - self.last_where >= WHERE_EVERY:
                self.last_where = time.time()
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

    LOCAL = ("127.0.0.1", "::1", "localhost")

    def server_name(self):
        """The game's name: what the host called it in Options, else DS_NAME, else this machine's."""
        return self.store.setting("name", "") or getattr(self, "default_name", "") or os.environ.get("DS_NAME", "") or \
            "Shards of Ashen on " + socket.gethostname()

    @property
    def lan_open(self):
        """Open to the network (anyone who can reach this machine may join), or this machine only. Kept with the
        world; DS_LAN_OPEN=0 starts a new world closed."""
        v = self.store.setting("lan_open", os.environ.get("DS_LAN_OPEN", "1"))
        return v.strip() not in ("0", "no", "off", "false")

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

    async def handle_ws(self, request):
        if not self.origin_ok(request):
            log.warning("A page from %s tried to join from %s", request.headers.get("Origin"), request.remote)
            return web.Response(status=403, text="Only this game's own page may join it.")
        ws = web.WebSocketResponse(heartbeat=5, max_msg_size=65536)     # (a closed browser: gone in seconds)
        await ws.prepare(request)
        c = Client(ws, self.client_addr(request))
        c.writer = asyncio.ensure_future(c.write())
        if not self.lan_open and not self.is_local(c.addr):
            await self.send(c, {"t": "closed", "text": "This game isn't open to the network just now."})
            await asyncio.sleep(0.2)
            await ws.close()
            return ws
        await self.send(c, {"t": "hello", "online": len(self.world.sessions), "max": self.max_players,
                            "name": self.server_name(), "id": self.server_id(), "central": bool(self.central_url()),
                            "registration": self.registration, "invite": bool(self.invite_code),
                            "assets": self.assets_version(), **self.version})
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

    def login_wait(self, name, addr):
        """Seconds a name or an address must wait after too many wrong passwords (0: none)."""
        now = time.monotonic()
        waits = []
        for key in (("name", name.lower()), ("addr", addr)):
            times = [t for t in self.login_fails.get(key, []) if now - t < FAIL_WINDOW]
            if times:
                self.login_fails[key] = times
            else:
                self.login_fails.pop(key, None)
            if len(times) >= FAILS:
                waits.append(int(FAIL_WAIT - (now - times[-1])) + 1)
        return max([w for w in waits if w > 0], default=0)

    def login_failed(self, name, addr):
        """Counted as a wrong password (before it's checked, so tries at once can't all slip by): when, for
        login_forgiven if it was right after all."""
        now = time.monotonic()
        for key in (("name", name.lower()), ("addr", addr)):
            self.login_fails.setdefault(key, []).append(now)
        return now

    def login_forgiven(self, name, addr, at):
        for key in (("name", name.lower()), ("addr", addr)):
            if at in self.login_fails.get(key, []):
                self.login_fails[key].remove(at)

    @staticmethod
    def rate_ok(c):
        now = time.monotonic()
        c.msg_times = [t for t in c.msg_times if now - t < 1.0]
        if len(c.msg_times) >= 120:
            return False
        c.msg_times.append(now)
        return True

    async def new_recovery(self, name):
        """A new recovery code for name: kept only as a hash, the code itself told to them once."""
        code = auth.recovery_code()
        self.store.set_setting("recover:" + name.lower(), await self.hashed(auth.clean_code(code)))
        return code

    async def reset_password(self, c, data):
        """Forgotten a password: the name, the recovery code written down at sign-up, a new password. The code is
        used up (a new one is given). Wrong codes count as wrong passwords (the wait)."""
        name = auth.clean_name(data.get("name", ""))
        code = auth.clean_code(data.get("code", ""))
        new = str(data.get("password", ""))[:200]
        fail = lambda text: self.send(c, {"t": "reset_result", "ok": False, "text": text})   # noqa: E731
        wait = self.login_wait(name, c.addr)
        if wait:
            return await fail("Too many tries: wait %d seconds." % wait)
        acct = self.store.account(name)
        stored = self.store.setting("recover:" + name.lower(), "") if acct else ""
        at = self.login_failed(name, c.addr)
        right = bool(stored) and await asyncio.get_running_loop().run_in_executor(None, auth.check_password, code, stored)
        if right:
            self.login_forgiven(name, c.addr, at)
        else:
            await asyncio.sleep(1)
            return await fail("That name and recovery code don't go together. (Lost the code too? Ask the server's "
                              "admin to set you a new password.)")
        least = max(4, self.setting_int("DS_PASSWORD_MIN", 4))
        if len(new) < least:
            return await fail("Use a new password of at least %d characters." % least)
        self.store.set_password(acct[0], await self.hashed(new))
        log.info("%s set a new password with their recovery code", acct[0])
        await self.send(c, {"t": "reset_result", "ok": True, "recovery": await self.new_recovery(acct[0]),
                            "text": "Your new password is set: log in with it."})

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

    async def central_post(self, path, body):
        import aiohttp
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as http:
                async with http.post(self.central_url() + path, json=body) as r:
                    return await r.json(content_type=None)
        except Exception as e:                          # (no network, the central server down: say so, go on)
            log.warning("The central server didn't answer %s: %s", path, e)
            return None

    async def ticket_account(self, c, data):
        """A ticket from the central server: the account it's for (made here the first time), or None (told why)."""
        if not self.central_url():
            await self.send(c, {"t": "login_fail", "reason": "This server isn't joined to the central server: log "
                                                             "in with a name and password here."})
            return None
        got = await self.central_post("/api/verify", {"ticket": str(data.get("ticket", ""))[:100],
                                                      "server": self.server_id()})
        if not got or not got.get("ok"):
            await self.send(c, {"t": "login_fail", "reason": (got or {}).get("text") or
                                "The central server couldn't be reached: log in with this server's own account."})
            return None
        name = auth.clean_name(got.get("name", ""))
        if self.banned(name):
            await self.send(c, {"t": "login_fail", "reason": "%s is banned from this server." % name})
            return None
        acct = self.store.account(name)
        if acct is None and name.lower() in self.claims:
            await self.send(c, {"t": "login_fail", "reason": "%s is kept for this server's admin: make it here with "
                                                             "the code from the server's log first." % name})
            return None
        if acct is None and (self.registration != "open" or self.invite_code):
            await self.send(c, {"t": "login_fail", "reason": "New characters can't be made on this server just by "
                                                             "signing in: ask its admin."})
            return None                                 # (closed, or by invitation: a ticket isn't one)
        if acct is None:
            self.store.create_account(name, "", False)  # (no password here: they come in by ticket)
            self.store.set_setting("central:" + name.lower(), "1")
            acct = self.store.account(name)
        elif not self.store.setting("central:" + name.lower(), ""):
            c.central_name = acct[0]                    # (their own here first: its password links it)
            await self.send(c, {"t": "login_fail", "reason": "This server already has a character called %s of its "
                                "own. Log in with its password here, and it's yours from the central server from now "
                                "on too." % acct[0]})
            return None
        return acct

    async def announce(self, bye=False):
        """A remote server (DS_PUBLIC=1) tells the central server it's there: its id, name, address (DS_PUBLIC_URL,
        or where it calls from and its port), how many are playing. Every minute; goodbye as it stops."""
        if not self.central_url() or os.environ.get("DS_PUBLIC", "").strip() not in ("1", "yes", "on", "true"):
            return
        key, secret = self.server_id(), self.store.setting("central_secret", "")
        if bye:
            await self.central_post("/api/goodbye", {"key": key, "secret": secret})
            return
        got = await self.central_post("/api/announce", {
            "key": key, "secret": secret, "name": self.server_name(), "url": os.environ.get("DS_PUBLIC_URL", ""),
            "port": int(os.environ.get("DS_PUBLIC_PORT", os.environ.get("DS_PORT", "8484"))),
            "online": len([s for s in self.world.sessions.values() if s.ready]), "max": self.max_players,
            "version": self.version.get("version", "")})
        if got and got.get("ok"):
            if got.get("secret") and got.get("secret") != secret:
                self.store.set_setting("central_secret", got["secret"])
            if got.get("key") and got["key"] != key:
                self.store.set_setting("server_id", got["key"])     # (the central server gave it another)

    async def handle_login(self, c, data):
        t = data.get("t")
        if t == "reset":
            await self.reset_password(c, data)
            return
        if t == "ticket":
            acct = await self.ticket_account(c, data)
            if acct is not None:
                await self.enter_game(c, acct, data)
            return
        if t not in ("login", "register"):
            return
        name = auth.clean_name(data.get("name", ""))
        password = str(data.get("password", ""))[:200]
        wait = self.login_wait(name, c.addr)
        if wait:
            await self.send(c, {"t": "login_fail", "reason": "Too many wrong passwords: try again in %d seconds."
                                % wait})
            return
        if not name:
            await self.send(c, {"t": "login_fail", "reason": "Pick a name: letters, numbers, spaces, _ and -."})
            return
        acct = self.store.account(name)
        if acct is not None and self.banned(acct[0]):
            await self.send(c, {"t": "login_fail", "reason": "%s is banned from this server." % acct[0]})
            return
        if t == "register":
            if acct is not None:
                await self.send(c, {"t": "login_fail", "reason": "That name is taken. Log in instead?"})
                return
            if name.lower() in self.RESERVED:
                await self.send(c, {"t": "login_fail", "reason": "That name is kept for the server: pick another."})
                return
            claim = self.claims.get(name.lower())
            if claim and auth.clean_code(str(data.get("invite", ""))) != auth.clean_code(claim):
                await self.send(c, {"t": "login_fail", "invite": True, "reason": "That name is kept for this "
                                    "server's admin: give the code from the server's log as the invite code."})
                return
            if self.signups_left(c.addr) <= 0:
                await self.send(c, {"t": "login_fail", "reason": "Too many new characters from here today: try "
                                                                   "again tomorrow."})
                return
            if self.registration != "open":
                await self.send(c, {"t": "login_fail", "reason": "New characters can't be made on this server."})
                return
            if self.invite_code and not claim and str(data.get("invite", "")) != self.invite_code:
                await self.send(c, {"t": "login_fail", "reason": "That invite code isn't right."})
                return
            least = max(4, self.setting_int("DS_PASSWORD_MIN", 4))
            if len(password) < least:
                await self.send(c, {"t": "login_fail", "reason": "Use a password of at least %d characters." % least})
                return
            if password.lower() == name.lower():
                await self.send(c, {"t": "login_fail", "reason": "Your password can't be your name."})
                return
            day = time.strftime("%Y%m%d")
            self.signups.setdefault(c.addr, []).append(day)     # (counted now: sign-ups at once can't all slip by)
            hashed = await asyncio.get_running_loop().run_in_executor(None, auth.hash_password, password)
            try:
                self.store.create_account(name, hashed, False)
            except sqlite3.IntegrityError:              # (someone took the name while the password was hashed)
                if day in self.signups.get(c.addr, []):
                    self.signups[c.addr].remove(day)
                await self.send(c, {"t": "login_fail", "reason": "That name is taken. Log in instead?"})
                return
            self.claims.pop(name.lower(), None)
            c.recovery = await self.new_recovery(name)  # (shown once, in the welcome: to write down)
            log.info("New character %s from %s", name, c.addr)
            acct = self.store.account(name)
        else:
            if acct is None:
                await self.send(c, {"t": "login_fail", "reason": "No character called %s. Make one?" % name})
                return
            if not acct[1]:                         # (a password every time: no browser logs in by itself)
                await self.send(c, {"t": "login_fail",
                                    "reason": "%s has no password yet: ask the server's admin to set one." % name})
                return
            at = self.login_failed(name, c.addr)
            if not await asyncio.get_running_loop().run_in_executor(None, auth.check_password, password, acct[1]):
                await self.send(c, {"t": "login_fail", "reason": "Wrong password."})
                return
            self.login_forgiven(name, c.addr, at)
            if getattr(c, "central_name", "") == acct[0]:
                self.store.set_setting("central:" + acct[0].lower(), "1")   # (theirs from the central server too)
        await self.enter_game(c, acct, data)

    async def enter_game(self, c, acct, data):
        """Logged in (a password, a new character, or a ticket from the central server): into the world."""
        name, _, admin = acct
        w = self.world
        old = w.sessions.get(name)
        if old is None and len([s for s in w.sessions.values() if s.ready]) >= self.max_players:
            await self.send(c, {"t": "login_fail", "reason": "The server is full (%d players). Try again soon." %
                                self.max_players})
            return
        if old is not None:                     # logged in again (another tab, a lost connection): this one takes over
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
            s = Session(w, name, admin=bool(admin) or name.lower() in self.admins)
            saved = self.store.load_character(name)
            s.load_state(saved)
            if saved is None and data.get("t") == "register":
                s.set_look(data.get("look"))
            w.sessions[name] = s
            s.enter_world()
            self.save_session(s)
            self.broadcast({"t": "chat", "from": "", "text": "%s has joined the game." % name}, exclude=s)
            s.friends_hear("Your friend %s has come into Ashen." % name)
        c.session = s
        self.clients[s] = c
        self.last_where_sent = None                     # (the one come in hasn't had the dots yet)
        log.info("%s logged in from %s (%d online)", name, c.addr, len(w.sessions))
        await self.send(c, {"t": "welcome", "name": name, "admin": s.admin_enabled, "uid": s.player.uid,
                            "recovery": getattr(c, "recovery", ""), "server": self.server_name(),
                            "linked": bool(self.store.setting("central:" + name.lower(), "")),
                            "host": s.admin_enabled or self.is_local(c.addr), "lan": self.lan_open,
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
        if cmd == "/unban":
            self.store.drop_setting("ban:" + name.lower())
            say("%s may play again." % name)
        elif cmd == "/unmute":
            if o is not None:
                o.muted_until = 0
            say("%s may talk again." % name)
        elif cmd == "/mute":
            minutes = int(extra) if extra.strip().isdigit() else 30
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
            c = self.clients.get(o) if o is not None else None
            if c is not None:
                self.save_session(o)
                asyncio.ensure_future(self.send(c, {"t": "kicked", "reason": "An admin has %s you." %
                                                    ("banned" if cmd == "/ban" else "removed")}))
                c.closed = True
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
        if low.strip() == "/records":
            s.records_menu()
            return
        if s.admin_enabled and self.moderate(s, text):
            return
        if low.startswith("/friend ") or low.startswith("/unfriend "):
            name = text.split(" ", 1)[1].strip()
            (s.remove_friend_named if low.startswith("/unfriend") else s.add_friend_named)(name)
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

    # (passwords: scrypt is slow on purpose, so it's worked out off the game's tick)
    async def hashed(self, password):
        return await asyncio.get_running_loop().run_in_executor(None, auth.hash_password, password)

    async def change_password(self, s, data):
        """A player changes their own password (Options): their current one first."""
        old, new = str(data.get("old", ""))[:200], str(data.get("new", ""))[:200]
        reply = lambda ok, text: s.emit({"t": "password_result", "ok": ok, "text": text})
        acct = self.store.account(s.player_name)
        if acct is None:
            return reply(False, "Your account wasn't found.")
        right = await asyncio.get_running_loop().run_in_executor(None, auth.check_password, old, acct[1] or "")
        if not right:
            await asyncio.sleep(1)                      # (no quick guessing)
            return reply(False, "That isn't your current password.")
        least = max(4, self.setting_int("DS_PASSWORD_MIN", 4))
        if len(new) < least:
            return reply(False, "Use a new password of at least %d characters." % least)
        self.store.set_password(s.player_name, await self.hashed(new))     # (other browsers forget them)
        log.info("%s changed their password", s.player_name)
        s.emit({"t": "password_result", "ok": True, "text": "Your password is changed. Use the new one next time you "
                "log in."})

    async def admin_password(self, s, data):
        """An admin sets another player's password (Admin panel): for someone who's forgotten theirs."""
        name = auth.clean_name(data.get("name", ""))
        new = str(data.get("new", ""))[:200]
        say = lambda text: s.emit({"t": "admin_status", "text": text})
        acct = self.store.account(name) if name else None
        if acct is None:
            return say("There's no character called %s." % (name or "that"))
        least = max(4, self.setting_int("DS_PASSWORD_MIN", 4))
        if len(new) < least:
            return say("Use a password of at least %d characters." % least)
        self.store.set_password(acct[0], await self.hashed(new))
        log.info("%s (admin) set %s's password", s.player_name, acct[0])
        other = self.world.sessions.get(acct[0])
        if other is not None and other is not s:
            other.display_message("An admin has given you a new password: use it next time you log in.", "INFO")
        say("%s's password is set. Tell them the new one." % acct[0])

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
        if t == "password":
            asyncio.ensure_future(self.change_password(s, data))
            return
        if t == "recovery":                             # (Options: a new recovery code, shown once)
            async def give():
                s.emit({"t": "recovery", "code": await self.new_recovery(s.player_name)})
            asyncio.ensure_future(give())
            return
        if t == "server_name":                          # (Options: the host names the game)
            if s.admin_enabled or self.is_local(c.addr):
                name = " ".join(str(data.get("name", "")).split())[:40]
                if name:
                    self.store.set_setting("name", name)
                    self.broadcast({"t": "server_name", "name": name})
            return
        if t == "admin_password":
            if s.admin_enabled:
                asyncio.ensure_future(self.admin_password(s, data))
            return
        if t == "ping":
            s.emit({"t": "pong", "c": data.get("c"), "tick": round(self.tick_ms, 1)})
            return
        if t == "lan":                                  # (open to the network or not: the host, or an admin)
            if s.admin_enabled or self.is_local(c.addr):
                self.store.set_setting("lan_open", "1" if data.get("open") else "0")
                log.info("%s %s the game to the network", s.player_name, "opened" if self.lan_open else "closed")
                if not self.lan_open:
                    for o, oc in list(self.clients.items()):
                        if not self.is_local(oc.addr) and not o.admin_enabled:
                            o.emit({"t": "chat", "from": "", "text": "The host has closed the game to the network."})
                            self.save_session(o)
                            oc.closed = True
                            asyncio.ensure_future(oc.ws.close())
                self.broadcast({"t": "lan", "open": self.lan_open})
            return
        self.world.guarded(s, "command %s" % str(t)[:20], s.handle, data)    # (a bad one logged once, not each time)

    def disconnect(self, c):
        s = c.session
        if s is None or self.clients.get(s) is not c:
            return
        del self.clients[s]
        self.save_session(s)
        s.leave_world()
        s.connected = False
        self.world.sessions.pop(s.player_name, None)
        self.store.save_world(self.world_state())
        log.info("%s left (%d online)", s.player_name, len(self.world.sessions))
        self.broadcast({"t": "chat", "from": "", "text": "%s has left the game." % s.player_name})
        s.friends_hear("Your friend %s has left Ashen." % s.player_name)
        self.broadcast(self.players_message())

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
