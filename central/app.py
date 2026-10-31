"""The central server: every player's account (one name and password for every game), the list of remote game servers
(each announces itself: its name, address and how many are playing), the ads on the start screen, and the start
screen itself for a browser. Standard library plus aiohttp, like the game server.

The apps (Android, desktop) and a browser open the start screen, log in here, and then: play alone, host a game (local:
only answered on its own network; remote: announced here, listed for everyone), or join one (local: on the network or
by address; remote: from the list here). Joining, the start screen asks here for a ticket for that one server, and the
game server asks here whether the ticket's good (the player's name, once, for that server only). A game server keeps
its own accounts too, for a network with no way to reach here.

  python -m central                    (DS_CENTRAL_DB, DS_CENTRAL_PORT 8490, DS_CENTRAL_NAME, DS_CENTRAL_ADS, ...)

  POST /api/register  {name, password, email?}    -> {ok, token, name, recovery}
  POST /api/account   {token}                     -> {ok, name, email, admin}
  POST /api/email     {token, email}              -> {ok}                (an email for a forgotten password)
  POST /api/forgot    {who}                       -> {ok}                (a code by email, if the account has one)
  POST /api/login     {name, password}            -> {ok, token, name}
  POST /api/reset     {name, code, password}      -> {ok, recovery}      (code: the recovery code, or the emailed one)
  POST /api/me        {token}                     -> {ok, name}
  POST /api/logout    {token}
  POST /api/recovery  {token}                     -> {ok, recovery}      (a new code, the old one gone)
  POST /api/ticket    {token, server}             -> {ok, ticket}        (server: the game server's id)
  POST /api/verify    {ticket, server}            -> {ok, name}          (a game server asking)
  POST /api/announce  {key, secret, name, url?, port, online, max, version}  -> {key, secret}
  POST /api/goodbye   {key, secret}
  GET  /api/servers                               -> [{key, name, url, online, max, version}]   (approved only)
  POST /api/admin/... {token, ...}                the admin page's (servers, approving, accounts, bans, ads, stats)
  GET  /admin, /privacy, /ads.txt, /app-ads.txt   the admin page, the privacy policy, AdSense's and AdMob's lines
  GET  /api/hello                                 -> {name, motd, ad, players, servers}
  GET  /                                          the start screen (a browser's: join a game, local or remote)"""
import asyncio
import json
import logging
import os
import random
import re
import time

from aiohttp import web

from server import auth
from . import mail
from .store import CentralStore

log = logging.getLogger("ashen.central")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS, FAIL_WINDOW, FAIL_WAIT = 6, 300, 60
RESERVED = {"admin", "administrator", "moderator", "mod", "server", "system", "gm", "staff", "support", "owner"}
DEFAULT_ADS = [
    {"text": "Host your own world: friends on your Wi-Fi join it from their phones.", "link": ""},
    {"text": "Run a server on a cloud VM and it's listed here for everyone: see README-Server.md.", "link": ""},
]


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,20}$")


