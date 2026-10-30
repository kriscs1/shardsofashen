"""The central server: every player's account (one name and password for every game), the list of remote game servers
(each announces itself: its name, address and how many are playing), the ads on the start screen, and the start
screen itself for a browser. Standard library plus aiohttp, like the game server.

The apps (Android, desktop) and a browser open the start screen, log in here, and then: play alone, host a game (local:
only answered on its own network; remote: announced here, listed for everyone), or join one (local: on the network or
by address; remote: from the list here). Joining, the start screen asks here for a ticket for that one server, and the
game server asks here whether the ticket's good (the player's name, once, for that server only). A game server keeps
its own accounts too, for a network with no way to reach here.

  python -m central                    (DS_CENTRAL_DB, DS_CENTRAL_PORT 8490, DS_CENTRAL_NAME, DS_CENTRAL_ADS, ...)

  POST /api/register  {name, password}            -> {ok, token, name, recovery}
  POST /api/login     {name, password}            -> {ok, token, name}
  POST /api/reset     {name, code, password}      -> {ok, recovery}
  POST /api/me        {token}                     -> {ok, name}
  POST /api/logout    {token}
  POST /api/recovery  {token}                     -> {ok, recovery}      (a new code, the old one gone)
  POST /api/ticket    {token, server}             -> {ok, ticket}        (server: the game server's id)
  POST /api/verify    {ticket, server}            -> {ok, name}          (a game server asking)
  POST /api/announce  {key, secret, name, url?, port, online, max, version}  -> {key, secret}
  POST /api/goodbye   {key, secret}
  GET  /api/servers                               -> [{key, name, url, online, max, version}]
  GET  /api/hello                                 -> {name, motd, ad, players, servers}
  GET  /                                          the start screen (a browser's: join a game, local or remote)"""
import asyncio
import json
import logging
import os
import random
import time

from aiohttp import web

from server import auth
from .store import CentralStore

