"""The central server: every player's account (one name and password for every game, or Google), the list of remote game
servers (each announces itself: its name, address and how many are playing), what every game's characters have got to
(for the admin page), the ads on the start screen, and the start screen itself for a browser. Standard library plus
aiohttp, like the game server.

The apps (Android, desktop) and a browser open the start screen, log in here, and then: play alone, host a game (local:
only answered on its own network; remote: announced here, listed for everyone), or join one (local: on the network or
by address; remote: from the list here). Joining, the start screen asks here for a ticket for that one server, and the
game server asks here whether the ticket's good (the player's name, once, for that server only). A game server keeps
its own accounts too, for a network with no way to reach here.

  python -m central                    (DS_CENTRAL_DB, DS_CENTRAL_PORT 8490, DS_CENTRAL_NAME, DS_CENTRAL_ADS, ...)

  POST /api/register  {name, password, email}     -> {ok, token, name, confirm}
  POST /api/account   {token}                     -> {ok, name, email, pending, admin}
  POST /api/email     {token, email}              -> {ok, email, pending, text}   (it counts once a link's confirmed it)
  POST /api/email/again {token}                   -> {ok, text}          (the link again, for the one waiting)
  POST /api/forgot    {who}                       -> {ok}                (a code by email, if it has a confirmed one)
  POST /api/login     {name, password}            -> {ok, token, name, needs_email}
  GET  /auth/google?to=home|app|admin, /auth/google/done   off to Google and back (google.py): a browser comes back to
                                                  the page with a code in its fragment, an app's shows the code to type
  POST /api/google    {code, name?, claim?}       -> {ok, token, name} or, new to us, {ok, choose}: send the name wanted
  POST /api/reset     {name, code, password}      -> {ok, name}          (code: the emailed one)
  POST /api/me        {token}                     -> {ok, name, needs_email}
  POST /api/logout    {token}
  POST /api/ticket    {token, server}             -> {ok, ticket}        (server: the game server's id; refused: banned,
                                                  or no confirmed email: the join stops there and says why)
  POST /api/verify    {ticket, server}            -> {ok, name}          (a game server asking)
  POST /api/game/standing {name}                  -> {ok, banned}        (a game server, for one come straight back)
  POST /api/game/report {secret, kind, name?, version, server?, proof?, characters: [...]}  -> {ok, took}  (a game server:
                                                  what its characters have got to, for the admin page: server/progress.py)
  POST /api/announce  {key, secret, name, url?, port, online, max, version}  -> {key, secret}
  POST /api/goodbye   {key, secret}
  GET  /api/servers                               -> [{key, name, url, online, max, version}]   (approved only)
  POST /api/admin/... {token, ...}                the admin page's (servers, approving, accounts, bans, deleting, ads, stats)
  GET  /confirm?code=, POST /confirm {code}       a link's page, and its button (a mail scanner opens links: only the
                                                  button confirms)
  GET  /admin, /privacy, /ads.txt, /app-ads.txt   the admin page, the privacy policy, AdSense's and AdMob's lines
  GET  /api/hello                                 -> {name, motd, ad, players, servers}
  GET  /health                                    -> {ok, servers, version, commit, date}
  GET  /                                          the start screen (a browser's: join a game, local or remote)"""
import asyncio
import functools
import hashlib
import hmac
import html
import json
import logging
import os
import random
import re
import sqlite3
import time

from aiohttp import web

from server import auth
from server.version import version_info
from ashen import ini
from . import google, mail
from .relay import Relays
from .store import CentralStore, CONFIRM_DAYS, MOST_FRIENDS, digest

log = logging.getLogger("ashen.central")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS, FAIL_WINDOW, FAIL_WAIT = 6, 300, 60
ANNOUNCES = 30                  # (calls from one address in ten minutes: a game announces itself once a minute)
REPORTS = 90                    # (reports from one address in ten minutes: every five, more while it catches up)
REPORTERS_A_DAY = 20            # (new game servers reporting from one address in a day)
REPORT_CHARACTERS = 50          # (characters in one report: more wait for the next)
REPORTER_MOST = 20000           # (characters a game server may have here)
PAGE = 50                       # (rows the admin page gets at a time)
GOOGLE_COOKIE = "ds_google"
GOOGLE_PENDING = 2000           # (sign-ins under way at once: past this the oldest go)
HOUSEKEEPING = 600              # (seconds between clearing out what's had its day)
HELLO_SECONDS = 30              # (the start screen's counts are worked out this often)
RESERVED = {"admin", "administrator", "moderator", "mod", "server", "system", "gm", "staff", "support", "owner"}
DEFAULT_ADS = [
    {"text": "Host your own world: friends on your Wi-Fi join it from their phones.", "link": ""},
    {"text": "Run a server on a cloud VM and it's listed here for everyone: see README-Server.md.", "link": ""},
]


CONFIRMS_A_DAY = 5
NEEDS_EMAIL = "Your account needs an email: it's the only way back in if you forget your password."
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,20}$")


def clean_email(text):
    e = str(text or "").strip()[:254]
    return e if EMAIL_RE.match(e) else ""


