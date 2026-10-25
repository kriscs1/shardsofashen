"""The game server: one shared World, up to MAX_PLAYERS players connected over WebSockets, the world ticking 20 times
a second, and everything saved to the database (every minute, when someone leaves, and when the server stops)."""
import asyncio
import json
import logging
import os
import time

from aiohttp import web, WSMsgType

from dsengine import World, Session
from dsengine.view import snapshot

from . import auth
from .store import Store

log = logging.getLogger("dragonsword.server")

TICK = 0.05
SAVE_EVERY = 60
WHERE_EVERY = 1.0           # (seconds between the minimap's dots for the other players)
CHAT_MAX = 200


class Client:
    """One browser connection."""

    def __init__(self, ws, addr):
        self.ws = ws
        self.addr = addr
        self.session = None
        self.msg_times = []
        self.closed = False


class GameServer:
    def __init__(self, root, db_path, max_players=5, registration="open", invite_code="", backup_dir=None, admins=""):
        self.root = root
        # (DS_ADMINS: names the server's owner gives the Admin button, besides the accounts tools/admin.py made admin)
        self.admins = {a.strip().lower() for a in str(admins or "").split(",") if a.strip()}
        from .version import version_info
        self.version = version_info(root)
        self.store = Store(db_path)
        self.max_players = max_players
        self.registration = registration
        self.invite_code = invite_code
        self.backup_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(db_path)), "backups")
        t0 = time.time()
        self.world = World(root)
        self.load_world()
        log.info("World ready: %d maps, %d things (%.1fs)", len(self.world.maps), len(self.world.ents),
                 time.time() - t0)
        self.clients = {}                   # Session -> Client
        self.running = False
        self.last_save = time.time()
        self.last_where = 0.0
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
        w.homes.load(st.get("homes"))
        w.farms.load(st.get("farms"))
        w.market.load(st.get("market"), old_stalls=st.get("stalls"))
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
        return {"queue": list(w.action_queue), "day": w.day_fraction(), "weather": wt, "homes": w.homes.state(), "farms": w.farms.state(), "market": w.market.state()}

    def save_all(self):
        try:
            self.store.save_characters([(s.player_name, s.save_state()) for s in self.world.sessions.values()
                                        if s.ready])
            self.store.save_world(self.world_state())
        except Exception:
            log.exception("Saving failed")
        self.last_save = time.time()

    def save_session(self, s):
        try:
            self.store.save_character(s.player_name, s.save_state())
        except Exception:
            log.exception("Saving %s failed", s.player_name)

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
        last = time.perf_counter()
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
            if any(s.save_requested for s in self.world.sessions.values()):
                for s in self.world.sessions.values():
                    if s.save_requested:
                        s.save_requested = False
                        self.save_session(s)
            if time.time() - self.last_where >= WHERE_EVERY:
                self.last_where = time.time()
                self.broadcast(self.where_message())
            if time.time() - self.last_save >= SAVE_EVERY:
                self.save_all()
                self.nightly_backup()
            spent = time.perf_counter() - start
            self.tick_ms = self.tick_ms * 0.95 + spent * 1000 * 0.05
            await asyncio.sleep(max(0.001, TICK - spent))

    async def send_updates(self):
        sends = []
        for s, c in list(self.clients.items()):
            if c.closed or not s.ready:
                continue
            msgs = snapshot(self.world, s)
            if s.out:
                msgs += s.take_out()
            if msgs:
                sends.append(self.send(c, msgs))
        if sends:
            await asyncio.gather(*sends, return_exceptions=True)

    async def send(self, c, msg):
        if c.closed:
            return
        try:
            await c.ws.send_str(json.dumps(msg, separators=(",", ":")))
        except (ConnectionResetError, RuntimeError):
            c.closed = True

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
                out.append({"name": s.player_name, "x": round(p.cx), "y": round(p.cy), "z": p.z})
        return {"t": "where", "list": out}

    def players_message(self):
        return {"t": "players", "list": [{"name": s.player_name, "map": s.screen_name, "level": s.player_level()}
                                         for s in self.world.sessions.values() if s.ready],
                "max": self.max_players}

    # =================================================================================================================
    # Connections
    # =================================================================================================================
    async def handle_ws(self, request):
        ws = web.WebSocketResponse(heartbeat=5, max_msg_size=65536)     # (a closed browser: gone in seconds)
        await ws.prepare(request)
        c = Client(ws, request.remote)
        await self.send(c, {"t": "hello", "online": len(self.world.sessions), "max": self.max_players,
                            "registration": self.registration, "invite": bool(self.invite_code), **self.version})
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

    async def handle_login(self, c, data):
        t = data.get("t")
        if t not in ("login", "register"):
            return
        name = auth.clean_name(data.get("name", ""))
        password = str(data.get("password", ""))[:200]
        if not name:
            await self.send(c, {"t": "login_fail", "reason": "Pick a name: letters, numbers, spaces, _ and -."})
            return
        acct = self.store.account(name)
        if t == "register":
            if acct is not None:
                await self.send(c, {"t": "login_fail", "reason": "That name is taken. Log in instead?"})
                return
            if self.registration != "open":
                await self.send(c, {"t": "login_fail", "reason": "New characters can't be made on this server."})
                return
            if self.invite_code and str(data.get("invite", "")) != self.invite_code:
                await self.send(c, {"t": "login_fail", "reason": "That invite code isn't right."})
                return
            if len(password) < 4:
                await self.send(c, {"t": "login_fail", "reason": "Use a password of at least 4 characters."})
                return
            self.store.create_account(name, auth.hash_password(password), False)
            acct = self.store.account(name)
        else:
            if acct is None:
                await self.send(c, {"t": "login_fail", "reason": "No character called %s. Make one?" % name})
                return
            if not acct[1]:                         # (a password every time: no browser logs in by itself)
                await self.send(c, {"t": "login_fail",
                                    "reason": "%s has no password yet: ask the server's admin to set one." % name})
                return
            elif not auth.check_password(password, acct[1]):
                await self.send(c, {"t": "login_fail", "reason": "Wrong password."})
                return
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
                await oc.ws.close()
            s = old
            s.connected = True
            s.out = []
            s.sent_maps = {}
            s.view_known = {}
            s.dirty_me = s.dirty_quests = s.cells_dirty = s.weather_dirty = True
            if not s.ready:
                s.enter_world()
            if s.dead_wait:                 # (they died and went: back to life, where they'd have woken)
                s.respawn()
        else:
            s = Session(w, name, admin=bool(admin) or name.lower() in self.admins)
            saved = self.store.load_character(name)
            s.load_state(saved)
            if saved is None and t == "register":
                from dsengine.session import clean_look
                s.look = clean_look(data.get("look"))
            w.sessions[name] = s
            s.enter_world()
            self.save_session(s)
            self.broadcast({"t": "chat", "from": "", "text": "%s has joined the game." % name}, exclude=s)
        c.session = s
        self.clients[s] = c
        log.info("%s logged in from %s (%d online)", name, c.addr, len(w.sessions))
        await self.send(c, {"t": "welcome", "name": name, "admin": s.admin_enabled, "uid": s.player.uid,
                            "explored": s.explored_for_client(), "time": w.clock_event(), "labels": w.map_labels()})
        self.broadcast(self.players_message())

    WHISPER = ("/w ", "/whisper ", "/tell ", "/msg ")

    def chat_command(self, s, text):
        """/w <name> <words>: only they hear it (names may have spaces: the longest online name that fits).
        /r <words>: answers whoever whispered to you last."""
        low = text.lower()
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
        if len(new) < 4:
            return reply(False, "Use a new password of at least 4 characters.")
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
        if len(new) < 4:
            return say("Use a password of at least 4 characters.")
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
            if text.startswith("/"):
                self.chat_command(s, text)
            elif text:
                self.broadcast({"t": "chat", "from": s.player_name, "text": text})
            return
        if t == "quit":
            self.save_session(s)
            return
        if t == "password":
            asyncio.ensure_future(self.change_password(s, data))
            return
        if t == "admin_password":
            if s.admin_enabled:
                asyncio.ensure_future(self.admin_password(s, data))
            return
        if t == "ping":
            s.emit({"t": "pong", "c": data.get("c"), "tick": round(self.tick_ms, 1)})
            return
        try:
            s.handle(data)
        except Exception:
            log.exception("Command %r from %s failed", t, s.player_name)

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
        self.broadcast(self.players_message())

    async def shutdown(self):
        self.running = False
        for s, c in list(self.clients.items()):
            await self.send(c, {"t": "kicked", "reason": "The server is stopping (your game is saved)."})
        self.save_all()
        for c in list(self.clients.values()):
            try:
                await c.ws.close()
            except Exception:
                pass
        self.store.close()