log = logging.getLogger("ashen.central")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS, FAIL_WINDOW, FAIL_WAIT = 6, 300, 60
RESERVED = {"admin", "administrator", "moderator", "mod", "server", "system", "gm", "staff", "support", "owner"}
DEFAULT_ADS = [
    {"text": "Host your own world: friends on your Wi-Fi join it from their phones.", "link": ""},
    {"text": "Run a server on a cloud VM and it's listed here for everyone: see README-Server.md.", "link": ""},
]


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Central:
    def __init__(self, db_path):
        self.store = CentralStore(db_path)
        self.fails = {}                 # (kind, which) -> [times]
        self.signups = {}               # address -> [days]
        self.name = os.environ.get("DS_CENTRAL_NAME", "Shards of Ashen")
        self.motd = os.environ.get("DS_CENTRAL_MOTD", "")

    # ----- who's asking, and how often
    @staticmethod
    def addr(request):
        if os.environ.get("DS_TRUST_PROXY", "").strip() in ("1", "yes", "on", "true"):
            fwd = request.headers.get("X-Forwarded-For", "")
            if fwd:
                return fwd.split(",")[0].strip()
        return request.remote or ""

    def wait(self, name, addr):
        now = time.monotonic()
        waits = []
        for key in (("name", name.lower()), ("addr", addr)):
            times = [t for t in self.fails.get(key, []) if now - t < FAIL_WINDOW]
            self.fails[key] = times
            if len(times) >= FAILS:
                waits.append(int(FAIL_WAIT - (now - times[-1])) + 1)
        return max([w for w in waits if w > 0], default=0)

    def failed(self, name, addr):
        now = time.monotonic()
        for key in (("name", name.lower()), ("addr", addr)):
            self.fails.setdefault(key, []).append(now)

    def ads(self):
        path = os.environ.get("DS_CENTRAL_ADS", "")
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    got = json.load(f)
                if isinstance(got, list) and got:
                    return got
            except (OSError, ValueError):
                log.warning("The ads file %s couldn't be read", path)
        return DEFAULT_ADS

    @staticmethod
    async def hashed(text):
        return await asyncio.get_running_loop().run_in_executor(None, auth.hash_password, text)

    @staticmethod
    async def matches(text, stored):
        return bool(stored) and await asyncio.get_running_loop().run_in_executor(None, auth.check_password, text,
                                                                                 stored)

    # ----- the API
    async def body(self, request):
        try:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError):
            return {}

    async def register(self, request):
        d, addr = await self.body(request), self.addr(request)
        name = auth.clean_name(d.get("name", ""))
        password = str(d.get("password", ""))[:200]
        if not name:
            return no("Pick a name: letters, numbers, spaces, _ and -.")
        if os.environ.get("DS_REGISTRATION", "open") != "open":
            return no("New accounts can't be made just now.")
        if name.lower() in RESERVED:
            return no("That name is kept back: pick another.")
        if self.store.account(name):
            return no("That name is taken. Log in instead?")
        least = max(4, env_int("DS_PASSWORD_MIN", 8))
        if len(password) < least or password.lower() == name.lower():
            return no("Use a password of at least %d characters (not your name)." % least)
        day = time.strftime("%Y%m%d")
        made = [x for x in self.signups.get(addr, []) if x == day]
        if env_int("DS_REGISTER_PER_DAY", 3) > 0 and len(made) >= env_int("DS_REGISTER_PER_DAY", 3):
            return no("Too many new accounts from here today: try again tomorrow.")
        code = auth.recovery_code()
        self.store.create_account(name, await self.hashed(password), await self.hashed(auth.clean_code(code)))
        self.signups[addr] = made + [day]
        log.info("New account %s from %s", name, addr)
        return yes(token=self.store.new_token(name), name=name, recovery=code)

    async def login(self, request):
        d, addr = await self.body(request), self.addr(request)
        name = auth.clean_name(d.get("name", ""))
        w = self.wait(name, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        acct = self.store.account(name)
        if acct is None or not await self.matches(str(d.get("password", ""))[:200], acct[1]):
            self.failed(name, addr)
            return no("That name and password don't go together.")
        if acct[3]:
            return no("%s is banned: %s" % (acct[0], acct[3]))
        return yes(token=self.store.new_token(acct[0]), name=acct[0])

    async def reset(self, request):
        d, addr = await self.body(request), self.addr(request)
        name = auth.clean_name(d.get("name", ""))
        w = self.wait(name, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        acct = self.store.account(name)
        if acct is None or not await self.matches(auth.clean_code(d.get("code", "")), acct[2]):
            self.failed(name, addr)
            return no("That name and recovery code don't go together.")
        new = str(d.get("password", ""))[:200]
        if len(new) < max(4, env_int("DS_PASSWORD_MIN", 8)):
            return no("Use a new password of at least %d characters." % max(4, env_int("DS_PASSWORD_MIN", 8)))
        code = auth.recovery_code()
        self.store.set_password(acct[0], await self.hashed(new))
        self.store.set_recover(acct[0], await self.hashed(auth.clean_code(code)))
        return yes(recovery=code, name=acct[0])

    async def me(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        return yes(name=name) if name else no("Not logged in.")

    async def logout(self, request):
        self.store.drop_token((await self.body(request)).get("token", ""))
        return yes()

    async def recovery(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        if not name:
            return no("Not logged in.")
        code = auth.recovery_code()
        self.store.set_recover(name, await self.hashed(auth.clean_code(code)))
        return yes(recovery=code)

    async def ticket(self, request):
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        server = str(d.get("server", ""))[:64]
        if not name:
            return no("Not logged in.")
        if not server:
            return no("Which game?")
        acct = self.store.account(name)
        if acct and acct[3]:
            return no("%s is banned." % name)
        return yes(ticket=self.store.new_ticket(name, server))

    async def verify(self, request):
        d = await self.body(request)
        name = self.store.use_ticket(d.get("ticket", ""), str(d.get("server", ""))[:64])
        return yes(name=name) if name else no("That ticket isn't good here.")

    async def announce(self, request):
        d = await self.body(request)
        name = " ".join(str(d.get("name", "")).split())[:40] or "A game of Shards of Ashen"
        url = str(d.get("url", "")).strip()[:200]
        if not url:                                   # (no address of its own: where it's calling from, its port)
            host = self.addr(request)
            if ":" in host:
                host = "[%s]" % host
            url = "http://%s:%d" % (host, int(d.get("port", 8484) or 8484))
        if not url.startswith(("http://", "https://")):
            return no("A server's address starts http:// or https://.")
        key, secret = self.store.announce(str(d.get("key", ""))[:32], str(d.get("secret", ""))[:64], name, url,
                                          int(d.get("online", 0) or 0), int(d.get("max", 0) or 0),
                                          str(d.get("version", ""))[:40])
        return yes(key=key, secret=secret, url=url)

    async def goodbye(self, request):
        d = await self.body(request)
        self.store.goodbye(str(d.get("key", "")), str(d.get("secret", "")))
        return yes()

    async def servers(self, request):
        return web.json_response(self.store.servers())

    async def hello(self, request):
        return yes(name=self.name, motd=self.motd, ad=random.choice(self.ads()),
                   servers=len(self.store.servers()), players=self.store.count_accounts())


def yes(**more):
    return web.json_response({"ok": True, **more})


def no(text):
    return web.json_response({"ok": False, "text": text})


def make_central(db_path):
    c = Central(db_path)
    home = os.path.join(ROOT, "web", "home")

    @web.middleware
    async def cors(request, handler):
        # (the apps' start screens are pages of their own, not this server's: they may ask too)
        if request.method == "OPTIONS":
            resp = web.Response()
        else:
            resp = await handler(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    async def index(request):
        return web.FileResponse(os.path.join(home, "index.html"), headers={"Cache-Control": "no-cache"})

    async def health(request):
        return web.json_response({"ok": True, "servers": len(c.store.servers())})

    app = web.Application(middlewares=[cors])
    app["central"] = c
    for path, fn in (("register", c.register), ("login", c.login), ("reset", c.reset), ("me", c.me),
                     ("logout", c.logout), ("recovery", c.recovery), ("ticket", c.ticket), ("verify", c.verify),
                     ("announce", c.announce), ("goodbye", c.goodbye)):
        app.router.add_post("/api/" + path, fn)
        app.router.add_route("OPTIONS", "/api/" + path, lambda r: web.Response())
    app.router.add_get("/api/servers", c.servers)
    app.router.add_get("/api/hello", c.hello)
    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    app.router.add_get("/config.js", lambda r: web.FileResponse(os.path.join(home, "config.js"),
                                                               headers={"Cache-Control": "no-cache"}))
    if os.path.isdir(home):
        app.router.add_static("/home/", home)
    ads = os.environ.get("DS_CENTRAL_ADS_DIR", "")
    if ads and os.path.isdir(ads):
        app.router.add_static("/ads/", ads)            # (the ads' pictures)
    return app


def main():
    import argparse
    p = argparse.ArgumentParser(description="Shards of Ashen central server: accounts, the server list, ads")
    p.add_argument("--db", default=os.environ.get("DS_CENTRAL_DB", os.path.join(ROOT, "server-data", "central.db")))
    p.add_argument("--host", default=os.environ.get("DS_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=env_int("DS_CENTRAL_PORT", 8490))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    log.info("Shards of Ashen central server on http://%s:%d", args.host, args.port)
    web.run_app(make_central(args.db), host=args.host, port=args.port, print=None)