compact = functools.partial(json.dumps, separators=(",", ":"))      # (no spaces: every answer a little smaller)


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Central:
    def __init__(self, db_path):
        self.store = CentralStore(db_path)
        self.relays = Relays(self.store)            # (games hosted for friends, passed through here)
        self.fails = {}                 # (kind, which) -> [times]
        self.signups = {}               # address -> [days]
        self.confirms = {}              # account or email -> how many confirmation emails today
        self.confirm_day = ""
        self.announces = {}             # address -> [times] a game server called
        self.reports = {}               # address -> [times] a game server reported
        self.new_reporters = {}         # address -> [days] a new game server reported
        self.google_flows = {}          # state -> a sign-in on its way to Google and back
        self.google_results = {}        # code -> who came back from Google: {name} or {sub, email}, and when
        self.hello_cache = (0.0, {})    # (when, the start screen's counts)
        self.ads_cache = (0.0, None)    # (when, the ads)
        self.quests_cache = (None, [])  # (Quests.ini's time, what's in it)
        self.name = os.environ.get("DS_CENTRAL_NAME", "Shards of Ashen")
        self.motd = os.environ.get("DS_CENTRAL_MOTD", "")
        # (an admin named in DS_CENTRAL_ADMINS with no account yet: only someone with the code from this log may make
        # it, or whoever signed up first would be the admin; kept, so a restart or an update doesn't change it)
        self.claims = {}
        for n in os.environ.get("DS_CENTRAL_ADMINS", "").split(","):
            if n.strip() and not self.store.account(n.strip()):
                key = "claim:" + n.strip().lower()
                if not self.store.setting(key):
                    self.store.set_setting(key, auth.recovery_code())
                self.claims[n.strip().lower()] = self.store.setting(key)
                log.warning("DS_CENTRAL_ADMINS names %s, who has no account yet: sign up as %s with the admin code %s",
                            n.strip(), n.strip(), self.claims[n.strip().lower()])

    # ----- who's asking, and how often
    @staticmethod
    def addr(request):
        return auth.client_address(request)

    def wait(self, name, addr):
        now = time.monotonic()
        waits = []
        for key in (("name", name.lower()), ("addr", addr)):
            times = [t for t in self.fails.get(key, []) if now - t < FAIL_WINDOW]
            if times:
                self.fails[key] = times
            else:
                self.fails.pop(key, None)
            if len(times) >= FAILS:
                waits.append(int(FAIL_WAIT - (now - times[-1])) + 1)
        return max([w for w in waits if w > 0], default=0)

    def failed(self, name, addr):
        """Counted as a wrong try (before it's checked, so tries at once can't all slip by): when, for forgiven."""
        now = time.monotonic()
        for key in (("name", name.lower()), ("addr", addr)):
            self.fails.setdefault(key, []).append(now)
        return now

    def forgiven(self, name, addr, at):
        for key in (("name", name.lower()), ("addr", addr)):
            if at in self.fails.get(key, []):
                self.fails[key].remove(at)

    def is_admin(self, name):
        """An admin of the central server: its account marked so (the admin page), or named in DS_CENTRAL_ADMINS."""
        if not name:
            return False
        names = {n.strip().lower() for n in os.environ.get("DS_CENTRAL_ADMINS", "").split(",") if n.strip()}
        acct = self.store.account(name)
        return bool(acct) and (bool(acct[5]) or name.lower() in names)

    def ads(self):
        now = time.monotonic()
        if self.ads_cache[1] is None or now - self.ads_cache[0] > HELLO_SECONDS:
            self.ads_cache = (now, self.read_ads())
        return self.ads_cache[1]

    def read_ads(self):
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
        refused = self.name_refused(name, d.get("claim", ""))
        if refused:
            return no(**refused)
        least = max(4, env_int("DS_PASSWORD_MIN", 8))
        if len(password) < least or password.lower() == name.lower():
            return no("Use a password of at least %d characters (not your name)." % least)
        made = self.signups_today(addr)
        if made is None:
            return no("Too many new accounts from here today: try again tomorrow.")
        email = clean_email(d.get("email", ""))
        if not d.get("email"):
            return no(NEEDS_EMAIL)
        if not email:
            return no("That doesn't look like an email address.")
        if self.store.account_by_email(email):
            return no("That email is on another account already.")
        self.signups[addr] = made + [time.strftime("%Y%m%d")]   # (counted now: sign-ups at once can't all slip by)
        try:
            self.store.create_account(name, await self.hashed(password))
        except sqlite3.IntegrityError:                  # (taken while the password was hashed)
            self.signups[addr] = made
            return no("That name is taken. Log in instead?")
        self.claims.pop(name.lower(), None)
        log.info("New account %s from %s", name, addr)
        self.store.set_pending_email(name, email)
        # (to one side: a mail service's trouble is never a sign-up's, and they can ask again from their account)
        asyncio.ensure_future(self.ask_confirm(self.base_url(request), name, email, welcome=True))
        return yes(token=self.store.new_token(name), name=name, confirm=True)

    def name_refused(self, name, claim):
        """Why a new account can't have this name, or nothing: (no's words)."""
        if not name:
            return {"text": "Pick a name: letters, numbers, spaces, _ and -."}
        if os.environ.get("DS_REGISTRATION", "open") != "open":
            return {"text": "New accounts can't be made just now."}
        if name.lower() in RESERVED:
            return {"text": "That name is kept back: pick another."}
        if self.store.account(name):
            return {"text": "That name is taken. Log in instead?"}
        code = self.claims.get(name.lower())
        if code and auth.clean_code(str(claim or "")) != auth.clean_code(code):
            return {"claim": True, "text": "That name is kept for this server's admin: give the admin code from the "
                                           "server's log."}
        return None

    def signups_today(self, addr):
        """The accounts made from here today, or None when that's as many as may be."""
        day = time.strftime("%Y%m%d")
        made = [x for x in self.signups.get(addr, []) if x == day]
        most = env_int("DS_REGISTER_PER_DAY", 3)
        return None if most > 0 and len(made) >= most else made

    def needs_email(self, name):
        """An account from before an email was required, with none given yet (or one forgotten, never confirmed)."""
        acct = self.store.account(name)
        return bool(acct and not acct[4] and not self.store.pending_email(name))

    @staticmethod
    def base_url(request):
        """Where a link in an email goes: this server's address. (Caddy answers only for its own domain, so the Host
        it passes on can be trusted.)"""
        proto = request.scheme
        if os.environ.get("DS_TRUST_PROXY", "").strip() in ("1", "yes", "on", "true"):
            told = request.headers.get("X-Forwarded-Proto", "")
            proto = told if told in ("http", "https") else proto
        return "%s://%s" % (proto, request.host)

    def counted_confirm(self, name, email):
        """So many confirmation emails a day, to an account or to an address: nobody's mailbox flooded."""
        day = time.strftime("%Y%m%d")
        if day != self.confirm_day:
            self.confirm_day, self.confirms = day, {}
        keys = (name.lower(), email.lower())
        if any(self.confirms.get(k, 0) >= CONFIRMS_A_DAY for k in keys):
            return False
        for k in keys:
            self.confirms[k] = self.confirms.get(k, 0) + 1
        return True

    async def ask_confirm(self, base, name, email, welcome=False):
        """Emails the link that confirms what's waiting on this account: "" when it's gone, else why not. Never a
        password or a recovery code."""
        if not mail.ready():
            return "This server can't send email just now."
        if not self.counted_confirm(name, email):
            return "We've sent that address enough for one day: look in its spam folder, or try again tomorrow."
        link = "%s/confirm?code=%s" % (base, self.store.new_mail_check(name))
        hello = ("Welcome to %s, %s.\n\nYour Shards account is ready: the same name and password sign you in to every "
                 "game. Your characters live on the server you make them on.\n\n" % (self.name, name) if welcome else
                 "Someone (we hope you) gave this address for the Shards account %s.\n\n" % name)
        text = ("%sConfirm this address so we can send you a code if you ever forget your password:\n\n%s\n\nThe link "
                "works for %d days. If this wasn't you, do nothing: this address won't be used, and we'll forget it.\n"
                % (hello, link, CONFIRM_DAYS))
        try:
            await asyncio.get_running_loop().run_in_executor(None, mail.send, email,
                                                             "%s: confirm your email" % self.name, text)
        except Exception as e:
            log.warning("The email to confirm %s's address didn't go: %s", name, e)
            return "The email couldn't be sent just now: try again later."
        return ""

    async def login(self, request):
        d, addr = await self.body(request), self.addr(request)
        name = auth.clean_name(d.get("name", ""))
        w = self.wait(name, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        acct = self.store.account(name)
        if acct and acct[6]:
            return no("%s has been deleted." % acct[0])
        at = self.failed(name, addr)
        if acct is None or not await self.matches(str(d.get("password", ""))[:200], acct[1]):
            if acct and self.store.google_of(acct[0]):
                return no("%s signs in with Google: it has no password." % acct[0])
            return no("That name and password don't go together.")
        self.forgiven(name, addr, at)
        if acct[3]:
            return no("%s is banned: %s" % (acct[0], acct[3]))
        return yes(token=self.store.new_token(acct[0]), name=acct[0], needs_email=self.needs_email(acct[0]))

    # ----- signing in with Google (google.py): one way for a browser and the apps, no polling, nothing kept on disk
    def google_person(self, sub, email):
        """Who this Google account is here: {name} (the account made with it, or the one with its email: accounts.email
        is only ever a confirmed address, and Google has verified it, so it's the same person; nothing's kept of it, so
        the account's password goes on working, and if its email changes this no longer gets in), or {sub, email} (nobody
        yet, a name to choose)."""
        acct = self.store.account_by_google(sub)
        if acct is None:
            acct = self.store.account_by_email(email)
            if acct is None:
                return {"sub": sub, "email": email}
            if self.store.google_of(acct[0]):           # (made with another Google account, that once had this address)
                raise google.Refused("That email is on an account made with another Google account.")
        if acct[3]:
            raise google.Refused("%s is banned: %s" % (acct[0], acct[3]))
        return {"name": acct[0]}

    def trim_google(self):
        now = time.time()
        for kept, seconds in ((self.google_flows, google.FLOW_SECONDS), (self.google_results, google.RESULT_SECONDS)):
            for k in [k for k, v in kept.items() if now - v["at"] > seconds]:
                del kept[k]
            while len(kept) > GOOGLE_PENDING:           # (dicts keep their order: the oldest first)
                del kept[next(iter(kept))]

    async def google_result(self, request):
        """The start screen hands in the code it was given: signed in, or (new here) it asks for a name, and creates the
        account as a sign-up would, its email the one Google has verified."""
        d, addr = await self.body(request), self.addr(request)
        code = auth.clean_code(d.get("code", ""))
        w = self.wait("google:" + code, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        at = self.failed("google:" + code, addr)
        self.trim_google()
        found = self.google_results.get(code)
        if found is None:
            return no("That code isn't right, or it's run out: sign in with Google again.")
        self.forgiven("google:" + code, addr, at)
        if "name" in found:
            del self.google_results[code]
            acct = self.store.account(found["name"])
            if acct is None or acct[6]:
                return no("That account has been deleted.")
            if acct[3]:
                return no("%s is banned: %s" % (acct[0], acct[3]))
            return yes(token=self.store.new_token(acct[0]), name=acct[0], needs_email=self.needs_email(acct[0]))
        wanted = d.get("name")
        if wanted is None:
            return yes(choose=True, email=found["email"])
        name = auth.clean_name(wanted)
        refused = self.name_refused(name, d.get("claim", ""))
        if refused:
            return no(choose=True, **refused)
        if self.store.account_by_google(found["sub"]) or self.store.account_by_email(found["email"]):
            del self.google_results[code]               # (made meanwhile, by another way in: sign in that way)
            return no("That email is on an account here now: sign in with Google again to go into it.")
        made = self.signups_today(addr)
        if made is None:
            return no("Too many new accounts from here today: try again tomorrow.")
        try:
            self.store.create_account(name, "", found["email"], found["sub"])
        except sqlite3.IntegrityError:
            return no("That name is taken. Log in instead?", choose=True)
        self.signups[addr] = made + [time.strftime("%Y%m%d")]
        self.claims.pop(name.lower(), None)
        del self.google_results[code]
        log.info("New account %s from %s, by Google", name, addr)
        return yes(token=self.store.new_token(name), name=name, needs_email=False, made=True)

    async def reset(self, request):
        d, addr = await self.body(request), self.addr(request)
        name = auth.clean_name(d.get("name", ""))
        w = self.wait(name, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        acct = self.store.account(name) or self.store.account_by_email(str(d.get("name", "")).strip())
        code = auth.clean_code(d.get("code", ""))
        at = self.failed(name, addr)
        if acct is None or not await self.matches(code, self.store.mail_code(acct[0])):
            return no("That name and code don't go together.")
        self.forgiven(name, addr, at)
        self.store.drop_mail_code(acct[0])
        new = str(d.get("password", ""))[:200]
        if len(new) < max(4, env_int("DS_PASSWORD_MIN", 8)):
            return no("Use a new password of at least %d characters." % max(4, env_int("DS_PASSWORD_MIN", 8)))
        self.store.set_password(acct[0], await self.hashed(new))
        return yes(name=acct[0])

    async def account(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        if not name:
            return no("Not logged in.")
        acct = self.store.account(name)
        return yes(name=name, email=acct[4] if acct else "", pending=self.store.pending_email(name),
                   admin=self.is_admin(name), mail=mail.ready())

    async def set_email(self, request):
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        if not name:
            return no("Not logged in.")
        email = clean_email(d.get("email", ""))
        if d.get("email") and not email:
            return no("That doesn't look like an email address.")
        if not email:
            return no(NEEDS_EMAIL)
        mine = self.store.account(name)[4]
        if email.lower() == mine.lower():               # (back to the one that's confirmed: nothing to ask)
            self.store.drop_mail_check(name)
            self.store.set_email(name, email)
            return yes(email=email, pending="", text="Saved.")
        other = self.store.account_by_email(email)
        if other and other[0].lower() != name.lower():
            return no("That email is on another account already.")
        if self.store.pending_email(name).lower() != email.lower():
            self.store.set_pending_email(name, email)   # (the one they have now, if any, counts till this is confirmed)
        why = await self.ask_confirm(self.base_url(request), name, email)
        return yes(email=mine, pending=email, text=why or "Look in that inbox for a link to confirm it.")

    async def email_again(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        if not name:
            return no("Not logged in.")
        email = self.store.pending_email(name)
        if not email:
            return no("There's no email waiting to be confirmed.")
        why = await self.ask_confirm(self.base_url(request), name, email)
        return no(why) if why else yes(text="Sent. Look in that inbox for the link, and its spam folder.")

    async def forgot(self, request):
        """A code by email to set a new password (the same answer whether or not there's such an account), only ever
        to an address its owner has confirmed. An account made with Google has no password to set: it's told so, no code."""
        d, addr = await self.body(request), self.addr(request)
        who = str(d.get("who", "")).strip()[:254]
        w = self.wait(who, addr)
        if w:
            return no("Too many tries: wait %d seconds." % w)
        if not mail.ready():
            return no("This server can't send email just now: try again later.")
        acct = self.store.account(auth.clean_name(who)) if "@" not in who else self.store.account_by_email(who)
        self.failed(who, addr)                          # (counted: nobody's mailbox flooded)
        if acct and acct[4]:
            if self.store.google_of(acct[0]):
                subject = "%s: signing in" % self.name
                text = ("Someone (we hope you) asked to set a new password for %s on %s. That account signs in with Google "
                        "and has no password: use Continue with Google on the start screen.\n" % (acct[0], self.name))
            else:
                code = auth.recovery_code()[:9]         # (two groups of four: easy to type in)
                self.store.new_mail_code(acct[0], await self.hashed(auth.clean_code(code)))
                subject = "%s: your code" % self.name
                text = ("Someone (we hope you) asked to set a new password for %s on %s.\n\nYour code: %s\n\nType it with "
                        "your name and a new password where you asked. It works for %d minutes. If it wasn't you, do "
                        "nothing: your password stays as it is.\n" % (acct[0], self.name, code, 30))
            try:
                await asyncio.get_running_loop().run_in_executor(None, mail.send, acct[4], subject, text)
            except Exception as e:
                log.warning("The email to %s didn't go: %s", acct[0], e)
                return no("The email couldn't be sent just now: try again later.")
        return yes(text="If that account has a confirmed email, a code is on its way: it works for 30 minutes.")

    async def me(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        return yes(name=name, needs_email=self.needs_email(name)) if name else no("Not logged in.")

    async def logout(self, request):
        self.store.drop_token((await self.body(request)).get("token", ""))
        return yes()

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
            return no("%s is banned: %s" % (name, acct[3]), refused=True)
        if self.needs_email(name):
            return no("Your account needs an email first: open your account to give one.", refused=True)
        if acct and not acct[4]:                        # (only ever a confirmed one: what's waiting doesn't count yet)
            return no("Confirm your email first: the link's in your inbox, or open your account to send it again.",
                      refused=True)
        known = self.store.server_url(server)
        if known and not same_place(known, str(d.get("url", ""))[:200]):
            # (a listed game is where it said it was: a game that gave another's id gets no ticket to pass on)
            return no("That game isn't at the address it was listed at.")
        return yes(ticket=self.store.new_ticket(name, server))

    async def verify(self, request):
        """A game server checks a ticket: whose it is, their friends, and a key to them while they play there."""
        d = await self.body(request)
        server = str(d.get("server", ""))[:64]
        name = self.store.use_ticket(d.get("ticket", ""), server)
        if not name:
            return no("That ticket isn't good here.")
        if self.is_banned(name):                        # (banned since the ticket was made)
            return no("%s is banned: %s" % (name, self.store.account(name)[3]), banned=True)
        return yes(name=name, grant=self.store.new_grant(name, server), **self.friends_of(name))

    def is_banned(self, name):
        """Kept out: banned, or the account's been deleted (a device it came in by doesn't go on being let in)."""
        acct = self.store.account(name)
        return acct is None or bool(acct[3] or acct[6])

    async def game_standing(self, request):
        """A game server, for someone who came straight back to it with no ticket: is the account banned? Only that:
        anyone can ask this, so the reason's kept for whoever signs in (login, ticket)."""
        d = await self.body(request)
        return yes(banned=self.is_banned(str(d.get("name", ""))[:40]))

    # ----- friends: by account, the same in every game
    def friends_of(self, name):
        """name's friends, asks either way, where friends are playing, and the games friends host (relay.py)."""
        friends, asking, asked = self.store.friend_lists(name)
        playing = self.store.playing_of(friends)
        for p in playing.values():
            p["relay"] = p["server"] in self.relays.tunnels      # (a friend's game: joined through here)
        return {"friends": friends, "asking": asking, "asked": asked, "playing": playing,
                "hosting": self.relays.hosting(friends)}

    def change_friend(self, name, other, remove):
        """name asks other to be friends (or accepts their ask), or they're friends no more: (what happened, why not)."""
        acct = self.store.account(auth.clean_name(other))
        if acct is None or acct[6]:
            return "", "There's no Shards account called %s." % str(other)[:20]
        if acct[0].lower() == name.lower():
            return "", "That's your own account."
        if remove:
            self.store.drop_friend(name, acct[0])
            return "removed", ""
        if self.store.asked_count(name) >= MOST_FRIENDS:
            return "", "Your friends list is full."
        return self.store.ask_friend(name, acct[0]), ""

    async def friends(self, request):
        name = self.store.token_name((await self.body(request)).get("token", ""))
        return yes(**self.friends_of(name)) if name else no("Not logged in.")

    async def friend(self, request):
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        if not name:
            return no("Not logged in.")
        done, why = self.change_friend(name, d.get("name", ""), bool(d.get("remove")))
        return no(why) if why else yes(done=done, **self.friends_of(name))

    async def game_friends(self, request):
        """A game server, for a player playing there (its key from their ticket): where they're playing (playing: the
        character, "" when they've gone), a friend asked or removed (name), and their friends back."""
        d = await self.body(request)
        got = self.store.grant_name(d.get("grant", ""))
        if not got:
            return no("Come in again from the start screen to see your friends.")
        name, server = got
        if self.is_banned(name):
            return no("%s is banned." % name, banned=True)
        done = ""
        if d.get("name"):
            done, why = self.change_friend(name, d["name"], bool(d.get("remove")))
            if why:
                return no(why)
        if "playing" in d:
            self.store.set_playing(name, server, str(d.get("place", ""))[:60], auth.clean_name(d.get("playing", "")))
        news = self.friends_of(name)
        have = hashlib.md5(json.dumps(news, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        if d.get("have") == have:                       # (each player, each minute: mostly nothing's changed)
            return yes(done=done, same=True)
        return yes(done=done, have=have, **news)

    # ----- what every game server's characters have got to (server/progress.py), for the admin page
    async def game_report(self, request):
        """A game server's report: only as honest as that server (the admin page says which it was, and can block it).
        Its key is the hash of its own secret, so nobody can write under another's; a character said to be an account's
        is taken only if there's such an account (a deleted one's stay deleted)."""
        d, addr = await self.body(request), self.addr(request)
        now = time.monotonic()
        heard = [t for t in self.reports.get(addr, []) if now - t < 600]
        if len(heard) >= REPORTS:
            return no("Too many reports from here: wait a while.")
        self.reports[addr] = heard + [now]
        secret = str(d.get("secret", ""))
        if not 16 <= len(secret) <= 128:
            return no("A report needs its server's secret.")
        key = digest(secret)[:32]
        known = self.store.reporter(key)
        if known and known["blocked"]:
            return yes(took=0, blocked=True)
        if known is None:
            day = time.strftime("%Y%m%d")
            new = [x for x in self.new_reporters.get(addr, []) if x == day]
            if len(new) >= REPORTERS_A_DAY:
                return no("Too many new game servers from here today.")
            self.new_reporters[addr] = new + [day]
        rows = clean_characters(d["characters"]) if isinstance(d.get("characters"), list) else []
        if self.store.count_reported(key) + len(rows) > REPORTER_MOST:
            return no("That's more characters than this server keeps for one game.")
        standing = self.store.account_standing({c["account"] for c in rows if c["account"]})
        rows = [c for c in rows if not c["account"] or standing.get(c["account"].lower())]
        kind = str(d.get("kind", ""))
        listed = self.store.proves_server(str(d.get("server", ""))[:64], str(d.get("proof", ""))[:128])
        self.store.take_report(key, " ".join(str(d.get("name", "")).split())[:40],
                               kind if kind in ("solo", "local", "friends", "public") else "local",
                               str(d.get("version", ""))[:40], listed, rows)
        return yes(took=len(rows))

    async def announce(self, request):
        d, addr = await self.body(request), self.addr(request)
        now = time.monotonic()
        heard = [t for t in self.announces.get(addr, []) if now - t < 600]
        if len(heard) >= ANNOUNCES:                     # (a game calls once a minute: not hundreds of rows a second)
            return no("Too many calls from here: a minute between them.")
        self.announces[addr] = heard + [now]
        name = " ".join(str(d.get("name", "")).split())[:40] or "A game of Shards of Ashen"
        url = str(d.get("url", "")).strip()[:200]
        if not url:                                   # (no address of its own: where it's calling from, its port)
            host = self.addr(request)
            if ":" in host:
                host = "[%s]" % host
            url = "http://%s:%d" % (host, whole(d.get("port"), 1, 65535, 8484))
        if not url.startswith(("http://", "https://")):
            return no("A server's address starts http:// or https://.")
        most = whole(d.get("max"), 0, 500)
        key, secret = self.store.announce(str(d.get("key", ""))[:32], str(d.get("secret", ""))[:64], name, url,
                                          whole(d.get("online"), 0, most), most, str(d.get("version", ""))[:40])
        pre = {k.strip() for k in os.environ.get("DS_CENTRAL_APPROVED", "").split(",") if k.strip()}
        if key in pre and not self.store.approved(key):
            self.store.set_approved(key, True)          # (approved in the settings, before it ever called)
        return yes(key=key, secret=secret, url=url, approved=self.store.approved(key))

    async def goodbye(self, request):
        d = await self.body(request)
        self.store.goodbye(str(d.get("key", "")), str(d.get("secret", "")))
        return yes()

    async def servers(self, request):
        # (the list as a browser has it already: said in a few bytes)
        text = compact(self.store.servers())
        tag = '"%s"' % hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
        if request.headers.get("If-None-Match") == tag:
            return web.Response(status=304, headers={"ETag": tag, "Cache-Control": "no-cache"})
        return web.Response(text=text, content_type="application/json", headers={"ETag": tag, "Cache-Control": "no-cache"})

    async def hello(self, request):
        client = os.environ.get("DS_ADSENSE_CLIENT", "").strip()
        now = time.monotonic()
        if not self.hello_cache[1] or now - self.hello_cache[0] > HELLO_SECONDS:
            self.hello_cache = (now, {"servers": self.store.count_servers(), "players": self.store.count_accounts()})
        return yes(name=self.name, motd=self.motd, ad=random.choice(self.ads()), mail=mail.ready(),
                   google=google.ready(), **self.hello_cache[1],
                   adsense={"client": client, "slot": os.environ.get("DS_ADSENSE_SLOT", "").strip()} if client else None)

    # ----- clearing out what's had its day: the database's, and the counts kept here
    def housekeeping(self):
        self.store.prune()
        self.trim_google()
        now, day = time.monotonic(), time.strftime("%Y%m%d")
        for times, seconds in ((self.announces, 600), (self.reports, 600)):
            for k in [k for k, v in times.items() if not v or now - v[-1] > seconds]:
                del times[k]
        for key in [k for k, v in self.fails.items() if not v or now - v[-1] > FAIL_WINDOW]:
            del self.fails[key]
        for days in (self.signups, self.new_reporters):
            for k in [k for k, v in days.items() if day not in v]:
                del days[k]

    async def keep_clean(self):
        while True:
            await asyncio.sleep(HOUSEKEEPING)
            try:
                self.housekeeping()
            except Exception:
                log.exception("Clearing out failed")

    # ----- the quests as the game has them (data/Quests.ini: this server is the same image), for the admin page
    def quest_list(self):
        """[(name, {KEY: value})], in the file's order, the main story's by chapter first."""
        path = os.path.join(ROOT, "data", "Quests.ini")
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            return []
        if self.quests_cache[0] != stamp:
            rows = [(name, {k.upper(): v.strip() for k, v in items}) for name, items in ini.sections(path)]
            main = sorted((r for r in rows if r[1].get("TYPE", "").lower() == "main"),
                          key=lambda r: whole(r[1].get("CHAPTER"), 0, 999))
            self.quests_cache = (stamp, main + [r for r in rows if r[1].get("TYPE", "").lower() != "main"])
        return self.quests_cache[1]

    # ----- the admin page's (an admin's token each time)
    async def admin(self, request):
        """POST /api/admin/<what> {token, ...}: what an admin may see and do."""
        d = await self.body(request)
        name = self.store.token_name(d.get("token", ""))
        if not self.is_admin(name):
            return no("That's for the central server's admins.")
        what = request.match_info["what"]
        if what == "stats":
            every, approved, up = self.store.server_stats()
            chars, accounted, today, week, reporting = self.store.progress_totals()
            return yes(accounts=self.store.count_accounts(), servers=every, approved=approved, up=up, mail=mail.ready(),
                       adsense=bool(os.environ.get("DS_ADSENSE_CLIENT")), google=google.ready(), characters=chars,
                       with_account=accounted, today=today, week=week, reporting=reporting)
        if what == "servers":
            mine = self.version["version"]
            return yes(version=mine, servers=[{**s, "behind": s["up"] and behind(s["version"], mine)}
                                              for s in self.store.servers(everyone=True)])
        if what == "approve":
            self.store.set_approved(str(d.get("key", "")), bool(d.get("on")))
            log.info("%s %s server %s", name, "approved" if d.get("on") else "unlisted", d.get("key"))
            return yes()
        if what == "remove":
            self.store.remove_server(str(d.get("key", "")))
            return yes()
        if what == "accounts":
            rows = self.store.find_accounts(str(d.get("q", ""))[:60], PAGE, whole(d.get("skip"), 0, 10 ** 9))
            names = {n.strip().lower() for n in os.environ.get("DS_CENTRAL_ADMINS", "").split(",") if n.strip()}
            return yes(accounts=[{"name": n, "email": e, "pending": p, "banned": b, "deleted": int(x), "google": bool(g),
                                  "admin": bool(a) or n.lower() in names, "made": int(m)}
                                 for n, e, b, a, m, p, x, g in rows], page=PAGE)
        server = str(d.get("server", ""))[:64]
        if what == "characters":
            return yes(characters=self.store.find_characters(str(d.get("q", ""))[:60], server, PAGE,
                                                             whole(d.get("skip"), 0, 10 ** 9)), page=PAGE)
        if what == "character":
            c = self.store.character(server, str(d.get("name", ""))[:40])
            if c is None:
                return no("No such character.")
            known = dict(self.quest_list())
            for q in c["quests"]:
                info = known.get(q["quest"], {})
                q["of"] = whole(info.get("DONE"), 0, 10 ** 6)
                q["doing"] = info.get("STAGE%d" % q["stage"], "")
            return yes(character=c)
        if what == "quests":
            counts = self.store.quest_stats(server)
            quests = [{"quest": n, "main": q.get("TYPE", "").lower() == "main", "chapter": whole(q.get("CHAPTER"), 0, 999),
                       "began": counts.get(n, (0, 0))[0], "done": counts.get(n, (0, 0))[1]} for n, q in self.quest_list()]
            have = {q["quest"] for q in quests}
            quests += [{"quest": n, "main": False, "chapter": 0, "began": c[0], "done": c[1]}    # (no longer in the game)
                       for n, c in sorted(counts.items()) if n not in have]
            return yes(quests=quests, characters=self.store.find_total(server))
        if what == "quest":
            quest = str(d.get("quest", ""))[:80]
            info = dict(self.quest_list()).get(quest, {})
            return yes(quest=quest, stages=[{"stage": s, "count": n, "doing": info.get("STAGE%d" % s, "")}
                                            for s, n in self.store.quest_stages(quest, server)],
                       done=whole(info.get("DONE"), 0, 10 ** 6))
        if what == "skills":
            return yes(skills=self.store.skill_stats(server))
        if what == "reporters":
            return yes(reporters=self.store.reporters())
        if what == "block":
            self.store.block_reporter(str(d.get("key", ""))[:64], bool(d.get("on")))
            log.info("%s %s a game server's reports", name, "blocked" if d.get("on") else "unblocked")
            return yes()
        if what in ("delete", "erase"):                 # (delete: the name's kept back; erase: it's free for anyone)
            acct = self.store.account(str(d.get("name", "")))
            if acct is None:
                return no("No such account.")
            if self.is_admin(acct[0]):                  # (nor could a name in DS_CENTRAL_ADMINS be left for anyone to take)
                return no("%s is an admin: take that away first." % acct[0])
            self.store.delete_account(acct[0], what == "delete")
            await self.relays.stop_hosting(acct[0])
            log.info("%s %s account %s", name, "deleted" if what == "delete" else "erased", acct[0])
            return yes()
        if what == "ban":
            acct = self.store.account(str(d.get("name", "")))
            if acct is None or acct[6]:
                return no("No such account.")
            self.store.set_banned(acct[0], str(d.get("why", ""))[:100])
            return yes()
        if what == "make_admin":
            acct = self.store.account(str(d.get("name", "")))
            if acct is None or acct[6]:
                return no("No such account.")
            self.store.set_admin(acct[0], bool(d.get("on")))
            return yes()
        if what == "ads":
            if "ads" in d:
                ads = [a for a in d["ads"] if isinstance(a, dict) and str(a.get("text", "")).strip()][:50] \
                    if isinstance(d["ads"], list) else []
                self.store.set_setting("ads", json.dumps(ads))
                self.ads_cache = (0.0, None)
            return yes(ads=self.ads())
        return no("Unknown.")


def yes(**more):
    return web.json_response({"ok": True, **more}, dumps=compact)


def clean_characters(rows):
    """A report's characters, as this server keeps them: names, numbers in range, no more than there should be of
    anything (it's anyone's to send)."""
    out = []
    for c in rows[:REPORT_CHARACTERS]:
        if not isinstance(c, dict):
            continue
        name = auth.clean_name(c.get("name", ""))
        skills, quests = c.get("skills"), c.get("quests")
        if not name:
            continue
        out.append({"name": name, "account": auth.clean_name(c.get("account", "")), "level": whole(c.get("level"), 1, 1000),
                    "shards": whole(c.get("shards"), 0, 10 ** 9), "gold": whole(c.get("gold"), 0, 10 ** 12),
                    "map": str(c.get("map", ""))[:24], "played": whole(c.get("played"), 0, 2 ** 40),
                    "skills": {str(k)[:30]: (whole(v[0], 0, 1000), number(v[1])) for k, v in list(skills.items())[:40]
                               if isinstance(v, list) and len(v) == 2} if isinstance(skills, dict) else {},
                    "quests": {str(k)[:80]: (whole(v[0], -10 ** 6, 10 ** 6), 1 if v[1] else 0)
                               for k, v in list(quests.items())[:400]
                               if isinstance(v, list) and len(v) == 2} if isinstance(quests, dict) else {}})
    return out


def number(v):
    try:
        x = float(v)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return x if 0 <= x < 1e12 else 0.0              # (and not NaN: that fails both)


def whole(v, lo, hi, default=0):
    """A whole number from a request, kept between lo and hi (anything else: default)."""
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError, OverflowError):      # (OverflowError: 1e999 is infinity, in JSON)
        return max(lo, min(hi, default))


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


def no(text, **more):
    return web.json_response({"ok": False, "text": text, **more}, dumps=compact)


def version_numbers(version):
    """A version's numbers ("1.0.123+": (1, 0, 123)), or None with none to go by ("1.0-dev", or none said)."""
    m = re.fullmatch(r"(\d+(?:\.\d+)*)\+?", str(version).strip())
    return tuple(int(n) for n in m.group(1).split(".")) if m else None


def behind(theirs, ours):
    """Is a game server's version older than this central server's? (A server a little ahead has only updated first.)"""
    a, b = version_numbers(theirs), version_numbers(ours)
    return bool(a and b and a < b)


def make_central(db_path):
    c = Central(db_path)
    c.version = version_info(ROOT)
    home = os.path.join(ROOT, "web", "home")

    @web.middleware
    async def cors(request, handler):
        # (the apps' start screens are pages of their own, not this server's: they may ask too)
        if request.method == "OPTIONS":
            resp = web.Response()
        else:
            try:
                resp = await handler(request)
            except UnicodeError:                        # (a broken character: nothing here could look it up or store it)
                resp = no("That has a character in it that can't be read.")
        if resp.prepared:                               # (a WebSocket: under way already)
            return resp
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return resp

    async def index(request):
        return web.FileResponse(os.path.join(home, "index.html"), headers={"Cache-Control": "no-cache"})

    pages = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

    async def admin_page(request):
        return web.FileResponse(os.path.join(pages, "admin.html"), headers={
            "Cache-Control": "no-cache", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                       "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; "
                                       "frame-ancestors 'none'"})

    async def privacy(request):
        with open(os.path.join(pages, "privacy.html"), encoding="utf-8") as f:
            text = f.read()
        for key, value in (("{{NAME}}", c.name), ("{{OPERATOR}}", os.environ.get("DS_CENTRAL_OPERATOR", c.name)),
                           ("{{CONTACT}}", os.environ.get("DS_CENTRAL_CONTACT", "the address on the game's page")),
                           ("{{ADS}}", "Google AdSense" if os.environ.get("DS_ADSENSE_CLIENT") else "our own notes"),
                           ("{{APPADS}}", "Google AdMob" if os.environ.get("DS_ADMOB_APP") else "our own notes")):
            text = text.replace(key, value.replace("<", "&lt;"))
        return web.Response(text=text, content_type="text/html", headers={"Cache-Control": "public, max-age=3600"})

    def confirm_page(title, words, code="", way_back=True):
        """The page a link in an email opens: its words, and its button (only that confirms) or the way back."""
        with open(os.path.join(pages, "confirm.html"), encoding="utf-8") as f:
            text = f.read()
        form = ('<form method="post" action="confirm"><input type="hidden" name="code" value="%s">'
                "<button>Confirm</button></form>" % html.escape(code)) if code else \
            '<p><a href="/">Go to the start screen</a></p>' if way_back else ""
        for key, value in (("{{FORM}}", form), ("{{NAME}}", html.escape(c.name)), ("{{TITLE}}", html.escape(title)),
                           ("{{WORDS}}", html.escape(words))):
            text = text.replace(key, value)
        return web.Response(text=text, content_type="text/html", headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})

    def confirm_gone():
        return confirm_page("That link has run out", "It's been used, it's more than %d days old, or a newer one has "
                            "been sent. Sign in and open your account to send another." % CONFIRM_DAYS)

    async def confirm_ask(request):
        code = request.query.get("code", "")
        found = c.store.mail_check(code)
        if not found:
            return confirm_gone()
        return confirm_page("Confirm your email", "Use %s for the Shards account %s? We only write to it to send a code "
                            "if you forget your password." % (found[1], found[0]), code)

    async def confirm_done(request):
        found = c.store.mail_check(str((await request.post()).get("code", "")))
        if not found:
            return confirm_gone()
        name, email = found
        other = c.store.account_by_email(email)
        c.store.drop_mail_check(name)
        if other and other[0].lower() != name.lower():
            return confirm_page("That email is taken", "%s is on another account already, so it can't be used for %s."
                                % (email, name))
        c.store.set_email(name, email)
        log.info("%s confirmed their email", name)
        return confirm_page("Email confirmed", "If %s's password is ever forgotten, we'll send a code to %s." % (name, email))

    # ----- off to Google and back (google.py)
    async def google_off(request):
        if not google.ready():
            return confirm_page("Not set up", "This server can't sign in with Google.")
        to = request.query.get("to", "home")
        flow = google.new_flow(to if to in ("home", "app", "admin") else "home")
        c.google_flows[flow["state"]] = flow
        c.trim_google()
        base = c.base_url(request)
        resp = web.HTTPFound(google.auth_url(base + "/auth/google/done", flow))
        # (this browser's own: Google's answer is taken only in the one that set off, so nobody can sign you in as them)
        resp.set_cookie(GOOGLE_COOKIE, flow["state"], max_age=google.FLOW_SECONDS, path="/auth/google", httponly=True,
                        samesite="Lax", secure=base.startswith("https://"))
        resp.headers["Cache-Control"] = "no-store"
        raise resp

    async def google_back(request):
        q = request.query
        state = q.get("state", "")
        c.trim_google()
        flow = c.google_flows.get(state)
        if flow is None or not hmac.compare_digest(request.cookies.get(GOOGLE_COOKIE, "").encode("utf-8"), state.encode("utf-8")):
            return confirm_page("That sign-in has run out", "Start again from the sign-in button.", way_back=flow is None)
        del c.google_flows[state]
        if q.get("error") or not q.get("code"):
            return confirm_page("Not signed in", "Google didn't sign you in. Nothing has changed.",
                                way_back=flow["to"] != "app")
        try:
            sub, email = await google.sign_in(q["code"], c.base_url(request) + "/auth/google/done", flow)
            email = clean_email(email)
            if not email:
                raise google.Refused("Google's address for that account can't be used here.")
            person = c.google_person(sub, email)
        except google.Refused as e:
            return confirm_page("Not signed in", str(e), way_back=flow["to"] != "app")
        code = auth.recovery_code()[:9]
        c.google_results[auth.clean_code(code)] = {**person, "at": time.time()}
        if flow["to"] == "app":                         # (the app's in another window, with nothing to come back through)
            return confirm_page("Signed in", "Go back to the game and type this code: %s" % code, way_back=False)
        where = "/admin" if flow["to"] == "admin" else "/"
        resp = web.HTTPFound("%s#google=%s" % (where, code))
        resp.del_cookie(GOOGLE_COOKIE, path="/auth/google")
        resp.headers["Cache-Control"] = "no-store"
        raise resp

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
        return web.json_response({"ok": True, "servers": c.store.count_servers(), **c.version}, dumps=compact)

    app = web.Application(middlewares=[cors])
    app["central"] = c
    cleaning = web.AppKey("cleaning", asyncio.Task)

    async def start_cleaning(app):
        app[cleaning] = asyncio.create_task(c.keep_clean())

    async def stop_cleaning(app):
        app[cleaning].cancel()

    app.on_startup.append(start_cleaning)
    app.on_shutdown.append(stop_cleaning)
    for path, fn in (("register", c.register), ("login", c.login), ("reset", c.reset), ("me", c.me),
                     ("logout", c.logout), ("ticket", c.ticket), ("verify", c.verify),
                     ("announce", c.announce), ("goodbye", c.goodbye), ("account", c.account),
                     ("email", c.set_email), ("email/again", c.email_again), ("forgot", c.forgot),
                     ("friends", c.friends), ("friend", c.friend),
                     ("game/friends", c.game_friends), ("game/standing", c.game_standing),
                     ("game/report", c.game_report), ("google", c.google_result)):
        app.router.add_post("/api/" + path, fn)
        app.router.add_route("OPTIONS", "/api/" + path, lambda r: web.Response())
    app.router.add_get("/api/servers", c.servers)
    app.router.add_get("/api/relay", c.relays.host)
    async def to_game(request):                     # (a friend's game's page is a folder: its files beside it)
        raise web.HTTPFound("/play/%s/" % request.match_info["key"])
    app.router.add_get("/play/{key}", to_game)
    app.router.add_route("*", "/play/{key}/{path:.*}", c.relays.play)
    app.router.add_post("/api/admin/{what}", c.admin)
    app.router.add_get("/admin", admin_page)
    app.router.add_get("/auth/google", google_off)
    app.router.add_get("/auth/google/done", google_back)
    app.router.add_get("/privacy", privacy)
    app.router.add_get("/confirm", confirm_ask)
    app.router.add_post("/confirm", confirm_done)
    app.router.add_get("/ads.txt", ads_txt)
    app.router.add_get("/app-ads.txt", ads_txt)        # (AdMob reads it on the developer's site the Play Store names)
    app.router.add_get("/api/hello", c.hello)
    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    app.router.add_get("/config.js", lambda r: web.FileResponse(os.path.join(home, "config.js"),
                                                               headers={"Cache-Control": "no-cache"}))
    for pic in ("logo.png", "bg.jpg"):                  # (the start screen's pictures, beside it)
        app.router.add_get("/" + pic, lambda r, pic=pic: web.FileResponse(os.path.join(home, pic), headers={
            "Cache-Control": "public, max-age=86400"}))     # (not asked for again each time the start screen opens)
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