def clean_email(text):
    e = str(text or "").strip()[:254]
    return e if EMAIL_RE.match(e) else ""


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
        # (an admin named in DS_CENTRAL_ADMINS with no account yet: only someone with the code from this log may make
        # it, or whoever signed up first would be the admin)
        self.claims = {}
        for n in os.environ.get("DS_CENTRAL_ADMINS", "").split(","):
            if n.strip() and not self.store.account(n.strip()):
                self.claims[n.strip().lower()] = auth.recovery_code()
                log.warning("DS_CENTRAL_ADMINS names %s, who has no account yet: sign up as %s with the admin code %s",
                            n.strip(), n.strip(), self.claims[n.strip().lower()])

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

    def is_admin(self, name):
        """An admin of the central server: its account marked so (the admin page), or named in DS_CENTRAL_ADMINS."""
        if not name:
            return False
        names = {n.strip().lower() for n in os.environ.get("DS_CENTRAL_ADMINS", "").split(",") if n.strip()}
        acct = self.store.account(name)
        return bool(acct) and (bool(acct[5]) or name.lower() in names)

    def ads(self):
        own = self.store.setting("ads", "")
        if own:                                         # (set on the admin page)
            try:
                got = json.loads(own)
                if isinstance(got, list) and got:
                    return got
            except ValueError:
                pass
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
        claim = self.claims.get(name.lower())
        if claim and auth.clean_code(str(d.get("claim", ""))) != auth.clean_code(claim):
            return web.json_response({"ok": False, "claim": True, "text": "That name is kept for this server's "
                                      "admin: give the admin code from the server's log."})
        least = max(4, env_int("DS_PASSWORD_MIN", 8))
        if len(password) < least or password.lower() == name.lower():
            return no("Use a password of at least %d characters (not your name)." % least)
        day = time.strftime("%Y%m%d")
        made = [x for x in self.signups.get(addr, []) if x == day]
        if env_int("DS_REGISTER_PER_DAY", 3) > 0 and len(made) >= env_int("DS_REGISTER_PER_DAY", 3):
            return no("Too many new accounts from here today: try again tomorrow.")
        email = clean_email(d.get("email", ""))
        if d.get("email") and not email:
            return no("That doesn't look like an email address (or leave it empty).")
        if email and self.store.account_by_email(email):
            return no("That email is on another account already.")
        code = auth.recovery_code()
        self.store.create_account(name, await self.hashed(password), await self.hashed(auth.clean_code(code)), email)
        self.claims.pop(name.lower(), None)
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
        acct = self.store.account(name) or self.store.account_by_email(str(d.get("name", "")).strip())
        code = auth.clean_code(d.get("code", ""))
        by_mail = acct is not None and await self.matches(code, self.store.mail_code(acct[0]))
        if acct is None or not (by_mail or await self.matches(code, acct[2])):
            self.failed(name, addr)
            return no("That name and code don't go together.")
        if by_mail:
            self.store.drop_mail_code(acct[0])
        new = str(d.get("password", ""))[:200]
        if len(new) < max(4, env_int("DS_PASSWORD_MIN", 8)):
            return no("Use a new password of at least %d characters." % max(4, env_int("DS_PASSWORD_MIN", 8)))
        code = auth.recovery_code()
        self.store.set_password(acct[0], await self.hashed(new))
        self.store.set_recover(acct[0], await self.hashed(auth.clean_code(code)))
        return yes(recovery=code, name=acct[0])

    async def account(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        if not name:
            return no("Not logged in.")
        acct = self.store.account(name)
        return yes(name=name, email=acct[4] if acct else "", admin=self.is_admin(name), mail=mail.ready())

    async def set_email(self, request):
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        if not name:
            return no("Not logged in.")
        email = clean_email(d.get("email", ""))
        if d.get("email") and not email:
            return no("That doesn't look like an email address.")
        other = self.store.account_by_email(email) if email else None
        if other and other[0].lower() != name.lower():
            return no("That email is on another account already.")
        self.store.set_email(name, email)
        return yes(email=email)

    async def forgot(self, request):
        """A code by email to set a new password (the same answer whether or not there's such an account)."""
        d, addr = await self.body(request), self.addr(request)
        who = str(d.get("who", "")).strip()[:254]
        w = self.wait(who, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        if not mail.ready():
            return no("This server can't send email: use the recovery code you wrote down.")
        acct = self.store.account(auth.clean_name(who)) if "@" not in who else self.store.account_by_email(who)
        self.failed(who, addr)                          # (counted: nobody's mailbox flooded)
        if acct and acct[4]:
            code = auth.recovery_code()[:9]             # (two groups of four: easy to type in)
            self.store.new_mail_code(acct[0], await self.hashed(auth.clean_code(code)))
            text = ("Someone (we hope you) asked to set a new password for %s on %s.\n\nYour code: %s\n\nType it with "
                    "your name and a new password where you asked. It works for %d minutes. If it wasn't you, do "
                    "nothing: your password stays as it is.\n" % (acct[0], self.name, code, 30))
            try:
                await asyncio.get_running_loop().run_in_executor(None, mail.send, acct[4],
                                                                 "%s: your code" % self.name, text)
            except Exception as e:
                log.warning("The email to %s didn't go: %s", acct[0], e)
                return no("The email couldn't be sent just now: try again later, or use your recovery code.")
        return yes(text="If that account has an email, a code is on its way: it works for 30 minutes.")

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
        known = self.store.server_url(server)
        if known and not same_place(known, str(d.get("url", ""))[:200]):
            # (a listed game is where it said it was: a game that gave another's id gets no ticket to pass on)
            return no("That game isn't at the address it was listed at.")
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
        pre = {k.strip() for k in os.environ.get("DS_CENTRAL_APPROVED", "").split(",") if k.strip()}
        if key in pre and not self.store.approved(key):
            self.store.set_approved(key, True)          # (approved in the settings, before it ever called)
        return yes(key=key, secret=secret, url=url, approved=self.store.approved(key))

    async def goodbye(self, request):
        d = await self.body(request)
        self.store.goodbye(str(d.get("key", "")), str(d.get("secret", "")))
        return yes()

    async def servers(self, request):
        return web.json_response(self.store.servers())

    async def hello(self, request):
        client = os.environ.get("DS_ADSENSE_CLIENT", "").strip()
        return yes(name=self.name, motd=self.motd, ad=random.choice(self.ads()),
                   servers=len(self.store.servers()), players=self.store.count_accounts(), mail=mail.ready(),
                   adsense={"client": client, "slot": os.environ.get("DS_ADSENSE_SLOT", "").strip()} if client else None)

    # ----- the admin page's (an admin's token each time)
    async def admin(self, request):
        """POST /api/admin/<what> {token, ...}: what an admin may see and do."""
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        if not self.is_admin(name):
            return no("That's for the central server's admins.")
        what = request.match_info["what"]
        if what == "stats":
            every = self.store.servers(everyone=True)
            return yes(accounts=self.store.count_accounts(), servers=len(every),
                       approved=sum(1 for s in every if s["approved"]), up=sum(1 for s in every if s["up"]),
                       mail=mail.ready(), adsense=bool(os.environ.get("DS_ADSENSE_CLIENT")))
        if what == "servers":
            return yes(servers=self.store.servers(everyone=True))
        if what == "approve":
            self.store.set_approved(str(d.get("key", "")), bool(d.get("on")))
            log.info("%s %s server %s", name, "approved" if d.get("on") else "unlisted", d.get("key"))
            return yes()
        if what == "remove":
            self.store.remove_server(str(d.get("key", "")))
            return yes()
        if what == "accounts":
            rows = self.store.find_accounts(str(d.get("q", ""))[:60])
            return yes(accounts=[{"name": n, "email": e, "banned": b, "admin": bool(a) or self.is_admin(n),
                                  "made": int(m)} for n, e, b, a, m in rows])
        if what == "ban":
            acct = self.store.account(str(d.get("name", "")))
            if acct is None:
                return no("No such account.")
            self.store.set_banned(acct[0], str(d.get("why", ""))[:100])
            return yes()
        if what == "make_admin":
            acct = self.store.account(str(d.get("name", "")))
            if acct is None:
                return no("No such account.")
            self.store.set_admin(acct[0], bool(d.get("on")))
            return yes()
        if what == "ads":
            if "ads" in d:
                ads = [a for a in d["ads"] if isinstance(a, dict) and str(a.get("text", "")).strip()][:50] \
                    if isinstance(d["ads"], list) else []
                self.store.set_setting("ads", json.dumps(ads))
            return yes(ads=self.ads())
        return no("Unknown.")


def yes(**more):
    return web.json_response({"ok": True, **more})


def same_place(a, b):
    """Do two addresses name the same server (its host and port, whichever scheme)?"""
    from urllib.parse import urlsplit
    try:
        ua, ub = urlsplit(a), urlsplit(b)
        pa = ua.port or (443 if ua.scheme == "https" else 80)
        pb = ub.port or (443 if ub.scheme == "https" else 80)
    except ValueError:
        return False
    return bool(ua.hostname) and ua.hostname == ub.hostname and pa == pb


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

    pages = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

    async def admin_page(request):
        return web.FileResponse(os.path.join(pages, "admin.html"), headers={"Cache-Control": "no-cache"})

    async def privacy(request):
        with open(os.path.join(pages, "privacy.html"), encoding="utf-8") as f:
            text = f.read()
        for key, value in (("{{NAME}}", c.name), ("{{OPERATOR}}", os.environ.get("DS_CENTRAL_OPERATOR", c.name)),
                           ("{{CONTACT}}", os.environ.get("DS_CENTRAL_CONTACT", "the address on the game's page")),
                           ("{{ADS}}", "Google AdSense" if os.environ.get("DS_ADSENSE_CLIENT") else "our own notes"),
                           ("{{APPADS}}", "Google AdMob" if os.environ.get("DS_ADMOB_APP") else "our own notes")):
            text = text.replace(key, value.replace("<", "&lt;"))
        return web.Response(text=text, content_type="text/html")

    async def ads_txt(request):
        # (Google's line for each publisher: AdSense's ca-pub-123..., AdMob's app ca-app-pub-123...~456, often the same)
        pubs = []
        for key, cut in (("DS_ADSENSE_CLIENT", "ca-"), ("DS_ADMOB_APP", "ca-app-")):
            pub = os.environ.get(key, "").strip().split("~")[0].replace(cut, "", 1)
            if pub and pub not in pubs:
                pubs.append(pub)
        return web.Response(text="".join("google.com, %s, DIRECT, f08c47fec0942fa0\n" % p for p in pubs),
                            content_type="text/plain")

    async def health(request):
        return web.json_response({"ok": True, "servers": len(c.store.servers())})

    app = web.Application(middlewares=[cors])
    app["central"] = c
    for path, fn in (("register", c.register), ("login", c.login), ("reset", c.reset), ("me", c.me),
                     ("logout", c.logout), ("recovery", c.recovery), ("ticket", c.ticket), ("verify", c.verify),
                     ("announce", c.announce), ("goodbye", c.goodbye), ("account", c.account),
                     ("email", c.set_email), ("forgot", c.forgot)):
        app.router.add_post("/api/" + path, fn)
        app.router.add_route("OPTIONS", "/api/" + path, lambda r: web.Response())
    app.router.add_get("/api/servers", c.servers)
    app.router.add_post("/api/admin/{what}", c.admin)
    app.router.add_get("/admin", admin_page)
    app.router.add_get("/privacy", privacy)
    app.router.add_get("/ads.txt", ads_txt)
    app.router.add_get("/app-ads.txt", ads_txt)        # (AdMob reads it on the developer's site the Play Store names)
    app.router.add_get("/api/hello", c.hello)
    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    app.router.add_get("/config.js", lambda r: web.FileResponse(os.path.join(home, "config.js"),
                                                               headers={"Cache-Control": "no-cache"}))
    for pic in ("logo.png", "bg.jpg"):                  # (the start screen's pictures, beside it)
        app.router.add_get("/" + pic, lambda r, pic=pic: web.FileResponse(os.path.join(home, pic)))
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
