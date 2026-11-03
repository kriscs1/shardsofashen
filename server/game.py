"""The game server: one shared World, up to MAX_PLAYERS players connected over WebSockets, the world ticking 20 times
a second, and everything saved to the database (every minute, when someone leaves, and when the server stops)."""
import asyncio
import hashlib
import hmac
import ipaddress
import gzip
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
MOST_CHARACTERS = 5     # (an account's, or a device's, on one server)


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
        self.owner = None           # (who's playing, once they've said: "a:<Shards account>" or "d:<device>")
        self.account = ""           # (their Shards account's name, if they came in by one)
        self.host = False           # (the host, by the key its app started the server with)
        self.grant = ""             # (the central server's key to their friends, from their ticket)
        self.friends_got = None     # (their friends, as the ticket's check said)
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
        # (DS_ADMINS: the Shards accounts the server's owner gives the Admin button, besides the characters
        # tools/admin.py made admin)
        self.admins = {a.strip().lower() for a in str(admins or "").split(",") if a.strip()}
        from .version import version_info
        self.version = version_info(root)
        self.assets_seen = (None, "")                   # (web/assets' manifest: when it was written, its version)
        self.code_seen = None                           # (the page's own code: its version, worked out once)
        self.store = Store(db_path)
        self.max_players = max_players
        self.registration = registration
        self.invite_code = invite_code
        self.central_http = None        # (the one connection to the central server: central_post)
        self.own = False                # (an app's own game: this machine's till its host opens it, in Options)
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
        self.load_world()
        self.world.data.places()                        # (read now, not on the first player's login: they'd wait)
        self.world.data.quest_table()
        log.info("World ready: %d maps, %d things (%.1fs)", len(self.world.maps), len(self.world.ents),
                 time.time() - t0)
        self.clients = {}                   # Session -> Client
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

    def server_name(self):
        """The game's name: what the host called it in Options, else DS_NAME, else this machine's (a public server's
        machine is a container's number, new each time it's made, and a new name takes it off the list till it's approved
        again: a plain name, till it's given one)."""
        named = self.store.setting("name", "") or getattr(self, "default_name", "") or os.environ.get("DS_NAME", "")
        if named:
            return named
        if os.environ.get("DS_PUBLIC", "").strip() in ("1", "yes", "on", "true"):
            return "A Shards of Ashen server"
        return "Shards of Ashen on " + socket.gethostname()

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
        if not self.lan_open and not self.is_local(c.addr) and not self.relayed(c.addr):
            await self.send(c, {"t": "closed", "text": "This game isn't open to the network just now."})
            await asyncio.sleep(0.2)
            await ws.close()
            return ws
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
                return await r.json(content_type=None)
        except Exception as e:                          # (no network, the central server down: say so, go on)
            log.warning("The central server didn't answer %s: %s", path, e)
            return None

    async def close_central(self):
        if self.central_http is not None:
            await self.central_http.close()

    # ----- friends by Shards account: the central server keeps them; this game asks it with the key a player's ticket
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
        Shards accounts' are asked by account instead (when both have come in, they're friends again)."""
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
        """The engine's ask (Add friend, Remove friend, the journal's Accept and Decline) for a Shards account."""
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
        await self.send(c, {"t": "kicked", "reason": "Your Shards account is banned."})
        await c.flush()                                 # (said before it's closed: a closed one sends nothing)
        c.closed = True
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

    # ----- who's playing: a Shards account (the central server's ticket), the host (the key its app started the server
    # with) or a device (a key of its own: on this machine and its network only); then one of their characters
    def devices_welcome(self, addr):
        """A device's own key (no Shards account) is enough here: from this machine and its network; from anywhere
        on a server with no central server (there's no other way in); never on a public one that has."""
        if not self.central_url():
            return True
        if os.environ.get("DS_PUBLIC", "").strip() in ("1", "yes", "on", "true"):
            return False
        try:
            ip = ipaddress.ip_address(addr or "")
        except ValueError:
            return False
        return ip.is_loopback or ip.is_private

    @staticmethod
    def relayed(addr):
        return (addr or "").startswith("relay:")

    def for_friends(self):
        """Open to the internet (its host's say, in Options; or DS_FRIENDS=1): it still runs here, and the central server
        passes the host's friends' visits to it."""
        return self.store.setting("internet_open", "0") == "1" or \
            os.environ.get("DS_FRIENDS", "").strip() in ("1", "yes", "on", "true")

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
        """A relayed visitor is let in only as the host's Shards account, or a friend's."""
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

    async def ticket_name(self, ticket):
        """The Shards account a ticket from the central server is for, why not, and what else it said (their friends
        and a key to them): (name, "", got) or ("", why, None)."""
        if not self.central_url():
            return "", "This game isn't joined to the central server.", None
        got = await self.central_post("/api/verify", {"ticket": str(ticket)[:100], "server": self.server_id()})
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

    async def authenticate(self, c, data):
        """Who's playing (a ticket, the host's key or a device's key): their characters here."""
        device = str(data.get("device", ""))[:100]
        device = self.device_owner(device) if len(device) >= 16 else ""
        linked = self.store.setting("dev:" + device[2:], "") if device else ""
        owner, why, got = "", "", None
        if data.get("ticket"):
            name, why, got = await self.ticket_name(data["ticket"])
            owner = "a:" + name if name else ""
        key = os.environ.get("DS_HOST_KEY", "")
        if key and self.is_local(c.addr) and hmac.compare_digest(str(data.get("host", "")), key):
            name = auth.clean_name(data.get("account", ""))
            mine = "a:" + name if name else linked or device
            if mine.lower() != owner.lower():
                got = None                              # (a ticket for someone else: the host's say goes)
            owner, c.host = mine, True
        if not owner and linked:
            if await self.central_banned(linked[2:]):   # (come straight back: a central ban still counts)
                await self.send(c, {"t": "login_fail", "reason": "Your Shards account is banned. Sign in on the start "
                                                                 "screen to see why."})
                return
            owner = linked                              # (this device came in by its account here before)
        elif not owner and device and self.devices_welcome(c.addr):
            owner = device
        if not owner:
            await self.send(c, {"t": "login_fail", "reason": why or "Sign in with your Shards account on the start "
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
        c.owner, c.account = owner, owner[2:] if owner.startswith("a:") else ""
        c.grant, c.friends_got = (got.get("grant") or "", got) if got else ("", None)
        if c.host and c.grant and c.account and c.grant != self.host_grant:
            self.hosted_by(c.account, c.grant)          # (the host's key: the relay opens with it, for friends)
        await self.send_characters(c)

    async def send_characters(self, c, text=""):
        mine = []
        for name in self.store.characters_of(c.owner):
            st = self.store.load_character(name) or {}
            mine.append({"name": name, "level": st.get("level") or 1, "look": st.get("look")})
        await self.send(c, {"t": "characters", "list": mine, "account": c.account, "most": MOST_CHARACTERS,
                            "make": self.registration == "open", "invite": bool(self.invite_code), "text": text})

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
        if not name:
            return await fail("Pick a name: letters, numbers, spaces, _ and -.")
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
            saved = self.store.load_character(name)
            s.load_state(saved)
            if saved is None and data.get("t") == "create":
                s.set_look(data.get("look"))
            w.sessions[name] = s
            s.enter_world()
            self.save_session(s)
            self.broadcast({"t": "chat", "from": "", "text": "%s has joined the game." % name}, exclude=s)
            s.friends_hear("Your friend %s has come into Ashen." % name)
        s.account = c.account
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
                if own:
                    self.store.set_setting("banowner:" + own.lower(), (extra or "banned")[:100])
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
        self.save_session(s)
        s.leave_world()
        s.connected = False
        self.world.sessions.pop(s.player_name, None)
        self.store.save_world(self.world_state())
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
